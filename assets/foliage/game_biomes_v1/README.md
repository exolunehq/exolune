# Rooted game vegetation prototype

**Status**

- Thirty-one models; technical validation passes, artistic acceptance remains open.
- The user requests a fresh generative foundation; `../../../docs/recherche-generation-vegetale.md`.
- This catalogue still adapts the previous source libraries; it must not be presented as original neural generation.

**Sources and modifications**

- Three conifers derive from evolveduk's [Pine Tree](https://sketchfab.com/3d-models/pine-tree-d45218a3fab349e5b1de040f29e7b6f9), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- Five broadleaves derive from Rakshi Games' [Free Realistic Tree 10](https://opengameart.org/content/free-realistic-tree-10), [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).
- The twelve baseline shrubs retain [their Searsia credits and transformations](../game_shrub_origins.md).
- Extra shrubs, sorrel, grasses and flowers retain [the diverse-source credits](../biomes_v1/README.md).
- The two added ferns use [Fern 02](https://polyhaven.com/a/fern_02), Rob Tuytel and Rico Cilliers, CC0; meshes b and c.
- Strengthen stems, arrange leaf bouquets, adjust normals and gently warm materials.
- Add a flared collar and seven volumetric roots per tree; adapt two game-pine crown architectures.
- Bake each final mesh's own impostor, volume and lighting data.
- Keep source authors and licenses with all redistributed adaptations.

**Reproduction**

- `python tools/foliage/prepare_vegetation_jeu.py` uses the baseline beside the repository by default.
- `--base assets/foliage/climate_shrubs_v2` selects a locally built baseline.
- `tools/plantes.ps1` prepares the baseline and this extension.
- Pinned source files: `tools/foliage/sources_vegetation_jeu.json` and its referenced baseline manifests.
- Dependencies: numpy, Pillow, numba and UnityPy; no runtime decoder or modeling application.
- Raw and cooked binary files stay outside git; readiness is written after the complete cook.
- `recipe.json` records model geometry counts; `catalogue.png` is a neutral source sheet.

**Format additions**

- `biomes.txt`: `FOLBIO02 31`, followed by folder, renderer class and leaf-material bitmask.
- Tree `form.bin`: `FOLFORM1` and four little-endian floats, 24 bytes total.
- Fields: base radius, root crest height, root reach and crown width before roots are added.
- A fractional material value of `.25` marks root vertices while preserving their integer bark layer.
- The engine fits these root vertices to cached terrain contacts; source and cooked distant shapes retain the same crown scale.
- Full behavior and limitations: `../../../docs/spec-diversite-vegetale.md`.
