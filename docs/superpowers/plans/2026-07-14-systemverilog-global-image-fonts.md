# SystemVerilog Global Image Fonts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Increase text size across every reader-facing article image and encode those lower bounds in `$gen_article`.

**Architecture:** Update shared SVG CSS typography, preserve image semantics and colors, rasterize the 16 PNG-backed assets again, then verify all 18 article image links and update the protected skill text.

**Tech Stack:** SVG, `rsvg-convert`, `xmllint`, Git/GitHub.

---

### Task 1: Enlarge code and table images

**Files:**

- Modify: `7_13/systemverilog_task_function/code-*.svg/png`
- Modify: `7_13/systemverilog_task_function/*table.svg/png`

- [ ] Replace code SVG font values with title `38px`, status `27px`, line number `28px`, and source code `35px`; rerender every code SVG to its 1600 px PNG.
- [ ] Replace comparison-table font values with title `46px`, subtitle `25px`, header `41px`, dimension/body `36px`, code `34px`, footer `25px`; rerender its PNG.
- [ ] Replace selection-table font values with title `46px`, subtitle `25px`, header `41px`, scenario/reason `34px`, pill `32px`, footer `25px`; rerender its PNG.

Run:

```bash
xmllint --noout 7_13/systemverilog_task_function/code-*.svg 7_13/systemverilog_task_function/*table.svg
for svg in 7_13/systemverilog_task_function/code-*.svg; do
  rsvg-convert --width 1600 --output "${svg%.svg}.png" "$svg"
done
rsvg-convert --width 1600 --output 7_13/systemverilog_task_function/function-vs-task-comparison-table.png 7_13/systemverilog_task_function/function-vs-task-comparison-table.svg
rsvg-convert --width 1600 --output 7_13/systemverilog_task_function/rtl-dv-function-task-selection-table.png 7_13/systemverilog_task_function/rtl-dv-function-task-selection-table.svg
```

### Task 2: Enlarge workflow diagrams

**Files:**

- Modify: `7_13/systemverilog_task_function/function-vs-task-overview.svg`
- Modify: `7_13/systemverilog_task_function/function-vs-task-decision.svg`

- [ ] Increase every CSS font class by at least 20%; adjust node geometry only where required to keep labels inside their boxes.
- [ ] Validate both SVG files:

```bash
xmllint --noout 7_13/systemverilog_task_function/function-vs-task-overview.svg 7_13/systemverilog_task_function/function-vs-task-decision.svg
```

### Task 3: Update gen_article and publish

**Files:**

- Modify: `/home/xuchen12/.claude/skills/gen_article/SKILL.md`
- Modify: `7_13/systemverilog_task_function/`

- [ ] Add code/table/diagram font-size lower bounds to the existing `秀米栅格化交付` section.
- [ ] Verify:

```bash
test "$(find 7_13/systemverilog_task_function -maxdepth 1 -name 'code-*.png' | wc -l)" -eq 14
test "$(file 7_13/systemverilog_task_function/code-*.png | rg -c '1600 x')" -eq 14
rg -n '代码 PNG 正文字号至少 35 px|表格正文至少 34 px|流程图、时序图和决策图' /home/xuchen12/.claude/skills/gen_article/SKILL.md
git diff --check
```

- [ ] Commit the article assets, the design, and this plan; merge and push `main`.
