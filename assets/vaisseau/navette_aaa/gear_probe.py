"""Build the landing gear into a hull scene, save it under another name, then check it.

Run:  blender -b <hull.blend> --python-exit-code 1 --python gear_probe.py -- <out.blend> [--phases 25]
The hull scene is a build.py scene made without the gear (its doors must be there); it is never
saved over. self_check covers the meshes at rest and the clip "Train": joints, the ground, the
free volume inside the hull, the stowed state under the skin and interference between parts,
the doors, the wells, the hull and its other meshes.
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gear
import hullgrid as hg
import materials


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    out = os.path.abspath(args[0])
    phases = int(args[args.index("--phases") + 1]) if "--phases" in args else 25
    assert out != os.path.abspath(bpy.data.filepath), "refusing to save over the hull scene"
    assert not any(o.name.startswith("Train_") for o in bpy.data.objects), "the scene already has a gear"
    found = {"white": "NAV_Email_Blanc", "belly": "NAV_Email_Ventre"}           # the hull scene's own enamels
    mats = {key: bpy.data.materials[name] for key, name in found.items() if name in bpy.data.materials}
    objs = gear.build(mats or materials.library(), hg.HullGrid())
    bpy.context.scene.frame_set(0)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out)          # saved first: a failed check can still be looked at
    facts = gear.self_check(objs, phases=phases)
    print(f"GEAR_SAVED {out} triangles={facts['triangles']}")


if __name__ == "__main__":
    main()
