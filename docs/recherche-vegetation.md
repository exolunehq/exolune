# Recherche : la végétation, de l'arbre à la forêt vue d'orbite

Statut : recherche et étape 1 faites le 2026-10-25, tag `piste/vegetation` ; v2 et v3 le même jour, tags `piste/vegetation-v2` et `piste/vegetation-v3`, sections « v2 » et « v3 » plus bas. Code : `Vegetation.hlsli`, `PlantPlacement.hlsli`, la canopée dans `PixelShader.hlsl`. Les plantes générées, `Vegetation.cpp` et `Plant*.hlsl`, sont retirées le 2026-10-30 ; leurs formes et leurs mesures sont dans `log/recherche-vegetation-historique.md`. Bancs : `tools/banc_vegetation.py`, `tools/saisons_terre.py`. Tests en vol : `tools/tests/2026-10-25-vegetation.txt`, `-v2.txt`, `-v3.txt`.

**En bref :**
- **Essai planétaire du 2026-10-27 :** arbres et arbustes de jeu, maillage proche et imposteurs lointains sur les mêmes instances ; bouquets foliaires, normales locales et visibilité précalculée comparés hors écran. Les premiers vols et les modèles rejetés sont dans le log de `vegetation-planetaire.md`.
- **Prototype comparé les 2026-10-26 et 27 :** modèles détaillés libres, agrégats volumiques inspirés de Nanite Foliage et imposteurs multivues ; silhouettes améliorées par les volumes, coût GPU mesuré, lumière et relais planétaire à poursuivre ; voir `log/prototype-vegetation-volumique.md`.
- **Une seule population de plantes, deux représentations, une seule source :** `Vegetation.hlsli` dit où pousse quoi, combien, de quelle taille.
  - **Près :** des objets sur la grille de la planète, dessinés par les modèles de jeu, maillages proches et imposteurs lointains (`vegetation-planetaire.md`) ; chacun entier dès qu'il est dessiné, de 8 à 5 pixels de haut.
  - **Loin :** la canopée dans la matière du sol, à la hauteur de ses arbres : sa part, sa couleur, le relief de ses couronnes, l'ombre qu'elle jette au sol.
  - **Le raccord :** la canopée au sol retire ce que les objets dessinent, comme une couche booléenne. Une forêt garde sa part de chaque pixel de 20 km à 50 m.
- **Où pousse quoi, par des lois publiées :**
  - la limite froide par la saison de croissance (Körner et Paulsen) ;
  - l'eau par l'aridité de Holdridge, le plafond de Sankaran et les deux états de Hirota et Staver, savane et forêt ;
  - où sont les bois, par deux champs de bruit comme les cailloux : des régions sans arbres, des clairières dans toute forêt, des arbustes par taches, un manteau aux lisières ;
  - les crêtes nues, les creux boisés, par la hauteur sur le sol régional ;
  - conifères au froid, feuillus au chaud, couronnes plates en savane, arbustes des terres sèches.
- **La recommandation d'alors, faite :** les imposteurs, dès 5 pixels, `vegetation-planetaire.md` ; le sol exact des tuiles gardé d'une image à l'autre, `optimisation.md`, round 3. Le placement reste recalculé à chaque image.

## L'état de l'art

Recherche du 2026-10-25, sources primaires sauf mention.

### Les modèles d'arbres

