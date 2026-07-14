# SystemVerilog 文章秀米代码图片化与 gen_article Skill 更新设计

## 目标

将 SystemVerilog `task` / `function` 文章改为完全适合秀米导入的图片化版：

- 两张横向表格使用更大的文字与自动换行。
- 全部 14 个 `systemverilog` 代码块转换为不可编辑的 PNG。
- 更新现有 `$gen_article` skill，使后续微信公众号技术文章默认遵守同一套表格与代码栅格化规则。

## 文章输出

### 表格

保留现有的两张横向表格 PNG 与 SVG 源文件，但重新布局：

- 保持 1600 px 宽。
- 核心差异表：标题 40 px、表头 35 px、单元格 31 px。
- RTL / DV 选型表：标题 40 px、表头 35 px、单元格 29 px。
- 长场景名与长原因文本使用两行 `tspan`，增加对应行高，不缩小字体、不截断文字。
- `function` 保持蓝色强调，`task` 保持橙色强调。

### 代码块

将 14 个代码块各自生成为一张 PNG，并保留对应 SVG 源图：

- 文件前缀：`code-01-` 至 `code-14-`。
- 宽度：1600 px；高度按行数自动增长。
- 白底、深灰等宽字体、浅灰行号区、顶部 `SystemVerilog` 标签。
- 正常示例使用蓝色标题条。
- `illegal` 反例使用红色标题条与 `ILLEGAL / 不应使用` 标记。
- 保留原有代码文本、缩进、空行、注释与关键字；不在图片中插入项目私有名词。
- 文章正文将每个 fenced code block 替换为同名 PNG 的 Markdown 图片链接。

SVG 源图中的 `text` 节点是这些代码图片的可维护源；文章正文与秀米导入版本只引用 PNG，不包含可编辑代码块。

## Markdown 变更

文章中不再保留 pipe table 或 fenced `systemverilog` code block。保留段落、标题、两张既有流程 SVG 和新图片的 alt text。

## gen_article Skill 更新

更新 `/home/xuchen12/.claude/skills/gen_article/SKILL.md`，增加一个简洁的“秀米栅格化交付”规则：

1. 当用户提到秀米、公众号导入、不可编辑表格、代码图片，启用该模式。
2. Markdown 表格必须生成可编辑 SVG 源图与 PNG；PNG 用于文章正文。
3. 代码块必须生成 SVG 源图与 PNG；正文只嵌 PNG，源代码保留在 SVG 的文字节点。
4. 表格与代码图片优先保证字号、换行、缩进和移动端可读性；不可为避免换行而缩小字体。
5. 提交前必须校验 SVG XML、PNG 非空与尺寸、所有图片链接存在、正文不含 pipe table 或 fenced code block。

现有的内容脱敏、目录结构、封面和图像检查规则保持不变。

## 验收

- 两张更新后的表格 PNG 均为 1600 px 宽，且字体比当前版本更大。
- 14 张代码 PNG 与 14 份代码 SVG 源图存在，图片尺寸非空。
- 所有 `ILLEGAL` 代码图片有清晰的红色标识。
- 文章正文不含 pipe table 或 `systemverilog` fenced code block，且所有图片链接存在。
- `$gen_article` skill 的基线检查能证明新增秀米栅格化规则在修改前缺失、修改后存在。
- `git diff --check` 通过，并将更新推送至 GitHub `main`。
