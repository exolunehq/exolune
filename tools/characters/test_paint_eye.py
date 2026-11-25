"""Check that the cook finds irises wherever an eye atlas puts them: python tools/characters/test_paint_eye.py"""
import numpy as np
from cook import paint_eye

size = 256
yy, xx = np.mgrid[0:size, 0:size] / size
atlas = np.full((size, size, 4), 255, np.uint8)
atlas[..., :3] = 205  # the white
for cx, cy in ((0.29, 0.71), (0.71, 0.29)):  # MakeHuman's diagonal layout, nothing at the centre
    atlas[np.hypot(xx - cx, yy - cy) < 0.11, :3] = (82, 33, 10)
atlas[size // 2 - 1:size // 2 + 1, :, :3] = (190, 90, 90)  # a thin red vein across the white
albedo, orm = paint_eye(atlas)
iris = orm[..., 2] / 255.0
assert iris[int(0.71 * size), int(0.29 * size)] > 0.95 and iris[int(0.29 * size), int(0.71 * size)] > 0.95
assert iris[size // 2, size // 2] < 0.05 and iris[size // 2, size // 8] < 0.05  # the centre and the vein stay white
assert albedo[int(0.71 * size), int(0.29 * size), 0] > 82  # the iris comes out clearer
print("paint_eye ok")
