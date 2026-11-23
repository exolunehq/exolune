"""Clean, orient, classify into semantic PBR material classes, and locally reduce Tripo H3.1 wardrobe pieces.

Follows AGENTS.md strictly:
- Local reduction only (never Tripo retopology).
- Never display a generated Tripo atlas: reads the draft's Color + ORM maps on the 2M-poly sculpt
  strictly to assign clean semantic PBR material classes (linen, accent cloth, piping, saddle leather,
  brushed brass, charcoal rubber), applies material-delimited Decimate, and writes metric UVs for
  Exolune's shared tactile PBR weave/grain detail maps.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_image_np(img) -> np.ndarray:
    w, h = img.size[0], img.size[1]
    arr = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(arr)
    # Blender pixels are bottom-to-top (row 0 = V=0, row H-1 = V=1).
    return arr.reshape((h, w, 4))


def _sample_uv(img_np: np.ndarray, uv: np.ndarray) -> np.ndarray:
    h, w, _ = img_np.shape
    u = np.mod(uv[:, 0], 1.0)
    v = np.mod(uv[:, 1], 1.0)
    ix = np.clip(np.rint(u * (w - 1)).astype(np.int32), 0, w - 1)
    iy = np.clip(np.rint(v * (h - 1)).astype(np.int32), 0, h - 1)
    return img_np[iy, ix]


def _make_pbr_mat(name: str, rgb: tuple[float, float, float], roughness: float, metallic: float = 0.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def _detect_jacket_front_sign(obj, color_np: np.ndarray) -> float:
    """Detect whether the jacket's slate-indigo wrap collar sits on +X or -X in raw Tripo space."""
    me = obj.data
    n_p = len(me.polygons)
    if n_p == 0 or not me.uv_layers:
        return 1.0
    uv_data = me.uv_layers.active.data
    # Sample every 30th polygon in the upper chest band (Z > 0.15) to find where the blue collar sits.
    xs_blue = []
    for pi in range(0, n_p, 30):
        p = me.polygons[pi]
        c = p.center
        if c.z < 0.10 or abs(c.y) > 0.22:
            continue
        uv = uv_data[p.loop_start].uv
        col = _sample_uv(color_np, np.array([[uv[0], uv[1]]], dtype=np.float32))[0]
        # Slate-indigo has higher blue channel than red.
        if col[2] > col[0] + 0.035 and col[2] > 0.22:
            xs_blue.append(c.x)
    if not xs_blue:
        return 1.0
    return 1.0 if float(np.median(xs_blue)) >= 0.0 else -1.0


def _detect_boot_toe_sign(obj) -> float:
    """Detect whether the lower toe box points toward +Y or -Y in raw Tripo space (heel sits higher/taller)."""
    me = obj.data
    verts = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", verts)
    pts = verts.reshape((-1, 3))
    z_hi = pts[:, 2].max()
    # The tall ankle cuff sits at the heel end; the toe box extends opposite the tall ankle cuff!
    top_y = float(np.median(pts[pts[:, 2] > z_hi - 0.15, 1]))
    # Toe is opposite the ankle cuff!
    return -1.0 if top_y >= 0.0 else 1.0


def _detect_satchel_front_sign(obj, color_np: np.ndarray, orm_np) -> float:
    """Detect whether the satchel's front pockets & brass buckles sit on +X or -X in raw Tripo space."""
    me = obj.data
    if not me.uv_layers:
        return 1.0
    uv_data = me.uv_layers.active.data
    xs_feat = []
    for pi in range(0, len(me.polygons), 25):
        p = me.polygons[pi]
        c = p.center
        if c.z > 0.22 or c.z < -0.35 or abs(c.y) > 0.38:
            continue
        uv = uv_data[p.loop_start].uv
        if orm_np is not None:
            orm = _sample_uv(orm_np, np.array([[uv[0], uv[1]]], dtype=np.float32))[0]
            if orm[2] > 0.35:  # metallic brass buckle / rivets on front face
                xs_feat.append(c.x)
        col = _sample_uv(color_np, np.array([[uv[0], uv[1]]], dtype=np.float32))[0]
        if col[0] > col[1] + 0.06 and col[0] > 0.20 and col[2] < 0.25:  # chestnut leather front straps
            xs_feat.append(c.x)
    if not xs_feat:
        return 1.0
    return 1.0 if float(np.median(xs_feat)) >= 0.0 else -1.0


