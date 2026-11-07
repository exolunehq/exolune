"""The 'couloirs' variant of etude_relief.py: the ravines relief, plus corridors for the large rivers of the level 0.
CPU prototype in the window's tangent plane; the engine is untouched.

- Rivers: the level-0 links whose discharge reaches Q_MIN. Their curves are erosion_valleys' quadratic pieces, except
  at a confluence: the largest inflow keeps its piece; every other one ends on it at a junction, arriving at Howard's
  angle (cos = main slope / tributary slope, clipped to JUNCTION) where the main stage has fallen to the tributary's.
  Outlets continue EXTEND past their node at their level, to reach the detailed coast.
- Course: the curve displaced sideways by a fractal offset m(s) of 3D noise read at the nearest curve point, octaves
  from MEANDER[0] down to MEANDER[1] channel widths (Leopold and Wolman 1960), amplitude a share of each wavelength,
  less on steep ground (SINUOUS). The coarse octaves bend the valley, the fine ones (below SPLIT finest wavelengths)
  only the channel inside its floodplain. Distance to the displaced course: |l - m| / sqrt(1 + m'^2), l the lateral
  distance, m' the offset's slope along the curve.
- Width: erosion_river_size's, +-WIDTH_NOISE[1] along the course. Depth: erosion_river_size's.
- Stage z: the level-0 stage, capped downstream by the lowest relief met upstream (filtered at HC_CELL) plus FILL, its
  drops then spread upstream at S_KNICK (condition). Above each head a dry valley rises at S_HEAD into the relief.
- Relief: h = z_b + (h_ravines - z_b) g(d), z_b the stage plus a bank of BANK depths, g = smoothstep from the
  floodplain's half-width F (channel, bank and fine meanders) to the corridor's D = F + wall width, the wall width the
  relief's height above the stage (filtered relief at the course less stage, plus a quarter of the relief amplitude)
  over a wall slope (WALL). The floodplain keeps FLOODPLAIN of the relief finer than 2 HP_CELL. Where h_ravines is below
  z_b this raises the ground towards the stage (floodplain fill, only where a river runs, never into the sea).
- Combination: H = h_ravines + max fill - max carve over the corridors (continuous: each vanishes at its corridor's edge);
  then each channel is cut, h = min(H, channel_i), the channel's banks continuing at STEEP_BANK beyond its edge so a
  channel crossing another corridor stays a trench. Water: the stage over the channel bed, where the box-filtered
  channel exists.
"""
import math

import numpy as np

import cp
import ravines
from arbre import Frame, d8_leaks

Q_MIN = 10.0                       # m3/s: a link carries a river from this discharge; full width from 1.5 Q_MIN
CURVE = 32                         # straight pieces per curve (prototype; the engine would solve the nearest point)
EXTEND = 15000.0                   # m: outlets continue at their level past the 25 km coast, to the detailed one
EXTEND_HEAD, S_HEAD = 12000.0, 0.15  # m, slope: above a head the dry valley floor rises over 12 km at 15 %
JUNCTION = (30.0, 75.0)            # degrees: a tributary's arrival angle bounds
MEANDER = (10000.0, 12.0, 0.1, 0.05)  # coarsest wavelength (m); finest wavelength in channel widths; amplitude per
                                   # wavelength of the two finest octaves, of the coarser ones
SINUOUS = (0.02, 0.15, 0.3)        # ground slope (25 km forms) from which sinuosity falls, to which; share kept when steep
OFFSET_MAX = 2500.0                # m: the coarse offset's bound (tanh), far inside the 25 km spacing of the links
SPLIT = 6.0                        # octaves below 6 finest wavelengths are the floodplain's; coarser ones bend the valley
WIDTH_NOISE = (3000.0, 0.3)        # wavelength (m), +- share of the width's variation along the course
BANK = 0.5                         # bank height above the stage, in channel depths
WALL = (0.2, 0.5, 300.0, 6000.0)   # wall slope on plains, in mountains; wall width bounds (m)
STEEP_BANK = 3.0                   # slope of a channel's banks beyond its edge
NETWORK = 80000.0                  # m: the river network read around a site, the same for all its windows
HC_CELL = 500.0                    # m: the relief that caps the stage is the no-erosion one filtered at this cell
FILL = 15.0                        # m: a stage may stand this much above that relief: the floodplain fill's bound
S_KNICK = 0.03                     # a drop of the stage spreads upstream at most this steep
HP_CELL, FLOODPLAIN = 200.0, 0.2   # the floodplain keeps 0.2 of the relief finer than ~400 m (cell 200 m filtered out)
SEED = 40                          # cp._rseed(SEED) + octave: meanders; + 16: width


