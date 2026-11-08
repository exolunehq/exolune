"""Coherent manufactured cabin surfaces, shared boundaries and fitted mounting planes.

No primitive meshes are used. Wall relief, floor, pilot support, lamp sockets,
rear port and the sensor assembly share one connected control surface.
"""
from pathlib import Path
import math,json
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

TAU=math.tau

def material(name,color,metal=.8,rough=.22,emit=None):
    m=bpy.data.materials.new('Navigator | '+name);m.use_nodes=True;m.diffuse_color=(*color,1)
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    if emit:
        p.inputs['Emission Color'].default_value=(*emit[0],1);p.inputs['Emission Strength'].default_value=emit[1]
    return m

class Surface:
    def __init__(self,materials):self.v=[];self.f=[];self.m=[];self.cache={};self.materials=materials
    def vertex(self,p):
        key=tuple(round(float(x),6) for x in p)
        if key not in self.cache:self.cache[key]=len(self.v);self.v.append(tuple(p))
        return self.cache[key]
    def ring(self,points):return [self.vertex(p) for p in points]
    def face(self,ids,mat):
        ids=list(dict.fromkeys(ids))
        if len(ids)>=3:self.f.append(tuple(ids));self.m.append(mat)
    def bridge(self,a,b,mat):
        assert len(a)==len(b)
        for i in range(len(a)):
            j=(i+1)%len(a);self.face([a[i],a[j],b[j],b[i]],mat)
    def cap(self,ring,centre,mat):
        c=self.vertex(centre)
        for i in range(len(ring)):self.face([ring[i],ring[(i+1)%len(ring)],c],mat)
    def finish(self,name,solid=0,floor=False,upward=False):
        # Grouped wall patches leave construction samples that do not belong to any face.
        used=sorted({idx for face in self.f for idx in face});remap={idx:j for j,idx in enumerate(used)}
        mesh=bpy.data.meshes.new(name);mesh.from_pydata([self.v[idx] for idx in used],[],[tuple(remap[idx] for idx in f) for f in self.f]);mesh.update()
        for m in self.materials:mesh.materials.append(m)
        for p,i in zip(mesh.polygons,self.m):p.material_index=i;p.use_smooth=True
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        if floor:
            probes=[f for f in bm.faces if abs(f.calc_center_median().z+1.15)<.008]
            if probes and sum(f.normal.z for f in probes)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
        if upward:
            probes=[f for f in bm.faces if abs(f.calc_center_median().x)<.15 and -1.3<f.calc_center_median().y<-.9]
            if probes and sum(f.normal.z for f in probes)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
        bm.to_mesh(mesh);bm.free();mesh.update()
        mesh.set_sharp_from_angle(angle=math.radians(45))
        obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
        if solid:
            mod=obj.modifiers.new('Continuous manufactured wall thickness','SOLIDIFY');mod.thickness=solid;mod.offset=-1;mod.use_even_offset=False;mod.use_quality_normals=True
        return obj

def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)

def rounded_xy(u,v,power=6):
    d=(abs(u)**power+abs(v)**power)**(1/power)
    s=max(abs(u),abs(v))/max(d,1e-12)
    return u*s,v*s

def loop2(n=48,power=6):
    result=[]
    for i in range(n):
        x=math.cos(TAU*i/n);y=math.sin(TAU*i/n)
        d=(abs(x)**power+abs(y)**power)**(1/power)
        result.append((x/d,y/d))
    return result

