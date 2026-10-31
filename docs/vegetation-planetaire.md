# Végétation détaillée sur la planète

**Statut : version validée en l'état par l'utilisateur le 2026-10-27.**
- Suite de `log/prototype-vegetation-volumique.md`.
- Base `piste/vegetation-planetaire-base`.
- Intégration sur `main`, jalon `jalon/24-vegetation-detaillee-main` ; aucun push demandé.
- Le seuil du banc qualité reste non satisfait ; les écarts sont conservés dans `log/vegetation-planetaire-historique.md` et `arbustes-climatiques.md`.
- Suite différée : `optimisation-vegetation.md`, à aspect, densité et portée conservés.
- Les premiers essais ont été jugés directement en vol ; la demande suivante autorise des itérations comparatives hors écran.
- Les mesures du prototype isolé ne valident pas les performances de cette version planétaire.
- L'historique des premiers vols et corrections est dans `log/vegetation-planetaire-historique.md`.
- Le catalogue de douze arbustes, `arbustes-climatiques.md`, est requis : sans lui, aucune plante. Ses résultats et limites de qualité y sont consignés.
- **Le seul feuillage du moteur depuis le 2026-10-30 :** actif par défaut, ses réglages en dur. Les autres modes, les modèles `photo` et `stylized` et leurs lanceurs sont retirés ; ils sont décrits dans `log/vegetation-planetaire-historique.md`, tag `piste/vegetation-relais-fondu`.

**Le raccord :**
- Le placement existant garde la grille planétaire, les graines, les espèces, le climat et les hauteurs.
- Les modèles de jeu : conifère et feuillu avec branches ramifiées et feuillage découpé.
- La taille du modèle suit la hauteur de chaque instance ; sa largeur suit la couronne prévue par le peuplement.
- Les arbustes gardent leurs instances, tailles sources et règles de présence ; le catalogue climatique remplace l'arbuste unique par douze architectures.
- Le terrain et la règle de présence ne changent pas.
- La fenêtre de placement compte 512 tuiles par octave, contre 184 pour les plantes générées.
- Les plantes sortent à 5–8 pixels, contre 14–21 pour les plantes générées ; la canopée utilise la même règle de retrait.
- La canopée conserve les plantes qui ne sont pas dessinées individuellement, jusqu'à l'orbite.

**Les représentations :**
- Imposteurs multivues au loin ; maillage détaillé de près.
- La représentation se choisit par plante, avec un fondu au relais (`PlanetFoliageMeshShare`, `PlanetFoliageLod.hlsli`) :
  - entre 0,8 et 1,25 fois le seuil de la plante, elle est dans les deux files, imposteur et maillage ;
  - chaque pixel tire l'une ou l'autre selon la part du maillage, par un tramage qui change à chaque image : l'œil le fond, sans grain fixe ; le lanceur de vol coupe l'antialiasing temporel, la touche T le rétablit ;
  - la touche H coupe le fondu en vol et revient à une seule représentation par plante, pour comparer ; en caméra libre seulement, car dans les vues du vaisseau H tourne la tête.
- Le choix dépend de la hauteur et de la largeur d'une couronne cylindrique projetée, à sa profondeur proche.
- Le seuil propre à chaque graine est compris entre 96 et 128 pixels.
- Sans fondu, le passage est un saut net de forme et de lumière ; il était la règle du 2026-10-27 au 2026-10-29.
- La classification et les appels de dessin indirects restent sur GPU, par espèce et représentation.

**Les files et la stabilité :**
- Les tuiles candidates ont un indice fixe ; un calcul de sommes préfixes conserve leur ordre pendant la compaction.
- Les plantes produites par tuile sont compactées dans le même ordre vers les listes proche et lointaine.
- Les limites gardent ainsi un sous-ensemble déterministe, même à caméra immobile ; l'ordre d'arrivée des vagues GPU ne choisit plus les arbres.
- Chaque liste source accepte 262 144 plantes.
- Chaque file du renderer accepte 524 288 instances, soit l'union maximale des deux listes sources.
- Six files regroupent les trois espèces et leurs deux représentations ; leur buffer réserve désormais 192 Mio.
- La bande de relais peut copier une plante dans les deux représentations ; elle ne peut pas saturer une file aval à elle seule.
- Les dépassements des tuiles et des listes de plantes restent signalés.
- Une saturation peut encore réduire le couvert géométrique attendu par la canopée ; le choix reste stable, et la limite reste visible.
- Le stockage temporaire des tuiles et des instances augmente la mémoire ; ce prototype privilégie la stabilité à la compacité.

