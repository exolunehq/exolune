# Specification: mineral walls from 100 m to 1 km

Status: searching the 2026-10-23; two separate tracks, rendering first. **In place:** the wall photo and the strata calculated to pixel. **Removed the 2026-10-24:** the broken bands, their faults and the rock families. The method is now the same as `spec-texturage-universel.md`. The options, tests and measures outdated are in `log/spec-parois-minerales-historique.md`. Following on from `log/spec-parois.md`, whose stands remain under the `piste/parois-gradins` tag. The geometry remains at complexplanet: `geometrie.md`.

## The finding

- **Close up, the rugged terrain is suitable.** The tingling and the flicker remain to be settled, later.
- **From 100 m to 1 km, the walls make fabric:** straight, continuous and regular strips on a smooth surface. They do not make mineral.
- **We turn in circles:** colors of the strata, rounded, stands have not changed anything. It is the basic method that is at issue.

## Diagnosis, face to face with photos

![Up, real walls; down, ours at the same distance](images/parois-tissu.jpg)

- **On a real wall, the dominant structure is perpendicular to the strata:** ravines, grooves, diaclases, dark varnish runs.
- **The strata are interrupted there:** crossed in V by the ravines, hidden by the scree and the vegetation of the vires, of variable thickness, displaced by the faults.
- **Colours change by large masses:** red at the bottom, white at the top at Zion, and few frank stripes.
- **The hollows are read by the shadow:** alcoves and ravines are black.
- **In our case, it is the opposite:** the strips are numerous and continuous, and nothing cuts them.

**The method:**
- **We start from the strata to make the wall.**
- **In nature, the wall is born from erosion,** which digs through flat layers. The bands are the consequence: this is the geologists' rule of the Vs.

## State of the art

