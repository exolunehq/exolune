# Detailed vegetation on the planet

**Status: baseline validated by the user on 2026-10-27; diversity extension awaits review.**
- The current `game_biomes_v1` technical prototype has 31 models, local communities, ground herbs, volumetric roots and wind; `spec-diversite-vegetale.md`.
- Its visual foundation is being reconsidered for original generation; `recherche-generation-vegetale.md`.
- The fourteen-model baseline remains a compatible fallback; its replaced limits are in `log/vegetation-planetaire-historique.md`.
- Sequel to `log/prototype-vegetation-volumique.md`.
- Base `piste/vegetation-planetaire-base`.
- Integration on `main`, milestone `jalon/24-vegetation-detaillee-main`; no push requested.
- The threshold of the benchmark quality remains unmet; the deviations are retained in `log/vegetation-planetaire-historique.md` and `arbustes-climatiques.md`.
- Delayed sequence: `optimisation-vegetation.md`, with aspect, density and range retained.
- The first tests were judged directly in flight; the subsequent application allows off-screen comparative iterations.
- The measurements of the isolated prototype do not validate the performance of this planetary version.
- The history of the first flights and corrections is in `log/vegetation-planetaire-historique.md`.
- A complete catalogue is required: diverse communities by default when built, otherwise the original twelve-shrub catalogue in `arbustes-climatiques.md`.
- **The only engine leaf since the 2026-10-30:** active by default, its settings hard. The other modes, the `photo` and `stylized` models and their launchers are removed; they are described in `log/vegetation-planetaire-historique.md`, tag `piste/vegetation-relais-fondu`.

**The connection:**
- The existing placement keeps the planetary grid, seeds, species, climate and heights.
- game models: coniferous and deciduous with branched branches and cut foliage.
- The size of the model follows the height of each instance; its width follows the crown provided by the population.
- Shrubs retain their instances, source sizes and rules of presence; the climate catalogue replaces the single shrub with twelve architectures.
- The terrain and the presence rule do not change.
- The placement window counts 512 tiles per octave, against 184 for generated plants.
- Plants come out at 5–8 pixels, against 14–21 for generated plants; the canopy uses the same drawing rule.
- The canopy retains plants that are not drawn individually, up to orbit.

**Representations:**
- impostors multiviews in the distance; mesh detailed close up.
- The representation is chosen per plant, with a relay fade (`PlanetFoliageMeshShare`, `PlanetFoliageLod.hlsli`):
  - between 0,8 and 1,25 times the threshold of the plant, it is in the two rows, impostor and mesh;
  - complementary coverage selects one representation per pixel; temporal smoothing is enabled by default and T toggles it. With smoothing disabled, coverage stays fixed instead of adding frame noise;
  - the key H cuts the fade in flight and returns to a single representation per plant, to compare; in free camera only, because in the views of the ship H turns the head.
- The choice depends on the height and width of a projected cylindrical crown, at its near depth.
- The threshold specific to each seed is between 96 and 128 pixels.
- Without fading, the passage is a clear jump of form and light; it was the rule of the 2026-10-27 to the 2026-10-29.
- The classification and indirect drawing calls remain on GPU, by species and representation.

**Queues and stability:**
- The candidate tiles have a fixed index; a prefix sum calculation keeps their order during compaction.
- Plants produced by tile are compacted in the same order to the near and distant lists.
- The limits thus keep a deterministic subset, even with a camera still; the order of arrival of the waves GPU no longer chooses the trees.
- Each source list accepts 262 144 plants.
- Each row of the renderer accepts 524 288 instances, which is the maximum union of the two source lists.
- Six rows group three renderer classes and two representations; up to 96 models partition the same 192 MiB instance buffer. Seven mesh levels reference it through a separate 12 MiB order buffer.
- The relay strip can copy a plant in both representations; it cannot saturate a downstream queue alone.
- Overruns of tiles and plant lists remain marked.
- Saturation can further reduce the geometric cover expected by the canopy; the choice remains stable, and the limit remains visible.
- Temporary storage of tiles and instances increases memory; this prototype prioritizes stability over compactness.

