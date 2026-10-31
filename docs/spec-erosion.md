# Spec : l'érosion globale

Statut : spec vivante, depuis le 2026-10-31, branche `erosion-globale`, piste `piste/erosion-globale`. Elle part de la pile tectonique (`spec-relief-tectonique.md`) ; la recherche de la branche `erosion-niveaux` n'est qu'une source (section « Ce que la recherche a appris »). Parcours courant : `tools/tests/2026-10-31-ravines-roche-auges.txt` ; les étapes précédentes restent dans `tools/tests/2026-10-31-erosion.txt`.

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
- **les précipitations P et la température T,** par `ErosionClimate`, lecture bilinéaire continue de `Climate::At` sur la carte CPU gardée depuis `CreateClimateMap`.

**Le calcul :**
1. **Le drainage :** un Priority-Flood depuis la mer donne la surface comblée et l'ordre de l'eau (Barnes, Lehman et Mulla 2014). Un corps sans mer se draine vers son point le plus bas.
2. **Les lacs par bilan d'eau :** une cuvette garde un lac terminal si l'eau qui y arrive est moindre que ce que toute sa surface évaporerait, moins la pluie sur elle ; son niveau, là où les cellules les plus basses évaporent l'apport. Les autres cuvettes débordent et se comblent : des plaines.
3. **Le routage :** chaque cellule vers sa voisine la plus basse sur la surface comblée, un plat par l'ordre de l'inondation ; la pente vers chaque voisine pesée de ±15 %, tirée par cellule et par voisine, d'après rho8 (Fairfield et Leymarie 1991) mais également : les chemins hésitent entre les deux directions qui encadrent la pente, au lieu de lignes droites à 45°. Le ruissellement par la courbe de Schreiber, cumulé vers l'aval.
4. **Le niveau de l'eau :** depuis la mer et les lacs, vers l'amont, la pente d'équilibre de la puissance fluviale, S = ks A^−θ, θ = 0,45 (Kirby et Whipple 2012) ; A l'aire drainée au ruissellement de référence, un bassin sec est plus raide. ks = √(30² + 150² U) / √K, U en mm/an : 30 sur les plaines, 150 à 1 mm/an, 330 à 5, l'Himalaya ; la racine, l'exposant de pente n = 2 mesuré sur les chaînes terrestres. Le niveau ne dépasse jamais la surface comblée : là où l'équilibre serait plus haut, le fleuve coule sur sa plaine.
5. **Le recul des points d'inflexion :** l'entaille remonte à vitesse finie, K A^0,5, le long des caractéristiques de la loi (Tzathas et al. 2024). Au-delà de 1 000 km parcourus par un fleuve de 10⁵ km², moins vite pour un plus petit, le sol garde sa forme : les plateaux ne sont entaillés qu'à leurs bords.
6. **La glace :** la ligne d'équilibre du dernier maximum glaciaire, 900 m sous l'actuelle ; l'actuelle où la température d'été vaut celle d'Ohmura, Kasser et Funk (1992) pour la précipitation, avec une correction fixe d'été de +8 °C à la moyenne annuelle. Le bilan, 0,6 m/an par 100 m, au plus 2 m/an et la précipitation ; cumulé le long du même réseau, la glace d'amont plus le bilan de la cellule là où elle en a. Un glacier là où le flux reste positif.
7. **Les dépôts :** un cône là où un fleuve sort d'une vallée de plus de 200 m pour un sol qu'il entaille moins du quart ; un delta à l'embouchure sans glace d'un débit de plus de 300 m³/s.

**Les sorties, une texture `R32G32_UINT` par face, `t23` (`Erosion.h`) :**
- le niveau de l'eau au nœud et la surface comblée, au quart de mètre ;
- le receveur parmi les huit voisines, les affluents parmi les huit ; les drapeaux : lac, mer, cône, embouchure ;
- le débit et le flux de glace, en log.
- **Le nœud de chaque cellule** est un point tiré dans la cellule par son hachage, à 0,3 cellule au plus : rien à stocker.

