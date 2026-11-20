# Flight, cockpit and suit audio

**Listener**

- One world-space listener receives measured propulsion, equivalent airspeed, heat, current habitat and walking exertion once per game frame. [Flight and suit specification](spec-vol-immersion.md)
- Cockpit and bare pilot views hear a filtered exterior mix, air circulation, structure-borne propulsion and the radio receiver.
- Chase hears exterior propulsion in proportion to local air density.
- Detached views hear the local environment.
- A walking suit carries the receiver and regulator through a vacuum. Its external microphone retains nearby footsteps and filters the habitat.
- Enter or the Radio button requests one French acknowledgement. Repeated presses during reception leave the current sentence playing.

**Sources and implementation**

- Flight simulators drive their sound events from measured engine state, apply a separate interior filter and trigger controls as discrete events. Exolune applies that design directly to its XAudio2 output. [Laminar Research](https://developer.x-plane.com/article/using-fmod-with-x-plane/)
- A single 48 kHz stereo stream combines production recordings and the original synthesizers. Initialization reads resident PCM. The callback only reads controls and mixes bounded voices. [Microsoft callback guidance](https://learn.microsoft.com/en-us/windows/win32/xaudio2/xaudio2-callbacks)
- Six ElevenLabs Sound Effects loops supply propulsion, cabin circulation, aerodynamic flow, entry buffeting, foliage and helmet breathing. A French ElevenLabs voice supplies the receiver. The manifests identify their exact takes, source hashes, nominal gains and cooked PCM. [Audio bank](../assets/audio/README.md) [ElevenLabs Sound Effects](https://elevenlabs.io/docs/overview/capabilities/sound-effects)
- The contiguous playback rate of each loop follows its own source. Rate, gain and cutoff approach their targets smoothly. The cockpit filter keeps hull vibration audible. A short attenuation of other sounds keeps radio speech intelligible.
- The Classic and Fighter share a reactor texture over their procedural engine and maneuvering jets. The Navigator retains its resonant propulsion design. [Navigator propulsion](spec-navigateur-cockpit-son.md)
- Hull airflow follows equivalent airspeed. Entry buffeting needs both the flight model's thermal response and air loading. Ground wind, foliage, surf and wildlife follow sampled climate, vegetation, terrain and day. [World audio](spec-marche-ambiances.md)
- Ground distance drives walking effort with a 1.8 s rise and 4 s recovery. Effort controls regulator level and playback speed up to 1.32 times the resting rate.
- Ship volume governs flight layers and cockpit radio. Ambience governs foliage, regulator and suit radio. Footsteps retain their own volume. Y controls the master.

**Verification**

- `python assets/audio/immersion/prepare.py --check` compares every local production WAV with its receipt and checks channel layout and loop joins.
- `tools/tests/check_walking.ps1` exercises the production mixer without a sound device. It writes a 21 s stereo audition to `x64/WalkingChecks/immersion-vol-casque.wav`.
- `tools/tests/check_navigator_sound.ps1` checks propulsion continuity, finite output and exterior vacuum attenuation.
- In the audition, the engine builds into entry, an exterior view crosses into vacuum, then a pilot walks beneath trees and receives a radio reply.
- The pilot's judgement of wind balance, regulator loudness and radio intelligibility belongs to the in-flight review. [Earlier ship sound experiments](log/recherche-son-historique.md)
