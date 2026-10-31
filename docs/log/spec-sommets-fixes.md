# Spécification : POC des sommets fixes (CDLOD)

Statut : clos après l'étape 3, tag `piste/sommets-fixes-etape3`. Le concept garde le plan glissant : voir la conclusion en fin de document. Fait suite au bilan de `spec-stabilite.md`.

## Le but

**Supprimer le tremblement à la racine :** chaque sommet échantillonne toujours le même point de la planète.

- **Le plan glissant** fait échantillonner le relief en d'autres points à chaque image : c'est la cause du tremblement, mesurée et documentée dans `spec-stabilite.md`.
- **Ce POC remplace seulement le placement du maillage.** Tout le reste est gardé tel quel :
  - le bruit complexplanet, recalculé pour chaque sommet à chaque image ;
  - l'atmosphère, les matériaux, le lissage temporel, l'arrondi des arêtes.
- **Pas de mémoire, pas de rattrapage, pas de limite de vitesse :** comme aujourd'hui, tout est recalculé à chaque image.
- **Comparaison directe en vol :** une touche bascule entre le plan glissant et les sommets fixes, avec le même terrain et le même éclairage.

## Le principe : la méthode CDLOD

Référence : Strugar 2009, *Continuous Distance-Dependent Level of Detail for Rendering Heightmaps*. Adaptée ici à une sphère et à un relief procédural.

### Le cube et ses carreaux

- **Six faces fixes d'un cube,** projetées sur la sphère. Une déformation en tangente égalise la taille des mailles entre le centre et les coins d'une face.
- **Chaque face est un arbre de carreaux :** un carreau se divise en quatre carreaux deux fois plus petits. Profondeur jusqu'à environ 24 niveaux, pour des mailles de l'ordre du centimètre au sol.
- **Chaque carreau est une grille de 64 × 64 mailles,** quel que soit son niveau. Seule sa taille change.

### Le choix des carreaux, à chaque image

- **Le processeur parcourt l'arbre** depuis les six faces.
- **Un carreau est divisé** quand la caméra est assez proche pour que ses mailles deviennent trop grandes à l'écran. Les seuils de distance doublent d'un niveau au suivant.
- **Il est écarté** s'il est hors du champ de vision ou derrière l'horizon, en tenant compte des plus hauts sommets possibles.
- **Densité :** au pire, celle d'aujourd'hui, environ 7 pixels par maille. Réglable par un facteur de distance.
- **Coût visé :** moins de 0,1 ms de processeur.

### Le fondu de hauteur

**C'est lui qui rend les changements de niveau invisibles.** Les sommets ne bougent jamais à l'horizontale.

- **Dans chaque carreau, on distingue deux sortes de sommets :**
  - les sommets pairs, qui existent aussi dans le carreau parent, plus grossier ;
  - les sommets impairs, qui n'existent qu'à ce niveau.
- **Un sommet impair est tiré vers la surface grossière :** la moyenne de ses deux voisins pairs, prise en position 3D, sur l'arête ou la diagonale du triangle parent.
- **Le facteur de fondu dépend de la distance du sommet à la caméra :**
  - 0 près de la caméra : vraie hauteur ;
  - 1 à la limite du niveau : posé sur la surface grossière ;
  - entre les deux, il varie en continu.
- **Le bruit est toujours évalué au point fixe du sommet,** jamais au point fondu : rien ne glisse.
- **Le filtrage des octaves suit le fondu :** la taille de maille effective passe en continu de celle du niveau à celle du parent. À la limite du niveau, le carreau et son voisin plus grossier calculent donc exactement les mêmes hauteurs, sans fente à la jonction.
- **Les diagonales des triangles** sont orientées de la même façon à tous les niveaux. Ainsi, une fois entièrement fondu, un carreau coïncide exactement avec son parent.

### Les normales et les bords

- **La normale vient des sommets voisins,** comme aujourd'hui.
- **Chaque carreau calcule une rangée de sommets de plus tout autour,** non dessinée. Ses sommets de bord ont ainsi leurs voisins, identiques à ceux du carreau adjacent du même niveau.
- **Les arêtes du cube :** les carreaux de deux faces voisines partagent les mêmes points de la sphère sur l'arête commune.

### La précision

**Même méthode qu'aujourd'hui : pas de grands nombres soustraits en float.**

- **Le centre de chaque carreau** est calculé en double sur le processeur, en direction sur la sphère et en position relative à la caméra.
- **Le décalage d'un sommet par rapport à ce centre** est calculé en float, avec des formules qui ne soustraient pas deux nombres proches.
- **Le bruit reçoit** le centre en double plus ce décalage, comme le compute shader actuel le fait avec le nadir.

### Le calcul et le dessin

