# Nuages : repartir d'une référence publiée

**Référence locale avant validation, 27 octobre 2026 :** cinq captures cachées avaient permis de livrer le cumulus et la nappe, avec un jugement en vol encore attendu. La décision suivante était de juger silhouettes, traversée et ancrage à temps figé avant d'étendre la météo. L'utilisateur a ensuite validé le rendu local et la stabilité à l'approche. Il demande de compléter les familles locales par des cirrus avant la répartition à grande échelle ; les cumulonimbus restent une piste future. Voir la [notice actuelle](spike-nuages-reference.md).

**Archive de la V1, 27 octobre 2026 :** état initial et recherche avant le retour utilisateur. La stabilité proche est ensuite jugée en progrès ; les plafonds plans, les répétitions à moyenne distance, la répartition uniforme et les coûts restent insatisfaisants. La [notice courante](spike-nuages-reference.md) décrit les versions V2 et V3 de diagnostic. Les mesures ci-dessous ne valent pas validation du rendu en vol.

**Statut, 27 octobre 2026 :** premier spike Wicked compilé et prêt au jugement utilisateur. Quatre captures initiales puis deux contrôles après déformation du domaine ont été produits sans erreur. La V2 voxel reste disponible comme témoin ; aucun verdict de stabilité en vol.

**Premier jet implémenté :**

- Nouveau chemin `AtmosphereWicked.hlsl` / `CloudWicked.hlsli`, activé par `MYPLANETENGINE_CLOUD_WICKED=1`.
- Une coquille sphérique entre 3 et 6,5 km ; gradients verticaux mélangés selon le type météo.
- Météo 3D périodique aux périodes de 1 024 et 4 096 km, sans raccord de faces.
- Forme Perlin-Worley, érosion de détail, phase à deux lobes et diffusion multiple approchée.
- Textures de forme 128³, détail 32³ et météo 64³, toutes avec mips, soit 10 935 148 octets.
- Génération hors ligne par `tools/gen_wicked_cloud_textures.py` ; chargement DX12 une seule fois, aucun rebake animé.
- Vent par rotation globale ; déplacement du domaine de détail avec l'horloge météo.
- Forme de période 8 km, détail de période 1 km ; déformation continue du domaine par un champ 3D de période 37 km, amplitude ±1,5 km.
- La déformation utilise la texture météo et une oscillation de 1 200 s ; le cycle de 2 400 s reste continu.
- Entrées et phases des textures en double ; boucles de parcours en décalages locaux float.
- Racines raffinées en double et plancher par conversion entière ; les intrinsics HLSL seuls perdaient la précision attendue.
- Mode économique : pas proche de 48 m, borne lointaine de 240 m et un échantillon solaire.
- Mode référence : pas proche de 24 m, borne lointaine de 160 m et deux échantillons solaires.
- Le mode référence est une comparaison d'échantillonnage, pas une référence physique convergée.
- Aucun historique temporel, curl ni ombre nouvelle sur le terrain dans ce premier jet.
- Le filtrage de densité après seuil et la stabilité des transitions restent à juger ; les mips de bruit ne garantissent pas la conservation de transparence.

