# Specification: Fixed Tops POC (CDLOD)

Status: closed after step 3, tag `piste/sommets-fixes-etape3`. The concept keeps the sliding plan: see the conclusion at the end of the document. Following the review of `spec-stabilite.md`.

## The purpose

**Remove the jitter at the root:** each vertex always samples the same point of the planet.

- **The sliding plane** makes the relief sampled in other points at each frame: this is the cause of the jitter, measured and documented in `spec-stabilite.md`.
- **This POC only replaces the mesh placement.** Everything else is kept as is:
  - the noise complexplanet, recalculated for each vertex at each frame;
  - atmosphere, materials, time smoothing, rounding of edges.
- **No memory, no catch-up, no speed limit:** as today, everything is recalculated at each frame.
- **Direct comparison in flight:** one key switches between the sliding plane and fixed vertex, with the same terrain and the same lighting.

## The principle: the CDLOD method

Reference: Strugar 2009, *Continuous Distance-Dependent Level of Detail for Rendering Heightmaps*. Adapted here to a sphere and a procedural relief.

### The cube and its tiles

- **Six fixed faces of a cube,** projected on the sphere. A tangent deformation equalizes the size of the grid cells between the center and corners of a face.
- **Each face is a tile tree:** a tile divides into four tiles twice as small. Depth up to about 24 levels, for grid cells of the order of the centimeter to the ground.
- **Each tile is a grid of 64 × 64 grid cells,** regardless of its level. Only its size changes.

### The choice of tiles, at each frame

- **The processor runs the tree** from all six faces.
- **A tile is split** when the camera is close enough to make its grid cells become too large on the screen. Distance thresholds double from one level to the next.
- **It is dismissed** if it is out of the field of view or behind the horizon, taking into account the highest possible peaks.
- **Density:** at worst, today's one, about 7 pixels per grid cell. Adjustable by a distance factor.
- **Target cost:** less than 0,1 ms of CPU.

### The fade of height

**It is he who makes level changes invisible.** Vertices never move horizontally.

- **In each tile, we distinguish two kinds of vertex:**
  - even vertices, which also exist in the parent tile, coarser;
  - Odd vertices, which exist only at this level.
- **An odd vertex is drawn to the rough surface:** the average of its two even neighbors, taken in position 3D, on the edge or diagonal of the parent triangle.
- **The fading factor depends on the distance from the summit to the camera:**
  - 0 near the camera: true height;
  - 1 at the level limit: laid on the rough surface;
  - between the two, it varies continuously.
- **The noise is always rated at the fixed point of the top,** never at the melting point: nothing slips.
- **Octaves filtering follows the fade:** the actual grid spacing is continuously changed from the level to the parent. At the level limit, the tile and its coarser neighbor therefore calculate exactly the same heights, without a gap at the junction.
- **The diagonals of triangles** are oriented in the same way at all levels. Thus, once completely melted, a tile coincides exactly with its parent.

### Normals and Edges

- **The normal comes from neighboring peaks,** as today.
- **Each tile calculates one more row of vertices around,** not drawn. Its edge vertices have their neighbors, identical to those of the adjacent tile of the same level.
- **Cube edges:** The tiles of two neighboring faces share the same points of the sphere on the common edge.

### The precision

**Same method as today: no large float subtractions.**

- **The center of each tile** is calculated in double precision on the processor, in direction on the sphere and in position relative to the camera.
- **The shift of a vertex from this center** is calculated in float, with formulas that did not subtract two close numbers.
- **The noise receives** the double center plus this offset, as the current compute shader does with the nadir.

### Calculation and drawing

- **A single compute dispatch for all tiles selected:** a list of tiles with center, axes, level and fading thresholds, then 67 × 67 vertices per tile: 65 × 65 drawn, plus the edge row.
- **One single drawing call,** instantiated: a common clue grid, and a vertices offset per tile.
- **The vertex shader and pixel shader** receive the same data as today, including the grid spacing, which keeps the fine grain and materials.

## What changes for the user

- **M key:** switches between the sliding plane and fixed vertex. The window title indicates the mode.
- **`MYPLANETENGINE_MESH=fixed`** starts in fixed vertex, for captures and the benchmark.
- **The benchmark of jitter:** the camera remains immobile, and the choice of tiles is as if it were flying. It is the exact equivalent of the current benchmark.

## The steps

1. **The cube and the tiles, without fade or row of edge:** validate the geometry, precision and choice of tiles. The slots at the level junctions are expected at this stage.
2. **The height fade:** the slits and jumps must disappear.
3. **The normal ones,** with the side row.
4. **The benchmark of jitter in fixed vertex,** then the measurements.
5. **The adjustment of density and cost.**

## Validation criteria

1. **jitter to benchmark** clearly below that of the sliding plane, without temporal smoothing, on mountain and plain views.
2. **No visible slit** at the level junctions or at the edges of the cube.
3. **No visible jump** when a tile splits or regroups. Only the gradual rise of the fine relief at the approach is accepted.
4. **Cost:** calculation GPU at worst comparable to today, at most twice as much. Processor under 0,1 ms.
5. **Flight judgment,** with toggle between the two modes.

## What we lose

- **The shot that looks at the camera,** and its perfectly continuous densification. It is replaced by doubled levels, softened by the fade.
- **If POC is selected,** the sliding plane can remain as a comparison mode and then be removed.

## Details of the stage 2

