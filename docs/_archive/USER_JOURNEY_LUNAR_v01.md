# User Journey: Lunar Robot Marketplace (v0.1 -- The Happy Path)

> **Version:** 0.1 | **Date:** 2026-03-26 | **Story:** Lunar
>
> This is the lunar user journey document for the marketplace story.
> It describes Kenji's experience hiring a rover for a regolith density survey at a lunar south pole site.
> For the foundational Earth-side journey, see `USER_JOURNEY_MARKETPLACE_v01.md`.
> For the private fleet journey, see `USER_JOURNEY_PRIVATE_v01.md`.
> For technical details, see `DECISIONS.md`, `SCOPE.md`, and `research/RESEARCH_SYNTHESIS_LUNAR.md`.

---

## Meet Kenji

Kenji is a project coordinator at Tsukimi Construction, a mid-size Artemis-era company contracted by JAXA and NASA to prepare building sites at the lunar south pole. He works from an office in Tsukuba, Japan. He manages three concurrent construction projects at the Shackleton Crater rim. He uses an AI assistant daily for scheduling, progress tracking, and subcontractor management. He has a corporate procurement account with pre-approved spending limits. He has never heard of DTN, Bundle Protocol, or optimistic rollups, and he never will.

Today, Kenji needs a regolith density survey at Grid Sector 7-C for a foundation assessment. He is going to get it in about 4 minutes, from a rover 384,400 km away, for $2,500.

---

## One-Time Setup (30 minutes, once)

Before Kenji ever requests a lunar task, his company's operations team sets up the account. This happens once.

1. **Tsukimi's ops lead visits the platform dashboard** and links the corporate procurement account. Because individual tasks cost thousands of dollars, the approval workflow is different from Earth -- the ops lead configures per-project spending limits and task-type authorizations.
2. **The ops lead funds the project wallet with $50,000 in USDC credits** -- a single wire transfer. The platform converts this to a prepaid balance tied to Tsukimi's three active projects.
3. **Kenji's AI assistant is connected to the platform.** The ops lead pastes an API key into the assistant's configuration. Kenji's assistant can auto-approve tasks up to $5,000; anything above requires ops lead sign-off.
4. **The ops lead reviews the rover fleet registry.** Five rovers are registered at the Shackleton rim site, operated by two companies (LunaOps Inc. and Selene Robotics). The platform shows each rover's capabilities, thermal ratings, and current lunar day availability windows.

That's it. Kenji has $50,000 in project credits, spread across three projects. No blockchain wallet, no crypto onboarding, no DTN configuration. His assistant is authorized to act on his behalf during the current lunar day.

<details>
<summary>Under the hood</summary>

Credits are held in an Earth-side escrow wallet managed by the platform. USDC settlement happens on Base (Ethereum L2). The platform batches on-chain transactions during communication windows -- Kenji's funding transaction settles on-chain within minutes, but rover payouts are batched and posted every 6 hours. The wire transfer shows up as a single line item on Tsukimi's books: `YAK ROBOTICS LUNAR OPS $50,000.00`.

</details>

---

## Journey A: The Happy Path

**Kenji asks for a regolith survey. Three rovers evaluate the task. The best one wins. He gets his data in about 4 minutes.**

### The One-Call Path

Under the hood, Kenji's assistant can use `auction_quick_hire` -- the same single MCP tool call used on Earth, but with lunar-aware parameters. It posts the task, opens a DTN-tolerant bid window, collects bids asynchronously, picks the best rover, monitors execution, and confirms delivery. The individual auction tools remain available when the agent needs fine-grained control.

### The Request

**10:22 AM JST** -- Kenji types a message to his AI assistant:

> "I need a regolith density survey at Grid Sector 7-C. We're assessing foundation viability for the habitat module pad. Standard survey protocol."

The assistant responds immediately:

> "On it. I'm posting the survey task to the rovers at Shackleton rim. Bid window is 30 seconds over DTN -- I'll have a price and assignment shortly. This will take a few minutes because of Earth-Moon relay time."

