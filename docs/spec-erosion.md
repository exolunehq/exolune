# Spec : l'érosion globale

Statut : spec vivante, depuis le 2026-10-31, branche `erosion-globale`, piste `piste/erosion-globale`. Elle part de la pile tectonique (`spec-relief-tectonique.md`) ; la recherche de la branche `erosion-niveaux` n'est qu'une source (section « Ce que la recherche a appris »). À juger en vol : `tools/tests/2026-10-31-erosion.txt`.

## L'objectif

**Les fleuves et les glaciers forment un seul système, de la planète au détail de 100 m.** Les chaînes montrent des vallées transverses ramifiées, des arêtes, des contreforts et une ligne de partage continue ; les plis restent en avant-pays ; tous les fleuves atteignent la mer ou un lac.

## L'architecture

**Trois niveaux, un seul réseau.** Le niveau 0 décide où va l'eau et à quelle hauteur ; les vallées et les ravines n'en sont que le dessin, de plus en plus fin, accroché à lui.

| Niveau | Échelles | Où, quand | Ce qu'il fait |
|---|---|---|---|
| 0, le réseau | nœuds à 20 km ; formes au-dessus de 40 km | CPU, au démarrage, sur la grille de la carte tectonique ; cache par graine | drainage vers la mer, lacs par bilan d'eau, niveau de l'eau par puissance fluviale, débit, glace, cônes et deltas |
| 1, les vallées du réseau | de 40 km à la largeur du lit | shader, par point (`Erosion.hlsli`) | chaque lien creuse sa vallée dans le sol grossier : fond au niveau de l'eau, versants à la pente de seuil, en U sous la glace ; deltas et cônes |
| 2, les ravines | de 11 km à 100 m | shader, dans les octaves du détail (`Relief.hlsli`) | les octaves réorientées le long de la pente du relief au-dessus d'elles : chaque ravine descend vers la vallée qui la porte |

**Pourquoi ce partage :**
- **Le niveau 0 est global :** un fleuve dépend de la mer et de tout l'amont. Il se calcule une fois, au démarrage, comme la carte tectonique.
- **Les niveaux fins sont locaux et déterministes :** une érosion simulée par tuiles est chaotique et coud mal (recherche, spike B). Une vallée ne lit que les liens du niveau 0 autour d'elle ; une ravine, la pente des octaves au-dessus d'elle.
- **Rien ne se calcule en route :** les niveaux 1 et 2 sont des fonctions du point, comme le bruit ; le niveau 0 est en mémoire dès le départ.
- **Un arbre explicite à plusieurs niveaux, à la Dendry, est écarté :** chaque nœud fin doit connaître les liens plus grossiers autour de lui, et ainsi de suite ; par sommet, le coût croît comme 9 puissance le nombre de niveaux.

## Le niveau 0, `Erosion.cpp`

**La grille :** celle de la carte tectonique, 6 × 512², environ 20 km. Le soulèvement et l'érodabilité s'y lisent sans interpolation.

**Les entrées :**
- **la forme avant érosion,** `ReliefElevation(p, false)` filtrée à deux mailles, calculée au démarrage sur le GPU au centre de chaque cellule (`ErosionForm.hlsl`) ;
- **le soulèvement U et l'érodabilité K,** tranches 3 et 4 de la carte tectonique, gardées en mémoire jusque-là ;
- **les précipitations P et la température T,** par une seule fonction de remplacement, `ErosionClimate`, jusqu'à la livraison du climat.

