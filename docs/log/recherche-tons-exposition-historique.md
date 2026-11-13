# Exposure history

**2026-11-12 and 2026-11-13: three local-adaptation rules — replaced by one local adaptation**
- **The bright-disc cap:** resolved bodies wrote a flag (`sunPart.a`, then `skyTransport.a`); the tone map capped their exposure at 8.
- **The night-hemisphere lift** (`NightHemisphereExposure`): above the air, each pixel of Exolune's night side took `NIGHT_LOCAL_ADAPTATION` of its own ground meter, in stops (`GroundExposure`).
  - Ramps: the camera's altitude from 20 to 80 km; the Sun from the terminator to 8.6° down; lift only.
  - 0.85 on 2026-11-12; 1 on 2026-11-13, once the moons' light was taken on Exolune.
- **The backlight rule:** the share fell to `NIGHT_BACKLIGHT_SHARE` = 0.82 with the Sun on the limb, whole again 16° away (`NIGHT_BACKLIGHT_ANGLE`), cut once the limb hid the Sun.
- **Rejected in flight, 2026-11-13:** at 37 000 km over a half-lit Exolune, the night side looked as bright as the day side, with a dark band at the terminator; ramps and cuts changed the image abruptly. The user asked for one simple, coherent system.
- **The prototypes of its replacement,** on the night views of `G:/ExoluneAssets/film-lune-ville-2026-11-12/lumiere` (sRGB p90 of the night side):
  - a blurred region, no edge awareness: thin crescents and limbs burnt white (p99 85 to 217); a 12.5-stop range left film 25 at 10;
  - a pixel never lifted more than 1.5 stops beyond its own light, larger regions: the crescents held, but a large dark disc rose more than a small one, film 33 over film 25, and a blurred region darkens the night next to the day;
  - the joint bilateral region: no halo, no band; with 1.5e-5 of the glare, the backlight barely showed;
  - 6e-5 of the glare: the night darkened towards the Sun, but film 25 fell to 8; 3e-5 kept.

**2026-11-07 asymmetric temporal exposure experiment — rejected**
- At the reported 1,815 km sunrise, a small displacement uncovered the solar crescent and rapidly darkened the planet on screen.
- The experiment followed `log2(exposure)` with one GPU state, shared by tone mapping and cockpit dimming at `t58`.
- Exponential time constants were 0.35 s towards light and 2.5 s towards darkness; about 95% convergence in 1.05 s and 7.5 s.
- These were display settings for flight, not a complete retinal adaptation model.
- Play used elapsed time independently of the physics clamp and weather pause; CINE used `1/fps`.
- Initialization and independent batch still jobs started at local illumination; interactive jumps, view changes and TAA resets preserved the state.
- Physical illumination, settled compensation, tone curve, glare, HDR history and geometry were unchanged.
- Release x64, shaders and CPU checks passed, including monotonic convergence and equal response at 30/60/144 Hz and irregular steps.
- A 371-frame native sequence crossed the reported sunrise in both directions with frozen weather; its GPU trace confirmed both time constants and no resets or overshoot.
- Four cockpit controls retained detail at the two former overexposure positions and readable instruments during atmospheric day and moonlit night.
- The user judged the result worse in flight and explicitly requested a revert.
- Removed the temporal state, compute pass, bindings, shader files, functional checks and CINE exposure trace; restored the previous direct incident meter.
- The previous observer-altitude solar correction remains active; a ground sunset is not an orbital eclipse.
- Local experiment artifacts remain in `artifacts/adaptation-exposition-2026-11-07/transition`, including frames and `exposure.csv`; no benchmark was run.
- The experiment was never committed or tagged; the planned `piste/adaptation-exposition-2026-11-07` tag was cancelled.
- Current response: `../recherche-tons-exposition.md`; review positions retained in `../../tools/tests/2026-11-07-exposition-sans-lissage.txt`.

**Superseded on 2026-11-07**
- The incident meter clamped solar altitude to the horizon after sunset.
- Twilight and night therefore retained sunset exposure.
- The celestial prototype replaces this clamp with incident night illumination and a perceptual key.
- Current behavior: `../recherche-tons-exposition.md` and `../spec-ciel-celeste.md`.

**2026-11-07 orbital exposure regression**
- The initial celestial meter kept the sea-level solar beam at every camera altitude.
- It selected night exposure over the dark hemisphere even when the orbital observer remained in direct sunlight.
- The day side saturated; optical glare could veil the entire frame.
- Reported positions: `13545630.4 19.751087 -107.588831 84.22 55.72` and `19810521.3 -20.915709 157.285984 82.53 -126.67`; Sun `10 -5`.
- Solar elevation above the observer horizon was about 63.09 and 6.14 degrees, respectively.
- Replaced the sea-level direct-beam rule with an altitude-aware incident meter, retaining the existing compensation, glare strength and tone curve.
- Regression flight: `../../tools/tests/2026-11-07-exposition-orbite.txt`.
- A centre-ray-only orbital meter was also rejected: a visible solar crescent can still illuminate the observer after its centre ray enters the planet or dense air.
