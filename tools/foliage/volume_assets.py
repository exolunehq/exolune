"""Variantes de feuillage et pré-calcul d'éclairage, sans modifier les sources.

Exécuter depuis la racine : python tools/foliage/volume_assets.py
Pré-requis : assets/foliage/game_{fir,broadleaf,shrub} et numpy, numba, Pillow.
"""
from pathlib import Path
import argparse, json, math, shutil, struct, time
import numpy as np
from numba import njit, prange
import bake
from importe import OUT

DEST = OUT/'volume_look'
HEADER=struct.Struct('<8s5I6f')
SPEC={'game_broadleaf':{'leaf':0,'copies':3},'game_shrub':{'leaf':1,'copies':3}}


def components(tris):
    """Ensembles connexes de triangles conservant chacun la même surface d'origine."""
    parent={}
    def find(x):
        parent.setdefault(x,x)
        if parent[x]!=x: parent[x]=find(parent[x])
        return parent[x]
    for a,b,c in tris:
        a,b,c=int(a),int(b),int(c);ra,rb,rc=find(a),find(b),find(c);parent[rb]=ra;parent[rc]=ra
    groups={}
    for tri in tris:groups.setdefault(find(int(tri[0])),[]).append(tri)
    return list(groups.values())


def make_mesh(name):
    src=OUT/name/'mesh.bin';data=src.read_bytes()
    magic,nv,ni,w,h,nmat,*bound=HEADER.unpack_from(data)
    if magic!=b'FOLMESH1':raise ValueError('Maillage source invalide')
    verts=np.frombuffer(data,dtype='<f4',count=nv*9,offset=HEADER.size).reshape(-1,9).copy()
    idx=np.frombuffer(data,dtype='<u4',count=ni,offset=HEADER.size+nv*36).reshape(-1,3).copy()
    atlas=data[HEADER.size+nv*36+ni*4:];lo=np.array(bound[:3]);hi=np.array(bound[3:])
    cfg=SPEC[name]
    if name=='game_shrub':
        # Import source : tronc, feuilles, puis brindilles. Ne dupliquer que les feuilles.
        first=4471; last=first+2064
        selected=idx[first:last]
        woody=idx[:first]
        if len(selected)!=2064 or not np.all(verts[selected,8]==1):raise ValueError('Ordre de source arbuste inattendu')
    else:
        selected=idx[verts[idx[:,0],8]==cfg['leaf']]
        woody=idx[verts[idx[:,0],8]!=cfg['leaf']]
    wood_points=verts[np.unique(woody),:3]
    groups=components(selected); rng=np.random.default_rng(20261027)
    extra_v=[];extra_i=[];total=nv
    for group in groups:
        group=np.asarray(group,dtype=np.uint32); old,local=np.unique(group,return_inverse=True);local=local.reshape(-1,3)
        source=verts[old].copy()
        # Point de branche le plus proche : copies disposées autour du rameau porteur.
        center=source[:,:3].mean(axis=0)
        pivot=wood_points[np.argmin(((wood_points-center)**2).sum(axis=1))].astype(float)
        for c in range(cfg['copies']):
            yaw=(c-(cfg['copies']-1)/2)*1.25 + rng.uniform(-0.18,0.18)
            if abs(yaw)<0.15:yaw += 0.45
            tilt=rng.uniform(-0.22,0.22)
            def transform(f):
                a=yaw*f;b=tilt*f;ca,sa=math.cos(a),math.sin(a);cb,sb=math.cos(b),math.sin(b)
                rot=np.array([[ca,sa*sb,sa*cb],[0,cb,-sb],[-sa,ca*sb,ca*cb]])
                q=source.copy();q[:,:3]=(source[:,:3]-pivot)@rot.T+pivot;q[:,3:6]=source[:,3:6]@rot.T
                return q
            # Les limites contractuelles et les pivots sont inchangés.
            chosen=None
            for fraction in (1.,0.75,0.5,0.25):
                q=transform(fraction)
                if np.all(q[:,:3]>=lo-1e-6) and np.all(q[:,:3]<=hi+1e-6):chosen=q;break
            if chosen is None: continue
            extra_v.append(chosen);extra_i.append(local.astype('<u4')+total);total+=len(q)
    allv=np.concatenate([verts]+extra_v).astype('<f4'); alli=np.concatenate([idx]+extra_i).astype('<u4')
    dst=DEST/name;dst.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(OUT/name/'material.bin',dst/'material.bin')
    with (dst/'mesh.bin').open('wb') as f:
        f.write(HEADER.pack(magic,len(allv),alli.size,w,h,nmat,*bound));f.write(allv.tobytes());f.write(alli.tobytes());f.write(atlas)
    print(name,'composants',len(groups),'triangles',len(idx),'->',len(alli),'sommets',len(allv),flush=True)