**The impostors optimized:**
- The rectangle is calculated in perspective projection, from the four sampled view planes.
- The shader reads color first and rejects transparency before normals, depths and visibilities.
- It is limited to the old square, with a margin of one pixel; the passage of the close-up keeps a conservative cover.
- Two textures `Texture2DArray` RGBA16F per species carry the linear color and the normale/profondeur.
- All components are pre-multiplied by the cover before building the mipmaps.
- Bilinear filtering and blending between mipmaps is done by hardware; the four angular views remain mixed in the shader.
- The heap reserves seven SRV per model and mesh level, up to 96 models and seven levels; shared levels reuse the same material resources.
- The impostors uses a fixed alpha threshold of 0,5; their mipmaps retains roughly the coverage per view.
- A silhouette support weighted by the four views protects the opaque core; color, normal and depth keep the original weights.
- The very small mipmaps still quantify the cover; the silhouette between views remains an approximation.
- The population, distances and thresholds remain those of the previous flight; the impostors take over the selected models.
- Compilation and static review only; no GPU time savings are measured yet.

**Game models:**
- The target is a realistic AAA game rendering, with leaves and branches readable in bouquets and irregular silhouettes.
- Full-bucket models were rejected by the user; their test is recorded in `log/vegetation-planetaire-historique.md`.
- Files `assets/foliage/game_fir` and `assets/foliage/game_broadleaf`; sources and reproduction in `assets/foliage/README.md`.
- Pine from evolveduk, 5 627 triangles; leafy Rakshi Games Tree10_1, 3 308 triangles, detailed foliage carried by alpha cards.
- Poly Haven Searsia Lucida f shrub, 7 232 triangles, opaque branches and cut leaves: the source of leaves and bark of climatic shrubs; credits in `../assets/foliage/game_shrub_origins.md`.
- Normals and roughness of the pine imported; normals Unity of the hardwood converted, roughness constant lack of exploitable source card.
- The quality is to be judged in flight; these accounts are neither a validation AAA nor a measure of FPS.
- The impostors and volumes are rebuilt from the selected mesh; volumes are only used offline, for light precalculation.

**Textures of the meshes nearby:**
- One layer per material in three texture tables: sRGB color, normals and masks UNORM.
- Material filtering anisotropic ×8 with repeated UV.
- Construction of mipmaps in linear color, alpha weighting, renormalized normals and coverage set to the threshold of 0,5.
- Colors are spread in the transparent texels to avoid dark borders.
- Raw atlases no longer go to the GPU: their bilinear folding reading is removed the 2026-10-30.

**Light and feet:**
- The textures of the models retain their color; sun, sky, shadow of the relief and surrounding cover participate in the light.
- The near mesh can load `material.bin`: OpenGL normals atlas, ambient occlusion, roughness and transmission.
- These maps add detail of bark and leaves, moderate spectral response and limited foliar backlight.
- The proxies keep an average normal; the detail of the normal maps is not reproduced. The impostors light up on the dispersion of their leaves (The lighting of the impostors).
- Generated trees keep their continuous authored root surface and exact source wood at L1–L4; legacy trunks retain burial extrusion.
- Root fitting and wind fade before the static impostor; proxies keep their own cooked bounds.
- The actual alpha fingerprints do not exactly match the theoretical disk of each crown.
- The preservation of cover and light at approach remains to be judged.
- Near-ground wind uses the shared climate and weather clock; its limits are in `spec-diversite-vegetale.md`.
- Near shading uses leaf-volume normals, two-sided transmission and GGX; `spec-rendu-vegetation.md` defines the current contract.
- Local depth supplies bounded contact occlusion and short sun shadows; complete tree cast shadows remain absent.