def bez(a, b, c, t):
    """The quadratic Bezier of controls a, b, c (scalars or points) at the parameters t."""
    t = t[:, None] if np.ndim(a) else t
    return (1.0 - t) ** 2 * a + 2.0 * (1.0 - t) * t * b + t * t * c


def network(frame, radius):
    """The river curves of the level 0 within radius (m) of the frame's centre, keyed ('main', node), ('outlet', node),
    ('tributary', node, inflow): dicts of xy (K+1, 2), z, lq (log2 of discharge), and their links: up (the key of the
    curve whose end they continue), down (the key of the curve they flow on into; a tributary: into, at vertex j)."""
    words, n = cp.erosion_map()
    face, x = cp._elocate(frame.c[None], n)
    m = int(radius / (2.0 * cp.R / n)) + 3
    o = np.stack(np.meshgrid(np.arange(-m, m + 1), np.arange(-m, m + 1)), -1).reshape(-1, 2)
    cells = np.unique(cp._ecell(np.repeat(face, len(o)), np.floor(x).astype(np.int64) + o, n))
    node = lambda c: frame.plane(cp._enode(np.atleast_1d(c), n).astype(np.float64))[0]
    read = lambda c: [v[0] for v in cp._eread(words, np.atleast_1d(c))]
    t = np.linspace(0.0, 1.0, CURVE + 1)
    curves = {}
    for r in cells:
        r = int(r)
        lv, _, q, _, bits = read(r)
        b, outlet = node(r), (bits & (cp._SEA | cp._LAKE)) != 0
        rr = None
        if (bits & cp._HAS_RECEIVER) and not outlet:
            rr = int(cp._eneighbour(np.array([r]), np.array([bits & 7]), n)[0])
            l2, _, q2, _, _ = read(rr)
            c, zc, qc = 0.5 * (b + node(rr)), 0.5 * (lv + l2), math.sqrt(q * q2)
        else:
            c, zc, qc = b, lv, q
        ins = []
        for k in range(8):
            if (bits >> (4 + k)) & 1:
                u = int(cp._eneighbour(np.array([r]), np.array([k]), n)[0])
                lu, _, qu, _, _ = read(u)
                ins.append(dict(u=u, a=0.5 * (node(u) + b), z=0.5 * (lu + lv), q=math.sqrt(qu * q),
                                into=b - node(u), qu=qu))
        if not ins and not outlet:
            ins.append(dict(u=None, a=b, z=lv, q=q, into=c - b, qu=q))
        if not ins or max(qc, max(i["q"] for i in ins)) < Q_MIN:
            continue
        main = max(ins, key=lambda i: i["qu"])
        lq = bez(math.log2(main["q"]), math.log2(q), math.log2(qc), t)
        curves["main", r] = dict(xy=bez(main["a"], b, c, t), z=bez(main["z"], lv, zc, t), lq=lq, kind="main", level=lv, node=r, receiver=rr, up=("main", main["u"]),
                                 down=("outlet", r) if outlet else None)
        if outlet:  # past the node, at its level, along its last direction
            d = (b - main["a"]) / max(np.linalg.norm(b - main["a"]), 1e-9)
            curves["outlet", r] = dict(xy=b + EXTEND * t[:, None] * d, z=np.full_like(t, lv), lq=np.full_like(t, math.log2(q)), kind="outlet", level=lv, up=("main", r), down=None)
        for i in ins:
            if i is not main and i["q"] >= Q_MIN:
                curves["tributary", r, i["u"]] = dict(main=curves["main", r], start=i, kind="tributary", level=lv,
                                                      up=("main", i["u"]), into=("main", r))
    for key, c in curves.items():  # where each main curve's water goes on
        if c["kind"] == "main" and c["down"] is None and c["receiver"] is not None:
            rr, r = c["receiver"], c["node"]
            if ("tributary", rr, r) in curves:
                c["down"] = ("tributary", rr, r)
            elif ("main", rr) in curves and curves["main", rr]["up"] == ("main", r):
                c["down"] = ("main", rr)
    return curves


