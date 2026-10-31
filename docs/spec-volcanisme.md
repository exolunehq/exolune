# Spec : le volcanisme

Statut : spec vivante, depuis le 2026-10-31. Faite le 2026-10-31 sur la branche `claude/volcanisme-7c3aea`, partie de `bruit-propre` ; piste `piste/volcanisme`, à juger en vol : `tools/tests/2026-10-31-volcanisme.txt`. C'est l'étape 5 de `spec-relief-tectonique.md`, ses collines abyssales exceptées.

## L'objectif

**Les volcans se déduisent de la carte tectonique :** arcs sur les subductions, points chauds et leurs chaînes, volcans des rifts. Avant, le volcanisme n'existait que comme type de roche.

- **Ce qu'on voit :** des stratovolcans en chaîne, en arcs insulaires et en cordillères ; des boucliers, des îles qui s'usent et s'enfoncent, des récifs-barrières, des atolls, des guyots ; des calderas, des coulées, des champs de petits cônes ; des traps en marches ; des basaltes et des cendres sombres.
- **Le modèle suivi :** celui de la carte. La liste des volcans se calcule une fois au démarrage ; le relief les évalue point par point.

## Les contraintes

- **Tout au démarrage, rien en route** (`principes.md`) : positions et formes des volcans dans une liste, avec un index sur un cube.
- **Un point ne dépend jamais de la maille :** chaque édifice est une fonction du point, dans le repère de la planète ; le filtrage seul suit la maille, comme pour les profils de la carte.
- **La forme avant érosion :** les édifices font partie de `ReliefElevation(p, false)` ; l'érosion les creusera.
- **Du code original,** depuis les articles cités.

## La liste des volcans, `Tectonics.cpp`

**À la fin de `Tectonics::Build`, avant le lissage des champs :** la liste, son index, et ce que les points chauds changent à la carte. Le même corps donne la même liste, au bit près.

**Chaque volcan,** `Tectonics::Volcano`, 52 octets : sa direction, son rayon, sa hauteur au-dessus du sol alentour, son profil, son cratère, le niveau où son sommet a été arasé, son récif, son champ de cônes, sa fraîcheur, sa graine.

**Les arcs, sur la plaque chevauchante :**
- **Le front volcanique** là où la plaque plongeante atteint une centaine de kilomètres de profondeur : à 140 à 230 km de la fosse, autour de l'arc de la carte, 175 km en mer, 170 à 200 km sur un continent (Stern 2002).
- **Les candidats :** les cellules à cette distance du front, chacune portée exactement à la distance voulue le long du grand cercle qui la relie à son point de front. Aucun là où la plaque plonge à plat, par tronçons.
- **Éclaircis dans l'ordre d'un tirage :** chacun gardé si aucun autre n'est à moins de 35 à 80 km.
- **Les stratovolcans :** 2 à 4 km de haut, un quart de plus en mer, bâtis depuis le pied de la ride de l'arc ; un rayon de 4,5 à 7,5 fois la hauteur ; un cratère de 0,4 à 1,1 km ; 12 % effondrés en caldeira de 4 à 10 km (Crater Lake) ; un tiers avec des cônes sur leurs flancs.
- **Derrière l'arc, sur un continent :** des champs de cônes sur un bouclier bas de coulées, tous les 180 à 300 km, à 110 km du front (le champ de Michoacán-Guanajuato).

**Les rifts continentaux,** à moins de 60 km de leur axe, tous les 70 à 150 km : stratovolcans jusqu'à 4,5 km (le Kilimandjaro), boucliers, calderas (Menengai), chacun dans un champ de cônes.

**Les points chauds :** 8 à 16 panaches fixes dans le manteau, les plaques en mouvement au-dessus (Wilson 1963, Morgan 1971).
- **La chaîne :** un volcan tous les 40 à 90 km en mer, 120 à 200 km sur un continent ; le point formé il y a t Ma au-dessus du panache est aujourd'hui tourné autour du pôle d'Euler de sa plaque.
- **Elle s'arrête** à la frontière de la plaque, là où la croûte est plus jeune que le volcan, ou à la tête du panache, 30 à 130 Ma.
- **La tête du panache :** des traps sur un continent (le Deccan), un plateau océanique en mer (Ontong Java).

