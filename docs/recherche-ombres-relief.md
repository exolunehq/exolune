# Recherche : les ombres portées du relief

Statut : recherche et première étape faite, le 2026-10-24, piste `piste/ombres-relief`. Le soleil caché par le relief, de la vallée à la chaîne ; le ciel caché par les versants reste à faire. Depuis `piste/ombre-unique`, la même marche donne aussi la hauteur d'ombre de l'air (`recherche-rayons.md`).

## 1. Conclusion

**L'horizon du terrain vers le soleil, calculé à chaque sommet du maillage, interpolé comme un angle, filtré au pixel.**
- **Notre terrain est un champ de hauteurs,** déjà recalculé à chaque image sur la face et ses anneaux. L'horizon s'y lit sans rien dessiner une seconde fois : une marche le long du grand cercle vers le soleil, à pas croissants avec la distance.
- **Une seule règle à toute distance.** Le maillage a déjà des mailles proportionnelles à la distance : la marche hérite de sa précision, du mètre près de la caméra à des kilomètres au loin.
- **Interpolé comme un angle, pas comme une ombre.** Entre deux sommets, l'horizon varie doucement ; le bord de l'ombre tombe là où il croise le soleil, entre les sommets, aussi net que le disque solaire et le pixel le permettent.
- **Le pixel montre la moyenne de la lumière.** La part du disque solaire au-dessus de l'horizon, élargie de l'étalement de l'horizon dans le pixel : `SpreadStep`, la règle des limites entre matériaux. Au loin, les ombres deviennent des parts douces, jamais des bords crénelés.
- **Le relief plus fin que le maillage :** son ombre est une part, l'ombrage de Smith pour la dispersion des pentes que la maille cache, `SlopeSpread`. Sans réglage nouveau.

**Écartés :**
- **Les cartes d'ombre en cascade ou virtuelles :** il faudrait redessiner le maillage depuis le soleil, et un maillage qui glisse fait trembler leurs bords. Pour 300 km d'ombre au couchant, des niveaux par dizaines.
- **La marche par pixel :** quatre à cinq fois plus de points que de sommets, pour des bords que la pénombre réelle rend déjà flous à l'échelle de la maille.
- **Les cartes d'horizon précalculées :** notre terrain n'est jamais stocké ; il change avec la caméra.

## 2. Ce que nous avions

- **Le soleil filtré par l'air,** caché seulement par la sphère, au bord de son disque (`SunTransmittance`).
- **Le ciel d'un sol horizontal,** pondéré par la normale et la cavité des textures.
- **Des micro-ombres de cavité,** sous le mètre.
- **Ni ombre portée, ni ciel caché par les versants** (`recherche-profondeur-atmospherique.md`, 3.6).

## 3. L'état de l'art

### Cartes d'ombre en cascade et virtuelles

