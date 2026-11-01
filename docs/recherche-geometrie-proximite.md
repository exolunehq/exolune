# Search: proximity geometry, cornices and relief by the meter

Status: search for the 2026-10-24; state of the art and plan, nothing decided. Prepares a spec. Following on from `log/spec-relief-reel.md`, `log/spec-parois.md` and `log/spec-parallaxe.md`. The geometry remains at complexplanet (`geometrie.md`): what is proposed here is an addition of detail, under 13,5 m.

## 1. The conclusion and the plan

**In brief:**
- **A relief can only happen without being seen if it happens small on the screen.** Engines that add relief without jumping make it come into being at a few pixels: constant width triangles on the screen in Battlefield 3, pixel-fixed cut-outs in Nanite.
- **In our case, it is born at 56 to 100 pixels.** The mesh bears a shape only from 8 to grid cells, and a grid cell bears 7 to 13 pixels. Hence the cornice that arises in the last meters.
- **Our mesh cannot wear it earlier:** its tops slide, and a relief shorter than 8 grid cells shakes (measured, `log/spec-relief-reel.md`).
- **The recommended way: amplify the nearby grid cells.** Each nearby grid cell is re-cut into 8 × 8, in constant numbers. Only the cheap detail is evaluated there; complexplanet is not evaluated either. The relief is born at 8 under-grid cells, or 7 to 13 pixels.
- **The shape first:** a cornice is not a level line. It is a hard bed that advances above a soft bed dug, uneven along itself, cut by diaclases and ravines, buried under its scree. The section 4 gives the field, linked to the stratigraphic column.
- **Overlay family:** detail addition, the beds from 1 to 13 m, of zero average. The seats of the formations of 20 to 60 m remain a replacement, on `piste/parois-gradins`.

**Dismissed:**
- **The fixed-vertices quadtree, CDLOD:** stable, but variable cost; POC closed, 34 % of snapshots.
- **Competing binary trees, CBT:** a state kept from one frame to another, contrary to integral calculation at each frame.
- **Parallax only:** no silhouette, 0,8 to 1 ms.
- **The cornices drawn in light alone:** the felt effect.

**The plan, by stages:**
1. **The benchmark arrival, without touching the rendering.**
   - The same view, fixed camera, rendered with a mesh increasingly thin: `MYPLANETENGINE_FACE_FACTOR` from 2 to 0,125, by octaves, 33 rendered in a `MYPLANETENGINE_BATCH` launch.
   - Measurements: the change from one rendering to the next, its peak and its total, on six walls.
   - Witnesses: the build of the tag `piste/parois-gradins`, where relief of materials and grades were active and appeared; and the last tag that keeps them in the code, `jalon/28-vaisseau-habitacle`, with `MATERIAL_RELIEF` = 1 and `WALL_RELIEF` = 1; they are removed since the 2026-10-30. The benchmark must detect them clearly; otherwise it is not sensitive enough.
   - Done when: the today's reference and the two witnesses are encrypted, and the thresholds of the section 5 set. A Python script, no engine changes.
2. **The cornice field, for diagnosis.**
   - `MYPLANETENGINE_VIEW` = `ledge`: the retreat in gray, without geometry.
   - Judged by the photos `cible-*.jpg` and measured by the right segments of the quality benchmark.
   - Done when: no cornice crosses a wall of a line, and the user validates the shapes.
3. **The grid cells amplified, without relief.**
   - An instanced draw of a grid of 9 × 9 vertices by grid cell near, calculated in the vertex shader, on the current triangle. Nothing in memory.
   - A fixed range of grid cells around the nadir, the face and the first rings: a constant cost. The mesh slider no longer draws these grid cellss.
   - At the edge of the beach, the relief is extinguished and the sub-summits remain on the ridge of the neighboring grid cell: no slit.
   - Two cost settings: the range width, and the cut, 8 × 8 or 4 × 4. All the face in 8 × 8 would make 3 millions of vertices.
   - Made when: image identical to 1/255 near, cost measured at 3, 30 and 300 m.
4. **The vertical relief of the cornices** in the amplified grid cells, filtered to 8 sub-grid cells; light carries the rest, as did `Texture.carried` of the relief of the materials, removed.
   - Entered in `geometrie.md`; shut down by a setting, `CORNICE_RELIEF` = 0; camera floor raised from maximum amplitude.
   - Arrival, jitter, Quality and Downhill benchmarks.
