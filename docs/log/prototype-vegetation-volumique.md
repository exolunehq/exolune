# Prototype : végétation volumique et imposteurs

**Au log depuis le 2026-10-30 :** prototype clos. La végétation du jeu est celle de `../vegetation-planetaire.md`. Ses mesures restent la référence de comparaison des représentations. Son code, `FoliagePrototype` et ses shaders, ses bancs et son lanceur sont retirés le même jour ; ils restent au tag `jalon/24-vegetation-detaillee-main`.

**Statut : prototype comparé les 2026-10-26 et 27, conservé comme outil de comparaison.** Base `piste/vegetation-foliage-base` ; intégré avec la version planétaire validée, jalon `jalon/24-vegetation-detaillee-main`. Complète `../recherche-vegetation.md`.

**Historique :** `prototype-vegetation-volumique-historique.md` garde les essais remplacés et les mesures intermédiaires.

**Suite planétaire du 2026-10-27 :** `../vegetation-planetaire.md` raccorde ces modèles à la population du moteur pour un premier jugement en vol, sans banc préalable à la demande de l'utilisateur. Les mesures ci-dessous restent celles de la parcelle isolée.

**La question :** conserver des arbres détaillés et leur volume de plus loin, avec une dépense GPU et mémoire mesurée.

**Le choix à comparer :**
- **Référence :** le modèle détaillé texturé, ses feuilles et leurs vrais trous.
- **Imposteur :** des vues précalculées du même modèle, avec couleur, opacité, normales et profondeur.
- **Volume :** une hiérarchie d'agrégats du même modèle, filtrée selon la taille du pixel.
- **Le terrain :** complexplanet reste inchangé.

**Le périmètre :**
- Un composant de rendu isolé dans le moteur DirectX 12.
- Une activation explicite pour le prototype.
- Un arbre seul puis une parcelle déterministe de plusieurs arbres.
- Une ancre fixe sur la planète pour tous les modes et toutes les vues.
- Le rendu HDR, la profondeur, l'atmosphère et le lissage temporel du moteur.
- Une inspiration de Nanite Foliage : le prototype ne reproduit pas tout Nanite.
- Le test isole les agrégats volumiques ; les assemblages de branches et le mouvement squelettique décrits par Epic restent hors périmètre.

**Les données :**
- Deux modèles détaillés de Poly Haven, sous licence CC0.
- Les fichiers sources, leurs URL et leurs empreintes sont conservés par le préparateur.
- Les trois représentations viennent du même arbre source et gardent les mêmes bornes.
- L'import garde les UV et le masque des feuilles.
- Les niveaux de détail ou variantes du fichier source sont identifiés avant la préparation.

**Les règles de comparaison :**
- Mêmes modèles, poses, tailles, graines, nombre d'arbres et lumière.
- Même traitement des ombres dans les trois modes.
- Aucun déplacement du terrain ni réglage de climat pour avantager une vue.
- Les vues couvrent plusieurs lieux, distances, angles et directions du soleil.
- Le jugement visuel regarde les silhouettes, les trouées, la lumière et la stabilité en mouvement.
- Les images rapprochées sont examinées à leur résolution native.
- Les temps viennent de mesures GPU après échauffement.
- Les modes passent successivement, sans essais GPU concurrents.
- Les médianes, p95, effectifs et données brutes accompagnent les résultats.
- La mémoire et les temps de préparation sont distincts du temps par image.
- La référence géométrique reste bornée ; les essais de charge sont identifiés séparément.

**Les vérifications :**
- Compilation du moteur et des shaders.
- Banc de comparaison dédié dans `tools/`.
- Captures sans fenêtre et sans prise de focus.
- Banc de qualité contre `tools/banc_qualite_reference.json` par `--before`.
- Les p95 sont contrôlés contre la référence historique et contre l'état de départ ; les dépassements déjà présents sont explicités.
- Fichier de tests en vol et lancement par `tools/lance.ps1` ou son lanceur dédié.

