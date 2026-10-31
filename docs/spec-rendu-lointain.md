# Spécification : le rendu de loin, de 5 km à l'orbite

Statut : validée le 2026-10-21. Faits : étape 1, étape 2 sur la face, mutation en descente, règle universelle des limites. Jalon `jalon/13-coherence-distance`, le 2026-10-22.

**En bref, ce qui garde la planète cohérente de l'orbite au sol :**
- **la grille fine :** le vrai relief sous la maille, en normale et en altitude ;
- **un relief qui garde sa hauteur moyenne,** à toute distance ;
- **la règle universelle :** chaque limite entre matériaux montre sa moyenne sur le pixel ;
- **le banc de descente et les vues de diagnostic,** pour le mesurer.

## Le constat

Trois défauts, vus en vol à 56 km, 300 km, 450 km et 1 160 km.

1. **Des confettis de roche.** De 50 à 450 km, des taches de roche blanches, roses et orange semées sur le vert, sans lien avec le relief.
2. **Le flou.** À 1 000 km, la planète n'est plus que de grandes taches floues : aucun relief ne se lit entre les grandes formes.
3. **Le niveau intermédiaire.** En descendant, les formes de complexplanet apparaissent d'un coup, et leur rendu paraît étrange.

## Les causes

**Les confettis.** La roche est décidée par la pente de la maille, plus un bruit local de 8 km à 1 m.

- De loin, une maille fait plusieurs kilomètres : sa pente est presque toujours douce.
- La roche n'apparaît donc que là où le bruit local la force, en taches de 1 à 5 km sans rapport avec les montagnes.
- Les nouvelles couleurs de roche, rouge et calcaire clair, les rendent très visibles.

**Le flou.** Le maillage a toujours 192 mailles sur la largeur de la face, donc une maille couvre environ 13 pixels à toute hauteur.

- **Près du sol,** les textures des matériaux remplissent l'intérieur des mailles.
- **Au-dessus de quelques kilomètres,** les textures se sont fondues dans leur moyenne. Le grain de l'éclairage s'arrête à la maille et ne dépasse pas 6 km. Entre le pixel et la maille, il n'y a donc rien : à 300 km, rien entre 0,4 et 6 km.

**Le niveau intermédiaire.** C'est la même lacune vue en descendant : les octaves de complexplanet n'apparaissent qu'une fois portées par le maillage, sans annonce dans les pixels.

## Les pistes

### 1. La roche en fraction, pas en taches

- **De loin, une maille contient des pentes plus raides que sa pente moyenne :** celles des octaves que le maillage ne porte pas.
- **La roche devient la fraction attendue de pentes raides** dans la maille, d'après la variance de ces pentes. C'est l'esprit de Toksvig et de LEAN pour les normales.
- **Le bruit local s'efface avec la taille du pixel.** Les montagnes deviennent des régions rocheuses continues, avec neige et éboulis, et les plaines restent vertes.
- **Coût :** quelques opérations par pixel. **Risque :** faible.

### 2. Le relief sous la maille, dans les pixels

Il faut remplir l'écart entre le pixel et la maille. Deux façons, très différentes.

- **A. Un grain plus fin que la maille,** la `DetailSlope` actuelle prolongée jusqu'au pixel, son amplitude réglée sur la rugosité du terrain, plus forte en montagne qu'en plaine.
  - **Pour :** coût faible, environ 0,1 ms.
  - **Contre :** c'est un relief inventé. À l'approche, le maillage apporte le vrai relief de complexplanet à la place du grain : la forme mute.
- **B. Les normales du vrai relief, plus fin que la maille,** calculées chaque image par une passe de calcul sur une grille 4 à 8 fois plus fine que le maillage, sans géométrie.
  - **Pour :** le vrai relief, sans mutation à l'approche : c'est ce qui manque au niveau intermédiaire.
  - **Contre :** 16 à 64 fois plus d'évaluations de complexplanet que le maillage, soit 1,5 à 6 ms à ajouter aux 0,1 à 2 ms d'aujourd'hui. Sauf à n'évaluer que les octaves fines, ce qui suppose de découper complexplanet.

