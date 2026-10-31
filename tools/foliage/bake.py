"""Construit les volumes et vues à partir du même mesh.bin texturé."""
from pathlib import Path
import argparse, math, shutil, struct, sys, time
import numpy as np
from numba import njit, prange
from importe import OUT
from filtre_transmission import filter_volume

@njit
def texel(atlas, u, v, material, material_count):
    h, w, _ = atlas.shape
    tile_width = w // material_count
    x = int(material)*tile_width + min(tile_width-1, int((u-math.floor(u))*tile_width))
    y = min(h-1, int((v-math.floor(v))*h))
    return atlas[y, x]

@njit
def srgb_to_linear(v):
    v = v / 255.0
    if v <= 0.04045: return v / 12.92
    return ((v + 0.055)/1.055)**2.4

@njit
def accumulate(verts, indices, atlas, lo, hi, resolution, material_count):
    # Sommes surface, couleur linéaire et normales ; une grille Z,Y,X contiguë.
    out = np.zeros((resolution,resolution,resolution,7), np.float64)
    step = (hi-lo)/resolution
    minstep = min(step[0], step[1], step[2])
    for tri in range(len(indices)//3):
        a, b, c = verts[indices[tri*3]], verts[indices[tri*3+1]], verts[indices[tri*3+2]]
        ab = b[:3]-a[:3]; ac = c[:3]-a[:3]
        cross = np.cross(ab, ac); area = 0.5*np.sqrt((cross*cross).sum())
        # Surface échantillonnée à une densité reliée à la taille des cellules.
        count = min(64, max(1, int(math.ceil(area / (minstep*minstep*0.15)))))
        for j in range(count):
            # Suite à faible discrépance, uniforme sur le triangle.
            q = math.sqrt((j+0.5)/count)
            r = (j*0.6180339887498949) % 1.0
            wa, wb, wc = 1-q, q*(1-r), q*r
            p = a[:3]*wa+b[:3]*wb+c[:3]*wc
            uv = a[6:8]*wa+b[6:8]*wb+c[6:8]*wc
            tex = texel(atlas, uv[0], uv[1], a[8], material_count); alpha = tex[3]/255.0
            if alpha <= 0: continue
            x = min(resolution-1, max(0, int((p[0]-lo[0])/step[0])))
            y = min(resolution-1, max(0, int((p[1]-lo[1])/step[1])))
            z = min(resolution-1, max(0, int((p[2]-lo[2])/step[2])))
            wt = area * alpha/count
            out[z,y,x,0] += wt
            nx=a[3]*wa+b[3]*wb+c[3]*wc
            ny=a[4]*wa+b[4]*wb+c[4]*wc
            nz=a[5]*wa+b[5]*wb+c[5]*wc
            normal_length=math.sqrt(nx*nx+ny*ny+nz*nz)
            for k in range(3):
                out[z,y,x,1+k] += wt*srgb_to_linear(tex[k])
            if normal_length > 1e-12:
                out[z,y,x,4] += wt*nx/normal_length
                out[z,y,x,5] += wt*ny/normal_length
                out[z,y,x,6] += wt*nz/normal_length
    return out

@njit(parallel=True)
def bake_views(verts, indices, atlas, radius, azimuths, elevations, size, material_count):
    count = azimuths*elevations
    # RGBA et normale/profondeur : taille double pour quatre sous-échantillons.
    color = np.zeros((count,size,size,4), np.uint8)
    nd = np.zeros((count,size,size,4), np.float32)
    depth = np.full((count,size,size), -1e10, np.float32)
    for view in prange(count):
        az = 2*math.pi*(view%azimuths)/azimuths
        el = 0.5*math.pi*(view//azimuths)/(elevations-1)
        st,ct,sp,cp=math.sin(az),math.cos(az),math.sin(el),math.cos(el)
        camera = np.array((st*cp,sp,ct*cp))
        right = np.array((ct,0.,-st))
        up = np.array((-st*sp,cp,-ct*sp))
        # projection indépendante de la vue, le sommet du pixel est en haut
        projected = np.empty((len(verts),3), np.float32)
        for i in range(len(verts)):
            px,py,pz=verts[i,0],verts[i,1]-0.5,verts[i,2]
            projected[i,0] = ((px*right[0]+py*right[1]+pz*right[2])/radius*0.5+0.5)*size
            projected[i,1] = (0.5-(px*up[0]+py*up[1]+pz*up[2])/radius*0.5)*size
            projected[i,2] = px*camera[0]+py*camera[1]+pz*camera[2]
        for t in range(len(indices)//3):
            i,j,k = indices[3*t], indices[3*t+1], indices[3*t+2]
            a,b,c=projected[i],projected[j],projected[k]
            det=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
            if abs(det)<1e-12: continue
            xmin=max(0,int(math.ceil(min(a[0],b[0],c[0])-0.5)))
            xmax=min(size-1,int(math.floor(max(a[0],b[0],c[0])-0.5)))
            ymin=max(0,int(math.ceil(min(a[1],b[1],c[1])-0.5)))
            ymax=min(size-1,int(math.floor(max(a[1],b[1],c[1])-0.5)))
            for y in range(ymin,ymax+1):
                for x in range(xmin,xmax+1):
                    dx=x+0.5-a[0]; dy=y+0.5-a[1]
                    wb=(dx*(c[1]-a[1])-dy*(c[0]-a[0]))/det
                    wc=((b[0]-a[0])*dy-(b[1]-a[1])*dx)/det
                    wa=1-wb-wc
                    if min(wa,wb,wc)<0: continue
                    z=a[2]*wa+b[2]*wb+c[2]*wc
                    if z<=depth[view,y,x]: continue
                    u=verts[i,6]*wa+verts[j,6]*wb+verts[k,6]*wc
                    v=verts[i,7]*wa+verts[j,7]*wb+verts[k,7]*wc
                    tex=texel(atlas,u,v,verts[i,8],material_count)
                    if tex[3]<128: continue
                    depth[view,y,x]=z
                    color[view,y,x,:3]=tex[:3]; color[view,y,x,3]=255
                    for d in range(3): nd[view,y,x,d]=verts[i,3+d]*wa+verts[j,3+d]*wb+verts[k,3+d]*wc
                    # Matériaux Poly Haven double face, normale tournée vers l'observateur.
                    if nd[view,y,x,0]*camera[0]+nd[view,y,x,1]*camera[1]+nd[view,y,x,2]*camera[2]<0:
                        nd[view,y,x,:3]*=-1
                    nd[view,y,x,3]=z
    return color,nd


def load(name):
    path=OUT/name/'mesh.bin'
    header=struct.Struct('<8s5I6f')
    with path.open('rb') as f:
        magic,nv,ni,w,h,material_count,*bounds=header.unpack(f.read(header.size))
        if magic!=b'FOLMESH1': raise ValueError('magic')
        verts=np.fromfile(f,dtype='<f4',count=nv*9).reshape(-1,9)
        inds=np.fromfile(f,dtype='<u4',count=ni)
        atlas=np.fromfile(f,dtype='u1',count=w*h*4).reshape(h,w,4)
        if f.read(1): raise ValueError('extra bytes')
    return verts,inds,atlas,np.array(bounds[:3]),np.array(bounds[3:]),material_count


def volume(name, verts, inds, atlas, lo, hi, material_count, resolution):
    sums=accumulate(verts,inds,atlas,lo,hi,resolution,material_count)
    levels=resolution.bit_length()
    path=OUT/name/f'volume{resolution}.bin'
    unfiltered=path.with_suffix('.unfiltered.tmp')
    filtered=path.with_suffix('.filtered.tmp')
    with unfiltered.open('wb') as f:
        f.write(struct.pack('<8s2I6f',b'FOLVOL01',resolution,levels,*lo,*hi))
        for level in range(levels):
            r=resolution>>level
            area=sums[...,0]
            # Surfaces bidirectionnelles : aire projetée moyenne d'une feuille = A/2.
            # Poisson : probabilité d'interception = 1-exp(-aire projetée/aire cellule).
            step=(hi-lo)/r
            cellarea=(step[0]*step[1]+step[1]*step[2]+step[0]*step[2])/3
            data=np.zeros((r,r,r,8),dtype='<f4')
            data[...,0]=1-np.exp(-0.5*area/cellarea)
            nz=area>0
            for j in range(3):
                data[...,1+j][nz]=(sums[...,1+j][nz]/area[nz])
                data[...,4+j][nz]=(sums[...,4+j][nz]/area[nz])
            coherence=np.sqrt((data[...,4:7]**2).sum(axis=-1))
            data[...,7]=1-np.minimum(1,coherence)
            nz2=coherence>1e-8
            data[...,4:7][nz2]/=coherence[nz2,None]
            f.write(data.tobytes())
            if r>1: sums=sums.reshape(r//2,2,r//2,2,r//2,2,7).sum(axis=(1,3,5))
    filter_volume(unfiltered, filtered)
    filtered.replace(path)
    unfiltered.unlink()
    if resolution==64: shutil.copyfile(path, OUT/name/'volume.bin')
    print(name, f'volume {resolution} ready',flush=True)


def impostor(name, verts, inds, atlas, lo, hi, material_count):
    radius=np.linalg.norm(np.maximum(abs(lo-np.array([0,.5,0])),abs(hi-np.array([0,.5,0]))))
    color,nd=bake_views(verts,inds,atlas,radius,12,5,256,material_count)
    # Average coverage and unassociated color; depth and normals weighted by visible subpixels.
    views=60
    colors=color.reshape(views,128,2,128,2,4)
    normals=nd.reshape(views,128,2,128,2,4)
    weights=colors[...,3].astype(np.float32)/255
    coverage=weights.sum(axis=(2,4))
    outc=np.zeros((views,128,128,4),np.uint8)
    # La moyenne en couleur linéaire, comme le filtrage des textures du maillage ; en sRGB, elle assombrissait
    # l'imposteur (docs/vegetation-planetaire.md, l'éclairage des imposteurs). Stockée en sRGB ; le moteur la linéarise.
    lin=colors[...,:3].astype(np.float64)/255
    lin=np.where(lin<=0.04045,lin/12.92,((lin+0.055)/1.055)**2.4)
    for c in range(3):
        # Avoid mixing uncovered black texels into unassociated colour.
        mean=(lin[...,c]*weights).sum(axis=(2,4))/np.maximum(coverage,1)
        srgb=np.where(mean<=0.0031308,12.92*mean,1.055*np.maximum(mean,0)**(1/2.4)-0.055)
        outc[...,c]=np.rint(np.clip(srgb,0,1)*255).astype(np.uint8)
    outc[...,3]=np.rint(coverage*255/4).astype(np.uint8)
    outn=np.zeros((views,128,128,4),dtype='<f4')
    for c in range(4): outn[...,c]=(normals[...,c]*weights).sum(axis=(2,4))/np.maximum(coverage,1)
    n=np.linalg.norm(outn[...,:3],axis=-1); mask=n>1e-6; outn[...,:3][mask]/=n[mask,None]
    with (OUT/name/'impostor.bin').open('wb') as f:
        f.write(struct.pack('<8s4I7f',b'FOLIMP01',12,5,128,128,*lo,*hi,radius))
        f.write(outc.tobytes()); f.write(outn.tobytes())
    print(name,'impostor ready radius',radius,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Volumes et imposteurs issus du maillage importé')
    parser.add_argument('names', nargs='+', help='Dossiers des modèles, par exemple game_fir game_broadleaf')
    parser.add_argument('--volume-res', nargs='+', type=int, choices=[32,64,128], default=[32,64,128])
    parser.add_argument('--volume-only', action='store_true')
    parser.add_argument('--impostor-only', action='store_true')
    parser.add_argument('--out', help='Dossier des modèles ; assets/foliage par défaut')
    args=parser.parse_args()
    if args.volume_only and args.impostor_only: parser.error('Modes incompatibles')
    if args.out: OUT=Path(args.out)
    for name in args.names:
        t=time.time(); verts,inds,atlas,lo,hi,material_count=load(name)
        if not args.impostor_only:
            for resolution in args.volume_res:
                volume(name,verts,inds,atlas,lo,hi,material_count,resolution)
        if not args.volume_only:
            impostor(name,verts,inds,atlas,lo,hi,material_count)
        print(name, 'seconds',time.time()-t,flush=True)