**L’intégration avec le climat et les volcans :** `t18` porte la tectonique, `t19` ses vues, `t20` le climat, `t21` les volcans, `t22` leur index, `t23` l’érosion. La table contient six descripteurs. Le niveau 0 lit la forme avant érosion complète, édifices et finition volcanique compris. Les vallées et les dépôts précèdent l’abrasion ; les cordons suivent le rivage lissé, puis vient la finition des récifs. Le climat est calculé avant le niveau 0, qui lit sa carte CPU ; `ErosionClimate` et `ErosionWaveWind` lisent les mêmes champs côté shader et portage.

**Le cache par graine :** `x64/Release/erosion-<graine>.bin`, sa clé la forme lue, la taille et tous les champs CPU du climat, la graine et la date de l’exécutable. L’ancienne clé ne couvrait pas explicitement le climat ; tout changement de ses champs invalide désormais le cache, même à exécutable et relief identiques. Le portage CPU le lit aussi.

**Le relief et l'eau viennent des mêmes données (règle R5 de la recherche) :** le fond des vallées, les lacs et plus tard l'eau des fleuves se lisent tous dans cette texture.

## Le niveau 1 : les vallées du réseau, `ErosionValleys`

**Chaque lien du niveau 0 est une courbe :** une B-spline quadratique entre les milieux des liens, tangente d'un lien à l'autre ; un affluent rejoint le tronc tangentiellement, vers l'aval. Le point se lit gauchi de 7 km, de 40 et 20 km de longueur d'onde, pour que les liens droits serpentent.

**Un gauchissement de direction reste sur la sphère :**
- **La cause des auges fermées :** la turbulence déplaçait p en 3D sans le renormaliser. La distance à la courbe comptait son décalage radial, parfois kilométrique, comme une distance transversale ; le profil remontait sur le thalweg et fermait le fond.
- **La correction dans `ErosionValleys` :** retour à l’unité avant la localisation et les distances ; estimation de la racine inverse en flottant, un raffinement de Newton en doubles avant de multiplier p. Aucun niveau d’eau modifié, aucun seuil forcé ni drainage local.
- **Le sol non creusé reste libre :** le fond ne calme le détail que si `h > max(surface, level)` ; la même surface bornée à l’eau sert à estimer la part creusée et le renfort de détail des parois. Le profil sous l’eau ne doit pas effacer un sol situé sous son niveau et qu’il ne peut creuser.

**La vallée, autour de la courbe la plus proche :**
- **le fond,** au niveau de l'eau interpolé le long de la courbe, d'une demi-largeur 2 √Q m, jusqu'à 15 fois plus sur un fleuve lent, 0,15 cellule au plus ; le détail s'y éteint, sauf sous la mer, rien de plus fin que le niveau 0 ne barre le cours ;
- **les versants,** à la pente de seuil, 14° sur les sols tendres à 33° sur les chaînes jeunes ;
- **sous la glace,** une auge en U : demi-largeur 600 m à 10⁸ m³/an de glace, comme sa puissance 0,4, de 150 m à 1,5 km ; surcreusée de 0,3 de sa demi-largeur, versants à 40° ; le détail s'éteint en son milieu, où se rencontreraient les ravines de ses deux versants. Près d'une côte froide, son fond passe sous la mer : un fjord ;
- **le maillage :** une vallée moins large que deux mailles s'élargit, moins profonde d'autant.

**Le creusement déplace le sol grossier, il ne le coupe pas :** le sol s'abaisse d'autant que la vallée passe sous les grandes formes et les octaves de plus de 20 km, par un minimum lissé sur 60 m, jamais sous le niveau de l'eau. Le détail plus fin reste sur les versants, renforcé jusqu'à 0,35 de la profondeur creusée au point : contreforts et ravines à l'échelle du versant, rien de plus sur une plaine.

