# Airless terrain history

**2026-11-08 · Single landable body replaced**
- Only moon 1 had terrain, rocks, contact and walking; moons 2 and 3 reused the NASA Moon Kit atlas with longitude offsets and different tints.
- The renderer held two 11,184,812-byte atlases and assumed body index zero for lunar lighting and exposure.
- The three-manifest integration replaces these assumptions, retains one detailed terrain allocation and cooks each moon's own surface.

**2026-11-08 · Contact latch removed**
- The old sweep stopped immediately whenever its initial gap was below 2 cm, including when moving away from the surface.
- A reproduced approach/contact/retreat sequence failed before the fix and passes with the current response.
- Stationary recovery used one hull radius while moving contact used 2.5; recovery could leave the camera inside its next movement support.
- The replacement shares support dimensions and a single bounded sample budget across recovery and sliding.
- Evidence: `artifacts/contact-libre-2026-11-08/repro-before.log`; current checks are in `tools/tests/check_airless.cpp`.

**2026-11-08 · Reference iterations**
- Iteration 1 added nested impact sizes and shared impact reflectance; overly dark circular basin floors looked artificial on the full disc.
- Iteration 2 reduced those patches and fractured their outlines; deeper simple bowls and shared stones improved the landing views.
- Its 1,024 × 512 proxy still looked sharper than the detailed grid just after approach; the next pass adds the atlas's unresolved slope residual to that grid.
- Iteration 3 uses a 2,048 × 1,024 atlas and restores crater structure through the detailed transition and full disc; walking remains unchanged.
- Final recaptures cover approach, full disc, 250 km, walking, the old basin and polar highlands; no benchmark scores were compared.
- Captures remain under `artifacts/lune-references-2026-11-08/iteration-1/` and `iteration-2/`.
- These stationary functional views do not measure motion performance.

**2026-11-08 · Initial sliding-plane appearance superseded**
- Background captures: `artifacts/lune-references-2026-11-08/baseline/view-01.bmp` through `view-04.bmp`.
- Orbit showed sparse, similarly sized rings on an otherwise soft, mottled ball.
- At 20 km the impact forms remained too smooth, with an obvious gap between surface-detail scales.
- Landing and walking exposed stretched material coordinates and no placed stones at the review site.
- The old field used nine scales from 300 km, radius fractions 0.13–0.32, and full crater weight only above four sampling footprints.
- Colour was an unrelated broad noise; the far atlas was 512 × 256.
- Per-pixel regolith bands ended at 32 m, leaving an unrepresented middle distance.
- These views are comparison evidence, not a performance benchmark.

**2026-11-08 · Separate quadtree rejected**
- The user requires the same sliding-plane renderer for every solid body, composed by manifests.
- These prototype settings and preliminary checks do not validate the required architecture or final surface quality.
- The rebase and original work remain preserved.
- Current contract: [body manifests](../spec-manifestes-corps.md).

# Airless terrain

**Status**
- First landable moon prototype, 2026-11-08, on erosion base `9780367`.
- Native flight review is in progress.
- The other moons and planets remain distant visual bodies.

**Physical field**
- `Airless::Surface` owns the first moon's radius of 1,800 km and deterministic seed 9173.
- Broad fractured highlands and nine impact bands replace hydrology, continents, water and vegetation.
- Impacts excavate bowls, raise compact rims and ejecta aprons, and add central uplifts to large craters.
- Mesh vertices, contact and the distant proxy sample this same field in body coordinates.
- Footprint filtering removes unresolved relief before mesh generation.
- The distant 512 × 256 linear albedo/normal atlas is cooked by `tools/prepare_airless.ps1`.
- Regenerate that atlas after changing the field or its seed.
- This is a fictional surface, not a reconstruction of the real Moon.

**Bounded work**
- Small resolved bodies draw only within conservative projected rectangles; invisible rectangles submit nothing.
- Subpixel bodies retain the existing stellar flux representation.
- The first moon uses its cooked sphere proxy below a projected radius of 24 pixels.
- Detailed relief uses a cube-sphere quadtree with 16 × 16 cells per tile.
- One worker generates requested tiles; the render thread never waits for terrain generation.
- Limits: 192 drawn tiles, 384 resident CPU tiles, 384 resident GPU tiles, 12 pending tiles.
- Refinement targets 12-pixel cells, subject to that fixed budget and a maximum level of 21.
- Children start at their parent's actual triangles and morph to their own surface over 0.2 seconds.
- Downward skirts cover adjacent levels; they do not define contact.
- The terrain worker and cache are created only when the detailed moon is first visible.
- Exolune uses its existing relief/climate maps once its maximum relief is below a quarter pixel.
- That representation bypasses terrain generation, horizon integration, FFT sea, objects and vegetation.
- Atmospheric scattering and clouds remain in the common physical frame.
- These are explicit work bounds, not measured frame-rate guarantees; no performance benchmark was requested.
- The current catalogue still has seven finite celestial bodies; arbitrary planet counts are not implemented.

**Landing and reference frames**
- Positions and body-relative subtraction use doubles; each rendered tile has a small camera-relative origin.
- Flight up, speed scaling, altimeters and walking use the nearby body's centre.
- Near the moon, the observer and landed ship follow its orbital translation.
- The prototype does not rotate the lunar surface or integrate spacecraft orbital dynamics.
- Flight sweeps the travelled segment through the shared relief field, including orbital chords.
- The swept spherical hull is conservative; exhausting the query budget stops motion at the last tested position.
- Walking samples the shared terrain at 0.5 m and uses 1.62 m/s² gravity without a sea-level restriction.
- No lunar wind, rain, ocean or terrestrial environmental sound is queried.
- The incident exposure meter uses the lunar horizon and planet shine without temporal exposure smoothing.

**Current limits**
- A teleport can expose coarse parent tiles while nearby detail is generated.
- The fixed detail budget can retain coarser geometry when the whole horizon is visible.
- Cast shadows from distant crater walls are not implemented; normal lighting and the existing local contact pass remain.
- Flight contact uses a spherical hull envelope; it does not solve individual landing-gear contacts.
- The distant Exolune material uses filtered relief and climate colours; detailed water glints and land materials require its terrain representation.
- The remaining two moons have neither displaced terrain nor landing contact.

**Review**
- Build: `powershell -NoProfile -ExecutionPolicy Bypass -File tools/lance.ps1 -Build -NoLaunch`.
- Model checks: `powershell -NoProfile -ExecutionPolicy Bypass -File tools/tests/check_airless.ps1`.
- Flight route: `tools/tests/2026-11-08-lune.txt`.
- Launch: `powershell -NoProfile -ExecutionPolicy Bypass -File tools/lance.ps1 -Parcours tools/tests/2026-11-08-lune.txt -DepartTest 1 -Resolution fenetre`.
- F1–F7 visit lunar orbit, descent, landing, walking, night and poles; F8–F12 return to Exolune.
- `J` disembarks; use the existing flight controls to descend and take off.
- `lune` in a route row selects lunar latitude/longitude and clearance above its terrain.
- Existing terrestrial rows retain their sea-level altitude.
- Functional stills: `tools/tests/capture_airless.ps1`; no benchmark comparisons are included.
