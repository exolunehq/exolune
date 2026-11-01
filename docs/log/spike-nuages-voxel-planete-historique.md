# Planetary Spike voxel: History

**Stop, 27 October 2026:** the planned V3 is interrupted before shader implementation and compilation. Native preparations are saved, then the sources and launcher are returned to V2. The [new scoping](spike-nuages-reference.md) is based on published technical references.

**V1, 26 October 2026**

- A 128³ texture repeated on six faces of 127 × 127 cells, i.e. 96 774 large benchmarks.
- Positions and density calculations in double precision precision at each viewpoint and sun.
- Binary `x64/NuageVoxelPlanete/MyPlanetEngineVoxelPlanete.exe`, SHA-256 `EA23375D6CA7975B23B471462AB6EBD3D27383E284F41D331290BE66E089EE68`.
- Two initial captures compliant with boot: `x64/VoxelPlanetStartup/`.
- Their titles indicated 74,89 ms of rendering GPU to 8 000 km and 58,67 ms in approach; spot measurements, without separation terrain/nuages.
- User feedback: about 10 FPS in both C modes; repeated blocks preventing judging the distant.
- C changed the density source, with the same path and the same lighting in both modes.
- Decision: move planetary calculations out of loops, add a real cloud cut-off and pass measurement, then replace the large uniform blocks with a thinner population and regional coverage.

**V2, limited digital control**

- Digital weather anchor of 32 km per interval, with input and cell references calculated in double precision precision.
- Loops use float local offsets; full planetary positions do not float for density.
- CPU point control on 2 000 shell point pairs: maximum error of altitude 3,92 cm, local coordinate 5,61 cm, zero cell identity difference.
- This check checks arithmetic; it does not replace images or flight stability validation.
- Report `x64/VoxelPlanetV2Startup/local-precision.json`.

**V2, first optimization without wide placement**

- Two static captures: orbit 10,36 ms/frame of which 6,11 ms clouds+air; approach 6,69 ms/frame of which 3,99 ms clouds+air.
- Cloudless orbit control: 9,12 ms/frame, including 0,73 ms for air. Do not subtract frame times between captures to isolate a pass; the 6–7 timestamps directly measure that pass.
- Report `x64/VoxelPlanetV2Startup/startup.json`.
- The centers still moved only faint in their cells; the rows remained visible.
- Decision: shift the centers largely, sum the neighborhood 3×3 and allow for overlaps. This richer placement increases the cost compared to this first optimization.

**V2, wide placement and user feedback of the 27 October 2026**

- Six faces of 1 023 × 1 023 fixed cells; a single family of shared density.
- Center shift up to ±2,1 local units, free rotation, variable dimensions and sum of nine neighbors.
- Two noise functions of regional coverage determine the presence; the silhouettes remain those of the four lobes of the POC.
- Binary `x64/NuageVoxelPlaneteV2/MyPlanetEngineVoxelPlaneteV2.exe`; EXE `4F02017258B14A9B793EF85C74F3E70BECA3B61A51CDEFDE457F1B1698495C4F`, shader `C9F77F3303FB6FC471B1689A5E79BE2D8C1CE0A9094FEAD1E8104A8996E4C6F3`.
- Captures `x64/VoxelPlanetV2Placement/`: approach 13,66 ms/frame of which 11,34 ms clouds+air; orbit 26,97 ms/frame of which 24,23 ms clouds+air.
- Two static views in 720p; no flight stability validation.
- User feedback: acceptable top view, horizontal stripes and flicker seen from the side; repetition of the same family, cost still high, voxel benefit not demonstrated.
- The course aimed at `24 m / max(vitesse radiale, 0,05)`; it could reach 480 m before the ceiling of 512 step, which further increased the pace of long journeys.
- This rule subsample the lateral structures relative to the 37,8 m of the local volume 128³.
- Decision: replace this rule, skip the empty supports, introduce a LOD of path and light, then three profiles common to bake and direct calculation.
- The V2 palette is kept as `tools/tests/2026-10-26-nuage-voxel-planete.txt`; the V3 uses a new palette.
