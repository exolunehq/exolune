# Airless terrain

**Status**
- Three airless moons share the landable stack, on erosion base `9780367`.
- The impact stack feeds the common sliding-plane path; background stills cover orbit, descent and walking.
- The earlier separate quadtree is rejected; its settings and preliminary checks are in [history](log/spec-lune-terrain-historique.md).
- Shared rendering and descriptive manifests are mandatory: [body manifest contract](spec-manifestes-corps.md).
- The other planets remain distant visual bodies.

**Body manifests**
- `CelestialManifest.h` describes each moon's identifier, version, radius, seed, gravity, mean reflectance and cooked atlas.
- Moon 1 retains radius 1,800 km, seed 9173 and gravity 1.62 m/s².
- Moon 2 uses radius 700 km, seed 28411 and gravity 0.63 m/s².
- Moon 3 uses radius 260 km, seed 60149 and gravity 0.234 m/s².
- The latter gravities scale with radius at the first moon's mean density; these are fictional bodies.
- Existing neutral, cool and ochre tints remain part of their descriptions.
- This is a typed manifest for the airless stack; the complete serialized celestial schema remains future work.

**Physical field**
- `Airless::Surface` receives the selected manifest's radius and deterministic seed.
- Broad fractured highlands and nine impact bands replace hydrology, continents, water and vegetation.
- Impact scales start at the smaller of 1,000 km and 60% of body radius, then divide by five; no impact is larger than its host body.
- Regolith, exposed rock, pebbles and boulders remain required through the shared material and object systems.
- Impacts excavate bowls, raise compact rims and ejecta aprons, and add central uplifts to large craters.
- Impact age controls floor infill and rim wear; large impacts have broad floors, steeper walls and displaced rim outlines.
- Fresh ejecta and old dark basin floors are material fields of those same impacts, not unrelated colour noise.
- Overlapping impacts share an excavation/deposit envelope within each band; their depths do not accumulate without a bound.
- The shared rendering and contact envelope is -16 to +16 km around the reference sphere.
- Mesh vertices, contact and the distant proxy compile the same `AirlessField.hlsli` field in body coordinates.
- Footprint filtering removes unresolved relief before mesh generation.
- The 2,048 × 1,024 linear albedo/normal atlas is cooked by `tools/prepare_airless.ps1`, including twelve mip levels.
- Regenerate that atlas after changing the field or its seed.
- The cooker builds all three atlases from the same manifests. A 32-byte header identifies layout, field version, radius, seed and dimensions; mismatched runtime data is rejected.
- `assets/celestial/airless-provenance.json` records source and cooked-file hashes.
- Its colour and normals are filtered at the atlas footprint before cooking; it contains no lunar photograph or painted lighting.
- When the detailed grid is coarser than that atlas, two filtered reads restore its unresolved slope residual and reflectance.
- This bridge uses the existing terrain map slot, fades out before landing and adds no vertices or physical-field queries per pixel.
- A shared particulate reflectance approximation lights detailed ground, rocks and the distant disc.
- Unresolved flux integrates that same surface law; the existing incident meter and lack of temporal exposure smoothing are preserved.
- This is a fictional surface, not a reconstruction of the real Moon.

