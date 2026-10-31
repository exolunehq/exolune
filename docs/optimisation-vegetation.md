# Optimisation des performances de la végétation

**Statut : premières optimisations intégrées à main le 2026-10-27 ; phase à poursuivre.**
- Base validée en l'état : `jalon/24-vegetation-detaillee-main`.
- Point de départ de la phase : `piste/vegetation-optimisation-base`.
- Intégration : `jalon/25-vegetation-performance-main`.
- Le HiZ et la profondeur matérielle sont détaillés dans `vegetation-hiz.md`.

**Le culling déjà en place :**

| Étape | Travail évité | Source |
|---|---|---|
| Relief | Sommets hors du volume visible, avec marges pour les normales, les vagues et les ombres | `TerrainCompute.hlsl`, `Terrain.hlsli::MaybeVisible` |
| Bruit de relief | Octaves invisibles à la maille et branches de terrain dont le poids est nul ; moyenne conservée | `Noise.hlsli`, `Relief.hlsli` |
| Placement | Tuiles hors champ, hors portée ou sans support de sol ; rejet avant le sol exact et les bruits lourds | `PlantPlacement.hlsli::CullPlantTile` |
| Plantes individuelles | Taille projetée, finesse du support et présence ; choix maillage ou proxy | `PlantPlacement.hlsli`, `PlanetFoliageClassify.hlsl` |
| Dessin | Commandes indirectes vides ignorées sur GPU et test de profondeur | `PlanetFoliage.cpp` |

- La passe suivante `vegetation-hiz.md` ajoute une pyramide de profondeur courante pour éviter le travail des imposteurs entièrement cachés par le terrain ou les maillages proches.
- Les imposteurs reconstruisent leur profondeur dans le pixel shader ; le test de profondeur n'économise donc pas nécessairement tout leur travail de pixel.
- Le feuillage est double face ; aucun rejet général des faces arrière n'est activé.

**Première passe :**
- Les angles, indices de vues et sinus/cosinus déjà calculés par le vertex du proxy sont transmis sans interpolation.
- Le pixel shader réutilise ces bases pour les quatre vues ; il ne recalcule plus leurs fonctions trigonométriques.
- Le placement, les scans, le maillage proche, le découpage alpha, la profondeur et les seuils restent ceux de la base validée.
- Les essais de compaction et de déplacement de l'atmosphère sont dans `log/optimisation-vegetation-historique.md`.
- Une mesure dédiée sépare le placement des plantes de leur classification ; l'ancien champ `placement` du sidecar désigne toujours la classification.
- Ces deux horodatages supplémentaires sont réservés aux captures batch ; le vol conserve les douze horodatages de la base.

**Protocole :**
- Référence et candidat ont la même instrumentation GPU ; sources et binaires sont figés sous `x64/VegetationPerf/`.
- `tools/banc_arbustes_climat.py` : quatorze vues, six familles climatiques ; série sur GPU libre avec 32 images de chauffe et 128 mesures par vue.
- Le temps de la mer est figé à `0 0` pour les comparaisons ; les applications de vol sont fermées pendant les mesures.
- Images, comptes par modèle et dépassements sont comparés sur les mêmes poses, soleils et assets.
- Le banc général reprend six lieux fixes, un par matériau et cinq hauteurs, avec la référence canonique inchangée et une comparaison appariée entre les deux binaires.
- Les exports d'identité sont distincts de la mesure de temps, pour éviter le trafic de readback.

**Le vol de comparaison :** son lanceur, qui ouvrait les binaires figés de la version retenue et de sa référence, est retiré le 2026-10-30 ; il est décrit dans `log/optimisation-vegetation-historique.md`.

**Résultat de cette passe :**
- Quatorze images identiques pixel à pixel ; mêmes comptes par modèle et famille, sans dépassement ; assets identiques.
- Sur les forêts denses mesurées, le dessin passe de 6,28 à 5,97 ms en boréal, de 11,05 à 10,78 ms en tempéré et de 8,93 à 8,38 ms en tropical.
- Les petits peuplements ne montrent pas de gain stable ; le temps total reste variable, notamment avec les autres rendus actifs. Aucun nombre de FPS n'est garanti.
- Le banc général termine les six lieux : 744 PNG sur 745 sont identiques ; un seul pixel diffère d'un niveau sur 255.
- Aucun p95 apparié ne régresse de plus de 10 % ; la référence canonique et les limites héritées restent inchangées.
- Synthèse conservée : `../tools/foliage/results/2026-10-27/optimisation.json`.
- Le placement demeure le prochain chantier ; les scans expérimentaux n'ont pas été livrés.
- **Suite le 2026-10-28 :** `optimisation.md`, round 3. Le sol exact des tuiles gardé d'une image à l'autre, les imposteurs en profondeur conservatrice, les maillages en profondeur d'abord.

**Ce qui doit être conservé :**
- L'aspect accepté des arbres et des douze arbustes climatiques.
- La densité, la distance d'affichage, les graines et les positions.
- Les mélanges climatiques et la stabilité à caméra immobile.
- Le relais entre maillage, imposteur et canopée.

**Les mesures à établir d'abord :**
- Profil GPU du placement, de la classification et du dessin, séparé du terrain et de la mer.
- Coût CPU, mémoire GPU résidente, chargement et préparation des mipmaps.
- Comparatifs appariés sur les mêmes poses, soleils et populations, sans charge GPU concurrente.
- Parcours au sol, en lisière et en approche aérienne, sur les six familles climatiques.
- Temps médians et p95 par passe ; budget cible à décider après cette référence isolée.

**Les axes à examiner :**
- Réduire les pixels transparents traités et les recouvrements des cartes de feuillage.
- Ajouter ou simplifier les niveaux de détail des maillages proches, à couverture et silhouette équivalentes.
- Ajuster les représentations intermédiaires et les mipmaps des imposteurs, sans réduire leur portée.
- Mutualiser les textures et données communes aux variantes ; mettre en cache la préparation hors ligne.
- Réduire les réservations et transferts des files bornées, sans sélection instable ni perte d'instances.
- Mesurer les appels de dessin et leur regroupement avant toute nouvelle modification.

**La référence de coût connue :**
- Six régions d'instances : 192 Mio.
- Buffers de représentation : 729 760 876 octets, hors files et mémoire temporaire.
- Les douze arbustes ajoutent environ 445 Mio face au catalogue précédent.
- Les chronométrages précédents subissent des charges concurrentes ; ils ne garantissent pas un budget de FPS.

**La vérification de la phase :**
- Un changement à la fois, avec avant/après sur plusieurs lieux et comptage des instances.
- Le banc `tools/banc_qualite.py --before tools/banc_qualite_reference.json` reste la référence générale.
- La base a été acceptée visuellement malgré les écarts documentés dans `vegetation-planetaire.md` et `arbustes-climatiques.md`.
- Ces écarts restent des limites de qualité ; ils ne sont ni effacés ni requalifiés en problèmes de performance.
- Aucun changement de référence ou de métrique ne doit masquer une régression.
