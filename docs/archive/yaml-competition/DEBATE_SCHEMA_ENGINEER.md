# Debate: Schema Engineer — Technical Component Representation in the YAML DSL

**Role:** Infrastructure/Protocol Engineer
**Date:** 2026-03-29
**Input:** PLAN_YAML_DSL_SYNTHESIS.md, FEATURE_REQUIREMENTS_v15.md, ANALYSIS_AUTONOMOUS_EXECUTION_GAPS.md, FOUNDATIONAL_TECH_ANALYSIS.md, auction/ source code
**Position:** The YAML must be a typed, cross-referenced, machine-parseable specification — not prose with indentation. Every node an agent reads should resolve to a concrete type, a concrete dependency, or a concrete gap.

---

## 1. Critique of the Current Plan

The plan (Option D: Debate -> Schema -> Parallel Fill -> Review) is structurally sound but underspecifies the hard parts. The 8 proposed domains are human-oriented categories. An agent parsing this YAML does not think in terms of "Vision & Thesis" — it thinks in terms of callable tools, typed interfaces, state transitions, and dependency graphs. The domain decomposition should be reorganized around **what a machine needs to resolve** when it encounters any node in the specification.

Specific weaknesses:

1. **"Product Architecture" is doing too much work.** MCP tools, the settlement abstraction, the autonomous execution stack, sensor-to-task mappings, and the state machine are five distinct schemas with cross-references between them. Lumping them into one domain guarantees an incoherent subgraph.

2. **No type system proposed.** Without explicit types, the YAML is a tree of strings. An agent cannot validate whether a settlement mode reference in a task spec actually resolves to a defined mode without type-aware parsing.

3. **Cross-reference mechanism undefined.** The plan says "ontologically coherent" but does not specify how node A in domain 3 refers to node B in domain 6. This is the single hardest problem in the synthesis and it is unaddressed.

---

## 2. MCP Tool Inventory and Relationships

The current system has 15 MCP tools registered via `register_auction_tools()` in `auction/mcp_tools.py`. These are thin wrappers around `AuctionEngine` methods. The gap analysis identifies at least 3 missing tools (`plan_flight`, `validate_capture`, a processing dispatch tool). The YAML must capture both the existing inventory and the planned inventory with a schema that lets an agent understand what each tool does, what it requires, and what it produces.

### Proposed schema: `mcp_tools`

```yaml
mcp_tools:
  # Each tool is keyed by its registered MCP tool name
  post_task:
    status: implemented            # implemented | planned | deprecated
    version: "1.0"
    source_module: auction.mcp_tools
    wraps: AuctionEngine.post_task
    input_schema:
      type: object
      required: [title, category, budget_ceiling_usd]
      properties:
        title: { type: string }
        category: { type: string, enum: "$ref:types.task_categories" }
        budget_ceiling_usd: { type: string, format: decimal }
        capability_requirements: { type: array, items: { type: string } }
        location: { "$ref": "types.geo_point" }
    output_schema:
      type: object
      properties:
        request_id: { type: string, format: uuid }
        state: { "$ref": "types.task_state" }
    errors:
      - code: INVALID_CATEGORY
        condition: "category not in VALID_TASK_CATEGORIES"
      - code: BUDGET_INVALID
        condition: "budget_ceiling_usd <= 0"
    triggers_state_transition: "null -> posted"
    settlement_relevant: false

  plan_flight:
    status: planned                # from gap analysis Layer 2
    version: null
    gap_reference: "execution_stack.layer_2_mission_planning"
    input_schema:
      type: object
      required: [boundary_polygon, sensor_id, altitude_agl_m, overlap_pct]
      properties:
        boundary_polygon: { "$ref": "types.geo_polygon" }
        sensor_id: { "$ref": "sensors.{sensor_id}" }
        altitude_agl_m: { type: number }
        overlap_pct: { type: number, minimum: 0, maximum: 100 }
    output_schema:
      type: object
      properties:
        waypoints: { type: array, items: { "$ref": "types.geo_point_3d" } }
        estimated_flight_time_min: { type: number }
        battery_swap_points: { type: array, items: { "$ref": "types.geo_point" } }

  validate_capture:
    status: planned                # from gap analysis Layer 4
    version: null
    gap_reference: "execution_stack.layer_4_infield_qc"
    input_schema:
      type: object
      required: [task_spec_ref, captured_dataset_path]
      properties:
        task_spec_ref: { type: string, format: uuid }
        captured_dataset_path: { type: string }
    output_schema:
      type: object
      properties:
        passed: { type: boolean }
        point_density_pts_per_sqm: { type: number }
        coverage_pct: { type: number }
        gsd_cm: { type: number }
        deficiencies: { type: array, items: { type: string } }
```

