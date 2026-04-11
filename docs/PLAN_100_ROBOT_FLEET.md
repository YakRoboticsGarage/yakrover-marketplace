# Plan: 100-Robot Fleet Registration for Demo Testing

**Date:** 2026-04-11
**Status:** Planning
**Goal:** Register ~100 test robots representing real commercial platforms, distributed across Michigan, with realistic operator fleets, reputation scores, and MCP capabilities. Enable multi-task RFP decomposition testing against 50 real MDOT RFPs.

---

## 1. Robot Models (Cross-referenced with DroneDeploy + industry)

### Tier 1 — Primary platforms (DroneDeploy-supported, high volume)

| # | Model | Manufacturer | Category | Sensors | Task Types | Price Range | Count |
|---|-------|-------------|----------|---------|------------|-------------|-------|
| 1 | Matrice 350 RTK + Zenmuse L2 | DJI | Aerial LiDAR | LiDAR (5 pts/m²), RTK GPS | Topo survey, volumetric, corridor | $10K drone + $5K sensor | 15 |
| 2 | Matrice 350 RTK + Zenmuse P1 | DJI | Aerial Photogrammetry | 45MP full-frame, RTK | Orthomosaic, progress monitoring, as-built | $10K + $6K | 12 |
| 3 | Matrice 350 RTK + Zenmuse H30T | DJI | Aerial Thermal + Visual | Thermal 640×512, wide + zoom | Thermal inspection, roof, envelope | $10K + $5K | 6 |
| 4 | Mavic 3 Enterprise RTK | DJI | Aerial (compact) | 20MP wide, 12MP tele, RTK | Small-site topo, visual inspection, progress | $5K | 10 |
| 5 | Matrice 4 Enterprise | DJI | Aerial (next-gen) | 20MP wide, 48MP tele, thermal option | General survey, inspection | $8K | 8 |
| 6 | Skydio X10 | Skydio | Aerial (US-made) | Visual, thermal, RTK, autonomy | Bridge inspection, close-range, BVLOS | $20K | 8 |
| 7 | Spot + Leica BLK ARC | Boston Dynamics | Ground LiDAR | 360° LiDAR, 5 cameras | Tunnel, interior, confined space, as-built | $75K + $40K | 6 |

### Tier 2 — Specialty platforms

| # | Model | Manufacturer | Category | Sensors | Task Types | Price Range | Count |
|---|-------|-------------|----------|---------|------------|-------------|-------|
| 8 | WingtraOne Gen 2 | Wingtra | Fixed-wing VTOL | Sony 61MP + LiDAR option | Large-area corridor, highway, statewide | $20K | 5 |
| 9 | Freefly Astro | Freefly | Aerial (US-made) | 61MP Sony, LiDAR, multispectral | Medium survey, US-manufactured req | $20K | 5 |
| 10 | Autel EVO II Pro RTK | Autel | Aerial (budget) | 20MP 1-inch, RTK | Small site, visual, budget topo | $4K | 8 |
| 11 | Flyability ELIOS 3 | Flyability | Confined-space | LiDAR, 4K camera, collision-tolerant | Tunnel interior, tank, bridge underside | $60K | 4 |
| 12 | Anzu Raptor RTK | Anzu Robotics | Aerial (no geofence) | Visual, thermal, RTK | Unrestricted airspace, no DJI geofence | $8K | 5 |
| 13 | Inspired Flight IF1200 | Inspired Flight | Heavy-lift (US-made) | LiDAR, GPR, custom payloads | Heavy payload, GPR-capable, NDAA-compliant | $29K | 4 |
| 14 | Spot + GSSI StructureScan | Boston Dynamics | Ground GPR | GPR 1600MHz + 400MHz | Subsurface utility, rebar, void detection | $75K + $25K | 4 |

**Total: 100 robots across 14 models**

### Distribution rationale
- DJI M350 variants dominate (33 units) — matches real market share for construction survey
- Mavic 3E (10) — budget entry, common for small operators
- Skydio X10 (8) — US-made requirement for government projects (Blue UAS)
- Spot variants (10) — ground capabilities for tunnel/interior (MDOT I-94 tunnel program)
- Specialty (18) — fixed-wing, confined-space, GPR for diverse RFP types

