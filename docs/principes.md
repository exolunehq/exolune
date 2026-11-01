# Principles: correct by rules, not on a case-by-case basis

Status: reference, since 2026-10-22. Any fix and any new function complies with it; the specs detail, this file is authoritative.

## The principle

**We generate a whole planet, on a real scale, with an infinity of places and shapes. A correction that only applies to the view is almost useless, and often breaks something else.**

- **Before correcting,** ask yourself which family of problems the reported case is an example of, and which rule it violates.
- **Correct the rule, where all cases pass,** not the case.
- **Write the rule here,** with the link to the spec that details it.
- **Check on multiple locations and families,** not only on the reported view, with the benchmarks below.
- **If a specific correction is unavoidable,** a material-specific data or a calibrated setting, document it as such, with its reason and limit.

## Public Git history

**The public repository must never receive commits from the old-license history.**

- **The only remote is `origin`:** `https://github.com/exolunehq/exolune.git`.
- **Publishing a ref also publishes its ancestry.** The restriction applies to branches, tags and commits brought in by merges, even when the tip uses the current license.
- **Base new changes on the public history.** Transfer new changes without importing the old ancestry.
- **Before any requested push,** recheck the remote URLs, the selected refs and every commit that would become reachable publicly.
- **Publish only explicitly selected, verified refs.** Do not use `--all`, `--tags` or `--mirror` while legacy refs are present.

## The established rules

**Selecting a manufactured asset selects its complete geometry profile** (`spec-vaisseau.md`).
- Keep each selectable model's source and delivery files in its own asset directory.
- Match the pilot eye, canopy weather surface, shadow centre, engine mouths and animation pivots to that model.
- Change the default through model selection; retain previous models and their packet compatibility.

**Manufactured parts derive their interfaces from the visible support mesh** (`spec-vaisseau.md`).
- Design the common fascia and instrument depth together; cut actual recesses for installed equipment.
- Derive panel outlines from the usable support surface, with metric edge clearance; validate the actual control hardware against each outline.
- The usable outline ends at the visible intersection with neighbouring parts, not at the hidden tub wall; check visibility from the pilot eye and its travel limits.
- Console returns share their dashboard boundary and join the console tangentially; their sections must advance monotonically.
- Keep fitted control positions and printed legends in the same coordinate mapping.
- Cut each support's complete pocket layout together so adjacent coplanar floors remain closed.
- Keep printed instrument faces below the fascia and exposed rims thin; mounting contact alone does not establish a coherent design.
- Join coaming sheets at the chassis return instead of overlapping its top face.
- Glazing retainers have flat structural faces and a separate narrow seal; their section follows the glazing tangent plane.
- Fit the whole mounting perimeter along the mounting normal; a centre point or constant-depth block cannot establish contact with a curved panel.
- Derive shelf width from module dimensions and assembly clearance.
- Close recessed display rims and attach hoses, straps and handles to explicit fittings.
- Preserve a finite orthogonal tangent frame at UV poles in both GLB and cooked packets.
- Inspect the reimported asset from several viewpoints and retain the in-flight review route.
- Solve nose visibility in the physical hull shape; keep the glazing contact, external paint layout and attitude-jet origins consistent with it.

**Out-of-real-time rendering follows the movie clock, never the time of the calculation** (`lancement.md`, the cinematic mode).
- **A common step to everything that advances:** sea, plants, glass and histories; poses and the weather moment come from the course.
- **Safety does not draw the route:** the generator keeps a free band around the flight; any engine clamp is logged.
- **An external camera does not move the ship:** their poses remain independent, with the same rendering and shadows as the game.
- **A connection of flight segments does not require a stop:** position, speed and acceleration remain continuous; only landing, pause and start of take-off require rest. The cruise follows the length of the safe route; the orbit keeps its exponential altitude.
- **The margin protects the ground:** each segment can specify it; on the sea, the height requested starts from the level 0, with a minimum of 3 m.

**Geometry comes from the Exolune relief,** `Relief.hlsli` (`geometrie.md`).
- **Rendering does not change the shape:** the appearance of materials is worked in colors, textures, pixel normals, parallax and shadows.
- **Any geometry modification is a documented overlay:** filtering, detailing under 13,5 m, or replacement.
- **A replacement is a separate subject,** on a experiment tagged, until explicit decision.

