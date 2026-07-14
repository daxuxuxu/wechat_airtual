# SystemVerilog Table Images Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two Markdown tables in the SystemVerilog `task` versus `function` article with horizontal 1600 px PNG information tables that import reliably into Xiumi.

**Architecture:** Each table is authored as a standalone SVG using the article's existing blue/orange visual language, then rasterized locally with `rsvg-convert` into a 1600 px wide PNG. The Markdown article embeds only the PNGs, while the SVGs remain adjacent as editable source assets.

**Tech Stack:** Markdown, SVG, `rsvg-convert`, `xmllint`, Git/GitHub.

---

## File Structure

- `7_13/systemverilog_task_function/function-vs-task-comparison-table.svg`: horizontal three-column comparison table source.
- `7_13/systemverilog_task_function/function-vs-task-comparison-table.png`: Xiumi-ready raster output for the comparison table.
- `7_13/systemverilog_task_function/rtl-dv-function-task-selection-table.svg`: horizontal three-column scenario-selection table source.
- `7_13/systemverilog_task_function/rtl-dv-function-task-selection-table.png`: Xiumi-ready raster output for the scenario-selection table.
- `7_13/systemverilog_task_function/systemverilog_task_function_article.md`: removes pipe tables and references the two PNG assets.

### Task 1: Create the function/task comparison-table assets

**Files:**

- Create: `7_13/systemverilog_task_function/function-vs-task-comparison-table.svg`
- Create: `7_13/systemverilog_task_function/function-vs-task-comparison-table.png`

- [ ] **Step 1: Create the SVG with a 1600×770 horizontal table**

Create an SVG with a white background, an 84 px dark-blue title band, and a three-column table beneath it. Use `#23313F` for the title band, `#1F6FB5` for the `function` header, `#E67E22` for the `task` header, `#F4F6F7` for alternate row backgrounds, and `#D5D8DC` for separators.

Set the title to:

```text
SystemVerilog：function 与 task 的核心差异
```

Use table columns with these exact headings and widths:

```text
维度 (300 px) | function (610 px) | task (610 px)
```

Render these five rows, in order:

```text
Time control | 不包含 #、@、wait | 可包含 #、@、wait
调用上下文 | expression / assertion | procedural statement
返回方式 | return value 或 void | output / inout / ref 参数
典型用途 | decode、CRC、parity、scoreboard 计算 | driver、BFM、reset、handshake
可重入性 | 并发调用时优先 automatic | 并发调用时优先 automatic
```

Use 31 px text for headers, 27 px text for cells, 42 px horizontal padding, 82 px row height, and blue/orange left-side accent bars on the `function` and `task` headers.

- [ ] **Step 2: Validate SVG source**

Run:

```bash
xmllint --noout \
  7_13/systemverilog_task_function/function-vs-task-comparison-table.svg
```

Expected: exit code 0 with no output.

- [ ] **Step 3: Render the Xiumi PNG**

Run:

```bash
rsvg-convert \
  --width 1600 \
  --output 7_13/systemverilog_task_function/function-vs-task-comparison-table.png \
  7_13/systemverilog_task_function/function-vs-task-comparison-table.svg
```

Expected: a non-empty PNG whose `file` output describes a 1600 px wide PNG image.

### Task 2: Create the RTL/DV scenario-selection table assets

**Files:**

- Create: `7_13/systemverilog_task_function/rtl-dv-function-task-selection-table.svg`
- Create: `7_13/systemverilog_task_function/rtl-dv-function-task-selection-table.png`

- [ ] **Step 1: Create the SVG with a 1600×900 horizontal table**

Create an SVG with the same white background, `#23313F` title band, separator color, typography, and outer border as Task 1.

Set the title to:

```text
RTL / DV 场景：该选 function 还是 task？
```

Use table columns with these exact headings and widths:

```text
场景 (480 px) | 更适合的构造 (410 px) | 原因 (630 px)
```

Render these six rows, in order:

