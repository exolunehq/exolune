"""Game silhouettes and real root meshes. Source images remain material data, never scene backplates.

Operate on a fresh normalized FOLMESH1; the placement origin becomes the actual trunk base.
"""
import hashlib
import math
import struct
import numpy as np
from volume_assets import components

HEADER=struct.Struct('<8s5I6f')


def unit(a):
    return a/np.maximum(np.linalg.norm(a,axis=-1,keepdims=True),1e-12)


def smooth(a,b,x):
    u=np.clip((x-a)/(b-a),0,1)
    return u*u*(3-2*u)


def roots(base,reach,crest,bark,uvrect,seed):
    rng=np.random.default_rng(seed);vertices=[];triangles=[]
    lo,hi=uvrect
    def vertex(p,n,u,v):
        vertices.append([*p,*n,lo[0]+u*(hi[0]-lo[0]),lo[1]+v*(hi[1]-lo[1]),bark+.25])
    # An irregular flared collar intersects the strengthened stem, rather than sitting under it as a flat disc.
    rings=[(-.025,1.28),(.005,1.60),(.45*crest,1.20),(1.65*crest,.78)]
    sides=16
    for j,(height,scale) in enumerate(rings):
        for k in range(sides):
            theta=k*math.tau/sides;r=base*scale*(1+.10*math.sin(6*theta+seed%17))
            p=[r*math.cos(theta),height,r*math.sin(theta)]
            n=unit(np.array([math.cos(theta),.4 if j<3 else .15,math.sin(theta)]))
            vertex(p,n,k/sides,j/(len(rings)-1))
    for j in range(len(rings)-1):
        for k in range(sides):
            a=j*sides+k;b=j*sides+(k+1)%sides;c=a+sides;d=b+sides
            triangles.extend([[a,c,b],[b,c,d]])
    centre=len(vertices);vertex([0,rings[-1][0],0],[0,1,0],.5,.5)
    for k in range(sides):
        triangles.append([(len(rings)-1)*sides+k,(len(rings)-1)*sides+(k+1)%sides,centre])
    count=7
    for spoke in range(count):
        first=len(vertices);theta=math.tau*(spoke+rng.uniform(-.12,.12))/count
        length=reach*rng.uniform(.76,1.0);curve=rng.uniform(-.18,.18)
        segments=7;around=8
        for j in range(segments):
            t=j/(segments-1);angle=theta+curve*t
            distance=base*1.05+(length-base*1.05)*t
            width=base*(.55*(1-t)**.75+.06)
            tall=crest*(1-t)**1.7+.003
            y=-.018-.012*t+tall*.5
            tangent=np.array([-math.sin(angle),0,math.cos(angle)])
            centre=np.array([distance*math.cos(angle),y,distance*math.sin(angle)])
            for k in range(around):
                a=math.tau*k/around
                pos=centre+tangent*(math.cos(a)*width)+np.array([0,math.sin(a)*tall*.5,0])
                normal=unit(tangent*(math.cos(a)/width)+np.array([0,2*math.sin(a)/tall,0]))
                vertex(pos,normal,k/around,t)
        for j in range(segments-1):
            for k in range(around):
                a=first+j*around+k;b=first+j*around+(k+1)%around;c=a+around;d=b+around
                triangles.extend([[a,b,c],[b,d,c]])
    return np.asarray(vertices,dtype='<f4'),np.asarray(triangles,dtype='<u4')


