"""Continuous manufactured surfaces and matched interfaces, in metres.

Profiles are connected before triangulation. Fine recesses are carried by
shared normal/roughness sheets; moving parts retain a deliberate separation.
"""
import math
from mathutils import Vector
from mathutils.geometry import tessellate_polygon


def finish(a,obj,bevel=.018):
    if bevel:
        a.bpy.context.view_layer.objects.active=obj
        mod=obj.modifiers.new('Manufacturing edge radius','BEVEL')
        mod.width=bevel;mod.segments=2;mod.affect='EDGES'
        a.bpy.ops.object.modifier_apply(modifier=mod.name)
        mod=obj.modifiers.new('Area weighted corner normals','WEIGHTED_NORMAL')
        mod.keep_sharp=True
        a.bpy.ops.object.modifier_apply(modifier=mod.name)
    obj['city_construction']='continuous_profile'
    return obj


def extrusion(a,name,outline,front,back,mat=0,bevel=.018,detail=0):
    """A single closed XZ profile, extruded along Y; concave contours allowed."""
    points=[Vector((x,0,z)) for x,z in outline];count=len(points)
    # Match the winding to an outward front (-Y) normal.
    area=sum(outline[i][0]*outline[(i+1)%count][1]-outline[(i+1)%count][0]*outline[i][1] for i in range(count))
    if area<0:points.reverse()
    vertices=[(v.x,y,v.z) for y in [front,back] for v in points]
    lookup={tuple(v):i for i,v in enumerate(points)};faces=[]
    for tri in tessellate_polygon([points]):
        ix=tuple(v if isinstance(v,int) else lookup[tuple(v)] for v in tri)
        faces.extend([ix,tuple(i+count for i in reversed(ix))])
    for i in range(count):
        j=(i+1)%count;faces.append((i,i+count,j+count,j))
    return finish(a,a.mesh(name,vertices,faces,mat,smooth=False,detail=detail),bevel)


def vessel(a,name,cx,cy,rx,ry,base,height,mat=0,n=48):
    """One hollow moulding: foot, outside, rolled lip, inside and bottom."""
    v=[];f=[]
    sections=[(.92,.92,base), (1,1,base+.06), (1,1,base+height-.045),
              (.992,.992,base+height), (1-.115/rx,1-.115/ry,base+height),
              (1-.145/rx,1-.145/ry,base+height-.045),
              (1-.17/rx,1-.17/ry,base+.12)]
    for sx,sy,z in sections:
        for k in range(n):
            t=k*math.tau/n;v.append((cx+rx*sx*math.cos(t),cy+ry*sy*math.sin(t),z))
    for j in range(len(sections)-1):
        for k in range(n):
            q=(k+1)%n;f.append((j*n+k,j*n+q,(j+1)*n+q,(j+1)*n+k))
    f.extend([tuple(reversed(range(n))),tuple(range((len(sections)-1)*n,len(sections)*n))])
    obj=a.mesh(name,v,f,mat)
    for cap in obj.data.polygons[-2:]:cap.use_smooth=False
    obj['city_construction']='closed_hollow_moulding'
    return obj


def portal(a,x,y,z,width,depth):
    # Crown and jambs are one U-shaped solid. The internal contour is the reveal.
    w=width/2;h=2.62;r=.45;inner=w-.17;ri=.29
    outer=[(-w,0),(-w,h-r)]
    for k in range(1,7):
        t=math.pi-k*math.pi/12;outer.append((-w+r+r*math.cos(t),h-r+r*math.sin(t)))
    outer.append((w-r,h))
    for k in range(1,7):
        t=math.pi/2-k*math.pi/12;outer.append((w-r+r*math.cos(t),h-r+r*math.sin(t)))
    outer.extend([(w,0),(inner,0),(inner,h-.15-ri)])
    for k in range(1,7):
        t=k*math.pi/12;outer.append((inner-ri+ri*math.cos(t),h-.15-ri+ri*math.sin(t)))
    outer.append((-inner+ri,h-.15))
    for k in range(1,7):
        t=math.pi/2+k*math.pi/12;outer.append((-inner+ri+ri*math.cos(t),h-.15-ri+ri*math.sin(t)))
    outer.append((-inner,0))
    return extrusion(a,'formed_entry_portal',[(x+xx,z+zz) for xx,zz in outer],y-.08,y+depth,0,.025)


def service_panel(a,x,y,z,w,h,screen=False):
    # One chamfered part. Its face has unique 0..1 UVs for the shared PBR sheet.
    r=min(w*.10,.035)
    outline=[(-w/2+r,0),(w/2-r,0),(w/2,r),(w/2,h-r),(w/2-r,h),(-w/2+r,h),(-w/2,h-r),(-w/2,r)]
    obj=extrusion(a,'formed_control_panel' if screen else 'formed_service_panel',[(x+xx,z+zz) for xx,zz in outline],y-.018,y+.025,19 if screen else 18,0,1)
    uv=obj.data.uv_layers.active
    for face in obj.data.polygons:
        for loop in face.loop_indices:
            p=obj.data.vertices[obj.data.loops[loop].vertex_index].co
            uv.data[loop].uv=((p.x-x)/w+.5,(p.z-z)/h)
    return obj


