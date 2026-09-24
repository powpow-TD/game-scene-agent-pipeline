# -*- coding: utf-8 -*-
"""
阶段3（核心）：状态接地层 —— 多模态接地（caption + pano + 几何占用 -> 结构化快照）

【设计要点：防空转/防循环】
  提取采用"开放词表"：不把任务书的目标物体清单喂给模型。
  原因：M2 指标 = 场景物体对任务书清单的覆盖率；
        若把清单喂给模型，模型会照着清单输出，覆盖率恒为 1，指标失效（循环论证）。
  因此：接地层自由识别场景里有什么；覆盖率在测量阶段（04）用独立清单计算。

【三后端】
  GROUNDING_BACKEND=openai   -> OpenAI 兼容的多模态 API（可用各类兼容服务）
  GROUNDING_BACKEND=codex    -> 本地 Codex CLI（GPT-6 Astra）适配（需填命令模板）
  GROUNDING_BACKEND=offline  -> 纯 caption 关键词规则（仅用于流程自测，非真实结果）

依赖：pip install requests
"""
import os, sys, json, base64, re, glob, subprocess
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

BACKEND = os.environ.get("GROUNDING_BACKEND", "offline")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-flash")
OPENAI_BASE = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
VISION_MODEL = os.environ.get("VISION_MODEL", "gpt-4o")
# 本地 Codex CLI 命令模板：{prompt_file} 会被替换为提示词文件路径
CODEX_CMD = os.environ.get("CODEX_CMD", "")


# ----------------------------------------------------------------------
# 1. 系统提示词（约束输出为严格 JSON）
# ----------------------------------------------------------------------
SYSTEM_PROMPT = """You are a scene-state grounding module for a 3D game-scene production pipeline.
You receive: (a) a natural-language scene caption, (b) a 360 equirectangular panorama image,
and (c) a summary of the scene's geometric occupancy (bounding box and voxel statistics).

Your task: reconstruct a STRUCTURED SCENE STATE describing what objects the scene contains.

CRITICAL RULES:
1. Use OPEN VOCABULARY. Identify objects freely from the image and caption. Do NOT expect a predefined list.
2. Only report objects you can actually justify from the caption or the image. If uncertain, set confidence < 0.5.
3. Estimate each object's 3D position as normalized coordinates in [-1,1]^3 relative to the scene
   bounding box (x right, y up, z forward). Use the occupancy summary to sanity-check scale.
4. Report spatial relations only when supported by the caption or clearly visible in the image.
5. Output STRICT JSON only, no prose, matching this schema:

{
  "scene_type": "<short scene label>",
  "objects": [
    {"id": "<snake_case_id>", "type": "<open-vocabulary object name>",
     "position_norm": [x, y, z], "size_class": "small|medium|large",
     "material": "<fabric|wood|metal|stone|water|sand|glass|other|null>",
     "physics_hint": {"collision": "box|mesh|none|null", "rigid": true|false|null},
     "confidence": 0.0-1.0, "evidence": "caption|image|both"}
  ],
  "relations": [
    {"subject": "<id>", "object": "<id>", "relation": "<on|under|next_to|facing|inside|above|below>"}
  ],
  "hierarchy": {"root": "<scene_type>", "children": ["<id>", ...]},
  "lighting": {"condition": "<indoor|overcast|sunny|harsh|null>", "notes": "<short>"},
  "uncertain": ["<id or aspect the model is unsure about>"]
}
"""


def build_user_text(caption, occupancy):
    return (
        "SCENE CAPTION:\n" + (caption or "(none)") + "\n\n"
        "GEOMETRIC OCCUPANCY SUMMARY:\n" + json.dumps(occupancy, ensure_ascii=False, indent=2) + "\n\n"
        "Reconstruct the structured scene state as strict JSON."
    )


