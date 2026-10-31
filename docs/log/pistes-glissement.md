# Pistes : rendre le glissement invisible

Statut : pistes ouvertes le 2026-10-21, après la clôture du POC des sommets fixes (`spec-sommets-fixes.md`). Le concept est maintenu : un maillage qui glisse avec la caméra et s'adapte à chaque image.

## Le constat

**Les sommets ne tremblent pas : ils sont exacts.** Chacun porte la vraie élévation de son point de la planète, une valeur absolue.

- **Ce qui tremble, c'est la reconstruction entre les sommets.** Un pixel tombe presque toujours entre des sommets. Il voit le triangle, pas le relief.
- **Le triangle dépend de l'endroit où sont les sommets.** Quand le maillage glisse, le même point de la planète est reconstruit autrement à chaque image.
- **Conséquence :** on ne supprime pas le tremblement en changeant les échantillons. On le supprime en changeant la façon de reconstruire entre eux.

## Le principe mathématique

**Théorème de Shannon :** un signal dont les longueurs d'onde dépassent deux mailles est entièrement déterminé par ses échantillons, où qu'ils tombent. Reconstruit avec le noyau idéal, il ne dépend plus de la position de la grille.

- **Le glissement est donc invisible en théorie,** à deux conditions : un relief filtré sous la limite des deux mailles, ce que fait déjà le filtrage des octaves, et une reconstruction proche de l'idéale.
- **Le triangle est la plus mauvaise reconstruction possible :** une interpolation linéaire, le noyau en tente.
- **Erreur du triangle,** pour une onde d'amplitude A et de longueur n mailles : au milieu d'une maille, la hauteur reconstruite vaut A·cos(π/n) au lieu de A. Le tremblement vaut donc A·(1 − cos(π/n)), environ 5·A/n².
- **Erreur de la pente,** qui fait l'éclairage : elle est bien plus forte que celle de la hauteur. C'est pourquoi le tremblement se voit surtout dans la lumière.

## Les chiffres

Variation de la pente reconstruite en un point fixe quand la grille glisse, en part de la vraie pente ; entre parenthèses, la part de la pente restituée en moyenne. Calcul numérique sur une sinusoïde de n mailles de longueur d'onde.

| n mailles | Normale actuelle | B-spline lissante | Spline cardinale |
|---|---|---|---|
| 2 | 0 % (×0,00) | 17 % (×0,17) | 51 % (×0,50) |
| 3 | 10 % (×0,28) | 6,5 % (×0,47) | 13 % (×0,94) |
| 4 | 9,3 % (×0,52) | 2,9 % (×0,66) | 4,4 % (×0,99) |
| 8 | 3,4 % (×0,85) | 0,4 % (×0,90) | 0,4 % (×1,00) |

- **La normale actuelle** est calculée sur les sommets voisins, puis interpolée sur le triangle. Elle efface presque les ondes de 2 à 3 mailles, c'est pourquoi elles y tremblent peu.
- **La spline cardinale** passe par les sommets et restitue toute la pente, y compris celle des ondes de 2 à 3 mailles, qui tremble alors fortement.
- **La B-spline lissante,** sans préfiltre, tremble moins que la normale actuelle dès 3 mailles, tout en restant plus nette.
- **Pour la hauteur,** l'écart est plus grand encore : à 4 mailles, 0,9 % de variation pour la B-spline lissante contre 15 % pour le triangle.
- **Correction :** la première version de ce tableau donnait l'erreur maximale, qui mêle le biais stable au tremblement. Elle prédisait à tort que la spline cardinale serait la meilleure. Le banc l'a démentie, voir `spec-normales-spline.md`.

**Conséquence : aucune reconstruction ne stabilise les ondes de 2 à 3 mailles.** Seule la coupure du relief avant elles les supprime.

## Les pistes, dans l'ordre proposé

### 1. Normales par pixel, reconstruites en spline

**C'est la « formule » : la meilleure reconstruction pour le coût le plus bas.** Elle vise l'éclairage, qui porte l'essentiel du tremblement.

