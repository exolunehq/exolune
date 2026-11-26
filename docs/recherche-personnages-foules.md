# Characters, crowds and engine architecture study

**Status**

- Architectural and state-of-the-art study completed on 2026-11-21.
- Engine direction is decided: Exolune remains the single runtime engine, extended with modular MIT/zlib C++ libraries and offline authoring tools.
- Primary human-base authoring is decided: **MPFB2 inside Blender** (free, CC0, Python-scriptable) paired with upgraded calibrated PBR skin and eye maps, with no Unreal Engine 5.6 dependency.
- `Character Creator 5` and `MetaHuman` remain optional Milestone 2 fallback controls only if native close-range lighting review exposes a facial quality gap.
- **Milestone 1 and Milestone 2 runtime + optical MoCap + Style B modular PBR wardrobe implemented on 2026-11-21–22:** `ozz-animation` runtime (`SamplingJob`, `BlendingJob` smooth `walk ↔ idle` cross-fading and concourse stops, `LocalToModelJob`, `IKTwoBoneJob`, `IKAimJob`, asynchronous eye blinking), real 120 Hz CMU Graphics Lab optical MoCap BVH clips retargeted onto MPFB2's canonical 59-bone skeleton (53 `game_engine` + 4 arm twist bones + 2 `eyelid_upper_l/r` blink bones) with living animated fingers and torso/satchel arm clearance (`tools/characters/retarget_mocap.py`), per-archetype measured MoCap strides (`CHRPLC1` v2, zero foot sliding), volume-preserving **Dual Quaternion Compute Skinning** (`CharacterSkin.hlsl`), `ToneMap.hlsl` dynamic TAA velocity buffer, local 0–35 m shadow map, **Style B refined PBR** hybrid asset chain (3-piece Tripo H3.1 solarpunk wardrobe kit locally decimated into semantic PBR classes in Blender with zero generated atlases, tailored trousers/belt/strap, procedural multi-layer hair cards, refined smooth skin albedo + deduplicated tileable tactile linen/leather/rubber/brass BC5 normal + ORM synthesis in `tools/characters/cook.py`), naturalist shading (Pre-Integrated Penner skin SSS, wet corneal eyes, Charlie cloth sheen, Kajiya-Kay temporally dithered hair, foot-ground contact AO) and 12 obstacle-validated actors around the extended city spaceport (`tools/tests/2026-11-21-personnages-spatioport.txt`). Next milestone: Milestone 3 (Jolt Physics, EnTT, Recast/Detour + RVO steering, batched GPU terrain probes, Clustered Forward local lights, 30–100+ NPCs).

**Target gameplay and crowd scope**

- Exolune is a solo open-world space and planetary exploration sandbox.
- Cities, villages, markets and stations are populated with 100 to 300 visible coherent NPCs alongside key interactive characters.
- Crowds follow day/night schedules, walk paths and stairs, avoid obstacles, and react to live world signals such as rain, wind, dusk and landing ships.
- First-person walking remains the primary view for the first milestones; a visible player body and third-person camera come after crowd foundations work.
- Populated spaces cover outdoor plazas, markets, spaceports and open covered halls, lit by artificial local lights at dusk and night.
- Full-scale vehicle/ragdoll chaos, close-up cinematic lip-sync cutscenes and multiplayer replication are outside the current scope.
- Development runs as a solo or very small team (1 to 3 people) assisted by coding agents, prioritizing iteration speed and architectural clarity.

**Engine architecture decision**

- **Keep Exolune as the single runtime engine, enriched with modular C++ libraries.**
- `MyPlanetEngine` currently implements real-scale planetary rendering in about 35,000 lines of C++ and HLSL with zero heavy runtime dependencies.
- That compact codebase already delivers double-precision GPU relief, tectonics, erosion, volumetric clouds, FFT sea, Hi-Z foliage, physical atmosphere and local eye adaptation.
- Adding targeted C++ libraries preserves 100 % of the planetary renderer, frame budgets, PolyForm Shield compatibility and rapid AI-assisted iteration.

