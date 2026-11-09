"""Triangulate one architectural face with true apertures and shared junctions.

This CPU stage partitions a single polygonal domain before triangulation. It
never joins disconnected object names or masks intersections with smoothing.
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


def spline(knots,count):
    points=np.asarray(knots,dtype=float);result=[]
    for j in range(count):
        t=j*len(points)/count;k=int(t);t-=k
        p,q,r,s=[points[i%len(points)] for i in (k-1,k,k+1,k+2)]
        result.append(((2*q+(-p+r)*t+(2*p-5*q+4*r-s)*t*t+(-p+3*q-3*r+s)*t*t*t)*.5).tolist())
    return result


def mapped(points,asset):
    result=[]
    for x,z in points:
        t=min(1,max(0,(z-3.8)/2));weight=t*t*(3-2*t)
        result.append([x+asset['upper_extension']*weight*max(0,x+1),
                       z+asset['crown_rise']*max(0,z-3.8)])
    return result


def door(asset):
    x=asset['entry_x'];z=asset['entry_z'];w=.84;h=2.55;r=.34
    points=[(x-w,z),(x+w,z),(x+w,z+h-r)]
    for k in range(1,9):
        t=k*math.pi/16;points.append((x+w-r+r*math.cos(t),z+h-r+r*math.sin(t)))
    for k in range(9):
        t=math.pi/2+k*math.pi/16;points.append((x-w+r+r*math.cos(t),z+h-r+r*math.sin(t)))
    return points


def build(config,asset):
    structure=config['structure'];step=structure['grid_m'];radius=structure['edge_radius_m']
    outer=mapped(spline(structure['outer'],240),asset)
    holes={name:mapped(spline(points,96),asset) for name,points in structure['openings'].items()}
    holes['entry']=door(asset)
    boundary=Polygon(outer)
    for name,points in holes.items():
        shape=Polygon(points)
        if not shape.is_valid or not boundary.contains(shape):raise ValueError('Invalid architectural aperture: '+name)
    domain=Polygon(outer,list(holes.values()))
    if not domain.is_valid:raise ValueError('Intersecting openings in structural domain')
    face=domain.buffer(-radius,quad_segs=3).simplify(.001,preserve_topology=True)
    if face.geom_type!='Polygon' or len(face.interiors)!=len(holes):raise ValueError('Wall or junction thinner than its edge radius')
    vertices=[];triangles=[];lookup={};seen=set()
    def index(p):
        key=tuple(round(v,6) for v in p)
        if key not in lookup:lookup[key]=len(vertices);vertices.append(list(key))
        return lookup[key]
    x0,z0,x1,z1=face.bounds
    for iz in range(math.floor(z0/step),math.ceil(z1/step)):
        for ix in range(math.floor(x0/step),math.ceil(x1/step)):
            cell=face.intersection(box(ix*step,iz*step,(ix+1)*step,(iz+1)*step))
            if cell.is_empty:continue
            parts=[cell] if cell.geom_type=='Polygon' else list(getattr(cell,'geoms',[]))
            for part in parts:
                if part.geom_type!='Polygon' or part.area<1e-10:continue
                for tri in constrained_delaunay_triangles(part).geoms:
                    points=list(tri.exterior.coords)[:3]
                    area=np.cross(np.subtract(points[1],points[0]),np.subtract(points[2],points[0])).item()
                    if abs(area)<1e-10:continue
                    if area<0:points.reverse()
                    ids=tuple(index(p) for p in points)
                    if len(set(ids))<3:continue
                    key=tuple(sorted(ids))
                    if key not in seen:triangles.append(ids);seen.add(key)
    # The triangulation owns its final boundary, including grid intersections.
    # Reuse these exact vertices for the wall lofts; no T-junction tolerance.
    edges={}
    for tri in triangles:
        for p,q in zip(tri,tri[1:]+tri[:1]):edges.setdefault(tuple(sorted((p,q))),[]).append((p,q))
    if any(len(v)>2 for v in edges.values()):raise ValueError('Nonmanifold face triangulation')
    border=[v[0] for v in edges.values() if len(v)==1];next_vertex={}
    for p,q in border:
        if p in next_vertex:raise ValueError('Split boundary in constrained triangulation')
        next_vertex[p]=q
    loops=[]
    while next_vertex:
        start=min(next_vertex);loop=[];p=start
        while True:
            loop.append(p);p=next_vertex.pop(p)
            if p==start:break
        loops.append(loop)
    if len(loops)!=len(holes)+1:raise ValueError('Unexpected face boundary count')
    records=[]
    for loop in loops:
        points=np.asarray([vertices[i] for i in loop]);area=float(np.sum(points[:,0]*np.roll(points[:,1],-1)-np.roll(points[:,0],-1)*points[:,1])*.5)
        if area>0:name='outer'
        else:
            centre=points.mean(0)
            name=min(holes,key=lambda key:np.linalg.norm(centre-np.mean(holes[key],axis=0)))
        records.append({'name':name,'indices':loop,'signed_area':area})
    if {r['name'] for r in records}!={'outer',*holes}:raise ValueError('Aperture attribution failed')
    return {'vertices_xz':vertices,'triangles':triangles,'boundaries':records,'apertures':holes,
            'grid_m':step,'edge_radius_m':radius,'face_area_m2':face.area,
            'structural_components':1,'aperture_count':len(holes),'asset':asset}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recipe',type=Path,required=True)
    p.add_argument('--asset',required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();config=json.loads(a.recipe.read_text());asset=next(p for p in config['assets'] if p['id']==a.asset)
    result=build(config,asset);a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print('Continuous domain:',len(result['vertices_xz']),'vertices,',len(result['triangles']),'triangles,',len(result['boundaries']),'boundaries')


if __name__=='__main__':main()