**Le calcul :**
1. **Le drainage :** un Priority-Flood depuis la mer donne la surface comblée et l'ordre de l'eau (Barnes, Lehman et Mulla 2014). Un corps sans mer se draine vers son point le plus bas.
2. **Les lacs par bilan d'eau :** une cuvette garde un lac terminal si l'eau qui y arrive est moindre que ce que toute sa surface évaporerait, moins la pluie sur elle ; son niveau, là où les cellules les plus basses évaporent l'apport. Les autres cuvettes débordent et se comblent : des plaines.
3. **Le routage :** chaque cellule vers sa voisine la plus basse sur la surface comblée, un plat par l'ordre de l'inondation ; la pente vers chaque voisine pesée de ±15 %, tirée par cellule et par voisine, d'après rho8 (Fairfield et Leymarie 1991) mais également : les chemins hésitent entre les deux directions qui encadrent la pente, au lieu de lignes droites à 45°. Le ruissellement par la courbe de Schreiber, cumulé vers l'aval.
4. **Le niveau de l'eau :** depuis la mer et les lacs, vers l'amont, la pente d'équilibre de la puissance fluviale, S = ks A^−θ, θ = 0,45 (Kirby et Whipple 2012) ; A l'aire drainée au ruissellement de référence, un bassin sec est plus raide. ks = √(30² + 150² U) / √K, U en mm/an : 30 sur les plaines, 150 à 1 mm/an, 330 à 5, l'Himalaya ; la racine, l'exposant de pente n = 2 mesuré sur les chaînes terrestres. Le niveau ne dépasse jamais la surface comblée : là où l'équilibre serait plus haut, le fleuve coule sur sa plaine.
5. **Le recul des points d'inflexion :** l'entaille remonte à vitesse finie, K A^0,5, le long des caractéristiques de la loi (Tzathas et al. 2024). Au-delà de 1 000 km parcourus par un fleuve de 10⁵ km², moins vite pour un plus petit, le sol garde sa forme : les plateaux ne sont entaillés qu'à leurs bords.
6. **La glace :** la ligne d'équilibre du dernier maximum glaciaire, 900 m sous l'actuelle ; l'actuelle où la température d'été vaut celle d'Ohmura, Kasser et Funk (1992) pour la précipitation, l'année 8 °C plus froide. Le bilan, 0,6 m/an par 100 m, au plus 2 m/an et la précipitation ; cumulé le long du même réseau, la glace d'amont plus le bilan de la cellule là où elle en a. Un glacier là où le flux reste positif.
7. **Les dépôts :** un cône là où un fleuve sort d'une vallée de plus de 200 m pour un sol qu'il entaille moins du quart ; un delta à l'embouchure sans glace d'un débit de plus de 300 m³/s.

**Les sorties, une texture `R32G32_UINT` par face, `t23` (`Erosion.h`) :**
- le niveau de l'eau au nœud et la surface comblée, au quart de mètre ;
- le receveur parmi les huit voisines, les affluents parmi les huit ; les drapeaux : lac, mer, cône, embouchure ;
- le débit et le flux de glace, en log.
- **Le nœud de chaque cellule** est un point tiré dans la cellule par son hachage, à 0,3 cellule au plus : rien à stocker.

**L’intégration avec le climat et les volcans :** `t18` porte la tectonique, `t19` ses vues, `t20` le climat, `t21` les volcans, `t22` leur index, `t23` l’érosion. La table contient six descripteurs. Le niveau 0 lit la forme avant érosion complète, édifices et finition volcanique compris. Les vallées et les dépôts précèdent l’abrasion ; les cordons suivent le rivage lissé, puis vient la finition des récifs. Les fonctions provisoires `ErosionClimate` et `ErosionWaveWind` restent celles de la piste ; leur raccord au climat calculé reste à faire.

**Le cache par graine :** `x64/Release/erosion-<graine>.bin`, sa clé la forme lue, la graine et la date de l'exécutable. Le portage CPU le lit aussi.

**Le relief et l'eau viennent des mêmes données (règle R5 de la recherche) :** le fond des vallées, les lacs et plus tard l'eau des fleuves se lisent tous dans cette texture.

## Le niveau 1 : les vallées du réseau, `ErosionValleys`

**Chaque lien du niveau 0 est une courbe :** une B-spline quadratique entre les milieux des liens, tangente d'un lien à l'autre ; un affluent rejoint le tronc tangentiellement, vers l'aval. Le point se lit gauchi de 7 km, de 40 et 20 km de longueur d'onde, pour que les liens droits serpentent.

**La vallée, autour de la courbe la plus proche :**
- **le fond,** au niveau de l'eau interpolé le long de la courbe, d'une demi-largeur 2 √Q m, jusqu'à 15 fois plus sur un fleuve lent, 0,15 cellule au plus ; le détail s'y éteint, sauf sous la mer, rien de plus fin que le niveau 0 ne barre le cours ;
- **les versants,** à la pente de seuil, 14° sur les sols tendres à 33° sur les chaînes jeunes ;
- **sous la glace,** une auge en U : demi-largeur 600 m à 10⁸ m³/an de glace, comme sa puissance 0,4, de 150 m à 1,5 km ; surcreusée de 0,3 de sa demi-largeur, versants à 40° ; le détail s'éteint en son milieu, où se rencontreraient les ravines de ses deux versants. Près d'une côte froide, son fond passe sous la mer : un fjord ;
- **le maillage :** une vallée moins large que deux mailles s'élargit, moins profonde d'autant.

