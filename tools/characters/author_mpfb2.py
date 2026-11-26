"""Author Milestone 1 MPFB2 spaceport characters in headless Blender 5.2.

Creates each archetype defined in assets/characters/spaceport_m1.json on the
canonical 53-bone MPFB2 `game_engine` skeleton, equips CC0 MakeHuman assets,
authors biomechanical looping clips (idle, walk, talk), exports clean glTF 2.0
(.glb) sources and renders neutral inspection cards outside Git.
"""
import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

try:
    bpy.ops.preferences.addon_enable(module="bl_ext.blender_org.mpfb")
except Exception:
    pass

from bl_ext.blender_org.mpfb.services.assetservice import AssetService
from bl_ext.blender_org.mpfb.services.humanservice import HumanService
from bl_ext.blender_org.mpfb.services.targetservice import TargetService

sys.path.insert(0, str(Path(__file__).resolve().parent))
import equip_styleb  # noqa: E402
import hair_cards  # noqa: E402
import retarget_mocap  # noqa: E402


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_asset(kind: str, stem: str) -> str:
    items = (
        AssetService.list_mhmat_assets("skins")
        if kind == "skins"
        else AssetService.list_mhclo_assets(kind)
    )
    for p in items:
        if p.stem == stem:
            return str(p)
    raise FileNotFoundError(f"MPFB2 asset not found: {kind}/{stem}")


def apply_mask_and_cleanup_modifiers(obj):
    """Bake active shape keys, apply MASK modifiers (removes helpers and cloth-occluded skin) and strip subsurf."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    # Bake any morphological shape keys into vertex positions before applying MASK modifiers.
    if obj.data.shape_keys is not None and len(obj.data.shape_keys.key_blocks) > 0:
        bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
    to_remove = [m.name for m in obj.modifiers if m.type == "SUBSURF"]
    for name in to_remove:
        obj.modifiers.remove(obj.modifiers[name])
    # Temporarily move MASK modifiers above ARMATURE so applying them preserves rest-pose geometry cleanly.
    mask_mods = [m.name for m in obj.modifiers if m.type == "MASK"]
    for name in mask_mods:
        while obj.modifiers.find(name) > 0:
            bpy.ops.object.modifier_move_up(modifier=name)
        bpy.ops.object.modifier_apply(modifier=name)


def clean_vertex_groups(obj, bone_names: set):
    """Keep only canonical skeleton bone vertex groups, max 4 influences, normalized."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for vg in list(obj.vertex_groups):
        if vg.name not in bone_names:
            obj.vertex_groups.remove(vg)
    if len(obj.vertex_groups) == 0:
        vg = obj.vertex_groups.new(name="head")
        vg.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
    # Ensure every vertex has non-zero total weight (fallback to nearest bone group).
    mesh = obj.data
    unweighted = []
    for v in mesh.vertices:
        total = sum(g.weight for g in v.groups)
        if total < 1e-5:
            unweighted.append(v.index)
    if unweighted:
        fallback_name = "head" if "hair" in obj.name.lower() or "eye" in obj.name.lower() else "pelvis"
        vg = obj.vertex_groups.get(fallback_name) or obj.vertex_groups.new(name=fallback_name)
        vg.add(unweighted, 1.0, "REPLACE")
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)


