# Specification: cover the field of view, then optimize

Status: to be validated before implementation in the POC. Follows the 1 jet described in `concept.md`.

## The problem

**The lower you go, the less the face covers the field of vision.** Its half width is equal to k × the height above the ground. It covers the bottom of the camera, never the horizon.

- At 10 km altitude with k = 4, the face covers ±40 km. The horizon is at 357 km.
- The mountains go beyond the horizon: a summit of 8 km remains visible until 323 km beyond, or √(2 R H).

**Objective:** from 1 m to about 5 000 km altitude, cover the entire field of view to the horizon, including mountains. The detail on the screen must remain fairly constant, for a controlled cost.

## Axis 1: cover the field of view

### Solution chosen: the face, extended by geometric rings

**Keep the face of the jet 1 in the center, and surround it with square rings increasing in size.** Everything remains in the same plane, with the same rotation and normalization on the sphere.

- Each ring is a little bigger than the previous one: the grid spacing grows proportionally with the distance to the center.
- The rings stop at the horizon, plus the margin of the mountains.
- This is the continuous version of the "×2 face size stack" proposed at the 3 point of `concept.md`.

**Why it's economical:** On the screen, a grid cell always occupies about the same angle, close as far, regardless of the direction of viewing.

- One mesh, one calculation, one display.
- No seam to be treated: each ring connects to the previous vertex by vertex.

**Estimated cost** with a face of 129 × 129 and rings of 512 vertices:

| Height above ground | Rings | Summits total |
|---|---|---|
| 1 m | 775 | 413 000 |
| 10 km | 228 | 134 000 |
| 300 km | 88 | 62 000 |

For comparison, the current face of 257 × 257 counts 66 000 vertices.

### Construction rules

| Component | Rule |
|---|---|
| Central face | Half width s0 = k × height above ground, with k ≈ 2. Grid of (n + 1) × (n + 1), n = 128. |
| Ring i | Half width s0 × (1 + 2/n)^i, with 4n vertices. The grid cells remains roughly square. |
| Outer radius | Arc to the horizon + 323 km margin for mountains, brought back into the plan: R × tan(arc / R). |
| Number of rings | ln(outer radius / s0) / ln(1 + 2/n). The mesh is built once for maximum; only the required rings are displayed. |

### Indispensable condition: filter the octaves according to the grid spacing

**Without filtering, the distant rings spark.** Their grid cellss are miles long, while complexplanet contains details of a few hundred meters. Each vertex randomly falls on a detail thinner than its grid cell. The horizon is sparkling and the whole relief waves when you move.

**Rule:** Each vertex evaluates only octaves whose wavelength exceeds two grid cells. The last octave held fades gradually, to avoid jumps.

- The elevation calculation receives the grid spacing of the summit.
- Each generator stops its octave loop at this limit, turbulence included.
- Bonus for the 2 axis: the far rings cost much less.

**Known limitation:** complexplanet is not linear, because of selectors, terraces and curves. Seen from afar, the filtered relief differs a little from the full relief. The fade keeps the transition continuous.

### Positioning relative to the look (old jet 2)

**Recommendation: abandon the offset of the face to the point looked at.**

- With the rings, the density on the screen is already uniform in all directions. Moving the center would bring almost nothing.
- The offset would move the mesh with every head movement, and thus sparkle the relief.

The look really counts in two places:

- **The zoom.** As the field of view narrows, k is reduced and n is increased to refine the detail.
- **What is out of scope.** We avoid to calculate it: it is the first site of the axis 2.

### Outside perimeter

- **Above about 5 000 km of altitude**, the visible cap exceeds what a single plane can cover, about 60° around the nadir. It will take a coarse full sphere in the background.
- Atmosphere, textures, realistic lighting.

### Validation criteria

1. From 1 m to 5 000 km, look at the horizon in all directions: no gap between the ground and the horizon.
2. The distant mountains appear above the horizon.
3. No crack in the mesh.
4. The size of the grid cells on the screen remains almost constant, checked in wire.
5. In constant speed flight, the horizon does not sparkle.
6. The frame rate is measured at the reference views of the 2 axis. These measurements serve as the starting point for the 2 axis.

### Steps of implementation

1. **Measure before changing:** time GPU of calculation and display, displayed in the title.
2. **Face and rings, without filtering:** validate the coverage and the absence of cracks.
3. **Octaves filtering:** validate the stability of the horizon and relief.
4. **Measurements** at reference altitudes.

### Results of implementation

**The 1 axis is implemented**, with k = 2 and n = 128.

| Criteria | Result |
|---|---|
| 1. No void to the horizon | Verified in still image at 1 m, 69 m, 10 km, 300 km and 2 000 km. |
| 2. Mountains far away | Their silhouette exceeds the horizon at 1 m of height. |
| 3. No crack | Checked in iron wire at the junction between the face and rings. |
| 4. grid cells on screen | Almost constant from the foreground to the distance. Near the horizon, the grid cellss are slowing down under the effect of the racing perspective: it is expected. |
| 5. No flicker in flight | Octave filtering in place, to be checked in flight: a still image does not show it. |
| 6. Measures | See below. |

**Measurements** above 15° S, 50° E, look at 3° below the horizon then at 80°. The rendering time remains below 0,1 ms: all the cost is in the calculation of the terrain.

