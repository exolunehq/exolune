# Climate shrubs, V2 experiment — October 27, 2026

- **Models:** six stylized archetypes, two geometries each. Branching varies with climate: boreal tuft, desert forks, steppe tuft, montane cover, temperate lobes and large alternate tropical leaves. These are not exact botanical species.
- **Source:** [Searsia Lucida](https://polyhaven.com/a/searsia_lucida), James Ray Cock and Jenelle van Heerden, [CC0](https://creativecommons.org/publicdomain/zero/1.0/). The twelve models share its leaf photography and bark; their maps are adapted and recolored.
- **Wood:** color, normals and mask copied from source tile 0; opaque alpha and zero transmission. `contact_bois_cpu.png` shows a close-up of the bases and the bark strip used by the UVs.
- **Budget:** 2,492 to 4,272 triangles; two 512² tiles; branches use material 0, leaves material 1. The large tropical leaves use subdivided curved cards.
- **In-engine allometry:** maximum width 1.1 times instance size; height multiplied by 0.65, 0.85, 0.60, 0.30, 1 and 1.15 respectively. `contact_runtime_cpu.png` applies these factors at equal instance size, with simplified CPU lighting, from the front and at 90°. `contact_cpu.png` and `contact_cpu_cote.png` show normalized models before allometry.
- **Files:** `shrubs.txt` manifest, meshes, materials, 64³ volumes, impostors and two visibility sidecars. The pine and broadleaf are copied identically from `volume_look_normals`.
- **Rebuild:** after preparing `game_shrub` and `volume_look_normals`, run `python tools/foliage/arbustes_climatiques_v2.py --preview`, `python tools/foliage/arbustes_climatiques_v2.py --final`, then `python tools/foliage/arbustes_climatiques_v2.py --runtime-preview`. Dependencies: numpy, Pillow, numba.
- **Limit:** the contact sheet is a simplified preview; appearance and performance must be reviewed in the application.
