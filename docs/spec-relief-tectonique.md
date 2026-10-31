# Spec : le relief tectonique

Statut : spec vivante, depuis le 2026-10-31. Étapes 0 à 3 faites le 2026-10-31 sur la branche `bruit-propre`, non commitées ; leurs défauts corrigés le même jour, seconde passe : côtes, rifts, chaînes, budget du démarrage, entrées du niveau 0. À juger en vol : `tools/tests/2026-10-31-relief-tectonique.txt`. **C'est le relief du jeu,** sans variable : `Relief.hlsli` ne garde rien de la composition héritée de complexplanet. L'ancien relief est au commit `f00004d`. Tout vient de `recherche-relief.md` : l'état de l'art, les licences, les sources. Les versions dépassées : `log/spec-relief-tectonique-historique.md`.

## L'objectif

**Le relief part d'une carte tectonique calculée au démarrage, pas d'un bruit.** Le bruit ne fait plus que le détail, sous 50 km, modulé par la géologie.

- **Pourquoi :** l'ancien relief n'avait aucune structure qui s'accorde avec l'eau ; 41 % des terres en cuvettes, des fleuves qui traversent les massifs (`recherche-relief.md`, section 3).
- **Le modèle suivi :** la structure globale se calcule une fois, hors du rendu ; le rendu l'évalue point par point et y ajoute du bruit. Personne ne simule les plaques par image.

## Les contraintes

- **Aucune limite de vitesse :** on passe d'un point à un autre de la planète, ou d'une planète à une autre, en une seule image. Rien ne se calcule en route ni en arrière-plan.
- **Le périmètre est un système solaire :** les cartes de toutes ses planètes et lunes se calculent au démarrage, une fois par graine.
- **Une carte porte de la géométrie à trois conditions :** données fixes par graine, lues de façon continue, au-dessus de deux de leurs cellules (`principes.md`).
- **Du code original :** aucune ligne des projets listés par la recherche, même sous MIT (`recherche-relief.md`, section 5).

## L'architecture, en quatre couches

| Couche | Échelles | Où, quand | Statut |
|---|---|---|---|
| 1. Carte tectonique | plaques de 1 000 à 10 000 km ; champs à 20 km | CPU, au démarrage, moins de 1 s, 38 Mo sur le GPU | faite, corrigée le 2026-10-31 |
| 2. Grandes formes | 6 000 km à 50 km ; les côtes jusqu'à 3 km | carte et profils analytiques, par sommet | faite le 2026-10-31 |
| 3. Détail | 50 km à 13,5 m | bruit de `Noise.hlsli` modulé par la carte, par sommet | fait le 2026-10-31 |
| 4. Niveau 0 | au-dessus de 20 à 40 km | au démarrage | entrées prêtes ; le branchement à faire, branche `erosion-niveaux` |

## La carte tectonique, `Tectonics.cpp`

**Une carte par corps céleste :** `Tectonics::Build({ seed, radiusKm })`. Le même exécutable et le même corps donnent le même fichier, au bit près. La planète prend `PLANET_SEED`.

**Le calcul :**
1. **La grille :** le cube de la planète, 6 × N², N la puissance de deux qui donne des texels de 20 km environ. Pour la planète, 512².
2. **Les bruits :** des fBm de bruit de gradient, de 3 000 à 60 km, chacun ramené à un écart-type de 1.
3. **Les continents, par lieu :** un fBm de la taille des continents, gauchi, seuillé à la part tirée, 40 à 44 % de croûte continentale, comme la Terre avec ses plateaux (Cogley 1984). Les taches de moins de 40 cellules rejoignent la croûte qui les entoure.
4. **Les plaques :** 12 à 20 germes, chacun le plus éloigné des autres parmi 24 tirés ; une croissance concurrente à coût bruité, ralentie quatre fois sur deux cellules de part et d'autre des côtes, où des frontières s'arrêtent. Des plaques de 0,3 à 22 % de la surface ; 18 sur 19 portent continent et océan, graine 0.
5. **Les mouvements :** un pôle d'Euler tiré ; 40 à 100 mm/an à 90° du pôle sur une plaque océanique, 10 à 40 sur une continentale, entre les deux selon sa part de continent.
6. **Les frontières :** toute cellule voisine d'une autre plaque ; leurs points lissés le long d'elles, sur les deux bords. La vitesse relative projetée sur la normale ; elle et la croûte de chaque bord moyennées le long de la frontière sur 100 km environ.
   - **transformante** si la composante normale fait moins de 40 % de la vitesse relative ;
   - **convergente,** par la croûte locale : subduction sous un continent, sous un océan, collision de deux continents ;
   - **divergente :** rift entre deux continents, dorsale sinon.
