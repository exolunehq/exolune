"""Prepare static, functional CINE inspection views. No benchmark or quality score."""
from pathlib import Path
import math, json
import numpy as np

root = Path(__file__).resolve().parents[2]
out = root/'artifacts'/'navigateur-jeu-2026-11-03'
out.mkdir(parents=True, exist_ok=True)
views = [
    ('foret', -11.039991, 49.783625, 65, 40, (-11, -12, 5), '-10 60'),
    ('ocean', -20.47, -75.45, 12, 160, (13, -12, 5), '-50.47 -75.45'),
    ('montagne', 38.1445, 103.5352, 9000, 90, (-12, -12, 6), '38.1445 128.5352'),
    ('orbite', 38.1445, 103.5352, 150000, 90, (12, -13, 4), '38.1445 128.5352'),
]
for name, lat, lon, alt, heading, offset, sun in views:
    folder = out/name
    folder.mkdir(exist_ok=True)
    a, b = np.radians([lat, lon])
    up = np.array([math.cos(a)*math.cos(b), math.sin(a), math.cos(a)*math.sin(b)])
    north = np.array([-math.sin(a)*math.cos(b), math.cos(a), -math.sin(a)*math.sin(b)])
    east = np.array([-math.sin(b), 0, math.cos(b)])
    ship = up*(6378000+alt)
    camera = ship + east*offset[0] + north*offset[1] + up*offset[2]
    radius = np.linalg.norm(camera)
    ca, cb = math.asin(camera[1]/radius), math.atan2(camera[2], camera[0])
    cu = camera/radius
    cn = np.array([-math.sin(ca)*math.cos(cb), math.cos(ca), -math.sin(ca)*math.sin(cb)])
    ce = np.array([-math.sin(cb), 0, math.cos(cb)])
    direction = (ship-camera)/np.linalg.norm(ship-camera)
    cap = math.degrees(math.atan2(direction@ce, direction@cn))
    pitch = math.degrees(math.asin(direction@cu))
    pose = [lat,lon,alt,heading,0,0,math.degrees(ca),math.degrees(cb),radius-6378000,cap,pitch,0,48,600]
    (folder/'pose.txt').write_text('fps 60\n0 exterieur '+' '.join(f'{x:.10f}' for x in pose)+'\n', encoding='utf-8')
(out/'views.json').write_text(json.dumps([{'name':v[0], 'sun':v[-1]} for v in views],indent=2),encoding='utf-8')
print(out)
