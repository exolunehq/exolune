# Spécification : les brins d'herbe en géométrie

**Au log depuis le 2026-10-30 :** jamais faite. L'herbe proche est venue autrement : des touffes de 40 brins générés, parmi les objets de proximité, `../spec-objets-proximite.md`, étape 2.

Statut : proposée le 2026-10-21, révisée après la recherche de `etat-de-l-art-details.md`, à valider. Partie de l'étape E de `spec-rendu.md`, les détails à la surface. Fait suite à la texture d'herbe de l'étape D.

## Le but

**De vrais brins qui se dressent près de la caméra,** pour donner l'échelle au ras du sol.

- **La texture d'herbe de l'étape D** peint le sol : touffes, grain, teintes. Vue de haut, elle suffit.
- **En vue rasante, elle reste plate :** rien ne se dresse, rien ne se découpe sur le fond. C'est pourtant ce que l'œil prend pour repère d'échelle.
- **Les brins prolongent la texture,** sans la remplacer : mêmes touffes, mêmes teintes. De loin, la texture seule reste.

## Les deux approches

| | Brins en géométrie | Coques |
|---|---|---|
| **Principe** | Un calcul génère à chaque image les brins proches ; chacun est un petit ruban de triangles, dessiné par instances | Le sol proche est redessiné en 8 à 16 couches superposées ; chaque pixel d'une couche garde ou jette une section de brin |
| **Vue de haut** | Bien | Bien |
| **Vue rasante** | Brins dressés, silhouettes sur le fond | Les couches se séparent : piles de disques, pas de silhouette |
| **Scintillement** | Brins fins à tenir à au moins un pixel de large | Découpe au pixel près, scintille sous le lissage temporel |
| **Coût** | Proportionnel au nombre de brins | Proportionnel à la surface proche, multipliée par le nombre de couches |
| **Concept** | Tout par image, sans mémoire | Tout par image, sans mémoire |

**Recommandation : les brins en géométrie.** Seuls ils donnent l'échelle en vue rasante, là où elle manque. Les coques ne font guère mieux que la texture actuelle.

## Le principe retenu

### Une grille fixe sur la planète

**Chaque brin naît dans une case d'une grille fixe sur la planète :** les six faces d'un cube projetées sur la sphère, comme au POC des sommets fixes.

- **Indices exacts :** une face, puis deux entiers par case. Avec des cases de 3 cm, ils restent sous 2³¹.
- **Précision :** le processeur calcule en double le centre de la fenêtre de cases autour de la caméra ; le GPU travaille en décalages float depuis ce centre. Méthode et tangente en série reprises du POC, tag `piste/sommets-fixes-etape3`.
- **Chaque brin est tiré du hachage de sa case :** position dans la case, orientation, hauteur, largeur, courbure, teinte. Rien n'est stocké d'une image à l'autre : le même brin renaît au même endroit, identique.

### Où pousse l'herbe, et combien

- **Les brins naissent des touffes :** la densité suit le champ de touffes de la texture d'herbe, `TuftField` dans `PixelShader.hlsl`. Les brins se groupent en touffes, avec des pieds plus clairsemés entre elles.
- **Seulement là où la texture d'herbe est présente :** même poids que dans `GroundAt`, y compris le mélange par la hauteur avec la neige et la roche.
- **Même teinte que le sol en dessous :** la couleur du sol est évaluée au pied du brin, par la même fonction que les pixels du sol. Le pied prend cette couleur, la pointe tire vers le jaune-vert. Un brin qui s'efface laisse donc le sol de la même couleur.
- **Le sol sous l'herbe s'assombrit** selon la densité des brins, par la même fonction.

### L'éclaircissement avec la distance

**La densité baisse en continu avec la distance, sans palier.**

- **Chaque brin reçoit un rang au hasard,** entre 0 et 1. Il est gardé si son rang est sous la densité voulue à sa distance.
- **Un brin qui va disparaître rapetisse d'abord,** sur une petite marge de rang. Il ne saute pas.
- **Les brins lointains s'élargissent** pour rester à un pixel au moins, et ne pas scintiller. Moins de brins, plus larges, plutôt que de la transparence.
- **Au loin, la normale tend vers celle de la touffe :** les reflets ne scintillent plus.
- **Au-delà d'environ 30 m, plus de brins :** la texture seule, de même teinte moyenne.
- **Au-dessus de 30 m d'altitude, pas de brins du tout,** avec un fondu entre 20 et 30 m.

### Posés sur le sol dessiné