5. **Retreat along the wall and overhangs:** the movement follows the smoothed normal of the wall, and extinguishes where it would fold the surface.
6. **The shadows:** contact shadows on the screen under the lips; from afar, the average darkening of the hollows, taken from the same field.
7. **Only if the jitter exceeds the criteria:** a proximity grid fixed on the planet, in nested and blended rings, in the manner of geometry clipmaps. The detail is captured in fixed points and does not shake at all.

## 2. Why our trials failed

**Three distinct problems, mixed in each test:** shape, filtering and arrival with stability. The plan separates them and measures each.

### The relief of materials in the mesh, disabled the 2026-10-23, removed the 2026-10-30

- **He was shaking.** A relief taken at the sliding vertices is re-sampled at each frame. The triangle error is about 5·A/n² for a wave of n grid cells (`log/pistes-glissement.md`).
  - Filtered to 2 grid cells: 0,17 with smoothing, against 0,04 without relief.
  - Filtered to 8 grid cells: 0,06. Again +50 %.
- **Non-linear decisions taken by vertex** made the relief jump from one neighbor to another: mixing by height, projection to the power 8, snow decided on the relief. Hence blades and needles.
- **He was coming up.** Filtered to 8 grid cells, it only carries the waves of more than 8 grid cells.
  - On the face, a grid cell is equal to altitude / 48; the shortest wave-bearing, altitude / 6.
  - A shape of 2 m wavelength is therefore born towards 12 m altitude: this is the cornice seen from 11 to 5 m.
  - On the screen, 8 grid cells make 56 to 100 pixels. It comes big.
- **The state of the art is the opposite:** CDLOD, clipmaps and Nanite take the detail in fixed points of the terrain, and make it come to a few pixels.

### The walls in steps, disabled on 2026-10-23, removed on 2026-10-30

- **The gradient is a non-linear function of `s`,** the altitude minus the offset of strata. Taken on the altitude interpolated between summits that slide, it amplifies their error of the slope of the cliff, three times that of the wall.
  - Net stands: 2,5 times more than jitter. Rounded on 16 grid cells: almost invisible.
- **A wall has only two or three vertices in height:** horizontal displacement in Outerra's way folded the surface, into black holes and saw tooth.
- **The noise of the ravines stretched from the anchor** (`WallRelief`), which jumps from 64 m: the pattern was re-cut in flight. `principes.md` keeps the rule.
- **The scale:** from beds of 10 to 60 m, above 13,5 m. This is a replacement for complexplanet, not an addition of detail.

### The cornices in the light, removed the 2026-10-24

- **Shape:** a `s` function alone draws level lines. Each counterstep becomes a stroke on the whole face, of equal strength. This is the rule "no structure of a uniform stroke" broken.
- **Filtering:** a counterstep thinner than the pixel, drawn in normal, gives a constant stroke width to the screen, at any distance: the felt.
  - From afar, a walk should not be seen as a line but as a statistic: average slope, roughness, shaded part. This is the principle of LEAN and LEADR, which filter relief into light without losing it.
- **Erasing by pixel size:** steps were erased according to `ds`, the step of `s` from one pixel to the next. They appeared and disappeared with distance, against the rule "a noise never fades according to the size of the pixel".
- **The parallax was the right transition technique:** the cornice had its depth as early as 11 m. But it cost 0,8 to 1 ms and drew the same bad shape.

### Our concept has a name in literature

- **Persistent grid mapping,** Livny et al. 2008: a grid attached to the camera, projected on the ground, moved in height by the ground. It's our slippery slope.
- **Its known defect:** the tops slide, tops and crests sparkle.
- **The remedies published,** Houska 2020: spread the vertexes to choose the right level of filtering, look for edges near the camera, consistency from one frame to another. They reduce the defect without removing it.
- **Our own calculation confirmed this:** no reconstruction stabilizes the waves from 2 to 3 grid cells; only filtering removes them.

## 3. Comparative techniques

### Continuity of level of detail

- **CDLOD,** Strugar 2010.
  - A quadtree of fixed grids. Each vertex blends into the coarser level on the last 15 to 30 % of its range, according to its own distance.
  - The relief is read in fixed points: no slipping.
  - Our POC, `piste/sommets-fixes-etape3`: no slit or seam, but variable cost, calculation 4 to 5 times more expensive near the ground, 34 % of images at-shocks.
