# SystemVerilog Xiumi Code Images and gen_article Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enlarge both publication tables, replace all 14 SystemVerilog code blocks with PNG images, and update `$gen_article` with reusable Xiumi raster-delivery rules.

**Architecture:** Rebuild the two table SVGs with larger type and manual line wrapping, then rasterize them at 1600 px wide. A temporary renderer extracts each `systemverilog` fenced block, creates an editable SVG source and a matching PNG, and replaces the fenced block with an image reference. The existing `gen_article` skill gains a concise Xiumi mode plus an explicit validation checklist.

**Tech Stack:** Markdown, SVG, Python standard library, `rsvg-convert`, `xmllint`, Git/GitHub.

---

## File Structure

- `7_13/systemverilog_task_function/function-vs-task-comparison-table.svg/png`: larger core-comparison table.
- `7_13/systemverilog_task_function/rtl-dv-function-task-selection-table.svg/png`: larger RTL/DV selection table.
- `7_13/systemverilog_task_function/code-01-*.svg/png` through `code-14-*.svg/png`: source and Xiumi PNG for each code block.
- `7_13/systemverilog_task_function/systemverilog_task_function_article.md`: image references replace every pipe table and `systemverilog` fenced block.
- `/home/xuchen12/.claude/skills/gen_article/SKILL.md`: updated Xiumi raster-delivery guidance.

### Task 1: Establish the failing skill baseline

**Files:**

- Test: `/home/xuchen12/.claude/skills/gen_article/SKILL.md`

- [ ] **Step 1: Check for the new Xiumi code-image rule before editing**

Run:

```bash
rg -n \
  '秀米栅格化交付|代码块.*SVG.*PNG|正文只嵌 PNG|fenced code block' \
  /home/xuchen12/.claude/skills/gen_article/SKILL.md
```

Expected: no matching output and exit code 1. This is the RED baseline proving the current skill does not require code-image delivery.

### Task 2: Rebuild the two table assets with larger typography

**Files:**

- Modify: `7_13/systemverilog_task_function/function-vs-task-comparison-table.svg`
- Modify: `7_13/systemverilog_task_function/function-vs-task-comparison-table.png`
- Modify: `7_13/systemverilog_task_function/rtl-dv-function-task-selection-table.svg`
- Modify: `7_13/systemverilog_task_function/rtl-dv-function-task-selection-table.png`

- [ ] **Step 1: Enlarge the core comparison table**

Use a 1600×860 SVG. Use a 40 px title, 35 px column headers, 31 px body text, and 112 px data rows. Preserve the existing color scheme: dark-blue title bar `#23313F`, blue `function` header `#1F6FB5`, orange `task` header `#E67E22`, and alternating `#F4F6F7` rows.

Keep the five rows:

```text
Time control | 不包含 #、@、wait | 可包含 #、@、wait
调用上下文 | expression / assertion | procedural statement
返回方式 | return value 或 void | output / inout / ref 参数
典型用途 | decode、CRC、parity、scoreboard 计算 | driver、BFM、reset、handshake
可重入性 | 并发调用时优先 automatic | 并发调用时优先 automatic
```

- [ ] **Step 2: Enlarge and wrap the RTL/DV selection table**

Use a 1600×1120 SVG. Use a 40 px title, 35 px column headers, and 29 px body text. Increase rows to 145 px. Break long scenario labels and reasons into two `<tspan>` lines; for example:

```text
combinational address
decode
```

and:

```text
uvm_object::do_compare /
convert2string
```

Keep blue `function` pills and orange `task` pills. Preserve all six scenario rows and their original meanings.

- [ ] **Step 3: Render and validate the updated table PNGs**

Run:

```bash
xmllint --noout \
  7_13/systemverilog_task_function/function-vs-task-comparison-table.svg \
  7_13/systemverilog_task_function/rtl-dv-function-task-selection-table.svg

rsvg-convert --width 1600 \
  --output 7_13/systemverilog_task_function/function-vs-task-comparison-table.png \
  7_13/systemverilog_task_function/function-vs-task-comparison-table.svg

rsvg-convert --width 1600 \
  --output 7_13/systemverilog_task_function/rtl-dv-function-task-selection-table.png \
  7_13/systemverilog_task_function/rtl-dv-function-task-selection-table.svg

file 7_13/systemverilog_task_function/*table.png
```

Expected: valid SVG XML and non-empty 1600 px wide PNG files.

### Task 3: Render all SystemVerilog code blocks as PNG images

**Files:**