def condition(curves, frame):
    """The stage z1 of every curve: the level-0 stage, never more than FILL above the relief (filtered at HC_CELL)
    upstream of it along the network, then knickpoints spread upstream at S_KNICK. Non-increasing downstream and
    continuous through every join and junction."""
    for c in curves.values():
        Hc = cp.elevation(cp.Ctx(HC_CELL), frame.sphere(c["xy"]), valleys=False)
        limit = np.maximum(Hc, 0.0) - BANK * c["depth"] + FILL
        c["cap"], c["junctions"], c["Hc"] = limit, [], Hc
    for c in curves.values():
        if c["kind"] == "tributary":
            curves[c["into"]]["junctions"].append(c)
    order = sorted(curves.values(), key=lambda c: (-c["level"], {"tributary": 0, "main": 1, "outlet": 2}[c["kind"]]))
    for c in order:  # 1. downstream, the lowest limit met so far
        up = curves.get(c["up"])
        cap = c["cap"].copy()
        if up is not None:
            cap[0] = min(cap[0], up["cap"][-1])
        for j in c["junctions"]:
            cap[j["j"]] = min(cap[j["j"]], j["cap"][-1])
        c["cap"] = np.minimum.accumulate(cap)
        c["z1"] = np.minimum(c["z"], c["cap"])
    for c in reversed(order):  # 2. upstream, no drop steeper than S_KNICK
        if c["kind"] == "tributary":
            end = curves[c["into"]]["z1"][c["j"]]
        else:
            down = curves.get(c["down"]) if c["down"] else None
            end = down["z1"][0] if down is not None else np.inf
        z = c["z1"]
        z[-1] = min(z[-1], end)
        ds = np.linalg.norm(np.diff(c["xy"], axis=0), axis=1)
        for i in range(CURVE - 1, -1, -1):
            z[i] = min(z[i], z[i + 1] + S_KNICK * ds[i])


def prepare(c, frame):
    """A curve's attributes per vertex: tangent, normal, discharge, width, depth, sinuosity, floodplain and corridor."""
    xy = c["xy"]
    d = np.gradient(xy, axis=0)
    c["T"] = d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-12)
    c["N"] = np.stack((-c["T"][:, 1], c["T"][:, 0]), 1)  # left normal
    q = 2.0 ** c["lq"]
    c["W0"], c["depth"] = cp.erosion_river_size(q)
    c["live"] = cp._smooth(Q_MIN, 1.5 * Q_MIN, q)
    tf = cp.tectonic_fields(frame.sphere(xy))
    slope, amplitude = np.linalg.norm(tf["forms_gradient"], axis=1) / (1000.0 * cp.R_KM), tf[0][:, 1]
    c["sinuous"] = 1.0 - (1.0 - SINUOUS[2]) * cp._smooth(SINUOUS[0], SINUOUS[1], slope)
    c["finest"] = MEANDER[1] * 2.0 * c["W0"]
    amp = amplitudes(c["finest"], c["sinuous"])
    c["fine_max"] = 2.0 * (amp * (1.0 - split(c["finest"]))).sum(1)
    c["F"] = 2.0 * c["W0"] + c["fine_max"]
    c["amplitude"] = amplitude
    return c


def corridor(c):
    """The corridor's half-width D: the floodplain, then a wall as wide as the relief's height above the stage (the
    filtered relief at the course less the stage, plus a quarter of the relief amplitude) over a wall slope from plains to
    mountains."""
    mountains = cp._smooth(300.0, 1200.0, c["amplitude"])
    above = np.maximum(c["Hc"] - c["z1"], 0.0) + 0.25 * c["amplitude"]
    c["D"] = c["F"] + np.clip(above / (WALL[0] + (WALL[1] - WALL[0]) * mountains), WALL[2], WALL[3])
    c["reach"] = float((c["D"].max() + OFFSET_MAX + c["fine_max"].max()))


