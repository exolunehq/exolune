# Specification: normals per pixel reconstructed in spline

Status: experiment 1 of `log/pistes-glissement.md`, measured at benchmark the 2026-10-21, tag `jalon/09-normales-spline`. Modest gain, kept with the smoothing B-spline; the relief cut-off is the essential. The cardinal spline prefilter, removed the 2026-10-30, is in `log/spec-normales-spline-historique.md`.

## The purpose

**A lighting that no longer depends on the position of the vertices.** The vertices of the sliding plane are accurate; it is the reconstruction between them that shakes, especially that of the slope.

- **Today:** the normal is calculated on the neighboring vertices, then linearly interpolated on the triangle. A wave of 8 grid cells still varies the slope of 17 % when the mesh slides.
- **With spline:** each pixel reconstructs the surface on the 4 × 4 neighboring vertices, with a smoothing cubic B-spline, and draws its normal from it. The cardinal spline of the original plane was shaking more (see benchmark results).
- **Nothing else changes:** neither the relief, nor the mesh, nor the drawn geometry. Only the normal of the lighting is replaced.

## The principle

### The two cards of the mesh

**The spline works in the coordinates of the grid of the mesh,** where the vertices are spaced evenly.

- **The face:** coordinates (i, j), from 0 to n, n = 192.
- **Rings:** coordinates (b, r). b is the position on the ring, from 0 to 4n, and returns to 0 after one turn. r is the ring number, starting from 1.
- **The spline reconstructs the 3D position of the vertices,** not just their height. The transition from grid to plane is smooth in each map: linear in the face, geometric from one ring to the next. The spline reproduces it without any noticeable error.

### Vertices for coefficients

**The smoothing B-spline takes the positions of the coefficient vertex,** without prefilter: it does not pass through them, and softens the waves from 2 to 3 grid cells, those that shake.

- **At the edges of a map,** the missing neighbor is replaced by the last vertex of the map. The rings start at r = 1: the edge of the face is not taken as the ring 0, because its neighbors do not follow the same grid.

### The normal of the pixel

- **Each pixel receives its coordinates in its map,** interpolated from its vertex.
- **It reads the 4 × 4 neighboring vertices** and calculates the two derivatives of the surface, along each axis of the map. Their vector product gives the normal.
- **No noise is evaluated:** 16 readings and some multiplications per pixel.

### Retreat areas

**Where spline does not apply, the pixel keeps the current normal,** with a fade on two grid cells.

- **The edge of the face:** the two cards do not extend each other. Normal current up to 3 grid cells of the edge, full spline from 5 grid cells, on both sides.
- **The corners of the rings:** the grid turns a quarter of a turn. Even faded, from 3 to 5 grid cells from the corner.
- **The triangles between the face and the first ring,** which mix the two cards: normal current.
- **Vertices offset out of field:** the margin of offset changes from 3 to 6 grid cells, so that the spline never touches the screen. If one of them is affected anyway, normal current.

## What changes in the code

- **`VertexShader.hlsl`** transmits to the pixel its map coordinates, its map and its distance to the nearest corner.
- **`PixelShader.hlsl`** reads the vertex of the mesh themselves, `splineVertices`, the vertex shader resource. It reconstructs the normal and blends it with the current normal according to the retreat zones. Fine grain per pixel is added then, as today.
- **`TerrainCompute.hlsl`**: margin of variation of 6 grid cells.
- **`PlanetSettings.hlsli`**: `SPLINE_NORMALS`, the weight of the normal spline. 1 activates it, 0 returns to the current normal.

## The measure

1. **The benchmark of jitter,** with and without temporal smoothing, on the three reference views: mountain at 50 m and at 10 km, plain at 10 km. `SPLINE_NORMALS` to 0 then to 1, also binary by the way.
2. **Heat maps of the benchmark,** to see where the jitter remains: the fold areas should come out.
3. **The cost GPU** of the spline.
4. **The judgment in vol.**

## Validation criteria

- **jitter to benchmark significantly lower** without temporal smoothing, excluding fold zones.
- **No visible seam** between the spline and the folding areas.
- **Cost:** less than 0,3 ms in total.

## Results of the benchmark

jitter mean between two images, on 255, without temporal smoothing; with smoothing in parentheses. benchmark of the 2026-10-21, same views as `log/spec-stabilite.md`.

| Variant | Mountain, 50 m | Mountain, 10 km | Plaine, 10 km |
|---|---|---|---|
| Normal current, cut-off at 2 grid cells | 0,17 (0,04) | 1,20 (0,17) | 0,08 (0,01) |
| Cardinal spline | 0,27 (0,06) | 1,52 (0,24) | 0,09 (0,01) |
| Spline half prefiltered | 0,20 (0,04) | 1,24 (0,19) | 0,08 (0,01) |
| B-spline smoothing | 0,15 (0,03) | 1,04 (0,15) | 0,07 (0,01) |
| B-spline smoothing, materials on the spline surface | 0,15 (0,03) | 1,01 (0,15) | 0,07 (0,01) |
| Same, cut off at 3 grid cells | 0,13 (0,03) | 0,69 (0,11) | 0,05 (0,00) |
| Same, cut off at 4 grid cells | 0,12 (0,02) | 0,51 (0,09) | 0,04 (0,00) |
| Normal current, cut-off at 4 grid cells | 0,13 (0,03) | 0,60 (0,09) | 0,04 (0,00) |

- **The cardinal spline worsens the jitter:** it restores the slope of the waves from 2 to 3 grid cells, which the current normal almost erased. The `log/pistes-glissement.md` table is corrected accordingly.
- **B-spline smoothing,** without prefilter, lowers it from 12 to 16 %. This is the saved setting. The prefilter and its adjustment, `SPLINE_SHARPENING`, are removed the 2026-10-30; tag `jalon/09-normales-spline`.
- **The materials taken on the spline surface,** at the meeting of the radius of view, bring almost nothing: 1,04 → 1,01. Keep, because without noticeable cost.
- **The diagnosis:** illuminated with a constant normal, the mountain view at 10 km still shakes from 0,79. The two thirds of the jitter do not come from the normal, but from geometry: the contours of the reliefs that mask themselves.
- **The cut of the relief is essential:** at 4 grid cells, the jitter is divided by two. The spline adds 15 % on the mountain view at 10 km.
- **The price of cut, judged in flight:** every detail is born closer to the camera, therefore larger on the screen, and the form mutes more as it approaches. Cut left at 2 grid cells. The benchmark does not yet measure this slow mutation.
- **Cost,** measured with prefilter: less than 0,1 ms in total.
- **The folding areas** are well limited: rendering of the spline weight checked on two views.
