# Principes : corriger par règles, pas au cas par cas

Statut : référence, depuis le 2026-10-22. Toute correction et toute nouvelle fonction s'y conforment ; les specs détaillent, ce fichier tranche.

## Le principe

**On génère une planète entière, à l'échelle réelle, avec une infinité de lieux et de formes. Une correction qui ne vaut que pour la vue signalée ne sert presque à rien, et casse souvent autre chose.**

- **Avant de corriger,** se demander de quelle famille de problèmes le cas signalé est un exemple, et quelle règle il enfreint.
- **Corriger la règle, à l'endroit où tous les cas passent,** pas le cas.
- **Écrire la règle ici,** avec le lien vers la spec qui la détaille.
- **Vérifier sur plusieurs lieux et familles,** pas seulement sur la vue signalée, avec les bancs ci-dessous.
- **Si une correction spécifique est inévitable,** une donnée propre à un matériau ou un réglage calibré, la documenter comme telle, avec sa raison et sa limite.

## Les règles établies

**Un rendu hors temps réel suit l'horloge du film, jamais la durée du calcul** (`lancement.md`, le mode cinématique).
- **Un pas commun à tout ce qui avance :** mer, plantes, verre et historiques ; les poses et l'instant météo viennent du parcours.
- **La sécurité ne dessine pas le trajet :** le générateur garde une bande libre autour du vol ; toute pince du moteur est journalisée.
- **Une caméra extérieure ne déplace pas le vaisseau :** leurs poses restent indépendantes, avec le même rendu et les mêmes ombres que le jeu.
- **Un raccord de segments de vol ne commande pas un arrêt :** position, vitesse et accélération restent continues ; seuls l'atterrissage, la pause et le départ du décollage imposent le repos. La croisière suit la longueur du trajet sécurisé ; l'orbite garde son altitude exponentielle.
- **La marge protège du terrain :** chaque segment peut la préciser ; sur la mer, la hauteur demandée part du niveau 0, avec un minimum de 3 m.

**La géométrie vient du relief d'Exolune,** `Relief.hlsli` (`geometrie.md`).
- **Le rendu ne change pas la forme :** l'apparence des matériaux se travaille en couleurs, textures, normales des pixels, parallaxe et ombres.
- **Toute modification de la géométrie est une surcouche documentée :** filtrage, ajout de détail sous 13,5 m, ou remplacement.
- **Un remplacement est un sujet à part,** sur une piste taguée, jusqu'à décision explicite.

**Ce qu'un point ne peut savoir seul se lit sur une carte de la planète** (`PlanetMap.hlsli`, `Tectonics.hlsli`, `recherche-rivieres.md`, `spec-relief-tectonique.md`).
- **Des cartes sur un cube fixé sur la planète :** la carte de la planète, le relief drainé, d'où viennent le sol régional de la brume, le niveau des cuvettes et le chemin vers la mer ; la carte tectonique, les plaques et leurs frontières.
- **Tout au démarrage, rien en route :** la vitesse n'a pas de limite, on passe d'un lieu à l'autre, d'une planète à l'autre, en une image. Aucune donnée ne se calcule pendant un trajet ni en arrière-plan.
- **Le périmètre est un système solaire :** les cartes de toutes ses planètes et lunes se calculent au démarrage, une fois par graine, puis restent en mémoire ; un cache sur disque par graine peut les garder. Leur budget de temps et de mémoire est celui du système entier.
- **Une planète de la taille de la Terre : moins d'une seconde et de 40 Mo sur le GPU** (`spec-relief-tectonique.md`). Ce que seuls les vues ou le niveau 0 lisent ne monte pas à pleine résolution sur le GPU ; une propagation s'arrête à la portée de ce qu'elle façonne ; ce qui ne dépend pas l'un de l'autre se calcule en même temps.
- **Sur la grille de la planète :** rien n'y dépend de la caméra ; le même lieu donne la même valeur de partout.

**Une carte précalculée peut porter de la géométrie, à trois conditions** (depuis le 2026-10-31 ; elle remplace « de la donnée, jamais de la géométrie », `recherche-relief.md`).
- **Des données planétaires fixes :** calculées une fois par graine, dans le repère de la planète.
- **Lues de façon continue :** sans couture entre les faces du cube, ni marche d'un texel à l'autre. Une carte qui porte une forme ne se lit pas en bilinéaire : la pente y sauterait à chaque texel, et la lumière dessinerait la grille.
- **Limitées aux échelles qu'elles résolvent :** au-dessus de deux de leurs cellules. Le bruit fait le reste, et n'a aucune octave au-dessus.
- **La carte tectonique porte les grandes formes depuis le 2026-10-31,** lue en B-spline cubique, les faces de son cube mêlées près de leurs arêtes ; la carte de la planète reste de la donnée (`spec-relief-tectonique.md`).

