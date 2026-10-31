# Optimisation du rendu de vol

**L'objectif :** 60 images par seconde au minimum en 1920×1080, 120 visées, à qualité perçue conservée. Départ le 2026-10-28 sur la branche `optimisation`, issue de `main` et du profil d'exécution optimisée (`execution-optimisee.md`).

## Le banc

**`tools/banc_perf.py` fait foi pour le temps.**
- **La configuration de vol :** le jeu, l'exe sans variable : nuages planétaires, mer FFT, végétation détaillée avec HiZ, sans TAA ni halo, coupés par défaut (`lancement.md`).
- **Huit vues,** du sol en forêt à 2 m jusqu'au globe à 10 000 km : `foret_sol`, `lisiere`, `montagne`, `mer`, `survol`, `cumulus`, `orbite`, `globe`.
- **1920×1080, VSync coupée, sans fenêtre.** Chaque vue donne le temps GPU de chaque passe, moyenné sur 120 images (`<capture>.perf`, `D3DApp::ReadGpuTimes`).
- **La garde de qualité :** `--before <perf.json>` compare chaque image à la précédente : écart moyen en niveaux 8 bits, part des pixels qui bougent de plus de 8 niveaux.
- **Le banc est déterministe :** deux passes donnent des images identiques au bit près. Le temps varie de 5 %, jusqu'à 10 % ; un gain se juge au-delà.
- **Construire d'abord :** `tools/lance.ps1 -Build -NoLaunch`. Un banc à la fois : le GPU est ce qu'on mesure.
- **La qualité du terrain** reste jugée par `tools/banc_qualite.py` ; ce qui se voit en mouvement, en vol (`tools/lance.ps1`).
- **La colonne `nuages_trace`** isole la trace des nuages dans la passe de l'atmosphère.
- **La colonne `terrain_dessin`** additionne la profondeur du terrain et sa couleur, dessinée après le feuillage (round 2).
- **Les colonnes `objets_place` et `plantes_place` se chevauchent :** aucune barrière entre les objets et le tri des tuiles de plantes ; on juge leur somme.
- **`--views a,b` :** un sous-ensemble des vues, pour itérer vite. Les images d'un sous-ensemble ne se comparent qu'à un sous-ensemble identique : la tuile 4×4 de chaque vue dépend des images rendues avant elle.
- **`cumulus_sol`** (round 7) : 150 m au-dessus d'une forêt, des cumulus dans le ciel ; le vol rapide entre le sol et les nuages.
- **Les options :** `--full` garde la passe unique des nuages en pleine résolution ; `--weather <s>` fixe le temps météo.
- **La cadence réelle** (round 5) : après les passes du GPU, l'image du CPU, en ms. `cpu_prep` la préparation, `cpu_liste` l'enregistrement, `cpu_present` la soumission et la présentation, `cpu_attente` l'attente du GPU ; `cadence` le temps d'une présentation à la suivante, ce que l'œil reçoit ; `gpu_inactif` le GPU inoccupé entre deux images, par ses horodatages. La colonne `réel` du tableau est la cadence en fps ; `fps` reste celle du temps GPU.
- **Le banc de mouvement :** `--motion "<cap °> <latitude °> <météo s>"`, par image. La caméra rejoint chaque vue à la capture en tournant et en volant vers le nord ; la météo court jusqu'à son temps. Comparé à un banc immobile, il montre ce qu'une passe temporelle perd en mouvement.

## La référence

**RTX 4070 Ti, commit `242d0f7`, ms GPU par image.** Le CPU attend le GPU à chaque image : le temps GPU fait la cadence.

| Vue | Atmosphère et nuages | Terrain, dessin | Feuillage, dessin | Plantes, placement | Terrain, calcul | Total | fps |
|---|---|---|---|---|---|---|---|
| foret_sol | 13,1 | 12,6 | 9,9 | 7,1 | 4,2 | 48,8 | 21 |
| lisiere | 19,0 | 11,2 | 9,4 | 7,2 | 4,2 | 53,0 | 19 |
| montagne | 14,3 | 16,3 | 3,7 | 8,3 | 3,2 | 47,6 | 21 |
| mer | 41,2 | 1,1 | 0,1 | 0,8 | 2,1 | 46,0 | 22 |
| survol | 9,7 | 11,6 | 1,8 | 4,9 | 1,4 | 30,0 | 33 |
| cumulus | 26,7 | 1,2 | 0,1 | 0 | 0,6 | 29,0 | 34 |
| orbite | 51,2 | 5,0 | 0,1 | 0 | 0,5 | 57,3 | 17 |
| globe | 45,5 | 2,1 | 0,1 | 0 | 1,2 | 49,4 | 20 |

**Les budgets :** 16,7 ms pour 60 fps, 8,3 ms pour 120.

**L'analyse de départ de la passe des nuages,** coût par part : `log/optimisation-historique.md`.

## Les rounds

**Un round par poste, du plus lourd au plus léger, l'un après l'autre.** Chacun : mesure, changement, banc avant et après, garde de qualité ; ce qui se voit en mouvement passe en vol.

1. **Nuages et atmosphère, fait :** une trace par tuile 4×4 en pleine résolution, reprojetée dans le monde ; la quadrature lointaine étalée dans le temps ; l'ombre au sol amortie de même, sans carte d'ombre (Les résultats).
2. **Le dessin du terrain, fait :** sa profondeur d'abord, sa couleur une fois par pixel montré ; le shader ne calcule plus ce qui ne change rien (Les résultats).
3. **La végétation, fait :** le sol exact des tuiles gardé d'une image à l'autre ; les imposteurs en profondeur conservatrice ; les maillages proches en profondeur d'abord (Les résultats).
4. **Le calcul du terrain, fait :** gardé tant que ses entrées sont celles de l'image précédente ; en vol, il reste refait en entier (Les résultats).
5. **Plusieurs images en vol, mesuré et arrêté :** le GPU n'attend le CPU que 0,6 à 1,2 ms par image ; sous le seuil, aucune refonte (Les résultats).
6. **Les nuages en mouvement, mis de côté :** chaque trace fraîche vérifiait l'historique reprojeté ; traînées, bruit et plongée corrigés, mais 4 à 6 ms de plus en vol lent en altitude. Au tag `piste/optimisation-r6-nuages-mouvement` (`016d9c7`), pour référence ; ses bancs `x64/r6_avant_*` et `x64/r6_full_*` servent au round 7.
7. **Les nuages en vol rapide, fait :** sous 14 km, les pixels dont l'historique a glissé se rebâtissent d'un pixel tracé par carré 2×2 ; au-dessus, rien ne change (Les résultats).
8. **Le sol en vol rapide, fait :** les trouées de ciel dans les feuilles remplies par l'historique au lieu d'être tracées par la résolution des nuages ; en vol, la grille du terrain en paires de floats ; forêt de 49 à 60 fps réels, lisière de 43 à 55, montagne de 48 à 54 (Les résultats).

## Les résultats

### Round 1 : nuages et atmosphère (2026-10-28)

**La passe tombe de 10 à 51 ms à 1,2 à 4,6 ms ; l'image immobile reste celle de la référence.** Banc `x64/banc_perf_round1`, ms GPU.

| Vue | Atmosphère, avant | Atmosphère, après | dont trace | Total, avant | Total, après | fps |
|---|---|---|---|---|---|---|
| foret_sol | 13,1 | 1,6 | 1,1 | 48,8 | 37,0 | 27 |
| lisiere | 19,0 | 3,1 | 2,6 | 53,0 | 36,5 | 27 |
| montagne | 14,3 | 2,0 | 1,4 | 47,6 | 35,5 | 28 |
| mer | 41,2 | 4,6 | 4,0 | 46,0 | 9,3 | 108 |
| survol | 9,7 | 1,2 | 0,7 | 30,0 | 21,4 | 47 |
| cumulus | 26,7 | 3,0 | 2,5 | 29,0 | 5,2 | 192 |
| orbite | 51,2 | 2,6 | 2,0 | 57,3 | 8,5 | 118 |
| globe | 45,5 | 1,4 | 1,0 | 49,4 | 4,8 | 208 |

**La garde de qualité :** écart moyen de 0 à 0,65 niveau ; aucun pixel au-delà de 8 niveaux, sauf 0,8 % au globe, dans le grain des nuages au bord du disque. Les autres passes ne bougent pas.

