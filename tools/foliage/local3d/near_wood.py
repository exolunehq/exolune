"""Bounded PN refinement of close wood; keep the authored master and far LODs.

This adds curvature guided by the source normals. It cannot invent missing
branches or high-frequency sculpt detail. Original vertices and root support
heights stay fixed. Shared geometric edges retain identical UV-seam positions.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import numpy as np


def refine(vertices, indices, light, extra, leaf_mask):
    vertices=np.asarray(vertices,dtype='<f4');faces=np.asarray(indices).reshape(-1,3)
    # Area-weighted coincident normals define geometry, independently of UV seams.
    _,keys=np.unique(np.round(vertices[:,:3],6),axis=0,return_inverse=True)
    keys=keys.reshape(-1);woody=((leaf_mask>>vertices[:,8].astype(int))&1)==0
    normal=np.zeros((int(keys.max())+1,3))
    wood_faces=faces[woody[faces].all(1)]
    area=np.linalg.norm(np.cross(vertices[wood_faces[:,1],:3]-vertices[wood_faces[:,0],:3],
                                 vertices[wood_faces[:,2],:3]-vertices[wood_faces[:,0],:3]),axis=1)
    for corner in range(3):np.add.at(normal,keys[wood_faces[:,corner]],vertices[wood_faces[:,corner],3:6]*area[:,None])
    normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12)
    marked={};lo=vertices[:,:3].min(0);hi=vertices[:,:3].max(0)
    excluded=set();root_edges=set()
    for face in wood_faces:
        if vertices[face,1].max()>=.68 or vertices[face,1].max()<=.002:
            for a,b in zip(face,np.roll(face,-1)):excluded.add(tuple(sorted((int(keys[a]),int(keys[b])))))
        if vertices[face,1].min()<.18 or np.any(np.mod(vertices[face,8],1)>.125):
            for a,b in zip(face,np.roll(face,-1)):root_edges.add(tuple(sorted((int(keys[a]),int(keys[b])))))
    for face in wood_faces:
        for a,b in zip(face,np.roll(face,-1)):
            edge=tuple(sorted((int(keys[a]),int(keys[b]))))
            if edge in marked or edge in excluded:continue
            p,q=vertices[a,:3],vertices[b,:3];mid=(p+q)*.5
            if max(p[1],q[1])>=.68:continue
            length=float(np.linalg.norm(q-p))
            if length<=.008:continue
            na,nb=normal[keys[a]],normal[keys[b]]
            delta=-.25*(na*np.dot(mid-p,na)+nb*np.dot(mid-q,nb))
            if edge in root_edges:delta[1]=0.0
            amount=float(np.linalg.norm(delta))
            if amount<1e-5:continue
            delta*=min(1.,min(.001 if edge in root_edges else .005,.12*length)/max(amount,1e-12))
            marked[edge]=np.clip(mid+delta,lo,hi)
    # One selected interior edge adds at most six triangles. Rank curvature,
    # then cap the added work independently of total leaf density.
    budget=max(0,min(20000,100000-len(indices)//3))
    if len(marked)>budget//6:
        points={int(k):vertices[j,:3] for j,k in enumerate(keys)}
        score=lambda edge:float(np.linalg.norm(marked[edge]-(points[edge[0]]+points[edge[1]])*.5))/max(.06,float((points[edge[0]][1]+points[edge[1]][1])*.5)+.06)
        marked={edge:marked[edge] for edge in sorted(marked,key=score,reverse=True)[:budget//6]}
    vs=[row.copy() for row in vertices];linear=[row[:3].copy() for row in vertices]
    ls=[row.copy() for row in light];es=[row.copy() for row in extra]
    mids={};output=[];parents=[];changed=[];max_displacement=0.;refined_faces=0
    def append(ids,weights,position):
        v=np.average(vertices[ids],axis=0,weights=weights);v[:3]=position
        v[3:6]/=max(float(np.linalg.norm(v[3:6])),1e-12)
        # Preserve material/root flags exactly, rather than interpolating integers.
        v[8]=vertices[ids[0],8]
        result=len(vs);vs.append(v);linear.append(np.average(vertices[ids,:3],axis=0,weights=weights))
        ls.append(np.average(light[ids],axis=0,weights=weights));es.append(np.average(extra[ids],axis=0,weights=weights))
        return result
    for face in faces:
        source_cross=np.cross(vertices[face[1],:3]-vertices[face[0],:3],vertices[face[2],:3]-vertices[face[0],:3])
        edge_keys=[tuple(sorted((int(keys[a]),int(keys[b])))) for a,b in zip(face,np.roll(face,-1))]
        if not woody[face].all() or not any(edge in marked for edge in edge_keys):
            output.append(face.tolist());parents.append(source_cross);changed.append(False);continue
        polygon=[]
        for a,b,edge in zip(face,np.roll(face,-1),edge_keys):
            polygon.append(int(a))
            if edge in marked:
                seam=tuple(sorted((int(a),int(b))))
                if seam not in mids:mids[seam]=append([a,b],[1,1],marked[edge])
                polygon.append(mids[seam])
                max_displacement=max(max_displacement,float(np.linalg.norm(marked[edge]-(vertices[a,:3]+vertices[b,:3])*.5)))
        p=vertices[face,:3];n=normal[keys[face]];centre=p.mean(0)
        controls=[]
        for a,b in [(0,1),(1,0),(1,2),(2,1),(2,0),(0,2)]:
            controls.append((2*p[a]+p[b]-np.dot(p[b]-p[a],n[a])*n[a])/3)
        e=np.mean(controls,axis=0);b111=e+(e-centre)*.5
        pn=p.sum(0)/27+np.sum(controls,axis=0)/9+b111*(2/9)
        delta=pn-centre;radius=min(.005,.12*float(np.max(np.linalg.norm(p-np.roll(p,1,axis=0),axis=1))))
        if p[:,1].min()<.18 or np.any(np.mod(vertices[face,8],1)>.125):
            delta[1]=0.0;radius=min(radius,.001)
        delta*=min(1.,radius/max(float(np.linalg.norm(delta)),1e-12))
        centre_id=append(face,[1,1,1],np.clip(centre+delta,lo,hi))
        for a,b in zip(polygon,np.roll(polygon,-1)):
            output.append([centre_id,int(a),int(b)]);parents.append(source_cross);changed.append(True)
        refined_faces+=1;max_displacement=max(max_displacement,float(np.linalg.norm(delta)))
    v=np.asarray(vs,dtype='<f4');i=np.asarray(output,dtype='<u4').reshape(-1)
    valid=np.asarray(changed)&(np.linalg.norm(parents,axis=1)>1e-12)
    linear=np.asarray(linear,dtype='<f4');delta=v[len(vertices):,:3]-linear[len(vertices):]
    # Limit curvature locally on thin/sliver source triangles. All coincident
    # UV-chart copies share that limit, so a repaired face cannot open a seam.
    _,groups=np.unique(np.round(linear[len(vertices):],6),axis=0,return_inverse=True)
    groups=groups.reshape(-1);scales=np.ones(int(groups.max())+1) if len(groups) else np.ones(0)
    for iteration in range(18):
        q=v[i.reshape(-1,3),:3];cross=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0])
        bad=valid&(np.sum(cross*np.asarray(parents),axis=1)<=0)
        if not bad.any():break
        touched=np.unique(i.reshape(-1,3)[bad]);touched=touched[touched>=len(vertices)]-len(vertices)
        affected=np.unique(groups[touched]);scales[affected]=scales[affected]*.5 if iteration<15 else 0
        v[len(vertices):,:3]=linear[len(vertices):]+delta*scales[groups,None]
    else:raise ValueError('A close woody triangle remains folded after bounded curvature reduction')
    max_displacement=float(np.linalg.norm(v[len(vertices):,:3]-linear[len(vertices):],axis=1).max()) if len(delta) else 0.
    assert np.array_equal(v[:len(vertices)],vertices),'Source vertices or root data changed'
    assert len(i)//3-len(indices)//3<=budget,'Close wood refinement exceeds its bounded geometry budget'
    report={'method':'Adaptive cubic PN curvature; source vertices, root support heights and underside triangles fixed',
        'source_vertices':len(vertices),'source_triangles':len(indices)//3,'vertices':len(v),'triangles':len(i)//3,
        'refined_wood_faces':refined_faces,'unique_refined_edges':len(marked),
        'maximum_displacement_normalized':max_displacement,'source_height_band':[0,.68],
        'root_height_preserved':True,'root_curvature_limit_normalized':.001,'underside_triangles_preserved':True,
        'maximum_edge_displacement_share':.12,'maximum_displacement_limit_normalized':.005,'maximum_added_triangles':budget,
        'safety_limited_vertices':int(np.count_nonzero(scales[groups]<1)),'winding_checked':True,'new_sculpt_detail':False}
    return v,i,np.asarray(ls,dtype='<f4'),np.asarray(es,dtype='<f4'),report


def cook(folder,leaf_mask):
    folder=Path(folder)
    if (folder/'near-wood-report.json').exists():raise ValueError('This immutable close-wood cook is already refined')
    raw=(folder/'mesh.bin').read_bytes();_,nv,ni,w,h,materials,*bounds=struct.unpack_from('<8s5I6f',raw)
    v=np.frombuffer(raw,dtype='<f4',count=nv*9,offset=52).reshape(-1,9).copy()
    i=np.frombuffer(raw,dtype='<u4',count=ni,offset=52+nv*36).copy()
    lit=(folder/'lighting.bin').read_bytes();light=np.frombuffer(lit,dtype='<f4',offset=16).reshape(nv,8).copy()
    lod=(folder/'lods.bin').read_bytes();magic,count,old=struct.unpack_from('<8s2I',lod)
    assert magic==b'FOLLOD02' and old==nv
    extra=np.frombuffer(lod,dtype='<f4',count=nv*16,offset=16).reshape(nv,16).copy()
    new,indices,light,extra,report=refine(v,i,light,extra,leaf_mask)
    header=struct.pack('<8s5I6f',b'FOLMESH1',len(new),len(indices),w,h,materials,*bounds)
    (folder/'mesh.bin').write_bytes(header+new.tobytes()+indices.tobytes()+raw[52+nv*36+ni*4:])
    (folder/'lighting.bin').write_bytes(struct.pack('<8s2I',b'FOLLIT01',len(new),8)+light.tobytes())
    (folder/'lods.bin').write_bytes(struct.pack('<8s2I',magic,count,len(new))+extra.tobytes()+lod[16+nv*64:])
    report['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (folder/'near-wood-report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);p.add_argument('--leaf-mask',type=int,required=True)
    a=p.parse_args();print(json.dumps(cook(a.folder,a.leaf_mask),indent=2))