Kenji switches to his construction timeline. He doesn't need to know which rover, how much to pay, which relay satellite will carry the message, or that the bid window accounts for 3-second round-trip light delay. The assistant handles all of that.

<details>
<summary>Under the hood</summary>

The assistant translates Kenji's request into a structured lunar task specification: task type (regolith density survey), grid coordinates (Sector 7-C), required sensors (ground-penetrating radar, accelerometer), data format (density map with 0.5m resolution), maximum budget ($5,000), deadline (end of current lunar day), thermal window (surface temperature must be below 100C), power budget (50 Wh max), and illumination requirement (day-only). This spec is packaged as a DTN bundle and transmitted to the Moon-side relay via Lunar Pathfinder.

</details>

### The Auction (Kenji doesn't see this)

Five rovers are registered at the Shackleton rim site. The platform's Earth-side coordinator transmits the RFQ as a DTN bundle. After relay propagation (~3 seconds), each rover's thin on-board agent evaluates the task locally:

- **Rover Alpha** (LunaOps, Sector 6) -- has ground-penetrating radar and accelerometer. 2 km from target. Eligible.
- **Rover Bravo** (LunaOps, Sector 9) -- has ground-penetrating radar. 5 km from target. Eligible.
- **Rover Charlie** (Selene Robotics, Sector 7) -- has ground-penetrating radar and accelerometer. 400m from target. Eligible.
- **Rover Delta** (Selene Robotics, Sector 3) -- currently in thermal shelter, low power mode. Filtered out automatically by on-board safety check.
- **Rover Echo** (LunaOps, Base Station) -- drill-equipped sampling rover, no ground-penetrating radar. Filtered out by capability check.

Rovers Alpha, Bravo, and Charlie each generate a bid locally and transmit it as a DTN bundle back to Earth. Bids arrive asynchronously over the 30-second bid window. No human operator is involved -- each rover's pricing is pre-configured by its operator based on amortized capital costs, power consumption, and distance.

| | Rover Alpha | Rover Bravo | Rover Charlie |
|---|---|---|---|
| **Operator** | LunaOps Inc. | LunaOps Inc. | Selene Robotics |
| **Location** | Sector 6 (2 km) | Sector 9 (5 km) | Sector 7 (400m) |
| **Battery** | 78% | 65% | 84% |
| **Price** | $2,800 | $3,400 | $2,500 |
| **Estimated time** | 45 minutes | 90 minutes | 25 minutes |
| **Power margin** | 34 Wh remaining after task | 12 Wh remaining | 41 Wh remaining |
| **Confidence** | 94% | 87% | 97% |

The Earth-side coordinator scores all three bids. The scoring function is adapted for lunar operations -- price (30%), speed (20%), confidence (15%), track record (10%), power margin (15%), and dust exposure rating (10%). Rover Charlie wins: it is closest, cheapest, fastest, has the best power margin, and its confidence is highest.

**The cheapest rover doesn't always win.** If Rover Charlie had a thin power margin or high cumulative dust exposure, the more expensive but safer Rover Alpha would win. On the Moon, reliability isn't just a quality metric -- it protects a $8M+ asset. The scoring function rewards safety, not just low price.

<details>
<summary>Under the hood</summary>

The auction uses a deadline-based bid window model adapted for DTN. The Earth-side coordinator publishes the RFQ via DTN bundle through Lunar Pathfinder. Each rover's on-board agent -- a minimal C state machine running on a RAD750-class processor -- evaluates the RFQ against local constraints (power budget, thermal state, current task queue, distance to target) and generates a signed bid bundle. Bids propagate back to Earth via the relay. The coordinator collects all bids received within the 30-second window, scores them using the six-factor weighted formula, and transmits the assignment back to the winning rover. Total auction time, from RFQ to assignment confirmation: about 40 seconds, dominated by two DTN relay round-trips.

</details>

### The Execution (Kenji sees a progress bar)

**10:23 AM JST** -- Kenji's assistant reports:

> "Rover Charlie (Selene Robotics) won the bid at $2,500. It's 400 meters from your survey grid and starting now. Estimated completion: 25 minutes. I'll let you know when results are in."

