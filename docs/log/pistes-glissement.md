# experiments: make the slide invisible

Status: experiments opened the 2026-10-21, after the closure of the POC of the fixed summits (`spec-sommets-fixes.md`). The concept is maintained: a mesh that slides with the camera and adapts to each frame.

## The finding

**The summits do not shake: they are accurate.** Each carries the true elevation of its point of the planet, an absolute value.

- **What shakes is the reconstruction between the summits.** A pixel almost always falls between vertices. He sees the triangle, not the relief.
- **The triangle depends on where the vertices are.** When the mesh slides, the same point of the planet is reconstructed differently at each frame.
- **Consequence:** jitter is not removed by changing samples. We remove it by changing the way of rebuilding between them.

## The mathematical principle

**Shannon's Theorem:** A signal whose wavelengths exceed two grid cells is entirely determined by its samples, wherever they fall. Rebuilt with the ideal core, it no longer depends on the position of the grid.

- **The slip is therefore invisible in theory,** under two conditions: a filtered relief below the limit of the two grid cells, which is already done by the octave filtering, and a reconstruction close to the ideal.
- **The triangle is the worst possible reconstruction:** a linear interpolation, the core in tent.
- **Triangle error,** for a wave of amplitude A and length n grid cells: in the middle of a grid cell, the reconstructed height is A·cos(π/n) instead of A. The jitter is therefore equal to A·(1 − cos(π/n)), approximately 5·A/n².
- **Error of the slope,** which makes the lighting: it is much stronger than that of the height. That is why the jitter is seen especially in the light.

## The figures

Variation of the slope reconstructed at a fixed point when the grid slides, as part of the real slope; in parentheses, the part of the slope restored as average. Numerical calculation on a sinusoid of n grid cells wavelength.

| n grid cells | Current normal | B-spline smoothing | Cardinal spline |
|---|---|---|---|
| 2 | 0 % (×0,00) | 17 % (×0,17) | 51 % (×0,50) |
| 3 | 10 % (×0,28) | 6,5 % (×0,47) | 13 % (×0,94) |
| 4 | 9,3 % (×0,52) | 2,9 % (×0,66) | 4,4 % (×0,99) |
| 8 | 3,4 % (×0,85) | 0,4 % (×0,90) | 0,4 % (×1,00) |

- **The current normal** is calculated on the neighboring vertices, then interpolated on the triangle. It almost erases the waves from 2 to 3 grid cells, which is why they shake little.
- **The cardinal spline** passes through the vertexes and returns the entire slope, including that of the waves from 2 to 3 grid cells, which then shakes strongly.
- **The smoothing B-spline,** without prefilter, shakes less than the current normal from 3 grid cells, while remaining sharper.
- **For height,** the difference is even greater: at 4 grid cells, 0,9 % variation for the smoothing B-spline versus 15 % for the triangle.
- **Correction:** the first version of this table gave the maximum error, which mixes the stable bias with the jitter. It wrongly predicted that the cardinal spline would be the best. The benchmark denied it, see `spec-normales-spline.md`.

**Consequence: no reconstruction stabilizes the waves from 2 to 3 grid cells.** Only cutting the relief before them removes them.

## The experiments, in the proposed order

### 1. Normals per pixel, reconstructed in spline

**This is the “formula”: the best reconstruction for the lowest cost.** It targets the lighting, which carries the essentials of the jitter.

- **A pass of calculation after the field** applies the prefilter to the vertices positions, row by row and column by column. No noise is revalued.
- **Each pixel receives its coordinates in the grid of the mesh,** interpolated from the vertices. It reads the 4 × 4 neighboring vertices and draws the spline surface, then its normal by the two derivatives.
- **Resultate at benchmark,** with smoothing B-spline: 12 to 16 % of jitter less. Details in `spec-normales-spline.md`.
- **Expected cost:** 16 readings and a few multiplications per pixel, without noise. Much cheaper than a relief evaluation per pixel.
- **The difficulty: setting the mesh.**
  - The face is a regular grid: nothing to report.
  - The rings are regular in their coordinates, ring number and position on the ring, but broken at the corners of the squares.
  - Between the face and the first ring, the two grids do not extend.
  - First shot: return to the current normal, in fading, two grid cells of the corners and the edge of the face.
- **Measure:** the benchmark of jitter without temporal smoothing, on mountain and plain views, then flight judgment.

### 2. Relief per pixel, reconstructed in spline

**The same spline surface, also applied to geometry:** silhouettes and depth.

- **The pixel corrects its depth** by one or two Newton iterations between the viewing radius and the spline surface. The deviation to the triangle is small, of the order of the error of the table.
- **The silhouettes:** the mesh must be slightly inflated so that the spline surface never protrudes from the triangle.
- **To do only if,** after the experiment 1, the jitter of the silhouettes remains visible.

### 3. Adjust the relief band

**The waves of 2 to 3 grid cells shake regardless of reconstruction.**

- **Today,** an octave is whole up to 4 grid cells and extinguishes at 2 grid cells.
- **`MESH_BAND_LIMIT` setting:** the shortest wavelength kept, in grid cells.
- **Measured at benchmark, with spline:** a cut at 4 grid cells divides the flicker by two.
- **Judged in flight:** the form mutes more as you approach, because every detail is born closer. Cut left at 2 grid cells. flicker and mutation exchange: the benchmark must measure both.

### 4. Rewriting: circular rings

**Circles that grow in geometric progression,** instead of squares.

- **Smooth setting everywhere:** no more corners, so the spline applies without exception out of the center.
- **Zoom without re-sampling:** in these coordinates, changing altitude is a translation along the rings. With a scale chosen by increments of the growth factor, about 1 %, the ring k falls exactly on the ring k + 1.
- **Horizontal translation always resamples:** no grid is both zoom and translation invariant.

### 5. Heavy rewrite: relief calculated per pixel

**The limit idea: each pixel evaluates the relief at its own point,** by a fine-tuned ray throw from the mesh.

- **Slip disappears by construction:** the sample is the pixel, and filtering to pixel size makes the rest invisible with temporal smoothing.
- **The cost is the lock:** about one million pixels versus one hundred thousand vertexes, and several evaluations of the full noise per pixel. Or 30 to 40 times the current calculation.
- **Prerequisite:** a noise much cheaper than complexplanet. A experiment of research in itself.

## Already discarded

- **The magnetization by rows,** tag `piste/aimantation-crans`: jumps visible at each row.
- **Fixed summits,** tag `piste/sommets-fixes-etape3`: stable, but a variable cost that sacks the flight.
- **A memory of the relief in planet space,** smoothed from frame to frame: contrary to the integral calculation at each frame.

## Proposal

**Start with the experiment 1,** on the only sliding plane, measured at benchmark before and after. It is the one that promises the most gain for the least changes, without touching the relief calculation.
