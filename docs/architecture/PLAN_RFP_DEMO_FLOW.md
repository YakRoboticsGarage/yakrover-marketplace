# Plan: RFP Upload Demo Flow

## Current Flow
Search bar → intent capture → Claude structures → payment → single auction → result

## New Flow (RFP-driven)
Upload RFP → processing animation → task decomposition view → individual auctions → aggregated results

## Screen-by-Screen

### Screen 1: Landing (modify existing)
- Keep hero, feed, robots, operator CTA
- Change search input placeholder to emphasize RFP upload
- Add a prominent "Try with sample RFP" button that loads a pre-baked MDOT highway RFP
- Clicking it skips the text input and goes straight to processing

### Screen 2: RFP Processing (NEW — replaces intent capture)
- Show the RFP document text (scrollable, styled like a document)
- Animated "processing" overlay: "Extracting survey requirements..."
- Requirements appear one by one as they're "found":
  - ✓ Survey type: Topographic + Subsurface
  - ✓ Accuracy: ±0.05 ft vertical (MDOT 104.09)
  - ✓ Area: 6.6 miles × 100 ft = ~80 acres
  - ✓ Deliverables: LandXML, DXF, GeoTIFF, LAS, CSV
  - ✓ Standards: MDOT Sec 104.09, NCHRP 748 Cat 1A
  - ✓ Budget: $45,000 total
  - ✓ Timeline: Complete by April 30, 2026
- Then: "Decomposing into 3 biddable tasks..."

### Screen 3: Task Decomposition View (NEW — replaces Claude spec)
- Show 3 task cards side by side (or stacked on mobile):
  1. Aerial LiDAR Topo Survey — 80 acres, ±0.05 ft, $20,000 budget
  2. GPR Subsurface Scan — 6.6 miles of pavement, $15,000 budget
  3. Pavement Core Sampling — 10 locations/mile, $10,000 budget
- Each card shows: task_index "Task 1 of 3", sensors needed, bundling: independent
- "3 tasks extracted · each independently biddable"
- "Connect payment to start auctions" button → payment screen

### Screen 4: Payment (keep existing, update copy)
- Same $10K credit bundle flow
- Copy: "Fund your account to start 3 auctions"

### Screen 5: Parallel Auctions (NEW — replaces single auction)
- Three auction panels running simultaneously (or sequentially animated):
  - Task 1: SkyVista Survey bids $14,200 (aerial) vs Desert Drone Works $16,800
  - Task 2: GroundTruth Robotics bids $12,500 (GPR) — only bidder
  - Task 3: No robot bids (pavement coring is manual) — flagged
- Winners highlighted per task
- "2 of 3 tasks awarded · 1 requires manual vendor"

### Screen 6: Results Dashboard (NEW — replaces single result)
- Aggregated view:
  - RFP: US-131 Resurfacing Survey
  - 2 tasks awarded to robots, 1 flagged for manual vendor
  - Total robot cost: $26,700 (vs $45,000 budget = 41% savings)
  - Estimated completion: 2 weeks
- Per-task result cards with status:
  - Task 1: Awarded → SkyVista Survey · $14,200 · est. 3 days
  - Task 2: Awarded → GroundTruth Robotics · $12,500 · est. 2 days
  - Task 3: No bids — "Pavement coring requires manual crew. Contact a vendor."
- "Download all deliverables" / "Add to Claude" / "Upload another RFP"

## Implementation Notes
- Use the existing mdot-highway-rfp.txt as the pre-loaded sample
- The processing animation is purely visual (timed reveals)
- Task decomposition is hardcoded for the demo (3 specific tasks)
- Auctions are animated sequentially with staggered timing
- The "no bids" task demonstrates the marketplace's honesty about gaps
