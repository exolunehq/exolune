# Spécification : un texturage universel, par échelles, vérifié par banc

Statut : validée le 2026-10-23 ; étapes 1 et 2 faites, étape 3 en cours. Remplace la méthode des corrections vue par vue. Reprend les plans de `spec-photos-par-echelle.md` et `spec-parois-minerales.md`.

## Le constat

**On stagne :** chaque correction règle la vue signalée, et la montagne d'à côté montre la même famille de défauts. Cas récents :
- **le sable flou** de 250 m à quelques kilomètres ;
- **les « sparadraps » :** des bandes et des crevasses qui s'arrêtent net ;
- **le grillage** de fissures sur le granite ;
- **les bandes qui glissent** à l'approche.

**Trois causes de méthode :**
1. **Aucun matériau n'a d'échelle de détail complète et déclarée.** Chacun empile des couches ajoutées au fil des besoins, avec des trous entre elles.
2. **Les règles existent, mais rien ne vérifie qu'elles sont tenues partout.** Le contrôle passe par l'œil, une vue à la fois.
3. **Les défauts se voient d'abord de loin et ailleurs,** là où personne ne regarde au moment de la correction.

## L'audit : ce qui couvre chaque échelle, matériau par matériau

Communs à tous : la couleur du biome, au-delà de 200 km ; un bruit de clarté de 8 km au pixel, ±15 % ; le grain d'éclairage des octaves de complexplanet que la maille ne porte pas.

| Matériau | Ce qui le couvre | Trou |
|---|---|---|
| Sable | grain fin sous 3 cm ; rides de 12 cm ; photo `sandy_gravel_02`, limitée à 50 cm | de 50 cm au kilomètre |
| Herbe | brins, touffes, taches de 2 m ; bosses jusqu'à 4 m, dans la lumière | de 4 m au kilomètre |
| Éboulis | tuile générée de 4 m | de 4 m au kilomètre |
| Granite, basalte | tuile de 8 m ; structures de 64 m | de 64 m au kilomètre |
| Roche litée | photo de 12,8 m ; structures de 64 m ; strates jusqu'à 300 m ; plaques de 128 m | couvert, mais des arrêts nets |
| Badlands | la photo de marbre de la roche litée | matière fausse |
| Neige | aucune texture | toutes les échelles |

## Ce que fait l'industrie

