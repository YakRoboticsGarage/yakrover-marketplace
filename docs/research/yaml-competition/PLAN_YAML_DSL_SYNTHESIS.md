# Plan: YAML DSL Synthesis of Entire Product

## What We're Building

A single YAML file that is the ontological map of the entire product — from vision to implementation. Not documentation, but a machine-readable specification that captures every decision, relationship, and component.

## Approach Options

### Option A: Document-First Decompose
- Read each research doc → extract YAML fragments → merge
- Risk: ends up as a flat dump with no ontological structure

### Option B: Schema-First Design
- Design the YAML schema/ontology first → then fill from research
- Risk: schema may miss things not anticipated

### Option C: Parallel Domain Extraction + Integration
- Define 8-10 domains (vision, users, tech, legal, market, etc.)
- Each agent extracts one domain from ALL relevant docs
- Final agent integrates into one ontologically coherent YAML
- Risk: integration is hard, may have gaps between domains

### Option D: Debate → Schema → Parallel Fill → Review
1. 3 agents debate the right ontological structure
2. Synthesize into agreed schema
3. Parallel agents fill each domain
4. Integration agent assembles and cross-references
5. Review agent checks for gaps

## Recommendation: Option D

This matches the user's request for debate-first, parallel execution, reintegration.

## Proposed Domains (for parallel extraction)

1. **Vision & Thesis** — north star, core assumptions, positioning
2. **User Profiles & Journeys** — all personas including agents
3. **Product Architecture** — components, MCP, CLI, web, skills
4. **Market & Competitive** — landscape, affordances, partnerships, geography
5. **Legal & Governance** — contracts, bonds, compliance, dispute resolution
6. **Technical Platform** — blockchain, sensors, equipment, autonomy gaps
7. **Roadmap & GTM** — phases, milestones, go-to-market strategy
8. **Constitutional Controls** — safety, mediation, conflict resolution, agent governance

## Source Documents

All in /Users/rafa/Documents/robots/yakrover-marketplace/docs/:
- research/ (18 files)
- feedback/ (12 files)
- ROADMAP_v4.md, USER_JOURNEY_CONSTRUCTION_v01.md
- FEATURE_REQUIREMENTS_v15.md, DECISIONS.md
- DEVELOPMENT_STRATEGY.md, SCOPE.md
- _archive/ (for historical context)
- demo/index.html (current product state)
- .claude/skills/ (2 skills with references)