**The spot erosion filter,** the newest experiment.
- **What it does:** branched ravines and ridges, aligned with the slope, placed on any height function. Each point is evaluated alone, without simulation: fast, adapted to GPU, calculable by pieces. [Johansen, March 2026](https://blog.runevision.com/2026/03/), after [Clay John 2018](https://www.shadertoy.com/view/MtGcWh) and [Rare 2023](https://www.shadertoy.com/view/7ljcRW).
- **The principle:** stripes oriented by the descending gradient, cut into cells at the Worley, fused between neighbors, in octaves that each inherit the slope of the previous one.
- **Traps:** confused direction on crests and flat bottoms, drains that stop halfway down. On a wall, the steep slope makes the direction clear.
- **License:** the reference code is in MPL 2.0. We rewrite it from the description, without copying the code.

**Other procedural experiments:**
- **strata plate broken:** the node [Stratify of Gaea](https://docs.quadspinner.com/Reference/Erosion/Stratify.html) makes local sub-strata between broken plates, not terraces.
- **Diaclases and blocks:** [Paris et al. 2020](https://hal.archives-ouvertes.fr/hal-02926218), [Peytavie et al. 2009](https://diglib.eg.org/handle/10.2312/CGF.v28i7pp1801-1809). Volumetric and offline; transposable in anisotropic Voronoi.
- **Shadow of the Hollows:** the [screen-space shadows by Bend](https://www.bendstudio.com/blog/inside-bend-screen-space-shadows/), delivered in Days Gone.
- **Colours and varnishes:** a noise stretched in the direction of the slope on the albedo, almost free. Physical base: [Dorsey 1996](https://graphics.stanford.edu/papers/flow).

**Games:**
- **The cliffs readable there are photogrammetric meshes:** [Far Cry 5](https://gdcvault.com/play/1025557/Procedural-World-Generation-of-Far), [Valley of the Ancients](https://dev.epicgames.com/documentation/unreal-engine/valley-of-the-ancient-sample-game-for-unreal-engine), [Battlefront](https://gdcvault.com/play/1023272/Photogrammetry-and-Star-Wars-Battlefront).
- **Star Citizen** paves height tiles according to slope and geology ([Adobe](https://www.adobe.com/products/substance3d/magazine/star-citizen-texturing-sci-fi-open-world-game-substance.html)).

**Dismissed:**
- [Dendry](https://www.cs.purdue.edu/cgvlab/www/resources/papers/Gaillard-2019-Dendry_A_Procedural_Model_for_Dendritic_Patterns.pdf): 10 s for 512².
- The neuronal, [Terrain Diffusion 2025](https://arxiv.org/html/2512.08309v3): seconds per region, not per frame.
- [The derivative fBm](https://iquilezles.org/articles/morenoise): smooths out steep slopes.

## Hybrid: free data

**The actual relief, 1 m or better:**
- **[IGN LiDAR HD](https://cartes.gouv.fr/catalogue/dataset/IGNF_MNT-LIDAR-HD):** 0,5 m, Open License 2.0, slabs of 1 km of about 16 MB. Vercors, Calanques, Verdon.
- **[USGS 3DEP](https://apps.nationalmap.gov/downloader/):** 1 m, public domain. Grand Canyon, Yosemite.
- **[swissALTI3D](https://www.swisstopo.admin.ch/en/height-model-swissalti3d):** 0,5 m, free data with mention. Eiger, Lauterbrunnen.

**The trap:** an aerial elevation model has only one height per point. A vertical wall fits in a few pixels. For the wall itself, you need a cloud of points taken from the front:
- **[San Gabriel and San Jacinto](https://doi.org/10.5069/G96H4FKG):** CC0, walls from 10 to 300 m, about 1 000 points per m², 4 GB, with front photos.
- **[El Capitan](https://doi.org/10.5066/P1YT5RK3):** CC0, terrestrial lidar on about 1 km² of vertical granite.

**Surfaces and meshes, CC0 at Poly Haven:**
- **Surfaces:** `marble_cliff_01` to `06`, from 4 to 20 m wall, with displacement.
- **meshes:** `coastal_cliff_04`, a cliff of 87 m.

**Not redistributable in a public repository:** Megascans and Fab, Textures.com.

**The use in our country:** a patch of real relief, of which we keep only the fine details, oriented by the slope, paved without repetition, from 1 to 30 m. **The risk:** the repetition is seen at 1 km.

## Two separate tracks

**Geometry comes from complexplanet** (`geometrie.md`). The problem of walls is first dealt with in the rendering; what changes the form is a separate subject.

### The rendered path: what is in place

Which makes a mineral wall from 100 m to 1 km without touching the shape. Pixels cover from 8 cm to 1 m. Of the five options studied the 2026-10-23, the cliff photo remains. The broken bands, their faults and the ripple of the strata are removed the 2026-10-24 with the rock families, `jalon/16-une-roche`. The options, their measures and the fixes of the first flight are in `log/spec-parois-minerales-historique.md`.

**Proximity geometry is removed from the code** the 2026-10-30, relief of materials and grades; tag `piste/parois-gradins`. The rendering is adjusted to the complexplanet geometry (`geometrie.md`).

**The strata pixel.** Computed by vertex and filtered by the grid cell, the strata, their offset and lenses let their octaves appear in sight when the grid cells shrank: a grid cell covers about 13 pixels. They are calculated in pixels and filtered by their size; geology, regional, remains at the tops (`journal-planete.md`, 2026-10-23). The rule is in `principes.md`.

### The photo of cliff

![Base, then cliff photo: steep wall, mountain at 45°, mountains at 5 km, cornice](images/parois-photo.jpg)

- **The photo:** `marble_cliff_04` of Poly Haven, CC0, a wall of 12,7 m photographed from the front, with vertical fractures and grooves. It is preferred to `marble_cliff_05`, 20 m, more isotropic and top-taken.
- **Where:** the tile of the rock, `ROCK_TILE` = 64/5 m, instead of the generated tile of 8 m; the fine tile remains generated. Since the 2026-10-24, all the rock is this photo, and the rock less than 45° takes `marble_cliff_05`, the same marble taken from above (`journal-planete.md`).
- **What she keeps:**
  - all its wavelengths up to the tile, without the high pass at 50 cm of sand;
  - 30 % of its variations of hue: the strata give the color;
  - 1,2 m of relief per unit, which gives its slopes the standard deviation of the universal rock rule, `STONE_SLOPE_SIGMA`.
- **What we see:** a fractured and grooved material on the steep walls and the cornice, more mineral. From 300 m to 1 km, the bands of strata still dominate.
- **Measures:**
  - jitter with smoothing 0,40 → 0,43, 0,19 → 0,23, 0,17 → 0,16 to the cornice;
  - cost of rendering unchanged;
  - Rock descent unchanged from 800 to 8 km.
- **Near the ground, since 2026-11-09:** its straight joints matched themselves along their length, repetition p95 0.22 to 0.28 at a few centimetres a pixel against the photos' 0.18.
  - The photo is read aside by about 2 cm, faded in between 6 and 3 cm a pixel (`FACE_WARP`): its joints wander.
  - The wall takes shades of 25 and 50 cm, 4 % each (`FACE_BANDS`).
  - Only under 1,000 m above the ground, in their own shader permutations, so no cost higher up (`diagnostic-orbite.md`).

### The geometry track, apart

On a branch, to be taken after rendering, and to be explicitly decided: `geometrie.md`, family "replacement".

**The erosion filter, tried the 2026-10-23,** is set aside: tag `piste/erosion-filtre`. What he gave and cost: `log/spec-parois-minerales-historique.md`.

**Other experiments:** Real relief patches, IGN LiDAR HD slabs in `../donnees-terre/lidar-hd`, out of the depot; sown rocks, `log/spec-parois.md`, option 3.
