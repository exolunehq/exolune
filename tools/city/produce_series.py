"""Reproducible neutral architecture batch; no cooking or runtime promotion."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import shutil
import subprocess

HERE=Path(__file__).resolve().parent
BLENDER=Path('C:/Program Files/Blender Foundation/Blender 5.2/blender.exe')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(script,arguments,log):
    command=[str(BLENDER),'--background','--factory-startup','--threads','6','--python-exit-code','1','--python',str(HERE/script),'--']+list(map(str,arguments))
    with log.open('w',encoding='utf-8') as output:
        result=subprocess.run(command,stdout=output,stderr=subprocess.STDOUT,creationflags=0x08000000)
    if result.returncode:raise RuntimeError(f'{script} failed; inspect {log}')


def source_valid(folder,recipe,check_live=False):
    report=json.loads((folder/'source.json').read_text())
    if report['master_sha256']!=sha(folder/'master.glb'):raise ValueError('Source GLB changed: '+str(folder))
    if report['recipe_sha256']!=sha(recipe):raise ValueError('Recipe changed; use a new output directory')
    for name,digest in report['tool_hashes'].items():
        if sha(folder/'authoring'/name)!=digest:raise ValueError('Author snapshot changed: '+name)
        if check_live and sha(HERE/name)!=digest:raise ValueError('Author changed; use a new output directory: '+name)
    return report


def report_batch(out,recipe,assets):
    records=[];cards=[]
    for asset in assets:
        id=asset['id'];folder=out/'models'/id;review=out/'reviews'/id;source=source_valid(folder,recipe)
        validation=json.loads((review/'reimport-validation.json').read_text());settings=json.loads((review/'render-settings.json').read_text())
        if not validation['passed'] or validation['master_sha256']!=source['master_sha256'] or settings['source_sha256']!=source['master_sha256']:raise ValueError('Stale or invalid review: '+id)
        views={name:{'path':str(review/(name+'.png')),'sha256':sha(review/(name+'.png'))} for name in ['hero','back','entry']}
        size=[round(b-a,2) for a,b in zip(*source['bounds'])]
        records.append({'id':id,'label':asset['label'],'family':asset['family'],'triangles':source['triangles'],'objects':source['objects'],
                        'dimensions_m':size,'master':str(folder/'master.glb'),'master_sha256':source['master_sha256'],'reimport_passed':True,'views':views})
        cards.append(f'''<article><h2>{html.escape(asset['label'])}</h2><a href="reviews/{id}/hero.png"><img src="reviews/{id}/hero.png" alt="Rendu 3D neutre de {html.escape(asset['label'])}"></a>
<p>{source['triangles']:,} triangles · {size[0]} × {size[1]} × {size[2]} m · source non réduite</p>
<nav><a href="reviews/{id}/back.png">Arrière</a><a href="reviews/{id}/entry.png">Entrée</a><a href="models/{id}/master.glb">Modèle GLB</a><a href="models/{id}/master.blend">Source Blender</a></nav></article>''')
    report={'stage':'Neutral source study; explicitly requested series','recipe_sha256':sha(recipe),'assets':records,
            'families':{family:sum(a['family']==family for a in assets) for family in sorted({a['family'] for a in assets})},
            'art_accepted':False,'performance_accepted':False,'runtime_replaced':False,'cooked':False,'texture_count':0}
    (out/'series.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    page='''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Série de bâtiments — études neutres</title>
<style>body{background:#171b1b;color:#e8eeeb;font:16px system-ui;margin:36px auto;max-width:1420px;padding:0 24px}h1{font-weight:550}header{max-width:1000px;margin-bottom:32px}p{color:#b9c5c1;line-height:1.6}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:24px}article{background:#232b29;border-radius:12px;padding:20px}h2{font-size:20px;font-weight:550}img{width:100%;height:auto}a{color:#acdcd0}nav{display:flex;gap:20px;flex-wrap:wrap}</style>
<header><h1>Maisons et bâtiments publics</h1><p>Huit modèles 3D issus de trois familles de construction. La maison de référence sert de témoin aux trois nouvelles variantes. Les maisons communes et les serres utilisent leurs propres surfaces paramétriques.</p>
<p>Rendus neutres des GLB réimportés, calculés sur CPU. Sources de forme : textures, LOD et validation dans Exolune restent à réaliser. Les faces arrière sont des interprétations de conception.</p></header><main class="grid">'''+''.join(cards)+'</main></html>'
    (out/'index.html').write_text(page,encoding='utf-8');print('SERIES_REPORT',out/'series.json',flush=True)
    for name,title,families in [('houses','Maisons — quatre proportions',{'house'}),('public','Bâtiments publics — deux familles',{'civic','greenhouse'})]:
        selected=[card for card,asset in zip(cards,assets) if asset['family'] in families]
        board='''<!doctype html><html lang="fr"><meta charset="utf-8"><title>Études de formes</title><style>
*{box-sizing:border-box}body{margin:0;padding:30px 34px;background:#172220;color:#edf3ef;font:17px system-ui;width:1440px}header{height:116px}h1{font-weight:550;font-size:32px;margin:0 0 12px}header p{color:#b8ccc4;margin:0;font-size:18px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}article{padding:14px 18px;background:#27302d;border-radius:8px}h2{font-size:21px;font-weight:550;margin:0 0 10px}img{width:100%;display:block}article p{margin:10px 0 0;color:#c4d4cd;font-size:15px}nav{display:none}a{color:inherit}footer{color:#adc3b9;padding-top:18px;font-size:16px}</style><header><h1>'''+html.escape(title)+'''</h1><p>Rendus neutres de véritables modèles 3D · Étude des volumes et des jonctions</p></header><main class="grid">'''+''.join(selected)+'''</main><footer>Sources non réduites. Textures, LOD et validation in-game restent à réaliser. Les cadrages sont ajustés à chaque modèle.</footer></html>'''
        (out/(name+'-board.html')).write_text(board,encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recipe',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--stages',default='author,review,report');p.add_argument('--resume',action='store_true');p.add_argument('--only',default='')
    args=p.parse_args();args.out=args.out.resolve();args.out.mkdir(parents=True,exist_ok=True);args.recipe=args.recipe.resolve()
    recipe=json.loads(args.recipe.read_text(encoding='utf-8'));assets=[a for a in recipe['assets'] if not args.only or a['id'] in args.only.split(',')]
    if not assets:raise ValueError('Empty series')
    inputs=args.out/'source-inputs';inputs.mkdir(exist_ok=True)
    for family,reference in recipe['references'].items():
        if sha(reference['path'])!=reference['sha256']:raise ValueError('Original board changed: '+family)
        shutil.copy2(reference['path'],inputs/(family+'-original.png'))
    if sha(recipe['house_source']['path'])!=recipe['house_source']['sha256']:raise ValueError('House control changed')
    shutil.copy2(recipe['house_source']['path'],inputs/'house-control.glb')
    shutil.copy2(__file__,args.out/'produce-series.py')
    logs=args.out/'logs';logs.mkdir(exist_ok=True);stages=args.stages.split(',')
    if any(s not in ['author','review','report'] for s in stages):raise ValueError('Unknown stage')
    for asset in assets:
        id=asset['id'];folder=args.out/'models'/id;review=args.out/'reviews'/id
        if 'author' in stages:
            if (folder/'source.json').exists():
                if not args.resume:raise ValueError('Source exists; choose a new directory or --resume')
                source_valid(folder,args.recipe,check_live=True)
            else:run('author_series.py',['--recipe',args.recipe,'--asset',id,'--out',folder],logs/(id+'-author.log'))
            print('AUTHORED',id,flush=True)
        if 'review' in stages:
            source=source_valid(folder,args.recipe)
            run('review_series.py',['--asset-dir',folder,'--out',review],logs/(id+'-review.log'))
            print('REVIEWED',id,source['triangles'],'triangles',flush=True)
    shutil.copy2(args.recipe,args.out/'recipe.json')
    if 'report' in stages:report_batch(args.out,args.recipe,assets)


if __name__=='__main__':main()
