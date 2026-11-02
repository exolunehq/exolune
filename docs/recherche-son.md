# The sound of the ship

**World audio and footsteps:** [spec-marche-ambiances.md](spec-marche-ambiances.md) extends the same XAudio2 output with credited CC0 / CC BY 3.0 recordings and contextual procedural layers.

**The goal:** a ship that understands each other. The engine follows the required thrust, the stabilizers blow when we roll or slide, the wind rises in the atmosphere.

**The condition, 2026-10-29:** in place, to be judged in flight.
- **Choice:** procedural synthesis, played by XAudio2. No sound files, no dependencies.
- **The code:** `MyPlanetEngine/Audio.h` and `Audio.cpp`. One call per frame, `mAudio.Update(ShipSound)`, filled in `D3DApp::UpdateShip`.
- **Voices:** the engine, three groups of stabilizers (roll, side slip, climb and descent), the wind.

## State of the art

**Flight and space games:**
- **Star Citizen:** Wwise, after FMOD. Layer loops driven by parameters; the propeller parameter was still called "RPM". The main engine is lowered when the superprop talks ([Audio Update, 2015](https://robertsspaceindustries.com/comm-link/transmission/14853-Star-Citizen-Audio-Update)).
- **Elite Dangerous:** the modules mounted change the sound of the ship, which is judged by ear ([Jose Castro, Frontier](https://forums.frontier.co.uk/goto/post?id=176161)). The engine sound follows the required thrust, not the speed.
- **MSFS:** Wwise. Recorded loops at multiple speeds, blended on a blend track according to the RPM, with a height curve ([Engine Audio Setup](https://docs.flightsimulator.com/msfs2024/retail/sound/aircraft-audio/engine-audio-setup/)).
- **X-Plane 11 and 12:** FMOD Studio, events driven by datarefs ([Using FMOD with X-Plane](https://developer.x-plane.com/article/using-fmod-with-x-plane/)).
- **No Man's Sky:** Wwise, with VocAlien, a plugin for synthesizing creature voices, and Pulse for music ([Paul Weir, Audiokinetic](https://www.audiokinetic.com/en/blog/behind-the-sound-of-no-mans-sky-a-qa-with-paul-weir-on-procedural-audio); [GDC 2017](https://gdcvault.com/play/1024067/The-Sound-of-No-Man)).
- **Everspace 2:** sounds created with synthesizers (Phase Plant, Vital, modular) and then played in loops ([Lukas Deuschel, Rockfish](https://everspace-game.com/rockfish-games-senior-sound-designer-lukas-deuschel-interview/)).
- **The known defect:** a sound related to speed rather than thrust. Players raise it ([Space Engineers 2](https://support.keenswh.com/spaceengineers2/pc/comments/93488/vote/toggle)).

**Piloted engine techniques:**
- **Faded loops:** some loops recorded at fixed speeds, faded and transposed according to the parameter. The rule of simulators. Simple, but the transposition is clear and the loops repeat.
- **Granular:** grains taken from a recording in upward rpm, replayed at the desired speed. No audible loop. Crankcase REV and SoundSeed Grain, paid plugins from Wwise ([REV](https://www.audiokinetic.com/products/plug-ins/crankcase-rev/), [granular modelling](https://www.audiokinetic.com/engine-sound-modeling-from-sampling-to-granular-synthesis-in-wwise)).
- **Procedural synthesis:** sound as a process, noise functions filtered and oscillators. The Farnell reactor: turbine and combustion ([Designing Sound, Practical 24](https://mitp-content-server.mit.edu/books/content/sectbyfn/books_pres_0/8375/designing_sound.zip/practical24.html)). Excellent for blows, wind, gas jets; more difficult for a real piston engine.

**The middleware against the API naked:**
- **FMOD and Wwise:** author tool, mixing, real-time parameters, plug-ins. Free under a budget ceiling, then paid; a SDK and one more editor.
- **XAudio2 nude:** shipped with Windows 10 and 11, in the SDK. Voice, filters, reverb, spatialization X3DAudio. Nothing to write for the author, everything to write for the sound.

## Free sound libraries

- **Freesound:** thousands of gas jets, blows, reactors; licenses CC0, CC-BY, CC-BY-NC to sort one by one ([licences](https://freesound.org/help/faq/#licenses)). Download after login.
- **OpenGameArt:** CC0 and CC-BY mostly, uneven quality ([engine sounds](https://opengameart.org/content/space-ship-engine-sounds)).
- **Sonniss GDC:** tens of GB every year, royalty free, commercial use, no attribution; no redistribution of the files alone, so not in a public repository ([GDC 2024](https://gamefromscratch.com/sonniss-27-5gb-sound-effect-giveaway-at-gdc-2024/)).

## Audio libraries for C++ on Windows

- **XAudio2:** native, `xaudio2.lib`; nothing to add to the repository.
- **miniaudio:** a header, public domain or MIT-0; decoders WAV, FLAC, MP3, node graph ([miniaud.io](https://miniaud.io/)).
- **SoLoud:** zlib/libpng; filters, sfxr synthesis, multiple sources ([solhsa.com/soloud](https://solhsa.com/soloud/)).
- **OpenAL Soft:** LGPL, so a DLL to be delivered; 3D and HRTF ([openal-soft.org](https://openal-soft.org/)).

## The choice

**The rule:** the prettiest first, then the least dependencies.

- **The procedural synthesis sounds better here:**
  - **The ship is imaginary,** no recording is the truth. The three sounds are blows: roar, gas jets, wind. The filtered noise functions make them well.
  - **The push range is continuous:** no loop to transpose, no connection between regimes, no repetition.
  - **Every spray is different:** filter and duration drawn randomly, no bank of variants.
- **Least dependencies:** XAudio2, already in Windows. No middleware, no library, no file in `assets/`.
- **What would change your mind:** a precise mechanical sound, a start or a valve click. Then a recording CC0, loaded in WAV by XAudio2.

## Implementation

**The stream:** a voice source XAudio2, 48 kHz stereo floating. The `OnVoiceProcessingPassStart` callback calculates the samples requested, on the XAudio2 wire. The game only passes atomic targets; the synthesis smooths them, without cracking.

**Engine:**
- **The thrust,** from 0 to 1: the wheel pitch on 30, to the power 2,5. At the 20ᵉ level, 100 km/h near the ground, the engine is in third; fully at the 30ᵉ. The speed, however, follows the altitude up to that of light: sound follows only the gases.
- **The gas only, not the acceleration:** the difference between desired and real speed, tried first, made the engine growl at the first turn and long after the gas cut off, the time that the ship slows down.
- **The answer:** 0,25 s at the rise, 0,12 s at the cut.
- **Three layers:** a brown noise rumbling, a bumble bee with some harmonics of 32 to 75 Hz that waves, a filtered white noise breath whose frequency rises with the push.
- **At slow motion,** a barely audible purr remains.

**Stabilizers:**
- **A “pschit” at each press,** then a breath held lower as long as the key remains, and a tail of 80 ms at release.
- **The noise white passed high,** frequency shot at each throw. The rolling left and right, the sliding on the side of the nozzle that blows; the climb in the center.

**Wind:**
- **Speed reduced to sea level,** as for the canopy glass. The volume is proportional to it: audible from 30 km/h, clear at 100 km/h, full at 150 m/s. As in real life, at 100 km/h the wind already covers a low-speed engine.
- **The volume follows the density of the air,** scale height 8 km: the rare air carries little sound. It takes this factor: the speed increases with altitude, and the speed brought back to sea level remained strong at 50 km. The wind goes out towards 30 km, regardless of the speed.
- **A noise bandpass** that increases in frequency with speed, and slow bursts.

**The view:**
- **In the cockpit,** everything goes through a low-pass filter: you hear through the hull. The grave rumbling remains, the breath is choked.
- **Outdoor,** full spectrum.

**Settings:** the gains and frequencies are in the head of `Audio.cpp`.
