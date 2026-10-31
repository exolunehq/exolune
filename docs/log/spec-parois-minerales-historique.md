# Historique des parois minérales

**Les sections dépassées de `../spec-parois-minerales.md`,** sorties le 2026-10-30. L'état présent y est.

- **Les options de la voie rendu,** du 2026-10-23 : la photo de falaise est restée.
- **Les bandes cassées et les correctifs du premier vol :** les failles, `STRATA_PLATE_RISE`, `STRATA_PLATE_TILT`, `STRATA_FAULT_ZONE`, l'ondulation `STRATA_WANDER` et le granite à part, `MASSIVE_TILE`, sont retirés le 2026-10-24 avec les familles de roche, `jalon/16-une-roche`. Les strates au pixel restent.
- **Le filtre d'érosion,** mis de côté : tag `piste/erosion-filtre`.

## La voie rendu, les options du 2026-10-23

Ce qui rend une paroi minérale de 100 m à 1 km sans toucher la forme. Les pixels y couvrent de 8 cm à 1 m.

| Option | Ce qu'elle apporte | Couche | Coût |
|---|---|---|---|
| **1. Bandes cassées** : plaques de 50 à 300 m qui décalent et inclinent les strates, épaisseurs variables, couleurs par grandes masses | fin des rayures continues | couleur | deux Voronoi par pixel |
| **2. Coulures et vernis** : traînées sombres dans le sens de la pente, sous les corniches | la structure verticale des vraies parois | couleur | presque rien |
| **3. Diaclases** : fractures verticales, en normale et en cavité | blocs, arêtes, ombres fines | normale | un Voronoi anisotrope |
| **4. Photos de falaise** : `marble_cliff` de Poly Haven, 4 à 20 m, en triplanaire, pavées sans répétition, recolorées par les strates | la matière minérale réelle de 1 à 20 m | couleur et normale | une tuile et des lectures ; téléchargement à autoriser |
| **5. Ombre des creux** : screen-space shadows | ravines et alcôves noires | ombre | une passe plein écran |

**Choix de l'utilisateur, le 2026-10-23 :** la photo de falaise d'abord, l'option 4.

**La géométrie de proximité est désactivée pendant ce travail,** `MATERIAL_RELIEF` = 0 et `WALL_RELIEF` = 0 : le rendu se règle sur la seule géométrie de complexplanet (`../geometrie.md`).

**La mesure :**
- vues de parois à 100 m, 300 m et 1 km, à côté des photos `cible-*.jpg` ;
- bancs de tremblement, de descente et des crêtes ;
- coût du rendu.

## Résultats de l'option 1 : les bandes cassées

![Photo de falaise seule, puis bandes cassées : paroi raide, montagne à 45°, de plus près, corniche](../images/parois-bandes.jpg)

- **Les plaques :** des failles presque verticales découpent les strates en plaques d'environ 128 m, un Voronoi de la grille de la planète aux cellules quatre fois plus hautes que larges. Chaque plaque relève les strates de ±20 m, `STRATA_PLATE_RISE`, et les incline de ±0,12, `STRATA_PLATE_TILT`. De part et d'autre d'une faille, les deux décalages se fondent sur deux pixels.
- **Les groupes :** les formations vont par groupes cinq fois plus épais, qui donnent la teinte. Une formation ne s'écarte plus que de 30 % de la teinte de son groupe, `STRATA_FORMATION_CONTRAST` ; les badlands gardent leurs bandes vives.
- **Couleur seulement :** la géométrie ne change pas. La colonne, la tuile de 64 m et la parallaxe suivent les mêmes strates décalées.
- **Ce qu'on voit :**
  - les bandes s'interrompent aux failles, décalées et inclinées ;
  - les couleurs changent par grandes masses ;
  - restent les fines lignes sombres des joints entre les bancs, désormais en tronçons.
- **Mesures :**
  - tremblement avec lissage 0,43 → 0,42 sur la paroi raide, 0,23 → 0,26 à 45° ; la corniche a changé de place, la vue n'est plus comparable ;
  - coût du rendu +0,1 à 0,3 ms, mesure bruitée par le GPU partagé ;
  - descente de la roche inchangée.