**La passe temporelle** (`CloudsTemporal.hlsli`, `D3DApp::Draw`) :
- **Chaque image trace un pixel par tuile 4×4,** en pleine résolution : 1/16 des rayons. Tout pixel a sa trace en 16 images ; l'image immobile converge vers la trace de chaque pixel.
- **La résolution, en pleine résolution,** reprend les autres pixels de l'historique et compose l'air.
- **L'historique se reprojette dans le repère où son contenu est fixe :** les nuages dans celui de la météo, que le vent tourne ; leur ombre au sol, sur le sol. Les nuages à leur distance pondérée, lue dans l'historique puis au point retrouvé.
- **Le rejet :** la fin de rayon, surface ou ciel, doit concorder. Sinon, le pixel prend les tuiles fraîches voisines qui voient la même surface, la plus proche des 5×5 au besoin, comme le ciel entre des feuilles : bandes minces, aux bords de l'écran ou autour de ce qui bouge. Ce remplissage part avec les trois quarts de la dérive permise : en mouvement, la trace le remplace vite. Devant la couche, il n'y a rien à tracer : le relief proche découpe les nuages net.
- **La distance des nuages se garde depuis la caméra courante.** L'historique la stocke depuis la caméra précédente : le point à cette distance de l'une est à une autre distance de l'autre, d'autant que la caméra a avancé le long de la vue. Sans cette correction, la distance gardée datait de la trace, jusqu'à 16 images : à 2 km par image en orbite, 10 % d'erreur, et chaque image reprojetait de travers, en traînées.
- **La dérive :** un volume n'est pas à une seule distance. La trace mesure l'écart type de la distance d'où vient sa lumière ; à chaque image, sa reprojection devant et derrière mesure ce que l'historique a pu glisser, et le changement de distance compte aussi, 20 % valant la dérive permise. La dérive s'accumule jusqu'à la trace suivante ; une visite n'en renouvelle que sa part de la moyenne lointaine.
- **Au-delà d'1 pixel de dérive, ou quand la direction d'où l'on voit un nuage tourne de plus d'1° en une image, la résolution trace le pixel elle-même,** comme la passe unique. Un remplissage par les tuiles fraîches n'irait pas : il lisse le grain des nuages lointains en plaques pâles et plates, celles vues en vol. En vol ordinaire, rien ne se retrace ; au-delà de x5 en orbite, la passe coûte la passe unique.
- **Le rééchantillonnage :** Catmull-Rom, borné par les quatre texels voisins ; aux bords d'une surface, bilinéaire parmi les texels qui la voient. L'écart type et la dérive sont dans une image à part, en demi-flottants : rien n'est empaqueté, l'image immobile reste exacte.
- **La quadrature lointaine s'étale dans le temps :** un rayon fin par visite, à l'une des quatre positions du 2×2 (neuf en référence) ; l'historique en moyenne jusqu'à huit, image immobile, deux en mouvement, ses rayons pris d'ailleurs. Même estimateur : lumière prémultipliée et transmittance moyennées. Les rayons proches remplacent l'historique ; un pixel retracé prend les quatre rayons d'un coup.
- **L'historique repart** à chaque saut de la caméra, au changement de référence, à l'allumage des nuages, et quand le soleil bouge de plus d'un degré.

**Dans la trace :**
- **Un seul site d'appel de la marche par pixel :** le rayon central si le poids lointain est sous 1, un rayon fin s'il est positif. Le code des rayons lointains pesait sur les registres de tous les pixels : 10 à 20 % partout.
- **Le pas borne l'altitude parcourue, pas la longueur :** au plus 240 m d'altitude par pas, la moitié de l'empreinte le long du rayon. Les rayons rasants du globe passent de 4,2 à 1,0 ms ; les rayons verticaux ne changent pas.
- **Les quatre échantillons vers le soleil sont déroulés,** et dans un nuage la forme et l'érosion se lisent avec la météo : la marche attend deux lectures par pas au lieu de quatre. Résultat identique au bit près.
- **Le saut de vide prend le seuil même de la densité :** couverture basse au plus 0,03 dans les mips maximum, au lieu de 0. C'est toujours une preuve.

**Dans la composition :**
- **L'air en simple précision,** depuis l'altitude de la caméra le long du rayon (`HeightAlong`) : les doubles coûtaient 1,5 à 2,5 ms, plus que l'air lui-même.
- **24 pas d'air vers le ciel, 12 vers une surface,** comme la passe de l'atmosphère, répartis sur l'air que la vue traverse. Le nuage ne coupe que le pas où il se trouve, en deux : les autres gardent les échantillons d'une marche unique, pour un pas de plus.
- **L'air est ainsi continu dans la distance du nuage.** Avant, un nuage partageait les pas en deux moitiés : un nuage invisible faisait passer de 12 pas à 6 + 6, et la distance déplaçait tous les échantillons. La passe temporelle reprojette une distance plus ancienne : sur le continent, sous des nuages à peine visibles, l'air changeait par régions aux bords nets, une « seconde peau » vue en vol à 160 km. À 160 km en vol rapide, les plaques passent de 18 % à 3 % de l'image ; la passe unique change de moins de 0,3 niveau, le banc de qualité pas du tout.

**Ce qui borne encore :**
- **La trace est limitée par la latence, pas par le nombre de rayons.** Une tuile 8×4, deux fois moins de rayons, ne gagne que 17 % en mer et rien au cumulus : chaque rayon enchaîne ses lectures de texture.
- **La mer reste à 4,6 ms.** Ses rayons rasants marchent 150 km de couche basse au pas de 48 m, sans rien y trouver de visible. Ce vide vient du profil et de l'érosion, que les mips de la météo ne bornent pas : aucun saut n'y est prouvable.
- **En mouvement, un pixel attend sa trace jusqu'à 16 images, tant que l'historique tient.** Les zones découvertes passent par le remplissage ; au globe, le grain de la quadrature se lisse au lieu de scintiller.
- **Au-delà de x5 en orbite, la passe coûte la passe unique, de 10 à 38 ms :** la direction d'où l'on voit chaque nuage tourne de 3° par image, et un volume vu d'ailleurs montre d'autres faces ; aucune reprojection ne le rattrape. Retracer en ordre dispersé coûte autant que tout retracer ; un budget de 15° ne gagne presque rien.
- **La plongée très rapide garde des erreurs.** Plongée de 1,5 % de la hauteur par image depuis 36 fois la hauteur : en orbite et au globe, l'écart se réduit de moitié ; à 440 km vers l'horizon, une bande de nuages reste fausse. Sa distance gardée y est fausse du double, et dérive, rotation et distance, toutes calculées depuis elle, ne le voient pas ; il faudrait vérifier la distance contre les traces fraîches.
- **Très vite, les nuages s'adoucissent,** tant que l'historique tient : en 15 images, Catmull-Rom perd les plus hautes fréquences, d'où un tissage de la grille 4×4 entre pixels frais nets et historique doux. Un historique sans interpolation, l'échantillon le plus proche et son décalage gardés, n'y change rien : c'est la direction de vue qui tourne.
- **L'ombre au sol est reprojetée sur le sol :** elle suit le vent avec un retard d'au plus 16 images, quelques mètres au vent réel.

**Les vérifications :**
- **Le banc de mouvement, contre la passe unique en mouvement** (`--full`, sans historique) : écart moyen, part des pixels au-delà de 8 niveaux, et part des plaques, l'écart moyen sur 9×9 pixels au-delà de 2 niveaux. Les deux premiers ne voyaient pas la seconde peau : un décalage plat, faible et étendu.

| Vue | 0,5° et 0,02° par image, avant | après | 2° et 0,05° par image, après |
|---|---|---|---|
| orbite | 10,35 ; 43,5 % | 3,45 ; 7,8 % | 4,47 ; 12,9 % |
| globe | 1,69 ; 6,8 % | 1,37 ; 5,0 % | 1,38 ; 5,0 % |
| cumulus | 1,01 ; 2,6 % | 0,24 ; 0 % | 0,24 ; 0 % |
| survol | 0,21 ; 0 % | 0,21 ; 0 % | 0,15 ; 0 % |

- **Les plaques vues en vol,** à 160 et 440 km, vitesse x5 à x9 : `haut160` et `haut440`, ajoutées au banc, et `--motion "0.2 0 0 0 0 0.05"`, 5 % de la hauteur par image vers le nord, la règle de vitesse de l'application. Contre `--full` à même mouvement (`x64/vol_full`, `x64/vol_t`) ; ms de la passe :

| Vue | avant | après | ms, après | ms, passe unique |
|---|---|---|---|---|
| haut160 | 1,06 ; 1,2 % | 0,72 ; 0,6 % | 14,7 | 20,4 |
| haut440 | 2,97 ; 8,9 % | 1,25 ; 3,8 % | 15,1 | 19,3 |
| orbite | 5,24 ; 16,5 % | 0,66 ; 1,1 % | 38,1 | 39,1 |
| globe | 1,39 ; 5,0 % | 0,56 ; 1,8 % | 9,5 | 12,8 |
| cumulus | 0,24 ; 0 % | 0,06 ; 0 % | 23,6 | 23,6 |
| lisière, mer, forêt | 0 à 0,3 | 0 à 0,3 | 2,9 à 6,7 | 13,6 à 38,2 |