- **Une passe de calcul après le terrain** applique le préfiltre aux positions des sommets, ligne par ligne puis colonne par colonne. Aucun bruit n'est réévalué.
- **Chaque pixel reçoit ses coordonnées dans la grille du maillage,** interpolées depuis les sommets. Il lit les 4 × 4 sommets voisins et en tire la surface spline, puis sa normale par les deux dérivées.
- **Résultat au banc,** avec la B-spline lissante : 12 à 16 % de tremblement en moins. Détails dans `spec-normales-spline.md`.
- **Coût attendu :** 16 lectures et quelques multiplications par pixel, sans bruit. Bien moins cher qu'une évaluation du relief par pixel.
- **La difficulté : le paramétrage du maillage.**
  - La face est une grille régulière : rien à signaler.
  - Les anneaux sont réguliers dans leurs coordonnées, numéro d'anneau et position sur l'anneau, mais cassés aux coins des carrés.
  - Entre la face et le premier anneau, les deux grilles ne se prolongent pas.
  - Premier jet : revenir à la normale actuelle, en fondu, à deux mailles des coins et du bord de la face.
- **Mesure :** le banc de tremblement sans lissage temporel, sur les vues de montagne et de plaine, puis le jugement en vol.

### 2. Relief par pixel, reconstruit en spline

**La même surface spline, appliquée aussi à la géométrie :** les silhouettes et la profondeur.

- **Le pixel corrige sa profondeur** par une ou deux itérations de Newton entre le rayon de vue et la surface spline. L'écart au triangle est petit, de l'ordre de l'erreur du tableau.
- **Les silhouettes :** le maillage doit être légèrement gonflé pour que la surface spline ne dépasse jamais du triangle.
- **À ne faire que si,** après la piste 1, le tremblement des silhouettes reste visible.

### 3. Régler la bande du relief

**Les ondes de 2 à 3 mailles tremblent quelle que soit la reconstruction.**

- **Aujourd'hui,** une octave est entière jusqu'à 4 mailles et s'éteint à 2 mailles.
- **Réglage `MESH_BAND_LIMIT` :** la longueur d'onde la plus courte gardée, en mailles.
- **Mesuré au banc, avec la spline :** une coupure à 4 mailles divise le scintillement par deux.
- **Jugé en vol :** la forme mute davantage à l'approche, car chaque détail naît plus près. Coupure laissée à 2 mailles. Scintillement et mutation s'échangent : le banc doit mesurer les deux.

### 4. Réécriture : des anneaux circulaires

**Des cercles qui grandissent en progression géométrique,** à la place des carrés.

- **Un paramétrage lisse partout :** plus de coins, donc la spline s'applique sans exception hors du centre.
- **Le zoom sans rééchantillonnage :** dans ces coordonnées, changer d'altitude est une translation le long des anneaux. Avec une échelle choisie par crans du facteur de croissance, environ 1 %, l'anneau k tombe exactement sur l'anneau k + 1.
- **La translation horizontale rééchantillonne toujours :** aucune grille n'est à la fois invariante par zoom et par translation.

### 5. Réécriture lourde : le relief calculé par pixel

**L'idée limite : chaque pixel évalue le relief à son propre point,** par lancer de rayon affiné depuis le maillage.

- **Le glissement disparaît par construction :** l'échantillon est le pixel, et le filtrage à la taille du pixel rend le reste invisible avec le lissage temporel.
- **Le coût est le verrou :** environ un million de pixels contre cent mille sommets, et plusieurs évaluations du bruit complet par pixel. Soit 30 à 40 fois le calcul actuel.
- **Préalable :** un bruit bien moins cher que complexplanet. Une piste de recherche en soi.

## Déjà écartées

- **L'aimantation par crans,** tag `piste/aimantation-crans` : des sauts visibles à chaque cran.
- **Les sommets fixes,** tag `piste/sommets-fixes-etape3` : stables, mais un coût variable qui saccade le vol.
- **Une mémoire du relief en espace planète,** lissée d'image en image : contraire au calcul intégral à chaque image.

## Proposition

**Commencer par la piste 1,** sur le seul plan glissant, mesurée au banc avant et après. C'est elle qui promet le plus de gain pour le moins de changements, sans toucher au calcul du relief.