---

## 2. Operator Fleets (Michigan-based)

### Large fleets (5-10 robots each)

| Operator | Location | Fleet Size | Models | Coverage Radius | Profile |
|----------|----------|-----------|--------|----------------|---------|
| Great Lakes Aerial Survey | Troy, MI | 8 | 3× M350+L2, 3× M350+P1, 2× Mavic 3E | 240 km | Full-service, MDOT experienced |
| Motor City Drones | Detroit, MI | 7 | 2× M350+L2, 2× Skydio X10, 2× M4E, 1× M350+H30T | 160 km | Tech-forward, Blue UAS compliant |
| Peninsular Survey Systems | Lansing, MI | 8 | 3× M350+P1, 2× WingtraOne, 2× Mavic 3E, 1× Freefly Astro | 320 km | Statewide corridor specialist |
| Wolverine Robotics | Ann Arbor, MI | 10 | 3× Spot+BLK, 2× Spot+GPR, 2× ELIOS 3, 3× M350+L2 | 160 km | Ground + confined space specialist |

### Mid fleets (3-5 robots)

| Operator | Location | Fleet Size | Models | Coverage Radius | Profile |
|----------|----------|-----------|--------|----------------|---------|
| Copper Country UAS | Houghton, MI | 4 | 2× M350+L2, 1× Freefly Astro, 1× Autel EVO II | 400 km | Upper Peninsula, mining/forestry |
| Saginaw Valley Mapping | Saginaw, MI | 5 | 2× M350+P1, 2× Mavic 3E, 1× Anzu Raptor | 190 km | Agricultural + construction |
| Lakeshore Inspections | Grand Haven, MI | 4 | 2× Skydio X10, 1× M350+H30T, 1× M4E | 130 km | Coastal, bridge, marine |
| I-94 Corridor Services | Kalamazoo, MI | 5 | 2× M350+L2, 1× M350+P1, 1× IF1200, 1× Spot+GPR | 160 km | Highway corridor, GPR |
| DroneScan MI | Port Huron, MI | 3 | 1× M350+P1, 1× Mavic 3E, 1× Autel EVO II | 130 km | Small projects, cost-focused |
| Blue Water Survey | Midland, MI | 4 | 2× M4E, 1× M350+H30T, 1× Anzu Raptor | 160 km | Infrastructure, thermal |

### Solo operators (1-2 robots)

| Operator | Location | Fleet Size | Models | Coverage Radius | Profile |
|----------|----------|-----------|--------|----------------|---------|
| Jake Mitchell Aerial | Traverse City, MI | 2 | 1× M350+L2, 1× Mavic 3E | 100 km | Solo operator, new to marketplace |
| Northern Drones LLC | Gaylord, MI | 1 | 1× Autel EVO II | 65 km | Budget, rural northern MI |
| River Rouge Robotics | Dearborn, MI | 2 | 1× Spot+BLK, 1× M350+P1 | 80 km | Urban, building scan |
| Mackinac Survey Co. | St. Ignace, MI | 2 | 1× WingtraOne, 1× Mavic 3E | 160 km | Bridge, Mackinac region |
| UP Drone Works | Marquette, MI | 2 | 1× Freefly Astro, 1× Autel EVO II | 240 km | Upper Peninsula remote sites |
| Campus Robotics | East Lansing, MI | 2 | 1× Skydio X10, 1× Mavic 3E | 50 km | MSU-adjacent, student-founded |
| Flint Aerial Solutions | Flint, MI | 2 | 1× M350+L2, 1× M350+H30T | 100 km | Infrastructure, thermal |
| Drone Sisters | Livonia, MI | 2 | 1× M350+P1, 1× Autel EVO II | 80 km | Residential, commercial |

**Total: 18 operators, 100 robots**
**Geography:** Detroit metro (30), Lansing/Ann Arbor (18), West MI (8), Saginaw/Midland (9), Kalamazoo (5), Northern LP (7), UP (7), Port Huron/Thumb (5), Traverse/Mackinac (4), Flint (7)

**Naming rhymes (inspired by real Michigan operators):**
- SSI → Peninsular Survey Systems (statewide survey partner)
- DroneView Technologies → DroneScan MI (tech-focused, Bloomfield Hills area → Port Huron)
- Drone Brothers → Drone Sisters (large network, Livonia area)

