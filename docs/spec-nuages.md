# Les nuages du jeu

**Les nuages du jeu, de l'orbite au sol, sur toute la planète.** Un volume en deux couches, tiré d'une carte météo planétaire calculée au démarrage sur le climat, et de deux bruits 3D fixés sur la planète, que le vent porte vers l'est. Ils ombrent le sol et la mer, et la verrière du vaisseau les traverse.

**État, 2026-10-31 :** le seul chemin, actif par défaut, sans variable (commit `3663177`). La lumière de l'air leur est rendue le 2026-10-30. Depuis le 2026-10-31, leur carte météo est tirée du climat, tag `piste/nuages-climat` : à juger en vol, `tools/tests/2026-10-31-nuages-climat.txt`. Le même jour, leur lumière, leur eau et leur pixel sont refaits pour la vue d'orbite, tag `piste/orbite-rendu` (`spec-rendu-orbite.md`) : à juger en vol, `tools/tests/2026-10-31-orbite-rendu.txt`.

- **Le code :** `MyPlanetEngine/Clouds.hlsli`, `CloudsTemporal.hlsli`, `AtmospherePass.hlsl` et ses trois enveloppes `CloudTrace.hlsl`, `CloudTraceHalf.hlsl`, `CloudResolve.hlsl` ; `D3DApp.cpp` et `.h` ; la carte météo, `Climate::Weather` dans `Climate.cpp` ; pour la verrière, `ShipWeather.hlsl`, `Ship.cpp`.
- **Les données :** `assets/clouds`, trois volumes de bruit et leur `manifest.json` ; la carte météo se calcule au démarrage.
- **L'origine :** les nuages volumétriques de Wicked Engine, adaptés (MIT, `NOTICE`) ; les bruits et les profils de Frostbite ; la carte sur la sphère. Les spikes qui y ont mené sont au log (`log/README.md`, les nuages) ; l'histoire de cette spec, dans `log/spec-nuages-historique.md`.
- **L'essayer :** `tools/lance.ps1 -Parcours tools/tests/2026-10-27-nuages-planete.txt` ; pour la lumière de l'air, `tools/tests/2026-10-30-lumiere.txt` (`lancement.md`).

## Le modèle

**Deux couches, dans une coquille de 2 à 13 km d'altitude.**
- **Les nuages bas,** de 2 à 8 km : cumulus et nappes.
- **Les cirrus,** de 9 à 13 km : une enveloppe de 0,35 à 0,6 km de demi-épaisseur, centrée vers 11 km et ondulée.
- **Le rayon de la planète :** 6 378 km.

**La carte météo couvre la sphère entière,** en 1 024 × 512 ; U la longitude, V la colatitude, nord en haut. Elle se calcule au démarrage sur le climat (la section suivante).
- **R :** la part du ciel couverte par les nuages bas, jusqu'à 0,28 ; au-dessus, leur épaisseur, jusqu'à 0,9 ; sous 0,03, pas de nuage.
- **G :** leur famille, 0 la nappe, 1 le cumulus ; entre les deux, les nuages épais des fronts.
- **B :** les cirrus, 0,286 au plus : enclumes, courant-jet, boucliers des fronts chauds.
- **Elle est lue au mip 0,** environ 39 km à l'équateur, en B-spline cubique : la part couverte la seuille d'une fonction raide, et l'interpolation bilinéaire y dessinait des carrés de 80 à 160 km. Elle porte ses formes jusqu'à 80 km. Ses mips 2 et plus gardent le maximum de R et de B, pour prouver le vide ; sa marge couvre les deux texels du filtre.

## La carte météo, tirée du climat

**Une climatologie des nuages et un instant de sa météo, calculés au démarrage par graine** (`Climate::Weather`), après la carte du climat (`spec-climat.md`), sur ses champs et les grandes formes du relief. Chaque texel se calcule seul ; la même graine donne la même carte, au bit près.

**R est la part du ciel couverte, vue d'en haut.**
- **Sous une fraction c de 0,92,** R vient d'une table mesurée sur les trois volumes, colonne de 6 km, sous la loi du rendu : la forme de 32 km et son octave de 128 km seuillées, l'eau indépendante de R hors l'épaisseur :

