# Documentation

**This directory contains only current material:** the vision, rules, implemented systems and future plans. Outdated material moves to `log/`.

## References

- **`concept.md`:** the cube face that follows the camera, recalculated every frame.
- **`principes.md`:** fix rules, not individual cases. This file is authoritative.
- **`spec-manifestes-corps.md`:** fundamental engine contract: one rendering technology, one descriptive manifest per celestial body, shared detail budgets and negligible distant work.
- **`geometrie.md`:** geometry comes from Exolune's tectonic terrain; its overlays, classified.
- **`journal-planete.md`:** settings history, milestones and tagged experiments.
- **`lancement.md`:** launch the app for an in-flight review; assets to build in a fresh worktree, launcher variables and controls.

## Implemented systems

- **`spec-lune-terrain.md`:** three seeded airless manifests, shared landable rendering, cooked distant surfaces, and bounded contact with retreat/sliding.

- **`spec-ciel-celeste.md`:** altitude-aware orbital exposure; finite moons and planets, photometric stellar points, volumetric galaxies, atmospheric visibility and night adaptation; current prototype and flight review.

- **`spec-reflets-vaisseau.md`:** selectable smooth Navigator exterior, current-scene chrome reflections, physical sky and planet fallback, review route and off-screen limits.
- **`spec-navigateur-cockpit-son.md`:** connected Navigator cabin, live heading and propulsion instruments, interior materials, panoramic viewing field and quiet levitation resonance.

**Terrain and materials**
- **`diagnostic-orbite.md`:** requested comparison against clean `main`; exact activity indexing, spherical-cap pruning, bounded GPU scheduling and the limb fallback fix; since 2026-11-05 night, the fine grid computed only at the limb in orbit, one river query per screen texel, and a startup map of the rivers for footprints wider than 25 km. Erosion costs under 1 ms from 10,000 km; the per-texel river query in mid orbit remains, located by pass. Since 2026-11-07, the erosion against `main`'s frame rate: within 15 % of `main` at every view, the cost split by pass and what remains; review route `2026-11-07.txt`. Moving-camera measurements, native precision limits, material quality comparison and review route `2026-11-05-orbite-correction.txt`.
- **`spec-erosion.md`:** asymmetric valleys, stable water reconstruction, physical banks and first-water contacts. Confluence banks match the receiving section and local flow. River queries share exact activity masks and conservative bounds; screen work uses bounded node queues and complete overflow fallback. Restart state: `../PASSATION-erosion.md`. Orbital corridor regularity remains only partly improved. Confluence sediment bars, long estuaries, independent distributary contacts, lake boundaries and finer tributaries remain open. Earlier evidence is in `log/spec-erosion-historique.md`.
- **`spec-rendu-lointain.md`:** the same planet from orbit to ground, the universal boundary rule; the screen relief above 150 to 400 km, validated in flight on 2026-11-02.
- **`spec-normales-spline.md`:** per-pixel B-spline normals; coherent fine-grid height and slope reconstruction under mountain flight review.
- **`spec-textures-generees.md`:** material tiles generated at startup and their tiling; rock has used a photo since 2026-10-24.
- **`spec-texturage-universel.md`:** each material's detail scale, from texel to kilometer, and the quality benchmark that checks it; step 3 in progress.
- **`spec-photos-par-echelle.md`:** real photos recomposed by our noise functions; biome palette and photo ground materials done, patterns seen from an aircraft taken over by universal texturing.
- **`spec-roche-organique.md`:** the colored stratigraphic column, its lenses and ledges; its rock families, removed on 2026-10-24.
- **`spec-parois-minerales.md`:** cliffs from 100 m to 1 km: the cliff photo and per-pixel strata.
- **`spec-objets-proximite.md`:** ground detail near the camera, pebbles, rocks and grass tufts at fixed positions on the planet, without popping; `jalon/19-detail-sol`.

**Light and air**
- **`recherche-tons-exposition.md`:** direct incident exposure with observer-altitude sunlight; shared cockpit response and tone curve. The rejected temporal filter is archived.
- **`recherche-ombres-relief.md`:** terrain cast shadows, a horizon per vertex; sky occlusion remains to be implemented.
- **`recherche-rayons.md`:** sun shafts, air in the terrain's shadow, using the cast-shadow march.
- **`recherche-profondeur-atmospherique.md`:** distance conveyed by air, haze, low mist and visibility; boundary-layer mist over the regional ground.
- **`recherche-halo.md`:** current energy-conserving optical glare, enabled in normal rendering; 1/θ² response and limits.
- **`spec-rendu-orbite.md`:** orbital atmosphere, cloud photometry and pixel statistics; physical surface depth preserves clouds through the distant-terrain transition.
- **The game's air is rendered through cloud compositing** (`spec-nuages.md`): rays and regional-ground mist rendered there since 2026-10-30, awaiting in-flight review; optical glare is enabled in normal rendering.

