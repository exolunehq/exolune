# Smooth Navigator and cockpit

**Selectable cabin prototype, 2026-11-03.** Use `tools/lance.ps1 -ModeleVaisseau navigateur -Resolution fenetre -Parcours tools/tests/2026-11-03-navigateur-cockpit.txt`.

- `vaisseau_travail.blend` retains the editable quad cage, subdivision and separate interior parts.
- `navigateur-cockpit.glb` contains the evaluated hull and cabin, batched by material.
- `vaisseau.vsx` is the VSX3 runtime package.
- `preparer.py` imports the approved smooth v2 Blender source, applies scale ×4, turns its +Y nose to the game's −Y and calls `cabine_maillage.py`.
- `instruments.py` forms the graduated dials, knurled controls, palm wells, engraved legends and captive fastener seats within each console.
- `paquet_moteur.py` uses the shared VSX3 cooker with roles 10 (chrome), 11 (cabin), 12 (live dial) and no animation pivots.
- `controler.py` checks interior containment, six connected closed solids, actual mounting contact, instrument sightlines and eye clearance in background Blender.
- Rebuild: run Blender in background with `--python preparer.py -- <smooth-v2.blend>`, then `python paquet_moteur.py`.
- Source: `E:/ExoluneAssets/navigateur-normal-v2-smooth/navigateur-normal-lisse.blend`; delivery copy in `artifacts/modeles/navigateur-normal-v2-smooth/`.

**Geometry and material**

- The exterior retains 98,306 vertices and 196,608 triangles; the complete packet has 459,757 vertices and 723,264 triangles in 12 material ranges.
- One continuous mesh joins the panelled wall, coved floor, rooted station and sensor; five fitted solids complete the consoles and seat.
- The 139 wall panels, large octagonal rear fitting and recessed console details share their support mesh boundaries.
- The cushion underside derives from the evaluated seat shell; padding follows its local normals.
- Mounting checks sample 1,876 points on evaluated geometry; maximum gap is below 0.02 mm.
- No texture images or photographed lighting are embedded.
- Approximate width 7.99 m, length 7.63 m, height 4.35 m; authored scale, without authenticated metric plans.
- Frame: metres, nose −Y, up +Z, pilot's left +X; shadow centre at the asset origin.
- Metallic 1, linear base colour `(0.84, 0.87, 0.91)`, perceptual roughness 0.075.
- No normal map, displacement or photographed lighting.
- The cooker checks finite positions, unit normals, orthogonal unit tangents, zero pose weights and the shadow bound.
- The original smooth source remains the reconstruction input.

**Runtime scope**

- Starts in cockpit view; Tab cycles cockpit, chase and bare view.
- Existing flight controls and camera orbit remain available.
- A broad forward viewing field opens the interior view while external views retain the opaque chrome shell.
- The cabin has a fitted floor and panelled walls, bucket seat, lateral consoles, rear fitting and suspended sensor.
- Eye position: `(0, -0.65, 0.70)` m; fixtures use matching normalized scene lighting.
- The field has no glazing or canopy weather surface.
- The left blue dial shows heading; the right amber dial shows commanded propulsion, both from actual flight data.
- `ShipNavigator.hlsli` shades the live faces using centres and radii generated from the console patches in `ShipNavigatorFixtures.hlsli`.
- Entry, stairs, moving rotary controls and sensor animation remain outside this prototype.
- `MyPlanetEngine/NavigatorSound.h` supplies a quiet original levitation resonance, without a throttle-linked pitch sweep or exhaust layer; listening review is pending.
- Actual visible terrain, sea and vegetation can appear in the reflections.
- Off-screen directions use a spherical planet, mapped biome colours and atmospheric scattering; off-screen trees are not captured.
- Rendering and limits: [ship reflections](../../../docs/spec-reflets-vaisseau.md).
- Cabin construction, sound and checks: [cockpit and sound](../../../docs/spec-navigateur-cockpit-son.md).
- Superseded primitive construction: `archive/`; current runtime paths use the new GLB and VSX only.
- `rendus.py` reviews physical geometry in background Blender; live dial marks are supplied only by the game shader.
- Current native stills: `artifacts/navigateur-cockpit-son-2026-11-03/integration-v6/`; sea, forest, orbit, night and paired instrument states.
- Release x64, geometry and packet checks pass; warn the user before launching the game for interactive review.