### 3. Les couleurs vues d'orbite

- **Le contraste des biomes :** forêts plus sombres, déserts plus clairs, montagnes brunes et neige, comme sur les images de la Terre vue d'orbite.
- **La brume rose** de l'atmosphère vers l'horizon, à vérifier contre des photos d'orbite.

## La mesure

- **Un banc d'orbite :** vues à 5 km, 56 km, 300 km et 1 000 km sur trois régions, à côté de photos de la Terre vue d'orbite.
- **Le banc de mutation en descente,** pour la piste 2.

## Les étapes proposées

1. **La roche en fraction :** piste 1, avec le banc d'orbite.
2. **Le relief sous la maille :** piste 2, A ou B, à choisir.
3. **Les couleurs vues d'orbite :** piste 3.

## Résultats de l'étape 1

- **La dispersion des pentes dans la maille,** `SlopeSpread`, calculée par sommet : la courbure du maillage d'une maille à l'autre donne la pente de la plus fine octave portée, et log2(maille / 13,5 m) octaves restent dessous, chacune de pente comparable.
- **Les limites de roche, d'éboulis et de neige s'élargissent** de 1,5 fois cette dispersion. La limite des neiges en température s'élargit aussi, selon l'étalement des altitudes dans la maille.
- **Les bruits locaux de roche et de température s'effacent** pour des pixels de 32 à 512 m.
- **Au banc d'orbite :**
  - les confettis de roche ont disparu du plateau herbeux, à 56 et 300 km ;
  - à 300 km, la neige forme un massif d'un seul tenant au lieu d'un semis de taches ;
  - à 56 km, la neige reste par plaques, mais adoucies ;
  - le désert reste flou : c'est l'étape 2.

## Corrections faites en chemin

- **Rayures de neige et de roche de 450 m à 1,3 km :** la tuile de 64 m porte ±1 m de relief ; le mélange par la hauteur intercalait neige et roche banc par banc, plus fin que le pixel. Ce mélange s'estompe maintenant pour des pixels de 25 cm à 2 m.
- **Les deux correctifs de la passe de relief des matériaux,** retirée le 2026-10-30 : `log/spec-rendu-lointain-historique.md`.

## L'étape 2 en B : la grille fine

Statut : choisie le 2026-10-21 ; première version faite, la face seule.

- **Une grille 4 fois plus fine que la face du maillage,** 768 × 768 mailles, recalculée à chaque image par complexplanet, filtrée à sa propre maille comme le maillage l'est à la sienne.
- **Deux passes de calcul :** les hauteurs de la grille fine, puis ses normales.
- **Le pixel prend la normale fine,** interpolée entre quatre points, à la place de celle du maillage. Elle s'efface sur les huit dernières mailles du bord de la face.
- **Le grain de l'éclairage et la dispersion des pentes** se règlent sur la maille fine : le grain inventé ne commence qu'en dessous d'elle.
- **Jusqu'à 160 m du sol pour les décisions des matériaux :** active à partir de mailles de face de 3,4 m, `FineMinCell`, pleinement à 6,8 m, soit 320 m de haut. Plus bas, le maillage porte l'octave la plus fine du relief, 13,5 m, sur ses 4 mailles. Elle s'arrêtait d'abord à 20 m de maille, vers 1 km : voir le correctif du 2026-10-24 ci-dessous.
- **Jusqu'à 1 km pour la lumière :** elle n'éclaire le sol qu'à partir de mailles de face de 20 m, `FINE_LIGHT_MIN_CELL`. Plus bas, les normales spline et le grain, plus stables, et les textures remplissent les mailles.
- **La face seule, d'abord :** d'orbite, elle couvre l'essentiel de la vue. Les anneaux suivront si la mesure le justifie.
- **Les points hors du champ** ne sont pas calculés, comme pour le maillage.

