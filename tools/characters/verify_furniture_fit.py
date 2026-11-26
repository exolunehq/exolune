"""Render EEVEE side/3-4 contact checks of rigged characters on real delivery-07 furniture."""
import json
import math
from pathlib import Path
import bpy
from mathutils import Euler, Matrix, Vector

OUT_DIR = Path(r"E:\ExoluneAssets\characters-m1-2026-11-21\cast-20\furniture_audit")
ARTIFACT_DIR = Path(r"C:\Users\etien\.gemini\antigravity\brain\ce25e74b-44a2-47ff-81cf-13ca8c48c97e")
PILOT_GLB = Path(r"E:\ExoluneAssets\characters-m1-2026-11-21\cast-20\glbs\crew_lead_aaa.glb")
SECOND_GLB = Path(r"E:\ExoluneAssets\characters-m1-2026-11-21\cast-20\glbs\botanist_f_aaa.glb")

FURN = {
    "planted_bench": Path(r"E:\ExoluneAssets\city-tripo-2026-11-11\delivery-04\models\planted_bench\master.glb"),
    "planted_bench_wild": Path(r"E:\ExoluneAssets\city-tripo-2026-11-11\delivery-04\models\planted_bench_wild\master.glb"),
    "sorting_station": Path(r"E:\ExoluneAssets\city-tripo-2026-11-11\delivery-07\models\sorting_station\master.glb"),
    "service_cabinet": Path(r"E:\ExoluneAssets\city-tripo-2026-11-11\delivery-04\models\service_cabinet\master.glb"),
}


def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.engine = "BLENDER_EEVEE"
    bpy.context.scene.render.resolution_x = 960
    bpy.context.scene.render.resolution_y = 640
    world = bpy.data.worlds.new("W")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.38, 0.45, 0.52, 1.0)
    bpy.ops.object.light_add(type="SUN", location=(4, -6, 9))
    bpy.context.active_object.data.energy = 3.2
    cam_d = bpy.data.cameras.new("C")
    cam = bpy.data.objects.new("C", cam_d)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


def shoot(cam, eye, tgt, path):
    cam.data.lens = 50.0
    cam.location = eye
    cam.rotation_euler = (Vector(tgt) - Vector(eye)).normalized().to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def import_char(glb_path: Path, loc, local_facing_yaw_deg: float, nla_clip: str):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    objs = [o for o in bpy.data.objects if o not in before]
    arm = [o for o in objs if o.type == "ARMATURE"][0]
    mesh = [o for o in objs if o.type == "MESH"][0]
    # Character exports facing -Y local; yaw -90 deg faces -Y, +90 deg faces +Y.
    # Rotate by (local_facing_yaw_deg + 90) deg around Z in Blender.
    rot_z = math.radians(local_facing_yaw_deg + 90.0)
    arm.location = loc
    arm.rotation_mode = "XYZ"
    arm.rotation_euler = (0.0, 0.0, rot_z)
    if arm.animation_data:
        for tr in arm.animation_data.nla_tracks:
            if tr.name == nla_clip and tr.strips:
                arm.animation_data.action = tr.strips[0].action
                tr.mute = False
            else:
                tr.mute = True
    bpy.context.view_layer.update()
    # Measure hip/thigh/foot world coordinates at frame 60
    bpy.context.scene.frame_set(60)
    bpy.context.view_layer.update()
    lhip = arm.matrix_world @ arm.pose.bones["mixamorig:LeftUpLeg"].head
    lfoot = arm.matrix_world @ arm.pose.bones["mixamorig:LeftFoot"].head
    hips = arm.matrix_world @ arm.pose.bones["mixamorig:Hips"].head
    print(f"[fit] {nla_clip} at {loc}: hips={tuple(round(v,3) for v in hips)}, lUpLegZ={lhip.z:.3f}, lFootZ={lfoot.z:.3f}")
    return arm, mesh


# 1. Bench Fit Check: planted_bench (front) & planted_bench_wild (front)
cam = setup_scene()
bpy.ops.import_scene.gltf(filepath=str(FURN["planted_bench"]))
# Second bench offset in X by +4.5m and rotated 180 so its +Y seat faces camera!
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(FURN["planted_bench_wild"]))
for o in bpy.data.objects:
    if o not in before and o.type == "MESH" and o.parent is None:
        o.location = (4.5, 0.0, 0.0)

import_char(SECOND_GLB, (-0.10, -0.48, 0.0), -90.0, "sit_talk")
import_char(PILOT_GLB, (0.75, -0.48, 0.0), -80.0, "sit_idle")
# On wild bench shifted by +4.5 in X, facing +Y (+90 deg)
import_char(PILOT_GLB, (4.5 - 0.82, 0.46, 0.0), 90.0, "sit_idle")
import_char(SECOND_GLB, (4.5 - 0.10, 0.46, 0.0), 80.0, "sit_talk")

shoot(cam, (0.3, -4.2, 1.5), (0.3, -0.1, 0.75), ARTIFACT_DIR / "furniture_bench_fit.png")
shoot(cam, (4.1, 4.2, 1.5), (4.1, 0.1, 0.75), OUT_DIR / "furniture_bench_wild_fit.png")

# 2. Interact Fit Check: sorting_station & service_cabinet
cam = setup_scene()
bpy.ops.import_scene.gltf(filepath=str(FURN["sorting_station"]))
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(FURN["service_cabinet"]))
for o in bpy.data.objects:
    if o not in before and o.type == "MESH" and o.parent is None:
        o.location = (4.2, 0.0, 0.0)

import_char(PILOT_GLB, (-0.15, -0.84, 0.0), 90.0, "interact_standing")
import_char(PILOT_GLB, (4.2 + 0.32, -0.94, 0.0), 90.0, "interact_standing")
shoot(cam, (2.2, -7.8, 2.0), (2.2, -0.4, 0.95), ARTIFACT_DIR / "furniture_interact_fit.png")
print("SAVED furniture fit verification renders.")
