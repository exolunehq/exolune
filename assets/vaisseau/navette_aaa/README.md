# Navette AAA

**Status:** Blender asset under review, version 5. It is not cooked for the engine yet.

**Source of the form**

- `blueprint.json` holds the validated hull sections: 41 rings of the remodelled shuttle, at 7.2 m per unit.
- The nose is designed from them: ahead of y = −3.40 m it is 0.40 m shorter and its tip 0.20 m higher (`surface.nose_y`), rounder as in the concept.
- The stern is designed too: from y = 5.5 m the hull closes on itself into a rounded tail.
- There is no rear engine: the two side thrusters are the only ones.
- The nose forward of the arch is one glass bubble, down to the keel, as in the concept.
- In flight the shoulder crest above each thruster slides out and the skin follows it: a rounded delta wing, as on the Navette in the game.
- The concept art and the review captures stay outside Git, in `E:\ExoluneAssets\navette-exolune-aaa-2026-11-22\`.
- Frame: metres, nose −Y, up +Z, port +X.

**Recipe**

- `surface.py` rebuilds the hull as a smooth surface between two poles. Each section is re-parametrised on its two shoulder edges. A penalised fit removes the sculpted lumps of the source. `python surface.py` prints the deviation from the blueprint.
- `hullgrid.py` meshes the half hull as one structured quad grid. Outlines pin grid lines: glazing, prow, thruster mouths, shoulder, belt, the three gear wells and the rear hatch. Openings are index rectangles: no boolean. `python hullgrid.py` checks that no grid line crosses another.
- `frames.py` sweeps the glazing seal, the amber trims, the arch hoop and the mullions along the skin. It also caps both poles: a glass tip on the nose, a light on the tail.
- `panels.py` builds doors from the hull's own cells, so they close flush: twelve gear door leaves and the ventral rear hatch.
- `thrusters.py` builds each side thruster: rounded lip, duct, liner, amber light. The four blades are strips of the hull skin.
- `tail.py` builds the dorsal fin, its root fairing and the split airbrake on its trailing part.
- `details.py` adds panel seams, the flank light slots, a vent and plates, static ports, the belt and hatch lights, the navigation lights and the dorsal radiators.
- `wings.py` draws the wings: the span law in plan, the share of travel of each grid row, and the extended twin that becomes the skin's shape key.
- `gear.py`, `interior.py` and `airlock.py` are optional modules: retractable landing gear, cockpit and cabin, aft airlock with its airstair.
- `anim.py` keys the animation clips. `materials.py` holds the palette of the concept on Principled BSDF.

**Animation**

- Four clips at 24 fps: `Train` (gear retraction, 84 frames), `Aerofrein` (30 frames), `Trappe_Arriere` (hatch and airstair, 72 frames), `Ailes` (wings out, 96 frames).
- Frame 0 of every clip is the rest pose: gear down, airbrake and hatch closed, wings in.
- Every rigid part is its own object, keyed in world space; the GLB carries one animation per clip.
- The gear rig solves every pin exactly: actuators, torque links and gimbals stay pinned at every frame.
- Retracted, every part of the gear lies inside the hull and the twelve leaves close flush. On the ground only the leaves the legs pass through hang open, close to vertical.
- The wings are a shape key "Aile" of the hull skin and of its seams, a morph target with positions and normals in the GLB. The navigation lights ride on the wings' rigid tips.

**Build**

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --python-exit-code 1 --python assets/vaisseau/navette_aaa/build.py -- '<out>/Navette_Exolune_AAA_v5.blend' --with gear,interior,airlock --glb
```

**Review**

- `review.py` renders named and custom views in four modes: beauty, clay, true-edge wireframe and zebra stripes.
- `--pose Train=1,Ailes=1` freezes clips at a phase; `--film Ailes` renders a clip as an MP4.
- `--floor` adds a studio floor: leave it out for the views from below.
- `check_glb.py` reads an exported GLB back: counts, size and animations.
- Read the zebra stripes for fairness and the wireframe for topology. Inspect every part at close range before showing the asset.

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b '<out>/Navette_Exolune_AAA_v5.blend' --python assets/vaisseau/navette_aaa/review.py -- '<captures>' --modes beauty,wire,zebra
```

**Module checks**

- `gear_probe.py`, `interior_probe.py` and `airlock_probe.py` build or open a scene and run each module's `self_check`.
- `--strict` makes them exit 1 when a check fails.
- The gear check runs all 85 frames of its clip: pins, collisions, free volume, and nothing below the skin when retracted.

**Measured, 2026-11-23**

- The hull stays within 6.2 cm of its designed sections, 3.6 cm outside the thruster zone. The beam is 4.86 m.
- Wings out, the span is 7.37 m: each crest travels 1.5 m at its tip, between y 4.3 and 5.0 m.
- Whole ship: 106 objects, 416,245 triangles, no face above four sides. It measures 4.86 × 13.28 × 5.31 m on its gear.
- The GLB is 15.1 MB: 316,789 triangles once the eight passenger seats share one mesh. It reimports with its four animations; a render of the reimport, wings out, matches the source.
- Stance: nose pad at y −3.37, main pads at y 1.18 and x ±1.64. The hull's centre of volume, y +0.43, lies between them.
- Cockpit deck: at least 0.27 m from the glass. The pilot seat sits 0.53 m from the console face.

**Open points**

- No level of detail, no engine packet, no flight review yet. In the game, the wings need the skin displacement that drives the Navette's wings.
- The wing's leading edge is stretched skin, not a rigid part; only its tip is rigid. The telescopic rams inside the wing are not modelled: they would never be seen.
- Gear doors have no hinge fittings. While open, some leaves drop 3 to 4 cm off their rims and show a dark wedge. Fitting goosenecks needs wider hinge-side gaps and straight hinge edges in `panels.py`.
- On the ground the main outer front leaf leans with the canted leg rather than hanging vertical.
- Cabin: a white sliver of the curtain at the deck's edge, small facets in the deck's amber line, small notches where seat belts cross.
- Airlock: the folded airstair reads as steps up to the rear wall; a 6 cm gap between the sill and the airstair's landing when open.
