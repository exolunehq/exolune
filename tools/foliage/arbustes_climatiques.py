"""Construit douze archétypes d'arbustes et leurs données CPU.

python tools/foliage/arbustes_climatiques.py --preview
python tools/foliage/arbustes_climatiques.py --final
Les feuilles et textures proviennent de game_shrub (Searsia Lucida, CC0).
"""
from pathlib import Path
import argparse, json, math, shutil, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import bake, volume_assets
from importe import OUT

DEST=OUT/'climate_shrubs'; CACHE=OUT/'cache'; HEADER=struct.Struct('<8s5I6f')
FAMILIES=['boreal','desert','steppe','montane','temperate','tropical']
# Stems, branch spread, secondary length, leaf width, leaf length, density, RGB tint.
PARAMS={
 'boreal':    (9, .44, .24, .054, .105, 7, (.87,.94,.79)),
 'desert':    (8, .54, .31, .034, .090, 6, (.86,.91,.80)),
 'steppe':    (10,.68, .28, .035, .092, 7, (.86,.93,.83)),
 'montane':   (11,.72, .29, .050, .105, 7, (.76,.90,.70)),
 'temperate': (10,.50, .26, .060, .125, 7, (.82,.96,.73)),
 'tropical':  (9, .49, .25, .115, .175, 7, (.68,.87,.64)),
}


def normalize(v):
    l=np.linalg.norm(v);return v/l if l>1e-10 else np.array([0.,1.,0.])


