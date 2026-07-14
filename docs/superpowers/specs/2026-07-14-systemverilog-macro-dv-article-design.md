# SystemVerilog 宏定义与 DV 应用文章设计

## 目标

生成一篇 `[SV]` 微信公众号技术文章，解释 SystemVerilog 预处理宏的编译前文本替换语义，以及它们在 DV/UVM 环境中的正确使用边界。

## 内容

- 从 `` `define ``、参数化宏、`` `ifdef `` / `` `ifndef ``、`` `include `` 解释 preprocessor 的工作位置。
- 区分 macro、parameter、runtime variable、UVM configuration 的生效时间与适用范围。
- 使用抽象 DV 场景说明 feature switch、assertion、coverage、日志包装和 regression compile option。
- 说明常见风险：全局命名空间污染、include 顺序、参数重复求值、宏不适合 runtime test selection。
- 结尾给出“什么时候用 macro，什么时候不用”的决策图与验证关注点。

## 交付

目录：`7_14/systemverilog_macro/`

- `systemverilog_macro_article.md`
- `cover_systemverilog_macro.png`
- `macro-preprocess-flow.drawio` 与对应 PNG
- `macro-vs-parameter-decision.drawio` 与对应 PNG
- 大字号表格 PNG/SVG
- 每段代码示例的 PNG/SVG

## 秀米规则

- 正文不含 Markdown table 或 fenced code block。
- 表格、代码、流程图均采用大字号图片。
- 代码图片宽度至少 1600 px；表格正文至少 34 px；流程图正文至少 20 px。
- 所有例子仅用语义化名称，不包含项目私有代码、地址、寄存器或项目代号。