- Create temporarily: `/tmp/render_systemverilog_code_images.py`
- Create: `7_13/systemverilog_task_function/code-01-even-parity.svg/png`
- Create: `7_13/systemverilog_task_function/code-02-byte-enable.svg/png`
- Create: `7_13/systemverilog_task_function/code-03-send-write.svg/png`
- Create: `7_13/systemverilog_task_function/code-04-decode-struct.svg/png`
- Create: `7_13/systemverilog_task_function/code-05-split-address.svg/png`
- Create: `7_13/systemverilog_task_function/code-06-ref-counter.svg/png`
- Create: `7_13/systemverilog_task_function/code-07-static-task-pitfall.svg/png`
- Create: `7_13/systemverilog_task_function/code-08-automatic-task.svg/png`
- Create: `7_13/systemverilog_task_function/code-09-function-time-control-illegal.svg/png`
- Create: `7_13/systemverilog_task_function/code-10-task-expression-illegal.svg/png`
- Create: `7_13/systemverilog_task_function/code-11-task-response-check.svg/png`
- Create: `7_13/systemverilog_task_function/code-12-bfm-time-control-illegal.svg/png`
- Create: `7_13/systemverilog_task_function/code-13-task-output-result.svg/png`
- Create: `7_13/systemverilog_task_function/code-14-task-output-interface.svg/png`

- [ ] **Step 1: Write the renderer**

Create `/tmp/render_systemverilog_code_images.py` with these behaviors:

```python
from html import escape
from pathlib import Path
import subprocess

ARTICLE = Path("7_13/systemverilog_task_function/systemverilog_task_function_article.md")
OUT = ARTICLE.parent
WIDTH = 1600
LINE_HEIGHT = 46
TOP = 130
BOTTOM = 54

def svg_for_code(title, code, illegal):
    lines = code.splitlines() or [""]
    height = TOP + len(lines) * LINE_HEIGHT + BOTTOM
    accent = "#C0392B" if illegal else "#1F6FB5"
    status = "ILLEGAL / 不应使用" if illegal else "SystemVerilog"
    body = []
    for number, line in enumerate(lines, 1):
        y = TOP + number * LINE_HEIGHT - 12
        body.append(
            f'<text x="112" y="{y}" class="line-no">{number:02d}</text>'
            f'<text x="188" y="{y}" class="code">{escape(line)}</text>'
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}">
<style>
.title {{ font: 700 30px "Noto Sans CJK SC", "Microsoft YaHei", Arial, sans-serif; fill: #FFFFFF; }}
.status {{ font: 700 22px "DejaVu Sans Mono", Consolas, monospace; fill: #FFFFFF; }}
.line-no {{ font: 400 23px "DejaVu Sans Mono", Consolas, monospace; fill: #7F8C8D; }}
.code {{ font: 400 29px "DejaVu Sans Mono", Consolas, monospace; fill: #23313F; xml:space="preserve"; }}
</style>
<rect width="{WIDTH}" height="{height}" fill="#FFFFFF"/>
<rect width="{WIDTH}" height="78" fill="{accent}"/>
<text x="54" y="49" class="title">{escape(title)}</text>
<rect x="1280" y="19" width="270" height="40" rx="20" fill="#23313F" opacity=".92"/>
<text x="1415" y="47" text-anchor="middle" class="status">{status}</text>
<rect x="40" y="96" width="110" height="{height - 136}" rx="10" fill="#F4F6F7"/>
<rect x="40" y="96" width="1520" height="{height - 136}" rx="10" fill="none" stroke="#D5D8DC" stroke-width="2"/>
{''.join(body)}
</svg>'''
```

Parse exactly 14 `systemverilog` fenced blocks in article order. Determine `illegal=True` when the immediately preceding heading begins with `#### 坑` and the following prose contains `**为什么错：**`, or when the code contains the text `illegal:`. Generate SVG and invoke:

```python
subprocess.run(
    ["rsvg-convert", "--width", "1600", "--output", str(png_path), str(svg_path)],
    check=True,
)
```

- [ ] **Step 2: Run the renderer and check the asset count**

Run:

```bash
python3 /tmp/render_systemverilog_code_images.py
find 7_13/systemverilog_task_function -maxdepth 1 -name 'code-*.png' | wc -l
find 7_13/systemverilog_task_function -maxdepth 1 -name 'code-*.svg' | wc -l
```

Expected: each count is exactly 14.

- [ ] **Step 3: Validate code assets**

Run:

```bash
xmllint --noout 7_13/systemverilog_task_function/code-*.svg
file 7_13/systemverilog_task_function/code-*.png
rg -l 'ILLEGAL / 不应使用' 7_13/systemverilog_task_function/code-*.svg
```

Expected: all SVG files are valid, all PNG files are non-empty, and the three illegal examples have red-tag source SVGs.

### Task 4: Replace article source constructs with image references

**Files:**

- Modify: `7_13/systemverilog_task_function/systemverilog_task_function_article.md`

- [ ] **Step 1: Replace all 14 fenced blocks**

Replace each `systemverilog` fenced block with a Markdown image reference in the same position. Use exactly these names in article order:

