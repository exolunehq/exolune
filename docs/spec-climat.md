# Spec : le climat

Statut : spec vivante, depuis le 2026-10-31, branche `claude/climat-0e9eb5`, tag `piste/climat`. **C'est le climat du jeu,** sans variable : l'humidité bruitée, sa bande sèche à 24° et le bruit régional de la température sont retirés. À juger en vol : `tools/tests/2026-10-31-climat.txt`. Le code : `Climate.cpp`, `Climate.h`, `Climate.hlsli` ; le portage : `climate(p)` dans `tools/hydro/cp.py`.

## L'objectif

**Le climat se calcule au démarrage sur la géographie de la planète, plus sur un bruit.**
- **Pourquoi :** l'ancienne humidité était un bruit régional ; il plaçait des déserts à l'équateur et des forêts derrière les chaînes. Rien ne liait la pluie aux mers, aux vents ni au relief.
- **Le modèle suivi :** une circulation générale simple, trois cellules par hémisphère ; un bilan de la vapeur que les vents portent depuis les mers jusqu'à son état d'équilibre ; la pluie par l'ascendance de l'air et par le relief.
- **Les déserts tombent vers 20 à 30°** par la circulation : la branche descendante de la cellule de Hadley y diverge, l'air y est sec. Aucune bande n'est imposée.

## Les contraintes

- **Tout au démarrage, rien en route,** comme la carte tectonique (`principes.md`) : moins de 0,3 s et de 10 Mo par planète.
- **Un calcul déterministe par graine :** chaque passe calcule chaque cellule depuis la passe précédente seule ; le même fichier au bit près, quel que soit le nombre de fils.
- **Le climat lit la forme avant érosion,** les grandes formes de la carte tectonique, jamais le relief érodé : le niveau 0 lit la pluie sans boucle.
- **Du code original,** écrit depuis les lois publiées citées ici.

## L'architecture

| Étape | Où | Ce qu'elle fait |
|---|---|---|
| 1. Les entrées | 256² par face | Les grandes formes, tranche 0 de la carte tectonique, 2 × 2 texels par cellule : le sol sous l'air, la surface de la mer en mer ; la part de terre |
| 2. Les vents | 64² puis 128² | Les trois cellules par la latitude ; l'équateur thermique décalé de 7° vers l'été ; les dépressions thermiques des terres chaudes et les anticyclones des froides ; le vent ralenti d'un quart sur terre |
| 3. L'air marin | idem | Un traceur porté par les vents : 1 sur la mer, il s'efface sur terre en 4 jours et au-dessus des chaînes sur 1 500 m de montée ; la continentalité est son complément |
| 4. Les courants froids | idem | Le transport d'Ekman vers le large, 90° à droite du vent au nord, à gauche au sud : l'eau froide remonte, jusqu'à 6 °C de moins, sous les vents réguliers ; portée à terre comme l'air marin |
| 5. Les températures | idem | La moyenne de l'année au niveau de la mer et la demi-amplitude des saisons |
| 6. La vapeur et la pluie | idem, par saison | La colonne d'eau portée par le vent et mêlée par les tourbillons ; évaporée sur la mer, tombée selon l'ascendance et le relief, recyclée en partie sur les terres chaudes |
| 7. La carte | 256² par face | Les champs grossiers en bilinéaire ; la pluie répartie par les pentes fines ; les températures sur la terre fine |

**Deux grilles pour l'état d'équilibre :** 200 km d'abord, 300 passes pour l'air, 400 pour la vapeur ; puis 100 km, partie de cette solution, 100 et 150 passes. Ce qui s'étale lentement, par le seul mélange dans les zones calmes, s'y établit en quatre fois moins de passes, chacune quatre fois moins chère.

