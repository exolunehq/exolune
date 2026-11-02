# Walking and environmental audio history

**2026-11-01 · Replaced footstep prototype**
- User feedback: contacts sounded poor and did not consistently match the visible ground.
- Five TinyWorlds CC0 takes served all surfaces; the soil fallback used `mud02.ogg`.
- Sand and snow reused filtered gravel; rock and gravel shared a random selector.
- Rain selected wet/mud contacts without evidence of a puddle.
- Surface probing disabled textures and height blending, at 0.5 m and up to 10 Hz.
- A 0.22 threshold compared partial material shares without residual soil or consistent coating coverage.
- Initial bank: 11 files, 1,241,082 bytes on disk, approximately 2.5 MB decoded.
- These choices were replaced by six real material banks and exposed coating areas at 0.12 m.
- Initial source: [TinyWorlds, Different steps](https://opengameart.org/content/different-steps-on-wood-stone-leaves-gravel-and-mud), CC0 1.0.
- Current implementation, limits and review: [spec-marche-ambiances.md](../spec-marche-ambiances.md).
