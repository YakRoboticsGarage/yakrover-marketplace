# Product Critique: Robot Task Marketplace Demo

**Reviewer perspective:** B2B SaaS product manager (Stripe Dashboard, Datadog, Linear)
**Date:** 2026-03-27
**Artifact reviewed:** `demo/index.html` + `docs/USER_JOURNEY_MARKETPLACE_v01.md`

---

## Overall Assessment

This demo is a technically impressive proof-of-concept that would impress engineers and robotics enthusiasts but would lose an enterprise buyer like Sarah (or more importantly, Sarah's IT admin and procurement team) within the first 10 seconds. The landing page leads with "What do you need?" -- a consumer marketplace pattern -- instead of communicating the value proposition, and the 6-screen linear flow buries the payoff (a $0.35 sensor reading in 42 seconds) behind a payment wall and auction animation that no enterprise buyer asked to watch. The user journey doc tells a compelling 42-second story; the demo takes 3+ minutes and six clicks to tell the same story.

---

## Value Proposition Issues

1. **No headline value prop.** The hero says "What do you need?" -- this is a search bar, not a pitch. Sarah's VP of Operations landing here has no idea what this product does or why they should care. **Fix:** Replace with a headline like "Sensor readings from autonomous robots. 42 seconds. $0.35." followed by a subhead: "Your AI assistant posts the task. Robots bid. You get the data." The search bar moves below.

2. **The 42-second story is invisible.** The user journey doc's killer stat -- temperature reading in 42 seconds for $0.35 -- is the single most compelling thing about this product. It appears nowhere on the landing page. **Fix:** Lead with it. A concrete before/after ("Before: email the facilities team, wait 2 hours. After: ask Claude, get data in 42 seconds") is worth more than any animated feed.

3. **"Robot Task Marketplace" means nothing to Sarah.** The meta description says "real-time auctions" -- Sarah does not want auctions, she wants sensor data. The product is being described in terms of its mechanism (auctions, bids, scoring) instead of its outcome (instant facility data on demand). **Fix:** Reframe all copy around outcomes. "On-demand facility sensing" or "Instant sensor data from autonomous robots" -- not "robot task auctions."

4. **No use cases section.** The example queries ("Humidity check Bay 3", "Photo of loading dock") are tiny monospaced text under the search bar. An enterprise buyer needs to see 3-4 concrete use cases with outcomes and price ranges front and center: HVAC compliance monitoring, loading dock inspections, air quality audits, inventory spot checks. **Fix:** Add a "Use Cases" section with cards showing task type, typical cost, typical time, and a sample result.

5. **The auction visualization is a liability, not an asset.** Enterprise buyers do not want to watch robots compete in real time. They want a result. The 8-second auction animation with score bars and "Collecting bids..." spinners is optimized for a demo day audience, not a procurement decision. Sarah's user journey explicitly says "The Auction (Sarah doesn't see this)." The demo makes her watch every second of it. **Fix:** Collapse the auction into a 2-second transition with a summary card ("Rover-A selected -- closest, fastest, cheapest"), and put the detailed scoring behind a "Show details" toggle for technical evaluators.

---

## Trust & Safety Issues

1. **Zero enterprise trust signals.** No SOC 2 badge, no GDPR mention, no data processing agreement link, no uptime SLA, no mention of where data is stored or who owns it. An enterprise buyer's security team would reject this on sight. **Fix:** Add a "Trust & Security" section or footer row with: SOC 2 Type II (even if "in progress"), GDPR-compliant, data ownership ("you own your data"), 99.9% uptime SLA, and a link to a security whitepaper.

2. **No company information.** "YAK ROBOTICS" with a GitHub link. No "About" page, no team, no physical address, no legal entity. Enterprise procurement requires knowing who they are contracting with. **Fix:** Add a minimal About section: company name, jurisdiction, contact email, and a brief "who we are" blurb.

