# PLS signature automation: options for removing manual labor from the service flow

---

## The question

Every construction survey deliverable that a GC uses for design or bid quantities needs a PLS (Professional Land Surveyor) stamp. This is the single manual step in an otherwise automatable pipeline. Can it be eliminated, reduced, or automated?

## The short answer

The stamp itself can be digital. The review behind it cannot be fully automated. But the review can be structured, accelerated, and priced as a service within the marketplace.

---

## What Michigan law requires

MCL 339.2007 defines:
- "Electronic seal" — a seal created by electronic or optical means and affixed electronically
- "Electronic signature" — a signature created by electronic or optical means with intent to sign

Michigan explicitly permits digital PLS seals on survey deliverables. The PLS does not need to physically stamp a piece of paper. A digital seal applied via DocuSign, Adobe Sign, or a custom API is legally valid.

The statute requires the PLS to "apply his or her seal and signature to a plan, specification, plat, or report that is issued by the licensee." The key word is "issued by" — the PLS must have professional responsibility for the work product, not merely stamp someone else's output.

Source: [MCL 339.2007](https://www.legislature.mi.gov/Laws/MCL?objectName=mcl-339-2007), [Michigan LARA Surveyor FAQ](https://www.michigan.gov/-/media/Project/Websites/lara/bpl/Surveyors/Surveyor-FAQ.pdf)

## Five options for handling PLS within the marketplace

### Option 1: Operator brings their own PLS (current model)

The operator has a PLS on staff or under contract. The marketplace verifies the PLS license but does not provide the stamp. The PLS reviews and stamps the deliverables before they're submitted through the platform.

**Manual labor:** PLS reviews each deliverable (30 min to 2 hours depending on complexity).
**Who pays:** The operator bakes PLS cost into their bid price.
**Automation:** None — the PLS is fully external to the marketplace.
**Risk:** Operators without a PLS arrangement can't bid on tasks that require stamped deliverables.

### Option 2: Marketplace PLS network ("PLS as a service")

The marketplace maintains a network of contracted PLSs in each state. When a task requires a stamped deliverable, the marketplace routes the completed data to an available PLS for review and stamping. The PLS cost is a line item on the invoice.

**Manual labor:** PLS reviews each deliverable (same as Option 1, but the marketplace manages the routing).
**Who pays:** The buyer, as a separate line item ($200-$500 per review depending on complexity).
**Automation:** The routing, scheduling, and payment are automated. The review itself is human.
**Advantage:** Any operator can bid — even without their own PLS. The marketplace supply grows.
**Risk:** The PLS must actually review the work, not rubber-stamp it. "Stamp mill" arrangements violate licensing law and expose the marketplace to liability.

This model exists in practice. Companies like Partner ESI and similar survey coordination firms match field crews with remote PLSs for review. Remote PLS review is standard for drone survey data where the PLS reviews processing logs, accuracy reports, and spot-checks the deliverables.

### Option 3: AI-assisted PLS review (reduce review time)

The marketplace builds a QA tool that pre-screens deliverables before the PLS sees them. The tool checks:
- Point density meets spec
- Accuracy (RMSE) meets the task requirement
- Coordinate system and datum are correct
- File formats are valid (LandXML schema, DXF layer structure)
- Cross-sections are at the specified interval
- No obvious data gaps or artifacts

The PLS then reviews the QA report + spot-checks the data, rather than reviewing from scratch. This could reduce review time from 1-2 hours to 15-30 minutes.

**Manual labor:** PLS reviews QA report and spot-checks (15-30 min).
**Who pays:** Platform absorbs QA tool cost; PLS review still charged to buyer.
**Automation:** 60-70% of the review work is automated. The PLS still makes the professional judgment call and applies the stamp.
**Advantage:** Faster turnaround. Lower PLS cost per review. More reviews per PLS per day.
**This maps directly to skill #6 (deliverable-validator) and #14 (capture-qc) from our skill candidates.**

### Option 4: Electronic seal via API (automate the stamp application)

Once the PLS approves, the actual application of the seal can be automated. DocuSign offers an Electronic Seal API that programmatically applies a certified seal to a document. The flow:

1. Operator uploads deliverables to marketplace
2. QA tool pre-screens (Option 3)
3. PLS reviews QA report in a web dashboard, clicks "approve"
4. System applies the PLS's digital seal via API (DocuSign, DocuSeal, or custom)
5. Stamped deliverable is delivered to the buyer

The PLS never handles the file directly. They review a dashboard, make a judgment, and click approve. The seal application is instant and automated.

**Manual labor:** PLS clicks "approve" after reviewing dashboard (5-15 min).
**Automation:** The seal application is fully automated. The professional review is streamlined to a dashboard interaction.
**Technical:** DocuSign eSignature REST API supports this. DocuSeal (open source) is an alternative. Custom PKI-based digital seal is also feasible.
**Legal:** Valid in Michigan (MCL 339.2007 permits electronic seals). Valid in most states that have adopted UETA (Uniform Electronic Transactions Act) or E-SIGN Act.

Source: [DocuSign Electronic Seal API](https://www.docusign.com/blog/developers/how-to-certify-your-documents-using-docusign-electronic-seal-api)

### Option 5: Platform employs PLSs directly (vertical integration)

The marketplace hires PLSs as W-2 employees or dedicated contractors. Every deliverable gets reviewed and stamped in-house. The operator never needs a PLS arrangement.

**Manual labor:** Same as Option 2, but the PLS is an employee.
**Who pays:** Built into the platform take rate (no separate line item for the buyer).
**Advantage:** Complete control over quality. Fastest turnaround. Simplest operator experience.
**Risk:** Expensive ($80-120K/yr per PLS). Need one per state (PLS licenses are state-specific). The platform becomes a professional services firm, not just a marketplace.

---

## What cannot be automated (the legal line)

A PLS stamp represents professional judgment. The PLS attests that:
- The survey was conducted to the applicable standard of care
- The data is accurate within the stated tolerances
- The deliverables are suitable for their intended use

This judgment cannot be delegated to an AI. No state licensing board accepts automated stamping without a licensed professional's review. The PLS must:
1. Be licensed in the state where the project is located
2. Have supervisory responsibility for the work
3. Actually review the deliverables (not rubber-stamp)
4. Accept professional liability (their E&O insurance covers errors)

The NSPS (National Society of Professional Surveyors) standard requires the PLS to confirm RMSE of checkpoints meets the project accuracy requirement and document the positioning method used. This is a professional judgment call, not a checkbox.

---

## Recommendation for the marketplace

**Phase 1 (v1.5-v2.0): Option 1 + Option 3**
Operators bring their own PLS. The marketplace builds the QA tool (deliverable-validator skill) that pre-screens data, reducing PLS review time. This accelerates the flow without the marketplace taking on PLS liability.

**Phase 2 (v2.0-v2.5): Option 2 + Option 4**
Launch the PLS network. Contract with 3-5 PLSs in Michigan, Ohio, and surrounding states. Build the electronic seal integration (DocuSign API or DocuSeal). Operators without a PLS can now bid — supply grows. The PLS reviews a dashboard, clicks approve, seal is applied automatically. Total PLS touchpoint: 15 minutes per deliverable.

**Phase 3 (v3.0+): Consider Option 5**
If PLS review becomes the bottleneck at scale, consider hiring PLSs directly. This only makes sense at 50+ reviews per month when dedicated staff is cheaper than per-review contracts.

**The fully automated endpoint that eliminates all manual labor does not exist under current law.** The closest achievable state is: AI pre-screens the data (automated), PLS reviews a dashboard and clicks approve (5-15 min human input), seal is applied via API (automated), deliverable is delivered (automated). Total human time per task: 5-15 minutes.

---

Sources:
- [MCL 339.2007 — Seal; signature](https://www.legislature.mi.gov/Laws/MCL?objectName=mcl-339-2007)
- [Michigan LARA Surveyor FAQ](https://www.michigan.gov/-/media/Project/Websites/lara/bpl/Surveyors/Surveyor-FAQ.pdf)
- [DocuSign Electronic Seal API](https://www.docusign.com/blog/developers/how-to-certify-your-documents-using-docusign-electronic-seal-api)
- [DocuSeal — Open Source Document Signing](https://www.docuseal.com/)
- [Oregon OSBEELS — Seals and Signatures](https://www.oregon.gov/osbeels/maintaining/pages/seals-and-signatures.aspx)
- [Texas PELS — Sealing Procedures](https://www.law.cornell.edu/regulations/texas/22-Tex-Admin-Code-SS-138-33)
- [50-State Survey of Stamping/Sealing Obligations (Baker Donelson)](https://www.bakerdonelson.com/webfiles/Bios/50StateSurveyofLicensedDesignProfessionalStampingandSealingObligations.pdf)
- [RPLS Forum — Working Remotely as a Professional Surveyor](https://rpls.com/forums/strictly-surveying/working-remotely-as-a-professional-surveyor/)
- [Commercial Drone Pilots Forum — Licensed Surveyors vs UAS Operators](https://commercialdronepilots.com/threads/licensed-surveyors-vs-uas-operators-offering-mapping-and-related-services.3510/)
