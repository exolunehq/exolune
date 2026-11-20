# Environmental and vehicle audio

**Flight and suit bank**

- The six ambient layers and French radio reply run locally at 48 kHz. Reactor, breath and radio use mono. Cabin, airflow, entry buffeting and foliage retain stereo.
- The ElevenLabs flow contains the seven generated takes. The radio uses the French library voice Antoine and the script “Ici le relais. Votre signal est clair. À vous.” [Production flow](https://elevenlabs.io/app/flows/HLq6tgk5WcJPC1FliFbW)
- The game and cooker both read channel counts from `immersion/bank.ini`. The mixer reads its gain for each role. The file records each model, prompt, generation ID and source hash. [Manifest](immersion/bank.ini)
- The production archive is `E:\ExoluneAssets\audio\vol-immersion-2026-11-20\masters`. Each `<role>.master` is the original ElevenLabs download.
- From another worktree, run `python assets/audio/immersion/prepare.py --masters "E:\ExoluneAssets\audio\vol-immersion-2026-11-20\masters"`. The cooker checks each source hash, joins the loops, shapes the radio and writes the same seven WAVs beside the manifest. Its default input is the local `x64/ImmersionAudio/masters` cache.
- Run `python assets/audio/immersion/prepare.py --check` to verify the cooked WAVs against their sample counts and SHA-256 hashes. [Cooked receipt](immersion/cooked.json)
- Game distributions may incorporate these effects into the production under the generating workspace's terms. The source repository holds the recipe and hashes. Isolated generated WAVs stay local. Commercial use depends on the plan at generation. [ElevenCreative terms, Exhibit 4](https://elevenlabs.io/creative-terms) [EEA account terms](https://elevenlabs.io/terms-of-use-eu)
- A source checkout synthesizes an original texture for each missing production take at startup. The receiver uses a two-tone acknowledgement in that configuration.
- Enter and the Radio button share a single receiver action in cockpit, bare pilot and walking views. [Runtime mix](../../docs/recherche-son.md)

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
- Load the 42 contact and bird recordings once from the first audio directory above the executable.
- No runtime decoder, download, account or environment variable.
