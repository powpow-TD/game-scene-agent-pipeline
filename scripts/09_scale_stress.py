# -*- coding: utf-8 -*-
"""
规模压力测试：检验"结构化状态优势是否随场景规模显现"
方法：合成 N 个物体的场景（含重叠），分别以 JSON 与等量散文给出，
      要求 Agent 消除重叠；测量残留重叠对数。N = 5 / 15 / 30 / 50。
用法：DEEPSEEK_API_KEY=xxx python 09_scale_stress.py   [输出 scale_results.csv]
"""
import os, sys, json, re, random, requests
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-flash")
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "scale_results.csv"))
random.seed(7)

TYPES = ["sofa", "table", "chair", "lamp", "shelf", "window", "rug", "plant", "tv", "cabinet"]
MATS = ["fabric", "wood", "metal", "glass", "stone"]

SYS = """You are a scene-layout repair module. You receive a scene state: a list of objects
with normalized positions in [-1,1]^3 and a size class. Many objects currently OVERLAP.
Produce a corrected layout where NO two objects overlap.
Keep every object's type; you may move them. Spread them out on a grid-like arrangement.
Output STRICT JSON only: {"objects":[{"id":"..","type":"..","position_norm":[x,y,z],"size_class":".."}]}"""


def make_scene(n):
    objs = []
    for i in range(n):
        objs.append({"id": f"o{i}", "type": TYPES[i % len(TYPES)],
                     "position_norm": [round(random.uniform(-0.1, 0.1), 3) for _ in range(3)],
                     "size_class": random.choice(["small", "medium", "large"])})
    return objs


def to_prose(objs):
    parts = ["当前场景包含以下物体："]
    for o in objs:
        p = o["position_norm"]
        parts.append(f"{o['type']}（编号 {o['id']}）位于 x={p[0]}、y={p[1]}、z={p[2]} 处，尺寸为{o['size_class']}。")
    parts.append("这些物体当前位置互相重叠，需要重新布置以避免重叠。")
    return "".join(parts)


def call(user):
    r = requests.post(f"{BASE}/chat/completions",
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": [{"role": "system", "content": SYS},
                                           {"role": "user", "content": user}],
              "temperature": 0, "max_tokens": 16000, "response_format": {"type": "json_object"}},
        timeout=300)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def extract_json(raw):
    start = raw.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(raw)):
            if raw[i] == "{": depth += 1
            elif raw[i] == "}":
                depth -= 1
                if depth == 0:
                    try: return json.loads(raw[start:i+1])
                    except Exception: break
    m = re.search(r"\{.*\}", raw, re.S)
    return json.loads(m.group(0)) if m else json.loads(raw)


SZ = {"small": 0.04, "medium": 0.09, "large": 0.15}


def overlaps(objs):
    boxes = []
    for o in objs:
        p = o.get("position_norm")
        if not p or len(p) != 3: continue
        s = SZ.get(o.get("size_class") or "medium", 0.09)
        boxes.append(([p[k]-s for k in range(3)], [p[k]+s for k in range(3)]))
    n = 0
    for i in range(len(boxes)):
        for j in range(i+1, len(boxes)):
            lo = [max(boxes[i][0][k], boxes[j][0][k]) for k in range(3)]
            hi = [min(boxes[i][1][k], boxes[j][1][k]) for k in range(3)]
            if all(hi[k] > lo[k] for k in range(3)): n += 1
    return n


def main():
    rows = []
    for n in [5, 15, 30, 50]:
        objs = make_scene(n)
        before = overlaps(objs)
        # B2: JSON
        b2_in = "SCENE STATE (structured):\n" + json.dumps({"objects": objs}, ensure_ascii=False, separators=(",", ":"))
        # B2A1: prose
        a1_in = "SCENE STATE:\n" + to_prose(objs)
        for cond, inp in [("B2", b2_in), ("B2A1", a1_in)]:
            try:
                plan = extract_json(call(inp + "\n\nOutput the corrected layout as strict JSON."))
                after = overlaps(plan.get("objects", []))
                kept = len(plan.get("objects", []))
            except Exception as e:
                after, kept = -1, -1
                print(f"  N={n} {cond} 失败: {e}")
            rows.append({"N": n, "cond": cond, "before": before, "after": after,
                         "objects_kept": kept})
            print(f"  N={n:2d} {cond:5s}: 修复前重叠 {before:3d} -> 修复后 {after:3d} (保留 {kept} 物体)")
    import csv
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["N", "cond", "before", "after", "objects_kept"])
        w.writeheader(); w.writerows(rows)
    print(f"\n已写出 {OUT}")


if __name__ == "__main__":
    main()
