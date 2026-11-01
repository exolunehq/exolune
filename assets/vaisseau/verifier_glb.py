"""Contrôle indépendant du GLB réimporté dans une scène Blender vide."""
import bpy, os
from mathutils import Vector
root=os.path.dirname(os.path.abspath(__file__))
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=os.path.join(root,'vaisseau.glb'))
s=bpy.context.scene; s.render.engine='CYCLES'; s.cycles.device='CPU'; s.cycles.samples=32; s.cycles.use_denoising=True
s.render.resolution_x=1000; s.render.resolution_y=700; s.render.resolution_percentage=100
s.world.color=(.18,.18,.18)
def light(loc, power, size):
    d=bpy.data.lights.new('Controle',type='AREA'); d.energy=power; d.shape='DISK'; d.size=size
    o=bpy.data.objects.new('Controle',d); s.collection.objects.link(o); o.location=loc
    o.rotation_euler=(Vector((0,-1,0))-o.location).to_track_quat('-Z','Y').to_euler()
light((2,-2,8),1700,8); light((-5,-4,4),1000,6)
d=bpy.data.cameras.new('Controle GLB'); o=bpy.data.objects.new('Controle GLB',d); s.collection.objects.link(o)
o.location=(11.6,-11.4,3.8); o.rotation_euler=(Vector((0,-1.4,.25))-o.location).to_track_quat('-Z','Y').to_euler(); d.lens=48
s.camera=o; s.render.filepath=os.path.join(root,'export_controle.png'); bpy.ops.render.render(write_still=True)
o.location=(0,-.9192,1.03); o.rotation_euler=(Vector((0,-1.87,.60))-o.location).to_track_quat('-Z','Y').to_euler(); d.lens=20; d.clip_start=.025
s.render.filepath=os.path.join(root,'export_pilote.png'); bpy.ops.render.render(write_still=True)
