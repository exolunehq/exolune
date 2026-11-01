# Triangular ship

**Files**

- `vaisseau_travail.blend`: editable scene, separate cockpit parts and packed textures.
- `vaisseau.glb`: static glTF 2.0 model, packed textures, without scenery or exhaust plumes.
- `vaisseau.vsx`: the package read by the engine, baked from the GLB by `paquet_moteur.py` (`python paquet_moteur.py`, without Blender); rerun after every export (`docs/spec-vaisseau.md`).
- `pieces_mobiles.py`: marks the stick and throttle, which the engine rotates, and places their pivots.
- `exporter.py`: GLB export, shared by `preparer.py` and `pieces_mobiles.py`.
- `modules_cockpit.py`: dimensions, controls and atlas position of each equipment module. Single source for panel markings and geometry.
- `plaques.png`: module panel-marking atlas, 2048 × 2048.
- `cockpit.png`, `commandes.png`, `pilote.png`, `pupitre.png`, `exterieur.png`, `arriere.png`: verification renders of the Blender scene. The canopy glass is hidden in cockpit and control views.
- `export_controle.png` and `export_pilote.png`: renders of the GLB reimported into an empty scene.

**Model**

- Based on Antigravity's `spaceship.blend`, from the “Blender Spaceship 3D Modeling” conversation of October 25, 2026. The original remains intact.
- Original triangular silhouette preserved. Hull, stern and cockpit rebuilt by `design_v2.py`; no original parts remain in the model.
- Canopy glass restored to the original proportions, made of two adjoining faces without a central arch or crossbar. A dark seal follows its perimeter.

**Hull**

- A continuous skin closes the volume from nose to stern frame. All panels sit flush at 12 mm above it, separated by 4 mm engraved joints.
- Paneling follows the structure. Sections between main frames, at the front and rear tips of the glass, intersect strips between stringers converging toward the nose. Joints are staggered between strips and never form a grid.
- Panels vary in size, and a quarter of their corners are chamfered. Rivets follow the frames and the lower stringer of each panel.
- Rivets are not modeled in the game model. The 2 mm domes are used only to bake a normal map and an occlusion map, then removed.
- These maps use the panels' second UV set, `UVDetail`: one non-overlapping island per panel, at 371 px/m. Islands are projected in the same frame as the paint UVs, so the two UV sets share tangents.
- Surface equipment is placed within a single panel for each item, checked by the script:
  - riveted hatches with chamfered corners and landing-gear hatches with wide seals;
  - caps, ventilation grilles and red and white markings;
  - one antenna on top, two below the keel.
- Paint is matte, light gray and slightly worn: sun fading, subtle rearward streaks, sparse clustered chips and scratches.
- Livery:
  - most panels retain the original paint;
  - some are slightly darker repairs, selected randomly;
  - a faded blue stripe covers the rear fairings and follows the joints, giving it a stepped edge;
  - the nose is blue-gray, the underside darker.
- All these tints multiply the same texture, exported by glTF as a color factor. The 1024 × 1024 texture covers 2 m, applied at world scale without discontinuities between panels.

**Stern**

- A frame closes the entire rear diamond, including its tips, and projects 4 cm beyond the skin. The backplate is recessed 40 cm and painted to remain legible in shadow.
- Three compact 35 cm nozzles, perpendicular to the backplate, on bolted flanges: machined throat, short divergent section, lip and stiffener. Two steering actuators per nozzle.
- Nothing projects beyond the ship: nozzle lips stop 5 cm short of the stern plane, checked by `controle_geometrie.py`.
- Longitudinal beams above and below the nozzles, stiffeners between them, two ventilation housings.
- Navigation lights at the tips: red on the pilot's left, green on the right.

**Cockpit**