**What a point cannot know alone is read on a map of the planet** (`PlanetMap.hlsli`, `Tectonics.hlsli`, `recherche-rivieres.md`, `spec-relief-tectonique.md`).
- **Maps on a cube fixed on the planet:** the map of the planet, drained relief, where the regional soil of the fog comes from, the level of the bowls and the way to the sea; the tectonic map, the plates and their boundaries.
- **Everything at startup, nothing on the way:** speed has no limit, we go from one place to another, from one planet to another, in one image. No data is calculated during a journey or in the background.
- **The perimeter is a solar system:** the maps of all its planets and moons are calculated at startup, once per seed, then remain in memory; a disk cache per seed can keep them. Their time and memory budget is the same as the whole system.
- **A planet the size of Earth: less than a second and 40 MB on the GPU** (`spec-relief-tectonique.md`). What only the views or the 0 level read does not rise to full resolution on the GPU; a propagation stops at the reach of what it shapes; what does not depend on each other is computed at the same time.
- **On the grid of the planet:** nothing depends on the camera; the same place gives the same value everywhere.

**A pre-calculated map can carry geometry, under three conditions** (since the 2026-10-31; it replaces "data, never geometry", `recherche-relief.md`).
- **Fix planetary data:** calculated once per seed, in the planet's reference frame.
- **Read continuously:** no seam between the faces of the cube, no walk from one texel to another. A map that bears a shape cannot be read in bilinear: the slope would jump at every texel, and the light would draw the grid.
- **Limited to the scales they resolve:** above two of their cells. The noise does the rest, and has no octaves above.
- **The tectonic map bears the large shapes since the 2026-10-31,** read in cubic B-spline, the faces of its cube mixed near their edges; the map of the planet remains of the data (`spec-relief-tectonique.md`).

**Geology decides, the noise details** (`spec-relief-tectonique.md`, since the 2026-10-31).
- **Any form of more than 50 km comes from the tectonic map:** no noise of the detail has an octave above.
- **Every analytical profile has a width of at least two grid cells:** wider, its depth decreases by the same amount, and the relief keeps its average.
- **A profile that crosses the sea filters its emergent part:** it covers at least two grid cells, or the profile remains underwater; expanding its support alone is not enough. The filter redistributes the height, without changing the area of the profile; no shape depends on the grid cell outside this filtering (`spec-relief-tectonique.md`, the cords).
- **Each profile follows a published law,** cited with its source: ocean depth by age, bending of the lithosphere, width of the plateaus.
- **A noise that moves a limit is adjusted in distance:** its amplitude is the slope of the field times the desired displacement. A coast is cut as much on a flat plain as against a mountain range; set in meters, the same noise moved it of 30 km on one, of 1 km on the other (`spec-relief-tectonique.md`, the coasts).
- **A smooth shape follows a smooth field, never the contour of a noise field:** the contour of a noise fine has its angles and its ridges. A cordon follows the shore without the fine octaves of the noise of the ribs or the detail; its crest rises from the relief below it, entire (`spec-relief-tectonique.md`, the ribs).
- **A noise never shears on a narrower area than its displacement:** shifted from 8 km to 0,6 km on either side of the transforming faults, the detail stretched in straight trenches, parallel cornices and rows of teeth. A width depends on the grid cell only to filter away.
- **A profile never stops sharply along its border:** its strength is smoothed along it and fades at its ends; two neighboring forms combine in smoothed maximum, never in sum or cut.
- **What is placed on a shape of the map is placed where the shader draws it:** its place read in the map, then brought back by the left reading of the map. Without this, the volcanoes of an arc fell down to 30 km from its ridge (`spec-volcanisme.md`, since the 2026-10-31).
- **One shape placed on another follows the contour, and its width varies with what shapes it:** a reef, the leveled top of a guyot follow the contour of their volcano; the plateau widens windward, the passes open leeward. A separate circle, of constant width, made atolls in rings (`spec-volcanisme.md`).
- **A pattern placed on a shape has a zero average:** it draws, it does not mount the shape. The flows of a volcano, laid on top of his building, drew a ring where they begin; their tongues are above him, the ground between them below (`spec-volcanisme.md`).
- **Nothing thinner than the 0 level blocks any of its watercourses** (4 stage).

**The climate comes from geography, the noise details it** (`spec-climat.md`, from the 2026-10-31).
- **Rain and temperature are calculated at startup,** on the large forms: the winds of the three cells, the water vapor carried from the seas, the rain windward of the reliefs. Never an imposed band of latitude: deserts fall where traffic and relief leave them.
- **The climate map bears what exceeds two of its cells, 100 km;** a gradient noise does the rest, and what the pixel does not show expands the limits drawn on humidity.
- **Climate only reads the form before erosion:** erosion reads rain, never the other way around.
- **Clouds also come from climate:** their weather map is calculated at startup on its fields and the relief, convection, subsidence, cold currents, depression tracks, slopes windward (`spec-nuages.md`). No cloud field taken from a noise without link with geography.