**En mer, les boucliers :**
- **4 à 9 km au-dessus du fond,** la plupart de faibles points chauds, donc des monts sous-marins ; un rayon de 7 à 10 fois la hauteur ; leur sommet à 4,5 km au-dessus de la mer au plus (Mauna Loa, Mauna Kea).
- **Le plus jeune** avec sa caldeira sommitale et ses cônes.
- **L'affaissement :** la houle du panache qui décroît et la plaque qui refroidit, 1 000 (1 − e^(−t/15)) + 6 t m, environ 1 km en 30 Ma.
- **L'arasement :** une île est usée par les vagues, son sommet à H e^(−t/4) au-dessus de la mer d'alors, puis il s'enfonce : un guyot.
- **Le récif, sous les tropiques, à moins de 26° :** sept fois sur dix, il s'installe sur la plate-forme usée de l'île, la moitié du rayon de son rivage à 1,5 Ma, et suit le niveau de la mer pendant qu'elle s'enfonce : un récif-barrière, puis un atoll (Darwin 1842).

**Sur un continent,** une caldeira tous les 120 à 200 km pendant 15 Ma (de la plaine de la Snake River à Yellowstone) : un dôme bas de 40 à 70 km, une caldeira de 10 à 25 km.

**Dans les champs de la carte,** avant leur lissage :
- **La houle du panache** autour de la jeune chaîne : 0,6 à 1,3 km sur 380 km de part et d'autre, décroissant en 10 Ma ; 60 % sous un continent.
- **Les traps :** 300 à 700 km de rayon, 0,8 à 1,6 km de haut, usés en 200 Ma ; leur bord en escarpement ; leurs strates en marches, les mesas des plates-formes (`Relief.hlsli`).
- **Le plateau océanique :** un dôme de 1,5 à 2,5 km, 300 à 600 km de rayon.
- **La roche volcanique** autour de chaque volcan et sur les traps : la classe et l'érodabilité, 0,6.

**Où se pose chaque volcan :** là où la carte porte sa forme, ramené par le gauchissement de la lecture de la carte (`RlTurbulence`, porté en C++). Il tombe sur la forme telle que le shader la dessine ; sans cela, jusqu'à 30 km d'écart avec la ride de l'arc ou le graben (`principes.md`).

**L'index :** un cube de 64² cellules par face ; chaque cellule liste les volcans à portée, 1,65 fois leur rayon et 80 km au moins. Un tableau unique : la position de la liste de chaque cellule, puis les numéros.

## Les édifices, `Volcanoes.hlsli`

**Le shader lit la cellule du point, évalue ses volcans.** Deux structures, `t21` et `t22`, dans la table de la carte tectonique.

| Forme | Profil | Source |
|---|---|---|
| Stratovolcan | flancs concaves, e^(−3x), un tablier jusqu'à 1,3 rayon | Karátson et al. 2010 |
| Bouclier | presque droit du fond à son large sommet plat, 1 − x^1,3 ; son pied fondu sur les 40 % extérieurs | Mauna Loa |
| Contour | allongé selon une direction tirée, jusqu'à 10 % du rayon pour un stratovolcan, 35 % pour un bouclier ; lobé et anguleux, deux octaves d'un bruit sur le cercle, 12 % à un écart-type ; 30 % au plus : zones de rift, coulées, effondrements. Le cratère, l'arasement et le récif le suivent | Hawaï |
| Cratère | l'édifice tiré vers un fond, H profil(cratère) − profondeur ; une cuvette, (1 − u²)² | — |
| Caldeira | un fond plat entre des murs raides, 1 − u⁸, au-delà de 0,8 à 2,5 km de rayon | Crater Lake |
| Coulées | des langues de 1,5 km de large à mi-rayon, deux fois plus sur un bouclier, étirées le long de la pente ; 40 m d'épaisseur sur un stratovolcan, 15 sur un bouclier, jeunes ; elles partent du tiers du rayon, couvrent la moitié du flanc, puis quelques longues atteignent le pied | — |
| Cônes | scories, une maille de 2,5 km, 0,25 à 0,75 km de rayon, hauts du quart, un cratère de 0,4 rayon | Wood 1980 |
| Guyot | le sommet arasé à son niveau, plat sous la mer, arrondi au-dessus | — |
| Récif, atoll | posé sur le contour de l'édifice, au niveau de l'ancien rivage, plus des éperons et des baies de quelques centaines de mètres ; un platier à −1,5 m, de 0,25 à 0,8 km, rongé, plus large au vent, l'est des alizés ; des motus séparés à +3 m, de 150 à 500 m de large, un tiers du platier au vent, un huitième sous le vent ; des passes de 8 m, surtout sous le vent ; un lagon à −12 m, 30 % plus ou moins profond par taches | Darwin 1842 |

