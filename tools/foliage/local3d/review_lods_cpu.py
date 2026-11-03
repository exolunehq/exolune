"""CPU coverage/silhouette diagnostics for the actual cooked native meshes.

These are unlit orthographic probes, not game screenshots or a quality threshold.
All levels use the same bounds and 36 views; the native alpha cutoff is retained.
"""
from pathlib import Path
import argparse
import json
import struct
import sys
import cv2
import numpy as np
from numba import set_num_threads
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import bake
sys.path.insert(0,str(HERE.parents[2]/'tools'))
from banc_local3d import sha


def review(catalogue,out):
    info=json.loads((catalogue/'native-report.json').read_text());folder=catalogue/info['name'];out.mkdir(parents=True,exist_ok=True)
    signature={'reviewer':sha(Path(__file__)),'rasterizer':sha(Path(bake.__file__)),
               'mesh':sha(folder/'mesh.bin'),'lods':sha(folder/'lods.bin'),'views':[12,3],'probe_pixels':128}
    result_file=out/'coverage.json'
    if result_file.exists():
        prior=json.loads(result_file.read_text())
        if prior['inputs']==signature and sha(out/'coverage.png')==prior['sheet_sha256']:return prior
        raise ValueError('Coverage inputs changed; use a new output folder')
    bake.OUT=catalogue;v,i,atlas,lo,hi,materials=bake.load(info['name'])
    levels=[(v,i,atlas)];data=(folder/'lods.bin').read_bytes();magic,count,n=struct.unpack_from('<8s2I',data)
    if magic!=b'FOLLOD02' or count not in [5,7] or n!=len(v):raise ValueError('Unsupported LOD data')
    at=16+n*64
    for _ in range(1,count):
        nv,ni,res=struct.unpack_from('<3I',data,at);at+=12
        vertices=np.frombuffer(data,dtype='<f4',count=nv*9,offset=at).reshape(-1,9);at+=nv*36
        indices=np.frombuffer(data,dtype='<u4',count=ni,offset=at);at+=ni*4+nv*(32+64)
        texture=atlas
        if res:
            texture=np.frombuffer(data,dtype='u1',count=res*res*materials*4,offset=at).reshape(res,res*materials,4)
            at+=res*res*materials*12
        levels.append((vertices.copy(),indices.copy(),texture.copy()))
    if at!=len(data):raise ValueError('Unexpected LOD bytes')
    radius=float(np.linalg.norm(np.maximum(abs(lo-np.array([0,.5,0])),abs(hi-np.array([0,.5,0])))))
    set_num_threads(4);probes=[];metrics=[]
    for level,(vertices,indices,texture) in enumerate(levels):
        print('CPU silhouette probe LOD',level,flush=True)
        rgba,_=bake.bake_views(vertices,indices,texture,radius,12,3,256,materials)
        coverage=rgba[...,3].reshape(36,128,2,128,2).mean((2,4))/255
        probes.append(coverage)
        if level:
            reference=probes[0];views=[]
            for view,(old,new) in enumerate(zip(reference,coverage)):
                old_mask=(old>.125).astype('u1');new_mask=(new>.125).astype('u1')
                # Signed contour differences include gaps; this is not a hull-only score.
                outward=cv2.distanceTransform(1-old_mask,cv2.DIST_L2,cv2.DIST_MASK_PRECISE)[new_mask>0]
                inward=cv2.distanceTransform(1-new_mask,cv2.DIST_L2,cv2.DIST_MASK_PRECISE)[old_mask>0]
                views.append({'azimuth':view%12*30,'elevation':view//12*45,
                    'coverage_ratio':float(new.sum()/max(old.sum(),1)),
                    'soft_iou':float(np.minimum(old,new).sum()/max(np.maximum(old,new).sum(),1)),
                    'outward_distance_p95_pixels':float(np.percentile(outward,95)),
                    'inward_distance_p95_pixels':float(np.percentile(inward,95))})
            metrics.append({'level':level,'coverage_ratio_range':[min(v['coverage_ratio'] for v in views),max(v['coverage_ratio'] for v in views)],
                            'soft_iou_median':float(np.median([v['soft_iou'] for v in views])),
                            'max_distance_p95_pixels':max(max(v['outward_distance_p95_pixels'],v['inward_distance_p95_pixels']) for v in views),
                            'views':views})
    selected=[0,2,4,7,12,14,16,24];cell=160
    sheet=Image.new('RGB',(cell*len(selected),cell*count),'white');draw=ImageDraw.Draw(sheet)
    for level,coverage in enumerate(probes):
        for col,view in enumerate(selected):
            old,new=probes[0][view],coverage[view]
            rgb=np.full((128,128,3),255,'u1')
            if level==0:rgb[:]=np.rint(255*(1-new[...,None])).astype('u1')
            else:
                # Grey overlap; red lost coverage; green added coverage.
                rgb[:]=np.rint(255*(1-np.minimum(old,new)[...,None])).astype('u1')
                lost=np.maximum(old-new,0);added=np.maximum(new-old,0)
                rgb[:,:,1:]=np.rint(rgb[:,:,1:]*(1-lost[...,None])).astype('u1')
                rgb[:,:,[0,2]]=np.rint(rgb[:,:,[0,2]]*(1-added[...,None])).astype('u1')
            sheet.paste(Image.fromarray(rgb),(col*cell+16,level*cell+22))
            draw.text((col*cell+4,level*cell+4),f'L{level} az{view%12*30} el{view//12*45}',fill='black')
    sheet.save(out/'coverage.png')
    result={'status':'diagnostic only; native visual acceptance is separate','inputs':signature,'levels':metrics,
            'scope':'36 orthographic directions, 128-pixel probes, four alpha samples per pixel; no native mip filtering, wind or lighting',
            'sheet':str(out/'coverage.png'),'sheet_sha256':sha(out/'coverage.png')}
    result_file.write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--catalogue',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();r=review(args.catalogue.resolve(),args.out.resolve())
    print(json.dumps({k:v for k,v in r.items() if k!='levels'}|{'summary':[{k:v for k,v in row.items() if k!='views'} for row in r['levels']]},indent=2))