- **Les plaques venaient du remplissage :** quand la dérive rejetait l'historique, des régions entières passaient aux tuiles fraîches, qui lissent le grain des nuages en voile pâle, aux bords nets. La colonne « avant » est mesurée avant ce traitement, à 13 km par image sur toutes les vues (`x64/pl_t`, supprimé).
- **La plongée** (`--motion "0 0 0 1.015"`, `x64/plong_t` contre `x64/plong_full`) : orbite 9,51 → 4,31 niveaux, globe 3,74 → 2,00, haut440 3,05 → 2,85, haut160 0,89 ; passe de 1,2 à 17,9 ms.

- **Avant, la faute vue en vol :** en orbite, les petits cumulus traînaient le long du mouvement ; au cumulus, des coutures séparaient des régions décalées. Après : formes et bords à leur place ; l'orbite reste un peu plus douce, le globe sans son grain. Images `x64/mvt_t`, `x64/mvt_full`. Au même banc après le traitement des plaques : orbite 3,37 ; 7,3 % à 3,0 ms, globe 1,36, cumulus 0,16 ; au sol, à 2,2 km par image, irréaliste près du sol, la passe retrace et monte jusqu'à 35 ms.
- **L'image immobile ne change pas :** 0,00 niveau contre `x64/fixe_verif` sur neuf vues ; au globe, au plus 2 niveaux sur 2 % du disque (`x64/fixe_t`). La passe garde son coût, de 1,2 à 4,5 ms.
- **Le vent,** 0,5 s de météo par image, trente fois le temps réel à 60 images par seconde : au plus 0,94 niveau et 1 % des pixels. À 30 s par image, le damier 4×4 apparaît sur les nuages lointains.
- **`--full`,** la passe unique, rend la même image que la référence ; elle reste celle des vues de diagnostic `weather` et `cloudshadow` (`spec-nuages.md`).
- **En vol :** `tools/tests/2026-10-28-optimisation-nuages.txt`, par `tools/lance.ps1 -Parcours`.

**Essayé et retiré :**
- **Une tuile 8×4 :** 17 % de mieux en mer, rien ailleurs, pour deux fois plus d'attente en mouvement.
- **Lire forme et érosion avec la météo à chaque pas :** 0,4 ms de moins au cumulus, 0,65 ms de plus en mer ; gardé seulement dans un nuage.
- **Une borne de présence sur la forme :** sa médiane, 0,89, dépasse tout seuil de couverture ; elle ne prouve aucun vide.
- **Une tuile 2×2 en vol rapide :** la trace triple partout, mer 3,6 → 10 ms.
- **Retracer selon un budget de rotation cumulée (4 à 20°) :** en orbite à vitesse moyenne, 8 à 27 ms pour un gain nul ; la limite par image le remplace.
- **Un historique sans interpolation,** l'échantillon le plus proche et son décalage gardés : plus net mais crénelé, plus loin de la passe unique (orbite 4,03 contre 3,45 à vitesse moyenne).
- **Compter le flou du rééchantillonnage dans la dérive :** meilleur (orbite 6,5 → 3,5), mais 30 à 39 ms.

### Round 2 : dessin du terrain (2026-10-28)

**Le dessin tombe de 11 à 17 ms à 3 à 7 ms près du sol ; l'image reste celle de la référence.** Banc `x64/banc_perf_r2_terrain_bis`, comparé à `x64/banc_perf_r1_verif`, ms GPU.

| Vue | Terrain, avant | Terrain, après | Total, avant | Total, après | fps |
|---|---|---|---|---|---|
| foret_sol | 12,7 | 4,0 | 37,5 | 28,8 | 35 |
| lisiere | 11,2 | 3,1 | 36,3 | 28,5 | 35 |
| montagne | 16,5 | 6,8 | 35,7 | 26,1 | 38 |
| mer | 1,2 | 1,4 | 9,7 | 9,2 | 109 |
| survol | 12,5 | 5,3 | 23,1 | 15,0 | 67 |
| cumulus | 1,3 | 1,2 | 5,6 | 5,2 | 192 |
| orbite | 5,3 | 4,3 | 9,2 | 7,9 | 127 |
| globe | 2,2 | 1,8 | 5,1 | 4,7 | 215 |

**La garde de qualité :** aucun pixel ne bouge de plus d'un niveau sur les huit vues.
- **Identiques au bit près :** forêt, montagne, cumulus, orbite, globe.
- **Un niveau, sur quelques pixels :** 6 en lisière, 4 en survol, 7 en mer.
- **`banc_qualite.py`,** 30 lieux, graine 1, contre `main` sur les mêmes lieux (`x64/qualite_r2_base`, `x64/qualite_r2_final`) : aucun p95 ne se dégrade, mutation comprise ; 87 crops sur 3 891 bougent, aucun pixel de plus de 8 niveaux. Contre `tools/banc_qualite_reference.json`, du 2026-10-24, `main` dépasse déjà les 10 % sur 26 mesures ; le round n'en ajoute aucune.

**La profondeur d'abord** (`D3DApp::Draw`) :
- **Le terrain écrit sa profondeur seul,** même vertex shader, sans pixel shader : 0,2 à 0,3 ms.
- **Puis les objets et le feuillage,** comme avant ; le HiZ du feuillage lit la même profondeur.
- **Puis la couleur du terrain,** en profondeur égale, sans écriture : le shader des matériaux tourne une fois par pixel montré, ni sous les plantes, ni sous le relief qui le cache.
- **Le gain :** 7 à 9 ms près du sol, 4,4 ms en survol. Le fil de fer garde l'ancien chemin.

**Dans le shader, ce qui ne change rien n'est plus calculé :**
- **Les strates, là où la roche les montre :** `StrataShift`, ses 12 octaves, et les lentilles, dans la branche de la roche et des parois seulement, une fois par pixel (`PixelStrataShift`). Les phases des bancs s'arrêtent où leurs sinus sont éteints, pixel de plus de 5,75 m ; les lentilles, où les bancs le sont, pas de la colonne de plus de 0,66 m.
- **La présence des bois s'arrête dès que la suite ne peut plus la changer :** `PresenceField` somme ses octaves tant que le reste, borné, peut ramener le champ dans la largeur du seuil. Au-delà, `Presence` vaut 0 ou 1 quelle que soit la suite. La borne est une preuve : 3,135 par unité d'amplitude de `Noise3`, pas son écart-type, 0,40.
- **Rien des bois où rien ne pousse ni ne s'enracine :** `WoodsAt` sauté où ni arbre ni arbuste n'est possible, ou sur la roche, l'éboulis ou la plage entiers.
- **Les plantes dessinées, sans leurs fondus au loin :** quand même la plus haute tient sous le seuil de pixels, tous les fondus de `PlantsDrawn` valent 0.
- **Une quadrature des pentes pour la roche, l'éboulis et la neige** (`SlopeShares3`), au lieu de deux.
- **`FbmLostShare` en forme close :** une somme géométrique, bornée à [0, 1] ; égale à la boucle sur les octaves à 10⁻¹⁶ près en double.
- **Pas à pas, ms en survol / montagne :** profondeur d'abord −4,4 / −9,4 ; strates et bois sans arbres −1,6 / −0,4 ; présence bornée −0,2 / 0 ; phases, lentilles et quadrature commune −0,3 / −0,7 ; le reste −0,3 / −0,3.

**Ce qui borne encore :**
- **Le surcoût des quads.** Le GPU ombre par quads de 2×2 pixels ; les triangles du terrain couvrent 6 pixels environ, et le feuillage laisse des pixels de sol isolés. Mesuré par `IsHelperLane` : 2,0 voies par pixel montré en survol, 1,9 en forêt, 1,6 en montagne et au cumulus, 1,2 en orbite.
- **La piste :** la couleur du terrain en compute, sur un tampon de visibilité, une voie par pixel. Un chantier : sorties des sommets en cache, dérivées analytiques au lieu des différences de quad, `ddx(q)` compris.
- **Le calcul entier des hachages.** Chaque octave de `Noise3` hache ses 8 coins (pcg3d) ; près du sol, un pixel somme environ 80 octaves.
- **Ce qui pèse encore,** variantes du shader, ms en survol / montagne / orbite : végétation 2,4 / 2,2 / 2,1, dont présence des bois 1,8 / 1,5 / 0,8 et dalle de la canopée 0,7 / 0,6 / 0 ; textures 0,8 / 3,6 / 2,0, dont roche 0,1 / 2,0 / 0 ; bruits local et de détail 1,2 / 0,7 / 1,0.
- **Montagne, survol et orbite restent au-dessus des 4 ms visés.**
- **En mouvement :** les trous éventuels de la profondeur égale, aux crêtes et sous les plantes, à juger en vol : `tools/tests/2026-10-28-optimisation-terrain.txt`. Les images immobiles n'en montrent aucun : elles restent celles de la référence à un niveau près.

