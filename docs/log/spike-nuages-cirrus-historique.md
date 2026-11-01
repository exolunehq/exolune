# Cirrus: first local tests

**User feedback, 27 October 2026:** rendered lower than the validated cumulus and blanket. Fibers too wide, common edges too sharp: captures at 33 km show an envelope that cuts the waves. The user requests to reunite the three families and maintain a trail attenuation.

**Delivery notice of the first test, kept for record:**

# Local cirrus

**State, 27 October 2026:** First test ready for flight. Rendering, opacity and cut compiled; four initial captures and two after-correcting captures inspected. The rendering and stability at the approach of the cumulus and the reference sheet are validated in flight by the user; those of cirrus remain to be judged.

**Launcher:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-frostbite-cirrus.ps1
```

- F1: below; F2–F4: together, approach and crossing; F5: above; F6–F7: distance; F8: sunset; F9: below from the east.
- B: opacity; C: qualité48/24 m; Space: weather pause, enabled by default.
- `-Temoin` opens the validated cumulus and layer, with their palette and four assets frozen; no reconstruction of the witness data.
- `-Vue Opacite`: diagnostic3D; `-Vue Densite`: fixed2D cut Est/altitude0-16 km, density normalized by0,022.
- `-Build -NoLaunch -Vue Rendu`, `Opacite` or `Densite` recompiles the selected isolated variant.

**Objective:** add high clouds fibrous and little opaque, to be judged from below, side, cross and above.

- The field remains fixed to the world with frozen weather.
- A continuous altitude envelope extinguishes density before the path markers.
- The fibers have their own 3D field; they do not come from a cumulus profile moved in altitude.
- The local scene is drawn to compare the shapes; it does not yet represent a planetary weather distribution.
- Flight checks belong to the user; short hidden captures before return in main.

**Explicit settings of this test:**

- Noise128³ author: two Gaussian fields filtered by FFT, correlations Est6/3,5 km, North0,75/0,40 km, vertical0,25/0,15 km; weight0,55/0,45.
- Fixed domain Est64/Nord32/vertical8 km; fibers shaped at mip0 before the 3D averages.
- Center toward 11 km, maximum smooth variation±0,35 km; total thickness0,7–1,2 km, extinct well before shell9–13 km.
- Shear North±0,8 km, period16 km East and 8 km in altitude; global and continuous anchorage.
- Three weather tapes on compact support; measured holding East−28,625..25,625 km, North−12,875..12,875 km.
- Maximum density0,022, extinction80/km and integration inherited from reference.
- Manifest, footprints and previews: `assets/frostbite-cirrus/scene-manifest.json`; source parameters in `tools/gen_frostbite_cirrus_scene.py`.
- Native executable V4 identical; outputs `x64/NuageFrostbiteCirrusRendu/`, `NuageFrostbiteCirrusOpacite/`, `NuageFrostbiteCirrusDensite/`.

**Short control:**

- Three DXC variants compiled; pre-existing binary shift warning in `Materials.hlsli`.
- Four initial views: bottom, side, top,80 km; correction of the too smooth veil and the rectangular support, then two final views dessous/80 km.
- Captures and report: `x64/CirrusPreview/`; first throw in `premier-jet/`.
- Point times clouds+air after correction:4,22 ms below,2,25 ms at 80 km; GPU shared, no verdict of overall performance.
- The field remains deliberately simple and smooth; the captures do not validate the flight, the planetary distribution, or the orbital rendering.
- Full witness, sources and verified reference assets unchanged.

**Witness:** `x64/NuageFrostbiteReferenceTemoin/`, frozen copy of executable, shaders, four assets and palette validated; printed in `witness.json`.

**Memory for the following:** the 27 October 2026, the user requests to keep the cumulonimbus as experiment future. Provide high vertical extension towers and anvils; this work follows the locally common forms and is not part of this essay.

**References:** [local families guided by Frostbite](spike-nuages-reference.md); [cirrus, International Cloud Atlas](https://cloudatlas.wmo.int/fr/clouds-genera-cirrus.html).
