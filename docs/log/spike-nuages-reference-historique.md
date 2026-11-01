# Clouds: starting from a published reference

**Local reference before validation, 27 October 2026:** five hidden captures had delivered the cumulus and the blanket, with a flight judgment still expected. The next decision was to judge silhouettes, crossing and anchoring in time-freeze before extending the weather. The user then validated the local rendering and approach stability. He calls for local families to be supplemented with cirrus before large-scale distribution; cumulonimbus remains a future experiment. See the [current notice](spike-nuages-reference.md).

**V1 Archive, 27 October 2026:** initial state and search before user return. Near stability is then judged as progress; flat ceilings, medium-distance repetitions, uniform distribution and costs remain unsatisfactory. The [current notice](spike-nuages-reference.md) describes the V2 and V3 diagnostic versions. The measures below are not validation of the rendering in flight.

**Status, 27 October 2026:** first Wicked spike compiled and ready for user judgment. Four initial captures and two controls after domain deformation were produced without error. The V2 voxel remains available as a test; no flight stability verdict.

**First draft implemented:**

- New path `AtmosphereWicked.hlsl` / `CloudWicked.hlsli`, enabled by `MYPLANETENGINE_CLOUD_WICKED=1`.
- A spherical shell between 3 and 6,5 km; vertical gradients mixed according to weather type.
- Weather 3D periodic to the periods of 1 024 and 4 096 km, without face connection.
- Perlin-Worley form, detail erosion, two-lobed phase and approximated multiple scattering.
- 128³ shape textures, 32³ detail and 64³ weather textures, all with mips, or 10 935 148 bytes.
- Offline generation by `tools/gen_wicked_cloud_textures.py`; loading DX12 once, no animated rebake.
- Wind by global rotation; moving the detail domain with the weather clock.
- Period form 8 km, period detail 1 km; continuous deformation of the domain by a 3D field of period 37 km, amplitude ±1,5 km.
- The deformation uses the weather texture and an oscillation of 1 200 s; the cycle of 2 400 s remains continuous.
- Texture entries and phases in double precision precision; path loops in float local shifts.
- Roots refined in double precision and floor by whole conversion; the intrinsics HLSL alone lost the expected accuracy.
- Economic mode: not close to 48 m, far bound of 240 m and a solar sample.
- Reference mode: not close to 24 m, far bound of 160 m and two solar samples.
- The reference mode is a sampling comparison, not a converged physical reference.
- No time history, curl or new shadow on the field in this first shot.
- The density filtering after threshold and the stability of transitions remain to be judged; the mips of noise do not guarantee transparency preservation.

