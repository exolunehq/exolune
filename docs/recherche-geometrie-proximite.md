# Recherche : la géométrie de proximité, corniches et relief au mètre

Statut : recherche du 2026-10-24 ; état de l'art et plan, rien de décidé. Prépare une spec. Fait suite à `log/spec-relief-reel.md`, `log/spec-parois.md` et `log/spec-parallaxe.md`. La géométrie reste à complexplanet (`geometrie.md`) : ce qui est proposé ici est un ajout de détail, sous 13,5 m.

## 1. La conclusion et le plan

**En bref :**
- **Un relief ne peut arriver sans se voir que s'il arrive petit à l'écran.** Les moteurs qui ajoutent du relief sans saut le font naître à quelques pixels : triangles de largeur constante à l'écran dans Battlefield 3, découpe à un pas fixé en pixels dans Nanite.
- **Chez nous, il naît à 56 à 100 pixels.** Le maillage ne porte une forme qu'à partir de 8 mailles, et une maille fait 7 à 13 pixels. D'où la corniche qui surgit dans les derniers mètres.
- **Notre maillage ne peut pas la porter plus tôt :** ses sommets glissent, et un relief plus court que 8 mailles tremble (mesuré, `log/spec-relief-reel.md`).
- **La voie recommandée : amplifier les mailles proches.** Chaque maille proche est redécoupée en 8 × 8, en nombre constant. Seul le détail, bon marché, y est évalué ; complexplanet ne l'est pas davantage. Le relief y naît à 8 sous-mailles, soit 7 à 13 pixels.
- **La forme d'abord :** une corniche n'est pas une ligne de niveau. C'est un banc dur qui avance au-dessus d'un banc tendre creusé, inégal le long de lui-même, coupé par les diaclases et les ravines, enterré sous ses éboulis. La section 4 en donne le champ, lié à la colonne stratigraphique.
- **Famille de surcouche :** ajout de détail, les bancs de 1 à 13 m, de moyenne nulle. Les gradins des formations de 20 à 60 m restent un remplacement, sur `piste/parois-gradins`.

**Écartés :**
- **Le quadtree à sommets fixes, CDLOD :** stable, mais coût variable ; POC clos, 34 % d'images à-coups.
- **Les arbres binaires concurrents, CBT :** un état gardé d'une image à l'autre, contraire au calcul intégral à chaque image.
- **La parallaxe seule :** pas de silhouette, 0,8 à 1 ms.
- **Les corniches dessinées dans la lumière seule :** l'effet feutre.

**Le plan, par étapes :**
1. **Le banc d'arrivée, sans toucher au rendu.**
   - La même vue, caméra fixe, rendue avec un maillage de plus en plus fin : `MYPLANETENGINE_FACE_FACTOR` de 2 à 0,125, par huitièmes d'octave, 33 rendus en un lancement `MYPLANETENGINE_BATCH`.
   - Mesures : le changement d'un rendu au suivant, son pic et son total, sur six parois.
   - Témoins : le build du tag `piste/parois-gradins`, où relief des matériaux et gradins étaient actifs et surgissaient ; et celui du dernier tag qui les garde dans le code, `jalon/28-vaisseau-habitacle`, avec `MATERIAL_RELIEF` = 1 et `WALL_RELIEF` = 1 ; ils sont retirés depuis le 2026-10-30. Le banc doit les détecter nettement ; sinon il n'est pas assez sensible.
   - Fait quand : la référence d'aujourd'hui et les deux témoins sont chiffrés, et les seuils de la section 5 fixés. Un script Python, aucun changement du moteur.
2. **Le champ de corniche, en vue de diagnostic.**
   - `MYPLANETENGINE_VIEW` = `ledge` : le recul en gris, sans géométrie.
   - Jugé à côté des photos `cible-*.jpg` et mesuré par les segments droits du banc de qualité.
   - Fait quand : aucune corniche ne traverse une paroi d'un trait, et l'utilisateur valide les formes.
3. **Les mailles amplifiées, sans relief.**
   - Un tirage instancié d'une grille de 9 × 9 sommets par maille proche, calculée dans le vertex shader, sur le triangle actuel. Rien en mémoire.
   - Une plage fixe de mailles autour du nadir, la face et les premiers anneaux : un coût constant. Le maillage glissant ne dessine plus ces mailles.
   - Au bord de la plage, le relief s'éteint et les sous-sommets restent sur l'arête de la maille voisine : pas de fente.
   - Deux réglages du coût : l'étendue de la plage, et la découpe, 8 × 8 ou 4 × 4. Toute la face en 8 × 8 ferait 3 millions de sommets.
   - Fait quand : image identique à 1/255 près, coût mesuré à 3, 30 et 300 m.