WAVES = MEANDER[0] / 2.0 ** np.arange(10)


def amplitudes(finest, sinuous):
    """Meander amplitude (m) per vertex and octave (n, 10): a share of the wavelength, octaves below the finest faded."""
    r = WAVES[None] / finest[:, None]
    share = MEANDER[3] + (MEANDER[2] - MEANDER[3]) * (1.0 - cp._smooth(2.0, 4.0, r))
    return share * WAVES[None] * cp._smooth(0.7, 1.4, r) * sinuous[:, None]


def split(finest):
    """Per octave, the share bending the valley (coarse), the rest bending only the channel (fine)."""
    return cp._smooth(SPLIT / 1.4, SPLIT * 1.4, WAVES[None] / finest[:, None])


def meander(frame, p, T, finest, sinuous):
    """Coarse and fine offsets (m) at the curve points p (n, 2) of tangent T, and their slopes along the curve."""
    p3, T3 = frame.sphere(p), T[:, :1] * frame.e + T[:, 1:] * frame.n
    amp, coarse = amplitudes(finest, sinuous), split(finest)
    out = np.zeros((4, len(p)))
    for o, wave in enumerate(WAVES):
        if not (amp[:, o] > 0.0).any():
            continue
        c, q = cp._lattice(p3, cp.R / wave, o)
        v, g = cp.gradient_noise_d(c, q, cp._rseed(SEED) + o)
        v, dv = v / cp.SIGMA, (g * T3).sum(1) / (cp.SIGMA * wave)
        out += np.stack((coarse[:, o] * v, coarse[:, o] * dv, (1 - coarse[:, o]) * v, (1 - coarse[:, o]) * dv)) * amp[:, o]
    mc, dmc, mf, dmf = out
    fine_max = 2.0 * (amp * (1.0 - coarse)).sum(1)
    k = np.maximum(fine_max, 1e-9)
    return (OFFSET_MAX * np.tanh(mc / OFFSET_MAX), dmc / np.cosh(mc / OFFSET_MAX) ** 2, k * np.tanh(mf / k),
            dmf / np.cosh(mf / k) ** 2)


def width_noise(frame, p):
    c, q = cp._lattice(frame.sphere(p), cp.R / WIDTH_NOISE[0], 0)
    return 1.0 + WIDTH_NOISE[1] * np.clip(cp.gradient_noise_d(c, q, cp._rseed(SEED) + 16)[0] / (2.0 * cp.SIGMA), -1.0, 1.0)


def tributary(c, frame):
    """A minor inflow re-routed: from its start (continuing its upstream piece) to the main curve's displaced course,
    where the main stage has fallen to its own, arriving at Howard's angle."""
    main, s = c["main"], c["start"]
    t = np.linspace(0.0, 1.0, CURVE + 1)
    j = int(np.argmax((t >= 0.5) & (main["z"] <= s["z"]))) if ((t >= 0.5) & (main["z"] <= s["z"])).any() else CURVE
    J, TJ, zJ = main["xy"][j], main["T"][j], main["z"][j]
    mc, _, mf, _ = meander(frame, J[None], TJ[None], main["finest"][j:j + 1], main["sinuous"][j:j + 1])
    J = J + (mc[0] + mf[0]) * main["N"][j]
    a, into = s["a"], s["into"] / max(np.linalg.norm(s["into"]), 1e-9)
    span = max(np.linalg.norm(J - a), 1.0)
    slope_main = abs(main["z"][max(j - 1, 0)] - main["z"][min(j + 1, CURVE)]) / max(
        np.linalg.norm(main["xy"][max(j - 1, 0)] - main["xy"][min(j + 1, CURVE)]), 1.0)
    cosine = np.clip(slope_main / max((s["z"] - zJ) / span, 1e-9), 0.0, 1.0)
    theta = math.radians(np.clip(math.degrees(math.acos(cosine)), *JUNCTION))
    NL = np.array([-TJ[1], TJ[0]])
    side = 1.0 if np.dot(a - J, NL) > 0.0 else -1.0
    arrive = math.cos(theta) * TJ - side * math.sin(theta) * NL  # heading into J, from the tributary's side
    # The control: where the start's heading meets the arrival line, if ahead of both; else the chord's middle.
    m = np.array([into, arrive]).T
    ok = abs(np.linalg.det(m)) > 1e-6
    lam = np.linalg.solve(m, J - a) if ok else np.array([-1.0, -1.0])
    ctrl = a + lam[0] * into if ok and 0.0 < lam[0] < 1.5 * span and 0.0 < lam[1] < 1.5 * span else 0.5 * (a + J)
    return dict(c, xy=bez(a, ctrl, J, t), z=zJ + (s["z"] - zJ) * (1.0 - t) ** 2, lq=np.full_like(t, math.log2(s["q"])), j=j, taper=1.0 - cp._smooth(0.6, 1.0, t))


