"""Validate a completed local authoring run and its saved native canvases."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'foliage/local3d'))
from audit import check

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('run',type=Path)
parser.add_argument('--review',type=Path)
args=parser.parse_args()
manifest=json.loads((args.run/'manifest.json').read_text())
recipe=json.loads((args.run/'recipe.json').read_text(encoding='utf8'))
asset=Path(manifest['asset'])
result=check(asset,recipe['max_triangles'],recipe['height_m'])
assert hashlib.sha256(asset.read_bytes()).hexdigest()==manifest['sha256']
try:check(asset,result['triangles']-1,recipe['height_m'])
except ValueError as error:assert 'budget exceeded' in str(error)
else:raise AssertionError('An exceeded triangle budget was accepted')

stages=['reference','wood_reference','cluster_reference','leaf_reference','wood_mesh','leaf_alpha']
for stage in stages:
    completed=[]
    for state_path in (args.run/stage).glob('*/state.json'):
        state=json.loads(state_path.read_text())
        if state['status']!='complete':continue
        folder=state_path.parent;api=json.loads((folder/'api.json').read_text());canvas=json.loads((folder/'workflow.json').read_text())
        history=json.loads((folder/'history.json').read_text())
        assert history['status']['status_str']=='success',stage
        assert {node['id'] for node in canvas['nodes']}=={int(i) for i in api['prompt']},stage
        nodes={node['id']:node for node in canvas['nodes']};actual=set()
        for number,source,output,target,slot,kind in canvas['links']:
            assert nodes[target]['inputs'][slot]['link']==number
            assert number in nodes[source]['outputs'][output]['links']
            actual.add((source,output,target,nodes[target]['inputs'][slot]['name']))
        expected=set()
        for identifier,node in api['prompt'].items():
            for name,value in node['inputs'].items():
                if isinstance(value,list):expected.add((int(value[0]),value[1],int(identifier),name))
            if node['class_type']=='RemeshMesh':assert isinstance(node['inputs']['sign_mode'],str)
            if node['class_type']=='DecimateMesh':assert isinstance(node['inputs']['placement_mode'],str)
        assert actual==expected,stage
        for artifact in state['artifacts'].values():
            assert hashlib.sha256(Path(artifact['path']).read_bytes()).hexdigest()==artifact['sha256'],stage
        completed.append(state_path)
    assert completed,'No completed '+stage

if args.review:
    wind=json.loads((args.review/'wind-check.json').read_text())
    for item in wind['results']:
        assert item['fixed_vertices']>0 and item['fixed_attachment_max_error_m']<1e-6
        assert item['moving_vertex_max_displacement_m']>0 and item['wood_motion_m']==0
    for view in ['quarter','back','walking','roots','wind']:assert (args.review/(view+'.png')).is_file()
print(json.dumps({'status':'pass','stages':stages,'asset':result,'wind_review':bool(args.review)},indent=2))
