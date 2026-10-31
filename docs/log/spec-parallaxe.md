# Spécification : la parallaxe du relief des matériaux

Statut : première version faite le 2026-10-22, à juger en vol.

## Le constat

- **Le maillage ne porte une forme qu'à partir de huit mailles par longueur d'onde,** `MATERIAL_RELIEF_BAND`. Une marche de 2 m n'apparaît dans la géométrie qu'à une vingtaine de mètres.
- **Avant, les pixels ne la montrent que par l'éclairage.** Le relief est plat, seule la lumière le dessine.
- **En approchant, la forme surgit donc dans les derniers mètres :** les corniches se creusent, et l'utilisateur voit les sommets bouger.

## Le principe : la profondeur dans les pixels, avant le maillage

**La parallaxe par occultation,** la technique standard des moteurs : le pixel suit son rayon de vue dans le relief et prend les matériaux au point où le rayon touche la surface.

- **Elle ne montre que le relief que le maillage ne porte pas encore :** le relief entier, moins sa part portée, `gMeshReach` fois le relief filtré à la maille. À mesure que le maillage le prend, la parallaxe s'efface d'elle-même. Le passage de l'un à l'autre ne change donc pas la forme vue.
- **Le relief suivi :** celui de la roche, la tuile de 8 m, la tuile de 64 m et la colonne stratigraphique. Ce sont eux qui portent les corniches. Le sable, l'herbe et les éboulis gardent leur relief dans l'éclairage seul : quelques centimètres.
- **Pour le coût :**
  - la famille de roche dominante seulement ;
  - le plan de projection dominant seulement ;
  - douze pas, puis un affinage ;
  - seulement sur la roche, et seulement là où le relief résiduel dépasse le pixel.
- **Ce qui ne change pas :** la profondeur écrite, donc les silhouettes contre le ciel, qui restent celles du maillage. Elles viendront avec lui.

## La mesure

- **La vue de la corniche,** de `2182.0 31.16045 8.58814 1.9 -17.1` à `2181.5 31.16051 8.58812 2.3 -11.8` : la forme doit se voir dès 11 m et ne plus surgir.
- **Le banc de tremblement** sur les mêmes positions.
- **Le coût de rendu** au constat, au site de la roche et à la corniche.

## Critères de validation

- **La corniche a sa profondeur dès 11 m,** et le passage au maillage ne se voit plus.
- **Pas de tremblement en plus.**
- **Coût :** moins de 1 ms de rendu en plus.

## Résultats de la première version

- **La corniche a sa profondeur dès 11 m :** le creux sous le replat se voit déjà, comme à 5 m. Sans parallaxe, il n'apparaissait qu'avec la géométrie.
- **Ce qui est suivi :** la tuile de 64 m et la colonne stratigraphique, moins leur part portée par le maillage. La tuile de 8 m, quelques dizaines de centimètres, reste dans l'éclairage.
- **Huit pas,** puis une interpolation du point de contact. La parallaxe s'efface là où elle déplacerait le point de moins de trois à six pixels.
- **Coût,** même build avec et sans parallaxe, au minimum de trois passages : +0,8 ms au constat, +1,0 ms à la corniche et au site de la roche, rien à 56 km. À la limite du budget.
- **Tremblement :**

| Avec / sans lissage | Sans parallaxe | Avec |
|---|---|---|
| Corniche, 11 m | 0,17 / 0,89 | 0,22 / 1,41 |
| Corniche, 5 m | 0,31 / 1,84 | 0,34 / 2,12 |
| Constat | 0,39 / 2,78 | 0,40 / 2,83 |

- **À faire si le coût gêne :** un seul calcul de la colonne par pas au lieu d'un par famille, ou moins de pas pour les pixels lointains.

## L'outil : des bancs qui ne prennent plus le focus

- **Les captures et le banc de tremblement rendent sans afficher la fenêtre.** L'exécutable écrit son titre dans `<capture>.txt`, que `tools/capture.ps1` relit.
- **Les mesures de coût se comparent entre builds de même génération :** une fenêtre cachée n'est pas limitée par la synchronisation verticale, ce qui change les temps GPU mesurés.