def _assign_metric_box_uvs(obj, tile_m: float = 0.36):
    """Assign distortion-free metric triplanar box UVs (1 UV unit = tile_m meters) for crisp weave/grain tiling."""
    me = obj.data
    while len(me.uv_layers) > 0:
        me.uv_layers.remove(me.uv_layers[0])
    uv_layer = me.uv_layers.new(name="UVMap")
    inv_t = 1.0 / max(tile_m, 0.05)

    v_co = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", v_co)
    v_co = v_co.reshape((-1, 3))

    n_loops = len(me.loops)
    loop_vi = np.empty(n_loops, dtype=np.int32)
    me.loops.foreach_get("vertex_index", loop_vi)

    uvs = np.empty((n_loops, 2), dtype=np.float32)
    for p in me.polygons:
        n = p.normal
        ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
        ls = p.loop_start
        lt = p.loop_total
        pts = v_co[loop_vi[ls : ls + lt]]
        if az >= ax and az >= ay:
            uvs[ls : ls + lt, 0] = pts[:, 0] * inv_t
            uvs[ls : ls + lt, 1] = pts[:, 1] * inv_t
        elif ax >= ay and ax >= az:
            uvs[ls : ls + lt, 0] = pts[:, 1] * inv_t
            uvs[ls : ls + lt, 1] = pts[:, 2] * inv_t
        else:
            uvs[ls : ls + lt, 0] = pts[:, 0] * inv_t
            uvs[ls : ls + lt, 1] = pts[:, 2] * inv_t
    uv_layer.data.foreach_set("uv", uvs.ravel())


