# -*- coding: utf-8 -*-
"""
阶段2：构造三臂的状态输入（B2 / B2-A1 / B2-A2）
核心：B2-A1 必须与 B2 信息量相当（条目一一对应），只改"组织形式"。
用法：python 02_build_inputs.py
"""
import os, json, glob

DATA_ROOT = os.path.join(os.path.dirname(__file__), "..", "data")

# ---- 场景任务书（真值来源，须与状态接地层解耦）----
# 这里给出"预期物体清单"作为 M2/M3 的独立真值，由人预先定义后固定
SPEC = {
    "living_room": ["fabric sofa", "wooden coffee table", "bookshelf", "floor lamp", "window", "curtain"],
    "basketball_court": ["basketball", "hoop", "bench", "fence", "ground"],
    "beach_sea": ["sand", "sea water", "sand dune", "shell", "sky"],
}


def build_b2_snapshot(scene, caption, glb_path, meta):
    """
    B2 结构化快照。
    真实实现需解析 GLB 几何做连通域/包围盒，再与 caption 语义对齐。
    此处给出结构骨架 + 从 caption 抽取的语义条目占位。
    """
    # TODO: 接入 GLB 解析（见 03_parse_grounding.py）后填充 objects/bbox/position
    objects = []
    for i, t in enumerate(SPEC[scene]):
        objects.append({
            "id": f"{t.replace(' ', '_')}_{i}",
            "type": t,
            "bbox": None,          # 待几何解析填充
            "position": None,
            "physics": {"collision": None, "material": None}  # 待填充
        })
    return {
        "scene": scene,
        "objects": objects,
        "relations": [],           # 待从 caption 抽取
        "hierarchy": {"room": scene, "children": [o["id"] for o in objects]},
        "physics_missing": [o["id"] for o in objects if not o["physics"]["collision"]],
        "source_caption": caption
    }


def snapshot_to_flattened_text(snap):
    """
    把 B2 快照改写成 B2-A1 等量非结构化文本。
    逐条目对应：每个 object 一句、每个 relation 一句、层级一句。
    """
    lines = [f"这个场景是{snap['scene']}。"]
    for o in snap["objects"]:
        lines.append(f"场景中有一个{o['type']}。")
    for r in snap.get("relations", []):
        lines.append(f"{r['subject']} 与 {r['object']} 的关系是{r['relation']}。")
    lines.append(f"这些物体都属于{snap['hierarchy']['room']}。")
    if snap.get("physics_missing"):
        lines.append("部分物体缺少物理参数。")
    return " ".join(lines)


def main():
    for sdir in glob.glob(os.path.join(DATA_ROOT, "*", "world_*")):
        meta_p = os.path.join(sdir, "meta.json")
        if not os.path.exists(meta_p):
            continue
        meta = json.load(open(meta_p, encoding="utf-8"))
        scene = meta["scene"]
        caption = open(os.path.join(sdir, "caption.txt"), encoding="utf-8").read()
        glb = os.path.join(sdir, "collider.glb")

        # B2
        snap = build_b2_snapshot(scene, caption, glb, meta)
        json.dump(snap, open(os.path.join(sdir, "input_B2.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        # B2-A1（等量非结构化文本）
        flat = snapshot_to_flattened_text(snap)
        open(os.path.join(sdir, "input_B2A1.txt"), "w", encoding="utf-8").write(flat)
        # B2-A2（仅意图）
        intent = f"请搭建一个{scene}的场景。"
        open(os.path.join(sdir, "input_B2A2.txt"), "w", encoding="utf-8").write(intent)

        # 信息量对账
        n_b2 = len(json.dumps(snap, ensure_ascii=False))
        n_a1 = len(flat)
        print(f"{os.path.basename(sdir)}: B2快照{n_b2}字符 vs A1文本{n_a1}字符 "
              f"(差异 {abs(n_b2-n_a1)/max(n_b2,1)*100:.0f}%)")
    print("三臂输入构造完成。请检查信息量差异是否在 ±15% 内。")


if __name__ == "__main__":
    main()
