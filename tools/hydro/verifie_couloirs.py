"""Self-check of step B's corridors (cp.py, mirror of Erosion.hlsli's ErosionRivers; docs/spec-erosion.md, step B).

Run from the repository root, after the engine has written its conditioned level 0: python tools/hydro/verifie_couloirs.py
[--sheets x64/etude-relief-taille-apres] [--sheets-before x64/etude-relief-taille-avant] [--before <an EXOEROS3 cache>]
- the conditioned stage (Erosion::Condition): non-increasing downstream, drops at most S_KNICK, and every drawn course at
  the five sites below its cap where it carries water, the relief it crosses plus the fill, sampled as ErosionStages.hlsl
  does;
- the sizes: the share of links carrying a course and water, the rivers' spacing, the valleys' widths by discharge, the
  stage's lowering; the widths must grow with the discharge and spread at each discharge;
- the re-routed tributaries: where their junction moved with the conditioning (sampled on the level 0's, drawn on the
  conditioned stages);
- the distance to the meandered course |l - m| / sqrt(1 + m'^2) against the exact distance to the densely sampled course;
- continuity across corridor edges, confluences and link joins: along lines through them, the corridors' change to the
  ground and the water depth are Lipschitz, their largest step shrinking with the sampling step;
- the drawn water against the engine before this sizing, dry share and wet leaks from etude_relief.py's sheets: the
  prototype's sheets no longer apply, its corridors are not sized;
- the pre-erosion form bit-identical with step B on or off; the old network path, both switches off, bit-identical on the
  new cache and on the previous one (--before).
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np

import cp
from verifie_lames import direction

SITES = dict(massif=(-7.138614, 122.604860), chaine_enneigee=(-25.6, -26.94),
             riviere_perchee=(26.692011, -23.292216), riviere_tropicale=(12.855277, 27.915018),
             montagnes_humides=(42.693130, -175.950838))
# The wet plateau seen from 465 km (-8.28, 124.60): its large river at its centre, for continuity.
SITES_RIVERS = dict(SITES, plateau_humide=(-6.6132, 125.3059))
FILL, S_KNICK = 15.0, 0.03  # Erosion.cpp's kRiverFill, kKnickSlope


def switched(f, *args, ravines=True, rivers=True, **kw):
    saved = cp.EROSION_RAVINES, cp.EROSION_RIVERS
    cp.EROSION_RAVINES, cp.EROSION_RIVERS = ravines, rivers
    try:
        return f(*args, **kw)
    finally:
        cp.EROSION_RAVINES, cp.EROSION_RIVERS = saved


def links():
    """Per cell: its receiver (or itself at an outlet), the midpoint discharge's two bytes summed, land."""
    words, n = cp.erosion_map()
    bits = words[:, 1].astype(np.int64)
    code = (bits >> 16) & 255
    has = (bits & cp._HAS_RECEIVER) != 0
    outlet = (bits & (cp._SEA | cp._LAKE)) != 0
    down = np.full(len(bits), -1)
    down[has] = cp._eneighbour(np.flatnonzero(has), bits[has] & 7, n)
    down = np.where(outlet, np.arange(len(bits)), down)
    twice = code + code[np.maximum(down, 0)]
    return down, np.where(down >= 0, twice, -1), (bits & cp._SEA) == 0