| R | 0,08 | 0,10 | 0,12 | 0,14 | 0,16 | 0,18 | 0,20 | 0,22 | 0,24 | 0,26 | 0,28 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| opacité | 0,06 | 0,13 | 0,21 | 0,32 | 0,44 | 0,55 | 0,66 | 0,75 | 0,82 | 0,88 | 0,92 |

- **Au-dessus,** les masses : R = 0,28 + 0,62 e, e l'épaisseur, que le rendu lit pour l'eau du nuage, `0,25 + 0,75 e`. Une nappe à e = 0 garde 8 % de trous.
- **L'épaisseur par classe :** nappes 0 à 0,2 en cellules de 120 km ; stratus polaires 0,1 à 0,25 ; bancs au vent 0,3 à 0,5 ; boucliers 0,35 à 0,6 ; bras des spirales 0,45 à 0,7 ; têtes des dépressions 0,8 à 1 ; fronts 0,75 à 1 sur l'axe, 0,5 au bout, 0,35 sur les flancs ; cœurs convectifs 0,85 à 1.
- **Sa structure :** des variations gauchies de 80 et 250 km ; e tombe à 0 sur les 40 à 80 km du bord d'une masse, gauchi, pour que les bords s'effilochent.
- **Sous 0,03,** R = 0 : le ciel est vide.

**Le ciel est clair par défaut,** comme sur la photo de la Terre, bimodale : sur des blocs de 150 km, 43 % clairs, 34 % mêlés, 23 % couverts, 37 % de blanc en tout. La carte ne met de nuage que là où une forme en fait.

**Deux classes de nuages :**
- **Les masses organisées,** dessinées par la carte, opaques, aux bords nets : bras et têtes des dépressions, fronts froids, boucliers chauds, amas de la ZCIT et de la convection humide, nappes de stratocumulus, stratus polaires, bancs au vent.
  - Les couches se réalisent en surface, pas en transparence : opaque où une texture n < c, n de 500 à 800 km rendu uniforme sur l'aire par sa fonction de répartition.
- **Les champs de petits nuages,** laissés au grain d'environ 30 km du shader : une fraction partielle, 0,5 au plus, sans seuillage, dans quatre régimes seulement, chacun éteint à 0 sur ses bords. Les cellules ouvertes derrière les fronts, les bords défaits des nappes, les cumulus d'alizé en aval des nappes, les cumulus des terres humides et chaudes.

| Nuage | Où | Fraction, famille |
|---|---|---|
| La ZCIT | la ligne du maximum de pluie entre ±25°, lissée sur 2 000 km ; demi-largeur 4°, gauchie | des amas de 0,46 à 0,68, seuillés ; épais, cumulus |
| La convection humide | au-dessus de 1 500 à 2 400 mm et de 20 à 25 °C, la terre surtout | jusqu'à 0,7, seuillée ; cumulus |
| Les nappes de stratocumulus | au-dessus des remontées froides lissées sur 500 km, portées sur 1 600 km sous le vent, plus fortes sur une mer fraîche | 0,9 au cœur, seuillées en déchirures ; défaites sous le vent en champs de 0,3 à 0,5 ; nappe |
| Les cumulus d'alizé | en aval des nappes, sous les alizés, éteints sur 1 250 km | 0,1 à 0,25 ; cumulus |
| Les stratus polaires | sous −8 à −18 °C sur la mer, −6 à −18 °C sur la terre | 0,3, seuillés ; nappe |
| Les bancs au vent | où le vent monte la pente des grandes formes lissée sur 120 km, de 0,02 à 0,12 m/s | 0,82, seuillés ; mixte |
| Les cumulus des terres | au-dessus de 1 000 à 1 600 mm et de 15 à 22 °C | 0,2 à 0,3 ; cumulus |
| Les dépressions | 8 à 10 en anneau entre 45 et 62° S ; 6 à 8 entre 38 et 62° N, sur la mer, à 2 500 km au moins | voir ci-dessous ; opaques, mixtes |

