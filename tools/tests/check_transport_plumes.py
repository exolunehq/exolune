"""Check both transport exhausts against points on the five physical slots as thrust vectors."""
from io import BytesIO
from pathlib import Path
import struct
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "assets/vaisseau/navette_aaa"))
import hullgrid


def grille_points():
    grid = hullgrid.HullGrid()
    rows = grid.points[grid.col["c0"]:grid.col["c1"] + 1]
    edges = [rows[:, hullgrid.B_CAV0], rows[:, hullgrid.B_CAV1]]
    edges.extend(.5 * (rows[:, top] + rows[:, bottom]) for top, bottom in grid.blade_rows)
    # Follow several stations inside each gap and along the four solid blade centres.
    edges = np.array(sorted(edges, key=lambda edge: edge[:, 2].mean()))[:, 5:-4:3]
    return .5 * (edges[:-1] + edges[1:]), edges[1:-1]


def sample_tile(tile, uv):
    x, y = (uv * [tile.shape[1], tile.shape[0]] - .5).T
    i, j = x.astype(int), y.astype(int)
    fx, fy = (x-i)[:, None], (y-j)[:, None]
    top = (1-fx) * tile[j, i] + fx * tile[j, i+1]
    bottom = (1-fx) * tile[j+1, i] + fx * tile[j+1, i+1]
    return (1-fy) * top + fy * bottom


def check_roots(nozzle, atlas, gaps, blades):
    count = int(nozzle[11])
    assert count >= 2 and atlas.shape == (count * 128, 192, 3), "Missing directional aperture tiles"
    tiles = atlas.reshape(count, 128, 192, 3)
    assert np.all(tiles[:, :16] == tiles[:, 16:17]) and np.all(tiles[:, 112:] == tiles[:, 111:112])
    tiles = tiles[:, 16:112] / 255.
    half_depth = .5 * nozzle[13]
    centre = nozzle[:3] + half_depth * nozzle[4:7]
    points = np.vstack((gaps.reshape(-1, 3), blades.reshape(-1, 3)))
    points = points * [np.sign(nozzle[0]), 1, 1] - centre
    gap_count = gaps.size // 3
    # Include angles between stored projections as well as both end stops.
    for weight in np.linspace(0, 1, 2 * count - 1):
        angle = np.arctan2(weight * nozzle[7], (1-weight) * half_depth)
        c, s = np.cos(angle), np.sin(angle)
        ray = np.array([0, c, -s])
        up = np.array([0, s, c])
        height = s * half_depth + c * nozzle[7]
        depth = c * half_depth + s * nozzle[7]
        uv = .5 + .5 * np.column_stack((points @ nozzle[8:11] / nozzle[3], points @ up / height))
        position = weight * (count-1)
        lower = int(position)
        fraction = position - lower
        lower_sample = sample_tile(tiles[lower], uv)
        upper_sample = sample_tile(tiles[min(lower+1, count-1)], uv)
        rgb = (1-fraction) * lower_sample + fraction * upper_sample
        np.testing.assert_allclose((2*rgb[:, 0]-1)*depth, points @ ray, atol=.015, rtol=0,
                                   err_msg="A discharge ray starts away from the physical grille")
        assert np.min(rgb[:gap_count, 1]) > .40, "An open slot has lost its hot sheet"
        assert np.max(rgb[gap_count:, 1]) < .08, "A solid blade is emitting gas"


def check(packet):
    gaps, blades = grille_points()
    with packet.open("rb") as source:
        magic, version, vertices, indices, draws, materials, image_count = struct.unpack("<4s6I", source.read(28))
        assert (magic, version) == (b"VSX1", 4), "Expected a transport flight packet"
        source.seek(vertices * 60 + indices * 4 + draws * 12 + materials * 96, 1)
        images = []
        for _ in range(image_count):
            srgb, size = struct.unpack("<2I", source.read(8))
            images.append((source.tell(), size, srgb))
            source.seek(size, 1)
        source.seek(52, 1)  # Cockpit pivots
        tag, clips = struct.unpack("<4sI", source.read(8))
        assert tag == b"ANI1"
        for _ in range(clips):
            tracks, frames, _fps = struct.unpack("<3I", source.read(12))
            source.seek(tracks * (32 + 28 * frames), 1)
        outlets = np.frombuffer(source.read(128), dtype="<f4").reshape(2, 16)
        assert np.allclose(outlets[0, :3] * [-1, 1, 1], outlets[1, :3]), "Asymmetric outlet roots"
        for nozzle in outlets:
            assert np.array_equal(nozzle[4:7], [0, 1, 0]), "Forward-burn gas must point straight aft"
            assert np.array_equal(nozzle[8:11], [np.sign(nozzle[0]), 0, 0]), "Misaligned grille width axis"
            image_id, depth, duct_width, stern_distance = nozzle[12:]
            assert duct_width > 0 and stern_distance > depth > 0
            assert 1 <= image_id <= len(images) and image_id == int(image_id)
            offset, size, srgb = images[int(image_id) - 1]
            assert not srgb, "Aperture depths require a linear texture"
            source.seek(offset)
            with Image.open(BytesIO(source.read(size))) as chart:
                check_roots(nozzle, np.asarray(chart), gaps, blades)
    print("PASS: both main exhausts stay on their five physical slots from aft thrust to full lift.")


if __name__ == "__main__":
    default = ROOT / "assets/vaisseau/navette/vaisseau.vsx"
    check(Path(sys.argv[1]) if len(sys.argv) > 1 else default)
