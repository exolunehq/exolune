"""Coque et cockpit du chasseur : géométrie modifiable avant export."""
import bpy, bmesh, math, os, random
from mathutils import Matrix, Vector

# Outils de construction : chaque pièce est un maillage à faces planes et arêtes
# vives, assemblé face par face avec son matériau et ses UV.
def newell(pts):
    n=Vector()
    for a,b in zip(pts,pts[1:]+pts[:1]): n+=Vector(((a.y-b.y)*(a.z+b.z),(a.z-b.z)*(a.x+b.x),(a.x-b.x)*(a.y+b.y)))
    return n
def centre(pts): return sum(pts,Vector())/len(pts)
def oriented(pts,direction): return pts if newell(pts).dot(direction)>0 else pts[::-1]
def planar(pts):
    n=newell(pts); n=n.normalized() if n.length>1e-12 else Vector((0,0,1))
    t=n.cross(Vector((0,0,1)) if abs(n.z)<.9 else Vector((1,0,0))).normalized(); b=n.cross(t)
    return [(p.dot(t),p.dot(b)) for p in pts]
class Piece:
    def __init__(self,name,collection):
        self.name=name; self.collection=collection; self.bm=bmesh.new(); self.uv=self.bm.loops.layers.uv.new('UVMap'); self.mats=[]
    def face(self,pts,mat,uvs=None):
        if mat not in self.mats: self.mats.append(mat)
        f=self.bm.faces.new([self.bm.verts.new(p) for p in pts]); f.material_index=self.mats.index(mat)
        if uvs is None: uvs=planar(pts)
        elif isinstance(uvs[0],(int,float)): uvs=[uvs]*len(pts)
        for loop,uv in zip(f.loops,uvs): loop[self.uv].uv=uv
    def loft(self,rings,mat,caps=(True,True),uv_end=None,flat=None,orient=True):
        # Anneaux successifs ; les faces regardent hors de la matière.
        rings=[[Vector(p) for p in r] for r in rings]
        if orient and newell(rings[0]).dot(centre(rings[-1])-centre(rings[0]))<0: rings=[r[::-1] for r in rings]
        for a,b in zip(rings,rings[1:]):
            for i in range(len(a)):
                j=(i+1)%len(a); self.face([a[i],a[j],b[j],b[i]],mat,flat)
        if caps[0]: self.face(rings[0][::-1],mat,flat)
        if caps[1]: self.face(rings[-1],mat,[uv_end(p) for p in rings[-1]] if uv_end else flat)
    def done(self):
        # Sommets soudés : les pièces rondes sont lissées, les arêtes de plus de 35° restent vives.
        bmesh.ops.remove_doubles(self.bm,verts=self.bm.verts,dist=1e-5)
        data=bpy.data.meshes.new(self.name); self.bm.to_mesh(data); self.bm.free(); data.update()
        data.shade_smooth(); data.set_sharp_from_angle(angle=math.radians(35))
        obj=bpy.data.objects.new(self.name,data); self.collection.objects.link(obj)
        for m in self.mats: data.materials.append(m)
        return obj
def rect(c,U,V,su,sv): return [c-U*su/2-V*sv/2,c+U*su/2-V*sv/2,c+U*su/2+V*sv/2,c-U*su/2+V*sv/2]
def block(pc,c,U,V,N,su,sv,sn,mat,ch=0,base=False,uv_end=None,flat=None):
    # Pavé posé par sa base en c ; ch chanfreine les arêtes supérieures.
    rings=[rect(c,U,V,su,sv)]
    rings+=[rect(c+N*(sn-ch),U,V,su,sv),rect(c+N*sn,U,V,su-2*ch,sv-2*ch)] if ch else [rect(c+N*sn,U,V,su,sv)]
    pc.loft(rings,mat,(base,True),uv_end,flat)
def _ring(c,U,V,r,sides): return [c+(U*math.cos(2*math.pi*i/sides)+V*math.sin(2*math.pi*i/sides))*r for i in range(sides)]
def tube(pc,a,b,r,mat,sides=8,r2=None,caps=(False,True)):
    a,b=Vector(a),Vector(b); N=(b-a).normalized(); U=N.orthogonal().normalized(); V=N.cross(U)
    pc.loft([_ring(a,U,V,r,sides),_ring(b,U,V,r if r2 is None else r2,sides)],mat,caps)
def lathe(pc,c,N,profile,mat,sides=12,caps=(False,True)):
    # Profil (rayon, hauteur) parcouru matière à droite : extérieur en montant.
    U=N.orthogonal().normalized(); V=N.cross(U)
    pc.loft([_ring(c+N*h,U,V,r,sides) for r,h in profile],mat,caps,orient=False)

