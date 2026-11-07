# Walking and environmental audio

**Status**
- Implemented on 2026-11-01; Release x64 and targeted controller/audio checks pass.
- Ground placement visually checked in tropical forest, desert, snow and a coastal plain.
- Ship return, keyboard/button mute and visible refusal above the sea checked.
- F10 reaches its route test without opening a modal Windows menu.
- Listening and the complete interactive route remain for user review.
- Footstep revision: six recorded material banks; textured coating selection and targeted PCM checks pass.
- Contact labels visually checked: grass in forest, sand in desert, snow on the plateau, bare soil on the coastal plain.
- Integration on current public main preserves its ship selection, cloud contrast and existing vegetation.
- Milestone: `jalon/2026-11-02-marche-ambiances`; vegetation authoring continues separately.

**Controls**
- J, or the upper-left Marcher/Vaisseau button, toggles walking and the saved flight view.
- Hold Alt or toggle M to release the cursor and click a button.
- WASD/ZQSD follows physical key positions; arrow keys also work.
- Shift runs; Ctrl crouches; Space jumps; H toggles the small walking bob.
- Mouse look is direct, without the flight stick or roll.
- Y, or the sound button, mutes and restores master volume.
- Tab and Backspace retain the ship views and free camera.
- Alt releases the cursor; Windows menu activation must not capture route keys or suspend the game loop.

**Disembarkation**
- Query current relief once, then place the eye instantly on dry ground beside the ship's projected position.
- Refuse submerged ground and slopes above 45 degrees; show a message in the action overlay.
- Hold the ship at its saved pose, with throttle and jets stopped.
- J returns to that pose from any walking distance.
- A ship left above the ground remains there; landing gear and landing animation are separate work.

**Controller**
- Standing eye: 1.68 m; crouched eye: 1.05 m.
- Walking: 1.5 m/s; running: 3.6 m/s; crouching: 0.75 m/s.
- Normalize diagonals; smooth acceleration and braking.
- Gravity: 9.81 m/s²; jump: 4 m/s at launch, approximately 0.8 m high.
- Substeps: at most 1/120 s; frame integration capped at 0.1 s.
- Sample a 9×9 grid of shared relief over 4×4 m, at 0.5 m spacing.
- Carry position, look and tangent velocity around the sphere in double precision.
- Interpolate the local height field; test a 0.25 m footprint and 0.30 m obstacle margin.
- Block steep ascent; retain motion along a blocked face.
- Keep ordinary descending slopes grounded; ledges start gravitational falls.
- Stop at unsampled or submerged ground.
- The footprint approximates height-field contact; it is not a full capsule sweep against arbitrary meshes.
- Trees, placed rocks and the hull currently have no solid collision; swimming is not implemented.
- Terrain generation, filtering and rendered geometry remain unchanged.

**Foot contacts**
- Trigger by actual grounded distance; no repeated steps while blocked or airborne.
- Stride: 0.78 m walking, 1.10 m running, 0.60 m crouching.
- Add a contact on sufficiently strong landings.
- Read `GroundMaterials` with material textures and height blending at a fixed 0.12 m contact footprint.
- Compose exposed areas in rendering order: soil/grass/sand, scree, rock, beach, snow.
- Normalize base soil shares; residual soil participates in selection.
- Select distinct soil, grass, loose gravel, hard rock, sand and snow recordings.
- Keep six takes per material; exclude the immediately preceding take in each bank.
- Mix at most two exposed materials; retain the second when it occupies at least 15% of their combined area.
- Use equal-power contact gains, ±1.5% pitch variation and subtle alternating left/right pan.
- Dampen wet contacts gently; rainfall alone never selects a puddle or mud sound.
- Invalid probes emit no fallback step.
- Show the dominant contact material below the walking buttons.

**Habitat and weather**
- Sample existing material and vegetation fields at a fixed physical footprint.
- Read climate winds through `Climate::At`.
- Read showers and cloud droplets through `WorldWeather.hlsli`, shared with canopy weather.
- Probe every walking frame and at up to 10 Hz in flight through the existing frame fence.
- Continuous layers: wind, leaves, liquid rain, nearby surf and warm-night insects.
- Sparse voices: recorded birds, procedural wetland calls and distant thunder under strong showers.
- Sun elevation drives day/night; cold, altitude, rain and habitat suppress inappropriate fauna.
- Ground layers fade over 120 m of clearance; outdoor sound follows atmospheric density.
- The cockpit attenuates and filters the exterior mix.
- Smooth habitat transitions; discard old-location calls after teleports.
- Animal calls retain world positions during playback.
- Stereo pan, distance attenuation and rear filtering follow listener motion.
- Calls are virtual ambience sources; they do not add visible or simulated animals.
- Surf uses sea/beach evidence and height as a proximity approximation.
- Wind shelter uses vegetation cover; acoustic terrain occlusion, diffraction, HRTF and geometric reverberation remain future work.

**Runtime**
- Keep XAudio2; add no middleware or runtime decoder.
- Load 42 shipped mono PCM16 recordings once, at 48 kHz: 36 foot contacts and six bird calls.
- Recording bank: 2,283,646 bytes on disk, approximately 4.6 MB decoded.
- Precompute wetland and thunder samples at startup.
- Bound transient playback to 12 voices and a 32-slot single-producer queue.
- The callback performs no file access, dynamic allocation or locking.
- Skip ship synthesis after its fade reaches silence.
- Add no per-frame CPU/GPU wait; disembarkation performs one explicit ground query.
- Automated captures and films remain silent; ordinary automated views skip the probes.
- Missing recordings fail explicitly; no audio device leaves the game usable.
- No performance or quality benchmark was requested or run.

**Mix settings**
- Default gains: master, footsteps, ambience and ship all at 1.
- `MYPLANETENGINE_AUDIO="1 1 1 1"` sets these gains independently in [0,1].
- A local executable profile may use `[Audio]` and `Volumes=1 1 1 1`.
- No variable or profile is required for walking or sound.

**Review**
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Build -NoLaunch
powershell -NoProfile -ExecutionPolicy Bypass -File tools\tests\check_walking.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Parcours tools\tests\2026-11-02-marche-main.txt -Resolution fenetre
```
- F1–F12 cover forest, night, showers, desert, steppe, shore, snow, slopes, sea, poles and orbit.
- The optional sixth pose token `marche` starts a route view on exact ground.
- Check stopping, diagonals, jumps, crouching, steep contact, mute and ship return at several locations.
- Check birds move across stereo when turning; sea and orbit should have no dry-land fauna.
- Match the contact label and audible material at several sites; cross visible coating boundaries while walking.
- The focused checks write isolated six-step auditions to ignored `x64/WalkingChecks/pas-*.wav`.
- Initial prototype choices are archived in `log/spec-marche-ambiances-historique.md`.

**Research and decision**
- [Microsoft XAudio2 callbacks](https://learn.microsoft.com/en-us/windows/win32/xaudio2/xaudio2-callbacks): bound real-time work; avoid storage, blocking and synchronization in callbacks.
- [NVIDIA character controllers](https://nvidia-omniverse.github.io/PhysX/physx/5.3.0/docs/CharacterControllers.html): kinematic control, slope limits and contact handling provide the FPS reference.
- [miniaudio resource management](https://miniaud.io/docs/manual/): asynchronous decode and streaming help large banks; this small resident PCM bank needs neither.
- [Microsoft audio accessibility](https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/105): independent category gains.
- Choice: continuous environmental layers plus sparse spatial recordings, driven by existing world data.
- CC0 and CC BY 3.0 recording credits and reproducible conversion: `assets/audio/README.md` and `sources.json`.
