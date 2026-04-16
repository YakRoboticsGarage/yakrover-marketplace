# Plan: Robot User Journey — Operator-to-Execution Path

**Date:** 2026-04-09
**Status:** Plan — next session
**Depends on:** v1.4 operator registration (complete)

---

## Objective

Map the full robot user journey from registration through task execution. Understand how:
1. A registered robot's MCP tools are discovered and connected
2. The marketplace routes tasks to the robot's physical capabilities
3. The buyer's execution phase triggers actual robot actions (move, sense, deliver)
4. Payment settles after verified delivery

---

## Key Questions

### 1. MCP Tool Discovery
- How does the marketplace know what tools a robot has? (MCP endpoint in IPFS agent card → `mcpTools` array)
- How does the demo currently execute a Tumbller `tumbller_move` or `tumbller_get_temperature_humidity`?
- Is the tool execution proxied through the marketplace MCP server or direct to the robot's MCP endpoint?
- What happens when a robot's MCP server is offline?

### 2. Robot Execution Flow
- Current flow: marketplace MCP server → Cloudflare Worker (`/api/demo`) → Claude tool_use loop → calls `auction_execute` → which calls what?
- How does the FakeRover simulator execute? (`MockRobot.execute()` → `http://localhost:8080/sensor/ht`)
- How does the Tumbller execute? (`MCPRobotAdapter.execute()` → robot's MCP endpoint → `tumbller_move`)
- What's the gap between "robot wins auction" and "robot physically does the task"?

### 3. Operator Journey Alignment
- After registration, how does the operator know a task is available?
- How does the operator's robot bid? (automated via `bid_engine()` or manual?)
- Can the operator watch execution in real-time?
- How does the operator confirm delivery and get paid?

### 4. Buyer Needs
- Does the buyer see which physical robot is executing?
- Does the buyer see real-time execution progress?
- How does the buyer verify the delivery is from the robot that won?
- What happens if the robot fails mid-execution?

---

## Investigation Plan

### Phase 1: Trace the execution path
1. Read `MCPRobotAdapter` in `auction/mcp_robot_adapter.py` — how does it call the robot's MCP tools?
2. Read `auction/engine.py` `execute()` method — what does it do with the adapter?
3. Read `mcp_server.py` fleet discovery — how are `MCPRobotAdapter` instances created from on-chain data?
4. Read `chatbot/src/index.js` `/api/demo` handler — how does Claude's tool_use loop trigger execution?

### Phase 2: Map the Tumbller flow end-to-end
1. Tumbller registered on Sepolia with MCP endpoint
2. Fleet discovery finds it via subgraph
3. Task posted → Tumbller bids → wins auction
4. `auction_execute` called → what happens to the Tumbller?
5. Tumbller moves, reads temperature → delivery payload returned
6. Buyer approves → payment settles

### Phase 3: Identify gaps for registered operators
1. Newly registered robots (via the form) don't have a running MCP server
2. They're `RuntimeRegisteredRobot` in-memory — mock execution only
3. What would it take for a real operator to run their own robot MCP server?
4. How does the robot MCP server connect to the marketplace?

### Phase 4: Design the operator execution experience
1. Operator registers robot → gets MCP connection command
2. Operator runs their robot's MCP server locally
3. Marketplace discovers the robot's MCP endpoint from IPFS agent card
4. Task posted → robot bids via its own `bid_engine` → wins
5. Marketplace calls robot's MCP tools for execution
6. Robot returns delivery payload → marketplace QA validates → buyer approves → payment

---

## Privacy Note

`bid_pct` (bid aggressiveness) is competitive intelligence — stored only in the in-memory fleet robot, never written on-chain or to IPFS. Operators cannot see each other's pricing strategy.

---

## Dependencies

- `yakrover-8004-mcp` — the robot MCP server implementation
- `tumbller-8004-mcp` — Tumbller-specific MCP tools
- `auction/mcp_robot_adapter.py` — bridges marketplace to robot MCP
- `auction/mock_fleet.py` — `RuntimeRegisteredRobot` for form-registered robots
- ERC-8004 agent card IPFS structure — `services[].endpoint`, `mcpTools[]`
