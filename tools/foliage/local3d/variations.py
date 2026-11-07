"""Derive deterministic structural plant variants without another AI inference.

The lower fifth stays fixed. Bounded vertical warping, crown spread, shear,
twist and lean change branch directions while preserving connectivity, UVs,
materials and attachment data. Each output needs its own native cook/review.
This does not invent branch forks or repair an invalid botanical master.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import struct
import numpy as np
from audit import array, read_glb, check


PROFILES={
    'compact': {'spread':[.82,.90], 'lift':.22, 'twist':.12, 'lean':.015, 'shear':.08},
    'spreading': {'spread':[1.16,1.08], 'lift':-.24, 'twist':-.16, 'lean':.022, 'shear':-.12},
    'windshaped': {'spread':[1.07,.91], 'lift':.10, 'twist':.22, 'lean':.065, 'shear':.14},
}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parameters(profile,seed):
    if profile not in PROFILES:raise ValueError('Unknown structural profile: '+profile)
    rng=np.random.default_rng(seed);p=PROFILES[profile]
    return {'profile':profile,'seed':seed,'fixed_fraction':.20,
            'spread':[float(v*rng.uniform(.98,1.02)) for v in p['spread']],
            'lift':p['lift'],'twist':p['twist'],'lean':p['lean'],
            'shear':p['shear'],'azimuth':float(rng.uniform(0,math.tau))}


def deform(points,p,frame):
    """Composition of three injective maps on the master's bounded domain.

    Y warp is monotone for each XZ (dy'/dy >= 1 - 1.5*abs(lift)).
    Each new horizontal slice then has an invertible shear, positive scaling
    and rotation. Roots and total height remain fixed, with smooth endpoints.
    """
    if not 0<=p['fixed_fraction']<1 or abs(p['lift'])>.30:
        raise ValueError('Unbounded vertical warp')
    if any(not .7<=v<=1.3 for v in p['spread']) or abs(p['shear'])>.2 or abs(p['twist'])>.3 or abs(p['lean'])>.08:
        raise ValueError('Unbounded crown variation')
    q=np.asarray(points,dtype=np.float64)-np.array(frame['origin'])
    height=frame['height'];radius=frame['radius'];a=p['fixed_fraction']
    t=np.clip((q[:,1]/height-a)/(1-a),0,1);s=t*t*(3-2*t)
    radial=q[:,0]**2+q[:,2]**2
    q[:,1]+=height*p['lift']*(1-a)*s*(1-s)*radial/(radius*radius+radial)
    t=np.clip((q[:,1]/height-a)/(1-a),0,1);s=t*t*(3-2*t)
    angle=p['azimuth'];c=math.cos(angle);sn=math.sin(angle)
    x=c*q[:,0]+sn*q[:,2];z=-sn*q[:,0]+c*q[:,2]
    x+=p['shear']*s*radius*np.tanh(z/radius)
    x*=np.exp(s*np.log(p['spread'][0]));z*=np.exp(s*np.log(p['spread'][1]))
    theta=p['twist']*s;ct=np.cos(theta);st=np.sin(theta)
    xx=ct*x-st*z;zz=st*x+ct*z
    q[:,0]=c*xx-sn*zz+height*p['lean']*s*s*c
    q[:,2]=sn*xx+c*zz+height*p['lean']*s*s*sn
    result=q+np.array(frame['origin'])
    fixed=points[:,1]<=frame['origin'][1]+height*a
    result[fixed]=points[fixed] # exact root/attachment preservation
    return result


def jacobian(points,p,frame):
    step=frame['height']*1e-5;columns=[]
    for axis in range(3):
        delta=np.zeros(3);delta[axis]=step
        columns.append((deform(points+delta,p,frame)-deform(points-delta,p,frame))/(2*step))
    return np.stack(columns,axis=2)


def write_glb(path,doc,blob):
    encoded=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    encoded+=b' '*((-len(encoded))%4);blob=bytes(blob)+b'\0'*((-len(blob))%4)
    path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(encoded)+len(blob))+
                     struct.pack('<II',len(encoded),0x4e4f534a)+encoded+
                     struct.pack('<II',len(blob),0x004e4942)+blob)


def derive(source,out,profile,seed,budget=40000):
    source=Path(source).resolve();out=Path(out).resolve()
    if out.exists():raise ValueError('Use a fresh structural variant path')
    master_sha=sha(source);doc,raw=read_glb(source);blob=bytearray(raw)
    if doc.get('animations') or doc.get('skins') or doc.get('extensionsRequired'):
        raise ValueError('Structural variations require an unpacked static plant')
    used=[]
    for node in doc.get('nodes',[]):
        if 'mesh' not in node:continue
        if any(k in node for k in ['matrix','translation','rotation','scale','skin']):
            raise ValueError('Bake node transforms before deriving structural variants')
        used.append(node['mesh'])
    if len(used)!=len(set(used)) or set(used)!=set(range(len(doc['meshes']))):
        raise ValueError('Expected one identity node per source mesh')
    primitives=[prim for mesh in doc['meshes'] for prim in mesh['primitives']]
    if any(prim.get('targets') or prim.get('mode',4)!=4 for prim in primitives):
        raise ValueError('Expected static triangle primitives')
    original={i:array(doc,raw,i).copy() for i in range(len(doc['accessors']))}
    points=np.concatenate([original[prim['attributes']['POSITION']] for prim in primitives])
    low=points.min(0);high=points.max(0);height=float(high[1]-low[1])
    check(source,budget,float(high[1]))
    wood=np.concatenate([original[prim['attributes']['POSITION']] for prim in primitives
                         if doc['materials'][prim['material']].get('alphaMode')!='MASK'])
    band=wood[(wood[:,1]>low[1]+height*.06)&(wood[:,1]<low[1]+height*.18)]
    if not len(band):raise ValueError('Master has no root collar')
    origin=[float(np.median(band[:,0])),float(low[1]),float(np.median(band[:,2]))]
    frame={'origin':origin,'height':height,'radius':float(np.linalg.norm(points[:,[0,2]]-np.array(origin)[[0,2]],axis=1).max())}
    if frame['radius']<height*.01:raise ValueError('Invalid plant width')
    p=parameters(profile,seed);changed={};determinants=[];displacements=[]
    def put(index,value):
        if index in changed:
            if not np.allclose(changed[index],value,atol=1e-6):raise ValueError('Incompatible shared accessor')
            return
        accessor=doc['accessors'][index]
        if accessor['componentType']!=5126 or accessor.get('sparse') or accessor.get('normalized'):
            raise ValueError('Mutable source attributes must be unpacked float32')
        target=array(doc,blob,index);target[:]=value
        accessor['min']=target.min(0).astype(float).tolist();accessor['max']=target.max(0).astype(float).tolist()
        changed[index]=value
    for prim in primitives:
        a=prim['attributes'];position=original[a['POSITION']].astype(float)
        j=jacobian(position,p,frame);det=np.linalg.det(j)
        if not np.isfinite(j).all() or det.min()<.20:raise ValueError('Structural variation folds or collapses geometry')
        determinants.append(float(det.min()))
        moved=deform(position,p,frame);put(a['POSITION'],moved)
        displacements.append(np.linalg.norm(moved-position,axis=1))
        normal=original[a['NORMAL']].astype(float)
        normal=np.linalg.solve(j.transpose(0,2,1),normal[:,:,None])[:,:,0]
        normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12);put(a['NORMAL'],normal)
        tangent=original[a['TANGENT']].astype(float)
        direction=np.einsum('nij,nj->ni',j,tangent[:,:3]);direction-=normal*np.sum(normal*direction,axis=1,keepdims=True)
        direction/=np.maximum(np.linalg.norm(direction,axis=1,keepdims=True),1e-12);tangent[:,:3]=direction
        put(a['TANGENT'],tangent)
        for name in ['_WIND_PIVOT','_LEAF_PIVOT']:
            if name in a:put(a[name],deform(original[a[name]],p,frame))
    # UVs, index connectivity, vertex colour, weights/phases and images are
    # copied byte for byte. Only positions, normal frames and pivots change.
    for index,value in original.items():
        if index not in changed and not np.array_equal(array(doc,blob,index),value):
            raise ValueError('Structural variation changed an immutable attribute')
    doc.setdefault('asset',{}).setdefault('extras',{})['exolune_structural_variant']={'master_sha256':master_sha,'parameters':p,'frame':frame}
    out.parent.mkdir(parents=True,exist_ok=True);temporary=out.with_suffix('.tmp.glb')
    try:
        write_glb(temporary,doc,blob);audit=check(temporary,budget,float(high[1]));temporary.replace(out)
    finally:
        if temporary.exists():temporary.unlink()
    audit['file']=str(out)
    report={'status':'derived; new cook, impostor and native acceptance required','master':str(source),'master_sha256':master_sha,
            'output':str(out),'sha256':sha(out),'script_sha256':sha(__file__),'parameters':p,'frame':frame,
            'triangles':audit['triangles'],'vertices':audit['vertices'],'minimum_sampled_jacobian':min(determinants),
            'max_displacement_m':float(max(d.max() for d in displacements)),
            'root_zone':'lower 20 percent unchanged exactly','connectivity':'unchanged; no new forks or branch pruning',
            'preserved':'UVs, indices, embedded images, materials, colours, wind weights and phases',
            'source_art_acceptance_inherited':False,'production_ready':False,'audit':audit}
    out.with_suffix('.variation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if sha(source)!=master_sha:raise ValueError('Master changed during derivation')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--profile',choices=list(PROFILES),required=True);parser.add_argument('--seed',type=int,default=424242)
    parser.add_argument('--budget',type=int,default=40000);args=parser.parse_args()
    if args.out.resolve().drive.lower()!='e:':raise ValueError('Generated variants belong on E:')
    print(json.dumps(derive(args.source,args.out,args.profile,args.seed,args.budget),indent=2))
