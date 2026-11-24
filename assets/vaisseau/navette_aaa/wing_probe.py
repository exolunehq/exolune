"""Check the complete ship with the wing clip at every keyed pose.

Run Blender in background on the built .blend, with --python-exit-code 1 --python wing_probe.py.
Optional arguments after --: --step N, --gear down,up,cycle. Any unexpected intersection fails.
"""
import argparse
import os
import sys

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anim
import hullgrid
import meshkit
import wing_bay
import wings


class Mesh:
    def __init__(self, obj):
        self.obj = obj
        mesh = obj.data
        xyz = np.empty(3 * len(mesh.vertices), np.float32)
        mesh.vertices.foreach_get("co", xyz)
        self.xyz = xyz.reshape(-1, 3)
        mesh.calc_loop_triangles()
        triangles = np.empty(3 * len(mesh.loop_triangles), np.int32)
        mesh.loop_triangles.foreach_get("vertices", triangles)
        self.tris = triangles.reshape(-1, 3).tolist()
        self.matrix = None
        self.update()

    def update(self):
        m = np.asarray(self.obj.matrix_world)
        if self.matrix is None or not np.array_equal(self.matrix, m):
            self.matrix = m
            self.world = self.xyz @ m[:3,:3].T + m[:3,3]
            self.low = self.world.min(axis=0)
            self.high = self.world.max(axis=0)
            self._tree = None

    def tree(self):
        if self._tree is None:
            self._tree = BVHTree.FromPolygons(self.world.tolist(), self.tris, all_triangles=True)
        return self._tree

    def hits(self, other):
        if (self.high < other.low).any() or (other.high < self.low).any():
            return []
        return self.tree().overlap(other.tree())


def check_stowage(meshes):
    """Cast outward from every stowed port wing and spar vertex to the uncut shoulder."""
    grid = hullgrid.HullGrid()
    indices = np.arange(grid.na * grid.nb).reshape(grid.na, grid.nb)
    shell = BVHTree.FromPolygons(grid.points.reshape(-1, 3).tolist(), meshkit.grid_faces(indices).tolist())
    parts = [m.world for m in meshes if m.obj.name.endswith("_G") and
             m.obj.name.startswith(("Aile_Emplanture_", "Aile_Saumon_", "Aile_Glissiere_"))]
    vertices = np.unique(np.vstack(parts), axis=0)
    clearance = float("inf")
    for point in vertices:
        hit = shell.ray_cast(point, (1, 0, 0))
        assert hit[0] is not None, f"stowed vertex outside the shoulder at {point}"
        clearance = min(clearance, hit[3])
    liner = next(m for m in meshes if m.obj.name == "Aile_Baie_G")
    for x, y, z in np.vstack([liner.world, liner.world[liner.tris].mean(axis=1)]):
        hit = shell.ray_cast((0.4, y, z), (1, 0, 0))
        assert hit[0] is not None and x <= hit[0].x + 0.001, f"bay liner outside the shoulder at {(x, y, z)}"
    airlock = float(vertices[:, 0].min()) - 0.62
    assert min(clearance, airlock) > 0.001
    print(f"STOW {clearance*1000:.1f} mm to the skin along X, {airlock*1000:.1f} mm beyond the airlock envelope")


def closure_rays():
    """Sample the whole aperture, both jambs, all edges and the centre line at grazing offsets."""
    g = hullgrid.HullGrid()
    wings.fit_bay(g)
    g, datum = wing_bay.installation(g)
    c = wing_bay.Shoulder(g, wings.airfoil)
    a0, a1 = wing_bay.columns(g)
    columns = np.unique(np.r_[c.a, (c.a[1:]+c.a[:-1])/2, a0, a0+0.005, a1-0.005, a1])
    top, bottom = c.row_z(columns, wing_bay.TOP), c.row_z(columns, wing_bay.BOTTOM)
    profiles = [np.interp(columns, c.a, p) for p in (c.upper, c.lower)]
    levels = [bottom*(1-u) + top*u for u in np.linspace(0, 1, 33)]
    for z in (top, bottom, *profiles, np.full_like(columns, wing_bay.Z)):
        levels.extend(z+d for d in (-0.00045, 0, 0.00045))
    p, n = c.skin(columns[:,None], np.stack(levels, axis=1))
    return p.reshape(-1,3) @ datum[:3,:3].T + datum[:3,3], n.reshape(-1,3) @ datum[:3,:3].T


