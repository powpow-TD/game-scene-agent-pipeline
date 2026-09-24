# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os
plt.rcParams["font.sans-serif"] = ["SimHei","Microsoft YaHei","DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["pdf.fonttype"] = 42
OUT = os.path.dirname(os.path.abspath(__file__))
OI = {"orange":"#E69F00","skyblue":"#56B4E9","green":"#009E73","yellow":"#F0E442",
      "blue":"#0072B2","vermillion":"#D55E00","purple":"#CC79A7","grey":"#999999"}

def box(ax,x,y,w,h,text,fc,ec="black",fs=8.5,bold=False,tc="black",ls="-",linespacing=1.4):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.005,rounding_size=0.015",
        fc=fc,ec=ec,lw=1.1,ls=ls,zorder=2))
    ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=fs,
            fontweight="bold" if bold else "normal",
            fontfamily="Microsoft YaHei" if bold else None,
            color=tc,zorder=3,linespacing=linespacing)
def arrow(ax,p1,p2,color="black",lw=1.3,ls="-",rad=0.0,z=1):
    ax.add_patch(FancyArrowPatch(p1,p2,arrowstyle="-|>",mutation_scale=11,lw=lw,color=color,
        linestyle=ls,zorder=z,connectionstyle=f"arc3,rad={rad}",shrinkA=1,shrinkB=1))

fig, ax = plt.subplots(figsize=(7.4,3.9)); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis("off")
ax.text(0.5,0.965,"状态接地层的输入、融合与输出",ha="center",fontsize=10.5,fontweight="bold",fontfamily="Microsoft YaHei")

# 三个输入流
box(ax,0.02,0.70,0.24,0.17,"① 语义文本流\n模型 caption\n（场景语义先验）",OI["skyblue"],fs=8.2,bold=True)
box(ax,0.02,0.42,0.24,0.17,"② 视觉流\n360° 全景图\n（实例布局主要来源）",OI["orange"],fs=8.2,bold=True)
box(ax,0.02,0.14,0.24,0.17,"③ 几何流\n合并网格 / 高斯点云\n（空间占用与尺度）",OI["purple"],fs=8.2,bold=True,tc="white")

# 融合
box(ax,0.38,0.30,0.24,0.40,"多模态融合\n\n·视觉+语义→物体类别\n 与相对布局\n·几何占用→空间\n 范围校验（坐标钳制）\n·三流相互校验",
    OI["green"],fs=8.2,bold=True,tc="white")
arrow(ax,(0.26,0.785),(0.38,0.63),color=OI["skyblue"],lw=1.5,rad=-0.12)
arrow(ax,(0.26,0.505),(0.38,0.52),color=OI["orange"],lw=1.5)
arrow(ax,(0.26,0.225),(0.38,0.40),color=OI["purple"],lw=1.5,rad=0.12)

# 输出快照
box(ax,0.70,0.205,0.28,0.575,
    "结构化全局状态快照\n\n{\n  scene: …\n  objects[]\n    {id, type,\n     position_norm,\n     physics}\n  relations[]\n  hierarchy\n  lighting\n  physics_missing[]\n}",
    "#FFFFFF",fs=7.4,ec="black",linespacing=1.22)
arrow(ax,(0.62,0.50),(0.70,0.50),color=OI["green"],lw=1.8)
ax.text(0.66,0.535,"融合",fontsize=7.5,color=OI["green"],ha="center")
# 回写（虚线走快照框正下方空白区，文字横排置于箭头下方，避免与箭头/快照框重叠）
arrow(ax,(0.84,0.205),(0.84,0.115),color=OI["green"],lw=1.3,ls="--")
ax.text(0.84,0.055,"UE5 场景图回读更新",fontsize=7.2,color=OI["green"],ha="center",va="center")

plt.subplots_adjust(left=0.01,right=0.99,top=0.93,bottom=0.03)

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

fig.savefig(os.path.join(OUT,"fig2_grounding.png"),dpi=600,facecolor="white")
fig.savefig(os.path.join(OUT,"fig2_grounding.pdf"),facecolor="white")
plt.close(fig)
print("fig2 done")