def construire(root, ship, cockpit, material, box, rod, link_only, metal, dark, edge, rubber, seat, screen, cyan, amber, red):
    def remove(name):
        o=bpy.data.objects.get(name)
        if o: bpy.data.objects.remove(o,do_unlink=True)
    for o in list(cockpit.objects):
        if o.type=='MESH': bpy.data.objects.remove(o,do_unlink=True)
    for name in ('Hull_Main','Hull_Armor_Plates','Hull_Armor_Details'): remove(name)
    hull=bpy.data.collections['Spaceship_Hull']
    # Les valeurs sont linéaires : proches de la texture de coque décodée sRGB.
    def teinte(name,tint):
        # Même tôle texturée que la coque, multipliée par une teinte : glTF
        # l'exporte en facteur de couleur, sans image supplémentaire.
        m=metal.copy(); m.name=name; nt=m.node_tree; p=nt.nodes['Principled BSDF']
        tex=p.inputs['Base Color'].links[0].from_node
        mix=nt.nodes.new('ShaderNodeMix'); mix.data_type='RGBA'; mix.blend_type='MULTIPLY'; mix.inputs['Factor'].default_value=1
        sock=lambda socks,ident: next(x for x in socks if x.identifier==ident)
        sock(mix.inputs,'B_Color').default_value=(*tint,1)
        nt.links.new(tex.outputs['Color'],sock(mix.inputs,'A_Color')); nt.links.new(sock(mix.outputs,'Result_Color'),p.inputs['Base Color'])
        m.diffuse_color=(*[.37*t for t in tint],1)
        return m
    mid=teinte('Jeu | Blindage moyen',(.68,.70,.73))
    sombre=teinte('Jeu | Joint encrasse',(.34,.31,.28))
    # Pièces sans rivets : fonds de trappe, flancs de carène, trappes de train.
    reprise=teinte('Jeu | Peinture reprise',(.88,.88,.87)); ventre=teinte('Jeu | Ventre',(.72,.71,.69))
    # Livrée des tôles : peinture d'origine, deux reprises à peine plus sombres
    # tirées au hasard, bande bleue passée sur les capots arrière, nez bleu-gris.
    # Elles portent en plus une carte de normales et d'occlusion cuite sur leur
    # deuxième UV (rivets) : leurs matériaux « Jeu | Tole » sont distincts.
    toles=[teinte('Jeu | Tole',(1,1,1)),teinte('Jeu | Tole passee',(.94,.93,.90)),teinte('Jeu | Tole reprise',(.88,.88,.87)),
           teinte('Jeu | Tole bleue',(.30,.46,.82)),teinte('Jeu | Tole nez',(.24,.33,.58))]
    toles_ventre=[teinte('Jeu | Tole ventre',(.72,.71,.69)),teinte('Jeu | Tole ventre reprise',(.68,.67,.655))]
    livree=material('Jeu | Livree rouge',(.42,.045,.035),0,.55)
    graphite=material('Jeu | Ceramique graphite',(.055,.075,.082),.55,.56)
    accent=material('Jeu | Peinture marquage',(.62,.43,.18),.28,.55)
    white=material('Jeu | Marquage clair',(.63,.68,.65),.2,.64)
    safety=material('Jeu | Plastique securite',(.32,.018,.012),.05,.42)
    # Paramétrisation des deux facettes supérieures de la pyramide d'origine.
    apex=Vector((0,-7.18,0)); top=Vector((0,2.3375,2.10)); chine=Vector((3.10,2.59525,.038))
    low=Vector((3.10,2.60475,-.038)); cheek=Vector((2.74,2.6369,-.295)); bottom=Vector((0,2.85,-2))
    # Contour de la verrière d'Antigravity : les équipements s'y adaptent.
    F=.332; S=.692; A=.788; V=.437
    def point(u,v,side=1,ra=top,rb=chine):
        p=apex.lerp(ra.lerp(rb,v),u); p.x*=side; return p
    def clip(poly, a,b,c, positive=True):
        result=[]
        for i,p in enumerate(poly):
            q=poly[(i+1)%len(poly)]; fp=a*p[0]+b*p[1]+c; fq=a*q[0]+b*q[1]+c
            inp=fp>=-1e-9 if positive else fp<=1e-9
            inq=fq>=-1e-9 if positive else fq<=1e-9
            if inp: result.append(p)
            if inp != inq:
                t=fp/(fp-fq); result.append((p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
        return result
    # Retire le triangle de verrière de chaque facette : trois régions disjointes.
    def outside(poly):
        # point(u,v) est bilinéaire en u,v. Le contour du vitrage est rectiligne
        # dans les coordonnées barycentriques (u,w=u*v), pas dans (u,v).
        # Découper dans ces coordonnées évite qu'une plaque traverse le verre.
        W=S*V
        rules=[(1,-(S-F)/W,-F),(-1,-(A-S)/W,A),(0,-1,W)]
        rest=[(u,u*v) for u,v in poly]; out=[]
        for a,b,c in rules:
            piece=clip(rest,a,b,c,False)
            if len(piece)>=3: out.append([(u,w/u if abs(u)>1e-9 else 0) for u,w in piece])
            rest=clip(rest,a,b,c,True)
            if len(rest)<3: break
        return out
    def mesh_object(name, polygons, mats, collection=hull):
        vertices=[]; faces=[]; indices=[]
        for coords,matidx in polygons:
            if len(coords)<3: continue
            start=len(vertices); vertices.extend([tuple(p) for p in coords]); faces.append(tuple(range(start,start+len(coords)))); indices.append(matidx)
        data=bpy.data.meshes.new(name); data.from_pydata(vertices,[],faces); data.update()
        obj=bpy.data.objects.new(name,data); collection.objects.link(obj)
        for m in mats: obj.data.materials.append(m)
        for p,i in zip(obj.data.polygons,indices): p.material_index=i
        return obj
    def facette(poly,side,ra=top,rb=chine,shrink=0):
        # Polygone (u,v) posé sur une facette, tourné vers l'extérieur.
        pts=[point(u,v,side,ra,rb) for u,v in poly]
        c=sum(pts,Vector())/len(pts)
        if shrink: pts=[p.lerp(c,min(.08,shrink/max((p-c).length,.01))) for p in pts]
        n=(ra-apex).cross(rb-apex); n.x*=side; n.normalize()
        if n.dot(Vector((c.x,0,c.z)))<0: n=-n
        return (pts if newell(pts).dot(n)>0 else pts[::-1]),n
    def plaque(pts,n,mat,out,h=.012,bevel=.005,lift=0):
        # Tôle d'épaisseur h posée sur son appui : chant incliné, dessus chanfreiné.
        c=sum(pts,Vector())/len(pts)+n*lift; pts=[p+n*lift for p in pts]
        haut=[p.lerp(c,min(.3,bevel/max((p-c).length,.01)))+n*h for p in pts]
        for i in range(len(pts)):
            j=(i+1)%len(pts); out.append(([pts[i],pts[j],haut[j],haut[i]],mat))
        out.append((haut,mat))
    def inset2d(poly,d):
        # Contour convexe, sens trigonométrique, décalé de d vers l'intérieur.
        lines=[]
        for (ax,aw),(bx,bw) in zip(poly,poly[1:]+poly[:1]):
            L=math.hypot(bx-ax,bw-aw); ex,ew=(bx-ax)/L,(bw-aw)/L; lines.append(((ax-ew*d,aw+ex*d),(ex,ew)))
        pts=[]
        for (p1,e1),(p2,e2) in zip(lines[-1:]+lines[:-1],lines):
            t=((p2[0]-p1[0])*e2[1]-(p2[1]-p1[1])*e2[0])/(e1[0]*e2[1]-e1[1]*e2[0]); pts.append((p1[0]+e1[0]*t,p1[1]+e1[1]*t))
        return pts
    def decale(pts,n,d):
        # Même décalage pour un polygone plan en 3D, d > 0 vers l'intérieur.
        U=(pts[1]-pts[0]).normalized(); V=n.cross(U); o=pts[0]
        return [o+U*x+V*y for x,y in inset2d([((p-o).dot(U),(p-o).dot(V)) for p in pts],d)]
    def normale(side,ra,rb):
        n=(ra-apex).cross(rb-apex); n.x*=side; c=(apex+ra+rb)/3; c.x*=side; n.normalize()
        return n if n.dot(Vector((c.x,0,c.z)))>0 else -n
    def rect_uv(u0,u1,v0,v1): return [(u0,v0),(u1,v0),(u1,v1),(u0,v1)]

    # Peau continue de la pointe au cadre de poupe ; les tôles s'y posent.
    base=[]
    for side in (-1,1):
        for poly in outside([(0,0),(1,0),(1,1)]): base.append((facette(poly,side)[0],0))
    mesh_object('Coque | sous-structure',base,[sombre])

    # Tôlerie : sections entre cadres principaux (u), bandes entre lisses (v),
    # joints décalés d'une bande à l'autre pour ne jamais former de grille.
    # (u0, u1, [(v0, v1, joints en fraction de la section)]).
    DESSUS=[(0,.12,[(0,.93,()),(.93,1,())]),
            (.12,.33,[(0,.40,(.55,)),(.40,.80,(.35,.75)),(.80,.93,(.5,)),(.93,1,(.3,.7))]),
            (.33,.79,[(0,.30,(.45,)),(.30,.55,(.3,.68)),(.55,.80,(.5,)),(.80,.93,(.25,.6,.85)),(.93,1,(.35,.7))]),
            (.79,1,[(0,.07,(.5,)),(.07,.30,(.55,)),(.30,.55,(.4,)),(.55,.80,(.6,)),(.80,.93,(.35,.7)),(.93,1,(.5,))])]
    VENTRE=[(0,.14,[(0,1,())]),
            (.14,.40,[(0,.18,(.5,)),(.18,.55,(.4,)),(.55,.85,(.6,)),(.85,1,(.3,.7))]),
            (.40,.75,[(0,.12,(.3,.65)),(.12,.40,(.5,)),(.40,.68,(.35,.7)),(.68,.90,(.55,)),(.90,1,(.25,.6))]),
            (.75,1,[(0,.12,(.5,)),(.12,.40,(.4,)),(.40,.68,(.6,)),(.68,.90,(.3,.7)),(.90,1,(.5,))])]
    def cellules(plan):
        for u0,u1,bandes in plan:
            for v0,v1,joints in bandes:
                us=[u0]+[u0+(u1-u0)*f for f in joints]+[u1]
                for ua,ub in zip(us,us[1:]): yield ua,ub,v0,v1
    tirage=random.Random(7); details=[]; rivets_hp=[]; ILES={}
    RIVET,PAS=.011,.11
    def rivets(pts,n,aretes,pas=PAS,retrait=.022):
        # Rangée de rivets parallèle aux arêtes choisies, sur le dessus de la pièce.
        # Dômes de 2 mm destinés à la cuisson seulement : ils ne sont pas exportés.
        try: ins=decale(pts,n,retrait)
        except ZeroDivisionError: return
        if newell(ins).dot(n)<=0: return
        for i in aretes:
            a,b=ins[i],ins[(i+1)%len(ins)]; e=b-a; L=e.length
            if L<.05: continue
            e/=L; k=max(1,int(L/pas)); w=n.cross(e)
            for j in range(k):
                c=a+e*(L*(j+.5)/k); r=_ring(c,e,w,RIVET/2,8); tip=c+n*.002
                for q in range(8): rivets_hp.append((oriented([r[q],r[(q+1)%8],tip],n),0))
    def tole(uv,v_lisse,side,ra,rb,mat,out):
        # Une tôle : joint de 4 mm, angles parfois chanfreinés, rivets sur ses
        # cadres et sur sa lisse basse. tags[i] décrit l'arête i -> i+1.
        m=len(uv); n=normale(side,ra,rb)
        pts=[point(u,v,side,ra,rb) for u,v in uv]
        tags=[(abs(uv[i][0]-uv[(i+1)%m][0])<1e-7) or (abs(uv[i][1]-v_lisse)<1e-7 and abs(uv[(i+1)%m][1]-v_lisse)<1e-7) for i in range(m)]
        if newell(pts).dot(n)<0: pts=pts[::-1]; tags=[tags[(m-2-j)%m] for j in range(m)]
        keep=[i for i in range(m) if (pts[(i+1)%m]-pts[i]).length>1e-4]
        pts=[pts[i] for i in keep]; tags=[tags[i] for i in keep]
        k=0
        while len(pts)>3 and k<len(pts):
            a,b,c=pts[k-1],pts[k],pts[(k+1)%len(pts)]
            if (b-a).normalized().cross((c-b).normalized()).length<1e-5: pts.pop(k); tags.pop(k)
            else: k+=1
        if len(pts)<3: return
        pts=decale(pts,n,.002)
        P,T=[],[]
        for i,p in enumerate(pts):
            a,b=pts[i-1],pts[(i+1)%len(pts)]
            if tirage.random()<.25 and (a-p).length>.2 and (b-p).length>.2:
                P+=[p+(a-p).normalized()*.035,p+(b-p).normalized()*.035]; T+=[False,tags[i]]
            else: P.append(p); T.append(tags[i])
        start=len(out); plaque(P,n,mat,out,bevel=.0015); ILES.setdefault(id(out),[]).append((start,len(out)-start,P,n))
        rivets([p+n*.012 for p in P],n,[i for i,t in enumerate(T) if t])
    plates=[]; ventre_=[]
    for side in (-1,1):
        for ua,ub,v0,v1 in cellules(DESSUS):
            mat=4 if ub<=.12 else 3 if ua>=.86 else (0 if tirage.random()<.6 else 1 if tirage.random()<.6 else 2)
            for part in outside(rect_uv(ua,ub,v0,v1)):
                if len(part)>=3: tole(part,v0,side,top,chine,mat,plates)
        for ra,rb,mat in ((chine,low,0),(low,cheek,0),(cheek,bottom,1)):
            ventre_.append((facette([(0,0),(1,0),(1,1)],side,ra,rb)[0],mat))
        for ua,ub,v0,v1 in cellules(VENTRE):
            tole(rect_uv(ua,ub,v0,v1),v0,side,cheek,bottom,2 if tirage.random()<.75 else 3,ventre_)
    panels=mesh_object('Coque | panneaux structurels',plates,toles)
    carene=mesh_object('Coque | carene',ventre_,[ventre,sombre]+toles_ventre)
    # Vitrage unique par flanc, sans arceau central ni traverse.
    glassfaces=[]
    for side in (-1,1):
        pts=[point(F,0,side),point(S,V,side),point(A,0,side)]
        if (pts[1]-pts[0]).cross(pts[2]-pts[0]).z<0: pts.reverse()
        glassfaces.append((pts,0))
    mesh_object('Canopy_Glass',glassfaces,[screen],cockpit)
    # Un simple joint sombre de pourtour, sans renfort qui traverse le vitrage.
    for side in (-1,1):
        for ua,va,ub,vb in ((F,0,S,V),(S,V,A,0)):
            rod('Verriere | joint perimetrique',point(ua,va,side),point(ub,vb,side),.012,rubber,8)

    # Équipements de peau, chacun dans une seule tôle : trappes rivetées, trappes
    # de train à joint large, bouchons, grilles, marquages peints, antennes.
    # Décalques posés 0,3 mm au-dessus du dessus des tôles.
    LEVE=.0123
    def dans_une_tole(plan,u0,u1,v0,v1):
        return any(ua+.004<=u0 and u1<=ub-.004 and va+.004<=v0 and v1<=vb-.004 for ua,ub,va,vb in cellules(plan))
    def trappe(u0,u1,v0,v1,side,ra=top,rb=chine,plan=DESSUS,ch=.03,rivetee=True,joint=.007,fond=4):
        assert dans_une_tole(plan,u0,u1,v0,v1), ('trappe à cheval sur un joint',u0,u1,v0,v1)
        pts,n=facette(rect_uv(u0,u1,v0,v1),side,ra,rb); pts=[p+n*LEVE for p in pts]
        P=[]
        for i,p in enumerate(pts): P+=[p+(pts[i-1]-p).normalized()*ch,p+(pts[(i+1)%4]-p).normalized()*ch]
        details.append((P,fond)); O=decale(P,n,-joint)
        for i in range(len(P)):
            j=(i+1)%len(P); details.append((oriented([P[i],P[j],O[j],O[i]],n),2))
        if rivetee: rivets(P,n,range(len(P)),pas=.05,retrait=.014)
    def bouchon(u,v,r,side,ra=top,rb=chine):
        n=normale(side,ra,rb); c=point(u,v,side,ra,rb)+n*LEVE; U=n.orthogonal().normalized(); W=n.cross(U)
        a,b=_ring(c,U,W,r,16),_ring(c,U,W,r+.006,16)
        details.append((oriented(a,n),3)); details.append((oriented(_ring(c+n*.0002,U,W,r*.35,8),n),2))
        for i in range(16):
            j=(i+1)%16; details.append((oriented([a[i],a[j],b[j],b[i]],n),2))
    def grille(u0,u1,v0,v1,side,ra=top,rb=chine,plan=DESSUS,lames=6):
        assert dans_une_tole(plan,u0,u1,v0,v1), ('grille à cheval sur un joint',u0,u1,v0,v1)
        n=normale(side,ra,rb); q=[point(u,v,side,ra,rb)+n*LEVE for u,v in rect_uv(u0,u1,v0,v1)]
        details.append((oriented(q,n),2))
        for k in range(lames):
            t0,t1=(k+.3)/lames,(k+.7)/lames
            details.append((oriented([q[0].lerp(q[3],t0),q[1].lerp(q[2],t0),q[1].lerp(q[2],t1),q[0].lerp(q[3],t1)],n),3))
    def peint(u0,u1,v0,v1,side,mat):
        assert dans_une_tole(DESSUS,u0,u1,v0,v1), ('marquage à cheval sur un joint',u0,u1,v0,v1)
        pts,n=facette(rect_uv(u0,u1,v0,v1),side); details.append(([p+n*LEVE for p in pts],mat))
    def antenne(p,t,up,h=.11,L=.20):
        # Lame d'antenne en flèche, plantée dans la tôle.
        s_=t.cross(up).normalized()
        f=[p+t*a+up*b+s_*.006 for a,b in ((0,0),(L,0),(L*.72,h),(L*.45,h))]; g=[q-s_*.012 for q in f]
        details.append((oriented(f,s_),3)); details.append((oriented(g,-s_),3))
        c=centre(f+g)
        for i in range(4):
            j=(i+1)%4; quad=[f[i],f[j],g[j],g[i]]; details.append((oriented(quad,centre(quad)-c),3))
    for side in (-1,1):
        trappe(.20,.27,.46,.74,side); trappe(.40,.50,.60,.74,side); trappe(.53,.60,.40,.52,side)
        trappe(.80,.865,.34,.50,side); trappe(.82,.90,.60,.74,side)
        grille(.87,.93,.83,.90,side); grille(.92,.98,.12,.26,side)
        bouchon(.66,.865,.028,side); bouchon(.17,.865,.02,side); bouchon(.70,.68,.03,side)
        peint(.205,.27,.765,.79,side,0); peint(.80,.86,.755,.772,side,1); peint(.80,.86,.778,.795,side,1)
        # Ventre : trappes de train avant et principal, trappes de service.
        trappe(.50,.60,.905,.995,side,cheek,bottom,VENTRE,ch=.02,rivetee=False,joint=.009,fond=5)
        trappe(.65,.745,.42,.66,side,cheek,bottom,VENTRE,ch=.04,rivetee=False,joint=.009,fond=5)
        trappe(.27,.36,.24,.48,side,cheek,bottom,VENTRE); trappe(.44,.53,.17,.33,side,cheek,bottom,VENTRE); trappe(.87,.95,.16,.34,side,cheek,bottom,VENTRE)
        grille(.92,.98,.46,.62,side,cheek,bottom,VENTRE)
        bouchon(.875,.79,.03,side,cheek,bottom)
    dos_=normale(1,top,chine); dos_=Vector((0,dos_.y,dos_.z)).normalized()
    antenne(point(.90,0)+dos_*.008,(top-apex).normalized(),dos_)
    quille=normale(1,cheek,bottom); quille=Vector((0,quille.y,quille.z)).normalized()
    for u in (.30,.68): antenne(point(u,1,1,cheek,bottom)+quille*.008,(bottom-apex).normalized(),quille,.09,.17)
    mesh_object('Coque | trappes et marquages',details,[white,livree,sombre,mid,reprise,ventre])
    cuisson=bpy.data.collections.new('Cuisson'); bpy.context.scene.collection.children.link(cuisson)
    mesh_object('Cuisson | rivets',rivets_hp,[mid],cuisson)

    # Poupe : cadre fermant tout le losange arrière, fond en retrait, trois
    # tuyères sur brides, vérins d'orientation. Le contour de poupe est plan.
    for name in ('Rear_Bulkhead_Assembly','Rear_Trench_Greebles')+tuple(f'Thruster_{k}_{i}' for k in ('Nozzle','Core') for i in (1,2,3)): remove(name)
    engines=bpy.data.collections['Spaceship_Engines']
    tuyere=material('Jeu | Tuyere',(.10,.085,.07),.9,.36)
    vert=material('Jeu | Feu vert',(.02,.6,.12),.05,.4,1.5)
    # Intérieur de poupe peint : il reste lisible à l'ombre, où le métal noircit.
    peinture=material('Jeu | Peinture poupe',(.12,.13,.14),.2,.58)
    Xr=Vector((1,0,0)); Ya=Vector((0,1,0)); Nr=Vector((0,1,.125)).normalized(); Zr=Vector((0,-.125,1)).normalized()
    O0=Vector((0,2.6,0))   # le plan de poupe est y + 0,125 z = 2,6
    def rp(x,w,h=0): return O0+Xr*x+Zr*w+Nr*h
    def flat(p): q=p-O0; return (q.dot(Xr),q.dot(Zr))
    WC,DF,HC=.16,.40,.04   # largeur du cadre, retrait du fond, saillie du cadre
    simp=[flat(top),flat((chine+low)/2),flat(cheek),flat(bottom)]; simp+=[(-x,w) for x,w in reversed(simp[1:-1])]
    inner=inset2d(simp[::-1],WC)[::-1]
    O=[top,chine,low,cheek,bottom]+[Vector((-p.x,p.y,p.z)) for p in (cheek,low,chine)]
    Oa=[p+Nr*HC for p in O]; I=[rp(x,w,HC) for x,w in inner]; Ib=[rp(x,w,-DF) for x,w in inner]
    idx=[0,1,1,2,3,4,5,5]
    def radial(c): r=c-O0; return r-Nr*r.dot(Nr)
    pp=Piece('Poupe | cadre et fond',hull)
    for i in range(8):
        j=(i+1)%8; q=[O[i],O[j],Oa[j],Oa[i]]; pp.face(oriented(q,radial(centre(q))),metal)
        q=[Oa[i],Oa[j],I[idx[j]],I[idx[i]]]; pp.face(oriented(q[:3] if idx[i]==idx[j] else q,Nr),metal)
    for k in range(6):
        l=(k+1)%6; q=[I[k],I[l],Ib[l],Ib[k]]; pp.face(oriented(q,-radial(centre(q))),peinture)
    pp.face(oriented(Ib,Nr),peinture)
    def demi(w):
        for (x0,w0),(x1,w1) in zip(inner[:4],inner[1:4]):
            if min(w0,w1)<=w<=max(w0,w1): return x0+(x1-x0)*(w-w0)/(w1-w0)
        return 0
    # Longerons au-dessus et au-dessous des tuyères, raidisseurs entre elles.
    for w in (.70,-.70): block(pp,rp(0,w,-DF),Xr,Zr,Nr,2*demi(w)-.06,.10,.10,mid,.01)
    for x in (-.625,.625): block(pp,rp(x,0,-DF),Xr,Zr,Nr,.05,1.30,.08,mid,.006)
    # Caissons de ventilation : cadre, fond sombre, lames.
    for w in (1.18,-1.12):
        c=rp(0,w,-DF); block(pp,c,Xr,Zr,Nr,.96,.30,.03,mid,.006); block(pp,c+Nr*.03,Xr,Zr,Nr,.90,.24,.004,dark)
        for k in range(6): block(pp,c+Nr*.03+Zr*(-.10+.04*k),Xr,Zr,Nr,.90,.012,.022,edge)
    # Feux de position aux pointes : rouge à gauche du pilote (+X), vert à droite.
    for s,mat in ((1,red),(-1,vert)): block(pp,rp(s*2.96,0,HC),Xr,Zr,Nr,.07,.05,.012,mat,.004)
    pp.done()
    # Tuyères compactes, perpendiculaires au fond et tenues dans la poupe : la
    # lèvre s'arrête 5 cm en retrait du plan de poupe, rien ne dépasse du vaisseau.
    BELL=[(.33,.14),(.37,.19),(.43,.24),(.50,.29),(.55,.32),(.575,.325),(.575,.35),(.535,.35),(.47,.30),(.40,.25),(.34,.21),(.29,.18)]
    for i,x in enumerate((-1.25,0,1.25)):
        en=Piece(f'Tuyere | {i+1}',engines)
        cb=rp(x,0,-DF)
        lathe(en,cb-Nr*.02,Nr,[(.60,0),(.60,.045),(.575,.07),(.45,.07)],peinture,24)
        for k in range(16):
            q=cb+Nr*.05+(Xr*math.cos(2*math.pi*k/16)+Zr*math.sin(2*math.pi*k/16))*.525; tube(en,q,q+Nr*.012,.014,edge,6)
        lathe(en,cb,Nr,[(.44,.03),(.44,.12),(.415,.14),(.33,.14)],edge,24)
        lathe(en,cb,Nr,BELL,tuyere,24)
        lathe(en,cb,Nr,[(.432,.233),(.45,.237),(.45,.253),(.437,.257)],edge,24)
        en.face(oriented(_ring(cb+Nr*.18,Xr,Zr,.29,24),Nr),cyan)
        # Deux vérins courts par tuyère, de la bride au raidisseur du divergent.
        for a in (math.radians(55),math.radians(125)):
            d=Xr*math.cos(a)+Zr*math.sin(a); a0=cb+Nr*.05+d*.53; a1=cb+Nr*.245+d*.47
            tube(en,a0,a0.lerp(a1,.55),.024,dark,8,caps=(True,True)); tube(en,a0.lerp(a1,.55),a1,.011,edge,8,caps=(False,True))
        lamp=bpy.data.objects.get(f'Light_Thruster_Glow_{i+1}')
        if lamp: lamp.location=cb+Nr*.30
        en.done()
    # UV à l'échelle du monde, une tuile de peinture pour 2 m : l'usure court
    # d'une tôle à l'autre, la coque se lit comme un seul revêtement.
    for o in list(hull.objects)+list(engines.objects):
        if o.type!='MESH': continue
        me=o.data; uv=me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
        for poly in me.polygons:
            nn=poly.normal; t=Ya-nn*Ya.dot(nn)
            if t.length<.3: t=Xr-nn*nn.x
            t.normalize(); b=nn.cross(t)
            for li in poly.loop_indices:
                p=o.matrix_world @ me.vertices[me.loops[li].vertex_index].co; uv.data[li].uv=(p.dot(t)/2,p.dot(b)/2)
    # Deuxième UV des tôles, UVDetail : une île par tôle, sans recouvrement,
    # projetée dans le même repère que UVMap pour partager les tangentes.
    iles=[]
    for obj,faces in ((panels,plates),(carene,ventre_)):
        for start,count,P,n in ILES[id(faces)]:
            t=(Ya-n*Ya.dot(n)).normalized(); b=n.cross(t); q=[(p.dot(t),p.dot(b)) for p in P]
            x0=min(x for x,_ in q); y0=min(y for _,y in q)
            iles.append((obj,start,count,t,b,x0,y0,max(x for x,_ in q)-x0,max(y for _,y in q)-y0))
    M=.012   # marge entre îles, en mètres
    side_=math.sqrt(sum((w+M)*(h+M) for *_,w,h in iles)/.8); place={}; x=y=row=0
    for k in sorted(range(len(iles)),key=lambda k:-iles[k][8]):
        w,h=iles[k][7],iles[k][8]
        if x+w+M>side_: x=0; y+=row; row=0
        place[k]=(x+M/2,y+M/2); x+=w+M; row=max(row,h+M)
    echelle=1/max(side_,y+row)
    for obj in (panels,carene):
        # Couche vide : les faces hors tôles (fonds de carène) restent en un point et ne cuisent rien.
        me=obj.data; me.uv_layers.new(name='UVDetail',do_init=False); me.uv_layers['UVMap'].active_render=True
    for k,(obj,start,count,t,b,x0,y0,w,h) in enumerate(iles):
        me=obj.data; uvd=me.uv_layers['UVDetail']; ox,oy=place[k]
        for poly in me.polygons[start:start+count]:
            for li in poly.loop_indices:
                p=me.vertices[me.loops[li].vertex_index].co; uvd.data[li].uv=((p.dot(t)-x0+ox)*echelle,(p.dot(b)-y0+oy)*echelle)
    print('UVDETAIL',len(iles),'tôles',round(echelle*4096),'px/m en 4096')

    # Cockpit : pièces posées en coordonnées du vaisseau, sans recadrage.
    # Les parois sont des plans accrochés aux arêtes de la verrière ; pupitre,
    # auvent, ailes et consoles en sont déduits, puis les modules standards de
    # modules_cockpit.py y sont vissés. Toutes les faces sont planes.
    import modules_cockpit as mc
    structure=material('Jeu | Structure cockpit',(.17,.18,.19),.15,.62)
    antireflet=material('Jeu | Antireflet',(.012,.013,.014),0,.92)
    lens=material('Jeu | Voyant eteint',(.035,.032,.026),0,.25)
    combiner=material('Jeu | Combineur ATH',(.10,.30,.22),0,.08)
    combiner.diffuse_color=(.10,.30,.22,.25); combiner.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value=.25
    combiner.surface_render_method='BLENDED'
    lit={'amber':amber,'cyan':cyan,'red':red,None:lens}
    image_mats={}
    def image_mat(filename, emissive=False):
        if filename in image_mats: return image_mats[filename]
        m=material('Jeu | '+filename,(1,1,1),.05,.48,1.0 if emissive else None)
        p=m.node_tree.nodes.get('Principled BSDF'); n=m.node_tree.nodes.new('ShaderNodeTexImage')
        n.image=bpy.data.images.load(os.path.join(root,filename+'.png'),check_existing=True); n.image.pack()
        m.node_tree.links.new(n.outputs['Color'],p.inputs['Base Color'])
        if emissive: m.node_tree.links.new(n.outputs['Color'],p.inputs['Emission Color'])
        image_mats[filename]=m
        return m
    plaques=image_mat('plaques'); plaques.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.62
    X=Vector((1,0,0)); Y=Vector((0,1,0)); Z=Vector((0,0,1))

    # Cuve : parois planes passant par les arêtes du vitrage, évasées vers le bas.
    Fp=point(F,0); Ap=point(A,0)
    def plane(p,n): n=n.normalized(); return n,n.dot(p)
    def meet(*planes): return Matrix([n for n,_ in planes]).inverted() @ Vector([k for _,k in planes])
    LEAN=.08
    SILL=(point(S,V).z-Fp.z)/(point(S,V).y-Fp.y)   # pente du seuil de verrière
    floor=plane(Vector((0,-2.65,-.30)),Vector((0,.2,2.41)))
    front_wall=plane(Fp,X.cross(Fp-Vector((0,-2.65,-.30))))
    rear_wall=plane(Ap,X.cross(Ap-Vector((0,-.24,-.50))))
    W={}
    for side in (-1,1):
        Sp=point(S,V,side); down=Vector((side*LEAN,0,-1)).normalized()
        n1=(Sp-Fp).cross(down); n2=(Ap-Sp).cross(down)
        w1=plane(Fp,n1 if n1.x*side<0 else -n1); w2=plane(Sp,n2 if n2.x*side<0 else -n2)
        e=Sp-Fp
        W[side]=dict(S=Sp,down=down,w1=w1,w2=w2,nin=Vector((-e.y,e.x,0)).normalized()*side,
                     Cf=meet(w1,front_wall,floor),Cm=meet(w1,w2,floor),Cr=meet(w2,rear_wall,floor))
    def fz(y): n,k=floor; return (k-n.y*y)/n.z
    def wall_x(y,z,side): (n,k)=W[side]['w1']; return (k-n.y*y-n.z*z)/n.x
    Y0=-2.10
    def cw(y,z,d,side):
        # Point de console : z suit la pente du seuil, d rentre depuis la paroi.
        z=z+SILL*(y-Y0); return Vector((wall_x(y,z,side),y,z))+W[side]['nin']*d
    inside=Vector((0,-1.4,.2))
    def facing_in(pts): return oriented(pts,inside-centre(pts))
    cuve=Piece('Cockpit | cuve structurelle',cockpit)
    for s in (-1,1):
        w=W[s]
        cuve.face(facing_in([Fp,w['S'],w['Cm'],w['Cf']]),structure)
        cuve.face(facing_in([w['S'],Ap,w['Cr'],w['Cm']]),structure)
    cuve.face(facing_in([Fp,W[1]['Cf'],W[-1]['Cf']]),structure)
    cuve.face(facing_in([Ap,W[-1]['Cr'],W[1]['Cr']]),structure)
    cuve.done()
    Nf=floor[0]; Yf=Nf.cross(X)
    sol=Piece('Cockpit | plancher',cockpit)
    sol.face(facing_in([W[s][c]+Nf*.012 for s,c in ((-1,'Cf'),(-1,'Cm'),(-1,'Cr'),(1,'Cr'),(1,'Cm'),(1,'Cf'))]),graphite)
    for k in range(9):
        y=-2.58+k*.075; block(sol,Vector((0,y,fz(y)+.012)),X,Yf,Nf,.46,.014,.004,rubber)
    sol.done()

    # Rails de seuil usinés sous chaque arête du vitrage, boulonnés à pas régulier.
    rails=Piece('Cockpit | rails de verriere',cockpit)
    PROFIL_RAIL=[(0,0),(0,.022),(.045,.025),(.06,.012),(.06,0)]   # (descente, rentrée)
    for s in (-1,1):
        w=W[s]
        for a,b,(n,_) in ((Fp,w['S'],w['w1']),(w['S'],Ap,w['w2'])):
            ra,rb=[[p+w['down']*dd+n*ii for dd,ii in PROFIL_RAIL] for p in (a,b)]
            # Aux pointes du vitrage, les deux rails se rejoignent en onglet sur l'axe.
            e=(b-a).normalized()
            if abs(a.x)<1e-6: ra=[q-e*(q.x/e.x) for q in ra]
            if abs(b.x)<1e-6: rb=[q-e*(q.x/e.x) for q in rb]
            rails.loft([ra,rb],structure)
            L=(b-a).length
            for k in range(1,int(L/.11)):
                q=a.lerp(b,k*.11/L)+w['down']*.03+n*.0236
                tube(rails,q,q+n*.003,.0045,edge,6)
    rails.done()

    rects=mc.atlas(); TA=mc.ATLAS; K=mc.ECHELLE
    tx,ty,_,_=rects[mc.TEINTE]; teinte=((tx+16)/TA,1-(ty+16)/TA)
    SEG={'0':'abcdef','1':'bc','4':'fgbc','8':'abcdefg'}
    def chiffres(pc,c,U,V,N,text):
        w,h,t=.0085,.014,.0016
        seg={'a':(0,h/2,w,t),'b':(w/2,h/4,t,h/2),'c':(w/2,-h/4,t,h/2),'d':(0,-h/2,w,t),'e':(-w/2,-h/4,t,h/2),'f':(-w/2,h/4,t,h/2),'g':(0,0,w,t)}
        for x,ch in zip((-.0225,-.0095,.0095,.0225),text):
            for k in SEG[ch]:
                dx,dy,sw,sh=seg[k]; block(pc,c+U*(x+dx)+V*dy,U,V,N,sw,sh,.0004,amber)
        for dy in (-.003,.003): block(pc,c+V*dy,U,V,N,.0016,.0016,.0004,amber)
    def equip(pc,it,top,U,V,N,k):
        kind=it[0]
        if kind in ('line','box','slot','text'): return
        _,u,v,label,*opt=it; opt=opt[0] if opt else None; P=top(u,v)
        if kind in ('tog','gtog'):
            tube(pc,P,P+N*.004,.0055,edge,6)
            tip=P+N*.022+V*(.007 if k%3 else -.007)
            tube(pc,P+N*.004,tip,.0022,edge,6,.0016)
            tube(pc,tip,tip+(tip-P).normalized()*.004,.003,edge,6)
            if kind=='gtog':
                a=P-U*.012; b=P+U*.012
                for q in (a,b): tube(pc,q,q+N*.026,.0016,safety,6)
                tube(pc,a+N*.026,b+N*.026,.0016,safety,6,caps=(True,True))
        elif kind=='rot':
            tube(pc,P,P+N*.002,.014,rubber,12)
            tube(pc,P+N*.002,P+N*.015,.0095,rubber,12,.0082)
            block(pc,P+N*.015+V*.003,U,V,N,.0018,.007,.0008,white)
        elif kind=='push':
            block(pc,P,U,V,N,.021,.021,.004,rubber,.001); block(pc,P+N*.004,U,V,N,.016,.016,.003,lit[opt])
        elif kind=='cb':
            tube(pc,P,P+N*.004,.0055,edge,8); tube(pc,P+N*.004,P+N*.012,.0038,rubber,8)
            tube(pc,P+N*.0075,P+N*.009,.004,white,8)
        elif kind=='lamp':
            block(pc,P,U,V,N,.030,.016,.003,rubber); block(pc,P+N*.003,U,V,N,.026,.012,.002,lit[opt])
        elif kind=='tb':
            block(pc,P,U,V,N,.016,.012,.002,rubber); block(pc,P+N*.002,U,V,N,.012,.008,.0008,lens)
        elif kind=='key':
            block(pc,P,U,V,N,.019,.019,.007,rubber,.0015)
        elif kind=='gauge':
            R=.045
            lathe(pc,P,N,[(R+.009,0),(R+.009,.008),(R+.006,.011),(R,.009),(R,0)],rubber,16,(False,False))
            ring=_ring(P+N*.003,U,V,R,16)
            pc.face(ring,image_mat(opt),[(.5+.48*math.cos(2*math.pi*i/16),.5+.48*math.sin(2*math.pi*i/16)) for i in range(16)])
        elif kind=='timer':
            block(pc,P,U,V,N,.072,.028,.005,rubber,.001); block(pc,P+N*.005,U,V,N,.062,.02,.0004,lens)
            chiffres(pc,P+N*.0054,U,V,N,'0418')
    def module(name,c,U,V,N):
        # Plaque sérigraphiée, quatre fixations quart de tour et ses commandes.
        (w,h),_,items=mc.MODULES[name]; x0,y0,x1,y1=rects[name]
        c=c+N*.0005; pc=Piece('Module | '+name,cockpit)
        def uv(p):
            q=p-c; return ((x0+(q.dot(U)+w/2)*K)/TA,1-(y1-(q.dot(V)+h/2)*K)/TA)
        block(pc,c,U,V,N,w,h,.004,plaques,.0015,uv_end=uv,flat=teinte)
        def top(u,v,z=.004): return c+U*(u-w/2)+V*(v-h/2)+N*z
        for u in (.008,w-.008):
            for v in (.008,h-.008): tube(pc,top(u,v),top(u,v,.0055),.0042,edge,8)
        for k,it in enumerate(items): equip(pc,it,top,U,V,N,k)
        pc.done()
        return top,U,V,N
    def mfd(c,U,V,N,file):
        # Même boîtier d'affichage trois fois : cadre usiné, touches de bord, vis.
        c=c+N*.0005; pc=Piece('Ecran | '+file+' | boitier',cockpit)
        wc=c+V*.03; f=rect(c+N*.021,U,V,.244,.294); win=rect(wc+N*.021,U,V,.20,.20); back=rect(wc+N*.008,U,V,.20,.20)
        pc.loft([rect(c,U,V,.25,.30),rect(c+N*.018,U,V,.25,.30),f],rubber,(False,False))
        for i in range(4):
            j=(i+1)%4
            pc.face([f[i],f[j],win[j],win[i]],rubber); pc.face([win[i],win[j],back[j],back[i]],rubber)
        for i in range(6):
            q=c+N*.021+U*(-.0875+.035*i)-V*.11
            block(pc,q,U,V,N,.022,.016,.005,graphite,.001); block(pc,q+N*.005,U,V,N,.010,.0016,.0003,white)
        for su in (-.115,.115):
            for sv in (-.14,.14): tube(pc,c+N*.021+U*su+V*sv,c+N*.0222+U*su+V*sv,.003,edge,6)
        pc.done()
        ecran=Piece('Ecran | '+file,cockpit); ecran.face(back,image_mat(file,True),[(0,0),(1,0),(1,1),(0,1)]); ecran.done()

    # Pupitre principal : plan incliné vers l'oeil, de paroi à paroi ; son bord
    # haut rejoint l'auvent, posé dans le plan du seuil jusqu'à la pointe du vitrage.
    def deck_z(y): return Fp.z-.015+SILL*(y-Fp.y)
    yb,zb,yt=-2.02,.28,-2.26; zt=deck_z(yt)
    Ob=Vector((0,yb,zb)); Vm=Vector((0,yt-yb,zt-zb)).normalized(); Nm=Vector((0,Vm.z,-Vm.y)); Um=Vm.cross(Nm)
    def mip(s,t): return Ob+Um*s+Vm*t
    corners=[Vector((wall_x(y,z,s),y,z)) for s,y,z in ((1,yb,zb),(-1,yb,zb),(-1,yt,zt),(1,yt,zt))]
    pup=Piece('Pupitre | chassis',cockpit)
    pup.loft([[p-Nm*.03 for p in corners],corners],structure,(False,True))
    tube(pup,corners[3]+Nm*.008-Vm*.006,corners[2]+Nm*.008-Vm*.006,.016,rubber,8,caps=(True,True))
    tip=meet(W[1]['w1'],W[-1]['w1'],plane(Vector((0,Fp.y,deck_z(Fp.y))),Vector((0,-SILL,1))))
    pup.face(oriented([tip,corners[2],corners[3]],Z),antireflet)
    n,k=front_wall; yu=(k-n.z*zb)/n.y
    pup.face(oriented([corners[0],corners[1],Vector((wall_x(yu,zb,-1),yu,zb)),Vector((wall_x(yu,zb,1),yu,zb))],-Z),structure)
    pup.done()
    module('alarme',mip(0,.477),Um,Vm,Nm)
    module('bas_g',mip(-.285,.072),Um,Vm,Nm); module('bas_d',mip(.285,.072),Um,Vm,Nm)
    for s,file in ((-.26,'ecran_nav'),(0,'ecran_vol'),(.26,'ecran_systemes')): mfd(mip(s,.292),Um,Vm,Nm,file)
    # Collimateur tête haute sur l'auvent, dans l'axe de visée.
    hud=Piece('Pupitre | ATH',cockpit)
    Nd=Vector((0,-SILL,1)).normalized(); Yd=X.cross(Nd)*-1; base=Vector((0,-2.37,deck_z(-2.37)))
    block(hud,base,X,Yd,Nd,.17,.11,.045,rubber,.006); block(hud,base+Nd*.045+Yd*.01,X,Yd,Nd,.09,.05,.004,lens)
    for x in (-.075,.075): tube(hud,base+Nd*.04+Yd*.045+X*x,Vector((x,-2.30,.955)),.005,rubber,6,caps=(True,True))
    tube(hud,Vector((-.075,-2.30,.955)),Vector((.075,-2.30,.955)),.005,rubber,6,caps=(True,True))
    hud.done()
    verre=Piece('Cockpit | combineur ATH',cockpit)
    verre.face(oriented([Vector((-.07,-2.325,.83)),Vector((.07,-2.325,.83)),Vector((.07,-2.302,.948)),Vector((-.07,-2.302,.948))],Y),combiner)
    verre.done()

    # Ailes et consoles latérales : un même profil le long de chaque paroi,
    # panneau incliné sous le rail de verrière puis tablette à hauteur de coude.
    AILE=[(0,.715),(.11,.5425),(.095,.52),(0,.45)]
    CONSOLE=[(0,.715),(.15,.48),(.30,.48),(.30,.10),(.26,.02),(0,.02)]
    Yj,Ye=-1.56,-.84
    def y_mip(z,d,side,off=.01):
        # Station où le point (z, d) de l'aile touche le plan du pupitre, décalé de off.
        return (off-Nm.z*(z-SILL*Y0-Ob.z)+Nm.y*(Ob.y-d*W[side]['nin'].y))/(Nm.y+Nm.z*SILL)
    def face_frame(side,y,pa,pb,horizontal=False,out=Z):
        a=cw(y,pa[1],pa[0],side); b=cw(y,pb[1],pb[0],side)
        along=(cw(y+.1,pa[1],pa[0],side)-a).normalized(); Vf=(b-a).normalized()
        Nn=along.cross(Vf); Nn=Nn if Nn.dot(out)>0 else -Nn
        if horizontal: Vf=-along   # tablettes : légendes lues vers le nez
        Uf=Vf.cross(Nn); return a.lerp(b,.5),Uf,Nn.cross(Uf),Nn
    for s in (-1,1):
        nom='gauche' if s>0 else 'droite'
        pc=Piece('Console | aile '+nom,cockpit)
        pc.loft([[cw(y_mip(z,d,s),z,d,s) for d,z in AILE],[cw(Yj,z,d,s) for d,z in AILE]],structure); pc.done()
        pc=Piece('Console | '+nom,cockpit)
        pc.loft([[cw(Yj,z,d,s) for d,z in CONSOLE],[cw(Ye,z,d,s) for d,z in CONSOLE]],structure); pc.done()
        module('aile_g' if s>0 else 'aile_d',*face_frame(s,-1.815,(.11,.5425),(0,.715)))
        for name,y in zip(('prop','elec') if s>0 else ('disj','env'),(-1.374,-1.027)):
            module(name,*face_frame(s,y,(.15,.48),(0,.715)))
        for name,y in zip(('gaz','trim') if s>0 else ('clavier','com'),(-1.343,-1.006)):
            top,U,Vv,N=module(name,*face_frame(s,y,(.16,.48),(.29,.48),True))
            if name!='gaz': continue
            # Manette des gaz : levier dans la fente sérigraphiée, poignée vers la main.
            pc=Piece('Manette | gaz',cockpit)
            P=top(.085,.21); head=P+N*.075+Vv*.012
            tube(pc,P-N*.02,head,.0065,edge,8)
            tube(pc,head-U*.006,head+U*.085,.019,rubber,12,caps=(True,True))
            for k in range(3): tube(pc,head+U*(.02+.02*k),head+U*(.026+.02*k),.0205,graphite,12)
            tube(pc,head+U*.07+N*.018,head+U*.07+N*.026,.0065,safety,10)
            tube(pc,head+U*.04+N*.018,head+U*.04+N*.023,.005,edge,8)
            pc.done()

    # Trappes d'accès vissées et baie d'équipements derrière le siège.
    acces=Piece('Cockpit | trappes et baie',cockpit)
    def trappe(c,U,V,N,w,h):
        block(acces,c+N*.0005,U,V,N,w,h,.003,plaques,.0012,flat=teinte)
        for u in (-1,1):
            for v in (-1,1):
                q=c+U*u*(w/2-.012)+V*v*(h/2-.012); tube(acces,q+N*.0035,q+N*.005,.0045,edge,8)
    for s in (-1,1):
        for y in (-1.37,-1.03): trappe(*face_frame(s,y,(.30,.10),(.30,.48),out=W[s]['nin']),.32,.30)
        n2=W[s]['w2'][0]; Vw=(Z-n2*Z.dot(n2)).normalized()
        trappe(W[s]['S'].lerp(Ap,.30)+W[s]['down']*.40,Vw.cross(n2),Vw,n2,.36,.28)
    block(acces,Vector((0,-.15,.30)),X,Y,Z,.52,.26,.02,structure,.003,True)
    for x in (-.13,.13):
        c=Vector((x,-.03,.44)); block(acces,c,X,Z,-Y,.22,.24,.24,structure,.006,True)
        f=c-Y*.24; trappe(f,X,Z,-Y,.19,.21)
        for u in (-.06,.06): tube(acces,f+X*u+Z*.08-Y*.003,f+X*u+Z*.08-Y*.03,.005,edge,6)
        tube(acces,f-X*.06+Z*.08-Y*.03,f+X*.06+Z*.08-Y*.03,.005,edge,6,caps=(True,True))
        tube(acces,f-Z*.06-Y*.003,f-Z*.06-Y*.02,.012,graphite,10)
    acces.done()

    # Manche central : carter au plancher, soufflet, poignée sculptée.
    st=Piece('Manche | ensemble',cockpit)
    ym=-1.72
    st.loft([rect(Vector((0,ym,fz(ym)-.02)),X,Y,.20,.24),rect(Vector((0,ym,-.06)),X,Y,.20,.24),rect(Vector((0,ym,-.042)),X,Y,.17,.21)],structure,(False,True))
    tube(st,Vector((0,ym,-.042)),Vector((0,ym,-.034)),.082,edge,16)
    lathe(st,Vector((0,ym,-.034)),Z,[(.072,0),(.075,.012),(.061,.024),(.066,.036),(.054,.048),(.058,.06),(.046,.072),(.05,.084),(.037,.096),(.024,.104)],rubber,16)
    tube(st,Vector((0,ym,.06)),Vector((0,ym-.02,.30)),.016,edge,10)
    rings=[(.29,.020,.024,.022),(.31,.022,.031,.028),(.35,.026,.035,.031),(.39,.030,.033,.029),(.43,.034,.034,.030),(.47,.038,.039,.034),(.50,.041,.036,.031),(.515,.043,.026,.024)]
    st.loft([[Vector((math.cos(2*math.pi*i/12)*rx,ym-dy+math.sin(2*math.pi*i/12)*ry,z)) for i in range(12)] for z,dy,rx,ry in rings],rubber)
    block(st,Vector((0,ym-.06,.44)),X,Z,-Y,.02,.035,.012,safety,.003)
    tube(st,Vector((0,ym-.05,.505)),Vector((0,ym-.05,.522)),.010,edge,10)
    tube(st,Vector((.024,ym-.035,.495)),Vector((.032,ym-.035,.50)),.006,red,8)
    tube(st,Vector((0,ym-.025,.516)),Vector((0,ym-.025,.524)),.007,amber,8)
    st.done()
    # Palonnier : pédales articulées au plancher, semelles striées.
    ped=Piece('Pedalier | ensemble',cockpit)
    Vp=Vector((0,-.42,.91)).normalized(); Np=Vector((0,.91,.42)).normalized(); Up=Vp.cross(Np)
    for s in (-1,1):
        x=s*.17; c=Vector((x,-2.47,fz(-2.47)+.13))
        block(ped,c,Up,Vp,Np,.10,.22,.016,edge,.003)
        for k in range(4): block(ped,c+Np*.016+Vp*(-.075+.05*k),Up,Vp,Np,.085,.012,.003,rubber)
        tube(ped,Vector((x,-2.40,fz(-2.40))),c-Np*.005-Vp*.05,.011,edge,8)
        block(ped,Vector((x,-2.40,fz(-2.40)-.01)),X,Yf,Nf,.07,.06,.04,structure,.005)
    ped.done()

    # Siège : glissières, flasques en tôle, baquet, dossier incliné, appui-tête, harnais.
    sg=Piece('Siege | ensemble',cockpit)
    for x in (-.19,.19):
        block(sg,Vector((x,-1.06,fz(-1.06))),X,Yf,Nf,.035,.72,.025,edge,.004)
        flasque=lambda xx:[Vector((xx,y,z)) for y,z in ((-1.30,fz(-1.30)+.02),(-.84,fz(-.84)+.02),(-.86,.07),(-1.26,.07))]
        sg.loft([flasque(x-.006),flasque(x+.006)],structure)
    for y,z in ((-1.05,-.20),(-1.20,-.02)): tube(sg,Vector((-.19,y,z)),Vector((.19,y,z)),.016,edge,8,caps=(True,True))
    block(sg,Vector((0,-1.13,.07)),X,Y,Z,.52,.58,.03,structure,.004,True)
    for x in (-.265,.265):
        joue=lambda xx:[Vector((xx,y,z)) for y,z in ((-1.42,.07),(-.84,.07),(-.84,.36),(-1.06,.31),(-1.42,.26))]
        sg.loft([joue(x-.007),joue(x+.007)],structure)
    block(sg,Vector((0,-1.305,.10)),X,Y,Z,.47,.19,.115,seat,.02,True)
    block(sg,Vector((0,-1.03,.10)),X,Y,Z,.47,.34,.12,seat,.02,True)
    # Dossier : coque trapézoïdale entre deux rails de guidage, coffre d'appui-tête.
    Vb=Vector((0,.21,1)).normalized(); Nb=Vector((0,-1,.21)).normalized()
    def dos(z): return Vector((0,-.70-.21*(1.07-z),z))
    def hw(z): return .27-.075*(z-.20)
    coque=[dos(.20)-Nb*.09-X*hw(.20),dos(.20)-Nb*.09+X*hw(.20),dos(1.0)-Nb*.09+X*hw(1.0),dos(1.0)-Nb*.09-X*hw(1.0)]
    sg.loft([coque,[p+Nb*.02 for p in coque]],structure)
    block(sg,dos(.60)-Nb*.07,X,Vb,Nb,.42,.70,.07,seat,.02,True)
    for s in (-1,1):
        joue=[dos(z)+Nb*f+X*s*hw(z) for z,f in ((.22,-.09),(.22,.07),(.80,.04),(.98,-.07))]
        sg.loft([[p-X*.007 for p in joue],[p+X*.007 for p in joue]],structure)
        tube(sg,dos(-.10)-Nb*.13+X*s*.17,dos(1.20)-Nb*.13+X*s*.17,.018,edge,8,caps=(True,True))
        block(sg,dos(1.10)-Nb*.10+X*s*.135,X,Vb,Nb,.05,.17,.12,seat,.02,True)
    for z in (.30,.90): tube(sg,dos(z)-Nb*.13-X*.17,dos(z)-Nb*.13+X*.17,.012,edge,8)
    block(sg,dos(1.16)-Nb*.24,X,Vb,Nb,.32,.17,.13,structure,.01,True)
    block(sg,dos(1.10)-Nb*.10,X,Vb,Nb,.22,.17,.10,seat,.025,True)
    def sangle(a,b,n,w=.045):
        v=(b-a).normalized(); u=v.cross(n).normalized(); block(sg,(a+b)/2,u,v,u.cross(v),w,(b-a).length,.004,accent)
    for s in (-1,1):
        sangle(dos(.97)+X*s*.11+Nb*.002,dos(.30)+X*s*.06+Nb*.002,Nb)
        sangle(Vector((s*.25,-1.00,.222)),Vector((s*.035,-1.06,.222)),Z)
    tube(sg,Vector((0,-1.06,.221)),Vector((0,-1.06,.232)),.032,edge,12)
    loop=[Vector((-.06,-1.42,.13)),Vector((-.06,-1.47,.18)),Vector((.06,-1.47,.18)),Vector((.06,-1.42,.13))]
    for a,b in zip(loop,loop[1:]): tube(sg,a,b,.009,accent,8,caps=(True,True))
    sg.done()

    lamp=bpy.data.objects.get('Light_Cockpit_HUD')
    if lamp:
        lamp.location=(0,-1.1,.78); lamp.data.energy=28; lamp.data.color=(.60,.78,1.0); lamp.data.shadow_soft_size=.8
    return panels