**Le fond se raccorde au niveau de l’eau, dans les deux sens (`ErosionCarve`) :**
- **Le résidu fin est `h − coarse` :** le simple abaissement grossier le laissait creuser des fosses et dresser des seuils au milieu des auges.
- **Le plateau réellement noyé compte entier :** le profil brut `bed` est borné par `min(coarse, level)` ; là où cette borne impose l’eau, le raccord retire tout le résidu, positif ou négatif. Le seul `floorShare` ne suffisait pas : le milieu calme du U s’arrête avant toute sa partie sous l’eau.
- **Vers les parois :** part `max(floorShare, 1 − smoothstep(0, 60, bed − level))` ; même part du fond, complétée par le plateau réellement borné à l’eau. Un `smoothstep(0, 60, coarse − cut)` ouvre le raccord avec le creusement ; aucun creusement, aucun changement. Le relief grossier et le profil restent entiers.
- **Le niveau vient toujours du lien lu :** un lac du niveau 0 garde son niveau propre ; aucune hauteur d’eau locale inventée. Ces fonds indiquent où sera l’eau des fleuves et des lacs ; elle n’est pas encore rendue.

**Les dépôts :** un delta, un lobe vers le large à 3 m au-dessus de la mer, 60 √Q m, 1,6 fois plus large le long de la côte, son front descendant vers le plateau ; un cône, de 120 √Q m vers l'aval, pente de 3 %, son pied à 45°. L'un et l'autre bornés à 0,25 cellule, éteints à 0,3 cellule de leur sommet : les nœuds lus les tiennent toujours.

**Les recherches dans la texture :** les 4 × 4 nœuds autour du point, chacun avec ses affluents et son receveur ; un nœud à plus de 1,75 cellule est sauté ; aucune vallée ne porte au-delà de 0,5 cellule, ni en mer à plus de 500 m de fond. Les positions sont relatives au point, en flottants : une seule lecture en doubles par sommet.

**Ce que le détail lit en est continu :** la profondeur et la glace d'une vallée sont le maximum de celles des liens proches, chacune éteinte avant que les liens lus ne changent. Prises au seul lien le plus bas, elles sautaient d'un lien à l'autre, et le détail avec elles.

## Le niveau 2 : les ravines, dans `ReliefDetail`

**Les octaves du détail de 11 km à 100 m changent de motif là où le sol penche :**
- **un bruit de phase** (Tricard et al. 2019, *Procedural Phasor Noise*) : des ondes planes à travers la pente, une période par maille de l'octave, sur les 8 coins d'une maille de deux périodes, chacun sa phase ; la phase de leur somme. Ses singularités sont les confluences ;
- **la pente qui l'oriente :** celle des grandes formes, ou des versants de la vallée là où elle les creuse, plus celle des octaves plus larges ;
- **un remplacement centré de l’octave ordinaire,** demandé à 85 % sur une pente de plus de 0,15, rien sous 0,02 ; sa part est réduite par le budget de pente, sans réduire le bruit porteur ;
- **près et au-dessus de la glace,** la bande de ±300 m autour de la ligne d’équilibre du maximum glaciaire seule active les arêtes ; `valley.glacier` garde les auges en U et ses autres lecteurs, sans affûter le détail ;
- **un profil monotone à pente finie :** pour `u = |x| / scale`, `(1+b)u − bu²` jusqu’à 1, puis sa tangente ; `b = 0,2 × glacial`, zéro l’arrête ; sa dérivée augmente d’au plus 15,1 % avant arrondi, contre une puissance singulière auparavant ;
- **le même intervalle d’arrondi :** une parabole raccordée en valeur et pente sur `max(crease, CREASE_ROUNDING × f / gCreaseMaxFrequency)` ; aucune largeur plus fine n’est réintroduite ;
- **la moyenne gardée :** normalisation par `E|cos| = 2/π` et `E cos² = 1/2`, puis soustraction de l’excès exact de l’arrondi sur les bandes sinusoïdales ; une série évite la soustraction de termes voisins ; le changement est exactement nul à `b = 0` ;
- **elles s'éteignent où la pente qui les oriente se retourne :** sur les crêtes de l'octave au-dessus et de la plus large, celle des chaînes et des plis, et au rebord des vallées. Le motif des deux versants ne s'y raccorde pas : il dressait des lames en peigne le long des crêtes ;
- **elles s'éteignent autour de leurs bifurcations,** où la somme des ondes tombe sous 0,3 : la phase y prend toutes les valeurs, le sol s'y déchirait ;
- **les plis restent en avant-pays :** leur part tombe à zéro là où les vallées passent de 800 m à 2 km de profondeur, au cœur des chaînes.

