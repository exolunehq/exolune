# Diverse vegetation catalogue

**Sources and licenses**
- Legacy 29-model prototype; the default technical catalogue is [game_biomes_v1](../game_biomes_v1/README.md).
- Models 0–13 retain the credited baseline in [game_origins.md](../game_origins.md) and [game_shrub_origins.md](../game_shrub_origins.md).
- `fir_open`, `fir_dense`: [Fir Sapling](https://polyhaven.com/a/fir_sapling), Rob Tuytel and Rico Cilliers, CC0 1.0; source meshes a and c.
- `broadleaf_2`–`broadleaf_5`: [Free Realistic Tree 10](https://opengameart.org/content/free-realistic-tree-10), Rakshi Games, CC BY 3.0; the four additional prefabs from the original pack.
- `edge_shrub_a`, `edge_shrub_c`: [Shrub 03](https://polyhaven.com/a/shrub_03), Rico Cilliers, CC0 1.0.
- `leafy_shrub`: [Searsia Lucida](https://polyhaven.com/a/searsia_lucida), James Ray Cock and Jenelle van Heerden, CC0 1.0; source mesh g.
- `sorrel_a`, `sorrel_c`: [Shrub Sorrel 01](https://polyhaven.com/a/shrub_sorrel_01), Rico Cilliers, CC0 1.0.
- `grass_tall_a`, `grass_tall_c`: [Grass Medium 01](https://polyhaven.com/a/grass_medium_01), Rob Tuytel and Rico Cilliers, CC0 1.0; tall variants a and c.
- `flower_a`, `flower_d`: [Flower Empodium](https://polyhaven.com/a/flower_empodium), Jenelle van Heerden and Rico Cilliers, CC0 1.0.
- Retain these credits and the [CC BY 3.0 terms](https://creativecommons.org/licenses/by/3.0/) with the adapted Rakshi models.
- The [CC0 dedication](https://creativecommons.org/publicdomain/zero/1.0/) applies to the Poly Haven sources.

**Adaptation**
- Normalize the source reference frames and height; preserve texture UVs and artist geometry.
- Reduce the two fir meshes to at most 48,000 triangles in background Blender, with UV interpolation.
- Convert Unity packed normals and cutout thresholds for the four broadleaves.
- Preserve normal, roughness and opacity maps; use 512-pixel material tiles for ground plants and 1,024 for woody models.
- Bake each model's own multiview impostors and visibility data.
- The architectural climate groups do not claim a botanical distribution of terrestrial species.

**Rebuild**
- `python tools/foliage/prepare_biomes.py`; the baseline `../climate_shrubs_v2` must already exist locally or beside the repository.
- `tools/plantes.ps1` now builds the rooted game prototype; use the explicit command above to reproduce this legacy catalogue.
- Requires numpy, Pillow, numba, UnityPy and Blender CLI during preparation; none at runtime.
- Source URLs, authors, licenses and SHA-256 hashes: `tools/foliage/sources_biomes.json`.
- `biomes.txt`: `FOLBIO01 29`, then folder, renderer group and leaf-material bitmask in fixed model order.
- Readiness is published after cooking all models; raw and cooked binaries remain ignored by git.
- Mesh/material and cooker fingerprints invalidate derived-data caches.
- `catalogue.png` is a neutral model sheet, not an in-game lighting reference.
