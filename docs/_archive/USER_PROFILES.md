# User Profiles: Robot Task Auction Marketplace

> **Version:** 0.1 | **Date:** 2026-03-27
>
> Centralized reference for all platform personas. Profiles are extracted from the user journey documents
> (`USER_JOURNEY_MARKETPLACE_v01.md`, `USER_JOURNEY_PRIVATE_v01.md`, `USER_JOURNEY_LUNAR_v01.md`,
> `research/RESEARCH_BUY_A_ROBOT_STORY.md`) and the frontend design sprint (`FRONTEND_DESIGN_SPRINT.md`).

---

## Primary Personas

### Sarah -- Facilities Manager (Enterprise Buyer)
**Type:** Buyer
**Story:** Marketplace
**First appears:** v0.1
**Journey:** Sarah manages three warehouses for a mid-size logistics company in Finland. She uses an AI assistant daily for scheduling, reports, and vendor management. When she needs a temperature and humidity reading from Warehouse Bay 3 for an HVAC maintenance report, she types a single sentence to her assistant. The platform posts the task to an auction, two robots compete, the closest one wins at $0.35, and Sarah has her reading in 42 seconds. She copies the numbers into her report and moves on. She never sees the auction, the bidding, or the payment settlement.
**Needs:**
- Sub-minute sensor readings from her warehouses on demand
- Plain-English interface through her existing AI assistant -- no new tools to learn
- Transparent, predictable pricing with one line item on her corporate card statement
- Automatic failure recovery when a robot goes offline mid-task
- Per-task cost breakdown accessible on the platform dashboard for expense reporting
**Pain points:**
- Cannot justify IT overhead for a tool she uses a few times per week
- Has no interest in blockchain, crypto wallets, or protocol details
- Needs instant fallback when robots fail -- cannot wait for manual reassignment
**Success metric:** Time from request to verified sensor reading (target: under 60 seconds)

---

### Diane -- Program Manager (Private Buyer)
**Type:** Buyer
**Story:** Privacy
**First appears:** v0.1
**Journey:** Diane manages physical security inspections across three classified facilities for a defense contractor in Helsinki. She holds a Finnish security clearance (KATAKRI level III). When she needs a structural vibration reading from a classified corridor, she asks her AI assistant in the same way Sarah does. The difference is invisible to her: her task spec is encrypted before it leaves her device, robots bid on a coarse capability vector without seeing the full spec, and only the winning robot receives the decrypted details. The reading arrives in 55 seconds -- 13 seconds slower than a standard task due to TEE attestation, BBS+ credential verification, and zero-knowledge proof generation. Diane never sees any of this overhead.
**Needs:**
- Encrypted task specs that never expose classified inspection targets to the platform, losing bidders, or external observers
- Identical workflow to a standard marketplace buyer -- privacy must not add UX friction
- Internal auditability: her CFO can decrypt task metadata (cost, time, facility) without seeing classified spec contents
- Regulatory compliance: platform retains data accessible on lawful request via escrow key
- Clear options when privacy infrastructure fails (retry, downgrade, or cancel)
**Pain points:**
- Every tool she uses must pass her company's security review board
- Cannot use any service that exposes what she inspects, where, or why
- TEE attestation failures are unpredictable and block time-sensitive inspections
**Success metric:** Zero information leakage beyond the public capability vector, verified by audit

---

### Kenji -- Project Coordinator (Lunar Buyer)
**Type:** Buyer
**Story:** Lunar
**First appears:** v0.1
**Journey:** Kenji coordinates construction projects at the lunar south pole for Tsukimi Construction, contracted by JAXA and NASA. He works from Tsukuba, Japan, and manages three concurrent projects at Shackleton Crater rim. When he needs a regolith density survey at a grid sector, he asks his AI assistant. The platform transmits the task as a DTN bundle through Lunar Pathfinder, rovers 384,400 km away evaluate and bid locally on RAD750-class processors, and the winning rover executes a 25-minute autonomous survey. Kenji gets a density map in about 4 minutes. When lunar night forces a rover to abort mid-task, the platform delivers partial data at a pro-rated price and queues the remainder for the next lunar day.
**Needs:**
- Reliable task execution across 3-second light-delay communication links
- Autonomous rover bidding and execution with no human-in-the-loop on the Moon
- Graceful handling of lunar-specific failures: thermal aborts, lunar night, power constraints
- Partial delivery with pro-rated payment when tasks cannot be completed in full
- Queued tasks with configurable TTL that auto-execute when rovers return to service
- Per-project budget tracking across multiple concurrent construction sites
**Pain points:**
- Communication windows are intermittent and latency makes real-time control impossible
- Rover assets cost $8M+ each -- task scoring must prioritize safety over lowest price
- Lunar night shuts down all surface operations for ~14 Earth days
**Success metric:** Survey data delivered within the current lunar day at the contracted resolution

