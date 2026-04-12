# Plan: Schema-Driven Delivery QA

**Date:** 2026-04-05
**Goal:** The task spec tells the robot exactly what to deliver. The QA validates against the same spec. The robot can self-check before submitting. No surprises.

---

## The Principle

One schema, three uses:

```
Task posted with delivery_schema
  |
  ├─→ Robot reads schema: "I need to return 3 readings with temp + humidity + timestamp"
  |     Robot can self-validate before submitting
  |
  ├─→ QA engine validates delivery against schema
  |     Same rules the robot already checked
  |
  └─→ Buyer sees: "QA passed — delivery matches spec (3/3 readings, all fields present)"
```

**The robot is never surprised** because it has the same validation rules the marketplace uses.

---

## Design

### The delivery_schema field

Added to `capability_requirements` in the task spec. It's a simplified JSON Schema that describes what the delivery data must look like.

```json
{
  "task_category": "env_sensing",
  "capability_requirements": {
    "hard": {
      "sensors_required": ["temperature", "humidity"]
    },
    "delivery_schema": {
      "description": "3 waypoint readings with temperature and humidity",
      "required": ["readings", "summary", "duration_seconds"],
      "properties": {
        "readings": {
          "type": "array",
          "minItems": 3,
          "items": {
            "required": ["waypoint", "temperature_c", "humidity_pct", "timestamp"],
            "properties": {
              "temperature_c": {"type": "number", "minimum": -40, "maximum": 85},
              "humidity_pct": {"type": "number", "minimum": 0, "maximum": 100},
              "waypoint": {"type": "integer", "minimum": 1},
              "timestamp": {"type": "string"}
            }
          }
        },
        "summary": {"type": "string", "minLength": 1},
        "duration_seconds": {"type": "number", "minimum": 0}
      }
    }
  }
}
```

### What the robot sees

When the marketplace calls `robot_submit_bid`, the task spec includes `delivery_schema`. The robot knows exactly what to return from `robot_execute_task`. The schema is human-readable (has `description`) and machine-validatable.

### What the QA engine does

Level 1 becomes: validate delivery against `delivery_schema`. No hardcoded sensor checks. The engine walks the schema:

1. **Required fields:** Are all `required` keys present in the delivery?
2. **Type checks:** Does each value match its declared type?
3. **Range checks:** Are numbers within `minimum`/`maximum`?
4. **Array counts:** Do arrays meet `minItems`/`maxItems`?
5. **String checks:** Do strings meet `minLength`?
6. **Nested objects:** Recurse into `items` (for arrays) and `properties` (for objects)

If no `delivery_schema` is in the task spec, fall back to the current behavior (basic existence + plausibility checks).

### Robot self-check

The robot (or fleet server) can run the same validation before calling back the marketplace:

```python
# In robot_execute_task:
delivery_data = await do_the_work()
schema = task_spec["capability_requirements"]["delivery_schema"]
errors = validate_against_schema(delivery_data, schema)
if errors:
    return {"success": False, "error": f"Self-check failed: {errors}"}
return {"success": True, "delivery_data": delivery_data}
```

The marketplace publishes the validation function as a utility (or documents the rules so clearly that any implementation matches).

---

## Schema Templates

For common task types, we provide pre-built schemas. The RFP processor generates these automatically.

### Template: env_sensing (Tumbller)

```json
{
  "description": "Environmental sensor readings at specified waypoints",
  "required": ["readings", "summary", "duration_seconds"],
  "properties": {
    "readings": {
      "type": "array",
      "minItems": "{waypoint_count}",
      "items": {
        "required": ["waypoint", "timestamp"],
        "properties": {
          "waypoint": {"type": "integer", "minimum": 1},
          "timestamp": {"type": "string"}
        }
      }
    },
    "summary": {"type": "string", "minLength": 1},
    "duration_seconds": {"type": "number", "minimum": 0}
  }
}
```

Plus dynamic sensor fields added based on `sensors_required`:
- temperature → `"temperature_c": {"type": "number", "minimum": -40, "maximum": 85}`
- humidity → `"humidity_pct": {"type": "number", "minimum": 0, "maximum": 100}`

### Template: site_survey (construction)

```json
{
  "description": "Topographic survey deliverables",
  "required": ["coordinate_system", "accuracy", "files"],
  "properties": {
    "coordinate_system": {"type": "string", "minLength": 1},
    "accuracy": {
      "type": "object",
      "required": ["horizontal_rmse_cm", "vertical_rmse_cm"],
      "properties": {
        "horizontal_rmse_cm": {"type": "number", "minimum": 0},
        "vertical_rmse_cm": {"type": "number", "minimum": 0}
      }
    },
    "files": {
      "type": "array",
      "minItems": 1,
      "items": {
        "required": ["name", "format"],
        "properties": {
          "name": {"type": "string"},
          "format": {"type": "string"}
        }
      }
    }
  }
}
```

---

## Implementation Plan

### Step 1: Schema validator function (auction/deliverable_qa.py)

Replace the hardcoded checks in `_check_level_1` with a generic schema validator. Keep backward compatibility — if no `delivery_schema` in the task spec, use the current checks.

```python
def validate_delivery_schema(data: dict, schema: dict) -> tuple[list[str], dict]:
    """Validate data against a delivery schema.
    Returns (issues: list[str], details: dict).
    """
```

Supports: `required`, `type`, `minimum`, `maximum`, `minItems`, `maxItems`, `minLength`, `properties`, `items` (for arrays). NOT a full JSON Schema implementation — just the subset we need. No external dependencies.

### Step 2: Wire into QA levels

- Level 0: No checks (unchanged)
- Level 1: Schema validation (if `delivery_schema` present) + basic existence (if not)
- Level 2: Schema validation + standards checks (CRS, accuracy, density)
- Level 3: Schema validation + standards + PLS stamp

### Step 3: Update task spec generation

The RFP processor and demo page should generate `delivery_schema` from task parameters. For the Tumbller demo:
- Waypoints: 3 → `readings.minItems: 3`
- Sensors: temperature, humidity → adds fields to `items.required` and `items.properties`

### Step 4: Update protocol spec + onboarding

- yakrover-protocols#15: add `delivery_schema` to `robot_submit_bid` input
- Onboarding guide: explain how robots read and self-validate against the schema
- Demo: show the schema in the delivery verification step so the buyer sees what was checked

### Step 5: Update demo page

- The task RFP generates a `delivery_schema`
- The delivery step shows: "Checking delivery against task spec..."
- QA results show which schema checks passed/failed
