# Navette AAA

**Version 9** supplies the playable transport and its Blender and GLB review masters. [Native packet](../navette/README.md)

**Source of the form**

- `blueprint.json` holds the validated hull sections: 41 rings of the remodelled shuttle, at 7.2 m per unit.
- The nose is designed from them: ahead of y = −3.40 m it is 0.40 m shorter and its tip 0.20 m higher (`surface.nose_y`), rounder as in the concept.
- The stern is designed too: from y = 5.5 m the hull closes on itself into a rounded tail.
- There is no rear engine: the two side thrusters are the only ones.
- The nose forward of the arch is one glass bubble, down to the keel, as in the concept.
- Each wing emerges through the original shoulder chine above its thruster. The rigid installation follows the chine at 1.04° of pitch. The leading edge sweeps 44° in the wing plane and the straight tip chord measures 1.60 m.
- The concept art and the review captures stay outside Git, in `E:\ExoluneAssets\navette-exolune-aaa-2026-11-22\`.
- Frame: metres, nose −Y, up +Z, port +X.

**Recipe**

- `surface.py` rebuilds the hull as a smooth surface between two poles. Each section is re-parametrised on its two shoulder edges. A penalised fit removes the sculpted lumps of the source. `python surface.py` prints the deviation from the blueprint.
- `hullgrid.py` meshes the half hull as one structured quad grid. Outlines pin grid lines: glazing, prow, thruster mouths, shoulder, belt, the three gear wells and the rear hatch. Openings are index rectangles: no boolean. `python hullgrid.py` checks that no grid line crosses another.
- `frames.py` sweeps the glazing seal, the amber trims, the arch hoop and the mullions along the skin. It also caps both poles: a glass tip on the nose, a light on the tail.
- `panels.py` builds doors from the hull's own cells, so they close flush: twelve gear door leaves and the ventral rear hatch.
- `thrusters.py` builds each side thruster: rounded lip, duct, liner, amber light. The four blades are strips of the hull skin.
- `tail.py` builds the dorsal fin, its root fairing and the split airbrake on its trailing part.
- `details.py` adds panel seams, the flank light slots, a vent and plates, static ports, the belt and hatch lights and the dorsal radiators.
- `wings.py` builds the tapered airfoil, two inclined telescopic spars and three bushed clevises per wing. The outer panel folds 180° over the root. A scarf backs the fold seam. The rounded tip contains a recessed navigation lens.
- `wing_bay.py` fits the installation between the original shoulder bevels. Both main doors and the docking fillet share the chine section. The central blank banks into the roof cassette. The floor follows the original nozzle. Sliding end keys back the seated joint.
- `wing_jacks.py` drives each main door with a fore and an aft hydraulic ram. The end webs carry the cylinder pins. Bored clevises on the door carry the rod pins. The barrels and piston rods move as separate rigid meshes.
- `gear.py`, `interior.py` and `airlock.py` are optional modules: retractable landing gear, cockpit and cabin, aft airlock with its airstair.
- `anim.py` keys the animation clips. `materials.py` holds the palette of the concept on Principled BSDF.

**Animation**

- Four clips at 24 fps: `Train` (gear retraction, 84 frames), `Aerofrein` (30 frames), `Trappe_Arriere` (hatch and airstair, 72 frames), `Ailes` (wings out, 96 frames).
- Frame 0 of every clip is the rest pose: gear down, airbrake and hatch closed, wings in.
- Every rigid part is its own object, keyed in world space; the GLB carries one animation per clip.
- The gear rig solves every pin exactly: actuators, torque links and gimbals stay pinned at every frame.
- Retracted, every part of the gear lies inside the hull and the twelve leaves close flush. On the ground only the leaves the legs pass through hang open, close to vertical.
- In `Ailes`, the main doors open by frame 20. The centre blanks park by frame 28. The folded panels clear the bay by frame 47. The outer panel swings into line by frame 73. The root docks by frame 87. The doors return flush and the end keys close by frame 96. Reverse playback retracts the wings.
- The Blender file opens with the wing clip active for playback. The GLB contains all four clips.

**Build**

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --python-exit-code 1 --python assets/vaisseau/navette_aaa/build.py -- '<out>/Navette_Exolune_AAA_v9.blend' --with gear,interior,airlock --glb
```

