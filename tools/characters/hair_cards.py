"""Procedural Style B hair for the Exolune character pipeline: sculpted locks fitted over each MPFB2 head.

Each lock is a solid clump traced from the scalp, pointed at its tip, with fine strands drawn over it (an opaque
strand texture, its normal and ORM), shaded along its length by CharacterPixel.hlsl's Kajiya-Kay lobes.
"""
import math
import random
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def _save_rgba_png(rgba_u8: np.ndarray, path: Path):
    """Save top-down uint8 RGBA numpy array directly to PNG via Blender native image API (no Pillow needed)."""
    h, w, _ = rgba_u8.shape
    img = bpy.data.images.new(name=path.stem, width=w, height=h, alpha=True)
    # Flip vertically because Blender image pixels are stored bottom-to-top (row 0 = V=0 root).
    flat = (rgba_u8[::-1].astype(np.float32) / 255.0).ravel()
    img.pixels.foreach_set(flat)
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def generate_lock_textures(tex_dir: Path, w: int = 256, h: int = 1024) -> dict[str, Path]:
    """Strand detail for sculpted locks: U across a lock, V from its root (0) to its tip (1), fully opaque.

    A lock is a solid shape; broad painted strokes of hair run over all of it. Its sides and root fall into shadow,
    and its tip catches more light: a lock reads as a rounded clump of hair, painted stroke by stroke.
    """
    tex_dir.mkdir(parents=True, exist_ok=True)
    paths = {k: tex_dir / f"hair_locks_v3_{k}.png" for k in ("albedo", "normal", "orm")}
    if all(q.exists() for q in paths.values()):
        return paths
    rng = np.random.default_rng(20261123)
    v_coord = np.linspace(1.0, 0.0, h, dtype=np.float32)  # image row 0 is the tip, V = 1
    x = np.arange(w, dtype=np.float32)[None, :]
    height = np.zeros((h, w), dtype=np.float32)
    # Painted style: broad strokes of hair along the lock, light over a darker ground, as a brush lays them.
    tone = np.full((h, w), 0.74, dtype=np.float32)  # the shade between strokes
    for _ in range(110):
        cx = rng.uniform(0.0, w) + rng.uniform(1.0, 5.0) * np.sin(v_coord * math.pi * rng.uniform(0.6, 1.8) + rng.uniform(0, 6.3))
        r = rng.uniform(2.0, 4.5)
        d = np.abs(x - cx[:, None]) / r
        hgt = np.sqrt(np.clip(1.0 - d * d, 0.0, 1.0)) * rng.uniform(0.5, 1.0)
        front = hgt > height
        height = np.where(front, hgt, height)
        tone = np.where(front & (hgt > 0.05), rng.uniform(0.80, 1.12) * (0.88 + 0.12 * hgt), tone)
    u = (x / (w - 1))[0]
    side_ao = 0.62 + 0.38 * np.sin(np.pi * u) ** 0.6
    root_ao = 0.55 + 0.45 * np.clip(v_coord / 0.20, 0.0, 1.0)
    tip_lift = 1.0 + 0.10 * np.clip((v_coord - 0.6) / 0.4, 0.0, 1.0)
    lum = np.clip(tone * side_ao[None, :] * root_ao[:, None] * tip_lift[:, None], 0.2, 1.0)
    rgb = np.stack([lum * 1.02, lum * 0.99, lum * 0.95], axis=-1)
    alb = np.concatenate([np.rint(np.clip(rgb, 0, 1) * 255), np.full((h, w, 1), 255.0)], axis=-1).astype(np.uint8)
    _save_rgba_png(alb, paths["albedo"])
    gx = np.zeros_like(height)
    gx[:, 1:-1] = (height[:, 2:] - height[:, :-2]) * 0.8
    nx, ny, nz = -gx, np.zeros_like(gx), np.ones_like(gx)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    nrm = np.stack([nx * inv * 0.5 + 0.5, ny * inv * 0.5 + 0.5, nz * inv * 0.5 + 0.5, np.ones_like(gx)], axis=-1)
    _save_rgba_png(np.rint(nrm * 255).astype(np.uint8), paths["normal"])
    ao = np.clip(side_ao[None, :] * root_ao[:, None] * (0.8 + 0.2 * height), 0.3, 1.0)
    rough = np.clip(0.48 - 0.10 * height, 0.34, 0.56)
    orm = np.stack([ao, rough, np.clip(0.6 + 0.4 * height, 0, 1), np.ones_like(ao)], axis=-1)
    _save_rgba_png(np.rint(orm * 255).astype(np.uint8), paths["orm"])
    return paths


def _srgb(c: float) -> float:
    v = max(0.012, min(1.0, float(c)))
    return v ** 2.2