**Une dépression,** à son échelle de 1 500 à 2 200 km et à son stade, d'une onde à une occlusion, en miroir au sud :
- **la spirale :** 2 ou 3 bras logarithmiques de 1 à 1,75 tour, larges de 0,2 à 0,3 fois l'échelle ; la tête pleine quand elle s'occlut ;
- **la fente sèche :** l'intervalle entre les bras, plus étroit qu'eux, dégagé ;
- **le front froid :** une polyligne sur la sphère, de 2 500 à 5 000 km, qui part au sud-est du centre, balaie vers le sud-sud-ouest puis l'ouest et atteint 25 à 31° ; large de 600 km près du centre, 220 km au bout, 30 % de plus au sud ;
- **côté froid du front,** une allée claire de 130 à 280 km ; **côté chaud,** le secteur chaud, éclairci ;
- **le bouclier chaud,** d'environ 1 350 × 1 000 km à l'est et vers le pôle, des cirrus sur son bord avant ;
- **le secteur froid,** sur la mer, des cellules ouvertes de 0,35 à 0,5 derrière le front, éteintes avant la dorsale, à mi-chemin de la dépression précédente.

- **Le ciel se dégage tout à fait,** sans plancher : sous les anticyclones, sur les dorsales entre les dépressions, dans les secteurs chauds, sur les déserts chauds, sous 250 mm et au-dessus de 5 à 10 °C, dans les fentes sèches et les allées des fronts ; sous le vent des reliefs, où l'air descend de 0,015 à 0,1 m/s.
- **Les cirrus :** les enclumes de la ZCIT, les boucliers chauds, des traînées du courant-jet vers 31°.
- **La combinaison :** un maximum lissé d'ordre 4, jamais une somme ; la famille vient de la forme la plus forte, en mélange doux.
- **Le budget,** graines 0 et 1 :
  - fraction opaque moyenne 0,37 et 0,35, pour 37 % de blanc sur la photo d'Apollo ;
  - ciel clair, opacité sous 0,05, sur 52 et 53 % de l'aire ; couvert, au-dessus de 0,9, sur 32 et 30 % ; mêlé sur 16 et 17 % ;
  - par bande, la fraction opaque de la Terre à ±0,1 : 0,4 de 0 à 10°, 0,2 à 0,25 de 10 à 30°, 0,5 à 0,65 de 40 à 70° ; sauf 30-40° S, à 0,21-0,24 pour 0,35, et 50-60° N de la graine 1, à 0,48 pour 0,6 ;
  - cirrus au-dessus de 0,03 sur 6 à 7 %.
- **Le temps :** 150 à 170 ms au titre, machine chargée par d'autres rendus.
- **La mesure :** `python tools/meteo_couverture.py <graine>` lit `meteo-<graine>.bin`, imprime ces chiffres et leurs cibles, et écrit une image de l'opacité vue d'en haut, `meteo-<graine>.png`.
- **Le moteur écrit la carte** à côté de l'exécutable, `meteo-<graine>.bin`, son mip 0 après un en-tête `EXOMETEO`, la graine, la largeur et la hauteur ; et ses dépressions, `meteo-<graine>.txt`, latitude, longitude, échelle et stade, pour les vues de test.

**La densité des nuages bas :**
- **La forme,** un bruit de Perlin-Worley de 128³ texels sur 32 km, et **l'érosion,** un bruit de Worley de 32³ sur 4 km. Tous deux sont fixés sur la planète.
- **Le profil vertical,** une table de 64² par famille et par hauteur dans la couche, donne la densité et la force de l'érosion.
- **La couverture seuille la forme,** à la façon de Frostbite : `remap(forme, 1 − R, 1) × R × profil`. L'érosion est ensuite retranchée au bord.
- **Puis la densité se divise par R :** R dit la part du ciel couverte, pas l'eau dans le nuage. La forme, le support et l'érosion ne changent pas.
- **L'eau dans le nuage suit l'épaisseur que la carte porte,** convention partagée avec le climat : `e = saturate((R − 0,28) / 0,62)`, nulle sous 0,28, et la densité multipliée par `0,25 + 0,75 e`, de 20 à 80 /km. Les cumulus épars et les nappes, environ 0,1 à 0,2 g/m³ d'eau, ont τ de 10 à 25 ; les cœurs des fronts et de la convection, 0,5 g/m³, τ de 80 et plus. Avec l'eau d'un cœur de front partout, une nappe d'1 km avait τ ≈ 60 : sa réflectance saturait, plate et sans texture vue d'orbite basse.
- **Une octave de la forme à 128 km,** le même volume relu à quatre fois son échelle, axes permutés pour que les deux pavages ne s'alignent pas, s'ajoute à la forme, centrée sur sa moyenne mesurée, 0,889 ; sa variance sous le texel s'ajoute à la loi au pixel. Sans elle, à couverture partielle, l'érosion de 4 km plaçait seule les cumulus : un semis uniforme de mêmes tailles, vu d'orbite basse. Avec elle, ils se groupent en amas et en allées, et les bords des nappes s'effilochent.

