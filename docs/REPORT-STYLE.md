# Report style guide — YAK ROBOTICS
**Applies to:** Pitch deck, investor materials, customer-facing docs, research summaries, demo copy
**Does not apply to:** Raw research notes, YAML ontology, code comments, internal feedback files

---

## The standard in one sentence

Every sentence must earn its place. If it restates what was just said, hedges a claim that doesn't need hedging, or exists to signal effort rather than convey information, cut it.

---

## Voice and register

**Use active voice.** "GCs wait 2-3 weeks for survey data" — not "Survey data turnaround is impacted by crew availability constraints."

**State the finding first, reasoning second.** Readers should be able to stop after the first sentence of any section and know what it says.

**Be confident, not hedged.** If the evidence supports a conclusion, state it. If the evidence is incomplete, say so once and move on. Don't hedge every sentence.

**Be specific, not gestural.** "Several GCs" → name the count. "Significant savings" → give the number. Vague quantifiers signal absence of evidence.

**Don't announce honesty.** Never label a section or claim as "honest." If the rest of the document isn't honest, labeling one section as honest makes it worse. State facts. Let the reader judge credibility from the evidence.

**Don't self-congratulate.** "Deep research" and "thorough analysis" are for the reader to conclude, not the writer to claim. Show the research; don't describe having done it.

---

## Pitch and investor materials

**Lead with the customer's problem, not your solution.** The first thing an investor reads should make them feel the pain. The solution is slide 2, not slide 1.

**Source every number.** "$8B TAM" needs "(IBISWorld 2025)." "368K Part 107 holders" needs "(FAA 2025)." Unsourced numbers are assumed fabricated.

**Never say "0 competitors."** It signals either naiveté or a nonexistent market. Say: "No platform combines automated procurement with physical robot execution. Adjacent players exist in each dimension separately."

**Don't label things as vision vs reality.** Instead, describe each item factually. "Auction engine: 5,300 lines of Python, 147 tests passing." "Michigan pilot: 15 target GCs identified, outreach starting Q2 2026." The reader can see what's built and what isn't from the verbs. "Built" vs "identified" vs "planned" — the tense does the work.

**Don't use the word "honest."** If you say "honest assessment" or "let's be honest," you're framing the surrounding content as potentially dishonest. Just say the thing.

**Phase gates, not year targets.** "Phase 3: When 10+ GCs and 5+ operators are active" — not "v3.0 (2027)." Conditions are credible; calendar dates for unvalidated markets are not.

---

## AI writing tropes to avoid

Reference: https://tropes.fyi/tropes-md

### Negative parallelism (the #1 AI tell)
"Not X — it's Y." The single most commonly identified AI writing pattern. One use per document max. The "Not X. Not Y. Just Z." dramatic countdown is worse.

| Avoid | Replace with |
|-------|-------------|
| "This is not a drone company — it's a procurement platform" | "YAK ROBOTICS is a procurement platform for construction survey services." |
| "Not a staffing agency. Not a blockchain project." | State what it IS, once. |
| "Not a bug. Not a feature. A design flaw." | "The design is flawed because..." |

### Em-dash addiction
Humans use 2-3 per piece. AI uses 20+. Two per page is a ceiling. Em-dash pairs ("— clause —") inside sentences are the worst offenders; the inner clause works better as its own sentence.

### Magic adverbs and assertion words
"Quietly," "deeply," "precisely," "fundamentally," "notably," "importantly" claim significance without demonstrating it. If the reasoning is sound, the adverb is unnecessary. "Quietly orchestrating" is not a thing.

### "Serves as" / "functions as" / "stands as"
Replace with "is." Every time.

### Self-answering rhetorical questions
"The result? Devastating." "What does this mean? It means..." Nobody asked. State the point.

### "Here's the kicker" / "Here's the thing"
False suspense. If the point is important, it doesn't need a drumroll.

### "Let's break this down" / "Let's unpack this"
Pedagogical voice that assumes the reader needs hand-holding. Just present the information.

### "Imagine a world where..."
Futurism framing. Describe what you're building, not a hypothetical utopia.

### Grandiose stakes inflation
Elevating mundane topics to world-historical significance. "This will fundamentally reshape everything" means nothing. Say what changes, for whom, by how much.

### One-point dilution
Making the same argument in four different phrasings. State the thesis once with precision. Don't restate it as if the reader forgot.

### Fractal summaries
Don't summarize a section after writing it. Don't introduce a section before writing it. Don't announce conclusions ("In summary," "To sum up"). If the section is well-structured, the synthesis is the final paragraph, not a separate recap.

### Tricolon abuse
Excessive rule-of-three patterns. "Products impress; platforms empower. Products solve; platforms create." One tricolon per document. More than that is a mechanical rhythm, not rhetoric.

### Anaphora abuse
"They could expose... They could offer... They could provide..." Repeated sentence openings in succession. Vary the structure.

### Bold-first bullets
Not every bullet needs a bold lead. Use bold only for defined terms (first use) and section findings. When everything is bold, nothing is emphasized.

### Invented concept labels
"Supervision paradox." "Acceleration trap." "Workload creep." If the concept doesn't have a source, don't coin a term for it. Describe the phenomenon in plain language.

### Vague attributions
"Experts argue." "Industry reports suggest." "Observers have cited." Name the expert. Cite the report. If you can't, cut the claim.

### Unicode decoration
Avoid arrows (→), smart quote styling, and decorative Unicode in analytical documents. Use standard punctuation.

---

## What to cut

### Opening throat-clearing
| Cut this | Replace with |
|----------|-------------|
| "This deck seeks to present..." | Start with the content |
| "Let's be honest about where we are" | State where you are |
| "What we've built so far" | Name what's built |
| "The honest truth is..." | Say the truth |

### Managerial filler
| Cut this | Use instead |
|----------|------------|
| leverage | use |
| stakeholders | name the parties |
| robust | say what the thing does |
| streamline | say the process change |
| optimize | improve, reduce, increase — be specific |
| end-to-end | describe the actual scope |
| comprehensive | name what it covers |

### Structural bloat
- Don't summarize a section before writing it
- Don't summarize a section after writing it
- Don't explain what a table shows if the table is clear
- Don't use color-coded badges as a substitute for clear writing (the tense and specificity of the claim should make status obvious)

---

## Evidence standards

**Source every external claim inline.** Format: "(Source, Year)" or small-text citation below the data point.

**Distinguish built from planned.** Use present tense for what exists ("The auction engine processes..."), future tense for what doesn't ("The Michigan pilot will..."). Don't use badges — the grammar does the work.

**Don't count internal artifacts as traction.** Tests, MCP tools, YAML lines, research docs — these are not traction. Traction is: customers, revenue, LOIs, waitlist signups, pilot agreements. If you have none, say so and explain what you have instead (domain research, working prototype, identified targets).

---

## Terms specific to this project

| Avoid | Use instead |
|-------|------------|
| robot (in pitch to GCs) | drone, automated survey platform, or the equipment name (DJI M350 RTK) |
| blockchain, on-chain, Base, x402 | escrow, verified payment, digital identity |
| MCP, ERC-8004 | AI-assisted, agent-mediated, or just describe the function |
| agentic | AI-assisted procurement (describe the function, not the architecture) |
| north star | long-term goal, or just describe the goal |
| moonshot (unless literally about the Moon) | ambitious, or describe the ambition |

---

*This guide applies to all materials produced for YAK ROBOTICS. Test: would a Michigan highway GC estimator with no tech background read this and immediately know what it means? If not, rewrite it.*