---

### Alex -- Independent Robot Operator
**Type:** Operator
**Story:** Supply
**First appears:** v0.1 (research)
**Journey:** Alex is a 28-year-old operations technician at a coworking space in Helsinki. He sees the marketplace dashboard showing live task activity and clicks "Become an Operator." The platform recommends starter hardware by use case. Alex orders an ESP32-based sensor rover for EUR 60, assembles it in under two hours, and onboards it via the CLI in 30 minutes -- firmware flash, WiFi config, ERC-8004 registration, sensor calibration, and pricing rules. He deposits EUR 10 as an operator bond and marks the robot as available. Within hours, the robot wins its first auction and earns EUR 0.35. After two months and EUR 120 in revenue, Alex buys a second robot.
**Needs:**
- Sub-hour onboarding from unboxing to first auction win
- One-command firmware flash with no toolchain installation required
- Demand heatmap showing where tasks are posted but no robots can serve them
- Dashboard showing revenue, task history, robot health, and payout history
- Gas-sponsored ERC-8004 registration so he never touches crypto during setup
**Pain points:**
- Revenue depends entirely on demand density -- a robot in an empty building earns nothing
- Price compression if too many operators deploy in the same area
- Sensor calibration drift can lead to disputed tasks and reputation penalties
**Success metric:** Breakeven on hardware cost within 30 days (requires 10+ tasks/day at moderate pricing)

---

## Supporting Personas

### Sarah's IT Admin -- Enterprise Administrator
**Type:** Admin
**Story:** Marketplace
**First appears:** v0.1
**Journey:** The IT admin performs the one-time, five-minute setup that enables Sarah's entire experience. They visit the platform dashboard, link the corporate Amex card, purchase a $25 credit bundle (one line item on the company statement), and paste an API key into Sarah's AI assistant configuration. They set spending limits: up to $50 per task, auto-approve anything under $5. From then on, the admin monitors the per-task cost breakdown on the dashboard and tops up credit bundles when the balance runs low.
**Needs:**
- Single dashboard for account setup, payment linking, and API key management
- Configurable per-task and per-user spending limits with auto-approval thresholds
- Clear expense reporting: one credit-card line item, granular per-task breakdown on dashboard
- Ability to revoke API keys and freeze spending instantly
**Pain points:**
- Must justify every new SaaS vendor to procurement; needs a clean, auditable paper trail
- Cannot afford to debug integration issues -- setup must work on the first attempt
**Success metric:** Setup completed in under 10 minutes with no follow-up support tickets

---

### Diane's Security Officer -- Privacy Setup
**Type:** Admin
**Story:** Privacy
**First appears:** v0.1
**Journey:** The security officer performs the one-time, 15-minute privacy setup for Diane's account. They link the corporate procurement card, purchase a EUR 200 credit bundle, and enable "Private Tasks" for Diane's account. This generates a viewer key pair: the CFO receives a viewer key for internal audit, while the platform holds an escrow key in a hardware security module accessible only under documented legal process. The officer pastes an API key into Diane's assistant and configures default encryption for all submitted task specs.
**Needs:**
- Organization-level public key upload for encrypted task storage
- Viewer key generation and distribution to authorized internal auditors
- Assurance that the platform escrow key is stored in an HSM with documented access controls
- Ability to enable or disable private-task mode per user account
**Pain points:**
- Must satisfy KATAKRI level III requirements -- no shortcuts on key management
- Needs cryptographic proof that the privacy infrastructure works as claimed (TEE attestation logs)
**Success metric:** Privacy configuration passes the company's security review board on first submission

---

### Diane's CFO -- Internal Auditor
**Type:** Auditor
**Story:** Privacy
**First appears:** v0.1
**Journey:** The CFO holds a viewer key that decrypts per-task metadata (cost, time, robot, facility) for internal audit purposes. They do not see classified task spec contents, which require Diane's personal key. At the end of each reporting period, the CFO reviews aggregate spend by facility, cost categorization, and per-task breakdowns to ensure procurement compliance. The viewer key architecture gives them full financial visibility without exposing sensitive operational details.
**Needs:**
- Viewer key that decrypts task metadata (cost, timestamp, robot assignment, facility) but not classified spec contents
- Aggregate spend reports by facility, project, and time period
- Exportable audit logs compatible with enterprise procurement systems
**Pain points:**
- Cannot perform audit duties if the viewer key architecture leaks classified information
- Needs assurance that the same data is available for regulatory requests without additional tooling
**Success metric:** Complete financial audit trail for all private tasks without accessing any classified content

---