**Reference review**
- Full disc: [Galileo PIA00113](https://science.nasa.gov/photojournal/moon-color-composite/) supplies basin, ejecta and crater-scale relationships.
- Its violet/red/near-infrared composite is a morphology reference, not a colour calibration.
- Low orbit: [LRO Taurus-Littrow oblique images](https://svs.gsfc.nasa.gov/4302/) supply nested crater sizes, slopes and cast-shadow relationships.
- Ground: the Apollo 17 panorama on that same NASA page supplies regolith, scattered stones, foothills and a sharp airless horizon.
- [Tycho](https://science.nasa.gov/resource/tycho-crater-oblique-view/) supplies a young complex crater's walls and central massif.
- [Lunar-Lambert photometry](https://pubs.usgs.gov/publication/70016679) motivates the inexpensive diffuse/single-scattering approximation; this is not a calibrated Hapke material.
- Compare spatial structure and illumination at several footprints; do not copy a photograph's exposure into the renderer.
- Keep a common site and sunlight during descent, then review another site and low sunlight.
- The dated route is `tools/tests/2026-11-08-lune-references.txt`; captures remain outside Git under `artifacts/lune-references-2026-11-08/`.
- Fourteen poses were inspected across three iterations; the final pass recaptured seven views, including the proxy transition, full disc, walking, basin and polar terrain.

**Bounded work**
- Small resolved bodies draw only within conservative projected rectangles; invisible rectangles submit nothing.
- Subpixel bodies retain the existing stellar flux representation.
- The detailed moon must reuse Exolune's sliding planes, rings, footprint filters, fine grid and screen reconstruction.
- Refinement follows the same per-frame camera motion and continuous scale changes as Exolune.
- The impact stack changes the sampled field; it must not introduce another mesh or transition system.
- Geometry, samples, objects, memory and preparation use shared global budgets.
- The prototype has three fixed atlas slots, each with 11,184,812 bytes of texels and mips; total payload is 33,554,436 bytes.
- This replaces the former procedural atlas plus NASA reference atlas; the net payload increase is 11,184,812 bytes.
- The catalogue cannot exceed these slots without implementing bounded residency; it does not allocate another detailed terrain engine per body.
- Each visible moon's draw binds its own atlas once; pixels do not search the moon catalogue.
- One selected nearby moon owns the existing detailed buffers. Changing bodies invalidates terrain, screen, placement and contact histories before reuse.
- Exolune uses its existing relief/climate maps once its maximum relief is below a quarter pixel.
- That representation bypasses terrain generation, horizon integration, FFT sea, objects and vegetation.
- Atmospheric scattering and clouds remain in the common physical frame.
- These are explicit work bounds, not measured frame-rate guarantees; no performance benchmark was requested.
- The current catalogue still has seven finite celestial bodies; arbitrary planet counts are not implemented.

**Landing and reference frames**
- Positions and body-relative subtraction use doubles; the common renderer uses camera-relative coordinates.
- Flight up, speed scaling, altimeters and walking use the nearby body's centre.
- Near any moon, the observer and landed ship follow that body's orbital translation.
- The prototype does not rotate the lunar surface or integrate spacecraft orbital dynamics.
- Flight sweeps the travelled segment through the shared relief field, including orbital chords.
- The swept spherical hull is conservative; exhausting the query budget stops motion at the last tested position.
- The airless support is 2.5 times the hull radius in placement, movement and clipping, with a 2 cm contact skin and up to 4 cm recovery clearance.
- Existing contact removes only the inward displacement; outward input and tangential sliding remain available, including submillimetre requests.
- At most five responses per sweep redirect unconsumed motion; body and chase-eye sweeps share 192 height samples across candidate moons.
- Every redirected segment is swept again; the correction does not permit endpoint-only escape through intervening terrain.
- Walking samples the shared terrain at 0.5 m and uses the selected manifest's gravity without a sea-level restriction.
- No lunar wind, rain, ocean or terrestrial environmental sound is queried.
- The incident exposure meter uses the lunar horizon and planet shine without temporal exposure smoothing.

**Current limits**
- Release x64 and CPU relief/contact/reflectance checks pass; interactive flight review remains with the user.
- Native walking views contain 436 and 77 placed stones at two different sites, with Exolune visible from the second site.
- Terrain shadows and object contact are visible in the stills; boarding, takeoff and ship interaction still need flight review.
- The crater hierarchy remains procedural and can repeat recognizable bowl forms; it is not a measured lunar terrain model.
- Some oblique crater walls remain smoother than the LRO reference; assess those views during flight as well as the improved orbital disc.
- Flight contact uses a spherical hull envelope; it does not solve individual landing-gear contacts.
- The distant Exolune material uses filtered relief and climate colours; detailed water glints and land materials require its terrain representation.
- All three moons use the same displaced terrain, surface objects, landing contact and walking controller.
- Eight final background stills validate the three-body integration; both new walking sites show Exolune and anchored stones. Evidence: `artifacts/trois-lunes-2026-11-08/lunes/`.
- Continuous flight and inter-body switching remain for the user's interactive review; the stills are not a motion-performance measurement.

**Review**
- Build: `powershell -NoProfile -ExecutionPolicy Bypass -File tools/lance.ps1 -Build -NoLaunch`.
- Model checks: `powershell -NoProfile -ExecutionPolicy Bypass -File tools/tests/check_airless.ps1`.
- Contact checks include 96 approach/retreat/slide/recovery sequences over synthetic profiles and all three shipped manifests, both poles, and camera/ship hull sizes.
- Body selection, geometry bounds, seed variation, orbital chords and the shared query budget are also checked without a GPU.
- Contact review: `tools/tests/2026-11-08-contact-libre.txt`; start with `-Camera libre`, touch the ground, hold briefly, then retreat and slide without changing views.
- Flight route: `tools/tests/2026-11-08-lune-references.txt`.
- Launch: `powershell -NoProfile -ExecutionPolicy Bypass -File tools/lance.ps1 -Parcours tools/tests/2026-11-08-lune-references.txt -DepartTest 3 -Resolution fenetre`.
- F1–F4 visit approach and orbit; F5–F10 visit descent and two ground sites; F11–F12 return to Exolune.
- The Tests palette also includes a basin under low sunlight and polar highlands.
- The original `tools/tests/2026-11-08-lune.txt` retains night and earlier terrestrial exposure checks.
- `J` disembarks; use the existing flight controls to descend and take off.
- `lune` and `lune1` select the first moon; `lune2` and `lune3` select the other manifests, using latitude/longitude and clearance above their own terrain.
- The three-body review route is `tools/tests/2026-11-08-trois-lunes.txt`; start with `-Camera libre`.
- Existing terrestrial rows retain their sea-level altitude.
- Functional stills: `tools/tests/capture_airless.ps1`; no benchmark comparisons are included.
- Use background native captures for agent visual checks, as requested on 2026-11-08; leave interactive flight review to the user.