4. **Le relief vertical des corniches** dans les mailles amplifiées, filtré à 8 sous-mailles ; la lumière porte le reste, comme le faisait `Texture.carried` du relief des matériaux, retiré.
   - Inscrit dans `geometrie.md` ; arrêt par un réglage, `CORNICE_RELIEF` = 0 ; plancher de la caméra relevé de l'amplitude maximale.
   - Bancs d'arrivée, de tremblement, de qualité et de descente.
5. **Le recul le long de la paroi et les surplombs :** le déplacement suit la normale lissée de la paroi, et s'éteint là où il replierait la surface.
6. **Les ombres :** ombres de contact à l'écran sous les lèvres ; de loin, l'assombrissement moyen des creux, tiré du même champ.
7. **Seulement si le tremblement dépasse les critères :** une grille de proximité fixée sur la planète, en anneaux emboîtés et fondus, à la manière des geometry clipmaps. Le détail y est pris en des points fixes et ne tremble plus du tout.

## 2. Pourquoi nos essais ont échoué

**Trois problèmes distincts, mêlés dans chaque essai :** la forme, le filtrage et l'arrivée avec la stabilité. Le plan les sépare et mesure chacun.

### Le relief des matériaux dans le maillage, désactivé le 2026-10-23, retiré le 2026-10-30

- **Il tremblait.** Un relief pris aux sommets qui glissent est rééchantillonné à chaque image. L'erreur du triangle vaut environ 5·A/n² pour une onde de n mailles (`log/pistes-glissement.md`).
  - Filtré à 2 mailles : 0,17 avec lissage, contre 0,04 sans relief.
  - Filtré à 8 mailles : 0,06. Encore +50 %.
- **Des décisions non linéaires prises par sommet** faisaient sauter le relief d'un voisin à l'autre : mélange par la hauteur, projection à la puissance 8, neige décidée sur le relief. D'où lames et aiguilles.
- **Il surgissait.** Filtré à 8 mailles, il ne porte que les ondes de plus de 8 mailles.
  - Sur la face, une maille vaut l'altitude / 48 ; la plus courte onde portée, l'altitude / 6.
  - Une forme de 2 m de longueur d'onde naît donc vers 12 m d'altitude : c'est la corniche vue de 11 à 5 m.
  - À l'écran, 8 mailles font 56 à 100 pixels. Elle arrive grande.
- **L'état de l'art fait l'inverse :** CDLOD, clipmaps et Nanite prennent le détail en des points fixes du terrain, et le font naître à quelques pixels.

### Les parois en gradins, désactivées le 2026-10-23, retirées le 2026-10-30

- **Le gradin est une fonction non linéaire de `s`,** l'altitude moins le décalage des strates. Prise sur l'altitude interpolée entre sommets qui glissent, elle amplifie leur erreur de la pente de la falaise, trois fois celle de la paroi.
  - Gradins nets : 2,5 fois plus de tremblement. Arrondis sur 16 mailles : presque invisibles.
- **Une paroi n'a que deux ou trois sommets en hauteur :** le déplacement horizontal à la manière d'Outerra repliait la surface, en trous noirs et dents de scie.
- **Le bruit des ravines s'étirait depuis l'ancre** (`WallRelief`), qui saute de 64 m : le motif se redécoupait en vol. `principes.md` en garde la règle.
- **L'échelle :** des bancs de 10 à 60 m, au-dessus de 13,5 m. C'est un remplacement de complexplanet, pas un ajout de détail.

### Les corniches dans la lumière, retirées le 2026-10-24

- **La forme :** une fonction de `s` seule dessine des lignes de niveau. Chaque contremarche devient un trait sur toute la face, de force égale. C'est la règle « aucune structure d'un trait uniforme » enfreinte.
- **Le filtrage :** une contremarche plus fine que le pixel, dessinée en normale, donne un trait de largeur constante à l'écran, à toute distance : le feutre.
  - De loin, une marche ne doit pas se voir comme un trait mais comme une statistique : pente moyenne, rugosité, part ombrée. C'est le principe de LEAN et de LEADR, qui filtrent le relief en lumière sans le perdre.
