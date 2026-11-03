from pathlib import Path
import json
import argparse
import sys
import math
import random
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from branch_volume import measure as branch_volume

parser = argparse.ArgumentParser(description='Cook a generated woody mesh and leaf cutout into a bounded game asset.')
parser.add_argument('--wood', type=Path, required=True)
parser.add_argument('--leaf', type=Path, required=True)
parser.add_argument('--recipe', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
recipe = json.loads(args.recipe.read_text(encoding='utf8'))
(out / 'assembly-recipe.json').write_text(json.dumps(recipe, indent=2) + '\n')
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(args.wood))
wood = [o for o in bpy.context.scene.objects if o.type == 'MESH']
assert len(wood) == 1
wood = wood[0]; wood.name = recipe['name']+' - generated wood and roots'
bpy.context.view_layer.objects.active = wood
bpy.ops.object.select_all(action='DESELECT'); wood.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# UV seams duplicate vertices. Establish connectivity by coincident positions.
coords = np.array([v.co[:] for v in wood.data.vertices], dtype=np.float32)
tri = np.array([p.vertices[:] for p in wood.data.polygons], dtype=np.int32)
assert tri.shape[1] == 3
_, inverse = np.unique(np.round(coords, 7), axis=0, return_inverse=True)
parent = np.arange(int(inverse.max()) + 1)
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]; i = parent[i]
    return i
for a, b, c in inverse[tri]:
    a, b, c = find(a), find(b), find(c)
    parent[b] = a; parent[c] = a
roots = np.array([find(i) for i in range(len(parent))])
face_roots = roots[inverse[tri[:, 0]]]
areas = np.linalg.norm(np.cross(coords[tri[:, 1]] - coords[tri[:, 0]], coords[tri[:, 2]] - coords[tri[:, 0]]), axis=1)
main = int(np.bincount(face_roots, weights=areas).argmax())
keep = face_roots == main
removed = int((~keep).sum())
retained_area = float(areas[keep].sum() / areas.sum())
if retained_area < 0.9:
    raise ValueError('Generated wood is too fragmented: manual review required before automatic cleanup')
if removed:
    bm = bmesh.new(); bm.from_mesh(wood.data); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.flatnonzero(~keep)], context='FACES')
    bm.to_mesh(wood.data); bm.free(); wood.data.update()
coords = np.array([v.co[:] for v in wood.data.vertices], dtype=np.float32)
lo, hi = coords.min(axis=0), coords.max(axis=0)
band = coords[(coords[:, 2] > lo[2] + 0.06 * (hi[2] - lo[2])) & (coords[:, 2] < lo[2] + 0.18 * (hi[2] - lo[2]))]
origin = np.array([*np.median(band[:, :2], axis=0), lo[2]])
scale = recipe['height_m'] / float(hi[2] - lo[2])
for v in wood.data.vertices: v.co = Vector((np.array(v.co[:]) - origin) * scale)
wood.data.update()
coords = np.array([v.co[:] for v in wood.data.vertices], dtype=np.float32)
tri = np.array([p.vertices[:] for p in wood.data.polygons], dtype=np.int32)
volume=branch_volume((coords[:,[0,2,1]]*np.array([1,1,-1]))[tri])
(out/'branch-volume.json').write_text(json.dumps(volume,indent=2)+'\n')
if volume['status']!='pass':
    raise ValueError('Woody structure is too planar; regenerate branches around the trunk before assembling foliage')