- **Geometry clipmaps,** Losasso and Hoppe 2004; on GPU, Asirvatham and Hoppe 2005.
  - Nested grids of fixed size, centered on the observer, each set on its own pitch.
  - A transition strip at the edge of each layer blends the geometry to the coarser layer.
  - Constant cost per construction.
  - Close to the ground, Losasso and Hoppe synthesize the finer levels by a noise fractal: it is exactly an addition of detail.
  - Our test “by notches” caled the whole face by steps, without fade: the steps were visible.
- **Hardware tessellation.**
  - Battlefield 3: moving through the height field in DX11; the factor keeps a constant triangle width on the screen.
  - Ghost of Tsushima: dynamic terrain tessellation; the rocks of the cliffs are models in their own right. Ghost of Yōtei: a terrain tessellation system, for detail and deformable snow.
  - The known trap: a fractional factor slides the new vertices, and the displacement amplifies this slip. An entire factor blows up. Remedies: fixed factors or vertices blending, filtered movement at the cut step.
- **Far Cry 5:** a GPU pipeline for detail selection, sorting, and height field sewing, which hosts generated cliffs and moving geometry. The cliffs come from Houdini tools. Details are not public.
- **Nanite tessellation,** Unreal 5.4; Karis, “Nanite + Reyes”, 2026.
  - Patches are cut down to one pixel step; the displacement is evaluated at each cut vertices.
  - The error measurement of the detail choice ignores displacement; it is scalar, bounded by a given range.
  - The straight discontinuities stretch the triangles beyond 64 pixels and tear the surface.
  - Nothing published on temporal stability.
- **Virtual Heightfield Mesh,** Unreal: a quadtree read in a virtual height texture, with a target size on the screen. Experimental, made for pre-calculated data.
- **Competing binary trees,** Dupuy et al. 2020; Benyoub and Dupuy 2024; Unity 2021.
  - An adaptive bisection on GPU, cut according to the length of the edges on the screen. Update in less than 0,1 ms; planetary scale, double precision.
  - Unity: 256 triangles per sheet, triangles up to 1,5 cm, micro-displacement of materials.
  - Only one cut level per frame: the tree is kept from one frame to the next. Jumps are not processed.
- **Mesh shaders,** DirectX 12: triangle groups generated on the GPU without stored buffer. Another way to amplify the grid cells nearby; assumes a GPU DirectX 12 Ultimate.
- **Star Citizen:** parallax on the ground, objects fade into the ground by depth, detail set in polygons per pixel. Rocks and cliffs are placed objects.
- **Outerra:** a horizontal fractal shift on the slopes, depending on the filtered slope, from 19 to 76 m. The author writes that he does not yet make real cliff walls or canyon.

| Technical | Birth of the retail | Stability | Cost | With our sliding face |
|---|---|---|---|---|
| CDLOD | Continuous melting by vertex | fixed points | variable with the number of tiles | POC closed: at-shocks |
| Geometry clipmaps | faded in one band per level | fixed points | constant | possible in proximity layer; sewing to be done |
| Hardware tessellation | continuous or melted factor | slide if fractional | moderate | possible, fixed factor near camera |
| Nanite tessellation | pixel pitch cut | Not published | high, GPU | the idea alone: cut to pixel, move cheap |
| Concurrent binary trees | pixel cut-out, one level per frame | fixed points, unprocessed jumps | < 0,1 ms update time | maintained: contrary to concept |
| grid cells amplified, proposed | 8 sub-grid cells, 7 to 13 px | slides with base, filtered | constant | direct: a grid by grid cell |
| Fixed proximity grid, folding | faded by distance | fixed points | constant | sewing with sliding mesh |

### Vertical or vector movement

- **A height field does not have a overhang.** On a slope wall m, a horizontal retreat r is equivalent to a height r·m: a hard bed can advance, but not overhang. Our stands did so.
- **The movement along a smoothed normal,** on 32 grid cells at least as `RELIEF_NORMAL_CELLS` of the relief of materials, removed, makes overhangs with respect to the vertical, without folding:
  - as long as the recoil remains below the radius of curvature of the smoothed surface;
  - and as long as the wall has enough vertices in height. The current mesh has only two or three; amplified 8 times, it has 16 to 24.
  - It extinguishes at the edges between wall and plateau, where the curvature is strong.