def cut(d, w, depth, r):
    """Box mean over +-r of the channel depth profile depth (1 - (d / w)^2)^2, |d| < w (erosion_river_cut's)."""
    lo, hi = np.clip((d - r) / w, -1.0, 1.0), np.clip((d + r) / w, -1.0, 1.0)
    primitive = lambda x: x * (1.0 + x * x * (-2.0 / 3.0 + x * x * 0.2))
    return depth * w * (primitive(hi) - primitive(lo)) / (2.0 * r)


def evaluate(c, frame, xy, hr, fine, cell):
    """One curve's corridor at the points xy (in reach): (fill, carve, channel surface, stage, wet, channel distance,
    meander slope)."""
    A, B = c["xy"][:-1], c["xy"][1:]
    e = B - A
    L2 = np.maximum((e * e).sum(1), 1e-12)
    rel = xy[:, None, :] - A[None]
    u = np.clip((rel * e[None]).sum(2) / L2[None], 0.0, 1.0)
    dist = np.linalg.norm(rel - u[..., None] * e[None], axis=2)
    j = dist.argmin(1)
    t = u[np.arange(len(xy)), j]
    at = lambda v: v[j] + (v[np.minimum(j + 1, CURVE)] - v[j]) * (t if np.ndim(v) == 1 else t[:, None])
    P = A[j] + t[:, None] * e[j]
    T = at(c["T"])
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    N = np.stack((-T[:, 1], T[:, 0]), 1)
    x = xy - P
    lat, along = (x * N).sum(1), (x * T).sum(1)
    finest, sinuous = at(c["finest"]), at(c["sinuous"])
    taper = at(c["taper"]) if "taper" in c else 1.0
    mc, dmc, mf, dmf = (v * taper for v in meander(frame, P, T, finest, sinuous))
    dv = np.hypot(along, (lat - mc) / np.sqrt(1.0 + dmc ** 2))
    slope = dmc + dmf
    dc = np.hypot(along, (lat - mc - mf) / np.sqrt(1.0 + slope ** 2))
    z, live, depth = at(c["z1"]), at(c["live"]), at(c["depth"])
    W = at(c["W0"]) * width_noise(frame, P) * live
    depth = depth * live
    zb = z + BANK * depth
    g = cp._smooth(at(c["F"]), at(c["D"]), dv)
    sea = cp._smooth(-50.0, 0.0, hr)
    r = cell
    edge = W + r
    bank = np.maximum(W, r)
    # The floodplain keeps a share of the fine relief (below HP_CELL), never below the stage, faded in past the banks.
    rough = np.maximum(FLOODPLAIN * fine, -0.8 * BANK * depth) * cp._smooth(edge + bank, edge + 3.0 * bank, dc)
    # Raised ground (fill) only where a river runs; a valley (carve) wherever the curve goes, even where the river is
    # narrowing to its head or dry above it: the channel is never cut below a shallower valley.
    S = zb + rough + (hr - zb - rough) * g
    S = hr + (S - hr) * np.where(S > hr, live * sea, 1.0)
    inside = np.where(dc < edge, cut(dc, np.maximum(W, 1e-3), depth, r), 0.0)
    channel = z + BANK * depth * cp._smooth(edge, edge + bank, dc) - inside + STEEP_BANK * np.maximum(dc - edge - bank, 0.0)
    channel = np.where(live > 0.0, channel, np.inf)
    return np.maximum(S - hr, 0.0), np.maximum(hr - S, 0.0), channel, z, (dc < edge) & (live > 0.0), dc, slope


