"""Fit the Navette's exterior and moving surfaces to its film packet.

Run with Blender Python for its BVH, from a clean film VSX to a distinct output.
Distances are metres in the ship frame. The seats, controls, glazing and
thruster data come directly from the film packet.
"""
import hashlib
import math
from pathlib import Path
import struct
import sys
import zlib

from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
import numpy as np


FILM_HASH = "d4498a432d77d4f37d68865fb0a3564d80c18ee9e1650977b355d7c1d865dfc6"
CHART_PADDING = np.array((.085, .065))
SKIN = {4, 6, 8, 9, 43}  # Exterior material IDs in this exact film packet.
OCCUPANTS = {36, 37, 38, 39, 40}
POSE_BRAKE = 14
BRAKE_ANGLE = math.radians(59)
LIP_EXTENSION = 1.62  # Transverse travel at the crest in metres.
BODY, TRIM, GASKET, TITANIUM, TEAL, CARBON, AMBER, SEAM, HOT_GUIDE, PISTON = range(10)


def smooth(low, high, value):
    t = np.clip((value - low) / (high - low), 0, 1)
    return t * t * (3 - 2 * t)


def unit_vectors(vectors):
    return vectors / np.linalg.norm(vectors, axis=-1, keepdims=True).clip(1e-12)


def stern_height(y, z):
    """Match both slopes between the thinning rear shell and the dorsal foil."""
    thickness = 1 - .65 * smooth(3.54, 5.68, y)
    centre, lower, deck, foil = -.50, .28, .94, .70
    t = np.clip((z-lower)/(deck-lower), 0, 1)
    at_lower = centre + thickness*(lower-centre)
    middle = ((1-t)**2*((1+2*t)*at_lower + t*(deck-lower)*thickness) +
              t*t*((3-2*t)*deck + (t-1)*(deck-lower)*foil))
    height = np.where(z <= lower, centre + thickness*(z-centre),
                      np.where(z >= deck, deck + foil*(z-deck), middle))
    return z + smooth(2.0, 2.95, y)*(height-z)


