# La planète vue d'orbite

**Le but :** que la planète vue d'orbite soutienne la comparaison avec la Terre d'Apollo 17, « Blue Marble » : un océan bleu sombre, des déserts ocre, des nuages blancs et opaques aux cœurs lisses, un limbe bleu fin. Sans rien dégrader à 10 km, à 1 km ni au sol.

**État, 2026-10-31 :** fait sur la piste `piste/orbite-rendu`, branche `claude/orbite-rendu-0e3f4e` ; à juger en vol, `tools/tests/2026-10-31-orbite-rendu.txt`.

- **Le code :** `Atmosphere.hlsli`, `AtmosphereMultiScattering.hlsl`, `Clouds.hlsli`, `CloudsTemporal.hlsli`, `ToneMap.hlsl`, `PlanetSettings.hlsli`, `D3DApp.cpp` (les écarts types des bruits au chargement), `ShipWeather.hlsl`.
- **Les références et le calage :** `tools/calage_orbite.py`, Monte-Carlo de l'air vu d'orbite et des couches nuageuses ; `tools/nuages_statistique.py`, le contrôle des lois du pixel.
- **Le détail des nuages :** `spec-nuages.md`, la lumière, la marche et la statistique au pixel.

## Le constat

**Mesuré à 10 000 km, soleil dans le dos, contre « Blue Marble »** (médianes sRGB ; océan dégagé, nuages opaques, anneau du limbe) :

| | Avant | Après | Apollo 17 |
|---|---|---|---|
| Océan | 102, 129, 177 | 56, 75, 111 | 45, 67, 100 |
| Nuages épais | 189, 186, 195 | 208, 202, 204 | 220 à 233, neutres |
| Limbe | 149, 165, 209 | 109, 123, 162 | 99, 133, 171 |

- **Trois écarts signalés :** des nuages ternes, gris rosé et translucides ; un grain sableux sur les nuages lointains ; un voile lavande sur toute la planète, le limbe bas qui rosit.

**La réflectance équivalente,** `π L / E_soleil` avant la courbe, d'orbite, en passe unique ; la médiane de l'océan dégagé et des nuages opaques, au centre du disque :

| | Océan | Nuage épais | Contraste |
|---|---|---|---|
| Avant, soleil dans le dos | 0,090 | 0,237 | 2,6 |
| Après, soleil dans le dos | 0,061 | 0,645 | 10,5 |
| Avant, soleil à 60° | 0,069 | 0,125 | 1,8 |
| Après, soleil à 60° | 0,046 | 0,302 | 6,6 |
| Terre, CERES | 0,08 à 0,1 | 0,5 à 0,8 | 6 à 8 |

- **Le nuage épais est dans la cible.**
- **L'océan est plus sombre que la moyenne de CERES :** sous un soleil presque au zénith, sans reflet, le Monte-Carlo de notre air donne le même 0,06 ; CERES moyenne tous les angles du soleil et le reflet. D'où un contraste de 10 au zénith, de 6,6 au soleil oblique.

## Les causes, établies par élimination

**Le voile lavande vient de l'air, pas des nuages.** Sans nuages, l'océan restait lavande. Variantes de la composition, au même lieu : sans air, sans aérosols, sans diffusion multiple, sans ozone, exposition à 0 IL.
- **La diffusion multiple de l'air égalait la simple :** 0,7 à 1,0 fois, contre 0,15 à 0,37 au Monte-Carlo de la même atmosphère (`calage_orbite.py air`).
- **Pour un air de Rayleigh seul, le moteur suivait le Monte-Carlo :** 0,31 contre 0,26 en bleu. L'excès venait des aérosols : la table de Hillaire 2020 suppose une phase isotrope, alors qu'ils diffusent vers l'avant, g = 0,7. Vus d'orbite, ils renvoyaient trois à cinq fois trop de lumière vers le haut.
- **Un sol gris de 0,3 sous l'air,** l'océan compris, faisait un quart de l'excès.
- **Un défaut :** dans la table, un booléen `ground` masquait le sol de la tranche ; la brume des rayons descendants était posée à 1 km.
- **L'exposition** de +1 IL, calée sur des paysages, ajoutait un IL de trop pour une photo de la Terre.

