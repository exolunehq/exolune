# Recherche : un relief planétaire tectonique pour Exolune

Statut : recherche du 2026-10-31. Elle fonde `spec-relief-tectonique.md`, la spec vivante du relief tectonique, le relief du jeu depuis le 2026-10-31. Les étapes 0 à 3 sont faites : la règle de la carte qui porte la géométrie, la carte tectonique, les grandes formes, le détail. Ce qui a changé depuis ce plan est dans la spec : la croûte continentale par lieu, une carte de 512² en texels de 20 km, aucune vallée creusée.

**Les renvois au niveau 0,** `recherche-erosion-niveaux.md`, `recherche-dendry.md`, `level0_erosion.py` et `level0_cut.py`, visent la branche `erosion-niveaux`, pas encore fusionnée.

## 1. Conclusion

**Le relief part d'une carte tectonique calculée au démarrage, pas d'un bruit.** Le bruit ne fait plus que le détail, sous 50 km, modulé par la géologie.

- **Pourquoi :** le relief actuel n'a aucune structure qui s'accorde avec l'eau. 41 % des terres sont en cuvettes ; le niveau 0 doit inventer un soulèvement en copiant les hauteurs de complexplanet, et ses fleuves traversent les massifs (`recherche-erosion-niveaux.md`, 5 bis à 5 quinquies).
- **Ce que la littérature et les jeux s'accordent à faire :** la structure globale se calcule une fois, hors du rendu ; le rendu l'évalue point par point et y ajoute du bruit. Personne ne simule les plaques par image.
- **La recommandation, en quatre couches :**
  1. **Le précalcul tectonique,** au démarrage, en C++ : des plaques, leurs mouvements, leurs frontières typées, et des champs lisses sur le cube de la planète, 6 × 1 024².
  2. **Les grandes formes,** dans le shader : des profils analytiques appliqués aux distances aux frontières. Continents, plateaux, chaînes, fosses, arcs, rifts, dorsales.
  3. **Le détail,** dans le shader : les briques de `Noise.hlsli`, orientées par la direction des plis et pondérées par l'âge et la roche.
  4. **L'érosion,** au démarrage : le niveau 0 reçoit enfin un vrai soulèvement, celui des frontières convergentes ; son relief érodé devient le relief au-dessus de deux de ses cellules.
- **Une simulation pas à pas, à la Cortial, n'est pas la première étape.** Un instantané cinématique, des plaques et leurs vitesses à un instant, donne déjà les frontières et leurs types, en quelques secondes et sans chaos. L'histoire, les sutures anciennes, se synthétise à part.
- **Le coût par sommet baisse probablement.** Trois lectures de carte et 40 à 80 évaluations de bruit, contre environ 340 aujourd'hui (`concept.md`, point 7). À mesurer.
- **Une règle de `principes.md` change :** la carte de la planète portera de la géométrie, au-dessus de deux texels. Décidée et écrite le 2026-10-31, avant tout code.

## 2. Le post Reddit signalé

**Il n'a pas pu être lu.** reddit.com, old.reddit.com, l'URL en `.json` et api.reddit.com sont refusés par l'outil de lecture du web et par le navigateur intégré, pour raison de sécurité. Aucun moteur de recherche n'indexe encore le fil `1xhximl`.

- **Ce qui manque :** son texte, ses commentaires, et le dépôt ou la vidéo qu'il cite.
- **Pour le lire :** coller le texte du post, ou le lien du dépôt ou de la vidéo, et je complète cette section.
- **Le candidat le plus probable, non confirmé : World Orogen,** `orogen.studio`, dépôt `raguilar011095/planet_heightmap_generation`. Créé en février 2026, mis à jour le 2026-10-31, 135 étoiles, sous **GPL-3.0** : idées seulement, aucun code.
  - **V1 :** sphère de Fibonacci, plaques par croissance concurrente, frontières convergentes, divergentes et transformantes, subduction selon la densité.
  - **Le relief V1 :** trois champs de distance, montagne, océan, côte, combinés par une moyenne harmonique ; profils de chaînes asymétriques, plateau continental, bassins d'avant-pays, rifts en graben, dorsales, fosses, arcs insulaires, points chauds.
  - **Puis :** gauchissement par bruit, Priority-Flood qui creuse les cols, puissance fluviale implicite à la Braun et Willett, érosion glaciaire et thermique.
  - **V2, « Evolution » :** une vraie histoire tectonique, cycle des supercontinents, collisions, rifting, sutures, avec 20 000 à 80 000 cellules de simulation. Les roches de l'histoire règlent l'érodabilité.
- **Les autres candidats récents :** la série « Plate Tectonics Simulation » de DasTobi, vidéo de février 2026 ; « Around the World » de Frozen Fractal, qui a abandonné sa simulation de plaques, trop lente et trop dure à contrôler, pour des plaques de Voronoï et du bruit.

**La leçon commune de ces projets,** utile quel que soit le post : les plaques donnent la structure, mais l'érosion fait le réalisme ; et une simulation pas à pas se contrôle mal. World Orogen V1 et Frozen Fractal partent d'un instantané, pas d'une histoire.

## 3. Ce que le relief actuel ne peut pas donner

- **Aucune structure géologique.** Les montagnes naissent d'un seuil sur un bruit, `RlTerrainType`, qui croît vers l'intérieur des terres. Elles ne suivent aucune frontière et n'ont aucun âge.
- **Aucun drainage.** 41 % des terres en cuvettes fermées, profondes de 260 m en médiane (`recherche-rivieres.md`).
- **Un niveau 0 qui travaille contre son entrée.** Son soulèvement est inversé pour retrouver les hauteurs de complexplanet ; les bassins restent géants ou les massifs s'abaissent ; ses tracés passent à travers les montagnes, 44 % de la longueur des fleuves creusée à plus de 50 m sous le sol.
- **Pas de fond océanique.** Le plateau est une rampe jusqu'à −700 m, puis un bruit lisse ; ni dorsale, ni fosse, ni arc (`recherche-cotes.md`).
- **La leçon du spike B :** à 1 km, complexplanet est un labyrinthe de cuvettes. Toute érosion qui s'y appuie le comble ou l'entaille. Le relief doit naître déjà organisé.

## 4. L'état de l'art

Pour chaque source : ce qu'elle apporte, son coût, et sa compatibilité avec notre contrainte, une fonction de la position évaluée par image avec des données précalculées au démarrage.

### 4.1 La tectonique procédurale