**Les imposteurs optimisés :**
- Le rectangle est calculé en projection perspective, à partir des quatre plans de vues échantillonnés.
- Le shader lit d'abord la couleur et rejette la transparence avant les normales, profondeurs et visibilités.
- Il est limité à l'ancien carré, avec une marge d'un pixel ; le passage du plan proche garde une couverture conservatrice.
- Deux textures `Texture2DArray` RGBA16F par espèce portent la couleur linéaire et la normale/profondeur.
- Toutes les composantes sont prémultipliées par la couverture avant de construire les mipmaps.
- Le filtrage bilinéaire et le mélange entre mipmaps sont réalisés par le matériel ; les quatre vues angulaires restent mélangées dans le shader.
- Le heap réserve sept SRV par modèle, jusqu'à quatorze modèles : deux pour l'imposteur, trois pour les matériaux du maillage et deux pour les visibilités précalculées.
- Les imposteurs utilisent un seuil alpha fixe de 0,5 ; leurs mipmaps conservent approximativement la couverture par vue.
- Un soutien de silhouette pondéré par les quatre vues protège le noyau opaque ; couleur, normale et profondeur gardent les poids d'origine.
- Les très petits mipmaps quantifient encore la couverture ; la silhouette entre vues reste une approximation.
- La population, les distances et les seuils restent ceux du vol précédent ; les imposteurs reprennent les modèles sélectionnés.
- Compilation et revue statique uniquement ; aucun gain de temps GPU n'est encore mesuré.

**Les modèles de jeu :**
- La cible est un rendu réaliste de jeu AAA, avec des feuilles et rameaux lisibles dans les bouquets et des silhouettes irrégulières.
- Les modèles à bouquets pleins ont été rejetés par l'utilisateur ; leur essai est consigné dans `log/vegetation-planetaire-historique.md`.
- Dossiers `assets/foliage/game_fir` et `assets/foliage/game_broadleaf` ; sources et reproduction dans `assets/foliage/README.md`.
- Pin d'evolveduk, 5 627 triangles ; feuillu Rakshi Games Tree10_1, 3 308 triangles, feuillage détaillé porté par les cartes alpha.
- Arbuste Searsia Lucida f de Poly Haven, 7 232 triangles, branches opaques et feuilles découpées : la source des feuilles et de l'écorce des arbustes climatiques ; crédits dans `../assets/foliage/game_shrub_origins.md`.
- Normales et rugosité du pin importées ; normales Unity du feuillu converties, rugosité constante faute de carte source exploitable.
- La qualité recherchée reste à juger en vol ; ces comptes ne constituent ni une validation AAA ni une mesure des FPS.
- Les imposteurs et les volumes sont reconstruits à partir du maillage sélectionné ; les volumes ne servent plus que hors ligne, au précalcul de la lumière.

**Les textures des maillages proches :**
- Une couche par matériau dans trois tableaux de textures : couleur sRGB, normales et masques UNORM.
- Filtrage matériel anisotrope ×8 avec UV répétées.
- Construction des mipmaps en couleur linéaire, pondération par l'alpha, normales renormalisées et couverture réglée au seuil de 0,5.
- Les couleurs sont propagées dans les texels transparents pour éviter les bordures sombres.
- Les atlas bruts ne vont plus au GPU : leur lecture bilinéaire de repli est retirée le 2026-10-30.

