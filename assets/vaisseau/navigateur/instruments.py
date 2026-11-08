"""Formed console instruments: shared seams, recessed dials and continuous tactile wells.

All visible details are geometry or material regions in one closed console solid.
Scales are authored reference-led fittings, not claims about the film's controls.
"""
import math
from mathutils import Vector

TAU=math.tau
DARK,SILVER,EDGE,FLOOR,SEAT,PAD,RED,BLUE,GREEN,LENS,PUPIL,ETCH,AMBER,LIVE=range(14)
DIAL_RADIUS=.131
DIAL_ARC=(.143,.148)

def ease(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)

def polar_loop(n=192,power=6):
    pts=[]
    for k in range(n):
        t=TAU*k/n;x=math.cos(t);y=math.sin(t);d=(abs(x)**power+abs(y)**power)**(1/power)
        pts.append((x/d,y/d))
    return pts

def bridge_parameter(mesh,a,ta,b,tb,mat):
    """Zip two CCW loops with different sampling, preserving every boundary edge."""
    assert len(a)==len(ta) and len(b)==len(tb)
    aa=sorted(zip(ta,a));bb=sorted(zip(tb,b));ta,a=map(list,zip(*aa));tb,b=map(list,zip(*bb))
    i=j=0
    while i<len(a) or j<len(b):
        ia=i%len(a);jb=j%len(b)
        na=ta[(i+1)%len(a)]+(TAU if i+1>=len(a) else 0) if i<len(a) else float('inf')
        nb=tb[(j+1)%len(b)]+(TAU if j+1>=len(b) else 0) if j<len(b) else float('inf')
        if abs(na-nb)<1e-7:
            mesh.face([a[ia],a[(i+1)%len(a)],b[(j+1)%len(b)],b[jb]],mat);i+=1;j+=1
        elif na<nb:
            mesh.face([a[ia],a[(i+1)%len(a)],b[jb]],mat);i+=1
        else:
            mesh.face([a[ia],b[(j+1)%len(b)],b[jb]],mat);j+=1

def patch_boundary(cells,mesh,cx,cy):
    counts={}
    for cell in cells:
        for a,b in zip(cell,cell[1:]+cell[:1]):
            edge=tuple(sorted((a,b)));counts[edge]=counts.get(edge,0)+1
    edges={e for e,n in counts.items() if n==1};vertices={v for e in edges for v in e}
    angle=lambda v:math.atan2(mesh.v[v][1]-cy,mesh.v[v][0]-cx)%TAU
    ordered=sorted(vertices,key=angle)
    assert {tuple(sorted(e)) for e in zip(ordered,ordered[1:]+ordered[:1])}==edges,f'Instrument patch perimeter is not a simple loop at {(cx,cy)}'
    return ordered,[angle(v) for v in ordered]

def ring_material(mesh,a,b,fn):
    for k in range(len(a)):
        kn=(k+1)%len(a);mesh.face([a[k],a[kn],b[kn],b[k]],fn(k))

def segment_distance(x,y,a,b):
    dx=b[0]-a[0];dy=b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/max(dx*dx+dy*dy,1e-12)))
    return math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)