**La géologie décide, le bruit détaille** (`spec-relief-tectonique.md`, depuis le 2026-10-31).
- **Toute forme de plus de 50 km vient de la carte tectonique :** aucun bruit du détail n'a d'octave au-dessus.
- **Tout profil analytique a une largeur d'au moins deux mailles :** plus large, sa profondeur baisse d'autant, et le relief garde sa moyenne.
- **Un profil qui franchit la mer filtre sa partie émergée :** elle couvre au moins deux mailles, ou le profil reste sous l'eau ; élargir son seul support ne suffit pas. Le filtre redistribue la hauteur, sans changer l'aire du profil ; aucune forme ne dépend de la maille hors de ce filtrage (`spec-relief-tectonique.md`, les cordons).
- **Chaque profil suit une loi publiée,** citée avec sa source : profondeur océanique par l'âge, flexion de la lithosphère, largeur des plateaux.
- **Un bruit qui déplace une limite se règle en distance :** son amplitude est la pente du champ fois le déplacement voulu. Une côte se découpe ainsi autant sur une plaine plate que contre une cordillère ; réglé en mètres, le même bruit la déplaçait de 30 km sur l'une, de 1 km sur l'autre (`spec-relief-tectonique.md`, les côtes).
- **Une forme lisse suit un champ lisse, jamais le contour d'un champ bruité :** le contour d'un bruit fin a ses angles et ses rias. Un cordon suit le rivage sans les octaves fines du bruit des côtes ni du détail ; sa crête se relève depuis le relief sous lui, entière (`spec-relief-tectonique.md`, les côtes).
- **Un bruit ne se cisaille jamais sur une zone plus étroite que son déplacement :** décalé de 8 km sur 0,6 km de part et d'autre des failles transformantes, le détail s'étirait en tranchées droites, en corniches parallèles et en rangées de dents. Une largeur ne dépend de la maille que pour filtrer au loin.
- **Un profil ne s'arrête jamais net le long de sa frontière :** sa force est lissée le long d'elle et s'effile à ses extrémités ; deux formes voisines se combinent en maximum lissé, jamais en somme ni en coupure.
- **Ce qui se pose sur une forme de la carte se place là où le shader la dessine :** sa place lue dans la carte, puis ramenée par le gauchissement de la lecture de la carte. Sans cela, les volcans d'un arc tombaient jusqu'à 30 km de sa ride (`spec-volcanisme.md`, depuis le 2026-10-31).
- **Une forme posée sur une autre en suit le contour, et sa largeur varie avec ce qui la façonne :** un récif, le sommet arasé d'un guyot suivent le contour de leur volcan ; le platier s'élargit au vent, les passes s'ouvrent sous le vent. Un cercle à part, de largeur constante, faisait des atolls en anneaux (`spec-volcanisme.md`).
- **Un motif posé sur une forme a une moyenne nulle :** il dessine, il ne monte pas la forme. Les coulées d'un volcan, posées en plus de son édifice, traçaient un anneau là où elles commencent ; leurs langues sont au-dessus de lui, le sol entre elles en dessous (`spec-volcanisme.md`).
- **Rien de plus fin que le niveau 0 ne barre un de ses cours d'eau** (étape 4).

**Le climat vient de la géographie, le bruit le détaille** (`spec-climat.md`, depuis le 2026-10-31).
- **La pluie et la température se calculent au démarrage,** sur les grandes formes : les vents des trois cellules, la vapeur portée depuis les mers, la pluie au vent des reliefs. Jamais une bande de latitude imposée : les déserts tombent où la circulation et le relief les laissent.
- **La carte du climat porte ce qui dépasse deux de ses cellules, 100 km ;** un bruit de gradient fait le reste, et ce que le pixel n'en montre pas élargit les limites tracées sur l'humidité.
- **Le climat ne lit que la forme avant érosion :** l'érosion lit la pluie, jamais l'inverse.
- **Les nuages aussi viennent du climat :** leur carte météo se calcule au démarrage sur ses champs et le relief, convection, subsidence, courants froids, rails des dépressions, pentes au vent (`spec-nuages.md`). Aucun champ de nuages tiré d'un bruit sans lien avec la géographie.

