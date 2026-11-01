# Climatic shrubs

**Status: validated in the state by the user the 2026-10-27; threshold of the benchmark quality not satisfied.**
- Continuation of `vegetation-planetaire.md`; base `piste/arbustes-climatiques-base`, on the initial commit.
- Integration on `main`, milestone `jalon/24-vegetation-detaillee-main`.
- Visual acceptance allows this integration with the deviations of benchmark recorded; it does not change the metric or its reference.
- The performance optimization phase is delayed: `optimisation-vegetation.md`.

**Diversity:**

| Family | Port and foliage | Height relative to instance |
|---|---|---:|
| Boréale | tufts low irregular, small leaves | 0,65 |
| Desert | Side forks, spaced grey-green bouquets | 0,85 |
| Steppe | Spread branches, fine foliage, some erect stems | 0,60 |
| Mountain and tundra | Horizontal arms, small leaves in low cover | 0,30 |
| Moderate | tufts branched deciduous trees, multiple lobes and perforations | 1,00 |
| Tropical | Stems offset, large alternate curved leaves | 1,15 |

- Two architectures per family; variant and orientation come from the stable seed.
- The twelve models have 2 492 to 4 272 triangles each, versus 13 406 for the previous bush.
- The twigs are connected; the leaves are cut surfaces, not opaque envelopes.
- The textures come from Poly Haven's Searsia Lucida, under CC0; the catalog represents game archetypes, not twelve identified botanical species.
- The two shafts remain identical to those of `volume_look_normals`.

**Climate coherence:**
- The engine reads the growing season, aridity, coniferous share, temperature and exposure already used by the vegetation.
- It first reserves the cold and exposed forms, then the boreal, arid, steppe and humid tropical; the rest is temperate.
- Weights are continuous, positive and sum 1; no minimum weight imposes a temperate bush in the desert.
- The thresholds are an artistic adjustment on these climatic fields; they are neither geographical boundaries nor a law of distribution by species.
- The mountain is recognized by the cold and exposure; no universal absolute altitude defines it.
- The low port references are the [Denali shrubs](https://www.nps.gov/dena/learn/nature/plants-by-form.htm) and the [Alpine suns](https://www.nps.gov/articles/000/little-willows-at-great-heights.htm). The narrow foliage of dry environments is described by the [US Forest Service](https://research.fs.usda.gov/feis/species-reviews/artcal).

**Conservation of population:**
- Neither the seed, nor the position, nor the source size, nor the acceptance, nor the scope change.
- The family occupies `axisY.y = 1 + famille` for only climatic shrubs; the spread factor is decoded separately.
- Model heights change the drawn port; presence thresholds keep the source size.
- The maillage/imposteur relay takes into account the size of the model; the cover height diagnosis takes the average of the families. The distant cover of shrubs remains superficial, without precise vertical parallax.
- `MYPLANETENGINE_OBJECT_LIST` can export seeds and source positions into `<capture>.plantes` for exact comparison on the same binary.

**The limited cost:**
- The fourteen models share the six regions of instances of 524 288 elements, 192 MiB in total.
- The GPU counts patterns, calculates prefixes, and disperses instances; each family receives a subrange of the two bush regions.
- There is no extra long queue per family.
- An indirect command contains the address of the SRV of the sub-range and the drawing; `SV_InstanceID` starts from zero, independent of `StartInstanceLocation`.
- Drawings are grouped by representation; the GPU ignores commands with zero instance count, without decision based on an old CPU counter.
- The small command and counter buffer occupies 1 056 bytes; additional patterns and textures have their own cost.
- The histories meters remain six aggregates; `model_counts`, `family_counts` and `queue_bytes` detail the catalog.

**Data:**
- Source: `assets/foliage/climate_shrubs_v2/`.
- Reconstruction: `python tools/foliage/arbustes_climatiques_v2.py --preview`, then `--final`.
- `shrubs.txt` starts with `FOLSHR01 6 2`, then the twelve files in order family and variant.
- The geometry, materials, impostors and visibility formats remain those of `assets/foliage/README.md`.
- The engine finds it alone: `MYPLANETENGINE_FOLIAGE_ASSETS`, otherwise the first folder of this name above its executable.
- Without a catalogue, no plants: the canopy on the ground everywhere, and the title says “absent vegetation”. The old folding on the three previous models is removed the 2026-10-30.
- The CPU boards give two orientations and a view to the engine allometry; they do not replace a contextual judgment.

**Comparisons:**
- `tools/banc_arbustes_climat.py`, manifest `tools/foliage/arbustes_climat_vues.json`.
- Hidden captures in multiple locations; biome names are confirmed by diagnostics, not assumed from latitude alone.
- Identities are compared between two passes of the same executable; the 2026-10-27, with and without catalog, which the engine no longer allows.
- Time measurement is distinct from identity export, whose readback adds traffic.
- The captures, frozen models and footprints are under `x64/ArbustesClimat/`.
- The earliest related vase forms are preserved in `log/arbustes-climatiques-historique.md`.
- On the fourteen views, the seeds and source positions fines/grossières are identical bit by bit after sorting, with and without catalog on the same executable; the totals by species are also identical, without overrun.
- Four richer neighboring views confirm the boréal/montagne and desert mixtures; both forms are present in sufficiently sampled families.
- The representation buffers go from 262 793 412 to 729 760 876 bytes, out of queue and temporary memory; diversity adds about 445 MiB.
- The call reorganization retains all fourteen BMPs and all accounts in full. Time measurements are sensitive to GPU loads; they do not guarantee a number of FPS in flight.
- On the same optimized executable, medians by location remain close between old catalog and V2: boreal 4,14/4,76 ms, desert 0,75/0,60, scrub 3,10/3,07, mountain 3,67/3,51, edge 6,98/7,44, tropical 8,97/9,08. A single sequence of 24 images per location and a non-randomized order: indicative result, not proof of budget.
- The full benchmark ends the 24 same sites without loss GPU. It fails at two new thresholds compared to the previous candidate: sand scale hole at 50 m (+10,15 %, 158 crops) and soil scale hole at 12 m (+20,83 %, 127 crops).
- The three deviations from the previous experiment remain inherited; user acceptance is not a project threshold success. The canonical at 30 sites keeps fourteen overruns, with different locations.
- Reports: `x64/ArbustesClimat/qualite_v2/comparaison_p95.json`, `optimisation_images.json` and log.

**The flight of judgment:**
- The game starts as it says `lancement.md`; the catalog V2 is the default engine.
- Palette `tools/tests/2026-10-27-arbustes-climatiques.txt`, twelve buttons and F1 to F12: temperate, boreal, desert, steppe/savane, mountain, tropical, two views per group.
- The then launcher and return to the single bush are removed: `log/arbustes-climatiques-historique.md`.