| Height above ground | Rings | Calculation GPU | Images per second |
|---|---|---|---|
| 1 m | 795 | 15 ms | 54 to 62 |
| 100 m | 499 | 11 ms | 70 |
| 10 km | 230 | 6 ms | 131 to 140 |
| 300 km | 88 | 2,4 ms | 272 to 276 |
| 2 000 km | 27 | 0,7 ms | 280 |

Looking does not change the cost: all the mesh is calculated, even out of the field. It is the first experiment of the 2 axis.

## Axis 2: performance

**Principle:** we start from the measurements of the axis 1. The most expensive job is tackled first, and every optimization is measured before and after.

### Constraints

- **All visible geometry is recalculated at each frame.** This is what allows you to move at any speed without waiting for loading. No optimization should break this principle.
- **The relief must remain planetary and credible**, with shapes that remind of the Earth. Any simplification of the noise passes through a visual comparison.

### Target

**Land calculation: 3 ms at most in the worst reference view, ideally 2 ms.** Today it is 15 ms at ground level. The rest of the budget will go to the rendering shaders coming: lighting, atmosphere, textures.

**Reference views:** above the continent at 15° S, 50° E, at 1 m, 100 m, 10 km, 300 km and 2 000 km of height, with the look at 3° below the horizon and then at 80°.

### Quality protocol

For each change that affects the noise:

1. Captures reference views before and after, by the capture built into the engine.
2. Side-by-side comparison, with the average elevation difference.
3. Validation by eye. If the relief changes character, the decision is up to you.

### Steps, by expected gain

1. **Calculate only what is in the field of view.** The calculation skips vertices out of the field, with a margin of two grid cells. A summit is tested with its entire possible altitude range, from sea level to 8 192 m. Thus, a mountain that enters the field from above is always calculated. The vertex below the camera is always calculated: it gives the height of the ground. Expected gain: 3 to 4 times when looking at the horizon, much more when looking down.
2. **Measure the cost of each complexplanet layer**, neutralizing them one by one. We will know where to put the effort. Turbulence is suspicious: it represents about two thirds of the octaves.
3. **Simplify the noise layers that cost the most**, according to the quality protocol. The experiments to test:
   - **A faster basic noise**, for example a tableless gradient noise, or a simplex, which interpolates 4 points instead of 8.
   - **Fewer octaves in turbulence.** Their last octaves distort the relief very little.
   - **The terrain type without recalculating the continents.** Today, he re-evaluates the whole chain of continents in a second point.
   - **The ocean in a simplified way.** Below sea level, the surface is flat: only the depth colours the water.
4. **Lighten the calculation in double precision precision.** The double is only useful for fine octaves, with a wavelength less than a few hundred meters. Wider octaves can float without visible loss.
5. **As a last resort, refresh the distant rings less often**, under two conditions: never above a given speed, and only if no delay is visible.
6. **Adapter n to budget**: reduce the fineness of the mesh if an image exceeds its time.

### Results of the 2 axis, in progress

**The worst case has gone from 15,1 to 1,6 ms**, below the ideal target of 2 ms. All views except ground level are under 0,3 ms. The detail of each setting is in `journal-planete.md`.

| Stage | Result |
|---|---|
| 1. Field of vision | Done. Worst case of 15,1 to 7,6 ms, no holes on the edges of the image. |
| 2. Cost of diapers | Made, at the ground level, look at the horizon. Turbulence: ~72 % of cost. Second continent calculation for terrain type: ~51 %. Double precision: ~20 %. These shares overlap. |
| 3a. Type of filtered terrain | Done. Its octaves are limited to a wavelength of ~100 km. Worst case of 7,6 to 4,6 ms. |
| 3b. Gradient table in shared memory | Done. Readings from the table to scattered indices cost a lot of constant memory. Render identical to pixel close, from 16 to 50 % gain depending on view. |
| 4. Double precision near camera only | Done. The double is only used for vertices where the grid cell is less than 4 m; further on, the imprecision of the float, 0,4 m, remains invisible. Up to 70 % gain depending on view. |
| 3c. Continental turbulence capped at 1024 | Done, validated. Worst case of 3,2 to 2,8 ms. Only the fine outline of some ribs changes: 0,2 % of pixels on the rib view, nothing else. |
| 3d. Vector turbulence | Done, validated in flight. The three axes of a turbulence in one noise: worst case of 2,8 to 1,6 ms. The exact shape of the rock spots and waves changes, without any difference noticeable to the eye. |

Each step was compared on six views: two over the continent of departure, one orbit view, another continent and two coast views. The average deviation remained below 0,13 on 255, with no pixel changed from more than 8 levels.

**Measurements after these steps**, above 15° S, 50° E:

| Height above ground | Looking at the horizon | Looking down |
|---|---|---|
| 1 m | 1,5 ms | 1,6 ms |
| 100 m | 0,3 ms | 0,3 ms |
| 10 km | 0,1 ms | 0,1 ms |
| 300 km | 0,1 ms | 0,0 ms |
| 2 000 km | 0,0 ms | 0,0 ms |

## Alternatives rejected

| Solution | Why it is rejected |
|---|---|
| Stack of nested faces, size ×2 | Density jumping by a factor 2 between levels, seams to be processed. At equal minimum density, about twice as many vertices as rings. |
| Quaternary tree on a fixed cube, the standard method of video game | The land pieces are fixed on the planet and cached: this is the most efficient. But she abandons the principle of a face that follows the camera, recalculated at each frame. To keep in reserve if the 2 axis is not enough. |
| One face, larger | At 10 km altitude, it would take close to 90 000 peaks per side to keep detail under the camera. |
