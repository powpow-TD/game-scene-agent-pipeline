# -*- coding: utf-8 -*-
"""图 1 生成脚本（图学学报投稿用）
配色：Okabe-Ito（色盲友好）；字体：SimHei（中文）+ DejaVu Sans（西文）
修订说明：重构图 1 为竖向主流程 + 右侧状态列，反馈路径走外侧，
         彻底消除原文中"解析融合/状态回写"与箭头重叠、"导出"箭头穿框两处遮挡。
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["svg.fonttype"] = "none"

OUT = os.path.dirname(os.path.abspath(__file__))

# Okabe-Ito 色盲友好配色
OI = {
    "black": "#000000", "orange": "#E69F00", "skyblue": "#56B4E9", "green": "#009E73",
    "yellow": "#F0E442", "blue": "#0072B2", "vermillion": "#D55E00", "purple": "#CC79A7",
    "grey": "#999999",
}


def box(ax, x, y, w, h, text, fc, ec="black", fs=9, bold=False, rounded=0.02, tc="black", z=2):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.005,rounding_size={rounded}",
                       fc=fc, ec=ec, lw=1.1, zorder=z)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal",
            fontfamily="Microsoft YaHei" if bold else None,
            zorder=z + 1, color=tc, linespacing=1.4)


def arrow(ax, p1, p2, color="black", style="-|>", lw=1.3, ls="-", rad=0.0, z=1):
    a = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=12, lw=lw,
                        color=color, linestyle=ls, zorder=z,
                        connectionstyle=f"arc3,rad={rad}", shrinkA=1, shrinkB=1)
    ax.add_patch(a)


def blank_ax(figsize):
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    return fig, ax


# ============================================================ 图 1 管线总体架构（竖向主流程）
fig, ax = blank_ax((7.0, 5.0))

ax.text(0.5, 0.972, "状态感知 Agent 调度管线（感知—规划—调度—执行—更新 闭环）",
        ha="center", fontsize=11, fontweight="bold", fontfamily="Microsoft YaHei")

# ---- 主流程（中列，自上而下）----
box(ax, 0.20, 0.855, 0.36, 0.085, "高层创意意图\n（人：意图供给 + 结果审核）",
    "#FFFFFF", fs=8.5)
box(ax, 0.17, 0.685, 0.42, 0.115, "状态感知 LLM-Agent\n（全局理解 · 任务拆解 · 层级规划）",
    OI["skyblue"], fs=9, bold=True)
box(ax, 0.22, 0.505, 0.32, 0.100, "MCP 协议网关\n（调度指令下发）",
    OI["yellow"], fs=8.5, bold=True)

box(ax, 0.04, 0.285, 0.30, 0.120, "生成式世界模型\n（Marble：高斯泼溅 / 网格）",
    OI["orange"], fs=8.5, bold=True)
box(ax, 0.44, 0.285, 0.30, 0.120, "UE5 引擎\n（排布 / 编辑 / 物理配置）",
    OI["purple"], fs=8.5, bold=True, tc="white")
box(ax, 0.16, 0.085, 0.52, 0.110, "异构导出物：caption / GLB / 360° 全景图",
    "#FFFFFF", fs=8.2)

# ---- 右侧：状态接地层（贯穿中段的独立层）----
box(ax, 0.74, 0.46, 0.24, 0.42,
    "状态接地层\n(State Grounding\nLayer)\n\n结构化全局\n状态快照",
    OI["green"], fs=8.5, bold=True, tc="white")

# ---- 主流程箭头 ----
arrow(ax, (0.38, 0.855), (0.38, 0.802), color=OI["black"])          # 意图 -> Agent
arrow(ax, (0.38, 0.685), (0.38, 0.607), color=OI["black"])          # Agent -> MCP
arrow(ax, (0.28, 0.505), (0.17, 0.407), color=OI["black"], rad=0.12)   # MCP -> Marble
arrow(ax, (0.48, 0.505), (0.59, 0.407), color=OI["black"], rad=-0.12)  # MCP -> UE5
arrow(ax, (0.19, 0.285), (0.28, 0.197), color=OI["black"])          # Marble -> 导出物
arrow(ax, (0.62, 0.285), (0.58, 0.197), color=OI["black"])          # UE5 -> 导出物

# ---- 状态接地：SGL -> Agent ----
arrow(ax, (0.74, 0.800), (0.59, 0.755), color=OI["green"], lw=1.7)
ax.text(0.655, 0.828, "状态接地", fontsize=7.8, color=OI["green"], ha="center")

# ---- 状态回写：导出物 -> SGL（走右侧外侧，避免与任何框/箭头交叉）----
arrow(ax, (0.68, 0.140), (0.88, 0.140), color=OI["green"], lw=1.3, ls="--", style="-")
arrow(ax, (0.88, 0.140), (0.88, 0.458), color=OI["green"], lw=1.3, ls="--")
ax.text(0.795, 0.300, "解析融合\n状态回写", fontsize=8, color=OI["green"],
        ha="center", va="center", linespacing=1.4)

plt.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.02)

# ===== scipilot 视觉自检 =====
import sys as _sys
_sys.path.insert(0, r"D:/openscience/openscience/data-root/user-skills/scipilot-figure-skill/scripts")
try:
    from visual_qa import audit_layout as _audit
    _iss = _audit(fig)
    _bad = [i for i in _iss if i[0] in ("WARN", "FAIL")]
    _l = [f"QA[{__file__}]: {len(_bad)} issue(s)"]
    for sev, msg in _bad:
        _l.append(f"   [{sev}] {msg}")
    open(os.path.join(OUT, "_qa12.txt"), "a", encoding="utf-8").write(chr(10).join(_l) + chr(10))
except Exception as _e:
    print("qa err", _e)

fig.savefig(os.path.join(OUT, "fig1_pipeline.png"), dpi=600, facecolor="white")
fig.savefig(os.path.join(OUT, "fig1_pipeline.pdf"), facecolor="white")
plt.close(fig)
print("fig1 done")
