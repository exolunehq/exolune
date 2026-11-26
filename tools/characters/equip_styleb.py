"""Modular Style B 3D wardrobe fitter, tailored trousers/belt/strap builder, and eyelid blink rigger.

Fits our locally reduced, semantic-PBR Tripo H3.1 modular wardrobe kit (`jacket.glb`, `boot.glb`,
`satchel.glb`) onto ANY MPFB2 character morph on Exolune's canonical 59-bone skeleton (53 game_engine
+ 4 arm twist bones + 2 upper-eyelid blink bones), aligning jacket sleeves cleanly to MPFB2's pre-bent
42-deg A-pose elbows and transferring smooth, clipping-free weights.
"""
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree


def _srgb(rgb) -> tuple[float, float, float]:
    """Convert perceptual sRGB [0..1] color to physical linear RGB for Blender Principled BSDF & glTF."""
    return tuple(max(0.0, min(1.0, float(c))) ** 2.2 for c in rgb)


def _make_pbr_mat(name: str, srgb: tuple[float, float, float], roughness: float, metallic: float = 0.0):
    mat = bpy.data.materials.new(name=name)
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    lin = _srgb(srgb)
    bsdf.inputs["Base Color"].default_value = (lin[0], lin[1], lin[2], 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def _assign_metric_box_uvs(obj, tile_m: float = 0.30):
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


def _import_single_glb(glb_path: Path, name: str):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    added = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in added if o.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"No mesh imported from {glb_path}")
    obj = meshes[0]
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    obj.parent = None
    obj.rotation_mode = "XYZ"
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in added:
        if o != obj:
            bpy.data.objects.remove(o, do_unlink=True)
    obj.name = name
    return obj


def _override_material_color(obj, prefix: str, srgb: list[float]):
    lin = _srgb(srgb)
    for mat in obj.data.materials:
        if mat and mat.name.startswith(prefix):
            bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf is not None:
                bsdf.inputs["Base Color"].default_value = (lin[0], lin[1], lin[2], 1.0)


def _transfer_weights_from_body(dst_obj, src_obj, rig, smooth_repeats: int = 3):
    """Transfer anatomical skinning weights from body mesh onto a fitted 3D garment, smoothed & normalized."""
    dst_obj.vertex_groups.clear()
    for vg in src_obj.vertex_groups:
        dst_obj.vertex_groups.new(name=vg.name)

    bpy.ops.object.select_all(action="DESELECT")
    dst_obj.select_set(True)
    bpy.context.view_layer.objects.active = dst_obj
    mod = dst_obj.modifiers.new(name="WeightTransfer", type="DATA_TRANSFER")
    mod.object = src_obj
    mod.use_vert_data = True
    mod.data_types_verts = {"VGROUP_WEIGHTS"}
    mod.vert_mapping = "POLYINTERP_NEAREST"
    bpy.ops.object.modifier_apply(modifier=mod.name)

    if smooth_repeats > 0:
        try:
            bpy.ops.object.vertex_group_smooth(group_select_mode="ALL", factor=0.5, repeat=smooth_repeats)
        except Exception:
            pass
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)

    dst_obj.parent = rig
    arm = dst_obj.modifiers.new(name="Armature", type="ARMATURE")
    arm.object = rig


def _ensure_outside_body(obj, body_bvh: BVHTree, min_clear: float = 0.008, iterations: int = 2):
    """Gently push any garment vertex that sits too close to underlying skin outward along its smooth normal."""
    me = obj.data
    me.update()
    for _ in range(iterations):
        moved = 0
        for v in me.vertices:
            loc, bnorm, _idx, _d = body_bvh.find_nearest(v.co)
            if loc is None or bnorm is None:
                continue
            signed = (v.co - loc).dot(bnorm)
            if signed < min_clear:
                # Only push outward if vertex is actually near the body surface (not deep hollow interior lining).
                if signed > -0.045:
                    v.co = loc + bnorm * min_clear
                    moved += 1
        if moved == 0:
            break
    me.update()


