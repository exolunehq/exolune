# Specification: geometry stability

Status: the magnetization by teeth was tested and then abandoned. The jitter is measured: it comes from the lighting. Testing in progress: the slope on neighbors and fine grain in pixels. Follow-up to `spec-champ-de-vision.md`.

## The problem

**In flight, the relief shakes. This is not a problem of precision: it is the mesh that slides on the relief.**

- **Diagnosis:** The G key freezes the mesh while the camera keeps moving forward. The jitter disappears.
- **Mechanism:** the face and rings follow the camera continuously. From one frame to the next, each vertex lands in a place where there was no vertex. It samples the relief at another point, and the area between the vertices changes.

Three causes add up:

1. **The shot rotates continuously** to stay in front of the camera: the entire grid slides when you move.
2. **The size of the grid follows the height above the ground.** In razor, each bump changes it, and the entire grid is resized.
3. **Octave filtering keeps reliefs from 2 to 4 grid cells**, which waver as soon as the grid moves.

## The solution: magnetizing the grid

**Principle: the grid moves only by increments, chosen so that the vertex fall back on old vertex.** Between two rows, nothing moves. The concept remains intact: the shot is always looking at the camera and is always normalised into a sphere.

### 1. The plan turns by increments of a grid cell

- **The plane retains its orientation as long as the camera remains within half-grid cell of the center of the face**, measured on the plane.
- **Beyond this, it rotates to refocus on the top of the grid closest to the camera.** The vertices of the central square fall back exactly on the positions of their neighbors, with a negligible error.
- **The shot follows the camera with a maximum of half-grid cell delay.** At 50 m in height, it is 75 cm.
- **Rotation transports the reference frame from the plane without turning it around itself.** The reference frame is no longer set to the north: this prevents the grille from pivoting from one angle to the other.

### 2. Size changes by the growth of the rings

- **The half-face width only takes values (1 + 2/n)^m meters**, with integer m. When m changes by one, each ring falls back exactly in the place of its neighbor.
- **A quarter-step hysteresis** prevents oscillation between two values.
- **The height above ground used for pruning is smoothed** for half a second. The camera, on the other hand, is always protected by the actual height of the ground.

### 3. Rings are filtered more severely

- **Rings cannot be magnetized while moving:** centered on a moving point, their vertices never fall back on old vertices.
- **They therefore only keep the reliefs of at least 4 grid cells**, instead of 2, with full intensity beyond 8. A wide relief changes very little when the grid slides by a fraction of grid cell.
- **The transition is made on the first rings 16**, to avoid a break of detail at the edge of the central square.
- **The central square keeps the current filtering:** it is magnetic, it can keep its detail.

### To compare in flight

**H key turns all stabilization on or off**, without recompilation. The title of the window indicates this.

## Known limits

- **When climbing or descending, the central square jumps slightly at each height step.** Its edge falls back on the old first ring, but its inner vertices move, up to a grid cell near the edge.
- **The rings slide a little bit** at each move, by a fraction of grid cell smaller as they are far away.
- **The reference frame of the plan is no longer set to the north.** On a long journey, it slowly turns on itself, without visible effect.

## Validation criteria

1. In horizontal flight at low altitude, more jitter visible in the central square.
2. In the rings, jitter residual weak, to be judged by eye with H.
3. Flying over bumps no longer causes the grid to resize constantly.
4. No measurable cost on the calculation GPU.

## Test result: abandoned

- **Flight observation:** no more jitter in the central square, but geometry changes in increments. Out of the square, the jitter remained.
- **The more severe filtering** smoothed out too much relief without removing the jitter.
- **The bottom of the problem:** the continuous slipping of the plane is what densifies the mesh gradually, seamlessly. Magnetizing it turns it into tiered levels of detail. We keep the continuous slip.

## Measurement of the jitter

**The benchmark measurement: the camera remains still, and the mesh is positioned as if it were flying.** The relief is fixed on the planet: any difference between two successive images is jitter, and nothing else.

- **Launch:** `MYPLANETENGINE_TREMBLE=préfixe`, with `MYPLANETENGINE_TREMBLE_SPEED` for speed (1 by default). After 60 images startup, the application saves 24 images then exits.
- **Measures:** the average difference between successive images on the field pixels, on 255. Witness: mesh frozen, zero deviation.
- **Views:** 50 m to the horizon, 50 m down, 10 km to the horizon.

