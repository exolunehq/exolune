"""Structural variant contract and independent geometry probes; no GPU."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import tempfile
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/foliage/local3d'))
from audit import array,read_glb
from variations import PROFILES,derive,deform,jacobian,parameters
from produce import variant_approved


def check(source,out):
    source=Path(source);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    before=hashlib.sha256(source.read_bytes()).hexdigest();doc,blob=read_glb(source)
    assert not variant_approved({'profile':'compact','seed':12345},before),'Parent acceptance leaked to a variant'
    assert variant_approved({'art_approved':True,'approved_sha256':before},before)
    try:variant_approved({'art_approved':True,'approved_sha256':'wrong'},before)
    except ValueError:pass
    else:raise AssertionError('Art approval survived a changed derived asset')
    summaries=[];shapes=[]
    for profile in PROFILES:
        target=out/profile/'plant.glb';target.parent.mkdir(exist_ok=True)
        # Test output is never an immutable production folder.
        with tempfile.TemporaryDirectory(dir=target.parent) as work:
            path=Path(work)/'plant.glb';report=derive(source,path,profile,12345)
            a,b=read_glb(path);frame=report['frame'];p=report['parameters']
            root_errors=[];moved=[];branch_angles=[]
            for i,mesh in enumerate(doc['meshes']):
                for j,prim in enumerate(mesh['primitives']):
                    attrs=prim['attributes'];other=a['meshes'][i]['primitives'][j]['attributes']
                    position=array(doc,blob,attrs['POSITION']);result=array(a,b,other['POSITION'])
                    fixed=position[:,1]<=frame['origin'][1]+frame['height']*.2
                    root_errors.append(float(np.abs(result[fixed]-position[fixed]).max()) if fixed.any() else 0)
                    assert np.array_equal(array(doc,blob,prim['indices']),array(a,b,prim['indices']))
                    for name in set(attrs)-{'POSITION','NORMAL','TANGENT','_WIND_PIVOT','_LEAF_PIVOT'}:
                        assert np.array_equal(array(doc,blob,attrs[name]),array(a,b,other[name])),name
                    normal=array(a,b,other['NORMAL']);tangent=array(a,b,other['TANGENT'])
                    assert np.allclose(np.linalg.norm(normal,axis=1),1,atol=2e-5)
                    assert np.allclose(np.sum(normal*tangent[:,:3],axis=1),0,atol=2e-5)
                    for name in ['_WIND_PIVOT','_LEAF_PIVOT']:
                        if name in attrs:
                            assert np.allclose(array(a,b,other[name]),deform(array(doc,blob,attrs[name]),p,frame),atol=1e-6)
                    moved.append(np.linalg.norm(result-position,axis=1))
                    # Independently check local triangle orientations against
                    # transformed source normals, excluding tiny source faces.
                    tri=array(doc,blob,prim['indices']).ravel().reshape(-1,3)
                    old=np.cross(position[tri[:,1]]-position[tri[:,0]],position[tri[:,2]]-position[tri[:,0]])
                    new=np.cross(result[tri[:,1]]-result[tri[:,0]],result[tri[:,2]]-result[tri[:,0]])
                    areas=np.linalg.norm(old,axis=1);valid=areas>frame['height']**2*1e-10
                    assert np.all(np.linalg.norm(new[valid],axis=1)/areas[valid]>.35),'Collapsed triangle'
                    if doc['materials'][prim['material']].get('alphaMode')!='MASK':
                        v=position[tri[:,1]]-position[tri[:,0]];w=result[tri[:,1]]-result[tri[:,0]]
                        band=valid&(position[tri[:,0],1]>.3*frame['height'])
                        cosine=np.sum(v[band]*w[band],axis=1)/np.maximum(np.linalg.norm(v[band],axis=1)*np.linalg.norm(w[band],axis=1),1e-15)
                        branch_angles.extend(np.degrees(np.arccos(np.clip(cosine,-1,1))).tolist())
                    shapes.append((profile,result.copy()))
            assert max(root_errors)==0,'Root zone moved'
            assert max(d.max() for d in moved)>.1,'Structural change is only cosmetic'
            assert np.percentile(branch_angles,95)>2,'Woody branch directions did not vary'
            for image in doc['images']:
                v=doc['bufferViews'][image['bufferView']];start=v.get('byteOffset',0);stop=start+v['byteLength']
                assert blob[start:stop]==b[start:stop],'Texture bytes changed'
            # A fixed-height horizontal slice stays one-to-one; a vertical
            # column stays monotone before slice deformation. Probe the whole
            # crown volume, not only visible vertices.
            rng=np.random.default_rng(779);samples=rng.uniform(-1,1,(2000,3))
            samples[:,[0,2]]*=frame['radius'];samples[:,1]=(samples[:,1]+1)*.5*frame['height'];samples+=frame['origin']
            assert np.linalg.det(jacobian(samples,p,frame)).min()>.25
            assert np.array_equal(deform(samples,p,frame),deform(samples,parameters(profile,12345),frame))
            assert not np.allclose(deform(samples,p,frame),deform(samples,parameters(profile,12346),frame))
            summaries.append({'profile':profile,'triangles':report['triangles'],'root_error_m':max(root_errors),
                              'max_displacement_m':report['max_displacement_m'],
                              'wood_edge_direction_p95_degrees':float(np.percentile(branch_angles,95))})
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before,'Master changed'
    result={'status':'pass','scope':'Derived geometry and attributes, not native art or performance acceptance','master_sha256':before,'variants':summaries}
    (out/'checks.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    print(json.dumps(check(args.source,args.out),indent=2))
