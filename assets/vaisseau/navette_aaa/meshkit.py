"""Small Blender mesh helpers shared by the shuttle builders."""
import bpy
import numpy as np


def collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def mesh_object(name, verts, faces, col_name, materials=(), face_mats=None, normals=None, uvs=None,
                orient=None):
    """Object from numpy arrays: verts (n, 3), faces (m, 4) or a list of index tuples.

    normals (n, 3) become custom vertex normals; orient (n, 3) only winds the faces to look that way;
    uvs (n, 2) one UV per vertex; face_mats (m,) material slot per face.
    """
    me = bpy.data.meshes.new(name)
    verts = np.asarray(verts, dtype=float)
    if normals is not None:
        normals = np.asarray(normals, dtype=float)
    guide = normals if orient is None else np.asarray(orient, dtype=float)
    if guide is not None and len(faces):
        # Wind every face so that its geometric normal agrees with the guide vectors.
        fixed = []
        for f in faces:
            f = [int(i) for i in f]
            p = verts[f]
            geo = np.cross(p[1] - p[0], p[2] - p[0]) + np.cross(p[2] - p[0], p[-1] - p[0])
            fixed.append(tuple(f) if np.dot(geo, guide[f].sum(axis=0)) >= 0.0 else tuple(reversed(f)))
        faces = fixed
    faces = [tuple(int(i) for i in f) for f in faces]
    me.from_pydata([tuple(v) for v in np.asarray(verts, dtype=float)], [], faces)
    for m in materials:
        me.materials.append(m)
    if face_mats is not None:
        me.polygons.foreach_set("material_index", np.asarray(face_mats, dtype=np.int32))
    me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), dtype=bool))
    layer = me.uv_layers.new(name="UVMap")
    loop_verts = np.zeros(len(me.loops), dtype=np.int32)
    me.loops.foreach_get("vertex_index", loop_verts)
    if uvs is not None:
        layer.data.foreach_set("uv", np.asarray(uvs, dtype=np.float32)[loop_verts].ravel())
    else:
        layer.data.foreach_set("uv", box_uv(me, verts, loop_verts).astype(np.float32).ravel())
    me.update()
    if normals is not None:
        me.normals_split_custom_set_from_vertices([tuple(n) for n in np.asarray(normals, dtype=float)])
    obj = bpy.data.objects.new(name, me)
    collection(col_name).objects.link(obj)
    return obj


def mesh_faces(verts, faces, guide):
    """Faces wound one by one so that each looks along its nodes' guide vectors."""
    verts, guide = np.asarray(verts, dtype=float), np.asarray(guide, dtype=float)
    out = []
    for f in faces:
        f = [int(i) for i in f]
        q = verts[f]
        geo = np.cross(q[1] - q[0], q[2] - q[0]) + np.cross(q[2] - q[0], q[-1] - q[0])
        out.append(f if np.dot(geo, guide[f].sum(axis=0)) >= 0.0 else f[::-1])
    return out


def grid_faces(index, keep=None):
    """Quads of a structured node-index grid (na, nb); keep (na-1, nb-1) selects the cells."""
    a = index[:-1, :-1]
    b = index[1:, :-1]
    c = index[1:, 1:]
    d = index[:-1, 1:]
    quads = np.stack([a, b, c, d], axis=-1)
    if keep is not None:
        return quads[keep]
    return quads.reshape(-1, 4)


def join(objects, name):
    """Join mesh objects into one named object (the first one's collection and slots lead)."""
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    out = bpy.context.view_layer.objects.active
    out.name = out.data.name = name
    return out


def wind(verts, faces, guide):
    """Faces of one consistently wound patch, all reversed together if they look against the guide.

    Use it where a per-face test would be unsure, for example round a sharp corner.
    """
    verts, guide = np.asarray(verts, dtype=float), np.asarray(guide, dtype=float)
    f = np.asarray(faces, dtype=np.int64)
    p = verts[f]
    geo = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]) + np.cross(p[:, 2] - p[:, 0], p[:, -1] - p[:, 0])
    agree = float((geo * guide[f].sum(axis=1)).sum())
    return f.tolist() if agree >= 0.0 else f[:, ::-1].tolist()


def box_uv(me, verts, loop_verts):
    """Per-loop UVs in metres by box projection: each face is seen along its dominant axis."""
    me.update()
    normals = np.zeros(len(me.polygons) * 3)
    me.polygons.foreach_get("normal", normals)
    totals = np.zeros(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get("loop_total", totals)
    axis = np.repeat(np.abs(normals.reshape(-1, 3)).argmax(axis=1), totals)
    p = np.asarray(verts, dtype=float)[loop_verts]
    u = np.where(axis == 0, p[:, 1], p[:, 0])
    v = np.where(axis == 2, p[:, 1], p[:, 2])
    return np.stack([u, v], axis=1)
