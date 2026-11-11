"""Terrain-constrained implementation of the approved braided archipelago plan."""
import math
import random
import numpy as np
from shapely.geometry import Point,Polygon,LineString,box
from shapely.ops import unary_union,nearest_points
from shapely.prepared import prep
from masterplan import proposal


def components(shape):
    if shape.is_empty:return []
    return list(shape.geoms) if hasattr(shape,'geoms') else [shape]


def organic(cx,cy,r,phase):
    return Polygon([(cx+r*(1+.13*math.sin(3*a+phase))*math.cos(a),
                     cy+r*.86*(1+.13*math.sin(3*a+phase))*math.sin(a)) for a in np.linspace(0,math.tau,65)[:-1]])


# Ground policy (docs/spec-ville-procedurale.md#earthworks). Every building, plaza, field terrace and
# transport footing stands on an earthwork pad graded into the planet's relief (grading.py): level at
# its median ground, cut and fill with banks of 1:2 at most. Paths drape over the graded ground, ramp
# up to 8 %, climb by steps beyond, and keep 10 m from water.
EARTHWORK_M=10.0                        # largest natural relief under one pad
PAD_MARGIN_M,PAD_ROUND_M=2.5,3.0        # level apron around a building (room for its planters and bench), rounded corners
STAIR_GRADE,MAX_GRADE,WATER_MARGIN_M=.08,.30,10.0
STAIR_RISE_M,STAIR_GOING_M,STAIR_WIDTH_M=.17,.29,1.6
GARDEN_M,OPEN_GARDEN=8.0,.75
# Field terraces: strips along the contours of food districts no steeper than 25 %, banks between them.
FIELD_W,FIELD_GAP,FIELD_LEN,FIELD_GRADE=8.0,4.0,24.0,.25
FIELD_DRAPED=.06                        # below this slope fields lie on the ground, without terraces
FARM_GRADE=.35                          # a farm's fields lie on its meadow up to this slope, as hillside fields do
# The spaceport: one earthwork platform for the terminal, two landing pads and their beacons.
PORT_HALF=(85.0,45.0)
# Cable car: spans of at most 150 m; cables clear the graded ground by 7 m between supports.
CABLE_SPAN,CABLE_CLEAR,CABIN_STEP=150.0,7.0,55.0
# On a face steeper than 1:2 a house or a pylon may span 14 m of relief: its bank, twice as steep as the face, keeps
# its earthworks within about half its depth.
STEEP_RELIEF_M=14.0
# Measured on the generated transport sources: the pylon's footing box (model metres), its sheaves
# at 0.84 of its half-width and 0.98 of its height, the station's bullwheel at 0.18 of its length
# across and half its height, the landing pad's deck at 0.485 of its height. Cabins hang by their top.
PYLON_BASE=((-6.6,-5.0),(3.4,5.0))
SHEAVE,BULLWHEEL,DECK=(.84,.98),(.18,.5),.485
# Earthworks stay local (grading.bank): they show at most REACH_M beyond a pad's edge. Buildings sit SEAT_M above
# their pad; furniture is set EMBED_M into the ground at its lowest corner, or stands on the paving it is on.
REACH_M,SEAT_M,EMBED_M=24.0,.01,.03
# The cliff's face: a stair path in switchbacks, legs across the slope at 25 %, turning back within 90 m of the axis
# from the foot's court to the top's; houses above its legs, one per 24 m of leg, up to 22.
FACE_GRADE,FACE_BAND,FACE_STEP_M,FACE_HOUSES=.25,(30.0,210.0),24.0,22
# The guideway beyond the city, towards other cities: level at the city's beam, on steel piers beside the line every
# 45 m, their arms over the beam. Its ground lies a ring's height below the beam on the site, PIER_CLEAR below beyond;
# no tree stands within CORRIDOR_M of the line (CityLand.hlsli).
PIER_STEP,PIER_SIDE,PIER_CLEAR,INTERCITY_M,CORRIDOR_M=45.0,6.5,42.0,9000.0,24.0