**Lancement et comparaison :**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-wicked.ps1
```

- Binaire du lanceur : `x64/NuageWicked/MyPlanetEngineWickedV1.exe`, SHA-256 `45AB7AD2F89FCF09FACF91B1E77CE4B46BCB8958F42C011833C41F05BD005F38`.
- Shader : `C629644327AC97820D29CD3B7F9627961A722A296551236EEB49BEB422FD05DB`.
- La première session ouverte utilise `MyPlanetEngineWicked.exe` ; V1 corrige seulement le compteur et les accents du titre, sans interrompre cette session.
- `-Temoin` lance l'ancien spike voxel V2 ; `-Static` fige la météo ; `-Reference` choisit la qualité fine ; `-Clear` coupe les nuages ; `-Build -NoLaunch` compile.
- C : économique / référence ; N : nuages oui / non ; Espace : pause météo ; B : opacité ; V : vitesse météo ×5.
- Palette `tools/tests/2026-10-27-nuages-wicked.txt` : F3 profil, F4 dans la couche, F5 au-dessus, F8 planète entière, F9 pôle et F10 autre continent.
- Le titre et les sidecars de capture mesurent « nuages+air » ; ils ne donnent pas le coût des seuls nuages.
- Source et licence épinglées dans `third_party/WickedEngine/`.

**Contrôles légers :**

- Build Debug x64 réussi ; les avertissements shader préexistants restent présents.
- Premier démarrage : profil, dessus, planète entière et une autre région ; fichiers `x64/WickedStartup/`.
- Ce premier réglage répétait visiblement la petite tuile de forme en vue oblique ; échelle et déformation du domaine ont été reprises avant livraison.
- Version à juger : `x64/WickedPreview/`, profil à 4,5 km et dessus à 10 km, météo figée, 1280 × 720.
- Profil : 9,91 ms/frame dont 8,76 ms nuages+air ; dessus : 7,51 ms/frame dont 6,10 ms nuages+air.
- Mesures ponctuelles sur GPU partagé ; elles ne fixent pas un budget garanti en vol.
- Le compteur et les accents du titre ont été corrigés après ces captures ; le champ de nuages reste identique.
- Les exécutables et shaders du témoin V2 sont inchangés, vérifiés par empreintes.
- Pas de campagne complète de bancs ; l'utilisateur fait les essais end to end.

**Constat local :**

- Le POC validait la stabilité d'une petite formation composée de quatre lobes.
- Le spike planétaire répétait cette forme, avec variations de placement et de couverture.
- Remplacer le calcul de densité par une texture ne changeait ni le parcours ni l'éclairage.
- Le test n'évaluait donc pas un système voxel comparable aux solutions de production.
- La correction des bandes latérales a commencé à imposer davantage de parcours, de supports et de variantes ; cette itération est arrêtée.

**Références consultées :**

| Référence primaire | Apport vérifié | Limite pour notre décision |
|---|---|---|
| [Wicked Engine, shader de rendu](https://github.com/turanszkij/WickedEngine/blob/5433f0a6cb0ed9ddfd41b7742978d038eaff70de/WickedEngine/shaders/volumetricCloud_renderCS.hlsl) et [modèle de densité](https://github.com/turanszkij/WickedEngine/blob/5433f0a6cb0ed9ddfd41b7742978d038eaff70de/WickedEngine/shaders/volumetricCloudsHF.hlsli) | HLSL existant ; météo, profils verticaux, bruits de forme et de détail, coquille sphérique, diffusion et ombres. | Projection météo XZ, coordonnées float et LOD arrondi dans cette version ; adaptation planétaire nécessaire. |
| [Licence de Wicked Engine](https://github.com/turanszkij/WickedEngine/blob/5433f0a6cb0ed9ddfd41b7742978d038eaff70de/LICENSE.txt) | MIT ; base de code adaptable avec attribution. | Auditer aussi les attributions des fonctions et ressources reprises. |
| [Unreal Engine, nuages volumétriques](https://dev.epicgames.com/documentation/unreal-engine/volumetric-cloud-component-in-unreal-engine?lang=en-US) | Documentation couvrant sol, vol et espace ; parcours volumétrique, reconstruction à plusieurs résolutions, diffusion multiple approchée et choix d'ombres. | Une architecture de référence ; aucun résultat garanti dans notre moteur. |
| [Nubis Evolved, 2022](https://www.guerrilla-games.com/read/nubis-evolved) et [Nubis³, 2023](https://www.guerrilla-games.com/read/nubis-cubed) | Deux générations documentées pour le vol dans les nuages ; Nubis³ associe voxels, champs de distance compressés, reconstruction du détail et accélération de la lumière. | Le système complet dépasse un simple cache de densité ; ce n'est pas une bibliothèque à brancher. |
| [Takram, three-clouds](https://github.com/takram-design-engineering/three-geospatial/blob/main/packages/clouds/README.md) | Implémentation ouverte avec ombres et reconstruction temporelle. | Le README annonce encore la couverture globale et les vues spatiales comme travaux futurs ; mentionne coutures et traînées temporelles. |

**Choix retenu :** partir d'un noyau HLSL neuf inspiré du modèle de Wicked Engine et des publications citées par ses auteurs. C'est un choix d'adaptation, pas une affirmation de supériorité sur les voxels.

**Premier spike borné :**

1. Une seule couche sphérique, avec une météo de couverture et de type ; cumulus et stratocumulus suffisent au premier jugement.
2. Des textures 3D périodiques précalculées de forme et d'érosion, utilisées dans un champ continu ; aucune population d'exemplaires du POC.
3. Une fonction de densité du lieu et du temps ; météo et coordonnées restent indépendantes de la caméra. La projection météo planétaire doit éviter les coutures.
4. Un éclairage conçu avec la densité : soleil, ciel, auto-ombre et diffusion multiple approchée. Éviter de juger des volumes avec l'ancien éclairage minimal du POC.
5. Un mode de référence sans historique et un mode économique comparables. La reconstruction temporelle peut ensuite amortir le calcul ; elle ne définit pas la forme des nuages.
6. Réutiliser la caméra, l'atmosphère et les références numériques en double ; reconstruire le parcours nuageux, sans reprendre les instances ni le plafond de pas du spike voxel.

**Points d'adaptation à traiter explicitement :**

- Les plages de distance de la référence ne prouvent pas la couverture depuis l'orbite ; conserver les intervalles visibles de coquille et tester l'extérieur de l'atmosphère.
- Le LOD fractionnaire et le filtrage doivent être étudiés après les seuils de densité ; la moyenne d'un bruit ne garantit pas la moyenne de la transparence.
- Le budget et la stabilité de notre intégration restent à mesurer ; les performances d'un autre moteur ne se transposent pas.

**Livraison rapide :** quelques vues comparables, un compteur GPU des nuages, pause météo, coupure des nuages et changement de qualité. L'utilisateur juge en vol le sol, le dessous, le profil latéral, l'intérieur, le dessus et l'orbite. Une première couche convaincante précède l'ajout des cirrus, des tempêtes et de la météo physique. Pas de campagne complète de bancs pour ce spike.

**Critère de poursuite :** le rendu doit progresser visuellement et rester cohérent à l'approche sur ces vues. Si l'adaptation du noyau publié n'y parvient pas, comparer une autre base plutôt qu'empiler des compensations.


## V2 avant diagnostic des bandes radiales

**Contrôles finaux, ponctuels en 720p figé sur GPU partagé :**

| Vue | GPU frame | Nuages + air |
|---|---:|---:|
| Au-dessus d'un champ convectif, 8 km | 19,05 ms | 13,12 ms |
| Vue oblique à 160 km | 9,11 ms | 3,22 ms |
| Planète entière à 8 000 km | 28,69 ms | 8,57 ms |

- Captures et empreintes : `x64/WickedV2FinalPreview/startup.json`.
- EXE : `E7583D53ED5418C2841D9879D2C214567771EB8256A716ACB6A45A5CC82B46E8`.
- Shader : `4BA776259F659AADC76E4A0E8944A466A3DD6A065A484720C92C6139CD6E83F1`.
- Météo : `AFE7F4212BE2D423A1CF1C582D25037B6E901B89B07B897E707B6FCD5A2AA939`.
- Aucun banc complet ; les temps de frame varient fortement avec les autres charges et ne garantissent pas le coût en vol.
- La V1 et sa session restent intactes ; aucun commit, tag ni push demandé.



## V3 : diagnostic des bandes radiales

**Bandes radiales : diagnostic et correction expérimentale :**

- Trois vues reproduites à météo figée : dessous à 1,4 km, oblique à 454 km et orbite à 2 601 km.
- Les bandes persistent sans composition atmosphérique ; celles de loin apparaissent aussi en opacité seule.
- Une forme macro constante conserve les anneaux ; l'intégration le long des rayons est en cause.
- Les pas V2 de 48 à 240 m peuvent traverser une transition très opaque sans l'intégrer suffisamment.
- Un pas uniforme de 12 m améliore le rendu mais coûte jusqu'à 219 ms pour nuages + air en orbite ; piste rejetée comme solution globale.
- La V3 garde les intervalles de parcours et leurs LOD ; elle subdivise les intervalles où début, milieu ou fin détectent du nuage, à 12 m maximum en Éco et 6 m en Référence.
- Le milieu original est réutilisé ; les sondes aux extrémités se limitent aux zones candidates du profil de hauteur.
- Le saut météo conservateur est conservé ; une densité nulle n'autorise aucun saut supplémentaire.
- L'intégration s'arrête dès que tous les canaux de transmission passent sous 0,003.
- Les formes, la météo et l'éclairage solaire restent ceux de la V2 ; les répétitions et le filtrage après seuil restent à reprendre.
- Ce raffinement est une quadrature approchée ; trois sondes ne prouvent pas l'absence d'une structure entre elles.
- Un premier raffinement commandé seulement par la variation de profondeur optique laissait des bandes proches ; sauvegarde dans `x64/Recovery/WickedV3AdaptiveFirst/`.

**Contrôles V3, ponctuels en 720p figé :**

| Vue | GPU nuages + air |
|---|---:|
| Dessous à 1,4 km | 31,67 ms |
| Oblique à 454 km | 26,26 ms |
| Orbite à 2 601 km | 38,55 ms |
| Stratus à 8 km, autre lieu | 45,88 ms |

- Quatre captures cachées ; compilation DXC réussie, aucun build natif requis.
- Les grandes bandes sont nettement atténuées sur ces images ; les répétitions restent visibles.
- Le coût régresse face à la V2 ; cette V3 sert au diagnostic et n'est pas déclarée acceptable.
- Artefacts et poses : `x64/WickedV3Preview/startup.json` ; comparaisons isolées : `x64/RadialDiagnostic/`.
- Aucun banc complet, aucun p95 ni validation du mouvement ; l'utilisateur conserve les vérifications en vol.
- Aucune session utilisateur interrompue ; aucun commit, tag ni push.
- Shader V3 : `F4FADA0649F52ABF931571077D67B4FDF62358014DC3AE67F3FA3A23071E4FEB`.


## V4 : variantes de parcours écartées

- **Déformation apériodique en HLSL :** deux bruits vectoriels monde à 48 et 13 km ; coût presque doublé, amélioration insuffisante de la grille. Sources et CSO dans `x64/Recovery/WickedV4Aperiodic/`, captures dans `x64/WickedV4AperiodicPreview/`.
- **Interpolation de densités positives :** trois mesures par pas, deux segments linéaires et positions d'éclairage prises à la profondeur optique moyenne ; bandes restantes. `x64/WickedV4IntegrationPreview/` et `x64/Recovery/WickedV4PositiveInterpolation/`.
- **Champ signé :** passage par zéro localisé avant intégration, sans remplir artificiellement toute la partie extérieure du pas ; amélioration insuffisante sur les vues proches et lointaines. `x64/WickedV4SignedPreview/` et `x64/Recovery/WickedV4SignedLinear/`.
- **Profil quadratique signé :** mêmes trois mesures, racines et masse analytique, inversion de la primitive par huit bissections ; contrôles CPU corrects mais bandes encore fortes et coût supérieur. `x64/WickedV4QuadraticPreview/` et `x64/Recovery/WickedV4Quadratic/`.
- **Albédo constant :** essai 0,95 sur l'interpolation signée linéaire ; bandes restantes, rendu plus plat. `x64/WickedV4AlbedoPreview/` et `x64/Recovery/WickedV4Albedo/`.
- **Décision :** ces parcours ne sont pas dans la livraison V4 ; la marche V2 est conservée. Le problème des rayons reste ouvert.
- **Repère bibliographique :** [Engel, Kraus et Ertl, 2001, High-Quality Pre-Integrated Volume Rendering](https://www3.cs.stonybrook.edu/~mueller/teaching/cse616/engel.pdf) intègre les fonctions de transfert entre mesures pour limiter les effets d'un échantillonnage insuffisant. Les essais ci-dessus n'en sont pas une implémentation complète ; aucune table de pré-intégration n'est livrée.


## V4 conservée comme témoin de la V5

# Spike Wicked : répartition et intégration du volume

**État, 27 octobre 2026 :** l'utilisateur juge le reste du rendu satisfaisant ; les deux défauts prioritaires sont les bandes radiales et les alignements en grille. La V4 isole la correction du bruit de forme et de ses mips, en conservant la marche V2. Les rayons restent non résolus ; les variantes plus coûteuses ont été écartées. Le jugement en vol reste à l'utilisateur.

**Lancer la V4 :**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-wicked-v4.ps1 -Static
```

