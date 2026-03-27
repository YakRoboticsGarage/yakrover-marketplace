# UX Design Critique

**Reviewer:** Senior UX (product studio perspective)
**Date:** 2026-03-27
**Artifact:** `demo/index.html` (static clickthrough prototype)
**Spec reference:** `docs/FRONTEND_DESIGN_SPRINT.md` (Sarah v2 user story)

---

## Overall Assessment

The demo successfully proves the core "intent before identity" flow in six screens, and the live feed gives the landing page a heartbeat that most B2B tools lack. However, the visual language (dark theme, electric cyan, monospace type, grain overlay) reads as a developer monitoring dashboard, not a trustworthy enterprise service that a facilities manager would hand her corporate card to. The prototype also has several dead-end interactions and hardcoded responses that mask real flow gaps -- most critically, the parsed intent screen is static regardless of input, and there is no back-navigation or error recovery at any step.

---

## Flow Issues

1. **The parsed intent card is always the same regardless of input.** If Sarah types "Photo of loading dock," she still sees "Task Type: Sensor Reading / Sensors: Temperature, Humidity." This instantly breaks trust -- the demo claims "We Understood" and then shows something unrelated to what she typed. **Fix:** Map each example query to a distinct parsed-card payload. For freeform input, at minimum echo back extracted keywords and show a "refining..." skeleton state before revealing the card.

2. **No back navigation anywhere.** Once Sarah clicks "Connect Claude," she cannot return to edit her query. Once she chooses Stripe, she cannot switch to USDC. The browser back button does nothing (single-page, no history state). **Fix:** Add a persistent breadcrumb or step indicator (Intent > Claude > Payment > Auction > Result) with clickable earlier steps. Push history state on each screen transition so the browser back button works.

3. **"Operator Login" is a dead link.** It is the only navigation element besides the logo, positioned where users expect account access. Clicking it does nothing, which signals "broken site." **Fix:** Either remove it entirely from the demo, or wire it to a lightweight modal explaining operator access is coming. If it must stay, make it visually inert (no hover state, add "Coming soon" tooltip).

4. **USDC payment path skips the card mock but has no wallet-connect simulation.** Clicking "Pay with USDC" jumps straight to "$25.00 USDC deposited from wallet" with no intermediate step. This is jarring compared to the Stripe path, which shows a card form. **Fix:** Show a brief "Connecting wallet..." state with a WalletConnect-style QR or wallet-selection mock, then resolve to the confirmation.

5. **No confirmation before starting the auction.** After payment, Sarah clicks "Start Auction" and is immediately in the auction -- there is no "Review your task before we go live" summary that combines the spec + payment into a final check. The design spec (step 5) implies the auction starts automatically, but the demo adds a manual button without a review gate. **Fix:** Show a compact summary card (task + payment method + budget) with a prominent "Start Auction" CTA, or auto-start with a 3-second countdown the user can cancel.

6. **"Download Data" and "View Receipt" use `alert()`.** These produce raw text in a system dialog, which on mobile is especially bad. **Fix:** Replace with a slide-down panel or modal that renders the JSON/receipt in a styled card with a "Copy to clipboard" button.

7. **"Hire Again" resets the entire demo including payment.** In production, Sarah already has a credit balance. Resetting payment state means she would re-buy the $25 bundle. **Fix:** "Hire Again" should return to the landing screen with the credit balance visible in the header, and skip the payment screen on the next run-through.

8. **Robot cards on the landing page are not interactive.** They look clickable (hover lift, pointer cursor implied by the lift animation) but do nothing. Sarah will click Rover-A expecting to see its profile or hire it directly. **Fix:** Either make them link into a pre-filled search ("Hire Rover-A for...") or remove the hover-lift affordance and mark them as purely informational.

9. **The "Add to Claude" button reveals raw JSON config.** For Sarah, a facilities manager, `mcpServers` and `Authorization: Bearer YOUR_TOKEN` is intimidating and meaningless. **Fix:** Replace with a one-click "Install in Claude Desktop" deep-link button, and hide the JSON behind an expandable "Advanced / manual setup" toggle.