def _make_hair_material(name: str, hair_color: list[float], tex_paths: dict[str, Path], opaque_cap: bool = False, locks: bool = False):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.44 if not opaque_cap else 0.90
    bsdf.inputs["Metallic"].default_value = 0.0
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.24 if not opaque_cap else 0.05
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    # Recipe hair_color is MPFB2 linear RGB; gentle gamma 1.35 deepens jet-black/espresso/chestnut without chalky grey.
    c = [max(0.018, min(1.0, float(x)) ** 1.35) for x in hair_color]
    if opaque_cap:
        # Deep matte root-shadow under-cap tucked inside the hair-card hairline perimeter.
        bsdf.inputs["Base Color"].default_value = (c[0] * 0.52, c[1] * 0.52, c[2] * 0.52, 1.0)
        if hasattr(mat, "blend_method"):
            mat.blend_method = "OPAQUE"
        return mat

    alb_img = bpy.data.images.load(str(tex_paths["albedo"]), check_existing=True)
    nrm_img = bpy.data.images.load(str(tex_paths["normal"]), check_existing=True)
    nrm_img.colorspace_settings.name = "Non-Color"

    tex = nodes.new("ShaderNodeTexImage")
    tex.image = alb_img
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    mix.inputs["B"].default_value = (c[0], c[1], c[2], 1.0)
    links.new(tex.outputs["Color"], mix.inputs["A"])
    links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    if not locks:
        links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])

    ntex = nodes.new("ShaderNodeTexImage")
    ntex.image = nrm_img
    nmap = nodes.new("ShaderNodeNormalMap")
    nmap.inputs["Strength"].default_value = 0.85
    links.new(ntex.outputs["Color"], nmap.inputs["Color"])
    links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    # Wire ORM AO channel into glTF Material Output Occlusion if present.
    orm_img = bpy.data.images.load(str(tex_paths["orm"]), check_existing=True)
    orm_img.colorspace_settings.name = "Non-Color"
    ng = bpy.data.node_groups.get("glTF Material Output")
    if ng is None:
        ng = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        ng.interface.new_socket(name="Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    aotex = nodes.new("ShaderNodeTexImage")
    aotex.image = orm_img
    sep = nodes.new("ShaderNodeSeparateColor")
    links.new(aotex.outputs["Color"], sep.inputs["Color"])
    gltf_out = nodes.new("ShaderNodeGroup")
    gltf_out.node_tree = ng
    links.new(sep.outputs["Red"], gltf_out.inputs["Occlusion"])

    if hasattr(mat, "blend_method"):
        mat.blend_method = "OPAQUE" if locks else "CLIP"
    return mat


def _make_hairtie_material(name: str):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        # Warm antique woven indigo-charcoal tie cuff with subtle satin sheen.
        bsdf.inputs["Base Color"].default_value = (_srgb(0.20), _srgb(0.24), _srgb(0.32), 1.0)
        bsdf.inputs["Roughness"].default_value = 0.62
        bsdf.inputs["Metallic"].default_value = 0.0
    return mat


def _add_lock(bm, uv_layer, pts: list[Vector], normals: list[Vector], half_widths: list[float], thick: float = 0.36,
              mat_idx: int = 0, sides: int = 8):
    """A sculpted lock along `pts`: a closed lens section, full from its root, drawn to a point at its tip.

    U runs across the lock, V from its root (0) to its tip (1), as on a card: the strand shading follows V. A flat card
    read as a strip of straw; a lock with its own thickness shades as a clump and casts its shadow on the next one.
    """
    n = len(pts)
    us = [0.5 + 0.5 * math.cos(2.0 * math.pi * j / sides) for j in range(sides)]
    rings, tan = [], Vector((0.0, 0.0, -1.0))
    for k, p in enumerate(pts):
        d = pts[min(k + 1, n - 1)] - pts[max(k - 1, 0)]
        tan = d.normalized() if d.length > 1e-6 else tan
        nrm = normals[k] - tan * normals[k].dot(tan)
        nrm = nrm.normalized() if nrm.length > 1e-5 else Vector((0.0, 0.0, 1.0))
        side = tan.cross(nrm).normalized()
        draw = min(1.0, max(0.0, (k / (n - 1) - 0.45) / 0.55))
        hw = half_widths[k] * (1.0 - 0.9 * draw * draw * (3.0 - 2.0 * draw))
        rings.append([bm.verts.new(p + side * (math.cos(a) * hw) + nrm * (math.sin(a) * hw * thick))
                      for a in (2.0 * math.pi * j / sides for j in range(sides))])
    tip = bm.verts.new(pts[-1] + tan * half_widths[-1] * 0.6)

    def face(verts, uvs):
        f = bm.faces.new(verts)
        f.smooth = True
        f.material_index = mat_idx
        for loop, uv in zip(f.loops, uvs):
            loop[uv_layer].uv = uv

    for k in range(n - 1):
        v0, v1 = k / float(n), (k + 1) / float(n)
        for j in range(sides):
            j2 = (j + 1) % sides
            face((rings[k][j], rings[k + 1][j], rings[k + 1][j2], rings[k][j2]),
                 ((us[j], v0), (us[j], v1), (us[j2], v1), (us[j2], v0)))
    v_last = (n - 1) / float(n)
    for j in range(sides):
        j2 = (j + 1) % sides
        face((rings[-1][j], tip, rings[-1][j2]), ((us[j], v_last), (0.5, 1.0), (us[j2], v_last)))


def _add_braid(bm, uv_layer, pts: list[Vector], normals: list[Vector], radius: float, lobe: float = 0.016,
               mat_idx: int = 0, sides: int = 6) -> Vector:
    """A braid along `pts`: a rope whose section swings side to side and swells between crossings, one lobe per
    half period, drawn to a point over its last lobe. Returns its tip. V runs along the braid, as on a lock.

    Three strands crossing read as alternate lobes left and right; a rope of constant section reads as a cord.
    """
    seg = [0.0]
    for a, b in zip(pts, pts[1:]):
        seg.append(seg[-1] + (b - a).length)
    total = seg[-1]
    n = max(4, int(total / (lobe / 4.0)) + 1)
    rings, tan = [], Vector((0.0, 0.0, -1.0))
    for k in range(n):
        s = total * k / (n - 1)
        j = min(len(seg) - 2, max(0, next((i for i in range(len(seg) - 1) if seg[i + 1] >= s), len(seg) - 2)))
        f = (s - seg[j]) / max(seg[j + 1] - seg[j], 1e-9)
        p = pts[j].lerp(pts[j + 1], f)
        nr = normals[j].lerp(normals[j + 1], f)
        d = pts[j + 1] - pts[j]
        tan = d.normalized() if d.length > 1e-9 else tan
        nr = nr - tan * nr.dot(tan)
        nr = nr.normalized() if nr.length > 1e-6 else Vector((0.0, 0.0, 1.0))
        side = tan.cross(nr).normalized()
        th = 2.0 * math.pi * s / lobe
        end = min(1.0, max(0.0, (total - s) / (1.5 * lobe)))
        r = radius * (0.78 + 0.22 * abs(math.cos(th))) * (0.25 + 0.75 * end)
        c = p + side * (0.35 * radius * math.sin(th) * end)
        rings.append([bm.verts.new(c + side * (math.cos(a) * r) + nr * (math.sin(a) * r))
                      for a in (2.0 * math.pi * q / sides for q in range(sides))])
    tip = bm.verts.new(pts[-1] + tan * radius * 0.5)
    us = [0.5 + 0.5 * math.cos(2.0 * math.pi * q / sides) for q in range(sides)]
    for k in range(n - 1):
        v0, v1 = k / float(n), (k + 1) / float(n)
        for q in range(sides):
            q2 = (q + 1) % sides
            f_ = bm.faces.new((rings[k][q], rings[k + 1][q], rings[k + 1][q2], rings[k][q2]))
            f_.smooth, f_.material_index = True, mat_idx
            for loop, uv in zip(f_.loops, ((us[q], v0), (us[q], v1), (us[q2], v1), (us[q2], v0))):
                loop[uv_layer].uv = uv
    for q in range(sides):
        q2 = (q + 1) % sides
        f_ = bm.faces.new((rings[-1][q], tip, rings[-1][q2]))
        f_.smooth, f_.material_index = True, mat_idx
        for loop, uv in zip(f_.loops, ((us[q], (n - 1) / float(n)), (0.5, 1.0), (us[q2], (n - 1) / float(n)))):
            loop[uv_layer].uv = uv
    return pts[-1]


def _add_bead(bm, uv_layer, at: Vector, axis: Vector, radius: float, length: float, mat_idx: int, sides: int = 8):
    """A brass bead threaded on a braid's end: a short barrel around `axis`."""
    axis = axis.normalized()
    u = axis.cross(Vector((0.0, 0.0, 1.0)) if abs(axis.z) < 0.9 else Vector((1.0, 0.0, 0.0))).normalized()
    w = axis.cross(u)
    rings = []
    for t, rr in ((-0.5, 0.8), (-0.3, 1.0), (0.3, 1.0), (0.5, 0.8)):
        rings.append([bm.verts.new(at + axis * (t * length) + (u * math.cos(a) + w * math.sin(a)) * radius * rr)
                      for a in (2.0 * math.pi * q / sides for q in range(sides))])
    for k in range(3):
        for q in range(sides):
            q2 = (q + 1) % sides
            f_ = bm.faces.new((rings[k][q], rings[k + 1][q], rings[k + 1][q2], rings[k][q2]))
            f_.smooth, f_.material_index = True, mat_idx
            for loop in f_.loops:
                loop[uv_layer].uv = (0.5, 0.5)


def _measure_head_frame(human_obj, rig):
    """Measure exact head cranium bounds and build scalp collision BVH in world/object space."""
    b_head = rig.data.bones["head"]
    mw = human_obj.matrix_world
    head_base = b_head.head_local.copy()
    # Cranium center sits slightly above head bone base and slightly behind face.
    top_z = max((mw @ v.co).z for v in human_obj.data.vertices)
    head_verts = [mw @ v.co for v in human_obj.data.vertices if (mw @ v.co).z > head_base.z - 0.02]
    front_y = min(v.y for v in head_verts)
    back_y = max(v.y for v in head_verts)
    side_x = max(abs(v.x) for v in head_verts)

    # Approximate cranium ellipsoid center & radii for clean hair draping.
    cx = 0.0
    cy = 0.5 * (front_y + back_y) + 0.012
    cz = head_base.z + (top_z - head_base.z) * 0.50
    rx = side_x * 0.94
    ry = 0.5 * (back_y - front_y) * 0.92
    rz = (top_z - cz) * 0.98

    depsgraph = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(human_obj, depsgraph)
    return {
        "center": Vector((cx, cy, cz)),
        "radii": Vector((rx, ry, rz)),
        "top_z": top_z,
        "head_base_z": head_base.z,
        "front_y": front_y,
        "back_y": back_y,
        "side_x": side_x,
        "bvh": bvh,
    }


def _push_outside_body(pt: Vector, head_info: dict, clearance: float = 0.008) -> tuple[Vector, Vector]:
    """Ensure a hair ribbon point stays cleanly outside the head/neck/upper-torso surface."""
    c = head_info["center"]
    rad = head_info["radii"]
    # 1. Exact BVH surface push-out against head/face/neck/shoulders mesh.
    loc, norm, _idx, dist = head_info["bvh"].find_nearest(pt)
    if loc is not None and norm is not None:
        to_p = pt - loc
        if to_p.dot(norm) < clearance:
            pt = loc + norm * clearance
        out_n = norm.normalized()
    else:
        out_n = (pt - c).normalized()

    # 2. Extra soft forehead/face guard so side locks never clip into cheeks/eyes/ears.
    rel = pt - c
    if rel.z > -rad.z * 0.85:
        ell = math.sqrt((rel.x / max(rad.x, 0.05)) ** 2 + (rel.y / max(rad.y, 0.05)) ** 2 + (rel.z / max(rad.z, 0.05)) ** 2)
        min_ell = 1.0 + clearance / max(rad.x, 0.05)
        if ell < min_ell and ell > 1e-4:
            pt = c + rel * (min_ell / ell)
            out_n = Vector((rel.x / (rad.x ** 2), rel.y / (rad.y ** 2), rel.z / (rad.z ** 2))).normalized()
    return pt, out_n


def _hairline_pol(az: float, style: str) -> float:
    """Anatomical hairline polar angle (from +Z crown) as a function of azimuth (0 = back +Y, +-pi = front -Y)."""
    a = (az + math.pi) % (2.0 * math.pi) - math.pi
    abs_deg = math.degrees(abs(a))
    cos_b = math.cos(a)  # +1 back nape, 0 ears/temples, -1 center forehead
    # Exact MPFB2 skull hairline contour from cranium center:
    # - Center forehead (180 deg): ~71 deg (smooth forehead hairline above brow).
    # - Temple corners (130 deg): ~84 deg dipping smoothly to sideburn (~98 deg at 104 deg).
    # - Ear arch (84 deg): ~92 deg clearing ear top cleanly.
    # - Behind-ear & occipital nape (0..65 deg): ~120..132 deg covering the entire painted MPFB2 nape hairline!
    base_deg = 104.0 + 30.0 * cos_b
    sideburn = 13.0 * math.exp(-((abs_deg - 104.0) / 15.0) ** 2)
    ear_arch = -5.0 * math.exp(-((abs_deg - 82.0) / 10.0) ** 2)
    behind_ear = 10.0 * math.exp(-((abs_deg - 55.0) / 18.0) ** 2)
    deg = base_deg + sideburn + ear_arch + behind_ear
    if style == "styleb_swept_short":
        deg -= 4.0 * max(0.0, cos_b)  # slightly higher tapered short nape
    return math.radians(max(68.0, min(136.0, deg)))


def _build_scalp_cap(bm: bmesh.types.BMesh, uv_layer, head_info: dict, mat_idx: int, style: str):
    """Build a deep matte skull under-cap strictly tucked inside the hair-card hairline perimeter."""
    c = head_info["center"]
    rad = head_info["radii"]
    n_u = 32
    n_v = 12
    grid = []
    for iv in range(n_v):
        frac_v = iv / float(n_v - 1)  # 0 = crown top, 1 = inset hairline rim
        row = []
        for iu in range(n_u):
            az = (iu / float(n_u)) * 2.0 * math.pi
            cos_b = math.cos(az)
            # Tuck cap extra-high at the front forehead (cos_b < 0) so wispy bangs never reveal a hard cap edge!
            inset_deg = 5.0 + (7.5 * max(0.0, -cos_b) if style != "styleb_high_ponytail" else 0.0)
            max_pol = _hairline_pol(az, style) - math.radians(inset_deg)
            pol = frac_v * max_pol
            dir_v = Vector((math.sin(pol) * math.sin(az), math.sin(pol) * math.cos(az), math.cos(pol)))
            hit_loc, hit_n, _i, _d = head_info["bvh"].ray_cast(c, dir_v, 0.25)
            if hit_loc is not None:
                p = hit_loc + dir_v * 0.0018
            else:
                p = c + Vector((dir_v.x * rad.x, dir_v.y * rad.y, dir_v.z * rad.z)) * 1.006
            row.append(bm.verts.new(p))
        grid.append(row)
    for iv in range(n_v - 1):
        for iu in range(n_u):
            iu2 = (iu + 1) % n_u
            try:
                f = bm.faces.new((grid[iv][iu], grid[iv + 1][iu], grid[iv + 1][iu2], grid[iv][iu2]))
                f.smooth = True
                f.material_index = mat_idx
                for loop in f.loops:
                    loop[uv_layer].uv = (0.12, 0.12)
            except ValueError:
                pass


def _add_hair_tie_cuff(bm: bmesh.types.BMesh, uv_layer, knot: Vector, mat_idx: int):
    """Sculpted wrapped hair-tie cuff snugly encircling the ponytail knot."""
    axis = Vector((0.0, 0.92, -0.39)).normalized()  # ponytail exit axis (back + slightly down)
    side_x = Vector((1.0, 0.0, 0.0))
    side_z = axis.cross(side_x).normalized()
    n_ring = 20
    n_prof = 8
    r_major = 0.022
    r_minor = 0.0065
    rings = []
    for i in range(n_ring):
        a = (i / float(n_ring)) * 2.0 * math.pi
        rad_dir = side_x * math.cos(a) + side_z * math.sin(a)
        ring_c = knot + rad_dir * r_major
        prof = []
        for j in range(n_prof):
            b = (j / float(n_prof)) * 2.0 * math.pi
            p = ring_c + rad_dir * (r_minor * 0.72 * math.cos(b)) + axis * (r_minor * 1.35 * math.sin(b))
            prof.append(bm.verts.new(p))
        rings.append(prof)
    for i in range(n_ring):
        i2 = (i + 1) % n_ring
        for j in range(n_prof):
            j2 = (j + 1) % n_prof
            try:
                f = bm.faces.new((rings[i][j], rings[i2][j], rings[i2][j2], rings[i][j2]))
                f.smooth = True
                f.material_index = mat_idx
                for loop in f.loops:
                    loop[uv_layer].uv = (i / float(n_ring), j / float(n_prof))
            except ValueError:
                pass


def build_styleb_hair(
    human_obj,
    rig,
    style_name: str,
    hair_color: list[float],
    tex_dir: Path,
    seed: int = 42,
):
    """Create a fitted, rigged multi-layer Hair Cards mesh object for the given MPFB2 character."""
    tex_paths = generate_lock_textures(tex_dir)
    head_info = _measure_head_frame(human_obj, rig)
    rng = random.Random(seed)

    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Material 0 = alpha-tested multi-strand hair cards, Material 1 = dark opaque under-scalp cap.
    mat_cards = _make_hair_material(f"EX_HAIR_{style_name}_locks", hair_color, tex_paths, locks=True)
    mat_cap = _make_hair_material(f"EX_HAIR_{style_name}_cap", hair_color, tex_paths, opaque_cap=True)
    mat_tie = _make_hairtie_material(f"EX_CLOTH_TRIM_{style_name}_hairtie") if style_name == "styleb_high_ponytail" else None
    if style_name == "styleb_braids":  # brass beads on the braids' ends
        mat_tie = bpy.data.materials.new(f"EX_METAL_BRASS_{style_name}_beads")
        mat_tie.use_nodes = True
        bsdf = mat_tie.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (_srgb(0.74), _srgb(0.62), _srgb(0.35), 1.0)
        bsdf.inputs["Metallic"].default_value = 0.88
        bsdf.inputs["Roughness"].default_value = 0.3

    _build_scalp_cap(bm, uv_layer, head_info, mat_idx=1, style=style_name)

    c = head_info["center"]
    rad = head_info["radii"]
    # A short cut ends above the garment's collar: the cards only know the body, and a lock that hangs lower pokes
    # through the cloth.
    floor_z = rig.data.bones["neck_01"].head_local.z + 0.06 if style_name == "styleb_swept_short" else None
    # A lock in front of the face ends above the brows: the eyes stay open, as the style's faces show them. Fuller
    # locks of the same length hung their points over the eyes.
    lid = rig.data.bones.get("eyelid_upper_l")
    brow = (abs(lid.head_local.x) + 0.035, lid.head_local.z + 0.022) if lid is not None else None

    def scalp_point(az: float, pol: float, lift: float = 0.005) -> tuple[Vector, Vector]:
        dir_v = Vector((math.sin(pol) * math.sin(az), math.sin(pol) * math.cos(az), math.cos(pol)))
        hit_loc, hit_n, _i, _d = head_info["bvh"].ray_cast(c, dir_v, 0.25)
        if hit_loc is not None and hit_n is not None:
            return hit_loc + hit_n.normalized() * lift, hit_n.normalized()
        p = c + Vector((dir_v.x * rad.x, dir_v.y * rad.y, dir_v.z * rad.z))
        return p + dir_v * lift, dir_v

    def trace_lock(
        root_az: float,
        root_pol: float,
        length_m: float,
        n_steps: int,
        width_root: float,
        width_tip: float,
        lane: int,
        layer_lift: float,
        sweep_az: float = 0.0,
        outward_flare: float = 0.012,
        curl_in: float = 0.0,
        wave_amp: float = 0.004,
        camber: float = 0.26,
    ):
        p0, n0 = scalp_point(root_az, root_pol, lift=layer_lift)
        pts = [p0]
        norms = [n0]
        hws = [width_root * 0.5]
        az = root_az
        pol = root_pol
        step_len = length_m / float(n_steps - 1)
        cur = p0.copy()
        w_ph = rng.uniform(0.0, 2.0 * math.pi)

        for k in range(1, n_steps):
            t = k / float(n_steps - 1)
            az_k = az + sweep_az * (t ** 1.15)
            down_dir = Vector((math.cos(pol) * math.sin(az_k), math.cos(pol) * math.cos(az_k), -math.sin(pol)))
            grav = Vector((0.0, 0.0, -1.0))
            out_rad = Vector((math.sin(az_k), math.cos(az_k), 0.0))
            skull_w = max(0.0, 1.0 - t * 1.45)
            flow = down_dir * skull_w + grav * (1.0 - skull_w * 0.72)
            radial_push = outward_flare * math.sin(t * math.pi) - curl_in * (t ** 2.2)
            flow = flow + out_rad * (radial_push / max(step_len, 0.01) * 0.35)
            side_v = Vector((math.cos(az_k), -math.sin(az_k), 0.0))
            flow = flow + side_v * (wave_amp * math.sin(t * math.pi * 2.2 + w_ph) * 4.0)
            flow.normalize()

            nxt = cur + flow * step_len
            if floor_z is not None and nxt.z < floor_z and len(pts) > 1:
                break
            if brow is not None and len(pts) > 2 and abs(nxt.x) < brow[0] and nxt.z < brow[1] and nxt.y < c.y - rad.y * 0.4:
                break
            clr = layer_lift + 0.004 * math.sin(t * math.pi)
            if nxt.y < c.y - rad.y * 0.35 and nxt.z < c.z + rad.z * 0.25:
                clr = max(clr, layer_lift + 0.008)
            nxt, out_n = _push_outside_body(nxt, head_info, clearance=clr)
            blend_n = (out_n * 0.65 + Vector((math.sin(az_k), math.cos(az_k), 0.18 * (1.0 - t))).normalized() * 0.35).normalized()
            pts.append(nxt)
            norms.append(blend_n)
            w_t = width_root * (1.0 - t) + width_tip * t
            w_t *= 1.0 + 0.14 * math.sin(t * math.pi)
            hws.append(max(w_t * 0.5, 0.004))
            cur = nxt
            pol = min(math.pi * 0.85, pol + step_len / max(rad.z, 0.08))

        # A lock gathers the strands of a card and a half: fewer, fuller clumps, as the style's references draw them.
        _add_lock(bm, uv_layer, pts, norms, [hw * 1.7 for hw in hws], thick=0.5 if lane == 3 else 0.36)

    def stratified_az(i: int, n: int, az_lo: float, az_hi: float, jitter: float = 0.38) -> float:
        step = (az_hi - az_lo) / float(max(n, 1))
        return az_lo + (i + 0.5 + rng.uniform(-jitter, jitter)) * step

    if style_name == "styleb_long_layered":
        # Matches Style B woman: open face, soft side-parted framing locks sweeping AWAY from eyes + flowing shoulders!
        # Layer 0: Full lower temple/behind-ear/nape inner curtain (strictly behind cheekbones: |az| <= 0.62*pi).
        for i in range(30):
            az = stratified_az(i, 30, -math.pi * 0.62, math.pi * 0.62, 0.28)
            hl = _hairline_pol(az, style_name)
            pol = hl * rng.uniform(0.66, 0.90)
            length = rng.uniform(0.24, 0.34)
            trace_lock(az, pol, length, 8, 0.062, 0.042, lane=0, layer_lift=0.005, sweep_az=rng.uniform(-0.08, 0.08), outward_flare=0.015, wave_amp=0.005)
        # Layer 1: Stratified mid-crown dense volume (back & sides behind forehead; temples sweep BACKWARD away from eyes!).
        for i in range(36):
            az = stratified_az(i, 36, -math.pi * 0.72, math.pi * 0.72, 0.30)
            hl = _hairline_pol(az, style_name)
            pol = hl * rng.uniform(0.32, 0.62)
            is_temple = abs(az) > math.pi * 0.50
            length = rng.uniform(0.32, 0.42) if not is_temple else rng.uniform(0.24, 0.32)
            # Negative sweep when az > 0 pulls temple locks BACK toward ears (+pi/2), keeping eyes & cheeks wide open!
            sw = (-0.42 if az > 0 else 0.42) if is_temple else rng.uniform(-0.08, 0.08)
            trace_lock(az, pol, length, 9, 0.058, 0.036, lane=0, layer_lift=0.008, sweep_az=sw, outward_flare=0.022, wave_amp=0.006)
        # Layer 2: Stratified top-crown flowing locks parting cleanly from top crown over sides & back (zero apex hole!).
        for i in range(44):
            az = stratified_az(i, 44, -math.pi * 0.78, math.pi * 0.78, 0.30)
            pol = rng.uniform(math.radians(3), math.radians(26))
            is_front = abs(az) > math.pi * 0.54
            length = rng.uniform(0.34, 0.45) if not is_front else rng.uniform(0.22, 0.30)
            sw = (-0.52 if az > 0 else 0.52) if is_front else rng.uniform(-0.10, 0.10)
            trace_lock(az, pol, length, 10, 0.050, 0.026, lane=1, layer_lift=0.013, sweep_az=sw, outward_flare=0.026, wave_amp=0.008)
        # Crown apex / part-line cover (eliminates top-down pinhole cleanly!).
        for i in range(14):
            az = stratified_az(i, 14, -math.pi * 0.65, math.pi * 0.65, 0.25)
            pol = rng.uniform(math.radians(1), math.radians(10))
            trace_lock(az, pol, rng.uniform(0.30, 0.40), 9, 0.048, 0.024, lane=0, layer_lift=0.011, sweep_az=(-0.22 if az > 0 else 0.22), outward_flare=0.020, wave_amp=0.006)
        # Airy eyebrow-skimming side-swept bangs (parted off-center, stopping cleanly ABOVE the eyes!).
        for i in range(22):
            rel_u = stratified_az(i, 22, -0.64, 0.64, 0.22)
            az = math.pi + rel_u
            pol = rng.uniform(math.radians(14), math.radians(38))
            # Part slightly left of center: sweep outward away from face center so eyes stay 100% open & expressive!
            to_right = (rel_u > -0.14)
            sw = -0.62 if to_right else 0.62
            # Shortest at forehead center (~0.095 m = brow line), slightly longer framing temples (~0.150 m).
            length = 0.095 + 0.088 * abs(rel_u)
            lane_b = 1 if (i % 2 == 0) else 2
            trace_lock(az, pol, length, 6, 0.036, 0.016, lane=lane_b, layer_lift=0.013 if lane_b == 1 else 0.016, sweep_az=sw, outward_flare=0.015, wave_amp=0.003)
        # Layer 3: Silhouette rim-light flyaway strands (strictly outside face zone!).
        for i in range(20):
            az = stratified_az(i, 20, -math.pi * 0.68, math.pi * 0.68, 0.35)
            pol = rng.uniform(math.radians(8), math.radians(42))
            length = rng.uniform(0.26, 0.42)
            trace_lock(az, pol, length, 9, 0.034, 0.020, lane=3, layer_lift=0.020, sweep_az=(-0.20 if az > 0 else 0.20), outward_flare=0.032, wave_amp=0.010, camber=0.18)

    elif style_name == "styleb_swept_short":
        # Matches Style B man: refined layered medium-short cut with tapered temples/nape, full apex & swept bangs.
        # Layer 0: Full stratified hairline/temple/sideburn/nape taper ring (zero exposed cap!).
        for i in range(42):
            az = stratified_az(i, 42, -math.pi * 0.88, math.pi * 0.88, 0.28)
            hl = _hairline_pol(az, style_name)
            pol = hl * rng.uniform(0.62, 0.92)
            length = rng.uniform(0.055, 0.088) if abs(az) < math.pi * 0.58 else rng.uniform(0.048, 0.072)
            sw = rng.uniform(-0.14, 0.20)
            trace_lock(az, pol, length, 6, 0.048, 0.024, lane=0, layer_lift=0.005, sweep_az=sw, outward_flare=0.008, wave_amp=0.002)
        # Layer 1: Stratified mid-crown layered volume sweeping across temples & occipital crown.
        for i in range(38):
            az = stratified_az(i, 38, -math.pi, math.pi, 0.32)
            hl = _hairline_pol(az, style_name)
            pol = hl * rng.uniform(0.32, 0.62)
            length = rng.uniform(0.085, 0.125)
            sw = -0.26 if az > -0.2 else 0.24
            trace_lock(az, pol, length, 6, 0.046, 0.022, lane=0 if i % 2 == 0 else 1, layer_lift=0.009, sweep_az=sw, outward_flare=0.013, wave_amp=0.004)
        # Crown apex whorl cover (eliminates top-center pinhole completely!).
        for i in range(14):
            az = stratified_az(i, 14, -math.pi, math.pi, 0.25)
            pol = rng.uniform(math.radians(1), math.radians(11))
            trace_lock(az, pol, rng.uniform(0.095, 0.125), 6, 0.046, 0.022, lane=0, layer_lift=0.011, sweep_az=(-0.22 if az > 0 else 0.22), outward_flare=0.014, wave_amp=0.003)
        # Layer 2: Top crown & textured forward-side swept bangs (stopping cleanly above eyes!).
        for i in range(34):
            az = stratified_az(i, 34, -math.pi, math.pi, 0.35)
            pol = rng.uniform(math.radians(6), math.radians(34))
            is_bang = abs(az) > math.pi * 0.62
            length = rng.uniform(0.095, 0.128) if is_bang else rng.uniform(0.095, 0.135)
            sw = -0.34 if az > -0.25 else 0.28
            trace_lock(az, pol, length, 7, 0.040, 0.018, lane=1 if not is_bang else 2, layer_lift=0.014, sweep_az=sw, outward_flare=0.018, wave_amp=0.005)
        # Layer 3: Wispy textured bangs & outer crown silhouette strands.
        for i in range(22):
            az = stratified_az(i, 22, -math.pi, math.pi, 0.38)
            pol = rng.uniform(math.radians(8), math.radians(48))
            is_bang = abs(az) > math.pi * 0.60
            length = rng.uniform(0.075, 0.115) if is_bang else rng.uniform(0.085, 0.135)
            sw = (-0.36 if az > 0 else 0.36) if is_bang else rng.uniform(-0.20, 0.25)
            trace_lock(az, pol, length, 6, 0.030, 0.014, lane=2 if i < 11 else 3, layer_lift=0.018, sweep_az=sw, outward_flare=0.023, wave_amp=0.006, camber=0.22)

    elif style_name == "styleb_chic_bob":
        # Layered jaw-to-collarbone sleek bob with open face, full behind-ear coverage, inward curve & feathered fringe.
        for i in range(32):
            az = stratified_az(i, 32, -math.pi * 0.66, math.pi * 0.66, 0.28)
            hl = _hairline_pol(az, style_name)
            pol = hl * rng.uniform(0.62, 0.90)
            length = rng.uniform(0.13, 0.18)
            trace_lock(az, pol, length, 7, 0.056, 0.036, lane=0, layer_lift=0.005, sweep_az=rng.uniform(-0.08, 0.08), outward_flare=0.013, curl_in=0.020, wave_amp=0.003)
        for i in range(36):
            az = stratified_az(i, 36, -math.pi * 0.74, math.pi * 0.74, 0.30)
            hl = _hairline_pol(az, style_name)
            pol = hl * rng.uniform(0.28, 0.60)
            is_temple = abs(az) > math.pi * 0.52
            length = rng.uniform(0.18, 0.24)
            sw = (-0.38 if az > 0 else 0.38) if is_temple else rng.uniform(-0.10, 0.10)
            trace_lock(az, pol, length, 8, 0.054, 0.034, lane=0, layer_lift=0.009, sweep_az=sw, outward_flare=0.018, curl_in=0.022, wave_amp=0.004)
        for i in range(42):
            az = stratified_az(i, 42, -math.pi * 0.78, math.pi * 0.78, 0.32)
            pol = rng.uniform(math.radians(2), math.radians(26))
            is_front = abs(az) > math.pi * 0.54
            length = rng.uniform(0.19, 0.26) if not is_front else rng.uniform(0.15, 0.20)
            sw = (-0.45 if az > 0 else 0.45) if is_front else rng.uniform(-0.10, 0.10)
            trace_lock(az, pol, length, 8, 0.048, 0.024, lane=1, layer_lift=0.014, sweep_az=sw, outward_flare=0.024, curl_in=0.025, wave_amp=0.005)
        for i in range(18):
            rel_u = stratified_az(i, 18, -0.58, 0.58, 0.24)
            az = math.pi + rel_u
            pol = rng.uniform(math.radians(20), math.radians(42))
            sw = -0.62 if (rel_u > -0.15) else 0.62
            length = 0.080 + 0.075 * abs(rel_u)
            trace_lock(az, pol, length, 6, 0.032, 0.014, lane=2, layer_lift=0.017, sweep_az=sw, outward_flare=0.012, wave_amp=0.003)
        for i in range(18):
            az = stratified_az(i, 18, -math.pi * 0.70, math.pi * 0.70, 0.36)
            pol = rng.uniform(math.radians(8), math.radians(42))
            trace_lock(az, pol, rng.uniform(0.16, 0.23), 8, 0.032, 0.016, lane=3, layer_lift=0.019, sweep_az=(-0.18 if az > 0 else 0.18), outward_flare=0.027, curl_in=0.018, wave_amp=0.007, camber=0.18)

    elif style_name == "styleb_braids":
        # Cornrows laid on the scalp from the hairline straight back over the head, each going on as a box braid that
        # hangs down the back, a brass bead threaded on its end.
        # Rows across the whole head, the outer ones over the temples and above the ears: spread over its top
        # alone, they left the sides a bare helmet.
        rows = 17
        for i in range(rows):
            u = ((i + 0.5) / rows) * 2.0 - 1.0
            x_off = math.copysign(abs(u) ** 0.85, u) * rad.x * 0.95
            path, nrms = [], []
            for k in range(26):
                phi = math.radians(19.0 + (222.0 - 19.0) * k / 25.0)  # from the front hairline over the top to the back
                d = Vector((x_off / max(rad.x, 0.05), -math.cos(phi), math.sin(phi))).normalized()
                p, nrm = scalp_point(math.atan2(d.x, d.y), math.acos(max(-1.0, min(1.0, d.z))), lift=0.003)
                path.append(p)
                nrms.append(nrm)
            _add_braid(bm, uv_layer, path, nrms, radius=0.0055, lobe=0.015)
            # The hanging braid starts where the cornrow ends and falls down the back, spreading a little.
            start = path[-1]
            hang = [start]
            hn = [nrms[-1]]
            length = rng.uniform(0.30, 0.40)
            cur = start.copy()
            for k in range(1, 14):
                t = k / 13.0
                step = Vector((x_off * 0.9, 0.35 - 0.3 * t, -1.0)).normalized() * (length / 13.0)
                cur, out_n = _push_outside_body(cur + step, head_info, clearance=0.012)
                hang.append(cur)
                hn.append(out_n)
            tip = _add_braid(bm, uv_layer, hang, hn, radius=0.0065, lobe=0.017)
            _add_bead(bm, uv_layer, hang[-3], hang[-2] - hang[-4], 0.0072, 0.012, mat_idx=2)
        # Over each side, four rows run from the temple above the ear to the back of the head, then hang too: rows
        # laid front to back alone reach no lower than halfway down the side.
        for side in (-1.0, 1.0):
            for pol_deg in (58.0, 67.0, 76.0, 85.0):
                path, nrms = [], []
                for k in range(22):
                    az = side * math.radians(108.0 + (50.0 - 108.0) * k / 21.0)
                    p, nrm = scalp_point(az, math.radians(pol_deg + 18.0 * k / 21.0), lift=0.003)
                    path.append(p)
                    nrms.append(nrm)
                _add_braid(bm, uv_layer, path, nrms, radius=0.0055, lobe=0.015)
                hang, hn, cur = [path[-1]], [nrms[-1]], path[-1].copy()
                length = rng.uniform(0.26, 0.36)
                for k in range(1, 12):
                    t = k / 11.0
                    step = Vector((side * 0.25, 0.25 - 0.2 * t, -1.0)).normalized() * (length / 11.0)
                    cur, out_n = _push_outside_body(cur + step, head_info, clearance=0.012)
                    hang.append(cur)
                    hn.append(out_n)
                _add_braid(bm, uv_layer, hang, hn, radius=0.0065, lobe=0.017)
                _add_bead(bm, uv_layer, hang[-3], hang[-2] - hang[-4], 0.0072, 0.012, mat_idx=2)

    else:  # styleb_high_ponytail
        # Full hairline-to-knot swept crown + sculpted hair-tie cuff + lush cascading ponytail. No loose tendrils at the
        # temples: a few thin cards hanging clear of the face read as stray wires.
        knot = c + Vector((0.0, rad.y * 1.05, rad.z * 0.34))

        def add_swept_crown_card(az: float, pol: float, lift: float, w_root: float, w_tip: float, lane: int, camber: float = 0.16):
            # Start root flush against scalp (1.8 mm) so feathered strand roots grow organically out of skin!
            p0, n0 = scalp_point(az, pol, lift=0.0018)
            pts, norms, hws = [], [], []
            d0 = (p0 - c).normalized()
            dk = (knot - c).normalized()
            n_seg = 8
            for k in range(n_seg):
                t = k / float(n_seg - 1)
                dir_t = d0.lerp(dk, t ** 1.05)
                if dir_t.length > 1e-5:
                    dir_t.normalize()
                else:
                    dir_t = dk
                # Smoothly rise from flush root (1.8 mm) to natural crown loft (`lift`), then converge tightly into knot.
                cur_lift = 0.0018 + (lift - 0.0018) * math.sin(min(t * 1.35, 1.0) * math.pi * 0.5)
                hit_loc, hit_n, _i, _d = head_info["bvh"].ray_cast(c, dir_t, 0.25)
                if hit_loc is not None and hit_n is not None:
                    surf_p = hit_loc + hit_n.normalized() * cur_lift
                else:
                    surf_p = p0.lerp(knot, t)
                knot_blend = max(0.0, (t - 0.72) / 0.28) ** 1.4
                p = surf_p.lerp(knot, knot_blend)
                p, n = _push_outside_body(p, head_info, clearance=cur_lift)
                pts.append(p)
                norms.append(n)
                hws.append((w_root * (1.0 - t) + w_tip * t) * 0.5)
            _add_lock(bm, uv_layer, pts, norms, [hw * 1.2 for hw in hws], thick=0.06)  # combed back: a smooth sheet

        # Ring 1: FULL hairline perimeter (54 tightly overlapping feathered cards covering forehead, temples, behind-ears & full nape!).
        for i in range(54):
            az = stratified_az(i, 54, -math.pi, math.pi, 0.16)
            hl = _hairline_pol(az, style_name)
            pol = hl * rng.uniform(0.95, 1.03)
            add_swept_crown_card(az, pol, lift=0.0045, w_root=0.044, w_tip=0.018, lane=0, camber=0.14)

        # Ring 2: Mid-crown full ring (40 overlapping flow cards covering upper temples, crown sides & back!).
        for i in range(40):
            az = stratified_az(i, 40, -math.pi, math.pi, 0.22)
            hl = _hairline_pol(az, style_name)
            pol = hl * rng.uniform(0.48, 0.74)
            add_swept_crown_card(az, pol, lift=0.0068, w_root=0.044, w_tip=0.017, lane=0 if i % 2 == 0 else 1, camber=0.18)

        # Ring 3: Upper crown & brushed-back sleek sheen strands (28 cards).
        for i in range(28):
            az = stratified_az(i, 28, -math.pi, math.pi, 0.26)
            hl = _hairline_pol(az, style_name)
            pol = hl * rng.uniform(0.14, 0.42)
            add_swept_crown_card(az, pol, lift=0.0092, w_root=0.038, w_tip=0.015, lane=1, camber=0.20)

        # Soft feathered hairline baby-hair wisps along forehead, temples & behind ears.
        for i in range(20):
            az = math.pi + stratified_az(i, 20, -1.55, 1.55, 0.22)
            hl = _hairline_pol(az, style_name)
            add_swept_crown_card(az, hl * rng.uniform(0.96, 1.05), lift=0.0060, w_root=0.026, w_tip=0.012, lane=2, camber=0.12)

        # Sculpted wrapped hair-tie cuff right around the ponytail knot!
        _add_hair_tie_cuff(bm, uv_layer, knot, mat_idx=2)

        # Lush cascading multi-layer ponytail locks arching out and down from the knot.
        for i in range(42):
            ang = (i / 42.0) * 2.0 * math.pi + rng.uniform(-0.14, 0.14)
            ring_r = rng.uniform(0.004, 0.017)
            p0 = knot + Vector((math.cos(ang) * ring_r, 0.0, math.sin(ang) * ring_r))
            length = rng.uniform(0.28, 0.39)
            out_y = rng.uniform(0.045, 0.115)
            out_x = math.cos(ang) * rng.uniform(0.032, 0.092)
            w_ph = rng.uniform(0.0, 2.0 * math.pi)
            pts, norms, hws = [], [], []
            for k in range(9):
                t = k / 8.0
                arch_z = 0.036 * math.sin(t * math.pi * 0.85) - length * (t ** 1.25)
                arch_y = out_y * (math.sin(min(t * 1.4, 1.0) * math.pi * 0.5)) + 0.03 * t
                arch_x = out_x * (t ** 0.75) + 0.006 * math.sin(t * math.pi * 2.5 + w_ph)
                p = p0 + Vector((arch_x, arch_y, arch_z))
                p, _ = _push_outside_body(p, head_info, clearance=0.014)
                n = Vector((math.cos(ang), 0.75 + 0.25 * math.sin(ang), 0.25 * (1.0 - t))).normalized()
                pts.append(p)
                norms.append(n)
                hws.append((0.040 * (1.0 - 0.55 * t) * (1.0 + 0.25 * math.sin(t * math.pi))) * 0.5)
            lane = 0 if i < 16 else (1 if i < 30 else 3)
            _add_lock(bm, uv_layer, pts, norms, [hw * 1.6 for hw in hws], thick=0.38)

    mesh = bpy.data.meshes.new(f"hair_cards_{style_name}")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    obj = bpy.data.objects.new(f"hair_cards_{style_name}", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat_cards)
    obj.data.materials.append(mat_cap)
    if mat_tie is not None:
        obj.data.materials.append(mat_tie)
    obj.parent = rig
    mod = obj.modifiers.new(name="Armature", type="ARMATURE")
    mod.object = rig

    # Smooth anatomical skinning: crown 100% head; long locks below nape smoothly blend neck/spine_03 so
    # long hair rests over shoulders cleanly instead of clipping into the collar during head Aim IK!
    vg_head = obj.vertex_groups.new(name="head")
    vg_neck = obj.vertex_groups.new(name="neck_01")
    vg_sp3 = obj.vertex_groups.new(name="spine_03")
    nape_z = head_info["head_base_z"] - 0.01
    for v in mesh.vertices:
        dz = nape_z - v.co.z
        if dz <= 0.0:
            vg_head.add([v.index], 1.0, "REPLACE")
        else:
            t = min(1.0, dz / 0.18)
            w_sp = 0.55 * (t ** 1.4)
            w_nk = 0.25 * math.sin(t * math.pi * 0.5)
            w_hd = max(0.20, 1.0 - w_sp - w_nk)
            s = w_hd + w_nk + w_sp
            vg_head.add([v.index], w_hd / s, "REPLACE")
            vg_neck.add([v.index], w_nk / s, "REPLACE")
            vg_sp3.add([v.index], w_sp / s, "REPLACE")

    return obj
