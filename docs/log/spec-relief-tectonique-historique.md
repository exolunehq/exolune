# Historique : le relief tectonique

**Les sections dépassées de `../spec-relief-tectonique.md`, pour mémoire.** Rien ici ne décrit l'état présent.

## Les cordons avant le filtrage de leur émergence, 2026-10-31

- **Troisième passe :** posés sur le contour du rivage bruité, ils en suivaient les angles et les rias ; dans une ria plus étroite qu'eux, leurs deux flancs se rejoignaient en un bloc plat à 3 m.
- **Quatrième passe :** le rivage lissé porte les arcs ; la crête se relève depuis le relief sous elle, pour que les octaves fines ne l'entaillent plus jusqu'à la mer.
- **La largeur totale seule était filtrée :** au moins deux mailles, amplitude abaissée en proportion.
- **Défaut restant :** vers 20 km d'altitude, la crête émergée occupait moins d'une maille et se dessinait en pointillés blancs ; continue à 8 et 3 km.
- **Remplacé par le filtrage de la partie émergée,** décrit dans `../spec-relief-tectonique.md`.
- **Les mesures antérieures du portage,** sur 600 mailles près du centre des faces : médiane 6 cm, p99 1,8 m, maximum 13 m sur le mur d'une fosse ; la première version, 6 cm, 1,6 m et 3,4 m.

## Les étapes 1 à 3 telles que faites le 2026-10-31, avant la seconde passe

Corrigé le même jour : les côtes, les rifts, les chaînes, le budget du démarrage, les entrées du niveau 0 (`../spec-relief-tectonique.md`). Les mesures et les défauts d'alors.

**Le stockage d'alors :** quatre tranches par face sur le GPU, 49,5 Mo ; la tranche 3 portait un soulèvement indicatif, celui de la seule frontière la plus proche, et la distance au bord des continents jusqu'à 3 000 km. Le fichier, `EXOTECT1`, ces quatre tranches.

**Le calcul d'alors :** les propagations sur un tas, une à une le long du chemin critique ; les champs régionaux à pleine résolution ; deux propagations des dorsales avant la polarité ; les cratons sur les continents d'après les marges actives.

### Les mesures

**Les ordres de grandeur,** portage CPU, graine 0, 400 000 points, mailles de 2 km :

| Mesure | Relief tectonique | Cible |
|---|---|---|
| Terres | 33,0 % ; graines 1 et 2 : 33,8 et 30,4 % | 30 à 45 %, plus proche de la Terre, 29 % |
| Mode des terres | +125 m, médiane 366 m | la Terre : médiane vers 400 m |
| Mode des océans | −4 625 m, médiane −4 447 m | −4 à −5 km |
| Sommets des 12 plus hautes chaînes | 6,8 à 7,9 km | 6 à 8 km |
| Fosses, les 8 plus profondes | −9,4 à −10,5 km | −8 à −10 km |
| Au-dessus de 3 km | 1,9 % de la surface | la Terre : 1,6 % |

- **Pourquoi 33 % de terres :** 44 % de croûte continentale, dont les plateaux, les talus et les bassins bas noient un quart, comme sur Terre (41 % pour 29 %).
- **L'hypsométrie est bimodale,** vers +0,1 et −4,6 km : `tecto3_hypsometrie.png` dans les captures de la session.

**Le temps :**
- **La carte tectonique :** 2,5 s au démarrage, contre 1 s à la première version : neuf propagations au lieu de quatre, deux classements des frontières. Mémoire GPU 50 Mo, contre 32.
- **Le calcul GPU du terrain,** caméra en mouvement, terrain recalculé à chaque image, mêmes six vues : 0,3 à 0,7 ms aux altitudes basses et moyennes, contre 0,5 à 1,3 ms ; au ras du sol, 0,7 à 2,5 ms selon la charge, contre 3,9. Les lieux des vues de référence sont désormais en mer, sauf l'orbite et le sol de `macro`, en forêt.
- **La carte de la planète :** 18 ms sur le GPU.

**Le jeu de vérification :** la compilation sans erreur ni nouvel avertissement ; les vues en vol de `tools/tests/2026-10-31-relief-tectonique.txt` ; la planche `tecto3_planche.jpg`.

### Les défauts connus

- **Les côtes sont lisses entre 50 et 5 km** sur les plaines côtières : le détail y est faible, la côte suit le seuil d'un champ lisse.
- **Les rifts sont nombreux,** 17 % des frontières, et leurs grabens souvent noyés en mers étroites aux murs réguliers.
- **Les chaînes à 300 km sont des rides ondulées,** un peu marbrées ; aucun réseau de vallées ne les draine.
- **La vue `relief` montre les facettes du maillage** sur les profils vifs vus d'orbite ; le relief du jeu ne les montre pas.
- **Pas encore de points chauds, de cônes volcaniques, de collines abyssales orientées par l'âge.**
- **Les vues de référence de `base_lumiere` tombent en mer :** il faut de nouvelles vues de contrôle sur terre ; la référence du banc de qualité ne vaut plus.
- **Le temps de démarrage :** 2,5 s pour une planète ; pour un système, le calcul en parallèle des corps reste à faire.
- **Aucune vallée creusée :** en attendant le niveau 0, `valleys` ne change rien.