- **Weber et Penn 1995** ([article](https://courses.cs.duke.edu/fall02/cps124/resources/p119-weber.pdf)) :
  - un modèle paramétrique, tronc, branches, sous-branches, feuilles, 3 à 4 niveaux ;
  - 5 000 à 100 000 facettes par arbre ;
  - de loin, les tiges deviennent des lignes et les feuilles des points, retirées par masses : un arbre de 100 000 facettes à 2 km n'en garde qu'une trentaine. Le but affiché : pas de vagues de résolution entre niveaux de détail.
- **La colonisation de l'espace,** Runions, Lane et Prusinkiewicz 2007 ([article](https://www.algorithmicbotany.org/papers/colonization.egwnp2007.html)) :
  - les branches poussent vers des points d'attraction semés dans l'enveloppe de la couronne, 1 500 à 12 000 ;
  - les rayons suivent le modèle des tuyaux, rⁿ = r₁ⁿ + r₂ⁿ, n de 2 à 3 ;
  - quelques secondes à quelques minutes par arbre.
- **Les modèles auto-organisés,** Palubicki et al. 2009 ([article](https://www.algorithmicbotany.org/papers/selforg.sig2009.html)) : les bourgeons se disputent la lumière ; la forme s'adapte aux voisins. Coût hors ligne.
- **Les L-systèmes** ([The Algorithmic Beauty of Plants](http://algorithmicbotany.org/papers/abop/abop.pdf)) : réécriture parallèle et tortue ; peu coûteux, mais aveugles à l'environnement sans extension.
- **SpeedTree** ([documentation](https://docs.unity3d.com/speedtree-runtime-sdk/manual/level-of-detail.html)) :
  - une hiérarchie : branches maillées, frondes le long des branches, cartes de feuilles face à la caméra, puis panneaux ;
  - les niveaux de détail se fondent par des positions interpolées dans le vertex shader : les petites branches se réduisent à leur axe, une part des cartes rétrécit pendant que les autres grandissent ;
  - le vent en étages : balancement global, ondulation des feuilles, branches, retournement des feuilles.
- **Les budgets des jeux,** source secondaire ([polycount](https://polycount.com/discussion/comment/2625799)) : 15 000 à 22 000 triangles au plus près, 4 500 à 5 000 au troisième niveau, 36 pour un panneau.
- **Ce qu'on en retient :** générer au démarrage une bibliothèque de quelques dizaines de formes est bon marché ; un arbre unique par instance ne l'est pas. Les formes de Weber et Penn suffisent aux couronnes ; la colonisation de l'espace vaudra pour les branches vues de près.

### La chaîne des niveaux de détail

- **Les imposteurs octaédriques,** Ryan Brucks ([blog](https://shaderbits.com/blog/octahedral-impostors), [ImpostorBaker](https://github.com/ictusbrucks/ImpostorBaker), [80.lv](https://80.lv/articles/impostor-baker-for-ue4/)) :
  - l'objet rendu depuis une grille de directions sur un octaèdre ou un demi-octaèdre, couleur, normale et profondeur dans un atlas ;
  - réglage courant, 16 × 16 vues sur 2048², trois vues mêlées par pixel, la profondeur pour la parallaxe ([three.js](https://discourse.threejs.org/t/a-forest-of-octahedral-impostors/85735), [Godot](https://github.com/SIsilicon/Godot-Octahedral-Impostors)) ;
  - le demi-octaèdre donne plus de résolution aux vues de côté, celles du feuillage ;
  - utilisé dans Fortnite pour les arbres lointains.
- **Les nuages de panneaux,** Décoret et al. 2003 ([article](https://graphics.cs.yale.edu/publications/billboard-clouds-extreme-model-simplification)) : quelques plans choisis sous une erreur géométrique bornée ; coûteux en remplissage.
- **La forêt comme matière du sol,** Bruneton et Neyret 2012 ([article](https://diglib.eg.org/handle/10.1111/v31i2pp373-382), [vidéo](https://www.youtube.com/watch?v=4Ghulpp6CPw)) :
  - les arbres proches rendus un par un ;
  - au-delà, un shader du terrain qui dépend du lieu, de la vue et de la lumière couvre les arbres plus petits que le pixel ;
  - le passage de l'un à l'autre se fait sans pop ni crénelage. Leurs temps n'ont pas pu être lus.
- **Le modèle géo-optique,** Li et Strahler 1992 ([rapport](https://apps.dtic.mil/sti/pdfs/ADA263570.pdf)) : des couronnes posées au hasard, un modèle booléen ; un pixel mêle couronnes au soleil et à l'ombre, sol au soleil et à l'ombre ; le point chaud quand la vue s'aligne sur le soleil. Une réflectance de forêt en forme close, de la densité et de la forme des couronnes.
- **Le feuillage de Nanite,** Unreal 5.7, expérimental ([documentation](https://dev.epicgames.com/documentation/unreal-engine/nanite-foliage)) :
  - des assemblages de pièces instanciées, jusqu'à 65 000 par maillage ;
  - de loin, des voxels de 4 × 4 × 4 qui gardent une distribution de normales ;
  - le vent par des os, 100 000 os pour 0,1 ms ;
  - les cartes à transparence et le vent déplaçant les sommets sont déconseillés.
- **Les fondus :** le fondu tramé d'Unreal laisse un pop en fin de fondu ; SpeedTree et Weber et Penn font grandir ou rétrécir, sans trame.

### Les grands mondes

- **Horizon Zero Dawn,** van Muijden, GDC 2017 ([diapositives](https://www.guerrilla-games.com/media/News/Files/GDC2017_VanMuijden_GPUBasedProceduralPlacementInHorizonZeroDawn.pdf)) :
  - déterministe, localement stable ; le monde construit autour du joueur par des passes de calcul ;
  - une carte de densité par type, comparée à un motif de seuils fixe ;
  - plus de 500 types, plus de 100 000 objets, environ 250 µs de GPU en moyenne.
- **La végétation d'Horizon,** Sanders, GDC 2018 ([GDC Vault](https://gdcvault.com/play/1025066/Between-Tech-and-Art-The)) : non lue. **Forbidden West** ([McLaren](https://www.guerrilla-games.com/read/adventures-with-deferred-texturing-in-horizon-forbidden-west)) : un pré-passage de visibilité pour le feuillage et la géométrie à transparence.
- **Ghost of Tsushima** ([herbe](https://gdcvault.com/play/1027214/Advanced-Graphics-Summit-Procedural-Grass), [vent](https://gdcvault.com/play/1027124/Blowing-from-the-West-Simulating)) : des brins générés par tuile sur GPU, en amas de Voronoi ; un vent de bruit 2D partagé par le CPU et le GPU ; au loin, des textures.
- **Far Cry 5** ([Carrier, 2018](https://blog.playstation.com/2018/03/22/the-procedural-world-generation-of-far-cry-5/)) : hors ligne, dans Houdini, sur 100 km² ; les espèces se disputent la place selon l'ensoleillement, l'humidité et l'eau. **Far Cry 4** ([McAuley](https://gdcvault.com/play/1022235/Rendering-the-World-of-Far)) : feuilles modélisées de près, panneaux tessellés et déplacés de loin.
- **Microsoft Flight Simulator,** Asobo ([Fuentes](https://www.asobostudio.com/files/inline-images/Designing_Terrain_System_Fuentes_Lionel.pdf)) : des arbres placés d'après des données de couverture, photogrammétrie dans les villes ; la distance de dessin des arbres n'a pas été trouvée.
- **Unreal 5, PCG** ([modes](https://dev.epicgames.com/documentation/en-us/unreal-engine/using-pcg-generation-modes-in-unreal-engine), [GPU](https://dev.epicgames.com/documentation/en-us/unreal-engine/using-pcg-with-gpu-processing-in-unreal-engine)) : des grilles emboîtées, les grands objets sur la grille grossière ; un rayon de génération par niveau ; des nœuds sur GPU.
- **Outerra,** forum de l'auteur, 2009 ([fil](https://forum.outerra.com/index.php?topic=15.0)) : des panneaux émis par tuile d'après une carte de couverture, l'altitude, la pente, la courbure et un bruit fractal ; au plus 44 000 arbres par km², environ 200 000 par scène.
- **Star Citizen,** source secondaire ([wiki](https://starcitizen.tools/Planet_Tech_v5)) : le shader de la planète estime la couleur lointaine, y compris les objets pas encore chargés, pour supprimer le pop.

### Les biomes et le placement

- **Whittaker,** redessiné par Ricklefs ([données numérisées](https://github.com/valentinitnelav/plotbiomes)) : la toundra sous −5 °C environ ; la forêt boréale de −7 à +4 °C ; le passage du tempéré au tropical vers 19 °C ; les forêts, bois et steppes séparés par les précipitations, de quelques dizaines à quelques centaines de cm.
- **Holdridge** ([Lugo et al. 1999](https://research.fs.usda.gov/download/treesearch/30306.pdf)) : la biotempérature, moyenne des températures entre 0 et 30 °C ; l'évapotranspiration potentielle, 58,93 mm par degré ; les provinces d'humidité par son rapport aux précipitations : humide sous 1, subhumide de 1 à 2, semi-aride de 2 à 4, aride au-delà.
- **La ligne des arbres** ([Körner et Paulsen 2004](https://edoc.unibas.ch/8594), [Paulsen et Körner 2014](https://edoc.unibas.ch/33369)) :
  - la saison de croissance, les jours de plus de 0,9 °C, d'au moins 94 jours et de 6,4 °C en moyenne ;
  - 6,7 ± 0,8 °C dans le sol à 46 sites de 68° N à 42° S ;
  - sur Terre, de 3 100 à 4 100 m aux tropiques, 4 200 m vers 28° N, 2 200 m dans les Alpes, 1 100 m à 61° N, la mer vers 68 à 70° N (compilation de Körner 1998, source secondaire).
- **La couverture des arbres et l'eau :**
  - Sankaran et al. 2005 ([article](https://researchspace.csir.co.za/bitstream/handle/10204/2072/sankaran_2005.pdf)) : dans 854 savanes africaines, le couvert ligneux au plus de 0,14 MAP − 14,2 %, de 101 à 650 mm ; aucun arbre sous 101 mm ; au-delà de 650 mm, la canopée peut se fermer ;
  - Hirota et al. 2011 ([article](https://gael.univ-grenoble-alpes.fr/sites/default/files/Mediatheque/Files/EC2%C2%B0C%20-%20hirota%26al_2011_science.pdf)) : trois états, forêt vers 80 %, savane vers 20 %, sans arbres sous 5 % ;
  - Staver et al. 2011 ([article](https://researchspace.csir.co.za/bitstream/handle/10204/4802/Staver_2011.pdf)) : forêt et savane bistables de 1 000 à 2 500 mm, le feu tranche.
- **La densité,** Crowther et al. 2015 ([article](https://cdanfort.w3.uvm.edu/csc-reading-group/crowther-nature-2015.pdf)) : 3 040 milliards d'arbres de plus de 10 cm, 43 % tropicaux, 24 % boréaux, 22 % tempérés. Les densités par hectare et par biome ne sont lisibles que sur une figure : non confirmées.
- **Les formes,** base Tallo, Jucker et al. 2022 ([article](https://eprints.gla.ac.uk/272945/1/272945.pdf)), médianes de 498 838 arbres, diamètre de la couronne sur hauteur : forêt tropicale humide 0,24 ; tempérée feuillue 0,36 ; tempérée résineuse 0,31 ; boréale 0,21 ; méditerranéenne 0,53 ; savane 0,34 ; terres sèches 1,07. Le rayon de la couronne croît comme H^0,7.
- **Les arbustes des déserts,** Larrea : 1,7 m en moyenne, 14 % du sol, 24 % avec les autres arbustes à Santa Rita ([FluxLetter](https://fluxnet.org/wp-content/uploads/FluxLetter_Vol2_No4.pdf)). **Le maquis et le chaparral :** couverture et hauteur non confirmées.
- **Les pentes :** 82 % des forêts sur des pentes de moins de 15°, 4 % au-delà de 30° ([SND](https://snd.se/en/catalogue/dataset/snd1296-1)) ; la forêt de montagne tropicale à 75 % sur plus de 27° ; les avalanches partent des pentes de plus de 30° sans forêt dense.

### La structure des forêts

- **Les arbres sont en amas,** presque toutes les espèces de six parcelles de 25 à 52 ha (Condit et al. 2000, [résumé](https://pubmed.ncbi.nlm.nih.gov/10827950/)).
- **Les trouées** (Asner et al. 2013, [article](https://pmc.ncbi.nlm.nih.gov/articles/PMC3626694/)) : 5,9 millions de trouées sur 125 581 ha ; leurs tailles en loi de puissance d'exposant 1,83 ± 0,09 ; une trouée descend à 2 m du sol.
- **Les lisières** (Laurance 2002) : bien des espèces évitent les clairières de moins de 100 m. Leur profondeur : non confirmée.
- **L'éclaircie naturelle,** loi de Reineke ([synthèse](https://en.wikipedia.org/wiki/Stand_density_index)) : log N = −1,605 log D + k.
- **La hauteur** ([Lang et al. 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10627820/), [Simard et al. 2011](https://earthobservatory.nasa.gov/IOTD/view.php?id=77637)) : plus de 30 m sous les tropiques humides, jusqu'à 65 m ; moins de 20 m en forêt boréale ; 3 m en moyenne à 70° N.

### La couleur d'une canopée

- **Un couvert est plus sombre qu'une feuille :** il cache ses propres ombres.
- **Visible et proche infrarouge,** Cescatti et al. 2012 ([article](https://www.cen.uni-hamburg.de/en/icdc/data/land/docs-land/cescattietal-rse-2012.pdf)), albédo de 0,3 à 5 µm : résineux persistants 0,05 à 0,11 ; feuillus caducs 0,11 à 0,15 ; savane 0,14 à 0,19 ; prairie 0,16 à 0,22.
- **Dans le bleu,** Moody et al. 2007 ([résumé](https://collaborate.umb.edu/en/publications/northern-hemisphere-five-year-average-2000-2004-spectral-albedos-/)) : 0,03 pour les résineux, 0,36 sous la neige.
- **L'Amazonie,** 0,03 ; 0,06 ; 0,025 en rouge, vert et bleu : l'ancre sombre de la palette des climats (`tools/palette_biomes.py`).

### Les coûts publiés

- Horizon : 250 µs pour plus de 100 000 objets.
- Nanite : 500 000 arbres de 1 à 10 millions de polygones dans la démo de The Witcher 4, à 60 images par seconde sur PS5.
- Imposteurs : 16 × 16 vues sur un atlas de 2048² ; 12 à 36 sommets par carte.
- Outerra : environ 200 000 panneaux par scène.

## La recommandation

**Trois architectures conviennent à nos règles,** place fixe sur la grille, pas de pop, un pixel montre sa moyenne :
1. **Un placement sans état sur la grille de la planète, des dessins indirects :** HZD, Proland, Outerra, PCG. C'est le système des objets de proximité.
2. **Deux représentations raccordées analytiquement :** Bruneton et Neyret, Li et Strahler, Star Citizen. La matière du sol porte la couverture, la couleur, l'ombre et le relief des couronnes, et retire ce que les objets dessinent.
3. **Des grappes et des voxels continus,** le feuillage de Nanite : le meilleur accord avec la moyenne au pixel, mais des mesh shaders, un niveau de détail par grappes et un rendu de voxels.

**Retenu : 1 et 2, dans cet ordre de travail.**
- **Étape 1, faite :** objets proches et canopée au sol, une seule source, le raccord booléen.
- **Étape 2 : un cache des plantes par tuile.** Le placement est recalculé à chaque image ; son coût par plante borne la portée des objets à 24 pixels. Une tuile évaluée une fois, gardée tant qu'elle reste à portée, le divise par le nombre d'images.
- **Étape 3 : des imposteurs pour la bande de 6 à 24 pixels,** générés au démarrage depuis nos formes, demi-octaédriques, 16 × 16 vues. Les plantes y sortiraient du sol à 6 pixels, comme les cailloux, au lieu de 24.
- **Ensuite :** le vent, le sous-bois et le sol forestier, les ombres portées des plantes, plus d'espèces.

## Étape 1 : ce qui est fait

### Où pousse quoi : `Vegetation.hlsli`, `VegetationAt`

**Le climat du moteur :** la température annuelle moyenne et l'humidité, le log des précipitations de 100 à 3 000 mm (`BiomePalette.hlsli`). Tout le reste en découle.
- **Les saisons :** une sinusoïde autour de la moyenne annuelle, de demi-amplitude 3,5 + 18 sin² de la latitude.
  - Ajustée sur les terres de la Terre, TerraClimate 1991-2020 (`tools/saisons_terre.py`).
  - Sur les mois eux-mêmes, la sinusoïde mesurée donne la même saison de croissance pour 98 % des cellules ; le modèle par la latitude, pour 92 %.
  - Avec elle, en forme close : la saison de croissance, sa moyenne et sa longueur ; la biotempérature de Holdridge.
- **La limite froide :** la moyenne de la saison de croissance, de 5,7 à 7,1 °C (`TREE_LINE`), 6,4 ± 0,7 de Körner et Paulsen, élargie par ce que le pixel couvre de températures (`SpreadStep`). Avec nos amplitudes, les 94 jours ne limitent jamais avant les 6,4 °C : vérifié jusqu'à 21,5 °C d'amplitude.
- **L'eau :** l'aridité, précipitations sur évapotranspiration de Holdridge.
  - Le plafond de Sankaran, réécrit avec l'aridité à leur évapotranspiration de 1 414 mm (24 °C).
  - L'état de savane : un quart de l'état de forêt sous le plafond, comme les deux modes de Hirota, 20 et 80 % ; soit 20 % dès 650 mm, le coude de Sankaran. Ses arbres sont épars entre les peuplements.
  - L'état de forêt : des peuplements à 90 % de couronnes (`STAND_COVER`), sur la part des terres qui donne les 80 % de Hirota avec la savane entre eux ; il gagne de 1 000 à 2 500 mm à cette évapotranspiration (Staver).
- **Les peuplements :** un champ du bruit de gradient de la planète, de 4 km à 8 m, au-dessus du seuil qui laisse la bonne part des terres. Clairières, bosquets et lisières en sortent, aussi nets que son octave la plus fine ; ce que le pixel ne peut pas montrer du champ élargit le seuil, la règle universelle.
- **Les arbustes :** 20 % du sol entre les peuplements dans les terres sèches (Larrea), de l'hyper-aride sans rien jusqu'aux terres humides où l'herbe les remplace.
- **Les espèces :** conifères sous 3 °C de moyenne annuelle, de 0 à 6 °C (Whittaker), feuillus au-dessus ; des couronnes plus basses et trois fois plus larges en savane, au-dessus de 19 °C et sous une aridité de 1.
- **La hauteur de la canopée :** 40 m dans le chaud et l'humide, moins avec la saison et l'eau : 15 à 20 m en boréal, 8 à 12 m en savane (Simard, Lang, Tallo). Les arbres s'étalent autour de 0,7 de cette hauteur, sur 0,6 octave.
- **Le sol :** ni sur la roche nue, ni sur les éboulis, ni sur la plage. Sur la neige, oui : notre neige suit la moyenne annuelle, et une forêt boréale pousse là où l'hiver est long.

### Les plantes près de la caméra : `PlantPlacement.hlsli`

- **Le système des objets de proximité, une classe de plus :** une octave de hauteurs par niveau de la grille, de 0,5 à 64 m ; un candidat par cellule du quart de la plus petite hauteur de l'octave. Dans des fenêtres de 424 cellules, un dispatch à part.
- **Un placement booléen :** les couronnes posées au hasard couvrent 1 − e^(−empreinte) du sol. L'empreinte de chaque octave est celle qui donne la couverture du lieu, partagée par les hauteurs.
- **Les deux passes :**
  - **la légère** borne chaque candidat par le climat sur le sol du maillage, et tire l'espèce comme la lourde : déserts, toundras et mers ne vont pas plus loin ;
  - **la lourde** pose le pied sur le sol exact, décide sur les parts des matériaux sans leurs textures (`gMaterialTextures`), tire l'espèce, garde ou non.
- **Le placement compte chaque couronne** comme le disque de Tallo vu de dessus : 0,3, 0,45 et 1,1 fois la hauteur, `PLANT_CROWN`.
- **La plante ne sort que là où les mailles font moins d'une fois et demie sa hauteur.** Son tronc descend toujours à 15 % de sa hauteur entière sous son pied : le sol du maillage ne le découvre jamais.
- **Ses formes générées et leur croissance,** retirées le 2026-10-30 : `log/recherche-vegetation-historique.md`.
- **La lumière :** l'ombre du relief à son pied, par l'horizon du maillage ; sous le couvert du peuplement, la lumière par ses trouées, de moins en moins vers son sommet, comme au sol.

### La forêt au-delà : la canopée dans le sol, `PixelShader.hlsl`

- **Sa part :** la couverture du lieu, moins ce que les objets dessinent à cette distance, en couche booléenne : 1 − (1 − couverture)^(1 − part dessinée). Le sol sous une couronne dessinée est caché par elle ; seul compte celui qu'elle laisse voir.
- **De côté,** une canopée cache davantage le sol, comme le modèle booléen : la part vue est 1 − (1 − part)^(1/cos de la vue).
- **Sa couleur, la sienne :** celle de l'Amazonie pour les feuillus, 0,7 de celle-ci pour les conifères, un gris olive pour les arbustes. Le sol ouvert garde la couleur du climat.
- **Son relief :** les bandes de détail de 2 à 16 m, la taille des couronnes, éclairées comme le sol.
- **Son ombre au sol :** le sol sous des couronnes, dessinées ou non, reçoit le soleil par leurs trouées, (1 − couverture)^(1/μ), et le ciel par (1 − couverture). Les cailloux et les touffes aussi ; sous un peuplement, le sol est la litière des arbres, sans les touffes ni les rochers d'une prairie.

### Les vues de diagnostic et les bancs

- **`MYPLANETENGINE_VIEW` :** `forest`, la canopée au sol en tramé et les plantes en blanc ; `trees`, les arbres seuls ; `biome`, la classe ; `temperature`, `humidity`, `season`, `altitude`, leurs valeurs telles quelles.
- **`MYPLANETENGINE_NO_PLANTS` :** aucune plante, la canopée au sol partout.
- **`tools/banc_vegetation.py` :** `biomes`, `orbite`, `raccord`, `lisiere`, `climat`, `tests`, `vues`, `releve`. Le banc `cout`, qui mesurait les plantes générées parmi les objets, est retiré avec elles.
- **Correctif en chemin :** la vue de diagnostic `objects` dessinait les objets dans la vue `sun`, l'indice ayant glissé à l'arrivée de celle-ci.

## Étape 1 : mesures

### La couverture par biome

Vue d'orbite, huit côtés de la planète, le milieu de chaque disque (`banc_vegetation.py biomes`). Biome du moteur : provinces d'humidité de Holdridge, températures de Whittaker.

| Biome | Part des terres | Couvert ligneux | Dont arbres | Publié |
|---|---|---|---|---|
| Toundra et alpin | 26,7 % | 7,9 % | 7,8 % | 0 ; le pixel d'orbite mêle les vallées boisées |
| Boréal | 13,0 % | 54,0 % | 51,7 % | forêt, mode à 80 % (Hirota), avec sa toundra boisée |
| Tempéré humide | 14,4 % | 58,8 % | 58,0 % | forêt, mode à 80 % |
| Tempéré sec | 10,5 % | 28,7 % | 15,8 % | bois et steppes, sous le plafond de Sankaran |
| Tropical humide | 6,5 % | 55,5 % | 52,6 % | forêt et savane bistables de 1 000 à 2 500 mm (Staver) |
| Savane et tropical sec | 13,1 % | 31,1 % | 15,3 % | savane, mode à 20 % (Hirota) |
| Désert | 15,9 % | 18,2 % | 3,1 % | sans arbres sous 5 % ; arbustes 14 à 24 % (Larrea) |

- **Les arbres suivent les modes publiés,** à la part bistable près : le tropical humide de la planète a surtout 1 000 à 2 000 mm, où forêt et savane se partagent la terre.
- **Une comparaison au couvert mesuré de la Terre par biome,** MODIS VCF ou Hansen, reste à faire : un téléchargement.

### La ligne des arbres

**Selon la latitude, la formule seule, ses bruits à zéro** (`banc_vegetation.py formule`) :

| Latitude | 0° | 10° | 20° | 30° | 40° | 45° | 50° | 55° |
|---|---|---|---|---|---|---|---|---|
| Planète | 4 320 m | 4 010 m | 3 480 m | 2 680 m | 1 610 m | 1 020 m | 440 m | la mer |
| Terre (Körner) | 3 100 à 3 900 m | | 4 000 m à 19° N | 4 200 m à 28° N | 3 200 à 3 600 m | 2 200 m à 47° N | | |

- **Sur Terre, plus loin vers le pôle :** 1 100 m à 61° N, 650 m à 68° N, la mer vers 70° N.

- **Aux tropiques, la planète est la Terre.** Aux latitudes moyennes, sa ligne est 1,5 à 2,5 km plus basse : son climat y est plus froid, 2 °C au niveau de la mer à 45° contre 10 à 12 °C sur Terre (`Temperature`, 28 − 52 sin²). La végétation suit le climat ; c'est le climat qui s'écarte de la Terre.

**Sur six massifs, les arbres tombent à moitié** (`banc_vegetation.py lisiere`, vue d'aplomb de 20 km, les valeurs exactes de l'altitude et de la saison) :

| Lieu | Saison où les arbres tombent à moitié | Altitude de la ligne ici | Formule seule | Terre |
|---|---|---|---|---|
| 15° S, 120° E | 5,3 °C | 3 870 m | 3 630 m | 4 100 m à 18° S |
| 32° N, 18° E | 6,2 °C | 2 410 m | 2 450 m | 4 200 m à 28° N |
| 40° N, 149° O | 6,3 °C | 290 m | 1 560 m | 3 200 à 3 600 m |
| 40° S, 119° O | 5,8 °C | 1 730 m | 1 650 m | 3 200 à 3 600 m |
| 50° N, 151° E | 5,8 °C | 670 m | 400 m | 1 100 à 2 200 m, de 47 à 61° N |
| 50° S, 91° E | 6,2 °C | 640 m | 480 m | 1 100 à 2 200 m, de 47 à 61° N |

- **La saison à la ligne : 5,3 à 6,3 °C,** dans l'écart de Körner et Paulsen, 6,4 ± 0,7, sauf de 0,4 °C à 15° S.
- **L'altitude varie de lieu en lieu** de plus de 1 km à 40° N : le bruit régional de la température, ±2,5 °C.

### Pas de pop : la part de forêt par pixel en descente

`banc_descente.py`, vue `forest`, d'aplomb, carrés fixes. Planche : `journal/2026-10-25-vegetation-descente.jpg`.

| Lieu, carré | Hauteurs | Part de forêt |
|---|---|---|
| Forêt tempérée, 30,4° N 120,5° E, 2 km | 20, 10, 5, 3, 2 km | 85,4 ; 85,2 ; 85,0 ; 85,1 ; 84,9 % |
| La même, 200 m | 2 km, 1 km, 700, 500, 400, 300, 250, 200 m | 91,5 ; 90,4 ; 89,2 ; 91,4 ; 91,6 ; 90,1 ; 90,9 ; 91,6 % |
| La même, 50 m | 200, 150, 100, 70, 50 m | 94,4 ; 94,3 ; 94,1 ; 93,1 ; 92,1 % |
| Forêt boréale, 49,6° S 90,5° E, 200 m | 2 km, 1 km, 700, 500, 400, 300, 200 m | 91,8 ; 91,5 ; 91,3 ; 90,7 ; 90,6 ; 90,9 ; 93,1 % |
| Savane, 10,4° N 119,5° O, 200 m | 2 km à 200 m | 35,3 à 33,3 % |

- **À ±1,5 point près,** là où les arbres passent de la canopée aux objets, de 700 à 200 m.
- **Avant le raccord booléen,** la canopée retirait la part dessinée en simple soustraction : la forêt perdait 7 à 9 points entre 500 et 300 m.

### Le raccord de la lumière

`banc_vegetation.py raccord` : la même vue, avec les plantes et sans, la canopée au sol partout ; le rapport de la lumière moyenne, linéaire, au milieu de l'écran. Planche : `journal/2026-10-25-vegetation-raccord.jpg`.

| Forêt | D'aplomb, 200 m | À 45°, 200 m |
|---|---|---|
| Tempérée | 1,05 | 1,05 |
| Tropicale | 1,07 | 0,99 |
| Boréale, sur la neige | 0,89 | 0,70 |
| Savane | 1,04 | 1,03 |
| Maquis | 1,02 | 1,01 |

- **Le réglage d'alors,** l'albédo des feuilles des plantes générées, `LEAF_ALBEDO`, est retiré avec elles : `log/recherche-vegetation-historique.md`.
- **Reste :** la forêt boréale vue de biais, 0,70 : ses cônes étroits laissent voir plus de neige à l'ombre que le modèle booléen.

### La lumière vue d'orbite

`banc_vegetation.py orbite` : avec la végétation, sur sans, par biome.

| Toundra | Boréal | Tempéré humide | Tempéré sec | Tropical humide | Savane | Désert |
|---|---|---|---|---|---|---|
| 0,92 | 0,62 | 0,82 | 0,83 | 0,95 | 0,93 | 0,89 |

- **Les forêts assombrissent la planète,** surtout la boréale, posée sur la neige de notre climat.
- **La palette des climats tient déjà les forêts de la Terre :** elle compte deux fois leur ombre là où la planète en pose. La corriger demande le couvert des arbres de la Terre, MODIS VCF, pour en tirer la couleur du sol ouvert : étape à venir.

### Le flottement, le tremblement

- **Aucune plante ne flotte d'un demi-pixel,** sur les quatorze vues de test ; au plus 0,3 pixel. Avant que le tronc ne descende à 15 % de la hauteur entière, quelques plantes naissantes flottaient de 3,4 pixels en montagne.
- **Le tremblement,** `banc_tremblement.py`, avant puis après, avec et sans lissage :

| Vue | Avant | Avec la végétation |
|---|---|---|
| Forêt tempérée, 2 m | 0,01 / 0,08 | 0,00 / 0,03 |
| Forêt tempérée, 150 m | 0,01 / 0,07 | 0,00 / 0,02 |
| Forêt boréale, 150 m | 0,07 / 0,36 | 0,00 / 0,03 |
| Savane, 2 m | 0,00 / 0,01 | 0,00 / 0,00 |
| Crête herbeuse, 1,7 m | 0,02 / 0,13 | 0,00 / 0,02 |

- **Jamais plus qu'avant :** les plantes ne bougent pas, et couvrent le sol qui tremble.

### Le coût, le banc de qualité et l'aspect

Mesurés sur les plantes générées, retirées le 2026-10-30 : `log/recherche-vegetation-historique.md`.

## v2 : où il n'y a pas d'arbres

Le 2026-10-25, sur le verdict de l'utilisateur après l'étape 1. Tests en vol : `tools/tests/2026-10-25-vegetation-v2.txt`. Planches avant et après : `journal/2026-10-25-vegetation-v2-avant-apres-1.jpg` et `-2.jpg` ; les seize vues : `journal/2026-10-25-vegetation-v2-tests.jpg`.

**Le verdict :** des arbres partout, quel que soit le sol ; trop peu d'arbustes ; des arbres sur les crêtes ; des formes trop simples ; des arbres qui sortent trop tard.

**En bref :**
- **Une règle de répartition à deux échelles, comme les cailloux :** un champ régional laisse des régions entières sans arbres ; un champ de taches ouvre des clairières de 30 m à 1 km dans toute forêt. Arbres et arbustes la partagent.
- **Des arbustes par taches,** plus nombreux, en manteau sur presque toutes les lisières, au-dessus de la ligne des arbres.
- **Les crêtes perdent leurs arbres :** 0 à 2 % au-dessus de 300 m sur le sol régional, contre 11 à 83 % en v1 ; les creux en gardent 14 à 80 %.
- **Les arbres sortent à 14 pixels au lieu de 24,** 1,7 fois plus loin, dessinés grossiers au loin ; huit variantes par espèce au lieu de quatre.
- **Le coût du placement des plantes :** 0,6 à 1,6 ms au repos, contre 0,4 à 1,2 ms en v1, pour trois fois plus de surface couverte.

### L'état de l'art, v2

Recherche du 2026-10-25, sources primaires sauf mention.

**Les terres sans arbres et les taches :**
- **Hirota et al. 2011** ([article](https://gael.univ-grenoble-alpes.fr/sites/default/files/Mediatheque/Files/EC2%C2%B0C%20-%20hirota%26al_2011_science.pdf)), MODIS sur 1 km², 35° S à 15° N. La part sans arbres, lue sur la figure 1B : 0,95 à 300 mm, 0,76 à 600, 0,32 à 900, 0,12 à 1 200, 0,05 à 1 500, 0,02 à 0,035 de 1 800 à 2 400 mm. Les tables du supplément n'ont pas pu être lues.
- **Scheffer et al. 2012** ([PMC3535627](https://pmc.ncbi.nlm.nih.gov/articles/PMC3535627)), forêt boréale, 45 à 70° N : des modes stables à 0, 20, 45 et 75 % de couvert ; la toundra au froid, la steppe au sec.
- **Taubert et al. 2018** ([article](https://formind.org/wp-content/uploads/2018/08/Taubert2018_Nature.pdf)) : 130 millions de fragments de forêt ; leurs tailles en loi de puissance d'exposant 1,90 à 1,98, la percolation donne 2,05 ; seuil de percolation à 59 % de forêt. Saravia et al. 2018 ([PMC6288094](https://pmc.ncbi.nlm.nih.gov/articles/PMC6288094)) : 1,90 à 2,01 sur le globe.
- **Asner et al. 2013** : les trouées de l'Amazonie, exposant 1,83 ± 0,09, le même pour tous les types de forêt.

**Le relief :**
- **Broll, Holtmeier et al. 2007** ([Fennia](https://fennia.journal.fi/article/view/3714)) : sur le sol balayé par le vent, la forêt de bouleaux s'éclaircit vers 240 à 300 m ; dans les vallées et sous le vent, des bosquets montent à 370 m. La neige : quelques cm sur les bosses, 1 m et plus dans les creux.
- **Case et Buckley 2015** ([PMC4627911](https://pmc.ncbi.nlm.nih.gov/articles/PMC4627911/)) : 2 189 points de la ligne des arbres ; la plupart 100 à 250 m sous le sommet local ; la courbure est le premier prédicteur.
- **Rita et al. 2023** ([PMC9843241](https://pmc.ncbi.nlm.nih.gov/articles/PMC9843241/)) : l'exposition au soleil change de signe, +78 m dans les Alpes du Sud limitées par le froid, −114 m dans les Apennins limités par l'eau.
- **Serious Sam 4,** Croteam, GDC 2019 ([PDF](https://gpuopen.com/gdc-presentations/2019/gdc-2019-agtd2-4-million-acres-serious-sam-4.pdf)) : la forêt placée par l'altitude, la pente et la convexité, sommet ou vallée.

**Les lisières et les arbustes :**
- **Les guides de lisière** suisses et autrichiens ([canton de Vaud](https://www.vd.ch/fileadmin/user_upload/themes/environnement/forets/fichiers_pdf/Biodiv_Foret/ANNEXE_4_Revitalisation_des_lisieres__final.pdf), [Naturschutzbund](https://naturschutzbund.at/files/NATUR%20VERBINDET/Waldraender-Gestaltung-Pflege_NL4_17.pdf), [WWF](https://www.wwf.ch/sites/default/files/doc-2019-02/2012-10-factsheet-gemeinden-waldraender.pdf)) : ourlet d'herbes de 5 à 10 m, cordon d'arbustes de 5 à 10 m, manteau de 10 à 20 m ; toute la lisière, 25 à 40 m. Des guides, pas des mesures.
- **Au-dessus de la ligne des arbres :** une zone de transition de 300 m et plus en Suisse ; un arbre fait 3 m, le reste est krummholz.
- **Le chaparral** ([USFS](https://fs.usda.gov/psw/publications/4403/On_Estimating.pdf)) : 60 à 100 % de couvert, 1 à 5 m.

**Sortir plus tôt :**
- **Les imposteurs d'Epic** ([Impostor Baker](https://dev.epicgames.com/documentation/en-us/unreal-engine/impostor-baker-plugin-in-unreal-engine)) : 12 × 12 vues en demi-sphère, 8 triangles par carte, trois vues mêlées ; Fortnite les emploie pour tous ses arbres sans Nanite.
- **Serious Sam 4 :** au loin, 2 triangles par arbre, 8 directions, les deux plus proches mêlées ; 16 000 arbres par bloc de 1 km.
- **SpeedTree** ([documentation](https://docs.unity3d.com/speedtree-runtime-sdk/manual/level-of-detail.html)) : les petites branches se réduisent à leur axe au lieu de disparaître ; seul le dernier niveau se fond dans le panneau.
- **Battlefield 3,** GDC 2012 ([PDF](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/gdc12-terrain-in-battlefield3.pdf)) : les instances pendues aux nœuds d'un quadtree, les niveaux grossiers pour les arbres épars vus de loin, les fins pour la densité ; 1 à 4 ms sur PS3.
- **Horizon Zero Dawn :** des empreintes de 6 m pour les arbres, 3 pour les buissons, 1 pour l'herbe ; une carte des arbres qui distingue arbres épars, lisière et cœur de forêt.
- **Non trouvés en sources primaires :** les distances de dessin d'Horizon Forbidden West, Ghost of Tsushima, Far Cry, Red Dead Redemption 2 et Flight Simulator.

**Ce qu'on en retient :** des taches en loi de puissance, ce que donne un champ de bruit fractal coupé à un seuil ; les crêtes nues et les creux boisés par la hauteur sur le sol régional ; le manteau d'arbustes sur la lisière ; pour sortir plus tôt, un niveau grossier de la même forme avant tout imposteur, puis la canopée au sol.

### Ce qui est fait

**Où sont les bois, `WoodsAt` : deux champs de bruit, une seule règle, `Presence`.**
- **La règle :** un champ du bruit de gradient de la planète, au-dessus du seuil qui laisse à un état sa part des terres, relevé ou abaissé de quelques écarts. Ce que le pixel ne montre pas du champ élargit le seuil.
- **Les régions,** champ de 32 km à 8 m : les bois, savane ou forêt, sur la part des terres que leur laisse Hirota ; le reste sans un arbre, quel que soit le sol.
- **Les taches,** champ de 1 km à 8 m, dans les bois seulement : les peuplements sur leur part des bois, le reste en clairières. Au moins un dixième de toute forêt, 30 m à 1 km ; la forêt humide de Hirota y garde 80 % de couvert.
- **Le produit des deux garde la moyenne :** deux champs indépendants, la part des peuplements est celle de l'étape 1. C'est la règle des cailloux, `OBJECT_STONY` puis `OBJECT_PATCHES`.
- **L'arbre ne sort que là :** la passe lourde décide de chaque plante à son pied, la canopée au sol à chaque pixel, la même fonction.

**Les arbustes :**
- **Un champ de taches à eux,** 1 km à 8 m, sur 60 % des terres (`SHRUB_LAND`) : des fourrés et des étendues sans un arbuste.
- **Plus nombreux :** 40 % du sol dans les clairières humides au lieu de 30, 30 % en sous-bois au lieu de 15. Des estimations, à vérifier sur photos.
- **Le manteau des lisières :** là où les peuplements, vus à 32 m, ne sont ni dedans ni dehors, le champ des arbustes est relevé de deux écarts (`FOREST_EDGE`).
- **Le krummholz :** leur limite froide 1,5 °C de saison sous celle des arbres, soit 300 m plus haut.
- **De loin, un fourré est lisse :** le relief des couronnes de la canopée au sol est celui des arbres seuls, pondéré par leur part de la canopée. Les clairières pleines d'arbustes se lisaient comme de la forêt.

**Les crêtes et les creux, `Exposure` :**
- **La hauteur du sol sur le sol régional,** la carte de la planète à 16 km, sur 300 m : −1 dans les creux, +1 sur les crêtes et les sommets.
- **Une crête refroidit la saison de 0,5 °C,** un creux la réchauffe : la ligne des arbres 100 m plus bas sur les bosses, comme Broll.
- **Elle abaisse les deux champs des bois de deux écarts,** un creux les relève : une forêt humide garde un cinquième de ses arbres sur une crête pleine. Une estimation : aucune loi publiée ne donne ce chiffre sous la ligne des arbres.

**Sortir plus tôt :**
- **Les formes, leurs niveaux de détail et leur sortie à 14 pixels,** retirés avec les plantes générées le 2026-10-30 : `log/recherche-vegetation-historique.md`.
- **Le pied au loin sur le sol dessiné :** sous 48 pixels, la plante se pose sur le sol du maillage, qu'elle suit ; de 48 à 64 pixels, son pied glisse vers le sol exact, où il reste de près. Le sol exact, un par plante, était le plus cher du placement : il ne sert plus qu'à un dixième des plantes.
- **Le placement par tuiles** de 4 × 4 cellules : la passe légère écarte la tuile par son milieu avant ses seize cellules ; la lourde décide du climat et des matériaux une fois par tuile, puis de chaque plante.

**Les bancs nouveaux,** `banc_vegetation.py` : `cretes`, les arbres par hauteur sur le sol régional ; `bord`, une clairière près du milieu d'une vue, pour s'y poser ; `krummholz`, un lieu juste au-dessus de la ligne des arbres.

### Mesures

**Les crêtes** (`banc_vegetation.py cretes`, d'aplomb de 20 km, la hauteur sur la moyenne à 16 km, loin sous la ligne des arbres, saison de plus de 8 °C) : la part du sol sous les arbres, entre parenthèses la part du lieu.

| Lieu | Build | Creux, sous −150 m | Entre-deux | Haut, 150 à 300 m | Crête, plus de 300 m |
|---|---|---|---|---|---|
| 15° N 121° E | v1 | 4 % | 4 % | 4 % | 4 % |
| | v2 | 42 % (30 %) | 26 % (19 %) | 7 % (5 %) | 0 % (3 %) |
| 30° N 89° O | v1 | 15 % | 14 % | 13 % | 11 % |
| | v2 | 40 % (27 %) | 15 % (37 %) | 2 % (11 %) | 1 % (4 %) |
| 32° N 19° E | v1 | 75 % | 76 % | 77 % | 83 % |
| | v2 | 80 % (2 %) | 66 % (93 %) | 19 % (5 %) | 2 % (0 %) |
| 15° N 119° O | v1 | 11 % | 10 % | 12 % | 12 % |
| | v2 | 26 % (3 %) | 3 % (89 %) | 0 % (7 %) | 0 % (1 %) |

- **En v1, les arbres ignoraient le relief.** En v2, la crête en garde 0 à 2 %, le creux 14 à 80 %.

**La couverture par biome** (`banc_vegetation.py biomes`), v1 puis v2 :

| Biome | Part des terres | Couvert ligneux | Dont arbres |
|---|---|---|---|
| Toundra et alpin | 26,7 % | 7,9 puis 11,1 % | 7,8 puis 5,6 % |
| Boréal | 13,0 % | 54,0 puis 59,1 % | 51,7 puis 43,8 % |
| Tempéré humide | 14,4 % | 58,8 puis 62,4 % | 58,0 puis 50,3 % |
| Tempéré sec | 10,5 % | 28,7 puis 34,4 % | 15,8 puis 9,9 % |
| Tropical humide | 6,5 % | 55,5 puis 58,5 % | 52,6 puis 43,2 % |
| Savane et tropical sec | 13,1 % | 31,1 puis 37,2 % | 15,3 puis 8,5 % |
| Désert | 15,9 % | 18,2 puis 14,4 % | 3,1 puis 1,2 % |

- **Moins d'arbres, plus d'arbustes :** les clairières, les crêtes nues et les terres sans arbres prennent 7 à 9 points d'arbres ; les arbustes en rendent plus.

**Pas de pop** (`banc_descente.py`, vue `forest`, d'aplomb, carrés fixes) :

| Lieu, carré | Hauteurs | Part de forêt |
|---|---|---|
| Forêt tempérée, 30,4° N 120,5° E, 2 km | 20, 10, 5, 3, 2 km | 86,8 ; 86,1 ; 86,1 ; 86,1 ; 85,9 % |
| La même, 200 m, sur une clairière | 2 km, 1 km, 700, 500, 400, 300, 250, 200 m | 62,0 ; 61,3 ; 62,1 ; 62,1 ; 62,0 ; 62,0 ; 62,1 ; 62,2 % |
| Forêt boréale, 49,6° S 90,5° E, 200 m | 2 km, 1 km, 700, 500, 400, 300, 200 m | 67,9 ; 67,9 ; 67,8 ; 67,5 ; 67,8 ; 67,7 ; 68,6 % |
| Savane, 10,4° N 119,5° O, 200 m | 2 km, 1 km, 500, 300, 200 m | 57,0 ; 57,7 ; 56,8 ; 55,9 ; 55,6 % |

- **À ±1 point près** là où les arbres passent de la canopée aux objets, à ±1,5 en savane.

**Le raccord de la lumière** (`banc_vegetation.py raccord`, avec les plantes sur sans, au milieu de l'écran) :

| Forêt | D'aplomb, 200 m, v1 puis v2 | À 45°, 200 m, v1 puis v2 |
|---|---|---|
| Tempérée | 1,05 puis 0,99 | 1,05 puis 0,98 |
| Tropicale | 1,07 puis 1,14 | 0,99 puis 0,98 |
| Boréale, sur la neige | 0,89 puis 0,93 | 0,70 puis 0,48 |
| Savane | 1,04 puis 1,02 | 1,03 puis 0,99 |
| Maquis | 1,02 puis 0,99 | 1,01 puis 0,98 |

- **La forêt boréale de biais s'assombrit :** ses clairières montrent la neige ; la canopée au sol les laisse voir, les cônes dessinés les cachent. La moyenne de l'image tient à la neige vue, vingt fois plus claire que la forêt.

**Le flottement, le tremblement :**
- **Aucune plante ne flotte d'un demi-pixel** sur les seize vues de test. En montagne, deux flottaient de 0,7 pixel avec le pied exact partout ; aucune avec le pied sur le sol dessiné au loin.
- **Le tremblement,** `banc_tremblement.py`, v1 puis v2, avec et sans lissage :

| Vue | v1 | v2 |
|---|---|---|
| Forêt tempérée, 2 m | 0,00 / 0,01 | 0,01 / 0,05 |
| Forêt tempérée, 150 m | 0,00 / 0,02 | 0,01 / 0,07 |
| Forêt boréale, 150 m | 0,01 / 0,03 | 0,02 / 0,10 |
| Savane, 2 m | 0,00 / 0,00 | 0,00 / 0,00 |
| Vue lointaine, 400 m | 0,00 / 0,03 | 0,01 / 0,05 |

- **Il monte sans lissage, au niveau du sol nu d'avant la végétation,** 0,07 à 0,36 : les plantes lointaines suivent le maillage qui glisse. Avec le lissage, 0,02 au plus.

**Le coût** des plantes générées, v1 contre v2, retiré avec elles : `log/recherche-vegetation-historique.md`.

### Reste après v2

- **Les deux questions posées à l'utilisateur, sans réponse :** réchauffer le climat des latitudes moyennes aux valeurs de la Terre ; retirer la part de forêt de la palette des biomes.
- **La forêt boréale vue de biais :** les conifères dessinés cachent la neige des clairières que la canopée au sol laisse voir ; la lumière, 0,5 à 45°.
- **Les arbustes :** leurs parts et leurs couverts sont des estimations, à caler sur des photos comptées comme les cailloux.
- **Sortir encore plus tôt :** des imposteurs de 6 à 14 pixels, ou un cache des plantes par tuile.

## v3 : les arbres ne poussent plus

Le 2026-10-25, sur le verdict de l'utilisateur après la v2. Tests en vol : `tools/tests/2026-10-25-vegetation-v3.txt`. Planches avant et après : `journal/2026-10-25-vegetation-v3-avant-apres-1.jpg` et `-2.jpg` ; un vol de 1 km à 150 m, image par image : `journal/2026-10-25-vegetation-v3-vol-150m.jpg`.

**Le verdict :** dans les vues comme F3, à 150 m, les arbres semblent pousser à mesure que la caméra avance ; les arbustes sont un peu trop nombreux.

**La cause, deux règles violées :**
- **Un arbre grandissait :** de 14 à 21 pixels de haut, sa taille suivait son fondu, de 0 à sa hauteur.
- **La forêt lointaine était plate :** la canopée au sol, à la hauteur du sol, une hauteur d'arbre sous les cimes. De biais, une hauteur d'arbre fait 14 pixels à la distance du relais : les cimes montaient de 14 pixels en passant de la canopée aux objets.

**En bref :**
- **Un arbre est entier ou absent :** chacun apparaît à sa hauteur, à son propre seuil du fondu. Les dessinés sont la part du fondu, comme la canopée les compte.
- **La canopée a la hauteur de ses arbres :** le rayon de vue traverse leurs couronnes avant le sol ; une lisière se dresse en mur, cache la clairière derrière elle ; les cimes ont la parallaxe de leur hauteur.
- **La hauteur vue de la forêt ne s'effondre plus au-delà des arbres dessinés :** 26 à 37 m jusqu'à 3 km, contre 0 à 4 m en v2 au-delà de 2 km.
- **Arbustes : un cinquième de moins,** buissons du désert bas et gris-vert, plus de taches sombres sur les déserts vus d'orbite.
- **Le coût :** 1 ms de plus pour le sol, le placement inchangé.

### L'état de l'art, v3

Recherche du 2026-10-25, sources primaires sauf mention.

- **Aucune source ne fait pousser les arbres :** le relais échange deux dessins des mêmes arbres, mêmes places, même lumière moyenne, par un fondu d'opacité à taille constante.
  - **SpeedTree** ([documentation](https://docs.unity3d.com/speedtree-runtime-sdk/manual/level-of-detail.html)) : l'arbre 3D s'efface pendant que le panneau apparaît, par alpha-to-coverage ; seules les petites branches rétrécissent, jamais l'arbre.
  - **Unity** ([LOD Group](https://docs.unity3d.com/Manual/class-LODGroup.html)) : fondu croisé ou glissement des sommets ; **Unreal**, fondu tramé.
- **Bruneton et Neyret 2012** ([article](https://web.archive.org/web/20140826014406/http://hal.inria.fr/docs/00/65/01/20/PDF/article.pdf)), la référence la plus proche :
  - une canopée plate « néglige l'épaisseur de la forêt » et fait sauter les silhouettes : ils passent aux objets vers 3 pixels de haut, pas 14 ;
  - les disques de couverture lointains viennent des mêmes graines que les arbres proches : les places se suivent d'un dessin à l'autre ;
  - la lumière des arbres proches est poussée vers la moyenne statistique au relais ; leur figure 7 vérifie que la lumière reste constante avec la distance.
- **Serious Sam 4,** Croteam, GDC 2019 ([PDF](https://gpuopen.com/gdc-presentations/2019/gdc-2019-agtd2-4-million-acres-serious-sam-4.pdf)) : arbres, imposteurs à 2 triangles, puis forêt dans le sol, tous tirés d'un même enregistrement par texel.
- **Flight Simulator 2020** ([SDK](https://docs.flightsimulator.com/html/Content_Configuration/Environment/Vegetation/Species_Definitions.htm)) : des imposteurs octaédriques. **Outerra** ([blog](https://outerra.blogspot.com/2008/08/lots-of-trees.html)) : des panneaux jusqu'à 1 pixel, plus de 500 000 arbres. **X-Plane 12** ([documentation](https://developer.x-plane.com/article/building-custom-3-d-trees/)) : l'arbre 3D jusqu'à 500 m, un panneau au-delà.
- **Horizon Zero Dawn** ([GDC 2017](https://www.guerrilla-games.com/media/News/Files/GDC2017_VanMuijden_GPUBasedProceduralPlacementInHorizonZeroDawn.pdf)) et **Unreal PCG** : le placement est gardé en cache, pas recalculé à chaque image.
- **Mantler et Jeschke 2006** ([article](https://www.cg.tuwien.ac.at/research/publications/2006/Mantler-06-landscape/Mantler-06-landscape-paper.pdf)) : la canopée lancée en rayons dans le pixel, 30 pas ; un coût par pixel.
- **Non trouvés en sources primaires :** les distances de Ghost of Tsushima, Horizon Forbidden West, Far Cry, Red Dead Redemption 2, Star Citizen, Arma, DCS.
- **Ce qu'on en retient :** ne jamais faire grandir ; donner sa hauteur à la forêt lointaine ; idéalement, dessiner au loin les mêmes arbres que de près.

### Ce qui est fait

**Un arbre entier ou absent** (`PlantPlacement.hlsli`) :
- **Chaque plante a son seuil du fondu,** tiré de sa cellule de la grille. Dessinée entière dès que le fondu le dépasse, de 21 à 14 pixels de haut en v3, de 8 à 5 depuis la végétation planétaire ; jamais à moitié.
- **La canopée retire la part dessinée,** la moyenne du fondu, en couche booléenne (`PlantsDrawn`). Le lissage temporel fond chaque apparition en une dizaine d'images.

**La canopée à la hauteur de ses arbres** (`PixelShader.hlsl`, `PlantsDrawn`) :
- **Les couronnes des plantes non dessinées,** chacune de 0,45 de sa hauteur à son sommet ; trois couches à 0,95, 0,75 et 0,55 de la hauteur sous laquelle se tiennent neuf dixièmes d'entre elles, chacune avec sa part des couronnes.
- **Le rayon de vue les traverse avant le sol :** chaque couche prend la part des bois près de son propre pied sur le chemin du rayon. Un seul échantillon de plus, au pied de la couche du milieu, vu à sa distance du pixel ; aucun quand ces pieds tombent dans le pixel.
- **Ce qui en sort :** une lisière se dresse en mur et cache la clairière derrière elle ; le relief des cimes est pris là où le rayon les rencontre, avec leur parallaxe ; la perspective aérienne, à leur distance et non à celle du sol.
- **Leur lumière vue de biais :** les plantes dessinées montrent leurs flancs ombrés ; mesurée sur elles, la canopée garde 1 − 0,2 (1 − sin e)³ de sa lumière à l'élévation e de la vue (`CANOPY_SIDE_LIGHT`) : 1 d'aplomb, 0,85 à 5 degrés.

**Les formes de la v3,** la forme grossière qui ne rétrécit ni n'enfle et le buisson en dôme, retirées avec les plantes générées le 2026-10-30 : `log/recherche-vegetation-historique.md`.

**Les arbustes** (`PlanetSettings.hlsli`) :
- **Un cinquième de moins :** sur 50 % des terres au lieu de 60 ; 35 % du sol dans les clairières humides au lieu de 40, 25 % en sous-bois au lieu de 30.
- **Le gris-vert des terres sèches :** `SHRUB_ALBEDO` moins saturé, une estimation à caler sur photos.

**Les taches sombres des déserts vus d'orbite :**
- **La cause :** la logistique de l'état de forêt laissait 1 % de forêt à 300 mm ; rapporté aux 5 % de bois d'un désert, un cinquième de peuplements. Des taches de 14 % d'arbres sombres sur le sable.
- **La règle :** pas d'état de forêt sous 1 000 mm, où forêt et savane ne sont pas encore bistables (Staver et al. 2011) ; la logistique ramenée à 0 là (`FOREST_RAIN.z`).

**Les bancs nouveaux,** `banc_vegetation.py` : `mouvement`, la caméra avance au-dessus d'une forêt, 41 images de 25 m ; `relais`, la lumière avec et sans les plantes par distance, vue de biais. Les vues `height` et `distance` de `MYPLANETENGINE_VIEW` : la hauteur de la surface vue sur le sol, 0 à 64 m, et sa distance, 0 à 4 km, telles quelles.

**Essayé, pas gardé : les couronnes de chaque arbre lancées dans le pixel,** comme Bruneton et Mantler le recommandent. Les mêmes cellules, tirages et couleurs que les objets, des ellipsoïdes rencontrés cellule par cellule le long du rayon. Rasant, le chemin du rayon dans les couronnes fait des centaines de cellules : 10 ms de plus à F3, et des couronnes encore en bandes. À reprendre avec un cache des plantes par tuile.

### Mesures

**Le vol, banc `mouvement`** : la hauteur vue de la surface, moyenne de toutes les images par bande de distance (m).

| Distance | 150 m, v2 | 150 m, v3 | 400 m, v2 | 400 m, v3 |
|---|---|---|---|---|
| 600 à 800 m | 21,5 | 22,0 | 17,7 | 19,0 |
| 800 m à 1 km | 27,3 | 28,9 | 18,5 | 22,4 |
| 1 à 1,3 km | 29,0 | 34,6 | 14,5 | 25,8 |
| 1,3 à 1,6 km | 26,0 | 35,8 | 13,7 | 29,5 |
| 1,6 à 2 km | 22,0 | 37,2 | 10,1 | 30,9 |
| 2 à 2,5 km | 3,6 | 33,3 | 1,2 | 28,2 |
| 2,5 à 3 km | 0,1 | 26,3 | 0,0 | 25,0 |

- **En v2, la forêt s'effondrait au-delà des arbres dessinés,** à 0 m vers 2,5 km : c'est la pousse vue en vol. En v3, elle garde sa hauteur.
- **Par bande de 20 m de sol, de 450 m à 2,2 km :** la hauteur vue change de 1,92 m d'une image à la suivante contre 2,58 en v2 à 150 m, de 0,97 contre 1,34 à 400 m. Le reste vient du sol lui-même, qui passe des clairières aux bois.
- **La couche reste un peu haute à la mesure :** 33 à 37 m contre 23 à 30 pour les arbres dessinés, dont les pixels voient aussi le bas des couronnes. Sur l'écran, à 2 km, moins de 3 pixels.

**Le relais de lumière, banc `relais`** : la lumière avec les plantes sur sans, par distance.

| Vue | 1 à 1,4 km | 1,4 à 1,8 km | 1,8 à 2,3 km | 2,3 à 3 km |
|---|---|---|---|---|
| F3, 150 m à 20°, v2 | 0,81 | 0,85 | 0,80 | 0,87 |
| F3, v3 | 0,94 | 0,95 | 0,90 | 0,88 |
| 400 m à 8°, v2 | 0,88 | 0,94 | 0,96 | 1,00 |
| 400 m à 8°, v3 | 0,90 | 0,96 | 0,97 | 0,99 |

- **Les arbres dessinés restent 5 à 12 % plus sombres** que la canopée de biais à F3, contre 13 à 20 % en v2.
- **D'aplomb et à 45°** (banc `raccord`) : 0,97 à 1,18, comme en v2 ; la forêt boréale vue de biais, 0,52, ses cônes cachant la neige des clairières.

**Le reste, inchangé ou mieux :**
- **Pas de pop en descente :** la part de forêt à ±1,5 point de 2 km à 200 m.
- **Aucune plante ne flotte** sur les seize vues de test.
- **Le tremblement,** le même qu'en v2 : 0,00 à 0,02 avec lissage.
- **Le coût,** au repos sous la charge d'une autre instance : le rendu 1 ms de plus, 10,1 à 10,9 ms contre 9,2 à 9,9 ; le placement inchangé.
- **Les arbustes,** couvert ligneux moins arbres : −17 % en forêt tempérée humide, −20 % en boréal, −23 % en savane et en terres sèches, −17 % au désert.

### Reste après v3

- **Les deux questions posées à l'utilisateur, sans réponse :** réchauffer le climat des latitudes moyennes ; retirer la part de forêt de la palette des biomes.
- **Les mêmes arbres au loin que de près :** les couronnes de chaque arbre dans le sol, ou des imposteurs, demandent un cache des plantes par tuile.
- **Les arbres dessinés, encore un peu plus sombres de biais** que la canopée : la courbe mesurée est une moyenne de deux forêts sous deux soleils.

## Ce qui reste de l'étape 1

- **Les imposteurs et les formes, faits :** les modèles de jeu, `vegetation-planetaire.md`. Le cache par tuile, en partie : le sol exact gardé d'une image à l'autre, `optimisation.md`, round 3.
- **Le couvert de la Terre par climat,** MODIS VCF, comme la palette des couleurs : la couverture et la couleur du sol ouvert mesurées, plus le comptage double.
- **La saison pour l'herbe aussi :** sa limite froide suit encore la moyenne annuelle, −2 à 6 °C ; la ligne des arbres suit la saison. Une forêt boréale pousse sur un sol nu.
- **Les ombres portées des plantes,** avec l'unification des ombres ; d'ici là, l'ombre statistique du couvert.
- **L'exposition sous le couvert :** le posemètre ignore la canopée ; dedans, la forêt est trop sombre.
- **Plus d'espèces et de formes :** palmiers, bouleaux, acacias en parasol ; des feuilles et des trouées de près, la colonisation de l'espace pour les branches.
- **Le vent,** la litière du sol forestier. Le manteau des lisières et le sous-bois d'arbustes : faits en v2.
- **Le point chaud** de la canopée lointaine (Li et Strahler) : plus claire à contre-soleil, plus sombre face à lui.
