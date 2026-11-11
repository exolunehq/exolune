"""Rank 1 km city windows in a terrain survey: real relief, buildable slopes, a river channel.

A survey is a `MYPLANETENGINE_CITY_PROBE` export, typically `lat lon 1025 20` (20 km).
Prints each window's centre as a probe request for a 513 x 2 m city export.
"""
import argparse
import math
from pathlib import Path

import numpy as np

from layout import Terrain

PLANET_RADIUS_M = 6378000.0


def blur(a, r):
    k = np.ones(2 * r + 1) / (2 * r + 1)
    a = np.apply_along_axis(lambda m: np.convolve(m, k, 'same'), 0, a)
    return np.apply_along_axis(lambda m: np.convolve(m, k, 'same'), 1, a)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('survey', type=Path)
    p.add_argument('--relief', type=float, nargs=2, default=(60, 260), help='Accepted relief range, metres')
    p.add_argument('--count', type=int, default=12)
    a = p.parse_args()
    t = Terrain(a.survey)
    h = t.values.astype('f8')
    gy, gx = np.gradient(h, t.cell)
    slope = np.hypot(gx, gy) * 100
    # A channel lies 3 m below its 200 m surroundings.
    channel = (h - blur(h, max(1, int(100 / t.cell)))) < -3
    w = int(1000 / t.cell)
    half = t.side // 2
    rows = []
    for cy in range(w // 2, t.side - w // 2, w // 4):
        for cx in range(w // 2, t.side - w // 2, w // 4):
            win = np.s_[cy - w // 2:cy + w // 2, cx - w // 2:cx + w // 2]
            s, relief = slope[win], np.ptp(h[win])
            # Stairs climb to 30 %; keep a margin for cliffs and flats for commons.
            buildable, flat, steep = ((s > 3) & (s < 35)).mean(), (s <= 3).mean(), (s >= 45).mean()
            if channel[win].mean() > .01 and a.relief[0] < relief < a.relief[1] and steep < .12:
                x, y = (cx - half) * t.cell, (cy - half) * t.cell
                lat = t.lat + math.degrees(y / PLANET_RADIUS_M)
                lon = t.lon + math.degrees(x / (PLANET_RADIUS_M * math.cos(math.radians(t.lat))))
                rows.append((buildable + .5 * flat, x, y, relief, np.median(s), buildable, steep, lat, lon))
    rows.sort(reverse=True)
    print('   x m     y m  relief  median%  3-35%  >45%  probe request')
    for _, x, y, relief, median, buildable, steep, lat, lon in rows[:a.count]:
        print(f'{x:6.0f} {y:7.0f} {relief:7.0f} {median:8.1f} {buildable:6.2f} {steep:5.2f}  {lat:.6f} {lon:.6f} 513 2')


if __name__ == '__main__':
    main()
