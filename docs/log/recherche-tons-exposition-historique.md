# Exposure history

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