- **The displacement triplanar,** Weiss et al. 2020: Extruded geometry along steep slopes by tessellation, including overhangs and blocks, without explicit triangulation.
- **Inclusive games pose items:** Ghost of Tsushima Cliff Rocks, Far Cry 5 Procedural Cliffs, Horizon Zero Dawn GPU Placement. This is our option of the sown rocks, `log/spec-parois.md`, to keep for later.
- **Offline tools:** Gaea's `Stratify` breaks the strata into independent plates, not terraces.
- **The materials remain decided on the field only** (`principes.md`), never on the share carried by the mesh.

## 4. Natural cornices

### What geomorphology says

- **The hard beds hold on cliffs, the soft beds on slopes.** Sandstones and limestones make the cliffs; clays, slopes (NPS, Grand Canyon).
- **The soft digs under the hard:** it retreats faster and undermines the benchmark above. The lip advances overhanging, then falls by blocks bounded by diaclases (Wingate sandstone).
- **A hard bed cliff retreats at the pace of its soft base,** and its debris reinforces the slope below (Ward and Anderson; Howard).
- **At the foot, the scree:** a slope at the angle of scree, 34° at our place, the `WALL_REPOSE` of the withdrawn stands. It buries the bottom of the wall and its cornices.
- **Along itself, a cornice varies:**
  - its advance follows the thickness of the hard bed and the contrast of hardness, which change: the lenses;
  - the ravines cut it in a V;
  - the diaclases cut it into blocks, some of which are missing, with their scar;
  - The replants carry debris and vegetation.

### Procedural approaches

- **Paris et al. 2019:** a rock resistance ρ(p) function of altitude, therefore in strata, deformed by folds and faults. Erosion removes from the surface `f_D·(1 − ρ)`: soft rock retreats, hard rock advances. Hence layered cliffs and overhangs. Offline, about one million requests per second.
- **Paris et al. 2020:** implicitly block walls bounded by fractures.
- **Peytavie et al. 2009:** piles of stones, therefore scree, by periodic paving.
- **Cordonnier et al. 2018:** deep layers raised and eroded; strata pleated on the cliffs.
- **Jones et al. 2010:** alteration by curvature: alveoli in the hollows, rounded bumps.

### Our cornice field

**A backlash R(p), along the smoothed normal of the wall,** fixed on the planet grid, never relative to the anchor.

- **The stratum:** `s` = smoothed altitude − `StrataShift`, like the colors. Smoothed on some grid cells, like the height of the stands, not to amplify the jitter of the base.
- **Hardness ρ(s):** the hard and soft beds of the column, those of `PlaneDrop`. So the cornices fall on the color strips.
- **The profile of a benchmark:**
  - the hard one advances in almost vertical face, its lip rounded on 10 to 50 cm;
  - tender retreats into concave hollow, the deepest in the upper third, under the lip;
  - zero average on each benchmark: the average wall remains that of complexplanet, and the relief keeps its average height.
- **The presence along the wall,** a factor w(p) between 0 and 1, product of:
  - the lenses, `BedLenses`, already in place;
  - a noise along the layers, from 8 to 64 m: the strong cornice here, erased there;
  - blocks of diaclases, a Voronoi in the wall plane, from 2 to 8 m: some fallen blocks;
  - ravines: vertical stripes where w falls to 0, in V;
  - the burial under the scree, at the foot of the wall.
- **Amplitude:** a portion of the thickness of the hard bed, 0,2 to 0,4, capped at 2 or 3 m. Zero on slopes softer than the angle of scree.
- **The scale:** the beds from 1 to 13 m. The formations of 20 to 60 m remain color, or replacement on their experiment.
- **Colour follows the same field:** darker hollows, varnish runs under the lips, debris on the replat.
- **The rules of irregularity,** verifiable:
  - no cornice keeps the same advance on more than 5 to 10 times its thickness;
  - it thins on a few times its width, never net;
  - none of them crosses a wall with a stroke.
- **From far, the same field in statistics:** mean slope zero, its variance in roughness, its shaded part in darkening. Never a stroke, never erased by pixel.

## 5. How to measure

### What others do

- **Few published protocols:** articles on Nanite and competing binary trees do not cipher temporal stability.
- **Public tools:**
  - ꟻLIP, NVIDIA 2020: the difference perceived when switching between two images;
  - ColorVideoVDP, Mantiuk et al. 2024: the visibility of defects that vary over time;
  - Schwarz and Stamminger 2009: a predictor of detail jumps, validated by a user study.