| Option | Visual coherence | Planetary core | Gameplay & character velocity | Verdict |
|---|---|---|---|---|
| Dual-engine parallel rendering (shared DXGI surfaces) | Broken across lighting, clouds, shadows, reversed-Z depth, transparency and TAA | Fragile GPU bridge and terrain readback loop | Lost in synchronization and glue code | **Rejected.** Creates two sources of truth and breaks Exolune's physical pipeline. |
| **Exolune runtime + MIT/zlib C++ libraries + offline authoring tools** | **100 % native** through shared HDR, `sunPart`, `LocalContacts`, clouds and `ToneMap` | **100 % preserved** | Strong on characters, crowds and physics; light editor/UI assembled incrementally | **Selected.** Fits solo/small-team open-world crowd simulation and planetary scale. |
| Port planetary core into Godot 4.6 (`GDExtension` + `RenderingDevice`) | Requires shader and lighting port | Must rewrite ~25,000 lines of double-precision HLSL; `CompositorEffect` restricts direct Forward+ depth writes | Good lightweight editor; moderate high-end character gain over `ozz` + `Jolt` | **Rejected.** High migration cost without decisive character-rendering gains. |
| Port planetary core into Unreal Engine 5.6/5.7 (LWC + RDG plugin) | Strong on characters; risks losing Exolune's planetary look | GPU shaders stay float32; real-scale planets fight Nanite, Lumen and stock sky/clouds | Unmatched built-in character, sequencer, UI and multiplayer suite | **Deferred.** Revisit only if the project pivots to a studio-scale narrative RPG with a larger team. |

**Runtime C++ middleware stack**

- **Skeletal animation and IK (`ozz-animation`, MIT):** zero-dependency SIMD C++ runtime for quantized clip sampling, layered blending, partial masks, two-bone foot IK and aim/look-at IK.
- **Physics and character collision (`Jolt Physics`, MIT):** multithreaded rigid-body, capsule character controller (`JPH::CharacterVirtual`) and optional ragdoll solver with native double-precision support (`JPH_DOUBLE_PRECISION`), run inside a local tangent bubble around the observer.
- **Navigation (`Recast & Detour`, zlib):** local NavMesh generation over graded terrain, city walkways, stairs and station decks, paired with local crowd avoidance (RVO/ORCA steering).
- **Entity and crowd architecture (`EnTT` or `flecs`, MIT):** data-oriented ECS to decouple actors and crowd tiers from `D3DApp.cpp`.
- **UI and debug tooling (`Dear ImGui` + `RmlUi`, MIT):** ImGui for inspection and world authoring overlays; RmlUi for lightweight in-game HUD and menus on DX12 when gameplay expands.
- **Gameplay scripting (`Luau` or `Lua + sol2`, MIT):** hot-reloadable schedules, dialogues and mission logic added when world interactions begin.

**State of the art: authoring, rigging and motion (2026)**

- **One canonical humanoid skeleton rule:** every human character shares one game skeleton (60 to 75 bones: spine, limbs, simplified hands, neck, head, jaw) so every locomotion and interaction clip plays across the entire crowd without runtime retargeting.
- **Modular wardrobe diversity:** combine a small set of base human morphs and heads with modular solarpunk clothing, headwear, bags, tools and per-instance shader tint/fabric variations to avoid clone crowds.
- **Outfits, props, robots and fauna:** author through the existing image-to-3D and Blender route (`spec-ville-procedurale.md`), using Tripo H3.1 plus open-source autoregressive auto-rigging models (**UniRig / SkinTokens**, **Puppeteer**) and **MagicArticulate** for articulated mechanical assets.
- **License boundary:** do not adopt checkpoints whose licences exclude the EU (for example Hunyuan3D-2.1 community terms).

**Human-base authoring decision (Blender-native MPFB2 selected)**

- **Selected primary base: `MPFB2` (MakeHuman 2 plugin inside Blender)** with upgraded calibrated PBR skin and eye textures (albedo, pore micro-normal, roughness, curvature/SSS mask).
- This eliminates Unreal Engine 5.6, RigLogic `.dna` conversion, multi-UDIM baking and proprietary toolchain lock-in while staying 100 % Python-scriptable alongside `tools/`.
- `Character Creator 5` (first fallback) and `MetaHuman` (reference control) are deferred and only tested at Milestone 2 if close-range native review in Exolune lighting reveals a visual deficit.

