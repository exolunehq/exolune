"""Comparaison climatique hors ecran : reference/candidat, un processus GPU a la fois.

La famille candidate indiquee dans le manifeste est une hypothese a verifier, et
les vues voisines ne constituent pas des regions independantes. Les temps GPU
sont indicatifs lorsque le vol interactif ou une autre charge utilise le GPU.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import struct
import time

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / 'tools/foliage/arbustes_climat_vues.json'
# Les scans de sol, hors du depot (tools/telecharger_scans.ps1) : a cote de la worktree par defaut.
SCANS = Path(os.environ.get('MYPLANETENGINE_SCANS', ROOT.parent / 'scans'))
FAMILIES = ('boreal', 'desert', 'steppe', 'montane', 'temperate', 'tropical')


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def snapshot_hashes(exe, assets):
    shaders = {p.name: sha256(p) for p in sorted(exe.parent.glob('*.cso'))}
    if not shaders:
        raise ValueError('Aucun shader compile a cote de l executable.')
    relevant = sorted(p for p in assets.rglob('*') if p.is_file() and
                      (p.suffix.lower() == '.bin' or p.name in ('shrubs.txt', 'catalog.txt', 'catalogue.txt', 'manifest.txt')))
    if not relevant:
        raise ValueError('Aucun fichier binaire de modele.')
    return {'exe': sha256(exe), 'shaders': shaders,
            'assets': {p.relative_to(assets).as_posix(): sha256(p) for p in relevant}}


def engine_processes():
    if os.name != 'nt':
        return []
    cmd = "Get-CimInstance Win32_Process -Filter \"Name LIKE 'MyPlanetEngine%.exe'\" | Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress"
    p = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', cmd],
                       capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    if not p.stdout.strip():
        return []
    result = json.loads(p.stdout)
    return result if isinstance(result, list) else [result]


def stats(values):
    x = np.asarray(values, dtype=float)
    if not x.size or not np.isfinite(x).all() or (x < 0).any():
        raise ValueError('Serie GPU invalide.')
    return {'n': int(x.size), 'mediane_ms': float(np.median(x)), 'p95_ms': float(np.percentile(x, 95))}


def image_sheet(views, captures, target, label):
    images = [Image.open(captures[v['id']]).convert('RGB') for v in views]
    if len({im.size for im in images}) != 1:
        raise ValueError('Dimensions de captures incoherentes.')
    w, h = images[0].size
    board = Image.new('RGB', (2*w, ((len(images)+1)//2)*(h+28)), 'black')
    draw = ImageDraw.Draw(board)
    for i, (view, image) in enumerate(zip(views, images)):
        x, y = i%2*w, i//2*(h+28)
        board.paste(image, (x,y+28))
        draw.text((x+4,y+6), f"{label} | {view['id']} | {view['label']}", fill='white')
    board.save(target)


def paired_sheets(views, reference, captures, target):
    target.mkdir(exist_ok=True)
    for view in views:
        old=Image.open(reference[view['id']]['capture']).convert('RGB')
        new=Image.open(captures[view['id']]).convert('RGB')
        if old.size!=new.size:
            raise ValueError('Dimensions de comparaison incoherentes.')
        w,h=old.size; board=Image.new('RGB',(2*w,h+28),'black');draw=ImageDraw.Draw(board)
        board.paste(old,(0,28));board.paste(new,(w,28))
        draw.text((4,6),'reference | '+view['id'],fill='white')
        draw.text((w+4,6),'candidat | '+view['id'],fill='white')
        board.save(target/(view['id']+'.png'))


def linear_centre(path):
    rgb = np.asarray(Image.open(path).convert('RGB'), dtype=np.float32) / 255
    h, w = rgb.shape[:2]
    rgb = rgb[h//2-4:h//2+5,w//2-4:w//2+5]
    rgb = np.where(rgb <= .04045, rgb/12.92, ((rgb+.055)/1.055)**2.4)
    return float(np.median(rgb.mean(axis=2)))


def load_identities(path):
    data=path.read_bytes()
    if len(data)<16 or data[:8]!=b'FOLPLN01':
        raise ValueError('Export des plantes absent ou invalide : '+str(path))
    fine,coarse=struct.unpack_from('<II',data,8)
    if len(data)!=16+16*(fine+coarse):
        raise ValueError('Export des plantes tronque : '+str(path))
    dtype=np.dtype([('seed','<u4'),('x','<u4'),('y','<u4'),('z','<u4')])
    raw=np.frombuffer(data,dtype=dtype,offset=16)
    groups=[]
    for group in (raw[:fine],raw[fine:]):
        ordered=np.sort(group,order=('seed','x','y','z'))
        groups.append({'nombre':int(len(group)), 'sha256_tries':hashlib.sha256(ordered.tobytes()).hexdigest()})
    return {'fine':groups[0], 'grossiere':groups[1], 'fichier':str(path), 'sha256_fichier':hashlib.sha256(data).hexdigest()}


def diagnostic_identities(old_path,new_path):
    from collections import Counter
    def records(path):
        data=Path(path).read_bytes()
        if len(data)<16 or data[:8]!=b'FOLPLN01':
            raise ValueError('Export de reference invalide.')
        fine,coarse=struct.unpack_from('<II',data,8)
        if len(data)!=16+16*(fine+coarse):
            raise ValueError('Export de reference tronque.')
        return [Counter(data[16+i*16:32+i*16] for i in range(0,fine)),
                Counter(data[16+i*16:32+i*16] for i in range(fine,fine+coarse))]
    a,b=records(old_path),records(new_path);result={}
    for i,name in enumerate(('fine','grossiere')):
        missing=a[i]-b[i];extra=b[i]-a[i]
        def examples(values):
            return [{'seed':struct.unpack('<I3f',key)[0], 'position':list(struct.unpack('<I3f',key)[1:]), 'nombre':n}
                    for key,n in list(values.items())[:5]]
        result[name]={'absents':sum(missing.values()),'nouveaux':sum(extra.values()),
                      'exemples_absents':examples(missing),'exemples_nouveaux':examples(extra)}
    return result


def validate_meta(meta, candidate, samples):
    counts, overflow = meta.get('counts'), meta.get('overflow')
    if meta.get('mode') != 'hybrid-impostor' or meta.get('models') != 'game':
        raise ValueError('Mode ou modele inattendu.')
    if abs(meta.get('volume_strength', -1) - 0.65) > 1e-5:
        raise ValueError('Force volumique inattendue.')
    if not isinstance(counts,list) or len(counts)!=6 or not isinstance(overflow,list) or len(overflow)!=6:
        raise ValueError('Six files et debordements requis.')
    if len(meta.get('gpu_samples_ms', [])) != samples:
        raise ValueError('Nombre de mesures GPU inattendu.')
    if candidate:
        if meta.get('climate_shrubs') is not True:
            raise ValueError('Le catalogue climatique ne semble pas actif.')
        models, families = meta.get('model_counts'), meta.get('family_counts')
        if len(models or [])!=14 or len(families or [])!=6 or len(meta.get('representation_bytes',[]))!=28:
            raise ValueError('Les 14 modeles et les six familles sont requis.')
        if meta.get('queue_bytes') != 201326592:
            raise ValueError('La memoire des six files differe de 192 Mio.')
        for family in range(6):
            pair = [sum(models[2+2*family+j][rep] for j in (0,1)) for rep in (0,1)]
            if pair != families[family]:
                raise ValueError('Comptes de famille incoherents avec les deux formes.')
        if [sum(pair[rep] for pair in families) for rep in (0,1)] != counts[4:6]:
            raise ValueError('Comptes arbustes incoherents avec les files globales.')
        for species in (0,1):
            if models[species] != counts[species*2:species*2+2]:
                raise ValueError('Comptes arbres incoherents avec les files globales.')
    return counts, overflow


def main():
    ap = argparse.ArgumentParser(description='Banc climatique de vegetation plan\u00e9taire')
    ap.add_argument('--exe', type=Path, required=True)
    ap.add_argument('--assets', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--stage', required=True)
    ap.add_argument('--baseline', action='store_true')
    ap.add_argument('--compare', type=Path, help='rapport.json de la reference')
    ap.add_argument('--diagnostics', action='store_true', help='vues nadir biome et climat avec 1+1 images')
    ap.add_argument('--identites', action='store_true', help='exporter graines et positions source si le moteur le permet')
    ap.add_argument('--identity-compare', type=Path, help='rapport dune passe du meme exe avec export identites')
    ap.add_argument('--reprise', action='store_true', help='analyser des captures existantes sans relancer le moteur')
    ap.add_argument('--manifest', type=Path, default=MANIFEST)
    ap.add_argument('--scans', type=Path, default=SCANS)
    ap.add_argument('--warmup', type=int, default=8)
    ap.add_argument('--samples', type=int, default=24)
    ap.add_argument('--timeout', type=int, default=3600)
    a = ap.parse_args()
    if a.identity_compare and not a.identites:
        ap.error('--identity-compare exige --identites.')
    if not re.fullmatch(r'[A-Za-z0-9_-]+',a.stage):
        ap.error('Nom de stage invalide.')
    if not (1 <= a.warmup <= 10000 and 1 <= a.samples <= 10000):
        ap.error('Warmup et samples doivent etre entre 1 et 10000.')
    exe, assets, out, manifest, scans = (p.resolve() for p in (a.exe,a.assets,a.out,a.manifest,a.scans))
    if not exe.is_file() or not assets.is_dir() or not scans.is_dir():
        ap.error('Exe, assets ou scans introuvables.')
    if any(c.isspace() for c in str(out)):
        ap.error('Le chemin de sortie ne peut pas contenir d espaces.')
    data=json.loads(manifest.read_text(encoding='utf8')); views=data['vues']
    if not views or len({v['id'] for v in views})!=len(views):
        ap.error('Manifeste vide ou identifiants dupliques.')
    for v in views:
        if not re.fullmatch(r'[A-Za-z0-9_-]+',v['id']) or len(v['camera'])!=5 or len(v['soleil'])!=2:
            ap.error('Vue invalide : '+str(v))
        if any(not isinstance(x,(int,float)) or not math.isfinite(x) for x in v['camera']+v['soleil']):
            ap.error('Coordonnees invalides.')
    dest=out/a.stage
    if a.reprise:
        if not dest.is_dir():
            raise FileNotFoundError(dest)
    else:
        dest.mkdir(parents=True,exist_ok=False)
    captures=dest/'captures'; logs=dest/'logs'
    if not a.reprise:
        captures.mkdir(); logs.mkdir()
    paths={v['id']:captures/(v['id']+'.bmp') for v in views}
    hashes=snapshot_hashes(exe,assets)
    prov={'stage':a.stage,'baseline':a.baseline,'exe':str(exe),'assets':str(assets),'scans':str(scans),
          'hashes':hashes,'manifest_sha256':sha256(manifest),'banc_sha256':sha256(Path(__file__).resolve()),
          'warmup':a.warmup,'samples':a.samples,'identites':a.identites,'volume':0.65,'mode':'hybrid-impostor','models':'game',
          'contexte_gpu':'Autres applications possibles ; vol interactif non interrompu. Temps indicatifs, sans garantie de budget.',
          'processus_initial':engine_processes() if not a.reprise else [],'processus_par_batch':{},'vues':views}
    if a.reprise:
        saved=json.loads((dest/'provenance.json').read_text(encoding='utf8'))
        for key in ('stage','baseline','exe','assets','hashes','manifest_sha256','warmup','samples','identites'):
            if saved.get(key,False if key=='identites' else None)!=prov.get(key):
                raise ValueError('Reprise impossible, provenance differente : '+key)
        prov=saved
    def save_prov():
        (dest/'provenance.json').write_text(json.dumps(prov,indent=2,ensure_ascii=False),encoding='utf8')
    def run_batch(name,jobs,warmup,samples):
        jobfile=logs/(name+'.txt')
        jobfile.write_text(''.join(' '.join(str(x) for x in job)+'\n' for job in jobs),encoding='utf8')
        env={k:v for k,v in os.environ.items() if not k.upper().startswith('MYPLANETENGINE_')}
        # Le feuillage du jeu est le defaut du moteur, HiZ et profondeur materielle compris ; seul son catalogue se choisit.
        env.update(MYPLANETENGINE_BATCH=str(jobfile),
                   MYPLANETENGINE_FOLIAGE_ASSETS=str(assets),MYPLANETENGINE_SCANS=str(scans),
                   MYPLANETENGINE_FOLIAGE_WARMUP=str(warmup),MYPLANETENGINE_FOLIAGE_SAMPLES=str(samples),MYPLANETENGINE_TIME='0 0',
                   MYPLANETENGINE_TAA='1',MYPLANETENGINE_GLARE='1')
        if a.identites and name=='couleur':
            env['MYPLANETENGINE_OBJECT_LIST']='1'
        prov['processus_par_batch'][name]=engine_processes();save_prov()
        print(f'{a.stage} : {name}, {len(jobs)} vues',flush=True)
        with (logs/(name+'.log')).open('w',encoding='utf8') as log:
            p=subprocess.run([str(exe)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=a.timeout,
                             creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        if p.returncode:
            raise RuntimeError(f'Erreur moteur {p.returncode} ; journal {log.name}')
    if not a.reprise:
        save_prov()
    start=time.monotonic()
    jobs=[(paths[v['id']],'-',*v['camera'],2.0,*v['soleil']) for v in views]
    if not a.reprise:
        run_batch('couleur',jobs,a.warmup,a.samples)
    diagnostics={}
    if a.diagnostics:
        diagdir=dest/'climat'
        if not a.reprise:
            diagdir.mkdir()
        jobs=[]
        for v in views:
            h,lat,lon,pitch,heading=v['camera']
            for kind in ('biome','temperature','humidity','season'):
                path=diagdir/(v['id']+'_'+kind+'.bmp')
                jobs.append((path,kind,200,lat,lon,89.9,heading,2.0,*v['soleil']))
        if not a.reprise:
            run_batch('climat',jobs,1,1)
        for v in views:
            vals={kind:linear_centre(diagdir/(v['id']+'_'+kind+'.bmp')) for kind in ('biome','temperature','humidity','season')}
            diagnostics[v['id']]={'biome_classe':min(max(round(vals['biome']*8),0),7),
                                  'temperature_c':vals['temperature']*70-30,'humidite':vals['humidity'],
                                  'saison_c':vals['season']*70-30,'methode':'mediane centrale 9x9, vue nadir a 200 m'}
    if snapshot_hashes(exe,assets)!=hashes:
        raise RuntimeError('Exe, shaders ou assets modifies pendant la passe.')
    prior={}
    if a.compare:
        previous=json.loads(a.compare.read_text(encoding='utf8'))
        prior={v['id']:v for v in previous['vues']}
        if set(prior)!=set(paths):
            raise ValueError('Les vues de reference ne correspondent pas.')
        for view in views:
            if prior[view['id']]['camera'] != view['camera'] or prior[view['id']]['soleil'] != view['soleil']:
                raise ValueError('Camera ou soleil differents de la reference.')
    identity_prior={}
    if a.identity_compare:
        previous=json.loads(a.identity_compare.read_text(encoding='utf8'))
        if previous.get('identites_exe_sha256') != hashes['exe']:
            raise ValueError('Comparaison identite invalide : executables differents.')
        identity_prior={v['id']:v for v in previous['vues']}
        if set(identity_prior)!=set(paths):
            raise ValueError('Les vues du rapport identite ne correspondent pas.')
        for view in views:
            ref=identity_prior[view['id']]
            if ref['camera']!=view['camera'] or ref['soleil']!=view['soleil'] or not ref.get('source_instances'):
                raise ValueError('La reference identite doit avoir les memes vues et leurs exports.')
    report={'stage':a.stage,'baseline':a.baseline,'secondes':None if a.reprise else round(time.monotonic()-start,2),
            'reprise_sans_gpu':a.reprise, 'identites_exe_sha256':hashes['exe'] if a.identites else None,
            'diagnostics_contextuels':diagnostics,'vues':[],
            'identites_positions':'exportees ; comparaison possible seulement au meme exe' if a.identites else 'non disponibles : les comptes seuls ne prouvent pas leur conservation',
            'gpu':'Serie de frames consecutives, GPU potentiellement partage ; temps indicatifs.',
            'population_comparee':bool(prior)}
    aggregate=[[],[],[]]
    for v in views:
        p=paths[v['id']]; side=Path(str(p)+'.planet-foliage.json')
        if not p.exists() or not side.exists():
            raise FileNotFoundError(p)
        meta=json.loads(side.read_text(encoding='utf-8-sig'))
        counts,overflow=validate_meta(meta,not a.baseline,a.samples)
        series=meta['gpu_samples_ms']; timings={}
        for k,name in enumerate(('placement','draw','total_frame')):
            x=[row[k] for row in series];aggregate[k].extend(x);timings[name]=stats(x)
        if 'source_placement_samples_ms' in meta:
            timings['source_placement']=stats(meta['source_placement_samples_ms'])
        if meta.get('hiz_gpu_samples_ms'):
            timings['hiz_build']=stats([x[0] for x in meta['hiz_gpu_samples_ms']])
            timings['hiz_cull']=stats([x[1] for x in meta['hiz_gpu_samples_ms']])
        measured=meta.get('queue_bytes'); queue=measured if measured is not None else meta['capacity_per_queue']*6*64
        if queue!=201326592:
            raise ValueError('La memoire des six files differe de 192 Mio.')
        item={'id':v['id'],'label':v['label'],'camera':v['camera'],'soleil':v['soleil'],
              'famille_candidate':v.get('famille_candidate'),'climat_nadir':diagnostics.get(v['id']),
              'capture':str(p),'sha256':sha256(p),'counts':counts,'overflow':overflow,
              'model_counts':meta.get('model_counts'),'family_counts':meta.get('family_counts'),
              'active_commands':meta.get('active_commands'),
              'hiz':{k:meta.get(k) for k in ('hiz_enabled','hiz_tested','hiz_rejected_candidates','hiz_rejected','hiz_drawn','hiz_occluders')},
              'representation_bytes':meta.get('representation_bytes'),'queue_bytes':queue,
              'queue_bytes_origine':'sidecar' if measured is not None else 'deduit de la capacite', 'gpu_ms':timings}
        if meta.get('family_counts'):
            family_totals=[sum(pair) for pair in meta['family_counts']]
            family_sum=sum(family_totals)
            item['familles_part']={name:(family_totals[i]/family_sum if family_sum else None) for i,name in enumerate(FAMILIES)}
            item['famille_dominante']=FAMILIES[family_totals.index(max(family_totals))] if family_sum else None
        if a.identites:
            item['source_instances']=load_identities(Path(str(p)+'.plantes'))
            if identity_prior:
                other=identity_prior[v['id']]['source_instances']
                item['identites_identiques']=all(item['source_instances'][group]['sha256_tries']==other[group]['sha256_tries']
                                                and item['source_instances'][group]['nombre']==other[group]['nombre']
                                                for group in ('fine','grossiere'))
                if not item['identites_identiques']:
                    item['identites_ecarts']=diagnostic_identities(other['fichier'],item['source_instances']['fichier'])
        if prior:
            old=prior[v['id']]['counts']
            item['difference_population']=[sum(counts[2*s:2*s+2])-sum(old[2*s:2*s+2]) for s in range(3)]
            item['counts_reference']=old
        report['vues'].append(item)
    report['totaux_gpu']={name:stats(aggregate[i]) for i,name in enumerate(('placement','draw','total_frame'))}
    report['overflow']=[v['id'] for v in report['vues'] if any(v['overflow'])]
    report['populations_differentes']=[v['id'] for v in report['vues'] if prior and any(v['difference_population'])]
    report['identites_differentes']=[v['id'] for v in report['vues'] if identity_prior and not v['identites_identiques']]
    (dest/'rapport.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    image_sheet(views,paths,dest/'planche.png',a.stage)
    if prior:
        paired_sheets(views,prior,paths,dest/'comparaisons')
    print(json.dumps({'stage':a.stage,'secondes':report['secondes'],'overflow':report['overflow'],
                      'populations_differentes':report['populations_differentes'],'rapport':str(dest/'rapport.json')},ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()