def stages():
    words, n = cp.erosion_map()
    z, wall, sinuous, floor = cp.erosion_courses()
    bits = words[:, 1].astype(np.int64)
    has = (bits & cp._HAS_RECEIVER) != 0
    c = np.flatnonzero(has)
    r = cp._eneighbour(c, bits[c] & 7, n)
    drop = z[c] - z[r]
    length = np.linalg.norm(cp._enode(c, n).astype(np.float64) - cp._enode(r, n).astype(np.float64), axis=1) * cp.R
    level = (words[:, 0] & 0xFFFF).astype(np.float64) * 0.25 - 8192.0
    down, twice, land = links()
    # The stored stage's quarter metre at both ends, and the engine's link lengths, measured in float on the GPU to 1 m.
    slack = 0.25 + S_KNICK * 1.0
    print(f"stage: {int((drop < 0).sum())} rises downstream over {len(c)} links (min drop {drop.min():.2f} m); "
          f"{int((drop > S_KNICK * length + slack).sum())} drops steeper than S_KNICK, largest excess "
          f"{(drop - S_KNICK * length).max():.2f} m")
    for name, q in (("course", cp.RIVER_Q[0]), ("river", cp.RIVER_Q[1])):
        river = land & (twice >= 16.0 * (math.log2(q) + 8.0))
        d = (level - z)[river]
        print(f"  lowered below the level 0 on {name} cells (from {q:g} m3/s): {np.mean(d > 0.25):.1%}, p50 "
              f"{np.median(d):.0f} m, p95 {np.percentile(d, 95):.0f} m, max {d.max():.0f} m; walls p50 "
              f"{np.median(wall[river]):.0f} m, sinuosity p50 {np.median(sinuous[river]):.2f}")
    assert (drop >= 0).all()
    assert (drop <= S_KNICK * length + slack).all()


def courses_near(site, km, ctx):
    words, n = cp.erosion_map()
    p = cp.window(direction(*SITES_RIVERS[site]), km * 1000.0, 8)
    face, x = cp._elocate(p, n)
    lo, hi = np.floor(x.min(0)).astype(int) - 1, np.floor(x.max(0)).astype(int) + 2
    cells = sorted({int(cp._ecell(np.array([f]), np.array([[i, j]]), n)[0]) for f in np.unique(face)
                    for i in range(lo[0], hi[0]) for j in range(lo[1], hi[1])})
    out = []
    for c in cells:
        ks, v = cp.river_courses(ctx, c)
        out += [(c, kind, k, v) for kind, k in ks]
    return out


def caps():
    """Every course drawn at the sites, below the relief it crosses plus the fill (ErosionStages.hlsl's sampling)."""
    ctx = cp.Ctx(cp.RIVER_CAP_CELL)
    t = np.linspace(0.0, 1.0, cp.RIVER_CAP_SAMPLES)
    excess, moved = [], []
    for site in SITES_RIVERS:
        for c, kind, k, v in courses_near(site, 60.0, ctx):
            if kind in ("head", "outlet"):
                continue
            T = cp._course_tangent(k, t)
            T /= np.linalg.norm(T, axis=1, keepdims=True)
            m, q = cp._meander(ctx, k, t, T)
            if k["taper"]:
                m = m * (1.0 - cp._smooth(0.6, 1.0, t))
            along = T - (T * q).sum(1, keepdims=True) * q
            along /= np.linalg.norm(along, axis=1, keepdims=True)
            at = q + ((m[0] + m[2]) / cp.R)[:, None] * np.cross(along, q)
            h = cp.elevation(ctx, at / np.linalg.norm(at, axis=1, keepdims=True), valleys=False)
            q = 2.0 ** cp._bez(k["lq"], t)
            wet = q > cp.RIVER_Q[1]
            if not wet.any():
                continue
            cap = np.maximum(h, 0.0) - cp.RIVER_BANK * cp.erosion_river_size(q)[1]
            excess.append(cp._bez(k["stage"], t)[wet] - cap[wet].min() - FILL)
            if not isinstance(kind, str):
                # The junction sampled on the level 0's stages, drawn on the conditioned ones.
                words, n = cp.erosion_map()
                level = (words[:, 0] & 0xFFFF).astype(np.float64) * 0.25 - 8192.0
                saved = cp.erosion_courses
                z, wall, sinuous, floor = saved()
                cp.erosion_courses = lambda seed=None: (level, wall, sinuous, floor)
                try:
                    u = cp._river_node(int(cp._eneighbour(np.array([c]), np.array([kind]), n)[0]))
                    zero = cp._connector(ctx, cp._node_courses(c), u)
                finally:
                    cp.erosion_courses = saved
                moved.append(abs(zero["junction"] - k["junction"]))
    e, moved = np.concatenate(excess), np.array(moved)
    print(f"cap: {len(e)} wet samples on the sites' courses, {np.mean(e > 0.5):.2%} above the cap + fill, max {e.max():.1f} m")
    print(f"  re-routed tributaries: {len(moved)}, junction moved by the conditioning on {np.mean(moved > 0.01):.0%} "
          f"(p95 {np.percentile(moved, 95) if len(moved) else 0:.2f} of the main course)")


