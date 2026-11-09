"""Metric, bounded architectural fittings shared by generated city assets.

Readable function precedes ornament: each entrance has a leaf, an opening
mechanism, a frame and a threshold. Small fasteners retire with distance.
"""
import math
import random
from mathutils import Vector
import manufacturing


def mark(obj, role, assembly=''):
    obj['city_part']=role
    if assembly:obj['city_assembly']=assembly
    return obj


def round_frame(a,name,x,y,z,w,h,r=.12,mat=1,radius=.045,detail=1):
    points=[]
    for cx,cz,start in [(x+w/2-r,z+r,-math.pi/2),(x+w/2-r,z+h-r,0),
                        (x-w/2+r,z+h-r,math.pi/2),(x-w/2+r,z+r,math.pi)]:
        for i in range(5):
            t=start+i*math.pi/8;points.append((cx+r*math.cos(t),y,cz+r*math.sin(t)))
    points.append(points[0])
    return a.tube(name,points,radius,mat,6,detail=detail)


def fastener(a,p,normal=(0,-1,0),radius=.022):
    p=Vector(p);n=Vector(normal)
    return mark(a.tube('captive_fastener',[tuple(p),tuple(p+n*.012)],radius,16,6,detail=3),'fastener')


def panel(a,x,y,z,w,h,assembly='service',screen=False):
    mark(manufacturing.service_panel(a,x,y,z,w,h,screen),'display' if screen else 'service_panel',assembly)


def door(a,x,y,z,w=1.05,h=2.30,assembly='entry',double=False,primary=False):
    # The two physical leaves remain closed in this exterior milestone.
    count=2 if double else 1;gap=.012
    for i in range(count):
        cx=x+(i-(count-1)/2)*w
        leaf=mark(a.cube('entry_door',(cx,y,z+h/2),(w-gap,.075,h),14,0),'door',assembly)
        if primary and i==0:leaf['city_primary_entry']=[x,y-.17,z]
        round_frame(a,'door_leaf_seal',cx,y-.05,z,w-gap,h,.09,15,.018,1)
        if not double:
            hx=cx+w*.34
            mark(a.tube('door_pull',[(hx,y-.065,z+.92),(hx,y-.15,z+.96),
                                    (hx,y-.15,z+1.35),(hx,y-.065,z+1.39)],.018,5,6,detail=2),'handle',assembly)
            for zz in [.36,h-.36]:
                mark(a.tube('door_hinge',[(cx-w*.47,y-.045,z+zz),(cx-w*.47,y-.045,z+zz+.11)],.025,16,6,detail=2),'hinge',assembly)
    round_frame(a,'entrance_reveal',x,y-.012,z-.025,w*count+.16,h+.12,.13,1,.070,0)
    mark(a.cube('door_threshold',(x,y-.075,z-.025),(count*w+.25,.40,.05),16,0),'threshold',assembly)
    # Transom actuator, presence sensor and a lock/read head make the mechanism legible.
    mark(a.cube('door_actuator',(x,y-.02,z+h+.17),(count*w*(1.08 if double else .68),.14,.095),16,0,detail=1),'opening_drive',assembly)
    mark(a.cube('presence_sensor',(x,y-.102,z+h+.16),(.12,.045,.047),15,0,detail=2),'opening_control',assembly)
    panel(a,x+w*count*.5+.24,y+.025,z+.94,.20,.32,assembly,screen=True)
    return x,y-.17,z


