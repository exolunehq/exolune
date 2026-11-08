# Optical glare

**Current behaviour, 2026-11-07**
- Enabled in normal rendering, including direct executable launch.
- `MYPLANETENGINE_GLARE=0` disables it for inspection.
- Diagnostic views bypass the pass.
- The linear HDR scene feeds the existing downsample/upsample pyramid before temporal smoothing and tone mapping.
- The final atmospheric transmission and real body depth have already occluded or attenuated the source.
- Stellar visibility reads the resulting veiling luminance, so a bright source reduces nearby stellar contrast.
- Stellar point images retain their own integrated point-spread response after this pass.

**One optical law**
- Distant glare falls as `s E / theta²`, with theta in degrees.
- `GLARE_STRAYLIGHT = 0.3` square degrees per steradian.
- Each octave redistributes `2 pi ln(2) (pi / 180)² s` of the light.
- The sharp image keeps the complementary energy.
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
