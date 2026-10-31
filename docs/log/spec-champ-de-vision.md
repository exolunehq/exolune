# Spécification : couvrir le champ de vision, puis optimiser

Statut : à valider avant implémentation dans le POC. Fait suite au jet 1 décrit dans `concept.md`.

## Le problème

**Plus on descend, moins la face couvre le champ de vision.** Sa demi-largeur vaut k × la hauteur au-dessus du sol. Elle couvre donc le dessous de la caméra, jamais l'horizon.

- À 10 km d'altitude avec k = 4, la face couvre ±40 km. L'horizon est à 357 km.
- Les montagnes dépassent l'horizon : un sommet de 8 km reste visible jusqu'à 323 km au-delà, soit √(2 R H).

**Objectif :** de 1 m à environ 5 000 km d'altitude, couvrir tout le champ de vision jusqu'à l'horizon, montagnes comprises. Le détail à l'écran doit rester à peu près constant, pour un coût maîtrisé.

## Axe 1 : couvrir le champ de vision

### Solution retenue : la face, prolongée par des anneaux géométriques

**On garde la face du jet 1 au centre, et on l'entoure d'anneaux carrés de plus en plus grands.** Tout reste dans le même plan, avec la même rotation et la même normalisation sur la sphère.

- Chaque anneau est un peu plus grand que le précédent : la taille de maille croît proportionnellement à la distance au centre.
- Les anneaux s'arrêtent à l'horizon, plus la marge des montagnes.
- C'est la version continue de la « pile de faces de taille ×2 » proposée au point 3 de `concept.md`.

**Pourquoi c'est économique :** à l'écran, une maille occupe toujours à peu près le même angle, près comme loin, quelle que soit la direction du regard.

- Un seul maillage, un seul calcul, un seul affichage.
- Pas de couture à traiter : chaque anneau se raccorde au précédent sommet par sommet.

**Coût estimé** avec une face de 129 × 129 et des anneaux de 512 sommets :

| Hauteur au-dessus du sol | Anneaux | Sommets au total |
|---|---|---|
| 1 m | 775 | 413 000 |
| 10 km | 228 | 134 000 |
| 300 km | 88 | 62 000 |

Pour comparaison, la face actuelle de 257 × 257 compte 66 000 sommets.

### Règles de construction

| Élément | Règle |
|---|---|
| Face centrale | Demi-largeur s0 = k × hauteur au-dessus du sol, avec k ≈ 2. Grille de (n + 1) × (n + 1), n = 128. |
| Anneau i | Demi-largeur s0 × (1 + 2/n)^i, avec 4n sommets. Les mailles restent à peu près carrées. |
| Rayon extérieur | Arc jusqu'à l'horizon + 323 km de marge pour les montagnes, ramené dans le plan : R × tan(arc / R). |
| Nombre d'anneaux | ln(rayon extérieur / s0) / ln(1 + 2/n). Le maillage est construit une fois pour le maximum ; on n'affiche que les anneaux nécessaires. |

### Condition indispensable : filtrer les octaves selon la taille de maille

**Sans filtrage, les anneaux lointains scintillent.** Leurs mailles font des kilomètres, alors que complexplanet contient des détails de quelques centaines de mètres. Chaque sommet tombe au hasard sur un détail plus fin que sa maille. L'horizon grésille et tout le relief ondule quand on se déplace.

**Règle :** chaque sommet n'évalue que les octaves dont la longueur d'onde dépasse deux mailles. La dernière octave retenue s'estompe progressivement, pour éviter les sauts.

- Le calcul d'élévation reçoit la taille de maille du sommet.
- Chaque générateur arrête sa boucle d'octaves à cette limite, turbulences comprises.
- Bonus pour l'axe 2 : les anneaux lointains coûtent beaucoup moins cher.

**Limite connue :** complexplanet n'est pas linéaire, à cause des sélecteurs, des terrasses et des courbes. Vu de loin, le relief filtré diffère un peu du relief complet. Le fondu garde la transition continue.

### Placement par rapport au regard (ancien jet 2)

**Recommandation : abandonner le décalage de la face vers le point regardé.**

- Avec les anneaux, la densité à l'écran est déjà uniforme dans toutes les directions. Décaler le centre n'apporterait presque rien.
- Le décalage ferait bouger le maillage à chaque mouvement de tête, et donc scintiller le relief.

Le regard compte vraiment à deux endroits :

- **Le zoom.** Quand le champ de vision se resserre, on diminue k et on augmente n pour affiner le détail.
- **Ce qui est hors champ.** On évite de le calculer : c'est le premier chantier de l'axe 2.

### Hors périmètre

