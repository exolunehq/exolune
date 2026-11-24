"""Machined shoulder opening, plug doors and docking collar of the Navette AAA."""
import copy

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

import anim
import hullgrid as hg
import meshkit
import wing_jacks

COL = "02_Exterieur_Appendices"
Z = -0.153
TOP, SPLIT, BOTTOM = 26, hg.B_E1 + 1, hg.B_CAV0 - 1
BAY_Y = (0.91, 5.28)
EDGE_Z = 0.00035   # half the vertical allowance at a split on the sloping shoulder
END_GAP = 0.00085  # longitudinal clearance at each jamb, metres
BLANK_LIFT, BLANK_BANK, BLANK_AXIS = 0.324, np.deg2rad(-20), 2.14


def columns(grid):
    return tuple(int(np.argmin(abs(grid.points[:, hg.B_E1, 1] - y))) for y in BAY_Y)


def fit_bay(grid, airfoil):
    """Leave both original chine bevels in place. Set the sill inside the metal above the duct."""
    a0, a1 = columns(grid)
    for a in range(a0 - 2, a1 + 3):
        blend = min(1, (a - a0 + 3) / 3, (a1 + 3 - a) / 3)
        y = grid.points[a,hg.B_E1,1]
        forward = 1-hg.smoothstep(1.58,2.02,y)
        over_mouth = hg.smoothstep(grid.col["c0"]-2,grid.col["c0"],a)*(1-hg.smoothstep(grid.col["c1"],grid.col["c1"]+2,a))
        available = grid.points[a,BOTTOM,2]-grid.points[a,BOTTOM+1,2]
        sill = np.clip(1-0.012*over_mouth/max(available,0.0001),0,0.72)
        for field in (grid.s, grid.t, grid.lam, grid.girth, grid.points, grid.normals):
            field[a,BOTTOM] += sill*blend*(field[a,BOTTOM+1]-field[a,BOTTOM])
            for r in range(24,29):
                field[a,r] += (1-abs(r-TOP)/3)*0.92*blend*forward*(field[a,r+1]-field[a,r])
        grid.normals[a,BOTTOM] /= np.linalg.norm(grid.normals[a,BOTTOM])
        grid.normals[a,24:29] = unit(grid.normals[a,24:29])
    # Size the upper doorway to the banked blank at its lateral handoff. The sill,
    # chine bevels and existing pressure pickup all retain their own seats.
    chart, _ = installation(grid)
    shoulder = Shoulder(chart,airfoil)
    p,_ = shoulder.skin(shoulder.a,shoulder.upper)
    parked = Z+BLANK_LIFT - np.sin(BLANK_BANK)*(p[:,0]-BLANK_AXIS) + np.cos(BLANK_BANK)*(p[:,2]-Z)
    envelope = np.maximum.reduce([np.roll(parked,d) for d in range(-3,4)])+0.022
    envelope[:3],envelope[-3:] = parked[:3]+0.022,parked[-3:]+0.022
    rows = np.arange(20,33)
    for a in range(a0,a1+1):
        z=chart.points[a,rows,2]
        required=max(chart.points[a,TOP,2],np.interp(a,shoulder.a,envelope))
        pin=np.interp(-required,-z,rows)
        mapped=np.interp(rows,(rows[0],TOP,rows[-1]),(rows[0],pin,rows[-1]))
        lo=np.floor(mapped).astype(int)
        hi=np.minimum(lo+1,rows[-1])
        for field in (grid.s,grid.t,grid.lam,grid.girth,grid.points,grid.normals):
            t=(mapped-lo)[:,None] if field.ndim==3 else mapped-lo
            field[a,rows]=field[a,lo]*(1-t)+field[a,hi]*t
        grid.normals[a,rows]=unit(grid.normals[a,rows])