**Le risque connu :** la piste `piste/relief-par-pixel`, abandonnée, évaluait le relief à chaque pixel. Son coût, 8 à 33 ms, n'est pas celui de B. Mais son défaut visuel vaut aussi pour B : de loin, des crêtes sans volume, puisque la normale seule ne fait pas de géométrie.

**La mesure :** le banc d'orbite avant et après ; le coût du calcul à 1, 5, 56 et 300 km ; une descente, pour la mutation.

### Résultats de la première version

- **D'orbite, le relief se lit :** à 300 km, le massif enneigé montre ses crêtes et ses vallées au lieu d'une tache blanche ; à 5 km, le désert est plus net.
- **Coût du calcul :** 0,2 → 1,8 ms à 56 km, 0,1 → 0,7 ms à 300 km. À 5 km, il reste dans le bruit de mesure.
- **Reste à faire :** les anneaux, qui gardent le relief du maillage seul ; la mesure en descente, pour la mutation.

## Corrections faites en chemin, suite

- **Lames de plusieurs mètres sur les crêtes, en vol :** le pavage aléatoire mêlait trois copies de la tuile en gardant leur contraste. Il amplifiait les écarts jusqu'à 1,7 fois, soit ±3,5 m sur la tuile de 64 m, et des corniches croisées formaient des lames. Les hauteurs et les pentes se mêlent maintenant simplement ; seules les couleurs gardent leur contraste. Pas reproduit sur nos points : à vérifier en vol.
- **Marches sous la neige :** il ne reste que 10 % du relief sous la neige, au lieu de 30 %, et les parois des couloirs de la tuile de 64 m sont adoucies.
- **Pour reproduire une vue :** la barre de titre donne la position de la caméra, et l'exécutable accepte un cinquième argument, le cap.
- **Banc des crêtes :** `tools/banc_cretes.py`, les crêtes à hauteur d'homme, plusieurs builds côte à côte.
- **Plantage loin de la planète, de 5 000 à 6 500 km, une fois sur deux :** au bord de la face, la coordonnée interpolée du pixel passait un cheveu sous 0. L'indice de la normale fine devenait alors énorme, et la lecture, sans contrôle de bornes sur un descripteur racine, faisait tomber le GPU. L'indice est maintenant borné des deux côtés : six lancements sur six réussis, contre trois avant. Une perte du GPU affiche désormais sa raison au lieu de fermer l'appli sans un mot.

## La mutation en descente : mesures

**Le banc :** `tools/banc_descente.py`. Il filme la même zone à la verticale, de 1 500 km à 60 km, et mesure ce qu'elle contient sur 60 km de côté. Le moteur tourne alors dans sa vue de diagnostic, `MYPLANETENGINE_VIEW` = `snow`, `rock` ou `elevation`. Chaque pixel y est blanc avec la probabilité du poids du matériau, ou de l'altitude sur 6 km, sans lumière ni lissage. La part de blanc donne la moyenne exacte.

**La neige, chaîne au nord de l'Afrique, 32,3° N, 17,9° E :**

| Hauteur | 1 500 km | 800 km | 400 km | 200 km | 130 km | 90 km | 60 km |
|---|---|---|---|---|---|---|---|
| Neige | 6,6 % | 6,0 % | 8,9 % | 45,3 % | 29,2 % | 26,8 % | 26,3 % |

- **Sans l'élargissement en température :** seul le loin change, 6,6 → 0 %.
- **Sans l'élargissement en pente, ou sans la grille fine :** rien ne change.
- **Sans l'effacement du bruit local de température :** le loin monte à 23–32 %, mais le pic à 200 km reste.

**Le pic à 200 km vient du relief lui-même.** L'altitude moyenne de la zone change avec la hauteur de vue :

| Hauteur | 1 500 km | 800 km | 400 km | 200 km | 130 km | 90 km | 60 km |
|---|---|---|---|---|---|---|---|
| Afrique du Nord | 1 690 m | 1 820 m | 1 840 m | 2 140 m | 1 990 m | 1 900 m | 1 810 m |
| Site de la roche, 15° S, 120° E | 4 450 m | 4 480 m | 4 630 m | 5 090 m | 4 870 m | 4 660 m | 4 270 m |

