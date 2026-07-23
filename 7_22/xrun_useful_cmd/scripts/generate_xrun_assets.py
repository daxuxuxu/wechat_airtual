#!/usr/bin/env python3
"""Generate SVG/PNG-ready assets for the standalone xrun article."""

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
BLUE = "#2563EB"
PURPLE = "#6D28D9"
ORANGE = "#D97706"
RED = "#B42318"


def doc(width: int, height: int, body: str, background: str = BG) -> str:
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


def text(x: int, y: int, value: str, size: int = 30, color: str = INK, weight: int = 500, anchor: str = "start") -> str:
    return f'<text x="{x}" y="{y}" font-family="Noto Sans CJK SC, Microsoft YaHei, Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escape(value)}</text>'


def multi(x: int, y: int, values: list[str], size: int = 30, color: str = INK, weight: int = 500, leading: int | None = None, anchor: str = "start") -> str:
    leading = leading or int(size * 1.45)
    out = [f'<text x="{x}" y="{y}" font-family="Noto Sans CJK SC, Microsoft YaHei, Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">']
    for index, value in enumerate(values):
        out.append(f'<tspan x="{x}" dy="{"0" if index == 0 else leading}">{escape(value)}</tspan>')
    out.append("</text>")
    return "".join(out)


def arrow(x1: int, y1: int, x2: int, y2: int, color: str = "#5B716A", width: int = 7) -> str:
    return f'<path d="M {x1} {y1} L {x2} {y2}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" marker-end="url(#arrow)"/>'


def pill(x: int, y: int, w: int, value: str, fill: str) -> str:
    return rect(x, y, w, 52, fill, radius=26) + text(x + w // 2, y + 35, value, 24, "#FFFFFF", 800, "middle")


def save(name: str, value: str) -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / name).write_text(value, encoding="utf-8")


def cover() -> str:
    body = [
        '<rect width="1600" height="900" fill="url(#coverGradient)"/>',
        '<circle cx="1360" cy="160" r="300" fill="#D4F7E0" opacity="0.08"/>',
        '<circle cx="1430" cy="710" r="330" fill="#74E7B8" opacity="0.10"/>',
        text(100, 130, "XCELIUM · XRUN", 26, "#A7E8C6", 800),
        multi(100, 320, ["xrun 命令为什么", "越写越长？"], 82, "#E5FBEF", 800, 104),
        text(104, 546, "先把 Compile、Elaborate、Run 分开", 38, "#D4F7E0", 500),
        rect(100, 640, 282, 108, "#0B765F", radius=28),
        text(241, 708, "Compile", 34, "#E5FBEF", 800, "middle"),
        arrow(404, 694, 500, 694, "#B9F2D2", 7),
        rect(522, 640, 310, 108, "#0B765F", radius=28),
        text(677, 708, "Elaborate", 34, "#E5FBEF", 800, "middle"),
        arrow(854, 694, 950, 694, "#B9F2D2", 7),
        rect(972, 640, 220, 108, "#0B765F", radius=28),
        text(1082, 708, "Run", 34, "#E5FBEF", 800, "middle"),
        text(100, 824, "用 option file 管住构建差异，用 plusarg 管住 test 差异。", 30, "#B8F0D0", 500),
    ]
    return doc(1600, 900, "".join(body), GREEN)


def stages() -> str:
    body = [
        text(90, 86, "xrun 的关键：同一个入口，驱动三个不同阶段", 46, INK, 800),
        text(90, 132, "不要把所有 option 都当成“运行参数”。它们在不同阶段生效，能解决的问题也不同。", 28, MUTED, 500),
        rect(105, 230, 470, 480, "#EAF1FF", "#8FB3F4", shadow=True),
        pill(140, 258, 178, "Compile", BLUE),
        multi(150, 380, ["读源文件与 package", "解析 SystemVerilog", "处理 include / define", "决定哪些内容进入库"], 31, INK, 650, 65),
        text(150, 654, "典型：-sv、-f、+incdir+、+define+", 25, BLUE, 700),
        arrow(587, 470, 685, 470),
        text(636, 432, "构建", 26, MUTED, 700, "middle"),
        rect(705, 230, 470, 480, "#EEE8FF", "#B6A4E6", shadow=True),
        pill(740, 258, 196, "Elaborate", PURPLE),
        multi(750, 380, ["确定 top 与层级", "连接 module / interface", "准备 debug 可见性", "插入覆盖率等 instrumentation"], 31, INK, 650, 65),
        text(750, 654, "典型：-top、-access、coverage 相关配置", 25, PURPLE, 700),
        arrow(1187, 470, 1285, 470),
        text(1236, 432, "启动", 26, MUTED, 700, "middle"),
        rect(1305, 230, 390, 480, "#E7F8F0", "#8CC9AA", shadow=True),
        pill(1340, 258, 112, "Run", GREEN),
        multi(1350, 380, ["选择 UVM test", "设置随机 seed", "控制 timeout / verbosity", "执行并产生 log / wave"], 31, INK, 650, 65),
        text(1350, 654, "典型：test name、seed、timeout", 24, GREEN, 700),
        rect(155, 790, 1490, 112, "#113D34", radius=28),
        text(900, 861, "判断口诀：需要重新建构仿真模型的，放在 Compile / Elaborate；只改变这一次 test 行为的，放在 Run。", 29, "#E5FBEF", 650, "middle"),
    ]
    return doc(1800, 970, "".join(body))