**Cortial, Peytavie, Galin, Guérin, « Procedural Tectonic Planets », CGF 38(2), 2019.**
- **L'apport :** la croûte est un nuage de points sur la sphère ; chaque point porte son épaisseur, son type, l'âge de la croûte océanique, le type et l'âge de l'orogenèse, la direction des plis. Les plaques tournent autour de leur pôle d'Euler.
- **Les phénomènes :** le soulèvement par subduction, fonction de la distance au front, de la vitesse relative et de l'altitude de la plaque plongeante ; la collision continentale, qui soude un terrane et soulève une large zone ; la croûte neuve aux dorsales, selon un profil de dorsale ; le rifting, qui découpe une plaque ; l'érosion continentale et l'amortissement océanique, linéaires dans le temps.
- **Les ordres de grandeur de l'article,** cités de mémoire, le PDF de plus de 10 Mo n'ayant pas pu être relu par l'outil : pas de temps de 2 Ma ; dorsale à −1 km, plaine abyssale à −6 km, fosse à −10 km, sommets jusqu'à 10 km ; portée de la subduction 1 800 km ; vitesse maximale 100 mm/an. À vérifier.
- **L'amplification :** les paramètres de croûte choisissent le détail. Des primitives procédurales pour l'océan, orientées par la dorsale, avec ses failles transformantes ; des exemplaires de MNT réels pour les continents, orientés par les plis et choisis par type d'orogenèse.
- **Le coût :** une simulation pas à pas sur CPU, puis une amplification coûteuse. Des secondes à des minutes selon la résolution, à relire dans l'article.
- **La compatibilité :** la simulation, oui, au démarrage. L'amplification par exemplaires demande une base de MNT réels ; une version par primitives procédurales est évaluable point par point.
- **Ce qu'on en prend :** les paramètres de croûte comme champs, et la forme des profils de subduction, de collision et de dorsale. Pas la boucle en temps, du moins pas d'abord.

**Andy Gainey, Experilous, « Procedural Planet Generation », 2014.**
- **L'apport :** l'instantané cinématique. Icosaèdre subdivisé, plaques par croissance aléatoire, un pôle de rotation par plaque. À chaque arête de frontière, la vitesse relative donne une pression, normale, et un cisaillement, tangent. Le type de frontière en découle : collision, subduction, divergence, transformante.
- **Le relief :** l'altitude de chaque frontière, puis une interpolation vers l'intérieur des plaques selon la distance à la frontière et au centre de la plaque, puis du bruit.
- **Le coût :** une seconde ou moins sur le navigateur, à quelques dizaines de milliers de cellules.
- **La compatibilité :** directe pour le précalcul. C'est le modèle de la couche 1 recommandée.
- **La limite :** le site est hors ligne au moment de cette recherche ; la licence du code n'a pas pu être vérifiée.

**Red Blob Games, « Procedural map generation on a sphere », 2018.**
- **L'apport :** la même idée, plus simple : points de Fibonacci, triangulation de Delaunay, plaques par remplissage, montagnes là où les plaques se rapprochent, par des champs de distance aux montagnes, à l'océan et à la côte.
- **Le coût :** quelques centaines de millisecondes.
- **La licence :** Apache-2.0.

**PlaTec, Viitanen 2012,** et WorldEngine qui l'utilise.
- **L'apport :** une simulation 2D de plaques sur une carte plane, rapide, pour des cartes de hauteur.
- **La limite :** une carte plane qui se replie, pas une sphère.
- **La licence :** LGPL-3.0 pour PlaTec ; WorldEngine est MIT mais embarque PlaTec. Rien à reprendre.

**World Orogen, 2026,** décrit à la section 2.
- **L'apport :** la chaîne complète la plus aboutie en accès libre : plaques, profils par type de frontière, puis érosion fluviale, glaciaire, thermique, et roches qui règlent l'érodabilité.
- **La licence :** GPL-3.0. Idées seulement.

**Michel, Emilien, Cani, « Generation of Folded Terrains from Simple Vector Maps », Eurographics short 2015.**
- **L'apport :** des plis à grande échelle à partir d'un modèle de plaques simplifié, affinés ensuite par une érosion hydraulique qui tient compte des rivières.
- **Ce qu'on en prend :** les plis comme champ orienté, parallèle au front.

**Les autres projets ouverts, vus pour leurs licences :** tectonics.js, CC-BY-4.0 ; SimpleTectonics, sans licence, donc tous droits réservés ; realistic-planet-generation-and-simulation, sans licence. Rien à reprendre.

### 4.2 Le soulèvement et l'érosion

**Cordonnier, Braun, Cani, Benes, Galin, Peytavie, Guérin, « Large Scale Terrain Generation from Tectonic Uplift and Fluvial Erosion », CGF 35(2), 2016.**
- **L'apport :** le terrain naît d'une carte de soulèvement et de la loi de puissance fluviale. Un graphe de drainage sur des points de Poisson, un solveur implicite à la Braun et Willett, les lacs résolus par un graphe des bassins. Les chaînes apparaissent là où le soulèvement est fort ; le réseau est en arbre et va à la mer.
- **Le coût :** des minutes sur CPU pour un domaine régional.
- **La compatibilité :** au démarrage, oui. C'est exactement le niveau 0 actuel ; il ne lui manque qu'un soulèvement qui ait un sens.
- **Ce qu'on en prend :** le soulèvement vient de la tectonique, pas des hauteurs voulues.

**Cordonnier, Cani, Benes, Braun, Galin, « Sculpting Mountains », TVCG 2018.**
- **L'apport :** des couches de roche plissées sous le terrain ; l'érosion dépend de la dureté de la roche affleurante.
- **Ce qu'on en prend :** un champ de roche qui règle l'érodabilité K du niveau 0 et le type de bruit en surface.

**Schott, Paris, Fournier, Guérin, Galin, « Large-scale Terrain Authoring Through Interactive Erosion Simulation », ACM TOG 42, 2023.**
- **L'apport :** la puissance fluviale avec soulèvement, entièrement sur GPU, interactive d'après les auteurs. L'utilisateur peint le soulèvement ; la chaîne et son réseau suivent.
- **La compatibilité :** au démarrage, sur GPU. C'est la voie pour passer le niveau 0 de 10 minutes en Python à quelques secondes.
- **La licence :** MIT, dépôt `H-Schott/StreamPowerErosion`. Lisible, mais le code d'Exolune reste original.

