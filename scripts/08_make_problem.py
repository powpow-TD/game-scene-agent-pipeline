# -*- coding: utf-8 -*-
"""
阶段3c-1：构造有判别力的任务实例（诊断+修复型）
从接地快照出发，注入两类缺陷：
  (a) 重叠：把部分物体挪到场景中心，制造互相穿插
  (b) 缺件：随机删掉若干物体，要求 Agent 补齐
并生成配套的"生产简报"（必含物体 + 空间约束）。
输出：problem.json（结构化真值）、brief.json、current_B2.json（结构化）、current_B2A1.txt（等量散文）
用法：python 08_make_problem.py
"""
import os, sys, json, glob, random
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
random.seed(42)

# 各场景的必含物体与空间约束（生产简报，独立于接地层）
BRIEF = {
    "living_room": {
        "required": ["sofa", "coffee table", "bookshelf", "floor lamp", "window", "curtain"],
        "constraints": ["沙发必须正对窗户", "茶几必须位于沙发前方", "书架靠墙放置",
                        "落地灯位于沙发一侧"],
    },
    "basketball_court": {
        "required": ["basketball", "hoop", "bench", "fence"],
        "constraints": ["篮球位于球场内地面", "篮筐位于场地端线", "长椅靠边线放置"],
    },
    "beach_sea": {
        "required": ["sand", "sea water", "sand dune", "shell"],
        "constraints": ["海水位于沙滩一侧", "沙丘位于沙滩后方", "贝壳散落在沙滩上"],
    },
}


def make_problem(snap):
    objs = [dict(o) for o in snap.get("objects", []) if o.get("type")]
    if not objs:
        return None
    # (b) 制造缺件：随机删掉最多 40% 但至少保留 1 个
    n = len(objs)
    drop = min(max(1, int(n * 0.4)), n - 1)
    keep = objs[:n - drop] if n - drop > 0 else objs[:1]
    # (a) 制造重叠：把保留物体中约一半挪到中心附近（半径很小 -> 互相穿插）
    victim_idx = random.sample(range(len(keep)), max(1, len(keep) // 2))
    for i, o in enumerate(keep):
        if i in victim_idx:
            o["position_norm"] = [round(random.uniform(-0.1, 0.1), 2) for _ in range(3)]
    return {"objects": keep, "dropped": [o["type"] for o in objs[n - drop:]],
            "overlap_injected": len(victim_idx)}


def to_prose(problem):
    parts = ["当前场景的状态如下。"]
    for o in problem["objects"]:
        p = o.get("position_norm")
        seg = f"场景中已有一个{o['type']}"
        if p:
            seg += f"，位于归一化坐标 x={p[0]}、y={p[1]}、z={p[2]} 处"
        ph = o.get("physics") or {}
        if ph.get("material"):
            seg += f"，材质为{ph['material']}"
        if ph.get("collision"):
            seg += f"，碰撞类型为{ph['collision']}"
        parts.append(seg + "。")
    parts.append("上述物体的位置存在相互重叠的情况，且部分应存在的物体缺失。")
    return "".join(parts)


def main():
    for wdir in sorted(glob.glob(os.path.join(DATA_ROOT, "*", "world_*"))):
        snap_p = os.path.join(wdir, "snapshot.json")
        if not os.path.exists(snap_p):
            continue
        scene = os.path.basename(os.path.dirname(wdir))
        snap = json.load(open(snap_p, encoding="utf-8"))
        problem = make_problem(snap)
        if not problem:
            continue
        brief = BRIEF.get(scene, {"required": [], "constraints": []})
        json.dump(problem, open(os.path.join(wdir, "problem.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        json.dump(brief, open(os.path.join(wdir, "brief.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        # B2 结构化输入（紧凑）
        cur_b2 = {"scene": scene, "current_objects": problem["objects"]}
        open(os.path.join(wdir, "current_B2.json"), "w", encoding="utf-8").write(
            json.dumps(cur_b2, ensure_ascii=False, separators=(",", ":")))
        # B2-A1 等量散文
        open(os.path.join(wdir, "current_B2A1.txt"), "w", encoding="utf-8").write(to_prose(problem))
        print(f"{os.path.basename(wdir)[:26]}: 保留 {len(problem['objects'])} 个物体、"
              f"注入重叠 {problem['overlap_injected']} 个、删除 {problem['dropped']}")


if __name__ == "__main__":
    main()