**Essayé et retiré :**
- **DXC et le modèle 6.0 au lieu de FXC :** 5 % de mieux avant les autres changements, rien ou pire après ; la compilation passe de 88 s à 4 s.
- **`precise` sur la position des sommets,** contre des trous supposés de la profondeur égale : sans effet, et la mer bougeait de 14 niveaux. Il n'y avait pas de trou.
- **La forme close de `FbmLostShare` sans borne :** un arrondi sous 0, sous une racine, donnait des pixels blancs isolés, quelques-uns aux vues du banc, des centaines à 50 m dans `banc_qualite.py`. Bornée à 0, l'image est revenue.
- **Les variantes du shader,** qui éteignent une part à la fois : diagnostic seulement (`log/optimisation-historique.md`).

### Round 3 : végétation (2026-10-28)

**Placement et dessin du feuillage tombent de 18 à 20 ms à 6 ms en forêt ; l'image reste celle de la référence.** Banc `x64/r3_final`, comparé à `x64/sup_fixe2`, ms GPU.

| Vue | Plantes, placement, avant | après | Objets, placement, avant | après | Feuillage, dessin, avant | après | Total, avant | après | fps |
|---|---|---|---|---|---|---|---|---|---|
| foret_sol | 7,7 | 2,2 | 1,1 | 0,8 | 10,5 | 3,8 | 30,3 | 17,6 | 57 |
| lisiere | 8,4 | 2,3 | 1,1 | 1,0 | 9,7 | 3,6 | 30,7 | 18,5 | 54 |
| montagne | 9,4 | 1,9 | 1,3 | 0,8 | 3,9 | 1,8 | 27,3 | 17,0 | 59 |
| mer | 0,8 | 0,2 | 0,4 | 0,3 | 0,1 | 0,1 | 9,6 | 8,7 | 115 |
| survol | 5,1 | 1,4 | 0 | 0 | 1,9 | 1,9 | 15,8 | 12,0 | 83 |

- **Le GPU varie de 5 % d'une série à l'autre :** une série précédente du même code donnait 16,9 / 17,4 / 16,3 / 8,5 / 11,6 ms, ses vues sans plantes 4 à 8 % sous la référence ; celle-ci, à 2 % près de la référence.
- **Le tri du feuillage** (`feuillage_tri`) ne change pas : 0,1 à 0,3 ms.
- **Six vues de plus,** familles climatiques au sol et à 150 m (tropical, boréal, steppe, désert, tempéré), contre le binaire du commit `3817e79` : placement de 3,9-9,7 à 1,6-3,2 ms, feuillage de 0,3-12,0 à 0,3-5,8 ms ; tropical à 150 m de 24,8 à 12,3 ms au total.

**La garde de qualité :** aucun pixel ne bouge de plus d'un niveau, sauf un.
- **Identiques au bit près :** mer, survol, cumulus, orbite, globe, haut160, haut440.
- **Un niveau sur 3 pixels** en forêt et en lisière, 7 en montagne : deux maillages à la même profondeur (la couleur en profondeur égale, plus bas). Sur les six vues de plus, au plus 11 pixels d'un niveau.
- **Un pixel de montagne,** le reflet d'une feuille, change de 76 niveaux d'une passe à l'autre, et un de boréal de 27 : l'ordre des plantes à profondeur égale, tiré par des opérations atomiques. Le binaire d'avant fait de même, d'une passe à l'autre.
- **`banc_qualite.py`,** 30 lieux, graine 1, contre `x64/qualite_r2_final` (`x64/qualite_r3`) : aucun p95 ne bouge ; une image sur 3 903 change, d'un niveau.

**Le profil de départ,** horodatages par étape, foret_sol / lisiere / montagne / survol, ms :
- **Placement :** la passe lourde 6,2 / 6,1 / 7,6 / 2,8, une tuile par fil ; le tri des tuiles 0,2 / 0,4 / 0,3 / 1,8 ; scans, compaction et dispersion 0,1.
- **Dans la passe lourde,** par variantes : les trois sols exacts de chaque tuile (`ExactElevation`), les trois quarts ; le sol exact des plantes proches 1 ; la présence des bois par candidat 0,85 ; les matériaux 0,2.
- **Dans `ExactElevation`,** la moitié est la grille en doubles (`Lattice`) : le GPU fait un double au 64e du rythme des floats.
- **Dessin :** imposteurs 6,2 / 5,2 / 1,7 / 1,7 ; maillages proches 3,6 / 4,0 / 1,9 / 0 ; HiZ 0,1.

**Le sol exact gardé d'une image à l'autre** (`PlantPlacement.hlsli`, `GroundCached` ; `PlanetPlantPlacement.cpp`) :
- **Le sol exact d'une tuile,** à sa première cellule et à une demi-tuile sur ses deux axes, ne dépend que de la tuile : sa cellule sur la grille de la planète. De même le sol exact d'une plante proche.
- **Une table de hachage sur le GPU les garde :** clé entière, tuile, tranche, plan, première cellule ; 2²⁰ cases de 32 octets, quatre par seau.
- **Lue dans la table de l'image précédente, écrite dans celle-ci :** deux tables en alternance ; chaque case réclamée par un seul écrivain. Aucun fil ne lit une case qu'un autre écrit.
- **Une clé sans case est recalculée,** et retente sa chance à l'image suivante.
- **Un saut de la caméra efface les tables** (`Reset` : chaque vue du banc, chaque bouton de la palette « Tests ») : une vue ne dépend pas, au dernier bit, de celles vues avant. Sans cela, `tropical_sol` après `tropical_150`, 300 m plus loin, changeait sur 2 965 pixels, 38 de plus d'un niveau.
- **64 Mo** de tables, 4 Mo de réclamations effacées à chaque image ; 32 Mo de zéros pour les effacer.
- **Immobile :** passe lourde 6,2 → 1,9 ms en forêt, 7,6 → 1,7 en montagne.
- **En mouvement,** cap 0,5° et 4 % de la hauteur par image, puis 2° et 20 % : placement 6,2 à 7,3 ms sans la table, 2,5 à 3,8 avec ; survol 4,6 → 3,2.
- **Ce qui change en mouvement :** une valeur gardée vient d'une caméra précédente. `MakeCandidate` place la cellule depuis le pied de la caméra, en float : le point bouge de moins d'un millimètre d'une caméra à l'autre, son sol exact du dernier bit. Contre le calcul de chaque image, au même mouvement : écart moyen de 0,000 à 0,006 niveau, au plus 0,006 % des pixels au-delà de 8, aucune plaque. Une plante au seuil exact de sa décision naît une image plus tôt ou plus tard ; sans la table, elle clignotait au gré de ces arrondis.
- **Rien à invalider :** le relief ne change pas en vol, et la clé nomme la cellule.

**Les imposteurs en profondeur conservatrice** (`PlanetFoliageDepth.hlsli`, `PlanetFoliageProxyVertex.hlsl`, `PlanetFoliageImpostorPixel.hlsl`) :
- **Le pixel d'un imposteur reconstruit sa profondeur** (`SV_Depth`) : le test attendait la fin du shader, quatre vues lues et éclairées, même pour un pixel caché.
- **La borne de cette profondeur existait :** celle du HiZ (`vegetation-hiz.md`), prouvée sur les moments de chaque vue et de chaque mip. Elle passe dans `ImpostorDepthBound`, partagée par le test HiZ et le dessin ; les réglages du modèle la portent (`depthBounds`).
- **Le quad se pose à la profondeur la plus proche possible ;** le pixel déclare la sienne au plus aussi proche (`SV_DepthLessEqual`). Le test rejette avant le shader ce que le terrain, les maillages ou un imposteur déjà dessiné cachent.
- **Sans borne,** situation mal conditionnée, le quad est au plan proche : aucun rejet.
- **Exigé par le compilateur :** la position du pixel au centroïde, sans perspective ; sans multiéchantillonnage, c'est le centre du pixel, comme avant.
- **Gain :** 6,2 → 0,8 ms en forêt, 5,2 → 0,6 en lisière, 1,7 → 0,6 en montagne. Rien en survol : vus de dessus, les imposteurs se recouvrent peu.

