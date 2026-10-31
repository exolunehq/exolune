# Référence des nuages Wicked Engine

- Projet : [Wicked Engine](https://github.com/turanszkij/WickedEngine).
- Révision épinglée : `5433f0a6cb0ed9ddfd41b7742978d038eaff70de`.
- Licence : [MIT, texte original](LICENSE.txt).
- Noyaux étudiés et adaptés : `volumetricCloudsHF.hlsli` et `volumetricCloud_renderCS.hlsl`.

**Adaptation :** `MyPlanetEngine/Clouds.hlsli`, les nuages du jeu, en descend ; son en-tête porte la mention MIT. Il conserve les principes de formation par météo, profil vertical, forme Perlin-Worley et érosion, ainsi que l'intégration volumétrique et un éclairage approché. La double précision, la météo planétaire, les deux couches, la quadrature lointaine et l'intégration DX12 appartiennent à MyPlanetEngine.

**Textures :** aucune ressource ni aucun code de génération de Wicked Engine n'est importé. Les volumes de bruit viennent de TileableVolumeNoise (MIT, `NOTICE`), provenance dans `assets/clouds/manifest.json` ; la carte météo se calcule au démarrage sur le climat (`Climate::Weather`).

**Références citées par Wicked :** Schneider, *Real-Time Volumetric Cloudscapes* ; Högfeldt, *Convincing Cloud Rendering* ; Hillaire, *Physically Based Sky, Atmosphere and Cloud Rendering in Frostbite*. Elles ne constituent pas une validation de l'adaptation.
