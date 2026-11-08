"""Optional ComfyUI architecture master using the existing local3d neural stages.

Reference isolation and mesh reconstruction are separate reviewable steps. No
plant topology test is applied to a building with intentionally closed arches.
"""
from pathlib import Path
import argparse
import json
import sys

LOCAL=Path(__file__).resolve().parents[1]/'foliage/local3d'
sys.path.insert(0,str(LOCAL))
from pipeline import Comfy, fingerprint, image_stage, model_manifest, save, stage, upload_reference


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--comfy-url',default='http://127.0.0.1:8190')
    parser.add_argument('--name',default='city_shell_house');parser.add_argument('--brief',required=True)
    parser.add_argument('--references-only',action='store_true')
    parser.add_argument('--faces',type=int,default=80000)
    parser.add_argument('--backend',choices=['trellis2','pixal3d'],default='trellis2')
    parser.add_argument('--wait-gpu',action='store_true',help='Wait for free VRAM without closing any engine')
    parser.add_argument('--minimum-free-vram-gib',type=float,default=7.25,
                        help='Explicit inference admission budget; ComfyUI still manages model offloading')
    parser.add_argument('--voxel-resolution',type=int,choices=[512,1024],default=1024)
    parser.add_argument('--subject',choices=['building','vehicle'],default='building')
    parser.add_argument('--surface-mode',choices=['preserve','closed'],default='preserve',
                        help='Closed opaque bodies can use manifold resampling; thin architectural shells must not')
    parser.add_argument('--prepared-reference',type=Path,help='Pin and reuse an isolated reference without regenerating it')
    parser.add_argument('--comfy-root',type=Path,default=Path('E:/ComfyUI'))
    parser.add_argument('--models',type=Path,default=Path('E:/ComfyUI_Models/models'))
    args=parser.parse_args();args.out=args.out.resolve();args.out.mkdir(parents=True,exist_ok=True)
    args.allow_shared_gpu=True;args.yield_if_gpu_busy=not args.wait_gpu
    args.recipe={'name':args.name,'description':args.brief,'geometry_backend':args.backend,'image_resolution':1024,
                 'image_seeds':{'reference':419307},'captions':{'reference':
                 'Extract and redesign the single complete main building from the supplied architectural board. '
                 'A premium warm solarpunk building asset, not a scene and not a collage. Preserve the sculpted '
                 'asymmetric inhabited shells, substantial ivory rim, deep green recessed reveals, flowing '
                 'structural transitions, golden timber and large inset windows. Physically plausible scale '
                 'and substantial depth. Keep the front and a long side visible in a clear elevated three quarter '
                 'view. A small integrated terrace is allowed. Remove all people, trees, surrounding grass, '
                 'landscape, sky, loose plants, pools, captions and diagrams. Neutral pale grey background, '
                 'even studio light, no strong baked shadows. All roof edges and supports fit inside the image '
                 'with ten percent margin. The complete bottom is visible, no soil slab or pedestal. '
                 + args.brief}}
    if not 8000<=args.faces<=200000:raise ValueError('Architecture mesh budget must be 8,000 to 200,000 faces')
    args.recipe['target_faces']=args.faces
    if args.subject=='vehicle':
        args.recipe['captions']['reference']=(
            'Extract the single suspended two-lobed panoramic train VEHICLE from the supplied board. '
            'This is a complete detached transport vehicle, not a building, not a station, not a landscape. '
            'Preserve the beautiful asymmetric ivory body, broad blue-green panoramic glazing with warm interior detail, '
            'two articulated passenger lobes, the dark flexible central joint, curved structural window frames and '
            'four compact roof-mounted suspension bogies. No wheels and no supporting rail. '
            'View the entire vehicle in a clear slightly elevated long three-quarter view; show its length and depth. '
            'No text, people, diagrams, vegetation, ground slab or pedestal. Neutral pale grey studio background. '
            'Soft even light and no strong baked shadows. All bogies, both noses and the complete underside visible with margin. '
            +args.brief)
    args.recipe['voxel_resolution']=args.voxel_resolution
    args.recipe['surface_mode']=args.surface_mode
    if args.minimum_free_vram_gib<6:raise ValueError('Keep at least 6 GiB free for an architectural inference attempt')
    args.recipe['minimum_free_vram_gib']=args.minimum_free_vram_gib
    comfy=Comfy(args.comfy_url,args.comfy_root);schema=comfy.call('object_info');models=model_manifest(args,schema)
    save(args.out/'recipe.json',args.recipe|{'input':str(args.reference),'input_sha256':fingerprint(args.reference)})
    reference=args.prepared_reference.resolve() if args.prepared_reference else image_stage('reference',args.reference,args,comfy,schema,models)
    save(args.out/'reference-review.json',{'image':str(reference),'sha256':fingerprint(reference),'accepted':False})
    if args.references_only:return
    body=json.loads((LOCAL/f'templates/wood_{args.backend}.json').read_text());p=body['prompt']
    p['122']['inputs']['image']=upload_reference(reference,args)
    if args.voxel_resolution==512:
        # Decode the native first shape stage. Do not upsample to a multi-million
        # face master only to destroy it with an extreme subsequent reduction.
        for node in p.values():
            for field,value in list(node['inputs'].items()):
                if value==['23',0]:node['inputs'][field]=['18',0]
                elif isinstance(value,list) and value[0]=='94':node['inputs'][field]=['91',value[1]]
        p.pop('23');p.pop('94')
    p['351']['inputs']['target_face_count']=args.faces
    # Architectural walls and arches must retain their original surface. The
    # woody solid-remesh stage can join opposite walls or tear thin shells.
    p['351']['inputs']['mesh']=['92',0]
    p['351']['inputs'].update({'placement_mode':'qem','placement_mode.line_quadric_weight':.5,
        'placement_mode.feature_edge_quadric_weight':2.,'placement_mode.feature_edge_min_dihedral_deg':35.,
        'placement_mode.clamp_v_to_edge':True})
    if args.surface_mode=='closed':
        p['350']['inputs'].update(resolution=256,project_back=.65,drop_small_components=.0002)
        p['351']['inputs']={'mesh':['350',0],'target_face_count':args.faces,'placement_mode':'midpoint'}
    for identifier,field in [('353','resolution'),('354','texture_size'),('355','resolution')]:p[identifier]['inputs'][field]=2048
    output=stage('wood_mesh',body,{'342':'high_raw','343':'high_colour','358':'low_pbr','360':'basecolor',
                 '361':'normal','362':'roughness','363':'metallic'},args,comfy,schema,models)
    save(args.out/'manifest.json',{'backend':'ComfyUI '+args.backend+' mesh',
         'prepared_reference':bool(args.prepared_reference),'reference_sha256':fingerprint(reference),
         'artifacts':{k:{'path':str(v),'sha256':fingerprint(v)} for k,v in output.items()},
         'art_accepted':False,'native_cook':'pending','performance_accepted':False})


if __name__=='__main__':main()