def build(hull,root):
    bpy.context.view_layer.update();tree=BVHTree.FromObject(hull,bpy.context.evaluated_depsgraph_get(),epsilon=1e-5)
    def support(phi,lat,depth=0):
        d=Vector((math.sin(phi)*math.cos(lat),-math.cos(phi)*math.cos(lat),math.sin(lat)))
        p,_,_,_=tree.ray_cast(Vector(),d,20)
        if p is None:raise RuntimeError('Cabin support ray missed the approved hull')
        p*=.875
        return p-p.normalized()*depth
    mats=[material('recessed alloy',(.012,.018,.027),.82,.30),
          material('formed inner silver',(.52,.57,.64),.97,.16),
          material('rolled edges',(.67,.72,.79),1,.105),
          material('floor alloy',(.12,.145,.18),.9,.32),
          material('seat graphite',(.006,.008,.012),0,.46),
          material('pressure surface',(.22,.27,.32),.88,.265),
          material('red indicators',(.25,.015,.01),.1,.25,((1,.045,.02),.5)),
          material('blue diffuser',(.07,.2,.45),.15,.2,((.18,.4,1),.65)),
          material('green optical core',(.025,.19,.07),.12,.16,((.04,1,.25),.32)),
          material('frosted sensor lens',(.30,.17,.075),.02,.28,((1,.38,.10),.075)),
          material('smoked instrument face',(.004,.009,.013),.15,.20),
          material('etched scale',(.34,.41,.45),.55,.27),
          material('amber instrument',(.45,.13,.018),.18,.24,((1,.32,.045),.32)),
          material('live instrument face',(.004,.009,.013),.15,.20)]
    DARK,SILVER,EDGE,FLOOR,SEAT,PAD,RED,BLUE,GREEN,LENS,PUPIL,ETCH,AMBER,LIVE=range(len(mats))
    room=Surface(mats);segments=28;step=TAU/segments
    latitudes=[-.4,-.2,.05,.3,.55,.8,1.05,1.3,1.49,math.pi/2]
    n=48
    square=[(math.cos(TAU*k/n)/max(abs(math.cos(TAU*k/n)),abs(math.sin(TAU*k/n))),
             math.sin(TAU*k/n)/max(abs(math.cos(TAU*k/n)),abs(math.sin(TAU*k/n)))) for k in range(n)]
    rounded=loop2(n,7)
    fixtures=[];floorPhis=set();panelCount=0;rearCells=[]
    opening=6.5*step

    def frame(phi,lat):
        c=support(phi,lat)
        u=(support(phi+.001,lat)-support(phi-.001,lat)).normalized()
        v=(support(phi,lat+.001)-support(phi,lat-.001)).normalized()
        normal=-c.normalized();v=(v-u*v.dot(u)).normalized()
        return c,u,v,normal

    def add_sensor(boundary,c,u,v,normal):
        from instruments import bridge_parameter
        ring=room.ring([c+u*math.cos(TAU*k/n)*.10+v*math.sin(TAU*k/n)*.10+normal*.025 for k in range(n)])
        room.bridge(boundary,ring,EDGE)
        eye=Vector((0,-.65,.7));head=Vector((-1.08,-2.28,.94));axis=(eye-head).normalized()
        back=head-axis*.18
        p0=c+normal*.07;p1=p0+normal*.62;p2=back-axis*.40;p3=back
        previous=ring;basis=u
        for j in range(1,37):
            t=j/36
            p=p0*(1-t)**3+p1*(3*(1-t)**2*t)+p2*(3*(1-t)*t*t)+p3*t**3
            tangent=((p1-p0)*(3*(1-t)**2)+(p2-p1)*(6*(1-t)*t)+(p3-p2)*(3*t*t)).normalized()
            basis=(basis-tangent*basis.dot(tangent)).normalized();other=tangent.cross(basis).normalized()
            radius=.036+.012*(1-t)+.012*math.exp(-((t-.22)/.035)**2)+.009*math.exp(-((t-.85)/.03)**2)
            current=room.ring([p+radius*(basis*math.cos(TAU*k/n)+other*math.sin(TAU*k/n)) for k in range(n)])
            room.bridge(previous,current,EDGE if j in [7,8,9,30,31,32] else SILVER);previous=current
        # Form the sensor housing, cooling returns, bezel and optical cap from that same terminal ring.
        basis=(basis-axis*basis.dot(axis)).normalized();other=axis.cross(basis).normalized()
        profile=[(-.17,.06),(-.158,.11),(-.146,.15),(-.13,.183),(-.12,.19),(-.115,.18),
                 (-.10,.184),(-.09,.207),(-.08,.211),(-.074,.198),(-.055,.200),(-.047,.217),
                 (-.035,.221),(-.028,.208),(-.01,.210),(0,.225),(.012,.225),(.018,.211),
                 (.035,.211),(.043,.223),(.056,.221),(.063,.207),(.08,.20),(.105,.19),
                 (.122,.19),(.13,.178),(.145,.178),(.152,.164),(.15,.153)]
        sn=192;angles=[TAU*k/sn for k in range(sn)]
        for j,(ax,r) in enumerate(profile):
            points=[]
            for angle in angles:
                # Integral crown and side bearings grow from the casing, with a protected lens lip.
                crown=.038*max(math.sin(angle),0)**8*math.exp(-((ax+.015)/.11)**4)
                bearing=.019*abs(math.cos(angle))**16*math.exp(-((ax-.01)/.095)**4)
                rr=r+crown+bearing
                points.append(head+axis*ax+(basis*math.cos(angle)+other*math.sin(angle))*rr)
            current=room.ring(points)
            mat=DARK if j in [5,9,13,17,21,25] else EDGE if j>=23 else SILVER
            if j==0:bridge_parameter(room,previous,[TAU*k/n for k in range(n)],current,angles,mat)
            else:room.bridge(previous,current,mat)
            previous=current
        for r in [.145,.135,.12,.10,.08,.06,.04,.02,.008]:
            ax=.15+.055*math.sqrt(max(0,1-(r/.153)**2))
            current=room.ring([head+axis*ax+(basis*math.cos(t)+other*math.sin(t))*r for t in angles])
            room.bridge(previous,current,LENS);previous=current
        room.cap(previous,head+axis*.205,LENS)

    for j,(a,b) in enumerate(zip(latitudes[:-1],latitudes[1:])):
        for i in range(segments):
            phi=-math.pi+i*step;wrapped=math.atan2(math.sin(phi),math.cos(phi))
            if abs(wrapped)<opening and a>=-.2:continue
            left=phi-step/2
            if j==0:
                for su,sv in square:
                    if sv<-.999:floorPhis.add(round(left+(su+1)*.5*step,12))
            outer=room.ring([support(left+(su+1)*.5*step,a+(sv+1)*.5*(b-a)) for su,sv in square])
            if i in [27,0,1] and j in [1,2,3]:
                rearCells.append(outer)
                continue
            prev=outer
            for inset,depth,mat in [(0.96,.002,DARK),(.90,.017,EDGE),(.84,.018,EDGE),(.78,.009,SILVER)]:
                current=room.ring([support(left+(.5+.5*su*inset)*step,a+(.5+.5*sv*inset)*(b-a),depth) for su,sv in rounded])
                room.bridge(prev,current,mat);prev=current
            c,u,v,normal=frame(phi,(a+b)/2)
            if i==7 and j==3:
                add_sensor(prev,c,u,v,normal)
            elif (i,j) in [(5,4),(23,4),(0,5)]:
                for scale,depth,mat in [(.70,.014,SILVER),(.65,.028,EDGE),(.61,.030,DARK)]:
                    points=[support(left+(.5+su*scale*.5)*step,a+(.5+sv*.065)*(b-a),depth) for su,sv in rounded]
                    current=room.ring(points);room.bridge(prev,current,mat);prev=current
                room.cap(prev,c-normal*.026,BLUE)
                fixtures.append(tuple(c+normal*.045))
            else:
                # Form shallow machined returns in selected panels, connected to the wall plate.
                fillInset=.78
                if (i+2*j)%4==0 and j<6:
                    for inset,depth,mat in [(.65,.009,SILVER),(.61,.018,EDGE),(.57,.019,DARK),(.53,.010,EDGE)]:
                        current=room.ring([support(left+(.5+.5*su*inset)*step,a+(.5+.5*sv*inset)*(b-a),depth) for su,sv in rounded])
                        room.bridge(prev,current,mat);prev=current
                    fillInset=.53
                # Sample the curved plate across its area; long triangle fans create star-shaped reflections.
                for fraction in [.75,.50,.25,.08]:
                    inset=fillInset*fraction
                    current=room.ring([support(left+(.5+.5*su*inset)*step,a+(.5+.5*sv*inset)*(b-a),.009) for su,sv in rounded])
                    room.bridge(prev,current,SILVER);prev=current
                room.cap(prev,support(phi,(a+b)/2,.009),SILVER)
            panelCount+=1

    # Replace a full 3x3 rear wall patch with the large octagonal optical assembly.
    # Its perimeter reuses the surrounding panels' exact edges, rather than overlapping them.
    edges={}
    for cell in rearCells:
        for a,b in zip(cell,cell[1:]+cell[:1]):
            key=tuple(sorted((a,b)));edges[key]=edges.get(key,0)+1
    boundary=set(v for e,count in edges.items() if count==1 for v in e)
    c,u,v,normal=frame(math.pi,.175)
    angles={idx:math.atan2((Vector(room.v[idx])-c).dot(v),(Vector(room.v[idx])-c).dot(u)) for idx in boundary}
    previous=sorted(boundary,key=angles.get);theta=[angles[idx] for idx in previous]
    assert {tuple(sorted(e)) for e in zip(previous,previous[1:]+previous[:1])}=={e for e,count in edges.items() if count==1}
    # Keep every flange contour strictly inside the real wall patch in its mounting plane.
    radialLimit=min(math.hypot((Vector(room.v[idx])-c).dot(u),(Vector(room.v[idx])-c).dot(v)) /
                    (math.cos(math.pi/8)/math.cos((angles[idx]%(math.pi/4))-math.pi/8)) for idx in previous)
    rearScale=min(1,radialLimit*.88/.78)
    for radius,depth,mat,octagonal in [(.78,.018,SILVER,True),(.735,.035,EDGE,True),(.70,.052,DARK,True),
                                      (.67,.061,EDGE,True),(.61,.073,SILVER,True),(.55,.084,EDGE,False),
                                      (.535,.075,DARK,False),(.512,.095,EDGE,False),(.475,.105,SILVER,False)]:
        points=[]
        for angle in theta:
            factor=math.cos(math.pi/8)/math.cos((angle%(math.pi/4))-math.pi/8) if octagonal else 1
            points.append(c+(u*math.cos(angle)+v*math.sin(angle))*radius*factor*rearScale+normal*depth)
        current=room.ring(points);room.bridge(previous,current,mat);previous=current
    for r in [.445,.42,.37,.31,.25,.20,.145,.09,.04,.012]:
        depth=.105+.255*math.sqrt(max(0,1-(r/.475)**2))
        current=room.ring([c+(u*math.cos(angle)+v*math.sin(angle))*r*rearScale+normal*depth for angle in theta])
        room.bridge(previous,current,GREEN if .145<=r<=.20 else SILVER if r>.25 else DARK);previous=current
    room.cap(previous,c+normal*.36,GREEN)

    # Close the wall into its cove, floor and the smoothly rooted pilot-station chassis.
    phis=sorted(floorPhis)
    wall=[support(p,latitudes[0]) for p in phis];previous=room.ring(wall)
    floorZ=-1.15
    for t in [.22,.48,.75,1.0]:
        points=[Vector((p.x*(1-.055*t),p.y*(1-.055*t),p.z*(1-t)+floorZ*t)) for p in wall]
        current=room.ring(points);room.bridge(previous,current,EDGE if t<.3 else FLOOR);previous=current
    outerPoints=points
    pod=lambda p:Vector((1.35*math.sin(p),-.95-1.20*math.cos(p),floorZ))
    for t in [.2,.4,.405,.42,.65,.655,.67,1]:
        points=[p*(1-t)+pod(phi)*t+Vector((0,0,-.004 if t in [.405,.655] else 0)) for p,phi in zip(outerPoints,phis)]
        current=room.ring(points);room.bridge(previous,current,DARK if t in [.405,.655] else FLOOR);previous=current
    def kernel(x,y,cx,cy,flatx,flaty,outerx,outery):
        r=max(abs(x-cx)/flatx,abs(y-cy)/flaty)
        if r<=1:return 1.
        return (1-smooth(flatx,outerx,abs(x-cx)))*(1-smooth(flaty,outery,abs(y-cy)))
    def station_height(x,y):
        s=.72*kernel(x,y,0,-.95,.30,.38,.58,.63)
        l=.99*kernel(x,y,-.82,-1.05,.12,.32,.42,.63)
        r=.99*kernel(x,y,.82,-1.05,.12,.32,.42,.63)
        return floorZ+max(s,l,r)
    for j in range(1,65):
        rho=1-j/64
        points=[]
        for phi in phis:
            p=pod(phi);x=p.x*rho;y=-.95+(p.y+.95)*rho
            height=(station_height(x,y)-floorZ)*(1-smooth(.85,1,rho))
            points.append(Vector((x,y,floorZ+height)))
        current=room.ring(points);room.bridge(previous,current,FLOOR if rho>.7 else SILVER);previous=current
    cabin=room.finish('Navigator | continuous cabin, station and sensor',solid=.025,floor=True)

    # Each console is one closed manufactured solid, including its instrument wells and tactile membrane.
    from instruments import build_console
    instrumentReports=[];contacts=[]
    for side in [-1,1]:
        obj,report=build_console(Surface,mats,side,station_height)
        instrumentReports.append(report);contacts.append(report['maximum_landing_error_m'])

    # One formed bucket surface carries pan, bolsters and back; its pad derives from the same support mapping.
    def seatpoint(u,t):
        if t<=.6:
            y=-1.5+1.1*t;z=-.30+.08*(1-smooth(0,.15,t))
        else:
            r=(t-.6)/.4;y=-.84+.44*(r+r*r-r*r*r);z=-.30+1.22*smooth(0,1,r)
        width=.405-.045*smooth(.7,1,t)-.055*smooth(.84,1,t)
        z+=(.075-.025*smooth(.6,1,t))*smooth(.65,1,abs(u))**2
        z-=.045*abs(u)**4*smooth(.85,1,t)
        return Vector((width*u,y,z))
    surf=Surface(mats)
    rows=[[surf.vertex(seatpoint(-1+2*i/24,j/48)) for i in range(25)] for j in range(49)]
    for j in range(48):
        for i in range(24):surf.face([rows[j][i],rows[j][i+1],rows[j+1][i+1],rows[j+1][i]],EDGE)
    seat=surf.finish('Navigator | formed bucket seat',solid=.035,upward=True)
    bpy.context.view_layer.update()
    seatTree=BVHTree.FromObject(seat,bpy.context.evaluated_depsgraph_get(),epsilon=1e-6)
    # Form the cushion from the evaluated seat, with a matching underside and a padded upper face.
    pad=Surface(mats);bottom=[];top=[]
    for j in range(49):
        t=.08+.86*j/48;lo=[];hi=[]
        for i in range(25):
            u=(-1+2*i/24)*.85
            hit,normal,_,distance=seatTree.find_nearest(seatpoint(u,t))
            assert hit is not None and distance<.012,f'Seat pad support is not on its actual shell: {distance}'
            du=seatpoint(u+.0001,t)-seatpoint(u-.0001,t)
            dt=seatpoint(u,t+.0001)-seatpoint(u,t-.0001)
            assert normal.dot(du.cross(dt).normalized())>.5,'Seat cushion projected to the wrong side of its shell'
            lo.append(pad.vertex(hit));hi.append(pad.vertex(hit+normal*(.018+.009*(1-(u/.85)**2))))
        bottom.append(lo);top.append(hi)
    for j in range(48):
        for i in range(24):
            pad.face([top[j][i],top[j][i+1],top[j+1][i+1],top[j+1][i]],SEAT)
            pad.face([bottom[j+1][i],bottom[j+1][i+1],bottom[j][i+1],bottom[j][i]],SEAT)
    def perimeter(grid):
        return grid[0][:]+[row[-1] for row in grid[1:]]+list(reversed(grid[-1][:-1]))+[row[0] for row in reversed(grid[1:-1])]
    pad.bridge(perimeter(bottom),perimeter(top),SEAT)
    cushion=pad.finish('Navigator | fitted seat pad')
    assert len(cushion.data.vertices)==len(pad.v),'Seat contact indices changed during finalization'
    cushion.vertex_groups.new(name='Mounting interface').add([idx for row in bottom for idx in row],1,'REPLACE')
    mount=Surface(mats);shape=loop2(64,4);previous=None
    for w,l,z in [(.25,.28,-.43),(.25,.28,-.415),(.19,.22,-.38),(.25,.15,-.335)]:
        current=mount.ring([(w*u,-1.0+l*v,z) for u,v in shape])
        if previous:mount.bridge(previous,current,EDGE if z<-.4 else SILVER)
        else:mount.cap(list(reversed(current)),(0,-1,-.43),DARK)
        previous=current
    mount.cap(previous,(0,-1,-.335),SILVER);mount.finish('Navigator | seat docking frame')
    for u,v in shape:contacts.append(abs(station_height(.25*u,-1+.28*v)+.43))
    assert max(contacts)<.001,'Station mating planes do not meet'

    report={'construction':'continuous quilted wall, coved floor, rooted station and swept sensor; fitted seat and console solids',
            'pilot_eye':[0,-.65,.7],'hull_role':10,'cabin_role':11,'fitted_panels':panelCount,
            'rear_assembly':{'shape':'octagonal mounting flange and integrated domed optical core','diameter_m':1.56*rearScale,'patch_clearance_scale':rearScale},
            'primitive_meshes':0,'maximum_mount_gap_m':max(contacts),'fixture_positions':fixtures,
            'instruments':instrumentReports,'instrument_state':'runtime heading and propulsion dials; rotary and palm controls remain static',
            'canopy_glass':False,'canopy_weather':False,'room_margin_scale':.875,
            'projection':'clear forward field with opaque exterior in external views',
            'approximation':'Reference-led reconstruction, without authenticated production dimensions.'}
    (root/'cockpit-inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    hlsl='// Generated from actual cabin sockets and console patches; do not edit by hand.\nstatic const float3 NAVIGATOR_LAMP_POSITIONS[3] = {\n'
    hlsl+=',\n'.join('    float3('+', '.join(f'{x:.7f}' for x in p)+')' for p in fixtures)+'\n};\n'
    assert len(fixtures)==3
    dials=sorted(instrumentReports,key=lambda r:r['live_dial_center'][0])
    hlsl+='static const float3 NAVIGATOR_DIAL_CENTERS[2] = {\n'
    hlsl+=',\n'.join('    float3('+', '.join(f'{x:.7f}' for x in r['live_dial_center'])+')' for r in dials)+'\n};\n'
    hlsl+=f"static const float NAVIGATOR_DIAL_RADIUS = {dials[0]['live_dial_radius']:.7f};\n"
    hlsl+='static const float2 NAVIGATOR_DIAL_ARC = float2('+', '.join(f'{x:.7f}' for x in dials[0]['live_arc_radii'])+');\n'
    target=root.parents[2]/'MyPlanetEngine'/'ShipNavigatorFixtures.hlsli'
    if not target.exists() or target.read_text(encoding='utf-8')!=hlsl:target.write_text(hlsl,encoding='utf-8')
    return report