**Les nuages ternes.**
- **Leur réflectance plafonnait vers 0,25,** même infiniment épais : diffusion simple et un second ordre approché, contre 0,86 à 0,99 au Monte-Carlo.
- **Leur phase renvoyait trop vers l'arrière :** 20 % d'un lobe g = −0,5. Un nuage d'épaisseur optique 1 sortait à 0,15 au lieu de 0,02 : les nuages minces et les bords faisaient eux aussi un voile laiteux.
- **Leur eau suivait la couverture du ciel :** la densité était multipliée par la couverture, et un champ de cumulus à 10 % était dix fois plus transparent qu'un front.

**Le grain.**
- **Des pas optiquement épais :** d'orbite, des pas de 240 m dans un nuage de 24 /km, six épaisseurs optiques. La lumière d'un nuage épais variait de 0,18 à 0,64 selon l'endroit où son sommet tombait dans le pas.
- **La quadrature lointaine :** 4 à 8 rayons ponctuels, au mip 0, pour un pixel de 10 km sur des cumulus de 1 à 4 km. L'écart type valait la moyenne.

## Les corrections

### L'air

- **La similitude de van de Hulst :** la diffusion multiple d'un milieu anisotrope se traite comme isotrope avec une diffusion réduite, `σs (1 − g)`. Les aérosols y entrent pour `Mie × (1 − 0,7)`, dans la table et dans la source multiple de `IntegrateScattering`. La diffusion simple ne change pas. L'océan d'orbite rejoint le Monte-Carlo : 0,071, 0,125, 0,283 exposés, contre 0,067, 0,123, 0,279.
- **Le sol sous l'air,** dans la table seulement : `AIR_GROUND_ALBEDO` = 0,12, l'albédo moyen par ciel clair, 70 % d'océan à 0,06 et des terres vers 0,25. `GROUND_ALBEDO` garde 0,3 pour les objets et les plantes.
- **Le booléen** s'appelle `hitsGround` et ne masque plus le sol de la tranche.

### La lumière des nuages

- **La phase des gouttes :** Henyey-Greenstein, g = 0,85 (Bohren et Huffman).
- **L'eau dans le nuage ne dépend plus de la couverture :** la densité finale se divise par la couverture R. La forme, le support et l'érosion restent. R ne dit plus que la part du ciel couverte ; l'eau suit l'épaisseur de la carte, de 20 à 80 /km (plus bas, vu d'orbite basse).
- **La diffusion multiple, calée sur le Monte-Carlo :** une source isotrope par km, `σ W (S_soleil μ + E_ciel) / (1 + b τs) / 4π`, sommée le long de la vue, puis multipliée par `F = 1 − exp(−k τ / μ̄)`.
  - W = 3,40, b = 0,040, k = 0,061, ajustés sur des couches de g = 0,85, épaisseurs 2 à 100, soleil au zénith et à 60°, vues de dessus et de dessous ; erreur 0,30 en log.
  - **La décroissance vers le soleil est celle de la transmission diffuse d'une couche,** `1 / (1 + b τs)` (deux flux) : raide près d'une face éclairée, lente au fond. Une exponentielle ajustée sur les mêmes couches, 0,31 d'erreur, laissait la face à l'ombre d'une tour à 57 % de sa face éclairée, au lieu de 38 %.
  - **μ, l'incidence du soleil sur le nuage :** une nappe le reçoit comme un sol, `dot(haut, soleil)` ; un cumulus comme une boule, 0,5 en moyenne sur sa face éclairée : `max(dot, 0,5 × famille, 0,05)`.
  - **τ, l'épaisseur du nuage là où il existe :** la plus grande de deux. La colonne verticale au point vu, douze tranches de 0,5 km de la couche basse ou huit des cirrus, en densité dans le nuage, sans la part couverte, lue à environ 1 km (mip ≥ 2 de la forme, ≥ 3 de l'érosion) : la diffusion multiple étale la lumière sur quelques libres parcours de transport, 1 / (σ (1 − g)) ≈ 170 m. Et l'épaisseur que la marche a traversée. Pour une couche plane, c'est son épaisseur : la grandeur du calage. Le bord d'un nuage, vu rasant ou éclairé de dos, a la colonne de tout le nuage.
  - **Le ciel y entre avec le soleil :** un nuage diffuse tout ce qu'il reçoit. Sans lui, les nuages sortaient crème.