def source_maps(family):
    root=OUT/'game_shrub'
    data=(root/'mesh.bin').read_bytes(); _,nv,ni,w,h,nm,*_=HEADER.unpack_from(data)
    color=np.frombuffer(data,dtype=np.uint8,offset=HEADER.size+36*nv+4*ni,count=w*h*4).reshape(h,w,4)[:,w//2:,:].copy()
    mat=(root/'material.bin').read_bytes();m,tw,th=struct.unpack_from('<8s2I',mat)
    assert m==b'FOLMAT01' and (tw,th)==(w,h)
    norm=np.frombuffer(mat,dtype=np.uint8,offset=16,count=w*h*4).reshape(h,w,4)[:,w//2:,:].copy()
    mask=np.frombuffer(mat,dtype=np.uint8,offset=16+w*h*4,count=w*h*4).reshape(h,w,4)[:,w//2:,:].copy()
    rgb=color[:,:,:3].astype(np.float32); tint=np.asarray(PARAMS[family][6],np.float32)
    # Teinte dans les seules zones feuillues. Bois partagé non recoloré.
    leaf_rgb=rgb[:420,:575]
    if family in ('desert','steppe'):
        grey=(leaf_rgb*np.array([.2126,.7152,.0722],np.float32)).sum(axis=2,keepdims=True)
        leaf_rgb[:]=leaf_rgb*.42+grey*.58
    leaf_rgb*=tint; color[:,:,:3]=np.clip(rgb,0,255).astype(np.uint8)
    leaves=Image.fromarray(color).resize((512,512),Image.Resampling.LANCZOS)
    bark=color.copy();bark[:,:,3]=255;bark=Image.fromarray(bark).resize((512,512),Image.Resampling.LANCZOS)
    n=Image.fromarray(norm).resize((512,512),Image.Resampling.LANCZOS)
    m0=mask.copy();m0[:,:,2]=0;m1=mask.copy();m1[:,:,2]=255
    ms=[Image.fromarray(m).resize((512,512),Image.Resampling.LANCZOS) for m in (m0,m1)]
    def pair(a,b):
        im=Image.new('RGBA',(1024,512));im.paste(a,(0,0));im.paste(b,(512,0));return im.tobytes()
    return pair(bark,leaves),pair(n,n),pair(*ms)


# Rectangles des sept feuilles alpha isolées de l'atlas original, marge incluse.
RECTS=[(31,211,178,399),(184,237,332,406),(371,233,512,388),
       (283,138,455,247),(54,77,195,218),(515,27,601,207),(226,73,342,174)]


def create(family,variant):
    rng=np.random.default_rng(270100+FAMILIES.index(family)*101+variant*29)
    stems,spread,child_len,leafw,leafl,density,_=PARAMS[family]
    # Des structures différentes : port éventail ou central élancé ; nombres de rameaux différents.
    stems += 2 if variant else 0
    vv=[];ii=[];branches=[];leaves=[]
    def vertex(p,n,uv,mat):vv.append([*p,*n,*uv,mat]);return len(vv)-1
    def cylinder(a,b,r0,r1):
        direction=normalize(b-a); helper=np.array([0.,1.,0.]) if abs(direction[1])<.9 else np.array([1.,0.,0.])
        side=normalize(np.cross(direction,helper));other=normalize(np.cross(direction,side));base=len(vv);ns=4
        for p,r,v in [(a,r0,.15),(b,r1,.88)]:
            for j in range(ns):
                angle=2*math.pi*j/ns; n=side*math.cos(angle)+other*math.sin(angle)
                vertex(p+n*r,n,(.65+.30*j/(ns-1),v),0)
        for j in range(ns):
            k=(j+1)%ns;ii.extend((base+j,base+k,base+ns+k,base+j,base+ns+k,base+ns+j))
    def card(base,forward,width,length,angle,rect):
        axis=normalize(forward);helper=np.array([0.,1.,0.]) if abs(axis[1])<.9 else np.array([1.,0.,0.])
        s=normalize(np.cross(axis,helper));t=normalize(np.cross(axis,s));side=normalize(s*math.cos(angle)+t*math.sin(angle))
        n=normalize(np.cross(side,axis));tip=base+axis*length
        # Feuilles unies au rameau par leur base ; normales légèrement bombées.
        points=[base-side*width*.17,base+side*width*.17,tip+side*width*.38,tip-side*width*.38]
        x0,y0,x1,y1=rect; uv=[(x0/1024,y1/1024),(x1/1024,y1/1024),(x1/1024,y0/1024),(x0/1024,y0/1024)]
        ids=[vertex(p,n,u,1) for p,u in zip(points,uv)];ii.extend((ids[0],ids[1],ids[2],ids[0],ids[2],ids[3]))
    phase=rng.uniform(0,6.28)
    for k in range(stems):
        a=phase+2*math.pi*k/stems+rng.uniform(-.18,.18)
        radial=np.array([math.cos(a),0.,math.sin(a)])
        skew=1.2 if variant and k%3==0 else 1.
        sideways=radial*spread*skew*rng.uniform(.75,1.05)
        if family=='montane':sideways*=1.35
        if family=='steppe':sideways*=1.2
        height=rng.uniform(.70,1.08) if variant else rng.uniform(.76,1.0)
        footprint=.08 if family in ('steppe','montane') else .055
        base=np.array([rng.uniform(-footprint,footprint),0.,rng.uniform(-footprint,footprint)])
        if family=='montane':mid_fraction=.20;tip_fraction=.65
        elif family=='steppe':mid_fraction=.28;tip_fraction=.78
        elif family=='tropical':mid_fraction=.28;tip_fraction=1.00
        else:mid_fraction=.42;tip_fraction=1.00
        mid=base+sideways*.42+np.array([0.,height*mid_fraction,0.]); tip=base+sideways+np.array([0.,height*tip_fraction,0.])
        cylinder(base,mid,.018,.012);cylinder(mid,tip,.012,.005)
        branches.extend((base,mid,mid,tip))
        for j in range(5):
            t=.12+j*.19+rng.uniform(-.025,.025)
            joint=base*(1-2*t)+mid*(2*t) if t<.5 else mid*(2-2*t)+tip*(2*t-1)
            turn=a+(-1 if j%2 else 1)*rng.uniform(.6,1.35)
            direction=normalize(np.array([math.cos(turn)*rng.uniform(.4,.85),rng.uniform(.35,.85),math.sin(turn)*rng.uniform(.4,.85)]))
            if family in ('steppe','montane'):direction=normalize(direction+radial*.45)
            length=child_len*rng.uniform(.8,1.3);end=joint+direction*length
            cylinder(joint,end,.006,.0022)
            # Trois feuilles par point réparties dans des plans obliques.
            for z in range(4):
                origin=joint+(end-joint)*(0.18+z*.23)
                for q in range(density):
                    az=2*math.pi*q/density+rng.uniform(-.35,.35)
                    lateral=np.array([math.cos(az),rng.uniform(.05,.35),math.sin(az)])
                    forward=normalize(direction*.35+lateral*.7+np.array([0.,.16,0.]))
                    w=leafw*rng.uniform(.8,1.25);ln=leafl*rng.uniform(.8,1.25)
                    card(origin,forward,w,ln,rng.uniform(0,6.28),RECTS[int(rng.integers(len(RECTS)))])
    v=np.asarray(vv,dtype='<f4');idx=np.asarray(ii,dtype='<u4')
    lo=v[:,:3].min(axis=0);hi=v[:,:3].max(axis=0);height=hi[1]-lo[1];offset=np.array([(hi[0]+lo[0])/2,lo[1],(hi[2]+lo[2])/2]);v[:,:3]=(v[:,:3]-offset)/height;lo=(lo-offset)/height;hi=(hi-offset)/height
    if idx.size//3>5000 or idx.size//3<2000:raise ValueError('budget inattendu '+str(idx.size//3))
    name=f'shrub_{family}_{variant}';folder=DEST/name;folder.mkdir(parents=True,exist_ok=True)
    color,norm,mask=source_maps(family)
    with (folder/'mesh.bin').open('wb') as f:f.write(HEADER.pack(b'FOLMESH1',len(v),len(idx),1024,512,2,*lo,*hi));f.write(v.tobytes());f.write(idx.tobytes());f.write(color)
    with (folder/'material.bin').open('wb') as f:f.write(struct.pack('<8s2I',b'FOLMAT01',1024,512));f.write(norm);f.write(mask)
    print(name,'triangles',len(idx)//3,'sommets',len(v),flush=True)


def preview():
    DEST.mkdir(parents=True,exist_ok=True)
    bake.OUT=DEST; sheet=Image.new('RGB',(6*256,2*300),(225,225,225));draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    for col,family in enumerate(FAMILIES):
        for variant in (0,1):
            create(family,variant);name=f'shrub_{family}_{variant}'
            v,i,a,lo,hi,n=bake.load(name);radius=np.linalg.norm(np.maximum(abs(lo-np.array([0,.5,0])),abs(hi-np.array([0,.5,0]))))
            color,nd=bake.bake_views(v,i,a,radius,12,5,128,n)
            im=Image.fromarray(color[0]).resize((256,256),Image.Resampling.NEAREST)
            sheet.paste(im,(col*256,variant*300+28),im);draw.text((col*256+5,variant*300+4),name,fill=(0,0,0),font=font)
    sheet.save(DEST/'contact_cpu.png');print('Planche CPU créée :',DEST/'contact_cpu.png',flush=True)


def final():
    if not (DEST/'contact_cpu.png').exists():raise ValueError('Lancer et inspecter --preview avant --final')
    bake.OUT=DEST;volume_assets.DEST=DEST
    for name in ('game_fir','game_broadleaf'):
        src=OUT/'volume_look_normals'/name;dst=DEST/name;dst.mkdir(parents=True,exist_ok=True)
        for p in src.glob('*.bin'):shutil.copyfile(p,dst/p.name)
    for family in FAMILIES:
        for variant in (0,1):
            name=f'shrub_{family}_{variant}';volume_assets.SPEC[name]={'leaf':1}
            v,i,a,lo,hi,n=bake.load(name)
            bake.volume(name,v,i,a,lo,hi,n,64);bake.impostor(name,v,i,a,lo,hi,n);volume_assets.bake_light(name)
    (DEST/'shrubs.txt').write_text('FOLSHR01 6 2\n'+''.join(f'shrub_{f}_{v}\n' for f in FAMILIES for v in (0,1)),encoding='ascii')
    (DEST/'metadata.json').write_text(json.dumps({'date':'2026-10-27','source':'https://polyhaven.com/a/searsia_lucida','license':'CC0-1.0','seed_base':270100,'variants':'génération indépendante de branches et de cartes','atlas':'2 matériaux de 512×512','leaf_mask':'0 branches, 1 feuilles','climates':FAMILIES},indent=2,ensure_ascii=False)+'\n',encoding='utf8')

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--preview',action='store_true');g.add_argument('--final',action='store_true');args=p.parse_args()
    if args.preview:preview()
    else:final()