Kenji goes back to his timeline. In the background, Rover Charlie traverses 400 meters of regolith to Sector 7-C, deploys its ground-penetrating radar, and executes the standard survey pattern -- a series of parallel passes across the grid sector, collecting density readings at 0.5-meter intervals. The rover operates fully autonomously using its local navigation stack (Space ROS). No human is driving it.

<details>
<summary>Under the hood</summary>

During execution, Rover Charlie sends periodic checkpoint bundles via DTN: "traversal started," "arrived at grid," "survey 25% complete," "survey 50% complete," "survey complete, compiling results." These checkpoints update a progress indicator in Kenji's assistant. If a checkpoint is missed beyond the expected interval plus a tolerance window, the platform flags the task for attention. The rover's on-board agent uses pessimistic self-locking -- the moment it accepted the task, it marked itself unavailable for other assignments.

</details>

### The Result

**10:26 AM JST** -- About 4 minutes after Kenji's request (40 seconds of auction + ~3 minutes of execution and data relay), his assistant reports:

> **Regolith density survey complete for Grid Sector 7-C.**
>
> Average density: 1.58 g/cm3. Range: 1.41-1.72 g/cm3 across the grid. Two anomalous low-density zones detected in the northwest quadrant (possible subsurface void or ice lens). Full density map attached.
>
> Measured by Rover Charlie (Selene Robotics), 400m from your survey grid. Cost: $2,500 from Project Shackleton-3 balance ($38,200 remaining). Three rovers competed; the closest one won.

Kenji opens the density map, flags the anomalous zones for the geotechnical team, and attaches the data to the foundation assessment report. He moves on to his next task.

<details>
<summary>Under the hood</summary>

Rover Charlie compiled its survey data into a structured completion proof: GPS coordinates for each measurement point, timestamped density readings, a hash of the raw sensor data, and a summary density map. This proof was transmitted as a DTN bundle to the Earth-side coordinator, which ran automated verification: correct grid sector, expected number of measurement points, density values within plausible range (1.0-2.0 g/cm3 for lunar regolith), all required fields present. Verification passed. The coordinator queued a $2,500 USDC settlement for Selene Robotics in the next batch. A 24-hour dispute window opened -- if Kenji's team finds issues with the data, they can challenge the result. Kenji never sees any of this.

</details>

---

## Journey B: No Rovers Available (Lunar Night)

**Kenji asks for a task during lunar night. He is told immediately. No charge.**

**Day 15 of the lunar cycle** -- All five rovers at the Shackleton rim are in thermal shelter. Surface temperature has dropped to -160C. Kenji types:

> "Can you get a quick density check at Sector 8-A? We want to compare it with 7-C before the team meeting tomorrow."

The assistant responds within 5 seconds:

> "Sorry, all rovers at Shackleton rim are currently in thermal shelter -- it's lunar night at the site and surface temperature is -160C. The next lunar day begins in approximately 6 Earth days. I can queue this task with a time-to-live so it auto-executes when rovers come back online. Want me to do that?"

Kenji replies:

> "Yes, queue it. No rush."

> "Done. Task queued for Sector 8-A density survey. It will execute automatically at the start of the next lunar day (estimated April 2). Estimated cost: $2,400-$3,000 depending on which rover is available first. No charge until the task actually runs."

Kenji's balance is untouched at $38,200. He was never shown a DTN timeout, a relay error, or a thermal constraint violation. The platform checked all registered rovers, determined that none were available due to the lunar night cycle, and offered a clear, actionable alternative.

<details>
<summary>Under the hood</summary>

The platform queried the rover registry and found all five rovers reporting "thermal shelter" status in their most recent DTN heartbeat. The hard constraint -- illumination required and surface temperature within operating range -- failed for all rovers. No RFQ was transmitted to the Moon. The task was stored Earth-side with a configurable TTL (default: 30 Earth days) and a trigger condition: re-post automatically when at least one eligible rover reports "available" status after lunar dawn. No bids were solicited, no credits were reserved, no charge was incurred.

