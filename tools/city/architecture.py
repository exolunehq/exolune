"""Structural variants and transport assemblies; metric meshes, never scaled facades."""
import math
import random
from masterplan import rail_point,rail_heading


def build(p,a):
    kind=p['kind'];w=p['width'];d=p['depth'];h=p['height'];seed=p['seed']
    if kind=='ribbon_habitat':
        wings=p.get('wings',2);floors=p.get('floors',4);phase=p.get('phase',.4)
        rise=p.get('floor_height',3.15);profile=p.get('profile','ribbon');rng=random.Random(seed)
        a.ellipse('podium',(0,0,-.35),w*.49,d*.49,.5,7,n=48,wave=.035)
        for wing in range(wings):
            angle=phase+wing*math.tau/max(wings,2)
            cx=math.cos(angle)*w*(.20 if wings>1 else 0);cy=math.sin(angle)*d*(.21 if wings>1 else 0)
            count=max(2,floors-(wing%3)*p.get('stagger',1))
            if profile=='split' and wing:count=max(2,count-1)
            rx=w*(.27 if wings>1 else .46);ry=d*(.30 if wings>1 else .44)
            for level in range(count):
                # Connected wings have small manufactured level offsets; their
                # overlapping terraces must never share a coplanar raster face.
                before=set(a.bpy.context.scene.objects)
                z=.18+level*rise+wing*.075;shrink=1-p.get('setback',.025)*level
                if profile=='terrace':shrink-=.055*(level//2)
                if profile=='lantern':shrink+=.045*math.sin(level*math.pi/max(1,count-1))
                dx=p.get('sweep',.25)*level*math.cos(angle+.7);dy=.18*level*math.sin(angle)
                x=cx+dx;y=cy+dy;r=rx*shrink;s=ry*shrink
                a.ellipse('inhabited_slab',(x,y,z),r,s,.32,0,n=48,wave=.045)
                a.ribbon('timber_shared_terrace',(x,y),r-.15,s-.15,z+.34,1.20,.08,2,wave=.045,n=32)
                a.ellipse('recessed_rooms',(x,y+.12,z+.34),r-1.25,s-1.28,rise-.49,12,n=48,wave=.045)
                a.ribbon('balcony_guard',(x,y),r-.15,s-.15,z+1.30,.045,.74,4,wave=.045,n=32)
                points=[(x+(r-.10)*math.cos(t)*(1+.045*math.sin(3*t+.7)),y+(s-.10)*math.sin(t)*(1+.045*math.sin(3*t+.7)),z+1.32) for t in [i*math.tau/32 for i in range(33)]]
                a.tube('handrail',points,.033,5,5,detail=2)
                fins=8 if profile!='lantern' else 12
                for j in range(fins):
                    t=j*math.tau/fins;wave=1+.045*math.sin(3*t+.7)
                    xx=x+(r-1.23)*math.cos(t)*wave;yy=y+.12+(s-1.25)*math.sin(t)*wave
                    ob=a.cube('timber_fin',(xx,yy,z+rise*.53),(.09,.25,rise-.53),2,0,detail=1);ob.rotation_euler.z=t-math.pi/2
                if level%2==wing%2:
                    a.planter((x-r*.4,y-s+.48,z+.34),1.1,.32,seed+level*17+wing,.32)
                if level==0 or (level+wing)%3==0:
                    for j in range(3):
                        a.cube('privacy_screen',(x+r*.42+j*.20,y-s*.65,z+1.25),(.075,.30,1.75),2,0,detail=1)
                twist=p.get('twist',0)*level
                if twist:
                    transform=a.Matrix.Translation((x,y,0))@a.Matrix.Rotation(twist,4,'Z')@a.Matrix.Translation((-x,-y,0))
                    for obj in set(a.bpy.context.scene.objects)-before:obj.matrix_world=transform@obj.matrix_world
            top=.18+count*rise+wing*.075
            a.shell('roof_leaf',(cx+p.get('sweep',.25)*(count-1)*math.cos(angle+.7),cy+.18*(count-1)*math.sin(angle),top),
                    rx*shrink*1.04,ry*shrink*2.03,1.25 if profile=='terrace' else 2.3 if profile=='lantern' else 1.9,math.sin(angle)*1.25,glass=False,thickness=.24)
            # The swept structural ribbon, unlike a uniform scale, changes its
            # connections with the floor count and lateral terrace offsets.
            pts=[]
            for j in range(33):
                t=j/32;pts.append((cx-rx*.60+math.sin(t*math.pi*1.7+phase)*1.3,cy-ry*.65,top*t))
            a.tube('structural_ribbon',pts,[(.27+.22*abs(math.cos(j/32*math.pi)),.38) for j in range(33)],0,10)
        a.ellipse('shared_vertical_core',(0,.5,.1),1.4,1.5,floors*rise,1,n=24)
        for level in range(1,floors):
            a.ellipse('shared_landing',(0,.5,level*rise),w*.22,2.0,.24,0,n=32)
        return True
    if kind=='courtyard_habitat':
        a.ellipse('foundation',(0,0,-.35),w*.50,d*.50,.5,7,n=56,wave=.06)
        for i in range(p.get('wings',3)):
            angle=i*2.18+p.get('phase',.4);x=math.cos(angle)*w*.22;y=math.sin(angle)*d*.22
            before=set(a.bpy.context.scene.objects)
            a.shell('inhabited_crescent',(0,0,.15),w*.22,d*.48,h*(.72+.12*math.sin(i+seed)),i*.65,thickness=.27)
            for obj in set(a.bpy.context.scene.objects)-before:
                obj.rotation_euler.z=angle+.7;obj.location.x+=x;obj.location.y+=y
        a.planter((0,-d*.08,.15),w*.12,d*.12,seed,.4)
        return True
    if kind=='market':
        a.ellipse('public_podium',(0,0,-.3),w*.51,d*.50,.45,7,n=56)
        for i in range(3):
            x=(i-1)*w*.27;y=(i%2)*d*.24
            a.pillar('market_branch',x-1,y,h*.65,1.4)
            a.shell('market_leaf',(x,y,h*.58),w*.22,d*.61,h*.28,(i-1)*.9,glass=False)
            a.cube('shared_counter',(x,y+1,1.0),(w*.26,1.2,.4),2,.08)
            a.planter((x,-d*.25,0),1.35,.5,seed+i,.42)
        a.shell('workshop_back',(0,d*.30,0),w*.27,d*.27,h*.5,.3)
        return True
    if kind=='station':
        # Guideway datum is z=23 m in every station/ring variant.
        # Public decks sit under the cabins; ramps are exterior scene geometry.
        a.ellipse('station_foundation',(0,0,-1.2),w*.47,d*.47,1.4,7,n=64,wave=.04)
        for x in [-w*.32,w*.32]:
            pts=[(x+math.copysign(1,x)*w*.19*math.sin(t+.6),math.cos(t)*d*.41,14+14*math.sin(t)) for t in [(-math.pi/2)+i*math.tau/80 for i in range(81)]]
            a.tube('load_ring',pts,[(.52,.84)]*len(pts),0,12)
            pts2=[(xx,yy*.97,zz) for xx,yy,zz in pts];a.tube('ring_teal_inlay',pts2,.26,1,8)
        deck=17.85
        a.ellipse('boarding_deck',(0,0,deck-.6),w*.46,d*.38,.60,0,n=64,wave=.025)
        for y in [-d*.28,d*.28]:
            a.tube('platform_guard',[(x,y,deck+1.08) for x in [-w*.41,w*.41]],.045,5,8,detail=1)
        for i in range(2):
            a.shell('solar_station_petal',((i-.5)*w*.43,(i-.5)*d*.18,25.0+i*1.05),w*.31,d*.77,3.4,(i-.5)*3,glass=False,thickness=.31)
        a.shell('waiting_lounge',(0,d*.25,deck),w*.26,d*.23,4.5,.9,thickness=.25)
        for x in [-w*.27,0,w*.27]:a.furniture((x,-d*.25,deck),'bench',seed+int(x*7))
        a.ellipse('lift_core',(0,d*.32,.1),1.75,1.85,deck-.1,4,n=32)
        for i in range(4):a.ellipse('lift_ring',(0,d*.32,4*i),1.82,1.92,.20,0,n=32)
        # A continuous spiral pedestrian ramp with guard, sized at 7% grade.
        turns=3.15;steps=240;verts=[];faces=[]
        for i in range(steps+1):
            t=i/steps;ang=t*math.tau*turns;z=.15+(deck-.15)*t
            for radius in [10.6,12.5]:verts.append((radius*math.cos(ang),radius*math.sin(ang),z))
            if i:faces.append((2*i-2,2*i-1,2*i+1,2*i))
        ramp=a.mesh('spiral_ramp',verts,faces,7,smooth=False)
        a.bpy.context.view_layer.objects.active=ramp
        solid=ramp.modifiers.new('Structural ramp thickness','SOLIDIFY');solid.thickness=.22;solid.offset=-1
        a.bpy.ops.object.modifier_apply(modifier=solid.name)
        a.tube('ramp_guard',[(12.5*math.cos(i/steps*math.tau*turns),12.5*math.sin(i/steps*math.tau*turns),1.2+(deck-.15)*i/steps) for i in range(steps+1)],.035,5,5,detail=1)
        return True
    if kind=='viaduct_ring':
        a.ellipse('ring_foundation',(0,0,-2),2.8,5.5,2.1,7,n=40)
        pts=[(1.5*math.sin(t+.8),9*math.cos(t),13+13*math.sin(t)) for t in [-math.pi/2+i*math.tau/72 for i in range(73)]]
        a.tube('supporting_ring',pts,[(.44,.78)]*len(pts),0,12)
        a.tube('teal_ring_reveal',[(x,y*.98,z) for x,y,z in pts],.23,1,8)
        for y in [-1.8,1.8]:a.tube('beam_saddle',[(0,y,22),(0,y,23.3)],.38,1,8)
        return True
    if kind=='guideway':
        for side in [-1,1]:
            points=[]
            for x in range(-455,456,3):
                xx,yy=rail_point(x);ang=rail_heading(x)
                points.append((xx-math.sin(ang)*side*1.8,yy+math.cos(ang)*side*1.8,0))
            a.tube('continuous_guidebeam',points,[(.42,.47)]*len(points),0,8)
            a.tube('guidebeam_teal_soffit',[(x,y,z-.37) for x,y,z in points],.13,1,6)
            a.tube('guideway_light',[(x,y,z-.46) for x,y,z in points],.022,6,5,detail=2)
        return True
    if kind=='suspended_train':
        for side in [-1,1]:
            cx=side*4.05
            # Longitudinal tapered ovoid. Distinct panels preserve windows and
            # bodywork as geometry without reconstructing people from a board.
            n=32;m=24;v=[];faces=[];mats=[]
            for i in range(m+1):
                t=math.pi*(.03+.94*i/m);xx=cx+3.92*math.cos(t);r=math.sin(t)**.55
                for j in range(n):
                    ang=j*math.tau/n;v.append((xx,r*1.54*math.cos(ang),-3.25+r*2.0*math.sin(ang)))
            for i in range(m):
                for j in range(n):
                    k=i*n+j;faces.append((k,i*n+(j+1)%n,(i+1)*n+(j+1)%n,k+n))
                    mats.append(13 if -0.35<math.sin((j+.5)*math.tau/n)<.88 and 2<i<m-2 else 0)
            faces.extend([tuple(reversed(range(n))),tuple(range(m*n,(m+1)*n))]);mats.extend([0,0])
            cabin=a.mesh('panoramic_cabin',v,faces,face_materials=mats)
            for loop in cabin.data.loops:
                point=cabin.data.vertices[loop.vertex_index].co
                cabin.data.uv_layers.active.data[loop.index].uv=((point.x-cx)/3.2,1-(point.z+4.9)/2.66)
            for xx in [cx-2,cx,cx+2]:
                radius=(1-((xx-cx)/3.92)**2)**.275
                a.tube('cabin_window_mullion',[(xx,(1.54*radius+.008)*math.cos(t),-3.25+(2*radius+.008)*math.sin(t)) for t in [j*math.tau/32 for j in range(33)]],.025,1,6,detail=1)
            for x in [cx-1.7,cx+1.7]:
                a.manufacturing.bogie(a,x,cx)
        for i in range(9):
            x=(i-4)*.12;a.tube('flexible_joint',[(x,1.25*math.cos(t),-3.25+1.6*math.sin(t)) for t in [j*math.tau/24 for j in range(25)]],.055,1,6,detail=1)
        return True
    if kind in ['irrigation','cabinet','wayfinding']:
        if kind=='wayfinding':
            a.pillar('wayfinding_stem',0,0,2.3,.2)
            a.cube('wayfinding_panel',(.2,0,1.9),(1.2,.15,.85),1,.11)
            for i in range(3):a.cube('inlaid_direction',(.05+i*.05,-.082,2.15-i*.19),(.7-.1*i,.012,.025),6,.003,detail=2)
        elif kind=='irrigation':
            a.shell('irrigation_casing',(0,0,0),1.1,1.3,1.1,.18,solar=True)
            for side in [-1,1]:a.tube('water_connection',[(side*.9,0,.25),(side*1.7,0,.25)],.13,5,10)
        else:
            a.cube('service_cabinet',(0,0,1.05),(2.4,.7,2.1),1,.13)
            for x in [-.6,.6]:
                a.cube('cabinet_door',(x,-.37,1.10),(1.08,.08,1.78),0,.06)
                a.cube('handle',(x+.3,-.44,1.1),(.035,.09,.30),5,.01,detail=1)
        return True
    return False