7. **La polarité, par paire de plaques là où elles convergent :** l'océanique sous la continentale ; de deux océaniques, la croûte la plus vieille ; de deux continents, celui qui avance le plus dans l'autre.
8. **Les marges actives :** un océan de moins de 700 km entre un front que sa plaque chevauche et un continent de cette plaque est consumé ; le continent atteint la fosse, comme sous les Andes. Plus loin, l'arc reste en mer, une mer marginale derrière lui, comme le Japon.
   - **Les rifts qui ont rompu leur continent :** un rift s'ouvre depuis 1 à 3 Ma, tirés par paire de plaques ; sa largeur est sa divergence fois ce temps. Au-delà de 50 km, la croûte y devient océanique, plus jeune vers l'axe : une mer étroite comme la mer Rouge, 300 km au plus, une dorsale en son milieu, deux marges jeunes. En deçà, il reste une vallée de rift.
   - **Puis les étapes 6 et 7 de nouveau.**
9. **Les familles des profils, par le signe du mouvement, pas par le type :** chevauchante, plongeante, collision, rift, dorsale. Une frontière oblique lève encore sa chaîne. Le mouvement de chaque famille est lissé le long de la frontière sur 200 km, les autres familles comptant 0 : il tombe à 0 aux extrémités, où chaînes et fosses s'effilent.
10. **L'âge du fond océanique :** la distance à la dorsale de la plaque, sur la demi-vitesse d'expansion de la plaque ; sans dorsale, la plus proche ailleurs, sur la vitesse moyenne ; 200 Ma au plus.
11. **Les sutures anciennes :** les continents d'avant les plaques découpés en cratons, un par 2 % de la surface, leurs germes tirés à part ; une suture entre deux cratons, de 100 à 1 000 Ma.
12. **Les distances :** une propagation du germe le plus proche par source ; à toutes les frontières, à chaque famille dans sa plaque, au bord des continents, aux sutures. Chacune s'arrête à la portée de ce qu'elle façonne : 1 500 km pour les frontières et les familles, 2 000 km pour le bord des continents, 1 000 km pour les sutures.

**Les champs par cellule,** puis lissés sur deux texels : les grandes formes, l'amplitude et le caractère du détail, les profils vifs, les classes (la section suivante) ; le soulèvement et l'érodabilité, pour le niveau 0.

**Le budget, moins de 1 s par planète :**
- **Les propagations sur des seaux d'un quart de texel,** l'ordre de Dijkstra à un quart de texel près, sans tas ; les voisins déjà plus proches écartés d'une comparaison.
- **Ce qui ne dépend pas l'un de l'autre en même temps :** les variations régionales et les cratons sur un fil pendant que les plaques croissent ; le bord des continents pendant le second classement ; les dernières propagations ensemble, une par fil.
- **Les tours le long des frontières sur huit fils** tenus ensemble d'un tour à l'autre ; les lissages de tous les champs dans les mêmes passes.
- **Ce qui dépasse 300 km sur un cube de demi-résolution,** lu en bilinéaire continu entre les faces : le gauchissement des continents, les premières octaves de leur potentiel et du coût des fronts, les variations régionales.
- **L'âge pour la polarité,** aux seules frontières, par une recherche parmi les dorsales ; son champ entier avec les dernières propagations.

**Le stockage, `Tectonics.hlsli` :** un tableau de textures RGBA16F, `t18`, trois tranches par face, 520² texels ; un second à un quart de la résolution, `t19`, une tranche par face, 130² texels, pour les vues. 38 Mo sur le GPU.
- **tranche 0 :** l'altitude des grandes formes (m) ; le relief du détail (m) ; sa jeunesse, 1 sur une chaîne jeune ; les strates, > 0 en couches horizontales sur une plate-forme, < 0 en sédiments tendres.
- **tranche 1 :** la distance à la frontière de la plaque (km) ; la profondeur d'une fosse, le relief axial d'une dorsale ou d'un rift, le creux d'une transformante (m).
- **tranche 2 :** la distance signée par l'ordre des plaques, à 300 km au plus, exacte à travers la frontière pour ses profils ; la distance à la frontière lissée sur 40 km, le long de laquelle s'étirent les chaînes ; la roche et la plaque, en classes.
- **tranche 3, pour les vues, au quart de la résolution :** l'âge du fond (Ma), la distance au bord des continents (km), 2 000 au plus, le soulèvement (mm/an), la distance aux sutures (km).
- **tranche 4, dans le fichier seulement, pour le niveau 0 :** l'érodabilité de la roche ; le fichier garde aussi la tranche 3 à pleine résolution.