**Tzathas, Gailleton, Steer, Cordonnier, « Physically-based Analytical Erosion for fast Terrain Generation », CGF 43(2), 2024.**
- **L'apport :** une solution analytique de la loi de puissance fluviale sous soulèvement. Plus d'intégration en temps : le relief d'équilibre se calcule le long du réseau, comme l'intégrale χ de Perron et Royden 2013.
- **Le coût :** de l'ordre d'une passe sur le réseau, après le drainage. Le code de `level0_erosion.py` a déjà une `chi_integral`.
- **La compatibilité :** au démarrage, directe. C'est le niveau 0 le moins cher.

**Braun et Willett, FastScape, 2013.**
- **L'apport :** le solveur implicite en O(n) le long du réseau, que `level0_erosion.py` met déjà en œuvre.
- **La licence :** fastscapelib, la bibliothèque de référence, est GPL-3.0 ; son enveloppe Python `fastscape` est BSD-3 mais dépend d'elle. L'algorithme publié est libre ; le code d'Exolune est le sien.

**Schott, Galin, Guérin, Paris, Peytavie, « Terrain Amplification using Multi-scale Erosion », ACM TOG 43(4), 2024.**
- **L'apport :** une amplification par érosions fluviale, thermique et de dépôt, alternées avec des suréchantillonnages ×2.
- **La compatibilité :** sur une grille entière, oui ; par tuiles, non : le spike B a montré qu'une érosion simulée diverge selon ses bords. Utilisable une fois sur la carte de la planète, pas autour de la caméra.
- **La licence :** MIT, `H-Schott/MultiScaleErosion`.

### 4.3 L'hydrologie d'abord

**Génevaux, Galin, Guérin, Peytavie, Benes, « Terrain Generation Using Procedural Models Based on Hydrology », ACM TOG 32(4), 2013.**
- **L'apport :** le réseau de rivières d'abord, à partir des embouchures sur une côte ; ordre de Strahler ; un type de lit par pente, selon Rosgen. Le terrain est un arbre de construction de primitives, vallées, collines, lacs, mêlées par des opérateurs.
- **La compatibilité :** le terrain est une fonction continue de la position, évaluable partout, à partir d'un réseau précalculé. Son coût par point est le nombre de primitives qui le couvrent, accéléré par une structure spatiale.
- **Ce qu'on en prend :** des primitives de vallée posées sur les fleuves du niveau 0, au profil réglé par leur débit et leur pente.

**Derzapf, Ganster, Guthe, Klein, « River Networks for Instant Procedural Planets », CGF 30(7), 2011.**
- **L'apport :** un réseau planétaire hiérarchique, raffiné à la volée.
- **La limite :** le relief y suit le réseau ; il ne sert pas un relief déjà donné.

**Gaillard et al., « Dendry », I3D 2019.**
- **L'apport :** un arbre dendritique calculable localement, niveau par niveau. Environ 10 s pour une grille de 512² sur un CPU à quatre cœurs.
- **La compatibilité :** par tuiles autour de la caméra, pas par sommet à chaque image (`recherche-dendry.md`, section 6).
- **La licence :** le code des auteurs, `mgaillard/Noise`, est **GPL-3.0**. Rien à reprendre ; la maquette d'Exolune est son propre code.

### 4.4 L'amplification et l'analyse

**Guérin, Digne, Galin, Peytavie, « Sparse Representation of Terrains for Procedural Modeling », CGF 35(2), 2016.**
- **L'apport :** le relief comme combinaison creuse d'atomes appris sur des MNT réels ; l'amplification remplace chaque atome grossier par son jumeau fin.
- **La compatibilité :** évaluable par point, mais il faut un dictionnaire appris sur des données réelles.
- **La licence :** MIT, en Matlab, `eric-guerin/terrain-amplification`.

**Galin et al., « A Review of Digital Terrain Modeling », CGF 38(2), STAR Eurographics 2019.**
- **L'apport :** la revue de référence : procédural, simulation, exemples. Elle situe chaque méthode ci-dessus.

**Grenier, Guérin, Galin, Sauvage, « Real-time Terrain Enhancement with Controlled Procedural Patterns », CGF 43(1), 2024.**
- **L'apport :** des motifs de phase, indépendants de la résolution, dont on contrôle la direction en chaque point.
- **La compatibilité :** directe, par point. C'est l'outil pour orienter les crêtes le long des plis sans cisailler le bruit.

**Argudo et al., « Terrain descriptors for landscape synthesis, analysis and simulation », Eurographics STAR 2025.**
- **L'apport :** des descripteurs mesurables : hypsométrie, pentes, proéminence, réseaux. Pour juger un relief contre la Terre.
- **La licence :** MIT, `oargudo/terrain-descriptors`. Utile pour les bancs, hors du moteur.

**Les modèles appris :** Borg et al., « Authoring Terrestrial Planets with Diffusion Models », CGF 45(2), 2026, conditionnés par un réseau fluvial global ; « Terrain Diffusion », arXiv 2025.
- **La compatibilité :** non par image. Un réseau de diffusion au démarrage sur la carte de la planète serait possible, mais il apporte un poids appris et des données d'entraînement : contraire à un code entièrement original.

### 4.5 Les bruits « érodés »

**Quilez, le bruit à dérivées analytiques.**
- **L'apport :** chaque octave du fBm est atténuée par la pente accumulée des octaves plus grossières, en 1 / (1 + |∇|²). Les pentes restent lisses, les creux et les replats se couvrent de détail : un aspect érodé, sans érosion.
- **Le coût :** une évaluation de bruit avec ses dérivées, environ 1,5 à 2 fois une évaluation simple.
- **La compatibilité :** directe, par point.
- **La licence :** le site de Quilez met sous MIT le code qui implémente un algorithme, et garde ses œuvres sous droit d'auteur ; ses shaders artistiques, comme « Elevated », interdisent toute réutilisation depuis 2021. L'idée est libre ; on l'écrit nous-mêmes.

**Le filtre d'érosion de runevision, Rune Skovbo Johansen, 2026.**
- **L'apport :** des ravines en ondes alignées sur la pente, posées sur des cellules à pivot aléatoire et mêlées entre voisines ; octave après octave, elles bifurquent. Chaque point s'évalue isolément.
- **Ses limites, dites par l'auteur :** pas de réseau global ; des lignes qui s'arrêtent à mi-pente ; un fondu selon l'altitude qui n'est pas robuste.
- **La licence :** le billet publie le code sous MPL-2.0. Un gist de l'auteur précise que la fonction centrale dérive de shaders de Fewes et clayjohn sous CC BY-NC-SA 3.0. Idée seulement.
- **Dans le projet :** une piste existe déjà, `piste/erosion-filtre` (`geometrie.md`).

### 4.6 Les jeux