**Le creusement déplace le sol grossier, il ne le coupe pas :** le sol s'abaisse d'autant que la vallée passe sous les grandes formes et les octaves de plus de 20 km, par un minimum lissé sur 60 m, jamais sous le niveau de l'eau. Le détail plus fin reste sur les versants, renforcé jusqu'à 0,35 de la profondeur creusée au point : contreforts et ravines à l'échelle du versant, rien de plus sur une plaine.

**Les dépôts :** un delta, un lobe vers le large à 3 m au-dessus de la mer, 60 √Q m, 1,6 fois plus large le long de la côte, son front descendant vers le plateau ; un cône, de 120 √Q m vers l'aval, pente de 3 %, son pied à 45°. L'un et l'autre bornés à 0,25 cellule, éteints à 0,3 cellule de leur sommet : les nœuds lus les tiennent toujours.

**Les recherches dans la texture :** les 4 × 4 nœuds autour du point, chacun avec ses affluents et son receveur ; un nœud à plus de 1,75 cellule est sauté ; aucune vallée ne porte au-delà de 0,5 cellule, ni en mer à plus de 500 m de fond. Les positions sont relatives au point, en flottants : une seule lecture en doubles par sommet.

**Ce que le détail lit en est continu :** la profondeur et la glace d'une vallée sont le maximum de celles des liens proches, chacune éteinte avant que les liens lus ne changent. Prises au seul lien le plus bas, elles sautaient d'un lien à l'autre, et le détail avec elles.

## Le niveau 2 : les ravines, dans `ReliefDetail`

**Les octaves du détail de 11 km à 100 m changent de motif là où le sol penche :**
- **un bruit de phase** (Tricard et al. 2019, *Procedural Phasor Noise*) : des ondes planes à travers la pente, une période par maille de l'octave, sur les 8 coins d'une maille de deux périodes, chacun sa phase ; la phase de leur somme. Ses singularités sont les confluences ;
- **la pente qui l'oriente :** celle des grandes formes, ou des versants de la vallée là où elle les creuse, plus celle des octaves plus larges ;
- **le même E|n| que l'octave qu'il remplace,** à 85 % sur une pente de plus de 0,15, rien sous 0,02 : la rugosité ne change pas, seul le motif s'ordonne vers l'aval ;
- **sous la glace,** à 300 m de part et d'autre de la ligne d'équilibre du maximum glaciaire et dans les auges : les crêtes en |x|^0,7, leur moyenne gardée. Des crêtes vives, des creux larges : arêtes, cirques, pics pyramidaux ;
- **elles s'éteignent où la pente qui les oriente se retourne :** sur les crêtes de l'octave au-dessus et de la plus large, celle des chaînes et des plis, et au rebord des vallées. Le motif des deux versants ne s'y raccorde pas : il dressait des lames en peigne le long des crêtes ;
- **elles s'éteignent autour de leurs bifurcations,** où la somme des ondes tombe sous 0,3 : la phase y prend toutes les valeurs, le sol s'y déchirait ;
- **les plis restent en avant-pays :** leur part tombe à zéro là où les vallées passent de 800 m à 2 km de profondeur, au cœur des chaînes.

## Les falaises côtières