**La lecture, continue entre les faces :**
- **Chaque face a une bordure de 4 texels,** le champ au-delà de son arête, interpolé sur la face voisine. Une B-spline cubique, 4 × 4 lectures, lit une face seule.
- **Près d'une arête, les faces se mêlent** sur 1,5 texel, par des poids qui ne dépendent que du point. Mesuré sur le portage, aucun saut ni coude aux arêtes et aux coins.
- **La position dans le texel en doubles :** 1/m en float, affiné par un pas de Newton en doubles ; le point se lit au millimètre près.
- **Pas de lecture filtrée par le matériel :** ses poids n'ont que 8 bits, la carte marcherait par pas de 80 m.

**Les vues de diagnostic,** par `MYPLANETENGINE_VIEW` ou en fin de place d'une ligne de test, sans lumière ni air :

| Nom | Ce qu'elle montre |
|---|---|
| `plates` | chaque plaque sa couleur, assombrie sur la croûte océanique ; les frontières en noir, le bord des continents en blanc |
| `boundaries` | le type de la frontière la plus proche sur 250 km ; deux fois plus sombre sur la plaque qui plonge ; les sutures en brun |
| `boundarydist` | la distance au bord des continents jusqu'à 2 000 km, orange sur la croûte continentale, bleue sur l'océanique |
| `crustage` | l'âge du fond, rouge aux dorsales à violet à 200 Ma ; les vieilles chaînes en brun |
| `rocktype` | croûte océanique, volcanique, plissée jeune, sédiments, plissée ancienne, socle |
| `uplift` | le soulèvement du niveau 0, orange jusqu'à +6 mm/an, bleu jusqu'à −6 |
| `relief` | le relief en teintes hypsométriques et au soleil, le fond de la mer compris, l'eau retirée, exagéré avec la taille du pixel |

## Les grandes formes, étape 2

**La carte donne les formes de plus de 50 km ; le shader y pose les profils vifs sur ses distances.** Tout est lu à un point gauchi par un bruit de 800 à 25 km, 30 km d'écart, pour qu'aucune forme ne paraisse dessinée. Les montées des chaînes, arcs et épaulements se combinent en maximum lissé, (Σ u⁴)^¼ : jamais leur somme.

| Forme | Où | Profil | Source |
|---|---|---|---|
| Croûte océanique | partout en mer | GDH1 : −(2 600 + 365 √t) avant 20 Ma, −(5 651 − 2 473 e^(−0,0278 t)) après ; moins la charge des sédiments, 800 (1 − e^(−t/60)) ; ±400 m de houle à grande échelle | Stein et Stein 1992 |
| Marge passive | bord des continents | talus de −3 300 m au pied à −140 m en 70 km ; plateau de 50 à 250 km jusqu'à la côte ; plaine côtière vers l'intérieur, 280 ± 220 m | Kennett, *Marine Geology* ; Cogley 1984 |
| Marge active | sous une subduction | talus de 35 km, plateau de 12 km, rupture à −250 m | idem |
| Marge jeune | au bord d'une mer étroite | celle d'une marge active, son pied à −1 800 m ; des épaulements de 1,1 km à 40 km de la côte | la mer Rouge |
| Fosse | front de subduction | 2,1 à 4,3 km sous la plaine, demi-largeur 22 km, fond arrondi sur 6 km ; segments de 120 km, ±25 % | Stern 2002 |
| Bourrelet externe | plaque plongeante | +380 m à 150 km du front | Turcotte et Schubert, *Geodynamics*, 3.17 |
| Cordillère | chevauchante continentale | 1,4 à 3,2 km de moyenne, ±20 %, de 90 à 400 km de la fosse, 150 à 400 km de large ; arc volcanique sur sa crête | Stern 2002 |
| Arc insulaire | chevauchante océanique | +3,3 à 4,2 km à 175 km du front, des îles par le détail | Stern 2002 |
| Chaîne de collision | deux continents | 1,7 à 3 km de moyenne sur 170 à 210 km de part et d'autre | — |
| Plateau d'arrière-pays | chevauchante, convergence > 15 mm/an | jusqu'à 4,6 km, sur 150 à 800 km (le Tibet) | — |
| Bassin d'avant-pays | plongeante d'une collision | −450 m à 240 km du front, sédiments tendres | Turcotte et Schubert |
| Rift | divergence lente entre continents | un dôme thermique de 1,2 km sur 400 km ; épaulements de 1,1 km à 55 km ; graben de 25 km de demi-largeur, 0,5 à 0,8 km, murs de 5 km : un fond émergé | le rift est-africain |
| Mer étroite | rift ouvert de plus de 50 km | croûte jeune relevée de 1 km, chaude et comblée : 2 à 3 km de fond ; une dorsale lente en son milieu, sa vallée axiale de moitié ; deux marges jeunes | la mer Rouge |
| Dorsale | divergence en mer | la croûte jeune ; vallée axiale de 1,6 km sur une dorsale lente, dôme de 350 m sur une rapide, 10 km de demi-largeur, par segments | Macdonald 1982 |
| Faille transformante | cisaillement dominant | creux de 1,2 km en mer, 600 m sur un continent | — |
| Vieille chaîne | sutures | 2 600 e^(−âge/250 Ma) : 750 m de moyenne à 300 Ma | les Appalaches, l'Oural |
| Craton | loin des frontières | 280 ± 220 m, ±150 m de collines sur le socle | — |

