"""Seven geometry levels with intact near branches and curved attached leaves."""
from pathlib import Path
import json
import os
import struct
import subprocess
import numpy as np
from PIL import Image


def source_extra(attributes,vertices,origin=None,height=None):
    positions=np.concatenate([attributes[f'part{i}_POSITION'] for i in range(len([k for k in attributes if k.endswith('_POSITION')]))])
    lo,hi=positions.min(0),positions.max(0)
    if height is None:height=hi[1]-lo[1]
    if origin is None:origin=np.array([(lo[0]+hi[0])/2,lo[1],(lo[2]+hi[2])/2])
    values=[]
    for i in range(len([k for k in attributes if k.endswith('_POSITION')])):
        key=f'part{i}_';count=len(attributes[key+'POSITION']);extra=np.zeros((count,16),'<f4');extra[:,:4]=1
        if key+'COLOR_0' in attributes:extra[:,:4]=attributes[key+'COLOR_0']
        for name,start in [('_WIND_PIVOT',4),('_LEAF_PIVOT',8)]:
            extra[:,start:start+3]=(attributes[key+name]-origin)/height if key+name in attributes else vertices[sum(map(len,values)):sum(map(len,values))+count,:3]
        for name,column in [('_WIND_WEIGHT',7),('_LEAF_WEIGHT',11),('_WIND_PHASE',12)]:
            if key+name in attributes:extra[:,column]=attributes[key+name].reshape(-1)
        values.append(extra)
    return np.concatenate(values)