**Le transport, en volumes finis :** les flux traversent les arêtes exactes des cellules sur la sphère, le vent de l'arête la moyenne de ses deux cellules, en amont ; le mélange agit sur la vapeur rapportée à ce que l'air peut tenir, par la plus petite des deux capacités : il ne monte jamais une pente que le vent ne monterait pas. Des pas de pseudo-temps locaux, les plus grands que la sortie permet : l'équilibre n'en dépend pas.

## Les lois

| Grandeur | Loi | Source |
|---|---|---|
| Vents de surface | alizés 6,5 m/s vers l'ouest, vents d'ouest 8 m/s, vents d'est polaires 3,5 m/s, en sin 6φ ; retour de Hadley de 3,5 m/s, convergent à moins de 4° de l'équateur thermique, divergent de 12 à 30° | Peixoto et Oort 1992, *Physics of Climate*, ch. 7 |
| Mousson | 6·10⁵ m/s par K/m vers le chaud, l'écart de la saison à la moyenne de sa latitude lissé sur 1 500 km ; tourné de 55° hors des tropiques, 5 m/s au plus | le vent thermique, choix calé |
| Capacité de la colonne | 65 mm à 28 °C, 6 % de plus par degré ; elle s'efface avec le sol sur 2 200 m ; le flux bas, bloqué par les chaînes, n'en monte que la moitié | Clausius-Clapeyron ; Smith 1979, le blocage pour un nombre de Froude sous 1 |
| Évaporation | la colonne de mer rejoint en 1 jour la moitié de sa capacité, sur une mer d'au moins −1,8 °C, moins sous la banquise | — |
| Pluie de grande échelle | la colonne tombe en 7 jours, divisés par exp(convergence / 1,5·10⁻⁶ s⁻¹), de 4,5 fois moins à 4,5 fois plus vite ; le taux divisé par 1 + descente / 0,03 m/s sous le vent | le temps de résidence de la vapeur, 8 à 9 jours sur Terre |
| Pluie orographique | 20 % de ce que la montée condense, montée / 2 200 m ; l'excès sur la capacité tombe en 5 heures | le modèle de pente montante |
| Recyclage | un tiers de la pluie des terres chaudes s'évapore de nouveau | Eltahir et Bras 1996 |
| Mélange | 6·10⁵ m²/s, de 0,4 fois à l'équateur à 1,4 fois vers 50°, les rails des dépressions ; 3·10⁵ pour l'air marin | les tourbillons de moyenne latitude |
| Température | 28 − 52 sin²φ au niveau de la mer, la loi d'avant ; plus le froid des courants ; moins 12 sin²φ (continentalité − 0,6) sur terre | l'ancienne loi, sans son bruit |
| Saisons | 1 + 5 sin²φ sur la mer ; sur terre, l'ajustement sur TerraClimate, 3,5 + 18 sin²φ, à la continentalité moyenne 0,6, jusqu'à 1,5 fois à l'intérieur | `tools/saisons_terre.py` |
| Courants froids | la remontée d'Ekman fois la régularité du vent, 1 sous les alizés, 0,4 au-delà de 42° | Ekman 1905 ; les alizés soufflent d'un quart 80 % du temps |

## Les sorties

**Deux cubes RGBA16F de 256² par face, 9 mips, 8,0 Mo sur le GPU** (`Climate.hlsli`, `t20`), lus en filtrage matériel, continus entre les faces. C'est de la donnée, jamais de la géométrie.

| Cube | x | y | z | w |
|---|---|---|---|---|
| 0 | précipitations de l'année (mm) | température moyenne de l'année au niveau de la mer (°C) | demi-amplitude des saisons (°C) | part de la pluie dans la moitié chaude de l'année |
| 1 | vent moyen vers l'est (m/s) | vent moyen vers le nord (m/s) | continentalité, 0 en mer à 1 où l'air marin n'arrive pas | refroidissement de la mer par les courants froids (°C, ≤ 0) |

**Sur le CPU :** `Climate::Build(tectonique, rayon)` rend la carte en floats ; `Climate::At(carte, direction, champs)` la lit en bilinéaire, les texels au-delà d'une arête pris sur la face voisine.

