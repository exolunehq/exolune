"""Background Blender checks of cabin clearance and the unchanged outer shell."""
from pathlib import Path
import bpy,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
root=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(root/'vaisseau_travail.blend'))
hull=bpy.data.objects['Navigator | smooth exterior']
deps=bpy.context.evaluated_depsgraph_get()
tree=BVHTree.FromObject(hull,deps,epsilon=1e-5)
outside=[];checked=0;topology=[];contactChecks=[]
visibleVertices=[];visibleFaces=[]
chassis=bpy.data.objects.get('Navigator | continuous cabin, station and sensor')
chassisTree=BVHTree.FromObject(chassis,deps,epsilon=1e-6) if chassis else None
seatTree=BVHTree.FromObject(bpy.data.objects['Navigator | formed bucket seat'],deps,epsilon=1e-6)
for obj in bpy.context.scene.objects:
    if obj==hull or obj.type not in {'MESH','CURVE'}:continue
    mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(deps),depsgraph=deps)
    first=len(visibleVertices)
    visibleVertices.extend(obj.matrix_world@v.co for v in mesh.vertices)
    visibleFaces.extend(tuple(first+i for i in p.vertices) for p in mesh.polygons)
    bad=0;worst=0
    for vertex in mesh.vertices:
        p=obj.matrix_world@vertex.co
        if p.length<1e-6:continue
        hit,_,_,_=tree.ray_cast(Vector(),p.normalized(),20)
        if hit is None:
            # Exact rays through a shared edge or pole need a small numerical tie break.
            hit,_,_,_=tree.ray_cast(Vector(),(p.normalized()+Vector((1e-5,-2e-5,3e-5))).normalized(),20)
        if hit is None:raise RuntimeError(f'Outer ray missed at {obj.name}: {tuple(p)}')
        error=p.length-hit.length
        if error>.005:bad+=1;worst=max(worst,error)
        checked+=1
    if bad:outside.append({'object':obj.name,'vertices':bad,'outside_m':worst})
    if chassisTree and ('fitted console' in obj.name or 'seat docking frame' in obj.name):
        landing=-.16 if 'console' in obj.name else -.43
        gaps=[]
        for vertex in mesh.vertices:
            p=obj.matrix_world@vertex.co
            if abs(p.z-landing)>1e-5:continue
            hit,_,_,_=chassisTree.ray_cast(p+Vector((0,0,.03)),Vector((0,0,-1)),.1)
            if hit is None:raise RuntimeError('A manufactured mounting point has no supporting chassis')
            gaps.append(abs(p.z-hit.z))
        assert gaps and max(gaps)<.001,'Actual mesh mounting gap exceeds 1 mm'
        contactChecks.append({'part':obj.name,'tested_points':len(gaps),'maximum_gap_m':max(gaps)})
    if obj.name=='Navigator | fitted seat pad':
        group=obj.vertex_groups['Mounting interface'].index
        gaps=[seatTree.find_nearest(obj.matrix_world@v.co)[3] for v in mesh.vertices if any(g.group==group for g in v.groups)]
        assert len(gaps)==1225 and max(gaps)<.001,'Cushion underside does not contact the evaluated seat'
        contactChecks.append({'part':obj.name,'tested_points':len(gaps),'maximum_gap_m':max(gaps)})
    import bmesh
    bm=bmesh.new();bm.from_mesh(mesh)
    todo=set(bm.verts);components=0
    while todo:
        components+=1;stack=[todo.pop()]
        while stack:
            vertex=stack.pop()
            for edge in vertex.link_edges:
                other=edge.other_vert(vertex)
                if other in todo:todo.remove(other);stack.append(other)
    topology.append({'object':obj.name,'components':components,'boundary_edges':sum(e.is_boundary for e in bm.edges),
                     'non_manifold_edges':sum(not e.is_manifold for e in bm.edges)})
    bm.free()
    bpy.data.meshes.remove(mesh)
eye=Vector((0,-.65,.7))
visibleTree=BVHTree.FromPolygons(visibleVertices,visibleFaces,epsilon=1e-6)
instrumentVisibility=[]
for side in [-1,1]:
    for label,offset in [('readout',(0,.40,.069)),('forward trim',(-.129,-.590,.115)),
                         ('forward field',(.129,-.590,.115)),('palm',(0,-.190,.058))]:
        point=Vector((side*.82+offset[0],-1.05+offset[1],offset[2]));delta=point-eye
        found,_,_,distance=visibleTree.ray_cast(eye,delta.normalized(),delta.length+.003)
        blocked=found is not None and distance<delta.length-.004
        instrumentVisibility.append({'console':side,'control':label,'blocked':blocked})
        assert not blocked,f'Instrument is hidden from the pilot eye: {side} {label}, obstruction {delta.length-distance} m before its face'
hit,_,_,_=tree.ray_cast(Vector(),eye.normalized(),20)
assert hit.length>eye.length+.15,'Eye is outside the outer shell'
report={'checked_cabin_vertices':checked,'outside_parts':sorted(outside,key=lambda x:-x['outside_m']),
        'eye':list(eye),'eye_radial_hull_clearance_m':hit.length-eye.length,'topology':topology,
        'actual_mount_contacts':contactChecks,'pilot_instrument_visibility':instrumentVisibility}
(root/'clearance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
if outside:raise RuntimeError('Cabin parts protrude outside the approved hull')
if any(p['components']!=1 or p['boundary_edges'] or p['non_manifold_edges'] for p in topology):
    raise RuntimeError('Each manufactured cabin part must be one closed connected mesh')