- **L'effacement par la taille du pixel :** les marches s'effaçaient selon `ds`, le pas de `s` d'un pixel au suivant. Elles apparaissaient et disparaissaient avec la distance, contre la règle « un bruit ne s'efface jamais selon la taille du pixel ».
- **La parallaxe était la bonne technique de transition :** la corniche avait sa profondeur dès 11 m. Mais elle coûtait 0,8 à 1 ms et dessinait la même mauvaise forme.

### Notre concept a un nom dans la littérature

- **Le persistent grid mapping,** Livny et al. 2008 : une grille attachée à la caméra, projetée sur le sol, déplacée en hauteur par le terrain. C'est notre face glissante.
- **Son défaut connu :** les sommets glissent, sommets et crêtes scintillent.
- **Les remèdes publiés,** Houska 2020 : répartir les sommets pour choisir le bon niveau de filtrage, chercher les arêtes près de la caméra, la cohérence d'une image à l'autre. Ils réduisent le défaut sans le supprimer.
- **Notre propre calcul le confirmait :** aucune reconstruction ne stabilise les ondes de 2 à 3 mailles ; seul le filtrage les retire.

## 3. Les techniques comparées

### La continuité du niveau de détail

- **CDLOD,** Strugar 2010.
  - Un quadtree de grilles fixes. Chaque sommet se fond dans le niveau plus grossier sur les derniers 15 à 30 % de sa plage, selon sa propre distance.
  - Le relief est lu en des points fixes : aucun glissement.
  - Notre POC, `piste/sommets-fixes-etape3` : sans fente ni couture, mais coût variable, calcul 4 à 5 fois plus cher près du sol, 34 % d'images à-coups.
- **Geometry clipmaps,** Losasso et Hoppe 2004 ; sur GPU, Asirvatham et Hoppe 2005.
  - Des grilles emboîtées de taille fixe, centrées sur l'observateur, chacune calée sur son propre pas.
  - Une bande de transition au bord de chaque niveau fond la géométrie vers le niveau plus grossier.
  - Coût constant par construction.
  - Près du sol, Losasso et Hoppe synthétisent les niveaux plus fins par un bruit fractal : c'est exactement un ajout de détail.
  - Notre essai « par crans » calait toute la face par paliers, sans fondu : les paliers se voyaient.
- **Tessellation matérielle.**
  - Battlefield 3 : déplacement par le champ de hauteur en DX11 ; le facteur garde une largeur de triangle constante à l'écran.
  - Ghost of Tsushima : un terrain tessellé dynamiquement ; les rochers des falaises sont des modèles à part. Ghost of Yōtei : un système de tessellation du terrain, pour le détail et la neige déformable.
  - Le piège connu : un facteur fractionnaire fait glisser les nouveaux sommets, et le déplacement amplifie ce glissement. Un facteur entier fait sauter. Les remèdes : facteurs fixes ou fondu des sommets, déplacement filtré au pas de la découpe.
- **Far Cry 5 :** un pipeline GPU de choix du détail, de tri et de couture du champ de hauteur, qui accueille des falaises générées et de la géométrie de déplacement. Les falaises viennent d'outils Houdini. Les détails ne sont pas publics.
- **Nanite tessellation,** Unreal 5.4 ; Karis, « Nanite + Reyes », 2026.
  - Les patchs sont découpés jusqu'à un pas en pixels ; le déplacement est évalué à chaque sommet découpé.
  - La mesure d'erreur du choix de détail ignore le déplacement ; il est scalaire, borné par une plage donnée.
  - Les discontinuités franches étirent les triangles au-delà de 64 pixels et déchirent la surface.
  - Rien de publié sur la stabilité temporelle.
- **Virtual Heightfield Mesh,** Unreal : un quadtree lu dans une texture virtuelle de hauteur, avec une taille cible à l'écran. Expérimental, fait pour des données précalculées.
- **Arbres binaires concurrents,** Dupuy et al. 2020 ; Benyoub et Dupuy 2024 ; Unity 2021.
  - Une bisection adaptative sur GPU, découpée selon la longueur des arêtes à l'écran. Mise à jour en moins de 0,1 ms ; échelle planétaire, en double précision.
  - Unity : 256 triangles par feuille, des triangles jusqu'à 1,5 cm, du micro-déplacement des matériaux.
  - Un seul niveau de découpe par image : l'arbre est gardé d'une image à l'autre. Les sauts ne sont pas traités.
