# Arbustes climatiques

**Statut : validé en l'état par l'utilisateur le 2026-10-27 ; seuil du banc qualité non satisfait.**
- Suite de `vegetation-planetaire.md` ; base `piste/arbustes-climatiques-base`, sur le commit de départ.
- Intégration sur `main`, jalon `jalon/24-vegetation-detaillee-main`.
- L'acceptation visuelle autorise cette intégration avec les écarts de banc consignés ; elle ne change ni la métrique ni sa référence.
- La phase d'optimisation des performances est différée : `optimisation-vegetation.md`.

**La diversité :**

| Famille | Port et feuillage | Hauteur relative à l'instance |
|---|---|---:|
| Boréale | Touffes basses irrégulières, petites feuilles | 0,65 |
| Désertique | Fourches latérales, bouquets espacés gris-vert | 0,85 |
| Steppe | Rameaux étalés, feuillage fin, quelques tiges dressées | 0,60 |
| Montagne et toundra | Bras horizontaux, petites feuilles en couvert bas | 0,30 |
| Tempérée | Touffes feuillues ramifiées, plusieurs lobes et percées | 1,00 |
| Tropicale | Tiges décalées, grandes feuilles alternes courbées | 1,15 |

- Deux architectures par famille ; la variante et l'orientation viennent de la graine stable.
- Les douze modèles ont 2 492 à 4 272 triangles chacun, contre 13 406 pour l'arbuste précédent.
- Les rameaux sont reliés ; les feuilles sont des surfaces découpées, pas des enveloppes opaques.
- Les textures viennent du Searsia Lucida de Poly Haven, sous CC0 ; le catalogue représente des archétypes de jeu, pas douze espèces botaniques identifiées.
- Les deux arbres restent identiques à ceux de `volume_look_normals`.