**The volume of foliage:**
- The derived variants are rebuilt by `tools/foliage/volume_assets.py`, then its option `--normals`.
- The original leaves are spread around the supporting branches; branches, atlases, pivots and bounds are preserved.
- Hardwood trees change from 3 308 to 7 010 triangles; shrubs from 7 232 to 13 406. The pine remains identical.
- The number of instances, seeds, sizes, relay thresholds, and scope remain unchanged.
- Foliary normals are oriented by local bouquets; no opaque envelope is added.
- A stable variation in colour per seed is limited to 6 %; it fades with the strength of self-shading.
- The alpha volume 64³ provides offline sixteen sky rays and six axial sun visibilities per vertex.
- The engine interpolates this self-visibility, then separately dims sky and sun; it traces no additional woody-volume rays per frame.
- The separate local contact pass samples visible scene depth within 1.28 m and fades out by 192 m.
- The impostorss carry the same visibilities in two RGBA8 textures; their filtering follows the alpha coverage.
- The six directions remain an approximation of self-shading; neighboring trees do not cast a precise shadow there.
- The strength of the self-shading is worth 0,65, hard: `VolumeStrength`, `PlanetFoliage.cpp`.
- An absent sidecar uses neutral data sized for all vertices; a HLSL branch does not guarantee the absence of speculative reading.
- The covering of trees and shrubs is composed by union for the lighting of the soil and objects; their addition sometimes produced a negative light.
- Ground and plant paths share porous canopy transport and smooth woodland shade boundaries; envelope cover no longer makes a fully opaque roof (`spec-diversite-vegetale.md`).
- The artistic criteria and the steps compared are in `log/vegetation-planetaire-historique.md`.

**Impostor lighting**
- Four cooked views and their mipmaps preserve fractional coverage and the mean normal length.
- Mean-normal coherence interpolates between a random leaf population and a single oriented leaf.
- Wrapped diffusion preserves the random-orientation mean of one quarter.
- Mesh and impostor share decoded self-visibility, leaf transmission and canopy transport.
- Impostor colour is filtered in linear light; the bake preserves alpha and directional lighting fields.
- Current rules and validation: spec-rendu-vegetation.md.
- The replaced 2026-10-29 investigation and measurements are in log/vegetation-planetaire-historique.md.

**Comparisons of the milestone 24:**
- Eight off-screen views on four biomes and two suns; optimization alone gives a median drawing of 9,34 to 7,43 ms, eight identical images bit by bit.
- The quality benchmark fails on 3 p95 on 59; the version is accepted as is with these known deviations.
- The detail, the benchmark of the forests removed and the reports: `log/vegetation-planetaire-historique.md`.

**Launch:**
- The game starts as `lancement.md` says; foliage is active by default.
- `assets/foliage/game_biomes_v1/biomes.txt` takes priority when fully built; its pipeline publishes readiness last.
- The former `biomes_v1` prototype and the fourteen-model baseline remain compatible fallbacks.
- The catalog is found alone: `MYPLANETENGINE_FOLIAGE_ASSETS`; otherwise the first one built above the executable, the repository one, then `plantes/climate_shrubs_v2`, published next to the repositories by `tools\plantes.ps1` and found by all worktrees, like scans.
- Without catalog, no vegetation, neither drawn nor in canopy: the naked planet, and the title says "absent vegetation" with reason. The canopy alone replaces the undrawn plants; everywhere, seen from under its crowns, it made a striated curtain (`journal-planete.md`, 2026-10-31). `MYPLANETENGINE_NO_PLANTS` keeps the canopy everywhere, for the benchmark vegetation.
- The `tools/tests/2026-10-27-arbustes-climatiques.txt` palette gives twelve views, by buttons or F1 to F12: two per climate group.
- The title indicates the FPS, the GPU times, the meshes and impostors counts by species and the overruns.

**To be observed during flight:**
- The readability of leaves, branches, breakouts and silhouettes during approach.
- Changes in light or cover during the relay.
- The feet, the silhouettes and the stability when the camera moves.
- The cost in dense forests, in raised view and on the ground.
- Any capacity overrun indicated by the title.

**Code:** `PlanetFoliage.cpp/.h`, `PlanetFoliage*.hlsl`, `PlanetPlantPlacement.cpp/.h`, `PlanetPlant*.hlsl`, `PlantPlacement.hlsli`, `Vegetation.hlsli`, `FoliageHiZ.cpp/.h`, `D3DApp.cpp`.