def installation(grid):
    """Fit the rigid wing plane along the existing face between the two shoulder bevels."""
    a0, a1 = columns(grid)
    edge = grid.points[a0:a1+1]
    centre = 0.68*edge[:,hg.B_E1] + 0.32*edge[:,hg.B_E2]
    slope, intercept = np.polyfit(centre[:,1], centre[:,2], 1)
    c = 1 / np.sqrt(1+slope*slope)
    s = slope*c
    rot = np.array(((1,0,0),(0,c,-s),(0,s,c)))
    y = centre[:,1].mean()
    origin = np.array((0,y,intercept+slope*y)) - rot @ np.array((0,y,Z))
    datum = np.eye(4)
    datum[:3,:3], datum[:3,3] = rot, origin
    local = copy.copy(grid)
    local.points = (grid.points-origin) @ rot
    local.normals = grid.normals @ rot
    local.ship_from_wing = datum
    return local, datum


def slot_cells(grid):
    a0, a1 = columns(grid)
    mask = np.zeros((grid.na - 1, grid.nb - 1), dtype=bool)
    mask[a0:a1, TOP:BOTTOM] = True
    return mask


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def sheet(name, p, normals, depth, paint, edge_mat, sign):
    """A closed formed sheet. Its front retains the loft normals, independently of the edge returns."""
    idx = np.arange(p.shape[0]*p.shape[1]).reshape(p.shape[:2])
    border = np.r_[idx[:,0],idx[-1,1:],idx[-2::-1,-1],idx[0,-2:0:-1]]
    return formed_sheet(name,p.reshape(-1,3),normals.reshape(-1,3),meshkit.grid_faces(idx).tolist(),
                        border,depth,paint,edge_mat,sign)


