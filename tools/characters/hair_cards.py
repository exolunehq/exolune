"""Procedural Style B multi-layer Hair Cards generator for Exolune Blender character pipeline.

Builds high-resolution strand-atlas textures (albedo+alpha, strand normal, root-to-tip ORM)
and anatomically fitted multi-layer arched hair-card meshes directly over each MPFB2 head
using BVHTree scalp projection, eliminating solid "Playmobil" helmets while matching
CharacterPixel.hlsl's Kajiya-Kay V-bitangent anisotropic shading and FoliageSequence TAA dithering.
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


def generate_hair_card_textures(tex_dir: Path, size: int = 1024) -> dict[str, Path]:
    """Generate deterministic 1024x1024 4-lane hair card atlas (albedo+alpha, normal, ORM) with feathered roots & tips."""
    tex_dir.mkdir(parents=True, exist_ok=True)
    albedo_path = tex_dir / "hair_cards_v2_albedo.png"
    normal_path = tex_dir / "hair_cards_v2_normal.png"
    orm_path = tex_dir / "hair_cards_v2_orm.png"
    if albedo_path.exists() and normal_path.exists() and orm_path.exists():
        return {"albedo": albedo_path, "normal": normal_path, "orm": orm_path}

    rng = np.random.default_rng(20261122)
    h, w = size, size
    v_lin = np.linspace(0.0, 1.0, h, dtype=np.float32)  # 0 = root (top in image? UV v=0 is bottom!)
    # In Blender/glTF UVs: image row 0 is TOP (V=1 tip), image row H-1 is BOTTOM (V=0 root).
    v_coord = np.linspace(1.0, 0.0, h, dtype=np.float32)  # row 0 -> V=1 (tip), row H-1 -> V=0 (root)

    cov = np.zeros((h, w), dtype=np.float32)
    height = np.zeros((h, w), dtype=np.float32)
    shade = np.zeros((h, w), dtype=np.float32)
    w_sum = np.zeros((h, w), dtype=np.float32)

    # 4 vertical lanes across U:
    #   0: [0.00..0.25] dense base clump
    #   1: [0.25..0.50] medium flow lock with multi-tapered tips
    #   2: [0.50..0.75] wispy bangs / fringe lock with airy gaps
    #   3: [0.75..1.00] fine outer silhouette flyaway strands
    lane_specs = [
        # (u0, u1, n_strands, width_px_range, tip_min, tip_max, spread, wave_amp)
        (0.00, 0.25, 115, (2.2, 5.2), 0.80, 0.99, 0.86, 0.022),
        (0.25, 0.50,  82, (1.8, 4.4), 0.68, 0.99, 0.78, 0.032),
        (0.50, 0.75,  54, (1.4, 3.4), 0.52, 0.98, 0.72, 0.038),
        (0.75, 1.00,  22, (1.1, 2.3), 0.58, 0.99, 0.76, 0.055),
    ]

    x_grid = np.arange(w, dtype=np.float32)[None, :]  # (1, W)

    for lane_idx, (u0, u1, n_strands, (w_lo, w_hi), t_lo, t_hi, spread, wave_amp) in enumerate(lane_specs):
        cx0 = (u0 + 0.5 * (u1 - u0)) * w
        half_lane = 0.5 * (u1 - u0) * w * spread

        # Sub-clump attractors for natural lock grouping in lanes 1 & 2.
        clump_centers = rng.uniform(-0.72, 0.72, size=5 if lane_idx == 2 else 3)

        for si in range(n_strands):
            if lane_idx in (1, 2) and rng.random() < 0.75:
                cc = clump_centers[si % len(clump_centers)]
                u_rel = np.clip(cc + rng.normal(0.0, 0.16), -0.92, 0.92)
            else:
                u_rel = float(rng.uniform(-0.92, 0.92))

            # Subtle S-wave and tip convergence per strand.
            freq = float(rng.uniform(0.9, 2.2))
            phase = float(rng.uniform(0.0, 2.0 * math.pi))
            amp = float(rng.uniform(0.35, 1.0)) * wave_amp * (u1 - u0) * w
            converge = 1.0 - (0.38 if lane_idx <= 1 else 0.20) * (v_coord ** 1.4)
            # Feathered staggered root start (prevents square shingle tabs!) and smooth multi-tapered tip.
            tip_end = float(rng.uniform(t_lo, t_hi))
            root_start = float(rng.uniform(0.0, 0.09)) if lane_idx <= 1 else float(rng.uniform(0.0, 0.14))

            center_x = cx0 + u_rel * half_lane * converge + amp * np.sin(v_coord * math.pi * freq + phase)
            base_r = float(rng.uniform(w_lo, w_hi))
            # Taper radius smoothly down to 0 at BOTH tip_end and root_start so every lock has organic feathery ends.
            t_taper = np.clip((tip_end - v_coord) / max(0.18 + 0.12 * (lane_idx >= 2), 1e-3), 0.0, 1.0)
            r_taper = np.clip((v_coord - root_start) / (0.11 if lane_idx <= 1 else 0.14), 0.0, 1.0)
            rad = np.maximum(base_r * (0.26 + 0.74 * np.sqrt(t_taper)) * (0.28 + 0.72 * np.sqrt(r_taper)), 0.01)
            active = (v_coord <= tip_end) & (v_coord >= root_start)

            # Evaluate only the narrow horizontal bounding window for speed.
            x_min = max(int(u0 * w) + 1, int(np.floor(center_x.min() - base_r - 2)))
            x_max = min(int(u1 * w) - 1, int(np.ceil(center_x.max() + base_r + 2)))
            if x_max <= x_min:
                continue
            dx = x_grid[:, x_min:x_max] - center_x[:, None]
            d_norm = np.abs(dx) / rad[:, None]
            mask = np.clip(1.0 - d_norm * d_norm, 0.0, 1.0)
            mask *= (t_taper * r_taper)[:, None]
            mask[~active, :] = 0.0

            # Cylindrical strand profile for normal baking & per-strand melanin variation.
            cyl_h = np.sqrt(np.clip(1.0 - np.clip(d_norm, 0.0, 1.0) ** 2, 0.0, 1.0)) * active[:, None]
            melanin = float(rng.uniform(0.76, 1.12))
            depth_z = float(rng.uniform(0.45, 1.0))
            strand_h = cyl_h * depth_z

            sub_cov = cov[:, x_min:x_max]
            sub_h = height[:, x_min:x_max]
            sub_sh = shade[:, x_min:x_max]
            sub_ws = w_sum[:, x_min:x_max]

            # Max-union coverage and front-most strand height/melanin.
            cov[:, x_min:x_max] = np.maximum(sub_cov, np.clip(mask * 1.45, 0.0, 1.0))
            front = strand_h > sub_h
            height[:, x_min:x_max] = np.where(front, strand_h, sub_h)
            sub_sh += mask * melanin * (0.65 + 0.35 * cyl_h)
            sub_ws += mask
            shade[:, x_min:x_max] = sub_sh
            w_sum[:, x_min:x_max] = sub_ws

    # Normalize albedo tone + rich root-to-tip AO & subtle highlight luminance.
    albedo_val = np.where(w_sum > 1e-4, shade / np.maximum(w_sum, 1e-4), 0.75)
    root_ao = 0.48 + 0.52 * np.clip(v_coord / 0.24, 0.0, 1.0)  # darker at root, brighter mid/tip
    tip_lift = 1.0 + 0.12 * np.clip((v_coord - 0.65) / 0.35, 0.0, 1.0)
    lum = np.clip(albedo_val * root_ao[:, None] * tip_lift[:, None], 0.24, 1.0)

    # Slight warm highlight undertone so tinted hair looks silky & alive, never muddy grey.
    r_ch = np.clip(lum * 1.02, 0.0, 1.0)
    g_ch = np.clip(lum * 0.99, 0.0, 1.0)
    b_ch = np.clip(lum * 0.95, 0.0, 1.0)
    # Crisp alpha with soft anti-aliased fiber edges (works cleanly with FoliageSequence temporal dithering).
    alpha_ch = np.clip(cov ** 0.78, 0.0, 1.0)
    # Clean 2px lane borders so mipmaps never bleed across lanes.
    for b_u in (0.0, 0.25, 0.50, 0.75, 1.0):
        bx = int(round(b_u * w))
        alpha_ch[:, max(0, bx - 2) : min(w, bx + 2)] = 0.0

    rgba = np.stack([
        np.rint(r_ch * 255.0).astype(np.uint8),
        np.rint(g_ch * 255.0).astype(np.uint8),
        np.rint(b_ch * 255.0).astype(np.uint8),
        np.rint(alpha_ch * 255.0).astype(np.uint8),
    ], axis=-1)
    _save_rgba_png(rgba, albedo_path)

    # Tangent-space normal from strand cylinder height + gentle per-lane card cross-curvature.
    gx = np.zeros_like(height)
    gy = np.zeros_like(height)
    gx[:, 1:-1] = (height[:, 2:] - height[:, :-2]) * 1.65
    gy[1:-1, :] = (height[2:, :] - height[:-2, :]) * 0.55
    # Add broad convex curve across each lane so cards catch rounded highlight bands.
    u_lane = ((np.arange(w, dtype=np.float32) / float(w)) * 4.0) % 1.0
    lane_tilt = (u_lane - 0.5) * 0.45
    nx = -(gx + lane_tilt[None, :])
    ny = gy
    nz = np.ones_like(height)
    inv_n = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz + 1e-6)
    n_rgb = np.stack([
        np.rint(np.clip((nx * inv_n) * 0.5 + 0.5, 0.0, 1.0) * 255.0).astype(np.uint8),
        np.rint(np.clip((ny * inv_n) * 0.5 + 0.5, 0.0, 1.0) * 255.0).astype(np.uint8),
        np.rint(np.clip((nz * inv_n) * 0.5 + 0.5, 0.0, 1.0) * 255.0).astype(np.uint8),
        np.full((h, w), 255, dtype=np.uint8),
    ], axis=-1)
    _save_rgba_png(n_rgb, normal_path)

    # ORM: R = root & inter-strand AO, G = smooth silky roughness (0.36..0.52), B = sheen mask.
    ao_ch = np.clip((0.52 + 0.48 * root_ao[:, None]) * (0.72 + 0.28 * height), 0.28, 1.0)
    rough_ch = np.clip(0.46 - 0.10 * height + 0.04 * (1.0 - root_ao[:, None]), 0.34, 0.56)
    sheen_ch = np.clip(0.65 + 0.35 * height, 0.4, 1.0)
    orm_rgba = np.stack([
        np.rint(ao_ch * 255.0).astype(np.uint8),
        np.rint(rough_ch * 255.0).astype(np.uint8),
        np.rint(sheen_ch * 255.0).astype(np.uint8),
        np.full((h, w), 255, dtype=np.uint8),
    ], axis=-1)
    _save_rgba_png(orm_rgba, orm_path)
    return {"albedo": albedo_path, "normal": normal_path, "orm": orm_path}


def _srgb(c: float) -> float:
    v = max(0.012, min(1.0, float(c)))
    return v ** 2.2


def _make_hair_material(name: str, hair_color: list[float], tex_paths: dict[str, Path], opaque_cap: bool = False):
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
        mat.blend_method = "CLIP"
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


def _add_arched_ribbon(
    bm: bmesh.types.BMesh,
    uv_layer,
    pts: list[Vector],
    normals: list[Vector],
    half_widths: list[float],
    lane: int,
    camber: float = 0.24,
    mat_idx: int = 0,
):
    """Append a smooth 3-column V-cambered hair card ribbon along 3D curve `pts` with V=0 root -> V=1 tip."""
    u0 = lane * 0.25 + 0.008
    u1 = (lane + 1) * 0.25 - 0.008
    u_mid = 0.5 * (u0 + u1)
    n_seg = len(pts)
    rows = []
    for k in range(n_seg):
        p = pts[k]
        if k == 0:
            tan = (pts[1] - pts[0]).normalized()
        elif k == n_seg - 1:
            tan = (pts[-1] - pts[-2]).normalized()
        else:
            tan = (pts[k + 1] - pts[k - 1]).normalized()
        n = normals[k]
        n = (n - tan * n.dot(tan))
        n = n.normalized() if n.length > 1e-5 else Vector((0.0, 0.0, 1.0))
        side = tan.cross(n)
        side = side.normalized() if side.length > 1e-5 else Vector((1.0, 0.0, 0.0))
        hw = half_widths[k]
        arch = hw * camber
        vl = bm.verts.new(p - side * hw)
        vm = bm.verts.new(p + n * arch)
        vr = bm.verts.new(p + side * hw)
        rows.append((vl, vm, vr))

    for k in range(n_seg - 1):
        v0 = k / float(n_seg - 1)
        v1 = (k + 1) / float(n_seg - 1)
        l0, m0, r0 = rows[k]
        l1, m1, r1 = rows[k + 1]
        for quad, u_pair in (((l0, m0, m1, l1), (u0, u_mid)), ((m0, r0, r1, m1), (u_mid, u1))):
            try:
                f = bm.faces.new(quad)
                f.smooth = True
                f.material_index = mat_idx
                ua, ub = u_pair
                uvs = ((ua, v0), (ub, v0), (ub, v1), (ua, v1))
                for loop, uv in zip(f.loops, uvs):
                    loop[uv_layer].uv = uv
            except ValueError:
                pass


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
    tex_paths = generate_hair_card_textures(tex_dir)
    head_info = _measure_head_frame(human_obj, rig)
    rng = random.Random(seed)

    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    # Material 0 = alpha-tested multi-strand hair cards, Material 1 = dark opaque under-scalp cap.
    mat_cards = _make_hair_material(f"EX_HAIR_{style_name}_cards", hair_color, tex_paths, opaque_cap=False)
    mat_cap = _make_hair_material(f"EX_HAIR_{style_name}_cap", hair_color, tex_paths, opaque_cap=True)
    mat_tie = _make_hairtie_material(f"EX_CLOTH_TRIM_{style_name}_hairtie") if style_name == "styleb_high_ponytail" else None

    _build_scalp_cap(bm, uv_layer, head_info, mat_idx=1, style=style_name)

    c = head_info["center"]
    rad = head_info["radii"]

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

        _add_arched_ribbon(bm, uv_layer, pts, norms, hws, lane=lane, camber=camber, mat_idx=0)

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

    else:  # styleb_high_ponytail
        # Full hairline-to-knot swept crown + sculpted hair-tie cuff + lush cascading ponytail + soft framing tendrils.
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
            _add_arched_ribbon(bm, uv_layer, pts, norms, hws, lane=lane, camber=camber, mat_idx=0)

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
            _add_arched_ribbon(bm, uv_layer, pts, norms, hws, lane=lane, camber=0.28, mat_idx=0)

        # Soft framing temple tendrils (Style B warmth!).
        for sgn in (-1.0, 1.0):
            for j in range(5):
                az = math.pi + sgn * rng.uniform(0.42, 0.82)
                hl = _hairline_pol(az, style_name)
                pol = hl * rng.uniform(0.75, 0.96)
                trace_lock(az, pol, rng.uniform(0.11, 0.17), 6, 0.022, 0.010, lane=2, layer_lift=0.012, sweep_az=sgn * 0.26, outward_flare=0.014, wave_amp=0.004)

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