## L'étape 1 telle que faite le 2026-10-31, avant la correction des continents

Les plaques y étaient entières, toutes continentales ou toutes océaniques ; chaque côte était une frontière de plaques. Corrigé le même jour : la croûte continentale par lieu, les marges passives et actives (`../spec-relief-tectonique.md`, la carte tectonique).

### La carte tectonique, première version

**En place, le relief ne la lit pas.** Elle se calcule au démarrage et se montre dans six vues de diagnostic.

#### Le calcul, `Tectonics.cpp`

**Une carte par corps céleste :** `Tectonics::Build({ seed, radiusKm })`. Le même corps donne la même carte, au bit près ; la planète prend la graine du relief, `CUR_SEED`.

1. **La grille :** le cube de la carte de la planète, 6 × N², N la puissance de deux qui donne des texels de 20 km environ. Pour la planète, 512².
2. **Les coûts :** des fBm de bruit de gradient, de 2 000 à 60 km, en exp(3 fBm) : la moitié à deux fois la médiane à un écart-type.
3. **Les plaques :** 12 à 20 germes, chacun le plus éloigné des autres parmi 24 tirés. Une croissance concurrente à coût bruité, des vitesses de 0,4 à 2,5 : des plaques de 0,3 à 17 % de la surface, aux contours irréguliers, jamais des arcs de grand cercle.
4. **Continentale ou océanique :** les plaques dans un ordre tiré, continentales tant que leur part reste sous une cible de 30 à 40 %.
5. **Les mouvements :** un pôle d'Euler tiré sur la sphère ; 40 à 100 mm/an à 90° du pôle pour une plaque océanique, 10 à 40 pour une continentale.
6. **Les frontières :** toute cellule voisine d'une autre plaque. La normale entre les cellules des deux plaques sur 4 pas ; la vitesse relative (ω_a − ω_b) × p, projetée sur la normale, moyennée le long de la frontière sur environ 100 km, des deux côtés.
   - **transformante** si la composante normale fait moins de 40 % de la vitesse relative ;
   - **convergente :** subduction océan sous continent, océan sous océan, collision de deux continents ;
   - **divergente :** dorsale si un côté est océanique, rift entre deux continents.
7. **La polarité, un choix par paire de plaques :** l'océanique sous la continentale ; de deux océaniques, la croûte la plus vieille ; de deux continents, celui qui avance le plus dans l'autre.
8. **L'âge du fond océanique :** la distance à la dorsale la plus proche de la plaque, sur la demi-vitesse d'expansion moyenne de la plaque ; 200 Ma au plus, et sur une plaque sans dorsale.
9. **Les sutures anciennes :** chaque continent découpé en 1 à 8 cratons par la même croissance, un par 2 % de la surface ; une suture entre deux cratons, d'un âge tiré de 100 à 1 000 Ma.
10. **Les distances :** une propagation du germe le plus proche, celle du niveau 0, depuis le point de frontière entre deux cellules ; lissées sur deux texels.
11. **Le soulèvement indicatif,** en mm/an, d'après le type, la polarité, la convergence et la distance :
    - subduction : fosse sur la plaque plongeante ; cordillère de 150 à 400 km, ou arc insulaire, sur l'autre ;
    - collision : chaîne sur les deux plaques, bassin d'avant-pays devant ;
    - rift : graben entre deux épaulements ; ailleurs, 0.
12. **La roche, par classe :** croûte océanique ; volcanique, sur les arcs ; plissée jeune, là où le soulèvement passe 1 mm/an ; sédiments, avant-pays, rifts et plates-formes ; plissée ancienne, à moins de 150 km d'une suture ; socle, en taches tirées par un bruit.

**Trois propagations en parallèle,** chacune sur son fil : les cratons et leurs sutures, les dorsales, les frontières. Le reste, cellule par cellule sur tous les fils.

#### Le stockage, `Tectonics.hlsli`

**Un tableau de deux cubes RGBA16F, mipmappés, `t18` :**
- **cube 0 :** distance à la frontière la plus proche de la plaque (km), positive sur une plaque continentale, négative sur une océanique, qui ne passe par 0 qu'aux marges ; convergence à travers elle (mm/an), négative quand les plaques s'écartent ; soulèvement (mm/an) ; âge du fond océanique (Ma).
- **cube 1 :** distance à la suture la plus proche (km) ; son âge (Ma) ; deux classes, lues sans filtre par `Gather` au mip 0 : la roche, plus 8 sur un continent ; la plaque, plus 32 fois le type de la frontière la plus proche, plus 256 si la plaque plonge sous elle.

**Le signe par la croûte, pas par la polarité :** une distance signée par la polarité sauterait de −d à +d entre deux frontières, et tout filtre y inventerait un faux zéro. Signée par la croûte, elle est continue partout ; la polarité passe dans les classes.