---

## 3. Reputation & Pricing Distribution

| Profile | Count | Reputation Score | Bid Strategy | Availability |
|---------|-------|-----------------|--------------|-------------|
| Established (high rep, premium price) | 15 | 4.2–4.9 | 85–95% of budget | 90% online |
| Experienced (good rep, competitive) | 35 | 3.0–4.2 | 75–85% of budget | 85% online |
| Growing (moderate rep, aggressive) | 25 | 1.5–3.0 | 65–80% of budget | 80% online |
| New entrants (no rep, lowest price) | 15 | 0.0–1.5 | 55–70% of budget | 75% online |
| Offline / busy | 10 | varies | N/A | 0% (offline) |

Reputation is seeded based on operator tier:
- Large fleets start with higher reputation (more history)
- Solo operators start with low/zero reputation
- 10 robots are marked offline at any given time (rotated)

---

## 4. MCP Servers (one per robot category)

Each robot category gets a FakeRover-style MCP server on Fly.io that simulates realistic capabilities.

| Server | Robot Models | MCP Tools | Fly.io App |
|--------|------------|-----------|-----------|
| `yakrover-aerial-lidar` | M350+L2, Freefly Astro, IF1200 | `fly_waypoint`, `capture_lidar_scan`, `get_gps_position`, `check_battery`, `return_to_home`, `set_flight_altitude`, `get_wind_speed` | New |
| `yakrover-aerial-photo` | M350+P1, Mavic 3E, M4E, Autel EVO II, Anzu Raptor | `fly_waypoint`, `capture_photo`, `capture_video`, `get_gps_position`, `check_battery`, `return_to_home`, `set_camera_params` | New |
| `yakrover-aerial-thermal` | M350+H30T, Skydio X10 (thermal) | `fly_waypoint`, `capture_thermal`, `capture_photo`, `get_surface_temp`, `get_gps_position`, `check_battery`, `return_to_home` | New |
| `yakrover-fixedwing` | WingtraOne Gen 2 | `launch_vtol`, `fly_corridor`, `capture_photo`, `get_gps_position`, `check_battery`, `land_vtol`, `set_flight_plan` | New |
| `yakrover-ground-lidar` | Spot+BLK ARC | `walk_to`, `scan_360_lidar`, `capture_photo`, `get_position`, `check_battery`, `dock`, `navigate_stairs` | New |
| `yakrover-ground-gpr` | Spot+GSSI | `walk_to`, `deploy_gpr`, `scan_gpr_line`, `get_position`, `check_battery`, `dock`, `mark_utility` | New |
| `yakrover-confined` | ELIOS 3 | `fly_indoor`, `capture_lidar_scan`, `capture_photo`, `detect_obstacle`, `get_position`, `check_battery`, `return_to_pilot` | New |
| `yakrover-skydio` | Skydio X10 (visual) | `fly_waypoint`, `fly_orbit`, `capture_photo`, `capture_thermal`, `autonomous_inspect`, `get_gps_position`, `check_battery` | New |

**8 new Fly.io apps**, each a FastMCP server returning simulated sensor data appropriate to the robot type.

---

## 5. Registration Flow Changes

### Current state
- `FakeRover-` prefix required unless admin
- No `is_test` metadata
- No geographic coordinates (location is free text)
- No service radius
- No reputation seeding

### Required changes

**Registration form (`docs/mcp_demo_5/index.html`):**
- Add `is_test` checkbox (admin-only, hidden for regular operators)
- Add lat/lng fields (auto-populated from location text via geocoding, or manual entry)
- Add service radius field (km, default 100)
- Add reputation seed field (admin-only, 0.0–5.0)

**Backend (`auction/mcp_tools.py` — `auction_register_robot_onchain`):**
- Accept `is_test`, `latitude`, `longitude`, `service_radius_km`, `initial_reputation` parameters
- Write `is_test` to on-chain metadata
- Write `latitude`, `longitude`, `service_radius_km` to on-chain metadata
- Seed reputation score in `ReputationTracker` if `initial_reputation` provided

**On-chain metadata additions:**

