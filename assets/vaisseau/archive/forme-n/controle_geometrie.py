"""Contrôles de visibilité du pupitre, de raccord des tôles au pourtour de la bulle et du volume sous la bulle (forme.py)."""
import bpy
from mathutils import Vector
s=bpy.context.scene; dg=bpy.context.evaluated_depsgraph_get()
eye=bpy.data.objects['Controle | pilote'].location
blocked=[]
# Neuf points de chaque dalle d'écran, pris sur sa géométrie : rien ne doit les masquer.
screens=[o for o in bpy.data.objects if o.name.startswith('Ecran | ecran_') and o.name.count('|')==1]
assert len(screens)==3, [o.name for o in screens]
for o in screens:
    q=[o.matrix_world @ v.co for v in o.data.vertices]
    for a in (.1,.5,.9):
        for b in (.1,.5,.9):
            target=q[0].lerp(q[1],a).lerp(q[3].lerp(q[2],a),b); direction=(target-eye).normalized()
            hit,loc,n,idx,obj,m=s.ray_cast(dg,eye,direction,distance=(target-eye).length+.005)
            if not hit or obj!=o:
                blocked.append((o.name,a,b,obj.name if hit else 'aucun'))
print('VISIBILITE', 'OK' if not blocked else blocked)

import os, sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import forme as fm
def clip(poly,a,b,c):
    result=[]
    for i,P in enumerate(poly):
        Q=poly[(i+1)%len(poly)]; u=a*P[0]+b*P[1]+c; v=a*Q[0]+b*Q[1]+c
        if u>=0: result.append(P)
        if (u>=0)!=(v>=0):
            t=u/(u-v); result.append((P[0]+t*(Q[0]-P[0]),P[1]+t*(Q[1]-P[1])))
    return result
def area(poly):
    return abs(sum(poly[i][0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*poly[i][1] for i in range(len(poly)))/2) if len(poly)>=3 else 0
# La découpe des tôles autour de la bulle, en plan, côté gauche, fermée sur l'axe : convexe.
coupe=fm.decoupe()+[(0.0,fm.decoupe()[0][1])]
cx=sum(x for x,_ in coupe)/len(coupe); cy=sum(y for _,y in coupe)/len(coupe); rules=[]
for (x0,y0),(x1,y1) in zip(coupe,coupe[1:]+coupe[:1]):
    a,b=y1-y0,-(x1-x0); c=-(a*x0+b*y0)
    if (a,b)!=(0,0): rules.append((a,b,c) if a*cx+b*cy+c>0 else (-a,-b,-c))
overlaps=[]
for name in ('Coque | sous-structure','Coque | panneaux structurels','Coque | trappes et marquages'):
    o=bpy.data.objects[name]
    for f in o.data.polygons:
        vs=[o.matrix_world @ o.data.vertices[i].co for i in f.vertices]
        if sum(v.z for v in vs)<0: continue   # le ventre : la verrière est sur le dessus
        poly=[(abs(v.x),v.y) for v in vs]
        for a,b,c in rules:
            if not poly: break
            poly=clip(poly,a,b,c)
        ar=area(poly)
        # Les tôles touchent le pourtour bord à bord : tolérer les éclats de chanfrein sous 10 mm².
        if ar>1e-5: overlaps.append((name,f.index,ar))
print('RACCORD VERRIERE', 'OK' if not overlaps else overlaps[:20])
# La bulle : son pied sur le dessus creusé, son sommet à la hauteur prévue.
glass=bpy.data.objects['Canopy_Glass']
verts=[glass.matrix_world @ v.co for v in glass.data.vertices]
pied=[abs(v.z-fm.dessus_z(v.x,v.y)) for v in verts if fm.goutte(v.y)<1e-6 or abs(abs(v.x)-fm.goutte(v.y))<1e-4]
shape_error=max(pied+[max(v.z for v in verts)-fm.GZT-.002,0])
print('BULLE', 'OK' if shape_error<.012 else round(shape_error,4), 'ecart_max_m',round(shape_error,4))
# Tester les sommets et les centres des faces de la cuve contre la surface
# inférieure de la carène : une cuve ne doit pas percer la coque par-dessous.
carene=bpy.data.objects['Coque | carene']; inv=carene.matrix_world.inverted()
protrusions=[]
for name in ('Cockpit | cuve structurelle','Cockpit | plancher'):
    o=bpy.data.objects[name]
    for face in o.data.polygons:
        vertices=[o.matrix_world @ o.data.vertices[i].co for i in face.vertices]
        samples=vertices+[sum(vertices,Vector())/len(vertices)]
        for v in samples:
            start=inv @ Vector((v.x,v.y,-5)); ok,hit,_,_=carene.ray_cast(start,Vector((0,0,1)))
            if ok and v.z < (carene.matrix_world @ hit).z-.012:
                protrusions.append((name,face.index,round(v.z-(carene.matrix_world @ hit).z,3)))
print('FOND DE CUVE', 'OK' if not protrusions else protrusions[:20])
above=[]
for o in bpy.data.collections['Spaceship_Cockpit'].objects:
    if o.type!='MESH' or o.name=='Canopy_Glass' or o.name.startswith('Verriere |'): continue
    for vertex in o.data.vertices:
        v=o.matrix_world @ vertex.co; zb=fm.bulle_z(v.x,v.y)
        ztop=max(fm.dessus_z(v.x,v.y),zb if zb is not None else -9)
        if v.z>ztop+.01: above.append((o.name,round(v.z-ztop,3)))
print('VOLUME SOUS VERRIERE', 'OK' if not above else above[:20])
# Les tuyères restent dans la poupe : aucun sommet au-delà du plan y + 0,125 z = 2,6.
beyond=[]
for o in bpy.data.collections['Spaceship_Engines'].objects:
    if o.type!='MESH': continue
    worst=max((o.matrix_world @ v.co).y+.125*(o.matrix_world @ v.co).z-2.6 for v in o.data.vertices)
    if worst>0: beyond.append((o.name,round(worst,3)))
print('TUYERES DANS LA POUPE', 'OK' if not beyond else beyond)
if blocked or overlaps or protrusions or above or beyond or shape_error>=.012: raise RuntimeError('Contrôle géométrique échoué')
