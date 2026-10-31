# Spécification : stabilité de la géométrie

Statut : l'aimantation par crans a été testée puis abandonnée. Le tremblement est mesuré : il vient de l'éclairage. Essai en cours : la pente sur les voisins et le grain fin dans les pixels. Fait suite à `spec-champ-de-vision.md`.

## Le problème

**En vol, le relief tremble. Ce n'est pas un problème de précision : c'est le maillage qui glisse sur le relief.**

- **Diagnostic :** la touche G fige le maillage pendant que la caméra continue d'avancer. Le tremblement disparaît.
- **Mécanisme :** la face et les anneaux suivent la caméra en continu. D'une image à l'autre, chaque sommet atterrit à un endroit où il n'y avait pas de sommet. Il échantillonne le relief en un autre point, et la surface entre les sommets change.

Trois causes s'additionnent :

1. **Le plan tourne en continu** pour rester face à la caméra : toute la grille glisse quand on se déplace.
2. **La taille de la grille suit la hauteur au-dessus du sol.** En rase-mottes, chaque bosse la change, et toute la grille se redimensionne.
3. **Le filtrage des octaves garde des reliefs de 2 à 4 mailles**, qui ondulent dès que la grille bouge.

## La solution : aimanter la grille

**Principe : la grille ne bouge que par crans, choisis pour que les sommets retombent sur d'anciens sommets.** Entre deux crans, rien ne bouge. Le concept reste intact : le plan regarde toujours la caméra et il est toujours normalisé en sphère.

### 1. Le plan tourne par crans d'une maille

- **Le plan garde son orientation tant que la caméra reste à moins d'une demi-maille du centre de la face**, mesuré sur le plan.
- **Au-delà, il tourne pour se recentrer sur le sommet de la grille le plus proche de la caméra.** Les sommets du carré central retombent alors exactement sur les positions de leurs voisins, à une erreur négligeable près.
- **Le plan suit donc la caméra avec au plus une demi-maille de retard.** À 50 m de hauteur, c'est 75 cm.
- **La rotation transporte le repère du plan sans le faire tourner sur lui-même.** Le repère n'est plus calé sur le nord : ça évite que la grille pivote d'un cran à l'autre.

### 2. La taille change par crans de croissance des anneaux

- **La demi-largeur de la face ne prend que des valeurs (1 + 2/n)^m mètres**, avec m entier. Quand m change d'un cran, chaque anneau retombe exactement à la place de son voisin.
- **Une hystérésis d'un quart de cran** évite d'osciller entre deux valeurs.
- **La hauteur au-dessus du sol utilisée pour la taille est lissée** sur une demi-seconde. La caméra, elle, reste toujours protégée par la hauteur réelle du sol.

### 3. Les anneaux sont filtrés plus sévèrement

- **Les anneaux ne peuvent pas être aimantés en déplacement :** centrés sur un point qui bouge, leurs sommets ne retombent jamais sur d'anciens sommets.
- **Ils ne gardent donc que les reliefs d'au moins 4 mailles**, au lieu de 2, avec une pleine intensité au-delà de 8. Un relief large change très peu quand la grille glisse d'une fraction de maille.
- **La transition se fait sur les 16 premiers anneaux**, pour éviter une rupture de détail au bord du carré central.
- **Le carré central garde le filtrage actuel :** il est aimanté, il peut garder son détail.

### Pour comparer en vol

**La touche H active ou désactive toute la stabilisation**, sans recompiler. Le titre de la fenêtre l'indique.

## Limites connues

- **En montée ou en descente, le carré central saute légèrement à chaque cran de taille.** Son bord retombe sur l'ancien premier anneau, mais ses sommets intérieurs se déplacent, jusqu'à une maille près du bord.
- **Les anneaux glissent encore un peu** à chaque cran de déplacement, d'une fraction de maille d'autant plus petite qu'ils sont loin.
- **Le repère du plan n'est plus calé sur le nord.** Sur un long trajet, il tourne lentement sur lui-même, sans effet visible.

## Critères de validation

