"""Probe of the interior module: build it in the opened scene, check it, save a scene of its own.

Run:  blender -b <contexte_coque.blend> --python-exit-code 1 --python interior_probe.py -- <out.blend> [--strict]
Without a scene (--factory-startup) the interior is built alone, which proves it needs no other object.
The opened scene is never saved over: the result goes to <out.blend>. One hull grid serves the build and
the check. The check measures the deck's clearance from the glass, the spine's, and what enters the nose
gear well's volume; --strict exits 1 when a check fails.
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hullgrid
import interior
import materials


def library():
    """The hull's material library; materials the opened scene already holds are reused."""
    mats = {}
    for key, mat in materials.library().items():
        base = bpy.data.materials.get(mat.name.rsplit(".", 1)[0]) if "." in mat.name else mat
        if base is not None and base is not mat:
            bpy.data.materials.remove(mat)
            mat = base
        mats[key] = mat
    return mats


def main():
    out = sys.argv[sys.argv.index("--") + 1]
    assert os.path.abspath(out) != os.path.abspath(bpy.data.filepath), "the context scene is read-only"
    if not bpy.data.filepath:                              # no scene given: start from an empty one
        bpy.ops.wm.read_factory_settings(use_empty=True)
    grid = hullgrid.HullGrid()
    objs = interior.build(library(), grid)
    report = interior.self_check(objs, grid)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print(f"INTERIOR_SAVED {out} objects={len(objs)} triangles={report['triangles']} "
          f"deck_glass={report.get('deck_glass', 0.0):.3f} gear_box={sorted(report['gear_box'])} ok={report['ok']}")
    if "--strict" in sys.argv and not report["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
