"""One place of the quality bench seen from many views: its crops of one material at one height, the p95 of their gap and
repeat per view and pooled. A p95 that rests on one view of one place is not a regression yet (docs/principes.md): run this
for the build and for main alike, and compare the pooled values.

python tools/banc_qualite_vues.py <exe> <out folder> --lat -26.501266 --lon 166.745418 [--height 12] [--material rock]
    [--offsets 0,40] [--analyse-only]

The views: headings 0 to 330 by 30 degrees, at the place and at each offset (m) east of it; the bench's camera, sun and
engine settings (banc_qualite.py). Images are kept in the out folder; --analyse-only reads them again.
"""
import argparse, json, math, os, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banc_qualite as bq

p = argparse.ArgumentParser()
p.add_argument('exe')
p.add_argument('out')
p.add_argument('--lat', type=float, required=True)
p.add_argument('--lon', type=float, required=True)
p.add_argument('--height', type=float, default=12.0)
p.add_argument('--material', default='rock', choices=bq.MATERIALS)
p.add_argument('--offsets', default='0,40')
p.add_argument('--analyse-only', action='store_true')
a = p.parse_args()
os.makedirs(a.out, exist_ok=True)
views = []
for dx in (float(x) for x in a.offsets.split(',')):
    for heading in range(0, 360, 30):
        lon = a.lon + math.degrees(dx / (bq.R * math.cos(math.radians(a.lat))))
        views.append(('v%d_%d' % (int(dx), heading), a.lat, lon, float(heading)))

if not a.analyse_only:
    jobs = []
    for name, lat, lon, heading in views:
        common = (a.height, lat, lon, bq.PITCH, heading)
        jobs.append((os.path.join(a.out, name + '_c.bmp'), '-', *common))
        jobs += [(os.path.join(a.out, '%s_%s.bmp' % (name, m)), m, *common) for m in bq.VIEWS + ['sea', 'rockall']]
    sun = '%.2f %.2f' % (max(min(a.lat - 20.0, 60.0), -60.0), a.lon + 35.0)  # as banc_qualite.py: the sun some 50 degrees up
    # Each heading and offset streams new ground: about 8 s a view, against the bench's 1.3 at one place.
    bq.run(os.path.abspath(a.exe), jobs, os.path.join(a.out, 'jobs.txt'), sun, per_view=20)

pooled, lines = {'gap': [], 'repeat': []}, []
for name, lat, lon, heading in views:
    colour = cv2.imread(os.path.join(a.out, name + '_c.bmp'))
    masks = {m: cv2.imread(os.path.join(a.out, '%s_%s.bmp' % (name, m))) for m in bq.VIEWS + ['sea', 'rockall']}
    if colour is None or any(v is None for v in masks.values()):
        lines.append('%-8s missing' % name)
        continue
    lum = bq.luminance(colour)
    ground = bq.ground_mask(masks['rock'])
    weights = bq.visible({m: bq.weight(v) for m, v in masks.items()})
    weights['rock'] = weights['rockall'] * (1.0 - weights['snow'])  # a wall as it is seen, as banc_qualite.py takes it
    gaps, repeats = [], []
    for y in range(bq.TOP, lum.shape[0] - bq.TILE + 1, bq.TILE):
        for x in range(0, lum.shape[1] - bq.TILE + 1, bq.TILE):
            if ground[y:y + bq.TILE, x:x + bq.TILE].mean() < 0.98 or weights['sea'][y:y + bq.TILE, x:x + bq.TILE].mean() > 0.05:
                continue
            shares = {m: float(weights[m][y:y + bq.TILE, x:x + bq.TILE].mean()) for m in bq.MATERIALS}
            if max(shares, key=shares.get) != a.material or shares[a.material] < bq.CROP_SHARE:
                continue
            tile = lum[y:y + bq.TILE, x:x + bq.TILE]
            e = bq.octaves(tile)
            gaps.append(float(max(0.5 * (e[i - 1] + e[i + 1]) - e[i] for i in range(1, 4))))
            repeats.append(bq.repeat(tile))
    pooled['gap'] += gaps
    pooled['repeat'] += repeats
    lines.append('%-8s %2d crops' % (name, len(gaps)) + ('  gap p95 %.2f  repeat p95 %.3f' % (
        np.percentile(gaps, 95), np.percentile(repeats, 95)) if len(gaps) >= 5 else ''))
result = {'material': a.material, 'height': a.height, 'n': len(pooled['gap']), 'views': lines}
if pooled['gap']:
    result.update(gap_p95=float(np.percentile(pooled['gap'], 95)), repeat_p95=float(np.percentile(pooled['repeat'], 95)))
json.dump(result, open(os.path.join(a.out, 'vues.json'), 'w'), indent=1)
print('\n'.join(lines))
if pooled['gap']:
    print('pooled %s %g m: %d crops, gap p95 %.2f, repeat p95 %.3f' % (a.material, a.height, result['n'],
                                                                      result['gap_p95'], result['repeat_p95']))