**No Man's Sky,** GDC 2017, Innes McKendrick et Sean Murray.
- **Ce qu'on en sait :** un « uber noise » par point, sur des voxels : gauchissement du domaine, atténuation par les dérivées, crêtes, plateaux, régions. Aucune tectonique ; une variété d'aspect, pas une géologie.

**Elite: Dangerous, Stellar Forge.**
- **Ce qu'on en sait :** une simulation du haut vers le bas, de la galaxie à la planète. Les propriétés de chaque planète, matériaux, volcanisme, tectonique, températures, sont envoyées au GPU dans un tampon ; des graphes de bruit en compute shaders les évaluent, fonction de la position et de l'identifiant de la planète. Double précision ou paires de floats, comme nous.
- **Ce qu'on en prend :** la confirmation du modèle : des paramètres géologiques précalculés, un relief évalué par point.

**Star Citizen, Planet Tech v4 et v5.**
- **Ce qu'on en sait :** des cartes globales créées par les artistes, puis des tuiles de hauteur de 4 km, en 2k, distribuées par écosystème. La v5, dite Genesis, ajoute des cartes de climat, de sol, de géologie et d'érosion qui décident du détail.
- **La différence :** de l'auteur, pas de la génération pure.

**SpaceEngine.**
- **Ce qu'on en sait :** des tuiles en arbre quaternaire générées sur GPU et gardées ; des bruits à crêtes, cratères, volcans ; des pseudo-rivières en boucles depuis 2013 (`recherche-rivieres.md`).

**Outerra.**
- **Ce qu'on en sait, de ses présentations publiques :** le MNT réel de la Terre, raffiné par du fractal sur GPU. Pas de génération de planète.

**Le constat :** aucun de ces jeux ne simule les plaques en vol. La géologie, quand elle existe, est un précalcul ou une donnée ; le rendu évalue une fonction de la position, comme Exolune.

## 5. Les licences

| Code | Licence | Verdict |
|---|---|---|
| libnoise, dont complexplanet | LGPL | interdit, déjà écarté |
| PlaTec, plate-tectonics | LGPL-3.0 | interdit |
| WorldEngine | MIT, embarque PlaTec | interdit tel quel |
| fastscapelib | GPL-3.0 | interdit ; l'algorithme reste libre |
| fastscape, l'enveloppe | BSD-3, dépend de fastscapelib | à écarter |
| World Orogen | GPL-3.0 | interdit |
| Dendry, `mgaillard/Noise` | GPL-3.0 | interdit |
| tectonics.js | CC-BY-4.0 | à écarter, licence non logicielle |
| SimpleTectonics | aucune, tous droits réservés | interdit |
| realistic-planet-generation-and-simulation | aucune | interdit |
| Experilous, générateur de planète | non vérifiée, site hors ligne | à écarter |
| Red Blob Games, 1843-planet-generation | Apache-2.0 | permis, avec avis ; inutile |
| StreamPowerErosion, Schott 2023 | MIT | permis ; on le lit, on n'en copie rien |
| MultiScaleErosion, Schott 2024 | MIT | idem |
| terrain-amplification, Guérin 2016 | MIT | idem |
| terrain-descriptors, Argudo 2025 | MIT | pour les bancs |
| Filtre d'érosion de runevision | MPL-2.0, une fonction d'origine CC BY-NC-SA | interdit |
| Shaders de Quilez | MIT pour les algorithmes, droit d'auteur pour les œuvres | à écarter ; l'idée est libre |

**La règle suivie :** aucune ligne n'est reprise, même sous MIT. Le relief est écrit en salle blanche depuis cette recherche et les articles, comme `Relief.hlsli` l'a été depuis complexplanet.

## 6. L'architecture recommandée

### 6.1 Vue d'ensemble

| Couche | Échelles | Où, quand | Ce qu'elle donne |
|---|---|---|---|
| 1. Précalcul tectonique | plaques de 1 000 à 10 000 km ; champs à 10 km | CPU, au démarrage, environ 1 à 3 s | plaques, frontières typées, distances, vitesses, âges, roche, soulèvement |
| 2. Grandes formes | 6 000 km à 50 km | shader, par sommet, depuis la carte | croûte, plateau, chaînes, fosses, arcs, rifts, dorsales, points chauds |
| 3. Détail | 50 km à 13,5 m | shader, par sommet, bruit | crêtes orientées, ravines, plaines, terrasses, volcans |
| 4. Niveau 0 | au-dessus de 20 à 40 km | au démarrage, CPU puis GPU | relief érodé, drainage, lacs, débit |

**Le relief final, par sommet :**
- au-dessus de deux cellules du niveau 0 : le relief érodé du niveau 0, lu en B-spline cubique ;
- sur la mer, et partout où l'eau n'agit pas : les grandes formes de la couche 2 ;
- en dessous : le détail de la couche 3, pondéré par la géologie et éteint dans les vallées du niveau 0.

### 6.2 Le précalcul au démarrage

**La grille :** le cube de la planète de `PlanetMap`, 6 × 1 024², 9,8 km au centre d'une face, 4,6 km aux coins. Ses voisins à travers les arêtes existent déjà, `ForNeighbours`.

**Les étapes, toutes déterministes, sur un seul fil ou sans ordre variable :**
1. **Les cratons et les continents.** Des noyaux continentaux posés par tirage du point le plus éloigné, puis grandis par un remplissage à coût bruité jusqu'à la part voulue. Environ 65 % de croûte continentale pour 60 % de terres, le reste en plateaux noyés. Indépendants des plaques : là où un continent chevauche une frontière naissent collisions et rifts.
2. **Les plaques.** 12 à 20 plaques, de tailles en loi de puissance comme sur Terre (Bird 2003). Germes par point le plus éloigné, croissance concurrente à coût bruité : des frontières irrégulières, jamais des arcs de grand cercle.
3. **Les mouvements.** Un pôle d'Euler et une vitesse angulaire par plaque, de 1 à 10 cm/an ; les plaques continentales plus lentes que les océaniques.
4. **Les frontières.** En chaque cellule de frontière, la vitesse relative (ω_a − ω_b) × p, projetée sur la normale et la tangente. Le type en découle :
   - convergente, avec sa polarité : l'océanique plonge sous la continentale, la plus vieille sous la plus jeune ; deux continents se heurtent ;
   - divergente : dorsale en mer, rift sur un continent ;
   - transformante, si le cisaillement domine.
   Des segments de dorsale décalés par des failles transformantes, tous les 100 à 500 km.
