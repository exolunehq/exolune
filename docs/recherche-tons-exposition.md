# Recherche : l'exposition et la courbe de tons

Statut : recherche et mise en œuvre, le 2026-10-24. Code : `ToneMap.hlsl`, réglages dans `PlanetSettings.hlsli`. Banc : `tools/banc_tons.py`. Vues en vol : `tools/tests/2026-10-24-tons.txt`. Sources en fin de fichier.

## 1. Conclusion

**Le choix le plus simple et le plus robuste : une exposition réglée sur l'éclairement, une courbe de photorécepteur sur le canal le plus fort.**

**L'exposition mesure la lumière qui tombe, pas celle de l'image.**
- Elle lit la lumière du jour sous la caméra, comme un posemètre à lumière incidente tourné vers le soleil : son faisceau à travers l'air, plus le ciel. Les tables de l'atmosphère la donnent déjà.
- Une carte grise tournée vers le soleil y montre sa réflectance, quelle que soit sa hauteur. Au soleil bas, les faces éclairées gardent leur clarté ; le sol plat et l'ombre s'assombrissent, comme sur une photo exposée pour ses hautes lumières.
- Elle ne lit jamais l'image : tourner la caméra ne la change pas. Ni pompage, ni scintillement, par construction.
- Après le coucher, elle garde la lumière du coucher : le crépuscule s'assombrit.
- **Un réglage :** la compensation, en IL, comme sur un appareil. Un IL : le sol médian de nos vues de jour vaut celui des photos ensoleillées.

**La courbe est celle des photorécepteurs : x^a / (x^a + k^a).**
- C'est la loi de Naka-Rushton. Lottes 2016 et le nouvel ACES 2 en partent.
- Elle passe par la carte grise, 0,18 vers 0,18 : l'exposition seule décide de la clarté.
- Son pied creuse les ombres, son épaule adoucit les hautes lumières vers le blanc, sans écrêter.
- Appliquée au canal le plus fort, les rapports entre canaux gardés : les teintes ne tournent pas.
- Ce qu'elle retire au canal le plus fort blanchit la couleur, comme un film surexposé : la désaturation de Khronos PBR Neutral, 0,15.
- **Un réglage :** le contraste a = 1,5 : une pente de 1,23 au gris, celle qu'il faut à un écran dans une pièce tamisée, 1,2 à 1,25.

**Écartés :**
- **l'histogramme :** sa mesure dépend du cadre ; même lissée, elle suit le cadre, plus lentement ; la neige y devient grise ;
- **ACES 1, Hable :** courbes par canal, les couleurs saturées virent en hautes lumières ;
- **AgX :** bon, mais par canal derrière deux matrices, plus de code, pour un gain que la courbe sur le canal fort donne déjà ;
- **Khronos PBR Neutral, notre courbe d'avant :** sans pied, par conception ; elle n'ajoute aucun contraste ;
- **un étalonnage sur l'écran, une table de couleurs 3D :** rien à étalonner tant que la physique et la courbe suffisent ; il masquerait les erreurs de règles.

**Depuis le 2026-10-31, la compensation suit l'altitude** (`spec-rendu-orbite.md`) : +1 IL au sol, celle des paysages ; 0 IL en orbite, celle des photos de la Terre, mesurée sur « Blue Marble » d'Apollo 17 ; entre les deux, la part de l'air sous la caméra, `1 − exp(−h / 8 km)`.

## 2. Ce que nous avions

**Aucune exposition :** une radiance de 1 donne le blanc.
- Le soleil vaut π au sommet de l'atmosphère : une surface blanche face à lui, hors de l'air, a une radiance de 1.
- C'est l'exposition d'un appareil en plein soleil, la règle du f/16, à peu près. Mais elle ne bouge pas quand le soleil baisse : l'image s'éteint.

**La courbe de Khronos PBR Neutral, sans son décalage du noir :** identité sous 0,76, puis fondu vers le blanc.

**Mesuré sur nos vues de jour, contre les photos ensoleillées** (section 8) :
- **le sol, deux fois et demie trop sombre :** médiane 0,096 en luminance linéaire, contre 0,266 ;
- **des ombres et une étendue courtes :** 1,1 IL de la médiane au 5e centile, contre 4,6 ; 2,7 IL du 5e au 95e, contre 5,8 ;
- **au soleil bas, l'image s'éteint :** sol médian 0,023 à 6 et 8° ; 0,002 au coucher.

