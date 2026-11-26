"""Inspect exact Pad 43 furniture local anchor frames & render orthographic contact reference in Blender."""
import json
from pathlib import Path
import bpy
from mathutils import Vector

ASSETS = {
    "planted_bench": Path(r"E:\ExoluneAssets\city-tripo-2026-11-11\delivery-04\models\planted_bench\master.glb"),
    "planted_bench_wild": Path(r"E:\ExoluneAssets\city-tripo-2026-11-11\delivery-04\models\planted_bench_wild\master.glb"),
    "sorting_station": Path(r"E:\ExoluneAssets\city-tripo-2026-11-11\delivery-07\models\sorting_station\master.glb"),
    "service_cabinet": Path(r"E:\ExoluneAssets\city-tripo-2026-11-11\delivery-04\models\service_cabinet\master.glb"),
}

OUT_DIR = Path(r"E:\ExoluneAssets\characters-m1-2026-11-21\cast-20\furniture_audit")
OUT_DIR.mkdir(parents=True, exist_ok=True)

report = {}
for name, glb in ASSETS.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    # Render front (-Y), back (+Y), and 3/4 view to inspect exact seat side & front controls
    bpy.ops.object.light_add(type="SUN", location=(4, -6, 8))
    bpy.context.active_object.data.energy = 3.0
    world = bpy.data.worlds.new("W")
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.35, 0.40, 0.45, 1.0)
    cam_d = bpy.data.cameras.new("C")
    cam = bpy.data.objects.new("C", cam_d)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    bpy.context.scene.render.engine = "BLENDER_EEVEE"
    bpy.context.scene.render.resolution_x = 640
    bpy.context.scene.render.resolution_y = 480

    # Compute exact world bounds after glTF Y-up->Z-up import
    deps = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in meshes:
        mw = o.matrix_world
        for v in o.data.vertices:
            pts.append(mw @ v.co)
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    ctr = 0.5 * (lo + hi)

    for tag, eye in (("negY", ctr + Vector((0.8, -4.2, 1.4))), ("posY", ctr + Vector((-0.8, 4.2, 1.4)))):
        cam.location = eye
        cam.rotation_euler = (ctr - eye).normalized().to_track_quat("-Z", "Y").to_euler()
        bpy.context.scene.render.filepath = str(OUT_DIR / f"{name}_{tag}.png")
        bpy.ops.render.render(write_still=True)

    # Probe downward raycast heights across grid to locate flat horizontal surfaces (bench seat / cabinet ledge)
    seat_hits = []
    for ix in range(-15, 16):
        x = ix * 0.1
        for iy in range(-6, 7):
            y = iy * 0.1
            best_z = None
            for o in meshes:
                res, loc, nrm, _ = o.ray_cast(o.matrix_world.inverted() @ Vector((x, y, 1.6)), (0, 0, -1))
                if res:
                    wl = o.matrix_world @ loc
                    wn = (o.matrix_world.to_3x3() @ nrm).normalized()
                    if 0.36 <= wl.z <= 0.56 and wn.z > 0.85:
                        best_z = wl.z if best_z is None else max(best_z, wl.z)
            if best_z is not None:
                seat_hits.append((round(x, 2), round(y, 2), round(best_z, 3)))
    report[name] = {
        "lo": [round(lo.x, 3), round(lo.y, 3), round(lo.z, 3)],
        "hi": [round(hi.x, 3), round(hi.y, 3), round(hi.z, 3)],
        "seat_hits": seat_hits[:30],
    }

(OUT_DIR / "furniture_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("WROTE", OUT_DIR / "furniture_report.json")