**Tout profil a une largeur d'au moins deux mailles :** plus large, sa profondeur baisse d'autant, sa moyenne reste.

## Les côtes

**Près du rivage, le niveau bouge d'un bruit, filtré par la maille, de sorte que la côte se déplace d'une distance donnée.** Son amplitude est la pente des grandes formes fois ce déplacement (`principes.md`) : une côte se découpe autant sur une plaine plate que contre une cordillère.
- **Où :** à moins de 40 km du rivage le long de la pente, et de 300 m du niveau de la mer ; la pente lue sur la B-spline de la carte.
- **Le type de côte, par cette pente :** plate sous 2 m/km, une marge passive ; raide au-dessus de 8 m/km, une marge active ou jeune.
- **Le bruit :** cinq octaves de 60 à 3 km, lacunarité 2,2 ; chacune 0,62 de la précédente sur une côte plate, 0,7 sur une raide, plus découpée. Les octaves fines en partie en vallées noyées, |n| moins sa moyenne, des sillons étroits le long des zéros du bruit : des rias et des estuaires, 60 % sur une côte raide, 35 % sur une plate.
- **Le déplacement :** 12 km à un écart-type sur une côte raide, 8 sur une plate. Des caps, des baies, des îles près des côtes raides.
- **Les côtes plates, des cordons :** sur la moitié d'entre elles, par taches de 400 km.
  - **Le long du rivage lissé,** pas du contour du rivage : les grandes formes, les trois plus larges octaves du bruit des côtes, leurs rias arrondies sur un demi-écart, et les trois du détail. Les octaves fines découpent la côte derrière la lagune.
  - **Des îles en arcs entre des passes,** les zéros d'un bruit de 15 km : à 2,5 km au large au milieu, à 1 km près des passes, où leurs pointes se recourbent et s'effilent.
  - **Leur profil :** 3 m au-dessus de la mer, ±40 % selon des dunes de 4 km, plus bas aux pointes ; 0,6 km de demi-largeur au milieu, 0,36 aux pointes ; une plage lisse côté mer ; derrière les dunes basses, des cônes de débordement dans la lagune, au tiers de la crête et trois fois plus larges.
  - **Relevés depuis le relief sous eux, leur crête entière.** Jamais sur la terre émergée, effacés sur son premier demi-mètre.
  - **La partie émergée porte sur deux mailles au moins, ou reste noyée.** `ReliefSeaProfile` redistribue le sommet dans un cœur plat à raccord gaussien, sans changer l'aire du profil, débordements compris ; assez résolu, le profil reste identique.
  - **La même règle couvre leurs pointes recourbées et leurs débordements.** Aucun autre profil distinct de flèche, platier ou motu volcanique n'existe dans le relief de cette branche ; les arcs insulaires sont de grandes formes de la carte.

**Le filtre des profils qui franchissent la mer, depuis le 2026-10-31 :** au-dessus d'un fond local `h < 0`, la montée `A`, présence comprise, a pour demi-largeur `w` après `ReliefWidth` et pour part de débordement `f` entre 0 et 1/3.
- **Son aire vaut `I = A w √π (1 + f)`.** Côté mer, une gaussienne ; côté lagune, son mélange avec une gaussienne trois fois plus large.
- **Le cœur plat a pour demi-largeur `b = max(2 c − k, 0)`,** où `c` est la maille, `L = max(log(A / (−h)), 0)` et `k = w min(√L, √π (1 + f) L / 2)`.
- **Ses flancs lisent `max(|x| − b, 0) / w`.** L'amplitude devient `A / (1 + 2 b / (w √π (1 + f)))` ; l'aire reste exactement `I`, à paramètres locaux fixés.
- **Si `b ≥ c`, toute émergence couvre deux mailles.** Sinon, `log(1 + t) ≤ t` et le choix de `k` bornent les deux flancs par une gaussienne encore émergée à `c`, ou par un sommet entièrement noyé.
- **Le filtre agit point par point, sans carte ni voisin.** Les distances qui déplacent le relief sur des centaines de kilomètres gardent leur double précision.
- **Les versions dépassées des cordons :** `log/spec-relief-tectonique-historique.md`.

