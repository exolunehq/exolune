"""Cook a local generated plant into an isolated native comparison catalogue.

The source GLB stays unchanged. Existing native wind is used for the cost test;
the exported shoot and leaf attributes are preserved, not interpreted by the engine.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import sys
import struct
import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from importe import ROOT, accessor
from poc_folimesh import load_glb, material_images
from prepare_biomes import write_model
import bake
import volume_assets


def root_reference(source,folder,shape,origin,height):
    """Bake coarse materials against the same deformed master as the meshes."""
    from audit import array
    from variations import write_glb
    doc,raw=load_glb(source);blob=bytearray(raw)
    def put(index,value):
        entry=doc['accessors'][index]
        if entry['componentType']!=5126:raise ValueError('Native root reference requires float attributes')
        target=array(doc,blob,index);target[:]=value
        entry['min']=target.min(0).astype(float).tolist();entry['max']=target.max(0).astype(float).tolist()
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            attrs=primitive['attributes'];p=(array(doc,raw,attrs['POSITION'])-origin)/height
            normal=array(doc,raw,attrs['NORMAL']);tangent=array(doc,raw,attrs['TANGENT']).copy()
            q,n,t=shape.apply(p,normal,tangent[:,:3]);tangent[:,:3]=t
            put(attrs['POSITION'],q*height+origin);put(attrs['NORMAL'],n);put(attrs['TANGENT'],tangent)
            for key in ['_WIND_PIVOT','_LEAF_PIVOT']:
                if key in attrs:
                    points=(array(doc,raw,attrs[key])-origin)/height
                    put(attrs[key],shape.apply(points)[0]*height+origin)
    path=folder/'native-reference.glb';write_glb(path,doc,blob);return path


def read_attribute(doc,blob,index):
    value=accessor(doc,blob,index).copy()
    if doc['accessors'][index].get('normalized'):
        if value.dtype.kind=='u':value=value.astype(np.float32)/np.iinfo(value.dtype).max
        elif value.dtype.kind=='i':value=np.maximum(-1,value.astype(np.float32)/np.iinfo(value.dtype).max)
    return value


def palette_tint(parts,images,colors,tile):
    """Bake bounded RGB tint variants into UV cells; no runtime format change."""
    palette=[np.ones(3)]+[np.array([.86,1,.86])*shade for shade in np.linspace(.78,1,15)]
    palette=np.asarray(palette,dtype=np.float32);grid=4;size=tile//grid
    tint=colors[:,:3]
    selected=np.argmin(np.sum((tint[:,None,:]-palette[None,:,:])**2,axis=2),axis=1)
    error=float(np.max(np.abs(tint-palette[selected])))
    triangles=parts[3].reshape(-1,3)
    if not np.all(selected[triangles]==selected[triangles[:,0,None]]):
        raise ValueError('Source tint varies inside a triangle; explicit baking is required')
    uv=parts[2].copy()
    if uv.min()<0 or uv.max()>1:raise ValueError('Tint-palette UVs must remain within the source image')
    uv[:,0]=(uv[:,0]+selected%grid)/grid;uv[:,1]=(uv[:,1]+selected//grid)/grid
    atlases=[Image.new('RGBA',(tile,tile)) for image in images]
    for slot,factor in enumerate(palette):
        for channel,image in enumerate(images):
            cell=image.resize((size,size),Image.Resampling.LANCZOS)
            if channel==0:
                rgba=np.asarray(cell).copy();rgb=rgba[:,:,:3].astype(np.float64)/255
                linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)*factor
                rgb=np.where(linear<=.0031308,linear*12.92,1.055*np.maximum(linear,0)**(1/2.4)-.055)
                rgba[:,:,:3]=np.rint(rgb.clip(0,1)*255).astype('u1');cell=Image.fromarray(rgba)
            atlases[channel].paste(cell,((slot%grid)*size,(slot//grid)*size))
    return (parts[0],parts[1],uv,parts[3],parts[4]),atlases,error


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--base',type=Path,default=ROOT/'assets/foliage/game_biomes_v1')
    parser.add_argument('--tile',type=int,default=2048,choices=[1024,2048])
    parser.add_argument('--lods',action='store_true',help='Cook the production geometry chain and source vertex data')
    parser.add_argument('--name',default='local_oak_approved')
    parser.add_argument('--blender',type=Path,default=Path('C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'))
    args=parser.parse_args();out=args.out.resolve();source=args.source.resolve();base=args.base.resolve()
    if out.is_relative_to(ROOT) or out==base:raise ValueError('Comparison assets must remain outside the source tree')
    if out.exists():raise ValueError('Use a fresh output directory')
    lines=(base/'biomes.txt').read_text().splitlines()
    if lines[0]!='FOLBIO02 31':raise ValueError('Expected the current 31-model catalogue')
    doc,blob=load_glb(source);parts=[];images=[];bake_parts=[];bake_images=[];attributes={};leaf_mask=0;tint_error=0
    for node in doc['nodes']:
        if 'mesh' not in node:continue
        if any(key in node for key in ['matrix','translation','rotation','scale','skin']):
            raise ValueError('Inspect transformed or skinned source nodes')
        for primitive in doc['meshes'][node['mesh']]['primitives']:
            if primitive.get('mode',4)!=4:raise ValueError('Triangle meshes required')
            a=primitive['attributes'];material=doc['materials'][primitive['material']]
            leaf=material.get('alphaMode')=='MASK';slot=len(parts)
            if leaf:leaf_mask|=1<<slot
            def read(name):return read_attribute(doc,blob,a[name])
            part=(read('POSITION'),read('NORMAL'),read('TEXCOORD_0'),read_attribute(doc,blob,primitive['indices']).reshape(-1),slot)
            maps=material_images(doc,blob,primitive['material'],leaf)
            original_part=part;original_maps=maps
            if 'COLOR_0' in a:
                part,maps,error=palette_tint(part,maps,read('COLOR_0'),args.tile);tint_error=max(tint_error,error)
            bake_parts.append(part);bake_images.append(maps)
            parts.append(original_part if args.lods else part);images.append(original_maps if args.lods else maps)
            for name,index in a.items():attributes[f'part{slot}_{name}']=read_attribute(doc,blob,index)
    if len(parts)!=2 or leaf_mask not in [1,2]:raise ValueError('Expected woody and masked foliage materials')
    name=args.name
    if not name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in name):raise ValueError('Invalid plant name')
    out.mkdir(parents=True);folder=out/name
    source_positions=np.concatenate([part[0] for part in parts]);source_height=float(np.ptp(source_positions[:,1]))
    source_origin=np.array([0,float(source_positions[:,1].min()),0])
    write_model(out,name,parts,*[list(channel) for channel in zip(*images)],tile=args.tile,origin=source_origin)
    np.savez_compressed(folder/'source_attributes.npz',**attributes)
    bake.OUT=out;volume_assets.DEST=out;volume_assets.SPEC[name]={'leaf':int(np.log2(leaf_mask))}
    v,indices,atlas,lo,hi,count=bake.load(name)
    extra=None;lod_report=None
    if args.lods:
        from lods import source_extra,make
        extra=source_extra(attributes,v,source_origin,source_height)
        wood=((leaf_mask>>v[:,8].astype(int))&1)==0
        radial=np.linalg.norm(v[:,[0,2]],axis=1);band=wood&(v[:,1]>.06)&(v[:,1]<.18)
        base_radius=float(np.quantile(radial[band],.6));reach=float(radial[wood&(v[:,1]<.16)].max())
        root=wood&(v[:,1]<.16)&(radial>base_radius*.65)
        v[root,8]=np.floor(v[root,8])+.25
        crown=v[v[:,1]>.2,:3];width=float(max(np.ptp(crown[:,0]),np.ptp(crown[:,2])))
        from roots import conform
        v,root_report,shape=conform(v,indices,leaf_mask,target_reach=.085*width/.45,return_shape=True)
        extra[:,4:7]=shape.apply(extra[:,4:7])[0];extra[:,8:11]=shape.apply(extra[:,8:11])[0]
        # Artist-style crown normals supply coherent bouquet volume while the
        # original curved leaf normals retain local variation. Wood is intact.
        faces=indices.reshape(-1,3);leaf_faces=faces[(~wood[faces]).all(1)&(extra[faces,11].max(1)>0)]
        leaf_ids=np.unique(leaf_faces);leaf_points=v[leaf_ids,:3]
        lower,upper=leaf_points.min(0),leaf_points.max(0);centre=(lower+upper)*.5;radii=np.maximum((upper-lower)*.5,.05)
        outward=(leaf_points-centre)/(radii*radii);outward/=np.maximum(np.linalg.norm(outward,axis=1,keepdims=True),1e-8)
        shaded=v[leaf_ids,3:6]*.65+outward*.35;shaded/=np.maximum(np.linalg.norm(shaded,axis=1,keepdims=True),1e-8)
        v[leaf_ids,3:6]=shaded
        base_radius*=shape.ratio;reach=float(np.linalg.norm(v[root][:,[0,2]],axis=1).max())
        flare=max(float(v[root,1].max()),.005)
        lo=v[:,:3].min(0);hi=v[:,:3].max(0)
        raw=bytearray((folder/'mesh.bin').read_bytes());struct.pack_into('<6f',raw,28,*lo,*hi);raw[52:52+len(v)*36]=v.astype('<f4').tobytes();(folder/'mesh.bin').write_bytes(raw)
        (folder/'form.bin').write_bytes(struct.pack('<8s4f',b'FOLFORM1',base_radius,flare,reach,width))
        bake_source=root_reference(source,folder,shape,source_origin,source_height)
    baked_vertices=v.copy();baked_atlas=Image.new('RGBA',(args.tile*count,args.tile));first=0
    for slot,(part,maps) in enumerate(zip(bake_parts,bake_images)):
        baked_vertices[first:first+len(part[0]),6:8]=part[2];first+=len(part[0])
        baked_atlas.paste(maps[0].resize((args.tile,args.tile),Image.Resampling.LANCZOS),(slot*args.tile,0))
    baked_atlas=np.asarray(baked_atlas)
    leaf_flags=None
    if args.lods:
        leaf_flags=np.zeros(len(v),np.float32);leaf_flags[leaf_ids]=1
    bake.volume(name,baked_vertices,indices,baked_atlas,lo,hi,count,64);bake.impostor(name,baked_vertices,indices,baked_atlas,lo,hi,count);volume_assets.bake_light(name,leaf_flags)
    if args.lods:
        light=np.frombuffer((folder/'lighting.bin').read_bytes(),dtype='<f4',offset=16).reshape(-1,8).copy()
        lod_report=make(folder,v,indices,light,extra,leaf_mask,args.blender,bake_source,source_origin,source_height)
        from near_wood import cook as refine_near_wood
        near_report=refine_near_wood(folder,leaf_mask)
        lod_report['levels'][0].update(vertices=near_report['vertices'],triangles=near_report['triangles'])
        lod_report['near_wood']=near_report
        (folder/'lod-report.json').write_text(json.dumps(lod_report,indent=2)+'\n')
    # A class-wide comparison: identical population and five broadleaf roles.
    replaced=[];published=[lines[0]]
    for slot,line in enumerate(lines[1:]):
        original,kind,mask=line.split()
        if int(kind)==1:
            replaced.append(slot);published.append(f'{name} {kind} {leaf_mask}');continue
        target=out/original;target.mkdir(exist_ok=True)
        for file in (base/original).glob('*.bin'):
            try:os.link(file,target/file.name)
            except OSError:shutil.copyfile(file,target/file.name)
        published.append(line)
    report={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'cooker_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(__file__).with_name('lods.py'),Path(__file__).with_name('wood_lods.py'),Path(__file__).with_name('near_wood.py'),Path(__file__).with_name('roots.py'),Path(__file__).with_name('variations.py')]},
            'name':name,'vertices':len(v),'triangles':len(indices)//3,'materials':count,'tile':args.tile,
            'leaf_mask':leaf_mask,'replaced_slots':replaced,'tint_palette_max_linear_error':tint_error,
            'texture_note':'16 RGB tint cells for the single leaf; source alpha threshold remapped to native 0.5',
            'wind':'Existing native height/leaf shader; source attachment attributes archived, not uploaded',
            'scope':'Cost comparison only; five broadleaf slots share the approved witness; default catalogue unchanged'}
    if args.lods:report.update(lods=lod_report,root_envelope=root_report,normalization={'origin':source_origin.tolist(),'height':source_height},
        foliage_normals={'source_curvature_share':.65,'crown_gradient_share':.35,'leaf_vertices':len(leaf_ids),'wood_unchanged':True},
        vertex_colour='Source RGBA retained in the vertex sidecar; tint quantisation only for offline proxy baking',root_contact='Continuous supported root shape and canonical footprint shared by every LOD and impostor',wind='Source shoot/leaf weights and phases drive the shared native deformation; roots remain fixed')
    if args.lods:report.update(vertices=near_report['vertices'],triangles=near_report['triangles'],near_wood=near_report)
    (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'biomes.txt').write_text('\n'.join(published)+'\n',encoding='ascii')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