**De loin comme de près, la même planète** (`spec-rendu-lointain.md`).
- **Un pixel montre la moyenne de ce qu'il couvre.** Toute limite entre matériaux s'élargit de ce que le pixel ne peut pas montrer de ses entrées : `SpreadStep`, `SlopeShares`, `RockShares`.
- **Un bruit ne s'efface jamais selon la taille du pixel.** Il reste le même à toute distance ; seule sa part invisible élargit les limites.
- **Le relief garde sa hauteur moyenne à toute distance,** quel que soit le filtrage des octaves.
- **Les décisions voient les formes du relief à toute hauteur.** La grille fine porte leur normale tant que le maillage ne porte pas l'octave la plus fine, 13,5 m, sur ses 4 mailles. Éteinte dès des mailles de 20 m, elle laissait les formes de 13,5 à 100 m de la neige et de la roche aller et venir de 2 km à 160 m (`journal-planete.md`, 2026-10-24).
- **Une largeur se décide sur la pente prise à sa propre échelle.** La plage, une hauteur d'eau, se plafonne à 120 m fois la pente prise sur 60 m, `SHORE_BASELINE`. Sur la normale des matériaux, prise à 1 m, les bosses du relief laissaient des kilomètres de plaine côtière en sable. Au loin, la grille fine porte cette pente dès que ses mailles couvrent 60 m ; plus fines, elles ramènent les bosses (`recherche-cotes.md`).
- **Un bruit de couleur se filtre au pixel, jamais à la maille.** Une maille couvre environ 13 pixels : calculé par sommet, ses octaves apparaissent à vue à l'approche, et ce qu'il dessine glisse (`spec-parois-minerales.md`).
- **Tout motif se calcule sur la grille de la planète, jamais relativement à l'ancre.** L'ancre saute de 64 m quand la caméra bouge ; un étirement ou une rotation pris depuis elle redécoupe le motif. Les ravines de `WallRelief` l'enfreignaient ; il est retiré le 2026-10-30.
- **Une grandeur passée d'une passe à l'autre garde la précision de l'échelle où elle sert,** pas celle de sa taille. La distance du terrain sert à l'atmosphère au mètre près et dépasse 30 000 km : en demi-flottant, ses pas de 16 km dessinaient des cercles sur les océans. L'image HDR est en flottants 32 bits. De même, la distance lissée à la frontière, des centaines de km, déplace le bruit des chaînes au mètre près : en flottant, ses pas de quelques cm faisaient des murs au sol ; elle se lit en double (`journal-planete.md`, 2026-10-31). Les petits cônes d'un volcan, jusqu'à 120 km de son sommet, se placent de même en double (`spec-volcanisme.md`).
- **Les photos de référence fixent l'exposition à chaque échelle.** Au sol, celles des paysages, +1 IL ; d'orbite, celles de la Terre, 0 IL ; entre les deux, la part de l'air sous la caméra. Toujours un posemètre incident, jamais la lecture de l'image (`spec-rendu-orbite.md`, `recherche-tons-exposition.md`).
- **Une ombre suit la règle des limites** (`recherche-ombres-relief.md`). L'horizon du relief s'interpole entre les sommets comme un angle ; la part du soleil se prend au pixel, élargie de l'étalement de l'horizon qu'il couvre. Le relief plus fin que la maille garde sa part d'ombre, en moyenne : l'ombrage de Smith, `FinerReliefLit`.
- **Ce qui agit sur l'écran se calcule même hors de l'écran.** Un sommet dont l'ombre peut tomber à l'écran est calculé (`ShadowSweep`) ; sinon les ombres apparaissent quand la caméra tourne.
- **Un bruit ne montre jamais sa grille : bruit de gradient, jamais de valeur.** Un bruit de valeur est plat autour de chaque point de sa grille, et ses octaves, sur des grilles emboîtées, alignent leurs plateaux. De loin, le pixel n'en garde que deux ou trois : ils pavent le sol comme une image basse résolution. Un seul bruit, `Noise3`, pour tous les champs, climat et géologie compris (`journal-planete.md`, 2026-10-24).
- **Les octaves d'un bruit ne partagent jamais les nœuds de leurs grilles.** Un bruit de gradient s'annule à ses nœuds ; sur des grilles emboîtées, toutes les octaves s'y annulent ensemble, et un seuil sur leur somme dessine des rangées de points vues d'orbite. Chaque octave est décalée d'une fraction de maille (`CloudFbm` de l'ancien volume, `log/recherche-nuages-historique.md`).
- **Un volume vu de près se calcule en 3D, pas en champ 2D extrudé.** Les octaves fines d'un champ 2D, dressées en hauteur, font des falaises et des aiguilles. Elles passent en un bruit 3D de même écart-type, dont les mips rendent la moyenne de loin (`ResolvedColumn` de l'ancien volume, `log/recherche-nuages-historique.md`).
- **La formation d'un nuage reste ancrée dans le monde.** À temps figé, sa densité ne dépend pas de la caméra, du maillage ni de l'ancre glissante. Une référence sans historique ni cascades sert à vérifier l'approche avant les optimisations (`log/poc-nuage-stable.md`).
- **Les nuages partagent un temps et un champ météo.** Le vent et les déformations se lisent dans le monde avec cette horloge ; les vues, le nombre d'images et l'identité des formations ne la modifient pas. Une pause météo laisse la caméra libre (`D3DApp.cpp`, `kWeatherWindSpeed` ; `spec-nuages.md`, la météo).
- **Un volume de densité précalculé garde le repère et le temps de sa source.** La caméra ne choisit ni son origine ni sa phase. Si la densité finale dépend du temps, publier le volume complet de ce même temps avant de le lire (`log/poc-nuage-voxel.md`).
- **Les directions combinées doivent appartenir au même repère.** Un soleil exprimé dans la face de terrain doit être transformé avant un calcul avec les positions planétaires ; fournir explicitement caméra et soleil monde aux passes concernées (`log/spike-nuages-voxel-planete.md`).
- **Les passes partagent un contrat GPU explicite.** Réserver une plage de ressources par système ; garder la structure des constantes identique en C++ et HLSL. La météo a ses champs, distincts des indicateurs de végétation et de la mer (`spec-nuages.md`).
- **Le rendu validé est celui de l'exécutable sans variable.** Un code présent mais désactivé ne compte pas ; une variable ne sert qu'aux bancs et aux comparaisons. Une ressource absente arrête le démarrage avec un message, sans retour silencieux à un ancien rendu (`spec-nuages.md`, `lancement.md`).
- **Une optimisation distingue qualité, résolution et cadence de présentation.** Comparer à résolution et paramètres identiques avant d'attribuer un gain ; une capture reste invisible même si le profil de vol demande le plein écran (`execution-optimisee.md`).
- **L'ombre solaire atténue la lumière solaire reçue par la surface.** Conserver séparément le ciel et l'air ; tracer le même volume, au même temps, depuis le récepteur vers le soleil, y compris au-dessus de la mer (`spec-nuages.md`).
- **La couleur, la profondeur et la part solaire décrivent la même surface visible.** Toute passe opaque, y compris les imposteurs et les maillages après HiZ, remplace les deux couleurs avec les mêmes rejets alpha. Une transmission solaire de1 laisse exactement la couleur intacte ; une ombre ne réintroduit jamais l'objet caché derrière (`spec-nuages.md`).
- **Une distance dans une carte n'est pas une distance sur la planète.** Un saut météo global se borne par les frontières sphériques des cellules, avec la marge de filtrage ; le raccord et les pôles font partie du contrat (`spec-nuages.md`).
- **Une enveloppe d'accélération ne dessine pas la forme du volume.** Sa densité s'éteint avant les faces de cette enveloppe ; ses limites visibles viennent de profils locaux continus, pas de la coquille de parcours (`log/spike-nuages-reference.md`).
- **Plusieurs couches se composent dans l'ordre du rayon.** Trier leurs segments avant d'accumuler lumière et transmittance ; sauter le vide entre les couches conserve cet ordre (`log/spike-nuages-cirrus.md`).
- **Une extinction douce se vérifie sur la densité finale, et sa continuité ne valide pas la silhouette.** Le seuil et l’érosion peuvent recouper un dégradé ; même continu, un support presque uniforme peut donner des faces planes opaques. Juger ensemble les champs3D, les hauteurs locales et l’épaisseur optique. Les paramètres géométriques restent mondiaux et indépendants de la caméra (`log/spike-nuages-reference.md`).
- **Prouver le vide exige une borne de présence.** Les niveaux utilisés pour un saut gardent un maximum conservateur et la marge du filtre ; ni une moyenne ni un échantillon nul ne prouvent le vide de l'intervalle (`log/spike-nuages-reference.md`).
- **Un calcul sauté se prouve sans effet.** Une décision sur un seuil s'arrête quand une borne rigoureuse du reste ne peut plus la changer, jamais sur un écart-type ; ce qui ne sert que dans une branche se calcule dans la branche (`optimisation.md`, round 2).
- **Une forme close garde le domaine de ce qu'elle remplace.** Un arrondi peut la sortir de [0, 1] où la boucle ne le pouvait pas : bornée, sinon une racine donne un NaN, des pixels blancs isolés (`optimisation.md`, round 2).
- **Un pixel coûteux se calcule une fois, sur la surface vue.** Le terrain écrit sa profondeur d'abord, sa couleur après le feuillage, en profondeur égale (`optimisation.md`, round 2). Les maillages des plantes de même ; à profondeur égale, la couleur garde le premier dessiné, comme le test strict : elle se dessine dans l'ordre inverse (round 3).
- **Un pixel qui écrit sa profondeur la déclare bornée dès qu'une borne est prouvée.** Sa primitive se pose à la borne, le pixel la promet (`SV_DepthLessEqual`) : le test rejette avant le shader. Les imposteurs prennent la borne de leur test HiZ (`optimisation.md`, round 3).
- **Ce qui ne dépend que d'une cellule de la grille se calcule une fois et se garde.** Le sol exact d'une tuile de plantes se lit d'une image à l'autre, la clé étant la cellule ; une valeur gardée ne diffère de la fraîche que des arrondis de la caméra. Un saut de la caméra l'efface, pour qu'un lieu ne dépende pas de ceux vus avant. Un cache qui déborde coûte plus qu'il ne rend : le mesurer à pleine charge (`optimisation.md`, round 3).
- **Un calcul dont les entrées n'ont pas changé ne se refait pas ; sa clé est exactement ce qu'il lit.** Les constantes que ses shaders lisent, relevées dans leur code compilé, comparées au bit près : ni plus large, ni approché. Une valeur qui ne dépend que d'une partie des entrées se garde quand cette partie est égale : la hauteur d'un sommet ne dépend pas de la vue, seul le tri en dépend. Ce que le tri écarte redevient ce qu'il serait dans le calcul entier. Se vérifie en mouvement contre le calcul entier, au bit près (`optimisation.md`, round 4).
- **Un calcul approché pour le mouvement se compile à part, et ce qui place la caméra reste exact.** Le même code exact, compilé avec du code de plus à côté, change ses derniers bits : le binaire du calcul exact reste celui d'avant. Le sol sous la caméra la place ; au dernier bit près, il déplace toute l'image d'une fraction de pixel et les bords des feuilles basculent. À l'arrêt, tout redevient exact (`optimisation.md`, round 8).
- **Le filtrage transversal ne remplace pas l'intégration le long du rayon.** Un mip adapté au pixel peut encore laisser une interface optiquement épaisse entre deux pas ; raffiner l'intégration de la densité avant de masquer ses bandes par du bruit ou un historique (`log/spike-nuages-reference.md`).
- **Une diffusion multiple isotrope réduit un milieu qui diffuse vers l'avant par la similitude.** Sa diffusion devient `σs (1 − g)` (van de Hulst) : prise entière, la brume renvoyait vers l'orbite trois à cinq fois trop de lumière (`spec-rendu-orbite.md`).
- **La couverture dit la part du ciel couverte, pas l'eau dans le nuage ; l'eau suit le régime, que la carte porte.** La densité des nuages se divise par la couverture, puis suit l'épaisseur de la carte, de 20 /km pour les cumulus épars et les nappes à 80 /km pour les cœurs des fronts : partout à 80 /km, une nappe saturait et perdait toute texture (`spec-nuages.md`).
- **Un champ de nuages a des octaves à toutes les échelles qu'on en voit.** Entre la tuile du bruit, 32 km, et deux texels de la carte, 80 km, il manquait une octave : à couverture partielle, les cumulus se semaient uniformément. Le même volume relu à 128 km la donne (`spec-nuages.md`).
- **La lumière qu'un nuage renvoie dépend de toute son épaisseur et de tout ce qu'il reçoit.** Sa diffusion multiple se cale sur des références Monte-Carlo, vues de dessus et de dessous ; le soleil et le ciel y entrent ensemble, et ses échantillons vers le soleil traversent toute la couche (`spec-rendu-orbite.md`, `tools/calage_orbite.py`).
- **L'épaisseur qui règle la diffusion multiple se lit dans le nuage, lissée à l'échelle de la diffusion, jamais le long d'un seul rayon.** Le long de la vue, un bord rasant s'éteignait en cerne ; le long du soleil, un cœur s'assombrissait ; le long de la normale d'un bruit fin, tout tournait au métal (`spec-rendu-orbite.md`).
- **Ce qu'un bruit ne porte pas sous ses texels reste une variance.** Ses octaves plus fines, extrapolées de la plus fine qu'il porte, élargissent ses bords en franges à toute distance : sans elles, son isosurface lisse se voit comme une surface (`spec-nuages.md`).
- **Un seuil sur plusieurs bruits se moyenne sur leur loi jointe.** Sous l'empreinte d'un pixel, la part couverte et la densité se calculent sur la loi de chaque bruit, son écart type lu par mip ; prise à sa moyenne, l'érosion effaçait tout nuage mince au loin. Dans l'empreinte, les nuages se superposent au maximum ; au-delà, au hasard (`spec-nuages.md`, la statistique au pixel).
- **Le pavage du générateur ne dessine pas les formations.** Un champ de forme visant une distribution sans axes privilégiés ne commence pas par une octave dominante réduite à un unique gradient périodique ; vérifier ses directions et ses mips à la source (`log/spike-nuages-reference.md`).
- **Le LOD d'un volume moyenne sa contribution optique.** Un seuil appliqué à un bruit moyenné ne conserve pas la couverture ; l'exponentielle d'une densité moyenne ne conserve pas la transmittance moyenne. Les approximations statistiques décrivent leur population, leurs paramètres et leurs limites (`log/spike-nuages-reference.md`).
- **Un niveau de détail s'éclaire comme la moyenne de ce qu'il remplace, pas comme une surface.** Ses couleurs se moyennent en linéaire. Une normale moyenne garde sa longueur, la cohérence de ce qu'elle résume : renormalisée, elle prétend à une seule orientation, et l'imposteur s'éclairait comme une carte face à l'œil. La lumière se prend en espérance sur cette dispersion ; le relais vers le détail ne doit changer que le détail (`vegetation-planetaire.md`, l'éclairage des imposteurs).
- **Une quadrature spatiale moyenne des rayons intégrés.** Évaluer chaque échantillon distant sur le même champ de densité fine, puis moyenner lumière prémultipliée et transmittance ; préciser le coût, le support du filtre et ses limites. Un mélange avec le rendu proche conserve ces mêmes grandeurs (`log/spike-nuages-orbite.md`).
- **Un historique se reprojette dans le repère où son contenu est fixe.** Les nuages dans celui de la météo, que le vent tourne ; leur ombre sur le sol. Une distance qu'il garde se rapporte à la caméra courante, sans quoi chaque image reprojette de travers. Ce qu'il transporte se rééchantillonne à chaque image : un compte ou une dérive s'y moyenne, un minimum l'éroderait et un maximum l'étendrait en quelques images (`CloudsTemporal.hlsli`, `optimisation.md`).
- **Ce qu'un historique fournit à un autre calcul, ce calcul doit y être continu.** Une valeur gardée diffère toujours un peu de la valeur fraîche ; si le calcul qui la lit saute ou déplace ses échantillons avec elle, l'écart devient des plaques aux bords nets, là même où ce qu'elle décrit est invisible : la distance d'un nuage presque transparent coupait l'air de la composition en deux moitiés (`optimisation.md`, round 1). Un garde-fou d'image mesure aussi les décalages plats, moyennés sur quelques pixels.
- **Une trace allégée ne vaut que là où l'image n'a pas de détail à l'échelle qu'elle perd.** Sous la porte de la quadrature lointaine, les nuages sont plus grands que le pixel : un pixel entre deux traces en est l'interpolation, à un niveau près. Au-dessus, leur grain est au pixel ; interpolé, il s'adoucit en plaques. Le régime se lit sur l'estimateur, pas sur l'image : décidé pixel par pixel, un raccourci coûte la vague entière (`optimisation.md`, round 7).
- **Un calcul long réservé à quelques pixels épars coûte la passe entière.** Chacun tient sa vague, la passe attend la dernière : quelques dizaines de trouées de ciel tracées dans la résolution des nuages en coûtaient 3 ms. Le cas rare prend la valeur de voisins qui voient la même surface ; à défaut, une valeur neutre pour une image, que le calcul en parallèle remplace (`optimisation.md`, round 8).
- **Chaque correction agit sur son échelle et son champ.** Une organisation de fronts se travaille dans la carte météo ; une déformation des coordonnées du bruit agit sur les nuages individuels. Comparer répartition, recette de densité et filtrage séparément, à temps et positions identiques. Désactiver un LOD ne constitue pas un témoin si la densité fine a aussi changé (`log/spike-nuages-reference.md`).
- **Une référence publiée distingue reproduction et choix locaux.** Conserver les sources, révisions, licences et paramètres des bruits ; nommer les parties non fournies par la publication. Vérifier densité, transmittance et lumière séparément avant de modifier une combinaison ou de la généraliser (`log/spike-nuages-reference.md`).
- **Deux contraintes de niveau se combinent sans coude, et une grille qui se recentre ne tourne pas.** Un `max` sec entre le niveau de l'empreinte et celui de la portée garde la valeur continue mais casse sa pente : le lieu de leur égalité, un cercle autour de la caméra, se dessine. De même, une cascade recentrée sur de nouveaux axes redécoupe la moyenne de chaque texel à chaque pas du vol. Le niveau se combine en maximum lissé (`LevelMax`) ; la cascade se recentre par texels entiers de son propre plan, ses axes transportés (l'ancien volume, tag `piste/nuages`, `log/recherche-nuages-historique.md`).