- **Au-dessus d'environ 5 000 km d'altitude**, la calotte visible dépasse ce qu'un seul plan peut couvrir, environ 60° autour du nadir. Il faudra une sphère complète grossière en arrière-plan.
- Atmosphère, textures, éclairage réaliste.

### Critères de validation

1. De 1 m à 5 000 km, regard à l'horizon dans toutes les directions : aucun vide entre le sol et l'horizon.
2. Les montagnes lointaines apparaissent au-dessus de l'horizon.
3. Aucune fissure dans le maillage.
4. La taille des mailles à l'écran reste à peu près constante, vérifiée en fil de fer.
5. En vol à vitesse constante, l'horizon ne scintille pas.
6. La fréquence d'images est mesurée aux vues de référence de l'axe 2. Ces mesures servent de point de départ à l'axe 2.

### Étapes d'implémentation

1. **Mesurer avant de changer :** temps GPU du calcul et de l'affichage, affichés dans le titre.
2. **Face et anneaux, sans filtrage :** valider la couverture et l'absence de fissures.
3. **Filtrage des octaves :** valider la stabilité de l'horizon et du relief.
4. **Mesures** aux altitudes de référence.

### Résultats de l'implémentation

**L'axe 1 est implémenté**, avec k = 2 et n = 128.

| Critère | Résultat |
|---|---|
| 1. Aucun vide jusqu'à l'horizon | Vérifié en image fixe à 1 m, 69 m, 10 km, 300 km et 2 000 km. |
| 2. Montagnes lointaines | Leur silhouette dépasse l'horizon dès 1 m de hauteur. |
| 3. Aucune fissure | Vérifié en fil de fer à la jonction entre la face et les anneaux. |
| 4. Taille des mailles à l'écran | À peu près constante du premier plan jusqu'au loin. Près de l'horizon, les mailles se tassent sous l'effet de la perspective rasante : c'est attendu. |
| 5. Pas de scintillement en vol | Filtrage des octaves en place, à vérifier en vol : une image fixe ne le montre pas. |
| 6. Mesures | Ci-dessous. |

**Mesures** au-dessus de 15° S, 50° E, regard à 3° sous l'horizon puis à 80°. Le temps de rendu reste sous 0,1 ms : tout le coût est dans le calcul du terrain.

| Hauteur au-dessus du sol | Anneaux | Calcul GPU | Images par seconde |
|---|---|---|---|
| 1 m | 795 | 15 ms | 54 à 62 |
| 100 m | 499 | 11 ms | 70 |
| 10 km | 230 | 6 ms | 131 à 140 |
| 300 km | 88 | 2,4 ms | 272 à 276 |
| 2 000 km | 27 | 0,7 ms | 280 |

Le regard ne change rien au coût : tout le maillage est calculé, même hors champ. C'est la première piste de l'axe 2.

## Axe 2 : performances

**Principe :** on part des mesures de l'axe 1. On s'attaque d'abord au poste le plus coûteux, et chaque optimisation est mesurée avant et après.

### Contraintes

- **Toute la géométrie visible est recalculée à chaque image.** C'est ce qui permet de se déplacer à n'importe quelle vitesse sans attendre de chargement. Aucune optimisation ne doit casser ce principe.
- **Le relief doit rester planétaire et crédible**, avec des formes qui rappellent la Terre. Toute simplification du bruit passe par une comparaison visuelle.

### Cible

**Calcul du terrain : 3 ms au plus dans la pire vue de référence, idéalement 2 ms.** Aujourd'hui, c'est 15 ms au ras du sol. Le reste du budget ira aux shaders de rendu à venir : éclairage, atmosphère, textures.

**Vues de référence :** au-dessus du continent à 15° S, 50° E, à 1 m, 100 m, 10 km, 300 km et 2 000 km de hauteur, avec le regard à 3° sous l'horizon puis à 80°.

### Protocole de qualité

Pour chaque changement qui touche au bruit :

1. Captures des vues de référence avant et après, par la capture intégrée au moteur.
2. Comparaison côte à côte, avec l'écart moyen d'altitude.
3. Validation à l'œil. Si le relief change de caractère, la décision te revient.

### Étapes, par gain attendu