**Les maillages proches en profondeur d'abord** (`PlanetFoliage.cpp`, `PlanetFoliageMeshDepthPixel.hlsl`) :
- **Leur profondeur seule,** mêmes sommets, mêmes rejets alpha ; puis leur couleur en profondeur égale, une fois par pixel montré. La règle du round 2, appliquée aux feuilles.
- **À profondeur égale,** feuilles doublées, le test strict gardait le premier triangle ; le test égal les ombre tous et garde le dernier. La couleur se dessine donc dans l'ordre inverse des triangles (`meshIndicesReversed`) : le dernier ombré est le premier dessiné. Sans cela, 50 000 à 74 000 pixels changeaient, jusqu'à 95 niveaux.
- **Gain :** 3,6 → 2,7 ms en forêt, 1,9 → 1,0 en montagne. La profondeur seule en coûte 1,3 à 1,5.

**Le tri des tuiles sans ses seize plans** (`CullPlantTile`) :
- **Chaque cellule d'une tuile vérifiait son plan :** son point sur la sphère, en doubles, seize fois. C'était presque tout le tri : 1,8 ms en survol, 0,7 en mer, où rien ne pousse.
- **Quand l'axe du plan domine la verticale au milieu de la tuile** de plus que la tuile ne peut la tourner, toutes ses cellules y sont. La borne : aucun candidat à plus de d√2 du milieu sur le plan, √3 fois plus sur la sphère ; deux fois cela, et l'arrondi du float.
- **Gain :** survol 1,8 → 0,4 ms, mer 0,7 → 0,1.

**Ce qui borne encore :**
- **La présence des bois par candidat,** 0,85 ms en forêt : deux champs de bruit par plante candidate.
- **Les pixels des maillages proches,** 2,7 ms en forêt : des feuilles en triangles de moins d'un pixel. La piste : un niveau de détail des maillages, à silhouette égale ; il change l'image.
- **Les imposteurs vus de dessus,** 1,8 ms en survol : peu de recouvrement, et la part transparente des quads des quatre vues.
- **En mouvement rapide,** le placement remonte vers 3 à 4 ms : les tuiles nouvelles.
- **Le reste de la forêt :** calcul du terrain 4,1 ms, dessin du terrain 3 à 4 ms, nuages et air 2,7 à 5,5 ms ; en montagne, le dessin du terrain, 6,5 ms.
- **En vol :** `tools/tests/2026-10-28-optimisation-vegetation.txt`.

**Essayé et retiré :**
- **La grille en paires de floats,** `Lattice` sans doubles : passe lourde −1 ms, mais l'image bouge partout près du sol, 1,2 % des pixels au-delà de 8 niveaux. Un écart au dernier bit du sol déplace la caméra et les feuilles d'une fraction de pixel ; les bords alpha basculent. Le calcul du terrain n'en gagnait rien.
- **Garder aussi la présence des bois par candidat :** plus lent en forêt, 1,9 → 2,7 ms ; les clés débordent la table.
- **Sauter les candidats rejetés avant leurs doubles** (`MakeCandidate`) : 0,1 ms au plus.

### Round 4 : calcul du terrain (2026-10-28)

**Le calcul du terrain n'est plus refait quand ses entrées sont celles de l'image précédente : de 4,2 ms à 0 au sol immobile, de 4,3 à 1,7 ms en tournant sur place. En vol, il reste à 2 à 4,6 ms : le maillage glisse avec la caméra, rien n'y est gardé.** Image identique au bit près, immobile comme en mouvement. Banc `x64/r4_final`, comparé à `x64/r3_verif`, ms GPU.

| Vue | Terrain, calcul, avant | après | Total, avant | après | fps |
|---|---|---|---|---|---|
| foret_sol | 4,23 | 0 | 17,3 | 13,2 | 76 |
| lisiere | 4,22 | 0 | 17,8 | 13,8 | 73 |
| montagne | 3,28 | 0 | 16,6 | 13,7 | 73 |
| mer | 2,12 | 0 | 8,7 | 6,7 | 150 |
| survol | 1,44 | 0 | 11,8 | 10,4 | 96 |
| cumulus | 0,58 | 0 | 5,5 | 5,0 | 199 |
| orbite | 0,47 | 0 | 8,3 | 8,0 | 124 |
| globe | 1,05 | 0,14 | 4,9 | 4,1 | 243 |
| haut160 | 0,41 | 0 | 4,0 | 3,5 | 283 |
| haut440 | 0,42 | 0 | 3,7 | 3,4 | 291 |

- **Les vues du banc sont immobiles :** ce tableau est le cas le plus favorable. Les deux bancs de mouvement suivants donnent ce qui vaut en vol.
- **En tournant sur place,** 0,5° par image, contre le calcul entier à chaque image au même mouvement :

| Vue | Terrain, calcul, entier | gardé | Total, entier | gardé | fps |
|---|---|---|---|---|---|
| foret_sol | 4,29 | 1,70 | 20,1 | 17,3 | 50 → 58 |
| lisiere | 4,85 | 1,88 | 22,0 | 19,1 | 45 → 52 |
| montagne | 3,29 | 1,08 | 19,3 | 17,1 | 52 → 59 |
| mer | 2,20 | 1,10 | 9,0 | 8,0 | 111 → 125 |
| survol | 1,46 | 0,47 | 12,4 | 11,5 | 81 → 87 |

- **En vol,** `--motion "0.2 0 0 0 0 0.05"`, 5 % de la hauteur par image : rien ne change, terrain 4,3 / 4,6 à 5,0 / 3,4 à 3,7 / 2,2 / 1,4 ms en forêt, lisière, montagne, mer, survol ; total 19 à 24 ms au sol, 41 à 52 fps.
- **Le GPU varie de 5 à 10 % d'une série à l'autre :** en vol, où rien n'est gardé, deux séries du même travail donnent 24,2 et 22,6 ms en lisière.

**La garde de qualité :** aucun pixel ne bouge.
- **Immobile :** les dix vues identiques au bit près à `x64/r3_verif`.
- **En mouvement,** contre le calcul entier à chaque image, au même mouvement : identiques au bit près en tournant (0,5° par image), en vol (5 % de la hauteur par image), en vol lent (0,2 %), et à l'arrêt après un mouvement (dix images immobiles avant la capture).
- **`banc_qualite.py`,** les 30 lieux de `x64/qualite_r2_final` (`x64/qualite_r4`) : aucun p95 ne bouge. Un crop sur 3 891 change d'un pixel, de 3 niveaux, à 12 m : le même crop change d'une passe à l'autre depuis le round 2, l'ordre des plantes à profondeur égale.

**Le profil de départ,** horodatages par étape, ms, foret_sol / lisiere / montagne / mer / survol :
- **Les sommets du maillage** (`TerrainCompute.hlsl`) : 2,96 / 2,89 / 2,52 / 1,27 / 0,47. 1 114 anneaux au sol, 890 000 sommets, le tri en garde la part visible.
- **La grille fine** (`FineTerrain.hlsl`, `FineNormals.hlsl`), loin du sol seulement : survol 0,85 et 0,01.
- **Le relief des matériaux** (`MaterialRelief.hlsl`), éteint, une copie : 0,07 à 0,19. Retiré le 2026-10-30 : la marche vers le soleil écrit dans les sommets du terrain.
- **La marche vers le soleil** (`Horizon.hlsl`) : 1,24 / 1,29 / 0,75 / 0,61 / 0,06.
- **Le préfiltre des normales** (`SplinePrefilter.hlsl`) : 0,02 à 0,13. Retiré le 2026-10-30 : la spline lit les sommets eux-mêmes (`spec-normales-spline.md`).
- **Dans les sommets,** par variantes : ceux de mailles de moins de 4 m, la grille en doubles (`EXACT_LATTICE_MAX_CELL`), coûtent 2,4 ms des 3 en forêt. La grille en floats partout ôterait 1,7 / 1,2 / 0,8 ms en forêt, montagne, mer : les doubles pèsent plus que tout le bruit en floats.
- **Ce qui se refait à entrées égales :** tout, à chaque image. Immobile, rien n'a changé ; en tournant, la hauteur des sommets n'a pas changé, seul le tri.

