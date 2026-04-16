# Assessment: "Link Your Agent" Flow

**Date:** 2026-03-27
**Trigger:** Founder feedback v4, item 1 — replace static agent compatibility text with an actionable onboarding link.

---

## Who Clicks This?

A developer or power user who wants their AI agent (Claude Code, Claude Desktop, ChatGPT, custom MCP client) to call marketplace tools programmatically. This is NOT the Sarah persona — she uses the web UI. This user already knows what MCP is, has an agent running, and wants the `.mcp.json` snippet or API key to wire it up.

## The Flow (5 Steps)

**Step 1 — Choose Your Agent**
Modal or slide-over panel. Four cards: Claude Code, Claude Desktop, ChatGPT, Custom MCP Client. Each card has a logo and one-liner ("Paste a config block" vs "One-click install"). Selection determines what Step 3 shows.

**Step 2 — Authenticate**
"Generate API Key" button. User enters a label (e.g. "my-laptop-claude") and clicks generate. System returns a bearer token and shows it once with a copy button. Warning: "This won't be shown again." The token scopes to `task:post`, `task:read`, `wallet:read`, `wallet:fund` (matching the OAuth scopes in the design sprint doc).

**Step 3 — Configure**
Based on Step 1 selection:
- **Claude Code / Claude Desktop:** Show the `.mcp.json` snippet pre-filled with their new token and the SSE endpoint (`/mcp/sse`). Copy button + "Open Claude settings" deep link where supported.
- **ChatGPT:** Show the plugin manifest URL and auth header to paste into the GPT builder.
- **Custom MCP Client:** Show raw endpoint URLs (`/mcp/sse`, `/mcp/`) and a curl example for the Streamable HTTP transport.

**Step 4 — Test Connection**
"Test Connection" button. Sends a lightweight ping to the MCP endpoint using the generated token. Shows green checkmark on success, red error with troubleshooting hint on failure. For the demo, this always succeeds after a brief spinner.

**Step 5 — Done**
Confirmation screen listing the 4 available tools: `auction_post_task`, `auction_quick_hire`, `auction_get_status`, `auction_fund_wallet`. Each with a one-line description. Link to API docs. "Try it: ask your agent to post a task" prompt.

## Mockable Now vs Needs Backend

| Part | Mockable in demo? | Notes |
|---|---|---|
| Step 1 (agent picker) | Yes | Pure UI |
| Step 2 (token generation) | Yes | Generate a fake `ym_live_xxxx` token client-side |
| Step 3 (config snippet) | Yes | Template string with fake token injected |
| Step 4 (test connection) | Yes | Fake 1.5s spinner, always succeeds |
| Step 5 (tool list) | Yes | Static content from existing tool definitions |
| Real OAuth / token storage | No | Needs backend auth service |
| Real MCP endpoint ping | No | Needs running MCP server |

**Everything in the flow is mockable.** No backend work needed for the demo.

## Recommended Mock Implementation

Replace the `.agent-line` text in `demo/index.html` with:

```
Or <a href="#" onclick="openAgentLinkFlow()">click here to link your Agent</a>
```

On click, open a modal that walks through Steps 1-5 as tabbed panels within a single overlay. All data is client-side. The generated "token" is a random string. The config snippet is a template literal. The test always passes. Total new code: ~150 lines of HTML/CSS/JS added to the existing demo file, consistent with the current single-file demo architecture.

Priority: implement after items 2 (feed page) and 5 (robot grid) since those affect the main user path. This flow targets a secondary persona.