_SITES = {}


def site(frame):
    """The site's river curves, prepared and conditioned once for all its windows."""
    site_key = tuple(np.round(frame.c, 12))
    if site_key not in _SITES:
        curves = network(frame, NETWORK)
        for c in curves.values():
            if c["kind"] != "tributary":
                prepare(c, frame)
        for k, c in curves.items():
            if c["kind"] == "tributary":
                curves[k] = prepare(tributary(c, frame), frame)
        condition(curves, frame)
        for key, c in list(curves.items()):  # above each head, its valley rises at S_HEAD, dry, into the relief
            if c["up"] not in curves:
                t = np.linspace(-1.0, 0.0, CURVE + 1)
                xy = c["xy"][0] + EXTEND_HEAD * t[:, None] * c["T"][0]
                head = dict(c, xy=xy, z=c["z1"][0] - S_HEAD * EXTEND_HEAD * t, kind="head", up=None, down=key)
                head.pop("taper", None)
                for k in ("lq", "W0", "depth", "sinuous", "finest", "fine_max", "F", "amplitude", "Hc"):
                    head[k] = np.full(CURVE + 1, c[k][0])
                head["T"], head["N"] = np.tile(c["T"][0], (CURVE + 1, 1)), np.tile(c["N"][0], (CURVE + 1, 1))
                head["live"], head["z1"] = np.zeros(CURVE + 1), head["z"]
                curves["head", key] = head
        for c in curves.values():
            corridor(c)
        _SITES[site_key] = list(curves.values())
    return _SITES[site_key]


def relief(points, cell):
    """The variant: (height, water depth, metrics) for a cp.window grid."""
    hr, sea_depth, extra, d = ravines.relief(points, cell, 2.0 * HP_CELL)
    n = int(round(math.sqrt(len(points))))
    frame, half = Frame(points.sum(0)), 0.5 * n * cell
    xy = frame.plane(points)
    curves = site(frame)
    fine = d["elev"] - cp.elevation(cp.Ctx(HP_CELL), points, valleys=False) + d["gullies_fine"]
    fill, carve, channel = np.zeros(len(xy)), np.zeros(len(xy)), np.full(len(xy), np.inf)
    level, tested, octaves = np.full(len(xy), -np.inf), np.zeros(len(xy)), np.zeros(len(xy))
    steep = []
    for c in curves:
        lo, hi = c["xy"].min(0) - c["reach"], c["xy"].max(0) + c["reach"]
        if (lo > half).any() or (hi < -half).any():
            continue
        sel = np.flatnonzero(((xy >= lo) & (xy <= hi)).all(1))
        if not len(sel):
            continue
        tested[sel] += 1
        octaves[sel] += (amplitudes(c["finest"], c["sinuous"]) > 0.0).any(0).sum() + 1
        f, k, ch, z, wet, dc, slope = evaluate(c, frame, xy[sel], hr[sel], fine[sel], cell)
        fill[sel], carve[sel] = np.maximum(fill[sel], f), np.maximum(carve[sel], k)
        channel[sel] = np.minimum(channel[sel], ch)
        level[sel] = np.where(wet, np.maximum(level[sel], z), level[sel])
        steep.append(np.abs(slope[dc < 3.0 * c["W0"].max()]))
    H = hr + fill - carve
    h = np.minimum(H, channel)
    river = np.where(np.isfinite(level), np.maximum(level - h, 0.0), 0.0)
    water = np.maximum(river, np.maximum(-h, 0.0) * (sea_depth > 0.0))
    steep = np.concatenate(steep + [np.zeros(1)])
    extra = dict(extra, courses=len(curves), curves_tested_per_sample=float(tested.mean()),
                 meander_octaves_per_sample=float(octaves.mean()), fill_share=float(np.mean(fill > 1.0)),
                 fill_max_m=float(fill.max()), carve_max_m=float(carve.max()),
                 meander_slope_max=float(steep.max()), meander_slope_over_1=float(np.mean(steep > 1.0)))
    extra.update(dry(curves, frame, h.reshape(n, n), water.reshape(n, n), sea_depth.reshape(n, n) > 0.0, cell))
    return h, water, extra


