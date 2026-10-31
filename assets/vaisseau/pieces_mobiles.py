"""Pièces mobiles du cockpit : le manche et la manette des gaz, que le moteur fait tourner (ShipPose, Ship.hlsli).

Usage : blender -b vaisseau_travail.blend --python pieces_mobiles.py   (marque, sauve la scène, exporte le GLB)
preparer.py l'appelle aussi, après design_v2.

- Chaque sommet porte l'attribut _POSE, exporté dans le GLB et lu par paquet_moteur.py :
  0 fixe ; dans ]0, 1] le manche, ]1, 2] la manette, par la fraction au-delà de l'entier.
  Le soufflet du manche passe de 0 à sa base à 1 en haut ; le carter reste fixe.
- Les pivots sont des vides, « Pivot | manche » et « Pivot | gaz » : leur axe Z est l'axe de torsion du manche,
  l'axe de rotation de la manette, orienté pour qu'un angle positif pousse la poignée vers le nez.
"""
import bpy, os, sys
import numpy as np
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))

def sommets(o, matiere=None):
    # Sommets du repère du vaisseau, ceux des faces d'un matériau seulement si donné.
    if matiere is None:
        ids = range(len(o.data.vertices))
    else:
        k = [m.name for m in o.data.materials].index(matiere)
        ids = sorted({i for f in o.data.polygons if f.material_index == k for i in f.vertices})
    return np.array([tuple(o.matrix_world @ o.data.vertices[i].co) for i in ids])

def pose(o, valeurs):
    a = o.data.attributes.get('_POSE') or o.data.attributes.new('_POSE', 'FLOAT', 'POINT')
    a.data.foreach_set('value', np.asarray(valeurs, np.float32))

def pivot(nom, point, axe, collection):
    old = bpy.data.objects.get(nom)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    e = bpy.data.objects.new(nom, None); collection.objects.link(e)
    e.location = point; e.rotation_mode = 'QUATERNION'; e.rotation_quaternion = Vector(axe).to_track_quat('Z', 'Y')
    e.empty_display_size = .05
    return e

def marquer(cockpit):
    # Le manche tourne sur sa rotule, au pied du soufflet ; le soufflet suit, sa base reste sur la bride.
    st = bpy.data.objects['Manche | ensemble']
    gomme = sommets(st, 'Jeu | Caoutchouc'); base = gomme[:, 2].min()
    soufflet = gomme[gomme[:, 2] < base + .2]; haut = soufflet[:, 2].max()
    centre = soufflet[soufflet[:, 2] < base + 1e-3].mean(0)
    z = sommets(st)[:, 2]
    pose(st, np.clip((z - base) / (haut - base), 0, 1))
    pivot('Pivot | manche', centre, (0, 0, 1), cockpit)

    # La manette pivote au fond de sa fente, autour de l'axe de sa poignée.
    gaz = bpy.data.objects['Manette | gaz']; plaque = bpy.data.objects['Module | gaz']
    f = max(plaque.data.polygons, key=lambda f: f.area)
    n = (plaque.matrix_world.to_3x3() @ f.normal).normalized(); n = n if n.z > 0 else -n
    v = sommets(gaz); d = v @ np.array(n)
    point = v[d < d.min() + 1e-3].mean(0)
    poignee = sommets(gaz, 'Jeu | Caoutchouc')
    axe = np.linalg.svd(poignee - poignee.mean(0))[2][0]
    # Une rotation positive autour de l'axe pousse la poignée vers le nez, -Y.
    if np.cross(axe, poignee.mean(0) - point)[1] > 0: axe = -axe
    pose(gaz, np.full(len(v), 2.0))
    pivot('Pivot | gaz', point, axe, cockpit)
    print('PIVOTS manche', np.round(centre, 4), 'haut du soufflet', round(haut, 4), '; gaz', np.round(point, 4), np.round(axe, 3))

if __name__ == '__main__':
    sys.path.insert(0, ROOT)
    import exporter
    marquer(bpy.data.collections['Spaceship_Cockpit'])
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'vaisseau_travail.blend'))
    exporter.exporter(ROOT)