**From far as close, the same planet** (`spec-rendu-lointain.md`).
- **A pixel shows the average of what it covers.** Any boundary between materials widens from what the pixel cannot show from its inputs: `SpreadStep`, `SlopeShares`, `RockShares`.
- **A noise never fades depending on the pixel size.** It remains the same at all distances; only its invisible part expands the limits.
- **The relief keeps its average height at any distance,** regardless of the octave filtering.
- **Decisions see the relief forms at any height.** The fine grid carries their normal as long as the mesh does not carry the finest octave, 13,5 m, on its 4 grid cells. Extinct from grid cells of 20 m, it let the forms of 13,5 to 100 m of snow and rock come and go from 2 km to 160 m (`journal-planete.md`, 2026-10-24).
- **A width is decided on the slope taken at its own scale.** The range, a water level, is capped at 120 m once the slope is taken on 60 m, `SHORE_BASELINE`. On the normal of materials, taken at 1 m, the bumps of the relief left kilometers of coastal plain in sand. In the distance, the fine grid carries this slope as soon as its grid cells covers 60 m; thinner, they bring back the bumps (`recherche-cotes.md`).
- **A noise color filters to pixel, never to grid cell.** A grid cell covers about 13 pixels: calculated by vertex, its octaves appear in sight when approaching, and what it draws slides (`spec-parois-minerales.md`).
- **Every pattern is calculated on the planet grid, never relative to the anchor.** The anchor jumps by 64 m when the camera moves; a stretch or rotation taken from it re-cuts the pattern. The ravines of `WallRelief` were infringing it; it is removed the 2026-10-30.
- **A quantity passed from one pass to another retains the accuracy of the scale it serves,** not that of its size. The distance of the ground serves the atmosphere to the meter close and exceeds 30 000 km: half-floating, its steps of 16 km drew circles on the oceans. The HDR image is in floating 32 bits. Likewise, the smoothed distance at the border, hundreds of km, moves the noise of the chains to the meter close: floating, its steps of a few cm made walls on the ground; it is read in double precision (`journal-planete.md`, 2026-10-31). The small cones of a volcano, up to 120 km from its summit, are placed in double precision (`spec-volcanisme.md`).
- **Reference photos set exposure at each scale.** On the ground, those of the landscapes, +1 EV; orbit, those of the Earth, 0 EV; between the two, the part of the air under the camera. Always an incident exposure meter, never the image reading (`spec-rendu-orbite.md`, `recherche-tons-exposition.md`).
- **A shadow follows the limit rule** (`recherche-ombres-relief.md`). The horizon of the relief is interpolated between the summits like an angle; the part of the sun is taken by pixel, enlarged by the spread of the horizon it covers. The relief thinner than the grid cell keeps its share of shadow, on average: the Smith shading, `FinerReliefLit`.
- **What acts on the screen is calculated even off the screen.** A vertex whose shadow can fall on the screen is calculated (`ShadowSweep`); otherwise shadows appear when the camera rotates.
- **A noise never shows its grid: noise gradient, never value.** A noise value is flat around each point of its grid, and its octaves, on nested grids, align their plates. From afar, the pixel only keeps two or three: they pave the floor like a low-resolution image. One noise, `Noise3`, for all fields, including climate and geology (`journal-planete.md`, 2026-10-24).
- **The octaves of a noise never share the nodes of their grids.** A gradient noise cancels itself at its nodes; on nested grids, all octaves cancel together, and a threshold on their sum draws rows of orbital points. Each octave is shifted by a fraction of grid cell (`CloudFbm` of the old volume, `log/recherche-nuages-historique.md`).
- **A close-up volume is calculated in 3D, not in extruded 2D field.** The thin octaves of a 2D field, raised in height, make cliffs and needles. They pass into a noise 3D of the same standard deviation, of which the mips make the average far (`ResolvedColumn` of the old volume, `log/recherche-nuages-historique.md`).
- **The formation of a cloud remains anchored in the world.** At time freeze, its density is not dependent on the camera, the mesh or the sliding anchor. A reference without history or cascades is used to check the approach before optimizing (`log/poc-nuage-stable.md`).
- **Clouds share a time and a weather field.** Wind and deformations are read in the world with this clock; views, the number of images and the identity of formations do not change it. A weather break leaves the camera free (`D3DApp.cpp`, `kWeatherWindSpeed`; `spec-nuages.md`, weather).
- **A pre-calculated density volume keeps the reference frame and the time of its source.** The camera does not choose its origin or phase. If the final density depends on time, publish the full volume of that same time before reading it (`log/poc-nuage-voxel.md`).
- **Combined directions must belong to the same reference frame.** A sun expressed in the field face must be transformed before a calculation with planetary positions; explicitly provide camera and sun world to the relevant passes (`log/spike-nuages-voxel-planete.md`).
- **Passes share an explicit GPU contract.** Reserve a range of resources per system; keep constant structure identical in C++ and HLSL. Weather has its fields, separate from the vegetation and sea indicators (`spec-nuages.md`).
- **The validated rendering is that of the executable without variable.** A code present but disabled does not count; a variable is only used for benchmarks and comparisons. A missing resource stops the boot with a message, without silent return to an old rendering (`spec-nuages.md`, `lancement.md`).
- **Optimization distinguishes quality, resolution and presentation rate.** Compare with identical resolution and settings before assigning a gain; a capture remains invisible even if the flight profile requests full screen (`execution-optimisee.md`).
- **Sun shade reduces the sunlight received by the surface.** Keep sky and air separate; plot the same volume, at the same time, from the receiver to the sun, including above the sea (`spec-nuages.md`).
- **Color, depth and solar share describe the same visible surface.** Any opaque pass, including impostors and meshes after HiZ, replaces both colors with the same alpha discards. A solar transmission of 1 leaves the color exactly intact; a shadow never reintroduces the object hidden behind (`spec-nuages.md`).
- **A distance on a map is not a distance on the planet.** A global weather jump is limited by the spherical boundaries of the cells, with the filter margin; the connection and poles are part of the contract (`spec-nuages.md`).
- **An acceleration envelope does not draw the shape of the volume.** Its density extinguishes before the faces of this envelope; its visible boundaries come from continuous local profiles, not from the course shell (`log/spike-nuages-reference.md`).
- **Multiple layers are composed in the order of radius.** Sorting their segments before accumulating light and transmittance; skipping the vacuum between layers keeps this order (`log/spike-nuages-cirrus.md`).
- **A soft extinction is verified on the final density, and its continuity does not validate the silhouette.** The threshold and erosion can intersect a gradient; even continuous, a nearly uniform substrate can give opaque flat faces. Judge together the 3D fields, local heights and optical thickness. Geometric parameters remain global and independent of the camera (`log/spike-nuages-reference.md`).
- **Proof of vacuum requires a presence bound.** The levels used for a jump keep a conservative maximum and filter margin; neither a mean nor a null sample proves the void of the interval (`log/spike-nuages-reference.md`).
- **A skipped calculation is proved to have no effect.** A decision on a threshold stops when a rigorous limit of the other can no longer change it, never on a standard deviation; what is only useful in a branch is calculated in the branch (`optimisation.md`, round 2).
- **A closed form keeps the domain of what it replaces.** A rounding can get it out of [0, 1] where the loop could not: bounded, otherwise a root gives a NaN, isolated white pixels (`optimisation.md`, round 2).
- **A costly pixel is calculated once, on the viewed surface.** The ground writes its depth first, its color after the foliage, in equal depth (`optimisation.md`, round 2). The meshes plants are the same; at equal depth, the color keeps the first drawn, as the strict test: it is drawn in the reverse order (round 3).
- **A pixel that writes its depth declares it bounded as soon as a bounded is proven.** Its primitive is placed at the bound, the pixel promises it (`SV_DepthLessEqual`): the test rejects before the shader. The impostors take the end of their HiZ test (`optimisation.md`, round 3).
- **What depends only on one grid cell is calculated once and saved.** The exact soil of a plant tile is read from one frame to another, the key being the cell; a kept value differs from the fresh only by the camera roundings. A jump of the camera erases it, so that a place does not depend on those seen before. An overflowing cache costs more than it makes: measure it at full load (`optimisation.md`, round 3).
- **A calculation whose inputs have not changed does not redo; its key is exactly what it reads.** The constants that its shaders read, found in their compiled code, compared to the bit close: not wider, nor approached. A value that depends only on a part of the entries is saved when that part is equal: the height of a vertex does not depend on the view, only the sorting depends on it. What sort discards becomes what it would be in the whole calculation. Checks in motion against the whole calculation, bit close (`optimisation.md`, round 4).
- **An approximate calculation for movement is compiled separately, and what places the camera remains accurate.** The exact same code, compiled with more code next to it, changes its last bits: the binary of the exact calculation remains the same as before. The ground under the camera places it; at the last bit, it moves the entire image by a fraction of a pixel and the edges of the leaves tilt. At the stop, everything becomes correct again (`optimisation.md`, round 8).
- **Cross-filtering does not replace integration along the radius.** A pixel-appropriate mip can still leave an optically thick interface between two steps; refine the density integration before masking its bands with noise or a history (`log/spike-nuages-reference.md`).
- **An isotropic multiple scattering reduces a medium that diffuses forward by similarity.** Its diffusion becomes `σs (1 − g)` (van de Hulst): taken whole, the fog returned to the orbit three to five times too much light (`spec-rendu-orbite.md`).
- **The cover says the part of the sky covered, not the water in the cloud; the water follows the regime, which the map carries.** The cloud density is divided by the cover, then follows the thickness of the map, from 20 /km for scattered cumulus and blankets to 80 /km for front hearts: everywhere at 80 /km, a blanket saturated and lost all texture (`spec-nuages.md`).
- **A cloud field has octaves at all scales that we see.** Between the tile of the noise, 32 km, and two texels of the map, 80 km, there was an octave missing: with partial coverage, the cumulus were uniformly sown. The same volume reread at 128 km gives (`spec-nuages.md`).
- **The light that a cloud sends back depends on its overall thickness and on what it receives.** His multiple scattering is set on Monte-Carlo references, seen from above and below; the sun and the sky enter together, and his samples to the sun cross the whole layer (`spec-rendu-orbite.md`, `tools/calage_orbite.py`).
- **The thickness that sets the multiple scattering is read in the cloud, smoothed at the scale of the diffusion, never along a single radius.** Along the view, a flat edge was extinguished in a circle; along the sun, a heart darkened; along the normal of a thin noise, everything turned to metal (`spec-rendu-orbite.md`).
- **What a noise does not carry under its texels remains a variance.** Its thinner octaves, extrapolated from the thinnest one it bears, broaden its edges in fringes at any distance: without them, its smooth isosurface is seen as a surface (`spec-nuages.md`).
- **A threshold on several noise functions is averaged on their attached law.** Under the pixel footprint, the covered part and density are calculated on the law of each noise, its standard deviation read by mip; taken at its average, the erosion erased any thin cloud in the distance. In the footprint, clouds are superimposed to the maximum; beyond, randomly (`spec-nuages.md`, the pixel statistic).
- **The generator paving does not draw the formations.** A field of form aiming at a distribution without preferred axes does not begin with a dominant octave reduced to a single periodic gradient; check its directions and its mips at the source (`log/spike-nuages-reference.md`).
- **The LOD of a volume averages its optical contribution.** A threshold applied to an averaged noise does not preserve coverage; the exponential of an average density does not preserve average transmittance. Statistical approximations describe their population, parameters and limits (`log/spike-nuages-reference.md`).
- **A detail level lights up as the average of what it replaces, not as a surface.** Its colors average linearly. An average normal keeps its length, the consistency of what it summarizes: renormalized, it claims to a single orientation, and the impostor lit up like a map facing the eye. Light is hopeful on this dispersion; the relay to the detail must change only the detail (`vegetation-planetaire.md`, the lighting of the impostors).
- **Average spatial quadrature of integrated rays.** Evaluate each distant sample on the same fine density field, then average premultiplied light and transmittance; specify the cost, filter support and its limits. A mix with the close rendering retains these same magnitudes (`log/spike-nuages-orbite.md`).
- **A history is reprojected in the reference frame where its content is fixed.** Clouds in the weather, that the wind turns; their shadow on the ground. A distance that it keeps is related to the current camera, otherwise each frame reprojects crooked. What it carries is re-sampled at each frame: a count or a drift averages, a minimum would erode it and a maximum would extend it in a few frames (`CloudsTemporal.hlsli`, `optimisation.md`).
- **What a history provides to another calculation, that calculation must be continuous there.** A saved value always differs a little from the fresh value; if the calculation that reads it jumps or moves its samples with it, the difference becomes plates with sharp edges, where what it describes is invisible: the distance of an almost transparent cloud cut the air of the composition in two halves (`optimisation.md`, round 1). An image guard also measures flat offsets, averaged over a few pixels.
- **A lightened trace is only valid where the image has no detail at the scale it loses.** Under the door of the distant quadrature, the clouds are larger than the pixel: a pixel between two traces is the interpolation, to one level close. Above, their grain is pixel; interpolated, it softens in plates. The regime is read on the estimator, not on the image: decided pixel by pixel, a shortcut costs the whole wave (`optimisation.md`, round 7).
- **A long calculation reserved for a few scattered pixels costs the entire pass.** Each one holds his wave, the pass waits the last one: a few dozen holes in the sky traced in the resolution of the clouds cost 3 ms. The rare case takes the value of neighbors who see the same surface; failing that, a neutral value for an image, which the parallel calculation replaces (`optimisation.md`, round 8).
- **Each correction acts on its scale and field.** A front organization is worked in the weather map; a deformation of the coordinates of the noise acts on individual clouds. Compare distribution, density recipe and filtering separately, at identical times and positions. Disabling a LOD is not a witness if the fine density has also changed (`log/spike-nuages-reference.md`).
- **A published reference distinguishes between reproduction and local selection.** Preserve the source, revisions, licenses, and parameters of noise functions; name parts not provided by the publication. Check density, transmittance and light separately before modifying a combination or generalizing it (`log/spike-nuages-reference.md`).
- **Two level constraints combine without a bend, and a recentering grid does not rotate.** A dry `max` between the level of the footprint and that of the range keeps the continuous value but breaks its slope: the place of their equality, a circle around the camera, is drawn. Similarly, a cascade recentered on new axes recuts the average of each texel at each step of the flight. The level is combined in smoothed maximum (`LevelMax`); the cascade is recentered by texels wholes of its own plane, its axes transported (the old volume, tag `piste/nuages`, `log/recherche-nuages-historique.md`).

