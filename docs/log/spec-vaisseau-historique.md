# Ship and camera history

## 2026-11-01: rejected clearance-dependent near plane

- The ship used a 5 cm near plane; views without the drawn ship used `max(0.01, 0.1 * clearance)` metres.
- At 41.4 m clearance, the latter clipped any wall closer than 4.14 m, even when the eye was outside the terrain.
- The near plane is now 5 cm in every view; reversed Z and the 1e9 m far plane are retained.
- The source audit also found delayed nadir-only contact; the interactive replacement is described in the current specification.
- Numerical projection checks cover clearances from 1 m to 40,000 km and finite, monotone reversed-Z depth.
- Local evidence is in `x64/erosion-render/`; no performance or image-quality benchmark was run.

## 2026-11-01: replaced interactive radial contact

- Interactive movement read the previous frame's nadir height, then clamped the proposed position radially.
- `UpdateShip` reused camera-ground height for the hull and offset chase camera, despite their different terrain positions.
- A radial clamp could enter a steep wall for a frame and then lift the observer onto its plateau.
- Querying only the endpoint would retain that tunnelling mechanism; cinematic endpoint positioning remains separate.
- The replacement uses swept contact for interactive flight; initial placement recovery remains a separate operation.
- An initial prototype inflated the hull by its final centre displacement; this did not bound intermediate rotational arcs and was replaced by a fixed origin-centred sphere.
- An initial tangent corridor clamped the endpoint projection; this did not cover arbitrary planet-crossing chords and was replaced by analytic outer-shell clipping and a sea-sphere stop.