- **Mesh shaders,** DirectX 12 : des groupes de triangles générés sur le GPU sans tampon stocké. Une autre façon d'amplifier les mailles proches ; suppose un GPU DirectX 12 Ultimate.
- **Star Citizen :** parallaxe sur le terrain, fondu des objets dans le sol par la profondeur, détail réglé en polygones par pixel. Rochers et falaises sont des objets placés.
- **Outerra :** un déplacement fractal horizontal sur les pentes, selon la pente filtrée, de 19 à 76 m. L'auteur écrit qu'il ne fait pas encore de vraies parois de falaise ni de canyon.

| Technique | Naissance du détail | Stabilité | Coût | Avec notre face glissante |
|---|---|---|---|---|
| CDLOD | fondu continu par sommet | points fixes | variable avec le nombre de carreaux | POC clos : à-coups |
| Geometry clipmaps | fondu dans une bande par niveau | points fixes | constant | possible en couche de proximité ; couture à faire |
| Tessellation matérielle | facteur continu ou fondu | glisse si fractionnaire | modéré | possible, facteur fixe près de la caméra |
| Nanite tessellation | découpe au pas en pixels | non publiée | élevé, GPU | l'idée seule : découper au pixel, déplacer peu cher |
| Arbres binaires concurrents | découpe par pixels, un niveau par image | points fixes, sauts non traités | < 0,1 ms de mise à jour | état gardé : contraire au concept |
| Mailles amplifiées, proposé | 8 sous-mailles, 7 à 13 px | glisse avec la base, filtré | constant | direct : une grille par maille |
| Grille fixe de proximité, repli | fondu par distance | points fixes | constant | couture avec le maillage glissant |

### Déplacement vertical ou vectoriel

- **Un champ de hauteur n'a pas de surplomb.** Sur une paroi de pente m, un recul horizontal r équivaut à une hauteur r·m : un banc dur peut avancer, mais pas surplomber. Nos gradins faisaient ainsi.
- **Le déplacement le long d'une normale lissée,** sur 32 mailles au moins comme `RELIEF_NORMAL_CELLS` du relief des matériaux, retiré, fait des surplombs par rapport à la verticale, sans repli :
  - tant que le recul reste sous le rayon de courbure de la surface lissée ;
  - et tant que la paroi a assez de sommets en hauteur. Le maillage actuel n'en a que deux ou trois ; amplifié 8 fois, il en a 16 à 24.
  - Il s'éteint donc aux arêtes entre paroi et plateau, là où la courbure est forte.
- **Le déplacement triplanaire,** Weiss et al. 2020 : de la géométrie extrudée le long des pentes raides par tessellation, surplombs et blocs compris, sans triangulation explicite.
- **Les jeux livrés posent des objets :** rochers de falaise de Ghost of Tsushima, falaises procédurales de Far Cry 5, placement GPU d'Horizon Zero Dawn. C'est notre option des rochers semés, `log/spec-parois.md`, à garder pour plus tard.
- **Les outils hors ligne :** `Stratify` de Gaea casse les strates en plaques indépendantes, et non en terrasses.
- **Les matériaux restent décidés sur le terrain seul** (`principes.md`), jamais sur la part portée par le maillage.

## 4. Des corniches naturelles

### Ce que dit la géomorphologie

- **Les bancs durs tiennent en falaise, les bancs tendres en pente.** Grès et calcaires font les falaises ; les argiles, des pentes (NPS, Grand Canyon).
- **Le tendre creuse sous le dur :** il recule plus vite et sape le banc au-dessus. La lèvre avance en surplomb, puis tombe par blocs bornés par les diaclases (grès de Wingate).
- **Une falaise à banc dur recule au pas de son socle tendre,** et ses débris arment la pente en dessous (Ward et Anderson ; Howard).
- **Au pied, les éboulis :** un talus à l'angle d'éboulis, 34° chez nous, le `WALL_REPOSE` des gradins retirés. Il enterre le bas de la paroi et ses corniches.
- **Le long d'elle-même, une corniche varie :**
  - son avancée suit l'épaisseur du banc dur et le contraste de dureté, qui changent : les lentilles ;
  - les ravines la coupent en V ;
  - les diaclases la découpent en blocs, dont certains manquent, avec leur cicatrice ;
  - les replats portent débris et végétation.

