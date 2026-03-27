# User Journey: Private Robot Task Hiring (v0.1 -- The Compliant Privacy Path)

> **Version:** 0.1 | **Date:** 2026-03-26 | **Story:** Private
>
> This is the privacy-preserving user journey document for the marketplace story.
> It describes Diane's experience hiring a robot for a classified facility inspection
> where the inspection targets themselves are sensitive.
> For technical implementation details, see `DECISIONS.md`, `SCOPE.md`, and `research/RESEARCH_SYNTHESIS_PRIVATE.md`.
> See also: `USER_JOURNEY_MARKETPLACE_v01.md`, `USER_JOURNEY_LUNAR_v01.md`.

---

## Meet Diane

Diane is a program manager at a defense contractor in Helsinki. She holds a Finnish security clearance (KATAKRI level III) and manages physical security inspections across three classified facilities. She uses an AI assistant for scheduling and vendor coordination, but every tool she touches goes through her company's security review board first. She has a corporate procurement card with pre-approved spend authority up to EUR 500 per task category.

Diane has never heard of TEE attestation, BBS+ credentials, or delegated ZK proving. She never will. What she knows is this: the inspection targets in her facilities are classified, and any service that can see what she inspects, where she inspects it, or what the results say is a service she cannot use.

Today, Diane needs a structural vibration reading from Corridor 7-East in Facility Bravo. The inspection target is classified. She is going to get the reading in 55 seconds, from a robot that never learns what it was really looking for, for $0.42.

---

## One-Time Setup (15 minutes, once)

Before Diane ever submits a private task, her company's IT security team sets up the account. This happens once.

1. **Diane's IT security officer visits the platform dashboard** and links the corporate procurement card. The officer also uploads the organization's public key for encrypted task storage.
2. **The officer purchases a EUR 200 credit bundle** -- a single line item on the procurement card statement: `YAK ROBOTICS MARKETPLACE EUR 200.00`. No mention of privacy, encryption, or classified work.
3. **The officer enables "Private Tasks" for Diane's account.** This generates a viewer key pair: Diane's CFO receives a viewer key that can decrypt per-task detail for internal audit. The platform holds an escrow key accessible only on lawful regulatory request.
4. **Diane's AI assistant is connected to the platform.** The officer pastes an API key into the assistant's configuration. The assistant is authorized to spend up to EUR 50 per task, auto-approving anything under EUR 10. All task specs submitted by the assistant are encrypted by default.

That is it. Diane has EUR 200 in platform credits, her task specs are encrypted at rest, and her CFO can audit any task she runs. No blockchain wallet, no crypto onboarding, no separate privacy tool. The privacy is in the infrastructure, not in Diane's workflow.

<details>
<summary>Under the hood</summary>

Credits are held in a prepaid wallet on the platform, identical to standard marketplace accounts. The privacy setup adds three things: (1) an organization public key used to encrypt task specs before they leave Diane's assistant, (2) a viewer key pair for internal audit (CFO key decrypts task-level detail; Diane sees her own history), and (3) a platform escrow key stored in a hardware security module, accessible only under a documented legal process. The viewer key architecture follows the selective-disclosure model validated in the research synthesis -- "private from the world, auditable by my CFO."

</details>

---

## Journey A: The Happy Path

**Diane asks for a reading. Two robots compete on capability alone -- neither sees the full task spec. The best one wins. She gets her answer in 55 seconds.**

### The One-Call Path

Under the hood, Diane's assistant uses the same `auction_quick_hire` tool as any marketplace user, but with the `privacy: true` flag set by her account configuration. The assistant encrypts the task spec, posts a public capability vector for matching, and the platform handles encrypted matching, scoring, and proof generation inside its TEE infrastructure. Diane's workflow is identical to Sarah's.

### The Request

**10:02 AM** -- Diane types a message to her AI assistant:

> "I need a structural vibration reading from Corridor 7-East in Facility Bravo. Standard sensor placement, report format B-7."

The assistant responds immediately:

> "On it. Checking for available robots with vibration sensors near Facility Bravo. Your task spec is encrypted -- only the winning robot will receive the full details. Back in a moment."

Diane goes back to her inspection schedule. She did not ask for encryption, did not toggle a privacy setting, did not think about threat models. The assistant told her the spec is encrypted because her account is configured that way. That one sentence is the entire privacy UX.

<details>
<summary>Under the hood</summary>

