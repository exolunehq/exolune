"""Read back an exported GLB: what a game engine would receive.

Run:  blender -b --factory-startup --python check_glb.py -- <file.glb> [<reimport.blend>]
Prints the node, mesh, material and triangle counts, the bounding box, and every animation with its
length and the number of nodes it moves. With a second path, saves the reimported scene, so
review.py can render it beside the source scene.
"""
import json
import struct
import sys

import bpy
import numpy as np


def document(path):
    """The JSON chunk of a GLB."""
    with open(path, "rb") as f:
        magic, _, _ = struct.unpack("<4sII", f.read(12))
        assert magic == b"glTF", "not a GLB"
        length, kind = struct.unpack("<I4s", f.read(8))
        assert kind == b"JSON"
        return json.loads(f.read(length))


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    doc = document(args[0])
    acc = doc["accessors"]
    tris = sum(acc[p["indices"]]["count"] // 3 for m in doc["meshes"] for p in m["primitives"])
    print(f"GLB nodes={len(doc['nodes'])} meshes={len(doc['meshes'])} materials={len(doc['materials'])} "
          f"images={len(doc.get('images', []))} triangles={tris}")
    for a in doc.get("animations", []):
        nodes = {c["target"]["node"] for c in a["channels"]}
        length = max(acc[s["input"]]["max"][0] for s in a["samplers"])
        print(f"GLB animation {a['name']}: {length:.2f} s, {len(nodes)} nodes, {len(a['channels'])} channels")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=args[0])
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    lo = np.min([np.min([o.matrix_world @ v.co for v in o.data.vertices], axis=0) for o in meshes], axis=0)
    hi = np.max([np.max([o.matrix_world @ v.co for v in o.data.vertices], axis=0) for o in meshes], axis=0)
    print(f"GLB reimport objects={len(meshes)} size={np.round(hi - lo, 3).tolist()} min={np.round(lo, 3).tolist()} "
          f"actions={sorted(a.name for a in bpy.data.actions)}")
    if len(args) > 1:
        bpy.ops.wm.save_as_mainfile(filepath=args[1])
        print("GLB reimport saved", args[1])


if __name__ == "__main__":
    main()
