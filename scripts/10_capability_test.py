# -*- coding: utf-8 -*-
"""
跨能力水平的 H2/H3 联合检验
方法：同一"布局去重"任务，reasoning_effort 取 low/high/max，
      状态输入分别用 B2(JSON) 与 B2-A1(等量散文)，比较修复效果。
      每个 (effort, cond) 重复 R 次以观察方差。
用法：DEEPSEEK_API_KEY=xxx python 10_capability_test.py
"""
import os, sys, json, re, random, requests, csv
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE = "https://api.deepseek.com/v1"
MODEL = "deepseek-flash"
N_OBJ = 30           # 场景规模
R = 3                # 每格重复次数
EFFORTS = ["low", "high", "max"]
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "capability_results.csv"))

TYPES = ["sofa","table","chair","lamp","shelf","window","rug","plant","tv","cabinet","desk","bed"]
SYS = """You are a scene-layout repair module. You receive a scene state: objects with normalized
positions in [-1,1]^3 and a size class. Many objects OVERLAP. Produce a corrected layout where
NO two objects overlap. Keep every object's type; you may move them.
Output STRICT JSON only: {"objects":[{"id":"..","type":"..","position_norm":[x,y,z],"size_class":".."}]}"""
SZ = {"small": 0.04, "medium": 0.09, "large": 0.15}


def make_scene(n, seed):
    random.seed(seed)
    return [{"id": f"o{i}", "type": TYPES[i % len(TYPES)],
             "position_norm": [round(random.uniform(-0.1, 0.1), 3) for _ in range(3)],
             "size_class": random.choice(["small", "medium", "large"])} for i in range(n)]


def to_prose(objs):
    parts = ["当前场景包含以下物体："]
    for o in objs:
        p = o["position_norm"]
        parts.append(f"{o['type']}（编号 {o['id']}）位于 x={p[0]}、y={p[1]}、z={p[2]} 处，尺寸为{o['size_class']}。")
    parts.append("这些物体当前位置互相重叠，需要重新布置以避免重叠。")
    return "".join(parts)


def call(user, effort):
    r = requests.post(f"{BASE}/chat/completions",
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": [{"role": "system", "content": SYS},
                                           {"role": "user", "content": user}],
              "temperature": 0, "max_tokens": 16000, "reasoning_effort": effort,
              "response_format": {"type": "json_object"}}, timeout=420)
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
    for seed in range(R):
        objs = make_scene(N_OBJ, seed * 100 + 1)
        before = overlaps(objs)
        b2_in = "SCENE STATE (structured):\n" + json.dumps({"objects": objs}, ensure_ascii=False, separators=(",", ":"))
        a1_in = "SCENE STATE:\n" + to_prose(objs)
        for effort in EFFORTS:
            for cond, inp in [("B2", b2_in), ("B2A1", a1_in)]:
                try:
                    out = call(inp + "\n\nOutput the corrected layout as strict JSON.", effort)
                    plan = extract_json(out)
                    after = overlaps(plan.get("objects", []))
                    kept = len(plan.get("objects", []))
                    ok = 1
                except Exception as e:
                    after, kept, ok = -1, -1, 0
                    print(f"  seed{seed} {effort} {cond}: 失败 {str(e)[:60]}")
                rows.append({"seed": seed, "effort": effort, "cond": cond,
                             "before": before, "after": after, "kept": kept, "parse_ok": ok})
                print(f"  seed{seed} effort={effort:4s} {cond:5s}: {before}->{after} (kept {kept})")
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["seed","effort","cond","before","after","kept","parse_ok"])
        w.writeheader(); w.writerows(rows)

    print("\n=== 汇总（各 effort 下 B2 vs B2A1 平均残留重叠）===")
    for effort in EFFORTS:
        b2 = [r["after"] for r in rows if r["effort"]==effort and r["cond"]=="B2" and r["after"]>=0]
        a1 = [r["after"] for r in rows if r["effort"]==effort and r["cond"]=="B2A1" and r["after"]>=0]
        okb2 = sum(r["parse_ok"] for r in rows if r["effort"]==effort and r["cond"]=="B2")
        oka1 = sum(r["parse_ok"] for r in rows if r["effort"]==effort and r["cond"]=="B2A1")
        mb2 = sum(b2)/len(b2) if b2 else float("nan")
        ma1 = sum(a1)/len(a1) if a1 else float("nan")
        print(f"  effort={effort:4s}: B2 avg_overlap={mb2:.2f}(成功{okb2}/{R})  "
              f"B2A1 avg_overlap={ma1:.2f}(成功{oka1}/{R})")
    print(f"\n已写出 {OUT}")


if __name__ == "__main__":
    main()
