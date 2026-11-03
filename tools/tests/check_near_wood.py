"""Check close-wood curvature, fixed roots, UV seams and conforming topology."""
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'foliage/local3d'))
from near_wood import refine


def cylinder():
    rows=[0,.1,.2,.4,.6,.8];vertices=[];faces=[]
    for y in rows:
        for side in range(9):
            angle=side*np.pi/4
            vertices.append([.06*np.cos(angle),y,.06*np.sin(angle),np.cos(angle),0,np.sin(angle),side/8,y,0])
    for row in range(len(rows)-1):
        for side in range(8):
            a=row*9+side;b=a+1;c=a+9;d=c+1
            faces.extend([[a,c,b],[b,c,d]])
    centre=len(vertices);vertices.append([0,0,0,0,-1,0,.5,.5,0])
    for side in range(8):faces.append([centre,side,side+1])
    v=np.asarray(vertices,dtype='<f4');i=np.asarray(faces,dtype='<u4').reshape(-1)
    # Separate each UV chart, as a glTF exporter does at a seam.
    v=v[i].copy();v[:,6]+=np.repeat(np.arange(len(faces))*.01,3)
    i=np.arange(len(v),dtype='<u4')
    light=np.ones((len(v),8),'<f4');extra=np.zeros((len(v),16),'<f4');extra[:,:4]=1
    return v,i,light,extra


v,i,l,e=cylinder();new,ids,light,extra,report=refine(v,i,l,e,2)
assert report['refined_wood_faces']>0
assert np.array_equal(new[:len(v)],v),'Original vertices changed'
root=i.reshape(-1,3)[v[i.reshape(-1,3),1].max(1)<=.002]
triangles={tuple(face) for face in ids.reshape(-1,3)}
assert all(tuple(face) in triangles for face in root),'A supported underside triangle changed'
assert len(root)==8,'The support witness has no closed underside'
added=new[len(v):,:3];radial=np.linalg.norm(added[:,[0,2]],axis=1)
assert np.median(abs(radial[added[:,1]>.21]-.06))<.002,'Round trunk did not retain its curvature above the protected support zone'
source_centres=v[i.reshape(-1,3),:3].mean(1)
source_root=source_centres[(source_centres[:,1]>.002)&(source_centres[:,1]<.18)]
coarse_error=np.median(abs(np.linalg.norm(source_root[:,[0,2]],axis=1)-.06))
assert np.median(abs(radial[added[:,1]<.18]-.06))<coarse_error,'Root-side curvature did not improve the faceted support'
# Coincident UV seam midpoints have the same geometric position.
_,counts=np.unique(np.round(added,6),axis=0,return_counts=True)
assert counts.max()>1,'The seam witness did not exercise shared refined edges'
faces=new[ids.reshape(-1,3),:3]
cross=np.cross(faces[:,1]-faces[:,0],faces[:,2]-faces[:,0])
assert np.all(np.linalg.norm(cross,axis=1)>1e-10),'Refinement created a degenerate face'
centres=faces.mean(1);outward=centres.copy();outward[:,1]=0
side=np.linalg.norm(cross[:,[0,2]],axis=1)>1e-10
assert np.all(np.sum(cross[side]*outward[side],axis=1)>0),'Refinement reversed a cylinder face'
root_heights=added[added[:,1]<.18,1]
possible=np.unique(np.array([v[a,1]*.5+v[b,1]*.5 for a in range(len(v)) for b in range(a,min(len(v),a+3))]+
                            [v[face,1].mean() for face in i.reshape(-1,3)]))
assert np.all(np.min(abs(root_heights[:,None]-possible[None,:]),axis=1)<1e-6),'Root support heights were curved vertically'
# Weld positions only for topology validation; UVs remain separate in the asset.
_,weld=np.unique(np.round(new[:,:3],6),axis=0,return_inverse=True);weld=weld.reshape(-1)
f=weld[ids.reshape(-1,3)];edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1)
unique,counts=np.unique(edges,axis=0,return_counts=True)
assert counts.max()<=2,'Refinement created a nonmanifold edge'
boundary=unique[counts==1]
positions=np.unique(np.round(new[:,:3],6),axis=0)
assert np.all((positions[boundary,1]==0).all(1)|(positions[boundary,1]==.8).all(1)),'A UV seam or partial split opened a crack'
again=refine(v,i,l,e,2)
assert all(np.array_equal(a,b) for a,b in zip((new,ids,light,extra),again[:4])),'Refinement is not deterministic'
assert light.min()>=0 and light.max()<=1
assert np.allclose(np.linalg.norm(new[:,3:6],axis=1),1,atol=1e-5)
print('PASS: near curvature, unchanged roots/source, UV seams, winding, topology and determinism')