**The shadow of the relief has a single source, for air as for the ground** (`recherche-rayons.md`, `recherche-ombres-relief.md`).
- **One single step:** towards the sun, at each vertex of the mesh, on the heights of the image. It gives the horizon, for the ground, and the shadow height, the altitude below which the column does not see the sun, for the air.
- **Nothing comes from the screen:** the mesh keeps every visible column of air, from the sea to the highest summit, and every relief whose shadow can reach it (`ShadowSweep`). An out-of-field relief casts its shadow in the field, and turning the camera does not change anything.
- **A step of the radius of view shows the illuminated part of its length,** as it shows the average of the air it passes through.

**Materials do not depend on what the mesh** (`log/spec-relief-reel.md`) is wearing.
- **Decisions are made on the ground alone** and on the entire slope of textures. Only light removes the part carried by the mesh.
- **A texture effect on a boundary is only faded with pixel size if it keeps the average,** and does not exist where materials are filtered to one cell, for object placement: `gHeightBlend`. The height, centered, moves the limit in both directions and keeps the average. The slope passes through the standard of a vector: added near the ground, it changed the snow share by several points, less on gentle slopes, more on steep ones. It no longer decides on snow.

**The relief carried by the mesh never jumps from one summit to another** (`log/spec-relief-reel.md`).
- **All that decides it is continuous, and taken at the scale of its forms:** projection triplanar to continuous weights, normal on 32 grid cells, peaks never thinner than grid cells of 2 m.
- **The copies of a tile blend without amplifying the heights.**
- **The calculations remain accurate in simple precision:** no subtraction of almost equal terms; a series where it is needed.
- **The mesh slides continuously with the camera, never by step on the grid of the planet:** placed by step, its refinement would be seen, especially in fast movement. A calculation gain is not purchased in this way (`optimisation.md`, round 4).