def formed_sheet(name, points, normals, faces, border, depth, paint, edge_mat, sign):
    flip = np.array((sign, 1, 1))
    front = points * flip
    n = unit(normals) * flip
    count = len(front)
    verts = np.vstack((front, front - depth * n))
    nfront = len(faces)
    # Use an interior face to establish the common winding of both triangles and quads.
    witness = faces[len(faces)//2]
    q = front[witness]
    if np.cross(q[1]-q[0],q[-1]-q[0]) @ n[witness].sum(axis=0) < 0:
        faces = [f[::-1] for f in faces]
        border = border[::-1]
    nloops = sum(map(len,faces))
    faces += [[v + count for v in reversed(f)] for f in faces]
    for v, w in zip(border, np.roll(border, -1)):
        faces.append([w, v, v + count, w + count])
    slots = [0] * nfront + [1] * (len(faces) - nfront)
    o = meshkit.mesh_object(name, verts, faces, COL, materials=[paint, edge_mat], face_mats=slots)
    me = o.data
    loops = np.empty(len(me.loops), dtype=np.int32)
    me.loops.foreach_get("vertex_index", loops)
    fn = np.empty(len(me.polygons) * 3, dtype=np.float32)
    me.polygons.foreach_get("normal", fn)
    sizes = np.empty(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get("loop_total", sizes)
    split = np.repeat(fn.reshape(-1, 3), sizes, axis=0)
    split[:nloops] = n[loops[:nloops]]
    split[nloops:2*nloops] = -n[loops[nloops:2*nloops] - count]
    me.normals_split_custom_set(split)
    return o


class Shoulder:
    """One port-side chart supplies the cover panels and both interchangeable seated interfaces."""
    top, bottom, centre_z = TOP, BOTTOM, Z
    def __init__(self, grid, airfoil):
        self.grid = grid
        self.airfoil = airfoil
        a0, a1 = columns(grid)
        dy0, dy1 = np.diff(grid.points[[a0, a0+1, a1-1, a1], SPLIT, 1])[[0, 2]]
        self.a = np.linspace(a0 + END_GAP / dy0, a1 - END_GAP / dy1, 4*(a1-a0) + 1)
        self.upper_rim = self.row_z(self.a, TOP)
        self.lower_rim = self.row_z(self.a, BOTTOM)
        y = np.interp(self.a, np.arange(grid.na), grid.points[:,SPLIT,1])
        run = np.minimum(y-y[0], y[-1]-y)
        taper = hg.smoothstep(0.038, 0.084, run)
        self.upper = Z + self.crossing(1) + 0.0090*taper
        self.lower = Z - self.crossing(-1) - 0.0080*taper
        active = np.flatnonzero(taper > 0.14)
        self.window = slice(active[0], active[-1]+1)
        if np.min(self.lower - self.lower_rim) < 0.004:
            raise ValueError(f"lower door at its narrowest: {np.min(self.lower - self.lower_rim):.4f} m")

    def row_z(self, a, row):
        return np.interp(a, np.arange(self.grid.na), self.grid.points[:, row, 2])

    def skin(self, a, z):
        a, z = np.broadcast_arrays(a, z)
        shape = z.shape
        a, z = a.ravel(), z.ravel()
        i = a.astype(int)
        t = (a - i)[:, None, None]
        p = self.grid.points[i, TOP:BOTTOM+1] * (1-t) + self.grid.points[i+1, TOP:BOTTOM+1] * t
        n = self.grid.normals[i, TOP:BOTTOM+1] * (1-t) + self.grid.normals[i+1, TOP:BOTTOM+1] * t
        j = np.clip((p[:, :, 2] > z[:, None]).sum(axis=1)-1, 0, BOTTOM-TOP-1)
        k = np.arange(len(z))
        f = ((p[k,j,2] - z) / (p[k,j,2] - p[k,j+1,2]))[:, None]
        pos = p[k,j] * (1-f) + p[k,j+1] * f
        normal = unit(n[k,j] * (1-f) + n[k,j+1] * f)
        return pos.reshape(*shape, 3), normal.reshape(*shape, 3)

    def crossing(self, direction):
        lo, hi = np.zeros_like(self.a), np.full_like(self.a, 0.13)
        for _ in range(25):
            mid = (lo + hi) / 2
            p, _ = self.skin(self.a, Z + direction*mid)
            height = self.airfoil(p[:,0], p[:,1], direction)
            inside = mid < height
            lo, hi = np.where(inside, mid, lo), np.where(inside, hi, mid)
        return (lo + hi) / 2

    def strip(self, name, high, low, depth, mats, sign, region=slice(None)):
        a, high, low = (np.broadcast_to(v, self.a.shape)[region] for v in (self.a, high, low))
        # Clip the actual bevel rows to each door. Every original break in the chine survives.
        rows = np.stack([self.row_z(a,b) for b in range(TOP,BOTTOM+1)],axis=1)
        between = (rows[:,1:]+rows[:,:-1])/2
        knots = np.empty((len(a), 2*rows.shape[1]-1))
        knots[:,::2], knots[:,1::2] = rows, between
        chains, labels, sections = [], [], []
        start = 0
        for zz,hi,lo in zip(knots,high,low):
            ids = np.flatnonzero((zz < hi-0.00001) & (zz > lo+0.00001))
            labels.append(np.r_[-1,ids,len(zz)])
            sections.append(np.r_[hi,zz[ids],lo])
            chains.append(np.arange(start,start+2+len(ids)))
            start += 2+len(ids)
        p,n = self.skin(np.repeat(a,[len(s) for s in sections]),np.concatenate(sections))
        faces = []
        for i,(left,right) in enumerate(zip(chains,chains[1:])):
            j=k=0
            while j < len(left)-1 and k < len(right)-1:
                l,r = labels[i][j+1], labels[i+1][k+1]
                face = [left[j],right[k]]
                if r <= l:
                    k+=1
                    face.append(right[k])
                if l <= r:
                    j+=1
                    face.append(left[j])
                faces.append(face)
        border = np.r_[[chain[0] for chain in chains],chains[-1][1:],
                       [chain[-1] for chain in chains[-2::-1]],chains[0][-2:0:-1]]
        return formed_sheet(name,p,n,faces,border,depth,mats["white"],mats["seam"],sign)

    def land(self, name, line, region, sign, mat, setback=0.0037, width=0.0055, stations=None, depth=0.0009):
        """A rebated lip intercepts the sightline behind a narrow manufacturing clearance."""
        a = self.a[region] if stations is None else stations
        centre = np.interp(a, self.a, np.broadcast_to(line, self.a.shape))
        up,down = width if isinstance(width,tuple) else (width,width)
        offsets = np.stack(np.broadcast_arrays(up,np.zeros_like(a),-np.asarray(down)),axis=1)
        p, n = self.skin(a[:,None], centre[:,None] + offsets)
        return sheet(name, p - setback*n, n, depth, mat, mat, sign)

    def saddle(self, mats, sign, side):
        """A small rolled shoulder fillet. Its outer seam is cut on the actual door chart."""
        parts = []
        for direction, boundary in ((1, self.upper), (-1, self.lower)):
            start, normal = self.skin(self.a, boundary - direction*EDGE_Z)
            bare, _ = self.skin(self.a, np.full_like(self.a, Z))
            active = self.airfoil(bare[:,0], bare[:,1], direction)
            rollout = 0.045 * hg.smoothstep(0.003, 0.033, active)
            base, _ = self.skin(self.a, boundary - direction*(0.009 if direction > 0 else 0.008))
            # Towards a narrow edge the blend dies into the original shoulder instead of projecting a tab.
            xend = np.where(active > 0, base[:,0], bare[:,0]) + rollout
            zend = Z + direction * np.maximum(0, self.airfoil(xend, base[:,1], direction) - 0.0004)
            end = np.column_stack((xend, base[:,1], zend))
            tangent = unit(np.column_stack((normal[:,2], np.zeros(len(normal)), -normal[:,0])))
            # The underside arrives at the lower door from above, then rolls out onto the intrados.
            p1 = start + direction*tangent * (0.007 + 0.25*rollout)[:,None]
            p2 = end - np.column_stack((0.37*rollout, np.zeros(len(rollout)), np.zeros(len(rollout))))
            t = np.linspace(0, 1, 8)[None,:,None]
            curve = ((1-t)**3*start[:,None] + 3*(1-t)**2*t*p1[:,None] +
                     3*(1-t)*t**2*p2[:,None] + t**3*end[:,None])
            # A station outside the wing is a flush piece of the shoulder down to the centre seam.
            z = boundary[:,None]*(1-t[0,:,0]) + Z*t[0,:,0]
            flush, fn = self.skin(self.a[:,None], z)
            weight = hg.smoothstep(0.0005, 0.009, active)[:,None,None]
            curve = flush*(1-weight) + curve*weight
            guide = unit(np.cross(np.gradient(curve, axis=0), np.gradient(curve, axis=1))) * -direction
            guide[:,0] = normal
            parts.append(sheet("Aile_Conge_" + side, curve[self.window], guide[self.window], 0.0010,
                               mats["white"], mats["seam"], sign))
            parts.append(self.land("Joint_Emplanture", boundary, self.window, sign, mats["seam"]))
        flight, _ = self.skin(self.a, np.full_like(self.a, Z))
        wet = np.flatnonzero(self.airfoil(flight[:,0], flight[:,1], 1) > 0.022)
        for region in (slice(self.window.start, wet[0]+1), slice(wet[-1], self.window.stop)):
            parts.append(self.land("Levre_du_conge", Z-0.0045, region, sign, mats["seam"], 0.0058, 0.0105))
        return parts

    def build(self, mats, sign, side):
        tub = liner(self.grid, mats, sign, side)
        web = BVHTree.FromPolygons([v.co[:] for v in tub.data.vertices],
                                   [p.vertices[:] for p in tub.data.polygons])
        bearings = []
        for upper, label, high, low in (
            (True, "Haute", self.upper_rim - EDGE_Z, self.upper + 0.0018),
            (False, "Basse", self.lower - 0.0018, self.lower_rim + 0.0018)):
            door = self.strip("Aile_Trappe_" + label + "_" + side, high, low, 0.0014, mats, sign)
            motion = lambda u, upper=upper: door_pose(sign, upper, u)
            foot, fixed_foot = wing_jacks.build(self, web, mats, sign, side, upper, motion)
            bearings.append(fixed_foot)
            door = meshkit.join([door,foot],door.name)
            anim.bake(door, "Ailes", motion)
        shutter = self.strip("Aile_Obturateur_" + side, self.upper-EDGE_Z, self.lower+EDGE_Z,
                             0.0015, mats, sign, self.window)
        seals = [self.land("Joint_Obturateur", line, self.window, sign, mats["seam"])
                 for line in (self.upper,self.lower)]
        shutter = meshkit.join([shutter,*seals],shutter.name)
        anim.bake(shutter, "Ailes", lambda u: shutter_pose(sign,u))
        inside = np.minimum(0.008,0.30*(self.lower-self.lower_rim))
        fixed = [self.land("Feuillure_Rive",self.upper_rim,slice(None),sign,mats["seam"],0.0037,0.0080),
                 self.land("Feuillure_Seuil",self.lower_rim,slice(None),sign,mats["seam"],0.0029,(inside,0.0068))]
        # The two short meeting edges terminate in sliding end keys. A key bridges its
        # running clearance only once the outer skin and the centre insert are seated.
        for direction, label, region, tip in ((-1, "Avant", slice(None, self.window.start+1), -1),
                                               (1, "Arriere", slice(self.window.stop-1, None), 0)):
            a = self.a[region].copy()
            end = a[tip]
            a[tip] += direction * 0.052
            fixed.append(self.land("Feuillure_Extremite", Z, region, sign, mats["seam"], 0.0059, 0.0080, a))
            key = self.land("Aile_Clavette_" + label + "_" + side, Z, region, sign, mats["seam"],
                            0.0026, 0.009, end + np.linspace(-0.15, 0.15, 7), 0.0006)
            seats, _ = self.skin(np.array((end, end + direction*0.40)), np.array((Z, Z)))
            slide = (seats[1]-seats[0]) * (sign, 1, 1)
            anim.bake(key, "Ailes", lambda u, slide=slide: anim.shift(slide *
                      (anim.ease(u, 0, 0.030) - anim.ease(u, 0.971, 1))))
        # Each jamb has a continuous seat across the corner and the two short meeting edges.
        a0, a1 = columns(self.grid)
        for end in (a0, a1):
            a = end + np.linspace(-0.16, 0.16, 7)
            t = np.linspace(0, 1, 25)
            z = (self.row_z(a,TOP)+0.007)[:,None]*(1-t) + (self.row_z(a,BOTTOM)-0.007)[:,None]*t
            p, n = self.skin(a[:,None], z)
            fixed.append(sheet("Feuillure_Montant", p-0.0056*n, n, 0.0009,
                               mats["seam"], mats["seam"], sign))
        meshkit.join([tub, *fixed, *bearings], tub.name)


def door_pose(sign, upper, u):
    # After docking the tooling faces return to exactly the same shoulder datum as at rest.
    u = (u-0.033)/0.934
    opened = anim.ease(u, 0.025, 0.165)
    seated = anim.ease(u, 0.84, 1.0)
    dz = (0.273 if upper else -0.098) * (opened - seated)
    dx = (0.21 if upper else -2.35)*dz
    plug = anim.ease(u, 0, 0.045) - anim.ease(u, 0.965, 1)
    return anim.shift((sign*(dx + 0.056*plug), 0, dz))


def shutter_pose(sign, u):
    # Park the central blank above the wing in the shoulder roof, clear of the existing exhaust.
    u = (u-0.033)/0.934
    lift = anim.ease(u,0.058,0.174)
    dx = -0.225*lift - 0.68*anim.ease(u,0.180,0.272)
    return anim.shift((sign*dx,0,BLANK_LIFT*lift)) @ anim.about(
        (sign*BLANK_AXIS,0,Z),(0,1,0),sign*BLANK_BANK*lift)


def exhaust_roof(grid):
    """Height of the existing nozzle skin in the local wing frame."""
    datum = grid.ship_from_wing
    points, triangles = [], []
    for name in ("Tuyere_Conduit_G", "Tuyere_Aubes_G", "Tuyere_Lumiere_G"):
        obj = bpy.data.objects[name]
        pts = np.array([tuple(obj.matrix_world @ v.co) for v in obj.data.vertices])
        pts = (pts-datum[:3,3]) @ datum[:3,:3]
        obj.data.calc_loop_triangles()
        triangles.extend((np.array([t.vertices[:] for t in obj.data.loop_triangles])+len(points)).tolist())
        points.extend(pts.tolist())
    roof = BVHTree.FromPolygons(points,triangles,all_triangles=True)
    def height(x,y):
        high = Z-0.152
        for dx,dy in ((0,0),(0.035,0),(-0.035,0),(0,0.034),(0,-0.034),
                      (0.027,0.027),(-0.027,0.027),(0.027,-0.027),(-0.027,-0.027)):
            hit = roof.ray_cast((x+dx,y+dy,1),(0,0,-1))[0]
            if hit is not None:
                high=max(high,hit.z+0.0035)
        return high
    return height


def liner(grid, mats, sign, side):
    """Form the roof cassette and keep the floor over the measured exhaust envelope."""
    a0, a1 = columns(grid)
    border = ([(a,TOP) for a in range(a0,a1)] + [(a1,b) for b in range(TOP,BOTTOM)] +
              [(a,BOTTOM) for a in range(a1,a0,-1)] + [(a0,b) for b in range(BOTTOM,TOP,-1)])
    rim = np.array([grid.points[a,b] for a,b in border])
    k = len(rim)
    lip, pocket, back = rim.copy(), rim.copy(), rim.copy()
    shell = BVHTree.FromPolygons(grid.points.reshape(-1,3).tolist(),
                                meshkit.grid_faces(np.arange(grid.na*grid.nb).reshape(grid.na,grid.nb)).tolist())
    duct = exhaust_roof(grid)
    def floor_at(x,y):
        bottom = shell.ray_cast((x,y,-4),(0,0,1))[0]
        return max(duct(x,y),bottom.z+0.004 if bottom is not None else -4)
    fractions = []
    for j,(a,b) in enumerate(border):
        f = (grid.points[a,TOP,2] - rim[j,2]) / (grid.points[a,TOP,2] - grid.points[a,BOTTOM,2])
        fractions.append(f)
        end = -1 if a == a0 else 1 if a == a1 else 0
        lip[j] += (-0.032 - 0.046*(1-f), end*0.012, 0.014*(1-f) + 0.008*f)
        lip_hit = shell.ray_cast((0.4,lip[j,1],lip[j,2]), (1,0,0))
        lip[j,0] = min(lip[j,0], lip_hit[0].x-0.015)
        pocket[j,1] += end*0.025
        floor = floor_at(lip[j,0]-0.04,pocket[j,1])
        pocket[j,2] = (1-f)*max(0.335,grid.points[a,TOP,2]+0.035) + f*floor
        hit = shell.ray_cast((0.4,pocket[j,1],pocket[j,2]), (1,0,0))
        pocket[j,0] = min(lip[j,0] - 0.035, hit[0].x - 0.028)
        back[j] = (0.645, pocket[j,1], pocket[j,2])
    rings = [rim,lip]
    for t in (0.25,0.50,0.75,1.0):
        ring=lip*(1-t)+pocket*t
        for j,(_,y,z) in enumerate(ring):
            bound=shell.ray_cast((0.4,y,z),(1,0,0))[0].x
            ring[j,0]=min(lip[j,0]-0.035*t,bound-0.023-t*0.005)
        rings.append(ring)
    pocket = rings[-1]
    for t in np.linspace(0,1,57)[1:]:
        ring=pocket*(1-t)+back*t
        for j,((a,b),f) in enumerate(zip(border,fractions)):
            if f>0:
                x,y=ring[j,:2]
                ring[j,2]=(1-f)*max(0.335,grid.points[a,TOP,2]+0.035) + f*floor_at(x,y)
        rings.append(ring)
    verts = np.vstack(rings)
    faces = [[r*k+j, r*k+(j+1)%k, (r+1)*k+(j+1)%k, (r+1)*k+j]
             for r in range(len(rings)-1) for j in range(k)]
    for a in range(a1-a0):
        j0, j1 = border.index((a0+a,BOTTOM)), border.index((a0+a+1,BOTTOM))
        end=(len(rings)-1)*k
        faces.append([end+a,end+a+1,end+j1,end+j0])
    flip = np.array((sign,1,1))
    guide = (np.array((1.55, np.mean(BAY_Y), Z)) - verts) * flip
    return meshkit.mesh_object("Aile_Baie_" + side, verts*flip, faces, COL,
                               materials=[mats["duct"]], orient=guide)