- **Les coulées en polaire :** (k cos a, k sin a, r / long), un cercle en travers, étiré le long de la pente, gauchi par un bruit plus large pour qu'elles serpentent. Leur moyenne est l'édifice même : les langues au-dessus, le sol entre elles en dessous. Sans cela, un anneau marquait leur départ.
- **Plusieurs volcans se combinent en maximum lissé,** (Σ e⁴)^¼, comme les chaînes de la carte ; le fond d'une caldeira sous le sol alentour, le plus bas ; les cônes en plus.
- **Le détail calmé sur les flancs jeunes :** jusqu'à 80 % du relief laissé au bruit, sinon une cordillère froisse le cône.
- **Après le détail :** l'arasement, le récif et le lagon du volcan qui domine le point.
- **Le récif suit l'édifice qu'il couronne :** le même contour, lu au niveau de l'ancien rivage ; un récif-barrière, un atoll et un guyot n'ont donc jamais d'autre forme que leur volcan. Avant le 2026-10-31 au soir, un cercle bruité à part et un platier de largeur constante, à +0,5 m : la houle le découvrait, une bande de plage continue.
- **Tout profil sur deux mailles au moins :** l'édifice, le cratère et les cônes plus larges et plus bas d'autant, leur volume gardé ; les coulées et les cônes remplacés par leur moyenne là où la maille ne les porte pas.

**Où est l'appel :** `ReliefElevation`, après les côtes et avant le détail, puis `VolcanoFinish` après les cordons des côtes. Les réglages : `VOLCANO_*` dans `PlanetSettings.hlsli`.

## Les matériaux

**Le sol volcanique frais, `gVolcanic`, de 0 à 1 :** le cône de cendres et de scories d'un stratovolcan, le sommet d'un bouclier, les coulées, les cônes ; pondéré par la fraîcheur, e^(−t/3) sur une chaîne.
- **Le chemin :** il remplace le champ `relief` inutilisé de `FaceVertex`, devenu `volcanic`, puis `geology.w` jusqu'au pixel.
- **La roche :** le basalte, la plus sombre de la palette (`RockColor`).
- **Le sol :** cendres et scories, réflectance 0,07, sur 85 % du sol ; les plages noires.

## Le portage CPU

**`tools/hydro/cp.py` lit `x64/Release/volcans-<graine>.bin`,** écrit par le moteur à chaque démarrage, en-tête `EXOVOLC1` ; `EXOLUNE_VOLCANS` donne un autre chemin. `volcano_edifices` et `volcano_finish` suivent le shader ; `elevation(..., extra=True)` donne aussi `volcanoes` et `volcanic`.