The assistant translates Diane's request into a structured task specification: sensor type (accelerometer, minimum 16-bit resolution), location coordinates (Corridor 7-East, Facility Bravo), data format (report format B-7), maximum budget (EUR 8.00), and a 15-minute deadline. Before posting, the assistant encrypts this spec with the platform's TEE public key. The encrypted blob is opaque to anyone outside the enclave -- including the platform's own operators.

Separately, the assistant generates a public capability vector: `[vibration_sensor, accelerometer_16bit, facility_bravo_access]`. This vector is intentionally coarse. It says what kind of robot is needed, not what the robot will be inspecting or why. The vector uses generalized capability classes rather than specific parameters to minimize information leakage.

</details>

### The Auction (Diane doesn't see this)

Four robots are registered at Diane's facilities. The platform checks each one against the public capability vector:

- **Robot A** (ground rover, Facility Bravo) -- has a 16-bit accelerometer, authorized for Bravo corridors. Eligible.
- **Robot B** (ground rover, Facility Bravo) -- has a 16-bit accelerometer, authorized for Bravo corridors. Eligible.
- **Robot C** (ground rover, Facility Alpha) -- has a vibration sensor but is not authorized for Facility Bravo. Filtered out.
- **Robot D** (aerial drone, Facility Bravo) -- no vibration sensor. Filtered out.

Robots A and B each submit a bid automatically. Neither robot has seen the full task spec. They are bidding against the capability vector only -- they know a vibration reading is needed somewhere in Facility Bravo, but not which corridor, not what the target structure is, not why the reading matters.

| | Robot A | Robot B |
|---|---|---|
| **Location** | Bravo, Corridor 5 (30m away) | Bravo, Corridor 12 (90m away) |
| **Battery** | 92% | 68% |
| **Price** | EUR 0.38 | EUR 0.62 |
| **Estimated time** | 4 minutes | 7 minutes |
| **Reputation** | 99.1% success (BBS+ credential) | 94.7% success (BBS+ credential) |

The platform scores both bids inside its TEE enclave. The scoring function is the same as the standard marketplace -- price 40%, speed 25%, confidence 20%, track record 15% -- but the track record verification uses BBS+ credentials instead of a public history lookup. Robot A wins: closer, cheaper, faster, and more reliable.

**Robot A now receives the decryption key for the full task spec.** Only now -- after winning the auction -- does it learn the specific corridor, sensor placement instructions, and report format. Robot B never sees any of this.

<details>
<summary>Under the hood</summary>

The auction runs inside the platform's TEE enclave (Intel TDX). The enclave decrypts Diane's task spec, matches it against robot capabilities, scores the bids, and selects a winner. The enclave then generates a single-use decryption key for the winning robot and destroys the losing robots' session context. The entire encrypted matching and scoring process adds approximately 4 seconds to the standard auction time.

The robots' BBS+ reputation credentials are verified without revealing individual task histories. Robot A proves "I have completed 847 tasks with a 99.1% success rate" via a zero-knowledge selective disclosure proof. The platform verifies this claim without learning which 847 tasks, for whom, or what they involved. This is the BBS+ selective disclosure property -- the credential is signed by a distributed issuer set (3 platform nodes using threshold BBS+), so no single node holds the complete issuance history.

</details>

### The Result

**10:02:55 AM** -- 55 seconds after Diane's request, her assistant replies:

> **Corridor 7-East vibration reading complete. Report B-7 attached.**
>
> Measured just now by a ground rover in Facility Bravo. Cost: EUR 0.42 from your platform balance (EUR 199.58 remaining). Two robots competed on capability; the closest one won. Your task spec and results are encrypted -- only you and your organization's auditors can access the details.

Diane opens the attached report, verifies the readings, and files it in the classified inspection system. The 55 seconds included 13 seconds of privacy overhead she never noticed.

<details>
<summary>Under the hood</summary>

The winning robot read its onboard accelerometer at the specified location and returned structured vibration data to the platform. The assistant verified the reading was complete and plausible (vibration frequencies within expected structural range, all requested fields present, delivered on time).

Before confirming delivery, the platform generated a completion proof. The robot's raw results were sent to a delegated ZK prover running inside a TEE-backed service (Succinct Private Proving on Phala Cloud). The prover generated a zero-knowledge proof that the returned data satisfies the original task specification -- correct sensor type, correct location, correct format, values within plausible range -- without revealing the spec or the results to anyone. This proof is stored alongside the encrypted task record.