5. **Les champs de distance.** Une propagation du germe le plus proche sur la grille, comme la Priority-Flood existante : distance signée au front convergent, distance à l'axe divergent, distance signée à la marge continentale, distance à la faille transformante. Précision au kilomètre ; lissés sur deux texels.
6. **Les âges.**
   - Croûte océanique : la distance à sa dorsale sur la demi-vitesse d'expansion.
   - Chaînes actives : de 0 à 50 Ma selon la durée supposée de la convergence.
   - Sutures anciennes, à l'intérieur des continents, entre les cratons : de 100 à 1 000 Ma, tirés par graine. C'est l'histoire synthétisée, sans simulation : les Appalaches et l'Oural d'Exolune.
7. **La roche.** Un indice continu : socle cristallin des cratons, bassins sédimentaires, roches volcaniques des arcs et des points chauds, roches plissées des chaînes. Il règle le bruit et l'érodabilité.
8. **Le soulèvement.** Positif sur les fronts convergents, selon la vitesse de convergence et un profil en travers ; négatif dans les avant-pays et les rifts ; nul sur les cratons.

**Le stockage :** deux cubes RGBA16F de 1 024², mipmappés comme `planetMap`, environ 100 Mo en tout avec les mips.
- **Le premier :** distance signée au front convergent ; distance à l'axe divergent ; distance signée à la marge continentale ; vitesse de convergence au front le plus proche.
- **Le second :** âge, de la croûte ou de l'orogenèse ; type de collision, en poids continu d'océan à continent ; indice de roche ; soulèvement.
- **La direction des plis n'est pas stockée :** elle est perpendiculaire au gradient de la distance au front, lu par deux lectures voisines.
- **Le demi-flottant suffit :** des distances au kilomètre sur 20 000 km tiennent en 11 bits de mantisse à 10 km près ; la distance fine se reconstruit par le profil.

**La résolution :** 1 024² pour les champs, la grille de la carte actuelle. Les formes qu'ils portent font plus de 50 km, au moins cinq texels. 512² suffirait à l'essai ; 2 048² n'apporterait rien que le bruit ne fasse mieux.

**Le temps, estimé :** les étapes 1 à 8 sont des remplissages et des propagations sur 6,3 millions de cellules, comme la Priority-Flood qui tourne déjà à chaque démarrage. De l'ordre de la seconde à quelques secondes en C++. À mesurer.

### 6.3 Les grandes formes

**Le principe :** la carte donne des distances lisses ; le shader en fait des formes nettes par des profils analytiques. Les arêtes vives, l'axe d'une fosse, le bord d'un graben, viennent du profil, jamais des texels.

**Les valeurs de départ,** tirées de la géophysique publiée, à régler pour 60 % de terres, des sommets de 5 à 8 km et des fosses à −8 km :

| Forme | Où | Profil |
|---|---|---|
| Craton | loin de toute frontière, sur la croûte continentale | +200 à +600 m, ondulations de 500 à 2 000 km de ±300 m : bassins et dômes intracratoniques |
| Plateau continental | de la côte à la rupture de pente | jusqu'à −130 m ; 80 à 300 km de large sur une marge passive, 10 à 40 km sur une marge active |
| Talus et glacis | après la rupture | jusqu'à −3 000 m sur 50 à 100 km, puis la plaine abyssale |
| Croûte océanique | partout en mer | −(2 500 + 350 √âge) m, l'âge en Ma, plafonné à −6 000 m (Parsons et Sclater 1977 ; Stein et Stein 1992) |
| Dorsale lente | axe divergent océanique | vallée axiale de 1 à 2 km de creux, 20 à 30 km de large ; failles transformantes et zones de fracture perpendiculaires |
| Dorsale rapide | idem, expansion rapide | un dôme axial de quelques centaines de mètres |
| Fosse | front convergent, côté plongeant | −8 000 m à l'axe, 50 à 100 km de large ; bourrelet externe par flexion, w₀ e^(−x/α) cos(x/α), α ≈ 70 km, +300 à +500 m |
| Arc insulaire | océan contre océan, à 150 à 300 km du front | chapelet de cônes, quelques îles au-dessus de la mer, et un bassin d'arrière-arc |
| Cordillère | océan contre continent | une chaîne de 150 à 400 km de large, jusqu'à 6 à 7 km selon la convergence, un arc volcanique sur sa crête, un haut plateau derrière si la convergence est forte |
| Chaîne de collision | continent contre continent | 200 à 400 km de large, 6 à 8 km ; un plateau de 4,5 à 5 km jusqu'à des centaines de km derrière si la collision est forte |
| Bassin d'avant-pays | devant la chaîne, sur la plaque plongeante | une flexion de −200 à −500 m avant comblement, α ≈ 100 à 150 km ; le niveau 0 la comble en plaine |
| Rift continental | axe divergent sur un continent | un graben de 40 à 60 km, fond 1 à 2 km sous des épaulements de +0,5 à +1,5 km ; une mer étroite s'il s'ouvre |
| Faille transformante | sur un continent | une vallée linéaire, ±200 m, des bassins en losange |
| Point chaud | tirés par graine, avec leur traînée le long du mouvement de la plaque | un bombement de +1 km sur 500 km ; des boucliers volcaniques qui vieillissent et s'enfoncent le long de la traînée |
| Chaîne ancienne | suture intracontinentale | l'amplitude décroît avec l'âge, A₀ e^(−âge/τ), τ de 100 à 200 Ma, un réglage ; 1 à 2 km à 300 Ma |

**La hypsométrie qui en sort est bimodale,** comme sur Terre : des continents vers +500 m, des océans vers −4 à −5 km. complexplanet n'a qu'un mode étalé.

**Le gauchissement :** un léger gauchissement des coordonnées de lecture, de 5 à 50 km, filtré par la maille, casse ce que les profils auraient de trop régulier. Il est appliqué avant toute lecture de carte, pour que toutes les couches restent d'accord.

### 6.4 Les échelles moyennes et fines

**Les briques :** `Noise.hlsli` reste tel quel : fBm, billow, ridged, Voronoi, turbulence, et leur filtrage. Deux briques s'ajoutent, écrites ici :
- **un bruit avec ses dérivées analytiques,** pour l'atténuation par la pente à la Quilez et pour orienter les ravines ;
- **un bruit orienté,** des crêtes alignées sur un champ de directions. Pas un étirement des coordonnées, qui cisaillerait là où la direction tourne : des cellules à orientation fixe mêlées entre voisines, l'idée des motifs de phase de Grenier 2024 et des pivots de runevision.

