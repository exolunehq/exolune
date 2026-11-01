# History of generated textures

**The outdated sections of `../spec-textures-generees.md`,** released the 2026-10-30. The present state is there.

## The other experiments drawn from the comparison, what they have become

- **The gravel and stones sown:** the objects of proximity, `../spec-objets-proximite.md`.
- **The shadows cast by the relief:** the horizon by vertex, `../recherche-ombres-relief.md`.
- **The mist:** the mist of the boundary layer, `../recherche-profondeur-atmospherique.md`.
- **The grass spikes:** never made, `spec-herbe.md`; tufts of spikes generated instead, among nearby objects.
- **Sea near the shore:** the sea FFT, `../spec-mer-fft-spike.md`; beaches, `../recherche-cotes.md`.
- **Depth of field:** not made.

The original text:

### Other experiments taken from comparison

**Outside of path B, but necessary to approach the target:**

- **The pebbles and stones sown in geometry,** step E. This is what weighs the most in the target's foreground, after wrinkles.
- **The shadows cast by the relief.** The engine does not have one: the valleys remain lit. Two experiments: a shadow card in cascades, or a ray throw on the relief.
- **The fog.** Hillaire's aerial perspective is in place, but the target shows a more charged air. The density of aerosols must be adjusted and a valley mist must be added at height. Quick adjustment.
- **The grass and dry shrubs,** in geometry: `spec-herbe.md`, never made.
- **Sea near the shore:** color gradient with depth, waves and foam. A experiment in its own right.
- **The depth of field,** last, if it still serves.

## Step 2: the towers of the generated rock

Before the wall picture, `jalon/15-roche-photo`.

- **Six turns of benchmark on the rock:**
  - **Scales:** a second level of facets of 40 cm surrounded each facet with a shadow. I withdraw.
  - **Slate:** all the boundaries of strata were dug and darkened. Now, only one layer in three is receding, and little.
  - **Craters:** the stones of the scree were disks, cut net when they overflowed their cell. Remade into angular fragments, each with its shrinking Voronoi cell, placed on dust.
  - **Black bars:** the crevices were too dark. Soften up.
- **Condition:** the rock is read in slabs and discrete cracks, but it remains flat. The real relief, in geometry, with contact shadows, becomes the main lever.

## The structure of the rock beyond 8 m

**Removed the 2026-10-24,** with rock families and parallax, `jalon/16-une-roche`: the rock is a single photo, without tile drawn from 64 m.

Status: made the 2026-10-21; to be judged in flight.

**The finding:** the rock tile repeats all 8 m. Viewed from 15 to 50 m, the wall remains a uniform grid of beds and diaclases, without cornices, corridors or spurs.

**The principle: a third tile for the rock, from 64 m in 1024 texels, 6 cm by texel.** It is the counterpart of the fine level, at the other end of the scale.

- **The large beds:** layers of 2 m grouped in beds from 2 to 8 m. Each bed advances or retreats by ±0,5 m and ends in a rounded cornice. The soft beds retreat under the hard ones.
- **Large fractures:** all 4 to 16 m according to the benchmark. Four out of ten are corridors of 0,3 to 1,2 m wide and 0,6 m deep, which cut out foothills.
- **The colors:** a shade by benchmark, and curtains of varnish a few meters wide that flow along the wall.
- **Same reading:** random paving, cells of 32 m, 64 m divide them; biplanar projection, strata turned to the vertical. Multiplied color and occlusion, slopes and heights added, average retained.
- **The mesh carries this relief** where its grid cells allows it, like that of other tiles.
- **The camera:** this relief reaches ±1 m. The height under the camera is therefore read after the relief pass, and no longer before.

**Measurement:** views at 50 m, 15 m and 1,5 m on steep slope, before and after; the benchmark of jitter; the cost.

**Criterion:** from 15 to 50 m, a structured wall and no longer a grid, without jitter in addition, for less than 0,3 ms.

**Results:**

- **From 15 to 50 m,** the walls show cornices, benchmarks recessed, corridors: the grid has disappeared.
- **At close sight,** the cornices cut out their silhouette, and the grass stands on the benchmarks retreating.
- **Cost:** +0,10 to 0,22 ms on rock.
- **jitter, rock at 3 m, with and without temporal smoothing:**

| Variant | Rock at 3 m | Dry soil at 1,3 m |
|---|---|---|
| Before the tile of 64 m | 0,05 / 0,27 | 0,06 / 0,39 |
| Tile of 64 m, benchmarks in steps | 0,12 / 0,58 | 0,08 / 0,51 |
| benchmarks connected in ramps of 0,6 m, retained | 0,10 / 0,52 | 0,08 / 0,51 |
| Without relief in the mesh | 0,04 / 0,25 | 0,05 / 0,35 |

- **Where does the jitter come from:** from the relief of ±1 m that the mesh carries. Filtering to 16 grid cells instead of 8 only gains 0,02; bringing the relief to the grid cells of 8 m does not change anything.
- **It remains low:** 0,10 on 255 on average, below the 0,17 of the filtering at 2 grid cells dismissed earlier. It concentrates on the edges between rock and grass. To be judged in flight.
- **The camera** now reads the ground height after the relief pass: no fixed margin of 30 cm.