Payment was settled on Base: EUR 0.42 in USDC debited from Diane's credits, transferred to the robot operator. The on-chain transaction carries only the amount, escrow contract address, and a nonce. The `request_id` linking this payment to Diane's task exists only in the platform's encrypted database -- not on-chain. An external observer sees a USDC transfer but cannot connect it to a vibration reading in Corridor 7-East.

</details>

---

## Journey B: Capability Mismatch Against Encrypted Spec

**Diane asks for something that requires a capability no available robot can prove it has. She is told immediately. No charge. No information leaked.**

**10:15 AM** -- Diane types:

> "I need a millimeter-wave radar scan of the north wall in Chamber 3, Facility Bravo."

The assistant responds within 4 seconds:

> "Sorry, none of the robots at your facilities have a millimeter-wave radar sensor. Your task spec was encrypted and has been discarded -- no robot saw any details. I can help you arrange a specialist contractor, or you can check back when new robots join the network. No charge for checking."

Diane's balance is untouched at EUR 199.58. The capability vector `[mmwave_radar, facility_bravo_access]` was broadcast, but no robot could match it. The encrypted task spec was never decrypted -- no TEE enclave session was opened, because there were no eligible bidders to score. The spec was purged from the platform's temporary storage.

<details>
<summary>Under the hood</summary>

The platform discovered all registered robots and ran the capability filter against the public capability vector. No robot passed the hard constraint (millimeter-wave radar sensor required). The encrypted task spec was never forwarded to the TEE enclave for decryption -- matching failed at the public capability layer, so the spec blob was discarded unread. No bids were solicited, no credits were reserved, no charge was incurred.

This is the privacy-specific equivalent of "no robots available": the capability attestation from registered robots could not satisfy the public capability vector. The encrypted spec remains sealed. Even the platform's TEE never saw the full task details. Diane's classified inspection target -- whatever it was behind that north wall -- was never exposed to any system.

</details>

---

## Journey C: TEE Attestation Failure

**The platform's TEE enclave fails attestation mid-task. Diane is informed and chooses whether to proceed without privacy or cancel.**

**10:30 AM** -- Diane asks for another vibration reading (she needs readings at two-hour intervals). The assistant encrypts the spec and posts it. Two robots bid.

**10:30:08 AM** -- The platform attempts to open a TEE enclave session for encrypted matching. The enclave's remote attestation fails -- the TEE cannot prove to the platform's verification service that it is running untampered code on genuine hardware.

**10:30:12 AM** -- Diane's assistant reports:

> "I found two robots that match your capability requirements, but the platform's secure processing environment failed a verification check. I can't guarantee your task spec will remain encrypted during matching."
>
> "Would you like me to: (a) retry in 60 seconds, (b) proceed as a standard (non-private) task, or (c) cancel? No charge so far."

Diane replies:

> "Cancel. I'll retry in an hour."

**10:30:18 AM** -- The assistant confirms:

> "Cancelled. Your encrypted task spec has been discarded. No robot saw any details. No charge. I'll remind you at 11:30."

Diane's balance is untouched. She made a security decision in six seconds, with clear options and no jargon. She was never shown an attestation error code, a TEE vendor name, or a cryptographic failure trace.

<details>
<summary>Under the hood</summary>

TEE remote attestation is verified before every enclave session. When attestation fails, it means the platform cannot cryptographically guarantee that the enclave code is untampered and running on genuine hardware. This could be a transient hardware issue, a firmware update in progress, or -- in the worst case -- a compromised enclave.

The platform's policy for private tasks is: if TEE attestation fails, the encrypted spec is never decrypted. The user is offered three options: retry (attestation failures are often transient), downgrade to standard non-private execution (the task runs on the normal marketplace path with full spec visibility), or cancel. The choice is always Diane's.

If Diane had chosen option (b), the assistant would have re-submitted the task as a standard marketplace request -- identical to Sarah's journey. The task would have completed in ~42 seconds at standard pricing. The only difference: the full task spec would have been visible to the platform and bidding robots, as in any non-private task.

</details>

---

## What Diane Sees on Her Expense Report

At the end of the month, Diane's finance team sees one line on the corporate procurement card:

| Date | Description | Amount |
|------|-------------|--------|
| Mar 10 | YAK ROBOTICS MARKETPLACE | EUR 200.00 |

On the platform dashboard, Diane sees her own task history (decrypted with her personal key):

| Date | Task | Robot | Cost | Balance After |
|------|------|-------|------|---------------|
| Mar 26, 10:02 AM | Vibration, Bravo 7-East | Ground Rover A | EUR 0.42 | EUR 199.58 |
| Mar 26, 10:30 AM | (Cancelled -- TEE attestation) | -- | EUR 0.00 | EUR 199.58 |