</details>

---

## Journey C: Rover Fails Mid-Task (Entering Lunar Night)

**A rover wins the auction but cannot complete the task as lunar night approaches. The task is deferred safely. Kenji is informed.**

**Day 13 of the lunar cycle** -- Kenji requests another survey, this time at Sector 9-B, a larger grid. Rover Alpha wins the bid at $3,200 with an estimated execution time of 90 minutes.

**11:15 AM JST** -- Rover Alpha begins the survey. It completes 60% of the grid over the next 50 minutes.

**12:05 PM JST** -- Rover Alpha's thermal sensors detect that surface temperature is dropping faster than predicted. The terminator (the boundary between lunar day and night) is approaching the survey area. Rover Alpha's on-board safety system triggers an autonomous abort: it saves its current survey checkpoint, marks the remaining grid sectors, and begins navigating back to thermal shelter.

**12:08 PM JST** -- Kenji's assistant reports:

> **Survey at Sector 9-B partially completed (60%).**
>
> Rover Alpha had to return to thermal shelter -- lunar night is approaching the survey area faster than forecast. 60% of the density grid is complete and the data looks good. The remaining 40% has been saved as a checkpoint.
>
> Options:
> 1. Accept the partial data now ($1,920 -- 60% of the bid price) and queue the remainder for next lunar day.
> 2. Reject the partial data and queue the full survey for next lunar day (no charge for the partial work).
> 3. Accept the partial data and I'll try to assign a closer rover for the remaining 40% if one is still available.

Kenji replies:

> "Accept the partial data and queue the rest."

> "Done. Partial survey data for Sector 9-B (60%) delivered. $1,920 charged to Project Shackleton-3 ($36,280 remaining). The remaining 40% is queued for the next lunar day with a checkpoint-resume, so the new rover will pick up exactly where Alpha left off."

Kenji gets useful data today and the rest in 15 days. He never saw thermal telemetry, safety abort protocols, or checkpoint serialization. The platform turned a potential failure into a partial delivery with a clear price adjustment and an automatic recovery plan.

<details>
<summary>Under the hood</summary>

When Rover Alpha's on-board safety system detected the thermal threshold breach, it triggered the `checkpoint_and_resume` failure recovery mode (configured in the task spec). The rover serialized its survey progress -- completed grid cells, raw data, current position, remaining waypoints -- into a checkpoint bundle and transmitted it via DTN before entering thermal shelter. The Earth-side coordinator received the checkpoint, validated the partial data (60% of grid cells present, density values plausible), and calculated the pro-rated payment. The remaining 40% was stored as a resume-task with the checkpoint attached. When a rover becomes available at the start of the next lunar day, it will receive the checkpoint and continue the survey from exactly where Alpha stopped. Kenji was only charged for verified, delivered work. Rover Alpha's operator (LunaOps) receives $1,920 via the next USDC settlement batch.

</details>

---

## What Kenji Sees on His Expense Report

At the end of the quarter, Tsukimi's finance team sees one line on the corporate accounts:

| Date | Description | Amount |
|------|-------------|--------|
| Jan 15 | YAK ROBOTICS LUNAR OPS - PROJECT FUNDING | $50,000.00 |

On the platform dashboard, Tsukimi's ops lead sees the per-task breakdown across all three projects:

| Date | Task | Rover | Operator | Project | Cost | Balance After |
|------|------|-------|----------|---------|------|---------------|
| Mar 26, 10:22 AM | Density survey, Sector 7-C | Charlie | Selene Robotics | Shackleton-3 | $2,500 | $38,200 |
| Mar 26, 11:15 AM | Density survey, Sector 9-B (60%) | Alpha | LunaOps Inc. | Shackleton-3 | $1,920 | $36,280 |
| Apr 2, 06:30 AM | Density survey, Sector 9-B (remaining 40%) | Bravo | LunaOps Inc. | Shackleton-3 | $1,280 | $35,000 |
| Apr 2, 08:15 AM | Density survey, Sector 8-A (queued) | Charlie | Selene Robotics | Shackleton-3 | $2,400 | $32,600 |

