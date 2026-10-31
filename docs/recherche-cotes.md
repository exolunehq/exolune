# Recherche : les côtes, plages, falaises et rivages rocheux

Statut : recherche du 2026-10-24. **Étapes 1 et 2 faites le 2026-10-25 sur la branche `plages`, tag `piste/plages`, sur l'ancienne mer. L'étape 1 est portée sur la mer FFT le 2026-10-31, sa largeur plafonnée ; l'étape 2 reste à porter.** Les mesures viennent d'un portage CPU de complexplanet, `tools/cotes/`. Le plan d'origine de l'étape 1 est dans `log/recherche-cotes-historique.md`.

## 1. Conclusion et plan

**La conclusion**

- **complexplanet n'a aucune forme côtière.** La côte est la courbe de niveau 0 d'une plaine douce qui s'enfonce sous la mer. 90 % des rivages sont des plaines, de pente médiane 6 % sur 20 m et 4 % sur 200 m. Rien n'y marque l'érosion, à aucune échelle.
- **Notre plage est dix fois trop large.** Sa bande de 5 à 25 m d'altitude, centrée sur 15 m, donne une largeur médiane de 540 m, et plus de 1,9 km pour un rivage sur dix. Une vraie plage fait 20 à 80 m.
- **Les bandes d'une côte réelle sont des hauteurs d'eau :** marée, jet de rive, berme. Une bande d'altitude est donc le bon outil pour le sable, le sable mouillé et les ceintures des roches. Sa largeur sort de la pente, comme dans la nature : largeur = hauteur / pente.
- **Il suffit de la mettre à la bonne hauteur.** De 0 à 2,5 m environ, la plage mesure 40 à 70 m de large en médiane sur nos rivages.
- **Une falaise demande la géométrie.** Sa pente vient de la roche, pas du terrain : il faut la distance au rivage. Estimée par l'altitude sur la pente d'un complexplanet privé de ses octaves sous 200 m, elle tombe à un facteur 2 près pour 82 à 86 % des points entre 25 et 100 m du rivage.
- **Personne ne le fait en pure fonction de la position.** Outerra et Flight Simulator calculent un champ de distance par tuile ; Flight Simulator admet le popping. Gaea, World Machine et World Creator remappent l'altitude près de l'eau. La revue de Galin 2019 classe l'érosion côtière parmi les phénomènes presque jamais traités en synthèse d'images.

**Le plan**

| Étape | Nature | Contenu | Mesure de réussite |
|---|---|---|---|
| 1 | Rendu seul, **portée sur la mer FFT** | La plage de 0 à 2,5 m ± 1 m, au plus 120 m de large, sur les pentes de moins de 0,18 | Largeur médiane 40 à 70 m, contre 540 m ; courbe `beach` plate au banc de descente |
| 2 | Rendu seul, **fait sur la branche `plages`** | Les bandes de l'eau : ligne d'eau nette, sable mouillé, laisse de mer, ceintures des roches | Sable mouillé de 10 à 45 m ; ligne d'eau nette au sol |
| 3 | Rendu seul | Le type de côte : sable, galets, plateforme rocheuse, vase ; un champ partagé avec la mer | Parts de côte : environ 31 % sable, 14 % vase, le reste rocheux |
| 4 | Surcouche géométrie, remplacement | Le profil d'érosion : plateforme et falaise, `min(h, P(d))` | Hauteurs de falaise contre Young et Carilli : moyenne 12 m, 90 % sous 30 m |
| 5 | Surcouche géométrie, remplacement | Le dépôt et le plan : berme, dune, caps et baies, aiguilles | Largeurs de plateforme 80 à 500 m ; baies en arc |
| 6 | Surcouche géométrie, ajout de détail sous 13,5 m | Blocs au pied des falaises, encoches, croissants de plage | Attend la voie géométrie de `geometrie.md` |

**Les étapes 1 et 2, faites le 2026-10-25 sur la branche `plages`, commit `c87dcd9`, tag `piste/plages`**
- **Une seule échelle, l'exposition :** toutes les bandes sont des hauteurs d'eau multipliées par `CoastExposure`, de moyenne 1 et d'écart 0,41, tirée du bruit local. C'est le champ à partager avec la mer.
- **Les bandes,** dans `GroundMaterials` :
  - la plage jusqu'à 2,5 m, adoucie de ±1 m, sur les pentes de moins de 0,12 à 0,22, au-dessus de 0 °C ;
  - le sol mouillé jusqu'à 1 m, deux fois plus sombre, et sa brillance, `WaterSheen` dans `PixelShader.hlsl` ;
  - la laisse de mer, de 1,06 à 1,16 m, cassée en taches par un bruit de 16 m à 50 cm ;
  - sur la roche, les algues jusqu'à 0,4 m, le lichen noir de 0,8 à 3 m.
- **La règle universelle :** chaque bande est une part de la terre du pixel, `ShoreBelow`. La ligne d'eau est l'étalement des hauteurs, cachées et propres au pixel, `ShoreSpread` : nette de près, moyenne de loin.
- **Mesures :**
  - largeur de plage sur 968 rivages : médiane 39 m, 53 m là où il y a une plage, contre 502 m ; p90 209 m contre 2 196 m ; 18 % des rivages sans plage, trop raides ;
  - sol mouillé : médiane 14 m, p90 51 m ;
  - banc de descente, côte de 0,478° N 116,513° E : part de plage plate à 0,1 point près de 1 500 à 260 km, à 0,2 point de 800 à 60 km, à 1,4 point de 60 à 2 km.
