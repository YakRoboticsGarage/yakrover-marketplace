# R-051: IMR-LLM — Industrial Multi-Robot Task Planning via LLMs

**Status:** Research complete
**Date:** 2026-04-11
**Source:** Su et al., "IMR-LLM: Industrial Multi-Robot Task Planning and Program Generation using Large Language Models," ICRA 2026. [arXiv:2603.02669](https://arxiv.org/abs/2603.02669)
**Code:** [github.com/XiangyuSu611/IMR-LLM-Code](https://github.com/XiangyuSu611/IMR-LLM-Code) (code not yet released, "coming soon")
**Project page:** [xiangyusu611.github.io/imr-llm](https://xiangyusu611.github.io/imr-llm/)
**Relevance:** Direct architectural reference for marketplace task decomposition, multi-robot scheduling, and executable program generation. Maps to `bet:agent_mediation_adds_value` and the v2.0 multi-robot workflow capability.

---

## Problem Addressed

In industrial production lines, multiple robots must collaborate on manufacturing tasks (polishing, welding, beveling, transport, assembly). Unlike household robotics where task order is flexible ("cut vegetables then fry" or "fry then cut"), industrial tasks have **strict sequential constraints** and **resource conflicts** — two robots cannot use the same polishing table simultaneously; transport must complete before assembly begins.

Existing LLM-based multi-robot planners (SMART-LLM, LaMMA-P, COHERENT) work well for household tasks but fail on industrial scheduling because they rely on the LLM to directly reason about operation ordering and resource conflicts. As complexity increases (>3 robots, >10 operations), LLMs produce infeasible schedules — conflicting allocations, missed dependencies, deadlocks.

**Core insight:** Don't ask the LLM to solve the scheduling problem. Ask it to *formalize* the problem as a graph, then use deterministic algorithms to solve it.

---

## Architecture: Three-Stage Pipeline

### Stage 1: Task Planning (LLM + Disjunctive Graph Solver)

**Input:** Natural language instruction `I` + scene description `S` (JSON: robots, machines, workpieces)

**Step 1a — LLM decomposes task into operations:**
The LLM receives the instruction and scene, then outputs:
- **Operation set O:** Each operation has a type (transport, polish, weld, bevel, assembly), workpiece, and required machines
- **Allocation set A:** Which robot performs each operation
- **Intra-workpiece precedence Q:** Processing order for operations on the same workpiece

The LLM uses Chain-of-Thought prompting with general rules (not few-shot examples). This is a key difference — rules generalize better than examples across diverse scenes.

**Step 1b — Construct disjunctive graph G:**
The textual LLM output is converted to a formal disjunctive graph `G = {V, C, D_M, D_R}`:
- **Vertices V:** Each operation is a node, plus source `V_S` and terminal `V_T`
- **Conjunctive arcs C:** Directed edges for precedence constraints within a workpiece
- **Machine disjunctive arcs D_M:** Undirected edges when operations compete for the same machine
- **Robot disjunctive arcs D_R:** Undirected edges when operations compete for the same robot

**Step 1c — Solve the graph:**
A FIFO heuristic algorithm (not the LLM) solves the disjunctive graph to produce a **scheduling graph F** — a feasible execution order for all operations. When multiple operations share a resource, execution order follows their sequence in the operation set.

**Why this matters for yakrobot.bid:** The marketplace currently uses `score_bids()` for single-robot task matching. For v2.0 compound tasks (aerial LiDAR + GPR + progress monitoring), we need exactly this: decompose the buyer's request into operations, assign operators, and schedule them with dependency constraints. The disjunctive graph approach is more robust than asking Claude to directly output a schedule.

### Stage 2: Program Generation (Process Tree → LLM → Code)

**Process tree T:** A hierarchical tree built once from program examples. Each node has:
- **Index:** Unique identifier
- **Type:** "General" (shared across operations) or operation-specific
- **Functional description:** What this step does
- **Snippet:** Python code template

The tree captures that different operation types (transport, polish, weld) share common sub-processes (e.g., photographing for localization appears in both transport and polishing). By structuring as a tree, common steps are shared nodes — reducing redundancy and improving code reuse.

**Code generation:** Given the process tree, scene, operation set, and allocations:
1. LLM selects a unique branch through the tree for each operation
2. Combines code snippets from all nodes in the branch
3. Creates wrapper functions per operation and entry-point function calls

**Output program P = {P_C, P_W, P_E}:**
- **P_C:** Function calls (entry points)
- **P_W:** Wrapper functions (one per operation)
- **P_E:** Execution functions (reusable, from tree nodes)

**Atomic skill library:** Pre-implemented primitives — `convert_to_robot()`, `motion_plan()`, `move_by_path()`, `control_device()`, etc.

### Stage 3: Execution

The scheduling graph F determines execution order. An operation starts only when all predecessors are complete. Each operation dispatches to its wrapper function in P.

---

## Benchmark: IMR-Bench

**Platform:** SpeedBot KunWu (industrial robot simulation + real hardware)

| Property | Detail |
|----------|--------|
| Scenes | 23 industrial production lines from real environments |
| Robots per scene | 1–7 |
| Tasks | 50 manufacturing tasks |
| Operation types | 5: transport, polishing, welding, beveling, assembly |

**Three complexity levels:**

| Level | Robots | Operations | Characteristics |
|-------|--------|------------|-----------------|
| Single robot | 1 | ≤5 | No resource conflicts |
| Simple multi-robot | ≤3 | ≤10 | Parallel or sequential, basic synchronization |
| Complex multi-robot | ≤7 | ≤24 | Mixed parallel/sequential, multiple resource conflicts |

**Distribution:** 20% single, 30% simple multi, 50% complex multi

**Scene format:** JSON describing robots (with end-effectors and controllable devices), machines (by name, with workpieces), and workpieces (type, processing states)

---

## Metrics

| Metric | What it measures | Formula |
|--------|-----------------|---------|
| **Operation Consistency (OC)** | Decomposition + allocation accuracy | Intersection-over-union of generated vs ground-truth allocations |
| **Scheduling Efficiency (SE)** | Schedule quality | Normalized makespan vs optimal (only calculated when OC=1) |
| **Executability (Exe)** | Can the program run? | Binary: syntactic + semantic validity |
| **Goal Completion Recall (GCR)** | Does execution achieve the goal? | Intersection of achieved vs expected workpiece state changes |
| **Success Rate (SR)** | Full success | 1 if SE=1 and GCR=1, else 0 |

---

## Results (Table I from paper)

| Method | Single Robot SR | Simple Multi SR | Complex Multi SR |
|--------|----------------|-----------------|------------------|
| SMART-LLM | 0.50 | 0.20 | 0.00 |
| LaMMA-S | 0.71 | 0.56 | 0.16 |
| LaMMA-O | 0.71 | 0.56 | 0.20 |
| LiP-O | 0.93 | 0.63 | 0.24 |
| **IMR-LLM (GPT-4o)** | **1.00** | **0.87** | **0.68** |
| **IMR-LLM (Qwen3-32B)** | **1.00** | **0.87** | **0.60** |

Key takeaway: All baselines collapse on complex multi-robot tasks (0–24% SR). IMR-LLM achieves 60–68% SR by offloading scheduling to a deterministic solver instead of asking the LLM to reason about resource conflicts directly.

---

## Ablation Study (Table II)

| Variant | What's removed | Complex Multi SR |
|---------|---------------|------------------|
| w/order | LLM generates execution order directly (no disjunctive graph) | 0.00 |
| w/dependency | LLM generates dependency graph (no disjunctive graph) | 0.36 |
| w/o T | No process tree (raw examples for code gen) | 0.44 |
| **Full IMR-LLM** | All components | **0.68** |

Both the disjunctive graph (for planning) and process tree (for code gen) are essential. Without the graph, scheduling collapses at scale. Without the tree, code executability drops.

---

## Applicability to Robot Task Auction Marketplace

### Direct parallels

| IMR-LLM concept | Marketplace equivalent | Status |
|-----------------|----------------------|--------|
| Task decomposition (NL → operations) | RFP → task specs (skills: rfp-to-robot-spec) | Built (v1.0) |
| Operation types (transport, polish, weld) | Survey types (aerial_lidar, gpr, photogrammetry, progress_monitoring) | Built (v1.0) |
| Robot allocation (capabilities + proximity) | Bid scoring (capability filter + 4-factor score) | Built (v1.0) |
| Disjunctive graph for scheduling | Not built — needed for compound tasks | v2.0 |
| Process tree for code generation | Not built — dynamic tool resolution is simpler version | v2.0 |
| Resource conflicts (machine exclusion) | Equipment conflicts (same drone can't fly two sites simultaneously) | Not modeled |
| IMR-Bench (23 scenes, 50 tasks) | Scale testing plan (100/1000 robots, varied equipment) | Planned (v1.5+) |

### What to adopt

1. **Disjunctive graph for compound tasks (v2.0).** When Marco posts "I need topo + subsurface + progress monitoring for SR-89A", the system decomposes into 3 operations with dependencies (topo before progress monitoring baseline). A disjunctive graph models operator/equipment conflicts and produces a feasible schedule. The LLM decomposes; the solver schedules.

2. **Don't ask the LLM to schedule.** IMR-LLM's core finding: LLMs are good at decomposition and allocation but bad at scheduling with resource constraints. Our auction engine already separates these — Claude decomposes the RFP, `score_bids()` handles matching. For multi-operator scheduling in v2.0, use a graph solver, not Claude.

3. **Process tree pattern for execution.** Construction survey execution follows consistent patterns per operation type (aerial LiDAR: plan flight → launch → capture → process → deliver). A process tree could replace the current `_resolve_tools()` pattern matching with structured operation templates. Each survey type maps to a tree branch with parameterizable steps.

4. **Operation Consistency metric.** Useful for evaluating our RFP decomposition quality — compare LLM-generated task specs against expert-annotated ground truth for real RFPs.

### What doesn't transfer

- **Fixed operation types.** IMR-LLM has 5 operation types in a controlled factory. Construction surveys have more variation (weather delays, partial data, site access changes). The rigid graph structure needs flexibility extensions.
- **Single-scene assumption.** Factory scenes are static. Construction sites change between visits — the scene description needs to incorporate temporal state.
- **No pricing/bidding.** IMR-LLM assigns robots directly. The marketplace uses competitive bidding. The disjunctive graph could model the scheduling layer *after* bid winners are selected.
- **Closed environment.** All robots and machines are known upfront. The marketplace discovers operators dynamically via ERC-8004.

---

## Comparison with Other LLM Multi-Robot Frameworks

| Framework | Approach | Strength | Weakness |
|-----------|----------|----------|----------|
| **SMART-LLM** [6] | Single LLM call: decompose + allocate + schedule + code | Simple | Collapses at >3 robots |
| **LaMMA-P** [9] | Decompose → allocate → schedule (LLM for all 3) | Better ordering | LLM still generates schedule |
| **LiP-LLM** [7] | Dependency graph + linear programming for allocation | Graph structure | LP can't handle all constraint types |
| **COHERENT** [8] | Task assigner + robot executor (heterogeneous robots) | Multi-type robots | Single LLM call for planning |
| **DART-LLM** | DAG for dependencies + parallel execution | Parallel tasks | Indoor-only |
| **IMR-LLM** | Disjunctive graph + FIFO solver + process tree | Deterministic scheduling | Factory-only, code not released |

**For the marketplace:** The IMR-LLM approach of "LLM formalizes, solver optimizes" is the right architectural pattern. The marketplace already does this for single-task scoring (LLM decomposes RFP → engine scores bids). For multi-task workflows, extend with a scheduling graph.

---

## Open Questions for Marketplace Integration

1. **How to model weather dependencies?** Construction surveys have weather windows. The disjunctive graph needs temporal constraints beyond simple precedence (e.g., "aerial LiDAR requires wind <15mph, can only execute during weather window W").

2. **How to handle partial completion?** If the aerial survey completes but GPR is weather-delayed, the scheduling graph needs to support pausing and resuming — checkpoint-and-continue semantics.

3. **How to incorporate bidding?** The graph could be constructed after bid winners are selected. Alternatively, the graph could be constructed first (with placeholder operators), then operators bid on individual operations within the graph.

4. **Process tree for construction operations.** What does the tree look like for aerial LiDAR topo? Likely: `plan_flight → check_airspace → check_weather → launch → capture → land → process_point_cloud → validate_density → export_landxml → deliver`. Each step maps to an MCP tool or external service.

---

## References

- Su et al., "IMR-LLM: Industrial Multi-Robot Task Planning and Program Generation using Large Language Models," ICRA 2026, arXiv:2603.02669
- Kannan et al., "SMART-LLM: Smart multi-agent robot task planning using large language models," IROS 2024
- Zhang et al., "LaMMA-P: Generalizable multi-agent long-horizon task allocation and planning with LLM-driven PDDL planner," ICRA 2025
- Obata et al., "LiP-LLM: Integrating linear programming and dependency graph with large language models for multi-robot task planning," Robotics and Automation Letters, 2024
- Liu et al., "COHERENT: Collaboration of heterogeneous multi-robot system with large language models," arXiv:2409.15146, 2024
- Survey: "Large Language Models for Multi-Robot Systems: A Survey," arXiv:2502.03814, 2025