### Les approches procédurales

- **Paris et al. 2019 :** une résistance de la roche ρ(p) fonction de l'altitude, donc en strates, déformée par plis et failles. L'érosion retire de la surface `f_D·(1 − ρ)` : la roche tendre recule, la dure avance. D'où falaises stratifiées et surplombs. Hors ligne, environ un million de requêtes par seconde.
- **Paris et al. 2020 :** des parois en blocs implicites bornés par les fractures.
- **Peytavie et al. 2009 :** des tas de pierres, donc des éboulis, par pavage apériodique.
- **Cordonnier et al. 2018 :** des couches profondes soulevées et érodées ; des strates plissées sur les falaises.
- **Jones et al. 2010 :** l'altération par courbure : alvéoles dans les creux, arrondi des bosses.

### Notre champ de corniche

**Un recul R(p), le long de la normale lissée de la paroi,** fixé sur la grille de la planète, jamais relatif à l'ancre.

- **La strate :** `s` = altitude lissée − `StrataShift`, comme les couleurs. Lissée sur quelques mailles, comme l'altitude des gradins, pour ne pas amplifier le tremblement de la base.
- **La dureté ρ(s) :** les bancs durs et tendres de la colonne, ceux de `PlaneDrop`. Les corniches tombent donc sur les bandes de couleur.
- **Le profil d'un banc :**
  - le dur avance en face presque verticale, sa lèvre arrondie sur 10 à 50 cm ;
  - le tendre recule en creux concave, le plus profond au tiers haut, sous la lèvre ;
  - moyenne nulle sur chaque banc : la paroi moyenne reste celle de complexplanet, et le relief garde sa hauteur moyenne.
- **La présence le long de la paroi,** un facteur w(p) entre 0 et 1, produit de :
  - les lentilles, `BedLenses`, déjà en place ;
  - un bruit le long des couches, de 8 à 64 m : la corniche forte ici, effacée là ;
  - des blocs de diaclases, un Voronoi dans le plan de la paroi, de 2 à 8 m : certains blocs tombés ;
  - les ravines : des bandes verticales où w tombe à 0, en V ;
  - l'enterrement sous les éboulis, au pied de la paroi.
- **L'amplitude :** une part de l'épaisseur du banc dur, 0,2 à 0,4, plafonnée à 2 ou 3 m. Nulle sur les pentes plus douces que l'angle d'éboulis.
- **L'échelle :** les bancs de 1 à 13 m. Les formations de 20 à 60 m restent couleur, ou remplacement sur leur piste.
- **La couleur suit le même champ :** creux plus sombres, coulures de vernis sous les lèvres, débris sur les replats.
- **Les règles d'irrégularité,** vérifiables :
  - aucune corniche ne garde la même avancée sur plus de 5 à 10 fois son épaisseur ;
  - elle s'amincit sur quelques fois sa largeur, jamais net ;
  - aucune ne traverse une paroi d'un trait.
- **De loin, le même champ en statistique :** pente moyenne nulle, sa variance en rugosité, sa part ombrée en assombrissement. Jamais un trait, jamais effacée selon le pixel.

## 5. Comment mesurer

### Ce que font les autres

- **Peu de protocoles publiés :** les articles sur Nanite et les arbres binaires concurrents ne chiffrent pas la stabilité temporelle.
- **Les outils publics :**
  - ꟻLIP, NVIDIA 2020 : la différence perçue en basculant entre deux images ;
  - ColorVideoVDP, Mantiuk et al. 2024 : la visibilité de défauts qui varient dans le temps ;
  - Schwarz et Stamminger 2009 : un prédicteur des sauts de détail, validé par une étude d'utilisateurs.
- **La pratique courante :** figer le niveau de détail, le balayer à caméra fixe, comparer les images. C'est le principe du banc d'arrivée.

### Nos bancs

1. **Le banc d'arrivée, nouveau.**
   - Caméra fixe ; `MYPLANETENGINE_FACE_FACTOR` = 2 × 2^(−k/8), k de 0 à 32 : quatre octaves de maillage.
   - Pour chaque pas, le changement relatif de la lumière du sol, après un flou de 8 pixels, comme la mutation du banc de qualité.
   - **Le saut :** le plus grand pas sur le pas médian. **La mutation :** la somme des pas. Et une carte de chaleur.