- **Un seul dispatch de compute pour tous les carreaux retenus :** une liste de carreaux avec centre, axes, niveau et seuils de fondu, puis 67 × 67 sommets par carreau : 65 × 65 dessinés, plus la rangée de bord.
- **Un seul appel de dessin,** instancié : une grille d'indices commune, et un décalage de sommets par carreau.
- **Le vertex shader et le pixel shader** reçoivent les mêmes données qu'aujourd'hui, dont la taille de maille, ce qui garde le grain fin et les matériaux.

## Ce qui change pour l'utilisateur

- **Touche M :** bascule entre le plan glissant et les sommets fixes. Le titre de la fenêtre indique le mode.
- **`MYPLANETENGINE_MESH=fixed`** démarre en sommets fixes, pour les captures et le banc.
- **Le banc de tremblement :** la caméra reste immobile, et le choix des carreaux se fait comme si elle volait. C'est l'équivalent exact du banc actuel.

## Les étapes

1. **Le cube et les carreaux, sans fondu ni rangée de bord :** valider la géométrie, la précision et le choix des carreaux. Les fentes aux jonctions de niveaux sont attendues à ce stade.
2. **Le fondu de hauteur :** les fentes et les sauts doivent disparaître.
3. **Les normales,** avec la rangée de bord.
4. **Le banc de tremblement en sommets fixes,** puis les mesures.
5. **Le réglage de la densité et du coût.**

## Critères de validation

1. **Tremblement au banc** nettement sous celui du plan glissant, sans lissage temporel, sur les vues de montagne et de plaine.
2. **Pas de fente visible** aux jonctions de niveaux ni aux arêtes du cube.
3. **Pas de saut visible** quand un carreau se divise ou se regroupe. Seule la montée progressive du relief fin à l'approche est acceptée.
4. **Coût :** calcul GPU au pire comparable à aujourd'hui, au plus deux fois plus. Processeur sous 0,1 ms.
5. **Jugement en vol,** avec la bascule entre les deux modes.

## Ce qu'on perd

- **Le plan qui regarde la caméra,** et sa densification parfaitement continue. Elle est remplacée par des niveaux qui doublent, adoucis par le fondu.
- **Si le POC est retenu,** le plan glissant pourra rester comme mode de comparaison, puis être retiré.

## Précisions de l'étape 2

- **Le fondu couvre toute la plage d'un niveau :** de la distance où le carreau se diviserait, 1,25 fois sa taille, à celle où son parent se regrouperait, 2,5 fois. Chaque sommet évolue ainsi à chaque image pendant toute l'approche.
- **Distance mesurée au sol sous la caméra,** comme pour le choix des carreaux. Un carreau gardé a tous ses sommets au-delà de son seuil de division, son voisin plus grossier tous les siens au-delà du seuil de regroupement : à leur jonction, le fin est entièrement fondu.
- **Taille de maille ne dépendant que du niveau :** R × π/2 / (64 × 2^niveau). La déformation en tangente garde la vraie taille à 6 % près. Deux carreaux voisins filtrent ainsi exactement pareil leurs sommets communs.
- **La maille effective ne dépend que de la distance :** distance / (64 × 1,25), jamais sous la maille du carreau. Elle fixe les octaves du bruit, et le fondu : un sommet d'un niveau de grille commence à fondre quand la maille effective atteint celle de ce niveau, et l'est entièrement quand elle vaut le double.
- **Le fondu est imbriqué :** à la jonction, le carreau grossier est lui-même en partie fondu vers son parent. Le carreau fin doit donc reproduire ce fondu sur ses sommets du niveau grossier.
  - Chaque carreau fond tous ses niveaux de grille, du pas de 64 mailles au pas d'une maille, du plus grossier au plus fin.
  - Un sommet est tiré vers le milieu de ses deux voisins de la grille deux fois plus lâche, tels qu'ils sont déjà dessinés.
  - La surface dessinée ne dépend ainsi que du point et de sa distance : deux carreaux dessinent pareil leurs points communs, quels que soient leurs niveaux.
- **Les passes de calcul :** la première évalue les vraies hauteurs. Puis une passe par niveau de grille, sept pour 64 mailles, écrit le maillage dessiné.

## Précisions de l'étape 3

**Défaut vu en vol à l'étape 2 :** une couture d'éclairage le long des bords des carreaux. Chaque carreau calculait la normale de ses sommets de bord avec ses seuls sommets, donc d'un seul côté.

- **La rangée de bord doit être fondue comme le reste.** Le fondu d'un sommet à une maille du bord demande ses voisins de la grille deux fois plus lâche, donc un sommet à deux mailles, qui demande lui-même un sommet à quatre mailles, et ainsi de suite.
- **Des rangées à 1, 2, 4 et 8 mailles de chaque bord,** non dessinées. Chacune ne porte que les sommets de son niveau : tous les 1, 2, 4 et 8 sommets. Soit 496 sommets de plus par carreau, 12 % de calcul en plus.
- **La rangée à 8 mailles n'est pas fondue.** C'est exact tant qu'un carreau ne s'étend pas sur plus de trois niveaux de distance, ce que garantit le choix des carreaux.
- **Entre deux niveaux, les normales des bords se raccordent aussi :** le petit carreau y est entièrement fondu, et ses différences centrées tombent sur les mêmes triangles que celles du grand carreau.