def check_closure(meshes, samples, phase, side):
    """A through-gap fails even when every moving part clears the hull without collision."""
    covers = [m for m in meshes if m.obj.name == "Coque_Principale" or
              (m.obj.name.startswith("Aile_") and m.obj.name.endswith("_" + side))]
    vertices, triangles = [], []
    for m in covers:
        triangles.extend((np.asarray(m.tris) + len(vertices)).tolist())
        vertices.extend(m.world.tolist())
    shell = BVHTree.FromPolygons(vertices, triangles, all_triangles=True)
    points, normals = samples
    if side == "D":
        points, normals = points * (-1, 1, 1), normals * (-1, 1, 1)
    across = wing_bay.unit(np.column_stack((normals[:,2], np.zeros(len(normals)), -normals[:,0])))
    along = wing_bay.unit(np.cross(normals, across))
    count, deepest, witness = 0, 0, None
    for lean in (0, 0.55*along, -0.55*along, 0.60*across, -0.60*across):
        dirs = wing_bay.unit(normals + lean)
        for p, d, cosine in zip(points, dirs, (dirs*normals).sum(axis=1)):
            hit = shell.ray_cast(p+2.2*d, -d, 2.275)
            depth = (hit[3]-2.2)*cosine if hit[0] is not None else 0.075
            if depth > 0.008:
                count += 1
            if depth > deepest:
                deepest, witness = depth, p
    print(f"CLOSURE {phase} {side}: {5*len(points)} rays, {count} deeper than 8 mm, "
          f"max={1000*deepest:.2f} mm near {np.round(witness,4) if witness is not None else '-'}", flush=True)
    assert count == 0, "the shoulder exposes the interior behind the joint"


def check_chine(meshes):
    """Measure the actual deployed installation against the two original shoulder bevels."""
    grid = hullgrid.HullGrid()
    upper,lower = (grid.points[:,b] for b in (hullgrid.B_E1,hullgrid.B_E2))
    datum = np.array(bpy.data.objects["Repere_Ailes_Tranche"].matrix_world)
    q = np.linspace(wing_bay.BAY_Y[0],wing_bay.BAY_Y[1],241)
    plane = np.column_stack((np.zeros_like(q),q,np.full_like(q,wing_bay.Z))) @ datum[:3,:3].T + datum[:3,3]
    y,z = plane[:,1],plane[:,2]
    top,bottom = (np.interp(y,p[:,1],p[:,2]) for p in (upper,lower))
    assert np.all(z<top) and np.all(z>bottom), "wing datum leaves the original chine"
    for x,mesh in ((wings.ROOT,meshes["Aile_Emplanture_G"]),(wings.TIP,meshes["Aile_Saumon_G"])):
        lead,_ = wings.chord(x)
        target = datum[:3,:3] @ (x,lead,wing_bay.Z) + datum[:3,3]
        assert np.linalg.norm(mesh.world-target,axis=1).min()<0.0002, "leading edge off installation plane"
    mid = len(q)//2
    print(f"CHINE centre Z {z[mid]:.3f} m, upper/lower margins {(top-z).min()*1000:.1f}/"
          f"{(z-bottom).min()*1000:.1f} mm, pitch {np.degrees(np.arctan2(datum[2,1],datum[1,1])):.3f} degrees")