**La cohérence climatique :**
- Le moteur lit la saison de croissance, l'aridité, la part de conifères, la température et l'exposition déjà utilisées par la végétation.
- Il réserve d'abord les formes froides et exposées, puis le boréal, l'aride, la steppe et le tropical humide ; le reste est tempéré.
- Les poids sont continus, positifs et de somme 1 ; aucun poids minimal n'impose un arbuste tempéré au désert.
- Les seuils sont un réglage artistique sur ces champs climatiques ; ils ne sont ni des frontières géographiques ni une loi de répartition par espèce.
- La montagne se reconnaît par le froid et l'exposition ; aucune altitude absolue universelle ne la définit.
- Les références de port bas sont les [arbustes du Denali](https://www.nps.gov/dena/learn/nature/plants-by-form.htm) et les [saules alpins](https://www.nps.gov/articles/000/little-willows-at-great-heights.htm). Le feuillage étroit des milieux secs est décrit par l'[US Forest Service](https://research.fs.usda.gov/feis/species-reviews/artcal).

**La conservation du peuplement :**
- Ni la graine, ni la position, ni la taille source, ni l'acceptation, ni la portée ne changent.
- La famille occupe `axisY.y = 1 + famille` pour les seuls arbustes climatiques ; le facteur d'étalement se décode séparément.
- Les hauteurs de modèle changent le port dessiné ; les seuils de présence gardent la taille source.
- Le relais maillage/imposteur tient compte de l'encombrement du modèle ; le diagnostic de hauteur du couvert reprend la moyenne des familles. Le couvert lointain des arbustes reste surfacique, sans parallaxe verticale précise.
- `MYPLANETENGINE_OBJECT_LIST` peut exporter les graines et positions sources dans `<capture>.plantes` pour une comparaison exacte sur le même binaire.

**Le coût borné :**
- Les quatorze modèles partagent les six régions d'instances de 524 288 éléments, soit 192 Mio au total.
- Le GPU compte les modèles, calcule des préfixes et disperse les instances ; chaque famille reçoit une sous-plage des deux régions d'arbustes.
- Il n'existe pas de grande file supplémentaire par famille.
- Une commande indirecte contient l'adresse du SRV de la sous-plage et le dessin ; `SV_InstanceID` repart de zéro, indépendamment de `StartInstanceLocation`.
- Les dessins sont regroupés par représentation ; le GPU ignore les commandes dont le nombre d'instances vaut zéro, sans décision fondée sur un compteur CPU ancien.
- Le petit buffer de commandes et compteurs occupe 1 056 octets ; les modèles et textures supplémentaires ont leur propre coût.
- Les compteurs historiques restent six agrégats ; `model_counts`, `family_counts` et `queue_bytes` détaillent le catalogue.

**Les données :**
- Source retenue : `assets/foliage/climate_shrubs_v2/`.
- Reconstruction : `python tools/foliage/arbustes_climatiques_v2.py --preview`, puis `--final`.
- `shrubs.txt` commence par `FOLSHR01 6 2`, puis les douze dossiers en ordre famille et variante.
- Les formats de géométrie, matériaux, imposteurs et visibilité restent ceux de `assets/foliage/README.md`.
- Le moteur la trouve seul : `MYPLANETENGINE_FOLIAGE_ASSETS`, sinon le premier dossier de ce nom au-dessus de son exécutable.
- Sans catalogue, aucune plante : la canopée au sol partout, et le titre dit « végétation absente ». L'ancien repli sur les trois modèles précédents est retiré le 2026-10-30.
- Les planches CPU donnent deux orientations et une vue à l'allométrie du moteur ; elles ne remplacent pas un jugement en contexte.

**Les comparatifs :**
- `tools/banc_arbustes_climat.py`, manifeste `tools/foliage/arbustes_climat_vues.json`.
- Captures cachées sur plusieurs lieux ; les noms de biome sont confirmés par les diagnostics, pas supposés d'après la latitude seule.
- Les identités se comparent entre deux passes du même exécutable ; le 2026-10-27, avec et sans catalogue, ce que le moteur ne permet plus.
- La mesure de temps est distincte de l'export d'identités, dont le readback ajoute du trafic.
- Les captures, modèles figés et empreintes sont sous `x64/ArbustesClimat/`.
- Les premières formes apparentées en vase sont conservées dans `log/arbustes-climatiques-historique.md`.
- Sur les quatorze vues, les graines et positions sources fines/grossières sont identiques bit à bit après tri, avec et sans catalogue sur le même exécutable ; les totaux par espèce sont aussi identiques, sans dépassement.
- Quatre vues voisines plus riches confirment les mélanges boréal/montagne et le désert ; les deux formes sont présentes dans les familles suffisamment échantillonnées.
- Les buffers des représentations passent de 262 793 412 à 729 760 876 octets, hors files et mémoire temporaire ; la diversité ajoute environ 445 Mio.
- La réorganisation des appels conserve intégralement les quatorze BMP et tous les comptes. Les mesures de temps sont sensibles aux charges GPU ; elles ne garantissent pas un nombre de FPS en vol.
- Sur le même exécutable optimisé, les médianes par lieu restent proches entre ancien catalogue et V2 : boréal 4,14/4,76 ms, désert 0,75/0,60, maquis 3,10/3,07, montagne 3,67/3,51, lisière 6,98/7,44, tropical 8,97/9,08. Une seule séquence de 24 images par lieu et un ordre non randomisé : résultat indicatif, pas une preuve de budget.
- Le banc complet termine les 24 mêmes sites sans perte GPU. Il échoue à deux nouveaux seuils face au candidat précédent : trou d'échelle du sable à 50 m (+10,15 %, 158 crops) et du sol à 12 m (+20,83 %, 127 crops).
- Les trois écarts de la piste précédente restent hérités ; l'acceptation utilisateur ne constitue pas une réussite au seuil du projet. Le canonique à 30 sites garde quatorze dépassements, avec des lieux différents.
- Rapports : `x64/ArbustesClimat/qualite_v2/comparaison_p95.json`, `optimisation_images.json` et le log.

**Le vol de jugement :**
- Le jeu se lance comme le dit `lancement.md` ; le catalogue V2 y est le défaut du moteur.
- Palette `tools/tests/2026-10-27-arbustes-climatiques.txt`, douze boutons et F1 à F12 : tempéré, boréal, désert, steppe/savane, montagne, tropical, deux vues par groupe.
- Le lanceur d'alors et le retour à l'arbuste unique sont retirés : `log/arbustes-climatiques-historique.md`.
