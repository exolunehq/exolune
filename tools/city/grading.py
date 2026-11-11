"""Earthworks under the city: flat pads graded into the planet's relief.

A pad is a rounded rectangle at a height. Around it, the ground may depart from that height by
at most its talus, in metres per metre of distance: a cut uphill, a fill downhill. The bank leaves the pad
level and reaches its slope over ROUND metres; crest and toe are rounded over KNEE metres. Beyond that envelope
the natural ground is untouched, exactly. Pads apply in index order. The engine evaluates the same function in the
relief (CityGrade.hlsli) and for walking (City::Grade), so terrain, its texture, vegetation, walking and the city's
paths share one graded ground. `grading.bin` (CITYPAD2) carries the pads and a 32 x 32 cell index.

Earthworks stay local. On gentle ground a bank keeps 1:2 (TALUS); on steeper ground it is twice as steep as the
ground, up to TALUS_MAX, so it meets the natural ground within about half the pad's depth: `bank(slope)`. A bank
no steeper than its ground would never meet it and would regrade the whole slope.
"""
import math
import struct

import numpy as np

TALUS = .5          # 1:2 slopes, the steepest a planted bank keeps
TALUS_MAX = 2.0     # a retaining cut on a cliff face
KNEE = 1.5          # crest and toe rounding (m)
ROUND = 2.0         # the bank leaves the pad level and reaches its slope over this distance (m)
CELLS = 32          # index cells per side over the 1,024 m land grid
MAX_PADS = 900      # the engine's constant buffers (Planet.hlsli, FlightGround.hlsl)
MAX_INDEX = 6144
WINDOW_M = 60.0     # a pad's earthworks never reach farther than this beyond its edge


def soft_clamp(v, limit):
    """v limited to +/- limit with a C1 quadratic knee of half-width min(KNEE, limit)."""
    v, limit = np.asarray(v, float), np.asarray(limit, float)
    w = np.minimum(KNEE, limit)
    a = np.abs(v)
    t = a - (limit - w)
    knee = (limit - w) + t - t * t / (4 * np.maximum(w, 1e-9))
    out = np.where(a <= limit - w, a, np.where(a >= limit + w, limit, knee))
    return np.sign(v) * out


def bank(slope):
    """The bank slope that keeps a pad's earthworks local on ground of this slope."""
    return float(min(TALUS_MAX, max(TALUS, 2 * slope)))


def envelope(d, talus=TALUS):
    """Largest departure from a pad's height at distance d from its edge."""
    d = np.maximum(np.asarray(d, float), 0)
    return talus * np.where(d < ROUND, d * d / (2 * ROUND), d - ROUND / 2)


def allowance(gap, talus=TALUS):
    """Largest level difference between two pads `gap` apart: the later pad's bank, less its knee."""
    limit = float(envelope(gap, talus))
    return max(0.0, limit - min(KNEE, limit))


def talus_of(p):
    return p[8] if len(p) > 8 else TALUS


def distance(pad, x, y):
    """Signed distance to the pad's rounded rectangle (negative inside)."""
    cx, cy, c, s, a, b, r = pad[:7]
    qx = (x - cx) * c + (y - cy) * s
    qy = -(x - cx) * s + (y - cy) * c
    ex, ey = np.abs(qx) - a + r, np.abs(qy) - b + r
    return np.hypot(np.maximum(ex, 0), np.maximum(ey, 0)) + np.minimum(np.maximum(ex, ey), 0) - r


def pad(cx, cy, yaw, half_a, half_b, height, radius=2.5, talus=TALUS):
    radius = min(radius, half_a, half_b)
    return (float(cx), float(cy), math.cos(yaw), math.sin(yaw), float(half_a), float(half_b), float(radius), float(height),
            float(talus))