- `-Temoin` lance la V2 conservée avec les mêmes positions et la même palette que la V4 ; `-Static` fige la météo ; `-Reference` affine l'échantillonnage ; `-Clear` coupe les nuages.
- `-Build -NoLaunch` copie le natif V2 et ses shaders communs dans une sortie distincte, puis compile seulement le shader Wicked V4.
- C : qualité ; N : nuages ; Espace : pause météo ; B : opacité ; V : vitesse météo.
- Palette `tools/tests/2026-10-27-nuages-wicked-v4.txt` : F1 sous les nuages, F2 près de la base, F6 stratus, F7 à 454 km, F8 à 2 601 km, F10 autre formation.
- Binaire : `x64/NuageWickedV4/MyPlanetEngineWickedV4.exe` ; les sorties V1, V2 et voxel restent distinctes.
- Le natif V4 est une copie du natif V2 ; les changements portent sur le shader et les données de forme.

**Limites verticales :**

- La coquille parcourue est une borne large de 1 à 9 km.
- La base locale varie entre 2 et 4 km ; l'épaisseur de référence entre 0,5 et 4 km.
- Les familles modulent l'épaisseur et la densité.
- La forme macro fait varier le bas de ±50 à ±150 m et le sommet de ±200 à ±600 m selon le type.
- Deux rampes adoucissent ces limites locales ; le profil de famille n'annule plus la densité avant la rampe de sommet.
- Les paramètres garantissent une densité nulle avant les limites de la coquille, environ 1,69 à 8,76 km au maximum.

**Répartition de référence :**