class Jack:
    def __init__(self, meshes, face, end, side):
        suffix = f"_{face}_{end}_{side}"
        self.barrel = meshes["Aile_Verin"+suffix]
        self.rod = meshes["Aile_Tige"+suffix]
        self.door = meshes[f"Aile_Trappe_{'Haute' if face=='Haut' else 'Basse'}_{side}"]
        self.base = self.barrel.matrix[:3,3].copy()
        head = self.rod.matrix[:3,3]
        self.foot = np.linalg.solve(self.door.matrix,np.r_[head,1])
        # The initial centres must be surrounded by an actual fixed pin and a door pin.
        for point, owner in ((self.base,meshes["Aile_Baie_"+side]),(head,self.door)):
            assert owner.tree().find_nearest(point)[3]<0.007, "ram pivot has no supporting pin"
        self.gland = self.barrel.xyz[:,2].max()
        self.tail = self.rod.xyz[:,2].min()
        self.lo,self.hi,self.engagement = np.inf,0,np.inf

    def check(self):
        p,q = self.barrel.matrix[:3,3], self.rod.matrix[:3,3]
        assert np.linalg.norm(p-self.base)<0.0002, "fixed pivot came off its web"
        assert np.linalg.norm(q-(self.door.matrix @ self.foot)[:3])<0.0002, "rod left its door pin"
        length = np.linalg.norm(q-p)
        for m in (self.barrel,self.rod):
            assert np.linalg.norm(np.cross(q-p,m.matrix[:3,2]))<0.0006, "rod is off the barrel axis"
        inside = length+self.tail
        assert 0.022 < inside < self.gland-0.012, "ram bottoms out or pulls out of its gland"
        self.engagement = min(self.engagement,self.gland-inside)
        self.lo,self.hi = min(self.lo,length),max(self.hi,length)


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--step", type=float, default=0.5)
    args.add_argument("--gear", default="down,up,cycle")
    opt = args.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    assert opt.step > 0
    anim.show({})
    meshes = [Mesh(o) for o in bpy.context.scene.objects if o.type == "MESH"]
    fixtures = {"Coque_Principale", "Sas_Habillage", "Cabine_Habillage", "Trappe_Arriere",
                "Train_Principal_G_Jambe", "Train_Principal_D_Jambe", "Tuyere_Conduit_G", "Tuyere_Conduit_D"}
    missing = fixtures - {m.obj.name for m in meshes}
    assert not missing, f"the full ship is required to check wing clearance, missing {sorted(missing)}"
    check_stowage(meshes)
    shutter_fixture = next(m for m in meshes if m.obj.name == "Aile_Baie_G")
    assert all(not shutter_fixture.hits(m) for m in meshes
               if m.obj.name.startswith(("Sas_", "Tuyere_", "Cabine_"))), "shutter pocket crosses an existing fixture"
    samples = closure_rays()
    moving = [m for m in meshes if m.obj.name.startswith("Aile_") and m.obj.animation_data]
    fixed = [m for m in meshes if m not in moving]
    assert len(moving) == 34, f"expected 34 moving rigid meshes, got {len(moving)}"
    objects = {m.obj.name:m for m in meshes}
    jacks = [Jack(objects,face,end,side) for face in ("Haut","Bas") for end in ("Avant","Arriere") for side in ("G","D")]
    tip_g = next(m for m in moving if m.obj.name == "Aile_Saumon_G")
    tip_d = next(m for m in moving if m.obj.name == "Aile_Saumon_D")
    roots = [next(m for m in moving if m.obj.name == f"Aile_Emplanture_{s}") for s in ("G", "D")]
    extent = {}
    first = {}
    length = anim.CLIPS["Ailes"]
    for mode_index, mode in enumerate(opt.gear.split(",")):
        frames = sorted(set(np.arange(0, length, opt.step).tolist()) | {length})
        for f in frames:
            u = f / length
            gear = {"down": 0, "up": 1, "cycle": u}[mode]
            anim.show({"Ailes": u, "Train": gear, "Trappe_Arriere": gear, "Aerofrein": gear})
            for m in meshes:
                m.update()
            for ram in jacks:
                ram.check()
            for i, m in enumerate(moving):
                for other in fixed + moving[i+1:]:
                    overlaps = m.hits(other)
                    if overlaps:
                        pair = (m.obj.name, other.obj.name)
                        point = m.world[m.tris[overlaps[0][0]]].mean(axis=0)
                        if pair not in first:
                            first[pair] = [f, f, np.round(point.astype(float), 4).tolist()]
                        first[pair][1] = f
            assert abs(tip_g.high[0] + tip_d.low[0]) < 0.0001
            for root, tip in zip(roots, (tip_g, tip_d)):
                # The two mesh origins lie on their common pin. Check both ends of its axis.
                for y in (2.55, 4.55):
                    pin = np.array((0, y, 0, 1))
                    assert np.linalg.norm((root.matrix - tip.matrix) @ pin) < 0.0001
                if u <= 0.48:
                    assert tip.matrix[0, 0] < -0.9999
                if u >= 0.77:
                    assert tip.matrix[0, 0] > 0.9999
            if f in (0, length):
                extent[f] = float(max(m.high[0] for m in meshes) - min(m.low[0] for m in meshes))
                if mode_index == 0:
                    for m in moving:
                        if m.obj.name.startswith("Aile_Trappe_"):
                            assert np.allclose(m.obj.matrix_local, np.eye(4), atol=0.00015), "main door outside its seat"
                    for side in ("G", "D"):
                        check_closure(meshes, samples, "stowed" if f == 0 else "flight", side)
                    if f == length:
                        check_chine(objects)
        print(f"WINGS {mode}: {len(frames)} wing poses", flush=True)
    for pair, limits in sorted(first.items()):
        print(f"CONTACT {pair} frames={limits[:2]} first_triangle_centre={limits[2]}")
    print("SPAN metres:", extent, flush=True)
    assert abs(extent[0] - 4.86) < 0.025 and abs(extent[length] - 2 * wings.TIP) < 0.001
    assert not first, f"{len(first)} intersecting mesh pairs"
    for ram in jacks:
        assert ram.hi-ram.lo>0.075
    print("JACKS 8, strokes (mm)",sorted({round((ram.hi-ram.lo)*1000,1) for ram in jacks}),
          "minimum rod engagement (mm)",round(min(ram.engagement for ram in jacks)*1000,1))
    # The scarf and moving rib pass within millimetres of each other at the nose.
    # Test this short rotation at higher resolution than the whole-ship sweep.
    fold_frames = np.arange(46, 74 + 1/32, 1/32)
    for frame in fold_frames:
        anim.show({"Ailes": frame/length})
        for root, tip in zip(roots, (tip_g, tip_d)):
            root.update()
            tip.update()
            assert not root.hits(tip), f"fold contact on {tip.obj.name} at frame {frame}"
    print(f"FOLD {len(fold_frames)} poses at 1/32 frame", flush=True)
    print("WINGS PASS", flush=True)


if __name__ == "__main__":
    main()
