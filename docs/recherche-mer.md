# Recherche : la mer et les lacs, de l'orbite au ras de l'eau

Statut : recherche du 2026-10-24, mise à jour le 2026-10-26. Le noyau proche est la mer FFT, en place depuis le `jalon/23-mer-fft-main` : `spec-mer-fft-spike.md`. Côte et lacs restent à faire.

## 1. Conclusion et plan

**En bref :**
- **L'état de l'art tient en trois couches,** la hiérarchie de Bruneton (2010) : les vagues plus grandes que la maille en géométrie, celles plus grandes que le pixel en normales, le reste en rugosité du reflet. Les productions sérieuses en font toutes une variante : FFT en cascades de près, statistique de loin.
- **C'est notre règle :** un pixel montre la moyenne de ce qu'il couvre. La pente des vagues que le pixel ne montre pas devient la rugosité du reflet. Les moutons qu'il ne montre pas deviennent une part du pixel.
- **Une seule grandeur pilote tout : le vent à 10 m, U.** Des lois mesurées en tirent la hauteur des vagues, leur pente moyenne (Cox-Munk), la part de moutons (Monahan), la longueur d'onde dominante. Une carte de vent sur nos bruits donne donc la mer calme, agitée ou en tempête, cohérente à toute distance.
- **Le premier pas ne demande aucune vague.** D'orbite et jusqu'à quelques kilomètres, la mer se voit par le reflet du soleil, le reflet du ciel et les moutons, tous statistiques. C'est petit, peu coûteux et mesurable contre des données satellite.
- **Les lacs demandent plus que du rendu.** Le niveau plat d'un lac dépend de tout son bassin, pas du point : il faut une passe d'hydrologie non locale, à décider à part.

**Le plan :**
1. **La mer statistique.** Carte de vent ; reflet du soleil par Cox-Munk ; Fresnel et ciel reflété ; moutons en part du pixel. **Premier noyau mesuré dans `log/recherche-mer-historique.md` ; raccord du spike à revérifier.**
   - **Mesures :** profil du reflet à 5 % de la formule Cox-Munk ; part de moutons plate en descente et égale à la loi ; banc de qualité inchangé sur terre.
2. **La couleur de l'eau.** Couleur des grands fonds par type d'eau, fond visible en eau peu profonde (Maritorena 1994), moyenne exacte sur les profondeurs du pixel. **Conservée dans le spike ; comparaison aux observations à faire.**
   - **Mesure :** couleurs d'orbite contre Blue Marble ou Sentinel-2, lagon, plateau, large.
3. **Les vagues.** Spectre JONSWAP, FFT en cascades, géométrie, normales et moments de pente communs, écume persistante déclenchée par le Jacobien. **Prototype dans `spec-mer-fft-spike.md` ; aspect à juger, couverture proche et raccord statistique à calibrer.**
   - **Mesures :** photos par force Beaufort, spectre de luminance, reflet et moutons plats en descente, coût.
4. **La côte.** Vagues amorties et réfractées par la profondeur, déferlement quand H > 0,78 d, écume de bord en part du pixel.
5. **Les lacs.** Spec à part et décision : carte de niveau d'eau par remplissage des cuvettes et bilan d'eau.

**Ce qui dépasse le rendu, signalé :**
- **Les lacs :** une passe non locale, voir section 5.
- **Le fetch,** distance sur laquelle le vent souffle : non local, approché localement en section 2.
- **La surface de l'eau déplacée :** de la géométrie, mais pas celle de complexplanet. À inscrire dans `geometrie.md` comme surface de l'eau, hors des trois familles.
- **Le fond vu à travers l'eau, de près :** la maille coupe à 0 m (`Terrain.hlsli`), le fond n'est pas dessiné. On le montre par parallaxe dans les pixels, pas par géométrie.
- **Le temps :** premier paramètre animé du moteur. Les bancs doivent pouvoir le fixer.

**Coordination :** les nuages se reflètent dans la mer et y portent leur ombre ; l'atmosphère voile déjà le reflet sans rien ajouter. À raccorder avec les travaux sur les nuages et la perspective aérienne.

## 2. La carte d'état de mer, liée à notre climat

**Le principe :** un champ de vent, vitesse et direction, sur la grille de la planète. Tout le reste en découle par des lois mesurées, sans réglage par lieu.