**L'ombre du relief a une seule source, pour l'air comme pour le sol** (`recherche-rayons.md`, `recherche-ombres-relief.md`).
- **Une seule marche :** vers le soleil, à chaque sommet du maillage, sur les hauteurs de l'image. Elle donne l'horizon, pour le sol, et la hauteur d'ombre, l'altitude sous laquelle la colonne ne voit pas le soleil, pour l'air.
- **Rien ne vient de l'écran :** le maillage garde toute colonne d'air visible, de la mer au plus haut sommet, et tout relief dont l'ombre peut l'atteindre (`ShadowSweep`). Un relief hors champ jette son ombre dans le champ, et tourner la caméra ne change rien.
- **Un pas du rayon de vue montre la part éclairée de sa longueur,** comme il montre la moyenne de l'air qu'il traverse.

**Les matériaux ne dépendent pas de ce que porte le maillage** (`log/spec-relief-reel.md`).
- **Les décisions se prennent sur le terrain seul** et sur la pente entière des textures. Seule la lumière retire la part portée par le maillage.
- **Un effet des textures sur une limite ne s'efface avec la taille du pixel que s'il garde la moyenne,** et n'existe pas là où les matériaux sont filtrés à une cellule, pour le placement des objets : `gHeightBlend`. La hauteur, centrée, déplace la limite dans les deux sens et garde la moyenne. La pente passe par la norme d'un vecteur : ajoutée près du sol, elle changeait la part de neige de plusieurs points, moins sur les pentes douces, plus sur les raides. Elle ne décide plus de la neige.