- **Le principe :** une image de profondeur vue du soleil, découpée en tranches de distance. Quatre tranches de 1 024² dans la démo de NVIDIA (Dimitrov 2007).
- **La stabilité :** chaque tranche se cale sur la grille de ses texels, à taille fixe, sinon les bords scintillent (Microsoft, d'après Engel 2006). Les tranches qui suivent la profondeur de l'image, SDSM, ne peuvent plus se caler ; leur parade : plus de résolution et un bon filtre (Lauritzen 2010).
- **Unreal Engine 5, ombres virtuelles :** 16 384² virtuels en pages de 128², des niveaux de 64 cm à environ 40 km, chacun deux fois plus large. Les pages se gardent d'une image à l'autre, mais un soleil qui bouge les invalide toutes. Pénombre par 8 rayons dans la carte, selon la taille du soleil.
- **Le lointain chez Unreal :** une cascade « lointaine » pour le seul paysage, puis des ombres par champs de distance : 2,8 ms contre 4,9 ms pour six cascades, à 1080p sur une R7870.
- **Frostbite :** rien de propre au terrain dans l'exposé d'Andersson 2007 ; des cascades stables, génériques.
- **Pour nous :** redessiner le maillage depuis le soleil, à chaque image, par tranches. Un maillage qui glisse change la forme qui projette l'ombre : les bords trembleraient malgré le calage des texels. Et un soleil couchant demande des centaines de kilomètres.

### Cartes d'horizon

- **Max 1988 :** l'horizon de chaque texel dans quelques azimuts, interpolé entre eux ; l'ombre là où le soleil passe sous l'horizon. Pour le relief des textures.
- **Sloan et Cohen 2000 :** huit directions dans deux textures, interpolées.
- **Stewart 1998 :** l'horizon de chaque point d'un modèle numérique de terrain, plus vite que les méthodes précédentes au-delà de 100 000 points.
- **Timonen et Westerholm 2010 :** l'horizon exact dans chaque azimut, en temps linéaire, par balayage ; ombres nettes et ciel entier. 23 images/s sur 1 024², 64 directions, sur une GTX 280.
- **CosmoScout VR, DLR, HPG 2025 :** horizons sur 360 azimuts, compressés en 16 coefficients de Fourier, pour des planètes. 0,1 à 0,55 ms à 1080p sur une RTX 4090. Le disque solaire pris comme une hauteur constante suffit.
- **Le ciel caché :** pour un ciel uniforme vu d'un sol horizontal, la part visible au-dessus d'un horizon d'élévation h vaut cos² h par azimut (GTAO, Jimenez 2016, éq. 17). HBAO, Bavoil 2008, prend un angle solide uniforme.
- **Pour nous :** le bon outil, à une différence près. Notre terrain n'est jamais stocké : l'horizon se recalcule à chaque image, là où on regarde.

### Marche dans le champ de hauteurs

- **Jung et al. 2020, terrain lunaire courbe :** un rayon vers le centre du soleil par pixel, accéléré par des mipmaps de maximum ; disque solaire en segment de cercle. 5,4 ms contre 18,2 ms en pas réguliers, à 1080p sur une GTX 970M. Des pas plus longs en oblique faisaient scintiller.
- **Chajdas et al. 2015 :** les ombres proches tracées dans le cache de terrain, les lointaines précalculées pour un cycle jour-nuit, 3 bits par point.
- **Red Dead Redemption 2 :** une carte d'ombre du terrain tracée dans les hauteurs, selon notre recherche précédente ; non revérifié dans les diapositives publiques.
- **Pour nous :** c'est ce que nous faisons, mais par sommet, sur le maillage, plutôt que par pixel.

### Les moteurs de planètes

- **Star Citizen :** des « cascades de hauteurs du terrain planétaire » pour des ombres douces à grande échelle, à la place des cartes d'ombre (rapport d'août 2018), puis plusieurs cascades fondues (fin 2019). L'algorithme n'est pas publié.
- **Outerra :** des cartes d'ombre en 2014, l'auto-ombrage du terrain pas encore au point ; la suite n'est pas publiée.
- **Flight Simulator, Proland, Elite Dangerous :** rien de publié trouvé sur les ombres du terrain.
- **CosmoScout VR :** les cartes d'horizon ci-dessus, la seule méthode planétaire publiée et chiffrée.

### La pénombre du disque solaire

- **Le soleil fait 0,53° :** un rayon de 0,00465 rad (NASA).
- **La part visible du disque** au-dessus d'un horizon décalé de d de son centre : 1 − A(d)/πr², A l'aire du segment de cercle. Un seuil doux de −r à +r l'approche ; CosmoScout VR trouve même une hauteur constante suffisante.
- **Sur le sol,** derrière un obstacle de hauteur H, soleil à e : une pénombre de H [cot(e − r) − cot(e + r)] ≈ 2rH / sin² e, soit 4r / sin 2e de la longueur de l'ombre. Au couchant, à 5°, 5 % de l'ombre : 1,1 km de pénombre derrière un sommet de 1 km. Livingston et Lynch 1979 mesurent ce profil sur les ombres de montagnes.

### Les coûts publiés

| Méthode | Coût | Matériel |
|---|---|---|
| Ombres virtuelles, Unreal 5 | non publié ; soleil sans cache dans Fortnite pour tenir 60 i/s | consoles |
| 6 cascades contre champs de distance, Unreal | 4,9 ms contre 2,8 ms, 1080p | R7870 |
| Marche par pixel avec mipmaps de maximum, Jung 2020 | 5,4 ms, 1080p | GTX 970M |
| Horizons de Fourier, CosmoScout VR | 0,1 à 0,55 ms, 1080p | RTX 4090 |
| Horizon par sommet, ici | voir les mesures | RTX 4070 Ti |

## 4. Ce qui est fait

