"""Continuous root contact and canonical footprint, before every representation."""
import numpy as np


def bottom_at(points,triangles):
    a=triangles[:,0];b=triangles[:,1]-a;c=triangles[:,2]-a
    det=b[:,0]*c[:,2]-b[:,2]*c[:,0];good=np.abs(det)>1e-10
    a,b,c,det=a[good],b[good],c[good],det[good]
    result=np.zeros(len(points),dtype=np.float32)
    if not len(a):return result
    for first in range(0,len(points),64):
        d=points[first:first+64,None,:]-a[None,:,:]
        u=(d[:,:,0]*c[None,:,2]-d[:,:,2]*c[None,:,0])/det
        w=(b[None,:,0]*d[:,:,2]-b[None,:,2]*d[:,:,0])/det
        hit=(u>=-1e-5)&(w>=-1e-5)&(u+w<=1.00001)
        heights=np.where(hit,a[None,:,1]+u*b[None,:,1]+w*c[None,:,1],np.inf)
        low=heights.min(1);result[first:first+len(low)]=np.where(np.isfinite(low),np.maximum(low,0),0)
    return result


def fade(y,a,b):
    t=np.clip((y-a)/(b-a),0,1)
    return 1-t*t*(3-2*t),-6*t*(1-t)/(b-a)


class RootShape:
    def __init__(self,grid,origin,cell,ratio=1):
        self.grid=grid;self.origin=np.asarray(origin);self.cell=cell;self.ratio=ratio

    def sample(self,points):
        uv=(points[:,[0,2]]-self.origin)/self.cell;nz,nx=self.grid.shape
        ix=np.clip(np.floor(uv[:,0]).astype(int),0,nx-2);iz=np.clip(np.floor(uv[:,1]).astype(int),0,nz-2)
        x=np.clip(uv[:,0]-ix,0,1);z=np.clip(uv[:,1]-iz,0,1)
        a=self.grid[iz,ix];b=self.grid[iz,ix+1];c=self.grid[iz+1,ix];d=self.grid[iz+1,ix+1]
        h=(1-z)*((1-x)*a+x*b)+z*((1-x)*c+x*d)
        gx=((1-z)*(b-a)+z*(d-c))/self.cell
        gz=((1-x)*(c-a)+x*(d-b))/self.cell
        gx[(uv[:,0]<0)|(uv[:,0]>nx-1)]=0;gz[(uv[:,1]<0)|(uv[:,1]>nz-1)]=0
        return h+.004,gx,gz

    def apply(self,points,normals=None,tangents=None):
        p=np.asarray(points,dtype=np.float64).copy()
        n=np.asarray(normals,dtype=np.float64).copy() if normals is not None else None
        t=np.asarray(tangents,dtype=np.float64).copy() if tangents is not None else None
        h,gx,gz=self.sample(p);w,dw=fade(p[:,1],.16,.24);den=1-dw*h
        if n is not None:
            ny=n[:,1]/den;n[:,0]+=w*gx*ny;n[:,2]+=w*gz*ny;n[:,1]=ny
        if t is not None:t[:,1]=t[:,1]*den-w*(gx*t[:,0]+gz*t[:,2])
        p[:,1]-=w*h
        w,dw=fade(p[:,1],.16,.32);s=1-(1-self.ratio)*w;ds=-(1-self.ratio)*dw
        if n is not None:
            n[:,0]/=s;n[:,2]/=s
            n[:,1]=(n[:,1]-ds*(p[:,0]*n[:,0]+p[:,2]*n[:,2]))/(s+p[:,1]*ds)
            n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
        if t is not None:
            t=t*s[:,None]+p*(ds*t[:,1])[:,None]
            if n is not None:t-=n*np.sum(t*n,axis=1,keepdims=True)
            t/=np.maximum(np.linalg.norm(t,axis=1,keepdims=True),1e-12)
        p*=s[:,None]
        return p,n,t


