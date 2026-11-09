"""Terrain-constrained implementation of the approved braided archipelago plan."""
import math
import random
import numpy as np
from shapely.geometry import Point,Polygon,LineString,box
from shapely.ops import unary_union,nearest_points
from shapely.prepared import prep
from shapely.affinity import scale,rotate,translate
from masterplan import proposal,rail_point,rail_heading


def components(shape):
    if shape.is_empty:return []
    return list(shape.geoms) if hasattr(shape,'geoms') else [shape]


def organic(cx,cy,r,phase):
    return Polygon([(cx+r*(1+.13*math.sin(3*a+phase))*math.cos(a),
                     cy+r*.86*(1+.13*math.sin(3*a+phase))*math.sin(a)) for a in np.linspace(0,math.tau,65)[:-1]])


def compose(terrain,library,seed):
    from layout import footprint,support
    rng=random.Random(seed);spec=proposal(seed);districts=spec['districts'];hubs=[d['centre'] for d in districts]+spec['stations']
    if terrain.half<510:raise ValueError('Expanded city needs a terrain export at least 1024 m wide')
    lookup={m['id']:i for i,m in enumerate(library['models'])}
    rail=LineString(spec['rail']);corridors=unary_union([LineString(line).buffer(spec['corridor_half_width_m']) for line in spec['habitat_corridors']])
    # A sparse nearest-neighbour tree and a few redundant foot connections.
    reached={0};edges=[]
    while len(reached)<len(hubs):
        _,a,b=min((math.dist(hubs[a],hubs[b]),a,b) for a in sorted(reached) for b in range(len(hubs)) if b not in reached)
        edges.append((a,b));reached.add(b)
    for i in range(len(hubs)):
        j=min((j for j in range(len(hubs)) if i!=j and (i,j) not in edges and (j,i) not in edges),key=lambda j:math.dist(hubs[i],hubs[j]))
        if math.dist(hubs[i],hubs[j])<190 and i%3==0:edges.append((i,j))
    roads=[]
    for a,b in edges:
        p=np.array(hubs[a]);q=np.array(hubs[b]);delta=q-p;normal=np.array([-delta[1],delta[0]])/np.linalg.norm(delta)
        control=(p+q)/2+normal*rng.uniform(-18,18)
        roads.append(LineString([(1-t)**2*p+2*(1-t)*t*control+t*t*q for t in np.linspace(0,1,33)]))
    network=unary_union(roads);clearance=network.buffer(2.05)
    station_z=max(terrain.sample(x,y) for x,y in spec['rail'])+23.4
    commons=[];gardens=[]
    for i,(x,y) in enumerate(hubs):
        radius=12 if i<len(districts) and districts[i]['density']>.6 else 9
        if i>=len(districts):radius=18
        commons.append(organic(x,y,radius,i*.8))
        # A planted off-centre island keeps the pedestrian surface porous.
        if i<len(districts):gardens.append(organic(x+3.3,y+2.8,radius*.43,i*.5))
    common_area=unary_union(commons);garden_area=unary_union(gardens)
    reserve=unary_union([clearance,common_area.buffer(.6),corridors,rail.buffer(13)])
    pathpieces=[];grass_links=[]
    for i,line in enumerate(roads):
        a,b=edges[i];dense=a>=len(districts) or b>=len(districts) or min(districts[a]['density'],districts[b]['density'])>.6
        if not dense and i%3==1:
            grass_links.append(i)
            for start,end in [(0,.32),(.68,1)]:pathpieces.append(LineString([line.interpolate(t,normalized=True) for t in np.linspace(start,end,14)]).buffer(1.1,quad_segs=5))
        else:pathpieces.append(line.buffer(1.45 if dense else 1.15,quad_segs=5))
        for distance in np.arange(0,line.length,3):
            p=line.interpolate(distance);q=line.interpolate(min(distance+3,line.length))
            hp=terrain.sample(p.x,p.y);hq=terrain.sample(q.x,q.y)
            if min(hp,hq)<2:raise ValueError('Pedestrian network crosses the water margin')
            if abs(hq-hp)/max(.01,p.distance(q))>.08:raise ValueError('Pedestrian network exceeds 8% grade')
    placed=[];lots=[];paths=[];platforms=[];props=[];rejected=[]
    def add(name,x,y,yaw,zone,hub):
        model=library['models'][lookup[name]];lot=footprint(model,x,y,yaw,.8)
        reason=None
        if max(map(abs,lot.bounds))>terrain.half-5:reason='terrain boundary'
        elif lot.intersects(reserve):reason='reserved nature, common or circulation'
        elif any(lot.intersects(other) for other in lots):reason='inhabited footprint clearance'
        elif any(lot.intersects(path) for path in paths):reason='existing shared access'
        if reason is None:
            low,high=support(terrain,lot)
            if low<2 or high-low>.5:reason='unsupported footing'
        if reason:
            rejected.append({'id':name,'xy':[x,y],'reason':reason});return False
        lo,hi=model['bounds_z_up'];entry=model.get('entrance_z_up',[0,lo[1],0])
        entrance=Point(x+entry[0]*math.cos(yaw)-entry[1]*math.sin(yaw),y+entry[0]*math.sin(yaw)+entry[1]*math.cos(yaw))
        destination=nearest_points(entrance,network)[1]
        line=LineString([entrance,destination]);path=line.buffer(1.05,quad_segs=5)
        if any(path.intersects(other) for other in lots):return False
        if line.length>105:return False
        # Architectural sources use z=0 as their ground datum. Negative plinth
        # vertices are buried structure, not a request to lift the whole asset.
        placed.append({'model':lookup[name],'id':name,'position':[x,y,high+.08],'yaw':yaw,'tint':rng.uniform(.96,1.04),
                       'zone':zone,'shared_court':hub,'density':districts[hub]['density'],'support_min':low,'support_max':high,
                       'entrance':[entrance.x,entrance.y],'access_length':line.length,'floors':model.get('floors',1)})
        # Rounded, closely fitting manufactured support. The actual rendered
        # support does not determine vegetation masks or alter planetary relief.
        # Render a support following the projected architecture, rather than
        # turning its conservative collision rectangle into a private apron.
        outline=model.get('footprint_outline')
        platform=translate(rotate(Polygon(outline),math.degrees(yaw),origin=(0,0)),x,y) if outline else footprint(model,x,y,yaw,0)
        platform=unary_union([platform,entrance.buffer(.65,quad_segs=5)]).convex_hull.buffer(.12,quad_segs=5)
        platforms.append((platform,high+.08+min(entry[2],.18)));lots.append(lot);paths.append(path);return True
    # Reserve complete station footprints before any building or garden prop.
    station_shapes=[]
    for i,(x,y) in enumerate(spec['stations']):
        name='interlaced_station' if i==1 else 'garden_station';yaw=rail_heading(x);model=library['models'][lookup[name]]
        shape=footprint(model,x,y,yaw,1);station_shapes.append(shape)
        low,high=support(terrain,shape)
        lo,hi=model['bounds_z_up']
        footing=scale(Point(0,0).buffer(1,quad_segs=16),(hi[0]-lo[0])*.43,(hi[1]-lo[1])*.43)
        footing=translate(rotate(footing,math.degrees(yaw),origin=(0,0)),x,y)
        platforms.append((footing,station_z-23+lo[2]+.12))
        placed.append({'id':name,'model':lookup[name],'position':[x,y,station_z-23],'yaw':yaw,'tint':1,
                       'zone':'transport','station':i,'guideway_datum':station_z})
    reserve=unary_union([reserve,*station_shapes])
    collective=[model['id'] for model in library['models'] if model['kind']=='ribbon_habitat']
    homes=[model['id'] for model in library['models'] if model['kind'] in ['house','courtyard_habitat']]
    homes+=['ribbon_low'] if 'ribbon_low' in lookup else []
    for hub,district in enumerate(districts):
        cx,cy=district['centre'];density=district['density'];role=district['role'];start=len(placed)
        if role in ['core','mixed']:choices=collective;target=10 if role=='core' else 7
        elif role=='garden':choices=homes;target=5
        elif role=='food':choices=['nested_greenhouse','greenhouse_long','water_tower'];target=4
        elif role=='arrival':choices=['space_terminal','asymmetric_hangar'];target=2
        else:choices=['civic_petals','civic_workshop','community_market'];target=4
        local_rng=random.Random(district['seed'])
        for attempt in range(280):
            if len(placed)-start>=target:break
            # Stratified area samples; no identical ring of individual houses.
            angle=attempt*2.399963229728653+local_rng.random()*.4
            radius=28+(district['radius']-20)*math.sqrt(local_rng.random())
            x=cx+math.cos(angle)*radius;y=cy+math.sin(angle)*radius*.88
            name=choices[(attempt+hub)%len(choices)]
            if role in ['core','mixed'] and attempt%17==0:name='community_market'
            yaw=math.atan2(cx-x,-(cy-y))+local_rng.uniform(-.15,.15)
            add(name,x,y,yaw,role,hub)
        district['buildings']=len(placed)-start
    def prop(name,x,y,yaw=0,zone='public'):
        model=library['models'][lookup[name]];shape=footprint(model,x,y,yaw,.18)
        if max(map(abs,shape.bounds))>terrain.half-4:return False
        if any(shape.intersects(other) for other in [*lots,*props,*station_shapes]):return False
        if name not in ['solar_canopy','agri_canopy'] and (shape.intersects(clearance) or any(shape.intersects(path) for path in paths)):return False
        if shape.intersects(corridors):return False
        low,high=support(terrain,shape)
        if high-low>.3:return False
        placed.append({'id':name,'model':lookup[name],'position':[x,y,high-model['bounds_z_up'][0][2]+.04],
                       'yaw':yaw,'tint':1,'zone':zone})
        props.append(shape);return True
    for i,(cx,cy) in enumerate(hubs[:len(districts)]):
        prop('solar_canopy',cx-6,cy+2,.3*i)
        for j in range(5):
            angle=j*2.3999+i*.7
            prop('planted_bench' if j%2 else 'planted_bench_wild',cx+10*math.cos(angle),cy+10*math.sin(angle),angle+math.pi/2)
            prop('rain_garden' if j%2 else 'rain_garden_long',cx+15*math.cos(angle+.3),cy+15*math.sin(angle+.3),angle+math.pi/2)
        prop('drinking_fountain',cx+5,cy-4);prop('wayfinding_leaf',cx-3,cy-8)
        prop('petal_lamp',cx-8,cy-5);prop('service_cabinet',cx+8,cy+6)
        if districts[i]['role']=='food':
            for row in range(4):
                for col in range(7):prop('growing_bed',cx+(col-3)*5.8,cy-18-row*4,math.sin(col*.6)*.2,'agriculture')
            prop('irrigation_node',cx-24,cy-19,0,'agriculture');prop('agri_canopy',cx+21,cy-23,.3,'agriculture')
    for line in roads:
        for distance in np.arange(22,line.length-10,42):
            p=line.interpolate(distance);q=line.interpolate(distance+1);delta=np.array([q.x-p.x,q.y-p.y]);delta/=np.linalg.norm(delta)
            prop('petal_lamp',p.x-delta[1]*2.6,p.y+delta[0]*2.6,math.atan2(delta[1],delta[0]))
    # Continuous guidebeams, separated supports and cabins share one datum.
    placed.append({'id':'canopy_guideway','model':lookup['canopy_guideway'],'position':[0,0,station_z],
                   'yaw':0,'tint':1,'zone':'transport','elevated':True})
    support_shapes=[]
    for x in np.arange(-432,440,54):
        if min(abs(x-s[0]) for s in spec['stations'])<28:continue
        xx,yy=rail_point(float(x));yaw=rail_heading(float(x))
        placed.append({'id':'viaduct_ring','model':lookup['viaduct_ring'],'position':[xx,yy,station_z-23],
                       'yaw':yaw,'tint':1,'zone':'transport','elevated':True})
        support_shapes.append(Point(xx,yy).buffer(5))
        footing=translate(rotate(scale(Point(0,0).buffer(1,quad_segs=12),2.85,5.55),math.degrees(yaw),origin=(0,0)),xx,yy)
        platforms.append((footing,station_z-25+.12))
    for x,lane in [(-365,-1),(-45,1),(190,-1),(365,1)]:
        xx,yy=rail_point(x);yaw=rail_heading(x)
        placed.append({'id':'panoramic_train','model':lookup['panoramic_train'],
                       'position':[xx-math.sin(yaw)*lane*1.8,yy+math.cos(yaw)*lane*1.8,station_z],
                       'yaw':yaw,'tint':1,'zone':'transport','elevated':True,'static_preview':True})
    # Union before material partition: no doubled ribbons or dark overlaps at
    # junctions. An inset stone course tells how aggregate paths are made.
    whole=unary_union([*pathpieces,*paths,common_area]).buffer(.28,quad_segs=4).buffer(-.28,quad_segs=4).difference(garden_area).simplify(.035,preserve_topology=True)
    border=whole.difference(whole.buffer(-.18,quad_segs=4))
    inner=whole.difference(border)
    common_surface=inner.intersection(common_area.buffer(.65))
    aggregate=inner.difference(common_surface)
    occupied=unary_union([whole.buffer(.18),network.buffer(.9),*lots,*props,*station_shapes,*support_shapes])
    cell=terrain.half*2/256;origin=(-terrain.half,-terrain.half);bits=np.zeros(2048,dtype='<u4');prepared=prep(occupied)
    for y in range(256):
        for x in range(256):
            tile=box(origin[0]+x*cell,origin[1]+y*cell,origin[0]+(x+1)*cell,origin[1]+(y+1)*cell)
            if prepared.intersects(tile):bit=y*256+x;bits[bit//32]|=np.uint32(1<<(bit%32))
    slots=library['material_slots']
    report={'schema':2,'seed':seed,'planet_seed':terrain.seed,'anchor':[terrain.lat,terrain.lon],
            'terrain_sha256':terrain.digest,'library_sha256':library['library_sha256'],'masterplan':spec,
            'composition':'approved braided archipelago; stacked habitats; protected nature corridors',
            'districts':districts,'habitat_centres':hubs,'commons':[list(p.exterior.coords) for p in components(common_area)],
            'instances':placed,'rejected':rejected,'road_lines':[list(line.coords) for line in roads],
            'pedestrian_edges':edges,'grass_links':grass_links,'parcels':[list(lot.exterior.coords) for lot in lots],
            'access_paths':[list(path.exterior.coords) for path in paths],
            'foundations':[{'outline':list(shape.exterior.coords),'top':top} for shape,top in platforms],
            'connected_pedestrian_network':network.buffer(.01).geom_type=='Polygon','land_grid':[*origin,cell,1],
            'land_use':{'path_area_m2':aggregate.area,'common_surface_m2':common_surface.area,'border_m2':border.area,
                        'built_surface_fraction':unary_union([whole,*lots,*station_shapes]).area/(terrain.half*2)**2},
            'policy':{'max_foundation_relief_m':.5,'max_path_grade':.08,'water_margin_m':2,'path_width_m':[2.2,2.9],
                      'private_plots':False,'vehicle_roads':False,'minimum_building_clearance_m':.8,'protected_corridors':True},
            'transport':{'stations':3,'guideway_elevation_m':station_z,'length_m':rail.length,'vehicles':'static exterior previews'},
            'acceptance':{'art':False,'performance':False}}
    return report,[(aggregate,slots['permeable'],.045),(common_surface,slots['common_paving'],.055),(border,slots['path_border'],.065)],bits
