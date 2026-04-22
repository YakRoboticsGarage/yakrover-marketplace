# R-053: MCP, Skills, and Plugins — Agent Integration Research

**Date:** 2026-04-16
**Status:** Complete
**Source:** Claude Code documentation, MCP specification, industry analysis

---

## 1. MCP Architecture

### Protocol Foundation

MCP (Model Context Protocol) is an open protocol using **JSON-RPC 2.0** messages for communication between three actors:

- **Hosts**: LLM applications that initiate connections (e.g., Claude Code, Cursor, Claude Desktop)
- **Clients**: Connectors within the host that manage individual server connections
- **Servers**: Services that provide context and capabilities

Created by David Soria Parra and Justin Spahr-Summers at Anthropic, inspired by the Language Server Protocol (LSP). Current spec version: **2025-03-26**.

Spec: https://modelcontextprotocol.io/specification/2025-03-26

### Transport Layers

**stdio** — Client launches the MCP server as a subprocess. Messages are newline-delimited JSON-RPC over stdin/stdout. Server MAY write logs to stderr. Simplest transport, recommended for local integrations.

**Streamable HTTP** (replaces deprecated HTTP+SSE from 2024-11-05) — Server operates as an independent process with a single HTTP endpoint (e.g., `https://example.com/mcp`). Clients POST JSON-RPC messages; servers respond with either `application/json` or `text/event-stream` (SSE) for streaming. Supports session management via `Mcp-Session-Id` headers, resumability via `Last-Event-ID`, and multiple simultaneous connections. Servers MUST validate Origin headers to prevent DNS rebinding attacks.

**Custom transports** — Any bidirectional channel is allowed, provided it preserves JSON-RPC message format and lifecycle requirements.

Spec: https://modelcontextprotocol.io/specification/2025-03-26/basic/transports

### Connection Lifecycle

1. **Initialization**: Client sends `initialize` request with protocol version, capabilities, and client info. Server responds with its capabilities and protocol version. Client sends `initialized` notification.
2. **Capability Negotiation**: Server declares support for `tools`, `resources`, `prompts`, `logging`, `completions`. Client declares `roots` and `sampling`.
3. **Operation**: Normal JSON-RPC message exchange respecting negotiated capabilities.
4. **Shutdown**: For stdio, close stdin then SIGTERM then SIGKILL. For HTTP, close connections and optionally DELETE the session endpoint.

Spec: https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle

### Server Primitives

**Tools** (model-controlled): Functions the AI model can invoke. Discovered via `tools/list`, invoked via `tools/call`. Each tool has a `name`, `description`, JSON Schema `inputSchema`, and optional `annotations`. Results contain content arrays (text, image, audio, embedded resources) with an `isError` flag.

