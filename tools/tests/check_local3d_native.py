"""Validate a cooked generated plant, every LOD, material and attachment stream."""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import numpy as np


def assets(catalogue):
    catalogue=Path(catalogue);report=json.loads((catalogue/'native-report.json').read_text());folder=catalogue/report['name']
    raw=(folder/'mesh.bin').read_bytes();magic,nv,ni,w,h,materials,*bounds=struct.unpack_from('<8s5I6f',raw)
    assert magic==b'FOLMESH1' and len(raw)==52+nv*36+ni*4+w*h*4
    vertices=np.frombuffer(raw,dtype='<f4',count=nv*9,offset=52).reshape(-1,9);indices=np.frombuffer(raw,dtype='<u4',count=ni,offset=52+nv*36)
    light_raw=(folder/'lighting.bin').read_bytes();assert struct.unpack_from('<8s2I',light_raw)==(b'FOLLIT01',nv,8)
    light=np.frombuffer(light_raw,dtype='<f4',offset=16).reshape(-1,8)
    data=(folder/'lods.bin').read_bytes();magic,count,original=struct.unpack_from('<8s2I',data)
    assert magic==b'FOLLOD02' and count in [5,7] and original==nv
    at=16
    def floats(rows,width):
        nonlocal at
        result=np.frombuffer(data,dtype='<f4',count=rows*width,offset=at).reshape(-1,width);at+=rows*width*4;return result
    extra=floats(nv,16);levels=[(vertices,indices,light,extra,0)]
    for level in range(1,count):
        n,index_count,res=struct.unpack_from('<3I',data,at);at+=12
        v=floats(n,9);i=np.frombuffer(data,dtype='<u4',count=index_count,offset=at);at+=index_count*4
        l=floats(n,8);e=floats(n,16)
        assert res in [0,128,256,512,1024]
        if res:
            maps=np.frombuffer(data,dtype='u1',count=res*res*materials*12,offset=at);at+=len(maps)
            assert maps.size==res*res*materials*12
        levels.append((v,i,l,e,res))
    assert at==len(data),'Unexpected trailing LOD bytes'
    summary=[]
    for level,(v,i,l,e,res) in enumerate(levels):
        assert len(i)%3==0 and i.max()<len(v) and len(i)>0
        assert all(np.isfinite(a).all() for a in [v,l,e])
        assert np.allclose(np.linalg.norm(v[:,3:6],axis=1),1,atol=.015),'Invalid normals'
        assert v[:,8].min()>=0 and v[:,8].max()<materials
        assert e[:,:4].min()>=0 and e[:,:4].max()<=1
        assert e[:,[7,11]].min()>=0 and e[:,[7,11]].max()<=1
        assert v[:,1].min()<0,'Root ends must extend beneath the ground origin'
        assert np.all(v[:,:3].min(0)>=np.array(bounds[:3])-2e-4) and np.all(v[:,:3].max(0)<=np.array(bounds[3:])+2e-4),'LOD exceeds the source bounds'
        root=np.mod(v[:,8],1)>.125
        assert root.any() and np.all(e[root,7]==0) and np.all(e[root,11]==0),'A root must remain fixed'
        if level:assert len(i)<len(levels[level-1][1])*(.9 if count==7 else .8),'Insufficient LOD reduction'
        summary.append({'level':level,'vertices':len(v),'triangles':len(i)//3,'texture_size':res or 'shared master'})
    assert summary[-1]['triangles']<=3000,'Last tree LOD exceeds the witness budget'
    assert (folder/'material.bin').stat().st_size==16+w*h*8
    assert (folder/'impostor.bin').read_bytes()[:8]==b'FOLIMP01'
    assert (folder/'impostor_light.bin').read_bytes()[:8]==b'FOLIL001'
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.bin')}
    return {'status':'pass','source_sha256':report['source_sha256'],'model':report['name'],'levels':summary,'hashes':hashes}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('catalogue',type=Path);p.add_argument('--out',type=Path);args=p.parse_args()
    result=assets(args.catalogue);text=json.dumps(result,indent=2)
    if args.out:args.out.write_text(text+'\n')
    print(text)
