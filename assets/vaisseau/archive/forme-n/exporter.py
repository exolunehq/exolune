"""Exporte vaisseau.glb depuis la scène de travail ouverte ; appelé par preparer.py et pieces_mobiles.py.

Modifie la scène (fusion, triangulation) : à appeler après l'avoir sauvée.
"""
import bpy, bmesh, os

def exporter(root):
    ship = bpy.data.collections['Spaceship']; cockpit = bpy.data.collections['Spaceship_Cockpit']
    # Fusionner le cockpit en un seul maillage : une primitive par matériau, les
    # pièces restent séparées dans le fichier de travail. Les vitrages restent à part
    # pour le tri de transparence. Le manche et la manette gardent leur attribut _POSE.
    parts=[o for o in cockpit.objects if o.type=='MESH' and o.name!='Canopy_Glass' and 'combineur' not in o.name]
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0]
    bpy.ops.object.join(); parts[0].name='Cockpit | ensemble'
    bpy.ops.object.select_all(action='DESELECT')
    meshes=[o for o in ship.all_objects if o.type=='MESH']
    for o in meshes:
        # Triangulation de la copie exportée ; toutes les pièces portent déjà leurs UV.
        bm=bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bm.to_mesh(o.data); bm.free(); o.data.update()
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes: o.select_set(True)
    for o in ship.all_objects:
        if o.name.startswith('Pivot |'): o.select_set(True)
    bpy.context.view_layer.objects.active=bpy.data.objects['Coque | sous-structure']
    bpy.ops.export_scene.gltf(filepath=os.path.join(root,'vaisseau.glb'), export_format='GLB', use_selection=True, export_apply=True,
                              export_tangents=True, export_attributes=True)
    print('JEU OBJETS',len(meshes),'TRIANGLES',sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes))