**Le fichier :** `x64/Release/climat-<graine>.bin`, 12,6 Mo, l'en-tête `EXOCLIM1`, la graine, la taille, 8 champs, 6 faces, puis les floats, face par face, rang par rang. `EXOLUNE_CLIMAT` donne un autre chemin au portage.

## L'interface pour l'érosion

- **La pluie à un point :** `cp.climate(p)["precipitation"]`, en mm par an, pour des directions `p` (n, 3) ; ou `Climate::At` sur la carte gardée en mémoire. `cp.humidity(P)` donne l'humidité des matériaux.
- **La température au sol :** `temperature − 5 × altitude (km)` ; au mois `t` de l'année, plus `amplitude × sin`, l'été au nord vers le milieu de l'année. La neige des matériaux tombe sous −2 °C de moyenne annuelle.
- **La saisonnalité de la pluie :** `summer`, sa part dans la moitié chaude.
- **Aucune boucle :** le climat ne lit que les grandes formes de la carte tectonique ; le relief érodé du niveau 0 ne change pas la pluie qui l'a creusé.
- **Garder la carte en mémoire :** `D3DApp::CreateClimateMap` la jette après l'envoi au GPU ; le niveau 0 la gardera, comme la carte tectonique.

## Les consommateurs

- **Les matériaux,** `GroundMaterials` : la température est celle de la carte au niveau de la mer, moins 5 °C/km, moins 8 °C par unité de pente vers le pôle, plus le bruit de la limite des neiges ; l'humidité est le log des précipitations, de 100 à 3 000 mm, plus leur variation sous la carte, `LocalRain`.
- **`LocalRain` :** la carte porte ce qui dépasse deux de ses cellules, 100 km ; un bruit de gradient de 100 à 6 km, écart-type 0,08 en humidité, fait le reste, comme le détail du relief sous la carte tectonique. Ce que le pixel n'en montre pas élargit les limites de l'herbe et du sable (`SpreadStep`).
- **Les plantes,** `PlantClimate` et `VegetationAt` : les mêmes champs ; la demi-amplitude des saisons vient de la carte, plus de la seule latitude.
- **La mer :** la couleur de l'eau suit la température de la carte ; les courants froids la verdissent.
- **Le vaisseau :** la température de la verrière, celle de la carte au niveau de la mer moins 6,5 °C/km ; le cube de bruit qu'il cuisait au démarrage est retiré.
- **Les nuages :** leur carte météo se calcule sur la carte du climat et le relief, depuis le 2026-10-31 (`Climate::Weather`, `spec-nuages.md`, la carte météo).
- **`ClimateNoise` reste,** pour les variantes des textures et la teinte régionale.

## Les vues de diagnostic

| Nom | Ce qu'elle montre |
|---|---|
| `precipitation` | les précipitations de l'année, en log : brun sous 100 mm, sable, vert pâle à 500 mm, vert, sarcelle à 2 000 mm, bleu au-delà de 4 000 ; la mer plus pâle |
| `wind` | le vent moyen : sa direction en teinte, est rouge, nord jaune-vert, ouest cyan, sud violet, plus vive avec la vitesse ; une flèche par cellule d'environ 600 km |
| `temperature` | la vue existante, la température au sol des matériaux, de −30 à 40 °C, en gris |

**Une graine à part pour comparer :** `MYPLANETENGINE_SEED` change la carte tectonique et le climat ; le bruit du détail garde `PLANET_SEED`.

## Les mesures

**Le temps et la mémoire,** au titre du moteur, sur une machine chargée par d'autres rendus, la carte tectonique y prenant 0,94 à 1,04 s contre 0,85 au repos :
- **Le temps :** 0,22 à 0,24 s, contre 0,33 s avec une seule grille de 400 passes.
- **La mémoire GPU :** 8,0 Mo ; le fichier, 12,6 Mo.
- **Au bit près** d'un calcul à l'autre.

