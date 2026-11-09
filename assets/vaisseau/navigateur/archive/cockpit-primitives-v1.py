"""Reference-led, editable Navigator cabin inside the approved smooth shell.

The front is a virtual panoramic field. It has no glass pane or canopy bars.
Coordinates are metres, nose -Y, up +Z. The pilot eye is (0, -.65, .7).
"""
import bpy
import math
import json
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree

def material(name, color, metal=.75, rough=.24, emission=None):
    m = bpy.data.materials.new('Navigator | '+name)
    m.diffuse_color = (*color,1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color,1)
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = rough
    if emission:
        p.inputs['Emission Color'].default_value = (*emission[0],1)
        p.inputs['Emission Strength'].default_value = emission[1]
    return m

def finish(obj, name, mat):
    obj.name = name
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return obj

def box(name, loc, size, mat, radius=.03):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = finish(bpy.context.object,name,mat)
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for face in obj.data.polygons:face.use_smooth=True
    if radius:
        b = obj.modifiers.new('Machined rounded edges','BEVEL')
        b.width=min(radius,min(size)*.45); b.segments=4; b.harden_normals=True
        n = obj.modifiers.new('Weighted face normals','WEIGHTED_NORMAL'); n.keep_sharp=True
    return obj

def sphere(name, loc, size, mat, segments=32, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=loc)
    obj = finish(bpy.context.object,name,mat)
    obj.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for p in obj.data.polygons:p.use_smooth=True
    return obj

def cylinder(name, loc, radius, depth, mat, rotation=(0,0,0), vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=loc,rotation=rotation)
    obj=finish(bpy.context.object,name,mat)
    for face in obj.data.polygons:face.use_smooth=True
    bevel=obj.modifiers.new('Rounded lip','BEVEL');bevel.width=min(.012,depth*.2);bevel.segments=3
    obj.modifiers.new('Weighted face normals','WEIGHTED_NORMAL')
    return obj

def tube(name, points, radius, mat, closed=False):
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D'
    curve.resolution_u=1;curve.bevel_depth=radius;curve.bevel_resolution=3
    sp=curve.splines.new('POLY');sp.points.add(len(points)-1)
    for p,v in zip(sp.points,points):p.co=(*v,1)
    sp.use_cyclic_u=closed
    obj=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(obj)
    return finish(obj,name,mat)

