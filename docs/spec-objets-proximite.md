# Spécification : les objets de proximité

Statut : en place, `jalon/19-detail-sol`. Piste ouverte le 2026-10-24, tag `piste/objets-proximite`. Étape 3 faite le 2026-10-25 : un champ de pierrosité décide où il y a des débris ; des cailloux plus petits, moins nombreux.

**En bref :**
- **Le détail du sol, pas la roche :** ce qu'on voit debout à ses pieds, des cailloux et des touffes posés sur le sol ; jamais la roche en place ni son relief, qui relèvent de la géométrie.
- **Des débris seulement dans les régions caillouteuses :** un champ de pierrosité de 0,5 à 32 km, sur la grille de la planète, plus haut sur les éboulis, le sol nu sec et les pentes. Aucun débris sur 74 % des prairies, 70 % des sables et sols nus, 11 % des éboulis.
- **Une recette par sol, là où il est caillouteux :**
  - sable et sol nu : surtout de petits cailloux de 3 à 6 cm, moins de 6 à 12 cm, de rares plus gros ; le gravier plus fin est la texture du sol ; quelques touffes sèches ;
  - herbe : des touffes partout, caillouteuse ou non ; des rochers à demi enfouis, rares, par taches ;
  - éboulis : leurs pierres ;
  - des blocs amassés seulement au pied des vraies parois, plus au fond de chaque ravine.
- **Calée sur deux photos prises debout,** comptées sur une tache de premier plan ; les lois publiées en garde-fou.
- **Chaque objet a sa place fixe sur la planète :** une cellule de la grille cartésienne de la planète, jamais le maillage glissant ni l'ancre de 64 m.
- **La caméra décide seulement s'il se voit :** il sort du sol quand il couvre 6 pixels, entier à 9 ; jamais là où le maillage ne peut pas porter son pied.
- **Par taches et par amas, jamais semés partout :** les rochers par taches, les cailloux et les touffes par amas plus doux.
- **Les pentes suivent la gravité :** rien au-delà de l'angle de repos, les plus gros d'abord.
- **Son pied est sur le sol exact,** complexplanet sans filtrage, enfoui dans un sol meuble, à peine assis sur la roche. L'écart au sol du maillage, mesuré, reste sous l'enfouissement.
- **Mesuré :** sur le sable caillouteux, 5,2, 1,0, 0,14 et 0,008 cailloux par m² de 3 à 50 cm, le bas de la photo, qui en a 16, 6 et 0,5 ; dans l'herbe, 9 touffes par m² sur 34 % du sol, la photo 6 à 15 sur 30 à 60 % ; aucun objet flottant ; aucun surgissement.

## Le détail du sol et les roches : la ligne

**Cette piste fait le détail du sol :** des objets posés, détachés, à l'échelle d'une photo prise debout.
- **Les cailloux et les graviers,** partout où le sol en porte : sable, sol nu, éboulis, herbe.
- **Les touffes d'herbe,** partout dans l'herbe ; quelques touffes sèches sur le sable et le sol nu.
- **Les roches moyennes et grosses, seulement là où elles s'accumulent vraiment :** les éboulis, le pied des vraies parois, des rochers à demi enfouis dans l'herbe par endroits.
- **Posés ou enfouis selon le sol :** à demi dans la terre, le sable ou les fines d'un éboulis ; à peine assis sur la roche.

**Les roches en place sont la piste de la géométrie** (`recherche-geometrie-proximite.md`, sur sa branche) : la roche nue, ses parois, ses saillies, ses blocs qui en dépassent. Un bloc à demi enfoui dans une paroi est du relief, pas un objet ; posé comme un objet, il se lit comme une mauvaise intégration.

## Ce que fait l'industrie

Recherche du 2026-10-24, sources primaires.