**Les brins doivent se poser exactement sur le sol qu'on voit,** qui est le maillage glissant.

- **Par inversion du maillage :** la position d'un brin sur la planète donne ses coordonnées dans la face ou dans un anneau, par le calcul inverse de celui des sommets. On lit les trois sommets du triangle qui le porte, et on interpole leur hauteur.
- **Pas de passe en plus,** et pas de mémoire.
- **Près de la caméra, le maillage a des mailles de quelques centimètres :** la hauteur glisse de moins d'un millimètre, sans tremblement visible.
- **Une carte de hauteur locale vue de dessus,** prévue d'abord, reste en réserve si l'inversion se révèle trop coûteuse.

### Le calcul et le dessin

1. **Un calcul par case** de la fenêtre autour de la caméra : il tire le brin, applique la densité, écarte les brins hors champ, et ajoute les autres à une liste.
2. **Un dessin indirect** des brins de la liste.

### La forme, d'après Ghost of Tsushima

- **Chaque brin est une courbe de Bézier,** réglée par sa hauteur, son inclinaison, sa courbure et son orientation, et s'affine vers la pointe.
- **Deux niveaux :** 15 sommets jusqu'à environ 15 m, puis 7. Le brin prend la forme simplifiée avant la bascule, sans saut.
- **Des touffes de Voronoï,** mêlées entre les deux centres les plus proches pour éviter les coutures. La touffe règle la hauteur, la teinte et l'orientation, et les brins penchent vers son centre.
- **De l'hétérogénéité :** plaques nues, brins secs ou à pointe brune selon un bruit d'humidité lent, 5 à 15 % pour commencer.

### L'éclairage

- **Normale courbe** le long du brin et en travers, pour qu'il s'éclaire comme un ruban arrondi.
- **Un brin vu par la tranche** s'épaissit un peu vers la caméra, pour ne pas disparaître.
- **Un reflet cireux** en vue rasante, en traînées le long du brin.
- **Translucidité :** un brin à contre-jour laisse passer une part de la lumière, teintée de vert.
- **Pied plus sombre :** occlusion simple, de la base vers la pointe.
- **Même chaîne que le sol :** haute dynamique, distance dans l'alpha pour l'atmosphère et le lissage temporel.
- **Pas d'ombres portées :** le moteur n'en a pas encore. Les ombres de contact à l'écran, de Bend Studio, viendront avec la roche.

### Le vent, en option

- **Une courbure qui ondule,** tirée d'un bruit fixe sur la planète qui défile avec le temps.
- **Le risque le plus fort :** le lissage temporel suppose une scène immobile, et un brin qui bouge laisse une traînée.
- **Le remède, peu coûteux :** chaque brin étant une fonction du hachage et du temps, on le recalcule à l'image précédente pour écrire son mouvement. Le lissage temporel doit alors lire ce mouvement par pixel. À faire avant le vent.

## Le budget

- **Moins de 1 ms à 2 m du sol,** en 1280 × 720.
- **Ordre de grandeur :** 50 000 à 100 000 brins visibles. Ghost of Tsushima dessinait environ 83 000 brins en 2,5 ms sur PS4 ; une carte de bureau actuelle devrait tenir 200 000 brins en 1 à 2 ms.
- **La limite sera le dessin des triangles fins,** pas le calcul : à mesurer tôt.
- **Rien quand la caméra est haute.**

## Les étapes

1. **Les brins immobiles,** sans éclairage soigné : grille, inversion du maillage, densité, éclaircissement.
2. **La forme et les touffes :** Bézier, deux niveaux, Voronoï, brins secs.
3. **L'éclairage :** normale courbe, translucidité, pied sombre, teinte du sol.
4. **Les réglages et les mesures :** densité, distances, coût.
5. **Le mouvement par pixel pour le lissage temporel,** puis le vent.

## La mesure

- **Le banc de tremblement et le banc de mutation,** sur des vues à 2 m et 10 m au-dessus de l'herbe. Les brins ne doivent ni trembler quand le maillage glisse, ni apparaître par vagues à l'approche.
- **Le coût GPU,** au pire, l'herbe couvrant tout l'écran.
- **Le jugement en vol,** au ras du sol et en descente.

## Critères de validation

- **L'échelle se lit en vue rasante :** brins dressés, silhouettes sur le fond.
- **Pas de palier visible** entre les brins et la texture, ni en vol ni en descente.
- **Pas de scintillement** des brins fins.
- **Coût :** moins de 1 ms au pire.
