"""Build the diverse, resident game catalogue from pinned artist sources.

Python/numpy/Pillow/numba/UnityPy and Blender CLI are development dependencies only.
Existing climate_shrubs_v2 remains unchanged. No benchmark or interactive window is launched.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import shutil
import struct
import subprocess
import tarfile
import urllib.parse
import urllib.request
import zipfile
import numpy as np
from PIL import Image, ImageDraw
from importe import ROOT, accessor
import bake
import volume_assets

OLD = ['game_fir','game_broadleaf'] + [f'shrub_{family}_{v}' for family in
        ['boreal','desert','steppe','montane','temperate','tropical'] for v in range(2)]
NEW = ['fir_open','fir_dense'] + [f'broadleaf_{i}' for i in range(2,6)] + [
       'edge_shrub_a','edge_shrub_c','leafy_shrub','sorrel_a','sorrel_c','grass_tall_a','grass_tall_c','flower_a','flower_d']


def download(cache):
    manifest=json.loads(Path(__file__).with_name('sources_biomes.json').read_text(encoding='utf-8'))
    for entry in manifest['files']:
        path=cache/entry['cache']; path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            request=urllib.request.Request(entry['url'],headers={'User-Agent':'Exolune/1.0 (vegetation asset build)'})
            path.write_bytes(urllib.request.urlopen(request,timeout=120).read())
        if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
            raise ValueError('Source checksum mismatch: '+entry['cache'])
    if not (cache/'tree10').exists():
        with zipfile.ZipFile(cache/'tree10.zip') as archive:
            with archive.open('uploadtool_Tree10.unitypackage') as src, (cache/'tree10.unitypackage').open('wb') as dst:
                shutil.copyfileobj(src,dst)
        with tarfile.open(cache/'tree10.unitypackage') as archive:
            archive.extractall(cache/'tree10',filter='data')


def mask(image, leaf):
    arm=np.asarray(image.convert('RGB'))
    return Image.fromarray(np.stack([arm[:,:,0],arm[:,:,1],np.full(arm.shape[:2],255 if leaf else 0,'u1'),
                                    np.full(arm.shape[:2],255,'u1')],axis=-1))


def write_model(out,name,parts,colors,normals,masks,tile=1024,origin=None):
    count=len(colors); atlases=[]
    for images in [colors,normals,masks]:
        atlas=Image.new('RGBA',(tile*count,tile))
        for i,image in enumerate(images): atlas.paste(image.resize((tile,tile),Image.Resampling.LANCZOS),(i*tile,0))
        atlases.append(atlas)
    positions=np.concatenate([p[0] for p in parts]); lo=positions.min(0); hi=positions.max(0)
    height=hi[1]-lo[1]
    if height<=0: raise ValueError('Invalid source bounds: '+name)
    offset=np.array([(lo[0]+hi[0])/2,lo[1],(lo[2]+hi[2])/2]) if origin is None else np.asarray(origin,dtype=float)
    verts=[];indices=[];first=0
    for position,normal,uv,triangles,material in parts:
        v=np.empty((len(position),9),'<f4'); v[:,:3]=(position-offset)/height
        v[:,3:6]=normal/np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-20)
        v[:,6:8]=uv;v[:,8]=material;verts.append(v);indices.append(np.asarray(triangles,dtype='<u4').reshape(-1)+first);first+=len(v)
    lo=(lo-offset)/height;hi=(hi-offset)/height; folder=out/name;folder.mkdir(parents=True,exist_ok=True)
    with (folder/'mesh.bin').open('wb') as f:
        f.write(struct.pack('<8s5I6f',b'FOLMESH1',first,sum(map(len,indices)),tile*count,tile,count,*lo,*hi))
        for v in verts:f.write(v.tobytes())
        for tri in indices:f.write(tri.tobytes())
        f.write(atlases[0].tobytes())
    with (folder/'material.bin').open('wb') as f:
        f.write(struct.pack('<8s2I',b'FOLMAT01',tile*count,tile));f.write(atlases[1].tobytes());f.write(atlases[2].tobytes())
    print(name,sum(map(len,indices))//3,'triangles',flush=True)


def polyhaven(cache,out,asset,node,name,reduced=None):
    folder=cache/asset; doc=json.loads((folder/(asset+'.gltf')).read_text()); blob=(folder/doc['buffers'][0]['uri']).read_bytes()
    colors=[];normals=[];masks=[];leaf_mask=0
    def texture(info,fallback):
        if not info:return fallback.copy()
        uri=doc['images'][doc['textures'][info['index']]['source']]['uri']
        return Image.open(folder/urllib.parse.unquote(uri)).convert('RGBA')
    for i,material in enumerate(doc['materials']):
        title=material.get('name','')
        leaf=asset not in ['fir_sapling','searsia_lucida'] or 'leaves' in title or (asset=='fir_sapling' and 'twig' in title)
        if leaf:leaf_mask|=1<<i
        color=texture(material.get('pbrMetallicRoughness',{}).get('baseColorTexture'),Image.new('RGBA',(16,16),'white'))
        # Opacity and leaf transmission are independent. The fir's modeled needles are opaque geometry.
        if material.get('alphaMode','OPAQUE')!='OPAQUE':
            alpha=list((folder/'textures').glob('*alpha*'))
            if alpha:color.putalpha(Image.open(alpha[0]).convert('L').resize(color.size))
        colors.append(color)
        normals.append(texture(material.get('normalTexture'),Image.new('RGBA',color.size,(128,128,255,255))))
        arm=texture(material.get('pbrMetallicRoughness',{}).get('metallicRoughnessTexture'),Image.new('RGBA',color.size,(255,190,0,255)))
        masks.append(mask(arm,leaf))
    if reduced:
        v=np.load(reduced)['vertices']; parts=[]
        for material in range(len(colors)):
            ids=np.flatnonzero(v[::3,8]==material)
            if len(ids):
                indices=(ids[:,None]*3+np.arange(3)).reshape(-1)
                parts.append((v[:,:3],v[:,3:6],v[:,6:8],indices,material))
    else:
        selected=next(n for n in doc['nodes'] if n.get('name')==node)
        if any(k in selected for k in ['matrix','rotation','scale','children']):raise ValueError('Unexpected source transform: '+node)
        translation=np.asarray(selected.get('translation',[0,0,0]));parts=[]
        for primitive in doc['meshes'][selected['mesh']]['primitives']:
            a=primitive['attributes'];parts.append((accessor(doc,blob,a['POSITION'])+translation,accessor(doc,blob,a['NORMAL']),
                accessor(doc,blob,a['TEXCOORD_0']),accessor(doc,blob,primitive['indices']),primitive['material']))
    write_model(out,name,parts,colors,normals,masks,tile=512 if name.startswith(('grass','flower','sorrel')) else 1024)
    return leaf_mask


def broadleaves(cache,out):
    import UnityPy
    from UnityPy.helpers.MeshHelper import MeshHandler
    files={p.read_text().strip():p.parent/'asset' for p in (cache/'tree10').glob('*/pathname')}
    result={}
    for i in range(2,6):
        def file(name):return files['Assets/Tree10/'+name]
        root=f'Tree10_{i}';env=UnityPy.load(str(file(root+'.prefab')))
        h=MeshHandler(next(o.read() for o in env.objects if o.type.name=='Mesh'));h.process()
        position=np.asarray(h.m_Vertices);normal=np.asarray(h.m_Normals);uv=np.asarray(h.m_UV0).copy();uv[:,1]=1-uv[:,1]
        parts=[(position,normal,uv,np.asarray(h.get_triangles()[j]),1-j) for j in range(2)]
        color=Image.open(file(root+'_Textures/diffuse.png')).convert('RGBA');leaf=np.array(color)
        leaf[:,:,3]=np.rint(leaf[:,:,3].astype(float)*(.5/.622)).clip(0,255).astype('u1');leaf=Image.fromarray(leaf)
        bark=color.copy();bark.putalpha(255)
        packed=np.array(Image.open(file(root+'_Textures/normal_specular.png')).convert('RGBA'))
        x=packed[:,:,3].astype(float)/127.5-1;y=1-packed[:,:,1].astype(float)/127.5;z=np.sqrt(np.maximum(0,1-x*x-y*y))
        nm=Image.fromarray(np.rint(np.stack([(x+1)*127.5,(y+1)*127.5,(z+1)*127.5,np.full(x.shape,255)],axis=-1)).clip(0,255).astype('u1'))
        arm=Image.new('RGB',color.size,(255,190,0));name=f'broadleaf_{i}'
        write_model(out,name,parts,[leaf,bark],[nm,nm],[mask(arm,True),mask(arm,False)])
        result[name]=1
    return result


def preview(out):
    board=Image.new('RGB',(5*224,6*248),(28,34,37));draw=ImageDraw.Draw(board)
    for i,name in enumerate(OLD+NEW):
        with (out/name/'impostor.bin').open('rb') as f:
            _,az,el,w,h,*_=struct.unpack('<8s4I7f',f.read(52));f.seek(52+az*w*h*4)
            image=Image.frombytes('RGBA',(w,h),f.read(w*h*4)).resize((216,216))
        x=(i%5)*224;y=(i//5)*248;board.paste(image,(x+4,y+4),image);draw.text((x+6,y+224),f'{i}: {name}',fill='white')
    board.save(out/'catalogue.png')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache',type=Path,default=ROOT/'x64/VegetationDiversity/sources')
    p.add_argument('--out',type=Path,default=ROOT/'assets/foliage/biomes_v1')
    p.add_argument('--base',type=Path,default=ROOT.parent/'plantes/climate_shrubs_v2')
    p.add_argument('--blender',default=shutil.which('blender') or r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe')
    args=p.parse_args();download(args.cache);args.out.mkdir(parents=True,exist_ok=True)
    if not (args.base/'shrubs.txt').exists():raise ValueError('Build the base catalogue first with tools/plantes.ps1')
    (args.out/'biomes.txt').unlink(missing_ok=True) # fallback remains available throughout an in-place rebuild
    for name in OLD:
        target=args.out/name;target.mkdir(exist_ok=True)
        for f in ['mesh.bin','material.bin','lighting.bin','impostor.bin','impostor_light.bin']:
            source=args.base/name/f
            if source.exists() and (not (target/f).exists() or source.read_bytes()!=(target/f).read_bytes()):
                shutil.copy2(source,target/f)
    leaves={name:1 if name=='game_broadleaf' else 2 for name in OLD}
    leaves.update(broadleaves(args.cache,args.out))
    reduced=args.cache/'reduced'
    reducer=Path(__file__).with_name('reduit_sapins.py')
    reduction_hash=hashlib.sha256(reducer.read_bytes()+(args.cache/'fir_sapling/fir_sapling.gltf').read_bytes()
        +(args.cache/'fir_sapling/fir_sapling.bin').read_bytes()).hexdigest()
    reduction_stamp=reduced/'source.sha256'
    if not all((reduced/(name+'.npz')).exists() for name in ['fir_open','fir_dense']) or not reduction_stamp.exists() or reduction_stamp.read_text()!=reduction_hash:
        subprocess.run([args.blender,'--background','--factory-startup','--python',str(Path(__file__).with_name('reduit_sapins.py')),
                        '--',str(args.cache/'fir_sapling/fir_sapling.gltf'),str(reduced)],check=True)
        reduction_stamp.write_text(reduction_hash)
    for name,node in [('fir_open','fir_sapling_a'),('fir_dense','fir_sapling_c')]:
        leaves[name]=polyhaven(args.cache,args.out,'fir_sapling',node,name,reduced/(name+'.npz'))
    for asset,node,name in [('shrub_03','shrub_03_a','edge_shrub_a'),('shrub_03','shrub_03_c','edge_shrub_c'),
            ('searsia_lucida','searsia_lucida_g_LOD0','leafy_shrub'),('shrub_sorrel_01','shrub_sorrel_01_a','sorrel_a'),
            ('shrub_sorrel_01','shrub_sorrel_01_c','sorrel_c'),('grass_medium_01','grass_medium_01_tall_a_LOD0','grass_tall_a'),
            ('grass_medium_01','grass_medium_01_tall_c_LOD0','grass_tall_c'),('flower_empodium','flower_empodium_a_LOD0','flower_a'),
            ('flower_empodium','flower_empodium_d_LOD0','flower_d')]:
        leaves[name]=polyhaven(args.cache,args.out,asset,node,name)
    bake.OUT=args.out;volume_assets.DEST=args.out
    for name in NEW:
        folder=args.out/name
        fingerprint=hashlib.sha256((folder/'mesh.bin').read_bytes()+(folder/'material.bin').read_bytes()
            +Path(bake.__file__).read_bytes()+Path(volume_assets.__file__).read_bytes()).hexdigest()
        stamp=folder/'cooked.sha256'
        if (folder/'impostor_light.bin').exists() and stamp.exists() and stamp.read_text()==fingerprint:continue
        verts,indices,atlas,lo,hi,materials=bake.load(name)
        bake.volume(name,verts,indices,atlas,lo,hi,materials,64)
        bake.impostor(name,verts,indices,atlas,lo,hi,materials)
        volume_assets.SPEC[name]={'leaf':int(math.log2(leaves[name]&-leaves[name]))}
        volume_assets.bake_light(name)
        stamp.write_text(fingerprint)
    preview(args.out)
    records=['FOLBIO01 29']
    for i,name in enumerate(OLD+NEW):
        group=0 if i in [0,14,15] else 1 if i==1 or 16<=i<=19 else 2
        records.append(f'{name} {group} {leaves[name]}')
    # Publish readiness last; incomplete builds are never auto-selected by the game.
    (args.out/'biomes.txt').write_text('\n'.join(records)+'\n',encoding='ascii')
    print('Ready:',args.out,'29 models, original catalogue preserved.',flush=True)


if __name__=='__main__':main()