**Resources** (application-driven): Data/context identified by URIs (file://, https://, git://, custom). Discovered via `resources/list`, read via `resources/read`. Supports templates (RFC 6570 URI templates), subscriptions for change notifications, and pagination.

**Prompts**: Templated messages and workflows for users. Discovered via `prompts/list`.

**Sampling** (client feature): Allows servers to request LLM completions from the client, enabling recursive agent behaviors.

Tool spec: https://modelcontextprotocol.io/specification/2025-03-26/server/tools
Resource spec: https://modelcontextprotocol.io/specification/2025-03-26/server/resources

---

## 2. MCP in Claude Code

### Configuration Methods

**CLI wizard**:
```bash
claude mcp add --transport http <name> <url>
claude mcp add --transport stdio --env KEY=VALUE <name> -- <command> [args...]
claude mcp add --transport sse <name> <url>              # deprecated
```

**Direct JSON** (via `claude mcp add-json`):
```bash
claude mcp add-json <name> '{"type":"http","url":"https://..."}'
```

**Manual `.mcp.json` files** at various scope levels.

### Scope Levels

| Scope | File Location | Shared with team? |
|-------|--------------|-------------------|
| User | `~/.claude/.mcp.json` | No |
| Project | `.mcp.json` in project root | Yes (commit to git) |
| Local | `.mcp.local.json` in project root | No (gitignored) |

Plugins can also bundle `.mcp.json` at the plugin root.

### Authentication Patterns

- **Bearer tokens / API keys**: `--header "Authorization: Bearer <token>"` or `--env API_KEY=value`
- **OAuth**: Claude Code supports OAuth flows for remote HTTP servers (used by Stripe, GitHub, etc.)
- **Environment variables**: Passed to stdio servers via `--env` flag

### Deferred Tool Loading (ToolSearch)

Launched January 14, 2026. Critical optimization:

- At session start, only tool **names** are loaded into context (not full schemas).
- When Claude needs a tool, it uses the `ToolSearch` meta-tool to search by regex or BM25 semantic matching.
- The API returns 3-5 relevant `tool_reference` blocks that expand into full definitions inline.
- **Impact**: Reduces context from ~77K tokens (50+ MCP tools, traditional) to ~8.7K tokens — a 95% reduction. The ToolSearch tool itself adds only ~500 tokens.
- As of v2.1.69, even built-in tools (Bash, Read, Edit, etc.) are deferred behind ToolSearch.

References:
- https://code.claude.com/docs/en/mcp
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool

---

## 3. Skills in Claude Code

### What is a Skill?

A Skill is a reusable set of instructions packaged as a `SKILL.md` file. Skills extend Claude's behavior without giving it new tools — they shape its approach. The body loads only when invoked, so long reference material costs almost nothing until needed.

Skills follow the open [Agent Skills](https://agentskills.io) standard.

### SKILL.md Structure

```yaml
---
name: my-skill
description: What this skill does
when_to_use: additional trigger phrases
disable-model-invocation: false
user-invocable: true
allowed-tools: Bash(git *) Read
context: fork
agent: Explore
model: opus
effort: high
paths: "*.py,src/**"
---

Markdown instructions here...
$ARGUMENTS placeholder for user input
!`shell command` for dynamic context injection
```

### Discovery and Invocation

| Location | Path | Scope |
|----------|------|-------|
| Enterprise | Managed settings | All org users |
| Personal | `~/.claude/skills/<name>/SKILL.md` | All your projects |
| Project | `.claude/skills/<name>/SKILL.md` | This project only |
| Plugin | `<plugin>/skills/<name>/SKILL.md` | Where plugin is enabled |

**Auto-invocation**: Skill descriptions are always in context (~1,536 char cap each). Claude matches them against conversation context and loads the full content when relevant.

**Manual invocation**: User types `/skill-name [arguments]`.

### Skills vs MCP Tools

| Dimension | Skills | MCP Tools |
|-----------|--------|-----------|
| Purpose | Shape Claude's behavior/approach | Give Claude new capabilities |
| Mechanism | Prompt injection (instructions) | External function calls |
| Discovery | Description matching | ToolSearch (deferred schemas) |
| Execution | Inline or forked subagent | JSON-RPC to MCP server |
| Can call MCP tools? | Yes | N/A |
| Can MCP trigger skills? | No | N/A |

Docs: https://code.claude.com/docs/en/skills

---

## 4. Plugins in Claude Code

### What is a Plugin?

A Plugin is a distributable package that bundles skills, agents, hooks, MCP servers, LSP servers, bin executables, and settings into a single unit with a namespace. Plugin skills use `plugin-name:skill-name` format to prevent conflicts.

### Directory Structure

```
my-plugin/
  .claude-plugin/
    plugin.json          # manifest (required)
  skills/                # skill directories
  commands/              # flat .md skill files
  agents/                # custom agent definitions
  hooks/
    hooks.json           # event handlers
  .mcp.json              # MCP server configs
  .lsp.json              # LSP server configs
  bin/                   # executables added to PATH
  settings.json          # default settings
```

### plugin.json Schema

```json
{
  "name": "my-plugin",
  "description": "What this plugin does",
  "version": "1.0.0",
  "author": { "name": "Your Name" },
  "homepage": "https://...",
  "repository": "https://..."
}
```

### Plugin Marketplace

A marketplace is a Git repository with `.claude-plugin/marketplace.json`. Plugins can be sourced from: relative paths, GitHub repos, git URLs, git subdirectories (sparse clone for monorepos), npm packages.

**Install flow**:
```bash
# Add marketplace
claude plugin marketplace add owner/repo

# Install plugin
claude plugin install my-plugin@marketplace-name

# Update
claude plugin marketplace update
```

**Official marketplace**: `anthropics/claude-plugins-official` — 100+ plugins as of early 2026.

Docs:
- https://code.claude.com/docs/en/plugins
- https://code.claude.com/docs/en/plugin-marketplaces

### Plugins vs Skills vs MCP

| Feature | MCP Server | Skill | Plugin |
|---------|-----------|-------|--------|
| Gives Claude new tools | Yes | No (shapes behavior) | Bundles all |
| External process | Yes | No | May include MCP servers |
| Distributable | As npm/docker/URL | Via git commit | Full marketplace system |
| Namespace | `mcp__server__tool` | `/skill-name` | `/plugin:skill` |
| Install command | `claude mcp add` | Copy SKILL.md | `/plugin install` |

---

## 5. Integration Patterns for Yak Robotics

### How Major Projects Distribute MCP

**Stripe** (https://docs.stripe.com/mcp):
- Remote HTTP server at `https://mcp.stripe.com` with OAuth
- Also available as local `npx -y @stripe/mcp` with API key
- Install: `claude mcp add --transport http stripe https://mcp.stripe.com/`

**GitHub** (https://github.com/github/github-mcp-server):
- Remote HTTP at `https://api.githubcopilot.com/mcp/` with OAuth
- Local Docker image `ghcr.io/github/github-mcp-server` with PAT via stdio
- Configurable toolsets (repos, issues, PRs, actions, etc.)

**Common pattern**: Dual offering — remote HTTP (primary, OAuth) + local stdio (fallback, API key).

### Hosted vs Local MCP Tradeoffs

| Factor | Hosted (HTTP) | Local (stdio) |
|--------|--------------|---------------|
| Setup complexity | One-line URL | Requires npx/docker |
| Multi-user | Yes | Per-machine |
| Authentication | OAuth/API key | Env vars |
| Latency | Network hop | Local, faster |
| Mobile/web clients | Works everywhere | Desktop only |
| Maintenance | Server manages uptime | User manages process |
| State management | Server-side sessions | Per-process |

**For a marketplace with paying customers**: Remote HTTP is strongly recommended.

### Recommended Architecture for Yak Robotics

1. **Primary distribution**: Remote HTTP MCP server (`https://yakrover-marketplace.fly.dev/mcp`) with API key auth. Works with Claude, Cursor, ChatGPT, OpenAI agents, LangChain — any MCP client.

2. **Enhanced Claude Code experience**: Plugin that bundles MCP server config + Skills (guided workflows like `/yak:run-auction`, `/yak:process-rfp`, `/yak:onboard-operator`) + hooks for validation.

3. **Deferred loading handles scale**: With ToolSearch, 39 tools add minimal context overhead (~500 tokens for ToolSearch + tool names, vs ~30K+ if all schemas loaded).

4. **Cross-platform**: Same MCP server works everywhere. Skills and Plugins are Claude Code-specific value-adds.

### Ideal Onboarding Flow

**Simplest (any MCP client)**:
```bash
claude mcp add --transport http yakrover https://yakrover-marketplace.fly.dev/mcp
```

**Full experience (Claude Code)**:
```bash
claude plugin marketplace add YakRoboticsGarage/yakrover-marketplace
claude plugin install yakrover
```

---

## 6. Cross-Agent Compatibility

### MCP Adoption (April 2026)

- **97 million** monthly SDK downloads across TypeScript, Python, Java, Kotlin, C#, Swift
- **500+** public MCP servers indexed in community directories
- **4,000+** servers listed in largest registries

### Client Support

| Client | MCP Support | Transport |
|--------|------------|-----------|
| Claude Code | Full | stdio, HTTP, SSE |
| Claude Desktop | Full | stdio, HTTP, SSE |
| Cursor | Full | stdio, HTTP |
| Windsurf | Full | stdio, HTTP |
| VS Code (Copilot) | Full | stdio, HTTP |
| ChatGPT | Full | HTTP (OAuth required) |
| OpenAI Agents SDK | Full | stdio, HTTP, SSE |
| OpenAI Codex | Full | MCP shortcuts |
| LangChain | Via adapter | All transports |
| CrewAI | Via adapter | stdio |

### MCP vs Function Calling vs OpenAPI

- **MCP**: Write the tool once, works in any MCP client. Standardized discovery, stateful sessions, streaming. Best for: portable integrations, multi-tool servers.
- **Function calling** (OpenAI/Anthropic native): Tightly coupled to a single API call. Every schema sent in every request. Best for: simple, single-provider apps.
- **OpenAPI/REST**: HTTP endpoints without AI-specific semantics. Requires custom wrapping per agent framework.

---

## Key References

- [MCP Specification](https://modelcontextprotocol.io/specification/2025-03-26)
- [MCP Transports](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)
- [MCP Lifecycle](https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle)
- [Claude Code MCP Docs](https://code.claude.com/docs/en/mcp)
- [Claude Code Skills Docs](https://code.claude.com/docs/en/skills)
- [Claude Code Plugins Docs](https://code.claude.com/docs/en/plugins)
- [Claude Code Plugin Marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
- [Tool Search Tool API Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool)
- [Stripe MCP](https://docs.stripe.com/mcp)
- [GitHub MCP Server](https://github.com/github/github-mcp-server)
- [OpenAI Agents SDK MCP](https://openai.github.io/openai-agents-python/mcp/)
- [MCP Authorization Tutorial](https://modelcontextprotocol.io/docs/tutorials/security/authorization)
- [MCP vs Function Calling](https://www.descope.com/blog/post/mcp-vs-function-calling)