def _render_check_card(obj, out_png: Path, title: str):
    """Render a quick 2-view (front 3/4 + back 3/4) Cycles inspection card of the cleaned PBR piece."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 20
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"

    world = bpy.data.worlds.new("KitReview")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.34, 0.37, 0.42, 1.0)
        bg.inputs["Strength"].default_value = 0.85

    # Duplicate piece side-by-side: left = front 3/4, right = back 3/4.
    ws = [obj.matrix_world @ v.co for v in obj.data.vertices]
    lo = Vector((min(v.x for v in ws), min(v.y for v in ws), min(v.z for v in ws)))
    hi = Vector((max(v.x for v in ws), max(v.y for v in ws), max(v.z for v in ws)))
    sz = hi - lo
    span = max(sz.x, sz.y, sz.z, 0.15)
    ctr = (lo + hi) * 0.5

    dup_front = obj.copy()
    dup_front.data = obj.data
    bpy.context.collection.objects.link(dup_front)
    dup_front.location = Vector((-span * 0.62 - ctr.x, -ctr.y, -lo.z))
    dup_front.rotation_euler = Euler((0.0, 0.0, math.radians(22.0)), "XYZ")

    dup_back = obj.copy()
    dup_back.data = obj.data
    bpy.context.collection.objects.link(dup_back)
    dup_back.location = Vector((span * 0.62 - ctr.x, -ctr.y, -lo.z))
    dup_back.rotation_euler = Euler((0.0, 0.0, math.radians(158.0)), "XYZ")

    obj.hide_render = True

    cam_d = bpy.data.cameras.new("Cam")
    cam_d.lens = 50.0
    cam = bpy.data.objects.new("Cam", cam_d)
    bpy.context.collection.objects.link(cam)
    cam.location = Vector((0.0, -span * 2.55, sz.z * 0.56))
    cam.rotation_euler = (Vector((0.0, 0.0, sz.z * 0.48)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    for name, loc, energy, size in (
        ("Key", (-span * 2.0, -span * 2.4, span * 2.2), 240.0 * span * span, span * 1.4),
        ("Fill", (span * 2.2, -span * 1.6, span * 1.4), 95.0 * span * span, span * 1.8),
        ("Rim", (0.0, span * 2.2, span * 1.9), 150.0 * span * span, span * 1.2),
    ):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.size = size
        lo_obj = bpy.data.objects.new(name, ld)
        bpy.context.collection.objects.link(lo_obj)
        lo_obj.location = Vector(loc)
        lo_obj.rotation_euler = (Vector((0.0, 0.0, sz.z * 0.5)) - lo_obj.location).to_track_quat("-Z", "Y").to_euler()

    scene.render.filepath = str(out_png)
    bpy.ops.render.render(write_still=True)

    obj.hide_render = False
    bpy.data.objects.remove(dup_front, do_unlink=True)
    bpy.data.objects.remove(dup_back, do_unlink=True)


# The smallest connected part each material class keeps, in m2 by class index. A panel is large, piping and straps are
# thin but long, hardware is small: a class absent here keeps every part.
MIN_PART_AREA = {
    "jacket": {0: 20e-4, 1: 20e-4, 2: 3e-4},
    "boot": {0: 5e-4, 1: 5e-4, 2: 5e-4, 3: 5e-4},
    "satchel": {0: 5e-4, 1: 1.5e-4},
}


def _merge_small_parts(me, mat_ids: np.ndarray, min_area: dict) -> np.ndarray:
    """Give each connected part below its class's minimum area to the neighbouring class it borders most.

    A generated atlas shades and stains its colours: read face by face, it leaves islands of a wrong class inside every
    panel. A majority vote cannot remove them without also eating thin piping.
    """
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    areas = [f.calc_area() for f in bm.faces]
    cur = mat_ids.copy()
    changed = True
    while changed:
        changed = False
        seen = np.zeros(len(bm.faces), dtype=bool)
        for start in bm.faces:
            if seen[start.index]:
                continue
            cls = int(cur[start.index])
            seen[start.index] = True
            part, stack, area, border = [], [start], 0.0, {}
            while stack:
                f = stack.pop()
                part.append(f.index)
                area += areas[f.index]
                for e in f.edges:
                    for nf in e.link_faces:
                        other = int(cur[nf.index])
                        if other != cls:
                            border[other] = border.get(other, 0.0) + e.calc_length()
                        elif not seen[nf.index]:
                            seen[nf.index] = True
                            stack.append(nf)
            if border and area < min_area.get(cls, 0.0):
                cur[part] = max(border, key=border.get)
                changed = True
    bm.free()
    return cur


def process_piece(kind: str, draft_glb: Path, out_dir: Path, target_tris: int):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(draft_glb))
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"No mesh in {draft_glb}")
    obj = meshes[0]
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    obj.rotation_mode = "XYZ"
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Locate draft Color and ORM textures strictly for semantic material-class reading.
    color_np = None
    orm_np = None
    for img in bpy.data.images:
        ln = img.name.lower()
        if "color" in ln or "base" in ln or "diff" in ln:
            color_np = _load_image_np(img)
        elif "orm" in ln or "metal" in ln or "rough" in ln:
            orm_np = _load_image_np(img)
    if color_np is None:
        raise RuntimeError(f"Missing Color texture in {draft_glb}")

    # 1. Orient piece into canonical Exolune Blender space (-Y forward, +X left, +Z up) and metric scale.
    if kind == "jacket":
        front_sgn = _detect_jacket_front_sign(obj, color_np)
        rot_z = -math.pi * 0.5 if front_sgn > 0 else math.pi * 0.5
        obj.rotation_mode = "XYZ"
        obj.rotation_euler = Euler((0.0, 0.0, rot_z), "XYZ")
        bpy.ops.object.transform_apply(rotation=True)
        ws = [v.co for v in obj.data.vertices]
        z_lo, z_hi = min(v.z for v in ws), max(v.z for v in ws)
        sc = 0.72 / max(z_hi - z_lo, 1e-4)
        obj.scale = (sc, sc, sc)
        bpy.ops.object.transform_apply(scale=True)
        ws = [v.co for v in obj.data.vertices]
        cx = 0.5 * (min(v.x for v in ws) + max(v.x for v in ws))
        cy = 0.5 * (min(v.y for v in ws) + max(v.y for v in ws))
        z0 = min(v.z for v in ws)
        obj.location = Vector((-cx, -cy, -z0))
        bpy.ops.object.transform_apply(location=True)

    elif kind == "boot":
        toe_sgn = _detect_boot_toe_sign(obj)
        rot_z = math.pi if toe_sgn > 0 else 0.0
        obj.rotation_mode = "XYZ"
        obj.rotation_euler = Euler((0.0, 0.0, rot_z), "XYZ")
        bpy.ops.object.transform_apply(rotation=True)
        ws = [v.co for v in obj.data.vertices]
        y_lo, y_hi = min(v.y for v in ws), max(v.y for v in ws)
        sc = 0.278 / max(y_hi - y_lo, 1e-4)
        obj.scale = (sc, sc, sc)
        bpy.ops.object.transform_apply(scale=True)
        ws = [v.co for v in obj.data.vertices]
        cx = 0.5 * (min(v.x for v in ws) + max(v.x for v in ws))
        cy = 0.5 * (min(v.y for v in ws) + max(v.y for v in ws))
        z0 = min(v.z for v in ws)
        obj.location = Vector((-cx, -cy, -z0))
        bpy.ops.object.transform_apply(location=True)

    elif kind == "satchel":
        front_sgn = _detect_satchel_front_sign(obj, color_np, orm_np)
        rot_z = -math.pi * 0.5 if front_sgn > 0 else math.pi * 0.5
        obj.rotation_mode = "XYZ"
        obj.rotation_euler = Euler((0.0, 0.0, rot_z), "XYZ")
        bpy.ops.object.transform_apply(rotation=True)
        ws = [v.co for v in obj.data.vertices]
        x_lo, x_hi = min(v.x for v in ws), max(v.x for v in ws)
        sc = 0.26 / max(x_hi - x_lo, 1e-4)
        obj.scale = (sc, sc, sc)
        bpy.ops.object.transform_apply(scale=True)
        ws = [v.co for v in obj.data.vertices]
        cx = 0.5 * (min(v.x for v in ws) + max(v.x for v in ws))
        cy = 0.5 * (min(v.y for v in ws) + max(v.y for v in ws))
        z0 = min(v.z for v in ws)
        obj.location = Vector((-cx, -cy, -z0))
        bpy.ops.object.transform_apply(location=True)

    # 2. Classify every polygon on the ORIGINAL 2M-poly sculpt BEFORE welding/decimation so Tripo's UVs are
    # 100% untouched (zero UV-seam smearing across islands!), then weld split seams for a watertight manifold.
    me = obj.data
    n_src = len(me.polygons)
    p_centers = np.empty(n_src * 3, dtype=np.float32)
    me.polygons.foreach_get("center", p_centers)
    p_centers = p_centers.reshape((-1, 3))

    loop_starts = np.empty(n_src, dtype=np.int32)
    me.polygons.foreach_get("loop_start", loop_starts)
    n_l = len(me.loops)
    all_uv = np.empty(n_l * 2, dtype=np.float32)
    me.uv_layers.active.data.foreach_get("uv", all_uv)
    all_uv = all_uv.reshape((-1, 2))
    p_uv = all_uv[loop_starts]

    col = _sample_uv(color_np, p_uv)
    r, g, b = col[:, 0], col[:, 1], col[:, 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    sat = (cmax - cmin) / np.maximum(cmax, 1e-4)
    metal_ch = _sample_uv(orm_np, p_uv)[:, 2] if orm_np is not None else np.zeros(n_src, dtype=np.float32)

    z_lo, z_hi = float(p_centers[:, 2].min()), float(p_centers[:, 2].max())
    z_norm = (p_centers[:, 2] - z_lo) / max(z_hi - z_lo, 1e-4)
    y_lo, y_hi = float(p_centers[:, 1].min()), float(p_centers[:, 1].max())
    y_norm = (p_centers[:, 1] - y_lo) / max(y_hi - y_lo, 1e-4)  # 0 = front (-Y), 1 = back (+Y)

    me.materials.clear()
    mat_ids = np.zeros(n_src, dtype=np.int32)

    if kind == "jacket":
        me.materials.append(_make_pbr_mat("EX_CLOTH_MAIN_jacket",   (0.84, 0.80, 0.71), roughness=0.82, metallic=0.0))
        me.materials.append(_make_pbr_mat("EX_CLOTH_ACCENT_jacket", (0.28, 0.34, 0.44), roughness=0.78, metallic=0.0))
        me.materials.append(_make_pbr_mat("EX_CLOTH_TRIM_jacket",   (0.39, 0.47, 0.38), roughness=0.76, metallic=0.0))
        me.materials.append(_make_pbr_mat("EX_METAL_BRASS_jacket",  (0.68, 0.56, 0.31), roughness=0.30, metallic=0.88))

        # Two crisp front chest clasps: metallic channel OR warm gold tone strictly in the central front lapel band!
        clasp_zone = (z_norm > 0.42) & (z_norm < 0.82) & (y_norm < 0.36) & (np.abs(p_centers[:, 0]) < 0.085)
        is_brass = clasp_zone & ((metal_ch > 0.24) | ((r > b + 0.14) & (g > b + 0.08) & (lum < 0.58)))
        is_accent = (b > r + 0.022) & (z_norm > 0.44) & (np.abs(p_centers[:, 0]) < 0.15) & (~is_brass)
        is_trim = (~is_accent) & (~is_brass) & (g >= r - 0.008) & (g >= b + 0.006) & (lum < 0.58) & (lum > 0.14)
        mat_ids[is_trim] = 2
        mat_ids[is_accent] = 1
        mat_ids[is_brass] = 3

    elif kind == "boot":
        me.materials.append(_make_pbr_mat("EX_LEATHER_MAIN_boot",   (0.42, 0.22, 0.11), roughness=0.45, metallic=0.0))
        me.materials.append(_make_pbr_mat("EX_RUBBER_SOLE_boot",    (0.11, 0.105, 0.10), roughness=0.72, metallic=0.0))
        me.materials.append(_make_pbr_mat("EX_CLOTH_TRIM_boot",     (0.74, 0.70, 0.60), roughness=0.84, metallic=0.0))
        me.materials.append(_make_pbr_mat("EX_LEATHER_ACCENT_boot", (0.34, 0.37, 0.32), roughness=0.56, metallic=0.0))
        me.materials.append(_make_pbr_mat("EX_METAL_BRASS_boot",    (0.64, 0.52, 0.28), roughness=0.30, metallic=0.86))

        # Clean geometric + color masks: dark charcoal sole, cream canvas top collar, sage rear heel cup, brass hardware.
        is_sole = (z_norm < 0.235) & ((lum < 0.24) | (sat < 0.18))
        is_collar = (z_norm > 0.68) & (lum > 0.44) & (sat < 0.22)
        is_heel = (y_norm > 0.72) & (z_norm >= 0.22) & (z_norm < 0.66) & (sat < 0.18) & (lum > 0.16) & (lum < 0.55)
        is_brass = (metal_ch > 0.55) & (z_norm > 0.28) & (~is_collar)
        mat_ids[is_heel] = 3
        mat_ids[is_collar] = 2
        mat_ids[is_sole] = 1
        mat_ids[is_brass] = 4

    elif kind == "satchel":
        me.materials.append(_make_pbr_mat("EX_CLOTH_BAG_satchel",   (0.54, 0.49, 0.33), roughness=0.84, metallic=0.0))
        me.materials.append(_make_pbr_mat("EX_LEATHER_BAG_satchel", (0.34, 0.16, 0.09), roughness=0.44, metallic=0.0))
        me.materials.append(_make_pbr_mat("EX_METAL_BRASS_satchel", (0.64, 0.53, 0.28), roughness=0.28, metallic=0.88))

        # Chestnut leather piping, straps & top handle (rich warm brown: R significantly exceeds G, low blue!).
        is_leather = ((r > g + 0.075) & (g > b + 0.02) & (lum < 0.42)) | ((z_norm > 0.84) & (r > g + 0.04) & (lum < 0.45))
        is_brass = (metal_ch > 0.55) & (z_norm > 0.15) & (z_norm < 0.82)
        mat_ids[is_leather] = 1
        mat_ids[is_brass] = 2

    me.polygons.foreach_set("material_index", mat_ids)
    for img in list(bpy.data.images):
        bpy.data.images.remove(img)

    # 3. Weld split UV seam vertices into a 100% watertight manifold (keeps exact material_index on every face!).
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=5e-5)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")

    # 4. Single watertight material-delimited Local Decimate (2M -> LOD0 budget, NO Tripo retopology!).
    # First gentle decimate to 48k (preserves tiny hardware), merge stray class islands, then final LOD0 target.
    stage1 = obj.modifiers.new(name="Stage1Decimate", type="DECIMATE")
    stage1.decimate_type = "COLLAPSE"
    stage1.ratio = min(1.0, 48000.0 / max(float(len(obj.data.polygons)), 1.0))
    stage1.use_collapse_triangulate = True
    stage1.delimit = {"MATERIAL"}
    bpy.ops.object.modifier_apply(modifier=stage1.name)

    cur_ids = np.empty(len(obj.data.polygons), dtype=np.int32)
    obj.data.polygons.foreach_get("material_index", cur_ids)
    cur_ids = _merge_small_parts(obj.data, cur_ids, MIN_PART_AREA[kind])
    obj.data.polygons.foreach_set("material_index", cur_ids)

    ratio = min(1.0, float(target_tris) / max(float(len(obj.data.polygons)), 1.0))
    mod = obj.modifiers.new(name="LocalDecimate", type="DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    mod.delimit = {"MATERIAL"}
    bpy.ops.object.modifier_apply(modifier=mod.name)

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.delete_loose()
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.shade_smooth()

    # 5. Metric box UVs for crisp weave/leather/metal micro-normal & ORM tiling.
    _assign_metric_box_uvs(obj, tile_m=0.32 if kind == "jacket" else 0.22)
    obj.name = f"kit_{kind}"

    out_dir.mkdir(parents=True, exist_ok=True)
    out_glb = out_dir / f"{kind}.glb"
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=str(out_glb),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_texcoords=True,
        export_normals=True,
        export_tangents=True,
        export_materials="EXPORT",
    )

    preview_png = out_dir / f"{kind}_classes_review.png"
    _render_check_card(obj, preview_png, kind)

    ws = [v.co for v in obj.data.vertices]
    lo = [round(min(v[i] for v in ws), 4) for i in range(3)]
    hi = [round(max(v[i] for v in ws), 4) for i in range(3)]
    class_counts = {}
    for p in obj.data.polygons:
        mn = obj.data.materials[p.material_index].name
        class_counts[mn] = class_counts.get(mn, 0) + 1
    info = {
        "kind": kind,
        "draft_glb": str(draft_glb),
        "draft_sha256": sha256_file(draft_glb),
        "clean_glb": str(out_glb),
        "clean_sha256": sha256_file(out_glb),
        "source_tris": int(n_src),
        "reduced_tris": len(obj.data.polygons),
        "verts": len(obj.data.vertices),
        "bounds_lo": lo,
        "bounds_hi": hi,
        "material_classes": class_counts,
        "review_png": str(preview_png),
    }
    print(f"[prepare_wardrobe_kit] {kind}: {n_src} -> {len(obj.data.polygons)} tris, bounds={lo}..{hi}, classes={class_counts}")
    return info


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="E:/ExoluneAssets/characters-kit-styleb-2026-11-22")
    args = ap.parse_args(argv)

    root = Path(args.root)
    clean_dir = root / "clean"
    drafts = {
        "jacket": (next((root / "drafts" / "jacket").rglob("model.glb")), 16000),
        "boot": (next((root / "drafts" / "boot").rglob("model.glb")), 9000),
        "satchel": (next((root / "drafts" / "satchel").rglob("model.glb")), 9000),
    }
    manifest = {"schema": "exolune.wardrobe.kit.v1", "pieces": {}}
    for kind, (glb, tris) in drafts.items():
        manifest["pieces"][kind] = process_piece(kind, glb, clean_dir, tris)
    (clean_dir / "kit_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[prepare_wardrobe_kit] wrote {clean_dir / 'kit_manifest.json'}")


if __name__ == "__main__":
    import sys
    main()
