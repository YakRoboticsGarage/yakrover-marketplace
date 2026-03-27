# Research: "Buy a Robot" Operator Onboarding Story

> **Status:** Research investigation | **Date:** 2026-03-27
> **Question:** Is it viable for someone who doesn't own a robot to buy one, join the marketplace as an operator, and earn revenue?
> **Related:** `USER_JOURNEY_MARKETPLACE_v01.md` (Sarah/buyer), `ROADMAP_v2.md` (current roadmap)

---

## 1. The User Story — Meet Alex

Alex is a 28-year-old operations technician at a coworking space in Helsinki. He sees Sarah's company paying $0.35 per sensor reading and thinks: "I could put a robot in this building and earn money while I sleep." He has no robot. He has EUR 200 to spend and a weekend to get started.

**Alex's journey:**

1. **Discovery** — Alex sees the marketplace dashboard (public stats: X tasks/day, Y robots online, average task price). He clicks "Become an Operator."
2. **Choose hardware** — The platform recommends starter robots by use case. Alex picks an ESP32-based sensor rover (~EUR 60) for indoor environmental monitoring.
3. **Purchase and assemble** — Alex orders the kit. It arrives in 2-3 days. Assembly takes 1-2 hours (soldering-free snap-together design for recommended kits).
4. **Onboard** — Alex runs `yakrover register --name "alex-rover-01"` from his laptop. The CLI walks him through WiFi config, sensor calibration check, and wallet setup. Total: ~30 minutes.
5. **Fund operator wallet** — Alex deposits EUR 10 as a small operator bond (covers platform fees during seed phase). Stripe or USDC.
6. **Go live** — Alex sets pricing rules (base rate: EUR 0.30/reading, distance multiplier: 1.2x) and marks the robot as available.
7. **First task** — Within hours (if deployed in an active facility), the robot wins an auction and completes a sensor reading. Alex earns EUR 0.35.
8. **Scale** — After 2 months, Alex has earned EUR 120. He buys a second robot. The flywheel turns.

**The gap today:** The marketplace has Sarah's buyer story and the operator side of YakRobotics (a fleet owner). There is no story for someone who starts from zero. Alex is the missing supply-side persona.

---

## 2. Hardware Options

