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
import surface_classes

# Shared city material of each class of a generated shell, in mask order.
# `baked` scales the draft's atlas normal map; glass and light stay smooth.
SHELL_KIT={'shell':{'role':0,'rough':.42,'metal':0,'detail':'shell_plaster','baked':.2},
           'timber':{'role':2,'rough':.82,'metal':0,'detail':'plank_timber','baked':.6},
           'glazing':{'role':15,'rough':.07,'metal':0,'baked':0},
           'light':{'role':6,'rough':.35,'metal':0,'baked':0},
           'solar':{'role':3,'rough':.22,'metal':.45,'baked':.3},
           'cladding':{'role':1,'rough':.92,'metal':0,'detail':'shell_plaster','baked':.1}}
DETAIL_TILE_M=2.0
# A baked interior is a record, not a vertex material: color = window origin and
# box depth, properties = width axis and this role, texture = layer and height axis.
INTERIOR_ROLE=25
# Displayed draft atlases, block compressed: 2048 colour and normal, 1024 metal-roughness.
ATLAS_SIZE,ATLAS_ORM_SIZE=2048,1024


def interior_layer(item,size):
    """The room seen from its window (tools/city/interior_bake.py).

    Colour layer: RGB colour, A depth on eight bits. Normal layer: the same depth
    on sixteen bits, high byte in R and low byte in G. Depth is linear in both
    bytes, so hardware filtering and box mips of each byte stay exact.
    """
    path,depth_path=Path(item['bake']),Path(item['bake_depth'])
    for file,key in ((path,'bake_sha256'),(depth_path,'bake_depth_sha256')):
        if hashlib.sha256(file.read_bytes()).hexdigest()!=item[key]:raise ValueError('Interior bake hash mismatch: '+str(file))
    image=Image.open(path).convert('RGBA')
    if image.size!=(size,size):
        # Resample the depth apart: a joint RGBA resize would premultiply the colour by it.
        image=Image.merge('RGBA',[c.resize((size,size),Image.Resampling.LANCZOS) for c in image.split()])
    depth=np.flipud(np.load(depth_path)).astype('f4')   # The bake stores rows bottom-up, like Blender.
    if depth.shape!=(size,size):
        depth=np.asarray(Image.fromarray(depth,'F').resize((size,size),Image.Resampling.BILINEAR))
    code=np.rint(np.clip(depth,0,1)*65535).astype('u4')
    packed=np.zeros((size,size,4),dtype='u1');packed[:,:,0]=code>>8;packed[:,:,1]=code&255;packed[:,:,3]=255
    return [image,Image.fromarray(packed,'RGBA'),Image.new('RGBA',(size,size),(255,255,255,255))]


def spectral(rng,size,weight):
    """Periodic noise with a chosen spectrum; `weight(fx,fy)` takes cycles per tile."""
    fy=np.fft.fftfreq(size)[:,None]*size;fx=np.fft.rfftfreq(size)[None,:]*size
    field=np.fft.irfft2(np.fft.rfft2(rng.standard_normal((size,size)))*weight(fx,fy),(size,size))
    return (field/field.std()).astype('f4')


def band(f,low,high):return np.exp(-(f/high)**4)*(1-np.exp(-(f/low)**4))