@njit(parallel=True)
def visibility(verts, vox, lo, hi, dirs):
    """Marches en repère voxels ; deux cellules sautées pour l'auto-occlusion."""
    n=len(verts); out=np.empty((n,len(dirs)),np.float32)
    for v in prange(n):
        xyz=(verts[v,:3]-lo)/(hi-lo)*64
        for d in range(len(dirs)):
            # Les directions sont en repère local ; la grille peut être anisotrope.
            dx=dirs[d,0]/(hi[0]-lo[0]);dy=dirs[d,1]/(hi[1]-lo[1]);dz=dirs[d,2]/(hi[2]-lo[2])
            norm=math.sqrt(dx*dx+dy*dy+dz*dz);dx/=norm;dy/=norm;dz/=norm
            x=xyz[0]+dx*2.25;y=xyz[1]+dy*2.25;z=xyz[2]+dz*2.25;opt=0.
            for s in range(111):
                ix,iy,iz=int(math.floor(x)),int(math.floor(y)),int(math.floor(z))
                if ix<0 or iy<0 or iz<0 or ix>=64 or iy>=64 or iz>=64:break
                a=max(0.,min(0.95,vox[iz,iy,ix]))
                opt += -math.log(1-a)*0.42
                x+=dx;y+=dy;z+=dz
            out[v,d]=math.exp(-opt)
    return out


def bake_light(name):
    folder=DEST/name;verts,idx,atlas,lo,hi,materials=bake.load(name)
    with (folder/'volume64.bin').open('rb') as f:
        magic,n,levels,*b=struct.unpack('<8s2I6f',f.read(40))
        if magic!=b'FOLVOL01' or n!=64:raise ValueError('volume invalide')
        vox=np.frombuffer(f.read(64**3*32),dtype='<f4').reshape(64,64,64,8)[:,:,:,0].copy()
    directions=[[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]]
    # 16 directions à poids égal sur l'hémisphère supérieur.
    for i in range(16):
        y=(i+0.5)/16;r=math.sqrt(1-y*y);a=i*math.pi*(3-math.sqrt(5));directions.append([r*math.cos(a),y,r*math.sin(a)])
    rays=visibility(verts,vox,lo,hi,np.asarray(directions,dtype=np.float64))
    light=np.empty((len(verts),8),'<f4')
    light[:,0]=0.30+0.70*rays[:,6:].mean(axis=1)
    light[:,1:7]=0.20+0.80*rays[:,:6]
    light[:,7]=(verts[:,8]==SPEC[name]['leaf']).astype(np.float32)
    if name=='game_shrub':
        # Les brindilles d'origine sont en alpha mais restent des branches.
        twig_start=(4471+2064)*3; twig_end=(4471+2064+697)*3
        light[np.unique(idx[twig_start:twig_end]),7]=0.0
    with (folder/'lighting.bin').open('wb') as f:
        f.write(struct.pack('<8s2I',b'FOLLIT01',len(verts),8));f.write(light.tobytes())
    with (folder/'impostor.bin').open('rb') as f:
        _,az,el,w,h,*rest=struct.unpack('<8s4I7f',f.read(52))
    radius=rest[-1]
    images,coverage=bake_light_views(verts,idx,atlas,light,radius,az,el,256,materials)
    images=images.reshape(az*el,128,2,128,2,8);weights=coverage.reshape(az*el,128,2,128,2)
    cov=weights.sum(axis=(2,4));planes=[]
    for first in (0,4):
        vals=(images[...,first:first+4]*weights[...,None]).sum(axis=(2,4))/np.maximum(cov[...,None],1)
        planes.append(np.rint(np.clip(vals,0,1)*255).astype(np.uint8))
    with (folder/'impostor_light.bin').open('wb') as f:
        f.write(struct.pack('<8s4I',b'FOLIL001',az,el,w,h))
        for plane in planes:f.write(plane.tobytes())
    print(name,'lighting ready', 'sky',float(light[:,0].min()),float(light[:,0].mean()),flush=True)


