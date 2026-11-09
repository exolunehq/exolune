# Grid hydrology helpers: priority flood (with epsilon, so every cell drains), D8 flow, accumulation, lakes.
import heapq, numpy as np

N8 = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))


def priority_flood(z, outlet, eps=0.0):
    n, m = z.shape
    filled = np.full(z.shape, np.inf); done = np.zeros(z.shape, bool); h = []
    for i, j in zip(*np.nonzero(outlet)):
        filled[i, j] = z[i, j]; done[i, j] = True; heapq.heappush(h, (z[i, j], i, j))
    while h:
        zz, i, j = heapq.heappop(h)
        for di, dj in N8:
            a, b = i + di, j + dj
            if 0 <= a < n and 0 <= b < m and not done[a, b]:
                done[a, b] = True
                filled[a, b] = max(z[a, b], zz + eps)
                heapq.heappush(h, (filled[a, b], a, b))
    return filled


def d8_accumulation(f, outlet):
    """f: filled surface with epsilon (strictly drains). Returns accumulation (cells) and receiver indices."""
    n, m = f.shape
    rec = -np.ones(n * m, int)
    for i in range(n):
        for j in range(m):
            if outlet[i, j]: continue
            best, bi = f[i, j], -1
            for di, dj in N8:
                a, b = i + di, j + dj
                if 0 <= a < n and 0 <= b < m:
                    s = (f[i, j] - f[a, b]) / (1.4142 if di and dj else 1.0)
                    if f[a, b] < f[i, j] and (bi < 0 or s > best):
                        best, bi = s, a * m + b
            rec[i * m + j] = bi
    order = np.argsort(-f.ravel())
    acc = np.ones(n * m)
    for k in order:
        r = rec[k]
        if r >= 0: acc[r] += acc[k]
    return acc.reshape(n, m), rec


def components(mask, steps=N8[:4]):
    n, m = mask.shape
    lab = -np.ones(mask.shape, int); sizes = []
    for i, j in zip(*np.nonzero(mask)):
        if lab[i, j] >= 0: continue
        k = len(sizes); st = [(i, j)]; lab[i, j] = k; s = 0
        while st:
            a, b = st.pop(); s += 1
            for da, db in steps:
                x, y = a + da, b + db
                if 0 <= x < n and 0 <= y < m and mask[x, y] and lab[x, y] < 0:
                    lab[x, y] = k; st.append((x, y))
        sizes.append(s)
    return lab, np.array(sizes)


if __name__ == "__main__":
    z = np.array([[5, 5, 5, 5], [5, 1, 2, 5], [5, 2, 3, 0], [5, 5, 5, 5]], float)
    out = np.zeros(z.shape, bool); out[2, 3] = True
    f = priority_flood(z, out)
    assert f[1, 1] == 2 and f[2, 2] == 3  # the pit fills to its 8-neighbour spill at (1,2)
    acc, _ = d8_accumulation(priority_flood(z, out, 1e-3), out)
    assert acc[2, 3] == 1 + acc[2, 2] or acc[2, 3] >= 4
    print("ok")