def _skin_jacket_cleanly(jacket_obj, human_obj, rig, sh_half_x: float, pelv_z: float):
    """Analytic sleeve-separated skinning for fitted 3D jackets: zero armpit/ribcage cross-grabbing!

    - Sleeve vertices outboard of the shoulder use exact analytical capsule weights along
      [clavicle -> upperarm/upperarm_twist_01 -> lowerarm/lowerarm_twist_01] so inner & outer
      sleeve walls deform cleanly as a solid tailored tube with zero accordion pinching.
    - Torso/collar/skirt vertices transfer cleanly from torso-only human vertices (ignoring arms!).
    """
    # 1. Transfer torso weights from a torso-only copy of human_obj (arms & hands stripped!) so chest/hip
    #    never accidentally grab forearm/hand/sleeve weights and sleeves never grab ribcage weights.
    torso_src = human_obj.copy()
    torso_src.data = human_obj.data.copy()
    bpy.context.collection.objects.link(torso_src)
    bm_t = bmesh.new()
    bm_t.from_mesh(torso_src.data)
    del_arm = [f for f in bm_t.faces if abs(f.calc_center_median().x) > sh_half_x * 1.05]
    if del_arm:
        bmesh.ops.delete(bm_t, geom=del_arm, context="FACES")
    bm_t.to_mesh(torso_src.data)
    bm_t.free()
    torso_src.data.update()

    _transfer_weights_from_body(jacket_obj, torso_src, rig, smooth_repeats=4)
    bpy.data.objects.remove(torso_src, do_unlink=True)

    # 2. Blend analytical arm/twist capsule weights smoothly onto left & right sleeves!
    me = jacket_obj.data
    vgs = {vg.name: vg for vg in jacket_obj.vertex_groups}
    for side, sgn in (("l", 1.0), ("r", -1.0)):
        b_ua = rig.data.bones[f"upperarm_{side}"]
        b_la = rig.data.bones[f"lowerarm_{side}"]
        b_ha = rig.data.bones[f"hand_{side}"]
        sh_p = b_ua.head_local.copy()
        el_p = b_la.head_local.copy()
        wr_p = b_ha.head_local.copy()
        v_ua = (el_p - sh_p).normalized()
        v_la = (wr_p - el_p).normalized()
        ua_len = (el_p - sh_p).length
        la_len = (wr_p - el_p).length

        vg_cl = vgs.get(f"clavicle_{side}") or jacket_obj.vertex_groups.new(name=f"clavicle_{side}")
        vg_ua = vgs.get(f"upperarm_{side}") or jacket_obj.vertex_groups.new(name=f"upperarm_{side}")
        vg_uat = vgs.get(f"upperarm_twist_01_{side}") or jacket_obj.vertex_groups.new(name=f"upperarm_twist_01_{side}")
        vg_la = vgs.get(f"lowerarm_{side}") or jacket_obj.vertex_groups.new(name=f"lowerarm_{side}")
        vg_lat = vgs.get(f"lowerarm_twist_01_{side}") or jacket_obj.vertex_groups.new(name=f"lowerarm_twist_01_{side}")

        for v in me.vertices:
            # Determine if vertex is in the sleeve/shoulder cap zone (smooth blend across shoulder seam).
            lat = v.co.x * sgn
            if lat < sh_half_x * 0.78 or v.co.z < pelv_z - 0.14:
                continue
            # Also exclude jacket skirt hem hanging beside thighs below armpit!
            rel_sh = v.co - sh_p
            # Distance from arm bone chain (upperarm + lowerarm segments).
            t1 = max(0.0, min(1.0, rel_sh.dot(v_ua) / max(ua_len, 1e-4)))
            p1 = sh_p + v_ua * (t1 * ua_len)
            d1 = (v.co - p1).length
            t2 = max(0.0, min(1.0, (v.co - el_p).dot(v_la) / max(la_len, 1e-4)))
            p2 = el_p + v_la * (t2 * la_len)
            d2 = (v.co - p2).length
            if min(d1, d2) > 0.135:
                continue

            arm_blend = max(0.0, min(1.0, (lat - sh_half_x * 0.78) / 0.085))
            arm_blend = arm_blend * arm_blend * (3.0 - 2.0 * arm_blend)
            if arm_blend <= 1e-3:
                continue

            # Compute exact analytical arm segment weight vector.
            w_cl, w_ua, w_uat, w_la, w_lat = 0.0, 0.0, 0.0, 0.0, 0.0
            if d1 <= d2 + 0.008 and t1 < 0.96:
                # Upperarm region: smooth transition from clavicle (deltoid seam) -> upperarm_twist -> upperarm -> elbow.
                if t1 < 0.25:
                    u = t1 / 0.25
                    w_cl = 0.45 * (1.0 - u)
                    w_uat = 0.55 + 0.35 * u
                    w_ua = 0.10 * u
                else:
                    u = max(0.0, min(1.0, (t1 - 0.08) / 0.68))
                    s = 1.0 - (u * u * (3.0 - 2.0 * u))
                    # Smooth blend into lowerarm near elbow (t1 > 0.80).
                    el_w = max(0.0, min(1.0, (t1 - 0.78) / 0.22)) * 0.50
                    w_la = el_w
                    rem = 1.0 - el_w
                    w_uat = rem * s
                    w_ua = rem * (1.0 - s)
            else:
                # Forearm region: smooth elbow blend -> lowerarm -> lowerarm_twist_01 near cuff!
                el_w = max(0.0, min(1.0, (0.20 - t2) / 0.20)) * 0.45
                w_ua = el_w
                rem = 1.0 - el_w
                u = max(0.0, min(1.0, (t2 - 0.15) / 0.78))
                s = u * u * (3.0 - 2.0 * u)
                w_lat = rem * s
                w_la = rem * (1.0 - s)

            # Scale existing torso weights by (1 - arm_blend) and mix in exact analytical arm weights.
            for g in list(v.groups):
                vg = jacket_obj.vertex_groups[g.group]
                vg.add([v.index], g.weight * (1.0 - arm_blend), "REPLACE")
            for vg, wv in ((vg_cl, w_cl), (vg_ua, w_ua), (vg_uat, w_uat), (vg_la, w_la), (vg_lat, w_lat)):
                if wv * arm_blend > 1e-4:
                    vg.add([v.index], wv * arm_blend, "ADD")

    bpy.ops.object.select_all(action="DESELECT")
    jacket_obj.select_set(True)
    bpy.context.view_layer.objects.active = jacket_obj
    try:
        bpy.ops.object.vertex_group_smooth(group_select_mode="ALL", factor=0.45, repeat=3)
    except Exception:
        pass
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)