## 3. L'exposition physique

**L'indice de lumination, EV100.**
- EV100 = log2(N²/t) − log2(S/100), avec N l'ouverture, t le temps de pose, S la sensibilité ISO.
- **La règle du f/16 :** en plein soleil, f/16 et 1/S s. Soit EV100 ≈ 15.

**Lagarde et de Rousiers 2014, Frostbite, repris par Filament :**
- **Saturation du capteur :** Lmax = 78 / (q S) × N²/t, avec q = 0,65. Soit Lmax = 1,2 × 2^EV100 à ISO 100.
- **L'exposition :** la luminance divisée par Lmax ; 1 est le blanc du capteur.
- **Posemètre réfléchi :** EV100 = log2(L S / K), K = 12,5, celui de Canon, Nikon et Sekonic.
- **Posemètre incident :** E = 2,5 × 2^EV100 en lux, capteur plan, C = 250 ; 3,4 × 2^EV100 avec une demi-sphère, C = 340.

**La norme des appareils, ISO 12232 :**
- **Sensibilité de sortie standard :** l'exposition qui donne 118 sur 255 en sRGB, soit 0,18 linéaire, à une carte grise.
- **Sensibilité de saturation :** 78 / H contre 10 / H. Le blanc du capteur est 7,8 fois, 3 IL, au-dessus de la carte grise.
- Une carte blanche, 5,5 fois la grise, garde un demi-IL de marge.

**Chez nous.**
- Le soleil au sommet de l'atmosphère, π, vaut 128 000 à 134 000 lx selon les sources : une unité vaut environ 42 000 lx.
- La carte grise vaut 0,18 × E / π, avec E la lumière qu'elle reçoit. L'exposition π / E la montre à 0,18 : la convention de la norme. Notre E est celle d'une carte tournée vers le soleil (section 4).
- À midi, E vaut environ π, et π / E environ 1 : notre absence d'exposition était celle-là, pour un soleil au zénith.

**Le contraste entre soleil et ombre** (mesures de Filament, Californie, mars, posemètre incident) :
- à 10 h, soleil et ciel 120 000 lx, ciel seul 20 000 lx : 6 pour 1, 2,6 IL ;
- à 17 h 30, 90 000 contre 9 000 lx : 10 pour 1, 3,3 IL.
- Une ombre portée est donc 2,5 à 3,5 IL sous le sol ensoleillé, avant la courbe. Nos rendus n'ont pas encore d'ombres portées.

## 4. L'exposition automatique, l'adaptation de l'œil

**Par histogramme : Unreal.**
- Un histogramme de 64 classes du logarithme de la luminance de l'image ; la moyenne entre deux centiles, 70 à 80 % et 80 à 95 % conseillés.
- Une vitesse de montée et de descente, en IL par seconde ; des bornes en EV100.
- Une compensation, et une courbe de compensation selon l'EV de la scène : les scènes sombres restent plus sombres.

**Son défaut, de nature : la mesure dépend du cadre.**
- Tourner la caméra du ciel vers le sol change la moyenne : l'exposition suit. Lissée, elle suit plus lentement ; elle suit quand même. C'est le pompage.
- La neige devient grise, une forêt sombre devient grise : le posemètre réfléchi ramène tout au gris moyen.
- D'orbite, la moitié du cadre est l'espace noir : il faut l'exclure par les centiles.

**Par l'éclairement : Ghost of Tsushima.**
- Patry 2021 : une exposition « principalement fondée sur l'éclairement » ; la luminance seulement quand des hautes lumières dépassent un seuil, feu ou reflets.
- Pourquoi : sur inFamous, la boucle entre l'exposition et les albédos avait poussé les artistes vers des albédos trop sombres.

**L'œil.**
- Les cônes répondent en I^n / (I^n + σ^n), Naka et Rushton 1966 ; σ suit l'adaptation. Reinhard et Devlin 2005 en tirent un opérateur de tons.
- L'adaptation à la lumière prend quelques secondes, à l'obscurité des minutes. Elle n'a de sens à modéliser que si l'exposition lit l'image.