- **Fade covers the entire range of a level:** from the distance where the tile would split, 1,25 times its size, to the distance where its parent would regroup, 2,5 times. Each vertex evolves with each frame during the whole approach.
- **Distance measured from the ground below the camera,** as for tile selection. A guarded tile has all its vertices beyond its division threshold, its coarser neighbor all its vertices beyond the grouping threshold: at their junction, the end is completely melted.
- **grid spacing depending only on the level:** R × π/2 / (64 × 2^level). Tangent deformation keeps the true size to 6 % close. Two neighboring tiles filter exactly the same their common vertices.
- **The actual grid cell depends only on the distance:** distance / (64 × 1,25), never below the grid cell of the tile. It sets the octaves of the noise, and the fade: a vertex of a grid level begins to fade when the actual grid cell reaches that level, and is fully fade when it is worth twice.
- **The fade is nested:** at the junction, the coarse tile itself is partially blended to its parent. The fine tile must therefore reproduce this fade on its vertices of the coarse level.
  - Each tile blends all its grid levels, from the pitch of 64 grid cells to the pitch of a grid cell, from the coarsest to the finest.
  - A vertex is drawn to the middle of its two neighbors of the twice looser grid, as they are already drawn.
  - The surface drawn depends only on the point and its distance: two tiles draw the same common points, regardless of their levels.
- **The calculation passes:** the first one evaluates the real heights. Then one pass per grid level, seven for 64 grid cells, writes the drawn mesh.

## Details of the stage 3

**Defect seen in flight at step 2:** a seam of lighting along the edges of the tiles. Each tile calculated the normal of its edge vertices with its only vertices, thus on one side.

- **The edge row must be blended like the rest.** The fading of a vertices to a grid cell edge asks its neighbors in the grid twice as loose, so a vertices to two grid cells, which itself asks a vertices to four grid cells, and so on.
- **Rows at 1, 2, 4 and 8 grid cells of each edge,** not drawn. Each one carries only the vertices of its level: all 1, 2, 4 and 8 vertices. So 496 more vertices per tile, 12 % more calculation.
- **The row at 8 grid cells is not blended.** This is true as long as a tile does not extend over more than three levels of distance, which is ensured by the choice of tiles.
- **Between two levels, the normals of the edges connect also:** the small tile is completely fused with it, and its centered differences fall on the same triangles as those of the large tile.

## T-joints

**At a level change, a small tile has twice as many vertices on the common edge as its large neighbor.** Its vertices are not connected to anything on the other side: it is a T-joint. If their height differs from that of the edge of the large tile, a slot opens.

- **What the 2 step does:**
  - on contact with a coarser neighbor, of one level or more, the finer grid levels of the small tile are completely fused: its vertices in addition are placed in the exact middle of their two neighbors, thus on the edge of the large tile;
  - its other vertexes are at the same points as those of the large tile, with the same heights, thanks to the filtering that follows the fade.
- **What can remain:** Even placed exactly on the edge, a T-vertice can leave slots of a fraction of a pixel, by the roundings of the rasterizer.
- **The conventional remedies, if they are seen:**
  - skirts, small vertical walls along the edges of the tiles, which block the slots from below;
  - or a seam: retriangle the edge of the small tile to remove the T-joints.

## Results of the stage 1

- **Geometry:** the tiles join, from orbit to the ground. Only a few slots remain at level changes, expected before the fade.
- **Fault found and corrected:** the tangent of the GPU is accurate only to about 1e-6 in absolute value, or 1 % error for small angles of thin tiles. Each tile was 1,5 % too small, resulting in a grid cell gap between all tiles. Replaced by its series development.
- **Tile Choice:** The height range of a tile is estimated around the floor below the camera, plus or minus a part of its size. Take 0 to 8 km for all divided all small tiles close to the centimeter.
- **Cost, still too high:**

| View | Carreaux | Calculation, fixed vertices | Calculation, sliding plane |
|---|---|---|---|
| Mountain, 10 km | 116 | 1,4 ms | 0,3 ms |
| Plaine, 50 m | 299 | 5,7 ms | 1,2 ms |
| Sol, 1 m | 446 | 12,3 ms | 3,3 ms |

- **Why:** a half-visible tile is calculated in its entirety, when the sliding plane pushes each vertex out of the field. To be processed in step 5: smaller tiles, off-field vertices in the compute shader.

## Results of the steps 2 and 3

- **No visible slit or seam,** from 10 km to 50 m, in solid as in wire.
- **The fine relief rises continuously as you approach,** without jumping when cutting a tile.
- **Cost of calculation in plunge view:** 1,6 ms in mountain at 10 km, 6,2 ms in plain at 50 m.

## Conclusion: fluidity

**Judged in flight: the ship seems to slow down and then accelerate again.** Measured by automatic straight-line flight, `MYPLANETENGINE_FLIGHT`, speed ×5:

| Vol | Mode | Duration of an image | Images à-coups | Calculation GPU |
|---|---|---|---|---|
| Mountain, 800 m | Plan glissant | 3,6 ms, regular | 0,5 % | 0,8 ms |
| Mountain, 800 m | Fixed summits | 12 ms, from 3,6 to 23 ms | 34 % | 7,5 ms, up to 17 |
| Plaine, 70 m | Plan glissant | 3,6 ms, regular | 0 % | 0,7 ms |
| Plaine, 70 m | Fixed summits | 8,5 ms | 1,5 % | 5,2 ms |

- **The cost follows the number of tiles retained,** which varies with the relief and the view: from 179 to 417 on the mountain flight. An image that exceeds the screen period waits for the next refresh: the motion is jagged.
- **Sliding plane always calculates the same number of vertices:** constant cost, regular images. That's the strength of the concept.
- **Secondary cause:** the speed follows the height above the ground, calculated here with all octaves. It jumps up to 22 % from one frame to another, compared to 5 % for the sliding plan.
- **Decision:** the POC stays on its branch, and we return to the sliding plane. Its reusable achievements: the nested fade, the tangent in series and the automatic flight.