1. En vol horizontal à basse altitude, plus de tremblement visible dans le carré central.
2. Dans les anneaux, tremblement résiduel faible, à juger à l'œil avec H.
3. En survolant des bosses, la grille ne se redimensionne plus en permanence.
4. Pas de coût mesurable sur le calcul GPU.

## Résultat du test : abandonné

- **Constat en vol :** plus de tremblement dans le carré central, mais des changements de géométrie par paliers. Hors du carré, le tremblement restait.
- **Le filtrage plus sévère** lissait trop le relief sans supprimer le tremblement.
- **Le fond du problème :** le glissement continu du plan est ce qui densifie le maillage progressivement, sans couture. L'aimanter le transforme en niveaux de détail à paliers. On garde donc le glissement continu.

## Mesure du tremblement

**Le banc de mesure : la caméra reste immobile, et le maillage est placé comme si elle volait.** Le relief est fixe sur la planète : toute différence entre deux images successives est du tremblement, et rien d'autre.

- **Lancement :** `MYPLANETENGINE_TREMBLE=préfixe`, avec `MYPLANETENGINE_TREMBLE_SPEED` pour la vitesse (1 par défaut). Après 60 images de mise en route, l'application enregistre 24 images puis quitte.
- **Mesure :** l'écart moyen entre images successives sur les pixels de terrain, sur 255. Témoin : maillage figé, écart nul.
- **Vues :** 50 m vers l'horizon, 50 m vers le bas, 10 km vers l'horizon.

| Variante | 50 m horizon | 50 m bas | 10 km horizon |
|---|---|---|---|
| Facettes | 0,63 | 0,68 | |
| Normale du relief, pas d'un quart de maille | 0,43 | 0,43 | 0,79 |
| Pas d'une maille | 0,25 | 0,28 | 0,50 |
| Pas de deux mailles | 0,15 | 0,17 | 0,34 |
| Sans éclairage | 0,00 | 0,00 | 0,12 |

**Conclusion : le tremblement vient presque entièrement de l'éclairage.** Le glissement de la géométrie elle-même ne se voit presque pas.

- **Pourquoi :** la pente varie bien plus vite que la hauteur. Échantillonnée en des sommets qui glissent, sa part fine, de 2 à 4 mailles, change d'une image à l'autre.
- **Une pente mesurée sur deux mailles ne tremble presque plus**, mais elle perd le grain fin de l'éclairage.

## Mesure de la mutation

**Le banc de tremblement ne voit que le scintillement rapide, d'une image à l'autre.** La mutation est lente : à l'approche, la maille rétrécit, et chaque octave apparaît dans le relief quand elle couvre la coupure `MESH_BAND_LIMIT`. Plus la coupure est haute, plus le détail naît près de la caméra, donc grand à l'écran.

- **Même banc que le tremblement :** caméra immobile, maillage placé comme si elle volait. En avançant, il rétrécit les mailles devant la caméra, comme à l'approche.
- **Lancement :** `MYPLANETENGINE_TREMBLE_FRAMES=64`, vitesse 1. Le maillage avance d'environ 1,07 fois la hauteur au-dessus du sol. Lissage temporel actif.
- **Mesure :** après un flou de 8 pixels, pour ne garder que les formes, l'écart moyen sur les pixels de terrain entre la moyenne des 8 dernières images et celle des 8 premières, sur 255. La moyenne sur 8 images atténue le scintillement.
- **Bruit de mesure :** le même écart entre les images 9 à 16 et 1 à 8.
- **L'ancienne mesure ne convient pas :** comparer l'image à celle d'une face 8 fois plus petite ne raffine que la face. Dans les anneaux, la maille ne dépend que de la distance au nadir.

### Résultats : la coupure du relief

**La mesure confirme le vol : plus la coupure est haute, plus le premier plan mute.** Banc du 2026-10-21, spline lissante active.

| Coupure | Scintillement sans lissage, montagne 10 km | Mutation, montagne 50 m | Mutation, montagne 10 km | Mutation, plaine 10 km |
|---|---|---|---|---|
| 2 mailles | 1,01 | 0,19 | 0,79 | 0,05 |
| 3 mailles | 0,69 | 0,21 | 0,76 | 0,05 |
| 4 mailles | 0,51 | 0,25 | 0,77 | 0,05 |