2. **Le banc de tremblement,** avec et sans lissage, sur six positions :
   - corniche, `2182.0 31.16045 8.58814 1.9 -17.1` et `2181.5 31.16051 8.58812 2.3 -11.8` ;
   - paroi très raide, `1391.1 -11.04542 50.06777 2.6 55.3` ;
   - roche rouge, `586.6 -25.21899 135.73187 -0.2 92.0` ;
   - montagne à 45°, `3756.3 -39.55694 12.77814 -13.1 -141.1` ;
   - paroi du papier peint, `2828.4 -0.03727 118.14886 -9.7 176.8` ;
   - paroi rasante, `1758.2 0.00182 118.14986 -10.9 81.8`.
   - Les climats ont changé le 2026-10-24, pas le relief : vérifier que ces parois sont toujours de la roche.
3. **Le banc de qualité :** mutation, segments droits, trous d'échelle, étalement.
4. **Le banc de descente :** l'altitude moyenne et la part de roche, de 800 à 8 km.
5. **La forme contre les photos,** nouveau dans le banc de qualité :
   - sur les crops de paroi à 30, 100 et 300 m, la longueur des segments sombres presque horizontaux, les creux, rapportée à la hauteur de la paroi ;
   - la même mesure sur `cible-falaise-alcoves.jpg`, `cible-gres-zion.jpg`, `cible-basalte.jpg`.
6. **Le coût,** calcul et rendu, à 3, 30 et 300 m.
7. **Le vol :** `MYPLANETENGINE_FLIGHT` le long d'une paroi, pour les à-coups, et un fichier `tools/tests/<date>.txt` d'approches à 300, 100, 30, 10 et 3 m sur cinq parois.

### Les critères proposés

- **Aucune apparition visible :**
  - au banc d'arrivée, aucun pas plus de 2 fois le pas médian de la référence, sur les six parois ;
  - mutation totale au plus +10 % sur la référence ;
  - les deux témoins doivent dépasser ces seuils. Sinon le banc n'est pas assez sensible, et on le revoit avant de juger.
- **Un scintillement pas au-dessus d'aujourd'hui :** au plus +5 % avec lissage, le bruit de mesure, et +10 % sans, sur les six positions.
- **L'aspect :** aucun p95 du banc de qualité dégradé de plus de 10 % (`AGENTS.md`) ; segments droits des vues de roche au plus ceux de la référence.
- **La cohérence :** altitude moyenne en descente à 1 % près, part de roche à 0,5 point près.
- **Les formes :** la distribution des longueurs de creux dans celle des photos ; aucun creux continu sur plus de la moitié de la largeur d'une paroi.
- **Le coût :** moins de 1 ms en tout près du sol.
- **En vol :** l'utilisateur juge les corniches « dessinées correctement », sans mutation au dernier moment, belles à toutes les approches.

## 6. Sources

**Continuité du niveau de détail**
- Strugar 2010, CDLOD, article et code : https://github.com/fstrugar/CDLOD
- Losasso et Hoppe 2004, Geometry clipmaps : https://hhoppe.com/proj/geomclipmap/
- Asirvatham et Hoppe 2005, GPU Gems 2, chapitre 2 : https://developer.nvidia.com/gpugems/gpugems2/part-i-geometric-complexity/chapter-2-terrain-rendering-using-gpu-based-geometry
- Livny et al. 2008, persistent grid mapping : https://link.springer.com/article/10.1007/s00371-007-0180-1
- Houska 2020, Improved Persistent Grid Mapping : https://www.cg.tuwien.ac.at/research/publications/2020/houska-2020-IPGM/
- Dupuy et al. 2020, Concurrent Binary Trees : https://diglib.eg.org/handle/10.1145/3406186
- Benyoub et Dupuy 2024, CBT for Large-Scale Game Components : https://arxiv.org/abs/2407.02215
- Deliot et al., Unity, SIGGRAPH 2021, tessellation du terrain par CBT : https://www.advances.realtimerendering.com/s2021/Siggraph21%20Terrain%20Tessellation.pdf
- Microsoft, mesh shaders : https://microsoft.github.io/DirectX-Specs/d3d/MeshShader.html

