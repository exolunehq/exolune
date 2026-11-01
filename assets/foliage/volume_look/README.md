# Appearance variants and precomputed lighting — October 27, 2026

- **Sources:** `game_broadleaf` and `game_shrub`; details and licenses in `assets/foliage/game_origins.md` and `assets/foliage/game_shrub_origins.md`. The pine is copied unchanged.
- **Foliage:** copies of the original leaf cards oriented around the nearest branch point. Original branches, textures and bounds remain unchanged. No solid envelope is added.
- **Budgets:** 7,010 triangles for the broadleaf; 13,406 for the shrub. The shrub's alpha twigs remain classified as branches for lighting.
- **Lighting:** rays through the 64³ alpha volume, starting 2.25 cells away, six local directions and sixteen sky directions. Calculation settings are in `bake_metadata.json`.
- **Formats:** `lighting.bin` stores eight floats per vertex. `impostor_light.bin` stores two non-premultiplied RGBA8 planes for the 60 views, in the same order as `impostor.bin`.
- **Rebuild:** from the root, `python tools/foliage/volume_assets.py`. Source tree and shrub files must be prepared first; dependencies: numpy, Pillow and numba.
- **Limit:** CPU silhouettes show more leaves, but the shrub remains open. Appearance and performance in the application remain to be evaluated.