**No uniform stroke structure** (`spec-roche-organique.md`).
- **strata, fractures, corridors, wrinkles:** each varies along itself, at several scales, in strength, shape and continuity. A perfectly regular pattern reads like a drawing.
- **No structure stops clearly:** it thins or fades over several times its width (`spec-texturage-universel.md`).

**Every material covers every scale** (`spec-texturage-universel.md`).
- **A material is a stack of strips, from millimeter to kilometer, without holes:** a declared data, verified by a validator.
- **Every pixel of the floor belongs to a material that has its pile:** the rest of the floors including, the bare floor, which had no and went unnoticed of benchmarks.
- **Every strip is erased by the same rule,** according to its wavelength and pixel size, regardless of its source: noise, tile or photo.
- **The bands extend the slope of the photo:** above its tile, each octave carries the slope by octave of the photo, the one that the distant rule already counts (`STONE_SLOPE_SIGMA`). Lower, they leave each wall in carpet equal to his photo.
- **A photo keeps the orientation of its shooting:** a wall photo goes on the slopes of more than 45°, a photo taken from above on the softest ones. The limit follows the universal rule and the noise limits, like that of the rock. A material that has only one photo keeps it everywhere.
- **A correction is accepted by the quality benchmark,** on randomly drawn locations, not on the only reported view.