### Key design decisions:

- **`$ref` uses dotted paths** into the same YAML namespace, not JSON Pointer. Reason: the YAML may be split into multiple files (see section 7) and dotted paths are unambiguous across files.
- **Every tool declares `input_schema` and `output_schema`** using JSON Schema vocabulary. An agent can use these to construct valid calls and parse responses without reading Python source.
- **`status` is an enum, not a boolean.** This lets the spec capture the full lifecycle: planned tools from gap analysis, implemented tools, and deprecated tools that agents should stop using.
- **`triggers_state_transition`** links tools to the state machine (section below). This is how an agent reasons about sequencing.

---

## 3. Settlement Abstraction as Typed Data

The settlement layer (`auction/settlement.py`) already defines `SettlementMode` as a 4-value enum and `SettlementReceipt` as a dataclass. The YAML must capture the full 2x2 matrix (timing x privacy) plus the chain-specific implementation details, version targets, and the `SettlementProvider` protocol interface.

### Proposed schema: `settlement`

```yaml
settlement:
  modes:
    immediate_transparent:
      timing: immediate
      privacy: transparent
      chain: base
      protocol: x402
      currency: usdc
      version_implemented: "1.5"
      version_designed: "1.5"
      escrow_contract: RobotTaskEscrow.sol
      commitment_hash: "H(request_id || salt)"  # FD-4
      receipt_fields:
        required: [task_request_id, commitment_hash, amount, currency, recipient_id, tx_hash]
        optional: [metadata]

    immediate_private:
      timing: immediate
      privacy: shielded
      chain: base_horizen_l3          # FD-5 candidate
      protocol: null                  # TBD
      currency: usdc
      version_implemented: null
      version_designed: "2.1-P"
      escrow_contract: null
      notes: "Horizen L3 on Base — same EVM, TEE-based compliant privacy"

    batched_transparent:
      timing: batched
      privacy: transparent
      chain: base
      protocol: dtn_settlement_bundle
      currency: usdc
      version_implemented: null
      version_designed: "2.1-L"
      batch_window_seconds: null      # determined by DTN link schedule
      notes: "Lunar operations — settlement queued until comm window"

    batched_private:
      timing: batched
      privacy: shielded
      chain: null
      protocol: null
      currency: null
      version_implemented: null
      version_designed: "3.0"
      notes: "Convergence of lunar + privacy tracks"

  interface:
    name: SettlementProvider
    type: protocol                    # Python Protocol (structural typing)
    source_module: auction.settlement
    methods:
      settle:
        async: true
        params:
          task_request_id: { type: string }
          amount: { type: decimal }
          currency: { type: string }
          recipient_id: { type: string }
          mode: { "$ref": "settlement.modes.*" }
        returns: { "$ref": "types.settlement_receipt" }
      refund:
        async: true
        params:
          receipt: { "$ref": "types.settlement_receipt" }
        returns: { "$ref": "types.settlement_receipt" }

  privacy_constraints:
    - rule: "Robot wallet addresses NEVER in API responses"
      decision_id: PP-2
      enforced_at: api_layer
    - rule: "Commitment hash, never raw request_id, in on-chain memos"
      decision_id: FD-4
      enforced_at: settlement_layer
    - rule: "No new metadata fields on ERC-8004 entries"
      decision_id: foundational_tech.consideration_2
      enforced_at: discovery_bridge

  types:
    settlement_receipt:
      fields:
        task_request_id: { type: string, format: uuid }
        commitment_hash: { type: string, description: "H(request_id || salt)" }
        mode: { "$ref": "settlement.modes.*" }
        amount: { type: decimal }
        currency: { type: string, enum: [usd, usdc, eur] }
        recipient_id: { type: string, description: "Platform-internal, never a wallet address" }
        tx_hash: { type: string, nullable: true }
        stripe_transfer_id: { type: string, nullable: true }
        timestamp: { type: string, format: datetime }
        metadata: { type: object }
```

