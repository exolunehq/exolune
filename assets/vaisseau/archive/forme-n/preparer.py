"""Reprend une copie du vaisseau Antigravity et prépare son modèle de jeu.

Usage : blender -b <spaceship.blend original> --python assets/vaisseau/preparer.py
"""
import bpy
import bmesh
import math
import os
import sys
import numpy as np
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__))
scene = bpy.context.scene
ship = bpy.data.collections['Spaceship']
cockpit = bpy.data.collections['Spaceship_Cockpit']

def remove(name):
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)

# Le fichier ouvert est l'original ; toutes les modifications sont sauvées ailleurs.
remove('Cockpit_Interior')
for obj in list(bpy.data.objects):
    if obj.name.startswith('Thruster_Plume_'):
        bpy.data.objects.remove(obj, do_unlink=True)

def material(name, color, metallic=0, roughness=.5, emission=None):
    m = bpy.data.materials.new(name); m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Roughness'].default_value = roughness
    if emission:
        p.inputs['Emission Color'].default_value = (*color, 1)
        p.inputs['Emission Strength'].default_value = emission
    return m

dark = material('Jeu | Structure graphite', (.055,.068,.075), .6, .46)
seat = material('Jeu | Garniture', (.13,.15,.16), .05, .78)
edge = material('Jeu | Metal brosse', (.22,.28,.30), .8, .34)
rubber = material('Jeu | Caoutchouc', (.018,.023,.027), 0, .82)
screen = material('Jeu | Ecran sombre', (.006,.025,.036), .15, .28)
cyan = material('Jeu | Affichage cyan', (.025,.52,.74), .05, .35, 2.0)
amber = material('Jeu | Voyant ambre', (1.0,.28,.025), .05, .38, 1.6)
red = material('Jeu | Signal rouge', (.8,.025,.012), .05, .42, 1.5)

def link_only(obj, collection):
    for c in list(obj.users_collection): c.objects.unlink(obj)
    collection.objects.link(obj)

def box(name, loc, size, mat, bevel=.012, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o=bpy.context.object; o.name=name; o.dimensions=size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if rot: o.rotation_euler=rot
    if bevel:
        mod=o.modifiers.new('Aretes', 'BEVEL'); mod.width=bevel; mod.segments=1
        bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=mod.name)
    o.data.materials.append(mat); link_only(o,cockpit)
    return o

def rod(name, a, b, radius, mat, vertices=8):
    a,b=Vector(a),Vector(b); d=b-a
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=d.length, location=(a+b)/2)
    o=bpy.context.object; o.name=name; o.rotation_euler=d.to_track_quat('Z','Y').to_euler()
    o.data.materials.append(mat); link_only(o,cockpit)
    return o

# Peinture de coque légèrement usée, répétable, une tuile pour 2 m : teinte chaude passée
# au soleil, coulures de crasse vers l'arrière (axe u des UV), poussière, éclats
# jusqu'à l'apprêt, rayures claires. Rugosité en données linéaires. Le relief
# (rivets) vient d'une carte cuite sur la deuxième UV des tôles, plus bas.
rng=np.random.default_rng(507); n=1024
def smear(a,k,axis):
    out=np.zeros_like(a)
    for i in range(-k,k+1): out+=np.roll(a,i,axis)
    return out/(2*k+1)
def noise(): return rng.normal(0,1,(n,n)).astype(np.float32)
yy,xx=np.mgrid[0:n,0:n].astype(np.float32)*(2*np.pi/n)
fade=sum(rng.uniform(.4,1)*np.cos(kx*xx+ky*yy+rng.uniform(0,2*np.pi)) for kx in range(-3,4) for ky in range(-3,4) if 0<kx*kx+ky*ky<=9)
fade/=np.abs(fade).max()
dust=smear(smear(noise(),2,0),2,1); dust/=dust.std()
streak=smear(smear(noise(),90,1),8,0); streak=np.clip(streak/streak.std()-.3,0,None)
# Les éclats se groupent dans quelques zones d'usure au lieu d'un semis uniforme.
wear=sum(rng.uniform(.4,1)*np.cos(kx*xx+ky*yy+rng.uniform(0,2*np.pi)) for kx in range(-4,5) for ky in range(-4,5) if 0<kx*kx+ky*ky<=16)
wear/=np.abs(wear).max()
chips=np.zeros((n,n),np.float32); spots=np.argwhere(wear>.45)
for _ in range(110):
    cy,cx=spots[rng.integers(len(spots))]; r=rng.uniform(.7,2.4)*(2 if rng.random()<.08 else 1); R=int(r*1.6)+2
    ys=np.arange(cy-R,cy+R+1); xs=np.arange(cx-R,cx+R+1); Y,X=np.meshgrid(ys,xs,indexing='ij')
    ang=np.arctan2(Y-cy,X-cx); bord=r*(1+.3*np.sin(3*ang+rng.uniform(0,6.3))+.15*np.sin(5*ang+rng.uniform(0,6.3)))
    win=np.ix_(ys%n,xs%n); chips[win]=np.maximum(chips[win],(np.hypot(Y-cy,X-cx)<bord).astype(np.float32))