def instrument(mesh,boundary,angles,cx,cy,kind,side):
    n=192;theta=[TAU*k/n for k in range(n)];rounded=polar_loop(n,7)
    previous=boundary
    if kind=='legend':
        for j,(sx,sy,z,mat) in enumerate([(.214,.022,.070,SILVER),(.209,.019,.069,EDGE),(.205,.016,.066,DARK)]):
            current=mesh.ring([(cx+sx*u,cy+sy*v,z) for u,v in rounded])
            if j==0:
                innerAngles=[math.atan2(mesh.v[idx][1]-cy,mesh.v[idx][0]-cx)%TAU for idx in current]
                bridge_parameter(mesh,previous,angles,current,innerAngles,mat)
            else:mesh.bridge(previous,current,mat)
            previous=current
        motifs=[[(0,1),(-1,1),(-1,-1),(.5,-1),(.5,0),(0,0)],
                [(-1,-1),(-1,1),(1,1),(1,0),(0,0),(0,-1)],
                [(-1,0),(0,0),(0,1),(1,1),(1,-1),(0,-1)],
                [(-1,1),(1,1),(1,-1),(-1,-1),(-1,0),(0,0)],
                [(1,1),(-1,1),(-1,-1),(0,-1),(0,0),(1,0)]]
        routes=[[(offset+x*.021,y*.010) for x,y in motif] for offset,motif in zip([-.16,-.08,0,.08,.16],motifs)]
        segments=[(a,b) for path in routes for a,b in zip(path[:-1],path[1:])]
        xs=sorted(set([-.201+i*.402/80 for i in range(81)]+[p[0]+d for route in routes for p in route for d in [-.0015,-.0008,.0008,.0015]]))
        ys=sorted(set([-.014+i*.028/12 for i in range(13)]+[p[1]+d for route in routes for p in route for d in [-.0015,-.0008,.0008,.0015]]))
        distance=lambda x,y:min(segment_distance(x,y,a,b) for a,b in segments)
        grid=[[mesh.vertex((cx+x,cy+y,.066-.0007*(1-ease(.0008,.0015,distance(x,y))))) for x in xs] for y in ys]
        for j in range(len(ys)-1):
            for i in range(len(xs)-1):
                d=distance((xs[i]+xs[i+1])/2,(ys[j]+ys[j+1])/2)
                mesh.face([grid[j][i],grid[j][i+1],grid[j+1][i+1],grid[j+1][i]],ETCH if d<.0013 else DARK)
        edge=grid[0][:]+[row[-1] for row in grid[1:]]+list(reversed(grid[-1][:-1]))+[row[0] for row in reversed(grid[1:-1])]
        pa=[math.atan2(mesh.v[idx][1]-cy,mesh.v[idx][0]-cx)%TAU for idx in previous]
        ea=[math.atan2(mesh.v[idx][1]-cy,mesh.v[idx][0]-cx)%TAU for idx in edge]
        bridge_parameter(mesh,previous,pa,edge,ea,DARK)
    elif kind=='readout':
        # Machined rectangular flange transitions into a circular instrument well.
        for j,(sx,sy,z,mat) in enumerate([(.232,.232,.071,SILVER),(.222,.222,.087,EDGE),
                                         (.211,.211,.088,EDGE),(.204,.204,.078,DARK),(.198,.198,.077,DARK)]):
            current=mesh.ring([(cx+sx*u,cy+sy*v,z) for u,v in rounded])
            if j==0:bridge_parameter(mesh,previous,angles,current,[math.atan2(mesh.v[idx][1]-cy,mesh.v[idx][0]-cx)%TAU for idx in current],mat)
            else:mesh.bridge(previous,current,mat)
            previous=current
        profile=[(.194,.079,EDGE),(.188,.086,EDGE),(.181,.086,DARK),(.176,.079,DARK),
                 (.170,.078,ETCH),(.164,.078,DARK),(.158,.081,EDGE),(.153,.081,EDGE),
                 (DIAL_ARC[1],.068,DARK),(DIAL_ARC[0],.067,DARK),(.137,.067,DARK),(DIAL_RADIUS,.067,DARK)]
        for j,(r,z,mat) in enumerate(profile):
            current=mesh.ring([(cx+r*math.cos(t),cy+r*math.sin(t),z) for t in theta])
            if j==4:
                ring_material(mesh,previous,current,lambda k:ETCH if k%8<1 else DARK)
            elif j==9:
                mesh.bridge(previous,current,LIVE)
            else:mesh.bridge(previous,current,mat)
            previous=current
        # The shader draws the live scale and index on this continuous flat optical surface.
        for j,r in enumerate([.120,.105,.090,.070,.050,.030,.012]):
            current=mesh.ring([(cx+r*math.cos(t),cy+r*math.sin(t),.067) for t in theta])
            mesh.bridge(previous,current,LIVE);previous=current
        mesh.cap(previous,(cx,cy,.069),EDGE)
    elif kind=='rotary':
        # A seated dial with knurled edge and a recessed face index.
        for j,(r,z,mat) in enumerate([(.102,.071,SILVER),(.096,.078,EDGE),(.088,.078,DARK),
                                    (.082,.071,DARK),(.078,.074,ETCH),(.072,.075,DARK),
                                    (.068,.084,SILVER),(.067,.110,EDGE),(.062,.116,EDGE),
                                    (.053,.116,DARK),(.048,.112,SILVER),(.037,.113,PAD),(.017,.114,PAD)]):
            points=[]
            for k,t in enumerate(theta):
                radius=r+(.0018*(.5+.5*math.cos(t*32)) if j in [6,7] else 0)
                points.append((cx+radius*math.cos(t),cy+radius*math.sin(t),z))
            current=mesh.ring(points)
            if j==0:bridge_parameter(mesh,previous,angles,current,theta,mat)
            elif j==4:ring_material(mesh,previous,current,lambda k:ETCH if k%12<2 else DARK)
            elif j in [10,11]:ring_material(mesh,previous,current,lambda k:ETCH if k in range(45,49) else mat)
            else:mesh.bridge(previous,current,mat)
            previous=current
        mesh.cap(previous,(cx,cy,.115),PAD)
    elif kind=='fastener':
        limit=min(math.hypot(mesh.v[idx][0]-cx,mesh.v[idx][1]-cy) for idx in boundary)
        radius=min(.018,limit*.84)
        for j,(scale,z,mat) in enumerate([(1,.070,SILVER),(.94,.069,DARK),(.82,.064,DARK),
                                         (.70,.064,SILVER),(.68,.068,SILVER),(.56,.069,ETCH),(.33,.069,SILVER),(.08,.069,SILVER)]):
            current=mesh.ring([(cx+radius*scale*math.cos(t),cy+radius*scale*math.sin(t),
                                z-(.002 if j>=5 and abs(radius*scale*math.sin(t))<.0013 else 0)) for t in theta])
            if j==0:bridge_parameter(mesh,previous,angles,current,theta,mat)
            elif j>=5:ring_material(mesh,previous,current,lambda k:DARK if abs(radius*scale*math.sin(theta[k]))<.0013 else mat)
            else:mesh.bridge(previous,current,mat)
            previous=current
        mesh.cap(previous,(cx,cy,.067),DARK)
    else:
        # A hand-sized tactile membrane, gasket, and a shallow palm depression with five formed finger tracks.
        for j,(sx,sy,z,mat) in enumerate([(.229,.209,.071,SILVER),(.221,.201,.081,EDGE),
                                         (.211,.191,.081,EDGE),(.203,.183,.072,DARK),(.197,.177,.071,PAD)]):
            current=mesh.ring([(cx+sx*u,cy+sy*v,z) for u,v in rounded])
            if j==0:bridge_parameter(mesh,previous,angles,current,theta,mat)
            else:mesh.bridge(previous,current,mat)
            previous=current
        for j in range(1,25):
            rho=1-j/25;points=[]
            for u,v in rounded:
                u*=rho;v*=rho
                palm=.013*math.exp(-((u/.72)**4+((v-.15)/.60)**4))
                track=min(abs(u-p) for p in [-.6,-.3,0,.3,.6])
                fingers=.0045*math.exp(-(track/.065)**4)*(1-ease(-.05,.25,v))*ease(-.95,-.7,v)
                points.append((cx+.197*u,cy+.177*v,.071-palm-fingers))
            current=mesh.ring(points);mesh.bridge(previous,current,PAD);previous=current
        mesh.cap(previous,(cx,cy,.058),PAD)