| Variant | 50 m horizon | 50 m low | 10 km horizon |
|---|---|---|---|
| Facettes | 0,63 | 0,68 |  |
| Normal relief, not a quarter of grid cell | 0,43 | 0,43 | 0,79 |
| Not a grid cell | 0,25 | 0,28 | 0,50 |
| Not two grid cells | 0,15 | 0,17 | 0,34 |
| Without lighting | 0,00 | 0,00 | 0,12 |

**Conclusion: the jitter comes almost entirely from the lighting.** The sliding of the geometry itself is almost not visible.

- **Why:** The slope changes much faster than the height. Sampled in slider vertices, its thin part, from 2 to 4 grid cells, changes from one frame to another.
- **A slope measured on two grid cellss almost no longer shakes**, but it loses the fine grain of the lighting.

## Measurement of mutation

**The benchmark of jitter only sees the flicker fast, from one frame to another.** The mutation is slow: as the grid cell approaches, it shrinks, and each octave appears in the relief when it covers the cut-off `MESH_BAND_LIMIT`. The higher the cut-off, the more detail comes close to the camera, so large on the screen.

- **Same benchmark as the jitter:** still camera, mesh placed as if it were flying. As he moves forward, he shrinks the grid cells in front of the camera, as he approaches.
- **Launch:** `MYPLANETENGINE_TREMBLE_FRAMES=64`, speed 1. The mesh advances about 1,07 times the height above ground. Temporal smoothing active.
- **Measurement:** after a blur of 8 pixels, to keep only the shapes, the average difference on the pixels of the field between the average of the 8 last images and that of the 8 first, on 255. The average on 8 images attenuates the flicker.
- **noise measurement:** the same deviation between images 9 to 16 and 1 to 8.
- **The old measurement is not suitable:** comparing the image to that of a face 8 times smaller only refines the face. In rings, the grid cell depends only on the distance to the nadir.

### Results: relief cut

**The measurement confirms the theft: the higher the cut, the more muted the foreground.** benchmark of the 2026-10-21, active smoothing spline.

| Cut | flicker without smoothing, mountain 10 km | Mutation, mountain 50 m | Mutation, mountain 10 km | Mutation, plain 10 km |
|---|---|---|---|---|
| 2 grid cells | 1,01 | 0,19 | 0,79 | 0,05 |
| 3 grid cells | 0,69 | 0,21 | 0,76 | 0,05 |
| 4 grid cells | 0,51 | 0,25 | 0,77 | 0,05 |

- **noise measurement:** 0,07 to 0,08 in mountains to 50 m, 0,17 to 0,20 to 10 km, 0,02 in plains.
- **In the foreground, the double mutation:** on the lower third of the image, at 50 m, from 0,17 to 0,36 between 2 and 4 grid cells. flicker and mutation exchange: the cut to 4 grid cells divides one by two and doubles the other.
- **At 10 km, the mutation is not dependent on the cut-off.** It comes from the terrain between 20 and 120 km, strong with the three cutoffs. Cause to look for: the turbulence of the continents and the rounding of the edges also follow the grid cell.
- **The benchmark field mask counts the sky from the atmosphere:** the averages are diluted, but remain comparable between variants.

## Testing in progress: slope on neighbors, fine grain in pixels

### 1. The slope comes from the neighboring peaks

- **The vertex shader calculates the normal by centered differences** between the positions of the four neighboring vertices: along the line and across, or along the ring and between neighboring rings.
- **Difference of two grid cells:** the pitch stability of two grid cells, without any additional relief evaluation. The calculation returns to its cost before the normals.
- **The lighting sticks to the drawn geometry**, since it comes from the same vertices.
- **A neighbor eliminated by framing is replaced by the vertex itself.** The margin of the framing changes from 2 to 3 grid cells, so that the visible vertices keep their neighbors.

### 2. Fine grain is drawn in pixels

- **A light noise, calculated pixel by pixel in fixed coordinates of the planet**, disturbs the normal. It does not move with the mesh, so it does not shake.
- **It covers only what the normal of the peaks does not see:** wavelengths less than 8 grid cells. It fades below two pixels, so it doesn't flicker.
- **The two bounds slide continuously** with the size of the grid cells and the distance: no bearing.
- **Precision:** the pixel calculates its position relative to an anchor near the camera, whole in units of 64 m. The indices of the noise network remain accurate on a global scale.
- **No grain on the sea**, which remains flat.
- **Only where complexplanet has fine relief:** between 13,5 m, its finest octave on earth, and 6 km. A first attempt without these markers invented a rough relief on the plains.
- **Tuning:** `DETAIL_SLOPE` in `PlanetSettings.hlsli`, the slope added per octave. 0 disables grain.

### Validation criteria