scratch=np.zeros((n,n),np.float32)
for _ in range(30):
    x0,y0=rng.uniform(0,n,2); a=rng.uniform(0,np.pi); L=rng.uniform(15,140); t=np.linspace(0,1,int(L*2))
    xs=((x0+np.cos(a)*L*t)%n).astype(int); ys=((y0+np.sin(a)*L*t)%n).astype(int)
    scratch[ys,xs]=np.maximum(scratch[ys,xs],rng.uniform(.3,.8))
def save_image(name, rgb, colorspace):
    rgba=np.concatenate((np.clip(rgb,0,1),np.ones((n,n,1),dtype=np.float32)),axis=2)
    im=bpy.data.images.new(name,width=n,height=n,alpha=True)
    im.colorspace_settings.name=colorspace; im.pixels.foreach_set(rgba.ravel()); im.update()
    im.filepath_raw=os.path.join(ROOT,name+'.png'); im.file_format='PNG'; im.save()
    im.pack()
    return im
shade=(1+fade*.035+dust*.012-streak*.04)[...,None]
paint=np.array((.47,.47,.455),np.float32)*shade
paint=paint*(1-chips[...,None])+np.array((.30,.30,.29),np.float32)*chips[...,None]
paint=paint*(1-scratch[...,None]*.4)+np.array((.58,.58,.57),np.float32)*scratch[...,None]*.4
albedo=save_image('coque_base',paint,'sRGB')
rough=save_image('coque_rugosite',np.repeat(np.clip(.62+fade*.02+streak*.02-chips*.2-scratch*.15,0,1)[...,None],3,axis=2),'Non-Color')
metal=material('Jeu | Coque peinte',(.47,.47,.455),0,.62)
nodes=metal.node_tree.nodes; links=metal.node_tree.links; p=nodes.get('Principled BSDF')
for img, socket in ((albedo,'Base Color'),(rough,'Roughness')):
    node=nodes.new('ShaderNodeTexImage'); node.image=img; links.new(node.outputs['Color'],p.inputs[socket])
# Seconde passe : remplace le cockpit et le panneau supérieur de la première
# version par une coque à panneaux structurels et une cuve élargie.
sys.path.insert(0,ROOT)
import design_v2
design_v2.construire(ROOT,ship,cockpit,material,box,rod,link_only,metal,dark,edge,rubber,seat,screen,cyan,amber,red)
import pieces_mobiles
pieces_mobiles.marquer(cockpit)

# Rivets cuits en cartes de normales et d'occlusion sur la deuxième UV des tôles
# (UVDetail). Les dômes modélisés ne servent qu'à la cuisson, puis disparaissent.
cuisson=bpy.data.collections['Cuisson']
cibles=[bpy.data.objects[name] for name in ('Coque | panneaux structurels','Coque | carene')]
scene.render.engine='CYCLES'; scene.cycles.device='CPU'
scene.render.bake.use_clear=False; scene.render.bake.margin=6
def carte(name,size,fond):
    im=bpy.data.images.new(name,size,size,alpha=False); im.colorspace_settings.name='Non-Color'
    im.generated_color=fond; return im
normale=carte('coque_details_normale',4096,(.5,.5,1,1)); occlusion=carte('coque_occlusion',2048,(1,1,1,1))
mats={m for o in cibles for m in o.data.materials}
def viser(img):
    for m in mats:
        nd=m.node_tree.nodes.get('Cuisson') or m.node_tree.nodes.new('ShaderNodeTexImage'); nd.name='Cuisson'; nd.image=img; m.node_tree.nodes.active=nd
def cuire(cible,sources,**options):
    bpy.ops.object.select_all(action='DESELECT')
    for o in sources: o.select_set(True)
    cible.select_set(True); bpy.context.view_layer.objects.active=cible
    bpy.ops.object.bake(uv_layer='UVDetail',margin=6,**options)