### Why this level of detail matters:

An agent evaluating whether it can bid on a task needs to know which settlement mode the task uses. If it sees `mode: batched_transparent`, it must understand that settlement will be delayed and that `version_implemented: null` means this mode is not yet live. The schema makes this computable, not inferential.

---

## 4. Autonomous Execution Stack (6 Layers)

The gap analysis defines a clean 6-layer stack. The YAML must represent each layer with its current status, the tools that serve it, the gaps that remain, and the dependencies between layers. This is where the cross-referencing system earns its keep.

### Proposed schema: `execution_stack`

```yaml
execution_stack:
  # Layers ordered from bottom (prerequisites) to top (outputs)
  layers:
    layer_0_regulatory:
      name: Regulatory Compliance
      description: "LAANC, 811 notification, COA, PE oversight"
      automation_level: partial       # none | partial | full
      human_required: true
      tools:
        existing: []
        planned:
          - name: file_laanc
            api: "Aloft/DroneUp LAANC API"
            status: identified
      dependencies: []                # no layer dependencies — this is the base
      gap_severity: low
      owner: operator                 # robot | operator | platform
      skill_coverage:
        rfp_to_robot_spec: identifies_requirements
        rfp_to_site_recon: flags_constraints

    layer_1_site_access:
      name: Site Access
      description: "Physical transport to launch position, gate access, safety compliance"
      automation_level: none
      human_required: true
      tools:
        existing: []
        planned: []
      dependencies: [layer_0_regulatory]
      gap_severity: high_remote       # HIGH for remote deployment, LOW for on-site robots
      owner: operator
      deployment_models:
        on_site: { gap_severity: low, description: "Robot already stationed" }
        remote: { gap_severity: high, description: "Human must transport and launch" }

    layer_2_mission_planning:
      name: Mission Planning
      description: "Convert boundary + spec into flight plan / scan plan"
      automation_level: none
      human_required: true            # currently — would be false with plan_flight tool
      tools:
        existing: []
        planned:
          - "$ref": "mcp_tools.plan_flight"
      dependencies: [layer_1_site_access]
      gap_severity: high
      inputs:
        - "$ref": "skills.rfp_to_site_recon.outputs.boundary_polygon"
        - "$ref": "skills.rfp_to_robot_spec.outputs.sensor_requirements"
        - "$ref": "skills.rfp_to_robot_spec.outputs.accuracy_requirements"
      outputs:
        waypoints: { "$ref": "types.waypoint_list" }
        battery_plan: { type: object }
        takeoff_landing_zones: { type: array }

    layer_3_mission_execution:
      name: Mission Execution
      description: "Fly the plan, avoid obstacles, handle weather holds"
      automation_level: partial
      human_required: false           # modern platforms handle this
      tools:
        existing: []
        planned: []
        note: "Handled by robot firmware (DJI Pilot, Skydio autonomy, Spot API)"
      dependencies: [layer_2_mission_planning]
      gap_severity: medium
      unresolved:
        deviation_tolerance: "Task spec does not define how far robot can deviate from plan"
        real_time_obstacles: "FAA database misses temporary structures"

    layer_4_infield_qc:
      name: In-Field Quality Control
      description: "Validate capture quality before declaring mission complete"
      automation_level: none
      human_required: true            # currently — post-processing QC only
      tools:
        existing: []
        planned:
          - "$ref": "mcp_tools.validate_capture"
      dependencies: [layer_3_mission_execution]
      gap_severity: high
      validation_checks:
        - point_density_vs_spec
        - coverage_completeness
        - gsd_achieved_vs_required
        - accuracy_estimate

    layer_5_deliverable_generation:
      name: Deliverable Generation
      description: "Raw data -> processed outputs (DTM, ortho, contours, reports)"
      automation_level: partial
      human_required: true            # format conversion to agency standards
      tools:
        existing: []
        planned: []
      dependencies: [layer_4_infield_qc]
      gap_severity: medium
      processing_models:
        operator_processes: { description: "Most realistic today" }
        platform_saas: { description: "Platform runs cloud processing — value-add" }
        marketplace_task: { description: "Separate processing task posted to marketplace" }

  coverage_summary:
    skills_cover: "Layer 0 (identified, not executed) + Layer 2 inputs"
    auction_covers: "Operator selection (right robot, certs, location)"
    missing: "Layer 2 (flight planning API), Layer 4 (in-field QC), Layer 5 (automated processing)"
```