@njit(parallel=True)
def bake_light_views(verts,indices,atlas,light,radius,azimuths,elevations,size,material_count):
    views=azimuths*elevations
    out=np.zeros((views,size,size,8),np.float32)
    cov=np.zeros((views,size,size),np.uint8)
    depth=np.full((views,size,size),-1e10,np.float32)
    for view in prange(views):
        az=2*math.pi*(view%azimuths)/azimuths;el=0.5*math.pi*(view//azimuths)/(elevations-1)
        st,ct,sp,cp=math.sin(az),math.cos(az),math.sin(el),math.cos(el)
        camera=np.array((st*cp,sp,ct*cp));right=np.array((ct,0.,-st));up=np.array((-st*sp,cp,-ct*sp))
        projected=np.empty((len(verts),3),np.float32)
        for i in range(len(verts)):
            px,py,pz=verts[i,0],verts[i,1]-0.5,verts[i,2]
            projected[i,0]=((px*right[0]+py*right[1]+pz*right[2])/radius*0.5+0.5)*size
            projected[i,1]=(0.5-(px*up[0]+py*up[1]+pz*up[2])/radius*0.5)*size
            projected[i,2]=px*camera[0]+py*camera[1]+pz*camera[2]
        for t in range(len(indices)//3):
            i,j,k=indices[3*t],indices[3*t+1],indices[3*t+2]
            a,b,c=projected[i],projected[j],projected[k]
            det=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
            if abs(det)<1e-12:continue
            xmin=max(0,int(math.ceil(min(a[0],b[0],c[0])-0.5)));xmax=min(size-1,int(math.floor(max(a[0],b[0],c[0])-0.5)))
            ymin=max(0,int(math.ceil(min(a[1],b[1],c[1])-0.5)));ymax=min(size-1,int(math.floor(max(a[1],b[1],c[1])-0.5)))
            for y in range(ymin,ymax+1):
                for x in range(xmin,xmax+1):
                    dx=x+0.5-a[0];dy=y+0.5-a[1]
                    wb=(dx*(c[1]-a[1])-dy*(c[0]-a[0]))/det;wc=((b[0]-a[0])*dy-(b[1]-a[1])*dx)/det;wa=1-wb-wc
                    if min(wa,wb,wc)<0:continue
                    z=a[2]*wa+b[2]*wb+c[2]*wc
                    if z<=depth[view,y,x]:continue
                    u=verts[i,6]*wa+verts[j,6]*wb+verts[k,6]*wc;v=verts[i,7]*wa+verts[j,7]*wb+verts[k,7]*wc
                    if bake.texel(atlas,u,v,verts[i,8],material_count)[3]<128:continue
                    depth[view,y,x]=z;cov[view,y,x]=1
                    for q in range(8):out[view,y,x,q]=light[i,q]*wa+light[j,q]*wb+light[k,q]*wc
    return out,cov


def main():
    DEST.mkdir(parents=True,exist_ok=True)
    for name in ['game_fir']:
        target=DEST/name;target.mkdir(exist_ok=True)
        for file in ['mesh.bin','material.bin','volume.bin','volume64.bin','impostor.bin']:
            shutil.copyfile(OUT/name/file,target/file)
    for name in SPEC:make_mesh(name)
    bake.OUT=DEST
    for name in SPEC:
        t=time.time();v,i,atlas,lo,hi,n=bake.load(name)
        bake.volume(name,v,i,atlas,lo,hi,n,64);bake.impostor(name,v,i,atlas,lo,hi,n)
        bake_light(name);print(name,'duration',round(time.time()-t,1),'s',flush=True)
    (DEST/'bake_metadata.json').write_text(json.dumps({'date':'2026-10-27','sources':['game_broadleaf','game_shrub'],'seed':20261027,'voxel_resolution':64,'directions':'+X,-X,+Y,-Y,+Z,-Z','sky_rays':16,'start_cells':2.25,'attenuation':0.42,'visibility_floor_sky':0.30,'visibility_floor_sun':0.20,'impostor_supersampling':2,'change':'rotation de cartes de feuilles autour des points de branche les plus proches, sans changer les bornes'},ensure_ascii=False,indent=2)+'\n',encoding='utf8')


def normals_variant(mix=0.55, up=0.15):
    """Infléchit les normales des feuilles vers l'extérieur de leur rameau."""
    global DEST
    previous=OUT/'volume_look'
    DEST=OUT/'volume_look_normals'
    DEST.mkdir(parents=True,exist_ok=True)
    for name in ['game_fir',*SPEC]:
        src=previous/name;dst=DEST/name;dst.mkdir(parents=True,exist_ok=True)
        for file in ['mesh.bin','material.bin','volume.bin','volume64.bin','impostor.bin']:
            shutil.copyfile(src/file,dst/file)
        if name=='game_fir':continue
        for file in ['lighting.bin','impostor_light.bin']:
            shutil.copyfile(src/file,dst/file)
        data=bytearray((dst/'mesh.bin').read_bytes())
        magic,nv,ni,w,h,nmat,*bound=HEADER.unpack_from(data)
        if magic!=b'FOLMESH1':raise ValueError('Maillage source invalide')
        verts=np.frombuffer(data,dtype='<f4',count=nv*9,offset=HEADER.size).reshape(-1,9)
        tris=np.frombuffer(data,dtype='<u4',count=ni,offset=HEADER.size+nv*36).reshape(-1,3)
        if name=='game_shrub':
            # Les 697 triangles des brindilles alpha suivent les feuilles originales.
            start=4471+2064;end=start+697
            woody=tris[:4471]
            leaf=np.concatenate((tris[4471:start],tris[7232:]),axis=0)
            if not np.all(verts[leaf,8]==1):raise ValueError('Feuilles arbuste inattendues')
        else:
            leaf=tris[verts[tris[:,0],8]==0];woody=tris[verts[tris[:,0],8]==1]
        wood=verts[np.unique(woody),:3].copy()
        count=0
        for group in components(leaf):
            indices=np.unique(group);pos=verts[indices,:3].astype(np.float64)
            center=pos.mean(axis=0)
            anchor=wood[np.argmin(((wood-center)**2).sum(axis=1))].astype(np.float64)
            radial=pos-anchor
            distance=np.linalg.norm(radial,axis=1,keepdims=True)
            radial[:,1]+=up*distance[:,0]
            radial/=np.maximum(np.linalg.norm(radial,axis=1,keepdims=True),1e-12)
            old=verts[indices,3:6].astype(np.float64)
            old/=np.maximum(np.linalg.norm(old,axis=1,keepdims=True),1e-12)
            # Les cartes sont double face : conserver la face orientée vers l'extérieur.
            old*=np.where((old*radial).sum(axis=1,keepdims=True)<0,-1.,1.)
            blended=old*(1-mix)+radial*mix
            verts[indices,3:6]=blended/np.maximum(np.linalg.norm(blended,axis=1,keepdims=True),1e-12)
            count+=len(indices)
        (dst/'mesh.bin').write_bytes(data)
        print(name,'normales de feuilles',count,'mix',mix,'biais haut',up,flush=True)
    bake.OUT=DEST
    for name in SPEC:
        v,i,atlas,lo,hi,n=bake.load(name)
        bake.volume(name,v,i,atlas,lo,hi,n,64)
        bake.impostor(name,v,i,atlas,lo,hi,n)
    metadata={'date':'2026-10-27','source':'volume_look','mix_radial':mix,'biais_haut':up,
              'ancrage':'sommet de branche le plus proche du centre de chaque carte',
              'visibilite':'sidecars recopiés car positions, UV, triangles et alpha inchangés',
              'reference':'https://docs9.speedtree.com/modeler/doku.php?id=card_generator'}
    (DEST/'bake_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Préparation CPU des variantes de végétation')
    parser.add_argument('--normals',action='store_true',help='Créer volume_look_normals depuis volume_look')
    parser.add_argument('--mix',type=float,default=0.55,help='Mélange radial des normales (0 à 1)')
    parser.add_argument('--up',type=float,default=0.15,help='Biais vertical des normales radiales')
    args=parser.parse_args()
    if not 0<=args.mix<=1 or args.up<0:parser.error('Paramètres de normales hors limites')
    if args.normals:normals_variant(args.mix,args.up)
    else:main()
