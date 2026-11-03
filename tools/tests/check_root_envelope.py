"""A raised root must retain thickness while its underside meets the soil."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'foliage/local3d'))
from roots import conform,RootShape

vertices=[]
for x in np.linspace(0,1,9):
    low=-.01+.10*np.sin(x*np.pi)
    for y,z in [(low,-.08),(low,.08),(low+.04,-.08),(low+.04,.08)]:
        vertices.append([x,y,z,0,1,0,x,z,.25])
v=np.array(vertices,dtype=np.float32);faces=[]
for j in range(8):
    a=j*4;b=a+4
    faces.extend([[a,a+1,b+1],[a,b+1,b],[a+2,b+2,b+3],[a+2,b+3,a+3]])
indices=np.array(faces,dtype=np.uint32).ravel();copy=v.copy();fixed,report=conform(v,indices,2)
assert np.array_equal(v,copy),'The master was mutated'
assert fixed[::4,1].max()<.002,'A raised underside still leaves a visible gap'
assert np.allclose(fixed[2::4,1]-fixed[::4,1],.04,atol=1e-5),'Root volume was flattened'
assert np.array_equal(fixed[:,[0,2,6,7,8]],v[:,[0,2,6,7,8]])
assert fixed[:,1].min()<=-.0099,'Buried ends were raised'
assert np.isfinite(fixed).all() and np.allclose(np.linalg.norm(fixed[:,3:6],axis=1),1)
print('Raised root envelope: supported underside, preserved thickness/UVs/buried ends and immutable master pass.',report)

# Material/UV seams at the collar must use the same continuous field. The
# previous root-tag-only warp separated coincident vertices on this boundary.
seam=np.array([[.15,y,.1] for y in [.1599999,.16,.1600001,.2399999,.24,.2400001,.3199999,.32,.3200001]])
shape=RootShape(np.array([[.01,.04],[.02,.05]]),[0,0],.3,.6)
q,_,_=shape.apply(seam)
for start in [0,3,6]:assert np.linalg.norm(np.diff(q[start:start+3],axis=0),axis=1).max()<1e-6,'A root transition tears the surface'
dupes=np.repeat(seam,2,axis=0);moved=shape.apply(dupes)[0]
assert np.array_equal(moved[::2],moved[1::2]),'Coincident material seams separated'

# Independently differentiate the complete warp, then check transported frames.
rng=np.random.default_rng(631);p=rng.uniform([.04,-.01,.04],[.24,.4,.24],(64,3))
n=rng.normal(size=p.shape);n/=np.linalg.norm(n,axis=1,keepdims=True)
t=np.cross(n,[0,1,0]);t/=np.linalg.norm(t,axis=1,keepdims=True)
q,nn,tt=shape.apply(p,n,t);epsilon=1e-6
jac=np.stack([(shape.apply(p+np.eye(3)[i]*epsilon)[0]-shape.apply(p-np.eye(3)[i]*epsilon)[0])/(2*epsilon) for i in range(3)],axis=2)
assert (np.linalg.det(jac)>0).all(),'Root correction folds the local volume'
expected_n=np.linalg.solve(jac.transpose(0,2,1),n[...,None])[...,0];expected_n/=np.linalg.norm(expected_n,axis=1,keepdims=True)
expected_t=np.einsum('nij,nj->ni',jac,t);expected_t/=np.linalg.norm(expected_t,axis=1,keepdims=True)
assert np.allclose(nn,expected_n,atol=1e-5) and np.allclose(tt,expected_t,atol=1e-5),'Normal/tangent transport disagrees with the deformed surface'
assert np.allclose(np.sum(nn*tt,axis=1),0,atol=1e-6)
assert np.array_equal(q[p[:,1]>.32],p[p[:,1]>.32]),'The crown was reshaped by ground contact'
print('Root continuity, positive Jacobian, seam identity, unchanged upper wood and differential normal/tangent transport pass.')
