# -*- coding: utf-8 -*-
"""
阶段3：测量三条件方案（跨 9 世界聚合，H1/H2 对照）
指标：M2_recall（覆盖率）、M2_precision（精度）、M4（物理缺失率）、M6（层级规整度）、M7（重叠对数）
真值：SPEC（场景任务书），独立于状态接地层
用法：python 07_measure_plan.py
"""
import os, sys, json, glob, csv
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
SPEC = {
    "living_room": ["fabric sofa", "wooden coffee table", "bookshelf", "floor lamp", "window", "curtain"],
    "basketball_court": ["basketball", "hoop", "bench", "fence", "ground"],
    "beach_sea": ["sand", "sea water", "sand dune", "shell", "sky"],
}
SZ = {"small": 0.05, "medium": 0.11, "large": 0.18}


def match(exp, got_types):
    core = max(exp.lower().split(), key=len)
    return any(core in t or t in exp.lower() for t in got_types)


def overlap_count(objs):
    boxes = []
    for o in objs:
        p = o.get("position_norm")
        if not p or len(p) != 3:
            continue
        s = SZ.get(o.get("size_class") or "medium", 0.11)
        boxes.append(([p[k] - s for k in range(3)], [p[k] + s for k in range(3)]))
    n = 0
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            lo = [max(boxes[i][0][k], boxes[j][0][k]) for k in range(3)]
            hi = [min(boxes[i][1][k], boxes[j][1][k]) for k in range(3)]
            if all(hi[k] > lo[k] for k in range(3)):
                n += 1
    return n


def measure(scene, plan):
    objs = plan.get("objects", [])
    got = [(o.get("type") or "").lower() for o in objs]
    req = SPEC.get(scene, [])
    recall = sum(1 for e in req if match(e, got)) / len(req) if req else 0
    precision = sum(1 for t in got if any(match(e, [t]) for e in req)) / len(got) if got else 0
    missing = sum(1 for o in objs if not (o.get("physics") or {}).get("collision"))
    m4 = missing / len(objs) if objs else 1.0
    kids = set((plan.get("hierarchy") or {}).get("children", []))
    m6 = sum(1 for o in objs if o.get("id") in kids) / len(objs) if objs else 0
    return {"M2_recall": round(recall, 3), "M2_precision": round(precision, 3),
            "M4": round(m4, 3), "M6": round(m6, 3), "M7_overlap": overlap_count(objs),
            "n_objects": len(objs)}


def main():
    rows = []
    by_world = {}
    for wdir in sorted(glob.glob(os.path.join(DATA_ROOT, "*", "world_*"))):
        scene = os.path.basename(os.path.dirname(wdir))
        wid = os.path.basename(wdir)[:15]
        by_world.setdefault(wid, {})
        for cond in ["B2", "B2A1", "B2A2"]:
            fp = os.path.join(wdir, f"plan_{cond}.json")
            if not os.path.exists(fp):
                continue
            plan = json.load(open(fp, encoding="utf-8"))
            m = measure(scene, plan)
            rows.append({"world": wid, "scene": scene, "cond": cond, **m})
            by_world[wid][cond] = m
    out = os.path.join(DATA_ROOT, "measured_plans.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["world", "scene", "cond", "M2_recall", "M2_precision",
                                          "M4", "M6", "M7_overlap", "n_objects"])
        w.writeheader(); w.writerows(rows)

    def agg(cond, key):
        v = [r[key] for r in rows if r["cond"] == cond]
        return (sum(v) / len(v), len(v)) if v else (float("nan"), 0)

    print(f"{'指标':<14}{'B2':>10}{'B2A1':>10}{'B2A2':>10}")
    print("-" * 46)
    for key in ["M2_recall", "M2_precision", "M4", "M6", "M7_overlap", "n_objects"]:
        vals = [agg(c, key)[0] for c in ["B2", "B2A1", "B2A2"]]
        print(f"{key:<14}" + "".join(f"{v:>10.3f}" for v in vals))
    n = agg("B2", "M2_recall")[1]
    print(f"\n(每组 n={n} 个世界)")

    print("\n=== H1 对照（B2 结构化 vs B2A2 仅意图）===")
    for key in ["M2_recall", "M2_precision", "M7_overlap"]:
        b2, _ = agg("B2", key); a2, _ = agg("B2A2", key)
        print(f"  {key}: B2={b2:.3f}  B2-A2={a2:.3f}  差={b2-a2:+.3f}")
    print("\n=== H2 对照（B2 结构化 vs B2A1 等量文本）===")
    for key in ["M2_recall", "M2_precision", "M7_overlap"]:
        b2, _ = agg("B2", key); a1, _ = agg("B2A1", key)
        print(f"  {key}: B2={b2:.3f}  B2-A1={a1:.3f}  差={b2-a1:+.3f}")
    print(f"\n已写出 {out}")


if __name__ == "__main__":
    main()