**Contrôle du 2026-10-31 :** trois côtes de la graine 0 à 20, 8 et 3 km, plus 60 m, dans `x64/Codex/rendus/avant/` et `apres/` ; aucun pointillé observé après filtrage.
- **À 3 km :** écart maximal de 1/255 par canal ; à 60 m, même borne sauf un pixel de feuillage, sans changement visible de silhouette.
- **À maille nulle, le profil est identique.** Sur 200 000 profils, la largeur émergée ou la submersion est respectée ; l'intégration numérique conserve l'aire à 3,5 × 10⁻¹² près en relatif.
- **À juger en vol :** `tools/tests/2026-10-31-cordons-emergence.txt`.
- **Les plaines côtières plates, calmes :** à moins de 12 km du rivage, le relief laissé au bruit et les badlands tombent à 10 % des leurs : posés avant, ils criblaient la côte de mares sous le niveau de la mer.

## Le lien avec l'érosion : le niveau 0

**La carte expose ce que le niveau 0 attend,** sur la branche `erosion-niveaux` (`recherche-relief.md`, 6.5).

| Entrée | Où | Ce que c'est |
|---|---|---|
| Soulèvement U | tranche 3, z ; `cp.uplift(p)` | mm/an, la même forme que la montée de chaque forme, une part de sa convergence : 4 % sous une cordillère, 3 % sous un arc, 12 % dans une collision, 3 % sous un plateau ; des épaulements et un dôme sur les rifts ; négatif dans les avant-pays, −2 % de la convergence, et les grabens, −10 % de la divergence ; 0 sur les cratons et les vieilles chaînes |
| Érodabilité K | tranche 4, x ; `cp.erodibility(p)` | relative, par roche : socle 0,25, vieille chaîne 0,45, volcanique 0,6, chaîne jeune 1, sédiments 1,6, jusqu'au double dans les sédiments tendres ; plusieurs ordres de grandeur sur Terre (Stock et Montgomery 1999), un facteur dix ici, le niveau 0 calant sa constante |
| Forme avant érosion | `ReliefElevation(p, false)` ; `cp.elevation(ctx, p, valleys=False)` | les grandes formes et le détail, sans vallée ; filtrée à la maille du niveau 0 par `Ctx(maille)` |
| Niveau de base | la mer, `elevation < 0` | les lacs terminaux du niveau 0 en plus |

**Ordres de grandeur, graine 0 :** le soulèvement dépasse 1 mm/an sur 9,5 % des terres, 1,7 mm/an en médiane au-dessus de 2,5 km, 12 mm/an au plus ; l'érodabilité vaut 0,25 sur les boucliers, 1,6 sur la moitié des terres.

**Le branchement, à faire sur `erosion-niveaux` :**
1. **Au démarrage, après la carte tectonique :** `Tectonics::Map` garde ses cinq tranches en mémoire jusqu'au niveau 0 ; il y lit U et K, sans relire le fichier.
2. **Sur la grille du niveau 0,** 20 à 40 km : la forme avant érosion filtrée à deux de ses mailles, U et K en B-spline ; l'équilibre analytique (Tzathas 2024), Priority-Flood, aire drainée, intégrale χ le long du réseau, deux ou trois fois.
3. **Le relief érodé remplace les grandes formes sur les terres,** au-dessus de deux de ses mailles, lu en B-spline ; le détail s'éteint au fond de ses vallées. `ReliefElevation(p, true)` le rend, `(p, false)` jamais : le niveau 0 ne lit pas ses propres sorties.
4. **Le budget :** le niveau 0 s'ajoute à la seconde de la carte ; un cache par graine s'il la dépasse.
5. **Les scripts de la recherche,** `tools/hydro/level0_*.py`, prennent `cp.uplift` et `cp.erodibility` au lieu du soulèvement tiré de complexplanet.

**La distance au front, vive à l'axe :** près de la frontière, la distance signée, exacte à travers elle ; plus loin, la distance simple. La signée change de signe aux jonctions triples : de faux axes courts possibles, sur 40 km.

## Le détail, étape 3