3. **Payment page shows test card number.** The mock card `4242 4242 4242 4242` is a Stripe test artifact. Showing this to an enterprise buyer signals "this is not production software." **Fix:** In a demo, show a branded checkout experience (Stripe Elements-style) with placeholder fields, not pre-filled test data.

4. **No refund or dispute policy.** What happens if the robot returns bad data? The user journey mentions verification, but the demo has no indication that results are validated or that there is any recourse. **Fix:** Add a "Satisfaction guarantee" or "Verified results" badge on the result screen, with a link to dispute/refund policy.

5. **USDC option on the same screen as corporate Amex.** Offering crypto payment alongside card payment is a red flag for enterprise procurement. It raises questions about regulatory compliance and suggests the product is aimed at crypto-native users, not facilities managers. **Fix:** For the enterprise demo, lead with card payment. Crypto should be a separate configuration option in account settings, not a choice at checkout. Or at minimum, label it clearly as "For robot operators" vs. "For enterprise customers."

6. **No indication of robot operator vetting.** Who owns these robots? Are they insured? Are they certified for warehouse operation? Sarah's company has liability concerns. **Fix:** Add robot operator verification badges ("Verified Operator", insurance status, certification level) to robot cards.

---

## Conversion Issues

1. **The biggest drop-off: "Connect Claude" wall.** Screen 2 says "connect your AI assistant" to proceed. This is a hard gate. A first-time visitor who came from a Google search or a colleague's link cannot proceed without Claude. There is no alternative path (no "Continue without AI assistant" or "Try a demo task"). **Fix:** Offer a "Try it now" path that skips the Claude connection and runs a simulated task end-to-end, so the buyer can see the full value before committing to any integration.

2. **$25 mandatory upfront payment before seeing a single result.** The credit bundle purchase happens at step 4 of 6. The user has invested 2+ minutes and still has not seen the product deliver value. In SaaS, you show value first, then ask for payment. Stripe Atlas lets you incorporate before paying. Datadog gives you 14 days free. **Fix:** Offer a free demo task (or a $0.00 sandbox task) that delivers a real result. Then upsell to the credit bundle. Alternatively, let the first $1.00 be free.

3. **Six screens is too many steps.** Landing -> Intent -> Claude Spec -> Payment -> Auction -> Result. That is 6 screens and 5 clicks minimum. Best-in-class B2B products get to value in 1-2 clicks. **Fix:** Collapse to 3 screens maximum: (1) Landing with value prop, (2) Task confirmation + payment (combined), (3) Result. The Claude spec and auction details become expandable sections, not mandatory screens.

4. **No "How It Works" explanation.** The demo assumes the user already understands the concept of robots bidding on tasks. A 3-step visual explanation ("Post a task -> Robots bid -> Get your data") should appear on the landing page before the search bar. **Fix:** Add a "How It Works" section with 3 steps, each with an icon and one sentence.

5. **"Add to Claude" on the result page is premature and confusing.** The MCP JSON config is meaningless to Sarah. It is a developer integration artifact shown to a facilities manager. Even for IT admins, showing raw JSON with "YOUR_TOKEN" is not a good onboarding experience. **Fix:** Replace with "Set up automatic tasks" leading to a guided setup wizard. The MCP config should be generated and downloadable after the admin authenticates, not copy-pasted from a tooltip.

6. **No back button or progress indicator.** Once you advance to screen 2, there is no way back except "Hire Again" on the final screen. Users who want to re-read the spec or change their query are stuck. **Fix:** Add a step indicator (1/6 or a breadcrumb) and allow backward navigation.

---

## Missing Elements

1. **Pricing page.** Enterprise buyers need a pricing page they can send to procurement. What does $25 buy? How many tasks is that? What are the price ranges by task type? Is there a monthly plan? Volume discounts? This is table stakes for any B2B product.

2. **Dashboard / account management.** After the first task, where does Sarah go? There is no indication of a dashboard showing task history, credit balance, usage analytics, or team management. The demo ends at a single task result with no sense of ongoing value.

