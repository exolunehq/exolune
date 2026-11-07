"""Reject rotated branch fans even when large roots hide their thinness."""
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'foliage/local3d'))
from branch_volume import measure


def box(lower,upper):
    points=np.array([[x,y,z] for x in [lower[0],upper[0]] for y in [lower[1],upper[1]] for z in [lower[2],upper[2]]],float)
    faces=np.array([[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]])
    return points[faces]


root=box([-6,0,-6],[6,1,6]);trunk=box([-.2,0,-.2],[.2,6,.2])
fan=box([-3,4,-.08],[3,5,.08])
flat=np.concatenate([root,trunk,fan])
volume=np.concatenate([flat,box([-.08,4,-3],[.08,5,3])])
assert measure(flat)['status']=='fail','Large roots concealed the flat branches'
assert measure(volume)['status']=='pass','A radial supporting crown was rejected'
for angle in np.linspace(0,np.pi,13):
    c,s=np.cos(angle),np.sin(angle);rotation=np.array([[c,0,s],[0,1,0],[-s,0,c]])
    assert measure(flat@rotation.T)['status']=='fail','A rotated fan escaped detection'
    assert measure(volume@rotation.T)['status']=='pass','Camera orientation changed acceptance'
base=measure(flat)
for scale in [.05,1,80]:
    result=measure(flat*scale+np.array([12000,7,-23000]))
    assert abs(result['surface_spread_ratio']-base['surface_spread_ratio'])<1e-6
    assert abs(result['extent_ratio']-base['extent_ratio'])<1e-6
# Four exact child triangles of each original face must preserve its moments.
a,b,c=flat[:,0],flat[:,1],flat[:,2];ab=(a+b)/2;bc=(b+c)/2;ca=(c+a)/2
subdivided=np.concatenate([np.stack([a,ab,ca],1),np.stack([ab,b,bc],1),np.stack([ca,bc,c],1),np.stack([ab,bc,ca],1)])
assert abs(measure(subdivided)['surface_spread_ratio']-base['surface_spread_ratio'])<1e-6
print('Branch volume: root exclusion, rotated fans, radial crowns, scale/translation and triangle subdivision pass.')
