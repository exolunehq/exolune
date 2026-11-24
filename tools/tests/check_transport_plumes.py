"""Check the main exhaust axes and the five emitting slots in the shipped transport packet."""
from io import BytesIO
from pathlib import Path
import struct
import sys

import numpy as np
from PIL import Image


def check(packet):
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
                rgba = np.asarray(chart)
            lip = rgba[:, :, 3]
            assert np.all(lip >= rgba[:, :, 0]) and np.all(lip == lip[:1]), "Bend starts inside the grille"
            open_slots = (rgba[:, :, 1] > 115).astype(int)
            starts = np.diff(np.pad(open_slots, ((1, 0), (0, 0))), axis=0) > 0
            assert starts.sum(axis=0).max() == 5, "Expected five distinct sheets across the outlet"
    print("PASS: parallel aft jets, mirrored grille roots, five sheets and downstream bend.")


if __name__ == "__main__":
    default = Path(__file__).resolve().parents[2] / "assets/vaisseau/navette/vaisseau.vsx"
    check(Path(sys.argv[1]) if len(sys.argv) > 1 else default)
