# Spec : l'érosion globale

Statut : spec vivante, depuis le 2026-10-31, branche `erosion-globale`, piste `piste/erosion-globale`. Elle part de la pile tectonique (`spec-relief-tectonique.md`) ; la recherche de la branche `erosion-niveaux` n'est qu'une source (section « Ce que la recherche a appris »). Parcours courant : `tools/tests/2026-10-31-fonds-vallees.txt` ; les étapes précédentes restent dans `tools/tests/2026-10-31-erosion.txt`.

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

**Le budget de pente, `ReliefGullyGain` :**
- **Le seuil des sols mobiles :** `EROSION_GULLY_CRITICAL = 1,25`, environ 51,3° ; valeur de travail issue de MR1, `1,25 ± 0,10`, [Roering, Kirchner et Dietrich 1999](https://seismo.berkeley.edu/~kirchner/reprints/1999_29_Roering_nonlinear.pdf), §5.2 et tableau 1. Leur transport croît sans borne à l’approche de ce seuil ; ce n’est pas l’angle de repos de grains sans cohésion.
- **Le seuil rocheux :** `Sc = lerp(1,25, tan(70°), gullies.glacial)`, `EROSION_GULLY_ROCK = 2,74747742` ; seule la bande de ligne d’équilibre, jamais `valley.glacier`. Selby 1980 relie la pente rocheuse à la résistance du massif ; 70° est notre choix pour la roche forte, dans la plage 60–80° signalée, pas un seuil universel de l’article. Le [travail de terrain d’Augustinus 2002](https://pubs.geoscienceworld.org/gsl/sjg/article-abstract/38/1/15/114650/The-influence-of-rock-mass-strength-on-the-form) reprend cet équilibre de résistance sur des versants déglacés. Le bruit ordinaire, les profils des vallées et les falaises ne changent pas de loi.
- **D’abord la place du bruit ordinaire :** `s` est la pente des octaves au-dessus, `N` une enveloppe de celle de l’octave ordinaire ; `L = max(Sc − s − N, 0)` et `B = L² / Sc`. Le carré raccorde la réserve à zéro avec une dérivée nulle.
- **Puis le remplacement seul :** `D = share × (N + G)`, `gain = B / sqrt(B² + D²)` ; le motif est mêlé au bruit pour `share × gain`, sans écrêter une hauteur. Sa pente supplémentaire est au plus B, B au plus L ; réserve épuisée, le bruit ordinaire reste entier.
- **G couvre les bandes et leur orientation :** période de l’onde, poids quintiques des huit coins et normalisation près des bifurcations ; la rotation de la direction suit l’enveloppe de courbure des octaves au-dessus, divisée par leur pente. Limiter la seule pente nominale de la sinusoïde ne suffisait pas.
- **Les enveloppes du bruit quintique :** 26 pour son gradient, 512 pour sa courbure en unités de maille ; des majorants conservateurs depuis les coins unitaires et les dérivées des poids, pas des réglages par lieu. La courbure des crêtes arrondies utilise le plancher physique de 2 m et la géologie ; jamais la maille courante, ni le poids de filtrage de l’octave.
- **La moyenne :** bruit et bande sont centrés séparément avant le remplacement ; pour les crêtes des bandes, moyenne exacte de la sinusoïde arrondie, affûtage compris. Le gain dépend des formes porteuses, pas de la phase de l’octave courante.
- **Le coût :** aucune lecture voisine de terrain ni de carte ; un budget épuisé saute le calcul du motif, sauf l’octave côtière de calibration. Aucun banc GPU lancé.

## Les falaises côtières

**L’abrasion suit un contour du sol complet, détail, vallées et dépôts inclus.**
- **Où :** `ErosionCoast`, après les dépôts et avant les cordons, avec `valleys = true` seulement.
- **Le rivage estimé borne la portée :** il ne place plus une paroi dans les montagnes.
- **Le contour :** `Hc = clamp(1000 W G, 8, 400)` m ; le sol au-dessus de `Hc + δ` reste identique.
- **La largeur W :** 1,2 km × exposition × érodabilité, au plus 3 km ; variation de 45 % par un bruit de 2,4 km (Sunamura 1992, force sur résistance).
- **La pente G :** norme tangentielle des grandes formes et des trois octaves du détail de plus de 9 km, avant la limitation des ravines des sols mobiles ; la pente côtière `coastSlope × shoreMetric / 1000` reste un plancher.
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

## Les mesures CPU des fonds et de la borne rocheuse, graine 0

**Même réseau actuel avant/après D, fourni par le moteur lancé par l’utilisateur.** Aucun moteur ni banc lancé ici ; le portage ne reconstruit pas le niveau 0.
- **La référence :** `x64/Release/cp-avant-fonds.py`, SHA256 `e8e551b5df2a62e8caaec981be4fb1289f8a07c424d9665bc800c70987a2f3e4` ; mesures C et références antérieures dans [l’historique](log/spec-erosion-historique.md).
- **Les commandes :** `python tools/hydro/verifie_fonds_vallees.py` ; `python tools/hydro/verifie_pentes_ravines.py --before-file x64/Release/cp-avant-fonds.py`.
- **L’inondation :** carré de 4 km entre les bords, 161² points, pas de 25 m, huit voisins, bords ouverts. Premier carré centré 2 325 m au nord et 1 475 m à l’est de −25,566 ; −26,916 ; second centré sur −25,486 ; −27,075. Maille du portage de 5 m.

| Zone | Profondeur fermée maximale du carré, avant → après | Au point le plus profond avant, avant → après | Carré de 10 km sous son niveau d’eau de plus de 5 m, avant → après |
|---|---:|---:|---:|
| Première auge | 77,010 → 72,964 m | 77,010 → 48,373 m | 0,450936 → 0 % |
| Seconde auge | 734,793 → 681,453 m | 734,793 → 579,469 m | 0,666601 → 0,058818 % |

- **Le premier fond :** au point de profondeur maximale avant, sol 992,265 → 1 021,138 m, son niveau d’eau. Au point décalé donné dans le signalement, sol 1 049,607 → 1 036,022 m, son niveau ; profondeur fermée 19,668 → 33,489 m. Le maximum résiduel du carré, 72,964 m, existe aussi dans le sol grossier creusé sans détail.
- **Le second fond :** au point de profondeur maximale avant, sol 1 060,705 → 1 216,029 m, son niveau d’eau. La fermeture du carré n’est pas supprimée : le sol grossier creusé seul, sans aucun détail, contient déjà une cuvette de 441,570 m. Cause de cette cuvette du réseau actuel à rechercher ; elle ne vient pas du seul détail résiduel.
- **Les plateaux réellement bornés à l’eau :** 4 592 et 2 764 points ; écarts sol − eau de [−67,036 ; +191,015] m et [−155,324 ; +164,339] m avant, zéro après. Les traces des thalwegs prennent le profil grossier le plus profond de chaque coupe, sans sélectionner sur la hauteur fine : 72 et 50 points ; écarts [−15,521 ; +58,883] m et [−39,522 ; +88,158] m avant, zéro après. CSV dans `x64/Release/thalweg-*-*.csv`.
- **Les carrés de 10 km :** 101² points à 100 m, centrés sur les deux coordonnées signalées. Sous le niveau de plus de 5 m parmi les points à `floorShare > 0` : 0,137241 → 0 % et 0,313695 → 0 %. Le déficit résiduel de 64,863 m de la seconde fenêtre est hors de ce masque.
- **La cuvette initiale de 84 m n’est pas reproduite avec le nouveau réseau :** ne pas confondre les mesures d’intégration avant A–C avec cette référence avant D.
- **Hors creusement :** correction des fonds isolée de la borne rocheuse, 6 172 et 7 234 points des deux carrés de 10 km identiques au bit près.

**Les fenêtres C :** 100 × 100 m entre les bords, 101² points à 1 m ; différences centrées, à un côté sur le bord.

| Lieu | >35°, avant → après | >45°, avant → après | >60°, avant → après | Maximum, avant → après |
|---|---:|---:|---:|---:|
| Forêt, 34,1611352 ; −73,72443 | 0 → 0 % | 0 → 0 % | 0 → 0 % | 30,647836 → 30,647798° |
| Versant, −48,3497 ; −44,8221 | 0 → 0 % | 0 → 0 % | 0 → 0 % | 22,577514 → 22,577126° |
| Canyon, −38,1080 ; 166,4916 | 14,253505 → 14,253505 % | 0 → 0 % | 0 → 0 % | 44,060265 → 44,060258° |
| Plat, 44,16 ; −60,08 | 0 → 0 % | 0 → 0 % | 0 → 0 % | 4,613229 → 4,613229° |
| Arêtes, −46,9 ; −33,8 | 31,947848 → 31,947848 % | 0,862661 → 0,862661 % | 0 → 0 % | 47,432335 → 47,432339° |

- **Le seuil rocheux ne suffit pas à restaurer les parois :** tan(70°) est bien appliqué, mais l’enveloppe conservatrice de C limite encore le motif à 0,255 mm dans la fenêtre d’arêtes. Le retour de parois au-dessus de 60° reste non obtenu ; il faudra resserrer les enveloppes de pente et de rotation, sans enlever la protection des sols.
- **Les sols restent comme en C :** zéro au-dessus de 45° dans les quatre témoins ; le canyon avant érosion reste à 1,499853 %. Le raccord des fonds ne change pas leurs bruits sans ravines, identiques au bit près.
- **Transects nord, 0 à 25 m à 0,25 m :** forêt, pente 17,267267 → 17,267291°, montée et variation absolue sur 0,5 m 0,155405864 → 0,155406092 m ; versant, 13,486420 → 13,485948°, 0,119753109 → 0,119749038 m pour les deux variations.
- **Indépendance de la maille :** cinq fenêtres identiques au bit près entre des mailles résolues de 0,25 et 1 m.

**Hc médiane / p90 / maximum :** mêmes six carrés de 60 km, 201² points ; mêmes points actifs avant/après D. Écart de champ nul partout.

| Centre | Hc avant = après, m |
|---|---:|
| 8,54005 ; −103,23344 | 203,744 / 382,981 / 400,000 |
| −23,01696 ; 158,00809 | 67,239 / 109,075 / 126,281 |
| −3,34285 ; 169,01181 | 82,142 / 175,291 / 218,965 |
| −51,89165 ; −40,94037 | 54,649 / 137,112 / 214,107 |
| −8,11021 ; 131,04460 | 50,437 / 71,033 / 89,271 |
| 8,76166 ; −103,24998 | 171,101 / 345,552 / 400,000 |

- **`valleys=false` :** 288 points × trois mailles, graines 0 et 1, identiques au bit près.
- **Côte plate :** 441 points du carré de 10 km à 16,71 ; −89,28, identiques au bit près ; le témoin plat C aussi.
- **Contrôles :** `cp.py`, falaises, contrôle analytique du budget et raccord des fonds affichent `ok`. Le contrôle des fenêtres échoue désormais explicitement sur les parois d’arêtes au-dessus de 60°, non restaurées ; les fermetures grossières restent mesurées, sans être déclarées corrigées.
- **Compilation :** Release x64 par `tools/lance.ps1 -Build -NoLaunch`, zéro erreur, aucun nouvel avertissement dans les fichiers modifiés ; avertissements restants dans les fichiers inchangés `Materials`, `Mesh`, `OceanSurface`, `PixelShader` et `PlanetFoliageMeshPixel`. Résultats dans `x64/Release/verification-build-fonds-final.txt`.
- **Jugement en vol :** `tools/tests/2026-10-31-fonds-vallees.txt`, sans lancement automatique.

## Les défauts connus

- **Le détail ne creuse plus sous le plateau borné à l’eau dans les deux auges testées :** le masque du fond initial seul ne couvrait pas tout ce plateau. Les deux zones gardent une fermeture, déjà présente dans le sol grossier creusé ; leur cause reste à expliquer. Des creux subsistent hors de ce plateau et du masque du fond.
- **Les sols de C sont gardés après retour utilisateur ; les arêtes restent trop atténuées :** activation par la ligne d’équilibre seule et arrondi sans cuspide gardés ; le seuil rocheux de 70° ne surmonte pas l’enveloppe trop prudente. Restauration des parois non obtenue.
- **Le budget de pente est conservateur :** il peut retirer presque tout le motif des ravines sur un relief dont le bruit occupe déjà la réserve ; la visibilité des ravines sur toute la planète reste à juger en vol.
- **Les vallées du niveau 0 restent trop régulières vues de près :** des versants plans à pente constante, des auges aux fonds plats et aux parois en falaise, comme taillées ; les versants convexes en haut, concaves en bas, et les éperons tronqués sont à faire.
- **Les deltas sont petits, et l'un d'eux faux :** 5 km au plus, la portée des nœuds lus ; à l'embouchure du plus grand fleuve, -7,8°, 27,2°, une langue de dépôt isolée au large, cause non trouvée, et un pan de côte aux bords droits, qui ne vient pas des dépôts. Les grands deltas demandent un champ des dépôts lu en B-spline.
- **Les ravines peuvent se voir peu de loin :** leur amplitude est désormais bornée par le sol porteur ; les deux octaves de plus de 20 km gardent leurs crêtes orientées le long des chaînes.
- **Le coût du calcul du terrain dépasse un peu le budget :** +0,65 ms au plus, à l'orbite et au ras du sol.
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
| 3 quater | Ravines à pente critique, moyenne nulle et bruit porteur conservé | sols validés par l’utilisateur ; arêtes trop atténuées |
| 3 quinquies | Fonds raccordés à l’eau, borne rocheuse à 70° | code et mesures CPU faits ; fermetures grossières et parois d’arêtes restent non résolues |
| 4 | Les versants : profils convexes-concaves, éperons tronqués des auges | à faire |
| 5 | Les grands deltas, par un champ des dépôts | à faire |
| 6 | L'eau des fleuves et des lacs, depuis le même réseau | à faire, avec la mer |
