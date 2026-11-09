# Navigator ship references

**Status: references, smooth exterior v2, modelled cockpit and original synthesized sound, 2026-11-03.**

- Subject: the Trimaxion Drone Ship from *Flight of the Navigator* (1986).
- Request: collect images and start a future Exolune model.
- Local collection: `artifacts/references/navigateur/`, excluded from git by the existing `artifacts/` rule.
- Open its `index.html` gallery or `README.md` inventory.
- The collection contains 46 selected 1920 × 1080 video frames and 27 downloaded web images.
- Six additional crops preserve source pixels and record their rectangles in `manifest.json`.
- Every reference records its source, category, dimensions and SHA-256.

**Source order**

- [User's video](https://www.youtube.com/watch?v=qB12mrdYPkc&t=360s): a five-second survey spans the whole 21:04 compilation; selected views cover the exterior, cabin and entrance.
- [Propstore production miniature](https://propstore.com/product/flight-of-the-navigator/trimaxion-drone-ship-model-with-replacement-animation-morphing-stair-sequence/): 20 photographs of the shell and replacement door/stair components.
- [Edward Eyth's portfolio](https://www.eeyth.com/vhclecncpt/): one original concept sheet, distinct from the final hull.
- [Moony's reconstruction](https://blenderartists.org/t/flight-of-the-navigator-update-complete-rebuild-and-new-screen-accurate-fast-mode/1290899): six fan-made topology, morph and print photographs from the later posts.
- [Captain Disillusion's Blender tutorial](https://www.youtube.com/watch?v=KC6es6PSKko): a direct modelling guide for the normal hull, including roof, belly, edge and fold construction.

**Additional video and audio references, 2026-11-03**

- [The Ship's Escape, Higher Quality Uploads](https://www.youtube.com/watch?v=761dtQvVsjo): continuous hangar escape, 119 s; upscaled upload, with the movie audio mix.
- [Ship undocks, athansky25](https://www.youtube.com/watch?v=wddvJkpkZxA): alternate upload of the same undocking sequence, 112 s.
- [CGI Spaceship, Gorkab](https://www.youtube.com/watch?v=1G13KzEJqBw): 140 s montage of CGI shots for flight, shape and reflection references.
- [All Spaceship Scenes, Major Grin](https://www.youtube.com/watch?v=RbuOHKlvtz8): 224 s compilation covering hover, fast flight, water and urban passes.
- Local videos and source metadata: `artifacts/references/navigateur/audio/sources/`.
- The videos remain source references; the rejected mixed-audio extraction stage is recorded in the authoring history.
- `NavigatorSound.h` now supplies an original procedural voice without film audio samples.
- Current cockpit, source construction and sound preview: `spec-navigateur-cockpit-son.md`.

**Read the shapes separately**

- Normal mode has an inflated shell, broad layered folds and a rounded belly.
- Fast mode has a flatter, elongated outline; its images stay in a separate group.
- The 07:35 frame is an intermediate transformation, excluded from reconstruction inputs.
- The 19:35–19:50 prop photographs in the compilation have unverified independent provenance and visible age or alterations.
- Fan orthographic renders explain topology; they are not production blueprints.
- Movie views are perspective images; no authenticated orthographic drawing or full-size metric specification was recovered.
- Video inserts vary in sharpness despite their 1080p container.

**Useful starting views**

| Purpose | Local file or video time |
|---|---|
| Main closed shell | `web/propstore-maquette-12.jpg` |
| Alternate shell angle | `web/propstore-maquette-13.jpg` |
| Two end silhouettes | `web/propstore-maquette-14.jpg`, `web/propstore-maquette-15.jpg` |
| Lower shell | `web/propstore-maquette-16.jpg`, `web/propstore-maquette-17.jpg` |
| Roof in the film | 16:10, 20:05 |
| Belly in the film | 06:20, 19:05 |
| Entrance and scale | 06:15, 06:50, 08:35, 19:10 |
| Fast outline | 00:30, 07:45, 20:25 |
| Cabin and pilot station | 05:40, 05:55, 08:40, 10:30, 15:15 |

**Smooth exterior prototype v2, 2026-11-03**

- Working directory: `E:/ExoluneAssets/navigateur-normal-v2-smooth/`.
- Delivery copy: `artifacts/modeles/navigateur-normal-v2-smooth/`.
- `navigateur-normal-lisse.blend` retains an editable quad cage and a Catmull–Clark subdivision modifier.
- `navigateur-normal-lisse.glb` carries the evaluated surface and the existing analytic chrome material.
- The source is the first neural shell; [its authoring history](log/recherche-vaisseau-navigateur-historique.md) preserves the original graph and conversion.
- 32,768 rays sample its closed surface in an ellipsoid-normalized frame.
- A spherical harmonic fit through degree 64 suppresses fine reconstruction variation with quartic attenuation at degree 40.
- X reflection symmetry is enforced before fitting; the fitted body is centred at the origin.
- One global axis scale preserves the source bounding dimensions after surface fitting; it does not project the skin back onto the acquired mesh.
- A closed cube-sphere cage has 6,146 control vertices and 6,144 quads.
- Two subdivision levels produce the delivered 196,608 triangles.
- The base geometry carries the intended broad folds and silhouette; photographic wear is removed from the skin.
- The source and fit are retained separately; subdivision remains editable and the dense source is not projected back onto the finished surface.
- Geometry and material checks use the reimported GLB from both sides, cardinal directions, above and below.
- Reflection stripes expose the roof, flanks and underside; neutral views check silhouette and folds.
- The analytic chrome keeps base colour `(0.84, 0.87, 0.91)`, metallic 1 and roughness 0.13.
- The shinier roughness-0.06 material is only a reflection inspection aid.
- The exported shell has zero boundary and non-manifold edges after reimport.
- `source.json`, `inspection.json`, the radial samples, coefficients and scripts retain the source hash and reproducible construction.
- The runtime derivative uses scale ×4 and a half-turn around Z: about 7.99 m wide, 7.63 m long and 4.35 m high, nose −Y and up +Z.
- This scale is an authoring choice; no authenticated metric plan was found.
- `assets/vaisseau/navigateur/` retains the editable source, GLB and VSX3 runtime packet.
- Optional `navigateur` selection starts in its reconstructed cockpit; the fighter remains the default.
- Runtime chrome uses roughness 0.075 and current-scene reflections, with a physical sky/planet fallback; `spec-reflets-vaisseau.md`.
- The continuous cockpit, fitted seat, recessed controls and wall-mounted sensor are authored in `cabine_maillage.py`.
- The forward viewing field is clear inside while the exterior remains opaque; `spec-navigateur-cockpit-son.md`.
- Entrance, steps and moving controls remain to be authored.

**Authoring route**

- Start with the normal closed shell and a single three-quarter reference.
- The existing `tools/foliage/comfyui/pixal3d_trellis2.json` supplies a reusable authoring graph; its vegetation choices need adapting to a manufactured shell.
- [TRELLIS.2](https://docs.comfy.org/tutorials/3d/trellis2) produced the first shape proposal; this does not establish production fidelity or game performance.
- [Pixal3D multiview](https://docs.comfy.org/tutorials/3d/pixal3d) is another candidate when the selected views depict one consistent configuration.
- Refine the silhouette and broad folds through the editable quad cage; retain symmetry and subdivision.
- Evaluate the silhouette with a neutral material before adding chrome.
- Rebuild the reflective material separately so photographed reflections do not become geometry or painted lighting.
- A morph between configurations requires matching topology after reconstruction.
- Model the entrance, steps and cabin as separately controlled parts.
- Runtime integration follows `spec-vaisseau.md`: metres, nose −Y, up +Z, pilot's left +X, and a complete model-specific geometry profile.
- Third-party images remain local references; no redistribution licence was obtained for them.