## Les jointures en T

**À un changement de niveau, un petit carreau a deux fois plus de sommets sur le bord commun que son grand voisin.** Ses sommets en plus ne sont reliés à rien de l'autre côté : c'est une jointure en T. Si leur hauteur diffère de celle du bord du grand carreau, une fente s'ouvre.

- **Ce que fait l'étape 2 :**
  - au contact d'un voisin plus grossier, d'un niveau ou plus, les niveaux de grille plus fins du petit carreau sont entièrement fondus : ses sommets en plus sont placés au milieu exact de leurs deux voisins, donc sur le bord du grand carreau ;
  - ses autres sommets sont aux mêmes points que ceux du grand carreau, avec les mêmes hauteurs, grâce au filtrage qui suit le fondu.
- **Ce qui peut rester :** même posé exactement sur le bord, un sommet en T peut laisser des fentes d'une fraction de pixel, par les arrondis du rasteriseur.
- **Les remèdes classiques, si elles se voient :**
  - des jupes, petits murs verticaux le long des bords des carreaux, qui bouchent les fentes par en dessous ;
  - ou une couture : retrianguler le bord du petit carreau pour supprimer les jointures en T.

## Résultats de l'étape 1

- **Géométrie :** les carreaux se rejoignent, de l'orbite jusqu'au sol. Seules restent quelques fentes aux changements de niveau, attendues avant le fondu.
- **Défaut trouvé et corrigé :** la tangente du GPU n'est précise qu'à environ 1e-6 en valeur absolue, soit 1 % d'erreur pour les petits angles des carreaux fins. Chaque carreau était 1,5 % trop petit, d'où une fente d'une maille entre tous les carreaux. Remplacée par son développement en série.
- **Choix des carreaux :** la plage de hauteur d'un carreau est estimée autour du sol sous la caméra, plus ou moins une part de sa taille. Prendre 0 à 8 km pour tous divisait tous les petits carreaux proches jusqu'au centimètre.
- **Coût, encore trop élevé :**

| Vue | Carreaux | Calcul, sommets fixes | Calcul, plan glissant |
|---|---|---|---|
| Montagne, 10 km | 116 | 1,4 ms | 0,3 ms |
| Plaine, 50 m | 299 | 5,7 ms | 1,2 ms |
| Sol, 1 m | 446 | 12,3 ms | 3,3 ms |

- **Pourquoi :** un carreau à moitié visible est calculé en entier, quand le plan glissant écarte chaque sommet hors champ. À traiter à l'étape 5 : carreaux plus petits, écart des sommets hors champ dans le compute shader.

## Résultats des étapes 2 et 3

- **Plus de fente ni de couture visible,** de 10 km à 50 m, en plein comme en fil de fer.
- **Le relief fin monte en continu à l'approche,** sans saut au découpage d'un carreau.
- **Coût du calcul en vue plongeante :** 1,6 ms en montagne à 10 km, 6,2 ms en plaine à 50 m.

## Conclusion : la fluidité

**Jugé en vol : le vaisseau semble ralentir puis réaccélérer.** Mesuré par un vol automatique en ligne droite, `MYPLANETENGINE_FLIGHT`, vitesse ×5 :

| Vol | Mode | Durée d'une image | Images à-coups | Calcul GPU |
|---|---|---|---|---|
| Montagne, 800 m | Plan glissant | 3,6 ms, régulière | 0,5 % | 0,8 ms |
| Montagne, 800 m | Sommets fixes | 12 ms, de 3,6 à 23 ms | 34 % | 7,5 ms, jusqu'à 17 |
| Plaine, 70 m | Plan glissant | 3,6 ms, régulière | 0 % | 0,7 ms |
| Plaine, 70 m | Sommets fixes | 8,5 ms | 1,5 % | 5,2 ms |

- **Le coût suit le nombre de carreaux retenus,** qui varie avec le relief et la vue : de 179 à 417 sur le vol en montagne. Une image qui dépasse la période de l'écran attend le rafraîchissement suivant : le mouvement saccade.
- **Le plan glissant calcule toujours le même nombre de sommets :** coût constant, images régulières. C'est la force du concept.
- **Cause secondaire :** la vitesse suit la hauteur au-dessus du sol, calculée ici avec toutes les octaves. Elle saute jusqu'à 22 % d'une image à l'autre, contre 5 % pour le plan glissant.
- **Décision :** le POC reste sur sa branche, et on revient au plan glissant. Ses acquis réutilisables : le fondu imbriqué, la tangente en série et le vol automatique.