def make(folder,vertices,indices,light,extra,leaf_mask,blender,source,origin=None,height=None,*,shrub=False):
    folder=Path(folder);work=folder/'lod-work';work.mkdir(exist_ok=True)
    triangles=indices.reshape(-1,3);leaf=((leaf_mask>>vertices[triangles[:,0],8].astype(int))&1)!=0
    wood_faces=triangles[~leaf];wood_ids,wood_indices=np.unique(wood_faces,return_inverse=True)
    attributes=np.load(folder/'source_attributes.npz');original=np.concatenate([attributes[k] for k in sorted(attributes.files) if k.endswith('_POSITION')]);lo,hi=original.min(0),original.max(0)
    if origin is None:origin=np.array([(lo[0]+hi[0])/2,lo[1],(lo[2]+hi[2])/2])
    if height is None:height=hi[1]-lo[1]
    np.savez_compressed(work/'wood.npz',vertices=vertices[wood_ids],indices=wood_indices.astype('<u4'),light=light[wood_ids],extra=extra[wood_ids],origin=origin,height=height)
    command=[str(blender),'--background','--factory-startup','--threads','4','--python-exit-code','1','--python',str(Path(__file__).with_name('wood_lods.py')),'--',str(work/'wood.npz'),str(work),'--glb',str(source)]
    if shrub:command.append('--shrub')
    with (work/'blender.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    leaf_faces=triangles[leaf];is_leaf=np.max(extra[leaf_faces,11],axis=1)>0
    card_faces=leaf_faces[is_leaf];stem_faces=leaf_faces[~is_leaf]
    if not len(card_faces):raise ValueError('Individual leaves with attachment attributes are required for this LOD recipe')
    ids=np.unique(card_faces);keys=np.round(np.column_stack((extra[ids,8:11],extra[ids,12])),7)
    _,labels=np.unique(keys,axis=0,return_inverse=True);leaves={}
    for label in range(labels.max()+1):
        group=ids[labels==label];bottom=group[extra[group,11]<.01];top=group[extra[group,11]>.99]
        if len(bottom)<2 or len(top)<2:raise ValueError('A leaf must have complete root and tip rows')
        middle=group[np.isclose(extra[group,11],.5)]
        if len(middle)<2:raise ValueError('A curved source leaf must have a middle row')
        quad=np.array([bottom[np.argmin(vertices[bottom,6])],bottom[np.argmax(vertices[bottom,6])],middle[np.argmin(vertices[middle,6])],middle[np.argmax(vertices[middle,6])],top[np.argmin(vertices[top,6])],top[np.argmax(vertices[top,6])]])
        phase=float(extra[quad[0],12]);leaves.setdefault(phase,[]).append(quad)
    report=[];streams=[]
    for level,keep in enumerate([12,9,9,4,4,2],1):
        wood=np.load(work/f'wood{level}.npz');vs=[wood['vertices']];ls=[wood['light']];es=[wood['extra']];ix=[wood['indices']];count=len(vs[0])
        # A foliage-heavy master cannot always retain all twelve curved leaves
        # at L1 and still reach the common reduction gate. Budget from actual
        # wood/shoot topology, then select distributed whole leaves. Curvature
        # and attachment data survive; coverage compensation stays shoot-local.
        previous=len(indices)//3 if level==1 else report[-1]['triangles']
        triangle_target=int(previous*.88);stem_cost=0
        for phase in leaves:
            stem=stem_faces[extra[stem_faces[:,0],12]==phase]
            if level<6 and len(stem):
                rows=len(np.unique(extra[np.unique(stem),7])) if level<=2 else 2
                stem_cost+=(rows-1)*2*(2 if level<=3 else 1)
        available=triangle_target-len(wood['indices'])//3-stem_cost
        leaf_cost=4 if level<=2 else 2
        while keep>1 and sum(min(len(cards),keep) for cards in leaves.values())*leaf_cost>available:keep-=1
        def append(v,l,e,i):
            nonlocal count
            vs.append(v);ls.append(l);es.append(e);ix.append(np.asarray(i,dtype='<u4').reshape(-1)+count);count+=len(v)
        for phase,cards in sorted(leaves.items()):
            centres=np.array([vertices[q,:3].mean(0) for q in cards]);selection=[]
            if len(cards)>keep:
                selection=[int(np.argmax(np.sum((centres-centres.mean(0))**2,axis=1)))]
                while len(selection)<keep:
                    distances=np.min(np.sum((centres[:,None,:]-centres[selection][None,:,:])**2,axis=2),axis=1);distances[selection]=-1;selection.append(int(distances.argmax()))
            else:selection=list(range(len(cards)))
            source_ids=np.unique(np.concatenate(cards));lower=vertices[source_ids,:3].min(0);upper=vertices[source_ids,:3].max(0)
            scale=np.sqrt(len(cards)/len(selection))
            for chosen in selection:
                q=cards[chosen] if level<=2 else cards[chosen][[0,1,4,5]];v=vertices[q].copy();e=extra[q].copy()
                v[:,:3]=np.clip(e[:,8:11]+(v[:,:3]-e[:,8:11])*scale,lower,upper)
                append(v,light[q],e,[0,1,3,0,3,2,2,3,5,2,5,4] if level<=2 else [0,1,3,0,3,2])
            stem=stem_faces[extra[stem_faces[:,0],12]==phase]
            if level<6 and len(stem):
                old=np.unique(stem);points=vertices[old,:3];weights=extra[old,7]
                root=extra[old[0],4:7];tip=points[np.isclose(weights,weights.max())].mean(0);axis=tip-root;axis/=max(np.linalg.norm(axis),1e-8)
                side=np.cross(axis,np.array([0,1,0]));side/=max(np.linalg.norm(side),1e-8)
                if np.linalg.norm(side)<.1:side=np.array([1,0,0])
                axes=[side,np.cross(axis,side)] if level<=3 else [side]
                for across in axes:
                    row_weights=np.unique(weights) if level<=2 else np.array([weights.min(),weights.max()])
                    row_points=[points[np.isclose(weights,w)].mean(0) for w in row_weights]
                    radii=[float(np.median(np.linalg.norm(points[np.isclose(weights,w)]-point,axis=1))) for w,point in zip(row_weights,row_points)]
                    n=len(row_points)*2;v=np.tile(vertices[old[0]],(n,1));v[:,:3]=np.array([point+sign*across*radius for point,radius in zip(row_points,radii) for sign in [-1,1]]);v[:,3:6]=np.cross(across,axis);v[:,6:8]=vertices[old,6:8].mean(0)
                    e=np.tile(extra[old[0]],(n,1));e[:,7]=np.repeat(row_weights,2);e[:,11]=0;e[:,8:11]=v[:,:3]
                    faces=[a for row in range(len(row_points)-1) for a in [2*row,2*row+1,2*row+3,2*row,2*row+3,2*row+2]]
                    append(v,np.tile(light[old].mean(0),(n,1)),e,faces)
        v=np.concatenate(vs).astype('<f4');l=np.concatenate(ls).astype('<f4');e=np.concatenate(es).astype('<f4');i=np.concatenate(ix).astype('<u4')
        root_envelope={'method':'Inherited from the canonical master; no second vertex-wise ground warp'}
        # Reconstructed roots may extend below the master's buried envelope;
        # thin shoot ribbons may also protrude by their radius. Keep every LOD
        # inside the common culling and proxy bounds, including hidden roots.
        bounded=np.clip(v[:,:3],vertices[:,:3].min(0),vertices[:,:3].max(0))
        bounded_count=int(np.any(bounded!=v[:,:3],axis=1).sum())
        v[:,:3]=bounded
        if not np.isfinite(v).all() or i.max()>=len(v):raise ValueError('Invalid cooked LOD')
        if len(i)//3>=previous*.9:raise ValueError('LOD cannot meet the reduction budget with this source topology')
        maps=b'';resolution={1:0,2:0,3:0 if shrub else 1024,4:512,5:256,6:128}[level]
        if resolution:
            raw=(folder/'mesh.bin').read_bytes();_,nv,ni,w,h,nmat,*_=struct.unpack_from('<8s5I6f',raw)
            atlas=Image.frombytes('RGBA',(w,h),raw[52+nv*36+ni*4:]);material=(folder/'material.bin').read_bytes()
            originals=[atlas,Image.frombytes('RGBA',(w,h),material[16:16+w*h*4]),Image.frombytes('RGBA',(w,h),material[16+w*h*4:])]
            wood_maps=None
            if level>4:
                wood_colour=np.array(Image.open(work/f'wood{level}_basecolor.png').convert('RGBA'));wood_normal=np.array(Image.open(work/f'wood{level}_normal.png').convert('RGBA'));rough=np.array(Image.open(work/f'wood{level}_roughness.png').convert('RGBA'))
                # Partially covered bake texels are not reliable padding seeds.
                known=wood_colour[:,:,3]>=250
                while not known.all():
                    expanded=known.copy()
                    for dy,dx in [(0,1),(0,-1),(1,0),(-1,0)]:
                        valid=np.roll(known,(dy,dx),(0,1))&~expanded
                        for image in [wood_colour,wood_normal,rough]:image[valid]=np.roll(image,(dy,dx),(0,1))[valid]
                        expanded|=valid
                    if np.array_equal(expanded,known):raise ValueError('Wood bake has no source coverage')
                    known=expanded
                wood_colour[:,:,3]=255;wood_normal[:,:,3]=255;mask=np.full_like(wood_colour,255);mask[:,:,1]=rough[:,:,0];mask[:,:,2]=0
                wood_maps=[wood_colour,wood_normal,mask]
            output=[]
            for channel in range(3):
                target=Image.new('RGBA',(resolution*nmat,resolution))
                for slot in range(nmat):
                    tile=originals[channel].crop((slot*h,0,(slot+1)*h,h)).resize((resolution,resolution),Image.Resampling.LANCZOS)
                    if wood_maps is not None and not ((leaf_mask>>slot)&1):tile=Image.fromarray(wood_maps[channel])
                    target.paste(tile,(slot*resolution,0))
                output.append(target.tobytes())
            maps=b''.join(output)
        streams.append((v,i,l,e,resolution,maps));report.append({'level':level,'vertices':len(v),'triangles':len(i)//3,'triangle_target':triangle_target,'leaves_per_shoot':keep,'leaf_rows':3 if level<=2 else 2,'texture_size':resolution or 'shared L0','root_envelope':root_envelope,'bounds_clamped_vertices':bounded_count})
    with (folder/'lods.bin').open('wb') as stream:
        stream.write(struct.pack('<8s2I',b'FOLLOD02',7,len(vertices)));stream.write(extra.astype('<f4').tobytes())
        for v,i,l,e,resolution,maps in streams:
            stream.write(struct.pack('<3I',len(v),len(i),resolution));stream.write(v.tobytes());stream.write(i.tobytes());stream.write(l.tobytes());stream.write(e.tobytes());stream.write(maps)
    materials=('L0–L3 share source maps; L4 downsampled to 512; coarse maps use 256/128' if shrub
               else 'L0/L1/L2 share maps; L3/L4 downsample source UV maps to 1024/512; coarse maps use 256/128')
    result={'levels':[{'level':0,'vertices':len(vertices),'triangles':len(indices)//3}]+report,'wood_reconstruction':json.loads((work/'wood-audit.json').read_text()),'source':'master wood unchanged through L4; near curved leaves and shoot rows retained; coarse wood UVs and textures rebaked','shared_materials':materials}
    (folder/'lod-report.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