**Quatre couches de bruit :**
1. **La circulation générale, par la latitude :** alizés, pot au noir, calmes subtropicaux, vents d'ouest, vents d'est polaires. Des gaussiennes en latitude, comme `ClimateHumidity` en pose déjà une à 24° pour les déserts.
2. **Le temps qu'il fait :** un vecteur de ±4 m/s tiré d'un `Fbm3` de 3 000 à 300 km, nouvelle graine. Il dessine dépressions et anticyclones, fixes d'abord ; une dérive lente viendra avec le temps.
3. **Les rafales et les nappes calmes :** un facteur de ±30 % sur la vitesse, `Fbm3` de 100 à 5 km. Les images de reflet d'orbite les montrent : taches calmes et brillantes, taches ventées et sombres (NASA, mer d'Arabie).
4. **La houle, à part :** une hauteur et une direction venues des ceintures de tempête, décroissant vers l'équateur, un bruit régional dessus.
   - Période de 10 à 16 s, soit 150 à 400 m de longueur d'onde.
   - Elle domine 75 % du temps sur le globe, plus de 85 % hors des ceintures de vent (Semedo 2011). Elle naît surtout aux hautes latitudes (Young 2013) et s'accumule à l'est des bassins tropicaux (Chen 2002).
   - Elle pèse peu dans la pente, donc dans le reflet d'orbite. Elle compte de près, en longues ondulations.

**La circulation proposée,** φ en degrés, u vers l'est, en m/s. Ordres de grandeur à caler sur ERA5 ou QuikSCAT :
- `u = −7 exp(−((|φ| − 15)/9)²) + 11 exp(−((|φ| − 48)/10)²) − 4 exp(−((|φ| − 75)/8)²)`
- une composante méridienne de 2 à 3 m/s vers l'équateur dans les alizés ;
- à l'équateur et vers 30°, u tombe près de 0 : le pot au noir et les calmes. La couche 2 y laisse un vent faible et variable, de 3 à 5 m/s ;
- **un seul vent pour la planète :** les rides de sable tournent aujourd'hui selon `8.0 * regional.z`. Elles pourront suivre ce même champ.

**Les lois, toutes en U** (m/s, à 10 m) :
- **Beaufort :** B = (U / 0,836)^(2/3).
- **Hauteur significative :** 0,22 U²/g pour une mer totalement levée (Pierson-Moskowitz) ; 5,2·10⁻⁴ U √F limitée par le fetch F en m (JONSWAP). On garde la plus petite.
- **Longueur d'onde du pic :** 0,83 U² m, soit 83 m à 10 m/s et 330 m à 20 m/s.
- **Pentes, Cox-Munk :** σ²_vent = 3,16·10⁻³ U ; σ²_travers = 0,003 + 1,92·10⁻³ U. Eau couverte d'un film, lacs abrités ou nappes : 0,005 + 0,78·10⁻³ U et 0,003 + 0,84·10⁻³ U.
- **Moutons :** W = 3,84·10⁻⁶ U^3,41 (Monahan 1980), 1 % à 10 m/s.
  - Les lois publiées divergent d'un facteur 2 à 5. Stramska et Petelski (2003) ont un seuil : W = 5,0·10⁻⁵ (U − 4,47)³.
  - Vu par satellite, la part de moutons varie moins avec la latitude : Monahan la surestime aux hautes latitudes (Salisbury et al. 2013 et 2014).
  - La loi se choisit au banc, contre les photos.

**Ce que donne la carte :**

| Zone | U (m/s) | Beaufort | Hs levée | Moutons, Monahan | σ² Cox-Munk |
|---|---|---|---|---|---|
| Pot au noir, 0–5° | 3–4 | 2–3 | 0,2–0,35 m, plus la houle | 0,03 % | 0,02 |
| Calmes subtropicaux, ~30° | 5 | 3 | 0,6 m | 0,1 % | 0,03 |
| Alizés, 10–25° | 7 | 4 | 1,1 m | 0,3 % | 0,04 |
| Vents d'ouest, 40–60° | 10–13 | 5–6 | 2,2–3,8 m | 1–2,4 % | 0,05–0,07 |
| Tempête | 20–25 | 8–10 | 9–14 m | 11–22 % | 0,11–0,13 |
| Lac, fetch 5 km | 5 | 3 | 0,18 m | 0,1 % | 0,03, ou moins sous film |

- **La table Beaufort concorde :** force 4 donne 1 à 2 m, force 6 donne 3 à 4 m, force 10 donne 9 à 12,5 m.

**Le fetch, seule entrée non locale :**
- **Étape 1 :** mer totalement levée partout. L'océan ouvert est juste ; les côtes et les lacs ont des vagues trop hautes.
- **Ensuite, une approximation locale :** le champ des continents de complexplanet est lent. La distance à la côte, en remontant le vent, vaut à peu près sa valeur divisée par sa pente dans cette direction. Limite : une île plus petite que ce champ n'abrite rien.
- **Lacs :** le fetch est la taille du lac, que donne la passe d'hydrologie.

## 3. Les vagues à toutes les distances

