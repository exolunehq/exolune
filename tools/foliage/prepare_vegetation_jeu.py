"""Cook substantial game vegetation, rooted forms and fern undergrowth from credited source models.

No Blender or interactive app is launched. Models, root geometry and their proxies share one asset recipe.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import shutil
import urllib.request
import zipfile
import tarfile
import numpy as np
from importe import ROOT
import prepare_biomes as source
import bake
import volume_assets
import formes_jeu

NAMES=source.OLD+source.NEW+['fern_b','fern_c']


def download(cache):
    manifest=json.loads(Path(__file__).with_name('sources_vegetation_jeu.json').read_text())
    for record in manifest['files']:
        path=cache/record['cache'];path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            request=urllib.request.Request(record['url'],headers={'User-Agent':'Exolune/1.0 (game vegetation build)'})
            path.write_bytes(urllib.request.urlopen(request,timeout=120).read())
        if hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('Changed source: '+record['cache'])
    if not (cache/'tree10').exists():
        with zipfile.ZipFile(cache/'tree10.zip') as archive:
            with archive.open('uploadtool_Tree10.unitypackage') as src,(cache/'tree10.unitypackage').open('wb') as dst:shutil.copyfileobj(src,dst)
        with tarfile.open(cache/'tree10.unitypackage') as archive:archive.extractall(cache/'tree10',filter='data')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=ROOT/'x64/VegetationDiversity/sources')
    parser.add_argument('--base',type=Path,default=ROOT.parent/'plantes/climate_shrubs_v2')
    parser.add_argument('--out',type=Path,default=ROOT/'assets/foliage/game_biomes_v1')
    args=parser.parse_args();download(args.cache);args.out.mkdir(parents=True,exist_ok=True)
    if not (args.base/'shrubs.txt').exists():raise ValueError('Missing base catalogue; build it through tools/plantes.ps1')
    (args.out/'biomes.txt').unlink(missing_ok=True)
    leaves={name:1 if name=='game_broadleaf' else 2 for name in source.OLD}
    for name in source.OLD+['fir_open','fir_dense']:
        original='game_fir' if name in ['fir_open','fir_dense'] else name
        folder=args.out/name;folder.mkdir(exist_ok=True)
        for file in ['mesh.bin','material.bin']:shutil.copy2(args.base/original/file,folder/file)
        if name in ['fir_open','fir_dense']:leaves[name]=2
    leaves.update(source.broadleaves(args.cache,args.out))
    for asset,node,name in [('shrub_03','shrub_03_a','edge_shrub_a'),('shrub_03','shrub_03_c','edge_shrub_c'),
            ('searsia_lucida','searsia_lucida_g_LOD0','leafy_shrub'),('shrub_sorrel_01','shrub_sorrel_01_a','sorrel_a'),
            ('shrub_sorrel_01','shrub_sorrel_01_c','sorrel_c'),('grass_medium_01','grass_medium_01_tall_a_LOD0','grass_tall_a'),
            ('grass_medium_01','grass_medium_01_tall_c_LOD0','grass_tall_c'),('flower_empodium','flower_empodium_a_LOD0','flower_a'),
            ('flower_empodium','flower_empodium_d_LOD0','flower_d'),('fern_02','fern_02_b','fern_b'),('fern_02','fern_02_c','fern_c')]:
        leaves[name]=source.polyhaven(args.cache,args.out,asset,node,name)
    bake.OUT=args.out;volume_assets.DEST=args.out
    records=['FOLBIO02 31'];report={}
    recipe=Path(formes_jeu.__file__).read_bytes()+Path(bake.__file__).read_bytes()+Path(volume_assets.__file__).read_bytes()
    for index,name in enumerate(NAMES):
        folder=args.out/name;kind=0 if index in [0,14,15] else 1 if index==1 or 16<=index<=19 else 2
        if index<29:formes_jeu.style(folder,index,leaves[name],kind<2)
        fingerprint=hashlib.sha256((folder/'mesh.bin').read_bytes()+(folder/'material.bin').read_bytes()+recipe).hexdigest()
        stamp=folder/'cooked.sha256'
        if not (folder/'impostor_light.bin').exists() or not stamp.exists() or stamp.read_text()!=fingerprint:
            v,tri,atlas,lo,hi,materials=bake.load(name)
            bake.volume(name,v,tri,atlas,lo,hi,materials,64)
            bake.impostor(name,v,tri,atlas,lo,hi,materials)
            volume_assets.SPEC[name]={'leaf':int(math.log2(leaves[name]&-leaves[name]))}
            volume_assets.bake_light(name);stamp.write_text(fingerprint)
        records.append(f'{name} {kind} {leaves[name]}')
        v,tri,_,_,_,_=bake.load(name)
        report[name]={'triangles':len(tri)//3,'vertices':len(v),'root_vertices':int(np.count_nonzero(np.mod(v[:,8],1)>.125))}
    (args.out/'recipe.json').write_text(json.dumps(report,indent=2)+'\n')
    # Contact sheet accepts the two extra undergrowth forms while retaining the same view and lighting recipe.
    old=source.OLD;new=source.NEW
    source.NEW=new+['fern_b','fern_c']
    # The original sheet is six rows; create a separate board for all 31 models.
    from PIL import Image,ImageDraw
    import struct
    board=Image.new('RGB',(5*224,7*248),(28,34,37));draw=ImageDraw.Draw(board)
    for i,name in enumerate(NAMES):
        with (args.out/name/'impostor.bin').open('rb') as f:
            _,az,el,w,h,*_=struct.unpack('<8s4I7f',f.read(52));f.seek(52+az*w*h*4)
            image=Image.frombytes('RGBA',(w,h),f.read(w*h*4)).resize((216,216))
        x=i%5*224;y=i//5*248;board.paste(image,(x+4,y+4),image);draw.text((x+5,y+225),f'{i}: {name}',fill='white')
    board.save(args.out/'catalogue.png');source.OLD=old;source.NEW=new
    (args.out/'biomes.txt').write_text('\n'.join(records)+'\n',encoding='ascii')
    print('Game vegetation ready:',args.out,'31 models; rooted trunks and fern undergrowth.',flush=True)


if __name__=='__main__':main()
