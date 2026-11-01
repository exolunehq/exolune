# Specification: the parallax of the relief of materials

Status: first version made the 2026-10-22, to be judged in flight.

## The finding

- **The mesh bears a form only from eight grid cells per wavelength,** `MATERIAL_RELIEF_BAND`. A step of 2 m appears in the geometry only at about twenty meters.
- **Before, pixels show it only by the lighting.** The relief is flat, only the light draws it.
- **As you approach, the shape appears in the last meters:** the cornices are digging, and the user sees the summits move.

## The principle: depth in pixels, before the mesh

**Parallax by occultation,** the standard engine technique: the pixel follows its viewing radius in the relief and takes materials at the point where the radius touches the surface.

- **It shows only the relief that the mesh does not carry yet:** the whole relief, less its portion carried, `gMeshReach` times the relief filtered to the grid cell. As the mesh takes it, the parallax disappears by itself. The transition from one to the other does not change the shape seen.
- **The relief followed:** that of the rock, the tile of 8 m, the tile of 64 m and the stratigraphic column. They are the ones who carry the cornices. Sand, grass and scree keep their relief in the lighting alone: a few centimeters.
- **For the cost:**
  - the dominant rock family only;
  - the dominant projection plane only;
  - twelve steps, then a refinement;
  - only on the rock, and only where the residual relief exceeds the pixel.
- **What does not change:** the depth of writing, so the silhouettes against the sky, which remain those of the mesh. They will come with him.

## The measure

- **The view of the cornice,** from `2182.0 31.16045 8.58814 1.9 -17.1` to `2181.5 31.16051 8.58812 2.3 -11.8`: the shape must be seen from 11 m and no longer arise.
- **The benchmark of jitter** on the same positions.
- **The cost of rendering** at the discovery, at the site of the rock and at the cornice.

## Validation criteria

- **The cornice has its depth from 11 m,** and the transition to mesh is no longer visible.
- **No jitter in addition.**
- **Cost:** less than 1 ms of additional rendering.

## Results of the first version

- **The cornice has its depth from 11 m:** the hollow under the plate is already visible, as at 5 m. Without parallax, it only appeared with geometry.
- **What is followed:** the 64 m tile and stratigraphic column, less their share carried by the mesh. The tile of 8 m, a few tens of centimeters, remains in the lighting.
- **Eight steps,** then an interpolation of the contact point. The parallax is erased where it would move the point less than three to six pixels.
- **Cost,** same build with and without parallax, at least three passages: +0,8 ms to the observation, +1,0 ms to the cornice and the rock site, nothing at 56 km. Within budget.
- **jitter :**

| With / without smoothing | No Parallel | With |
|---|---|---|
| Corniche, 11 m | 0,17 / 0,89 | 0,22 / 1,41 |
| Corniche, 5 m | 0,31 / 1,84 | 0,34 / 2,12 |
| Constat | 0,39 / 2,78 | 0,40 / 2,83 |

- **To do if cost is a problem:** a single column calculation per step instead of one per family, or fewer steps for distant pixels.

## The tool: benchmarkss that no longer take the focus

- **Captures and benchmark from jitter render without displaying the window.** The executable writes its title to `<capture>.txt`, which `tools/capture.ps1` reads back.
- **Cost measurements are compared between builds of the same generation:** a hidden window is not limited by vertical sync, which changes the measured GPU times.
