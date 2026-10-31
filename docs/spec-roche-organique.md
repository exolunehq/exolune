# Spécification : une roche organique, variée d'une région à l'autre

Statut : proposée le 2026-10-22, étapes 1 à 5 faites et fusionnées le 2026-10-22. Depuis le 2026-10-24, une seule roche, sa photo (`journal-planete.md`) : familles, tuiles dessinées, marches de la colonne et parallaxe retirées. Restent vivants les replats de l'étape 1, la colonne stratigraphique en couleur et ses lentilles.

## Le constat

Vue à 150 m d'une paroi, position `1391.1 -11.04542 50.06777 2.6 55.3`.

- **La paroi n'a rien d'organique :** des couches de 50 cm et des bancs de 2 à 8 m, parallèles, horizontaux, d'une régularité de papier peint.
- **Toute la roche de la planète est litée de la même façon,** quelle que soit la région.
- **Rien ne pousse ni ne s'accumule sur les replats.**

## Les cibles

Sept photos, en 1280 px dans `docs/images/`, toutes du domaine public ou sous CC0, issues de Wikimedia Commons.

| Fichier | Sujet | Licence et source |
|---|---|---|
| `cible-granite.jpg` | Dômes de granite, Yosemite | CC0, GeoDIL, [Half Dome 2435](https://commons.wikimedia.org/wiki/File:Half_Dome_(GeoDIL_number_-_2435).jpg) |
| `cible-gres-zion.jpg` | Falaises de grès dans le brouillard, Zion | Domaine public, NPS, [Fog Surrounds the Cliffs](https://commons.wikimedia.org/wiki/File:Fog_Surrounds_the_Cliffs_(17694606102).jpg) |
| `cible-gres-neige.jpg` | Grès à stratification croisée sous la neige, Zion | Domaine public, NPS, [Snow on cliffs](https://commons.wikimedia.org/wiki/File:Snow_on_cliffs_(23224079893).jpg) |
| `cible-plis.jpg` | Couches plissées, Provo Canyon | Domaine public, [Folded Rock Provo Canyon](https://commons.wikimedia.org/wiki/File:Folded_Rock_Provo_Canyon.JPG) |
| `cible-falaise-alcoves.jpg` | Falaises de grès à alcôves, éboulis, Nouveau-Mexique | Domaine public, [Mountains Albuquerque 2](https://commons.wikimedia.org/wiki/File:Mountains_Albuquerque_2.jpg) |
| `cible-basalte.jpg` | Coulées de basalte empilées, Bruneau Canyon | Domaine public, BLM, [Bruneau Wild and Scenic River](https://commons.wikimedia.org/wiki/File:Bruneau_Wild_and_Scenic_River,_Idaho_(36255524650).jpg) |
| `cible-badlands.jpg` | Badlands ravinés, Wyoming | Domaine public, BLM, [Dubois Badlands](https://commons.wikimedia.org/wiki/File:-mypubliclandsroadtrip_2016-_On_The_Way_To,_Dubois_Badlands_Wilderness_Study_Area_(27982944793).jpg) |

## Ce que montrent les photos

**Une famille de roche par région, chacune sa structure.**

- **Le granite est massif :** des dômes arrondis, des écailles parallèles à la surface, quelques grandes fractures, aucune couche.
- **Les grès et calcaires sont lités, mais pas comme chez nous :**
  - des bancs de quelques mètres à plusieurs dizaines de mètres, d'épaisseur très inégale ;
  - des stratifications croisées, obliques à l'intérieur des bancs ;
  - des bandes de couleur d'une formation à l'autre, du rouge au blanc ;
  - des sommets arrondis par l'érosion, des alcôves creusées dans les bancs tendres.
- **Les couches se plient :** elles plongent et se courbent à l'échelle de 100 m à quelques kilomètres, au lieu de rester horizontales.
- **Le basalte s'empile en coulées** de 5 à 20 m, débitées en colonnes verticales, séparées par des talus d'éboulis.
- **Les badlands sont tendres :** des bandes fines et colorées, ravinées partout de rigoles serrées.

**Partout, la vie et les débris prennent les replats :** végétation sur chaque corniche, éboulis au pied de chaque paroi. La roche nue n'occupe que ce qui est trop raide pour retenir quoi que ce soit.

## Le principe

### 1. Des familles de roche, choisies par la géologie

Le bruit de géologie, qui choisit déjà la couleur de la roche par région, choisit aussi sa structure, en quatre familles.

- **Massive,** granite : pas de couches ; des écailles courbes de quelques mètres et de grandes fractures espacées, aux arêtes arrondies.
- **Litée,** grès et calcaire : la structure actuelle, mais des bancs de 1 à 30 m d'épaisseur très variable, des stratifications croisées et des bandes de couleur par formation.
- **En coulées,** basalte : des bancs de 5 à 20 m, des colonnes verticales, un talus entre deux coulées.
- **Tendre,** badlands : des bandes fines et des rigoles serrées dans le sens de la pente.

Chaque famille a sa tuile de 64 m, générée au démarrage comme les autres. Entre deux régions, deux familles se mêlent.

### 2. Des couches qui plongent et se plient

- **Le pendage :** le plan des couches s'incline par région, de 0 à 40°, au lieu de suivre toujours l'horizontale.
- **Les plis :** l'angle varie lentement, à l'échelle de 100 m à 2 km, et les couches se courbent.
- **Le moyen :** la rotation des tuiles, qui aligne déjà les strates sur la verticale, reçoit en plus cet angle.

### 3. Le sol et la végétation sur les replats

- **Aujourd'hui,** la roche se décide sur la pente du maillage. Une corniche de la tuile de 64 m reste donc de la roche nue.
- **Demain,** la décision prend aussi la pente de la texture : là où une corniche est plate, le sol, l'herbe ou le sable la recouvrent ; là où elle est raide, la roche reste nue.
- **Au pied des parois,** les éboulis suivent la même logique, sur les pentes moyennes.

### 4. L'usure

- Des arêtes arrondies à toutes les échelles, plus fortes pour les roches tendres.
- Des bancs qui s'interrompent en lentilles, au lieu de traverser toute la paroi.

## La mesure

- **Le banc visuel,** à 100 m, 500 m et 2 km, sur des sites de montagne, à côté des sept photos.
- **La vue du constat,** reprise à sa position exacte, avant et après.
- **Les bancs de tremblement et des crêtes,** pour vérifier que le relief porté par le maillage ne se dégrade pas.
- **Le coût,** pour la tuile de chaque famille.

## Critères de validation

- **D'une région à l'autre,** on reconnaît des familles de roche différentes.
- **Plus de papier peint :** pas de couches régulières et horizontales partout.
- **Les replats verdissent ou se couvrent de débris,** la roche nue reste sur le raide.
- **Coût :** moins de 0,5 ms en plus.

## Les étapes

1. **Le sol sur les replats :** le gain le plus large pour le moins de code.
2. **Pendage et plis.**
3. **Les familles massive et litée,** avec les bancs inégaux et les bandes de couleur.
4. **Les familles en coulées et tendre.**
5. **L'usure.**

## Résultats

**Le banc :** `tools/banc_roche.py`, la vue du constat et trois sites de montagne à 100 m, 500 m et 2 km. Canyon à 11° S, 50° E ; montagnes sèches à 20° S, 125° E ; sommets enneigés à 15° S, 120° E.

### Étape 1 : le sol sur les replats

- **La décision :** la roche cède là où sa propre surface, maillage plus texture, est plate. Éboulis entre 0,72 et 0,82 de cosinus, sol entre 0,84 et 0,92.
- **Les replats :** les corniches arrondies de la tuile de 64 m ne s'aplatissaient jamais sur une paroi. Le haut de chaque banc penche désormais vers l'arrière, autant qu'il monte, sur 40 % du banc et au plus 2,5 m. Une contremarche au pied du banc suivant reprend la hauteur, sans marche.
- **Effet :** des bandes d'herbe ou de sable sur chaque banc, la neige s'y pose aussi. Plus aucun effet au-delà de 500 m, où la tuile filtrée perd ses replats.
- **Coût :** nul. **Crêtes :** pas de pics.
- **Reste :** les bandes sont aussi régulières que les bancs, d'où les étapes 2 et 3.

### Étape 2 : pendage et plis

- **Le moyen retenu, un décalage et non une rotation :** un champ lisse en mètres, `StrataShift`, relève les strates des tuiles de roche. Sa pente est le pendage. Les deux plans de la projection biplanaire voient le même décalage au même point.
- **Pourquoi pas la rotation de la spec :** chaque plan de projection voit un autre pendage apparent, et un plan oblique le déforme encore. Résultat : des chevrons nets le long des coutures.
- **Le pendage :** octaves de 8 à 2 km, jusqu'à `STRATA_DIP` = 0,5 de pente, nul là où le bruit régional est faible.
- **Les plis :** octaves de 1 km à 128 m, chacune 0,75 fois la précédente, jusqu'à `STRATA_FOLD` = 0,4, seulement dans les régions déformées.
- **Effet :** couches inclinées et ondulées d'une région à l'autre ; elles dessinent des V dans les ravins, comme de vraies strates.
- **Coût :** +0,1 ms au rendu, +0,1 ms au calcul près du sol. **Crêtes :** pas de pics.

### Étape 3 : familles massive et litée

- **Le choix :** `MassiveRock`, sur la palette du bruit de géologie. Granite, et basalte en attendant l'étape 4 : massif. Du calcaire au grès rouge : lité. Environ la moitié des montagnes de chaque.
- **Les bancs ne viennent plus de la tuile :** elle les répéterait tous les 64 m le long de la paroi. Une colonne stratigraphique, `StrataColumn`, les calcule au pixel sur s, l'altitude moins le décalage de l'étape 2.
  - Formations de 10 à 60 m, chacune sa teinte, du blanc au rouge, sa part de bancs tendres et l'épaisseur de ses bancs.
  - Bancs de 4 à 24 m : un replat au sommet des bancs durs, une pente au dos des tendres, une contremarche au pied du suivant.
  - Le même relief porté par le maillage, sans marche : chaque plan de stratification décide seul de sa hauteur, des deux côtés.
- **La tuile litée de 64 m** ne garde que ce qui varie le long des bancs : diaclases et couloirs, stratification oblique, rideaux de vernis.
- **Le granite :** tuiles de 8 m et 64 m, sans couches. Bosses, dômes, écailles courbes qui meurent sur les côtés, deux réseaux de fractures, stries d'eau. Gris clair quelle que soit la teinte régionale.
- **Pièges rencontrés :**
  - Zigzags d'éclairage sur les bancs : l'altitude de la spline, lissée, ne suivait pas le relief retranché, interpolé linéairement. La colonne prend l'altitude linéaire des sommets.
  - Contremarches de 2 à 3 pixels, crénelées : largeurs d'au moins 4 pas, pas tiré de la maille et non des dérivées écran.
- **Coût :** +0,2 ms au rendu depuis le départ, à la vue du constat. **Crêtes :** pas de pics.

### Étape 4 : familles en coulées et tendre

- **Le choix, `RockFamilies` :** sur la palette du bruit de géologie, basalte en coulées, granite massif, puis sédiments. Parmi les sédiments, tendre là où le bruit du fer est fort et la région sèche. Transitions étroites : deux familles se calculent seulement le long d'une bande.
- **Coulées :** la même colonne, des coulées de 3 à 20 m, toutes dures, chacune terminée par un replat large de 2 à 4 m que les éboulis couvrent, le talus. Tuile de 64 m en colonnes prismatiques de 1,3 à 2,2 m, joints transversaux. Basalte presque noir.
- **Tendre :** bandes de 2 à 15 m blanches, rouges, mauves, jaunes et grises, bancs de 0,8 à 3 m surtout tendres. Tuile de 64 m en rigoles de 1,3 à 2,7 m. Roche nue dès 25° de pente au lieu de 33°.
- **Le pendage et les plis** prennent leur dosage dans le bruit de géologie, déjà calculé par sommet ; le bruit régional propre de l'étape 2 disparaît. Plis ramenés à 0,25.
- **Sites du banc :** basalte à 15° S, 120° E ; granite à 19,7° S, 124,6° E ; badlands à 20,3° S, 125,4° E.
- **Limites :** les badlands du banc sont sur des collines douces, la roche tendre s'y voit peu. Les colonnes du basalte ne se lisent que de près.
- **Coût :** total depuis le départ, +0,2 à +0,35 ms au rendu. Mesuré sous un GPU chargé à 80 % par une autre instance, temps divisés par le facteur de charge. **Crêtes :** pas de pics.

### Étape 5 : l'usure

- **Lentilles, `BedLenses` :** un champ lent, bruits de 256 et 128 m, calculé par sommet. Chaque plan de stratification a son seuil contre lui ; en dessous, sa marche s'efface et les deux bancs se fondent. Les bancs s'interrompent en lentilles, les formations rarement. La teinte d'un banc s'efface avec lui.
- **Arêtes arrondies :** contremarches et replats 2,5 fois plus larges pour la roche tendre. Le reste de l'arrondi était déjà là : profils en `smoothstep`, largeurs d'au moins 4 pas.
- **Effet :** discret au constat, quelques corniches qui s'arrêtent net.

### Bilan

- **Coût final, GPU libre, rendu :** +0,26 ms au constat, +0,32 ms au canyon à 100 m, +0,53 ms au site sec à 100 m. Calcul inchangé.
- **Le site sec dépasse de 0,03 ms :** la seule famille litée y est dessinée, mais les quatre branches de familles déroulées pèsent sur les registres. Essayés sans gain : deux familles choisies par indice, `[branch]`, boucle non déroulée.
- **Critères :**
  - Familles reconnaissables d'une région à l'autre : oui pour litée, granite et basalte ; badlands peu visibles faute de pentes raides sur le site trouvé.
  - Plus de papier peint : bancs inégaux, formations colorées, pendage et plis variables.
  - Replats couverts, roche nue sur le raide : oui de près ; au-delà de 500 m les replats s'effacent avec le filtrage.
- **Pour la fusion :** les nouvelles limites sont à passer à la règle universelle de `spec-rendu-lointain.md`. Liste dans la note de passation de la session.

## Fusion du 2026-10-22

- **Limites converties à la règle universelle** de `spec-rendu-lointain.md` : familles en `SpreadStep`, roche tendre en `SlopeShares`, replats en `RockShares`.
- **Les replats tels quels effaçaient la roche de loin :** décidés sur la pente du maillage, presque plate à grande distance, ils couvraient toute la roche. Ils sont maintenant une part, d'après les pentes cachées et la pente de texture perdue : roche vue 9–13 % de 800 à 8 km.
- **Projection triplanaire** et normale de la passe de relief sur 32 mailles, venues des correctifs des lames.
- **Coût :** rendu +0,1 à +0,8 ms par rapport à avant la fusion.

## Correctif du 2026-10-22 : l'effet « feutre »

**Symptôme,** vu en vol à `3756.3 -39.55694 12.77814 -13.1 -141.1` : des strates rectilignes, marquées d'un trait sombre régulier, avec des rangées de taches noires.

**La règle enfreinte,** dans `principes.md` : aucune structure dessinée d'un trait uniforme. Elle vaut pour toutes les familles et tous les lieux.

**Les causes, isolées en coupant chaque couche :**
- **Les traits :** chaque plan de la colonne stratigraphique avait une marche de 0,6 à 2 m, et chaque banc courait d'un bout à l'autre de la paroi.
- **Les taches :** dans la tuile de 64 m, les couloirs étaient taillés banc par banc et s'alignaient en rangées de tirets sombres.

**Les corrections, pour toutes les familles :**
- **Les marches des plans suivent une loi au cube :** la plupart sont à peine visibles, quelques-unes seulement font les corniches.
- **Les bords des strates ondulent** d'environ 80 cm, sur des longueurs de 4 à 64 m.
- **Les bancs s'interrompent et reprennent** le long de la paroi, sur 16 à 128 m, au-delà des lentilles par sommet.
  - Le seuil de chaque plan s'élargit de ce que le pixel ne montre pas de ce champ, selon la règle universelle.
  - Sur 4 à 64 m, les bancs se brisaient en tirets.
- **Les couloirs suivent toute la pente :** quatre emplacements par tuile, un sur deux occupé, larges de 0,4 à 2 m, qui ondulent et s'interrompent. Leur couleur et leur occlusion sont adoucies.

**Mesures :**
- **Tremblement,** avec lissage : 0,22 → 0,19 au site du constat, 0,22 → 0,18 à la corniche, 0,40 → 0,37 à la vue des bancs.
- **Roche en descente :** inchangée, 10 à 13 %.
- **Coût :** non mesurable pendant que la session hybride occupe le GPU ; à reprendre.

## Correctif du 2026-10-24 : craquelures et rigoles

**Symptômes,** en vol : des craquelures en segments droits à `4242.2 16.27025 123.15986 16.1 -166.5`, un versant de badlands en velours côtelé à `4285.0 16.27172 123.16603 4.8 -159.1`.

**La règle enfreinte,** la même : aucune structure dessinée d'un trait uniforme.

**Les corrections, pour tous les usages :**
- **Tout Voronoi a des bords qui ondulent :** sa grille est déformée par un bruit périodique d'une demi-maille et d'un huitième, dans `Voronoi` même. Granite, cristaux et pierres en héritent.
- **Une fissure varie le long d'elle-même :** elle s'élargit, se resserre et s'interrompt sur un demi-mètre.
- **Les rigoles des badlands vont par plaques** de 8 à 32 m et se rassemblent en ravines d'environ 16 m.

**Mesures :** banc de qualité sans régression nette ; tremblement 0,55 → 0,54 sur le versant ; aucun coût, les tuiles sont générées au démarrage.
