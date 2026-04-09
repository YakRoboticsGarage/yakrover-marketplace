# Demo UI Code Review Plan

**Date:** 2026-04-09
**Scope:** `docs/mcp_demo_5/index.html` (single-file demo), `mcp_server.py` (backend), `auction/mcp_tools.py` (registration tool)
**Goal:** End-to-end review of every user journey, error path, code quality, and deployment readiness

---

## Review Agents

### Agent 1 — Buyer Journey Review
Walk through every buyer path: Setup > Auction > Dispatch (3 payment methods) > Execute > Done.
Check: form validation, error states, loading states, progress feedback, payment edge cases, mobile responsiveness.

### Agent 2 — Operator Registration Journey Review  
Walk through every registration path: Mode A (platform signs), Mode B (own wallet), Mode C (Claude Code).
Check: 3-step flow (Profile > Equipment > Payment), form validation, chain selection, progress display, confirmation card accuracy, partial failure display, sidebar update.

### Agent 3 — Frontend Code Quality
Review HTML/CSS/JS patterns: accessibility (a11y), semantic HTML, CSS consistency, JS error handling, memory leaks, event listener cleanup, XSS vectors, performance.

### Agent 4 — Backend Code Quality
Review `mcp_tools.py` registration tool and `mcp_server.py` fleet management: error handling, thread safety, input validation, SDK failure modes, idempotency.

### Agent 5 — Deployment & CI/CD Review
Review: Dockerfile, fly.toml, here.now publish flow, worker deployment, test coverage for new code, environment variable management, secret handling.

---

## Evaluation Tree

