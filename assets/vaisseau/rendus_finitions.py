"""Close inspection of the saved scene, without altering the game asset.

blender -b vaisseau_travail.blend --python rendus_finitions.py -- ABSOLUTE_OUTPUT
Uses CPU Cycles; the canopy is hidden only for the four assembly views.
"""
from pathlib import Path
import sys
import bpy
from mathutils import Vector

out = Path(sys.argv[sys.argv.index('--')+1]).resolve()
out.mkdir(parents=True, exist_ok=True)
if '--glb' in sys.argv:
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(Path(__file__).resolve().parent/'vaisseau.glb'))
s = bpy.context.scene
s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = 32; s.cycles.use_denoising = True
s.render.resolution_x, s.render.resolution_y = 1440, 1000
s.render.resolution_percentage = 100
s.render.film_transparent = False
s.view_settings.view_transform = 'AgX'; s.view_settings.exposure = -.5
bpy.data.objects['Canopy_Glass'].hide_render = True
world = bpy.data.worlds.new('Inspection studio'); s.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (.24,.28,.32,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = .7
for name, position, watts, size in [('Softbox', (0,-2.6,3.2), 160, 2), ('Rim', (-2,-.2,2.5), 100, 1.5)]:
    light = bpy.data.objects.new(name, bpy.data.lights.new(name, 'AREA')); s.collection.objects.link(light)
    light.location = position; light.data.energy = watts; light.data.shape = 'DISK'; light.data.size = size
    light.rotation_euler = (Vector((0,-1.1,.55))-light.location).to_track_quat('-Z','Y').to_euler()
cam = bpy.data.objects.new('Inspection', bpy.data.cameras.new('Inspection')); s.collection.objects.link(cam)
s.camera = cam; cam.data.clip_start = .025
views = [('assemblage', (1.35,-2.4,2.25), (0,-1.05,.62), 32),
         ('console', (-.18,-1.0,1.08), (.68,-1.15,.48), 24),
         ('siege_detail', (.58,-1.7,1.25), (0,-.9,.65), 26),
         ('pupitre_detail', (0,-.9192,1.03), (0,-1.87,.60), 20),
         ('vue_vol', (0,-.9192,1.03), (0,-10,1.03), 18),
         ('verriere', (2.6,-4.5,2.1), (0,-1.05,.8), 40),
         ('exterieur', (11.6,-11.4,3.8), (0,-1.4,.25), 48),
         ('arriere', (4.2,6.2,2.6), (.6,2.6,.55), 40)]
selected = sys.argv[sys.argv.index('--views')+1].split(',') if '--views' in sys.argv else None
for name, pos, target, lens in views:
    if selected and name not in selected: continue
    bpy.data.objects['Canopy_Glass'].hide_render = name not in ('vue_vol','verriere', 'exterieur', 'arriere')
    s.render.resolution_x,s.render.resolution_y=(1440,810) if name=='vue_vol' else (1440,1000)
    cam.location = pos; cam.rotation_euler = (Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.lens = lens
    s.render.filepath = str(out/(name+'.png')); bpy.ops.render.render(write_still=True)