def equip_styleb_jacket(
    human_obj,
    rig,
    jacket_glb: Path,
    main_rgb: list[float],
    accent_rgb: list[float],
    trim_rgb: list[float],
    trousers_obj=None,
):
    """Fit our Tripo H3.1 sculpted solarpunk jacket cleanly over body + trousers with aligned pre-bent sleeves."""
    obj = _import_single_glb(jacket_glb, "styleb_jacket")
    _override_material_color(obj, "EX_CLOTH_MAIN", main_rgb)
    _override_material_color(obj, "EX_CLOTH_ACCENT", accent_rgb)
    _override_material_color(obj, "EX_CLOTH_TRIM", trim_rgb)
    _override_material_color(obj, "EX_METAL_BRASS", [0.76, 0.64, 0.36])

    b_neck = rig.data.bones["neck_01"]
    b_pelv = rig.data.bones["pelvis"]
    b_ua_l = rig.data.bones["upperarm_l"]
    b_ua_r = rig.data.bones["upperarm_r"]
    b_la_l = rig.data.bones["lowerarm_l"]
    b_la_r = rig.data.bones["lowerarm_r"]
    b_ha_l = rig.data.bones["hand_l"]
    b_ha_r = rig.data.bones["hand_r"]

    sh_half_x = abs(b_ua_l.head_local.x)
    neck_z = b_neck.head_local.z
    pelv_z = b_pelv.head_local.z

    # Measure combined torso + trouser hip extents so the jacket clears female & male hips generously!
    ref_objs = [human_obj] + ([trousers_obj] if trousers_obj is not None else [])
    torso_verts = [
        v.co for ro in ref_objs for v in ro.data.vertices
        if pelv_z - 0.14 <= v.co.z <= neck_z - 0.02 and abs(v.co.x) < sh_half_x * 1.25
    ]
    hip_verts = [
        v.co for ro in ref_objs for v in ro.data.vertices
        if pelv_z - 0.22 <= v.co.z <= pelv_z + 0.06 and abs(v.co.x) < 0.32
    ]
    body_depth_y = max(v.y for v in torso_verts) - min(v.y for v in torso_verts)
    body_cy = 0.5 * (max(v.y for v in torso_verts) + min(v.y for v in torso_verts))
    hip_half_x = max(abs(v.x) for v in hip_verts) if hip_verts else sh_half_x
    hip_y_min = min(v.y for v in hip_verts) if hip_verts else -0.11
    hip_y_max = max(v.y for v in hip_verts) if hip_verts else 0.13

    j_vs = [v.co for v in obj.data.vertices]
    j_z0, j_z1 = min(v.z for v in j_vs), max(v.z for v in j_vs)
    j_h = j_z1 - j_z0
    j_core = [v for v in j_vs if abs(v.x) < 0.15 and 0.25 * j_h < (v.z - j_z0) < 0.80 * j_h]
    j_depth_y = max(v.y for v in j_core) - min(v.y for v in j_core)
    j_width_x = max(abs(v.x) for v in j_vs if 0.72 * j_h < (v.z - j_z0) < 0.84 * j_h) * 2.0

    target_z_top = neck_z + 0.055
    target_z_bot = pelv_z - 0.24
    target_h = target_z_top - target_z_bot
    sx = max(sh_half_x * 2.0 * 1.28, hip_half_x * 2.0 * 1.15) / max(j_width_x, 0.25)
    sy = (body_depth_y * 1.36) / max(j_depth_y, 0.16)
    sz = target_h / max(j_h, 0.30)

    obj.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    j_vs2 = [v.co for v in obj.data.vertices]
    j_z1_new = max(v.z for v in j_vs2)
    j_core2 = [v for v in j_vs2 if abs(v.x) < sh_half_x * 0.95 and v.z > target_z_bot + 0.15]
    j_cy_new = 0.5 * (max(v.y for v in j_core2) + min(v.y for v in j_core2)) if j_core2 else 0.0
    obj.location = Vector((0.0, body_cy - j_cy_new, target_z_top - j_z1_new))
    bpy.ops.object.transform_apply(location=True)

    # Smoothly flare lower jacket skirt around hip/glute contour (NO vertex-crushing on hollow walls!) so
    # trousers never poke through the coat skirt on either female or male morphologies.
    waist_z = pelv_z + 0.11
    for v in obj.data.vertices:
        if v.co.z >= waist_z or abs(v.co.x) > 0.28:
            continue
        t_skirt = min(1.0, (waist_z - v.co.z) / 0.13)
        s_skirt = t_skirt * t_skirt * (3.0 - 2.0 * t_skirt)
        # Check radial hip ellipse clearance (preserves outer+inner wall thickness rigidly with sleek tailored fit!).
        rx_req = hip_half_x + 0.014
        ry_back = abs(hip_y_max - body_cy) + 0.020
        ry_front = abs(body_cy - hip_y_min) + 0.016
        dx = v.co.x
        dy = v.co.y - body_cy
        ry_req = ry_back if dy > 0.0 else ry_front
        e = math.hypot(dx / max(rx_req, 0.10), dy / max(ry_req, 0.10))
        if e < 1.0 and e > 0.20:
            push = (1.0 / e - 1.0) * s_skirt
            v.co.x += dx * push
            v.co.y += dy * push

    # Bend the jacket's straight 45-deg A-pose sleeves smoothly onto MPFB2's exact pre-bent 42-deg elbows,
    # keeping inner & outer sleeve walls strictly intact (zero accordion crushing!).
    for side, b_ua, b_la, b_ha, sgn in (
        ("l", b_ua_l, b_la_l, b_ha_l, 1.0),
        ("r", b_ua_r, b_la_r, b_ha_r, -1.0),
    ):
        sh_p = b_ua.head_local.copy()
        el_p = b_la.head_local.copy()
        wr_p = b_ha.head_local.copy()
        v_ua = (el_p - sh_p).normalized()
        v_la = (wr_p - el_p).normalized()
        ua_len = (el_p - sh_p).length
        la_len = (wr_p - el_p).length

        sleeve_pts = [
            v.co for v in obj.data.vertices
            if (v.co.x * sgn) > (sh_half_x * 1.08) and v.co.z > pelv_z - 0.12
        ]
        if len(sleeve_pts) < 20:
            continue
        xs_s = sorted(p.x * sgn for p in sleeve_pts)
        x_cut = xs_s[int(len(xs_s) * 0.92)]
        cuff_pts = [p for p in sleeve_pts if p.x * sgn >= x_cut]
        cuff_c = sum(cuff_pts, Vector((0, 0, 0))) / float(len(cuff_pts))
        v_sl = (cuff_c - sh_p).normalized()
        sl_len = (cuff_c - sh_p).length

        q_ua_align = v_sl.rotation_difference(v_ua)
        q_el_bend = v_ua.rotation_difference(v_la)
        target_sl_len = ua_len + la_len * 0.85
        len_scale = target_sl_len / max(sl_len, 0.25)

        for v in obj.data.vertices:
            if v.co.x * sgn <= sh_half_x * 0.88 or v.co.z < pelv_z - 0.14:
                continue
            rel = v.co - sh_p
            t_along = rel.dot(v_sl)
            if t_along <= 0.0:
                continue
            # Exclude coat skirt edge below armpit.
            if (rel - v_sl * t_along).length > 0.14:
                continue
            lat_w = min(1.0, max(0.0, (v.co.x * sgn - sh_half_x * 0.88) / 0.075))
            lat_w = lat_w * lat_w * (3.0 - 2.0 * lat_w)

            radial = rel - v_sl * t_along
            t_scaled = t_along * (1.0 + (len_scale - 1.0) * lat_w)
            p_ua = sh_p + q_ua_align @ (v_sl * t_scaled + radial)

            if t_scaled > ua_len * 0.76:
                u_b = min(1.0, max(0.0, (t_scaled - ua_len * 0.76) / (ua_len * 0.44)))
                u_b = u_b * u_b * (3.0 - 2.0 * u_b)
                q_b = Quaternion((1.0, 0.0, 0.0, 0.0)).slerp(q_el_bend, u_b * lat_w)
                p_final = el_p + q_b @ (p_ua - el_p)
            else:
                p_final = p_ua
            v.co = v.co.lerp(p_final, lat_w)

    obj.data.update()
    _assign_metric_box_uvs(obj, tile_m=0.32)
    _skin_jacket_cleanly(obj, human_obj, rig, sh_half_x, pelv_z)
    return obj