**Le relief porté par le maillage ne saute jamais d'un sommet à l'autre** (`log/spec-relief-reel.md`).
- **Tout ce qui le décide est continu, et pris à l'échelle de ses formes :** projection triplanaire aux poids continus, normale sur 32 mailles, crêtes jamais plus fines que des mailles de 2 m.
- **Les copies d'une tuile se mêlent sans amplifier les hauteurs.**
- **Les calculs restent précis en simple précision :** pas de soustraction de termes presque égaux ; une série là où il le faut.
- **Le maillage glisse en continu avec la caméra, jamais par pas sur la grille de la planète :** posé par pas, son affinement se verrait, surtout en déplacement rapide. Un gain de calcul ne s'achète pas ainsi (`optimisation.md`, round 4).

**Aucune structure dessinée d'un trait uniforme** (`spec-roche-organique.md`).
- **Strates, fractures, couloirs, rides :** chacun varie le long de lui-même, à plusieurs échelles, en force, en forme et en continuité. Un motif parfaitement régulier se lit comme un dessin.
- **Aucune structure ne s'arrête net :** elle s'amincit ou s'estompe sur quelques fois sa largeur (`spec-texturage-universel.md`).

**Chaque matériau couvre chaque échelle** (`spec-texturage-universel.md`).
- **Un matériau est une pile de bandes, du millimètre au kilomètre, sans trou :** une donnée déclarée, vérifiée par un validateur.
- **Tout pixel de sol appartient à un matériau qui a sa pile :** le reste des sols compris, le sol nu, qui n'en avait pas et passait inaperçu des bancs.
- **Toute bande s'efface par la même règle,** selon sa longueur d'onde et la taille du pixel, quelle que soit sa source : bruit, tuile ou photo.
- **Les bandes prolongent la pente de la photo :** au-dessus de sa tuile, chaque octave porte la pente par octave de la photo, celle que la règle lointaine compte déjà (`STONE_SLOPE_SIGMA`). Plus faibles, elles laissent chaque paroi en tapis égal de sa photo.
- **Une photo garde l'orientation de sa prise de vue :** une photo de paroi va sur les pentes de plus de 45°, une photo prise de dessus sur les plus douces. La limite suit la règle universelle et le bruit des limites, comme celle de la roche. Un matériau qui n'a qu'une photo la garde partout.
- **Une correction est acceptée par le banc de qualité,** sur des lieux tirés au hasard, pas sur la seule vue signalée.

