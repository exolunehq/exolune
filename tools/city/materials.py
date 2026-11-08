"""Pack generated GLB PBR maps into shared, mipmapped architectural texture arrays."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import math
import re
import struct
import sys
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/foliage'))
from poc_folimesh import load_glb


def generated_surface(name,size):
    """Periodic metric detail. All three maps share the same generated height."""
    rng=np.random.default_rng(810+sum(map(ord,name)))
    y,x=np.mgrid[0:size,0:size].astype('f4')/size
    height=np.zeros_like(x)
    for frequency,weight in [(4,.35),(13,.22),(37,.12),(93,.04)]:
        height+=weight*np.sin(math.tau*(x*frequency+y*(frequency//3))+rng.uniform(0,6))*np.cos(math.tau*y*frequency+rng.uniform(0,6))
    if name in ['timber','slatted_timber']:
        # Long fibres, broad growth rings and restrained pores share their
        # height/colour/roughness signals; no painted-in illumination.
        bend=.035*np.sin(y*math.tau)+.012*np.sin(y*math.tau*3)
        fibre=np.sin(math.tau*(x+bend)*47)
        rings=np.sin(math.tau*((x+bend)*7+.12*np.sin(y*math.tau)))
        height=.12*fibre+.22*rings+.025*height
        if name=='slatted_timber':
            groove=np.exp(-(np.minimum(np.mod(x*12,1),1-np.mod(x*12,1))/.045)**4)
            height-=groove*.70
    if name=='ceramic':height*=.18
    contrast={'ceramic':.025,'timber':.15,'slatted_timber':.15,'stone':.12,'permeable':.19,'path_border':.09,'common_paving':.10}[name]
    color=np.clip(.94+height*contrast,0,1)
    if name=='slatted_timber':color*=1-groove*.40
    strength=2.4 if name in ['timber','slatted_timber'] else 1.4 if name in ['stone','common_paving'] else .9
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))*strength;dy=(np.roll(height,-1,0)-np.roll(height,1,0))*strength
    normal=np.stack([-dx,-dy,np.ones_like(x)],-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    if name in ['timber','slatted_timber']:
        # A two-metre finished timber sheet has submillimetre grain relief.
        # Keep its normal amplitude independent of texture resolution.
        metres=height*.0003
        if name=='slatted_timber':metres-=groove*.0015
        dx=(np.roll(metres,-1,1)-np.roll(metres,1,1))*size/4
        dy=(np.roll(metres,-1,0)-np.roll(metres,1,0))*size/4
        normal=np.stack([-dx,-dy,np.ones_like(x)],-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    panel=None
    if name=='ceramic':
        # Two-metre cladding sheet, 1.2 mm recessed joints with a rounded lip.
        # Height, colour and roughness share this mask. Pixel filtering of the
        # maps replaces a second, unrelated line grid in the fragment shader.
        edge=np.minimum(np.minimum(x,1-x),np.minimum(y,1-y))
        panel=np.exp(-(edge/.0025)**2)
        metres=height*.00008-panel*.0012
        dx=(np.roll(metres,-1,1)-np.roll(metres,1,1))*size/4
        dy=(np.roll(metres,-1,0)-np.roll(metres,1,0))*size/4
        normal=np.stack([-dx,-dy,np.ones_like(x)],-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
        color=np.clip(color-panel*.08,0,1)
    rgba=np.full((size,size,4),255,dtype='u1');rgba[:,:,:3]=np.rint(color[:,:,None]*255).astype('u1')
    nr=rgba.copy();nr[:,:,:3]=np.rint((normal*.5+.5)*255).astype('u1')
    orm=rgba.copy();orm[:,:,0]=255;orm[:,:,1]=np.rint(np.clip(.88+height*(.22 if name=='timber' else .10),0,1)*255).astype('u1');orm[:,:,2]=255
    if panel is not None:orm[:,:,1]=np.rint(np.clip(.88+height*.1+panel*.07,0,1)*255).astype('u1')
    return [Image.fromarray(rgba),Image.fromarray(nr),Image.fromarray(orm)]


def manufactured_sheet(name,size):
    """Reusable shallow features, with a shared height-derived normal and PBR.

    This is deterministic material authoring, not an image-to-mesh result or
    a claimed high-poly projection. Silhouettes and deep openings stay meshes.
    """
    y,x=np.mgrid[0:size,0:size].astype('f4')/(size-1)
    h=np.zeros_like(x);tone=np.ones_like(x)*.90;rough=np.ones_like(x)*.88
    distance=np.minimum.reduce([x-.035,.965-x,y-.035,.965-y])
    seam=np.exp(-(distance/.007)**4)
    h-=seam*.0015;tone-=seam*.30;rough+=seam*.10
    for xx in [.09,.91]:
        for yy in [.09,.91]:
            r=np.hypot(x-xx,y-yy)
            head=np.exp(-(r/.023)**8);socket=np.exp(-(r/.010)**4)
            h+=head*.0007-socket*.0017;tone+=head*.08-socket*.45
    if name=='service_panel':
        for yy in [.30,.40,.50,.60,.70]:
            slot=np.exp(-((y-yy)/.014)**4)*np.clip((x-.18)*80,0,1)*np.clip((.82-x)*80,0,1)
            h-=slot*.002;tone-=slot*.58;rough+=slot*.09
    else:
        screen=(x>.18)&(x<.82)&(y>.18)&(y<.57)
        h-=screen*.0008;tone[screen]=.27;rough[screen]=.43
        for row,length in [(.27,.47),(.34,.36),(.41,.43)]:
            line=(x>.26)&(x<length+.26)&(abs(y-row)<.006)
            tone[line]=1.0
        for xx in [.29,.50,.71]:
            button=np.exp(-((x-xx)**2+(y-.76)**2)/.028**2)
            h+=button*.001;tone+=button*.12
    # The single panel is UV-mapped once; mipmaps filter tiny slots and bolts.
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))*size;dy=(np.roll(h,-1,0)-np.roll(h,1,0))*size
    normal=np.stack([-dx,-dy,np.ones_like(h)],-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    rgba=np.full((size,size,4),255,dtype='u1');rgba[:,:,:3]=np.rint(np.clip(tone,0,1)[:,:,None]*255).astype('u1')
    nr=rgba.copy();nr[:,:,:3]=np.rint((normal*.5+.5)*255).astype('u1')
    orm=rgba.copy();orm[:,:,0]=255;orm[:,:,1]=np.rint(np.clip(rough,0,1)*255).astype('u1');orm[:,:,2]=255
    return [Image.fromarray(rgba),Image.fromarray(nr),Image.fromarray(orm)]


def mip(image,srgb):
    a=np.asarray(image,dtype=np.float32)/255
    if srgb:a[:,:,:3]=np.where(a[:,:,:3]<=.04045,a[:,:,:3]/12.92,((a[:,:,:3]+.055)/1.055)**2.4)
    h,w=a.shape[:2]
    a=a.reshape(h//2,2,w//2,2,4).mean((1,3))
    if srgb:a[:,:,:3]=np.where(a[:,:,:3]<=.0031308,a[:,:,:3]*12.92,1.055*np.maximum(a[:,:,:3],0)**(1/2.4)-.055)
    return Image.fromarray(np.rint(np.clip(a,0,1)*255).astype('u1'))


def prepare(recipe,sources,out,size=1024,overrides=None):
    out.mkdir(parents=True,exist_ok=True);entries=[];mapping={};layers=[];known={}
    # The shared white/flat layer makes procedural materials texture independent.
    layers.append([Image.new('RGBA',(size,size),(255,255,255,255)),Image.new('RGBA',(size,size),(128,128,255,255)),Image.new('RGBA',(size,size),(255,255,255,255))])
    base_names=['ceramic','teal','timber','solar','glazing','bronze','light','stone','leaf','soil','flower','water']
    roles={name:i for i,name in enumerate(base_names)}
    roles.update(room_glass=15,cabin_glass=16,door_glass=17,rubber=18,satin_metal=19,control_screen=20)
    roles.update(service_panel=21,control_panel=22,slatted_timber=23)
    for asset in recipe['assets']:
        source=Path((overrides or {}).get(asset['id'],sources/asset['id']/'master.glb'))
        doc,blob=load_glb(source);local={}
        def image(info,fallback):
            if not info:return Image.new('RGBA',(size,size),fallback)
            item=doc['images'][doc['textures'][info['index']]['source']]
            if 'bufferView' not in item:raise ValueError('Production GLB must embed textures')
            view=doc['bufferViews'][item['bufferView']];start=view.get('byteOffset',0)
            return Image.open(io.BytesIO(blob[start:start+view['byteLength']])).convert('RGBA').resize((size,size),Image.Resampling.LANCZOS)
        for j,mat in enumerate(doc.get('materials',[])):
            name=mat.get('name',f'material_{j}');pbr=mat.get('pbrMetallicRoughness',{})
            # Blender adds .001 when a second master is authored in one
            # process. Stable source semantics must survive that display name.
            canonical=mat.get('extras',{}).get('city_material',re.sub(r'\.\d{3}$','',name))
            semantic=roles.get(canonical,100)
            maps=any(k in pbr for k in ['baseColorTexture','metallicRoughnessTexture']) or 'normalTexture' in mat
            signature=json.dumps({**mat,'name':canonical},sort_keys=True) if not maps else hashlib.sha256(source.read_bytes()).hexdigest()+':'+str(j)
            if signature not in known:
                layer=0
                if maps:
                    layer=len(layers)
                    color=image(pbr.get('baseColorTexture'),(255,255,255,255))
                    normal=image(mat.get('normalTexture'),(128,128,255,255))
                    orm=image(pbr.get('metallicRoughnessTexture'),(255,255,255,255))
                    layers.append([color,normal,orm])
                elif canonical in ['service_panel','control_panel']:
                    layer=len(layers);layers.append(manufactured_sheet(canonical,size))
                elif canonical in ['ceramic','timber','stone','slatted_timber']:
                    layer=len(layers);layers.append(generated_surface(canonical,size))
                emission=mat.get('emissiveFactor',[0,0,0]);emit=max(emission)*mat.get('extensions',{}).get('KHR_materials_emissive_strength',{}).get('emissiveStrength',1)
                entry={'name':canonical,'color':pbr.get('baseColorFactor',[1,1,1,1]),
                       'properties':[pbr.get('roughnessFactor',1),pbr.get('metallicFactor',1),emit,semantic],
                       'texture':[layer,mat.get('normalTexture',{}).get('scale',1),0,0]}
                known[signature]=len(entries);entries.append(entry)
            local[name]=known[signature]
        mapping[asset['id']]=local
    for name,color,rough,semantic in [('permeable',[.24,.215,.16,1],.96,12),
                                    ('path_border',[.42,.37,.28,1],.85,13),
                                    ('common_paving',[.48,.45,.36,1],.82,14)]:
        layer=len(layers);layers.append(generated_surface(name,size))
        entries.append({'name':name,'color':color,'properties':[rough,0,0,semantic],'texture':[layer,1,0,0]})
    levels=size.bit_length()
    for channel in range(3):
        file=out/f'texture{channel}.bin'
        with file.open('wb') as f:
            f.write(struct.pack('<8s4I',b'CITYTEX1',size,len(layers),levels,channel))
            for layer in layers:
                current=layer[channel]
                for level in range(levels):
                    f.write(current.tobytes())
                    if level+1<levels:current=mip(current,channel==0)
    report={'materials':entries,'mapping':mapping,'layers':len(layers),'texture_size':size,'mips':levels,
            'textures':{f'texture{k}.bin':hashlib.sha256((out/f'texture{k}.bin').read_bytes()).hexdigest() for k in range(3)}}
    (out/'materials.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recipe',type=Path,required=True)
    p.add_argument('--sources',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--overrides',type=Path);a=p.parse_args()
    prepare(json.loads(a.recipe.read_text(encoding='utf8')),a.sources,a.out,
            overrides=json.loads(a.overrides.read_text()) if a.overrides else None)


if __name__=='__main__':main()