def option_files() -> str:
    body = [
        text(90, 86, "把长命令拆成四份 option file，差异才可追踪", 46, INK, 800),
        text(90, 132, "文件名只是团队约定；真正重要的是每一份文件只放同一生效阶段的配置。", 28, MUTED, 500),
        rect(100, 220, 365, 480, "#EAF1FF", "#8FB3F4", shadow=True),
        pill(132, 248, 210, "compfiles.f", BLUE),
        multi(142, 368, ["源文件顺序", "package / interface", "RTL 与 testbench", "第三方模型"], 30, INK, 650, 63),
        text(142, 638, "回答：编什么？", 30, BLUE, 800),
        rect(505, 220, 365, 480, "#FFF3E6", "#F0B76E", shadow=True),
        pill(537, 248, 206, "compopts.f", ORANGE),
        multi(547, 368, ["-sv / -64bit", "+incdir+", "+define+", "语言与编译策略"], 30, INK, 650, 63),
        text(547, 638, "回答：怎样编？", 30, ORANGE, 800),
        rect(930, 220, 365, 480, "#EEE8FF", "#B6A4E6", shadow=True),
        pill(962, 248, 204, "elabopts.f", PURPLE),
        multi(972, 368, ["-top", "-access +rwc", "coverage / bind", "结构与可见性"], 30, INK, 650, 63),
        text(972, 638, "回答：建成什么模型？", 30, PURPLE, 800),
        rect(1335, 220, 365, 480, "#E7F8F0", "#8CC9AA", shadow=True),
        pill(1367, 248, 194, "runopts.f", GREEN),
        multi(1377, 368, ["Tcl input", "log / wave policy", "默认 UVM runtime", "运行期行为"], 30, INK, 650, 63),
        text(1377, 638, "回答：这次怎么跑？", 30, GREEN, 800),
        arrow(280, 762, 1510, 762, "#5B716A", 7),
        text(900, 730, "xrun -f compfiles.f -f compopts.f -f elabopts.f -f runopts.f", 30, INK, 700, "middle"),
        rect(210, 838, 1380, 88, "#113D34", radius=28),
        text(900, 895, "test name、seed 这类单次变化放在命令行或 run config，避免为每个 test 重编一次。", 30, "#E5FBEF", 650, "middle"),
    ]
    return doc(1800, 980, "".join(body))


def debug_wave() -> str:
    body = [
        text(90, 86, "最常见误解：-access、-gui 和 waveform 不是一回事", 46, INK, 800),
        text(90, 132, "可见性让你“有资格看”；probe 才决定“有没有把信号录下来”。", 28, MUTED, 500),
        rect(115, 246, 330, 368, "#EAF1FF", "#8FB3F4", shadow=True),
        pill(145, 274, 176, "-access", BLUE),
        multi(155, 390, ["保留 read / write /", "connectivity 等", "debug access", "不会自动 dump wave"], 30, INK, 650, 58),
        arrow(457, 430, 555, 430),
        text(506, 394, "可见", 26, MUTED, 700, "middle"),
        rect(575, 246, 330, 368, "#FFF3E6", "#F0B76E", shadow=True),
        pill(605, 274, 126, "probe", ORANGE),
        multi(615, 390, ["选择 scope", "选择信号与深度", "写入 SHM", "控制记录范围"], 30, INK, 650, 58),
        arrow(917, 430, 1015, 430),
        text(966, 394, "录制", 26, MUTED, 700, "middle"),
        rect(1035, 246, 330, 368, "#E7F8F0", "#8CC9AA", shadow=True),
        pill(1065, 274, 160, "waves.shm", GREEN),
        multi(1075, 390, ["仿真数据库", "可供 post-process", "在 SimVision 中", "打开查看"], 30, INK, 650, 58),
        arrow(1377, 430, 1475, 430),
        text(1426, 394, "分析", 26, MUTED, 700, "middle"),
        rect(1495, 246, 200, 368, "#EEE8FF", "#B6A4E6", shadow=True),
        pill(1525, 274, 108, "GUI", PURPLE),
        multi(1530, 412, ["SimVision", "看波形", "查 driver", "定位问题"], 29, INK, 650, 56),
        rect(205, 742, 1390, 112, "#113D34", radius=28),
        multi(900, 790, ["-gui 只是以 GUI 模式启动；batch run 想保留波形，仍要明确配置 probe / waveform database。", "probe 范围越大，数据库与 runtime 开销通常也越大。"], 29, "#E5FBEF", 500, 42, "middle"),
    ]
    return doc(1800, 930, "".join(body))