# ----------------------------------------------------------------------
# 2. 模型适配器
# ----------------------------------------------------------------------
def call_openai_compatible(user_text, pano_path):
    """OpenAI 兼容的多模态调用（vision）"""
    import requests
    content = [{"type": "text", "text": user_text}]
    if pano_path and os.path.exists(pano_path):
        b64 = base64.b64encode(open(pano_path, "rb").read()).decode()
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"}})
    payload = {
        "model": VISION_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    r = requests.post(f"{OPENAI_BASE}/chat/completions",
                      headers={"Authorization": f"Bearer {OPENAI_KEY}",
                               "Content-Type": "application/json"},
                      json=payload, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def call_deepseek(user_text, pano_path):
    """DeepSeek 视觉调用（OpenAI 兼容，deepseek-flash 支持图像输入）"""
    import requests
    content = [{"type": "text", "text": user_text}]
    if pano_path and os.path.exists(pano_path):
        b64 = base64.b64encode(open(pano_path, "rb").read()).decode()
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"}})
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        "temperature": 0,
        "max_tokens": 32000,
        "response_format": {"type": "json_object"},
    }
    r = requests.post(f"{DEEPSEEK_BASE}/chat/completions",
                      headers={"Authorization": f"Bearer {DEEPSEEK_KEY}",
                               "Content-Type": "application/json"},
                      json=payload, timeout=300)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def call_codex_cli(user_text, pano_path):
    """
    本地 Codex CLI（GPT-6 Astra）适配。
    因 Codex CLI 无标准 HTTP 接口，这里用子进程调用；
    请在 CODEX_CMD 中给出命令模板，用 {prompt_file} 占位提示词文件路径。
    例：CODEX_CMD='codex exec --file {prompt_file}'
    注意：若该 CLI 不支持图像输入，则仅传文本（caption+几何），
          此时"视觉流"退化为文本流，须在论文中如实说明。
    """
    if not CODEX_CMD:
        raise RuntimeError("未设置 CODEX_CMD；请填写本地 CLI 调用模板，或改用 openai/offline 后端。")
    prompt_file = os.path.join(DATA_ROOT, "_prompt_tmp.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(SYSTEM_PROMPT + "\n\n" + user_text)
    cmd = CODEX_CMD.format(prompt_file=prompt_file)
    out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
    if out.returncode != 0:
        raise RuntimeError(f"Codex CLI 失败: {out.stderr[:300]}")
    return out.stdout


def call_offline(caption, occupancy):
    """
    离线回退：仅用 caption 做关键词规则抽取。
    【重要】仅用于跑通管线与自测，其结果不得作为论文实验数据。
    """
    text = (caption or "").lower()
    # 常见物体词表（可扩展）
    LEX = {
        "fabric sofa": ["sofa", "couch"], "wooden coffee table": ["coffee table", "table"],
        "bookshelf": ["bookshelf", "shelf"], "floor lamp": ["lamp"],
        "window": ["window"], "curtain": ["curtain", "drape"],
        "basketball": ["basketball"], "hoop": ["hoop", "basket"],
        "bench": ["bench"], "fence": ["fence"], "ground": ["ground", "pavement", "floor"],
        "sand": ["sand"], "sea water": ["sea", "water", "wave", "ocean"],
        "sand dune": ["dune"], "shell": ["shell"], "sky": ["sky", "cloud"],
    }
    objs = []
    for canon, keys in LEX.items():
        if any(k in text for k in keys):
            objs.append({"id": canon.replace(" ", "_"), "type": canon,
                         "position_norm": None, "size_class": "medium",
                         "material": None, "physics_hint": {"collision": None, "rigid": None},
                         "confidence": 0.5, "evidence": "caption"})
    return json.dumps({
        "scene_type": "unknown", "objects": objs, "relations": [],
        "hierarchy": {"root": "unknown", "children": [o["id"] for o in objs]},
        "lighting": {"condition": None, "notes": "offline fallback"},
        "uncertain": ["offline mode: positions not estimated"],
    }, ensure_ascii=False)


# ----------------------------------------------------------------------
# 3. 解析、校验、落地
# ----------------------------------------------------------------------
def extract_json(raw):
    """从模型输出中稳健提取 JSON（容忍 ```json 包裹与前后文）"""
    if not raw:
        raise ValueError("空响应")
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.S)
    if m:
        return json.loads(m.group(1))
    m = re.search(r"(\{.*\})", raw, re.S)
    if m:
        return json.loads(m.group(1))
    return json.loads(raw)


def build_b2a1_text(snap):
    """
    把 B2 结构化快照改写成 B2-A1 等量非结构化散文。
    信息必须与 B2 完全对应：场景、每个物体的类型/位置/尺寸/材质/碰撞/刚体、
    关系、层级归属、光照、以及不确定项。只改变"组织形式"（散文 vs JSON）。
    """
    parts = []
    parts.append(f"这段描述的是一个{snap.get('scene') or '场景'}。")
    for o in snap.get("objects", []):
        seg = f"场景中有一个{o.get('type')}"
        if o.get("size_class"):
            seg += f"，它属于{o['size_class']}型物体"
        if o.get("position_norm"):
            pos = o["position_norm"]
            seg += f"，其大致位置在一化坐标 x={pos[0]}、y={pos[1]}、z={pos[2]} 处"
        if o.get("physics"):
            ph = o["physics"]
            if ph.get("material"):
                seg += f"，材质是{ph['material']}"
            if ph.get("collision"):
                seg += f"，碰撞类型为{ph['collision']}"
            if ph.get("rigid") is not None:
                seg += f"，刚体属性为{'是' if ph['rigid'] else '否'}"
        if o.get("confidence") is not None:
            seg += f"，该判断的置信度为{o['confidence']}"
        if o.get("evidence"):
            seg += f"，依据来源为{o['evidence']}"
        parts.append(seg + "。")
    for r in snap.get("relations", []):
        parts.append(f"此外，{r.get('subject')} 与 {r.get('object')} 之间存在{r.get('relation')}的空间关系。")
    hier = snap.get("hierarchy") or {}
    if hier.get("children"):
        parts.append(f"上述所有物体都归属于同一层级结构下，根节点为{hier.get('root')}，"
                     f"包含子项{hier.get('children')}。")
    light = snap.get("lighting") or {}
    if light.get("condition") or light.get("notes"):
        parts.append(f"场景的光照条件为{light.get('condition')}，备注：{light.get('notes')}。")
    if snap.get("physics_missing"):
        parts.append(f"其中以下物体缺少物理碰撞参数：{snap['physics_missing']}。")
    if snap.get("uncertain"):
        parts.append(f"需要说明的不确定之处包括：{snap['uncertain']}。")
    return "".join(parts)


def to_snapshot(parsed, caption, occupancy):
    """把模型输出规范化为论文定义的快照结构"""
    objs = []
    clamped_count = [0]
    bmin = occupancy.get("bounds_min"); bmax = occupancy.get("bounds_max")
    for o in parsed.get("objects", []):
        p = o.get("position_norm")
        pos = None
        if p and bmin and bmax:
            # 钳制到约定的 [-1,1] 归一化范围，并记录钳制（接地层保真度指标）
            p_clamped = [max(-1.0, min(1.0, v)) for v in p]
            if any(abs(a - b) > 1e-9 for a, b in zip(p, p_clamped)):
                clamped_count[0] += 1
            p = p_clamped
            pos = [(bmin[k] + bmax[k]) / 2 + p[k] * (bmax[k] - bmin[k]) / 2 for k in range(3)]
        objs.append({
            "id": o.get("id") or o.get("type", "obj").replace(" ", "_"),
            "type": o.get("type"),
            "position": pos,
            "position_norm": p,
            "size_class": o.get("size_class"),
            "physics": {"collision": (o.get("physics_hint") or {}).get("collision"),
                        "material": o.get("material"),
                        "rigid": (o.get("physics_hint") or {}).get("rigid")},
            "confidence": o.get("confidence"),
            "evidence": o.get("evidence"),
        })
    return {
        "scene": parsed.get("scene_type"),
        "objects": objs,
        "relations": parsed.get("relations", []),
        "hierarchy": parsed.get("hierarchy", {}),
        "lighting": parsed.get("lighting", {}),
        "physics_missing": [o["id"] for o in objs if not o["physics"]["collision"]],
        "uncertain": parsed.get("uncertain", []),
        "provenance": {"backend": BACKEND,
                       "model": (VISION_MODEL if BACKEND == "openai"
                                 else DEEPSEEK_MODEL if BACKEND == "deepseek" else BACKEND),
                       "clamped_positions": clamped_count[0],
                       "source_caption": bool(caption), "source_pano": os.path.exists(
                           os.path.join(os.path.dirname(DATA_ROOT), "data"))},
    }


def validate(snap, occupancy):
    """基础校验：坐标落在包围盒内、id 唯一、relations 引用有效 id"""
    warns = []
    ids = [o["id"] for o in snap["objects"]]
    if len(ids) != len(set(ids)):
        warns.append("存在重复 object id")
    bmin, bmax = occupancy.get("bounds_min"), occupancy.get("bounds_max")
    for o in snap["objects"]:
        if o["position"] and bmin and bmax:
            for k in range(3):
                if not (bmin[k] - 1e-6 <= o["position"][k] <= bmax[k] + 1e-6):
                    warns.append(f"{o['id']} 坐标越界")
                    break
    idset = set(ids)
    for r in snap["relations"]:
        if r.get("subject") not in idset or r.get("object") not in idset:
            warns.append(f"关系引用未知 id: {r}")
    return warns


def prepare_pano(wdir):
    """把大 pano 压缩到可上传尺寸，返回小图路径（缓存）"""
    src = os.path.join(wdir, "pano.png")
    if not os.path.exists(src):
        return None
    small = os.path.join(wdir, "pano_small.jpg")
    if os.path.exists(small):
        return small
    try:
        from PIL import Image
        im = Image.open(src)
        im.thumbnail((2048, 1024))
        im.convert("RGB").save(small, "JPEG", quality=85)
        return small
    except Exception:
        return src


def load_occupancy(wdir):
    """读取几何占用摘要（优先用 03 生成的结果，否则现场计算）"""
    occ_p = os.path.join(wdir, "occupancy.json")
    if os.path.exists(occ_p):
        return json.load(open(occ_p, encoding="utf-8"))
    glb = os.path.join(wdir, "collider.glb")
    if os.path.exists(glb):
        try:
            import trimesh, numpy as np
            mesh = trimesh.load(glb, force="mesh")
            pts = mesh.vertices
            vox = set(map(tuple, np.floor(pts / 1.0).astype(int)))
            return {"voxel_size": 1.0, "occupied_voxels": len(vox),
                    "bounds_min": mesh.bounds[0].tolist(),
                    "bounds_max": mesh.bounds[1].tolist(),
                    "total_faces": int(len(mesh.faces))}
        except Exception as e:
            return {"error": str(e)}
    return {}


def ground_one(wdir):
    cap_p = os.path.join(wdir, "caption.txt")
    caption = open(cap_p, encoding="utf-8").read() if os.path.exists(cap_p) else ""
    pano = prepare_pano(wdir)
    occ = load_occupancy(wdir)

    if BACKEND == "openai":
        raw = call_openai_compatible(build_user_text(caption, occ), pano)
        parsed = extract_json(raw)
        snap = to_snapshot(parsed, caption, occ)
    elif BACKEND == "deepseek":
        raw = call_deepseek(build_user_text(caption, occ), pano)
        parsed = extract_json(raw)
        snap = to_snapshot(parsed, caption, occ)
    elif BACKEND == "codex":
        raw = call_codex_cli(build_user_text(caption, occ), pano)
        parsed = extract_json(raw)
        snap = to_snapshot(parsed, caption, occ)
    else:  # offline
        parsed = json.loads(call_offline(caption, occ))
        snap = to_snapshot(parsed, caption, occ)

    snap["_occupancy"] = occ
    warns = validate(snap, occ)
    json.dump(snap, open(os.path.join(wdir, "snapshot.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    # 三臂输入文件
    # 快照：美观版供人读
    json.dump(snap, open(os.path.join(wdir, "snapshot.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    # B2 输入：紧凑 JSON（去掉缩进空白 token，与 B2-A1 散文做 token 对齐）
    compact = json.dumps(snap, ensure_ascii=False, separators=(",", ":"))
    open(os.path.join(wdir, "input_B2.json"), "w", encoding="utf-8").write(compact)
    flat = build_b2a1_text(snap)
    open(os.path.join(wdir, "input_B2A1.txt"), "w", encoding="utf-8").write(flat)
    open(os.path.join(wdir, "input_B2A2.txt"), "w", encoding="utf-8").write(
        f"请搭建一个{snap.get('scene') or '场景'}。")
    # 信息量对账（token 计量，优先 tiktoken）
    n_b2, n_a1, unit = len(compact), len(flat), "字符"
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        n_b2, n_a1, unit = len(enc.encode(compact)), len(enc.encode(flat)), "token"
    except Exception:
        pass
    diff = abs(n_b2 - n_a1) / max(n_b2, 1) * 100
    flag = "OK" if diff <= 15 else "超出±15%，请检查"
    print(f"   信息量对账: B2 {n_b2} {unit} vs B2A1 {n_a1} {unit} (差异 {diff:.0f}% [{flag}])")
    return snap, warns


def main():
    print(f"接地后端: {BACKEND}")
    if BACKEND not in ("openai", "deepseek", "codex", "offline"):
        print(f"[警告] 未知后端 {BACKEND}，将按 offline 处理。")
    if BACKEND == "offline":
        print("[警告] offline 模式仅用于流程自测，结果不得作为论文数据。")
    targets = sorted(glob.glob(os.path.join(DATA_ROOT, "*", "world_*")))
    if not targets:
        print("未找到 world_* 目录，请先跑 01_freeze_assets.py。")
        return
    for wdir in targets:
        snap, warns = ground_one(wdir)
        n = len(snap["objects"])
        print(f"{os.path.basename(wdir)}: 识别 {n} 个物体" +
              (f"，告警 {len(warns)}" if warns else ""))
        for w in warns[:3]:
            print("   -", w)


if __name__ == "__main__":
    main()
