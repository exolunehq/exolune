# Geometry: relief and its overlays

Status: reference, since 2026-10-23. Complete `principes.md`, which refers to it.

## The rule

**The Exolune tectonic relief is the source of geometry truth,** since the 2026-10-31 (`spec-relief-tectonique.md`).

- **The large shapes, above 50 km, come from the tectonic map:** continents, margins, pits, chains, plateaus, rifts and ridges, narrow seas, calculated at startup (`Tectonics.cpp`), read in B-spline and put in profiles (`Tectonics.hlsli`, `Relief.hlsli`).
- **The coasts, from 60 to 3 km, are divided by type of margin,** a noise that moves the shore by a given distance: capes, bays, islands and rias on the steep coasts, cordons and lagoons on the flats.
- **The detail, under 50 km, comes from the noise of `Noise.hlsli`,** modulated by the geology of the map; the wider octave of the strings in folds along them.
- **From the original code,** written in the clean room since `recherche-relief.md`.
- **Before:** from 2026-10-20 to 2026-10-30, the port of the libnoise complexplanet example, commit `b7b8c76` and following; the 2026-10-31, an original rewrite of its composition, commit `f00004d`. There is nothing left of it.

- **The appearance of materials is worked in the rendering:** colors, textures, pixel normals, parallax, shadows. A desert that looks like a desert, a rock that looks like rock, it is first of all a rendering work.
- **Any geometry modification is an overlay,** listed in the table below before being merged.
- **Each overlay gives:** its family, wavelengths, amplitude, where it acts, its stop setting and spec.

**The three families of topcoats:**
1. **Filtering:** the same composition, from which we remove or round up what the grid cell cannot carry. The shape remains that of the relief on the scale of the grid cell.
2. **Add detail:** wavelengths that the relief does not have, under its finest octave, 13,5 m. Above, the form remains its own.
3. **Replacement:** the shape changes at scales that the relief already decides. We move away from the original composition.

**A replacement is a separate subject:**
- a dedicated spec and an explicit decision;
- a branch and a tag `piste/…` until it is decided;
- a setting that brings it back to 0.

## The superlayers

