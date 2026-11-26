# Character authoring, cooking and native review tools

**Pipeline (Milestones 1 & 2 — Style B modular PBR)**

- `assets/characters/spaceport_m1.json` defines the canonical 59-bone archetypes (`game_engine` 53 bones + 4 arm twist bones + 2 `eyelid_upper_l/r` blink bones, Style B solarpunk civil wardrobe palettes, procedural multi-layer hair cards, distinct CMU MoCap clips) and obstacle-checked spaceport placements on Pad 43.
- `tools/characters/prepare_wardrobe_kit.py` prepares the 3-piece Tripo H3.1 modular wardrobe kit (`jacket`, `boot`, `satchel` under `E:/ExoluneAssets/characters-kit-styleb-2026-11-22/`): classifies original 2M-poly faces into clean semantic PBR classes (`EX_CLOTH_*`, `EX_LEATHER_*`, `EX_RUBBER_*`, `EX_METAL_BRASS`), welds seams into watertight manifolds, locally decimates to real-time budgets (no Tripo retopology), writes metric box UVs and strips raw Tripo atlases completely.
- `tools/characters/equip_styleb.py` fits the cleaned 3D jacket (pre-bent to MPFB2's 42-deg A-pose elbows with analytical sleeve-separated twist skinning), tailored woven trousers, mirrored lace-up boots, 3D waist belt + brass buckle, satchel + crossbody strap, hidden-skin cleanup and `eyelid_upper_l/r` blink bones onto any MPFB2 morph.
- `tools/characters/hair_cards.py` generates a deterministic 1024² 4-lane feathered strand atlas (`albedo+alpha`, strand normal, root-to-tip ORM) and anatomically fitted multi-layer arched hair-card meshes (`styleb_swept_short`, `styleb_high_ponytail`, `styleb_long_layered`, `styleb_chic_bob`).
- `tools/characters/retarget_mocap.py` retargets 120 Hz CMU Graphics Lab optical MoCap BVH clips (`E:/ExoluneAssets/characters-m1-2026-11-21/mocap/`) onto the 59-bone skeleton with arm twist distribution, scapulohumeral clavicle rhythm, living animated fingers, arm-vs-torso/satchel self-collision clearance, cyclic seam blending, metric stride measurement and shoe-sole ground locking (`Z = 0.000 m`).
- `tools/characters/author_mpfb2.py` runs headlessly in Blender 5.2 with MPFB2, equips the modular Style B kit & hair cards, retargets distinct `idle`, `walk` and `talk` clips, exports glTF 2.0 (`.glb`) sources and renders neutral Cycles inspection cards (`preview.png`, `preview_talk.png`, `preview_closeup.png`) to `E:/ExoluneAssets/characters-m1-2026-11-21/sources/`.
- `tools/characters/cook.py` invokes `gltf2ozz.exe` (built from `third_party/ozz-animation`), validates joint mapping, weights, orthogonal tangents and ground datum, refines Style B smooth skin albedo/ORM, synthesizes deduplicated tileable tactile PBR BC5 normal + ORM maps (woven linen, leather grain, matte rubber, brushed brass, wet cornea), checks spaceport obstacle clearance against `layout.json`, and packs `characters.bin` (`CHR1`), `placements.bin` (`CHRPLC1` v2 with per-archetype measured MoCap strides), `.ozz` skeletons/clips and `manifest.json` under `E:/ExoluneAssets/characters-m1-2026-11-21/bank/`.
- `MyPlanetEngine/Characters.cpp` & `Character*.hlsl` evaluate `ozz-animation` clips with runtime **`BlendingJob`** smooth `walk ↔ idle` transitions and staggered concourse stops, exact per-archetype stride locking (`0 %` foot sliding), **Two-Bone Foot IK** (`IKTwoBoneJob` via `City::Surface`), **Head & Neck Aim IK** (`IKAimJob`) and asynchronous **eye blinking**, run volume-preserving **Dual Quaternion Compute Skinning** (`CharacterSkin.hlsl`), render a local 0–35 m shadow map, shade with Pre-Integrated Skin SSS, wet corneal eyes, Charlie cloth sheen and Kajiya-Kay temporally dithered hair cards, and feed exact motion vectors into `ToneMap.hlsl`.
- `tools/characters/review_native.py` captures hidden native Exolune spaceport views (midday & low-sun portraits, terminal, concourse walkway, shuttle stairs crew, canopy lounge, dusk, twilight, wide) and writes the user review route `tools/tests/2026-11-21-personnages-spatioport.txt`.

**Commands**

```powershell
# 1. Author MPFB2 sources in Blender 5.2
& "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --python tools\characters\author_mpfb2.py -- --recipe assets\characters\spaceport_m1.json

# 2. Cook CHR1 bank + ozz skeletons/clips + spaceport placements
python tools\characters\cook.py --recipe assets\characters\spaceport_m1.json

# 3. Build Release x64
powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Build -NoLaunch

# 4. Run hidden native spaceport review captures
python tools\characters\review_native.py

# 5. Interactive review launch around the spaceport
powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 `
  -Ville E:/ExoluneAssets/city-tripo-2026-11-11/delivery-07/bank `
  -Personnages E:/ExoluneAssets/characters-m1-2026-11-21/bank `
  -Parcours tools\tests\2026-11-21-personnages-spatioport.txt
```