def get_or_create_gltf_output_group():
    """Return Blender's glTF Material Output node group so occlusionTexture exports natively to GLB."""
    ng = bpy.data.node_groups.get("glTF Material Output")
    if ng is None:
        ng = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        ng.interface.new_socket(name="Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    return ng


def normalize_material(mat, role_prefix: str, tint=None, roughness: float = 0.7, alpha_blend: bool = False, override_diffuse_path: str = None):
    """Rebuild or tune a clean Principled BSDF material for reliable glTF 2.0 export (including AO & Normals)."""
    if not mat:
        return
    if not mat.name.startswith("EX_"):
        mat.name = f"{role_prefix}_{mat.name}"
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links

    # Find existing image textures from MPFB2 MAKESKIN node graph (diffuse, normal, ambient occlusion).
    diffuse_img = None
    normal_img = None
    ao_img = None
    for n in nodes:
        if n.type == "TEX_IMAGE" and n.image is not None:
            lname = (n.name + " " + n.label + " " + n.image.name + " " + n.image.filepath).lower()
            if "norm" in lname or "bump" in lname:
                normal_img = n.image
            elif "_ao" in lname or "occlusion" in lname or "ao." in lname:
                ao_img = n.image
            elif diffuse_img is None:
                diffuse_img = n.image
            elif "diff" in lname or "albedo" in lname or "color" in lname:
                diffuse_img = n.image

    if override_diffuse_path and Path(override_diffuse_path).exists():
        diffuse_img = bpy.data.images.load(override_diffuse_path, check_existing=True)

    # Fallback: check sibling *_ao.png on disk if MAKESKIN did not wire it into a node.
    if ao_img is None and diffuse_img is not None and diffuse_img.filepath:
        dp = Path(bpy.path.abspath(diffuse_img.filepath))
        if "_diffuse" in dp.stem.lower():
            cand = dp.with_name(dp.stem.lower().replace("_diffuse", "_ao") + dp.suffix)
            if cand.exists():
                ao_img = bpy.data.images.load(str(cand), check_existing=True)

    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.5 if role_prefix != "EX_EYE" else 0.85
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    if diffuse_img is not None:
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = diffuse_img
        if tint is not None:
            # Blender's glTF 2.0 exporter maps Mix(MULTIPLY, Factor=1.0) directly to baseColorTexture * baseColorFactor.
            w = 0.72 if role_prefix == "EX_CLOTH" else 0.85
            tc = [1.0 - w + w * float(c) for c in tint]
            mix = nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            mix.inputs["Factor"].default_value = 1.0
            mix.inputs["B"].default_value = (tc[0], tc[1], tc[2], 1.0)
            links.new(tex.outputs["Color"], mix.inputs["A"])
            links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
        else:
            links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        if alpha_blend:
            links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    elif tint is not None:
        bsdf.inputs["Base Color"].default_value = (tint[0], tint[1], tint[2], 1.0)

    if normal_img is not None:
        normal_img.colorspace_settings.name = "Non-Color"
        ntex = nodes.new("ShaderNodeTexImage")
        ntex.image = normal_img
        nmap = nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = 0.75 if role_prefix == "EX_SKIN" else 0.9
        links.new(ntex.outputs["Color"], nmap.inputs["Color"])
        links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    if ao_img is not None:
        ao_img.colorspace_settings.name = "Non-Color"
        aotex = nodes.new("ShaderNodeTexImage")
        aotex.image = ao_img
        gltf_out = nodes.new("ShaderNodeGroup")
        gltf_out.node_tree = get_or_create_gltf_output_group()
        links.new(aotex.outputs["Color"], gltf_out.inputs["Occlusion"])

    if hasattr(mat, "blend_method"):
        mat.blend_method = "CLIP" if alpha_blend else "OPAQUE"


def add_arm_twist_bones_and_polish_weights(rig, meshes: list, clothing_objs: set):
    """Add 4 canonical arm twist helper bones (upperarm/lowerarm twist l/r) and smooth clothing weights.

    Twist bones are leaf helpers parallel to the main FK arm chain so they never alter hand world poses,
    while allowing the deltoid cap and wrist/forearm sleeves to distribute axial rotation cleanly without
    candy-wrapper pinching.
    """
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = rig.data.edit_bones
    for side in ("l", "r"):
        ua = eb.get(f"upperarm_{side}")
        if ua is not None and f"upperarm_twist_01_{side}" not in eb:
            uat = eb.new(f"upperarm_twist_01_{side}")
            uat.parent = ua
            uat.use_connect = False
            uat.head = ua.head.copy()
            uat.tail = ua.head.lerp(ua.tail, 0.55)
            uat.roll = ua.roll
        la = eb.get(f"lowerarm_{side}")
        if la is not None and f"lowerarm_twist_01_{side}" not in eb:
            lat = eb.new(f"lowerarm_twist_01_{side}")
            lat.parent = la
            lat.use_connect = False
            lat.head = la.head.lerp(la.tail, 0.45)
            lat.tail = la.tail.copy()
            lat.roll = la.roll
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()

    # Smooth clothing weights slightly before splitting twist weights to eliminate armpit/shoulder creasing.
    for obj in meshes:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        if obj in clothing_objs:
            try:
                bpy.ops.object.vertex_group_smooth(group_select_mode="ALL", factor=0.45, repeat=2)
            except Exception:
                pass

        for side in ("l", "r"):
            # Upperarm -> upperarm_twist_01 (highest weight near shoulder deltoid to cancel humeral twist at shoulder).
            ua_name = f"upperarm_{side}"
            uat_name = f"upperarm_twist_01_{side}"
            vg_ua = obj.vertex_groups.get(ua_name)
            b_ua = rig.data.bones.get(ua_name)
            if vg_ua is not None and b_ua is not None:
                vg_uat = obj.vertex_groups.get(uat_name) or obj.vertex_groups.new(name=uat_name)
                p0 = b_ua.head_local
                axis = b_ua.tail_local - b_ua.head_local
                l2 = max(axis.length_squared, 1e-6)
                ua_idx = vg_ua.index
                for v in obj.data.vertices:
                    w = 0.0
                    for g in v.groups:
                        if g.group == ua_idx:
                            w = g.weight
                            break
                    if w <= 1e-4:
                        continue
                    t = max(0.0, min(1.0, (v.co - p0).dot(axis) / l2))
                    u = max(0.0, min(1.0, (t - 0.04) / 0.66))
                    s = 1.0 - (u * u * (3.0 - 2.0 * u))
                    if s > 1e-4:
                        vg_ua.add([v.index], w * (1.0 - s), "REPLACE")
                        vg_uat.add([v.index], w * s, "ADD")

            # Lowerarm -> lowerarm_twist_01 (highest weight near wrist to distribute pronation/supination).
            la_name = f"lowerarm_{side}"
            lat_name = f"lowerarm_twist_01_{side}"
            vg_la = obj.vertex_groups.get(la_name)
            b_la = rig.data.bones.get(la_name)
            if vg_la is not None and b_la is not None:
                vg_lat = obj.vertex_groups.get(lat_name) or obj.vertex_groups.new(name=lat_name)
                p0 = b_la.head_local
                axis = b_la.tail_local - b_la.head_local
                l2 = max(axis.length_squared, 1e-6)
                la_idx = vg_la.index
                for v in obj.data.vertices:
                    w = 0.0
                    for g in v.groups:
                        if g.group == la_idx:
                            w = g.weight
                            break
                    if w <= 1e-4:
                        continue
                    t = max(0.0, min(1.0, (v.co - p0).dot(axis) / l2))
                    u = max(0.0, min(1.0, (t - 0.15) / 0.78))
                    s = u * u * (3.0 - 2.0 * u)
                    if s > 1e-4:
                        vg_la.add([v.index], w * (1.0 - s), "REPLACE")
                        vg_lat.add([v.index], w * s, "ADD")

        bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)


