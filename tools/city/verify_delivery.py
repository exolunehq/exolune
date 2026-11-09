"""Verify that delivery and both native review routes describe the same files."""
from pathlib import Path
import argparse
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--houses',action='store_true',help='Verify the paired house/variant route instead of the whole-city routes')
    p.add_argument('--series',action='store_true',help='Verify all eight neutral-series models in the full city bank')
    p.add_argument('--review-dir',default='native-review',help='Whole-city/series capture directory inside the delivery')
    a=p.parse_args();bank=a.out/'bank';prod=json.loads((bank/'production.json').read_text())
    lib=json.loads((bank/'library.json').read_text());layout=json.loads((bank/'layout.json').read_text())
    assert prod['library_sha256']==sha(bank/'library.bin')
    assert prod['scene_sha256']==sha(bank/'scene.bin')
    reviews=[]
    labels=[['Vue ensemble de la ville','Approche et LOD','Coeur dense - habitats collectifs','Habitat en terrasses',
        'Maison generee ComfyUI','Maison commune','Serres et cultures','Hangar exterieur','Station entrelacee',
        'Rame et viaduc suspendu','Jardin partage et mobilier','Connexions des chemins'],
        ['Entree collective','Maison ComfyUI - temoin source','Entree maison commune','Entree serre','Acces station',
         'Variante helicoidale','Variante lanterne','Terrasses jardin','Banc et assemblages','Fontaine',
         'Armoire technique','Suspension de la rame']]
    directories=[a.review_dir,'native-details'];palettes=['2026-11-07-ville-archipel','2026-11-07-ville-details']
    if a.houses:
        directories=['native-houses'];palettes=['2026-11-08-maison-variantes']
        labels=[[prefix+' - '+view for prefix in ['Maison coques','Variante patio']
                 for view in ['ensemble','depuis le chemin','facade arriere','distance et LOD','entree et seuil','intrados et raccords']]]
    if a.series:
        directories=[a.review_dir];palettes=['2026-11-08-ville-serie']
        labels=[['Maison source','Maison basse','Maison allongee','Maison haute',
                 'Forum commun','Maison des jardins','Serre large','Serre longue',
                 'Entree maison','Entree forum','Ville complete','Approche et distance']]
    for directory,palette,titles in zip(directories,palettes,labels):
        review=json.loads((a.out/directory/'functional.json').read_text());protocol=review['protocol']
        assert protocol['library']==prod['library_sha256'] and protocol['scene']==prod['scene_sha256'],directory
        assert protocol['executable']==sha(ROOT/'x64/Release/MyPlanetEngine.exe'),directory
        assert len(review['captures'])==12,directory
        for name,digest in protocol['shaders'].items():assert sha(ROOT/'x64/Release'/name)==digest,name
        for name,digest in protocol['textures'].items():assert sha(bank/name)==digest,name
        for capture in review['captures']:assert sha(a.out/directory/(capture['name']+'.bmp'))==capture['sha256']
        route=(a.out/directory/'route.txt').read_text().splitlines();assert len(route)==len(titles)
        (ROOT/'tools/tests'/(palette+'.txt')).write_text(
            '\n'.join(title+' | '+line.split(' | ',1)[1] for title,line in zip(titles,route))+'\n',encoding='ascii')
        reviews.append({'route':directory,'views':len(review['captures']),'protocol':protocol})
    if a.houses and (a.out/'native-regression/functional.json').exists():
        review=json.loads((a.out/'native-regression/functional.json').read_text());protocol=review['protocol']
        assert protocol['library']==prod['library_sha256'] and protocol['scene']==prod['scene_sha256']
        assert protocol['executable']==sha(ROOT/'x64/Release/MyPlanetEngine.exe')
        assert {c['name'] for c in review['captures']}=={'collective_entry','train_fittings'}
        for name,digest in protocol['shaders'].items():assert sha(ROOT/'x64/Release'/name)==digest,name
        for name,digest in protocol['textures'].items():assert sha(bank/name)==digest,name
        for capture in review['captures']:assert sha(a.out/'native-regression'/(capture['name']+'.bmp'))==capture['sha256']
        reviews.append({'route':'native-regression','views':len(review['captures']),'protocol':protocol})
    if a.houses and (a.out/'native-lods/functional.json').exists():
        review=json.loads((a.out/'native-lods/functional.json').read_text());protocol=review['protocol']
        assert protocol['library']==prod['library_sha256'] and protocol['scene']==prod['scene_sha256']
        assert protocol['executable']==sha(ROOT/'x64/Release/MyPlanetEngine.exe')
        assert {c['name'] for c in review['captures']}=={prefix+'_lod'+str(level) for prefix in ['house','variant'] for level in [1,2,3]}
        for name,digest in protocol['shaders'].items():assert sha(ROOT/'x64/Release'/name)==digest,name
        for name,digest in protocol['textures'].items():assert sha(bank/name)==digest,name
        for capture in review['captures']:assert sha(a.out/'native-lods'/(capture['name']+'.bmp'))==capture['sha256']
        reviews.append({'route':'native-lods','views':len(review['captures']),'protocol':protocol})
    for name,digest in prod['tools'].items():assert sha(ROOT/'tools/city'/name)==digest,name
    for source in prod['sources']:
        assert sha(source['path'])==source['sha256'],source['id']
        assert sha(Path(source['path']).parent/'source.json')==source['metadata_sha256'],source['id']
    assert prod['functional_cpu']['passed'] and len(prod['functional_cpu']['geometry_budgets'])==len(lib['models'])
    topology=json.loads((bank/'manufacturing-validation.json').read_text());assert topology['accepted']
    source_hashes={item['id']:item['sha256'] for item in prod['sources']}
    for item in topology['models']:assert source_hashes[item['id']]==item['sha256'],item['id']
    assert lib['geometric_seam_weld_m']==1e-6 and lib['closed_part_boundary_guard']
    assert layout['composition_sha256']==sha(ROOT/'tools/city/settlement.py')
    assert layout['masterplan_sha256']==sha(ROOT/'tools/city/masterplan.py')
    report={'exact_reviewed_bank':True,'models':len(lib['models']),'instances':len(layout['instances']),
        'buildings':len(layout['parcels']),'native_views':sum(r['views'] for r in reviews),
        'connected_parts':sum(len(item['parts']) for item in topology['models']),
        'stored_geometry_MiB':lib['geometry_bytes']/2**20,'triangles_all_stored_lods':lib['triangles_all_levels'],
        'manufactured_ground_triangles':layout['street_triangles'],'art_accepted':False,'performance_accepted':False,
        'reviews':reviews}
    (a.out/'delivery-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='reviews'},indent=2))


if __name__=='__main__':main()