- **Les montagnes gonflent puis dégonflent** de 300 à 800 m selon la distance, avec un maximum pour des mailles d'environ 4 km.
- **La cause :** le filtrage des octaves remplace chaque octave écartée par sa moyenne, mais complexplanet combine ses octaves de façon non linéaire. La moyenne d'une octave ne garde donc pas la moyenne du relief.
- **Les conséquences :** une mutation de forme, les montagnes qui changent de taille, et une mutation de neige, puisque la neige suit l'altitude.

## La mutation en descente : corrections

**1. Le relief garde sa hauteur moyenne.** La cause du gonflement était l'arrondi des crêtes, `CreaseAbs` :
- près de la coupure, il arrondit sur jusqu'à deux fois l'amplitude du bruit, et la valeur absolue arrondie y valait presque 1 au lieu de sa moyenne de 0,32 ;
- son excès moyen est maintenant retiré, calculé exactement pour un bruit de loi normale d'écart-type 0,4. Cet écart-type se déduit des moyennes déjà mesurées, celles de Billow et de RidgedMulti. Un tirage aléatoire confirme le calcul à 0,1 % près ;
- les crêtes restent arrondies, donc toujours stables.

| Altitude moyenne | 400 km | 200 km | 130 km | 90 km | 60 km | 30 km | 15 km |
|---|---|---|---|---|---|---|---|
| Site de la roche, avant | 4 700 m | 5 160 m | 4 810 m | 4 550 m | 4 120 m | 4 090 m | 4 150 m |
| Site de la roche, après | 4 610 m | 4 540 m | 4 460 m | 4 360 m | 4 280 m | 4 250 m | 4 220 m |
| Afrique du Nord, après | 2 000 m | 2 000 m | 1 900 m | 1 890 m | 1 900 m | 1 890 m | 1 880 m |

- **Il reste un écart régulier** de 400 m sur le site de la roche, de 400 à 15 km, sans bosse. C'est probablement la cascade de RidgedMulti, dont les poids d'octave dépendent des octaves précédentes.

**2. La neige suit le relief réel.**
- **Son altitude est celle de la grille fine,** quatre fois plus précise que le maillage : la neige se pose sur les vrais sommets sous la maille.
- **Le bruit de température** ne porte plus que des longueurs d'onde de 2 km et moins, pour environ 0,6 °C. Il est le même à toute distance.
- **Ce que le pixel ne peut pas montrer de ce bruit** élargit la limite des neiges autour de −2 °C, au lieu de l'effacer : la part moyenne ne bouge plus.
- **L'ancien effacement du bruit local de 8 km** pour les pixels de 32 à 512 m est retiré de la température. C'est lui qui faisait des taches de neige sans lien avec le relief.

| Neige, Afrique du Nord | 800 km | 400 km | 200 km | 130 km | 90 km | 60 km |
|---|---|---|---|---|---|---|
| Avant | 6,0 % | 8,9 % | 45,3 % | 29,2 % | 26,8 % | 26,3 % |
| Après | 11,0 % | 8,2 % | 9,9 % | 10,9 % | 11,8 % | 12,2 % |

- **De 400 à 60 km,** les mêmes plaques de neige sur les mêmes sommets.
- **À 800 km,** la grille fine ne distingue plus les sommets, et la neige devient une bande au même endroit.
- **Le bruit seul,** à 1,5 °C sur 1 km, faisait un semis de points de 90 à 60 km : essai écarté.

## La règle universelle : une limite montre sa moyenne sur le pixel

Statut : en place le 2026-10-22, pour tous les matériaux.