# Normales : rayons lancés 4 mm au-dessus des tôles vers les dômes, ou vers une
# copie des tôles elles-mêmes là où il n'y a pas de rivet.
copies=[]
for o in cibles:
    c=o.copy(); cuisson.objects.link(c); copies.append(c)
viser(normale); scene.cycles.samples=4
for o in cibles: cuire(o,list(cuisson.objects),type='NORMAL',normal_space='TANGENT',use_selected_to_active=True,cage_extrusion=.004,max_ray_distance=.012)
for c in copies: bpy.data.objects.remove(c,do_unlink=True)
# Occlusion locale, 6 cm : joints, pied des rivets, abords des trappes. Le verre
# ne doit pas assombrir les tôles qui le bordent.
bpy.data.objects['Canopy_Glass'].hide_render=True
viser(occlusion); scene.cycles.samples=48; scene.world.light_settings.distance=.06
for o in cibles: cuire(o,[],type='AO')
bpy.data.objects['Canopy_Glass'].hide_render=False
for im,name in ((normale,'coque_details_normale.png'),(occlusion,'coque_occlusion.png')):
    im.filepath_raw=os.path.join(ROOT,name); im.file_format='PNG'; im.save(); im.pack()
for m in mats: m.node_tree.nodes.remove(m.node_tree.nodes['Cuisson'])
for o in list(cuisson.objects): bpy.data.objects.remove(o,do_unlink=True)
bpy.data.collections.remove(cuisson)
# Branchement dans les matériaux de tôle ; l'occlusion passe par le groupe que
# l'export glTF reconnaît.
sortie=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree')
sortie.interface.new_socket('Occlusion',in_out='INPUT',socket_type='NodeSocketFloat')
for m in [m for m in bpy.data.materials if m.name.startswith('Jeu | Tole')]:
    nt=m.node_tree; p=nt.nodes['Principled BSDF']
    uvd=nt.nodes.new('ShaderNodeUVMap'); uvd.uv_map='UVDetail'
    tn=nt.nodes.new('ShaderNodeTexImage'); tn.image=normale; nt.links.new(uvd.outputs['UV'],tn.inputs['Vector'])
    nm=nt.nodes.new('ShaderNodeNormalMap'); nm.uv_map='UVDetail'
    nt.links.new(tn.outputs['Color'],nm.inputs['Color']); nt.links.new(nm.outputs['Normal'],p.inputs['Normal'])
    ta=nt.nodes.new('ShaderNodeTexImage'); ta.image=occlusion; nt.links.new(uvd.outputs['UV'],ta.inputs['Vector'])
    g=nt.nodes.new('ShaderNodeGroup'); g.node_tree=sortie; nt.links.new(ta.outputs['Color'],g.inputs['Occlusion'])

# Dépliage des éléments sans UV. Les UV sont également conservées dans le GLB.
meshes=[o for o in ship.all_objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:
    if not o.data.uv_layers:
        o.select_set(True); bpy.context.view_layer.objects.active=o
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(island_margin=.008)
        bpy.ops.object.mode_set(mode='OBJECT'); o.select_set(False)

# Verrière fumée transparente, exportée en mélange alpha.
glass=material('Jeu | Verriere fumee',(.075,.16,.20), .1,.16)
glass.diffuse_color=(.075,.16,.20,.22)
p=glass.node_tree.nodes.get('Principled BSDF'); p.inputs['Alpha'].default_value=.22
glass.surface_render_method='BLENDED'; glass.use_transparency_overlap=False
bpy.data.objects['Canopy_Glass'].data.materials.clear(); bpy.data.objects['Canopy_Glass'].data.materials.append(glass)

# Caméras de contrôle dans le fichier éditable.
def camera(name, location, target, lens):
    data=bpy.data.cameras.new(name); obj=bpy.data.objects.new(name,data); scene.collection.objects.link(obj)
    obj.location=location; obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler(); data.lens=lens; data.clip_start=.025
    return obj
camera('Controle | pilote', (0,-.9192,1.07), (0,-3.032,.25), 20)
camera('Controle | cockpit', (2.7,1.3,3.4), (0,-1.45,.16), 45)
camera('Controle | commandes', (1.1,-.48,1.42), (0,-1.85,.13), 50)
camera('Controle | pupitre', (.32,-1.0,.98), (-.05,-2.15,.42), 24)

# Sélection explicite : aucun décor, lumière, caméra ou panache dans le modèle jeu.
bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active=bpy.data.objects['Coque | sous-structure']
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'vaisseau_travail.blend'))
import exporter
exporter.exporter(ROOT)
