"""Build a shared face domain with independent front/rear 3D boundary controls.

Run with the city CPU Python. Harmonic coordinate extension fills only the
thin front/rear structural ribbons; curved transverse spans own their depth.
"""
import argparse
import json
import math
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,'E:/ExoluneTools/city-python')
from shapely.geometry import Polygon,box
from shapely import constrained_delaunay_triangles
from profile_domain import spline


def boundary_value(point,front,rear):
    a=front[:,[0,2]];b=np.roll(a,-1,axis=0);edge=b-a
    t=np.clip(((point-a)*edge).sum(1)/np.maximum((edge*edge).sum(1),1e-15),0,1)
    nearest=a+edge*t[:,None];distance=((nearest-point)**2).sum(1);i=int(distance.argmin())
    f=front[i]*(1-t[i])+front[(i+1)%len(front)]*t[i]
    r=rear[i]*(1-t[i])+rear[(i+1)%len(rear)]*t[i]
    return np.array([f[1],r[0]-f[0],r[1],r[2]-f[2]])


def build(recipe):
    profiles={name:(np.array(spline(p['front'],p['samples'])),np.array(spline(p['rear'],p['samples']))) for name,p in recipe['profiles'].items()}
    outer=profiles['outer'][0][:,[0,2]];holes=[p[0][:,[0,2]] for name,p in profiles.items() if name!='outer']
    domain=Polygon(outer,holes)
    if not domain.is_valid:raise ValueError('Intersecting canonical profile controls')
    radius=recipe['lip_radius_m'];face=domain.buffer(-radius,quad_segs=5).simplify(.0001,preserve_topology=True)
    if face.geom_type!='Polygon' or len(face.interiors)!=len(profiles)-1:raise ValueError('A structural ribbon is thinner than its lip')
    step=recipe['face_grid_m'];vertices=[];faces=[];lookup={};seen=set()
    def index(p):
        key=tuple(round(float(v),7) for v in p)
        if key not in lookup:lookup[key]=len(vertices);vertices.append(key)
        return lookup[key]
    x0,z0,x1,z1=face.bounds
    for iz in range(math.floor(z0/step),math.ceil(z1/step)):
        for ix in range(math.floor(x0/step),math.ceil(x1/step)):
            cell=face.intersection(box(ix*step,iz*step,(ix+1)*step,(iz+1)*step))
            parts=[cell] if cell.geom_type=='Polygon' else list(getattr(cell,'geoms',[]))
            for part in parts:
                if part.geom_type!='Polygon' or part.area<1e-11:continue
                for tri in constrained_delaunay_triangles(part).geoms:
                    p=list(tri.exterior.coords)[:3]
                    cross=(p[1][0]-p[0][0])*(p[2][1]-p[0][1])-(p[1][1]-p[0][1])*(p[2][0]-p[0][0])
                    if abs(cross)<1e-11:continue
                    if cross<0:p.reverse()
                    ids=tuple(index(q) for q in p);key=tuple(sorted(ids))
                    if len(set(ids))==3 and key not in seen:faces.append(ids);seen.add(key)
    edges={}
    for tri in faces:
        for a,b in zip(tri,tri[1:]+tri[:1]):edges.setdefault(tuple(sorted((a,b))),[]).append((a,b))
    if any(len(v)>2 for v in edges.values()):raise ValueError('Nonmanifold front surface')
    nextv={}
    for values in edges.values():
        if len(values)!=1:continue
        a,b=values[0]
        if a in nextv:raise ValueError('Split structural boundary')
        nextv[a]=b
    loops=[];vertices=np.array(vertices);fixed=np.zeros(len(vertices),dtype=bool)
    values=np.zeros((len(vertices),4))
    while nextv:
        start=min(nextv);ids=[];p=start
        while True:
            ids.append(p);p=nextv.pop(p)
            if p==start:break
        pts=vertices[ids];area=float((pts[:,0]*np.roll(pts[:,1],-1)-np.roll(pts[:,0],-1)*pts[:,1]).sum())
        if area>0:name='outer'
        else:name=min((n for n in profiles if n!='outer'),key=lambda n:np.linalg.norm(pts.mean(0)-profiles[n][0][:,[0,2]].mean(0)))
        front,rear=profiles[name]
        for i in ids:values[i]=boundary_value(vertices[i],front,rear);fixed[i]=True
        loops.append({'name':name,'indices':ids})
    if {l['name'] for l in loops}!=set(profiles):raise ValueError('Missing structural opening')
    pairs=np.array(list(edges));a=np.r_[pairs[:,0],pairs[:,1]];b=np.r_[pairs[:,1],pairs[:,0]]
    weights=1/np.maximum(.02,np.linalg.norm(vertices[a]-vertices[b],axis=1))
    denom=np.bincount(a,weights,minlength=len(vertices));values[~fixed]=values[fixed].mean(0)
    error=0
    for iteration in range(5000):
        new=np.column_stack([np.bincount(a,weights*values[b,k],minlength=len(vertices))/denom for k in range(4)])
        error=float(np.max(np.abs(new[~fixed]-values[~fixed]))) if (~fixed).any() else 0
        values[~fixed]=new[~fixed]
        if error<1e-8:break
    front=np.column_stack([vertices[:,0],values[:,0],vertices[:,1]])
    rear=np.column_stack([vertices[:,0]+values[:,1],values[:,2],vertices[:,1]+values[:,3]])
    if 'front_surface' in recipe:
        surface=recipe['front_surface'];x=front[:,0];z=front[:,2]
        def smooth(a,b,v):
            t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)
        shoulder=smooth(-4,1,x)
        living=(surface['living_depth_m']+surface['living_rise']*z+surface['living_plan_curve']*(x+4)**2
                +surface['shoulder_depth_m']*shoulder+surface['porch_rise_m']*shoulder*smooth(2,4,z))
        upper=surface['upper_depth_m']+surface['upper_rise']*(z-4.6)-surface['upper_plan_curve']*(x-4)**2
        blend=smooth(4,5.2,z);front[:,1]=living*(1-blend)+upper*blend
    # A manufactured rear ribbon uses one smooth support surface. Extending
    # unrelated boundary Y values harmonically caused ripples around the lips.
    if 'rear_surface' in recipe:
        surface=recipe['rear_surface']
        rear[:,1]=surface['depth_m']-surface['x_curvature']*rear[:,0]**2-surface['z_curvature']*(rear[:,2]-surface['centre_z_m'])**2
    return {'front':front.tolist(),'rear':rear.tolist(),'faces':faces,'loops':loops,
            'lip_radius_m':radius,'harmonic_iterations':iteration+1,'harmonic_residual_m':error,
            'method':'Independent 3D front/rear controls; harmonic ribbon faces and non-linear transverse lofts'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--recipe',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();data=build(json.loads(a.recipe.read_text()));a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(data,separators=(',',':'))+'\n')
    print('Master domain',len(data['front']),'vertices;',data['harmonic_iterations'],'iterations;',data['harmonic_residual_m'],'m residual')
