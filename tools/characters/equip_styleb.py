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
from mathutils import Euler, Matrix, Quaternion, Vector, geometry, interpolate
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


def _fit_opening(cloth, body, a: Vector, b: Vector, t0: float, t1: float, t_end: float, ease: float, reach: float,
                 recentre: bool):
    """Close a garment's opening on the limb it ends around, along the bone from a towards the opening at b.

    From t0 metres along the bone, where nothing changes, to t1, where the change is whole, and on to t_end past the
    opening's edge, the cloth within `reach` of the bone moves, section by section (3 cm), onto the bone's axis when
    `recentre`, then narrows direction by direction until its inner surface lies `ease` outside the limb's own
    outline there. Cloth already closer keeps its place; every layer scales alike, so lining and outer cloth keep
    their order. A sleeve's own axis is the line through the centres of its full sections: its end is cut on the bias,
    and each slice of it holds only an arc. A generated cuff stood around a wrist at three times its radius and 5 cm
    off its axis: the hand came out of its side, over a dark gap.
    """
    axis = (b - a).normalized()
    u = axis.orthogonal().normalized()
    w = axis.cross(u)
    step, sectors = 0.03, 16
    n_bins = int(math.ceil((t_end - t0) / step)) + 1

    def split(p):
        t = (p - a).dot(axis)
        return t, (p - a) - axis * t

    def sector(r):
        return (math.atan2(r.dot(w), r.dot(u)) / (2.0 * math.pi) + 0.5) * sectors

    def bin_of(t):
        return min(n_bins - 1, max(0, int((t - t0) / step)))

    def whole(t):
        x = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
        return x * x * (3.0 - 2.0 * x)

    pts = [(v, *split(v.co)) for v in cloth.data.vertices]
    pts = [(v, t, r) for v, t, r in pts if t0 <= t <= t_end and r.length < reach]
    if not pts:
        return
    # The limb's outline: its skin's furthest reach in each section and direction.
    skin = np.zeros((n_bins, sectors))
    for bv in body.data.vertices:
        t, r = split(bv.co)
        if t0 <= t <= t_end and r.length < reach * 0.8:
            i, s = bin_of(t), int(sector(r)) % sectors
            skin[i, s] = max(skin[i, s], r.length)
    # The cloth's own axis: a line through the box centres of the sections whose cloth surrounds the limb.
    shift = lambda t: Vector((0.0, 0.0, 0.0))
    if recentre:
        rows = []
        for i in range(n_bins):
            sec = [(r.dot(u), r.dot(w)) for _v, t, r in pts if bin_of(t) == i]
            if len(sec) < 8 or skin[i].max() <= 0.0:
                continue
            us, ws = zip(*sec)
            if min(max(us) - min(us), max(ws) - min(ws)) > 2.5 * skin[i].max():
                rows.append((t0 + (i + 0.5) * step, (max(us) + min(us)) * 0.5, (max(ws) + min(ws)) * 0.5))
        if len(rows) >= 2:
            ts, cu, cw = (np.array(c) for c in zip(*rows))
            fu, fw = np.polyfit(ts, cu, 1), np.polyfit(ts, cw, 1)
            shift = lambda t: u * float(np.polyval(fu, t)) + w * float(np.polyval(fw, t))
    inner = np.full((n_bins, sectors), np.inf)
    for _v, t, r in pts:
        i = bin_of(t)
        rc = r - shift(t) * whole(t)
        s = int(sector(rc)) % sectors
        inner[i, s] = min(inner[i, s], rc.length)
    k = np.where(np.isfinite(inner) & (skin > 0.0), np.minimum(1.0, (skin + ease) / np.maximum(inner, 1e-6)), np.nan)
    for i in range(n_bins):  # a direction without cloth or skin there takes its section's middle
        known = ~np.isnan(k[i])
        k[i, ~known] = np.median(k[i, known]) if known.any() else 1.0
    for _ in range(2):
        k = (np.roll(k, 1, axis=1) + 2.0 * k + np.roll(k, -1, axis=1)) * 0.25
        k[1:-1] = (k[:-2] + 2.0 * k[1:-1] + k[2:]) * 0.25
    for v, t, r in pts:
        i, f = bin_of(t), whole(t)
        rc = r - shift(t) * f
        s = sector(rc) - 0.5
        s0 = math.floor(s)
        kk = k[i, s0 % sectors] * (1.0 - (s - s0)) + k[i, (s0 + 1) % sectors] * (s - s0)
        v.co = a + axis * t + rc * (1.0 + (kk - 1.0) * f)
    cloth.data.update()