**An optical effect moves light, it does not create light** (`recherche-halo.md`).
- **On the linear image, before the tone curve, without threshold:** the total light of the image does not change.
- **Strength is measured:** The halo follows the spread of a real target, not a taste.
- **Nothing that the viewer's eye already adds:** in front of the screen, its own halo covers everything that the screen shows.
**Sea: one slope variation, shown or lost** (`recherche-mer.md`).
- **The slope of the sea always has the Cox and Munk variance,** of the orbit at the level of the water: what the pixel shows of waves, each its average on the pixel, plus what it loses, which broadens the reflection. The reflection keeps its width and its medium light at any height.
- **The whitecapss that the pixel does not show are their share of the pixel,** that of Monahan; close up, their pattern keeps this average.
- **The wind is a map of the climate,** and everything that comes from it: slopes, waves, whitecaps.
- **One single function for reflecting water,** sea like wet sand: `ReflectOnWater` (`Sea.hlsli`).
- **Visual validation is not equal to physical calibration:** deviations of the FFT kernel to these laws remain declared in `spec-mer-fft-spike.md`, even after its integration.

**What moves by itself** (`recherche-mer.md`).
- **Time is a parameter of the frame:** the clock in flight, 1/60 s per frame in capture, so that the benchmarks repeat; `MYPLANETENGINE_TIME` fixes it.
- **A surface that moves by itself shows its average at each frame, without temporal smoothing of its light:** its past is elsewhere; kept, it spread the movement of the waves. The physical history of the foam remains in its simulation maps.
- **An animated pattern can follow the camera, if it never jumps:** the wave plane is carried by the camera without turning, its origin keeps the path traveled in double precision precision. A point of the sea keeps its waves, to a few millimeters per kilometer traveled. It is the exception to the grid of the planet, for a pattern that moves anyway.
- **Normal and foam are derived from the actual displaced surface:** a phase mask is not sufficient. Displacement, slope and compression share their source; see `spec-mer-fft-spike.md`.