**Diane's CFO** uses the organization viewer key and sees the same per-task breakdown, plus cost categorization and aggregate spend by facility. The CFO sees task costs and robot assignments but does not need to see the classified task spec contents -- the viewer key decrypts metadata (cost, time, robot, facility) but not the inspection target details, which require Diane's personal key.

**An external observer** (someone monitoring the Base blockchain, a competitor, a foreign intelligence service) sees: a USDC transfer of $0.42 from the platform escrow contract to a robot operator address. No task ID, no facility name, no sensor type, no timestamp correlation beyond the block time. One anonymous payment among thousands.

---

## What the Robot Operator Sees

The operator -- in this case, YakRobotics -- manages the same fleet that serves both standard and private tasks. Their experience for private tasks differs only slightly:

- **Setup (once):** Register each robot on the platform. Configure pricing rules. Connect a bank account for payouts. **For private tasks:** the operator's robots receive an additional TEE-compatible firmware module that handles encrypted task spec decryption. This is a one-time install.
- **Ongoing:** Robots bid and execute tasks automatically. For private tasks, the robot receives the full spec only after winning the auction. The operator's dashboard shows the task was completed and the revenue earned, but for private tasks, the task description reads "Private task -- [capability class]" rather than showing full details.
- **Payout:** After each successful delivery, the task payment is transferred to the operator's account. For Diane's vibration reading, YakRobotics receives EUR 0.42. The operator knows a vibration reading was performed in Facility Bravo. The operator does not know which corridor, what the target structure was, or why the reading was requested.

The privacy boundary is clear: the operator sees capability class and revenue. The operator does not see the classified details that make Diane's work sensitive.

---

## What Diane Never Saw

Everything below happened invisibly, in the 55 seconds between Diane's request and her answer:

- Her assistant encrypted the full task specification with the platform's TEE public key before it left her device. The plaintext spec existed only in her assistant's memory and inside the TEE enclave.
- The platform verified the TEE enclave's remote attestation -- a cryptographic proof that the enclave is running untampered code on genuine Intel TDX hardware -- before decrypting anything.
- A public capability vector (`[vibration_sensor, accelerometer_16bit, facility_bravo_access]`) was broadcast to all registered robots. This vector is deliberately coarse: it reveals the category of work, not the classified details.
- Two robots verified their own capabilities against the vector and submitted bids. Neither robot saw the encrypted task spec. They bid blind on capability match alone.
- Each robot proved its reputation using a BBS+ signed credential -- a zero-knowledge proof that it has completed N tasks with X% success rate, without revealing which tasks, for whom, or what they involved. The credential was issued by a threshold set of three platform nodes; no single node holds the full issuance history.
- Inside the TEE enclave, the platform decrypted the task spec, scored both bids against the full requirements, and selected Robot A. The enclave generated a single-use decryption key for Robot A and destroyed Robot B's session context.
- Robot A decrypted the full spec, navigated to Corridor 7-East, read its accelerometer, and returned structured vibration data.
- The platform forwarded the robot's results to a delegated ZK prover running inside a Succinct/Phala TEE-backed proving service. The prover generated a zero-knowledge proof that the results satisfy the task specification -- correct sensor, correct location, correct format, plausible values -- without the prover seeing the spec or the results in plaintext.
- Payment settled on Base as a standard USDC transfer. The on-chain memo contains no `request_id` -- the link between this payment and Diane's classified inspection exists only in the platform's encrypted database.
- The completion proof, encrypted task spec, encrypted results, and viewer-key-accessible metadata were stored in the platform's encrypted database. Diane's CFO can decrypt the metadata. A regulator with lawful authority can request the platform escrow key to decrypt the full record. No one else can.

Diane typed one sentence and got a report. The classified details of her inspection never left the encrypted envelope. That is the product.

---

## Timing

