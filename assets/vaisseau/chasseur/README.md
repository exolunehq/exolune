# The concept fighter

**Source and silhouette**

- The user's three-quarter concept is the artistic reference.
- `forme_chasseur.py` defines the hull, canopy, wings, elevons, intakes, nozzles and pilot eye in metres.
- The nose points toward -Y, up is +Z, and the pilot's left is +X.
- The chine, blue shoulder stripe, orange nose band and four engine outlets retain the concept's overall proportions.
- The foredeck rolls down beside the canopy, with up to 22 cm of shoulder relief and an 18 mm forward rake.
- The glazing boundary and canopy shape stay fixed; the nose is hidden by physical geometry from the pilot eye and its normal translation range.
- The previous form N remains in `../archive/forme-n/`.
- Historical construction and measurements are in [the ship history](../../../docs/log/spec-vaisseau-historique.md).

**Default model**

- The executable and launcher select this fighter by default.
- The original triangular model remains one directory above, selected with `-ModeleVaisseau classique`.

**Cabin assembly**

- `cockpit_chasseur.py` builds the tub, dashboard, consoles, controls and seat.
- Each console has one continuous inclined fascia, a horizontal control shelf and a folded knee panel.
- The fascia defines the instrument layout; upper infill joins it to the curved cockpit wall.
- `encastrements.py` cuts closed pockets into the actual chassis before fitting the instruments.
- Seven fitted printed panels and three live displays are inset; four side service covers use the same construction.
- `panneaux_cockpit.py` derives each panel outline from the usable support surface, with 7–12 mm edge margins and chamfered corners.
- Each side has one full-length fascia panel and one shelf panel; tapered dashboard wings fill the space beside the displays.
- Dashboard wings stop at the visible console junction, rather than extending behind it.
- A 65 mm lateral return follows a cubic curve from the dashboard into each console; the flat instrument bays begin at d = 3.84 m.
- Return sections advance monotonically toward the seat and meet the neighbouring faces tangentially.
- Control hardware and printed legends share the same coordinates after fitting the panel outline.
- Each support receives one compound Boolean cut with Blender's manifold solver, preserving the coplanar pocket floors.
- Printed faces sit 1.5 mm below the fascia; display rims project by only 1 mm.
- Pockets are 10 mm deep for controls, 28 mm for displays and 12 mm for service covers.
- The 18 cm shelf follows the console direction and leaves clearance around the horizontal controls.
- Only the two exterior identification plates retain fitted mounting sockets.
- The dashboard spans the tub; its coaming meets the canopy sill.
- Its shallow curved crown keeps the centre at 0.845 m and lowers the shoulders by 35 mm along the dashboard plane.
- The alert strip follows this curve; the coaming meets the dark chassis return without overlapping it.
- The pilot eye, camera settings and three display planes retain their previous positions.
- Display bezels return to the recessed screen surface instead of leaving an open rim.
- Structural housings carry 1.5 mm bevels with two segments.
- `cadre_verriere.py` builds a flat glazing retainer, 34 mm wide and 12 mm thick, with 2 mm edge chamfers and a separate 4 mm seal.
- The glass retains its analytic shape, sampled at 64 columns and 52 rows to resolve the thin frame.
- The pilot eye and three live display roles stay the same.

**Visible fittings**

- `finitions_cockpit.py` adds fitted defogging grilles, screwed service covers, knee rails and canopy latch housings.
- Electrical harnesses terminate in connectors and have bolted clips along their route.
- Seat feet bolt to the floor rails; shoulder and lap restraints have anchors and continue to the central buckle.
- Upholstery uses curved bolsters, a rounded headrest, welts and stitch rows.
- A guarded emergency handle mounts to the front of the seat bucket.
- Service placards and exterior EX-01 identification plates share the panel label atlas.
- The stick, throttle and four elevons keep their six animation pivots and `_POSE` attributes.