- **The common practice:** freeze the level of detail, scan it with a fixed camera, compare images. This is the principle of the benchmark arrival.

### No benchmarks

1. **The benchmark of arrival, new.**
   - Fixed camera; `MYPLANETENGINE_FACE_FACTOR` = 2 × 2^(−k/8), k from 0 to 32: four octaves of mesh.
   - For each step, the relative change of the ground light, after a blur of 8 pixels, as the mutation of the quality benchmark.
   - **The jump:** the largest step on the middle step. **The mutation:** the sum of the steps. And a heat map.
2. **The benchmark of jitter,** with and without smoothing, on six positions:
   - cornice, `2182.0 31.16045 8.58814 1.9 -17.1` and `2181.5 31.16051 8.58812 2.3 -11.8`;
   - Very steep wall, `1391.1 -11.04542 50.06777 2.6 55.3`;
   - red rock, `586.6 -25.21899 135.73187 -0.2 92.0`;
   - mountain at 45°, `3756.3 -39.55694 12.77814 -13.1 -141.1`;
   - wall of wallpaper, `2828.4 -0.03727 118.14886 -9.7 176.8`;
   - wall level, `1758.2 0.00182 118.14986 -10.9 81.8`.
   - Climates have changed the 2026-10-24, not the relief: check that these walls are still rock.
3. **The quality benchmark:** mutation, straight segments, scale holes, spreading.
4. **The benchmark of descent:** the average altitude and the part of rock, from 800 to 8 km.
5. **The shape against the photos,** new in the quality benchmark:
   - on wall crops at 30, 100 and 300 m, the length of the dark almost horizontal segments, the hollows, in relation to the wall height;
   - the same measure on `cible-falaise-alcoves.jpg`, `cible-gres-zion.jpg`, `cible-basalte.jpg`.
6. **The cost,** calculation and rendering, at 3, 30 and 300 m.
7. **Flight:** `MYPLANETENGINE_FLIGHT` along one wall, for the bumps, and a `tools/tests/<date>.txt` file of approaches to 300, 100, 30, 10 and 3 m on five walls.

### Proposed criteria

- **No visible appearance:**
  - at the finish benchmark, no step more than 2 times the median pitch of the reference, on the six walls;
  - Total mutation not more than +10 % on the reference;
  - both witnesses must exceed these thresholds. Otherwise the benchmark is not sensitive enough, and we review it before judging.
- **A flicker not above today:** at most +5 % with smoothing, the noise measurement, and +10 % without, on all six positions.
- **Appearance:** no p95 of quality benchmark degraded by more than 10 % (`AGENTS.md`); straight segments of rock views at most those of reference.
- **Consistency:** average altitude in descent to 1 % near, rock share to 0,5 point near.
- **The shapes:** the distribution of the lengths of the hollows in the photos; no continuous hollow on more than half the width of a wall.
- **Cost:** less than 1 ms at all near the ground.
- **In flight:** the user judges the cornices "drawn correctly", without mutation at the last moment, beautiful at all approaches.

## 6. Sources

**Continuity of level of detail**
- Strugar 2010, CDLOD, article and code: https://github.com/fstrugar/CDLOD
- Losasso and Hoppe 2004, Geometry clipmaps: https://hhoppe.com/proj/geomclipmap/
- Asirvatham and Hoppe 2005, GPU Gems 2, Chapter 2: https://developer.nvidia.com/gpugems/gpugems2/part-i-geometric-complexity/chapter-2-terrain-rendering-using-gpu-based-geometry
- Livny et al. 2008, persistent grid mapping : https://link.springer.com/article/10.1007/s00371-007-0180-1
- Houska 2020, Improved Persistent Grid Mapping : https://www.cg.tuwien.ac.at/research/publications/2020/houska-2020-IPGM/
- Dupuy et al. 2020, Concurrent Binary Trees : https://diglib.eg.org/handle/10.1145/3406186
- Benyoub and Dupuy 2024, CBT for Large-Scale Game Components: https://arxiv.org/abs/2407.02215
- Deliot et al., Unity, SIGGRAPH 2021, terrain tessellation by CBT: https://www.advances.realtimerendering.com/s2021/Siggraph21%20Terrain%20Tessellation.pdf
- Microsoft, mesh shaders : https://microsoft.github.io/DirectX-Specs/d3d/MeshShader.html