centers = coords[tri].mean(axis=1)
normal = np.cross(coords[tri[:, 1]] - coords[tri[:, 0]], coords[tri[:, 2]] - coords[tri[:, 0]])
area = np.linalg.norm(normal, axis=1)
normal /= np.maximum(area[:, None], 1e-12)
radial = np.linalg.norm(centers[:, :2], axis=1)
eligible = (centers[:, 2] > recipe.get('min_foliage_height',.34) * recipe['height_m']) & (radial > recipe['height_m']*.0525) & (normal[:, 2] > -0.45) & (area > 1e-10)
ids = np.flatnonzero(eligible)
assert len(ids) > 20
weights = area[ids] * (0.5 + radial[ids]) * np.sqrt(centers[ids, 2] / recipe['height_m'])
weights /= weights.sum()
wood_bvh=BVHTree.FromPolygons(coords.tolist(),tri.tolist(),all_triangles=True)
rng = np.random.default_rng(recipe['seed'])
anchors = []; targets = []; grid = {}; distance = recipe.get('cluster_spacing_m',recipe.get('min_anchor_distance_m',0.4))
wood_triangles = len(tri)
limit = min(recipe['cluster_limit'], (recipe['max_triangles'] - wood_triangles) // 76)
mode = recipe.get('foliage_distribution','crown_volume')
upper = coords[coords[:,2] > recipe['height_m']*.4]
center = np.array([*(upper[:,:2].min(axis=0)+upper[:,:2].max(axis=0))*.5, recipe['height_m']*recipe.get('crown_centre',.69)])
radii = np.array([*(upper[:,:2].max(axis=0)-upper[:,:2].min(axis=0))*.57, recipe['height_m']*recipe.get('crown_depth',.30)])
shape_phase = (recipe['seed'] % 1009) / 1009 * math.tau
for attempt in range(50000):
    if mode == 'crown_volume':
        sphere = rng.uniform(-1,1,3)
        if np.dot(sphere,sphere)>1:continue
        angle = math.atan2(sphere[1],sphere[0])
        sphere[:2] *= 1 + .10*math.sin(3*angle+shape_phase) + .06*math.cos(5*angle-shape_phase)
        if recipe.get('crown_profile')=='cone':sphere[:2]*=1.15-.85*((sphere[2]+1)*.5)
        pt = center + sphere*radii
        pt[2] += .025*recipe['height_m']*math.sin(2*angle+shape_phase)*(1-sphere[2]**2)
        nearest = int(np.argmin(np.sum((centers[ids]-pt)**2,axis=1))); anchor = centers[ids[nearest]]
        span = np.linalg.norm(pt-anchor)
        if not recipe['height_m']*.03125 < span < recipe.get('max_connector_m',recipe['height_m']*.275):continue
        way=Vector((pt-anchor).tolist()).normalized()
        hit=wood_bvh.ray_cast(Vector(anchor.tolist())+way*.02,way,float(span))
        if hit[0] is not None and hit[3]>.04:continue
    else:
        fid = rng.choice(ids,p=weights);u,v = rng.random(2)
        if u+v>1:u,v=1-u,1-v
        pt = coords[tri[fid,0]]*(1-u-v)+coords[tri[fid,1]]*u+coords[tri[fid,2]]*v
        anchor=pt
    cell = tuple(np.floor(pt/distance).astype(int))
    nearby = [q for dx in [-1,0,1] for dy in [-1,0,1] for dz in [-1,0,1]
              for q in grid.get((cell[0]+dx,cell[1]+dy,cell[2]+dz),[])]
    if any(np.linalg.norm(pt-q)<distance for q in nearby):continue
    anchors.append(anchor);targets.append(pt);grid.setdefault(cell,[]).append(pt)
    if len(anchors)>=limit:break
assert anchors

image = bpy.data.images.load(str(args.leaf), check_existing=True)
rgba = np.array(image.pixels[:], dtype=np.float32).reshape(image.size[1], image.size[0], 4)
# Extend edge colour into transparent texels before texture filtering.
known = rgba[:,:,3] > 0.1
for step in range(8):
    expanded = known.copy()
    for dy, dx in [(0,1),(0,-1),(1,0),(-1,0)]:
        y0,y1=max(0,dy),min(len(known),len(known)+dy)
        x0,x1=max(0,dx),min(known.shape[1],known.shape[1]+dx)
        target=rgba[y0:y1,x0:x1,:3]; source=rgba[y0-dy:y1-dy,x0-dx:x1-dx,:3]
        take=(~expanded[y0:y1,x0:x1]) & known[y0-dy:y1-dy,x0-dx:x1-dx]
        target[take]=source[take];expanded[y0:y1,x0:x1] |= take
    known=expanded
image.pixels.foreach_set(rgba.ravel());image.filepath_raw=str(out/'leaf-padded.png');image.file_format='PNG';image.save()
ys, xs = np.where(rgba[:,:,3] > 0.75)
root_y = int(ys.min()); root_x = float(np.median(xs[ys < root_y + max(2, image.size[1]*0.015)]))
root_uv = ((root_x+0.5)/image.size[0], (root_y+0.5)/image.size[1])
uv_min = (xs.min()/image.size[0], ys.min()/image.size[1]); uv_max = ((xs.max()+1)/image.size[0], (ys.max()+1)/image.size[1])
mat = bpy.data.materials.new(recipe['name']+' leaves and twigs'); mat.use_nodes=True; mat.use_backface_culling=False; mat.surface_render_method='DITHERED'
bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=0.82;bs.inputs['Metallic'].default_value=0
tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image
cut=mat.node_tree.nodes.new('ShaderNodeMath');cut.operation='GREATER_THAN';cut.inputs[1].default_value=0.4
colour=mat.node_tree.nodes.new('ShaderNodeVertexColor');colour.layer_name='FoliageTint'
multiply=mat.node_tree.nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=1
mat.node_tree.links.new(tex.outputs['Color'],multiply.inputs[1]);mat.node_tree.links.new(colour.outputs['Color'],multiply.inputs[2]);mat.node_tree.links.new(multiply.outputs[0],bs.inputs['Base Color'])
mat.node_tree.links.new(tex.outputs['Alpha'],cut.inputs[0]);mat.node_tree.links.new(cut.outputs[0],bs.inputs['Alpha'])
verts=[];faces=[];uvs=[];normals=[];pivots=[];phases=[];wind=[];leaf_pivots=[];leaf_weights=[];tints=[]
def vertex(point, uv, normal, pivot, phase, weight, lpivot, lweight, tint):
    verts.append(point);uvs.append(uv);normals.append(normal);pivots.append(pivot[:]);phases.append(phase);wind.append(weight);leaf_pivots.append(lpivot[:]);leaf_weights.append(lweight);tints.append((*tint,1))
for index, anchor in enumerate(anchors):
    pivot=Vector(anchor);radial_v=Vector((anchor[0],anchor[1],0)).normalized();growth=(radial_v*0.8+Vector((0,0,recipe.get('shoot_upward_bias',0.25)))).normalized()
    near=coords[np.sum((coords-anchor)**2,axis=1)<(recipe['height_m']*.04375)**2]
    if len(near)>6:
        _,eigen=np.linalg.eigh(np.cov(near.T));direction=Vector(eigen[:,-1])
        if direction.dot(growth)<0:direction=-direction
        alignment=recipe.get('branch_alignment',0.25)
        growth=(direction*alignment+growth*(1-alignment)+Vector((0,0,0.05))).normalized()
    if mode == 'crown_volume':growth=(Vector(targets[index])-pivot).normalized()
    side=growth.cross(Vector((0,0,1)))
    if side.length<0.1:side=growth.cross(Vector((1,0,0)))
    side.normalize();across=growth.cross(side).normalized();length=float(rng.uniform(*recipe['shoot_length_m']));phase=float(rng.uniform(0,2*math.pi))
    if mode == 'crown_volume':length=(Vector(targets[index])-pivot).length+recipe['height_m']*.0375
    hit=wood_bvh.ray_cast(pivot+growth*.025,growth,length)
    if hit[0] is not None and hit[3]>.04:length=min(length,max(.08,hit[3]-.04))
    def stem(t):return pivot+growth*(length*t)+Vector((0,0,0.09*length*t*t))
    first=len(verts)
    for row in range(4):
        t=row/3;radius=(0.008*(1-t)+0.0018*t)*recipe['height_m']/8
        for s in range(4):
            angle=s*math.pi/2;n=side*math.cos(angle)+across*math.sin(angle);point=stem(t)+n*radius
            uv=(root_uv[0]+math.cos(angle)*0.002,root_uv[1]+0.025+t*0.012)
            vertex(point,uv,n,pivot,phase,t*0.6,point,0,(1,1,1))
    for row in range(3):
        for s in range(4):
            a=first+row*4+s;b=first+row*4+(s+1)%4;c=a+4;d=b+4;faces.extend([(a,b,d),(a,d,c)])
    faces.extend([(first,first+2,first+1),(first,first+3,first+2),(first+12,first+13,first+14),(first+12,first+14,first+15)])
    for leaf_index in range(12):
        t=(leaf_index+0.6)/12.5
        if mode == 'crown_volume':t=.45+.55*t
        leaf_root=stem(t);azimuth=leaf_index*2.399963+phase
        if recipe.get('leaf_arrangement')=='opposite':
            t=(leaf_index//2+.6)/6.5;leaf_root=stem(t);azimuth=(leaf_index%2)*math.pi+(leaf_index//2)*2.399963+phase
        outward=side*math.cos(azimuth)+across*math.sin(azimuth)
        axis=(outward*0.8+growth*0.25+Vector((0,0,0.4))).normalized()
        front=Vector((0,0,1))+radial_v*0.25;front=(front-axis*front.dot(axis)).normalized();right=axis.cross(front).normalized()
        leaf_length=float(rng.uniform(*recipe['leaf_length_m']));unit=leaf_length/(uv_max[1]-uv_min[1]);first=len(verts)
        shade=float(rng.uniform(0.78,1));tint=(shade*0.86,shade,shade*0.86)
        for iy in range(3):
            v=uv_min[1]+(uv_max[1]-uv_min[1])*iy/2
            for ix in range(2):
                u=uv_min[0]+(uv_max[0]-uv_min[0])*ix;x=(u-root_uv[0])*unit;y=(v-root_uv[1])*unit
                bend=leaf_length*0.09*math.sin(math.pi*iy/2);point=leaf_root+right*x+axis*y+front*bend
                n=(front+axis*(iy/2-0.4)*0.3+right*(ix-0.5)*0.2).normalized()
                vertex(point,(u,v),n,pivot,phase,t*0.6,leaf_root,max(0,iy/2),tint)
        faces.extend([(first,first+1,first+3),(first,first+3,first+2),(first+2,first+3,first+5),(first+2,first+5,first+4)])
mesh=bpy.data.meshes.new('Individual leaves on supported shoots');mesh.from_pydata(verts,[],faces);mesh.update()
leaves=bpy.data.objects.new(recipe['name']+' - deformable foliage',mesh);bpy.context.collection.objects.link(leaves);mesh.materials.append(mat)
layer=mesh.uv_layers.new(name='UVMap')
for loop in mesh.loops:layer.data[loop.index].uv=uvs[loop.vertex_index]
for poly in mesh.polygons:poly.use_smooth=True
mesh.normals_split_custom_set_from_vertices(normals)
for name,kind,values,prop in [('_WIND_WEIGHT','FLOAT',wind,'value'),('_WIND_PHASE','FLOAT',phases,'value'),('_WIND_PIVOT','FLOAT_VECTOR',pivots,'vector'),('_LEAF_PIVOT','FLOAT_VECTOR',leaf_pivots,'vector'),('_LEAF_WEIGHT','FLOAT',leaf_weights,'value')]:
    a=mesh.attributes.new(name,kind,'POINT');a.data.foreach_set(prop,np.array(values,dtype=np.float32).ravel())
c=mesh.color_attributes.new(name='FoliageTint',type='FLOAT_COLOR',domain='POINT');c.data.foreach_set('color',np.array(tints,dtype=np.float32).ravel())
leaves['wind_description']='Shoot bending: _WIND_PIVOT, _WIND_WEIGHT, _WIND_PHASE. Individual leaf flutter: _LEAF_PIVOT, _LEAF_WEIGHT.'
wood['provenance']='Local FLUX references; '+recipe['geometry_backend']+'; native remesh, reduction, UV and material baking.'
assert len(mesh.polygons)+len(wood.data.polygons)<=recipe['max_triangles']

# Normalize final canopy height and convert custom pivot coordinates for export.
maximum = max(v.co.z for obj in [wood, leaves] for v in obj.data.vertices)
final_scale = recipe['height_m'] / maximum
for obj in [wood, leaves]:
    for v in obj.data.vertices: v.co *= final_scale
for name in ['_WIND_PIVOT', '_LEAF_PIVOT']:
    attr = mesh.attributes[name]
    for item in attr.data: item.vector *= final_scale
pivot_backup = {}
for name in ['_WIND_PIVOT', '_LEAF_PIVOT']:
    attr = mesh.attributes[name]
    values = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    attr.data.foreach_get('vector', values); values = values.reshape(-1,3)
    pivot_backup[name] = values.copy()
    values = values[:,[0,2,1]]; values[:,2] *= -1
    attr.data.foreach_set('vector', values.ravel())
bpy.ops.object.select_all(action='DESELECT'); wood.select_set(True); leaves.select_set(True); bpy.context.view_layer.objects.active = wood
dest = out / 'plant.glb'
bpy.ops.export_scene.gltf(filepath=str(dest), export_format='GLB', use_selection=True,
                          export_apply=False, export_attributes=True, export_vertex_color='ACTIVE', export_all_vertex_colors=False, export_tangents=True, export_animations=False)

for name, values in pivot_backup.items(): mesh.attributes[name].data.foreach_set('vector',values.ravel())

scene = bpy.context.scene; scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = 16; scene.cycles.transparent_max_bounces = 64; scene.view_settings.exposure = -0.4; scene.cycles.use_denoising = True
scene.render.threads_mode = 'FIXED'; scene.render.threads = 4; scene.render.resolution_x = 960; scene.render.resolution_y = 960
scene.render.image_settings.file_format = 'PNG'; scene.view_settings.view_transform = 'AgX'
scene.world.use_nodes = True; scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.25,.25,.25,1); scene.world.node_tree.nodes['Background'].inputs[1].default_value = .6
bpy.ops.mesh.primitive_plane_add(size=100,location=(0,0,-0.02)); floor=bpy.context.object; floor.name='Review floor'
floor_mat = bpy.data.materials.new('Review floor'); floor_mat.diffuse_color=(.14,.14,.14,1); floor.data.materials.append(floor_mat)
for name, loc, power, size in [('Key',(-5,-7,11),1800,6),('Fill',(5,-2,7),650,5),('Rim',(2,6,10),1600,5)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=loc;obj.rotation_euler=(Vector((0,0,4))-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Review camera'); camera=bpy.data.objects.new('Review camera',data);scene.collection.objects.link(camera);scene.camera=camera;data.type='ORTHO';data.ortho_scale=11
target=Vector((0,0,4.3));camera.location=target+Vector((16,-16,3));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.wm.save_as_mainfile(filepath=str(out/'review.blend'))
scene.render.filepath=str(out/'quarter.png');bpy.ops.render.render(write_still=True)
report={'wood_triangles':len(wood.data.polygons),'leaf_triangles':len(mesh.polygons),'total_triangles':len(wood.data.polygons)+len(mesh.polygons),'wood_vertices':len(wood.data.vertices),'leaf_vertices':len(mesh.vertices),'clusters':len(anchors),'foliage_distribution':mode,'discarded_disconnected_wood_faces':removed,'retained_wood_surface_fraction':retained_area,'source_height_scale':scale*final_scale,'final_height_m':recipe['height_m'],'leaf_count':len(anchors)*12,'pivot_coordinate_space':'glTF Y-up; Blender Z-up in review.blend','root_uv':root_uv,'leaf_transparency_fraction':float((rgba[:,:,3]<0.1).mean()),'asset':str(dest),'preview':scene.render.filepath,'wind_attributes':['_WIND_WEIGHT','_WIND_PHASE','_WIND_PIVOT','_LEAF_PIVOT','_LEAF_WEIGHT'],'leaf_representation':'Individual curved leaf cutouts on small 3D shoots, with shoot and leaf pivots.'}
(out/'assembly-report.json').write_text(json.dumps(report,indent=2)+'\n');print('EXOLUNE_ASSEMBLY',json.dumps(report),flush=True)