```markdown
![偶校验 function 示例](code-01-even-parity.png)
![byte-enable function 示例](code-02-byte-enable.png)
![valid-ready task 示例](code-03-send-write.png)
![struct return 示例](code-04-decode-struct.png)
![task 多输出示例](code-05-split-address.png)
![ref 参数示例](code-06-ref-counter.png)
![static lifetime 陷阱](code-07-static-task-pitfall.png)
![automatic task 修正](code-08-automatic-task.png)
![function time control 错误示例](code-09-function-time-control-illegal.png)
![task expression 错误示例](code-10-task-expression-illegal.png)
![task response 检查](code-11-task-response-check.png)
![BFM time control 错误示例](code-12-bfm-time-control-illegal.png)
![task output 返回结果](code-13-task-output-result.png)
![task 多输出接口](code-14-task-output-interface.png)
```

- [ ] **Step 2: Verify article-image integrity**

Run:

```bash
! rg -n '^```systemverilog' 7_13/systemverilog_task_function/systemverilog_task_function_article.md
rg -n '^!\\[.*\\]\\(code-[0-9]{2}-.*\\.png\\)$' \
  7_13/systemverilog_task_function/systemverilog_task_function_article.md | wc -l
```

Expected: no fenced SystemVerilog block and exactly 14 code-image references.

### Task 5: Update and validate gen_article

**Files:**

- Modify: `/home/xuchen12/.claude/skills/gen_article/SKILL.md`

- [ ] **Step 1: Add the Xiumi raster-delivery section**

Insert a `## 秀米栅格化交付` section directly after `## Format Rules` that contains:

```markdown
当用户提到“秀米”“公众号导入”“不可编辑表格”“代码图片”或“表格/代码显示会乱”时，启用秀米栅格化交付模式：

- Markdown 表格必须生成同名 SVG 源图与 PNG；正文只嵌 PNG。
- fenced code block 必须生成同名 SVG 源图与 PNG；正文只嵌 PNG，不保留可编辑代码块。
- 表格、代码图片优先保证字号、换行、缩进和移动端可读性；不得为避免换行而缩小字体。
- `illegal` / 错误反例的图片必须使用红色标题条并标注 `ILLEGAL / 不应使用`。
- 提交前校验：SVG XML 有效、PNG 非空且宽度至少 1600 px、图片链接存在、正文不含 pipe table 或 fenced code block。
```

- [ ] **Step 2: Run the green skill test**

Run:

```bash
rg -n \
  '秀米栅格化交付|代码块.*SVG.*PNG|正文只嵌 PNG|fenced code block' \
  /home/xuchen12/.claude/skills/gen_article/SKILL.md
```

Expected: matching lines prove the new Xiumi image rules are discoverable in the skill.

- [ ] **Step 3: Validate the skill frontmatter**

Run:

```bash
python3 \
  /proj/cip_nbif_dv_host_2/Users/xuchen12/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  /home/xuchen12/.claude/skills/gen_article
```

Expected: validation reports no frontmatter or name errors.

### Task 6: Final verification and publish

**Files:**

- Test: `7_13/systemverilog_task_function/`
- Test: `/home/xuchen12/.claude/skills/gen_article/SKILL.md`

- [ ] **Step 1: Run the complete validation suite**

Run:

```bash
set -e
xmllint --noout \
  7_13/systemverilog_task_function/*table.svg \
  7_13/systemverilog_task_function/code-*.svg

test "$(find 7_13/systemverilog_task_function -maxdepth 1 -name 'code-*.png' | wc -l)" -eq 14
test "$(find 7_13/systemverilog_task_function -maxdepth 1 -name 'code-*.svg' | wc -l)" -eq 14

! rg -n '^\\| .* \\|$|^```systemverilog' \
  7_13/systemverilog_task_function/systemverilog_task_function_article.md

image_count=0
while IFS= read -r image; do
  test -f "7_13/systemverilog_task_function/$image"
  image_count=$((image_count + 1))
done < <(sed -n 's/^!\\[.*\\](\\([^)]*\\))$/\\1/p' \
  7_13/systemverilog_task_function/systemverilog_task_function_article.md)
test "$image_count" -eq 18

git diff --check
```

Expected: valid image sources, 14 code image pairs, 18 total Markdown image assets, no table/code constructs, and no whitespace errors.

- [ ] **Step 2: Commit and push**

Run:

```bash
git add \
  7_13/systemverilog_task_function \
  docs/superpowers/specs/2026-07-14-systemverilog-xiumi-code-images-and-skill-design.md \
  docs/superpowers/plans/2026-07-14-systemverilog-xiumi-code-images-and-skill.md
git commit -m "Add Xiumi-ready SystemVerilog code images"
git push origin main
```

Expected: GitHub `main` contains image-only tables/code article and the skill file is updated in its configured skill directory.