**Un effet optique déplace la lumière, il n'en crée pas** (`recherche-halo.md`).
- **Sur l'image linéaire, avant la courbe de tons, sans seuil :** la lumière totale de l'image ne change pas.
- **Sa force est mesurée :** le halo suit la diffusion d'un objectif réel, pas un goût.
- **Rien de ce que l'œil du spectateur ajoute déjà :** devant l'écran, son propre halo couvre tout ce que l'écran montre.
**La mer : une seule variance de pente, montrée ou perdue** (`recherche-mer.md`).
- **La pente de la mer a toujours la variance de Cox et Munk,** de l'orbite au ras de l'eau : ce que le pixel montre des vagues, chacune sa moyenne sur le pixel, plus ce qu'il en perd, qui élargit le reflet. Le reflet garde sa largeur et sa lumière moyenne à toute hauteur.
- **Les moutons que le pixel ne montre pas sont leur part du pixel,** celle de Monahan ; de près, leur motif garde cette moyenne.
- **Le vent est une carte sur le climat,** et tout en découle : pentes, vagues, moutons.
- **Une seule fonction pour l'eau qui réfléchit,** la mer comme le sable mouillé : `ReflectOnWater` (`Sea.hlsli`).
- **La validation visuelle ne vaut pas calibration physique :** les écarts du noyau FFT à ces lois restent déclarés dans `spec-mer-fft-spike.md`, y compris après son intégration.