def entrance(a,p,x,y,z=.15,double=True,primary=True,depth=1.45):
    w=1.02 if double else 1.10;outer=w*(2 if double else 1)+.48
    assembly=p['id']+'_main_entry'
    # A deep porch joins the facade to the pedestrian threshold without a flat sticker.
    manufacturing.portal(a,x,y,z,outer+.25,depth)
    a.cube('porch_light',(x,y+.28,z+2.545),(outer*.62,.035,.016),6,0,detail=2)
    a.cube('entrance_landing',(x,y-.20,z-.075),(outer+.45,1.2,.15),7,0)
    for step in range(max(0,math.ceil((z-.18)/.12))):
        top=z-(step+1)*.12
        a.cube('entry_step',(x,y-.90-step*.32,top-.075),(outer+.45,.40,.15),7,0)
    door(a,x,y,z,w,2.30,assembly,double,primary)
    # Service identifier is generated geometry, not unreadable baked pseudo-text.
    panel(a,x-outer*.5-.23,y+.06,z+1.02,.26,.42,assembly,screen=True)
    for side in [-1,1]:
        a.cube('drain_grille',(x+side*(outer/2+.12),y-.35,z+.006),(.10,.78,.012),15,0,detail=2)


def furnishings(a,p):
    k=p['kind'];h=p['height']
    if k=='lamp':
        panel(a,-.43,-.19,.18,.17,.34)
        for x in [-.62,-.27]:fastener(a,(x,0,.065),(0,0,1))
    if k=='fountain':
        panel(a,-.03,-.30,.22,.27,.38,screen=False)
        a.tube('basin_drain',[(0,-.20,.853),(0,-.20,.86)],.055,16,12,detail=2)
        a.cube('water_button',(.17,-.30,1.0),(.065,.04,.08),5,.01,detail=2)
    if k=='cabinet':
        panel(a,-.60,-.424,1.34,.58,.36,screen=True)
        panel(a,.60,-.424,.34,.70,.42)
        for x in [-1.0,1.0]:
            for z in [.44,1.72]:fastener(a,(x,-.424,z))
    if k=='irrigation':
        panel(a,0,-.68,.26,.56,.49,screen=True)
        for side in [-1,1]:
            for x in [1.03,1.44]:
                a.tube('pipe_flange',[(side*x,0,.25),(side*(x+.065),0,.25)],.20,16,10,detail=1)
    if k in ['planter','growing_bed']:
        for x in [-p['width']*.32,p['width']*.32]:
            a.cube('planter_drain_slot',(x,-p['depth']*.48,.12),(.15,.028,.032),15,0,detail=2)


