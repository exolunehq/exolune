# Climate shrubs — October 27, 2026

- **Data:** six stylized archetypes, two distinct branching patterns per family: boreal, desert, steppe, montane, temperate and tropical. Structures and proportions vary; they do not claim to represent exact botanical species.
- **Source of leaves, bark and PBR maps:** [Searsia Lucida](https://polyhaven.com/a/searsia_lucida), James Ray Cock (modeling), Jenelle van Heerden (photography), [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). Leaf cards, normals, occlusion and roughness come from `game_shrub`; colors adjusted and atlas resampled.
- **Geometry:** connected generated branches, leaf cards distributed along twigs and oriented in three dimensions. Each variant has its own seed and branching pattern. No solid foliage volume is added.
- **Budget:** 2,368 to 4,368 triangles; two 512 × 512 tiles per model. Material 0 is for branches and 1 for leaves.
- **Lighting:** the same `FOLLIT01` and `FOLIL001` formats, six directions and sixteen sky rays; 64³ volumes and 60 impostor views at 128² generated on the CPU.
- **Manifest:** `shrubs.txt` lists the twelve directories in the order of the six families, variant 0 then 1. The pine and broadleaf are copied unchanged from `volume_look_normals`.
- **Rebuild:** after preparing `game_shrub` and `volume_look_normals`, run `python tools/foliage/arbustes_climatiques.py --preview`, inspect `contact_cpu.png`, then run `python tools/foliage/arbustes_climatiques.py --final`. Dependencies: numpy, Pillow and numba.
- **Limit:** these families share the same photographic leaf source; their appearance in motion and in context must be checked in the engine.