**La statistique au pixel** (`CloudLowDensity`) : un échantillon lit la forme et l'érosion au mip de l'empreinte du pixel, et leur loi sous elle, pas leur seule moyenne.
- **L'écart type de chaque bruit sous chaque texel,** de chaque mip, se calcule au chargement depuis le mip 0, dans le canal B des deux volumes (`D3DApp::UploadCloudVolume`) ; le fichier sur disque ne change pas.
- **La marge sur l'érosion,** `U = clamp(X − (1 − R), 0, R) p − D g`, X la forme, D l'érosion, p et g le profil, est prise gaussienne : moyenne et variance depuis les deux moments du seuil et l'écart type de D.
- **La part couverte** `f = Φ(mU / sU)` ; **la densité dans le nuage** `E[U⁺] / f / (1 − g μD) / R`, bornée à [0, 1] ; sous 1e-4, la part est nulle.
- **Les échelles plus fines que les texels,** que les bruits ne portent pas, ajoutent leur variance à toute distance : 0,0124 pour la forme, 0,033 pour l'érosion, la variance de l'octave la plus fine, celle des blocs du mip 1, les octaves suivantes de moitié. De près, un bord devient une frange de part couverte partielle, comme un bord turbulent vu au pixel. Contrôle : `tools/nuages_statistique.py`.
- **Les cirrus,** minces, gardent leur densité moyenne.

**La densité des cirrus :** des fibres, canal G du volume de forme, sur 64 km vers l'est et 16 km vers le nord, cisaillées. Elles sont multipliées par B, par l'enveloppe et par 0,018.
- **Leur repère est fixe :** le même est et le même nord sur toute la planète (`CLOUD_CIRRUS_*`).

**La précision :**
- **En double :** la caméra, la vue et les distances, depuis une ancre posée sur une grille de 32 km.
- **En float,** seulement le reste local : aucune coordonnée absolue n'entre dans une lecture de bruit.

**La lumière, à chaque pas dans un nuage :**
- **L'extinction :** 80 /km par unité de densité, albédo 1 ; 0,5 g/m³ d'eau à 10 µm de rayon effectif.
- **Vers le soleil :** six pas, de 125 m à 4 km, 7,875 km en tout, la couche basse entière ; Beer sur la densité traversée.
- **La phase simple :** Henyey-Greenstein, g = 0,85, celle des gouttes (Bohren et Huffman).
- **Le soleil et le ciel** viennent des tables de l'atmosphère, à l'altitude du pas : `SunTransmittance`, `MultiScattering`, `SkyIrradiance`.
- **La diffusion multiple,** isotrope : `σ W (S_soleil μ + E_ciel) / (1 + b τs) / 4π` par km, la transmission diffuse d'une couche vers le soleil, sommée le long de la vue, puis multipliée par `F = 1 − exp(−k τ / μ̄)` ; W = 3,40, b = 0,040, k = 0,061, calés sur des couches de Monte-Carlo (`tools/calage_orbite.py nuages`).
  - **μ :** une nappe reçoit le soleil comme un sol, `dot(haut, soleil)` ; un cumulus comme une boule, 0,5 sur sa face éclairée : `max(dot, 0,5 × famille, 0,05)`.
  - **τ, l'épaisseur du nuage là où il existe :** la plus grande de deux. La colonne verticale au point vu, douze tranches de 0,5 km de la couche basse ou huit des cirrus, en densité dans le nuage, sans la part couverte, lue à environ 1 km (mip ≥ 2 de la forme, ≥ 3 de l'érosion) : la diffusion multiple étale la lumière sur quelques libres parcours de transport, 1 / (σ (1 − g)) ≈ 170 m. Et l'épaisseur que la marche a traversée. Pour une couche plane, c'est son épaisseur : la grandeur du calage. Le bord d'un nuage, vu rasant ou éclairé de dos, a la colonne de tout le nuage.