**La hiérarchie de Bruneton (2010), chez nous :**

| Longueur d'onde | Portée par | Chez nous |
|---|---|---|
| plus de 2 mailles | la géométrie : la surface de l'eau déplacée | la face et les anneaux, déjà posés à 0 m sur la mer |
| plus de 2 pixels | les normales du pixel | comme la grille fine et `DetailSlope` |
| moins de 2 pixels | la rugosité du reflet | σ²_reflet = σ²_Cox-Munk(U) − σ²_montrée |

- **Le fondu par longueur d'onde est le nôtre :** celui de `Fbm3`, entre 2 et 4 pixels. La variance montrée se calcule comme `FbmLostShare`, octave par octave du spectre.
- **Le total reste constant à toute distance :** le reflet garde sa largeur de l'orbite au ras de l'eau. Pas de scintillement, pas de mutation.
- **La mer suit déjà « une pente par octave » :** dans la queue du spectre, chaque octave porte à peu près la même variance de pente, comme `OCTAVE_SLOPE` pour le relief.

**Le spectre :**
- **JONSWAP ou TMA, avec un étalement directionnel** (Horvath 2015), plutôt que Phillips (Tessendorf 2001). Ils prennent le vent, le fetch et la profondeur : exactement les sorties de notre carte.
- **Trois bandes, comme Unity HDRP :** la houle, la mer du vent, les rides.
- **Deux spectres superposés,** mer du vent et houle chacune avec sa direction, comme WaveWorks 2.

**FFT ou somme de Gerstner :**
- **FFT (Tessendorf) :** 65 000 vagues par tuile de 256², un coût en log N par point. Cascades de 3 ou 4 tailles non multiples contre la répétition : Atlas en a 4 (GDC 2019). Limite : une tuile, un spectre, donc un seul état de mer.
- **Somme de Gerstner** (Bruneton, Proland, Outerra, Unreal) : 30 à 100 vagues par pixel, coût en N. Leurs amplitudes se calculent au pixel depuis le vent local : l'état de mer varie naturellement. Limite : peu de vagues, répétition visible de près.
- **Recommandation :** la FFT pour le champ proche, calculée pour le vent sous la caméra. Son amplitude est mise à l'échelle et tournée vers le vent local, cellule par cellule ; la statistique prend le relais au loin.
  - **Limite connue :** un front qui traverse le champ proche change la hauteur des vagues, pas leur forme.
  - **Évolution :** deux ou trois états FFT interpolés, comme les niveaux Beaufort d'Assassin's Creed III.

**Poser les vagues sur la sphère, sur la grille de la planète :**
- **Ce qui ne marche pas :** la projection des tuiles de matériaux sur les axes de la planète (`GeneratedTexture`). Elle étire la tuile jusqu'à 1,7 fois aux coins du cube ; le spectre s'y déforme.
- **Ce qui marche :** un repère tangent par cellule de la grille de la planète, de quelques kilomètres. La tuile y est tournée vers le vent local, et les cellules voisines se mêlent.
- **Le mélange, à variance constante :** poids divisés par √Σw² (Heitz et Neyret 2018).
  - Pour une mer, c'est exact : une mer FFT est un champ gaussien.
  - Le mélange simple des tuiles actuelles perdrait de la pente et rétrécirait le reflet.
  - Rotation par cellule : le pavage hexagonal de Mikkelsen (2022).
- **La phase de chaque cellule :** calculée en double sur le CPU, jamais relative à l'ancre de 64 m.

**Le temps :**
- **Dispersion :** ω² = g k tanh(k d).
- **Un temps dans les constantes de l'image,** fixé par une variable d'environnement pour les bancs.
- **Lissage temporel :** la reprojection sur le point de la surface reste exacte ; l'éclairage qui change est borné par les voisins. À surveiller au banc de tremblement.

**La géométrie, près :**
- **Déplacement vertical et horizontal** (vagues « choppy ») pour les longueurs d'onde de plus de 2 mailles. Une maille couvre environ 13 pixels à toute hauteur : la géométrie porte ce qui dépasse 26 pixels, les normales le reste.
- **Seule la surface de l'eau bouge,** jamais le terrain de complexplanet.

**La côte :**
- **La profondeur d est connue au pixel :** l'altitude sous 0.
- **Toutes les déformations sont locales,** en d et en sa pente : les vagues raccourcissent et ralentissent (dispersion), s'amortissent (facteur TMA), tournent vers la côte (réfraction).
- **Elles déferlent quand H > 0,78 d** (critère de McCowan). La bande de déferlement a une largeur de H / (0,78 × pente) : large sur une plage plate, mince au pied d'une falaise. C'est une limite sur un champ : `SpreadStep` sur la profondeur.
- **Des vagues de bord alignées sur les isobathes,** plus tard. Outerra les place par la distance à la côte ; chez nous, la profondeur divisée par la pente lissée en tient lieu.
- **Les rouleaux qui se brisent** d'Horizon Forbidden West sont animés à la main : hors de portée.

