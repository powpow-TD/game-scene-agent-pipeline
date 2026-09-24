# -*- coding: utf-8 -*-
"""
阶段1：生成并冻结资产池（3 场景 × 3 世界）
- 先存 operation_id，支持中断续传
- 跳过已存在的 world（幂等）
- 不下载 SPZ（28MB/个，无指标使用）；只留 caption / GLB / pano / meta
用法：WLT_API_KEY=xxx python 01_freeze_assets.py
"""
import os, sys, time, json, requests
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

API = "https://api.worldlabs.ai"
KEY = os.environ["WLT_API_KEY"]
H = {"WLT-Api-Key": KEY, "Content-Type": "application/json"}
MODEL = "marble-1.1"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

SCENES = {
    "living_room": "a modern living room interior with a fabric sofa, wooden coffee table, bookshelf, floor lamp, and a large window with curtains, warm indoor lighting",
    "basketball_court": "an outdoor basketball court with a basketball on the ground, hoops, benches, chain-link fence, clear sky with some clouds, bright daylight",
    "beach_sea": "a sandy beach meeting the sea, with sand dunes, scattered shells, gentle waves, and strong sunlight, clear sky",
}
REPEATS = 3


def gen(prompt, name):
    r = requests.post(f"{API}/marble/v1/worlds:generate",
                      json={"display_name": name, "model": MODEL,
                            "world_prompt": {"type": "text", "text_prompt": prompt}}, headers=H)
    if r.status_code == 402:
        raise RuntimeError("余额不足")
    r.raise_for_status()
    return r.json()["operation_id"]


def poll(opid, timeout=1800):
    t0 = time.time()
    misses = 0
    while time.time() - t0 < timeout:
        try:
            op = requests.get(f"{API}/marble/v1/operations/{opid}", headers=H, timeout=60).json()
            misses = 0
        except Exception as e:
            misses += 1
            print(f"  [网络重试{misses}] {str(e)[:60]}")
            if misses > 20:
                raise
            time.sleep(15)
            continue
        if op.get("done"):
            if op.get("error"):
                raise RuntimeError(op["error"])
            return op
        time.sleep(10)
    raise TimeoutError(opid)


def dl(u, p, tries=5):
    if not u:
        return
    for t in range(tries):
        try:
            r = requests.get(u, stream=True, timeout=120)
            r.raise_for_status()
            with open(p, "wb") as f:
                for c in r.iter_content(8192):
                    f.write(c)
            return
        except Exception as e:
            print(f"  [下载重试{t+1}] {str(e)[:60]}")
            time.sleep(5)
    raise RuntimeError(f"下载失败: {u}")


def already_done(sdir, k):
    if not os.path.isdir(sdir):
        return False
    return any(d.startswith(f"world_{k}_") for d in os.listdir(sdir))


def main():
    for scene, prompt in SCENES.items():
        sdir = os.path.join(ROOT, scene)
        os.makedirs(sdir, exist_ok=True)
        for k in range(1, REPEATS + 1):
            if already_done(sdir, k):
                print(f"[{scene}#{k}] 已存在，跳过")
                continue
            opfile = os.path.join(sdir, f"op_{k}.json")
            if os.path.exists(opfile):
                opid = json.load(open(opfile, encoding="utf-8"))["operation_id"]
                print(f"[{scene}#{k}] 复用 op_id {opid}")
            else:
                opid = gen(prompt, f"{scene}_{k}")
                json.dump({"operation_id": opid, "scene": scene, "repeat": k,
                           "prompt": prompt, "model": MODEL},
                          open(opfile, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
                print(f"[{scene}#{k}] op_id {opid} 已存盘")
            op = poll(opid)
            wid = op["metadata"]["world_id"]
            w = requests.get(f"{API}/marble/v1/worlds/{wid}", headers=H).json()
            a = w["assets"]
            d = os.path.join(sdir, f"world_{k}_{wid}")
            os.makedirs(d, exist_ok=True)
            open(os.path.join(d, "caption.txt"), "w", encoding="utf-8").write(a.get("caption") or "")
            dl(a["mesh"].get("collider_mesh_url"), os.path.join(d, "collider.glb"))
            dl(a.get("imagery", {}).get("pano_url"), os.path.join(d, "pano.png"))
            json.dump({"world_id": wid, "model": MODEL, "prompt": prompt,
                       "caption": a.get("caption"),
                       "semantics": a.get("splats", {}).get("semantics_metadata"),
                       "cost": op.get("cost")},
                      open(os.path.join(d, "meta.json"), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            print(f"  -> 固化 {d}")


if __name__ == "__main__":
    main()