- **Six échantillons vers le soleil,** de 0,125 à 4 km, soit 7,875 km : toute la couche basse. Avec quatre, la base d'un nuage épais recevait la lumière d'un nuage mince.
- **Un pas éclairé ne dépasse pas une épaisseur optique de 1** tant que la colonne est transparente.

### Le pixel : la statistique au lieu des rayons fins

- **La loi jointe de la forme et de l'érosion :** X la forme, D l'érosion, sous l'empreinte du pixel, gaussiennes de moyenne lue au mip du pixel et d'écart type calculé au chargement (canal B des deux volumes). La marge `U = clamp(X − (1 − c), 0, c) p − D g` donne la part couverte `f = Φ(mU / sU)` et la densité dans le nuage `E[U⁺] / f / (1 − g μD) / c`.
  - **Mesuré sur les textures :** à c = 0,2, f = 0,724 et une densité moyenne de 0,178, pour 0,727 et 0,183 vrais.
  - **Les échelles plus fines que les texels** ajoutent leur variance à toute distance : 0,0124 pour la forme, 0,033 pour l'érosion. Un bord devient une frange partielle, comme un bord turbulent vu au pixel.
  - **Prise à sa moyenne, l'érosion effaçait tout nuage mince au loin :** d'orbite, la part de pixels partiels tombait de 16 % à 2 %.
- **Le recouvrement maximal sur une empreinte, aléatoire au-delà :** dans le pixel, les nuages d'une couche se superposent, la colonne nuageuse est la plus large rencontrée ; quand le rayon a quitté l'empreinte, une nouvelle colonne se compose à la précédente comme une couche.
- **La quadrature lointaine est retirée,** et la moyenne des rayons lointains de la passe temporelle avec elle.
- **La carte météo se lit au mip 0, 39 km, en B-spline cubique :** seuillée par une fonction raide, son interpolation bilinéaire dessinait des carrés et des losanges de 80 à 160 km ; au mip 0, la carte du climat dessine ses formes jusqu'à 80 km.

### L'exposition

- **0 IL en orbite, +1 IL au sol :** les photos de paysages sont exposées pour le sol, celles de la Terre pour ses nuages. Mesurée sur « Blue Marble », sa mer et ses nuages s'accordent aux nôtres à 0 IL.
- **Entre les deux, la part de l'air sous la caméra,** `1 − exp(−h / 8 km)` : +0,88 IL à 1 km, +0,29 à 10 km. L'exposition reste un posemètre incident, sans lecture de l'image.

## Le coût GPU

**Mesuré au même lieu, avant puis après, en 1920 × 1080, l'exe seul du lanceur** (colonnes `nuages_trace` et `atmosphere`, ms ; d'autres moteurs tournaient sur le GPU) :

| Vue | Trace avant | Trace après | Nuages et air avant | Nuages et air après |
|---|---|---|---|---|
| Orbite, soleil dans le dos | 0,92 | 1,44 | 1,58 | 2,09 |
| Orbite, terminateur | 1,34 | 1,80 | 1,98 | 2,44 |
| 10 km, cumulus sur la chaîne | 6,17 | 7,90 | 7,78 | 9,48 |
| 10 km, nappe sur la mer | 4,88 | 7,73 | 6,41 | 9,21 |
| 1 km, forêt sous les nuages | 4,55 | 5,33 | 6,02 | 6,80 |
| 1 km, sous la nappe | 1,81 | 1,83 | 3,22 | 3,24 |
| Au sol, plaine équatoriale | 1,49 | 1,14 | 2,93 | 2,58 |
| Au ras de la mer | 2,73 | 1,75 | 4,14 | 3,15 |