def engineering(a,p):
    k=p['kind'];w=p['width'];d=p['depth'];h=p['height']
    if k in ['station','viaduct_ring']:
        for y in [-1.8,1.8]:
            a.cube('guideway_bearing',(0,y,22.54),(1.8,1.15,.20),16,.025)
            a.cube('elastomer_bearing',(0,y,22.39),(1.54,.92,.11),15,0)
            for x in [-.66,.66]:
                for yy in [-.36,.36]:fastener(a,(x,y+yy,22.66),(0,0,1),.055)
        for y in [-3.3,3.3]:
            a.cube('anchor_plate',(0,y,.15),(2.5,1.5,.12),16,.02)
            for x in [-.92,.92]:
                for yy in [-.51,.51]:fastener(a,(x,y+yy,.22),(0,0,1),.06)
    if k=='station':
        entrance(a,p,0,d*.32-1.91,.15,double=True)
        door(a,0,d*.32-1.91,17.87,1.0,2.30,p['id']+'_platform_lift',True)
        for side in [-1,1]:
            a.cube('platform_edge_inlay',(0,side*d*.28,17.862),(w*.80,.17,.018),5,0,detail=1)
        panel(a,w*.32,-d*.27,18.1,1.4,.72,screen=True)
    if k=='water_tower':
        panel(a,-.48,-.77,.50,.55,.85,screen=True)
        for z in [1.1,h*.50,h*.74]:
            for x in [-.45,.1]:a.tube('pipe_coupling',[(x,0,z),(x,0,z+.12)],.15,16,10,detail=1)
    if k=='hangar':
        for side in [-1,1]:
            a.tube('door_guide_channel',[(side*w*.38,-d*.44,.20),(side*w*.38,-d*.44,h*.65)],(.09,.17),16,6)
        for x in [-w*.15,w*.15]:
            a.cube('apron_drain',(x,-d*.44,.015),(w*.25,.25,.025),15,0,detail=1)
        panel(a,w*.22,-d*.435,.55,.70,1.2,screen=True)
    if k=='suspended_train':
        # Door fittings conform to the ovoid; no flat rectangle floats in space.
        for cx in [-4.05,4.05]:
            for side in [-1,1]:
                def surface(x,z,offset=.018):
                    r=max(.1,1-((x-cx)/3.92)**2)**.275
                    yy=1.54*r*math.sqrt(max(.01,1-((z+3.25)/(2*r))**2))
                    return (x,side*(yy+offset),z)
                assembly=f"cabin_{cx}_{side}"
                # Two sliding leaves, a central seal and flush emergency pulls.
                for half in [-1,1]:
                    xx=cx+half*.36;v=[surface(xx+dx,z) for dx,z in [(-.35,-4.72),(.35,-4.72),(.35,-2.32),(-.35,-2.32)]]
                    mark(a.mesh('cabin_door',v,[(0,1,2,3)],13,smooth=False),'door',assembly)
                for x in [cx-.72,cx,cx+.72]:
                    a.tube('cabin_door_seal',[surface(x,-4.72+i*2.4/12,.040) for i in range(13)],.026,15,5,detail=1)
                for z in [-4.72,-2.32]:
                    a.tube('cabin_door_rail',[surface(cx-.72+i*1.44/10,z,.045) for i in range(11)],.045,16,6,detail=1)
                for half in [-1,1]:
                    mark(a.tube('cabin_emergency_pull',[surface(cx+half*.12,z,.075) for z in [-3.8,-3.45]],.023,5,6,detail=2),'handle',assembly)
                for z in [-4.85,-1.92]:
                    a.tube('cabin_panel_seam',[surface(cx-2.7+i*5.4/24,z,.016) for i in range(25)],.012,15,4,detail=2)
            for x in [cx-1.7,cx+1.7]:
                # Captive wheel pairs, brake calipers and suspension pivots.
                for dx in [-.38,.38]:
                    for side in [-1,1]:
                        a.tube('bogie_running_wheel',[(x+dx,side*.35,-.18),(x+dx,side*.48,-.18)],.16,15,12,detail=1)
                        a.tube('bogie_axle_cap',[(x+dx,side*.48,-.18),(x+dx,side*.51,-.18)],.065,16,8,detail=2)
                for side in [-1,1]:
                    a.tube('suspension_damper',[(x-.25,side*.27,-.45),(x+.10,side*.27,-1.20)],.055,16,8,detail=1)
                    a.tube('pivot_pin',[(x,side*.28,-.80),(x,side*.36,-.80)],.10,5,10,detail=1)
                a.cube('bogie_inspection_cover',(x,0,-.27),(.68,.59,.055),1,0,detail=1)
        for end in [-1,1]:
            x=end*7.66
            for y in [-.32,.32]:
                a.tube('recessed_headlight',[(x,y,-3.4),(x+end*.04,y,-3.4)],.10,6,8,detail=1)