### Design rationale:

- Each layer has a `dependencies` array pointing to other layers. An agent can topologically sort these to determine execution order.
- `tools.planned` entries use `$ref` to the `mcp_tools` section — single source of truth for tool definitions.
- `gap_severity` is per-layer but can be overridden per deployment model (see `layer_1_site_access.deployment_models`).
- `skill_coverage` links back to the skills section (below), closing the loop between "what we know" and "what we can do."

---

## 5. Sensor-Equipment-Task-Operator Mapping

This is a four-way relationship that the current research documents describe in prose. The YAML must make these relationships traversable. An agent evaluating a bid needs to answer: "Does this operator's equipment have sensors that satisfy this task's requirements?"

### Proposed schema: `sensors` and `equipment`

```yaml
sensors:
  l2_lidar:
    type: lidar
    model_example: "Riegl VQ-780 II"
    point_density_pts_per_sqm: { min: 8, typical: 12 }
    accuracy_nva_cm: 10
    usgs_quality_level: QL1
    weight_kg: 11.5
    power_draw_w: 280
    compatible_platforms: [matrice_350, vapor_55, alta_x]

  photogrammetry_42mp:
    type: camera
    model_example: "Sony A7R IV"
    resolution_mp: 42
    gsd_at_120m_cm: 1.5
    usgs_quality_level: QL2
    weight_kg: 0.6
    compatible_platforms: [matrice_350, phantom_4_rtk, skydio_x10]

equipment:
  matrice_350:
    type: drone
    manufacturer: DJI
    model: "Matrice 350 RTK"
    max_payload_kg: 2.7
    flight_time_min: 55
    rtk_capable: true
    obstacle_avoidance: basic
    compatible_sensors: [l2_lidar, photogrammetry_42mp]
    autonomy_level: semi            # manual | semi | full
    firmware_api: dji_pilot_2

  skydio_x10:
    type: drone
    manufacturer: Skydio
    model: "X10"
    max_payload_kg: 1.0
    flight_time_min: 35
    rtk_capable: true
    obstacle_avoidance: ai_full     # relevant to execution_stack.layer_3
    compatible_sensors: [photogrammetry_42mp]
    autonomy_level: full
    firmware_api: skydio_autonomy

# The mapping chain an agent traverses:
# task.sensor_requirements -> sensors.{id} -> sensors.{id}.compatible_platforms
#   -> equipment.{id} -> operators who own equipment.{id}
#   -> operator.certifications vs task.regulatory_requirements
```

### Proposed schema: `task_templates`

```yaml
task_templates:
  lidar_survey_ql1:
    category: survey
    sensor_requirements:
      - "$ref": "sensors.l2_lidar"
    accuracy_requirements:
      nva_cm: 10
      nps_pts_per_sqm: 8
    regulatory_requirements:
      - faa_part_107
      - laanc_or_coa
    deliverable_formats:
      - LAS_1.4
      - DTM_surface
      - contour_map
    typical_budget_per_acre_usd: { min: 150, max: 400 }
    execution_stack_requirements:
      gcp_required: conditional      # depends on PPK/RTK availability
      layer_0: [faa_part_107, laanc_authorization]
      layer_2: { overlap_pct: 60, sidelap_pct: 60 }
      layer_4: [point_density_check, accuracy_check]
      layer_5: [las_processing, surface_generation, format_conversion]

  photogrammetry_ortho:
    category: mapping
    sensor_requirements:
      - "$ref": "sensors.photogrammetry_42mp"
    accuracy_requirements:
      gsd_cm: 2.0
    regulatory_requirements:
      - faa_part_107
    deliverable_formats:
      - GeoTIFF_orthomosaic
      - point_cloud
    typical_budget_per_acre_usd: { min: 50, max: 150 }
```