- **Ce qui change à l'œil :** les terres de 3 à 25 m reprennent les couleurs du climat ; une plage ne monte plus sur une falaise.
- **Règles, sur la branche seulement :** la côte est une limite comme les autres ; un bruit élargit une limite de ce qu'il la déplace, pas plus. Elles vont dans `principes.md` avec l'intégration.
- **Le détail :** l'entrée du 2026-10-25 de `journal-planete.md`.

**L'étape 1 sur la mer FFT, le 2026-10-31**
- **Portée de `c87dcd9`,** dans `GroundMaterials` : `ShoreSpread`, `LandShare`, `ShoreBelow`, `CoastExposure` et la bande de plage. Sans l'étape 2.
- **La largeur plafonnée :** le haut de la bande vaut `min(2,5 m, 120 m × pente)`, `BEACH.z`. Sans plafond, une bande de 2,5 m faisait 1,25 km sur les plaines côtières de pente 0,002, que le relief a (`RELIEF_COAST_QUIET`).
- **La pente du plafond, sur 60 m :** une normale de rivage lue sur la surface du maillage à `SHORE_BASELINE` de part et d'autre (`VertexShader.hlsl`). La normale des matériaux, à 1 m, suivait les bosses : au portage, 73 % des terres d'une plaine côtière en plage, 3 % avec une pente prise sur 20 m. Au loin, la grille fine porte la normale de rivage dès que ses mailles couvrent 60 m (`PixelShader.hlsl`).
- **L'exposition au large,** `CoastFetch` : l'eau ouverte à 3, 10 et 30 km vers le bas de la pente, sur la carte de la planète, une part continue du sol de 10 m à 0 ; une côte fermée garde `BEACH.w`, 40 % de son exposition.
- **Vérifié en rendu,** avant et après : motus verts frangés de sable ; cordon de 20 km à 150 m, plage de 50 à 90 m côté mer ; plaine côtière aux couleurs du climat ; côte raide sans plage.
- **Les limites :**
  - une mare de quelques centaines de mètres garde un anneau de sable, la carte à 3 km ne la voit pas abritée ;
  - au-delà de la face du maillage, sans grille fine, un cordon étroit perd sa plage ;
  - l'exposition reste le bruit local, pas encore la houle de la mer FFT.

**À porter sur la mer FFT**
- **Faites sur l'ancienne mer :** la branche part du `jalon/18-lumiere`, avant la mer animée et la mer FFT. Un essai de fusion avec la mer animée, tag `piste/essai-fusion-mer-plages`, donnait au sable mouillé le reflet de la mer au lieu de `WaterSheen` ; il est resté avec l'ancienne mer (`log/recherche-mer-historique.md`).
- **Ce qui reste à faire pour intégrer l'étape 2 :**
  - la part de mer, `LandShare` et `ShoreSpread`, à la place du fondu fixe de `PixelShader.hlsl`, en accord avec la surface de la mer FFT ;
  - la brillance du sable mouillé par la réflexion de l'eau de `Sea.hlsli`, que la mer FFT prévoit déjà pour le film d'un rivage mouillé ;
  - `CoastExposure` partagé avec le vent et la houle de la mer.
- **Restait sur la branche :** de près, le sable mouillé plus clair qu'une mer sans reflet, ce que la mer FFT peut régler ; la part de mer de loin, qui varie de 6 points sur 2 km ; le type de côte, étape 3.

**Les étapes 4 et 5 sont des remplacements :** une spec dédiée, une branche, un tag `piste/cotes-erosion`, un réglage `COAST_EROSION` qui les ramène à 0.

## 2. Audit : complexplanet au bord de la mer

**Méthode**
- **Un portage CPU** de `ComplexPlanet.hlsli` et `LibNoise.hlsli` en numpy, en double précision, avec le même filtrage des octaves et le même arrondi des crêtes.
- **Validé contre le moteur :** quatre hauteurs de sol relevées dans `tools/tests/2026-10-24-detail-roche.txt` sont retrouvées à 0,2 m près, 1,8 m sur un sommet de 4 354 m.
- **279 points de rivage,** trouvés sur 1 500 arcs tirés au hasard, de 150 km chacun. Un arc coupe la côte en proportion de sa longueur : chaque kilomètre de côte pèse autant.
- **Détail complet,** celui que le maillage porte près du sol. Les scripts sont dans `tools/cotes/` : `cp.py` et `t0.py` à `t7.py` ; `t8.py` et `t9.py`, sur la branche `plages`, mesurent les bandes et les parts de sol.

**Les bruits qui touchent la côte, et leurs échelles**

| Bruit | Longueurs d'onde | Amplitude au rivage | Rôle à la côte |
|---|---|---|---|
| Continents, Perlin 14 octaves | 6 378 km à 214 m | pente 1,4 % sur 20 m, 0,9 % sur 2 km | pose la côte, en pente douce |
| Turbulences des continents | plafonnées à 6 km | quelques mètres de déplacement de côte | sinuosité de grande échelle |
| Plaines, deux Billow de 8 octaves | 5,8 km à 13,5 m | ±32 m autour de +64 m | **dessinent la côte fine** : pente 4,7 % sur 20 m |
| Rivières, RidgedMulti | 340 et 150 km | −26 m médian au rivage | vallées larges, rias de 100 km |
| Collines | 3,8 km à 81 m | jusqu'à 2 km | 9 % des rivages |
| Montagnes | 4,6 km à 22 m | jusqu'à 8 km | aucun rivage mesuré |
| Badlands, falaises en terrasses | 7,6 km à 143 m | des centaines de mètres | 1 % des rivages |