**De l'orbite au sol.**
- Les simulateurs de vol publient peu sur leur exposition.
- Ce que le problème impose : d'orbite, le cadre est à moitié noir, et la planète couvre de grandes différences d'éclairement. Une mesure sur l'image surexpose la planète, sauf à exclure le noir.
- Une mesure sur l'éclairement au nadir n'a pas ce problème. En descente verticale, le point mesuré ne bouge pas : l'exposition non plus.
- **Sa limite :** d'orbite, au-dessus de la nuit, le jour vu au loin est surexposé. C'est le cas réel d'un photographe dans la nuit qui vise le jour.

**Le posemètre tourné vers le soleil, pas posé à plat.**
- **Essayé d'abord à plat,** l'éclairement d'un sol horizontal : à midi, les deux se valent ; au soleil bas, le sol plat ne reçoit presque que le ciel, et l'exposition montait de 3 à 4 IL.
- **Mesuré :** les soleils bas sortaient plus clairs que midi, sol médian 0,35 contre 0,27, ciel vers le soleil écrêté sur 11 à 15 % ; en vol, une brume laiteuse, plus rien du soir.
- **Tourné vers le soleil,** la carte reçoit le faisceau entier : les faces éclairées gardent leur clarté, le reste s'assombrit avec le soleil. C'est l'exposition d'un photographe qui protège ses hautes lumières au soleil couchant.
- **Le ciel est compté comme sur un sol plat :** une approximation ; il pèse peu face au faisceau, sauf au coucher, où il reste seul.
- **Essayé, pas gardé :** le ciel propre de la carte, l'auréole et le ciel bas devant elle, dans la table du ciel. 0,1 IL de moins de jour, 0,3 à 0,5 au soleil bas ; le coucher reste clair. Un gain faible pour une table de plus.

## 5. Les courbes filmiques

**Pourquoi un pied : l'image n'est pas vue comme la scène.**
- Un écran sRGB fait 80 cd/m², dans une pièce peu éclairée. L'image doit porter plus de contraste que la scène.
- Hunt : un gamma de rendu d'environ 1,0 en ambiance claire, 1,25 tamisée, 1,5 dans le noir.
- BT.2100 : la télévision HLG ajoute un gamma système de 1,2 à 1 000 cd/m².

**ACES 1 :**
- courbe par canal dans les primaires AP1 ; pente log-log au gris d'environ 1,55 ;
- par canal, les couleurs saturées virent en montant : bleus vers le violet, rouges vers l'orangé ; ACES y ajoute des corrections ad hoc.

**ACES 2, 2024 :**
- la courbe, une Michaelis-Menten, ne touche que la clarté J d'un modèle d'apparence, Hellwig 2022 : la teinte est gardée ;
- 0,18 donne 10 cd/m² sur un écran de 100, 1,0 donne 45,8 et 2,0 donne 64 ;
- pente au gris imposée sous 1,55.

**AgX, Sobotka ; défaut de Blender 4.0, à la place de Filmic :**
- un encodage logarithmique autour du gris 0,18, puis une sigmoïde par canal ;
- avant elle, une matrice rapproche les primaires du gris : les couleurs vives vont vers le blanc sans s'écraser sur six teintes, le défaut de Filmic ;
- les teintes bougent un peu, par cette matrice ; une matrice inverse, un polynôme : plus de code.

**Hable 2010, Uncharted 2 :**
- une fraction rationnelle par canal, six constantes et un blanc à 11,2 : pied et épaule ;
- par canal, les couleurs saturées virent ; Hable 2017 la remplace par des puissances par morceaux, aux réglages directs.

**Khronos PBR Neutral, 2024 :**
- identité sous 0,76, moins un décalage du noir de 0,04 ; au-dessus, fondu vers le blanc et désaturation de 0,15 ;
- teinte gardée : tout reste dans le plan de la couleur et du blanc ;
- fait pour garder les couleurs de base reconnaissables : pas de pied, pas de contraste.

**Lottes 2016, AMD :**
- z = x^a, puis y = z / (z^d b + c), b et c choisis pour passer par (gris, gris) et atteindre 1 au blanc ;
- son exemple : gris 0,18 vers 0,18, blanc 64, contraste a = 1,3, épaule d = 0,995 ;
- appliquée au maximum de r, g, b, les rapports gardés ; un chemin vers le blanc par diaphonie ;
- la clarté se règle avant la courbe, par le gris : un gamma après elle change contraste et saturation.

