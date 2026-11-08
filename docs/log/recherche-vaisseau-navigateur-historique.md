# Navigator ship authoring history

**Superseded material.** Current references and model: [Navigator research](../recherche-vaisseau-navigateur.md).

**Instrument modelling v5 before live integration**

- The detailed cabin packet had 460,291 vertices, 723,264 triangles and 13 material ranges.
- Amber and blue arcs and raised needles were fixed mesh details; no flight data drove them.
- `artifacts/navigateur-cockpit-son-2026-11-03/modelisation-v5/` preserves seven studio views and the GLB reimport close-up.
- That delivery was checked in background Blender without launching the game.
- Integration replaces fixed needles with flat optical faces carrying live heading and propulsion; centres and radii come from the console patches.
- The earlier native stills and studio lighting do not represent the current runtime review.

**Coherent cabin before instrument detailing**

- The accepted modelling base used six closed solids, 139 wall panels and a larger octagonal rear fitting.
- The runtime packet had 338,964 vertices, 582,148 triangles and 12 material ranges; 1,536 points checked the support interfaces.
- Console details were five long pressure tracks and two rows of red blocks on a recessed rear plate.
- The sensor used a simpler concentric housing, an amber face and a dark pupil.
- The user requested finer rendering, fittings and instruments.
- `artifacts/navigateur-cockpit-son-2026-11-03/source-v4/` preserves its source, palette and checks; `modelisation-v4/` preserves the studio renders.
- Current consoles replace those details with seated rotary controls, graduated faces, hand-sized tactile wells, engraved legends and captive fastener seats.
- Studio review changed from broad even illumination to distinct key, blue strip, warm return and reading lights; no studio illumination enters the exported asset.

**Primitive cabin and rejected sound candidates, 2026-11-03**

- The first cabin combined a fitted backing with separate floor, seat, consoles, ribs and sensor primitives at a 12% hull inset.
- The user requested coherent meshes with details anchored to their supporting parts.
- `assets/vaisseau/navigateur/archive/` retains that generator and GLB; current generation uses `cabine_maillage.py`.
- A subsequent six-solid cabin joined the wall, floor, station and sensor, with 148 panels and 295 mounting checks.
- The current revision replaces nine rear panels with a larger octagonal optical fitting, refines formed console wells and derives the cushion underside from the evaluated seat shell.
- Early curved panel caps used long triangle fans; extra surface sampling replaces their star-shaped reflection artifacts.
- Sound v1 used a 62–130 Hz beating field, inharmonic FM and higher glassy tones driven by thrust.
- The user heard a car or old-game sound after second 10 of the preview.
- Sound v2 removed the strong power-linked pitch movement but retained a broad wash; the user requested less reactor character because the craft has no visible reactors.
- Sound v3 reduces the wash and sub layer and uses quiet nearly stationary noise-excited resonances, without an exhaust layer.
- Original headers and preview files remain under `artifacts/navigateur-cockpit-son-2026-11-03/`; no movie samples were used by these synths.
- Earlier native cockpit stills show the six-solid cabin before the detailed instrument revision; the v5 review used offline Blender images.
- These stages are uncommitted; no tag or publication was requested.

**Superseded journal settings**

- The exterior-only Navigator started in chase view, with zero jets and pivots and no canopy simulation.
- It introduced the smooth ×4 shell, metallic 1, roughness 0.075 and linear base colour `(0.84, 0.87, 0.91)`.
- Scene HDR/depth reflections, the physical sky/planet fallback and 32-bit signed-distance overlay preceded the cabin.
- The first cabin switched startup to cockpit, with eye `(0, -0.65, 0.70)` m, three blue fixtures and a clear forward viewing field.
- Its initial original voice used continuous FM and beating oscillators, with thrust and maneuvers driving the tone.
- Current material, camera and transport settings are in `journal-planete.md`; rejected synthesis and construction choices are described above.

**Exterior-only runtime stage and mixed-audio extraction**

- The first selectable Navigator started in chase view, without a cabin or canopy simulation.
- Its smooth shell used scale ×4 and a complete exterior reflection pass.
- Four extra public videos and five short WAV cuts were recovered under `artifacts/references/navigateur/audio/`.
- Filtered copies adjusted bandwidth, level and fades, while retaining the movie's music and dialogue.
- The user rejected these mixed cuts as game sounds and requested a fresh synthesis.
- Automatic speech timing and visual inspection assisted those cuts; no listening assessment was claimed.
- The current cabin and original antigravity synthesis supersede that runtime stage; `spec-navigateur-cockpit-son.md`.

**Smooth v2 before runtime integration**

- The normalized smooth prototype initially had no calibrated game scale or fore/aft alignment.
- Its local studio material retained roughness 0.13; roughness 0.06 was an inspection aid.
- Game selection and runtime rendering were unchanged at that stage.
- Integration now uses an authored ×4 scale, nose −Y and roughness 0.075; see the current reflection specification.

**2026-11-03: generated and locally smoothed v1, replaced by the regular control surface.**

**First exterior prototype**

- Working directory: `E:/ExoluneAssets/navigateur-normal-v1/`.
- The normal closed shell uses `propstore-maquette-12.jpg` as its image condition.
- Native ComfyUI 0.43.0 runs TRELLIS.2 INT8 at 1024 with structure/shape/upsampling seeds 56/42/42.
- `api.json`, `workflow.json`, `history.json` and `manifest.json` retain the executed graph, input fingerprint, model fingerprints and outputs.
- Saved canvas: `Exolune/navigateur/01-normal-hull-trellis2.json` in the local ComfyUI workflow list.
- The preserved raw mesh has 12,000,534 triangles.
- Blender CPU voxel remeshing closes the surface before reducing it to 150,000 triangles.
- `cpu-remesh.json` records zero boundary edges and zero non-manifold edges after that conversion.
- Geometry and the analytic chrome material are authored separately; photographed lighting is not baked into the material.
- The generated surface also contains miniature wear; the review includes a smoothed derivative.
- Review images use the actual imported GLB under neutral and chrome materials from multiple directions.
- Delivery copy: `artifacts/modeles/navigateur-normal-v1/`, with the editable `.blend`, `.glb`, review board, workflow and source manifest.
- The delivered GLB was reimported and checked from both sides, above and below; it retains 150,000 triangles and zero boundary or non-manifold edges.
- This is an exterior shape proposal; production retopology, fold fidelity, exact symmetry, cabin and entrance remain to be authored.
- The longest extent is normalized to two units; metric scale and fore/aft alignment remain uncalibrated.
- Game assets, settings and model selection are unchanged.

**Why superseded**

- The user rejected visible dents and uneven reflections.
- Repeated local smoothing retained acquired miniature wear and reconstruction noise.
- V2 fits a smooth global shape and uses a regular quad control cage with subdivision.
- The intermediate degree-filter comparison and native direct-decimation failure remain in the local authoring folders, outside the current spec.