**Review**

- `review.py` renders named and custom views in four modes: beauty, clay, true-edge wireframe and zebra stripes.
- `--pose Train=1,Ailes=1` freezes clips at a phase; `--film Ailes` renders a clip as an MP4.
- `--floor` adds a studio floor: leave it out for the views from below.
- `check_glb.py` reads an exported GLB back: counts, size and animations.
- Read the zebra stripes for fairness and the wireframe for topology. Inspect every part at close range before showing the asset.

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b '<out>/Navette_Exolune_AAA_v9.blend' --python assets/vaisseau/navette_aaa/review.py -- '<captures>' --modes beauty,wire,zebra
```

**Module checks**

- `gear_probe.py`, `interior_probe.py` and `airlock_probe.py` build or open a scene and run each module's `self_check`.
- `--strict` makes them exit 1 when a check fails.
- The gear check runs all 85 frames of its clip: pins, collisions, free volume, and nothing below the skin when retracted.
- Open the full scene or the GLB reimport with `--python-exit-code 1 --python assets/vaisseau/navette_aaa/wing_probe.py -- --step 0.25`. It checks 385 wing poses in each of three gear and hatch configurations. It measures the stowed clearances, checks hinge alignment, and casts tilted rays across the seated doors and inserts at rest and in flight.
- A separate sweep checks the folding ribs and their scarf at 897 poses through the rotation.
- Each sampled pose checks the eight anchor pairs, the common rod and barrel axes, and rod engagement in each cylinder. The deployed leading edge is checked against the installation frame.

**Measured, 2026-11-24**

- The hull stays within 6.2 cm of its designed sections, 3.6 cm outside the thruster zone. The beam is 4.86 m.
- The docked span is 7.46 m, an increase of 1.30 m per side. The folded wing and spars clear the shoulder skin by at least 163 mm along X and the airlock envelope by 40 mm.
- At mid-bay the wing datum lies at Z = −0.314 m. The entire datum stays between the two original shoulder bevels.
- The upper rams travel 159 mm and the lower rams travel 303 mm. At full extension at least 37 mm of rod remains inside the gland.
- The exported wing measures 159 mm thick at X = 2.62 m and 104 mm at X = 3.70 m. The two skins meet at the 44° leading edge. The folding ribs are spaced 2.6 mm apart.
- With the wing stowed and deployed, the deepest visible joint lies within 7.6 mm of the shoulder datum across 137,520 sampled sightlines per side and position.
- The 58 checked airlock, cabin, canopy, thruster, landing gear and hatch meshes match v8 in vertex positions, faces and rest transforms.
- The 142 mesh objects contain 720,051 triangles. The ship measures 4.86 × 13.28 × 5.31 m on its gear.
- The GLB carries four independent clips. Thirty-four rigid nodes move in `Ailes`.
- Stance: nose pad at y −3.37, main pads at y 1.18 and x ±1.64. The hull's centre of volume, y +0.43, lies between them.
- Cockpit deck: at least 0.27 m from the glass. The pilot seat sits 0.53 m from the console face.

**Open points**

- The player ship uses the full-resolution packet in both pilot and chase views.
- Gear doors have no hinge fittings. While open, some leaves drop 3 to 4 cm off their rims and show a dark wedge. Fitting goosenecks needs wider hinge-side gaps and straight hinge edges in `panels.py`.
- On the ground the main outer front leaf leans with the canted leg rather than hanging vertical.
- Cabin: a white sliver of the curtain at the deck's edge, small facets in the deck's amber line, small notches where seat belts cross.
- Airlock: the folded airstair reads as steps up to the rear wall; a 6 cm gap between the sill and the airstair's landing when open.
