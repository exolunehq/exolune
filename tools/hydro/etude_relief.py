"""Side-by-side terrain variants at several window sizes, for judging an erosion method on images. CPU only.

Run from the repository root: python tools/hydro/etude_relief.py [--sites ...] [--variants ...] [--samples 64]
Writes x64/etude-relief/<site>.jpg (rows: variants, columns: window sizes) and <site>.json (metrics per tile).
A new variant is one function decorated with @variant: f(points, cell_m) -> (height_m, water_depth_m or None[, extra
metrics dict]).
"""
import argparse
import json
from pathlib import Path
import time

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from PIL import Image, ImageDraw, ImageFont
import arbre as tree
import cp
import couloirs as corridor
import ravines as gully
from hydro import N8, components, priority_flood
from verifie_lames import direction

SITES = dict(massif=(-7.138614, 122.604860), chaine_enneigee=(-25.6, -26.94),
             riviere_perchee=(26.692011, -23.292216), riviere_tropicale=(12.855277, 27.915018),
             montagnes_humides=(42.693130, -175.950838),
             # The wet plateau seen from 465 km, its large river (step B's sizing, 2026-11-03).
             plateau_humide=(-6.6132, 125.3059))
SIZES = (40000., 10000., 2500., 600.)
VARIANTS = {}


def variant(f):
    VARIANTS[f.__name__] = f
    return f


def network(f, *args):
    """f(*args) with the network's valleys, as before step A (cp.EROSION_RAVINES off)."""
    saved, cp.EROSION_RAVINES = cp.EROSION_RAVINES, False
    try:
        return f(*args)
    finally:
        cp.EROSION_RAVINES = saved


def step_a(f, *args, **kw):
    """f(*args) at step A, without step B's corridors (cp.EROSION_RIVERS off)."""
    saved, cp.EROSION_RIVERS = cp.EROSION_RIVERS, False
    try:
        return f(*args, **kw)
    finally:
        cp.EROSION_RIVERS = saved


@variant
def sans(points, cell_m):
    # No erosion: the uncut parent. Its only water is the sea.
    d = cp.elevation(cp.Ctx(cell_m), points, extra=True, valleys=False)
    return d['elev'], d['water_depth']


@variant
def actuelle(points, cell_m):
    d = network(cp.elevation, cp.Ctx(cell_m), points, True)
    return d['elev'], d['water_depth']


@variant
def arbre(points, cell_m):
    return tree.relief(points, cell_m)


@variant
def ravines(points, cell_m):
    return gully.relief(points, cell_m)[:3]


@variant
def ravines_moteur(points, cell_m):
    return network(gully.moteur, points, cell_m)


@variant
def ravines_moteur2(points, cell_m):
    # The engine's step A (cp.EROSION_RAVINES): the ravines steered per point inside ReliefDetail, no network.
    d, cells = step_a(gully.counted, cp.elevation, cp.Ctx(cell_m), points, extra=True)
    return d['elev'], d['water_depth'], dict(noise_cells_per_sample=cells / len(points),
                                             gully_rms_m=float(np.sqrt(np.mean(d['ravines'] ** 2))))


@variant
def couloirs(points, cell_m):
    return corridor.relief(points, cell_m)


@variant
def couloirs_moteur(points, cell_m):
    # The engine's step B (cp.EROSION_RIVERS): the corridors per point on step A's ravines, their water; the cost per point,
    # and the drawn channels' dry share as the prototype's.
    ctx = cp.Ctx(cell_m)
    d, cells = gully.counted(cp.elevation, ctx, points, extra=True)
    cost = {f'river_{k}_per_sample': float(v.mean()) for k, v in d['river_cost'].items()}
    n = int(round(np.sqrt(len(points))))
    z, water = d['elev'].reshape(n, n), d['water_depth'].reshape(n, n)
    frame, half = tree.Frame(points.sum(0)), 0.5 * n * cell_m
    xy = frame.plane(cp.river_lines(ctx, points, 0.5 * cell_m))
    xy = xy[(np.abs(xy) < half - cell_m).all(1)]
    col, row = np.floor((xy[:, 0] + half) / cell_m).astype(int), np.floor((half - xy[:, 1]) / cell_m).astype(int)
    ok = (col >= 1) & (col < n - 1) & (row >= 1) & (row < n - 1)
    col, row = col[ok], row[ok]
    sea = (d['elev'].reshape(n, n) < 0.0) & (d['water_level'].reshape(n, n) <= 0.0)
    keep = ~sea[row, col]
    bad = (water <= 0.0) | tree.d8_leaks(z, water > 0.0)
    hits = bad[row[keep], col[keep]]
    return d['elev'], d['water_depth'], dict(noise_cells_per_sample=cells / len(points), **cost,
                                             drawn_km=float(len(hits) * 0.5 * cell_m / 1000.0),
                                             dry_share=float(hits.mean()) if len(hits) else None)