**La règle.** Toute limite entre matériaux est une transition douce sur un champ : température, altitude, pente. Un pixel montre la moyenne de cette transition sur tout ce qu'il couvre, à toute distance.
- **Le bruit qui rend une limite irrégulière est le même à toute distance.** On ne l'efface jamais selon la taille du pixel.
- **Ce que le pixel ne peut pas montrer d'un champ élargit la limite :** sa variance perdue s'ajoute à la transition. Le centre ne bouge pas, donc la part moyenne non plus.
- **Toute entrée d'une limite apporte sa variance perdue.** Pour la température : le bruit de la limite des neiges, les altitudes cachées dans la maille, et l'orientation des versants cachés.

**Les outils, dans `Materials.hlsli` :**
- `SpreadStep(lo, hi, x, sigma)` pour un champ à une dimension : la transition élargie à variance égale. Écart de moins de 3 % avec un tirage aléatoire.
- `SlopeShares(slope, sigma, limits)` pour la pente, champ à deux dimensions : une quadrature polaire stratifiée, six rayons et cinq angles. Écart de moins de 2 % avec un tirage aléatoire, contre 15 % pour un Gauss-Hermite 3 × 3.
- `FbmLostShare` : la part de variance d'un bruit que le pixel ne montre pas.
- `SlopeSpread` et `ElevationSpread` : les pentes et les altitudes que la maille cache, d'après la rugosité du type de terrain.

**La rugosité, seule donnée propre au terrain.** Les octaves de montagne de complexplanet, en RidgedMulti, portent chacune à peu près la même pente. Les pentes cachées valent donc cette pente par octave, multipliée par la racine du nombre d'octaves perdues.
- **Elle vient du type de terrain,** calculé avec le relief et transmis par sommet (`FaceVertex.roughness`) : 1 pour les montagnes, 0,6 pour les badlands, 0,4 pour les collines, 0,1 pour les plaines.
- **La pente par octave,** `OCTAVE_SLOPE` = 0,16, est calibrée sur la roche au banc de descente.
- **Pourquoi pas une mesure sur le maillage :** une maille de plusieurs kilomètres ne voit que la courbure des continents. La dispersion mesurée tombait à 0,014 à 400 km.

**Bilan matériau par matériau,** au banc de descente :

| Matériau | Décidé sur | Traitement | Part mesurée, de loin à près |
|---|---|---|---|
| Relief | complexplanet | universel : l'arrondi des crêtes garde la moyenne | altitude moyenne sans bosse ; reste un écart de 400 m sur une chaîne |
| Neige | température, pente | règle universelle ; orientation des versants calibrée, voir plus bas | 12 → 16 % et 6 → 14 %, contre 6 → 45 → 26 % avant |
| Roche | pente | règle universelle, `SlopeShares` | 18 → 22 %, contre 0 → 17 % avant |
| Éboulis | pente | règle universelle, `SlopeShares` | 33 → 45 %, stable |
| Herbe, sable | humidité, température | stables par construction : humidité régionale de plus de 200 km, jamais filtrée ; limites de température en `SpreadStep` | 100 % sur les sites testés ; herbe 6,0 → 8,1 % à la frontière froide et sèche de la chaîne d'Afrique du Nord |
| Vert des terres humides, forêt | humidité | stable par construction | 100 % sur le site testé |
| Plage | altitude, bruit local, température | règle universelle, `SpreadStep` | 5,1 → 6,0 %, contre 4,0 → 6,1 % |
| Mer | altitude | règle universelle : part de mer dans le pixel, au lieu d'un oui ou non | 83 → 87 %, stable |
| Toundra, couleur | température | `SpreadStep` | non mesurée, même règle |
| Clarté, teinte | bruits locaux et régionaux | linéaires : leurs moyennes sont exactes par construction | sans objet |
| Textures | tuiles générées | les mipmaps gardent la moyenne | sans objet |