**Sea, clouds and vegetation**
- **`spec-eaux-interieures.md`:** rivers and terminal lakes; reported side trenches, coastal contours and river contours accepted; earlier river visibility sufficient for this stage. Coarse routing, volcanic integration, ribbon widths and full approach stability remain open.
- **`spec-mer-fft-spike.md`:** FFT sea, normals and persistent foam, integrated into main; local depth-limited coastal foam under review; physical limitations and connection to planetary wind documented.
- **`spec-nuages.md`:** the game's clouds, from orbit to ground: model, passes, resources, data and provenance, known defects; their shadow on land and sea; their weather map derived from climate since 2026-10-31.
- **`recherche-vegetation.md`:** trees, shrubs and forests from orbit to undergrowth; state of the art; climate, placement and ground canopy implemented; generated plants v1 to v3, removed on 2026-10-30, archived in the log.
- **`vegetation-planetaire.md`:** the game's trees and shrubs, the only foliage, enabled by default; nearby meshes and distant impostors, deterministic population; leaf clusters, precomputed lighting.
- **`spec-diversite-vegetale.md`:** climate-compatible communities, the 31-model default and 91-role generated review banks; roots, porous forest lighting and wind.
- **`recherche-generation-vegetale.md`:** premium game packs and neural authoring; current diversity and native-engine limits; FoliMesh rejected after native review, with the POC archived in the log.
- **`recherche-comfyui-vegetation.md`:** tested native local generation, separate wood/leaf authoring and compact-mesh candidates; evidence, selection and remaining limits.
- **`spec-pipeline-creation3d.md`:** local generation, a hybrid radial tropical witness, structural variations and root volume; seven LODs, impostors and art/performance gates.
- **`spec-rendu-vegetation.md`:** near-trunk curvature and bark, temporally filtered coverage, leaf transmission, litter, canopy transport, bounded observer adaptation and contact lighting.
- **`direction-artistique-vegetation.md`:** the user's eight biome boards, mature silhouettes and volumetric ground connection.
- **`arbustes-climatiques.md`:** twelve shapes across six climate families; same instances and range, shared GPU subranges.
- **`vegetation-hiz.md`:** current-frame depth pyramid and GPU mask for fully occluded impostors; population and drawing order preserved.
- **`optimisation-vegetation.md`:** vegetation culling and GPU timings, preserving appearance, density and distance; memory optimization remains.

**Ship and execution**
- **`spec-ville-procedurale.md`:** generated architecture, neutral house/public-building series and native integration, generated first-draft buildings whose atlas is read as material classes, shared junctions and bounded variants, braided-archipelago masterplan, shared paths, suspended transport, five LODs and native validation.
- **`recherche-generation-architecture.md`:** tested local methods, rejected house reconstructions, original-reference master and exploratory series, hosted first-draft decision and house pilot, separate technical/artistic promotion gates.
- **`spec-marche-ambiances.md`:** instant disembarkation, FPS walking, contextual foot contacts, environmental audio and shared keyboard/button controls.
- **`spec-vaisseau.md`:** default fighter, model selection, cockpit, independent flight/free-camera controls and canopy weather; history in `log/spec-vaisseau-historique.md`.
- **`recherche-vaisseau-navigateur.md`:** Trimaxion references, smooth editable v2 exterior and provenance of the selectable runtime derivative.
- **`recherche-eau-verriere.md`:** water on the canopy glass, drops, rivulets and film in flight; state of the art; simulated drops and trails implemented, awaiting in-flight review.
- **`recherche-son.md`:** ship sound, engine, stabilizers and wind; state of the art, procedural synthesis on XAudio2 selected and implemented, awaiting in-flight review.
- **`execution-optimisee.md`:** Release executable with a local profile, borderless full screen, startup resolution and optional unrestricted presentation.

## Plans

- **`spec-relief-tectonique.md`:** the game's terrain since 2026-10-31: a tectonic map computed at startup, continents, plates and boundaries; large shapes as profiles, detail modulated by geology; CPU port using a cache; steps 1 to 3 done, awaiting in-flight review.
- **`spec-climat.md`:** the game's climate since 2026-10-31: three-cell winds, vapor carried from the seas, windward rainfall and rain shadows, continentality and cold currents, computed at startup from the tectonic terrain; the map read by materials, plants, sea and ship, and by the erosion port; step 1 done, awaiting in-flight review.
- **`spec-volcanisme.md`:** volcanoes derived from the tectonic map, listed at startup and evaluated point by point: arcs, hotspots and their chains, atolls and guyots, rifts, calderas, flows, cones and flood basalts; basalt and ash; experiment `piste/volcanisme`, awaiting in-flight review.
- **`spec-erosion.md`:** replacement of the frozen network-valley stage by ravines and river corridors; current flight route `2026-11-04-confluents.txt`. Earlier trough-stage observations are preserved in the erosion log.
- **`recherche-relief.md`:** planetary terrain, tectonics, erosion, eroded noise and games; licenses; the four-layer architecture and plan behind the spec.
- **`optimisation.md`:** at least 60 fps at 1080p, targeting 120, preserving perceived quality; performance benchmark, baseline and rounds.
- **`recherche-nuages.md`:** cloud cover, weather map, types and rendering from orbit to ground; state of the art and plan; the old volume is in the log.
- **`recherche-mer.md`:** sea and lakes; state of the art and reference laws; coasts and lakes remain to be implemented.
- **`recherche-cotes.md`:** beaches, cliffs and shores; audit of complexplanet at the coast, state of the art and plan; step 1 ported to the FFT sea, beach based on distance to water; step 2 on branch `plages`, awaiting porting.
- **`recherche-rivieres.md`:** streams, rivers and mountain lakes; audit of complexplanet's valleys, state of the art and plan; step 1, the planet map, done; October 26 and 27 spikes archived in the log; research continues on branch `erosion-niveaux`.
- **`recherche-geometrie-proximite.md`:** ledges and meter-scale terrain near the camera, without popping or jitter; state of the art and plan, no decision yet.

## The log

**`log/` preserves outdated material for reference:** closed, superseded or disabled specs, older research and outdated sections of living specs. See `log/README.md`.