**L'écart au moteur :**
- **Contre la carte de la planète,** 200 texels sur des volcans, mailles de 12 km : 0,4 cm en médiane, 6 cm au plus.
- **Au sol sous la caméra,** 33 points sur des volcans, mailles fines : 7,9 cm en médiane, 0,9 m au plus, depuis la correction de `bruit-propre` (`d304da0`) et les cônes en doubles. L'écart suit la pente, le moteur donnant sa position au décimètre ; avant elles, 11 cm, 6 sur sol doux et 13 sur les flancs, contre 4 et 43 cm pour le relief seul loin des volcans.
- **Les cônes se placent en doubles :** à 120 km du sommet d'un bouclier, une position en float avance par pas de 8 mm, et le flanc d'un cône en escalier (`principes.md`, la précision de l'échelle où une grandeur sert).

## Les mesures

**Graine 0 :** 1 113 volcans, 15 points chauds ; 697 stratovolcans, 352 boucliers, 163 calderas, 532 champs de cônes, 75 champs d'arrière-arc ; 26 atolls, 3 récifs-barrières, 113 guyots. Graines 1 et 2 : 1 060 et 1 041 volcans, 10 points chauds.

| Mesure | Avec | Sans | |
|---|---|---|---|
| Démarrage, le volcanisme | 60 à 77 ms | — | sur 1,0 à 1,3 s de carte, machine chargée par d'autres sessions |
| Mémoire GPU | +0,18 Mo | 38 Mo | la liste et l'index |
| Calcul du terrain en mouvement, lieux volcaniques | 0,20 à 0,65 ms | 0,19 à 0,54 ms | +0,02 à +0,12 ms ; GPU partagé, au bruit près ailleurs |
| Terres, graines 0, 1, 2 | 32,8, 34,3, 30,7 % | 32,6 % ; 34,0 et 30,5 % | portage, 400 000 points, mailles de 2 km |
| Médiane des terres, graine 0 | 388 m | 380 m | |
| Modes, graine 0 | +375 m, −4 525 m | +375 m, −4 525 m | bimodale |
| Médiane des océans, graine 0 | −4 430 m | −4 450 m | la houle et les plateaux |
| Au-dessus de 3 km, graine 0 | 2,03 % | 1,99 % | |
| Sous un édifice de plus de 10 m | 0,5 à 0,6 % de la surface | — | |

- **Le calcul sans édifices :** `VolcanoEdifices` coupé à sa source, le temps et le reste égaux ; les terres sans volcanisme, la carte de `bruit-propre`.
- **Les graines 1 et 2 :** leurs cartes calculées par `Tectonics.cpp` hors du moteur, un petit programme de la session ; le même fichier que le moteur pour la graine 0, au bit près.
- **Le pic de mémoire du calcul** ne change pas : quelques mégaoctets de plus.

**Le jeu de vérification :** la compilation sans erreur ni avertissement nouveau ; `tools/tests/2026-10-31-volcanisme.txt` ; la planche `volcanisme_planche.jpg` dans les notes des sessions ; le relief ombré du portage autour d'un volcan d'arc, ses coulées et ses cônes.

## Les défauts connus

- **Les cônes et les coulées se voient mal en lumière de face :** quelques dizaines de mètres sur un flanc boisé. Ils se jugent en lumière rasante, ou par le relief ombré du portage.
- **Les îles hautes des tropiques paraissent pâles d'orbite :** le climat du sol, pas le volcanisme.
- **Les arcs insulaires :** près d'un tiers de leurs volcans reste sous la mer, la ride de l'arc vers −1,5 km ; des monts sous-marins d'arc, comme aux Izu-Bonin.
- **Les motus restent en sable nu près de l'eau :** la plage est une bande d'altitude, de 5 à 25 m (`Materials.hlsli`) ; quelques palmiers seulement, là où la végétation les admet. Une plage par la distance au rivage, une règle des matériaux, les couvrirait de végétation.
- **Les petits cailloux posés** gardent la couleur de la roche régionale, pas celle du basalte (`ObjectPlacement.hlsl`).
- **Les coulées fraîches portent encore la végétation du climat :** la carte des plantes ne lit pas `gVolcanic`.
- **Pas de lacs de caldeira propres :** l'eau vient de la carte de la planète, qui remplit les cuvettes à sa maille.
- **Pas encore de collines abyssales orientées par l'âge,** ni de monts sous-marins hors des chaînes.

## Les suites

- **L'érosion,** sur `erosion-niveaux` : creuser les édifices, ravines rayonnantes et barrancos ; les îles anciennes en amphithéâtres.
- **Les plantes sur les coulées fraîches :** `gVolcanic` dans le placement et la canopée, ensemble, pour qu'un lieu reste le même de loin et de près.
- **Les monts sous-marins isolés et les collines abyssales,** le reste de l'étape 5.