**Le spécifique, et pourquoi.**
- **Les rugosités par type de terrain et `OCTAVE_SLOPE`** sont des données propres à complexplanet, pas une règle. Elles sont calibrées sur la roche du site de la roche.
- **L'orientation des versants cachés compte pour 4 °C par unité de pente,** au lieu des 8 °C du terme d'orientation de la température :
  - à 8 °C, la neige était deux fois trop abondante de loin sur la chaîne d'Afrique du Nord, 28 % contre 14 % ;
  - à 0 °C, elle était deux fois trop rare de loin sur les deux chaînes ;
  - à 4 °C, elle tient sur les deux à quelques points près.
  - Raison probable : la rugosité par type de terrain surestime les pentes de certaines montagnes, plus douces que la moyenne.
- **La limite de toute méthode statistique :** sur une petite zone de 3 km, la part de roche monte encore à l'approche, de 20 à 33 % ou de 18 à 45 %. De loin, on montre la part moyenne de la région, pas celle d'un endroit plus raide que la moyenne.

**Ce qui reste à mesurer ou à faire :**
- une frontière entre herbe et désert chaud, où le sable compte ;
- l'écart de 400 m du relief, probablement la cascade de RidgedMulti ;
- une rugosité mesurée plutôt que tirée du seul type de terrain, par exemple par la grille fine, pour ne plus calibrer à la main.

**Coût :** +0,10 à +0,28 ms de rendu, au minimum de trois passages.

## Correctif du 2026-10-22 : le scintillement de près

**Symptôme,** vu en vol après le jalon 13 : de gros scintillements et des formes aberrantes près du sol, des boules et des arches de roche. Positions `6561.8 -18.67002 131.64981 9.8 -117.1` et `563.6 5.98065 127.83668 11.2 -58.7`.

**Le banc :** `tools/banc_tremblement.py <dossier> <exe> "<position>" [exe ...]`. Il reprend une position exacte de la barre de titre et mesure l'écart moyen entre images successives, avec et sans lissage temporel, quand le maillage glisse sous une caméra fixe.

**La cause, trouvée en remontant les builds du jour :** le correctif de l'arrondi des crêtes, `CreaseExcess`.
- **Pour un petit arrondi,** sa forme exacte soustrait des termes presque égaux puis divise par l'arrondi.
- **En simple précision,** l'erreur grandissait à mesure que l'arrondi rétrécissait, c'est-à-dire près de la caméra, et différait d'un sommet à l'autre : le sol vibrait et se plissait.
- **Le correctif :** sous un arrondi de 0,4, on prend sa série, `p0 e²/3 − p0 e⁴/(60 σ²)`, exacte à 0,0002 près. La forme exacte ne sert qu'au-dessus.

| Tremblement, avec / sans lissage | Vue de crête enneigée | Vue de dune |
|---|---|---|
| Avant le correctif des crêtes, `5f53ef9` | 0,43 / 1,68 | 0,21 / 1,46 |
| Jalon 13 | 1,26 / 3,07 | 2,37 / 5,11 |
| Avec la série | 0,37 / 1,37 | 0,16 / 1,01 |

- **Mieux qu'avant le jalon 13,** sur les deux vues.
- **L'altitude moyenne en descente reste plate,** 71 à 72 % de 200 à 15 km sur le site de la roche, et la part de roche ne change pas.
- **Essai écarté :** déplacer le relief des matériaux à la verticale au lieu de la normale. Cela gagnait peu, et les crêtes se couvraient de dents de scie.

## Correctif du 2026-10-24 : les cercles sur les océans, vus de loin

**Symptôme,** vu en vol à 24 600 km, `24622915.3 46.51198 60.64808 79.2 78.2` : les océans couverts d'anneaux concentriques autour de nombreux centres, comme un moiré. Nets de 10 000 à 30 000 km ; pâles dès 2 000 km, sur les terres aussi. Image : `images/cercles-avant-apres.jpg`.

**Le diagnostic, par élimination, sur la vue signalée :**
- couleur de la mer fixe, au lieu de sa profondeur : les cercles restent ;
- normale verticale partout : ils restent ;
- terrain noir, l'atmosphère seule : ils restent. C'est l'atmosphère.

