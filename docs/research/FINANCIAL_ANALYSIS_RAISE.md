# Financial Analysis: Capital Raise for Robot Task Auction Marketplace

**Date:** 2026-03-29
**Prepared for:** YAK Robotics Garage founding team
**Model period:** 18 months (April 2026 - September 2027)
**Source documents:** PRODUCT_DSL_v2.yaml, ROADMAP_v4.md, FEATURE_REQUIREMENTS_v15.md, RESEARCH_OPERATOR_ONBOARDING_CONSTRUCTION.md, RESEARCH_COMPETITIVE_LANDSCAPE.md, RESEARCH_CONSTRUCTION_PAYMENT_FLOWS.md

---

## 1. Team Plan by Phase

### Phase 1: v1.5 — Crypto Rail + Construction Specs (Months 1-4)

v1.5 is a 4-week sprint (Weeks 13-16 per roadmap) but we model a 4-month Phase 1 inclusive of hiring ramp, QA, and MDOT pilot prep. The founding team (assumed: 1 technical founder) carries the build; hires fill gaps.

| Role | FTE | Type | Monthly Cost | Joins | Rationale |
|------|-----|------|-------------|-------|-----------|
| Technical Founder / CEO | 1.0 | FT | $0 (equity) | M1 | Existing. Drives architecture, hires, customer discovery. |
| Sr. Full-Stack Engineer | 1.0 | FT | $17,500 | M1 | Core auction engine, settlement abstraction, Next.js frontend. Assumption: $210K/yr total comp. Source: Levels.fyi 2025 median for senior full-stack in mid-market startup is $180-240K. |
| Smart Contract / Blockchain Engineer | 0.5 | Contract | $10,000 | M1 | RobotTaskEscrow.sol, x402 integration, Base deployment. 20 hrs/wk at $125/hr. Source: Web3 contract rates $100-175/hr per Toptal/Braintrust 2025. |
| Product Designer (UI/UX) | 0.5 | Contract | $6,000 | M2 | Frontend Phase 0-1, landing page, intent capture flow. 20 hrs/wk at $75/hr. |
| Construction Domain Advisor | 0.1 | Contract | $2,000 | M1 | Monthly retainer. Former GC estimator or DOT project manager. Validates task specs, payment flows, contract templates. |
| **Phase 1 Monthly Personnel** | | | **$35,500** | | |

**Phase 1 total personnel (4 months): $142,000**

### Phase 2: v2.0 — Multi-Robot + Operator Dashboard + Construction Features (Months 5-10)

v2.0 is 12 weeks (Weeks 17-28) per roadmap. We model 6 months to include hiring ramp and Michigan pilot execution.

| Role | FTE | Type | Monthly Cost | Joins | Rationale |
|------|-----|------|-------------|-------|-----------|
| Technical Founder / CEO | 1.0 | FT | $0 (equity) | Cont. | |
| Sr. Full-Stack Engineer | 1.0 | FT | $17,500 | Cont. | |
| Smart Contract Engineer | 0.5 | Contract | $10,000 | Cont. | TEE integration, Horizen L3 eval, Mode 2 prep. |
| ML/AI Engineer | 1.0 | FT | $19,000 | M5 | Task decomposition, bid scoring optimization, weather-aware scheduling. $228K/yr. Source: ML engineer median at early-stage startup $200-260K per Levels.fyi 2025. |
| Frontend Engineer | 1.0 | FT | $15,000 | M5 | Operator dashboard, payment flow UI, live auction view. $180K/yr. |
| Product Designer | 1.0 | FT | $12,500 | M5 | Full-time for dashboard, operator onboarding flows, mobile. $150K/yr. |
| DevOps / Infrastructure | 0.5 | Contract | $7,500 | M6 | CI/CD, monitoring, cloud infrastructure, security. 20 hrs/wk at $95/hr. |
| Construction Domain Advisor | 0.1 | Contract | $2,000 | Cont. | |
| Business Development (Construction) | 1.0 | FT | $10,000 | M6 | Base $120K/yr. Targets GCs and operators in AZ/NV/NM/MI. Commission structure separate (see marketing). |
| **Phase 2 Monthly Personnel** | | | **$93,500** | | |

