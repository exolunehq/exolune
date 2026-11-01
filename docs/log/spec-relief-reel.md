# Specification: the actual relief of materials

**In the log:** disabled the 2026-10-23, its code removed the 2026-10-30, `MaterialRelief.hlsl` and `MATERIAL_RELIEF` including. It remains at the `piste/parois-gradins` tag, where it is active. Track geometry: `../geometrie.md`.

Status: validated on 2026-10-21. Steps 1 to 3 done; visual gain still low. Continued track B (`spec-textures-generees.md`): after six laps of benchmark, the rock remains flat. Recommendation 4 from `etat-de-l-art-details.md`.

## The finding

**The relief of materials exists only in normal.** The bumps, slabs, cracks and stones light up like relief, but:

- **no silhouette:** a stone never cut on the bottom;
- **no obscuration:** nothing hides anything;
- **no cast shadow:** a bump does not shade its neighbor.

**This is the limit of texture alone,** and we have reached it.

## The purpose

**That the mesh itself carries the relief of materials where its grid cells allows it.**

- **Near the camera, the grid cells are already a few centimeters:** 3 cm to 1,5 m from the ground, 20 cm to 10 m.
- **The relief of the materials becomes an octave more of the relief,** below those of complexplanet.
- **Further, it remains in the normal,** as today.
- **Everything remains calculated at each frame, without memory.**

## The principle

### A move pass, after the relief

**A second pass of calculation moves each visible vertex** along the surface normal, from the height of the materials to its point on the planet.

1. **The normal of the vertex,** by its neighbors, as in the vertex shader. It chooses the axes of the biplanar projection and gives the direction of the displacement. A rock bump is therefore moving out of the wall, not towards the sky.
2. **Material weights**: climate, slope, sand, scree, rock, snow. This is the same code as the pixels of the ground, shared in a shared file.
3. **The height of each material,** read from the generated textures, at the mipmap level that corresponds to the grid cell of the summit.
4. **The sand wrinkles,** by the same function as pixels, filtered to the grid cell.
5. **The movement,** mixed by height as the colors.

- **No movement under the sea.**
- **Under the snow, the relief softens.**
- **The spline prefilter comes after:** spline normals see the relief shifted.

### The sharing between mesh and pixels

**Each wavelength is carried only once.**

- **The mesh carries what exceeds two grid cells,** according to the same cutoff rule as complexplanet, `MESH_BAND_LIMIT`. This is what the chosen mipmap level gives.
- **The pixels only keep the relief finer than the grid cell:** the slope of the texture less its slope at the mipmap level of the mesh.
- **Wrinkles:** in the mesh as long as two grid cells fit in a wrinkle, otherwise in pixels.

### The shadows

**Three scales, from the thinnest to the widest.**

- **Fine shadows in the sun,** already in place: the hollows cut off direct light.
- **Texture shadows,** pixel: a few steps on the height of the texture, towards the sun, for relief finer than the grid cell. A crack shades its side, a stone shades the dust. Eight steps at most, only close.
- **Shadows of the contact of the displaced relief,** on the screen: a short ray throw to the sun in the depth, the way of Bend Studio for Days Gone. It requires a depth pass beforehand, so that the pixel shader of the ground knows the shadow before lighting. This is the heaviest step: it comes last.
- **The mountain shadows on the valleys** remain outside of this spec. They need a shadow card or a ray throw on the large relief.

## Risks

- **jitter:** the material relief slides with the mesh as the rest of the relief. The two-cut grid cells and spline normals limit it. The jitter benchmark will measure it.
- **Mutation:** on approach, the relief changes from pixels to mesh. The lighting was already the same, only silhouettes and occultations appear, gradually. The mutation benchmark will measure it.
- **The camera at ground level:** the height under the camera ignores the relief of the materials. At 1 m, a rock bump of 20 cm could border the lens. The floor of the camera will be raised to the maximum amplitude of relief.
- **The cost:** an evaluation of materials per visible vertex, i.e. 100 000 to 150 000. Order of magnitude: 0,3 to 0,6 ms.

## What changes in the code