**Ce qui bouge de soi-même** (`recherche-mer.md`).
- **Le temps est un paramètre de l'image :** l'horloge en vol, 1/60 s par image en capture, pour que les bancs se répètent ; `MYPLANETENGINE_TIME` le fixe.
- **Une surface qui bouge d'elle-même montre sa moyenne à chaque image, sans lissage temporel de sa lumière :** son passé est ailleurs ; gardé, il étalait le mouvement des vagues. L'histoire physique de l'écume reste dans ses cartes de simulation.
- **Un motif animé peut suivre la caméra, s'il ne saute jamais :** le plan des vagues est porté par la caméra sans tourner, son origine garde le chemin parcouru en double précision. Un point de la mer garde ses vagues, à quelques millimètres près par kilomètre parcouru. C'est l'exception à la grille de la planète, pour un motif qui bouge de toute façon.
- **La normale et l’écume dérivent de la surface effectivement déplacée :** un masque de phase ne suffit pas. Déplacement, pente et compression partagent leur source ; voir `spec-mer-fft-spike.md`.

**L'écran montre la lumière, pas le cadrage** (`recherche-tons-exposition.md`).
- **L'exposition suit la lumière qui tombe, jamais l'image :** celle que reçoit, sous la caméra, une carte tournée vers le soleil. Tourner la caméra ne change rien ; la neige reste blanche, une forêt reste sombre.
- **Une seule courbe, sur le canal le plus fort :** les teintes ne tournent pas. La clarté se règle par l'exposition, avant elle, jamais par un gamma après.
**Un objet a sa place fixe sur la planète** (`spec-objets-proximite.md`).
- **Un objet est le détail du sol, posé :** un caillou, une touffe. La roche en place et son relief relèvent de la géométrie.
- **Sa recette est celle de son sol,** calée sur des photos prises debout, comptées : la loi publiée sert de garde-fou. Un champ propre aux débris décide d'abord s'il y en a.
- **Tout ce qui le fait vient de sa cellule de la grille de la planète :** place, taille, forme, densité. Jamais du maillage glissant, jamais de l'ancre.
- **Il obéit à la gravité, à la forme du sol et aux lois mesurées :** rien au-delà de l'angle de repos ; les blocs s'amassent au pied des vraies parois, quittent les crêtes ; par taches ; les tailles des champs de pierres réels.
- **La caméra décide seulement s'il se voit,** par sa taille à l'écran et la finesse du maillage sous lui ; il sort du sol, sans pop.
- **Son pied est sur le sol exact,** enfoui selon le sol, toujours de plus que l'écart mesuré au sol que dessine le maillage.

**Le vaisseau garde sa forme ; ses détails ont une fonction et suivent l'écoulement** (`spec-vaisseau.md`, `assets/vaisseau/README.md`).
- **Du détail, pas de la masse :** des nacelles et des dérives ajoutées changeaient l'idée du vaisseau.
- **La forme ne change que par décision, sur maquettes :** des volumes en argile à comparer, puis une seule source, `assets/vaisseau/forme_chasseur.py`, que tout le reste suit.
- **Chaque pièce a une fonction lisible,** comme sur un vrai appareil : volet, écope, trappe, feu, tuyère, poignée. Elle tient dans une tôle, à l'écart des autres équipements.
- **Rien ne fait face à l'écoulement en arête vive :** tuyères d'attitude percées dans la peau, carénages profilés, bouts effilés, lèvres arrondies, panneaux presque affleurants. Des blocs posés sur la coque cassaient l'aérodynamisme.

