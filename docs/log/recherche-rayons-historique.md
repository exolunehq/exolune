# History: the shadow height on a polar grid

Step 1 of sun rays, of the 2026-10-24, tag `piste/rayons-soleil`. Replaced the 2026-10-25 by the shadow height marked at each vertex of the mesh, with the horizon of the cast shadows (`../recherche-rayons.md`, tag `piste/ombre-unique`).

## The grid (`SunShadow.hlsli`)

- 512 directions on 512 radii, around the center of the face of the mesh, up to the reach of its rings.
- Radii increase in proportion to the distance beyond an inner radius, half the width of the face or 1 km. A cell covers 1,2% of its distance, close to the 1% of the rings.
- All directions are calculated: a relief outside the image casts its shadow into the image.

## Both passes, at every frame

- **The relief (`SunShadowTerrain.hlsl`):** the elevation of the terrain at each point of the grid, filtered to the cell like the mesh, `MESH_BAND_LIMIT`.
- **The walk (`SunShadow.hlsl`):** from each point, a walk to the sun on the sphere, of half a cell per step. The shadow height is the highest altitude hidden by a point of the relief: h cos φ − 2R sin²(φ/2) − (R + h) sin φ tan θ, for a relief h at the angle φ, a sun at the height θ. It stops when nothing higher than `MAX_TERRAIN_HEIGHT` can hide the sun anymore.

## Why she left

- **Two sources for one shadow:** the grid recalculated the relief and walked towards the sun, when the pass `Horizon.hlsl` already walked, at each vertex, on the heights of the image.
- **Its relief was not that of the image:** another grid, other cells.
- **Cost:** relief 0,50 to 0,67 ms, step 0,27 to 0,37 ms.

## Its measures

- **Cost,** minimum on images, RTX 4070 Ti, 1280 × 720: relief 0,50 to 0,67 ms, walk 0,27 to 0,37 ms, reading in atmosphere 0,02 to 0,09 ms.
- **jitter,** with and without smoothing: peak at 14°, 0,04/0,34 → 0,06/0,46; valleys at 9°, 0,06/0,40 → 0,06/0,44; needle at 11°, 0,04/0,30 → 0,05/0,34. Air alone, without ground: 0,05 → 0,09 without smoothing, at the edges of the beams, and 0,01 unchanged with.
- **Rotation of 1°:** air alone, returned on the previous image, departs from 0,41 with shadow, 0,43 without.
- **Resolution:** a grid of 256 × 256 lowered the hands, the air in front of the top of a peak remained in the sun and this band shook. 768 × 768 did not change almost anymore the image, for 2,4 ms.