### Kenji's Operations Lead -- Project Budget Manager
**Type:** Admin
**Story:** Lunar
**First appears:** v0.1
**Journey:** The ops lead at Tsukimi Construction performs the one-time, 30-minute setup for lunar operations. They link the corporate procurement account, fund the project wallet with $50,000 in USDC credits via wire transfer, and configure per-project spending limits and task-type authorizations. They review the rover fleet registry -- five rovers from two operators at Shackleton rim -- and connect Kenji's AI assistant with an API key. The ops lead sets Kenji's auto-approval limit at $5,000 per task. Ongoing, they monitor a dashboard showing per-task costs, rover assignments, and project budget burn across all three active projects.
**Needs:**
- Per-project budget allocation and spend tracking across multiple concurrent sites
- Task-type authorization controls (which task categories each coordinator can auto-approve)
- Visibility into rover fleet status: health, power levels, dust accumulation, thermal status, lunar day availability
- Settlement batch monitoring: USDC payouts posted every 6 hours during communication windows
**Pain points:**
- Individual tasks cost thousands of dollars -- misauthorized spending has real financial impact
- Must reconcile platform spend against JAXA/NASA contract milestones
**Success metric:** Project spend stays within authorized budget with full per-task traceability to contract deliverables

---

### Fleet Operator -- Commercial Robot Fleet Owner
**Type:** Operator
**Story:** Marketplace
**First appears:** v0.1
**Journey:** The fleet operator (e.g., YakRobotics) manages multiple robots registered on the platform across one or more facilities. Setup is a one-time process: register each robot with its capabilities and pricing rules, connect a bank account for payouts via Stripe Connect Express or a USDC wallet. Ongoing, robots bid and execute tasks autonomously based on pre-configured pricing logic. The operator monitors a dashboard showing completed tasks, revenue per robot, fleet health, and payout history. They never manually accept a task or submit a bid. Their job is to keep robots charged, maintained, and online.
**Needs:**
- Multi-robot management dashboard: per-robot revenue, health, uptime, and task history
- Configurable pricing rules per robot: base price, distance multiplier, battery threshold, sensor-type premiums
- Automatic payout after each successful delivery to connected bank account or USDC wallet
- Alert rules for robot offline, low battery, sensor drift, and failed tasks
**Pain points:**
- Robot downtime directly reduces revenue -- needs proactive health monitoring
- Price competition from independent operators (like Alex) could compress margins
- For lunar operators: batched settlement and intermittent communication add operational complexity
**Success metric:** Fleet utilization rate above 50% during operating hours with sub-1% task failure rate

---

### Claude (AI Agent) -- Autonomous Buyer Agent
**Type:** Agent
**Story:** Marketplace | Privacy | Lunar
**First appears:** v0.1
**Journey:** Claude acts as the intermediary between human buyers and the auction platform. When Sarah types "check the temperature in Bay 3," Claude translates her natural-language request into a structured task specification (sensor requirements, accuracy thresholds, data format, budget, deadline), posts it to the auction via `auction_quick_hire`, monitors the bidding in real time, verifies the delivered data against the original requirements, confirms delivery, and presents the result in plain language. For Diane's private tasks, Claude encrypts the spec before posting and adds the `privacy: true` flag. For Kenji's lunar tasks, Claude adjusts bid windows for DTN latency and monitors checkpoint bundles during execution. Claude can also be discovered programmatically by other agents via `/.well-known/mcp.json` and OAuth.
**Needs:**
- MCP tool access: `auction_post_task`, `auction_quick_hire`, `auction_get_status`, `auction_confirm_delivery`, `auction_fund_wallet`
- OAuth token with scopes: `task:post`, `task:read`, `wallet:read`, `wallet:fund`
- Structured task spec schema for translating natural language to formal requirements
- SSE subscription for real-time auction updates (bids, winner, execution progress, delivery)
- Ability to auto-approve tasks within configured spending limits without human confirmation
**Pain points:**
- Must handle ambiguous user requests gracefully (ask for clarification, not guess)
- Must verify delivery data is plausible before confirming payment
- Must explain failures, retries, and cost changes in plain language without exposing protocol details
**Success metric:** End-to-end task completion without human intervention for requests within auto-approval limits

---

### Anonymous Web Visitor -- Pre-Authentication Explorer
**Type:** Buyer (potential)
**Story:** Marketplace (frontend)
**First appears:** v1.5 (frontend design sprint)
**Journey:** The visitor searches "robot sensor reading service" and lands on the marketplace homepage. Without logging in or creating an account, they see a live ticker of recent robot activity, a list of available robots with capabilities and pricing, and a search bar. They type what they need -- "temperature reading in my warehouse" -- and the site immediately shows a structured preview with estimated cost and time. Only when they want to start an actual auction does the site ask them to connect Claude (OAuth) and then connect payment (Stripe or USDC). Their anonymous intent is captured in the backend for demand analytics regardless of whether they convert.
**Needs:**
- Zero-friction exploration: no login wall, no sign-up form, no paywall before seeing what the platform offers
- Live social proof: real robots completing real tasks in the feed
- Estimated cost and time for their specific request before committing any credentials
- Progressive disclosure: authenticate only when ready to act, not when ready to browse
**Pain points:**
- Will bounce immediately if the first screen demands registration
- Needs to trust that the platform is real and active before entering payment details
- May not have an AI assistant configured -- the web path must work independently
**Success metric:** Conversion from anonymous intent capture to first completed task