**L'implémentation :**
- `FoliagePrototype.cpp` et ses shaders isolent les trois rendus.
- Les modèles sont normalisés à 12 m pour comparer leurs représentations à la même taille d'écran.
- Le jacaranda conserve 3 863 832 triangles ; le jeune sapin, 157 402 triangles.
- Les volumes existent en 32³, 64³ et 128³ ; le défaut est 64³.
- La hiérarchie filtre la transmission des enfants ; elle ne somme pas les feuilles cachées comme si elles restaient toutes visibles.
- La normale moyenne et sa dispersion servent à l'éclairage diffus.
- Les normales sont moyennées avant leur orientation vers la vue ; cette approximation peut éclaircir ou assombrir les feuilles.
- L'imposteur comporte 12 azimuts et 5 élévations, avec une pyramide filtrée de couleur, couverture, normale et profondeur.
- Les masques ont leur capture dédiée, avec la profondeur du terrain et sans lissage temporel.
- Les pieds rencontrent le triangle dessiné suivant la droite de leur ancrage planétaire.
- Le placement teste les deux triangles et les mailles voisines, en double précision relative à la caméra.
- L'audit GPU couvre douze cas sur deux lieux, pour 1, 16 et 1 024 instances, de près et de loin.
- Le résidu maximal au plan du triangle reste sous 0,032 mm pour les pieds trouvés ; les cas de 1 et 16 arbres sont tous valides.
- Un cas proche du second lieu ne trouve que 971 pieds sur 1 024 ; le banc de charge annonce donc des instances demandées.
- Le précontrôle refuse tout masque de référence vide avant de calculer la qualité.
- Les séries de temps GPU viennent de deux captures de 60 images après 40 images d'échauffement, soit 120 échantillons par cas.

**Le protocole :**
- RTX 4070 Ti, 12 Go ; pilote NVIDIA 610.88 ; image de 1 280 × 720 pixels.
- La campagne exploratoire compte vingt vues distinctes et quatre petites translations ou rotations.
- Elle couvre deux lieux : 30,37° N, 120,53° E et 0,37° N, 60,53° E.
- Elle compare arbre seul et bosquet de 16 arbres, à 128, 32 et 8 pixels, sous plusieurs angles et lumières.
- Elle utilise trois captures de 120 images après 120 images d'échauffement.
- La campagne finale compare les volumes 64³ et 128³ sur six vues : les deux arbres à 512, 128 et 8 pixels, au premier lieu.
- Les tests de placement couvrent aussi les arbres seuls et les bosquets sur les deux lieux.
- Les échantillons consécutifs ne sont pas des répétitions indépendantes.
- Les temps de dessin sont isolés du placement et du terrain.
- Les images de masque ne servent pas aux mesures de performance.
- Le banc de charge compare les deux représentations simplifiées avec 64, 256 et 1 024 instances demandées, à 300, 400 et 500 m.
- Les modèles sont répétés sur une grille de 13 m ; cela mesure une représentation, pas un peuplement naturel.
- Les campagnes intermédiaires dont une référence avait disparu sont invalidées ; elles ne fondent aucun résultat.

**Les limites du prototype :**
- Deux arbres sources, sans vent ni ombres portées des arbres.
- Les modèles sources utilisent encore des masques alpha pour leurs feuilles ou aiguilles ; tous leurs contours ne sont pas maillés.
- L'éclairage Soleil/ciel est commun, sans ombres propres ni ombres du relief sur les arbres.
- Les cartes de normales, la rugosité et la transmission des feuilles ne sont pas encore exploitées.
- Les modes comparent les représentations pures ; le relais automatique vers le maillage proche reste à construire.
- Le volume utilise une grille dense et une marche dans le pixel, avec une profondeur moyenne pondérée.
- Il échantillonne le voxel le plus proche et un niveau entier ; le passage entre niveaux reste à lisser.
- La référence teste l'alpha bilinéaire à 0,5 ; les préparateurs emploient un test au point pour l'imposteur et un poids continu pour le volume.
- Les écarts de couverture incluent donc le filtrage des masques, au-delà de la seule forme géométrique.
- Les représentations GPU sont stockées sans compression.
- Il n'y a pas de streaming, de sélection de briques éparses ni de réutilisation de branches à l'intérieur d'un arbre.
- Les vues d'imposteur couvrent l'hémisphère supérieur.
- Le mode prototype retire les plantes proches habituelles ; leur compensation dans la canopée du fond reste active.
- Ce fond commun aux trois modes ne constitue donc pas une validation du raccord au peuplement habituel.
- Les mesures d'une parcelle bornée ne prédisent pas le coût d'une planète boisée.