**Le calcul gardé** (`D3DApp::Draw`, `TerrainInputs` ; `TerrainCompute.hlsl`, `FineTerrain.hlsl`) :
- **La clé est exacte :** les constantes que lisent les passes du terrain, relevées dans leur code compilé (`cbufferLoadLegacy` du DXIL), comparées au bit près. Rien d'autre n'entre : les tampons du terrain ne sont écrits que par ces passes, leurs textures sont fixes.
- **Le maillage d'abord :** les axes de la face, sa demi-largeur, le nadir en doubles, les anneaux et la grille fine, la caméra sur la face. Égaux, chaque sommet est au même point de la planète, avec les mêmes octaves : sa hauteur est la même.
- **Puis la vue et le soleil :** les axes de la caméra, le soleil, la marge des vagues. Ils ne décident que des sommets nécessaires et de l'horizon.
- **Tout égal :** aucune de ces passes n'est lancée. Les transitions restent ; les tampons gardent ce qu'elles ont écrit.
- **Le maillage seul égal,** la caméra tourne sur place : un sommet calculé à l'image précédente, `NaN` sinon, garde sa hauteur ; seuls ceux qui entrent dans la vue sont calculés. Un sommet sorti de la vue redevient `NaN`, comme dans le calcul entier : les normales et la marche vers le soleil voient le même maillage. Ces passes-là sont refaites.
- **La marche vers le soleil est refaite en tournant :** elle lit les hauteurs des sommets voisins, nulles pour ceux que le tri écarte ; le tri changeant, son résultat peut changer.
- **Aucun saut de la caméra n'est à traiter :** une clé égale donne un résultat égal au bit près, quel que soit ce qui précède.

**Ce qui borne encore :**
- **En vol, tout est refait.** Le maillage glisse en continu avec la caméra : aucun sommet ne reste au même point d'une image à l'autre. Un maillage posé par pas sur la grille de la planète garderait chaque sommet, mais il est écarté : son affinement se verrait en déplacement rapide (`principes.md`).
- **La grille en doubles,** 1,7 ms en forêt : par axe et par octave, une multiplication et une addition en double, au 64e du rythme des floats. Approchée, elle change le dernier bit du sol sous la caméra, donc toute l'image (round 3).
- **La marche vers le soleil,** 0,6 à 1,3 ms au sol : ses pas partent de la maille et croissent de 2 %, environ 500 près de la caméra ; la moitié du temps est la lecture des hauteurs.
- **La marge des vagues s'applique aussi sur terre :** 16 à 128 m autour de la vue, pour les sommets de mer que les vagues déplacent. Sans elle, 0,3 ms de moins en forêt et 0,6 en mer, image inchangée sur cinq vues ; mais prouver qu'un sommet n'est pas de la mer demande sa hauteur.
- **Le reste au sol en vol :** dessin du terrain 3 à 7 ms, feuillage 2 à 4 ms, nuages et air 3 à 7 ms ; la forêt et la lisière restent sous 60 fps en vol rapide.
- **En vol :** `tools/tests/2026-10-28-optimisation-terrain.txt`.

**Essayé et retiré :**
- **La grille en entiers :** le découpage de `Lattice`, plancher et reste en float, refait par des opérations entières sur les bits du double, le produit seul en double. Exact au bit près sur 1,1 million de valeurs, arrondis et égalités compris, et sur toutes les vues ; mais pas plus rapide, 3,07 ms contre 2,96 en forêt. Une addition en double vaut une trentaine d'opérations entières, le découpage en demandait autant.
- **Dérouler les boucles d'octaves,** pour que les fréquences en double deviennent des constantes : plus lent, 3,26 ms, et la mer changeait de 20 niveaux en moyenne.
- **128 fils par groupe au lieu de 64 :** sans effet.
- **Garder les hauteurs de la dernière maille dans la marche vers le soleil :** exact, sans effet ; les lectures étaient déjà en cache.
- **Une borne de hauteur plus basse pour arrêter la marche :** 2 000 m au lieu de 10 000, non exacte, ne gagne que 0,25 ms en forêt. Une borne exacte, le maximum des hauteurs du maillage, gagnerait moins là où des montagnes sont en vue.

### Round 5 : images en vol (2026-10-28)

**Arrêté à la mesure : le GPU n'attend le CPU que 0,7 à 0,9 ms par image au sol, immobile comme en vol.** Deux images en vol rendraient au plus ce temps : de 71 à 75 fps au sol immobile, de 50 à 52 en vol. C'est sous le seuil d'1 ms fixé au départ, dans le bruit du GPU, pour une refonte qui touche toutes les lectures du GPU vers le CPU.

**La mesure,** `tools/banc_perf.py`, nouvelles colonnes (Le banc). Immobile `x64/r5_mesure`, en vol `--motion "0.2 0 0 0 0 0.05"` `x64/r5_mesure_vol` ; ms par image.

| Vue | Liste et soumission, CPU | GPU inactif | Total GPU | Cadence | fps GPU | fps réels |
|---|---|---|---|---|---|---|
| foret_sol | 0,83 | 0,77 | 13,3 | 14,1 | 75 | 71 |
| lisiere | 0,93 | 0,89 | 14,7 | 15,6 | 68 | 64 |
| montagne | 0,85 | 0,84 | 14,2 | 15,1 | 70 | 66 |
| mer | 0,73 | 0,73 | 6,8 | 7,5 | 147 | 133 |
| survol | 0,86 | 0,82 | 10,8 | 11,6 | 92 | 86 |
| cumulus | 0,62 | 0,62 | 5,2 | 5,9 | 191 | 171 |
| orbite | 0,82 | 0,83 | 8,3 | 9,1 | 120 | 109 |
| globe | 0,76 | 0,77 | 4,1 | 4,9 | 244 | 205 |
| foret_sol, en vol | 0,84 | 0,81 | 19,1 | 19,9 | 52 | 50 |
| lisiere, en vol | 0,82 | 0,80 | 22,1 | 22,9 | 45 | 44 |
| montagne, en vol | 0,87 | 0,81 | 19,1 | 19,9 | 52 | 50 |
| survol, en vol | 0,76 | 0,71 | 12,5 | 13,2 | 80 | 76 |
| orbite, en vol | 0,90 | 1,16 | 43,9 | 45,1 | 23 | 22 |

- **La préparation de l'image coûte 0,01 à 0,04 ms ;** l'enregistrement des listes 0,35 à 0,53 ms ; la soumission et la présentation 0,27 à 0,40 ms.
- **Le CPU attend le GPU presque tout le reste :** `cpu_attente` vaut le total GPU à 0,1 ms près.
- **Le GPU inactif vaut ce que le CPU fait entre deux images :** il attend l'enregistrement et la soumission de la suivante. La cadence est le total GPU plus ce temps, à 0,05 ms près.
- **Les fps des rounds 1 à 4 sont ceux du temps GPU :** la cadence réelle est de 4 à 16 % plus basse, le plus en haute altitude où l'image est courte.
- **L'image ne change pas :** les dix vues immobiles identiques au bit près à `x64/r4_verif` ; la mesure n'ajoute que des horodatages du CPU.

**Ce que deux images en vol demanderaient,** relevé dans le code et non fait :
- **Doubler par image en vol** les tampons que le CPU écrit : constantes de l'image, des nuages, de la mer, des cascades.
- **Lire chaque relevé dans l'image qui l'a écrit :** horodatages, compteurs des objets et des plantes, hauteur de la mer, capture.
- **Le sol sous la caméra** (`mReadbackBuffer`) arriverait une image plus tard : la hauteur de la caméra changerait en vol, donc l'image. Le mode banc devrait garder une image en vol.
- **Ce que le GPU garde d'une image à l'autre resterait exact sans rien faire :** le terrain du round 4, la table du sol des plantes, les historiques. La file exécute les images dans l'ordre ; la clé compare à l'image précédente, qui a écrit les tampons juste avant sur le GPU.

**Ce qui borne la cadence :**
- **Le temps GPU,** 94 à 96 % de la cadence au sol : 19 à 22 ms en vol en forêt et en lisière, dont le calcul du terrain refait à chaque image, 4,4 ms (round 4).
- **En vol au-delà de x5 en altitude,** la passe des nuages, 15 à 38 ms (round 1).
- **La part du CPU,** 0,8 ms, ne compte qu'au-dessus de 120 fps : 10 % de la cadence en mer, 16 % au globe.

**À reprendre si** le temps GPU tombe sous 8 ms au sol : le gain deviendrait 10 % de la cadence.


### Round 7 : nuages en vol rapide (2026-10-29)

**Sous 14 km, le vol rapide ne retrace plus chaque pixel qui a glissé : un pixel par carré 2×2 est tracé, les trois autres en sont interpolés.** Cumulus à 10 km en vol rapide : la passe de 24,2 à 8,1 ms, de 36 à 90 fps réels ; 150 m sous les cumulus en plongée : de 18,1 à 9,5 ms, de 34 à 52 fps. Au-dessus de 14 km, rien ne change : 160 et 440 km restent à 15 ms, l'orbite à 38 ms. Image immobile identique au bit près. Bancs `x64/r7_final_*` contre la passe pleine au même mouvement, `x64/r6_full_*` ; avant, `x64/r6_avant_*`.