def command_demo() -> str:
    lines = [
        ("# 以四份 option file 启动一次 UVM smoke", "#91E3B0"),
        ("xrun \\", "#F0F6F4"),
        ("  -f snippets/compfiles.f \\", "#F0F6F4"),
        ("  -f snippets/compopts.f \\", "#F0F6F4"),
        ("  -f snippets/elabopts.f \\", "#F0F6F4"),
        ("  -f snippets/runopts.f \\", "#F0F6F4"),
        ("  +UVM_TESTNAME=smoke_test \\", "#F0F6F4"),
        ("  +ntb_random_seed=20260722 \\", "#F0F6F4"),
        ("  -l logs/smoke_seed20260722.log", "#F0F6F4"),
    ]
    body = [
        rect(70, 52, 1660, 720, "#102A25", "#234C42", radius=28, shadow=True),
        rect(70, 52, 1660, 78, "#173E35", radius=28),
        '<circle cx="116" cy="92" r="12" fill="#FF6B6B"/>',
        '<circle cx="154" cy="92" r="12" fill="#F7B955"/>',
        '<circle cx="192" cy="92" r="12" fill="#5FE08A"/>',
        text(900, 100, "xrun · maintainable command-line example", 28, "#CBEADB", 650, "middle"),
    ]
    y = 190
    for value, color in lines:
        body.append(text(132, y, value, 28, color, 500))
        y += 58
    body.extend([
        rect(70, 820, 1660, 116, "#E7F8F0", "#8CC9AA", radius=28),
        text(900, 892, "单次 test 与 seed 在命令行覆盖；会影响 build 的 source、define、top、access 放回对应 option file。", 28, GREEN, 650, "middle"),
    ])
    return doc(1800, 990, "".join(body))


def option_code() -> str:
    body = [
        rect(70, 48, 1660, 774, "#102A25", "#234C42", radius=28, shadow=True),
        rect(70, 48, 1660, 76, "#173E35", radius=28),
        text(900, 97, "option files · split by lifecycle", 28, "#CBEADB", 650, "middle"),
        rect(110, 166, 370, 560, "#163B33", "#2F7562", radius=20),
        text(145, 218, "compfiles.f", 29, "#91E3B0", 800),
        multi(145, 284, ["./rtl/dut_pkg.sv", "./rtl/dut.sv", "./tb/tb_pkg.sv", "./tb/tb_top.sv"], 24, "#F0F6F4", 500, 58),
        rect(515, 166, 370, 560, "#163B33", "#2F7562", radius=20),
        text(550, 218, "compopts.f", 29, "#91E3B0", 800),
        multi(550, 284, ["-64bit", "-sv", "-uvm", "+incdir+./rtl", "+incdir+./tb", "+define+ENABLE_SVA"], 22, "#F0F6F4", 500, 50),
        rect(920, 166, 370, 560, "#163B33", "#2F7562", radius=20),
        text(955, 218, "elabopts.f", 29, "#91E3B0", 800),
        multi(955, 284, ["-top tb_top", "-access +rwc"], 24, "#F0F6F4", 500, 58),
        rect(1325, 166, 370, 560, "#163B33", "#2F7562", radius=20),
        text(1360, 218, "runopts.f", 29, "#91E3B0", 800),
        multi(1360, 284, ["-input snippets/probe.tcl", "+UVM_VERBOSITY=UVM_MEDIUM", "+UVM_TIMEOUT=100us,YES"], 20, "#F0F6F4", 500, 54),
        rect(70, 868, 1660, 80, "#E7F8F0", "#8CC9AA", radius=28),
        text(900, 921, "示例中的文件名与层级均为通用写法；请按自己的 top、source list 与版本规范调整。", 27, GREEN, 650, "middle"),
    ]
    return doc(1800, 990, "".join(body))