- La luminance du composite historique [NASA Blue Marble: Clouds](https://visibleearth.nasa.gov/images/57747/blue-marble-clouds/77558l) sert de masque de couverture.
- Le fichier original et les crédits sont dans `third_party/NASA/` ; les transformations sont dans le manifeste de l'asset.
- Cette donnée permet de juger le rendu sur des formations réelles ; elle n'est pas une météo procédurale ni une mesure de fraction nuageuse.
- Les types, bases et épaisseurs restent des champs synthétiques ; stratus, stratocumulus et convection sont mélangés par région.
- La carte 1024 × 512 RGBA8 se lit en longitude/latitude dans le monde météo, avec U périodique et V borné.
- Les volumes restent en 3D ; aucune image de nuage n'est plaquée sur une sphère.

**Correction de grille, V4 :**

- La première octave du Perlin périodique V2 n'utilisait qu'une cellule et un vecteur de gradient.
- Cette octave dominante se séparait selon les trois axes ; elle favorisait une distribution rectiligne.
- La base V4 emploie 3 cellules par axe, puis les fréquences 3, 6, 12, 24 et 48.
- Les cinq poids sont renormalisés vers la somme 1,984375 d'origine ; le rôle des canaux et la combinaison Perlin-Worley sont conservés.
- Les mips shape utilisent un filtre binomial périodique séparable `[1,3,3,1]/8` avant chaque sous-échantillonnage ; le niveau 0 n'est pas modifié par ce filtre.
- Les données V4 sont dans `assets/wicked-clouds-v4/` ; les anciennes restent dans `assets/wicked-clouds/` et la sortie V2.
- Détail, déformation 3D et météo planétaire sont bit à bit identiques à la V2.
- Le mip de la seconde lecture shape tient compte de sa fréquence plus élevée : +0,470553.
- Le mip de déformation suit son empreinte aux grandes distances, avec un minimum de 1 comme auparavant.
- Les alignements diminuent sur les captures ; ni l'absence complète de répétition ni la stabilité en mouvement ne sont validées.
- La chaîne de bruit reste périodique ; ce correctif ne constitue pas un champ de formes sans répétition à toute échelle.

**Régénérer les assets V4 :**

```powershell
python tools/gen_wicked_cloud_textures.py --output assets/wicked-clouds-v4 --shape-perlin-base 3 --shape-mip-filter binomial
```

- Les défauts du générateur restent `base 1 / box` pour les témoins.
- Le cache vérifie les paramètres, le filtre et l'empreinte du shape ; une taille correcte ne suffit pas.
- La couverture NASA, les profils d'altitude, les familles, l'animation, les phases de diffusion et l'albédo V2 sont conservés.
- Les formations individuelles changent avec le bruit de forme ; aucun placement particulier aux vues de test.

**Forme et distance :**

- Deux lectures Perlin-Worley utilisent des repères monde fixes et des fréquences différentes, avec ancrage numérique en double.
- Le mélange des canaux bruts précède un seul remap ; une double transformation introduisait un excès de densité.
- Le niveau macro varie continûment selon l'empreinte, jusqu'au mip 7 ; le détail s'érode séparément.
- L'éclairage solaire utilise un niveau fixe, indépendant du niveau de la vue.
- Le second ordre de diffusion prend une atténuation solaire réduite.
- Le filtrage reste approximatif : les mips de bruit ne garantissent pas la conservation de transparence.

**Vide et performances :**

- La météo réelle se lit au mip 1 ; ces texels restent moyennés.
- Les niveaux 2 et suivants conservent le maximum de R, comme borne de présence ; GBA restent moyennés.
- Un saut n'est permis que dans une case prouvée vide, rétrécie pour inclure les taps du filtre bilinéaire.
- Sa distance est bornée par les frontières du secteur sphérique, avec une marge de 20 %, et plafonnée à 10 km.
- Aucun saut ne repose sur un seul échantillon nul de densité.
- Le plein écran sans reconstruction temporelle reste coûteux dans certaines vues.

**Contrôle de livraison, ponctuel en 720p figé :**

| Vue | GPU nuages + air |
|---|---:|
| proche | 9.55 ms |
| moyen454 | 6.47 ms |
| orbite | 14.68 ms |
| stratus | 16.69 ms |

- Quatre vues cachées, plusieurs distances et trois lieux ; compilation DXC réussie.
- La V4 conserve le parcours V2 ; ces mesures sur GPU partagé ne sont pas un banc statistique de performances.
- Les bandes radiales restent présentes ; aucun résultat présenté comme une correction de ces bandes.
- Images et poses : `x64/WickedV4DeliveryPreview/startup.json`.
- Shader V4 : `D0777E1D538283313D6B348EE81BC0C69664B4BED9FF4CACF4CB688C4114CC47`.
- Shape V4 : `33A530A1147AF0615EA7C12E0F8D70811BF87ABE18C984466737EFF87AE954E0`.
- Aucun banc complet, aucun p95 ni vérification de mouvement ; l'utilisateur juge en vol.
- Le projet Debug x64 sort désormais dans V4 pour protéger les binaires V2 des builds ordinaires.
- Aucun commit, tag ni push demandé.

**Historique :** [V1 et recherche](spike-nuages-reference-historique.md). L'essai V2 purement synthétique a été écarté : `x64/WickedV2Preview/` et sauvegarde `x64/Recovery/WickedV2Start/`. La version NASA avant saut vide est conservée sous `x64/WickedV2ReferencePreview/`. Référence HLSL et licence : `third_party/WickedEngine/`.


---

## V5 : essai non retenu après jugement en vol

**Retour utilisateur, 27 octobre 2026 :** le LOD réduit le bruit sans corriger la répétition, avec des contours plus nets et un aspect moins bon. Les formations deviennent plus jointives dès la proximité. La répartition paraît trop étendue, sans organisation météorologique convaincante. Les planchers et plafonds restent trop nets ; les familles ne donnent pas de cirrus distincts.

- J désactive seulement le LOD ; les changements de morphologie V5 restent actifs.
- La hausse de couverture et le remplissage des creux dans les nappes affectent aussi le champ fin.
- Les détails techniques et mesures ci-dessous décrivent l'essai livré, pas un résultat validé.

# Spike Wicked V5 : formations et couverture optique

**État, 27 octobre 2026 :** prototype compilé, captures cachées produites ; jugement en vol confié à l'utilisateur. Les nappes et les grandes trouées remplacent une partie du semis de petites silhouettes. Le rendu lointain reste approximatif ; aucune validation globale de stabilité ou de réalisme.

**Lancer :**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-wicked-v5.ps1 -Static
```

- Départ à 271 km ; F6 retrouve cette vue.
- J : couverture optique active / volume détaillé seul, avec les mêmes formations V5 et la même météo.
- `-FineOnly` démarre avec le LOD optique coupé.
- `-Temoin` ouvre la V4 figée avec les mêmes positions et la même palette ; elle conserve sa propre morphologie.
- Espace : pause météo ; C : qualité fine ; B : opacité ; N : nuages ; V : météo ×5.
- F1/F2 : proximité et 10 km ; F3/F4/F5 : approche à 30/80/160 km ; F6/F7 : 271/454 km ; F8 : orbite ; F9/F10 : stratus ; F11 : autre front ; F12 : pôle.
- Binaire isolé : `x64/NuageWickedV5/MyPlanetEngineWickedV5.exe`.
- `-Build -NoLaunch` compile le seul shader V5 et le natif ciblé ; les shaders communs sont repris de la V4.

**Champ de formations commun :**

- La couverture NASA reste une référence visuelle et une borne de présence ; ce n'est pas une fraction nuageuse mesurée.
- Une lecture de bruit 3D à période 192 km module le type, la continuité des bancs et leur couverture.
- Une enveloppe de forme à période 32 km module la couverture à une autre échelle.
- Les régions fermées favorisent des nappes ; les régions convectives conservent davantage de cellules séparées.
- Les petits volumes utilisent le bruit primaire de période 8 km et l'érosion de détail.
- Toutes les phases sont calculées dans le monde météo, à ancrage double ; le vent et le temps restent partagés.
- La densité fine utilise des niveaux fixes : forme 0, détail 1 et déformation 1, y compris pour l'enveloppe large fine.
- La caméra choisit le mélange des représentations ; elle ne déplace pas les phases du champ fin.
- Les formes individuelles changent par rapport à V4, mais les bases de lumière, les profils verticaux et leur coquille 1–9 km sont repris.
- Le masque de banc reste nul quand la météo source est vide ; la preuve Rmax des sauts V4 reste conservatrice.

**Table optique :**

- `tools/gen_wicked_optical_lut.py` échantillonne le modèle fin sur 512 colonnes et 48 pas verticaux, avec deux azimuts.
- La table moyenne les transmittances après exponentielle : `E[exp(-k × intégrale de densité)]`.
- Elle n'applique pas l'exponentielle à une densité déjà moyennée.
- Texture 32³ RGBA8, six mips stockés ; seul le mip0 sert au rendu.
- X : 32 couvertures entre 0 et 1.
- Y : 4 types × 8 épaisseurs entre 0,5 et 4 km, index `type × 8 + épaisseur`.
- Z : 32 cosinus absolus de vue entre 0,08 et 1.
- RGB : coefficients d'extinction 71/86/100 par km ; A : coefficient 0,2 × 86 pour le second ordre.
- Quatre lectures interpolent séparément type et épaisseur ; le filtrage matériel interpole couverture et angle.
- Le résultat optique de vue est moyenné sur cinq points de l'empreinte, après les lectures de table ; les contours de l'enveloppe sont donc filtrés aussi.
- Couverture zéro donne exactement une transmission unitaire ; les valeurs sont bornées et le cache vérifie les paramètres et les empreintes.
- La table mesure une population statistique ; elle ne précalcule pas chaque colonne géographique de la planète.

**Représentation lointaine :**

- Une coquille représentative fournit un point monde dans le segment visible du rayon.
- La météo, le type et l'enveloppe de ce point alimentent la table optique.
- Un éclairage moyen réutilise soleil, phase et ambiance V4 ; sa diffusion est approximative.
- La transition mélange directement lumière prémultipliée et transmittance, puis une profondeur pondérée par l'opacité.
- Elle s'étend d'une empreinte de 0,12 km à 0,65 km par pixel ; à son terme, le parcours micro détaillé est évité.
- Les rayons rasants sans croisement de la coquille représentative utilisent le milieu du segment ; un cap de hauteur adoucit le limbe.
- Le mode J désactivé conserve entièrement le volume fin V5 et permet de juger cet apport séparément.
- Aucun historique temporel ni nouveau traitement des rayons détaillés n'est ajouté.

**Limites à juger en vol :**

- La table suppose un milieu local stationnaire et une couche plane ; les très petits cosinus sont bornés à 0,08.
- Le cap au limbe et l'éclairage moyen ne sont pas une intégration physique complète d'une longue traversée planétaire.
- Le modèle statistique n'est pas la moyenne exacte de chaque voisinage local ; la conservation des petites trouées pendant l'approche reste à contrôler.
- L'aspect lointain peut devenir trop plat ou trop opaque ; la transition de lumière peut nécessiter un réglage.
- Les bandes radiales du parcours fin restent un problème ouvert.
- Aucun p95, banc complet ni validation de mouvement ; l'utilisateur fait les vérifications de bout en bout.

**Génération :**

```powershell
python tools/gen_wicked_optical_lut.py --source assets/wicked-clouds-v4 --output assets/wicked-clouds-v5
```

- Les sept fichiers de source V4 sont copiés sans changement ; seule la table optique est ajoutée.
- La texture occupe 149 796 octets avec ses mips ; aucune reconstruction de cette table par image.
- Le manifeste décrit les équations, les paramètres, le temps de génération et les empreintes.

**Contrôle court de livraison, 720p figé sur GPU partagé :**

| Vue | GPU nuages + air |
|---|---:|
| motifs271 | 5.40 ms |
| orbite | 4.98 ms |

- Quatre vues initiales V5, puis deux vues finales après le filtre optique ; comparaisons ciblées volume seul et témoin V4 à 271 km.
- Images finales, poses et empreintes : `x64/WickedV5DeliveryPreview/` ; comparaisons : `x64/WickedV5OpticalPreview/`, `x64/WickedV5FinePreview/`, `x64/WickedV5WitnessPreview/`.
- Les temps de frame sont perturbés par d'autres charges ; ces valeurs ne constituent pas une mesure statistique.
- Natif : `E1C1CCF785171ADD3EA52ED293711C39C8B999A60BC54BEEA08AA0F756EE3C21`.
- Shader : `4C4212025774F01983B32C9F34A5C9B20E6738B261C7F0DA4CAAE6E917FBB28C`.
- Table : `35D941E685664C2CEAE26A72F95509F3B24BACF94F73BA11C252349BB31ABE87`.
- Les binaires V4 et V2 restent intacts ; aucun commit, tag ni push demandé.

**Historique :** [recherche, V1 à V4 et essais écartés](spike-nuages-reference-historique.md).


---

## Diagnostic après V5, avant l’essai météo A

# Spike nuages : diagnostic après la V5

**État, 27 octobre 2026 :** V5 non retenue après jugement en vol. La V4 reste le témoin de comparaison ; elle conserve des répétitions et des bandes radiales. Aucune de ces versions n'est une solution planétaire validée.

**Constats :**

- Le LOD V5 rend l'aspect moins bon : les répétitions persistent, les contours deviennent plus nets et le bruit disparaît sans organisation convaincante.
- La V5 change aussi les formes proches : hausse de couverture dans certaines régions et remplissage des creux pour joindre les nappes.
- J désactive seulement le LOD ; il ne rétablit pas les formes V4.
- Les bases et sommets restent trop plans malgré leurs rampes continues et leurs variations de hauteur.
- Les familles actuelles modulent une même recette de densité ; aucun modèle distinct de cirrus n'est implémenté.

**Diagnostic du code :**

- Le volume est borné par des profils d'altitude locaux ; ce n'est pas un clipping graphique.
- La base utilise une douceur de 80 à 160 m ; le sommet, de 160 à 400 m.
- L'extinction élevée peut rendre ces rampes rapidement opaques ; adoucir seulement leur interpolation ne garantit pas un contour naturel.
- La coquille 1–9 km sert au parcours ; elle ne doit pas être confondue avec les limites visibles des profils locaux.
- La carte NASA fournit un proxy de couverture issu de luminance ; G/B/A restent synthétiques et ne décrivent pas un état météo cohérent mesuré.
- La conversion de luminance relève les faibles valeurs par `0,25 + 0,5 × sqrt(L)` au-dessus de `L = 0,03`.
- Audit du mip0 V4 partagé avec V5 : R dépasse 0,03 sur 79,81 % de l'aire sphérique, moyenne R de 0,4038.
- Ces nombres décrivent le paramètre de présence ; ils ne mesurent pas la fraction nuageuse rendue.

**Comparaison conservée :**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-wicked-v5.ps1 -Temoin -Static
```

- Ouvre la V4 figée avec les mêmes positions et la même palette que la V5.
- Sans `-Temoin`, le lanceur ouvre la V5 rejetée pour reproduire l'essai ; `-FineOnly` en conserve les formes sans LOD.
- F1/F2 : proximité et 10 km ; F3/F4/F5 : 30/80/160 km ; F6/F7 : 271/454 km ; F8 : orbite ; F9/F10 : nappe ; F11 : autre région ; F12 : pôle.
- Espace : pause météo ; C : qualité fine ; B : opacité ; N : nuages ; V : météo ×5.
- Aucun binaire, shader ou réglage modifié à la suite de ce diagnostic ; session utilisateur conservée.

**Suite à isoler :**

- Évaluer la répartition régionale sans changer simultanément le LOD et les formes proches.
- Distinguer les recettes de densité des amas, des nappes et d'une éventuelle couche fibreuse haute.
- Traiter les contours de volume avant de reprendre le filtrage lointain.
- Conserver les témoins et remettre rapidement chaque essai à l'utilisateur pour le jugement en vol.

**Historique :** [recherche, V1 à V5 et essais écartés](spike-nuages-reference-historique.md).


---

## Météo A : essai de répartition, conservé comme témoin des formes

# Essai météo A : répartition seule sur V4

**État, 27 octobre 2026 :** comparaison préparée, trois paires de captures cachées contrôlées. Essai remis à l'utilisateur pour le jugement en vol. La V5 n'est pas retenue ; la V4 figée sert de témoin.

**Lancer la candidate :**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-meteo-a.ps1 -Static
```

**Lancer le témoin aux mêmes positions :**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-meteo-a.ps1 -Temoin -Static
```

- Départ en orbite ; F1 retrouve la vue planétaire.
- F2/F3 : ancienne vue des motifs à 271/454 km ; F4/F5 : amas proches et vus de dessus.
- F6/F7 : nappe connue à 8/271 km ; F8/F9 : région dense à 400/10 km.
- F10/F11 : région de trouées à 271/30 km ; F12 : pôle.
- Les mêmes douze positions et soleils sont utilisés pour les deux cartes.
- Espace : pause météo ; N : nuages ; C : qualité ; B : opacité.
- `-NoLaunch` prépare la candidate sans ouvrir de fenêtre ; aucun build requis.
- Exécutable isolé : `x64/NuageWickedMeteoA/MyPlanetEngineWickedMeteoA.exe`.
- `-Temoin` n'écrit ni dans la V4 ni dans ses assets.

**Une seule variable :**

- La luminance L vient de la même image NASA, redimensionnée de la même manière et orientée dans le même repère.
- Ancienne courbe : R nul sous L=0,03, puis `0,25 + 0,5 × sqrt(L)`.
- Candidate : `R = 0,75 × smoothstep(0,08, 0,68, L)`.
- Les seuils 0,08/0,68 et le plafond 0,75 sont des réglages de cet essai visuel, pas une loi météorologique.
- Les faibles luminances n'ont plus de plancher positif ; les régions fortes gardent une couverture élevée.
- R reste un coefficient de la recette de densité ; ce n'est pas une fraction nuageuse mesurée.
- Changer R modifie les silhouettes et la continuité locales via le seuillage existant ; la recette de forme reste la même.
- Mip1 moyen et mips2+ par maximum conservateur, comme le témoin.

**Ce qui est conservé :**

- Binaire et tous les shaders copiés de la V4 figée ; aucune compilation ni nouvelle lecture GPU.
- Trois textures 3D identiques bit à bit ; GBA identiques sur les onze mips de la carte.
- Profils verticaux, éclairage, animation et parcours V4 ; aucun LOD ou remplissage des nappes V5.
- Planchers et plafonds trop nets, répétitions et bandes radiales restent ouverts ; aucun cirrus distinct.
- La répartition des types et des altitudes reste synthétique ; cette carte ne simule pas un état météo cohérent complet.

**Contrôle court :**

- Six captures cachées : trois vues par carte, en orbite, à 271 km et au-dessus d'une nappe proche.
- Les zones faibles sont moins couvertes ; le motif répétitif reste visible dans les bancs denses à moyenne distance.
- L'essai confirme que la répartition ne suffit pas à expliquer ce motif ; aucun autre réglage n'a été ajouté pour le masquer.
- Les copies de l'exécutable et du shader ont les mêmes empreintes que le témoin.
- Moyenne R pondérée par l'aire : 0,403798 pour V4, 0,215494 pour la candidate.
- Cette mesure ne donne pas le taux de couverture rendu.
- Données et comparaisons : `x64/WickedWeatherACompare/` ; GPU partagé, pas de mesure de performance ni de validation de mouvement.
- La densité peut modifier la longueur des parcours malgré un shader identique ; aucun gain de performance promis.

**Reproduction :**

- Générateur : `tools/gen_wicked_weather_a.py` ; assets : `assets/wicked-clouds-weather-a/`.
- Le cache dépend des paramètres et des empreintes de ses entrées ; génération inférieure à une seconde dans cet environnement.
- Carte SHA-256 : `4AE42A455682D0ECD0862E22361947EBF5BEA0615A6FF0F6170AD6092B8FBBF3`.
- Exécutable SHA-256 : `E7583D53ED5418C2841D9879D2C214567771EB8256A716ACB6A45A5CC82B46E8`.
- Shader SHA-256 : `D0777E1D538283313D6B348EE81BC0C69664B4BED9FF4CACF4CB688C4114CC47`.
- Aucun commit, tag ni push demandé.

**Historique :** [recherche, V1 à V5 et diagnostic](spike-nuages-reference-historique.md).


**Formes A, contrôle intermédiaire :** la première recette de nappe au champ large non contrasté donnait une couche trop uniforme. Le champ au mip3 a p10=0,595, médiane=0,719 et p90=0,825 ; sa faible amplitude passait presque partout le seuil de couverture. Une seule correction remappe ce champ avant le seuil, et normalise séparément sa variation de support. Sources et shader initiaux dans `x64/Recovery/FormsAInitial/`, trois premières paires dans `x64/WickedFormsACompare/` ; les deux comparaisons finales sont dans `x64/WickedFormsAFinalCompare/`.


---

## Formes A : retour en vol, essai insuffisant

**Retour utilisateur :** tailles et formes répétitives, surfaces planes en haut et en bas, grands contours trop lisses et géométriques. Les fades appliqués après seuillage n'ont pas suffi à corriger les silhouettes. Formes A reste un témoin, pas une solution validée.

# Formes A : cumulus et nappes sur la météo A figée

**État, 27 octobre 2026 :** shader compilé, comparaisons courtes produites et inspectées ; jugement en vol à l'utilisateur. Météo A avec le rendu V4 est conservée comme témoin exact.

**Lancer :**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-formes-a.ps1 -Static
```

**Comparer au témoin météo A :**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-formes-a.ps1 -Temoin -Static
```

- F1/F2 : profil et base des cumulus ; F3/F4 : leurs sommets depuis 8 et 10 km.
- F5/F6 : base et profil d'une nappe ; F7/F8 : vue depuis 6 et 30 km.
- F9/F10 : autre nappe ; F11 : motifs à 271 km ; F12 : planète entière.
- Les deux modes emploient les mêmes positions, soleils et horloge météo.
- Espace : pause météo ; C : qualité ; N : nuages ; B : opacité.
- `-Build -NoLaunch` compile le seul shader de cet essai et prépare son dossier ; aucun build natif.
- Sortie : `x64/NuageWickedFormesA/MyPlanetEngineWickedFormesA.exe`.
- Témoin : `x64/NuageWickedMeteoA/`, assets figés dans `wicked-clouds/`, empreintes dans `witness-forms-a.json`.
- Le lanceur vérifie le témoin et n'y écrit pas ; sa session en cours est conservée.

**Recettes distinctes :**

- La carte météo A reste inchangée ; G mélange continûment nappe et cumulus, sans changement de répartition régionale.
- Les cumulus utilisent le champ de forme 3D primaire de période 8 km et un apport large.
- Les nappes utilisent le champ large de période 32 km, au mip3 fixe ; leur support vertical est moins épais.
- Le champ brut de nappe est remappé par `smoothstep(0,55, 0,85, sheetMacro)` avant le seuil de couverture pour conserver de larges trouées.
- Les hauteurs locales utilisent `smoothstep(0,50, 0,90, sheetMacro)` ; elles ne dépendent ni de macroLod ni de la caméra.
- B donne toujours une base de 2 à 4 km, A une épaisseur de référence de 0,5 à 4 km.
- La fraction de hauteur vaut 0,35 pour les nappes et 0,88 pour les cumulus.
- L'amplitude de base vaut 0,10 à 0,30 km ; celle du sommet, 0,18 à 0,90 km.
- Les demi-largeurs de fade sont de 0,22 à 0,40 km en bas et de 0,24 à 0,50 km en haut.
- Les fades smoothstep sont appliqués après couverture et érosion ; aucun seuil ne les recoupe ensuite.
- Les phases du champ large viennent des coordonnées absolues en double et d'un reste local float ; l'ancre ne déplace pas les motifs.

**Support et coût :**

- Borne basse globale : `2 − 0,15 − 0,40 = 1,45 km`.
- Borne haute globale : `4 + 4 × 0,88 + 0,45 + 0,50 = 8,47 km`.
- La densité s'éteint strictement avant la coquille d'accélération 1–9 km ; aucun clamp de hauteur ne sert à imposer ces bornes.
- Les rejets locaux emploient les mêmes extrema conservateurs avant les lectures de forme.
- Cinq lectures au maximum par densité occupée, comme V4 : carte météo, déformation, deux formes, détail.
- Aucun nouveau volume, ressource, historique, parcours ou passe ; seul `AtmosphereWicked.cso` change.

**Contrôles :**

- Compilation DXC ps_6_0 O3 réussie ; avertissement préexistant de shift dans Materials.hlsli.
- Exécutable et quatre textures identiques au témoin ; tous les autres shaders et le code du marcher, de la lumière et de la composition inchangés.
- Trois paires initiales, puis deux paires ciblées après la correction du contraste de nappe ; deux lieux, cumulus et nappe.
- Les trouées de nappe sont plus larges ; les fades et sommets des cumulus changent visiblement dans ces captures.
- Données finales : `x64/WickedFormsAFinalCompare/` ; les captures ne valident ni le mouvement, ni toutes les distances, ni le réalisme.
- GPU partagé ; aucun p95, banc complet ou gain de performance annoncé.
- Shader final SHA-256 : `6D65FF9FF893418A57A165E993AA88B01F7CB21D6B45086B65586C16395D0CED`.
- Carte météo SHA-256 inchangée : `4AE42A455682D0ECD0862E22361947EBF5BEA0615A6FF0F6170AD6092B8FBBF3`.

**À juger en vol :**

- Différence lisible entre nappes et cumulus ; bases et sommets moins artificiels, y compris pendant la traversée.
- Ancrage des formes lors de l'approche à météo figée.
- Les nappes peuvent rester très lisses ; les cumulus denses peuvent encore paraître solides et les longues faces verticales restent à juger.
- Aucun cirrus ni nouveau LOD ; les répétitions lointaines et les bandes radiales restent des sujets distincts.
- Aucun commit, tag ni push demandé.

**Historique :** [recherche, essais Wicked et météo A](spike-nuages-reference-historique.md).


**Formes B, préparation :** un premier potentiel utilisant la plage brute du bruit donnait un voile uniforme. Recentrage et contraste borné sans plateau, puis variation de hauteur et déformation de domaine renforcées. La texture météo3D a un alpha constant à1 ; le mélange des bandes utilise RGB, après contrôle des données. Première comparaison densité seule dans `x64/WickedFormsBCompare/`, livraison ciblée dans `x64/WickedFormsBFinalCompare/`.


---

## Formes B : perturbation à la mauvaise échelle

**Retour utilisateur :** la déformation a étiré les nuages individuels en formes étranges, alors que la demande visait les grands courants et l'organisation des ensembles. Le warp local de ±12 km est donc retiré au profit d'un réglage doux. Le transport macro doit modifier la couverture R aussi, pas seulement les frontières GBA. Formes B reste figée comme témoin.

# Formes B : volumes, échelles et frontières de régimes

**État, 27 octobre 2026 :** prototype compilé et contrôles courts ; jugement en vol à l'utilisateur. Formes A est jugée insuffisante et conservée comme témoin exact.

**Lancement :**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-formes-b.ps1 -Static
```

- `-Temoin` ouvre Formes A avec sa météo A figée.
- `-MeteoA` ouvre la densité B avec l'ancienne carte, pour isoler la perturbation des régimes.
- `-Build -NoLaunch` compile seulement le shader B et prépare les données.
- F1–F4 : cumulus ; F5–F8 : nappe ; F9/F10 : autre nappe ; F11 : 600 km ; F12 : 1 600 km.
- Espace : pause météo ; C : qualité ; B : opacité ; N : nuages.
- Binaire : `x64/NuageWickedFormesB/MyPlanetEngineWickedFormesB.exe`.

**Changement de modèle :**

- La silhouette n'est plus un champ rempli entre deux rampes verticales à plateau.
- Potentiel : `p = noise3D − (1 − couverture) − z² − 0,12 × erosion` ; densité `gain × max(p,0)²`.
- Le champ 3D et la pénalité de hauteur forment ensemble la surface ; la densité est C1 à zéro.
- Deux domaines de périodes 8 et 29,3 km, orientés différemment, sont mélangés avec des poids mondiaux variables.
- Le champ large de période 128 km sert à la déformation, aux poids et à la variation de hauteur, au mip1 fixe.
- Déformation maximale par composante de ±12 km ; aucun repère ou poids choisi par la caméra.
- Contraste du bruit borné par une fonction rationnelle lisse, sans plateau à0 ou1 ; gain de0,65 pour les nappes à0,55 pour les cumulus.
- Centre nominal `base + 0,4 × épaisseur`, déplacé de ±0,25 km ; demi-hauteur maximale de `0,35+0,1T` à `0,5+0,4T` selon le type.
- La demi-hauteur locale varie de60 à100% de sa borne pour les nappes, de30 à100% pour les cumulus.
- Support conservateur global entre1,25 et7,95 km, strictement dans la coquille1–9 km ; pas de clamp pour faire respecter ces bornes.

**Frontières macro :**

- L'audit désigne G comme cause probable des frontières familiales trop lisses ; ce n'est pas une preuve par projection des captures utilisateur.
- Météo B déforme ensemble G/B/A sur la sphère, avec deux bandes de bruit17 et43 et une borne angulaire de0,08 rad.
- R est identique bit à bit sur les onze mips ; la couverture NASA et les maxima conservateurs restent inchangés.
- Les trois textures 3D restent identiques ; GBA sont filtrés par moyenne après la déformation.
- C'est une perturbation visuelle de régimes synthétiques, pas une simulation météorologique.
- Générateur : `tools/gen_wicked_weather_b.py` ; données et manifeste : `assets/wicked-clouds-weather-b/`.

**Isolation et contrôle :**

- Exécutable, ressources, éclairage, extinction, marcher et composition identiques au témoin ; seul le shader de densité et, en mode normal, GBA changent.
- Maximum de cinq lectures par densité occupée, carte incluse ; le nombre de pas réellement parcourus peut changer avec l'opacité.
- DXC réussi ; avertissement préexistant dans Materials.hlsli. Empreintes du témoin et invariants R/textures contrôlés.
- Comparaisons courtes sur deux lieux proches et une vue à600 km ; aucun banc complet ni validation de mouvement.
- Données initiales : `x64/WickedFormsBCompare/` ; livraison : `x64/WickedFormsBFinalCompare/`.
- Les répétitions lointaines et l'effet de couche restent à juger ; aucun résultat global validé.
- Le contrôle final montre des hauteurs plus variables mais des répétitions encore visibles à600 km ; aucun des trois défauts n’est déclaré résolu.
- Temps ponctuels nuages+air : proche17,40 ms contre4,92 ms pour le témoin ; à600 km10,27 ms contre9,42 ms. GPU partagé, valeurs sans portée statistique ; la régression proche reste un problème.
- Shader livré SHA-256 : `5F275B573E8213F6F78D5D88A5C834CFEA6255DCD72309906C2A74F1A6FDFFEF`.
- Aucun commit, tag ni push demandé.

**Historique :** [Wicked, météo A et Formes A](spike-nuages-reference-historique.md).


---

## Courants C : avant la reference locale Frostbite

**Bilan :** le transport a corrigé l'échelle de la perturbation, sans résoudre les silhouettes, la répétition et les profils trop plans. La lecture du rapport Frostbite a motivé une référence locale, avec bruits auteur et choix de profils explicites. Courants C reste figé comme témoin.

# Courants C : organisation macro, formes locales préservées

**État, 27 octobre 2026 :** comparaison compilée et deux paires de captures macro inspectées. Remise en vol à l'utilisateur. Correction de l'échelle de perturbation ; aucune résolution annoncée des répétitions ou plafonds.

**Lancer :**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-courants-c.ps1 -Static
```

- Départ sur la vue utilisateur à180 km ; F11 retrouve cette vue.
- F12 : autre ensemble dans l'hémisphère sud à1 600 km ; F1–F10 : contrôles proches déjà connus.
- `-MeteoA` : même shader C, carte météo A d'origine ; cette comparaison isole le transport macro.
- `-Temoin` : Formes B et sa météo B figées, avec la forte déformation locale rejetée.
- `-Build -NoLaunch` : compile uniquement le shader C et prépare les données.
- Espace : pause météo ; C : qualité ; N : nuages ; B : opacité.
- Sortie isolée : `x64/NuageWickedCourantsC/MyPlanetEngineWickedCourantsC.exe`.

**Échelles séparées :**

- Le shader C reprend B avec une seule correction de forme : amplitude du warp local24 vers3, soit ±1,5 km par composante au lieu de ±12 km.
- La nouvelle organisation est précalculée dans la carte météo ; elle ne déforme pas les coordonnées du bruit3D local.
- Source : météo A figée dans `x64/NuageWickedFormesA/wicked-clouds/`, sans la perturbation GBA de B.
- RGBA sont transportés ensemble sur la sphère par un champ tangent très lisse, aux fréquences2 et4.
- Une étape d'exponentielle sphérique transporte la référence en arrière ; aucune intégration temporelle nouvelle dans le moteur.
- Échelles de maille estimées à3 189 et1 594,5 km ; proxies de corrélation mesurés à850 et426 km.
- Déplacement médian182 km, maximum573 km ; borne638 km.
- Ce champ est un transport statique de référence, pas une simulation physique des courants atmosphériques.
- La couverture R change cette fois ; mip1 moyen et mips2+ par maximum conservateur sont reconstruits. GBA sont moyennés.
- Les trois textures3D, les phases locales, la lumière, le marcher, les ressources et le code natif sont conservés.

**Contrôles :**

- DXC réussi ; avertissement préexistant dans Materials.hlsli.
- Différence shader B/C limitée au retour du warp24 vers3 ; témoin B intact, quatre assets réels figés dans `witness-courants-c-assets/`.
- Mips RGBA vérifiés indépendamment ; aucun pli mesuré sur523 264 cellules de la carte, rapport d'aire orientée minimal0,245.
- Deux paires cachées, à180 km sur la vue utilisateur et à1 600 km dans le sud, avec le même shader C et les cartes A/C.
- Les ensembles se déplacent et changent de contour sans la torsion forte des coordonnées locales de B ; la répétition fine persiste.
- Comparaisons et empreintes : `x64/WickedCurrentsCCompare/` ; source carte, manifeste et champs : `assets/wicked-clouds-weather-c/`.
- Aucun banc complet, p95, gain de performance ou verdict de stabilité en vol.
- Shader C SHA-256 : `F2D856EDABA17B6FD44E32D3222C1B88B4BCD9D015738CBF9E0AE04474B8F31C`.
- Carte C SHA-256 : `DF67169C5DBC7E1197B043D1853A4A91EAAC20E96C09CF204A383AE4C5C8988E`.
- Aucun commit, tag ni push demandé.

**Limites :**

- La recette locale et ses défauts de silhouettes, de filtrage lointain et de coût proche restent ceux de B, avec une déformation réduite.
- Transporter la référence ne crée pas une météo dynamique ni une variété nouvelle de formations.
- La carte est filtrée sur sa grille1024×512 ; le contrôle de cellules est discret et ne prouve pas toutes les déformations sous le texel.

**Historique :** [recherche, météo A, Formes A et B](spike-nuages-reference-historique.md).
