# Yak Robotics Style Guide (Gwern-adapted)

Adapted from the [Gwern.net Manual of Style](https://gwern.net/style-guide) for a technical robotics marketplace brief. This documents which Gwern patterns apply to our context and which we skip.

## Design Principles Adopted

### Typography
- **Serif body text**: Source Serif 4 for reading; monospace (JetBrains Mono) reserved for code, commands, and data values only
- **18px base font size**: larger than typical web, optimized for sustained reading
- **1.8 line-height** for body, 1.3 for headings
- **~700px max-width** for body text column (60-75 chars per line, Gwern standard)
- **Justified text with hyphens**: Gwern uses full justification; we adopt this for the essay feel
- **Emphasis cycle**: **bold** -> *italics* -> small caps (repeating)
- **First line smallcaps**: first line of the opening paragraph uses smallcaps (Gwern convention)

### Color Palette
- Background: `#fffff8` (warm cream, Gwern's signature off-white)
- Body text: `#000` (true black for max contrast)
- Headings: `#000` (no colored headings — color is for links and accents only)
- Links: `#3b7ea1` (Gwern's muted teal-blue)
- Link hover: underline appears (no underline by default)
- Muted/secondary: `#555`
- Borders: `#ddd`
- Brand accent: `#E8792B` (Yak orange — used only for the header rule and CTAs, never structural)
- Code background: `#f0f0f0`

### Information Hierarchy (Iceberg Model)
From Gwern's structure section:
1. **Abstract** (blockquote at top) — the executive summary becomes a proper abstract
2. **Margin notes** — brief 1-3 word summaries in the left margin on desktop, inline on mobile
3. **Body paragraphs** — the main content
4. **Sidenotes** — evidence, citations, asides float in the right margin (replace our current evidence popovers)
5. **Collapsible sections** — detailed breakdowns that readers can expand
6. **Appendices** — reference tables, full lists

### Link Behavior (from HTML section)
- No underline by default (cleaner reading flow)
- Underline on hover
- External links: append `title` attribute with `'Title', Author Year` metadata
- First use of a term or citation is hyperlinked; subsequent uses are not
- Links should be to fulltext URLs where possible

### Headings (from Structure section)
- Mixed title case (not uppercase transforms)
- h1: large serif, normal weight, bottom rule
- h2: section headers, <6 words, with thin separator rule
- h3: subsection, bold
- Headers should not exceed 6 words to prevent ToC line-wrapping

### Structure Rules
- Sections should be at least 2 paragraphs long
- Information density goes left-to-right: section title -> margin note -> paragraph -> sidenote -> collapse -> appendix
- "See Also" / external links at the end
- Footnotes <200 words; essays <10,000 words

### HTML Conventions (from HTML section)
- Use raw `<div>`/`<span>` for control, not framework abstractions
- Big-endian class naming: `link-live`, `link-icon`, with `-not` suffix for negation
- `div.abstract` containing a blockquote for the page abstract
- `div.collapse` with `.abstract-collapse` for expandable sections
- `div.admonition [tip/note/warning]` for callouts
- `div.epigraph` for opening quotes
- Self-documenting: all elements readable as text or with useful `title` attributes

### What We Skip from Gwern
- Pandoc/Markdown compilation (we write raw HTML)
- Dropcaps (nice but unnecessary for a brief)
- Transclusion system (site-specific, not applicable to single-file)
- Backlinks and similar-links sections
- Poetry formatting
- Link archiving and link-rot prevention
- Inflation adjustment syntax
- Interwiki shortcuts

## Key Visual Differences from Current Memo

| Current Memo | Gwern-style Version |
|---|---|
| JetBrains Mono everywhere | Source Serif 4 body, JetBrains Mono code only |
| Orange (#E8792B) h2 headings | Black headings, thin rule separators |
| UPPERCASE section titles | Title case |
| White background (#fff) | Warm cream (#fffff8) |
| Evidence popovers (click) | Sidenotes in right margin (always visible on desktop) |
| Breadcrumb nav bar | Table of contents sidebar or top block |
| 1100px max-width | ~700px text column with wide margins for sidenotes |
| 15px font size | 18px font size |
| Two-column layouts | Single column with margin notes |
