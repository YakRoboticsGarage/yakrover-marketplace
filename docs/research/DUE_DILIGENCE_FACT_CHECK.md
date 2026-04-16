# Due Diligence Fact Check — Partner Brief (yakrobot.bid/memo)

**Date:** 2026-04-16
**Method:** Three independent agents (market analyst, legal/regulatory expert, VC investor) reviewed all claims.

---

## Critical Issues (fix immediately)

### 1. Legal positioning contradicts internal research (HIGH)
**Brief says:** "The platform is positioned as a data-acquisition procurement layer, not a surveying firm" (referencing FlyGuys/Aerotas model).
**Internal research says (R-045):** "YAK is positioned as a surveying services procurement platform, not a data acquisition infrastructure provider for licensed firms. In enforcement-prone states (NC, OR, TX, NY), this positioning invites board scrutiny."
**Problem:** The brief presents a legal positioning the team's own research says is not yet implemented. A partner doing diligence who reads both documents will see the contradiction.
**Fix:** Either restructure the platform to match the FlyGuys model, or rewrite the brief to accurately describe the current positioning and the plan to evolve it.

### 2. Wrong case citation link (MEDIUM-HIGH)
**Brief links to:** Justia case 23-1506 (a different case, decided May 7, 2024)
**Actual case:** 23-1472 (360 Virtual Drone Services v. Ritter, decided May 20, 2024)
**The team's own R-007b has the correct citation.**
**Fix:** Update the Justia URL to the correct case number.

### 3. MDOT tolerances internally inconsistent (MEDIUM-HIGH)
**Memo says:** Section 205.03.N: subgrade ±1 inch
**Pitch deck says:** Section 205.03.N: subgrade ±0.75 inches (without subbase)
**Problem:** Two different values for the same section in different documents. One says "verified against source documents." An MDOT engineer would catch this immediately.
**Fix:** Verify against the actual 2020 MDOT Standard Specifications PDF and use one consistent value.

---

## Misleading Claims (should be rewritten)

### 4. "$8 billion per year US market" — category broadening
IBISWorld's "Surveying & Mapping Services" (NAICS 54137) includes oil/gas, environmental, cadastral, and GIS — not just construction surveying. Construction surveying is a subset. The actual addressable market for robotic construction survey is a fraction of $8B.
**Fix:** Either cite the broader category accurately ("$8B surveying and mapping services market") or narrow to the construction-specific segment with a clear source.

### 5. "$31 billion per year to rework" — cherry-picked sub-figure
The PlanGrid/FMI study headline is $177.5B total. The $31B is a sub-category (poor project data + miscommunication). Presented without context, a reader who checks finds $177B and wonders what happened.
**Fix:** Either cite as "$31 billion in rework attributable to poor data" (with the $177B context) or use the full figure.

### 6. "DroneDeploy operates docked drones on 100+ projects" — conflation
DroneDeploy is primarily a software platform. "Docked drones" likely refers to a Skydio partnership/integration, not DroneDeploy operating hardware.
**Fix:** Rewrite as "DroneDeploy's dock automation integrates with autonomous drone platforms on 100+ projects" or cite the specific Skydio partnership.

### 7. Japan i-Construction "86% ICT adoption" — narrow definition
The 86% refers to qualifying large public earthwork projects using at least one ICT method (GPS grading, drone survey). Not 86% of Japan's construction industry.
**Fix:** Add qualifier: "86% adoption on qualifying public earthwork projects."

### 8. NIST $15.8B — 22 years old, no inflation adjustment
The 2004 study measured in 2002 dollars. Inflation-adjusted: ~$27-28B in 2026 dollars. No follow-up study exists.
**Fix:** Either adjust for inflation or note the year: "$15.8 billion per year in 2002 dollars (NIST, 2004)."

### 9. "Robotics insurance does not yet cover AI-mediated missions" — oversimplified
Coverage exists but is not standardized. SkyWatch, Global Aerospace, and AXIS write policies for increasingly autonomous operations. The accurate statement is that standard Part 107 policies don't cover fully autonomous operations.
**Fix:** Rewrite as "Standard commercial drone policies are written for piloted operations. Coverage for fully autonomous missions is available but not standardized."

### 10. ACEC "51% turning down work" — likely distorted
ACEC surveys ask about difficulty filling positions and capacity constraints, not specifically "turning down work." The wording is likely embellished.
**Fix:** Check the actual Q4 2024 report wording and match it precisely.

---

## Weak Analogies (should be reconsidered)

### 11. Airbnb cold-start analogy
Airbnb's supply is spare bedrooms ($0 marginal cost, 15-minute onboarding). Robot operators need $30K-$200K equipment, FAA certification, insurance. The supply-side economics are fundamentally different.
**Better framing:** Acknowledge the difference. Reference OpenDoor (capital-intensive supply) or Uber Freight (physical asset matching at scale with $17B bookings) instead.

### 12. Amazon liability analogy
Amazon didn't "accept" liability strategically — courts imposed it (Bolger v. Amazon 2020, McMillan v. Amazon 2021). Amazon adapted messaging after the fact. Also, consumer product liability vs. autonomous drone liability are categorically different risk profiles.
**Better framing:** Describe the actual insurance/liability structure the platform uses rather than borrowing Amazon's story.

### 13. Epic Care Everywhere analogy
Healthcare interoperability works because of HIPAA, HL7/FHIR standards, and $35B in HITECH Act incentives. Construction has none of this infrastructure. Citing Epic proves the problem is hard, not that it's solved.
**Better framing:** Acknowledge healthcare needed regulation + standards + funding. Position the protocol as building the equivalent from scratch in a greenfield domain.

### 14. "No equivalent exists" — competitors exist
Uber Freight ($17B bookings), Convoy/Flexport, DroneDeploy, Measure (acquired by AgEagle). The space is not greenfield. Algorithmic physical-world procurement is a proven category.
**Better framing:** Name the competitors and explain why construction robotics procurement has unique characteristics (credentialing, deliverable verification, multi-modal coordination) that existing platforms don't address.

---

## Unverifiable Claims (should be flagged or removed)

### 15. Komatsu "35,000 sites"
No Komatsu press release confirms this specific number. Official materials reference "tens of thousands" without precision. The number could refer to different things (GPS-equipped machines vs. integrated SMARTCONSTRUCTION deployments).

### 16. Ukraine "24,500 frontline missions"
Wartime statistics from a belligerent, reported by Scripps from Ukrainian government sources. Unverifiable by independent parties.

### 17. Epic "100 million exchanges per month"
Private company, no independent audit. Appears in Epic marketing materials only.

---

## What's Actually Solid

- FAA Part 108 / EO 14307 regulatory knowledge: correct
- 4th Circuit ruling understanding (per R-007b): deep and accurate
- NIST interoperability study: real, well-cited (just old)
- McKinsey digitization ranking: real, widely cited
- PlanGrid/FMI study: real study, real numbers (just needs context)
- Stripe integration philosophy: valid principle
- Team bios: verifiable, accurate
- Protocol architecture (auction engine, ERC-8004, settlement): functional and demonstrable

---

## Priority Actions

1. Fix the Justia case link (wrong case number)
2. Rewrite the legal positioning paragraph to match R-045's findings
3. Add qualifiers to the misleading statistics ($8B scope, $31B context, NIST date)
4. Replace or qualify the Airbnb/Amazon/Epic analogies
5. Address competitors (Uber Freight, DroneDeploy) instead of claiming greenfield
6. Verify MDOT tolerance values against the actual spec