- **Bruit de mesure :** 0,07 à 0,08 en montagne à 50 m, 0,17 à 0,20 à 10 km, 0,02 en plaine.
- **Au premier plan, la mutation double :** sur le tiers bas de l'image, à 50 m, de 0,17 à 0,36 entre 2 et 4 mailles. Scintillement et mutation s'échangent : la coupure à 4 mailles divise l'un par deux et double l'autre.
- **À 10 km, la mutation ne dépend pas de la coupure.** Elle vient du terrain entre 20 et 120 km, forte avec les trois coupures. Cause à chercher : les turbulences des continents et l'arrondi des arêtes suivent aussi la maille.
- **Le masque de terrain du banc compte le ciel depuis l'atmosphère :** les moyennes sont diluées, mais restent comparables entre variantes.

## Essai en cours : la pente sur les voisins, le grain fin dans les pixels

### 1. La pente vient des sommets voisins

- **Le vertex shader calcule la normale par différences centrées** entre les positions des quatre sommets voisins : le long de la ligne et en travers, ou le long de l'anneau et entre anneaux voisins.
- **Écart de deux mailles :** la stabilité du pas de deux mailles, sans aucune évaluation du relief en plus. Le calcul retrouve son coût d'avant les normales.
- **L'éclairage colle à la géométrie dessinée**, puisqu'il vient des mêmes sommets.
- **Un voisin éliminé par le cadrage est remplacé par le sommet lui-même.** La marge du cadrage passe de 2 à 3 mailles, pour que les sommets visibles gardent leurs voisins.

### 2. Le grain fin est dessiné dans les pixels

- **Un bruit léger, calculé pixel par pixel en coordonnées fixes de la planète**, perturbe la normale. Il ne bouge pas avec le maillage, donc il ne tremble pas.
- **Il ne couvre que ce que la normale des sommets ne voit pas :** les longueurs d'onde de moins de 8 mailles. Il s'efface en dessous de deux pixels, pour ne pas scintiller.
- **Les deux bornes glissent en continu** avec la taille des mailles et la distance : pas de palier.
- **Précision :** le pixel calcule sa position par rapport à une ancre proche de la caméra, entière en unités de 64 m. Les indices du réseau du bruit restent exacts à l'échelle de la planète.
- **Pas de grain sur la mer**, qui reste plate.
- **Seulement là où complexplanet a du relief fin :** entre 13,5 m, son octave la plus fine sur terre, et 6 km. Un premier essai sans ces bornes inventait un relief rugueux sur les plaines.
- **Réglage :** `DETAIL_SLOPE` dans `PlanetSettings.hlsli`, la pente ajoutée par octave. 0 désactive le grain.

### Critères de validation

1. Tremblement mesuré au banc au niveau du pas de deux mailles ou en dessous.
2. Grain fin de l'éclairage comparable au pas d'un quart de maille, sur images côte à côte.
3. Calcul GPU revenu vers 1,6 ms ; rendu en hausse de moins de 0,5 ms.

### Résultats

**Le tremblement baisse de 43 à 67 % selon la vue, et le calcul de 4,9 à 1,9 ms au pire.** Détail et images : `journal-planete.md`.

- **Critère 1 :** proche au-dessus du continent de départ, 0,22 contre 0,15 pour le pas de deux mailles. Montagne à 10 km : de 17,6 à 6,6, le reste vient surtout de la couleur roche ou neige.
- **Critère 2 :** atteint au-dessus du continent de départ, grain mesuré à 3 % près. En montagne, arêtes plus douces : 9 % de grain en moins à 50 m, 38 % à 10 km.
- **Critère 3 :** 1,9 ms, à cause de la marge de cadrage élargie. Rendu : 0,11 ms au plus.
- **Grain mesuré :** écart type de la luminance après un flou de 2 pixels, sur le terrain, loin des silhouettes.

## Écarté

**Les grilles fixées sur la planète** : clipmaps, CDLOD, Proland, CBT. Elles suppriment le glissement, mais abandonnent le plan qui regarde la caméra, cœur du concept.