**Notre courbe : celle de Lottes, épaule d = 1, sans point blanc.**
- Avec d = 1, c'est la loi de Naka-Rushton, asymptote 1 : un seul réglage, a.
- Le point blanc et d ne changent presque rien : de 8 à 64, moins de 0,02 sur l'écran sRGB, sauf tout en haut.
- Pente log-log : a dans les ombres, 0,82 a au gris, puis décroissante.

## 6. L'étalonnage référé à l'affichage

- **Ce que c'est :** corriger les couleurs après la courbe, sur les valeurs de l'écran, par courbes ou table 3D, comme un photographe sur son JPEG. L'inverse de l'étalonnage référé à la scène, avant la courbe, en lumière linéaire.
- **Pour :** on règle ce qu'on voit.
- **Contre :** sans sens physique ; propre à un écran ; une table de 32³ perd 2 à 3 bits, selon Lottes.
- **Pour nous, rien maintenant.** La couleur vient des règles : air, albédos, lumière. Une table masquerait leurs erreurs (`principes.md`).

## 7. Calibrer sur des photos

**Ce qu'on compare :** la luminance linéaire du sol, ses centiles, sur les photos `docs/images/cible-*.jpg` et sur nos vues.
- **Les photos :** le sol sous une ligne posée à la main par photo ; trois couvertes, montrées mais hors de la médiane.
- **Nos vues :** le sol et la mer exactement, par la vue de diagnostic de la mer.
- **Les mesures :** la médiane ; les ombres, de la médiane au 5e centile, en IL ; l'étendue, du 5e au 95e ; le ciel ; la part écrêtée.

**Les limites.**
- L'exposition des photos est inconnue ; chaque appareil a sa courbe et son contraste local.
- Nos rendus n'ont pas d'ombres portées : leurs ombres restent plus claires que celles des photos, quelle que soit la courbe. On ne règle pas la courbe pour les compenser.
- La médiane du sol dépend des albédos : la compensation règle l'ensemble, pas un matériau.

## 8. Mesures

**Les vues :** `tools/tests/2026-10-24-tons.txt`, celles de la profondeur atmosphérique, plus des soleils bas, un crépuscule et le terminateur vu d'orbite. Luminance linéaire du sol, médiane des vues.

![Avant, après, sur sept vues](images/tons-avant-apres.jpg)

| | p5 | p25 | p50 | p75 | p95 | ombres | étendue | ciel |
|---|---|---|---|---|---|---|---|---|
| Photos ensoleillées, 6 | 0,011 | 0,105 | 0,266 | 0,391 | 0,571 | 4,6 IL | 5,8 IL | |
| Avant, jour, 7 vues sous 20 km | 0,036 | 0,059 | 0,096 | 0,175 | 0,262 | 1,1 IL | 2,7 IL | 0,113 |
| Après, jour | 0,095 | 0,167 | 0,254 | 0,451 | 0,520 | 1,3 IL | 2,9 IL | 0,296 |
| Avant, soleil de 2 à 8°, 4 vues | 0,009 | 0,012 | 0,023 | 0,058 | 0,088 | 1,4 IL | 3,6 IL | 0,047 |
| Après, soleil bas | 0,118 | 0,140 | 0,224 | 0,412 | 0,638 | 1,1 IL | 2,5 IL | 0,676 |

- **Le jour :** la médiane rejoint celle des photos ; le 75e et le 95e centile, à 0,06 près.
- **Les ombres restent courtes :** 1,3 IL contre 4,6. Ce sont les ombres portées qui manquent, pas la courbe : à 1,8 de contraste, la meilleure adéquation, le 5e centile ne descendrait encore qu'à 0,07.
- **Le soleil bas** n'est plus éteint, et reste un peu plus sombre que le jour. Vers le soleil, le ciel s'écrête : 9 % de l'image à 6°, 16 % au coucher.
- **Le crépuscule à −3° :** sol 0,050, cinq fois plus sombre que le jour ; le ciel garde ses couleurs.
- **D'orbite :** sol 0,27 à 160 km, 0,33 à 1 200 km ; l'espace reste noir.

**Le choix des deux réglages, sur ces mesures.**
- **La compensation :** nos images inversées par la courbe puis réexposées donnent un sol médian de jour de 0,15 à 1/3 d'IL, 0,25 à 1 IL, 0,32 à 4/3 d'IL ; les photos, 0,27 : 1 IL, un cran d'appareil.
- **Le contraste :** à médiane égale, l'écart du 25e au 75e centile vaut 1,2 IL à 1,3 de contraste, 1,4 IL à 1,5 ; les photos, 1,9. Au-delà de 1,5, on compenserait les ombres absentes : à reprendre avec elles.

