# Historique de l'optimisation

**Ce qui a servi aux rounds, et ne décrit plus l'état présent** (`../optimisation.md`).

## Round 1 : l'analyse de départ

**La passe des nuages pèse le plus partout,** de 10 à 51 ms. Un rayon par pixel en pleine résolution, à chaque image ; à chaque pas dans un nuage, quatre échantillons vers le soleil.

**Ce que coûte chaque part,** mesuré par variantes du shader :
- **La quadrature lointaine,** quatre rayons de plus par pixel au loin (`spike-nuages-orbite.md`) : 39 ms sur 51 en orbite, 11 sur le globe, 6 en mer, 4 au cumulus. En mer et au cumulus, la caméra sous 14 km l'éteint : ces 6 et 4 ms venaient du poids de son code sur les registres de tous les pixels.
- **L'ombre des nuages au sol,** une marche vers le soleil par pixel éclairé : 3 à 4 ms près du sol, 1 à 6 ailleurs.
- **La marche principale, sans ces deux parts :** encore 23 à 35 ms en mer, au cumulus et sur le globe. En rasant l'horizon, un rayon traverse des centaines de kilomètres de couche à pas de 240 m au plus.

## Round 2 : l'analyse de départ

**Le dessin du terrain pesait 11 à 17 ms près du sol, et 12 ms en survol.** Le vertex shader et la trame n'en prennent que 0,2 à 0,3 ms : tout est dans le pixel shader.

**Ce que coûte chaque part,** variantes du shader avant la profondeur d'abord, ms en forêt / montagne / survol :
- **Le sol entier, matériaux et végétation :** 12,4 / 16,6 / 11,4. Le reste, normales, lumière, mer : 0,5 à 0,7.
- **La végétation :** 4,9 / 7,0 / 5,5.
- **Les textures :** 5,1 / 9,4 / 4,1.
- **Les bruits local et de détail :** 2,9 / 3,0 / 2,8.
- **Les strates :** 0,8 / 0,4 / 1,0 ; quadratures des pentes 0,2 / 1,8 / 0,4 ; normales des splines et pente fine, jusqu'à 0,5 chacune.

**Après la profondeur d'abord,** ms en forêt / montagne / survol / orbite :
- **La présence des bois :** 1,5 / 1,8 / 2,6 / 0,6 ; la dalle de la canopée : 0,8 / 1,0 / 1,1 / 0,2 ; `PlantsDrawn` : 0,8 / 0,8 / 0,6 / 0,5.
- **La roche :** 1,0 / 2,8 / 1,5 / 0,7 ; l'herbe : 1,2 / 0,9 / 0,7 / 0,3.

**Le surcoût des quads,** mesuré après la profondeur d'abord (`IsHelperLane`, modèle 6.6) : 2,0 voies par pixel montré en survol, 1,9 en forêt, 1,6 en montagne et au cumulus, 1,2 en orbite.