**Douze octaves de 50 km à 13,5 m, lacunarité 2,11, d'amplitude le relief de la carte.** Chaque octave nourrit deux formes, mêlées par le relief et la jeunesse :
- **les chaînes,** au-dessus de 300 à 1 200 m de relief : 1 − |n| moins sa moyenne, crêtes et vallées en V ; chaque octave affaiblie dans les vallées de la précédente ; crêtes vives sur les jeunes, arrondies sur 0,3 de bruit sur les vieilles ;
- **leurs plis,** la plus large octave des chaînes à moins de 500 à 800 km de la frontière, une ceinture plissée plutôt qu'une empreinte digitale :
  - **des crêtes le long des lignes de niveau de la distance à la frontière,** des sinus que l'octave lit comme un bruit, de même |n| moyen ;
  - **deux jeux, de 26 et 52 km d'écart,** qui se relaient selon un bruit de 120 km : l'espacement varie du simple au double, le long des plis et en travers ; là où un jeu s'éteint, les crêtes de l'autre prennent le relais, en échelon. Leur mélange garde l'écart-type d'un seul ;
  - **décalés en travers** du même bruit, 0,35 fois l'écart du jeu court, de 150 et 50 km : les plis se courbent et se décalent, jamais plus raides que la distance, pour qu'aucune crête ne se ferme ;
  - **leur amplitude par segments,** 1 + 0,8 tanh(1,5 z) sur un bruit de 50 km, 1 en moyenne : des plis forts, d'autres à peine marqués, leurs extrémités plongeantes. Elle pèse le poids de l'octave, pas sa valeur : un pli faible n'est pas un plateau ;
  - **sous eux,** les crêtes des deux octaves suivantes réduites de moitié là où les plis sont pleins, les vallées entre les chaînons où l'octave suivante s'affaiblit ;
  - **ils s'effacent** là où la distance cesse de croître, à mi-chemin de deux frontières, et là où elle tourne court, au changement de frontière la plus proche : sous la moitié de sa pente, mesurée sur la B-spline, plus rien ;
- **les collines et les plaines,** ailleurs : le bruit de gradient lui-même.

**L'érosion sans érosion :** chaque octave est affaiblie par la pente des précédentes, 1 / (1 + k s²), k = 1,5 sur les collines, 0,5 sur les chaînes. Un bruit à dérivées analytiques, `RlGradientNoiseD`, ajouté à `Noise.hlsli`.

**Les chaînes orientées :** les trois octaves les plus larges, la première hors des plis, lisent un point gauchi de 5 km, pour qu'aucune crête ne se ferme sur elle-même, et étiré le long des chaînes.
- **L'étirement :** le point est soulevé hors de la sphère d'une mesure de la distance lissée à la frontière ; le bruit varie 2,5 fois plus vite en travers qu'en long. Pas de cisaillement là où la direction tourne.
- **En double, de la carte au bruit :** la distance lissée (`TectonicSample.along`), le soulèvement et la phase des plis. En flottant, leurs centaines de km avançaient par pas de quelques cm, que le soulèvement et les plis rendaient au sol : des murs de 8 à 17 cm tous les demi-mètres, sur les chaînes, vus à 1 m. Le soulèvement suit une quintique plutôt qu'une tanh, qui n'a pas de double : même pente à la frontière, même hauteur, atteinte à 15/8 de 450 km.
- **Il s'éteint à 450 km de la frontière :** plus loin, le bruit est isotrope. Les sutures n'orientent rien : autour d'un point, l'étirement dessinait des anneaux.

**Les plates-formes :** des mesas, leur relief de 350 m sur 12 km mis en marches de 120 m, chaque contremarche de 10 à 60 % de la marche, tirée par marche : des falaises et des pentes. **Les sédiments tendres :** des ravines fines, 45 m de 600 à 14 m, les badlands.

**`gRoughness`,** des mêmes champs : 0,1 les plaines, 0,35 les collines, 0,5 les vieilles chaînes, 0,6 les mesas et badlands, 1 les chaînes jeunes.

**Les vallées :** aucune n'est creusée. Les vallées en zéros d'un bruit dessinaient des canaux en boucles ; les rivières seront celles du niveau 0. `ReliefElevation(p, false)` donne le même relief.

**Ce qui tient :** l'interface `ReliefElevation(p)` et `(p, valleys)` ; les doubles pour le découpage des octaves ; le filtrage par `gMaxFrequency` et l'arrondi des crêtes ; aucune octave sous deux mailles ; les sommets plafonnés en douceur au-dessus de 8 km.

## Le portage CPU et le cache

**Le moteur écrit sa carte à chaque démarrage, à côté de l'exécutable :** `x64/Release/tectonique-<graine>.bin`, 65 Mo, un en-tête `EXOTECT2` puis les cinq tranches à pleine résolution (`Tectonics::Save`).