**Reproduire les mesures :**

```powershell
$env:MYPLANETENGINE_SCANS = '<dossier des scans>'
python tools/banc_foliage.py x64/FoliageProto/MyPlanetEngine.exe x64/FoliageComparaison --reduced --masks --volume-res 64 --warmup 40 --samples 60 --repetitions 2
python tools/banc_foliage.py x64/FoliageProto/MyPlanetEngine.exe x64/FoliageSixVues --manifest tools/foliage/results/2026-10-26/manifeste-final.json --masks --volume-res 64 --warmup 40 --samples 60 --repetitions 2
# Refaire cette commande dans un autre dossier avec --volume-res 128 pour l'autre resolution.
python tools/banc_foliage_stress.py x64/FoliageProto/MyPlanetEngine.exe x64/FoliageCharge --volume-res 64 --warmup 40 --samples 60 --repetitions 2
python tools/foliage/foot_audit.py prepare
python tools/foliage/foot_audit.py run --exe x64/FoliageProto/MyPlanetEngine.exe
```

**Juger en vol :**

```powershell
./tools/lance_foliage.ps1 -Mode volume -Model jacaranda -Scene grove
./tools/lance_foliage.ps1 -Mode impostor -Model jacaranda -Scene grove
./tools/lance_foliage.ps1 -Mode reference -Model fir -Scene single
```

- Le lanceur appelle `tools/lance.ps1` et la palette de tests.
- Les positions de la palette sont relevées sur les captures, en altitude absolue.
- Le second lieu utilise `-Tests tools/tests/2026-10-26-vegetation-prototype-tropical.txt -Anchor '0.37 60.53'`.
- Les variables `MYPLANETENGINE_FOLIAGE_COUNT` et `MYPLANETENGINE_FOLIAGE_VOLUME_RES` sélectionnent la charge et la résolution.

**La qualité mesurée :**

| Vue | IoU imposteur | IoU volume 64³ | IoU volume 128³ | Couvert 64³ / référence | Couvert 128³ / référence |
|---|---:|---:|---:|---:|---:|
| Jacaranda, 128 pixels | 0,613 | 0,733 | 0,754 | 1,070 | 1,018 |
| Sapin, 128 pixels | 0,376 | 0,537 | 0,590 | 1,115 | 0,995 |
| Jacaranda, 512 pixels | 0,549 | 0,724 | 0,744 | 1,086 | 1,034 |
| Sapin, 512 pixels | 0,382 | 0,542 | 0,593 | 1,122 | 1,000 |

- L'IoU est l'intersection des masques divisée par leur union ; 1 correspond à la référence.
- Le volume 64³ dépasse l'imposteur sur les six vues ; le 128³ améliore les quatre vues d'au moins 128 pixels.
- À 8 pixels, les références ne comptent que 36 pixels de jacaranda et 7 de sapin ; ces résultats sont très sensibles à l'aliasing.
- La meilleure silhouette ne restitue pas les feuilles individuelles : de près, les deux proxies perdent du détail.
- Dans la vue latérale du jacaranda à 128 pixels, le volume garde environ 0,875 de la luminance de référence sur l'union des masques.
- L'exploration des contre-jours montre un biais de lumière de signe opposé ; un multiplicateur de couleur ne corrigerait pas la règle d'éclairage.
- Les quatre paires de petits mouvements de l'exploration ne suffisent pas à certifier l'absence de scintillement.