- **Le détail et ses raisons :** `spec-rendu-orbite.md`.

**La marche, en colonnes :** dans le pixel, les nuages d'une couche se superposent au maximum ; la colonne nuageuse est la plus large part rencontrée, fc, et seule une part de 2 % plus large l'élargit. Quand le rayon a quitté l'empreinte du pixel, la colonne se ferme et se compose aux précédentes comme une couche : recouvrement aléatoire au-delà. La transmittance du pixel est `1 − fc (1 − Tc)`.

**La marche :**
- **Les segments** de chaque couche sont triés le long du rayon, arrêtés au terrain et au sol de la planète.
- **Le pas :** la moitié de l'empreinte du pixel, 48 m au moins, 240 m d'altitude au plus.
- **Le vide se saute :** dans une cellule de la carte vide aux mips 3 à 7, jusqu'à 80 % de la distance à ses bords sphériques, 50 km au plus.
- **Un pas éclairé ne dépasse pas une épaisseur optique de 1** tant que la colonne est transparente ; opaque, elle reprend le pas géométrique.
- **La marche s'arrête** quand la transmission du pixel tombe sous 0,003.
- **La qualité Référence,** touche C : pas de 24 m, 160 m d'altitude par pas.

**La quadrature lointaine, retirée le 2026-10-31 :** la statistique au pixel la remplace (`log/spec-nuages-historique.md`).

**L'ombre au sol :**
- **Une trace par pixel de surface éclairée,** du point vers le soleil, à travers les deux couches, sur la même densité au même temps.
- **Le pas :** 250 m au moins, 256 échantillons au plus par segment.
- **Elle n'atténue que la part solaire :** `scène − min(part solaire, scène) × (1 − T)`. Une transmission de 1 laisse l'image exacte.
- **La part solaire** est la seconde cible de la scène (`sunPart`, t17). Terrain, mer, objets et végétation y écrivent la lumière directe du soleil, avec les mêmes rejets alpha que la couleur.

## Les passes

**Une passe plein écran suit la scène,** dans l'image composite (`D3DApp::Draw`, étape 3). Elle lit l'image HDR, sa distance en alpha, et la part solaire.

**La passe temporelle, par défaut** (`CloudsTemporal.hlsli` ; `optimisation.md`, rounds 1, 7 et 8) :
- **La trace, `PSCloudTrace` :** un pixel par tuile 4 × 4 et par image, dans l'ordre de Bayer ; tout pixel a sa trace en 16 images. Elle écrit lumière, transmittance, distance, son écart type, ombre et poids lointain.
- **La demi-trace, `PSCloudTraceHalf`,** sous 14 km d'altitude seulement : un pixel par carré 2 × 2, là où l'historique d'un pixel du carré a glissé.
- **La résolution, `PSCloudResolve`,** en pleine résolution. Elle prend la trace fraîche ; à défaut, l'historique reprojeté, les nuages dans le repère de la météo, leur ombre sur le sol ; à défaut, les carrés de la demi-trace ; à défaut, elle trace le pixel. Elle compose l'air et écrit l'historique suivant.
- **Un pixel se retrace** au-delà d'1 pixel de dérive, d'1° de rotation de la direction de vue par image, ou de 20 % de changement de distance.
- **L'historique repart** à un saut de la caméra, au changement de qualité, à l'allumage des nuages, et quand le soleil tourne de plus d'1°.

**La passe unique, `PSMain`** (`AtmospherePass.hlsl`) : chaque pixel tracé, à chaque image.
- **Elle sert** avec `MYPLANETENGINE_CLOUD_FULL=1` ou `-PassePleine` du lanceur, et toujours pour les vues `weather` et `cloudshadow`.