```
Demo Review
├── Buyer Journey
│   ├── Setup Phase
│   │   ├── Form defaults and validation
│   │   ├── RFP textarea behavior
│   │   ├── Site info fields
│   │   └── Mobile CTA visibility
│   ├── Auction Phase
│   │   ├── Progress display during Claude orchestration
│   │   ├── Winner card rendering
│   │   ├── "Proceed to Dispatch" button placement
│   │   ├── Error: MCP server unreachable
│   │   ├── Error: No robots available
│   │   └── Back navigation
│   ├── Dispatch Phase (3 payment methods)
│   │   ├── Card payment (Stripe Elements)
│   │   ├── ACH bank transfer
│   │   ├── USDC stablecoin (EIP-3009)
│   │   ├── Error: payment declined
│   │   ├── Error: wallet not connected (USDC)
│   │   └── Test vs Production mode behavior
│   ├── Execute Phase
│   │   ├── Commitment status card
│   │   ├── Delivery result + QA badge
│   │   ├── "Release Payment" button
│   │   └── Error: delivery rejected
│   └── Done Phase
│       ├── Receipt card (per payment method)
│       ├── Feedback form (star rating)
│       ├── Reset demo flow
│       └── Data reveal section
│
├── Operator Registration Journey
│   ├── Entry Points
│   │   ├── Sidebar "Register Robot" button
│   │   ├── Mobile "Register Robot" button
│   │   └── Breadcrumb switching (buyer ↔ registration)
│   ├── Step 1: Profile
│   │   ├── FakeRover prefix enforcement
│   │   ├── Admin passcode bypass
│   │   ├── Required field validation
│   │   └── Navigation to Step 2
│   ├── Step 2: Equipment
│   │   ├── Multi-select sensor checkboxes
│   │   ├── "Other" sensor with text input
│   │   ├── Model dropdown + "Other" option
│   │   ├── Certification file uploads
│   │   └── Navigation (back/forward)
│   ├── Step 3: Payment & Bidding
│   │   ├── Bid aggressiveness slider
│   │   ├── Payment channel checkboxes
│   │   ├── Stripe/USDC destination fields
│   │   ├── USDC wallet pre-fill from connected wallet
│   │   ├── Chain selection (advanced)
│   │   └── Register & Activate button
│   ├── Registration Modes
│   │   ├── Mode A: Platform signs
│   │   ├── Mode B: Connect wallet (MetaMask)
│   │   ├── Mode C: Claude Code / MCP
│   │   └── Mode selector interaction
│   ├── Progress & Confirmation
│   │   ├── Per-chain progress lines
│   │   ├── On-chain verification query
│   │   ├── Partial success display
│   │   ├── All-chains-failed error display
│   │   ├── Confirmation card accuracy
│   │   └── Activity feed items
│   └── Post-Registration
│       ├── Sidebar robot list update
│       ├── "Return to Demo" flow
│       ├── Fleet filter interaction
│       └── Registered robot appears in auction bids
│
├── Admin Journey
│   ├── Fleet Configuration
│   │   ├── "Demo fleet only" toggle behavior
│   │   ├── "Hide FakeRovers" toggle behavior
│   │   ├── Mutual exclusion logic between toggles
│   │   ├── Server-side fleet-mode sync (/api/fleet-mode)
│   │   ├── Sidebar robot list filtering accuracy
│   │   └── Auction bidding fleet matches filter state
│   ├── Environment Settings
│   │   ├── Production vs Test mode switch
│   │   ├── Test credential hints (card, ACH, USDC)
│   │   ├── Tunnel URL configuration (hidden input)
│   │   └── Environment auto-detection from robot chain
│   ├── Admin Passcode
│   │   ├── "robotadmin" passcode entry
│   │   ├── FakeRover prefix bypass activation
│   │   ├── Name field hint update on passcode entry
│   │   ├── Passcode clearing / mode reset
│   │   └── Security: client-side only, no server validation
│   ├── Monitoring
│   │   ├── Activity feed completeness (all actions logged)
│   │   ├── Active Operators panel accuracy
│   │   ├── Robot discovery status display
│   │   ├── Health endpoint (/health) data
│   │   └── Fleet size tracking after registration
│   └── Edge Cases
│       ├── Switching filters mid-auction
│       ├── Registering robot while auction is running
│       ├── Multiple registrations in same session
│       └── Server restart: registered robots lost vs. re-discovered
│
├── Frontend Code Quality
│   ├── Accessibility
│   │   ├── Keyboard navigation
│   │   ├── Screen reader labels (aria)
│   │   ├── Focus management on phase transitions
│   │   ├── Color contrast ratios
│   │   └── Form label associations
│   ├── HTML/CSS
│   │   ├── Semantic elements vs divs
│   │   ├── CSS variable consistency
│   │   ├── Inline styles vs classes (proliferation)
│   │   ├── Mobile responsiveness gaps
│   │   └── Print styles
│   ├── JavaScript
│   │   ├── Global variable pollution
│   │   ├── Error handling completeness
│   │   ├── Memory leaks (event listeners, intervals)
│   │   ├── XSS: escapeHtml coverage
│   │   ├── Race conditions (concurrent submissions)
│   │   ├── AbortController usage
│   │   └── Promise chain error propagation
│   └── Performance
│       ├── Bundle size (single file)
│       ├── External dependency count
│       ├── Render-blocking resources
│       └── Unnecessary re-renders
│
├── Backend Code Quality
│   ├── auction_register_robot_onchain
│   │   ├── Input validation
│   │   ├── Thread safety (asyncio.to_thread)
│   │   ├── SDK exception handling completeness
│   │   ├── Idempotency (re-registration)
│   │   ├── Fleet mutation atomicity
│   │   └── Return value consistency
│   ├── Fleet Management
│   │   ├── Discovery race conditions
│   │   ├── Fleet swap atomicity
│   │   ├── RuntimeRegisteredRobot persistence
│   │   └── Filter flag consistency
│   └── REST API
│       ├── CORS configuration
│       ├── Error response format consistency
│       ├── Timeout handling
│       └── Rate limiting
│
└── Deployment
    ├── Dockerfile
    │   ├── Layer caching efficiency
    │   ├── Security (non-root user)
    │   └── Size optimization
    ├── CI/CD
    │   ├── Test coverage for registration code
    │   ├── Lint passing
    │   └── Type check passing
    ├── Secrets Management
    │   ├── SIGNER_PVT_KEY handling
    │   ├── PINATA_JWT handling
    │   └── No secrets in client code
    └── Publish Flow
        ├── here.now publish script
        ├── Fly.io deploy command
        └── Worker deploy script
```