def bench(a,p,seed):
    x,y,z=p
    vessel(a,'integrated_planter',x,y+.35,2.12,.72,z,.67)
    a.ellipse('planting_soil',(x,y+.35,z+.60),1.95,.55,.02,9,n=36)
    a.plants((x,y+.35,z+.64),1.92,.52,seed,count=10)
    # Front crescent seat and its cradle share matched contours. No floating
    # ellipse or capped cylinders hidden inside the planter.
    n=36;v=[];f=[];m=[]
    for rx,ry,zz in [(2.10,1.34,.36),(2.14,1.38,.43),(2.14,1.38,.49),(2.08,1.32,.53),
                      (1.99,.74,.53),(1.99,.74,.43)]:
        for j in range(n+1):
            t=math.pi+j*math.pi/n;v.append((x+rx*math.cos(t),y+.35+ry*math.sin(t),z+zz))
    stride=n+1
    for row in range(6):
        following=(row+1)%6
        for j in range(n):
            f.append((row*stride+j,row*stride+j+1,following*stride+j+1,following*stride+j));m.append(20 if row in [1,2,3,4] else 1)
    for j in [0,n]:f.append(tuple(row*stride+j for row in (range(6) if j==0 else reversed(range(6)))));m.append(1)
    seat=a.mesh('joined_seat_cradle',v,f,face_materials=m)
    seat['city_construction']='closed_seat_cradle'
    # UVs keep manufactured slat grooves on the surface, not as extra bars.
    uv=seat.data.uv_layers.active
    for loop in seat.data.loops:
        p0=seat.data.vertices[loop.vertex_index].co
        uv.data[loop.index].uv=((p0.x-x)*.5,(p0.y-y)*.5)
    for side in [-1,1]:
        xx=x+side*1.40
        outline=[(xx-.12,z+.05),(xx+.12,z+.05),(xx+.18,z+.41),(xx+.11,z+.45),(xx-.14,z+.45)]
        extrusion(a,'seat_ground_bracket',outline,y-.59,y+.05,1,.025)
        # Bent plate armrest with continuous root, not pipe elbows.
        outline=[(xx-.04,z+.48),(xx+.04,z+.48),(xx+.08,z+.70),(xx+.04,z+.75),(xx-.04,z+.75),(xx-.08,z+.70)]
        extrusion(a,'cast_armrest',outline,y-.80,y-.25,5,.024,1)
    for k in range(3):
        # Curved backrest seated into the planter's front lip.
        vv=[];ff=[]
        for yy,dz in [(0,0),(.07,0),(.07,.065),(0,.065)]:
            for j in range(25):
                xx=-1.55+j*3.1/24;front=.35-.72*math.sqrt(max(.01,1-(xx/2.12)**2))
                vv.append((x+xx,y+front+yy,z+.68+k*.085+dz))
        for row in range(4):
            for j in range(24):ff.append((row*25+j,row*25+j+1,((row+1)%4)*25+j+1,((row+1)%4)*25+j))
        ff.extend([(0,25,50,75),(24,99,74,49)])
        a.mesh('curved_timber_backrest',vv,ff,2,smooth=False,detail=1)
    for xx in [-1.3,1.3]:
        front=.35-.72*math.sqrt(1-(xx/2.12)**2)
        # Rear straps join all three boards to the planter moulding.
        extrusion(a,'backrest_mounting_strap',[(x+xx-.035,z+.51),(x+xx+.035,z+.51),
                  (x+xx+.035,z+.93),(x+xx-.035,z+.93)],y+front+.05,y+front+.12,1,.012,1)


def canopy_support(a,p):
    h=p['height'];w=p['width']
    outline=[(-1.4,0),(-.65,0),(-.42,h*.60),(w*.28,h*.83),(w*.32,h*.87),
             (w*.22,h*.86),(-.15,h*.70),(-w*.28,h*.84),(-w*.32,h*.82),(-1.17,h*.59)]
    return extrusion(a,'continuous_forked_canopy_support',outline,-.25,.25,0,.055)


def bogie(a,x,cabin_x):
    # A single forged yoke has a broad roof saddle and a flared axle carrier.
    outline=[(x-.24,-1.31),(x+.24,-1.31),(x+.17,-.94),(x+.45,-.42),(x+.57,-.34),
             (x+.57,-.08),(x-.57,-.08),(x-.57,-.34),(x-.38,-.43),(x-.20,-.96)]
    obj=extrusion(a,'forged_suspension_yoke',outline,-.31,.31,1,.035)
    # The saddle ends match the cabin crown; it spreads the suspension load.
    vertices=[];faces=[];nx=4;ny=4;stride=ny+1
    for layer in [0,1]:
        for i in range(nx+1):
            xx=x-.42+.84*i/nx;r=(1-((xx-cabin_x)/3.92)**2)**.275
            for j in range(ny+1):
                yy=-.42+.84*j/ny
                zz=-3.25+2*r*math.sqrt(1-(yy/(1.54*r))**2)+.003 if layer==0 else -1.22
                vertices.append((xx,yy,zz))
    count=(nx+1)*(ny+1)
    for i in range(nx):
        for j in range(ny):
            k=i*stride+j;quad=(k,k+1,k+stride+1,k+stride)
            faces.extend([quad,tuple(q+count for q in reversed(quad))])
    perimeter=[i*stride for i in range(nx+1)]+[nx*stride+j for j in range(1,ny+1)]+[i*stride+ny for i in reversed(range(nx))]+list(reversed(range(1,ny)))
    for i,k in enumerate(perimeter):
        q=perimeter[(i+1)%len(perimeter)];faces.append((k,q,q+count,k+count))
    saddle=a.mesh('conformal_roof_saddle',vertices,faces,0)
    saddle['city_construction']='closed_conformal_interface'
    return obj