| Candidate | Runtime licence & cost | Close-up realism | Pipeline friction for Exolune | Verdict |
|---|---|---|---|---|
| **MPFB2 (MakeHuman 2 in Blender)** | Open source, CC0 assets | Clean quad topology and unlimited anthropometric morphs; base skin maps upgraded with calibrated PBR skin/eye textures | Zero external dependency; 100 % Python-scriptable inside Blender alongside `tools/` | **Selected (primary base).** Best fit for scripted 100–300 NPC crowd diversity and zero-lock-in cooking. |
| **Human Generator V4 (Blender)** | Commercial Blender add-on, 0 % royalties | High procedural skin, aging and morphs inside Blender | Runs 100 % inside Blender; procedural materials require baking to PBR maps for real-time export | **Not selected.** Optional Blender upgrade only if `MPFB2` skin authoring proves too slow. |
| **Character Creator 5 (CC5) + Blender Auto Setup** | Commercial suite, 0 % royalties | Very high; 8K `SkinGen` game-ready PBR layers, clean ARKit blendshapes and hair cards | Standalone Windows app plus official Blender bridge; avoids RigLogic `.dna` and full UE install | **Fallback #1 (Milestone 2 control if needed).** Strongest non-UE alternative for studio-grade close-ups. |
| **MetaHuman (UE 5.6+ / Fab)** | Free below $1M gross revenue; 0 % royalties outside UE; seat licences above $1M; `NoAI` marketplace tag | Highest scanned skin, eye and facial detail out of the box | Requires UE 5.6 (~60–100 GB) offline; RigLogic `.dna` (~800 facial joints + RBF) does not export natively to glTF and must be baked to shape keys in Blender; Alembic grooms must convert to hair cards; UDIMs must be atlased; harder to batch-script in Python | **Deferred (reference control only).** Pipeline friction outweighs gains at 1.5–30 m crowd distances. |

- **Key trade-off:** at 1.5 m to 30 m under Exolune's physical sun, most perceived realism comes from the runtime skin/fabric shaders, grounded foot contact, proportions and motion quality rather than 800-joint cinematic facial rigs.
- **Source-agnostic contract:** all authoring tools bake down to the same glTF 2.0 intermediate and canonical skeleton before entering Exolune's cooker, keeping `CC5` or `MetaHuman` swappable later without changing runtime code.

**Motion pipeline (2026)**

- **Locomotion datasets:** use open-access multi-style locomotion corpora (**100STYLE**, 4M frames across 100 styles) for Motion Matching and Mixamo only as an early technical placeholder.
- **AI text-to-motion and markerless capture:** generate everyday gestures and crowd actions with open DiT/Flow-Matching models (**HY-Motion 1.0**) or video capture (**Move.ai**).
- **Physical cleanup:** pass raw mocap and generated clips through **Cascadeur** to fix foot sliding, balance and clean root motion before cooking to `.ozz`.
- **Runtime transitions:** combine `ozz-animation` with **Inertialization** first, then add lightweight **Motion Matching** over a compact `.ozz` clip database for natural walking, turning and stopping.

**Rendering integration in MyPlanetEngine**

- **Shared Forward HDR contract:** characters render into `mHdrTarget` (RGB linear radiance, alpha = distance in km) and `mSunPart` (direct sunlight only), automatically inheriting cloud shadows, aerial haze, `LocalContacts`, `Glare`, `Adaptation`, `RodVision` and `FilmCurve`.
- **Compute skinning (`CharacterSkin.hlsl`):** execute Dual Quaternion Skinning (or LBS plus optional facial morphs) once per visible character per frame before shadow and opaque passes, keeping both current (`N`) and previous (`N-1`) skinned positions in GPU buffers.
- **Motion vectors for TAA (`ToneMap.hlsl`):** add a lightweight `DXGI_FORMAT_R16G16_FLOAT` screen-space velocity target written only by deforming dynamic meshes (`currNDC - prevNDC`); `ToneMap.hlsl` uses it when non-zero and preserves the exact analytical reprojection for terrain, sky and ship.
- **Unified local shadow map:** render nearby dynamic characters into a camera-centred 2048² shadow map (0–35 m, texel-stabilized) for facial/limb self-shadowing and ground/street cast shadows, while characters also read terrain `SunHorizon`, `CitySunVisibility`, `shipSunShadow` and cloud shadows via `sunPart`.
- **Clustered Forward local lights:** extend the Forward pixel shaders (`CityPixel.hlsl`, terrain near shading and character shaders) with a 3D frustum-clustered point/spot light grid (e.g. 16×9×24 clusters) so markets, street lamps, spaceport beacons and open halls light crowds realistically at dusk and night.
- **Naturalist character PBR shading:**
  - **Skin:** Pre-Integrated Skin Shading (Penner 2D LUT indexed by `dot(N, L)` and curvature, compatible with `sunPart` cloud modulation), dual specular lobes and distance-filtered pore micro-normals.
  - **Fabrics:** Estevez-Kulla Charlie microfiber sheen lobe plus weave normal/roughness maps to avoid plastic highlights under low grazing sun.
  - **Hair:** game hair cards with simplified Kajiya-Kay anisotropic highlights and temporally dithered alpha (`FoliageSequence`).
  - **Eyes:** crisp sky/sun corneal reflection over soft sclera and subtle upper-lid ambient occlusion.