**`tools/hydro/cp.py` le relit :** la même lecture en B-spline, le même mélange des faces, les mêmes profils et le même bruit, en float64. `EXOLUNE_TECTONIQUE` donne un autre chemin.
- **Pourquoi ce choix :** porter le calcul de la carte en numpy doublerait 900 lignes de C++ et divergerait au moindre arrondi. Le cache est la carte même du moteur.
- **La limite :** une graine que le moteur n'a jamais calculée n'a pas de carte ; le portage le dit.
- **Vérifié le 2026-10-31 après le filtrage de l'émergence :** contre la carte de la planète du moteur, 600 mailles près du centre des faces : écart médian 6,48 cm, p99 2,17 m, maximum 13,39 m ; mêmes écarts avant le filtre ; `x64/Codex/rendus/apres/portage.json`.
- **L'interface gardée :** `Ctx`, `elevation(ctx, p, extra, valleys)`, `window`, `latlon`, `move` ; en plus, pour le niveau 0, `uplift(p)` et `erodibility(p)`. `extra` donne `elev`, `norivers`, `large`, `relief`, `youth`, `strata`, `axis`, `roughness`. `CUR_SEED` devient `PLANET_SEED`. Les scripts de la recherche érosion qui lisent `CUR_SEED`, et ceux de `tools/hydro` et `tools/cotes` qui lisaient les parties de l'ancien relief, sont à adapter.

**La carte de la planète se calcule après la carte tectonique,** qu'elle lit (`D3DApp::CreateTectonicMap`).

## Les mesures

**Les ordres de grandeur,** portage CPU, 400 000 points, mailles de 2 km, sommets et fosses affinés sur 80 km à 500 m :

| Mesure | Seconde passe | Avant | Cible |
|---|---|---|---|
| Terres, graine 0 ; graines 1 et 2 | 32,9 % ; 34,0 et 30,5 % | 33,0 % ; 33,8 et 30,4 % | 30 à 45 %, la Terre 29 % |
| Mode et médiane des terres | +125 m, 379 m | +125 m, 363 m | la Terre : médiane vers 400 m |
| Mode et médiane des océans | −4 525 m, −4 452 m | −4 525 m, −4 445 m | −4 à −5 km |
| Sommets des 12 plus hautes chaînes | 6,9 à 7,6 km | 6,6 à 7,6 km | 6 à 8 km |
| Fosses, les 8 plus profondes | −9,1 à −10,1 km | −9,0 à −10,5 km | −8 à −10 km |
| Au-dessus de 3 km | 2,0 % | 1,9 % | la Terre : 1,6 % |
| Rifts, en part des cellules de frontière, graines 0, 1, 2 | 2,5, 8,6, 2,5 % | 15,7, 17,6, 10,9 % | quelques pour cent |

- **Les plaques et les continents restent ceux d'avant :** 0,2 % des cellules changent de plaque, 0,7 % de croûte, les rifts ouverts surtout ; les lieux des tests gardent leur sens.
- **Pourquoi 33 % de terres :** 43 % de croûte continentale, dont les plateaux, les talus et les bassins bas noient un quart, comme sur Terre (41 % pour 29 %). L'hypsométrie reste bimodale, vers +0,1 et −4,5 km.
- **Les mers étroites prennent les rifts rapides :** les plaques s'écartent ici de 10 à 60 mm/an, bien plus que les rifts terrestres, quelques mm/an.

**Le temps et la mémoire de la carte tectonique,** au repos :
- **Le temps :** 0,81 à 0,86 s au titre du moteur, sur trois démarrages, contre 2,53 s pour la première version ; 0,88 à 0,90 s hors du moteur. Au bit près d'un calcul à l'autre.
- **La mémoire GPU :** 37,9 Mo, contre 49,5 : trois tranches à pleine résolution, la tranche des vues au quart.
- **Le pic sur le CPU :** 440 à 500 Mo pendant le calcul, rendus après ; à surveiller pour les corps d'un système calculés en parallèle.

**Le jeu de vérification :** la compilation sans erreur ni nouvel avertissement ; les huit vues de contrôle, `rend_tecto.ps1`, et leur référence `base_tecto` dans les captures de la session ; les vues en vol de `tools/tests/2026-10-31-relief-tectonique.txt` ; la planche `tecto4_planche.jpg`, et `tecto4_portage.jpg`, les reliefs ombrés du portage aux mêmes lieux.

**Les huit vues de contrôle,** sur la carte de la graine 0, hauteur au-dessus du sol :

