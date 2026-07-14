# SystemVerilog 文章表格图片化设计

## 目标

将 `7_13/systemverilog_task_function/systemverilog_task_function_article.md` 中的两张 Markdown 表格改为适合秀米和微信公众号导入的横向 PNG 信息图，避免 Markdown 表格在富文本编辑器中丢失列宽、代码样式或对齐关系。

## 范围

处理以下两张表：

1. `function` 与 `task` 的五行核心差异对比表。
2. RTL / DV 场景选型表。

文章中其余代码块、段落、SVG 流程图和可编辑 draw.io 源图不改动。

## 输出

- `function-vs-task-comparison-table.svg`：核心差异表的可编辑矢量源图。
- `function-vs-task-comparison-table.png`：用于秀米导入的 1600 px 宽 PNG。
- `rtl-dv-function-task-selection-table.svg`：RTL / DV 选型表的可编辑矢量源图。
- `rtl-dv-function-task-selection-table.png`：用于秀米导入的 1600 px 宽 PNG。

## 视觉规范

- 横向 1600 px 宽布局，白底、深蓝表头、淡灰分隔线。
- `function` 列使用蓝色强调，`task` 列使用橙色强调。
- 使用清晰的无衬线字体；代码术语保留等宽或明确的英文样式。
- 按单元格内容自动增加行高，确保手机端缩放后仍可读。
- 两张 PNG 直接由同名 SVG 渲染；SVG 保留供后续调整文本与颜色。

## Markdown 更新

两处表格将分别替换为：

```markdown
![function 与 task 核心差异表](function-vs-task-comparison-table.png)
```

和：

```markdown
![RTL / DV 场景选型表](rtl-dv-function-task-selection-table.png)
```

图片文件与文章位于同一目录，因此秀米可直接使用导出的 PNG，GitHub 也可正确渲染对应链接。

## 验收

- 两个 SVG 文件为有效 XML。
- 两个 PNG 文件非空，宽度为 1600 px。
- Markdown 不再包含原来的 pipe table 行。
- 两个新的图片链接均指向存在的 PNG 文件。
- `git diff --check` 无 whitespace error。