def bake_world_origin_and_ground(rig, meshes):
    """Bake object transforms into mesh + armature data so feet sit at exact Z = 0 and transforms are identity."""
    bpy.context.view_layer.update()
    # Compute lowest world Z across all visible meshes (shoes/feet define ground datum).
    min_z = 1e9
    max_z = -1e9
    for obj in meshes:
        mw = obj.matrix_world
        for v in obj.data.vertices:
            wz = (mw @ v.co).z
            if wz < min_z:
                min_z = wz
            if wz > max_z:
                max_z = wz

    shift = Vector((0.0, 0.0, -min_z))
    rig.location = rig.location + shift
    bpy.context.view_layer.update()

    # Apply transforms cleanly to armature and meshes so glTF has identity node transforms.
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Ensure Root bone sits cleanly at (0, 0, 0) in armature space.
    bpy.ops.object.mode_set(mode="EDIT")
    root = rig.data.edit_bones.get("Root")
    if root:
        delta = Vector((0.0, 0.0, 0.0)) - root.head
        root.head += delta
        root.tail += delta
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()

    # Re-verify bounds.
    z0 = min((obj.matrix_world @ v.co).z for obj in meshes for v in obj.data.vertices)
    z1 = max((obj.matrix_world @ v.co).z for obj in meshes for v in obj.data.vertices)
    return z0, z1


def world_rot_to_pose_quat(rig, bone_name: str, rx_deg: float, ry_deg: float, rz_deg: float) -> Quaternion:
    """Convert an anatomical world-space Euler XYZ rotation (deg) into pose bone local quaternion.

    In Blender MPFB2 space (right-handed): character faces -Y, +Z is up, +X is character's left.
      For hanging limbs (-Z): R_x(a)*(0,0,-1) = (0, +sin a, -cos a), so:
        rx < 0 swings a hanging limb FORWARD (-Y): hip/shoulder/elbow flexion, ankle dorsiflexion.
        rx > 0 swings a hanging limb BACKWARD (+Y): hip/shoulder extension, knee flexion, ankle plantarflexion.
      For upward segments (+Z, torso/neck/head): R_x(a)*(0,0,+1) = (0, -sin a, +cos a), so:
        rx > 0 leans/nods FORWARD (-Y).
      ry > 0 rolls counter-clockwise looking down +Y (lowers left arm, raises right arm).
      rz > 0 yaws counter-clockwise looking down +Z (turns left).
    """
    b = rig.data.bones.get(bone_name)
    if b is None:
        return Quaternion((1, 0, 0, 0))
    m_rest = b.matrix_local.to_3x3()
    r_world = Euler((math.radians(rx_deg), math.radians(ry_deg), math.radians(rz_deg)), "XYZ").to_matrix()
    r_local = m_rest.inverted() @ r_world @ m_rest
    return r_local.to_quaternion()


def world_trans_to_pose_loc(rig, bone_name: str, vec_world: Vector) -> Vector:
    b = rig.data.bones.get(bone_name)
    if b is None:
        return Vector((0, 0, 0))
    return b.matrix_local.to_3x3().inverted() @ vec_world


def reset_pose(rig):
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
        pb.location = Vector((0, 0, 0))
        pb.scale = Vector((1, 1, 1))


def set_bone_world_rot(rig, name: str, rx: float, ry: float, rz: float):
    pb = rig.pose.bones.get(name)
    if pb is None:
        return
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = world_rot_to_pose_quat(rig, name, rx, ry, rz)


def set_elbow_flex(rig, side: str, flex_deg: float, supinate_deg: float = 0.0):
    """Set anatomical elbow flexion in degrees (0 = straight, 90 = right angle) along lowerarm's true hinge axis.

    MPFB2's game_engine lowerarm rest pose is already flexed ~42 deg around local +X (hinge axis u x l).
    """
    pb = rig.pose.bones.get(f"lowerarm_{side}")
    if pb is None:
        return
    pb.rotation_mode = "QUATERNION"
    delta_x = math.radians(flex_deg - 42.0)
    delta_y = math.radians(supinate_deg)
    pb.rotation_quaternion = Euler((delta_x, delta_y, 0.0), "XYZ").to_quaternion()


