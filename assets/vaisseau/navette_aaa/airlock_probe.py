"""Probe of the airlock module: check it in a built scene, or build it alone and check it.

Run:  blender -b <scene.blend> --python-exit-code 1 --python airlock_probe.py -- [--strict]
      blender -b --factory-startup --python-exit-code 1 --python airlock_probe.py -- <out.blend> [--strict]
With a scene that holds the collection 07_Sas_Arriere, its objects are checked as they are; the scene
is not saved. Without one, the module is built into an empty scene, checked, and saved to <out.blend>.
--strict exits 1 when a check fails.
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import airlock
import hullgrid
import materials


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    grid = hullgrid.HullGrid()
    col = bpy.data.collections.get(airlock.COL)
    if col is not None and col.objects:
        objs = list(col.objects)
    else:
        out = [a for a in args if not a.startswith("--")]
        assert out and os.path.abspath(out[0]) != os.path.abspath(bpy.data.filepath or "."), "give an output .blend"
        bpy.ops.wm.read_factory_settings(use_empty=True)
        objs = airlock.build(materials.library(), grid)
        bpy.ops.wm.save_as_mainfile(filepath=out[0])
    report = airlock.self_check(objs, grid)
    print(f"AIRLOCK_CHECK objects={len(objs)} triangles={report['triangles']} ok={report['ok']}")
    if "--strict" in args and not report["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
