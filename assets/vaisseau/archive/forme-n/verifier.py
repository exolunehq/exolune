import bpy, os
root=os.path.dirname(os.path.abspath(__file__))
s=bpy.context.scene
s.render.engine='CYCLES'; s.cycles.samples=24
s.cycles.device='CPU'
s.render.resolution_x=1200; s.render.resolution_y=800; s.render.resolution_percentage=100
for name, filename, hidden in [('Controle | cockpit','cockpit.png', True),('Controle | commandes','commandes.png', True),('Controle | pilote','pilote.png', False),('Controle | pupitre','pupitre.png', False),('Camera_Front_34','exterieur.png',False),('Camera_Rear_Close','arriere.png',False)]:
    s.camera=bpy.data.objects[name]
    bpy.data.objects['Canopy_Glass'].hide_render=hidden
    s.render.filepath=os.path.join(root,filename)
    bpy.ops.render.render(write_still=True)
