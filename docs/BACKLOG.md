# Improvement Backlog

**Last updated:** 2026-04-12
**Source:** v1.4.1 100-robot demo fleet build (2026-04-11)

---

## High Priority

### B-001: Delivery schema QA end-to-end verification
**Status:** In progress
**Context:** Category-specific delivery schemas are implemented (`auction/delivery_schemas.py`) and deployed to all 9 category servers. Server auto-injects schema based on `task_category`. Adapter passes through category-specific `delivery_data` directly. Not yet verified end-to-end on all 9 RFP presets — GPR was tested, others need confirmation.
**Action:** Run each of the 9 RFP presets through full auction cycle (bid → execute → QA → payment) and verify QA passes with correct category-specific data. Fix any schema mismatches.
**Files:** `auction/delivery_schemas.py`, `fly-fleet-sim/category_server.py`, `auction/mcp_robot_adapter.py`, `auction/deliverable_qa.py`

### B-002: Realistic delivery payload data quality
**Status:** Not started
**Context:** The research agent produced detailed specs per category (ASPRS, USGS LBS, ASCE 38, ASTM C1153, NBI/AASHTO, USIBD LOA). Current simulated data has the right structure but values are randomly generated. Should reference research output for realistic ranges: e.g., LiDAR RMSEz 0.02-0.08m, GPR dielectric constant 4-9, thermal delta-T 2-15°C.
**Action:** Update each category in `category_server.py` to produce more realistic metadata values aligned with the research specs. Add sensor model names, standards compliance fields, and file size estimates. Save research output as `docs/research/R-052_survey_deliverable_formats.md`.
**Files:** `fly-fleet-sim/category_server.py`, research output at `/private/tmp/.../tasks/a17580db5e635e2b0.output`

### B-003: Sensor vocabulary management
**Status:** Not started
**Context:** Claude generates `sensors_required` from RFP text. Sometimes produces sensor names not in the fleet vocabulary (e.g., `robotic_total_station` from surveying terminology). The fleet has a finite set: `aerial_lidar`, `gpr`, `photogrammetry`, `thermal_camera`, `rtk_gps`, `terrestrial_lidar`, `temperature`, `humidity`. When Claude produces an unrecognized name, no robot matches and the auction fails silently.
**Action:** (a) Create a canonical sensor registry in `auction/core.py`. (b) Add a mapping layer that translates equivalent terms (e.g., `total_station` → `rtk_gps`, `lidar` → `aerial_lidar`, `drone_camera` → `photogrammetry`). (c) If an unknown sensor is requested, log a warning and suggest the closest match rather than hard-failing. New sensor types should be addable without code changes.
**Files:** `auction/core.py` (sensor registry), `auction/engine.py` (filter), `auction/mcp_tools.py` (RFP processor)

### B-004: Multi-task RFP decomposition
**Status:** Not started (Phase 8 in fleet plan)
**Context:** One RFP can require multiple survey types (e.g., I-94 = aerial topo + GPR subsurface + bridge inspection). Currently the demo posts one task per "Hire Operator" click. Need: Claude decomposes RFP into N tasks, user sees preview and confirms, N auctions run in parallel, N winner cards displayed. Each task settles independently. See `docs/research/automated/R-051_imr_llm_multi_robot_task_planning.md` for architectural reference (disjunctive graphs).
**Action:** (a) Update Claude prompt to decompose multi-sensor RFPs. (b) Build decomposition preview UI. (c) Build parallel auction execution (`auction_post_task` called N times with shared `rfp_id`). (d) Build multi-result display. (e) Test with 3 MDOT RFPs that naturally decompose.
**Files:** `docs/mcp_demo_5/index.html`, `chatbot/src/index.js`, `auction/engine.py`

---

## Medium Priority

### B-005: RFP corpus expansion to 50
**Status:** 43 of 50
**Context:** `docs/research/market/RESEARCH_MICHIGAN_RFP_EXAMPLES.md` has 43 Michigan RFPs researched. Need 7 more to reach 50 target. Each should be decomposed into structured task specs with lat/lng coordinates. 5 additional demo presets could be created from the corpus.
**Action:** Research 7 more Michigan RFPs (MDOT, RCOC, DWSD, EGLE), add to the research doc, decompose into task specs.
**Files:** `docs/research/market/RESEARCH_MICHIGAN_RFP_EXAMPLES.md`

