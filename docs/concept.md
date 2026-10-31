# Concept : la face de cube qui suit la caméra

Statut : référence. Validé et en place depuis le jalon 01 ; il remplace le maillage radial « toile d'araignée » de `log/general_spec.md`.

## En une phrase

**On ne génère qu'une grille : une face de cube centrée sous la caméra, projetée sur la sphère, qui rétrécit quand on descend.** Son relief est recalculé à chaque frame par le relief tectonique d'Exolune, évalué dans le repère fixe de la planète.

Rappel de l'objectif : une planète en taille réelle, du vol orbital jusqu'au sol, sans aucun chargement de modèle.

## Le pipeline, à chaque frame

1. **Nadir.** On trace la droite du centre de la planète à la caméra. Son intersection avec la sphère est le nadir.
2. **Orientation.** On tourne le cube pour qu'une de ses faces regarde la caméra. Elle est alors centrée sur le nadir.
3. **Taille.** Au départ, c'est une face entière : elle couvre 45° de part et d'autre du nadir. Plus la caméra descend, plus on réduit la face.
4. **Sphérisation.** Chaque vertex est normalisé par rapport au centre du cube. On obtient une direction sur la sphère.
5. **Élévation.** On évalue le bruit sur cette direction, exprimée dans le repère fixe de la planète. La rotation du cube n'intervient pas.
6. **Position.** Le vertex final est placé à `direction × (R + élévation)`.

L'ordre des étapes 2 et 4 est libre : une rotation ne change pas les longueurs. On peut donc préparer la face normalisée dans son repère local, puis la tourner dans le shader.

## Ce que le concept garantit

- **Le terrain ne bouge pas avec la grille.** Un point de la planète a toujours la même altitude, quelle que soit l'orientation du cube.
- **Rien à charger.** Pas de tuiles ni de modèle : tout se recalcule à partir de la position.
- **Pas de couture.** Tant qu'on garde une seule face, il n'y a aucun raccord entre faces du cube à gérer.
- **Une origine flottante naturelle.** La face est centrée sous la caméra. Son repère local sert de repère de rendu et limite les erreurs de précision.

## La règle de taille

**Proposition : la demi-largeur de la face vaut k × altitude.** Vue du dessus, une maille occupe alors toujours le même angle à l'écran. C'est ce qui donne un détail constant « du point de vue de l'utilisateur ».

La face est plafonnée à la face entière du cube, soit une demi-largeur égale au rayon R.

Exemple avec R = 6 378 km, k = 2 et une grille de 512 × 512 :

| Altitude | Horizon | Demi-largeur de la face | Maille au sol |
|---|---|---|---|
| 2 m | 5 km | 4 m | 1,6 cm |
| 100 m | 36 km | 200 m | 78 cm |
| 10 km | 357 km | 20 km | 78 m |
| 400 km | 2 200 km | 800 km | 3,1 km |

k et la taille de la grille règlent le compromis entre finesse et coût.

## Points à trancher

### 1. Centre de la face : tranché, en deux jets

**Jet 1 : la face regarde la caméra.** Elle est posée sur la ligne qui relie le centre de la planète à la caméra, à une distance R du centre. Son centre est donc le nadir. C'est un panneau toujours tourné vers la caméra.

**Jet 2 : la face coulisse légèrement vers le point regardé.** Un décalage qui dépend de l'altitude place le maximum de détail au centre du regard.

Contraintes du jet 2 :

- **Le décalage reste borné.** À basse altitude, le point regardé peut être à des centaines de kilomètres, voire dans le ciel. Si la face le suivait, le sol sous la caméra sortirait de la face. Proposition : un décalage proportionnel à la taille de la face, donc à l'altitude.
- **Tourner la tête déplace la face.** Le glissement du point 2 apparaît alors même caméra immobile. Il faudra lisser le décalage.
- **PlanetaryEngine en a déjà une version.** Son maillage vise un point situé devant la caméra, à deux fois l'altitude, plafonné à 2 500 km.

### 2. Le relief qui « nage »

**La grille glisse sur le terrain à chaque frame**, puisqu'elle suit la caméra en position et en taille. Le terrain reste fixe, mais il est échantillonné à des endroits différents d'une frame à l'autre. Les détails plus fins qu'une maille scintillent et les crêtes ondulent.

Deux remèdes classiques, combinables :

- **Limiter les octaves à la maille.** On n'évalue que les octaves dont la longueur d'onde dépasse deux mailles, avec un fondu sur la dernière. Bonus : le calcul coûte moins cher.
- **Déplacer la grille par crans.** La face avance d'une maille entière à la fois et change de taille par paliers de ×2, avec un fondu entre paliers, le geomorphing.

