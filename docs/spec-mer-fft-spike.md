# Spike: FFT ocean and persistent foam

**Status:** appearance validated in flight on 2026-10-26; rebased onto main 083bfb1, then integrated at jalon/23-mer-fft-main.
**Initial milestone:** jalon/22-mer-fft; base 47c404b preserved under piste/mer-fft-spike.

**Goal**
- Start again with a fresh near-field kernel after the rejection of white streaks and foam strips.
- The first iteration remains at tag `piste/mer-animee`; its documentation is in `log/recherche-mer-historique.md`.

**Architecture**
- Fetch-limited JONSWAP spectrum, Donelan-Banner spreading, separate swell.
- Four 256² cascades: tiles of 1,103, 113.1, 11.57 and 1.183 m; disjoint bands.
- Choppiness 1.25, damped below 40 cm wavelength; capillary ripples remain close to the linear model.
- Precomputed initial spectrum; time evolution, row FFT followed by column FFT.
- Shared outputs: XYZ displacement, five derivatives, slope moments and a second height moment in the spare fourth channel; mips every frame.
- Normal from the inverse horizontal Jacobian; unresolved covariance transformed by that Jacobian.
- Foam deposited according to the Jacobian; density and freshness in two 512² toroidal maps covering 128 and 1,024 m.
- Drift of 0.03 U downwind; density dissipates at 0.22/s, freshness at 1.6/s.
- Multiscale periodic pores precomputed on the GPU; white foam lit by the surface, trails aligned with the wind.
- About 40 MiB of nominal resources; no global texture.
- Local height for the camera, four GPU iterations and a 16-byte readback; 75 cm clearance.
- The FFT timer separates simulation from the remaining GPU work.
- On main: SRV t11 to t16, after shadow t9 and planet map t10; FFT timestamps 6 and 7, separate from objects.
- Main diagnostics 1 to 26 preserved; foam, glint, foamfresh, foamold and crest added as 27 to 31.

**Planet**
- Sky, atmosphere, bottom color, terrain and spherical mesh preserved.
- Transported tangent plane; coordinates accumulated in double precision on the CPU.
- Fractions modulo the tiles and differences of integer indices in shaders.
- Foam maps cleared after a camera jump or spectrum change.
- Displacement damped by depth; waves included in the visibility margin.

**Local coastal foam, 2026-11-04**
- The incident FFT height and height variance are read before depth damping, from the existing displacement/moment fetches.
- A crest exceeding 0.39 water depth activates a calibrated source, using the approximate depth-limited wave-height ratio 0.78; this is not a resolved breaker solver ([USACE, EM 1110-2-1420](https://www.publications.usace.army.mil/Portals/76/Publications/EngineerManuals/EM_1110-2-1420.pdf)).
- Unresolved incident heights retain their Gaussian exceedance probability. Mixed coastal pixels condition that mean on their immersed heights.
- Coverage is bounded by 0.75, with energy activation over 0.02–0.08 m RMS. Existing pores modulate nearby detail; the same coastal mean remains in distant shading.
- No new texture, buffer or FFT sample fetch is added. Terrain geometry and dry-land inundation are unchanged.
- Native flight review and mathematical verification are recorded with the mouth/bank work in `spec-erosion.md`; no benchmark is requested.

**Spike limitations**
- Uniform wind and swell set per view; planetary wind map remains to be connected.
- Coastal foam is a local depth-limited approximation. Refraction, shoaling transformation, foam transport through the surf zone and swash on dry ground remain untreated.
- Simplified distant transition to Cox-Munk and Monahan; near-field coverage not calibrated against Monahan.
- Reflection at 400 km: mean error of 2.8% at 12 m/s, 6.2% at 24 m/s; the 5% target is therefore not met in strong wind.
- The measured variation on a frozen sea as the mesh slides is not eliminated.
- Height field: no overturning wave crests or droplets.
- Visual success precedes integration; compilation and averages do not suffice to validate foam.

**State**
- Appearance accepted by the user after testing; connection to planetary wind and the limitations above remain open.
- Camera jump: cached ground height and GPU readback from the old position invalidated before collision.
- Initial benchmark at 30 locations, stability, poles, main integration and cost: [measurements and limitations in the log](log/spec-mer-fft-spike-historique.md).

**Try and measure**
- Palette `tools/tests/2026-10-26-mer-main.txt`, through the game launcher's `-Parcours` (`lancement.md`); F1 to F7 for the sea, F8 and F9 for forests, F10 for orbit, F11 and F12 for poles.
- Optional fourth column: wind speed, direction in degrees, significant swell height.
- MYPLANETENGINE_OCEAN_WIND supplies these three numbers at startup.
- MYPLANETENGINE_CAPTURE_FRAME sets the capture frame to allow trails to mature.
- tools/banc_qualite.py --reuse-sites précédent/qualite.json reuses locations and headings; all images, masks and scores are recalculated.

**Provenance and code**
- Simulation and foam material adapted from [Noniv/web-ocean](https://github.com/Noniv/web-ocean), commit a07c7fd522ef0a897601c114f927a49d93d95520.
- MIT, copyright 2026 Maksymilian Dendura; license preserved in third_party/web-ocean/LICENSE.
- DX12 scheduling, barriers, plane transport and precise toroidal coordinates specific to this spike.
- Ocean.cpp / Ocean.h: resources and scheduling; OceanCompute.hlsl: simulation; OceanSurface.hlsli / Sea.hlsli: geometry and light; OceanUniform.hlsli: constants.