**Phase 2 total personnel (6 months): $561,000**

### Phase 3: v2.5-v3.0 — Mining + Infrastructure + Privacy (Months 11-18)

| Role | FTE | Type | Monthly Cost | Joins | Rationale |
|------|-----|------|-------------|-------|-----------|
| All Phase 2 roles | — | — | $93,500 | Cont. | |
| Sr. Backend Engineer | 1.0 | FT | $17,500 | M11 | Escrow milestone management, retainage, lien waivers, mining task specs. |
| Security / Privacy Engineer | 0.5 | Contract | $10,000 | M12 | ZK proofs, TEE attestation, BBS+ credentials, privacy compliance. 20 hrs/wk at $125/hr. |
| Customer Success | 1.0 | FT | $7,500 | M11 | Operator onboarding support, GC relationship management. $90K/yr. |
| **Phase 3 Monthly Personnel** | | | **$128,500** | | |

**Phase 3 total personnel (8 months): $1,028,000**

### Personnel Cost Summary

| Phase | Duration | Monthly Burn | Total |
|-------|----------|-------------|-------|
| Phase 1 (v1.5) | Months 1-4 | $35,500 | $142,000 |
| Phase 2 (v2.0) | Months 5-10 | $93,500 | $561,000 |
| Phase 3 (v2.5-3.0) | Months 11-18 | $128,500 | $1,028,000 |
| **Total Personnel** | **18 months** | | **$1,731,000** |

---

## 2. Non-Personnel Costs

### Infrastructure & Cloud

| Item | Monthly | Annual | Phase | Assumptions |
|------|---------|--------|-------|-------------|
| Cloud hosting (AWS/GCP) | $1,500 → $5,000 | — | M1-18 | Start small (SQLite + single VM). Scale to multi-service by M10. Source: Early-stage SaaS typically $1-3K/mo, construction data processing pushes higher. |
| CDN / Edge (Vercel) | $200 | $2,400 | M1-18 | Next.js deployment. Pro tier. |
| Monitoring (Datadog/Sentry) | $300 → $800 | — | M1-18 | Scales with services. |
| Database (managed Postgres, later) | $0 → $500 | — | M6-18 | SQLite sufficient through v1.5. Migrate for v2.0. |
| **Infrastructure subtotal (18 mo)** | | | | **$52,200** |

Ramp assumption: $2,000/mo M1-4, $4,000/mo M5-10, $6,500/mo M11-18.

### Legal

| Item | One-Time | Monthly | Assumptions |
|------|----------|---------|-------------|
| Corporate formation (Delaware C-corp) | $5,000 | — | Standard startup formation with Clerky/Stripe Atlas. Source: Clerky $3-5K all-in. |
| IP assignment + founder agreements | $3,000 | — | |
| Outside counsel retainer | — | $3,000 | General corporate, contract review. Source: Startup law firms $250-400/hr; $3K/mo covers ~10 hrs. |
| Money transmitter analysis | $25,000 | — | 50-state analysis of whether escrow model triggers MTL requirements. Source: FinCEN compliance counsel estimates $15-30K for comprehensive analysis. Ref: unknown:money_transmission_escrow in YAML. |
| Money transmitter licensing (4 states) | $80,000 | — | If required. MI, AZ, NV, NM application fees + surety bonds. Source: State MTL applications range $2,500-$50,000 per state; most are $5-15K plus $25-100K surety bond per state. Model 4 priority states at $20K avg. |
| Insurance broker setup | $10,000 | — | E&O policy for platform, cyber liability. Setup and first year included in insurance line below. |
| Contract template development | $15,000 | — | ConsensusDocs 751 customization, e-signature integration, survey-specific exhibits. Requires construction law specialist. Source: $300-500/hr x 30-40 hrs. |
| Privacy / CCPA compliance | $8,000 | — | PII handling policy, operator data rights. |
| **Legal subtotal (18 mo)** | **$146,000** | **$54,000** | **Total: $200,000** |