**Engines and games**
- Widmark 2012, Terrain in Battlefield 3 : https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/gdc12-terrain-in-battlefield3.pdf
- Moore 2018, Terrain Rendering in Far Cry 5 : https://gdcvault.com/play/1025261/Terrain-Rendering-in-Far-Cry
- Carrier 2018, Procedural World Generation of Far Cry 5 : https://gdcvault.com/play/1025557/Procedural-World-Generation-of-Far
- Pohlmann 2021, Samurai Landscapes, Ghost of Tsushima : https://gdcvault.com/play/1027352/Samurai-Landscapes-Building-and-Rendering
- PlayStation Blog, Ghost of Tsushima effects, tesselated terrain and cliff rocks: https://blog.playstation.com/?p=345372
- PlayStation Blog 2025, Ghost of Yōtei, terrain tessellation: https://blog.playstation.com/?p=411201
- van Muijden 2017, placement GPU d'Horizon Zero Dawn : https://www.guerrilla-games.com/media/News/Files/GDC2017_VanMuijden_GPUBasedProceduralPlacementInHorizonZeroDawn.pdf
- Karis 2026, Nanite + Reyes : https://graphicrants.blogspot.com/2026/02/nanite-reyes.html
- Epic, Nanite and the landscapes: https://dev.epicgames.com/documentation/unreal-engine/using-nanite-with-landscapes-in-unreal-engine
- Epic, Virtual Heightfield Mesh : https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/VirtualHeightfieldMesh/UVirtualHeightfieldMeshComponent
- Star Citizen, interview with Sean Tracy on parallax: https://gamersnexus.net/gg/2636-citizencon-parallax-occlusion-mapping-sean-tracy-interview
- Star Citizen, Planet Tech v5: https://starcitizen.tools/Planet_Tech_v5
- Kemen 2009, Outland, Horizontal fractal displacement: https://www.gamedeveloper.com/programming/horizontal-fractal-displacement
- US Patent 10229536, fractional tessellation vertices movement and sliding: https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10229536

**Cliffs, vector shift, filtering**
- Weiss, Bayer and Westermann 2020, Triplanar Displacement Mapping: https://diglib.eg.org/handle/10.2312/egs20201016
- Paris et al. 2019, Terrain Amplification with Implicit 3D Features : https://hal.archives-ouvertes.fr/hal-02273097
- Paris et al. 2020, implied block walls: https://hal.archives-ouvertes.fr/hal-02926218
- Peytavie et al. 2009, pile of stones: https://diglib.eg.org/handle/10.2312/CGF.v28i7pp1801-1809
- Cordonnier et al. 2018, Sculpting Mountains : https://hal.archives-ouvertes.fr/hal-01517343
- Jones et al. 2010, alteration of rocks by curvature: https://scholarsarchive.byu.edu/facpub/110
- Gaea, Stratify : https://docs.quadspinner.com/Reference/Erosion/Stratify.html
- Dupuy et al. 2013, LEADR mapping : https://perso.liris.cnrs.fr/victor.ostromoukhov/publications/pdf/SAsia2013-LEADR.pdf
- Bend Studio, contact shadows on screen: https://www.bendstudio.com/blog/inside-bend-screen-space-shadows/

**Geomorphology**
- NPS, the geology of the Grand Canyon: https://www.nps.gov/grca/planyourvisit/upload/life_geology.pdf
- Ward and Anderson, retreat from the cliffs at bed hard: https://www.colorado.edu/program/hydrosciences/2018/08/23/retreat-rates-and-controls-form-hard-capped-cliffs-plateau-country
- Howard 2004, slopes of Colorado plateau under hard bed: https://gsa.confex.com/gsa/2004AM/webprogram/Paper75355.html
- Wingate Sandstone, sapping and diaclase falls, secondary source: https://moabhappenings.com/Archives/Geology202402-WingateSandstone.htm

**Measure**
- Andersson et al. 2020, ꟻLIP : https://research.nvidia.com/labs/rtr/publication/andersson2020flip
- Mantiuk et al. 2024, ColorVideoVDP : https://arxiv.org/abs/2401.11485
- Schwarz and Stamminger 2009, predict detail jumps: https://cris.fau.de/publications/118172384