---

### Developer/Integrator -- API/MCP Consumer
**Type:** Buyer | Operator
**Story:** Marketplace (frontend)
**First appears:** v1.5 (frontend design sprint)
**Journey:** The developer discovers the marketplace through its public API surface. They fetch `/.well-known/mcp.json` to find the MCP endpoint, tool list, and auth requirements. They read the OpenAPI spec at `/api/openapi.json` for REST integration. They authenticate via OAuth, obtain scoped tokens, and integrate the marketplace into their own application -- whether that is a custom AI agent, a facility management system, or an operator dashboard. They subscribe to the SSE endpoint for real-time auction updates and use structured JSON responses for programmatic consumption.
**Needs:**
- Well-documented MCP endpoint with tool schemas and auth flow
- OpenAPI spec for REST consumers who do not use MCP
- OAuth with granular scopes (task:post, task:read, wallet:read, wallet:fund)
- SSE endpoints for real-time event streams (auction updates, robot status, feed)
- Sandbox/test mode with mock robots for integration testing without real payments
**Pain points:**
- Incomplete or outdated API documentation blocks integration
- Breaking schema changes without versioning
- No test environment means every integration attempt costs real money
**Success metric:** Time from API discovery to first successful programmatic task completion (target: under 1 hour)

---

### Platform Administrator -- Marketplace Operator
**Type:** Admin
**Story:** Marketplace | Privacy | Lunar
**First appears:** v0.1 (implicit)
**Journey:** The platform administrator operates the marketplace infrastructure itself -- the auction engine, payment settlement, robot registry, reputation system, and privacy infrastructure. During the seed phase, they manage zero-fee operations to incentivize supply growth. They monitor system health: auction throughput, settlement success rates, TEE attestation status, DTN relay connectivity for lunar operations, and robot registry integrity. They handle edge cases: disputed tasks, ghost operators who register but never come online, sensor quality complaints, and regulatory data requests requiring the platform escrow key.
**Needs:**
- System-wide dashboard: auction volume, settlement rates, active robots, task failure rates, revenue
- Robot registry management: auto-delist robots offline for 24+ hours, enforce heartbeat requirements
- Dispute resolution tooling: review task data, adjudicate buyer-operator conflicts, issue refunds
- Privacy infrastructure monitoring: TEE attestation success rates, escrow key access audit log
- Lunar operations monitoring: DTN relay status, settlement batch processing, rover fleet health
- Regulatory response workflow: process lawful escrow key access requests with full audit trail
**Pain points:**
- Seed phase economics mean operating at a loss -- must track path to sustainable unit economics
- Privacy infrastructure failures (TEE attestation) erode buyer trust
- Lunar communication intermittency makes real-time monitoring impossible -- must rely on batched telemetry
**Success metric:** Platform uptime above 99.9% with sub-10-second auction completion for Earth-side tasks

---

## Persona Summary

| # | Name | Type | Story | Key Action |
|---|------|------|-------|------------|
| 1 | Sarah | Buyer | Marketplace | Hires robots for warehouse sensor readings via AI assistant |
| 2 | Diane | Buyer | Privacy | Hires robots for classified facility inspections with encrypted specs |
| 3 | Kenji | Buyer | Lunar | Hires lunar rovers for regolith surveys across DTN links |
| 4 | Alex | Operator | Supply | Buys a robot, onboards it, and earns revenue from marketplace tasks |
| 5 | Sarah's IT Admin | Admin | Marketplace | Sets up corporate account, payment, and API keys |
| 6 | Diane's Security Officer | Admin | Privacy | Configures encryption keys, viewer keys, and private-task mode |
| 7 | Diane's CFO | Auditor | Privacy | Audits private task spend using viewer key without seeing classified content |
| 8 | Kenji's Ops Lead | Admin | Lunar | Manages project budgets, rover fleet visibility, and spending limits |
| 9 | Fleet Operator | Operator | Marketplace | Manages commercial robot fleet, pricing, and payouts |
| 10 | Claude (AI Agent) | Agent | All | Translates human intent to structured tasks, runs auctions, verifies delivery |
| 11 | Anonymous Visitor | Buyer (potential) | Marketplace | Explores the platform and captures intent before authenticating |
| 12 | Developer/Integrator | Buyer/Operator | Marketplace | Integrates the marketplace via MCP or REST API |
| 13 | Platform Admin | Admin | All | Operates marketplace infrastructure, disputes, compliance, monitoring |