```text
combinational address decode | function automatic | 无 time control，结果直接进入 expression
parity / CRC / expected data | function automatic | 纯计算，适合 monitor 或 scoreboard 复用
UVM driver transaction | task automatic | 需要等待 clock、credit、ready 或 response
reset sequence | task automatic | pulse width 和 release point 受时间控制
uvm_component::run_phase | task | run phase 本身是 time-consuming phase
uvm_object::do_compare / convert2string | function | 返回 comparison result 或 string，不应推进时间
```

Use a blue pill behind `function` and `function automatic`, an orange pill behind `task` and `task automatic`, and a 98 px row height so no text wraps or collides.

- [ ] **Step 2: Validate SVG source**

Run:

```bash
xmllint --noout \
  7_13/systemverilog_task_function/rtl-dv-function-task-selection-table.svg
```

Expected: exit code 0 with no output.

- [ ] **Step 3: Render the Xiumi PNG**

Run:

```bash
rsvg-convert \
  --width 1600 \
  --output 7_13/systemverilog_task_function/rtl-dv-function-task-selection-table.png \
  7_13/systemverilog_task_function/rtl-dv-function-task-selection-table.svg
```

Expected: a non-empty PNG whose `file` output describes a 1600 px wide PNG image.

### Task 3: Replace Markdown tables with image references

**Files:**

- Modify: `7_13/systemverilog_task_function/systemverilog_task_function_article.md:23-29`
- Modify: `7_13/systemverilog_task_function/systemverilog_task_function_article.md:310-317`

- [ ] **Step 1: Replace the core comparison pipe table**

Replace the seven Markdown pipe-table lines directly below `### 一、先看时间：同一时刻算完，还是跨多个 cycle` with:

```markdown
![function 与 task 核心差异表](function-vs-task-comparison-table.png)
```

Keep the explanatory paragraphs before and after the table unchanged.

- [ ] **Step 2: Replace the RTL/DV scenario pipe table**

Replace the eight Markdown pipe-table lines directly below `### 七、RTL / DV 中怎么选` with:

```markdown
![RTL / DV 场景选型表](rtl-dv-function-task-selection-table.png)
```

Keep the decision list and the existing decision SVG unchanged.

- [ ] **Step 3: Check the image references**

Run:

```bash
rg -n \
  'function-vs-task-comparison-table\.png|rtl-dv-function-task-selection-table\.png' \
  7_13/systemverilog_task_function/systemverilog_task_function_article.md
```

Expected: exactly two lines, one for each new PNG.

### Task 4: Verify the publication assets and publish

**Files:**

- Test: `7_13/systemverilog_task_function/systemverilog_task_function_article.md`
- Test: `7_13/systemverilog_task_function/*.svg`
- Test: `7_13/systemverilog_task_function/*.png`

- [ ] **Step 1: Verify markup, asset dimensions, and source-table removal**

Run:

```bash
set -e
xmllint --noout \
  7_13/systemverilog_task_function/function-vs-task-comparison-table.svg \
  7_13/systemverilog_task_function/rtl-dv-function-task-selection-table.svg

file \
  7_13/systemverilog_task_function/function-vs-task-comparison-table.png \
  7_13/systemverilog_task_function/rtl-dv-function-task-selection-table.png

! rg -n '^\\| .* \\|$' \
  7_13/systemverilog_task_function/systemverilog_task_function_article.md

git diff --check
```

Expected: both SVG files are valid, both PNG files are 1600 px wide, the article has no pipe-table rows, and no whitespace errors are reported.

- [ ] **Step 2: Review the publication diff**

Run:

```bash
git diff -- \
  7_13/systemverilog_task_function \
  docs/superpowers/specs/2026-07-14-systemverilog-table-images-design.md \
  docs/superpowers/plans/2026-07-14-systemverilog-table-images.md
```

Expected: only the two table assets, two table PNGs, Markdown replacements, and associated design/plan documents are included.

- [ ] **Step 3: Commit and push**

Run:

```bash
git add \
  7_13/systemverilog_task_function \
  docs/superpowers/specs/2026-07-14-systemverilog-table-images-design.md \
  docs/superpowers/plans/2026-07-14-systemverilog-table-images.md
git commit -m "Add Xiumi-ready SystemVerilog table images"
git push origin main
```

Expected: GitHub `main` contains the image-backed article and both PNG files.
