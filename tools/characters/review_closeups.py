"""Close-view review board of one authored character source, rendered headlessly in Blender (Cycles CPU).

A defect inventory needs each piece seen up close before any native or in-game review (docs/principes.md).
The board frames the face, the collar, both hands, the torso, the hips, the back and the whole figure, in the
rest pose or at a chosen clip frame.

blender --background --python tools/characters/review_closeups.py -- --glb <source.glb> --out <board.png>
    [--clip idle|walk|talk] [--ratio 0.25] [--views close|body|shoulders|skirt]
"""
import argparse
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Vector

TILE = 512
# name, target bone, target offset (m), camera offset from the target (m), lens (mm). The figure faces -Y.
VIEWS = {
    # Each piece up close.
    "close": [
        ("face_front", "head", (0.0, -0.05, 0.075), (0.0, -0.62, 0.0), 68.0),
        ("face_34", "head", (0.0, -0.05, 0.075), (0.42, -0.48, 0.03), 68.0),
        ("collar", "neck_01", (0.0, -0.04, 0.0), (0.16, -0.50, 0.12), 70.0),
        ("torso", "spine_02", (0.0, 0.0, 0.05), (0.0, -1.30, 0.0), 50.0),
        ("hand_l", "middle_01_l", (0.0, 0.0, 0.0), (0.62, -0.18, 0.06), 110.0),
        ("hand_r", "middle_01_r", (0.0, 0.0, 0.0), (-0.62, -0.18, 0.06), 110.0),
        ("hips", "pelvis", (0.0, 0.0, -0.05), (0.30, -1.15, 0.0), 50.0),
        ("back", "spine_02", (0.0, 0.0, -0.25), (-0.55, 2.75, 0.25), 50.0),
    ],
    # The whole figure from its four sides, then its limbs against the garments: for a pose in motion.
    "body": [
        ("front", "pelvis", (0.0, 0.0, 0.05), (0.0, -3.0, 0.15), 50.0),
        ("right", "pelvis", (0.0, 0.0, 0.05), (-3.0, 0.0, 0.15), 50.0),
        ("back", "pelvis", (0.0, 0.0, 0.05), (0.0, 3.0, 0.15), 50.0),
        ("left", "pelvis", (0.0, 0.0, 0.05), (3.0, 0.0, 0.15), 50.0),
        ("legs_front", "pelvis", (0.0, 0.0, -0.45), (0.25, -1.75, 0.0), 50.0),
        ("legs_right", "pelvis", (0.0, 0.0, -0.45), (-1.75, -0.20, 0.0), 50.0),
        ("arm_right", "spine_03", (-0.15, 0.0, -0.10), (-1.25, -0.55, 0.10), 50.0),
        ("arm_left", "spine_03", (0.15, 0.0, -0.10), (1.25, -0.55, 0.10), 50.0),
        ("armhole_right", "spine_03", (-0.14, 0.05, -0.02), (-0.45, 0.95, 0.12), 70.0),
        ("armhole_left", "spine_03", (0.14, 0.05, -0.02), (0.45, 0.95, 0.12), 70.0),
    ],
    # The face as the style reference shows it: front, three-quarter, profile, and from a little below, at eye level.
    "face": [
        ("front", "head", (0.0, -0.03, 0.05), (0.0, -0.75, 0.02), 75.0),
        ("three_quarter", "head", (0.0, -0.03, 0.05), (0.52, -0.55, 0.04), 75.0),
        ("profile", "head", (0.0, -0.01, 0.05), (0.75, 0.0, 0.02), 75.0),
        ("below", "head", (0.0, -0.03, 0.05), (-0.42, -0.60, -0.14), 75.0),
    ],
    # The skirt's front slit and its pockets, from both front quarters: where the panels part with the stride.
    "skirt": [
        ("slit_left", "pelvis", (0.0, -0.10, -0.22), (0.45, -0.85, 0.05), 50.0),
        ("slit_right", "pelvis", (0.0, -0.10, -0.22), (-0.45, -0.85, 0.05), 50.0),
        ("pocket_left", "pelvis", (0.12, -0.08, -0.08), (0.25, -0.55, 0.10), 55.0),
        ("pocket_right", "pelvis", (-0.12, -0.08, -0.08), (-0.25, -0.55, 0.10), 55.0),
    ],
    # Each shoulder at arm's length, from the front and the back, from above: where a sleeve meets its coat.
    "shoulders": [
        ("front_left", "upperarm_l", (0.0, 0.0, 0.0), (0.30, -0.60, 0.22), 60.0),
        ("front_right", "upperarm_r", (0.0, 0.0, 0.0), (-0.30, -0.60, 0.22), 60.0),
        ("back_left", "upperarm_l", (0.0, 0.0, 0.0), (0.30, 0.60, 0.22), 60.0),
        ("back_right", "upperarm_r", (0.0, 0.0, 0.0), (-0.30, 0.60, 0.22), 60.0),
    ],
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--glb", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--clip", default="")
    ap.add_argument("--ratio", type=float, default=0.25)
    ap.add_argument("--views", choices=sorted(VIEWS), default="close")
    args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:])

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(args.glb))
    scene = bpy.context.scene
    rig = next(o for o in scene.objects if o.type == "ARMATURE")
    # The engine skins with dual quaternions (CharacterSkin.hlsl), and so does the board: linear blending hid where a
    # garment's edge and the skin under it part.
    for o in scene.objects:
        for m in o.modifiers:
            if m.type == "ARMATURE":
                m.use_deform_preserve_volume = True

    if args.clip:
        action = next(a for a in bpy.data.actions if args.clip in a.name.lower())
        if rig.animation_data is None:
            rig.animation_data_create()
        for track in rig.animation_data.nla_tracks:
            track.mute = True
        rig.animation_data.action = action
        first, last = action.frame_range
        scene.frame_set(int(round(first + (last - first) * args.ratio)))
    else:
        if rig.animation_data is not None:
            rig.animation_data.action = None
            for track in rig.animation_data.nla_tracks:
                track.mute = True
        for bone in rig.pose.bones:
            bone.matrix_basis.identity()
    bpy.context.view_layer.update()

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = TILE
    scene.world = bpy.data.worlds.new("ReviewWorld")
    background = scene.world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (0.35, 0.42, 0.50, 1.0)
    background.inputs["Strength"].default_value = 0.72
    sun = bpy.data.objects.new("KeySun", bpy.data.lights.new("KeySun", type="SUN"))
    sun.data.energy = 3.5
    sun.rotation_euler = Euler((math.radians(48), math.radians(15), math.radians(-38)), "XYZ")
    scene.collection.objects.link(sun)
    camera = bpy.data.objects.new("ReviewCam", bpy.data.cameras.new("ReviewCam"))
    camera.data.clip_start = 0.02
    scene.collection.objects.link(camera)
    scene.camera = camera

    tiles = []
    for name, bone, offset, eye, lens in VIEWS[args.views]:
        target = rig.matrix_world @ rig.pose.bones[bone].head + Vector(offset)
        camera.location = target + Vector(eye)
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.lens = lens
        path = args.out.with_name(f"{args.out.stem}_{name}.png")
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(str(path))
        tiles.append(np.array(image.pixels[:], dtype=np.float32).reshape(TILE, TILE, 4))
        bpy.data.images.remove(image)

    # Blender stores rows bottom-up: the first four views form the top row.
    half = len(tiles) // 2
    sheet = np.concatenate([np.concatenate(tiles[half:], axis=1), np.concatenate(tiles[:half], axis=1)], axis=0)
    board = bpy.data.images.new("board", width=sheet.shape[1], height=sheet.shape[0], alpha=True)
    board.pixels.foreach_set(sheet.ravel())
    board.filepath_raw = str(args.out)
    board.file_format = "PNG"
    board.save()
    print(f"[review_closeups] {args.out}")


if __name__ == "__main__":
    main()
