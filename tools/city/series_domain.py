"""CPU parameter domains for connected public-building shells."""
import argparse
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,'E:/ExoluneTools/city-python')
from shapely.geometry import Polygon,box
from shapely import constrained_delaunay_triangles
from reference_house_domain import build as house_domain


def civic(asset):
    p=asset['parameters'];sx=p['width'];sz=p['height'];depth=p['depth_m']
    outlines={
        'outer':[[-15.7,-.35],[-17,1.7],[-16.4,6.3],[-12.5,8.8],[-8.4,9.1],[-5.3,8.6],[-2.8,10.5],[1.2,13.2],[5.6,13.5],[8.8,11.4],[8.2,8.5],[12.5,8.1],[16.4,6.0],[17.1,2.4],[15.9,-.35],[8,-.40],[0,-.40],[-8,-.40]],
        'left':[[-15.0,.48],[-16.0,1.8],[-15.55,5.6],[-12.3,7.8],[-9.2,8.15],[-6.6,7.45],[-4.9,4.4],[-5.2,.45],[-10,.43]],
        'forum':[[-3.8,.46],[-4.05,3.1],[-3.5,6.4],[-1.0,10.25],[2.1,12.25],[5.2,12.1],[7.3,10.3],[5.9,6.1],[5.4,2.8],[5.6,.45],[.8,.43]],
        'right':[[7.1,.45],[6.9,2.2],[8.0,5.2],[10.2,7.2],[12.7,7.25],[15.55,5.15],[16.0,1.7],[15.0,.45],[10.5,.43]]}
    profiles={}
    for name,points in outlines.items():
        front=[];rear=[]
        for x,z in points:
            lift=p.get('left_lift',0)*math.exp(-((x+10)/5)**2)
            xx=x*sx;zz=z*sz*(1+lift)
            front.append([xx,-3,zz]);rear.append([xx*.93,depth*.5,zz*.97])
        profiles[name]={'front':front,'rear':rear,'samples':200 if name=='outer' else 120}
    config={'profiles':profiles,'face_grid_m':.32,'lip_radius_m':.10,
            'shape_controls':{'roof_camber_m':.85,'soffit_camber_m':.32}}
    domain=house_domain(config)
    for x in domain['front']:
        xx=x[0]/sx
        x[1]=-3.0-2*math.exp(-((xx+10)/5)**2)-1.3*math.exp(-((xx-11)/4)**2)+.08*(x[2]-4)
    for x in domain['rear']:x[1]=depth*.5-.004*x[0]**2-.004*(x[2]-6)**2
    return {'domain':domain,'config':config}


def parameter_mesh(shape,step=.025):
    vertices=[];faces=[];lookup={};seen=set()
    def index(point):
        key=tuple(round(v,8) for v in point)
        if key not in lookup:lookup[key]=len(vertices);vertices.append(key)
        return lookup[key]
    for iy in range(math.ceil(1/step)):
        for ix in range(math.ceil(1/step)):
            cell=shape.intersection(box(ix*step,iy*step,(ix+1)*step,(iy+1)*step))
            parts=[cell] if cell.geom_type=='Polygon' else list(getattr(cell,'geoms',[]))
            for part in parts:
                if part.geom_type!='Polygon' or part.area<1e-12:continue
                for triangle in constrained_delaunay_triangles(part).geoms:
                    points=list(triangle.exterior.coords)[:3]
                    a,b,c=points;cross=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
                    if abs(cross)<1e-13:continue
                    if cross<0:points.reverse()
                    ids=tuple(index(p) for p in points);key=tuple(sorted(ids))
                    if key not in seen:faces.append(ids);seen.add(key)
    edges={}
    for face in faces:
        for a,b in zip(face,face[1:]+face[:1]):edges.setdefault(tuple(sorted((a,b))),[]).append((a,b))
    if any(len(v)>2 for v in edges.values()):raise ValueError('Nonmanifold parameter domain')
    return {'vertices':vertices,'faces':faces,'boundary':[v[0] for v in edges.values() if len(v)==1]}


def greenhouse(asset):
    count=asset['parameters']['length_bays'];holes=[]
    spans=[(.025,.175),(.19,.345),(.36,.455),(.555,.695),(.71,.845),(.86,.975)]
    for u0,u1 in spans:
        for j in range(count):
            v0=.04+.92*j/count+.007;v1=.04+.92*(j+1)/count-.007
            holes.append([u0,v0,u1,v1])
    shape=box(0,0,1,1)
    for h in holes:shape=shape.difference(box(*h))
    if shape.geom_type!='Polygon' or not shape.is_valid:raise ValueError('Disconnected greenhouse frame')
    return {'frame':parameter_mesh(shape,.02),'panes':[parameter_mesh(box(*h),.035) for h in holes]}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recipe',type=Path,required=True);p.add_argument('--asset',required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();recipe=json.loads(a.recipe.read_text(encoding='utf-8'));asset=next(i for i in recipe['assets'] if i['id']==a.asset)
    data=civic(asset) if asset['family']=='civic' else greenhouse(asset)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(data,separators=(',',':'))+'\n')
