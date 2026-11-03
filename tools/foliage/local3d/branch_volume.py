"""Reject planar woody masters before foliage, LOD and variant production.

Measure the upper wood with triangle-area weights. Roots and leaf bouquets
cannot conceal a flat supporting structure; PCA makes the result independent
of the tree's horizontal orientation and UV seam vertex duplication.
"""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np


def measure(triangles,max_ratio=3.0):
    triangles=np.asarray(triangles,dtype=np.float64)
    if triangles.ndim!=3 or triangles.shape[1:]!=(3,3) or not len(triangles) or not np.isfinite(triangles).all():
        raise ValueError('Expected finite woody triangles in the Y-up frame')
    floor=float(triangles[:,:,1].min());height=float(np.ptp(triangles[:,:,1]))
    if height<=1e-8:raise ValueError('Woody master has no height')
    cutoff=floor+.35*height
    # Clip crossing faces at the same plane, rather than admitting them by
    # their centroids. Large trunk triangles and finer tessellations then
    # measure the exact same upper surface.
    inside=triangles[:,:,1]>=cutoff;counts=inside.sum(1)
    pieces=[triangles[counts==3]]
    for count in [1,2]:
        faces=triangles[counts==count];mask=inside[counts==count]
        if not len(faces):continue
        index=np.argmax(mask if count==1 else ~mask,axis=1);rows=np.arange(len(faces))
        p=faces[rows,index];a=faces[rows,(index+1)%3];b=faces[rows,(index+2)%3]
        ea=p+(a-p)*((cutoff-p[:,1])/(a[:,1]-p[:,1]))[:,None]
        eb=p+(b-p)*((cutoff-p[:,1])/(b[:,1]-p[:,1]))[:,None]
        if count==1:pieces.append(np.stack([p,ea,eb],axis=1))
        else:pieces.extend([np.stack([a,b,eb],axis=1),np.stack([a,eb,ea],axis=1)])
    selected=np.concatenate(pieces)
    areas=np.linalg.norm(np.cross(selected[:,1]-selected[:,0],selected[:,2]-selected[:,0]),axis=1)*.5
    valid=areas>height*height*1e-12;selected=selected[valid];areas=areas[valid]
    if len(selected)<4:raise ValueError('Insufficient upper wood for volume validation')
    xz=selected[:,:,[0,2]]
    centre=np.average(xz.mean(1),axis=0,weights=areas);local=xz-centre
    sums=local.sum(1)
    # Exact second moment of uniformly sampled triangle surfaces, rather
    # than a vertex histogram whose answer changes with tessellation.
    moments=(np.einsum('nki,nkj->nij',local,local)+np.einsum('ni,nj->nij',sums,sums))/12
    covariance=np.average(moments,axis=0,weights=areas)
    eigenvalues,axes=np.linalg.eigh(covariance)
    projected=local.reshape(-1,2)@axes;spans=np.ptp(projected,axis=0)
    extent_ratio=float(spans.max()/max(spans.min(),height*1e-10))
    spread_ratio=float(np.sqrt(max(eigenvalues[-1],0)/max(eigenvalues[0],height*height*1e-20)))
    return {'status':'pass' if max(extent_ratio,spread_ratio)<=max_ratio else 'fail',
            'method':'Upper woody surface; area-weighted horizontal PCA and oriented spans',
            'root_exclusion_fraction':.35,'cutoff_y':cutoff,'woody_height':height,
            'principal_horizontal_spans':spans.tolist(),'extent_ratio':extent_ratio,
            'surface_spread_ratio':spread_ratio,'maximum_ratio':max_ratio,
            'selected_triangles':len(selected),'art_acceptance':'Separate multi-view review remains required'}


def inspect(path):
    from audit import read_glb,array
    path=Path(path);doc,blob=read_glb(path);parts=[]
    for node in doc.get('nodes',[]):
        if 'mesh' in node and any(k in node for k in ['matrix','translation','rotation','scale','skin']):
            raise ValueError('Inspect the assembled master after baking node transforms')
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            if doc['materials'][primitive['material']].get('alphaMode')=='MASK':continue
            v=array(doc,blob,primitive['attributes']['POSITION'])
            i=array(doc,blob,primitive['indices']).reshape(-1,3);parts.append(v[i])
    if not parts:raise ValueError('No wood in this master')
    result=measure(np.concatenate(parts))
    result.update(source=str(path.resolve()),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  auditor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('asset',type=Path)
    parser.add_argument('--out',type=Path);args=parser.parse_args();result=inspect(args.asset)
    text=json.dumps(result,indent=2)
    if args.out:args.out.write_text(text+'\n',encoding='utf-8')
    print(text)
    raise SystemExit(0 if result['status']=='pass' else 2)
