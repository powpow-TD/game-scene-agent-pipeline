# -*- coding: utf-8 -*-
"""
双模型最小移动去重测试（H2/H3 联合检验）
任务：消除物体重叠，但要求"尽量少移动"，保持每个物体靠近原位置。
指标：残留重叠数 + 总位移量。
对比：B2(JSON) vs B2-A1(散文) × {deepseek-flash, deepseek-v4-pro}
"""
import os, sys, json, re, random, requests, csv, math, time
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE = "https://api.deepseek.com/v1"
MODELS = ["deepseek-flash"]
N_OBJ = 12
R = 5
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "minmove_results.csv"))

TYPES = ["sofa", "table", "chair", "lamp", "shelf", "window", "rug", "plant", "tv"]
SYS = """You are a scene-layout repair module. You receive a scene state: objects with normalized
positions in [-1,1]^3 and a size class. Several objects currently OVERLAP.

Repair the layout with MINIMAL MOVEMENT: remove all overlaps, but keep every object as close
to its ORIGINAL position as possible. Do NOT re-plan the whole scene; make the smallest position
adjustments that remove the overlaps. Keep every object's id and type unchanged.
Output STRICT JSON only: {"objects":[{"id":"..","type":"..","position_norm":[x,y,z],"size_class":".."}]}"""
SZ = {"small": 0.04, "medium": 0.09, "large": 0.15}


def make_scene(n, seed):
    random.seed(seed)
    objs = []
    for i in range(n):
        if i < n // 2:
            pos = [round(random.uniform(-0.15, 0.15), 3) for _ in range(3)]
        else:
            pos = [round(random.uniform(-0.9, 0.9), 3) for _ in range(3)]
        objs.append({"id": f"o{i}", "type": TYPES[i % len(TYPES)], "position_norm": pos,
                     "size_class": random.choice(["small", "medium", "large"])})
    return objs


def to_prose(objs):
    parts = ["当前场景包含以下物体："]
    for o in objs:
        p = o["position_norm"]
        parts.append(f"{o['type']}（编号 {o['id']}）位于 x={p[0]}、y={p[1]}、z={p[2]} 处，尺寸为{o['size_class']}。")
    parts.append("其中部分物体位置重叠，请在尽量少移动的前提下消除重叠。")
    return "".join(parts)


def call(user, model):
    body = {"model": model,
            "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": user}],
            "temperature": 0, "max_tokens": 32000,
            "response_format": {"type": "json_object"}}
    last = ""
    for attempt in range(4):
        r = requests.post(f"{BASE}/chat/completions",
                          headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
                          json=body, timeout=420)
        if r.status_code == 200:
            c = r.json()["choices"][0]["message"].get("content") or ""
            if c.strip():
                return c
            last = "空响应"
        else:
            last = f"HTTP {r.status_code}"
        time.sleep(3)
    raise RuntimeError(last)


def extract_json(raw):
    start = raw.find("{")
    if start >= 0:
        d = 0
        for i in range(start, len(raw)):
            if raw[i] == "{":
                d += 1
            elif raw[i] == "}":
                d -= 1
                if d == 0:
                    try:
                        return json.loads(raw[start:i + 1])
                    except Exception:
                        break
    m = re.search(r"\{.*\}", raw, re.S)
    return json.loads(m.group(0)) if m else json.loads(raw)


def overlaps(objs):
    boxes = []
    for o in objs:
        p = o.get("position_norm")
        if not p or len(p) != 3:
            continue
        s = SZ.get(o.get("size_class") or "medium", 0.09)
        boxes.append(([p[k] - s for k in range(3)], [p[k] + s for k in range(3)]))
    n = 0
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            lo = [max(boxes[i][0][k], boxes[j][0][k]) for k in range(3)]
            hi = [min(boxes[i][1][k], boxes[j][1][k]) for k in range(3)]
            if all(hi[k] > lo[k] for k in range(3)):
                n += 1
    return n


def total_drift(orig, plan):
    om = {o["id"]: o["position_norm"] for o in orig if o.get("position_norm")}
    drift, cnt = 0.0, 0
    for o in plan.get("objects", []):
        p = o.get("position_norm")
        if o.get("id") in om and p and len(p) == 3:
            o0 = om[o["id"]]
            drift += math.sqrt(sum((p[k] - o0[k]) ** 2 for k in range(3)))
            cnt += 1
    return drift, cnt


def main():
    rows = []
    for seed in range(R):
        objs = make_scene(N_OBJ, seed * 37 + 5)
        before = overlaps(objs)
        b2_in = "SCENE STATE (structured):\n" + json.dumps({"objects": objs}, ensure_ascii=False, separators=(",", ":"))
        a1_in = "SCENE STATE:\n" + to_prose(objs)
        for model in MODELS:
            for cond, inp in [("B2", b2_in), ("B2A1", a1_in)]:
                try:
                    plan = extract_json(call(inp + "\n\nOutput the repaired layout as strict JSON.", model))
                    after = overlaps(plan.get("objects", []))
                    drift, cnt = total_drift(objs, plan)
                    ok = 1
                except Exception as e:
                    after, drift, cnt, ok = -1, -1, -1, 0
                    print(f"  seed{seed} {model} {cond}: 失败 {str(e)[:50]}")
                rows.append({"seed": seed, "model": model, "cond": cond, "before": before,
                             "after": after, "drift": round(drift, 3), "n_matched": cnt, "ok": ok})
                print(f"  seed{seed} {model:17s} {cond:5s}: 重叠 {before}->{after}, 总位移 {drift:.2f}")
                with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
                    w = csv.DictWriter(f, fieldnames=["seed","model","cond","before","after","drift","n_matched","ok"])
                    w.writeheader(); w.writerows(rows)
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["seed", "model", "cond", "before", "after", "drift", "n_matched", "ok"])
        w.writeheader()
        w.writerows(rows)

    print("\n=== 汇总（最小移动任务）===")
    for model in MODELS:
        for cond in ["B2", "B2A1"]:
            rs = [r for r in rows if r["model"] == model and r["cond"] == cond and r["ok"] == 1]
            if rs:
                ma = sum(r["after"] for r in rs) / len(rs)
                md = sum(r["drift"] for r in rs) / len(rs)
                print(f"  {model:17s} {cond:5s}: 残留重叠={ma:.2f}  平均总位移={md:.2f}  (n={len(rs)})")
            else:
                print(f"  {model:17s} {cond:5s}: 无有效结果")
    print(f"\n已写出 {OUT}")


if __name__ == "__main__":
    main()