def sizes():
    """The share of land links carrying a course and water, the rivers' spacing (land area over their length), and the
    valley's floor and corridor widths at the nodes of the wet courses, without the valley's noise, which widens or
    narrows them by up to twice along the course, by discharge."""
    words, n = cp.erosion_map()
    z, wall, sinuous, floor = cp.erosion_courses()
    down, twice, land = links()
    nodes = cp._enode(np.arange(len(words)), n).astype(np.float64)
    length = np.where(down >= 0, np.linalg.norm(nodes[np.maximum(down, 0)] - nodes, axis=1) * cp.R_KM, 0.0)
    area = land.sum() * 4.0 * math.pi * cp.R_KM ** 2 / len(words)
    lq = ((words[:, 1] >> 16) & 255).astype(np.float64) / 8.0 - 8.0
    for name, q in (("course", cp.RIVER_Q[0]), ("river", cp.RIVER_Q[1])):
        m = land & (twice >= 16.0 * (math.log2(q) + 8.0))
        print(f"links carrying a {name} (from {q:g} m3/s): {m.sum() / land.sum():.1%} of land cells, spacing "
              f"{area / length[m].sum():.0f} km")
    wet = land & (twice >= 16.0 * (math.log2(cp.RIVER_Q[1]) + 8.0))
    q = 2.0 ** lq[wet]
    F = np.maximum(2.0 * cp.erosion_river_size(q)[0], np.minimum(cp._valley_floor(q, floor[wet]), cp.RIVER_FLOOR[2]))
    D = np.minimum(F + wall[wet], cp.RIVER_REACH)
    print("valley widths at the wet courses' nodes (m), floor 2F and corridor 2D, p10 / p50 / p90:")
    medians = []
    for lo, hi in ((100, 300), (300, 1000), (1000, 3000), (3000, 1e9)):
        k = (q >= lo) & (q < hi)
        if k.sum() < 20:
            continue
        f, d = np.percentile(2.0 * F[k], [10, 50, 90]), np.percentile(2.0 * D[k], [10, 50, 90])
        medians.append(f[1])
        print(f"  Q {lo:g}-{hi:g} m3/s, {k.sum()} nodes: floor {f[0]:.0f} / {f[1]:.0f} / {f[2]:.0f}, corridor "
              f"{d[0]:.0f} / {d[1]:.0f} / {d[2]:.0f}")
        # Rivers alike would share one width: at each discharge the widths spread by the rock and the relief.
        assert f[2] > 1.5 * f[0] and d[2] > 1.5 * d[0]
    assert all(np.diff(medians) > 0)