def build_console(Surface,mats,side,station_height):
    mesh=Surface(mats);cx=side*.82;cy=-1.05;w=.29;length=.81
    # Patch bounds are in console coordinates; every hole reuses the actual deck edges.
    slots=[(-.243,-.015,-.716,-.464,'rotary'),(.015,.243,-.716,-.464,'rotary'),
           (-.243,.243,-.424,.044,'palm'),(-.243,.243,.146,.654,'readout'),(-.22,.22,.072,.122,'legend')]
    slots += [(x-.021,x+.021,y-.021,y+.021,'fastener') for x in [-.252,.252] for y in [-.755,.710]]
    xs=sorted(set([-w+i*(2*w)/36 for i in range(37)]+[p for a,b,c,d,t in slots for p in [a,b]]))
    ys=sorted(set([-length+i*(2*length)/88 for i in range(89)]+[p for a,b,c,d,t in slots for p in [c,d]]))
    cells=[[] for _ in slots];grid=[]
    for y in ys:
        row=[]
        for x in xs:
            # Only the perimeter is rounded; patch coordinates stay on their shared plane.
            power=10;u=x/w;v=y/length;d=(abs(u)**power+abs(v)**power)**(1/power)
            scale=max(abs(u),abs(v))/max(d,1e-12)
            blend=ease(.88,1,max(abs(u),abs(v)));xx=x*(1-blend+blend*scale);yy=y*(1-blend+blend*scale)
            z=.070
            row.append(mesh.vertex((cx+xx,cy+yy,z)))
        grid.append(row)
    for j in range(len(ys)-1):
        for i in range(len(xs)-1):
            x=(xs[i]+xs[i+1])/2;y=(ys[j]+ys[j+1])/2
            quad=[grid[j][i],grid[j][i+1],grid[j+1][i+1],grid[j+1][i]]
            slot=next((s for s,(a,b,c,d,t) in enumerate(slots) if a<x<b and c<y<d),None)
            if slot is not None:cells[slot].append(quad);continue
            mesh.face(quad,SILVER)
    for parts,(a,b,c,d,kind) in zip(cells,slots):
        centre=(cx+(a+b)/2,cy+(c+d)/2)
        if kind=='fastener':
            points=[mesh.v[idx] for part in parts for idx in part]
            centre=tuple((min(p[k] for p in points)+max(p[k] for p in points))/2 for k in [0,1])
        boundary,angles=patch_boundary(parts,mesh,*centre)
        instrument(mesh,boundary,angles,*centre,kind,side)
    boundary=grid[0][:]+[row[-1] for row in grid[1:]]+list(reversed(grid[-1][:-1]))+[row[0] for row in reversed(grid[1:-1])]
    params=[(mesh.v[idx][0]-cx,mesh.v[idx][1]-cy) for idx in boundary];previous=boundary
    for sx,sy,z,mat in [(1.009,1.004,.057,EDGE),(1.014,1.006,.040,EDGE),(1.014,1.006,.030,DARK),
                        (1.005,1.003,.025,DARK),(1.010,1.005,.018,EDGE),(.995,1,-.040,SILVER),
                        (.980,.995,-.048,DARK),(.975,.991,-.055,DARK),(.965,.985,-.062,EDGE),
                        (.91,.955,-.108,SILVER)]:
        current=mesh.ring([(cx+x*sx,cy+y*sy,z) for x,y in params]);mesh.bridge(previous,current,mat);previous=current
    current=mesh.ring([(cx+x/w*.095,cy+y/length*.27,-.16) for x,y in params]);mesh.bridge(previous,current,SILVER)
    mesh.cap(current,(cx,cy,-.16),DARK)
    errors=[abs(station_height(*mesh.v[idx][:2])+.16) for idx in current]
    assert max(errors)<.001
    obj=mesh.finish('Navigator | fitted console '+('L' if side>0 else 'R'))
    # Preserve a genuinely flat machined deck; nearby bevels must not bend its reflection normals.
    for face in obj.data.polygons:
        if all(abs(obj.data.vertices[idx].co.z-.070)<1e-6 for idx in face.vertices):face.use_smooth=False
    readout=next(s for s in slots if s[4]=='readout')
    dial_center=(cx+(readout[0]+readout[1])/2,cy+(readout[2]+readout[3])/2,.067)
    return obj,{'dial_count':3,'live_dial_center':dial_center,'live_dial_radius':DIAL_RADIUS,'live_arc_radii':DIAL_ARC,
                'tactile_wells':1,'engraved_legend_strips':1,'integrated_captive_seats':4,'maximum_landing_error_m':max(errors)}