**Ce que la géologie module :**
- **Les chaînes jeunes :** un ridged de 8 à 12 octaves, aligné sur les plis, d'amplitude donnée par le profil de la chaîne ; des ravines sur les versants. La rugosité la plus forte.
- **Les chaînes anciennes :** le même bruit, octaves fines atténuées par l'âge, crêtes arrondies. Rugosité moyenne.
- **Les plateaux et les bassins sédimentaires :** des terrasses où la roche est litée et le climat sec, les badlands d'aujourd'hui à leur place géologique.
- **Les cratons :** billow doux, collines de socle.
- **Les arcs et les points chauds :** des cônes posés par cellule hachée le long de l'arc ou de la traînée, cratère au sommet, pente de 5 à 30° selon le type.
- **Le fond océanique :** des collines abyssales allongées parallèlement à la dorsale, d'autant plus enfouies sous les sédiments que la croûte est vieille.

**La rugosité `gRoughness` :** calculée des mêmes champs, continue : 0,1 sur les plaines, 0,3 sur les cratons, 0,5 sur les chaînes anciennes, 0,6 sur les terrasses, 1 sur les chaînes jeunes.

**Le filtrage :** chaque bande lit `gMaxFrequency`, comme aujourd'hui. Chaque profil analytique a une largeur d'au moins deux mailles, comme l'arrondi des crêtes : une fosse vue de 400 km n'est pas une fente d'un pixel.

### 6.5 Le lien avec l'érosion

**Ce que le niveau 0 attend en entrée, et ce qu'il reçoit enfin :**

| Entrée du niveau 0 | Aujourd'hui | Demain |
|---|---|---|
| Soulèvement U | proportionnel à complexplanet, plus un minimum, inversé vers ses hauteurs | celui des fronts convergents, nul sur les cratons, négatif dans les avant-pays et les rifts |
| Relief initial | complexplanet sans ses vallées | les grandes formes, `ReliefElevation(p, false)` |
| Érodabilité K | uniforme | selon la roche : forte sur les sédiments, faible sur le socle (Cordonnier 2018) |
| Niveau de base | la mer et les lacs terminaux | idem, la côte venant de la marge continentale |
| Pluie | décroissante vers l'intérieur | idem, puis l'ombre des chaînes, que la tectonique place enfin |

**Pourquoi c'est plus simple pour lui :**
- **Les chaînes sont là où le soulèvement les tient.** À l'équilibre, la hauteur d'une chaîne vient de U / K et de l'aire drainée ; le niveau 0 n'a plus à les copier. L'inversion du spike A3 peut rester, vers les hauteurs des profils, mais elle part d'un soulèvement déjà cohérent.
- **Les cuvettes ont une cause.** Les bassins d'avant-pays, les rifts et les intérieurs arides sont des cuvettes réelles ; le reste se draine vers la mer par construction.
- **Les bassins ont une taille terrestre.** Les chaînes côtières, les rifts et les sutures découpent les continents en plusieurs bassins ; le bassin géant du spike A2 venait d'un intérieur sans relief organisé.
- **Les fleuves contournent les massifs.** Les massifs sont ceux que l'érosion a laissés debout ; ils ne viennent plus d'un bruit que le tracé ignore.

**Le solveur, du moins cher au plus cher :**
1. **L'équilibre analytique** (Tzathas 2024) : Priority-Flood, aire drainée, puis l'intégrale χ le long du réseau, deux ou trois fois, car le réseau dépend du relief. Quelques secondes estimées.
2. **FastScape transitoire sur GPU** (Schott 2023), si l'équilibre manque de variété. Quelques secondes estimées pour un millier de pas.
3. **Un cache sur disque par graine,** en attendant le GPU, comme le bake actuel `x64\Erosion`.

**Ce qu'il rend, et comment le relief l'emploie :**
- **Le relief érodé** remplace les grandes formes au-dessus de deux de ses cellules, sur les terres ; lu en B-spline, par mips.
- **L'aire drainée et le niveau de l'eau** donnent le masque des vallées : le bruit des couches moyennes s'éteint sur le fond, que suit le profil du fleuve. Le fond a la largeur du lit, puis de la plaine, selon le débit (`recherche-dendry.md`).
- **La pente du niveau 0** oriente les ravines : elles descendent vers ses fleuves.
- **La moyenne reste juste :** la carte est calculée avec les octaves filtrées à deux texels et remplacées par leur moyenne. Le niveau 0 voit la hauteur moyenne du relief qu'il érode.

**Ce qui reste ouvert :** les vallées entre 20 km et 1 km. Le bruit orienté y creuse des vallées longitudinales, parallèles aux plis, qui peuvent se fermer. Deux réponses, dans l'ordre :
1. **Le masque et la pente vers le fleuve le plus proche,** dans la fonction elle-même : bon marché, à mesurer.
2. **Les niveaux fins de Dendry,** par tuiles autour de la caméra, accrochés aux fleuves du niveau 0 (`recherche-dendry.md`, section 6).

### 6.6 Ce qui reste du projet

- **L'interface :** `ReliefElevation(double3 p)` et `ReliefElevation(double3 p, bool valleys)`.
  - Avec `valleys`, le relief complet, niveau 0 compris.
  - Sans, la forme avant érosion, celle que lit le niveau 0. Elle ne lit jamais ses propres sorties.
- **`gRoughness` :** écrite à chaque appel, de 0 à 1, calculée des champs géologiques.
- **La double précision :** seulement pour la découpe des octaves sur la grille, comme aujourd'hui. Les lectures de carte se font en float : 0,4 m d'erreur de direction contre 10 km de texel.
- **Le filtrage par la maille :** `gMaxFrequency`, `gCreaseMaxFrequency`, `MapLevel` pour les mips des cartes.
- **La stabilité quand la maille glisse :** tout est ancré sur la planète ; aucun calcul ne dépend de l'ancre ni de la caméra.
- **Les ordres de grandeur :** environ 60 % de terres, sommets de 5 à 8 km, fosses à −8 km, dans `MAX_ELEV` = 8 192 m. La part de terres se règle à l'étape 1 du précalcul, la hauteur des sommets par les profils et le soulèvement.
- **Le portage CPU des bancs :** comme `tools/hydro/cp.py` pour le relief actuel, un portage numpy du précalcul et des profils, pour `banc_carte.py` et les planches.

### 6.7 Le coût par sommet, estimé