![Comparaison aux pixels natifs](../journal/2026-10-27-vegetation-prototype-qualite.png)

**Le coût des représentations :**
- Par espèce sur GPU, sans compression : imposteur 26,214 Mo, volume 64³ 9,587 Mo, volume 128³ 76,696 Mo utiles.
- Ces chiffres excluent les instances et les copies temporaires ; ils ne comparent pas des formats de production compressés.
- À 128 pixels, le jacaranda seul demande 0,380 ms en maillage, 0,008 ms en imposteur, 0,048 ms en volume 64³ et 0,177 ms en 128³, médianes de dessin.
- À 512 pixels, le sapin seul demande 0,030 ms en maillage, 0,104 ms en imposteur et 0,143 ms en volume 64³.
- La simplification n'est donc pas systématiquement plus rapide que le modèle source.
- Le 128³ multiplie la mémoire par huit pour un gain de masque modéré ; il ne convient pas comme résolution uniforme.

**La charge, temps GPU de dessin en ms, médiane / p95 :**

| Modèle | Instances demandées | Imposteur | Volume 64³ |
|---|---:|---:|---:|
| Jacaranda | 64 | 0,046 / 0,056 | 0,228 / 0,275 |
| Jacaranda | 256 | 0,124 / 0,132 | 0,389 / 0,428 |
| Jacaranda | 1 024 | 0,373 / 0,386 | 0,980 / 1,047 |
| Sapin | 64 | 0,024 / 0,035 | 0,114 / 0,144 |
| Sapin | 256 | 0,066 / 0,076 | 0,227 / 0,275 |
| Sapin | 1 024 | 0,209 / 0,222 | 0,467 / 0,518 |

- Chaque ligne et chaque mode comptent 120 images mesurées, réparties en deux captures.
- Le placement est séparé : environ 0,010 ms de médiane dans ces scènes.
- Ce sont des temps de représentation sur des grilles locales ; ils ne prédisent pas le budget d'une forêt mondiale.

**La décision d'architecture :**
- Conserver les modèles importés détaillés pour les vues proches.
- Continuer la piste volumique pour les arbres denses à moyenne et longue distance ; le coût de calcul seul ne l'écarte pas.
- Choisir la représentation par l'erreur de projection et le coût propre à chaque modèle, au lieu d'un seuil unique pour toutes les espèces.
- Corriger d'abord la distribution des normales, la visibilité et la profondeur avant de multiplier les espèces.
- Remplacer ensuite la grille dense par des briques éparses et des parties réutilisées ; construire le relais et le cache de population planétaire.
- Garder les imposteurs comme référence de coût et comme option pour les distances où leur erreur devient acceptable.
- Ces suites ne sont pas implémentées par le prototype.

**Les données :** `../../tools/foliage/results/2026-10-26/README.md` décrit les rapports, leurs empreintes et les sorties brutes locales.

**Le rendu habituel :**
- Le prototype désactivé garde exactement les mêmes mesures sur les 24 lieux repris du banc avant modification.
- Les 2 990 extraits sont identiques pixel par pixel ; aucun p95 ne se dégrade.
- Les captures après modification désactivent le TAA statique ; cette identité des pixels est vérifiée, pas supposée.
- Contre la référence historique, 16 indicateurs de trou ou répétition et 2 de mutation dépassent déjà 10 % avant ce travail.
- Ces 18 dépassements restent identiques après ; la référence canonique est conservée.
- Le détail est dans `../../tools/foliage/results/2026-10-26/qualite.json`.

**Sources techniques :**
- [Nanite Foliage, Epic](https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-foliage).
- [Impostor Baker, Epic](https://dev.epicgames.com/documentation/en-us/unreal-engine/impostor-baker-plugin-in-unreal-engine).
- [Licence des modèles Poly Haven](https://polyhaven.com/license).