**Deux sols, deux échelles, un mélange continu (`ReliefGullyRock`, `ReliefGullyGain`) :**
- **Le sol et les éboulis :** `Sc = 1,25`, Roering et al. 1999 ; sous 300 m de longueur d’onde et hors des chaînes, le budget conservateur de C reste entier.
- **Le passage à la roche :** de 300 m à 1 km, `smoothstep` physique, jamais le pas du maillage. [Grieve, Mudd et Hurst 2016](https://onlinelibrary.wiley.com/doi/10.1002/esp.3884), *How long is a hillslope?*, mesurent des médianes de versants de 98 à 228 m ; la plage 300 m–1 km est notre séparation progressive entre ces versants et les incisions de massif, pas une constante universelle tirée de l’article.
- **La roche présente :** `r = mountains × smoothstep(600, 1400, relief) × smoothstep(0,3, 1, wavelengthKm) × (0,8 + 0,2 glacial)`. `relief` est l’amplitude en mètres passée au détail, `mountains` la part de chaînes existante ; la ligne d’équilibre renforce la roche, elle n’est plus sa seule preuve. Jamais `valley.glacier`.
- **La résistance rocheuse :** `Sc = tan(70°)`, choix de roche forte dans le cadre de Selby 1980, conservé de D. L’arrondi fini des crêtes et leur moyenne ne changent pas.
- **La saturation commune :** pour la pente porteuse s, la réserve de l’octave ordinaire N et celle de la bande G, `L = max(Sc − s − N, 0)`, `B = L²/Sc`, `gain = B / sqrt(B² + [share × (N + G)]²)` ; raccord C1 à réserve nulle.
- **Sur le manteau :** N et G gardent les enveloppes conservatrices de C, gradient 26 et courbure 512 du bruit, poids et bifurcations des bandes compris ; l’arrondi physique de 2 m borne les retournements.
- **Dans la roche large :** réserve à l’échelle de l’octave : N est amplitude × fréquence, G la pente de la sinusoïde finie, `2π × stripeScale × amplitude × fréquence`, affûtage compris. Garder les enveloppes de retournement à 2 m pour une incision kilométrique annulait ses bandes même à `Sc = tan(70°)`.
- **La portée de ce seuil rocheux :** pente caractéristique à l’échelle de l’octave, pas plafond de toutes les pentes locales après orientation ; des parois locales dépassent 70°, comme le bruit et les profils des vallées conservés. Le manteau garde son enveloppe conservatrice point par point.
- **Le mélange :** `share × lerp(gainSoil, gainRock, r)` remplace le seul motif ; il ne réduit pas le bruit ordinaire lorsque la réserve est épuisée. Gain et part rocheuse ne lisent pas la phase courante ; bruit et bande restent centrés séparément.
- **Le coût :** aucune lecture voisine de relief ni nouvelle octave pour le budget ; mêmes bandes, saturation scalaire. Coût GPU non mesuré, aucun banc lancé.

## Les falaises côtières

**L’abrasion suit un contour du sol complet, détail, vallées et dépôts inclus.**
- **Où :** `ErosionCoast`, après les dépôts et avant les cordons, avec `valleys = true` seulement.
- **Le rivage estimé borne la portée :** il ne place plus une paroi dans les montagnes.
- **Le contour :** `Hc = clamp(1000 W G, 8, 400)` m ; le sol au-dessus de `Hc + δ` reste identique.
- **La largeur W :** 1,2 km × exposition × érodabilité, au plus 3 km ; variation de 45 % par un bruit de 2,4 km (Sunamura 1992, force sur résistance).
- **La pente G :** norme tangentielle des grandes formes et des trois octaves du détail de plus de 9 km, avant la limitation des ravines des sols mobiles ; la pente côtière `coastSlope × shoreMetric / 1000` reste un plancher.
- **Pourquoi 9 km :** trois fois le recul maximal ; les octaves de 50, 23,7 et 11,2 km gardent les grands versants sans laisser les petits éperons déplacer Hc.
- **Une seule évaluation du relief :** `cliffSlope` vient du `ReliefDetail` principal et de ses trois octaves de plus de 9 km ; aucun recalcul ni lecture hors sphère pour figer Hc. Le paramètre de projection est retiré : les vallées se lisent toujours sur la sphère.
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
- **Le seul vent :** `ErosionWaveWind`, son jumeau CPU `erosion_wave_wind`, cube 1 du climat, est et nord en m/s, direction de déplacement.
- **La force relative :** 1 jusqu’à 5 m/s, linéaire vers 1,6 à 8 m/s, plafonnée ; les calmes s’éteignent continûment de 0 à 1 m/s. L’intervalle utile 1–1,6 garde la calibration précédente, sans conserver ses directions zonales.
- **Le repère :** est `(-d.z, 0, d.x)`, nord `cross(est, d)`, comme `Climate.cpp` ; aucune inversion du vent ni direction « venant de ».
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
| `WAVES` | `(0.28, 1.6)` | houle, force relative maximale à 8 m/s |

**Les contrôles actuels :** `python tools/cotes/verifie_falaises.py`, puis `python tools/hydro/verifie_cretes_climat.py --before fe22cfe9d6d96e9680ca44ef2fd5e47704467939`.
- **Les trois coupes fixes restent mesurées :** avec les caches intégrés, le port commité ne retrouve déjà que deux faces, dont une de plus de 100 m ; la troisième face historique est absente avant le raccord. Le contrôle compare les nombres avant/après sur ce même témoin, sans changer les limites physiques.
- **Les limites physiques restent sur le vent calculé :** abaissement au plus Hc + 1 m, aucun sol relevé, montagnes intactes, moins de 5 % de coupes enclavées et portée p99 sous 4 km.
- **Les anciennes tables :** [historique](log/spec-erosion-historique.md).

## Le drapeau `valleys`

**`ReliefElevation(p, true)` rend le relief érodé ; `(p, false)` la forme avant érosion,** sans aucun niveau, celle que le niveau 0 lit. Le niveau 0 ne lit jamais ses propres sorties.

## Les branchements

**Avec le climat :** `ErosionClimate` rend P en m/an, précipitations annuelles du cube 0 divisées par 1 000, et T annuelle au niveau de la mer en °C.
- **CPU :** `CreateTectonicMap` appelle `CreateClimateMap`, qui garde `mClimateCpu`, puis vient `CreateErosionMap` et `Erosion::Build` ; aucune boucle, le climat lit toujours la forme avant érosion.
- **GPU :** `ClimateAt` lit t20 ; les passes terrain, terrain fin, carte planétaire et placement gardent leur table t18–t23, avec le sampler linéaire s4 ; l’érosion reste t23.
- **Le portage :** `erosion_climate` et `erosion_wave_wind` lisent `cp.climate(p)`.
- **La ligne d’équilibre :** relation d’Ohmura, correction d’été fixe de 8 °C, gradient de 6,5 K/km et abaissement glaciaire de 900 m conservés ; pas de nouvelle formule ni de recalage de la part glaciée. La demi-amplitude calculée n’est pas utilisée ici.
- **La limite de mesure :** la part glaciée du nouveau réseau reste à mesurer au prochain démarrage autorisé ; le portage ne reconstruit pas le niveau 0.

**Avec le volcanisme :** ses édifices s'ajoutent à la forme avant érosion, `ReliefElevation(p, false)`. Le niveau 0 les voit s'ils dépassent 40 km ; plus petits, les ravines les découpent comme tout relief. `ReliefDetail` gagne deux paramètres, les ravines et la somme grossière.

**Avec l'eau, plus tard :** les fleuves se dessinent depuis le débit et le niveau de l'eau des liens, les lacs depuis leur niveau, les fjords et les estuaires où les vallées passent sous la mer.

## Le portage CPU

**`tools/hydro/cp.py` lit le niveau 0 du moteur,** `erosion-<graine>.bin`, et refait les vallées, les dépôts et les ravines ; les nœuds en float32, comme le shader. `EXOLUNE_EROSION` donne un autre chemin.

## Les mesures CPU des ravines rocheuses et des auges ouvertes, graine 0

**Références sur les mêmes caches :** intégration `fe22cfe`, D `1ca9743`, sources chargées directement par `git show` ; aucune reconstruction du niveau 0. Commande : `python tools/hydro/verifie_erosion_roche.py`, ou `--only windows`, `troughs`, `coasts`.

**Les chaînes vues de loin :** carrés de 5 × 5 km entre les bords, 201² points à 25 m, maille de 25 m ; gradient centré, différence à un côté sur le bord. Parts en pour cent.

| Lieu | Version | >35° | >45° | >60° |
|---|---|---:|---:|---:|
| −25,60 ; −26,94 | Intégration | 56,867 | 40,472 | 7,039 |
| | D | 45,595 | 26,715 | 0,196 |
| | E | 51,432 | 44,746 | 6,307 |
| −46,9 ; −33,8 | Intégration | 26,390 | 9,784 | 1,017 |
| | D | 5,745 | 0,183 | 0 |
| | E | 27,645 | 11,599 | 2,193 |

- **Même échantillonnage, maille de 5 m pour contrôle :** chaîne E 51,662 / 44,454 / 6,903 %, arêtes E 29,455 / 12,178 / 2,205 % ; crêtes fines davantage résolues.
- **La protection de C reste tenue :** dans les quatre carrés de 100 × 100 m à 1 m, zéro au-dessus de 45° et de 60°, avant et après E. Maxima D → E : forêt 30,648 → 31,358°, versant 22,577 → 20,052°, canyon 44,060 → 43,960°, plat 4,613 → 4,613°. Au-dessus de 35°, seul le canyon : 14,254 → 12,214 %.
- **La petite fenêtre d’arêtes reste locale :** sur 100 m à 1 m, E atteint 14,626 % au-dessus de 45°, zéro au-dessus de 60°, maximum 52,675° ; elle peut tomber sur un seul flanc d’une bande kilométrique. Le contrôle rocheux de E porte sur le carré de 5 km demandé, où les parois au-dessus de 60° sont présentes. Le bruit sans érosion reste comparé par `valleys=false` ; le sol sans ravines mais creusé peut changer avec la correction des vallées.
- **La moyenne des bandes reste nulle :** gain et part rocheuse indépendants de la phase courante ; mêmes profils centrés, même affûtage et même arrondi. Quadrature du profil : erreur sous 1,03·10⁻¹³ unité de bruit.

**Les auges :** carrés de 4 km, 161² points à 25 m ; inondation à huit voisins, bords ouverts, maille de 5 m. Premier centre à −25,545112988 ; −26,901313945, soit le décalage signalé de 2 325 m nord et 1 475 m est ; second à −25,486 ; −27,075.

| Zone | Fermeture du creusement grossier D → E | Fermeture du fond borné à l’eau D → E | Maximum sur tout le carré D → E |
|---|---:|---:|---:|
| Première auge | 72,964 → 0 m | 72,964 → 0 m | 72,964 → 57,498 m |
| Seconde auge | 441,570 → 0 m | 609,559 → 0 m | 681,453 → 65,790 m |

- **Les maxima restants sont hors creusement :** sol 3 067,853 m contre niveau d’eau 963,779 m pour le premier, 3 281,771 contre 1 225,714 m pour le second ; `coarse == cut`, `floorShare == 0`. Ils ne ferment pas les fonds des auges.
- **Les vrais thalwegs sont suivis vers l’aval :** courbe du lien, puis de ses receveurs ; inversion du gauchissement angulaire, erreur sous 3,4 nm. Parcours de 5 002 et 5 046 m, sans interpoler des hauteurs hors de la courbe ; CSV `x64/Release/erosion-e-thalweg-*.csv`.
- **Écart sol − eau, premier parcours :** D de 0 à +708,725 m à maille 5 m, 0 à +690,982 m à 200 m ; E zéro aux deux mailles. Creusement grossier E − eau : zéro aussi.
- **Second parcours :** D de +571,903 à +3 177,031 m à maille 5 m, +592,529 à +3 180,971 m à 200 m ; E zéro aux deux mailles, sol complet et grossier. Le niveau d’eau descend sur les deux parcours.
- **Les lacs du niveau 0 :** seize débouchés lacustres recevant un affluent ; niveau lu à leur nœud à moins de 0,000006 m de leur niveau stocké. Les cellules lacustres isolées n’ont pas de courbe de niveau 1 ; elles ne font pas partie de ce contrôle.

**Les falaises sans recalcul côtier :** comparaison avant/après suppression du bloc qui conservait Hc au bit près. Même port E et mêmes caches actuels pour les deux versions ; référence `x64/Release/cp-avant-simplification-cotes.py`, SHA256 `b89e84542c3826aea5656bdc73315e366479693d32a10496781f5941f4c3ed01`. Commande du relevé : `python x64/Release/mesure-simplification-cotes.py` ; sortie `verification-simplification-cotes.txt` dans le même dossier.

**Hc sur les six côtes, médiane / p90 / maximum en m :** carrés de 60 km, 201² points, maille de 10 m ; quantiles sur les points actifs de chaque version, comme `distribution` dans `verifie_falaises.py`.

| Centre | Avant | Après |
|---|---:|---:|
| 8,54005 ; −103,23344 | 212,071 / 378,526 / 400,000 | identique |
| −23,01696 ; 158,00809 | 70,800 / 109,075 / 119,508 | identique |
| −3,34285 ; 169,01181 | 80,218 / 180,002 / 255,085 | 81,427 / 181,618 / 343,741 |
| −51,89165 ; −40,94037 | 54,558 / 133,074 / 214,107 | identique à 0,001 m près |
| −8,11021 ; 131,04460 | 51,545 / 68,277 / 89,271 | 51,969 / 68,365 / 89,271 |
| 8,76166 ; −103,24998 | 170,834 / 345,453 / 400,000 | identique |

- **La variation principale :** maximum de la troisième fenêtre +88,657 m ; médiane +1,209 m, p90 +1,616 m. Le plafond reste 400 m ; le maximum ne doit pas être décrit comme une petite variation.
- **Le sol avant abrasion est identique au bit près** dans les six carrés ; seuls la pente fournie à Hc et le résultat des vagues changent.

**Les trois coupes fixes :** avant = après aux précisions indiquées ; angle à pas de 10 m, platier adjacent à la face, terre au-dessus de +5 m jusqu’à la mer originale.

| Coupe, latitude ; longitude | Paroi | Angle | Platier | Terre devant |
|---|---:|---:|---:|---:|
| 8,72580 ; −103,29430 | 377,816 m | 84,91° | −1,412 m | 0 m |
| −23,18981 ; 157,86949 | 41,877 m | 72,47° | −1,099 m | 0 m |
| −3,21302 ; 169,26372 | 42,519 m | 75,64° | −1,540 m | 0 m |

**Les trois fenêtres de contrôle, graine 0 :** carrés de 10 km, 201² points à 50 m ; avant = après aux précisions indiquées.

| Centre | Part enclavée avant → après | Portée marine p99 avant = après |
|---|---:|---:|
| 8,73276 ; −103,30263 | 0 → 0 % | 1 138,519 m |
| −23,18173 ; 157,88952 | 0 → 0 % | 400,031 m |
| −3,21302 ; 169,26372 | 0 → 0 % | 683,482 m |

- **Aucune cible des falaises n’échoue :** trois faces actives, dont une de plus de 100 m, avant et après ; aucun seuil terrestre devant leur pied, aucune coupe enclavée dans ces trois fenêtres, p99 sous 4 km, abaissement sous Hc + 1 m. Le contrôle complet `python tools/cotes/verifie_falaises.py` affiche aussi `ok`.
- **Les ressources :** une requête `ErosionValleys`, toujours sur la sphère, et le seul `ReliefDetail` principal pour `cliffSlope` ; paramètres `sphere` / `project` retirés. Aucun gain de temps GPU annoncé sans mesure.
- **Le jugement en vol :** `tools/tests/2026-10-31-cotes-sans-recalcul.txt`, sans lancement automatique ; le parcours E des chaînes reste valable.

- **`valleys=false` :** identique au bit près sur 288 points × trois mailles, graines 0 et 1. Côte plate, 441 points à 16,71 ; −89,28 : écart nul.
- **Vérifications de la simplification :** `cp.py`, comparaison avant/après et contrôle complet des falaises affichent `ok` ; Release x64 sans erreur ni nouvel avertissement dans les fichiers modifiés (`verification-build-simplification-cotes.txt`). L’ancienne assertion d’identité de Hc est retirée ; les limites physiques restent testées.
- **Limites :** ni moteur ni banc lancé ; le retour en vol reste nécessaire, `tools/tests/2026-10-31-ravines-roche-auges.txt`. Les caches ne sont pas réécrits.

## Les défauts connus

- **Les sols de C sont gardés ; les grandes bandes rocheuses sont rétablies dans les deux fenêtres :** séparation par longueur d’onde et par roche ; formes et neige à juger en vol. Le seuil rocheux porte sur la pente à l’échelle de l’octave, sans plafonner chaque pente locale.
- **Les fermetures des deux auges testées sont retirées :** distance prise sur la sphère, fonds et thalwegs au niveau d’eau ; les creux de versant hors creusement subsistent. L’eau des fleuves et des lacs n’est pas encore rendue.
- **Les vallées du niveau 0 restent trop régulières vues de près :** des versants plans à pente constante, des auges aux fonds plats et aux parois en falaise, comme taillées ; les versants convexes en haut, concaves en bas, et les éperons tronqués sont à faire.
- **Les deltas sont petits, et l'un d'eux faux :** 5 km au plus, la portée des nœuds lus ; à l'embouchure du plus grand fleuve, -7,8°, 27,2°, une langue de dépôt isolée au large, cause non trouvée, et un pan de côte aux bords droits, qui ne vient pas des dépôts. Les grands deltas demandent un champ des dépôts lu en B-spline.
- **Les ravines peuvent se voir peu de loin :** leur amplitude est désormais bornée par le sol porteur ; les deux octaves de plus de 20 km gardent leurs crêtes orientées le long des chaînes.
- **Le coût actuel reste à mesurer sur demande :** le recalcul côtier de E est retiré ; aucun banc lancé.
- **Les fleuves des flancs restent parallèles et droits sur 50 à 100 km,** sur les pentes régulières : la forme avant érosion filtrée à 40 km n'y a pas de relief qui les dévie.
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

- Selby, *A rock mass strength classification for geomorphic purposes: with tests from Antarctica and New Zealand*, Zeitschrift für Geomorphologie 24(1), 31–51, 1980 ; Augustinus, *The influence of rock mass strength on the form and evolution of deglaciated valley slopes in the English Lake District*, Scottish Journal of Geology 38(1), 15–20, 2002.
- Grieve, Mudd, Hurst, *How long is a hillslope?*, Earth Surface Processes and Landforms 41(8), 1039–1054, 2016, DOI `10.1002/esp.3884`.
- Roering, Kirchner, Dietrich, *Evidence for nonlinear, diffusive sediment transport on hillslopes and implications for landscape morphology*, Water Resources Research 35(3), 853–870, 1999, DOI `10.1029/1998WR900090`.
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
| 3 ter | Arêtes sans cuspide, pluie, température et vent calculés ; clé du cache climatique | fait et rendu validé par l’utilisateur le 2026-10-31 ; nouveau réseau livré |
| 3 quater | Ravines à pente critique, moyenne nulle et bruit porteur conservé | sols validés par l’utilisateur ; arêtes reprises par E |
| 3 quinquies | Fonds raccordés à l’eau, borne rocheuse à 70° | fait dans D ; limites reprises par E |
| 3 sexies | Ravines selon roche et échelle ; directions gauchies sur la sphère | code et contrôles CPU faits ; jugement en vol à faire |
| 4 | Les versants : profils convexes-concaves, éperons tronqués des auges | à faire |
| 5 | Les grands deltas, par un champ des dépôts | à faire |
| 6 | L'eau des fleuves et des lacs, depuis le même réseau | à faire, avec la mer |