**Ce que font les autres :**

| Qui | Vagues | Au loin | Écume | Coût publié |
|---|---|---|---|---|
| Tessendorf 2001 | FFT, spectre de Phillips, déplacement horizontal |  | Jacobien |  |
| Bruneton 2010, Proland | somme de trochoïdes | normales puis BRDF Cox-Munk, ciel filtré | Dupuy et Bruneton 2012, Jacobien préfiltré | temps réel |
| Assassin's Creed III et IV | FFT précalculées en boucle, deux jeux | maille projetée, opaque au large | clés par force Beaufort 0–12 ; écume de côte précalculée | 200 i/s eau seule |
| Sea of Thieves | FFT de Tessendorf |  | masque de crêtes tiré du déplacement |  |
| Atlas, GDC 2019 | FFT en 4 bandes, contre la répétition et le manque de détail |  |  |  |
| Unity HDRP | FFT, 3 bandes : houle, agitation, rides | maille adaptative | simulée selon le vent | 4 ms au total, PS5 et Xbox Series |
| Unreal Water | sommes de Gerstner tirées d'un spectre, par octaves |  |  | bon marché, ne dépend que du temps |
| NVIDIA WaveWorks 2 | FFT, deux JONSWAP, réglage par l'échelle Beaufort |  |  | ~1 ms sur GTX 680, non vérifié |
| Crest | cascades centrées sur la caméra, 256² | clipmaps |  |  |
| Outerra | somme de Gerstner en tuile, amplitudes pondérées par le vent ; vagues de bord par distance à la côte |  |  |  |
| Uncharted 3 et 4 | particules d'onde : vagues locales, rivières |  |  |  |

- **Star Citizen, Elite Dangerous, Flight Simulator :** aucune source technique publique trouvée sur leurs océans.

## 4. Le rendu : reflet, soleil, couleur, écume

**La somme :** L = F·L_ciel + L_soleil + (1 − F)·L_eau, l'écume remplaçant sa part W du pixel.
- **Aujourd'hui,** la mer est un sol diffus : `albedo / PI * (sunLight + skyLight)`. Ni Fresnel, ni reflet.
- **Le reflet se calcule avec la normale de l'eau :** la verticale plus les vagues, jamais celle de la côte. Il est pondéré par la part de mer du pixel, `sea`.

**Fresnel :**
- **Eau d'indice 1,333 :** F0 = 0,02.
- **Moyenné sur la distribution des pentes,** par l'ajustement de Bruneton (2010).
- **Au ras de l'eau, presque tout est reflet :** c'est ce qui manque le plus aux vues basses.

**Le reflet du soleil :**
- **Cox-Munk est une distribution de Beckmann anisotrope :** α² = 2σ², alignée sur le vent.
- **La formule :** L = E_soleil · T_soleil · F · p(pente) / (4 μ_vue μ_h⁴), avec p la gaussienne de Cox-Munk et μ_h le cosinus de la facette.
- **Masquage de Smith aux angles rasants :** sans lui, le reflet est trop fort vers l'horizon. Près de l'horizon, Cox-Munk et une vraie surface FFT diffèrent de quelques dizaines de pour cent (Mobley).
- **Ordre de grandeur :** une réflectance de 0,13 au centre du reflet, soleil au zénith et 7 m/s. Bréon et Henriot (2006) mesurent 0,2 comme valeur typique.
- **Rien à ajouter pour l'atmosphère :** le soleil passe déjà par `SunTransmittance` et rougit au couchant ; le chemin vers l'œil passe par la passe d'atmosphère.
- **L'anticrénelage vient de la variance :** montrée plus perdue, elle reste constante. Pour les normales montrées, ajouter leur variance dans le pixel (LEAN mapping ; Tokuyoshi et Kaplanyan 2019 et 2021).

**Le reflet du ciel :**
- **L'atmosphère est à symétrie sphérique :** le ciel vu du niveau de la mer ne dépend que de trois angles. Il est le même partout sur la planète.
- **Étape 1, sans rien ajouter :** `IntegrateScattering` depuis h = 0, le long de la direction réfléchie, en 6 à 8 pas, sur les seuls pixels de mer. La passe d'atmosphère en fait déjà 12 sur chaque pixel.
- **Si c'est trop cher :** une table à trois dimensions, angles de vue, du soleil et entre eux, au niveau de la mer, calculée au démarrage comme les trois tables existantes. Bruneton (2017) ajoute l'altitude en quatrième dimension, utile aux lacs de montagne.
- **Mer agitée :** le ciel est lisse ; la direction moyenne et le Fresnel moyen suffisent d'abord. Bruneton filtre une carte du ciel par l'ellipse des pentes.
- **Le relief reflété,** une montagne dans un lac calme : réflexions en espace écran, repli sur le ciel. Avec les lacs.

