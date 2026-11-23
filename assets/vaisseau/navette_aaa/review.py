"""Review renders of a shuttle scene: beauty, clay and true-edge wireframe.

Run:  blender -b <scene.blend> --python review.py -- <out_dir> [--views a,b] [--modes beauty,clay,wire,zebra]
          [--cam "name;lx,ly,lz;tx,ty,tz;lens[;noglass]"]... [--res 1440x960] [--only Prefix,Prefix] [--floor]
          [--pose Train=0.5,Aerofrein=1] [--tag suffix] [--film Train]
The scene is never saved. --pose freezes the animation clips at the given phases (0 rest, 1 end).
--film renders one clip as an MP4 per view instead of stills, the other clips held at rest. Views are named cameras in VIEWS (metres, nose -Y, up +Z, port +X);
--cam adds a camera from a location and a target, and alone renders only the added cameras.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anim

# name: (camera location, target, lens mm or None for ortho, ortho scale, hide glass)
VIEWS = {
    # whole ship
    "ens_avant_3q":     ((12.6, -10.4, 2.0), (0.0, -0.4, -0.2), 50, 0, False),
    "ens_arriere_3q":   ((11.9, 14.0, -0.4), (0.0, 0.2, 0.1), 55, 0, False),
    "ens_profil":       ((19.0, 0.0, 0.1), (0.0, 0.0, 0.1), None, 16.5, False),
    "ens_dessus":       ((0.0, 0.0, 20.0), (0.0, 0.0, 0.0), None, 16.0, False),
    "ens_dessous":      ((0.0, 0.0, -20.0), (0.0, 0.0, 0.0), None, 16.0, False),
    "ens_face":         ((0.0, -19.0, 0.0), (0.0, 0.0, 0.0), None, 8.0, False),
    "ens_poupe":        ((0.0, 19.0, 0.0), (0.0, 0.0, 0.0), None, 8.0, False),
    "ens_concept":      ((10.5, -11.5, 0.2), (0.0, 0.2, -0.3), 50, 0, False),
    "concept":          ((12.6, -14.2, 1.3), (0.2, 0.2, -0.75), 40, 0, False),
    # canopy
    "verr_nez":         ((3.6, -8.6, 0.6), (0.0, -5.2, -0.4), 50, 0, False),
    "verr_flanc":       ((6.0, -3.0, 0.5), (1.2, -2.6, -0.1), 50, 0, False),
    "verr_pointe_ar":   ((4.2, -0.4, 0.5), (1.35, -0.9, 0.05), 60, 0, False),
    "verr_pointe_gros": ((2.9, -0.2, 0.35), (1.42, -0.75, 0.08), 85, 0, False),
    "verr_sourcil":     ((3.4, -5.6, 2.4), (0.3, -3.4, 0.5), 55, 0, False),
    "verr_dessus":      ((0.0, -3.4, 9.0), (0.0, -3.4, 0.0), None, 7.2, False),
    "verr_proue":       ((4.4, -6.4, -0.3), (1.0, -4.2, -1.05), 55, 0, False),
    "verr_coin_seuil":  ((3.0, -4.6, -0.2), (1.25, -3.72, -0.78), 85, 0, False),
    "verr_quille":      ((1.8, -6.6, -3.0), (0.0, -4.6, -1.7), 55, 0, False),
    # hull
    "nez_pointe":       ((1.6, -8.6, -0.2), (0.0, -6.7, -0.75), 70, 0, False),
    "flanc_milieu":     ((7.5, 1.0, 0.4), (1.9, 0.8, -0.3), 50, 0, False),
    "tuyere_3q":        ((6.8, 7.6, -0.4), (1.75, 2.6, -0.75), 65, 0, False),
    "tuyere_gros":      ((4.6, 5.6, -0.5), (1.85, 2.9, -0.75), 85, 0, False),
    "tuyere_dessous":   ((7.3, 2.4, -3.3), (1.6, 2.4, -0.65), 60, 0, False),
    "tuyere_profil":    ((9.0, 2.6, -0.75), (1.6, 2.6, -0.75), None, 3.2, False),
    "poupe_3q":         ((5.2, 11.6, 1.6), (0.0, 6.2, 0.1), 60, 0, False),
    "poupe_gros":       ((1.6, 9.6, 0.9), (0.0, 6.8, 0.2), 70, 0, False),
    "poupe_haut":       ((4.2, 10.4, 3.4), (0.0, 5.6, 0.3), 50, 0, False),
    "trappe_ar":        ((4.5, 11.5, -1.2), (0.0, 4.8, -1.6), 45, 0, False),
    "trappe_profil":    ((10.0, 4.6, -1.6), (0.0, 4.6, -1.6), None, 5.0, False),
    "frein_ar":         ((4.6, 9.6, 3.3), (0.0, 4.9, 1.75), 60, 0, False),
    "frein_gros":       ((1.9, 7.9, 2.4), (0.05, 5.0, 1.8), 70, 0, False),
    "derive_3q":        ((6.8, 4.7, 3.0), (0.6, 4.2, 1.1), 55, 0, False),
    # wings
    "aile_3q":          ((9.0, -6.5, 5.0), (0.6, 1.6, -0.4), 40, 0, False),
    "aile_saumon":      ((6.5, 2.0, 1.6), (3.2, 4.5, -0.3), 45, 0, False),
    "aile_dessous":     ((7.0, 1.0, -4.0), (2.2, 3.2, -0.5), 40, 0, False),
    "aile_arriere":     ((6.5, 12.0, 4.5), (0.4, 3.0, -0.4), 40, 0, False),
    "derive_pied":      ((3.4, -0.6, 2.2), (0.0, 1.0, 0.75), 60, 0, False),
    "derive_saumon":    ((3.4, 8.6, 3.4), (0.0, 6.2, 2.5), 75, 0, False),
    "radiateur":        ((3.6, 6.4, 2.2), (0.8, 5.0, 0.45), 70, 0, False),
    "ventre_3q":        ((10.4, 10.4, -8.3), (0.0, 0.6, -0.6), 52, 0, False),
    # gear
    "train_principal":  ((6.5, 0.9, -2.15), (1.45, 1.6, -1.95), 55, 0, False),
    "train_avant":      ((3.6, -6.6, -2.2), (0.0, -3.9, -2.0), 60, 0, False),
    "puits_principal":  ((4.6, 3.6, -2.5), (1.1, 1.5, -1.5), 50, 0, False),
    "patin_gros":       ((3.6, 0.6, -2.35), (1.9, 1.7, -2.45), 70, 0, False),
    # interior (glass hidden)
    "int_poste":        ((0.95, -3.75, 0.05), (0.0, -4.85, -0.62), 35, 0, True),
    "int_pilote_pov":   ((0.0, -4.05, -0.20), (0.0, -5.6, -0.62), 22, 0, True),
    "int_console":      ((0.42, -4.35, -0.25), (0.0, -4.95, -0.62), 50, 0, True),
    "int_siege_pilote": ((1.25, -5.0, -0.1), (0.0, -4.15, -0.75), 40, 0, True),
    "int_cabine_3q":    ((2.9, -4.3, 0.85), (0.0, -2.2, -0.55), 38, 0, True),
    "int_siege_gros":   ((1.75, -2.7, -0.25), (0.66, -2.38, -0.8), 55, 0, True),
    "int_cloison":      ((0.0, -3.2, -0.25), (0.0, -0.3, -0.4), 28, 0, True),
    "int_plafond":      ((0.0, -3.6, -0.95), (0.0, -1.7, 0.7), 22, 0, True),
}


def args_after_dashes():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def aim(obj, loc, target, up="Y"):
    obj.location = Vector(loc)
    d = Vector(target) - Vector(loc)
    if abs(d.normalized().z) > 0.999:
        up = "X"
    obj.rotation_euler = d.normalized().to_track_quat("-Z", up).to_euler()


def area_light(scene, name, loc, target, energy, size, color):
    data = bpy.data.lights.new(name, type="AREA")
    data.energy, data.size, data.color = energy, size, color
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    aim(obj, loc, target)
    return obj


def flat_material(name, rgb, rough=0.55, emit=0.0):
    mat = bpy.data.materials.new(name)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emit
    return mat


def main():
    argv = args_after_dashes()
    out_dir = argv[0]
    wanted = list(VIEWS)
    custom = []
    modes = ["beauty", "clay", "wire"]
    res = (1440, 960)
    for i, a in enumerate(argv):
        if a == "--views":
            wanted = [v for v in argv[i + 1].split(",") if v]
        if a == "--modes":
            modes = argv[i + 1].split(",")
        if a == "--res":
            res = tuple(int(x) for x in argv[i + 1].split("x"))
        if a == "--cam":            # "name;lx,ly,lz;tx,ty,tz;lens[;noglass]" (lens 0 = ortho, scale 8 m)
            f = argv[i + 1].split(";")
            vec = lambda t: tuple(float(v) for v in t.split(","))
            lens = float(f[3])
            VIEWS[f[0]] = (vec(f[1]), vec(f[2]), lens or None, 8.0, len(f) > 4 and f[4] == "noglass")
            custom.append(f[0])
    wanted = custom if (custom and "--views" not in argv) else wanted + custom
    os.makedirs(out_dir, exist_ok=True)
    tag = argv[argv.index("--tag") + 1] if "--tag" in argv else ""
    if "--pose" in argv:
        anim.show({k: float(v) for k, v in (item.split("=") for item in argv[argv.index("--pose") + 1].split(","))})

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass

    world = bpy.data.worlds.new("ReviewWorld")
    scene.world = world
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.74, 0.77, 0.81, 1.0)
    bg.inputs[1].default_value = 0.42

    c = (0.0, 0.0, 0.0)
    area_light(scene, "R_Key", (16.0, -10.0, 14.0), c, 4200, 5.0, (1.0, 0.98, 0.94))
    sun_data = bpy.data.lights.new("R_Sun", type="SUN")         # a soft sun: it grounds the ship with a shadow
    sun_data.energy, sun_data.angle, sun_data.color = 4.5, math.radians(7.0), (1.0, 0.97, 0.92)
    sun = bpy.data.objects.new("R_Sun", sun_data)
    scene.collection.objects.link(sun)
    aim(sun, (5.0, -9.0, 16.0), c)
    area_light(scene, "R_Fill", (-16.0, 8.0, 9.0), c, 4500, 14.0, (0.88, 0.94, 1.0))
    area_light(scene, "R_Rim", (4.0, 18.0, 7.0), c, 6000, 9.0, (0.95, 0.98, 1.0))
    area_light(scene, "R_Under", (10.0, 10.0, -9.0), c, 2600, 11.0, (0.92, 0.94, 0.98))
    area_light(scene, "R_Cabin", (0.0, -2.5, 0.45), (0.0, -2.8, -1.2), 140, 2.4, (1.0, 0.90, 0.78))

    floor = None
    if "--floor" in argv:                # a matte studio floor under the footpads, in the beauty pass
        bpy.ops.mesh.primitive_plane_add(size=120.0, location=(0.0, 0.0, -2.6392))
        floor = bpy.context.active_object
        floor.name = "ReviewFloor"
        floor.data.materials.append(flat_material("ReviewFloorMat", (0.50, 0.52, 0.55), 0.9))

    cam_data = bpy.data.cameras.new("ReviewCam")
    cam_data.clip_start, cam_data.clip_end = 0.02, 200.0
    cam = bpy.data.objects.new("ReviewCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    if "--only" in argv:                 # keep only the objects whose name starts with one of the prefixes
        keep = tuple(argv[argv.index("--only") + 1].split(","))
        for o in [o for o in scene.objects if o.type == "MESH" and not o.name.startswith(keep)]:
            bpy.data.objects.remove(o, do_unlink=True)
    meshes = [o for o in scene.objects if o.type == "MESH" and o is not floor]
    glass = [o for o in meshes if "Vitre" in o.name or o.name == "Nez_Embout"
             or any(m and ("Glass" in m.name or "Verre" in m.name) for m in o.data.materials)]
    for o in meshes:                       # a mesh without a slot would ignore the clay override
        if not o.material_slots:
            o.data.materials.append(None)
    original = {o.name: [s.material for s in o.material_slots] for o in meshes}

    clay = flat_material("ReviewClay", (0.30, 0.31, 0.33), 0.32)
    # Zebra: black and white bands of the reflected direction. Lumps bend the bands.
    zebra = bpy.data.materials.new("ReviewZebra")
    nt = zebra.node_tree
    nt.nodes.clear()
    coord = nt.nodes.new("ShaderNodeTexCoord")
    split = nt.nodes.new("ShaderNodeSeparateXYZ")
    wave = nt.nodes.new("ShaderNodeMath")
    wave.operation = "SINE"
    scale = nt.nodes.new("ShaderNodeMath")
    scale.operation = "MULTIPLY"
    scale.inputs[1].default_value = 34.0
    edge = nt.nodes.new("ShaderNodeMath")
    edge.operation = "GREATER_THAN"
    edge.inputs[1].default_value = 0.0
    emit = nt.nodes.new("ShaderNodeEmission")
    out_node = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(coord.outputs["Reflection"], split.inputs[0])
    nt.links.new(split.outputs["Z"], scale.inputs[0])
    nt.links.new(scale.outputs[0], wave.inputs[0])
    nt.links.new(wave.outputs[0], edge.inputs[0])
    nt.links.new(edge.outputs[0], emit.inputs["Color"])
    nt.links.new(emit.outputs[0], out_node.inputs["Surface"])
    ink = flat_material("ReviewInk", (0.0, 0.0, 0.0), 1.0)
    wires = []

    def set_mode(mode):
        # Clay and wire read the form: darker, glossier, less exposed than the beauty pass.
        scene.view_settings.exposure = 0.0 if mode in ("beauty", "zebra") else -0.7
        override = {"clay": clay, "wire": clay, "zebra": zebra}.get(mode)
        for o in meshes:
            for slot, mat in zip(o.material_slots, original[o.name]):
                slot.material = override or mat
        for w in wires:
            w.hide_render = mode != "wire"
        if floor is not None:
            floor.hide_render = mode != "beauty"
        if mode == "wire" and not wires:
            for o in meshes:
                w = o.copy()
                w.data = o.data.copy()
                w.name = "W_" + o.name
                scene.collection.objects.link(w)
                w.data.materials.clear()
                w.data.materials.append(ink)
                mod = w.modifiers.new("Wire", "WIREFRAME")
                mod.thickness = 0.004
                mod.use_replace = True
                mod.use_even_offset = False
                mod.use_boundary = True
                w["of"] = o.name
                wires.append(w)

    if "--film" in argv:                 # one clip played forward, then held, in the beauty pass
        clip = argv[argv.index("--film") + 1]
        for owner in anim.animated():
            for track in owner.animation_data.nla_tracks:
                track.mute = track.name != clip
        set_mode("beauty")
        scene.frame_start, scene.frame_end = 0, anim.CLIPS[clip] + anim.FPS // 2
        scene.render.fps = anim.FPS
        scene.eevee.taa_render_samples = 16
        scene.render.image_settings.media_type = "VIDEO"
        scene.render.ffmpeg.format, scene.render.ffmpeg.codec = "MPEG4", "H264"
        scene.render.ffmpeg.constant_rate_factor = "HIGH"
        for name in wanted:
            loc, target, lens, ortho_scale, hide_glass = VIEWS[name]
            if lens is None:
                cam_data.type, cam_data.ortho_scale = "ORTHO", ortho_scale
            else:
                cam_data.type, cam_data.lens = "PERSP", lens
            aim(cam, loc, target)
            scene.render.filepath = os.path.join(out_dir, f"{name}_{clip}{tag}.mp4")
            bpy.ops.render.render(animation=True)
            print("REVIEW", scene.render.filepath)
        return

    for mode in modes:
        set_mode(mode)
        for name in wanted:
            loc, target, lens, ortho_scale, hide_glass = VIEWS[name]
            if lens is None:
                cam_data.type, cam_data.ortho_scale = "ORTHO", ortho_scale
            else:
                cam_data.type, cam_data.lens = "PERSP", lens
            aim(cam, loc, target)
            # Clay and wire views read the opaque surfaces: the glass hides in interior views only.
            for g in glass:
                g.hide_render = hide_glass
            for w in wires:
                if w.get("of") in {g.name for g in glass}:
                    w.hide_render = hide_glass or mode != "wire"
            scene.render.filepath = os.path.join(out_dir, f"{name}_{mode}{tag}.png")
            bpy.ops.render.render(write_still=True)
            print("REVIEW", scene.render.filepath)


if __name__ == "__main__":
    main()
