"""Audit close-root UV continuity and the actual L2 material payload."""
from pathlib import Path
import argparse
import json
import struct
import numpy as np
from PIL import Image


def check(catalogue):
    report=json.loads((catalogue/'native-report.json').read_text());folder=catalogue/report['name']
    raw=(folder/'mesh.bin').read_bytes();_,nv,ni,w,h,materials,*_=struct.unpack_from('<8s5I6f',raw)
    master=np.frombuffer(raw,dtype='<f4',count=nv*9,offset=52).reshape(-1,9)
    maps=[Image.frombytes('RGBA',(w,h),raw[52+nv*36+ni*4:])]
    material=(folder/'material.bin').read_bytes()
    maps.extend([Image.frombytes('RGBA',(w,h),material[16:16+w*h*4]),Image.frombytes('RGBA',(w,h),material[16+w*h*4:])])
    data=(folder/'lods.bin').read_bytes();_,level_count,_=struct.unpack_from('<8s2I',data);at=16+nv*64
    source_indices=np.frombuffer(raw,dtype='<u4',count=ni,offset=52+nv*36).reshape(-1,3)
    def wood_surface(v,faces):
        woody=((report['leaf_mask']>>v[faces[:,0],8].astype(int))&1)==0
        return v[faces[woody]]
    original_wood=wood_surface(master,source_indices)
    refined=report.get('near_wood',{}).get('refined_wood_faces',0)>0
    def rooted_rows(v):
        root=(np.mod(v[:,8],1)>.125)&(v[:,1]>.002)&(v[:,1]<.16)
        return {tuple(row) for row in np.round(v[root][:,[0,1,2,6,7]],6)}
    source_rows=report.get('near_wood',{}).get('source_vertices',len(master))
    expected=rooted_rows(master[:source_rows]);retained=1.;protected=4 if level_count==7 else 2
    assert expected,'The master has no exposed root witness'
    for level in range(1,level_count):
        count,indices,res=struct.unpack_from('<3I',data,at);at+=12
        vertices=np.frombuffer(data,dtype='<f4',count=count*9,offset=at).reshape(-1,9)
        faces=np.frombuffer(data,dtype='<u4',count=indices,offset=at+count*36).reshape(-1,3)
        at+=count*(36+32+64)+indices*4
        if level<=protected:
            share=len(expected&rooted_rows(vertices))/len(expected);retained=min(retained,share)
            assert share>.995,f'Close root positions or UV seams changed: {share}'
            if level_count==7:
                if refined and level==1:original_wood=wood_surface(vertices,faces)
                assert np.array_equal(wood_surface(vertices,faces),original_wood),'A nearby branch was collapsed into a spanning face'
        if res:
            for channel in range(3):
                texture=np.frombuffer(data,dtype='u1',count=res*res*materials*4,offset=at).reshape(res,res*materials,4)
                at+=res*res*materials*4
                if level>protected:continue
                for slot in range(materials):
                    if (report['leaf_mask']>>slot)&1:continue
                    reference=np.asarray(maps[channel].crop((slot*h,0,(slot+1)*h,h)).resize((res,res),Image.Resampling.LANCZOS))
                    assert np.array_equal(texture[:,slot*res:(slot+1)*res],reference),'Protected bark no longer preserves the source material'
    assert at==len(data)
    return {'model':report['name'],'retained_root_position_uv_share':retained,'protected_wood_levels':protected,
        'near_wood_surface':('bounded L0 curvature; exact source wood at L1 through L4' if refined else 'exact master geometry through L4') if level_count==7 else 'legacy root protection',
        'protected_materials':'shared source maps or exact downsample','status':'pass'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('catalogue',type=Path);a=p.parse_args()
    print(json.dumps(check(a.catalogue),indent=2))
