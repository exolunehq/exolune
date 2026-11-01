# Spike: voxel clouds on the planet

**Archive of 27 October 2026:** V3 interrupted at user request before shader implementation and compilation. The sections below describe the planned plan, not an available outcome. The launcher and native sources have been returned to V2; its limits and measurements are included in the [historical](spike-nuages-voxel-planete-historique.md). The new framing is in [reference research](spike-nuages-reference.md).

**Goal:** quickly compare a voxelized density and its direct calculation during a flight from ground to orbit.

- Flight checks remain the responsibility of the user.
- The controls in this iteration are limited to compilation and a few hidden captures.
- A branch apart, today in the tag `piste/nuages-orbite-spike`.
- The old tests and measurements are in the [historical](spike-nuages-voxel-planete-historique.md).

**V3:** correction of lateral path, variety of profiles and cost reduction with distance.

- The V2 had side stripes and repeated the same family.
- Its pitch depended on the radius inclination and could exceed 480 m on long journeys.
- The V3 removes this rule and the 512 ceiling not that stretched the samples.
- Empty areas are skipped according to geometric supports, with margins; a zero density sample is not enough.
- Weather and formation identities remain independent of the camera.

**Common field for both modes:**

- Six faces of spherical cube each carry 1 023 × 1 023 fixed cells.
- Offsets, orientations and dimensions depend on these identities.
- The 3×3 neighborhood retains the overlays.
- The regional cover opens holes and mixes three profiles: cumulus, stratocumulus and fragmented sheets.
- This is a simplified visual distribution, without weather simulation.
- The three density sources are used for bake and procedural mode.
- Wind drives the common reference frame; weather animates the profiles.
- Planetary references are calculated in double precision precision; loops use float local offsets.

**Storage:**

- Planetary texture `N × N × 3N`, three contiguous volumes on Z.
- Density `R32_FLOAT`, 24 MiB to N=128 and 192 MiB to N=256.
- Each family uses its own texels centers; no interpolation crosses a family boundary.
- The validated local volume retains its N³ texture and its own binary.
- The texture is reconstructed at current weather and then published as a whole.

**Launcher:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuage-voxel-planete.ps1
```

- Binary: `x64/NuageVoxelPlaneteV3/MyPlanetEngineVoxelPlaneteV3.exe`.
- Options: `-Static`, `-Time 60`, `-Size 256`, `-Clear`, `-Build -NoLaunch`.
- C: compare voxel and procedural with the same field and path.
- N: cut clouds and bake them; keep air and land.
- Space: freeze the weather; B: opacity; V: weather speed ×5.
- Palette `tools/tests/2026-10-26-nuage-voxel-planete.txt`: F4 side profile, F5 interior, F7 horizon, F8 whole planet; F9 to F11 change region.
- The title gives the weather GPU "clouds + air", bake included when it is executed.

**Limits of judgment:**

- One LOD path is not enough to properly filter formations smaller than one pixel.
- The air composition and the lighting remain approximations of the spike.
- A static capture does not validate the flicker in motion.
- No advantage of voxels is acquired; C must show whether the density cache justifies its memory cost and reconstruction.