| Key | Type | Example | Purpose |
|-----|------|---------|---------|
| `is_test` | bool | `true` | Filter test robots from production |
| `latitude` | float | `42.3314` | Home base latitude |
| `longitude` | float | `-83.0458` | Home base longitude |
| `service_radius_km` | int | `100` | Maximum travel distance for tasks |
| `home_type` | string | `garage` or `docked` | Whether robot travels or executes in-place |

**Frontend fleet filter:**
- Add "Hide test robots" toggle (reads `is_test` metadata)
- Deprecate `FakeRover-` prefix convention (keep for backward compat)

**Bid engine update (`auction/engine.py` or `mock_fleet.py`):**
- Geographic filtering: **hard cutoff** — robots do not bid on tasks outside their `service_radius_km`
- Haversine distance calculation from robot home (lat/lng) to task location
- This requires task location (lat/lng) — already partially supported in task spec as `survey_area`
- Busy/offline filtering: robots track `busy_until` timestamp after winning a task. Bid engine excludes robots where `busy_until > now()`. Task durations are realistic (minutes to hours per task type).

---

## 6. Batch Registration Script

**Script:** `scripts/register_fleet.py`

```
Usage: uv run python scripts/register_fleet.py --fleet-file fleet_manifest.yaml --chain base-mainnet --dry-run
```

**Fleet manifest format (`fleet_manifest.yaml`):**
```yaml
operators:
  - name: "Great Lakes Aerial Survey"
    company: "Great Lakes Aerial Survey LLC"
    location: "Troy, MI"
    latitude: 42.6064
    longitude: -83.1498
    service_radius_km: 240
    stripe_connect_id: "acct_test_greatlakes"
    robots:
      - name: "GL-LiDAR-01"
        model: "DJI Matrice 350 RTK + Zenmuse L2"
        equipment_type: "aerial_lidar"
        sensors: ["aerial_lidar", "rtk_gps"]
        mcp_endpoint: "https://yakrover-aerial-lidar.fly.dev/mcp"
        bid_pct: 0.85
        initial_reputation: 4.5
        home_type: "garage"
        is_test: true
      - name: "GL-LiDAR-02"
        ...
```

**Script behavior:**
1. Load manifest
2. For each operator → for each robot:
   - Call `auction_register_robot_onchain` via HTTP to MCP server
   - Wait for confirmation (tx mined)
   - Rate limit: 1 registration per 5 seconds (avoid nonce collision)
   - Log results to `fleet_registration_log.json`
3. Dry-run mode: validate manifest, estimate gas cost, print plan
4. Resume mode: skip already-registered robots (check by name in subgraph)

**Estimated cost:** 100 registrations × ~$0.005 gas = ~$0.50 on Base mainnet

---

## 7. RFP Test Corpus (50 MDOT-derived tasks)

We already have 43 Michigan RFPs documented in `docs/research/market/RESEARCH_MICHIGAN_RFP_EXAMPLES.md`. Expand to 50 and decompose each into auction tasks.

### Task type distribution (derived from RFP analysis)

| Task Type | Count | Required Sensors | Example RFP |
|-----------|-------|-----------------|-------------|
| Aerial topo survey (LiDAR) | 12 | aerial_lidar, rtk_gps | I-94 reconstruction, M-14 rebuild |
| Aerial photogrammetry / orthomosaic | 10 | photogrammetry, rtk_gps | Progress monitoring, as-built |
| Bridge inspection (aerial) | 8 | photogrammetry, thermal | 70+ bridges on I-94, Forest Ave |
| Subsurface / GPR scan | 5 | gpr | Utility detection, drainage tunnel |
| Tunnel / confined space | 4 | terrestrial_lidar | I-94 drainage tunnel, Spot interior |
| Thermal inspection | 3 | thermal_camera | Roof, envelope, MEP |
| Highway corridor (fixed-wing) | 3 | aerial_lidar, photogrammetry | MiSAIL, long corridors |
| Volumetric / stockpile | 3 | aerial_lidar | Cut/fill, aggregate |
| Dam / hydraulic survey | 2 | aerial_lidar, photogrammetry | EGLE dam program |

**Multi-task RFPs:** ~20 of the 50 RFPs decompose into 2-3 tasks each (e.g., I-94 = topo + tunnel + bridge inspection). Total auction tasks: ~80.