## Correctifs après le vol du 2026-10-23 : des bandes immobiles, un granite sans grillage

![En haut, deux positions à 10 m l'une de l'autre, failles de tous pendages puis failles verticales ; en bas, le granite avant et après](../images/parois-immobiles.jpg)

**Symptôme 1 :** à l'approche, les bandes se déplaçaient. Entre deux positions distantes de 10 m, `3624.7 26.66682 114.99606 25.8 46.0` et `3621.6 26.66686 114.99611 25.8 46.0`, plus rien n'était au même endroit.
- **Les plaques étaient étirées à la verticale à partir de l'ancre des bruits.** L'ancre saute de 64 m quand la caméra bouge, et les plaques se redécoupaient. Elles sont désormais un Voronoi 2D de la grille de la planète, sur ses deux axes les plus éloignés de la verticale : les failles restent presque verticales. Un essai à tous les pendages étalait les bandes en Z sur des dizaines de mètres, là où une faille longeait la paroi.
- **La géologie, le décalage des strates et les lentilles étaient calculés par sommet et filtrés par la maille.** Une maille couvre environ 13 pixels : leurs octaves apparaissaient à vue à mesure que les mailles rétrécissaient, jusqu'aux plis de 128 m et à leurs ±10 m. Ils sont désormais calculés dans les pixels et filtrés par la taille du pixel.
- **Les failles dessinaient un trait noir :** la forte pente de `s` dans la zone de faille était éclairée comme une marche. Elle ne sert plus qu'à adoucir les bancs, `gStrataFault`, sur une zone broyée de 30 cm, `STRATA_FAULT_ZONE`, ou deux pixels : la bande s'arrête à la faille et reprend décalée.

**Symptôme 2 :** des lignes encore droites. Les strates ondulent désormais de 2,5 m d'écart type sur 4 à 256 m, `STRATA_WANDER`, au lieu de 0,8 m sur 4 à 64 m.

**Symptôme 3 :** un grillage de fissures sur toutes les parois de granite, `3364.2 26.61429 115.05042 0.3 -179.4`.
- **La cause :** la tuile de 64 m du granite trace deux familles de fractures tous les 21 m, partout avec la même force. Elles se croisent en grillage.
- **Le correctif :** chaque fracture se montre par tronçons d'environ 16 m, le plus souvent faible, parfois profonde.
- **Au passage :** le granite et le basalte gardent leur propre tuile de 8 m, `MASSIVE_TILE`. Le passage de la roche litée à 12,8 m pour la photo les avait agrandis.

**Mesures :**
- les deux positions à 10 m l'une de l'autre montrent les mêmes bandes et la même faille ;
- tremblement avec lissage 0,26 → 0,22 à 45°, 0,34 → 0,28 sur le granite, 0,42 et 0,26 → 0,28 ailleurs ; le banc garde la caméra fixe et ne voit pas l'ancre sauter ;
- coût inchangé, mesure faussée par une instance de l'app ouverte ; descente de la roche inchangée.

## La voie géométrie, le filtre d'érosion

**Le filtre d'érosion, essayé le 2026-10-23,** tag `piste/erosion-filtre` :
- **Ce qu'il fait :** des ravines de 366 m à 11 m dans le relief lui-même, le long de la pente lissée sur 512 m, en 3D sur la grille de la planète.
- **Ce qu'il donne :** des couloirs sur les montagnes lointaines, des strates pliées en V dans les ravines ; de près, des ravines trop rares et trop fines.
- **Ce qu'il coûte :** +1,7 à 2,4 ms de calcul du terrain. Les trois évaluations de plus de complexplanet par sommet en sont la cause probable, non isolée.
- **Le tremblement avec lissage :** 0,61 → 0,95, 0,22 → 0,46, 0,16 → 0,52. Des creux arrondis sur deux mailles ont été écrits ensuite, non mesurés.