**La composition, `CloudComposite` :**
- **L'air :** 12 pas vers une surface, 24 vers le ciel, en simple précision depuis l'altitude de la caméra.
- **Le nuage s'insère à sa distance pondérée :** il coupe en deux le seul pas où il tombe. L'air reste continu quand cette distance change.
- **Derrière :** la surface, son ombre retirée ; ou, sur le ciel, le disque solaire.

**Le temps GPU,** horodatages 18 à 19 : « nuages+air » au titre, colonne `atmosphere` de `tools/banc_perf.py`. La trace seule, horodatages 18 à 20, colonne `nuages_trace`.

## Le b1, `CloudFrame`

**304 octets, identiques en C++ (`D3DApp.h`) et en HLSL (`Clouds.hlsli`),** tenus d'accord par un `static_assert`. `D3DApp::Update` le remplit.

| Champ | Contenu |
|---|---|
| `cloudCameraKm` | la caméra dans le repère de la planète, km, double ; w : 1 avec les nuages, touche N |
| `cloudForward`, `cloudRightTan`, `cloudUpTan` | les axes de la vue, roulis du vaisseau compris ; w : les tangentes du champ |
| `cloudWind` | xy : sinus et cosinus de l'angle du vent ; z : 1 en qualité Référence |
| `cloudSun` | la direction du soleil |
| `cloudPrevQ[3]`, `cloudPrevGround[3]` | la caméra précédente, pour la reprojection, dans le repère de la météo puis du sol |
| `cloudTemporal` | xy : le pixel tracé de la tuile ; z : 1 si l'historique vaut ; w : réservé |

## Les ressources

| Registre | Ressource | Format, taille |
|---|---|---|
| b1 | `CloudFrame` | 304 octets, tampon d'envoi |
| t17 | la part solaire de la scène | RGBA16F, plein écran |
| t24 | la forme et les fibres, `shape128` ; B : l'écart type de la forme sous le texel, calculé au chargement | RGBA8, 128³, 8 mips |
| t25 | l'érosion, `detail32` ; B : son écart type sous le texel, calculé au chargement | RGBA8, 32³, 6 mips |
| t26 | les profils, `weather64` | RGBA8, 64³, 7 mips |
| t27 | la carte météo, calculée au démarrage (`Climate::Weather`) | RGBA8, 1 024 × 512, 11 mips |
| s2, s3 | les bruits, en répétition ; la carte | linéaires |
| t44, t45 | les tuiles fraîches, un texel par 4 × 4 | RGBA16F ; RGBA32F |
| t46 à t48 | l'historique lu : lumière, données, écart type et dérive | RGBA16F ; RGBA32F ; RG16F, plein écran |
| t49, t50 | la demi-trace, un texel par 2 × 2 | RGBA16F ; RGBA32F |

- **Deux historiques,** l'un lu, l'autre écrit, s'échangent à chaque image.
- **Les images temporelles ne sont pas créées** avec `MYPLANETENGINE_CLOUD_FULL=1`.

## L'air autour des nuages

**Depuis le 2026-10-30, l'air de la composition est de nouveau celui de la passe d'atmosphère d'avant les nuages** (`CloudAirPiece`, `IntegrateScattering`, `Atmosphere.hlsli`). En place, à juger en vol :
- **Les rayons de soleil :** l'ombre du relief dans l'air, par la hauteur d'ombre de chaque sommet (`recherche-rayons.md`).
- **La brume sur le sol régional,** le long de la vue : la couche limite suit le sol de la carte de la planète (`recherche-profondeur-atmospherique.md`, 3.5).
- **Le disque solaire,** derrière les nuages et l'air, quand la vue ne rencontre pas la planète. Il montre la part du pixel qu'il couvre.
- **Avant ce jour,** la composition des nuages les omettait : son air était celui d'un sol au niveau de la mer, sans relief.

**Le halo de l'objectif et le lissage temporel ne dépendent plus des nuages** (`lancement.md`) :
- **le halo** est coupé par défaut ; `MYPLANETENGINE_GLARE` l'active (`recherche-halo.md`) ;
- **le TAA** est coupé au démarrage ; la touche T le rétablit, `MYPLANETENGINE_TAA` dès le démarrage.

