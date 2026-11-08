"""One continuous architectural skin across wings, supports and their junctions.

Run in background Blender. Structural continuity is established in a single
domain with true apertures, before fittings and material detail are authored.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import bpy
from mathutils import Vector

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import author as a
import manufacturing as m
from details import audit as fittings_audit
from finish_shell_house import tagged,profile_solid,clip_x,xy_solid,sha,spline


def front(x,z,asset):
    left=1/(1+math.exp(max(-60,min(60,(x+.5)*1.1))))
    lower=1/(1+math.exp(max(-60,min(60,(z-4.6)*2))))
    saddle=.70*math.exp(-((x-1.7)/2.2)**2-((z-3.8)/.85)**2)
    upper=min(1,max(0,(z-4.0)/2));upper=upper*upper*(3-2*upper)
    return -2.70-1.3*left*lower+saddle-(.85+asset['upper_advance'])*upper


def back(x,z):return 3.55+.18*math.tanh((z-4)*.5)


def shape(p,t):
    crown=min(1,max(0,(p.y-.5)/3.5))
    return Vector((p.x*(1-.13*t)+.20*math.sin(math.pi*t),
                   .1+(p.y-.1)*(1-.075*t)+.65*math.sin(math.pi*t)*crown))


def at(p,t,asset,offset=0):
    q=shape(p,t)
    return (q.x,(1-t)*front(p.x,p.y,asset)+t*back(p.x,p.y)+offset,q.y)


def face_normal(p,t,asset):
    epsilon=.0001
    dx=Vector(at(p+Vector((epsilon,0)),t,asset))-Vector(at(p-Vector((epsilon,0)),t,asset))
    dz=Vector(at(p+Vector((0,epsilon)),t,asset))-Vector(at(p-Vector((0,epsilon)),t,asset))
    normal=dx.cross(dz).normalized()
    return normal if t<.5 else -normal


def structural_skin(domain,asset):
    points=[Vector(p) for p in domain['vertices_xz']];n=len(points);radius=domain['edge_radius_m']
    vertices=[at(p,0,asset) for p in points]+[at(p,1,asset) for p in points]
    faces=[tuple(f) for f in domain['triangles']]+[tuple(i+n for i in reversed(f)) for f in domain['triangles']]
    mats=[0]*len(faces);openings={};uvs=[];wall_rigs=[];roof={'faces':[],'depth':{}}
    for face in faces:uvs.append([(vertices[i][0]*.5,vertices[i][2]*.5) for i in face])
    for loop in domain['boundaries']:
        ids=loop['indices'];profile=[points[i] for i in ids];count=len(ids);normals=[]
        for j,p in enumerate(profile):
            incoming=(p-profile[(j-1)%count]).normalized()
            outgoing=(profile[(j+1)%count]-p).normalized()
            first=Vector((incoming.y,-incoming.x));second=Vector((outgoing.y,-outgoing.x))
            normal=(first+second).normalized()
            # Equal-angle miters preserve tiny grid-cut edges. A tangent
            # weighted by adjacent edge lengths can fold a bevel backwards.
            normals.append(normal/max(.25,normal.dot(second)))
        body=[p+normal*radius for p,normal in zip(profile,normals)]
        openings[loop['name']]=body
        rings=[ids];arc=[0.0]
        for i in range(count):arc.append(arc[-1]+(profile[(i+1)%count]-profile[i]).length)
        # A small quarter-round lip has matching tangent directions at the
        # face and wall. The body itself is never voxel-smoothed into blobs.
        for t,theta in [(0,math.pi/4),(0,math.pi/2),(.2,math.pi/2),(.4,math.pi/2),(.6,math.pi/2),(.8,math.pi/2),(1,math.pi/2),(1,math.pi/4)]:
            ring=[]
            for p,normal in zip(profile,normals):
                q=p+normal*radius*math.sin(theta)
                offset=radius*(1-math.cos(theta))*(1-2*t)
                ring.append(len(vertices));vertices.append(at(q,t,asset,offset))
            rings.append(ring)
        rings.append([i+n for i in ids])
        wall_rigs.append(rings)
        if loop['name']=='outer':
            for ring,t in zip(rings,[0,0,0,.2,.4,.6,.8,1,1,1]):
                for index in ring:roof['depth'][index]=t
        centre=sum(p.y for p in body)/count
        for j,(one,two) in enumerate(zip(rings,rings[1:])):
            for i in range(count):
                if loop['name']=='outer':roof['faces'].append(len(faces))
                k=(i+1)%count;face=(one[i],one[k],two[k],two[i]);faces.append(face)
                if loop['name']=='outer' or j in [0,8]:material=0
                else:material=2 if body[i].y>centre+.35 or loop['name']=='entry' else 1
                mats.append(material)
                uvs.append([(arc[i]*.5,vertices[one[i]][1]*.5),(arc[i+1]*.5,vertices[one[k]][1]*.5),
                            (arc[i+1]*.5,vertices[two[k]][1]*.5),(arc[i]*.5,vertices[two[i]][1]*.5)])
    obj=a.mesh('continuous_shell_and_junctions',vertices,faces,face_materials=mats)
    uv=obj.data.uv_layers.active
    for face,values in zip(obj.data.polygons,uvs):
        for loop,value in zip(face.loop_indices,values):uv.data[loop].uv=value
    tagged(obj,'structural_skin','inhabited_shell')
    # A triangulation fan near an aperture must not change the intended smooth
    # surface. Use its differential normal, then loft tangents for the lips.
    normals=[face_normal(p,0,asset) for p in points]+[face_normal(p,1,asset) for p in points]
    normals.extend(Vector(v.normal) for v in obj.data.vertices[len(normals):])
    for rings in wall_rigs:
        count=len(rings[0])
        for j in range(1,len(rings)-1):
            for i,index in enumerate(rings[j]):
                tangent=Vector(vertices[rings[j][(i+1)%count]])-Vector(vertices[rings[j][(i-1)%count]])
                depth=Vector(vertices[rings[j+1][i]])-Vector(vertices[rings[j-1][i]])
                normal=tangent.cross(depth).normalized()
                if normal.dot(obj.data.vertices[index].normal)<0:normal=-normal
                normals[index]=normal
    obj.data.normals_split_custom_set([normals[loop.vertex_index] for loop in obj.data.loops])
    obj['city_junctions']='One connected wall domain; no intersecting shell, entry or support volumes'
    return obj,openings,roof


def curved_profile(name,points,t,asset,mat=12,thickness=.055,room=None):
    clean=[]
    for point in points:
        if not clean or (point-clean[-1]).length>1e-5:clean.append(point)
    if len(clean)>2 and (clean[0]-clean[-1]).length<1e-5:clean.pop()
    points=clean
    obj=profile_solid(name,points,-thickness*.5,thickness*.5,mat)
    coords=[]
    for v in obj.data.vertices:
        p=Vector((v.co.x,v.co.z));offset=v.co.y
        coords.append((p,offset))
        v.co=at(p,t,asset,offset)
    tagged(obj)
    normals=[]
    for poly in obj.data.polygons:
        offsets=[coords[obj.data.loops[i].vertex_index][1] for i in poly.loop_indices]
        flat=max(offsets)-min(offsets)<1e-6
        for loop in poly.loop_indices:
            index=obj.data.loops[loop].vertex_index
            normal=face_normal(coords[index][0],t,asset)
            if normal.dot(poly.normal)<0:normal=-normal
            normals.append(normal if flat else poly.normal)
    obj.data.normals_split_custom_set(normals)
    if room:
        index,left,step,bottom,height=room;uv=obj.data.uv_layers.active
        for face in obj.data.polygons:
            for loop in face.loop_indices:
                p=coords[obj.data.loops[loop].vertex_index][0]
                uv.data[loop].uv=(index+.001+.998*(p.x-left)/step,.001+.998*(p.y-bottom)/height)
    return obj


def diagnostic_closures(openings,asset):
    for name in ['garden','upper','entry']:
        contour=openings[name]
        curved_profile(name+'_temporary_closure',contour,.045,asset,12 if name!='entry' else 2)
        if name!='entry':curved_profile(name+'_rear_closure',contour,.955,asset,12)


def band(name,contour,t,asset,radius=.025,mat=1,detail=1):
    """A sealed extrusion follows the very same aperture as its structural wall."""
    vertices=[];faces=[];n=len(contour)
    for i,p in enumerate(contour):
        tangent=(contour[(i+1)%n]-contour[(i-1)%n]).normalized()
        normal=Vector((tangent.y,-tangent.x))
        for j in range(4):
            angle=math.tau*j/4
            vertices.append(at(p+normal*(radius*math.cos(angle)),t,asset,radius*math.sin(angle)))
    for i in range(n):
        for j in range(4):faces.append((i*4+j,i*4+(j+1)%4,((i+1)%n)*4+(j+1)%4,((i+1)%n)*4+j))
    return tagged(a.mesh(name,vertices,faces,mat,detail=detail),'seal')


def glazing(contour,bays,name,t,asset):
    low=min(p.x for p in contour);high=max(p.x for p in contour)
    bottom=min(p.y for p in contour);height=max(p.y for p in contour)-bottom;step=(high-low)/bays
    for i in range(bays):
        left=low+i*step;right=left+step
        part=clip_x(clip_x(contour,left+.025,True),right-.025,False)
        if len(part)<3:continue
        # One inhabited room spans the wing; mullions do not create separate
        # cubicles or restart the interior at every narrow glazing pane.
        obj=curved_profile(name+f'_pane_{i}',part,t,asset,12,room=(0,low,high-low,bottom,height))
        obj['city_part']='glazing'
        if i:
            strip=clip_x(clip_x(contour,left-.027,True),left+.027,False)
            if len(strip)>2:
                mullion=curved_profile(name+f'_mullion_{i}',strip,t,asset,5,.12)
                mullion['city_part']='glazing_frame';mullion['city_detail']=1
    band(name+'_sealed_perimeter',contour,t,asset,.040,1)


def shell_light(name,contour,t,asset):
    centre=sum(p.y for p in contour)/len(contour)
    # Work on the cyclic order, then keep only the continuous upper reveal.
    candidates=[i for i,p in enumerate(contour) if p.y>centre+.35]
    if not candidates:return
    start=next((i for i in candidates if (i-1)%len(contour) not in candidates),candidates[0])
    ids=[];i=start
    while i in candidates and len(ids)<len(contour):ids.append(i);i=(i+1)%len(contour)
    curve=[Vector(at(contour[i],t,asset,-.025)) for i in ids]
    lengths=[0.0]
    for p,q in zip(curve,curve[1:]):lengths.append(lengths[-1]+(q-p).length)
    count=max(2,math.ceil(lengths[-1]/.12));points=[];segment=0
    for i in range(count+1):
        distance=lengths[-1]*i/count
        while segment<len(curve)-2 and lengths[segment+1]<distance:segment+=1
        weight=(distance-lengths[segment])/max(1e-9,lengths[segment+1]-lengths[segment])
        points.append(tuple(curve[segment].lerp(curve[segment+1],weight)))
    channel=a.tube(name,points,.015,6,4,2);tagged(channel,'lighting')


def roof_panel(name,x0,x1,support,roof,min_z):
    """Clip the actual supporting triangles, not a second loft approximation.

    A sampled offset grid can still cross a curved support between its samples.
    Every laminate triangle here lies above one source plane by 4--16 mm.
    """
    support.data.calc_loop_triangles();allowed=set(roof['faces'])
    vertices=[];triangles=[];lookup={};normal_values=[]
    def clip(points,axis,value,greater):
        result=[]
        for p,q in zip(points,points[1:]+points[:1]):
            a=p[axis]>=value if greater else p[axis]<=value
            b=q[axis]>=value if greater else q[axis]<=value
            if a:result.append(p)
            if a!=b:
                t=(value-p[axis])/(q[axis]-p[axis]);result.append([a+(b-a)*t for a,b in zip(p,q)])
        return result
    def index(p):
        key=tuple(round(v,6) for v in p[:3])
        if key not in lookup:
            lookup[key]=len(vertices);vertices.append(tuple(p[:3]));normal_values.append(Vector(p[4:7]).normalized())
        return lookup[key]
    for tri in support.data.loop_triangles:
        if tri.polygon_index not in allowed or tri.normal.z<.25:continue
        points=[]
        for v,loop in zip(tri.vertices,tri.loops):
            p=support.data.vertices[v].co;n=support.data.corner_normals[loop].vector
            points.append([*p,roof['depth'][v],*n])
        for axis,value,greater in [(0,x0,True),(0,x1,False),(2,min_z,True),(3,.10,True),(3,.90,False)]:
            points=clip(points,axis,value,greater)
            if len(points)<3:break
        if len(points)<3:continue
        ids=[index(p) for p in points]
        for i in range(1,len(ids)-1):
            face=(ids[0],ids[i],ids[i+1])
            p,q,r=[Vector(vertices[v]) for v in face]
            if (q-p).cross(r-p).length>1e-9:triangles.append(face)
    count=len(vertices);faces=triangles+[tuple(v+count for v in reversed(f)) for f in triangles]
    edges={}
    for tri in triangles:
        for p,q in zip(tri,tri[1:]+tri[:1]):edges.setdefault(tuple(sorted((p,q))),[]).append((p,q))
    for key,values in edges.items():
        if len(values)==1:
            p,q=values[0];faces.append((p,q,q+count,p+count))
        elif len(values)!=2:raise ValueError('Split photovoltaic laminate')
    vertices=[(x,y,z+.016) for x,y,z in vertices]+[(x,y,z+.004) for x,y,z in vertices]
    obj=tagged(a.mesh(name,vertices,faces,3),'photovoltaic')
    normals=[]
    for face in obj.data.polygons:
        for loop in face.loop_indices:
            v=obj.data.loops[loop].vertex_index
            normals.append(normal_values[v%count]*(1 if v<count else -1) if len(face.vertices)==3 else face.normal)
    obj.data.normals_split_custom_set(normals)
    uv=obj.data.uv_layers.active
    for face in obj.data.polygons:
        for loop in face.loop_indices:
            p=obj.data.vertices[obj.data.loops[loop].vertex_index].co;uv.data[loop].uv=(p.x*.5,p.y*.5)


def entry(openings,asset,rear=False):
    contour=openings['entry'];x=asset['entry_x'];z=asset['entry_z'];t=.94 if rear else .055
    group='service_entry' if rear else 'primary_entry';prefix='rear' if rear else 'entry'
    target=Vector(at(Vector((x,z)),t,asset));direction=1 if rear else -1
    # The two leaves and the reveal inherit the structural surface. A doorway
    # is not modelled as a second structural capsule intersecting the facade.
    for i,(lo,hi) in enumerate([(x-.86,x),(x,x+.86)]):
        part=clip_x(clip_x(contour,lo+.006,True),hi-.006,False)
        obj=curved_profile(prefix+f'_sliding_leaf_{i}',part,t,asset,2,.065)
        obj['city_part']='door';obj['city_assembly']=group
        if not rear and i==0:
            # Conservative nearest leaf plane over the standing approach.
            yy=min(front(x+dx,z+dz,asset)*(1-t)+t*back(x+dx,z+dz) for dx in [-.55,0,.55] for dz in [.35,1.15,2.0])
            obj['city_primary_entry']=[target.x,yy-.075,target.z]
    band(prefix+'_continuous_door_seal',contour,t,asset,.036,1)
    drivepart=clip_x(clip_x(contour,x-.62,True),x+.62,False)
    # The head drive is captive inside the upper reveal, above standing height.
    headz=max(p.y for p in contour)-.08;drivepoints=[Vector((x-.62,headz-.045)),Vector((x+.62,headz-.045)),Vector((x+.62,headz+.045)),Vector((x-.62,headz+.045))]
    drive=curved_profile(prefix+'_recessed_drive',drivepoints,t,asset,5,.10)
    drive['city_part']='opening_drive';drive['city_assembly']=group;drive['city_detail']=1
    # Map the common control sheet onto the local wall, including its recess.
    control=m.service_panel(SimpleNamespace(**vars(a)),x+1.04,0,1.25,.18,.32,True)
    for v in control.data.vertices:
        p=Vector((v.co.x,v.co.z));off=v.co.y;v.co=at(p,1 if rear else 0,asset,direction*.025+off*direction*-1)
    tagged(control,'opening_control',group)
    sill=xy_solid(prefix+'_threshold',[(target.x-.91,target.y-.32),(target.x+.91,target.y-.32),(target.x+.91,target.y+.18),(target.x-.91,target.y+.18)],target.z-.045,target.z,5,.008)
    sill['city_part']='threshold';sill['city_assembly']=group
    shell_light(prefix+'_recessed_light',contour,t-.015 if not rear else t+.015,asset)
    return target


def fittings(openings,asset,support,roof):
    for name,bays in [('garden',asset['lower_bays']),('upper',asset['upper_bays'])]:
        for rear in [False,True]:glazing(openings[name],bays,name+('_rear' if rear else ''),.94 if rear else .065,asset)
        shell_light(name+'_soffit_light',openings[name],.035,asset)
    shell_light('passage_soffit_light',openings['passage'],.05,asset)
    contour=openings['upper'];lo=min(p.x for p in contour);hi=max(p.x for p in contour)
    for i in range(asset['fins']):
        x=lo+(hi-lo)*(.68+.24*i/max(1,asset['fins']-1))
        strip=clip_x(clip_x(contour,x-.045,True),x+.045,False)
        if len(strip)>2:
            obj=curved_profile('formed_sun_fin_'+str(i),strip,.045,asset,2,.32)
            obj['city_part']='sunshade';obj['city_detail']=1
    target=entry(openings,asset);entry(openings,asset,True)
    outer=openings['outer'];left=min(p.x for p in outer);right=max(p.x for p in outer)
    deck=spline([(right+.08,-.8),(right-.55,3.65),(0,3.9),(left+.25,2.8),
                 (left-.25,-2.7),(left+.55,-5.05),(target.x-1.7,-5.45),(target.x+2.4,-4.65)],56)
    tagged(xy_solid('continuous_foundation',deck,-.32,.18,0),'foundation')
    tagged(xy_solid('terrace_plinth',deck,.17,target.z-.035,7,.025),'terrace')
    for i in range(2):
        w=1.24+(1-i)*.18;y=-5.8+i*.32
        tread=spline([(target.x+w,y+.14),(target.x+w,-5.0),(target.x,-4.92),(target.x-w,-5.0),
                      (target.x-w,y+.14),(target.x-w+.15,y),(target.x,y-.035),(target.x+w-.15,y)],24)
        tagged(xy_solid('entry_step_'+str(i),tread,-.06,.13*(i+1),7,.018),'step')
    roof_panel('lower_roof_pv',left+1.1,-2.3,support,roof,3.0)
    roof_panel('upper_roof_pv',-1.8,max(p.x for p in openings['upper'])-.15,support,roof,5.0)
    # Standard service sheet carries vents, socket and fastener detail in PBR.
    panel=m.service_panel(SimpleNamespace(**vars(a)),asset['entry_x']-1.25,0,.95,.6,.8,False)
    for v in panel.data.vertices:
        p=Vector((v.co.x,v.co.z));v.co=at(p,1,asset,.025-v.co.y)
    tagged(panel,'service_access')


def seal_export_normals(objects):
    """Preserve authored normals, repair only missing corners on source faces.

    Grid/curve intersections can create micron edges. Weld those before export
    at the same tolerance as the native seam contract, not by voxel remeshing.
    """
    for obj in objects:
        bpy.context.view_layer.objects.active=obj
        modifier=obj.modifiers.new('Resolve micron boundary intersections','WELD');modifier.merge_threshold=1e-6
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        mesh=obj.data;mesh.update()
        normals=[Vector(n.vector) for n in mesh.corner_normals]
        missing=sum(n.length<.5 for n in normals)
        if missing:
            for face in mesh.polygons:
                for loop in face.loop_indices:
                    if normals[loop].length<.5:
                        normal=Vector(mesh.vertices[mesh.loops[loop].vertex_index].normal)
                        if normal.length<.5:normal=Vector(face.normal)
                        if normal.length<.5:raise ValueError('Missing source normal: '+obj.name)
                        normals[loop]=normal.normalized()
            mesh.normals_split_custom_set(normals)
        if any(not .99<n.vector.length<1.01 for n in mesh.corner_normals):
            raise ValueError('Invalid source normals before GLB: '+obj.name)


def export(asset,config,args):
    folder=args.out/asset['id'];folder.mkdir(parents=True,exist_ok=True)
    subprocess.run(['C:/Python313/python.exe',str(HERE/'profile_domain.py'),'--recipe',str(args.recipe.resolve()),
                    '--asset',asset['id'],'--out',str((folder/'domain.json').resolve())],check=True,
                   creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    domain=json.loads((folder/'domain.json').read_text())
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);a.PART=0;a.materials()
    obj,openings,roof=structural_skin(domain,asset)
    if args.diagnostic:diagnostic_closures(openings,asset)
    else:fittings(openings,asset,obj,roof)
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    for o in objects:
        bpy.context.view_layer.objects.active=o;o.select_set(True)
        bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);o.select_set(False)
    seal_export_normals(objects)
    audit=None if args.diagnostic else fittings_audit(objects)
    triangles=0
    for o in objects:o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
    if triangles>config['triangle_ceiling']:raise ValueError(f'Triangle ceiling exceeded: {triangles}')
    if audit and not audit['approach_clear']:raise ValueError('Blocked entrance: '+json.dumps(audit['approach_obstructions']))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'source.blend'))
    output=folder/('structure.glb' if args.diagnostic else 'master.glb')
    bpy.ops.export_scene.gltf(filepath=str(output),export_format='GLB',use_selection=True,
                              export_extras=True,export_yup=True,export_cameras=False,export_lights=False)
    obj.data.calc_loop_triangles()
    points=[v.co for o in objects for v in o.data.vertices]
    report={'id':asset['id'],'recipe':asset,'backend':config['method'],'neural_mesh':False,
            'status':'junction diagnostic' if args.diagnostic else 'manufactured source awaiting native art review',
            'triangles':triangles,'triangle_ceiling':config['triangle_ceiling'],'structural_triangles':len(obj.data.loop_triangles),
            'domain_components':1,'apertures':len(domain['boundaries'])-1,'source_sha256':sha(args.source),
            'reference_sha256':sha(args.reference),'master_sha256':sha(output),
            'recipe_sha256':sha(args.recipe),'author_sha256':sha(__file__),'domain_builder_sha256':sha(HERE/'profile_domain.py'),
            'toolchain':{name:sha(HERE/name) for name in ['author.py','manufacturing.py','details.py','finish_shell_house.py']},
            'bounds_z_up':[[min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]],
            'lineage':{'neural_source':str(args.source.resolve()),'neural_source_sha256':sha(args.source),
                       'reference':str(args.reference.resolve()),'reference_sha256':sha(args.reference),
                       'neural_vertices_reused':0,'reconstruction':'All final vertices rebuilt from a single connected architectural domain. Neural parts and images are design evidence, not automatically retopologized production geometry.'},
            'fittings':audit,'material_detail':'Shared generated PBR sheets; no source normal bake claimed',
            'surface_contacts':config.get('surface_contacts',[]),
            'art_accepted':False,'performance_accepted':False}
    (folder/('structure.json' if args.diagnostic else 'source.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recipe',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--reference',type=Path,required=True);p.add_argument('--asset')
    p.add_argument('--diagnostic',action='store_true')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);config=json.loads(args.recipe.read_text())
    for path,key in [(args.source,'neural_source_sha256'),(args.reference,'clean_reference_sha256')]:
        if sha(path)!=config[key]:raise ValueError('Unpinned input '+str(path))
    for asset in config['assets']:
        if not args.asset or args.asset==asset['id']:export(asset,config,args)


if __name__=='__main__':main()
