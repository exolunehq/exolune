"""Experimental tropical wood: neural trunk, radial branches and unified PBR bake.

Run in background Blender. This fixed eight-metre authoring profile is a witness,
not a general botanical generator. Topology, volume, art and native gates remain
mandatory. Source data stays untouched and outputs require a fresh directory.
"""
from pathlib import Path
import argparse,json,math,sys,hashlib,random
import bpy,bmesh
from mathutils import Vector
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--seed',type=int,default=71303);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.out.mkdir(parents=True,exist_ok=False);rng=random.Random(a.seed)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=str(a.source));trunk=next(o for o in bpy.context.scene.objects if o.type=='MESH');bpy.context.view_layer.objects.active=trunk;trunk.select_set(True);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
lo=min(v.co.z for v in trunk.data.vertices);h=max(v.co.z for v in trunk.data.vertices)-lo
for v in trunk.data.vertices:v.co=(v.co-Vector((0,0,lo)))*8/h
bm=bmesh.new();bm.from_mesh(trunk.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-5);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));cut=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,2.45),plane_no=(0,0,1),clear_outer=True);edges=[e for e in cut['geom_cut'] if isinstance(e,bmesh.types.BMEdge) and e.is_boundary]
if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
bm.to_mesh(trunk.data);bm.free();trunk.name='Neural trunk and roots'
trunk.data.validate();trunk.data.update()
cap=[v.co for v in trunk.data.vertices if abs(v.co.z-2.45)<.005]
attachment=Vector((sorted(v.x for v in cap)[len(cap)//2],sorted(v.y for v in cap)[len(cap)//2],0))
print('ATTACHMENT',attachment[:],flush=True)
for v in trunk.data.vertices:
 t=max(0,min(1,(v.co.z-1.7)/.75));t=t*t*(3-2*t);v.co.x=attachment.x+(v.co.x-attachment.x)*(1-.35*t);v.co.y=attachment.y+(v.co.y-attachment.y)*(1-.35*t)
trunk.data.update()
mat=bpy.data.materials.new('Metric branch bark');mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;bs=n.get('Principled BSDF');bs.inputs['Roughness'].default_value=.88;uv=n.new('ShaderNodeTexCoord');split=n.new('ShaderNodeSeparateXYZ');l.new(uv.outputs['UV'],split.inputs[0]);angle=n.new('ShaderNodeMath');angle.operation='MULTIPLY';angle.inputs[1].default_value=2*math.pi;l.new(split.outputs[0],angle.inputs[0]);si=n.new('ShaderNodeMath');si.operation='SINE';co=n.new('ShaderNodeMath');co.operation='COSINE';l.new(angle.outputs[0],si.inputs[0]);l.new(angle.outputs[0],co.inputs[0]);vec=n.new('ShaderNodeCombineXYZ');l.new(si.outputs[0],vec.inputs[0]);l.new(co.outputs[0],vec.inputs[1]);ax=n.new('ShaderNodeMath');ax.operation='MULTIPLY';ax.inputs[1].default_value=.32;l.new(split.outputs[1],ax.inputs[0]);l.new(ax.outputs[0],vec.inputs[2]);noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=9;noise.inputs['Detail'].default_value=3;noise.inputs['Roughness'].default_value=.7;l.new(vec.outputs[0],noise.inputs['Vector']);ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.22;ramp.color_ramp.elements[0].color=(.055,.028,.012,1);ramp.color_ramp.elements[1].position=.76;ramp.color_ramp.elements[1].color=(.25,.16,.075,1);l.new(noise.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],bs.inputs['Base Color']);bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.45;bump.inputs['Distance'].default_value=.009;l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bs.inputs['Normal'])
objects=[trunk]
def curve(c,t):return c[0]*(1-t)**3+c[1]*3*t*(1-t)**2+c[2]*3*t*t*(1-t)+c[3]*t**3
def tube(name,control,radius,tip,phase):
 pts=[curve(control,j/40) for j in range(41)];verts=[];faces=[];rings=32;side=None;distance=0;distances=[0]
 for j in range(1,len(pts)):distance+=(pts[j]-pts[j-1]).length;distances.append(distance)
 for j,point in enumerate(pts):
  t=j/40;tangent=(pts[min(j+1,40)]-pts[max(j-1,0)]).normalized()
  if side is None:side=tangent.cross(Vector((0,0,1)));side=side if side.length>.05 else tangent.cross(Vector((1,0,0)))
  side=(side-tangent*side.dot(tangent)).normalized();other=tangent.cross(side).normalized();r=radius*(1-t)**1.1+tip*t
  for k in range(rings):
   angle=2*math.pi*k/rings;rib=1+.055*math.sin(5*angle+phase+.7*t)+.025*math.sin(11*angle+phase+t*1.4)
   verts.append(point+(side*math.cos(angle)+other*math.sin(angle))*r*rib)
 for j in range(40):
  for k in range(rings):faces.append((j*rings+k,j*rings+(k+1)%rings,(j+1)*rings+(k+1)%rings,(j+1)*rings+k))
 faces.extend([tuple(reversed(range(rings))),tuple(40*rings+k for k in range(rings))]);mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.materials.append(mat);layer=mesh.uv_layers.new()
 for poly in mesh.polygons:
  poly.use_smooth=True;ks=[mesh.loops[x].vertex_index%rings for x in poly.loop_indices];wrap=min(ks)==0 and max(ks)==rings-1
  for li in poly.loop_indices:
   vi=mesh.loops[li].vertex_index;k=vi%rings;j=vi//rings;layer.data[li].uv=((rings if wrap and k==0 else k)/rings,distances[j]+phase)
 obj=bpy.data.objects.new(name,mesh);obj.location=attachment;bpy.context.scene.collection.objects.link(obj);objects.append(obj)
for i in range(5):
 theta=2*math.pi*i/5+rng.uniform(-.08,.08);r=Vector((math.cos(theta),math.sin(theta),0));side=Vector((-r.y,r.x,0));phase=rng.uniform(0,6)
 end=r*rng.uniform(2.35,2.8)+side*rng.uniform(-.25,.25)+Vector((0,0,rng.uniform(5.5,6.1)))
 control=[Vector((0,0,2.05)),r*.45+side*rng.uniform(-.4,.4)+Vector((0,0,3.2)),r*1.65+side*rng.uniform(-.55,.55)+Vector((0,0,4.8)),end];tube('Primary '+str(i),control,rng.uniform(.27,.34),.018,phase)
 start=curve(control,.59);tangent=(curve(control,.61)-curve(control,.57)).normalized()
 for sign in [-1,1]:
  phi=theta+sign*rng.uniform(.24,.34);direction=Vector((math.cos(phi),math.sin(phi),0));finish=direction*rng.uniform(2.8,3.2)+Vector((0,0,rng.uniform(5.9,6.65)))
  controls=[start,start+tangent*.55,direction*2.55+Vector((0,0,5.25)),finish];tube('Fork '+str(i)+' '+str(sign),controls,.105,.009,phase+sign)
bpy.ops.object.select_all(action='DESELECT')
for obj in objects:obj.select_set(True)
bpy.context.view_layer.objects.active=trunk;bpy.ops.object.join();high=trunk;high.name='Retained trunk and radial branch references';low=high.copy();low.data=high.data.copy();bpy.context.scene.collection.objects.link(low);bpy.context.view_layer.objects.active=low;high.select_set(False);low.select_set(True)
mod=low.modifiers.new('Continuous branch collars','REMESH');mod.mode='VOXEL';mod.voxel_size=.018;bpy.ops.object.modifier_apply(modifier=mod.name);mod=low.modifiers.new('Round voxel edges','SMOOTH');mod.factor=.55;mod.iterations=2;bpy.ops.object.modifier_apply(modifier=mod.name);low.data.calc_loop_triangles();triangles=len(low.data.loop_triangles);mod=low.modifiers.new('Bound woody budget','DECIMATE');mod.ratio=min(1,28000/triangles);bpy.ops.object.modifier_apply(modifier=mod.name)
bm=bmesh.new();bm.from_mesh(low.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(low.data);bm.free()
for poly in low.data.polygons:poly.use_smooth=True
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.004);bpy.ops.object.mode_set(mode='OBJECT')
material=bpy.data.materials.new('Unified woody bake');material.use_nodes=True;low.data.materials.clear();low.data.materials.append(material)
for poly in low.data.polygons:poly.material_index=0
low.data.validate();low.data.update();nodes=material.node_tree.nodes;links=material.node_tree.links;bs=nodes.get('Principled BSDF');node=nodes.new('ShaderNodeTexImage');nodes.active=node
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1;scene.render.threads_mode='FIXED';scene.render.threads=4;scene.render.bake.use_selected_to_active=True;scene.render.bake.cage_extrusion=.045;scene.render.bake.max_ray_distance=.12;scene.render.bake.margin=12
bpy.ops.object.select_all(action='DESELECT');high.select_set(True);low.select_set(True);bpy.context.view_layer.objects.active=low
for label,kind in [('basecolor','EMIT'),('normal','NORMAL')]:
 image=bpy.data.images.new('Radial wood '+label,2048,2048,alpha=True);image.colorspace_settings.name='sRGB' if label=='basecolor' else 'Non-Color';node.image=image;restored=[]
 if kind=='EMIT':
  for source_material in high.data.materials:
   nn=source_material.node_tree.nodes;ll=source_material.node_tree.links;pbs=next(n for n in nn if n.type=='BSDF_PRINCIPLED');output=next(n for n in nn if n.type=='OUTPUT_MATERIAL' and n.is_active_output);prior=output.inputs['Surface'].links[0].from_socket;emission=nn.new('ShaderNodeEmission');colour=pbs.inputs['Base Color']
   if colour.is_linked:ll.new(colour.links[0].from_socket,emission.inputs['Color'])
   else:emission.inputs['Color'].default_value=colour.default_value
   ll.new(emission.outputs[0],output.inputs['Surface']);restored.append((source_material,output,prior,emission))
 bpy.ops.object.bake(type=kind)
 for source_material,output,prior,emission in restored:source_material.node_tree.links.new(prior,output.inputs['Surface']);source_material.node_tree.nodes.remove(emission)
 image.filepath_raw=str(a.out/(label+'.png'));image.file_format='PNG';image.save();image.pack();tex=nodes.new('ShaderNodeTexImage');tex.image=image
 if label=='basecolor':links.new(tex.outputs['Color'],bs.inputs['Base Color'])
 else:normal=nodes.new('ShaderNodeNormalMap');links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bs.inputs['Normal'])
