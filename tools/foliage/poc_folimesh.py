"""Cook a licensed FoliMesh GLB into an external Exolune comparison catalogue.

No account, download, engine change, interactive launch or benchmark is performed.
The original pivot, textures and alpha are retained; the existing native wind is used.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import shutil
import struct
import numpy as np
from PIL import Image
from importe import ROOT, accessor
from prepare_biomes import write_model
import bake
import volume_assets


def load_glb(path):
    data=path.read_bytes()
    if struct.unpack_from('<4sII',data)!=(b'glTF',2,len(data)):
        raise ValueError('Expected a complete glTF 2 GLB')
    chunks={};offset=12
    while offset<len(data):
        size,kind=struct.unpack_from('<II',data,offset);offset+=8
        if offset+size>len(data):raise ValueError('Truncated GLB chunk')
        chunks[kind]=data[offset:offset+size];offset+=size
    return json.loads(chunks[0x4e4f534a]),chunks[0x004e4942]


def image_for(doc,blob,info,fallback):
    if not info:return fallback.copy()
    if info.get('texCoord',0)!=0 or info.get('extensions'):
        raise ValueError('Texture transforms or alternate material UVs need explicit import support')
    image=doc['images'][doc['textures'][info['index']]['source']]
    view=doc['bufferViews'][image['bufferView']];start=view.get('byteOffset',0)
    return Image.open(io.BytesIO(blob[start:start+view['byteLength']])).convert('RGBA')


def material_images(doc,blob,index,leaf):
    material=doc['materials'][index];pbr=material.get('pbrMetallicRoughness',{})
    color=image_for(doc,blob,pbr.get('baseColorTexture'),Image.new('RGBA',(16,16),'white'))
    rgba=np.array(color,dtype=np.float64)/255
    factor=np.asarray(pbr.get('baseColorFactor',[1,1,1,1]))
    linear=np.where(rgba[:,:,:3]<=.04045,rgba[:,:,:3]/12.92,((rgba[:,:,:3]+.055)/1.055)**2.4)*factor[:3]
    rgba[:,:,:3]=np.where(linear<=.0031308,linear*12.92,1.055*np.maximum(linear,0)**(1/2.4)-.055)
    rgba[:,:,3]*=factor[3]
    if material.get('alphaMode','OPAQUE')=='OPAQUE':rgba[:,:,3]=1
    else:rgba[:,:,3]*=.5/max(material.get('alphaCutoff',.5),1e-6)
    color=Image.fromarray(np.rint(rgba.clip(0,1)*255).astype('u1'))
    normal=image_for(doc,blob,material.get('normalTexture'),Image.new('RGBA',(16,16),(128,128,255,255)))
    scale=material.get('normalTexture',{}).get('scale',1)
    if scale!=1:
        values=np.asarray(normal,dtype=np.float64)[:,:,:3]/127.5-1
        values[:,:,:2]*=scale;values/=np.maximum(np.linalg.norm(values,axis=2,keepdims=True),1e-8)
        normal=Image.fromarray(np.concatenate((np.rint((values+1)*127.5).clip(0,255).astype('u1'),np.full((*values.shape[:2],1),255,'u1')),axis=2))
    arm=image_for(doc,blob,pbr.get('metallicRoughnessTexture'),Image.new('RGBA',(16,16),'white')).resize(color.size)
    ao=image_for(doc,blob,material.get('occlusionTexture'),Image.new('RGBA',(16,16),'white')).resize(color.size)
    masks=np.empty((*np.asarray(color).shape[:2],4),'u1')
    strength=material.get('occlusionTexture',{}).get('strength',1)
    masks[:,:,0]=np.rint(255+(np.asarray(ao)[:,:,0].astype(float)-255)*strength).clip(0,255)
    masks[:,:,1]=np.rint(np.asarray(arm)[:,:,1].astype(float)*pbr.get('roughnessFactor',1)).clip(0,255)
    masks[:,:,2]=255 if leaf else 0;masks[:,:,3]=255
    return color,normal,Image.fromarray(masks)


def apply_vertex_shade(folder,name,shade):
    """Preserve the source's grey vertex tint in the seven native lighting factors."""
    path=folder/'lighting.bin';raw=path.read_bytes()
    light=np.frombuffer(raw,dtype='<f4',offset=16).reshape(-1,8).copy()
    light[:,:7]*=shade[:,None].clip(0,1)
    path.write_bytes(raw[:16]+light.tobytes())
    verts,indices,atlas,_,_,materials=bake.load(name)
    header=(folder/'impostor.bin').read_bytes()[:52]
    _,az,el,w,h,*rest=struct.unpack('<8s4I7f',header)
    images,coverage=volume_assets.bake_light_views(verts,indices,atlas,light,rest[-1],az,el,w*2,materials)
    images=images.reshape(az*el,h,2,w,2,8);weights=coverage.reshape(az*el,h,2,w,2)
    total=np.maximum(weights.sum(axis=(2,4)),1);planes=[]
    for first in (0,4):
        values=(images[...,first:first+4]*weights[...,None]).sum(axis=(2,4))/total[...,None]
        planes.append(np.rint(values.clip(0,1)*255).astype('u1'))
    with (folder/'impostor_light.bin').open('wb') as stream:
        stream.write(struct.pack('<8s4I',b'FOLIL001',az,el,w,h))
        for plane in planes:stream.write(plane.tobytes())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--base',type=Path,default=ROOT/'assets/foliage/game_biomes_v1')
    parser.add_argument('--lod',type=int,default=1,help='GLB LOD 0 is the hero mesh; 1 is the first game LOD')
    args=parser.parse_args();out=args.out.resolve();source=args.source.resolve()
    if out.is_relative_to(ROOT.resolve()) or out==args.base.resolve():
        raise ValueError('The licensed POC catalogue must stay outside the public repository')
    records=(args.base/'biomes.txt').read_text().splitlines()
    if records[0]!='FOLBIO02 31':raise ValueError('Expected the current 31-model baseline')
    if (out/'biomes.txt').exists():raise ValueError('Use a fresh output catalogue to preserve previous trials')
    doc,blob=load_glb(source);parts=[];attributes={};shades=[];names=[];original_materials=[]
    for node in doc['nodes']:
        metadata=node.get('extras',{}).get('alardonTree',{})
        if 'mesh' not in node or metadata.get('lod')!=args.lod:continue
        if any(k in node for k in ['matrix','rotation','translation','scale','skin']):
            raise ValueError('Unexpected node transform or skin; inspect the exported GLB')
        names.append(node['name'])
        for primitive in doc['meshes'][node['mesh']]['primitives']:
            if primitive.get('mode',4)!=4:raise ValueError('Expected triangles')
            a=primitive['attributes'];material=primitive['material']
            if material not in original_materials:original_materials.append(material)
            target=original_materials.index(material)
            position=accessor(doc,blob,a['POSITION']).copy();normal=accessor(doc,blob,a['NORMAL']).copy()
            uv=accessor(doc,blob,a['TEXCOORD_0']).copy();triangles=accessor(doc,blob,primitive['indices']).reshape(-1).copy()
            tint=accessor(doc,blob,a['COLOR_0']).copy() if 'COLOR_0' in a else np.ones_like(position)
            if np.ptp(tint[:,:3],axis=1).max()>1e-5:raise ValueError('Coloured vertex tint needs a separate native colour channel')
            shades.append(tint[:,0]);parts.append((position,normal,uv,triangles,target))
            for key,index in a.items():attributes[f'part{len(parts)-1}_{key}']=accessor(doc,blob,index).copy()
    if not parts:raise ValueError('No meshes found for the selected vendor LOD')
    materials=[doc['materials'][i] for i in original_materials]
    leaves=[i for i,m in enumerate(materials) if 'leav' in m.get('name','').lower()]
    if len(leaves)!=1:raise ValueError('Inspect the woody/leafy material split before cooking')
    out.mkdir(parents=True,exist_ok=True);name='folimesh_old_oak';folder=out/name
    maps=[material_images(doc,blob,i,j in leaves) for j,i in enumerate(original_materials)]
    write_model(out,name,parts,*[list(images) for images in zip(*maps)],tile=1024)
    # Keep the authored ground pivot, including roots below Y=0 and crown asymmetry.
    positions=np.concatenate([part[0] for part in parts]);lo=positions.min(0);hi=positions.max(0)
    offset=np.array([(lo[0]+hi[0])/2,lo[1],(lo[2]+hi[2])/2])/(hi[1]-lo[1])
    path=folder/'mesh.bin';raw=bytearray(path.read_bytes());header=list(struct.unpack_from('<8s5I6f',raw))
    vertices=np.frombuffer(raw,dtype='<f4',count=header[1]*9,offset=52).reshape(-1,9)
    vertices[:,:3]+=offset;header[6:9]=(np.asarray(header[6:9])+offset).tolist();header[9:12]=(np.asarray(header[9:12])+offset).tolist()
    struct.pack_into('<8s5I6f',raw,0,*header);path.write_bytes(raw)
    np.savez_compressed(folder/'source_attributes.npz',**attributes)
    bake.OUT=out;volume_assets.DEST=out;volume_assets.SPEC[name]={'leaf':leaves[0]}
    v,idx,atlas,lo,hi,count=bake.load(name)
    bake.volume(name,v,idx,atlas,lo,hi,count,64);bake.impostor(name,v,idx,atlas,lo,hi,count)
    volume_assets.bake_light(name);apply_vertex_shade(folder,name,np.concatenate(shades))
    replacement_ids={1,16,17,18,19};published=[records[0]]
    for index,line in enumerate(records[1:]):
        original,kind,mask=line.split()
        if index in replacement_ids:published.append(f'{name} {kind} {1<<leaves[0]}');continue
        destination=out/original;destination.mkdir(exist_ok=True)
        for file in (args.base/original).glob('*.bin'):shutil.copyfile(file,destination/file.name)
        published.append(line)
    report={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'source_generator':doc['asset'].get('generator'),'source_metadata':doc['nodes'][0].get('extras'),
            'selected_vendor_lod':args.lod,'nodes':names,'vertices':len(v),'triangles':len(idx)//3,
            'material_names':[m['name'] for m in materials],'leaf_mask':1<<leaves[0],
            'mesh_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'replaced_model_ids':sorted(replacement_ids),
            'scope':'Isolated source-evaluation catalogue; all broadleaf slots use one witness; no diversity claim',
            'pivot':'Original GLB ground origin; uniform height normalization only',
            'vertex_colour':'Grey tint folded into native diffuse-light factors, clamped to [0,1]',
            'wind':'Existing native height/leaf wind; source extra UV attributes preserved but not interpreted',
            'root_contact':'Source roots preserved; no new root deformation or terrain geometry',
            'materials':'Base colour/alpha, normal including scale, roughness/AO; native leaf transmission; vendor volume/specular extensions not reproduced',
            'licence':'FoliMesh Free; non-commercial prototype/evaluation; sources and cooked files outside git'}
    (out/'poc-report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'biomes.txt').write_text('\n'.join(published)+'\n',encoding='ascii')
    print(json.dumps({'catalogue':str(out),'triangles':report['triangles'],'vertices':len(v),'status':'cooked; native review still required'}),flush=True)


if __name__=='__main__':main()