def apply_relaxed_stance(rig):
    """Move arms from A-pose down to natural relaxed sides with true in-plane elbow carry."""
    set_bone_world_rot(rig, "clavicle_l", 0.0, 3.0, 0.0)
    set_bone_world_rot(rig, "clavicle_r", 0.0, -3.0, 0.0)
    # Lower upperarms ~34 deg from 45 deg A-pose so arms hang naturally ~11 deg clear of hips/coats.
    set_bone_world_rot(rig, "upperarm_l", 0.0, 34.0, 0.0)
    set_bone_world_rot(rig, "upperarm_r", 0.0, -34.0, 0.0)
    # Relaxed 14 deg natural elbow carry (straightened cleanly from the 42 deg rest bend).
    set_elbow_flex(rig, "l", 14.0)
    set_elbow_flex(rig, "r", 14.0)
    set_bone_world_rot(rig, "hand_l", 0.0, 4.0, 0.0)
    set_bone_world_rot(rig, "hand_r", 0.0, -4.0, 0.0)
    # Gentle natural curl on fingers so hands are not stiff boards.
    for side, sgn in (("l", 1.0), ("r", -1.0)):
        for finger, curl in (("index", 16.0), ("middle", 20.0), ("ring", 24.0), ("pinky", 28.0)):
            for seg in ("01", "02", "03"):
                set_bone_world_rot(rig, f"{finger}_{seg}_{side}", 0.0, sgn * curl, 0.0)
        set_bone_world_rot(rig, f"thumb_01_{side}", -6.0, -sgn * 8.0, 0.0)
        set_bone_world_rot(rig, f"thumb_02_{side}", -5.0, -sgn * 8.0, 0.0)
    # Narrow A-pose legs slightly into natural upright stance.
    set_bone_world_rot(rig, "thigh_l", 0.0, -3.5, 0.0)
    set_bone_world_rot(rig, "thigh_r", 0.0, 3.5, 0.0)
    set_bone_world_rot(rig, "foot_l", 0.0, 3.5, 0.0)
    set_bone_world_rot(rig, "foot_r", 0.0, -3.5, 0.0)


def keyframe_pose(rig, frame: int, bone_names):
    for name in bone_names:
        pb = rig.pose.bones.get(name)
        if pb is None:
            continue
        pb.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        if name == "pelvis":
            pb.keyframe_insert(data_path="location", frame=frame)


def build_clip(rig, name: str, frames: int, fps: int, pose_fn, animated_bones):
    """Build a seamless looping action and push it onto an NLA strip for glTF multi-clip export."""
    bpy.context.scene.render.fps = fps
    action = bpy.data.actions.new(name=name)
    if rig.animation_data is None:
        rig.animation_data_create()
    rig.animation_data.action = action

    for f in range(frames + 1):
        phase = 2.0 * math.pi * (f / float(frames))
        reset_pose(rig)
        apply_relaxed_stance(rig)
        pose_fn(rig, phase)
        keyframe_pose(rig, f + 1, animated_bones)

    if hasattr(action, "fcurves"):
        for fc in action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"

    track = rig.animation_data.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name, 1, action)
    strip.action_frame_start = 1
    strip.action_frame_end = frames + 1
    rig.animation_data.action = None
    return action


def pose_idle(rig, phase: float):
    breath = math.sin(phase * 2.0)
    sway = math.sin(phase)
    look = math.sin(phase - 0.8)
    pb_pelvis = rig.pose.bones["pelvis"]
    pb_pelvis.location = world_trans_to_pose_loc(rig, "pelvis", Vector((0.014 * sway, 0.0, -0.004 * abs(sway))))
    set_bone_world_rot(rig, "pelvis", 0.0, -1.6 * sway, 2.2 * sway)
    set_bone_world_rot(rig, "spine_01", 1.0 + 0.8 * breath, 0.8 * sway, -1.0 * sway)
    set_bone_world_rot(rig, "spine_02", 0.6 * breath, 0.6 * sway, -1.0 * sway)
    set_bone_world_rot(rig, "spine_03", 0.8 * breath, 0.0, -0.8 * sway)
    set_bone_world_rot(rig, "clavicle_l", 0.0, 4.0 - 1.5 * breath, 0.0)
    set_bone_world_rot(rig, "clavicle_r", 0.0, -4.0 + 1.5 * breath, 0.0)
    set_bone_world_rot(rig, "neck_01", -0.5 * breath, 0.0, 4.5 * look)
    set_bone_world_rot(rig, "head", 1.5 * math.sin(phase * 2.0 + 0.5), 1.5 * sway, 6.5 * look)
    set_bone_world_rot(rig, "upperarm_l", -2.0 - 2.0 * sway, 34.0 - 1.5 * breath, 0.0)
    set_bone_world_rot(rig, "upperarm_r", -2.0 + 2.0 * sway, -34.0 + 1.5 * breath, 0.0)
    set_elbow_flex(rig, "l", 15.0 + 2.5 * breath)
    set_elbow_flex(rig, "r", 15.0 - 2.5 * breath)
    # Soft natural knee cushion (thigh slightly forward rx<0, knee bent backward rx>0, foot compensates rx<0).
    set_bone_world_rot(rig, "thigh_l", -2.0 + 1.2 * sway, -3.5, 0.0)
    set_bone_world_rot(rig, "calf_l", 4.0 - 2.0 * sway, 0.0, 0.0)
    set_bone_world_rot(rig, "foot_l", -2.0 + 0.8 * sway, 3.5, 0.0)
    set_bone_world_rot(rig, "thigh_r", -2.0 - 1.2 * sway, 3.5, 0.0)
    set_bone_world_rot(rig, "calf_r", 4.0 + 2.0 * sway, 0.0, 0.0)
    set_bone_world_rot(rig, "foot_r", -2.0 - 0.8 * sway, -3.5, 0.0)