**La stabilité.**
- **Tourner la caméra, `banc_tons.py tour` :** de −20° à 70° d'inclinaison, à 800 m, le ciel à 10° au-dessus de l'horizon ne bouge pas, 0,00 IL ; le sol à 25° dessous, 0,02 IL. L'image entière varie de 1,36 IL : ce qu'une exposition mesurée sur l'image aurait suivi. Au soleil bas, 2,10 IL, et toujours 0,00 et 0,01.
- **Descendre, `banc_tons.py descente` :** de 1 500 km à 30 m, à la verticale d'une montagne. L'exposition ne dépend que du soleil au nadir : elle ne bouge pas. Contre l'avant, le centre de l'image gagne de 1,37 IL en orbite à 1,08 IL au sol, sans saut : 0,07 IL au plus d'une hauteur à la suivante, la forme de la courbe.
- **Le scintillement, `banc_tremblement.py` :** avec lissage, 0,16 → 0,18 et 0,09 → 0,12 niveaux sur deux vues ; l'image y est 1,5 à 1,6 fois plus claire en niveaux sRGB. Le même tremblement, montré plus clair ; rien de nouveau ne scintille.

**Le banc de qualité,** 12 lieux, avant puis après, les mêmes lieux et les mêmes soleils :
- **la neige gagne son détail :** fin détail médian +3 à +6 dB, vers celui des photos ; la courbe d'avant l'écrasait au-dessus de 0,76 ;
- **le reste ne bouge presque pas :** trou d'échelle p95 à 0,2 dB près, répétition p95 à 0,02 près ; fin détail de l'herbe −0,6 à −1,6 dB ;
- **au-delà de la règle des 10 % :**
  - le trou d'échelle p95 de la neige à 800 et 3 000 m, +0,6 et +0,5 dB : son détail, désormais visible, montre ses trous ; les photos en ont 3,5 dB ;
  - la répétition p95 du sable à 50 m, 0,12 → 0,28 : le pire crop vaut 0,31 avant comme après ; sur 60 crops, le p95 bascule d'un crop à l'autre ;
  - la mutation p95 à 12 et 200 m, 0,016 → 0,019 et 0,130 → 0,144 : le pied amplifie les écarts relatifs dans les sombres ; elle baisse à 800 et 3 000 m.
- **Les vues de diagnostic** passaient par la courbe d'avant, leur blanc à 0,88 ; avec l'exposition, il aurait varié avec le soleil, et le banc choisissait d'autres crops. Elles ne passent plus par l'exposition ni par la courbe : blanc à 1, quel que soit le soleil.

## Sources

- Lagarde S., de Rousiers C., « Moving Frostbite to Physically Based Rendering 3.0 », SIGGRAPH 2014, notes de cours, la caméra physique.
- Google, « Physically Based Rendering in Filament », la caméra physique et les mesures de soleil et de ciel.
- ISO 12232:2019, sensibilité des appareils numériques, SOS et saturation ; ISO 2720, étalonnage des posemètres, K et C.
- Epic Games, « Auto Exposure in Unreal Engine », documentation.
- Patry J., « Real-Time Samurai Cinema: Lighting, Atmosphere, and Tonemapping in Ghost of Tsushima », SIGGRAPH 2021, Advances in Real-Time Rendering.
- Naka K. I., Rushton W. A. H., « S-potentials from colour units in the retina of fish », J. Physiol. 185, 1966.
- Reinhard E., Devlin K., « Dynamic Range Reduction Inspired by Photoreceptor Physiology », IEEE TVCG 11(1), 2005.
- Lottes T., « Advanced Techniques and Optimization of HDR VDR Color Pipelines », GDC 2016.
- Hable J., « Uncharted 2: HDR Lighting », GDC 2010 ; « Filmic Tonemapping with Piecewise Power Curves », 2017.
- Academy, ACES 2.0 Output Transforms, documentation technique, la courbe de tons.
- Khronos Group, « PBR Neutral Tone Mapping », 2024.
- Sobotka T., AgX ; Blender 4.0, notes de version, gestion des couleurs.
- Hunt R. W. G., « The Reproduction of Colour », gamma de rendu selon l'ambiance.
- ITU-R BT.2100, le gamma système de HLG.