**La couleur sous la surface :**
- **La physique :** réflectance R∞ ≈ 0,33 b_b/a, b_b la rétrodiffusion, a l'absorption (Gordon, Morel). L'eau pure absorbe le rouge, ~0,34 m⁻¹ à 650 nm, et presque pas le bleu, ~0,009 m⁻¹ à 450 nm (Pope et Fry 1997).
- **Le bleu actuel des grands fonds est du bon ordre :** 0,033 en linéaire, contre une réflectance d'environ 0,03 en bleu pour un océan clair.
- **Le dégradé sur 3 000 m de profondeur est faux :**
  - au-delà de quelques dizaines de mètres, la couleur ne dépend plus de la profondeur ;
  - les plateaux continentaux paraissent plus verts à cause des sédiments et du plancton, pas de leur profondeur.
- **À la place, deux paramètres :** la turbidité et le plancton, par un champ de type d'eau. Plus forts près des côtes et des embouchures, sur les plateaux, et dans les eaux froides qui remontent, selon la température.
- **Le fond visible,** Maritorena, Morel et Gentili (1994) : R = R∞ + (A − R∞) e^(−2Kd), A l'albédo du fond, celui du sable de plage. C'est le turquoise des lagons.
- **La moyenne sur le pixel est exacte :** pour des profondeurs d'écart-type σ_d autour de d, la moyenne de e^(−2Kd) vaut e^(−2Kd + 2K²σ_d²). Valable de l'orbite, les bancs des Bahamas, jusqu'au bord.
- **De près :** la texture du fond vue à travers l'eau, décalée par la réfraction. Une parallaxe dans les pixels, permise par `principes.md`.

**L'écume :**
- **Les moutons de loin :** la part W(U) du pixel.
- **Les moutons de près :** là où le Jacobien du déplacement J passe sous un seuil J0 (Tessendorf). Ils persistent par accumulation et disparition lente, comme dans Atlas, HDRP et Crest.
- **Le raccord, Dupuy et Bruneton (2012) :** la part de J < J0 dans le pixel se tire de la moyenne et de la variance de J, lues dans les mips. C'est un `SpreadStep` sur J. J0 se cale pour que la part de loin égale W(U) : la même couverture à toute distance.
- **L'albédo :** 0,22 en moyenne (Koepke 1984), × (0,89 ; 1 ; 1) en rouge, vert, bleu (Frouin 1996). Diffus. L'écume fraîche est plus claire, la vieille plus terne : 0,22 est leur moyenne.
- **Dès la force 7 :** des traînées d'écume dans le sens du vent.
- **L'écume de bord :** là où H > 0,78 d, en part du pixel. Le sable mouillé, plus sombre, sur la bande que les vagues atteignent.

## 5. Les lacs

**Aujourd'hui :**
- **Aucun lac.** Tout point sous 0 est de la mer, même au cœur d'un continent.
- **Les cuvettes au-dessus de 0 restent sèches.**

**Ce que font les mondes procéduraux :**
1. **Remplir les cuvettes, puis un bilan d'eau.** Le remplissage par priorité (Priority-Flood, Barnes 2014) coûte n log n. La pluie sur le bassin, contre l'évaporation sur le lac, décide :
   - un lac plein jusqu'à son seuil ;
   - un lac fermé partiel, comme la mer Morte ;
   - une cuvette sèche, salar ou playa.
2. **Générer le relief depuis l'hydrologie** (Génevaux 2013) : le relief suit les rivières. Exclu chez nous : c'est un remplacement de complexplanet.
3. **Une nappe phréatique locale :** niveau = relief lissé moins une profondeur liée à l'humidité. Local, mais faux sur les pentes : la surface de l'eau penche avec le relief lissé.
4. **Creuser un bassin et poser une eau plate :** un remplacement de géométrie.

**Pourquoi c'est plus que du rendu :** un lac a une surface plate. Son niveau dépend du seuil le plus bas de tout son bassin, parfois à des dizaines de kilomètres. Aucun pixel ne peut le calculer seul.

**Proposition, à décider :**
- **Une carte de niveau d'eau, globale :**
  - complexplanet échantillonné sur un cube fixe de la planète, 2 048² par face, des mailles d'environ 3 km ;
  - le remplissage par priorité ;
  - le bilan d'eau tiré de notre humidité et de notre température ;
  - au démarrage ou en cache. Ordre de grandeur : 25 millions de points à ~340 évaluations, à mesurer ; le maillage en fait 220 millions par image.
