# Wicked Engine cloud reference

- Project: [Wicked Engine](https://github.com/turanszkij/WickedEngine).
- Pinned revision: `5433f0a6cb0ed9ddfd41b7742978d038eaff70de`.
- License: [MIT, original text](LICENSE.txt).
- Kernels studied and adapted: `volumetricCloudsHF.hlsli` and `volumetricCloud_renderCS.hlsl`.

**Adaptation:** `MyPlanetEngine/Clouds.hlsli`, the game's clouds, derives from it; its header carries the MIT notice. It retains the principles of weather-driven formation, vertical profile, Perlin-Worley shape and erosion, as well as volumetric integration and approximate lighting. Double precision, planetary weather, the two layers, distant quadrature and DX12 integration belong to MyPlanetEngine.

**Textures:** no Wicked Engine resources or generation code are imported. The noise volumes come from TileableVolumeNoise (MIT, `NOTICE`), with provenance in `assets/clouds/manifest.json`; the weather map is computed at startup from climate (`Climate::Weather`).

**References cited by Wicked:** Schneider, *Real-Time Volumetric Cloudscapes*; Högfeldt, *Convincing Cloud Rendering*; Hillaire, *Physically Based Sky, Atmosphere and Cloud Rendering in Frostbite*. They do not constitute validation of the adaptation.