def polygon(p):
    """The pad's flat as a shapely polygon."""
    from shapely.affinity import rotate, translate
    from shapely.geometry import box
    cx, cy, c, s, a, b, r = p[:7]
    shape = box(-a + r, -b + r, a - r, b - r).buffer(r, quad_segs=4) if r > 1e-3 else box(-a, -b, a, b)
    return translate(rotate(shape, math.atan2(s, c), origin=(0, 0), use_radians=True), cx, cy)


class Grading:
    """Pads graded into a terrain grid (CITYGRD1 layout: rows north, columns east, centred)."""

    def __init__(self, terrain):
        self.terrain = terrain
        self.pads, self.reach, self.shapes, self.visible = [], [], [], []
        self.arrays = None  # centres, half-diagonals and levels of the pads, for bounds()
        self.natural = terrain.values.astype('f8').copy()
        self.values = self.natural.copy()

    def bounds(self, p, cap):
        """Levels within `cap` of p's level that keep its bank out of every earlier pad's flat:
        at a gap g the bank allows envelope(g), less its knee. Close neighbours share a level.
        A pad farther than the bank its level difference needs cannot constrain it."""
        shape, lo, hi = polygon(p), -1e9, 1e9
        if not self.pads:
            return lo, hi
        if self.arrays is None or len(self.arrays[0]) != len(self.pads):
            a = np.asarray(self.pads)
            self.arrays = (a[:, :2], np.hypot(a[:, 4], a[:, 5]), a[:, 7])
        centres, extents, levels = self.arrays
        reaches = (np.abs(levels - p[7]) + cap + KNEE) / TALUS + ROUND / 2 + 1
        near = np.hypot(centres[:, 0] - p[0], centres[:, 1] - p[1]) <= math.hypot(p[4], p[5]) + extents + reaches
        for k in np.flatnonzero(near):
            q, reach = self.pads[k], reaches[k]
            gap = shape.distance(self.shapes[k])
            if gap > reach:
                continue
            room = allowance(gap, talus_of(p))
            lo, hi = max(lo, q[7] - room), min(hi, q[7] + room)
        return lo, hi

    def window(self, p, margin):
        cx, cy, c, s, a, b, r = p[:7]
        ex, ey = abs(a * c) + abs(b * s) + margin, abs(a * s) + abs(b * c) + margin
        t, half = self.terrain, self.terrain.side // 2
        i0, i1 = max(0, int((cx - ex) / t.cell) + half), min(t.side, int((cx + ex) / t.cell) + half + 2)
        j0, j1 = max(0, int((cy - ey) / t.cell) + half), min(t.side, int((cy + ey) / t.cell) + half + 2)
        return j0, j1, i0, i1

    def graded(self, p):
        """The ground of p's window once p is graded in, the window, how far beyond its edge p moves the ground by
        more than 5 cm, how far it moves it at all, and its largest cut or fill. ValueError when its earthworks run
        to the window's edge: a bank no steeper than its ground."""
        t, half = self.terrain, self.terrain.side // 2
        j0, j1, i0, i1 = self.window(p, WINDOW_M)
        y, x = np.mgrid[j0:j1, i0:i1]
        x, y = (x - half) * t.cell, (y - half) * t.cell
        d = distance(p, x, y)
        g = self.values[j0:j1, i0:i1]
        graded = p[7] + soft_clamp(g - p[7], envelope(d, talus_of(p)))
        moved = np.abs(graded - g)
        visible = moved > .05
        reach = float(d[visible].max()) if visible.any() else 0.0
        if reach > WINDOW_M - 2 * t.cell:
            raise ValueError(f'Earthworks beyond {WINDOW_M:.0f} m at ({p[0]:.0f}, {p[1]:.0f})')
        changed = moved > 1e-6
        return graded, (j0, j1, i0, i1), max(reach, 0.0), (float(d[changed].max()) if changed.any() else 0.0), float(moved.max())

    def local(self, p):
        """How far beyond p's edge its earthworks would show (m), and the largest cut or fill they make (m)."""
        try:
            _, _, reach, _, depth = self.graded(p)
        except ValueError:
            return float('inf'), float('inf')
        return reach, depth

    def add(self, p):
        """Grade one more pad into the current ground; returns its index."""
        if len(self.pads) >= MAX_PADS:
            raise ValueError('Too many earthwork pads')
        t = self.terrain
        graded, (j0, j1, i0, i1), visible, reach, _ = self.graded(p)
        self.visible.append(visible)
        # The pad touches the ground only where its envelope binds: its reach bounds the cell index.
        self.values[j0:j1, i0:i1] = graded
        self.pads.append(p)
        self.shapes.append(polygon(p))
        self.reach.append(max(reach, 0.0) + 2 * t.cell)
        return len(self.pads) - 1

    def exact(self, x, y):
        """The engine's graded height at (x, y), between grid nodes too: the natural relief, then each pad whose reach
        covers the point, in order. The grid's bilinear values smooth a steep bank's crest and toe."""
        t, half = self.terrain, self.terrain.side // 2
        gx, gy = x / t.cell + half, y / t.cell + half
        i, j = int(math.floor(gx)), int(math.floor(gy))
        u, v = gx - i, gy - j
        n = self.natural
        h = (n[j, i] * (1 - u) + n[j, i + 1] * u) * (1 - v) + (n[j + 1, i] * (1 - u) + n[j + 1, i + 1] * u) * v
        if not self.pads:
            return float(h)
        if getattr(self, 'boxes', None) is None or len(self.boxes) != len(self.pads):
            a = np.asarray([p[:7] for p in self.pads])
            ex = np.abs(a[:, 4] * a[:, 2]) + np.abs(a[:, 5] * a[:, 3]) + np.asarray(self.reach)
            ey = np.abs(a[:, 4] * a[:, 3]) + np.abs(a[:, 5] * a[:, 2]) + np.asarray(self.reach)
            self.boxes = np.stack([a[:, 0] - ex, a[:, 1] - ey, a[:, 0] + ex, a[:, 1] + ey], 1)
        b = self.boxes
        for k in np.flatnonzero((b[:, 0] <= x) & (x <= b[:, 2]) & (b[:, 1] <= y) & (y <= b[:, 3])):
            p = self.pads[k]
            h = p[7] + float(soft_clamp(h - p[7], envelope(distance(p, x, y), talus_of(p))))
        return float(h)

    def index(self, origin=(-512.0, -512.0), cell=32.0):
        lists = [[] for _ in range(CELLS * CELLS)]
        for k, (p, reach) in enumerate(zip(self.pads, self.reach)):
            cx, cy, c, s, a, b, r = p[:7]
            ex, ey = abs(a * c) + abs(b * s) + reach, abs(a * s) + abs(b * c) + reach
            for j in range(max(0, int((cy - ey - origin[1]) // cell)), min(CELLS, int((cy + ey - origin[1]) // cell) + 1)):
                for i in range(max(0, int((cx - ex - origin[0]) // cell)), min(CELLS, int((cx + ex - origin[0]) // cell) + 1)):
                    lists[j * CELLS + i].append(k)
        cells, flat = [], []
        for entries in lists:
            cells.append(len(flat) | (len(entries) << 16))
            flat += entries
        if len(flat) > MAX_INDEX:
            raise ValueError(f'Earthwork index too large: {len(flat)}')
        return cells, flat

    def write(self, path, origin=(-512.0, -512.0), cell=32.0):
        cells, flat = self.index(origin, cell)
        with open(path, 'wb') as f:
            f.write(struct.pack('<8s2I6f', b'CITYPAD2', len(self.pads), len(flat), TALUS, KNEE, ROUND, origin[0], origin[1], cell))
            for p in self.pads:
                cx, cy, c, s, a, b, r, level = p[:8]
                f.write(struct.pack('<8f', cx, cy, math.atan2(s, c), talus_of(p), a, b, r, level))
            f.write(struct.pack(f'<{CELLS * CELLS}I', *cells))
            f.write(struct.pack(f'<{len(flat)}H', *flat))
            if len(flat) % 2:
                f.write(b'\0\0')
        return {'pads': len(self.pads), 'index': len(flat), 'talus': TALUS,
                'talus_max': max(map(talus_of, self.pads), default=TALUS), 'knee': KNEE, 'round': ROUND}


def grade_point(pads, x, y, h, cells=None, flat=None, origin=(-512.0, -512.0), cell=32.0):
    """The engine's evaluation at one point: the pads of its cell, in index order."""
    if cells is None:
        order = range(len(pads))
    else:
        i, j = int((x - origin[0]) // cell), int((y - origin[1]) // cell)
        if not (0 <= i < CELLS and 0 <= j < CELLS):
            return h
        packed = cells[j * CELLS + i]
        order = flat[packed & 0xffff:(packed & 0xffff) + (packed >> 16)]
    for k in order:
        p = pads[k]
        h = p[7] + float(soft_clamp(h - p[7], envelope(distance(p, x, y), talus_of(p))))
    return h


if __name__ == '__main__':
    # A 20 % slope with one pad: flat inside, taluses of 1:2 at most, nature untouched beyond reach,
    # and the indexed point evaluation equals the grid.
    class Plane:
        side, cell = 129, 2.0
        def __init__(self):
            y, x = np.mgrid[0:self.side, 0:self.side]
            self.values = (100 + .2 * (y - 64) * self.cell).astype('f4')
    t = Plane()
    g = Grading(t)
    p = pad(0, 0, .3, 9, 6, 100.0)
    g.add(p)
    half = t.side // 2
    inside = g.values[half - 2:half + 3, half - 2:half + 3]
    assert np.allclose(inside, 100.0), 'flat pad'
    dy = np.abs(np.diff(g.values, axis=0)) / t.cell
    assert dy.max() <= TALUS + .02, f'talus steeper than 1:2: {dy.max():.3f}'
    assert np.allclose(g.values[:4], g.natural[:4]) and np.allclose(g.values[-4:], g.natural[-4:]), 'far ground unchanged'
    cells, flat = g.index((-128.0, -128.0), 8.0)
    for x, y in [(4.0, 8.0), (-12.0, -10.0), (20.0, 16.0), (0.0, 30.0)]:
        j, i = int(round(y / t.cell)) + half, int(round(x / t.cell)) + half
        exact = grade_point(g.pads, x, y, float(g.natural[j, i]), cells, flat, (-128.0, -128.0), 8.0)
        assert abs(exact - g.values[j, i]) < 1e-4, (x, y, exact, g.values[j, i])
        assert abs(g.exact(x, y) - g.values[j, i]) < 1e-4, ('exact', x, y)
    # A far, much higher pad is still bounded: its bank needs more than 40 m to come down 28 m.
    lo, hi = g.bounds(pad(0, 70, 0, 5, 5, 128.0), 5.0)
    assert abs(hi - (100.0 + allowance(polygon(pad(0, 70, 0, 5, 5, 128.0)).distance(g.shapes[0])))) < 1e-6 and hi < 128.0, (lo, hi)
    # A 70 % face: a 1:2 bank never meets it; a bank twice as steep closes within about half the pad's depth.
    class Face(Plane):
        def __init__(self):
            y, x = np.mgrid[0:self.side, 0:self.side]
            self.values = (100 + .7 * (y - 64) * self.cell).astype('f4')
    f = Grading(Face())
    steep = pad(0, 0, 0, 8, 6, 100.0, 2.0, bank(.7))
    reach, depth = f.local(steep)
    assert reach < 9 and depth < 6, (reach, depth)
    assert f.local(pad(0, 0, 0, 8, 6, 100.0, 2.0))[0] == float('inf'), 'a 1:2 bank regrades the whole face'
    f.add(steep)
    print(f'grading self-check passed: max talus {dy.max():.3f}, reach {g.reach[0]:.1f} m, steep face reach {reach:.1f} m')