3. **Team and permissions model.** Sarah's user journey mentions an IT admin setting up the account and configuring spending limits. The demo has no concept of teams, roles, or approval workflows. Enterprise buyers need multi-user support with audit trails.

4. **API documentation link.** The footer links to `/api/openapi.json` but for an enterprise buyer, the question is: "Can I integrate this into my facility management system?" There should be a developer docs section or at least a "Built for integration" callout.

5. **SLA and uptime guarantees.** What happens if no robot is available? What is the guaranteed response time? What is the fallback? Enterprise facilities management has compliance deadlines.

6. **Compliance and audit trail.** For HVAC maintenance reports (Sarah's exact use case), the sensor data needs to be traceable, timestamped, and potentially certified. The demo shows raw numbers with no provenance chain or exportable audit record.

7. **Onboarding flow for robot operators.** The "Operator Login" link in the header is a dead end. The marketplace is two-sided -- the supply side (robot operators) has no story at all in this demo. Even if it is out of scope for the buyer demo, a "For Robot Operators" landing page would signal that the marketplace has healthy supply.

8. **Mobile experience.** The demo has some responsive CSS but enterprise facility managers often work from tablets or phones on the warehouse floor. The search-bar-first pattern works on mobile, but the 6-screen flow would be painful on a small screen.

9. **Notifications and scheduling.** Sarah's story is one-shot: ask for a reading, get a reading. But the real value for enterprise is recurring tasks: "Check Bay 3 temperature every morning at 7 AM." There is no indication this is possible.

10. **Competitive comparison or differentiation.** Why this instead of a $50 wall-mounted sensor? Why this instead of asking the facilities intern? The demo does not address the "why now" or "why this approach" question that every enterprise buyer asks.

---

## Top 10 Changes (Prioritized)

1. **Rewrite the landing page hero to lead with value, not a search bar.** Headline: concrete outcome + stat. Subhead: how it works in one sentence. Social proof (task count, companies served). Then the search bar. This is the single highest-leverage change -- it determines whether anyone stays past 5 seconds.

2. **Add a free/sandbox task that delivers a result with zero payment.** Remove the $25 wall from the first-time experience. Let the user see a real (or realistic simulated) result before asking for money. Every successful B2B marketplace (AWS, Twilio, Stripe) lets you try before you buy.

3. **Collapse 6 screens to 3.** Landing -> Confirmation (with inline payment) -> Result. Move Claude spec and auction scoring into expandable detail sections. Reduce clicks from 5 to 2.

4. **Add a "How It Works" section to the landing page.** Three steps, visual, one sentence each. This replaces the current approach of making the user discover the process by walking through it.

5. **Add a pricing page.** Show credit bundles, per-task price ranges by category, and a "Contact Sales" option for volume/enterprise plans. Link it from the landing page nav.

6. **Add enterprise trust signals.** Security section or footer badges: SOC 2, GDPR, data ownership, uptime SLA, encryption in transit/at rest. Even "in progress" certifications are better than silence.

7. **Replace the "Add to Claude" JSON tooltip with a guided setup flow.** The current MCP config dump is developer-facing. Replace with a "Set up your AI assistant" wizard that generates and delivers the config appropriately based on the user's role (admin vs. end user).

8. **Add a result/dashboard page that shows ongoing value.** After the first task, show a dashboard mockup: task history, spending trends, robot performance, and a "Schedule recurring task" button. This shifts the narrative from "one-off tool" to "platform I rely on."

9. **Reframe the auction as invisible infrastructure, not a feature.** Sarah does not care about score bars. Show the outcome ("Rover-A selected -- $0.35, 42s") and let technical users expand the details. The current auction screen is optimized for investor demos, not buyer demos.

10. **Add a "For Robot Operators" section or page.** Even a single section ("Own robots? Earn revenue by joining the marketplace") signals a healthy two-sided marketplace and reassures buyers that supply will be available when they need it.