def solid(name, points, mat, thickness=.025):
    # An inward face and a parallel backing; each decorative panel is a closed part.
    centre=sum((Vector(p) for p in points),Vector())/len(points)
    n=centre.normalized()
    verts=[tuple(p) for p in points]+[tuple(Vector(p)+n*thickness) for p in points]
    count=len(points)
    faces=[tuple(reversed(range(count))),tuple(range(count,2*count))]
    faces += [(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    finish(obj,name,mat)
    for face in mesh.polygons:face.use_smooth=True
    b=obj.modifiers.new('Pressed panel edge','BEVEL');b.width=.012;b.segments=3
    obj.modifiers.new('Weighted face normals','WEIGHTED_NORMAL')
    return obj

def build(hull, root):
    bpy.context.view_layer.update()
    tree=BVHTree.FromObject(hull,bpy.context.evaluated_depsgraph_get())
    def skin(phi,lat):
        d=Vector((math.sin(phi)*math.cos(lat),-math.cos(phi)*math.cos(lat),math.sin(lat)))
        p,_,_,_=tree.ray_cast(Vector(),d,20)
        if p is None:raise RuntimeError('Hull ray missed')
        return p*.88
    chrome=material('inner silver',(.36,.43,.54),.82,.21)
    trim=material('bright ribs',(.66,.72,.82),.92,.16)
    dark=material('recesses',(.018,.025,.042),.62,.36)
    floorMat=material('floor alloy',(.13,.17,.23),.8,.29)
    cushion=material('seat graphite',(.022,.029,.045),.2,.51)
    pads=material('control pads',(.055,.075,.09),.48,.23)
    blue=material('blue fixtures',(.13,.3,.7),.35,.2,((.32,.52,1),.8))
    dimBlue=material('panel light',(.07,.16,.35),.5,.24,((.16,.32,1),.045))
    red=material('red indicators',(.3,.018,.012),.1,.3,((1,.028,.012),.8))
    green=material('green lens',(.012,.18,.055),.2,.12,((.05,1,.25),1.4))
    amber=material('sensor lens',(.42,.3,.15),.05,.12,((1,.54,.18),.018))
    pupil=material('sensor pupil',(.025,.06,.035),.12,.2,((.18,.6,.3),.04))

    # The chamber follows actual ray intersections with the final outer skin.
    # Its front hemisphere above the lower lip is the clear viewing field.
    azimuths=28; layers=10; lower=-.56; upper=1.49; opening=math.pi*6/14
    panelCount=0
    for j in range(layers):
        a=lower+(upper-lower)*j/layers;b=lower+(upper-lower)*(j+1)/layers
        for i in range(azimuths):
            p=-math.pi+2*math.pi*i/azimuths;q=-math.pi+2*math.pi*(i+1)/azimuths
            top=b
            if abs((p+q)/2)<opening:
                if a>=-.2:continue
                top=min(b,-.2)
            corners=[skin(p,a),skin(q,a),skin(q,top),skin(p,top)]
            solid(f'Cabin backing {j:02d}-{i:02d}',[v*1.012 for v in corners],dark,.03)
            centre=sum(corners,Vector())/4
            inset=[centre+(v-centre)*.87 for v in corners]
            obj=solid(f'Cabin panel {j:02d}-{i:02d}',inset,chrome)
            panelCount+=1
            # Chrome return and nested rails are intentional broad forms, not acquired noise.
            if j%2==0:
                rail=[centre+(v-centre)*.68-centre.normalized()*.024 for v in corners]
                tube(f'Panel channel {j}-{i}',rail,.009,trim,True)
            if j>=5 and i%3==0:
                edge=[inset[0]*.2+inset[1]*.8,inset[0]*.8+inset[1]*.2]
                tube(f'Blue seam {j}-{i}',[v-centre.normalized()*.03 for v in edge],.007,dimBlue)
    # Three structural ribs over the remaining ceiling and rear quarters.
    for phi in [math.pi,-2.24,2.24]:
        tube('Ceiling spine', [skin(phi,lower+(upper-lower)*k/55)*.984 for k in range(56)],.024,trim)
    ceiling=skin(math.pi,math.pi/2)
    cylinder('Ceiling central fitting',(0,0,ceiling.z-.03),.19,.05,chrome)
    for phi in [-opening,opening]:
        tube('Panoramic side return',[skin(phi,-.2+1.69*k/60)*.987 for k in range(61)],.032,trim)
    tube('Panoramic lower lip',[skin(-opening+2*opening*k/80,-.2)*.984 for k in range(81)],.033,trim)

    # A fitted floor; its boundary uses the hull's horizontal section, not an independent ellipse.
    floor=[]
    for i in range(96):
        phi=2*math.pi*i/96
        d=Vector((math.sin(phi),math.cos(phi),0))
        p,_,_,_=tree.ray_cast(Vector((0,0,-1.15)),d,20)
        if p is None:raise RuntimeError('Floor boundary missed hull')
        floor.append(Vector((p.x*.88,p.y*.88,-1.15)))
    floorObj=solid('Cabin floor',floor,floorMat,.09)
    for scale in [.38,.64,.88]:
        tube('Floor inlay',[Vector((v.x*scale,v.y*scale,-1.128)) for v in floor],.009,trim,True)
    for i in range(0,96,8):
        tube('Floor radial channel',[(0,.15,-1.124),floor[i]*.95+Vector((0,0,.075))],.006,dark)

    # Bucket seat and a sculpted pedestal, with arms at the reference's lateral control pads.
    cylinder('Seat pedestal foot',(0,-.85,-1.06),.43,.16,chrome)
    box('Seat pedestal',(0,-.85,-.74),(.46,.52,.57),chrome,.08)
    box('Seat underframe',(0,-.92,-.43),(.89,1.04,.17),trim,.065)
    sphere('Seat cushion',(0,-.99,-.28),(.41,.49,.13),cushion)
    back=box('Seat back',(0,-.48,.05),(.84,.15,.87),chrome,.12);back.rotation_euler.x=-.11
    back=box('Seat back inset',(0,-.57,.05),(.68,.055,.7),cushion,.08);back.rotation_euler.x=-.11
    sphere('Seat head crest',(0,-.45,.49),(.37,.08,.12),chrome)
    for side in [-1,1]:
        for y in [-.5,-1.38]:
            tube('Console support',[(side*.38,y,-.43),(side*.67,y,-.22),(side*.8,y,-.08)],.045,chrome)
        console=box('Lateral console',(side*.85,-1.05,-.025),(.57,1.62,.19),chrome,.09)
        box('Palm control pad',(side*.85,-1.20,.083),(.45,.65,.027),pads,.012)
        # Five clean pressure strips, rather than a conventional aircraft joystick/dashboard.
        for k in range(5):
            x=side*.85+(k-2)*.071
            box('Pressure strip',(x,-1.23,.102),(.044,.49,.012),trim,.005)
        box('Console readout well',(side*.85,-.54,.084),(.42,.31,.02),dark,.008)
        for j in range(3):
            for k in range(6):
                box('Console indicator',(side*.85+(k-2.5)*.047,-.62+j*.076,.1),(.028,.034,.009),red if (j+k)%4 else dimBlue,.003)
        for k in range(8):
            cylinder('Console collar',(side*.85,-1.77+k*.085,-.055),.055,.012,trim,rotation=(0,math.pi/2,0),vertices=16)

    # Max's articulated sensor. Its lens faces the pilot, not the direction of flight.
    sensorCentre=Vector((-1.1,-2.3,.92))
    sensorRotation=Matrix.Rotation(-.7,4,'Z')
    sensorTransform=Matrix.Translation(sensorCentre)@sensorRotation@Matrix.Scale(.72,4)@Matrix.Translation(Vector((1.35,1.9,-.88)))
    arm=[skin(-opening,.25)*.986,Vector((-2.05,-1.35,1.05)),sensorCentre+sensorRotation.to_3x3()@Vector((0,-.24*.72,0))]
    tube('Max support',arm,.045,chrome)
    for p in arm:sphere('Max hinge',p,(.095,.095,.095),trim,24,12)
    beforeSensor=set(bpy.data.objects)
    head=sphere('Max sensor housing',(-1.35,-1.9,.88),(.3,.24,.34),chrome,48,24)
    for k in range(4):
        z=.69+k*.12
        tube('Max crown rib',[(-1.35+.29*math.cos(t),-1.9+.22*math.sin(t),z) for t in [math.pi*.05+j*math.pi*1.9/48 for j in range(49)]],.018,trim)
    cylinder('Max lens collar',(-1.35,-1.66,.88),.22,.07,trim,(math.pi/2,0,0))
    sphere('Max lens',(-1.35,-1.615,.88),(.19,.14,.19),amber)
    sphere('Max central pupil',(-1.35,-1.472,.88),(.047,.012,.047),pupil)
    for z in [.61,1.15]:
        box('Max brow',(-1.35,-1.69,z),(.44,.13,.045),chrome,.018)
    for obj in set(bpy.data.objects)-beforeSensor:
        obj.matrix_world=sensorTransform@obj.matrix_world

    # Rear circular fitting and closed service panel, retained behind the transparent forward field.
    centre=skin(math.pi,.035)
    y=centre.y-.13
    cylinder('Rear circular housing',(0,y,.13),.48,.10,chrome,(math.pi/2,0,0))
    cylinder('Rear circular recess',(0,y-.06,.13),.36,.02,dark,(math.pi/2,0,0))
    sphere('Rear green core',(0,y-.085,.13),(.2,.04,.2),green)
    for radius in [.25,.41]:
        tube('Rear concentric ring',[(radius*math.cos(t),y-.10,.13+radius*math.sin(t)) for t in [2*math.pi*i/64 for i in range(64)]],.013,trim,True)
    for side in [-1,1]:
        # The shader lights use these same fixture positions.
        sphere('Blue cabin lamp',(side*1.65,.15,.95),(.19,.045,.075),blue)
        anchor=skin(math.atan2(side*1.65,-.15),math.atan2(.95,math.hypot(1.65,.15)))*.988
        tube('Lamp support',[(side*1.65,.15,.95),anchor],.018,chrome)
    sphere('Rear ceiling lamp',(0,1.75,1.25),(.16,.08,.045),blue)
    tube('Rear lamp support',[(0,1.75,1.25),skin(math.pi,math.atan2(1.25,1.75))*.988],.018,chrome)

    report={'pilot_eye':[0,-.65,.7],'hull_role':10,'cabin_role':11,'fitted_panels':panelCount,
            'projection':'clear forward field; opaque exterior retained in exterior views',
            'canopy_glass':False,'canopy_weather':False,'room_margin_scale':.88,
            'references':['video/interieur/08m40s.jpg','video/interieur/08m55s.jpg','video/interieur/10m30s.jpg','video/interieur/15m15s.jpg','video/interieur/20m35s.jpg'],
            'approximation':'Reference-led reconstruction, not authenticated production dimensions.'}
    (root/'cockpit-inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report
