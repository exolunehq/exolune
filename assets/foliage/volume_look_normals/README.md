# Leaf normal variant — October 27, 2026

- **Base:** `volume_look`. Geometry, UVs, indices, atlases and bounds are identical; the pine is copied unchanged.
- **Foliage:** original normals oriented outward, then blended 55% with a radial field anchored at the nearest branch point of each card. This field has a vertical bias of 0.15. Bark and twigs are unchanged.
- **Reference:** “Parent Puffiness” normal anchoring in the [SpeedTree documentation](https://docs9.speedtree.com/modeler/doku.php?id=card_generator). This variant does not use SpeedTree software.
- **Rebuild:** `python tools/foliage/volume_assets.py --normals`; `--mix` and `--up` control the blend and bias. The volume and impostor normals are recalculated. The two visibility files are identical to the base because surfaces and their alpha do not change.
- **Limit:** shading must be compared in the engine with the reference views; this variant alone does not guarantee a more realistic appearance.
