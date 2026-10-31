# Historique : la hauteur d'ombre sur une grille polaire

Étape 1 des rayons de soleil, du 2026-10-24, tag `piste/rayons-soleil`. Remplacée le 2026-10-25 par la hauteur d'ombre marchée à chaque sommet du maillage, avec l'horizon des ombres portées (`../recherche-rayons.md`, tag `piste/ombre-unique`).

## La grille (`SunShadow.hlsli`)

- 512 directions sur 512 rayons, autour du centre de la face du maillage, jusqu'à la portée de ses anneaux.
- Les rayons croissent en proportion de la distance au-delà d'un rayon intérieur, la demi-largeur de la face ou 1 km. Une cellule couvre 1,2 % de sa distance, près du 1 % des anneaux.
- Toutes les directions sont calculées : un relief hors de l'image projette son ombre dans l'image.

## Les deux passes, à chaque image

- **Le relief (`SunShadowTerrain.hlsl`) :** l'altitude du terrain en chaque point de la grille, filtrée à la cellule comme le maillage, `MESH_BAND_LIMIT`.
- **La marche (`SunShadow.hlsl`) :** de chaque point, une marche vers le soleil sur la sphère, d'une demi-cellule par pas. La hauteur d'ombre est la plus haute altitude cachée par un point du relief : h cos φ − 2R sin²(φ/2) − (R + h) sin φ tan θ, pour un relief h à l'angle φ, un soleil à la hauteur θ. Elle s'arrête quand rien de plus haut que `MAX_TERRAIN_HEIGHT` ne peut plus cacher le soleil.

## Pourquoi elle est partie

- **Deux sources pour une ombre :** la grille recalculait le relief et marchait vers le soleil, quand la passe `Horizon.hlsl` marchait déjà, à chaque sommet, sur les hauteurs de l'image.
- **Son relief n'était pas celui de l'image :** une autre grille, d'autres cellules.
- **Son coût :** relief 0,50 à 0,67 ms, marche 0,27 à 0,37 ms.

## Ses mesures

- **Coût,** minimum sur les images, RTX 4070 Ti, 1280 × 720 : relief 0,50 à 0,67 ms, marche 0,27 à 0,37 ms, lecture dans l'atmosphère 0,02 à 0,09 ms.
- **Tremblement,** avec et sans lissage : pic à 14°, 0,04 / 0,34 → 0,06 / 0,46 ; vallées à 9°, 0,06 / 0,40 → 0,06 / 0,44 ; aiguille à 11°, 0,04 / 0,30 → 0,05 / 0,34. L'air seul, sans le sol : 0,05 → 0,09 sans lissage, aux bords des faisceaux, et 0,01 inchangé avec.
- **Rotation de 1° :** l'air seul, ramené sur l'image précédente, s'écarte de 0,41 avec l'ombre, 0,43 sans.
- **La résolution :** une grille de 256 × 256 abaissait les aiguilles, l'air devant le haut d'un pic restait au soleil et cette bande tremblait. 768 × 768 ne changeait presque plus l'image, pour 2,4 ms.