Recherche du 2026-10-23. Aucun studio n'écrit mot pour mot « du contenu dans chaque octave », mais tous convergent vers cette architecture.
- **Des étages par échelle :** une couleur macro au kilomètre, un méso de 10 à 100 m, un micro de 1 à 4 m. [Frostbite, Andersson 2007](https://www.advances.realtimerendering.com/s2007/Andersson-TerrainRendering(Siggraph07)-CourseNotes.pdf), [Wildlands](https://80.lv/articles/landscape-and-material-pipeline-of-ghost-recon-wildlands/), [Star Citizen](https://www.adobe.com/products/substance3d/magazine/star-citizen-texturing-sci-fi-open-world-game-substance.html).
- **Une couche est la bande qui manque à la couche du dessus :** la texture de détail est définie comme ce qui manque au niveau plus grossier. [Brevet SGI](https://patents.google.com/patent/US5471572)
- **Des bandes à moyenne nulle n'altèrent pas les échelles au-dessus :** pas de saut quand une bande s'efface. [Brevet Pixar](https://patents.google.com/patent/US7672476), [Proland](https://proland.inrialpes.fr/doc/proland-4.0/terrain/html/index.html)
- **Une bande trop fine pour le pixel est retirée,** et sa variance passe ailleurs : dans les limites, dans la rugosité. [Lagae 2010](https://lirias.kuleuven.be/retrieve/104878), [LEAN](https://userpages.cs.umbc.edu/olano/papers/lean/)
- **Contre la répétition :** décalage et rotation par tuile, mélange qui garde moyenne et variance, hex-tiling. [Quilez](https://iquilezles.org/articles/texturerepetition), [Heitz et Neyret 2018](https://highperformancegraphics.org/2018/best-paper/), [Mikkelsen 2022](https://jcgt.org/published/0011/03/05/paper.pdf)
- **Un seul exemplaire ne couvre qu'une plage d'échelles :** il en faut plusieurs, chaînés, pour un zoom continu. [Han 2008](https://www.cs.columbia.edu/cg/mts/)
- **Le symptôme du sable flou est connu ailleurs :** les joueurs de Flight Simulator le signalent. [Forum MSFS](https://forums.flightsimulator.com/t/ground-textures-are-blurry-lod-system-is-too-aggressive-and-loss-of-detail-in-2024-streamed-scenery-and-clouds-looks-worse-than-2020/676315?page=53)

## La règle : une pile de bandes par matériau

**Un matériau est une pile de bandes, du millimètre au kilomètre, environ 22 octaves, sans trou.** C'est une donnée, pas du code.

- **Une bande déclare :** sa source, procédurale, tuile générée ou photo ; ses longueurs d'onde ; son écart type par canal, en couleur et en pente.
- **La couverture :** la plus grande longueur d'onde d'une bande dépasse la plus petite de la suivante. Un validateur, hors du moteur, refuse toute pile trouée. Le sable actuel échouerait.
- **L'amplitude suit une loi par matériau :** l'écart type d'une octave en fonction de sa longueur d'onde, mesurée sur des photos du matériau, comme `STONE_SLOPE_SIGMA` l'est déjà pour la pente de la roche.
- **Chaque bande est à moyenne nulle :** sa moyenne appartient à la bande du dessus, jusqu'à la palette du biome.
- **Une seule règle d'effacement pour toutes les sources :** le poids d'une bande est `OctaveFade(log2 λ, log2 pixel)`, celui que les bruits ont déjà. Tuiles, photos et bruits s'effacent pareil, sans seuil de distance.
- **Ce que le pixel perd n'est pas perdu :** la variance des bandes effacées élargit les limites entre matériaux (`SpreadStep`, la règle universelle) et, à terme, la rugosité.
- **Contre la répétition :** les tuiles gardent le pavage décalé et tourné de `ProjectMaterial`, au mélange qui garde la variance ; chaque bande est modulée par la bande du dessus, ce qui masque sa période.
- **Aucune structure ne s'arrête net :** une bande, une crevasse, une strate finit en s'amincissant ou en s'estompant, sur une longueur d'au moins quelques fois sa largeur. C'est la règle des « sparadraps » ; failles et lentilles y sont soumises.

**Ce que nous avons déjà :** l'effacement par octave (`OctaveFade`), la règle universelle des limites (`SpreadStep`, `SlopeShares`), le pavage qui garde la variance (`ProjectMaterial`), le chargement des photos par échelle (`kScans`). **Ce qui manque :** la pile déclarée, le validateur, les sources des bandes de 1 m à 1 km, et le banc.

**Ce que ça remplace :** la tuile fine, la tuile grossière, la tuile de 64 m et les bruits ajoutés au cas par cas deviennent une pile générique, lue par une seule fonction.

## Le banc : mesurer au lieu de regarder

Recherche du 2026-10-23. Aucun outil ne couvre seul ces familles de défauts ; la littérature fournit une brique par famille, en Python. Aucun banc publié n'échantillonne massivement des lieux : le nôtre est à construire.

**Fait le 2026-10-23 :** `tools/banc_qualite.py`, sur le mode liste du moteur (`MYPLANETENGINE_BATCH`), qui enchaîne des centaines de vues en un lancement, sans fenêtre : environ 1,3 s par vue, 25 lieux en une dizaine de minutes.

```
python tools/banc_qualite.py <exe> <dossier> [--sites 25] [--seed 1] [--before tools/banc_qualite_reference.json]
```

**L'échantillonnage :**
- **des lieux tirés par matériau :** huit fois plus de candidats que de lieux, vus de 3 km à la verticale dans la vue de chaque matériau ; sur la terre ferme, une part égale des lieux pour chacun, là où il couvre le plus ;
- **chaque lieu regarde vers où son matériau se montre le plus,** parmi huit caps, à 35° sous l'horizon ;
- **cinq hauteurs au-dessus du sol :** 12, 50, 200, 800 et 3 000 m ;
- **des crops de 128² pixels,** attribués au matériau visible qui en couvre 70 %, la neige couvrant les autres, l'eau exclue ; masques tirés des vues de diagnostic `MYPLANETENGINE_VIEW`.

**Les mesures, une par famille de défauts :**

| Défaut | Mesure | Référence : photos réelles |
|---|---|---|
| Flou, détail fin manquant | `hf` : énergie de l'octave la plus fine du crop, 2 à 4 pixels, contre celle de 16 à 32 pixels, en dB ; une image naturelle a autant d'énergie dans chaque octave ([spectres des images naturelles](https://pmc.ncbi.nlm.nih.gov/articles/PMC2929959/figure/F3)) | médiane +0,8 dB, p5 −6,9 |
| Trou d'échelle | `trou` : de combien l'octave du milieu la plus faible tombe sous ses deux voisines, en dB | p95 3,5 dB |
| Répétition | plus haut pic local de l'autocorrélation du détail, hors du lobe central, aussi long soit-il ; vérifiée : bruit 0,03, motif pavé 1,0 ([Lutz 2023](https://diglib.eg.org/bitstream/handle/10.1111/cgf14766/v42i2pp347-358_cgf14766.pdf)) | p95 0,18 |
| Bandes droites, coutures | segments droits de plus de 60 pixels au sol ([LSD](https://ipol.im/pub/art/2012/gjmr-lsd), qui coupe une bande ondulée en morceaux de moins de 120 pixels) | — |
| Mutation à l'approche | la même caméra, le maillage deux fois plus fin : changement relatif de la lumière au sol. Ce que le maillage décide de l'aspect change quand on approche ; ce que les pixels effacent selon leur taille ne compte pas, la caméra est la même | — |
| Scintillement | `tools/banc_tremblement.py`, caméra fixe | — |

**Les photos de référence** sont `docs/images/cible-*.jpg`, passées par les mêmes crops. Restent à faire : la comparaison aux photos du même matériau, et la distance KID ([KID](https://arxiv.org/pdf/1801.01401)).

**Rendre les régressions visibles :**
- `qualite.json` et `rapport.md` à chaque passage, avec les planches des douze crops les plus flous et les plus répétitifs de chaque matériau ;
- `--before` ajoute au rapport l'écart à un passage précédent ; la référence est `tools/banc_qualite_reference.json` ;
- une correction n'est acceptée que si aucun p95 ne se dégrade de plus de 10 %.

**L'œil humain reste juge du goût,** sur quelques vues de référence, comme le conseille [Wronski](https://bartwronski.com/2019/08/14/how-not-to-test-graphics-algorithms/) : une dizaine d'images dorées, le reste par des invariants mesurés.

## La référence du 2026-10-23

25 lieux, 5 par matériau, graine 1, état `5b5af34`. Chiffres complets dans `tools/banc_qualite_reference.json`. Une paroi y compte roche et vires ensemble, telle qu'on la voit.

![Les crops les plus flous de chaque matériau, et les plus répétitifs du sable](images/banc-qualite-pires.jpg)

**Le détail fin, `hf` médiane en dB, contre +0,8 pour les photos réelles :**

| Matériau | 12 m | 50 m | 200 m | 800 m | 3 000 m |
|---|---|---|---|---|---|
| Sable | +10,6 | +16,9 | −5,9 | −14,8 | −8,5 |
| Herbe | −3,7 | −17,2 | −7,1 | −12,7 | −7,1 |
| Neige | −6,7 | −6,0 | −9,6 | −13,0 | −6,7 |
| Roche | −1,7 | 0,0 | −1,7 | +0,1 | — |

**Les constats :**
- **Tout est flou de 200 m à 3 km, sauf la roche :** 6 à 17 dB de détail fin manquent. La roche se tient près des photos grâce à la photo de falaise, aux strates et aux structures de 64 m, qui couvrent ses échelles. C'est le trou que l'audit prévoyait.
- **Le sable, de près, est plus net que nature,** +10 à +17 dB : le grain de la photo. Puis plus rien au-delà de 200 m, et un trou d'octave de 9 dB à 50 m, contre 3,5 dB pour les photos.
- **La neige a un trou de 9 dB à 50 m :** elle n'a pas de texture.
- **La répétition est faible,** 0,16 à 0,32 contre 0,18 pour les photos ; sauf les rides du sable de près, 0,46, en partie naturelle.
- **La mutation à l'approche :** quand le maillage s'affine, la lumière change de moins de 1 % en médiane, mais de 7 à 10 % au p95, de 200 m à 3 km. Des lieux où l'aspect dépend encore du maillage, à examiner.
- **Les éboulis sont trop peu échantillonnés,** 19 crops : la roche les couvre presque partout ; il leur faudra des lieux dédiés.

## Étape 2 : la pile déclarée et son validateur

Faite le 2026-10-23, sans rien changer à l'image.

**La pile déclarée,** `tools/bandes_materiaux.json` : pour chaque matériau, chaque source de détail relevée dans le code, avec ses longueurs d'onde, ce qu'elle porte, couleur ou lumière, et où elle est dans le code. Les sources communes à tous, la clarté locale, le grain du relief et le relief du maillage, y sont à part.

**Le validateur,** `tools/valide_bandes.py`, en deux volets :
- **déclaré :** octave par octave, de 2 mm à 2 km, une source de couleur assez forte pour se voir ; la clarté locale perd 38 % par octave vers le fin et ne compte plus sous 10 % de sa force, soit sous 256 m ;
- **mesuré :** le moteur vise le sol à la verticale de 1,5 m à 6 km, chaque hauteur montrant cinq octaves de taille connue au sol ; la roche et les éboulis, qui tiennent aux pentes, sont visés à 45° vers la paroi. Le contraste de chaque octave, l'écart type du logarithme de la lumière en dB, est rangé par matériau et par octave du monde, à côté de la même mesure sur les scans réels de `../scans`, dont la largeur est connue. Les scans n'ont que leur albédo, sans soleil.

```
python tools/valide_bandes.py --declared
python tools/valide_bandes.py <exe> <dossier> [--sites 15]
```

**Le tirage des lieux** tient compte de ce qui couvre chaque matériau : une roche sous la neige ne compte pas pour la roche. Une paroi se mesure telle qu'on la voit, roche et vires comprises, la vue `rockall`.

### Le résultat

![Contraste par octave au sol, rendu et scans réels ; en gris, les octaves sans couleur déclarée](images/spectre-materiaux.png)

**La déclaration et la mesure concordent :** chaque trou déclaré se voit dans le rendu. Chiffres dans `tools/spectre_reference.json`, 20 lieux, graine 2.

| Matériau | Trou déclaré, sans couleur | Ce que mesure le rendu | Écart aux scans réels |
|---|---|---|---|
| Sable | de 50 cm à 256 m | une chute jusqu'à −60 dB à 4 m, entre −25 dB au centimètre et −40 dB au-delà de 16 m | 16 à 18 dB sous les scans de 1 à 8 m |
| Neige | toutes les échelles | −70 à −77 dB jusqu'à 1 m ; −53 dB au-delà de 16 m, la seule lumière du relief | 40 à 50 dB sous les autres matériaux |
| Herbe | de 25 cm à 1 m, de 4 m à 256 m | des creux à −37 dB vers 1 m et de 16 à 128 m, contre −28 dB entre 1 et 25 cm | pas de scan d'herbe |
| Éboulis | de 4 m à 256 m | au niveau des scans jusqu'à 25 cm ; au-delà, pas assez de vues | — |
| Roche litée, granite | de 64 à 256 m pour le granite | au niveau des scans de 8 mm à 50 cm, −21 à −28 dB de 8 à 128 m | aucun |

**Ce que ça règle :**
- **L'ordre de l'étape 3 :** la neige, puis le sable, puis l'herbe, puis les éboulis au-delà de 4 m ; la roche n'en a pas besoin.
- **La cible de chaque octave à combler :** le niveau des scans réels du matériau, ou celui de ses octaves voisines, soit environ −25 à −40 dB.
- **La vérification :** une octave comblée remonte dans ce graphe ; le banc de qualité confirme qu'elle se voit à l'écran.

**Les limites :** les scans n'ont que l'albédo ; la neige et l'herbe n'ont pas de scan de référence ; la roche manque de vues de 1 à 4 m.


## Étape 3 : combler les trous

### Première passe, le 2026-10-23 : les bandes de détail

**Une seule fonction pour tous les matériaux,** `DetailBands` (`Materials.hlsli`) : une octave de bruit de gradient de la grille de la planète par longueur d'onde, de `2^finest` à `2^widest` m.
- **Chaque octave incline le sol de la même pente :** un relief auto-similaire, comme celui de la nature, donne le même contraste à chaque octave.
- **Chaque octave change la couleur du même facteur.**
- **Chaque octave s'efface selon la taille du pixel,** comme tout bruit (`OctaveFade`).
- **Seuls les paramètres diffèrent par matériau,** dans `PlanetSettings.hlsli` : `SNOW_BANDS`, `SAND_BANDS`, `GRASS_BANDS`, `SCREE_BANDS`.
- **Le calibrage, mesuré :** une pente de 0,05 par octave donne environ −49 dB de contraste ; une couleur de 0,04, environ −40 dB.

| Matériau | Bandes | Pente, couleur par octave | Avant, contraste au plus bas | Après |
|---|---|---|---|---|
| Neige | 1 cm à 16 m ; au-delà, la neige lisse le sol, le relief dessine | 0,08 ; 0,015 | −70 à −77 dB sous 1 m | −42 à −48 dB, plat |
| Sable | 50 cm à 32 m, entre sa photo et la lumière du relief | 0,05 ; 0,04 | −60 dB à 4 m | −41 à −42 dB, le niveau de ses scans réels |
| Herbe | 25 cm à 128 m | 0,06 ; 0,2 | −35 à −38 dB vers 1 m | −30 à −34 dB |
| Éboulis | 4 à 64 m, au-delà de sa tuile | 0,05 ; 0,06 | non mesuré | non mesuré, faute de vues |

![Contraste par octave après les bandes de détail](images/spectre-materiaux-bandes.png)

**Le banc de qualité :**
- **les trous d'échelle reviennent au niveau des photos,** 3,5 dB au p95 : sable à 50 m de 9,1 à 2,8 dB, neige de 8,7 à 2,4 dB, herbe à 800 m de 6,5 à 1,5 dB ;
- **la répétition et la mutation ne bougent pas ;**
- **le scintillement non plus,** sur quatre vues ;
- **le détail fin rapporté au détail moyen, `hf`, baisse de près,** sable à 12 m de +10,6 à +3,5 dB : le moyen a gagné plus que le fin. La dernière octave de l'écran reste en partie effacée par la règle anti-crénelage ; `hf` ne peut pas atteindre les photos, et ne se lit qu'en écart.

**Essayé et écarté :** l'effacement des bruits selon la moyenne géométrique des deux côtés du pixel, au lieu du plus long, pour les vues rasantes. Effet invisible.

### Le flou qui restait : le sol nu, un matériau oublié

**Le constat :** à la vue signalée en vol, `2588.6 32.10988 10.53312 9.8 49.1`, une large zone brun clair restait floue à toute distance.

**La cause, trouvée par les vues de diagnostic :** cette zone n'était **aucun matériau**. Ni sable, ni herbe, ni éboulis, ni roche, ni neige : du **sol nu**, là où il fait trop sec pour l'herbe et trop humide ou trop froid pour le sable. Il n'avait que la couleur du biome, sans texture à aucune échelle.

**L'angle mort du banc :** il ne mesurait que les cinq matériaux qui ont une vue de diagnostic. Le sol nu, le reste des sols, n'était dans aucun crop.

![Avant, puis avec le sol nu texturé : la vue signalée, une montagne, un désert](images/sol-nu.png)

**Les correctifs :**
- **Le sol nu a sa texture :** la photo `sandy_gravel_02`, un sol de désert sableux et caillouteux, sans les rides du sable ; ses bandes de détail de 50 cm à 64 m, `SOIL_BANDS`. Il entre dans la pente, le relief et la cavité comme les autres sols.
- **Le banc et le validateur ont une sixième classe,** `soil`, le reste des sols une fois l'herbe et le sable posés, tirée et mesurée comme les autres.
- **La règle, dans `principes.md` :** tout pixel de sol appartient à un matériau qui a sa pile de bandes.

**Mesures, sur les mêmes 30 lieux :**
- sol nu : détail fin +4,7 à +5,4 dB de 12 à 50 m, +3,5 dB à 800 m ; trous d'échelle −1 à −2,5 dB ;
- spectre du sol nu plat, de −28 à −42 dB, au niveau des scans de gravier ;
- aucun autre matériau ne bouge ; scintillement inchangé.

### Essayé et écarté : le grain du relief sous la maille

**L'idée :** le relief de complexplanet entre la taille du pixel et celle de la maille n'est dessiné par personne, sauf la grille fine sur la face ; la règle universelle compte ces octaves comme cachées et étale les limites des matériaux sur une maille. Le grain des pixels, `DetailSlope`, les aurait dessinées jusqu'au pixel, avec la pente par octave que suppose la dispersion : 2 `OCTAVE_SLOPE` fois la rugosité, le gradient de notre bruit ayant un écart type de 0,5 par axe.

**Le résultat, mesuré :**
- **aucun gain au banc de qualité** sur les mêmes lieux ;
- **la roche perd un point en descente,** 10,5 % → 9,0 % à 200 km : notre bruit de gradient a moins de pentes extrêmes qu'une loi normale, et moins de pixels passent le seuil de la roche ;
- **le scintillement monte de 14 %** sur une vue.

**Retiré.** Le flou venait du sol nu. L'idée reste valable, mais il faudrait un bruit aux queues normales, et un gain mesuré.

## Le plan

1. **Le banc d'abord,** fait le 2026-10-23 : `tools/banc_qualite.py`, sa référence et ses premiers constats ci-dessus.
2. **La pile déclarée et son validateur,** faits le 2026-10-23, ci-dessus.
3. **Combler les trous, matériau par matériau, dans l'ordre que mesure l'étape 2 :** neige, sable, herbe et sol, éboulis au-delà de 4 m. Première passe faite ; le sol nu, oublié, a sa texture. Les sources des bandes de 1 m à 1 km : bruits par matériau, tuiles générées plus grandes, photos aériennes de Poly Haven de 15 à 90 m, déjà en partie dans `../scans`.
4. **La règle des arrêts :** failles, lentilles et crevasses finissent en s'amincissant ; mesurée par les segments droits du banc.
5. **Chaque étape est acceptée par le banc :** aucune régression de plus de 10 % sur un p95, et l'œil seulement sur une dizaine de vues de référence.

**Ce qui est en suspens, à reprendre sous ces règles :**
- les failles des strates, `StrataPlates`, non commitées : elles coupent les bandes net, d'où des « sparadraps » ;
- le sable flou de 250 m à quelques kilomètres, en montagne comme ailleurs, `2588.6 32.10988 10.53312 9.8 49.1` : le trou de sa pile ;
- les badlands, qui portent la photo de marbre de la roche litée.
