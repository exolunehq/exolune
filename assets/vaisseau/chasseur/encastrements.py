"""Machined recesses in a shared fascia, with real openings and closed backs."""
import bpy
import bmesh
from mathutils import Vector
from panneaux_cockpit import offset, clearance

_cutters={}


def logement(g, support, center, u, v, normal, width, height, depth=.010, contour=None):
    center, u, v, normal = map(Vector, (center, u, v, normal))
    bpy.context.view_layer.update()
    contour = contour or [(-width/2,-height/2),(width/2,-height/2),(width/2,height/2),(-width/2,height/2)]
    def ring(z, clearance):
        return [center+u*x+v*y+normal*z for x,y in offset(contour,-clearance)]
    corners = ring(0,.005)
    perimeter = [a.lerp(b, k/4) for a, b in zip(corners, corners[1:]+corners[:1]) for k in range(4)]
    contacts = []
    for p in perimeter:
        hit, q, _, _ = support.ray_cast(p+normal*.04, -normal, distance=.08)
        if not hit or abs((q-p).dot(normal)) > .0005:
            raise ValueError(f'{support.name}: inset requires a planar fascia at {tuple(p)}; hit={hit}, gap={(q-p).dot(normal)*1000:.3f} mm')
        contacts.append(q.copy())
    # The cutter forms a narrow chamfer, a clearance gap and a closed pocket.
    cutter = g['Piece']('Temporary instrument pocket', g['cockpit'])
    rings = [ring(z,gap) for z,gap in ((-depth,.0015),(-.0025,.0015),(0,.003),(.06,.003))]
    g['loft'](cutter, rings, g['TOLE_INT'])
    cutter.souder(); bmesh.ops.triangulate(cutter.bm,faces=list(cutter.bm.faces)); obj = cutter.fin(30)
    _cutters.setdefault(support.name,[]).append(obj)
    probe=center.copy()
    if clearance(contour,(0,0)) < .004:
        a,b=contour[:2]; dx,dy=b[0]-a[0],b[1]-a[1]; length=(dx*dx+dy*dy)**.5
        probe=center+u*((a[0]+b[0])/2-dy/length*.008)+v*((a[1]+b[1])/2+dx/length*.008)
    return {'support_mesh': support.name, 'support_normal': list(normal),
            'support_contacts': [a for p in contacts for a in p],
            'mounting_mode': 'recessed', 'mounting_center': list(center),
            'mounting_u': list(u), 'mounting_v': list(v),
            'mounting_size': [width, height], 'mounting_outline': [a for p in contour for a in p],
            'pocket_probe': list(probe), 'pocket_depth': depth}


def finaliser():
    """Cut each complete instrument layout once, before the finish bevels.

    Separate Boolean operations on adjacent coplanar pockets can remove the
    previous floor. One compound cutter keeps all recess backs in one solid.
    """
    for name,parts in _cutters.items():
        support=bpy.data.objects[name]
        bpy.ops.object.select_all(action='DESELECT')
        for obj in parts: obj.select_set(True)
        bpy.context.view_layer.objects.active=parts[0]
        bpy.ops.object.join(); cutter=parts[0]
        bpy.ops.object.select_all(action='DESELECT')
        support.select_set(True); bpy.context.view_layer.objects.active=support
        mod=support.modifiers.new('Integrated instrument recesses','BOOLEAN')
        mod.operation='DIFFERENCE'; mod.solver='MANIFOLD'; mod.object=cutter
        bpy.ops.object.modifier_apply(modifier=mod.name)
        mesh=cutter.data; bpy.data.objects.remove(cutter,do_unlink=True); bpy.data.meshes.remove(mesh)
    _cutters.clear(); bpy.context.view_layer.update()


def annoter(obj, values):
    for key, value in values.items():
        obj[key] = value