**Robot-task eligibility matrix:** Each task type maps to specific sensor requirements. The 100-robot fleet is designed so every task type has 8-15 eligible bidders, ensuring competitive auctions.

---

## 8. Implementation Sequence

### Phase A — Infrastructure (1-2 days)
1. Build 8 MCP server templates (one per robot category)
2. Deploy to Fly.io
3. Verify each server responds to `tools/list` and returns category-appropriate tools

### Phase B — Registration flow updates (1 day)
4. Add `is_test`, lat/lng, service_radius, `home_type`, `initial_reputation` to registration backend
5. Update frontend form with new fields (admin-only for test/reputation)
6. Add "Hide test robots" filter toggle

### Phase C — Fleet manifest + script (1 day)
7. Write `fleet_manifest.yaml` with all 100 robots, 18 operators
8. Write `scripts/register_fleet.py` batch registration script
9. Dry-run against Base Sepolia

### Phase D — Registration (1-2 hours)
10. Run batch registration on Base mainnet
11. Verify all 100 robots appear in subgraph
12. Verify IPFS enrichment shows correct tools for each robot

### Phase E — RFP corpus (1 day)
13. Expand MDOT RFP research to 50 entries
14. Decompose each into structured task specs
15. Test multi-task auctions with the full fleet

### Phase F — Demo verification
16. Run 10 diverse RFP auctions through the demo
17. Verify competitive bidding (multiple bidders per task)
18. Verify geographic filtering works
19. Verify reputation-weighted scoring produces expected winner distribution
20. Verify "busy/offline" robots correctly excluded

---

## 9. Design Decisions (Resolved)

1. **Geographic filtering: hard cutoff.** Robot will NOT bid on any task outside its `service_radius_km`. This is a hard constraint in the bid engine filter (same layer as sensor capability filtering). Requires task location (lat/lng) in the task spec — already partially supported via `survey_area`. Need to add haversine distance calculation to the filter.

2. **Busy/offline: dynamic simulation.** Robots go offline after winning a task. Task duration is realistic — minutes for small tasks, hours for large survey tasks. While a robot is executing, it cannot bid on other tasks. This creates natural competition dynamics: if the best robot just won a task, the second-best gets the next one. Implementation: `MCPRobotAdapter` or `RuntimeRegisteredRobot` tracks `busy_until` timestamp. Bid engine checks `busy_until > now()` as a hard filter alongside geographic radius.

3. **Multi-task RFP UI: user confirms decomposition.** Claude decomposes the RFP and presents the task breakdown to the user ("This project requires 3 separate survey tasks: aerial topo, GPR subsurface, bridge inspection. Each will be auctioned independently."). User confirms or edits before auctions begin. Tasks run as independent auctions — no cross-task scheduling constraints in v1.4/v1.5 (that's v2.0 per IMR-LLM research, R-051).

4. **Fly.io: always-on (~$16/mo).** 8 MCP servers at $2/mo each for stable demo. No scale-to-zero cold starts during live demos.

5. **Operator names: fictional but rhyming.** SSI → Peninsular Survey Systems, DroneView → DroneScan MI, Drone Brothers → Drone Sisters. All other names are original Michigan-themed fiction.

## 10. Remaining Open Questions

1. **Reputation decay** — should seeded reputation decay if the robot doesn't complete tasks? Or is it static for test purposes? Recommend: static for initial test, decay mechanism designed but not active until v2.0.

2. **Task duration model** — how long should each task type take in real time? Proposal:
   - Small aerial (Mavic 3E, <5 acres): 5-15 minutes
   - Medium aerial (M350, 5-50 acres): 30-90 minutes
   - Large corridor (WingtraOne, >50 acres): 2-4 hours
   - Ground scan (Spot, interior): 1-3 hours
   - Confined space (ELIOS 3): 30-60 minutes

3. **Simultaneous auctions** — when an RFP decomposes into 3 tasks, do all 3 auctions run at once (parallel) or sequentially? Parallel is more realistic (different robot types needed), but the demo UI needs to show multiple auction results.

4. **Fleet manifest review** — should we review the 100-robot manifest together before registration, or proceed with the plan as-is?
