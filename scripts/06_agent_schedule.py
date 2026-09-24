# -*- coding: utf-8 -*-
"""
阶段2：Agent 调度（转录型任务，用于 H1/H2 对照）
任务：给定场景的三臂状态输入之一，产出"场景构建方案"。
  B2   -> input_B2.json  （结构化状态快照）
  B2A1 -> input_B2A1.txt （等量自然语言描述）
  B2A2 -> input_B2A2.txt （仅高层意图，无状态）
测量（07）以独立的场景任务书为真值。
用法：DEEPSEEK_API_KEY=xxx python 06_agent_schedule.py
"""
import os, sys, json, glob, re, requests, time
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-flash")

AGENT_SYS = """You are a scene-construction scheduler in a game-scene production pipeline.
Given an environment-state input (which may be structured, a natural-language description, or
absent), produce a SCENE CONSTRUCTION PLAN: the objects to create in the scene, each with type,
normalized position in [-1,1]^3 (x right, y up, z forward), size class, material and collision type,
plus the spatial relations and the scene hierarchy.

RULES:
1. When an environment state is provided, ground your plan in it as faithfully as possible.
2. When no state is provided, plan a reasonable scene from the intent alone.
3. Every object must have a physics specification (collision type and material).
4. Output STRICT JSON only:
{
  "scene": "<label>",
  "objects": [
    {"id":"<snake_case>","type":"<name>","position_norm":[x,y,z],"size_class":"small|medium|large",
     "physics":{"collision":"box|mesh|none","material":"<material>","rigid":true|false}}
  ],
  "relations": [{"subject":"<id>","object":"<id>","relation":"<on|under|next_to|facing|inside|above|below>"}],
  "hierarchy": {"root":"<scene>","children":["<id>",...]}
}"""

CONDITIONS = {
    "B2": "input_B2.json",
    "B2A1": "input_B2A1.txt",
    "B2A2": "input_B2A2.txt",
}


def call(user):
    body = {"model": MODEL,
            "messages": [{"role": "system", "content": AGENT_SYS},
                         {"role": "user", "content": user}],
            "temperature": 0, "max_tokens": 32000,
            "response_format": {"type": "json_object"}}
    last = ""
    for attempt in range(4):
        try:
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
        except Exception as e:
            last = str(e)[:60]
        time.sleep(4)
    raise RuntimeError(last)


def extract_json(raw):
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
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


def main():
    targets = sorted(glob.glob(os.path.join(DATA_ROOT, "*", "world_*")))
    if not targets:
        print("未找到 world_*")
        return
    for wdir in targets:
        # 幂等：已有方案则跳过
        for cond, fname in CONDITIONS.items():
            out = os.path.join(wdir, f"plan_{cond}.json")
            if os.path.exists(out):
                print(f"  {os.path.basename(wdir)[:26]}/{cond}: 已存在，跳过")
                continue
            fp = os.path.join(wdir, fname)
            if not os.path.exists(fp):
                print(f"  跳过 {cond}: 缺 {fname}")
                continue
            raw_in = open(fp, encoding="utf-8").read()
            label = "ENVIRONMENT STATE" if cond != "B2A2" else "INTENT"
            user = (f"{label}:\n{raw_in}\n\nProduce the scene construction plan as strict JSON.")
            plan = None
            for attempt in range(2):
                try:
                    plan = extract_json(call(user))
                    break
                except Exception as e:
                    if attempt == 1:
                        print(f"  {cond} 解析失败: {str(e)[:60]}")
            if plan is None:
                continue
            json.dump(plan, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"  {os.path.basename(wdir)[:26]}/{cond}: 方案 {len(plan.get('objects', []))} 物体")
    print("Agent 调度完成。")


if __name__ == "__main__":
    main()