| Vue | Hauteur | Lieu, tangage, cap | Soleil |
|---|---|---|---|
| Orbite, le grand continent | 10 000 km | −0,5, −18,225, 90°, 0° | 10, −5 |
| Au-dessus des cumulus, une plaine | 10 km | 38,1445, 103,5352, 35°, 90° | 38,1445, 128,5352 |
| Des cumulus épars et leurs ombres, sur des collines | 30 km | −27,875, −0,375, 45°, 270° | −25, 30 |
| Une côte plate, tropicale, vue de la mer | 60 m | 16,70628, −89,28981, 6°, 9° | 30, −70 |
| Une pente boisée à 590 m, 30 m au-dessus des cimes : à 30 m du sol, la caméra est dans les couronnes | 60 m | −8,44835, 118,48865, 8°, 163° | −20, 130 |
| La chaîne de collision, à 4 700 m | 1 km | −7,37725, 116,87998, 10°, 108° | −20, 100 |
| Les mesas d'une plate-forme | 1,5 km | 15,625, 95,625, 12°, 90° | 15, 70 |
| Cailloux et touffes au pied d'une mesa | 1,2 m | 15,62455, 95,6292, 25°, 90° | 15, 70 |

**Le départ du jeu :** 300 km au-dessus de −12°, 116,875°, la chaîne de collision à l'horizon au nord ; le soleil à −5°, 125° (`main.cpp`, `Settings.h`). Le globe du lanceur : −0,5°, −18,225°, le soleil à 10°, −5°.

## Les défauts connus

- **Les vallées entre 20 km et 1 km :** aucune n'est creusée ; les chaînes ont leurs plis et leurs cols, pas de réseau qui les draine. Le niveau 0 et ses vallées fines, étapes 4 et 7.
- **Les estuaires aux bouches des fleuves :** les rias des côtes sont des vallées noyées tirées par le bruit ; les vrais estuaires attendent les fleuves du niveau 0.
- **Les plis suivent la distance à la frontière la plus proche :** les chevrons les plus vifs, près des jonctions triples, s'effacent ; autour d'une frontière très courbe, ses lignes de niveau dessinent encore des arcs concentriques, et un pli fort peut y serpenter.
- **Les très basses plaines côtières,** sous 0,5 m/km, ont encore des cuvettes sous le niveau de la mer à l'intérieur ; le niveau 0 les drainera.
- **La vue `relief` montre les facettes du maillage** sur les profils vifs vus d'orbite ; le relief du jeu ne les montre pas.
- **Pas encore de collines abyssales orientées par l'âge :** les volcans sont faits, `spec-volcanisme.md`.
- **La référence du banc de qualité ne vaut plus :** ses lieux sont ceux de l'ancien relief ; elle se ré-enregistre sur demande.
- **Le pic de mémoire du calcul,** 0,5 Go : pour un système calculé en parallèle, à réduire ou à étaler.
- **Aucune vallée creusée :** en attendant le niveau 0, `valleys` ne change rien.

## Le plan par étapes

| Étape | Contenu | Statut |
|---|---|---|
| 0 | La règle de la carte qui porte la géométrie ; cette spec | faite le 2026-10-31 |
| 1 | La carte tectonique et ses vues de diagnostic ; les continents par lieu, les marges | faite le 2026-10-31, à juger en vol |
| 2 | Les grandes formes : océans, marges, fosses, chaînes, plateaux, rifts, transformantes, vieilles chaînes | faite le 2026-10-31, à juger en vol |
| 3 | Le détail modulé : chaînes orientées, érosion par la pente, mesas, badlands, `gRoughness` | fait le 2026-10-31, à juger en vol ; banc de qualité à refaire sur de nouvelles vues |
| 4 | Le niveau 0 sur le soulèvement tectonique, à l'équilibre analytique ; son relief érodé au-dessus de deux cellules | entrées prêtes le 2026-10-31 ; à faire sur `erosion-niveaux` |
| 5 | Les points chauds, les cônes volcaniques, les collines abyssales | volcans faits le 2026-10-31, `spec-volcanisme.md`, piste `piste/volcanisme` ; collines abyssales à faire |
| 6 | Les côtes par type de marge | faite le 2026-10-31 par la pente de la marge ; les estuaires avec les fleuves du niveau 0 |
| 7 | Les vallées fines : Dendry par tuiles, accroché au niveau 0 | à faire |
| 8 | Une histoire simulée à la Cortial, si l'instantané paraît trop régulier | si besoin |

Le détail de chaque étape : `recherche-relief.md`, section 7. Les règles nouvelles sont dans `principes.md`.
