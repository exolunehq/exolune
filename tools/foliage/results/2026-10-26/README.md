# Campagne de végétation des 26 et 27 octobre 2026

**Lecture :** `docs/prototype-vegetation-volumique.md` donne le jugement et les limites.

**Résultats finaux :**
- `comparaison64.json` et `comparaison128.json` : six vues, deux modèles, trois tailles d'écran.
- `stress64.json` : 64, 256 et 1 024 instances demandées, deux modèles, deux représentations.
- `manifeste-final.json` : caméras, ancre et lumière de la comparaison finale.
- `provenance64.json`, `provenance128.json` et `provenance-stress64.json` : empreintes de l'exécutable, des shaders, des données et des bancs.
- `pieds.json` : douze cas de placement, sur deux lieux, à deux distances, pour 1, 16 et 1 024 instances demandées.
- `qualite.json` : contrôle avant/après sur les mêmes 24 lieux, prototype désactivé.
- `contexte.json` : matériel et protocole.

**Exploration :**
- `comparaison-initiale64.json` : vingt vues distinctes et quatre mouvements, avant les derniers correctifs.
- `binaire-initial.json` : empreintes des shaders et de l'exécutable de cette exploration.
- Les anciennes séries GPU restent dans `x64/FoliageComparaison64/rapport.json` ; l'export exploratoire conserve leurs statistiques.
- Les campagnes intermédiaires `FoliageFinal*` sont invalidées et exclues.

**Données locales :**
- `x64/FoliageValide64/` et `x64/FoliageValide128/` gardent les captures couleur, les masques, les mesures brutes et les planches.
- `x64/FoliageValideStress64/` garde les essais de charge.
- `x64/FoliageValidePieds/` garde les lectures GPU du placement.
- `x64/QualiteAvant/` et `x64/QualiteValideApres/` gardent les deux bancs de qualité complets.
- Ces sorties volumineuses sont ignorées par git ; les scripts permettent de les régénérer.

**Interprétation :**
- Les séries contiennent des images consécutives, pas des répétitions indépendantes.
- Le temps de dessin exclut le placement, le terrain et l'atmosphère.
- Les petites durées proches de zéro atteignent la résolution des horodatages GPU.
- Le nombre demandé ne signifie pas autant d'arbres visibles ; des pieds peuvent être hors de la zone couverte par le terrain.
- `triangles_par_instance` est le nombre de triangles du modèle source ; les deux proxies dessinent chacun deux triangles de support par instance.
- La mémoire de représentation décrit des formats non compressés, sans extrapolation à des imposteurs optimisés.
- La référence historique du banc de qualité n'est pas modifiée ; ses écarts déjà présents sont distingués des changements de ce prototype.