- **Horizon Zero Dawn, placement procédural sur GPU** ([van Muijden, GDC 2017](https://www.guerrilla-games.com/media/News/Files/GDC2017_VanMuijden_GPUBasedProceduralPlacementInHorizonZeroDawn.pdf)) :
  - le monde est construit autour du joueur, à la volée, par des passes de calcul ;
  - chaque type d'objet a une carte de densité, calculée par un graphe de règles sur les données du terrain ;
  - la densité est comparée à un motif de seuils fixe, posé sur le monde : le placement est déterministe et localement stable, changer une densité ne déplace que les objets voisins ;
  - chaque type a son rayon de placement autour du joueur.
- **Ghost of Tsushima, l'herbe procédurale** ([Wohllaib, GDC 2021](https://gdcvault.com/play/1027214/Advanced-Graphics-Summit-Procedural-Grass)) : chaque brin est généré sur GPU, avec son aspect et son animation propres, des hectares d'herbe dans des limites de mémoire et de temps tenues.
- **Far Cry 5** ([Carrier, GDC 2018](https://gdcvault.com/play/1025557/Procedural-World-Generation-of-Far)) : biomes, végétation et rochers de falaise générés par des outils Houdini, mais hors ligne, à la construction du monde. Pas transposable à une planète entière.
- **Unreal Engine 5, PCG** ([modes de génération](https://dev.epicgames.com/documentation/en-us/unreal-engine/using-pcg-generation-modes-in-unreal-engine), [génération hiérarchique à l'exécution](https://dev.epicgames.com/documentation/unreal-engine/runtime-hierarchical-generation)) :
  - le domaine est découpé en grilles, une taille de cellule par classe d'objets : grande pour les arbres et les rochers, petite pour l'herbe et les pierres ;
  - à l'exécution, les cellules sont générées dans un rayon propre à chaque taille de grille, autour de la caméra.
- **DirectX 12, dessin indirect** ([Microsoft](https://learn.microsoft.com/en-us/windows/win32/direct3d12/indirect-drawing-and-gpu-culling-)) : une passe de calcul trie les instances et écrit les arguments du dessin ; `ExecuteIndirect` les lit, le compte venant du GPU.
- **Les fondus sans pop :** le fondu tramé est le défaut du feuillage d'Unreal, avec ses défauts connus, une marche de pop en fin de fondu ([UE-40065](https://issues.unrealengine.com/issue/UE-40065)) et le coût de dessiner les deux niveaux ; Cesium fait monter un seuil de tramage dans le temps ([Cesium](https://cesium.com/blog/2022/10/20/smoother-lod-transitions-in-cesium-for-unreal/)).
- **Grille et tirage** ([Red Blob Games](https://redblobgames.com/x/1830-jittered-grid), [Bridson 2007](https://www.cs.ubc.ca/~rbridson/docs/bridson-siggraph07-poissondisk.pdf)) : la grille décalée au hasard est le substitut bon marché du tirage de Poisson, avec un peu plus d'amas et de trous ; le tirage de Poisson est global et séquentiel, impossible sur une planète sans fin.

**Les débris réels, leurs tailles et leurs pentes :**
- **Les tailles des champs de pierres** ([Golombek et Rapp 1997](https://doi.org/10.1029/96JE03319), [Golombek et al. 2003](https://ntrs.nasa.gov/citations/20030111177), [InSight 2021](https://authors.library.caltech.edu/records/d1t32-akr32)) :
  - sur les sites Viking et sur des sites terrestres de toutes origines, la part du sol couverte par les pierres de largeur D ou plus suit une exponentielle, k exp(−q D) ;
  - k est l'abondance, la part couverte par toutes les pierres ; q = 1,79 + 0,152 / k ;
  - les sites mesurés vont de quelques pour cent à quelques dizaines de pour cent ; InSight retrouve la loi en 2021.
- **La fragmentation** ([Turcotte 1986](https://doi.org/10.1029/JB091iB02p01921)) : les fragments de roche suivent souvent une loi de puissance du nombre selon la taille, sur un large domaine d'échelles. Beaucoup de petits, peu de gros.
- **Les talus et éboulis** ([Kirkby et Statham 1975](https://doi.org/10.1086/628097), [éboulis, synthèse](https://en.wikipedia.org/wiki/Scree), [JNCC, mouvements de masse](https://data.jncc.gov.uk/data/c9bdfe0b-ca6f-4a90-87a6-d03f64e8124c/gcr-v33-mass-movements-c4.pdf)) :
  - un talus sec se tient à son angle de repos, de 33 à 37° environ ; au-delà, rien de meuble ne tient ;
  - le tri par la chute : les plus gros fragments vont le plus loin, au pied, où la pente s'adoucit ;
  - les débris s'accumulent au pied des parois qui les fournissent.
- **Les fragments de roche des sols** ([Poesen et Lavee 1994](https://doi.org/10.1016/0341-8162(94)90050-7), [versants semi-arides d'Espagne](https://bibliotecadigital.ipb.pt/entities/publication/db20b92a-6dc6-440f-851a-fa51859fdec0)) :
  - leur couverture et leur taille sont le résultat de processus, tri et érosion sélective des fines, pas un tirage uniforme ;
  - sur les versants semi-arides, la couverture croît avec la pente, les fines partant les premières.
- **Les blocs dans les chenaux** ([Shobe, Tucker et Anderson 2016](https://doi.org/10.1002/2016GL069262)) : les gros blocs des torrents de montagne viennent des versants voisins et s'amassent au fond des chenaux.
- **Les regs** ([Wood, Graham et Wells 2005](https://www.resolutionmineeis.us/sites/default/files/references/wood-graham-wells-2005.pdf)) : un pavage désertique couvre plus de 65 % du sol de clastes, surtout des graviers ; il forme une mosaïque d'unités distinctes par la taille, la couverture et le tri. Les graviers sont la texture du sol nu ; nos objets, de 6 cm et plus, y restent rares.
- **Les semis de pierres sont agrégés, pas aléatoires** ([Hickory Run, GSA 2010](https://gsa.confex.com/gsa/2010AM/webprogram/Paper178867.html), [Mars, plaines du nord](https://ri.cmu.edu/?p=9666), [Ryugu et Itokawa](https://cosmochemistry-papers.com/2025/06/13/statistical-evaluation-of-boulder-spatial-patterns-on-asteroids-and-application-to-eros-itokawa-and-ryugu/)) : 12 000 blocs d'un champ de Pennsylvanie forment des amas et des alignements de 3 à 7 m ; sur Mars, des degrés d'agrégation variés ; sur les astéroïdes, les petits blocs sont groupés. Les éboulements d'une falaise de Catalogne aussi.
- **Les photos de `docs/images/cible-*.jpg`, à l'œil, sans échelle connue :** le désert porte des pierres de quelques centimètres à quelques décimètres, éparses, quelques pour cent du sol ; au pied des badlands, des blocs épars sur la prairie ; les canyons de basalte, des talus de blocs sous les falaises.

**Ce qu'on en retient :**
- **le placement est une fonction pure de la cellule,** évaluée sur GPU, sans état : HZD, PCG ;
- **une grille par classe de tailles,** chacune avec son rayon : PCG ;
- **une densité lue sur le terrain,** comparée à un tirage fixe : HZD ;
- **un dessin indirect dont le GPU écrit le compte :** DX12 ;
- **un fondu qui ne dépend que de la distance,** sans bruit temporel.

## Les règles

**Une place fixe, sur la grille de la planète** (`principes.md`, tout motif se calcule sur la grille de la planète).
- **La grille :** le quadrillage cartésien du repère de la planète. Là où la plus grande composante de la verticale est selon l'axe a, les objets viennent de la grille des deux autres axes, projetée selon a sur la sphère : pas de couture qui bouge, une cellule couvre s² / |up.a| du sol.
- **Une octave de tailles par niveau de grille et par classe :** l'octave k porte des objets de 2^k à 2^(k+1) m, décalés au hasard dans leur cellule. Les cailloux, de 3 cm à 2 m, un candidat par cellule de 4 × 2^k m ; les touffes, de 12 à 50 cm, plus denses, un par cellule de 2 × 2^k m.
- **Tout vient du hachage de la cellule :** place, taille, forme, rotation, teinte, tirage. Rien du maillage, rien de la caméra.
- **Les calculs en double précision** pour la place sur la sphère ; sommes et produits seulement, le GPU n'a pas de division en double.

**Une recette par sol, à l'échelle d'une photo prise debout.**
- **Les parts des sols, lues à sa place** par `GroundMaterials`, filtrées à sa cellule, comme les pixels les superposent : herbe, sable, sol nu, éboulis, roche, sable de plage, neige. Rien sur la roche nue ni sous la neige.
- **Les débris d'abord, s'il y en a** (`OBJECT_STONY`) : le champ de pierrosité, un bruit de gradient de la planète de 0,5 à 32 km, d'écart type 0,29, propre aux débris ; relevé de 0,22 fois ce qui retire au sol ses fines ou lui apporte des débris : trois fois la part d'éboulis, le sol nu d'autant plus que l'air est sec, la tangente de la pente. Des débris au-delà de 0,27, entièrement au-delà de 0,42, par la règle des limites. Les touffes n'en dépendent pas.
- **Le gravier sous 3 cm est la texture du sol :** la tuile fine porte les longueurs d'onde sous 3 cm, le scan de sable et gravier celles de 3 à 50 cm. Les objets commencent à 3 cm.
- **Sable et sol nu, plage comprise :**
  - des cailloux, 2 % du sol à 3 cm, la part s'effaçant au-delà de 8 cm (`PEBBLES`) : surtout de petits, cinq fois moins à chaque octave au-dessus, de rares galets, presque pas de blocs ;
  - quelques touffes sèches, 1 % du sol par octave (`TUFT_COVER`).
- **Herbe :**
  - des touffes partout, 20 % du sol par octave de 12 à 50 cm (`TUFT_COVER`) ;
  - des rochers à demi enfouis, par taches, la loi de Golombek et Rapp à l'abondance 0,03 (`GRASS_ROCKS`), le bas des sites mesurés.
- **Éboulis :** leurs pierres, la loi de Golombek et Rapp à 0,05 (`DEBRIS_ABUNDANCE`).
- **Les éboulements, au pied des vraies parois seulement :** où le sol s'adoucit sous 10 à 20° (`OBJECT_GATHER`) sous une pente moyenne de plus de 35 à 45° sur les 16 m au-dessus (`OBJECT_LANDFORM`), la loi à 0,25. Plus au fond de chaque creux : une ravine n'est pas un éboulement.
- **Les crêtes et les hauts de falaise,** courbure négative sur 16 m (`OBJECT_CREST`) : 10 % des pierres d'éboulis et d'éboulement.
- **Par taches et par amas,** un champ du bruit de gradient de la planète, de 8 à 64 m, de moyenne 1 : les rochers par taches, nulles sur 58 % du sol (`OBJECT_PATCHES`) ; les cailloux et les touffes par amas, de 0,4 à 1,6 fois leur moyenne (`OBJECT_CLUMPS`). Ils changent le nombre, pas les tailles.
- **L'angle de repos** (`OBJECT_REPOSE`) : rien au-delà de 38° pour la plus petite octave, un degré de moins à chaque octave, comme le tri d'un talus ; la part s'efface sur 3°.
- **Le candidat est gardé** si son tirage est sous la probabilité qui donne cette part.
- **Le sol à sa place est le sol exact :** complexplanet sans filtrage, sa pente sur 1 m. Jamais celle du maillage, qui glisse : un objet au seuil apparaîtrait et disparaîtrait.

**La caméra décide seulement s'il se voit.**
- **Par sa taille à l'écran :** il sort du sol à 6 pixels, entier à 9 (`OBJECT_PIXELS`). La même règle que les octaves des bruits, qui s'effacent selon le pixel.
- **Par le maillage sous lui :** il n'apparaît que là où les mailles font moins d'une fois et demie sa largeur, entier sous une fois (`OBJECT_CELLS`). Plus grossier, le maillage dessine le sol trop loin du sol exact.
- **Le fondu est une croissance :** l'objet grandit depuis son pied, enfoui ; il sort du sol. Pas de tramage, pas de transparence, rien qui dépende de l'image précédente.

**Son pied est sur le sol exact, enfoui selon le sol** (`OBJECT_BURIAL`).
- **Dans un sol meuble,** terre, sable, herbe, fines d'un éboulis : 40 % de sa hauteur. Une touffe, son pied.
- **Sur la roche,** à peine assis : 8 %.
- **Jamais moins de 3 mm,** plus que l'écart mesuré au sol du maillage près de la caméra, à hauteur d'homme.

## Le flottement : le pied sur le sol exact

**Le problème :** le sol est dessiné par le maillage glissant, dont les sommets échantillonnent complexplanet, filtré à leur maille. Entre ses sommets, le sol dessiné s'écarte du sol exact ; l'écart change quand le maillage glisse.

**Les deux choix :**
- **la hauteur du maillage sous l'objet :** écart nul, mais l'objet monte et descend à chaque image avec le maillage. Refusé : c'est le glissement qu'on veut éviter ;
- **le sol exact, plus un enfouissement :** retenu. L'objet ne bouge jamais ; il faut que l'écart reste sous l'enfouissement, ce que le banc mesure.

**Pourquoi le sol exact tient.** Sous des mailles de 3,4 m, le maillage porte toutes les octaves de complexplanet ; sous 2 m, l'arrondi des crêtes est celui de `CREASE_MIN_CELL` ; sous 4 m, la grille du bruit est en double précision. Le sol exact est donc la limite du maillage quand ses mailles rétrécissent : l'écart n'est que l'erreur d'interpolation entre sommets, de l'ordre de maille² × courbure / 8.

**Le plancher : la précision de complexplanet.** Près du sol, l'écart ne baisse plus avec la maille : moyen 3,3 mm à 1,5 m comme à 6 m, avec des mailles quatre fois plus fines ou plus grosses. Déplacer le point de 1 mm change l'altitude calculée jusqu'à 16 mm à 2,6 km d'altitude, 1,2 mm à 1 km : l'arrondi des flottants dans la somme des octaves. Ce bruit est celui du maillage lui-même ; il reste sous 2 pixels.

**Ce qui l'a borné :** des blocs de 2 m vus de 200 m, dans des mailles de 4 m, flottaient de 84 cm. D'où la règle des mailles : un objet n'apparaît que si le maillage sous lui est assez fin pour porter son pied.

## Le plan

1. **Des cailloux, pierres et blocs posés :** fait, ci-dessous. Choisis d'abord : statiques, sans vent, ils prolongent des matériaux qui existent, et `GroundMaterials` donne leurs parts partout. Les éboulis d'abord, puis le pied des pentes et les sols caillouteux, avec la loi des tailles et l'angle de repos.
2. **Les ombres portées :** sans elles, une pierre au soleil reste posée sur le sol plutôt que dedans. Une carte d'ombre de proximité servira aussi l'herbe et les arbres.
3. **Tous les terrains :** les blocs sous la neige, qui en dépassent selon leur taille ; les champs de blocs loin des pentes, des chaos de granite, qui demandent une donnée de géologie. Le sol nu et les déserts sont faits. Une source de débris de plus, le même système.
4. **Les touffes d'herbe :** commencées à l'étape 2, la même grille et la même règle de pixels, des brins générés ; reste le vent.
5. **Les brins :** une octave de plus vers le bas, générés sur GPU comme dans Ghost of Tsushima.
6. **Les arbres :** commencés le 2026-10-25, `recherche-vegetation.md` : trois espèces selon le climat, une classe de plus sur la même grille, de 0,5 à 64 m ; au-delà de leur portée, la canopée dans la matière du sol, ce que les objets dessinent retiré.

**Ce qui reste ouvert :**
- **un cache par cellule,** si le coût monte avec les classes : aujourd'hui tout est recalculé à chaque image ;
- **des niveaux de détail des formes :** une seule forme de 1 280 triangles, dessinée en 0,01 à 0,08 ms ;
- **le plancher de précision de complexplanet,** à signaler au bruit : de 1 mm à 1,6 cm selon l'altitude.

## Étape 1 : mesures

**Le banc :** `tools/banc_objets.py`, sur trois lieux au soleil « 10 70 » : des éboulis (1,09° N, 110,67° E), une pente de roche (14,96° S, 119,99° E), une paroi (0,23° S, 118,42° E). Les mesures du flottement viennent du moteur lui-même : chaque objet placé compare son pied au triangle du maillage sous lui, et la barre de titre en donne le bilan. Tests en vol : `tools/tests/2026-10-24-objets.txt`.

**Le flottement, le long d'une approche de 200 à 1,5 m :**

| Lieu | Objets | Écart moyen | Sol sous un pied, au plus | Part de l'enfouissement, au plus | Flottent | À l'écran, au plus |
|---|---|---|---|---|---|---|
| Éboulis | 0 à 415 | 3,3 mm près du sol, 32 mm à 100 m | 46 mm | 87 % | 0 | 1,75 px |
| Roche | 0 à 805 | 2,7 mm, 39 mm à 100 m | 114 mm | 24 % | 0 | 0,52 px |
| Paroi | 0 à 399 | 0,3 mm, 42 mm à 100 m | 127 mm | 30 % | 0 | 0,60 px |

- **Aucun objet ne flotte,** à aucune hauteur ; le sol monte au plus de 30 % de la hauteur visible d'un objet.
- **Sans la règle des mailles,** sur la paroi : à 200 m, des blocs de 2 m dans des mailles de 4 m, 84 cm sous un pied, 3 objets sur 6 flottent, 2,9 px ; à 100 m, un flotte.
- **Le pixel et demi des éboulis près du sol** est le plancher de précision de complexplanet, pas l'interpolation : à 1,5 m comme à 6 m, l'écart moyen reste de 3,3 à 3,8 mm avec des mailles quatre fois plus fines ou plus grosses.

**Le pop, le long d'une descente de 40 à 3 m par pas de 1,5 %, 174 pas :** le moteur liste les objets de chaque image, nommés par leur graine ; un objet qui arrive loin des bords de l'écran est mesuré à son arrivée.

| Lieu | Arrivées | Largeur à l'arrivée, médiane / au plus | Référence : objets entiers dès 7,5 px |
|---|---|---|---|
| Éboulis | 684 | 0,00 / 0,05 px | 8,6 / 12,0 px |
| Roche | 421 | 0,00 / 0,04 px | 7,5 / 10,3 px |
| Paroi | 565 | 0,00 / 0,06 px | 8,5 / 15,6 px |

- **Un objet grandit au plus de 0,75 px d'un pas à l'autre ;** 2,5 px sur la paroi, un bloc proche qui grandit en se rapprochant.

**Le tremblement,** `tools/banc_tremblement.py`, avant et après, avec et sans lissage temporel :

| Vue | Avant | Avec les objets |
|---|---|---|
| Éboulis à 1,6 m | 3,59 / 8,64 | 3,49 / 8,39 |
| Éboulis à 10 m | 0,64 / 2,71 | 0,61 / 2,63 |
| Roche à 3 m | 0,04 / 0,23 | 0,04 / 0,23 |
| Paroi à 12 m | 0,02 / 0,19 | 0,02 / 0,18 |
| Blocs à 3 m | 0,03 / 0,24 | 0,02 / 0,23 |

- **Jamais plus qu'avant,** un peu moins là où les pierres couvrent le sol qui tremble : elles ne bougent pas.

**Le banc de qualité,** 30 lieux, graine 1, contre `tools/banc_qualite_reference.json` :
- **la roche gagne :** trous d'échelle au p95 de −0,8 à −2,7 dB de 12 à 800 m, répétition −0,1 de 50 à 800 m ;
- **son détail fin rapporté au moyen baisse à 12 m,** −4,6 dB en médiane, dont −1,0 dB du nettoyage de la roche avant cette piste : les blocs ajoutent du contraste aux échelles moyennes ;
- **les autres matériaux bougent de moins de 0,4 dB ;** le seul p95 au-delà de 10 %, le trou du sable à 3 km, +0,4 dB, est à une hauteur où aucun objet ne se dessine : le bruit du banc.

**Le coût,** GPU au repos, RTX 4070 Ti, neuf vues de trois lieux, de 3 à 60 m :
- **placement :** 0,31 à 0,43 ms, pour 50 à 800 objets gardés sur 400 à 3 200 candidats évalués ; le calcul du terrain prend 2,1 à 5,0 ms ;
- **dessin :** 0,01 à 0,08 ms, une seule forme de 1 280 triangles ;
- **sous la charge des autres instances,** les temps gonflent tous : placement de 0,6 à 4,9 ms, pour un calcul du terrain de 6 à 20 ms.

**Le chemin vers ce coût,** en part du calcul du terrain, les mêmes objets à chaque fois :
- **une passe unique,** une cellule par fil : 40 à 80 %. Les candidats vus sont épars parmi les cellules : chaque vague déroulait le sol exact pour quelques fils seulement ;
- **la vue tirée du maillage, à une marge près,** au lieu de toute hauteur du niveau de la mer aux sommets : 17 à 30 % ;
- **deux passes,** une légère sur les cellules, une lourde sur la liste compacte des candidats, lancée en indirect : 7 à 15 %.

## Étape 1 bis : des cailloux, leurs tailles et leurs pentes

Le 2026-10-24, après le vol de l'utilisateur : « beaucoup sur des pentes abruptes, alors qu'ils ne tiendraient pas » ; « beaucoup de rochers de taille moyenne » ; « à demi enfouis dans des parois rocheuses, ça fait simplement mauvaise intégration ».

**Le banc :** `tools/banc_objets.py recensement`. Sur 23 lieux, ceux de roche, d'éboulis, de sol nu et de sable du banc de qualité et les nôtres, le moteur enregistre chaque cellule des fenêtres, gardée ou non, sans l'avis de la caméra (`MYPLANETENGINE_OBJECT_CENSUS`) : son sol, sa pente, la pente au-dessus, les parts des matériaux, la largeur de l'objet. 22 400 m² pour l'octave la plus fine, 6 km² pour la plus grosse.

**Ce qui a changé :**
- **les blocs à demi enfouis dans la roche nue sont retirés :** c'est du relief, la piste de la géométrie ;
- **une source de débris de plus, le pied des pentes ;** une autre, le sol nu et le désert caillouteux ;
- **les tailles suivent Golombek et Rapp,** au lieu d'une même part par octave ;
- **l'angle de repos selon la taille ;**
- **l'enfouissement selon le sol ;**
- **la lumière que le sol renvoie** sur les flancs et le dessous des pierres, `GROUND_ALBEDO` : sans elle, leurs faces à l'ombre étaient noires.

**Par pente, tout le sol,** objets par m² et part du sol couverte :

| Pente | Part du sol | Avant | Après | Dont 50 cm à 2 m, avant / après |
|---|---|---|---|---|
| 0 à 10° | 53 % | 0,001 ; 0,02 % | 1,09 ; 1,59 % | 65 / 9 % |
| 10 à 20° | 13 % | 1,23 ; 1,82 % | 1,20 ; 1,80 % | 18 / 12 % |
| 20 à 30° | 11 % | 1,10 ; 2,96 % | 1,06 ; 2,20 % | 35 / 22 % |
| 30 à 35° | 5 % | 4,57 ; 8,32 % | 2,95 ; 4,80 % | 28 / 14 % |
| 35 à 40° | 4 % | 4,74 ; 9,85 % | 0,76 ; 0,65 % | 30 / 0 % |
| 40 à 50° | 7 % | 3,11 ; 9,35 % | 0 | 38 / 0 % |
| 50 à 90° | 8 % | 2,42 ; 11,24 % | 0 | 45 / 0 % |

- **Avant, la couverture montait avec la pente,** jusqu'à 11 % sur les parois, des blocs pour près de moitié. **Après, plus rien au-delà de 40°,** le maximum sur les talus de 30 à 35°.

**Au pied des pentes,** le sol de moins de 20° selon la pente moyenne des 24 m au-dessus : sous plus de 40°, avant 0,42 objet par m² et 1,7 % du sol, **après 6,4 par m² et 15 %, dont 29 % de blocs.** Ailleurs sur le sol doux, 1,6 %.

**Par taille, sur les éboulis,** part de plus de 0,5 :

| Largeur | Avant, par m² ; couvert | Après, par m² ; couvert | Golombek et Rapp à l'abondance des lieux |
|---|---|---|---|
| 6 à 12 cm | 6,3 ; 3,65 % | 2,1 ; 1,20 % | 1,93 % |
| 12 à 25 cm | 1,67 ; 3,85 % | 0,69 ; 1,61 % | 2,93 % |
| 25 à 50 cm | 0,42 ; 3,87 % | 0,18 ; 1,69 % | 3,33 % |
| 50 cm à 1 m | 0,107 ; 3,90 % | 0,028 ; 1,01 % | 2,24 % |
| 1 à 2 m | 0,001 ; 0,20 % | 0,002 ; 0,27 % | 0,74 % |

- **Avant, les tailles moyennes, de 25 cm à 1 m, couvraient 7,8 % des éboulis,** plus que la loi ; après, 2,7 %. Par nombre, les petits cailloux dominent : 2,1 par m² contre 0,03 pour les pierres de plus de 50 cm.
- **L'écart à la loi est l'angle de repos :** les éboulis montent jusqu'à 40°, où seuls les petits tiennent.

**Sur le sol nu et le désert,** part de plus de 0,5 : rien avant ; après 1,5 objet par m², 3 % du sol, à la loi près pour chaque octave.

**Le flottement, la même approche de 200 à 1,5 m :** aucun objet ne flotte ; le sol descend au plus de 73 % de l'enfouissement, 1,3 px à l'écran.

**Le tremblement,** trois des vues de test, avant les objets puis avec, avec et sans lissage : talus 0,05 / 0,34 puis 0,04 / 0,31 ; reg 0,02 / 0,21 puis 0,02 / 0,20 ; éboulis 0,18 / 1,17 puis 0,16 / 1,07.

**Le pop et l'apparition ne changent pas :** la règle des pixels et celle des mailles sont les mêmes.

**Le coût :** un sol exact de plus par candidat, la pente au-dessus. Sous la charge des autres instances, le placement prend 13 à 24 % du calcul du terrain, contre 7 à 27 % avant dans les mêmes conditions ; le dessin, 0,06 à 0,6 ms, le plus sur un reg semé de petits cailloux : une forme de 1 280 triangles pour quelques pixels, les niveaux de détail des formes deviennent utiles.

## Étape 1 ter : la forme du sol et les taches

Le 2026-10-24, en vol : « beaucoup trop de manière uniforme » ; « en bas des ravines, logique qu'il y ait pas mal de grosses pierres ; mais dans les pentes même, petites » ; « en haut des falaises, ce n'est pas logique ; de façon sporadique » ; « les plaines, tu en as mis partout ; les petits cailloux plus courants, les moyens un peu moins, les rochers beaucoup moins ».

**Le banc** ajoute au recensement la forme du sol, la courbure mesurée par le moteur, et les taches : dans des cellules de 20 m, la part des cellules qui tient la moitié des pierres de 25 cm et plus, 50 % pour un semis uniforme, et l'indice de dispersion, 1 pour un semis au hasard. `--avant` mesure une autre version sur les mêmes cellules.

**Par forme du sol,** objets par m² ; part couverte ; part des 50 cm et plus, avant puis après :

| Forme | Part du sol | Avant | Après |
|---|---|---|---|
| Creux, courbure de plus de 0,008 /m | 20 % | 0,82 ; 1,65 % ; 18 % | 0,37 ; 1,09 % ; 40 % |
| Plat | 56 % | 1,14 ; 1,63 % ; 10 % | 0,23 ; 0,19 % ; 1 % |
| Bombé, crêtes | 24 % | 0,78 ; 1,27 % ; 15 % | 0,06 ; 0,06 % ; 4 % |
| Pied de pente, sous plus de 40° | 0,1 % | 6,4 ; 15,3 % ; 29 % | 0,18 ; 2,4 % ; 64 % |

- **Les creux, 18 fois plus couverts que les crêtes,** contre 1,3 fois avant ; les blocs y font 40 % de la couverture, 64 % au pied des pentes.
- **Les plaines, 0,19 % du sol,** des cailloux par taches, presque aucun bloc.

**Par pente,** objets par m² ; part couverte ; part des 50 cm et plus :

| Pente | Avant | Après |
|---|---|---|
| 0 à 10° | 1,09 ; 1,59 % ; 9 % | 0,16 ; 0,25 % ; 31 % |
| 10 à 20° | 1,20 ; 1,80 % ; 12 % | 0,56 ; 1,20 % ; 33 % |
| 20 à 30° | 1,06 ; 2,20 % ; 22 % | 0,11 ; 0,14 % ; 8 % |
| 30 à 35° | 2,95 ; 4,80 % ; 14 % | 0,56 ; 0,68 % ; 4 % |
| 35 à 40° | 0,76 ; 0,65 % ; 0 % | 0,22 ; 0,17 % ; 0 % |
| au-delà | 0 | 0 |

- **Dans les pentes, de petites pierres :** 4 à 8 % de blocs de 20 à 35°. Les blocs restent où le sol s'adoucit.

**Par taille,** objets par m², de 6 cm à 1 m :
- **tout le sol :** avant 0,72 ; 0,22 ; 0,047 ; 0,005 ; après 0,165 ; 0,023 ; 0,010 ; 0,002. Les blocs de 1 à 2 m, sous 0,001 par m² dans les deux ;
- **la loi est plus raide là où les débris passent,** plaines et pentes, où les blocs font 1 à 8 % de la couverture contre 9 à 22 % avant ;
- **les blocs restent là où les débris s'amassent,** si bien que sur tout le sol leur part ne baisse pas autant que leur nombre : 0,005 → 0,002 par m² de 50 cm à 1 m ;
- **les graviers sont la texture du sol,** sous 6 cm ; les objets n'en prennent que le haut.

**Les taches,** pierres de 25 cm et plus : avant, la moitié dans 25 % des cellules de 20 m, indice de dispersion 13 ; après, la moitié dans 9 %, indice 39. Sur le sol doux, de 38 % à 11 %. Agrégé comme les relevés publiés, sans valeur publiée à notre échelle pour caler mieux.

**Le flottement,** la même approche : aucun objet ne flotte, 1,1 px au plus.

**Le tremblement,** trois vues de test, sans objets puis avec, avec et sans lissage : ravine 0,03 / 0,19 puis 0,02 / 0,18 ; plaine 0,02 / 0,14 puis 0,02 / 0,14 ; éboulis 0,12 / 0,76 puis 0,12 / 0,73.

**Le coût :** quatre sols exacts de plus par candidat, la forme du sol, mais les taches écartent dès la première passe 58 % des cellules. Sous la charge des autres instances, sur trois vues de test : placement 1,5 à 1,7 ms, 14 à 17 % du calcul du terrain, contre 1,3 ms et 12 à 14 % pour la version précédente ; dessin 0,02 à 0,3 ms.

## Étape 2 : le détail du sol, une recette par sol

Le 2026-10-25, en vol, deux photos à l'appui (`images/cible-sol-sable-cailloux.jpg`, `images/cible-sol-herbe-rochers.jpg`) : « plus rendu des roches sur un thème éboulis que réellement des détails du sol » ; « des cailloux au bas de chaque ravin, comme s'il y avait des éboulements systématiques » ; « posés au milieu de nulle part ».

**Ce qui a changé :**
- **une recette par sol,** au lieu de trois sources de débris : cailloux et graviers sur le sable et le sol nu ; touffes et rochers dans l'herbe ; pierres des éboulis ;
- **les touffes d'herbe,** une classe nouvelle sur la même grille : quatre formes de 40 brins générées au démarrage ; la couleur de l'herbe du sol à leur place, `ClimateColor`, partagée avec les pixels, plus sombre au pied, plus pâle à la pointe ; un second dessin indirect ;
- **une octave de 1,5 à 3 cm,** et un enfouissement minimal de 3 mm au lieu de 1 cm, qui enterrait les graviers ;
- **plus de creux qui amassent :** les éboulements au pied des seules pentes de plus de 35 à 45° ;
- **des amas plus doux que les taches** pour les cailloux et les touffes : un sable semé partout, plus ou moins.

**Compter les photos :**
- **Le sable,** 1 376 × 768 pixels. Un appareil supposé à 1,6 m et 70° de champ, soit une focale de 983 pixels ; l'horizon de la mer à 268 pixels donne 6,7° d'inclinaison. La tache de premier plan, x de 400 à 1 000, y de 600 à 768, va de 3,1 à 4,7 m de l'appareil : environ 2,3 × 1,6 m, 3,7 m², 3,2 à 4,8 mm par pixel. Comptés à l'œil sur l'image agrandie : 12 cailloux de 8 cm et plus, 35 de 4 à 8 cm, environ 150 de 1,5 à 4 cm, ceux-là sous-comptés, 3 à 8 pixels de large.
- **Soit, par m² et par octave :** 30 et plus de 1,5 à 3 cm, 16 de 3 à 6 cm, 6 de 6 à 12 cm, 0,5 de 12 à 25 cm ; 6 à 8 % du sol couvert.
- **L'herbe,** un panorama de 884 × 316 pixels, sans horizon proche : l'échelle vient des touffes, 20 à 40 cm. Au premier plan, 6 à 15 touffes par m², 30 à 60 % du sol ; dans la tache rocheuse, environ 2 rochers de 20 cm à 1 m par m², 15 à 20 % du sol ; ailleurs, rares ; du gravier entre eux.
- **Une photo est un lieu, pas une moyenne :** le moteur compte sur 23 lieux, ses amas vont de 0,4 à 1,6 fois la moyenne, ses taches de rochers de 0 à 3,8 fois. La cible : le facteur 2.
- **Les lois publiées en garde-fou :** la part du sol à peu près égale à chaque octave des fragments de roche des sols, Turcotte, Poesen et Lavee ; Golombek et Rapp pour les rochers et les éboulis.

**Le banc,** `tools/banc_objets.py recensement`, par m², sur le sol dont la part dépasse 0,5 :

| largeur | sable et sol nu | herbe | éboulis | photo du sable |
|---|---|---|---|---|
| 1,5 à 3 cm | 54 | 8,6 | 40 | 30 et plus |
| 3 à 6 cm | 12 | 5,3 | 7,2 | 16 |
| 6 à 12 cm | 2,6 | 2,1 | 1,5 | 6 |
| 12 à 25 cm | 0,45 | 0,45 | 0,23 | 0,5 |
| 25 à 50 cm | 0,05 | 0,19 | 0,03 | 0 |
| 50 cm à 1 m | 0,002 | 0,02 | 0,002 | 0 |

- **Le sable et le sol nu :** 6,7 % du sol couvert, la photo 6 à 8 %. Le facteur 2 partout, sauf de 6 à 12 cm, 2,6 contre 6 : la photo a un peu plus de cailloux vers 10 cm que la loi, qui garde la même part à chaque octave. Un seul lieu ne justifie pas une loi à bosse.
- **L'herbe :** 9,0 touffes par m² sur 34 % du sol, la photo 6 à 15 sur 30 à 60 % ; rochers de 20 cm à 1 m dans les taches, 1,1 par m², la photo 2 dans une tache rocheuse.
- **Les creux :** 2,8 % du sol couvert, dont 10 % de 50 cm et plus, contre 40 % à l'étape 1 ter ; le plat 6,6 %, des cailloux ; le pied des vraies pentes 3,7 %, dont 44 % de blocs.
- **Les pentes :** rien au-delà de 40°, comme avant.

**À hauteur d'homme,** `tools/banc_objets.py photos` : 1,7 m, regard devant, le soleil haut sur chaque lieu, quatre vues trouvées par le recensement, les mêmes que les tests en vol. Planche : `journal/2026-10-25-objets-sol.jpg`, les photos à gauche.
- **Ce qui rapproche :** le sable semé de cailloux épars et de touffes sèches ; l'herbe hérissée de touffes ; une tache de rochers dans l'herbe ; plus de blocs au fond des ravines.
- **Ce qui reste loin :**
  - la couleur des cailloux et des rochers, celle de la roche du lieu, parfois bien plus claire que sur les photos ;
  - les touffes vertes et fines d'un climat humide, où la photo a de l'herbe sèche et dorée, haute et dense ;
  - à 720 pixels de haut, un gravier de 1,5 cm ne sort du sol qu'à moins de 2 m : au-delà, le gravier est la texture du sol ;
  - pas d'ombres portées : l'étape des ombres de proximité.

**Le flottement :** l'approche de 200 à 1,5 m, sur les éboulis, au pied d'une paroi, et sur le sable, l'herbe et le sol nu des vues : aucun objet ne flotte ; le sol descend sous un pied de 25 % de l'enfouissement au plus, 0,4 px à l'écran. À hauteur d'homme, sur le sable, 1 mm au plus : les graviers enfouis de 3 mm tiennent. Les touffes, plantées par leur pied, ne sont pas mesurées.

**Le pop :** la descente de 40 à 3 m sur les cinq mêmes lieux, cailloux et touffes : 8 800 arrivées, à 0,07 px au plus ; entiers, ils arriveraient à 7,5 à 15,6 px. La plus forte croissance d'une étape, 2,1 px, est celle d'une touffe dans l'herbe.

**Le tremblement,** deux des vues, sans objets puis avec, avec et sans lissage : crête herbeuse 0,01 / 0,07 puis 0,01 / 0,05 ; sable 0,04 / 0,26 puis 0,03 / 0,25.

**Le coût :** sous la charge de trois autres instances, sur les quatre vues et une prairie : placement 0,4 à 0,75 ms, 14 à 28 % du calcul du terrain ; dessin 0,04 à 0,23 ms, jusqu'à 3 700 touffes et 1 500 pierres. Les touffes, deux octaves, n'ajoutent que deux tranches de la grille ; la forme du sol n'est lue que pour les cailloux.

## Étape 3 : où il y a des cailloux, et lesquels

Le 2026-10-25, en vol : « globalement, il y a trop de cailloux partout. De taille un peu trop grande » ; « c'est vraiment du gravier qui va se trouver couramment. Les cailloux plus gros vont se trouver moins couramment » ; « de grandes zones de prairies, il n'y aura que de l'herbe, ou encore de grandes zones de sable ». La photo du sable lui paraît elle-même plus dense qu'un sol ordinaire.

**Ce qui décidait la présence, avant :**
- **la part de chaque sol à la place de l'objet,** lue par `GroundMaterials` : tout sable, tout sol nu portait des cailloux, toute herbe des rochers ;
- **des taches de 8 à 64 m,** nulles sur 58 % du sol, pour les rochers, et des amas de 0,4 à 1,6 fois la moyenne pour les cailloux ;
- **aucun champ régional :** rien de complexplanet, sauf la pente et la forme du sol ; d'où des cailloux partout, à peine moins par endroits.

**Après, un champ de pierrosité propre aux débris** (`OBJECT_STONY`) :
- **un bruit de gradient de la planète, de 0,5 à 32 km,** d'écart type 0,29, le même pour toute caméra ; ses octaves fines découpent les bords des régions ;
- **relevé par ce qui retire au sol ses fines ou lui apporte des débris :** trois fois la part d'éboulis, le sol nu d'autant plus que l'air est sec, la tangente de la pente ; 0,22 fois leur somme ;
- **seuillé par la règle des limites,** `SpreadStep` : des débris au-delà de 0,27, entièrement au-delà de 0,42 ;
- **il décide si des débris existent,** les taches et les amas décident où, dedans ; les touffes n'en dépendent pas ;
- **dans la première passe,** au plus haut que les sols peuvent le relever : les régions sans débris ne coûtent pas de sol exact.

**Les tailles, décalées vers le bas :**
- **le gravier sous 3 cm est la texture :** la tuile fine porte les longueurs d'onde sous 3 cm, le scan de sable et gravier celles de 3 à 50 cm. L'octave de 1,5 à 3 cm est retirée ;
- **les cailloux du sable et du sol nu,** 2 % du sol à 3 cm, la part s'effaçant au-delà de 8 cm : cinq fois moins de cailloux à chaque octave au-dessus ;
- **les rochers de l'herbe,** la loi de Golombek et Rapp à 0,03, le bas des sites mesurés, au lieu de 0,08.

**Le banc,** `tools/banc_objets.py recensement` :
- **la part du sol sans débris,** sur les terres de 120 points tirés sur la planète, 67 lieux : 68 % de tout le sol, 74 % des prairies, 70 % des sables et sols nus, 11 % des éboulis ;
- **là où il y en a,** par m², sur le sol dont la part dépasse 0,5 :

| largeur | sable et sol nu | herbe | éboulis | photo du sable |
|---|---|---|---|---|
| 3 à 6 cm | 5,2 | 0,25 | 0,84 | 16 |
| 6 à 12 cm | 1,0 | 0,53 | 0,65 | 6 |
| 12 à 25 cm | 0,14 | 0,16 | 0,12 | 0,5 |
| 25 à 50 cm | 0,008 | 0,019 | 0,020 | 0 |
| 50 cm à 1 m | 0,0001 | 0,002 | 0,001 | 0 |

- **Au regard des photos :** le sable caillouteux au tiers de la photo pour les petits cailloux, au sixième de 6 à 12 cm, au quart de 12 à 25 cm, 1,7 % du sol couvert contre 6 à 8 % ; le bas de la photo, voulu. Les rochers de l'herbe, 0,22 par m² de 20 cm à 1 m dans les taches, contre 2 sur la photo d'une crête rocheuse.
- **Au regard des lois publiées :** les fragments des sols ont une part à peu près égale à chaque octave, un pavage désertique couvre jusqu'à 65 % du sol ; nos sols caillouteux, 1,7 %, sont au plus bas de ce que l'on mesure, comme demandé.
- **Sur tout le sol,** débris absents compris : de 0 à 10°, 2,2 objets par m² et 0,6 % du sol, contre 71 et 7,3 % à l'étape 2.
- **Les creux :** 6 % de blocs de 50 cm et plus ; le pied des vraies pentes, 58 %.

**À hauteur d'homme,** `tools/banc_objets.py photos`, six vues trouvées par le recensement, les mêmes que les tests en vol : sable caillouteux, sable sans débris près de la côte, herbe et rochers, prairie sèche sans débris, sol nu caillouteux, pente d'éboulis. Planche : `journal/2026-10-25-objets-pierrosite.jpg`, les photos à gauche.

**Le flottement :** l'approche de 200 à 1,5 m, sur les éboulis, au pied d'une paroi, et sur le sable, l'herbe et le sol nu caillouteux des vues : aucun objet ne flotte ; le sol descend sous un pied de 11 % de l'enfouissement au plus, 0,85 px à l'écran.

**Le pop :** la descente de 40 à 3 m sur les cinq mêmes lieux : 8 450 arrivées, à 0,06 px au plus ; entiers, ils arriveraient à 7,5 à 15,6 px. Le tremblement du sable caillouteux, sans objets puis avec, avec et sans lissage : 0,02 / 0,16 puis 0,02 / 0,13.

**Le coût :** sous forte charge de deux autres instances, le calcul du terrain à 20 à 32 ms : placement 1,5 à 4,6 ms, 6 à 19 % de ce calcul, contre 14 à 28 % à l'étape 2 ; dessin 0,06 à 0,15 ms. Le champ de pierrosité écarte les régions sans débris dès la première passe.