**La convergence,** contre 1 500, 2 000, 800 et 1 200 passes : humidité p99 0,019, au plus 0,067 ; température p99 0,07 °C.

**Les précipitations des terres par bande de latitude,** mm, portage, trois graines :

| Bande | Graine 0 | Graine 1 | Graine 2 | La Terre, environ |
|---|---|---|---|---|
| 0 à 10° | 2 167 | 1 946 | 2 293 | 2 000 |
| 10 à 20° | 1 222 | 1 059 | 1 170 | 1 100 |
| 20 à 30° | 596 | 530 | 520 | 600 |
| 30 à 40° | 615 | 714 | 605 | 600 |
| 40 à 50° | 542 | 584 | 743 | 600 |
| 50 à 60° | 417 | 367 | 504 | 500 |
| 60 à 75° | 161 | 193 | 203 | 300 |

- **Les déserts, sous 250 mm :** 28,5, 27,8 et 27,6 % des terres ; 33, 45 et 46 % de la bande de 20 à 30°, 2, 3 et 1 % de celle de 0 à 10°. La moyenne des terres : 879, 888 et 940 mm.
- **Les extrêmes, graine 0 :** plus de 4 000 mm sur 2,0 % des terres, plus de 6 000 sur 0,5 %, au plus 15,6 m au vent des chaînes équatoriales.
- **Les lieux typés, graine 0 :** désert intérieur 20 mm à 25,3° 56,3° ; désert côtier sur courant froid 77 mm à 18,3° 37,8°, la mer 4,6 °C plus froide ; savane de mousson 754 mm, 99 % en été, à 19,8° 99,8° ; plaine équatoriale 7 730 mm à −7,8° −37,3° ; steppe continentale 213 mm, saisons de ±15,6 °C, à 41,8° −22,3° ; pluies d'hiver, 737 mm, 3 % en été, à 28,3° −42,3°.
- **L'ombre pluviométrique :** une chaîne de 2,5 km sous les alizés, près du départ du jeu, 2 937 mm au vent à −12,4° 112,1°, 61 mm sous le vent à −11,8° 110,9°.

**Le jeu de vérification :** les vues de contrôle de la spec du relief et les vues du climat rendues sans fenêtre, avant et après ; la planche `climat_planche.jpg` dans les notes de la session ; les cartes globales du portage, trois graines.

## Les défauts connus

- **Le vent de la mer reste uniforme :** la carte porte le vent, la mer ne le lit pas encore (`principes.md`, la mer).
- **Les extrêmes au vent des chaînes équatoriales** dépassent ceux de la Terre : 15,6 m au plus, contre 8 à 12 à 50 km.
- **Les hauts plateaux sont secs :** 136 mm en médiane au-dessus de 2 km, contre 200 à 500 sur Terre.
- **La loi zonale de la température est celle d'avant,** froide : neige au niveau de la mer dès 50°. Inchangée, puisque hors du sujet.
- **La variation sous la carte est un bruit,** pas la pente fine du relief au vent.
- **Les lieux de deux vues de contrôle ont changé de climat :** la côte plate tropicale, 16,7° −89,3°, est une côte sous le vent, 250 mm ; les mesas, 15,6° 95,6°, une savane de mousson, 919 mm.

## Le plan par étapes

| Étape | Contenu | Statut |
|---|---|---|
| 1 | La carte du climat, ses lois, ses vues, son portage ; les matériaux, les plantes, la mer et le vaisseau branchés | faite le 2026-10-31, à juger en vol |
| 2 | Les nuages sur le climat : la carte météo calculée au démarrage sur ses champs | faite le 2026-10-31, à juger en vol ; tag `piste/nuages-climat` |
| 3 | Le vent de la mer depuis la carte | à faire |
| 4 | La pluie sous la carte par la pente fine au vent, à la place d'une part du bruit | si le vol le demande |
| 5 | Le niveau 0 lit la pluie et la température : fleuves et glaciers | session érosion |