def build_styleb_trousers(human_obj, rig, pants_rgb: list[float]):
    """Build clean tailored Style B woven slim trousers conforming to the lower body (excluding A-pose hands!)."""
    b_pelv = rig.data.bones["pelvis"]
    b_foot_l = rig.data.bones["foot_l"]
    # Stop trouser top cleanly inside the jacket skirt below the waist belt (zero rear-hip poke-through!).
    waist_z = b_pelv.head_local.z - 0.04
    ankle_z = b_foot_l.head_local.z + 0.03

    src_me = human_obj.data
    bm = bmesh.new()
    bm.from_mesh(src_me)
    bm.faces.ensure_lookup_table()
    # Strictly keep lower-body faces (|x| < 0.28 excludes hanging A-pose fingertips completely!).
    to_del = [
        f for f in bm.faces
        if f.calc_center_median().z > waist_z
        or f.calc_center_median().z < ankle_z
        or abs(f.calc_center_median().x) > 0.28
    ]
    if to_del:
        bmesh.ops.delete(bm, geom=to_del, context="FACES")

    # Gentle anatomical trouser tailoring: inflate +11mm over thighs/knees, taper cleanly at ankle (+5.5mm)
    # and tuck slightly inward at upper pelvis hidden inside the belted coat skirt.
    bm.normal_update()
    knee_z = rig.data.bones["calf_l"].head_local.z
    skirt_z = b_pelv.head_local.z - 0.16
    for v in bm.verts:
        z = v.co.z
        u_leg = max(0.0, min(1.0, (z - ankle_z) / max(waist_z - ankle_z, 0.20)))
        inflate = 0.0055 + 0.0060 * (u_leg ** 0.7)
        if abs(z - knee_z) < 0.16:
            inflate += 0.0025 * (1.0 - abs(z - knee_z) / 0.16)
        if z > skirt_z:
            t_in = min(1.0, (z - skirt_z) / max(waist_z - skirt_z, 0.06))
            inflate *= (1.0 - 0.75 * t_in)
        v.co += v.normal * inflate
        # Gently drop crotch seam slightly downward so upper inner thighs look tailored, not anatomical tights.
        if abs(v.co.x) < 0.055 and abs(z - (b_pelv.head_local.z - 0.11)) < 0.09:
            c_w = (1.0 - abs(v.co.x) / 0.055) * (1.0 - abs(z - (b_pelv.head_local.z - 0.11)) / 0.09)
            v.co.z -= 0.016 * c_w
            v.co.y -= 0.005 * c_w

    # Smooth 2 light passes to create clean tailored trouser cloth flow.
    bmesh.ops.smooth_vert(bm, verts=list(bm.verts), factor=0.35, use_axis_x=True, use_axis_y=True, use_axis_z=True)

    mesh = bpy.data.meshes.new("styleb_trousers")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    obj = bpy.data.objects.new("styleb_trousers", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(_make_pbr_mat("EX_CLOTH_PANTS_styleb", tuple(pants_rgb), roughness=0.84, metallic=0.0))
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()
    _assign_metric_box_uvs(obj, tile_m=0.30)
    _transfer_weights_from_body(obj, human_obj, rig, smooth_repeats=2)
    return obj


def equip_styleb_boots(human_obj, rig, boot_glb: Path):
    """Fit our Tripo H3.1 sculpted solarpunk boot to the right foot and mirror symmetrically for the left foot."""
    right_boot = _import_single_glb(boot_glb, "styleb_boot_r")
    _override_material_color(right_boot, "EX_LEATHER_MAIN", [0.46, 0.27, 0.16])
    _override_material_color(right_boot, "EX_RUBBER_SOLE", [0.18, 0.175, 0.17])
    _override_material_color(right_boot, "EX_CLOTH_TRIM", [0.80, 0.76, 0.66])
    _override_material_color(right_boot, "EX_LEATHER_ACCENT", [0.44, 0.47, 0.41])
    _override_material_color(right_boot, "EX_METAL_BRASS", [0.72, 0.60, 0.34])
    left_boot = right_boot.copy()
    left_boot.data = right_boot.data.copy()
    left_boot.name = "styleb_boot_l"
    bpy.context.collection.objects.link(left_boot)

    # Mirror left boot cleanly across X and flip face normals so winding stays outward!
    bpy.ops.object.select_all(action="DESELECT")
    left_boot.select_set(True)
    bpy.context.view_layer.objects.active = left_boot
    left_boot.scale = (-1.0, 1.0, 1.0)
    bpy.ops.object.transform_apply(scale=True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.mode_set(mode="OBJECT")

    out_boots = []
    for side, obj in (("r", right_boot), ("l", left_boot)):
        b_foot = rig.data.bones[f"foot_{side}"]
        b_ball = rig.data.bones[f"ball_{side}"]
        # Measure character's actual foot vertices on this side to match exact length & width.
        sgn = 1.0 if side == "l" else -1.0
        f_verts = [v.co for v in human_obj.data.vertices if v.co.z < b_foot.head_local.z + 0.04 and v.co.x * sgn > 0.01]
        if f_verts:
            f_y_min = min(v.y for v in f_verts)
            f_y_max = max(v.y for v in f_verts)
            f_x_mid = 0.5 * (min(v.x for v in f_verts) + max(v.x for v in f_verts))
            f_len = max(f_y_max - f_y_min, 0.22)
        else:
            f_len = 0.26
            f_y_min = b_ball.tail_local.y - 0.03
            f_y_max = b_foot.head_local.y + 0.055
            f_x_mid = b_foot.head_local.x

        # Current boot bounds (toe at y_min, heel at y_max, sole at z=0).
        b_vs = [v.co for v in obj.data.vertices]
        by0, by1 = min(v.y for v in b_vs), max(v.y for v in b_vs)
        bz0 = min(v.z for v in b_vs)
        b_len = max(by1 - by0, 0.20)
        # Scale boot slightly larger than bare foot (+11% for thick leather + lugged rubber sole).
        sc = (f_len * 1.11) / b_len

        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        obj.scale = (sc, sc, sc)
        bpy.ops.object.transform_apply(scale=True)

        b_vs2 = [v.co for v in obj.data.vertices]
        by0, by1 = min(v.y for v in b_vs2), max(v.y for v in b_vs2)
        bx_mid = 0.5 * (min(v.x for v in b_vs2) + max(v.x for v in b_vs2))
        bz0 = min(v.z for v in b_vs2)
        # Align boot ankle/heel to character's foot centerline and place sole at exact Z = 0!
        f_y_mid = 0.5 * (f_y_min + f_y_max)
        b_y_mid = 0.5 * (by0 + by1)
        obj.location = Vector((f_x_mid - bx_mid, f_y_mid - b_y_mid - 0.005, -bz0))
        bpy.ops.object.transform_apply(location=True)

        # Clean flexible boot skinning: heel/ankle/midsole on foot_{side}, smooth forefoot bend onto ball_{side},
        # and gentle top cuff transition onto calf_{side} so ankle flexes naturally without ripping.
        obj.vertex_groups.clear()
        vg_calf = obj.vertex_groups.new(name=f"calf_{side}")
        vg_foot = obj.vertex_groups.new(name=f"foot_{side}")
        vg_ball = obj.vertex_groups.new(name=f"ball_{side}")
        ball_y = b_ball.head_local.y
        ankle_z = b_foot.head_local.z
        for v in obj.data.vertices:
            if v.co.y < ball_y - 0.015:
                t_b = min(1.0, (ball_y - 0.015 - v.co.y) / 0.045)
                w_ball = t_b * t_b * (3.0 - 2.0 * t_b)
                vg_ball.add([v.index], w_ball, "REPLACE")
                if 1.0 - w_ball > 1e-4:
                    vg_foot.add([v.index], 1.0 - w_ball, "REPLACE")
            elif v.co.z > ankle_z + 0.035:
                t_c = min(0.55, (v.co.z - (ankle_z + 0.035)) / 0.11 * 0.55)
                vg_calf.add([v.index], t_c, "REPLACE")
                vg_foot.add([v.index], 1.0 - t_c, "REPLACE")
            else:
                vg_foot.add([v.index], 1.0, "REPLACE")

        obj.parent = rig
        arm = obj.modifiers.new(name="Armature", type="ARMATURE")
        arm.object = rig
        out_boots.append(obj)

    return out_boots


def equip_styleb_belt_and_satchel(
    rig,
    jacket_obj,
    satchel_glb: Path,
    with_satchel: bool = True,
    with_belt: bool = True,
):
    """Build a crisp 3D leather waist belt + brass buckle and optionally fit our Tripo satchel + crossbody strap."""
    out = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    j_bvh = BVHTree.FromObject(jacket_obj, depsgraph)
    b_pelv = rig.data.bones["pelvis"]
    b_sp1 = rig.data.bones["spine_01"]
    b_clav_l = rig.data.bones["clavicle_l"]
    waist_z = b_pelv.head_local.z + 0.085

    if with_belt:
        # Trace 40-point belt contour tightly around the jacket WAIST (handles wider male waists while ignoring sleeves!).
        sh_x_lim = abs(rig.data.bones["upperarm_l"].head_local.x) * 1.18
        ring_pts = []
        ctr = Vector((0.0, b_pelv.head_local.y, waist_z))
        for k in range(40):
            ang = (k / 40.0) * 2.0 * math.pi  # 0 = front (-Y)
            d = Vector((math.sin(ang), -math.cos(ang), 0.0))
            origin = ctr + d * 0.285
            hit_loc, hit_n, _i, _dist = j_bvh.ray_cast(origin, -d, 0.285)
            if hit_loc is not None and abs(hit_loc.x) < sh_x_lim and (hit_loc - ctr).length < 0.275:
                ring_pts.append(hit_loc + d * 0.005)
            else:
                ring_pts.append(ctr + d * 0.165)
        for _ in range(4):
            ring_pts = [
                (ring_pts[(k - 1) % 40] * 0.25 + ring_pts[k] * 0.50 + ring_pts[(k + 1) % 40] * 0.25)
                for k in range(40)
            ]

        bm = bmesh.new()
        half_h = 0.017
        thick = 0.007
        rings = []
        for k in range(40):
            p = ring_pts[k]
            out_d = (Vector((p.x, p.y, 0.0)) - Vector((ctr.x, ctr.y, 0.0))).normalized()
            v_ib = bm.verts.new(p + Vector((0, 0, -half_h)) - out_d * 0.002)
            v_ob = bm.verts.new(p + Vector((0, 0, -half_h)) + out_d * thick)
            v_ot = bm.verts.new(p + Vector((0, 0,  half_h)) + out_d * thick)
            v_it = bm.verts.new(p + Vector((0, 0,  half_h)) - out_d * 0.002)
            rings.append((v_ib, v_ob, v_ot, v_it))
        for k in range(40):
            k2 = (k + 1) % 40
            r0, r1 = rings[k], rings[k2]
            for j in range(4):
                j2 = (j + 1) % 4
                f = bm.faces.new((r0[j], r1[j], r1[j2], r0[j2]))
                f.smooth = True
                f.material_index = 0

        # Sculpted 3D matte-brass rectangular buckle frame centered on front waist (-Y)!
        p_front = ring_pts[0] + Vector((0.0, -thick - 0.003, 0.0))
        bw, bh, bd = 0.044, 0.044, 0.009
        bar = 0.007
        for cx, cz, sx, sz in (
            (0.0,  bh * 0.5 - bar * 0.5, bw, bar),
            (0.0, -bh * 0.5 + bar * 0.5, bw, bar),
            (-bw * 0.5 + bar * 0.5, 0.0, bar, bh),
            ( bw * 0.5 - bar * 0.5, 0.0, bar, bh),
            (0.0, 0.0, bar * 0.65, bh * 0.85),  # center tongue bar
        ):
            res = bmesh.ops.create_cube(bm, size=1.0)
            for v in res["verts"]:
                v.co = Vector((p_front.x + cx + v.co.x * sx, p_front.y + v.co.y * bd, p_front.z + cz + v.co.z * sz))
            for f in set(f for v in res["verts"] for f in v.link_faces):
                f.material_index = 1

        mesh = bpy.data.meshes.new("styleb_belt")
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        belt_obj = bpy.data.objects.new("styleb_belt", mesh)
        bpy.context.collection.objects.link(belt_obj)
        belt_obj.data.materials.append(_make_pbr_mat("EX_LEATHER_BAG_belt", (0.44, 0.24, 0.14), roughness=0.44, metallic=0.0))
        belt_obj.data.materials.append(_make_pbr_mat("EX_METAL_BRASS_belt", (0.74, 0.62, 0.35), roughness=0.28, metallic=0.88))
        _assign_metric_box_uvs(belt_obj, tile_m=0.20)
        # Clean smooth waist skinning (pelvis + spine_01).
        vg_p = belt_obj.vertex_groups.new(name="pelvis")
        vg_s = belt_obj.vertex_groups.new(name="spine_01")
        for v in belt_obj.data.vertices:
            vg_p.add([v.index], 0.55, "REPLACE")
            vg_s.add([v.index], 0.45, "REPLACE")
        belt_obj.parent = rig
        arm = belt_obj.modifiers.new(name="Armature", type="ARMATURE")
        arm.object = rig
        out.append(belt_obj)

    if with_satchel and satchel_glb.exists():
        sat = _import_single_glb(satchel_glb, "styleb_satchel")
        _override_material_color(sat, "EX_CLOTH_BAG", [0.64, 0.59, 0.43])
        _override_material_color(sat, "EX_LEATHER_BAG", [0.44, 0.24, 0.14])
        _override_material_color(sat, "EX_METAL_BRASS", [0.74, 0.62, 0.35])
        # Place satchel naturally on right-rear/side hip (-X side), angled along hip contour, outside jacket!
        hip_z = b_pelv.head_local.z - 0.14
        # Raycast right hip side of jacket to place satchel flush without penetration.
        hip_hit, _, _, _ = j_bvh.ray_cast(Vector((-0.55, 0.03, hip_z + 0.05)), Vector((1.0, 0.0, 0.0)), 0.55)
        hip_x = hip_hit.x if hip_hit is not None else -0.20
        sat_vs = [v.co for v in sat.data.vertices]
        sat_depth = max(v.y for v in sat_vs) - min(v.y for v in sat_vs)
        sat_h = max(v.z for v in sat_vs) - min(v.z for v in sat_vs)
        sat_w = max(v.x for v in sat_vs) - min(v.x for v in sat_vs)

        # Rotate satchel so its front pockets face outward (-X, slightly forward-outward) along the right hip!
        bpy.ops.object.select_all(action="DESELECT")
        sat.select_set(True)
        bpy.context.view_layer.objects.active = sat
        sat.rotation_mode = "XYZ"
        # Front (-Y) -> -X is -90 deg around Z; tilt slightly back (+12 deg) so it rests naturally at the hip!
        sat.rotation_euler = Euler((math.radians(6.0), math.radians(-8.0), math.radians(-78.0)), "XYZ")
        bpy.ops.object.transform_apply(rotation=True)
        sat_vs2 = [v.co for v in sat.data.vertices]
        sx_hi = max(v.x for v in sat_vs2)
        sz_mid = 0.5 * (min(v.z for v in sat_vs2) + max(v.z for v in sat_vs2))
        sy_mid = 0.5 * (min(v.y for v in sat_vs2) + max(v.y for v in sat_vs2))
        sat.location = Vector((hip_x - sx_hi - 0.012, 0.045 - sy_mid, hip_z - sz_mid))
        bpy.ops.object.transform_apply(location=True)

        # Rigid pelvis-dominant skinning so leather satchel never stretches like rubber!
        sat.vertex_groups.clear()
        vg_p = sat.vertex_groups.new(name="pelvis")
        vg_s = sat.vertex_groups.new(name="spine_01")
        for v in sat.data.vertices:
            vg_p.add([v.index], 0.85, "REPLACE")
            vg_s.add([v.index], 0.15, "REPLACE")
        sat.parent = rig
        arm = sat.modifiers.new(name="Armature", type="ARMATURE")
        arm.object = rig
        out.append(sat)

        # Build fitted crossbody leather strap hugging the exact jacket shoulder top & chest/back contour!
        sat_vs3 = [v.co for v in sat.data.vertices]
        sat_top_z = max(v.z for v in sat_vs3) - 0.025
        sat_cx = 0.5 * (min(v.x for v in sat_vs3) + max(v.x for v in sat_vs3))
        sat_y_lo, sat_y_hi = min(v.y for v in sat_vs3), max(v.y for v in sat_vs3)
        p_front_ring = Vector((sat_cx, sat_y_lo + 0.025, sat_top_z))
        p_back_ring = Vector((sat_cx, sat_y_hi - 0.025, sat_top_z))
        # Raycast straight down onto jacket's left shoulder crest so the strap sits flush (never floating!).
        sh_probe_x = b_clav_l.tail_local.x * 0.62
        sh_probe_y = b_clav_l.tail_local.y
        sh_hit, _, _, _ = j_bvh.ray_cast(Vector((sh_probe_x, sh_probe_y, b_clav_l.tail_local.z + 0.22)), Vector((0.0, 0.0, -1.0)), 0.35)
        sh_top = (sh_hit + Vector((0.0, 0.0, 0.005))) if sh_hit is not None else Vector((sh_probe_x, sh_probe_y, b_clav_l.tail_local.z + 0.03))

        strap_pts = []
        n_half = 16
        # Front run: satchel front D-ring -> across chest -> over left shoulder crest.
        for k in range(n_half + 1):
            t = k / float(n_half)
            p = p_front_ring.lerp(sh_top, t)
            if 0.08 < t < 0.94:
                spine_c = Vector((0.0, b_pelv.head_local.y, p.z))
                out_dir = Vector((p.x, min(p.y - spine_c.y, -0.05), 0.0)).normalized()
                hit, hit_n, _, _ = j_bvh.ray_cast(spine_c + out_dir * 0.28, -out_dir, 0.28)
                if hit is not None:
                    p = hit + (hit_n.normalized() if hit_n else out_dir) * 0.005
            strap_pts.append(p)
        # Back run: over left shoulder crest -> across back -> satchel rear D-ring.
        for k in range(1, n_half + 1):
            t = k / float(n_half)
            p = sh_top.lerp(p_back_ring, t)
            if 0.06 < t < 0.92:
                spine_c = Vector((0.0, b_pelv.head_local.y, p.z))
                out_dir = Vector((p.x, max(p.y - spine_c.y, 0.05), 0.0)).normalized()
                hit, hit_n, _, _ = j_bvh.ray_cast(spine_c + out_dir * 0.28, -out_dir, 0.28)
                if hit is not None:
                    p = hit + (hit_n.normalized() if hit_n else out_dir) * 0.005
            strap_pts.append(p)
        # Gentle 2-pass curve smooth (keep endpoints & shoulder crest fixed) for a sleek tailored leather strap.
        for _ in range(2):
            for k in range(1, len(strap_pts) - 1):
                if k == n_half:
                    continue
                strap_pts[k] = strap_pts[k - 1] * 0.25 + strap_pts[k] * 0.50 + strap_pts[k + 1] * 0.25
        # Final outward BVH projection after smoothing so the strap ALWAYS rides cleanly above lapels & collar!
        for k in range(1, len(strap_pts) - 1):
            p = strap_pts[k]
            loc, norm, _idx, dist = j_bvh.find_nearest(p)
            if loc is not None and norm is not None:
                # Use radial/upward fallback if nearest normal points inward on a double-walled fold.
                out_ref = Vector((0.0, 0.0, 1.0)) if abs(k - n_half) <= 1 else Vector((p.x, p.y - b_pelv.head_local.y, 0.15)).normalized()
                n_out = norm.normalized()
                if n_out.dot(out_ref) < 0.0:
                    n_out = out_ref
                signed = (p - loc).dot(n_out)
                if signed < 0.0085:
                    strap_pts[k] = loc + n_out * 0.0085

        # Extrude flat 2.8 cm wide x 5.5 mm thick smooth crossbody strap!
        bm = bmesh.new()
        w_half = 0.014
        t_thick = 0.0055
        n_s = len(strap_pts)
        s_rings = []
        for k in range(n_s):
            p = strap_pts[k]
            tan = (strap_pts[min(k + 1, n_s - 1)] - strap_pts[max(k - 1, 0)]).normalized()
            rad_v = Vector((p.x, p.y - b_pelv.head_local.y, 0.0))
            rad_v = rad_v.normalized() if rad_v.length > 1e-4 else Vector((0, -1, 0))
            w_up = math.exp(-((k - n_half) / 2.8) ** 2)
            out_v = (rad_v * (1.0 - w_up) + Vector((0.0, 0.0, 1.0)) * w_up).normalized()
            out_v = (out_v - tan * out_v.dot(tan))
            out_v = out_v.normalized() if out_v.length > 1e-4 else Vector((0, -1, 0))
            side_v = tan.cross(out_v).normalized()
            v0 = bm.verts.new(p - side_v * w_half)
            v1 = bm.verts.new(p + side_v * w_half)
            v2 = bm.verts.new(p + side_v * w_half + out_v * t_thick)
            v3 = bm.verts.new(p - side_v * w_half + out_v * t_thick)
            s_rings.append((v0, v1, v2, v3))
        for k in range(n_s - 1):
            r0, r1 = s_rings[k], s_rings[k + 1]
            for j in range(4):
                j2 = (j + 1) % 4
                f = bm.faces.new((r0[j], r1[j], r1[j2], r0[j2]))
                f.smooth = True
        smesh = bpy.data.meshes.new("styleb_satchel_strap")
        bm.to_mesh(smesh)
        bm.free()
        smesh.update()
        strap_obj = bpy.data.objects.new("styleb_satchel_strap", smesh)
        bpy.context.collection.objects.link(strap_obj)
        strap_obj.data.materials.append(_make_pbr_mat("EX_LEATHER_BAG_strap", (0.44, 0.24, 0.14), roughness=0.44, metallic=0.0))
        _assign_metric_box_uvs(strap_obj, tile_m=0.20)
        _transfer_weights_from_body(strap_obj, jacket_obj, rig, smooth_repeats=3)
        out.append(strap_obj)

    return out


def hide_covered_body_skin(human_obj, rig):
    """Delete shoulder, torso, upper/mid-arm, leg and foot faces on human_obj hidden under jacket, trousers & boots.

    Keeps head, neck cylinder, wrists and hands 100% intact while eliminating shoulder deltoid & distal forearm
    poke-through across all MoCap poses!
    """
    b_neck = rig.data.bones["neck_01"]
    b_ha_l = rig.data.bones["hand_l"]
    b_ha_r = rig.data.bones["hand_r"]
    b_la_l = rig.data.bones["lowerarm_l"]
    b_la_r = rig.data.bones["lowerarm_r"]

    neck_z = b_neck.head_local.z
    wr_l = b_ha_l.head_local
    wr_r = b_ha_r.head_local
    la_dir_l = (wr_l - b_la_l.head_local).normalized()
    la_dir_r = (wr_r - b_la_r.head_local).normalized()

    bm = bmesh.new()
    bm.from_mesh(human_obj.data)
    to_del = []
    for f in bm.faces:
        c = f.calc_center_median()
        # 1. Always keep entire head & upper neck above the collar top (z >= neck_z + 0.025).
        if c.z >= neck_z + 0.025:
            continue
        # 2. Keep inner front throat/neck inside collar opening (excludes trapezius, shoulder caps & back-collar poke!).
        if c.z >= neck_z - 0.035 and abs(c.x) < 0.058 and c.y < 0.032:
            continue
        # 3. Keep hands + 2.8 cm wrist tucked cleanly inside jacket sleeve cuffs (excludes outer forearm poke-through!).
        if (c - wr_l).dot(la_dir_l) > -0.028 and (c - wr_l).length < 0.22:
            continue
        if (c - wr_r).dot(la_dir_r) > -0.028 and (c - wr_r).length < 0.22:
            continue
        to_del.append(f)
    if to_del:
        bmesh.ops.delete(bm, geom=to_del, context="FACES")
    bm.to_mesh(human_obj.data)
    bm.free()
    human_obj.data.update()


def add_eyelid_blink_bones(rig, human_obj, eyes_obj, lashes_obj):
    """Add canonical `eyelid_upper_l` and `eyelid_upper_r` bones (59-bone rig) for natural runtime blinking."""
    if eyes_obj is None:
        return
    l_pts = [v.co for v in eyes_obj.data.vertices if v.co.x > 0.005]
    r_pts = [v.co for v in eyes_obj.data.vertices if v.co.x < -0.005]
    if not l_pts or not r_pts:
        return

    def _bbox_center(pts):
        return Vector((
            0.5 * (min(p.x for p in pts) + max(p.x for p in pts)),
            0.5 * (min(p.y for p in pts) + max(p.y for p in pts)),
            0.5 * (min(p.z for p in pts) + max(p.z for p in pts)),
        ))

    eye_c = {"l": _bbox_center(l_pts), "r": _bbox_center(r_pts)}

    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = rig.data.edit_bones
    head_b = eb["head"]
    for side in ("l", "r"):
        bname = f"eyelid_upper_{side}"
        if bname not in eb:
            b = eb.new(bname)
            b.parent = head_b
            b.use_connect = False
            b.head = eye_c[side].copy()
            b.tail = eye_c[side] + Vector((0.0, -0.025, 0.0))
            b.align_roll(Vector((0.0, 0.0, 1.0)))
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()

    # Assign smooth upper-eyelid weights on human skin and eyelashes (peak on upper lid margin, 0 at brow).
    for obj, is_lash in ((human_obj, False), (lashes_obj, True)):
        if obj is None:
            continue
        vg_head = obj.vertex_groups.get("head") or obj.vertex_groups.new(name="head")
        for side in ("l", "r"):
            ec = eye_c[side]
            vg_lid = obj.vertex_groups.get(f"eyelid_upper_{side}") or obj.vertex_groups.new(name=f"eyelid_upper_{side}")
            for v in obj.data.vertices:
                dx = v.co.x - ec.x
                dy = v.co.y - ec.y
                dz = v.co.z - ec.z
                # Upper eyelid zone sits right in front of the eyeball and above its horizontal midline.
                if abs(dx) > 0.020 or dy > 0.005 or dy < -0.026 or dz < -0.0015 or dz > 0.0175:
                    continue
                wx = max(0.0, 1.0 - (abs(dx) / 0.020) ** 2.2)
                if is_lash:
                    # Upper eyelashes rotate cleanly with the upper lid!
                    w = wx * (0.95 if dz > 0.0 else 0.0)
                else:
                    # Smooth vertical bell: strongest right along the lid rim (dz ~ +0.004), fading to 0 at brow crease.
                    if dz < 0.005:
                        wz = max(0.0, (dz + 0.0015) / 0.0065)
                    else:
                        wz = max(0.0, 1.0 - (dz - 0.005) / 0.0125)
                    w = 0.90 * wx * (wz * wz * (3.0 - 2.0 * wz))
                if w > 0.02:
                    vg_lid.add([v.index], w, "REPLACE")
                    vg_head.add([v.index], max(0.0, 1.0 - w), "REPLACE")
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