When the balance runs low, the ops lead wires another funding tranche. One wire transfer, many lunar tasks.

---

## What the Rover Operator Sees

The operators -- LunaOps Inc. and Selene Robotics -- each manage a fleet of rovers registered on the platform. Their experience is adapted for lunar economics:

- **Setup (once):** Register each rover with its capabilities, thermal ratings, power profile, and operating constraints. Configure pricing rules (base price per task type, adjustments for distance, power consumption, and remaining lunar day). Connect a USDC wallet for payouts. Set safety parameters (minimum power reserve, thermal abort thresholds).
- **Ongoing:** Rovers bid and execute tasks autonomously via their on-board agents. The operator monitors a dashboard (updated every DTN pass) showing completed tasks, revenue, rover health, power levels, dust accumulation, and thermal status. During lunar night, the dashboard shows all rovers in shelter mode with estimated return-to-service dates.
- **Payout:** Settlement is batched. Every 6 hours during communication windows, completed task payments are posted on-chain (USDC on Base) and transferred to the operator's wallet. For Kenji's Sector 7-C survey, Selene Robotics receives $2,500 in the next settlement batch.

The operator never manually accepts a task or submits a bid. Their rovers compete autonomously based on pre-configured pricing logic and local constraint evaluation. The operator's job is to keep rovers maintained, charged during lunar day, and safely sheltered during lunar night.

---

## What Kenji Never Saw

Everything below happened invisibly, in the ~4 minutes between Kenji's request and his density map:

- His assistant translated "regolith density survey at Sector 7-C" into a structured lunar task specification with sensor requirements, grid coordinates, resolution targets, thermal constraints, power budgets, and a data format contract.
- The task spec was serialized as a DTN bundle and routed through Lunar Pathfinder, a relay satellite in lunar orbit, adding ~3 seconds of light-time delay each way.
- The RFQ bundle was store-and-forwarded through two relay hops before reaching the surface rovers.
- Five rovers received the RFQ. Two were filtered out instantly -- one by an on-board safety check (thermal shelter), one by a capability check (no radar). Three generated cryptographically signed bids on RAD750-class processors running at 400 MIPS.
- Three bids propagated back through the relay as separate DTN bundles, arriving asynchronously over a 30-second window.
- A six-factor scoring algorithm evaluated the bids on price, speed, confidence, track record, power margin, and dust exposure.
- $2,500 in USDC credits were reserved from Kenji's project balance the moment a bid was accepted.
- The assignment bundle was transmitted back to the Moon. Rover Charlie received it, locked itself to the task, and began autonomous traversal and survey execution via Space ROS.
- Periodic checkpoint bundles propagated back to Earth during execution, updating Kenji's progress indicator.
- The rover compiled a structured completion proof -- GPS fixes, timestamped readings, data hashes -- and transmitted it as a DTN bundle.
- The Earth-side coordinator verified the proof automatically: correct grid sector, correct number of measurement points, plausible density values, delivered within deadline.
- Payment was queued for the next on-chain settlement batch: $2,500 USDC transferred to Selene Robotics on Base.
- A 24-hour dispute window opened. If Kenji's geotechnical team finds the data suspect, they can challenge the result and trigger a review.
- Every step was logged with a unique task ID for auditing across both Earth-side and Moon-side systems.

Kenji typed one sentence and got a density map. From 384,400 km away. That's the product.

---

## Timing