- **Le rendu :** de l'eau là où l'altitude est sous le niveau de son lac, dans son bassin. Le même modèle d'eau que la mer.
- **Les lacs plus petits que la carte :** une part de lac statistique de loin, la taïga à lacs, puis un remplissage local autour de la caméra. La même règle que les moutons.
- **Les cuvettes sous 0, dans les terres :** en attendant, elles restent de l'eau au niveau 0. C'est un lac plein plausible en climat humide ; en climat aride, un fond de sel serait plus juste. Les distinguer de la mer demande de savoir si elles la touchent : la même passe.
- **Les rivières :** complexplanet creuse déjà des vallées, jusqu'à ~190 m (`RIVER_DEPTH`). Y mettre de l'eau pose la même question de niveau, à étudier avec les lacs.

**Le rendu d'un lac, avec le même modèle :**
- **Fetch court :** des vagues faibles. 5 m/s sur 5 km donnent 0,18 m.
- **Film fréquent :** les variances Cox-Munk de l'eau couverte, un reflet plus net.
- **La couleur :** sur 85 000 lacs, 31 % sont bleus et 69 % verts à bruns (Yang 2022). Les bleus sont profonds et froids ; les verts et bruns, peu profonds et chauds. Donc une couleur tirée de la profondeur et de la température, calée sur l'échelle Forel-Ule, 21 teintes.
- **Les reflets nets du relief :** réflexions en espace écran.

## 6. Les coûts

| Brique | Coût | Source |
|---|---|---|
| Mer statistique, étape 1 | moins de 0,1 à 0,3 ms en 1440p | estimation : une dizaine d'opérations et 6 à 8 pas de ciel par pixel de mer |
| Table du ciel au niveau de la mer | au démarrage, puis une lecture par pixel | comme les tables existantes |
| FFT, 3 cascades de 256², hauteurs | 0,38 ms sur RTX 2070 Super | Algis et al. 2025 |
| FFT, 3 cascades de 256, non optimisée | 1,65 ms sur RTX 4070 | 80.lv |
| WaveWorks 2 | ~1 ms sur GTX 680 | forum citant la doc, non vérifié |
| Toute l'eau HDRP, simulation et rendu | 4 ms sur PS5 et Xbox Series, 7 ms la génération d'avant | Unity |
| Normales des vagues au pixel | 0,3 à 0,6 ms en 1440p, mer plein écran | estimation : 4 cascades × 3 copies = 12 lectures |
| Réflexions en espace écran | 0,5 à 1,5 ms en 1440p | ordre de grandeur courant, à mesurer |
| Carte des lacs | une fois, quelques secondes | estimation |

- **Réaliste pour un premier pas :** l'étape 1, moins de 0,3 ms.
- **Les vagues complètes,** étape 3 : 0,5 à 1,5 ms au total, selon la part de mer à l'écran.
- **Le rendu coûte plus que la simulation :** Unity le dit pour HDRP, la passe de G-buffer domine.

## 7. Mesurer contre le réel

**1. Le banc du reflet,** devenu `tools/banc_mer.py`, mode `reflet` :
- une vue d'orbite où le soleil se reflète ;
- une vue de diagnostic `glint`, la réflectance πL/(E μ_soleil) sans atmosphère ;
- **critère :** le profil à 5 % du calcul Cox-Munk, fait en Python pour le vent du lieu ;
- l'ordre de grandeur contre POLDER (Bréon et Henriot 2006), l'allure contre les images MODIS de NASA Earth Observatory.

**2. Le banc de descente, de nouvelles vues :**
- **`foam`,** la part de moutons : une courbe plate de 1 500 km à 10 m, égale à W(U) du lieu ;
- **le reflet :** sa largeur ne change pas en descente, la variance totale est constante.

**3. Le banc visuel, des sites de mer par état :**
- un lieu calme, un modéré, une tempête, de 10 m à 10 km ;
- à côté des photos de chaque force Beaufort : le livret NOAA des observateurs de navires, domaine public ;
- **mesures :** la part de moutons seuillée sur la photo et sur le rendu ; le spectre de luminance de `realisme.py`, à la même échelle.

**4. Les couleurs d'orbite :**
- l'océan profond, un plateau, un lagon, contre Blue Marble ou Sentinel-2 : Bahamas, mer Rouge, Pacifique ouvert ;
- au même angle de soleil.

**5. Les lois, sans GPU :**
- un petit script vérifie Hs(U), W(U), σ²(U), λ_pic(U) contre la table Beaufort et les lois citées ;
- sur la tuile FFT : Hs mesurée égale à la loi, variance de pente égale à Cox-Munk.