def dry(curves, frame, z, water, sea, cell):
    """Drawn water: the displaced channel lines of the live courses, sampled every half cell inside the window off the
    sea. Its dry share: samples on a dry cell or on a wet cell whose D8 steepest descent leaves the water."""
    n = z.shape[0]
    half = 0.5 * n * cell
    bad = (water <= 0.0) | d8_leaks(z, water > 0.0)
    hits = []
    for c in curves:
        length = np.linalg.norm(np.diff(c["xy"], axis=0), axis=1).sum()
        s = np.linspace(0.0, CURVE, max(int(length / (0.5 * cell)), 2))
        j, t = np.minimum(s.astype(int), CURVE - 1), s - np.minimum(s.astype(int), CURVE - 1)
        at = lambda v: v[j] + (v[j + 1] - v[j]) * (t if np.ndim(v) == 1 else t[:, None])
        live = at(c["live"]) > 0.0
        P, T = at(c["xy"]), at(c["T"])
        inside = live & (np.abs(P) < half - cell).all(1)
        if not inside.any():
            continue
        P, T = P[inside], T[inside] / np.linalg.norm(T[inside], axis=1, keepdims=True)
        taper = at(c["taper"])[inside] if "taper" in c else 1.0
        mc, _, mf, _ = meander(frame, P, T, at(c["finest"])[inside], at(c["sinuous"])[inside])
        Q = P + ((mc + mf) * taper)[:, None] * np.stack((-T[:, 1], T[:, 0]), 1)
        col, row = np.floor((Q[:, 0] + half) / cell).astype(int), np.floor((half - Q[:, 1]) / cell).astype(int)
        ok = (col >= 1) & (col < n - 1) & (row >= 1) & (row < n - 1)
        ok[ok] &= ~sea[row[ok], col[ok]]
        hits.append(bad[row[ok], col[ok]])
    hits = np.concatenate(hits) if hits else np.zeros(0, bool)
    return dict(drawn_km=float(len(hits) * 0.5 * cell / 1000.0), dry_share=float(hits.mean()) if len(hits) else None)


if __name__ == "__main__":
    # On one site: every stage runs downhill and meets the next curve's; the displaced-course distance
    # |l - m| / sqrt(1 + m'^2) matches the exact distance to the densely sampled course, near the channels.
    from verifie_lames import direction
    frame = Frame(direction(-25.6, -26.94))
    curves = site(frame)
    for c in curves:
        assert np.all(np.diff(c["z1"]) <= 1e-9), c["kind"]
    rng = np.random.default_rng(1)
    errors, widths = [], []
    for c in [c for c in curves if c["kind"] == "main" and c["live"].min() > 0.0][:12]:
        s = np.linspace(0.0, CURVE, 20001)
        j = np.minimum(s.astype(int), CURVE - 1)
        t = s - j
        at = lambda v: v[j] + (v[j + 1] - v[j]) * (t if np.ndim(v) == 1 else t[:, None])
        P, T = at(c["xy"]), at(c["T"])
        T /= np.linalg.norm(T, axis=1, keepdims=True)
        mc, _, mf, _ = meander(frame, P, T, at(c["finest"]), at(c["sinuous"]))
        line = P + (mc + mf)[:, None] * np.stack((-T[:, 1], T[:, 0]), 1)
        k = rng.integers(2000, 18000, 300)
        W = at(c["W0"])[k]
        x = line[k] + (rng.uniform(-3.0, 3.0, 300) * W)[:, None] * np.stack((-T[k, 1], T[k, 0]), 1)
        exact = np.linalg.norm(x[:, None] - line[None], axis=2).min(1)
        dc = evaluate(c, frame, x, np.full(300, 1e4), np.zeros(300), 1.0)[5]
        errors.append(np.abs(dc - exact))
        widths.append(W)
    e, w = np.concatenate(errors), np.concatenate(widths)
    print("distance error / half-width: median %.3f, p95 %.3f, max %.3f" % tuple(np.percentile(e / w, [50, 95, 100])))
    assert np.median(e / w) < 0.1
    print("ok")