**La lumière et les pieds :**
- Les textures des modèles gardent leur couleur ; soleil, ciel, ombre du relief et couvert environnant participent à la lumière.
- Le maillage proche peut charger `material.bin` : atlas de normales OpenGL, occlusion ambiante, rugosité et transmission.
- Ces cartes ajoutent le détail de l'écorce et des feuilles, une réponse spéculaire modérée et un contrejour foliaire borné.
- Les proxies gardent une normale moyenne ; le détail des cartes de normales n'y est pas reproduit. Les imposteurs s'éclairent sur la dispersion de leurs feuilles (L'éclairage des imposteurs).
- Le maillage proche prolonge le bas du tronc sous le pied, sans modifier la couronne.
- Les proxies gardent leurs bornes ; leur base peut différer pendant le relais.
- Les empreintes alpha réelles ne correspondent pas exactement au disque théorique de chaque couronne.
- La conservation du couvert et de la lumière à l'approche reste à juger.
- Pas de vent ni d'ombres portées précises des arbres ; la normale moyenne du volume reste une approximation.

**Le volume du feuillage :**
- Les variantes dérivées sont reconstruites par `tools/foliage/volume_assets.py`, puis son option `--normals`.
- Les feuilles d'origine sont réparties autour des rameaux porteurs ; les branches, atlas, pivots et bornes sont conservés.
- Les feuillus passent de 3 308 à 7 010 triangles ; les arbustes de 7 232 à 13 406. Le pin reste identique.
- Le nombre d'instances, les graines, les tailles, les seuils de relais et la portée restent inchangés.
- Les normales foliaires sont orientées par bouquets locaux ; aucune enveloppe opaque n'est ajoutée.
- Une variation de teinte stable par graine est bornée à 6 % ; elle s'efface avec la force d'auto-ombrage.
- Le volume alpha 64³ fournit hors ligne seize rayons de ciel et six visibilités axiales du soleil par sommet.
- Le moteur interpole ces données, puis atténue séparément le ciel et le soleil ; il ne lance aucun rayon d'ombre supplémentaire par image.
- Les imposteurs portent les mêmes visibilités dans deux textures RGBA8 ; leur filtrage suit la couverture alpha.
- Les six directions restent une approximation de l'auto-ombrage ; les arbres voisins n'y projettent pas d'ombre précise.
- La force de l'auto-ombrage vaut 0,65, en dur : `VolumeStrength`, `PlanetFoliage.cpp`.
- Un sidecar absent utilise des données neutres dimensionnées pour tous les sommets ; un branchement HLSL ne garantit pas l'absence de lecture spéculative.
- Les couverts des arbres et des arbustes se composent par union pour l'éclairage du sol et des objets ; leur addition produisait parfois une lumière négative.
- Les critères artistiques et les étapes comparées sont dans `log/vegetation-planetaire-historique.md`.

**L'éclairage des imposteurs (2026-10-29) :**
- **Le défaut vu en vol :** au relais, un arbre sombre s'éclairait en devenant maillage. Antérieur à l'optimisation : `242d0f7` et le round 8 donnent la même image immobile.
- **La cause, la normale :** l'imposteur mélange quatre vues cuites et ses mips. La moyenne des normales de feuilles différentes, renormalisée, tourne vers la caméra. L'imposteur s'éclairait comme une carte face à l'œil : sombre en contre-jour et sous un soleil haut devant, clair soleil dans le dos.
- **Ce qui n'y est pour rien,** testé un terme à la fois : spéculaire, occlusion, cartes de normales, transmission, visibilités précalculées, couvert de la canopée.
- **La correction de la lumière :** la longueur de la normale moyenne est la cohérence k des feuilles. Le direct, le contre-jour et le terme sol/ciel prennent l'espérance sur ces feuilles : E[max(0, x)] = E[x]/2 + E|x|/2 ; E[x] suit la normale moyenne, E|x| va de 1/2, feuilles dispersées, à |x|, une seule feuille.
- **Où :** `OutputVolume`, et `Light` pour les pins sans visibilités précalculées, sous `PLANET_FOLIAGE_IMPOSTOR`. Les shaders des maillages compilent au bit près comme avant.
- **La correction de la couleur :** `tools/foliage/bake.py` moyennait ses quatre sous-échantillons en sRGB ; il les moyenne en linéaire. Luminance des imposteurs : feuillu +8,6 %, pin +1,9 %, arbustes +1 %.
- **Recuits** par `python tools/foliage/bake.py --impostor-only --out assets/foliage/climate_shrubs_v2 <modèles>`, la liste complète dans `lancement.md` : normales, alpha et entêtes identiques au bit près. Les `.bin` ne sont pas versionnés ; ceux d'avant sont dans `x64/vegetation_eclairage/imposteurs_avant/`.
- **La mesure :** luminance des mêmes plantes, maillage contre imposteur seul. Au sol, plantes de plus de 300 pixels, 4 lieux, 5 soleils et un lieu sous les cumulus. Au relais, à 25 m du sol, le quart le plus lointain des maillages.

| Rapport maillage / imposteur | avant | couleur seule | couleur et lumière |
|---|---|---|---|
| Au sol, image entière | 0,82 à 1,30 ; 13 % en moyenne | 0,79 à 1,24 ; 11 % | 0,87 à 1,15 ; 7 % |
| Au sol, couronnes | 0,89 à 1,47 ; 18 % | 0,80 à 1,33 ; 12 % | 0,88 à 1,21 ; 9 % |
| Au relais | 0,86 à 2,05 ; 21 % | 0,77 à 1,90 ; 16 % | 0,86 à 1,74 ; 13 % |

- **Ce qui reste :** le maillage reste plus clair de 4 à 26 % sous un soleil haut devant ou rasant, plus sombre de 10 à 14 % soleil dans le dos. Le pire au relais, 1,74, est la lisière en contre-jour, où un grand arbre proche domine la mesure. Cause non trouvée.
- **Le coût :** quelques opérations par pixel d'imposteur, non mesuré au banc.
- **En vol :** `tools/tests/2026-10-29-imposteurs-eclairage.txt`, à juger. Images et mesures : `x64/vegetation_eclairage/`.

**Les comparatifs du jalon 24 :**
- Huit vues hors écran sur quatre biomes et deux soleils ; l'optimisation seule donne un dessin médian de 9,34 à 7,43 ms, huit images identiques bit à bit.
- Le banc de qualité échoue sur 3 p95 sur 59 ; la version est acceptée en l'état avec ces écarts connus.
- Le détail, le banc des forêts retiré et les rapports : `log/vegetation-planetaire-historique.md`.

**Lancement :**
- Le jeu se lance comme le dit `lancement.md` ; le feuillage y est actif par défaut.
- Le catalogue se trouve seul : `MYPLANETENGINE_FOLIAGE_ASSETS` ; sinon le premier construit au-dessus de l'exécutable, celui du dépôt, puis `plantes/climate_shrubs_v2`, publié à côté des dépôts par `tools\plantes.ps1` et trouvé par tous les worktrees, comme les scans.
- Sans catalogue, aucune végétation, ni dessinée ni en canopée : la planète nue, et le titre dit « végétation absente » avec la raison. La canopée seule tient lieu des plantes non dessinées ; partout, vue de sous ses cimes, elle faisait un rideau strié (`journal-planete.md`, 2026-10-31). `MYPLANETENGINE_NO_PLANTS` garde la canopée partout, pour le banc de végétation.
- La palette `tools/tests/2026-10-27-arbustes-climatiques.txt` donne douze vues, par boutons ou F1 à F12 : deux par groupe climatique.
- Le titre indique les FPS, les temps GPU, les comptes de maillages et d'imposteurs par espèce et les dépassements.

**À observer pendant le vol :**
- La lisibilité des feuilles, des branches, des percées et des silhouettes pendant l'approche.
- Les changements de lumière ou de couvert pendant le relais.
- Les pieds, les silhouettes et la stabilité quand la caméra bouge.
- Le coût dans les forêts denses, en vue rasante et au sol.
- Tout dépassement de capacité indiqué par le titre.

**Code :** `PlanetFoliage.cpp/.h`, `PlanetFoliage*.hlsl`, `PlanetPlantPlacement.cpp/.h`, `PlanetPlant*.hlsl`, `PlantPlacement.hlsli`, `Vegetation.hlsli`, `FoliageHiZ.cpp/.h`, `D3DApp.cpp`.