def distance():
    """dc against the exact distance to the densely sampled meandered course, near the channels."""
    ctx = cp.Ctx(5.0)
    rng = np.random.default_rng(1)
    errors, widths = [], []
    for c, kind, k, v in courses_near("plateau_humide", 60.0, ctx)[:60]:
        if kind != "main" or cp.erosion_river_size(2.0 ** k["lq"].min())[0] < 2.0:
            continue
        s = np.linspace(0.0, 1.0, 20001)
        T = cp._course_tangent(k, s)
        T /= np.linalg.norm(T, axis=1, keepdims=True)
        m, q = cp._meander(ctx, k, s, T)
        along = T - (T * q).sum(1, keepdims=True) * q
        along /= np.linalg.norm(along, axis=1, keepdims=True)
        left = np.cross(along, q)
        line = q + ((m[0] + m[2]) / cp.R)[:, None] * left
        pick = rng.integers(2000, 18000, 200)
        W = cp.erosion_river_size(2.0 ** cp._bez(k["lq"], s[pick]))[0]
        x = line[pick] + (rng.uniform(-3.0, 3.0, 200) * W / cp.R)[:, None] * left[pick]
        x /= np.linalg.norm(x, axis=1, keepdims=True)
        exact = np.array([np.linalg.norm(line[max(i - 400, 0):i + 400] - xi, axis=1).min() for i, xi in zip(pick, x)]) * cp.R
        dc = corridor_distance(ctx, k, x)
        errors.append(np.abs(dc - exact))
        widths.append(W)
    e, w = np.concatenate(errors), np.concatenate(widths)
    print("distance error / half-width: median %.3f, p95 %.3f, max %.3f" % tuple(np.percentile(e / w, [50, 95, 100])))
    assert np.median(e / w) < 0.1


def corridor_distance(ctx, k, P):
    """dc as _corridor computes it, at the unit points P."""
    proj = lambda x: (x[None] - P) - ((x[None] - P) * P).sum(1, keepdims=True) * P
    a, b, c = (proj(x) for x in k["xyz"])
    _, t, nearest = cp._curve(a, b, c)
    T = (b - a) + t[:, None] * ((c - b) - (b - a))
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    N = np.cross(T, P)
    lat, along = -(nearest * N).sum(1) * cp.R, -(nearest * T).sum(1) * cp.R
    m, _ = cp._meander(ctx, k, t, T)
    slope = np.clip(m[1] + m[3], -1.0, 1.0)
    return np.hypot(along, (lat - m[0] - m[2]) / np.sqrt(1.0 + slope ** 2))


