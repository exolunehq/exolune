# Historique des essais de végétation planétaire

**2026-10-27 : premières variantes en vol.**
- L'hybride volumique est jugé trop coûteux et peu convaincant à distance intermédiaire par l'utilisateur.
- Les imposteurs purs restent des images à toute distance ; leur agrandissement devient visible à l'approche.
- La variante `hybrid-impostor` ajoute le maillage proche avec le même relais que l'hybride volumique.
- Aucun banc ni capture automatique n'est lancé avant ces vols, à la demande de l'utilisateur.

**2026-10-27 : clignotement à caméra immobile.**
- Le premier placement conservait les premiers arrivés par append atomique jusqu'à 65 536 plantes par liste.
- Le renderer imposait encore une limite de 65 536 par espèce et représentation, après réunion des listes.
- Dans le titre de l'application pendant le vol, le placement annonce 87 395 plantes lointaines, au-delà de sa capacité.
- Le renderer annonce aussi 1 134 dépassements dans la file des imposteurs de feuillus.
- Ces troncatures peuvent changer les plantes retenues selon l'ordre des vagues GPU, même sans mouvement de caméra.
- Le masque d'opacité utilise déjà le pixel et la graine stable de la plante ; aucun numéro de frame n'y intervient.
- La correction remplace les sélections saturantes par une compaction déterministe et dimensionne les files aval pour l'union des listes sources.
- Les valeurs relevées viennent du titre existant de l'application ; elles ne constituent pas un banc de performance.

**2026-10-27 : modèles photo, rectangles et filtrage matériel.**
- Le premier raccord utilise le jeune sapin et le jacaranda Poly Haven, même dans les forêts adultes.
- L'utilisateur juge le raccord et la portée satisfaisants, mais les modèles trop photoréalistes et trop détaillés.
- Une première optimisation conserve ces modèles pour isoler les rectangles projetés et les textures filtrées par le matériel.
- La direction choisie ensuite est semi-réaliste stylisée : formes naturelles, feuillage en masses et détails simplifiés.
- Les modèles photo restent sélectionnables par `-Models photo` ; ils ne sont plus le défaut du lanceur.

**2026-10-27 : essai de bouquets pleins, rejeté.**
- `tools/foliage/stylise.py` construit un feuillu de 9 720 triangles et un conifère de 8 174 triangles.
- Le feuillage utilise des volumes opaques lobés, des couleurs douces et des normales lissées, sans feuilles individuelles.
- L'utilisateur voit des boules et juge cette simplification excessive.
- La cible est précisée : arbres réalistes de jeu AAA, feuilles et rameaux crédibles ; les masses se composent de feuillage détaillé.
- `-Models stylized` conserve cet essai ; il n'est plus le défaut du lanceur.
- La baisse du nombre de triangles ne constitue pas une validation visuelle ni une mesure de gain de FPS.

**État présent :** `../vegetation-planetaire.md`.

**2026-10-27 : pointillisme au sol et arbustes pleins.**
- La capture de l'utilisateur montre un feuillu dont le tronc et les contours se désagrègent en points, devant les anciens arbustes en masses.
- Vue : `364.2 10.37168 -119.46971 1.1 89.2` ; le titre de la capture annonce 56 FPS, sans constituer un banc.
- Les imposteurs 128² participaient jusqu'à 512 pixels de hauteur théorique, avec opacité et relais stochastiques.
- Les maillages proches lisaient les atlas au buffer, sans mipmaps ; les arbustes restaient dans l'ancien renderer.
- La correction ajoute un relais plus précoce par plante, un alpha-test stable, les mipmaps et un véritable modèle d'arbuste.
- Aucune mesure ni capture automatique n'a précédé ce nouveau vol, à la demande de l'utilisateur.

