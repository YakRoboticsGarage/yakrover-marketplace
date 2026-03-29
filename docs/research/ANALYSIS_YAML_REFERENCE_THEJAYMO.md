# YAML Ontology Analysis: thejaymo.net Reference Patterns

## What thejaymo.net Does

**Repo structure.** The repo at `github.com/tehjaymo/thejaymo.net` is not a website source. It is a collection of "Knowledge Objects" — YAML-structured markdown files (`.yaml.md`) that encode essays as machine-readable reasoning scaffolds. Each object lives in its own directory under `Objects/`, accompanied by a `README.md` explaining provenance and usage.

```
Objects/
  Enchanted Knowledge Objects in LLM UI/
    Enchanted_Knowledge_Objects_in_LLM_UI.yaml.md
    README.md
  Ontological Hardness/
    Ontological_Hardness.yaml.md
    README.md
  Hard Worlds For Little Guys/
    Hard_Worlds_For_Little_Guys.yaml.md
    README.md
```

**YAML patterns found.** Every Knowledge Object follows an identical schema:

1. **`metadata`** — title, author, source_url, repo_url, object_url, provenance_statement, legal (copyright, license, usage_intent). Provenance is a first-class concern: the object carries its own attribution chain.
2. **`executive_summary`** — `core_problem` (list) + `central_answer` (list). Forces compression of the argument into machine-parseable claims.
3. **`thesis_stack`** — primary/secondary/tertiary thesis, each with `statement`, `quote`, and `gravity_effect` (a one-line directive telling a model how this thesis should shape reasoning).
4. **`sections`** — ordered list of argument segments. Each has `id`, `title`, `purpose`, `implied_critiques`, and an `argument_map` of claims with evidence patterns (`logic_path`, `associative_path`, `diagnostic_lens`, `case_study`). Takeaways close each section.
5. **`talisman_taxonomy`** — type classification (Analytical, Reference, Procedural, Narrative), purpose, likely_effects. This is a self-describing usage tag.
6. **`glossary`** — key terms with `definition` and `note`, scoped to the object's domain.
7. **`mantra`** and **`essence`** — single-sentence distillations for quick orientation.

**Key design principles:**
- Objects are self-contained: everything needed to reason with the object is inside it.
- Provenance travels with the artefact, not in external metadata.
- `gravity_effect` fields are unique — they tell models how to weight claims, not just what claims are.
- The schema is dual-legible: a human can scan it, a model can parse it structurally.
- No external dependencies or cross-references between objects.

## Patterns We Should Adopt

### 1. Self-describing metadata with provenance
thejaymo objects carry `provenance_statement`, `usage_intent`, and `legal` inside every file. Our PRODUCT_DSL.yaml has `meta.sources` but no provenance chain, no license, no usage_intent. When this file gets pasted into an LLM context or shared externally, it has no self-description.

### 2. Gravity effects / reasoning directives
Every thesis in thejaymo's schema includes `gravity_effect` — a short instruction to the model about how to use the claim. Our PRODUCT_DSL has `claim` and `evidence_for/against` but never tells a model which claims should dominate reasoning. This matters when the file is used as an LLM reasoning scaffold.

### 3. Executive summary as structured compression
thejaymo forces `core_problem` + `central_answer` as lists at the top. Our PRODUCT_DSL has `vision.thesis` which is close, but it is buried under `meta` and `vision` blocks. A model scanning our file has to read 60+ lines before finding the core proposition.

### 4. Talisman taxonomy / usage classification
Each thejaymo object declares what kind of reasoning artefact it is and what effects it will have when loaded. Our PRODUCT_DSL has no equivalent. Adding a `usage` block would help both humans and models understand whether this file is a reference doc, a decision scaffold, or an operational specification.

### 5. Glossary with scoped definitions
thejaymo's glossary defines terms as used within the object, with notes distinguishing borrowed vs. coined terms. Our PRODUCT_DSL uses domain-specific terms (reverse auction, MCP, ERC-8004, x402, JTBD, DTN) without inline definitions. A model unfamiliar with our domain must infer or hallucinate meanings.

### 6. Mantra and essence
A one-line summary that serves as the object's identity anchor. Our file has `vision.tagline` which is close, but it describes the product, not the document's purpose.

## Patterns We Already Have

1. **Cross-reference syntax** (`domain:slug`). Our `meta.cross_reference_syntax` is well-designed and more systematic than thejaymo's standalone objects which have no cross-referencing at all. Our pattern is better for a multi-document system.

2. **Source traceability.** Every section in our PRODUCT_DSL links back to a source document. thejaymo links to one source URL per object. Our granular per-claim sourcing is stronger for a product context.