**La végétation suit le climat par des lois publiées** (`recherche-vegetation.md`).
- **La diversité d'aspect reprend les champs du peuplement :** froid, aridité et exposition décident des familles, avec des mélanges continus aux frontières. La graine choisit la forme ; changer de modèle ne déplace pas la plante et n'en crée pas une nouvelle (`arbustes-climatiques.md`).
- **Une représentation simplifiée se juge contre son propre modèle détaillé,** avec les mêmes arbres, poses, tailles et lumière (`log/prototype-vegetation-volumique.md`). Le couvert et les trouées comptent autant que les silhouettes ; des seuils d'opacité communs à tous les arbres ne doivent pas corréler leurs trous.
- **Une seule source pour ce qui pousse,** `Vegetation.hlsli` : les plantes proches et la canopée lointaine la lisent toutes deux.
- **Changer la représentation ne change pas l'identité de la plante :** le maillage et son proxy reprennent la même instance ; le retrait de canopée utilise exactement sa règle de présence à l'écran (`vegetation-planetaire.md`).
- **Filtrer une image découpée conserve sa couverture :** couleur en lumière linéaire et grandeurs pondérées par l'alpha pour les mipmaps. Les imposteurs restent prémultipliés jusqu'au filtrage ; les textures découpées des maillages ont des bords dilatés et des mipmaps réglés pour leur seuil alpha (`vegetation-planetaire.md`).
- **Des couverts superposés se composent par leur transmission :** arbres et arbustes peuvent occuper le même sol ; leur union vaut `1 − (1 − arbres) × (1 − arbustes)`. Leur addition peut dépasser 100 % et produire une lumière négative.
- **L'occlusion du feuillage filtre la lumière qui arrive :** ciel et soleil ont leurs visibilités propres ; ni l'albédo ni l'exposition ne servent à peindre les ombres (`vegetation-planetaire.md`).
- **Une ressource GPU facultative garde une plage d'accès valide :** un branchement peut être aplati par le compilateur. Un SRV racine sans bornes reçoit des données neutres couvrant tous les indices possibles, même quand l'effet est désactivé.
- **Une limite GPU ne choisit jamais les objets par ordre d'arrivée :** la sélection bornée suit un ordre déterministe ; la compaction et le passage entre représentations ne doivent pas faire varier le peuplement à caméra immobile (`vegetation-planetaire.md`).
- **Un rejet d'occlusion doit couvrir toute l'enveloppe effectivement dessinée :** une profondeur de l'image courante, une borne conservatrice et un repli visible pour tout cas incertain. Les listes sources et l'ordre de dessin restent conservés (`vegetation-hiz.md`).
- **Un déplacement de calcul se valide par le temps GPU, pas par le nombre d'instructions :** travail ajouté aux sommets, données transmises et commandes peuvent annuler l'économie au pixel. Comparer sur les mêmes poses, avec le même peuplement et sans charge concurrente (`optimisation-vegetation.md`).
- **Chaque limite est une loi mesurée :** la saison de croissance pour le froid, l'aridité, le plafond de Sankaran et les modes de Hirota pour l'eau ; ses seuils s'élargissent par la règle universelle.
- **Où sont les plantes, une seule règle à deux échelles, comme les cailloux** (`Presence`) : un champ de bruit au-dessus du seuil qui laisse à chaque état sa part. Le champ des régions laisse des régions entières sans arbres, quel que soit le sol ; celui des taches ouvre des clairières dans toute forêt et range les arbustes en fourrés. Deux champs indépendants : le produit garde la moyenne.
- **Les crêtes perdent leurs arbres, les creux les gardent :** la hauteur du sol sur le sol régional refroidit la saison et abaisse les champs des bois. Jamais une règle propre à un massif.
- **Une plante lointaine se pose sur le sol dessiné, une proche sur le sol exact :** au loin, elle suit le sol qu'on voit ; son pied glisse vers le sol exact pendant que sa forme s'affine. Jamais de plante qui flotte au-dessus du maillage.
- **Une plante ne grandit jamais :** entière ou absente, à son propre seuil du fondu ; sa forme grossière couvre l'écran comme la fine. La forêt qu'elle remplace a déjà sa hauteur : la canopée lointaine se tient à la hauteur de ses arbres, le rayon de vue traverse leurs couronnes avant le sol.
- **Ce qui remplace un objet au loin en a la hauteur, la place et la lumière,** mesurées sur l'objet (bancs `relais`, `mouvement`).
- **Une forêt de loin est la canopée du sol, pas des millions d'arbres :** sa part, sa couleur, le relief de ses couronnes, l'ombre qu'elle jette.
- **Ce que les objets dessinent en est retiré en couche booléenne :** 1 − (1 − couverture)^(1 − part dessinée). Retirée en simple soustraction, la forêt perdait 8 points là où les arbres naissent.
- **Ce que la lumière voit sous un couvert vaut pour tout ce qui s'y trouve :** le sol, les cailloux, les touffes, le bas des plantes.

## Les bancs, pour vérifier une règle

- **`tools/banc_qualite.py` :** l'aspect sur des lieux tirés par matériau, de 12 m à 3 km : flou, trous d'échelle, répétition, bandes droites, mutation quand le maillage s'affine. Sa référence : `tools/banc_qualite_reference.json`.
- **`tools/banc_descente.py` :** la part vue de chaque matériau sur un même carré de sol, de 1 500 km à 100 m, avec les vues de diagnostic `MYPLANETENGINE_VIEW`. Une courbe plate, c'est une planète cohérente.
- **`tools/banc_tremblement.py` :** le scintillement à une position exacte, copiée de la barre de titre.
- **`tools/banc_halo.py` :** le halo autour du soleil et de la neige, en lumière linéaire, contre la loi en 1/θ².
- **`tools/banc_tons.py` :** la luminance du sol et du ciel contre les photos ; l'exposition en descente et quand la caméra tourne.
- **`tools/banc_ombres.py` :** la lumière directe du soleil sur un même sol, de 50 km à 200 m, au soleil bas. Sa moyenne ne doit pas bouger : sur un sol rugueux, c'est celle de sa surface moyenne, quel que soit le relief dessiné. La part d'ombre, elle, croît avec lui.
- **`tools/banc_carte.py` :** la carte de la planète vérifiée contre le portage numpy du relief et contre un remplissage écrit à part ; ses lacs et son réseau mesurés contre la Terre.
- **`tools/banc_mer.py` :** le reflet du soleil contre Cox et Munk, pixel par pixel, au vent du pixel ; en descente, le reflet moyen et la part de moutons contre Monahan ; la carte du vent. **`tools/banc_tremblement_mer.py` :** le scintillement hors de la mer quand elle bouge, et le mouvement de la mer avec ou sans lissage.
- **`tools/banc_cretes.py`, `tools/banc_visuel.py`, `tools/realisme.py` :** crêtes, vues à plusieurs hauteurs, distance aux scans réels.
- **`tools/banc_objets.py` :** les objets par sol au regard des photos comptées, l'écart entre leur pied et le sol du maillage le long d'une approche, les surgissements le long d'une descente, et les vues à hauteur d'homme à côté des photos.
- **`tools/banc_vegetation.py` :** la couverture par biome, la ligne des arbres, le raccord de lumière entre plantes et canopée, la lumière vue d'orbite, les vues de test. Avec `banc_descente.py` et la vue `forest` : la part de forêt par pixel, de 20 km au sol.
- **Les bancs rendent sans fenêtre** et ne prennent pas le focus de l'utilisateur.