**La cause : la distance passée à l'atmosphère en demi-flottant.**
- **Le terrain écrit sa distance,** en km, dans l'alpha de l'image HDR ; l'atmosphère y arrête son intégration le long du rayon.
- **Un demi-flottant n'a que 11 bits :** des pas de 0,5 km à 1 000 km, 8 km à 10 000 km, 16 km au-delà de 16 384 km.
- **Le rayon s'arrêtait jusqu'à 8 km avant le sol,** ou au sol quand l'arrondi tombait dessous. La couche d'air la plus dense, 8 km d'échelle de hauteur, comptait ou non selon le pixel.
- **Ces paliers suivent la distance :** des cercles autour du nadir. Plus serrés que le pixel, ils se replient en anneaux autour d'un réseau de centres, comme une mire de Fresnel.

**Le correctif :** l'image HDR passe en flottants 32 bits (`HdrFormat`, `D3DApp.h`). La distance y garde 2 m à 30 000 km, à l'endroit où passe toute distance vers l'atmosphère et le lissage temporel.

**La règle** (`principes.md`) : une grandeur passée d'une passe à l'autre garde la précision de l'échelle où elle sert, pas celle de sa taille.

**Les mesures :**
- **Plus aucun cercle,** de 2 000 à 30 000 km, sur deux régions, même à contraste × 8.
- **L'océan s'éclaircit un peu de loin :** chaque pixel compte enfin toute la colonne d'air.
- **Descente, parts inchangées au dixième :** neige 20,5 → 14,6 % en Afrique du Nord, mer 98,8 → 97,7 % de 25 000 à 1 200 km.
- **Banc de qualité, 30 lieux :** tous les p95 à 0,1 dB près de la référence, mutation identique, segments droits par vue à 0,3 près.
- **Près du sol, image identique** à 1/255 près ; coût dans le bruit de mesure, moins de 0,1 ms.

## Correctif du 2026-10-24 : la mutation à l'approche

**Symptôme,** en vol vers un massif enneigé : une tache verte dans la neige, nette à 1,6 km du sol, mangée par le blanc à 1,3 km, revenue à 530 m ; des taches brunes au dernier moment, à 143 m. Vues : `tools/tests/2026-10-24-approche.txt`.

**Les causes, mesurées au banc de descente sur un carré de 100 m sous la tache, de 2 km à 100 m :**
- **La normale des décisions perdait les formes de 13,5 à 100 m.** La grille fine s'éteignait entre des mailles de face de 40 et 20 m, de 1,9 km à 960 m de haut. Le maillage seul ne porte une octave qu'au-delà de 4 mailles : 84 m à 1 km, 13,5 m seulement sous 160 m. La température suit l'orientation des versants : la tache, versant tourné vers l'équateur, se refermait puis se rouvrait.
- **La pente des textures changeait la neige près du sol.** Ajoutée à la normale de la neige pour les pixels de moins de 2 m, sans que sa part perdue compte de loin : sur les 600 derniers mètres, la neige perdait jusqu'à 7 points sur les pentes douces, la roche apparaissant dessous, et en gagnait 8 sur la roche raide.
- **Écartés à la mesure :** sans `HeightBlend`, les parts ne bougent pas ; sans le grain `DetailSlope` dans les décisions, ou avec les versants cachés comptés à 8 °C, elles bougent davantage.

**Le correctif :** la grille fine reste active pour les décisions jusqu'aux mailles de 3,4 m, la lumière garde son seuil de 20 m ; la neige ne tient compte que de la pente du terrain. Les mesures sont dans `journal-planete.md`.

**Reste :** l'octave de 13,5 m et une part de celle de 27 m manquent encore à la grille fine au-dessus de 500 m, et `SlopeSpread` ne les compte pas ; la roche monte encore de 3 à 9 % sur la tache entre 2 et 1,2 km, de 4 à 17 % sur des collines. Compter ces octaves avec la rugosité par type de terrain règle les montagnes mais déborde ailleurs : il faut la rugosité mesurée, plus haut.
