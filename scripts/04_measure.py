# -*- coding: utf-8 -*-
"""
阶段4：程序化测量客观指标 + 汇总台账
测量：M2 完整度 / M4 物理缺失率 / M6 层级规整度 / M7 穿插
用法：python 04_measure.py
"""
import os, json, glob, csv

DATA_ROOT = os.path.join(os.path.dirname(__file__), "..", "data")

SPEC = {  # 与 02 中一致，作为独立真值
    "living_room": ["fabric sofa", "wooden coffee table", "bookshelf", "floor lamp", "window", "curtain"],
    "basketball_court": ["basketball", "hoop", "bench", "fence", "ground"],
    "beach_sea": ["sand", "sea water", "sand dune", "shell", "sky"],
}


def measure_one(sdir):
    snap_p = os.path.join(sdir, "input_B2.json")
    if not os.path.exists(snap_p):
        return None
    snap = json.load(open(snap_p, encoding="utf-8"))
    # 场景名从目录结构取（experiment/data/{scene}/world_*），避免依赖模型返回的场景标签
    scene = os.path.basename(os.path.dirname(sdir))
    objs = snap.get("objects", [])

    # M2 资产完整度：目标清单覆盖率（关键词模糊匹配，避免"sofa" vs "fabric sofa"误判）
    expected = SPEC.get(scene, [])
    got_types = [(o.get("type") or "").lower() for o in objs]

    def matched(exp):
        # 任务书条目按空格分词，核心名词命中即视为覆盖
        keys = exp.lower().split()
        # 用最长的词作为核心名词（如 "fabric sofa" -> sofa）
        core = max(keys, key=len)
        return any(core in t or t in exp.lower() for t in got_types)

    hit = sum(1 for e in expected if matched(e))
    m2 = hit / len(expected) if expected else 0

    # M4 物理参数缺失率
    missing = sum(1 for o in objs if not o.get("physics", {}).get("collision"))
    m4 = missing / len(objs) if objs else 1.0

    # M6 层级规整度：所有物体都在 hierarchy.children 中
    children = set(snap.get("hierarchy", {}).get("children", []))
    in_hier = sum(1 for o in objs if o["id"] in children)
    m6 = in_hier / len(objs) if objs else 0

    # M7 穿插（用 bbox，需 03 已填充）
    m7 = 0
    boxes = [(o["id"], o["bbox"]) for o in objs if o.get("bbox")]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b1 = boxes[i]; b, b2 = boxes[j]
            lo = [max(b1[0][k], b2[0][k]) for k in range(3)]
            hi = [min(b1[1][k], b2[1][k]) for k in range(3)]
            if all(hi[k] > lo[k] for k in range(3)):
                m7 += 1

    return {"world": os.path.basename(sdir), "scene": scene,
            "M2": round(m2, 3), "M4": round(m4, 3), "M6": round(m6, 3), "M7": m7}


def main():
    rows = []
    for sdir in sorted(glob.glob(os.path.join(DATA_ROOT, "*", "world_*"))):
        r = measure_one(sdir)
        if r:
            rows.append(r)
            print(r)
    out = os.path.join(DATA_ROOT, "measured.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["world", "scene", "M2", "M4", "M6", "M7"])
        w.writeheader(); w.writerows(rows)
    print(f"\n已写出 {out}")


if __name__ == "__main__":
    main()