- **`Materials.hlsli`,** new: material weight, reading of generated textures and wrinkles, shared between vertices and pixels calculation.
- **`MaterialRelief.hlsl`,** new: the travel pass.
- **`D3DApp.cpp`**: the pass between the relief calculation and the spline prefilter, and the floor of the camera.
- **`PixelShader.hlsl`**: it keeps only the relief finer than the grid cell, and adds the shadows of the texture.
- **`PlanetSettings.hlsli`**: `MATERIAL_RELIEF`, the intensity of the relief moved; 0 returns to the texture only.

## The steps

1. **Common code,** without rendering change, verified frame by frame.
2. **Moving,** on the rock and the scree first, then the sand.
3. **The sharing between mesh and pixels.**
4. **The shadows of texture.**
5. **The contact shadows,** with the depth pass.

## The measure

- **The visual benchmark,** at 1,5 m, 10 m, 100 m and 1 km, on the rock, the scree and the desert: silhouettes and occultations visible close up.
- **The benchmarks of jitter and mutation.**
- **The cost of GPU** of Pass and Shadows.

## Validation criteria

- **At close sight, the stones and bumps cut apart** on the bottom, and hide each other.
- **No jitter or mutation visible in addition,** in flight.
- **Cost:** less than 1 ms in total for the 1 to 4 steps.

## Results of the steps 1 and 2

- **Step 1, the common code:** `Materials.hlsli` and `Mesh.hlsli`, shared by the pixels, the vertex shader and the relief pass. Render identical to pixel on all views of the benchmark.
- **Step 2, the shift:** the `MaterialRelief.hlsl` pass moves nearby vertices. The cracks and bumps of the rock take real relief.
- **Defect expected until step 3:** relief is counted twice, in the mesh and in the normal of the texture. Close to the camera, this results in too dark facets along the cracks.
- **Sand:** the wrinkles of 6 mm change little the geometry; their effect is mainly through the light.

## Results of the 3 stage and measurements

- **The split between mesh and pixels:** each texture reading also gives its slope to the scale of the mesh filter; the pixel cuts it off, dosed like the relief pass. The dark facets along the cracks have disappeared.
- **The jitter, on the rock, with and without temporal smoothing:**

| Variant | Rock at 3 m | Rock at 14 m |
|---|---|---|
| Without relief | 0,04 / 0,25 | 0,03 / 0,22 |
| Relief filtered to 2 grid cells | 0,17 / 0,91 | 0,12 / 0,72 |
| Relief filtered to 4 grid cells | 0,09 / 0,49 | 0,07 / 0,41 |
| Relief filtered to 8 grid cells | 0,06 / 0,33 | 0,04 / 0,27 |

- **Setting retained:** `MATERIAL_RELIEF_BAND` = 8, the relief only bears the waves of eight grid cells and more. The sand does not shake, its wrinkles of 6 mm hardly change the geometry.
- **Cost:** 0,1 ms of extra compute.
- **The visual gain remains low:** in rasant view at 1,5 m, without relief and with relief are almost the same. The bumps and facets of the generated rock, from a few centimeters to 15 cm, are too soft to cut a silhouette. It will take more frank forms in the recipe, blocks, cornices, rocks, or sown objects.

## Fix for 2026-10-21: peaks

- **Symptom:** in dry zone, peaks of 10 to 30 cm that sparkle in flight.
- **Cause:** the mixing by height is not linear. On heights filtered, however, it makes a summit of one material to the other between two neighbors. The relief jumps then from that of the rock, ±30 cm, to that of the sand.
- **Correction:** the relief pass mixes materials by their base weights, without height. The relief remains as filtered as the textures.

## Fix of the 2026-10-22: blades, needles and relief flicker

**Symptom,** in flight after the milestone 13: blades and needles of one to three meters, and a relief that sparkles. Positions `6559.3 -18.67003 131.64985 37.0 -70.2` and `586.6 -25.21899 135.73187 -0.2 92.0`.

**Three causes,** isolated one by one to benchmark of jitter, which takes an exact position:

1. **Snow was decided on the relief itself.** In the relief pass, the slope of the textures, that of the relief of the tile of 64 m, chased the snow. Now the snow crushed the relief at 10 %: one summit in two swinged between rock and snow, and raised a blade.
   - **Fix:** the slope of the textures moves the snow limit as the mixture by height, with the same dosage `gHeightBlend`. It is absent from the relief pass and fades for large pixels.
2. **The biplanar projection tilted near the diagonal of the cube.** Its weights, raised to the power 8, both tended to zero when the normal approached a diagonal. The slightest deviation from the normal then made one plane to pass to another, and the relief of one copy of tile to another.
   - **Correction:** weights triplanar `max(|n| − 0,45, 0)²`. One plane only less than 25° from its axis, two along one edge of the cube, three at its diagonal, and continuous everywhere.
3. **The normal of the relief pass was too thin.** Taken on 4 grid cells, it followed the waves of the mesh long from 2 to 8 grid cells, which slide under the peaks. The relief meters of the tile of 64 m changed projection at each frame.
   - **Fix:** the normal is taken on 32 grid cells, `RELIEF_NORMAL_CELLS`. Cost: +0,2 to 0,3 ms of calculation.

**And a caution:** complexplanet peaks are no longer rounded on less than two grid cells of 2 m, `CREASE_MIN_CELL`, as close as the camera. The relief has no octave under 13,5 m, and a ridge wide of a few centimeters turned the normal from one summit to another.

| jitter, with / without smoothing | Before | After | Without relief of materials |
|---|---|---|---|
| Red Rock, `586.6 -25.21899 135.73187`  | 10,1 / 21,4 | 2,1 / 7,5 | 1,1 / 5,6 |
| Snowy Ridge, `6559.3 -18.67003 131.64985`  | 1,7 / 7,8 | 0,55 / 1,1 | 0,45 / 1,7 |
| Snowy Ridge, `6561.8`  | 0,19 / 0,86 | 0,12 / 0,48 | 0,12 / 0,56 |
| Dune, `563.6 5.98065 127.83668`  | 0,16 / 1,0 | 0,16 / 0,94 | 0,13 / 0,86 |
| Rock site, 3 m |  | 0,10 / 0,42 | 0,06 / 0,29 |

- **The blades and needles have disappeared** on both reported views. The cornices of the 64 m tile remain on the cliffs.
- **There is still a surcharge of jitter** on the red rock, 2,1 against 1,1 without relief.
- **The real solution, to be studied:** a rock structure in volume, function of altitude and position, rather than projected on planes. strata and diaclases would then have no projection to choose, nor normal to depend on.

## Fix of the 2026-10-22: a cornice that changes material when approaching

**Symptom,** in flight: from 11 m to 5 m of a cornice, positions `2182.0 31.16045 8.58814 1.9 -17.1` to `2181.5 31.16051 8.58812 2.3 -11.8`.
- From afar, the cornice is seen by its color.
- As you approach, the color disappears, and geometry forms.
- Nearby, another sand spot appears, of another shape.

**The cause:** the materials, rock, replat or sand, decided on the normal of the mesh. The mesh bears a growing share of the material relief as its grid cells shrinks. The plate became flat in geometry, was no longer rock, and changed material.

**The rule, which applies to any material:** decisions never depend on the part of the relief that the mesh carries.
- **The decision normal** is that of the field alone. The vertex shader calculates it on the vertices before the relief pass. From afar, the thin grid, which only carries the ground, takes over.
- **The textures make their slope entire,** and apart, the part that bears the mesh (`Texture.carried`). Decisions take the entire slope; the pixel light takes away the bearing part.

**Measures:**
- **Without relief in the mesh,** the cornice already kept its color and shape on the three positions: this is the reference.
- **With this fix,** the clear strip of the replat remains in place from 11 m to 5 m.
- **jitter,** to 5 m: 0,31, against 0,29 before correction and 0,22 without relief. At 11 m: 0,17 against 0,18.
- **benchmark downhill:** rock and snow unchanged.

**What remains:** the geometry of the cornice still appears in the last meters. This is the price of a mesh that only carries a relief from eight grid cells per wavelength. To soften it, it would be necessary that the pixels show the depth before the mesh, by a parallax, or that the mesh bears the relief earlier, at the price of the jitter.
