"""Bound neural metallic and normal detail for a manufactured vehicle finish.

Keep the exact closed geometry, UVs and neural colour maps. The derivative
retains the original fingerprint and records explicit material multipliers.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import bpy

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(a.source))
for mat in bpy.data.materials:
    if not mat.use_nodes:continue
    nodes=mat.node_tree.nodes;links=mat.node_tree.links
    for node in nodes:
        if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.18
    for bs in [n for n in nodes if n.type=='BSDF_PRINCIPLED']:
        for field,factor in [('Metallic',.12),('Roughness',.8)]:
            slot=bs.inputs[field]
            if slot.is_linked:
                old=slot.links[0].from_socket;mix=nodes.new('ShaderNodeMath');mix.operation='MULTIPLY'
                mix.inputs[1].default_value=factor;links.new(old,mix.inputs[0]);links.new(mix.outputs[0],slot)
            else:slot.default_value*=factor
bpy.ops.wm.save_as_mainfile(filepath=str(a.out/'source.blend'))
bpy.ops.export_scene.gltf(filepath=str(a.out/'master.glb'),export_format='GLB',export_extras=True,
                          export_yup=True,export_cameras=False,export_lights=False)
source=json.loads(a.source.with_name('source.json').read_text(encoding='utf8'))
source.update(backend='ComfyUI closed vehicle; bounded neural PBR finish',
              input_master=str(a.source),input_master_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
              material_finish={'normal_strength':.18,'metallic_multiplier':.12,'roughness_multiplier':.8},
              finisher_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              master_sha256=hashlib.sha256((a.out/'master.glb').read_bytes()).hexdigest())
(a.out/'source.json').write_text(json.dumps(source,indent=2)+'\n',encoding='utf8')