| Event | Wall Clock (JST) | Elapsed | Notes |
|-------|-------------------|---------|-------|
| Kenji sends request | 10:22:00 AM | 0s | |
| Task spec created | 10:22:02 AM | 2s | Assistant translates to structured spec |
| RFQ bundle transmitted via DTN | 10:22:03 AM | 3s | Queued for Lunar Pathfinder relay |
| RFQ arrives at lunar surface | 10:22:06 AM | 6s | ~3s light-time through relay |
| Rovers evaluate and generate bids | 10:22:08 AM | 8s | On-board agents, ~2s local processing |
| Bid window opens | 10:22:06 AM | 6s | 30-second window from RFQ arrival |
| Bids arrive at Earth-side coordinator | 10:22:12 AM | 12s | First bids, ~3s return relay |
| Bid window closes | 10:22:36 AM | 36s | All bids collected |
| Winning bid scored and accepted | 10:22:37 AM | 37s | Earth-side scoring, <1s |
| Assignment bundle transmitted | 10:22:38 AM | 38s | Back to Moon via DTN |
| Rover Charlie receives assignment | 10:22:41 AM | 41s | ~3s relay |
| Rover begins traversal to Sector 7-C | 10:22:42 AM | 42s | 400m autonomous drive |
| Survey execution begins | 10:23:30 AM | ~90s | Arrives at grid, deploys radar |
| Survey complete | 10:25:00 AM | ~180s | ~90s of survey passes |
| Completion proof transmitted via DTN | 10:25:02 AM | ~182s | Structured proof bundle |
| Proof arrives at Earth, verified | 10:25:06 AM | ~186s | ~3s relay + auto-verification |
| Kenji sees his density map | 10:26:00 AM | **~4 minutes** | Assistant formats and delivers |

---

## Cost Breakdown

| | Amount | Recipient | Notes |
|---|---|---|---|
| **Kenji's project pays** | $2,500 | Debited from project credits | |
| **Rover operator receives** | $2,375 | Selene Robotics, via USDC batch settlement | |
| **Platform fee** | $125 (5%) | Platform operating costs | Covers Earth-side coordinator, relay bandwidth, settlement gas fees |
| **Settlement gas fees** | ~$0.02 | Base L2 | Negligible, absorbed by platform fee |

### Amortized Economics

How $2,500 for a 25-minute task makes sense:

| Factor | Value |
|--------|-------|
| Rover delivery cost (CLPS) | ~$6M ($1.2M/kg x 5 kg) |
| Rover hardware cost | ~$2M |
| Total asset value | ~$8M |
| Operational lunar days (2-year life) | ~24 lunar days |
| Productive hours per lunar day | ~8 hours |
| Total productive hours | ~192 hours |
| Amortized cost per hour (100% utilization) | ~$41,700/hour |
| Amortized cost per hour (50% utilization) | ~$83,400/hour |
| 25-minute task at 50% utilization | ~$34,750 (fully amortized) |
| **Kenji's price ($2,500)** | **Subsidized during seed phase** |

During the seed phase, task prices are set below full amortization to drive adoption. Operators accept this because the platform increases their utilization rate -- a rover sitting idle during lunar day costs $41,700/hour in wasted capital. Even at subsidized pricing, every task Kenji runs improves the operator's economics.

---

## From Seed to Scale

- **Phase 0 -- Single-Operator Dispatch (2027-2028):** One operator, their own rovers, scheduling tasks via the Earth-side coordinator. Validates DTN protocol, lunar task spec, and settlement flow. Kenji's company is the first customer. 3-5 rovers at one site.
- **Phase 1 -- Multi-Operator Dispatch (2028-2030):** 2-3 operators share the coordinator at the south pole. Tasks assigned by priority and capability, not competitive bidding. Validates cross-operator coordination and shared-resource economics. 8-15 rovers across 2-3 sites.
- **Phase 2 -- Competitive Marketplace (2030+):** Robot populations reach 15-30+. Multiple independent operators compete on price and reliability. Full auction dynamics emerge. Relay constellations (ESA Moonlight, NASA LCRNS) provide near-continuous communication. The marketplace becomes real infrastructure.
- **Multi-Robot Workflows (2030+):** Kenji asks for a full site assessment. The platform decomposes it into sub-tasks -- density survey, imaging, sample collection -- and dispatches multiple rovers simultaneously. One request, many rovers, one invoice. This is when construction-scale operations become viable.
- **Autonomous Operations (2032+):** Rovers monitor site conditions continuously without human prompting. Kenji reviews a daily digest of foundation readiness metrics instead of requesting individual surveys. The marketplace becomes the operating system for the lunar surface.