This four-entity chain (task -> sensor -> equipment -> operator) is the core matching logic. Without it in structured form, the auction engine's `score_bids()` function is a black box to any agent trying to understand why its bid was rejected.

---

## 6. State Machine Representation

The auction engine (`auction/engine.py`) implements a task lifecycle: `posted -> bidding -> bid_accepted -> in_progress -> delivered -> verified -> settled`. Plus failure states: `withdrawn`, `rejected`, `abandoned`, `cancelled`, `failed`. The YAML must represent this as a first-class state machine, not as implicit knowledge buried in code.

### Proposed schema: `state_machine`

```yaml
state_machine:
  task_lifecycle:
    initial_state: posted
    terminal_states: [settled, withdrawn, cancelled, failed]
    states:
      posted:
        description: "Task published, awaiting bids"
        transitions:
          - to: bidding
            trigger: first_bid_received
            tool: "$ref:mcp_tools.submit_bid"
          - to: withdrawn
            trigger: poster_withdraws
            tool: "$ref:mcp_tools.cancel_task"
      bidding:
        description: "Collecting bids, scoring"
        transitions:
          - to: bid_accepted
            trigger: poster_accepts_bid
            tool: "$ref:mcp_tools.accept_bid"
          - to: withdrawn
            trigger: poster_withdraws
            tool: "$ref:mcp_tools.cancel_task"
        timeout:
          duration_source: task.bidding_deadline
          on_expire: auto_accept_highest_score
      bid_accepted:
        description: "Winning operator notified, escrow funded"
        transitions:
          - to: in_progress
            trigger: operator_begins_work
            tool: "$ref:mcp_tools.accept_and_execute"
          - to: bidding
            trigger: operator_rejects
            action: re_pool
          - to: bidding
            trigger: operator_timeout
            action: re_pool
      in_progress:
        description: "Robot executing task"
        transitions:
          - to: delivered
            trigger: operator_delivers
            tool: "$ref:mcp_tools.confirm_delivery"
          - to: bidding
            trigger: operator_abandons
            action: re_pool
        timeout:
          duration_source: task.sla_seconds
          on_expire: abandon_and_repool
      delivered:
        description: "Deliverables submitted, awaiting verification"
        transitions:
          - to: verified
            trigger: poster_verifies
            tool: "$ref:mcp_tools.verify_delivery"
          - to: in_progress
            trigger: poster_rejects
            action: request_redelivery
      verified:
        description: "Work accepted, settlement triggered"
        transitions:
          - to: settled
            trigger: settlement_complete
            settlement_mode: "$ref:settlement.modes.*"
      settled:
        description: "Payment disbursed, task complete"
        transitions: []
      withdrawn:
        description: "Poster cancelled before acceptance"
        transitions: []
      cancelled:
        description: "Admin or system cancellation"
        transitions: []
      failed:
        description: "Unrecoverable failure"
        transitions: []
```

This lets an agent answer: "Given the current state of task X, what are my valid next actions?" by traversing `state_machine.task_lifecycle.states.{current_state}.transitions`.

---

## 7. One File vs. Directory of Files

**Recommendation: Directory of files with a manifest.**

Reasons:

1. **Parallel extraction.** The plan calls for parallel agents filling domains. If the target is a single file, agents must coordinate writes. If the target is a directory, each agent writes its own file independently and a final agent assembles the manifest.

2. **Size.** The full specification — tools, settlement, execution stack, sensors, equipment, state machine, user profiles, legal constraints, roadmap — will exceed 2,000 lines of YAML. A single file of that size is painful to diff, review, and validate.

3. **Agent context windows.** An agent resolving a specific question ("what sensors satisfy QL1?") should not need to load the legal governance section. File-level granularity lets agents load only what they need.

