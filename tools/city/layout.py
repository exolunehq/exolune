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
        # The sea lies below 2 m. Until the engine exports its rivers, a site may state its
        # river surface in `<export>.json`; the planner keeps clear of both by `margin`.
        sidecar=self.path.with_name(self.path.name+'.json')
        self.meta=json.loads(sidecar.read_text(encoding='utf8')) if sidecar.exists() else {}
        self.water_level=max(2.0,float(self.meta.get('water_level_m',2.0)))
        self.wet_masks={}
        # A wider, coarser export of the same anchor carries what reaches beyond the site: the guideway's branches.
        self.region=None
        if self.meta.get('regional_export'):
            region=Terrain(self.meta['regional_export'])
            if (region.lat,region.lon,region.seed)!=(self.lat,self.lon,self.seed):raise ValueError('Regional export does not share the site anchor')
            self.region=region

    def wet(self,x,y,margin=10.0):
        """Water, or land within `margin` metres of water, at (x, y)."""
        if self.wet_masks.get('values') is not self.values:self.wet_masks={'values':self.values}
        mask=self.wet_masks.get(margin)
        if mask is None:
            mask=self.values<self.water_level
            for _ in range(int(math.ceil(margin/self.cell))):
                p=np.pad(mask,1);mask=np.logical_or.reduce([p[1+dy:1+dy+self.side,1+dx:1+dx+self.side] for dy in (-1,0,1) for dx in (-1,0,1)])
            self.wet_masks[margin]=mask
        ix=int(round(x/self.cell+self.side//2));iy=int(round(y/self.cell+self.side//2))
        if not 0<=ix<self.side or not 0<=iy<self.side:return True
        return bool(mask[iy,ix])

    def slope(self,x,y,radius):
        """Median ground slope (rise over run) within `radius` metres of (x, y)."""
        r=max(1,int(radius/self.cell));ix=int(x/self.cell+self.side//2);iy=int(y/self.cell+self.side//2)
        patch=self.values[max(0,iy-r):iy+r+1,max(0,ix-r):ix+r+1].astype('f8')
        if patch.shape[0]<3 or patch.shape[1]<3:return 1.0
        gy,gx=np.gradient(patch,self.cell);return float(np.median(np.hypot(gx,gy)))

    def height(self,x,y):
        """The ground at (x, y): the site's export, then the regional one around it; None beyond both."""
        for terrain in (self,self.region):
            if terrain is None:continue
            try:return terrain.sample(x,y)
            except ValueError:continue
        return None

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


# Built paths (docs/spec-ville-procedurale.md#ground-and-access): level across, PATH_LIFT above the highest graded
# ground across them, so the relief never shows through; a CURB_M stone curb along every edge; a SKIRT_M stone side
# down into the ground, so a path reads as a built course with its own thickness, not a strip laid on the slope.
PATH_LIFT,CURB_M,SKIRT_M=.15,.06,.35


def surface_mesh(terrain,surfaces,foundations=(),materials=None,cables=(),lines=(),piers=()):
    """Built paths and commons, crops on their terraces, then steps and cables (`foundations.py`).
    A path surface stands at its level (`lift` above it); a crop, which carries its angle as a fourth value, lies
    `lift` above its terrace with its UVs along it. `lines` are the paths' centre lines. Returns vertices,
    indices and the walkable index count: structure triangles follow the walkable ones."""
    import foundations as supports
    from shapely import STRtree
    from shapely.geometry.polygon import orient
    vertices=[];indices=[]
    edge_shape=None;turn=None;cache={}
    segments=[LineString([a,b]) for line in lines for a,b in zip(line,line[1:]) if math.dist(a,b)>1e-6]
    tree=STRtree(segments) if segments else None
    def level(x,y):
        """The highest graded ground across the path at (x, y), at its station on the nearest centre line, and
        0.8 m along it; plus the lift. A common far from any line takes the highest ground within 0.8 m."""
        key=(round(x,3),round(y,3))
        if key not in cache:
            heights=[terrain.sample(x,y)];point=Point(x,y)
            nearest=segments[int(tree.nearest(point))] if tree is not None else None
            if nearest is not None and nearest.distance(point)<3.5:
                (ax,ay),(bx,by)=nearest.coords;dx,dy=bx-ax,by-ay;length=math.hypot(dx,dy);dx/=length;dy/=length
                c=nearest.interpolate(nearest.project(point))
                heights+=[terrain.sample(c.x-dy*t,c.y+dx*t) for t in (-1.6,-.8,0,.8,1.6)]
                heights+=[terrain.sample(x+dx*t,y+dy*t) for t in (-.8,.8)]
            else:heights+=[terrain.sample(x+ox,y+oy) for ox,oy in ((.8,0),(-.8,0),(0,.8),(0,-.8))]
            cache[key]=max(heights)+PATH_LIFT
        return cache[key]
    def height(p,lift):
        return terrain.sample(*p)+lift if turn is not None else level(*p)+lift
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
        xyz=[(p[0],p[1],height(p,lift)) for p in [a,b,c]]
        n=np.cross(np.subtract(xyz[1],xyz[0]),np.subtract(xyz[2],xyz[0]));n/=max(float(np.linalg.norm(n)),1e-12)
        if n[2]<0:n=-n
        start=len(vertices)
        if turn is not None:
            c,s=math.cos(turn),math.sin(turn)
            vertices.extend([(*p,*n,(p[0]*c+p[1]*s)*.5,(p[1]*c-p[0]*s)*.5,material,1.0) for p in xyz])
        else:
            vertices.extend([(*p,*n,edge_shape.boundary.distance(Point(p[0],p[1])) if material==surfaces[0][1] else p[0]*.5,p[1]*.5,material,1.0) for p in xyz])
        indices.extend([start,start+1,start+2])
    rims=[]
    for shape,material,lift,*angle in surfaces:
        turn=angle[0] if angle else None
        pieces=list(shape.geoms) if hasattr(shape,'geoms') else [shape]
        for poly in pieces:
            if poly.is_empty:continue
            poly=poly.segmentize(2.8)
            edge_shape=poly
            tris=constrained_delaunay_triangles(poly)
            for tri in tris.geoms:
                a,b,c=list(tri.exterior.coords)[:3];triangle(a,b,c,material,lift)
            if turn is None and lift>=CURB_M:rims.append(orient(poly))
    mesh=supports.Mesh(vertices,indices)
    # The curb's rings: on the paths' outer edge a stone side down into the ground, on its inner edge the curb's step.
    inner=unary_union([shape for shape,_,lift,*angle in surfaces if not angle and lift<CURB_M])
    wall=(materials or {}).get('wall',surfaces[0][1])
    for poly in rims:
        for ring in [poly.exterior,*poly.interiors]:
            coords=list(ring.coords)
            mid=coords[len(coords)//2]
            step=inner.distance(Point(*mid))<.05
            for p,q in zip(coords,coords[1:]):
                dx,dy=q[0]-p[0],q[1]-p[1];length=math.hypot(dx,dy)
                if length<1e-6:continue
                out=(dy/length,-dx/length,0.0)
                top=[level(*p)+CURB_M,level(*q)+CURB_M]
                # The band's outward normal faces the lower path surface on its inner ring, the open ground on its outer.
                if step:mesh.face([(*p,level(*p)),(*q,level(*q)),(*q,top[1]),(*p,top[0])],out,wall)
                else:mesh.face([(*p,terrain.sample(*p)-SKIRT_M),(*q,terrain.sample(*q)-SKIRT_M),(*q,top[1]),(*p,top[0])],out,wall)
    supports.build(mesh,terrain,foundations,materials or {},cables,piers)
    walkable=len(indices)
    return np.asarray(vertices,dtype='<f4'),np.asarray(indices+mesh.structure,dtype='<u4'),walkable


def write_plan(out,report,surfaces,bits,terrain,grade):
    report['terrain_source']=str(terrain.path)
    vertices,indices,walkable=surface_mesh(terrain,surfaces,report['foundations'],report['foundation_materials'],report['cables'],
                                           report['road_lines']+report['access_lines'],report.get('pier_members',()))
    out.mkdir(parents=True,exist_ok=True)
    # The guideway's tree-free corridor beyond the land grid (CITYCOR1): segment count, half width, segments.
    corridor=report['transport'].get('corridor') or {}
    if corridor.get('segments'):
        with (out/'corridor.bin').open('wb') as f:
            f.write(struct.pack('<8sIf',b'CITYCOR1',len(corridor['segments']),corridor['half_width_m']))
            for segment in corridor['segments']:f.write(struct.pack('<4f',*segment))
    elif (out/'corridor.bin').exists():(out/'corridor.bin').unlink()
    # The engine grades its relief with the same pads (CityGrade.hlsli): one index cell per 32nd of the land grid.
    report['earthworks']['grading']=grade.write(out/'grading.bin',(-terrain.half,-terrain.half),terrain.half*2/32)
    # Version 4 appends the walkable index count: posts, beams, rails and walls follow it.
    with (out/'scene.bin').open('wb') as f:
        f.write(struct.pack('<8s2I2d3I4fI',b'CITYSCN1',4,terrain.seed,terrain.lat,terrain.lon,len(report['instances']),len(vertices),len(indices),*report['land_grid'],walkable))
        f.write(bits.tobytes())
        for p in report['instances']:f.write(struct.pack('<I5f',p['model'],*p['position'],p['yaw'],p['tint']))
        f.write(vertices.tobytes());f.write(indices.tobytes())
    report['street_triangles']=len(indices)//3;report['scene_sha256']=hashlib.sha256((out/'scene.bin').read_bytes()).hexdigest()
    report['planner_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report['composition_sha256']=hashlib.sha256(Path(__file__).with_name('settlement.py').read_bytes()).hexdigest()
    report['masterplan_sha256']=hashlib.sha256(Path(__file__).with_name('masterplan.py').read_bytes()).hexdigest()
    (out/'layout.json').write_text(json.dumps(report,indent=2)+'\n')
    # A compact standalone plan is functional evidence, not a beauty render.
    colours={'residential':'#bea87b','civic':'#d5824e','core':'#ca7e46','mixed':'#bc8664','garden':'#82a17a','food':'#b6bf77','arrival':'#69949c','transport':'#69949c','agriculture':'#80a36f','public':'#d6c7a9',
             'farm':'#b6bf77','cliff_foot':'#ca7e46','cliff_top':'#bea87b','cliff_face':'#bea87b'}
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
    report,surfaces,bits,grade=build_plan(terrain,library,args.seed)
    if not report['connected_pedestrian_network']:raise ValueError('Disconnected pedestrian network')
    if not any(p['zone'] in ['core','garden','mixed'] for p in report['instances']):raise ValueError('No supported residential parcels')
    write_plan(args.out,report,surfaces,bits,terrain,grade)
    print(json.dumps({'instances':len(report['instances']),'parcels':len(report['parcels']),
                      'rejected':len(report['rejected']),'street_triangles':report['street_triangles']},indent=2))


if __name__=='__main__':main()
