"""Rebuild the reviewed neural house as editable, closed manufactured surfaces.

Run in background Blender. The neural parts are immutable design evidence,
not silently relabelled procedural vertices. This is a directed reconstruction;
the recipe, source hashes and reconstruction extent are recorded explicitly.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace

import bpy
import bmesh
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

sys.path.insert(0, str(Path(__file__).resolve().parent))
import author as a
import manufacturing as m
from details import audit as fittings_audit


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def spline(knots, count=128):
    """Periodic Catmull-Rom with shared parameterization for paired profiles."""
    points = [Vector(p) for p in knots]
    result = []
    for j in range(count):
        t = j * len(points) / count
        k = int(t); t -= k
        p, q, r, s = [points[i % len(points)] for i in (k-1, k, k+1, k+2)]
        result.append((2*q + (-p+r)*t + (2*p-5*q+4*r-s)*t*t + (-p+3*q-3*r+s)*t*t*t)*.5)
    return result


def tagged(obj, role=None, assembly=None):
    obj['city_construction'] = 'closed_matched_surface'
    if role: obj['city_part'] = role
    if assembly: obj['city_assembly'] = assembly
    # Parametric winding differs between front/back profiles. Recalculate once
    # on the complete closed solid, without merging distinct functional parts.
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data); bm.free(); obj.data.update()
    return obj


def profile_solid(name, contour, front, back, mat, detail=0, bevel=0):
    obj = m.extrusion(SimpleNamespace(**vars(a)), name, [tuple(p) for p in contour], front, back, mat, bevel, detail)
    return tagged(obj)


def deform(point, v, center):
    # A small rear taper and a continuous depth bulge keep the side elevation
    # inhabited, instead of stretching a flat facade into an empty extrusion.
    taper = 1 - .065*v + .045*math.sin(math.pi*v)
    p = center + (point-center)*taper
    return Vector((p.x + .20*math.sin(math.pi*v), p.y + .10*math.sin(math.pi*v)))


def shell(name, outer, inner, front, back, count=96, soffit=True, body=0, rear_rise=0):
    out = spline(outer, count); ins = spline(inner, count)
    center = sum(out, Vector((0, 0))) / count
    # Cross-section around the wall thickness: outside, rolled rear lip,
    # inside, rolled front lip. Its periodic seam is welded by construction.
    sections = []
    for j in range(9): sections.append((0, j/8, .10 if j==0 else -.10 if j==8 else 0, 'outside'))
    for j in range(1,6):
        t=j/6; sections.append((t, 1, -.10 + .20*math.sin(math.pi*t), 'rear_lip'))
    for j in range(7): sections.append((1, 1-j/6, -.10 if j==0 else .10 if j==6 else 0, 'inside'))
    for j in range(1,6):
        t=1-j/6; sections.append((t, 0, .10-.20*math.sin(math.pi*t), 'front_lip'))
    vertices=[]; faces=[]; materials=[]; coords=[]
    arc=[0.0]
    for k in range(count): arc.append(arc[-1]+(out[(k+1)%count]-out[k]).length)
    wall_uv=[0.0]
    mean_thickness=sum((o-i).length for o,i in zip(out,ins))/count
    for prev,cur in zip(sections,sections[1:]+sections[:1]):
        wall_uv.append(wall_uv[-1]+math.hypot((cur[0]-prev[0])*mean_thickness,(cur[1]-prev[1])*(back-front)+cur[2]-prev[2]))
    for mix,v,offset,label in sections:
        for i in range(count):
            p=deform(out[i].lerp(ins[i], mix), v, center)
            rise=min(1,v*3.5);rise=rise*rise*(3-2*rise)
            p.y+=rear_rise*rise*max(0,(p.y-.43)/3.5)
            vertices.append((p.x,front+(back-front)*v+offset,p.y))
    for j,(mix,v,off,label) in enumerate(sections):
        jn=(j+1)%len(sections)
        for i in range(count):
            ni=(i+1)%count
            faces.append((j*count+i,j*count+ni,jn*count+ni,jn*count+i))
            is_ceiling=ins[i].y>center.y+.5
            material=2 if label=='inside' and soffit and is_ceiling else 1 if label=='inside' else body
            materials.append(material)
            # Shared metric unwrap. A deliberate seam is placed on the right
            # jamb; no per-triangle planar projection on the curved shell.
            coords.append(((arc[i]*.5,wall_uv[j]*.5),(arc[i+1]*.5,wall_uv[j]*.5),
                           (arc[i+1]*.5,wall_uv[j+1]*.5),(arc[i]*.5,wall_uv[j+1]*.5)))
    obj=a.mesh(name,vertices,faces,face_materials=materials)
    uv=obj.data.uv_layers.active
    for face,values in zip(obj.data.polygons,coords):
        for loop,value in zip(face.loop_indices,values):uv.data[loop].uv=value
    tagged(obj,'shell',name)
    return {'object':obj,'outer':out,'inner':ins,'center':center,'front':front,'back':back}


def curve_band(name, contour, y, radius, mat, detail=1, sides=6):
    """Closed profile extrusion around a closed curve, without duplicate caps."""
    n=len(contour); vertices=[];faces=[]
    for i,p in enumerate(contour):
        tangent=(contour[(i+1)%n]-contour[(i-1)%n]).normalized()
        normal=Vector((tangent.y,-tangent.x))
        for j in range(sides):
            angle=j*math.tau/sides
            vertices.append((p.x+normal.x*radius*math.cos(angle),y+radius*math.sin(angle),p.y+normal.y*radius*math.cos(angle)))
    for i in range(n):
        for j in range(sides):
            faces.append((i*sides+j,i*sides+(j+1)%sides,((i+1)%n)*sides+(j+1)%sides,((i+1)%n)*sides+j))
    return tagged(a.mesh(name,vertices,faces,mat,detail=detail),'seal')


def clip_x(points, value, greater):
    result=[]
    for p,q in zip(points,points[1:]+points[:1]):
        pi=p.x>=value if greater else p.x<=value
        qi=q.x>=value if greater else q.x<=value
        if pi:result.append(p)
        if pi!=qi:result.append(p.lerp(q,(value-p.x)/(q.x-p.x)))
    return result


def glazing(wing, bays, name, rear=False):
    v=.94 if rear else .06
    contour=[deform(p,v,wing['center']) for p in wing['inner']]
    y=wing['front']+(wing['back']-wing['front'])*v
    low=min(p.x for p in contour); high=max(p.x for p in contour)
    bottom=min(p.y for p in contour)
    height=max(p.y for p in contour)-bottom
    step=(high-low)/bays
    for i in range(bays):
        left=low+i*step;right=left+step
        part=clip_x(clip_x(contour,left+.026,True),right-.026,False)
        if len(part)<3:continue
        obj=profile_solid(name+f'_pane_{i}',part,y-.028,y+.028,12)
        uv=obj.data.uv_layers.active
        for face in obj.data.polygons:
            for loop in face.loop_indices:
                p=obj.data.vertices[obj.data.loops[loop].vertex_index].co
                uv.data[loop].uv=(i+.001+.998*(p.x-left)/step,.001+.998*(p.z-bottom)/height)
        obj['city_part']='glazing'
        if i:
            strip=clip_x(clip_x(contour,left-.027,True),left+.027,False)
            if len(strip)>2:
                profile_solid(name+f'_mullion_{i}',strip,y-.07,y+.065,5,1,.008)
    curve_band(name+'_continuous_gasket',contour,y,.045,1,sides=6)
    # A thin light channel sits inside the front soffit, not on a floating bar.
    if not rear:
        points=contour[8:len(contour)//2]
        obj=a.tube(name+'_soffit_channel',[(p.x,y-.22,p.y) for p in points],.024,6,6,2)
        tagged(obj,'lighting')
    return contour,y


def solar_patch(wing,name):
    out=wing['outer'];center=wing['center'];n=len(out)
    indices=list(range(int(n*.075),int(n*.43)+1,2))
    rows=13;vertices=[];faces=[];uvfaces=[]
    for layer in range(2):
        for j in range(rows):
            v=.13+.74*j/(rows-1)
            for i in indices:
                p=deform(out[i],v,center)
                tangent=out[(i+1)%n]-out[(i-1)%n]
                normal=Vector((tangent.y,-tangent.x)).normalized()
                p+=normal*(.020 if layer==0 else .005)
                vertices.append((p.x,wing['front']+(wing['back']-wing['front'])*v,p.y))
    w=len(indices);layer_count=w*rows
    for layer in range(2):
        for j in range(rows-1):
            for i in range(w-1):
                q=layer*layer_count+j*w+i
                faces.append((q,q+1,q+w+1,q+w) if layer==0 else (q+w,q+w+1,q+1,q))
    perimeter=list(range(w))+[j*w+w-1 for j in range(1,rows)]+list(range((rows-1)*w+w-2,(rows-1)*w-1,-1))+[j*w for j in range(rows-2,0,-1)]
    for p,q in zip(perimeter,perimeter[1:]+perimeter[:1]):faces.append((p,q,q+layer_count,p+layer_count))
    obj=tagged(a.mesh(name,vertices,faces,3),'photovoltaic')
    # Metric roof unwrap; the runtime filters the cell grid from derivatives.
    uv=obj.data.uv_layers.active
    for face in obj.data.polygons:
        for loop in face.loop_indices:
            p=obj.data.vertices[obj.data.loops[loop].vertex_index].co
            uv.data[loop].uv=(p.x*.5,p.y*.5)


def xy_solid(name,contour,bottom,top,mat=0,bevel=.035):
    # Four connected perimeter rings give the slab an actual edge radius.
    # This avoids beveling every triangulation edge of a concave planar cap.
    points=[Vector(p) for p in contour];n=len(points)
    area=sum(points[i].x*points[(i+1)%n].y-points[(i+1)%n].x*points[i].y for i in range(n))
    if area<0:points.reverse()
    inset=[]
    bevel=min(bevel,(top-bottom)*.4)
    for i,p in enumerate(points):
        prev=(p-points[(i-1)%n]).normalized();nxt=(points[(i+1)%n]-p).normalized()
        normal=Vector((-prev.y-nxt.y,prev.x+nxt.x)).normalized()
        inset.append(p+normal*bevel/max(.25,normal.dot(Vector((-nxt.y,nxt.x)))))
    vertices=[];faces=[]
    for ring,z in [(inset,bottom),(points,bottom+bevel),(points,top-bevel),(inset,top)]:
        vertices.extend((p.x,p.y,z) for p in ring)
    for j in range(3):
        for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    shape=[Vector((p.x,p.y,0)) for p in inset];lookup={tuple(v):i for i,v in enumerate(shape)}
    for tri in tessellate_polygon([shape]):
        ids=tuple(v if isinstance(v,int) else lookup[tuple(v)] for v in tri)
        faces.append(tuple(reversed(ids)));faces.append(tuple(i+3*n for i in ids))
    obj=tagged(a.mesh(name,vertices,faces,mat))
    for face in obj.data.polygons:face.use_smooth=abs(face.normal.z)<.75 and n>8
    return obj


def rounded_door(x,z,width=1.7,height=2.6):
    w=width*.5; r=.35
    points=[Vector((x-w,z)),Vector((x+w,z)),Vector((x+w,z+height-r))]
    for k in range(1,13):
        t=k*math.pi/24;points.append(Vector((x+w-r+r*math.cos(t),z+height-r+r*math.sin(t))))
    for k in range(13):
        t=math.pi/2+k*math.pi/24;points.append(Vector((x-w+r+r*math.cos(t),z+height-r+r*math.sin(t))))
    return points


def entry(p):
    x=p['entry_x'];y=p['entry_y'];z=.43; assembly='primary_entry'
    contour=rounded_door(x,z)
    # Continuous structural core mates with both inhabited envelopes. The
    # doorway is a real hole in it, with two closed leaves behind the reveal.
    outer=[(x+1.35,2.05),(x+1.25,3.35),(x+.35,3.8+p['support_rise']*.3),
           (x-.7,3.55),(x-1.5,2.5),(x-1.4,.12),(x,.1),(x+1.35,.25)]
    # Same angular landmarks, with a near-flat sill and usable standing sides.
    inner=[(x+.9,1.8),(x+.82,2.75),(x+.3,3.12),(x-.5,3.05),
           (x-.9,2.0),(x-.9,.43),(x,.43),(x+.9,.43)]
    core=shell('entry_structural_core',outer,inner,y+.1,2.8,64,False,body=21,rear_rise=.65+p['support_rise'])
    back_contour=[deform(q,1,core['center']) for q in core['inner']]
    for q in back_contour:q.y+=(.65+p['support_rise'])*max(0,(q.y-.43)/3.5)
    profile_solid('rear_service_wall',back_contour,2.66,2.82,20)
    door_y=y+.42
    for i,(left,right) in enumerate([(x-.85,x),(x,x+.85)]):
        leaf=clip_x(clip_x(contour,left+.007,True),right-.007,False)
        obj=profile_solid(f'entry_sliding_leaf_{i}',leaf,door_y-.025,door_y+.075,2)
        uv=obj.data.uv_layers.active
        for face in obj.data.polygons:
            for loop in face.loop_indices:
                point=obj.data.vertices[obj.data.loops[loop].vertex_index].co
                uv.data[loop].uv=((point.x-x+.85)/1.7,(point.z-z)/2.6)
        obj['city_part']='door';obj['city_assembly']=assembly
        if i==0:obj['city_primary_entry']=[x,door_y-.075,z]
    curve_band('entry_sealed_reveal',contour,door_y-.04,.055,1,1,8)
    drive=profile_solid('entry_recessed_drive',[(x-.66,2.85),(x+.66,2.85),(x+.59,3.01),(x-.59,3.01)],door_y-.07,door_y+.12,5,1,.016)
    drive['city_part']='opening_drive';drive['city_assembly']=assembly
    panel=m.service_panel(SimpleNamespace(**vars(a)),x+1.08,y-.015,1.28,.20,.36,True)
    tagged(panel,'opening_control',assembly)
    sensor=m.service_panel(SimpleNamespace(**vars(a)),x,door_y-.10,2.87,.15,.07,True)
    tagged(sensor,'presence_sensor',assembly)
    threshold=xy_solid('door_threshold',[(x-.94,door_y-.25),(x+.94,door_y-.25),
                                       (x+.94,door_y+.14),(x-.94,door_y+.14)],.39,z,5,.008)
    threshold['city_part']='threshold';threshold['city_assembly']=assembly
    for xx in [x-.83,x+.83]:
        obj=a.tube('entry_jamb_light',[(xx,door_y-.085,z+.16),(xx,door_y-.085,2.68)],.013,6,6,2)
        tagged(obj,'lighting',assembly)
    return x,y,z


def finish_house(p):
    low=shell('lower_inhabited_envelope',p['lower_outer'],p['lower_inner'],p['lower_front'],p['lower_back'])
    upper=shell('upper_inhabited_envelope',p['upper_outer'],p['upper_inner'],p['upper_front'],p['upper_back'])
    for wing,bays,name in [(low,p['lower_bays'],'garden'),(upper,p['upper_bays'],'upper')]:
        glazing(wing,bays,name);glazing(wing,bays,name+'_rear',True)
        solar_patch(wing,name+'_conformal_pv')
    w=p['support_width'];rise=p['support_rise']
    out=[(7.1*w,2.25),(6.3*w,3.9+rise),(4.2,4.5+rise),(3.7,3.75+rise),
         (4.05,2.3),(4.3,.3),(5.6*w,.04),(7.1*w,.62)]
    ins=[(6.4*w,2.2),(5.9*w,3.15+rise),(4.9,3.6+rise),(4.6,3.2+rise),
         (4.8,2.1),(4.85,.85),(5.65*w,.57),(6.35*w,1.1)]
    arch=shell('continuous_load_bearing_arch',out,ins,p['upper_front']+.12,2.4,80,True)
    arc=arch['inner'][6:38]
    channel=a.tube('arch_recessed_light',[(q.x,p['upper_front']+.32,q.y) for q in arc],.019,6,6,2)
    tagged(channel,'lighting')
    x,y,z=entry(p)
    # Inset louvers follow the accepted aperture at both ends; they terminate
    # in its reveal instead of passing through the shell.
    c=upper['inner'];lo=min(v.x for v in c);hi=max(v.x for v in c)
    yy=p['upper_front']+.25
    for i in range(p['fins']):
        xx=lo+(hi-lo)*(.68+.25*i/max(1,p['fins']-1))
        strip=clip_x(clip_x(c,xx-.045,True),xx+.045,False)
        if len(strip)>2:
            profile_solid(f'formed_timber_sun_fin_{i}',strip,yy-.14,yy+.22,2,1,.018)
    # A single shaped footing anchors the whole building. The accessible deck
    # and two lower treads share their outline, levels and drainage fall.
    left=min(v.x for v in low['outer']);right=max(v.x for v in upper['outer'])
    back=max(p['lower_back'],p['upper_back'])+.15
    deck=spline([(right+.3,-.7),(right-.1,back),(0,back+.15),(left-.2,3.0),
                 (left-.55,-2.5),(left+.6,p['lower_front']-1.45),(x-1.5,y-2.5),(x+2.5,y-2.15)],64)
    xy_solid('continuous_foundation',deck,-.35,.18,0)
    xy_solid('terrace_plinth',deck,.16,.40,7,.025)
    for i in range(2):
        width=1.25+(2-i)*.16;front=y-3.0+(i*.33);back_step=y-2.25
        points=spline([(x+width,front+.13),(x+width,back_step),(x,back_step+.08),(x-width,back_step),
                       (x-width,front+.13),(x-width+.15,front),(x,front-.04),(x+width-.15,front)],32)
        xy_solid('entry_step_'+str(i),points,-.08,.13*(i+1),7,.018)
    # Functional service access and water handling on the rear, using common
    # sheets for vents, sockets and fasteners rather than thousands of bolts.
    panel=m.service_panel(SimpleNamespace(**vars(a)),p['entry_x'],2.9,.9,.65,1.05,False)
    for vertex in panel.data.vertices:vertex.co.y=5.8-vertex.co.y
    tagged(panel,'service_access')
    for xx in [-.35,.35]:
        points=[(2.2+xx,2.9,3.8),(2.2+xx,2.9,1.1),(2.2+xx,3.05,.45)]
        tagged(a.tube('integrated_water_drop',points,.045,5,8,2),'drainage')
    return [o for o in bpy.context.scene.objects if o.type=='MESH']


def export(p,config,out,source,reference):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    a.PART=0
    objects=finish_house(p)
    for o in objects:
        bpy.context.view_layer.objects.active=o;o.select_set(True)
        bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
        o.select_set(False)
    report_fittings=fittings_audit(objects)
    for role in ['door','threshold','opening_drive','opening_control']:
        if not report_fittings['parts'].get(role):raise ValueError('Missing functional detail: '+role)
    folder=out/p['id'];folder.mkdir(parents=True,exist_ok=True)
    for o in objects:o.select_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'source.blend'))
    bpy.ops.export_scene.gltf(filepath=str(folder/'master.glb'),export_format='GLB',use_selection=True,
                              export_extras=True,export_yup=True,export_cameras=False,export_lights=False)
    points=[v.co for o in objects for v in o.data.vertices]
    triangles=0
    for o in objects:o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
    report={'id':p['id'],'recipe':p,'triangles':triangles,'triangle_ceiling':config['triangle_ceiling'],
            'bounds_z_up':[[min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]],
            'master_sha256':sha(folder/'master.glb'),'author_sha256':sha(__file__),
            'toolchain':{name:sha(Path(__file__).parent/name) for name in ['author.py','manufacturing.py','details.py']},
            'backend':config['method'],'neural_mesh':False,
            'lineage':{'neural_source':str(source.resolve()),'neural_source_sha256':sha(source),
                       'reference':str(reference.resolve()),'reference_sha256':sha(reference),
                       'neural_vertices_reused':0,'reconstruction':'All final surfaces rebuilt from reviewed profile controls. Neural part decomposition and images guide the design; no automatic retopology claim.'},
            'fittings':report_fittings,'material_detail':'Shared generated PBR tiles; no source normal bake claimed',
            'art_accepted':False,'performance_accepted':False}
    (folder/'source.json').write_text(json.dumps(report,indent=2)+'\n')
    if triangles>config['triangle_ceiling']:raise ValueError(f'Triangle budget exceeded: {triangles}')
    if not report_fittings['approach_clear']:raise ValueError('Blocked entry: '+json.dumps(report_fittings['approach_obstructions']))
    print('FINISHED_SOURCE',p['id'],triangles,flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--recipe',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--asset')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    config=json.loads(args.recipe.read_text())
    for path,key in [(args.source,'neural_source_sha256'),(args.reference,'clean_reference_sha256')]:
        if sha(path)!=config[key]:raise ValueError('Unpinned source: '+str(path))
    a.materials()
    enamel=a.MATS[1].copy();enamel.name='teal_enamel';enamel['city_material']='teal_enamel'
    shader=enamel.node_tree.nodes['Principled BSDF']
    shader.inputs['Roughness'].default_value=.49;shader.inputs['Metallic'].default_value=.035
    a.MATS.append(enamel)
    for asset in config['assets']:
        if not args.asset or args.asset==asset['id']:export(asset,config,args.out,args.source,args.reference)


if __name__=='__main__':main()
