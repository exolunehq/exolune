# Celestial sky

**Status**
- Integrated prototype, 2026-11-07; native stills verified, in-flight user review remains open.
- Replaces the unavailable `etoiles` branch implementation described in [the archived research](log/recherche-ciel-nocturne.md).
- Fictional system; no terrestrial star catalogue or claim of real ephemerides.
- Superseded visual choices: `log/spec-ciel-celeste-historique.md`.

**One light scale**
- Solar irradiance is pi in scene units, approximately 126,000 lux.
- Stellar magnitude uses the solar reference V = -26.74.
- Reflected bodies use diffuse reflectance, solar distance, surface-integrated phase and observer distance; all three airless moons share particulate photometry.
- Exolune casts a finite solar penumbra on the bodies.
- The review Sun controls the illumination of the entire system.
- Three moons have radii 1,800 / 700 / 260 km and orbital distances 280,000 / 110,000 / 42,000 km.
- Three outer visual bodies use orbital radii 0.68 / 1.65 / 4.7 AU and body radii 6,100 / 4,200 / 63,000 km.
- Circular Kepler orbits follow the shared weather clock; pausing the world also pauses the system.
- CPU positions use double precision; camera-relative shader positions use kilometres.
- Infinite reversed depth keeps the finite Sun and planets beyond the old terrain far plane.
- The near plane stays at 5 cm; reversed Z remains infinite at astronomical distances.

**Resolved and unresolved bodies**
- Distant moons, planets and the Sun use ray/sphere intersections within their projected rectangles, ordered by depth.
- Their angular radii follow physical size and observer distance.
- All three moons have shared procedural terrain, distinct manifest seeds and a cooked distant proxy from that same field (`spec-lune-terrain.md`).
- Manifest reflectance colours vary the moons; the giant uses procedural gas bands.
- The illuminated hemisphere faces the finite Sun.
- Weak reflected planet light preserves part of the dark lunar hemisphere.
- Pixel coverage filters the silhouette.
- Resolved bodies write their actual scene depth before atmospheric integration and temporal reprojection.
- Subpixel bodies hand their integrated flux to the stellar point-image renderer.
- Exolune, terrain, vegetation, ships and resolved celestial discs occult the background.
- All three moons have landable terrain and contact; the outer planets and Sun remain visual bodies.

**Stellar points**
- 42,000 deterministic stars span apparent magnitudes -1.46 to 8.
- Counts interpolate through 171 at magnitude 3, 1,600 at 5 and 4,800 at 6.
- Bright points cover the sphere; fainter populations concentrate towards the common galactic plane.
- Warm and cool spectral approximations preserve integrated luminance.
- A normalized Moffat profile distributes each point's flux over its pixel footprint.
- Four quadrature samples stabilize subpixel motion.
- No random time modulation or scintillation.
- Stellar light is added after terrain temporal smoothing and before glass and display encoding.

**Galactic depth**
- Integrate stellar emission and absorbing dust through a 3D spiral disk.
- The observer is 8.2 kpc from its centre, inside the disk.
- Thick and thin stellar populations, spiral arms, central bulge and a narrower dust layer share that volume.
- Near dust attenuates more distant emission and reddens it.
- Two remote galaxies integrate inclined emitting volumes with internal dust.
- There is no sky photograph, camera-facing nebula card or screen-space galaxy pattern.
- Solar-system travel produces negligible galactic parallax; nearby bodies provide the visible depth cues.

**Atmosphere and night**
- Both cloud paths export their actual final RGB transmission.
- Stars and galaxies use it, including coloured extinction near the horizon.
- Point visibility uses the background luminance and the Schaefer rod/cone threshold.
- Diffuse galactic contrast decreases continuously as the sky brightens.
- Moonlight enters the common sky irradiance and atmospheric scattering.
- Water reflects each moon through the same facet distribution and Fresnel law as the Sun.
- Ambient natural night illumination is 2e-8 scene units, about 0.8 millilux.
- A finite 86--98 km airglow layer uses analytic step coverage.
- Atmosphere table coordinates concentrate resolution at twilight.
- The sky irradiance table uses 32-bit floats to retain night light.
- The incident meter continues below sunset; a perceptual key keeps the night dark.
- Above the air, its direct beam follows the observer altitude and apparent planetary horizon; a ground sunset does not imply orbital shadow.
- Scene and cockpit use the incident meter directly; the global temporal filter was reverted after flight review (`recherche-tons-exposition.md`).
- Stellar/diffuse-source response is bounded between 650,000 and 2,000,000; it extends the display range without raising planet exposure.
- Resolved bright bodies use local adaptation capped at exposure 8, preserving visible lunar markings.
- These are perceptual display choices, not increased physical illumination or an astrophotography mode.
- Energy-conserving optical glare is enabled by default at straylight 0.3; stars use the veiled background for visibility (`recherche-halo.md`).
- Fixed sub-code-value dither prevents contour bands in the dark gradients.
- Cockpit screens, instruments, HUD and cabin fixtures dim with the shared incident meter; exterior beacons retain their flux.

**Current limits**
- Moon illumination in material shaders is a hemispherical contribution, without terrain/cloud-cast lunar shadows or solar-eclipse lighting on Exolune.
- Lunar scattering uses the camera's body directions over the short atmospheric path.
- The main terrain solar light remains the existing parallel source at the configured solar direction.
- No orbital interactions, tides, stellar proper motion or complete astronomical catalogue.
- The galaxy density and stellar colours are procedural approximations.
- Off-screen ship reflections do not yet contain the new stellar points or galactic volume.

**Review**
- Build: `powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Build -NoLaunch`.
- Flight: `tools/tests/2026-11-07-ciel.txt`, F1--F12 and the windowed Tests palette.
- Launch: `powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Parcours tools\tests\2026-11-07-ciel.txt -Resolution fenetre -Position '12000 -8 145 -60 90'`.
- Native checks cover day, both twilight stages, moonless/moonlit night, both cloud paths, cockpit instruments, orbital occultation, lunar surfaces and the finite Sun.
- Orbital exposure regression: `tools/tests/2026-11-07-exposition-orbite.txt`, including both user-reported views and actual planetary eclipse.
- Direct-response review: `tools/tests/2026-11-07-exposition-sans-lissage.txt`; F1/F2 cross the reported sunrise in both directions.
- Model checks: `tools/tests/check_celestial.ps1`.
- Functional stills: `tools/tests/capture_celestial.ps1`; optional `-CloudFull` checks the alternate cloud path.
- No performance or quality benchmark is part of this review.

**References**
- [Jensen et al., A Physically-Based Night Sky Model](https://graphics.stanford.edu/~henrik/papers/nightsky/): common photometry, atmosphere and night illumination.
- [Stellarium sky drawer documentation](https://stellarium.org/doc/head/classStelSkyDrawer.html): luminance-dependent limiting magnitude and point-source response.
- [Nordic Optical Telescope sky brightness](https://www.not.iac.es/weather/skybrightness.html): lunar contribution to the sky background.
- [NASA CGI Moon Kit](https://svs.gsfc.nasa.gov/4720/): photometrically normalized lunar colour and matching laser altimetry; image use and derivation in the asset manifest.
