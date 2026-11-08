"""Shared garden habitats and manufactured paths on Exolune's own relief.

No imported city layout and no replacement terrain. Shapely performs polygon
unions so intersections share one road surface instead of overlapping ribbons.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import random
import struct
import sys
import numpy as np
sys.path.insert(0,'E:/ExoluneTools/city-python')
from shapely.geometry import Point,Polygon,LineString,box
from shapely.ops import unary_union,nearest_points
from shapely import constrained_delaunay_triangles
from shapely.affinity import rotate,translate


class Terrain:
    def __init__(self,path):
        self.path=Path(path).resolve()
        data=Path(path).read_bytes()
        magic,self.side,self.seed,self.lat,self.lon,self.cell=struct.unpack_from('<8s2I3d',data)
        if magic!=b'CITYGRD1' or len(data)!=40+self.side*self.side*4:raise ValueError('Invalid terrain export')
        self.values=np.frombuffer(data,dtype='<f4',offset=40).reshape(self.side,self.side)
        if not np.isfinite(self.values).all():raise ValueError('Nonfinite terrain')
        self.digest=hashlib.sha256(data).hexdigest();self.half=(self.side//2)*self.cell

    def sample(self,x,y):
        gx=x/self.cell+self.side//2;gy=y/self.cell+self.side//2
        ix=int(math.floor(gx));iy=int(math.floor(gy))
        if not 0<=ix<self.side-1 or not 0<=iy<self.side-1:raise ValueError('City exceeds sampled terrain')
        u=gx-ix;v=gy-iy;a,b=self.values[iy,ix:ix+2];c,d=self.values[iy+1,ix:ix+2]
        return float((a+(b-a)*u)*(1-v)+(c+(d-c)*u)*v)


def footprint(model,x,y,yaw,margin=1.2):
    lo,hi=model['bounds_z_up']
    shape=box(lo[0]-margin,lo[1]-margin,hi[0]+margin,hi[1]+margin)
    return translate(rotate(shape,math.degrees(yaw),origin=(0,0)),x,y)


def support(terrain,shape):
    x0,y0,x1,y1=shape.bounds
    heights=[]
    for y in np.linspace(y0,y1,max(3,math.ceil((y1-y0)/3))):
        for x in np.linspace(x0,x1,max(3,math.ceil((x1-x0)/3))):
            if shape.covers(Point(x,y)):heights.append(terrain.sample(x,y))
    for x,y in shape.exterior.coords:heights.append(terrain.sample(x,y))
    return min(heights),max(heights)


def build_plan(terrain,library,seed):
    from settlement import compose
    return compose(terrain,library,seed)


def surface_mesh(terrain,surfaces,foundations=(),foundation_material=0):
    vertices=[];indices=[]
    edge_shape=None
    def triangle(a,b,c,material,lift):
        # Boundary segmentation makes long narrow borders triangulate locally.
        # Bisect only the longest edge; four-way splitting wastes most vertices
        # across a 0.18 m stone course while trying to refine its length.
        edges=[math.dist(a,b),math.dist(b,c),math.dist(c,a)]
        if max(edges)>4.5:
            k=int(np.argmax(edges));p,q,r=[a,b,c][k:]+[a,b,c][:k]
            midpoint=tuple((p[i]+q[i])/2 for i in range(2))
            triangle(p,midpoint,r,material,lift);triangle(midpoint,q,r,material,lift)
            return
        xyz=[(p[0],p[1],terrain.sample(*p)+lift) for p in [a,b,c]]
        n=np.cross(np.subtract(xyz[1],xyz[0]),np.subtract(xyz[2],xyz[0]));n/=max(float(np.linalg.norm(n)),1e-12)
        if n[2]<0:n=-n
        start=len(vertices)
        vertices.extend([(*p,*n,edge_shape.boundary.distance(Point(p[0],p[1])) if material==surfaces[0][1] else p[0]*.5,p[1]*.5,material,1.0) for p in xyz]);indices.extend([start,start+1,start+2])
    for shape,material,lift in surfaces:
        pieces=list(shape.geoms) if hasattr(shape,'geoms') else [shape]
        for poly in pieces:
            if poly.is_empty:continue
            poly=poly.segmentize(2.8)
            edge_shape=poly
            tris=constrained_delaunay_triangles(poly)
            for tri in tris.geoms:
                a,b,c=list(tri.exterior.coords)[:3];triangle(a,b,c,material,lift)
    def face(points):
        n=np.cross(np.subtract(points[1],points[0]),np.subtract(points[2],points[0]));n/=max(float(np.linalg.norm(n)),1e-12)
        start=len(vertices)
        vertices.extend([(*p,*n,p[0]*.5,p[1]*.5,foundation_material,1.0) for p in points]);indices.extend([start,start+1,start+2])
    for foundation in foundations:
        shape=Polygon(foundation['outline']);top=foundation['top']
        for tri in constrained_delaunay_triangles(shape).geoms:
            face([(x,y,top) for x,y in list(tri.exterior.coords)[:3]])
        coords=list(shape.exterior.coords)
        for a,b in zip(coords,coords[1:]):
            for t0,t1 in zip(np.linspace(0,1,math.ceil(math.dist(a,b)/2)+1),np.linspace(0,1,math.ceil(math.dist(a,b)/2)+1)[1:]):
                p=tuple(a[k]+(b[k]-a[k])*t0 for k in range(2));q=tuple(a[k]+(b[k]-a[k])*t1 for k in range(2))
                bottom_p=terrain.sample(*p)-.15;bottom_q=terrain.sample(*q)-.15
                face([(*p,bottom_p),(*q,bottom_q),(*q,top)]);face([(*p,bottom_p),(*q,top),(*p,top)])
    return np.asarray(vertices,dtype='<f4'),np.asarray(indices,dtype='<u4')


def write_plan(out,report,surfaces,bits,terrain):
    report['terrain_source']=str(terrain.path)
    vertices,indices=surface_mesh(terrain,surfaces,report['foundations'],surfaces[1][1]);out.mkdir(parents=True,exist_ok=True)
    with (out/'scene.bin').open('wb') as f:
        f.write(struct.pack('<8s2I2d3I4f',b'CITYSCN1',3,terrain.seed,terrain.lat,terrain.lon,len(report['instances']),len(vertices),len(indices),*report['land_grid']))
        f.write(bits.tobytes())
        for p in report['instances']:f.write(struct.pack('<I5f',p['model'],*p['position'],p['yaw'],p['tint']))
        f.write(vertices.tobytes());f.write(indices.tobytes())
    report['street_triangles']=len(indices)//3;report['scene_sha256']=hashlib.sha256((out/'scene.bin').read_bytes()).hexdigest()
    report['planner_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report['composition_sha256']=hashlib.sha256(Path(__file__).with_name('settlement.py').read_bytes()).hexdigest()
    report['masterplan_sha256']=hashlib.sha256(Path(__file__).with_name('masterplan.py').read_bytes()).hexdigest()
    (out/'layout.json').write_text(json.dumps(report,indent=2)+'\n')
    # A compact standalone plan is functional evidence, not a beauty render.
    colours={'residential':'#bea87b','civic':'#d5824e','core':'#ca7e46','mixed':'#bc8664','garden':'#82a17a','food':'#b6bf77','arrival':'#69949c','transport':'#69949c','agriculture':'#80a36f','public':'#d6c7a9'}
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="-512 -512 1024 1024">','<rect x="-512" y="-512" width="1024" height="1024" fill="#142c28"/>','<g transform="scale(1,-1)">']
    for line in report['road_lines']:
        svg.append('<polyline points="'+' '.join(f'{x:.3f},{y:.3f}' for x,y in line)+'" fill="none" stroke="#617b73" stroke-width="2.7" stroke-linejoin="round"/>')
    for p in report['instances']:
        x,y,_=p['position'];r=4 if p['zone']=='public' else 3 if p['id']=='growing_bed' else 6
        svg.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{r}" fill="{colours[p["zone"]]}"/>')
    for polygon in report['parcels']:svg.append('<polygon points="'+' '.join(f'{x:.3f},{y:.3f}' for x,y in polygon)+'" fill="none" stroke="#d6c7a9" stroke-width=".5"/>')
    svg.append('</g></svg>');(out/'plan.svg').write_text('\n'.join(svg))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--terrain',type=Path,required=True);parser.add_argument('--library',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--seed',type=int,default=11072026)
    args=parser.parse_args();terrain=Terrain(args.terrain);library=json.loads(args.library.read_text())
    report,surfaces,bits=build_plan(terrain,library,args.seed)
    if not report['connected_pedestrian_network']:raise ValueError('Disconnected pedestrian network')
    if not any(p['zone'] in ['core','garden','mixed'] for p in report['instances']):raise ValueError('No supported residential parcels')
    write_plan(args.out,report,surfaces,bits,terrain)
    print(json.dumps({'instances':len(report['instances']),'parcels':len(report['parcels']),
                      'rejected':len(report['rejected']),'street_triangles':report['street_triangles']},indent=2))


if __name__=='__main__':main()