**6. Les bancs existants :**
- **qualité :** la terre inchangée, aucun p95 dégradé de plus de 10 % ;
- **coût :** temps GPU aux hauteurs habituelles ;
- **tremblement :** le reflet ne scintille pas en vol.

## 8. État actuel : spike FFT (2026-10-26)

**Noyau proche remplacé par la mer FFT,** validée en vol au `jalon/22-mer-fft`, intégrée au `jalon/23-mer-fft-main`. Déplacements, dérivées, normales, moments et écume persistante viennent des mêmes cascades FFT.

**Spécification courante :** [spec-mer-fft-spike.md](spec-mer-fft-spike.md).

**Ancien noyau :** conservé dans [l'historique](log/recherche-mer-historique.md), et au tag `piste/mer-animee`.

## 9. Sources

**Le loin et le reflet :**
- Bruneton, Neyret, Holzschuch, *Real-time Realistic Ocean Lighting using Seamless Transitions from Geometry to BRDF*, CGF 2010 : [HAL](https://inria.hal.science/inria-00443630), [Eurographics](https://diglib.eg.org/items/fb727c69-2be2-4edd-833e-f7a9baea9b63), [présentation](https://cgg.mff.cuni.cz/~jaroslav/teaching/2012-npgr031/prezentace/Realtime%20Realistic%20Ocean%20Lighting.pdf)
- Dupuy, Bruneton, *Real-time Animation and Rendering of Ocean Whitecaps*, SIGGRAPH Asia 2012 : [PDF](https://liris.cnrs.fr/Documents/Liris-5812.pdf)
- Bruneton, *Precomputed Atmospheric Scattering: a New Implementation*, 2017 : [site](https://ebruneton.github.io/precomputed_atmospheric_scattering/)
- Hillaire, *A Scalable and Production Ready Sky and Atmosphere Rendering Technique*, EGSR 2020 : [PDF](https://sebh.github.io/publications/egsr2020.pdf)
- Olano, Baker, *LEAN Mapping*, I3D 2010 : [page](https://www.csee.umbc.edu/~olano/papers/lean/)
- Tokuyoshi, Kaplanyan, *Stable Geometric Specular Antialiasing with Projected-Space NDF Filtering*, JCGT 2021, suite de leur article d'I3D 2019 : [PDF](https://www.jcgt.org/published/0010/02/02/paper-lowres.pdf)
- Heitz, Neyret, *High-Performance By-Example Noise using a Histogram-Preserving Blending Operator*, HPG 2018 : [page](https://eheitzresearch.wordpress.com/722-2/)
- Mikkelsen, *Practical Real-Time Hex-Tiling*, JCGT 2022 : [PDF](https://jcgt.org/published/0011/03/05/paper.pdf)

**Les vagues :**
- Tessendorf, *Simulating Ocean Water*, 2001 : [PDF](https://jtessen.people.clemson.edu/reports/papers_files/simdoc.pdf)
- Horvath, *Empirical Directional Wave Spectra for Computer Graphics*, DigiPro 2015 : [DOI](https://doi.org/10.1145/2791261.2791267)
- Stewart, *Ocean-Wave Spectra* : Pierson-Moskowitz, JONSWAP et leurs lois en U et F : [LibreTexts](https://geo.libretexts.org/Bookshelves/Oceanography/Introduction_to_Physical_Oceanography_(Stewart)/16:_Ocean_Waves/16.4:_Ocean-Wave_Spectra)
- Jeschke, Wojtan, *Water Wave Packets*, SIGGRAPH 2017 : [page](https://visualcomputing.ist.ac.at/publications/2017/WWP)
- Algis et al., *Arc Blanc: a real time ocean simulation framework*, JCGT 2025 : [arXiv](https://arxiv.org/abs/2503.03326)

**Les productions :**
- Mihelich, Tcheblokov, *Wakes, Explosions and Lighting: Interactive Water Simulation in Atlas*, GDC 2019 : [PDF](https://gpuopen.com/gdc-presentations/2019/gdc-2019-agtd6-interactive-water-simulation-in-atlas.pdf)
- Ang et al., *The Technical Art of Sea of Thieves*, SIGGRAPH 2018 : [PDF](https://history.siggraph.org/wp-content/uploads/2022/09/2018-Talks-Ang_The-Technical-Art-of-Sea-of-Thieves.pdf)
- Assassin's Creed III, l'océan et l'échelle Beaufort : [fxguide](https://www.fxguide.com/?p=38193) ; Black Flag : [PlayStation Blog](https://blog.playstation.com/archive/2013/09/12/why-assassins-creed-iv-black-flag-on-ps4-is-a-truly-next-gen-experience)
- Malan, *Rendering Water in Horizon Forbidden West*, SIGGRAPH 2022 : [PDF](https://advances.realtimerendering.com/s2022/SIGGRAPH2022-Advances-Water-Malan.pdf)
- Unity HDRP Water : [blog](https://unity.com/blog/engine-platform/new-hdrp-water-system-in-2022-lts-and-2023-1)
- Unreal Water, vagues de Gerstner par spectre : [API](https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/Water/UGerstnerWaterWaveGeneratorSpect-)
- NVIDIA WaveWorks : [page](https://developer.nvidia.com/waveworks)
- Crest : [documentation](https://crest.readthedocs.io/en/stable/about/introduction.html), [SIGGRAPH Advances](https://advances.realtimerendering.com/)
- Outerra, *Ocean Rendering* : [blog](https://gamedev.net/blogs/entry/2249487-ocean-rendering)
- FFT dans Unity, 3 cascades de 256 : [80.lv](https://80.lv/articles/real-time-physically-accurate-ocean-surface-simulation-in-unity/)

**Les mesures du réel :**
- Cox, Munk, *Measurement of the Roughness of the Sea Surface from Photographs of the Sun's Glitter*, JOSA 1954 : [PDF](https://data-ww3.ifremer.fr/BIB/Cox_Munk_JOSA1954.pdf) ; résumé : [Ocean Optics Web Book](https://oceanopticsbook.info/view/surfaces/cox-munk-sea-surface-slope-statistics)
- Bréon, Henriot, *Spaceborne observations of ocean glint reflectance and modeling of wave slope distributions*, JGR 2006 : [PDF](https://data-ww3.ifremer.fr/BIB/Breon_Henriot_JGR2006.pdf)
- Monahan, O'Muircheartaigh, *Optimal power-law description of oceanic whitecap coverage dependence on wind speed*, JPO 1980 : [notice](https://researchrepository.universityofgalway.ie/entities/publication/955c2fc7-e4f6-4a44-ab15-7e7073732378)
- Salisbury, Anguelova, Brooks, *On the variability of whitecap fraction using satellite-based observations*, JGR 2013 : [notice](https://eprints.whiterose.ac.uk/77830)
- Moutons en correction atmosphérique : Stramska et Petelski 2003, Koepke 1984, Frouin 1996 : [Ocean Optics Web Book](https://oceanopticsbook.info/view/atmospheric-correction/level-2/whitecaps)
- Maritorena, Morel, Gentili, *Diffuse reflectance of oceanic shallow waters*, L&O 1994 : [HAL](https://hal-lirmm.ccsd.cnrs.fr/LOV_OMTAB/hal-03284969v1)
- Absorption de l'eau pure, Pope et Fry 1997 : [OMLC](https://omlc.org/spectra/water/abs/index.html)
- Échelle de Beaufort, vitesses et hauteurs de vagues : [Wikipédia](https://en.wikipedia.org/wiki/Beaufort_scale)
- Photos d'état de mer par force Beaufort, NOAA : [livret](https://repository.library.noaa.gov/view/noaa/56110/noaa_56110_DS1.pdf)
- Reflet du soleil vu d'orbite : [NASA, The Science of Sunglint](https://earthobservatory.nasa.gov/images/84333/the-science-of-sunglint), [mer d'Arabie](https://earthobservatory.nasa.gov/images/90132/sunglint-on-the-arabian-sea)
- Climat des vagues : Young 1999 : [PDF](https://data-ww3.ifremer.fr/BIB/Young_IJC1999.pdf) ; Chen et al. 2002, réservoirs de houle : [PDF](https://data-ww3.ifremer.fr/BIB/Chen_etal_JTECH2002.pdf) ; Semedo et al. 2011 : [PDF](https://data-ww3.ifremer.fr/BIB/Semedo_etal_JC2011.pdf)
- Vents de surface, climatologie QuikSCAT : [NOAA NCEI](https://www.ncei.noaa.gov/archive/accession/0177404)

**Les lacs :**
- Barnes, Lehman, Mulla, *Priority-Flood*, Computers & Geosciences 2014 : [arXiv](https://arxiv.org/abs/1511.04463)
- Génevaux et al., *Terrain Generation Using Procedural Models Based on Hydrology*, SIGGRAPH 2013 : [PDF](https://www.cs.purdue.edu/homes/bbenes/papers/Genevaux13ToG.pdf)
- Yang et al., *The Color of Earth's Lakes*, GRL 2022 : [notice](https://doaj.org/article/c8d49c4c3ddf4418a449a17586e25ad6)
- Wang et al., indice Forel-Ule des eaux continentales, 2000–2018 : [Scientific Data](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7835379/)