**La courbe des continents autour de `SEA_LEVEL`**
- **Le rivage tombe dans un seul morceau de cubique,** de l'entrée 0 à 0,0625 de la courbe : de −768 à +256 m. `continentDef` y vaut −0,016 en médiane, de −0,13 à +0,04.
- **Le rivage n'est pas à `continentDef` = 0 :** les plaines ajoutent +42 m en médiane, la côte est donc où le continent descend à −42 m.
- **La courbe a une cassure, mais pas à la côte.** libnoise interpole en paramètre uniforme sur des points d'écarts inégaux : la pente saute de 1,5 à 24 à l'entrée 0. Cette cassure est à `continentDef` = −0,375, soit −768 m, au bord du plateau.
- **Un replat de basses terres suit la côte :** de l'entrée 0,0625 à 0,125, la courbe monte quatre fois moins vite. C'est une plaine côtière de dizaines de kilomètres.

**Le plateau continental, `SHELF_LEVEL` = −0,375**
- **Le « plateau » de complexplanet est une rampe** du rivage à −700 m. Il atteint −130 m à 20 km du rivage en médiane, et −700 m à 74 km.
- **Puis le talus tombe d'un coup,** de −700 à −2 000 m en deux à trois kilomètres : c'est la marche du sélecteur, sur une transition de 0,03125.
- **Sa terrasse est celle des abysses,** de −0,75 à −0,375 de `continentDef`, et ses fosses viennent d'un RidgedMulti de 16 octaves, jusqu'à 10 m.
- **Au large du rivage, la pente est vraisemblable :** −5,7 m à 200 m et −12,4 m à 1 km en médiane. C'est un profil de Dean de coefficient A ≈ 0,12 à 0,17, dans la plage mesurée sur Terre, 0,08 à 0,40.

**Aucune forme côtière du mètre à la centaine de mètres**
- **Aucun bruit ne dépend de la distance au rivage,** ni de l'altitude près de 0. Le seul sélecteur près du niveau de la mer est celui des rivières, qui creuse à demi-profondeur au rivage, à l'échelle de 100 km.
- **La côte fine est une plaine de Billow noyée.** Un Billow a des creux en V et des bosses rondes : la mer remplit les creux. Nos caps sont des lobes arrondis, nos criques des entailles pointues. Une côte érodée fait l'inverse : baies en arcs lisses, caps anguleux.

**La pente du terrain au rivage**

| Base de mesure | p10 | Médiane | p90 | Part au-delà de 0,65, la roche |
|---|---|---|---|---|
| 2 m | 0,033 | 0,076 | 0,25 | 4 % |
| 20 m | 0,030 | 0,065 | 0,22 | 3 % |
| 200 m | 0,017 | 0,041 | 0,13 | 2 % |
| 2 km | 0,006 | 0,017 | 0,06 | 0 % |

- **Par type de terrain, sur 20 m :** plaines 0,06, 252 points ; collines 0,42, 24 points ; badlands 2,0, 3 points.
- **La pente des plaines vient des Billow :** 0,047 sur 20 m, contre 0,014 pour les continents et 0,002 pour les rivières.
- **De 0 à 3 m d'altitude, la pente moyenne** est de 0,045 en médiane : celle d'une vraie face de plage, 0,05 à 0,11. Mais elle continue des kilomètres sans berme, sans dune, sans falaise.

**Le profil vers l'intérieur, le long de la plus grande pente**

| Distance du rivage | 10 m | 50 m | 100 m | 200 m | 500 m | 1 km |
|---|---|---|---|---|---|---|
| Altitude médiane | 0,6 m | 2,4 m | 4,0 m | 6,1 m | 9,4 m | 11,9 m |
| Altitude p90 | 2,2 m | 6,9 m | 11,5 m | 19 m | 37 m | 49 m |

- **Le relief de l'arrière-côte est presque juste.** À 100 m du rivage, 45 % de nos points dépassent 4,4 m, moyenne 8,1 m. Sur Terre : 52 % et 12 m, et au-delà de 4,4 m une falaise est plus probable qu'une plage (Young et Carilli 2019).
- **Ce qui manque, c'est la forme abrupte.** Seuls 6,5 % des rivages montent de 20 m dans les 100 premiers mètres ; 7 % ont une pente de plus de 0,65 dans les 200 premiers mètres.
- **La plaine côtière est vaste :** 50 m d'altitude à 6 km du rivage en médiane, 100 m à 15 km.

**La largeur de notre plage, en pratique**

| Haut de la bande | p10 | p25 | Médiane | p75 | p90 |
|---|---|---|---|---|---|
| 15 m, la bande actuelle | 98 m | 286 m | 540 m | 1 090 m | 1 890 m |
| 4 m | 23 m | 50 m | 92 m | 188 m | 363 m |
| 3 m | 18 m | 34 m | 66 m | 124 m | 286 m |
| 2 m | 10 m | 22 m | 40 m | 74 m | 158 m |
| 1 m | 6 m | 10 m | 18 m | 28 m | 44 m |

- **La bande actuelle :** de 5 à 25 m, centre 15 m, déplacée par `60 * local.y`, un écart type de 8,8 m. 24 % des rivages n'atteignent pas 15 m dans les 3 premiers kilomètres.
- **10 % des rivages sont plus raides que toute face de plage,** plus de 0,18 entre 0 et 3 m. 10 % sont plus plats que 0,01, des estrans.

