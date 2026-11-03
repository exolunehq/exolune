# Near vegetation rendering

**Status**

- Implemented on codex/vegetation-biomes, 2026-11-03.
- Visual iteration uses hidden native screenshots and unchanged world seeds.
- Art, complete quality and performance acceptance remain separate gates.
- The current bank contains three oak derivatives and one radial hybrid kapok candidate.
- The planar kapok is retired from this bank; source oak branch cycles remain an art limitation.

**Geometry and approach**

- Keep source wood and UVs at L1 through L4.
- Refine L0 trunk curvature offline with adaptive cubic PN edges and centres.
- Preserve every original vertex and UV seam.
- Keep underside triangles unchanged and new root heights barycentric.
- Bound root curvature horizontally to 0.1% of normalized height.
- New curvature uses averaged coincident normals and local winding safeguards.
- Bound displacement to 12% of its edge and 0.5% of normalized plant height.
- Add at most 20,000 triangles; stop adding work at 100,000 total triangles.
- This interpolates curvature; it does not recover a missing high-resolution sculpt.
- Reduce leaves, shoots and texture resolution progressively.
- L0/L1/L2 retain curved leaves.
- L5/L6 reduce wood with section and root-surface checks.
- Seven-level spacing uses projected-size ratio 1.55 with complementary fades.
- Legacy five-level assets remain compatible.
- The same plant retains its impostor and its stable world identity.
- Wind reaches zero before the static impostor relay.
- Instance queues remain 192 MiB; order indices remain 12 MiB.

| Witness | L0 | L1 | L2 | L3 | L4 | L5 | L6 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Spreading oak | 53,423 | 33,741 | 29,097 | 19,035 | 14,391 | 6,269 | 2,866 |
| Radial hybrid kapok | 76,425 | 52,555 | 45,515 | 37,595 | 32,315 | 6,800 | 2,960 |

**Foliage light**

- Blend individual leaf normals with the crown gradient, 65%/35%.
- Preserve woody normals and attachment data.
- Bake resulting normals and leaf masks into every representation.
- Separate thin leaves from woody shoots inside masked materials.
- Wrapped diffusion preserves the random-orientation Lambert mean of one quarter.
- Backlighting uses transmission 0.45 and a bounded forward phase.
- Mesh materials use dielectric GGX instead of the previous Phong lobe.
- Leaf roughness blends 55% toward 0.62; dielectric F0 is 0.035.
- Decode acquisition visibility floors before applying porous transport.
- Impostor diffusion retains mean-normal coherence.
- Canopy bounce derives from intercepted sunlight, with coefficient 0.12 and colour weights 0.45/0.65/0.32.
- Record that bounce in the solar attachment for cloud shadows.
- Diffuse canopy transport includes leaf scattering 0.28 and return factor 0.5.
- Sky transport is (gap + 0.28 * intercepted) / (1 - 0.14 * intercepted).
- Open ground retains unit transport; closed crowns retain about 0.46 instead of 0.21.
- Sky and sun remain separate throughout cloud compositing.
- Ordinary tufts and rocks store unshadowed reflectance, with eight canopy bits in the blue mantissa.
- Decode colour before shading; apply direct and indirect transport separately.
- This preserves the 64-byte instance layout and existing queues.

**Forest floor and observer**

- The orbital biome palette includes dark canopy reflectance; it is not exposed litter.
- Closed forests use broadleaf litter reflectance 0.24/0.18/0.105, or conifer 0.20/0.145/0.09.
- Humidity reduces litter reflectance by at most 22%; existing rock, beach and snow overlays remain.
- Roots read the same material colour as the terrain.
- Exposure retains the open incident-light baseline and orbital calibration.
- A separate observer response meters bounded sun/sky transport under the camera's canopy.
- Reuse the habitat probe and its existing frame fence; add only one float4 to its readback.
- Gain is at most four, or two stops; coverage fades above the crowns and gain vanishes at night.
- The 0.35 s interactive response depends on the world, never the image or viewing direction.
- Hidden stills use the settled canopy value for reproducible review.
- Apply exposure after the linear history; this does not add light to scene radiance.

**Close bark**

- Keep the source UV colour and macro normal map.
- Preserve full woody normal-map strength; thin leaves retain their 0.55 bound.
- Add metric gradient-noise bands at 18, 64 and 200 cycles per metre.
- Heights are 8, 1.2 and 0.2 mm; longitudinal scales remain longer.
- Reuse the ground material's Noise3; shift the bands to avoid shared lattice nodes.
- Filter each band by its pixel footprint before taking a surface gradient.
- Rest-pose coordinates keep detail attached during wind and root fitting.
- Bound added slopes to 0.55 and retain rough bark response.
- No new runtime texture, material ID or instance queue is required.

**Coverage filtering**