1. jitter measured at benchmark at the two-step level of grid cells or below.
2. Fine grain of the lighting comparable to the quarter pitch of grid cell, on side-by-side images.
3. GPU calculation returned to 1,6 ms; rendered upward by less than 0,5 ms.

### Results

**The jitter decreases from 43 to 67 % depending on the view, and the calculation from 4,9 to 1,9 ms at worst.** Detail and images: `journal-planete.md`.

- **Criterion 1:** close above the continent of departure, 0,22 against 0,15 for the step of two grid cells. Mountain to 10 km: from 17,6 to 6,6, the rest comes mostly from the color rock or snow.
- **2 criterion:** achieved above the continent of departure, grain measured to 3 % close. In mountains, softer edges: 9 % grain less at 50 m, 38 % at 10 km.
- **3 criterion:** 1,9 ms, due to the wider frame margin. Rendering: 0,11 ms at most.
- **Grain measured:** standard deviation of the luminance after a blur of 2 pixels, on the field, away from the silhouettes.

## Dismissed

**The grids fixed on the planet**: clipmaps, CDLOD, Proland, CBT. They eliminate the slipping, but abandon the camera-facing plane, the heart of the concept.

**Nested grids**: the transition between levels would be too abrupt and difficult to hide.

## Summary: is there a limit that cannot be crossed?

**Yes, but it is due to the mesh slide, not the recalculation at each frame.**

- **The mechanism:** a mesh slider samples the relief in other points at each frame. Between the vertices, the reconstructed surface changes, so the image too. This is a property of sampling, not a defect in accuracy.
- **What makes it visible:** The sharp edges of the noise, ridged and billow, are infinitely thin. No grid samples them without error. A fixed grid keeps a fixed, invisible error; a sliding grid moves it at each frame.
- **What can be done without changing the method:** lower this floor, without canceling it.

| Lever | Measured effect, mountain at 10 km | Cost |
|---|---|---|
| Normal on neighboring peaks | from 17,6 to 6,6 | gain of calculation |
| Temporal smoothing | from 3,4 to 0,62 | Negligible |
| 192 grid cells per side | from 0,62 to 0,46 | calculation × 2,2 |

- **An untried workaround:** round the sharp edges to the scale of the grid cell, with a softened absolute value, softer as the grid cell is large. The sampled relief has no more fine detail than the grid, so almost nothing to shake. The edges are continuously strengthened on approach, without bearing. Cost is negligible.
- **The basic solution, if the floor remains annoying:** vertices fixed on the planet, for example on the six faces of a cube, with a fading of the heights between levels of detail, in the manner of CDLOD.
  - We keep the recalculation of everything at each frame, without memory, so no catch-up or speed limit.
  - We lose the shot that looks at the camera.
- **A static geometry recalculated in the background is not necessary:** it would add memory and catch-up, for stability that fixed vertexes get without them.

## Test: round the edges to the scale of the grid cell

- **Where:** the absolute value of noise functions Billow and RidgedMulti, which creates the sharp crests and dips.
- **How:** Below a threshold ε, the absolute value becomes a parabola that joins it without break. Above, nothing changes: no bias on the rest of the relief.
- **ε follows the grid cell of the summit,** for each octave: ε = `CREASE_ROUNDING` × frequency of the octave / maximum frequency of the summit. The edge is rounded about one grid cell wide, regardless of its wavelength.
- **No bearing:** the grid cell shrinks continuously on approach, ε also, and the ridge firms.
- **Setting:** `CREASE_ROUNDING` in `PlanetSettings.hlsli`, 0 disables it.
- **Measure:** benchmark of jitter in mountain and plain, pictures, cost. Several values compared.

### Results

**Rounding divides the jitter by 2,5 in mountain, at no cost.** jitter on the whole image, with and without time smoothing:

| Round | Mountain, 50 m | Mountain, 10 km | Plaine, 10 km |
|---|---|---|---|
| 0, sharp edges | 0,06 / 0,21 | 0,46 / 3,02 | 0,02 / 0,14 |
| 0,5 | 0,05 / 0,20 | 0,34 / 2,37 | 0,01 / 0,13 |
| 1 | 0,05 / 0,19 | 0,26 / 1,88 | 0,01 / 0,11 |
| 2 | 0,04 / 0,17 | 0,17 / 1,20 | 0,01 / 0,08 |

- **In pictures:** at 10 km, the rounded 2 softens a little the ridges; close, almost nothing changes, the grid cells being small there.
- **Cost:** none, in the measurement noise.
- **Retained: 2,** judged a little better in flight, slight gain.

