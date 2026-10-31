# Spécification : des photos réelles, recomposées par nos bruits, à toutes les échelles

Statut : étapes 1 et 2 faites ; l'étape 3, les motifs vus d'avion, devient une source des bandes de 10 m à 1 km de `spec-texturage-universel.md`. Complète `log/etat-de-l-art-details.md` (voie C) et `log/spec-hybride-scans.md` : l'essai des scans, puis le sable photo.

## L'idée

**Garder le procédural pour le « quoi et où », prendre au réel le « à quoi ça ressemble ».** Nos bruits de climat, de géologie et de relief décident de ce qu'il y a à chaque endroit ; des photos réelles donnent l'apparence de chaque chose, recomposée à la volée par ces mêmes bruits.

- **On ne recopie jamais une photo telle quelle à grande échelle :** elle recopierait la Terre, avec des côtes et des reliefs qui ne coïncident pas avec notre terrain.
- **On en tire ce qui se transpose :** des statistiques, couleur moyenne et variance, ou des textures sans position, qui se pavent et se recolorent.
- **La règle universelle s'applique** (`principes.md`) : une apparence tirée d'une photo est une moyenne par endroit, et un pixel montre la moyenne de ce qu'il couvre.

## Ce que dit l'état de l'art

- **Mêler des copies d'une photo sans perdre son contraste :** pavage aléatoire avec mélange qui préserve l'histogramme. [Heitz et Neyret 2018](https://eheitzresearch.wordpress.com/722-2/), [Burley 2019](https://jcgt.org/published/0008/04/02/), [hex-tiling 2022](https://jcgt.org/published/0011/03/05/). Nous avons déjà un pavage proche, en triangles.
- **Recolorer une photo à la volée selon des statistiques cibles,** le cœur de l'idée : [Lutz et Gilet 2026](https://www.lirmm.fr/nicolas-lutz/publications/lg26/preprint.pdf), environ 1 ms. Chez nous, les cibles viennent du climat et de la géologie.
- **Mêler plusieurs photos selon un bruit :** [Laplacian blending, Wronski 2025](https://arxiv.org/abs/2502.13945), environ 0,1 ms.
- **Semer des éléments découpés dans les photos,** rochers ou fissures : [texture bombing](https://developer.nvidia.com/gpugems/gpugems/part-iii-materials/chapter-20-texture-bombing).
- **Synthétiser du relief à partir de vrais modèles d'élévation :** [Zhou et al. 2007](https://faculty.cc.gatech.edu/~turk/my_papers/terrain_synth_tvcg.pdf). Demande un précalcul et une mémoire du terrain.
- **À écarter pour nous :** la synthèse de texture complète et le neuronal, trop lents ou à état, alors que tout est recalculé à chaque image.
- **Ce que font les autres :** [Star Citizen](https://starcitizen.tools/Planet_Tech_v5) répartit ses matériaux par température, humidité et géologie, comme nous, sans publier sa méthode.

## Les pistes, par échelle

| Échelle | Ce qu'on prend aux photos | Source | Faisabilité |
|---|---|---|---|
| Orbite à 10 km | palette de couleurs et variance par biome | mosaïque satellite, [Blue Marble de la NASA](https://visibleearth.nasa.gov/collection/1484/blue-marble), domaine public | facile : un petit tableau, pas d'image dans le moteur |
| 10 km à 100 m | motifs vus d'avion : champs, forêts, dunes, éboulis, lits asséchés | photos aériennes libres de droits, rares | moyenne : mêmes outils que de près, mais il faut les photos |
| 100 m au sol | la matière de près : roche, sable, sol | scans CC0, Poly Haven et ambientCG | sable photo fait ; la roche reste procédurale, `log/spec-hybride-scans.md` |
| Relief | morceaux de vrais reliefs | modèles d'élévation | possible, mais contre le concept « recalculé à chaque image » ; piste lointaine |

## Étape 1 : la palette par biome tirée de Blue Marble

**Le principe.** Aujourd'hui, la couleur du sol vient de quelques teintes choisies à la main : désert, steppe, prairie, forêt, toundra. Elles deviennent les vraies couleurs de la Terre, rangées par climat.

1. **Hors du moteur, une fois :** `tools/palette_biomes.py` lit la mosaïque Blue Marble et deux cartes climatiques de la Terre, température moyenne et précipitations annuelles. Les données restent hors du dépôt, dans `../donnees-terre/`, avec leurs licences.
2. **Il range chaque pixel de terre** dans une case température × humidité, et mesure la couleur moyenne et sa dispersion de chaque case, en lumière linéaire. Les glaces permanentes sont exclues, la neige a son propre traitement.
3. **L'humidité de nos bruits** se relie aux précipitations par une échelle logarithmique : 100 mm par an pour 0, 3 000 mm pour 1. À calibrer pour que nos seuils de désert, de steppe et de forêt tombent sur les mêmes précipitations que sur Terre.
4. **Le tableau entre dans le moteur comme un fichier de code généré,** `BiomePalette.hlsli`, quelques Ko. Aucune image n'est chargée.
5. **Le pixel lit sa couleur** dans le tableau, par interpolation, à sa température et à son humidité. La dispersion de la case règle l'amplitude de la variation de clarté locale.

**La mesure :** le banc d'orbite et des vues à 5, 56 et 300 km, à côté de vues de la Terre aux mêmes latitudes ; le banc de descente, pour vérifier que la couleur ne mute pas.

**Critère :** des couleurs vues d'orbite reconnaissables comme terrestres, sans changer la répartition des matériaux.

### Résultats de l'étape 1

- **Les données :**
  - Blue Marble de janvier et de juillet 2004, NASA, domaine public ; chaque hémisphère est pris dans son été, son mois le moins enneigé, puisque la neige est dessinée à part ;
  - normales TerraClimate 1991-2020 à 1°, CC0. Le service NASA NEO, prévu d'abord, a fermé en septembre 2026.
- **Blue Marble n'est pas une mesure de réflectance :** ses couleurs sont rehaussées. Elles sont ramenées à l'albédo par canal, `albédo = a · valeur^g`, calé sur deux repères mesurés par satellite : le Sahara libyen, (0,45 ; 0,35 ; 0,22), et l'Amazonie, (0,03 ; 0,06 ; 0,025).
- **Le tableau :** 23 températures de −20 à 35 °C et 11 humidités. 202 cases sur 253 sont remplies par la Terre ; les autres, des climats que la Terre n'a pas, prennent la moyenne de leurs voisines.
- **Repères, albédo rouge, vert, bleu :**
  - Sahara 0,42 ; 0,34 ; 0,22 ;
  - steppe 0,20 ; 0,18 ; 0,12 ;
  - Europe 0,08 ; 0,10 ; 0,06 ;
  - Amazonie 0,04 ; 0,07 ; 0,03.
- **Dans le moteur :** `BiomeColor`, trois lectures sur l'étalement de la température dans le pixel, d'après la règle universelle. La variation locale de clarté porte la moitié de la dispersion mesurée.
- **Ce qui change à l'écran :**
  - les déserts gardent presque leur couleur, déjà proche ;
  - les régions humides tempérées deviennent moins vertes, plus olive et brunes. À 20 °C et 550 mm, la Terre est une savane sèche, pas une prairie verte ; notre planète était plus verte que son climat.
- **Coût :** aucun mesurable.
- **Calibrages à revoir en vol :** l'échelle entre humidité et précipitations, 100 à 3 000 mm, et la part de dispersion donnée au bruit local.

## Étape 2 : les sols photo, de près

Lancée le 2026-10-22, d'après l'essai `log/spec-hybride-scans.md` : les sols meubles passent à l'hybride, la roche reste procédurale.

- **Le scan de sable et gravier remplace la tuile générée du sable,** sur la bande de 3 cm à 50 cm. Un passe-haut le coupe au-dessus pour éviter le camouflage répété.
- **Il reste un facteur de moyenne 1 :** la teinte vient de la palette du biome, l'étape 1. C'est la recoloration statistique, à son premier degré.
- **Fusionnée le 2026-10-23,** commit `7bf38a9`.

## Étape 3 : les motifs vus d'avion, de 100 m à 4 km

**Le constat :** entre le pixel et la maille, à 1 à 50 km d'altitude, le sol n'a que la couleur de son biome et le grain de l'éclairage. Rien ne dessine les dunes, les champs, les forêts en taches, les lacs de la taïga, les réseaux d'oueds.

**Le principe :**
- **Une tuile par paysage,** environ 4 km en 1024 px, soit 4 m par pixel, découpée dans une image satellite libre de droits à un endroit typique de la Terre : erg, reg, savane, bocage et cultures, forêt tempérée, taïga à lacs, toundra, steppe, forêt tropicale, réseau d'oueds.
- **Rendue raccordable hors du moteur,** puis pavée au hasard comme les autres tuiles, sans répétition visible.
- **Un facteur de moyenne 1 sur la couleur du biome :** la tuile donne le motif, la palette donne la teinte. Les paysages se mêlent par leurs poids, tirés du climat et du relief, avec les limites élargies selon la règle universelle.
- **Elle s'efface d'elle-même de loin,** par ses mipmaps, quand un pixel couvre la tuile entière.
- **Les grandes tuiles ne divisent pas l'ancre de 64 m :** leurs coordonnées sont prises sur la planète entière, en simple précision. L'erreur, un demi-mètre, reste sous le pixel de la tuile.

**Le chargement :** le même que les sols photo, par WIC, au démarrage, désormais sur la branche principale.

**La mesure :** le banc d'orbite et des vues à 2, 10 et 50 km, à côté des mêmes paysages réels ; le banc de descente lumineux, pour vérifier que la couleur moyenne ne bouge pas.

## Étapes suivantes, à décider

2. **La recoloration statistique de près,** après l'essai hybride : chaque scan prend la moyenne et la variance de sa région.
3. **Le mélange de plusieurs scans** selon un bruit.
4. **Les motifs vus d'avion,** si l'on trouve des photos aériennes libres.
