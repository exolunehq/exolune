# Celestial body manifests and shared rendering

**Status**
- Fundamental engine architecture required by the user on 2026-11-08.
- Authoritative rules are in [principles](principes.md).
- This contract defines the target architecture; the current celestial prototype does not yet implement the complete manifest system.
- Three typed airless manifests use the common sliding-plane path; the separate lunar quadtree prototype is rejected.
- Their radius, seed, gravity and reflectance feed terrain, contact, walking, lighting and cooked distant maps from one description.
- The prototype has one detailed terrain allocation and three fixed atlas slots; catalogue expansion requires bounded atlas residency.

**Body description**
- Every body has a stable identifier, manifest version and deterministic seeds.
- This includes the main planet, moons, other terrestrial planets, gas giants and the Sun.
- Physical properties describe size, shape, reference frame, motion, gravity and surface availability.
- A composed field describes noise layers, tectonics, impacts, erosion and deposits where applicable.
- Materials describe reflectance, roughness, grain, regional distribution and physical detail scales.
- Population rules describe anchored pebbles, boulders and other supported surface objects.
- Optional modules describe atmospheres, clouds, liquids, vegetation, participating volumes and emission.
- Asset and generated-data references retain their provenance and version or content hash.
- Units, bounds and module compatibility must be validated before activation.
- The serialization format and complete schema remain implementation decisions; this document is not a claim that a loader already exists.

**One common engine**
- Solid terrain uses the same sliding planes and rings as Exolune, recalculated as the observer moves.
- The same footprint filtering, fine grid, screen reconstruction and continuous transitions apply to every solid body.
- The manifest changes the evaluated stack and its parameters, not mesh topology or the rendering algorithm.
- Shared extensions belong to the engine and are reusable by manifests; no body-specific rendering fork is accepted.
- Stars and gaseous bodies select appropriate shared media and emission modules within the same hierarchy and compositing framework.
- An atmospheric or emissive body does not automatically have solid ground or landing contact.
- Geometry, contact, object placement, shadowing and distant appearance consume the same physical description.

**Quality at every scale**
- Simpler physics does not lower the surface quality target.
- An airless moon retains impact topography, fractured rock, regolith, detailed materials, pebbles and boulders.
- Its stack omits unrelated hydrology, atmospheric erosion and vegetation.
- Objects remain fixed in body coordinates, seated on the shared relief and filtered by the common visibility rules.
- Light, cast shadows, contact and material response remain coherent from orbit to ground.
- Review includes continuous approach, descent, landing, walking and looking back toward other bodies.

**Distance and budgets**
- Keep inactive manifests as compact descriptions, not allocated planet engines.
- Select visible candidates spatially before evaluating their physical stacks.
- Unresolved bodies use integrated light; small resolved bodies use filtered representations of the same description.
- Expensive geometry, material detail, object populations and optional simulation activate only at justified projected scales.
- Detailed buffers and preparation budgets are shared and bounded across active bodies.
- Increasing the catalogue must not multiply full-resolution terrain or per-pixel body loops.
- A distant representation preserves silhouette, phase, brightness, occlusion and continuity during approach.
- Widely separated planets normally allow one nearby detailed body; the engine still enforces budgets if several bodies compete.
- Negligible distant cost is an engineering requirement to verify, not literal zero work or an unlimited visible population.
- Performance conclusions require requested measurements in motion on both Exolune and the approached body.

**First integration**
- Reuse the erosion branch's current common rendering path.
- Integrate one airless impact stack through that path, with shared surface objects and landing contact.
- Remove the separate lunar quadtree and its transitions.
- Keep the existing orbital exposure corrections and the user's rejection of temporal exposure smoothing.
- Record implementation and validation status in [airless terrain](spec-lune-terrain.md).
