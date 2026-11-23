"""Build the Navette AAA scene.

Run:  blender -b --factory-startup --python build.py -- <out.blend> [--with gear,interior,airlock] [--glb]
Sources stay in this directory; the scene, its GLB and the review captures go outside Git.
"""
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anim
import details
import frames
import hullgrid as hg
import materials
import meshkit
import panels
import tail
import thrusters
import wings


def skin_objects(grid, mats):
    """Hull and canopy glass from the conformed grid, both sides welded on the centreline."""
    na, nb = grid.na, grid.nb
    port = np.arange(na * nb).reshape(na, nb)
    stbd = port.copy()
    stbd[:, 1:-1] = na * nb + np.arange(na * (nb - 2)).reshape(na, nb - 2)
    flip = np.array([-1.0, 1.0, 1.0])
    pts = np.vstack([grid.points.reshape(-1, 3), (grid.points[:, 1:-1] * flip).reshape(-1, 3)])
    nrm = np.vstack([grid.normals.reshape(-1, 3), (grid.normals[:, 1:-1] * flip).reshape(-1, 3)])
    uv_half = np.stack([grid.lam, grid.girth], axis=-1)
    uvs = np.vstack([uv_half.reshape(-1, 2), (uv_half[:, 1:-1] * np.array([1.0, -1.0])).reshape(-1, 2)])

    cells = grid.cells()
    hull_cells = ~(cells["glass"] | cells["mouth"] | cells["doors"] | cells["hatch"])
    paint = np.zeros(hull_cells.shape, dtype=np.int32)             # 0 pearl white
    paint[cells["belly"]] = 2                                      # 2 pale belly
    paint[cells["belt"] | cells["bezel"] | cells["prow"] | wings.under_cells(grid)] = 1    # 1 teal

    def part(name, mask, col, slots, face_mats=None):
        faces = np.vstack([meshkit.grid_faces(port, mask), meshkit.grid_faces(stbd, mask)])
        used = np.unique(faces)
        remap = np.full(len(pts), -1, dtype=np.int64)
        remap[used] = np.arange(len(used))
        fm = None if face_mats is None else np.concatenate([face_mats[mask], face_mats[mask]])
        return meshkit.mesh_object(name, pts[used], remap[faces], col, materials=slots, face_mats=fm,
                                   normals=nrm[used], uvs=uvs[used])

    hull = part("Coque_Principale", hull_cells, "01_Exterieur_Coque",
                [mats["white"], mats["teal"], mats["belly"], mats["blade"]], paint)
    glass = part("Verriere_Vitre", cells["glass"], "03_Verriere", [mats["glass"]])
    return hull, glass


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    out = args[0]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    mats = materials.library()
    grid = hg.HullGrid()
    hull, _ = skin_objects(grid, mats)
    panels.build(grid, mats)
    frames.canopy(grid, mats)
    frames.opening_returns(grid, mats)
    frames.boss(grid, mats, "Nez_Embout", mats["glass"])            # the bubble ends in glass, ringed in dark
    frames.boss(grid, mats, "Poupe_Feu", mats["amber"], stern=True)
    thrusters.build(grid, mats)
    tail.fin(grid.hull, grid.maps, mats)
    seams = details.build(grid, mats)[0]

    def hull_twin(g):
        twin, glass = skin_objects(g, mats)
        mesh = glass.data
        bpy.data.objects.remove(glass, do_unlink=True)
        bpy.data.meshes.remove(mesh)
        return twin

    wings.build(grid, [(hull, hull_twin), (seams, lambda g: details.seams(g, mats))],
                [bpy.data.objects["Feu_Nav_G"], bpy.data.objects["Feu_Nav_D"]])
    if "--with" in args:                                # modules built apart: gear, interior, airlock
        for name in args[args.index("--with") + 1].split(","):
            __import__(name).build(mats, grid)
    scene.frame_start, scene.frame_end, scene.render.fps = 0, max(anim.CLIPS.values()), anim.FPS
    scene.frame_set(0)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=out)
    meshes = [o for o in scene.objects if o.type == "MESH"]
    tris = sum(len(p.vertices) - 2 for o in meshes for p in o.data.polygons)
    ngons = sum(1 for o in meshes for p in o.data.polygons if len(p.vertices) > 4)
    lo = np.min([np.min([o.matrix_world @ v.co for v in o.data.vertices], axis=0) for o in meshes], axis=0)
    hi = np.max([np.max([o.matrix_world @ v.co for v in o.data.vertices], axis=0) for o in meshes], axis=0)
    print(f"BUILD_SAVED {out} objects={len(meshes)} triangles={tris} ngons={ngons} "
          f"size={np.round(hi - lo, 3).tolist()} min={np.round(lo, 3).tolist()}")
    if "--glb" in args:
        glb = os.path.splitext(out)[0] + ".glb"
        bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_tangents=True,
                                  export_animation_mode="NLA_TRACKS")
        print(f"GLB_SAVED {glb} {os.path.getsize(glb) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
