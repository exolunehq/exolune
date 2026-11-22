# Navette AAA

**Status:** Blender asset under review, version 3. It is not cooked for the engine yet.

**Source of the form**

- `blueprint.json` holds the validated hull sections: 41 rings of the remodelled shuttle, at 7.2 m per unit.
- The stern is designed, not taken from the blueprint. From y = 5.5 m the hull closes on itself into a rounded tail.
- There is no rear engine: the two side thrusters are the only ones.
- The nose forward of the arch is one glass bubble, down to the keel, as in the concept.
- The concept art and the review captures stay outside Git, in `E:\ExoluneAssets\navette-exolune-aaa-2026-11-22\`.
- Frame: metres, nose −Y, up +Z, port +X.

**Recipe**

- `surface.py` rebuilds the hull as a smooth surface between two poles. Each section is re-parametrised on its two shoulder edges. A penalised fit removes the sculpted lumps of the source. `python surface.py` prints the deviation from the blueprint.
- `hullgrid.py` meshes the half hull as one structured quad grid. Outlines pin grid lines: glazing, prow, thruster mouths, shoulder, belt, nose gear well and rear hatch. Openings are index rectangles: no boolean.
- `frames.py` sweeps the glazing seal, the amber trims, the arch hoop and the mullions along the skin. It also caps both poles: a glass tip on the nose, a light on the tail.
- `panels.py` builds doors from the hull's own cells, so they close flush: the nose gear doors and the ventral rear hatch.
- `thrusters.py` builds each side thruster: rounded lip, duct, liner, amber light. The four blades are strips of the hull skin.
- `tail.py` builds the dorsal fin, its root fairing and the split airbrake on its trailing part.
- `details.py` adds panel seams, the flank light slots, a vent and plates, static ports, the belt and hatch lights, the navigation lights and the dorsal radiators.
- `gear.py`, `interior.py` and `airlock.py` are optional modules: retractable landing gear, cockpit and cabin, aft airlock with its airstair.
- `anim.py` keys the animation clips. `materials.py` holds the palette of the concept on Principled BSDF.

**Animation**

- Three clips at 24 fps: `Train` (gear retraction, 84 frames), `Aerofrein` (30 frames), `Trappe_Arriere` (hatch and airstair, 72 frames).
- Frame 0 of every clip is the rest pose: gear down, airbrake and hatch closed.
- Every moving part is its own object, keyed in world space; the GLB carries one animation per clip.
- The gear rig solves every pin exactly: actuators, torque links and gimbals stay pinned at every frame.

**Build**

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --python-exit-code 1 --python assets/vaisseau/navette_aaa/build.py -- '<out>/Navette_Exolune_AAA_v3.blend' --with gear,interior,airlock --glb
```

**Review**

- `review.py` renders named and custom views in four modes: beauty, clay, true-edge wireframe and zebra stripes.
- `--pose Train=1` freezes clips at a phase; `--film Train` renders a clip as an MP4.
- `check_glb.py` reads an exported GLB back: counts, size and animations.
- Read the zebra stripes for fairness and the wireframe for topology. Inspect every part at close range before showing the asset.

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b '<out>/Navette_Exolune_AAA_v3.blend' --python assets/vaisseau/navette_aaa/review.py -- '<captures>' --modes beauty,wire,zebra
```

**Module checks**

- `gear_probe.py`, `interior_probe.py` and `airlock_probe.py` build or open a scene and run each module's `self_check`.
- `--strict` makes them exit 1 when a check fails.

**Measured, 2026-11-22**

- The hull stays within 6.2 cm of the blueprint forward of the stern, 3.6 cm outside the thruster zone. The beam is 4.863 m.
- Whole ship: 97 objects, 417,723 triangles, no face above four sides. It measures 4.864 × 13.684 × 5.311 m on its gear.
- Exterior 152,665 triangles, landing gear 56,196, cabin 178,778, airlock 30,084.
- The GLB is 14.6 MB: 318,267 triangles once the eight passenger seats share one mesh. It reimports with its three animations, and a render of the reimport matches the source scene.
- Cockpit deck: at least 0.27 m from the glass. Stowed pads stand 0.15 m proud of the belly and pods.

**Open points**

- No level of detail, no engine packet, no flight review yet.
- Landing gear: the nose doors close over the actuator, not over the struts; deployed, each main pad's socket is an open dark hole; stowed, the nose leg shows through 3 to 4 cm gaps round its pad; the pod tips are still pinched.
- Doors: no hinge fittings on the nose gear doors and the hatch; a 6 cm gap between the sill and the airstair's landing when open.
- Cabin: small notches where seat belts cross; flat deck underside, without a fairing at the spine.
- Airlock: the folded airstair reads as steps up to the rear wall; the floor's amber lines stop 0.2 m short of the sill.