**Launch and comparison:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-wicked.ps1
```

- Launcher binary: `x64/NuageWicked/MyPlanetEngineWickedV1.exe`, SHA-256 `45AB7AD2F89FCF09FACF91B1E77CE4B46BCB8958F42C011833C41F05BD005F38`.
- Shader: `C629644327AC97820D29CD3B7F9627961A722A296551236EEB49BEB422FD05DB`.
- The first open session uses `MyPlanetEngineWicked.exe`; V1 only corrects the counter and the title accents, without interrupting that session.
- `-Temoin` launches the old spike voxel V2; `-Static` freezes the weather; `-Reference` chooses fine quality; `-Clear` cuts clouds; `-Build -NoLaunch` compiles.
- C: economic/reference; N: clouds yes/no; Space: weather break; B: opacity; V: weather speed ×5.
- Palette `tools/tests/2026-10-27-nuages-wicked.txt`: F3 profile, F4 in layer, F5 above, F8 whole planet, F9 pole and F10 other continent.
- The title and capture sidecars measure clouds+air; they don't give the cost of clouds alone.
- Source and license pinned in `third_party/WickedEngine/`.

**Light controls:**

- Build Debug x64 successful; pre-existing shader warnings remain present.
- First boot: profile, top, whole planet and another region; `x64/WickedStartup/` files.
- This first setting visibly repeated the small tile shape in oblique view; scale and deformation of the domain were taken before delivery.
- Version to judge: `x64/WickedPreview/`, profile at 4,5 km and top at 10 km, weather frozen, 1280 × 720.
- Profile: 9,91 ms/frame of which 8,76 clouds+air; top: 7,51 ms/frame of which 6,10 clouds+air.
- Point measures on shared GPU; they do not set a guaranteed budget in flight.
- The counter and title accents have been corrected after these captures; the cloud field remains the same.
- The executables and shaders of the V2 test are unchanged, verified by footprints.
- No complete campaign of benchmarks; the user does the end to end testing.

**Local record:**

- The POC validated the stability of a small formation composed of four lobes.
- The planetary spike repeated this shape, with variations in placement and cover.
- Replacing density calculation with texture did not change the path or the lighting.
- The test was therefore not evaluating a voxel system comparable to production solutions.
- The side band correction has begun to impose more paths, supports and variants; this iteration is stopped.

**References:**

| Primary reference | Audited contribution | Limit for our decision |
|---|---|---|
| [Wicked Engine, shader de rendu](https://github.com/turanszkij/WickedEngine/blob/5433f0a6cb0ed9ddfd41b7742978d038eaff70de/WickedEngine/shaders/volumetricCloud_renderCS.hlsl) and [density model](https://github.com/turanszkij/WickedEngine/blob/5433f0a6cb0ed9ddfd41b7742978d038eaff70de/WickedEngine/shaders/volumetricCloudsHF.hlsli) | Existing HLSL; weather, vertical profiles, shape and detail noise functions, spherical shell, diffusion and shadows. | XZ weather projection, float coordinates and LOD rounded in this version; planetary adaptation required. |
| [Wicked Engine License](https://github.com/turanszkij/WickedEngine/blob/5433f0a6cb0ed9ddfd41b7742978d038eaff70de/LICENSE.txt) | MIT; adaptive code base with attribution. | Audit also the allocation of the taken over functions and resources. |
| [Unreal Engine, volumetric clouds](https://dev.epicgames.com/documentation/unreal-engine/volumetric-cloud-component-in-unreal-engine?lang=en-US) | Documentation covering ground, flight and space; volumetric path, reconstruction at multiple resolutions, multiple scattering approximate and shadow choice. | A reference architecture; no guaranteed results in our engine. |
| [Nubis Evolved, 2022](https://www.guerrilla-games.com/read/nubis-evolved) and [Nubis³, 2023](https://www.guerrilla-games.com/read/nubis-cubed) | Two documented generations for cloud flight; Nubis³ combines voxels, compressed distance fields, detail reconstruction and light acceleration. | The complete system goes beyond a simple density cache; it is not a plug-in library. |
| [Takram, three-clouds](https://github.com/takram-design-engineering/three-geospatial/blob/main/packages/clouds/README.md) | Open implementation with shadows and temporal reconstruction. | The README still announces global coverage and spatial views as future work; mentions seams and time trails. |

**Choice:** start from a new HLSL kernel inspired by the Wicked Engine model and the publications cited by its authors. It is a choice of adaptation, not a claim of superiority over the voxels.

**First spike bordered:**

1. A single spherical layer, with a weather cover and type; cumulus and stratocumulus sufficient for the first judgment.
2. Pre-calculated periodic 3D shape and erosion textures, used in a continuous field; no population of POC specimens.
3. A function of place and time density; weather and coordinates remain independent of the camera. The planetary weather projection must avoid seams.
4. A lighting designed with density: sun, sky, auto-shade and multiple scattering approached. Avoid judging volumes with the old lighting minimum of the POC.
5. A comparable reference mode without history and economic mode. Time reconstruction can then amortize the calculation; it does not define the cloud shape.
6. Reuse the camera, atmosphere and digital references in double precision precision; reconstruct the cloudy path, without taking over the instances or the step ceiling of the voxel spike.

**Adaptation points to be explicitly addressed:**

- Reference distance ranges do not prove coverage from orbit; keep visible shell intervals and test outside the atmosphere.
- The fractional LOD and filtering must be studied after density thresholds; the average of a noise does not guarantee the average of transparency.
- The budget and stability of our integration remain to be measured; performance of another engine does not translate.

**Fast delivery:** some comparable views, a GPU cloud counter, weather break, cloud cut and quality change. The user judges in flight the ground, the bottom, the side profile, the inside, the top and the orbit. A convincing first layer precedes the addition of cirrus, storms and physical weather. No complete campaign of benchmarks for this spike.

**Support criterion:** the rendering must visually progress and remain consistent as it approaches these views. If the port of the released kernel fails to do this, compare another base rather than stack offsets.


## V2 before radial band diagnosis

**Final checks, point-by-point in 720p frozen on GPU shared:**

| View | GPU frame | Clouds + air |
|---|---:|---:|
| Above a convective field, 8 km | 19,05 ms | 13,12 ms |
| Oblique view at 160 km | 9,11 ms | 3,22 ms |
| Whole planet at 8 000 km | 28,69 ms | 8,57 ms |

- Captures and fingerprints: `x64/WickedV2FinalPreview/startup.json`.
- EXE : `E7583D53ED5418C2841D9879D2C214567771EB8256A716ACB6A45A5CC82B46E8`.
- Shader: `4BA776259F659AADC76E4A0E8944A466A3DD6A065A484720C92C6139CD6E83F1`.
- Weather: `AFE7F4212BE2D423A1CF1C582D25037B6E901B89B07B897E707B6FCD5A2AA939`.
- No benchmark complete; frame times vary greatly with other loads and do not guarantee the cost in flight.
- The V1 and its session remain intact; no commit, tag, or push requests.



## V3: radial band diagnostics

**Radial bands: diagnostic and experimental correction:**

- Three views reproduced in fixed weather: below at 1,4 km, oblique at 454 km and orbit at 2 601 km.
- Bands persist without atmospheric composition; those far away also appear in opacity alone.
- A constant macro shape preserves the rings; integration along the radii is involved.
- The V2 steps of 48 to 240 m can cross a very opaque transition without integrating it sufficiently.
- A uniform pitch of 12 m improves rendering but costs up to 219 ms for orbiting clouds + air; experiment rejected as a global solution.
- The V3 keeps the intervals of the course and their LOD; it subdivide the intervals where start, middle or end detect cloud, to 12 m maximum in Eco and 6 m in Reference.
- The original medium is reused; the probes at the ends are limited to candidate areas of the height profile.
- The conservative weather jump is preserved; a zero density allows no additional jumps.
- The integration stops as soon as all transmission channels are under 0,003.
- The shapes, weather and solar lighting remain those of the V2; the repetitions and the filtering after threshold remain to be resumed.
- This refinement is an approximated quadrature; three probes do not prove the absence of a structure between them.
- A first refinement controlled only by the variation of optical depth left bands close; save in `x64/Recovery/WickedV3AdaptiveFirst/`.

**V3 controls, pointed in 720p frozen:**

| View | GPU clouds + air |
|---|---:|
| Underwear at 1,4 km | 31,67 ms |
| Oblique to 454 km | 26,26 ms |
| Orbite at 2 601 km | 38,55 ms |
| Stratus at 8 km, change location | 45,88 ms |

- Four hidden captures; DXC compilation successful, no native build required.
- The large bands are clearly attenuated on these images; the repetitions remain visible.
- The cost is lower than V2; this V3 is used for diagnostics and is not declared acceptable.
- Artefacts and poses: `x64/WickedV3Preview/startup.json`; isolated comparisons: `x64/RadialDiagnostic/`.
- No complete benchmark, no p95 or movement validation; user keeps checks in flight.
- No user session interrupted; no commits, tags, or pushes.
- Shader V3 : `F4FADA0649F52ABF931571077D67B4FDF62358014DC3AE67F3FA3A23071E4FEB`.


## V4: route alternatives rejected

- **Periodic deformation in HLSL:** two noise functions vectors world at 48 and 13 km; cost almost doubled, insufficient improvement of the grid. Sources and CSO in `x64/Recovery/WickedV4Aperiodic/`, captures in `x64/WickedV4AperiodicPreview/`.
- **Positive density interpolation:** three measurements per step, two linear segments and lighting positions taken at average optical depth; remaining bands. `x64/WickedV4IntegrationPreview/` and `x64/Recovery/WickedV4PositiveInterpolation/`.
- **Signed field:** passage by localized zero before integration, without artificially filling all the outside part of the step; insufficient improvement on near and far views. `x64/WickedV4SignedPreview/` and `x64/Recovery/WickedV4SignedLinear/`.
- **Signed quadratic profile:** same three measurements, roots and analytical mass, inversion of the primitive by eight bissections; correct CPU controls but still strong bands and higher cost. `x64/WickedV4QuadraticPreview/` and `x64/Recovery/WickedV4Quadratic/`.
- **Constant albedo:** 0,95 test on linear signed interpolation; remaining bands, flattened. `x64/WickedV4AlbedoPreview/` and `x64/Recovery/WickedV4Albedo/`.
- **Decision:** these routes are not in the delivery V4; the V2 walk is retained. The problem of the shelves remains open.
- **reference frame bibliographic:** [Engel, Kraus and Ertl, 2001, High-Quality Pre-Integrated Volume Rendering](https://www3.cs.stonybrook.edu/~mueller/teaching/cse616/engel.pdf) incorporates transfer functions between measurements to limit the effects of insufficient sampling. The above tests are not a complete implementation; no pre-integration tables are delivered.


## V4 preserved as witness of V5

# Spike Wicked: Volume Splitting and Integration

**State, 27 October 2026:** User finds the rest of the rendering satisfactory; the two priority defects are radial stripes and grid alignments. The V4 isolates the correction of the noise shape and its mips, retaining the V2 step. The radii remain unresolved; more expensive variants have been discarded. The judgment in flight remains with the user.

**Launch V4:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-wicked-v4.ps1 -Static
```

