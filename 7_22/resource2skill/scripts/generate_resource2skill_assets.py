#!/usr/bin/env python3
"""Generate the Resource2Skill article SVG assets and one editable draw.io source."""

from __future__ import annotations

from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

BG = "#F5F8F6"
INK = "#102A25"
MUTED = "#58706A"
GREEN = "#0A5A48"
GREEN_2 = "#159477"
MINT = "#D4F7E0"
TEAL = "#0F766E"
BLUE = "#2563EB"
PURPLE = "#6D28D9"
ORANGE = "#D97706"
RED = "#B42318"
LINE = "#B9CDC6"


def svg_doc(width: int, height: int, body: str, background: str = BG) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<defs>
  <linearGradient id="coverGradient" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#0A5A48"/>
    <stop offset="100%" stop-color="#159477"/>
  </linearGradient>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
    <feDropShadow dx="0" dy="10" stdDeviation="12" flood-color="#173E35" flood-opacity="0.14"/>
  </filter>
  <marker id="arrow" markerWidth="14" markerHeight="14" refX="10" refY="7" orient="auto">
    <path d="M 0 0 L 12 7 L 0 14 z" fill="#5B716A"/>
  </marker>
</defs>
<rect width="100%" height="100%" fill="{background}"/>
{body}
</svg>
"""


def rect(x: int, y: int, w: int, h: int, fill: str, stroke: str = "none", radius: int = 28, shadow: bool = False) -> str:
    filt = ' filter="url(#shadow)"' if shadow else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="3"{filt}/>'


def line(x1: int, y1: int, x2: int, y2: int, color: str = "#5B716A", width: int = 6, arrow: bool = True) -> str:
    marker = ' marker-end="url(#arrow)"' if arrow else ""
    return f'<path d="M {x1} {y1} L {x2} {y2}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round"{marker}/>'


def text(x: int, y: int, value: str, size: int = 30, color: str = INK, weight: int = 500, anchor: str = "start") -> str:
    return f'<text x="{x}" y="{y}" font-family="Noto Sans CJK SC, Microsoft YaHei, Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escape(value)}</text>'


def multiline(x: int, y: int, values: list[str], size: int = 30, color: str = INK, weight: int = 500, leading: int | None = None, anchor: str = "start") -> str:
    leading = leading or int(size * 1.45)
    parts = [f'<text x="{x}" y="{y}" font-family="Noto Sans CJK SC, Microsoft YaHei, Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">']
    for index, value in enumerate(values):
        dy = "0" if index == 0 else str(leading)
        parts.append(f'<tspan x="{x}" dy="{dy}">{escape(value)}</tspan>')
    parts.append("</text>")
    return "".join(parts)


def pill(x: int, y: int, w: int, value: str, fill: str, color: str = "#FFFFFF") -> str:
    return rect(x, y, w, 52, fill, radius=26) + text(x + w // 2, y + 35, value, 24, color, 700, "middle")


def save(name: str, content: str) -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / name).write_text(content, encoding="utf-8")


def cover() -> str:
    body = [
        '<rect width="1600" height="900" fill="url(#coverGradient)"/>',
        '<circle cx="1280" cy="190" r="310" fill="#5EE4B0" opacity="0.12"/>',
        '<circle cx="1450" cy="690" r="360" fill="#D4F7E0" opacity="0.08"/>',
        text(100, 130, "AGENT SKILL ENGINEERING", 26, "#A7E8C6", 800),
        multiline(100, 320, ["人类教程，怎样变成", "Agent 真正会用的 Skill？"], 76, "#E5FBEF", 800, 102),
        text(104, 555, "Resource2Skill：从资源到可执行技能", 36, "#D4F7E0", 500),
        pill(104, 650, 180, "视频", "#0B765F"),
        pill(310, 650, 180, "文章", "#0B765F"),
        pill(516, 650, 180, "代码", "#0B765F"),
        line(710, 676, 830, 676, "#B9F2D2", 7),
        rect(870, 585, 285, 184, "#E5FBEF", radius=32, shadow=True),
        text(1012, 657, "Skill Wiki", 34, GREEN, 800, "middle"),
        text(1012, 711, "+ 可执行资产", 28, TEAL, 600, "middle"),
        line(1170, 676, 1280, 676, "#B9F2D2", 7),
        rect(1310, 618, 178, 116, "#0C3F35", radius=58),
        text(1399, 688, "Run", 34, "#E5FBEF", 800, "middle"),
        text(100, 824, "把“看过”变成“检索、组合、执行过”。", 30, "#B8F0D0", 500),
    ]
    return svg_doc(1600, 900, "".join(body), background=GREEN)


def pipeline() -> str:
    body = [
        text(90, 86, "Resource2Skill 的主线：资源不是直接塞给 Agent，而是先变成可管理的 Skill", 44, INK, 800),
        text(90, 132, "每一步都补上“能否使用、如何查找、是否可追溯、怎样执行”的缺口。", 28, MUTED, 500),
        rect(90, 215, 300, 560, "#E7F8F0", "#8CC9AA", shadow=True),
        pill(122, 246, 146, "输入资源", GREEN),
        multiline(132, 356, ["教程视频", "文章与参考资料", "代码与静态资产"], 30, INK, 650, 62),
        text(132, 644, "人类容易理解", 27, TEAL, 700),
        text(132, 690, "机器难以直接复用", 27, MUTED, 500),
        line(402, 497, 490, 497, "#5B716A", 7),
        text(446, 458, "采集", 26, MUTED, 700, "middle"),
        rect(500, 215, 300, 560, "#FFF3E6", "#F0B76E", shadow=True),
        pill(532, 246, 172, "Candidate Skill", ORANGE),
        multiline(542, 356, ["来源 URL / 作者", "代码、文本、视觉素材", "许可证与适用范围"], 29, INK, 650, 62),
        text(542, 644, "先保留上下文", 27, ORANGE, 700),
        text(542, 690, "再决定是否可收录", 27, MUTED, 500),
        line(812, 497, 900, 497, "#5B716A", 7),
        text(856, 458, "清洗 / QA", 26, MUTED, 700, "middle"),
        rect(910, 215, 385, 560, "#EAF1FF", "#8FB3F4", shadow=True),
        pill(942, 246, 172, "Skill Wiki", BLUE),
        multiline(952, 356, ["meta：来源、许可、标签", "text：概览与适用条件", "visual：参考图", "code：可读的实现资产"], 28, INK, 650, 57),
        text(952, 644, "不确定或不合规的项", 27, BLUE, 700),
        text(952, 690, "进入 quarantine，不进索引", 27, MUTED, 500),
        line(1306, 497, 1394, 497, "#5B716A", 7),
        text(1350, 458, "检索 / 组合", 26, MUTED, 700, "middle"),
        rect(1404, 215, 306, 560, "#EEE8FF", "#B6A4E6", shadow=True),
        pill(1436, 246, 205, "Agent Runtime", PURPLE),
        multiline(1448, 356, ["任务拆解", "BM25 候选池", "LLM 重排序", "MCP 调真实工具"], 29, INK, 650, 57),
        text(1448, 644, "最终产生", 27, PURPLE, 700),
        text(1448, 690, "网页 / PPT / 表格 / 场景 / 音频", 24, MUTED, 500),
        rect(118, 838, 1470, 104, "#113D34", radius=28),
        text(853, 904, "关键不是“把资料喂进模型”，而是把资料沉淀成可发现、可执行、可审计的中间层。", 32, "#E5FBEF", 650, "middle"),
    ]
    return svg_doc(1800, 1020, "".join(body))


def wiki_library() -> str:
    body = [
        text(90, 86, "为什么要同时维护 Skill Wiki 和 Skill Library？", 46, INK, 800),
        text(90, 132, "它们不是重复存储：一个负责“知道该选什么”，另一个负责“真正把事情做出来”。", 28, MUTED, 500),
        rect(120, 214, 720, 650, "#EAF1FF", "#8FB3F4", shadow=True),
        rect(120, 214, 720, 104, BLUE, radius=28),
        text(480, 282, "Skill Wiki：给 Agent 的技能说明书与索引", 32, "#FFFFFF", 800, "middle"),
        rect(168, 360, 246, 408, "#FFFFFF", "#B7D0FB", radius=22),
        text(291, 425, "一个技能目录", 29, BLUE, 800, "middle"),
        multiline(206, 488, ["meta.json", "text/", "overview.md", "visual/...", "code/..."], 28, INK, 650, 54),
        rect(462, 360, 320, 408, "#F7FAFF", "#B7D0FB", radius=22),
        multiline(500, 425, ["它回答：", "• 适用于什么任务？", "• 来源与许可证是什么？", "• 有没有视觉参考？", "• 是否通过", "  可执行检查？"], 26, INK, 650, 52),
        text(480, 824, "检索、筛选、可追溯", 32, BLUE, 800, "middle"),
        rect(960, 214, 720, 650, "#E7F8F0", "#8CC9AA", shadow=True),
        rect(960, 214, 720, 104, GREEN, radius=28),
        text(1320, 282, "Skill Library：给工具调用的可执行资产", 32, "#FFFFFF", 800, "middle"),
        rect(1008, 360, 246, 408, "#FFFFFF", "#9FD5B7", radius=22),
        text(1131, 425, "运行时资产", 29, GREEN, 800, "middle"),
        multiline(1046, 500, ["Python 组件", "模板 / 预设", "主题 / 公式", "场景脚手架"], 28, INK, 650, 64),
        rect(1302, 360, 320, 408, "#F4FCF7", "#9FD5B7", radius=22),
        multiline(1340, 435, ["它负责：", "• 写入项目文件", "• 创建工作区", "• 调用领域工具", "• 产出最终 Artifact"], 28, INK, 650, 62),
        text(1320, 824, "执行、落地、生成文件", 32, GREEN, 800, "middle"),
        line(838, 538, 956, 538, "#506C64", 8),
        text(897, 500, "skill_id", 27, MUTED, 800, "middle"),
        rect(220, 922, 1360, 86, "#113D34", radius=28),
        text(900, 978, "可以把 Wiki 看成“带证据的目录”，把 Library 看成“能被工具调用的工具箱”。", 32, "#E5FBEF", 650, "middle"),
    ]
    return svg_doc(1800, 1060, "".join(body))


def runtime() -> str:
    body = [
        text(90, 86, "一次真实任务在运行时怎样流过 Resource2Skill？", 46, INK, 800),
        text(90, 132, "以“做一个网页”为例：Agent 先决定需要哪些能力，再用可执行资产把页面组起来。", 28, MUTED, 500),
        rect(95, 218, 290, 190, "#FFF3E6", "#F0B76E", shadow=True),
        pill(125, 242, 74, "1", ORANGE),
        multiline(125, 330, ["用户 Brief", "“做一个公益组织落地页”"], 28, INK, 700, 52),
        line(397, 313, 467, 313, "#5B716A", 7),
        rect(478, 218, 290, 190, "#EEE8FF", "#B6A4E6", shadow=True),
        pill(508, 242, 74, "2", PURPLE),
        multiline(508, 330, ["Task Planner", "拆成 hero、活动、FAQ…"], 28, INK, 700, 52),
        line(780, 313, 850, 313, "#5B716A", 7),
        rect(861, 218, 290, 190, "#EAF1FF", "#8FB3F4", shadow=True),
        pill(891, 242, 74, "3", BLUE),
        multiline(891, 330, ["先检索", "BM25 找候选技能"], 28, INK, 700, 52),
        line(1163, 313, 1233, 313, "#5B716A", 7),
        rect(1244, 218, 290, 190, "#E7F8F0", "#8CC9AA", shadow=True),
        pill(1274, 242, 74, "4", GREEN),
        multiline(1274, 330, ["再重排序", "LLM 选出更贴合的 skill_id"], 26, INK, 700, 52),
        line(1390, 420, 1390, 514, "#5B716A", 7),
        rect(1244, 528, 290, 190, "#F2F5F4", "#B9CDC6", shadow=True),
        pill(1274, 552, 74, "5", TEAL),
        multiline(1274, 638, ["按 section 组合", "并把代码写入工作区"], 27, INK, 700, 52),
        line(1233, 623, 1163, 623, "#5B716A", 7),
        rect(861, 528, 290, 190, "#EAF1FF", "#8FB3F4", shadow=True),
        pill(891, 552, 74, "6", BLUE),
        multiline(891, 638, ["MCP / Adapter", "调用领域实际工具"], 28, INK, 700, 52),
        line(850, 623, 780, 623, "#5B716A", 7),
        rect(478, 528, 290, 190, "#E7F8F0", "#8CC9AA", shadow=True),
        pill(508, 552, 74, "7", GREEN),
        multiline(508, 638, ["产物生成", "HTML、样式、资源文件"], 28, INK, 700, 52),
        line(397, 623, 327, 623, "#5B716A", 7),
        rect(95, 528, 290, 190, "#FFF3E6", "#F0B76E", shadow=True),
        pill(125, 552, 74, "8", ORANGE),
        multiline(125, 638, ["检查与反思", "必要时换技能或再生成"], 28, INK, 700, 52),
        rect(160, 800, 1480, 118, "#113D34", radius=28),
        multiline(900, 850, ["这里的“组合”很重要：不是找一个万能 Skill，而是让多个小能力按任务结构协作。", "Web 域还提供面向页面组合与视觉检查的流程。"], 29, "#E5FBEF", 500, 44, "middle"),
    ]
    return svg_doc(1800, 990, "".join(body))


def code_demo() -> str:
    code_lines = [
        ("# Python 3.11 环境中安装依赖", "#91E3B0"),
        ("python -m pip install -r requirements.txt", "#F0F6F4"),
        ("python -m playwright install chromium", "#F0F6F4"),
        ("", "#F0F6F4"),
        ("# 用 Web Domain 生成一个实际项目", "#91E3B0"),
        ("python cli.py agent \\", "#F0F6F4"),
        ('  --domain web \\', "#F0F6F4"),
        ('  --task "Build a one-page landing site for a nonprofit..." \\', "#F0F6F4"),
        ("  --model gpt-5.4 --reasoning low --max-iter 40", "#F0F6F4"),
    ]
    body = [
        rect(70, 54, 1660, 720, "#102A25", "#234C42", radius=28, shadow=True),
        rect(70, 54, 1660, 76, "#173E35", radius=28),
        '<circle cx="116" cy="92" r="12" fill="#FF6B6B"/>',
        '<circle cx="154" cy="92" r="12" fill="#F7B955"/>',
        '<circle cx="192" cy="92" r="12" fill="#5FE08A"/>',
        text(900, 100, "Resource2Skill · README Quick Start", 28, "#CBEADB", 650, "middle"),
    ]
    y = 195
    for value, color in code_lines:
        body.append(text(132, y, value or " ", 28, color, 500))
        y += 58
    body.extend([
        rect(70, 822, 1660, 116, "#E7F8F0", "#8CC9AA", radius=28),
        text(900, 894, "命令来自项目 README：它展示的是“由 Agent 编排真实工具、把生成物写到 demo/<domain>/”的最小入口。", 28, GREEN, 650, "middle"),
    ])
    return svg_doc(1800, 990, "".join(body))


def drawio_pipeline() -> str:
    return """<mxfile host="app.diagrams.net" modified="2026-07-22T00:00:00.000Z" agent="Resource2Skill article" version="26.0.16">
  <diagram id="resource2skill-pipeline" name="Resource2Skill pipeline">
    <mxGraphModel dx="1600" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1800" pageHeight="1020" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="title" value="Resource2Skill：从人类资源到可执行 Skill" style="text;html=1;align=left;verticalAlign=middle;fontSize=42;fontStyle=1;fontColor=#102A25;" vertex="1" parent="1"><mxGeometry x="80" y="45" width="1120" height="70" as="geometry"/></mxCell>
        <mxCell id="resources" value="输入资源&lt;br&gt;&lt;br&gt;教程视频&lt;br&gt;文章与参考资料&lt;br&gt;代码与静态资产" style="swimlane;html=1;rounded=1;startSize=55;fillColor=#E7F8F0;swimlaneFillColor=#0A5A48;fontColor=#FFFFFF;strokeColor=#8CC9AA;strokeWidth=2;fontSize=28;align=center;verticalAlign=middle;shadow=1;" vertex="1" parent="1"><mxGeometry x="90" y="220" width="285" height="440" as="geometry"/></mxCell>
        <mxCell id="candidate" value="Candidate Skill&lt;br&gt;&lt;br&gt;来源 / 许可&lt;br&gt;代码、文本、视觉素材&lt;br&gt;适用范围" style="swimlane;html=1;rounded=1;startSize=55;fillColor=#FFF3E6;swimlaneFillColor=#D97706;fontColor=#FFFFFF;strokeColor=#F0B76E;strokeWidth=2;fontSize=28;align=center;verticalAlign=middle;shadow=1;" vertex="1" parent="1"><mxGeometry x="470" y="220" width="300" height="440" as="geometry"/></mxCell>
        <mxCell id="wiki" value="Skill Wiki&lt;br&gt;&lt;br&gt;meta / text / visual / code&lt;br&gt;标签、来源、许可证&lt;br&gt;QA 与 quarantine" style="swimlane;html=1;rounded=1;startSize=55;fillColor=#EAF1FF;swimlaneFillColor=#2563EB;fontColor=#FFFFFF;strokeColor=#8FB3F4;strokeWidth=2;fontSize=28;align=center;verticalAlign=middle;shadow=1;" vertex="1" parent="1"><mxGeometry x="865" y="220" width="330" height="440" as="geometry"/></mxCell>
        <mxCell id="runtime" value="Agent Runtime&lt;br&gt;&lt;br&gt;任务拆解&lt;br&gt;检索与重排序&lt;br&gt;MCP 调用真实工具" style="swimlane;html=1;rounded=1;startSize=55;fillColor=#EEE8FF;swimlaneFillColor=#6D28D9;fontColor=#FFFFFF;strokeColor=#B6A4E6;strokeWidth=2;fontSize=28;align=center;verticalAlign=middle;shadow=1;" vertex="1" parent="1"><mxGeometry x="1290" y="220" width="320" height="440" as="geometry"/></mxCell>
        <mxCell id="edge1" value="采集" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;fontSize=28;fontColor=#58706A;strokeColor=#5B716A;strokeWidth=3;endArrow=block;endFill=1;" edge="1" parent="1" source="resources" target="candidate"><mxGeometry relative="1" as="geometry"/></mxCell>
        <mxCell id="edge2" value="清洗 / QA" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;fontSize=28;fontColor=#58706A;strokeColor=#5B716A;strokeWidth=3;endArrow=block;endFill=1;" edge="1" parent="1" source="candidate" target="wiki"><mxGeometry relative="1" as="geometry"/></mxCell>
        <mxCell id="edge3" value="检索 / 组合" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;fontSize=28;fontColor=#58706A;strokeColor=#5B716A;strokeWidth=3;endArrow=block;endFill=1;" edge="1" parent="1" source="wiki" target="runtime"><mxGeometry relative="1" as="geometry"/></mxCell>
        <mxCell id="footer" value="资源先被治理为可发现、可执行、可审计的 Skill，Agent 才能稳定复用。" style="rounded=1;html=1;fillColor=#113D34;fontColor=#E5FBEF;strokeColor=#113D34;fontSize=30;align=center;verticalAlign=middle;" vertex="1" parent="1"><mxGeometry x="220" y="790" width="1300" height="82" as="geometry"/></mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
"""


def main() -> None:
    save("resource2skill-cover.svg", cover())
    save("resource2skill-pipeline.svg", pipeline())
    save("resource2skill-wiki-library.svg", wiki_library())
    save("resource2skill-runtime.svg", runtime())
    save("resource2skill-cli-demo.svg", code_demo())
    save("resource2skill-pipeline.drawio", drawio_pipeline())


if __name__ == "__main__":
    main()
