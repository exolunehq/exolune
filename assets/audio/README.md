# Environmental recordings

**Credits and licenses**
- **`step-soil-*.wav`:** congusbongus, [Footsteps on different surfaces](https://opengameart.org/content/footsteps-on-different-surfaces), [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). Mastered from swuing, [footstep-grass.wav](https://freesound.org/people/swuing/sounds/38874/), CC BY 3.0. The pack describes this soft contact as grass, dirt or leaves.
- **`step-gravel-*.wav`:** congusbongus, the same mastered pack, CC BY 3.0. Original recordings: Ali_6868, [Gravel Footsteps](https://freesound.org/people/Ali_6868/packs/21608/), [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
- **`step-rock-*.wav` and `step-sand-*.wav`:** Fantozzi, [Fantozzi's Footsteps (Grass/Sand & Stone)](https://opengameart.org/content/fantozzis-footsteps-grasssand-stone), CC0 1.0; uploaded by qubodup. Six original FLAC takes per material.
- **`step-grass-*.wav`:** SilentStrikeZ, [Grass Footsteps](https://freesound.org/people/SilentStrikeZ/sounds/389625/), CC0 1.0. Six contacts from the public high-quality preview.
- **`step-snow-*.wav`:** florianreichelt, [Walking on fresh Snow](https://freesound.org/people/florianreichelt/sounds/453168/), CC0 1.0. Six contacts from the public high-quality preview.
- **`bird0.wav`–`bird5.wav`:** isaiah658, [Ambient Bird Sounds](https://opengameart.org/content/ambient-bird-sounds), CC0 1.0. Six distinct 1.8-second phrases; unchanged by the footstep revision.
- Keep these credits with redistributed recordings; original pack notices are preserved in `licenses/`.

**Changes**
- Contacts: mono PCM16 at 48 kHz; 55 Hz high-pass and 16 kHz low-pass; DC removal, contact extraction and short edge fades.
- One gain per material preserves differences between takes; peak stays below 0.72.
- Sand and snow use their own recordings; rock and loose gravel remain separate.
- Playback chooses six takes without immediate repetition, with ±1.5% pitch variation and subtle alternating pan.
- Birds retain their original peak normalization and edge fades.
- Air, rain, surf, insects, wetland calls and distant thunder use original procedural synthesis in `WorldAudio.cpp`.

**Rebuild**
- `python assets/audio/prepare.py`; development dependencies: numpy, ffmpeg and 7-Zip.
- Downloads are cached under ignored `x64/WalkingChecks/footstep-sources`; `--cache` and `--sevenzip` override the paths.
- Check source SHA-256 before conversion; `sources.json` identifies sources and generated WAVs.

**Runtime**
- Load the 42 shipped WAV files once, above the executable.
- No runtime decoder, download, account or environment variable.