| Poste | Aujourd'hui | Demain, estimé |
|---|---|---|
| Lectures de carte | 0 | 2 cubes en B-spline, environ 8 lectures bilinéaires ; plus le niveau 0 |
| Profils analytiques | 0 | quelques dizaines d'opérations |
| Turbulences | 12, à 3 bruits chacune | un gauchissement de 2 octaves, 6 bruits |
| Octaves | environ 114 dans les générateurs, et des sous-graphes recalculés | 30 à 70 selon le terrain, dans des branches réelles |
| Total | environ 340 évaluations de bruit | 40 à 80, à mesurer |

### 6.8 Les règles nouvelles, pour `principes.md`

- **La géologie décide, le bruit détaille.** Toute forme de plus de 50 km vient de la carte tectonique ; aucun bruit n'a d'octave au-dessus.
- **Une carte précalculée peut porter la géométrie,** à trois conditions : ancrée sur la planète, lue en B-spline cubique et par mips, au-dessus de deux de ses texels seulement. Elle remplace la règle « de la donnée, jamais de la géométrie », que le niveau 0 enfreint déjà sur `erosion-niveaux`.
- **Une carte qui porte une forme ne se lit jamais en bilinéaire :** la pente y saute à chaque texel, et la lumière dessine la grille.
- **Tout profil analytique a une largeur d'au moins deux mailles.**
- **Rien de plus fin que le niveau 0 ne barre un de ses cours d'eau.**
- **Chaque profil suit une loi publiée,** citée avec sa source : profondeur océanique par l'âge, flexion de la lithosphère, largeur des plateaux.

## 7. Le plan par étapes

Chaque étape se juge en vol, avec un fichier `tools/tests/<date>.txt` et `tools/lance.ps1`, sur plusieurs graines et plusieurs lieux. Chacune est sur la piste `piste/relief-tectonique`, avec un réglage qui ramène au relief actuel ; le relief actuel reste le rendu sans variable jusqu'à la décision.

| Étape | Contenu | Ce qui se juge en vol | Mesure |
|---|---|---|---|
| 0 | Décider de la règle de la carte qui porte la géométrie ; écrire la spec | rien | la décision |
| 1 | Le précalcul tectonique et ses vues de diagnostic, `MYPLANETENGINE_VIEW` : plaques, type de frontière, âge, roche. Le relief ne change pas | depuis l'orbite, les plaques et leurs frontières sur la planète actuelle : formes, tailles, irrégularité | temps de démarrage ajouté ; tailles des plaques contre Bird 2003 |
| 2 | Les grandes formes seules, sur les briques actuelles pour le détail | depuis l'orbite et à 50 km : continents, plateaux, chaînes le long des fronts, fosses, dorsales, rifts | 60 % de terres ; hypsométrie bimodale ; sommets de 5 à 8 km ; fosses à −8 km |
| 3 | Le détail modulé : bruit orienté par les plis, âge, roche, `gRoughness` | de 10 km à 100 m : crêtes parallèles aux chaînes, chaînes vieilles arrondies, terrasses des bassins secs | banc de qualité : aucun p95 dégradé de plus de 10 % ; banc de descente plat |
| 4 | Le niveau 0 sur le soulèvement tectonique, à l'équilibre analytique ; son relief érodé au-dessus de deux cellules ; le masque des vallées | aux sources des fleuves, là où ils traversaient les montagnes : ils les contournent ; bassins et lacs | `level0_cut.py` : part des fleuves creusée à plus de 50 m sous le sol, contre 44 % ; tailles des bassins contre la Terre ; corrélation des massifs avec la couche 2 |
| 5 | Les arcs, les points chauds, les failles transformantes, les collines abyssales | les chapelets d'îles, les volcans, le fond océanique vu en basse altitude | nombre et espacement des volcans d'arc |
| 6 | Les côtes par type de marge : plateaux larges et plages sur les marges passives, côtes raides et falaises sur les actives | le long de plusieurs côtes de chaque type | parts de côte de `recherche-cotes.md`, étape 3 |
| 7 | Les vallées fines : Dendry par tuiles, accroché au niveau 0 | en montagne à 2 km : affluents en arbre, sans cuvettes | lacs de moins de 1 % des terres à 300 m ; banc de tremblement |
| 8, si besoin | Une histoire simulée à la Cortial, si l'instantané paraît trop régulier | des continents assemblés de terranes, des sutures multiples | — |

**L'étape 2 est le premier vrai jugement.** Elle montre à elle seule si la planète a une géologie lisible de l'orbite. Les étapes 1 et 2 ne touchent ni au niveau 0 ni aux matériaux.

## 8. Risques et questions

- **La décision de la règle de la carte,** étape 0, prise le 2026-10-31 (`principes.md`). Sans elle, le niveau 0 ne pouvait pas porter le relief au-dessus de 20 km, et l'architecture perdait sa couche 4.
- **Le démarrage s'allonge :** quelques secondes pour les plaques, quelques secondes pour le niveau 0 sur GPU, peut-être une minute sur CPU. Un cache par graine borne le pire cas.
- **Les lectures en B-spline aux arêtes du cube :** les lectures décalées traversent les faces ; à vérifier aux coins, où trois faces se rencontrent.
- **Le bruit orienté :** là où la direction des plis tourne vite, aux coudes des chaînes, le mélange des cellules peut brouiller les crêtes.
- **L'instantané cinématique manque d'histoire :** des chaînes toutes jeunes, des continents sans terranes. Les sutures synthétisées de l'étape 1 sont la parade ; la simulation pas à pas, l'étape 8, le recours.
- **Le niveau 0 à 20 km :** il ne voit pas les vallées entre 20 et 1 km. La question ouverte de la section 6.5.
- **Le post Reddit :** non lu. Il peut changer une recommandation s'il apporte une méthode absente d'ici.

## 9. Sources

**Le post et les projets récents**
- Le post signalé : https://www.reddit.com/r/proceduralgeneration/comments/1xhximl/procedural_plate_tectonics_simulation_for_a/ (non lu, accès refusé).
- World Orogen : https://github.com/raguilar011095/planet_heightmap_generation ; https://orogen.studio/
- Frozen Fractal, « Around The World, Part 29: One year in », 2026 : https://frozenfractal.com/blog/2026/2/14/around-the-world-29-one-year-in/
- DasTobi, « Plate Tectonics Simulation, Oceans and Mountains », 2026 : https://www.youtube.com/watch?v=cP-5czRuTII