## La météo et la verrière

- **Une seule horloge :** la météo tourne vers l'est autour de l'axe de la planète, 12 m/s à l'équateur (`kWeatherWindSpeed`). Les formes ne se déforment pas. À l'instant 0, la carte est posée sur la géographie.
- **Elle démarre en pause, à l'instant 0.** Espace la relance en caméra libre ; V passe de ×1 à ×5.
- **La palette de tests suit le vent :** chaque test retrouve ses nuages quand la météo a tourné.
- **La verrière lit les mêmes nuages,** au même temps, à la place du vaisseau : `ShipWeather.hlsl` inclut `Clouds.hlsli`. Elle se mouille dans un nuage, prend la pluie sous sa base.
- **Sa température** vient de la carte du climat, au niveau de la mer moins 6,5 °C/km (`spec-climat.md`). Voir `spec-vaisseau.md`.

## Les vues de diagnostic

**Par `MYPLANETENGINE_VIEW`,** au lancement direct de l'exe : le lanceur efface les variables.

| Vue | Ce qu'elle montre | Passe |
|---|---|---|
| `clouds` | l'opacité des nuages, 1 − transmittance | les deux |
| `weather` | la carte météo à plat : bleu à orangé la couverture par famille, magenta les cirrus | unique |
| `cloudshadow` | la transmission vers le soleil sur toute surface tournée vers lui ; blanc, aucune ombre | unique |
| `ground` | la vue du sol, sous la silhouette des nuages ; touche B | les deux |

- **Les autres vues du terrain sont des mesures :** ni nuages ni air par-dessus.

## Les variables et les touches

| Variable | Effet |
|---|---|
| `MYPLANETENGINE_NO_CLOUDS` | sans nuages, comme N |
| `MYPLANETENGINE_CLOUD_FULL=1` | la passe unique |
| `MYPLANETENGINE_WEATHER_TIME` | l'instant de la météo, en secondes |

| Touche | Effet |
|---|---|
| N | les nuages, oui ou non |
| C | la qualité, Éco ou Référence |
| B | la vue du sol sous leur silhouette |
| Espace | la météo reprend ou s'arrête, en caméra libre |
| V | la météo ×1 ou ×5 |
| O, P | le soleil tourne |

- **Le titre** dit la qualité, l'état des nuages, l'instant et la vitesse de la météo, et le temps « nuages+air ».
- **Les bancs posent leurs variables eux-mêmes,** et ne tournent que sur demande : `tools/banc_perf.py` (`--full`, `--weather`, `--motion`) ; `tools/banc_composition_surfaces.py`, qui vérifie qu'une transmission de 1 laisse les surfaces intactes.

## Les données et leur provenance

**Trois textures figées dans `assets/clouds`,** 10,9 Mo : RGBA8 sans en-tête, mips à la suite, x le plus rapide. L'exe les trouve au-dessus de lui, comme le vaisseau ; s'il en manque une, il s'arrête avec un message. La carte météo n'est plus un asset : elle se calcule au démarrage.

| Fichier | Rôle | Fait par |
|---|---|---|
| `shape128` | R : la forme ; G : les fibres des cirrus | R : TileableVolumeNoise de Hillaire (MIT), commit `1f879a26` ; G : fibres générées |
| `detail32` | R : l'érosion | TileableVolumeNoise |
| `weather64` | RG : les profils par famille et hauteur | profils écrits à la main |

- **`manifest.json` fait foi :** empreintes SHA-256, rôle et source de chaque texture.
- **L'ancienne carte,** des champs de bruit sans lien avec la géographie, et son générateur sont retirés le 2026-10-31 : `log/spec-nuages-historique.md`.
- **Les trois volumes ne se régénèrent plus dans ce dépôt.** Leur chaîne, générateurs et sources, de `third_party/FrostbiteNoise` à `assets/frostbite-orbit`, est au tag `jalon/26-nuages-main`.
- **Les licences :** `NOTICE`, parties 1 et 2 ; `LICENSES/MIT-TileableVolumeNoise.txt` ; `third_party/WickedEngine/LICENSE.txt`.

