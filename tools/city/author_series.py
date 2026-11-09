"""Author a bounded neutral architecture series, preserving real interfaces."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import bpy
import bmesh
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
import reference_house_master as common

HERE=Path(__file__).resolve().parent


def bvh(obj):
    bm=bmesh.new();bm.from_mesh(obj.data);tree=BVHTree.FromBMesh(bm);bm.free();return tree


def mats():
    values={k:common.material('Neutral series - '+k,g,r) for k,g,r in [('shell',.63,.55),('soffit',.40,.7),('reveal',.29,.65),('glass',.19,.30),('metal',.25,.40),('solar',.33,.55),('door',.47,.65),('floor',.55,.8)]}
    for key,value in values.items():value['city_material']={'shell':'ceramic','soffit':'timber','reveal':'teal','floor':'stone','door':'timber'}.get(key,key)
    return values


def bounds(objects):
    points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]
    return [[min(p[k] for p in points) for k in range(3)],[max(p[k] for p in points) for k in range(3)]]


def smooth(t):
    t=min(1,max(0,t));return t*t*t*(10-15*t+6*t*t)


def house(asset,recipe,materials):
    source=Path(recipe['house_source']['path'])
    if common.sha(source)!=recipe['house_source']['sha256']:raise ValueError('Changed house source')
    bpy.ops.import_scene.gltf(filepath=str(source));objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    transforms={o:o.matrix_world.copy() for o in objects}
    for obj in objects:
        obj.data.transform(transforms[obj]);obj.parent=None;obj.matrix_world=Matrix.Identity(4)
    body=next(o for o in objects if o.name.startswith('Primary_shell'))
    support=bvh(body);parameters=asset['parameters']
    for obj in list(objects):
        if obj.name.startswith('Upper_fitted_sunblade'):bpy.data.objects.remove(obj,do_unlink=True)
    for i in range(parameters['fins']):
        x=5.15+2.28*i/max(1,parameters['fins']-1);y=-.15+.055*(x-4)**2-.34
        lo=[];hi=[]
        for xx,yy in [(x-.045,y-.21),(x+.045,y-.21),(x+.045,y+.21),(x-.045,y+.21)]:
            origin=Vector((xx,yy,6));a=support.ray_cast(origin,Vector((0,0,-1)),10)[0];b=support.ray_cast(origin,Vector((0,0,1)),10)[0]
            if a is None or b is None:raise ValueError('Unfitted upper blade')
            lo.append(a+Vector((0,0,.012)));hi.append(b-Vector((0,0,.012)))
        common.mesh('Upper_fitted_sunblade_'+str(i),lo+hi,[(3,2,1,0),(4,5,6,7)]+[(j,(j+1)%4,(j+1)%4+4,j+4) for j in range(4)],materials['soffit'],False)
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    # The transition lies in the solid belt, outside every inhabited pane.
    lower=max(v.co.z for o in objects if 'living_porch' in o.name for v in o.data.vertices)
    upper=min(v.co.z for o in objects if 'upper' in o.name.lower() for v in o.data.vertices)
    z0=lower+.06;z1=upper-.06
    if z1-z0<.12:raise ValueError('No clear structural band for a controlled variation')
    sx=parameters['width'];sy=parameters['depth'];uw=parameters['upper_width'];uh=parameters['upper_height'];dx=parameters['upper_shift_x'];dy=parameters['upper_shift_y'];length=z1-z0
    if min(sx,sy,uw,uh)<.6:raise ValueError('Variation exceeds the bounded family')
    def warp(p):
        t=min(1,max(0,(p.z-z0)/length));w=smooth(t);dw=30*t*t*(1-t)*(1-t)/length
        integral=0 if p.z<=z0 else (p.z-(z0+z1)*.5 if p.z>=z1 else length*(t**6-3*t**5+2.5*t**4))
        point=Vector((sx*(4.2+(p.x-4.2)*(1+(uw-1)*w)+dx*w),sy*p.y+dy*w,p.z+(uh-1)*integral))
        jac=Matrix(((sx*(1+(uw-1)*w),0,sx*dw*((uw-1)*(p.x-4.2)+dx)),(0,sy,dy*dw),(0,0,1+(uh-1)*w)))
        return point,jac
    minimum=1e9;max_shear=0
    for obj in objects:
        normals=[n.vector.copy() for n in obj.data.corner_normals];positions=[v.co.copy() for v in obj.data.vertices];matrices=[]
        for v,p in zip(obj.data.vertices,positions):
            v.co,jac=warp(p);minimum=min(minimum,jac.determinant());max_shear=max(max_shear,math.hypot(jac[0][2],jac[1][2]));matrices.append(jac.inverted().transposed())
        transformed=[(matrices[loop.vertex_index]@normal).normalized() for loop,normal in zip(obj.data.loops,normals)]
        obj.data.update();obj.data.normals_split_custom_set(transformed)
    if minimum<=0:raise ValueError('Folded variation')
    if max_shear>1.25:raise ValueError('Excessive junction shear; author a new wing instead of stretching this master')
    return [body],{'family':'house','source_sha256':common.sha(source),'transition_z_m':[z0,z1],'minimum_sampled_jacobian':minimum,
                   'maximum_junction_shear':max_shear,
                   'construction':'Positive-Jacobian shared deformation; affine glazing regions; rebuilt fitted fins','entries':[list(warp(Vector((2.05,.4,.37)))[0])]}


def facade(body,name,x0,x1,plan_y,floor,bays,materials,door_x=None,door_width=2.4,door_height=2.6,floor_line=None):
    tree=bvh(body);cuts=[x0+(x1-x0)*i/bays for i in range(bays+1)]
    if door_x is not None:cuts+= [door_x-door_width*.5,door_x,door_x+door_width*.5]
    cuts=sorted(set(round(x,7) for x in cuts));heads=[];entries=[]
    for i,(left,right) in enumerate(zip(cuts,cuts[1:])):
        if right-left<.01:continue
        yl,yr=plan_y(left),plan_y(right);top=[];bottom=[]
        doorway=door_x is not None and door_x-door_width*.5<=.5*(left+right)<=door_x+door_width*.5
        base=floor+door_height if doorway else floor
        for j in range(9):
            x=left+.012+(right-left-.024)*j/8;y=yl+(yr-yl)*(x-left)/(right-left)
            hit=tree.ray_cast(Vector((x,y,floor+.10)),Vector((0,0,1)),40)[0]
            if hit is None or hit.z<=base+.10:raise ValueError(f'Facade leaves its roof support: {name}, {x}, {y}, {hit}')
            top.append(hit-Vector((0,0,.015)));bottom.append(Vector((x,y,base)))
        common.closed_sheet(f'{name}_pane_{i}',bottom+list(reversed(top)),.026,materials['glass'])
        common.tube(f'{name}_head_{i}',top,.035,materials['metal'],False,6)
        common.tube(f'{name}_stile_{i}',[Vector((left,yl,floor)),top[0]],.035,materials['metal'],False,6)
        if floor_line is not None and min(p.z for p in top)>floor_line+.12:
            common.tube(f'{name}_floor_band_{i}',[Vector((left,yl,floor_line)),Vector((right,yr,floor_line))],.075,materials['soffit'],False,8)
        if doorway:
            leaf=[Vector((left+.015,yl+.035,floor)),Vector((right-.015,yr+.035,floor)),Vector((right-.015,yr+.035,base)),Vector((left+.015,yl+.035,base))]
            common.closed_sheet(f'{name}_sliding_leaf_{i}',leaf,.04,materials['glass'])
            common.tube(f'{name}_door_head_{i}',[Vector((left,yl,base)),Vector((right,yr,base))],.055,materials['metal'],False,8)
    if door_x is not None:
        p=Vector((door_x+door_width*.5+.16,plan_y(door_x+door_width*.5+.16)-.045,floor+1.1))
        common.tube(name+'_opening_control',[p,p+Vector((0,0,.36))],.025,materials['metal'],False,6)
        entries.append([door_x,plan_y(door_x),floor])
    # Complete the narrow end bays against the actual structural aperture.
    # A fitted head alone leaves an unsealed wedge beside a curved jamb.
    for side,x,direction in [('left',x0,-1),('right',x1,1)]:
        y=plan_y(x);roof=tree.ray_cast(Vector((x,y,floor+.12)),Vector((0,0,1)),40)[0]
        if roof is None:raise ValueError('Missing facade edge support')
        edge=[]
        for j in range(49):
            z=floor+.025+(roof.z-floor-.055)*j/48
            hit,normal,_,_=tree.ray_cast(Vector((x,y,z)),Vector((direction,0,0)),10)
            if hit is None or normal.x*direction>=0:continue
            if (hit.x-x)*direction<.004:continue
            edge.append(Vector((hit.x+direction*.008,y,z)))
        if len(edge)<3:continue
        contour=[Vector((x,y,edge[0].z))]+edge+[Vector((x,y,edge[-1].z))]
        common.closed_sheet(name+'_fitted_end_'+side,contour,.026,materials['glass'])
        common.tube(name+'_jamb_seal_'+side,edge,.025,materials['metal'],False,6)
    return entries


def staircase(name,center,width,start,end,base,top,materials):
    count=math.ceil((top-base)/.18);tread=(end-start)/count;rise=(top-base)/count
    profile=[(start,base),(start,base+rise)]
    for j in range(1,count):profile.extend([(start+j*tread,base+j*rise),(start+j*tread,base+(j+1)*rise)])
    profile.extend([(end,top),(end,base)]);n=len(profile)
    vertices=[(x,y,z) for x in [center-width*.5,center+width*.5] for y,z in profile]
    faces=[tuple(reversed(range(n))),tuple(n+i for i in range(n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return common.mesh(name,vertices,faces,materials['floor'],False)


def fitted_steps(name,contour,center,width,top,materials):
    """Sweep shared risers into the actual chamfered terrace outline."""
    count=math.ceil(top/.15);rise=top/count;tread=.44
    profile=[(-count*tread,0),(-count*tread,rise)]
    for i in range(1,count):profile.extend([(-(count-i)*tread,i*rise),(-(count-i)*tread,(i+1)*rise)])
    profile.extend([(0,top),(0,0)]);n=len(profile)
    outline=common.spline(contour,128);middle=sum(outline,Vector((0,0)))/len(outline)
    outline=[middle+(q-middle)*.994 for q in outline];vertices=[];faces=[]
    for i in range(33):
        x=center-width*.5+width*i/32;hits=[]
        for a,b in zip(outline,outline[1:]+outline[:1]):
            if min(a.x,b.x)<=x<max(a.x,b.x):hits.append(a.y+(b.y-a.y)*(x-a.x)/(b.x-a.x))
        if not hits:raise ValueError('Approach leaves its terrace')
        vertices.extend((x,min(hits)+dy,z) for dy,z in profile)
    for j in range(32):faces.extend((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for i in range(n))
    faces.extend([tuple(reversed(range(n))),tuple(32*n+i for i in range(n))])
    return common.mesh(name,vertices,faces,materials['floor'],False)


def civic(asset,domain,materials):
    p=asset['parameters'];data=domain['domain'];config=domain['config'];body,loops=common.structure(data,config,materials)
    body.name='Civic_shared_shells_and_forum';sx=p['width'];entries=[]
    # Transverse openings remove the heavy blind end walls while preserving
    # the front/rear load paths. Each pane occupies the real boolean aperture.
    sy=p['depth_m']/11;sz=p['height']
    config['lateral_apertures']=[]
    for name,near,far,plane,profile in [
        ('Civic_left_window',-20,-12,-15.9,[(-1.6,1.2),(-1.5,5.4),(.2,6.1),(3.3,5.5),(3.5,1.2)]),
        ('Civic_right_window',12,20,15.9,[(-1.5,1.2),(-1.4,3.8),(.2,4.7),(3.2,4.1),(3.4,1.2)])]:
        config['lateral_apertures'].append({'name':name,'min_x':near*sx,'max_x':far*sx,'glazing_x':plane*sx,
            'profile_yz':[[y*sy,z*sz] for y,z in profile]})
    cuts=common.lateral_apertures(body,config,materials)
    for side,span,door in [('left',(-13.8,-5.9),-9.7),('right',(7.9,14.25),11.1)]:
        def front_y(x):
            xx=x/sx;return -2.15-2*math.exp(-((xx+10)/5)**2)-1.3*math.exp(-((xx-11)/4)**2)
        entries+=facade(body,side+'_front',span[0]*sx,span[1]*sx,front_y,.38,p['bays'],materials,door*sx,2.3,2.6,p['gallery_z'])
        facade(body,side+'_rear',span[0]*sx*.93,span[1]*sx*.93,lambda x:p['depth_m']*.5-.004*x*x-1.1,.38,p['bays'],materials,floor_line=p['gallery_z'])
    tree=bvh(body);height=p['gallery_z'];y0=1.8;y1=3.7;ys=[y0+(y1-y0)*i/8 for i in range(9)];left=[];right=[]
    for y in ys:
        origin=Vector((0,y,height-.1));a=tree.ray_cast(origin,Vector((-1,0,0)),30)[0];b=tree.ray_cast(origin,Vector((1,0,0)),30)[0]
        if a is None or b is None:raise ValueError('Gallery lacks structural support')
        left.append((a.x-.025,y));right.append((b.x+.025,y))
    common.deck('Forum_gallery_with_fitted_ends',left+list(reversed(right)),height-.23,height,materials['floor'])
    stair_center=(left[0][0]+right[0][0])*.5;stair_width=min(4.5,(right[0][0]-left[0][0])*.62)
    staircase('Forum_public_stair',stair_center,stair_width,y0-(height-.36)*1.95,y0,.36,height,materials)
    for label,a,b in [('left',left[0][0]+.10,stair_center-stair_width*.5-.04),('right',stair_center+stair_width*.5+.04,right[0][0]-.10)]:
        points=[Vector((a,y0,height+.08)),Vector((b,y0,height+.08)),Vector((b,y0,height+1.05)),Vector((a,y0,height+1.05))]
        common.closed_sheet('Gallery_balustrade_'+label,points,.035,materials['glass'])
        common.tube('Gallery_rail_'+label,[points[3],points[2]],.04,materials['metal'],False,8)
    rear=[Vector((left[-1][0]+.10,y1,height+.08)),Vector((right[-1][0]-.10,y1,height+.08)),
          Vector((right[-1][0]-.10,y1,height+1.05)),Vector((left[-1][0]+.10,y1,height+1.05))]
    common.closed_sheet('Gallery_rear_balustrade',rear,.035,materials['glass'])
    common.tube('Gallery_rear_rail',[rear[3],rear[2]],.04,materials['metal'],False,8)
    for side in [-1,1]:
        x=stair_center+side*(stair_width*.5-.08);start=y0-(height-.36)*1.95
        contour=[Vector((start+.1,x,.60)),Vector((y0,x,height+.12)),Vector((y0,x,height+1.05)),Vector((start+.1,x,1.41))]
        panel=common.closed_sheet('Stair_balustrade_'+str(side),contour,.035,materials['glass'])
        for v in panel.data.vertices:v.co.x,v.co.y=v.co.y,v.co.x
        common.tube('Stair_continuous_rail_'+str(side),[Vector((x,start+.1,1.41)),Vector((x,y0,height+1.05))],.04,materials['metal'],False,8)
    terrace=[(-17.6*sx,-6.7),(-12*sx,-7.9),(-3*sx,-7.4),(5*sx,-6.7),(16.8*sx,-5.8),(18*sx,1.5),(16*sx,p['depth_m']*.5+.9),(-15.8*sx,p['depth_m']*.5+.9),(-18*sx,1.5)]
    common.deck('Shared_public_terrace',terrace,-.14,.36,materials['floor'])
    fitted_steps('Public_approach_steps',terrace,0,8*sx,.36,materials)
    return [body],{'family':'civic','construction':'Single continuous three-aperture structural domain; fitted public gallery and entrances','entries':entries,'gallery_z':height,'lateral_apertures':cuts}


def open_spline(points,t):
    n=len(points)-1;s=min(n-1e-9,max(0,t*n));i=int(s);s-=i
    a,b,c,d=[Vector(points[min(n,max(0,k))]) for k in [i-1,i,i+1,i+2]]
    return (2*b+(-a+c)*s+(2*a-5*b+4*c-d)*s*s+(-a+3*b-3*c+d)*s*s*s)*.5


def greenhouse(asset,domain,materials):
    p=asset['parameters'];w=p['width'];h=p['height'];length=p['length_m']
    arch=[(-9,.37),(-8.9,3.0),(-6.4,6.8),(-2.6,8.05),(.3,7.25),(2.9,5.95),(6.5,5.3),(8.9,3.1),(9.1,.37)]
    def surface(u,v):
        a=open_spline(arch,u);scale=1-.10*v+.055*math.sin(math.tau*v)
        x=w*a.x*scale+.65*math.sin(math.pi*v);z=.37+(a.y-.37)*h+.65*math.sin(math.pi*v)*math.sin(math.pi*u)**2
        y=(v-.5)*length+.004*x*x*(1-2*v)
        return Vector((x,y,z))
    def normal(u,v):
        a=surface(min(1,u+.0001),v)-surface(max(0,u-.0001),v)
        b=surface(u,min(1,v+.0001))-surface(u,max(0,v-.0001))
        return a.cross(b).normalized()
    def sheet(name,data,thickness,mat):
        uv=data['vertices'];count=len(uv);vertices=[]
        for direction in [-.5,.5]:vertices.extend(surface(u,v)+normal(u,v)*thickness*direction for u,v in uv)
        faces=[tuple(reversed(t)) for t in data['faces']]+[tuple(i+count for i in t) for t in data['faces']]
        faces.extend((a,b,b+count,a+count) for a,b in data['boundary'])
        return common.mesh(name,vertices,faces,mat)
    body=sheet('Greenhouse_continuous_frame_and_ridge',domain['frame'],.28,materials['shell'])
    transparent=common.material('Neutral conservatory glass',.58,.12);transparent['city_material']='glass'
    transparent.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value=.62
    transparent.node_tree.nodes['Principled BSDF'].inputs['IOR'].default_value=1.45
    for i,pane in enumerate(domain['panes']):sheet('Fitted_roof_glass_'+str(i),pane,.026,transparent)
    def plan_front(x):return -length*.5+.004*x*x+.24
    entries=facade(body,'Conservatory_front',-8.3*w,8.3*w,plan_front,.40,8,materials,0,2.65,2.75)
    facade(body,'Conservatory_rear',-7.3*w,7.6*w,lambda x:length*.5-.004*x*x-.24,.40,8,materials,0,2.65,2.75)
    foundation=[(-9.5*w,-length*.5-.7),(0,-length*.5-.9),(9.8*w,-length*.5-.7),(9.2*w,length*.5+.6),(0,length*.5+.8),(-8.7*w,length*.5+.6)]
    common.deck('Greenhouse_foundation',foundation,-.14,.38,materials['floor'])
    fitted_steps('Greenhouse_entry_steps',foundation,0,4.6,.38,materials)
    # Formed cultivation troughs, with real inner walls and shared rims.
    for side in [-1,1]:
        for j in range(p['length_bays']):
            x=side*4.4*w;y=-length*.5+2+(length-4)*(j+.5)/p['length_bays'];half=(length-4)/p['length_bays']*.40
            outline=[(x-1.5*w,y-half),(x+1.5*w,y-half),(x+1.5*w,y+half),(x-1.5*w,y+half)]
            outer=common.spline(outline,32);inner=[Vector((x,y))+(q-Vector((x,y)))*.92 for q in outer];n=len(outer)
            vs=[(q.x,q.y,z) for line,z in [(outer,.38),(outer,1.0),(inner,1.0),(inner,.85)] for q in line]
            fs=[]
            for k in range(3):fs.extend((k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i) for i in range(n))
            fs.extend([tuple(reversed(range(n))),tuple(3*n+i for i in range(n))])
            common.mesh(f'Formed_cultivation_trough_{side}_{j}',vs,fs,materials['floor'])
    return [body],{'family':'greenhouse','construction':'One curved parameter-domain frame with real panel apertures and conforming glazing','entries':entries,'roof_panes':len(domain['panes'])}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recipe',type=Path,required=True);p.add_argument('--asset',required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);args.out=args.out.resolve();args.out.mkdir(parents=True,exist_ok=True)
    recipe=json.loads(args.recipe.read_text(encoding='utf-8'));asset=next(x for x in recipe['assets'] if x['id']==args.asset)
    reference=recipe['references'][asset['family']]
    if common.sha(reference['path'])!=reference['sha256']:raise ValueError('Changed original reference')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);materials=mats()
    if asset['family']=='house':bodies,construction=house(asset,recipe,materials)
    else:
        subprocess.run(['C:/Python313/python.exe',str(HERE/'series_domain.py'),'--recipe',str(args.recipe.resolve()),'--asset',asset['id'],'--out',str(args.out/'domain.json')],check=True,creationflags=0x08000000)
        domain=json.loads((args.out/'domain.json').read_text());bodies,construction=(civic if asset['family']=='civic' else greenhouse)(asset,domain,materials)
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    common.prepare_meshes(objects,bodies)
    audit=common.topology(objects);failures=[x for x in audit if x['components']!=1 or x['nonmanifold_edges'] or x['zero_faces']]
    if failures:raise ValueError('Series source topology: '+json.dumps(failures))
    triangles=0
    for obj in objects:
        obj.data.calc_loop_triangles();triangles+=len(obj.data.loop_triangles);obj['city_construction']='shared_surface_or_fitted_part';obj['asset_id']=asset['id']
    if triangles>recipe['master_triangle_ceiling']:raise ValueError('Unbounded neutral master')
    bpy.ops.wm.save_as_mainfile(filepath=str(args.out/'master.blend'));bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=str(args.out/'master.glb'),export_format='GLB',use_selection=True,export_extras=True,export_cameras=False,export_lights=False)
    tools={name:common.sha(HERE/name) for name in ['author_series.py','series_domain.py','reference_house_master.py','reference_house_domain.py','profile_domain.py']}
    report={'id':asset['id'],'label':asset['label'],'family':asset['family'],'recipe':asset,'recipe_sha256':common.sha(args.recipe),'reference':reference,
            'tool_hashes':tools,'master_sha256':common.sha(args.out/'master.glb'),'construction':construction,'triangles':triangles,'objects':len(objects),
            'bounds':bounds(objects),'topology':audit,'topology_passed':True,'art_accepted':False,'performance_accepted':False,'textures':0,'lods_generated':False,
            'lineage':'Directed parametric architecture; neutral series; zero neural vertices','source_budget_stage':'Unreduced master, not game LOD0'}
    (args.out/'source.json').write_text(json.dumps(report,indent=2)+'\n');(args.out/'recipe.json').write_text(json.dumps(asset,indent=2)+'\n')
    snapshot=args.out/'authoring';snapshot.mkdir(exist_ok=True)
    for name in tools:shutil.copy2(HERE/name,snapshot/name)
    print('SERIES_SOURCE',asset['id'],triangles,'triangles',len(objects),'parts',flush=True)


if __name__=='__main__':main()
