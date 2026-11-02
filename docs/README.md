# Documentation

**This directory contains only current material:** the vision, rules, implemented systems and future plans. Outdated material moves to `log/`.

## References

- **`concept.md`:** the cube face that follows the camera, recalculated every frame.
- **`principes.md`:** fix rules, not individual cases. This file is authoritative.
- **`geometrie.md`:** geometry comes from Exolune's tectonic terrain; its overlays, classified.
- **`journal-planete.md`:** settings history, milestones and tagged experiments.
- **`lancement.md`:** launch the app for an in-flight review; assets to build in a fresh worktree, launcher variables and controls.

## Implemented systems

**Terrain and materials**
- **`spec-erosion.md`:** global drainage, glacial troughs and directional gullies; composed coastal incision filtering, cliff-talus and metric corrections under review; green scar, coastal input sensitivity and distant repetition unresolved.
- **`spec-rendu-lointain.md`:** the same planet from orbit to ground, the universal boundary rule.
- **`spec-normales-spline.md`:** per-pixel B-spline normals; coherent fine-grid height and slope reconstruction under mountain flight review.
- **`spec-textures-generees.md`:** material tiles generated at startup and their tiling; rock has used a photo since 2026-10-24.
- **`spec-texturage-universel.md`:** each material's detail scale, from texel to kilometer, and the quality benchmark that checks it; step 3 in progress.
- **`spec-photos-par-echelle.md`:** real photos recomposed by our noise functions; biome palette and photo ground materials done, patterns seen from an aircraft taken over by universal texturing.
- **`spec-roche-organique.md`:** the colored stratigraphic column, its lenses and ledges; its rock families, removed on 2026-10-24.
- **`spec-parois-minerales.md`:** cliffs from 100 m to 1 km: the cliff photo and per-pixel strata.
- **`spec-objets-proximite.md`:** ground detail near the camera, pebbles, rocks and grass tufts at fixed positions on the planet, without popping; `jalon/19-detail-sol`.

**Light and air**
- **`recherche-tons-exposition.md`:** exposure set by illuminance, the tone curve; state of the art, choices and measurements against photos.
- **`recherche-ombres-relief.md`:** terrain cast shadows, a horizon per vertex; sky occlusion remains to be implemented.
- **`recherche-rayons.md`:** sun shafts, air in the terrain's shadow, using the cast-shadow march.
- **`recherche-profondeur-atmospherique.md`:** distance conveyed by air, haze, low mist and visibility; boundary-layer mist over the regional ground.
- **`recherche-halo.md`:** lens halo around the sun and snow, the 1/θ² law and its measurement; experiment `piste/halo-optique`.
- **`spec-rendu-orbite.md`:** the planet from orbit compared with Apollo 17: aerosol multiple scattering by similarity, cloud light calibrated against Monte Carlo, cloud water independent of coverage, pixel statistics replacing fine rays, orbital exposure; experiment `piste/orbite-rendu`, awaiting in-flight review.
- **The game's air is rendered through cloud compositing** (`spec-nuages.md`): rays and regional-ground mist rendered there since 2026-10-30, awaiting in-flight review; the halo is disabled by default.

**Sea, clouds and vegetation**
- **`spec-eaux-interieures.md`:** rivers and terminal lakes; reported side trenches, coastal contours and river contours accepted; earlier river visibility sufficient for this stage. Coarse routing, volcanic integration, ribbon widths and full approach stability remain open.
- **`spec-mer-fft-spike.md`:** FFT sea, normals and persistent foam, integrated into main; physical limitations and connection to planetary wind documented.
- **`spec-nuages.md`:** the game's clouds, from orbit to ground: model, passes, resources, data and provenance, known defects; their shadow on land and sea; their weather map derived from climate since 2026-10-31.
- **`recherche-vegetation.md`:** trees, shrubs and forests from orbit to undergrowth; state of the art; climate, placement and ground canopy implemented; generated plants v1 to v3, removed on 2026-10-30, archived in the log.
- **`vegetation-planetaire.md`:** the game's trees and shrubs, the only foliage, enabled by default; nearby meshes and distant impostors, deterministic population; leaf clusters, precomputed lighting.
- **`arbustes-climatiques.md`:** twelve shapes across six climate families; same instances and range, shared GPU subranges.
- **`vegetation-hiz.md`:** current-frame depth pyramid and GPU mask for fully occluded impostors; population and drawing order preserved.
- **`optimisation-vegetation.md`:** vegetation culling and GPU timings, preserving appearance, density and distance; memory optimization remains.

**Ship and execution**
- **`spec-marche-ambiances.md`:** instant disembarkation, terrain walking and contextual audio; textured contact layers, six recorded footstep materials and bounded XAudio2 mixing.
- **`spec-vaisseau.md`:** the player's ship, cockpit, controls and canopy weather; common near plane and bounded swept terrain contact, with sampling limits and flight review pending.
- **`recherche-eau-verriere.md`:** water on the canopy glass, drops, rivulets and film in flight; state of the art; simulated drops and trails implemented, awaiting in-flight review.
- **`recherche-son.md`:** ship sound, engine, stabilizers and wind; state of the art, procedural synthesis on XAudio2 selected and implemented, awaiting in-flight review.
- **`execution-optimisee.md`:** Release executable with a local profile, borderless full screen, startup resolution and optional unrestricted presentation.

## Plans

- **`spec-relief-tectonique.md`:** the game's terrain since 2026-10-31: a tectonic map computed at startup, continents, plates and boundaries; large shapes as profiles, detail modulated by geology; CPU port using a cache; steps 1 to 3 done, awaiting in-flight review.
- **`spec-climat.md`:** the game's climate since 2026-10-31: three-cell winds, vapor carried from the seas, windward rainfall and rain shadows, continentality and cold currents, computed at startup from the tectonic terrain; the map read by materials, plants, sea and ship, and by the erosion port; step 1 done, awaiting in-flight review.
- **`spec-volcanisme.md`:** volcanoes derived from the tectonic map, listed at startup and evaluated point by point: arcs, hotspots and their chains, atolls and guyots, rifts, calderas, flows, cones and flood basalts; basalt and ash; experiment `piste/volcanisme`, awaiting in-flight review.
- **`recherche-relief.md`:** planetary terrain, tectonics, erosion, eroded noise and games; licenses; the four-layer architecture and plan behind the spec.
- **`optimisation.md`:** at least 60 fps at 1080p, targeting 120, preserving perceived quality; performance benchmark, baseline and rounds.
- **`recherche-nuages.md`:** cloud cover, weather map, types and rendering from orbit to ground; state of the art and plan; the old volume is in the log.
- **`recherche-mer.md`:** sea and lakes; state of the art and reference laws; coasts and lakes remain to be implemented.
- **`recherche-cotes.md`:** beaches, cliffs and shores; audit of complexplanet at the coast, state of the art and plan; step 1 ported to the FFT sea, beach based on distance to water; step 2 on branch `plages`, awaiting porting.
- **`recherche-rivieres.md`:** streams, rivers and mountain lakes; audit of complexplanet's valleys, state of the art and plan; step 1, the planet map, done; October 26 and 27 spikes archived in the log; research continues on branch `erosion-niveaux`.
- **`recherche-ciel-nocturne.md`:** stars, planets, Milky Way, airglow and the eye at night; implemented on branch `etoiles`, awaiting integration.
- **`recherche-geometrie-proximite.md`:** ledges and meter-scale terrain near the camera, without popping or jitter; state of the art and plan, no decision yet.

## The log

**`log/` preserves outdated material for reference:** closed, superseded or disabled specs, older research and outdated sections of living specs. See `log/README.md`.
