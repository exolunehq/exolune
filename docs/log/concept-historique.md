# Historique du concept

**Les sections dépassées de `../concept.md`,** sorties le 2026-10-30. Elles datent d'avant le jalon 01, quand complexplanet n'était pas encore porté. Les branches qu'elles citent, `complex-planet`, `debug-zoom-planet` et `unity-tw-portage`, sont des branches distantes de 2025, hors de `main`.

## Les couches de bruit : état des sources

**Verdict : les couches complexplanet ne sont pas dans les sources.** Seules les briques de base et le premier sous-groupe sont portés.

**L'original** est `complexplanet.cpp` de libnoise : 1 996 lignes de C++.

- 12 groupes et 26 sous-groupes : continents, type de terrain, montagnes, collines, plaines, badlands, rivières, quatre groupes de mise à l'échelle, planète finale.
- 23 générateurs, 52 modificateurs, 18 combinateurs, 9 sélecteurs et 26 caches.
- Générateurs : 11 RidgedMulti, 6 Perlin, 3 Billow, 1 Voronoi, 2 constantes.

**Dans les branches du repo :**

| Fichier | Branches | Contenu | État |
|---|---|---|---|
| `Engine/Shaders/TerrainCompute.hlsl` | `complex-planet`, `debug-zoom-planet`, `unity-tw-portage` | Bruit de gradient libnoise avec ses constantes, Perlin, Billow, RidgedMulti | Briques de base faites. Voronoi absent. |
| `Engine/Shaders/ComplexPlanetHLSL.hlsl` | mêmes branches | Graphe complexplanet | Seul le sous-groupe « continents de base » est fait, puis un TODO. Turbulence écrite mais non branchée. |
| `Legacy/ComplexPlanet.cpp` | `debug-zoom-planet`, `unity-tw-portage` | Graphe décrit en C++ | Partiel : continents, type de terrain, base des montagnes, début des collines. Turbulence neutralisée. Des valeurs s'écartent de l'original : les collines utilisent un Perlin à 1211 au lieu d'un Billow à 1663 et d'un RidgedMulti à 367,5. |
| `Legacy/CudaKernels/NoiseKernels.cu` | `unity-tw-portage` | Perlin et Simplex 3D, fBm, ridge, billow, sélecteurs | Autre famille de bruits : portage du shader Unity de 2012, pas de libnoise. |

**Reste à faire :** porter le graphe complet en HLSL à partir de l'original.

**Attention à la licence.** `complexplanet.cpp` est sous GPL v2, libnoise sous LGPL. Porter le graphe tel quel fait du moteur une œuvre dérivée GPL s'il est distribué.

## Prochaine étape proposée

Un prototype minimal pour valider le concept avant d'investir dans le bruit :

1. Une face de 256 × 256 centrée sous la caméra, de taille k × altitude.
2. Un bruit simple, par exemple les continents déjà portés.
3. Une caméra libre de l'orbite au sol, avec l'altitude affichée.

But : voir de nos yeux le glissement du relief et le problème de l'horizon, puis choisir les remèdes.
