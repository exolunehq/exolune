# POC: voxelized cloud

**Log since 2026-10-30:** POC closed, replaced by published references of Frostbite spikes. Sources and launcher of the test: tag `piste/nuages-orbite-spike`.

**Goal:** to quickly obtain a voxelized volume to judge in flight, next to the validated procedural POC.

**User feedback, 26 October:** “it works”. The [planetary test](spike-nuages-voxel-planete.md) is stopped on October 27; a [new scoping](spike-nuages-reference.md) compares published technical bases.

**Isolation:** a branch apart, today in the tag `piste/nuages-orbite-spike`. Base `7298330`.

**State:** compiled in Debug x64. A hidden capture 128³, in time 0, is produced in 1 280 × 720 without error. The cloud is visible; no verdict of flight stability or final performance is given. The user performs end to end testing.

**Binary:** `x64/NuageVoxelPoc/MyPlanetEngineVoxel.exe`. The fingerprint SHA-256 `658C6FC9337E7D9B0B1E281A1301295CEFBDCF10D9F5CD8ABDE0713C907057C4`. Capture and start control: `x64/VoxelStartup/voxel128.png` and `startup.json`.

**Principle:**

- Store the final density of the same four-lobed cloud in a 3D R32_FLOAT texture.
- Keep the local cube `[-2,4 ; +2,4] km` attached to the cloud reference frame.
- Generate the volume from the same procedural function, with the current weather.
- Recalculate when weather phase changes; reuse volume during break.
- Read density by trilinear interpolation, without mipmap.
- Keep the global wind, view and sun rays, the lighting and the composition of the POC.
- Compare the two density readings at identical exposure and exposure time with C.

**Resolutions:** 128³ by default, about 37,8 m between samples and 8 MiB density. Option 256³, about 18,8 m and 64 MiB. These sizes exclude other engine resources and allocation alignment.

**Run, once compiled:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuage-voxel-poc.ps1
```

**Variants:** `-Static` to check the approach at fixed time; `-Size 256` for the finer grid; `-Time 60` for another initial time; `-Build -NoLaunch` for compile only.

**Controls:** C voxel/procédural; Space pause/reprise; B silhouette; V weather ×5; F1–F8 palette views. Arrows, Page haut/bas and mouse as in the previous POC.

**Brief manual test:** freeze time, move to the outline and enter the cloud; switch C on the same views; resume weather; try top and other side. Record contour changes, blur, blocks and fluidity.

**Scope:** first local dense volume. No planetary coverage, hollow brick, resolution transition or final performance validation. The cost of animation reconstruction is part of the trial. The voxelss do not prove stability or distant transparency on their own.
