"""Seconde piste d'arbustes : six architectures climatiques, formes 0 et 1.

python tools/foliage/arbustes_climatiques_v2.py --preview
python tools/foliage/arbustes_climatiques_v2.py --final  # après examen de la planche
"""
import argparse, json, math, shutil, struct
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import bake, volume_assets
from importe import OUT
from arbustes_climatiques import RECTS,FAMILIES,PARAMS,normalize,HEADER

DEST=OUT/'climate_shrubs_v2'
RUNTIME_HEIGHTS=(.65,.85,.60,.30,1.,1.15)


def source_maps(family):
    """Conserve séparément les tuiles bois et feuilles de l'arbuste source."""
    root=OUT/'game_shrub';data=(root/'mesh.bin').read_bytes()
    _,nv,ni,w,h,nm,*_=HEADER.unpack_from(data)
    if nm!=2 or w%2:raise ValueError('Atlas de source inattendu')
    colors=np.frombuffer(data,dtype=np.uint8,offset=HEADER.size+36*nv+4*ni,count=w*h*4).reshape(h,w,4)
    mat=(root/'material.bin').read_bytes();magic,tw,th=struct.unpack_from('<8s2I',mat)
    if magic!=b'FOLMAT01' or (tw,th)!=(w,h):raise ValueError('Matériaux source inattendus')
    normals=np.frombuffer(mat,dtype=np.uint8,offset=16,count=w*h*4).reshape(h,w,4)
    masks=np.frombuffer(mat,dtype=np.uint8,offset=16+w*h*4,count=w*h*4).reshape(h,w,4)
    bark=colors[:,:w//2].copy();bark[:,:,3]=255
    leaves=colors[:,w//2:].copy();rgb=leaves[:,:,:3].astype(np.float32);leaf_rgb=rgb[:420,:575]
    if family in ('desert','steppe'):
        grey=(leaf_rgb*np.array([.2126,.7152,.0722],np.float32)).sum(axis=2,keepdims=True)
        leaf_rgb[:]=leaf_rgb*.42+grey*.58
    leaf_rgb*=np.asarray(PARAMS[family][6],np.float32);leaves[:,:,:3]=np.clip(rgb,0,255).astype(np.uint8)
    bark_mask=masks[:,:w//2].copy();bark_mask[:,:,2]=0
    leaf_mask=masks[:,w//2:].copy();leaf_mask[:,:,2]=255
    def pair(a,b):
        im=Image.new('RGBA',(1024,512))
        for x,src in ((0,a),(512,b)):
            im.paste(Image.fromarray(src).resize((512,512),Image.Resampling.LANCZOS),(x,0))
        return im.tobytes()
    return pair(bark,leaves),pair(normals[:,:w//2],normals[:,w//2:]),pair(bark_mask,leaf_mask)


def create(family,variant):
    rng=np.random.default_rng(428009+FAMILIES.index(family)*701+variant*113)
    vv=[];ii=[]
    def vertex(p,n,uv,m):vv.append([*p,*n,*uv,m]);return len(vv)-1
    def tube(a,b,r0,r1):
        direction=normalize(b-a);helper=np.array([0.,1.,0.]) if abs(direction[1])<.9 else np.array([1.,0.,0.])
        side=normalize(np.cross(direction,helper));other=normalize(np.cross(direction,side));base=len(vv);N=4
        for p,r,v in ((a,r0,.15),(b,r1,.88)):
            for j in range(N):
                angle=2*math.pi*j/N;n=side*math.cos(angle)+other*math.sin(angle)
                vertex(p+r*n,n,(.65+.30*j/(N-1),v),0)
        for j in range(N):
            k=(j+1)%N;ii.extend((base+j,base+k,base+N+k,base+j,base+N+k,base+N+j))
    def card(base,forward,width,length,angle,rect,subdiv=1):
        axis=normalize(forward);helper=np.array([0.,1.,0.]) if abs(axis[1])<.9 else np.array([1.,0.,0.])
        s=normalize(np.cross(axis,helper));t=normalize(np.cross(axis,s));side=normalize(s*math.cos(angle)+t*math.sin(angle));n=normalize(np.cross(side,axis))
        x0,y0,x1,y1=rect;start=len(vv)
        for row in range(subdiv+1):
            along=row/subdiv
            for col in range(subdiv+1):
                across=col/subdiv*2-1
                # Courbure légère de la feuille sur les grands limbes tropicaux.
                blade=base+axis*(length*along)+side*(across*width*.5)+n*(width*.12*(1-across*across)*math.sin(math.pi*along))
                uv=((x0+(x1-x0)*col/subdiv)/1024,(y1-(y1-y0)*along)/1024)
                vertex(blade,n,uv,1)
        for row in range(subdiv):
            for col in range(subdiv):
                a=start+row*(subdiv+1)+col;b=a+1;c=a+subdiv+1;d=c+1;ii.extend((a,b,d,a,d,c))
    def foliage(a,b,slots,density,width,length,terminal=False):
        direction=normalize(b-a)
        for j in range(slots):
            u=(.56+.40*(j+.3)/slots) if terminal else (.07+.9*(j+.3)/slots)
            point=a*(1-u)+b*u
            for q in range(density):
                angle=q*2.399963+rng.uniform(-.35,.35)
                lateral=np.array([math.cos(angle),rng.uniform(-.12,.55),math.sin(angle)])
                f=normalize(direction*.30+lateral*.76+np.array([0.,.12,0.]))
                card(point,f,width*rng.uniform(.75,1.3),length*rng.uniform(.8,1.25),rng.uniform(-3,3),RECTS[int(rng.integers(len(RECTS)))])
    def vec(a,r,y):return np.array([math.cos(a)*r,y,math.sin(a)*r])
    if family=='tropical':
        # Tiges séparées et feuilles alternes : grandes lames subdivisées, pas de petits bouquets.
        stems=4+variant
        for k in range(stems):
            phi=2*math.pi*k/stems+rng.uniform(-.2,.2)
            root=vec(phi,.11+rng.uniform(0,.04),0.);drift=vec(phi,rng.uniform(.05,.22),0.)
            heights=np.linspace(0,rng.uniform(.75,1.1),10)
            for j in range(9):
                a=root+drift*(j/9)+np.array([0,heights[j],0]);b=root+drift*((j+1)/9)+np.array([0,heights[j+1],0]);tube(a,b,.014*(1-j*.07),.013*(1-j*.07))
                for q in range(2):
                    theta=phi+j*2.4+q*math.pi+rng.uniform(-.2,.2)
                    f=normalize(vec(theta,1.,rng.uniform(.15,.52)))
                    card(b,f,rng.uniform(.18,.27),rng.uniform(.31,.43),rng.uniform(-.6,.6),RECTS[int(rng.integers(len(RECTS)))],4)
    else:
        if family=='boreal':count=9+variant*3;slots=5;density=5;width=.055;length=.105
        elif family=='desert':count=7+variant*2;slots=5;density=6;width=.032;length=.086
        elif family=='steppe':count=15+variant*2;slots=5;density=5;width=.035;length=.090
        elif family=='montane':count=15+variant*2;slots=5;density=5;width=.050;length=.103
        else:count=10+variant*2;slots=5;density=6;width=.060;length=.120
        phase=rng.uniform(0,6.28)
        # Plusieurs racines décalées évitent le pied unique de la première piste.
        for k in range(count):
            theta=phase+2*math.pi*k/count+rng.uniform(-.24,.24)
            if family=='desert':
                origin=vec(theta,.04+rng.uniform(0,.08),0.)+np.array([.09*variant,0.,-.04*variant]); reach=rng.uniform(.38,.75);height=rng.uniform(.50,.90)
                mid=origin+vec(theta,reach*.32,height*.22);tip=origin+vec(theta,reach,height)
            elif family=='steppe':
                origin=vec(theta,rng.uniform(.08,.26),0.);reach=rng.uniform(.25,.70);height=rng.uniform(.18,.48)
                if k%6==variant:height=rng.uniform(.65,.9);reach*=.35
                mid=origin+vec(theta,reach*.48,height*.32);tip=origin+vec(theta,reach,height)
            elif family=='montane':
                origin=vec(theta,rng.uniform(.05,.19),0.);reach=rng.uniform(.40,.75);height=rng.uniform(.14,.30)
                mid=origin+vec(theta,reach*.5,height*.45);tip=origin+vec(theta,reach,height)
            elif family=='boreal':
                origin=vec(theta,rng.uniform(.05,.19),0.);reach=rng.uniform(.10,.42);height=rng.uniform(.55,1.0)
                mid=origin+vec(theta,reach*.44,height*.45);tip=origin+vec(theta,reach,height)
            else:
                # Larges touffes asymétriques avec trois centres feuillus excentrés.
                lobe=k%3;phi=phase+2*math.pi*lobe/3+(variant*.31);origin=vec(phi,rng.uniform(.06,.16),0.)
                reach=rng.uniform(.15,.40);height=rng.uniform(.53,1.05);theta=phi+rng.uniform(-.55,.55)
                mid=origin+vec(theta,reach*.48,height*.48);tip=origin+vec(theta,reach,height)
            tube(origin,mid,.012,.008);tube(mid,tip,.008,.003)
            childcount=3 if family in ('steppe','montane') else 5
            for j in range(childcount):
                u=(j+.7)/(childcount+1);joint=origin*(1-2*u)+mid*(2*u) if u<.5 else mid*(2-2*u)+tip*(2*u-1)
                phi=theta+(-1 if j%2 else 1)*rng.uniform(.50,1.55)
                if family=='montane':d=normalize(vec(phi,1.,rng.uniform(.02,.18)));extent=rng.uniform(.18,.32)
                elif family=='steppe':d=normalize(vec(phi,1.,rng.uniform(.12,.40)));extent=rng.uniform(.12,.27)
                elif family=='desert':d=normalize(vec(phi,1.,rng.uniform(.12,.48)));extent=rng.uniform(.18,.36)
                else:d=normalize(vec(phi,1.,rng.uniform(.35,.9)));extent=rng.uniform(.14,.28)
                end=joint+d*extent;tube(joint,end,.0045,.0016)
                foliage(joint,end,slots,density,width,length,terminal=(family=='desert'))
            if family=='boreal':foliage(origin,mid,3,4,width,length)
    v=np.asarray(vv,dtype='<f4');inds=np.asarray(ii,dtype='<u4');lo=v[:,:3].min(axis=0);hi=v[:,:3].max(axis=0);height=hi[1]-lo[1]
    off=np.array([(lo[0]+hi[0])/2,lo[1],(lo[2]+hi[2])/2]);v[:,:3]=(v[:,:3]-off)/height;lo=(lo-off)/height;hi=(hi-off)/height
    count=len(inds)//3
    if not 2000<=count<=5000:raise ValueError(f'{family} {variant}: {count} triangles hors budget')
    name=f'shrub_{family}_{variant}';dst=DEST/name;dst.mkdir(parents=True,exist_ok=True);color,norm,mask=source_maps(family)
    with (dst/'mesh.bin').open('wb') as f:f.write(HEADER.pack(b'FOLMESH1',len(v),len(inds),1024,512,2,*lo,*hi));f.write(v.tobytes());f.write(inds.tobytes());f.write(color)
    with (dst/'material.bin').open('wb') as f:f.write(struct.pack('<8s2I',b'FOLMAT01',1024,512));f.write(norm);f.write(mask)
    print(name,'tris',count,'verts',len(v),flush=True)


def preview():
    DEST.mkdir(parents=True,exist_ok=True);bake.OUT=DEST
    sheets=[Image.new('RGB',(6*256,2*300),(225,225,225)) for _ in range(2)]
    draws=[ImageDraw.Draw(sheet) for sheet in sheets];font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    for col,fam in enumerate(FAMILIES):
        for variant in (0,1):
            create(fam,variant);name=f'shrub_{fam}_{variant}';v,i,a,lo,hi,n=bake.load(name)
            radius=np.linalg.norm(np.maximum(abs(lo-np.array([0,.5,0])),abs(hi-np.array([0,.5,0]))))
            color,_=bake.bake_views(v,i,a,radius,12,5,128,n)
            for sheet,draw,view in zip(sheets,draws,(0,3)):
                im=Image.fromarray(color[view]).resize((256,256),Image.Resampling.NEAREST)
                sheet.paste(im,(col*256,variant*300+28),im);draw.text((col*256+5,variant*300+4),name,fill=(0,0,0),font=font)
    sheets[0].save(DEST/'contact_cpu.png');sheets[1].save(DEST/'contact_cpu_cote.png')
    print('Planches:',DEST/'contact_cpu.png',DEST/'contact_cpu_cote.png',flush=True)


def runtime_preview():
    """Projection CPU à la même taille d'instance et allométrie que Scale()."""
    bake.OUT=DEST
    sheet=Image.new('RGB',(6*256,4*300),(225,225,225));draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
    sun=normalize(np.array([.35,.85,.40]))
    for col,(family,height) in enumerate(zip(FAMILIES,RUNTIME_HEIGHTS)):
        for variant in (0,1):
            name=f'shrub_{family}_{variant}';v,i,a,lo,hi,n=bake.load(name)
            width=max(hi[0]-lo[0],hi[2]-lo[2])
            scale=np.array([1.1/width,height,1.1/width])
            v=v.copy();v[:,:3]*=scale
            normal=v[:,3:6]/scale;v[:,3:6]=normal/np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12)
            color,nd=bake.bake_views(v,i,a,1.05,12,5,128,n)
            for viewrow,view in enumerate((0,3)):
                row=variant*2+viewrow
                light=.55+.45*np.maximum(0,np.sum(nd[view,:,:,:3]*sun,axis=2))
                rgba=color[view].copy();rgba[:,:,:3]=np.clip(rgba[:,:,:3]*light[:,:,None],0,255).astype('u1')
                im=Image.fromarray(rgba).resize((256,256),Image.Resampling.NEAREST)
                sheet.paste(im,(col*256,row*300+28),im)
                draw.text((col*256+4,row*300+4),f'{name} h={height:g} vue={viewrow}',font=font,fill=(0,0,0))
    sheet.save(DEST/'contact_runtime_cpu.png')
    print('Planche allométrique :',DEST/'contact_runtime_cpu.png',flush=True)


def final():
    if not (DEST/'contact_cpu.png').exists():raise ValueError('Planche absente')
    bake.OUT=DEST;volume_assets.DEST=DEST
    for name in ('game_fir','game_broadleaf'):
        src=OUT/'volume_look_normals'/name;dst=DEST/name;dst.mkdir(parents=True,exist_ok=True)
        for p in src.glob('*.bin'):shutil.copyfile(p,dst/p.name)
    for family in FAMILIES:
        for variant in (0,1):
            name=f'shrub_{family}_{variant}';volume_assets.SPEC[name]={'leaf':1};v,i,a,lo,hi,n=bake.load(name)
            bake.volume(name,v,i,a,lo,hi,n,64);bake.impostor(name,v,i,a,lo,hi,n);volume_assets.bake_light(name)
    (DEST/'shrubs.txt').write_text('FOLSHR01 6 2\n'+''.join(f'shrub_{f}_{v}\n' for f in FAMILIES for v in (0,1)),encoding='ascii')
    (DEST/'metadata.json').write_text(json.dumps({'date':'2026-10-27','source':'https://polyhaven.com/a/searsia_lucida','license':'CC0-1.0','generation':'six architectures climatiques distinctes','climates':FAMILIES,'runtime_height_factors':dict(zip(FAMILIES,RUNTIME_HEIGHTS)),'runtime_max_width_factor':1.1},ensure_ascii=False,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--preview',action='store_true');g.add_argument('--runtime-preview',action='store_true');g.add_argument('--final',action='store_true');a=p.parse_args()
    if a.preview:preview()
    elif a.runtime_preview:runtime_preview()
    else:final()