def _leg_angles(phi: float):
    """Biomechanically grounded hip, knee and ankle sagittal angles (deg) for walk phase phi.

    phi = 0: heel strike (leg forward, rx < 0); phi = pi: toe-off (leg back, rx > 0);
    phi = 1.5*pi: mid-swing (knee folded backward, rx > 0).
    """
    hip = -(18.0 * math.cos(phi) + 2.5 * math.cos(2.0 * phi - 0.4) + 1.0)
    # Knee always flexes BACKWARD (rx > 0): soft ~5-11 deg stance cushion, ~46 deg swing fold.
    swing_bell = max(0.0, -math.sin(phi - 0.15)) ** 1.35
    stance_cushion = max(0.0, math.sin(phi + 0.35)) * 7.0
    knee = 4.0 + stance_cushion + 42.0 * swing_bell
    # Ankle dorsiflexes (rx < 0) at heel strike, stays flat in mid-stance, plantarflexes (rx > 0) at push-off.
    ankle = -6.5 * math.cos(phi - 0.2) + 10.0 * max(0.0, -math.cos(phi - 0.35)) ** 1.5
    toe = -14.0 * max(0.0, -math.cos(phi - 0.25)) ** 1.4
    return hip, knee, ankle, toe


def pose_walk(rig, phase: float):
    l_hip, l_knee, l_ank, l_toe = _leg_angles(phase)
    r_hip, r_knee, r_ank, r_toe = _leg_angles(phase + math.pi)

    # Vertical double-frequency bob: lowest at double support (cos(2p)=1 -> drop), highest at mid-stance.
    bob_z = -0.022 - 0.020 * math.cos(2.0 * phase)
    sway_x = 0.020 * math.sin(phase)
    pelvis_yaw = -6.0 * math.cos(phase)
    pelvis_roll = 3.0 * math.sin(phase)

    pb_pelvis = rig.pose.bones["pelvis"]
    pb_pelvis.location = world_trans_to_pose_loc(rig, "pelvis", Vector((sway_x, 0.0, bob_z)))
    set_bone_world_rot(rig, "pelvis", 3.0, pelvis_roll, pelvis_yaw)

    # Counter-rotating spine + slight natural forward walk lean (rx > 0 leans upper body forward).
    set_bone_world_rot(rig, "spine_01", 1.8, -1.2 * math.sin(phase), 3.0 * math.cos(phase))
    set_bone_world_rot(rig, "spine_02", 1.2, -1.0 * math.sin(phase), 3.2 * math.cos(phase))
    set_bone_world_rot(rig, "spine_03", 0.8, -0.6 * math.sin(phase), 3.0 * math.cos(phase))
    # Stabilize head upright toward travel direction.
    set_bone_world_rot(rig, "neck_01", -1.5, 0.0, -1.5 * math.cos(phase))
    set_bone_world_rot(rig, "head", -1.5 - 0.8 * math.cos(2.0 * phase), 0.0, -1.5 * math.cos(phase))

    # Legs.
    set_bone_world_rot(rig, "thigh_l", l_hip, -3.5, 0.0)
    set_bone_world_rot(rig, "calf_l", l_knee, 0.0, 0.0)
    set_bone_world_rot(rig, "foot_l", l_ank, 3.5, 0.0)
    set_bone_world_rot(rig, "ball_l", l_toe, 0.0, 0.0)

    set_bone_world_rot(rig, "thigh_r", r_hip, 3.5, 0.0)
    set_bone_world_rot(rig, "calf_r", r_knee, 0.0, 0.0)
    set_bone_world_rot(rig, "foot_r", r_ank, -3.5, 0.0)
    set_bone_world_rot(rig, "ball_r", r_toe, 0.0, 0.0)

    # Counter-swinging arms: left leg forward (phase=0) -> left arm BACK (rx>0), right arm FORWARD (rx<0).
    arm_l = 14.0 * math.cos(phase) - 2.0
    arm_r = -14.0 * math.cos(phase) - 2.0
    # True in-plane elbow flexion: ~12 deg when swinging back, ~30 deg when swinging forward.
    elb_l = 12.0 + 18.0 * max(0.0, -math.cos(phase))
    elb_r = 12.0 + 18.0 * max(0.0, math.cos(phase))
    set_bone_world_rot(rig, "upperarm_l", arm_l, 33.0, 0.0)
    set_elbow_flex(rig, "l", elb_l)
    set_bone_world_rot(rig, "upperarm_r", arm_r, -33.0, 0.0)
    set_elbow_flex(rig, "r", elb_r)