3. **Structured evidence with confidence.** Our `bet_chain` with `confidence`, `evidence_for`, `evidence_against`, and `falsified_by` is more rigorous than thejaymo's `argument_map` which lacks quantified confidence. We should keep this.

4. **State machines and technical specifications.** thejaymo objects are pure conceptual scaffolds. Our file encodes operational specifications (state machines, equipment catalogs, settlement modes) which thejaymo's schema was never designed for. Our domain demands this.

5. **Decision ID system.** Our `AD-X`, `FD-X`, `PP-X` prefix system for tracing decisions is a strong pattern not present in thejaymo.

## Recommended Changes to PRODUCT_DSL.yaml

1. **Add a `usage` block after `meta`.** Declare what this file is for:
   ```yaml
   usage:
     type: "reference + decision scaffold"
     intent: "Single-document ontological map of the entire product for human and LLM consumption"
     gravity_effect: "When reasoning about this product, treat this file as the authoritative source of entities, relationships, strategic bets, and architectural decisions."
   ```

2. **Add an `executive_summary` block before `vision`.** Extract the core problem and answer into a machine-scannable compression at the top, within the first 20 lines:
   ```yaml
   executive_summary:
     core_problem:
       - "No platform exists where AI agents post physical-world tasks and robots bid autonomously"
       - "Construction survey scheduling is a bottleneck costing GCs 2-3 missed bids/quarter"
     central_answer:
       - "Reverse auction marketplace with AI agent mediation, starting with construction site surveying"
       - "Earth-proven sensor stacks and workflows transfer to lunar operations"
   ```

3. **Add `gravity_effect` to each bet in `bet_chain`.** For each bet, add a one-line reasoning directive:
   ```yaml
   gravity_effect: "If this bet is false, the entire construction wedge strategy fails. Prioritize validation."
   ```

4. **Add a `glossary` section.** Define the 10-15 terms that are most likely to confuse an LLM or new reader: reverse auction, MCP, ERC-8004, x402, JTBD, DTN, BBS+, LAANC, PLS, ConsensusDocs, TEE, commitment hash.

5. **Add `provenance` to `meta`.** Include a provenance statement and usage license so the file is self-describing when extracted from this repo:
   ```yaml
   provenance: "Generated from research documents listed in sources. Authoritative for entity definitions and relationships."
   license: "Proprietary — Robot Task Auction Marketplace project"
   ```

6. **Add a `mantra` and `essence` at the end of the file.** One-line anchors:
   ```yaml
   mantra: "AI agents post tasks, physical robots bid, winners get paid."
   essence: "This file is the single ontological map of the product — every entity, bet, unknown, and architectural decision lives here."
   ```

7. **Add `implied_critiques` to the `unknowns` section.** For each unknown, note what it implies about the current design, following thejaymo's pattern of making implicit assumptions explicit.

8. **Move `vision.thesis` higher or duplicate it into `executive_summary`.** The thesis claim and confidence level are the most important 5 lines in the file. They should be scannable within the first 30 lines.

## Reference Pattern for Future YAML/Skills

When creating new YAML ontology documents (skills, research objects, analysis files), use this checklist:

```yaml
# --- REQUIRED: Self-description ---
metadata:
  title: ""           # Human-readable name
  author: ""          # Who created this
  created: ""         # ISO date
  updated: ""         # ISO date
  source: ""          # Where the underlying content comes from
  provenance: ""      # How this file was generated
  usage_intent: ""    # What this file is for (reasoning scaffold / spec / reference)
  license: ""         # Ownership/sharing terms

# --- REQUIRED: Compressed core ---
executive_summary:
  core_problem: []    # 2-3 bullet points
  central_answer: []  # 2-3 bullet points

# --- REQUIRED: Self-classification ---
usage:
  type: ""            # reference | decision_scaffold | operational_spec | analytical
  gravity_effect: ""  # One-line directive for models: how should this shape reasoning?

# --- RECOMMENDED: Cross-reference ---
cross_references:
  syntax: "domain:slug"
  related: []         # Links to other YAML objects in the project

# --- CONTENT: Domain-specific sections ---
# ... (varies by document type)

# --- RECOMMENDED: Domain glossary ---
glossary:
  term_name:
    definition: ""
    note: ""          # Borrowed vs. coined, scope of usage

# --- RECOMMENDED: Anchors ---
mantra: ""            # One-line identity statement
essence: ""           # One-line purpose statement
```

**Rules:**
- Every YAML file should be self-contained enough that a model can reason with it without needing external context.
- Provenance and attribution travel with the file, not in a separate README.
- Use `gravity_effect` on key claims to guide model attention.
- Glossary terms should be scoped to the document's usage, not generic definitions.
- The first 30 lines should tell a reader (human or model) what this file is and why it matters.