def style(folder,model,leafmask,tree):
    raw=(folder/'mesh.bin').read_bytes();magic,nv,ni,w,h,materials,*bound=HEADER.unpack_from(raw)
    vertices=np.frombuffer(raw,dtype='<f4',offset=HEADER.size,count=nv*9).reshape(-1,9).copy()
    indices=np.frombuffer(raw,dtype='<u4',offset=HEADER.size+nv*36,count=ni).reshape(-1,3).copy()
    atlas=np.frombuffer(raw,dtype='u1',offset=HEADER.size+nv*36+ni*4).reshape(h,w,4).copy()
    material=vertices[indices[:,0],8].astype(int)
    leafy=np.array([bool(leafmask&(1<<int(m))) for m in material])
    seed=int.from_bytes(hashlib.sha256(folder.name.encode()).digest()[:4],'little');rng=np.random.default_rng(seed)
    old_wood=vertices[np.unique(indices[~leafy]),:3].copy()
    if tree:
        ids=np.unique(indices[~leafy]);wood=vertices[ids,:3]
        bottom=wood[wood[:,1]<wood[:,1].min()+.035]
        origin=np.array([np.median(bottom[:,0]),wood[:,1].min(),np.median(bottom[:,2])])
        vertices[:,:3]-=origin;old_wood-=origin
        if model in [14,15]:
            # Both conifer companions come from the game pine: readable boughs instead of thinned scanned needles.
            y=vertices[:,1].copy()
            breadth=1+(.15 if model==15 else -.10)*np.sin(np.pi*np.clip((y-.12)/.88,0,1))
            vertices[:,[0,2]]*=breadth[:,None]
            vertices[:,0]+=(.025 if model==14 else -.012)*y*y
            old_wood=vertices[ids,:3].copy()
        lo=vertices[:,:3].min(0);hi=vertices[:,:3].max(0);crown_width=max(hi[0]-lo[0],hi[2]-lo[2])
        crown=.3 if model in [0,14,15] else .45
        target=(.018 if crown==.3 else .026)*crown_width/crown
        measured=max(np.percentile(np.linalg.norm(vertices[ids][vertices[ids,1]<.04][:,[0,2]],axis=1),85),.002)
        strength=np.clip(target/measured,1.25,3.5)
        # Widen around the local stem centre, keeping the original forks and branch attachment architecture.
        levels=[];centres=[]
        for j in range(10):
            low=j*.05;take=ids[(vertices[ids,1]>=low)&(vertices[ids,1]<low+.05)]
            if len(take):levels.append(low+.025);centres.append(np.median(vertices[take][:,[0,2]],axis=0))
        take=ids[vertices[ids,1]<.5]
        centre=np.stack([np.interp(vertices[take,1],levels,np.asarray(centres)[:,axis]) for axis in range(2)],1)
        factor=1+(strength-1)*(1-smooth(.04,.5,vertices[take,1]))
        vertices[np.ix_(take,[0,2])]=centre+(vertices[take][:,[0,2]]-centre)*factor[:,None]
        styled_wood=vertices[ids,:3].copy()
    else:
        crown_width=max(bound[3]-bound[0],bound[5]-bound[2]);styled_wood=old_wood
    # Connected leaf cards are arranged around their supporting branch and keep the source's cutout images.
    additions=[];new_indices=[];total=nv
    groups=components(indices[leafy]) if tree else []
    for group in groups:
        group=np.asarray(group,'u4');old,local=np.unique(group,return_inverse=True);source=vertices[old].copy()
        centre=source[:,:3].mean(0)
        nearest=int(np.argmin(((old_wood-centre)**2).sum(1)));pivot=old_wood[nearest];shift=styled_wood[nearest]-pivot
        vertices[old,:3]+=shift
        copies=2 if model in [16,17,18,19] else 1 if model==15 and rng.random()<.55 else 0
        for copy in range(copies):
            angle=(copy*2-1)*rng.uniform(.35,.9);ca,sa=math.cos(angle),math.sin(angle)
            rot=np.array([[ca,0,sa],[0,1,0],[-sa,0,ca]])
            q=source.copy();q[:,:3]=(q[:,:3]-pivot)@rot.T+pivot+shift
            q[:,3:6]=q[:,3:6]@rot.T
            if np.all(q[:,:3]>=lo-.005) and np.all(q[:,:3]<=hi+.005):
                additions.append(q);new_indices.append(local.reshape(-1,3).astype('u4')+total);total+=len(q)
    if additions:vertices=np.concatenate([vertices]+additions);indices=np.concatenate([indices]+new_indices)
    leaf_ids=np.unique(indices[np.array([bool(leafmask&(1<<int(m))) for m in vertices[indices[:,0],8]])])
    if tree and len(leaf_ids):
        centre=np.array([0,.65,0]);radial=vertices[leaf_ids,:3]-centre
        radial[:,1]*=.5
        vertices[leaf_ids,3:6]=unit(.65*vertices[leaf_ids,3:6]+.35*unit(radial)+np.array([0,.08,0]))
    # A restrained warmer material balance; opacity remains untouched.
    tile=w//materials
    for m in range(materials):
        factor=np.array([1.045,1.0,.955]) if leafmask&(1<<m) else np.array([1.065,1.015,.955])
        atlas[:,m*tile:(m+1)*tile,:3]=np.rint(atlas[:,m*tile:(m+1)*tile,:3]*factor).clip(0,255).astype('u1')
    if tree:
        wood_ids=np.unique(indices[~np.array([bool(leafmask&(1<<int(m))) for m in vertices[indices[:,0],8]])])
        bark=int(vertices[wood_ids[0],8]);lower=wood_ids[vertices[wood_ids,1]<.10]
        uv=vertices[lower if len(lower)>=3 else wood_ids,6:8];uvrect=(uv.min(0),uv.max(0))
        base=target;reach=.085*crown_width/crown;crest=.028 if crown==.3 else .042
        root_vertices,root_indices=roots(base,reach,crest,bark,uvrect,seed)
        root_indices+=len(vertices);vertices=np.concatenate([vertices,root_vertices]);indices=np.concatenate([indices,root_indices])
        (folder/'form.bin').write_bytes(struct.pack('<8s4f',b'FOLFORM1',base,crest,reach,crown_width))
    lo=vertices[:,:3].min(0);hi=vertices[:,:3].max(0)
    with (folder/'mesh.bin').open('wb') as f:
        f.write(HEADER.pack(magic,len(vertices),indices.size,w,h,materials,*lo,*hi))
        f.write(vertices.astype('<f4').tobytes());f.write(indices.astype('<u4').tobytes());f.write(atlas.tobytes())
    print(folder.name,'game form',len(indices),'triangles; roots',tree,flush=True)
