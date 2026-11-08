# Reflective ship surfaces

**Navigator integration, 2026-11-03.** A smooth metallic hull reflects the current game scene and a physical planet fallback; its interior viewing field is described in `spec-navigateur-cockpit-son.md`.

**Material**

- The editable smooth v2 skin is exported at scale ×4 into `assets/vaisseau/navigateur/`.
- Metallic 1, linear base colour `(0.84, 0.87, 0.91)`, roughness 0.075; no normal texture or baked reflection.
- Existing GGX sunlight and Fresnel use the actual smooth mesh normals.
- Solar attenuation includes the hull's shadow maps, terrain horizon and cloud shadow at the ship.
- Selection retains the fighter as the executable's default.
- The Navigator starts in its modelled cockpit; its virtual viewing field uses no canopy water simulation.
- The profile supplies no exhaust jets or animation pivots.

**Scene transport**

- Render the world without any Navigator geometry for the exterior reflection source.
- Draw the opaque cabin only in cockpit views; its hidden interior must not create false exterior reflection hits.
- Trace the reflected direction through the current HDR composite and its radial depth in camera-relative metres.
- Up to 64 increasing steps locate a crossing; seven refinements resolve it.
- Reject depth discontinuities and fade near the viewport boundary.
- Five depth-aware colour samples soften the hit according to material roughness and travel distance.
- Visible terrain, rocks, vegetation, ocean and atmospheric light come from the same scene as the game.
- On-screen sky and clouds can complete unobstructed reflected directions.
- The reference approach is screen-space ray tracing: [McGuire and Mara, 2014](https://jcgt.org/published/0003/04/04/).

**Directions outside the image**

- Integrate the existing physical atmosphere from the hull along the reflected ray.
- Intersect the actual spherical planet and retain curvature in orbit.
- Read the planet elevation and climate maps at the hit; use the existing biome albedo palette for land.
- Use a dark ocean albedo below the atmosphere for the sea fallback.
- The fallback is coarse illumination, without local terrain silhouettes, individual trees, off-screen cloud volumes or reflected ship geometry.
- Screen-space radiance includes the original camera's atmospheric path; this is an approximation for distant reflected hits.
- Full off-screen vegetation requires a separate scene capture or ray-tracing structure.

**Composition and history**

- Draw the reflective skin after the world's atmosphere into the ship overlay, depth-tested and depth-writing.
- Omit that outer skin in cockpit view; the modelled cabin bounds its clear forward field.
- The world composite is read-only during this pass; there is no feedback from the current hull.
- Apply the short camera-to-hull atmospheric path and local cloud extinction.
- The 32-bit float overlay stores opaque hull distance as negative alpha.
- Tone mapping resolves that layer before temporal smoothing and uses the existing ship reprojection.
- Existing canopy and plume alpha compositing remains after temporal smoothing.
- Common world exposure and film curve apply to chrome without a special brightness multiplier.

**Review**

- Build: `tools/lance.ps1 -Build -NoLaunch`.
- In-flight route: `tools/tests/2026-11-03-navigateur-cockpit.txt`, six locations; Tab selects the exterior.
- Launch: `tools/lance.ps1 -ModeleVaisseau navigateur -Resolution fenetre -Parcours tools/tests/2026-11-03-navigateur-cockpit.txt`.
- Functional CINE stills: `python tools/tests/capture_navigateur.py`, then `tools/tests/capture_navigateur.ps1 -Vue foret|ocean|montagne|orbite` with one engine at a time.
- Outputs: `artifacts/navigateur-jeu-2026-11-03/`.
- These are functional visual inspections; no performance or quality benchmark was requested.
