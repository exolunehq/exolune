"""Cut two hinged elevons from the approved outer wing skins in their original folding frames."""
import struct

import numpy as np
import wing_bay
import wings


def transformed(matrix, points):
    return points @ matrix[:3, :3].T + matrix[:3, 3]


def cap_strip(rings, outward, slot):
    """Close a cut between the pressure and suction sides with correctly wound metal faces."""
    vertices = []
    for (a, b), (c, d) in zip(rings, rings[1:]):
        for corners in ((a, c, d), (a, d, b)):
            p, q, r = corners
            normal = np.cross(q-p, r-p)
            area = np.linalg.norm(normal)
            if area < 1e-10:
                continue
            normal /= area
            if normal @ outward < 0:
                q, r = r, q
                normal = -normal
            tangent = (q-p) / np.linalg.norm(q-p)
            for point in (p, q, r):
                vertices.append((*point, *normal, *tangent, 1, point[1], point[2], 0, 0, slot))
    return vertices


def add_controls(grid, vertex, indices, draws, materials, slots):
    _, datum = wing_bay.installation(grid)
    # These are existing skin rings and a chord column in wings.panel. The
    # fixed inboard rib carries the folding pin and the fixed tip carries the light.
    rings = np.linspace(wings.HINGE + wings.HINGE_GAP, wings.TIP, 15)
    root, tip = rings[1], rings[-2]
    hinge = .5 * (1-np.cos(np.pi * 52/84))
    faces = indices.reshape(-1, 3)
    result = faces.copy()
    enamel = np.zeros(len(faces), dtype=bool)
    for first, count, material in draws:
        if materials[material] in ('NAV_Email_Blanc', 'NAV_Email_Sarcelle'):
            enamel[first//3:(first+count)//3] = True
    pieces = [vertex]
    caps = []
    records = bytearray(b'AER1')
    for number, (sign, side) in enumerate(((1,'G'), (-1,'D')), 1):
        parent = slots['Aile_Saumon_' + side]
        child = max(slots.values()) + number
        assert child <= 96
        bind = (datum @ wings.wing_pose(sign, True, 0) @ np.linalg.inv(wings.wing_pose(sign, True, 1))
                @ np.diag([sign, 1, 1, 1]))
        select = np.flatnonzero(enamel & (vertex[faces[:, 0], 14] == parent))
        ids, compact = np.unique(faces[select], return_inverse=True)
        triangles = compact.reshape(-1, 3)
        points = transformed(np.linalg.inv(bind), vertex[ids, :3])
        x, y, z = points.T
        lead, aft = wings.chord(x)
        f = (y-lead)/(aft-lead)
        cx, cf = x[triangles].mean(1), f[triangles].mean(1)
        take = (cx > root) & (cx < tip) & (cf > hinge)
        moving, remap = np.unique(triangles[take], return_inverse=True)
        assert len(moving) > 400 and np.all(x[moving] > root-.0001) and np.all(f[moving] > hinge-.0001)
        result[select[take]] = remap.reshape(-1, 3) + sum(map(len, pieces))
        moved = points.copy()
        # Mill the end clearances and the hinge reveal into the moving panel.
        moved[:, 0] = (x-(root+tip)/2) * (1-.010/(tip-root)) + (root+tip)/2
        new_lead, new_aft = wings.chord(moved[:, 0])
        moved[:, 1] = new_lead + f*(new_aft-new_lead) + .019*(1-f)/(1-hinge)
        mobile = vertex[ids[moving]].copy()
        mobile[:, :3] = transformed(bind, moved[moving])
        mobile[:, 14] = child
        pieces.append(mobile)

        y0, y1 = wings.chord(np.array([root, tip]))
        pin = np.column_stack(([root, tip], y0+hinge*(y1-y0)+.025, [wing_bay.Z]*2))
        start, end = transformed(bind, pin)
        axis = sign * (end-start)/np.linalg.norm(end-start)  # positive raises either trailing edge in flight
        records.extend(struct.pack('<2I6f', child, parent, *start, *axis))
        for coordinate, value, along, outward in (
                (x, root, f, (-1,0,0)), (x, tip, f, (1,0,0)), (f, hinge, x, (0,-1,0))):
            rim = moving[np.abs(coordinate[moving]-value) < .00003]
            rim = rim[np.argsort(along[rim])]
            sections = np.split(rim, np.flatnonzero(np.diff(along[rim]) > .00001)+1)
            pairs = []
            for sample in sections:
                pairs.append([sample[np.argmin(z[sample])], sample[np.argmax(z[sample])]])
            if len(pairs)<10 or np.any(np.ptp(z[pairs], axis=1) <= .0001):
                raise ValueError(f'Open rib on {side} elevon at station {value:.3f}')
            direction = bind[:3, :3] @ outward
            caps.extend(cap_strip(vertex[ids[pairs], :3], -direction, parent))
            caps.extend(cap_strip(transformed(bind, moved[pairs]), direction, child))
    # A yaw command opens one of the existing split-fin leaves with its own live strut.
    for side in ('G', 'D'):
        records.extend(struct.pack('<3I', *(slots[name+'_'+side] for name in
                                            ('Aerofrein', 'Aerofrein_Verin', 'Aerofrein_Tige'))))
    first_cap = sum(map(len, pieces))
    pieces.append(np.asarray(caps, dtype='<f4'))
    draws.append([len(indices), len(caps), materials.index('NAV_Metal_Sombre')])
    all_indices = np.r_[result.ravel(), np.arange(first_cap, first_cap+len(caps))]
    used, dense = np.unique(all_indices, return_inverse=True)
    return np.concatenate(pieces)[used], dense.astype('<u4'), records
