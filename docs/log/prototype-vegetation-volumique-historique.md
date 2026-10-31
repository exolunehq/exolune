# Historique du prototype de végétation volumique

**2026-10-26 : filtrage des volumes.** L'état présent est dans `prototype-vegetation-volumique.md`.

**L'essai écarté :** additionner les surfaces de feuilles dans chaque parent, puis appliquer une loi de Poisson isotrope.
- Les feuilles déjà cachées contribuaient encore comme si elles étaient toutes visibles.
- Le couvert grossissait avec la simplification.
- L'audit CPU compare 60 projections orthographiques du même modèle.
- Il intègre la couverture attendue des rayons ; il ne mesure aucun temps GPU.

**Rapport moyen d'aire projetée, hiérarchie issue du 128³ :**

| Modèle | Niveau | Somme des surfaces | Transmission des enfants |
|---|---:|---:|---:|
| Sapin | 64³ | 1,10 | 1,04 |
| Sapin | 32³ | 1,22 | 1,06 |
| Sapin | 16³ | 1,36 | 1,08 |
| Sapin | 8³ | 1,50 | 1,10 |
| Jacaranda | 64³ | 1,05 | 1,02 |
| Jacaranda | 32³ | 1,12 | 1,04 |
| Jacaranda | 16³ | 1,24 | 1,06 |
| Jacaranda | 8³ | 1,43 | 1,09 |

**Le choix :** filtrer la transmission de deux enfants le long du rayon, puis moyenner les quatre colonnes et les extinctions des trois axes.
- Le niveau de base reste inchangé.
- La couverture moyenne s'améliore, sans coefficient propre à une vue.
- Le pire rapport d'aire, sur tous les niveaux et angles, descend de 2,77 à 1,61.
- La moyenne isotrope reste imparfaite selon l'angle.
- Au niveau 32³, le jacaranda vu du dessus passe de 0,991 à 0,917.
- Sur le sapin au niveau 8³, l'intersection/union douce passe de 0,477 à 0,453, malgré une erreur absolue moyenne réduite de 0,0649 à 0,0576.

**Les premières captures fonctionnelles :**
- Les trois modes et le masque binaire fonctionnent.
- Les statistiques de pipeline vérifient les 2 518 432 triangles de 16 sapins.
- Ces captures ont été faites pendant le banc de qualité initial.
- Leurs temps GPU sont écartés de la comparaison finale.

**L'interpolation des pieds, remplacée :**
- Le premier prototype interpolait les quatre sommets d'une maille.
- Le maillage dessine deux triangles ; les surfaces ne coïncident pas exactement.
- L'audit sur les deux lieux trouve moins de 0,008 pixel d'écart dans les cas de 16 arbres.
- L'erreur en mètres croît avec la taille de la maille au loin.
- La version retenue rencontre directement le triangle suivant la droite de l'ancrage planétaire.
- Un premier correctif trouvait 0,097 mm sur huit cas, mais omettait les arbres seuls sur une frontière de maille.
- Le test strict des coordonnées du triangle rejetait alors certains pieds à quelques millionièmes de la frontière.
- Les campagnes `FoliageFinal64`, `FoliageFinal128` et `FoliageFinalStress64` sont invalidées ; les masques d'arbres seuls étaient vides.
- Le correctif retenu rencontre les deux triangles et les mailles voisines, sans déplacer l'ancre.
- Les captures de régression couvrent deux modèles, deux lieux, un arbre ou seize, en couleur et en masque.
- Le banc refuse désormais toute référence vide, avant ses statistiques et ses planches.
- Les grands écarts de projection de l'audit initial à 1 024 arbres très proches incluent des pieds hors écran et presque au plan caméra ; ils ne mesurent pas un défaut visible.

**Reproduction :** `tools/foliage/audit.py` et `tools/foliage/filtre_transmission.py` ; les fichiers intermédiaires restent sous `x64/FoliageAssetsAudit/`.

**2026-10-27 : revue avant la campagne finale.**
- La première marche volumique appliquait une longueur complète au dernier pas, même s'il dépassait la boîte.
- Le dernier segment est borné à la longueur réellement traversée avant les mesures finales.
- La profondeur est cumulée au milieu du segment, comme la matière échantillonnée, au lieu de son début.
- Les résultats de la première campagne restent exploratoires ; ils ne remplacent pas les mesures finales du code corrigé.