def conform(vertices,indices,leaf_mask,target_reach=None,return_shape=False):
    vertices=vertices.copy();faces=indices.reshape(-1,3)
    wood=((leaf_mask>>vertices[:,8].astype(int))&1)==0
    root=wood&(np.mod(vertices[:,8],1)>.125);ids=np.flatnonzero(root)
    if not len(ids):
        report={'root_vertices':0,'moved_vertices':0};shape=RootShape(np.zeros((2,2)),[0,0],1)
        return (vertices,report,shape) if return_shape else (vertices,report)
    candidate=wood[faces].all(1)&(vertices[faces,1].min(1)<.17)
    points=vertices[ids,:3].copy();probe=points.copy();probe[:,[0,2]]*=.997
    support=np.minimum(bottom_at(probe,vertices[faces[candidate],:3]),np.maximum(points[:,1],0))
    xz=points[:,[0,2]].astype(float);span=np.ptp(xz,axis=0);cell=max(float(span.max())/192,.002)
    origin=xz.min(0)-cell;nx,nz=np.maximum(np.ceil(span/cell).astype(int)+3,3)
    grid=np.zeros((nz,nx),dtype=np.float64);slope=.35
    positive=support>1e-7;q=xz[positive];values=support[positive]
    cells=np.floor((q-origin)/cell).astype(int)
    # A separable max-plus distance transform is a continuous majorant with
    # gradient length <= sqrt(2)*.35. Seed four corners conservatively.
    for dx,dz in [(0,0),(1,0),(0,1),(1,1)]:
        at=cells+np.array([dx,dz]);position=origin+at*cell
        high=values+slope*np.abs(position-q).sum(1)
        np.maximum.at(grid,(at[:,1],at[:,0]),high)
    for axis in [0,1]:
        ramp=np.arange(grid.shape[axis])*cell*slope
        ramp=ramp[:,None] if axis==0 else ramp[None,:]
        grid=np.maximum.accumulate(grid+ramp,axis=axis)-ramp
        flipped=np.flip(grid,axis=axis)
        flipped=np.maximum.accumulate(flipped+ramp,axis=axis)-ramp
        grid=np.flip(flipped,axis=axis)
    reach=float(np.linalg.norm(xz,axis=1).max())
    ratio=min(1,float(target_reach)/reach) if target_reach is not None else 1.0
    if not 0<ratio<=1:raise ValueError('Invalid canonical root footprint')
    shape=RootShape(grid,origin,cell,ratio)
    original=vertices[:,:3].copy();positions,normals,_=shape.apply(original,vertices[:,3:6])
    edges=np.unique(np.sort(faces[wood[faces].all(1)][:,[0,1,1,2,2,0]].reshape(-1,2),axis=1),axis=0)
    core=(original[edges,1].max(1)<=.16)&(positions[edges,1].max(1)<=.16)
    edges=edges[core];before=np.linalg.norm(original[edges[:,1]]-original[edges[:,0]],axis=1)
    valid=before>1e-6;edges=edges[valid];before=before[valid]
    stretch=np.linalg.norm(positions[edges[:,1]]-positions[edges[:,0]],axis=1)/before
    # The shear's spectral norm bounds distortion independently of triangle
    # density. Catch vertex-tag discontinuities before they reach any LOD.
    gradient=np.sqrt(2)*slope;bound=ratio*(np.sqrt(4+gradient*gradient)+gradient)/2
    if len(stretch) and stretch.max()>bound+1e-4:raise ValueError('Root conformation exceeds its continuous strain bound')
    vertices[:,:3]=positions;vertices[:,3:6]=normals
    report={'root_vertices':len(ids),'moved_vertices':int((np.linalg.norm(positions-original,axis=1)>1e-6).sum()),
            'max_removed_underside_gap_normalized':float(grid.max()+.004),'support_grid':list(grid.shape),
            'support_cell':cell,'maximum_support_gradient':float(np.sqrt(2)*slope),'canonical_root_scale':ratio,
            'core_wood_edges_checked':len(stretch),'core_edge_stretch_p95':float(np.percentile(stretch,95)) if len(stretch) else 0,
            'core_edge_stretch_max':float(stretch.max()) if len(stretch) else 0,'core_edge_stretch_bound':float(bound),
            'method':'Continuous bounded support, smooth trunk transition and footprint baked into every representation'}
    return (vertices,report,shape) if return_shape else (vertices,report)