**Pourquoi l'historique est rejeté en vol rapide,** mesuré à 5 % de la hauteur par image :
- **Le virage n'est pas seul en cause.** Sans lui, cumulus 24,0 → 22,8 ms, haut160 14,9 → 13,2 ; l'orbite 38 → 20 ms, mais son écart à la passe pleine passe de 0,67 à 4,88 niveaux, 46 % de plaques.
- **À 10 km, la dérive rejette :** 500 m par image, des nuages à quelques kilomètres ; l'étalement en distance d'un volume glisse de plus d'un pixel.
- **La reprojection voit déjà la parallaxe du volume :** la dérive est le glissement entre l'avant et l'arrière de sa lumière. Le virage par image borne l'adoucissement du rééchantillonnage (round 6, tag `piste/optimisation-r6-nuages-mouvement`). Garder l'historique plus longtemps coûte de l'écart partout.
- **Il reste à tracer moins cher ce qui a glissé.**

**Les pixels qui ont glissé, un par carré 2×2** (`CloudsTemporal.hlsli`, `PSCloudTraceHalf`, `CloudTemporalHalfFill`) :
- **Une passe à demi-résolution,** un texel par carré de 2×2 pixels ; le pixel tracé fait le tour du carré en quatre images, avec la tuile 4×4.
- **Elle trace un carré quand l'historique d'un de ses quatre pixels a glissé ou tourné,** par la décision même de la résolution (`CloudTemporalLookup`, partagée).
- **La résolution prend la trace telle quelle au pixel tracé,** et pour les trois autres l'interpolation bilinéaire des carrés voisins qui voient la même surface. Sans carré voisin, le pixel se trace, comme avant.
- **Le pixel interpolé se garde comme un remplissage,** à 0,75 pixel de dérive : à l'arrêt, la tuile 4×4 le remplace en 16 images.
- **Décidé par carré, non par pixel :** décidé au seul pixel tracé, ses voisins du même carré retraçaient en ordre dispersé ; cumulus 14,2 ms au lieu de 8,2.

**Sous la porte de la quadrature lointaine seulement,** caméra sous 14 km (`CloudTemporalHalfOn`, `CLOUD_FROSTBITE_ORBIT_CAMERA_GATE_LOW_KM`) :
- **Là, aucun pixel ne moyenne de rayons sous le pixel :** les nuages sont plus grands que lui. L'interpolation s'écarte d'un niveau sur 12 % des pixels du cumulus, de plus de 2 niveaux sur moins qu'avant.
- **Au-dessus, le grain des nuages lointains est au pixel :** interpolé, il s'adoucit. Partout, l'orbite tombait de 38 à 14 ms, mais de 0,67 à 2,94 niveaux et de 1,1 à 7,5 % au-delà de 8 ; globe 0,55 → 1,13 ; haut440 1,15 → 1,78.
- **haut160 n'en souffrait pas,** 15 → 7 ms à écart égal : son grain est faible. Aucune règle tirée de l'estimateur ne le distingue de l'orbite ; les seuils sur l'image ont échoué (plus bas).
- **Au passage de 14 km,** l'écart entre les deux régimes est d'un niveau : rien ne saute.
- **Au-dessus, la passe ne se lance pas** (`D3DApp::Draw`) : 0,2 à 0,7 ms de moins qu'en la lançant à vide, en plongée au-dessus de 14 km.

**Le coût, passe de l'atmosphère et des nuages, ms, avant → après ; fps réels avant → après :**

| Vue | vol rapide | fps réels | plongée | fps réels | vol lent |
|---|---|---|---|---|---|
| cumulus | 24,2 → 8,1 | 36 → 90 | 17,3 → 16,6 | 50 → 50 | 23,4 → 8,8 |
| cumulus_sol | 7,6 → 6,0 | 59 → 70 | 18,1 → 9,5 | 34 → 52 | 5,1 → 5,3 |
| survol | 1,5 → 1,4 | 71 → 77 | 18,6 → 15,2 | 35 → 38 | 1,5 → 1,4 |
| foret_sol | 3,2 → 3,0 | 48 → 52 | 5,5 → 5,2 | 43 → 49 | 2,9 → 2,8 |
| lisiere | 7,1 → 6,9 | 41 → 43 | 7,5 → 7,2 | 45 → 48 | 6,7 → 6,3 |
| montagne | 2,7 → 2,6 | 48 → 50 | 2,9 → 3,0 | 45 → 45 | 2,5 → 2,6 |
| mer | 4,5 → 4,5 | 104 → 102 | 4,4 → 4,7 | 117 → 108 | 4,7 → 4,6 |
| haut160 | 15,1 → 14,9 | 56 → 57 | 4,1 → 4,3 | 166 → 158 | 3,4 → 3,4 |
| haut440 | 15,7 → 15,0 | 50 → 53 | 3,3 → 3,5 | 203 → 189 | 3,4 → 3,3 |
| orbite | 38,3 → 38,0 | 22 → 22 | 17,6 → 18,1 | 43 → 43 | 4,0 → 3,8 |
| globe | 9,7 → 9,4 | 74 → 77 | 2,8 → 3,0 | 189 → 182 | 10,8 → 10,5 |

- **Vol rapide** `--motion "0.2 0 0 0 0 0.05"`, **plongée** `"0 0 0 1.025"`, **vol lent** `"0.1 0 0 0 0 0.01"`.
- **En plongée, cumulus et survol gagnent peu :** la descente part de 36 fois la hauteur, au-dessus de 14 km pour la plupart des 120 images mesurées.
- **Au-dessus de 14 km, les écarts sont dans le bruit du GPU,** 5 à 10 %. Avant/après mesurés le même jour en plongée, haut160 4,21 → 4,27 ms, orbite 17,59 → 17,73.

**La garde de qualité :**
- **Immobile :** les dix vues identiques au bit près à `x64/r4_verif`, montagne comprise (`x64/r7_final_fixe`).
- **En mouvement, contre la passe pleine au même mouvement :** les onze vues donnent les mêmes écarts qu'avant, sauf deux, au centième près :
  - **cumulus en vol rapide :** 0,06 → 0,13 niveau moyen ; au-delà de 8 niveaux, 0,01 → 0 % ; plaques 0,03 → 0 %. Le moyen monte par des écarts d'un niveau, sur 12 % des pixels ; ceux de 2 niveaux et plus baissent.
  - **cumulus_sol en plongée :** plaques 4,91 → 4,95 %, le reste égal.
- **Ce qui s'améliore :** cumulus en plongée, 1,66 → 1,55 % au-delà de 8 niveaux, plaques 3,26 → 2,19 % ; cumulus en vol lent, 0,21 → 0,19 niveau, plaques 0,06 → 0,01 %.
- **`banc_qualite.py`,** les 30 lieux de `x64/qualite_r2_final` (`x64/qualite_r7`) : aucun p95 ne bouge.

**Ce qui borne encore :**
- **Au-dessus de 14 km en vol rapide, la passe coûte la passe pleine :** orbite 38 ms, 22 fps ; 160 et 440 km 15 ms, 53 à 57 fps ; globe 9,4 ms.
- **La piste :** une quadrature lointaine moins chère sans grain, ses rayons sous le pixel partageant la marche, le saut du vide et la lumière vers le soleil ; ou une passe de calcul qui compacte les pixels à retracer.
- **Le seuil de 14 km est celui de la quadrature lointaine,** pas une mesure du grain : à 160 km, la demi-résolution irait aussi bien, sans qu'une règle le prouve.
- **En vol :** `tools/tests/2026-10-28-optimisation-nuages-rapides.txt`.

**Essayé et retiré,** vol rapide, contre la passe pleine :
- **Sans le virage :** voir plus haut ; l'orbite à 4,88 niveaux.
- **Un seul rayon lointain par pixel retracé :** orbite 38 → 19 ms, haut160 15 → 8,9 à écart égal ; mais globe 0,55 → 1,34 niveau, haut440 1,15 → 1,66, orbite 0,67 → 1,01 : un grain qui scintille.
- **Un seul rayon lointain là où l'historique est lisse,** jugé sur la plage de ses quatre texels : seuils serrés, aucun gain ; lâches, haut160 15,6 → 14,0 ms, orbite 38,8 → 34,8, l'écart en hausse partout.
- **La demi-résolution partout, l'historique borné aux carrés voisins,** comme un TAA : orbite 2,31 niveaux au lieu de 2,94, encore loin de 0,67 ; cumulus 0,32.
- **La demi-résolution partout, retracée là où les carrés voisins s'écartent :** orbite 43 ms, plus lent qu'avant. Les retraces dispersées coûtent la vague entière.
- **Le grain mesuré dans l'historique du carré :** encore dispersé, orbite 38 ms et 2,03 niveaux.
- **Là où le poids lointain du pixel est nul :** haut160 ne gagne rien, et le globe passe de 1,80 à 2,23 % au-delà de 8 niveaux : son limbe, rasant, n'a pas de quadrature lointaine, mais du grain.