10. **No empty state or error handling for search.** Submitting an empty query is silently blocked, but there is no visual feedback. Submitting gibberish proceeds as if it were a valid task. **Fix:** Show inline validation ("Tell us what you need -- try 'temperature reading in Bay 3'") for empty/too-short input. For unrecognizable input, show the intent screen with a "We couldn't parse this -- can you add more detail?" state.

---

## Visual Hierarchy Issues

1. **The hero heading "What do you need?" is too lightweight.** At `font-weight: 300` it barely registers against the dark background. The question mark is styled in a muted color, splitting a 4-word headline into two visual weights for no clear reason. **Fix:** Use weight 500 or 600. Drop the `<span>` on the question mark -- it should not be de-emphasized.

2. **Three sections compete equally on the landing page.** The search bar, live feed, and robot grid all occupy similar visual weight. The feed and robot cards are interesting social proof, but they pull attention away from the primary action (search). **Fix:** Increase vertical spacing above the feed. Consider collapsing robot cards into a single summary line ("3 robots online near Helsinki") that expands on click, keeping the hero + search dominant.

3. **Example queries under the search bar are too small and read as a paragraph.** At `0.72rem` monospace with middot separators, they form a dense line that is easy to miss and hard to parse. **Fix:** Replace with pill-shaped chips (like Google's search suggestions) at a readable size (0.8-0.85rem, system font). Use 2 rows max, 2-3 chips per row. Each chip should look tappable -- rounded rect with a subtle border, not inline text.

4. **The spec card on Screen 3 uses code-style formatting for non-technical content.** Colons, monospace, colored values -- this is a terminal output aesthetic. Sarah does not think in key-value pairs. **Fix:** Present the structured spec as a clean table or card with labeled rows (like Screen 2's parsed card, which is actually better). Use the same component for consistency.

5. **Score bars in the auction screen lack numeric values.** The bars fill to a percentage but the actual score number is not displayed. Sarah sees four unlabeled colored bars and has no idea what 92% vs 72% means in context. **Fix:** Add the numeric percentage at the end of each bar. Better yet, show a single composite score prominently and collapse the breakdown behind a "See scoring details" toggle.

6. **The payment screen headline "Choose payment method" has no task context.** Sarah has navigated through 3 screens and now sees a payment form with no reminder of what she is paying for. **Fix:** Add a compact task summary at the top of the payment screen: "Sensor reading, Bay 3 -- est. $0.25-$0.80" so she knows the $25 credit bundle is not the task price.

7. **Footer links (MCP endpoint, OpenAPI, GitHub) are developer-facing.** Sarah does not need these. They dilute the enterprise trust signal. **Fix:** Move technical endpoints to a /developers page. Keep the footer minimal: company name, terms, privacy, support contact.

---

## Copy Issues

1. **"We Understood" (Screen 2 heading).** Grammatically awkward and presumptuous -- the system is claiming perfect comprehension. **Fix:** "Here's what we got" or "Your request, parsed" -- something that invites correction rather than asserting completeness.

2. **"Connect your AI assistant."** Sarah may not think of Claude as "her AI assistant." If she has never used Claude, this is confusing. **Fix:** "Connect Claude to refine your request and manage the auction." Name the product. Explain the benefit in the same sentence.

3. **"$25 credit bundle -- use credits across multiple tasks."** This raises an immediate question: what if I only want one $0.35 reading? Forcing a $25 minimum buy is a major conversion barrier and the copy does not address it. **Fix:** Acknowledge the gap: "Credits don't expire. Your first task will cost ~$0.35 -- the rest stays in your account for future use." Or better, offer pay-per-task for the first interaction.

4. **"Clarifies details / Sets accuracy / Manages auction"** (feature pills under Connect Claude). These are feature labels, not benefits. "Sets accuracy" means nothing to Sarah. **Fix:** Rewrite as benefits: "Asks the right follow-up questions / Picks the best robot for your budget / Handles the whole process."

5. **"payment: pending connection"** (Screen 3 spec card). Reads like a system status log, not a user-facing message. **Fix:** "Payment: not yet connected" or simply omit this line until payment is actually connected.

6. **"Powered by the Robot Task Auction Protocol"** (footer). Jargon. Sarah does not care about the protocol name. **Fix:** "Powered by YAK Robotics" or remove entirely.

7. **Robot names "Rover-A," "Rover-B," "Drone-C."** These are inventory IDs, not names that build trust. The spec uses "Ground Rover A" which is marginally better. **Fix:** Give robots human-readable names or at least descriptive labels: "Bay 3 Rover" or "Warehouse Sensor Unit #1." The ID can appear as a secondary label.

8. **"best composite score"** (winner badge). Enterprise users do not think in composite scores. **Fix:** "Best match for your task" or "Closest, cheapest, most reliable."

---

## Mobile Issues

1. **Example query chips will wrap into a dense block on small screens.** The inline text with middot separators becomes unreadable below 400px. **Fix:** Switch to horizontally scrollable pill chips with `overflow-x: auto` and no wrapping.

2. **The 900px max-width container is fine, but there is no responsive typography scaling below 375px.** The `clamp()` on h1 helps, but monospace labels at 0.62-0.72rem will be illegible on small Android devices. **Fix:** Set a floor of 0.75rem for any user-facing text. Reserve sub-0.75rem for truly optional metadata.

3. **The payment options grid collapses to single column (good), but the card mock form has no mobile-specific input formatting.** The "4242 4242 4242 4242" card number has no `inputmode="numeric"` or mobile card-entry pattern. **Fix:** Use `inputmode="numeric"` and proper autocomplete attributes on real card inputs. For the demo mock, this is cosmetic, but flag it for production.

4. **The bid-grid 2-column layout on desktop becomes 1-column on mobile, but the score bars are already dense.** On a phone, Screen 5 will be very long -- two full bid cards with 4 score bars each, plus a progress bar. **Fix:** On mobile, show only the winning bid expanded and collapse the losing bid into a single summary line: "Rover-B also bid: $0.55, 91% -- not selected."

5. **The ticker-style mini-feed uses `translateX` animation with fixed timing.** On narrow screens, the text is cut off and the animation speed feels wrong relative to the visible width. **Fix:** Use a CSS custom property for animation duration based on content length, or replace the ticker with a static "Last activity: Rover-A completed reading, 42s ago" on mobile.

6. **Touch targets on example queries are too small.** The `<em>` elements have no padding -- the tap target is just the text bounding box, well under the 44px minimum. **Fix:** Wrap each example in a padded, tappable chip component.

7. **The ambient gradient blurs (600px circles) may cause performance issues on low-end mobile devices.** A 600px element with `filter: blur(180px)` is GPU-intensive. **Fix:** Reduce blur radius on mobile via media query, or replace with a static radial gradient background.

---

## Top 10 Changes (prioritized by impact)

1. **Replace the dark/cyan/amber developer aesthetic with a neutral light theme.** Use a white or warm-gray background, dark text, and a single accent color (blue or teal at moderate saturation). Think Stripe Dashboard, not a terminal. This is the single biggest barrier to enterprise trust.

2. **Make the parsed intent screen dynamic based on actual input.** Map example queries to distinct payloads. Show a skeleton/loading state for freeform input. Never show "We Understood" with content that contradicts what the user typed.

3. **Add step indicator and back navigation.** A horizontal stepper (What > Claude > Pay > Auction > Done) gives Sarah orientation and escape routes. Push browser history on each transition.

4. **Redesign example queries as tappable pill chips.** Replace the monospace inline text with rounded-rect chips at a readable size, horizontally scrollable on mobile, each with adequate touch targets.

5. **Add a task context summary to the payment screen.** Show what Sarah is buying (sensor reading, Bay 3) alongside the $25 credit bundle, and address the "why $25 for a $0.35 task?" objection directly in copy.

6. **Rewrite all copy for Sarah, not for developers.** Specifically: "We Understood" heading, "Sets accuracy" feature label, "best composite score" winner badge, "payment: pending connection" status, and footer protocol name.

7. **Simplify the auction scoring UI.** Show a single "match score" per robot with one bar. Hide the 4-factor breakdown behind a toggle. Add numeric values to all bars.

8. **Replace alert()-based data/receipt views with styled inline panels.** Use expandable cards with copy-to-clipboard, not system dialogs.

9. **Hide the raw MCP JSON behind "Advanced setup."** The default "Add to Claude" action should be a one-click install link. Show the JSON config only on explicit request.

10. **Fix the Operator Login dead end.** Either remove it, wire it to a "coming soon" modal, or implement a basic login flow. A dead link in the header is the first thing a skeptical evaluator will click.
