"""Author one original-reference house master and CPU neutral review views.

No textures, LOD cooking, procedural variants or runtime replacement. Front
and rear three-dimensional controls are joined by curved structural spans.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import shutil
import bpy
import bmesh
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

HERE=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def material(name,gray,rough=.65):
    m=bpy.data.materials.new(name);m.use_nodes=True
    shader=m.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=(gray,gray,gray,1)
    shader.inputs['Roughness'].default_value=rough
    return m


def mesh(name,vertices,faces,mat,smooth=True):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    bm=bmesh.new();bm.from_mesh(data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    for face in data.polygons:face.use_smooth=smooth
    data.materials.append(mat);obj['source_stage']='Original-reference neutral master'
    return obj


def spline(points,count):
    points=[Vector(p) for p in points];out=[]
    for j in range(count):
        t=j*len(points)/count;k=int(t);t-=k
        p,q,r,s=[points[i%len(points)] for i in [k-1,k,k+1,k+2]]
        out.append((2*q+(-p+r)*t+(2*p-5*q+4*r-s)*t*t+(-p+3*q-3*r+s)*t*t*t)*.5)
    return out


def miter(points):
    # Grid intersections can create submillimetre edges on a long curved lip.
    # Estimate its tangent over a physical arc, not those unstable short edges.
    def neighbour(i,direction,reach=.12):
        p=points[i];left=reach;j=i
        for _ in range(len(points)):
            k=(j+direction)%len(points);q=points[k]
            length=Vector((q.x-p.x,q.z-p.z)).length
            if length>=left:return p.lerp(q,left/length)
            left-=length;p=q;j=k
        return p
    out=[]
    for i,p in enumerate(points):
        before=p-neighbour(i,-1);after=neighbour(i,1)-p
        before=Vector((before.x,before.z)).normalized();after=Vector((after.x,after.z)).normalized()
        n1=Vector((before.y,-before.x));n2=Vector((after.y,-after.x));n=(n1+n2).normalized()
        n/=max(.25,n.dot(n2));out.append(Vector((n.x,0,n.y)))
    return out


def span(front,back,t,name,config):
    p=front.lerp(back,t);wave=math.sin(math.pi*t)
    crown=min(1,max(0,(p.z-2.8)/2.0))
    if name=='outer':
        p.z+=config['shape_controls']['roof_camber_m']*wave*crown
        swelling=.22*(1-crown)+.80*math.exp(-((p.z-6.25)/1.3)**2)
        p.x+=swelling*wave*math.tanh(p.x/4)
    else:p.z+=config['shape_controls']['soffit_camber_m']*wave*min(1,max(0,(p.z-.5)/2.5))
    return p


def structure(domain,config,mats):
    front=list(map(Vector,domain['front']));rear=list(map(Vector,domain['rear']));n=len(front)
    vertices=front+rear;faces=[tuple(f) for f in domain['faces']]+[tuple(i+n for i in reversed(f)) for f in domain['faces']]
    materials=[0]*len(faces);loops={};roof_faces=[];radius=domain['lip_radius_m']
    for loop in domain['loops']:
        name=loop['name'];ids=loop['indices'];f=[front[i] for i in ids];r=[rear[i] for i in ids]
        nf=miter(f);nr=miter(r);count=len(ids)
        body_f=[p+normal*radius+Vector((0,radius,0)) for p,normal in zip(f,nf)]
        body_r=[p+normal*radius-Vector((0,radius,0)) for p,normal in zip(r,nr)]
        loops[name]=(body_f,body_r)
        rings=[ids];parameters=[(0,0)]
        for theta in [math.pi/6,math.pi/3,math.pi/2]:parameters.append((0,theta))
        parameters.extend((j/16,math.pi/2) for j in range(1,16))
        parameters.extend((1,theta) for theta in [math.pi/2,math.pi/3,math.pi/6])
        for t,theta in parameters[1:]:
            ring=[]
            for pf,pr,normal_f,normal_r in zip(f,r,nf,nr):
                ff=pf+normal_f*radius*math.sin(theta)+Vector((0,radius*(1-math.cos(theta)),0))
                rr=pr+normal_r*radius*math.sin(theta)-Vector((0,radius*(1-math.cos(theta)),0))
                ring.append(len(vertices));vertices.append(span(ff,rr,t,name,config))
            rings.append(ring)
        rings.append([i+n for i in ids]);parameters.append((1,0))
        center=sum(p.z for p in f)/count
        for j,(one,two) in enumerate(zip(rings,rings[1:])):
            for i in range(count):
                k=(i+1)%count;face=(one[i],one[k],two[k],two[i])
                if name=='outer' and 4<=j<=16:
                    normal=(vertices[face[1]]-vertices[face[0]]).cross(vertices[face[3]]-vertices[face[0]])
                    middle=sum((vertices[v] for v in face),Vector())/4
                    if normal.z<0 and middle.z>3.3 and -normal.normalized().z>.30:roof_faces.append(tuple(face))
                faces.append(face)
                reveal=name!='outer' and j>=3 and j<len(rings)-4
                materials.append(1 if reveal and f[i].z>center+.35 else 2 if reveal else 0)
    obj=mesh('Primary_shell__continuous_3D_wings_and_support',vertices,faces,mats['shell'])
    obj.data.materials.append(mats['soffit']);obj.data.materials.append(mats['reveal'])
    for face,index in zip(obj.data.polygons,materials):face.material_index=index
    obj['architecture']='Shared wing/support topology; independently controlled 3D lips and rear profiles'
    # Neutral PV surface zones copy their structural support; no cell texture.
    if roof_faces and config.get('show_roof_zones',False):
        ids=sorted({i for f in roof_faces for i in f});mapping={i:j for j,i in enumerate(ids)}
        pv=mesh('Roof_laminate__neutral_surface_zone',[vertices[i]+Vector((0,0,.018)) for i in ids],
                [tuple(mapping[i] for i in f) for f in roof_faces],mats['solar'])
        bpy.context.view_layer.objects.active=pv
        solid=pv.modifiers.new('Thin roof laminate','SOLIDIFY');solid.thickness=.012;solid.offset=-1
        bpy.ops.object.modifier_apply(modifier=solid.name)
    return obj,loops


def lateral_apertures(body,config,mats):
    """Cut designed transverse apertures into the actual continuous shell.

    These remove the deep blank side wall. No remeshing or rounded primitive
    is merged into the exterior surface; front/rear load paths remain intact.
    """
    bpy.context.view_layer.objects.active=body
    body.data.materials.append(mats['soffit'])
    triangles=body.modifiers.new('Explicit curved-span triangulation','TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=triangles.name)
    cuts=[]
    for opening in config.get('lateral_apertures',[]):
        profile=spline(opening['profile_yz'],128);n=len(profile)
        vertices=[(x,p.x,p.y) for x in [opening['min_x'],opening['max_x']] for p in profile]
        faces=[tuple(reversed(range(n))),tuple(n+i for i in range(n))]
        faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
        cutter=mesh(opening['name']+'_tool',vertices,faces,mats['shell'])
        for mat in [mats['soffit'],mats['reveal'],mats['soffit']]:cutter.data.materials.append(mat)
        for face in cutter.data.polygons:face.material_index=3
        volumes=[]
        for target in [body,cutter]:
            bm=bmesh.new();bm.from_mesh(target.data);bmesh.ops.triangulate(bm,faces=list(bm.faces))
            bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
            if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
            if any(not e.is_manifold for e in bm.edges):raise ValueError('A Boolean operand is not a closed manifold: '+target.name)
            volumes.append(bm.calc_volume(signed=True))
            bm.to_mesh(target.data);bm.free()
        bpy.context.view_layer.objects.active=body
        operation=body.modifiers.new(opening['name'],'BOOLEAN');operation.operation='DIFFERENCE';operation.solver='MANIFOLD';operation.object=cutter
        bpy.ops.object.modifier_apply(modifier=operation.name);bpy.data.objects.remove(cutter,do_unlink=True)
        bm=bmesh.new();bm.from_mesh(body.data)
        remaining=bm.calc_volume(signed=True)
        if any(not e.is_manifold for e in bm.edges) or not volumes[0]-volumes[1]-.0001<=remaining<=volumes[0]+.0001:
            raise ValueError('Invalid structural difference: '+opening['name'])
        cuts.append({'name':opening['name'],'solver':'MANIFOLD','before_m3':volumes[0],'cutter_m3':volumes[1],'after_m3':remaining});bm.free()
        print('APERTURE',opening['name'],len(body.data.vertices),'vertices',len(body.data.polygons),'faces',flush=True)
        if opening['glazing_x'] is not None:
            x=opening['glazing_x']
            # Vertical side panes occupy a real lateral opening in the shell.
            points=[Vector((p.x,x,p.y)) for p in profile]
            low=min(p.x for p in points);high=max(p.x for p in points)
            for i in range(4):
                left=low+(high-low)*i/4;right=low+(high-low)*(i+1)/4
                pane=clip(clip(points,left+.02,True),right-.02,False)
                obj=closed_sheet(opening['name']+'_pane_'+str(i),pane,.025,mats['glass'])
                for vertex in obj.data.vertices:vertex.co.x,vertex.co.y=vertex.co.y,vertex.co.x
                bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
            tube(opening['name']+'_seal',[Vector((x,p.x,p.y)) for p in profile],.028,mats['metal'],True,8)
    # The primary lips already have modelled curvature. A global bevel after
    # triangulation pinches those lips and skinny Boolean intersections.
    # Preserve their analytic radii and split only the cut/reveal normals.
    bm=bmesh.new();bm.from_mesh(body.data)
    bmesh.ops.dissolve_degenerate(bm,dist=1e-5,edges=list(bm.edges))
    for face in bm.faces:face.smooth=True
    for edge in bm.edges:
        cut_junction=edge.is_manifold and ((edge.link_faces[0].material_index==3)!=(edge.link_faces[1].material_index==3))
        edge.smooth=not cut_junction or edge.calc_face_angle()<.65
    bm.to_mesh(body.data);bm.free()
    return cuts


def section(loops,name,t,config):return [span(f,r,t,name,config) for f,r in zip(*loops[name])]


def clip(points,x,greater):
    out=[]
    for p,q in zip(points,points[1:]+points[:1]):
        one=p.x>=x if greater else p.x<=x;two=q.x>=x if greater else q.x<=x
        if one:out.append(p.copy())
        if one!=two:out.append(p.lerp(q,(x-p.x)/(q.x-p.x)))
    clean=[]
    for p in out:
        if not clean or (p-clean[-1]).length>1e-6:clean.append(p)
    if len(clean)>2 and (clean[0]-clean[-1]).length<1e-6:clean.pop()
    return clean


def closed_sheet(name,points,thickness,mat,axis=1):
    if len(points)<3:return None
    # Rays can leave collinear samples on one manufactured edge. Remove only
    # sub-0.02 mm deviations before triangulation, avoiding coincident slivers.
    points=list(points)
    changed=True
    while changed and len(points)>3:
        changed=False
        for i,p in enumerate(points):
            a=points[i-1];b=points[(i+1)%len(points)];edge=b-a
            if edge.length>1e-8 and (p-a).cross(edge).length/edge.length<2e-5 and 0<=(p-a).dot(edge)<=edge.length_squared:
                points.pop(i);changed=True;break
    # X/Z is the dominant projection for glazing, reveals and the core wall.
    projected=[Vector((p.x,p.z,0)) for p in points]
    lookup={tuple(p):i for i,p in enumerate(projected)}
    tris=[tuple(v if isinstance(v,int) else lookup[tuple(v)] for v in tri) for tri in tessellate_polygon([projected])]
    n=len(points);shift=Vector();shift[axis]=thickness*.5
    vertices=[p-shift for p in points]+[p+shift for p in points]
    faces=tris+[tuple(i+n for i in reversed(tri)) for tri in tris]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    return mesh(name,vertices,faces,mat,False)


def tube(name,path,radius,mat,closed=False,sides=8):
    verts=[];faces=[]
    for i,p in enumerate(path):
        tangent=(path[(i+1)%len(path)]-path[i-1] if closed else path[min(i+1,len(path)-1)]-path[max(0,i-1)]).normalized()
        normal=tangent.cross(Vector((0,1,0)))
        if normal.length<.1:normal=tangent.cross(Vector((1,0,0)))
        normal.normalize();binormal=tangent.cross(normal).normalized()
        for j in range(sides):
            angle=math.tau*j/sides;verts.append(p+radius*(normal*math.cos(angle)+binormal*math.sin(angle)))
    for i in range(len(path) if closed else len(path)-1):
        for j in range(sides):faces.append((i*sides+j,i*sides+(j+1)%sides,((i+1)%len(path))*sides+(j+1)%sides,((i+1)%len(path))*sides+j))
    if not closed:faces.extend([tuple(reversed(range(sides))),tuple((len(path)-1)*sides+j for j in range(sides))])
    return mesh(name,verts,faces,mat)


def glazing(loops,name,t,bays,mats,config,edge=None,prefix='front',support=None):
    contour=section(loops,name,t,config)
    if edge is not None:contour=clip(contour,edge,False)
    low=min(p.x for p in contour);high=max(p.x for p in contour)
    if support is not None:
        # A curtain wall has vertical, planar manufactured panes. Intersect
        # their actual planes with the structural vault instead of tilting
        # glass between unrelated front lip points.
        low+=.18
        if edge is None:high-=.10
        def plan_y(x):
            if prefix=='rear':return 2.55 if name=='living_porch' else 3.20
            return (-4.1+2.15*((x+8.8)/8.5)**2) if name=='living_porch' else (-.15+.055*(x-4.0)**2)
        for i in range(bays):
            left=low+(high-low)*i/bays;right=low+(high-low)*(i+1)/bays
            yl,yr=plan_y(left),plan_y(right)
            bottom=[];top=[]
            for j in range(13):
                x=left+.018+(right-left-.036)*j/12;y=yl+(yr-yl)*(x-left)/(right-left)
                a,b=vertical_hits(contour,x);origin=Vector((x,y,(a.z+b.z)*.5))
                upper=support.ray_cast(origin,Vector((0,0,1)),10)[0]
                lower=support.ray_cast(origin,Vector((0,0,-1)),10)[0]
                if upper is None or lower is None:raise ValueError(f'Curtain wall leaves its structural support: {name}, {tuple(origin)}, up={upper}, down={lower}')
                top.append(upper-Vector((0,0,.012)));bottom.append(lower+Vector((0,0,.012)))
            pane=bottom+list(reversed(top));closed_sheet(f'{prefix}_{name}_pane_{i}',pane,.025,mats['glass'])
            tube(f'{prefix}_{name}_mullion_{i}',[bottom[0],top[0]],.028,mats['metal'],False,8)
            tube(f'{prefix}_{name}_head_{i}',top,.025,mats['metal'],False,6)
            tube(f'{prefix}_{name}_sill_{i}',bottom,.025,mats['metal'],False,6)
        return contour
    for i in range(bays):
        left=low+(high-low)*i/bays;right=low+(high-low)*(i+1)/bays
        pane=clip(clip(contour,left+.018,True),right-.018,False)
        if len(pane)>2:closed_sheet(f'{prefix}_{name}_pane_{i}',pane,.025,mats['glass'])
        if i:
            bar=clip(clip(contour,left-.025,True),left+.025,False)
            if len(bar)>2:closed_sheet(f'{prefix}_{name}_mullion_{i}',bar,.10,mats['metal'])
    tube(f'{prefix}_{name}_fitted_perimeter',contour,.028,mats['metal'],True,6)
    return contour


def vertical_hits(contour,x):
    points=[]
    for p,q in zip(contour,contour[1:]+contour[:1]):
        if (p.x<=x<q.x) or (q.x<=x<p.x):points.append(p.lerp(q,(x-p.x)/(q.x-p.x)))
    if len(points)<2:raise ValueError('Missing aperture intersection at '+str(x))
    return min(points,key=lambda p:p.z),max(points,key=lambda p:p.z)


def living_return(loops,config,mats,support):
    x=config['shape_controls']['living_right_edge_x'];ys=-4.1+2.15*((x+8.8)/8.5)**2
    end=vertical_hits(section(loops,'living_porch',.46,config),x)[1].y-.12
    sections=[]
    for i in range(4):
        y=ys+(end-ys)*i/3;origin=Vector((x,y,2))
        bottom=support.ray_cast(origin,Vector((0,0,-1)),10)[0];top=support.ray_cast(origin,Vector((0,0,1)),10)[0]
        if top is None or bottom is None:raise ValueError('Unfitted living-room return')
        sections.append((bottom,top))
    for i,(a,b) in enumerate(zip(sections,sections[1:])):
        p=[a[0],b[0],b[1],a[1]];shift=Vector((.016,0,0));n=4
        faces=[(0,1,2,3),(7,6,5,4)]+[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
        mesh('Living_glazed_return_'+str(i),[v-shift for v in p]+[v+shift for v in p],faces,mats['glass'],False)
        tube('Living_return_mullion_'+str(i),list(a),.028,mats['metal'],False,6)


def core(loops,config,mats):
    contour=section(loops,'living_porch',.46,config)
    def ceiling(x):return vertical_hits(contour,x)[1]
    def point(x,z):p=ceiling(x);return Vector((x,p.y-.12,z))
    floor=.37;left=-.35;right=4.9;door_x=2.05;half=.64;top=3.18;radius=.43
    arch=[point(door_x-half,floor),point(door_x-half,top-radius)]
    for j in range(17):
        angle=math.pi-j*math.pi/16
        arch.append(point(door_x+(half-radius if angle<math.pi/2 else -half+radius)+radius*math.cos(angle),top-radius+radius*math.sin(angle)))
    arch.append(point(door_x+half,floor))
    outer=[point(left,floor),*arch,point(right,floor)]
    outer.extend(point(right+(left-right)*j/32,ceiling(right+(left-right)*j/32).z-.015) for j in range(33))
    closed_sheet('Recessed_service_core__matched_to_vault',outer,.22,mats['reveal'])
    closed_sheet('Recessed_entry_leaf',list(reversed([p+Vector((0,.045,0)) for p in arch])),.07,mats['door'])
    tube('Entry_arch_reveal',arch,.045,mats['soffit'],False,8)
    # One flush actuator strip records the opening system without ornamental pieces.
    p=point(door_x+.40,1.15);tube('Entry_opening_strip',[p,p+Vector((0,0,.70))],.018,mats['metal'],False,6)


def deck(name,contour,bottom,top,mat):
    pts=spline(contour,128);n=len(pts);vertices=[]
    center=sum(pts,Vector((0,0)))/n
    rings=[(bottom,.98),(bottom+.035,1),(top-.035,1),(top,.994)]
    for z,scale in rings:vertices.extend((center+(p-center)*scale).to_3d()+Vector((0,0,z)) for p in pts)
    faces=[]
    for j in range(len(rings)-1):
        for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    faces.extend([tuple(reversed(range(n))),tuple((len(rings)-1)*n+i for i in range(n))])
    return mesh(name,vertices,faces,mat)


def stairs(mats,terrace):
    # One closed stepped sweep; risers and treads share their exact edges.
    profile=[(-1.44,0),(-1.44,.12),(-.96,.12),(-.96,.24),(-.48,.24),(-.48,.36),(0,.36),(0,0)]
    xs=[.55+4.4*j/32 for j in range(33)];vertices=[];faces=[];n=len(profile)
    outline=spline(terrace,128);center=sum(outline,Vector((0,0)))/len(outline)
    outline=[center+(p-center)*.994 for p in outline]
    for x in xs:
        hits=[]
        for p,q in zip(outline,outline[1:]+outline[:1]):
            if (p.x<=x<q.x) or (q.x<=x<p.x):hits.append(p.y+(q.y-p.y)*(x-p.x)/(q.x-p.x))
        boundary=min(hits)
        vertices.extend((x,y+boundary,z) for y,z in profile)
    for j in range(len(xs)-1):
        for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    faces.extend([tuple(reversed(range(n))),tuple((len(xs)-1)*n+i for i in range(n))])
    return mesh('Curved_entry_steps__shared_risers',vertices,faces,mats['floor'],False)


def fittings(loops,config,mats,body):
    shape=config['shape_controls']
    bm=bmesh.new();bm.from_mesh(body.data);support=BVHTree.FromBMesh(bm);bm.free()
    glazing(loops,'living_porch',shape['living_front_recess'],10,mats,config,shape['living_right_edge_x'],support=support)
    glazing(loops,'upper',shape['upper_front_recess'],9,mats,config,support=support)
    glazing(loops,'living_porch',.92,12,mats,config,3.7,'rear',support)
    glazing(loops,'upper',.90,8,mats,config,prefix='rear',support=support)
    living_return(loops,config,mats,support);core(loops,config,mats)
    if 'garden_recess' in loops:
        closed_sheet('Recess_between_inhabited_shells',section(loops,'garden_recess',.52,config),.10,mats['reveal'])
    for i in range(shape['upper_fins']):
        x=5.15+i*.38;y=-.15+.055*(x-4.0)**2-.34
        bottom=[];top=[]
        for xx,yy in [(x-.045,y-.21),(x+.045,y-.21),(x+.045,y+.21),(x-.045,y+.21)]:
            origin=Vector((xx,yy,6));lo=support.ray_cast(origin,Vector((0,0,-1)),10)[0];hi=support.ray_cast(origin,Vector((0,0,1)),10)[0]
            if lo is None or hi is None:raise ValueError('Unfitted vertical sunblade')
            bottom.append(lo+Vector((0,0,.012)));top.append(hi-Vector((0,0,.012)))
        faces=[(3,2,1,0),(4,5,6,7)]+[(j,(j+1)%4,(j+1)%4+4,j+4) for j in range(4)]
        mesh('Upper_fitted_sunblade_'+str(i),bottom+top,faces,mats['soffit'],False)
    terrace=[(9.15,-2.9),(9.7,-.1),(8.5,3.55),(3,4.35),(-5.4,3.7),(-8.75,2.1),(-9.55,-2.6),(-8.9,-4.95),(-6.5,-6.05),(-2.5,-6.3),(.5,-5.45),(3.5,-4.2),(6.4,-3.5)]
    deck('Continuous_terrace',terrace,-.13,.36,mats['floor'])
    stairs(mats,terrace)


def topology(objects):
    report=[]
    for obj in objects:
        bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
        bm.edges.ensure_lookup_table();bm.faces.ensure_lookup_table()
        remaining=set(bm.faces);components=0
        while remaining:
            stack=[remaining.pop()];components+=1
            while stack:
                face=stack.pop()
                for edge in face.edges:
                    for adjacent in edge.link_faces:
                        if adjacent in remaining:remaining.remove(adjacent);stack.append(adjacent)
        report.append({'name':obj.name,'components':components,'boundary_edges':sum(e.is_boundary for e in bm.edges),
                       'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'zero_faces':sum(f.calc_area()<1e-10 for f in bm.faces)})
        if report[-1]['zero_faces']:
            print('SMALL_FACES',obj.name,[(f.calc_area(),[tuple(v.co) for v in f.verts]) for f in bm.faces if f.calc_area()<1e-10],flush=True)
        bm.free()
    return report


def studio(args,config):
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU'
    scene.cycles.samples=16 if args.preview else 48;scene.cycles.use_denoising=True
    scene.render.threads_mode='FIXED';scene.render.threads=6
    scene.render.resolution_x=1000 if args.preview else 1600;scene.render.resolution_y=700 if args.preview else 1120
    scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    scene.world.use_nodes=True;world=scene.world.node_tree.nodes['Background'];world.inputs[0].default_value=(.6,.6,.6,1);world.inputs[1].default_value=.45
    # A neutral, continuous studio backdrop, outside the exported master.
    rings=[(30,0)]+[(30+20*math.sin(j*math.pi/48),20*(1-math.cos(j*math.pi/48))) for j in range(1,25)]+[(50,80)]
    vertices=[(r*math.cos(math.tau*i/128),r*math.sin(math.tau*i/128),z) for r,z in rings for i in range(128)]
    faces=[tuple(reversed(range(128)))]+[(j*128+i,j*128+(i+1)%128,(j+1)*128+(i+1)%128,(j+1)*128+i) for j in range(len(rings)-1) for i in range(128)]
    backdrop=mesh('Neutral studio cyclorama',vertices,faces,material('Neutral studio ground',.32,.9))
    backdrop.scale.x=backdrop.scale.y=2
    for name,position,power,size in [('Key',(-10,-12,18),3600,9),('Fill',(12,-5,13),1800,10),('Rim',(2,11,16),2600,8)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size
        obj=bpy.data.objects.new(name,light);scene.collection.objects.link(obj);obj.location=position;obj.rotation_euler=(Vector((0,0,3))-obj.location).to_track_quat('-Z','Y').to_euler()
    camera_data=bpy.data.cameras.new('Geometry review');camera=bpy.data.objects.new('Geometry review',camera_data);scene.collection.objects.link(camera);scene.camera=camera
    for name in args.views.split(','):
        view=config['views'][name];camera.location=view['position'];camera.rotation_euler=(Vector(view['target'])-camera.location).to_track_quat('-Z','Y').to_euler()
        camera_data.type='ORTHO' if 'ortho_scale' in view else 'PERSP';camera_data.ortho_scale=view.get('ortho_scale',24);camera_data.lens=view.get('lens',50)
        scene.render.filepath=str(args.out/(name+'.png'));bpy.ops.render.render(write_still=True)
    view=config['views']['hero'];camera.location=view['position'];camera.rotation_euler=(Vector(view['target'])-camera.location).to_track_quat('-Z','Y').to_euler()
    camera_data.type='PERSP';camera_data.lens=view['lens'];scene.render.filepath=str(args.out/'hero.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(args.out/'neutral-review.blend'))



def prepare_meshes(objects,smooth_bodies=()):
    # Audit the actual exported triangles, not only pre-export polygon areas.
    # Curved Boolean n-gons can otherwise introduce tiny slivers at export.
    for obj in objects:
        # Preserve the polygon-surface normals across export triangulation.
        # Fans in a thin cut reveal otherwise change its smooth weighting.
        original_corners=[[] for v in obj.data.vertices];tree=KDTree(len(obj.data.vertices))
        if obj in smooth_bodies:
            for vertex in obj.data.vertices:tree.insert(vertex.co,vertex.index)
            tree.balance()
            for polygon in obj.data.polygons:
                for loop in polygon.loop_indices:
                    original_corners[obj.data.loops[loop].vertex_index].append(
                        (polygon.material_index,polygon.normal.copy(),obj.data.corner_normals[loop].vector.copy()))
        bm=bmesh.new();bm.from_mesh(obj.data)
        # glTF duplicates vertices at normal/UV/material seams. Restore the
        # geometric manifold before dissolving tiny triangles at those seams.
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
        for _ in range(2):
            bmesh.ops.triangulate(bm,faces=list(bm.faces))
            bmesh.ops.dissolve_degenerate(bm,dist=1e-4,edges=list(bm.edges))
            bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-5)
        bmesh.ops.triangulate(bm,faces=list(bm.faces))
        for _ in range(16):
            tiny=[f for f in bm.faces if f.calc_area()<1e-10]
            if not tiny:break
            for face in tiny:
                if not face.is_valid:continue
                edge=min(face.edges,key=lambda e:e.calc_length())
                if edge.calc_length()>2e-4:
                    # An imported sliver can have long, almost collinear edges.
                    # Flip a coplanar diagonal instead of moving its endpoints.
                    flipped=False
                    for diagonal in sorted(face.edges,key=lambda e:-e.calc_length()):
                        adjacent=[f for f in diagonal.link_faces if f!=face]
                        if len(adjacent)!=1 or len(adjacent[0].verts)!=3:continue
                        a,b=diagonal.verts;c=next(v for v in face.verts if v not in diagonal.verts)
                        d=next(v for v in adjacent[0].verts if v not in diagonal.verts)
                        plane=(b.co-a.co).cross(d.co-a.co)
                        one=(d.co-c.co).cross(a.co-c.co);two=(c.co-d.co).cross(b.co-d.co)
                        if min(one.length,two.length)<2e-10 or one.dot(two)<=0 or plane.length<1e-12:continue
                        if abs((c.co-a.co).dot(plane.normalized()))>1e-4:continue
                        try:flipped=bmesh.utils.edge_rotate(diagonal,False) is not None
                        except ValueError:flipped=False
                        if flipped:break
                    if flipped:continue
                    raise ValueError('A degenerate triangle exceeds the 0.1 mm endpoint cleanup bound: '+obj.name)
                ends=list(edge.verts);middle=(ends[0].co+ends[1].co)*.5
                bmesh.ops.pointmerge(bm,verts=ends,merge_co=middle)
            bmesh.ops.triangulate(bm,faces=list(bm.faces))
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bm.to_mesh(obj.data);bm.free()
        if obj in smooth_bodies:
            candidates=[]
            for vertex in obj.data.vertices:
                nearest=tree.find(vertex.co)
                ids=[i for _,i,_ in tree.find_range(vertex.co,nearest[2]+2e-6)]
                candidates.append([corner for i in ids for corner in original_corners[i]])
            normals=[None]*len(obj.data.loops)
            for polygon in obj.data.polygons:
                for loop in polygon.loop_indices:
                    choices=[c for c in candidates[obj.data.loops[loop].vertex_index] if c[0]==polygon.material_index]
                    normals[loop]=max(choices,key=lambda c:c[1].dot(polygon.normal))[2] if choices else obj.data.corner_normals[loop].vector.copy()
            obj.data.normals_split_custom_set(normals)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recipe',type=Path,required=True)
    p.add_argument('--reference',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--views',default='hero,front,side,back,porch');p.add_argument('--preview',action='store_true')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);args.out=args.out.resolve();args.out.mkdir(parents=True,exist_ok=True)
    config=json.loads(args.recipe.read_text(encoding='utf-8'))
    if sha(args.reference)!=config['reference_sha256']:raise ValueError('The original reference hash does not match this master recipe')
    subprocess.run(['C:/Python313/python.exe',str(HERE/'reference_house_domain.py'),'--recipe',str(args.recipe.resolve()),'--out',str(args.out/'domain.json')],check=True,creationflags=0x08000000)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    mats={k:material('Neutral study - '+k,g,r) for k,g,r in [('shell',.63,.55),('soffit',.40,.70),('reveal',.29,.65),('glass',.16,.30),('metal',.25,.40),('solar',.33,.55),('door',.47,.65),('floor',.55,.8)]}
    body,loops=structure(json.loads((args.out/'domain.json').read_text()),config,mats)
    cuts=lateral_apertures(body,config,mats);fittings(loops,config,mats,body)
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    prepare_meshes(objects,[body])
    audit=topology(objects)
    failed=[item for item in audit if item['components']!=1 or item['nonmanifold_edges'] or item['zero_faces']]
    if failed:raise ValueError('Master topology failed: '+json.dumps(failed))
    triangles=0
    for obj in objects:obj.data.calc_loop_triangles();triangles+=len(obj.data.loop_triangles)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.out/'master.blend'))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=str(args.out/'master.glb'),export_format='GLB',use_selection=True,export_extras=True,export_cameras=False,export_lights=False)
    report={'stage':config['stage'],'reference':str(args.reference),'reference_sha256':sha(args.reference),
            'recipe_sha256':sha(args.recipe),'author_sha256':sha(__file__),'domain_tool_sha256':sha(HERE/'reference_house_domain.py'),'spline_tool_sha256':sha(HERE/'profile_domain.py'),
            'master_sha256':sha(args.out/'master.glb'),'triangles':triangles,'objects':len(objects),'topology':audit,
            'textures':0,'lods_generated':False,'variants_generated':False,'native_integration':False,
            'art_accepted':False,'lineage':'Directed 3D surface master authored against original board; zero neural vertices',
            'unseen_sides':'Inferred from board side panels; not measured reconstruction','views':config['views'],'lateral_cuts':cuts,
            'topology_passed':True,'export_sliver_cleanup_m':.0001,'render_engine':'Cycles CPU','preview':args.preview,'source_budget_stage':'Unreduced shape master, not game LOD0'}
    (args.out/'source.json').write_text(json.dumps(report,indent=2)+'\n')
    (args.out/'recipe.json').write_bytes(args.recipe.read_bytes())
    snapshot=args.out/'authoring';snapshot.mkdir(exist_ok=True)
    for source in [Path(__file__),HERE/'reference_house_domain.py',HERE/'profile_domain.py']:shutil.copy2(source,snapshot/source.name)
    print('MASTER',triangles,'triangles',len(objects),'objects',flush=True)
    studio(args,config)


if __name__=='__main__':main()
