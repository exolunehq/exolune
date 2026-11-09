"""Resumable local biome library: five trees and five shrubs per climate family.

Planning is CPU-only. Generation waits for other engines, retains rejected
attempts and never labels an unreviewed candidate production-ready.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
BLENDER=Path('C:/Program Files/Blender Foundation/Blender 5.2/blender.exe')
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'tools/tests'))
from banc_local3d import freeze_catalogue,sha
from check_local3d_native import assets
from banc_local3d import RUNTIME
from variations import derive,PROFILES

# Botanical inspirations define different silhouettes and leaf/stem structures.
# They do not claim that every member of a broad climate family coexists locally.
BIOMES={
'boreal':{
 'trees':[('scots_pine','Scots pine','rugged orange-brown trunk, high asymmetrical umbrella of layered needle sprays','one short airy pine needle spray with a slender brown petiole'),
          ('siberian_spruce','Siberian spruce','straight sturdy trunk, dense tiered pointed conical crown, hanging lower branch tips','one small flat spruce needle spray with a visible brown petiole'),
          ('siberian_fir','Siberian fir','thick grey trunk, orderly broad lower boughs and a narrow pointed top','one small flat fir needle spray, pale undersides, a brown petiole'),
          ('siberian_larch','Siberian larch','warm fissured bark, airy irregular crown of horizontal limbs and light green needle tufts','one small larch needle tuft attached to a short brown petiole'),
          ('siberian_pine','Siberian stone pine','strong forked trunk, compact rounded layered crown of dense long needle tufts','one compact five-needle pine tuft attached to a brown petiole')],
 'shrubs':[('juniper','common juniper','low spreading dense evergreen with woody twisted stems','one small prickly juniper needle spray'),('bilberry','bilberry','low airy branching mound with green angular stems','one small oval softly serrated bilberry leaf'),('lingonberry','lingonberry','compact low evergreen with many short woody shoots','one thick small rounded glossy evergreen leaf'),('labrador_tea','Labrador tea','upright open woody shrub with rust-brown stems','one narrow leathery leaf with rolled edges'),('boreal_willow','boreal willow','rounded irregular multi-stem shrub with smooth slender branches','one elongated matte willow leaf')]},
'desert':{
 'trees':[('mesquite','velvet mesquite','gnarled branching trunk, broad airy low umbrella, sparse tiny paired leaflets','one small mesquite compound leaf with paired tiny leaflets'),('palo_verde','blue palo verde','thick blue-green branching trunks, open arched crown with very small leaves','one tiny palo verde compound leaf with a short petiole'),('ironwood','desert ironwood','stout dark twisted trunk, broad irregular rounded canopy, sparse grey-green foliage','one grey-green oval ironwood leaflet'),('catclaw','catclaw acacia','multi-trunk small tree, tangled but separate tapering limbs, open airy umbrella','one delicate bipinnate acacia leaf with a short petiole'),('desert_willow','desert willow','sculptural multi-stem trunk, loose upright spreading crown','one narrow long willow-like dark green leaf')],
 'shrubs':[('creosote','creosote bush','open fountain of warm brown woody stems with sparse paired waxy leaves','one paired creosote leaf unit'),('bursage','white bursage','low rounded grey-green finely branched mound','one small deeply lobed silver-grey leaf'),('brittlebush','brittlebush','rounded low woody bush with separated broad soft leaves','one fuzzy triangular silver-green leaf'),('fairy_duster','fairy duster','airy arching woody shrub, fine thin compound foliage','one tiny bipinnate compound leaf'),('saltbush','fourwing saltbush','loose grey rounded shrub, stout old base and sparse branch tips','one narrow grey-green saltbush leaf')]},
'steppe':{
 'trees':[('downy_oak','downy oak','short substantial crooked trunk, broad irregular dry woodland crown','one small lobed downy oak leaf'),('oriental_hornbeam','oriental hornbeam','multi-stem warm grey trunk, low spreading irregular canopy','one small sharply serrated oval hornbeam leaf'),('terebinth','terebinth','sculptural multiple trunks, open broad rounded canopy','one small oval leathery terebinth leaflet'),('montpellier_maple','Montpellier maple','low crooked grey trunk and an airy flat rounded crown','one small three-lobed maple leaf'),('prickly_juniper','prickly juniper','old twisted reddish trunk, uneven compact evergreen crown','one small pointed juniper needle spray')],
 'shrubs':[('rockrose','rockrose','low broad rounded woody shrub with soft grey leaves','one grey-green oval softly textured leaf'),('rosemary','rosemary','upright irregular woody shrub with dense fine aromatic foliage','one short rosemary shoot with thin needle-like leaves'),('thyme','wild thyme','low spreading cushion with visible fine woody stems','one tiny thyme leaf pair'),('thorny_burnet','thorny burnet','dense low cushion with a strong old woody core and airy twig ends','one tiny compound burnet leaf'),('wormwood','white wormwood','irregular low grey woody mound with sparse upright tips','one fine divided silver-green wormwood leaf')]},
'montane':{
 'trees':[('stone_pine','Swiss stone pine','stout wind-shaped trunk, irregular rounded layered high-altitude crown','one dense small pine needle spray'),('alpine_spruce','alpine Norway spruce','tapered straight dark trunk, narrow layered conical crown and visible lower boughs','one flat spruce needle spray'),('european_larch','European larch','strong warm reddish trunk, open layered crown of light green tufts','one delicate larch needle tuft'),('silver_fir','silver fir','substantial pale grey trunk and broad tiered conical evergreen crown','one flat fir spray with a visible short brown petiole'),('mountain_pine','mountain pine','low strong crooked multi-trunk tree, broad asymmetric compact needle crown','one compact pine needle spray')],
 'shrubs':[('alpine_rose','alpine rhododendron','dense low spreading woody bush with irregular tips','one thick elongated dark green alpine rhododendron leaf'),('dwarf_willow','dwarf willow','very low prostrate woody shrub with a small raised canopy','one small round veined matte leaf'),('alpine_juniper','alpine juniper','prostrate old woody stems supporting irregular dense needle cushions','one short small juniper needle spray'),('green_alder','green alder','low arching multi-stem shrub, strongly branching and broad-leaved','one rounded serrated green alder leaf'),('bog_bilberry','bog bilberry','open low woody mound with grey twiggy stems','one small rounded blue-green bilberry leaf')]},
'temperate':{
 'trees':[('beech','European beech','smooth thick silver-grey trunk, several clearly separated powerful limbs, full high domed crown','one oval slightly wavy-edged beech leaf'),('oak','pedunculate oak','warm deeply fissured substantial trunk, strong crooked separate limbs, broad irregular crown','one clearly lobed mature oak leaf'),('hornbeam','European hornbeam','thick fluted grey trunk, elegant multiple ascending limbs and a layered oval crown','one pointed oval double-serrated hornbeam leaf'),('maple','field maple','warm grey strongly branching trunk with an airy uneven broad crown','one small five-lobed field maple leaf'),('birch','silver birch','substantial white and warm grey bark, upright trunk with graceful separate arching limbs and open hanging sprays','one small triangular serrated birch leaf')],
 'shrubs':[('hazel','hazel','rounded multi-stem shrub with warm brown basal stems and broad full foliage','one large rounded softly hairy serrated hazel leaf'),('holly','holly','compact uneven evergreen shrub with thick grey stems and dense dark foliage','one thick glossy dark green spiny holly leaf'),('hawthorn','hawthorn','gnarled woody multi-stem shrub, open layered tips and clear old branch structure','one small lobed hawthorn leaf'),('dogwood','common dogwood','airy upright shrub with distinct reddish woody stems and arching tips','one oval dogwood leaf with curved veins'),('spindle','European spindle','open angular woody shrub with a clearly readable branching silhouette','one oval pointed finely serrated spindle leaf')]},
'tropical':{
 'trees':[('kapok','kapok','massive warm grey trunk, low broad buttress roots merging into the soil, lofty umbrella canopy with separate major branches','one complete palmate kapok leaf with a short petiole'),('rainforest_fig','rainforest fig','broad substantial flared trunk, separate sinuous supporting limbs, dense uneven rounded crown; no strangler loops or hanging aerial roots','one large oval leathery tropical fig leaf'),('mahogany','big-leaf mahogany','tall warm brown straight bole, several powerful separate ascending limbs and a high irregular domed crown','one large elongated pointed mahogany leaflet'),('cecropia','cecropia','strong pale trunk with distinct tiered horizontal limbs, open umbrella crown of large separated leaves','one large deeply palmate lobed cecropia leaf'),('inga','inga','broad warm grey trunk, long separate arching limbs and a low layered spreading canopy','one large elliptical inga leaflet')],
 'shrubs':[('psychotria','Psychotria','upright dark woody shrub with broad glossy leaves in opposite pairs','one glossy elliptical tropical understory leaf'),('piper','Piper aduncum','airy arching woody shrub, slender green-brown stems and large soft foliage','one large pointed asymmetric heart-based Piper leaf'),('miconia','Miconia','strong multi-stem tropical shrub with a full irregular crown','one large oval matte tropical leaf with three prominent longitudinal veins'),('palicourea','Palicourea','open branching understory shrub with upright stems and opposite foliage','one large smooth elongated glossy green leaf'),('isertia','Isertia','broad uneven woody shrub with sturdy branch forks and soft full foliage','one broad oval softly textured green tropical leaf')]}}

SHRUB_SCAFFOLDS = {
    'temperate_shrub_hazel': dict(stems=7, spread=.64, arch=.18, bend=.24, flare=.38, bark=[.22, .133, .085]),
    'temperate_shrub_dogwood': dict(stems=6, spread=.42, arch=.23, bark=[.31, .113, .074]),
    'tropical_shrub_psychotria': dict(stems=5, spread=.36, arch=.055, bark=[.19, .14, .083]),
    'tropical_shrub_piper': dict(stems=5, spread=.62, arch=.22, bark=[.20, .19, .084]),
}
SHRUB_LEAVES = {
    'temperate_shrub_hazel': [.10, .17],
    'temperate_shrub_dogwood': [.085, .14],
    'tropical_shrub_psychotria': [.14, .24],
    'tropical_shrub_piper': [.16, .27],
}

SOURCES=['https://science.nasa.gov/kids/earth/mission-biomes/biotemperate/',
         'https://www.nps.gov/im/sodn/ecosystems.htm',
         'https://www.adfg.alaska.gov/static/species/wildlife_action_plan/appendix5_forest_habitats.pdf',
         'https://www.nationalparks.nsw.gov.au/~/media/E8073DC1918348D3AD95B4650C8FE915.ashx',
         'https://www.luontoon.fi/en/destinations/urho-kekkonen-national-park/nature']


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix('.'+str(os.getpid())+'.tmp')
    temp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');temp.replace(path)


def plan(out):
    jobs=[]
    for family,(biome,groups) in enumerate(BIOMES.items()):
        for kind,records in groups.items():
            for variant,(slug,species,shape,leaf) in enumerate(records):
                name=biome+'_'+('tree_' if kind=='trees' else 'shrub_')+slug
                seed=int(hashlib.sha256(name.encode()).hexdigest()[:7],16)
                tree=kind=='trees';height=8.0 if tree else 1.8
                style='Premium first-person game vegetation, warm tactile substantial organic volumes, softly simplified natural forms, individual readable foliage, neither cartoon nor a thin photographic sapling.'
                framing='Complete isolated subject with every root and leaf tip visible, ten percent empty margin, plain pale grey background, neutral diffuse lighting, no cast shadow, no floor slab, no pot, no landscape, no text.'
                structure='Every branch forks outward and tapers to a free tip. Branches never reconnect, fuse, form rings, bridge separate limbs or grow back into the trunk. Roots are low solid flares with undersides at soil level, not raised arches.'
                volume='Strongly three-dimensional radial branching all around the trunk, through the full 360 degrees. Several substantial boughs point toward the viewer with clear foreshortening; other boughs extend behind the trunk. Crown depth is comparable to crown width. Oblique three-quarter view revealing the front, side and depth. Irregular organic asymmetry within a full spatial volume.'
                wood_shape=', '.join(part for part in shape.split(', ') if not any(word in part.lower() for word in ['crown','canopy','foliage','leaf','needle']))
                recipe={'name':name,'description':f'{species}, {biome} climate. {shape}. {style}',
                    'reference':None,'geometry_backend':'trellis2','height_m':height,'wood_triangles':12000 if tree else 6000,
                    'max_triangles':40000 if tree else 18000,'cluster_limit':400 if tree else 150,
                    'texture_resolution':2048 if tree else 1024,'image_resolution':1024,'seed':seed,'geometry_seed':seed,
                    'foliage_distribution':'crown_volume','cluster_spacing_m':.38 if tree else .11,'max_connector_m':2.0 if tree else .55,
                    'leaf_length_m':[.20,.34] if tree else [.055,.11],'shoot_length_m':[.65,1.0] if tree else [.16,.28],
                    'leaf_arrangement':'opposite' if slug in ['maple','dogwood','psychotria','palicourea'] else 'alternate',
                    'min_foliage_height':.34 if tree else .18,'crown_centre':.69 if tree else .56,'crown_depth':.30 if tree else .40,
                    'crown_profile':'cone' if tree and biome in ['boreal','montane'] and slug not in ['scots_pine','mountain_pine','stone_pine'] else 'irregular',
                    'reject_branch_cycles':True,'image_seeds':{stage:seed+i*7919 for i,stage in enumerate(['reference','wood_reference','cluster_reference','leaf_reference'])},
                    'independent_wood_reference':True,'require_leafless_wood':True,'allow_green_stems':slug in ['palo_verde','bilberry','piper'],
                    'captions':{
                      'reference':f'A mature {species}, {shape}. {volume} {style} {structure} {framing}',
                      'wood_reference':f'A completely LEAFLESS {species}. Show ONLY bare wood: {wood_shape}. Substantial tactile trunk and a limited number of powerful clearly separated tapering supporting limbs. {volume} Generous empty space between limbs. No fine twig lattice. All leaves, green foliage, needle sprays, leafy bouquets and canopy masses are entirely absent. Only bark-covered branches remain, each ending freely. No green dots or needles anywhere. {structure} {style} {framing}',
                      'cluster_reference':f'Exactly one short leafy branch of the same {species} in <ref_image_0>, with individually readable botanical foliage: {leaf}. A brown twig enters from bottom centre. {style} {framing}',
                      'leaf_reference':f'Exactly {leaf}, matching <ref_image_0>. Isolated flat botanical game cutout with its complete short brown petiole pointing straight down and leaf tip at top. Deep natural green, olive highlights, weak shading, no other leaves, no branch network. {style} {framing}'}}
                if slug in ['cecropia','kapok']:recipe['leaf_length_m']=[.32,.52]
                if biome=='desert':recipe.update(cluster_limit=260 if tree else 120,cluster_spacing_m=.45 if tree else .14)
                if name in SHRUB_SCAFFOLDS:
                    recipe.update(shrub_scaffold=SHRUB_SCAFFOLDS[name], wood_triangles=750,
                                  max_triangles=7000, cluster_limit=80, leaf_length_m=SHRUB_LEAVES[name],
                                  min_foliage_height=.28, foliage_distribution='surface',
                                  cluster_spacing_m=.085, shoot_length_m=[.12,.23],
                                  shoot_upward_bias=.17, branch_alignment=.55)
                relative='recipes/'+name+'.json';save(out/relative,recipe)
                jobs.append({'name':name,'biome':biome,'family':family,'kind':kind,'variant':variant,
                             'slot':31+family*10+(0 if tree else 5)+variant,'recipe':relative,'botanical_inspiration':species})
    # Prioritise the two environments the user has just reviewed, then all trees,
    # followed by all shrubs. State is per asset, not tied to queue position.
    priority=['temperate_tree_beech','tropical_tree_kapok','temperate_shrub_hazel','tropical_shrub_psychotria']
    jobs.sort(key=lambda j:(priority.index(j['name']) if j['name'] in priority else 10+(0 if j['kind']=='trees' else 100)+j['family']*5+j['variant']))
    result={'schema':1,'status':'60 distinct woody candidates planned; no generation or acceptance implied','jobs':jobs,
            'sources':SOURCES,'scope':'Six existing climate families; dry woodland trees remain restricted by the existing growth laws. Names guide architecture, not an exact terrestrial species census.',
            'next_ground_layer':['woodland anemone patches','violet patches','dry grass tussocks','temperate tall grass','tropical fern clumps','tropical broad-leaf ground clumps','alpine flower cushions','desert seasonal flower patches']}
    save(out/'plan.json',result);return result


def run_job(command,log):
    with log.open('a',encoding='utf-8') as stream:
        return subprocess.run(list(map(str,command)),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0).returncode


def comfy_available(url='http://127.0.0.1:8188'):
    # An unavailable local service is an infrastructure wait, never a rejected
    # botanical source. Keep the three modelling attempts for actual models.
    try:
        with urllib.request.urlopen(url.rstrip('/')+'/queue',timeout=3) as response:
            queue=json.load(response)
        return 'queue_running' in queue and 'queue_pending' in queue
    except (OSError,ValueError):return False


def reuse_stages(previous,current):
    # Each stage key already includes its graph and model hashes. Changed wood
    # prompts/seeds get a different directory; unchanged leaf references reuse
    # their verified historical files and execution records.
    for stage in ['reference','wood_reference','cluster_reference','leaf_reference','wood_mesh','leaf_alpha']:
        for source in (previous/stage).glob('*/state.json'):
            state=json.loads(source.read_text())
            if state.get('status')!='complete':continue
            if not all(Path(v['path']).is_file() and sha(Path(v['path']))==v['sha256'] for v in state['artifacts'].values()):continue
            target=current/stage/source.parent.name
            if (target/'state.json').exists():continue
            target.mkdir(parents=True,exist_ok=True)
            for original in source.parent.iterdir():
                if not original.is_file() or (target/original.name).exists():continue
                dest=target/original.name
                if original.suffix.lower() in ['.png','.glb']:
                    try:os.link(original,dest)
                    except OSError:shutil.copyfile(original,dest)
                else:shutil.copyfile(original,dest)


def structural_variants(out,job,state):
    """Cheap offline derivatives; no resident-pool or acceptance implication."""
    manifest=json.loads((Path(state['authoring'])/'manifest.json').read_text())
    source=Path(manifest['asset']);recipe=json.loads((out/job['recipe']).read_text())
    if sha(source)!=manifest['sha256']:raise ValueError('Plant master fingerprint changed')
    cook={'tile':recipe['texture_resolution']}
    if job['kind']=='shrubs':cook['shrub_family']=job['family']
    # Masters and derivatives enter the same complete acceptance chain. The
    # library queue only cooks candidates; it never starts benchmark campaigns.
    master_production={'name':job['name'],'height_m':recipe['height_m'],'source_triangle_budget':recipe['max_triangles'],
                       'target_fps':60,'source':{'glb':str(source),'sha256':manifest['sha256'],'art_approved':False},
                       'cook':cook}
    save(out/'plants'/job['name']/'production.json',master_production)
    spec={'master':manifest['sha256'],'profiles':list(PROFILES),'seed':recipe['seed'],'script':sha(HERE/'variations.py')}
    signature=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()[:16]
    root=out/'plants'/job['name']/'structural-variants'/signature;root.mkdir(parents=True,exist_ok=True)
    variants=[]
    for index,profile in enumerate(PROFILES):
        asset=root/profile/'plant.glb';seed=recipe['seed']+index*104729
        if not asset.exists():derive(source,asset,profile,seed,recipe['max_triangles'])
        info=json.loads(asset.with_suffix('.variation.json').read_text())
        if info['master_sha256']!=manifest['sha256'] or info['script_sha256']!=spec['script'] or info['sha256']!=sha(asset):
            raise ValueError('Structural variant cache changed')
        production={'name':job['name']+'_'+profile,'height_m':recipe['height_m'],'source_triangle_budget':recipe['max_triangles'],
                    'target_fps':60,'source':{'glb':str(source),'sha256':manifest['sha256'],'art_approved':False},
                    'variation':{'profile':profile,'seed':seed,'art_approved':False,'approved_sha256':info['sha256']},'cook':cook}
        production_file=asset.parent/'production.json';save(production_file,production)
        variants.append({'profile':profile,'asset':str(asset),'sha256':info['sha256'],'production_recipe':str(production_file),
                         'status':'derived; own native LODs, impostor and acceptance required','production_ready':False})
    save(root/'variants.json',{'inputs':spec,'variants':variants,'residency':'offline only; review bank still selects one master per role'})
    return variants


def bank(out,allow_fallback=False):
    inventory=json.loads((out/'plan.json').read_text());base=out/'_baseline'
    base_rows=[line.split() for line in (base/'biomes.txt').read_text().splitlines()[1:]]
    states={};ready={}
    for job in inventory['jobs']:
        path=out/'plants'/job['name']/'state.json'
        state=json.loads(path.read_text()) if path.exists() else {'status':'queued'}
        states[job['name']]=state
        if state['status']=='cooked_needs_review':ready[job['slot']]=(job,state)
    if not ready and not allow_fallback:return None
    signature={str(slot):state['audit']['hashes'] for slot,(_,state) in ready.items()}
    digest=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()[:16]
    target=out/'review-banks'/digest;target.mkdir(parents=True,exist_ok=True)
    rows=base_rows.copy();origins={name:base/name for name,_,_ in base_rows};roles=[]
    for job in sorted(inventory['jobs'],key=lambda j:j['slot']):
        if job['slot'] in ready:
            _,state=ready[job['slot']];catalogue=Path(state['native']);info=json.loads((catalogue/'native-report.json').read_text())
            row=[job['name'],str(0 if job['kind']=='trees' and job['family'] in [0,3] else 1 if job['kind']=='trees' else 2),str(info['leaf_mask'])]
            origins[job['name']]=catalogue/job['name'];status='generated candidate; art and native acceptance pending'
        else:
            if job['kind']=='shrubs':slot=2+2*job['family']+job['variant']%2
            elif job['family'] in [0,3]:slot=[0,14,15,0,14][job['variant']]
            else:slot=[1,16,17,18,19][job['variant']]
            row=base_rows[slot];status='temporary baseline fallback; not a newly generated model'
        rows.append(row);roles.append(job|{'status':status,'folder':row[0]})
    assert len(rows)==91
    # Legacy roles remain readable, but share completed candidate resources;
    # they must not retain a second complete tree/shrub library in VRAM.
    aliases={0:31,14:32,15:33,1:71,16:72,17:73,18:74,19:75,20:76,21:77,22:86}
    for family in range(6):
        aliases[2+2*family]=36+10*family;aliases[3+2*family]=37+10*family
    for legacy,generated in aliases.items():
        if generated in ready:rows[legacy]=rows[generated]
    for name in sorted({r[0] for r in rows}):
        folder=target/name;folder.mkdir(exist_ok=True)
        for filename in RUNTIME:
            original=origins[name]/filename
            if not original.exists():continue
            dest=folder/filename
            if not dest.exists():
                try:os.link(original,dest)
                except OSError:shutil.copyfile(original,dest)
    save(target/'bank-report.json',{'status':'review only; not production-ready','generated_candidates':len(ready),'planned_woody_models':60,'roles':roles})
    # The manifest is the publication marker; every referenced resource exists first.
    (target/'biomes.txt').write_text('FOLBIO03 91\n'+'\n'.join(' '.join(row) for row in rows)+'\n',encoding='ascii')
    save(out/'review-bank.json',{'catalogue':str(target),'generated_candidates':len(ready),'planned':60,'production_ready':False})
    lines=['# Local vegetation library','',f'Generated candidates: **{len(ready)} / 60**. Native acceptance remains pending.','',
           '| Biome | Plant | State | 3D preview |','|---|---|---|---|']
    for job in inventory['jobs']:
        state=states[job['name']];preview=''
        if state['status']=='cooked_needs_review':
            manifest=json.loads((Path(state['authoring'])/'manifest.json').read_text());preview='[3D render]('+Path(manifest['preview']).as_posix()+')'
        lines.append(f"| {job['biome']} | {job['botanical_inspiration']} | {state['status']} | {preview} |")
    (out/'gallery.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return target


def run(out,minutes,limit,allow_shared,comfy_url='http://127.0.0.1:8188',plant=None):
    inventory=json.loads((out/'plan.json').read_text());base=out/'_baseline'
    jobs=[job for job in inventory['jobs'] if not plant or job['name']==plant]
    if not jobs:raise ValueError('Plant does not appear in the library plan: '+plant)
    if not (base/'biomes.txt').exists():freeze_catalogue(ROOT/'assets/foliage/game_biomes_v1',base,{})
    deadline=time.monotonic()+minutes*60;completed=0
    with (out/'library.lock').open('a+b') as lock:
        if os.name=='nt':
            import msvcrt
            lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        while time.monotonic()<deadline:
            progressed=False
            for job in jobs:
                if (out/'pause.flag').exists():
                    save(out/'progress.json',{'status':'paused for native functional checks; no asset is lost'});time.sleep(5);break
                if not comfy_available(comfy_url):
                    save(out/'progress.json',{'status':'waiting for local ComfyUI service; modelling attempts preserved'});time.sleep(20);break
                folder=out/'plants'/job['name'];folder.mkdir(parents=True,exist_ok=True);state_file=folder/'state.json'
                state=json.loads(state_file.read_text()) if state_file.exists() else {'status':'queued','attempt':0}
                if state['status'] in ['cooked_needs_review','rejected_after_retries','cook failed; retained for review','native audit failed']:continue
                if shutil.disk_usage(out).free<8*2**30:save(out/'progress.json',{'status':'waiting for disk space','minimum_free_GiB':8});return
                save(out/'progress.json',{'status':'authoring with VRAM admission' if allow_shared else 'authoring; waits for other engines before inference','current':job,'completed_this_run':completed})
                attempt=folder/f"attempt_{state['attempt']:02}";attempt.mkdir(exist_ok=True)
                recipe=json.loads((out/job['recipe']).read_text(encoding='utf-8'));shift=state['attempt']*104729
                recipe['geometry_seed']+=shift;recipe['seed']+=shift
                recipe['image_seeds']['wood_reference']+=shift;save(attempt/'recipe.json',recipe)
                authoring=attempt/'authoring';authoring.mkdir(exist_ok=True)
                if state['attempt']:
                    for previous in folder.glob('attempt_*/authoring'):
                        if previous!=authoring:reuse_stages(previous,authoring)
                cached=Path('E:/ExoluneAssets/oak-witness-v1/model-hashes.json')
                if cached.exists() and not (authoring/'model-hashes.json').exists():shutil.copyfile(cached,authoring/'model-hashes.json')
                log=attempt/'authoring.log';save(state_file,state|{'status':'authoring','log':str(log)})
                start_offset=log.stat().st_size if log.exists() else 0
                command=['E:/ComfyUI/.venv/Scripts/python.exe',HERE/'pipeline.py',attempt/'recipe.json','--out',authoring,'--yield-if-gpu-busy','--comfy-url',comfy_url]
                if recipe.get('shrub_scaffold'):
                    identity=sha(attempt/'recipe.json')[:16]+'-'+sha(HERE/'shrub_scaffold.py')[:16]
                    candidates=sorted(attempt.glob(f'scaffold-{identity}-*/scaffold-report.json'))
                    if candidates:
                        scaffold=candidates[-1].parent
                        report=json.loads(candidates[-1].read_text())
                        if report['wood_sha256']!=sha(scaffold/'wood.glb'):
                            raise ValueError('Cached shrub scaffold changed: '+str(scaffold))
                    else:
                        scaffold=attempt/f'scaffold-{identity}-{time.time_ns()}'
                        code=run_job([BLENDER,'--background','--factory-startup','--threads','4',
                                      '--python-exit-code','1','--python',HERE/'shrub_scaffold.py',
                                      '--',attempt/'recipe.json','--out',scaffold],attempt/'scaffold.log')
                        if code:raise RuntimeError('Shrub scaffold failed; see '+str(attempt/'scaffold.log'))
                    command+=['--wood-source',scaffold/'wood.glb']
                if allow_shared:command+=['--allow-shared-gpu']
                code=run_job(command,log)
                if code:
                    with log.open('rb') as stream:stream.seek(start_offset);tail=stream.read().decode('utf-8',errors='replace')[-12000:]
                    if any(s in tail.lower() for s in ['prompt_outputs_failed_validation','value_not_in_list','invalid_prompt']):
                        save(state_file,state|{'status':'waiting for service','log':str(log)})
                        save(out/'progress.json',{'status':'waiting for ComfyUI model/workflow configuration; modelling attempts preserved','log':str(log)})
                        time.sleep(20);break
                    if any(s in tail.lower() for s in ['connection refused','actively refused','winerror 10061']):
                        save(state_file,state|{'status':'waiting for service','log':str(log)});continue
                    if code==75 or any(s in tail.lower() for s in ['gpu budget unavailable','game still running','comfyui is busy','out of memory','is still running']):
                        save(state_file,state|{'status':'waiting for GPU','log':str(log)});continue
                    state['attempt']+=1;state['status']='rejected_after_retries' if state['attempt']>=3 else 'queued'
                    save(state_file,state|{'last_error_log':str(log)});progressed=True;continue
                manifest=json.loads((authoring/'manifest.json').read_text());native=attempt/'native'
                if not (native/'biomes.txt').exists():
                    # An interrupted cook is retained; retry into a fresh directory.
                    if native.exists():native=attempt/f'native_retry_{time.time_ns()}'
                    cook=[sys.executable,HERE/'native.py','--source',manifest['asset'],'--out',native,
                          '--base',base,'--lods','--name',job['name'],'--tile',str(recipe['texture_resolution'])]
                    if job['kind']=='shrubs':cook+=['--shrub-family',str(job['family'])]
                    code=run_job(cook,attempt/'native.log')
                    if code:save(state_file,state|{'status':'cook failed; retained for review','authoring':str(authoring),'log':str(attempt/'native.log')});continue
                try:audit=assets(native)
                except Exception as error:save(state_file,state|{'status':'native audit failed','error':str(error),'native':str(native)});continue
                cooked_state=state|{'status':'cooked_needs_review','native':str(native),'authoring':str(authoring),'source_sha256':manifest['sha256'],'audit':audit,
                                    'production_ready':False,'native_visual_review':'pending','performance':'pending',
                                    'production_recipe':str(folder/'production.json')}
                try:cooked_state['structural_variants']=structural_variants(out,job,cooked_state)
                except Exception as error:cooked_state['variant_error']=str(error)
                save(state_file,cooked_state)
                progressed=True;completed+=1
                bank(out)
                if limit and completed>=limit:return
            else:
                pending=[]
                for job in jobs:
                    f=out/'plants'/job['name']/'state.json';s=json.loads(f.read_text()) if f.exists() else {'status':'queued'}
                    if s['status'] in ['queued','waiting for GPU','waiting for service','authoring']:pending.append(job)
                if not pending:return
                if not progressed:
                    save(out/'progress.json',{'status':'waiting for GPU capacity; stages checkpointed','pending_assets':len(pending),'mode':'VRAM admission' if allow_shared else 'exclusive engine admission'})
                    time.sleep(20)
                continue
            if not progressed:time.sleep(10)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['plan','run','bank','variants']);p.add_argument('--out',type=Path,default=Path('E:/ExoluneAssets/biome-library'))
    p.add_argument('--plant',help='Restrict generation or variant derivation to one plant')
    p.add_argument('--comfy-url',default='http://127.0.0.1:8188',help='Local ComfyUI endpoint; forwarded to each checkpointed stage')
    p.add_argument('--watch-minutes',type=float,default=720);p.add_argument('--limit',type=int,default=0)
    p.add_argument('--allow-shared-gpu',action='store_true');a=p.parse_args();out=a.out.resolve()
    if out.drive.lower()!='e:':raise ValueError('Library assets belong on E:')
    out.mkdir(parents=True,exist_ok=True)
    if a.action=='plan':print(json.dumps({'assets':len(plan(out)['jobs']),'plan':str(out/'plan.json')},indent=2))
    elif a.action=='bank':print(bank(out,allow_fallback=True))
    elif a.action=='variants':
        inventory=json.loads((out/'plan.json').read_text());processed=[]
        for job in inventory['jobs']:
            if a.plant and job['name']!=a.plant:continue
            path=out/'plants'/job['name']/'state.json'
            state=json.loads(path.read_text()) if path.exists() else {}
            if state.get('status')!='cooked_needs_review':continue
            state['structural_variants']=structural_variants(out,job,state);state['production_recipe']=str(path.parent/'production.json')
            state.pop('variant_error',None);save(path,state)
            processed.append(job['name'])
        if a.plant and not processed:raise ValueError('Plant has no successfully cooked master: '+a.plant)
        print(json.dumps({'plants':processed,'variants_per_plant':len(PROFILES),'native_cook_and_acceptance':'required for every selected variation'},indent=2))
    else:run(out,a.watch_minutes,a.limit,a.allow_shared_gpu,a.comfy_url,a.plant)


if __name__=='__main__':main()
