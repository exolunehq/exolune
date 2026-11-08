# Celestial surface data

**Current airless surfaces**
- `CelestialManifest.h` describes the three moons, their seeds, radii, gravity, reflectance and atlas names.
- `airless.rgba8mips`, `airless-2.rgba8mips` and `airless-3.rgba8mips` come from the same procedural impact field as terrain and contact.
- Build all three with `powershell -NoProfile -ExecutionPolicy Bypass -File tools/prepare_airless.ps1` after changing the field or manifests.
- Each file has a 32-byte `Celestial::AirlessAtlasHeader`, followed by twelve linear RGBA8 mip levels, 2048 × 1024 through 1 × 1.
- The header identifies the layout, field version, seed, radius and dimensions; runtime rejects a mismatch.
- R stores linear albedo divided by 0.32; G/B store east/north slopes as `(byte - 128) / 127`; A is opaque.
- Each payload is 11,184,812 bytes; the fixed three-slot residency budget is 33,554,436 bytes before GPU allocation alignment.
- `airless-provenance.json` records source and cooked-file hashes.
- These surfaces use no lunar photograph or painted lighting.

**Retained reference assets, no longer loaded by the engine**

**Credit:** NASA's Scientific Visualization Studio; Ernie Wright; LRO/LROC/LOLA instrument teams.

- Source: [NASA CGI Moon Kit](https://svs.gsfc.nasa.gov/4720/).
- [SVS usage policy](https://svs.gsfc.nasa.gov/help/) places its content in the public domain unless identified otherwise; these maps have no separate restriction.
- No NASA endorsement is implied.
- `manifest.json` records the exact downloads, source hashes, dimensions and cooked hash.
- `lunar.rgba8mips` and `manifest.json` retain the previous reference cook and provenance.
- Rebuild with `python tools/prepare_celestial.py`.
- R: relative linear albedo, encoded over 0--2 and normalized to unit spherical mean.
- G/B: east/north height slopes from LOLA, encoded as `(byte - 128) / 127`.
- A: normalized elevation preview; not used for geometry.
- Twelve linear-field mip levels, 2048 × 1024 down to 1 × 1; 11,184,812 bytes.