rough=bpy.data.images.new('Radial roughness metallic',2,2,alpha=True);rough.colorspace_settings.name='Non-Color';rough.pixels=[1,.88,0,1]*4;rough.pack();tex=nodes.new('ShaderNodeTexImage');tex.image=rough;channels=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],channels.inputs[0]);links.new(channels.outputs['Green'],bs.inputs['Roughness']);links.new(channels.outputs['Blue'],bs.inputs['Metallic'])
high.hide_render=True;bpy.ops.object.select_all(action='DESELECT');low.select_set(True);bpy.context.view_layer.objects.active=low;low.name='Tropical radial woody scaffold';dest=a.out/'wood.glb';bpy.ops.export_scene.gltf(filepath=str(dest),export_format='GLB',use_selection=True,export_normals=True,export_tangents=True)
report={'source':str(a.source),'source_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'profile_height_m':8,'source_seams_welded':True,'upper_trunk_taper':.65,'seed':a.seed,'trunk_cut_m':2.45,'primary_boughs':5,'secondary_boughs':10,'voxel_m':.018,'wood_triangles':len(low.data.polygons),'method':'Retained neural lower trunk; deterministic radial cubic branches; continuous collar remesh and source colour/normal bake','art_approved':False,'asset':str(dest)};(a.out/'scaffold-report.json').write_text(json.dumps(report,indent=2)+'\n');bpy.ops.wm.save_as_mainfile(filepath=str(a.out/'scaffold.blend'));print(json.dumps(report),flush=True)