- Everything starts from the canopy glass. Cockpit tub walls are planes passing through its edges, flared 8% toward the floor. A bolted sill rail follows each edge; the two rails meet in miters at the tips.
- The coaming lies in the sill plane, from the front tip of the glass to the instrument panel. The head-up display is on the sight line.
- The main instrument panel spans the walls, tilted 27° toward the eye. Wings and consoles follow each wall with the same profile: an inclined panel below the rail, then an elbow-height shelf.
- Equipment uses standard modules: printed panel, chamfered edge, four quarter-turn fasteners. Switches, guards, rotary selectors, circuit breakers, indicator lights, keyboard and dials are placed at their label coordinates.
- The same display housing is mounted three times: machined frame, edge buttons, screws.
- Seat on sliders, sheet-metal side plates and bucket, guide rails, headrest housing and harness. Equipment bay and screwed access hatches behind the seat and on the consoles.
- Shuttle panel palette: painted gray, black housings, brushed metal, white labels.
- All faces are planar. Round parts are smoothed; edges above 35° remain sharp. Left and right are the pilot's, looking toward −Y: left is +X, on the throttle side.

**Mesh**

- 21,237 triangles, 11 meshes and 60 primitives in the GLB, 4.8 MB. The cockpit is merged into a single mesh at export, one primitive per material; the HUD combiner and canopy glass remain separate.
- Blender unit: meter. About 9.8 m long and 6.2 m wide. In Blender: forward −Y, up +Z. At glTF export: forward −Z, up +Y.
- PBR materials, transparent canopy glass and emissive displays. The hull uses tileable 1024 × 1024 color and roughness on `UVMap`. Panels add a 4096 × 4096 normal map and 2048 × 2048 occlusion map, baked on `UVDetail`: `coque_details_normale.png` and `coque_occlusion.png`. These textures are a new game approximation, not a bake of the original procedural materials.
- Normals and tangents are present in each primitive. The normal map is in tangent space. Roughness, normals and occlusion are linear data.
- The engine must read the second UV set: `normalTexture` and `occlusionTexture` in the “Jeu | Tole” materials use `texCoord: 1`.

**Integration**

- The export was reimported and rendered in Blender. The engine loads it through the `vaisseau.vsx` package (`docs/spec-vaisseau.md`).
- `controle_geometrie.py` compares canopy corners with the original model, then checks nine points of each display surface from the pilot's eye, panel joins, tub floor, positions of items under the glass and nozzle positions within the stern. Removing the crossbars and glass inset creates a maximum deviation of 1.7 cm at the reference corners. This check does not replace inspection from every player position.
- The engine must import glTF, handle PBR materials, canopy transparency and emissions, then validate axes, scale and lighting in flight. Exhaust plumes must be made separately.
- **The stick and throttle move in the engine** (`pieces_mobiles.py`):
  - each vertex carries a `_POSE` attribute, exported in the GLB: 0 fixed, 0 to 1 for the stick, 1 to 2 for the throttle;
  - the stick boot goes from 0 at its flange to 1 at the top; the housing stays fixed;
  - two empties, `Pivot | manche` and `Pivot | gaz`, give each part's pivot and Z axis; these are found from geometry, without copying dimensions.
- Displays are static elements. Maps include neither baked ambient occlusion nor levels of detail. Cockpit scene lighting is not exported: its in-game lighting remains to be adjusted in the engine.

**Reproduction**

- Run `textures_cockpit.py` with Python and Pillow, then open the original in background mode with Blender 5.2 and run `preparer.py`. `design_v2.py` rebuilds the hull and cockpit; textures and GLB are saved in this directory.
- To modify a panel, edit its module in `modules_cockpit.py`, then rerun both steps: the label and control move together.
- After editing the stick or throttle in the working scene: `blender -b vaisseau_travail.blend --python pieces_mobiles.py`, which marks, saves and exports, then `python paquet_moteur.py`.
- `verifier.py` renders scene views; `verifier_glb.py` reimports and renders the GLB; `controle_geometrie.py` checks its joins in the working scene. These scripts do not require a Blender window.
