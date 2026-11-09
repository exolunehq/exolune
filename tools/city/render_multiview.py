"""Render an existing source with the exact native Pixal multiview orbit rig.

These calibrated views are a reconstruction control, not independent evidence
of an unseen facade. The source and cameras remain explicit in the manifest.
Run with Blender in background mode; rendering uses the CPU.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--size', type=int, default=1024)
    parser.add_argument('--clay', action='store_true', help='Neutral surface control, without generated colour artifacts')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    args.out.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(args.source.resolve()))
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if args.clay:
        material = bpy.data.materials.new('Neutral reconstruction control')
        material.use_nodes = True
        shader = material.node_tree.nodes['Principled BSDF']
        shader.inputs['Base Color'].default_value = (.62, .62, .62, 1)
        shader.inputs['Roughness'].default_value = .8
        for obj in objects:
            obj.data.materials.clear()
            obj.data.materials.append(material)
            for face in obj.data.polygons:
                face.material_index = 0
    points = [o.matrix_world @ Vector(corner) for o in objects for corner in o.bound_box]
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center = (low + high) * .5
    extent = max(high - low)
    # Bake transforms into vertices once; retain the full source silhouette.
    for obj in objects:
        matrix = obj.matrix_world.copy()
        for vertex in obj.data.vertices:
            vertex.co = (matrix @ vertex.co - center) / extent
        obj.matrix_world.identity()
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 6
    scene.render.resolution_x = scene.render.resolution_y = args.size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'Standard'
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.8, .8, .8, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = 1.0
    data = bpy.data.cameras.new('Pixal native orbit')
    data.type = 'PERSP'
    data.angle = math.radians(20)
    data.clip_start = .01
    data.clip_end = 20
    camera = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    distance = 1.1 * .5 / math.tan(math.radians(10))
    records = {}
    for name, angle in [('front', 0), ('left', 90), ('back', 180), ('right', 270)]:
        azimuth = math.radians(angle)
        camera.location = (math.sin(azimuth) * distance, -math.cos(azimuth) * distance, 0)
        camera.rotation_euler = (-camera.location).to_track_quat('-Z', 'Y').to_euler()
        bpy.context.view_layer.update()
        image = args.out / (name + '.png')
        scene.render.filepath = str(image)
        bpy.ops.render.render(write_still=True)
        records[name] = {'image': str(image.resolve()), 'sha256': digest(image),
                         'azimuth_degrees': angle, 'elevation_degrees': 0,
                         'camera_to_world': [list(row) for row in camera.matrix_world]}
    report = {'schema': 1, 'source': str(args.source.resolve()), 'source_sha256': digest(args.source),
              'scope': 'Calibrated reconstruction control from an existing dense generated house. These are not independent views of a new design.',
              'unit_cube_extent': 1.0, 'source_center': list(center), 'source_extent': extent,
              'fov_degrees': 20, 'distance': distance, 'up_axis': 'Z',
              'material': 'neutral clay' if args.clay else 'source material', 'views': records}
    (args.out / 'rig.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')


if __name__ == '__main__':
    main()