4. **Validation.** Each file can have its own JSON Schema validator. The manifest defines the cross-file reference rules.

### Proposed structure:

```
spec/
  manifest.yaml          # version, file list, cross-reference index
  types.yaml             # shared type definitions (geo_point, decimal, uuid, etc.)
  mcp_tools.yaml         # all MCP tools (existing + planned)
  settlement.yaml        # 4 modes, interface, privacy constraints
  execution_stack.yaml   # 6 layers, gaps, coverage
  state_machine.yaml     # task lifecycle, transitions, triggers
  sensors.yaml           # sensor catalog
  equipment.yaml         # platform catalog
  task_templates.yaml    # task archetypes with requirement chains
  skills.yaml            # rfp-to-robot-spec, rfp-to-site-recon, future skills
  users.yaml             # personas, including agent personas
  legal.yaml             # bonds, compliance, dispute resolution, PE requirements
  roadmap.yaml           # versions, milestones, feature-to-version mapping
  decisions.yaml         # all decision IDs with status and references
```

The `manifest.yaml` file serves as the entry point:

```yaml
manifest:
  version: "0.1.0"
  schema_version: "1"
  generated: "2026-03-29"
  files:
    - path: types.yaml
      domain: shared_types
      depends_on: []
    - path: mcp_tools.yaml
      domain: tool_inventory
      depends_on: [types.yaml, state_machine.yaml]
    - path: settlement.yaml
      domain: payment
      depends_on: [types.yaml]
    # ...
  cross_reference_rules:
    syntax: "dotted_path"
    resolution: "domain.key.subkey"
    example: "settlement.modes.immediate_transparent"
    unresolved_ref_is: error          # not warning — strict validation
```

---

## 8. Making the YAML Parseable by Agents (Not Just Human-Readable)

This is the central concern and the one most likely to be underweighted by the other debate participants. "Machine-readable" is not the same as "valid YAML." Valid YAML that an agent cannot reason over is useless.

### Principles:

**8.1. Every node must have a deterministic type.**

Bad:
```yaml
accuracy: "high"
```

Good:
```yaml
accuracy:
  nva_cm: 10
  unit: centimeters
  standard: USGS_QL1
```

An agent cannot act on "high." It can act on `nva_cm: 10`.

**8.2. References must be resolvable, not implied.**

Bad:
```yaml
tools:
  - plan_flight  # presumably defined somewhere
```

Good:
```yaml
tools:
  planned:
    - "$ref": "mcp_tools.plan_flight"
```

The `$ref` syntax is borrowed from JSON Schema / OpenAPI. Agents already know how to resolve these. Do not invent a new reference syntax.

**8.3. Enums must be closed sets, not open strings.**

Every field that has a finite set of valid values must declare that set. This is what lets an agent validate its own output before submitting it.

```yaml
types:
  task_state:
    type: enum
    values: [posted, bidding, bid_accepted, in_progress, delivered, verified, settled, withdrawn, cancelled, failed]
    source: auction.core.TaskState

  settlement_mode:
    type: enum
    values: [immediate_transparent, immediate_private, batched_transparent, batched_private]
    source: auction.settlement.SettlementMode

  gap_severity:
    type: enum
    values: [low, medium, high, high_remote]
```

**8.4. Every planned/future item must have a `version_target` and a `status`.**

Agents need to distinguish between "exists and callable" vs. "designed but not built" vs. "identified as needed but not designed." The three-value status enum (`implemented`, `planned`, `deprecated`) should apply uniformly to tools, settlement modes, features, and skills.

**8.5. The YAML should include its own JSON Schema.**

Ship a `spec/schema/` directory with JSON Schema files that validate each YAML file. This serves two purposes: (a) CI can validate the spec itself, and (b) agents can read the schema to understand the structure without reading the data.

```
spec/
  schema/
    mcp_tools.schema.json
    settlement.schema.json
    execution_stack.schema.json
    ...
```

**8.6. Decision traceability must be machine-traversable.**

Every node that exists because of a decision should carry a `decision_id` field. An agent that encounters `commitment_hash: "H(request_id || salt)"` should be able to resolve `decision_id: FD-4` to the full decision record in `decisions.yaml`, including rationale, status, and supersedes/superseded_by links.