def pose_talk(rig, phase: float):
    pose_idle(rig, phase)
    g1 = 0.5 + 0.5 * math.sin(phase * 2.0)
    g2 = math.sin(phase * 3.0 + 0.6)
    nod = math.sin(phase * 2.0 + 1.1)
    set_bone_world_rot(rig, "spine_02", 1.2, 1.0 * math.sin(phase), 3.0 * math.sin(phase))
    set_bone_world_rot(rig, "neck_01", 2.0 * nod, 0.0, 3.0 * math.sin(phase))
    set_bone_world_rot(rig, "head", 4.0 * nod, 2.0 * math.sin(phase), 4.5 * math.sin(phase))
    # Expressive conversational right-hand gesture IN FRONT OF CHEST with natural elbow flexion & palm inward.
    set_bone_world_rot(rig, "upperarm_r", -16.0 - 8.0 * g1, -30.0 - 3.0 * g2, -14.0)
    set_elbow_flex(rig, "r", 64.0 + 16.0 * g2, supinate_deg=-18.0)
    set_bone_world_rot(rig, "hand_r", -5.0 * g2, -6.0, -8.0 * g1)
    # Relaxed supportive left arm poised gently forward.
    set_bone_world_rot(rig, "upperarm_l", -8.0 - 5.0 * (1.0 - g1), 32.0, 8.0)
    set_elbow_flex(rig, "l", 34.0 + 10.0 * math.sin(phase * 2.0 + 2.0), supinate_deg=12.0)