Il faut aussi fixer la rotation de la face autour de la verticale, par exemple sur le nord. Sinon, chaque changement de cap fait tourner toute la grille.

**Recommandation : prototyper d'abord la version continue**, pour voir l'artefact avant de le corriger.

### 3. Le détail vers l'horizon

**Une face proportionnelle à l'altitude couvre le dessous de la caméra, pas l'horizon.** À 10 km d'altitude, la face couvre ±20 km alors que l'horizon est à 357 km. Dès qu'on regarde devant soi, l'essentiel de l'écran est hors de la face.

Agrandir une seule grille jusqu'à l'horizon ne marche pas. À 10 km d'altitude, garder sous la caméra une maille d'environ 8 m, soit un pixel en 1080p, demanderait près de 90 000 vertices par côté.

Les « vues distantes » se posent donc à toutes les altitudes, pas seulement depuis l'orbite.

**Piste : empiler des faces de taille ×2**, toutes centrées sous la caméra et avec la même grille. Il faut environ log2(horizon / taille de la face) niveaux : une dizaine à 2 m d'altitude, quatre ou cinq à 10 km. C'est le principe des geometry clipmaps, appliqué à la sphère.

Un prototype Unity de l'auteur, en 2012, faisait déjà ça : 16 patchs de 255 × 255, de largeur croissante, positionnés sous la caméra.

L'alternative déjà écrite dans `log/general_spec.md` est le maillage radial en toile d'araignée, prototypé dans le moteur The-Forge, hors de ce dépôt.

### 4. Au-dessus de 2 640 km d'altitude

**Une face entière ne couvre plus tout ce qui est visible.** La calotte visible dépasse 45° autour du nadir quand l'altitude dépasse R × (√2 − 1), soit environ 2 640 km. Il faut alors les faces voisines, jusqu'à cinq faces visibles. C'est le vrai cas « vue depuis l'espace ».

### 5. La précision des float

**En float32, à 6 378 km du centre, le pas de précision est de 0,5 m.** Deux conséquences :

- **Rendu.** Les positions doivent être relatives à la caméra. Le repère local de la face s'y prête.
- **Bruit.** Évalué en coordonnées absolues float32, le relief est quantifié à 0,5 m. C'était suffisant pour complexplanet, le premier relief, pas pour marcher au sol. Solution connue : calculer en double sur CPU le décalage de chaque octave, et ne passer au GPU que des coordonnées locales.

Pas bloquant pour un premier prototype.

### 6. complexplanet s'arrêtait à 7,5 m

**Son propre code le disait : au-delà de 0,25 seconde d'arc, soit environ 7,5 m, le terrain devenait flou.** Pour descendre jusqu'au sol, il faudra des couches de détail supplémentaires sous 7,5 m, modulées par le type de terrain.

### 7. Le coût par frame

**complexplanet demandait environ 340 évaluations de bruit par vertex.** Le décompte : 114 octaves dans les générateurs, plus 12 turbulences à 3 bruits de Perlin chacune, soit 225 octaves, plus un Voronoi.

Ordre de grandeur, à mesurer : 10 niveaux de 256 × 256 font environ 650 000 vertices, soit 220 millions d'évaluations par frame. Ça doit tenir sur un GPU récent, mais c'est le poste dominant.

**Mesuré sur le prototype du jet 1, complexplanet complet :**

- Une face de 513 × 513 : 13 à 22 images/s en orbite.
- Une face de 257 × 257 : environ 50 images/s en orbite, 150 à 4 km d'altitude.
- Le coût est plus élevé que prévu : la turbulence fait recalculer certains sous-graphes en un second point, comme les continents.

Les normales se calculent à partir des vertices voisins de la grille, sans réévaluer le bruit.

## Les couches de bruit

**Le relief tectonique d'Exolune :** `Relief.hlsli`, sur la carte tectonique de `Tectonics.hlsli` et les briques de `Noise.hlsli` (`geometrie.md`, `spec-relief-tectonique.md`).

- **Les grandes formes, au-dessus de 50 km,** viennent d'une carte calculée au démarrage : continents, plaques, frontières, chaînes, fosses.
- **Le détail, sous 50 km,** vient de douze octaves de bruit modulées par la géologie, environ 40 à 60 évaluations de bruit par vertex, contre 340 pour complexplanet.
- **L'histoire :** le portage de complexplanet et de libnoise, du jalon 01 au 2026-10-30 ; une réécriture originale de sa composition le 2026-10-31, commit `f00004d` ; l'état des sources avant le premier portage, `log/concept-historique.md`.

**La licence.** Le relief n'est pas une œuvre dérivée de complexplanet ni de libnoise. La licence du moteur est celle de `../LICENSE` ; les crédits des tiers, `../NOTICE`.