**L’abrasion suit un contour du sol complet, détail, vallées et dépôts inclus.**
- **Où :** `ErosionCoast`, après les dépôts et avant les cordons, avec `valleys = true` seulement.
- **Le rivage estimé borne la portée :** il ne place plus une paroi dans les montagnes.
- **Le contour :** `Hc = clamp(1000 W G, 8, 400)` m ; le sol au-dessus de `Hc + δ` reste identique.
- **La largeur W :** 1,2 km × exposition × érodabilité, au plus 3 km ; variation de 45 % par un bruit de 2,4 km (Sunamura 1992, force sur résistance).
- **La pente G :** norme tangentielle des grandes formes et des trois octaves du détail de plus de 9 km ; la pente côtière `coastSlope × shoreMetric / 1000` reste un plancher.
- **Pourquoi 9 km :** trois fois le recul maximal ; les octaves de 50, 23,7 et 11,2 km gardent les grands versants sans laisser les petits éperons déplacer Hc.
- **Le coût :** pente capturée dans la somme existante de `ReliefDetail`, sans lecture supplémentaire de carte ou de bruit.
- **Le plafond de 400 m :** calibrage proche des 426 m de Conachair recensés par [NatureScot](https://www.nature.scot/landscapes-and-habitats/habitat-types/coast-and-seas/coastal-habitats/coastal-cliffs), sans maximum géologique universel.
- **Les caps et les anses :** roche dure et abri réduisent W et le contour ; roche tendre et exposition les augmentent.

**Le profil remappe la hauteur h.**
- **Sous Hc :** `min(h, P)` ; P vaut −1 m au pied, puis descend linéairement avec h vers l’ancien rivage.
- **Le platier :** pente nominale de 2 % sur W, dénivelé limité à 4 m (Trenhaile 1987).
- **Sous la mer :** raccord continu à la même droite ; tout fond plus profond reste intact.
- **La face :** raccord sur `δ = max(0,1 Hc, 2000 cellKm G)` m ; moins de deux mailles, elle s’élargit et s’incline.
- **L’abaissement :** au plus `Hc + 1 m`, même à maille grossière ; aucun sol relevé.
- **Les éboulis :** pente de 35°, jusqu’à 22 % de Hc, par taches de 900 m ; distance au pied exprimée par `abs(h − Hc) / G`.
- **Les stacks :** rares croisements de bandes de 130 m conservant le sol original ; élargis sur deux mailles, moins forts en proportion de leur surface.
- **Les rivières :** les fonds bas peuvent percer le contour et devenir des entrées de mer.

**Les entrées et la portée sont conservées.**
- **La roche :** classe convertie par texel avant B-spline ; croûte océanique 1, volcanique 0,6, jeune chaîne 1, sédiments 1,6, vieille chaîne 0,45, bouclier 0,25.
- **Les sédiments tendres :** facteur `1 + saturate(-forms.w)` au texel ; proxy continu du K absent de la carte GPU.
- **Le seul vent :** `ErosionWaveWind`, son jumeau CPU `erosion_wave_wind`, à remplacer ici par le climat.
- **Les zones :** alizés vers l’ouest ; vents d’ouest entre 30 et 60°, maximum de force 1,6 vers 45° ; vents polaires vers l’ouest ; transitions sur 26–34° et 56–64°.
- **L’exposition :** direction du large par le gradient des grandes formes ; houle omnidirectionnelle de 0,28.
- **Les baies :** éteintes à −12 km de déplacement côtier, pleinement exposées à −6 km.
- **La bande côté mer :** aucune limite intérieure au proxy brut de 8 km ; le détail peut y faire émerger la côte réelle.
- **La bande côté terre :** `shoreKm / shoreMetric < min(W + 1 + relief / coastSlope, 8)` km ; extinction sur les 500 derniers mètres.
- **Le déplacement du détail :** son amplitude tectonique `relief`, avant le terme des parois de vallée, divisée par la pente côtière en m/km ; une distance en km, sans nouvelle lecture.
- **Le proxy brut :** `abs(shoreKm) < 8 km`, extinction sur 500 m des deux côtés ; limite de calcul conservée, indépendante de la maille.
- **L’accès marin :** un témoin à 3 km, `RETREAT.z`, dans la direction du large des grandes formes déjà utilisée pour les vagues ; son sol avant érosion doit être sous −50 m.
- **Pourquoi avant érosion :** une vallée ou une auge creusée ne doit pas ouvrir à elle seule l’accès aux vagues.
- **Le témoin :** même relief, cordons et limitation des sommets, sans vallées, ravines d’érosion ni dépôts ; aucune lecture supplémentaire du réseau d’érosion.
- **Le raccord :** sa présence passe continûment de 1 à 0 sur 250 m de distance côtière, convertis par la pente du témoin ; elle vaut 0 dès −50 m.
- **La nature du test :** témoin marin conservateur, pas une mesure globale de connexité ; le seuil de −50 m est celui du contrôle de portée, pas une profondeur universelle d’abrasion.
- **La position du témoin :** rotation à petit angle en doubles ; aucun produit d’une position planétaire en float par le rayon.
- **Rien sur les côtes plates ni dans les baies totalement abritées.**
- **Le coût :** sorties précoces hors bande ; les sols intacts sautent les bruits des éboulis et des vestiges ; seule une coupe potentielle lit ce second point de terrain, sans nouvelle recherche de vallées.
- **Le branchement :** `ReliefSampleGround` sépare le sol du traitement côtier ; `ReliefFinish` garde les cordons et le plafond ; le témoin ne récursive pas et ne remplace pas la rugosité du point principal.

**Les réglages, préfixe `EROSION_CLIFF_` dans `PlanetSettings.hlsli` :**

| Réglage | Valeur | Sens |
|---|---|---|
| `RETREAT` | `(1, 1.2, 3, 0.45)` | activation, recul unitaire et maximum en km, variation relative |
| `NOISE` | `2.4` | longueur d’onde du recul, km |
| `BAY` | `(-12, -6)` | extinction et pleine exposition, km de déplacement |
| `REACH` | `(1, 0.5, 8)` | marge intérieure en plus du recul et du détail, extinction, plafond intérieur et borne du proxy, km |
| `SEA` | `(50, 0.25)` | profondeur minimale du témoin en m, transition en km ; sa distance est `RETREAT.z` |
| `HEIGHT` | `(8, 400)` | bornes Hc, m |
| `SLOPE_KM` | `9` | seuil des octaves qui portent la pente, km ; auparavant 0,3 |
| `FACE` | `0.1` | part minimale de Hc pour δ |
| `SCREE` | `(0.7002, 0.22)` | pente de repos, part de Hc |
| `PLATFORM` | `(-1, 0.02, 4)` | pied en m, pente nominale, dénivelé maximal en m |
| `STACK` | `(0.065, 0.8, 1.4)` | demi-largeur et bruit en km, seuil régional |
| `WAVES` | `(0.28, 1.6)` | houle, force des quarantièmes |

**Les mesures CPU, graines 0 et 1 :** `python tools/cotes/verifie_falaises.py`.
- **Les trois coupes fixes :** centres rendus par l’utilisateur ; orientation par la pente du sol original ; face recherchée à moins de 2 km du centre, pas de 10 m.
- **La hauteur :** du platier voisin à la crête qui rejoint le sol original, sans remplacer cette mesure par Hc.
- **La terre devant le pied :** largeur cumulée au-dessus de +5 m, jusqu’au premier fond original sous −20 m vers le large.

| Centre | Paroi, m | Angle | Platier, m | Terre devant, m |
|---|---:|---:|---:|---:|
| 8,72580 ; −103,29430 | 252,295 | 80,95° | −1,157 | 0 |
| −23,18981 ; 157,86949 | 42,020 | 67,38° | −1,242 | 0 |
| −3,21302 ; 169,26372 | 121,945 | 83,76° | −1,939 | 0 |

**Les six fenêtres restent sous 5 % de coupes enclavées et 4 km de portée au p99.**
- **Les fenêtres :** 10 × 10 km, 201² points incluant les bords, pas et maille de 50 m.
- **L’inondation :** départ du sol original sous −20 m ; quatre voisins ; passage par le sol nouveau sous 0 m ou abaissé de plus de 1 m.
- **La part enclavée :** fraction des points abaissés de plus de 10 m que l’inondation n’atteint pas.
- **La mer originale :** sol original sous 0 m relié, par quatre voisins dans la fenêtre, à un sol sous −50 m.
- **La distance à la mer :** minimum euclidien exact sur cette grille, pour les points abaissés de plus de 10 m ; p99 et maximum, sans scipy.
- **Une fenêtre sans coupe :** aucun quantile à calculer, noté « — ».

| Graine ; centre | Enclavé | Distance mer p99 / maximum, m | Abaissement maximal, m | Surface abaissée de plus de 10 m |
|---|---:|---:|---:|---:|
| 0 ; 8,73276 ; −103,30263 | 0 % | 604,152 / 680,074 | 296,530 | 4,846 % |
| 0 ; −23,18173 ; 157,88952 | 0 % | 400,000 / 502,494 | 109,573 | 1,317 % |
| 0 ; −3,21302 ; 169,26372 | 0 % | 549,885 / 696,419 | 227,117 | 2,728 % |
| 1 ; −65,00789 ; −113,42094 | 0 % | — | 0 | 0 % |
| 1 ; 23,78161 ; −126,35919 | 0,113 % | 1 388,320 / 1 656,050 | 365,902 | 4,384 % |
| 1 ; 40,46592 ; −84,75513 | 0 % | 559,017 / 626,498 | 189,467 | 2,267 % |

- **La côte tropicale de graine 1 :** secteur actif le plus proche de 23,70143/−126,32998 dans un carré de 60 km, pas de 496 m ; aucune coupe dans le carré initial de 10 km.
- **La plaine glaciaire :** aucun abaissement ; son témoin reste sur des terres, de +26 à +799 m pour les anciennes coupes.
- **Le diagnostic :** le défaut existait avec la bande symétrique ; les deux extensions du cinquième passage ne l’aggravaient que légèrement, [historique](log/spec-erosion-historique.md).
- **L’hypothèse des vallées :** aucun lien du niveau 0 ne creusait les points abaissés de cette fenêtre ; un Hc régional trop permissif suffit à y couper les collines et les dépressions du détail.
- **Le contour :** Hc, son filtre de 9 km et les trois parois mesurées restent inchangés ; l’ouverture côté mer est conservée derrière le contrôle d’accès.
- **La limite globale :** le test d’accès local n’est pas un routage océanique ; la distance est vérifiée sur le sol réellement érodé, et le plafond du proxy peut encore exclure un rivage déplacé de plus de 8 km.
- **La borne mesurée sur ces fenêtres :** `abaissement − Hc ≤ 0,998 m`.
- **La côte plate témoin :** écart nul à 16,71/−89,28, sur la coupe et 441 points d’un carré de 10 km.
- **`valleys = false` :** identique au portage commité sur 288 points de chacune des deux graines, aux mailles de 10 m, 1 km et 30 km.
- **Le portage :** les deux scripts affichent `ok` ; continuité aux trois raccords du profil et aux bords de la bande, ouverture côté mer, fond profond et abaissement borné vérifiés jusqu’à une maille de 30 km.
- **La compilation :** Release x64 réussie, aucun avertissement dans les fichiers modifiés ; aucun moteur ni banc lancé.

**Hc sur la côte active, médiane/p90/maximum, en mètres :** carré de 60 km, 201² points, pas de 300 m, maille de 10 m ; sol original entre 0 et Hc, abaissé de plus de 1 m.

| Centre | Points | Médiane | p90 | Maximum |
|---|---:|---:|---:|---:|
| 8,54005 ; −103,23344 | 112 | 134,698 | 251,737 | 337,176 |
| −23,01696 ; 158,00809 | 105 | 64,819 | 110,074 | 126,281 |
| −3,34285 ; 169,01181 | 229 | 78,515 | 163,812 | 245,786 |
| −51,89165 ; −40,94037 | 89 | 89,894 | 132,712 | 214,339 |
| −8,11021 ; 131,04460 | 140 | 135,055 | 163,490 | 192,919 |
| 8,76166 ; −103,24998 | 173 | 110,260 | 219,854 | 329,615 |

**Les côtes froide et active :** recentrage sur le premier passage par zéro du sol original, le plus proche du point demandé sur une coupe de 30 km normale aux grandes formes.
- **La recherche :** passage encadré au pas de 10 m, affiné par dichotomie ; aucune sélection sur la hauteur ou la raideur de la paroi.
- **La côte froide :** rivage à −51,79251/−40,80271 ; paroi de 86,900 m à 75,62°, platier à −1,576 m ; bande et proxy à 1, exposition 0,28, K 0,984724.
- **La limite de cette coupe froide :** elle croise encore 660 m de terres au-dessus de +5 m entre ce pied et le premier fond original sous −20 m.
- **La côte active :** rivage à −8,10764/131,04054 ; aucune face à moins de 2 km sur sa coupe ; exposition 0,663389, K 1, proxy et bande nuls.
- **La cause sur la côte active :** son proxy de 11,407 km dépasse le plafond conservé de 8 km ; ce n’est pas un abri des vagues.
- **Les statistiques de Hc :** la valeur du champ au point reste identique ; le témoin filtre les surfaces actives, donc les distributions changent.
- **Les modèles remplacés :** [historique](log/spec-erosion-historique.md) ; jugement en vol par l’utilisateur : `tools/tests/2026-10-31-erosion.txt` pour la graine 0, `2026-10-31-falaises-graine1.txt` sur un build de la graine 1.

## Le drapeau `valleys`

**`ReliefElevation(p, true)` rend le relief érodé ; `(p, false)` la forme avant érosion,** sans aucun niveau, celle que le niveau 0 lit. Le niveau 0 ne lit jamais ses propres sorties.

## Les branchements

**Avec le climat :** `ErosionClimate` rend P (m/an) et T au niveau de la mer (°C), dans `Erosion.cpp` et sa jumelle dans `Erosion.hlsli`. La session climat remplace leur corps par la lecture de ses cartes. Aujourd'hui, des moyennes zonales tous les 10° de latitude, symétriques ; l'érosion applique elle-même 6,5 K/km.

**Avec le volcanisme :** ses édifices s'ajoutent à la forme avant érosion, `ReliefElevation(p, false)`. Le niveau 0 les voit s'ils dépassent 40 km ; plus petits, les ravines les découpent comme tout relief. `ReliefDetail` gagne deux paramètres, les ravines et la somme grossière.

**Avec l'eau, plus tard :** les fleuves se dessinent depuis le débit et le niveau de l'eau des liens, les lacs depuis leur niveau, les fjords et les estuaires où les vallées passent sous la mer.

## Le portage CPU

**`tools/hydro/cp.py` lit le niveau 0 du moteur,** `erosion-<graine>.bin`, et refait les vallées, les dépôts et les ravines ; les nœuds en float32, comme le shader. `EXOLUNE_EROSION` donne un autre chemin.

## Les mesures, graine 0

| Mesure | Valeur | Budget proposé, et pourquoi |
|---|---|---|
| Démarrage, niveau 0 à froid | 0,54 s, dont 0,50 s de réseau ; le shader de la forme compilé pendant la carte tectonique | 0,5 s par planète : la moitié de la carte tectonique, le système entier en quelques secondes au premier lancement |
| Démarrage, depuis le cache | 0,03 s | 0,05 s : un fichier de 12 Mo par corps |
| Mémoire GPU | 12 Mo | 13 Mo : 8 octets par cellule, un tiers de la carte tectonique |
| Calcul du terrain, en mouvement | 0,67 à 1,46 ms contre 0,28 à 0,95 ms, +0,2 à +0,65 ms ; minimum de 3 passages, GPU partagé et chargé à 75 % | +0,5 ms au plus : la marge d'une image à 120 fps |
| Portage contre la carte de la planète, 600 mailles | écart médian 0,6 cm ; p99 0,22 m ; 0,6 m au plus | 10 cm en médiane |
| Portage contre le sol sous la caméra, mailles fines, 7 lieux | médiane 0,18 m, 0,5 m au plus, la précision du titre | — |

**Le réseau, graines 0, 1 et 2,** mesuré sur le fichier du moteur, `erosion-<graine>.bin` :

| Graine | Vers la mer, vers les lacs | Lacs | Glace | Plus grands bassins | Plus grand débit | Entaille aux nœuds, p90 et p99 |
|---|---|---|---|---|---|---|
| 0 | 82,2 %, 17,8 % | 0,95 % | 22,1 % | 5,6, 3,1, 2,4 Mkm² | 71 000 m³/s | 314 m, 2,3 km |
| 1 | 81,2 %, 18,8 % | 0,80 % | 18,3 % | 4,6, 3,5, 2,9 Mkm² | 93 000 m³/s | 430 m, 2,3 km |
| 2 | 86,4 %, 13,6 % | 1,87 % | 21,8 % | 7,7, 3,0, 2,8 Mkm² | 185 000 m³/s | 559 m, 2,6 km |

- **Toutes les terres atteignent la mer ou un lac terminal,** aucun cycle, pour les trois graines. Sur Terre, environ 18 % des terres sont endoréiques ; l'Amazone draine 7 Mkm², 200 000 m³/s.
- **Graine 0 :** 787 deltas, 2 115 cônes ; entaille médiane nulle, les fleuves des plaines coulent sur leur plaine.
- **Les graines 1 et 2** ont été vérifiées avant le routage pesé ; la graine 0, avant et après, garde un drainage complet.

## Les défauts connus

- **Les vallées du niveau 0 restent trop régulières vues de près :** des versants plans à pente constante, des auges aux fonds plats et aux parois en falaise, comme taillées ; les versants convexes en haut, concaves en bas, et les éperons tronqués sont à faire.
- **Les deltas sont petits, et l'un d'eux faux :** 5 km au plus, la portée des nœuds lus ; à l'embouchure du plus grand fleuve, -7,8°, 27,2°, une langue de dépôt isolée au large, cause non trouvée, et un pan de côte aux bords droits, qui ne vient pas des dépôts. Les grands deltas demandent un champ des dépôts lu en B-spline.
- **Les ravines se voient peu de loin :** elles gardent l'amplitude des octaves qu'elles remplacent ; les deux octaves de plus de 20 km gardent leurs crêtes orientées le long des chaînes.
- **Le coût du calcul du terrain dépasse un peu le budget :** +0,65 ms au plus, à l'orbite et au ras du sol.
- **Les fleuves des flancs restent parallèles et droits sur 50 à 100 km,** sur les pentes régulières : la forme avant érosion filtrée à 40 km n'y a pas de relief qui les dévie.
- **Le climat de remplacement n'a pas de continentalité :** peu de lacs terminaux à l'intérieur des continents.
- **Les falaises manquent où le rivage réel s'écarte de plus de 8 km de son estimation :** la côte active à -8,11°, 131,04° n'en a pas ; le plafond borne le coût.
- **Les falaises ne se voient qu'à quelques km :** de 30 km, le platier n'est qu'une bande turquoise ; la paroi à 23° S reste basse, 42 m.
- **Le témoin marin relit le relief avant érosion là où une coupe est possible :** son coût GPU n'a pas été mesuré au banc, seulement dans le bruit des rendus en mouvement.
- **Les vues de la planche** sont des premiers jets : à juger en vol, la liste `tools/tests/2026-10-31-erosion.txt`.

## Ce que la recherche a appris

Branche `erosion-niveaux`, `docs/recherche-erosion-niveaux.md` :
- **un niveau 0 global, calculé une fois, tient** (spikes A3) : drainage complet, lacs par bilan d'eau, bassins de 1 à 9 millions de km². Repris ici, son bilan d'eau compris ;
- **une érosion simulée par tuiles est chaotique** (spike B) : 43 m d'écart moyen entre tuiles et calcul d'un bloc, jusqu'à 2 km. Les niveaux fins sont donc une construction locale ;
- **un tracé choisi sur des cellules de 25 km fait passer les fleuves à travers les montagnes** (constat du 2026-10-27) : 44 % de leur longueur creusée à plus de 50 m sous le sol. D'où : le sol grossier s'abaisse jusqu'à la vallée au lieu d'être coupé, la vallée a des versants, le détail s'éteint sur son fond ;
- **ce qu'on ne reprend pas :** le soulèvement inventé à partir des hauteurs, l'érosion pas à pas, 10 minutes par graine, les tuiles calculées à l'approche.

## Les sources

- Barnes, Lehman, Mulla, *Priority-Flood: An Optimal Depression-Filling and Watershed-Labeling Algorithm*, Computers & Geosciences 62, 2014.
- Kirby, Whipple, *Expression of active tectonics in erosional landscapes*, Journal of Structural Geology 44, 2012.
- Tzathas, Gailleton, Steer, Cordonnier, *Physically-based Analytical Erosion for fast Terrain Generation*, CGF 43(2), 2024.
- Ohmura, Kasser, Funk, *Climate at the equilibrium line of glaciers*, Journal of Glaciology 38(130), 1992.
- Tricard, Efremov, Zanni, Neyret, Martínez, Lefebvre, *Procedural Phasor Noise*, ACM TOG 38(4), 2019.
- Fairfield, Leymarie, *Drainage networks from grid digital elevation models*, Water Resources Research 27(5), 1991 : rho8.
- Sunamura, *Geomorphology of Rocky Coasts*, Wiley, 1992 : force des vagues et résistance de la roche ; distance cumulée paramétrée ici, sans simulation temporelle.
- Trenhaile, *The Geomorphology of Rock Coasts*, Oxford University Press, 1987 : platiers d'abrasion à faible pente.
- Gaillard, Guérin, Galin, Peytavie, Paris, *Dendry: A Procedural Model for Dendritic Patterns*, I3D 2019 : lu, écarté pour son coût par sommet.

## Le plan par étapes

| Étape | Contenu | Statut |
|---|---|---|
| 1 | Le niveau 0 au démarrage, sa texture, les vallées de ses liens | fait le 2026-10-31 |
| 2 | Les ravines, le recul des points d'inflexion, les cônes et les deltas, le portage | fait le 2026-10-31 |
| 3 | Le coût : positions en flottants, cache par graine | fait le 2026-10-31 |
| 3 bis | Les lames et les déchirures des ravines, la continuité de ce que lit le détail, le routage pesé, le portage à 0,6 cm | fait le 2026-10-31 |
| 4 | Les versants : profils convexes-concaves, éperons tronqués des auges | à faire |
| 5 | Les grands deltas, par un champ des dépôts | à faire |
| 6 | L'eau des fleuves et des lacs, depuis le même réseau | à faire, avec la mer |
