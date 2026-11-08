"""Metric architectural master from a pinned neural GLB. Background Blender."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import math
import numpy as np
import bpy
from mathutils import Vector,Matrix

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--height',type=float,required=True);parser.add_argument('--id',required=True)
parser.add_argument('--anchor',choices=['ground','top'],default='ground')
parser.add_argument('--backend',default='trellis2',choices=['trellis2','pixal3d'])
parser.add_argument('--long-axis-x',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if args.height<=0:raise ValueError('Positive metric height required')
args.out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(args.source))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
angle=0.0
if args.long_axis_x:
    xy=np.asarray([tuple(p)[:2] for p in points])
    _,axes=np.linalg.eigh(np.cov(xy.T))
    axis=axes[:,-1]
    if axis[0]<0:axis=-axis
    angle=-math.atan2(axis[1],axis[0])
rotation=Matrix.Rotation(angle,4,'Z')
points=[rotation@p for p in points]
lo=Vector([min(p[i] for p in points) for i in range(3)])
hi=Vector([max(p[i] for p in points) for i in range(3)])
origin=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z if args.anchor=='ground' else hi.z));factor=args.height/(hi.z-lo.z)
for obj in objects:
    mat=obj.matrix_world.copy()
    for vertex in obj.data.vertices:
        vertex.co=(rotation@mat@vertex.co-origin)*factor
    obj.matrix_world=Matrix.Identity(4);obj['detail']=0
bpy.ops.wm.save_as_mainfile(filepath=str(args.out/'source.blend'))
bpy.ops.export_scene.gltf(filepath=str(args.out/'master.glb'),export_format='GLB',export_extras=True,
                          export_yup=True,export_cameras=False,export_lights=False)
(args.out/'source.json').write_text(json.dumps({'id':args.id,'backend':'ComfyUI '+args.backend+', metric normalization',
    'neural_mesh':True,'original':str(args.source),'original_sha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),
    'master_sha256':hashlib.sha256((args.out/'master.glb').read_bytes()).hexdigest(),'height_m':args.height,
    'scale':factor,'origin':list(origin),'anchor':args.anchor,'horizontal_rotation_radians':angle,
    'normalized_bounds':[list((lo-origin)*factor),list((hi-origin)*factor)],
    'normalizer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'art_accepted':False,'performance_accepted':False},indent=2)+'\n')
