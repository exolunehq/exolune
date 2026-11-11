"""Block compression for the generated atlases, in numpy: BC1 for colour and BC5 for normals.

BC1 fits each 4 x 4 block along its principal colour axis, then picks the nearest of
four palette entries; BC4 fits one channel between its block extremes with eight
steps. BC5 is two BC4 blocks. The encoders favour robustness over the last decibel.
"""
import numpy as np


def blocks(image):
    """(H, W, C) array -> (H/4 * W/4, 16, C) blocks, row-major; pads to a multiple of 4."""
    h, w = image.shape[:2]
    ph, pw = -h % 4, -w % 4
    if ph or pw:
        image = np.pad(image, ((0, ph), (0, pw), (0, 0)), mode='edge')
    h, w, c = image.shape
    return image.reshape(h // 4, 4, w // 4, 4, c).transpose(0, 2, 1, 3, 4).reshape(-1, 16, c)


def bc1(rgb):
    """RGB uint8 image -> BC1 bytes (opaque four-colour blocks)."""
    b = blocks(np.asarray(rgb)[..., :3]).astype('f4')
    mean = b.mean(1, keepdims=True)
    centred = b - mean
    cov = np.einsum('nki,nkj->nij', centred, centred)
    axis = np.ones((len(b), 3), 'f4')
    for _ in range(6):
        axis = np.einsum('nij,nj->ni', cov, axis)
        axis /= np.maximum(np.linalg.norm(axis, axis=1, keepdims=True), 1e-6)
    t = np.einsum('nki,ni->nk', centred, axis)
    lo = mean[:, 0] + axis * t.min(1, keepdims=True)
    hi = mean[:, 0] + axis * t.max(1, keepdims=True)

    def pack(c):
        c = np.clip(c, 0, 255)
        r, g, bl = np.rint(c[:, 0] * 31 / 255), np.rint(c[:, 1] * 63 / 255), np.rint(c[:, 2] * 31 / 255)
        return (r.astype('u2') << 11) | (g.astype('u2') << 5) | bl.astype('u2')

    def unpack(v):
        v = v.astype('u4')
        r, g, bl = (v >> 11) & 31, (v >> 5) & 63, v & 31
        return np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (bl << 3) | (bl >> 2)], 1).astype('f4')

    c0, c1 = pack(hi), pack(lo)
    swap = c0 < c1
    c0, c1 = np.where(swap, c1, c0), np.where(swap, c0, c1)
    p0, p1 = unpack(c0), unpack(c1)
    palette = np.stack([p0, p1, (2 * p0 + p1) / 3, (p0 + 2 * p1) / 3], 1)
    index = ((b[:, :, None, :] - palette[:, None, :, :]) ** 2).sum(-1).argmin(-1).astype('u4')
    index[c0 == c1] = 0
    bits = (index << (2 * np.arange(16, dtype='u4'))).sum(1, dtype='u4')
    out = np.zeros(len(b), dtype=[('c0', '<u2'), ('c1', '<u2'), ('bits', '<u4')])
    out['c0'], out['c1'], out['bits'] = c0, c1, bits
    return out.tobytes()


def bc4(channel):
    """One uint8 channel (H, W) -> BC4 bytes (eight-step blocks)."""
    b = blocks(np.asarray(channel)[..., None])[..., 0].astype('f4')
    r0, r1 = b.max(1), b.min(1)
    steps = np.stack([r0, r1] + [((7 - k) * r0 + k * r1) / 7 for k in range(1, 7)], 1)
    index = np.abs(b[:, :, None] - steps[:, None, :]).argmin(-1).astype('u8')
    index[r0 == r1] = 0
    bits = (index << (3 * np.arange(16, dtype='u8'))).sum(1, dtype='u8')
    out = np.zeros((len(b), 8), 'u1')
    out[:, 0], out[:, 1] = r0.astype('u1'), r1.astype('u1')
    for k in range(6):
        out[:, 2 + k] = (bits >> np.uint64(8 * k)) & np.uint64(255)
    return out


def bc5(rg):
    """Two uint8 channels (H, W, 2+) -> BC5 bytes: a red block then a green block."""
    rg = np.asarray(rg)
    return np.concatenate([bc4(rg[..., 0]), bc4(rg[..., 1])], 1).tobytes()


def decode_bc1(data, h, w):
    """Reference decoder for the self-check."""
    raw = np.frombuffer(data, dtype=[('c0', '<u2'), ('c1', '<u2'), ('bits', '<u4')])
    out = np.zeros((len(raw), 16, 3), 'f4')
    for n, (c0, c1, bits) in enumerate(raw):
        def unpack(v):
            r, g, b = (v >> 11) & 31, (v >> 5) & 63, v & 31
            return np.array([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)], 'f4')
        p0, p1 = unpack(int(c0)), unpack(int(c1))
        pal = [p0, p1, (2 * p0 + p1) / 3, (p0 + 2 * p1) / 3] if c0 > c1 else [p0, p1, (p0 + p1) / 2, np.zeros(3)]
        for k in range(16):
            out[n, k] = pal[(int(bits) >> (2 * k)) & 3]
    return out.reshape(h // 4, w // 4, 4, 4, 3).transpose(0, 2, 1, 3, 4).reshape(h, w, 3)


if __name__ == '__main__':
    rng = np.random.default_rng(1)
    y, x = np.mgrid[0:64, 0:64]
    image = np.stack([x * 4, y * 4, (x + y) * 2], -1).astype('u1')
    image[16:32, 16:32] = rng.integers(0, 255, (16, 16, 3))
    data = bc1(image)
    assert len(data) == 64 * 64 // 2, 'BC1 stores half a byte per texel'
    error = np.abs(decode_bc1(data, 64, 64) - image).mean()
    assert error < 6, f'BC1 gradient error {error:.2f}'
    rg = bc5(np.stack([x * 4, y * 4], -1).astype('u1'))
    assert len(rg) == 64 * 64, 'BC5 stores one byte per texel'
    print(f'bc self-check passed: BC1 mean error {error:.2f} levels')