- **À 10 km, +1,7 à +2,8 ms :** l'image entière passe de 15,2 à 16,9 ms au-dessus des cumulus, sous les 60 images par seconde. Six échantillons vers le soleil au lieu de quatre et un pas optique de 2 au lieu de 1 n'en pèsent que 0,1 à 0,2 ms : le reste est la statistique, calculée à chaque échantillon, et des nuages plus denses, donc plus de pas éclairés.
- **D'orbite, +0,5 ms ; au sol et au ras de la mer, 0,2 à 1 ms de moins :** un seul rayon par pixel au lieu de la quadrature lointaine.

## Au-dessus et au-dessous des couches

**Le critère :** blanchir les nuages sans cramer le contraste au-dessus ni au-dessous d'une couche. Six vues, à midi et au soleil bas, à 12°, avant et après, en passe unique (planche).
- **Au-dessus, à midi :** des sommets blancs, non écrêtés, 0,96 exposé au 90e centile, 226 en sRGB ; leurs ombres internes, rapport des 10e et 90e centiles de luminance, 0,65 contre 0,76 avant : plus marquées.
- **Au-dessus, au soleil bas :** 0,68 contre 0,57 avant : moins marquées. Un cumulus y reçoit le soleil en moyenne, μ = 0,5, et non selon l'incidence de chaque face.
- **Au-dessous :** des bases plus claires qu'avant, grises au soleil bas, crème à midi.
- **Aucune exposition locale :** les réflectances justes et la courbe suffisent ; à envisager seulement si le relief manque encore au-dessus d'une couche.
- **Rien dans l'historique ne garde la trace d'un blanchiment qui ait cramé le contraste :** le journal mesure le contraste de 2,5 ; l'ancien volume avait d'abord des sommets gris, deux flux inversés (`log/recherche-nuages-historique.md`).

## Vus de près : le reflet sur les contours, corrigé le même jour

**Le défaut, en vol, après fusion dans `integration` :** de 1 à 10 km, des nuages de plastique brillant, un cerne sombre sur leurs contours et sur les plis où un lobe passe devant un autre, un liseré éclatant à contre-jour, un intérieur plat.

**Les causes, par élimination,** sur des cumulus vus de 1,5 et 3 km, soleil de face, de côté et de dos, contre les shaders d'avant la piste et la même carte :
- **F mesurait l'épaisseur le long de la vue :** sur un bord ou la silhouette d'un lobe, le rayon rasant ne traverse qu'une corde mince, F s'effondre, la diffusion multiple s'éteint : le cerne. Couper F l'efface.
- **Les bords étaient des surfaces lisses :** l'eau physique du nuage, jusqu'à 80 /km, rend la frontière opaque en 12 m, et les bruits n'ont aucun détail sous leurs texels, 250 m et 125 m : leur isosurface lisse se voyait comme du plastique. L'ancienne loi, densité × R, les adoucissait par la transparence.
- **Ni la phase ni la carte au mip 0** n'y étaient pour rien.

**Les essais écartés :** F le long du soleil, des taches grises au cœur des cumulus là où la ligne du soleil sort par la base ; le long de la normale, un aspect de métal liquide, le gradient d'un bruit fin tournant d'un pixel à l'autre ; la colonne en densité moyenne, des anneaux, puis des cumulus gris là où la part couverte mêle le ciel clair.

**La correction :** l'épaisseur de F est celle du nuage là où il existe, sa colonne lissée à l'échelle de la diffusion (plus haut, la diffusion multiple) ; et la variance des échelles non résolues élargit les bords en franges. Plus de cerne, de pli ni de plastique ; les cibles d'orbite ne bougent pas, nuage épais à 0,685 avant comme après.

**Ce qui reste :** le relief des cumulus vus de près est plus doux qu'avant la piste ; rapport des 10e et 90e centiles de luminance, de côté et de dos, 0,68 et 0,77 contre 0,46 et 0,67. Leur source multiple prend une incidence moyenne, 0,5 pour un cumulus, et non celle de chaque face. Piste : l'incidence locale, par le gradient de la densité lissée à l'échelle de la diffusion, lisse à cette échelle.

