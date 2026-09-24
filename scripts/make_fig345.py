# -*- coding: utf-8 -*-
"""图 3–5：数据图（按 scipilot-figure-skill 规范重构）
关键改动：每组 n=9（图5 每格 n=3），远小于 10，
按 viz_pitfalls P1「n<10 → 直接 stripplot / dot plot，不画统计柱」，
改为「全点散点 + 均值线 + 标准差须」，替代原均值柱+误差棒。
配色沿用 Okabe-Ito（与图1/图2 一致）；字体 SimHei + DejaVu Sans；dpi=600。
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, csv, os, statistics as st

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["svg.fonttype"] = "none"

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(OUT, "..", ".."))
CSV = os.path.join(ROOT, "experiment", "data", "measured_plans.csv")

OI = {"orange": "#E69F00", "skyblue": "#56B4E9", "green": "#009E73",
      "yellow": "#F0E442", "blue": "#0072B2", "vermillion": "#D55E00",
      "purple": "#CC79A7", "grey": "#999999"}

CONDS = ["B2", "B2A1", "B2A2"]
LABELS = ["G1\n结构化快照", "G2\n等量文本", "G3\n仅意图"]
COLORS = [OI["blue"], OI["orange"], OI["green"]]

rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig")))


def vals(cond, key):
    return [float(r[key]) for r in rows if r["cond"] == cond]


def vals_scene(scene, cond, key):
    return [float(r[key]) for r in rows if r["scene"] == scene and r["cond"] == cond]


def cohen_d(a, b):
    ma, mb = st.mean(a), st.mean(b)
    s = ((st.pstdev(a) ** 2 + st.pstdev(b) ** 2) / 2) ** 0.5
    return (ma - mb) / s if s > 0 else 0.0


def dot_strip(ax, groups, labels, colors, jitter=0.13, seed=42):
    """画 stripplot + 均值线 + 标准差须（P1 合规做法）"""
    rs = np.random.RandomState(seed)
    for i, (v, c) in enumerate(zip(groups, colors)):
        x = i + rs.uniform(-jitter, jitter, len(v))
        ax.scatter(x, v, s=26, color=c, alpha=0.85, edgecolor="black",
                   linewidth=0.45, zorder=3)
        m, sd = st.mean(v), st.pstdev(v)
        ax.plot([i - 0.26, i + 0.26], [m, m], color="black", lw=2.0, zorder=5)
        ax.errorbar(i, m, yerr=sd, fmt="none", ecolor="black",
                    elinewidth=1.1, capsize=4, capthick=1.1, zorder=4)
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels(labels, fontsize=8.5)



# ===== scipilot-figure-skill 视觉自检闭环 =====
import sys as _sys
_sys.path.insert(0, r"D:/openscience/openscience/data-root/user-skills/scipilot-figure-skill/scripts")
try:
    from visual_qa import audit_layout as _audit, print_report as _pr
    _HAS_QA = True
except Exception as _e:
    print("visual_qa unavailable:", _e)
    _HAS_QA = False

_QA_LOG = []
def _qa(fig, tag):
    if not _HAS_QA: return
    issues = _audit(fig)
    bad = [i for i in issues if i[0] in ("WARN", "FAIL")]
    _QA_LOG.append(f"--- QA[{tag}]: {len(bad)} issue(s) ---")
    for sev, msg in bad:
        _QA_LOG.append(f"    [{sev}] {msg}")

def _gray(fig, name):
    """灰度预览：检查色盲可区分性"""
    from PIL import Image
    import matplotlib.pyplot as _plt
    _tmp = os.path.join(OUT, "_tmp.png")
    fig.savefig(_tmp, dpi=120, facecolor="white")
    im = Image.open(_tmp).convert("L")
    im.save(os.path.join(OUT, f"_gray_{name}.png"))
    os.remove(_tmp)

# ============================================================ 图 3 主要结果
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.5), constrained_layout=True)

for ax, key, ylab in [(axes[0], "M2_recall", "目标物体覆盖率"),
                      (axes[1], "M2_precision", "目标物体精度")]:
    groups = [vals(c, key) for c in CONDS]
    dot_strip(ax, groups, LABELS, COLORS)
    ax.set_ylabel(ylab, fontsize=10)
    ax.set_ylim(0, 1.18)
    ax.grid(axis="y", ls=":", alpha=0.45, zorder=0)
    ax.set_axisbelow(True)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    d = cohen_d(groups[0], groups[2])
    ax.set_title(f"G1 vs G3：Cohen's d = {d:+.2f}", fontsize=9,
                 color=OI["vermillion"], pad=6)

# 共享图例（均值线 / 标准差须 说明）
from matplotlib.lines import Line2D
handles = [
    Line2D([], [], color="black", lw=2.0, label="均值"),
    Line2D([], [], color="black", lw=1.1, marker="|", markersize=8, label="±1 SD"),
    Line2D([], [], color="grey", marker="o", linestyle="none", markersize=5,
           markeredgecolor="black", label="单个冻结世界（n=9/组）"),
]
# 共享图例置于两幅面板下方（横排），避免遮挡数据点
fig.legend(handles=handles, fontsize=7.5, frameon=False, ncol=3,
           loc="lower center", bbox_to_anchor=(0.5, -0.045),
           handletextpad=0.6, columnspacing=1.6)

_qa(fig, "fig3"); _gray(fig, "fig3")
fig.savefig(os.path.join(OUT, "fig3_results.png"), dpi=600, facecolor="white")
fig.savefig(os.path.join(OUT, "fig3_results.pdf"), facecolor="white")
plt.close(fig)
print("fig3 done（stripplot）")

# ============================================================ 图 4 效应量
fig, ax = plt.subplots(figsize=(5.0, 2.5), constrained_layout=True)
mets = ["目标物体精度", "目标物体覆盖率"]
ds = [cohen_d(vals("B2", "M2_precision"), vals("B2A2", "M2_precision")),
      cohen_d(vals("B2", "M2_recall"), vals("B2A2", "M2_recall"))]
y = np.arange(len(mets))
for i, (d, c) in enumerate(zip(ds, [OI["skyblue"], OI["blue"]])):
    ax.plot([0, d], [i, i], color=c, lw=3, solid_capstyle="butt", zorder=5)
    ax.scatter([d], [i], s=110, color=c, edgecolor="black", linewidth=0.8, zorder=6)
    ax.text(d + 0.06, i, f"{d:+.2f}", va="center", fontsize=10, fontweight="bold", fontfamily="Microsoft YaHei")
for v, lab in [(0.2, "小"), (0.5, "中"), (0.8, "大")]:
    ax.axvline(v, color=OI["grey"], ls=":", lw=0.9, zorder=1)
    ax.text(v, len(mets) - 0.32, lab, fontsize=7, color=OI["grey"], ha="center")
ax.axvline(0, color="black", lw=1.0)
ax.set_yticks(y); ax.set_yticklabels(mets, fontsize=9.5)
ax.set_xlabel("Cohen's d（G1 vs G3）", fontsize=9.5)
ax.set_xlim(0, 2.0); ax.set_ylim(-0.6, len(mets) - 0.15)
ax.grid(axis="x", ls=":", alpha=0.4, zorder=0); ax.set_axisbelow(True)
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
_qa(fig, "fig4_effsize"); _gray(fig, "fig4_effsize")
fig.savefig(os.path.join(OUT, "fig5_effectsize.png"), dpi=600, facecolor="white")
fig.savefig(os.path.join(OUT, "fig5_effectsize.pdf"), facecolor="white")
plt.close(fig)
print("fig4 done（lollipop）")

# ============================================================ 图 5 任务依赖性
fig, ax = plt.subplots(figsize=(5.2, 3.4), constrained_layout=True)
scenes = ["living_room", "basketball_court", "beach_sea"]
snames = ["室内客厅", "户外篮球场", "沙滩与大海"]
rs = np.random.RandomState(7)
for si, sc in enumerate(scenes):
    for ci, (cond, c) in enumerate([("B2", OI["blue"]), ("B2A2", OI["green"])]):
        v = vals_scene(sc, cond, "M2_recall")
        off = -0.16 if ci == 0 else 0.16
        x = si + off + rs.uniform(-0.045, 0.045, len(v))
        ax.scatter(x, v, s=32, color=c, alpha=0.9, edgecolor="black",
                   linewidth=0.5, zorder=3)
        m = st.mean(v)
        ax.plot([si + off - 0.10, si + off + 0.10], [m, m], color="black", lw=1.8, zorder=4)
    d = st.mean(vals_scene(sc, "B2", "M2_recall")) - st.mean(vals_scene(sc, "B2A2", "M2_recall"))
    ax.text(si, 1.16, f"Δ={d:+.2f}", ha="center", fontsize=8.5,
            color=OI["vermillion"], fontweight="bold", fontfamily="Microsoft YaHei")
ax.set_xticks(range(3)); ax.set_xticklabels(snames, fontsize=9.5)
ax.set_ylabel("目标物体覆盖率", fontsize=10); ax.set_ylim(0, 1.30)
ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])   # 显式刻度，避免自动生成越界刻度(1.4)溢出画布
ax.grid(axis="y", ls=":", alpha=0.45, zorder=0); ax.set_axisbelow(True)
for s in ["top", "right"]:
    ax.spines[s].set_visible(False)
h = [Line2D([], [], marker="o", linestyle="none", color=OI["blue"],
            markeredgecolor="black", markersize=7, label="G1 结构化快照"),
     Line2D([], [], marker="o", linestyle="none", color=OI["green"],
            markeredgecolor="black", markersize=7, label="G3 仅意图")]
ax.legend(handles=h, fontsize=8, frameon=False, loc="lower right")
_qa(fig, "fig5_taskdep"); _gray(fig, "fig5_taskdep")
fig.savefig(os.path.join(OUT, "fig4_taskdep.png"), dpi=600, facecolor="white")
fig.savefig(os.path.join(OUT, "fig4_taskdep.pdf"), facecolor="white")
plt.close(fig)
print("fig5 done（stripplot, n=3/格）")


# 输出 QA 报告到文件（规避控制台编码）
_rp = os.path.join(OUT, "_qa_report.txt")
open(_rp, "w", encoding="utf-8").write(chr(10).join(_QA_LOG) if _QA_LOG else "(no issues)")
print("QA report written")