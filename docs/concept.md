# Concept: the cube face that follows the camera

Status: reference. Validated and implemented since milestone 01; it replaces the radial “spiderweb” mesh in `log/general_spec.md`.

## In one sentence

**We generate just one grid: a cube face centered below the camera, projected onto the sphere, which shrinks as we descend.** Its terrain is recalculated every frame by Exolune's tectonic terrain function, evaluated in the planet's fixed reference frame.

The goal: a real-scale planet, from orbital flight down to the ground, without loading any models.

## The pipeline, every frame

1. **Nadir.** Draw the line from the planet's center to the camera. Its intersection with the sphere is the nadir.
2. **Orientation.** Rotate the cube so that one face points toward the camera. It is then centered on the nadir.
3. **Size.** Initially, this is a complete face: it covers 45° on either side of the nadir. Shrink the face as the camera descends.
4. **Spherization.** Normalize each vertex relative to the cube's center. This gives a direction on the sphere.
5. **Elevation.** Evaluate noise along this direction, expressed in the planet's fixed reference frame. The cube's rotation plays no part.
6. **Position.** Place the final vertex at `direction × (R + élévation)`.

Steps 2 and 4 can occur in either order: rotation preserves lengths. The normalized face can therefore be prepared in its local frame, then rotated in the shader.

## What the concept guarantees

- **The terrain does not move with the grid.** A point on the planet always has the same altitude, regardless of the cube's orientation.
- **Nothing to load.** No tiles or models: everything is recalculated from position.
- **No seams.** With just one face, there are no joins between cube faces to manage.
- **A natural floating origin.** The face is centered below the camera. Its local frame serves as the rendering frame and limits precision errors.

## The size rule

**Proposal: the face's half-width equals k × altitude.** Viewed from above, a grid cell then always subtends the same angle on screen. This gives constant detail “from the user's point of view”.

The face is capped at a complete cube face, with a half-width equal to radius R.

Example with R = 6,378 km, k = 2 and a 512 × 512 grid:

| Altitude | Horizon | Face half-width | Ground grid spacing |
|---|---|---|---|
| 2 m | 5 km | 4 m | 1.6 cm |
| 100 m | 36 km | 200 m | 78 cm |
| 10 km | 357 km | 20 km | 78 m |
| 400 km | 2,200 km | 800 km | 3.1 km |

k and the grid size control the trade-off between detail and cost.

## Decisions to make

### 1. Face center: decided, in two iterations

**Iteration 1: the face points toward the camera.** It lies on the line joining the planet's center to the camera, at distance R from the center. Its center is therefore the nadir. It is a panel that always faces the camera.

**Iteration 2: the face slides slightly toward the point being viewed.** An altitude-dependent offset places the most detail at the center of the view.

Constraints for iteration 2:

- **The offset stays bounded.** At low altitude, the viewed point may be hundreds of kilometers away, or even in the sky. Following it would move the ground below the camera outside the face. Proposal: an offset proportional to the face size, and therefore to altitude.
- **Turning the view moves the face.** The sliding in point 2 then occurs even with a stationary camera. The offset will need smoothing.
- **PlanetaryEngine already has a version.** Its mesh targets a point ahead of the camera, at twice the altitude, capped at 2,500 km.

### 2. “Swimming” terrain

**The grid slides over the terrain every frame,** because it follows the camera's position and changes size. The terrain stays fixed, but is sampled at different locations from one frame to the next. Details finer than a grid cell flicker, and ridges ripple.

Two standard remedies, which can be combined:

- **Limit octaves to grid spacing.** Evaluate only octaves whose wavelength exceeds two grid cells, fading out the last one. Bonus: less computation.
- **Move the grid in increments.** Advance the face one whole grid cell at a time and change its size in ×2 steps, fading between levels through geomorphing.

The face's rotation around the vertical must also be fixed, for example to north. Otherwise, every heading change rotates the whole grid.

**Recommendation: prototype the continuous version first,** to observe the artifact before correcting it.

### 3. Detail toward the horizon

**A face proportional to altitude covers the area below the camera, not the horizon.** At 10 km altitude, the face covers ±20 km while the horizon is 357 km away. As soon as you look ahead, most of the screen lies outside the face.

Expanding a single grid to the horizon does not work. At 10 km altitude, keeping roughly 8 m grid spacing below the camera, about one pixel at 1080p, would require nearly 90,000 vertices per side.

“Distant views” therefore matter at every altitude, not just from orbit.

**Approach: stack faces with sizes increasing by ×2,** all centered below the camera and using the same grid. About log2(horizon / face size) levels are needed: around ten at 2 m altitude, four or five at 10 km. This applies geometry clipmaps to the sphere.

A Unity prototype by the author already did this in 2012: 16 patches of 255 × 255, increasing in width, positioned below the camera.

The alternative already described in `log/general_spec.md` is the radial spiderweb mesh, prototyped in The-Forge outside this repository.

### 4. Above 2,640 km altitude

**One complete face no longer covers everything visible.** The visible spherical cap extends beyond 45° around the nadir when altitude exceeds R × (√2 − 1), approximately 2,640 km. Neighboring faces are then needed, up to five visible faces. This is the true “view from space” case.

### 5. Float precision

**In float32, at 6,378 km from the center, precision spacing is 0.5 m.** Two consequences:

- **Rendering.** Positions must be relative to the camera. The face's local frame is suitable for this.
- **Noise.** Evaluated in absolute float32 coordinates, terrain is quantized to 0.5 m. This was sufficient for complexplanet, the first terrain function, but not for walking on the ground. A known solution: calculate each octave's offset in double precision on the CPU and pass only local coordinates to the GPU.

Not a blocker for an initial prototype.

### 6. complexplanet stopped at 7.5 m

**Its own code said so: beyond 0.25 arcseconds, about 7.5 m, the terrain became blurry.** Reaching the ground will require additional detail layers below 7.5 m, modulated by terrain type.

### 7. Cost per frame

**complexplanet required about 340 noise evaluations per vertex.** Breakdown: 114 octaves in the generators, plus 12 turbulence operations with 3 Perlin noise evaluations each, totaling 225 octaves, plus one Voronoi.

Order of magnitude, to be measured: 10 levels of 256 × 256 give about 650,000 vertices, or 220 million evaluations per frame. A recent GPU should handle this, but it is the dominant cost.

**Measured on the iteration 1 prototype, with complete complexplanet:**

- One 513 × 513 face: 13 to 22 fps in orbit.
- One 257 × 257 face: about 50 fps in orbit, 150 at 4 km altitude.
- Cost is higher than expected: turbulence recalculates some subgraphs, such as continents, at a second point.

Normals are calculated from neighboring grid vertices, without reevaluating noise.

## Noise layers

**Exolune's tectonic terrain:** `Relief.hlsli`, using the tectonic map in `Tectonics.hlsli` and the building blocks in `Noise.hlsli` (`geometrie.md`, `spec-relief-tectonique.md`).

- **Large shapes, above 50 km,** come from a map computed at startup: continents, plates, boundaries, mountain ranges and trenches.
- **Detail, below 50 km,** comes from twelve noise octaves modulated by geology, about 40 to 60 noise evaluations per vertex, compared with 340 for complexplanet.
- **History:** the complexplanet and libnoise port, from milestone 01 to 2026-10-30; an original rewrite of its composition on 2026-10-31, commit `f00004d`; source status before the first port in `log/concept-historique.md`.

**License.** The terrain is not derived from complexplanet or libnoise. The engine's license is in `../LICENSE.md`; third-party credits are in `../NOTICE`.