**2026-10-27 : volume des feuillus et des arbustes.**
- La demande suivante autorise des itérations hors écran comparées à des photos de forêt, sans viser leur reproduction photographique.
- La boréale sert de témoin ; le manque de feuilles et le dessin filaire concernent surtout les feuillus et les arbustes.
- Deux références de structure et de lumière ont été examinées : [Parkhill, Jim Champion](https://commons.wikimedia.org/wiki/File:Broadleafed_woodland_in_summer,_Parkhill,_New_Forest_-_geograph.org.uk_-_210761.jpg) et [A woodland edge, Evelyn Simak](https://commons.wikimedia.org/wiki/File:A_woodland_edge_-_geograph.org.uk_-_1348876.jpg), sous [CC BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0/). Les originaux locaux et leurs empreintes sont sous `x64/ForetVolumeComparaisons/references/`.
- Critères retenus : bouquets hiérarchisés, feuillage orienté dans plusieurs plans, cœurs ombragés, extrémités éclairées, percées irrégulières ; les petits détails seuls ne donnent pas le volume.
- L'approche d'occlusion précalculée s'appuie sur [Unity, Book of the Dead](https://unity.com/blog/industry/book-of-the-dead-quixel-wind-scene-building-and-content-optimization-tricks) ; l'orientation locale des normales sur [SpeedTree, Card generator](https://docs9.speedtree.com/modeler/doku.php?id=card_generator). Ce projet n'utilise ni Unity ni SpeedTree.
- Série 1 : modèles sources et éclairage d'origine, puis bouquets plus fournis à éclairage identique (`volume_0`). Les couronnes se remplissent, mais les plans restent lisibles.
- Série 2 : même géométrie avec forces d'auto-ombrage 0,65 et 1. La force maximale assombrit davantage les cœurs ; 0,65 garde plus de lisibilité.
- Série 3 : normales foliaires à ancrage local, force 0,65. Géométrie et visibilités identiques à la série 2 ; le modelé progresse sans triangles supplémentaires.
- Ces séries couvrent huit vues sur quatre biomes et deux soleils ; les six comptes sont identiques et les dépassements nuls dans chaque vue.
- Les premières mesures GPU partagent la carte avec une autre application : elles ne permettent pas de conclure à un gain ou à une régression de FPS.
- Le sous-bois noir révèle aussi une erreur préexistante : le couvert lumineux additionne arbres et arbustes, parfois au-delà de 1. La composition par transmission corrige cette règle pour le sol et ses objets.
- Le banc qualité déclenche ensuite un blocage GPU sur son premier site. Le shader compilé lit le buffer de visibilité même sans sidecar ; son tampon neutre de 24 octets ne couvre pas les sommets. Un tampon complet corrige l'accès ; la vue ciblée est de nouveau capturée.
- Les étapes intermédiaires, leurs exécutables et leurs assets sont figés et hachés dans `x64/ForetVolumeComparaisons/`.
- Les 60 vues orthographiques du bake gagnent en moyenne 24,7 % de couverture pour le feuillu et 33,0 % pour l'arbuste, au même rayon et au seuil alpha 0,5. Cela mesure les silhouettes des modèles, pas le couvert planétaire ou les performances.
- La version finale compose le couvert du sol par union ; le sol du sous-bois redevient lisible dans les vues comparées.
- Optimisation retenue : lectures couleur et rejet alpha avant normales, profondeur et visibilité. Huit captures identiques bit à bit avant/après ; médiane du dessin de végétation 9,34 → 7,43 ms et p95 30,26 → 26,73 ms sur cette série de 192 images, sans répétitions indépendantes. Les temps globaux restent variables ; aucun gain de FPS garanti.
- Variante écartée : ignorer les vues de poids exactement nul. Les huit images restent identiques, mais six vues sur huit ralentissent légèrement ; bénéfice global non établi. Le shader retenu garde seulement le rejet transparent précoce.
- La référence qualité réparée termine les 24 sites sans blocage GPU. Elle dépasse déjà quatorze seuils p95 du canonique condensé à 30 sites ; ces écarts ne peuvent pas être attribués à la variante finale. La comparaison appariée utilise ces mêmes 24 sites.
- Le candidat V1 termine aussi les 24 sites sans perte GPU, mais échoue à trois seuils : éboulis/50 m, gap +53,48 % et répétition +14,67 % sur quatre crops ; sol/200 m, gap +19,68 % sur 125 crops. Rapport : `x64/ForetVolumeComparaisons/qualite_finale/comparaison_p95.json`.
- Les coordonnées des crops sont appariées exactement. Les images étiquetées éboulis contiennent une canopée ; celles du sol à 200 m contiennent de minuscules silhouettes végétales. L'analyse CPU voit le feuillage dominer les différences, sans prouver à elle seule une contribution nulle des ombres.
- Les vues de diagnostic rejettent la végétation planétaire, alors que la couleur la dessine ; l'étiquette du crop ne signifie pas que tous ses pixels visibles sont du sol. Le banc et son seuil restent inchangés ; le candidat n'est pas déclaré validé.
- Attribution ciblée : modèles sources, force 0, sol et objets avec union corrigée. Les quatre crops éboulis gardent le p95 gap à 1,49814, contre 1,49811 en référence et 2,29934 avec le candidat. Sur les 60 crops sol des seuls sites 23–24 : 2,11036, contre 2,10876 et 2,75590. L'union seule explique très peu ces écarts ; les nouveaux modèles et leur éclairage restent associés dans ce diagnostic. Rapport : `x64/ForetVolumeComparaisons/attribution_union/rapport.json`.

**2026-10-27 : les comparatifs du jalon 24, sortis de la spec le 2026-10-30.**
- `tools/banc_foret_volume.py` et `tools/foliage/foret_volume_vues.json` fixaient huit vues sur quatre biomes et deux soleils. Retirés le 2026-10-30 : ils visaient l'arbuste unique `game_shrub` et la force d'auto-ombrage réglable.
- Captures cachées, mêmes caméras, shaders et assets hachés ; 8 images de chauffe puis 24 mesures GPU par vue.
- Les photos servent de références de structure et de lumière ; elles ne sont pas des scènes recalées pour une métrique pixel à pixel.
- Les rapports, captures et journaux sont conservés dans `x64/ForetVolumeComparaisons/`.
- Les premières séries partagent le GPU avec une autre application ; leurs temps ne démontrent aucun gain de FPS.
- Sur la série appariée après réparation, l'optimisation seule donne un dessin de végétation médian de 9,34 à 7,43 ms, avec huit images identiques bit à bit ; les temps globaux restent variables.
- Face aux modèles sources, le coût final augmente surtout au cœur des forêts tempérées et tropicales ; ce travail ne constitue pas une validation à 60 FPS.
- Les buffers de représentation passent de 229,49 à 250,62 Mio sur cette comparaison ; files d'instances et mémoire temporaire exclues.
- Le banc qualité accepte `--batch-suns --from-sites <rapport détaillé>` pour reproduire les sites et leur soleil dans un seul processus caché.
- Le rapport condensé `tools/banc_qualite_reference.json` sert à `--before`, et non à `--from-sites`.
- Les deux passes appariées terminent les mêmes 24 sites sans perte GPU ; les binaires et assets restent identiques à leurs empreintes de départ.
- Le critère de qualité échoue sur 3 p95 sur 59 : trou d'échelle des éboulis à 50 m (+53,48 %, 4 crops), répétition des mêmes crops (+14,67 %) et trou d'échelle du sol à 200 m (+19,68 %, 125 crops).
- Ces crops contiennent de la végétation dans la vue couleur, alors que les vues de diagnostic la rejettent ; leur nom de matériau n'isole donc pas le sol réellement visible. Les mesures sont conservées, sans changement de métrique.
- Le canonique à 30 sites présente quatorze dépassements dans la référence à 24 sites comme dans le candidat ; les lieux différents ne permettent pas d'en attribuer la cause à cette itération.
- La version est acceptée en l'état par décision utilisateur, avec ces écarts connus ; le seuil automatique reste non satisfait. Détails : `x64/ForetVolumeComparaisons/qualite_finale/comparaison_p95.json`.

**2026-10-30 : les modes, les modèles et le lanceur retirés du moteur.**
- **Retirés par le commit `3a4508a` ;** ils restent au tag `piste/vegetation-relais-fondu`. Le feuillage du jeu reste seul, actif par défaut.
- **Les représentations retirées :** `hybrid`, volume 64³ au loin et maillage de près ; `volume`, volumes seuls, pour isoler leur comportement ; `impostor`, imposteurs seuls, pour comparer le coût. Les volumes utilisaient la projection des huit coins de leur boîte. Les deux variantes hybrides partageaient le même choix par plante.
- **Les modèles retirés :** `-Models photo` gardait le jeune sapin et le jacaranda importés pour comparaison ; `-Models stylized`, l'essai de couronnes pleines. Leurs arbres gardaient le masque complémentaire historique à 384–512 pixels, et leurs imposteurs un alpha stochastique. L'arbuste utilisait le même renderer dans les trois jeux de modèles.
- **Sans catalogue,** le Searsia Lucida restait l'arbuste unique ; `-Assets assets/foliage/volume_look_normals` le retrouvait. Le catalogue est désormais requis.
- **Le repli bilinéaire des maillages** lisait les atlas bruts, chargés sur GPU pour lui seul ; le chemin actif filtrait déjà par le matériel.
- **La force d'auto-ombrage** se réglait par `MYPLANETENGINE_FOLIAGE_VOLUME`, de 0 à 1 ; 0 retrouvait l'éclairage historique pour la même géométrie.
- **Le lancement retiré :**

```powershell
./tools/lance_planet_foliage.ps1 -Mode hybrid-impostor -Models game
```

- Exécutable courant : `x64/FoliageShrubs/MyPlanetEngine.exe` ; le précédent reste sous `x64/FoliagePlanet/`.
- Le lanceur utilise `tools/lance.ps1` et démarre près de la vue signalée, à 1,6 m du sol ; le cap tronqué de la capture est supposé à −115°.
- `-Position` accepte cinq valeurs : altitude absolue, latitude, longitude, inclinaison et cap, pour reprendre un vol.
- `-Sun` accepte la latitude et la longitude du soleil ; par défaut, `20 120`.
- `MYPLANETENGINE_PLANET_FOLIAGE` active le raccord ; sans cette variable, la végétation habituelle reste utilisée.
- Le prototype isolé et le mode planétaire ne peuvent pas être activés ensemble.
- `-Mode hybrid-impostor` est le défaut du lanceur ; `-Mode hybrid` conserve le relais vers les volumes.
- `-Mode volume` et `-Mode impostor` restent des représentations pures, y compris de près.
- `-Models game` est le défaut du lanceur ; `-Models photo` retrouve les arbres du prototype précédent.
- `-Assets` choisit explicitement le dossier des trois espèces ; le moteur ne cherche pas de variante dans ses sous-dossiers.
- `-Volume` choisit la force d'auto-ombrage ; elle figure aussi dans le titre et les statistiques.
- `MYPLANETENGINE_PLANET_FOLIAGE_MODELS=game` choisit les nouveaux modèles ; absente, cette variable garde les modèles photo.
- Les palettes `2026-10-27-vegetation-volume.txt` et `2026-10-27-vegetation-planetaire.txt` restent disponibles par `-Tests`.
- Le titre indique le jeu de modèles, les FPS, les temps GPU et les comptes de maillages et proxies.
- **Les outils retirés avec eux :** `tools/foliage/telecharge.ps1` et `sources.json`, qui téléchargeaient les modèles photo ; `tools/foliage/stylise.py`, qui construisait les stylisés ; l'import des modèles photo de `tools/foliage/importe.py`.