## Les défauts connus

**La passe temporelle, en mouvement :** trois défauts vus en vol le 2026-10-28, mis de côté pour finir les rounds de performance.
- **Le round 6 les corrige au banc :** chaque trace fraîche vérifie l'historique. Mais il coûte 4 à 6 ms de plus en vol lent, en altitude et près des cumulus. Il est au tag `piste/optimisation-r6-nuages-mouvement`, à reprendre par une variante moins chère.
- **Le bruit à haute vitesse :** en altitude, en vol rapide, un grain sur les nuages. Cause supposée : trois grains mêlés, celui des pixels frais à un rayon lointain, des pixels retracés à quatre, et de l'historique adouci. La quadrature lointaine retirée le 2026-10-31 en ôte les deux premiers : à revoir en vol.
- **Le ghosting en plongée depuis l'orbite :** en approchant très vite d'une formation, des traînées de sa taille ou plus, qui s'effacent en 2 à 3 s à l'arrêt. Cause supposée : la moyenne lointaine garde ses rayons alors que l'empreinte rétrécit. La distance gardée est fausse, et la dérive, calculée depuis elle, ne le voit pas (`optimisation.md`, round 1).
- **Les traînées en approche d'un cumulus :** près du sol, en avançant vers un cumulus puis en reculant, des traînées en damier 4 × 4 autour de sa silhouette, pendant quelques images. Cause supposée : le bord avance sur le ciel sans dérive mesurable ; l'historique est gardé alors que la trace fraîche le contredit.

**Le coût :**
- **Au-delà de ×5 en orbite,** la passe coûte la passe unique, 10 à 38 ms : chaque nuage est vu sous un angle qui tourne trop vite.
- **Au-dessus de la mer,** les rayons rasants marchent la couche basse sans rien prouver de vide : 4,6 ms au round 1.

**Les limites du modèle :**
- **La carte** a un texel d'environ 39 km à l'équateur : pas de variation régionale plus fine.
- **La géographie n'est juste qu'à l'instant 0 :** l'horloge tourne la carte d'un bloc vers l'est, 43 km par heure à ×1 ; au fil des heures, les déserts et les nappes se décalent de leurs côtes.
- **Les dépressions sont des gabarits,** d'une forme commune à leur échelle et leur stade près ; elles ne naissent ni ne meurent.
- **Les cirrus** gardent un repère fixe, pas un vent local.
- **Les formes ne vivent pas :** la météo tourne d'un bloc, sans formation ni dissipation.
- **Ni cumulonimbus, ni pluie visible, ni brouillard au sol.**
- **Pas d'ombre des nuages dans l'air,** seulement au sol.

## La suite

- **Les trois défauts en mouvement,** par une vérification de l'historique moins chère que celle du round 6.
- **Les transmittances vers le soleil précalculées,** pour l'ombre et la lumière.
- **Une météo qui vit :** la ZCIT et les nappes fixées sur la planète, les dépressions qui suivent les rails ; la direction des cirrus, les cumulonimbus.

## Les références

- **[Frostbite 2016](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/s2016-pbs-frostbite-sky-clouds-new.pdf),** Hillaire, §5.3.1 : la carte météo pour la couverture et le type ; les profils de densité et d'érosion séparés des bruits 3D. §5.9 : les ombres des nuages en texture de transmittance, sur une planète plate ; ici, tracées sur le globe.
- **[Epic, Volumetric Clouds](https://dev.epicgames.com/documentation/unreal-engine/volumetric-clouds?application_version=4.27) :** des parcours secondaires pour le passage du sol à l'espace ; des cartes d'ombre plus rapides pour les surfaces.
- **[NASA, Earth's Clouds on the Move](https://science.nasa.gov/earth/earth-observatory/earths-clouds-on-the-move-154443/) :** la convergence tropicale et les systèmes des moyennes latitudes ; ici, des tendances douces, pas des anneaux.
- **Wicked Engine,** `volumetricCloudsHF.hlsli` et `volumetricCloud_renderCS.hlsl`, commit `5433f0a6` : la base du shader.
- **L'état de l'art et le plan d'origine :** `recherche-nuages.md`.