- Temporal smoothing is enabled by default; T toggles it.
- MYPLANETENGINE_TAA=0 actually disables it; earlier presence-only parsing treated 0 as enabled.
- Accumulate filtered impostor alpha as area coverage.
- Mesh leaves derive edge coverage from the alpha derivative.
- Depth and colour share the exact coverage seed and frame.
- Mesh relay, mesh-level relay and alpha use three digitally shifted Sobol dimensions over 64 frames.
- Each dimension visits its 64 strata once; joint half-coverage retains all eight octants equally.
- Fractional impostor alpha retains conservative depth bounds down to 1/1024 coverage.
- MYPLANETENGINE_FOLIAGE_WHITE_NOISE=1 selects the previous white sequence as a functional control.
- A changing coverage sequence requires temporal smoothing; otherwise freeze its frame.
- Existing ocean motion pixels remain outside temporal history.
- The resolve remains the existing bounded history filter, not a new TSR or motion-vector system.
- Native captures record effective settings in the foliage-filter sidecar.
- Forestlight diagnostic channels are canopy cover, material cavity and diffuse canopy transport.
- Groundalbedo shows material colour independently of lighting.

**Local contact lighting**

- Reconstruct positions and normals from current HDR distance.
- Evaluate eight directions and three squared-radius samples at half resolution.
- Bound indirect occlusion to a 1.2 m support.
- Trace six solar contact steps from 0.04 to 1.28 m.
- Reject unrelated depth neighbours and fade at screen borders.
- Fade both effects from 96 to 192 m.
- Reconstruct full resolution with four depth-weighted samples.
- Apply AO to indirect light and sun contacts to direct light.
- Preserve HDR distance and the ocean motion sign exactly.
- Use one RG16F half-resolution image, about 2 MiB at 1080p.
- No temporal history or additional CPU/GPU synchronization.
- Skip diagnostic views, wireframe and unsupported typed UAV loads.
- MYPLANETENGINE_LOCAL_CONTACTS=0 supplies the functional control image.

**Limits and validation**

- Contacts use visible depth and cannot cast complete off-screen crown shadows.
- Precise long tree shadows need a world-space caster solution.
- Cached six-direction self-visibility remains approximate.
- Legacy procedural tufts share sun/sky transport but retain simple geometry and self-shading.
- The reviewed master supplies maximum close detail.
- The tropical witness combines a generated lower trunk with a deterministic radial branch scaffold.
- It has one master, five catalogue roles and its own seven levels and impostor; these are not five species.
- Legacy placement still sets species crown width; a source preview does not establish native silhouette approval.
- Validate exact protected wood, root UVs, maps and seven native levels.
- Compare repeated poses, wind, several climates and backlighting.
- Contact-on/off controls use identical executable and shader hashes.
- Current L0 upgrades pass stream, unchanged root-UV, winding and protected L1–L4 material audits.
- The native refinement review retains fourteen views, including diagnostic-to-natural relay, with zero queue overflow.
- Thirty-eight root/branch views exercise all seven forced levels, repeated identities, stationary feet, visible wind and contact controls.
- Twelve additional native views exercise the radial tropical candidate and all seven forced levels.
- F4/F5 report the same observer canopy; sea, orbit and above-crown controls report zero.
- Frozen default/white/disabled coverage controls retain their effective settings and all frames.
- Disabled controls are bit-identical; the sequence comparison is a static functional witness, not motion or FPS acceptance.
- Near-wood checks use an independently faceted cylinder with UV seams, fixed underside, root support and winding checks.
- Earlier native captures and contact-control measurements are archived in the pipeline history.
- New native appearance and temporal controls must use the effective smoothing settings.
- The max-channel tone curve makes display-channel changes distinct from linear radiance changes.
- Shared-GPU screenshots do not validate FPS.
- Current refinements, native images and functional controls remain under E:/ExoluneAssets/vegetation-refinement-2026-11-03/.

**Sources**

- [Epic: Two Sided Foliage](https://dev.epicgames.com/documentation/en-us/unreal-engine/shading-models-in-unreal-engine#twosidedfoliage): thin-surface transmission.
- [NVIDIA: SpeedTree rendering](https://developer.nvidia.com/gpugems/gpugems3/part-i-geometry/chapter-4-next-generation-speedtree-rendering): leaf normals and backlighting.
- [Intel: XeGTAO](https://github.com/GameTechDev/XeGTAO): finite support and depth-aware reconstruction; this local pass is an independent smaller horizon approximation.
- [Guerrilla: Horizon Forbidden West texturing](https://www.guerrilla-games.com/read/adventures-with-deferred-texturing-in-horizon-forbidden-west): bounded shading work for dense masked vegetation.
- [Vlachos et al.: Curved PN Triangles](https://www.cs.jhu.edu/~misha/ReadingSeminar/Papers/Vlachos01.pdf): curvature from positions and normals; local bounds are this pipeline's additions.
- [Mikkelsen: Surface Gradient-Based Bump Mapping](https://jcgt.org/published/0009/03/04/): metric procedural detail and gradient composition.
- [Godot: 3D antialiasing](https://docs.godotengine.org/en/stable/tutorials/3d/3d_antialiasing.html): coverage and temporal filtering tradeoffs.
- [Epic: Auto Exposure](https://dev.epicgames.com/documentation/en-us/unreal-engine/auto-exposure-in-unreal-engine): adaptation and shadow readability; this implementation uses a world probe, not an image histogram or Unreal's local exposure filter.
- Production chain: spec-pipeline-creation3d.md.
- History: log/spec-pipeline-creation3d-historique.md.
