# End-to-End Test Scenarios

Simulated marketplace usage by real GC personas, operators, and PLSs. Each scenario exercises the full MCP tool chain and reports gaps.

## Quick Start

```bash
# Run all 5 GC scenarios
cd yakrover-marketplace
PYTHONPATH=. python auction/tests/scenarios/run_all.py

# Run a single scenario
PYTHONPATH=. python auction/tests/scenarios/gc_profiles/01_dans_excavating/scenario.py

# Run with verbose output
PYTHONPATH=. python auction/tests/scenarios/run_all.py --verbose
```

## Structure

```
scenarios/
├── README.md              ← This file
├── run_all.py             ← Test runner — runs all GC scenarios, produces gap report
├── gc_profiles/           ← 5 General Contractor personas
│   ├── 01_dans_excavating/    Multi-task highway RFP (happy path)
│   ├── 02_ca_hull/            Bridge inspection (compliance-heavy)
│   ├── 03_kamminga/           Progress monitoring (budget tier)
│   ├── 04_ajax_paving/        Topo + GPR dual-task (PLS-as-a-service)
│   └── 05_anlaan/             I-94 tunnel + topo (demo scenario, most complex)
├── operator_profiles/     ← 5 Drone survey operator personas
│   ├── 01_ssi/                Full-service PLS firm
│   ├── 02_rigg_land/          Traditional surveyor + drones
│   ├── 03_emmet_drones/       Solo operator, NO PLS
│   ├── 04_jeek_productions/   Small team, minimal docs
│   └── 05_droneview/          Premium, federal/state, full compliance
├── pls_profiles/          ← 2 Professional Land Surveyor personas
│   ├── 01_jennifer_chen/      Aerial LiDAR specialist, MI #42871
│   └── 02_david_okonkwo/      Tunnel/terrestrial specialist, MI #38902
└── service_mocks/         ← Mock external services
    └── mock_payment_service.py    Plaid, escrow, payout, mediation
```

## How Each Scenario Works

Each `scenario.py`:
1. Loads the profile's RFP, bond, terms, and compliance documents
2. Creates an AuctionEngine with the construction mock fleet (7 operators)
3. Exercises the full tool chain step by step
4. Prints pass/fail for each step
5. Returns a list of gaps (failures + missing capabilities)

## Adding a New Scenario

1. Create a folder under `gc_profiles/` or `operator_profiles/`
2. Add `PROFILE.md` with company info, persona, and expected outcome
3. Add supporting documents (rfp.txt, bond.txt, gc_terms.txt, etc.)
4. Add `scenario.py` following the pattern from existing scenarios
5. The `run_all.py` runner auto-discovers new folders

### Profile Folder Contents

**GC profiles need:**
| File | Required | Description |
|------|----------|-------------|
| PROFILE.md | Yes | Company context, persona, scenario description |
| rfp.txt | Yes | The RFP document (real or realistic) |
| bond.txt | No | Payment bond (for bonded public projects) |
| gc_terms.txt | Yes | Subcontract terms for terms comparison |
| scenario.py | Yes | Test script exercising the tool chain |

**Operator profiles need:**
| File | Required | Description |
|------|----------|-------------|
| PROFILE.md | Yes | Operator info, equipment, coverage area |
| faa_part_107.txt | Yes | FAA certificate |
| insurance_coi.txt | Yes | Certificate of insurance |
| pls_license.txt | No | PLS license (not all operators have one) |
| sam_registration.txt | No | SAM.gov registration (federal work) |
| operator_terms.txt | No | Operator's standard terms |
| scenario.py | Yes | Onboarding and bid flow test |

**PLS profiles need:**
| File | Required | Description |
|------|----------|-------------|
| PROFILE.md | Yes | License info, review process |
| pls_license.txt | Yes | License document |
| review_checklist.md | Yes | What they verify before stamping |

## Service Mocks

`service_mocks/mock_payment_service.py` provides:
- **MockPlaidConnection** — Bank account linking for ACH transfers
- **MockEscrowAccount** — Fund, hold, release escrow for task payments
- **MockOperatorPayout** — Stripe Connect or ACH payout to operators
- **MockMediationService** — Dispute opening and resolution

These are used by scenario scripts to test end-to-end payment flow from GC funding through operator payout.

## Gap Report

After running, `run_all.py` produces a consolidated gap report:
- **Tool failures** — which MCP tools errored and why
- **Missing capabilities** — what scenarios needed but doesn't exist
- **Data flow gaps** — information lost between tool calls
- **Scoring issues** — wrong operator won
- **Edge cases** — PLS gaps, small budgets, confined space, near-airport airspace

Use the gap report to prioritize the next round of engine improvements. Fix gaps, re-run scenarios, repeat.

## Service Connections Needed

| Service | Mock | Production | Purpose |
|---------|------|-----------|---------|
| Bank/ACH | MockPlaidConnection | Plaid API | GC funds escrow via ACH |
| Escrow | MockEscrowAccount | Platform escrow (Stripe) | Holds funds during task execution |
| Payout | MockOperatorPayout | Stripe Connect | Pays operators on delivery |
| Bond verify | bond_verifier.py | Surety portal APIs | Verifies payment bonds |
| Insurance | compliance.py | myCOI / Jones API | Verifies COI documents |
| PLS verify | compliance.py | State licensing boards | Verifies PLS licenses |
| SAM.gov | compliance.py | SAM.gov Entity API | Checks debarment status |
| E-signature | (not yet mocked) | DocuSign / DocuSeal API | Agreement execution |
| Mediation | MockMediationService | AAA / platform rules | Dispute resolution |
| PLS stamp | (not yet mocked) | DocuSign e-seal API | Electronic PLS seal |