def detail_maps(height,tone,rough):
    """Colour, normal and ORM images of one metric detail tile. `height` is in metres, `tone` linear."""
    size=height.shape[0];texel=DETAIL_TILE_M/size
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*texel);dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(2*texel)
    normal=np.stack([-dx,-dy,np.ones_like(dx)],-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    tone=np.clip(tone if tone.ndim==3 else tone[:,:,None].repeat(3,2),0,1)
    encoded=np.where(tone<=.0031308,tone*12.92,1.055*tone**(1/2.4)-.055)
    rgba=np.full((size,size,4),255,dtype='u1');rgba[:,:,:3]=np.rint(encoded*255).astype('u1')
    nr=rgba.copy();nr[:,:,:3]=np.rint((normal*.5+.5)*255).astype('u1')
    orm=np.full((size,size,4),255,dtype='u1');orm[:,:,1]=np.rint(np.clip(rough,0,1)*255).astype('u1')
    return [Image.fromarray(rgba),Image.fromarray(nr),Image.fromarray(orm)],float(tone.mean())


def shell_plaster(size):
    """Seamless mineral shell: a hand-finished undulation under a fine grain. No joints: the shells are monolithic."""
    rng=np.random.default_rng(2611)
    radial=lambda low,high:(lambda fx,fy:band(np.hypot(fx,fy),low,high))
    wave=spectral(rng,size,radial(6,34));grain=spectral(rng,size,radial(90,360));cloud=spectral(rng,size,radial(1.5,7))
    return detail_maps(wave*.00022+grain*.00004,.955+.022*cloud+.010*grain,.90+.07*cloud-.04*grain)


def plank_timber(size):
    """Boards 125 mm wide along U with open joints, end joints, growth rings and fibre."""
    rng=np.random.default_rng(2612);rows=16;step=size//rows
    across=((np.arange(size)%step)+.5)[:,None]/step
    fibre=spectral(rng,size,lambda fx,fy:np.exp(-(fx/2.5)**2)*band(np.abs(fy),70,380))
    figure=spectral(rng,size,lambda fx,fy:np.exp(-(fx/1.8)**2)*np.exp(-(np.abs(fy)/22)**2))
    tone=np.empty((size,size),'f4');late=np.empty((size,size),'f4');joint=np.zeros((size,size),'f4')
    shifted=np.empty((size,size),'f4')
    along=np.arange(size)
    for r in range(rows):
        rows_here=slice(r*step,(r+1)*step)
        # Each board is a different cut: its own fibre, ring count, tone and end joints.
        shifted[rows_here]=np.roll(fibre[rows_here],int(rng.integers(size)),1)
        warp=np.roll(figure[rows_here],int(rng.integers(size)),1)
        rings=rng.uniform(2.2,5.5)
        phase=across[rows_here]*rings+.85*warp+rng.uniform(0,1)
        late[rows_here]=(.5+.5*np.sin(math.tau*phase))**3
        ends=np.sort(rng.choice(size,int(rng.integers(1,3)),replace=False))
        board=np.searchsorted(ends,along)%len(ends)
        tone[rows_here]=(.80+.16*rng.random(len(ends)))[board][None,:]
        distance=np.min(np.abs((along[None,:]-ends[:,None]+size//2)%size-size//2),0)*DETAIL_TILE_M/size
        joint[rows_here]=np.exp(-(distance/.0022)**2)[None,:]
    edge=np.minimum(across,1-across)*DETAIL_TILE_M/rows
    gap=np.maximum(np.exp(-(edge/.0030)**2),joint)
    ease=np.exp(-(edge/.008)**2)
    height=late*.00012+shifted*.00007-gap*.0035-ease*.0006
    shade=tone*(1-.20*late+.045*shifted)*(1-.62*gap)
    # Latewood is darker and redder than earlywood.
    colour=np.stack([shade,shade*(1-.07*late),shade*(1-.16*late)],-1)
    return detail_maps(height,colour,.84+.10*(1-late)-.05*shifted+.12*gap)


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


def write_atlases(out,atlases):
    """CITYATL1: block-compressed layer-major mip chains. Channel 0 BC1 sRGB colour, 1 BC5 normal, 2 BC1 linear metal-roughness."""
    import bc
    atlases=atlases or [[Image.new('RGBA',(ATLAS_SIZE,)*2,(255,255,255,255)),Image.new('RGBA',(ATLAS_SIZE,)*2,(128,128,255,255)),
                         Image.new('RGBA',(ATLAS_ORM_SIZE,)*2,(255,255,255,255))]]
    for channel in range(3):
        side=atlases[0][channel].size[0];levels=side.bit_length()
        with (out/f'atlas{channel}.bin').open('wb') as f:
            f.write(struct.pack('<8s4I',b'CITYATL1',side,len(atlases),levels,channel))
            for layer in atlases:
                current=layer[channel]
                for level in range(levels):
                    pixels=np.asarray(current)
                    f.write(bc.bc5(pixels[...,:2]) if channel==1 else bc.bc1(pixels[...,:3]))
                    if level+1<levels:current=mip(current,channel==0)
    return {f'atlas{k}.bin':hashlib.sha256((out/f'atlas{k}.bin').read_bytes()).hexdigest() for k in range(3)}


def prepare(recipe,sources,out,size=1024,overrides=None):
    out.mkdir(parents=True,exist_ok=True);entries=[];mapping={};layers=[];known={};atlases=[]
    # The shared white/flat layer makes procedural materials texture independent.
    layers.append([Image.new('RGBA',(size,size),(255,255,255,255)),Image.new('RGBA',(size,size),(128,128,255,255)),Image.new('RGBA',(size,size),(255,255,255,255))])
    base_names=['ceramic','teal','timber','solar','glazing','bronze','light','stone','leaf','soil','flower','water']
    roles={name:i for i,name in enumerate(base_names)}
    roles.update(room_glass=15,cabin_glass=16,door_glass=17,rubber=18,satin_metal=19,control_screen=20)
    roles.update(service_panel=21,control_panel=22,slatted_timber=23)
    shells=[];surfaces={}
    for asset in recipe['assets']:
        source=Path((overrides or {}).get(asset['id'],sources/asset['id']/'master.glb'))
        doc,blob=load_glb(source);local={}
        def image(info,fallback,side=size):
            if not info:return Image.new('RGBA',(side,side),fallback)
            item=doc['images'][doc['textures'][info['index']]['source']]
            if 'bufferView' not in item:raise ValueError('Production GLB must embed textures')
            view=doc['bufferViews'][item['bufferView']];start=view.get('byteOffset',0)
            return Image.open(io.BytesIO(blob[start:start+view['byteLength']])).convert('RGBA').resize((side,side),Image.Resampling.LANCZOS)
        for j,mat in enumerate(doc.get('materials',[])):
            name=mat.get('name',f'material_{j}');pbr=mat.get('pbrMetallicRoughness',{})
            # Blender adds .001 when a second master is authored in one
            # process. Stable source semantics must survive that display name.
            canonical=mat.get('extras',{}).get('city_material',re.sub(r'\.\d{3}$','',name))
            semantic=roles.get(canonical,100)
            maps=any(k in pbr for k in ['baseColorTexture','metallicRoughnessTexture']) or 'normalTexture' in mat
            surface=asset.get('surface') if canonical=='generated_shell' else None
            if surface:
                # The atlas keeps the draft's colour and normal. Its third map and the colour alpha hold the class masks.
                _,labels,colours=surface_classes.read(source,surface)
                layer=len(layers);packed,extra=surface_classes.masks(labels,size)
                colour=image(pbr.get('baseColorTexture'),(255,255,255,255));colour.putalpha(extra)
                layers.append([colour,image(mat.get('normalTexture'),(128,128,255,255)),packed])
                local[name]=len(entries)
                entries.append({'name':canonical,'color':[surface['mullion_m'],surface['storey_m'],surface['floor_z'],0],
                                'properties':[1,1,0,24],'texture':[layer,mat.get('normalTexture',{}).get('scale',1),0,len(surface_classes.CLASSES)]})
                shells.append((asset['id'],entries[-1],colours,asset.get('interiors',[])))
                covered=labels<surface_classes.UNKNOWN
                surfaces[asset['id']]={kind:round(float((labels==k).sum()/covered.sum()),4) for k,kind in enumerate(surface_classes.CLASSES)}
                continue
            signature=json.dumps({**mat,'name':canonical},sort_keys=True) if not maps else hashlib.sha256(source.read_bytes()).hexdigest()+':'+str(j)
            if signature not in known:
                layer=0
                if maps and canonical=='generated_shell':
                    # A displayed draft atlas goes to the block-compressed arrays: 2048 colour and
                    # normal, 1024 metal-roughness. texture.w = -1 names those arrays.
                    layer=len(atlases)
                    atlases.append([image(pbr.get('baseColorTexture'),(255,255,255,255),ATLAS_SIZE),
                                    image(mat.get('normalTexture'),(128,128,255,255),ATLAS_SIZE),
                                    image(pbr.get('metallicRoughnessTexture'),(255,255,255,255),ATLAS_ORM_SIZE)])
                elif maps:
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
                       'texture':[layer,mat.get('normalTexture',{}).get('scale',1),0,-1 if maps and canonical=='generated_shell' else 0]}
                known[signature]=len(entries);entries.append(entry)
            local[name]=known[signature]
        mapping[asset['id']]=local
    # Masonry dresses step risers: coursed stone drawn in the shader. Crop rows over tilled soil
    # cover the field terraces, drawn in the shader along the terrace.
    for name,color,rough,semantic in [('permeable',[.24,.215,.16,1],.96,12),
                                    ('path_border',[.42,.37,.28,1],.85,13),
                                    ('common_paving',[.48,.45,.36,1],.82,14),
                                    ('masonry',[.35,.32,.27,1],.90,26),
                                    ('crop',[.26,.20,.14,1],.95,27)]:
        layer=len(layers);layers.append(generated_surface({'masonry':'stone','crop':'permeable'}.get(name,name),size))
        entries.append({'name':name,'color':color,'properties':[rough,0,0,semantic],'texture':[layer,1,0,0]})
    # Class materials and their detail tiles follow the kit: existing material slots keep their numbers.
    details={}
    for owner,shell,colours,interiors in shells:
        shell['texture'][2]=len(entries)
        for kind,colour in zip(surface_classes.CLASSES,colours):
            kit=SHELL_KIT[kind];tile,mean=0,1.0
            if 'detail' in kit:
                if kit['detail'] not in details:
                    maps,tone=(shell_plaster if kit['detail']=='shell_plaster' else plank_timber)(size)
                    details[kit['detail']]=(len(layers),tone);layers.append(maps)
                tile,mean=details[kit['detail']]
            # The class keeps the draft's measured colour, bounded as an albedo; the detail tile only modulates it.
            bound=min(1,.80/max(max(colour),1e-6))
            entries.append({'name':owner+':'+kind,'color':[*(c*bound/mean for c in colour),1],
                            'properties':[kit['rough'],kit['metal'],0,kit['role']],
                            'texture':[tile,1,DETAIL_TILE_M,kit['baked']]})
        # Baked rooms follow the classes: the shell names its first record and their count.
        if interiors:
            shell['color'][3]=len(entries);shell['properties'][2]=len(interiors)
            for item in interiors:
                layer=len(layers);layers.append(interior_layer(item,size))
                entries.append({'name':owner+':interior:'+item['name'],'color':[*item['origin'],item['depth']],
                                'properties':[*item['u'],INTERIOR_ROLE],'texture':[layer,*item['v']]})
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
    atlas_hashes=write_atlases(out,atlases)
    report={'materials':entries,'mapping':mapping,'layers':len(layers),'texture_size':size,'mips':levels,
            'atlases':{'layers':len(atlases),'colour_and_normal':ATLAS_SIZE,'metal_roughness':ATLAS_ORM_SIZE,'files':atlas_hashes},
            'generated_surfaces':surfaces,
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
