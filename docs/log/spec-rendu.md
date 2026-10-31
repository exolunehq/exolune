# Spécification : rendu, matériaux et atmosphère

Statut : validé, procédural, dans l'ordre proposé. Étapes A, B et C faites, étape C bis arrêtée, lissage temporel gardé. Étape D spécifiée le 2026-10-21. Fait suite à `spec-stabilite.md`.

## Les objectifs

1. **Des matériaux plus détaillés que le maillage.** De loin, les détails sont visibles avant que la géométrie s'affine : pas d'effet de mutation.
2. **Des textures de détail de surface.**
3. **Des détails à la surface,** en shaders ou en objets procéduraux pilotés par les bruits.

**Partout, une texture va de pair avec ses normales.** La couleur seule reste plate : c'est la normale qui fait lire le relief dans la lumière.
4. **Une atmosphère, le ciel et le soleil.**
5. **La perspective aérienne**, pour améliorer le rendu lointain.

## Le principe commun

**Tout ce qui est nouveau est calculé pixel par pixel, en coordonnées fixes de la planète.** C'est la méthode du grain fin, qui a fait ses preuves au banc de tremblement.

- **Rien ne dépend de la position des sommets :** pas de tremblement, et pas de changement quand le maillage s'affine.
- **Ancrage :** le réseau de 64 m proche de la caméra, déjà en place. Les indices des bruits restent exacts à l'échelle de la planète.
- **Filtrage :** chaque octave s'efface sous 2 pixels, et ne scintille donc pas.
- **Procédural, aucune image chargée,** dans l'esprit du concept. C'est un choix à valider, voir la fin.
- **Mesures à chaque étape :** coût GPU sur les dix vues de référence, banc de tremblement, images avant et après.
- **Budget :** environ 3 ms pour tout le rendu, en 1280 × 720. Le calcul du terrain reste sous 2 ms.

## Étape A : l'image en haute dynamique

**Prérequis du ciel et du soleil :** leur dynamique ne tient pas dans une image 8 bits.

- **Rendu dans une image en virgule flottante,** 16 bits par canal, en lumière linéaire.
- **Puis passage à l'écran :** compression des hautes lumières, puis sortie sRGB par le matériel.
- **Compression neutre de Khronos :** identité sous 0,76, puis un fondu vers le blanc qui garde les teintes.
- **Les couleurs actuelles sont reprises telles quelles,** pour que l'étape ne change que la chaîne d'image.

**Résultat :** image identique à ±1 niveau près sur quatre vues. Rendu +0,01 ms.

## Étape B : atmosphère, ciel et soleil