**La ligne d'eau, au rendu**
- **La mer couvre la part du pixel sous 0 :** `1 - SpreadStep(-1, 1, elevation, elevationSpread)` dans `PixelShader.hlsl`.
- **Près du sol, l'étalement tombe à 0,** mais le fondu de −1 à +1 m reste. À la pente médiane, il fait 30 à 45 m de rivage flou. La terre jusqu'à 1 m prend la teinte de la mer, et le fond jusqu'à −1 m se voit sur la mer plate.
- **Le fond peu profond ne se voit pas :** la géométrie est plafonnée à `max(e, 0)`, et la couleur de la mer ne dépend que de `-elevation / 3000`.

## 3. Les côtes réelles : types, tailles, ce qui les décide

**Les parts du littoral mondial, qui se recouvrent**
- **Sableux, graviers compris :** 31 % du littoral libre de glace, 1,11 million de km mesurés (Luijendijk 2018). Afrique 66 %, Europe 22 %.
- **Probablement à falaise :** environ 52 % (Young et Carilli 2019). L'ancienne estimation de 80 % (Emery et Kuhn 1982) est trop haute. Europe 47 %, Californie 67 à 72 %, Malte 87 %.
- **Vaseux :** 14 % du littoral libre de glace, dont 60 % entre 25° N et 25° S. Les mangroves couvrent 17 % du trait de côte mondial.
- **Les parts se recouvrent :** une plage au pied d'une falaise compte dans les deux.
- **Par latitude :** les falaises culminent à 45 à 50°, les plages à 25 à 30° ; sous les tropiques humides, moins de 20 % de sable.

**Les plages**
- **Largeur émergée, du rivage au pied de dune :** aucune base mondiale. Narrabeen, 40 à 80 m. Îles de l'Égée : 59 % des plages font moins de 20 m au plus large.
- **Longueur :** 1,37 km en moyenne en Australie, 0,8 km pour les plages réfléchissantes, 15 km pour les dissipatives. Une plage de poche fait moins de 200 m de long.
- **Pente de la face, tan β :** 0,01 à 0,18 ; médianes régionales 0,055 à 0,08 sur 5 207 plages australiennes. Plus le grain est fin et la houle forte, plus elle est plate.
  - sable de 0,2 mm : 1/50 à 1/100 ;
  - sable de 0,5 mm : 1/20 à 1/40 ;
  - graviers de 5 mm : 1/8 à 1/15 ; bermes de galets, 0,1 à 0,25.
- **Dissipative ou réfléchissante :** paramètre de Dean Ω = Hs / (w T). Sous 1, réfléchissante, raide, sans zone de surf ; au-dessus de 6, dissipative, plate, zone de surf jusqu'à 500 m.
- **Berme :** 2 à 3,5 m au-dessus du niveau moyen ; c'est le niveau d'eau plus le jet de rive.
- **Jet de rive, R2 :** environ 1 m. Sa largeur au sol vaut R2 / tan β : 45 m sur une plage dissipative, 15 m intermédiaire, 8 m réfléchissante. Mesuré : 13 à 32 m.
- **Profil sous l'eau :** h = A x^(2/3), A de 0,08 à 0,40. Pour A = 0,1, 10 m de fond à 1 km. Profondeur de fermeture : 13 m en moyenne mondiale. Pente médiane mondiale jusque-là : 0,007.

**Les dunes**
- **Avant-dune :** moins de 1 m à 10 ou 20 m de haut, jusqu'à 35 m. Narrabeen : 3 à 9 m.
- **Champs de dunes :** de centaines de mètres à quelques kilomètres vers l'intérieur.

**Les falaises**
- **Hauteur :** l'arrière-côte à 100 m du rivage fait 12 m en moyenne, écart type 15 m ; 90 % des régions sont sous 30 m ; plus de 500 m au Yémen et en Colombie-Britannique.
- **Exemples :** Algarve, 10 à 120 m ; plateau du Caux en Normandie, 100 à 180 m ; aiguilles des Douze Apôtres, 45 m.
- **Trois formes, selon Sunamura :**
  - **type A :** une plateforme en pente douce, de 1 à 7,5°, du pied de falaise jusque sous la basse mer ;
  - **type B :** une plateforme presque horizontale, de 0,2 à 1,3°, finie au large par une petite falaise ; 80 à 270 m de large en Nouvelle-Zélande ;
  - **plongeante :** pas de plateforme, la falaise entre dans l'eau.
- **Encoche :** de quelques centimètres à quelques mètres de creux. Sa hauteur vaut à peu près le marnage.
- **Recul, médianes mondiales :** roche dure, 2,9 cm par an ; roche moyenne, 10 cm ; roche tendre, craie ou grès tendre, 23 cm. Craie normande : 0,1 à 0,5 m par an. Argiles glaciaires de Holderness : 0,8 à 2,1 m par an.

**Caps, baies, aiguilles**
- **Baies en arc :** une spirale logarithmique ou une parabole, de quelques centaines de mètres à quelques kilomètres. La forme ne dépend pas de la taille entre 0,1 et 16 km.
- **Caps :** leur avancée croît avec leur espacement et avec le contraste de dureté des roches ; elle décroît avec l'apport de sable.
- **Aiguilles :** plus nombreuses là où le sédiment manque.

**Ce qui décide plage, falaise ou rocher**
- **L'altitude de l'arrière-côte :** au-delà de 4,4 m à 100 m du rivage, la falaise devient probable. C'est la règle chiffrée la plus utile.
- **La dureté de la roche :** elle règle le recul, donc la largeur des plateformes et l'avancée des caps.
- **L'apport de sédiment :** du sable abondant fait des plages et des dunes ; rare, des aiguilles et de la roche nue.
- **L'énergie des vagues :** les côtes de tempête, de 40 à 60° de latitude, ont de larges plages et des dunes ; les mers abritées, des vagues faibles.
- **La marée :** au-delà d'un rapport de 15 entre marnage et hauteur des vagues, la plage devient estran.
- **L'histoire du niveau marin :** rias et fjords sont des vallées noyées, fluviales ou glaciaires.
- **Le cadre tectonique :** côtes de collision, plateau étroit et falaises ; marges passives, plateau large et cordons.