**La tectonique procédurale**
- Cortial, Peytavie, Galin, Guérin, *Procedural Tectonic Planets*, CGF 38(2), 2019 : https://perso.liris.cnrs.fr/eric.galin/Articles/2019-planets.pdf ; https://onlinelibrary.wiley.com/doi/abs/10.1111/cgf.13614
- Gainey, *Procedural Planet Generation*, Experilous, 2014 : https://www.experilous.com/1/blog/post/procedural-planet-generation (hors ligne le 2026-10-31).
- Red Blob Games, *1843-planet-generation* : https://github.com/redblobgames/1843-planet-generation
- PlaTec : https://github.com/Mindwerks/plate-tectonics ; WorldEngine : https://github.com/Mindwerks/worldengine
- tectonics.js : https://github.com/davidson16807/tectonics.js ; SimpleTectonics : https://github.com/weigert/SimpleTectonics ; https://github.com/FreezeDriedMangos/realistic-planet-generation-and-simulation
- Michel, Emilien, Cani, *Generation of Folded Terrains from Simple Vector Maps*, Eurographics short 2015 : https://diglib7.eg.org/bitstream/handle/10.2312/egsh.20151019.077-080/077-080.pdf

**Le soulèvement et l'érosion**
- Cordonnier et al., *Large Scale Terrain Generation from Tectonic Uplift and Fluvial Erosion*, CGF 35(2), 2016 : https://hal.archives-ouvertes.fr/hal-01262376 ; https://www.cs.purdue.edu/homes/bbenes/papers/Cordonier16CGF.pdf
- Cordonnier et al., *Sculpting Mountains: Interactive Terrain Modeling Based on Subsurface Geology*, TVCG 2018 : https://www.cs.purdue.edu/homes/bbenes/papers/Cordonnier18TVCG.pdf
- Schott et al., *Large-scale Terrain Authoring Through Interactive Erosion Simulation*, ACM TOG 42, 2023 : https://hal.science/hal-04049125v1 ; https://github.com/H-Schott/StreamPowerErosion
- Schott et al., *Terrain Amplification using Multi-scale Erosion*, ACM TOG 43(4), 2024 : https://h-schott.github.io/publications/mserosion/publi_mserosion.html ; https://github.com/H-Schott/MultiScaleErosion
- Tzathas, Gailleton, Steer, Cordonnier, *Physically-based Analytical Erosion for fast Terrain Generation*, CGF 43(2), 2024 : https://diglib.eg.org/handle/10.1111/cgf15033
- fastscapelib : https://github.com/fastscape-lem/fastscapelib ; fastscape : https://github.com/fastscape-lem/fastscape
- Astrolith, *Real-time planet scale erosion* : https://gamedev.net/blogs/entry/2275217-real-time-planet-scale-erosion

**L'hydrologie et l'amplification**
- Génevaux et al., *Terrain Generation Using Procedural Models Based on Hydrology*, ACM TOG 32(4), 2013 : https://www.cs.purdue.edu/homes/bbenes/papers/Genevaux13ToG.pdf ; https://hal.archives-ouvertes.fr/hal-01339224
- Derzapf et al., *River Networks for Instant Procedural Planets*, CGF 30(7), 2011 : https://diglib.eg.org/handle/10.1111/v30i7pp2031-2040
- Gaillard et al., *Dendry: A Procedural Model for Dendritic Patterns*, I3D 2019 : https://www.cs.purdue.edu/cgvlab/www/resources/papers/Gaillard-2019-Dendry_A_Procedural_Model_for_Dendritic_Patterns.pdf ; code GPL-3.0 : https://github.com/mgaillard/Noise
- Guérin, Digne, Galin, Peytavie, *Sparse Representation of Terrains for Procedural Modeling*, CGF 35(2), 2016 : https://diglib.eg.org/handle/10.1111/cgf12821 ; https://github.com/eric-guerin/terrain-amplification
- Galin et al., *A Review of Digital Terrain Modeling*, CGF 38(2), 2019 : https://www.cs.purdue.edu/homes/bbenes/papers/Galin19CGF.pdf
- Grenier, Guérin, Galin, Sauvage, *Real-time Terrain Enhancement with Controlled Procedural Patterns*, CGF 43(1), 2024 : https://diglib.eg.org/handle/10.1111/cgf14992
- Argudo et al., *Terrain descriptors for landscape synthesis, analysis and simulation*, Eurographics 2025 : https://hal.science/hal-05246144/document ; https://github.com/oargudo/terrain-descriptors
- Borg et al., *Authoring Terrestrial Planets with Diffusion Models*, CGF 45(2), 2026 : https://diglib.eg.org/handle/10.1111/cgf70390
- *Terrain Diffusion*, arXiv 2025 : https://arxiv.org/abs/2512.08309

**Les bruits érodés**
- Quilez, articles sur le bruit et ses dérivées : https://iquilezles.org/ ; le changement de licence de 2021 : https://github.com/huwb/volsample/issues/1
- Johansen, *Fast and Gorgeous Erosion Filter*, 2026 : https://blog.runevision.com/2026/03/ ; https://www.shadertoy.com/view/wXcfWn ; https://gist.github.com/runevision

**Les jeux**
- McKendrick, *Continuous World Generation in No Man's Sky*, GDC 2017 : https://gdcvault.com/play/1024265/Continuous-World-Generation-in-No
- Murray, *Building Worlds Using Math(s)*, GDC 2017 : https://gdcvault.com/play/1024514/Building-Worlds-Using
- *Generating the Universe in Elite: Dangerous*, 80.lv : https://80.lv/articles/generating-the-universe-in-elite-dangerous/
- Star Citizen, Planet Tech v5 : https://starcitizen.tools/Planet_Tech_v5 ; https://theimpound.com/pages/star-citizen-starchitect-planet-tech-v5
- SpaceEngine, *First procedural terrain* : https://spaceengine.org/news/blog100531/

**La géophysique des profils** (lois publiées, sans code)
- Parsons, Sclater, *An analysis of the variation of ocean floor bathymetry and heat flow with age*, JGR 82, 1977, doi:10.1029/JB082i005p00803.
- Stein, Stein, *A model for the global variation in oceanic depth and heat flow with lithospheric age*, Nature 359, 1992, doi:10.1038/359123a0.
- Bird, *An updated digital model of plate boundaries*, G³ 4(3), 2003, doi:10.1029/2001GC000252.
- Turcotte, Schubert, *Geodynamics*, la flexion de la lithosphère : bourrelet externe et bassins d'avant-pays.
- Perron, Royden, *An integral approach to bedrock river profile analysis*, 2013 : https://dspace.mit.edu/handle/1721.1/75359
- Braun, Willett, *A very efficient O(n), implicit and parallel method to solve the stream power equation*, Geomorphology 180, 2013.
- Barnes, Lehman, Mulla, *Priority-Flood*, 2014.
