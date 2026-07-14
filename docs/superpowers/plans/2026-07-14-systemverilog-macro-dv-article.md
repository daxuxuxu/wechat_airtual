# SystemVerilog Macro DV Article Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a Xiumi-ready SystemVerilog macro-definition article explaining DV uses and boundaries.

**Architecture:** Write a standalone Markdown article with only image references for code and comparison content. Generate native draw.io workflow/decision diagrams plus large-font SVG/PNG code and table assets in the dated article directory.

**Tech Stack:** Markdown, SystemVerilog, draw.io, SVG, `rsvg-convert`, Git/GitHub.

---

### Task 1: Create the article and image assets

**Files:**

- Create: `7_14/systemverilog_macro/systemverilog_macro_article.md`
- Create: `7_14/systemverilog_macro/*.png`
- Create: `7_14/systemverilog_macro/*.svg`
- Create: `7_14/systemverilog_macro/*.drawio`

- [ ] Create the article with `[SV]` title, a personal hook, macro semantics, DV use cases, mechanism comparison, risks, verification points, and conclusion.
- [ ] Create a cover image, a macro preprocess flow, a macro choice decision diagram, one comparison table image, and code images for all macro examples.
- [ ] Keep prose self-contained and generic; use Chinese full-width punctuation outside code images.

### Task 2: Verify publication quality

**Files:**

- Test: `7_14/systemverilog_macro/`

- [ ] Validate SVG/draw.io XML, PNG dimensions, image links, no fenced code blocks, no Markdown tables, no prohibited private names, and `git diff --check`.

### Task 3: Publish

**Files:**

- Modify: Git history on `main`

- [ ] Commit the article and assets, merge the verified branch into `main`, and push it to GitHub.