def refine_stern(vertices, draws, faces, shape):
    """Split shared edges where a straight triangle misses the formed skin by 3 mm."""
    batches = [(faces[i//3:(i+n)//3], m) for i,n,m in draws]
    for _ in range(3):
        next_batches, extra = [], []
        next_id = len(vertices)
        for tris, mat in batches:
            nearby = vertices[tris,1].max(axis=1) > 3.50
            if not nearby.any():
                next_batches.append((tris, mat))
                continue
            local = tris[nearby]
            edges = np.stack((local,np.roll(local,-1,axis=1)),axis=2)
            pairs, inverse = np.unique(np.sort(edges.reshape(-1,2),axis=1),axis=0,return_inverse=True)
            first, last = vertices[pairs[:,0]], vertices[pairs[:,1]]
            mid = (first+last)*.5
            error = np.linalg.norm(shape(mid[:,:3])-(shape(first[:,:3])+shape(last[:,:3]))*.5,axis=1)
            split = (error > .003) & (np.maximum(first[:,1],last[:,1]) > 3.50)
            if not split.any():
                next_batches.append((tris,mat))
                continue
            new = mid[split]
            new[:,3:6] = unit_vectors(new[:,3:6])
            new[:,6:9] = unit_vectors(new[:,6:9]-(new[:,6:9]*new[:,3:6]).sum(axis=1)[:,None]*new[:,3:6])
            new[:,9] = first[split,9]
            extra.append(new)
            middle = np.full(len(pairs), -1, dtype=int)
            middle[split] = np.arange(next_id,next_id+len(new))
            next_id += len(new)
            ids = middle[inverse].reshape(-1,3)
            count = (ids >= 0).sum(axis=1)
            pieces = [tris[~nearby],local[count == 0]]
            # Rotate the triangle so the split edges lead. All patterns preserve winding.
            for k in range(3):
                a,b,c = np.roll(local,-k,axis=1).T
                ab,bc,ca = np.roll(ids,-k,axis=1).T
                one = (count==1) & (ab>=0)
                two = (count==2) & (ab>=0) & (bc>=0)
                for mask, corners in ((one,(a,ab,c)),(one,(ab,b,c)),(two,(ab,b,bc)),
                                      (two,(a,ab,c)),(two,(ab,bc,c))):
                    pieces.append(np.column_stack(corners)[mask])
            a,b,c = local.T
            ab,bc,ca = ids.T
            for corners in ((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)):
                pieces.append(np.column_stack(corners)[count==3])
            next_batches.append((np.concatenate(pieces).astype("<u4"),mat))
        if not extra:
            break
        vertices = np.concatenate([vertices,*extra])
        batches = next_batches
    draws, start = [], 0
    for tris, mat in batches:
        draws.append((start,tris.size,mat))
        start += tris.size
    return vertices, np.concatenate([t for t,_ in batches]).ravel(), np.asarray(draws,dtype="<u4")


def finish_stern(vertices, faces, material_draws):
    # Aftmost station at each horizontal cut of the original side drawing,
    # in metres. The low point of the fin blends into one descending afterdeck.
    silhouette = np.array(((-1.60,3.68),(-1.45,3.86),(-1.30,4.03),(-1.15,4.21),(-1.05,4.32),
                           (-.90,4.54),(-.80,4.80),(-.72,5.12),(-.65,5.45),
                           (-.59,5.72),(-.55,5.80),(-.52,5.81),(-.48,5.77),(-.41,5.64),
                           (-.25,5.33),(0.,4.84),(.18,4.48),(.30,4.24),(.38,4.13),
                           (.45,4.09),(.54,4.10),(.80,4.21),(1.25,4.40),(1.75,4.62),(2.17,4.79)))
    skin = np.concatenate([faces[i//3:(i+n)//3] for i,n,m in material_draws if m in SKIN])
    tri = vertices[skin, :3]
    tri = tri[tri[:,:,1].max(axis=1)>3.52].astype(float)
    tri[:,:,2] = stern_height(tri[:,:,1], tri[:,:,2])
    def aft_edge(triangles, levels):
        a = triangles.reshape(-1,3)
        b = np.roll(triangles,-1,axis=1).reshape(-1,3)
        result = []
        for level in levels:
            hit = (a[:,2] > level) != (b[:,2] > level)
            i, j = a[hit], b[hit]
            result.append((i[:,1]+(j[:,1]-i[:,1])*(level-i[:,2])/(j[:,2]-i[:,2])).max())
        return np.asarray(result)

    cuts = np.linspace(silhouette[0,0], tri[:,:,2].max()-.0001, 241)
    aft = aft_edge(tri, cuts)
    kernel = np.exp(-.5*(np.arange(-7,8)/2.2)**2)
    aft = np.convolve(np.pad(aft,7,mode="edge"),kernel/kernel.sum(),mode="valid")
    guide = np.interp(cuts, *silhouette.T)
    guide = np.convolve(np.pad(guide,2,mode="edge"), np.array((1,4,6,4,1))/16., mode="valid")

    def stations(points):
        result = points.copy()
        x, y, z = points.T
        level = stern_height(y,z)
        source_end = np.interp(level, cuts, aft)
        end = np.interp(level, cuts, guide)
        t = np.clip((y-3.52)/(source_end-3.52), 0, 1)
        # Whole waterlines share the same monotone map. All seams stay seated
        # where the rear deck and fin meet, including on the hidden side.
        weight = t*t*(2-t)*smooth(-1.60,-1.43,level)
        result[:,1] += weight*(end-source_end)
        result[:,0] = x*(1-.13*smooth(3.80,5.68,y)*(1-smooth(.15,.76,z)))
        result[:,2] = level
        return result

    vertices, indices, draws = refine_stern(vertices, material_draws, faces, stations)
    y, z = vertices[:,1], vertices[:,2]
    selected = (y > 3.52) | ((y > 2.0) & (z > .28))
    v = vertices[selected].astype(float)
    p, normal, tangent = v[:,:3], v[:,3:6], v[:,6:9]
    bitangent = np.cross(normal,tangent) * v[:,9:10]
    step = .0004
    def transport(direction):
        return stations(p+step*direction) - stations(p-step*direction)
    t, b = transport(tangent), transport(bitangent)
    # A section may taper, but it must never turn back into the previous one.
    dy = transport(np.array((0.,1.,0.))) / (2*step)
    dz = transport(np.array((0.,0.,1.))) / (2*step)
    if np.min(dy[:,1]*dz[:,2] - dy[:,2]*dz[:,1]) < .12:
        raise ValueError("Crossed stations in the aft shell")
    v[:,6:9] = unit_vectors(t)
    v[:,3:6] = unit_vectors(np.cross(t,b)) * v[:,9:10]
    v[:,:3] = stations(p)
    vertices[selected] = v
    skin = np.concatenate([indices[i:i+n] for i,n,m in draws if m in SKIN]).reshape(-1,3)
    finished = vertices[skin,:3]
    finished = finished[finished[:,:,1].max(axis=1)>3.52]
    for low, high, direction in ((-1.56,-.55,1),(-.47,.40,-1),(.60,2.10,1)):
        edge = aft_edge(finished,np.linspace(low,high,61))*direction
        if (np.maximum.accumulate(edge)-edge).max() > .018:
            raise ValueError("A second edge interrupts the stern silhouette")
    return vertices, indices, draws


class LipTravel:
    """Fit a transverse deployment to the actual upper mouth and its blade clearance."""
    def __init__(self, vertices, faces, draws):
        self.stations = np.linspace(.30, 3.68, 129)

        def profile(polygons):
            tri = vertices[polygons, :3]
            tri = tri[tri[:,:,0].min(axis=1) > 0]
            a = tri.reshape(-1,3)
            b = np.roll(tri, -1, axis=1).reshape(-1,3)
            crest = []
            for y in self.stations:
                crosses = (a[:,1] > y) != (b[:,1] > y)
                p, q = a[crosses], b[crosses]
                if not len(p):
                    crest.append((np.nan, np.nan))
                    continue
                hits = p + (q-p) * ((y-p[:,1]) / (q[:,1]-p[:,1]))[:,None]
                crest.append(hits[np.argmax(hits[:,2]), (0,2)])
            crest = np.asarray(crest)
            valid = np.isfinite(crest[:,0])
            if valid.sum() < len(crest) * .45:
                raise ValueError("The upper outlet contour is incomplete")
            return [np.interp(self.stations, self.stations[valid], col[valid]) for col in crest.T]

        # The machined return runs under the teal lip. The ceramic stator edges
        # bound the stationary part of the liner, including the rising aft ends.
        lip = np.concatenate([faces[i//3:(i+n)//3] for i,n,m in draws if m == 9])
        blades = [faces[i//3:(i+n)//3] for i,n,m in draws if m == 3 and vertices[faces[i//3],0].mean() > 0]
        top_blade = max(blades, key=lambda blade: vertices[blade,2].mean())
        self.radius, self.height = profile(lip)
        self.return_faces = vertices[lip,:3].astype(float)
        ids, corners = np.unique(lip, return_inverse=True)
        self.return_tree = BVHTree.FromPolygons(vertices[ids,:3].tolist(), corners.reshape(-1,3).tolist(), all_triangles=True)
        _, blade = profile(top_blade)
        pad = np.pad(blade, 4, mode="edge")
        self.clearance = np.maximum.reduce([pad[i:i+len(blade)] for i in range(9)]) + .014

    def mount(self, y, inset):
        """Contact on the rolled underside and its exact rendered travel."""
        x = np.interp(y, self.stations, self.radius) - inset
        h = np.interp(y, self.stations, self.height)
        hit,_,face,_ = self.return_tree.ray_cast((x,y,h-.14),(0,0,1),.22)
        if hit is None:
            raise ValueError(f"Guide shoe misses the rolled edge at {x:.3f}, {y:.3f}")
        tri = self.return_faces[face]
        bary = np.linalg.solve(np.column_stack((tri[:,:2],np.ones(3))).T, (hit.x,y,1))
        return np.array(hit), bary @ self.offset(tri)

    def offset(self, points):
        x, y, z = points.T
        lip = np.interp(y, self.stations, self.height)
        radius = np.interp(y, self.stations, self.radius)
        base = np.maximum(lip-.14, np.interp(y, self.stations, self.clearance))
        # The two sides of the rolled nose travel together. On the underside,
        # the liner returns to its original position above the fixed stators.
        # Near the jambs the sheet rises above the highest fixed blade. Its
        # planform stays continuous when the outline crosses another vane.
        crest = np.maximum(lip, base+.082)
        underside = smooth(0., 1., (z-base) / (crest-base-.004))
        upper = 1 - smooth(.026, .78, z-crest)
        reach = smooth(-.91, -.13, np.abs(x)-radius)
        t = np.clip((y-.38) / (3.55-.38), 0., 1.)
        chord = (4*t*(1-t))**2
        return np.sign(x) * LIP_EXTENSION * chord * upper * underside * reach

    def fit(self, vertices, indices, draws, first_detail, slide):
        ids = np.unique(np.concatenate([indices[i:i+n] for i,n,m in draws
                                        if m in {4,5,6,7,8,9,43} or m >= first_detail]))
        ids = ids[(vertices[ids,14] == 0) & np.isnan(slide[ids])]
        p = vertices[ids,:3].astype(float)
        offset = self.offset(p)
        active = np.abs(offset) > 1.e-8
        ids, p, offset = ids[active], p[active], offset[active]
        # The local derivative transports the tangent frame at any extension.
        step = .0005
        gradient = np.column_stack([(self.offset(p+v) - self.offset(p-v)) / (2.*step)
                                    for v in np.eye(3)*step])
        driven = np.flatnonzero(np.isfinite(slide) & (slide != 0))
        records = np.zeros(len(ids) + len(driven), dtype=[("vertex","<u4"),("travel","<f4",4)])
        records["vertex"] = np.r_[ids, driven]
        records["travel"][:len(ids)] = np.column_stack((offset, gradient))
        # A guide or piston translates as a rigid part. Its spatial gradient is zero.
        records["travel"][len(ids):,0] = slide[driven]
        blades = np.concatenate([indices[i:i+n] for i,n,m in draws if m == 3])
        if np.max(np.abs(self.offset(vertices[vertices[:,14] >= POSE_BRAKE,:3]))) > .0001:
            raise ValueError("The nacelle travel crosses the dorsal brake seat")
        if np.max(np.abs(self.offset(vertices[blades,:3]))) > .0001:
            raise ValueError("The transverse map would unseat a stator")
        if not len(ids) or not np.isfinite(gradient).all() or gradient[:,0].min() < -.001:
            raise ValueError("Invalid transverse map for the folded turbine skin")
        span = [float(np.max(np.abs(p[:,0] + k*offset))) for k in (0,.25,.5,.75,1)]
        opened = p.copy()
        opened[:,0] += offset
        if span[-1]-span[0] < 1.1 or np.linalg.norm(opened,axis=1).max() >= 6.7:
            raise ValueError(f"Invalid nacelle extension envelope {span}")
        self.check_planform(vertices, indices, draws, records)
        return records, span

    def check_planform(self, vertices, indices, draws, records):
        """Intersect the actual cowling triangles to catch a notch at any vane tip."""
        face_ids = np.concatenate([indices[i:i+n] for i,n,m in draws if m in {6,8,9}]).reshape(-1,3)
        pts = vertices[face_ids, :3]
        travel = np.zeros(len(vertices))
        travel[records["vertex"]] = records["travel"][:,0]
        fractions = np.array((0,.25,.5,.75,1))
        for side in (-1,1):
            shell = face_ids[((side*pts[:,:,0]).min(axis=1)>0) & (pts[:,:,2].max(axis=1)>-1.1)]
            a, b = shell.ravel(), np.roll(shell, -1, axis=1).ravel()
            sections = []
            for y in self.stations:
                hit = (vertices[a,1] > y) != (vertices[b,1] > y)
                i, j = a[hit], b[hit]
                t = (y-vertices[i,1]) / (vertices[j,1]-vertices[i,1])
                x = vertices[i,0] + t*(vertices[j,0]-vertices[i,0])
                dx = travel[i] + t*(travel[j]-travel[i])
                sections.append((side*(x[:,None] + dx[:,None]*fractions)).max(axis=0))
            for widths in np.asarray(sections).T:
                peak = np.argmax(widths)
                for rising in (widths[:peak+1], widths[peak:][::-1]):
                    if (np.maximum.accumulate(rising)-rising).max() > .035:
                        raise ValueError("A second point breaks the nacelle outline")


class Exterior:
    def __init__(self, vertices, triangles, draws):
        faces = np.concatenate([triangles[first // 3:(first + count) // 3]
                                for first, count, material in draws if material in SKIN])
        self.materials = np.concatenate([np.full(count//3, material) for _,count,material in draws if material in SKIN])
        ids, corners = np.unique(faces, return_inverse=True)
        self.tree = BVHTree.FromPolygons(vertices[ids, :3].tolist(),
                                         corners.reshape(-1, 3).tolist(), all_triangles=True)

    def enamel_edge(self, y, inside, outside):
        def enamel(x):
            hit, _, face, _ = self.tree.ray_cast((x,y,5), (0,0,-1), 5.75)
            return hit is not None and self.materials[face] == 6
        if not enamel(inside) or enamel(outside):
            raise ValueError(f"Missing roof panel boundary at y={y:.2f}")
        for _ in range(16):
            mid = .5 * (inside + outside)
            if enamel(mid):
                inside = mid
            else:
                outside = mid
        return inside - math.copysign(.007, outside-inside), y

    def project(self, point, offset, side):
        def cast(a, b):
            origin = (6, a, b) if side else (a, b, 5)
            direction = (-1, 0, 0) if side else (0, 0, -1)
            hit, normal, _, _ = self.tree.ray_cast(origin, direction, 6.3)
            min_width = .015 if side == "fin" else 1.18
            if hit is None or (side and hit.x < min_width):
                return None
            axis = 0 if side else 2
            n = np.asarray(normal)
            return hit[axis], n if n[axis] >= 0 else -n

        a, b = point
        sample = cast(a, b)
        if sample is None:
            # The source has a few sub-centimetre gaps between separate fitted sheets.
            # Bridge only if opposite samples agree on the supporting skin.
            for e in (.004, .009, .015):
                opposite_pairs = ((cast(a-e,b), cast(a+e,b)), (cast(a,b-e), cast(a,b+e)))
                for left, right in opposite_pairs:
                    if left is not None and right is not None and abs(left[0] - right[0]) < .095:
                        sample = (.5 * (left[0] + right[0]), unit_vectors(left[1] + right[1]))
                        break
                if sample is not None:
                    break
        if sample is None:
            raise ValueError(f"Panel at {a:.3f}, {b:.3f} misses the exterior (side={side})")
        position, normal = sample
        hit = np.array((position, a, b) if side else (a, b, position))
        return hit + offset * normal


class Mesh:
    """Batch details by material. Each vertex retains its own authored pose."""
    def __init__(self):
        self.batches = {}
        self.brake_vertices = []

    def add(self, points, faces, material, pose=0, hint=None, slide=np.nan):
        points = np.asarray(points, dtype=np.float64)
        faces = np.asarray(faces, dtype=np.int64).reshape(-1, 3)
        edges = points[faces[:, 1:]] - points[faces[:, 0, None]]
        face_normals = np.cross(edges[:, 0], edges[:, 1])
        valid = np.linalg.norm(face_normals, axis=1) > 1e-9
        faces, face_normals = faces[valid], face_normals[valid]
        if not len(faces):
            return
        if hint is not None and float(face_normals.sum(axis=0) @ hint) < 0:
            faces = faces[:, ::-1]
            face_normals *= -1
        used, remap = np.unique(faces, return_inverse=True)
        normal = np.zeros_like(points)
        for column in faces.T:
            np.add.at(normal, column, face_normals)
        points, normal = points[used], unit_vectors(normal[used])
        if np.ndim(slide):
            slide = np.asarray(slide)[used]
        if not np.isfinite(points).all() or (np.linalg.norm(normal, axis=1) < .99).any():
            raise ValueError("An exterior patch has invalid geometry")
        tangent = unit_vectors(np.cross(np.eye(3)[np.argmin(np.abs(normal), axis=1)], normal))
        uv = points[:, :2] / .58
        vertices = np.column_stack((points, normal, tangent, np.ones(len(points)), uv, uv, np.full(len(points), pose)))
        mirrored = vertices.copy()
        mirrored[:, (0, 3, 6, 9)] *= -1
        if pose:
            mirrored[:, -1] += 1
        self.batches.setdefault(material, []).append((vertices.astype("<f4"), remap.reshape(-1, 3), slide))
        self.batches[material].append((mirrored.astype("<f4"), remap.reshape(-1, 3)[:, ::-1], -slide))
        if pose == POSE_BRAKE:
            self.brake_vertices.append(points)

    def cook(self, first_vertex, first_index, first_material):
        vertices, indices, draws = [], [], []
        slides = [np.full(first_vertex, np.nan)]
        for material, patches in sorted(self.batches.items()):
            count = 0
            for vertex, faces, slide in patches:
                vertices.append(vertex)
                slides.append(np.broadcast_to(slide, (len(vertex),)))
                indices.append((faces.ravel() + first_vertex).astype("<u4"))
                first_vertex += len(vertex)
                count += faces.size
            draws.append((first_index, count, first_material + material))
            first_index += count
        return np.concatenate(vertices), np.concatenate(indices), np.array(draws, dtype="<u4"), np.concatenate(slides)


def quad(a, b, c, d):
    return [(a, b, c), (a, c, d)]


def guide_section(mesh, y, z, rings, slide, cap=False, cylindrical=False):
    """Loft a keyed octagonal guide along x. Reversed inner rings form a real bore."""
    contour = np.array(((-.82,-1),(.82,-1),(1,-.58),(1,.58),(.82,1),(-.82,1),(-1,.58),(-1,-.58)))
    if cylindrical:
        angle = np.arange(16)*math.tau/16
        contour = np.column_stack((np.cos(angle),np.sin(angle)))
    count = len(contour)
    def section(x, width, height):
        return np.column_stack((np.full(count,x), y + width*contour[:,0], z + height*contour[:,1]))
    rows = [section(x, width, height) for x,width,height,_ in rings]
    for a,b,(_,_,_,finish) in zip(rows,rows[1:],rings[1:]):
        if cylindrical:
            faces = [f for i in range(count) for f in quad(i,(i+1)%count,(i+1)%count+count,i+count)]
            mesh.add(np.vstack((a,b)),faces,finish,slide=slide)
        else:
            for i in range(count):
                j = (i+1) % count
                mesh.add((a[i],a[j],b[j],b[i]),quad(0,1,2,3),finish,slide=slide)
    if cap:
        fan = [(0,i,i+1) for i in range(1,count-1)]
        mesh.add(rows[-1], fan, rings[-1][3], hint=(1,0,0), slide=slide)
        mesh.add(rows[0], fan, rings[0][3], hint=(-1,0,0), slide=slide)


def fit_wing_guides(mesh, lip):
    """A keyed spar and paired telescopic rams join each nacelle to its lip."""
    for y, rams in ((1.63,False),(2.22,True)):
        anchor, stroke = lip.mount(y,.029)
        z = np.interp(y, lip.stations, lip.clearance) + .019
        tip = anchor[0]-.012
        heights = (.030,.022,.016,.0095)
        widths = heights if rams else (.110,.084,.060,.038)
        # Each stage remains engaged at full stroke; its end gland will accept
        # the next stage's flats throughout a stop or reversal.
        stage_length = .72
        pitch = .046
        if stage_length - stroke/3 - pitch < .12:
            raise ValueError("Insufficient guide engagement at full deployment")
        for k,(w,h) in enumerate(zip(widths,heights)):
            drive = stroke*k/3
            end = tip - (3-k)*pitch
            start = end-stage_length
            metal = (CARBON,TITANIUM,PISTON,PISTON)[k]
            gauge = .0018 if rams else .004
            rings = [(start,w,h,metal),(end-.045,w,h,metal),
                     (end-.040,w+gauge,h+.0018,TITANIUM),(end-.012,w+gauge,h+.0018,TITANIUM),
                     (end,w,h,GASKET)]
            if k < 3:
                bore_w, bore_h = w-(.003 if rams else .010), h-.003
                if widths[k+1]+gauge >= bore_w or heights[k+1]+.0018 >= bore_h:
                    raise ValueError("The nested slide does not clear its receiver")
                rings += [(end,bore_w,bore_h,TITANIUM),(start,bore_w,bore_h,CARBON),
                          (start,w,h,metal)]
            for centre in ((y-.038,y+.038) if rams else (y,)):
                guide_section(mesh,centre,z,rings,drive,cap=k == 3,cylindrical=rams)
        # Mount both cheeks to a shoe surveyed on the actual underside. Every
        # corner of the shoe stays on its supporting triangle as the lip opens.
        perimeter = [(-.084,.022),(-.070,.038),(.070,.038),(.084,.022),
                     (.070,.012),(-.070,.012)]
        pads = [lip.mount(y+dy,inset) for dy,inset in perimeter]
        points = np.array([p for p,_ in pads])
        drives = np.array([dx for _,dx in pads])
        face = [(0,i,i+1) for i in range(1,len(points)-1)]
        lower = points-(0,0,.008)
        mesh.add(lower,face,TITANIUM,hint=(0,0,-1),slide=drives)
        for i in range(len(points)):
            j = (i+1)%len(points)
            mesh.add((lower[i],points[i],points[j],lower[j]),quad(0,1,2,3),GASKET,
                     slide=drives[[i,i,j,j]])
        half_pin = .062 if rams else .049
        for side in (-1,1):
            top = lip.mount(y+side*half_pin,.029)[0][2]+.004
            bottom = z-.016
            centre = (top+bottom)/2
            cheek = (top-bottom)/2
            rings = [(tip-.032,.009,cheek*.67,TITANIUM),(tip-.008,.012,cheek,TITANIUM),
                     (tip+.012,.012,cheek,TITANIUM),(tip+.019,.010,cheek*.82,TITANIUM)]
            guide_section(mesh,y+side*half_pin,centre,rings,stroke,cap=True)
        # The through-pin connects the rod eyes to both cheeks, with retained ends.
        angles = np.arange(16)*math.tau/16
        prev = None
        for depth,radius,finish in ((-half_pin-.015,.010,PISTON),(-half_pin-.013,.013,PISTON),
                                    (-half_pin-.009,.011,GASKET),(half_pin+.009,.011,TITANIUM),
                                    (half_pin+.013,.013,GASKET),(half_pin+.015,.010,PISTON)):
            ring = np.column_stack((tip-.005+radius*np.cos(angles),np.full(16,y+depth),z+radius*np.sin(angles)))
            if prev is not None:
                mesh.add(np.vstack((prev,ring)),[f for i in range(16) for f in quad(i,i+16,(i+1)%16+16,(i+1)%16)],
                         finish,slide=stroke)
            if abs(depth) > half_pin+.014:
                mesh.add(ring,[(0,i,i+1) for i in range(1,15)],PISTON,hint=(0,np.sign(depth),0),slide=stroke)
            prev = ring


def round_outline(points):
    polygon = np.asarray(points, dtype=float)
    divisions = 2 if np.ptp(polygon,axis=0).max() > .76 else 1
    for _ in range(divisions):
        following = np.roll(polygon, -1, axis=0)
        polygon = np.stack((.81 * polygon + .19 * following,
                            .19 * polygon + .81 * following), axis=1).reshape(-1, 2)
    # Keep the projection close to the authored contour through the recess.
    return np.concatenate([np.linspace(a, b, max(1, math.ceil(np.linalg.norm(b-a) / .078)), endpoint=False)
                           for a, b in zip(polygon, np.roll(polygon, -1, axis=0))])


def fitted_strip(mesh, shell, path, width, height, material, side=False, taper=0.0):
    anchors = np.asarray(path, dtype=float)
    if len(anchors) < 12:
        # Round the drafted panel breaks while retaining their exact endpoints.
        for _ in range(2):
            a, b = anchors[:-1], anchors[1:]
            fillets = np.stack((.75*a + .25*b, .25*a + .75*b), axis=1)
            anchors = np.vstack((anchors[0], fillets.reshape(-1,2), anchors[-1]))
    centres = np.concatenate([np.linspace(a, b, max(1, math.ceil(np.linalg.norm(b-a) / .035)), endpoint=False)
                              for a, b in zip(anchors[:-1], anchors[1:])] + [anchors[-1:]])
    delta = unit_vectors(np.gradient(centres, axis=0))
    perpendicular = np.column_stack((-delta[:, 1], delta[:, 0]))
    if taper:
        length = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(centres, axis=0), axis=1))]
        perpendicular *= (.08 + .92 * smooth(0, taper, np.minimum(length, length[-1] - length)))[:, None]
    pairs = [shell.project(point + sign * width * across / 2, height, side)
             for point, across in zip(centres, perpendicular) for sign in (-1, 1)]
    mesh.add(pairs, [f for i in range(0, len(pairs) - 2, 2) for f in quad(i, i+1, i+3, i+2)],
             material, hint=(1, 0, 0) if side else (0, 0, 1))


def fastener(mesh, shell, centre, height, side=False, radius=.014):
    a, b = centre
    for scale, raised, material in ((1, .001, SEAM), (.72, .002, TITANIUM)):
        ring = [(a + scale * radius * math.cos(t), b + scale * radius * math.sin(t))
                for t in np.linspace(0, 2 * math.pi, 10, endpoint=False)]
        points = [shell.project(centre, height + raised, side)]
        points += [shell.project(p, height + raised, side) for p in ring]
        mesh.add(points, [(0, i+1, (i+1) % len(ring) + 1) for i in range(len(ring))], material,
                 hint=(1, 0, 0) if side else (0, 0, 1))


def fit_body(mesh, shell):
    # Panel breaks run from the dorsal spine towards the canopy and nacelle.
    for joint in (((0,-1.01),(.39,-.99),(.87,-.81),(1.27,-.49),shell.enamel_edge(-.02,1.46,1.89)),
                  (shell.enamel_edge(1.23,.76,0),(.76,1.23),(1.12,1.30),(1.53,1.52),
                   (1.91,1.91),(2.30,2.05),shell.enamel_edge(2.14,2.37,3.34))):
        fitted_strip(mesh, shell, joint, .009, .0045, SEAM)
    for p in ((.53,-.91),(1.29,-.38),(.83,1.27),(1.49,1.56),(1.87,1.91)):
        fastener(mesh, shell, p, .0045)

    # Stagger panel breaks between the sill, the side instrument and the nacelle.
    for joint in (((-2.26,-1.30),(-2.24,-1.37),(-2.31,-1.47),(-2.42,-1.60)),
                  ((-.88,-1.07),(-.75,-1.17),(-.79,-1.32),(-.98,-1.63)),
                  ((.80,-.095),(.94,-.14),(1.05,-.26),(1.00,-.38))):
        fitted_strip(mesh, shell, joint, .0075, .0035, SEAM, side=True)
    for p in ((-2.29,-1.38),(-2.39,-1.54),(-.82,-1.24),(-.91,-1.48),
              (.89,-.147),(1.00,-.247),(1.61,-.207),(1.82,-.216),(2.07,-.246)):
        fastener(mesh, shell, p, .004, side=True)


def fit_brake(mesh, shell):
    """Form a hinged dorsal spoiler on the pressure skin inboard of the turbine."""
    outline = round_outline(((.71,2.34),(1.47,2.09),(1.50,2.20),
                             (1.30,2.87),(.99,3.43),(.71,3.52),(.61,3.35)))
    centre = outline.mean(axis=0)
    count = len(outline)
    bridge = [f for i in range(count) for f in quad(i,(i+1)%count,count+(i+1)%count,count+i)]
    def crown(scale, height):
        return np.asarray([shell.project(centre + scale*(p-centre), height, False) for p in outline])

    # The seat stays on the sealed pressure shell. Its leaf has a painted upper
    # surface, a rolled edge and a dark underside exposed only during braking.
    for pose, layers in ((0, ((0,.003,CARBON),(.35,.0045,CARBON),(.70,.0045,CARBON),(.96,.0045,CARBON),(1,.0035,SEAM))),
                         (POSE_BRAKE, ((0,.015,BODY),(.30,.015,BODY),(.60,.015,BODY),(.86,.015,BODY),(.973,.013,BODY),
                                       (.980,.010,TRIM),(.975,.007,GASKET),(.88,.007,CARBON),(.55,.007,CARBON),(0,.007,CARBON)))):
        previous = None
        for i,(scale,lift,material) in enumerate(layers):
            ring = crown(scale, lift)
            if previous is not None:
                mesh.add(np.vstack((previous,ring)), bridge, material, pose,
                         hint=(0,0,-1 if pose and i >= 7 else 1))
            previous = ring
    pin = shell.project((.73,2.34), .011, False)
    end = shell.project((1.46,2.10), .011, False)
    axis = unit_vectors(end-pin)
    rel = np.vstack(mesh.brake_vertices) - pin
    opened = pin + rel*math.cos(BRAKE_ANGLE) + np.cross(axis,rel)*math.sin(BRAKE_ANGLE) + (rel@axis)[:,None]*axis*(1-math.cos(BRAKE_ANGLE))
    if np.linalg.norm(opened,axis=1).max() >= 6.7 or (opened[:,2]-rel[:,2]-pin[2]).max() < .5:
        raise ValueError("The dorsal brake does not clear its seat")
    return pin, axis


def fit_grille_guide(mesh, vertices, faces, draws):
    # The six hot leading edges survey the double curvature of the turbine.
    # Fit each station through the blade tips so the retainer bridges the gaps.
    hot_faces = np.concatenate([faces[first//3:(first+count)//3]
                                for first, count, mat in draws if mat == 3])
    tips = np.unique(vertices[np.unique(hot_faces), :3], axis=0)
    tips = tips[tips[:, 0] > 0]
    path = round_outline(((.48,-1.396),(.68,-1.163),(1.13,-.772),(1.36,-.697),
                          (1.83,-.683),(2.38,-.716),(2.50,-.754),(2.40,-.814),
                          (1.52,-1.201),(1.02,-1.395),(.76,-1.43),(.51,-1.43)))
    centres, normals = [], []
    for y,z in path:
        dy, dz = (tips[:, 1:] - (y,z)).T
        weight = np.exp(-.5*((dy/.14)**2 + (dz/.19)**2))
        basis = np.column_stack((np.ones_like(dy), dy, dz, dy*dy))
        coef = np.linalg.lstsq(basis*weight[:,None], tips[:,0]*weight, rcond=None)[0]
        centres.append((coef[0], y, z))
        normals.append(unit_vectors(np.array((1., -coef[1], -coef[2]))))
    centres, normals = np.asarray(centres), np.asarray(normals)
    tangent = unit_vectors(np.roll(centres, -1, axis=0) - np.roll(centres, 1, axis=0))
    across = unit_vectors(np.cross(normals, tangent))
    normals = unit_vectors(np.cross(tangent, across))
    profile = ((-.023,-.014),(-.025,.006),(-.017,.019),(-.011,.021),
               (.011,.021),(.017,.019),(.025,.006),(.023,-.014))
    surfaces = (CARBON, TITANIUM, AMBER, HOT_GUIDE, AMBER, TITANIUM, CARBON, CARBON)
    rows = np.asarray([centres + width*across + lift*normals for width,lift in profile])
    n = len(path)
    bridges = [f for i in range(n) for f in quad(i,(i+1)%n,n+(i+1)%n,n+i)]
    for i, material in enumerate(surfaces):
        mesh.add(np.vstack((rows[i], rows[(i+1)%len(rows)])), bridges, material)


def fit_fin(mesh, shell, vertices, faces, draws):
    # Follow the two painted panels of the film fin from root to crown.
    # The light sits in the turquoise leading panel, the hinge in the ivory rudder.
    for finish, inlay, width in ((8,AMBER,.010),(6,SEAM,.008)):
        selected = np.concatenate([faces[i//3:(i+n)//3] for i,n,mat in draws if mat == finish])
        triangles = vertices[selected,:3]
        triangles = triangles[triangles[:,:,2].max(axis=1) > .96]
        a = triangles.reshape(-1,3)
        b = np.roll(triangles, -1, axis=1).reshape(-1,3)
        path = []
        for z in np.linspace(1.025, triangles[:,:,2].max()-.115, 41):
            crossing = (a[:,2] > z) != (b[:,2] > z)
            p, q = a[crossing], b[crossing]
            points = p + (q-p)*((z-p[:,2])/(q[:,2]-p[:,2]))[:,None]
            y = points[(points[:,0] > .008) & (points[:,1] > 1.2),1]
            path.append((.25*y.min() + .75*y.max(), z))
        if finish == 6:
            y, z = np.asarray(path).T
            path = np.column_stack((np.polyval(np.polyfit(z, y, 1), z), z))
        fitted_strip(mesh, shell, path, width, .0035, inlay, side="fin", taper=.10)


def fit_support_outlets(mesh, shell):
    # The four hover ports share the existing flight profile's two stations.
    # Seat the entire rim and its recessed dark disk on the curved lower shell.
    angles = np.linspace(0, 2 * math.pi, 28, endpoint=False)
    for station in (.18, 2.26):
        rows = []
        for radius, proud in ((.110,.0015),(.100,.008),(.084,.013),(.071,.004),(0.,.004)):
            row = []
            for angle in angles:
                x, y = 1.36 + radius * math.cos(angle), station + radius * math.sin(angle)
                point, _, _, _ = shell.tree.ray_cast((x,y,-4), (0,0,1), 2.2)
                if point is None:
                    raise ValueError("A hover port misses the lower nacelle")
                row.append((x, y, point.z - proud))
            rows.append(row)
        if abs(rows[-1][0][2] + 2.14) > .02:
            raise ValueError("The stabilizer plume must start inside its fitted outlet")
        n = len(angles)
        bridge = [f for i in range(n) for f in quad(i,(i+1)%n,n+(i+1)%n,n+i)]
        for i, material in enumerate((SEAM,TITANIUM,GASKET,CARBON)):
            mesh.add(rows[i] + rows[i+1], bridge, material, hint=(0,0,-1))


def material_records(old):
    def material(color, metal, roughness, emission=(0,0,0), enamel=False):
        if enamel:
            record = bytearray(old[6*96:7*96])
            struct.pack_into("<4f3f4f", record, 0, *color, 1, *emission, metal, roughness, 1, 1)
            return record
        return struct.pack("<4f3f4f2I5i5II", *color, 1, *emission, metal, roughness, 1, 1,
                           0, 0, *[-1]*5, *[0]*5, 0)
    # The skin and movable panels share the same pearl coat and enamel maps.
    ivory = (.80,.764,.706)
    struct.pack_into("<3f", old, 6*96, *ivory)
    struct.pack_into("<3f", old, 8*96, .008,.118,.148)
    struct.pack_into("<3f", old, 10*96, .008,.118,.148)
    struct.pack_into("<3f", old, 3*96+16, .095,.031,.008)
    hot = bytearray(old[3*96:4*96])
    struct.pack_into("<3f", hot, 0, .55,.225,.043)
    struct.pack_into("<3f", hot, 16, 1.85,.48,.061)
    return b"".join((
        material(ivory,.09,.418,enamel=True),
        material((.773,.738,.684),.10,.433,enamel=True),
        material((.025,.035,.040),.14,.62),
        material((.23,.263,.279),.68,.48),
        material((.008,.118,.148),.32,.36),
        material((.026,.032,.035),.23,.60),
        material((.68,.286,.040),.42,.34,(1.7,.49,.043)),
        material((.27,.261,.24),.22,.60),
        hot,
        material((.53,.58,.60),.74,.31),
    ))


def empty_cabin(vertex, indices, draws):
    retained = []
    geometry = []
    first_index = 0
    for first, count, material in draws:
        if material in OCCUPANTS:
            continue
        retained.append((first_index, count, material))
        geometry.append(indices[first:first+count])
        first_index += int(count)
    used, remap = np.unique(np.concatenate(geometry), return_inverse=True)
    return vertex[used], remap.astype("<u4"), np.array(retained, dtype="<u4")


def discard_unused_images(raw, start_m, end_m, count):
    material = bytearray(raw[start_m:end_m])
    for i in OCCUPANTS:
        struct.pack_into("<5i", material, i*96+52, *[-1]*5)
    groups = [struct.unpack_from("<5i", material, pos) for pos in range(52, len(material), 96)]
    used = {i for group in groups for i in group if i >= 0}
    images = []
    remap = {-1: -1}
    offset = end_m
    for i in range(count):
        _, length = struct.unpack_from("<2I", raw, offset)
        next_offset = offset + 8 + length
        if i in used:
            remap[i] = len(images)
            images.append(raw[offset:next_offset])
        offset = next_offset
    for i, group in enumerate(groups):
        struct.pack_into("<5i", material, i*96+52, *(remap[k] for k in group))
    return material, images, offset


def packet_image(rgb, srgb):
    """RGB8 or RGBA8 PNG in the VSX image table. Data charts use linear channels."""
    height, width, _ = rgb.shape
    def chunk(name, data):
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data))
    pixels = b"".join(b"\0" + row.tobytes() for row in rgb)
    header = struct.pack(">2I5B", width, height, 8, {3: 2, 4: 6}[rgb.shape[2]], 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(pixels, 9)) + chunk(b"IEND", b"")
    return struct.pack("<2I", int(srgb), len(png)) + png


def exhaust_chart(vertices, faces, draws, axis, across):
    """Measure the five open channels in the direction of discharge."""
    up = unit_vectors(np.cross(axis, across))
    up *= np.sign(up[2])
    frame = np.stack((across,up,axis))
    stations = np.linspace(.012,.988,65)
    edges = []
    for i,n,m in draws:
        if m != 3:
            continue
        tri = vertices[faces[i//3:(i+n)//3],:3].astype(float)
        if tri[0,0,0] * across[0] < 0:
            continue
        a = tri.reshape(-1,3)
        b = np.roll(tri,-1,axis=1).reshape(-1,3)
        ys = a[:,1].min() + stations*np.ptp(a[:,1])
        path = []
        for y in ys:
            hit = (a[:,1]>y) != (b[:,1]>y)
            p, q = a[hit], b[hit]
            cut = p + (q-p) * ((y-p[:,1])/(q[:,1]-p[:,1]))[:,None]
            path.append(cut[np.argmax(cut[:,0]*np.sign(across[0]))])
        edges.append(np.asarray(path))
    if len(edges) != 6:
        raise ValueError("A turbine must supply six discharge edges")
    return chart_from_edges(edges, frame, stations)


def chart_from_edges(edges, frame, stations, bend_stations=False, duct_axis=(0, 0, 1)):
    """Project the five slots and weight emission along the physical duct axis expressed in chart space."""
    across = frame[0]
    edges.sort(key=lambda edge: edge[:,2].mean())
    # The backmost intersection in the exhaust frame is the visible outlet,
    # including where the raked ends or the forward part fold in projection.
    points = np.concatenate(edges) @ frame.T
    low, high = points.min(0), points.max(0)
    radii = .5*(high-low)[:2] + CHART_PADDING
    origin = np.r_[.5*(low+high)[:2],low[2]]
    depth = high[2]-low[2]
    sections = len(stations)
    polys = np.array([f for row in range(5) for k in range(sections-1)
                      for f in quad(row*sections+k, row*sections+k+1,
                                    (row+1)*sections+k+1, (row+1)*sections+k)])
    tree = BVHTree.FromPolygons(points.tolist(),polys.tolist(),all_triangles=True)
    uv = points[polys,:2]
    # Signed barycentric coordinates interpolate blade station and gap height.
    def cross2(a,b):
        return a[0]*b[1] - a[1]*b[0]
    width, height = 192, 96
    chart = np.zeros((height,width,3))
    covered = np.zeros((height,width),dtype=bool)
    for j in range(height):
        y = origin[1] + ((j+.5)*2/height-1)*radii[1]
        for i in range(width):
            x = origin[0] + ((i+.5)*2/width-1)*radii[0]
            p,normal,face,_ = tree.ray_cast((x,y,high[2]+.05),(0,0,-1),depth+.10)
            if p is None:
                continue
            a,b,c = uv[face]
            ab, ac, ap = b-a, c-a, np.array((x,y))-a
            area = cross2(ab,ac)
            if abs(area) < 1e-12:
                continue
            u, v = cross2(ap,ac)/area, cross2(ab,ap)/area
            bary = np.array((1-u-v,u,v))
            ids = polys[face]
            along = bary @ stations[ids % sections]
            band = bary @ (ids // sections)
            gap = band - math.floor(band)
            jamb = smooth(.012,.18,min(along,1-along)) * smooth(.02,.70,min(band,5-band))
            # Flux belongs to the physical duct. The chart can look along a different discharge axis.
            flux = jamb * smooth(.025,.64,abs(normal.dot(duct_axis)))
            chart[j,i] = ((p.z-low[2])/depth, flux*smooth(.085,.39,min(gap,1-gap)), flux)
            covered[j,i] = True
    if covered.mean() < .22 or chart[:,:,1].max() < .97:
        raise ValueError("The five turbine channels do not fill the fitted mouth")
    # Extend the origin depth across the border. Filtering an empty neighbour
    # may soften emission, but must never move the gas upstream into the hull.
    filled = np.column_stack(np.where(covered))
    nearest = KDTree(len(filled))
    for k,(j,i) in enumerate(filled):
        nearest.insert((i*radii[0]/width,j*radii[1]/height,0),k)
    nearest.balance()
    for j,i in zip(*np.where(~covered)):
        _,k,_ = nearest.find((i*radii[0]/width,j*radii[1]/height,0))
        row,col = filled[k]
        chart[j,i,0] = chart[row,col,0]
    if bend_stations:
        # Begin each column's turn beyond its furthest lip, including the filter footprint.
        last = chart[:, :, 0].max(axis=0)
        pad = np.pad(last, 1, mode='edge')
        last = np.maximum.reduce((pad[:-2], pad[1:-1], pad[2:]))
        chart = np.dstack((chart, np.broadcast_to(last, covered.shape)))
    image = packet_image(np.rint(np.clip(chart,0,1)*255).astype(np.uint8), False)
    print(f"Outlet {np.sign(across[0]):+.0f}: {2*radii[0]:.2f} x {2*radii[1]:.2f} m chart, "
          f"{depth:.2f} m rake, {covered.mean():.0%} open coverage")
    return origin @ frame, radii, depth, image


def fit_exhaust(controls, vertices, faces, draws, images):
    pos = len(controls) - (8 + 2*48 + 12)
    if struct.unpack_from("<4sI",controls,pos) != (b"JET2",2) or controls[-12:-8] != b"THR1":
        raise ValueError("Missing the two surveyed turbine axes")
    fitted = bytearray(struct.pack("<4sI",b"JET3",2))
    for k in range(2):
        original = np.frombuffer(controls,"<f4",12,pos+8+k*48)
        axis, across = original[4:7], original[8:11]
        mouth, radii, depth, image = exhaust_chart(vertices,faces,draws,axis,across)
        if image not in images:
            images.append(image)
        index = images.index(image)
        fitted.extend(struct.pack("<16f",*mouth,radii[0],*axis,radii[1],*across,0,index+1,depth,0,0))
    return controls[:pos] + fitted + controls[-12:]


def paint_chine(vertices, faces, draws, materials, image_index):
    # The original film fibre is retained as the belt's lower physical edge.
    # Paint uses the skin's spare UV set so its colour crosses panel seams
    # without an overlapping shell. The roughness and relief keep their UVs.
    width, height = 1024, 512
    y = -6.4 + (np.arange(width)+.5)*12.8/width
    z = (3.0 - (np.arange(height)+.5)*6.0/height)[:,None]
    t = np.clip((y+3.10)/5.49, 0, 1)
    rail = -1.833 - .061*(1-t)**3
    low = rail + .013 + 1.33*smooth(1.65, 5.35, y)
    belt_height = (.19 + .125*smooth(-1.15,.5,y))*smooth(-3.13,-2.64,y)*(1-smooth(2.50,5.22,y))
    coverage = np.clip(.5 + np.minimum(z-low, low+belt_height-z)*height/6.0, 0, 1)
    coverage[:,belt_height < .0001] = 0
    ivory = struct.unpack_from("<3f", materials, 6*96)
    petrol = np.array(struct.unpack_from("<3f", materials, 8*96)) / ivory
    linear = 1 + coverage[:,:,None]*(petrol-1)
    rgb = np.uint8(np.rint(255*(1.055*linear**(1/2.4)-.055)))
    skin = np.unique(np.concatenate([faces[i//3:(i+n)//3].ravel() for i,n,m in draws if m == 6]))
    vertices[skin,12] = (vertices[skin,1]+6.4)/12.8
    vertices[skin,13] = (3-vertices[skin,2])/6.0
    struct.pack_into("<i", materials, 6*96+52, image_index)
    struct.pack_into("<I", materials, 6*96+72, 1)
    return packet_image(rgb, True)


def cook_glass(vertex, indices, draws, material, transport=False):
    # The game and fitter read the same fixed dimensions and angular scale.
    header = Path(__file__).resolve().parents[3] / "MyPlanetEngine" / "ShipProfiles.h"
    values = {terms[1]: float(terms[2].rstrip("f")) for line in header.read_text().splitlines()
              if line.startswith(("#define SHUTTLE_PANE_", "#define SHUTTLE_WATER_"))
              for terms in [line.split()]}
    cols, rows = (int(values[f"SHUTTLE_PANE_{axis}"]) for axis in ("COLUMNS", "ROWS"))
    scale = values["SHUTTLE_PANE_RADIUS"]
    pitch = values["SHUTTLE_WATER_TEXEL"]
    width = values["SHUTTLE_WATER_WIDTH"] * pitch
    height = values["SHUTTLE_WATER_HEIGHT"] * pitch
    bottom = values["SHUTTLE_WATER_Y"]
    origin = (0, values["SHUTTLE_PANE_CENTRE_Y"], values["SHUTTLE_PANE_CENTRE_Z"])
    if not transport:
        origin = (0, .80, -.88)  # Original film weather projection.
    panes = np.concatenate([indices[first:first+count] for first,count,m in draws
                            if struct.unpack_from("<I",material,m*96+44)[0] == 2])
    points, corners = np.unique(panes, return_inverse=True)
    glass = BVHTree.FromPolygons(vertex[points,:3].tolist(), corners.reshape(-1,3).tolist(), all_triangles=True)

    coords = [(x,y,0.0) for y in np.linspace(bottom,bottom+height,rows)
              for x in np.linspace(-width/2,width/2,cols)]
    fit = np.zeros((len(coords),4),dtype="<f4")
    valid = np.zeros(len(coords),dtype=bool)
    for i, (x,y,_) in enumerate(coords):
        a, e = x/scale, y/scale
        direction = (math.sin(a)*math.cos(e), -math.cos(a)*math.cos(e), math.sin(e))
        hit, normal, _, radius = glass.ray_cast(origin,direction,10.0)
        if hit is None:
            continue
        n = np.array(normal)
        if n @ direction < 0:
            n = -n
        fit[i,:3] = n * radius
        valid[i] = True
    if not .24 < valid.mean() < .86:
        raise ValueError(f"The glass covers {valid.mean():.1%} of the chart")
    centre = (cols - 1)//2 + cols * round(-bottom / height * (rows - 1))
    if not valid[centre]:
        raise ValueError("The front sightline misses the weather chart")

    def tree(polygon):
        selected = np.flatnonzero(polygon)
        kd = KDTree(len(selected))
        for i in selected:
            kd.insert(coords[i], int(i))
        kd.balance()
        return kd

    interior, exterior = tree(valid), tree(~valid)
    half_step = .5 * min(width/(cols-1), height/(rows-1))
    for i, point in enumerate(coords):
        if valid[i]:
            _, _, distance = exterior.find(point)
            fit[i,3] = max(0.0, distance - half_step)
        else:
            _, near, distance = interior.find(point)
            fit[i,:3] = fit[near,:3]
            fit[i,3] = -max(0.0, distance - half_step)
    print(f"Pane fit {cols} x {rows}, {valid.mean():.1%} coverage.")
    return b"WTR1" + fit.tobytes()


def cook(source, destination):
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != FILM_HASH:
        raise ValueError("The exterior is fitted to the exact film VSX. Use the pristine source.")
    version, nv, ni, nd, nm, images = struct.unpack_from("<6I", raw, 4)
    start_i = 28 + nv * 60
    start_d = start_i + ni * 4
    start_m = start_d + nd * 12
    end_m = start_m + nm * 96
    vertex = np.frombuffer(raw, dtype="<f4", offset=28, count=nv*15).reshape(-1, 15).copy()
    indices = np.frombuffer(raw, dtype="<u4", offset=start_i, count=ni)
    draws = np.frombuffer(raw, dtype="<u4", offset=start_d, count=nd*3).reshape(-1, 3)
    vertex, indices, draws = empty_cabin(vertex, indices, draws)
    removed_crew = (ni-len(indices))//3
    clean_triangles = len(indices)//3
    material, retained_images, controls_at = discard_unused_images(raw, start_m, end_m, images)
    vertex, indices, draws = finish_stern(vertex, indices.reshape(-1,3), draws)
    nv, ni, nd = len(vertex), len(indices), len(draws)
    shell = Exterior(vertex, indices.reshape(-1, 3), draws)
    mesh = Mesh()
    travel = LipTravel(vertex, indices.reshape(-1,3), draws)
    fit_wing_guides(mesh, travel)
    fit_body(mesh, shell)
    fit_grille_guide(mesh, vertex, indices.reshape(-1, 3), draws)
    fit_fin(mesh, shell, vertex, indices.reshape(-1, 3), draws)
    fit_support_outlets(mesh, shell)
    brake, axis = fit_brake(mesh, shell)
    add_v, add_i, add_d, slide = mesh.cook(nv, ni, nm)
    records, span = travel.fit(np.vstack((vertex, add_v)), np.concatenate((indices, add_i)),
                               np.vstack((draws, add_d)), nm, slide)
    extra_materials = material_records(material)
    retained_images.append(paint_chine(vertex, indices.reshape(-1,3), draws, material, len(retained_images)))
    controls = fit_exhaust(raw[controls_at:], vertex, indices.reshape(-1,3), draws, retained_images)
    radius = np.linalg.norm(add_v[:, :3], axis=1).max()
    if radius >= 6.7 or add_i.size > .06 * ni:
        raise ValueError(f"The exterior exceeds its geometric budget: {radius:.2f} m, {add_i.size//3} triangles")
    trailer = struct.pack("<4s7fI", b"FLW2", *brake, BRAKE_ANGLE, *axis, len(records)) + records.tobytes()
    canopy = cook_glass(vertex, indices, draws, material)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix(".tmp.vsx")
    with temp.open("wb") as f:
        f.write(b"VSX1" + struct.pack("<6I", version, nv+len(add_v), ni+len(add_i), nd+len(add_d),
                                    nm+len(extra_materials)//96, len(retained_images)))
        for data in (vertex, add_v, indices, add_i, draws, add_d):
            f.write(data.tobytes())
        f.write(material)
        f.write(extra_materials)
        for texture in retained_images:
            f.write(texture)
        f.write(controls)
        f.write(trailer)
        f.write(canopy)
    temp.replace(destination)
    print(f"Fitted the engine lips and guides to {len(records)} vertices. Added {add_i.size//3} detail triangles.")
    print(f"Refined the aft skin by {ni//3-clean_triangles} triangles. Removed {removed_crew} occupant triangles and two crew images.")
    print("Outer lip positions at 0, 25, 50, 75 and 100 percent:", [round(x,3) for x in span])
    print("Packet SHA-256", hashlib.file_digest(destination.open("rb"), "sha256").hexdigest())


if __name__ == "__main__":
    source, destination = map(Path, sys.argv[sys.argv.index("--") + 1:])
    if source.resolve() == destination.resolve():
        raise ValueError("Use a distinct output path to preserve the film package.")
    cook(source, destination)