**The screen shows the light, not the framing** (`recherche-tons-exposition.md`).
- **The exposure follows the light that falls, never the image:** the one that receives, under the camera, a map facing the sun. Turning the camera does not change anything; snow remains white, a forest remains dark.
- **One curve, on the strongest channel:** the shades do not turn. Clarity is regulated by exposure, before it, never by a gamma after.
**An object has a fixed place on the planet** (`spec-objets-proximite.md`).
- **An object is the detail of the ground, laid:** a pebble, a tuft. The bedrock and its relief are geometry.
- **His recipe is that of his soil,** based on photos taken standing, counted: the published law serves as a safeguard. A debris-clean field first decides if there is any debris.
- **Everything that does comes from its cell of the planet grid:** place, size, shape, density. Never mesh slipping, never anchor.
- **It obeys gravity, soil shape and measured laws:** nothing beyond the angle of rest; blocks accumulate at the foot of the real walls, leave the ridges; by spots; the sizes of real stone fields.
- **The camera only decides if it is visible,** by its size on the screen and the thinness of the mesh under it; it comes out of the ground, without pop.
- **His foot is on the exact ground,** buried according to the ground, always more than the measured deviation to the ground that draws the mesh.

**Vegetation follows the climate by published laws** (`recherche-vegetation.md`).
- **The diversity of appearance takes over the fields of the population:** cold, aridity and exposure decide the families, with continuous mixtures at the borders. The seed chooses the shape; changing the pattern does not move the plant and create a new one (`arbustes-climatiques.md`).
- **A simplified representation is judged against its own detailed model,** with the same trees, poses, sizes and light (`log/prototype-vegetation-volumique.md`). Cover and holes count as much as silhouettes; opacity thresholds common to all trees should not correlate their holes.
- **One source for what grows,** `Vegetation.hlsli`: nearby plants and the distant canopy read it both.
- **Changing the representation does not change the identity of the plant:** the mesh and its proxy take over the same instance; the removal of canopy uses exactly its screen presence rule (`vegetation-planetaire.md`).
- **Filtering a cut image retains its coverage:** color in linear light and alpha weighted values for mipmaps. impostors remain premultiplied until filtering; cut textures of meshes have dilated edges and mipmaps are set to their alpha threshold (`vegetation-planetaire.md`).
- **Superimposed coverings are composed by their transmission:** trees and shrubs can occupy the same ground; their union is `1 − (1 − arbres) × (1 − arbustes)`. Their addition can exceed 100 % and produce negative light.
- **The occlusion of the foliage filters the light that comes in:** sky and sun have their own visibilities; neither the albedo nor the exposure are used to paint the shadows (`vegetation-planetaire.md`).
- **An optional GPU resource keeps a valid access range:** a branch can be flattened by the compiler. A SRV root without limits receives neutral data covering all possible clues, even when the effect is disabled.
- **A GPU limit never chooses objects in order of arrival:** the bounded selection follows a deterministic order; compaction and transition between representations must not vary the population with a still camera (`vegetation-planetaire.md`).
- **An occlusion rejection must cover the entire envelope actually drawn:** a depth of the current image, a conservative limit and a visible fold for any uncertain case. Source lists and drawing order are retained (`vegetation-hiz.md`).
- **A computation shift is validated by the GPU time, not by the number of instructions:** Work added to the vertex, transmitted data and commands can cancel pixel saving. Compare on the same poses, with the same population and without competing load (`optimisation-vegetation.md`).
- **Each limit is a measured law:** the growing season for cold, aridity, the Sankaran ceiling and Hirota modes for water; its thresholds are widened by the universal rule.
- **Where are the plants, a single rule with two scales, like the pebbles** (`Presence`): a field of noise above the threshold that leaves each state its share. The field of regions leaves entire regions without trees, whatever the soil; the field of spots opens clearings in any forest and arranges shrubs in thickets. Two independent fields: the product keeps the average.
- **The ridges lose their trees, the hollows keep them:** the height of the ground on the regional soil cools the season and lowers the fields of the woods. Never a rule specific to a mountain.
- **A distant plant stands on the drawn ground, a near one on the exact ground:** in the distance, it follows the ground that we see; its foot slides towards the exact ground while its shape refines. Never a plant floating above the mesh.
- **A plant never grows:** whole or absent, at its own threshold of the fade; its coarse form covers the screen as the fine. The forest it replaces has already its height: the distant canopy stands at the height of its trees, the ray of view crosses their crowns before the ground.
- **What replaces an object in the distance has its height, space and light,** measured on the object (benchmarks `relais`, `mouvement`).
- **A forest from far is the canopy of the ground, not millions of trees:** its share, its color, the relief of its crowns, the shadow it casts.
- **What the objects draw is removed in boolean layer:** 1 − (1 − cover)^ (1 − drawn part). Removed in simple subtraction, the forest lost 8 points where trees are born.
- **What the light sees under a cover is true for everything there:** the ground, the pebbles, the tufts, the bottom of the plants.