- `-Temoin` launches the retained V2 with the same positions and palette as V4; `-Static` freezes the weather; `-Reference` fine-tunes the sampling; `-Clear` cuts the clouds.
- `-Build -NoLaunch` copies the native V2 and its common shaders to a separate output, then compiles only the Wicked V4 shader.
- C: quality; N: clouds; Space: weather break; B: opacity; V: weather speed.
- Palette `tools/tests/2026-10-27-nuages-wicked-v4.txt`: F1 under the clouds, F2 near the base, F6 stratus, F7 at 454 km, F8 at 2 601 km, F10 other formation.
- Binary: `x64/NuageWickedV4/MyPlanetEngineWickedV4.exe`; outputs V1, V2 and voxel remain separate.
- Native V4 is a copy of Native V2; the changes are in shader and shape data.

**Vertical limits:**

- The shell traveled is a wide bound of 1 to 9 km.
- The local base varies between 2 and 4 km; the reference thickness between 0,5 and 4 km.
- Families modulate thickness and density.
- The macro shape varies the bottom from ±50 to ±150 m and the top from ±200 to ±600 m depending on the type.
- Two ramps soften these local boundaries; the family profile no longer cancels density before the summit ramp.
- The parameters guarantee zero density before the shell limits, about 1,69 to 8,76 km maximum.

**Reference allocation:**