## 4. Les construire dans notre moteur : options comparées

**Ce que font les autres**
- **Outerra :** une carte de distance par tuile, seulement pour les tuiles qui ont terre et mer ; filtrée, son gradient oriente l'écume. Pour les parois, un déplacement horizontal dans le shader de sommets, dont l'auteur dit qu'il ne fait pas encore de vraies falaises.
- **Flight Simulator :** un champ de distance par tuile, tiré de polygones vectoriels d'eau ; il sert au fondu eau-image, à l'écume, à l'aplanissement. Leur présentation GDC admet le popping aux changements de niveau de détail.
- **Star Citizen, No Man's Sky, Elite Dangerous :** rien de publié sur les côtes.
- **SpaceEngine, Terragen :** une couleur de plage par bande d'altitude, sans forme.
- **Gaea, World Machine, World Creator :** des remappages de l'altitude près du niveau de l'eau. World Creator a un profil à deux côtés, terre et mer, avec longueurs, angles et bruit. Gaea choisit plage ou falaise par la raideur de la transition. World Machine se dit « une approximation sans simulation », et ses plages restent trop larges.
- **Houdini :** aucun nœud de côte.
- **La recherche :** Galin 2019 classe l'érosion côtière parmi les phénomènes presque jamais traités. Paris 2019 creuse falaises, grottes et arches par des primitives implicites, l'action de la mer limitée à ±8 m autour du niveau moyen. Génevaux 2013 adoucit ou raidit les versants selon la distance à la côte. Sapoval 2004 montre qu'une érosion qui s'amortit converge vers une côte fractale de dimension 4/3.

**Nos règles, pour juger :** une pure fonction de la position ; la même à toute distance ; des motifs sur la grille de la planète ; pas de mutation quand le maillage s'affine.

| Option | Pure fonction | Même à toute distance | Coût | Précision au mètre | Famille dans `geometrie.md` |
|---|---|---|---|---|---|
| **(a) Bande d'altitude, rendu** | oui | oui, par `SpreadStep` | nul | exacte : les bandes sont des hauteurs d'eau | rendu seul |
| **(b) Remappage de l'altitude près de 0,** `h' = F(h)`, type choisi par un bruit | oui | oui, si `F` est lissée par l'étalement caché | nul | largeurs en `1/pente` : bon pour une berme, faux pour une falaise | remplacement |
| **(c) Distance estimée,** `d = h / s_L`, `s_L` la pente d'un complexplanet sans octaves sous 200 m | oui | oui, `s_L` est fixe | 2 évaluations plafonnées en plus, sur les sommets côtiers | facteur 2 pour 82 à 86 % des points de 25 à 100 m | remplacement |
| **(d) Champ de distance tramé,** par tuile ou fenêtre, par inondation par sauts | non | non : dépend du texel et de la fenêtre | une passe par tuile | exacte au texel | hors règles |
| **(e) Déformation du plan de côte,** caps et baies par un bruit de dureté | oui | oui | un bruit | ne donne pas de distance | remplacement |
| **(f) Simulation,** érosion de Sapoval, primitives de Paris | non | non | lourd, précalculé | réaliste | hors règles |

**(b) Le remappage seul** ne suffit pas aux falaises. Une falaise de 20 m ne dépend pas de la pente du terrain ; un remappage en altitude en fait une rampe de 400 m sur une plaine à 5 %, et une paroi sur une colline.

**(c) La distance estimée est la clé des falaises.** Mesures du banc CPU, distance le long de la plus grande pente :

| Vraie distance | Pente prise sans les octaves sous 50 m | sous 200 m | sous 1 km |
|---|---|---|---|
| 10 m | 88 % à ×2 près | 67 % | 25 % |
| 25 m | 89 % | 82 % | 36 % |
| 50 m | 81 % | 86 % | 46 % |
| 100 m | 73 % | 82 % | 58 % |
| 200 m | 63 % | 73 % | 66 % |
| 400 m | 57 % | 66 % | 69 % |

- **Une pente sans octaves sous 200 m, prise en différences avant au pas de 50 m,** couvre la bande de 20 à 200 m des plages et falaises. Les médianes tombent juste.
- **L'erreur restante vient des octaves fines de `h`,** ±0,5 m environ : ±12 m de distance à 4 % de pente. Elle fait onduler le pied de falaise, ce qui est naturel.
- **La direction de la mer** est la descente de cette pente : `-∇h_L / |∇h_L|`. Dans les pixels, la normale du terrain la donne déjà.
- **Ne pas prendre la pente du maillage :** elle dépend de la maille, donc change en descendant.

**Le profil recommandé, étape 4 : l'érosion retire, elle n'ajoute pas**
- **`h' = min(h, P(d))`,** avec `d = h / s_L`. `P` est le profil érodé : une plateforme à +0,3 à +1 m jusqu'au recul `r`, puis une paroi de pente 2 à 6, soit 63 à 80°.
- **Le rivage ne bouge pas :** `h' ≤ h` et `P ≥ 0` sur la terre.
- **La hauteur de la falaise sort du terrain :** c'est l'altitude du terrain au recul `r`. Mesuré sur nos rivages :