**La marche, `SunHorizon` dans `Shadows.hlsli`,** dans une passe à part, `Horizon.hlsl`, juste après le calcul du terrain, dans ses sommets.
- **Pour chaque sommet visible,** du maillage tel que le terrain vient de le calculer.
- **Le long du grand cercle vers le soleil :** une droite sur le plan de la face, celle qui joint le sommet au point du soleil.
- **Des pas de 2 % de la distance parcourue,** jamais plus fins que la maille sous eux, `HORIZON_STEP`. L'horizon compte comme un angle : une hauteur manquée entre deux pas pèse sa hauteur sur sa distance. La hauteur d'ombre de l'air la compte entière : à 5 %, les ombres du sol étaient les mêmes, mais les rayons tremblaient davantage (`journal-planete.md`, 2026-10-25).
- **La hauteur entre les sommets,** bilinéaire, sur la face ou sur la carte des anneaux.
- **Les vraies positions,** courbure comprise : la sphère cache le soleil d'elle-même.
- **Elle s'arrête** quand rien au-delà, même un sommet de 10 km, ne peut dépasser l'horizon trouvé et le bas du disque solaire, ni passer au-dessus du rayon du soleil tiré de la hauteur d'ombre. Au soleil haut, quelques pas ; au couchant, des centaines de kilomètres.

**Ceux qui projettent l'ombre sont calculés, même hors de l'écran.** Le maillage ne calcule que les sommets qui peuvent être vus. Un sommet est désormais gardé aussi si son ombre peut tomber sur l'écran : sa colonne, du niveau de la mer à 10 km, balayée à l'opposé du soleil jusqu'où son ombre peut porter (`ShadowSweep`, `MaybeVisible`).

**Dans le pixel, `PixelShader.hlsl` :**
- **la part du disque au-dessus de l'horizon interpolé,** élargie de l'étalement de l'horizon dans le pixel, tiré des dérivées à l'écran (`SunAboveHorizon`) ;
- **fois la part du relief plus fin que la maille que son propre relief laisse au soleil :** l'ombrage de Smith, pour la dispersion des pentes que la maille cache (`FinerReliefLit`) ;
- **seule la lumière directe change.** Le ciel reste celui d'un sol dégagé.

**La vue de diagnostic `sun`** (`MYPLANETENGINE_VIEW`) : chaque pixel blanc avec la probabilité de la lumière directe qu'il reçoit, N.L fois la part du soleil que le relief laisse. La part de blanc en donne la moyenne.

**Pour les rayons de soleil, la même marche :** chaque point marché garde aussi sa hauteur au-dessus du rayon du soleil tiré du sommet. La plus grande donne la hauteur d'ombre de la colonne, que l'atmosphère lit entre les sommets (`recherche-rayons.md`, partie 4).

## 5. Les mesures

Le 2026-10-24, sur une RTX 4070 Ti partagée avec trois à six autres instances du moteur : les temps sont des minimums sur huit lancements alternés. Image : `images/ombres-avant-apres.jpg`.

**Le scintillement ne monte pas** (`banc_tremblement.py`, avec / sans lissage) :

| Vue | Avant | Après |
|---|---|---|
| Crête enneigée, soleil à 10° de côté | 0,08 / 0,47 | 0,08 / 0,42 |
| Massif à 8 km, soleil à 15° | 0,18 / 0,98 | 0,16 / 0,92 |
| Sommet à 600 m, soleil à 10° dans le dos | 0,11 / 0,54 | 0,10 / 0,48 |
| Fond de vallée, soleil à 10° | 0,07 / 0,42 | 0,06 / 0,36 |

- L'ombre assombrit l'image, ce qui baisse aussi les écarts absolus.
- La carte du scintillement montre le bord de l'ombre en pyramide, en trait fin : il bouge à peine quand le maillage glisse.

**Pas de saut à la descente** (`banc_ombres.py`, soleil à 10°) : la lumière directe moyenne sur le sol de la vue suivante, son écart d'une hauteur à l'autre.

| Massif, 15° S 120° E | 50 → 20 km | 20 → 8 km | 8 → 3 km | 3 → 1,2 km |
|---|---|---|---|---|
| Sans ombres, l'éclairage d'avant | +7 % | +7 % | +13 % | −10 % |
| Ombres, sans Smith | −7 % | −3 % | −8 % | non mesuré |
| Ombres avec Smith, retenu | +5 % | +4 % | +2 % | −6 % |
| Corrélation des cartes de lumière | 0,68 | 0,80 | 0,69 | 0,83 |

| Fond de vallée plat, bord d'une ombre | 8 → 3 km | 3 → 1,2 km | 1,2 km → 500 m | 500 → 200 m |
|---|---|---|---|---|
| Sans ombres | +8 % | +5 % | −2 % | +1 % |
| Ombres | +9 % | +9 % | −2 % | 0 % |
| Corrélation | 0,70 | 0,80 | 0,82 | 0,60 |