def continuity(sites=None):
    """Along lines through corridor edges, confluences and joins: the corridors' change and the water depth Lipschitz."""
    ctx = cp.Ctx(4.0)
    rng = np.random.default_rng(3)
    worst = {}
    for site in sites or ("massif", "montagnes_humides", "plateau_humide"):
        cs = courses_near(site, 40.0, ctx)
        lines = []
        for c, kind, k, v in cs:
            if kind == "main":
                # across the corridor at its middle, and along the river through its downstream join
                # Centre the witnesses on the actual displaced course. A long valley bend can leave a 300 m
                # line through the undisplaced graph completely dry, silently skipping the water join.
                at_t = np.array([0.5, 1.0])
                tangent = cp._course_tangent(k, at_t)
                tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
                bends, points = cp._meander(ctx, k, at_t, tangent)
                tangent -= (tangent*points).sum(1, keepdims=True)*points
                tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
                left = np.cross(tangent, points)
                points += ((bends[0]+bends[2])/cp.R)[:, None]*left
                points /= np.linalg.norm(points, axis=1, keepdims=True)
                mid, end = points
                N = left[0]
                lines.append(("edge", mid, N, 8000.0, c))
                Te = tangent[1] + np.clip(bends[1, 1]+bends[3, 1], -1., 1.)*left[1]
                lines.append(("join", end, Te / np.linalg.norm(Te), 300.0, c))
            elif not isinstance(kind, str):
                J = k["xyz"][2]
                lines.append(("confluence", J, np.cross(J, rng.normal(size=3)), 300.0, c))
        for name, at, d, span, node in lines[:40]:
            at = at / np.linalg.norm(at)
            d = d - (d @ at) * at
            d /= np.linalg.norm(d)
            jumps = []
            peaks = [[], []]
            # The change across a corridor at steps of 10 and 2.5 m; the water, and everything through a join or a
            # confluence, over 300 m either side at 0.25 and 0.06 m: fine enough for the narrowest channels' banks, so
            # that a step's largest change measures a slope, or a jump.
            for count in (4800, 19200):
                s = np.linspace(-span, span, count // 3 if name == "edge" else count)
                if name == "edge":
                    s = np.concatenate((s, np.linspace(-300.0, 300.0, count)))
                P = at[None] + (s / cp.R)[:, None] * d[None]
                P /= np.linalg.norm(P, axis=1, keepdims=True)
                B = cp.elevation(ctx, P, extra=True)
                # Once a footprint is fully inside water, its mean depth must be the actual stage/bed gap.
                # Separate coverage may represent an unresolved river below mean land, never paint a resolved
                # channel over uncut dry ground (which also lets vegetation occupy the visible water).
                resolved = (B["water_coverage"] > 1.0 - 1e-6) & (B["water_level"] > 0.0)
                gap = np.maximum(B["water_level"] - B["elev"], 0.0)
                assert np.max(np.abs(B["water_depth"][resolved] - gap[resolved]), initial=0.0) < 2e-5, (name, "resolved water has no matching bed")
                A = switched(cp.elevation, ctx, P, rivers=False)
                change, water = B["elev"] - A, B["water_depth"]
                # Under the sea or a lake, where an outlet runs on at its level, the highest stage's cut may pass from one
                # course to another: a step of the drowned floor, out of the check.
                dry = np.minimum(B["elev"] >= 0.0, B["lake_level"] <= B["elev"])
                dry = dry[1:] & dry[:-1]
                wide, near = (slice(0, len(s) - count), slice(len(s) - count, None)) if name == "edge" else (slice(None),) * 2
                step = lambda x, k: np.abs(np.diff(x[k]))[dry[k][: len(x[k]) - 1]].max(initial=0.0)
                jumps.append((step(change, wide), step(water, near)))
                for field, (values, part) in enumerate(((change, wide), (water, near))):
                    positions = s[part]
                    delta = np.where(dry[part][:len(positions)-1], np.abs(np.diff(values[part])), 0.)
                    peak = int(np.argmax(delta))
                    peaks[field].append((.5*(positions[peak]+positions[peak+1]), positions[peak+1]-positions[peak]))
            # Lipschitz: a quarter of the step, about a quarter of the largest change; a jump stays.
            ratio = [j1 / j0 if j0 > 0.01 else 0.0 for j0, j1 in zip(*jumps)]
            # The broad 10 m edge grid can miss a shallow head narrower than its spacing. Resolve both detected peaks
            # locally before diagnosing a discontinuity. Keep the same fourfold refinement and the same 0.6 limit.
            for field in range(2):
                if ratio[field] < .6:
                    continue
                local = []
                for divider in (16, 64):
                    largest = 0.
                    for centre, spacing in peaks[field]:
                        x = np.linspace(centre-4.*spacing, centre+4.*spacing, 8*divider+1)
                        P = at[None]+(x/cp.R)[:, None]*d[None]
                        P /= np.linalg.norm(P, axis=1, keepdims=True)
                        b = cp.elevation(ctx, P, extra=True)
                        values = b['water_depth'] if field else b['elev']-switched(cp.elevation, ctx, P, rivers=False)
                        dry = (b['elev'] >= 0.) & (b['lake_level'] <= b['elev'])
                        largest = max(largest, np.abs(np.diff(values))[dry[1:] & dry[:-1]].max(initial=0.))
                    local.append(largest)
                ratio[field] = local[1]/local[0] if local[0] > .01 else 0.
                print(f"continuity local refinement: {site}, node {node}, {name}, field {field}, steps {local}, ratio {ratio[field]:.3f}", flush=True)
            if max(ratio) >= .6:
                print(f"continuity witness: {site}, node {node}, {name}, steps {jumps}, ratios {ratio}", flush=True)
            worst.setdefault(name, []).append((ratio, jumps[1]))
    for name, r in worst.items():
        ratios = np.array([x for x, _ in r])
        print(f"continuity, {name}: {len(r)} lines, largest change at a quarter step over at the step (Lipschitz 0.25, a "
              f"jump 1): ground p50 {np.median(ratios[:, 0]):.2f}, max {ratios[:, 0].max():.2f}; water p50 "
              f"{np.median(ratios[:, 1]):.2f}, max {ratios[:, 1].max():.2f}, largest step {max(j[1] for _, j in r):.3f} m")
        assert ratios[:, 0].max() < 0.6
        # Overlapping channels blend their stages: no step at confluences or joins either.
        assert ratios[:, 1].max() < 0.6


def sheets(folder, before):
    """The drawn water before and after this sizing, from etude_relief.py's sheets of the engine's step B: no dry gap and
    no leaking water where there was none."""
    rows = []
    for f in sorted(Path(folder).glob("*.json")):
        g = Path(before) / f.name
        if not g.exists():
            continue
        a, b = (json.loads(x.read_text(encoding="utf-8"))["tiles"]["couloirs_moteur"] for x in (g, f))
        for size in ("40 km", "10 km", "2.5 km", "600 m"):
            rows.append((f.stem, size, a[size].get("dry_share"), b[size].get("dry_share"), a[size]["wet_leak_share"],
                         b[size]["wet_leak_share"], a[size]["wet_share"], b[size]["wet_share"], a[size]["pits_over_2m"],
                         b[size]["pits_over_2m"]))
    print("water: site, window, dry share before / after, wet leaks before / after, wet share before / after, pits over "
          "2 m before / after")
    fmt = lambda x: "-" if x is None else f"{x:.3f}"
    for row in rows:
        print("  %-18s %-6s  %s / %s   %s / %s   %s / %s   %s / %s" % (row[0], row[1], *map(fmt, row[2:])))
        # Fewer rivers drawn: the dry share and the leaks of what is still drawn stay within 0.02 of before, or lower.
        assert row[3] is None or row[3] <= max(row[2] or 0.0, 0.0) + 0.02, row
        assert row[5] <= row[4] + 0.02, row


def identity(before):
    """The pre-erosion form with step B on or off; the old network path, both switches off, on the new and old caches."""
    p = np.concatenate([cp.window(direction(*s), 20000.0, 24) for s in SITES.values()])
    for cell in (50.0, 5.0):
        ctx = cp.Ctx(cell)
        a = switched(cp.elevation, ctx, p, valleys=False, rivers=True)
        b = switched(cp.elevation, ctx, p, valleys=False, rivers=False)
        assert np.array_equal(a, b)
    print("pre-erosion form: bit-identical with step B on or off")
    if before is None:
        return
    ctx = cp.Ctx(20.0)
    new = switched(cp.elevation, ctx, p, extra=True, ravines=False, rivers=False)
    saved = cp.EROSION_CACHE, dict(cp._erosion), dict(cp._basins)
    try:
        cp.EROSION_CACHE = before
        cp._erosion.clear(), cp._basins.clear()
        old = switched(cp.elevation, ctx, p, extra=True, ravines=False, rivers=False)
    finally:
        cp.EROSION_CACHE = saved[0]
        cp._erosion.clear(), cp._basins.clear()
        cp._erosion.update(saved[1]), cp._basins.update(saved[2])
    for key in ("elev", "water_depth"):
        assert np.array_equal(new[key], old[key]), key
    words_new, _ = cp.erosion_map()
    print("old network path, both switches off: bit-identical on the new cache and on " + Path(before).name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheets", default=None, help="Optional saved sheets; these do not evaluate the current code")
    parser.add_argument("--sheets-before", default=None)
    parser.add_argument("--before", default=None)
    parser.add_argument("--continuity-site", action="append", choices=("massif", "montagnes_humides", "plateau_humide"),
                        help="Run only continuity on selected regions, retaining the full sampling and assertions")
    args = parser.parse_args()
    if args.continuity_site:
        continuity(args.continuity_site)
        print("ok")
        return
    if bool(args.sheets) != bool(args.sheets_before):
        parser.error("--sheets and --sheets-before must be supplied together")
    stages()
    sizes()
    caps()
    distance()
    continuity()
    if args.sheets:
        sheets(args.sheets, args.sheets_before)
    identity(args.before)
    print("ok")


if __name__ == "__main__":
    main()