class Bins:
    """Shapes on a 32 m grid: whether a new shape touches any of them, without testing them all."""
    def __init__(self,cell=32.0):self.cell,self.bins,self.shapes=cell,{},[]
    def keys(self,shape):
        x0,y0,x1,y1=shape.bounds;c=self.cell
        return [(i,j) for i in range(int(x0//c),int(x1//c)+1) for j in range(int(y0//c),int(y1//c)+1)]
    def add(self,shape):
        self.shapes.append(shape)
        for key in self.keys(shape):self.bins.setdefault(key,[]).append(len(self.shapes)-1)
    def touching(self,shape):
        return [self.shapes[k] for k in {k for key in self.keys(shape) for k in self.bins.get(key,())} if self.shapes[k].intersects(shape)]
    def hits(self,shape):return bool(self.touching(shape))


def contour_spine(terrain,region=None):
    """A level line across a hill site for the guideway: the longest contour of the dry ground between its 35th and
    65th percentiles, kept 80 m inside the site (or a region of it) and smoothed over 160 m, whose ground stays
    within 12 m; None when no contour spans half the site."""
    import contourpy
    axis=(np.arange(terrain.side)-terrain.side//2)*terrain.cell;values=np.asarray(terrain.values,float)
    x0,y0,x1,y1=region or (-terrain.half,-terrain.half,terrain.half,terrain.half)
    inside=box(x0+80,y0+80,x1-80,y1-80);best=None
    within=np.ix_((axis>=y0)&(axis<=y1),(axis>=x0)&(axis<=x1))
    land=values[within][values[within]>terrain.water_level+2]
    if land.size==0:return None
    generator=contourpy.contour_generator(axis,axis,values)
    for q in (35,42,50,58,65):
        for piece in generator.lines(float(np.percentile(land,q))):
            if len(piece)<10:continue
            for part in components(LineString(piece).intersection(inside)):
                if part.geom_type!='LineString' or part.length<terrain.half:continue
                points=np.array([part.interpolate(d).coords[0] for d in np.arange(0,part.length,10)]);k=8
                padded=np.vstack([np.repeat(points[:1],k,0),points,np.repeat(points[-1:],k,0)])
                smooth=np.array([padded[i:i+2*k+1].mean(0) for i in range(len(points))])
                # A guideway runs one way: keep the longest stretch that never turns back on the line's main axis.
                axis_=np.linalg.svd(smooth-smooth.mean(0),full_matrices=False)[2][0];tangent=np.gradient(smooth,axis=0)
                ahead=tangent@axis_/np.maximum(np.linalg.norm(tangent,axis=1),1e-9);ahead*=np.sign(ahead.sum())
                runs=np.split(np.arange(len(smooth)),np.flatnonzero(np.diff((ahead>.3).astype(int)))+1)
                keep=max((r for r in runs if ahead[r[0]]>.3),key=len,default=None)
                if keep is None or len(keep)<10:continue
                smooth=smooth[keep];heights=np.array([terrain.sample(*p) for p in smooth])
                if np.ptp(heights)>12 or any(terrain.wet(*p,10) for p in smooth[::3]):continue
                score=LineString(smooth).length-30*np.ptp(heights)
                if best is None or score>best[0]:best=(score,smooth)
    return [[float(x),float(y)] for x,y in best[1][::2]] if best else None


def switchback(terrain,start,end,band=FACE_BAND,grade=FACE_GRADE,step=3.0):
    """A stair path from the court at start up to the court at end, climbing beside the line between them, so that
    line stays free for a cable car: legs across the slope at `grade`, turning back at the lateral offsets `band` (m)
    on the side of the line whose face is gentler. It leaves start and reaches end across that line, on the gentle
    ground of the foot and the top. None if it never arrives."""
    a=np.asarray(start,float);b=np.asarray(end,float);axis=(b-a)/np.linalg.norm(b-a);across=np.array([-axis[1],axis[0]])
    near,far=band;run=float(np.dot(b-a,axis))
    def gradient(p,e=6.0):
        return np.array([terrain.sample(p[0]+e,p[1])-terrain.sample(p[0]-e,p[1]),terrain.sample(p[0],p[1]+e)-terrain.sample(p[0],p[1]-e)])/(2*e)
    def mean_slope(sigma):
        return np.mean([np.linalg.norm(gradient(a+axis*run*f+across*sigma*u)) for f in np.linspace(.2,.8,7) for u in np.linspace(near,far,5)])
    sigma=min((1.0,-1.0),key=mean_slope)
    p=a+across*sigma*near;points=[a.copy(),p.copy()];going=1.0;goal=terrain.sample(*b)-3
    for _ in range(3000):
        if terrain.sample(*p)>=goal or np.dot(p-a,axis)>=run-8:break
        g=gradient(p);s=float(np.linalg.norm(g))
        if s<=grade*1.2:d=axis  # gentle ground: straight on, parallel to the line
        else:
            up=g/s;contour=np.array([-up[1],up[0]])
            if np.dot(contour,across*sigma)*going<0:contour=-contour
            t=grade/s;d=contour*math.sqrt(1-t*t)+up*t
        p=p+d*step;points.append(p.copy())
        u=float(np.dot(p-a,across))*sigma
        if (going>0 and u>far) or (going<0 and u<near):going=-going
    else:return None
    points+=[b+across*sigma*near,b.copy()]
    return [tuple(map(float,q)) for q in points]


def intercity(terrain,end,before,datum,beam,length=INTERCITY_M,step=10.0):
    """The guideway beyond the city's end, level at `beam`. Every 10 m it turns at most 1.2 degrees: the turn rate whose
    next 120 m keep the ground nearest its target, a ring's height below the beam (the datum) on the site, PIER_CLEAR
    below beyond it, and never within 12 m of the beam. It ends at the regional export's edge, or where no turn keeps
    that clearance."""
    p=np.asarray(end,float);heading=math.atan2(p[1]-before[1],p[0]-before[0]);points=[p.copy()]
    region=getattr(terrain,'region',None);limit=(region.half if region else terrain.half)-120
    def target(q):
        t=min(1.0,max(0.0,(max(abs(q[0]),abs(q[1]))-(terrain.half-200))/400));return datum*(1-t)+(beam-PIER_CLEAR)*t
    for _ in range(int(length/step)):
        best=None
        for rate in np.radians(np.linspace(-1.2,1.2,13)):
            q=p.copy();h=heading;cost=0.0;first=None
            for k in range(12):
                h+=rate;q=q+step*np.array([math.cos(h),math.sin(h)]);g=terrain.height(*q)
                if g is None or g<2:cost+=1e4;break
                aim=target(q);cost+=(g-aim if g>aim else .3*(aim-g))+(1e3 if g>beam-12 else 0)
                if first is None:first=(heading+rate,q.copy(),g)
            cost+=.05*abs(math.degrees(rate))
            if first and (best is None or cost<best[0]):best=(cost,*first)
        if best is None or best[3]>beam-12:break
        heading,p=best[1],best[2];points.append(p.copy())
        if max(abs(p[0]),abs(p[1]))>limit:break
    # A moving average over 100 m smooths the discrete turns; the line still starts at the city's end.
    pts=np.array(points);k=5
    if len(pts)>2*k+2:
        padded=np.vstack([np.repeat(pts[:1],k,0),pts,np.repeat(pts[-1:],k,0)])
        pts=np.array([padded[i:i+2*k+1].mean(0) for i in range(len(pts))]);pts[0]=points[0]
    return [tuple(map(float,q)) for q in pts]


def supports_materials(slots):
    """Paving, masonry and cable steel for the built supports that remain: steps and cables.
    A fully generated kit may carry no procedural stone: fall back on the cooker's ground materials."""
    wall=slots.get('masonry',slots.get('stone',slots['path_border']))
    return {'top':slots['common_paving'],'wall':wall,'cable':slots.get('satin_metal',wall),'pier':slots.get('satin_metal',wall)}


def compose(terrain,library,seed):
    from layout import footprint,support,PATH_LIFT,CURB_M
    from grading import Grading,pad as earthwork,polygon as pad_shape,allowance,bank,talus_of,TALUS,TALUS_MAX,KNEE,ROUND
    rng=random.Random(seed);spec=proposal(seed)
    if terrain.half<510:raise ValueError('Expanded city needs a terrain export at least 1024 m wide')
    # Earthworks grade the relief as the plan goes: every composition starts from the natural ground.
    if getattr(terrain,'graded',None) is terrain.values:terrain.values=terrain.natural
    terrain.natural=terrain.values
    grade=Grading(terrain);terrain.values=terrain.graded=grade.values
    def dig(p):
        """Grade a pad in: its bank steepens, up to TALUS_MAX, until it meets the ground within REACH_M, so it never
        runs along a slope, nor along a neighbour's bank, as steep as itself."""
        for talus in sorted({talus_of(p),*[t for t in (1.0,1.5,TALUS_MAX) if t>talus_of(p)]}):
            q=earthwork(p[0],p[1],math.atan2(p[3],p[2]),p[4],p[5],p[7],p[6],talus)
            if grade.local(q)[0]<=REACH_M:break
        return grade.add(q)
    def seated(shape):
        """The lowest and highest graded ground under a small footprint, every metre and at its corners, exactly as
        the engine grades it: the grid's bilinear values smooth a steep bank's crest and toe."""
        x0,y0,x1,y1=shape.bounds;prepared_=prep(shape)
        points=[(qx,qy) for qx in np.linspace(x0,x1,max(2,math.ceil(x1-x0)+1)) for qy in np.linspace(y0,y1,max(2,math.ceil(y1-y0)+1))
                if prepared_.covers(Point(qx,qy))]+list(shape.exterior.coords)
        heights=[grade.exact(qx,qy) for qx,qy in points];return min(heights),max(heights)
    # The guideway stands on fixed 27 m rings: it needs level, dry ground along its whole line. A hill site, or one
    # wider than the 1 km braid, lays its braid along a contour instead: the mobility spine stays level.
    rail_heights=[terrain.sample(x,y) for x,y in spec['rail']]
    region=terrain.meta.get('spine_region')
    if terrain.half>520 or max(rail_heights)-min(rail_heights)>12:
        spine=contour_spine(terrain,region)
        # The same ground rule as the district filter below; fields need 25 % at most, the spaceport gentle ground.
        def fits(x,y,radius,role):
            if max(abs(x),abs(y))>terrain.half-radius or terrain.wet(x,y,WATER_MARGIN_M+radius*.25):return False
            return terrain.slope(x,y,radius*.5)<={'arrival':.12,'food':FIELD_GRADE}.get(role,MAX_GRADE)
        if spine:spec=proposal(seed,extent=2*terrain.half,spine=spine,fits=fits,region=region);rail_heights=[terrain.sample(x,y) for x,y in spec['rail']]
    # Places the site states beside its export (the user's choice): farms in a meadow, dwellings at a cliff's foot
    # and on its top, the top served by the cable car.
    stated=random.Random(seed+3)
    for place in terrain.meta.get('farmland',[]):
        spec['districts'].append({'centre':place['centre'],'role':'farm','density':.2,'radius':place['radius'],
                                  'label':place.get('label','Exploitations'),'seed':stated.randrange(1,1000000)})
    cliff=terrain.meta.get('cliff')
    if cliff:
        foot,top=np.array(cliff['foot'],float),np.array(cliff['top'],float);valley=(foot-top)/np.linalg.norm(foot-top)
        # The foot district stands a little off the face, so its ring of towers reaches the cliff's base.
        spec['districts'].append({'centre':[float(v) for v in foot+valley*45],'role':'cliff_foot','density':1,'radius':66,
                                  'label':cliff.get('label','Falaise')+', pied','seed':stated.randrange(1,1000000)})
        spec['districts'].append({'centre':[float(v) for v in top-valley*70],'role':'cliff_top','density':.6,'radius':70,
                                  'label':cliff.get('label','Falaise')+', sommet','seed':stated.randrange(1,1000000)})
    elevated=max(rail_heights)-min(rail_heights)<=12 and not any(terrain.wet(x,y,WATER_MARGIN_M) for x,y in spec['rail'])
    if not elevated:spec['stations']=[]
    # A shared court needs dry ground and a slope it can stand on.
    spec['districts']=districts=[d for d in spec['districts'] if not terrain.wet(*d['centre'],WATER_MARGIN_M+d['radius']*.25)
                                 and terrain.slope(*d['centre'],d['radius']*.5)<=MAX_GRADE]
    if len(districts)<3:raise ValueError('Unsupported site: too few districts on dry, moderate ground')
    hubs=[d['centre'] for d in districts]+spec['stations']
    lookup={m['id']:i for i,m in enumerate(library['models'])}
    models=library['models']
    rail=LineString(spec['rail']);corridors=unary_union([LineString(line).buffer(spec['corridor_half_width_m']) for line in spec['habitat_corridors']])
    def along(s):
        """A point of the guideway's line at arc length s, and its heading."""
        a=rail.interpolate(max(0,s-1));b=rail.interpolate(min(rail.length,s+1));p=rail.interpolate(s)
        return p.x,p.y,math.atan2(b.y-a.y,b.x-a.x)
    def passable(points):
        """Dry, and no steeper than stairs, between consecutive samples about 3 m apart."""
        heights=[terrain.sample(*p) for p in points]
        if any(h<2 or terrain.wet(*p,6) for h,p in zip(heights,points)):return False
        return all(abs(b-a)/max(.01,math.dist(p,q))<=MAX_GRADE for a,b,p,q in zip(heights,heights[1:],points,points[1:]))
    def straight(a,b):
        n=max(2,int(math.dist(hubs[a],hubs[b])/3));return [tuple(np.array(hubs[a])+(np.array(hubs[b])-np.array(hubs[a]))*t) for t in np.linspace(0,1,n)]
    link={}
    def linkable(a,b):
        key=(min(a,b),max(a,b))
        if key not in link:link[key]=passable(straight(a,b))
        return link[key]
    # A sparse nearest-neighbour tree over passable links and a few redundant foot connections.
    by_cable={k for k,d in enumerate(districts) if d['role']=='cliff_top'}
    reached={0};edges=[]
    while len(reached)<len(hubs):
        options=[(math.dist(hubs[a],hubs[b]),a,b) for a in sorted(reached) for b in range(len(hubs)) if b not in reached and linkable(a,b)]
        if not options:
            if set(range(len(hubs)))-reached<=by_cable:break
            raise ValueError('Unsupported site: districts cannot be linked on foot')
        _,a,b=min(options);edges.append((a,b));reached.add(b)
    # A district reached by cable alone keeps its own paths: four spokes from its court where the ground allows.
    for k in sorted(set(range(len(hubs)))-reached):
        for angle in np.arange(4)*math.pi/2+.4:
            end=(hubs[k][0]+55*math.cos(angle),hubs[k][1]+55*math.sin(angle))
            spoke=[tuple(np.array(hubs[k])+(np.array(end)-np.array(hubs[k]))*t) for t in np.linspace(0,1,19)]
            if passable(spoke):edges.append((k,k,spoke))
    for i in range(len(hubs)):
        if i not in reached:continue
        others=[j for j in range(len(hubs)) if i!=j and j in reached and (i,j) not in edges and (j,i) not in edges and linkable(i,j)]
        if not others:continue
        j=min(others,key=lambda j:math.dist(hubs[i],hubs[j]))
        if math.dist(hubs[i],hubs[j])<190 and i%3==0:edges.append((i,j))
    # The cliff's face: a stair path in switchbacks from the foot's court up to the top's.
    feet_=[k for k,d in enumerate(districts) if d['role']=='cliff_foot'];tops_=[k for k,d in enumerate(districts) if d['role']=='cliff_top']
    face_path=switchback(terrain,hubs[feet_[0]],hubs[tops_[0]]) if feet_ and tops_ else None
    if face_path:edges.append((feet_[0],tops_[0],face_path))
    roads=[]
    for edge in edges:
        if len(edge)==3:roads.append(LineString(edge[2]));continue
        a,b=edge
        p=np.array(hubs[a]);q=np.array(hubs[b]);delta=q-p;normal=np.array([-delta[1],delta[0]])/np.linalg.norm(delta)
        control=(p+q)/2+normal*rng.uniform(-18,18)
        line=LineString([(1-t)**2*p+2*(1-t)*t*control+t*t*q for t in np.linspace(0,1,33)])
        # A curve that bends into water or onto a cliff falls back to the passable chord.
        samples=[(line.interpolate(d).x,line.interpolate(d).y) for d in np.arange(0,line.length,3)]+[tuple(q)]
        roads.append(line if passable(samples) else LineString(straight(a,b)))
    network=unary_union(roads);clearance=network.buffer(2.05)
    station_z=max(rail_heights)+23.4;datum=station_z-23
    def ground(shape,step=3.0):
        """Ground samples covered by a shape."""
        x0,y0,x1,y1=shape.bounds;prepared_shape=prep(shape)
        out=[terrain.sample(x,y) for y in np.arange(y0,y1+step,step) for x in np.arange(x0,x1+step,step) if prepared_shape.contains(Point(x,y))]
        return out or [terrain.sample(*shape.centroid.coords[0])]
    def settle(p,heights,cap=EARTHWORK_M/2):
        """The pad at its median ground, dry, and within the levels its graded neighbours allow; its bank twice as
        steep as the ground under it, so its earthworks stay local. None when its neighbours would hold it more than
        `cap` from its own ground, or when its earthworks would show more than REACH_M beyond its edge."""
        median=max(float(np.median(heights)),terrain.water_level+1)
        least=bank(terrain.slope(p[0],p[1],max(p[4],p[5])))
        # Where a close neighbour stands at another level, the bank steepens as a terrace's would, up to TALUS_MAX.
        for talus in sorted({least,*[t for t in (1.0,1.5,TALUS_MAX) if t>least]}):
            lo,hi=grade.bounds(earthwork(p[0],p[1],math.atan2(p[3],p[2]),p[4],p[5],median,p[6],talus),cap)
            h=min(max(median,lo),hi)
            if lo<=hi and abs(h-median)<=cap:break
        else:return None
        q=earthwork(p[0],p[1],math.atan2(p[3],p[2]),p[4],p[5],h,p[6],talus)
        return q if grade.local(q)[0]<=REACH_M else None
    radii=[(12 if districts[i]['density']>.6 else 9) if i<len(districts) else 18 for i in range(len(hubs))]
    commons=[organic(x,y,radii[i],i*.8) for i,(x,y) in enumerate(hubs)]
    # A planted off-centre island keeps each district's pedestrian surface porous.
    gardens=[organic(x+3.3,y+2.8,radii[i]*.43,i*.5) for i,(x,y) in enumerate(hubs[:len(districts)])]
    placed=[];lots=[];paths=[];walks=[];props=[];rejected=[];accesses=[]
    lot_bins,path_bins,prop_bins=Bins(),Bins(),Bins()
    # The guideway's footings come first, at its fixed datum: stations, then a small embanked
    # footing under every ring. Everything graded later keeps clear of their level.
    station_shapes=[];rings=[]
    if elevated:
        for i,(x,y) in enumerate(spec['stations']):
            name='interlaced_station' if i%2 else 'garden_station';yaw=along(rail.project(Point(x,y)))[2];model=models[lookup[name]]
            station_shapes.append(footprint(model,x,y,yaw,1));lo,hi=model['bounds_z_up']
            dig(earthwork(x,y,yaw,(hi[0]-lo[0])/2+PAD_MARGIN_M,(hi[1]-lo[1])/2+PAD_MARGIN_M,datum+lo[2]-SEAT_M,PAD_ROUND_M,
                                bank(terrain.slope(x,y,(hi[0]-lo[0])/2))))
            placed.append({'id':name,'model':lookup[name],'position':[x,y,datum],'yaw':yaw,'tint':1,
                           'zone':'transport','station':i,'guideway_datum':station_z,'foundation':'earthwork'})
        lo=models[lookup['viaduct_ring']]['bounds_z_up'][0];stops=[rail.project(Point(*q)) for q in spec['stations']]
        for s in np.arange(23,rail.length-10,54):
            if min(abs(s-t) for t in stops)<28:continue
            xx,yy,yaw=along(float(s));rings.append((xx,yy,yaw))
            dig(earthwork(xx,yy,yaw,3.4,6.1,datum+lo[2]-SEAT_M,2.5,bank(terrain.slope(xx,yy,6.1))))
    # Beyond the city the guideway goes on towards other cities, from both ends, on its piers; a station where it
    # passes the farms. A branch never runs back along the city's own line.
    branches=[];farm_station=None
    if elevated and getattr(terrain,'region',None) is not None:
        coords=list(rail.coords)
        for end,before in ((coords[-1],coords[-2]),(coords[0],coords[1])):
            line_=intercity(terrain,end,before,datum,station_z);keep=[line_[0]]
            for q in line_[1:]:
                g=terrain.height(*q)
                if g is None or g>station_z-10 or (len(keep)>3 and LineString([keep[-1],q]).distance(rail)<30):break
                keep.append(q)
            if len(keep)>10:branches.append(keep)
        farms=[k for k,d in enumerate(districts) if d['role']=='farm'];best=None
        for b in branches if farms and 'garden_station' in lookup else []:
            line_=LineString(b);fx,fy=districts[farms[0]]['centre'];s_=line_.project(Point(fx,fy));q=line_.interpolate(s_)
            if 60<s_<line_.length-60 and max(abs(q.x),abs(q.y))<terrain.half-80 and q.distance(Point(fx,fy))<600:
                if best is None or q.distance(Point(fx,fy))<best[0]:best=(q.distance(Point(fx,fy)),line_,s_)
        if best:
            _,line_,s_=best;q=line_.interpolate(s_);a_=line_.interpolate(s_-1);b_=line_.interpolate(s_+1)
            yaw=math.atan2(b_.y-a_.y,b_.x-a_.x);model=models[lookup['garden_station']];lo,hi=model['bounds_z_up']
            if abs(terrain.sample(q.x,q.y)-datum)<8:
                station_shapes.append(footprint(model,q.x,q.y,yaw,1))
                dig(earthwork(q.x,q.y,yaw,(hi[0]-lo[0])/2+PAD_MARGIN_M,(hi[1]-lo[1])/2+PAD_MARGIN_M,datum+lo[2]-SEAT_M,PAD_ROUND_M,
                                    bank(terrain.slope(q.x,q.y,(hi[0]-lo[0])/2))))
                placed.append({'id':'garden_station','model':lookup['garden_station'],'position':[q.x,q.y,datum],'yaw':yaw,'tint':1,
                               'zone':'transport','station':len(spec['stations']),'guideway_datum':station_z,'foundation':'earthwork',
                               'serves':'farm'})
                farm_station=(q.x,q.y,farms[0])
    # The spaceport: the platform around the arrival court that moves the least earth, with its
    # terminal at one end and two landing pads toward the other, clear of every path.
    port=None;port_plan=None;port_index=None
    arrival=[i for i,d in enumerate(districts) if d['role']=='arrival']
    if arrival and 'landing_pad' in lookup and 'space_terminal' in lookup:
        i=arrival[0];cx,cy=hubs[i];terminal=models[lookup['space_terminal']];landing=models[lookup['landing_pad']]
        tlo,thi=terminal['bounds_z_up'];llo,lhi=landing['bounds_z_up'];span=lhi[0]-llo[0]
        keep_clear=prep(unary_union([clearance,commons[i].buffer(1)]))
        def plan_port(p,sign):
            pcx,pcy,c,s,a=p[:5];u=np.array([c,s])*sign;v=np.array([-s,c])
            at=lambda du,dv:(pcx+u[0]*du+v[0]*dv,pcy+u[1]*du+v[1]*dv)
            heading=math.atan2(u[1],u[0])
            # The terminal's depth runs along the platform, its entrance toward the pads.
            hall=(*at(-a+(thi[1]-tlo[1])/2+3,0),heading+math.pi/2)
            landings=[(*at(a-span*(k+.5)-6-8*k,0),heading) for k in range(2)]
            shapes=[footprint(terminal,*hall,.8)]+[footprint(landing,*q,.4) for q in landings]
            flat=pad_shape(p).buffer(-1)
            if any(not flat.contains(shape) or keep_clear.intersects(shape) for shape in shapes):return None
            return {'terminal':hall,'landings':landings,'heading':heading,'at':at,'shapes':shapes}
        best=None
        for dx in np.arange(-60,61,10):
            for dy in np.arange(-60,61,10):
                for turn in np.radians(np.arange(0,180,15)):
                    candidate=earthwork(cx+dx,cy+dy,turn,*PORT_HALF,0,10);shape=pad_shape(candidate)
                    if not shape.buffer(-12).contains(Point(cx,cy)) or shape.intersects(corridors):continue
                    if max(map(abs,shape.bounds))>terrain.half-10 or (elevated and shape.intersects(rail.buffer(20))):continue
                    if any(shape.intersects(LineString(b).buffer(20)) for b in branches):continue
                    if any(shape.intersects(Point(*h).buffer(20)) for k,h in enumerate(hubs) if k!=i):continue
                    plan=plan_port(candidate,1) or plan_port(candidate,-1)
                    if plan is None:continue
                    x0,y0,x1,y1=shape.bounds
                    if any(terrain.wet(qx,qy,WATER_MARGIN_M) for qx in np.linspace(x0,x1,7) for qy in np.linspace(y0,y1,7) if shape.contains(Point(qx,qy))):continue
                    heights=np.array(ground(shape,6.0))
                    if np.ptp(heights)>2*EARTHWORK_M:continue
                    depth=float(np.mean(np.abs(heights-np.median(heights))))
                    if best is None or depth<best[0]:best=(depth,candidate,heights,plan)
        if best:
            port=settle(best[1],best[2])
            if port:port_index=dig(port);port_plan=best[3]
    # Plazas: one level court per district at the median ground under its common.
    for i,(x,y) in enumerate(hubs[:len(districts)]):
        if port and pad_shape(port).contains(Point(x,y)):continue
        r=radii[i];court=settle(earthwork(x,y,0,r+1,r+1,0,r*.9),ground(Point(x,y).buffer(r),2.0))
        if court:dig(court)
    common_area=unary_union(commons);garden_area=unary_union(gardens);plaza=common_area.buffer(1)
    # Circulation keeps every footing off paths, commons and the transport lines; buildings also keep
    # out of the nature corridors, which a cable car's pylon footings may cross.
    circulation=unary_union([clearance,common_area.buffer(.6),*([rail.buffer(13)] if elevated else []),
                             *[LineString(b).buffer(13) for b in branches],*([pad_shape(port).buffer(4)] if port else []),*station_shapes])
    reserve=unary_union([circulation,corridors])
    def tread(a,b,width,top):
        """One solid step from a to b, `width` wide, its top at `top`."""
        a=np.asarray(a,float);b=np.asarray(b,float);n=np.array([a[1]-b[1],b[0]-a[0]]);n*=width/2/max(1e-9,float(np.linalg.norm(n)))
        return (Polygon([a-n,b-n,b+n,a+n]),top,'stair',None)
    def across(p,d,half):
        """The highest graded ground across a run at p, `half` metres each side of its direction d."""
        n=np.array([-d[1],d[0]]);return max(terrain.sample(*(p+n*t)) for t in np.linspace(-half,half,5))
    def climb(a,b,width):
        """Steps for one sampled run steeper than a ramp, level across: each step's top at its upper edge stands
        at the path's level, the highest ground across plus the path's lift (layout.PATH_LIFT)."""
        a=np.asarray(a,float);b=np.asarray(b,float);d=(b-a)/max(1e-9,float(np.linalg.norm(b-a)))
        ha=across(a,d,width/2);hb=across(b,d,width/2);grade_=abs(hb-ha)/max(.01,math.dist(a,b))
        if grade_<=STAIR_GRADE:return []
        if hb<ha:a,b,ha,hb=b,a,hb,ha
        count=max(1,round((hb-ha)/STAIR_RISE_M))
        return [tread(a+(b-a)*k/count,a+(b-a)*(k+1)/count,width,ha+(hb-ha)*(k+1)/count+PATH_LIFT) for k in range(count)]
    pathpieces=[];grass_links=[];stairs=[]
    for i,line in enumerate(roads):
        a,b=edges[i][:2];dense=a>=len(districts) or b>=len(districts) or min(districts[a]['density'],districts[b]['density'])>.6
        if not dense and i%3==1 and len(edges[i])==2:
            grass_links.append(i)
            for start,end in [(0,.32),(.68,1)]:pathpieces.append(LineString([line.interpolate(t,normalized=True) for t in np.linspace(start,end,14)]).buffer(1.1,quad_segs=5))
        else:pathpieces.append(line.buffer(1.45 if dense else 1.15,quad_segs=5))
        for distance in np.arange(0,line.length,3):
            p=line.interpolate(distance);q=line.interpolate(min(distance+3,line.length))
            if min(terrain.sample(p.x,p.y),terrain.sample(q.x,q.y))<2 or terrain.wet(p.x,p.y,6):raise ValueError('Pedestrian network crosses the water margin')
    def entrance_of(model,x,y,yaw):
        lo,hi=model['bounds_z_up'];entry=model.get('entrance_z_up',[0,lo[1],0])
        return Point(x+entry[0]*math.cos(yaw)-entry[1]*math.sin(yaw),y+entry[0]*math.sin(yaw)+entry[1]*math.cos(yaw))
    def site(model,x,y,yaw,accessible=True,keep=None,relief=EARTHWORK_M,steepest=None):
        """Lot, earthwork pad and access for one orientation, or the reason it fails."""
        lot=footprint(model,x,y,yaw,.8)
        if max(map(abs,lot.bounds))>terrain.half-5:return 'terrain boundary'
        if lot.intersects(reserve if keep is None else keep):return 'reserved nature, common or circulation'
        if lot_bins.hits(lot):return 'inhabited footprint clearance'
        if path_bins.hits(lot):return 'existing shared access'
        x0,y0,x1,y1=lot.bounds
        if any(terrain.wet(px,py,WATER_MARGIN_M) for px in np.linspace(x0,x1,4) for py in np.linspace(y0,y1,4)):return 'water margin'
        low,high=support(terrain,lot)
        if high-low>relief:return 'unsupported footing'
        lo,hi=model['bounds_z_up'];mx,my=(lo[0]+hi[0])/2,(lo[1]+hi[1])/2
        heights=ground(lot)
        p=settle(earthwork(x+mx*math.cos(yaw)-my*math.sin(yaw),y+mx*math.sin(yaw)+my*math.cos(yaw),yaw,
                           (hi[0]-lo[0])/2+PAD_MARGIN_M,(hi[1]-lo[1])/2+PAD_MARGIN_M,0,PAD_ROUND_M),heights)
        if p is None:return 'earthworks clash'
        entrance=entrance_of(model,x,y,yaw);line=None;path=None
        if accessible:
            destination=nearest_points(entrance,network)[1];line=LineString([entrance,destination])
            if line.length>105:return 'access too long'
            path=line.buffer(1.05,quad_segs=5)
            if lot_bins.hits(path):return 'access crosses a footprint'
            if steepest and abs(p[7]-terrain.sample(destination.x,destination.y))>steepest*max(line.length,.5):return 'access too steep'
        return {'lot':lot,'path':path,'line':line,'pad':p,'top':p[7],'low':low,'high':high,'entrance':entrance,
                'access':line.length if line else 0,'score':float(np.mean(np.abs(np.asarray(heights)-p[7])))}
    def commit(name,model,x,y,yaw,best,zone,hub,extra=None):
        k=dig(best['pad'])
        # Architectural sources use z=0 as their ground datum: the pad's level.
        placed.append({'model':lookup[name],'id':name,'position':[x,y,best['top']+SEAT_M],'yaw':yaw,'tint':rng.uniform(.96,1.04),
                       'zone':zone,'shared_court':hub,'density':districts[hub]['density'] if hub is not None else 1,
                       'support_min':best['low'],'support_max':best['high'],'foundation':'earthwork','pad':k,
                       'entrance':[best['entrance'].x,best['entrance'].y],'access_length':best['access'],
                       'floors':model.get('floors',1),**(extra or {})})
        lots.append(best['lot']);lot_bins.add(best['lot'])
        if best['path'] is not None:
            paths.append(best['path']);path_bins.add(best['path']);walks.append(best['path']);accesses.append(best['line'])
    def add(name,x,y,yaw,zone,hub,relief=EARTHWORK_M,turns=range(4),steepest=None):
        model=models[lookup[name]];options=[];reason='no orientation'
        # The lot turned a quarter at a time: the least earthwork wins; facing the shared court breaks ties.
        for turn in turns:
            option=site(model,x,y,yaw+turn*math.pi/2,relief=relief,steepest=steepest)
            if isinstance(option,str):reason=option
            else:options.append((option['score']+.3*min(turn,4-turn),turn,option))
        if not options:
            rejected.append({'id':name,'xy':[x,y],'reason':reason});return False
        _,turn,best=min(options,key=lambda o:o[:2]);commit(name,model,x,y,yaw+turn*math.pi/2,best,zone,hub);return True
    # The spaceport's buildings stand on its platform; the shuttles rest on the landing decks.
    if port:
        h=port[7];heading=port_plan['heading'];at=port_plan['at']
        x,y,yaw=port_plan['terminal']
        placed.append({'model':lookup['space_terminal'],'id':'space_terminal','position':[x,y,h+SEAT_M],'yaw':yaw,'tint':1,
                       'zone':'arrival','foundation':'spaceport platform','pad':port_index,
                       'entrance':list(entrance_of(models[lookup['space_terminal']],x,y,yaw).coords[0])})
        lots.append(port_plan['shapes'][0]);lot_bins.add(port_plan['shapes'][0])
        llo,lhi=models[lookup['landing_pad']]['bounds_z_up']
        for k,(x,y,yaw) in enumerate(port_plan['landings']):
            placed.append({'model':lookup['landing_pad'],'id':'landing_pad','position':[x,y,h-EMBED_M-llo[2]],'yaw':yaw,'tint':1,'zone':'arrival'})
            props.append(port_plan['shapes'][1+k]);prop_bins.add(port_plan['shapes'][1+k])
            if 'civil_shuttle' in lookup:
                deck=h-EMBED_M+(lhi[2]-llo[2])*DECK-models[lookup['civil_shuttle']]['bounds_z_up'][0][2]
                placed.append({'model':lookup['civil_shuttle'],'id':'civil_shuttle','position':[x,y,deck],
                               'yaw':yaw+(.6 if k else -.4),'tint':1,'zone':'arrival','carried':True,'static_preview':True})
        if 'runway_beacon' in lookup:
            beacon=models[lookup['runway_beacon']]
            for du in np.arange(-port[4]*.15,port[4]-4,16):
                for dv in (-port[5]+3,port[5]-3):
                    x,y=at(du,dv);yaw=heading+(math.pi/2 if dv<0 else -math.pi/2);shape=footprint(beacon,x,y,yaw,.2)
                    if shape.intersects(clearance) or shape.intersects(plaza) or prop_bins.hits(shape):continue
                    placed.append({'model':lookup['runway_beacon'],'id':'runway_beacon','position':[x,y,h-EMBED_M],'yaw':yaw,'tint':1,'zone':'arrival'})
                    props.append(shape);prop_bins.add(shape)
    # Cable car on hill sites: the lowest, a middle and the highest district, each station beside its court.
    # Pylons stand on their own footing pads, as few as keep the cables clear of the graded ground.
    cable_lines=[];cable_reports=[];clearings=[]
    # With a guideway on the site, the cable line stays on one side of it and never crosses it: the side whose
    # districts span the most height.
    levels=[terrain.sample(*d['centre']) for d in districts];chain=[]
    def side(k):
        x,y=districts[k]['centre'];t=rail.project(Point(x,y));ax,ay,h=along(t)
        return 1 if (x-ax)*-math.sin(h)+(y-ay)*math.cos(h)>0 else -1
    groups=[list(range(len(districts)))] if not elevated else [[k for k in range(len(districts)) if side(k)==sd] for sd in (-1,1)]
    for group in sorted(groups,key=lambda g:-np.ptp([levels[k] for k in g]) if len(g)>1 else 0):
        if len(group)<2 or np.ptp([levels[k] for k in group])<40:continue
        order=sorted(group,key=lambda k:levels[k])
        chord=LineString([districts[order[0]]['centre'],districts[order[-1]]['centre']])
        if elevated and chord.intersects(rail.buffer(20)):continue
        # A middle station near the chord and at least 250 m from either end; otherwise one span of pylons.
        ends=[districts[order[0]]['centre'],districts[order[-1]]['centre']]
        middle=min((k for k in order[1:-1] if min(math.dist(districts[k]['centre'],e) for e in ends)>=250),
                   key=lambda k:chord.distance(Point(districts[k]['centre'])),default=None)
        chain=[order[0]]+([middle] if middle is not None and chord.distance(Point(districts[middle]['centre']))<120 else [])+[order[-1]];break
    tops=[k for k,d in enumerate(districts) if d['role']=='cliff_top'];feet=[k for k,d in enumerate(districts) if d['role']=='cliff_foot']
    if tops:
        low=feet[0] if feet else min((k for k in reached-by_cable if k<len(districts)),key=lambda k:math.dist(hubs[k],hubs[tops[0]]))
        chain=[low,tops[0]]
    # Each line from its anchors, lowest first: a district's court, or a guideway station (no court, reached by rail).
    anchors_=[[(districts[k]['centre'],k) for k in chain]] if chain else []
    if farm_station:anchors_.append([((farm_station[0],farm_station[1]),None),(districts[farm_station[2]]['centre'],farm_station[2])])
    for anchors in anchors_ if 'cable_station' in lookup and 'cable_pylon' in lookup else []:
        station=models[lookup['cable_station']];slo,shi=station['bounds_z_up']
        stations=[]
        for n,(centre,k) in enumerate(anchors):
            hub=np.array(centre,float)
            ahead=np.array(anchors[n+1][0])-hub if n+1<len(anchors) else hub-np.array(anchors[n-1][0])
            ahead/=np.linalg.norm(ahead);done=None
            for offset in (30,38,46,54,62):
                for swing in (0,.35,-.35,.7,-.7):
                    d=np.array([ahead[0]*math.cos(swing)-ahead[1]*math.sin(swing),ahead[0]*math.sin(swing)+ahead[1]*math.cos(swing)])
                    x,y=hub+d*offset*(1 if n+1<len(anchors) else -1)
                    for yaw in (math.atan2(ahead[1],ahead[0]),math.atan2(ahead[1],ahead[0])+math.pi):
                        option=site(station,x,y,yaw,accessible=k is not None,relief=EARTHWORK_M if k is not None else STEEP_RELIEF_M)
                        if not isinstance(option,str):done=(x,y,yaw,option);break
                    if done:break
                if done:break
            if done:
                x,y,yaw,option=done
                stations.append({'xy':np.array([x,y]),'yaw':yaw,'z':option['top']+SEAT_M+(shi[2]-slo[2])*BULLWHEEL[1],
                                 'half':(shi[0]-slo[0])*BULLWHEEL[0],'site':option,'court':k})
        pylon=models[lookup['cable_pylon']];plo,phi=pylon['bounds_z_up']
        base={'bounds_z_up':[[*PYLON_BASE[0],plo[2]],[*PYLON_BASE[1],phi[2]]]}
        gauge=(phi[0]-plo[0])*SHEAVE[0];rise=(phi[2]-plo[2])*SHEAVE[1]
        def cable(supports,side):
            """One cable over its supports, sagging 1/60 of each span; supports are (xy, z, half-gauge)."""
            line=[]
            for (pa,za,ga),(pb,zb,gb) in zip(supports,supports[1:]):
                length=float(np.linalg.norm(pb-pa));d=(pb-pa)/length;n=np.array([-d[1],d[0]])*side
                for t in np.linspace(0,1,max(2,math.ceil(length/8))+1)[:-1]:
                    xy=pa+(pb-pa)*t+n*(ga+(gb-ga)*t);line.append([float(xy[0]),float(xy[1]),float(za+(zb-za)*t-4*length/60*t*(1-t))])
            (pa,_,_),(pb,zb,gb)=supports[-2],supports[-1];d=(pb-pa)/np.linalg.norm(pb-pa);xy=pb+np.array([-d[1],d[0]])*side*gb
            return line+[[float(xy[0]),float(xy[1]),float(zb)]]
        def lowest(supports):
            """Least clearance over the graded ground, 20 m or more from every support."""
            ends=[s[0] for s in supports];worst=1e9
            for side in (-1,1):
                for x,y,z in cable(supports,side):
                    if min(math.dist((x,y),e) for e in ends)>=20:worst=min(worst,z-terrain.sample(x,y))
            return worst
        if len(stations)>=2:
            supports=[(stations[0]['xy'],stations[0]['z'],stations[0]['half'])];towers=[];length=0.0
            for a_,b_ in zip(stations,stations[1:]):
                pa,pb=a_['xy'],b_['xy'];span=float(np.linalg.norm(pb-pa));d=(pb-pa)/span;yaw=math.atan2(d[1],d[0])+math.pi/2
                # Each pylon as far along as its span from the last support still clears the ground: the fewest
                # pylons, each where the ground needs one (a convex rim, a bulge). A pylon stands on its own small pad,
                # its bank as steep as the face needs, off paths, commons and nature corridors; stations and pylons
                # are built together once the line clears, so their levels must already agree.
                here=supports[-1];at=0.0;trial=[];end=(pb,b_['z'],b_['half'])
                while lowest([here,end])<CABLE_CLEAR:
                    found=None
                    for t in np.arange(min(at+CABLE_SPAN,span-30),at+29,-6.0):
                        x,y=pa+d*t
                        if any(math.dist((x,y),(q[0],q[1]))<30 for q in trial+towers):continue
                        option=site(base,x,y,yaw,accessible=False,keep=circulation,relief=STEEP_RELIEF_M)
                        if isinstance(option,str):continue
                        # Its bank steepens until the stations' and other pylons' flats keep their level, up to TALUS_MAX.
                        pad_=option['pad'];others=[st['site']['pad'] for st in stations]+[q[2]['pad'] for q in trial+towers]
                        need=max([(abs(pad_[7]-o[7])+KNEE)/max(pad_shape(pad_).distance(pad_shape(o))-ROUND/2,.1) for o in others],default=0)
                        if need>talus_of(pad_):
                            if need>TALUS_MAX:continue
                            option=dict(option,pad=earthwork(pad_[0],pad_[1],math.atan2(pad_[3],pad_[2]),pad_[4],pad_[5],pad_[7],pad_[6],need))
                        support_=(np.array([x,y]),option['top']+SEAT_M+rise,gauge/2)
                        if lowest([here,support_])>=CABLE_CLEAR:found=(x,y,option,yaw,support_,float(t));break
                    if found is None:break
                    trial.append(found[:4]);here=found[4];at=found[5]
                if lowest([here,end])<CABLE_CLEAR:
                    rejected.append({'id':'cable_pylon','xy':[float(v) for v in (pa+pb)/2],'reason':'no clear cable span'});break
                towers+=trial;supports+=[(np.array([x,y]),o['top']+SEAT_M+rise,gauge/2) for x,y,o,_ in trial]+[end];length+=span
            else:
                # Every span clears the ground: the stations and pylons are built, then the cables.
                for n,item in enumerate(stations):
                    commit('cable_station',station,*item['xy'],item['yaw'],item['site'],'transport',item['court'],{'cable_station':n})
                for x,y,option,yaw in towers:
                    commit('cable_pylon',pylon,x,y,yaw,option,'transport',None,{'overhang':True})
                mine=[cable(supports,side) for side in (-1,1)];cable_lines+=mine
                # Cabins hang by their grip every 55 m, each cable travelling its own way.
                cabin=lookup.get('cable_cabin');cabins=0
                for side,line in zip((-1,1),mine):
                    xy=np.array([q[:2] for q in line]);zs=np.array([q[2] for q in line])
                    run=np.concatenate([[0],np.cumsum(np.linalg.norm(np.diff(xy,axis=0),axis=1))])
                    for s in (np.arange(30 if side>0 else 57,run[-1]-30,CABIN_STEP) if cabin is not None else []):
                        x,y=np.interp(s,run,xy[:,0]),np.interp(s,run,xy[:,1]);x2,y2=np.interp(s+1,run,xy[:,0]),np.interp(s+1,run,xy[:,1])
                        top=models[cabin]['bounds_z_up'][1][2]
                        placed.append({'model':cabin,'id':'cable_cabin','position':[float(x),float(y),float(np.interp(s,run,zs))-top],
                                       'yaw':math.atan2(y2-y,x2-x)+(math.pi if side<0 else 0),'tint':1,'zone':'transport',
                                       'elevated':True,'static_preview':True});cabins+=1
                cable_corridor=LineString([s[0] for s in supports]).buffer(gauge/2+3)
                # No tree crown reaches the cables or the cabins: the forest keeps 12 m beyond the outer cable.
                clearings.append(LineString([s[0] for s in supports]).buffer(gauge/2+12))
                reserve=unary_union([reserve,cable_corridor])
                cable_reports.append({'stations':len(stations),'pylons':len(towers),'length_m':length,'cabins':cabins,
                              'gauge_m':gauge,'min_clearance_m':min(lowest(supports[k:k+2]) for k in range(len(supports)-1)),
                              'serves':districts[anchors[-1][1]]['role']})
    collective=[model['id'] for model in models if model['kind']=='ribbon_habitat']
    homes=[model['id'] for model in models if model['kind'] in ['house','courtyard_habitat']]
    homes+=['ribbon_low'] if 'ribbon_low' in lookup else []
    for hub,district in enumerate(districts):
        cx,cy=district['centre'];role=district['role'];start=len(placed)
        # Dense crowns hold fifteen stacked habitats, mixed ones eleven, garden edges eight houses.
        if role in ['core','mixed']:choices=collective;target=15 if role=='core' else 11
        elif role=='garden':choices=homes;target=8
        elif role=='food':choices=['nested_greenhouse','greenhouse_long','water_tower'];target=5
        elif role=='arrival':choices=['asymmetric_hangar'] if port else ['space_terminal','asymmetric_hangar'];target=2
        elif role=='cliff_foot':choices=[k for k in ['ribbon_lantern','ribbon_compact','ribbon_helix'] if k in lookup];target=4
        elif role=='cliff_top':choices=homes+[k for k in ['ribbon_low','shell_tall'] if k in lookup];target=12
        elif role=='farm':choices=[k for k in ['greenhouse_long','nested_greenhouse','water_tower','asymmetric_hangar'] if k in lookup];target=6
        else:choices=['civic_petals','civic_workshop','community_market'];target=6
        local_rng=random.Random(district['seed'])
        for attempt in range(420):
            if len(placed)-start>=target:break
            # Stratified area samples; no identical ring of individual houses.
            angle=attempt*2.399963229728653+local_rng.random()*.4
            radius=28+(district['radius']-20)*math.sqrt(local_rng.random())
            if role=='arrival' and port:radius+=45  # hangars line the spaceport platform
            x=cx+math.cos(angle)*radius;y=cy+math.sin(angle)*radius*.88
            name=choices[(attempt+hub)%len(choices)]
            if role in ['core','mixed'] and attempt%17==0:name='community_market'
            yaw=math.atan2(cx-x,-(cy-y))+local_rng.uniform(-.15,.15)
            if role in ('cliff_foot','cliff_top'):
                # Fronts to the valley: backs against the face at its foot, views over the edge on its top.
                yaw=math.atan2(valley[0],-valley[1])+local_rng.uniform(-.2,.2)
            add(name,x,y,yaw,role,hub)
        district['buildings']=len(placed)-start
    # Houses on the cliff's face, each above a leg of the stair path on its own small terrace, front and terrace to the
    # valley; the cable car's corridor stays clear (reserve).
    face_houses=0
    if face_path:
        line=LineString(face_path);local=random.Random(seed+29);face_homes=[k for k in homes if k in lookup]
        for s_ in np.arange(15,line.length-15,FACE_STEP_M):
            if face_houses>=FACE_HOUSES or not face_homes:break
            a_=line.interpolate(s_);b_=line.interpolate(min(s_+2,line.length));d=np.array([b_.x-a_.x,b_.y-a_.y])
            if np.linalg.norm(d)<1e-6 or terrain.slope(a_.x,a_.y,8)<.2:continue  # the face only
            e=8.0;n=np.array([terrain.sample(a_.x+e,a_.y)-terrain.sample(a_.x-e,a_.y),terrain.sample(a_.x,a_.y+e)-terrain.sample(a_.x,a_.y-e)])
            n/=max(float(np.linalg.norm(n)),1e-9)  # uphill: the house's back to the slope, its long side along the contour
            name=face_homes[local.randrange(len(face_homes))];lo_,hi_=models[lookup[name]]['bounds_z_up']
            # The nearest offset above the leg whose lot clears it: the door a short flight above the leg.
            rise=math.tan(math.asin(min(.95,FACE_GRADE/max(terrain.slope(a_.x,a_.y,8),FACE_GRADE))))
            ok=False
            for off in np.arange((hi_[1]-lo_[1])/2+3.0,(hi_[1]-lo_[1])/2+5.0+((hi_[0]-lo_[0])/2+1)*rise,1.5):
                x,y=np.array([a_.x,a_.y])+n*off
                ok=add(name,float(x),float(y),math.atan2(-n[0],n[1]),'cliff_face',feet_[0],relief=STEEP_RELIEF_M,turns=(0,),steepest=1.0)
                if ok:break
            face_houses+=ok
    if len(lots)<20:raise ValueError('Unsupported site: too few buildings on stable ground')
    # Field terraces along the contours of each food district. The banks between them take the slope
    # at 1:2 at most: the gap grows with the slope.
    fields=[];farmland=[]
    if 'growing_bed' in lookup:
        blocked=unary_union([reserve,*[lot.buffer(6) for lot in lots],*[p.buffer(1.5) for p in paths],plaza.buffer(2)])
        for district in districts:
            if district['role'] not in ('food','farm'):continue
            # The fields' slope is the meadow's own: the natural ground, not the banks graded since.
            cx,cy=district['centre'];e=20.0;graded_=terrain.values;terrain.values=terrain.natural
            gx=(terrain.sample(cx+e,cy)-terrain.sample(cx-e,cy))/(2*e);gy=(terrain.sample(cx,cy+e)-terrain.sample(cx,cy-e))/(2*e)
            terrain.values=graded_
            slope=math.hypot(gx,gy);farm=district['role']=='farm'
            if slope>(FARM_GRADE if farm else FIELD_GRADE):continue
            down=np.array([-gx,-gy])/slope if slope>1e-3 else np.array([0.,-1.]);row=np.array([-down[1],down[0]])
            yaw=math.atan2(row[1],row[0]);reach=district['radius']+30;mine=[]
            gap=max(FIELD_GAP,(slope*FIELD_W+TALUS*ROUND/2+KNEE)/(TALUS-slope)+1);pitch=FIELD_W+gap
            area=Point(cx,cy).buffer(reach).difference(blocked)
            if slope<=FIELD_DRAPED or farm:
                # Gentle ground needs no terrace: 48 x 10 m fields lie on it, 3 m grass strips between them.
                for j in range(-int(reach/13),int(reach/13)+1):
                    last=-1e9
                    for t in np.arange(-reach,reach,3.0):
                        if t<last+51:continue
                        mid=np.array([cx,cy])+down*j*13+row*(t+24)
                        strip=pad_shape(earthwork(mid[0],mid[1],yaw,24,5,0,1.5))
                        if not area.contains(strip) or terrain.wet(*mid,WATER_MARGIN_M):continue
                        fields.append((strip,yaw,None));mine.append(strip);last=t
                if mine:farmland.append(unary_union(mine).convex_hull.buffer(10).difference(corridors))
                continue
            for j in range(-int(reach/pitch),int(reach/pitch)+1):
                # Each row packs its terraces into the free ground, sliding 3 m at a time.
                last=-1e9
                for t in np.arange(-reach,reach,3.0):
                    if t<last+FIELD_LEN+FIELD_GAP:continue
                    mid=np.array([cx,cy])+down*j*pitch+row*(t+FIELD_LEN/2)
                    p=earthwork(mid[0],mid[1],yaw,FIELD_LEN/2,FIELD_W/2,0,1.5);strip=pad_shape(p)
                    if not area.contains(strip) or terrain.wet(*mid,WATER_MARGIN_M):continue
                    low_,high_=support(terrain,strip)
                    if high_-low_>3.5:continue
                    p=settle(p,ground(strip,2.0),cap=1.5)
                    if p is None:continue
                    dig(p);fields.append((strip,yaw,p[7]));mine.append(strip);last=t
            # The terraces make one open farmland: no forest between or around them.
            if mine:farmland.append(unary_union(mine).convex_hull.buffer(10).difference(corridors))
        # An agrivoltaic canopy over every third terrace, growing benches on the others, irrigation along them.
        for n,(strip,yaw,h) in enumerate(fields):
            c=strip.centroid;u=np.array([math.cos(yaw),math.sin(yaw)])
            # A terrace is level; on a field lying on the meadow each piece is set into its own lowest ground.
            seat=(lambda shape:h) if h is not None else (lambda shape:seated(shape)[0])
            for kind,offset in [('agri_canopy',0)] if n%3==0 and 'agri_canopy' in lookup else [('growing_bed',-7),('growing_bed',7)]:
                model=models[lookup[kind]];x,y=c.x+u[0]*offset,c.y+u[1]*offset;shape=footprint(model,x,y,yaw,.1)
                if not strip.buffer(1.5).contains(shape) or prop_bins.hits(shape):continue
                placed.append({'id':kind,'model':lookup[kind],'position':[x,y,seat(shape)-model['bounds_z_up'][0][2]-EMBED_M],'yaw':yaw,'tint':1,'zone':'agriculture'})
                props.append(shape);prop_bins.add(shape)
            if n%4==1 and 'irrigation_node' in lookup:
                model=models[lookup['irrigation_node']];x,y=c.x+u[0]*(FIELD_LEN/2-2),c.y+u[1]*(FIELD_LEN/2-2);shape=footprint(model,x,y,yaw,.1)
                if prop_bins.hits(shape):continue
                placed.append({'id':'irrigation_node','model':lookup['irrigation_node'],'position':[x,y,seat(shape)-model['bounds_z_up'][0][2]-EMBED_M],
                               'yaw':yaw,'tint':1,'zone':'agriculture'})
                props.append(shape);prop_bins.add(shape)
    paved=prep(common_area.difference(garden_area))
    def prop(name,x,y,yaw=0,zone='public'):
        model=models[lookup[name]];shape=footprint(model,x,y,yaw,.18)
        if max(map(abs,shape.bounds))>terrain.half-4 or terrain.wet(x,y,WATER_MARGIN_M):return False
        if lot_bins.hits(shape) or prop_bins.hits(shape) or any(shape.intersects(o) for o in station_shapes):return False
        if name not in ['solar_canopy','agri_canopy'] and (shape.intersects(clearance) or path_bins.hits(shape)):return False
        if shape.intersects(corridors) or any(shape.intersects(f[0]) for f in fields):return False
        low,high=seated(shape)
        if high-low>.2:return False
        # On a court's paving it stands on the paving (layout: the highest ground plus the path's lift, plus 1 cm);
        # across the paving's edge it would float on one side; elsewhere it is set into its lowest ground.
        if paved.intersects(shape) and not paved.contains(shape):return False
        on_paving=paved.contains(shape);z=high+PATH_LIFT+.01 if on_paving else low-EMBED_M
        placed.append({'id':name,'model':lookup[name],'position':[x,y,z-model['bounds_z_up'][0][2]],
                       'yaw':yaw,'tint':1,'zone':zone,**({'seat':'paving'} if on_paving else {})})
        props.append(shape);prop_bins.add(shape);return True
    # Generated street furniture: the larger pieces on their own small level pads near each court, before the small
    # furniture, so no later bank cuts the ground from under a bench; a bicycle shelter beside every station.
    def piece(name,x,y,yaw,zone='public'):
        """A larger piece of furniture on its own level pad where the ground allows; False otherwise."""
        if name not in lookup:return False
        model=models[lookup[name]];shape=footprint(model,x,y,yaw,.5)
        if max(map(abs,shape.bounds))>terrain.half-6 or terrain.wet(x,y,WATER_MARGIN_M):return False
        if lot_bins.hits(shape) or prop_bins.hits(shape) or path_bins.hits(shape) or shape.intersects(clearance) or shape.intersects(corridors):return False
        if any(shape.intersects(f[0]) for f in fields) or any(shape.intersects(o) for o in station_shapes):return False
        low,high=support(terrain,shape)
        if high-low>2.5:return False
        lo_,hi_=model['bounds_z_up'];mx,my=(lo_[0]+hi_[0])/2,(lo_[1]+hi_[1])/2
        p=settle(earthwork(x+mx*math.cos(yaw)-my*math.sin(yaw),y+mx*math.sin(yaw)+my*math.cos(yaw),yaw,
                           (hi_[0]-lo_[0])/2+1.2,(hi_[1]-lo_[1])/2+1.2,0,1.5),ground(shape,2.0),cap=1.2)
        if p is None:return False
        dig(p)
        placed.append({'id':name,'model':lookup[name],'position':[x,y,p[7]-lo_[2]-EMBED_M],'yaw':yaw,'tint':1,'zone':zone})
        props.append(shape);prop_bins.add(shape);return True
    sets={'core':['kiosk','bike_shelter','play_sculpture'],'mixed':['bike_shelter','play_sculpture'],'garden':['pergola','play_sculpture'],
          'civic':['kiosk','pergola'],'cliff_top':['pergola','kiosk'],'cliff_foot':['bike_shelter','kiosk'],'food':['bike_shelter'],'farm':['bike_shelter']}
    for i,district in enumerate(districts):
        cx,cy=district['centre'];r=radii[i]
        for k,name in enumerate(sets.get(district['role'],[])):
            for j in range(16):
                angle=k*2.1+j*math.tau/16+i*.37;rad=r+7+(j%3)*4
                if piece(name,cx+rad*math.cos(angle),cy+rad*math.sin(angle),angle+math.pi/2):break
    for q in [q for q in placed if q['id'] in ('garden_station','interlaced_station','cable_station')]:
        x,y=q['position'][:2]
        for j in range(12):
            angle=j*math.tau/12;rad=26+(j%3)*5
            if piece('bike_shelter',x+rad*math.cos(angle),y+rad*math.sin(angle),angle+math.pi/2,'transport'):break
    # Each court: two shades, eight benches round it, six rain gardens beyond, four lamps, water, a sign, a cabinet.
    for i,(cx,cy) in enumerate(hubs[:len(districts)]):
        prop('solar_canopy',cx-6,cy+2,.3*i);prop('solar_canopy',cx+6,cy-3,.3*i+math.pi)
        for j in range(8):
            angle=j*math.tau/8+i*.7
            prop('planted_bench' if j%2 else 'planted_bench_wild',cx+9.5*math.cos(angle),cy+9.5*math.sin(angle),angle+math.pi/2)
        for j in range(6):
            angle=j*math.tau/6+i*.7+.3
            prop('rain_garden' if j%2 else 'rain_garden_long',cx+14.5*math.cos(angle),cy+14.5*math.sin(angle),angle+math.pi/2)
        for j in range(4):
            angle=j*math.tau/4+i*.7+.4;prop('petal_lamp',cx+12*math.cos(angle),cy+12*math.sin(angle),angle)
        prop('drinking_fountain',cx+5,cy-4);prop('wayfinding_leaf',cx-3,cy-8);prop('service_cabinet',cx+8,cy+6)
    # Along every path, every 21 m: a lamp, then a bench facing the path with a planter beside it, either side.
    for line in roads:
        for k,distance in enumerate(np.arange(14,line.length-8,21)):
            p=line.interpolate(distance);q=line.interpolate(distance+1);d=np.array([q.x-p.x,q.y-p.y]);d/=np.linalg.norm(d)
            n=np.array([-d[1],d[0]]);heading=math.atan2(d[1],d[0]);at=np.array([p.x,p.y])
            if k%2==0:
                prop('petal_lamp',*(at+n*(2.6 if k%4==0 else -2.6)),heading);continue
            for sd in (1,-1):
                x,y=at+n*sd*2.9
                if prop('planted_bench' if k%4==1 else 'planted_bench_wild',x,y,heading+(math.pi if sd>0 else 0)):
                    prop('rain_garden' if k%4==1 else 'rain_garden_long',*(at+n*sd*3.1+d*2.9),heading);break
    # A bench and a planter on each building's level apron, either side of its door.
    for item in [q for q in placed if 'support_max' in q and not q.get('overhang') and 'entrance' in q]:
        pad=grade.pads[item['pad']];flat=pad_shape(pad).buffer(-.4);model=models[item['model']]
        x0,y0=item['position'][:2];body=footprint(model,x0,y0,item['yaw'],.15);own=footprint(model,x0,y0,item['yaw'],.8)
        ex,ey=item['entrance'];d=np.array([ex-x0,ey-y0]);d/=max(np.linalg.norm(d),1e-6);n=np.array([-d[1],d[0]])
        for name,lateral in (('planted_bench',2.8),('rain_garden',-2.8)):
            x,y=np.array([ex,ey])+n*lateral+d*1.2;yaw=math.atan2(d[1],d[0])+math.pi/2;furniture=models[lookup[name]]
            shape=footprint(furniture,x,y,yaw,.1)
            if not flat.contains(shape) or shape.intersects(body) or path_bins.hits(shape) or prop_bins.hits(shape):continue
            if any(not o.equals_exact(own,1e-6) for o in lot_bins.touching(shape)):continue
            placed.append({'id':name,'model':lookup[name],'position':[x,y,pad[7]-furniture['bounds_z_up'][0][2]-EMBED_M],
                           'yaw':yaw,'tint':1,'zone':'public'})
            props.append(shape);prop_bins.add(shape)
    # Garden districts share growing beds and rain gardens between the houses.
    for district in districts:
        if district['role']!='garden':continue
        cx,cy=district['centre'];local=random.Random(district['seed']+7)
        for j in range(24):
            angle=local.uniform(0,math.tau);r=local.uniform(18,district['radius']-6)
            prop('growing_bed' if j%2 else 'rain_garden',cx+r*math.cos(angle),cy+r*math.sin(angle),local.uniform(0,math.pi))
    # Small pieces: a sorting station by every court; insect hotels in gardens, farms, fields and on the cliff top.
    for i,district in enumerate(districts):
        cx,cy=district['centre'];r=radii[i]
        if 'sorting_station' in lookup:
            for j in range(10):
                angle=j*math.tau/10+i*.53;rad=r+4+(j%2)*3
                if prop('sorting_station',cx+rad*math.cos(angle),cy+rad*math.sin(angle),angle+math.pi/2):break
        if district['role'] in ('garden','farm','food','cliff_top') and 'insect_hotel' in lookup:
            local=random.Random(district['seed']+11);count=0
            for j in range(20):
                if count>=3:break
                angle=local.uniform(0,math.tau);rr=local.uniform(14,district['radius'])
                count+=prop('insect_hotel',cx+rr*math.cos(angle),cy+rr*math.sin(angle),local.uniform(0,math.tau))
    # Steps on the finished, graded ground: the network, then each access from its door.
    for i,line in enumerate(roads):
        a,b=edges[i][:2];dense=a>=len(districts) or b>=len(districts) or min(districts[a]['density'],districts[b]['density'])>.6
        for distance in np.arange(0,line.length,3):
            p=line.interpolate(distance);q=line.interpolate(min(distance+3,line.length))
            trail=i in grass_links and .32<(distance+1.5)/line.length<.68
            if not trail and not plaza.contains(Point((p.x+q.x)/2,(p.y+q.y)/2)):stairs+=climb((p.x,p.y),(q.x,q.y),2*(1.45 if dense else 1.15)+.1)
    steepest=0.0
    for line in accesses:
        for s in np.arange(0,line.length,3):
            p=line.interpolate(s);q=line.interpolate(min(s+3,line.length))
            if p.distance(q)>.2:steepest=max(steepest,abs(terrain.sample(q.x,q.y)-terrain.sample(p.x,p.y))/p.distance(q))
            stairs+=climb((p.x,p.y),(q.x,q.y),2.2)
    # Continuous guidebeams, separated supports and cabins share one datum.
    support_shapes=[]
    guide=models[lookup['canopy_guideway']];lo,hi=guide['bounds_z_up']
    if elevated and hi[0]-lo[0]>200:
        placed.append({'id':'canopy_guideway','model':lookup['canopy_guideway'],'position':[0,0,station_z],
                       'yaw':0,'tint':1,'zone':'transport','elevated':True})
    elif elevated:
        # A generated straight segment repeats along the line, one length of arc apart.
        step=(hi[0]-lo[0])*.995
        for s_ in np.arange(step/2,rail.length,step):
            xx,yy,yaw=along(float(s_))
            placed.append({'id':'canopy_guideway','model':lookup['canopy_guideway'],'position':[xx,yy,station_z],
                           'yaw':yaw,'tint':1,'zone':'transport','elevated':True})
    for xx,yy,yaw in rings:
        placed.append({'id':'viaduct_ring','model':lookup['viaduct_ring'],'position':[xx,yy,datum],
                       'yaw':yaw,'tint':1,'zone':'transport','elevated':True,'foundation':'earthwork'})
        support_shapes.append(Point(xx,yy).buffer(5))
    pier_members=[];piers=0;corridor=[];corridor_half=0.0
    for b in branches:
        line_=LineString(b)
        if hi[0]-lo[0]<=200:
            step=(hi[0]-lo[0])*.995
            for s_ in np.arange(step/2,line_.length,step):
                p_=line_.interpolate(s_);a_=line_.interpolate(max(0,s_-1));b_=line_.interpolate(min(line_.length,s_+1))
                placed.append({'id':'canopy_guideway','model':lookup['canopy_guideway'],'position':[p_.x,p_.y,station_z],
                               'yaw':math.atan2(b_.y-a_.y,b_.x-a_.x),'tint':1,'zone':'transport','elevated':True,'intercity':True})
        for s_ in np.arange(30,line_.length-5,PIER_STEP):
            p_=line_.interpolate(s_)
            if farm_station and math.dist((p_.x,p_.y),farm_station[:2])<32:continue
            a_=line_.interpolate(max(0,s_-1));b_=line_.interpolate(min(line_.length,s_+1));d=np.array([b_.x-a_.x,b_.y-a_.y]);d/=np.linalg.norm(d)
            n=np.array([-d[1],d[0]]);c=np.array([p_.x,p_.y])
            # The column stands on the higher side, the shorter one, set 1.5 m into the ground; its arm reaches over
            # the beam and holds it by a hanger, a brace under the arm; the train passes between column and line.
            if (terrain.height(*(c-n*PIER_SIDE)) or -1e9)>(terrain.height(*(c+n*PIER_SIDE)) or -1e9):n=-n
            foot=c+n*PIER_SIDE;g=terrain.height(*foot)
            if g is None:continue
            head=station_z+1.9
            pier_members+=[[[*foot,g-1.5],[*foot,head],1.5],[[*foot,head],[*(c-n*.4),head],.8],[[*c,head],[*c,station_z+.7],.5],
                           [[*foot,head-5.5],[*(foot-n*3.2),head],.5]]
            piers+=1
        for f,lane in ((.3,-1),(.7,1)):
            p_=line_.interpolate(line_.length*f);b_=line_.interpolate(line_.length*f+1);yaw=math.atan2(b_.y-p_.y,b_.x-p_.x)
            placed.append({'id':'panoramic_train','model':lookup['panoramic_train'],
                           'position':[p_.x-math.sin(yaw)*lane*1.8,p_.y+math.cos(yaw)*lane*1.8,station_z],
                           'yaw':yaw,'tint':1,'zone':'transport','elevated':True,'static_preview':True,'intercity':True})
    if branches:
        # The engine keeps 192 segments at most: the line simplified, the corridor widened by the simplification.
        for tolerance in (3.0,4.0,6.0,8.0,12.0):
            corridor=[[*a,*b] for line_ in map(LineString,branches) for a,b in zip(line_.simplify(tolerance).coords,line_.simplify(tolerance).coords[1:])]
            if len(corridor)<=192:break
        corridor_half=CORRIDOR_M+tolerance
    for f,lane in [(.1,-1),(.45,1),(.66,-1),(.9,1)] if elevated else []:
        xx,yy,yaw=along(rail.length*f)
        placed.append({'id':'panoramic_train','model':lookup['panoramic_train'],
                       'position':[xx-math.sin(yaw)*lane*1.8,yy+math.cos(yaw)*lane*1.8,station_z],
                       'yaw':yaw,'tint':1,'zone':'transport','elevated':True,'static_preview':True})
    # Union before material partition: no doubled ribbons or dark overlaps at
    # junctions. An inset stone course tells how aggregate paths are made.
    whole=unary_union([*pathpieces,*walks,common_area]).buffer(.28,quad_segs=4).buffer(-.28,quad_segs=4).difference(garden_area).simplify(.035,preserve_topology=True)
    border=whole.difference(whole.buffer(-.18,quad_segs=4))
    inner=whole.difference(border)
    common_surface=inner.intersection(common_area.buffer(.65))
    aggregate=inner.difference(common_surface)
    crops=[(strip.buffer(-.5,quad_segs=2).difference(whole.buffer(.3)),yaw) for strip,yaw,_ in fields]
    # Trees keep a garden's width from every building: the forest stays between groups. Fields,
    # the spaceport platform and the cable's corridor are open ground too.
    occupied=unary_union([whole.buffer(.18),network.buffer(.9),*[lot.buffer(GARDEN_M) for lot in lots],*paths,*props,*station_shapes,
                          *support_shapes,*[f[0].buffer(1) for f in fields],*farmland,*([pad_shape(port).buffer(6)] if port else []),
                          *clearings,*([rail.buffer(16)] if elevated else []),*[LineString(b).buffer(16) for b in branches]])
    cell=terrain.half*2/256;origin=(-terrain.half,-terrain.half);bits=np.zeros(2048,dtype='<u4');prepared=prep(occupied)
    # Inhabited districts are open gardens: most trees give way there, the corridors stay whole.
    opened=prep(unary_union([Point(*d['centre']).buffer(d['radius']) for d in districts]).difference(corridors));thin=random.Random(seed+1)
    for y in range(256):
        for x in range(256):
            tile=box(origin[0]+x*cell,origin[1]+y*cell,origin[0]+(x+1)*cell,origin[1]+(y+1)*cell);draw=thin.random()
            if prepared.intersects(tile) or (draw<OPEN_GARDEN and opened.contains(tile.centroid)):bit=y*256+x;bits[bit//32]|=np.uint32(1<<(bit%32))
    slots=library['material_slots']
    report={'schema':2,'seed':seed,'planet_seed':terrain.seed,'anchor':[terrain.lat,terrain.lon],
            'terrain_sha256':terrain.digest,'library_sha256':library['library_sha256'],'masterplan':spec,
            'composition':'approved braided archipelago; stacked habitats; protected nature corridors',
            'districts':districts,'habitat_centres':hubs,'commons':[list(p.exterior.coords) for p in components(common_area)],
            'instances':placed,'rejected':rejected,'road_lines':[list(line.coords) for line in roads],
            'pedestrian_edges':edges,'grass_links':grass_links,'parcels':[list(lot.exterior.coords) for lot in lots],
            'access_paths':[list(path.exterior.coords) for path in paths],'access_lines':[list(line.coords) for line in accesses],
            'foundations':[{'outline':list(shape.exterior.coords),'top':top,'kind':kind} for shape,top,kind,_ in stairs],
            'steps':len(stairs),'foundation_materials':supports_materials(slots),
            'earthworks':{'pads':[list(p) for p in grade.pads],'fields':len(fields),'spaceport':list(port) if port else None,
                          'steepest_access':steepest,'largest_reach_m':max(grade.visible,default=0.0),'reach_limit_m':REACH_M,
                          'steepest_bank':max(map(talus_of,grade.pads),default=TALUS)},
            'cliff_face':{'path':face_path,'houses':face_houses},
            'pier_members':pier_members,
            'cables':cable_lines,
            'connected_pedestrian_network':all(part.distance(Point(*hubs[0]))<1 or any(part.distance(Point(*hubs[k]))<5 for k in by_cable)
                                               for part in components(network.buffer(.01))),'land_grid':[*origin,cell,1],
            'land_use':{'path_area_m2':aggregate.area,'common_surface_m2':common_surface.area,'border_m2':border.area,
                        'field_area_m2':sum(f[0].area for f in fields),
                        'built_surface_fraction':unary_union([whole,*lots,*station_shapes]).area/(terrain.half*2)**2},
            'policy':{'earthwork_relief_m':EARTHWORK_M,'pad_margin_m':PAD_MARGIN_M,'talus':TALUS,'ramp_grade':STAIR_GRADE,
                      'max_path_grade':MAX_GRADE,'stair_m':{'rise':STAIR_RISE_M,'going':STAIR_GOING_M,'width':STAIR_WIDTH_M},
                      'water_level_m':terrain.water_level,'water_margin_m':WATER_MARGIN_M,'path_width_m':[2.2,2.9],
                      'private_plots':False,'vehicle_roads':False,'minimum_building_clearance_m':.8,'protected_corridors':True,
                      'cable_clearance_m':CABLE_CLEAR,'steep_relief_m':STEEP_RELIEF_M,'earthwork_reach_m':REACH_M,
                      'pad_seat_m':SEAT_M,'furniture_embed_m':EMBED_M},
            'transport':{'stations':len(spec['stations'])+(1 if farm_station else 0),'guideway_elevation_m':station_z if elevated else None,
                         'length_m':rail.length if elevated else 0,'vehicles':'static exterior previews' if elevated else None,
                         'cable_car':cable_reports[0] if cable_reports else None,'cable_cars':cable_reports,
                         'intercity':{'branches':[LineString(b).length for b in branches],'piers':piers,'farm_station':list(farm_station[:2]) if farm_station else None,
                                      'lines':[[list(q) for q in LineString(b).simplify(1.0).coords] for b in branches]},
                         'corridor':{'segments':corridor,'half_width_m':corridor_half}},
            'acceptance':{'art':False,'performance':False}}
    # Built paths at their level: aggregate on it, the common's paving 1 cm above, the stone curb CURB_M above.
    surfaces=[(aggregate,slots['permeable'],0.0),(common_surface,slots['common_paving'],.01),(border,slots['path_border'],CURB_M)]
    if 'crop' in slots:surfaces+=[(shape,slots['crop'],.035,yaw) for shape,yaw in crops if not shape.is_empty]
    return report,surfaces,bits,grade