- **Les ombres ne sautent pas plus que l'éclairage d'avant,** et le bord de l'ombre reste au même endroit de 8 km à 200 m.
- **Smith retenu sur la mesure :** sans lui, le loin est 3 à 8 % trop clair ; avec lui, 2 à 5 % trop sombre. Il n'a aucun réglage.
- **La part d'ombre seule n'est pas la bonne mesure.** À vue fixe, depuis 50 km, elle passe de 42 à 61 % quand les mailles passent de 1 km à 130 m : le relief dessiné projette davantage d'ombre. La lumière moyenne, elle, se conserve, celle de la surface moyenne (Smith) : c'est elle que le banc compare.
- **Au-dessus d'un relief abrupt, sous 1 km,** la comparaison ne vaut plus : le relief est aussi haut que la caméra, et la même zone ne se retrouve pas d'une vue à l'autre.

**Le banc de qualité ne bouge pas** (`banc_qualite.py`, 10 lieux, soleil vers 50°) : toutes les mesures à 0,0 dB près, mutation comprise, sauf l'unique crop de roche à 800 m, −2,3 dB de détail fin : une ombre le traverse.

**Les réglages de la marche, mesurés :**
- **Des pas de 2 % au lieu de 5 %** donnent les mêmes parts d'ombre, à 0,1 point près, sur les six paires de la descente. Retenus le 2026-10-25, pour l'air.
- **Marcher jusqu'à 3° sous le soleil** au lieu de son bord : aucun changement.

**Le coût** (« GPU calcul » de la barre de titre ; le rendu ne change pas, au bruit de mesure près) :

| Vue | Avant | Après |
|---|---|---|
| Massif à 8 km, soleil à gauche | 1,3 ms | 1,5 ms |
| Sommet à 600 m, soleil dans le dos | 0,6 ms | 2,0 ms |
| Crête enneigée, soleil à 20° | 3,1 ms | 4,3 ms |

- **Le pire cas :** le soleil dans le dos, quand le maillage calcule le relief derrière la caméra pour son ombre.
- **Le ciel caché, essayé :** quatre marches de plus par sommet, jusqu'à 5° au-dessus de la surface, coûtent 6 ms de plus sur la crête. Pas bon marché : non retenu.

**Le réalisme :**
- **Une ombre est aussi longue que la géométrie le dit,** puisque la marche suit la vraie surface, courbure comprise : L = ΔH / tan e, plus L² / 2R. Mesuré sur 212 ombres d'une chaîne, vue d'en haut à 20 km, soleil à 10° : rapport médian 1,15 entre la hauteur perdue et L tan e. La dispersion est large, la crête qui projette étant mal repérée sur la vue d'altitude tramée.
- **Les ombres réelles :** le Teide, 3 718 m, projette plus de 40 km au couchant, soit un soleil vers 5° ; un pic central lunaire de 1,4 km, 22 km à 3,7°. La même règle ici.
- **La pénombre :** derrière un sommet de 1 km, soleil à 10°, environ 310 m. Interpolé comme un angle, l'horizon garde cette largeur tant qu'il varie doucement d'un sommet à l'autre.
- **Pas encore de comparaison à des photos :** aucune photo de montagne au soleil bas dans `images/`.

## 6. Points ouverts

- **Le ciel caché par les versants.** Il faut des marches plus courtes : borner le relief par le plus haut sommet du maillage de l'image, au lieu de 10 km ; ou un sommet sur quatre ; ou le répartir sur plusieurs images.
- **Le même plus haut sommet raccourcirait la marche du soleil et le balayage des ombres** derrière la caméra, le pire cas du coût.
- **De loin, le contour des ombres suit les triangles :** il est droit sur une maille, 13 pixels. Interpoler l'horizon en B-spline, comme les normales, l'arrondirait.
- **Le banc de descente sous 1 km** demande un fond de vallée plat.
- **Des photos de montagne au soleil bas,** à hauteur de soleil connue, pour juger la part d'ombre et la lumière des faces à l'ombre.

## Sources

