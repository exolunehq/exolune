"""Local brief/reference -> generated wood/materials -> independently deformable foliage."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import numpy as np
from PIL import Image
from audit import check

HERE = Path(__file__).resolve().parent


class GpuBudgetUnavailable(RuntimeError):
    pass


def load_recipe(path):
    defaults=json.loads((HERE/'examples/oak.json').read_text(encoding='utf8'))
    supplied=json.loads(path.read_text(encoding='utf8')) if path.suffix.lower()=='.json' else {'description':path.read_text(encoding='utf8')}
    recipe=defaults | {'name':'plant_witness','reference':None,'description':''} | supplied
    recipe['captions']=json.loads((HERE/'templates/captions.json').read_text(encoding='utf8')) | supplied.get('captions',{})
    recipe['image_seeds']=defaults['image_seeds'] | supplied.get('image_seeds',{})
    for field in ['wood_reference_source','wood_source']:
        if recipe.get(field):
            source=Path(recipe[field])
            recipe[field]=str((path.parent/source if not source.is_absolute() else source).resolve())
    return recipe


def fingerprint(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def key(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf8')


def prepared_references(path, *, shrub=False):
    """Reuse a pinned art review across geometry backends without regenerating images."""
    path=path.resolve();bundle=json.loads(path.read_text(encoding='utf8'))
    names=['reference','cluster_reference','leaf_reference']
    if not shrub:names.append('wood_reference')
    if set(bundle.get('images',{}))!=set(names):raise ValueError('The reference review must pin all images required by the recipe')
    images={}
    for name in names:
        entry=bundle['images'][name];image=Path(entry['path'])
        image=(path.parent/image if not image.is_absolute() else image).resolve()
        if not image.is_file() or fingerprint(image)!=entry['sha256']:
            raise ValueError('Reference review image is missing or has changed: '+name)
        images[name]=image
    return images,{'path':str(path),'sha256':fingerprint(path)}


def wood_reference_check(path,allow_green_stems=False):
    rgb=np.asarray(Image.open(path).convert('RGB'),dtype=np.float32)/255
    crop=rgb[int(len(rgb)*.08):int(len(rgb)*.78)];r,g,b=np.moveaxis(crop,-1,0)
    leafy=(g>=r*.98)&(g-b>.075)&((np.max(crop,2)-np.min(crop,2))>.12)&(g>.12)
    share=float(leafy.mean());threshold=.16 if allow_green_stems else .03
    return {'status':'pass' if share<=threshold else 'reject leafy wood reference',
            'upper_image_green_share':share,'maximum':threshold,
            'scope':'Cheap colour guard for unwanted foliage; green stems are an explicit botanical exception. It does not replace structural review.'}


class Comfy:
    def __init__(self, url, root):
        if urllib.parse.urlparse(url).hostname not in ['127.0.0.1', 'localhost', '::1']:
            raise ValueError('This pipeline requires a loopback ComfyUI endpoint')
        self.url = url.rstrip('/')
        self.root = root.resolve()

    def call(self, route, body=None):
        request = urllib.request.Request(self.url+'/'+route, data=json.dumps(body).encode() if body is not None else None,
                                         headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response) if response.length != 0 else {}
        except urllib.error.HTTPError as error:
            raise RuntimeError(error.read().decode()) from error

    def idle(self):
        queue = self.call('queue')
        return not queue['queue_running'] and not queue['queue_pending']

    def release(self):
        self.call('free', {'unload_models':True, 'free_memory':True})
        time.sleep(2)


def no_game(required_gib=0,allow_shared=False,yield_if_busy=False):
    if os.name == 'nt':
        started=time.monotonic();reported=False
        while True:
            listing = subprocess.check_output(['tasklist','/FI','IMAGENAME eq MyPlanetEngine.exe','/FO','CSV','/NH'], creationflags=subprocess.CREATE_NO_WINDOW)
            engines=b'myplanetengine.exe' in listing.lower()
            free_gib=None
            if allow_shared:
                try:free_gib=float(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],creationflags=subprocess.CREATE_NO_WINDOW).decode().strip().splitlines()[0])/1024
                except (OSError,ValueError,subprocess.CalledProcessError):pass
            if (not engines and not allow_shared) or (allow_shared and free_gib is not None and free_gib>=required_gib):return
            if yield_if_busy:raise GpuBudgetUnavailable(f'GPU budget unavailable: need {required_gib:.1f} GiB free; observed {free_gib}; completed stages retained')
            if not reported:print('Waiting for the game to close before the next GPU stage; saved results are retained.',flush=True);reported=True
            if time.monotonic()-started>3600:raise TimeoutError('Game still running; this authoring job can be resumed later.')
            time.sleep(5)


def canvas(body, schema):
    """Keep saved native canvases in sync with the executed API graph."""
    original = body.get('extra_data',{}).get('extra_pnginfo',{}).get('workflow',{})
    existing = {n['id']:n for n in original.get('nodes',[])}
    result = {'last_node_id':max(map(int,body['prompt'])), 'last_link_id':0, 'nodes':[], 'links':[],
              'groups':[], 'config':{}, 'extra':original.get('extra',{}), 'version':0.4}
    widget_types = {'INT','FLOAT','STRING','BOOLEAN','COMBO','COLOR','LOAD_3D','COMFY_DYNAMICCOMBO_V3'}
    for order,(identifier,node) in enumerate(body['prompt'].items()):
        definition = schema[node['class_type']]
        ui = copy.deepcopy(existing.get(int(identifier),{}))
        ui.update({'id':int(identifier),'type':node['class_type'],'order':order,'mode':0,'flags':{},
                   'properties':{'Node name for S&R':node['class_type']},'inputs':[],'outputs':[],'widgets_values':[]})
        ui.setdefault('pos',[order%4*420,order//4*350]);ui.setdefault('size',[340,260])
        for section in ['required','optional']:
            fields = definition['input'].get(section,{})
            for name in definition.get('input_order',{}).get(section,fields):
                typ = fields[name][0];options = fields[name][1] if len(fields[name])>1 else {};value = node['inputs'].get(name)
                widget = isinstance(typ,list) or typ in widget_types
                if typ == 'COMFY_DYNAMICCOMBO_V3':
                    selected = next((x for x in options['options'] if x['key']==value),None)
                    if selected is None:
                        raise ValueError(f'{identifier}.{name}: dynamic selectors must be flat API strings')
                    ui['widgets_values'].append(value)
                    for child,spec in selected['inputs'].get('required',{}).items():
                        ui['widgets_values'].append(node['inputs'][name+'.'+child])
                elif widget:
                    default = options.get('default',typ[0] if isinstance(typ,list) and typ else '' if typ in ['STRING','COMBO','LOAD_3D','COLOR'] else False if typ=='BOOLEAN' else 0)
                    ui['widgets_values'].append(default if isinstance(value,list) else value if value is not None else default)
                    if options.get('control_after_generate'):ui['widgets_values'].append('fixed')
                if isinstance(value,list) or not widget:
                    slot = {'name':name,'type':typ if isinstance(typ,str) else 'COMBO','link':None}
                    if widget:slot['widget']={'name':name}
                    ui['inputs'].append(slot)
        for index,typ in enumerate(definition['output']):
            ui['outputs'].append({'name':definition.get('output_name',definition['output'])[index],'type':typ,'links':[]})
        result['nodes'].append(ui)
    nodes = {n['id']:n for n in result['nodes']}
    for identifier,node in body['prompt'].items():
        for name,value in node['inputs'].items():
            if not isinstance(value,list):continue
            source,target = int(value[0]),int(identifier)
            slot = next(i for i,x in enumerate(nodes[target]['inputs']) if x['name']==name)
            number = len(result['links'])+1;typ=nodes[source]['outputs'][value[1]]['type']
            result['links'].append([number,source,value[1],target,slot,typ]);nodes[target]['inputs'][slot]['link']=number;nodes[source]['outputs'][value[1]]['links'].append(number)
    result['last_link_id']=len(result['links'])
    body['extra_data']={'extra_pnginfo':{'workflow':result}}
    return result


def model_manifest(args, schema):
    files = [('diffusion_models','flux3-image-klein-int8-convrot.safetensors'),
             ('text_encoders','qwen3vl_4b_int8_convrot.safetensors'),('vae','flux2-vae.safetensors')]
    if not args.recipe.get('wood_source'):
        files.extend([('diffusion_models','trellis_2_int8_convrot.safetensors' if args.recipe['geometry_backend']=='trellis2' else 'pixal3d_int8_convrot.safetensors'),
            ('vae','trellis_2_shape_vae_bf16.safetensors'),('vae','trellis_2_texture_vae_bf16.safetensors'),('clip_vision','dino_v3_L_naf_fp32.safetensors')])
    files.append(('background_removal','birefnet.safetensors'))
    if not args.recipe.get('wood_source') and args.recipe['geometry_backend']=='pixal3d':files.append(('geometry_estimation','moge_2_vitl_normal_fp16.safetensors'))
    loaders={'diffusion_models':('UNETLoader','unet_name'),'text_encoders':('CLIPLoader','clip_name'),
             'vae':('VAELoader','vae_name'),'clip_vision':('CLIPVisionLoader','clip_name'),
             'background_removal':('LoadBackgroundRemovalModel','bg_removal_name'),
             'geometry_estimation':('LoadMoGeModel','model_name')}
    cache_file=args.out/'model-hashes.json';cache=json.loads(cache_file.read_text()) if cache_file.exists() else {};result=[]
    for folder,name in files:
        node,field=loaders[folder]
        specification=schema.get(node,{}).get('input',{}).get('required',{}).get(field,[])
        choices=specification[0] if specification and isinstance(specification[0],list) else specification[1].get('options',[]) if len(specification)>1 else []
        if name not in choices:raise ValueError(f'ComfyUI cannot see {folder}/{name}; check its explicit model-path configuration before inference')
        path=args.models/folder/name
        if not path.is_file():raise FileNotFoundError(path)
        stat=path.stat();stamp=[stat.st_size,stat.st_mtime_ns];record=cache.get(str(path))
        if not record or record['stamp']!=stamp:
            print('Fingerprint model:',name,flush=True);record={'stamp':stamp,'sha256':fingerprint(path)};cache[str(path)]=record
        result.append({'path':str(path),'bytes':stat.st_size,'sha256':record['sha256']})
    save(cache_file,cache)
    return result


def upload_reference(source, args):
    digest=fingerprint(source);relative=Path('exolune_local3d')/args.recipe['name']/(digest+source.suffix.lower())
    target=args.comfy_root/'input'/relative;target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists() or fingerprint(target)!=digest:shutil.copyfile(source,target)
    return relative.as_posix()


def stage(name, body, roles, args, comfy, schema, models):
    semantic=copy.deepcopy(body['prompt'])
    for node in semantic.values():
        if 'filename_prefix' in node['inputs']:node['inputs']['filename_prefix']='<output>'
    digest=key({'graph':semantic,'models':models});folder=args.out/name/digest[:16];folder.mkdir(parents=True,exist_ok=True);state_path=folder/'state.json'
    state=json.loads(state_path.read_text()) if state_path.exists() else {'key':digest}
    if state.get('status')=='complete' and all(Path(v['path']).is_file() and fingerprint(v['path'])==v['sha256'] for v in state['artifacts'].values()):
        print(name+': reused verified artifacts',flush=True);return {k:Path(v['path']) for k,v in state['artifacts'].items()}
    prefix='Exolune/local3d/'+args.recipe['name']+'/'+digest[:16]+'/'+name
    for identifier,node in body['prompt'].items():
        if 'filename_prefix' in node['inputs']:node['inputs']['filename_prefix']=prefix+'_'+identifier
    # A diagnostic preview must not make a rejected geometry graph look valid.
    body['partial_execution_targets']=list(roles)
    workflow=canvas(body,schema);save(folder/'api.json',body);save(folder/'workflow.json',workflow)
    saved=args.comfy_root/'user/default/workflows/Exolune/local3d';saved.mkdir(parents=True,exist_ok=True);save(saved/(args.recipe['name']+'_'+name+'.json'),workflow)
    if state.get('prompt_id') and state.get('status') != 'error' and not comfy.call('history/'+state['prompt_id']):
        queue = comfy.call('queue')
        known = [item[1] for item in queue['queue_running'] + queue['queue_pending']]
        if state['prompt_id'] not in known:
            state.update({'status':'error', 'details':'Previous server no longer knows this prompt; submitting the saved graph again.'})
    if not state.get('prompt_id') or state.get('status')=='error':
        required=7.25 if name=='wood_mesh' else 2.0 if name=='leaf_alpha' else 7.0
        no_game(required,args.allow_shared_gpu,args.yield_if_gpu_busy)
        if not comfy.idle():raise GpuBudgetUnavailable('ComfyUI is busy with another queued job; resume when it is idle.')
        response=comfy.call('prompt',body);save(folder/'submission.json',response)
        if response.get('node_errors'):
            state.update(status='error',details=response['node_errors']);save(state_path,state)
            raise ValueError(name+': ComfyUI rejected required nodes; see submission.json')
        state.pop('details',None);state.update({'status':'running','prompt_id':response['prompt_id']});save(state_path,state)
        print(name+': queued '+state['prompt_id'],flush=True)
    started=time.monotonic()
    while True:
        history=comfy.call('history/'+state['prompt_id'])
        if history:break
        if time.monotonic()-started>3600:raise TimeoutError(name+' is still running; the saved prompt id can be resumed.')
        time.sleep(2)
    entry=history[state['prompt_id']];save(folder/'history.json',entry)
    if any(identifier not in entry.get('outputs',{}) for identifier in roles):
        state.update(status='error',details='Required artifacts absent from the completed graph');save(state_path,state)
        if comfy.idle():comfy.release()
        raise ValueError(name+': required output missing; inspect the saved graph and node model paths')
    if entry['status']['status_str']!='success':
        if comfy.idle():comfy.release()
        state.update({'status':'error','details':entry['status']});save(state_path,state);raise RuntimeError(name+' failed: '+str(entry['status'])+'; see '+str(folder/'history.json'))
    artifacts={}
    for identifier,role in roles.items():
        output=entry['outputs'][identifier];items=output.get('images',output.get('3d',[]))
        if len(items)!=1:raise ValueError(name+': expected one artifact for '+role)
        item=items[0];base=(args.comfy_root/item['type']).resolve();source=(base/item.get('subfolder','')/item['filename']).resolve()
        if not source.is_relative_to(base):raise ValueError('Invalid artifact path')
        target=folder/(role+source.suffix);shutil.copyfile(source,target);artifacts[role]={'path':str(target),'sha256':fingerprint(target),'source':str(source)}
    state.update({'status':'complete','artifacts':artifacts});save(state_path,state);comfy.release();print(name+': complete',flush=True)
    return {k:Path(v['path']) for k,v in artifacts.items()}


def image_stage(name, reference, args, comfy, schema, models):
    body=json.loads((HERE/'templates/reference.json').read_text());p=body['prompt']
    caption=args.recipe['captions'][name]
    if name == 'reference':caption='Art brief: '+args.recipe['description']+'\n\n'+caption
    p['4']['inputs']['text']=caption;p['7']['inputs']['seed']=args.recipe['image_seeds'][name]
    size=args.recipe['image_resolution'];p['6']['inputs'].update(width=size,height=size)
    if reference:
        p['10']['inputs']['image']=upload_reference(reference,args)
    else:
        for identifier in ['10','11','12','13','14']:p.pop(identifier)
        p['7']['inputs'].update(positive=['4',0],negative=['5',0])
    return stage(name,body,{'9':'image'},args,comfy,schema,models)['image']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('brief',type=Path);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--reference',type=Path,help='Optional image overriding the brief reference')
    parser.add_argument('--wood-source',type=Path,help='Curated PBR wood GLB, including a radial scaffold; topology and volume gates still apply')
    parser.add_argument('--references-only',action='store_true',help='Stop after isolated references so their art can be inspected before 3D inference')
    parser.add_argument('--prepared-references',type=Path,help='Reuse all four hash-pinned images from a reference-review.json when comparing geometry backends')
    parser.add_argument('--allow-shared-gpu',action='store_true',help='Admit authoring stages by free VRAM; never use this for performance acceptance')
    parser.add_argument('--yield-if-gpu-busy',action='store_true',help='Retain completed stages and let a library queue try another asset')
    parser.add_argument('--comfy-url',default='http://127.0.0.1:8188');parser.add_argument('--comfy-root',type=Path,default=Path('E:/ComfyUI'))
    parser.add_argument('--models',type=Path,default=Path('E:/ComfyUI_Models/models'))
    parser.add_argument('--blender',type=Path,default=Path('C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'))
    args=parser.parse_args();args.out=args.out.resolve();args.out.mkdir(parents=True,exist_ok=True);args.recipe=load_recipe(args.brief)
    if args.reference:args.recipe['reference']=str(args.reference.resolve())
    if args.wood_source:args.recipe['wood_source']=str(args.wood_source.resolve())
    recipe=args.recipe
    if recipe.get('wood_source') and not Path(recipe['wood_source']).is_file():raise FileNotFoundError(recipe['wood_source'])
    if not recipe['name'] or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in recipe['name']):raise ValueError('Use a lowercase asset name with digits, underscores or hyphens')
    if recipe['geometry_backend'] not in ['trellis2','pixal3d']:raise ValueError('Unsupported local geometry backend')
    if recipe['max_triangles']<recipe['wood_triangles']+76 or recipe['height_m']<=0:raise ValueError('Invalid geometry budget or height')
    if recipe['cluster_limit'] < 1 or recipe.get('cluster_spacing_m',recipe.get('min_anchor_distance_m',0)) <= 0:raise ValueError('Invalid foliage population')
    if recipe.get('foliage_distribution','crown_volume') not in ['crown_volume','surface']:raise ValueError('Invalid foliage distribution')
    if not recipe.get('description','').strip():raise ValueError('A text art brief is required')
    for field in ['leaf_length_m','shoot_length_m']:
        if len(recipe[field])!=2 or not 0 < recipe[field][0] <= recipe[field][1]:raise ValueError('Invalid '+field)
    shrub=bool(recipe.get('shrub_scaffold'))
    if shrub and not recipe.get('wood_source'):
        raise ValueError('Build the shrub scaffold first and pass it with --wood-source')
    pinned,reference_set=prepared_references(args.prepared_references,shrub=shrub) if args.prepared_references else ({},None)
    comfy=Comfy(args.comfy_url,args.comfy_root);schema=comfy.call('object_info');models=model_manifest(args,schema);save(args.out/'recipe.json',recipe)
    environment={'comfyui':comfy.call('system_stats')['system'], 'runner_sha256':fingerprint(Path(__file__)), 'assembler_sha256':fingerprint(HERE/'assemble.py'),'branch_volume_sha256':fingerprint(HERE/'branch_volume.py')}
    try:environment['comfyui_revision']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=args.comfy_root,text=True,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0).strip()
    except subprocess.CalledProcessError:environment['comfyui_revision']='unavailable'
    save(args.out/'environment.json',environment)
    reference=Path(recipe['reference']) if recipe.get('reference') else None
    if reference and not reference.is_absolute():reference=args.brief.resolve().parent/reference
    if reference and not reference.is_file():raise FileNotFoundError(reference)
    full=pinned['reference'] if pinned else image_stage('reference',reference,args,comfy,schema,models)
    wood_input=Path(recipe['wood_reference_source']) if recipe.get('wood_reference_source') else None if recipe.get('independent_wood_reference') else full
    wood_ref=None
    if not shrub:
        wood_ref=pinned['wood_reference'] if pinned else image_stage('wood_reference',wood_input,args,comfy,schema,models)
        reference_check=wood_reference_check(wood_ref,recipe.get('allow_green_stems',False));save(args.out/'wood-reference-check.json',reference_check)
        if recipe.get('require_leafless_wood') and reference_check['status']!='pass':
            raise ValueError('Wood reference still contains foliage; regenerate the bare structure before spending GPU time on reconstruction')
    cluster=pinned['cluster_reference'] if pinned else image_stage('cluster_reference',full,args,comfy,schema,models)
    leaf=pinned['leaf_reference'] if pinned else image_stage('leaf_reference',cluster,args,comfy,schema,models)
    if args.references_only:
        review={'status':'reference art review; no 3D inference requested','prepared_source':reference_set,
                'images':{label:{'path':str(path),'sha256':fingerprint(path)} for label,path in
                          [('reference',full),('wood_reference',wood_ref),('cluster_reference',cluster),('leaf_reference',leaf)] if path is not None}}
        save(args.out/'reference-review.json',review)
        print(json.dumps(review,indent=2),flush=True)
        return
    if recipe.get('wood_source'):
        wood={'low_pbr':Path(recipe['wood_source'])}
    else:
        body=json.loads((HERE/('templates/wood_'+recipe['geometry_backend']+'.json')).read_text());p=body['prompt'];p['122']['inputs']['image']=upload_reference(wood_ref,args)
        p['351']['inputs']['target_face_count']=recipe['wood_triangles']
        if 'geometry_seed' in recipe:
            for node in p.values():
                if 'seed' in node['inputs']:node['inputs']['seed']=(int(node['inputs']['seed'])+recipe['geometry_seed'])%(2**31)
        for identifier,field in [('353','resolution'),('354','texture_size'),('355','resolution')]:p[identifier]['inputs'][field]=recipe['texture_resolution']
        wood=stage('wood_mesh',body,{'342':'high_raw','343':'high_colour','358':'low_pbr','360':'basecolor','361':'normal','362':'roughness','363':'metallic'},args,comfy,schema,models)
    topology_folder=args.out/'wood_source'/fingerprint(wood['low_pbr'])[:16] if recipe.get('wood_source') else wood['low_pbr'].parent
    topology_folder.mkdir(parents=True,exist_ok=True);topology_file=topology_folder/'topology.json'
    if recipe.get('reject_branch_cycles'):
        topology=json.loads(topology_file.read_text()) if topology_file.exists() else {}
        if topology.get('auditor_sha256')!=fingerprint(HERE/'topology.py') or topology.get('source_sha256')!=fingerprint(wood['low_pbr']):
            command=[str(args.blender),'--background','--factory-startup','--threads','4','--python-exit-code','1','--python',str(HERE/'topology.py'),'--',str(wood['low_pbr']),'--out',str(topology_file)]
            with topology_file.with_suffix('.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        if json.loads(topology_file.read_text())['suspect']:raise ValueError('Generated wood has a potential branch cycle; retain evidence and retry a different geometry seed')
    body=json.loads((HERE/'templates/alpha.json').read_text());body['prompt']['1']['inputs']['image']=upload_reference(leaf,args)
    atlas=stage('leaf_alpha',body,{'6':'image'},args,comfy,schema,models)['image']
    cook_key=key({'wood':fingerprint(wood['low_pbr']),'leaf':fingerprint(atlas),'recipe':recipe,'script':fingerprint(HERE/'assemble.py'),'branch_volume':fingerprint(HERE/'branch_volume.py')})
    cooked=args.out/'cook'/cook_key[:16];cooked.mkdir(parents=True,exist_ok=True);asset=cooked/'plant.glb';cook_recipe=cooked/'recipe.json';save(cook_recipe,recipe)
    if not asset.exists() or not (cooked/'assembly-report.json').exists():
        command=[str(args.blender),'--background','--factory-startup','--threads','4','--python-exit-code','1','--python',str(HERE/'assemble.py'),'--','--wood',str(wood['low_pbr']),'--leaf',str(atlas),'--recipe',str(cook_recipe),'--out',str(cooked)]
        print('Cook: assembling supported shoots and leaves on CPU',flush=True)
        with (cooked/'blender.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    audit=check(asset,recipe['max_triangles'],recipe['height_m']);save(cooked/'audit.json',audit)
    manifest={'status':'complete; artistic acceptance pending','recipe':str(args.out/'recipe.json'),'environment':str(args.out/'environment.json'),'reference':{'path':str(reference.resolve()),'sha256':fingerprint(reference)} if reference else None,'prepared_references':reference_set,'wood_source':{'path':str(wood['low_pbr']),'sha256':fingerprint(wood['low_pbr']),'topology':str(topology_file)},'models':models,'asset':str(asset),'sha256':fingerprint(asset),'audit':audit,'review':str(cooked/'review.blend'),'preview':str(cooked/'quarter.png'),'runtime_integration':False,'benchmarks_run':False}
    save(args.out/'manifest.json',manifest);print(json.dumps(manifest,indent=2),flush=True)


if __name__=='__main__':
    try:main()
    except GpuBudgetUnavailable as error:
        print(str(error),flush=True);raise SystemExit(75)