def decorate(p,a):
    k=p['kind'];w=p['width'];d=p['depth']
    if k in ['ribbon_habitat','apartments','courtyard_habitat','civic','terminal','greenhouse','market','house','hangar']:
        # The public entrance establishes the placement/access contract.
        if k=='house':x=w*.20;y=-d*.43
        elif k=='hangar':x=w*.35;y=-d*.44
        elif k in ['civic','terminal']:x=-w*.29;y=-d*.43
        elif k=='market':x=0;y=d*.165
        else:x=0;y=-d*.49
        z=.52 if k=='ribbon_habitat' else .15
        depth=1.45
        if k!='market':
            # Sample the complete standing approach. One centre ray misses
            # an asymmetric shell or reveal crossing the side of a doorway.
            facade=[];deps=a.bpy.context.evaluated_depsgraph_get()
            for dx in [-.75,0,.75]:
                for dz in [.35,1.15,2.0]:
                    hit,location,normal,index,obj,matrix=a.bpy.context.scene.ray_cast(
                        deps,Vector((x+dx,-100,z+dz)),Vector((0,1,0)))
                    if hit:facade.append(float(location.y))
            if facade:y=min(facade)-1.65
        if k=='greenhouse':
            # The glazed bays project beyond the central service spine. An
            # actual continuous vestibule joins that spine to the public face.
            back=y+1.45;y=-d*.51-.65;depth=max(1.45,back-y)
            cutter=a.cube('temporary_vestibule_clearance',(0,y+depth*.5,z+1.35),(3.0,depth+.20,2.75),0,0)
            for obj in list(a.bpy.context.scene.objects):
                if obj==cutter or obj.type!='MESH' or not any(s in obj.name for s in ['glass_envelope','greenhouse_rib','glazing_rail']):continue
                a.bpy.context.view_layer.objects.active=obj
                mod=obj.modifiers.new('Clear continuous public vestibule','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
                a.bpy.ops.object.modifier_apply(modifier=mod.name)
            a.bpy.data.objects.remove(cutter,do_unlink=True)
        if k=='ribbon_habitat':
            # Remove only the ground-level rail across the approach. A closed
            # boolean cut caps the two rail ends before LOD simplification.
            cutter=a.cube('temporary_entry_clearance',(x,y+1.0,z+1.1),(3.2,5.2,2.9),0,0)
            for obj in list(a.bpy.context.scene.objects):
                if obj==cutter or obj.type!='MESH' or not any(s in obj.name for s in ['balcony_guard','handrail']):continue
                points=[obj.matrix_world@v.co for v in obj.data.vertices]
                if min(v.z for v in points)>2.3 or max(v.x for v in points)<x-1.6 or min(v.x for v in points)>x+1.6:continue
                a.bpy.context.view_layer.objects.active=obj
                modifier=obj.modifiers.new('Open public approach','BOOLEAN');modifier.operation='DIFFERENCE';modifier.solver='EXACT';modifier.object=cutter
                a.bpy.ops.object.modifier_apply(modifier=modifier.name)
            a.bpy.data.objects.remove(cutter,do_unlink=True)
        entrance(a,p,x,y,z,double=k not in ['house','hangar'],depth=depth)
    furnishings(a,p);engineering(a,p)


def audit(objects):
    parts={};assemblies={};primary=[]
    for obj in objects:
        role=obj.get('city_part');group=obj.get('city_assembly')
        if role:parts[role]=parts.get(role,0)+1
        if group:assemblies.setdefault(group,set()).add(role)
        if 'city_primary_entry' in obj:primary.append(list(obj['city_primary_entry']))
    for name,roles in assemblies.items():
        if 'door' in roles and not roles.intersection({'handle','opening_control','opening_drive'}):
            raise ValueError('Door without a readable opening system: '+name)
    # Independent spatial check: a 1.1 m wide standing approach must remain
    # clear in front of the closed leaf. Topology alone cannot find a planter
    # or structural rib placed in front of an otherwise valid door.
    blocked=[]
    for x,y,z in primary:
        for dx in [-.55,0,.55]:
            for dz in [.35,1.15,2.0]:
                start=Vector((x+dx,y-2.5,z+dz));end=Vector((x+dx,y-.025,z+dz))
                for obj in objects:
                    inverse=obj.matrix_world.inverted();origin=inverse@start;finish=inverse@end
                    direction=finish-origin
                    hit,point,normal,index=obj.ray_cast(origin,direction.normalized(),distance=direction.length)
                    if hit:blocked.append({'object':obj.name,'probe':[dx,dz],'point':list(obj.matrix_world@point)})
    return {'parts':parts,'assemblies':{name:sorted(v) for name,v in assemblies.items()},'primary_entries':primary,
            'approach_clear':not blocked,'approach_obstructions':blocked}