def metrics(z, water):
    detail = z[4:-3, 4:-3] - sliding_window_view(z, (8, 8)).mean((2, 3))
    border = np.ones(z.shape, bool)
    border[1:-1, 1:-1] = False
    fill = priority_flood(z, border) - z
    row = dict(detail_rms_m=float(np.sqrt(np.mean(detail**2))), pits_over_2m=float(np.mean(fill > 2.)),
               pits_over_10cm=float(np.mean(fill > .1)))
    if water is not None:
        wet = water > 0.
        lab, sizes = components(wet, N8)
        i, j = np.nonzero(wet)
        k = lab[i, j]
        extent = np.zeros((2, len(sizes)), int)
        for axis, x in enumerate((i, j)):
            lo, hi = np.full(len(sizes), z.shape[0]), np.zeros(len(sizes), int)
            np.minimum.at(lo, k, x)
            np.maximum.at(hi, k, x)
            extent[axis] = hi - lo + 1
        row.update(wet_share=float(wet.mean()), wet_runs_over_10=int(np.sum(extent.max(0) > 10)),
                   wet_leak_share=float(tree.d8_leaks(z, wet).sum() / max(wet[1:-1, 1:-1].sum(), 1)))
    return row


def shade(z, cell):
    # Lambert shading, sun from the north-west at 45 degrees; rows run north to south, columns west to east.
    north, east = np.gradient(z, cell)
    n = np.stack((-east, north, np.ones_like(z)), -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return np.clip(n @ np.array([-.5, .5, np.sqrt(.5)]), 0., 1.)


def picture(z, water, cell, lo, hi):
    # Gentle hypsometric tint (green, tan, pale grey) under the hillshade; positive water depth in blue.
    t = np.clip((z - lo) / max(hi - lo, 1.), 0., 1.)[..., None]
    tint = np.where(t < .5, [.55, .64, .50] + ([.78, .71, .58] - np.array([.55, .64, .50])) * t * 2.,
                    [.78, .71, .58] + ([.93, .92, .90] - np.array([.78, .71, .58])) * (t * 2. - 1.))
    rgb = np.clip(tint * (.3 + .95 * shade(z, cell)[..., None]), 0., 1.)
    if water is not None:
        a = np.where(water > 0., .6 + .35 * np.clip(water / 10., 0., 1.), 0.)[..., None]
        rgb = rgb + ([.12, .32, .72] - rgb) * a
    return (rgb * 255.).astype(np.uint8)


def label(size):
    return f'{size / 1000:g} km' if size >= 1000. else f'{size:g} m'


def study(site, names, n, out):
    lat, lon = SITES[site]
    c = direction(lat, lon)
    start = time.perf_counter()
    tiles, extra, spent = {v: {} for v in names}, {v: {} for v in names}, dict.fromkeys(names, 0.)
    for size in SIZES:
        p, cell = cp.window(c, size, n), size / n
        for v in names:
            t = time.perf_counter()
            z, water, *more = VARIANTS[v](p, cell)
            spent[v] += time.perf_counter() - t
            tiles[v][size] = (z.reshape(n, n), None if water is None else water.reshape(n, n))
            extra[v][size] = more[0] if more else {}
    seconds = time.perf_counter() - start
    report = dict(site=site, lat=lat, lon=lon, samples=n, seconds=round(seconds, 1),
                  seconds_by_variant={v: round(x, 1) for v, x in spent.items()},
                  tiles={v: {label(s): {**metrics(*tiles[v][s]), **extra[v][s]} for s in SIZES} for v in names})

    side, gap, top = max(n, 256), 4, 22
    sheet = Image.new('RGB', (len(SIZES) * (side + gap) + gap, top + len(names) * (side + gap) + gap), (24, 24, 24))
    draw, font = ImageDraw.Draw(sheet), ImageFont.load_default(14)
    draw.text((gap, 4), f'{site}  {lat:.6f}, {lon:.6f}  seed {cp.PLANET_SEED}  {n} x {n}', fill=(230, 230, 230), font=font)
    for col, size in enumerate(SIZES):
        lo = min(tiles[v][size][0].min() for v in names)
        hi = max(tiles[v][size][0].max() for v in names)
        for row, v in enumerate(names):
            x, y = gap + col * (side + gap), top + gap + row * (side + gap)
            tile = Image.fromarray(picture(*tiles[v][size], size / n, lo, hi)).resize((side, side), Image.NEAREST)
            sheet.paste(tile, (x, y))
            text = f'{v}  {label(size)}'
            draw.rectangle((x, y, x + draw.textlength(text, font) + 8, y + 18), fill=(0, 0, 0))
            draw.text((x + 4, y + 2), text, fill=(255, 255, 255), font=font)
    sheet.save(out / f'{site}.jpg', quality=92)
    (out / f'{site}.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sites', nargs='+', choices=list(SITES), default=list(SITES))
    parser.add_argument('--variants', nargs='+', choices=list(VARIANTS), default=list(VARIANTS))
    parser.add_argument('--samples', type=int, default=256)
    parser.add_argument('--out', default=str(Path(cp._REPO) / 'x64' / 'etude-relief'))
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for site in args.sites:
        r = study(site, args.variants, args.samples, out)
        print(f"{site}: {r['seconds']} s", flush=True)
        for v, row in r['tiles'].items():
            for size, m in row.items():
                print(f'  {v:10s} {size:>6s}  ' + '  '.join(f'{k}={x:.4g}' for k, x in m.items() if x is not None), flush=True)


if __name__ == '__main__':
    main()