### B-006: EAS attestation frontend performance
**Status:** Monitoring
**Context:** Frontend sidebar queries EAS GraphQL at page load (~500 attestations across 2 chains). At 100 robots this takes 1-2 seconds. At 1000+ robots or with many attestations, could become slow or hit rate limits. Consider caching attestations server-side or in localStorage with TTL.
**Action:** Monitor load times. If >3s, add server-side attestation cache or localStorage with 5-min TTL.
**Files:** `docs/mcp_demo_5/index.html` (loadEASAttestations function)

### B-007: EAS attestation as registration gate
**Status:** Not started
**Context:** Currently EAS attestation filters at discovery time (post-registration). For production: attestation should gate marketplace participation — unattested robots can register on-chain but don't appear in discovery until platform attests. This separates "registered on ERC-8004" from "verified by marketplace". The `auction_eas_attest` MCP tool exists for platform admin use.
**Action:** Design attestation-gated registration flow. Consider: auto-attest on registration (current), manual review queue, or verification checklist (Part 107, insurance, etc.) before attestation.
**Files:** `auction/mcp_tools.py`, `mcp_server.py`, `scripts/eas_attest.py`

### B-008: IPFS vs off-chain delivery storage
**Status:** Research needed
**Context:** Current delivery payloads are small JSON metadata uploaded to IPFS via Pinata. Real survey deliverables are 50MB-10GB (LAS point clouds, GeoTIFF orthomosaics, DZT GPR scans). IPFS is impractical for multi-GB files. Need: metadata summary on IPFS (what was delivered), actual files on off-chain storage (S3, Filecoin, operator's own server), with content hash for verification.
**Action:** Design delivery architecture: IPFS manifest (metadata + content hashes) + off-chain storage (presigned S3 URLs or Filecoin CIDs). Buyer downloads from off-chain, verifies hash against IPFS manifest.
**Files:** New design doc needed

---

## Low Priority / Deferred

### B-009: IPFS enrichment at 1000 scale
**Status:** Deferred
**Context:** Frontend fetches each robot's IPFS card in batches of 10. At 100 robots this works. At 1000+ robots, need server-side cache or aggregated query.
**Action:** When scaling beyond 200 robots, move IPFS enrichment to server-side discovery (cache tool lists per MCP endpoint URL, not per robot).

### B-010: Sidebar virtualization
**Status:** Deferred
**Context:** 100 DOM elements render fine. At 1000+ needs virtual scroll or pagination.
**Action:** Implement when robot count exceeds 300.

### B-011: Bid engine concurrency
**Status:** Deferred
**Context:** `bid_engine()` calls are sequential per eligible robot via `MCPRobotAdapter`. 20 eligible = 20 serial HTTP calls to category MCP servers (~2s each = 40s total). Works for demo but too slow for production.
**Action:** Convert to `asyncio.gather` with per-robot timeout for parallel bidding. Cap at 30 concurrent requests.
**Files:** `auction/engine.py` (get_bids method)

### B-012: Subgraph pagination
**Status:** Deferred
**Context:** Subgraph query uses `first: 200`. At 200+ robots per chain needs cursor-based pagination.
**Action:** Implement when approaching 200 robots on a single chain.
**Files:** `mcp_server.py`, `docs/mcp_demo_5/index.html`

### B-013: Batch 1 robot is_test metadata cleanup
**Status:** Resolved (2026-04-12)
**Context:** The 4 non-is_test robots on Base Sepolia (#4104, #4107, #4492, #4494) are old test probes without `is_test` metadata. They don't have EAS attestations so they're filtered out of discovery. No action needed — they're invisible.

### B-014: Mole-04B duplicate
**Status:** Resolved (2026-04-12)
**Context:** Agent #4419 was a renamed duplicate. Set `is_test: false`, deactivated, renamed to "Mole-04B [RETIRED]", EAS attestation revoked. No longer visible.

### B-015: Batch 1 robot ownership
**Status:** Resolved (2026-04-12)
**Context:** 5 robots (#4292-4296) transferred from platform signer to correct operator wallets via ERC-721 `transferFrom`.

### B-016: RuntimeRegisteredRobot decoupling
**Status:** Resolved (2026-04-12)
**Context:** Form registration now creates `MCPRobotAdapter` directly with sensor metadata. No more `mock_fleet.py` dependency.

### B-017: Commented-out fallback in MCPRobotAdapter
**Status:** Resolved (2026-04-12)
**Context:** Deleted 16 lines of dead tumbller/fakerover hardcoded tool fallback code. Dynamic `_resolve_tools()` verified across 100 robots.