| Robot | Type | Price (EUR) | Capabilities | Time to Marketplace | Best For |
|-------|------|-------------|-------------|---------------------|----------|
| **ESP32-S3 sensor rover** | Ground, DIY kit | 40-80 | Temp, humidity, light, gas sensors. WiFi. Basic navigation. | 1-2 hours assembly + 30 min onboard | Indoor environmental monitoring (Alex's path) |
| **Raspberry Pi rover** (e.g., PiCar-X) | Ground, kit | 100-150 | Camera, full Linux stack, extensible GPIO. WiFi/BT. | 2-3 hours setup + 30 min onboard | Visual inspection, more complex tasks |
| **Tumbller self-balancer** | Ground, assembled | 30-50 | IMU, ultrasonic, IR. ESP32-S3. Already supported in codebase (`src/robots/tumbller/`). | 30 min (pre-assembled) + 30 min onboard | Cheapest entry point, patrol/presence tasks |
| **DJI Tello** | Aerial drone | 90-120 | 720p camera, 13 min flight time. Already supported (`src/robots/tello/`). | 15 min unbox + 30 min onboard | Aerial visual inspection, hard-to-reach areas |

**Recommendation:** The Tumbller is the lowest-friction entry because it is already supported in the codebase and ships assembled. The ESP32 sensor rover is the best value for earning revenue because environmental monitoring is the most common task type in Sarah's story. The Tello is compelling but flight time limits utilization.

**Not recommended for starters:** Custom builds, ROS-based platforms (steep learning curve), anything requiring soldering or 3D-printed parts.

---

## 3. Onboarding Flow

| Step | Duration | What Happens | Blocking? |
|------|----------|-------------|-----------|
| 1. Create operator account | 2 min | Email, Stripe Connect onboarding (bank details for payouts) | Yes — needed before robot registration |
| 2. Unbox / assemble robot | 30 min - 2 hrs | Depends on kit. Tumbller: 0 assembly. ESP32 rover: snap-together. | Yes |
| 3. Flash firmware | 10 min | `yakrover flash --target tumbller` downloads and flashes marketplace-compatible firmware via USB | Yes |
| 4. Connect WiFi | 5 min | Robot creates AP, operator connects and enters WiFi credentials via captive portal | Yes |
| 5. Register on platform | 5 min | `yakrover register` — generates Ed25519 keypair, registers on ERC-8004 registry, uploads capability vector | Yes |
| 6. Calibrate sensors | 5 min | Automated self-test. Robot reports which sensors are working and their accuracy ranges. | Yes — determines which tasks the robot is eligible for |
| 7. Set pricing rules | 5 min | Operator sets base price per task type, distance multiplier, minimum battery threshold | Yes |
| 8. Fund operator wallet | 3 min | Deposit via Stripe or USDC. Minimum EUR 5 (covers potential dispute bonds). | Yes for paid tasks |
| 9. Go live | 1 min | `yakrover activate` — robot starts listening for auctions | No — can be deferred |

**Total time (Tumbller):** ~35 minutes from unbox to live.
**Total time (ESP32 kit):** ~2.5 hours from unbox to live.

**Key friction points to address:**
- Step 3 (firmware flash) is the biggest drop-off risk. Must be one-command, no toolchain installation.
- Step 5 (ERC-8004 registration) currently requires on-chain transaction. In v1.5, the platform should sponsor gas for new operator registration to eliminate crypto friction.

---

## 4. Business Model

### Unit economics for a single ESP32 sensor rover

| | Conservative | Moderate | Optimistic |
|---|---|---|---|
| **Tasks per day** | 3 | 10 | 25 |
| **Avg price per task** | EUR 0.30 | EUR 0.35 | EUR 0.35 |
| **Daily revenue** | EUR 0.90 | EUR 3.50 | EUR 8.75 |
| **Monthly revenue** | EUR 27 | EUR 105 | EUR 263 |
| **Robot cost** | EUR 60 | EUR 60 | EUR 60 |
| **Monthly operating cost** (electricity, WiFi — marginal) | EUR 2 | EUR 2 | EUR 2 |
| **Breakeven** | 2.4 months | 18 days | 7 days |
| **Annual profit** | EUR 298 | EUR 1,236 | EUR 3,132 |

**Platform fee impact:** At seed phase (0% fee), all revenue goes to operator. At 10% platform fee, breakeven extends by ~10%. Still viable.

**Is this viable?** Yes, at moderate utilization. The critical assumption is task density — Alex's robot needs to be in a location where tasks are being posted. A robot in an empty warehouse earns nothing. The marketplace must solve demand-side placement or give operators visibility into where demand exists.

**Comparison:** Helium hotspot economics at launch were similar — EUR 50-500 hardware, EUR 20-100/month earnings, 1-3 month breakeven. That model attracted 900K+ nodes. The difference: Helium demand was synthetic (token rewards), ours must be real (actual tasks from actual buyers).

---

## 5. Marketplace Implications

**Positive network effects:**
- More robots = better geographic coverage. Sarah's "no robots available" scenario (Journey B) becomes rarer.
- More robots = price competition. Sarah's reading drops from EUR 0.35 to EUR 0.25 as operators compete.
- More robots = faster response. Closer robot = less travel time = faster completion.
- Diverse hardware = broader capability coverage. Thermal cameras, gas sensors, drones for aerial tasks.

**Demand-side benefits for buyers:**
- Lower prices through competition (good for Sarah).
- Higher reliability — more backup robots for Journey C (failure recovery).
- New task types become possible as the capability set expands.

**Supply-side risks for operators:**
- Price compression if too many robots in one area. Need geographic balancing signals.
- Utilization drops as supply grows faster than demand. Classic marketplace chicken-and-egg.

**The marketplace must grow demand and supply in lockstep.** If Alex deploys 5 robots but Sarah is the only buyer, utilization is ~2%. The "Become an Operator" funnel should be gated by demand signals — show Alex a heatmap of unserved tasks before he buys hardware.

---

## 6. Integration with Existing Roadmap

### Where this fits

| Roadmap Phase | Relevant Features | Effort |
|---|---|---|
| **v1.5** (weeks 13-16) | Operator Stripe Connect onboarding already spec'd. Add: operator registration CLI, gas-sponsored ERC-8004 registration, demand heatmap API. | +1-2 weeks |
| **v2.0** (weeks 17-28) | Operator dashboard (task history, revenue, robot health). Payout configuration. Multi-robot management for operators scaling from 1 to 5 robots. | Fits naturally in multi-robot workflow track |
| **v2.1+** | Operator reputation (BBS+ credentials for operators, not just robots). Operator-to-operator robot resale marketplace. | Longer-term |

### Backend features needed

1. **Operator registration flow** — Account creation, KYC-light (email + bank), Stripe Connect Express. Already partially built for YakRobotics; needs to be generalized for independent operators.
2. **Robot onboarding CLI** (`yakrover` tool) — Firmware flash, WiFi config, ERC-8004 registration, sensor calibration. New tooling.
3. **Operator dashboard** — Revenue, task history, robot status, payout history. New frontend (or API for third-party dashboards).
4. **Demand signal API** — "Where are tasks being posted that no robot can serve?" Helps operators decide where to deploy. New feature.
5. **Gas sponsorship** — Platform pays gas for new robot ERC-8004 registration. Small cost (< $0.10/registration on Base), big friction reduction.
6. **Robot health monitoring** — Battery, uptime, sensor drift alerts. Push notifications to operator. Partially exists in fleet server; needs operator-facing exposure.

### Recommended approach

Add operator onboarding as a **v1.5 stretch goal** (registration CLI + gas sponsorship). Full operator dashboard and demand signals in **v2.0**. This avoids scope creep in v1.5 while signaling that supply-side growth is on the roadmap.

---

## 7. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Ghost operators** — Register but never come online. Pollutes registry, misleads buyers about coverage. | Medium | Require heartbeat every 15 min. Auto-delist after 24 hours offline. Reputation score includes uptime. |
| **Quality control** — Poorly calibrated sensors return bad data. Buyers lose trust. | High | Mandatory sensor self-test at registration. Periodic calibration checks. Buyer can dispute readings with independent verification. Reputation score penalizes disputed tasks. |
| **Race to bottom** — Too many operators in one area, prices crash below viable levels. | Medium | Show operators the local supply/demand ratio before deployment. Consider minimum price floors during seed phase. Scoring algorithm rewards reliability over cheapest price (already designed). |
| **Geographic concentration** — All operators deploy in Helsinki, none in Oulu. | Medium | Demand heatmap showing unserved areas. Consider location-based incentives (bonus for underserved zones). |
| **Support burden** — Hobby operators need more hand-holding than fleet companies. | Medium | Invest in self-service tooling (CLI, docs, community forum). Tier support: community-first, platform support for paying operators. |
| **Hardware fragmentation** — 50 different robot models, each with quirks. | Medium | Maintain a "certified compatible" list of 3-5 starter robots. Provide reference firmware for each. Community can add others but without official support. |
| **Regulatory** — Drones in shared spaces, data privacy for sensor readings in occupied buildings. | Low (for now) | Start with ground rovers in private facilities (operator has facility permission). Drone support requires explicit geofencing and operator certification. |

---

## 8. Verdict

**Is this story viable?** Yes, with caveats.

The economics work at moderate utilization (10+ tasks/day). The hardware is cheap enough (EUR 40-150) that breakeven is measured in weeks, not years. The onboarding flow can be compressed to under an hour for pre-assembled robots.

**The critical dependency is demand density.** Alex's robot earns nothing without buyers posting tasks in his location. The marketplace must either (a) grow demand first and then invite supply, or (b) give operators clear demand signals so they deploy where tasks exist.

**Recommended next steps:**
1. Add "Become an Operator" to the v1.5 scope as a stretch goal (CLI + registration flow).
2. Build a demand heatmap prototype showing unserved task types by location.
3. Write the full user journey document (like Sarah's) once this research is validated.
4. Test the onboarding flow end-to-end with a Tumbller (already in codebase) to measure actual time-to-first-task.