### Round 8 : le sol en vol rapide (2026-10-29)

**En vol rapide au sol, de 49 à 60 fps réels en forêt, de 43 à 55 en lisière, de 48 à 54 en montagne.** Deux changements : les trouées de ciel dans les feuilles ne sont plus tracées par la résolution des nuages ; en vol, la grille du terrain se découpe en paires de floats. Image immobile identique au bit près à `x64/r4_verif`. Bancs `x64/r8_final_*`, contre le binaire d'avant mesuré dans la même séance, `x64/r8_avant_seance_*` ; le premier « avant », `x64/r8_avant_*`, est d'une séance où le GPU allait 10 % plus vite.

**L'inactivité du GPU en montagne n'était pas du moteur :** 5,5 ms dans `x64/r7_verif_rapide`, mais tous les temps du CPU y étaient multipliés par quatre, la mer aussi. Refait, 0,55 ms, comme partout.

**Le vol rapide,** `--motion "0.2 0 0 0 0 0.05"`, ms GPU avant → après :

| Vue | Terrain, calcul | Résolution des nuages | Total | Cadence | fps réels |
|---|---|---|---|---|---|
| foret_sol | 4,6 → 3,0 | 1,8 → 0,8 | 19,7 → 16,1 | 20,6 → 16,8 | 49 → 60 |
| lisiere | 4,8 → 3,3 | 3,6 → 0,9 | 22,5 → 17,5 | 23,5 → 18,2 | 43 → 55 |
| montagne | 3,6 → 2,5 | 1,2 → 1,0 | 19,7 → 17,6 | 20,6 → 18,4 | 48 → 54 |
| mer | 2,3 → 1,7 | 0,7 | 9,2 → 8,3 | 10,0 → 9,0 | 100 → 111 |
| survol | 1,4 | 0,5 | 12,7 → 12,0 | 13,5 → 12,7 | 74 → 79 |
| cumulus_sol | 1,7 → 1,4 | 1,3 | 14,4 → 13,2 | 15,4 → 13,8 | 65 → 73 |

- **La résolution :** la passe de l'atmosphère moins la trace des nuages.
- **En vol lent,** `"0.1 0 0 0 0 0.01"` : forêt 51 → 57 fps réels, lisière 46 → 54, montagne 53 → 56. **En plongée,** `"0 0 0 1.025"` : forêt 48 → 56, lisière 47 → 55, montagne 47 → 48.
- **Au-dessus du sol, rien ne change,** à 5 % près, le bruit du GPU : cumulus, orbite, globe, 160 et 440 km.
- **La forêt atteint les 60 fps réels, de justesse :** 16,8 ms de cadence. Lisière et montagne restent au-dessus des 16,6 ms.
- **Un autre moteur sur le GPU fausse le banc :** une session sur un autre worktree a fait monter cumulus_sol immobile de 11 à 15,7 ms ; signature, plus de 2 ms de GPU inactif et l'attente du CPU au-dessus du temps GPU. Les chiffres ci-dessus sont refaits sans elle.

**Les trouées de ciel tenaient la résolution des nuages** (`CloudsTemporal.hlsli`) :
- **Immobile, la résolution coûte 0,6 ms ; en vol, 1,8 ms en forêt, 3,6 en lisière.**
- **La cause :** 28 pixels par image en forêt, 45 en lisière, tracés par la résolution elle-même : des trouées de ciel nouvelles dans les feuilles, que ni l'historique ni les tuiles fraîches des 5×5 ne voient.
- **Chacun tient sa vague :** un rayon de ciel presque horizontal marche des centaines de kilomètres, et la passe attend la dernière vague. Sans ces traces, lisière 6,1 → 3,2 ms, forêt 2,8 → 1,6.
- **Désormais, sous la porte des 14 km** (`CloudTemporalHistoryFill`) : le texel le plus proche de l'historique, autour du pixel reprojeté, qui voit la même surface ; dans les 5×5, sinon sur une grille de 9×9 tous les 6 texels.
- **Une trouée que rien ne voit reste claire pour cette image,** puis les carrés 2×2 la retracent. Une surface que rien ne voit est tracée comme avant : ses nuages devant elle diffèrent de ceux de ses voisines.
- **Au-dessus de 14 km,** rien ne change.

**La grille du terrain en paires de floats, en vol** (`Noise.hlsli`, `TerrainComputePairs.hlsl`, `D3DApp::Draw`) :
- **La grille en doubles coûtait 2,4 ms des 3 du calcul des sommets en forêt** (round 4) : le GPU fait un double au 64ᵉ du rythme des floats.
- **En paires :** le point et la fréquence, chacun en deux floats, environ 48 bits ; le produit exact par la méthode de Dekker. Par octave, deux opérations en double au lieu de sept.
- **Le point est le même à 2·10⁻⁸ m près ;** seul le dernier bit d'une hauteur peut changer (`geometrie.md`).
- **Seulement en vol :** le maillage a glissé à cette image et à la précédente, et ses mailles font moins de 4 m, là où la grille passe en doubles. Après un saut, la première image est exacte ; à l'arrêt, tout le maillage est recalculé en doubles, une fois.
- **Un shader à part :** le même code exact, compilé dans un seul shader avec la voie en paires à côté, changeait ses derniers bits, et l'image immobile avec : lisière 1,11 niveau, 1,77 % au-delà de 8. Le shader exact reste le binaire d'avant, au bit près.
- **Le sommet sous la caméra reste exact :** la voie en paires le laisse sans terrain ; le shader exact, relancé avec le maillage gardé (`camPlane.z`), ne calcule que lui. Calculé en paires, il déplaçait la caméra d'une fraction de millimètre : lisière 1,56 niveau, 2,7 % au-delà de 8, dans les bords des feuilles.

**La garde de qualité :**
- **Immobile :** les dix vues identiques au bit près à `x64/r4_verif`, montagne comprise ; cumulus_sol identique à `x64/r8_avant_fixe` (`x64/r8_final_fixe`).
- **En mouvement, contre le binaire d'avant au même mouvement :** au sol, 0,05 à 0,09 niveau moyen, 0,02 % des pixels au-delà de 8. Des pixels isolés aux bords des feuilles et du pied des troncs, que le dernier bit du sol déplace d'une fraction de pixel. En montagne, 0,15 % de plaques au pied des troncs, à 4 km d'altitude où le dernier bit vaut 0,5 mm. Au-dessus du sol, identique.
- **Contre la passe pleine au même mouvement** (`x64/r6_full_*`) : les mêmes écarts qu'avant à 0,1 niveau près. Forêt 0,10 → 0,15, lisière 0,11 → 0,16, montagne 0,05 → 0,13 en vol rapide ; les autres vues inchangées, en vol rapide, lent et en plongée.
- **`banc_qualite.py`,** les 30 lieux de `x64/qualite_r2_final` (`x64/qualite_r8`) : aucun p95 ne bouge, mutation comprise.

**Ce qui borne encore :**
- **Lisière et montagne restent sous 60 fps en vol rapide,** 55 et 54. La lisière : nuages et air 3,8 ms, dont la trace 2,6. La montagne : le dessin du terrain, 7 ms, deux fois la forêt.
- **Le calcul du terrain en vol reste à 2,6 à 3,4 ms :** la marche vers le soleil, 0,6 à 1,3 ms, et le reste des sommets.
- **La piste de la marche vers le soleil :** sauter les pas dont la plus haute des mailles de l'anneau ne peut changer ni l'horizon ni la hauteur d'ombre. Exacte, mais une passe de plus.
- **Le placement des plantes en vol,** 2,1 à 2,6 ms : ses sols exacts sont aussi en doubles ; en paires, leur dernier bit entrerait dans la table gardée.
- **En vol :** `tools/tests/2026-10-29-optimisation-sol-vol-rapide.txt`.

**Essayé et retiré :**
- **Élargir la recherche dans les tuiles fraîches,** 9×9 puis 17×17 : lisière 6,1 → 4,1 ms ; sa boucle devient la nouvelle traîne.
- **Une recherche dense dans l'historique,** jusqu'à 25×25 : de même, 4,3 ms.
- **Laisser claire toute surface que rien ne voit :** des points isolés sur le relief lointain de la montagne, 0,25 % de plaques.
- **Remplir aussi les pixels glissés que les carrés 2×2 ne voient pas :** aucun cas mesuré.
- **Les paires dans le même shader que le calcul exact :** l'image immobile changeait (plus haut).