| Event | Wall Clock | Elapsed | Privacy Overhead |
|-------|-----------|---------|-----------------|
| Diane sends request | 10:02:00 AM | 0s | -- |
| Task spec encrypted, capability vector posted | 10:02:01 AM | 1s | +0s (encryption is instant) |
| TEE attestation verified | 10:02:03 AM | 3s | +2s |
| Robots discovered and filtered (capability vector) | 10:02:04 AM | 4s | +0s (same as standard) |
| Bids received from 2 robots (BBS+ credentials verified) | 10:02:08 AM | 8s | +1s (credential verification) |
| Encrypted spec decrypted in TEE, bids scored | 10:02:10 AM | 10s | +2s (TEE decryption + scoring) |
| Winning robot receives decryption key | 10:02:11 AM | 11s | +1s |
| Robot reads sensor and returns data | 10:02:45 AM | 45s | +0s (physical task is the same) |
| Delegated ZK proof generated (TEE-backed) | 10:02:50 AM | 50s | +5s (proof generation) |
| Delivery verified and settled | 10:02:53 AM | 53s | +2s (proof verification + encrypted storage) |
| Diane sees her answer | 10:02:55 AM | **55 seconds** | **+13s total overhead** |

The 13 seconds of privacy overhead break down as: TEE attestation (2s), BBS+ credential verification (1s), encrypted matching in TEE (3s), delegated ZK proof generation (5s), proof verification and encrypted storage (2s). Diane perceives a 55-second task. She has no reason to know it would have been 42 seconds without privacy.

---

## Cost Breakdown

| | Amount | Recipient | Notes |
|---|---|---|---|
| **Diane pays** | EUR 0.42 | Debited from platform credits | |
| Of which: base task price | EUR 0.35 | Robot operator | Same as standard marketplace rate |
| Of which: privacy overhead | EUR 0.07 | Platform infrastructure | TEE compute + delegated proving |
| **Robot operator receives** | EUR 0.35 | Transferred to operator bank account | Operator pricing is unaffected by privacy |
| **Platform fee** | EUR 0.00 (seed phase) | Platform takes no cut during seed phase | |
| **Privacy infrastructure cost** | EUR 0.07 | Covers TEE enclave time + Succinct prover fee | |

**Privacy overhead breakdown:**

| Component | Cost | Notes |
|-----------|------|-------|
| TEE enclave session (attestation + encrypted matching + scoring) | ~EUR 0.02 | Intel TDX instance, amortized across session |
| Delegated ZK proof generation (Succinct/Phala) | ~EUR 0.04 | SP1 proving for simple sensor verification circuit |
| Encrypted storage + viewer key management | ~EUR 0.01 | Platform database operations |
| **Total privacy overhead** | **~EUR 0.07** | **~20% above standard task price** |

The privacy overhead ranges from EUR 0.05 to EUR 0.15 depending on task complexity. For Diane's simple sensor reading, it adds EUR 0.07 -- less than the price difference between Robot A and Robot B's bids. Privacy is cheaper than choosing the wrong robot.

---

## From Seed to Scale

- **Platform-mediated privacy (now -- v2.0):** TEE-based encrypted matching and scoring. Task specs encrypted at rest, decrypted only inside TEE enclaves. Viewer keys for enterprise audit. Delegated ZK proofs for completion verification. Settlement on Base with `request_id` removed from on-chain memos. This is compliant privacy: private from external observers, auditable by the organization and regulators on lawful request. Built to satisfy EU AMLR Article 79 from day one -- the platform retains compliance data, shielded tokens are never involved.

- **BBS+ reputation at scale (v2.5, 6 months):** Threshold BBS+ issuance across 5+ platform nodes. Robots prove aggregate reputation across hundreds of tasks. Credential revocation via privacy-preserving revocation lists. Semaphore-based anonymous group membership proofs ("prove you are a registered robot without revealing which one") complement BBS+ for auction participation.

- **Compliant privacy pools (v3.0, 12 months):** If Privacy Pools (0xbow) deploys on Base, integrate the association-set model for settlement privacy. Prove payment funds are not from sanctioned sources while shielding transaction details. This adds cryptographic settlement privacy on top of the existing platform-mediated privacy, without violating EU AMLR -- the funds remain auditable via association proofs.

- **Aleo private settlement rail (v3.5, 18 months):** For non-EU markets where full cryptographic privacy is legally viable, add Aleo + USDCx as an optional settlement rail. Diane's Finnish operations continue on Base with compliant privacy. A client in a jurisdiction without AMLR-equivalent restrictions can opt into fully private settlement. The application layer remains chain-agnostic; settlement is a configuration choice.

- **Multi-party private workflows (v4.0, 24+ months):** Diane requests a full facility inspection -- multiple rooms, multiple sensor types, multiple robots. The platform decomposes it into sub-tasks, each with its own encrypted spec, and dispatches robots in parallel. Encrypted output from step N feeds step N+1 without leaving the TEE boundary. One request, many readings, one invoice, zero information leakage between stages.
