# Sources and reproduction

**Game catalog, found by default by the engine in `assets/foliage/climate_shrubs_v2`:**
- `climate_shrubs_v2`: two trees from `volume_look_normals` and twelve shrubs from six climate families.
- Build everything in one command from the root: `tools\plantes.ps1`. It imports the game sources below, then runs `volume_assets.py`, `volume_assets.py --normals`, and `arbustes_climatiques_v2.py --preview` and `--final`.
- The catalog and its limitations are described in `../../docs/arbustes-climatiques.md`; generated binaries remain ignored by git.
- A catalog built before 2026-10-29 retains darker impostors averaged in sRGB: rebake them as described in `../../docs/lancement.md`.

**Source game models:**
- Pine [Pine Tree](https://sketchfab.com/3d-models/pine-tree-d45218a3fab349e5b1de040f29e7b6f9), evolveduk, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/): 5,627 triangles.
- Broadleaf [Free Realistic Tree 10 / Tree10_1](https://opengameart.org/content/free-realistic-tree-10), Rakshi Games, [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/): 3,308 triangles.
- Shrub [Searsia Lucida](https://polyhaven.com/a/searsia_lucida), James Ray Cock and Jenelle van Heerden, CC0: 7,232 triangles; credits in `game_shrub_origins.md`.
- Artist models with mesh branches and cutout foliage; the texture provides leaves and fine twigs.
- Sources are kept in the cache with URLs and SHA-256 hashes pinned in `tools/foliage/sources_jeu.json`.
- Reference-frame conversion, Unity UVs and packed normals; two-material atlas at 2,048 × 1,024.
- Pine roughness maps are preserved; the broadleaf uses constant roughness because no usable source map is available.
- Full credits and transformations: `game_origins.md`.

```powershell
python -m pip install numpy pillow numba UnityPy
python tools/foliage/telecharge_jeu.py
python tools/foliage/importe_jeu.py
python tools/foliage/bake.py game_fir game_broadleaf --volume-res 64
python tools/foliage/importe_arbuste.py
python tools/foliage/bake.py game_shrub --volume-res 64
./tools/lance.ps1 -Build
```

- `material.bin`: magic `FOLMAT01`, uint32 width and height, RGBA8 atlas of OpenGL normals, then RGBA8 masks for AO, roughness, transmission, alpha 255.
- The engine places these two atlases alongside color in the mesh buffer; bit 0 of `unused` enables their reading.
- The active path also creates three texture arrays per model: sRGB color, UNORM normals and masks, one layer per material; ×8 anisotropy and coverage-weighted mipmaps.
- Bit 1 selects the transition and stable alpha for `game` and shrubs; bit 2 enables these material textures.
- Impostors and volume retain mesh normals, without normal-map details or the nearby material's reflection.
- Triangle budgets are those of the imported files; no AAA quality level or FPS gain is validated before in-flight review.
- No benchmark, test or verification render was run before the requested flight.

**Files, little-endian:**
- Foliage variants are rebuilt after the game models: `python tools/foliage/volume_assets.py`, then `python tools/foliage/volume_assets.py --normals`. The current catalog uses these two trees; `MYPLANETENGINE_FOLIAGE_ASSETS` specifies another catalog. Source models remain in `game_*`.
- `lighting.bin`: magic `FOLLIT01`, uint32 vertex count and stride of 8 floats, then sky, sun +X/−X/+Y/−Y/+Z/−Z and leaf mask per vertex, all in [0, 1].
- `impostor_light.bin`: magic `FOLIL001`, four uint32 values for azimuths, elevations, width and height; two non-premultiplied RGBA8 planes, in the view order of `impostor.bin`, carrying the same eight fields.
- `mesh.bin`: magic `FOLMESH1`, four uint32 values for vertices, indices, atlas width and height, then uint32 material count and two float3 bounds. Vertices `float3 position, float3 normale, float2 UV, float matériau`, uint32 indices, then RGBA8 sRGB atlas with material tiles side by side. Non-premultiplied color.
- `volume32.bin`, `volume64.bin`, `volume128.bin`: magic `FOLVOL01`, uint32 resolution 32, 64 or 128 and level count 6, 7 or 8, float3 min and max bounds. `volume.bin` is a copy of the 64 by default. Levels from the selected resolution to 1³, X fastest, then Y, Z; voxel `float4 couverture, albédo RGB linéaire`, then `float4 normale XYZ, dispersion`. At the base level, coverage is `1-exp(-0,5 × surface alpha / aire moyenne des faces)`. Each parent preserves its children's transmission: product along two cells, average over four columns, then average of the three axes' extinction values. Colors and normals remain surface-weighted. Dispersion: 1 minus the mean normal's length before normalization. Sample distribution and isotropic averaging remain approximate.
- `impostor.bin`: magic `FOLIMP01`, uint32 azimuth count 12, elevation count 5, width and height 128, float3 min and max bounds, float radius. Then 60 RGBA8 sRGB images, then 60 float4 images containing object normal XYZ and depth; order: elevation, azimuth, row, column. Non-premultiplied color. A 0.5 alpha test on a 256² image, reduced over four samples, preserves fractional coverage.
- Azimuth θ=2πa/12; elevation φ=πe/8. Camera `(sinθ cosφ, sinφ, cosθ cosφ)`, right `(cosθ,0,-sinθ)`, up `(-sinθ sinφ,cosφ,-cosθ sinφ)`. Center `(0 ; 0,5 ; 0)`; orthographic image from −radius to +radius on each axis, image top upward; depth `dot(position-centre, caméra)` increases toward the camera. Double-sided normals face the camera.

**Photo and stylized models,** experiments from the volumetric prototype, were removed with it; they remain at tag `jalon/24-vegetation-detaillee-main`, with their history in `../../docs/log/prototype-vegetation-volumique-historique.md`.
