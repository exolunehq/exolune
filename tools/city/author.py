"""Architectural backend of the local production chain. Execute in background Blender.

The source is an editable metric assembly. Closed double surfaces, independent
reveals, roofs and fittings retain their identities through reduction and review.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import random
import sys
import bpy
from mathutils import Vector, Matrix
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parent))
from architecture import build as extended_architecture
from details import decorate, audit as audit_fittings
import manufacturing

TAU = math.tau
MATERIALS = [
    ('ceramic', (0.76, .72, .62), .38, .02),
    ('teal', (.022, .115, .106), .31, .20),
    ('timber', (.38, .19, .065), .48, 0),
    ('solar', (.025, .092, .21), .21, .45),
    ('glazing', (.048, .13, .14), .14, .50),
    ('bronze', (.43, .25, .085), .30, .65),
    ('light', (1, .48, .13), .35, 0),
    ('stone', (.34, .33, .28), .80, 0),
    ('leaf', (.075, .20, .042), .65, 0),
    ('soil', (.052, .036, .021), .96, 0),
    ('flower', (.38, .16, .48), .62, 0),
    ('water', (.035, .23, .25), .10, .35),
    ('room_glass', (.065, .11, .105), .23, 0),
    ('cabin_glass', (.055, .095, .10), .20, 0),
    ('door_glass', (.065, .11, .105), .24, 0),
    ('rubber', (.020, .025, .024), .84, 0),
    ('satin_metal', (.55, .57, .56), .38, 1),
    ('control_screen', (.018, .085, .10), .30, 0),
    ('service_panel', (.10, .20, .19), .47, .45),
    ('control_panel', (.12, .23, .22), .43, .35),
    ('slatted_timber', (.38, .19, .065), .48, 0),
]
MATS = []
PART = 0


def materials():
    MATS.clear()
    for name, rgb, rough, metal in MATERIALS:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bs = m.node_tree.nodes.get('Principled BSDF')
        bs.inputs['Base Color'].default_value = (*rgb, 1)
        bs.inputs['Roughness'].default_value = rough
        bs.inputs['Metallic'].default_value = metal
        if name == 'light':
            bs.inputs['Emission Color'].default_value = (1, .43, .10, 1)
            bs.inputs['Emission Strength'].default_value = 2.5
        # The preview and runtime use recessed reflective glass. No claim of
        # interior traversal or runtime refraction accompanies this exterior kit.
        m.diffuse_color = (*rgb, 1)
        m['city_material'] = name
        MATS.append(m)


def mesh(name, vertices, faces, mat=0, smooth=True, detail=0, face_materials=None):
    global PART
    PART += 1
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(f'{PART:04d}_{name}', data)
    bpy.context.collection.objects.link(obj)
    if face_materials is None:
        data.materials.append(MATS[mat])
    else:
        for m in MATS:
            data.materials.append(m)
    for i, poly in enumerate(data.polygons):
        poly.use_smooth = smooth
        if face_materials is not None:
            poly.material_index = face_materials[i]
    # Metric planar UVs. Cylindrical surfaces receive a coherent custom unwrap
    # in the native material shader from the same local coordinates.
    uv = data.uv_layers.new(name='UVMap')
    for poly in data.polygons:
        n = poly.normal
        axes = (0, 1) if abs(n.z) > .6 else (0, 2) if abs(n.y) > abs(n.x) else (1, 2)
        for loop in poly.loop_indices:
            p = data.vertices[data.loops[loop].vertex_index].co
            uv.data[loop].uv = (p[axes[0]] * .5, p[axes[1]] * .5)
    obj['detail'] = detail
    return obj


def tube(name, points, radii, mat=0, sides=10, detail=0):
    pts = [Vector(p) for p in points]
    if isinstance(radii, (float, int)):
        radii = [radii] * len(pts)
    vertices, faces = [], []
    previous = None
    for j, p in enumerate(pts):
        tangent = (pts[min(j+1, len(pts)-1)]-pts[max(0, j-1)]).normalized()
        axis = Vector((0, 0, 1)) if abs(tangent.z) < .95 else Vector((0, 1, 0))
        side = tangent.cross(axis).normalized() if previous is None else (previous - tangent * previous.dot(tangent)).normalized()
        if side.length < .1:
            side = tangent.cross(axis).normalized()
        other = tangent.cross(side).normalized()
        previous = side
        r = radii[j]
        rx, ry = (r, r) if isinstance(r, (float, int)) else r
        for k in range(sides):
            a = k * TAU/sides
            vertices.append(tuple(p + side*(rx*math.cos(a)) + other*(ry*math.sin(a))))
        if j:
            for k in range(sides):
                a = (j-1)*sides+k
                b = (j-1)*sides+(k+1)%sides
                faces.append((a, b, b+sides, a+sides))
    faces += [tuple(reversed(range(sides))), tuple(range((len(pts)-1)*sides, len(pts)*sides))]
    obj=mesh(name, vertices, faces, mat, detail=detail)
    for cap in obj.data.polygons[-2:]:cap.use_smooth=False
    return obj


def cube(name, loc, size, mat=0, bevel=.04, detail=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(MATS[mat])
    obj['detail'] = detail
    if bevel:
        mod = obj.modifiers.new('Soft manufactured edge', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        bpy.ops.object.modifier_apply(modifier=mod.name)
        mod = obj.modifiers.new('Corner normals', 'WEIGHTED_NORMAL')
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj


def ellipse(name, centre, rx, ry, height, mat=0, n=64, wave=0):
    x, y, z = centre
    v, f = [], []
    for zz in [z, z+height]:
        for k in range(n):
            a = TAU*k/n
            w = 1+wave*math.sin(3*a+.7)
            v.append((x+rx*math.cos(a)*w, y+ry*math.sin(a)*w, zz))
    f.append(tuple(reversed(range(n))))
    f.append(tuple(range(n, 2*n)))
    for k in range(n):
        f.append((k, (k+1)%n, (k+1)%n+n, k+n))
    obj=mesh(name, v, f, mat, smooth=False)
    if mat != 9:
        # Smooth the manufactured curved wall while retaining planar caps.
        # Analytic normals survive the GLB's UV splits and coarse LODs;
        # flat normals on each imported triangle made glazing look fractured.
        corner=[]
        for polygon in obj.data.polygons:
            polygon.use_smooth=polygon.index>=2
            for loop in polygon.loop_indices:
                if polygon.index<2:
                    normal=(0,0,-1 if polygon.index==0 else 1)
                else:
                    k=obj.data.loops[loop].vertex_index%n;a=TAU*k/n
                    r=1+wave*math.sin(3*a+.7);dr=3*wave*math.cos(3*a+.7)
                    dx=rx*(-math.sin(a)*r+math.cos(a)*dr)
                    dy=ry*(math.cos(a)*r+math.sin(a)*dr)
                    length=math.hypot(dx,dy);normal=(dy/length,-dx/length,0)
                corner.append(normal)
        obj.data.normals_split_custom_set(corner)
    if mat==12:
        # Runtime UVs are in room units. The continuous cylindrical unwrap
        # avoids tangent jumps between adjacent glazing triangles.
        perimeter=math.pi*(3*(rx+ry)-math.sqrt((3*rx+ry)*(rx+3*ry)))
        rooms=max(6,round(perimeter/3.2));uv=obj.data.uv_layers.active
        for polygon in obj.data.polygons:
            if polygon.index<2:continue
            for loop in polygon.loop_indices:
                vertex=obj.data.loops[loop].vertex_index;k=vertex%n
                u=k/n
                if polygon.index==n+1 and k==0:u=1
                uv.data[loop].uv=(u*rooms,1-(1 if vertex>=n else 0))
    return obj


def ribbon(name, centre, rx, ry, z, width, thickness, mat=0, wave=.06, n=96):
    cx, cy = centre
    v, f = [], []
    for dz, inset in [(0, 0), (0, width), (-thickness, 0), (-thickness, width)]:
        for k in range(n):
            a = TAU*k/n
            r = 1+wave*math.sin(3*a+.7)
            v.append((cx+(rx-inset)*math.cos(a)*r, cy+(ry-inset)*math.sin(a)*r, z+dz))
    for a in range(n):
        b = (a+1)%n
        f.extend([(a,b,n+b,n+a), (2*n+a,3*n+a,3*n+b,2*n+b),
                  (a,2*n+a,2*n+b,b), (n+a,n+b,3*n+b,3*n+a)])
    return mesh(name, v, f, mat)


def shell_point(t, s, rx, depth, height, skew, centre):
    sn = math.sin(t)
    width = .90+.10*math.sin(math.pi*s)
    x = rx*math.cos(t)*width + skew*sn*sn*(.5+.5*s)
    y = (s-.5)*depth + depth*.12*sn + .10*depth*math.sin(math.pi*s)*math.cos(t)
    z = height*sn*(.92+.08*math.sin(math.pi*s))
    return Vector((x+centre[0], y+centre[1], z+centre[2]))


def shell(name, centre, rx, depth, height, skew=.6, thickness=.28, solar=True, glass=True):
    nu, nv = 40, 10
    v, f, mats = [], [], []
    def point(i, j, inner):
        t, s = math.pi*i/nu, j/nv
        p = shell_point(t, s, rx, depth, height, skew, centre)
        if inner:
            p.x -= thickness*math.cos(t)
            p.z -= thickness*math.sin(t)
        return p
    for inner in [False, True]:
        for j in range(nv+1):
            for i in range(nu+1):
                v.append(tuple(point(i,j,inner)))
    layer = (nu+1)*(nv+1)
    for j in range(nv):
        for i in range(nu):
            a=j*(nu+1)+i
            f += [(a,a+1,a+nu+2,a+nu+1), (a+layer,a+nu+1+layer,a+nu+2+layer,a+1+layer)]
            mats += [0,2]
    for j in [0, nv]:
        for i in range(nu):
            a=j*(nu+1)+i
            f.append((a,a+layer,a+1+layer,a+1));mats.append(0)
    for i in [0, nu]:
        for j in range(nv):
            a=j*(nu+1)+i;b=a+nu+1
            f.append((a,b,b+layer,a+layer));mats.append(0)
    obj = mesh(name, v, f, face_materials=mats)
    # Continuous thick reveal and inset warm light follow the structural opening.
    for s in [0,1]:
        pts=[]
        for i in range(nu+1):
            t=math.pi*i/nu
            p=shell_point(t,s,rx-.37,depth-.10,height-.26,skew,centre)
            pts.append(tuple(p))
        tube(name+'_deep_reveal',pts,[(.22,.40)]*len(pts),1,10)
        trim=[]
        for i in range(4,nu-3):
            p=shell_point(math.pi*i/nu,s,rx-.46,depth-.21,height-.34,skew,centre)
            p.y += .11 if s==0 else -.11
            trim.append(tuple(p))
        tube(name+'_light',trim,.021,6,6,detail=2)
        if glass:
            # Recess behind the overhang. Panels touch the reveal and foot rail.
            recess=.65 if s==0 else -.45
            curve=[shell_point(math.pi*i/nu,s,rx-.48,depth,height-.40,skew,centre) for i in range(nu+1)]
            vertices=[]
            for p in curve:
                vertices += [(p.x,p.y+recess,centre[2]+.12), (p.x,p.y+recess,max(centre[2]+.13,p.z))]
            glazing=mesh(name+'_recessed_glazing',vertices,[(2*i,2*i+2,2*i+3,2*i+1) for i in range(nu)],12,smooth=False)
            for loop in glazing.data.loops:
                p=glazing.data.vertices[loop.vertex_index].co
                glazing.data.uv_layers.active.data[loop.index].uv=((p.x-centre[0])/3.2,1-(p.z-centre[2])/2.66)
            for i in range(5,nu,6):
                p=curve[i]
                if p.z>centre[2]+.4:
                    tube(name+'_mullion',[(p.x,p.y+recess-.035,centre[2]+.12),(p.x,p.y+recess-.035,p.z)],.034,5,6,detail=1)
    if solar:
        v,f=[],[]
        for j in range(13):
            s=.12+.76*j/12
            for i in range(33):
                t=math.pi*(.20+.58*i/32)
                p=shell_point(t,s,rx,depth,height,skew,centre)
                p+=Vector((math.cos(t),0,math.sin(t)))*.035
                v.append(tuple(p))
        for j in range(12):
            for i in range(32):
                a=j*33+i;f.append((a,a+1,a+34,a+33))
        mesh(name+'_photovoltaic_skin',v,f,3)
    return obj


def plants(centre, rx, ry, seed, count=9):
    rng=random.Random(seed)
    for j in range(count):
        a=rng.random()*TAU;r=math.sqrt(rng.random())*.85
        root=Vector((centre[0]+rx*r*math.cos(a),centre[1]+ry*r*math.sin(a),centre[2]))
        height=rng.uniform(.22,.56)
        for k in range(4):
            angle=a+k*TAU/4+rng.uniform(-.3,.3);v=[];f=[]
            forward=Vector((math.cos(angle),math.sin(angle),0));side=Vector((-math.sin(angle),math.cos(angle),0))
            for q in range(5):
                t=q/4;mid=root+forward*(height*.72*t)+Vector((0,0,height*(math.sin(t*2.0)*.70+t*.15)))
                width=height*.16*math.sin(math.pi*t)**.65
                v.extend([tuple(mid-side*width),tuple(mid+Vector((0,0,.012*math.sin(math.pi*t)))),tuple(mid+side*width)])
                if q:
                    b=(q-1)*3;f.extend([(b,b+3,b+4,b+1),(b+1,b+4,b+5,b+2)])
            mesh('curved_planted_leaf',v,f,8,detail=3)
        if j%3==0:
            tip=root+Vector((0,0,height*1.12))
            tube('flower_stem',[tuple(root),tuple(tip)],.008,8,5,detail=3)
            for k in range(5):
                a=k*TAU/5
                side=Vector((-math.sin(a),math.cos(a),0))*.03
                end=tip+Vector((math.cos(a),math.sin(a),.3))*.085
                mesh('flower_petals',[tuple(tip),tuple(end-side),tuple(end+side)],[(0,1,2)],10,detail=3)


def planter(centre, rx, ry, seed, height=.45, planted=True):
    manufacturing.vessel(SimpleNamespace(**globals()),'formed_planter',*centre[:2],rx,ry,centre[2],height,n=40)
    ellipse('planting_soil',(centre[0],centre[1],centre[2]+height-.065),rx-.16,ry-.16,.025,9,n=36)
    if planted:plants((centre[0],centre[1],centre[2]+height-.04),max(.05,rx-.2),max(.05,ry-.2),seed,count=max(3,min(14,int(rx*ry*7))))


def pillar(name,x,y,height,lean=1.4,mat=0):
    points=[];radii=[]
    for i in range(21):
        t=i/20
        points.append((x+lean*(t*t*(3-2*t)-.26*math.sin(math.pi*t)),y,height*t))
        radii.append((.23+.22*(1-t)**3+.40*t**5,.34+.16*t*t))
    tube(name,points,radii,mat,16)


def furniture(p, kind, seed):
    if kind=='bench':
        manufacturing.bench(SimpleNamespace(**globals()),p,seed)
    elif kind=='lamp':
        pts=[(p[0]-.45+.9*(i/25)**2,p[1],p[2]+3.9*i/25) for i in range(26)]
        tube('lamp_stem',pts,[(.13-.055*i/25,.19-.07*i/25) for i in range(26)],0,12)
        ellipse('lamp_petal',(p[0]+.55,p[1],p[2]+3.85),.72,.38,.12,0,n=40)
        ellipse('lamp_diffuser',(p[0]+.55,p[1],p[2]+3.83),.62,.28,.018,6,n=32)
        ellipse('lamp_base',(p[0]-.45,p[1],p[2]-.02),.28,.29,.08,1,n=24)
    elif kind=='fountain':
        tube('water_spine',[(p[0]-.18+.23*math.sin(i/24*math.pi/2),p[1],p[2]+1.55*i/24) for i in range(25)],[(.25-.13*i/24,.29-.16*i/24) for i in range(25)],0,16)
        manufacturing.vessel(SimpleNamespace(**globals()),'formed_drinking_basin',p[0],p[1]-.18,.38,.32,p[2]+.73,.22,1,n=32)
        tube('fountain_spout',[(p[0],p[1],p[2]+1.16),(p[0],p[1]-.22,p[2]+1.16)],.033,5,10,detail=1)


def building(recipe):
    if extended_architecture(recipe,SimpleNamespace(**globals())):return
    kind=recipe['kind'];w=recipe['width'];d=recipe['depth'];h=recipe['height'];seed=recipe['seed']
    if kind=='house':
        ellipse('foundation',(0,0,-.5),w*.53,d*.51,.62,7,n=72)
        shell('living_shell',(-w*.12,-d*.06,.12),w*.41,d*.86,h*.62,.8)
        shell('upper_shell',(w*.22,d*.15,h*.47),w*.27,d*.62,h*.47,.6,thickness=.23)
        # The upper pod's two sculpted buttresses arrive at the same foundation.
        pillar('upper_support',w*.32,d*.30,h*.56,lean=.8)
        pillar('entrance_support',w*.35,-d*.24,h*.48,lean=1.1)
        ellipse('arrival_terrace',(-w*.12,-d*.37,.04),w*.40,d*.30,.12,2,n=56)
        for i in range(3):
            cube('entry_step',(w*.27,-d*.49-i*.30,-.06-i*.12),(2.6,1.1,.20),7,.06)
        for x in [-w*.4,w*.36]:
            planter((x,-d*.35,.12),.70,.52,seed+int(x*20),.4)
        for i in range(6):
            x=w*.12+i*w*.038
            cube('sun_louvre',(x,-d*.13,h*.61),(.08,.36,h*.20),2,.025,detail=1)
        if recipe.get('variation')=='patio':
            shell('patio_awning',(-w*.34,d*.27,1.9),w*.20,d*.48,2.1,-.5,solar=False,glass=False)
    elif kind=='apartments':
        ellipse('podium',(0,0,-.6),w*.51,d*.52,.75,7,n=80)
        for side in [-1,1]:
            cx=side*w*.245
            for level in range(4):
                z=.25+level*3.35
                rx=w*.255*(1-.035*level);ry=d*.43*(1-.035*level)
                ellipse('apartment_floor',(cx,0,z),rx,ry,.30,0,n=80,wave=.035)
                ribbon('timber_balcony',(cx,0),rx-.24,ry-.24,z+.32,1.45,.10,2,wave=.035)
                ellipse('recessed_rooms',(cx,.40,z+.35),rx-1.55,ry-1.7,2.80,4,n=64,wave=.035)
                for i in range(15):
                    a=math.pi+i*math.pi/14
                    x=cx+(rx-1.52)*math.cos(a);y=.4+(ry-1.67)*math.sin(a)
                    cube('facade_fin',(x,y,z+1.7),(.09,.36,2.7),2,.02,detail=1).rotation_euler.z=a-math.pi/2
                ribbon('balcony_guard',(cx,0),rx-.14,ry-.14,z+1.27,.035,.70,4,wave=.035,n=80)
                ring=[(cx+(rx-.13)*math.cos(a), (ry-.13)*math.sin(a),z+1.31) for a in [i*TAU/80 for i in range(81)]]
                tube('balcony_handrail',ring,.032,5,6,detail=1)
                planter((cx, -ry+.7,z+.32),1.55,.32,seed+level+side,.37)
            shell('roof_petal',(cx,0,13.7),w*.265,d*.85,2.55,side*.9,glass=False)
            pillar('ribbon_spine',cx-side*w*.16,-d*.21,h*.88,side*2.5)
        ellipse('circulation_core',(0,1,.2),1.7,2.5,14.6,4,n=32)
        for z in [3.6,6.95,10.3,13.65]:
            ellipse('core_landing',(0,1,z),2.0,2.7,.24,0,n=40)
    elif kind in ['civic','terminal']:
        ellipse('public_podium',(0,0,-.65),w*.53,d*.54,.80,7,n=96)
        for side in [-1,1]:
            shell('inhabited_petal',(side*w*.29,0,.15),w*.23,d*.84,h*.58,side*.9)
        # A high, open central portico is a genuine gap between the wings.
        shell('central_portico',(0,d*.05,.15),w*.23,d*.80,h*.94,1.2,glass=False,thickness=.42)
        ellipse('upper_mezzanine',(0,d*.24,h*.36),w*.32,d*.21,.28,2,n=64)
        for i in range(5):
            cube('forum_step',(0,d*.1+i*.6,.15+i*.23),(w*.25,1.0,.3),7,.05)
        # Keep planted edges outside the public wing's door approach.
        for x in [-w*.43,w*.43]:
            planter((x,-d*.43,.15),2.0,.82,seed+int(x),.46)
        if kind=='terminal':
            for side in [-1,1]:
                shell('boarding_canopy',(side*w*.39,d*.65,0),w*.14,d*.43,h*.44,side*.6,glass=False)
    elif kind=='greenhouse':
        ellipse('greenhouse_plinth',(0,0,-.40),w*.51,d*.51,.55,7,n=72)
        # Glazed arch bays share the shell profile, with opaque structural ribs.
        for side in [-1,1]:
            cx=side*w*.235;rx=w*.24
            n,m=40,16;v=[];f=[]
            for j in range(m+1):
                for i in range(n+1):
                    v.append(tuple(shell_point(math.pi*i/n,j/m,rx,d*.9,h*.71,.3,(cx,0,.15))))
            for j in range(m):
                for i in range(n):
                    a=j*(n+1)+i;f.append((a,a+1,a+n+2,a+n+1))
            mesh('glass_envelope',v,f,4)
            for j in range(11):
                points=[tuple(shell_point(math.pi*i/40,j/10,rx+.03,d*.9,h*.71+.04,.3,(cx,0,.15))) for i in range(41)]
                tube('greenhouse_rib',points,.085,0,8)
            for i in range(2,40,5):
                points=[tuple(shell_point(math.pi*i/40,j/16,rx+.06,d*.9,h*.71+.08,.3,(cx,0,.15))) for j in range(17)]
                tube('glazing_rail',points,.030,5,6,detail=1)
        shell('service_spine',(0,d*.05,.15),w*.13,d*.94,h*.94,.5,glass=True,thickness=.23)
        for side in [-1,1]:
            planter((side*w*.27,-d*.46,.15),2,.65,seed+side,.65)
    elif kind=='hangar':
        cube('hangar_apron',(0,0,-.20),(w*1.04,d*1.04,.4),7,.12)
        shell('hangar_shell',(-w*.05,0,.0),w*.43,d*.96,h*.92,2.5,thickness=.48,glass=False)
        # Sealed rear, open front. Repeated ribs have real depth and tapered ends.
        for j in range(1,9):
            points=[tuple(shell_point(math.pi*i/48,j/9,w*.42,d*.95,h*.89,2.5,(-w*.05,0,.03))) for i in range(49)]
            tube('hangar_internal_rib',points,(.13),1,8)
        cube('back_wall',(0,d*.43,h*.32),(w*.68,.24,h*.64),1,.03)
        cube('workshop_gantry',(0,d*.15,h*.57),(w*.65,.65,.65),5,.08)
        for side in [-1,1]:
            cube('gantry_support',(side*w*.31,d*.15,h*.28),(.42,.50,h*.56),5,.05)
        shell('workshop_annex',(w*.35,-d*.19,.05),w*.17,d*.49,h*.30,-.6,thickness=.26)
    elif kind=='water_tower':
        ellipse('tower_plinth',(0,0,-.4),3.3,3.3,.6,7,n=64)
        pts=[];radii=[]
        for i in range(41):
            t=i/40;pts.append((-2.8*math.sin(math.pi*t)+.8*t,0,h*.84*t));radii.append((.42+.30*abs(2*t-1),.75))
        tube('tower_crescent',pts,radii,0,20)
        ellipse('reservoir_base',(0,0,h*.75),3.45,3.45,.40,0,n=64)
        ellipse('reservoir',(0,0,h*.75+.4),3.15,3.15,2.05,11,n=64)
        ellipse('reservoir_roof',(0,0,h*.75+2.45),3.45,3.45,.27,0,n=64)
        ellipse('reservoir_solar',(0,0,h*.75+2.73),3.03,3.03,.03,3,n=64)
        for x in [-.45,.1]:tube('water_pipe',[(x,0,.15),(x,0,h*.75)],.10,5,10,detail=1)
    elif kind=='canopy':
        manufacturing.canopy_support(SimpleNamespace(**globals()),recipe)
        # Elevated open petal with a shallow crown and no glazing.
        shell('canopy_petal',(0,0,h*.68),w*.5,d,h*.25,.7,thickness=.18,glass=False)
        furniture((-.6,.3,0),'bench',seed)
    elif kind in ['bench','lamp','fountain']:
        furniture((0,0,0),kind,seed)
    elif kind in ['planter','growing_bed']:
        planter((0,0,0),w/2,d/2,seed,h*.62)


def export_asset(recipe,out):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    for data in list(bpy.data.meshes):
        if data.users==0:bpy.data.meshes.remove(data)
    global PART
    PART=0
    building(recipe)
    decorate(recipe,SimpleNamespace(**globals()))
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    for obj in objects:
        bpy.context.view_layer.objects.active=obj
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
        obj.select_set(False)
    folder=out/recipe['id'];folder.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'source.blend'))
    for o in objects:o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(folder/'master.glb'),export_format='GLB',use_selection=True,
                              export_extras=True,export_tangents=False,export_yup=True,export_cameras=False,export_lights=False)
    bounds=[tuple(v.co) for o in objects for v in o.data.vertices]
    lo=[min(p[i] for p in bounds) for i in range(3)];hi=[max(p[i] for p in bounds) for i in range(3)]
    triangles=0
    for o in objects:
        o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
    report={'id':recipe['id'],'recipe':recipe,'bounds_z_up':[lo,hi],'triangles':triangles,
            'master_sha256':hashlib.sha256((folder/'master.glb').read_bytes()).hexdigest(),
            'author_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'structure_sha256':hashlib.sha256((Path(__file__).parent/'architecture.py').read_bytes()).hexdigest(),
            'details_sha256':hashlib.sha256((Path(__file__).parent/'details.py').read_bytes()).hexdigest(),
            'manufacturing_sha256':hashlib.sha256((Path(__file__).parent/'manufacturing.py').read_bytes()).hexdigest(),
            'fittings':audit_fittings(objects),
            'backend':'metric procedural architecture','neural_mesh':False,
            'reference_is_geometry':False,'art_accepted':False,'performance_accepted':False}
    (folder/'source.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print('AUTHORED',recipe['id'],triangles,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipe',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--asset');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    recipes=json.loads(args.recipe.read_text(encoding='utf8'))
    materials()
    for recipe in recipes['assets']:
        if not args.asset or recipe['id']==args.asset:export_asset(recipe,args.out)


if __name__=='__main__':main()