**Le coût :** +0,1 à +0,5 ms, la colonne de chaque segment.

## Vus d'orbite basse, 750 km : des nappes plates et un semis régulier, corrigés le même jour

**Le défaut, en vol :** des nappes d'un blanc uniforme, sans texture, aux bords nets ; entre elles, un semis régulier de petits cumulus de même taille, partout.

**Les causes, par élimination,** à 750 km, sur deux lieux et trois soleils :
- **Les nappes avaient l'eau d'un cœur de front,** 80 /km : τ ≈ 60 pour 1 km, où la réflectance sature. Avec un quart de cette eau, elles prennent une texture cellulaire.
- **Une octave manquait entre 10 et 150 km :** l'érosion de 4 km plaçait seule les cumulus épars. La forme relue à 128 km les groupe en amas et en allées et effiloche les bords des nappes.
- **Ni la carte au mip 0 ni la variance fine.** La même famille que le plastique vu de près : des nuages devenus physiquement denses montrent les lacunes du bruit. La couverture trop haute de la carte, elle, est reprise par la session du climat.

**Les corrections :** l'eau dans le nuage suit l'épaisseur que la carte porte, `0,25 + 0,75 e`, de 20 à 80 /km, convention partagée avec le climat ; l'octave de la forme à 128 km (`spec-nuages.md`).

**Le résultat :** des nappes texturées aux bords effilochés, des cumulus en amas et en allées, les fronts épais toujours blancs ; d'orbite, nuage épais à 0,674, contraste 8,1 au soleil oblique ; de près, des cumulus plus translucides et plus doux, plus proches d'avant la piste.

**Le coût, mesuré par paires :** +0,3 à +0,9 ms à 10 km, +0,4 à +0,5 à 1 km, +1,7 ms au sol sous la convection : des cumulus moins denses demandent plus de pas avant d'être opaques.

## Les limites

- **Une octave manque entre 32 et 160 km :** entre la tuile du bruit de forme et deux texels de la carte météo. D'orbite, les champs partiels sont justes en moyenne mais flous, en taches ; le grain d'avant donnait l'illusion d'un détail. À voir avec la carte météo (`spec-climat.md`).
- **Le dessous d'une nappe est plus clair qu'avant :** 0,45 en facteur de réflectance, ce que transmet une nappe d'épaisseur 10 à 20, contre 0,11 à 0,24. Il reste un peu chaud, R/B = 1,18 : la lumière du soleil à 2 km, sans balance des blancs.
- **Le limbe** garde une bande un peu plus rouge qu'Apollo, R/B 0,67 contre 0,58 ; une brume deux fois plus claire n'y change rien.
- **La diffusion multiple des nuages est un ajustement,** d'erreur 0,3 en log : les nuages minces au soleil bas sortent un peu trop clairs.
- **Au soleil bas, le relief d'un cumulus vu de dessus est plus doux qu'avant :** sa source multiple prend une incidence moyenne. Piste : l'incidence locale, par le gradient de la densité, pour la face éclairée et la face à l'ombre.
- **Un NaN,** sur 163 pixels de deux millions au sol en passe unique, que l'instrumentation fait disparaître : la lumière des nuages est bornée à 0 avant l'historique, qui l'étalait en blocs noirs.
- **Le recouvrement maximal** suppose des nuages droits dans l'empreinte ; un cumulus incliné par le vent est un peu trop couvrant.

## Les références

- **Hillaire 2020,** *A Scalable and Production Ready Sky and Atmosphere Rendering Technique* : la table de diffusion multiple isotrope.
- **Van de Hulst 1980,** *Multiple Light Scattering* : les relations de similitude, `σs (1 − g)`.
- **Bohren et Huffman 1983 :** la phase et l'extinction des gouttes, g ≈ 0,85.
- **Sigg et Hadwiger 2005,** GPU Gems 2, chapitre 20 : la B-spline en lectures bilinéaires.
- **Le recouvrement maximal des nuages,** des schémas de rayonnement des modèles de climat (Geleyn et Hollingsworth 1979).
- **Apollo 17, AS17-148-22727, « Blue Marble »,** NASA, 1972.
