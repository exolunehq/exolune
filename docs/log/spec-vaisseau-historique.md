# Ship and camera history

**2026-11-08 · Free look preserved during contact recovery**
- Terrestrial contact recovery and invalid-query rollback restored the complete saved camera pose.
- Repeated recovery could discard accumulated mouse look even though the free-camera contact shape is spherical.
- Contact now restores position alone for free camera; ship pose correction retains its existing behavior.

**2026-11-08 · Removed implicit orbital steering**
- The old update rotated the camera, ship and ship velocity whenever the local vertical changed with position.
- The free camera rebuilt its up axis from the nearby body and clamped pitch at a dot product of 0.995, about six degrees short of vertical.
- Switching between Exolune and the Moon blended those verticals and could steer the observer without input.
- Exact nadir and zenith depended on a nearly zero cross product; initial frames now retain an explicit heading-derived up axis.
- The replacement keeps a world-space flight attitude; walking retains the surface vertical.
- The near-Moon translating reference frame remains; this change removes steering, not the prototype's orbital translation.

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
# Ship assembly history

**2026-11-01 · Superseded junctions and flat foredeck**

- The first fitted layout contained 62,216 triangles and retained the flat nose shoulders.
- The dashboard wings followed the hidden tub boundary and extended behind the consoles.
- Console front caps met the dashboard with broad diagonal returns and some reversed lower sections.
- Nine of 142 samples on each wing panel were hidden by a console from the nominal pilot eye.
- The flat foredeck was visible on 90 of 18,281 forward probe rays from that eye.
- The user requested clean junctions, an invisible nose from inside and a more fluid exterior profile.
- Its minimum hardware-to-panel clearance was 5.503 mm; GLB/VSX sizes were about 17.3/17.8 MB.
- A first lowered-shoulder experiment introduced a local trough; a gradual ramp from the forward nose replaced it.
- The exact Boolean solver remained sensitive to the revised coplanar pockets; the manifold solver passed all closed-pocket checks.
- The previous source, assets and captures remain locally in the `Exolune-vaisseau-finitions` worktree under `out/vaisseau-finitions/avant-raccords/`.

**2026-11-01 · Superseded rectangular panel layout**

- The first integrated revision recessed thirteen rectangular printed panels and three displays, with four service pockets.
- It introduced the continuous console fascias, 18 cm shelves and thin flat canopy retainer.
- The asset contained 57,375 triangles, 34 materials, 48 draw ranges and 12 images.
- Its 2048px label atlas used 1800 px/m source labels; GLB and VSX were about 13.2 and 13.6 MB.
- Its checks covered 360 mounting samples, 20 closed pockets and 27 display sightlines.
- Individual rectangular panels left unused space in the tapered dashboard and side fascias.
- The user requested fitted layouts, retained physical switches, a slightly more futuristic design and richer textures.
- A later pilot screenshot prompted the shallow dashboard crown; the circled white strip was traced to the actual external hull.
- The exterior nose was left unchanged in this revision.
- Sequential Boolean cuts lost some coplanar pocket floors; a compound cut per support resolved this before delivery.
- Intermediate captures and the tracked binary patch remain locally in the `Exolune-vaisseau-finitions` worktree under `out/vaisseau-finitions/avant-panneaux/`.

**2026-11-01 · Superseded surface-mounted finish pass**

- Conforming sockets closed mounting gaps but kept instruments standing proud of the console.
- The canopy still used the original 104 mm circular tube, which read as an inflated seal.
- The intermediate asset contained 47,143 triangles, 34 materials, 47 draw ranges and 12 images.
- Its checks covered 216 support samples and 27 screen sightlines.
- Daylight and low-sun cockpit/chase views were inspected in the engine before the last socket correction.
- The integrated revision replaces instrument sockets with closed recesses and the tube with a flat retainer.
- Intermediate screenshots and the tracked binary patch remain locally in the `Exolune-vaisseau-finitions` worktree under `out/vaisseau-finitions/avant-integration/`.
- At that stage the finish work was uncommitted; the baseline tag identified only `ad981f4`. The accepted asset was later committed as `b43d8ee`.

**2026-11-01 · Cabin finish baseline**

- Claude's conversation “Vaisseau : modélisation, textures et rendu poussés” produced the concept fighter in `ad981f4`.
- Its exported GLB contained 29,855 triangles, 31 materials and 10 images.
- The earlier asset README quoted 29,555 triangles; the exported file is the measured baseline.
- Inclined module sockets used a constant-depth box under an analytically sampled panel.
- Horizontal modules followed the global axes on a shelf only 14 cm wide.
- Flat sockets and curved supports could leave visible gaps.
- Screen recesses lacked the return from the bezel to the display surface.
- Interior panelling reused a small region of the hull atlas.
- The seat bolsters and headrest used coarse chamfered sections.
- Baseline tag: `piste/2026-11-01-vaisseau-finitions-base`, pointing to `ad981f4`.
- Current construction and review procedure: [ship specification](../spec-vaisseau.md) and [asset README](../../assets/vaisseau/chasseur/README.md).

**2026-11-01 · Before default selection**

- The fighter finish was reviewed on `codex/vaisseau-finitions`, starting from `ad981f4`.
- The user accepted the revised junctions and nose, then requested a merge onto `main` while preserving the previous ship.
- The earlier spec quoted roughly 120 MB of ship textures; that count described the classic asset, not the new fighter.
