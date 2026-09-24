# -*- coding: utf-8 -*-
"""
阶段3：状态接地层——融合 caption + pano + GLB 几何，生成结构化快照
依赖：pip install trimesh numpy (可选: scikit-learn networkx)

【2026-09-24 实测重要修正】
  实测发现：Marble 的 collider GLB 是"一整块合并几何"，
  连通域分割只能切出 1-2 个大块，无法恢复物体级包围盒。
  详见 experiment/几何解析实测发现.md

  因此本脚本的定位调整为：
    - caption + pano 多模态  -> 提供物体级语义（主力）
    - GLB 几何              -> 提供空间占用/整体尺度（辅助校验）
  几何侧不再依赖"连通域分割出物体"，改用体素占用分析。
"""
import os, json, glob
import numpy as np
import trimesh


def voxel_occupancy(glb_path, voxel_size=1.0):
    """
    几何空间占用分析（替代不可行的连通域分割）。
    返回被几何占据的体素集合大小与整体包围盒，用于描述场景空间结构。
    """
    mesh = trimesh.load(glb_path, force="mesh")
    pts = mesh.vertices
    vox = np.floor(pts / voxel_size).astype(int)
    uniq = set(map(tuple, vox))
    return {"voxel_size": voxel_size, "occupied_voxels": len(uniq),
            "bounds_min": mesh.bounds[0].tolist(),
            "bounds_max": mesh.bounds[1].tolist(),
            "total_faces": int(len(mesh.faces))}


def parse_glb_components(glb_path, min_faces=50):
    """
    [已降级] 连通域分割。
    实测表明 Marble GLB 为合并几何，此函数通常只能得到 1-2 个大块，
    不足以恢复物体级包围盒；保留作为几何完整性检查之用。
    """
    mesh = trimesh.load(glb_path, force="mesh")
    comps = mesh.split(only_watertight=False)
    out = []
    for c in comps:
        if len(c.faces) < min_faces:
            continue
        b = c.bounds  # [[xmin,ymin,zmin],[xmax,ymax,zmax]]
        out.append({
            "bbox_min": b[0].tolist(),
            "bbox_max": b[1].tolist(),
            "centroid": c.centroid.tolist(),
            "faces": int(len(c.faces)),
            "volume": float(c.volume) if c.is_watertight else None,
        })
    out.sort(key=lambda x: x["faces"], reverse=True)
    return out


def build_snapshot(scene, caption, components, spec_objects):
    """把几何成分与 caption 语义对齐，生成快照（对齐可用 LLM 或多模态模型辅助）"""
    objects = []
    for i, t in enumerate(spec_objects):
        comp = components[i] if i < len(components) else None
        objects.append({
            "id": f"{t.replace(' ', '_')}_{i}",
            "type": t,
            "bbox": [comp["bbox_min"], comp["bbox_max"]] if comp else None,
            "position": comp["centroid"] if comp else None,
            "physics": {"collision": "box" if comp else None, "material": None},
            "faces": comp["faces"] if comp else 0,
        })
    return {"scene": scene, "objects": objects,
            "relations": [], "hierarchy": {"room": scene,
            "children": [o["id"] for o in objects]},
            "physics_missing": [o["id"] for o in objects if not o["physics"]["collision"]]}


def check_interpenetration(objects):
    """M7：用轴对齐包围盒检测物体穿插"""
    hits = []
    boxes = [(o["id"], o["bbox"]) for o in objects if o.get("bbox")]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            id1, b1 = boxes[i]; id2, b2 = boxes[j]
            lo = np.maximum(b1[0], b2[0]); hi = np.minimum(b1[1], b2[1])
            if np.all(hi > lo):  # 有重叠
                vol = float(np.prod(np.maximum(hi - lo, 0)))
                if vol > 1e-6:
                    hits.append({"a": id1, "b": id2, "overlap_volume": vol})
    return hits


if __name__ == "__main__":
    DATA_ROOT = os.path.join(os.path.dirname(__file__), "..", "data")
    for sdir in glob.glob(os.path.join(DATA_ROOT, "*", "world_*")):
        glb = os.path.join(sdir, "collider.glb")
        if not os.path.exists(glb):
            continue
        comps = parse_glb_components(glb)
        print(f"{os.path.basename(sdir)}: 解析出 {len(comps)} 个几何成分")
        hits = check_interpenetration([{"id": f"c{i}", "bbox": [c["bbox_min"], c["bbox_max"]]}
                                       for i, c in enumerate(comps)])
        print(f"  M7 潜在穿插对: {len(hits)}")