## The benchmarks, to check a rule

- **`tools/banc_qualite.py`:** the appearance on places drawn by material, from 12 m to 3 km: blur, scale holes, repetition, straight bands, mutation when the mesh is refined. Its reference: `tools/banc_qualite_reference.json`.
- **`tools/banc_descente.py`:** the viewed share of each material on a single square of soil, from 1 500 km to 100 m, with the diagnostic views `MYPLANETENGINE_VIEW`. A flat curve is a coherent planet.
- **`tools/banc_tremblement.py`:** the flicker at an exact position, copied from the title bar.
- **`tools/banc_halo.py`:** the halo around the sun and snow, in linear light, against the law in 1/θ².
- **`tools/banc_tons.py`:** the luminance of the ground and sky against the photos; the exposure in descent and when the camera turns.
- **`tools/banc_ombres.py`:** direct sunlight on a single ground, from 50 km to 200 m, at low sun. Its average must not move: on a rough soil, it is that of its average surface, regardless of the relief drawn. The shadow part, it, grows with him.
- **`tools/banc_carte.py`:** the map of the planet checked against the port numpy of the relief and against a separate written fill; its lakes and network measured against the Earth.
- **`tools/banc_mer.py`:** the reflection of the sun against Cox and Munk, pixel by pixel, windward of the pixel; downhill, the average reflection and the share of whitecaps against Monahan; the wind map. **`tools/banc_tremblement_mer.py`:** the flicker out of the sea when it moves, and the sea movement with or without smoothing.
- **`tools/banc_cretes.py`, `tools/banc_visuel.py`, `tools/realisme.py`:** peaks, views at multiple heights, distance to actual scans.
- **`tools/banc_objets.py`:** objects per ground in the counted photos, the distance between their foot and the mesh's ground along an approach, the rises along a descent, and the man-height views next to the photos.
- **`tools/banc_vegetation.py` :** biome cover, tree line, light connection between plants and the canopy, the orbit light view, the test views. With `banc_descente.py` and `forest` view: the share of forest per pixel, from 20 km to the ground.
- **The benchmarks render without window** and do not take the user's focus.