| Surcouche | Family | Scale | Amplitude | Where | Arrêt | Status |
|---|---|---|---|---|---|---|
| Octaves filtered by grid cell | Filtering | under 2 grid cells, `MESH_BAND_LIMIT`  | octave replaced by its average | everywhere | none, it's sampling | in place |
| Maximum frequencies of terrain type and turbulence | Filtering | between ~100 km and ~6 km | 0,13/255 on screen; ribs of a few meters | everywhere |  `NO_LIMIT`  | removed the 2026-10-31 with the old relief |
| Rounded crests | Filtering | 2 grid cells, never under grid cells of 2 m | hollows and ridges of the billow and ridged multifractal, and chains of tectonic relief | everywhere |  `CREASE_ROUNDING` = 0 | in place |
| Expanded profiles | Filtering | 2 grid cells | pits, axial valleys, grabens, hollows of the transformants, cordons of the flat coasts: wider, shallower or less high, their average kept | everywhere | none, it's sampling | in place since the 2026-10-31 |
| Profiles crossing the sea | Filtering | part emerged on at least 2 grid cells, or completely drowned | including cords, spikes and overflows: core flattened, amplitude reduced, profile area retained; resolved profile unchanged | flat ribs; no distinct profile of arrow, plate or motu on this branch | grid cell null: original profile | 2026-10-31, `ReliefSeaProfile`, `spec-relief-tectonique.md` ; to be judged in flight |
| Relief of materials | Adding detail, which overflows | from the centimeter to the tile of 64 m | centimeters to a few meters; tile cornices from 64 m above 13,5 m | grid cells from 8 m and less |  `MATERIAL_RELIEF`, withdrawn | disabled the 2026-10-23, removed from code the 2026-10-30; tag `piste/parois-gradins`, where it is active; `log/spec-relief-reel.md`  |
| Walls and steps | Replacement | beds from 10 to 60 | up to two thirds of the thickness of a bed, i.e. 10 to 40 m | Steep slopes, grid cells of 16 m and less |  `WALL_RELIEF`, withdrawn | disabled the 2026-10-23, removed from code the 2026-10-30; tag `piste/parois-gradins` ; `log/spec-parois.md`  |
| Erosion filter | Replacement | ravines from 366 m to 11 m | tens of meters | all slopes, grid cells of 91 m and less |  `EROSION` = 0 | set aside, tag `piste/erosion-filtre`  |
| Real relief patches | Replacement | 1 to 200 m | of the actual place | Non-integrated | — | dalles IGN LiDAR HD dans `../donnees-terre/lidar-hd`, off-engine test not completed |
| Objects of proximity | Added detail, detail of laid floor, pebbles and tufts, never the bedrock | 3 cm to 2 m | buried from 8 % on rock to 40 % in loose soil; soil does not move | in rocky regions only, a recipe per soil: sand and bare soil, grass, scree, foot of real walls; by spots and by clusters, at the angle of repose; under 6 pixels or in grid cells more 1,5 times their width, nothing |  `PEBBLES`, `GRASS_ROCKS`, `DEBRIS_ABUNDANCE`, `TUFT_COVER` to 0 | experiment, tag `piste/objets-proximite`, `spec-objets-proximite.md`  |
| Plants | Adding detail, objects placed: trees and shrubs, never a form of relief | 0,5 to 64 m high | the ground does not move; the trunk buried at 15 % of the height; in the distance, the foot on the ground of the mesh, close on the exact ground; whole or absent, never growing | according to the climate, by regions and by spots, rare on the ridges; neither on the bare rock, nor on the scree, nor on the beach; under 5 to 8 pixels, the canopy in the soil material, at the height of trees, without moving a summit |  `MYPLANETENGINE_NO_PLANTS`, or no catalog | in place: the population of `piste/vegetation-v3`, drawn by planetary vegetation; plants generated v1 to v3 removed from code the 2026-10-30, tags `piste/vegetation`, `-v2` and `-v3` ; `recherche-vegetation.md`  |
| Prototype of detailed vegetation | Add detail, objects placed; representation by mesh, impostors or volumes | trees of 12 m in a bounded comparison plot; volumes of 32³ to 128³ | the ground does not move ; the feet follow the drawn mesh | deterministic plot attached to a planetary anchor; same poses in the three modes |  `MYPLANETENGINE_FOLIAGE`, withdrawn | prototype isolated, closed; removed from code the 2026-10-30, tag `jalon/24-vegetation-detaillee-main` ; `log/prototype-vegetation-volumique.md`  |
| Detailed planetary vegetation | Added detail, pose objects; mesh near and impostor far | height and width of the instances of the existing population; impostors multiviews, rectangles projected on their support | terrain does not change; extension of the lower trunk near under the foot | Same grid, climate and seeds; shrubs preserved |  `MYPLANETENGINE_NO_PLANTS`, or no catalog | in place, `jalon/24-vegetation-detaillee-main` and `jalon/25-vegetation-performance-main` ; the volume 64³ distant and other modes removed from the code the 2026-10-30, tag `piste/vegetation-relais-fondu` ; `vegetation-planetaire.md`  |
| Volcanoes | Replacement, on a experiment: shapes that the relief did not have, from 120 km to the cones of 0,5 km | arcs, hotspot chains, rifts; stratovolcanoes of 2 to 5 km, shields of 4 to 9 km above the bottom, guyots, atolls, calderas, flows of 15 to 40 m, cones of 60 to 190 m; swell of plumes, traps and oceanic plateaus in the map | around volcanoes listed at start, 0,5 to 0,6 % of surface; any profile on at least two grid cells | no adjustment: no volcanism, commit `d304da0` of `bruit-propre`  | 2026-10-31, branch `claude/volcanisme-7c3aea`, tag `piste/volcanisme`, to be judged in flight; `spec-volcanisme.md`  |
| Tectonic relief | Replacement, decided: it's the relief | forms of more than 40 km, two texels of the tectonic map; the coasts of 60 to 3 km; the noise below | continents, plateaus, chains from 6,9 to 7,6 km, pits from −9,1 to −10,1 km, abysses to −4,5 km; coasts displaced from 8 to 12 km | everywhere | none: the old relief is at commit `f00004d`  | stages 1 to 3 of the 2026-10-31, defects corrected on the same day: coasts by margin type, emerging rifts and narrow seas, chain folds in two sets that alternate; their rise and their folds read in double precision, without walls on the ground, the rise in quintic; the more offset detail along the transformants, the cords along the smoothed shore, in arcs between passes; branch `bruit-propre`, to be judged in flight; `spec-relief-tectonique.md`  |

**Validated planetary models of the 2026-10-27:** added detail to the placed objects, milestone `jalon/24-vegetation-detaillee-main`. Hardwood Rakshi Games enriched to 7 010 triangles, pine evolveduk to 5 627 triangles, twelve climatic shrubs to 2 492–4 272 triangles. Leaves cut around mesh branches; normal by bouquets and visibilities pre-calculated without displacement of the tops. Instances and scope retained; `vegetation-planetaire.md`.