| Recul `r` | Falaise médiane | Falaise p90 |
|---|---|---|
| 50 m | 2,4 m | 6,9 m |
| 100 m | 4,0 m | 11,5 m |
| 200 m | 6,1 m | 19 m |
| 500 m | 9,4 m | 37 m |

- **Un recul de 200 à 500 m approche les hauteurs de la Terre :** moyenne 12 m, 90 % sous 30 m. Il donne aussi des plateformes de la largeur des vraies, 80 à 500 m.
- **Le recul vient de la dureté :** un bruit sur la grille de la planète, à prendre dans `Geology`, pour que couleur de roche et forme de côte s'accordent. Roche tendre, recul long ; roche dure, recul court et côte plongeante.
- **De loin, une maille plus large que la falaise** prend la moyenne de `min(h, P)` sur ses hauteurs cachées, comme `SpreadStep` le fait pour les limites. Sans cela, le plateau et la falaise muteraient à l'approche.
- **La roche vient seule :** la paroi dépasse 0,65 de pente, la règle des matériaux y pose la roche et ses photos de paroi ; la plateforme, douce, prend la photo prise de dessus.
- **Coût :** deux évaluations plafonnées à 200 m, pour les seuls sommets entre 0 et 100 m d'altitude. À mesurer sur une vue côtière.

**L'étape 5 : le dépôt et le plan**
- **Berme et dune :** `h' = max(h', B(d))` là où le type est sableux. Une face de pente 0,05 à 0,11 jusqu'à une berme de 2 à 3,5 m, un haut de plage plat, une avant-dune de 2 à 10 m.
- **Caps et baies :** un bruit de dureté déplace le rivage, `h + a · dureté` près de 0. Avancée sur roche dure, baie sur roche tendre. Le rivage bouge : remplacement à l'échelle de 100 m à quelques kilomètres.
- **Aiguilles :** dans la plateforme érodée, un bruit cellulaire garde des piliers à l'altitude d'origine, là où le sédiment manque.

## 5. Le rendu du rivage, sans géométrie

**Les bandes de l'eau, toutes en altitude, donc exactes et pures**
- **La ligne d'eau, nette de près :** le fondu de −1 à +1 m devient l'étalement du pixel seul, sa pente fois sa taille. La transition se dessine par les bandes suivantes.
- **Le sable mouillé :** de 0 au jet de rive, 0,5 à 1,5 m selon l'exposition. Albédo divisé par 2 environ : 0,18 sec contre 0,09 mouillé. Sur nos pentes, 0 à 1 m fait 18 m en médiane, 44 m au p90 ; le jet de rive réel fait 8 à 45 m.
- **La brillance du mouillé :** il faut un lobe spéculaire, absent du sol aujourd'hui, qui n'est que diffus. Lagarde : diffus multiplié par `lerp(1, 0.2, porosité)`, brillance vers 1. À partager avec la mer.
- **La laisse de mer :** une ligne sombre et cassée au plus haut du jet de rive, de quelques décimètres à 1 ou 2 m. Elle suit la règle universelle de loin.
- **Les ceintures des roches,** sur la roche au rivage :
  - **mouillée** sous le jet de rive, plus sombre ;
  - **algues et balanes** sur le marnage, de −½ à +½ marnage, brun-vert ;
  - **lichen noir,** *Verrucaria maura*, juste sous la pleine mer et au-dessus, plus large sur les côtes exposées ; les vagues y ajoutent 2 à 4,4 m ;
  - **roche sèche** au-dessus.
- **Le fond sous l'eau peu profonde :** sable ou roche, atténué par la profondeur `-h`, qui est exacte. C'est le côté mer qui l'absorbe.

**Les matières**
- **Le sable de plage :** le scan Aerial Beach 01 a des rides de 50 à 80 cm, en langues ; nos rides de vent font 12,5 cm (`spec-textures-generees.md`). Sur la face de plage, les rides de vent n'ont pas lieu d'être.
- **Les galets :** une matière à part, sur les pentes de 0,1 à 0,25, là où le type de côte le dit.
- **Les falaises :** les photos de paroi en place, `marble_cliff`, et la colonne des strates. Craie, granite, grès : des teintes de `Geology` et de `StrataColumn`.
- **Candidats Poly Haven, à vérifier :** des textures de rivage, sable et roches mêlés, et le maillage `coastal_cliff_04` de 87 m déjà repéré dans `spec-parois-minerales.md`.

**Ce que la côte attend de la mer**
- **La hauteur et la période des vagues,** pour fixer le jet de rive, donc la hauteur du sable mouillé et de la laisse.
- **Un champ d'exposition partagé :** les côtes exposées ont falaises et ceintures larges, les abritées des plages et de la vase. Côte et vagues doivent lire le même bruit.
- **Le marnage, s'il y en a :** il règle les bandes d'estran. Micro sous 2 m, méso de 2 à 4 m, macro au-delà.
- **L'écume du déferlement et du jet de rive,** orientée par la direction de la mer : la descente de la pente.
- **La transparence de l'eau peu profonde,** pour voir le fond de la côte.

## 6. Mesurer contre le réel

**Le banc CPU, `tools/cotes/`**
- **Le portage CPU de complexplanet** est validé à 0,2 m contre le moteur. Il mesure en quelques minutes, sans GPU, sur des centaines de points de rivage tirés au hasard.
- **Ce qu'il sort :** largeur des bandes, pentes au rivage à six échelles, profils vers l'intérieur et le large, précision de la distance estimée, hauteurs de falaise d'un profil candidat.
- **Les scripts :** `t2.py` trouve les rivages ; sur la branche `plages`, `t8.py` mesure la largeur des bandes, `t9.py` donne les parts vraies d'un carré de sol, pour le banc de descente.