**Moteurs et jeux**
- Widmark 2012, Terrain in Battlefield 3 : https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/gdc12-terrain-in-battlefield3.pdf
- Moore 2018, Terrain Rendering in Far Cry 5 : https://gdcvault.com/play/1025261/Terrain-Rendering-in-Far-Cry
- Carrier 2018, Procedural World Generation of Far Cry 5 : https://gdcvault.com/play/1025557/Procedural-World-Generation-of-Far
- Pohlmann 2021, Samurai Landscapes, Ghost of Tsushima : https://gdcvault.com/play/1027352/Samurai-Landscapes-Building-and-Rendering
- PlayStation Blog, les effets de Ghost of Tsushima, terrain tessellé et rochers de falaise : https://blog.playstation.com/?p=345372
- PlayStation Blog 2025, Ghost of Yōtei, tessellation du terrain : https://blog.playstation.com/?p=411201
- van Muijden 2017, placement GPU d'Horizon Zero Dawn : https://www.guerrilla-games.com/media/News/Files/GDC2017_VanMuijden_GPUBasedProceduralPlacementInHorizonZeroDawn.pdf
- Karis 2026, Nanite + Reyes : https://graphicrants.blogspot.com/2026/02/nanite-reyes.html
- Epic, Nanite et les landscapes : https://dev.epicgames.com/documentation/unreal-engine/using-nanite-with-landscapes-in-unreal-engine
- Epic, Virtual Heightfield Mesh : https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/VirtualHeightfieldMesh/UVirtualHeightfieldMeshComponent
- Star Citizen, entretien avec Sean Tracy sur la parallaxe : https://gamersnexus.net/gg/2636-citizencon-parallax-occlusion-mapping-sean-tracy-interview
- Star Citizen, Planet Tech v5 : https://starcitizen.tools/Planet_Tech_v5
- Kemen 2009, Outerra, Horizontal fractal displacement : https://www.gamedeveloper.com/programming/horizontal-fractal-displacement
- Brevet US 10229536, déplacement et glissement des sommets en tessellation fractionnaire : https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10229536

**Falaises, déplacement vectoriel, filtrage**
- Weiss, Bayer et Westermann 2020, Triplanar Displacement Mapping : https://diglib.eg.org/handle/10.2312/egs20201016
- Paris et al. 2019, Terrain Amplification with Implicit 3D Features : https://hal.archives-ouvertes.fr/hal-02273097
- Paris et al. 2020, parois en blocs implicites : https://hal.archives-ouvertes.fr/hal-02926218
- Peytavie et al. 2009, tas de pierres : https://diglib.eg.org/handle/10.2312/CGF.v28i7pp1801-1809
- Cordonnier et al. 2018, Sculpting Mountains : https://hal.archives-ouvertes.fr/hal-01517343
- Jones et al. 2010, altération des roches par courbure : https://scholarsarchive.byu.edu/facpub/110
- Gaea, Stratify : https://docs.quadspinner.com/Reference/Erosion/Stratify.html
- Dupuy et al. 2013, LEADR mapping : https://perso.liris.cnrs.fr/victor.ostromoukhov/publications/pdf/SAsia2013-LEADR.pdf
- Bend Studio, ombres de contact à l'écran : https://www.bendstudio.com/blog/inside-bend-screen-space-shadows/

**Géomorphologie**
- NPS, la géologie du Grand Canyon : https://www.nps.gov/grca/planyourvisit/upload/life_geology.pdf
- Ward et Anderson, recul des falaises à banc dur : https://www.colorado.edu/program/hydrosciences/2018/08/23/retreat-rates-and-controls-form-hard-capped-cliffs-plateau-country
- Howard 2004, pentes du plateau du Colorado sous banc dur : https://gsa.confex.com/gsa/2004AM/webprogram/Paper75355.html
- Grès de Wingate, sapement et chutes par diaclases, source secondaire : https://moabhappenings.com/Archives/Geology202402-WingateSandstone.htm

**Mesure**
- Andersson et al. 2020, ꟻLIP : https://research.nvidia.com/labs/rtr/publication/andersson2020flip
- Mantiuk et al. 2024, ColorVideoVDP : https://arxiv.org/abs/2401.11485
- Schwarz et Stamminger 2009, prédire les sauts de détail : https://cris.fau.de/publications/118172384