**Ombres en cascade et virtuelles**
- Dimitrov 2007, *Cascaded Shadow Maps*, NVIDIA : [document](https://developer.download.nvidia.com/SDK/10/opengl/src/cascaded_shadow_maps/doc/cascaded_shadow_maps.pdf).
- Microsoft, *Common Techniques to Improve Shadow Depth Maps*, calage sur les texels, d'après Engel, ShaderX5 : [article](https://learn.microsoft.com/en-us/windows/win32/dxtecharts/common-techniques-to-improve-shadow-depth-maps).
- Lauritzen 2010, *Sample Distribution Shadow Maps* : [notes SIGGRAPH](https://www.intel.com/content/dam/develop/external/us/en/documents/sampledistributionshadowmaps-siggraph2010-notes-181237.pdf).
- Epic, *Virtual Shadow Maps* : [documentation](https://dev.epicgames.com/documentation/unreal-engine/virtual-shadow-maps-in-unreal-engine) ; Fortnite chapitre 4 : [blog](https://www.unrealengine.com/en-US/tech-blog/virtual-shadow-maps-in-fortnite-battle-royale-chapter-4) ; cascade lointaine : [API](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/FShadowCascadeSettings) ; champs de distance : [documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/distance-field-soft-shadows-in-unreal-engine).
- Andersson 2007, *Terrain Rendering in Frostbite Using Procedural Shader Splatting* : [notes](https://www.advances.realtimerendering.com/s2007/Andersson-TerrainRendering(Siggraph07)-CourseNotes.pdf).

**Horizons**
- Max 1988, *Horizon mapping: shadows for bump-mapped surfaces*, The Visual Computer 4(2) ; non lu, décrit par l'exposé de CosmoScout VR.
- Sloan et Cohen 2000, *Interactive Horizon Mapping* ; brevet lu à la place : [US7102647B2](https://patents.google.com/patent/US7102647B2/en).
- Stewart 1998, *Fast Horizon Computation at All Points of a Terrain* : [page](https://www.dgp.toronto.edu/public_user/jstewart/papers/tvcg97.html).
- Timonen et Westerholm 2010, *Scalable Height Field Self-Shadowing*, CGF 29(2) : [résumé](https://diglib.eg.org/handle/10.2312/CGF.v29i2pp723-731).
- Bavoil, Sainz et Dimitrov 2008, *Image-Space Horizon-Based Ambient Occlusion* : [article](https://www.cse.chalmers.se/edu/year/2018/course/TDA361/Advanced%20Computer%20Graphics/Image-Space%20Horizon-Based%20Ambient%20Occlusion.pdf).
- Jimenez et al. 2016, *Practical Real-Time Strategies for Accurate Indirect Occlusion* : [article](https://www.activision.com/cdn/research/Practical_Real_Time_Strategies_for_Accurate_Indirect_Occlusion_NEW%20VERSION_COLOR.pdf).
- CosmoScout VR, *Fast Planetary Shadows using Fourier-Compressed Horizon Maps*, HPG 2025 : [diapositives](https://highperformancegraphics.org/untracked/2025/presentations/Pa5_2_Fast%20Planetary%20Shadows%20using%20Fourier-Compressed%20Horizon%20Maps.pdf).

**Marche dans les hauteurs, moteurs de planètes**
- Jung et al. 2020, ombres sur un terrain lunaire courbe : [arXiv](https://arxiv.org/abs/2005.06671).
- Chajdas et al. 2015, *High-Quality Shadows for Streaming Terrain Rendering* : [page](https://www.cs.cit.tum.de/cg/research/publications/2015/high-quality-shadows-for-streaming-terrain-rendering).
- Bauer 2019, *Creating the Atmospheric World of Red Dead Redemption 2* : [cours SIGGRAPH](https://advances.realtimerendering.com/s2019/index.htm).
- Star Citizen : [rapport d'août 2018](https://robertsspaceindustries.com/en/comm-link/transmission/16743-Monthly-Studio-Report-August-2018), [rapport de fin 2019](https://robertsspaceindustries.com/en/comm-link/transmission/17416-Star-Citizen-Monthly-Report-November-December-2019).
- Outerra, février 2014 : [blog](https://outerra.blogspot.com/2014/02/).

**Le soleil, les ombres réelles**
- NASA, fiche du Soleil, diamètre apparent : [fiche](https://nssdc.gsfc.nasa.gov/planetary/factsheet/sunfact.html).
- Segment de cercle : [MathWorld](https://mathworld.wolfram.com/CircularSegment.html).
- Livingston et Lynch 1979, ombres de montagnes, longueur et pénombre : [article](https://thulescientific.com/MountainShadow_Livingston&Lynch_AO_1979.pdf).
- Cratère Théophile, hauteurs tirées des ombres : [Sky at Night](https://www.skyatnightmagazine.com/advice/skills/how-to-measure-lunar-craters-moon).
- Ombre du Teide, plus de 40 km : [snowy.es](https://snowy.es/wikimeteo/sombra-volcanica), source secondaire.
- Walter et al. 2007, *Microfacet Models for Refraction through Rough Surfaces*, l'approximation de l'ombrage de Smith pour Beckmann : [article](https://www.cs.cornell.edu/~srm/publications/EGSR07-btdf.pdf).