def _skin_jacket_cleanly(jacket_obj, human_obj, rig, sh_half_x: float, pelv_z: float, sleeve_r: dict, slit: bool = False):
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

    # A skirt hangs from the pelvis and each thigh pushes its own side: its weights vary smoothly across and down, the
    # same for every layer at one place. Taken from the nearest skin, two neighbours on the front panel followed the
    # pelvis and a thigh, and the panel tore between them at every step. The thigh's share grows with the depth below
    # the hip joint, as the cloth's clearance shrinks against the thigh's travel there.
    me = jacket_obj.data
    vgs = {vg.name: vg for vg in jacket_obj.vertex_groups}
    hip_z = rig.data.bones["thigh_l"].head_local.z
    # A collar is sewn to the jacket: the trunk carries it and the neck turns inside it. A thigh moves the cloth only
    # through the skirt's smooth push below. From the nearest skin, a stand collar's rim took the jaw's weights and
    # cloth standing off the groin a thigh's; their neighbours followed the trunk, and the cloth tore between them as
    # the head turned and the leg swung.
    names = {vg.index: vg.name for vg in jacket_obj.vertex_groups}
    for v in me.vertices:
        for gi, w in [(g.group, g.weight) for g in v.groups]:  # copied: removing a weight invalidates the others
            name = names[gi]
            if name in ("head", "neck_01") or name.startswith("thigh_"):
                jacket_obj.vertex_groups[gi].remove([v.index])
                vgs["pelvis" if name.startswith("thigh_") else "spine_03"].add([v.index], w, "ADD")
    # A skirt slit up the front parts there: each panel's edge follows its own thigh.
    front_y = rig.data.bones["pelvis"].head_local.y
    for v in me.vertices:
        depth = hip_z - v.co.z
        if depth <= 0.0 or abs(v.co.x) > 0.32:
            continue
        push = 0.88 * (1.0 - math.exp(-depth / 0.07))
        half = 0.002 if slit and v.co.y < front_y else 0.04
        left = min(1.0, max(0.0, (v.co.x + half) / (2.0 * half)))
        left = left * left * (3.0 - 2.0 * left)
        join = min(1.0, depth / 0.05)
        join = join * join * (3.0 - 2.0 * join)
        for g in list(v.groups):
            jacket_obj.vertex_groups[g.group].add([v.index], g.weight * (1.0 - join), "REPLACE")
        for name, w in (("pelvis", 1.0 - push), ("thigh_l", push * left), ("thigh_r", push * (1.0 - left))):
            vgs[name].add([v.index], w * join, "ADD")

    # 2. Blend analytical arm/twist capsule weights smoothly onto left & right sleeves!
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
            # Beside the armpit the arm holds the cloth within the sleeve's own radius, and its hold fades over 4 cm beyond
            # it. Past mid-arm no flank is near, and it holds the whole sleeve, elbow bulge included. A fixed 13.5 cm
            # reach held the flank down to the lower ribs and let it go at once: the cloth tore along that line.
            past = min(1.0, max(0.0, (t1 - 0.35) / 0.35))
            reach = sleeve_r[side] + (0.135 - sleeve_r[side]) * past * past * (3.0 - 2.0 * past)
            beyond = min(1.0, max(0.0, min(d1 - reach, d2 - 0.135) / 0.04))
            arm_blend = max(0.0, min(1.0, (lat - sh_half_x * 0.78) / 0.085))
            arm_blend = arm_blend * arm_blend * (3.0 - 2.0 * arm_blend) * (1.0 - beyond * beyond * (3.0 - 2.0 * beyond))
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

    j_vs = [v.co for v in obj.data.vertices]
    j_z0, j_z1 = min(v.z for v in j_vs), max(v.z for v in j_vs)
    j_h = j_z1 - j_z0
    j_core = [v for v in j_vs if abs(v.x) < 0.15 and 0.25 * j_h < (v.z - j_z0) < 0.80 * j_h]
    j_depth_y = max(v.y for v in j_core) - min(v.y for v in j_core)
    j_width_x = max(abs(v.x) for v in j_vs if 0.72 * j_h < (v.z - j_z0) < 0.84 * j_h) * 2.0

    # A stand collar rises over the lower part of the neck, and the head stands clear of it. Set at a fixed 5.5 cm over
    # the neck's base, it reached the jaw of the shorter female necks: no neck showed, and the head sank into the coat.
    neck_len = (rig.data.bones["head"].head_local - b_neck.head_local).length
    target_z_top = neck_z + 0.40 * neck_len
    print(f"[equip_styleb] collar top {0.40 * neck_len * 100:.1f} cm over the neck's base ({neck_len * 100:.1f} cm neck)")
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

    # One cut serves every morphology. A garment's ease in front is its own: the one it has where it sits closest,
    # at the waist. Where its chest stands further off the wearer's than that, the front's depth scales back to it,
    # every layer alike. The deepest point across the chest sets each height's depth: cloth bridges the hollow
    # between two breasts. A fixed ease instead dents the chest of a loose cut above its own waist.
    z_lo, z_hi, step = pelv_z + 0.06, neck_z - 0.06, 0.02
    n_bins = max(8, math.ceil((z_hi - z_lo) / step))
    body_front, cloth_front = np.zeros(n_bins), np.zeros(n_bins)
    for src, front in ((human_obj, body_front), (obj, cloth_front)):
        for v in src.data.vertices:
            i = int((v.co.z - z_lo) / step)
            if 0 <= i < n_bins and abs(v.co.x) < sh_half_x * 0.80:
                front[i] = max(front[i], body_cy - v.co.y)
    closest = max(0.015, float(np.percentile((cloth_front - body_front)[2:-2], 10)))
    depth = np.minimum(1.0, (body_front + closest + 0.008) / np.maximum(cloth_front, 1e-3))
    for _ in range(2):
        depth[1:-1] = (depth[:-2] + 2.0 * depth[1:-1] + depth[2:]) * 0.25
    for v in obj.data.vertices:
        f = (v.co.z - z_lo) / step - 0.5
        if f < 0.0 or f > n_bins - 1.0 or v.co.y >= body_cy:
            continue
        i = min(int(f), n_bins - 2)
        k = depth[i] + (depth[i + 1] - depth[i]) * (f - i)
        # Full across the chest; none at the armholes, nor at the band's two ends.
        w = min(1.0, max(0.0, (sh_half_x * 0.95 - abs(v.co.x)) / (sh_half_x * 0.35)))
        w *= min(1.0, f / 3.0, (n_bins - 1.0 - f) / 3.0)
        v.co.y = body_cy + (v.co.y - body_cy) * (1.0 + (k - 1.0) * w)

    # Flare the skirt over the hips and trousers so neither pokes through, on female and male morphologies. The
    # clearance is the wearer's own outline, measured in each direction and at each height, plus a margin: hips are
    # squarer than an ellipse through their extremes, which let the seat through the back of the skirt. Cloth inside
    # the clearance moves towards it and keeps a quarter of its depth: the layers keep their order. Pushed all the way
    # onto it, the lining and the wrapped front panel folded through the outer cloth.
    waist_z = pelv_z + 0.11
    n_az, z_step, margin = 36, 0.03, 0.015
    n_z = math.ceil((waist_z - (pelv_z - 0.27)) / z_step)

    def polar(co):
        dy = co.y - body_cy
        return (math.hypot(co.x, dy), (math.atan2(dy, co.x) / (2.0 * math.pi) + 0.5) * n_az - 0.5,
                (waist_z - co.z) / z_step - 0.5)

    outline = np.zeros((n_az, n_z))
    for ro in ref_objs:
        for v in ro.data.vertices:
            if abs(v.co.x) < 0.32 and waist_z - n_z * z_step <= v.co.z < waist_z:
                r, az, zi = polar(v.co)
                cell = (int(round(az)) % n_az, min(n_z - 1, max(0, int(round(zi)))))
                outline[cell] = max(outline[cell], r)
    # A direction without a sample takes its neighbours'; each takes the widest of its three, then one pass rounds it.
    for _ in range(2):
        outline = np.maximum(outline, np.maximum(np.roll(outline, 1, axis=0), np.roll(outline, -1, axis=0)))
    outline = (np.roll(outline, 1, axis=0) + 2.0 * outline + np.roll(outline, -1, axis=0)) * 0.25 + margin
    for v in obj.data.vertices:
        if v.co.z >= waist_z or abs(v.co.x) > 0.28:
            continue
        r, az, zi = polar(v.co)
        a0, zc = math.floor(az), min(n_z - 1.0, max(0.0, zi))
        z0 = min(n_z - 2, int(zc))
        fa, fz = az - a0, zc - z0
        clear = ((outline[a0 % n_az, z0] * (1.0 - fa) + outline[(a0 + 1) % n_az, z0] * fa) * (1.0 - fz)
                 + (outline[a0 % n_az, z0 + 1] * (1.0 - fa) + outline[(a0 + 1) % n_az, z0 + 1] * fa) * fz)
        e = r / clear
        if 0.20 < e < 1.0:
            t_skirt = min(1.0, (waist_z - v.co.z) / 0.13)
            k = 1.0 + ((1.0 - (1.0 - e) * 0.25) / e - 1.0) * t_skirt * t_skirt * (3.0 - 2.0 * t_skirt)
            v.co.x *= k
            v.co.y = body_cy + (v.co.y - body_cy) * k

    # Bend the jacket's straight 45-deg A-pose sleeves smoothly onto MPFB2's exact pre-bent 42-deg elbows,
    # keeping inner & outer sleeve walls strictly intact (zero accordion crushing!).
    sleeve_r = {"l": 0.09, "r": 0.09}  # each sleeve's own radius, measured below
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

    # Raise the armhole. The generated jacket carries a low web of cloth from its flank to its sleeve, cut for raised
    # arms: with the arm down it has nowhere to go, and tears between the two (edges stretched nine times). Under the
    # arm, the cloth gathers within the sleeve's own tube, close to the arm: a set-in sleeve, flat on its underside.
    # Gathered onto the tube's full radius, the web's folds stood out as teeth between the hanging arm and the flank.
    for side, b_ua, b_la, sgn in (("l", b_ua_l, b_la_l, 1.0), ("r", b_ua_r, b_la_r, -1.0)):
        sh_p = b_ua.head_local.copy()
        ua_len = (b_la.head_local - sh_p).length
        v_ua = (b_la.head_local - sh_p) / ua_len
        arm_down = (Vector((0.0, 0.0, -1.0)) + v_ua * v_ua.z).normalized()  # down, square to the upper arm
        tube = sorted(
            r for r in (
                (v.co - sh_p - v_ua * (v.co - sh_p).dot(v_ua)).length for v in obj.data.vertices
                if v.co.x * sgn > sh_half_x and 0.55 * ua_len < (v.co - sh_p).dot(v_ua) < 0.90 * ua_len
            ) if r < 0.14
        )
        if tube:
            sleeve_r[side] = tube[len(tube) // 2] * 1.15
            r_in = tube[len(tube) // 2] * 0.70
            for v in obj.data.vertices:
                rel = v.co - sh_p
                along = rel.dot(v_ua)
                radial = rel - v_ua * along
                r = radial.length
                if not 0.0 < along < ua_len or r <= r_in:
                    continue
                w = min(1.0, max(0.0, (v.co.x * sgn - sh_half_x) / 0.03))
                w *= min(1.0, max(0.0, ((radial / r).dot(arm_down) - 0.2) / 0.3))
                w *= min(1.0, (ua_len - along) / (0.25 * ua_len))  # the elbow keeps its whole tube
                # Left as gathered: relaxing these vertices between their fixed neighbours drags the web back
                # through the sleeve and opens slits along it.
                v.co -= radial * ((r - r_in) / r) * (w * w * (3.0 - 2.0 * w))

    # Openings close on the limb they end around: each cuff on its wrist, over the forearm's last half, and the collar
    # on the neck from just below its base.
    for side in "lr":
        el, wr = rig.data.bones[f"lowerarm_{side}"].head_local, rig.data.bones[f"hand_{side}"].head_local
        la = (wr - el).length
        _fit_opening(obj, human_obj, el, wr, 0.40 * la, 0.85 * la, la + 0.04, ease=0.012, reach=0.12, recentre=True)
    n0, n1 = b_neck.head_local, rig.data.bones["head"].head_local
    _fit_opening(obj, human_obj, n0, n1, -0.03, 0.02, (n1 - n0).length, ease=0.010, reach=0.11, recentre=False)

    obj.data.update()
    _assign_metric_box_uvs(obj, tile_m=0.32)
    _skin_jacket_cleanly(obj, human_obj, rig, sh_half_x, pelv_z, sleeve_r)
    return obj


def _hull_radii(radii: np.ndarray) -> np.ndarray:
    """Push a ring's radii, at evenly spaced angles, out onto the ring's convex hull: cloth spans the hollows."""
    n = len(radii)
    ang = np.arange(n) * 2.0 * math.pi / n
    pts = [(float(r * math.cos(a)), float(r * math.sin(a))) for r, a in zip(radii, ang)]
    hull = [pts[i] for i in geometry.convex_hull_2d(pts)]
    out = radii.copy()
    for k, a in enumerate(ang):
        dx, dy = math.cos(a), math.sin(a)
        for (x0, y0), (x1, y1) in zip(hull, hull[1:] + hull[:1]):
            ex, ey = x1 - x0, y1 - y0
            den = dx * ey - dy * ex
            if abs(den) < 1e-12:
                continue
            t, s = (x0 * ey - y0 * ex) / den, (x0 * dy - y0 * dx) / den
            if t > 0.0 and -1e-6 <= s <= 1.0 + 1e-6:
                out[k] = max(out[k], t)
    return out


def _ring_outline(points: np.ndarray, centre: np.ndarray, u: np.ndarray, w: np.ndarray, sectors: int) -> np.ndarray:
    """Furthest reach of points around a centre, per angular sector of the plane (u, w); 0 where none."""
    rel = points - centre
    x, y = rel @ u, rel @ w
    s = ((np.arctan2(y, x) / (2.0 * math.pi) + 1.0) % 1.0 * sectors).astype(int) % sectors
    out = np.zeros(sectors)
    np.maximum.at(out, s, np.hypot(x, y))
    return out


def _close_ring(r: np.ndarray) -> np.ndarray:
    """Fill a ring's empty sectors from their nearest filled neighbours, around the ring."""
    have = np.flatnonzero(r > 0.0)
    if len(have) == 0:
        return r
    out = r.copy()
    n = len(r)
    for k in np.flatnonzero(r <= 0.0):
        d = np.minimum((have - k) % n, (k - have) % n)
        out[k] = r[have[np.argmin(d)]]
    return out


def _dome(bm, c: np.ndarray, n: np.ndarray, radius: float, height: float, segs: int = 12) -> list:
    """A domed stud on c, facing n: a rim, a shoulder and a crown, wound to face n."""
    t1 = np.cross(n, [0.0, 0.0, 1.0] if abs(n[2]) < 0.9 else [1.0, 0.0, 0.0])
    t1 /= np.linalg.norm(t1)
    t2 = np.cross(n, t1)
    a = np.arange(segs) * 2.0 * math.pi / segs

    def ring(r, h):
        return [bm.verts.new(tuple(c + (t1 * math.cos(x) + t2 * math.sin(x)) * r + n * h)) for x in a]

    rim, mid, top = ring(radius, 0.0), ring(0.65 * radius, 0.7 * height), bm.verts.new(tuple(c + n * height))
    faces = [bm.faces.new((rim[i], rim[(i + 1) % segs], mid[(i + 1) % segs], mid[i])) for i in range(segs)]
    return faces + [bm.faces.new((mid[i], mid[(i + 1) % segs], top)) for i in range(segs)]


def build_styleb_coat(human_obj, rig, main_rgb: list[float], accent_rgb: list[float], trim_rgb: list[float], trousers_obj=None):
    """Build a Style B coat on the wearer's own body: a tailored shell, fitted by construction.

    A stylized game models its clothes on the body as clean shapes. A torso tube runs from the hem to the stand collar,
    each ring the body's own outline plus the cut's ease, bridging its hollows; below the hip line the skirt flares
    over the legs and opens in front. Each sleeve is a tube along its arm, ending in a cuff band around the wrist. The
    wrap's V, its piping, the collar and the cuffs are colour zones on that one surface. A generated coat stood off
    the body with its own lumps: nothing seemed to lie under it, and every opening had to be refitted.
    """
    bones = rig.data.bones
    n0, h0 = bones["neck_01"].head_local, bones["head"].head_local
    pelv_z = bones["pelvis"].head_local.z
    hip_z = bones["thigh_l"].head_local.z
    sh_half_x = abs(bones["upperarm_l"].head_local.x)
    z_top = n0.z + 0.40 * (h0 - n0).length  # a stand collar over the neck's lower part
    z_hem = hip_z - 0.27
    belt_z = pelv_z + 0.08
    S, step = 48, 0.012
    v_top, piping, collar_open = 0.070, 0.009, 0.026  # the wrap's V at the collar, its piping, the collar's front gap

    me = human_obj.data
    P = np.array([v.co[:] for v in me.vertices])
    names = {g.index: g.name for g in human_obj.vertex_groups}
    arm_prefix = ("upperarm", "lowerarm", "hand", "thumb", "index", "middle", "ring", "pinky")
    armw = np.array([sum(g.weight for g in v.groups if names[g.group].startswith(arm_prefix)) for v in me.vertices])
    headw = np.array([sum(g.weight for g in v.groups if names[g.group] == "head") for v in me.vertices])
    # Above the armpit the coat's body covers the shoulder's cap as well, the deltoid included: a set-in sleeve hangs
    # from it. Left to the sleeve alone, the cap stood out in front of the shoulder as a knob.
    joints = [np.array(bones[f"upperarm_{sd}"].head_local) for sd in "lr"]
    cap = np.zeros(len(P), dtype=bool)
    for j in joints:
        cap |= (np.linalg.norm(P - j, axis=1) < 0.10) & (P[:, 2] > j[2] - 0.03)
    trunk = P[((armw < 0.3) | cap) & (headw < 0.5)]
    if trousers_obj is not None:
        T = np.array([v.co[:] for v in trousers_obj.data.vertices])
        trunk = np.vstack([trunk, T[T[:, 2] < hip_z]])

    # Torso tube, top to bottom.
    zs = np.arange(z_top, z_hem - 1e-6, -step)
    X, Y = np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0])
    rings, centres = [], []
    for z in zs:
        sl = trunk[np.abs(trunk[:, 2] - z) < step * 0.75]
        cy = 0.5 * (sl[:, 1].max() + sl[:, 1].min()) if len(sl) else (centres[-1][1] if centres else 0.0)
        if z < hip_z and centres:
            cy = centres[-1][1]  # a skirt hangs straight down from the hips, about their centre
        c = np.array([0.0, cy, z])
        out = _close_ring(_ring_outline(sl, c, X, Y, S)) if len(sl) else rings[-1] - 0.0
        ease = 0.010 if z > n0.z else 0.012
        x = min(1.0, max(0.0, (hip_z - z) / (hip_z - z_hem)))
        rings.append(_hull_radii(out + ease + 0.05 * x * x * (3.0 - 2.0 * x)))
        centres.append(c)
    R = np.array(rings)
    floor = R.copy()
    for _ in range(3):  # tailored: no ring stands apart from its neighbours, never inside the body's own outline
        R[1:-1] = (R[:-2] + 2.0 * R[1:-1] + R[2:]) * 0.25
        R = np.maximum(R, floor - 0.004)
    # The shoulders' cloth is pressed smooth: over the cap, a ring and its neighbours, along and around, agree.
    upper = zs > min(j[2] for j in joints) - 0.06
    for _ in range(4):
        R[upper] = (np.roll(R[upper], 1, axis=1) + 2.0 * R[upper] + np.roll(R[upper], -1, axis=1)) * 0.25
        R[1:-1][upper[1:-1]] = ((R[:-2] + 2.0 * R[1:-1] + R[2:]) * 0.25)[upper[1:-1]]
        R = np.maximum(R, floor - 0.004)
    # A skirt hangs from the hips: below them each direction keeps the widest reach above it, and falls smooth. Cut
    # to each height's own outline, its front stepped in and out over the trousers by up to 1.5 cm from one ring to
    # the next, and the thigh's swing folded those steps into creases along the slit at every stride.
    skirt = np.flatnonzero(zs < hip_z)
    for i in skirt:
        R[i] = np.maximum(R[i], R[i - 1])
    hang = R.copy()
    for _ in range(6):
        R[skirt] = (R[skirt - 1] + 2.0 * R[skirt] + R[np.minimum(skirt + 1, len(zs) - 1)]) * 0.25
        R = np.maximum(R, hang - 0.002)
    cyz = np.array([c[1] for c in centres])
    for _ in range(3):
        cyz[1:-1] = (cyz[:-2] + 2.0 * cyz[1:-1] + cyz[2:]) * 0.25
    # Cloth that hangs free folds. The flared skirt falls in eight soft flutes, deepening to its hem and flat along its
    # opening; above the belt the body blouses over it. A tube cut to the body's outline read as a moulded shell.
    ang = np.arange(S) * 2.0 * math.pi / S
    off_front = np.abs((ang - 0.5 * math.pi) % (2.0 * math.pi) - math.pi)  # angle from the front, -Y
    flute = (0.5 - 0.5 * np.cos(8.0 * (ang - 1.5 * math.pi))) * np.clip((off_front - 0.15) / 0.35, 0.0, 1.0)
    for i, z in enumerate(zs):
        x = min(1.0, max(0.0, (hip_z - z) / (hip_z - z_hem)))
        R[i] += 0.012 * x ** 1.5 * flute
        if belt_z < z < belt_z + 0.09:
            R[i] += 0.006 * math.sin(math.pi * (z - belt_z) / 0.09) ** 2

    bm = bmesh.new()
    zone = bm.faces.layers.int.new("zone")  # 0 main, 1 accent, 2 trim, 3 brass
    z_yoke = min(j[2] for j in joints) - 0.03  # the shoulder yoke's lower edge, just under the shoulder joints
    seams = {int(round(((a0 / 360.0) % 1.0) * S)) % S for a0 in (270 - 38, 270 + 38, 90 - 38, 90 + 38, 90)}
    Rs = R.copy()
    for k in seams:
        Rs[zs < z_yoke, k] -= 0.0015  # a seam reads as a fine groove in the cloth, from the yoke to the hem
    grid = [[bm.verts.new((float(Rs[i, k] * math.cos(a)), float(cyz[i] + Rs[i, k] * math.sin(a)), float(zs[i])))
             for k, a in enumerate(ang)] for i in range(len(zs))]
    front = int(round(S * 0.75)) % S  # the sector facing -Y
    for i in range(len(zs) - 1):
        for k in range(S):
            k2 = (k + 1) % S
            bm.faces.new((grid[i][k], grid[i][k2], grid[i + 1][k2], grid[i + 1][k]))
    # Below the belt the skirt is slit up the front: its two panels meet at rest and part with the stride. Cut open by
    # two sectors, it showed the dark inside of the coat between the legs.
    slit = [bm.edges.get((grid[i][front], grid[i + 1][front])) for i in range(len(zs) - 1) if zs[i] < belt_z]
    bmesh.ops.split_edges(bm, edges=slit)
    for v in bm.verts:  # each panel's edge stands 2 mm its own side of the slit, where its own thigh carries it
        xs = [f.calc_center_median().x for f in v.link_faces]
        if abs(v.co.x) < 1e-5 and v.co.z < belt_z and v.co.y < float(np.interp(v.co.z, zs[::-1], cyz[::-1])) and xs:
            if min(xs) > 0.0 or max(xs) < 0.0:
                v.co.x = math.copysign(0.002, xs[0])

    def front_faces(z0, z1):
        return [f for f in bm.faces if z0 < f.calc_center_median().z < z1 and abs(f.calc_center_median().x) < 0.12
                and f.calc_center_median().y < float(np.interp(f.calc_center_median().z, zs[::-1], cyz[::-1])) - 0.02]

    def cut(faces, co, no):
        verts = {v for f in faces for v in f.verts}
        edges = {e for f in faces for e in f.edges}
        bmesh.ops.bisect_plane(bm, geom=list(verts) + list(edges) + faces, dist=1e-5, plane_co=co, plane_no=no)

    # The stand collar opens in front over the wrap's V, between straight edges. Faces dropped whole left a stair.
    for co, no in (((collar_open, 0.0, 0.0), (1.0, 0.0, 0.0)), ((-collar_open, 0.0, 0.0), (1.0, 0.0, 0.0)),
                   ((0.0, 0.0, n0.z), (0.0, 0.0, 1.0))):
        cut(front_faces(n0.z - step, z_top + 1.0), Vector(co), Vector(no))
    bmesh.ops.delete(bm, geom=[f for f in front_faces(n0.z, z_top + 1.0) if abs(f.calc_center_median().x) < collar_open],
                     context="FACES")

    # The wrap's V and its piping are cut into the cloth along straight lines, from the collar's base to the belt.
    def v_half(z):
        return v_top * min(1.0, max(0.0, (z - belt_z) / (n0.z - belt_z)))

    y_front = float(cyz[int(np.argmin(np.abs(zs - belt_z)))]) - 0.2
    for sgn in (-1.0, 1.0):
        for off in (0.0, piping):
            top = Vector((sgn * (v_top + off), y_front, n0.z))
            bot = Vector((sgn * off, y_front, belt_z))
            cut(front_faces(belt_z - 0.02, n0.z + 0.02), bot, (top - bot).cross(Vector((0.0, 1.0, 0.0))).normalized())
    for zc in (z_yoke, z_yoke - piping):
        geom = list(bm.faces)
        bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + geom, dist=1e-5,
                               plane_co=Vector((0.0, 0.0, zc)), plane_no=Vector((0.0, 0.0, 1.0)))

    # Each armhole is cut upright through the shoulder joint: the body keeps the yoke over the shoulder's inner half,
    # and the sleeve is set into the opening. Laid over or under the body's cap instead, the sleeve met it almost
    # tangent over the deltoid and broke through it in ragged patches. Leaning in below, the cut ran on down the flank.
    holes = {}
    for side, sgn in (("l", 1.0), ("r", -1.0)):
        j = Vector(bones[f"upperarm_{side}"].head_local)
        pno = Vector((sgn, 0.0, 0.0))
        cut([f for f in bm.faces if (f.calc_center_median() - j).length < 0.16], j, pno)

        def on_plane(v):
            return abs((v.co - j).dot(pno)) < 1e-4

        seed = min(bm.faces, key=lambda f: (f.calc_center_median() - (j + Vector((sgn * 0.035, 0.0, 0.035)))).length)
        region, stack = {seed}, [seed]
        while stack:
            for e in stack.pop().edges:
                if all(on_plane(v) for v in e.verts):
                    continue
                for g in e.link_faces:
                    if g not in region and (g.calc_center_median() - j).dot(pno) > 0.0 and (g.calc_center_median() - j).length < 0.13:
                        region.add(g)
                        stack.append(g)
        bmesh.ops.delete(bm, geom=list(region), context="FACES")
        holes[side] = [e for e in bm.edges if e.is_boundary and all(on_plane(v) and (v.co - j).length < 0.16 for v in e.verts)]
        print(f"[equip_styleb] armhole {side}: {len(region)} faces cut, rim {len(holes[side])} edges")
    gap = math.radians(360.0 / S)  # one sector
    for f in bm.faces:
        c = f.calc_center_median()
        cyc = float(np.interp(c.z, zs[::-1], cyz[::-1]))
        in_front = c.y < cyc - 0.02
        a = math.atan2(c.y - cyc, c.x)
        if c.z > n0.z - 0.004:
            f[zone] = 1  # the stand collar
        elif in_front and c.z > belt_z and abs(c.x) < v_half(c.z):
            f[zone] = 1  # the wrap's inner panel, in its V
        elif in_front and c.z > belt_z and abs(c.x) < v_half(c.z) + piping:
            f[zone] = 2  # its piping
        elif c.z > z_yoke:
            f[zone] = 1  # the shoulder yoke
        elif c.z > z_yoke - piping:
            f[zone] = 2  # its piping
        elif c.z < z_hem + 0.012:
            f[zone] = 2  # the hem's piping
        elif c.z < belt_z and abs(a + 0.5 * math.pi) < 3.0 * gap and in_front:
            f[zone] = 1  # the facing along the slit, three sectors each side, its edge halfway between two
        else:
            f[zone] = 0

    patches = []  # cloth and studs sewn on the coat
    # Flap pockets on the skirt, each side of the front: a 12 cm patch of cloth, its lower edge piped, 9 mm proud: once
    # thickened it stands 5 mm clear of the panel.
    for sgn in (-1.0, 1.0):
        a0 = -0.5 * math.pi + sgn * math.radians(52.0)
        zr = np.linspace(hip_z - 0.095, hip_z - 0.045, 5)  # a row per ring: it bends as the panel under it does
        r_mid = float(np.interp(hip_z - 0.07, zs[::-1], R[::-1, int(round(a0 / (2 * math.pi) * S)) % S]))
        half = 0.06 / r_mid
        aa = np.linspace(a0 - half, a0 + half, 9)
        pv = []
        for z in zr:
            row = []
            cyv = float(np.interp(z, zs[::-1], cyz[::-1]))
            for a in aa:
                kf = (a / (2 * math.pi) % 1.0) * S
                k0 = int(math.floor(kf)) % S
                t = kf - math.floor(kf)
                rk = [float(np.interp(z, zs[::-1], R[::-1, kk])) for kk in (k0, (k0 + 1) % S)]
                r = rk[0] * (1.0 - t) + rk[1] * t + 0.009
                row.append(bm.verts.new((r * math.cos(a), cyv + r * math.sin(a), z)))
            pv.append(row)
        patches += [v for row in pv for v in row]
        for i in range(len(zr) - 1):
            for j in range(len(aa) - 1):
                f = bm.faces.new((pv[i][j], pv[i][j + 1], pv[i + 1][j + 1], pv[i + 1][j]))
                f[zone] = 2 if i == 0 else 1

    # Sleeves: each set into its armhole. Its head is lofted on the shoulder's own sections, from the armhole's rim to
    # the first section of the arm clear of it; a tube then runs along the arm to the wrist, its last 5 cm a cuff band.
    sleeve_r = {}
    skin = P[headw < 0.5]
    for side, sgn in (("l", 1.0), ("r", -1.0)):
        sh = np.array(bones[f"upperarm_{side}"].head_local)
        el = np.array(bones[f"lowerarm_{side}"].head_local)
        wr = np.array(bones[f"hand_{side}"].head_local)
        d1, d2 = (el - sh) / np.linalg.norm(el - sh), (wr - el) / np.linalg.norm(wr - el)
        l1, l2 = float(np.linalg.norm(el - sh)), float(np.linalg.norm(wr - el))
        pno = np.array([sgn, 0.0, 0.0])
        arm = P[(armw > 0.5) & (headw < 0.5)]
        # Half steps over the elbow, where the sleeve creases.
        stations = np.concatenate([np.arange(0.0, l1 - 0.06, step), np.arange(l1 - 0.06, l1 + 0.06, 0.5 * step),
                                   np.arange(l1 + 0.06, l1 + l2 - 0.005, step)])
        u = np.cross(d1, np.array([0.0, 0.0, 1.0]))
        u /= np.linalg.norm(u)
        u0 = u.copy()
        srings, frames = [], []
        for s in stations:
            b = min(1.0, max(0.0, (s - l1 + 0.04) / 0.08))
            b = b * b * (3.0 - 2.0 * b)
            d = d1 * (1.0 - b) + d2 * b
            d /= np.linalg.norm(d)
            c = sh + d1 * min(s, l1) + d2 * max(0.0, s - l1)
            u = u - d * float(u @ d)
            u /= np.linalg.norm(u)
            w = np.cross(d, u)
            near = arm[np.abs((arm - c) @ d) < step * 0.75]
            near = near[np.linalg.norm((near - c) - np.outer((near - c) @ d, d), axis=1) < 0.12]
            out = _ring_outline(near, c, u, w, S) if len(near) else np.zeros(S)
            srings.append(out)
            frames.append((c, u, w))
        SR = np.array(srings)
        first = next(i for i in range(len(SR)) if SR[i].max() > 0.0)
        SR[:first] = SR[first]
        SR = np.array([_hull_radii(_close_ring(r) + 0.010) for r in SR])
        cuff = stations > l1 + l2 - 0.05
        SR[cuff] += 0.004
        floor = SR.copy()
        for _ in range(3):
            SR[1:-1] = (SR[:-2] + 2.0 * SR[1:-1] + SR[2:]) * 0.25
            SR = np.maximum(SR, floor - 0.004)
        sleeve_r[side] = float(np.median(SR[(stations > 0.3 * l1) & (stations < 0.9 * l1)]))
        # The sleeve creases inside the elbow, and stacks in two soft rolls over its cuff.
        crook = d2 - d1 * float(d1 @ d2)
        if np.linalg.norm(crook) < 0.05:
            crook = np.array([0.0, -1.0, 0.0]) + d1 * float(d1[1])
        crook /= np.linalg.norm(crook)
        for i, ((c, u_, w_), s) in enumerate(zip(frames, stations)):
            inner = np.clip((np.cos(ang)[:, None] * u_ + np.sin(ang)[:, None] * w_) @ crook, 0.0, 1.0) ** 1.5
            SR[i] += 0.0045 * math.exp(-((s - l1) / 0.05) ** 2) * (0.5 + 0.5 * math.cos(2.0 * math.pi * (s - l1) / 0.04)) * inner
            SR[i] += 0.003 * sum(math.exp(-((s - (l1 + l2 - e)) / 0.011) ** 2) for e in (0.068, 0.098))
        rings = [np.array([c + (u_ * math.cos(a) + w_ * math.sin(a)) * r[k] for k, a in enumerate(ang)])
                 for (c, u_, w_), r in zip(frames, SR)]
        s1 = next(i for i, ring in enumerate(rings) if ((ring - sh) @ pno).min() > 0.01)
        # The head leaves the armhole flush with the body's cloth and takes on the shoulder's own sections towards the
        # arm. Its own sections alone stood a step inside the rim, which rose as a fin as soon as the arm hung down.
        rim_co = np.array([v.co[:] for v in {v for e in holes[side] for v in e.verts}])
        ch = rim_co.mean(axis=0)
        uh = u0 - pno * float(u0 @ pno)
        uh /= np.linalg.norm(uh)
        rel = rim_co - ch
        th = np.arctan2(rel @ np.cross(pno, uh), rel @ uh) % (2.0 * math.pi)
        order = np.argsort(th)
        rim_r = np.interp(ang, th[order], np.hypot(rel @ uh, rel @ np.cross(pno, uh))[order], period=2.0 * math.pi)
        heads = []
        for tau in (0.15, 0.55):
            c = (1.0 - tau) * ch + tau * frames[s1][0]
            n = (1.0 - tau) * pno + tau * d1
            n /= np.linalg.norm(n)
            uu = u0 - n * float(u0 @ n)
            uu /= np.linalg.norm(uu)
            ww = np.cross(n, uu)
            near = skin[np.abs((skin - c) @ n) < step * 0.75]
            near = near[np.linalg.norm((near - c) - np.outer((near - c) @ n, n), axis=1) < 0.10]
            r = _hull_radii(_close_ring(_ring_outline(near, c, uu, ww, S)) + 0.010)
            keep = 1.0 - tau / 0.7  # the rim's share of the section
            r = np.maximum(r, keep * rim_r + (1.0 - keep) * r)
            heads.append(np.array([c + (uu * math.cos(a) + ww * math.sin(a)) * r[k] for k, a in enumerate(ang)]))
        sg = [[bm.verts.new(tuple(p)) for p in ring] for ring in heads + rings[s1:]]
        ends = [None, None] + list(l1 + l2 - stations[s1:])
        for k in range(S):
            k2 = (k + 1) % S
            for i in range(len(sg) - 1):
                f = bm.faces.new((sg[i][k], sg[i][k2], sg[i + 1][k2], sg[i + 1][k]))
                to_end = ends[i] if ends[i] is not None else 1.0
                f[zone] = 1 if to_end < 0.050 else (2 if to_end < 0.059 else 0)
        # The armhole's seam: its rim and the head's first section, joined by a piped band.
        seam = bmesh.ops.bridge_loops(bm, edges=holes[side] + [bm.edges.get((sg[0][k], sg[0][(k + 1) % S])) for k in range(S)])
        for f in seam["faces"]:
            f[zone] = 2
        print(f"[equip_styleb] sleeve {side}: set in {stations[s1] * 100:.1f} cm down the arm, seam {len(seam['faces'])} faces")
    # Brass buttons: three down the wrap's inner panel, one on each pocket's flap.
    def surface(z, a):
        k = int(round(a / (2.0 * math.pi) * S)) % S
        r = float(np.interp(z, zs[::-1], R[::-1, k]))
        return np.array([r * math.cos(a), float(np.interp(z, zs[::-1], cyz[::-1])) + r * math.sin(a), z])

    studs = []
    for z in np.linspace(belt_z + 0.045, n0.z - 0.075, 3):
        n = np.cross(np.array([1.0, 0.0, 0.0]), surface(z + 0.01, 1.5 * math.pi) - surface(z - 0.01, 1.5 * math.pi))
        n /= np.linalg.norm(n)
        studs += _dome(bm, surface(z, 1.5 * math.pi) + n * 0.0015, n, 0.007, 0.003)
    for sgn in (-1.0, 1.0):
        a0 = -0.5 * math.pi + sgn * math.radians(52.0)
        n = np.array([math.cos(a0), math.sin(a0), 0.0])
        studs += _dome(bm, surface(hip_z - 0.076, a0) + n * 0.0105, n, 0.0065, 0.0028)
    for f in studs:
        f[zone] = 3
    patches += [v for f in studs for v in f.verts]
    cloth = [f for f in bm.faces if f[zone] != 3]  # a stud's own winding faces out
    bmesh.ops.recalc_face_normals(bm, faces=cloth)
    bm.normal_update()
    # The cloth faces away from the body: the lining is laid inside it. Recalculated on an open shell, the normals
    # turned inwards on some figures, and the pilot wore her blue lining over the coat.
    out = sum(f.normal.dot(Vector((f.calc_center_median().x, f.calc_center_median().y - float(np.interp(
        f.calc_center_median().z, zs[::-1], cyz[::-1])), 0.0))) * f.calc_area() for f in cloth)
    if out < 0.0:
        bmesh.ops.reverse_faces(bm, faces=cloth)
    bm.verts.index_update()
    patch_ids = sorted({v.index for v in patches})
    mesh = bpy.data.meshes.new("styleb_jacket")
    bm.to_mesh(mesh)
    zones = [f[zone] for f in bm.faces]
    bm.free()
    obj = bpy.data.objects.new("styleb_jacket", mesh)
    bpy.context.collection.objects.link(obj)
    for name, rgb in (("EX_CLOTH_MAIN_coat", main_rgb), ("EX_CLOTH_ACCENT_coat", accent_rgb), ("EX_CLOTH_TRIM_coat", trim_rgb)):
        obj.data.materials.append(_make_pbr_mat(name, tuple(rgb), roughness=0.8))
    brass = _make_pbr_mat("EX_METAL_BRASS_coat", (0.74, 0.62, 0.35), roughness=0.28, metallic=0.88)
    obj.data.materials.append(brass)
    # The coat is lined in a shade of its accent: through the parted slit, a turned hem or a cuff, the inside reads as
    # cloth. Unlined, an open slit showed a black gap between the legs.
    lining = _make_pbr_mat("EX_CLOTH_ACCENT_lining", tuple(0.85 * c for c in accent_rgb), roughness=0.82)
    for m in (lining, lining, lining, brass):
        obj.data.materials.append(m)
    for poly, z_ in zip(obj.data.polygons, zones):
        poly.material_index = z_
        poly.use_smooth = True
    # Skinned as one layer, then thickened: the cloth's two faces carry the same weights.
    _skin_jacket_cleanly(obj, human_obj, rig, sh_half_x, pelv_z, sleeve_r, slit=True)
    # A patch sewn on the cloth moves with the cloth under it: it takes the weights found under it on that cloth.
    # With weights of its own, the panel bulged through a pocket's flap as the thigh swung.
    vs = [v.co.copy() for v in obj.data.vertices]
    patch_set = set(patch_ids)
    base = [tuple(p.vertices) for p in obj.data.polygons if not patch_set & set(p.vertices)]
    tree = BVHTree.FromPolygons(vs, base)
    W = [{g.group: g.weight for g in v.groups} for v in obj.data.vertices]
    for pi in patch_ids:
        _loc, _n, fi, _d = tree.find_nearest(vs[pi])
        mix = {}
        for vi, b in zip(base[fi], interpolate.poly_3d_calc([vs[k] for k in base[fi]], vs[pi])):
            for gi, w in W[vi].items():
                mix[gi] = mix.get(gi, 0.0) + b * w
        for gi in W[pi]:
            obj.vertex_groups[gi].remove([pi])
        for gi, w in mix.items():
            if w > 1e-4:
                obj.vertex_groups[gi].add([pi], w, "REPLACE")
    sol = obj.modifiers.new("Thickness", "SOLIDIFY")
    sol.thickness, sol.offset, sol.use_rim, sol.material_offset = 0.004, -1.0, True, 4  # the inner face takes the lining
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_move_to_index(modifier=sol.name, index=0)
    bpy.ops.object.modifier_apply(modifier=sol.name)
    print(f"[equip_styleb] built coat: {len(obj.data.vertices)} verts, sleeve radius l {sleeve_r['l'] * 100:.1f} r {sleeve_r['r'] * 100:.1f} cm")
    # The coat's brush strokes follow its forms: U runs around the body and around each sleeve, V up the body and
    # along the arm, so strokes laid on the bias wrap the figure. A box projection turned them at every face's axis.
    me, tile = obj.data, 0.32
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    uv_layer = me.uv_layers.new(name="UVMap")
    co = np.array([v.co[:] for v in me.vertices])
    cyv = np.interp(co[:, 2], zs[::-1], cyz[::-1])
    ang = np.arctan2(co[:, 1] - cyv, co[:, 0])
    reach = np.full(len(co), 0.16)  # the radius a turn of U is measured at: the body's, then each arm's
    along = co[:, 2].copy()
    for side, sgn in (("l", 1.0), ("r", -1.0)):
        sh, el, wr = (np.array(bones[f"{b}_{side}"].head_local) for b in ("upperarm", "lowerarm", "hand"))
        d1, d2 = (el - sh) / np.linalg.norm(el - sh), (wr - el) / np.linalg.norm(wr - el)
        l1 = float(np.linalg.norm(el - sh))
        sel = co[:, 0] * sgn > abs(sh[0])  # beyond the upright armhole: the sleeve
        s1 = (co[sel] - sh) @ d1
        fore = s1 > l1
        along[sel] = np.where(fore, l1 + (co[sel] - el) @ d2, s1)
        u1 = np.cross(d1, [0.0, 0.0, 1.0])
        u1 /= np.linalg.norm(u1)
        w1 = np.cross(d1, u1)
        rel = co[sel] - sh
        ang[sel] = np.arctan2(rel @ w1, rel @ u1)
        reach[sel] = 0.05
    uvs = np.empty((len(me.loops), 2), dtype=np.float32)
    loop_vi = np.empty(len(me.loops), dtype=np.int32)
    me.loops.foreach_get("vertex_index", loop_vi)
    for poly in me.polygons:
        vi = loop_vi[poly.loop_start:poly.loop_start + poly.loop_total]
        a = ang[vi].copy()
        if a.max() - a.min() > math.pi:  # a face across the seam behind: its angles taken on one side
            a[a < 0.0] += 2.0 * math.pi
        uvs[poly.loop_start:poly.loop_start + poly.loop_total, 0] = a * reach[vi] / tile
        uvs[poly.loop_start:poly.loop_start + poly.loop_total, 1] = along[vi] / tile
    uv_layer.data.foreach_set("uv", uvs.ravel())
    # Under the skirt the trousers show only through its slit. Away from the slit, their cloth is cut where the coat
    # always covers it, as the skin is under the coat: swung forward, a thigh came out through the panel by a pocket.
    if trousers_obj is not None:
        cy_hip = float(np.interp(hip_z, zs[::-1], cyz[::-1]))
        bm_t = bmesh.new()
        bm_t.from_mesh(trousers_obj.data)
        hidden = [f for f in bm_t.faces if z_hem + 0.06 < f.calc_center_median().z < hip_z + 0.05
                  and abs(math.atan2(f.calc_center_median().x, cy_hip - f.calc_center_median().y)) > math.radians(35.0)]
        bmesh.ops.delete(bm_t, geom=hidden, context="FACES")
        bm_t.to_mesh(trousers_obj.data)
        bm_t.free()
        print(f"[equip_styleb] trousers: {len(hidden)} faces under the skirt cut away")
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

    # Tailored cloth hangs from where the body carries it. In each direction around a leg, a trouser narrows no
    # faster than its cloth can fall: it keeps the leg's own section and bridges its hollows, behind the knee and
    # under the calf, where a constant ease wraps them like tights. It gathers into the boot, whose top it meets with
    # almost no ease.
    # The coat skirt hides the trousers above its hem, where they stay close; the drape starts just under it.
    drape_z = b_pelv.head_local.z - 0.20
    tuck_z = b_foot_l.head_local.z + 0.11  # the boot's top
    # Over the thigh the cloth may narrow as fast as the thigh does towards its knee: held to a slower fall there, or
    # rounded to its widest radius, the leg balloons as soon as the knee bends. Below the knee the shank is rigid and
    # the cloth falls straight, as cut: following the calf and the ankle, it reads as tights on a heavy thigh.
    # Stretched between two bulges, it spans the hollow between them.
    ease, fall_thigh, fall_shank, span = 0.006, 0.20, 0.03, 0.05  # m, then m of radius per m of leg
    bins, sectors = 48, 12  # samples along and around the leg
    for sgn, side in ((1.0, "l"), (-1.0, "r")):
        hip = rig.data.bones[f"thigh_{side}"].head_local
        axis = rig.data.bones[f"foot_{side}"].head_local - hip
        length = axis.length
        axis = axis / length
        side_u = axis.cross(Vector((0.0, 1.0, 0.0))).normalized()
        side_v = axis.cross(side_u)
        leg = []
        for v in bm.verts:
            if v.co.x * sgn <= 0.0 or v.co.z > drape_z:
                continue
            rel = v.co - hip
            along = rel.dot(axis)
            leg.append((v, along, min(bins - 1, max(0, int(along / length * bins))), rel.dot(side_u), rel.dot(side_v)))
        # The tube follows the limb's own centre line, which leaves the hip-to-ankle axis at the thigh.
        lo = np.full((bins, 2), 1e9)
        hi = np.full((bins, 2), -1e9)
        for _v, _along, i, pu, pv in leg:
            lo[i] = np.minimum(lo[i], (pu, pv))
            hi[i] = np.maximum(hi[i], (pu, pv))
        filled = hi[:, 0] > lo[:, 0]
        centre = np.where(filled[:, None], (lo + hi) * 0.5, 0.0)
        for _ in range(2):
            centre[1:-1] = (centre[:-2] + 2.0 * centre[1:-1] + centre[2:]) * 0.25
        polar = []
        body_r = np.zeros((bins, sectors))
        for v, along, i, pu, pv in leg:
            du, dv = pu - centre[i, 0], pv - centre[i, 1]
            r, s = math.hypot(du, dv), (math.atan2(dv, du) / (2.0 * math.pi) + 0.5) * sectors
            polar.append((v, along, i, du, dv, r, s))
            body_r[i, int(s) % sectors] = max(body_r[i, int(s) % sectors], r)
        # A direction without a sample takes its section's mean; one pass around rounds the section slightly.
        for i in range(bins):
            got = body_r[i] > 0.0
            if got.any():
                body_r[i, ~got] = body_r[i, got].mean()
        body_r = (np.roll(body_r, 1, axis=1) + 2.0 * body_r + np.roll(body_r, -1, axis=1)) * 0.25
        drape = np.zeros((bins, sectors))
        bin_z = [hip.z + axis.z * (i + 0.5) * length / bins for i in range(bins)]
        gather = [min(1.0, max(0.0, (tuck_z + 0.08 - z) / 0.08)) for z in bin_z]
        for i in range(bins):
            close = body_r[i] + ease + (0.004 - ease) * gather[i]
            fall = fall_thigh if bin_z[i] > knee_z else fall_shank
            hang = drape[i - 1] - fall * length / bins if i and filled[i - 1] else 0.0
            drape[i] = np.maximum(close, hang * (1.0 - gather[i]))
        for i in range(bins - 2, -1, -1):
            if filled[i] and filled[i + 1] and gather[i + 1] == 0.0:
                drape[i] = np.maximum(drape[i], drape[i + 1] - span * length / bins)
        for v, along, i, du, dv, r, s in polar:
            s0 = math.floor(s - 0.5)
            fs = s - 0.5 - s0
            target = drape[i, s0 % sectors] * (1.0 - fs) + drape[i, (s0 + 1) % sectors] * fs
            w = min(1.0, (drape_z - v.co.z) / 0.06)
            k = (r + (max(target, r + 0.004) - r) * w * w * (3.0 - 2.0 * w)) / max(r, 1e-6)
            v.co = hip + axis * along + side_u * (centre[i, 0] + du * k) + side_v * (centre[i, 1] + dv * k)
            v.co.x = sgn * max(v.co.x * sgn, 0.003)  # the two legs meet at the inseam, they never cross

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

    if with_belt:
        # Trace 40-point contours around the jacket, ignoring the sleeves; 0 = front (-Y).
        sh_x_lim = abs(rig.data.bones["upperarm_l"].head_local.x) * 1.18
        dirs = [Vector((math.sin(k / 40.0 * 2.0 * math.pi), -math.cos(k / 40.0 * 2.0 * math.pi), 0.0)) for k in range(40)]

        def trace(z):
            c = Vector((0.0, b_pelv.head_local.y, z))
            radii = []
            for d in dirs:
                hit_loc, _n, _i, _dist = j_bvh.ray_cast(c + d * 0.285, -d, 0.285)
                seen = hit_loc is not None and abs(hit_loc.x) < sh_x_lim and (hit_loc - c).length < 0.275
                radii.append((hit_loc - c).length if seen else 0.160)
            return radii

        # A belt cinches the garment's own waist: its narrowest ring, which clears the pocket flaps below it.
        waist_z = min((b_pelv.head_local.z + 0.06 + 0.01 * i for i in range(19)), key=lambda z: sum(trace(z)))
        ctr = Vector((0.0, b_pelv.head_local.y, waist_z))
        cloth = trace(waist_z)
        radii = cloth
        for _ in range(4):
            radii = [radii[k - 1] * 0.25 + radii[k] * 0.50 + radii[(k + 1) % 40] * 0.25 for k in range(40)]
        # Pulled taut, it bridges hollows and never sinks into the cloth.
        ring_pts = [ctr + d * (max(r, c) + 0.005) for d, r, c in zip(dirs, radii, cloth)]

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
                bm.edges.get((r0[j], r1[j])).smooth = False  # a band's edges stay crisp, as on the strap

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
        # The belt moves with the cloth it cinches: it takes the jacket's own weights.
        _transfer_weights_from_body(belt_obj, jacket_obj, rig, smooth_repeats=2)
        out.append(belt_obj)

    if with_satchel and satchel_glb.exists():
        sat = _import_single_glb(satchel_glb, "styleb_satchel")
        _override_material_color(sat, "EX_CLOTH_BAG", [0.64, 0.59, 0.43])
        _override_material_color(sat, "EX_LEATHER_BAG", [0.44, 0.24, 0.14])
        _override_material_color(sat, "EX_METAL_BRASS", [0.74, 0.62, 0.35])
        # A bag hung from a strap rests against the hip: its inner face lies on the tangent to the garment's outline
        # there, behind the hanging arm. Its top leans in, where the strap pulls it. Set flat along the side, its rear
        # corner stood 15 cm off the seat and the strap crossed the back in mid-air.
        hip_z = b_pelv.head_local.z - 0.14
        # Behind the right side. At 25 deg its front corner stands where the hand hangs; at 60 deg the strap has to
        # wrap the hips like a second belt.
        bearing = math.radians(40.0)
        out_d = Vector((-math.cos(bearing), math.sin(bearing), 0.0))
        along_t = Vector((math.sin(bearing), math.cos(bearing), 0.0))  # towards the back
        bpy.ops.object.select_all(action="DESELECT")
        sat.select_set(True)
        bpy.context.view_layer.objects.active = sat
        sat.rotation_mode = "XYZ"
        # The bag's front (-Y) turns to face outwards; its top leans 6 deg towards the body.
        sat.rotation_euler = Euler((math.radians(-6.0), 0.0, -math.pi / 2.0 - bearing), "XYZ")
        bpy.ops.object.transform_apply(rotation=True)
        sat_vs2 = [v.co for v in sat.data.vertices]
        sz_lo, sz_hi = min(v.z for v in sat_vs2), max(v.z for v in sat_vs2)
        rest = max(
            (v.co for v in jacket_obj.data.vertices if abs(v.co.z - hip_z) < 0.5 * (sz_hi - sz_lo) and v.co.x < 0.0),
            key=lambda co: co.dot(out_d),
        )
        t_mid = 0.5 * (min(v.dot(along_t) for v in sat_vs2) + max(v.dot(along_t) for v in sat_vs2))
        sat.location = (out_d * (rest.dot(out_d) + 0.012 - min(v.dot(out_d) for v in sat_vs2))
                        + along_t * (rest.dot(along_t) - t_mid) + Vector((0.0, 0.0, hip_z - 0.5 * (sz_lo + sz_hi))))
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
        # Its two rings sit at the top corners, on the body's side of the bag's thickness.
        ring_d = min(v.dot(out_d) for v in sat_vs3) + 0.02
        ring_z = max(v.z for v in sat_vs3) - 0.025
        p_front_ring = out_d * ring_d + along_t * (min(v.dot(along_t) for v in sat_vs3) + 0.025) + Vector((0.0, 0.0, ring_z))
        p_back_ring = out_d * ring_d + along_t * (max(v.dot(along_t) for v in sat_vs3) - 0.025) + Vector((0.0, 0.0, ring_z))
        # Raycast straight down onto jacket's left shoulder crest so the strap sits flush (never floating!).
        sh_probe_x = b_clav_l.tail_local.x * 0.62
        sh_probe_y = b_clav_l.tail_local.y
        sh_hit, _, _, _ = j_bvh.ray_cast(Vector((sh_probe_x, sh_probe_y, b_clav_l.tail_local.z + 0.22)), Vector((0.0, 0.0, -1.0)), 0.35)
        sh_top = (sh_hit + Vector((0.0, 0.0, 0.005))) if sh_hit is not None else Vector((sh_probe_x, sh_probe_y, b_clav_l.tail_local.z + 0.03))

        # A taut strap lies in one plane, through the shoulder crest and the satchel's rings, on the convex hull of the
        # garment's section there: it bridges hollows and cannot kink.
        ring_mid = (p_front_ring + p_back_ring) * 0.5
        e_up = (sh_top - ring_mid).normalized()
        # Fore and aft, not along the rings: turned with the bag, the plane cuts the collar and the strap climbs it.
        e_fwd = Vector((0.0, -1.0, 0.0))
        e_fwd = (e_fwd - e_up * e_fwd.dot(e_up)).normalized()
        ctr = (sh_top + ring_mid) * 0.5
        reach = (sh_top - ring_mid).length
        section = [p_front_ring, p_back_ring]
        # The strap runs up from its rings: only the garment above them can carry it. A seat that swells below a
        # ring is not in its way.
        ring_level = max((p - ctr).dot(e_up) for p in section)
        for k in range(96):
            ang = k / 96.0 * 2.0 * math.pi
            d = e_up * math.cos(ang) + e_fwd * math.sin(ang)
            hit, _n, _i, _dist = j_bvh.ray_cast(ctr + d * reach, -d, reach)
            if hit is not None and (hit - ctr).dot(e_up) > ring_level:
                section.append(hit)
        flat = [((p - ctr).dot(e_fwd), (p - ctr).dot(e_up)) for p in section]
        hull = geometry.convex_hull_2d(flat)
        if 0 not in hull or 1 not in hull:
            raise ValueError("The satchel's rings lie inside the garment: its strap cannot hang taut")
        # From the front ring over the shoulder to the back ring: the hull's way round that climbs.
        ia, ib, n_h = hull.index(0), hull.index(1), len(hull)
        arc = [hull[(ia + s) % n_h] for s in range((ib - ia) % n_h + 1)]
        if max(flat[i][1] for i in arc) < 0.0:
            arc = [hull[(ia - s) % n_h] for s in range((ia - ib) % n_h + 1)]
        strap_pts = [section[arc[0]]]
        for i0, i1 in zip(arc, arc[1:]):
            steps = max(1, math.ceil((section[i1] - section[i0]).length / 0.015))
            strap_pts += [section[i0].lerp(section[i1], s / steps) for s in range(1, steps + 1)]
        n_s = len(strap_pts)

        def outward(p, normal):
            return normal if normal.dot(p - ctr) > 0.0 else -normal

        # Where it rests on the cloth, the band lies flat on it; where it bridges, it faces away from the body. It turns
        # from the one to the other over 2 cm of clearance, and along 10 cm of its length: switched at once, the band
        # twisted, its lift swung sideways with it, and it read as an S along the back.
        faces = []
        for k, p in enumerate(strap_pts):
            away = (p - ctr).normalized()
            loc, nrm, _i, dist = j_bvh.find_nearest(p)
            rest_w = 0.0 if loc is None or k in (0, n_s - 1) else min(1.0, max(0.0, (0.03 - dist) / 0.02))
            faces.append(away.lerp(outward(p, nrm), rest_w * rest_w * (3.0 - 2.0 * rest_w)).normalized() if rest_w else away)
        for _ in range(8):
            faces = [faces[0]] + [(faces[k - 1] + faces[k] * 2.0 + faces[k + 1]).normalized() for k in range(1, n_s - 1)] + [faces[-1]]

        # A flat 3.2 cm x 3.5 mm band; each section lifts until both of its edges clear the cloth.
        w_half, t_thick, clear = 0.016, 0.0035, 0.0015
        frames, lifts = [], []
        for k, p in enumerate(strap_pts):
            tan = (strap_pts[min(k + 1, n_s - 1)] - strap_pts[max(k - 1, 0)]).normalized()
            out_v = (faces[k] - tan * faces[k].dot(tan)).normalized()
            side_v = tan.cross(out_v)
            lift = 0.0
            for edge in (p - side_v * w_half, p + side_v * w_half):
                loc, nrm, _i, _dist = j_bvh.find_nearest(edge)
                if loc is not None:
                    lift = max(lift, min(0.02, -(edge - loc).dot(outward(edge, nrm))))
            frames.append((out_v, side_v))
            lifts.append(lift)
        lifts = [max(lifts[max(k - 2, 0):k + 3]) for k in range(n_s)]
        for _ in range(3):
            lifts = [(lifts[max(k - 1, 0)] + lifts[k] * 2.0 + lifts[min(k + 1, n_s - 1)]) * 0.25 for k in range(n_s)]

        bm = bmesh.new()
        s_rings = []
        for p, (out_v, side_v), lift in zip(strap_pts, frames, lifts):
            base = p + out_v * (clear + lift)
            s_rings.append((
                bm.verts.new(base - side_v * w_half),
                bm.verts.new(base + side_v * w_half),
                bm.verts.new(base + side_v * w_half + out_v * t_thick),
                bm.verts.new(base - side_v * w_half + out_v * t_thick),
            ))
        for r0, r1 in zip(s_rings, s_rings[1:]):
            for j in range(4):
                j2 = (j + 1) % 4
                f = bm.faces.new((r0[j], r1[j], r1[j2], r0[j2]))
                f.smooth = True
                # Smooth along its length, crisp at its four edges: fully smoothed, a band shades like a tube.
                bm.edges.get((r0[j], r1[j])).smooth = False
        smesh = bpy.data.meshes.new("styleb_satchel_strap")
        bm.to_mesh(smesh)
        bm.free()
        smesh.update()
        strap_obj = bpy.data.objects.new("styleb_satchel_strap", smesh)
        bpy.context.collection.objects.link(strap_obj)
        strap_obj.data.materials.append(_make_pbr_mat("EX_LEATHER_BAG_strap", (0.44, 0.24, 0.14), roughness=0.44, metallic=0.0))
        _assign_metric_box_uvs(strap_obj, tile_m=0.20)
        _transfer_weights_from_body(strap_obj, jacket_obj, rig, smooth_repeats=3)
        # A taut strap hangs between its two anchors, the shoulder it rests on and the bag sewn to its ends: its
        # weights blend along its length from the jacket's at the crest to the bag's at each ring. Taken from the
        # cloth under it, it bent wherever the jacket's weights turn from chest to pelvis: an S on the back at each
        # step, and ends that parted from the bag whenever the trunk turned over the hips.
        run = [0.0]
        for p0, p1 in zip(strap_pts, strap_pts[1:]):
            run.append(run[-1] + (p1 - p0).length)
        k_top = max(range(n_s), key=lambda k: strap_pts[k].z)  # the shoulder crest
        names = {vg.index: vg.name for vg in strap_obj.vertex_groups}
        crest = {}
        for v in strap_obj.data.vertices:
            if v.index // 4 == k_top:
                for g in v.groups:
                    crest[names[g.group]] = crest.get(names[g.group], 0.0) + g.weight / 4.0
        bag = {"pelvis": 0.85, "spine_01": 0.15}
        # Where it rests on the cloth, it moves with the cloth: the layers at one place move as one. Weighted between
        # its anchors there too, it sank into the coat over the chest as the trunk turned over the hips at each step.
        rest = []
        for k, p in enumerate(strap_pts):
            loc, _n, _i, dist = j_bvh.find_nearest(p)
            rest.append(0.0 if loc is None or k in (0, n_s - 1) else min(1.0, max(0.0, (0.03 - dist) / 0.02)))
        for _ in range(8):
            rest = [rest[0]] + [(rest[k - 1] + 2.0 * rest[k] + rest[k + 1]) * 0.25 for k in range(1, n_s - 1)] + [rest[-1]]
        # The cloth's weights are taken per section and eased along the strap over a few centimetres: a leather band
        # bends gradually where the trunk turns over the hips. Taken at each section, it jogged across the belt.
        cloth = [{} for _ in range(n_s)]
        for v in strap_obj.data.vertices:
            for g in v.groups:
                cloth[v.index // 4][names[g.group]] = cloth[v.index // 4].get(names[g.group], 0.0) + g.weight / 4.0
        for _ in range(12):
            cloth = [cloth[0]] + [{n: (cloth[k - 1].get(n, 0.0) + 2.0 * cloth[k].get(n, 0.0) + cloth[k + 1].get(n, 0.0)) * 0.25
                                   for n in set(cloth[k - 1]) | set(cloth[k]) | set(cloth[k + 1])}
                                  for k in range(1, n_s - 1)] + [cloth[-1]]
        groups = {n: strap_obj.vertex_groups.get(n) or strap_obj.vertex_groups.new(name=n)
                  for n in set(crest) | set(bag) | {n for c in cloth for n in c}}
        for v in strap_obj.data.vertices:
            k = v.index // 4
            u = abs(run[k] - run[k_top]) / max(run[-1] - run[k_top] if k > k_top else run[k_top], 1e-6)
            taut = {n: w * (1.0 - u) for n, w in crest.items()}
            for n, w in bag.items():
                taut[n] = taut.get(n, 0.0) + w * u
            for gi in [g.group for g in v.groups]:  # copied: removing a weight invalidates the others
                strap_obj.vertex_groups[gi].remove([v.index])
            for n in set(taut) | set(cloth[k]):
                w = rest[k] * cloth[k].get(n, 0.0) + (1.0 - rest[k]) * taut.get(n, 0.0)
                if w > 1e-4:
                    groups[n].add([v.index], w, "REPLACE")
        bpy.ops.object.select_all(action="DESELECT")
        strap_obj.select_set(True)
        bpy.context.view_layer.objects.active = strap_obj
        bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
        out.append(strap_obj)

    return out


def hide_covered_body_skin(human_obj, rig, jacket_obj):
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

    bm_j = bmesh.new()
    bm_j.from_mesh(jacket_obj.data)
    cover = BVHTree.FromBMesh(bm_j)
    bm_j.free()

    bm = bmesh.new()
    bm.from_mesh(human_obj.data)
    bm.normal_update()
    # Inside the collar's opening the skin shows down to where the cloth closes over it. A face stays if a ray from
    # it, straight out or towards the front and above, leaves without meeting the garment; two rings of neighbours
    # stay with it, so the skin's cut edge lies under the cloth. This cut runs narrower than a broad chest: where the
    # cloth lies just under the skin, the cloth is the surface, and the kept margin of skin yields beneath it. A fixed
    # box at the throat ended in a stepped edge and a dark gap inside every collar.
    up, fwd = Vector((0.0, 0.0, 1.0)), Vector((0.0, -1.0, 0.0))
    # The opening is the collar's, within 10 cm of the neck's base: a shoulder broader than the cut is not an opening,
    # nor is a gap between the wrapped front's layers further down, where kept skin showed as pale shards.
    collar = {f for f in bm.faces
              if neck_z - 0.10 <= f.calc_center_median().z < neck_z + 0.025 and abs(f.calc_center_median().x) < 0.10}
    shown = set()
    for f in collar:
        c = f.calc_center_median()
        if cover.ray_cast(c, -f.normal, 0.05)[0] is not None:
            continue
        for d in (f.normal, f.normal + up, f.normal + fwd, f.normal + up + fwd, f.normal + up * 2.0):
            if d.length > 1e-6 and cover.ray_cast(c + f.normal * 0.002, d.normalized(), 1.5)[0] is None:
                shown.add(f)
                break
    for _ in range(2):
        shown |= {g for f in shown for v in f.verts for g in v.link_faces if g in collar}
    for v in {v for f in shown for v in f.verts}:
        sunk = cover.ray_cast(v.co, -v.normal, 0.05)[0]
        if sunk is not None:
            v.co = sunk - v.normal * 0.003

    to_del = []
    for f in bm.faces:
        c = f.calc_center_median()
        # 1. Always keep entire head & upper neck above the collar top (z >= neck_z + 0.025).
        if c.z >= neck_z + 0.025 or f in shown:
            continue
        # 3. Keep the hands and 6 cm of forearm inside the cuff, which closes on the wrist: looking into it shows the
        # wrist, never the skin's cut edge.
        if (c - wr_l).dot(la_dir_l) > -0.06 and (c - wr_l).length < 0.22:
            continue
        if (c - wr_r).dot(la_dir_r) > -0.06 and (c - wr_r).length < 0.22:
            continue
        to_del.append(f)
    if to_del:
        bmesh.ops.delete(bm, geom=to_del, context="FACES")
    bm.to_mesh(human_obj.data)
    bm.free()
    human_obj.data.update()


def add_lash_lines(rig, human_obj):
    """A dark line along each upper lid's margin, as a painter draws the lashes, weighted like the lid it lies on.

    The margin is the lowest skin of the upper lid, in front of the eye: per 2.5 mm across, its lowest vertex that
    the lid carries. A ribbon 1.5 mm high at the inner corner and 3.2 mm at the outer one, which it overruns in a short
    lifted wing, lies 0.4 mm proud of the skin and 0.5 mm over the eye's top. Eyelash cards alone left the lid's edge
    as soft as the cheek; a 1 mm line was one pixel at conversation distance.
    """
    me = human_obj.data
    names = {g.index: g.name for g in human_obj.vertex_groups}
    bm = bmesh.new()
    weights = []
    for side, sgn in (("l", 1.0), ("r", -1.0)):
        gi = human_obj.vertex_groups.get(f"eyelid_upper_{side}")
        if gi is None:
            continue
        lid = [v for v in me.vertices if any(g.group == gi.index and g.weight > 0.1 for g in v.groups)]
        if len(lid) < 6:
            continue
        x0 = min(v.co.x for v in lid)
        bins = {}
        for v in lid:
            b = int((v.co.x - x0) / 0.0025)
            if b not in bins or v.co.z < bins[b].co.z:
                bins[b] = v
        margin = [bins[b] for b in sorted(bins, key=lambda b: b * sgn)]  # from the inner corner outwards
        pts = [v.co.copy() for v in margin] 
        pts.append(pts[-1] + (pts[-1] - pts[-2]).normalized() * 0.003 + Vector((0.0, 0.0, 0.0015)))  # the wing
        n_pts = len(pts)
        row = []
        for i, p in enumerate(pts):
            src = margin[min(i, len(margin) - 1)]
            tan = (pts[min(i + 1, n_pts - 1)] - pts[max(i - 1, 0)]).normalized()
            nrm = src.normal.copy()
            up = nrm.cross(tan).normalized()
            if up.z < 0.0:
                up = -up
            t = i / (n_pts - 1)
            high = 0.0 if i == n_pts - 1 else 0.0015 + 0.0017 * t * t
            base = p + nrm * 0.0004
            row.append((bm.verts.new(base - up * 0.0005), bm.verts.new(base + up * high)))
            w = {names[g.group]: g.weight for g in src.groups}
            weights += [w, w]
        for (a0, a1), (b0, b1) in zip(row, row[1:]):
            bm.faces.new((a0, b0, b1, a1))
    if not bm.faces:
        bm.free()
        return None
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new("styleb_lash_line")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("styleb_lash_line", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(_make_pbr_mat("EX_HAIR_lashline_cap", (0.035, 0.025, 0.02), roughness=0.85))
    for poly in obj.data.polygons:
        poly.use_smooth = True
    for i, w in enumerate(weights):
        for name, wt in w.items():
            (obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)).add([i], wt, "REPLACE")
    obj.parent = rig
    obj.modifiers.new(name="Armature", type="ARMATURE").object = rig
    return obj


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