**Les cibles chiffrées**

| Grandeur | Réel | Aujourd'hui | Source |
|---|---|---|---|
| Largeur de plage | 20 à 80 m ; Égée, 59 % sous 20 m | médiane 540 m ; 39 m sur la branche `plages` | Narrabeen, Égée |
| Pente de la face de plage | médianes 0,055 à 0,08, 0,01 à 0,18 | 0,045 de 0 à 3 m | Vos 2022 |
| Pente sous l'eau jusqu'à 13 m | médiane 0,007 | environ 0,012 | Athanasiou 2019 |
| Arrière-côte à 100 m | moyenne 12 m ; 52 % au-delà de 4,4 m | moyenne 8,1 m ; 45 % | Young et Carilli 2019 |
| Côte à falaise | environ 52 % | 7 % ont une pente de plus de 0,65 | Young et Carilli 2019 |
| Côte sableuse | 31 % | toute côte tempérée | Luijendijk 2018 |
| Côte vaseuse | 14 % | 0 % | côtes vaseuses, 2023 |
| Largeur de plateforme | 80 à 500 m | aucune | Sunamura, Trenhaile |

**Les jeux de données ouverts**
- **Pentes de plage :** Australie, 132 000 transects ; Pacifique, 3 000 plages ; Californie.
- **Pentes du proche côtier, monde :** Athanasiou 2019, un point par kilomètre.
- **Profils lidar des plages des États-Unis :** USGS, pied de dune, crête, largeur, tous les 10 m.
- **Profils de Narrabeen depuis 1976.**
- **Taux de recul des falaises :** GlobR2C2, plus de 1 680 valeurs.
- **OpenStreetMap :** `natural=coastline`, `beach`, `cliff`, `bare_rock`, `shingle`. Les comptes de taginfo donnent un ordre de grandeur, les falaises intérieures comprises.
- **Téléchargements :** à autoriser au cas par cas.

**Dans le moteur**
- **`banc_descente.py`,** vues `beach` et `sea` : la part de plage de 1 500 km au sol doit rester plate.
- **`banc_qualite.py` :** aucun p95 dégradé de plus de 10 %.
- **`banc_visuel.py` :** des lieux de côte à plusieurs hauteurs, face à des photos cibles. Étretat pour la craie, l'Algarve pour le grès, la Côte de Granit rose, les Douze Apôtres pour les aiguilles, une plage australienne pour le sable. Images du domaine public, comme les `cible-*.jpg`.
- **La dimension fractale du trait de côte :** par comptage de boîtes sur les points de rivage du banc CPU, de 10 m à 10 km. Côte ouest de la Grande-Bretagne : 1,25 selon Mandelbrot.

## 7. Sources

**Géomorphologie**
- Young et Carilli 2019, falaises côtières du monde : https://escholarship.org/uc/item/579326kr
- Luijendijk et al. 2018, l'état des plages du monde : https://www.vliz.be/imisdocs/publications/ocrd/312913.pdf
- Côtes vaseuses du monde, 2023 : https://pmc.ncbi.nlm.nih.gov/articles/PMC10716179/
- Vos et al. 2022, pentes de plage en Australie : https://essd.copernicus.org/articles/14/1345/2022/
- Athanasiou et al. 2019, pentes du proche côtier, monde : https://essd.copernicus.org/articles/11/1515/2019/
- Short 2006, plages australiennes : https://ozcoasts.org.au/wp-content/uploads/2018/05/ShortJCR06.pdf
- Masselink et Short 1993, marnage relatif : https://journals.flvc.org/jcr/article/view/79047
- Plages réfléchissantes et dissipatives, Coastal Wiki : https://coastalwiki.org/wiki/Reflective_beach , https://www.coastalwiki.org/wiki/Dissipative_beach
- Jet de rive, Stockdon 2006, Coastal Wiki : https://www.coastalwiki.org/wiki/Wave_run-up
- Pente selon le grain, CEDD Hong Kong : https://www.cedd.gov.hk/filemanager/eng/content_102/p5_table.pdf
- Profil d'équilibre de Dean, Bosboom et Stive : https://geo.libretexts.org/Bookshelves/Oceanography/Coastal_Dynamics_(Bosboom_and_Stive)/07%3A_Cross-shore_transport_and_profile_development/7.02%3A_Equilibrium_shorface_profile/7.2.2%3A_(Semi-)_empirical_derivations
- Classification tectonique, Bosboom et Stive : https://geo.libretexts.org/Bookshelves/Oceanography/Coastal_Dynamics_(Bosboom_and_Stive)/02%3A_Large-scale_geographical_variation_of_coasts/2.03%3A_Tectonic_control_of_coasts/2.3.4%3A_Summary_of_the_tectonic_classification
- Environnements de vagues de Davies : https://geo.libretexts.org/Bookshelves/Oceanography/Coastal_Dynamics_(Bosboom_and_Stive)/04%3A_Global_wave_and_tidal_environments/4.03%3A_Large-scale_variation_in_wave_environments/4.3.2%3A_Wave_environments
- Bermes des îles-barrières, USGS : https://www.usgs.gov/publications/predictions-barrier-island-berm-evolution-time-varying-storm-climatology
- Narrabeen : https://pmc.ncbi.nlm.nih.gov/articles/PMC4828941/
- Plages de l'Égée : https://nhess.copernicus.org/articles/17/449/2017/
- Hesp 2011, dunes côtières : https://ref.coastalrestorationtrust.org.nz/site/assets/files/6990/568c626208ae153299b66729.pdf
- Plateformes de type A et B : https://www.erudit.org/en/journals/gpq/2006-v60-n1-gpq1758/016362ar/ , https://pmc.ncbi.nlm.nih.gov/articles/PMC4754505
- Plateformes de Nouvelle-Zélande : https://researchspace.auckland.ac.nz/handle/2292/19986
- Encoches : https://www.redalyc.org/pdf/505/50544801002.pdf
- Prémaillon et al. 2018, GlobR2C2, recul des falaises : https://esurf.copernicus.org/articles/6/651/2018/
- Recul de la craie du Sussex : https://research.edgehill.ac.uk/en/publications/temporal-and-spatial-variations-of-chalk-cliff-retreat-in-east-su/
- Baies en arc : https://nora.nerc.ac.uk/id/eprint/512322/
- Limber et Murray 2014, caps : https://scholars.duke.edu/publication/1033824
- Douze Apôtres : https://www.doi.org/10.2112/SI75-119.1
- Bird et al. 2013, zones des rivages rocheux : https://pmc.ncbi.nlm.nih.gov/articles/PMC3792175/
- Ceinture de *Verrucaria maura*, MarLIN : https://www.marlin.ac.uk/habitats/detail/120/verrucaria_maura_on_littoral_fringe_rock
- Sable mouillé plus sombre : https://www.wgtn.ac.nz/scps/staff/pdf/darkerwhenwet.pdf , https://pmc.ncbi.nlm.nih.gov/articles/PMC4226492/
- Morphologie des plages des États-Unis, USGS : https://www.usgs.gov/data/lidar-derived-beach-morphology-dune-crest-dune-toe-and-shoreline-us-sandy-coastlines
- Profils de Narrabeen : https://datadryad.org/dataset/doi:10.5061/dryad.28g01
- Pentes de plage du Pacifique : https://zenodo.org/records/18368941
- OpenStreetMap, valeurs de `natural` : https://taginfo.openstreetmap.org/keys/natural#values
- Mandelbrot 1967 : https://gis.humboldt.edu/olm/courses/gsp_510/Articles/Mandelbrot1967.pdf

