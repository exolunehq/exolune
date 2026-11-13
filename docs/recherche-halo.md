# Optical glare

**Current behaviour, 2026-11-12**
- Enabled in normal rendering, including direct executable launch.
- `MYPLANETENGINE_GLARE=0` disables it for inspection.
- Diagnostic views bypass the pass.
- The linear HDR scene feeds the existing downsample/upsample pyramid; the composite image itself is left untouched.
- The tone map spreads the summed pyramid over the image after temporal smoothing, at the observer's exposure: the local adaptation never amplifies the Sun's veil. A small share of the veil enters what that adaptation reads (`LOCAL_ADAPTATION_GLARE`, `recherche-tons-exposition.md`).
- The final atmospheric transmission and real body depth have already occluded or attenuated the source.
- Stellar visibility reads the sky without the veil: a bright source in view no longer erases the stars and the galaxy; the veil only adds over them (2026-11-12, a cinematic choice).
- Stellar point images retain their own integrated point-spread response after this pass.

**One optical law**
- Distant glare falls as `s E / theta²`, with theta in degrees.
- `GLARE_STRAYLIGHT = 0.3` square degrees per steradian.
- Each octave redistributes `2 pi ln(2) (pi / 180)² s` of the light.
- The sharp image keeps the complementary energy, `1 - GLARE_OCTAVE x levels`, in the tone map.
- There is no luminance threshold and no added light.
- Thirteen-tap downsampling and tent upsampling keep the response smooth between scales.
- The finite Sun now supplies the source through `CelestialBodies.hlsl`.
- Moon and planet discs use the same optical pass; their local display adaptation remains separate.

**Limits and review**
- Sources outside the rendered image do not yet produce optical glare.
- Edge clamping retains some light that would leave the frame.
- This is a lens-like display response, not a full retinal model.
- Fixed output dither reduces dark-gradient contouring.
- Functional review: `tools/tests/2026-11-07-ciel.txt`, especially Sun, moonlit night, lunar approach and daylight.
- Historical measurements were not rerun for this change; no benchmark was requested.
- Current celestial integration: `spec-ciel-celeste.md`.
- Superseded opt-in behaviour, research alternatives, intermediate measurements and source bibliography: `log/recherche-halo-historique.md`.