**Crowd simulation and planetary coupling**

- **Four-tier crowd LOD:**
  - **Tier 0 (0–25 m, up to ~25 NPCs):** LOD0/1 mesh, full 60 Hz `ozz-animation`, Inertialization/Motion Matching, two-bone foot IK, aim/look-at IK, full PBR skin/hair/cloth, local shadow caster, Jolt avoidance.
  - **Tier 1 (25–70 m, up to ~100 NPCs):** LOD1/2 mesh, 15–30 Hz `ozz-animation` without foot IK, simplified fabric/skin shading, instanced tint variation.
  - **Tier 2 (70–250 m, up to ~200+ NPCs):** LOD2/3 mesh driven by GPU-instanced **Vertex Animation Textures (VAT)** or reduced-bone skinning with minimal CPU cost.
  - **Tier 3 (off-screen / > 250 m):** pure schedule state (time, waypoint, role) with zero skeleton or rendering cost, promoting smoothly on approach.
- **Batched GPU ground probes:** generalize `WalkGround.hlsl` and `D3DAppWalk.cpp` from a single 9×9 player patch to one batched compute dispatch per frame querying ground heights (including `City::Grade` and `City::Surface`) for active Tier-0 NPCs and feet, read back one frame later with zero GPU stalls.
- **Live world reactivity:** feed existing `WorldWeather.hlsli` (rain, cloud cover), `Climate` wind, solar elevation and parked/descending `Ship` position directly into crowd behaviour (seeking canopy shelter in rain, turning heads via Aim IK when a ship passes overhead, opening and closing market stalls with daylight).

**Cooked asset contract (`CHR1`)**

- Keep raw sources, `.blend` files and intermediate renders outside Git on `E:`; keep recipes, schemas and cooking tools in `tools/characters/`.
- Validate canonical bone names, normalized skin weights (max 4 influences per vertex), metric scale (eye height ~1.68 m matching `Walker::Eye`) and orthogonal tangents at UV poles.
- Generate 4 LODs via `meshoptimizer`, block-compress textures to BC7 (albedo, ORM, masks) and BC5 (normals), cook `.ozz` skeleton and clip binaries, and record SHA-256 source hashes.

**Phased roadmap and next validation gates**

1. **Milestone 1 — Vertical technical slice:** integrate `ozz-animation`, `CharacterSkin.hlsl`, `CHR1` loader, `ToneMap.hlsl` motion vectors, local 0–35 m shadow map and one animated explorer/citizen on terrain and in the city; verify noon, dusk, night, cloud shadows and TAA stability.
2. **Milestone 2 — Naturalist shading & MPFB2 visual gate:** implement Pre-Integrated Skin, Charlie cloth sheen, dithered hair cards, Two-Bone Foot IK and Aim IK on the selected `MPFB2` base with upgraded PBR skin/eye maps; inspect in native noon, dusk and night lighting, and only run a `CC5` or `MetaHuman` comparison control if close-range facial quality fails review.
3. **Milestone 3 — Local physics, navigation and evening light:** integrate `Jolt Physics` (`CharacterVirtual` + city/ship/terrain bubble), `EnTT`, `Recast & Detour` with RVO steering, batched GPU terrain probes and Clustered Forward local lights; populate a review market/plaza with 30–100 active NPCs.
4. **Milestone 4 — Full crowd tiers & third-person option:** add Tier 2 VAT crowds (100–300 visible NPCs), day/night and weather/ship reactions, lightweight Motion Matching, modular wardrobe variety, performance benchmarks (`banc_perf.py`) and optional third-person player avatar.