**Les grilles imbriquées** : la transition entre niveaux serait trop abrupte et difficile à masquer.

## Bilan : y a-t-il une limite infranchissable ?

**Oui, mais elle tient au glissement du maillage, pas au recalcul à chaque image.**

- **Le mécanisme :** un maillage qui glisse échantillonne le relief en d'autres points à chaque image. Entre les sommets, la surface reconstruite change, donc l'image aussi. C'est une propriété de l'échantillonnage, pas un défaut de précision.
- **Ce qui le rend visible :** les arêtes vives du bruit, ridged et billow, sont infiniment fines. Aucune grille ne les échantillonne sans erreur. Une grille fixe garde une erreur fixe, invisible ; une grille qui glisse la déplace à chaque image.
- **Ce qu'on peut faire sans changer de méthode :** abaisser ce plancher, sans l'annuler.

| Levier | Effet mesuré, montagne à 10 km | Coût |
|---|---|---|
| Normale sur les sommets voisins | de 17,6 à 6,6 | gain de calcul |
| Lissage temporel | de 3,4 à 0,62 | négligeable |
| 192 mailles par côté | de 0,62 à 0,46 | calcul × 2,2 |

- **Un contournement non essayé :** arrondir les arêtes vives à l'échelle de la maille, avec une valeur absolue adoucie, d'autant plus douce que la maille est grande. Le relief échantillonné n'a plus de détail plus fin que la grille, donc presque plus rien à faire trembler. Les arêtes se raffermissent en continu à l'approche, sans palier. Coût négligeable.
- **La solution de fond, si le plancher reste gênant :** des sommets fixés sur la planète, par exemple sur les six faces d'un cube, avec un fondu des hauteurs entre niveaux de détail, à la manière de CDLOD.
  - On garde le recalcul de tout à chaque image, sans mémoire, donc pas de rattrapage ni de limite de vitesse.
  - On perd le plan qui regarde la caméra.
- **Une géométrie statique recalculée en arrière-plan n'est pas nécessaire :** elle ajouterait mémoire et rattrapage, pour une stabilité que les sommets fixes obtiennent sans eux.

## Essai : arrondir les arêtes à l'échelle de la maille

- **Où :** la valeur absolue des bruits Billow et RidgedMulti, qui crée les creux et les crêtes vives.
- **Comment :** sous un seuil ε, la valeur absolue devient une parabole qui la rejoint sans cassure. Au-dessus, rien ne change : pas de biais sur le reste du relief.
- **ε suit la maille du sommet,** pour chaque octave : ε = `CREASE_ROUNDING` × fréquence de l'octave / fréquence maximale du sommet. L'arête est arrondie sur environ une maille de large, quelle que soit sa longueur d'onde.
- **Sans palier :** la maille rétrécit en continu à l'approche, ε aussi, et l'arête se raffermit.
- **Réglage :** `CREASE_ROUNDING` dans `PlanetSettings.hlsli`, 0 le désactive.
- **Mesure :** banc de tremblement en montagne et en plaine, images, coût. Plusieurs valeurs comparées.

### Résultats

**L'arrondi divise le tremblement par 2,5 en montagne, sans coût.** Tremblement sur l'image entière, avec et sans le lissage temporel :

| Arrondi | Montagne, 50 m | Montagne, 10 km | Plaine, 10 km |
|---|---|---|---|
| 0, arêtes vives | 0,06 / 0,21 | 0,46 / 3,02 | 0,02 / 0,14 |
| 0,5 | 0,05 / 0,20 | 0,34 / 2,37 | 0,01 / 0,13 |
| 1 | 0,05 / 0,19 | 0,26 / 1,88 | 0,01 / 0,11 |
| 2 | 0,04 / 0,17 | 0,17 / 1,20 | 0,01 / 0,08 |

- **En images :** à 10 km, l'arrondi 2 adoucit un peu les crêtes ; de près, presque rien ne change, les mailles y étant petites.
- **Coût :** aucun, dans le bruit de mesure.
- **Retenu : 2,** jugé un peu mieux en vol, gain léger.