def drawio_stages() -> str:
    return """<mxfile host="app.diagrams.net" modified="2026-07-22T00:00:00.000Z" agent="xrun article" version="26.0.16">
  <diagram id="xrun-stages" name="xrun lifecycle">
    <mxGraphModel dx="1600" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1800" pageHeight="970" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="title" value="xrun：一个入口，三个不同阶段" style="text;html=1;align=left;verticalAlign=middle;fontSize=42;fontStyle=1;fontColor=#102A25;" vertex="1" parent="1"><mxGeometry x="80" y="45" width="1000" height="70" as="geometry"/></mxCell>
        <mxCell id="compile" value="Compile&lt;br&gt;&lt;br&gt;读源文件与 package&lt;br&gt;解析 SystemVerilog&lt;br&gt;处理 include / define&lt;br&gt;&lt;br&gt;-sv、-f、+incdir+、+define+" style="swimlane;html=1;rounded=1;startSize=58;fillColor=#EAF1FF;swimlaneFillColor=#2563EB;fontColor=#FFFFFF;strokeColor=#8FB3F4;strokeWidth=2;fontSize=28;align=center;verticalAlign=middle;shadow=1;" vertex="1" parent="1"><mxGeometry x="110" y="210" width="430" height="440" as="geometry"/></mxCell>
        <mxCell id="elab" value="Elaborate&lt;br&gt;&lt;br&gt;确定 top 与层级&lt;br&gt;连接 module / interface&lt;br&gt;准备 debug 可见性&lt;br&gt;&lt;br&gt;-top、-access、coverage" style="swimlane;html=1;rounded=1;startSize=58;fillColor=#EEE8FF;swimlaneFillColor=#6D28D9;fontColor=#FFFFFF;strokeColor=#B6A4E6;strokeWidth=2;fontSize=28;align=center;verticalAlign=middle;shadow=1;" vertex="1" parent="1"><mxGeometry x="685" y="210" width="430" height="440" as="geometry"/></mxCell>
        <mxCell id="run" value="Run&lt;br&gt;&lt;br&gt;选择 UVM test&lt;br&gt;设置随机 seed&lt;br&gt;控制 timeout / verbosity&lt;br&gt;&lt;br&gt;+UVM_TESTNAME、+ntb_random_seed" style="swimlane;html=1;rounded=1;startSize=58;fillColor=#E7F8F0;swimlaneFillColor=#0A5A48;fontColor=#FFFFFF;strokeColor=#8CC9AA;strokeWidth=2;fontSize=28;align=center;verticalAlign=middle;shadow=1;" vertex="1" parent="1"><mxGeometry x="1260" y="210" width="430" height="440" as="geometry"/></mxCell>
        <mxCell id="edge1" value="构建" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;fontSize=28;fontColor=#58706A;strokeColor=#5B716A;strokeWidth=3;endArrow=block;endFill=1;" edge="1" parent="1" source="compile" target="elab"><mxGeometry relative="1" as="geometry"/></mxCell>
        <mxCell id="edge2" value="启动" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;fontSize=28;fontColor=#58706A;strokeColor=#5B716A;strokeWidth=3;endArrow=block;endFill=1;" edge="1" parent="1" source="elab" target="run"><mxGeometry relative="1" as="geometry"/></mxCell>
        <mxCell id="footer" value="需要重新建构模型的 option 放在 Compile / Elaborate；只改变这次 test 行为的参数放在 Run。" style="rounded=1;html=1;fillColor=#113D34;fontColor=#E5FBEF;strokeColor=#113D34;fontSize=30;align=center;verticalAlign=middle;" vertex="1" parent="1"><mxGeometry x="210" y="770" width="1380" height="82" as="geometry"/></mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
"""


def main() -> None:
    save("xrun-cover.svg", cover())
    save("xrun-stages.svg", stages())
    save("xrun-option-files.svg", option_files())
    save("xrun-debug-wave.svg", debug_wave())
    save("xrun-command-demo.svg", command_demo())
    save("xrun-option-files-code.svg", option_code())
    save("xrun-stages.drawio", drawio_stages())


if __name__ == "__main__":
    main()
