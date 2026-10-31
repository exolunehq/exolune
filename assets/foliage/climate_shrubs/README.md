# Arbustes climatiques — 27 octobre 2026

- **Données :** six archétypes stylisés, deux ramifications distinctes par famille : boréal, désert, steppe, montagnard, tempéré et tropical. Les structures et les proportions varient ; elles ne prétendent pas représenter des espèces botaniques exactes.
- **Source des feuilles, écorce et cartes PBR :** [Searsia Lucida](https://polyhaven.com/a/searsia_lucida), James Ray Cock (modélisation), Jenelle van Heerden (photographie), [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). Les rectangles de feuilles, normales, occlusion et rugosité proviennent de `game_shrub` ; couleurs adaptées et atlas rééchantillonné.
- **Géométrie :** branches générées raccordées, cartes de feuilles distribuées sur les rameaux et orientées en trois dimensions. Chaque variante a sa propre graine et sa propre ramification. Aucun volume plein de feuillage n'est ajouté.
- **Budget :** 2 368 à 4 368 triangles ; deux tuiles de 512 × 512 par modèle. Les matériaux sont 0 pour les branches et 1 pour les feuilles.
- **Éclairage :** mêmes formats `FOLLIT01` et `FOLIL001`, six directions et seize rayons de ciel ; volumes 64³ et 60 vues d'imposteur 128² générés sur CPU.
- **Manifeste :** `shrubs.txt` liste les douze dossiers dans l'ordre des six familles, variante 0 puis 1. Le pin et le feuillu sont copiés sans modification depuis `volume_look_normals`.
- **Reconstruction :** après préparation de `game_shrub` et `volume_look_normals`, exécuter `python tools/foliage/arbustes_climatiques.py --preview`, inspecter `contact_cpu.png`, puis `python tools/foliage/arbustes_climatiques.py --final`. Dépendances : numpy, Pillow et numba.
- **Limite :** ces familles partagent la même source photographique de feuilles ; leur aspect en mouvement et en contexte doit être vérifié en moteur.