**Moteurs et outils**
- Outerra, carte de distance du rivage : https://outerra.blogspot.com/2011/02/ocean-rendering.html
- Outerra, algorithme du terrain : https://outerra.blogspot.com/2009/02/procedural-terrain-algorithm.html
- Outerra, déplacement horizontal : https://outerra.blogspot.com/2009/05/horizontal-displacement.html
- Flight Simulator, Fuentes, GDC 2022 : https://www.asobostudio.com/files/inline-images/Designing_Terrain_System_Fuentes_Lionel.pdf
- SpaceEngine, créer une planète : https://spaceengine.org/manual/making-addons/creating-a-planet/
- Gaea, nœud Sea : https://docs.quadspinner.com/Reference/Water/Sea.html
- Gaea, nœud Coast : https://docs.quadspinner.com/Reference/Water/Coast.html
- World Machine, érosion côtière : https://www.world-machine.com/blog/?p=73
- World Creator, filtre Shore : https://docs.world-creator.com/reference/terrain/filters/effect/shore
- Houdini, HeightField Erode : https://www.sidefx.com/docs/houdini/nodes/sop/heightfield_erode.html
- Crest, eaux peu profondes : https://crest.readthedocs.io/en/stable/user/shallows-and-shorelines.html
- Sea of Thieves, SIGGRAPH 2018 : https://history.siggraph.org/wp-content/uploads/2022/09/2018-Talks-Ang_The-Technical-Art-of-Sea-of-Thieves.pdf
- Lagarde, surfaces mouillées : https://seblagarde.wordpress.com/2013/04/14/water-drop-3b-physically-based-wet-surfaces/

**Recherche en synthèse d'images**
- Galin et al. 2019, revue de la modélisation des terrains : https://people.cs.uct.ac.za/~jgain/wp-content/papercite-data/pdf/galin2019.pdf
- Génevaux et al. 2013, terrains par l'hydrologie : https://www.cs.purdue.edu/homes/bbenes/papers/Genevaux13ToG.pdf
- Cordonnier et al. 2016, soulèvement et érosion fluviale : https://www.cs.purdue.edu/homes/bbenes/papers/Cordonier16CGF.pdf
- Paris et al. 2019, amplification par formes implicites, falaises et arches marines : https://people.cs.uct.ac.za/~jgain/wp-content/papercite-data/pdf/paris2019.pdf
- Paris et al. 2020, roches en blocs implicites : https://hal.science/hal-02926218
- Doran et Parberry 2010, agents de plage : https://ianparberry.com/pubs/terrain.pdf
- Sapoval et al. 2004, côtes fractales par érosion : https://arxiv.org/abs/cond-mat/0311509
- Quilez, estimation de distance : https://iquilezles.org/articles/distance/
- Quilez, dérivées du bruit de gradient : https://iquilezles.org/articles/gradientnoise/
- Rong et Tan 2006, inondation par sauts : https://www.comp.nus.edu.sg/~tants/jfa/i3d06.pdf
- libnoise, complexplanet : https://raw.githubusercontent.com/eXpl0it3r/libnoise/master/examples/complexplanet.cpp

**Non vérifié ou manquant**
- Aucune statistique mondiale de largeur de plage, de hauteur ou de pente de falaise, de largeur d'avant-dune, de taille d'aiguille ou de crique.
- Les hauteurs en mètres de la ceinture de lichen noir ; les parts mondiales de micro, méso et macro marées.
- Les pages de Proland et de HAL n'ont pu être lues directement.