```yaml
# In decisions.yaml
FD-4:
  title: "Commitment hash in on-chain memos"
  status: approved
  version: "1.5"
  rationale: "Prevents permanent public link between tasks and payments"
  supersedes: AD-3
  referenced_by:
    - "settlement.modes.immediate_transparent.commitment_hash"
    - "settlement.privacy_constraints[1]"
```

---

## 9. Skill Definitions

The two existing skills (`rfp-to-robot-spec`, `rfp-to-site-recon`) and any future skills need representation. A skill is not a tool — it is a multi-step agent workflow that may invoke multiple tools and produce structured output.

```yaml
skills:
  rfp_to_robot_spec:
    status: implemented
    version: "1.0"
    description: "Extract task specification from an RFP document"
    inputs:
      rfp_document: { type: string, format: file_path }
    outputs:
      task_spec:
        type: object
        properties:
          sensor_requirements: { type: array, items: { "$ref": "sensors.*" } }
          accuracy_requirements: { "$ref": "types.accuracy_spec" }
          deliverable_formats: { type: array, items: { type: string } }
          budget_ceiling_usd: { type: decimal }
          regulatory_requirements: { type: array }
    execution_stack_coverage:
      layer_0: identifies_requirements
      layer_2: provides_inputs
    validation: validate_task_spec.py

  rfp_to_site_recon:
    status: implemented
    version: "1.0"
    description: "Generate execution context from RFP + public data sources"
    inputs:
      rfp_document: { type: string, format: file_path }
      task_spec: { "$ref": "skills.rfp_to_robot_spec.outputs.task_spec" }
    outputs:
      site_recon:
        type: object
        properties:
          boundary_polygon: { "$ref": "types.geo_polygon" }
          airspace_class: { type: string }
          obstacles: { type: array }
          weather_norms: { type: object }
          unknowns: { type: array, items: { type: string } }
          pre_mobilization_checklist: { type: array }
    execution_stack_coverage:
      layer_0: flags_constraints
      layer_2: provides_inputs
    validation: validate_site_recon.py
    data_staleness_policy:
      max_age_days: 90
      fields_affected: [airspace_class, obstacles, weather_norms]
```

---

## 10. API Contracts

The fleet server exposes an HTTP API alongside the MCP tools. The YAML should capture API endpoints with the same rigor as MCP tools — routes, auth requirements, request/response schemas, and which privacy constraints apply.

```yaml
api:
  base_url: "/api/v1"
  auth:
    type: bearer_token
    env_var: MCP_BEARER_TOKEN
  endpoints:
    accept_bid:
      method: POST
      path: "/tasks/{task_id}/accept"
      payment_middleware: x402          # v1.5: USDC payment verified before handler
      privacy_constraints:
        - "$ref": "settlement.privacy_constraints[0]"  # no wallet addresses in response
      request_schema:
        task_id: { type: string, format: uuid }
        bid_id: { type: string, format: uuid }
      response_schema:
        "$ref": "mcp_tools.accept_bid.output_schema"
```

---

## Summary of Positions

| Question | Position |
|----------|----------|
| File structure | Directory with manifest, not single file |
| Reference syntax | `$ref` with dotted paths, JSON Schema compatible |
| Type system | Explicit types on all leaf nodes; closed enums |
| MCP tools | Full input/output schemas, status lifecycle, state machine links |
| Settlement | 4 modes as typed records with chain/protocol/version fields |
| Execution stack | 6 layers with dependencies, tool refs, gap severity, ownership |
| Sensor mapping | 4-entity chain: task -> sensor -> equipment -> operator |
| State machine | First-class representation with transitions, triggers, tool refs |
| Agent parseability | JSON Schema validation, no ambiguous strings, resolvable refs |
| Decision tracing | Every node carries `decision_id` linking to decisions.yaml |

The risk I am guarding against: a YAML that reads well in a code review but that no agent can actually traverse to answer a question like "can I bid on this task with my equipment?" If the spec cannot answer that question mechanically, it has failed its purpose.