1. **Ne calculer que ce qui est dans le champ de vision.** Le calcul saute les sommets hors du champ, avec une marge de deux mailles. Un sommet est testé avec toute sa plage d'altitude possible, du niveau de la mer à 8 192 m. Ainsi, une montagne qui entre dans le champ par le haut est toujours calculée. Le sommet sous la caméra est toujours calculé : il donne la hauteur du sol. Gain attendu : 3 à 4 fois en regardant l'horizon, bien plus en regardant vers le bas.
2. **Mesurer le coût de chaque couche de complexplanet**, en les neutralisant une à une. On saura ainsi où porter l'effort. Les turbulences sont suspectes : elles représentent environ les deux tiers des octaves.
3. **Simplifier les couches de bruit qui coûtent le plus**, selon le protocole de qualité. Les pistes à tester :
   - **Un bruit de base plus rapide**, par exemple un bruit de gradient sans table, ou un simplex, qui interpole 4 points au lieu de 8.
   - **Moins d'octaves dans les turbulences.** Leurs dernières octaves déforment très peu le relief.
   - **Le type de terrain sans recalculer les continents.** Aujourd'hui, il réévalue toute la chaîne des continents en un second point.
   - **L'océan simplifié.** Sous le niveau de la mer, la surface est plate : seule la profondeur colore l'eau.
4. **Alléger le calcul en double précision.** Le double n'est utile que pour les octaves fines, d'une longueur d'onde inférieure à quelques centaines de mètres. Les octaves plus larges peuvent passer en float sans perte visible.
5. **En dernier recours, rafraîchir moins souvent les anneaux lointains**, à deux conditions : jamais au-delà d'une vitesse donnée, et seulement si aucun retard n'est visible.
6. **Adapter n au budget** : réduire la finesse du maillage si une image dépasse son temps.

### Résultats de l'axe 2, en cours

**Le pire cas est passé de 15,1 à 1,6 ms**, sous la cible idéale de 2 ms. Toutes les vues sauf le ras du sol sont sous 0,3 ms. Le détail de chaque réglage est dans `journal-planete.md`.

| Étape | Résultat |
|---|---|
| 1. Champ de vision | Fait. Pire cas de 15,1 à 7,6 ms, aucun trou sur les bords de l'image. |
| 2. Coût des couches | Fait, au ras du sol, regard à l'horizon. Turbulences : ~72 % du coût. Second calcul des continents pour le type de terrain : ~51 %. Double précision : ~20 %. Ces parts se recouvrent. |
| 3a. Type de terrain filtré | Fait. Ses octaves sont limitées à une longueur d'onde de ~100 km. Pire cas de 7,6 à 4,6 ms. |
| 3b. Table de gradients en mémoire partagée | Fait. Les lectures de la table à des indices dispersés coûtaient cher en mémoire constante. Rendu identique au pixel près, de 16 à 50 % de gain selon la vue. |
| 4. Double précision près de la caméra seulement | Fait. Le double ne sert qu'aux sommets dont la maille fait moins de 4 m ; plus loin, l'imprécision du float, 0,4 m, reste invisible. Jusqu'à 70 % de gain selon la vue. |
| 3c. Turbulences des continents plafonnées à 1024 | Fait, validé. Pire cas de 3,2 à 2,8 ms. Seul le contour fin de quelques côtes change : 0,2 % des pixels sur la vue de côte, rien ailleurs. |
| 3d. Turbulence vectorielle | Fait, validé en vol. Les trois axes d'une turbulence en un seul bruit : pire cas de 2,8 à 1,6 ms. La forme exacte des taches de roche et des ondulations change, sans différence remarquée à l'œil. |

Chaque étape faite a été comparée sur six vues : deux au-dessus du continent de départ, une vue d'orbite, un autre continent et deux vues de côte. L'écart moyen est resté sous 0,13 sur 255, sans aucun pixel changé de plus de 8 niveaux.

**Mesures après ces étapes**, au-dessus de 15° S, 50° E :

| Hauteur au-dessus du sol | Regard à l'horizon | Regard vers le bas |
|---|---|---|
| 1 m | 1,5 ms | 1,6 ms |
| 100 m | 0,3 ms | 0,3 ms |
| 10 km | 0,1 ms | 0,1 ms |
| 300 km | 0,1 ms | 0,0 ms |
| 2 000 km | 0,0 ms | 0,0 ms |

## Alternatives écartées

| Solution | Pourquoi elle est écartée |
|---|---|
| Pile de faces imbriquées, de taille ×2 | Densité qui saute d'un facteur 2 entre niveaux, coutures à traiter. À densité minimale égale, environ deux fois plus de sommets que les anneaux. |
| Arbre quaternaire sur un cube fixe, la méthode standard du jeu vidéo | Les morceaux de terrain sont fixés sur la planète et mis en cache : c'est la plus performante. Mais elle abandonne le principe d'une face qui suit la caméra, recalculée à chaque image. À garder en réserve si l'axe 2 ne suffit pas. |
| Une seule face, plus grande | À 10 km d'altitude, il faudrait près de 90 000 sommets par côté pour garder le détail sous la caméra. |