**Méthode : Hillaire 2020** (Eurographics, celle d'Unreal). Diffusion de Rayleigh et de Mie, absorption par l'ozone, diffusion multiple approchée. Elle vaut du sol jusqu'à l'espace.

### Trois petites tables, calculées au démarrage

Elles ne dépendent que des réglages de l'atmosphère, ni de la caméra ni du soleil : les recalculer à chaque image ne servirait à rien.

- **Transmittance,** 256 × 64 : ce que l'atmosphère laisse passer, selon l'altitude et la direction.
- **Diffusion multiple,** 32 × 32 : la lumière qui a rebondi plusieurs fois, selon l'altitude et la hauteur du soleil.
- **Éclairement du ciel,** 64 × 16 : la lumière que tout le ciel envoie sur un sol horizontal. Elle éclaire les ombres.

### Le reste est calculé pixel par pixel

**Plus simple que les deux tables liées à la caméra de la méthode d'origine,** et plus juste. À mesurer : si c'est trop cher, ces tables reviennent.

- **Le ciel :** un rayon par pixel traverse l'atmosphère, en 32 pas. Le disque du soleil s'y ajoute.
- **Le terrain :**
  - il reçoit le soleil filtré par l'atmosphère, d'où les couchers rouges, plus l'éclairement du ciel ;
  - la perspective aérienne voile ensuite sa couleur selon la distance, par le même rayon, de la caméra au sol.
- **Vue d'orbite :** le rayon entre dans l'atmosphère par le haut. Le limbe bleu apparaît de lui-même.
- **Éclairage linéaire :** les couleurs du terrain deviennent des réflectances, éclairées en lumière linéaire.

### Réglages et essais

- **Réglages de la Terre** dans `PlanetSettings.hlsli`, atmosphère de 100 km d'épaisseur.
- **Touches O et P :** le soleil tourne autour de l'axe de la planète, pour voir les couchers.
- **`MYPLANETENGINE_SUN=latitude longitude`** place le soleil au démarrage, pour les captures.
- **Coût visé :** moins de 0,5 ms.

### Résultats

**L'atmosphère coûte 0,15 ms au pire des dix vues de référence :** rendu de 0,11 à 0,26 ms.

- **La perspective aérienne est appliquée dans la passe finale, une fois par pixel.** Le terrain lui transmet sa distance par le canal alpha.
  - Calculée dans le shader du terrain, elle coûtait 0,65 ms en montagne : chaque fragment caché par un relief plus proche la payait aussi.
  - L'image est la même à ±2 niveaux près.
- **Ciel, soleil, couchers et limbe** visibles sur les captures du journal.
- **Tremblement :** légèrement plus bas, de 0,22 à 0,14 sur la plaine à 50 m. Le voile de l'air adoucit les contrastes.
- **Défaut corrigé :** soleil au zénith, la table d'éclairement du ciel contenait des NaN, d'où un océan noir vu d'orbite.
- **Limites :**
  - exposition fixe, la scène est sombre au coucher ;
  - pas encore de reflet du soleil sur l'océan ;
  - de très haut, le voile bleu domine sur les terres sombres. C'est physique, mais les matériaux de l'étape C, plus clairs et plus variés, le rééquilibreront.

## Étape C : les matériaux par pixel

**Le problème : la couleur vient de l'altitude et de la pente interpolées entre les sommets.**

- **De loin,** les frontières de couleur suivent le maillage grossier. Quand il s'affine, elles changent de forme : c'est la mutation.
- **En montagne,** la couleur roche ou neige tremble, mesuré au banc.

**Le principe : chaque pixel pondère ses matériaux,** mer, sable, herbe, roche, neige et sol aride. Chaque matériau apporte sa couleur et sa normale.

- **L'altitude et la pente des sommets ne donnent que de larges transitions.**
- **Le tracé fin des frontières vient d'un bruit par pixel,** fixe sur la planète, à toutes les échelles visibles.
- **Une entrée stable en plus :** le type de terrain de complexplanet, plaines, collines, montagnes ou badlands, exporté par le compute shader. Ses octaves sont déjà limitées à ~100 km, il ne tremble pas.
- **Un climat simple, fait de quelques bruits :** aujourd'hui la couleur suit l'altitude, de façon uniforme, avec des frontières nettes. Ce n'est pas réaliste.
  - **Température :** latitude et altitude, plus un bruit régional de quelques centaines de kilomètres.
  - **Humidité :** un bruit régional, plus un bruit plus large de l'ordre de 1 000 km.
  - **Ensemble, ils choisissent le biome :** désert, steppe, prairie, forêt, toundra, neige. Toujours par fondus larges, jamais par seuils nets.
  - **Variations macro et micro :** des bruits de teinte à toutes les échelles, du continent au mètre, pour que deux prairies voisines ne soient jamais identiques.
- **Aucune frontière n'est une ligne, à aucune échelle.** Aujourd'hui, la neige s'arrête net sur une chaîne de montagnes.
  - **La limite des neiges se défait :** névés isolés en dessous, roche qui perce au-dessus, langues de neige dans les couloirs. Son altitude varie avec un bruit à plusieurs échelles, de la vallée au mètre.
  - **Le relief la module :** la neige tient dans les creux et sur les versants à l'ombre, glisse des pentes raides où la roche affleure.
  - **Même principe pour les autres frontières :** plage, prairie et roche, forêt et alpage.
  - **Le tracé fin est calculé dans les pixels :** il reste net et stable de près comme de loin, sans dépendre du maillage.
- **La pente utilisée est celle du pixel,** normale des sommets plus grain fin.

- **Les normales des matériaux prolongent le relief au-delà du maillage :** strates et éboulis pour la roche, surface lisse pour la neige, rides pour le sable. Elles remplacent le grain fin générique, qui ne savait pas faire les arêtes de montagne.

**Résultat attendu :** une montagne lointaine montre déjà ses névés, ses arêtes et ses éboulis, dans la couleur comme dans la lumière, avant que sa géométrie s'affine.

**Limite :** le relief réel apparaît quand le maillage s'affine. Les frontières bougent alors un peu, mais seulement dans leurs larges transitions.

### Conception

**Tout tient dans le pixel shader du terrain.** Les bruits utilisent l'ancre de 64 m du grain fin : indices exacts sur toute la planète, stables, filtrés sous 2 pixels.

- **Deux familles de bruits, trois canaux chacune pour le prix d'une :**
  - **régionale,** de 3 000 à 200 km : écart de température, humidité, humidité large ;
  - **locale,** de 8 km jusqu'au pixel : taches de neige, affleurements de roche, variation de teinte.
- **Température en °C :**
  - 27 °C à l'équateur, −25 °C aux pôles ;
  - −6,5 °C par km d'altitude ;
  - ±6 °C de bruit régional ;
  - ±5 °C de bruit local, qui découpe la limite des neiges en névés et en langues ;
  - −3 °C sur les versants tournés vers le pôle.
- **Humidité de 0 à 1 :** bruits régionaux, plus une bande sèche vers 25° de latitude, celle des grands déserts.
- **Végétation :** désert, steppe, prairie, forêt selon l'humidité ; toundra quand il fait froid. Fondus larges.
- **Roche :** sur les pentes raides, avec un seuil de pente perturbé par le bruit local.
- **Neige :** sous 0 °C, chassée des pentes trop raides.
- **Plage :** près du niveau de la mer, avec une largeur variable.
- **Teinte :** ±15 % de luminosité et une légère dérive de couleur, à toutes les échelles.
- **Normales par matériau :** le grain fin est renforcé sur la roche et adouci sur la neige et le sable.
- **Pas encore :** le type de terrain exporté par le compute shader. Le climat et la pente suffisent à un premier essai ; il viendra si les montagnes manquent de caractère.

**Validation :** images avant et après sur les vues de référence, banc de tremblement, coût du rendu. Les couleurs sont un choix de goût : c'est toi qui tranches sur les images.

### Résultats, premier essai

- **En montagne :** neige sur les sommets, limite découpée en névés et en langues, roche qui affleure sur les pentes, vallées vertes.
- **Régions :** steppes et déserts autour de 25° de latitude, prairies et forêts ailleurs, teinte qui varie à toutes les échelles.
- **Tremblement :** pas de hausse, et divisé par deux en montagne à 50 m, de 0,44 à 0,21 sur toute l'image.
- **Coût :** rendu de 0,26 à 0,78 ms au pire. Les matériaux sont calculés pour chaque fragment, y compris ceux qu'un relief plus proche cache ensuite. Une passe de profondeur préalable supprimerait ce gaspillage, si le budget l'exige.
- **Réglages :** palette et climat dans `GroundAt`, `PixelShader.hlsl`. Les couleurs sont des réflectances linéaires : forêt 8 %, prairie 15 %, désert 35 %, neige 85 %.
- **Corrigé en route :**
  - couleurs d'abord écrites comme des valeurs d'écran, deux fois trop sombres ;
  - bruit de température trop fort, qui mettait de la neige sous les tropiques.
- **Ce n'était pas un bug :** une vue toute noire était simplement de nuit. Les captures placent maintenant le soleil dans l'après-midi de chaque vue.

## Étape C bis : le vrai relief dans les pixels

**Le but : que le rendu montre le vrai relief de complexplanet avant que la géométrie s'affine.** Couleur et normales viennent de la même source de vérité que les élévations, à la résolution de l'écran. Le grain générique et le climat seul n'en sont qu'un habillage.

**Le concept reste intact :** tout est recalculé à chaque image, sans mémoire ni rattrapage, pour un coût fixe.

### Le principe : partager le graphe entre sommets et pixels

- **Les sommets évaluent les parties lentes du graphe :** continents, type de terrain, turbulences, facteurs d'échelle. Elles varient peu d'un sommet à l'autre, leur valeur interpolée est juste.
- **Les pixels réévaluent les fractales qui portent le relief fin,** avec les mêmes fonctions, les mêmes graines et les mêmes fréquences. Leurs octaves sont filtrées à 2 pixels au lieu de 2 mailles.
- **Le pixel en déduit un écart d'élévation :** sa propre valeur moins la valeur interpolée des sommets. C'est exactement ce que la géométrie ne montre pas encore.
- **La normale vient de la surface corrigée,** la position du pixel élevée de cet écart. Les arêtes de la géométrie disparaissent sous le vrai relief.
- **La couleur utilise l'élévation et la pente corrigées.**

### Le prototype : les montagnes

**C'est là que l'écart se voit le plus :** les arêtes des montagnes ont des longueurs d'onde de 0,6 à 4 km, plus fines que les mailles vues de 10 km d'altitude.

- **Réévalués par pixel :** les cinq fractales ridged des montagnes, la base, les hautes crêtes et les basses montagnes, soit environ 27 évaluations de bruit au plus.
- **Interpolés depuis les sommets :** les deux déformations des montagnes, le facteur d'échelle, la part des montagnes dans le terrain.
- **Seulement là où il y a des montagnes,** et seulement là où les mailles dépassent 8 m. Plus près, les sommets montrent déjà tout le relief, jusqu'à son octave la plus fine de 22 m.
- **Le grain générique s'efface en montagne.**
- **Compilation :** les shaders du terrain passent au shader model 6, comme le compute shader, pour partager le code du bruit.

### Limites attendues

- **Les déformations restent interpolées :** leurs octaves plus fines que la maille manquent aux pixels. Il en reste une mutation résiduelle, faible.
- **La normale vient des dérivées entre pixels voisins,** calculées par blocs de 2 × 2 pixels.

### Validation

- Images avant et après en montagne à 10 km et à 50 m.
- Mutation : comparaison des pixels avec la géométrie fine, en rapprochant la caméra.
- Banc de tremblement, et coût du rendu.

### Résultats du prototype

**Le vrai relief apparaît bien :** vues de 10 km, les montagnes montrent leurs arêtes, la neige se pose sur les replats, la roche reste nue sur les crêtes.

- **Normale :** la différence entre deux évaluations du pixel, l'une filtrée à 2 pixels, l'autre à 8 mailles, plie la normale lisse des sommets. Une première version, qui dérivait la surface corrigée entre pixels voisins, laissait voir les arêtes des triangles.
- **Mutation,** mesurée en comparant l'image à celle d'un maillage 8 fois plus fin, après un flou de 8 pixels : de 1,91 à 1,36 à 10 km, de 2,76 à 1,95 à 3 km. Au pixel près, elle augmente : le détail fin ne tombe jamais exactement sur les mêmes pixels.
- **Coût :** rendu de 0,73 à 0,96 ms en montagne à 10 km, 1,49 ms au pire à 50 m.

**Mais le tremblement augmente fortement en montagne vue de haut :**

| Tremblement, image entière | Étape C | Prototype |
|---|---|---|
| Montagne, 50 m | 0,21 | 0,25 |
| Montagne, 10 km, horizon | 3,39 | 7,99 |
| Montagne, 10 km, vers le bas | 4,30 | 7,71 |

**La cause, établie par élimination, couleurs remplacées par un gris :**

- de 1,5 sans le relief à 4,7 avec ;
- inchangé avec les déformations calculées dans le pixel, une coupure fixe, une taille de pixel stable, des dérivées projetées sur la surface lisse ;
- 3,3 en limitant le relief aux octaves de plus de 2 mailles.

**C'est la parallaxe.** Le pixel évalue le relief au point où son rayon touche le maillage grossier, pas le vrai relief. Ce maillage glisse : le point évalué glisse avec lui le long du rayon. En vue rasante, quelques dizaines de mètres d'écart de hauteur deviennent des centaines de mètres le long du sol. Plus le relief est contrasté, plus ce glissement se voit. Le grain générique de l'étape C, dix fois moins contrasté, le cachait.

### Pistes

1. **Corriger la parallaxe :** avancer le point évalué le long du rayon de l'écart de hauteur, puis réévaluer, une ou deux fois. Coût du relief multiplié par 2 à 3. Réduit l'erreur, sans l'annuler aux angles les plus rasants.
2. **Lisser dans le temps (TAA) :** la méthode standard des moteurs contre ce scintillement. Le terrain est fixe sur la planète : la reprojection d'une image à l'autre est exacte. Léger flou, coût faible.
3. **Garder le prototype pour la couleur seule,** sans plier la normale : moins de gain visuel.

### Piste 1 : la correction de parallaxe

- **Le pixel estime l'écart de hauteur** entre le vrai relief et le maillage, là où son rayon touche le maillage : sa propre valeur des montagnes moins celle des sommets.
- **Il avance le long de son rayon** jusqu'à la hauteur du vrai relief, en supposant le relief localement plat. L'avancée est bornée aux angles rasants.
- **Il évalue le relief, le climat et le grain à ce nouveau point,** au lieu du point du maillage.
- **Une seule itération d'abord,** puis deux si la mesure le justifie. Chaque itération coûte une évaluation des montagnes de plus.

**Résultat : écartée.** Le tremblement empire, de 8,0 à 9,7 en montagne à 10 km, et le rendu passe à 2,3 ms. L'écart de hauteur qui sert à avancer le long du rayon dépend lui-même des sommets interpolés, qui glissent : la correction glisse avec eux.

### Piste 2 : le lissage temporel (TAA)

- **Chaque pixel mélange sa couleur avec celle qu'il avait à l'image précédente,** à 10 % pour la nouvelle.
- **Reprojection exacte :** le terrain est fixe sur la planète. La position du pixel, sa distance et sa direction, est ramenée dans la caméra de l'image précédente, en double précision sur le processeur. Le ciel, à l'infini, suit seulement la rotation.
- **Contre les traînées :** la couleur passée est bornée par les couleurs de l'image courante autour du pixel, sur 3 × 3 pixels.
- **Deux passes :** l'atmosphère écrit l'image composée, puis la passe finale la lisse et compresse les hautes lumières.
- **Pas de décalage du sous-pixel** pour l'instant : le but est la stabilité, pas l'anticrénelage.
- **Touche T** pour le désactiver, et comparer.

**Résultat : le tremblement tombe sous celui de l'étape C.**

| Tremblement, image entière | Étape C | Prototype seul | Prototype et lissage |
|---|---|---|---|
| Montagne, 50 m | 0,21 | 0,25 | 0,07 |
| Montagne, 10 km, horizon | 3,39 | 7,99 | 0,95 |
| Montagne, 10 km, vers le bas | 4,30 | 7,71 | 1,18 |

- **Image immobile identique** à ±1 niveau près : sans mouvement, le lissage converge vers la même image.
- **Coût du lissage :** dans le bruit de mesure. Le rendu culmine à 1,6 ms en montagne à 50 m, à cause du relief par pixel.
- **À vérifier en vol :** les traînées derrière les reliefs en mouvement rapide. Le banc ne bouge pas la caméra.

### Correction après essai en vol : fausses crêtes

**Constat :** en s'approchant d'une montagne, des crêtes dessinées par la normale disparaissaient : elles n'existaient pas dans le vrai relief.

- **Cause :** les octaves entre 2 et 8 mailles étaient comptées deux fois, dans la normale lisse des sommets et dans le relief des pixels. La pente était exagérée de loin.
- **Correction :** les sommets calculent aussi une normale sans la part des montagnes. Le pixel y ajoute toute la pente des montagnes, qu'il évalue lui-même jusqu'à 2 pixels. Plus de double comptage, et une seule évaluation par pixel au lieu de deux.
- **Mutation,** après un flou de 8 pixels : de 2,11 à 1,36 à 10 km, de 2,70 à 1,95 à 3 km, de 1,80 à 1,47 à 2 km.
- **Tremblement avec lissage :** 0,18 à 50 m, 0,99 à 10 km. Rendu de 0,8 à 1,5 ms.

### Corrections suivantes, de près

- **Bruit poivre et sel à quelques centaines de mètres :** la direction du pixel n'était précise qu'à 0,6 m, et la pente divisait cette erreur par des pixels d'un mètre. Le point est maintenant un décalage depuis le nadir, en double, comme dans le compute shader.
- **Essai écarté : la double précision réservée aux octaves fines.** Elle cassait la géométrie au ras du sol : un point en float n'est précis qu'à 20 cm sur la planète, et les mailles y font 1,6 cm. La précision se juge à la maille, pas à la longueur d'onde. Double précision dans le pixel sous 4 m de pixel, comme les sommets sous 4 m de maille.
- **Facettes sur les montagnes lointaines :** les turbulences, interpolées entre sommets, changeaient de pente à chaque triangle. Elles sont recalculées dans le pixel, filtrées comme aux sommets. Rendu jusqu'à 2,8 ms en montagne à 50 m.
- **Taille du pixel au sol** tirée de la distance et de l'angle de vue, et dérivées fines : plus de sauts d'un triangle à l'autre, plus de blocs de 2 × 2.

### Conclusion : étape C bis arrêtée

**Le constat en vol qui tranche :** de près, la géométrie montre un relief riche, en volume ; de loin, il ne reste que les crêtes ridged, isolées et étranges.

- **Cause de fond :** le pixel ne réévaluait que la branche des montagnes. Les collines, les basses montagnes, les octaves fines des turbulences n'existaient qu'en géométrie.
- **Pour être fidèle, il faudrait tout le graphe par pixel :** 8 à 33 ms. Et la précision exige la double précision dans le pixel, mesurée à 11 ms de rendu quand on l'étend jusqu'aux pixels de 16 m.
- **La leçon :** le coût est dans l'évaluation du bruit, pas dans le nombre de sommets. Un échantillon de texture coûte autant qu'un sommet. Afficher une texture plus fine que le maillage n'a donc d'intérêt que si le nombre de sommets bloque, ce qui n'est pas le cas ici. Densifier le maillage donne le même détail, et en plus de vraies silhouettes.
- **Ce qu'on garde :** le lissage temporel, indépendant du relief par pixel.
- **Retour au rendu de l'étape C,** climat et grain générique. Le code du prototype n'est pas versionné ; la démarche et les mesures sont ici.

### Limite constatée en vol : les silhouettes

**Vu de loin, le relief des pixels est plus détaillé que les contours du maillage.** Les crêtes très marquées à l'intérieur font ressortir des silhouettes restées polygonales. C'est la limite connue de tout relief dessiné par la normale.
- **Le banc mesure un écart d'une image à l'autre :** le lissage le réduit par construction. Le jugement en vol reste nécessaire.

## Essai : la densité du maillage

**La finesse a une seule source de vérité :** `FaceCells`, le nombre de mailles par côté du plan central. La croissance des anneaux en découle, 1 + 2/FaceCells : une maille couvre toujours environ 2/FaceCells de sa distance au nadir, donc la même taille à l'écran, quelle que soit la taille du plan. Le facteur de taille du plan, touches K et L, ne règle que l'étendue du plan central.

| Mailles par côté | Maille à l'écran | Calcul, pire cas | Calcul, montagne 50 m | Tremblement, montagne 10 km, avec lissage |
|---|---|---|---|---|
| 128 | ~11 px | 1,8 ms | 1,0 ms | 0,62 |
| 160 | ~9 px | 2,8 ms | 1,2 ms | 0,53 |
| 192 | ~7 px | 3,9 ms | 1,8 ms | 0,46 |

- **Le coût suit le nombre de sommets,** comme prévu : ×1,6 et ×2,2.
- **Le gain visuel est réel mais modeste** sur les captures : la normale des sommets lisse sur 2 mailles, le relief reste doux.
- **Le lissage temporel seul** fait passer le tremblement de l'étape C de 3,39 à 0,62 en montagne à 10 km, à 128 mailles.
- **Retenu : 192 mailles,** jugé nettement mieux en vol.

## Étape D : textures de détail, couleur et normales

### Le constat

**De près, le sol est lisse : on perd l'échelle.**

- **Le relief s'arrête à 13,5 m :** c'est l'octave la plus fine de complexplanet sur terre. Le maillage n'a rien de plus fin à montrer.
- **Le grain fin de l'éclairage s'éteint vers 7 m,** à la moitié de cette octave.
- **La couleur varie jusqu'au mètre,** par le bruit local de l'étape C, mais sans normale : elle reste plate.
- **En dessous, rien :** ni touffe, ni caillou, ni ride. À 2 m du sol, rien ne dit si l'on voit 1 m ou 100 m.

### Le but

**Chaque matériau a sa texture de près, couleur et normale ensemble,** de 8 m jusqu'au pixel, soit le millimètre au ras du sol.

- **Elle prend le relais du grain fin sans rupture :** le grain générique garde les longueurs d'onde au-dessus de 8 m, les textures de matériaux celles d'en dessous.
- **Elle ne double rien :** complexplanet n'a aucune longueur d'onde sous 13,5 m, le maillage non plus.
- **Elle est calculée pixel par pixel,** ancrée sur la planète et filtrée sous 2 pixels, comme le grain fin : stable par construction, recalculée à chaque image, sans mémoire.

### Les matériaux

| Matériau | Couleur | Normale et relief |
|---|---|---|
| Herbe, steppe, prairie | Plaques de teintes vertes et sèches de 1 à 3 m ; touffes plus sombres à leur pied | Touffes de 20 à 40 cm, bosselage fin de quelques centimètres |
| Roche | Veines et taches de lichen ; fissures sombres | Strates suivant une direction qui varie lentement ; fissures en réseau de 20 cm à 2 m ; rugosité jusqu'au pixel |
| Sable de plage et de désert | Variations claires et sombres des rides ; grains | Rides de 10 à 20 cm dans une direction de vent qui varie lentement |
| Neige | Presque uniforme, légèrement bleutée dans les creux | Ondulations de vent, les sastrugi, de 0,5 à 2 m, faibles ; surface lisse au-dessous |
| Sol aride, toundra | Graviers clairs et sombres ; mousses en toundra | Craquelures en réseau de 10 à 30 cm ; cailloux de 2 à 10 cm |

- **La mer reste lisse.** Les vagues relèvent d'un autre chantier.
- **Les forêts restent une couleur** à cette étape : leurs arbres viendront avec les objets de l'étape E.

### Le principe

#### Une fonction par matériau

**Chaque matériau donne, au point de la planète du pixel, trois valeurs :**

- **un facteur de couleur,** de moyenne 1 ;
- **une pente,** dans le plan du sol, qui incline la normale ;
- **une hauteur,** sans unité, qui sert au mélange.

#### La moyenne est préservée

**De loin, chaque texture s'efface vers sa moyenne :** le facteur de couleur tend vers 1, la pente vers 0.

- **La couleur de loin ne change donc pas :** celle de l'étape C reste valable à toute distance.
- **Pas de mutation à l'approche :** la texture apparaît par octaves fines, sans décaler la teinte d'ensemble.
- **Les creux assombris** par la hauteur, pour lire le relief à l'échelle du centimètre, sont compensés pour garder la même moyenne.

#### Le mélange par la hauteur

**Aux frontières, le matériau le plus haut l'emporte,** sur une bande de transition étroite.

- **La neige s'accumule dans les creux,** la roche affleure sur les bosses, l'herbe pousse entre les cailloux.
- **Les poids de l'étape C restent la base :** la hauteur de chaque texture ne fait que déplacer la frontière à petite échelle.

#### Des bruits partagés

**Le coût vient du nombre d'octaves,** jusqu'à onze entre 8 m et le millimètre au ras du sol.

- **Un seul jeu d'octaves par pixel,** mis en forme différemment par chaque matériau : en crête pour la roche, en valeur absolue pour les fissures, déformé en sinus pour les rides.
- **Un bruit cellulaire,** distance au point le plus proche d'un réseau aléatoire, pour les cailloux, les craquelures et les touffes. Il est nouveau, et c'est le plus coûteux : réservé aux octaves proches.
- **Seuls les matériaux présents sont évalués :** un poids sous 1 % les saute.
- **Seules les octaves au-dessus de 2 pixels sont évaluées :** de loin, la texture ne coûte presque rien.

#### L'éclairage

- **La pente de la texture incline la normale,** comme le grain fin, après la normale spline.
- **La matière intervient aussi :** le choix entre neige, roche et herbe se fait avec la normale finale, texture comprise. Une pierre isolée peut donc percer la neige.

### Ce qui change dans le code

- **`PixelShader.hlsl` :** une fonction de détail par matériau, le bruit cellulaire, le mélange par la hauteur, dans `GroundAt`.
- **`PlanetSettings.hlsli` :** `TEXTURE_DETAIL`, l'intensité des textures, 0 les désactive ; les longueurs d'onde de passage avec le grain fin.
- **Rien côté processeur ni maillage.**

### Les étapes

1. **Le cadre :** la fonction de détail, la préservation de la moyenne, le mélange par la hauteur, le filtrage. Validé avec l'herbe, le matériau le plus courant près du départ.
2. **La roche,** puis **le sable,** puis **la neige,** puis **le sol aride et la toundra.** Chacun jugé sur images et en vol avant le suivant.
3. **Les mesures,** à chaque matériau.

### La mesure

- **Des vues au ras du sol,** à 2 m, 10 m et 50 m, sur herbe, roche, sable et neige. Les vues de plage et de neige basse sont à trouver.
- **Le banc de tremblement et le banc de mutation,** sur les vues de référence et les nouvelles.
- **La couleur de loin :** captures à 10 km avant et après, écart moyen de moins de 1 sur 255.
- **Le coût GPU,** au pire au ras du sol, l'écran entier couvert de sol proche.

### Critères de validation

- **L'échelle se lit à 2 m du sol :** touffes, cailloux, rides, fissures.
- **Pas de scintillement ni de mutation en plus,** au banc et en vol.
- **La couleur de loin ne change pas.**
- **Coût :** moins de 0,5 ms de plus au pire.

### Résultats de l'étape 1 : le cadre et l'herbe

- **L'échelle se lit au ras du sol :** gazon dense, touffes irrégulières de 15 à 35 cm aux pieds plus sombres, grain des brins, plaques de teintes de 2 m.
- **Premier essai écarté :** des touffes en bruit cellulaire ressemblaient à des pavés, à cause de l'arête vive où le point le plus proche change. Remplacées par des bosses douces qui se chevauchent, de taille et de hauteur aléatoires.
- **Couleur de loin préservée :** écart moyen nul à 2 km, −0,08 sur 255 à 50 m. Au ras du sol, −1,6 : le relief des touffes assombrit un peu l'ensemble.
- **Tremblement :** inchangé avec le lissage temporel. Sans lui, de 0,04 à 0,07 à 3 m, de 0,02 à 0,03 à 10 m.
- **Coût du rendu :** +0,4 ms à 3 m, +0,25 ms à 10 m, +0,1 ms à 50 m, rien à 2 km.
- **Pas encore fait :** le banc de mutation sur les nouvelles vues, et le jugement en vol.

### Résultats de l'étape 2 : la roche

- **La roche se lit de près :** strates ondulées d'environ 0,8 m, chacune de sa teinte, fissures fines de 2 m et 50 cm, lichens gris-vert d'environ 25 cm, rugosité jusqu'au pixel. Ses bosses de 1 m percent la neige mince en petites taches.
- **Premier essai écarté :** des strates tirées d'un bruit de 16 m dessinaient des cercles concentriques, comme des empreintes digitales, autour des sommets du bruit. Tirées d'un bruit de 256 m, elles sont presque parallèles à l'échelle d'une paroi, ondulées par un bruit de 4 m.
- **Corrigés au premier regard :** des lichens trop jaunes et trop grands, des fissures trop sombres qui serpentaient.
- **Jugé en vol : ne rend pas bien.** De près, les fissures, lignes où un bruit passe par zéro, faisaient des boucles molles comme des tuyaux. Refaites en réseau de fractures, sur les bords de cellules de Voronoï, interrompues par endroits. La roche reste peu convaincante, comme un enduit lisse : recherche de l'état de l'art lancée, voir `etat-de-l-art-details.md`.
- **Couleur de loin préservée :** −0,1 sur 255 à 50 m, −1,4 au ras du sol.
- **Tremblement :** inchangé avec le lissage temporel ; sans lui, de 0,18 à 0,21.
- **Coût :** presque nul en plus, +0,07 ms à 4 m, car l'herbe n'est plus calculée là où la roche couvre tout.

### Ce qui reste pour l'étape E

- **La profondeur :** cailloux et fissures en parallaxe, à partir des mêmes hauteurs.
- **Les objets :** brins d'herbe, cailloux, rochers et arbres, générés à chaque image sur une grille fixe sur la planète. Brins d'herbe : `spec-herbe.md`.

## Étape E : les détails à la surface

**Deux voies, je recommande les shaders d'abord.**

- **En shaders :** un relief de parallaxe donne de la profondeur au sol vu de près, cailloux et fissures, à partir des mêmes textures et normales. Peu coûteux, sans limite de nombre.
- **En objets procéduraux :** rochers, arbres et herbe placés par les bruits sur une grille fixe sur la planète, générés à chaque image en compute, puis dessinés par instances. Plus réaliste de près, mais c'est un gros chantier : niveaux de détail des objets, apparition sans saut.

## Ordre proposé

1. **A puis B, l'atmosphère d'abord.** Elle change toute la lumière : régler les matériaux avant serait à refaire.
2. **C,** les matériaux par pixel.
3. **D,** les textures de détail.
4. **E,** les détails à la surface : shaders d'abord, objets ensuite.

## Choix à valider

- **L'ordre ci-dessus.**
- **Détails à la surface : shaders d'abord, objets ensuite.**
- **Textures procédurales ou images :**
  - le procédural garde l'esprit du concept et n'a pas de limite d'échelle ;
  - des images libres, de type CC0, plaquées sans coutures, donneraient un réalisme rapide, mais de près elles se répètent.