def render_preview(out_png: Path, rig, height_m: float, action_name: str = None, frame_ratio: float = 0.25, closeup: bool = False):
    """Render a neutral studio Cycles CPU check image (front-3/4 full body or close-up portrait)."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24 if closeup else 18
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 576
    scene.render.resolution_y = 768
    scene.render.filepath = str(out_png)
    scene.world = bpy.data.worlds.new("PreviewWorld")
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.35, 0.42, 0.50, 1.0)
        bg.inputs["Strength"].default_value = 0.72

    sun_data = bpy.data.lights.new("KeySun", type="SUN")
    sun_data.energy = 3.5
    sun_obj = bpy.data.objects.new("KeySun", sun_data)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = Euler((math.radians(48), math.radians(15), math.radians(-38)), "XYZ")

    cam_data = bpy.data.cameras.new("PreviewCam")
    cam_data.lens = 75.0 if closeup else 55.0
    cam_obj = bpy.data.objects.new("PreviewCam", cam_data)
    scene.collection.objects.link(cam_obj)
    if closeup:
        target = Vector((0.0, 0.0, height_m * 0.87))
        cam_obj.location = Vector((0.36, -1.05, height_m * 0.89))
    else:
        target = Vector((0.0, 0.0, height_m * 0.52))
        cam_obj.location = Vector((1.15, -2.65, height_m * 0.58))
    direction = target - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam_obj

    act = bpy.data.actions.get(action_name) if action_name else None
    if act is not None:
        if rig.animation_data is None:
            rig.animation_data_create()
        for tr in rig.animation_data.nla_tracks:
            tr.mute = True
        rig.animation_data.action = act
        f0, f1 = act.frame_range
        scene.frame_set(int(round(f0 + (f1 - f0) * frame_ratio)))
    else:
        reset_pose(rig)
        apply_relaxed_stance(rig)
        pose_walk(rig, 0.65)
    bpy.context.view_layer.update()
    bpy.ops.render.render(write_still=True)

    # Restore rest pose and NLA tracks before export.
    if rig.animation_data is not None:
        rig.animation_data.action = None
        for tr in rig.animation_data.nla_tracks:
            tr.mute = False
    reset_pose(rig)
    bpy.data.objects.remove(cam_obj, do_unlink=True)
    bpy.data.objects.remove(sun_obj, do_unlink=True)


def author_archetype(arch: dict, out_dir: Path, canonical_rig: str, do_preview: bool, mocap_root: Path = None, wardrobe_kit_root: Path = None):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.preferences.addon_enable(module="bl_ext.blender_org.mpfb")
    AssetService.update_all_asset_lists()

    macro = TargetService.get_default_macro_info_dict()
    m = arch["macro"]
    for k in ("gender", "age", "muscle", "weight", "proportions", "height"):
        if k in m:
            macro[k] = float(m[k])
    macro["race"] = {
        "african": float(m.get("african", 0.33)),
        "asian": float(m.get("asian", 0.33)),
        "caucasian": float(m.get("caucasian", 0.34)),
    }

    human = HumanService.create_human(
        mask_helpers=True,
        detailed_helpers=True,
        extra_vertex_groups=True,
        feet_on_ground=True,
        scale=0.1,
        macro_detail_dict=macro,
    )
    skin_path = find_asset("skins", arch["skin"])
    HumanService.set_character_skin(skin_path, human, skin_type="MAKESKIN", material_instances=False)
    rig = HumanService.add_builtin_rig(human, canonical_rig, import_weights=True)

    equipped = [human]

    def equip(kind: str, stem: str, asset_type: str, role_prefix: str, tint=None, roughness=0.75, alpha=False, override_tex=None):
        if not stem:
            return None
        path = find_asset(kind, stem)
        obj = HumanService.add_mhclo_asset(
            path,
            human,
            asset_type=asset_type,
            subdiv_levels=0,
            material_type="MAKESKIN",
            set_up_rigging=True,
            interpolate_weights=True,
            import_subrig=False,
            import_weights=True,
        )
        for mat in obj.data.materials:
            normalize_material(mat, role_prefix, tint=tint, roughness=roughness, alpha_blend=alpha, override_diffuse_path=override_tex)
        equipped.append(obj)
        return obj

    for mat in human.data.materials:
        normalize_material(mat, "EX_SKIN", tint=None, roughness=0.52, alpha_blend=False)

    # Resolve distinct iris texture from MPFB2 eyes/materials/<eye_material>_eye.png when specified.
    eye_tex = None
    eye_mat_name = arch.get("eye_material")
    if eye_mat_name:
        eyes_path = Path(find_asset("eyes", arch.get("eyes", "high-poly")))
        cand = eyes_path.parents[1] / "materials" / f"{eye_mat_name}_eye.png"
        if cand.exists():
            eye_tex = str(cand)

    eyes_obj = equip("eyes", arch.get("eyes", "high-poly"), "Eyes", "EX_EYE", tint=None, roughness=0.05, alpha=False, override_tex=eye_tex)
    equip("eyebrows", arch.get("eyebrows"), "Eyebrows", "EX_HAIR", tint=arch.get("hair_color"), roughness=0.58, alpha=True)
    lashes_obj = equip("eyelashes", arch.get("eyelashes"), "Eyelashes", "EX_HAIR", tint=arch.get("hair_color"), roughness=0.55, alpha=True)

    styleb = arch.get("styleb")
    use_styleb_hair = bool(styleb and styleb.get("hair_style"))
    use_styleb_wardrobe = bool(styleb and wardrobe_kit_root is not None and (wardrobe_kit_root / "jacket.glb").exists())

    clothing_objs = set()
    if not use_styleb_hair:
        equip("hair", arch.get("hair"), "Hair", "EX_HAIR", tint=arch.get("hair_color"), roughness=0.52, alpha=True)
    if not use_styleb_wardrobe:
        for cloth_stem in arch.get("clothes", []):
            cobj = equip("clothes", cloth_stem, "Clothes", "EX_CLOTH", tint=arch.get("cloth_tint"), roughness=0.82, alpha=False)
            if cobj is not None:
                clothing_objs.add(cobj)
        equip("clothes", arch.get("shoes"), "Clothes", "EX_LEATHER", tint=[0.28, 0.24, 0.22], roughness=0.44, alpha=False)

    bone_names = set(rig.data.bones.keys())
    for obj in equipped:
        apply_mask_and_cleanup_modifiers(obj)
        clean_vertex_groups(obj, bone_names)

    z0, z1 = bake_world_origin_and_ground(rig, equipped)
    # Add 4 canonical arm twist bones FIRST so fitted Style B garments inherit twist weights automatically!
    add_arm_twist_bones_and_polish_weights(rig, equipped, clothing_objs)
    # Add 2 canonical upper-eyelid blink bones (59-bone canonical rig) for natural asynchronous blinking!
    equip_styleb.add_eyelid_blink_bones(rig, human, eyes_obj, lashes_obj)

    if use_styleb_hair:
        tex_dir = out_dir / "shared_textures"
        hair_obj = hair_cards.build_styleb_hair(
            human,
            rig,
            styleb["hair_style"],
            arch.get("hair_color", [0.18, 0.13, 0.09]),
            tex_dir,
            seed=int(styleb.get("hair_seed", 42)),
        )
        equipped.append(hair_obj)

    if use_styleb_wardrobe:
        trousers_obj = equip_styleb.build_styleb_trousers(
            human,
            rig,
            pants_rgb=styleb.get("pants_color", [0.24, 0.26, 0.32]),
        )
        jacket_obj = equip_styleb.equip_styleb_jacket(
            human,
            rig,
            wardrobe_kit_root / "jacket.glb",
            main_rgb=styleb.get("jacket_main", [0.84, 0.80, 0.71]),
            accent_rgb=styleb.get("jacket_accent", [0.28, 0.34, 0.44]),
            trim_rgb=styleb.get("jacket_trim", [0.39, 0.47, 0.38]),
            trousers_obj=trousers_obj,
        )
        boot_objs = equip_styleb.equip_styleb_boots(human, rig, wardrobe_kit_root / "boot.glb")
        acc_objs = equip_styleb.equip_styleb_belt_and_satchel(
            rig,
            jacket_obj,
            wardrobe_kit_root / "satchel.glb",
            with_satchel=bool(styleb.get("satchel", False)),
            with_belt=bool(styleb.get("belt", True)),
        )
        equip_styleb.hide_covered_body_skin(human, rig)
        equipped.extend([jacket_obj, trousers_obj] + boot_objs + acc_objs)
        z0, z1 = bake_world_origin_and_ground(rig, equipped)

    height_m = z1 - z0

    # Author canonical clips before exporting.
    animated_bones = [
        "pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "head",
        "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l",
        "clavicle_r", "upperarm_r", "lowerarm_r", "hand_r",
        "thigh_l", "calf_l", "foot_l", "ball_l",
        "thigh_r", "calf_r", "foot_r", "ball_r",
    ]
    for side in ("l", "r"):
        for finger in ("thumb", "index", "middle", "ring", "pinky"):
            for seg in ("01", "02", "03"):
                animated_bones.append(f"{finger}_{seg}_{side}")

    arch_dir = out_dir / "sources" / arch["id"]
    arch_dir.mkdir(parents=True, exist_ok=True)

    mocap_clips = arch.get("mocap_clips")
    clip_meta = {}
    if mocap_clips and mocap_root is not None:
        for cname in ("idle", "walk", "talk"):
            spec = mocap_clips[cname]
            bvh_path = mocap_root / spec["bvh"]
            if not bvh_path.exists():
                raise FileNotFoundError(f"Missing CMU MoCap BVH: {bvh_path}")
            clip_meta[cname] = retarget_mocap.retarget_bvh_to_action(
                rig,
                equipped,
                bvh_path,
                cname,
                int(spec["start"]),
                int(spec["end"]),
                mode=cname,
                target_fps=30,
            )
            print(f"[author_mpfb2] {arch['id']} MoCap {cname}: {clip_meta[cname]}")
    else:
        build_clip(rig, "idle", frames=90, fps=30, pose_fn=pose_idle, animated_bones=animated_bones)
        build_clip(rig, "walk", frames=32, fps=30, pose_fn=pose_walk, animated_bones=animated_bones)
        build_clip(rig, "talk", frames=120, fps=30, pose_fn=pose_talk, animated_bones=animated_bones)

    if do_preview:
        render_preview(arch_dir / "preview.png", rig, height_m, action_name="walk", frame_ratio=0.22)
        render_preview(arch_dir / "preview_talk.png", rig, height_m, action_name="talk", frame_ratio=0.35)
        render_preview(arch_dir / "preview_closeup.png", rig, height_m, action_name="talk", frame_ratio=0.18, closeup=True)

    # Export clean glTF 2.0 (.glb) with Y-up standard, tangents, skins and all NLA animation strips.
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    for obj in equipped:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = rig

    glb_path = arch_dir / f"{arch['id']}.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_apply=False,
        export_texcoords=True,
        export_normals=True,
        export_tangents=True,
        export_materials="EXPORT",
        export_skins=True,
        export_all_influences=False,
        export_animations=True,
        export_animation_mode="NLA_TRACKS",
        export_optimize_animation_size=False,
    )

    tri_count = sum(len(o.data.polygons) for o in equipped)
    meta = {
        "id": arch["id"],
        "label": arch["label"],
        "canonical_rig": canonical_rig,
        "bones": len(rig.data.bones),
        "height_m": round(height_m, 4),
        "ground_min_z": round(z0, 5),
        "polygons": tri_count,
        "mocap": clip_meta,
        "glb": str(glb_path),
        "glb_sha256": sha256_file(glb_path),
    }
    (arch_dir / "source.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[author_mpfb2] {arch['id']}: height={height_m:.3f}m z0={z0:.4f}m bones={len(rig.data.bones)} polys={tri_count} -> {glb_path}")
    return meta


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--recipe", default="assets/characters/spaceport_m1.json")
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", default=None, help="Optional single archetype id")
    ap.add_argument("--no-preview", action="store_true")
    args = ap.parse_args(argv)

    recipe_path = Path(args.recipe).resolve()
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    out_dir = Path(args.out or recipe["output_root"])
    out_dir.mkdir(parents=True, exist_ok=True)
    mocap_root = Path(recipe["mocap_root"]) if recipe.get("mocap_root") else None
    wardrobe_kit_root = Path(recipe["wardrobe_kit_root"]) if recipe.get("wardrobe_kit_root") else None

    results = []
    for arch in recipe["archetypes"]:
        if args.only and arch["id"] != args.only:
            continue
        results.append(author_archetype(arch, out_dir, recipe["canonical_rig"], not args.no_preview, mocap_root=mocap_root, wardrobe_kit_root=wardrobe_kit_root))

    summary_path = out_dir / "sources" / "summary.json"
    summary_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"[author_mpfb2] wrote {len(results)} archetypes to {summary_path}")


if __name__ == "__main__":
    main()
