# Specification: Rock walls, procedural or hybrid

**In the log:** the grades, options 1 and 2, disabled the 2026-10-23, their code removed the 2026-10-30, `WALL_RELIEF` included. They remain at the `piste/parois-gradins` tag.

Status: options 1 and 2 tried the 2026-10-23, to be judged in flight. Results at the end of the file.

## The finding

Vertical walls are not convincing, from 15 to 150 m: smooth surfaces draped like a fabric, striped with colored stripes. No blocks, no overhangs, no steps in geometry, no cones of scree.

## What the comparison showed

**The procedural and hybrid test,** with the scan `dark_rock_02` instead of the rock of 8 m, on five walls (`spec-hybride-scans.md`, planks of this spec):
- **less than 10 m,** the scan gives fine cracks, on the red rock;
- **from 15 to 150 m, nothing changes.**

**The defect is not the matter of close, but the scale of 2 to 100 m, and it is geometry:**
- **a height field has only one height per column:** no overhang, a smooth silhouette;
- **a vertical wall has only two or three vertices in height:** triangles stretch;
- **our strata are color strips and material relief of one to two meters,** on a smooth complexplanet relief at these scales.

**A photo alone can't do anything:** free scans are 2 m wide; cliff photos from 10 to 100 m are rare under free license, and a vertical wall on a height field would stretch them.

## What others do

- **The delivered sets put rock objects on the ground:** photogrammetry kits or Megascans, connected to the ground by normals and a depth screen. Placement by slope and curvature rules, often on the GPU: [Horizon Zero Dawn](https://www.guerrilla-games.com/media/News/Files/GDC2017_VanMuijden_GPUBasedProceduralPlacementInHorizonZeroDawn.pdf), [Ghost Recon Wildlands](https://80.lv/articles/procedural-technology-in-ghost-recon-wildlands/), [Far Cry 5](https://80.lv/articles/houdini-procedural-world-generation-of-far-cry-5/), [Star Citizen](https://starcitizen.tools/Planet_Tech_v5).
- **[Outerra](https://www.gamedeveloper.com/programming/horizontal-fractal-displacement) moves the steep peaks horizontally,** in the direction of the slope, by a noise fractal: the rock bombs or digs.
- **Search:** [triplanar, Weiss et al. 2020](https://cs.cit.tum.de/cg/research/publications/2020/triplanar-displacement-mapping); [implicitly stratified cliffs, Paris et al. 2019](https://perso.liris.cnrs.fr/aparis/public_html/projects/paris2019_3D.html); [fracture blocks, Paris et al. 2020](https://hal.archives-ouvertes.fr/hal-02926218).
- **Discarded for us:** voxels and marching cubes at each frame, too expensive; simulated erosion, which requires a stored state; parallax only, which does not change the silhouette.

## The options

**1. The geological cliffs, in the relief itself.** Geology makes the walls: the hard beds hold in cliff, the soft beds collapse in slope, hence the profiles in grades.
- **The stratigraphic column already exists,** per vertex; its formations of 10 to 60 m become relief stages, in the calculation of the mesh, on steep slopes.
- **The silhouette breaks by real steps,** and the strata are no longer painted strips: they are the form.
- **Universal:** any layered rock of the planet, at any distance, filtered like the rest of the relief.

**2. Horizontal displacement of steep peaks.** In the direction of the slope, through a noise of blocks and fractures: the wall bombs, ditches, takes foothills and false overhangs.
- **Inexpensive:** a few octaves on the only steep peaks.
- **The known traps:** recalculate the normals on the displaced positions, and the jitter of a relief carried by the mesh, that our rules already frame (`principes.md`).

**3. Rocks sown in real volumes.** Blocks, pillars and scree, instantiated on the GPU by a hash above a slope threshold, connected to the ground.
- **The only true volume 3D,** with overhangs and shadows.
- **The most expensive** in calculation and code: a new pipeline.

**4. The hybrid for the material of the walls.** Cliff scans on the tile of 8 m.
- **After geometry only:** alone, it only changes cracks within 10 m.

## Recommendation

**The options 1 and 2 together, then 3.**
- They attack the cause, geometry, instead of painting.
- They remain in the concept, all recalculated at each frame, without memory.
- The 1 option connects what we see from far away, the strata, to what we see close up, the stands: the same structure at all scales.
- The hybrid of matter remains open afterwards, as a layer of detail.

**The measurement:** the views of walls of this spec, at 15, 50 and 150 m, next to the photos `cible-*.jpg`; the benchmarks of jitter, of descent and of ridges; the cost of calculation of the mesh.

## Results of options 1 and 2

**What is in place:**
- **Option 1, the stairs:** each hard bed of the stratigraphic column makes a cliff on the lower third of its height, `WALL_CLIFF`, then a replat. The relief passes through the height: the ground remains a field of height.
- **The replats rest at the angle of scree,** 34°, `WALL_REPOSE`; the cliffs take the rest of the climb. A wall no steeper than his scree has no steps; the steeper it is, the more they are marked.
- **The sharing:** the mesh carries the rounded stands on 16 grid cells, the pixels illuminate the rest. From close up, the stands are in the silhouette; from far away, in the light only.
- **Option 2:** ravines and foothills by a noise stretched vertically, rounded masses of granite, in the mesh, up to the grid cells of 16 m. Without jitter measurable.

**What was discarded:**
- **The horizontal displacement of Outerra:** on a height field, the displaced vertices are folded. Black holes, saw teeth.
- **Net stands in the mesh alone:** the best rendering, but 2,5 times more than jitter. Rounded on 16 grid cells, they almost do not see each other anymore.
- **Flat replat:** every steep slope became a zebra staircase, especially from afar.
- **A fault corrected on the way:** the slope added in the light must be multiplied by the vertical component of the normal. Without this, the replats leaned back and went black.

**Measurements,** jitter with and without smoothing, base and walls:
- Very steep wall, `1391.1 -11.04542 50.06777 2.6 55.3`: 0,37 / 2,47 → 0,61 / 5,05;
- mountain at 45°, `3756.3 -39.55694 12.77814 -13.1 -141.1`: 0,19 / 1,54 → 0,22 / 1,67;
- corniche, `2182.0 31.16045 8.58814 1.9 -17.1`: 0,18 / 1,12 → 0,21 / 1,23;
- mountains at 5 km, `4657 -14.9635 119.991 10`: 0,11 / 0,61 → 0,16 / 0,73.
- **Rock descent:** unchanged from 800 to 8 km.
- **Cost:** +0,2 ms rendering on the steep wall, +0,2 ms calculation at the cornice.

**The jitter remaining,** on the very steep walls:
- **Dismissed as cause:** the rounding of the edges to the pixel, the normal used, the part of the mesh, the size of the grid cells, the fine height of the pixel. None reduces it.
- **In part:** the illuminated replacings make this wall clearer by 36 %, and the gap between two images increases with clarity.
- **experiment following:** the height `s` of the grades, interpolated between the sliding vertices.

**Settings:** `WALL_RELIEF` 1, 0 disables all; `WALL_MAX_CELL` 16 m; `WALL_SLOPE` 0,55 to 1; `WALL_CLIFF` 0,35; `WALL_REPOSE` 0,67.

**Continue:** from 100 m to 1 km, the rendering remains straight, "fabric". The method is reviewed in `spec-parois-minerales.md`.