- The luminance of the historical composite [NASA Blue Marble: Clouds](https://visibleearth.nasa.gov/images/57747/blue-marble-clouds/77558l) serves as a cover mask.
- The original file and credits are in `third_party/NASA/`; the transformations are in the asset manifest.
- This data allows to judge the rendering on real formations; it is not a procedural weather or a measure of cloud fraction.
- Types, bases and thicknesses remain synthetic fields; stratus, stratocumulus and convection are mixed by region.
- The 1024 × 512 RGBA8 map is read as longitude/latitude in the weather world, with periodic U and bounded V.
- Volume remains in 3D; no cloud image is placed on a sphere.

**Grid correction, V4:**

- The first octave of the periodic Perlin V2 used only one cell and one gradient vector.
- This dominant octave separated along the three axes; it favored a rectilinear distribution.
- The V4 base uses 3 cells per axis, then the frequencies 3, 6, 12, 24 and 48.
- The five weights are renormalized to the original 1,984375 sum; the role of channels and the Perlin-Worley combination are retained.
- The mips shapes use a separated periodic binomial filter `[1,3,3,1]/8` before each subsampling; the 0 level is not modified by this filter.
- V4 data is in `assets/wicked-clouds-v4/`; the old data remains in `assets/wicked-clouds/` and the output is V2.
- Detail, deformation 3D and planetary weather are bit by bit identical to the V2.
- The mip of the second shape read takes into account its higher frequency: +0,470553.
- The mip of deformation follows its footprint at long distances, with a minimum of 1 as before.
- Alignments decrease on captures; neither the complete absence of repetition nor the stability in motion are validated.
- The string of noise remains periodic; this fix does not constitute a field of shapes without repetition at any scale.

**Regenerate assets V4:**

```powershell
python tools/gen_wicked_cloud_textures.py --output assets/wicked-clouds-v4 --shape-perlin-base 3 --shape-mip-filter binomial
```

- The generator defects remain `base 1 / box` for the witnesses.
- The cache checks the parameters, filter and shape footprint; a correct size is not enough.
- The NASA coverage, altitude profiles, families, animation, diffusion phases and V2 albedo are preserved.
- Individual formations change with the shape noise; no particular placement to test views.

**Shape and distance:**

- Two Perlin-Worley readings use fixed reference frames worlds and different frequencies, with digital anchorage in double precision.
- The mixing of raw channels precedes a single remap; a double transformation introduced an excess of density.
- The macro level varies continuously according to the footprint, up to the mip 7; the detail erodes separately.
- The solar lighting uses a fixed level, independent of the view level.
- The second order of diffusion takes a reduced solar attenuation.
- Filtering remains approximate: the mips of noise do not guarantee the preservation of transparency.

**Vacuum and performance:**

- The actual weather is read at the mip 1; these texels remain averaged.
- Levels 2 and following retain the maximum R, as a presence boundary; GBA remain averaged.
- A jump is allowed only in a proved empty box, shrunk to include the taps of the bilinear filter.
- Its distance is limited by the boundaries of the spherical sector, with a margin of 20 %, and capped at 10 km.
- No jump is based on a single zero density sample.
- Full screen without time reconstruction is still expensive in some views.

**Delivery control, punctual in 720p frozen:**

| View | GPU clouds + air |
|---|---:|
| near | 9.55 ms |
| medium454 | 6.47 ms |
| orbite | 14.68 ms |
| stratum | 16.69 ms |

- Four hidden views, several distances and three locations; DXC compilation successful.
- The V4 retains the V2 path; these measurements on shared GPU are not a benchmark performance statistic.
- Radial bands remain present; no results presented as a correction of these bands.
- Images and poses: `x64/WickedV4DeliveryPreview/startup.json`.
- Shader V4 : `D0777E1D538283313D6B348EE81BC0C69664B4BED9FF4CACF4CB688C4114CC47`.
- Shape V4 : `33A530A1147AF0615EA7C12E0F8D70811BF87ABE18C984466737EFF87AE954E0`.
- No benchmark complete, no p95 or motion verification; user judges in flight.
- The Debug x64 project is now released in V4 to protect V2 binaries from ordinary builds.
- No commit, tag or push requested.

**History:** [V1 and research](spike-nuages-reference-historique.md). The purely synthetic test V2 was dismissed: `x64/WickedV2Preview/` and backup `x64/Recovery/WickedV2Start/`. The NASA version before the empty jump is retained as `x64/WickedV2ReferencePreview/`. Reference HLSL and license: `third_party/WickedEngine/`.


---

## V5: test not accepted after flight judgment

**User feedback, 27 October 2026:** The LOD reduces the noise without correcting the repetition, with sharper contours and a less good look. The formations become more joint as soon as close. The distribution seems too extensive, without convincing meteorological organization. Floors and ceilings remain too clean; families do not give distinct cirrus.

- J only disables the LOD; the V5 morph changes remain active.
- The increase in cover and the filling of the hollows in the sheets also affect the fine field.
- The technical details and measurements below describe the test delivered, not a validated result.

# Spike Wicked V5: training and optical coverage

**State, 27 October 2026:** prototype compiled, hidden captures produced; flight judgment entrusted to user. layers and large holes replace part of the planting of small silhouettes. The distant rendering remains approximate; no overall validation of stability or realism.

**Launcher:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-wicked-v5.ps1 -Static
```

- Start at 271 km; F6 finds this view.
- J: active optical coverage / detailed volume alone, with the same V5 formations and the same weather.
- `-FineOnly` starts with the LOD optical cut off.
- `-Temoin` opens the V4 frozen with the same positions and the same palette; it retains its own morphology.
- Space: weather break; C: fine quality; B: opacity; N: clouds; V: weather ×5.
- F1/F2: proximity and 10 km; F3/F4/F5: approach to 30/80/160 km; F6/F7: 271/454 km; F8: orbit; F9/F10: stratus; F11: other front; F12: pole.
- Isolated binary: `x64/NuageWickedV5/MyPlanetEngineWickedV5.exe`.
- `-Build -NoLaunch` compiles the only V5 shader and the target native; common shaders are taken from V4.

**Common training fields:**

- The NASA coverage remains a visual reference and a presence boundary; it is not a measured cloud fraction.
- A reading of noise 3D at period 192 km modulates the type, continuity of benchmarks and their coverage.
- An envelope of period shape 32 km modulates the coverage to another scale.
- Closed regions favor blankets; convective regions retain more separate cells.
- Small volumes use the primary noise period 8 km and detail erosion.
- All phases are calculated in the weather world, with double anchoring; wind and time remain shared.
- Fine density uses fixed levels: shape 0, detail 1 and deformation 1, including for the thin wide envelope.
- The camera chooses the mixture of the images; it does not move the phases of the fine field.
- Individual shapes change from V4, but light bases, vertical profiles and their shell 1–9 km are retained.
- The mask of benchmark remains null when the source weather is empty; the Rmax proof of V4 jumps remains conservative.

**Optical table:**

- `tools/gen_wicked_optical_lut.py` samples the fine model on 512 columns and 48 not vertical, with two azimuths.
- The table averages transmittances after exponential: `E[exp(-k × intégrale de densité)]`.
- It does not apply exponential to a density that has already been averaged.
- Texture 32³ RGBA8, six mips stored; only the mip0 is used for rendering.
- X: 32 covers between 0 and 1.
- Y: 4 types × 8 thicknesses between 0,5 and 4 km, index `type × 8 + épaisseur`.
- Z: 32 absolute cosine of view between 0,08 and 1.
- RGB: extinction coefficients 71/86/100 per km; A: coefficient 0,2 × 86 for the second order.
- Four readings separately interpolate type and thickness; hardware filtering interpolates coverage and angle.
- The optical result of view is averaged on five points of the footprint, after the table readings; the envelope contours are therefore filtered as well.
- Zero coverage gives exactly one unit transmission; values are limited and the cache checks parameters and footprints.
- The table measures a statistical population; it does not pre-compute every geographical column of the planet.

**Far-reaching representation:**

- A representative shell provides a world point in the visible segment of the radius.
- The weather, type and envelope of this point feeds the optical table.
- A lighting average reuses sun, phase and atmosphere V4; its diffusion is approximate.
- The transition directly mixes light premultiplied and transmittance, then opacity weighted depth.
- It extends from a footprint of 0,12 km to 0,65 km per pixel; at its end, detailed micro path is avoided.
- The crossless rasant rays of the representative shell use the middle of the segment; a height cap softens the limb.
- The disabled J mode fully retains the fine volume V5 and allows this input to be judged separately.
- No time history or new processing of detailed rays is added.

**Limits to be judged in flight:**

- The table assumes a stationary local medium and a plane layer; the very small cosinus are limited to 0,08.
- The Limbic Head and the lighting Medium are not a complete physical integration of a long planetary crossing.
- The statistical model is not the exact average of each local neighborhood; the conservation of small holes during approach remains to be controlled.
- The distant aspect may become too flat or too opaque; the light transition may require adjustment.
- Radial bands of the thin path remain an open problem.
- No p95, benchmark full or motion validation; user does end-to-end checks.

**Generation:**

```powershell
python tools/gen_wicked_optical_lut.py --source assets/wicked-clouds-v4 --output assets/wicked-clouds-v5
```

- The seven V4 source files are copied without change; only the optical table is added.
- The texture occupies 149 796 bytes with its mips; no reconstruction of this table per frame.
- The manifest describes the equations, parameters, generation time, and footprints.

**Short delivery control, 720p frozen on GPU shared:**

| View | GPU clouds + air |
|---|---:|
| reasons271 | 5.40 ms |
| orbite | 4.98 ms |

- Four initial V5 views, then two final views after the optical filter; targeted volume alone and V4 sample comparisons at 271 km.
- Final images, poses and footprints: `x64/WickedV5DeliveryPreview/`; comparisons: `x64/WickedV5OpticalPreview/`, `x64/WickedV5FinePreview/`, `x64/WickedV5WitnessPreview/`.
- Frame times are disturbed by other loads; these values are not a statistical measure.
- Native: `E1C1CCF785171ADD3EA52ED293711C39C8B999A60BC54BEEA08AA0F756EE3C21`.
- Shader: `4C4212025774F01983B32C9F34A5C9B20E6738B261C7F0DA4CAAE6E917FBB28C`.
- Table: `35D941E685664C2CEAE26A72F95509F3B24BACF94F73BA11C252349BB31ABE87`.
- The V4 and V2 binaries remain intact; no commit, tag, or push requested.

**History:** [search, V1 to V4 and excluded tests](spike-nuages-reference-historique.md).


---

## Diagnosis after V5, before weather test A

# Spike clouds: diagnosis after V5

**State, 27 October 2026:** V5 not retained after flight judgment. The V4 remains the benchmark; it retains repetitions and radial bands. None of these versions is a validated planetary solution.

**Findings:**

- The LOD V5 makes the look less good: repetitions persist, outlines become sharper and the noise disappears without convincing organization.
- The V5 also changes the nearby shapes: raising the cover in some regions and filling the hollows to join the layers.
- J only disables the LOD; it does not restore the V4 shapes.
- The bases and summits remain too flat despite their continuous ramps and their height variations.
- The current families modulate a same density recipe; no separate cirrus model is implemented.

**Diagnosis of the code:**

- The volume is bounded by local elevation profiles; it is not a graphic clipping.
- The base uses a smoothness of 80 to 160 m; the top, from 160 to 400 m.
- High extinction can make these ramps opaque quickly; softening only their interpolation does not guarantee a natural outline.
- The shell 1–9 km is used for the course; it should not be confused with the visible boundaries of local profiles.
- The NASA map provides a coverage proxy from luminance; G/B/A remain synthetic and do not describe a consistent weather state measured.
- The conversion of luminance raises the low values by `0,25 + 0,5 × sqrt(L)` above `L = 0,03`.
- Audit of mip0 V4 shared with V5: R exceeds 0,03 on 79,81 % of spherical area, average R of 0,4038.
- These numbers describe the presence parameter; they do not measure the cloud fraction rendered.

**Comparison retained:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-wicked-v5.ps1 -Temoin -Static
```

- Opens the frozen V4 with the same positions and palette as the V5.
- Without `-Temoin`, the launcher opens the rejected V5 to reproduce the test; `-FineOnly` retains its shapes without LOD.
- F1/F2: proximity and 10 km; F3/F4/F5: 30/80/160 km; F6/F7: 271/454 km; F8: orbit; F9/F10: plate; F11: other region; F12: pole.
- Space: weather break; C: fine quality; B: opacity; N: clouds; V: weather ×5.
- No binary, shader, or setting changed as a result of this diagnostic; user session retained.

**Following to isolate:**

- Evaluate regional distribution without simultaneously changing the LOD and nearby forms.
- Distinguish density recipes of clusters, sheets and a possible high fibrous layer.
- Process volume contours before resuming the far filtering.
- Keep the samples and quickly hand over each test to the user for flight judgment.

**History:** [search, V1 to V5 and excluded tests](spike-nuages-reference-historique.md).


---

## Weather A: distribution test, kept as a control of the patterns

# Weather test A: distribution only on V4

**State, 27 October 2026:** comparison prepared, three pairs of hidden captures checked. Test delivered to the user for flight judgment. V5 is not retained; the frozen V4 serves as a witness.

**Launch the candidate:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-meteo-a.ps1 -Static
```

**Launch the stick at the same positions:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-meteo-a.ps1 -Temoin -Static
```

- Departure into orbit; F1 regains planetary view.
- F2/F3: old view of the patterns at 271/454 km; F4/F5: close clusters and views from above.
- F6/F7: known blanket at 8/271 km; F8/F9: dense region at 400/10 km.
- F10/F11: region of holes at 271/30 km; F12: pole.
- The same twelve positions and suns are used for both maps.
- Space: weather break; N: clouds; C: quality; B: opacity.
- `-NoLaunch` prepares the candidate without opening a window; no build required.
- Isolated executable: `x64/NuageWickedMeteoA/MyPlanetEngineWickedMeteoA.exe`.
- `-Temoin` does not write to the V4 or its assets.

**One variable:**

- The luminance L comes from the same image NASA, resized in the same way and oriented in the same reference frame.
- Old curve: R null under L=0,03, then `0,25 + 0,5 × sqrt(L)`.
- Candidate : `R = 0,75 × smoothstep(0,08, 0,68, L)`.
- The 0,08/0,68 thresholds and the 0,75 ceiling are settings of this visual test, not a weather law.
- Low luminances no longer have a positive floor; strong regions keep high coverage.
- R remains a coefficient of the density recipe; it is not a measured cloud fraction.
- Change R changes local silhouettes and continuity via existing sealing; the shape recipe remains the same.
- Mip1 medium and mips2+ by conservative maximum, like the control.

**What is retained:**

- Binary and all shaders copied from the frozen V4; no compilation or replay GPU.
- Three 3D textures identical bit by bit; GBA identical on the eleven mips of the card.
- Vertical profiles, lighting, animation and path V4; no LOD or fill of the sheets V5.
- Floors and ceilings too clear, repetitions and radial bands remain open; no distinct cirrus.
- The distribution of types and altitudes remains synthetic; this map does not simulate a complete consistent weather state.

**Short control:**

- Six hidden captures: three views per map, in orbit, at 271 km and above a nearby blanket.
- Weak areas are less covered; the repetitive pattern remains visible in dense benchmarkss at medium distance.
- The test confirms that the distribution is not sufficient to explain this pattern; no other adjustments were added to mask it.
- The copies of the executable and shader have the same footprints as the witness.
- Area-weighted R mean: 0,403798 for V4, 0,215494 for the candidate.
- This measure does not give the coverage rate rendered.
- Data and Comparisons: `x64/WickedWeatherACompare/`; GPU shared, no performance measurement or motion validation.
- Density can change the length of paths despite an identical shader; no performance gains promised.

**Reproduction:**

- Generator: `tools/gen_wicked_weather_a.py`; assets: `assets/wicked-clouds-weather-a/`.
- The cache depends on the parameters and footprints of its inputs; generation less than a second in this environment.
- Map SHA-256: `4AE42A455682D0ECD0862E22361947EBF5BEA0615A6FF0F6170AD6092B8FBBF3`.
- Executable SHA-256: `E7583D53ED5418C2841D9879D2C214567771EB8256A716ACB6A45A5CC82B46E8`.
- Shader SHA-256 : `D0777E1D538283313D6B348EE81BC0C69664B4BED9FF4CACF4CB688C4114CC47`.
- No commit, tag or push requested.

**History:** [research, V1 to V5 and diagnostics](spike-nuages-reference-historique.md).


**Forms A, intermediate control:** the first recipe of layer with wide field without contrast gave a layer too uniform. The field at mip3 has p10=0,595, median=0,719 and p90=0,825; its low amplitude almost everywhere passed the coverage threshold. A single correction remaps this field before the threshold, and separately normalizes its variation from the support. Initial sources and shader in `x64/Recovery/FormsAInitial/`, first three pairs in `x64/WickedFormsACompare/`; the final two comparisons are in `x64/WickedFormsAFinalCompare/`.


---

## Forms A: return in flight, insufficient test

**User feedback:** repetitive sizes and shapes, flat surfaces at the top and bottom, large contours too smooth and geometric. The fades applied after seiling were not enough to correct the silhouettes. Forms A remains a test case, not a validated solution.

# Forms A: cumulus and clouds on weather A frozen

**State, 27 October 2026:** shader compiled, short comparisons produced and inspected; in-flight judgment to user. Weather A with the V4 rendering is kept as the exact witness.

**Launcher:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-formes-a.ps1 -Static
```

**Compare to weather warning A:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-formes-a.ps1 -Temoin -Static
```

- F1/F2: profile and base of cumulus; F3/F4: their peaks from 8 and 10 km.
- F5/F6: base and profile of a layer; F7/F8: view from 6 and 30 km.
- F9/F10: other layer; F11: patterns at 271 km; F12: whole planet.
- Both modes use the same positions, suns and weather clock.
- Space: weather break; C: quality; N: clouds; B: opacity.
- `-Build -NoLaunch` compiles the only shader of this test and prepares its file; no native build.
- Exit: `x64/NuageWickedFormesA/MyPlanetEngineWickedFormesA.exe`.
- Witness: `x64/NuageWickedMeteoA/`, assets frozen in `wicked-clouds/`, footprints in `witness-forms-a.json`.
- The launcher checks the witness and does not write to it; its current session is retained.

**Separate income:**

- Weather map A remains unchanged; G continuously mixes cloud cover and cumulus, without changing regional distribution.
- Cumulus uses the primary 3D form field of 8 km period and a wide input.
- The sheets use the wide field of period 32 km, at fixed mip3; their vertical support is less thick.
- The raw layer field is remapped by `smoothstep(0,55, 0,85, sheetMacro)` before the cover threshold to retain wide holes.
- Local heights use `smoothstep(0,50, 0,90, sheetMacro)`; they are not dependent on macroLod or camera.
- B always gives a base of 2 to 4 km, A a reference thickness of 0,5 to 4 km.
- The height fraction is 0,35 for clouds and 0,88 for cumulus.
- The base amplitude is 0,10 to 0,30 km; the summit amplitude is 0,18 to 0,90 km.
- The half-fade widths are 0,22 to 0,40 km at the bottom and 0,24 to 0,50 km at the top.
- Smoothstep fades are applied after covering and erosion; no threshold intersects them afterwards.
- The phases of the wide field come from the absolute coordinates in double precision precision and a local float rest; the anchor does not move the patterns.

**Support and cost:**

- Global low bound: `2 − 0,15 − 0,40 = 1,45 km`.
- Global high-end: `4 + 4 × 0,88 + 0,45 + 0,50 = 8,47 km`.
- Density extinguishes strictly before the acceleration shell 1–9 km; no height clamp is used to impose these limits.
- Local rejections use the same conservative extrema before form readings.
- Five readings maximum per occupied density, like V4: weather map, deformation, two shapes, detail.
- No new volume, resource, history, path or pass; only `AtmosphereWicked.cso` changes.

**Controls:**

- Compilation DXC ps_6_0 O3 successful; preexisting shift warning in Materials.hlsli.
- Executable and four textures identical to the witness; all other shaders and code of the walker, light and composition unchanged.
- Three initial pairs, then two targeted pairs after the correction of the layer contrast; two locations, cumulus and layer.
- The holes in the blanket are wider; the fades and summits of the cumulus change visibly in these captures.
- Final data: `x64/WickedFormsAFinalCompare/`; captures do not validate movement, nor all distances, nor realism.
- GPU shared; no p95, benchmark full or performance gain announced.
- Final shader SHA-256 : `6D65FF9FF893418A57A165E993AA88B01F7CB21D6B45086B65586C16395D0CED`.
- Weather map SHA-256 unchanged: `4AE42A455682D0ECD0862E22361947EBF5BEA0615A6FF0F6170AD6092B8FBBF3`.

**To be judged in flight:**

- A clear difference between clouds and cumulus; bases and summits less artificial, even during the crossing.
- Anchoring of shapes during approach in frozen weather.
- The sheets may remain very smooth; dense cumulus may still appear solid and long vertical faces remain to be judged.
- No cirrus or new LOD; distant repeats and radial bands remain separate subjects.
- No commit, tag or push requested.

**History:** [research, trials Wicked and weather A](spike-nuages-reference-historique.md).


**Forms B, preparation:** a first potential using the raw range of the noise gave a uniform veil. Refocus and bounded contrast without plateau, then height variation and domain distortion enhanced. The weather3D texture has a constant alpha of 1; the band blending uses RGB, after data check. First density only comparison in `x64/WickedFormsBCompare/`, targeted delivery in `x64/WickedFormsBFinalCompare/`.


---

## Forms B: disturbance at the wrong scale

**User Feedback:** The deformation stretched individual clouds into strange shapes, while the request was for large currents and the organization of the sets. The local warp of ±12 km is therefore removed in favor of a soft setting. The macro transport should change the R cover as well, not just the GBA borders. Forms B remains frozen as a witness.

# Forms B: volumes, scales and regime boundaries

**State, 27 October 2026:** prototype compiled and short controls; in-flight judgment to user. Forms A is considered insufficient and retained as an exact witness.

**Launch:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-formes-b.ps1 -Static
```

- `-Temoin` opens Forms A with its frozen weather A.
- `-MeteoA` opens density B with the old map, to isolate the regime disturbance.
- `-Build -NoLaunch` only compiles shader B and prepares the data.
- F1-F4: cumulus; F5-F8: cloud cover; F9/F10: other cloud cover; F11: 600 km; F12: 1 600 km.
- Space: weather break; C: quality; B: opacity; N: clouds.
- Binary: `x64/NuageWickedFormesB/MyPlanetEngineWickedFormesB.exe`.

**Model change:**

- The silhouette is no longer a filled field between two vertical ramps with plateau.
- Potential: `p = noise3D − (1 − couverture) − z² − 0,12 × erosion`; density `gain × max(p,0)²`.
- The 3D field and the height penalty together form the surface; the density is C1 to zero.
- Two differently oriented period domains 8 and 29,3 km are mixed with variable global weights.
- The wide period field 128 km is used for deformation, weights and height variation, at fixed mip1.
- Maximum deformation per component of ±12 km; no reference frame or weight chosen by camera.
- Contrast of noise bounded by a smooth rational function, without plateau at 0 or 1; gain of 0,65 for sheets at 0,55 for cumulus.
- Nominal center `base + 0,4 × épaisseur`, displaced from ±0,25 km; maximum half height from `0,35+0,1T` to `0,5+0,4T` depending on type.
- The local half-height varies from 60 to 100% of its boundary for the sheets, from 30 to 100% for the cumulus.
- Conservative global support between 1,25 and 7,95 km, strictly in the shell 1–9 km; no clamp to respect these limits.

**Macro borders:**

- The audit identifies G as the probable cause of the too smooth family boundaries; this is not evidence by projection of user captures.
- Weather B deformations together G/B/A on the sphere, with two noise bands17 and43 and an angular limit of0,08 rad.
- R is identical bit to bit on the eleven mips; the NASA cover and conservative maxima remain unchanged.
- The three 3D textures remain identical; GBA are filtered by average after deformation.
- It is a visual disturbance of synthetic regimes, not a weather simulation.
- Generator: `tools/gen_wicked_weather_b.py`; data and manifest: `assets/wicked-clouds-weather-b/`.

**Isolation and control:**

- Executable, resources, lighting, extinction, walk and composition identical to the witness; only the density shader and, in normal mode, GBA change.
- Maximum of five readings per occupied density, card included; actual number of steps traveled may change with opacity.
- DXC successful; warning pre-existing in Materials.hlsli. Testimony fingerprints and R/textures invariants controlled.
- Short comparisons on two nearby locations and a view at 600 km; no complete benchmark or movement validation.
- Initial data: `x64/WickedFormsBCompare/`; delivery: `x64/WickedFormsBFinalCompare/`.
- The distant repetitions and the layer effect remain to be judged; no overall result validated.
- The final control shows more variable heights but repetitions still visible at 600 km; none of the three defects is declared resolved.
- Point clouds+air times: near17,40 ms against4,92 ms for the witness; at600 km10,27 ms against9,42 ms. GPU shared, values without statistical scope; close regression remains a problem.
- Shader delivered SHA-256: `5F275B573E8213F6F78D5D88A5C834CFEA6255DCD72309906C2A74F1A6FDFFEF`.
- No commit, tag or push requested.

**History:** [Wicked, weather A and Forms A](spike-nuages-reference-historique.md).


---

## Currents C: before the local reference Frostbite

**Balance:** transport corrected the scale of the disturbance, without resolving silhouettes, repetition and profiles too flat. Reading the Frostbite report motivated a local reference, with noise functions author and choice of explicit profiles. Currents C remains frozen as a witness.

# Currents C: macro organization, local forms preserved

**State, 27 October 2026:** compiled comparison and two pairs of macro captures inspected. Return to the user. Fixed disturbance scale; no announced resolution of repeats or ceilings.

**Launcher:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-courants-c.ps1 -Static
```

- Starts on the user view at 180 km; F11 finds this view.
- F12: another set in the southern hemisphere at 1 600 km; F1–F10: close controls already known.
- `-MeteoA`: same shader C, original weather map A; this comparison isolates macro transport.
- `-Temoin`: Forms B and its weather B frozen, with strong local deformation rejected.
- `-Build -NoLaunch`: compiles only the C shader and prepares the data.
- Space: weather break; C: quality; N: clouds; B: opacity.
- Isolated exit: `x64/NuageWickedCourantsC/MyPlanetEngineWickedCourantsC.exe`.

**Separate scales:**

- Shader C takes B with only one shape correction: amplitude of the local warp24 vers3, or ±1,5 km per component instead of ±12 km.
- The new organization is pre-calculated in the weather map; it does not distort the local noise3D coordinates.
- Source: weather A frozen in `x64/NuageWickedFormesA/wicked-clouds/`, without B's perturbation GBA.
- RGBA are transported together on the sphere by a very smooth tangent field, at frequencies2 and4.
- A spherical exponential step transports the reference backward; no new temporal integration in the engine.
- Scales of grid cell estimated at 3 189 and 1 594,5 km; correlation proxies measured at 850 and 426 km.
- Median travel182 km, maximum573 km; pillar638 km.
- This field is a static transport reference, not a physical simulation of atmospheric currents.
- The R coverage changes this time; mip1 mean and mips2+ per conservative maximum are reconstructed. GBA are averaged.
- The three 3D textures, local phases, light, walk, resources and native code are preserved.

**Controls:**

- DXC successful; warning pre-existing in Materials.hlsli.
- B/C shader difference limited to the return of warp24 vers3; witness B intact, four real assets frozen in `witness-courants-c-assets/`.
- mips RGBA independently verified; no fold measured on523 264 card cells, minimum oriented area ratio0,245.
- Two hidden pairs, at 180 km on user view and at 1 600 km in the south, with the same shader C and A/C. cards
- The sets move and change contour without the strong twist of the local coordinates of B; fine repetition persists.
- Comparisons and footprints: `x64/WickedCurrentsCCompare/`; source map, manifest and fields: `assets/wicked-clouds-weather-c/`.
- No benchmark complete, p95, performance gain or flight stability verdict.
- Shader C SHA-256 : `F2D856EDABA17B6FD44E32D3222C1B88B4BCD9D015738CBF9E0AE04474B8F31C`.
- Map C SHA-256: `DF67169C5DBC7E1197B043D1853A4A91EAAC20E96C09CF204A383AE4C5C8988E`.
- No commit, tag or push requested.

**Limits:**

- The local recipe and its defects of silhouettes, distant filtering and near cost remain those of B, with reduced deformation.
- Transporting the reference does not create dynamic weather or a new variety of formations.
- The card is filtered on its grid1024×512; the cell control is discrete and does not show any deformations under the texel.

**History:** [search, weather A, Forms A and B](spike-nuages-reference-historique.md).