**La résolution, 512² pour la planète :** 25 km au centre d'une face, 11 km aux coins, 20 km en moyenne.
- **Ce qu'elle porte :** des formes de plus de deux texels, 40 km ; les grandes formes en font plus de 50.
- **Les arêtes vives viennent des profils analytiques de l'étape 2,** posés sur des distances lisses, qui s'interpolent à une fraction de texel près.
- **1 024² ne servirait pas :** quatre fois la mémoire et le temps, pour des échelles que le bruit fait mieux. Il ne tiendrait plus le budget d'un système entier.

#### Les vues de diagnostic

**Par `MYPLANETENGINE_VIEW`, par nom en mode batch, ou en fin de place d'une ligne de test.** Sans lumière, ni air, ni nuages ; elles se lisent de l'orbite à 500 km.

| Nom | Ce qu'elle montre |
|---|---|
| `plates` | chaque plaque sa couleur, assombrie sur les océans ; leurs frontières en noir |
| `boundaries` | le type de la frontière la plus proche sur 250 km : rouge, subduction sous un continent ; orange, sous un océan ; magenta, collision ; cyan, dorsale ; jaune, rift ; vert, transformante. Deux fois plus sombre sur la plaque qui plonge ; les sutures en brun |
| `boundarydist` | la distance signée jusqu'à 3 000 km, orange sur les continents, bleue sur les océans ; une ligne tous les 250 km |
| `crustage` | l'âge du fond, rouge aux dorsales à violet à 200 Ma ; sur les continents, les sutures, claires à 100 Ma, sombres à 1 000 Ma |
| `rocktype` | croûte océanique bleu nuit, volcanique rouge, plissée jeune brune, sédiments sable, plissée ancienne olive, socle rose |
| `uplift` | le soulèvement, orange jusqu'à +6 mm/an, bleu jusqu'à −6 |

**À juger en vol :** `tools/tests/2026-10-31-tectonique.txt`, chaque vue de l'orbite puis à 500 km sur un trait marquant.

#### Les mesures

- **Le temps :** 0,93 à 0,99 s au démarrage, au titre « tectonique … ms » ; 0,89 à 1,0 s hors du moteur. Mesuré avec d'autres sessions sur la machine.
- **La mémoire :** 32 Mo sur le GPU, plus 32 Mo de tampon d'envoi, rendus au démarrage. Un pic de 190 Mo sur le CPU pendant le calcul, rendus après.
- **Le déterminisme :** deux calculs, le même fichier au bit près.
- **Le rendu du jeu :** identique au bit près sur les six vues de contrôle, de l'orbite au sol.
- **Les plaques, sur trois graines :** 15, 15 et 19 plaques, de 0,3 à 17 % de la surface ; 31, 35 et 38 % de croûte continentale.
  - **Contre Bird 2003 :** la plus grande plaque terrestre, le Pacifique, fait environ 20 % ; les nôtres plafonnent à 17 %.
  - **Il manque les microplaques :** Bird en compte des dizaines sous 1 %, l'instantané n'en a que 2 ou 3.
- **Les frontières, graine 0, en part des cellules de frontière :** subduction sous un continent 41 %, sous un océan 4 %, collision 1 %, dorsales 23 %, rifts 1 %, transformantes 29 %.

#### Le budget d'un système solaire

**Le temps et la mémoire suivent la surface :** la grille garde des texels de 20 km, sa taille suit le rayon.

| Corps | Grille | Mémoire GPU | Temps |
|---|---|---|---|
| Taille de la Terre ou de Vénus | 512² | 32 Mo | 1 s |
| Taille de Mars, Mercure, Ganymède, Titan | 256² | 8 Mo | 0,23 s |
| Taille de la Lune, Io, Europe | 128² | 2 Mo | 0,07 s |

- **Le budget visé :** 150 Mo et 2 s pour tout le système. Un système comme le nôtre, sans les géantes : deux grandes planètes, cinq corps moyens, cinq petits ; 114 Mo, 3,5 s de calcul à la suite, moins de 1,5 s estimées en calculant les corps en parallèle.
- **Au-delà :** le cache sur disque par graine, 32 Mo par planète de la taille de la Terre.
- **Pas encore fait :** la liste des corps du système ; l'étape 1 n'en calcule qu'un.

#### Ce qui reste incertain

- **Les plaques sont entières :** toute continentale ou toute océanique. Pas de marge passive ; chaque côte est une frontière de plaques. La recherche pose des continents indépendants des plaques, `recherche-relief.md`, 6.2, étape 1 : à décider avant l'étape 2.
- **Leurs formes :** irrégulières mais souvent rondes ; les petites plaques en taches, jamais allongées.
- **Quelques traits transformants isolés** coupent encore des subductions, sur une ou deux cellules.
- **Les classes sont au texel :** vues de près, à 500 km, leurs limites marchent par 20 km. Les champs, eux, sont lisses.
- **L'âge est plat, à 200 Ma,** sur une plaque océanique sans dorsale.
- **Le temps** a été mesuré sur une machine chargée ; à refaire au repos.
