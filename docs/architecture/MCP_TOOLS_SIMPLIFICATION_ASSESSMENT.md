# MCP Tools Simplification Assessment

**Date:** 2026-04-16
**Current state:** 41 tools, ~2,011 LOC in `auction/mcp_tools.py`

---

## Key Findings

### Tool Count: 41 is at the edge

- **Cursor hard limit:** 40 tools. We exceed it.
- **Accuracy degradation:** Studies show tool selection accuracy drops noticeably above 30 tools.
- **Claude's ToolSearch:** Handles 10,000+ tools via deferred loading — not our constraint.
- **Comparison:** Stripe has 27 tools. GitHub has 162+ but uses configurable toolsets (clients load only what they need).

### The real problem is not the count — it's the overlap

5-6 tools have clear functional overlap:

| Overlap | Tools | Recommendation |
|---------|-------|----------------|
| Bid retrieval | `get_bids` + `review_bids` | Merge — add `format` parameter |
| Bid acceptance | `accept_bid` + `award_with_confirmation` | Merge — add optional `buyer_notes` |
| Operator registration | `register_operator` + `onboard_operator` + `onboard_operator_guided` | Keep only `onboard_operator_guided`, deprecate others |
| Composite wrappers | `accept_and_execute` | Keep but document as convenience |

### 73% of tools are not called by the frontend — and that's by design

30 of 41 tools are programmatic (for Claude orchestration, REST API, CLI). Only 11 are called by the demo UI. This is correct architecture — the frontend is one consumer, not the only one.

### Constants defined inside the function

5 constants and one large ABI (350+ LOC) are defined inside `register_auction_tools()` but have no dependency on function arguments. Moving them out reduces the function by ~400 lines.

---

## Recommended Simplification Plan

### Phase 1: Move constants out (immediate, no API change)

Move to module level or separate files:
- `COMMON_MODELS` → module level
- `SENSOR_TO_CATEGORY` → module level (already done in IMP-049)
- `CHAIN_CONFIG`, `DEFAULT_CHAIN` → module level (already done in IMP-049)
- `EAS_ABI`, `EAS_ADDRESS`, `EAS_SCHEMA_UID` → `auction/eas_config.py`

**Impact:** -400 LOC from register_auction_tools(), no API change.

### Phase 2: Merge overlapping tools (short-term, minor API change)

1. Merge `auction_get_bids` + `auction_review_bids` → keep `auction_get_bids` with `format` param
2. Merge `auction_accept_bid` + `auction_award_with_confirmation` → keep `auction_accept_bid` with optional `buyer_notes`
3. Deprecate `auction_register_operator` (keep `onboard_operator_guided` as the one path)
4. Deprecate `auction_onboard_operator` (Stripe-only, subsumed by guided flow)

**Impact:** 41 → 37 tools, clearer API surface, ~80 LOC saved.

### Phase 3: Split into domain modules (IMP-083)

```
auction/
  mcp_tools/
    __init__.py              # register_auction_tools() imports from modules
    auction_flow.py          # post, get_bids, accept, execute, confirm, reject, cancel
    operator_tools.py        # register, onboard, activate, update_profile, add_equipment
    payment_tools.py         # fund_wallet, get_balance
    compliance_tools.py      # verify_bond, verify_operator, upload_doc, compare_terms, sam
    rfp_tools.py             # process_rfp, validate_specs, get_site_recon
    agreement_tools.py       # generate_agreement, track_execution, list_tasks
    discovery_tools.py       # register_robot_onchain, eas_attest
    observability_tools.py   # update_progress, get_task_feed, submit_feedback
    demand_tools.py          # log_unmet_demand, get_demand_signals
    convenience_tools.py     # quick_hire, accept_and_execute, get_task_schema
  eas_config.py              # EAS ABI, addresses, schema UIDs
```

**Impact:** Each module is 100-300 LOC instead of one 2,000+ LOC file. Merge conflicts eliminated.

### Phase 4: Toolset configuration (strategic, matches GitHub pattern)

Add configurable toolsets so clients can load only what they need:

```json
{
  "toolsets": {
    "buyer": ["post_task", "get_bids", "accept_bid", "execute", "confirm_delivery", "reject_delivery", "cancel_task"],
    "operator": ["onboard_operator_guided", "add_equipment", "activate_operator", "update_progress", "get_demand_signals"],
    "admin": ["eas_attest", "register_robot_onchain", "verify_operator_compliance"],
    "all": ["*"]
  }
}
```

**Impact:** Cursor users stay under 40 tools. Each persona loads only relevant tools. Selection accuracy improves.

---

## What NOT to simplify

- **Core auction flow (8 tools):** Minimal, clean, keep as-is.
- **Compliance/legal tools (6 tools):** Each has distinct domain logic, no overlap.
- **RFP tools (3 tools):** Legitimately different operations.
- **quick_hire:** High-value all-in-one convenience for simple tasks.
- **Demand signal tools:** Just built, clean design.

---

## Priority Order

1. Phase 1 (constants) — 30 min, zero risk
2. Phase 2 (merge overlaps) — 1-2 hours, minor risk
3. Phase 3 (split file) — 2-3 hours, medium risk (imports change)
4. Phase 4 (toolsets) — 3-4 hours, new feature

Recommend doing 1-2 now, 3 when the next batch of tools is added, 4 when targeting Cursor users.
