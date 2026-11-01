# Regional cloud formations

**Log from the 2026-10-30:** spike closed, replaced by the weather on the whole sphere, `../spec-nuages.md`. Launcher and assets of the test: tag `piste/nuages-orbite-spike`.

**State, 27 October 2026:** First Regional Test Ready for Flight. Map inspected, three variants compiled and four hidden captures verified. The extended distribution is visible; the far rendering retains repetitive grain and cirrus of the striations.

**Return in flight:** the user judges the other clouds correct and requests to reduce the too regular cirrus. The [spike orbital](spike-nuages-orbite.md) continues this work; this regional version remains frozen as a witness in `x64/NuageFrostbiteRegionalTemoin/`.

**Launcher:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-region.ps1
```

- F1-F4: same centre from 800, 200,80 and 30 km; F11:500 km.
- F5–F7: two cumulus fields and the blanket; F8–F9: cirrus; F10: clear; F12: low sun.
- `-Vue Meteo` opens the fixed map; `-Vue Opacite` opens the 3D transmission; B switches the opacity to normal rendering.
- `-Temoin` opens the local scene frozen of the three families, with its palette.
- C: qualité48/24 m; Space: pause/reprise; V: weather×1/×5; weather frozen at start.
- `-Build -NoLaunch -Vue Rendu`, `Meteo` or `Opacite` recompiles the selected variant.

**Objective:** to judge larger and more numerous formations at different distances, keeping local forms as reference.

**Distribution:**

- Local weather map of1200×800 km, origin0,5°/161,775°; fixed tangential projection on spherical layers.
- Fragmented cloud cover, irregular front, regions of cumulus clusters, extended cirrus and large clearings.
- Variations at multiple scales act on the weather map.
- Vertical profiles, textures3D, lighting and integration of local families are preserved.
- The map is an explicit artistic choice, inspired by Frostbite's météo/type/forme cut-out; no planetary weather simulation is claimed.

**Isolation:**

- Sources, data and binaries of previous trials retained.
- Witness of the three families: `x64/NuageFrostbiteFamiliesTemoin/`, forty copied files, printed in `witness.json`.
- Three 3D textures copied entirely from `assets/frostbite-families/`; only the 2D weather texture changes.
- Weather R: low cover; G: type nappe/cumulus; B: cirrus; A unused.
- Medium coverage Mip1, conservative maximum Mips2+; averaged type profile.
- Expanded acceleration envelope and bounds to regional support; no path beyond the depth of field.
- Segments of both layers remain sorted along the radius.
- Data, parameters, printouts and test points: `assets/frostbite-regional/regional-manifest.json` and `regional-probes.json`.
- Legended map: `assets/frostbite-regional/regional-weather-art-preview.png`; channel map and central cropping provided next to it.

**Remission in main:**

- First examine the distribution map viewed from above.
- Then compile the regional rendering and make some hidden captures over several locations and distances.
- Pallet in `tools/tests/2026-10-27-nuages-region.txt`; launch by `tools/nuages-region.ps1`.
- B: opacity; C: quality; Space: weather break; V: weather ×1/×5.
- In-flight checks belong to the user; no extended benchmark.

**Control performed:**

- Three DXC builds successful; pre-existing binary shift warning in `Materials.hlsli`.
- Four captures: region from 800 and 80 km, cumulus seen from 10 km and blanket from 6 km; `x64/RegionalPreview/report.json`.
- Three3D textures identical to the sources, low density recipe unchanged,11 mips weather compliant, mipsR/B presence conservatives and blank edges checked.
- Full witness and frozen sources checked intact.
- Spot clouds+air:2,93 ms at 800 km,5,59 ms at 80 km,9,24 ms on the cumulus field,5,15 ms on the table; GPU split, no statistical comparison.
- On the two nearby locations, the GPU calculation of the field also dominates the total time; the global FPS of these captures do not measure the cloud cost alone.
- Captures make distant boundaries explicit; they do not validate stability in motion.

**Limits to be judged separately:**

- Periodic 3D noise can remain recognizable over a large region.
- The mips of noise do not guarantee the preservation of transparency after sealing.
- The extension allows to observe these limits; it does not yet validate a stable rendering of the orbit at the ground.
- The coverage and length of the routes can increase the cost despite the jump of the vacuum.
- The distant filtering, the temporal reconstruction and the distribution over the whole planet remain next steps.

**Memory:** Cumulonimbus retained for later; tower and anvil out of this test.

**References:** [local families](spike-nuages-cirrus.md); [reference Frostbite and provenance](spike-nuages-reference.md).
