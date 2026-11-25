"""Fit auxiliary exhaust sockets to the V9 skin and export their visible mouth axes."""
import math
import struct

from mathutils.bvhtree import BVHTree
import numpy as np

# One port-side station per mirrored pair, nose towards -Y. The first pair brakes.
# The forward and aft groups each have dorsal, ventral and lateral outlets.
# Station Y, section parameter, open radius, discharge direction in ship axes.
PORTS = (
    (-3.38, .585, .112, (.44, -.88, -.17)),
    (-2.76, .091, .049, (.23, -.08, .97)),
    (-2.86, .717, .051, (.34, -.08, -.94)),
    (-2.18, .534, .046, (.98, -.16, -.09)),
    (4.70, .323, .049, (.39, .09, .92)),
    (4.82, .695, .051, (.30, .08, -.95)),
    (5.78, .483, .046, (.98, .17, .01)),
)


def fixed_skin(vertex, indices, draws, materials):
    paint = {'NAV_Email_Blanc', 'NAV_Email_Ventre', 'NAV_Email_Sarcelle'}
    triangles = np.concatenate([indices[first:first+count] for first, count, mat in draws
                                if materials[mat] in paint]).reshape(-1, 3)
    triangles = triangles[np.all(vertex[triangles, 14] == 0, axis=1) & np.all(vertex[triangles, 0] > 0, axis=1)]
    used, local = np.unique(triangles.ravel(), return_inverse=True)
    return BVHTree.FromPolygons(vertex[used, :3].tolist(), local.reshape(-1, 3).tolist(), all_triangles=True)


def add_ports(grid, vertex, indices, draws, materials):
    skin = fixed_skin(vertex, indices, draws, materials)
    sides = 32
    phi = np.arange(sides) * (2 * math.pi / sides)
    vertices = []
    faces = {'NAV_Metal_Titane': [], 'NAV_Tuyere_Conduit': []}
    records = []

    for y, t, radius, direction in PORTS:
        centre = grid.hull.eval(np.array([grid.maps.s_of_y(y)]), np.array([t]))[0]
        axis = np.array(direction) / np.linalg.norm(direction)
        u = np.cross(axis, (0, 1, 0))
        u /= np.linalg.norm(u)
        v = np.cross(axis, u)
        radial = np.cos(phi)[:, None] * u + np.sin(phi)[:, None] * v
        # Project each edge onto the actual skin. The flared foot follows its curvature and rake.
        def skin_ring(scale):
            ring = []
            for line in centre + scale * radius * radial:
                hit, _, _, _ = skin.ray_cast(line + .42 * axis, -axis, .84)
                if hit is None:
                    raise ValueError(f'Exhaust crosses a hull opening at station {y}')
                ring.append(tuple(hit))
            return np.array(ring)

        foot = skin_ring(1.36)
        seat = skin_ring(.68)
        lip = max((skin_ring(1.06) - centre) @ axis) + .015
        mouth = centre + lip * axis
        records.append(struct.pack('<8f', *mouth, radius, *axis, 0))
        rings = [foot - .005 * axis, skin_ring(1.29) + .006 * axis,
                 mouth + 1.08 * radius * radial - .005 * axis,
                 mouth + radius * radial, seat + .005 * axis]
        for sign in (1, -1):
            mirror = np.array((sign, 1, 1))
            def add_band(outer, inner, material):
                offset = len(vertex) + len(vertices)
                edge = np.roll(outer, -1, axis=0) - np.roll(outer, 1, axis=0)
                tangent = edge / np.linalg.norm(edge, axis=1)[:, None]
                normal = np.cross(tangent, inner - outer)
                normal /= np.linalg.norm(normal, axis=1)[:, None]
                for ring in (outer, inner):
                    for p, n, tan in zip(ring, normal, tangent):
                        vertices.append((*(p*mirror), *(n*mirror), *(tan*mirror), sign, 0, 0, 0, 0, 0))
                for k in range(sides):
                    j = (k + 1) % sides
                    for tri in ((k, j, k+sides), (j, j+sides, k+sides)):
                        faces[material].extend(offset+i for i in (tri if sign==1 else tri[::-1]))
            for k in range(4):
                add_band(rings[k], rings[k+1], 'NAV_Metal_Titane' if k<3 else 'NAV_Tuyere_Conduit')
            # A dark throat behind the rolled lip. It meets the hull even at the shallowest edge.
            base = len(vertex) + len(vertices)
            floor = np.vstack((rings[-1].mean(axis=0), rings[-1]))
            for p in floor:
                vertices.append((*(p*mirror), *(axis*mirror), *(u*mirror), sign, 0, 0, 0, 0, 0))
            for k in range(sides):
                tri = (base, base+1+k, base+1+(k+1)%sides)
                faces['NAV_Tuyere_Conduit'].extend(tri if sign==1 else tri[::-1])

    added = []
    first = len(indices)
    for name, group in faces.items():
        draws.append([first, len(group), materials.index(name)])
        first += len(group)
        added.extend(group)
    vertex = np.concatenate((vertex, np.asarray(vertices, dtype='<f4')))
    indices = np.concatenate((indices, np.asarray(added, dtype='<u4')))
    return vertex, indices, struct.pack('<4sI', b'RCS1', len(records)) + b''.join(records)