**Materials and export**

- The exterior retains its 4096px hull atlas: colour, roughness/metallic, normal and occlusion.
- Cabin paint, rubber, upholstery, woven straps and brushed metal use distinct material factors.
- `textures_finitions.py` generates two shared 1024px linear maps: `cabine_normale.png` and `cabine_metal_rugosite.png`.
- Four padded swatches describe coating grain, leather pores, woven fibres and directional machining.
- Cabin normals and roughness use nondegenerate `UVMap` coordinates; the hull and printed panels use `UVDetail` for micro-surfaces.
- The panel atlas combines graphite and petrol paint, fine coating grain, subtle hand wear, pale legends and cyan sector markings.
- `modules_cockpit.py` remains the common source of control positions and panel printing.
- Its deterministic atlas packer preserves 1800 px/m source labels within 4096px, including the full-length panels and placards.
- `exporter.py` applies each part's modifiers before joining the cockpit and exporting the GLB.
- `paquet_moteur.py` writes VSX version 3, validates all material roles and six pivots, and repairs singular tangent frames in both delivery formats.
- The current GLB contains **61,698 triangles, 15 meshes, 34 materials, 48 draw ranges and 12 images**.
- GLB: about 17.3 MB; VSX: about 17.8 MB.
- All 12 engine image slots are used; another image needs a deliberate descriptor-layout change.
- These are asset counts, not performance measurements.

**Rebuild from the worktree root**

```powershell
python assets/vaisseau/chasseur/textures_cockpit.py
python assets/vaisseau/chasseur/textures_finitions.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --python-exit-code 1 --python assets/vaisseau/chasseur/design_chasseur.py
python assets/vaisseau/chasseur/paquet_moteur.py
```

- Rebuild `textures_chasseur.py` when the exterior shape or atlas changes; its paint boundaries follow the hull sections.
- The working scene is `vaisseau_travail.blend`; deliverables are `vaisseau.glb` and `vaisseau.vsx`.
- Relative render destinations in design_chasseur.py resolve from the worktree root; rendus_finitions.py takes an absolute path.
- `ShipChasseur.hlsli` duplicates the canopy and nozzle geometry; `ShipProfiles.h` holds the camera and resource dimensions. Keep both in agreement with this asset.

**Review**

- `controle_finitions.py`, run in Blender on the working scene, checks 504 support contacts, 14 pocket depths, fascia protrusion, actual control clearance, 27 display sightlines, eye clearance and six pivots.
- `controle_visibilite.py` checks that no foredeck is visible in the forward cone from five pilot-eye positions and that all 1,180 dashboard-wing samples remain visible.
- `rendus_finitions.py -- ABSOLUTE_OUTPUT --glb`, run in an empty Blender scene, imports the delivered GLB and renders eight inspection views on the CPU.
- Its canopy is hidden in the four assembly views and visible in the forward pilot, canopy, exterior and rear views.
- `verifier_glb.py` checks two additional views of the reimported GLB with the canopy present.
- `cockpit.png`, `commandes.png`, `siege.png` and `pilote.png` show the current reimported cabin under inspection lighting.
- `vue_vol.png` shows the forward sightline from the pilot eye at 16:9; its camera looks horizontally, while the game's resting head looks 4.5° down.
- `verriere.png`, `exterieur.png` and `arriere.png` show the revised frame and exterior; `dessous.png` documents the unchanged underside.
- `export_controle.png` and `export_pilote.png` show the additional GLB checks.
- These studio views verify the asset; the engine has its own sky, shadows, exposure and glass shader.
- In-flight review: `tools/tests/2026-11-01-vaisseau-finitions.txt`; use F1-F8, Tab, H and R.
- Build first with `tools/lance.ps1 -Build -NoLaunch`, then launch that route with `tools/lance.ps1 -Parcours tools/tests/2026-11-01-vaisseau-finitions.txt -Resolution fenetre`.