**Key assumption:** Money transmitter licensing may not be required for v1.5 (prepaid credits via Stripe are covered by Stripe's licenses per YAML analysis). The $80K is modeled as a Phase 2-3 expense, triggered if escrow features require it. If Stripe covers the flow end-to-end, this drops to $0. We include it as the conservative case.

### Insurance

| Item | Annual | Assumptions |
|------|--------|-------------|
| Platform E&O (Errors & Omissions) | $8,000 | Covers marketplace liability for incorrect insurance verification, bond misrepresentation. Source: Tech E&O for early-stage $5-15K/yr depending on revenue. |
| Cyber liability | $5,000 | Data breach, ransomware. Source: Cyber insurance for startups $3-8K/yr per Coalition/Embroker 2025. |
| General liability | $3,000 | Standard business CGL. |
| D&O (Directors & Officers) | $6,000 | Required before institutional fundraising. Source: Startup D&O $4-10K/yr. |
| **Insurance subtotal (18 mo)** | | **$33,000** |

### Blockchain / On-Chain

| Item | Cost | When | Assumptions |
|------|------|------|-------------|
| Solidity audit (RobotTaskEscrow.sol) | $30,000 | M3 | Single contract, moderate complexity. Source: Trail of Bits/OpenZeppelin audits $30-80K for simple contracts; Sherlock/Code4rena contest model $15-40K. We use a mid-tier auditor. |
| Base mainnet deployment gas | $500 | M4 | Base L2 gas is cheap (~$0.01/tx). Contract deployment + initial testing. |
| Ongoing gas costs | $200/mo | M4-18 | Escrow create/release transactions. At 50-200 tasks/mo, $1-2 per on-chain tx on Base. |
| Horizen L3 testnet evaluation | $2,000 | M3 | Per feature F-12. Dev time + testnet gas. |
| **Blockchain subtotal (18 mo)** | | | **$35,500** |

### Equipment: Test Fleet for Dogfooding

| Item | Cost | When | Assumptions |
|------|------|------|-------------|
| DJI Mini 4 Pro (test drone) | $1,200 | M2 | Basic platform testing. Not survey-grade. |
| DJI Tello (already owned per prototype_fleet) | $0 | — | ERC-8004 integrated per tello-8004-mcp repo. |
| YakRover (already owned per prototype_fleet) | $0 | — | ERC-8004 integrated per yakrover-8004-mcp repo. |
| Operator partnership (test flights) | $5,000 | M3-6 | Pay a local M350+L2 operator for 2-3 test survey flights to validate the full pipeline. $1,500-2,500 per flight. |
| Boston Dynamics Spot (evaluation lease) | $0 | — | Do NOT purchase ($75-195K). Arrange demo/eval through BD partnership program. Model $0 for now. |
| **Equipment subtotal** | | | **$6,200** |

### Marketing & Sales

| Item | Monthly/One-Time | Phase | Assumptions |
|------|-----------------|-------|-------------|
| CONEXPO-CON/AGG 2026 (if applicable) | $15,000 | — | Booth, travel, materials. Source: Small booth packages $5-10K; total with travel $12-20K. CONEXPO is every 3 years; next is 2029. Model $0 unless a relevant regional show in 2026-27. |
| Construction industry conferences (2x) | $8,000 each | M6, M14 | AGC regional, ARTBA, state DOT conferences. $4K registration + $4K travel. |
| Content marketing / SEO | $2,000/mo | M3-18 | Blog, case studies, technical content targeting "drone survey" and "construction survey marketplace" keywords. |
| Operator acquisition (digital ads) | $3,000/mo | M5-18 | Targeted ads on LinkedIn, drone forums, Part 107 communities. |
| Sales commission / incentives | $2,000/mo | M6-18 | BD rep commission on GC signups. |
| Website / brand design | $5,000 | M1 | yakrobot.bid is live; this covers professional brand refinement. |
| **Marketing subtotal (18 mo)** | | | **$117,000** |

### Travel

| Item | Cost | Frequency | Assumptions |
|------|------|-----------|-------------|
| Customer discovery (AZ/NV/NM) | $3,000/trip | 4 trips | GC interviews, operator meetups. $800 flights + $1,200 hotel + $1,000 meals/transport. |
| MDOT pilot (Michigan) | $4,000/trip | 3 trips | On-site pilot execution, DOT meetings. |
| Investor meetings | $2,000/trip | 4 trips | SF, NYC, Austin/Denver (contech hubs). |
| Site visits with operators | $1,500/trip | 6 trips | Fly with operators, validate workflows. |
| **Travel subtotal (18 mo)** | | | **$41,000** |

### Software & Services

| Item | Monthly | Assumptions |
|------|---------|-------------|
| Stripe fees (2.9% + $0.30 per charge) | Variable | Modeled in revenue section. Platform absorbs on credit bundles. |
| GitHub Team | $100 | 4-8 seats. |
| Figma | $150 | Design team. |
| Linear / project management | $100 | |
| Slack | $150 | |
| Google Workspace | $150 | |
| DocuSign (e-signatures) | $300 | M5+ for contract execution. |
| Pix4D (test license) | $300 | Validate deliverable format pipeline. |
| Legal tools (Ironclad or similar) | $200 | M8+ for contract generation. |
| **Software subtotal (18 mo)** | | **$27,000** |

### Non-Personnel Cost Summary

| Category | 18-Month Total |
|----------|---------------|
| Infrastructure & Cloud | $52,200 |
| Legal | $200,000 |
| Insurance | $33,000 |
| Blockchain / On-Chain | $35,500 |
| Equipment / Test Fleet | $6,200 |
| Marketing & Sales | $117,000 |
| Travel | $41,000 |
| Software & Services | $27,000 |
| **Total Non-Personnel** | **$511,900** |

---

## 3. Revenue Model

### Platform Take Rate Analysis

| Comparable | Take Rate | Model | Notes |
|-----------|-----------|-------|-------|
| Upwork | 10% (freelancer side) | Escrow marketplace | Reduced from 20% in 2023. Source: Upwork 10-K 2025. |
| Thumbtack | $5-$300 per lead | Lead-gen, not transaction | Not applicable to our model. |
| AWS Marketplace | 3-5% | SaaS distribution | Low touch, digital delivery. |
| Procore (marketplace) | N/A | SaaS subscription | Not transaction-based. |
| Stripe (payment processing) | 2.9% + $0.30 | Payment rail | We pay this; not our revenue. |
| Construction staffing agencies | 15-30% markup | Labor marketplace | High-touch, relationship-heavy. |
| Equipment rental marketplaces | 10-20% | Asset rental | Closest analog for capital equipment. |

**Recommended take rate: 12% of task value** (buyer-side fee, inclusive of Stripe processing).

Rationale:
- Lower than staffing agencies (15-30%) because we add less human touch.
- Higher than AWS Marketplace (3-5%) because we provide escrow, insurance verification, contract generation, and quality assurance.
- Competitive with Upwork (10%) but justified by construction-domain intelligence (bond verification, COI parsing, PLS tracking, deliverable format validation).
- Operators receive 100% of their bid price. The 12% is charged to the buyer on top.
- At $3,600 task value (Marco's SR-89A scenario), the platform earns $432. At $72K full project lifecycle, the platform earns $8,640.

**Sensitivity: If market pressure forces 8% take rate, revenue projections drop by 33%. See Section 5.**

### Transaction Volume Projections

**Assumptions:**
- Michigan MDOT pilot starts Month 4 with 1-2 test tasks.
- AZ/NV/NM operator onboarding begins Month 5.
- Average task value: $2,500 (weighted toward progress monitoring at $1,000-1,500 and topo surveys at $2,000-5,000).
- Tasks per GC customer per month: 1-2 (some months 0, some months 3+).

| Month | Active GCs | Tasks/Mo | Avg Task Value | GMV | Platform Revenue (12%) |
|-------|-----------|----------|---------------|-----|----------------------|
| M1-3 | 0 | 0 | — | $0 | $0 |
| M4 | 1 (MDOT pilot) | 2 | $2,500 | $5,000 | $600 |
| M5 | 2 | 3 | $2,500 | $7,500 | $900 |
| M6 | 3 | 5 | $2,500 | $12,500 | $1,500 |
| M7 | 4 | 7 | $2,800 | $19,600 | $2,352 |
| M8 | 6 | 10 | $2,800 | $28,000 | $3,360 |
| M9 | 8 | 14 | $3,000 | $42,000 | $5,040 |
| M10 | 10 | 18 | $3,000 | $54,000 | $6,480 |
| M11 | 12 | 22 | $3,200 | $70,400 | $8,448 |
| M12 | 15 | 28 | $3,200 | $89,600 | $10,752 |
| M13 | 18 | 34 | $3,500 | $119,000 | $14,280 |
| M14 | 22 | 42 | $3,500 | $147,000 | $17,640 |
| M15 | 25 | 48 | $3,500 | $168,000 | $20,160 |
| M16 | 28 | 55 | $3,800 | $209,000 | $25,080 |
| M17 | 32 | 64 | $3,800 | $243,200 | $29,184 |
| M18 | 35 | 72 | $4,000 | $288,000 | $34,560 |
| **Total** | | **424** | | **$1,502,800** | **$180,336** |

**Key milestone: Revenue exceeds monthly burn around Month 28-30 (not within this 18-month model).** This is consistent with marketplace businesses: Upwork, Thumbtack, and Angi all took 3-5 years to reach profitability.

### Revenue Composition (Month 18 Snapshot)

| Source | Monthly | Assumptions |
|--------|---------|-------------|
| Task transaction fees (12%) | $34,560 | 72 tasks at avg $4,000 |
| Premium listings (operators) | $0 | Not modeled yet. Potential future revenue from featured operator placement. |
| Data / analytics | $0 | Not modeled. Potential for anonymized construction survey pricing intelligence. |
| SaaS subscription (enterprise) | $0 | Not modeled for 18-mo period. v3.0+ potential for DOT/enterprise dashboard subscriptions. |

---

## 4. Raise Calculation

### Monthly Burn Table

| Month | Personnel | Non-Personnel | Total Burn | Cumulative Burn | Revenue | Net Burn |
|-------|-----------|--------------|------------|----------------|---------|----------|
| M1 | $35,500 | $20,000 | $55,500 | $55,500 | $0 | $55,500 |
| M2 | $35,500 | $15,000 | $50,500 | $106,000 | $0 | $50,500 |
| M3 | $35,500 | $48,000 | $83,500 | $189,500 | $0 | $83,500 |
| M4 | $35,500 | $18,000 | $53,500 | $243,000 | $600 | $52,900 |
| M5 | $93,500 | $32,000 | $125,500 | $368,500 | $900 | $124,600 |
| M6 | $93,500 | $30,000 | $123,500 | $492,000 | $1,500 | $122,000 |
| M7 | $93,500 | $28,000 | $121,500 | $613,500 | $2,352 | $119,148 |
| M8 | $93,500 | $28,000 | $121,500 | $735,000 | $3,360 | $118,140 |
| M9 | $93,500 | $28,000 | $121,500 | $856,500 | $5,040 | $116,460 |
| M10 | $93,500 | $28,000 | $121,500 | $978,000 | $6,480 | $115,020 |
| M11 | $128,500 | $32,000 | $160,500 | $1,138,500 | $8,448 | $152,052 |
| M12 | $128,500 | $30,000 | $158,500 | $1,297,000 | $10,752 | $147,748 |
| M13 | $128,500 | $28,000 | $156,500 | $1,453,500 | $14,280 | $142,220 |
| M14 | $128,500 | $34,000 | $162,500 | $1,616,000 | $17,640 | $144,860 |
| M15 | $128,500 | $28,000 | $156,500 | $1,772,500 | $20,160 | $136,340 |
| M16 | $128,500 | $28,000 | $156,500 | $1,929,000 | $25,080 | $131,420 |
| M17 | $128,500 | $28,000 | $156,500 | $2,085,500 | $29,184 | $127,316 |
| M18 | $128,500 | $28,000 | $156,500 | $2,242,000 | $34,560 | $121,940 |
| **TOTAL** | **$1,731,000** | **$511,000** | **$2,242,000** | | **$180,336** | **$2,061,664** |

**Note:** M3 non-personnel spike includes Solidity audit ($30K) and legal formation. M5-6 spike includes hiring costs and conference. M14 includes second conference.

### Raise Summary

| Line | Amount |
|------|--------|
| 18-month gross burn | $2,242,000 |
| Less: projected revenue | ($180,336) |
| Net cash requirement | $2,061,664 |
| Contingency buffer (20%) | $412,333 |
| **Recommended raise** | **$2,500,000** |

### Round Structure

**Recommended: Seed round at $2.5M**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Round type | Seed | Too much for pre-seed ($500K-$1.5M). Not enough traction for Series A ($5-15M). Product is built (v1.0, 151 tests, 11.4K LOC) but pre-revenue. |
| Raise amount | $2,500,000 | 18 months runway + 20% buffer. |
| Instrument | SAFE (post-money) | Standard for seed. Avoids board seat / valuation negotiation friction. Source: YC standard SAFE. |
| Valuation cap | $12-15M | See comparable analysis below. |
| Dilution | 17-21% | $2.5M on $12-15M cap. |

### Comparable Raises (Construction-Tech Marketplaces)

| Company | Stage | Year | Raise | Valuation | Notes |
|---------|-------|------|-------|-----------|-------|
| Procore | Seed | 2003 | $500K | N/A | Pre-cloud era. Now public ($10B+ mktcap). Source: Crunchbase. |
| PlanHub | Seed | 2019 | $4M | ~$16M | Construction bidding marketplace. Source: Crunchbase. |
| OpenSpace | Seed | 2017 | $3.3M | ~$13M | Construction reality capture. Raised $102M total. Source: Crunchbase. |
| DroneDeploy | Seed | 2013 | $2M | ~$10M | Drone mapping SaaS. Raised $142M total. Source: Crunchbase. |
| Built Robotics | Seed | 2016 | $2.5M | ~$12M | Autonomous construction equipment. Raised $112M total. Source: Crunchbase. |
| Buildots | Seed | 2019 | $3.5M | ~$14M | Construction progress monitoring. Raised $60M total. |
| Fabric/OpenMind (ROBO) | Seed | 2025 | $20M | N/A | Robot economy protocol. Pantera Capital led. Source: RESEARCH_COMPETITIVE_LANDSCAPE.md. |
| FrodoBots | Seed | 2025 | $8M | N/A | DePIN robotics on Solana. Source: Blockworks. |

**Analysis:** Construction-tech seed rounds in 2024-2026 range $2-5M at $10-20M valuation caps. Our $2.5M at $12-15M cap is at the conservative end, reflecting pre-revenue status offset by: (a) working product (v1.0 built with 151 tests), (b) no direct competitors in the robot task auction space, (c) $8B TAM in construction surveying, (d) strong crypto/DePIN narrative with real construction use case.

### Alternative: Staged Raise

If a single $2.5M is difficult, consider:

| Tranche | Amount | Milestone | Timing |
|---------|--------|-----------|--------|
| Pre-seed | $750K | v1.5 shipped, MDOT pilot live | M1 (close now) |
| Seed | $2.0M | 10 paying GCs, $50K+ GMV/mo | M8-10 |

This reduces initial dilution and de-risks for seed investors with real traction data. Downside: fundraising twice in 10 months is a distraction.

---

## 5. Key Assumptions and Sensitivities

### Assumption Register

| # | Assumption | Source | Impact if Wrong |
|---|-----------|--------|----------------|
| A1 | Founder takes $0 salary for 18 months | Team plan | Add $150-180K if founder needs salary. |
| A2 | 12% take rate is sustainable | Market analysis (Section 3) | See sensitivity S2. |
| A3 | MDOT pilot closes by Month 4 | Roadmap + RESEARCH_MICHIGAN_RFP_EXAMPLES.md | See sensitivity S1. |
| A4 | Money transmitter license NOT required for v1.5 | YAML: legal:money_transmitter ("Stripe covers v1.5 prepaid model") | If required before v2.5, add $80-200K and 6+ months delay. |
| A5 | Solidity audit at $30K (mid-tier) | Single-contract, moderate complexity | Top-tier audit (Trail of Bits) could be $60-100K. |
| A6 | No office lease (remote team) | Cost reduction | Coworking budget of $500/mo per person could add $54-90K. |
| A7 | Average task value reaches $4,000 by M18 | RESEARCH_OPERATOR_ONBOARDING_CONSTRUCTION.md: LiDAR topo $2-5K, progress monitoring $1-2.5K | If avg stays at $2,500, M18 revenue drops to $21,600/mo. |
| A8 | Engineering salaries at mid-market startup levels | Levels.fyi 2025 data | SF/NYC-based hires could cost 30-50% more. Remote-first assumption. |

### Sensitivity S1: Customer Acquisition Takes 2x Longer

If MDOT pilot slips and GC acquisition takes twice as long:

| Metric | Base Case | 2x Slower |
|--------|-----------|-----------|
| First revenue | Month 4 | Month 8 |
| Active GCs at Month 18 | 35 | 15 |
| Monthly GMV at Month 18 | $288,000 | $120,000 |
| 18-month total revenue | $180,336 | $72,000 |
| Additional cash needed | — | $108,000 |

**Impact:** Manageable within the 20% contingency buffer ($412K). But if combined with other sensitivities, the buffer erodes. Mitigation: Accelerate operator-side onboarding (operators are also customers paying listing/premium fees in the future).

### Sensitivity S2: Take Rate Forced to 8%

If GC customers push back on 12% and competitive pressure (from Thumbtack, direct operator hiring) forces 8%:

| Metric | 12% Take | 8% Take |
|--------|----------|---------|
| 18-month total revenue | $180,336 | $120,224 |
| Revenue shortfall | — | $60,112 |
| Break-even timeline | Month 28-30 | Month 34-38 |

**Impact:** Revenue drops by 33%. Within contingency buffer for 18 months. Longer-term, need to introduce operator-side fees or premium features to compensate.

### Sensitivity S3: Money Transmitter Licensing in 10 States

If escrow features trigger MTL requirements more broadly:

| Item | 4-State (Base) | 10-State (Expanded) |
|------|---------------|-------------------|
| Application fees | $80,000 | $200,000 |
| Surety bonds (refundable) | $100,000 | $250,000 |
| Ongoing compliance (annual) | $30,000 | $75,000 |
| Legal counsel | $25,000 | $50,000 |
| **Total additional cost** | — | **$195,000** |

**Impact:** This would consume nearly half the contingency buffer. Mitigation: Delay escrow to v2.5 as planned and use Stripe-facilitated payments for v1.5-v2.0. Alternatively, use a licensed escrow partner (adds 0.5-1% to transaction cost but avoids licensing burden).

### Sensitivity S4: Combined Worst Case

2x slower customer acquisition + 8% take rate + 10-state MTL:

| Metric | Amount |
|--------|--------|
| 18-month gross burn | $2,242,000 |
| Revenue (2x slower + 8%) | ($48,000) |
| Additional MTL costs | $195,000 |
| Net cash requirement | $2,389,000 |
| Buffer remaining | $111,000 |

**Verdict:** The $2.5M raise survives even the combined worst case, but barely. The 20% buffer is consumed. To de-risk further, consider raising $3M.

---

## 6. Construction-Tech Burn Rate Benchmarks

| Company Stage | Monthly Burn | Team Size | Source |
|---------------|-------------|-----------|-------|
| Pre-seed construction-tech | $30-60K | 2-4 | Crunchbase/industry benchmarks 2024-2025 |
| Seed construction-tech | $80-150K | 5-10 | DroneDeploy, OpenSpace, PlanHub early filings |
| Series A construction-tech | $200-400K | 15-30 | Procore (early), Buildots, Built Robotics |

Our model: $56K/mo (Phase 1) ramping to $157K/mo (Phase 3). This is within the normal range for a seed-stage construction-tech company with a 5-10 person team.

---

## 7. Use of Funds Summary

| Category | Amount | % of Raise |
|----------|--------|-----------|
| Engineering (personnel) | $1,171,000 | 47% |
| Go-to-Market (BD, marketing, travel) | $258,000 | 10% |
| Legal & Compliance | $200,000 | 8% |
| Product & Design (personnel) | $300,000 | 12% |
| Infrastructure & Blockchain | $87,700 | 4% |
| Operations (insurance, software, equipment) | $66,200 | 3% |
| Domain Advisor + Customer Success | $114,000 | 5% |
| Contingency (20%) | $303,100 | 12% |
| **Total** | **$2,500,000** | **100%** |

---

## 8. Key Milestones for Investors

| Month | Milestone | Validates |
|-------|-----------|-----------|
| M3 | v1.5 shipped: USDC settlement live on Base Sepolia | Technical capability |
| M4 | MDOT pilot: first paid task completed | Product-market fit signal |
| M6 | 5 active GC customers, 10 registered operators | Supply-demand matching |
| M10 | v2.0 shipped: multi-robot workflows, operator dashboard | Platform scalability |
| M10 | $50K+ monthly GMV | Revenue traction |
| M12 | 15 active GCs, $90K GMV/mo | Series A readiness signal |
| M15 | Mining vertical first customer | Horizontal expansion |
| M18 | 35 active GCs, $288K GMV/mo, $35K platform revenue/mo | Series A raise position |

**Series A trigger:** $250K+ monthly GMV, 25+ active GCs, 50+ registered operators, multi-vertical (construction + mining). Target Series A at Month 18-22 for $8-12M at $40-60M valuation.

---

## Sources and Methodology

**Salary data:** Levels.fyi 2025 compensation data for startup (Series A-B equivalent) companies. Remote-first assumption reduces SF/NYC premium by 15-20%.

**Legal cost estimates:** Fenwick & West, Cooley, and Goodwin Procter published startup legal cost guides (2024-2025). Money transmitter licensing costs from NMLS state fee schedules and FinCEN compliance counsel estimates.

**Comparable raises:** Crunchbase funding data for Procore, OpenSpace, DroneDeploy, Built Robotics, PlanHub, Buildots, Fabric/OpenMind, FrodoBots.

**Construction-tech burn rates:** Publicly available data from Procore S-1 (early years), DroneDeploy funding announcements, and construction-tech VC reports from Fifth Wall, Building Ventures, and Brick & Mortar Ventures (2024-2025).

**Blockchain audit costs:** OpenZeppelin, Trail of Bits, and Sherlock published pricing guides (2025). Mid-tier auditor (Cyfrin, Pashov) estimated at $30K for single-contract scope.

**Insurance costs:** Coalition, Embroker, and Vouch published startup insurance pricing (2025). Construction-specific E&O from CNA, Hartford, and Zurich broker estimates.

**Market data:** US construction surveying TAM from PRODUCT_DSL_v2.yaml (sourced from SYNTHESIS_JTBD_WEDGE_PROPOSAL.md): $8B/yr total, $1.2B/yr pre-bid surveys. RaaS market from Precedence Research: $28.5B (2024) growing to $76.6B (2030).

---

*This model should be updated monthly as actual costs and revenue materialize. Key re-evaluation triggers: (1) MDOT pilot outcome, (2) money transmitter legal opinion, (3) first 10 GC NPS results (per validation_register), (4) actual operator signup rates vs. bet:robot_supply_exists falsification criteria.*