**Climate shrubs:** six families of two branched forms; same seeds and positions, reference crown preserved, height of silhouette adapted to the climate. The terrain does not change. The height diagnosis takes the average of the families; the distant cover remains superficial, without precise vertical parallax. `arbustes-climatiques.md`. Previous models and their tests remain described in `log/vegetation-planetaire-historique.md`.

**Water surface of spike FFT:** specific overlay, four cascades, amplitude of spectrum JONSWAP and swell; peaks under the sea, dampened by depth and filtered by the grid cell. The relief background is preserved. Displacement and normal share their derivatives; see [spec-mer-fft-spike.md](spec-mer-fft-spike.md). The first kernel remains in mer-animee.

**Are not top layers:**
- **The fine grid:** the same function, sampled four times finer, for normal pixels.
- **The grid of the noise in pairs of floats, in flight:** the same function; the splitting of each octave on the grid into two floats, 48 bits, instead of a double, on the vertices that slide (`Noise.hlsli`, `optimisation.md`, round 8). The point is the same at 2·10⁻⁸ m; only the last bit of a height can change. The vertex under the camera remains in double precision; at a standstill, all the mesh also.
- **The planet map:** the same function on a cube fixed on the planet, 6 × 1 024², calculated at startup after the tectonic map (`PlanetMap.hlsli`). Data for mist and water: it does not move any vertices.
- **The tectonic map:** it is part of the relief, it is not a superlayer.
- **Parallax:** an illusion in pixels, without changing geometry.
- **The fine grain of pixels:** the octaves of relief that the grid cell does not bear, drawn in the light.

## The geometry track, apart

Opened the 2026-10-23, to resume after rendering. **The proximity geometry is waiting there:** the relief of materials and grades, disabled the 2026-10-23, are removed from the code the 2026-10-30; tag `piste/parois-gradins`. The rendering of the relief first goes as close as possible to photorealism. It appeared in the last meters, a sign that it is not yet well integrated into the generation by noise functions. The question: how to refine the relief under its scales, and by what? It landed then on complexplanet; it now lands on the tectonic relief.
- **noise functions or algorithms:** the erosion filter, `spec-parois-minerales.md`.
- **Real relief:** lidar patches melted by our noise functions.
- **Objects:** rocks sown in real volumes, `log/spec-parois.md`, option 3. Open the 2026-10-24 for stones and blocks: `spec-objets-proximite.md`.

**2026-11-01 · Manufactured ship geometry**

- **Classification:** added detail on a manufactured asset, outside the terrain-overlay system.
- **Scope:** fitted console panels, curved console returns, integrated dashboard recesses, curved coaming, rolled foredeck, glazing retainer, seat upholstery, service fittings and identification plates.
- **Scale:** 1.5 mm recessed instrument faces, 10–28 mm pockets, a 34 × 12 mm glazing retainer and 4 mm seal.
- **Panel outlines:** seven custom skins follow their support contours with 7–12 mm margins and chamfered corners.
- **Dashboard curve:** the centre stays at 0.845 m; the shoulders lower by 35 mm along the dashboard plane.
- **Console junction:** a 65 mm lateral return meets the dashboard and the flat console bay at d = 3.84 m with tangent cubic sections.
- **Foredeck:** shoulder relief rises smoothly to at most 220 mm and fades before d = 3.8 m; the forward centreline lowers by at most 18 mm, fading before d = 2 m.
- **Sightline:** five eye positions cover the nominal eye, ±30 mm sideways and ±60 mm fore/aft; the camera settings are unchanged.
- **Attached details:** hull paint is regenerated from the new sections; the top and side forward attitude jets follow the revised skin.
- **Glass:** unchanged analytic shape, tessellated at 64 × 52 for the thinner retainer.
- **Reference frame:** the ship; no change to Exolune relief, planetary meshes or terrain settings.
- **Source:** `assets/vaisseau/chasseur/forme_chasseur.py`, `cockpit_chasseur.py`, `panneaux_cockpit.py`, `encastrements.py`, `cadre_verriere.py` and `finitions_cockpit.py`.
- **Selection:** the accepted fighter is the default; `-ModeleVaisseau classique` restores the original triangular asset and its geometry profile.
- **Milestone:** `jalon/2026-11-01-chasseur-par-defaut`; approved asset source: `b43d8ee`.
- **Specification:** [ship assembly](spec-vaisseau.md).
