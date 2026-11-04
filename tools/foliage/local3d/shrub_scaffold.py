"""Build a seeded, rooted shrub scaffold for the local leaf assembly stage.

Run with background Blender. The recipe describes woody architecture in
fractions of height. The plant pipeline adds generated leaf cutouts separately.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys

import bmesh
import bpy
from mathutils import Vector
import numpy as np


UP = Vector((0, 0, 1))


def cubic(points, t):
    a, b, c, d = points
    s = 1 - t
    return s**3 * a + 3 * s*s*t * b + 3 * s*t*t * c + t**3 * d


def append_stem(vertices, faces, path, base, tip):
    steps, sides = 14, 12
    first = len(vertices)
    for step in range(steps + 1):
        t = step / steps
        point = path(t)
        axis = (path(min(t + .01, 1)) - path(max(t - .01, 0))).normalized()
        side = axis.cross(Vector((1, 0, 0))).normalized()
        cross = axis.cross(side)
        radius = tip + (base - tip) * (1 - t)**1.15
        for i in range(sides):
            angle = math.tau * i / sides
            vertices.append(point + radius * (side * math.cos(angle) + cross * math.sin(angle)))
    for step in range(steps):
        for i in range(sides):
            a = first + step * sides + i
            b = first + step * sides + (i + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces.append(tuple(first + i for i in reversed(range(sides))))
    faces.append(tuple(first + steps * sides + i for i in range(sides)))


def bark(material, colour, seed):
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    size = 512
    y, x = np.mgrid[:size, :size] * (math.tau / size)
    phase = seed % 1009 / 1009 * math.tau
    grain = .06 * np.sin(x*31 + np.sin(y*3 + phase))
    grain += .07 * np.sin(x*9 + np.sin(y*2 - phase)*.8)
    grain += .04 * np.sin(x*55 + y*5 + phase) * np.sin(y*11)
    albedo = np.ones((size, size, 4), dtype=np.float32)
    albedo[:, :, :3] = np.array(colour) * (1 + grain[:, :, None])
    normal = np.ones_like(albedo)
    normal[:, :, :3] = np.stack((.5 - np.gradient(grain, axis=1)*2,
                                 .5 - np.gradient(grain, axis=0)*2, np.ones_like(x)), axis=-1)
    roughness = np.broadcast_to([1, .84, 0, 1], (2, 2, 4)).astype(np.float32)

    def image_node(label, rgba, space):
        image = bpy.data.images.new(label, rgba.shape[1], rgba.shape[0], alpha=True)
        image.colorspace_settings.name = space
        image.pixels.foreach_set(rgba.ravel())
        image.pack()
        node = nodes.new('ShaderNodeTexImage')
        node.image = image
        return node

    base = image_node('Stem colour', albedo, 'sRGB')
    links.new(base.outputs['Color'], bsdf.inputs['Base Color'])
    detail = image_node('Stem normal', normal, 'Non-Color')
    normal_map = nodes.new('ShaderNodeNormalMap')
    links.new(detail.outputs['Color'], normal_map.inputs['Color'])
    links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])
    mask = image_node('Stem roughness and metallic', roughness, 'Non-Color')
    channels = nodes.new('ShaderNodeSeparateColor')
    links.new(mask.outputs['Color'], channels.inputs[0])
    links.new(channels.outputs['Green'], bsdf.inputs['Roughness'])
    links.new(channels.outputs['Blue'], bsdf.inputs['Metallic'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recipe', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    recipe = json.loads(args.recipe.read_text(encoding='utf8'))
    profile = recipe['shrub_scaffold']
    seed = recipe['seed']
    rng = random.Random(seed)
    args.out.mkdir(parents=True, exist_ok=False)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    vertices, faces = [], []
    collar = [UP*z for z in [-.04, .01, .07, .16]]
    append_stem(vertices, faces, lambda t: cubic(collar, t), .066, .012)
    count, spread, arch = (profile[key] for key in ['stems', 'spread', 'arch'])
    heading = rng.uniform(0, math.tau)
    for i in range(count):
        angle = heading + math.tau * i / count + rng.uniform(-.13, .13)
        direction = Vector((math.cos(angle), math.sin(angle), 0))
        tangent = direction.cross(UP)
        reach = spread * rng.uniform(.68, 1.06)
        end = direction * reach + UP * rng.uniform(.62, 1)
        stem = [UP * rng.uniform(.025, .060), UP*.28 + direction*(reach*profile.get('flare',.12)),
                end*.72 + UP*arch + tangent*rng.uniform(-.09, .09), end]
        bend = profile.get('bend', 0.0)
        swing = tangent * bend * (-1 if i % 2 else 1)
        def cane(t):
            # Each cane bows and turns in its own radial plane. The collar
            # and the tip retain their position and fork anchors follow it.
            return cubic(stem, t) + swing * (math.sin(math.pi*t)**2) * (0.82 - 1.42*t)
        append_stem(vertices, faces, cane, rng.uniform(.028, .043), .010)
        for sign in [-1, 1]:
            t = rng.uniform(.42, .59) if sign < 0 else rng.uniform(.62, .76)
            start = cane(t)
            fork = direction*.8 + tangent*sign*rng.uniform(.55, .78)
            finish = start + fork*(reach*rng.uniform(.32, .55)) + UP*rng.uniform(.10, .23)
            branch = [start, start + UP*.04, finish - fork*.05 - UP*.08, finish]
            append_stem(vertices, faces, lambda u: cubic(branch, u), .017, .008)

    mesh = bpy.data.meshes.new('Root collar and free stem tips')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    wood = bpy.data.objects.new(recipe['name'] + ' scaffold', mesh)
    bpy.context.collection.objects.link(wood)
    bpy.context.view_layer.objects.active = wood
    wood.select_set(True)
    remesh = wood.modifiers.new('Solid stem junctions', 'REMESH')
    remesh.mode = 'VOXEL'
    remesh.voxel_size = .006
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    smooth = wood.modifiers.new('Rounded stem junctions', 'SMOOTH')
    smooth.factor = .55
    smooth.iterations = 2
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    wood.data.calc_loop_triangles()
    reduce = wood.modifiers.new('Stem triangle budget', 'DECIMATE')
    reduce.ratio = min(1, recipe['wood_triangles'] / len(wood.data.loop_triangles))
    bpy.ops.object.modifier_apply(modifier=reduce.name)
    bm = bmesh.new()
    bm.from_mesh(wood.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(wood.data)
    bm.free()
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(island_margin=.006)
    bpy.ops.object.mode_set(mode='OBJECT')
    for polygon in wood.data.polygons:
        polygon.use_smooth = True
    material = bpy.data.materials.new('Shrub stems')
    material.use_nodes = True
    bark(material, profile['bark'], seed)
    wood.data.materials.append(material)
    dest = args.out / 'wood.glb'
    bpy.ops.export_scene.gltf(filepath=str(dest), export_format='GLB', use_selection=True,
                              export_normals=True, export_tangents=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.out/'scaffold.blend'))
    report = {'seed': seed, 'profile': profile, 'wood_triangles': len(wood.data.polygons),
              'recipe_sha256': hashlib.sha256(args.recipe.read_bytes()).hexdigest(),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'wood_sha256': hashlib.sha256(dest.read_bytes()).hexdigest()}
    (args.out/'scaffold-report.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
