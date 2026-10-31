# Rivières : les spikes du 26 et 27 octobre 2026

**Statut : piste mise de côté, hors de `main`.** Tag `piste/rivieres-spikes`, `31a1271`, l'ancienne branche `codex/rivieres-spikes`. Départ : tag `jalon/avant-spikes-rivieres`, la maquette Dendry, `b0252c9`. Résultat : tag `jalon/rivieres-cp-resultat-prometteur`, sur le même commit que `piste/rivieres-spikes`.

**La suite :** la recherche d'une érosion à niveaux, branche `erosion-niveaux`, qui contient la maquette Dendry, tag `piste/dendry-maquette`.

**Pour retrouver le code :** `git checkout piste/rivieres-spikes`. La plupart des fichiers `tools/…` et `MyPlanetEngine/…` cités ici n'existent que dans ce tag. Les exécutables, caches et captures sous `x64/` sont restés locaux.

**Ce fichier réunit la doc du spike, prise dans le tag :**
- **L'état final :** les sections 8 à 15 ajoutées à `../recherche-rivieres.md`, numéros gardés.
- **Les essais remplacés :** le `log/recherche-rivieres-historique.md` de la branche.
- **Le journal des spikes :** ses entrées de `journal-planete.md`, la plus récente en haut ; le journal de `main` n'en garde qu'une entrée courte.
- **Les règles et les surcouches de la branche :** ses ajouts à `principes.md` et `geometrie.md`, que `main` ne reprend pas.

## L'état final, au tag

### 8. Spike Phasor : référence des auteurs puis bassin à une octave

**Repères git :** tag `piste/rivieres-spikes` ; tag de départ `jalon/avant-spikes-rivieres`. Aucun commit ni push ; tag du nouvel essai en attente d’un commit demandé.

**Statut :** référence officielle reproduite localement, puis adaptateur du bassin à une octave. Code GPT-6.1 Terra xhigh ; méthode, intégration et jugement par l’agent principal. Aucun banc à la demande de l’utilisateur.

**Pour essayer :** `tools/lance-phasor.ps1`, ou http://127.0.0.1:8766/phasor-spike/ lorsque le serveur local est actif.
- Vue Versant, source Bassin · 1 octave et graine 13 au démarrage.
- Original / Phasor compare le même terrain et la même pose ; observer les sillons sur les versants.
- Petites ravines active le second niveau ; Intensité règle l’amplitude commune.
- Eau des collecteurs est activé sur notre bassin ; décocher montre le lit avec les mêmes berges. Le cas des auteurs reste inchangé, sans mise en eau ajoutée.
- Graine / +1 régénèrent le bassin par la même fonction procédurale.
- Terrain des auteurs permet de revoir le cas de référence ; Ensemble élargit le cadrage.
- Le lanceur sert seulement en local, avec un processus caché ; il réutilise le serveur ou choisit un port libre.

**Reproduction :** `tools/phasor-reference/` contient le dépôt officiel TerrainEnhancement, état `e0c75976013514e713bc05215927d4ec46462075`, avec ses shaders, framework et cartes d’entrée. La démo est liée depuis la page de Charline Grenier. Code original conservé ; adaptations dans `tools/phasor-spike/`. Les captures de travail utilisent une sortie 512², avec le même calcul et les paramètres d’origine. Provenance et état des droits documentés dans les README locaux ; aucune redistribution ni intégration au moteur décidée.

**Méthode conservée :** convolution de Gabor complexe guidée par le gradient du relief lissé, profil angulaire arrondi, atténuation radiale des singularités et cascade. Le noyau et les shaders des auteurs sont chargés sans modification. Le second niveau reprend le facteur d’amplitude 0,3 du code de démo ; l’article indique 0,2. La fréquence est multipliée par trois. Le fBm de crête reste celui des auteurs.

**Adaptation au bassin :**
- Entrée : `RiverFirst.referenceSample`, une octave, sans les essais latéraux et triangulaires. Région de 20 × 20 km centrée sur le bassin, textures flottantes 512² ; hauteur divisée par 3 km et échelle physique fixe.
- Les deux entrées de hauteur du shader reçoivent le même terrain original échantillonné. La bascule ne lisse donc pas la géométrie de référence ; le gradient d’orientation utilise séparément 16 passes du lissage des auteurs.
- Le pilotage automatique du papier utilise une carte de drainage. Ici, l’amplitude est calculée depuis la distance procédurale au collecteur et la pente lissée : `(1−exp(−d²/0,8²)) × g²/(g²+0,03²)`, d en km, g en pente physique. Aucun nouveau réseau ni routage n’est calculé.
- Intensité initiale 0,04, fréquence 50 : longueurs d’onde d’environ 400 m puis 133 m sur la région de 20 km ; amplification de hauteur de l’ordre de 120 m puis proportionnelle au premier niveau.
- Le calcul des reliefs se fait en textures lors des changements de source, graine ou paramètres ; tourner la caméra ne régénère pas le terrain.
- Les normales du bassin viennent de la hauteur finale et de son échelle physique 3/20. Le cas des auteurs conserve leur passe de normales d’origine. L’ombrage de notre comparaison suit la géométrie affichée.

**Mise en eau des collecteurs :** périmètre choisi par l’utilisateur, sans calcul de drainage local pour les ravines Phasor.
- Le niveau vient exclusivement de `referenceSample.water` ; le lit de référence est déjà incisé de 3 m. L’amplitude Phasor s’annule dans ces chenaux.
- Les triangles de la grille sont découpés à la distance signée zéro. Le terrain et la nappe partagent les sommets de rive au niveau exact du profil.
- Avec eau : terre hors chenal et surface opaque au profil, sans surface de terrain superposée dans l’eau. Sans eau : même triangulation de terre et lit du chenal.
- La nappe ne prend pas la hauteur des bosses ; aucune interruption par masque d’obstacle ni relèvement automatique au terrain.
- La triangulation est calculée lors du changement de bassin ou de graine, puis gardée en mémoire. La caméra et la bascule d’eau ne déclenchent pas ce calcul.

**Jugement visuel préalable :** comparaison sans/avec sur le terrain officiel, puis sur le bassin graine 13 à pose fixe. Les nouveaux sillons sont lisibles sur les versants ; les grandes formes et le fond du collecteur sont conservés. Captures de travail dans `x64/PhasorAuteur/` et `x64/PhasorBassin/`. L’aperçu eau/lit sur les collecteurs confirme leur lecture au fond des vallées et le raccord de rive. Aucun banc ni mesure multi-seeds ; le jugement utilisateur reste à recueillir.

**Limites :** ce spike amplifie le relief et met en eau les collecteurs existants. Les ravines Phasor restent sèches ; aucun drainage calculé n’a été ajouté, selon la décision de l’utilisateur. Leur mise en eau et leur connexion hydrologique jusqu’à l’océan restent ouvertes. Le domaine d’essai est régional et échantillonné ; le raccord planétaire et le portage dans le moteur restent ouverts. Les essais précédents sont dans la partie « Les essais remplacés ».

### 9. Bruit spécialisé de bassin : structure et descente communes

**But :** éprouver un noyau procédural dont les vallées, les crêtes et les cours raccordés proviennent de la même construction.

**Pour essayer :** `tools/lance-bassin-noise.ps1`, ou http://127.0.0.1:8766/basin-noise/ avec le serveur local actif.
- Ensemble montre sources, bifurcations et exutoire marin dans le même cadrage.
- Confluence et Versant rapprochent la caméra, sans changer de terrain.
- Sources surplombe les têtes amont ; Sources hautes, activé au départ, varie leur portée et leur altitude. Décocher restitue la première version du module, sans déplacer la caméra.
- Structure variée, activé au départ, change les subdivisions et le champ commun ; décocher retrouve la structure précédente avec les mêmes réglages de sources et de détail. Le nombre réel de tronçons et de sources est affiché.
- Décocher Eau montre le lit avec les mêmes berges.
- Détail des versants active une modulation de gradient ; désactivé au départ pour lire la structure.
- Graine et +1 régénèrent les cellules ; le lien Référence ouvre le bassin Phasor à une octave, distinct de ce nouveau terrain.

**Périmètre :** un bassin macroscopique, avant le détail Complex Planet ; deux à quatre niveaux de subdivisions internes dans la variante courante, trois dans la référence, distincts d’une addition d’octaves de relief. La référence à une octave reste accessible dans le visualiseur Phasor de la section 8.

**Construction :**
- La graine détermine les subdivisions transversales et les longueurs des cellules.
- Chaque cellule se termine à sa bifurcation ; les deux filles héritent de sa position et de sa largeur.
- La coordonnée `y` augmente vers l’amont ; les courbes des noyaux ne reviennent pas en arrière selon cette coordonnée.
- Un profil commun `W(y)` croît vers l’amont et vaut zéro à la côte. Une confluence partage donc position et niveau.
- La distance aux noyaux finis définit les fonds et le relief entre les cours ; les frontières de voisinage forment les crêtes.
- Le relief latéral et son détail s’annulent aux rives ; le lit reste sous le profil d’eau.
- La terre et l’eau partagent la découpe des rives ; la caméra ne reconstruit pas la géométrie.

**Réglages :** domaine de 22 × 23,5 km, incluant 2,5 km de mer ; longueur de référence du bassin 18 km ; grille fixe 448², mailles d’environ 49 × 53 m. La référence donne 15 noyaux finis et huit têtes terminales ; la variante reste bornée à 31 noyaux. Demi-largeurs de 150 m à 65 m, puis extinction des sources. La distance par section et cap n’est pas une distance euclidienne exacte à la courbe. Relief latéral `1,3 × (hypot(max(D,0),80)−80)^0,9`, atténué à la côte ; lit jusqu’à 4,5 m sous l’eau.

**Ramifications et crêtes variées :**
- Les décisions de fin proviennent du hash de chaque cellule : arrêt possible aux profondeurs 2, 3 et 4 ; probabilité de poursuite de 0,74 au niveau 2 et de 0,52 au niveau 3.
- Les partages transversaux vont de 24 à 76 % ; les confluences ont des coordonnées amont déphasées. Les enfants héritent toujours de l’extrémité et du profil du parent.
- Le domaine commun devient `u=x+650 N(seed+4099,x/9000+17,31,y/4200−7,1)` m, avec `y` inchangé. La borne de dérivée du bruit donne `du/dx>0,54` ; la transformation ne se replie pas. Les axes, les crêtes et l’eau partagent cette transformation.
- Une modulation lente `1+0,22 N(seed+239,x/5200+3,8,y/6000−2,4)` varie la raideur du relief latéral. Elle reste positive et s’annule aux rives par multiplication du relief ; aucun massif indépendant n’est creusé après coup.
- La descente conserve le même profil `W(y)`. La variation est visible sans le détail des versants ; désactiver Structure variée conserve la comparaison antérieure.
- Sur graine 13 : 21 tronçons, 11 sources aux niveaux 2 à 4. Aperçus Ensemble et Sources comparés à pose fixe ; la distribution des branches est plus asymétrique. Les profils restent schématiques et la répétition n’est pas déclarée entièrement résolue.

**Sources de portées variées :**
- Les cellules parentes et les bifurcations restent identiques à la référence. Un hash dédié de chaque feuille donne `h` ; sa fin devient `max(yDépart+800,18 000 × (0,72+0,38 h²))` m. Les appels du générateur initial sont inchangés.
- Avec `t=y/18 000`, le profil commun devient `W=1 250 t+2 200 max(t−0,45,0)²` m. Sa dérivée reste positive ; les parties en aval de 8,1 km gardent le profil précédent. Eau et terrain utilisent le même profil.
- Désactiver Sources hautes rétablit les anciennes fins entre `0,84` et `0,99` fois 18 km, et `W=1 250 t` m.
- Le détail facultatif associe trois champs de gradient tournés, à 550, 290 et 150 m, poids 0,6 / 0,3 / 0,1, puis facteur `1+0,2 N`. La référence conserve son seul champ à 550 m. Le détail reste nul aux rives par multiplication du relief latéral.
- La référence répétait une construction binaire à profondeur fixe et des profils de vallées communs. Le visualiseur échantillonne ce champ ; il ne crée pas ces motifs. La variante de structure en change les subdivisions et le domaine, sans établir encore une morphologie naturelle complète.

**Nature du module :** bruit cellulaire hiérarchique structuré, avec règles identiques pour toutes les graines. Aucune courbe fournie à la main, correction par lieu, simulation, recherche de chemin ou drainage d’un ancien relief. Ce noyau dépasse une simple somme de bruits Perlin ; les contraintes de raccordement font partie de sa définition.

**Portée de la descente :** les axes construits descendent vers leur racine côtière. Cela ne prouve pas que tout point des versants rejoint un cours sans cuvette. Le bassin orienté et borné n’établit pas une hydrologie planétaire ni son raccord à une seed quelconque de Complex Planet.

**Aperçu préalable :** graine 13, vues d’ensemble, confluence avec eau et lit, puis détail et versant inspectés. La variante Sources hautes est comparée à la référence à pose fixe en vue Sources ; trois têtes sont vers 2 060 à 2 284 m, les autres vers 1 159 à 1 355 m selon le profil du module. Les connexions et les crêtes communes sont lisibles ; le relief reste schématique et les sources sont synthétiques. La géométrie reste fixe au changement de caméra. Captures de travail dans `x64/BasinNoise/`. Aucun banc ni balayage de graines ; aucune revendication de réalisme hydrologique complet.

**Travail :** code GPT-6.1 Terra xhigh ; architecture et jugement par l’agent principal. Pas de bancs, de commit ni de push à la demande de l’utilisateur ; aperçu visuel avant présentation. Tag de piste en attente d’un commit demandé.

### 10. Premier rendu du noyau dans MyPlanetEngine

**Statut :** essai régional explicite, avec les matériaux, l’éclairage, l’atmosphère et le détail Complex Planet du moteur. Le noyau analytique remplace la structure régionale ; il ne route pas des rivières à travers un massif indépendant. L’hydrologie planétaire n’est pas intégrée.

**Lancement :** `tools/lance-bassin-planete.ps1`, après compilation Release x64. Le script exporte le bassin puis ouvre directement sa vue générale et la palette `tools/tests/2026-10-27-bassin-noise.txt` : F1 ensemble, F2 collecteur, F3 confluence, F4 branches, F5 versant. `-Seed 13` par défaut ; `-SansPlantes` permet de lire le sol. Notice de reproduction dans `tools/README-bassin-planete.md`.

**Champ partagé :**
- `tools/export-bassin-noise.cjs` exécute le modèle JS, sources hautes et structure variée activées. Il exporte les cellules et le ruban d’eau, sans carte de hauteurs ni mips.
- `MyPlanetEngine/Bassin.hlsli` évalue les mêmes noyaux, hash, déformation de domaine et profil d’eau sur la planète. Les coordonnées sont prises dans le repère tangent fixe, en double avant conversion des petits décalages en flottants.
- `Terrain.hlsli` place le noyau avant le détail Complex Planet de moins d’environ 1 km ; la différence fin/grossier est bornée à ±10 % du relief latéral. Elle est donc nulle aux rives et ne décide pas du niveau de l’eau.
- Les passes River réutilisent le profil exporté ; leur découpe vient du champ signé analytique. Aucun masque d’obstacle ni relèvement de la nappe sur les bosses du terrain.
- Le cache contient des paramètres de cellules ; changer de caméra ne choisit pas une autre carte de hauteurs ni une autre structure de réseau.

**Région d’essai :** fenêtre de 64 km, repère centré sur 34° N / 40° O, rayon 6 378 km. Le centre du repère correspond à `y=9 km` dans le bassin. Transition de 8 km vers le terrain extérieur, hors des confluences jugées ; cette bordure de présentation ne définit pas de bassins planétaires. La graine du bassin est 13 ; la graine propre de Complex Planet reste 0.

**Activation :** variable `MYPLANETENGINE_BASSIN` vers le fichier analytique versionné ; l’ancien format Dendry suit son chemin séparé. Le lanceur restaure ses variables d’environnement après ouverture. Sans ce mode explicite, le moteur utilise son terrain habituel.

**Aperçu préalable :** confluence et vue d’ensemble inspectées dans le rendu natif. Eau raccordée aux deux branches à la confluence ; eau uniforme et berges abruptes. L’ensemble révèle une côte trop rectiligne, une mer en bande et des cours peu lisibles à cette hauteur ; la composition régionale reste à reprendre. Images `x64/BasinNoise/planete-confluence.png` et `planete-ensemble.png`. Cet aperçu ne valide pas le mouvement, tous les niveaux de maillage ni une hydrologie mondiale. Aucun banc ni balayage de graines.

**Limite pratique :** la première initialisation Release a demandé plusieurs minutes et une forte mémoire pendant la préparation des shaders. L’option `MYPLANETENGINE_CAPTURE_FRAMES` abrège seulement le nombre d’images d’aperçu après initialisation ; elle ne résout pas ce coût. Le rendu natif est proposé comme essai, sans validation de performance.

### 11. Trois bassins voisins sur une côte Complex Planet

**But :** éprouver le raccord entre bassins avant une organisation planétaire. Le noyau précédent existe et reste accessible ; cette étape généralise son domaine et ses entrées CP.

**Pour essayer :** `tools/lance-bassins-cotiers.ps1`, ou http://127.0.0.1:8766/coastal-basins/. Vues Ensemble, Crête commune et Embouchure ; Eau et Relief CP se basculent sans changer la pose. La graine 0 est commune à la côte et aux trois réseaux ; aucune commande ne change les seuls arbres en prétendant changer CP.

**Source CP :**
- `tools/coastal-basins/prepare_cp.py` utilise le port NumPy de CP et les gradients du dépôt. `tools/hydro/cp.py` retrouve désormais `LibNoise.hlsli` relativement à son fichier.
- Une recherche déterministe de changements de signe sur la sphère propose des tronçons ; le programme retient un graphe côtier `y=C(x)` échantillonné de la mer vers la terre. Il échoue explicitement si aucun candidat ne convient ; aucune côte de secours inventée.
- Les 256 points côtiers sont des zéros de l’élévation CP complète, filtrée à 500 m, y compris son bruit fluvial d’origine. Les relier linéairement constitue une approximation ; sur la graine 0, l’écart de hauteur aux milieux des segments reste inférieur à environ 2,6 m dans le diagnostic de préparation.
- Le jeu courant couvre 75 km de côte ; repère tangent proche de 2,868° N / 78,750° E. L’axe terrestre du repère est déterminé par le gradient CP, sans latitude de test imposée à la géométrie.
- Deux contrôles CP de 192² valeurs : `middle=clip((mountain_base(cell=2000m)+1)/2,0,1)` ; `fine=clip(0,5+mountainous(cell=grille)−mountainous(cell=2000m),0,1)`. Ce sont des champs de contrôle du relief, pas des hauteurs finales du bassin.

**Construction commune :**
- La coordonnée amont est `v=y−C(x)` ; les exutoires sont sur `v=0`, la mer sur `v<0`.
- Le domaine latent `u=x+650 N(seed+4099,x/9000+17,31,v/4200−7,1)` conserve `v` ; sa dérivée suivant `x` reste positive. Un point de branche inverse ce champ puis restitue `y=C(x)+v`.
- Trois partitions transversales contiguës produisent trois arbres seedés, de longueurs comprises entre 15 et 23 km ; au plus 93 tronçons. Le jeu courant contient 57 tronçons.
- Un seul minimum de distances à tous les tronçons définit les vallées et les crêtes entre les bassins. Les terrains ne sont pas calculés puis fondus séparément.
- Le profil commun `W(v)=1 250 t+2 200 max(t−0,45,0)²`, `t=max(v/18 000,0)`, garantit la descente sur les axes et le niveau commun aux jonctions. La côte donne le même zéro aux trois racines.
- Le relief latéral est `1,3 × (hypot(max(D,0),80)−80)^0,9 × (1−exp(−(v/5000)²))`. L’enveloppe côtière remonte progressivement sur 5 km, au lieu d’imposer le rempart du prototype.
- Relief CP multiplie ce relief par `(0,72+0,65 middle) × (0,78+0,44 fine)`, strictement positif. Le relief reste nul aux rives, le lit est jusqu’à 4,5 m sous le profil d’eau.
- Le maillage du visualiseur suit des lignes de `v` fixes ; des points d’axes et de rives complètent la grille de fond. Les triangles terre/eau partagent leurs sommets de rive ; les normales viennent de la géométrie affichée.

**Aperçu préalable :** Ensemble, Embouchure et Crête commune inspectés, puis même pose sans Relief CP. Les trois réseaux rejoignent la mer et les crêtes sont continues entre bassins ; les contrôles CP enrichissent le relief. Profils encore schématiques et traces d’échantillonnage visibles sur certaines crêtes. Captures dans `x64/BassinsCotiers/web-*.png`. Aucun banc ni balayage de graines.

**Portage natif V2 :**
- `tools/lance-bassins-planete.ps1` ouvre le moteur Release avec les trois bassins et la palette `tools/tests/2026-10-27-bassins-cotiers.txt` : Ensemble, trois confluences et Embouchure centrale.
- `tools/export-bassins-cotiers.cjs` exporte 57 cellules, 256 points de côte, deux champs CP 192² et 35 754 sommets de ruban. L’en-tête V2 reste distinct du bassin unique ; l’ancien mode conserve son lanceur.
- Le repère vient du jeu CP ; la palette et le soleil sont dérivés de ce repère et des branches, sans coordonnées de test recopiées d’une autre région.
- Le noyau HLSL lit les contrôles CP au même endroit que le modèle JS. Dans son cœur il ne recalcule pas deux fois CP complet ; l’extérieur reste CP. Les appels CP normal et filtré des chemins historiques sont factorisés sans changer leurs formules.
- La fenêtre native de 100 km a une transition extérieure de 8 km. Sa limite amont vient de la plus haute source plus 8 km ; le raccord commence après les sources, ce qui évite de prolonger le profil polynomial hors domaine.
- Le lanceur restaure ses variables de soleil, de données et de végétation. Le natif refuse explicitement toute seed autre que 0, sa graine CP compilée ; il ne mélange pas une nouvelle côte avec une ancienne planète.
- Compilation Release réussie, avertissements Materials connus uniquement. Vue d’ensemble native inspectée : côte irrégulière et grands ensembles de vallées lisibles, cours très fins à 40 km. Images dans `x64/BassinsCotiers/native-*.png` ; pas de banc ni de validation en mouvement.
- Embouchure centrale inspectée après correction du cadrage depuis le large : le ruban rejoint la mer au même niveau visible. Rives encore anguleuses et eau uniforme ; la lecture du raccord ne valide pas un delta, le mouvement ou les changements de maille.

**Portée :** une côte représentable comme graphe, trois bassins et une graine préparée. La preuve concerne les cours construits ; ni toutes les gouttes des versants, ni tous les continents, ni les raccords sphériques d’un découpage mondial ne sont établis. Lacs, deltas, débit et climat des sources restent ouverts. La recherche d’un zéro de bruit côtier n’ajoute aucun drainage ou routage au réseau.

**Travail :** code GPT-6.1 Terra xhigh ; architecture et jugement par l’agent principal. Aucun commit ni push ; tag de piste en attente d’un commit demandé.

### 12. Organisation globale cellulaire sur la sphère CP

**Statut :** prototype mondial grossier dans `tools/global-basins/`, hors moteur. Le bassin local à une octave et l’essai côtier restent accessibles. La première version globale à arcs libres est conservée dans [l’historique](#les-essais-remplacés) ; ses branches trop directes pouvaient se croiser ou traverser une baie.

**Pour essayer :** `tools/lance-bassins-globaux.ps1`, ou http://127.0.0.1:8766/global-basins/. Basculer CP actuel / CP + bassins conserve pose, éclairage d’inspection, grille et amplification. Réseau structurel affiche les axes, sans surface d’eau. Les vues Bassin courant et Embouchure du bassin courant sont des caméras du même globe. Voir les axes masqués affiche explicitement la topologie au-dessus de la grille : ce schéma ne valide pas son incision.

**Entrée CP :**
- Graine commune 0, rayon 6 378 km, 32 514 directions et 65 024 triangles ; pôles partagés et couture fermée. La maille équatoriale vaut environ 157 km.
- La hauteur CP complète filtrée à 30 km fournit le signe terre/mer et les contrôles d’altitude. Elle comprend encore le bruit fluvial natif CP ; les bandes ne sont pas toutes séparées. Le poids montagneux CP module la sélection des sources.
- 4 154 zéros côtiers sont affinés sur les arêtes changeant de signe. Les champs continentaux et l’élévation filtrée à 10 km sont exportés, sans former encore une nouvelle bande de détail.

**Bruit spécialisé et préparation :**
- Le module génère une structure cellulaire globale discrète puis un champ continu de relief. Cette préparation dépend de la grille et de la graine ; ce n’est pas une simple octave Perlin évaluée isolément en un point.
- Chaque triangle CP est découpé au zéro côtier en polygone terrestre convexe. Les connexions passent seulement par des portions d’arête terrestres partagées ; elles ne peuvent sauter au-dessus d’une baie présente dans ce domaine.
- Des exutoires côtiers espacés de 600 km sont sélectionnés dans chaque composante terrestre. Un bruit cellulaire macroscopique affecte les centres au site côtier le plus proche de leur composante.
- Kruskal construit une forêt seedée : connexions internes à une même cellule macroscopique d’abord, hash ensuite ; une union ne réunit jamais deux composantes déjà munies d’un exutoire. Les morceaux séparés d’une cellule peuvent rejoindre un autre bassin par une connexion terrestre.
- Cette forêt constitue la topologie générée du module. Aucun coût de pente ni chemin optimal sur les altitudes CP, aucun écoulement, remplissage de cuvettes, déplacement correctif des anciens tracés ou simulation d’érosion.
- Des cellules sources sont choisies avec probabilité de 2 à 4 % selon le poids montagneux. Une cellule à haute altitude fournit la sélection lorsqu’un arbre n’en a aucune ; les branches sans source sont élaguées. Les feuilles actives prennent la hauteur CP interpolée à leur centre.

**Courbes et profils :**
- Chaque port est partagé en position et en altitude par ses deux cellules. Les jonctions sont intérieures, à coordonnées barycentriques positives.
- Autour d’une vraie jonction, chaque bras reste dans son triangle-éventail, distinct de ceux des autres bras. Les courbes ont des contrôles positifs et une progression radiale monotone ; leurs polylignes restent dans ces secteurs.
- Dans les cellules à deux ports, une seule cubique les relie sans passage imposé par le centre. Ses contrôles restent dans le polygone convexe en projection gnomonique ; leur progression par tiers de corde exclut une boucle. Sources et vraies confluences conservent leurs centres.
- Les ports visent une tangente commune ; seule la continuité en position et en altitude est garantie partout. Les éventails utilisent quatre segments par bras, les cellules traversées huit segments par courbe.
- Le minimum des hauteurs sources descendantes multiplie `depth/(depth+12)` pour les jonctions ; les feuilles prennent leur hauteur CP positive. Les ports gardent un niveau commun entre parent et enfant et chaque exutoire vaut 0.
- Les profils interpolent ces niveaux de façon monotone ; la courbure spatiale n’ajoute pas de bruit à l’altitude de l’eau. La preuve porte sur les axes construits, pas sur toutes les gouttes des versants.

**Champ commun :**
- Les petits arcs des courbes et les arcs côtiers de niveau 0 portent des noyaux à support compact de 450 km. Le poids est proportionnel à leur longueur et à `(1−u)^4(1+4u)/u^4`, avec `u=d/L<1`.
- `W=(0,01 H_CP+Σ wᵢhᵢ)/(0,01+Σ wᵢ)` revient continûment à CP hors des supports. Les axes et jonctions exactement reconnus reprennent leur niveau partagé.
- `H=W+max(H_CP−W,0) × smooth(D/120 km)` définit le relief autour du même réseau. Cette largeur représente une structure mondiale grossière, pas celle d’un chenal réaliste.
- Une grille spatiale 3D fixe accélère les noyaux de cette fonction compacte. La caméra ne sélectionne ni une autre structure ni une autre donnée de hauteur.
- Le visualiseur subdivise la source en 130 050 sommets et 260 096 triangles. Sur les arêtes côtières, les nouveaux sommets sont les zéros CP ; ailleurs, les hauteurs CP sont interpolées. Les deux modes partagent cette grille, leurs normales géométriques et l’amplification visuelle initiale ×20.

**Limites :**
- L’absence de passage en mer concerne les polygones côtiers de cette grille. La côte CP continue plus fine, les petites îles et les changements de signe manqués restent à reconstruire.
- La résolution et l’orientation de la maille influencent la forme. Le réseau n’est pas une reconstruction hydrologique ; les grandes lignes de partage des massifs ne sont pas encore déduites de CP.
- `W > H_CP` peut relever un bas terrain. Le nouveau module peut modifier fortement le relief près des cours ; la conservation exacte des massifs n’est pas garantie.
- La grille du globe peut masquer les axes et n’échantillonne pas les rives. Le zoom avec lit et eau est décrit en section 13 ; le globe ne possède ni détail de versant rebranché ni portage global dans le moteur.
- Une seule graine est préparée ; changer de graine demande de régénérer ensemble CP et le module. Aucun jugement de stabilité à tous les niveaux de maillage n’est établi.

**Travail :** code GPT-6.1 Terra xhigh ; architecture et jugement par l’agent principal. Syntaxe et aperçu ciblé ; aucun banc, balayage multi-seeds, commit ni push. Tag en attente d’un commit demandé. Construction détaillée dans `tools/global-basins/README-reseau.md` et `README-modele.md`.

**Jeu courant :** 35 956 cellules terrestres, 217 exutoires, 9 410 cellules actives, 610 sources effectives et 74 412 petits arcs. La préparation est indépendante de la caméra ; les effectifs ne constituent pas une mesure de qualité hydrologique.

**Aperçu :** même graine 0, globe et bassin comparés à CP à pose fixe, embouchure et île de 131 sommets terrestres inspectées ; aucune erreur JavaScript au chargement. Courbes plus douces, raccords continus dans le schéma complet et axes contenus dans la terre visible sur ces cadrages. Les méandres restent parfois systématiques, avec des retours serrés ; le relief large et la maille de contrôle sont encore visibles. Les traits masqués par la grille restent un défaut d’échantillonnage du terrain, distinct de la topologie construite. Captures `x64/GlobalBasins/cell-review-*.png` et `cell-final-*.png` ; aucun banc ni validation multi-seeds.

### 13. Lit et mise en eau du réseau global

**Statut :** spike couplé du lit, des rives et de l’eau, dans `tools/global-basins/water.html`. Les vues sont des fenêtres d’échantillonnage fixes du même module global ; aucun autre réseau ni terrain local n’est généré. Le globe de la section 12 reste la référence de structure. Aucun portage natif supplémentaire.

**Pour essayer :** http://127.0.0.1:8766/global-basins/index.html?water=1 ouvre d’abord la sphère, centrée sur le site d’essai repéré. Le parcours Planète → Bassin → Lit et eau annonce le changement d’échelle ; Voir le bassin d’essai cadre son réseau avant Approcher l’eau. L’ancienne entrée `water.html` revient sur ce globe. `water.html?detail=1` ouvre explicitement le zoom de 32 km, avec localisateur CP et retours visibles vers la planète ou le bassin.

**Dans le zoom :** Collecteur, Confluence et Embouchure cadrent le même bassin ; Berge rapproche la caméra d’une rive du collecteur. Eau masque la nappe en conservant le terrain et la pose. Vue ensemble ou R rétablit le cadrage. La molette approche ; glisser tourne, Maj-glisser déplace. L’eau reste testée dans ces fenêtres ; sa mise en eau sur toute la sphère n’est pas réalisée.

**Profil partagé :**
- `model.sampleChannel` réutilise le niveau `W` et la distance `D` du modèle global sans changer les sources, les jonctions, les courbes ou leur graine 0. La référence `sample` et les hauteurs du globe restent accessibles.
- Demi-largeur `b=300 m`, profondeur nominale `p=8 m`, largeur de structure `L=120 km`. Ce sont des réglages uniformes de spike, sans débit ni calibration hydrologique.
- Sur terre : `q=max(1−(D/b)²,0)²`, puis `H=W−p q+max(H_CP−W,0) × smooth(max(D−b,0)/L)`. Sur la rive `D=b`, le fond rejoint exactement `W` ; dans le chenal, le fond est dessous.
- En mer : niveau d’eau 0, `H=min(H_CP,−p q)`. Le lit continue sous la nappe marine à l’embouchure. Les supports côtiers de niveau 0 gardent le raccord avec le profil fluvial.

**Géométrie :**
- Une règle de cadrage choisit une confluence proche d’un exutoire, puis le milieu de son bras descendant et sa racine. Le choix ne change pas le module.
- Les contrôles CP sont les mêmes triangles subdivisés que le globe, avec zéros côtiers partagés. L’interpolation barycentrique radiale fournit le contrôle CP aux nouveaux points.
- Chaque fenêtre mesure 32 km de côté, grille fixe de 256 cases par côté, pas de 125 m. Les intersections supplémentaires suivent la côte et les rives.
- Chaque triangle est découpé d’abord au zéro CP, puis à `D−b=0` sur la partie terrestre. Les intersections d’arête sont mises en cache et réutilisées par les triangles voisins.
- Le terrain conserve tous les polygones, secs ou mouillés. La nappe est triangulée une fois dans l’union mouillée : une confluence ne superpose pas plusieurs rubans indépendants.
- Les sommets de rive ont exactement la même position dans le terrain et l’eau. Masquer l’eau garde donc le lit. Les nappes fluviale et marine reprennent leurs sommets côtiers communs de niveau 0.
- Les positions métriques locales incluent la courbure planétaire, calculée en doubles avant conversion en flottants. Les normales viennent du terrain affiché. Aucun déplacement de l’eau pour cacher un défaut de profondeur.
- La caméra ne reconstruit ni le réseau ni le maillage ; les vues sont mises en cache. L’amplification ×1 ou ×3 agit identiquement sur terrain et eau ; la profondeur graphique est logarithmique pour l’inspection rapprochée.
- Dans Collecteur et Berge, une coupe intersecte les triangles réellement affichés, terrain et eau, sur ±800 m en travers du cours. Ses axes en mètres ont des échelles distinctes ; elle conserve les hauteurs ×1 et ne remplace pas la géométrie 3D.

**Portée :** le test porte sur la traduction en géométrie du réseau déjà construit. La largeur reste constante, le maillage représente approximativement le profil de 8 m, la côte reste celle des contrôles grossiers et les matériaux sont sobres. Les sources, les deltas, le débit, le détail CP fin, les changements de niveau de maillage et les performances du moteur ne sont pas validés.

**Travail :** code GPT-6.1 Terra xhigh ; architecture et jugement par l’agent principal. Syntaxe et aperçus ciblés, aucun banc ni balayage de graines. Aucun commit ni push ; tag en attente d’un commit demandé. Notices `tools/global-basins/README-eau.md` et `README-eau-geometrie.md`.

**Aperçu :** graine 0, bassin 55, confluence de la cellule 12 342 à environ 5,66 m, proche de 6,24 km de son exutoire. Confluence et raccord à la mer inspectés ; la nappe reste continue dans ces cadrages. Le terrain du collecteur garde son lit lorsque l’eau est masquée ; la coupe du maillage montre un fond voisin de −5,2 m sous une eau vers 2,8 m. Approche de 180 à 100 m et petite rotation inspectées, même objet de maillage conservé et aucune erreur JavaScript. Rendu encore très sobre et creusement peu perceptible en vue large avec 600 m de largeur ; pas de validation de tous les lieux ni des niveaux de détail du moteur. Captures dans `x64/GlobalWater/review-*.png`.

### 14. Référence CP et comparaison native

**Référence :** CP complet fournit le terrain et la rugosité, avec toutes ses bandes ; aucune approximation du globe grossier ne remplace les montagnes.

- B bascule CP original / CP + rivières avec la même pose, le même éclairage et la même finesse.
- La hauteur CP au nadir règle la maille et le plan proche dans les deux états ; la collision suit le terrain actif.
- La carte régionale reste CP original ; aucun drainage historique n’alimente le module fluvial.
- Y masque l’eau et conserve le lit.
- Le premier assemblage avec profils indépendants pouvait relever le sol ; son code et ses vues restent dans `x64/GlobalBasinsAvantMorpho` pour la comparaison, son compte rendu dans [l’historique](#les-essais-remplacés).

### 15. Profils bornés par CP, méandres et largeurs variables

**But :** supprimer les monticules fluviaux, conserver les reliefs CP et rendre les cours moins rectilignes et uniformes.

**Structure du module :**
- Le réseau cellulaire seedé conserve sa topologie terrestre et ses jonctions partagées.
- Deux bruits de gradient, aux pas de 12 km et 3,5 km, déforment les bras dans leurs secteurs admissibles.
- Le déplacement est borné par 70 % de la marge du secteur et 2 200 m ; le second bruit pèse 0,45.
- Un fondu C1 de 1,2 km à chaque extrémité conserve les raccords sans supprimer la courbure sur les premiers kilomètres.
- Les phases sont seedées par bras pour ne pas aligner les départs des bruits. La subdivision affine la courbe selon un écart au milieu de corde de `max(10 m, 25 % de la demi-largeur)`, avec pas cible de 125 m à 1 km ; une approximation polygonale subsiste.

**Profil et côte :**
- `CPNoiseSampler.hlsl` appelle directement `ComplexPlanetElevation`, aux mêmes positions d’axe et de berge, à deux mailles fixes de 32 m et 256 m.
- Cette évaluation fait partie de la génération du module ; aucun écoulement par image, routage sur les pentes ou remplissage des cuvettes n’est ajouté.
- Chaque source terrestre conserve son chemin construit jusqu’au premier contact marin du CP échantillonné ; le chemin y est coupé, sans continuation sur mer puis sur terre.
- L’enveloppe nodale prend le minimum des deux références CP et des berges, avec marge de 8 m ; ses minima hérités contraignent les profils vers l’aval.
- Le facteur analytique `d / (d + 20 000 m)`, avec d la distance au nouvel exutoire, donne une pente commune sous cette enveloppe et rejoint 0 à la mer.
- Les contacts sont interpolés entre sondes ; cela ne prouve pas le zéro ni la descente en tout point du CP continu.

**Lit et largeur :**
- Le sol vaut `min(CP, lerp(CP, W - profondeur, masque))` : ce module ne relève jamais la géométrie CP.
- Le masque de raccord décroît à zéro sur 3 km depuis la rive ; hors influence, le terrain est CP exact.
- La demi-largeur part de 4 m à la source et croît selon le nombre de sources réunies ; sa base vaut `24 sqrt(nombre de sources)`.
- Une variation cohérente de coefficient 0,3 et de pas 9 km change la largeur le long des bras, avec le même fondu aux jonctions.
- L’évasement atteint un facteur 2,2 sur les 25 derniers kilomètres avant l’exutoire ; la profondeur dépend de la largeur.
- Il s’agit d’une embouchure élargie ; aucun éventail de bras distributaires ni dépôt de delta n’est encore construit.

**Format et coût :**
- V4 : 32 floats par segment, positions haute+basse précision, niveaux et largeurs aux deux extrémités.
- Le hash 3D clairsemé de maille 20 km interroge un support de 12 km, contre 450 km auparavant.
- Les sections sont alignées sur 64 floats ; leurs grandes adresses sont reconstruites en uint, les IDs et offsets relatifs restent exactement représentables.
- Graine 0 : 1 456 417 segments fluviaux retenus, 196 nouveaux contacts marins, données d’environ 268 Mo.
- Sur 610 sources initiales, 18 sont en mer dans le CP plus fin et sont exclues par le masque terrestre.

**Pour juger :**
- `tools/lance-global-basins-planete.ps1` ouvre `x64/GlobalBasinsMorpho/bin/MyPlanetEngine.exe` et le parcours `tools/tests/2026-10-27-global-morpho.txt`.
- F10 confluence en vue d’ensemble, F4 au même lieu de près, F3 source, F5 collecteur, F8 relief CP, F9 embouchure affinée ; F1 et F2 gardent le contexte planétaire.
- La finesse d’inspection vaut 0,25 ; les comparaisons avant/après gardent cette même valeur et les mêmes poses absolues.
- `x64/GlobalBasinsMorpho/comparaison.html` compare l’ancien et le nouveau module ; B dans le moteur compare CP original et le nouveau module.

**Limites :**
- La contrainte sur l’axe et les berges est échantillonnée, pas démontrée entre les sondes.
- Aux contacts côtiers, des sondes ont un sol CP négatif sous une eau maintenue à zéro ; la mer et le chenal sont découpés par le signe CP natif.
- Les rives d’eau suivent encore les interpolants du maillage ; les chenaux fins exigent une maille plus fine que leur largeur.
- La validité sur d’autres graines, le mouvement et tous les changements de maille restent ouverts. Le coût GPU reste sensible dans certaines vues.

**Vérification :** Release isolé compilé ; trois paires natives source, confluence et embouchure inspectées, même pose absolue, soleil et finesse 0,25. Le cap surélevé de la source disparaît et le contact marin est rétabli ; les largeurs changent entre source, collecteurs et côte. La grande organisation des branches reste géométrique malgré les courbes ajoutées, et la rivière conserve un aspect uniforme dans certains cadrages rapprochés. Les détails du lit et la stabilité en mouvement restent à juger. Captures finales `x64/GlobalBasinsMorpho/{source,confluence,embouchure}-{avant,apres}.png`, page locale `comparaison.html`. L’ouverture automatisée des fichiers locaux est bloquée par le navigateur intégré ; les images natives ont été inspectées directement. Aucun banc ni balayage de graines.

**Jalon :** `jalon/rivieres-cp-resultat-prometteur`, sauvegarde des sources et outils demandée le 27 octobre 2026 sur la branche du tag `piste/rivieres-spikes`. Les exécutables, caches et captures sous `x64/` restent locaux ; les commandes de reproduction figurent dans `tools/README-global-basins-planete.md`.

**Travail :** code GPT-6.1 Terra xhigh ; architecture, orchestration et jugement par l’agent principal. Résultat prometteur avec les limites ci-dessus ; aucun banc supplémentaire pour cette sauvegarde.

## Les essais remplacés

### 2026-10-26 · Profil Dendry brut · écarté

**Essai :** transmettre le profil de l'arbre au bake, creuser sous lui et mettre les sommets du chenal à son niveau.

- **Résultat :** des parois d'eau au-dessus de la vallée sur les captures à 600 m et à 30 m.
- **Cause :** le terrain prend le plus bas des vallées superposées. Le profil d'une autre branche peut donc passer au-dessus du terrain obtenu.
- **Mesure avant correction :** écart eau–terrain au cours, p90 84,8 m, p99 347 m, maximum 1 171 m. 8,5 % des échantillons dépassent le terrain de plus de 100 m.
- **Autre défaut :** les affluents finissent sur l'axe du parent avant ses méandres. Ils peuvent manquer le cours visible de plusieurs centaines de mètres.
- **Suite :** borner le profil par le terrain, propager les abaissements vers l'aval, raccorder les affluents au cours méandré et étaler les berges de l'incision.

**Le rendu d'origine :** le bake ne conservait que le point du cours, la largeur et la distance. Le pixel colorait le relief sans changer la hauteur de l'eau. Aucun chenal n'était creusé sous un profil indépendant.

### 2026-10-26 · Profil incisé sur champs interpolés · écarté

- **Réglages :** marge de profil de 2 m ; pente minimale de 1 m/km ; raccord de berge au moins deux demi-largeurs, ou 1,5 fois l'incision.
- **Profil :** 194 156 nœuds, aucune remontée ; abaissement médian 2 m, p95 11,3 m, maximum 573 m.
- **Défauts :** la grille de 293 m coupe les cours en morceaux arrondis ; dépassement eau–terrain intérieur résiduel jusqu'à 4,5 m. Le relief fin et les mips ne partagent pas encore la référence du profil.
- **Captures :** sept vues ; 13,8 s avec Dendry2 contre 8,2 s avec le premier build corrigé, caches différents possibles. Ce temps n'est pas une mesure isolée du coût de rivière.
- **Banc qualité :** 30 lieux, graine 1, référence du 24 octobre : 22 des 57 p95 comparables dépassent +10 %. Douze captures témoins sur trois lieux à 12 m et 3 000 m sont identiques à Dendry2 du 25 octobre.
- **Palette remplacée :** `tools/tests/2026-10-26-dendry-profil.txt`.

### 2026-10-26 · Minimum des berges vectorielles · écarté

- Le minimum de toutes les incisions peut creuser le sol sous une rivière haute au voisinage d'un lit beaucoup plus bas.
- Sur 3 025 sondes hors chenaux dans la zone active : dépassement maximal de 529,31 m ; 13 points au-dessus de 0,1 m.
- Pire cas trouvé : latitude 34.241986, longitude −40.289026 ; niveaux de cours 4 248 m et 3 680 m, distants d'environ 135 m.
- La première partition Shepard avec une sélection discrète des chenaux supprime le dépassement, mais crée un saut de 3,60 m à leur bord.
- La suite prolonge continûment la contrainte hors chenal ; aucune sélection `distance <= half` ne change le terrain par saut.

### 2026-10-26 · Itérations de berge et de profil · remplacées

- **Partition sans couplage :** 3 025 rives hors chenaux actives, dépassement maximal 6,23 cm. La vue du pire ancien dépassement révèle toutefois une gorge artificielle très raide ; le contrôle des niveaux ne suffit pas au jugement visuel.
- **Profil couplé avec lit et marge répétés :** écarté ; prendre le fond du voisin comme plafond d'eau et retirer encore 3 m à chaque passe force une baisse diffuse. Ce résultat ne démontre pas une divergence du couplage limité aux berges.
- **Couplage limité aux berges :** seulement d'autres branches, hors de leur chenal ; aucun retrait de marge supplémentaire. Les 12 puis 36 passes améliorent nettement le cas extrême. La variante de 36 passes reste explicitement non convergée.
- **Simplification verticale à 24 cm :** le nouveau profil révèle un écart de 17,26 cm sur une rive. La borne est ramenée à 4 cm ; le banc complet du spike courant passe ensuite avec un maximum de 5,10 cm.
- **Correction du banc de couplage :** les cellules de plus de 128 sondes demandaient l'offset du paquet dans la réduction locale ; corrigé, puis 36 passes rejouées depuis le profil initial. Les données non finies provoquent désormais un échec explicite.

### 2026-10-26 · Maquette vectorielle et couplage · écartés après essai en vol

**Constat utilisateur :** mutations de géométrie et scintillement importants à l’approche des rivières. Les contrôles de profil et les captures fixes ne validaient pas cette stabilité. Le glissement du maillage est une hypothèse, pas une cause démontrée.

#### Ancien état · Maquette Dendry : profil d'eau, sources, delta

**Spike courant : continuité et lit incisé, 2026-10-26.**
- Le réseau de 150 km garde un profil d'eau indépendant, strictement descendant vers l'aval et partagé aux confluences.
- Le profil est plafonné 3 m sous le terrain Catmull-Rom du bake, sur l'axe et les deux rives, avec des sondes espacées de 2,29 m au plus. Tout abaissement se propage vers l'aval.
- Les tronçons vectoriels remplacent les cinq champs de rivière interpolés à 293 m. Une grille de 512² cellules donne les tronçons candidats, sans décider des connexions.
- Un ruban triangulé porte l'eau indépendamment du maillage de terrain. Le pixel découpe son bord selon l'union des chenaux ; le sol est réellement incisé sous le profil.
- Les coordonnées restent en double précision jusqu'à la soustraction du point de tronçon. Les marches dues à la quantification planétaire ne doivent pas entrer dans le relief local.
- Le rayon de berge varie par Hermite monotone, partagé aux raccords. Dans son corridor, le terrain emploie le même Catmull-Rom mip 0 que le profil ; le détail et le filtrage reviennent sur 100 m.
- Avant le rendu, 36 passes abaissent les profils que les berges d'autres cours rendent incompatibles. Ces baisses se propagent vers l'aval ; 1,65 % des points baissent de plus de 1 m.
- Les berges voisines sont ensuite combinées par une partition continue ; une contrainte de chenal prolongée protège la profondeur sans changer brutalement de branche.
- La simplification conserve le niveau d'eau à 4 cm près, et le tracé à 5 % de sa demi-largeur près.
- Le ruban apparaît à 8 km du bord et atteint sa couverture entière à 10 km. Cette bordure est un raccord de maquette, pas une embouchure.
- Les essais écartés et les mesures intermédiaires sont dans [l'historique](#les-essais-remplacés).

**Pour tester :** `powershell -NoProfile -File tools/lance-rivieres.ps1`.
- La palette `tools/tests/2026-10-26-dendry-continu.txt` propose douze vues, accessibles par boutons et F1 à F12. Les altitudes absolues sont synchronisées depuis les titres GPU.
- Ajouter `-SansPlantes` au lanceur permet de lire les berges, notamment la vue F11 masquée par un arbre.
- L'exécutable est `x64/Release/MyPlanetEngine.exe` et le bake `tools/hydro/proto/dendry-2026-10-26-continu.bin`.
- Sans `MYPLANETENGINE_DENDRY`, cette surcouche est désactivée.

**Reproduction du bake :** après le cache terrain et réseau `*-river-input.npz` produit par `dendry.py` :
```powershell
python tools/hydro/river_profile.py tools/hydro/proto/dendry-2026-10-26-river-input.npz tools/hydro/proto/dendry-profile-catmull.bin
python tools/hydro/river_segments.py tools/hydro/proto/dendry-2026-10-26-river-input.npz tools/hydro/proto/dendry-2026-10-26-river-segments.npz --profile-cache tools/hydro/proto/dendry-profile-catmull-profile.npz --water-tolerance-m 0.24
python tools/hydro/river_profile_coupled.py --passes 36 --output tools/hydro/proto/dendry-profile-coupled-checked-36.npz
python tools/hydro/river_segments.py tools/hydro/proto/dendry-2026-10-26-river-input.npz tools/hydro/proto/dendry-coupled-precis-segments-36.npz --profile-cache tools/hydro/proto/dendry-profile-coupled-checked-36.npz --water-tolerance-m 0.04
python tools/hydro/build_river_spike.py tools/hydro/proto/dendry-2026-10-26-river-input.npz tools/hydro/proto/dendry-coupled-precis-segments-36.npz tools/hydro/proto/dendry-2026-10-26-continu.bin
python tools/hydro/river_spike_checks.py
```

**Format courant :** header16 et terrain 512², puis payload version 2 : prefix16, index CSR, segments de 12 flottants et sommets de ruban de 4 flottants. Les coordonnées des tronçons sont en kilomètres locaux ; hauteurs, largeurs et rayons sont en mètres. Les offsets comptent des flottants. Le chargeur ajoute les mips et encode l'offset signé du payload dans `header[15]`. Le format historique à cinq champs reste lisible.

**Limites :**
- Le bord du réseau reste son exutoire ; ni les sources glaciaires ni le raccord à l'océan ni les deltas ne sont implémentés dans ce spike.
- Le terrain reste un bake à 293 m. Les rares incisions atteignent environ 602 m. Le préajustement atténue nettement la gorge de F10, mais celle-ci reste raide ; les très petits cours peuvent être partiellement masqués par le maillage vu de haut. Ce cas reste visuellement non accepté.
- Le préajustement en 36 passes ne constitue pas un solveur convergé : sa borne auxiliaire sur les berges voisines garde un résidu maximal de 0,617 m sur 186 points. Le creusement final pondéré passe son contrôle séparé à 0,1 m. Ce couplage reste une piste expérimentale.
- La couleur d'eau est provisoire. Le jugement porte sur la continuité, le niveau et les berges ; l'animation et les matériaux d'eau restent à travailler.
- L'indépendance du ruban ne donne pas au maillage de sol une résolution infinie : les très petits chenaux vus au loin restent un cas à surveiller.

**Travail parallèle de ce spike, trois sous-agents GPT-6 Luna xhigh :**
- Continuité : simplification bornée, tronçons, index CSR et ruban d'eau.
- Profil et lit : profil Catmull-Rom, raccords et rayons de berge continus.
- Validation : échantillonneur indépendant, profils, rives, index, précision et creusements superposés.
- L'agent principal intègre le format et les shaders, compile et vérifie les captures sans fenêtre.

**Architecture proposée :**
- **`RiverGraph` :** carte hydrologique globale, liée à `PlanetMap`, avec sources de ruissellement et de fonte, nœuds, récepteurs, débit et exutoires mer/lac. Dendry ajoute des affluents entre les ancrages du graphe ; il ne choisit pas l'embouchure.
- **`RiverProfile` :** passe topologique qui donne un niveau d'eau par nœud et impose une baisse vers l'aval. Les lacs sont des étendues plates qui relient deux niveaux du graphe.
- **`RiverBed` :** largeur et profondeur depuis le débit ; le sol est incisé sous le niveau d'eau, et la surface de l'eau est rendue séparément au niveau du profil.
- **`RiverReach` et ruban d'eau :** polyligne continue, ancrée sur la planète, avec altitude d'eau, débit, largeur et profondeur à ses points. Une géométrie d'eau indépendante suit cette polyligne. Les tronçons sont indexés par tuile pour le creusement ; le champ grossier du point le plus proche ne décide plus des connexions visibles.
- **`RiverDelta` :** à un exutoire océanique de débit suffisant, le cours se partage en distributaires dans un éventail déposé sur la côte. Le delta n'est pas un type de source ni une règle appliquée aux lacs.

**Contrat commun pour les futures tâches parallèles :**
- **Le graphe est en lecture seule** après sa construction. Chaque cellule a une clé stable, un récepteur ou un exutoire, une aire drainée, un débit et une contribution de source (pluie, fonte, ou les deux).
- **Les lacs sont des nœuds explicites.** Le graphe intérieur est sans cycle ; un nœud intérieur a un seul récepteur. Chaque exutoire fournit son type et son niveau d'eau.
- **Les profils consomment les arêtes orientées** et rendent un niveau d'eau par nœud. Les lits consomment ce profil et le débit ; ils ne recalculent pas le drainage.
- **Un tronçon conserve ses extrémités et son sens.** Son contrat contient sa polyligne, son abscisse le long du cours, ses niveaux d'eau, débits, largeurs et profondeurs, avec des unités déclarées.
- **Les deltas consomment les exutoires marins** et rendent leurs distributaires et dépôts comme géométrie locale. Ils ne changent ni le graphe intérieur ni le profil du fleuve amont.
- **L'intégration est le seul propriétaire du format de bake et des shaders.** Elle fixe les vues de test et vérifie les raccords entre les livrables.

**Lots futurs, après jugement de la continuité et du lit :**

| Lot | Livrable hors moteur | Limite |
|---|---|---|
| Sources et drainage | graphe orienté, débit de pluie et de fonte, parcours d'une source de montagne à l'océan | ne modifie aucun shader |
| Profil et lit | tronçons vectoriels continus, niveaux descendants, chenal et berges sur un graphe fourni | ne choisit ni les sources ni les exutoires |
| Delta | fragment à distributaires, partage du débit et dépôt pour un exutoire côtier fourni | laisse fixe l'entrée du fleuve |

- **Avant le travail parallèle :** fixer le contrat et deux petits jeux de données, montagne–océan et exutoire côtier. Les lots profil et delta démarrent sur ces jeux de données.
- **L'agent principal intègre** les livrables, le ruban d'eau et l'index des tronçons dans le moteur. Il tient les captures et les bancs. Chaque lot livre une palette courte pour le jugement en vol.

**Ordre des spikes :**
1. **Profil et lit sur la maquette de 150 km :** supprimer la hauteur qui suit les bosses, inciser le chenal ; aucun changement à la source du relief.
2. **Sources de montagne jusqu'à l'océan :** injecter ruissellement et fonte, raccorder les petits torrents au réseau global, vérifier le profil et les confluences.
3. **Un delta côtier :** choisir un seul grand exutoire, créer ses distributaires et le dépôt, puis tester l'approche depuis l'avion et le sol.

**Contrat de mesure :**
- aucun segment du profil ne remonte vers l'aval ;
- le fond du chenal reste sous l'eau d'une profondeur déterminée par le débit ;
- les sources de la scène de montagne rejoignent le même réseau jusqu'à l'océan ;
- les bras du delta restent connectés au fleuve et atteignent la côte sans traverser la terre vers l'amont.

**Vérification du spike vectoriel :**
- Build Release x64 réussi ; douze vues capturées sans fenêtre, aux altitudes sol et avion, plus douze captures sans plantes.
- Banc CPU complet : 4 817 634 sondes, dont 2 348 399 dans le domaine actif ; aucune remontée ni rupture d'arête. Sur 3 132 sondes hors chenaux après combinaison des incisions : dépassement maximal de 0,0510 m, sous le seuil de 0,1 m. Le cas extrême de F10 reste visuellement non accepté.
- Banc qualité courant : 1 350 vues sur les mêmes trente lieux et caps du premier banc. Les 59 p95 comparables sont identiques au premier spike ; aucun nouveau dépassement. Face à la référence officielle du 24 octobre, 22 des 57 p95 dépassent encore +10 %, donc l'acceptation globale reste non acquise.
- Résultats locaux : `x64/Release/river-spike-checks-precis-final.txt`, `x64/Release/rivieres-pret-a-tester/`, `x64/Release/rivieres-pret-a-tester-sans-plantes/`, `x64/Release/qualite-continu-2026-10-26/`.
- La référence officielle n'a pas été remplacée. Les essais précédents sont dans l'historique.
- Pour refaire les captures : `python tools/banc_rivieres.py x64/Release/MyPlanetEngine.exe --dendry tools/hydro/proto/dendry-2026-10-26-continu.bin --tests tools/tests/2026-10-26-dendry-continu.txt --out x64/Release/rivieres-rejeu`. Ajouter `--sans-plantes` pour lire le sol.
- Travail sans commit ni push. Le tag de piste attend le commit demandé après jugement en vol.

### 2026-10-26 · Visualiseur analytique à deux cours · remplacé

### Ancienne section 8 · Nouveau spike : un relief construit avec ses rivières

**Statut : visualiseur autonome implémenté, premier banc exécuté.** L’essai Dendry vectoriel est écarté après la régression observée en vol. Son état, ses mesures et ses limites sont dans [l’historique](#les-essais-remplacés).

**Question à trancher :** une géométrie unique, construite autour de cours d’eau connus, reste-t-elle stable pendant une approche et lorsque le maillage glisse ?

**Contrainte utilisateur : composition mathématique de bruits.** La cible garde l’architecture modulaire de complexplanet : champs procéduraux déterministes, octaves, déformations du domaine, courbes et opérateurs génériques. Les exceptions par lieu, retouches de profils par passes et solveurs correctifs ne font pas partie de cette piste. Un graphe de drainage calculé séparément serait une autre approche, à distinguer explicitement.

**Distinction :** le visualiseur actuel utilise deux courbes prédéfinies et un profil linéaire imposé. Sa fonction est pure et indépendante de la caméra, mais ce n’est pas encore un bruit fluvial générique. Il vérifie une coupe de vallée et son échantillonnage ; il ne démontre pas une génération procédurale de réseau. Le prochain problème est de construire un module fluvial qui fournisse ses connexions et sa descente par construction ; un empilement d’octaves seul ne les garantit pas.

**Périmètre :** un bassin sur une sphère, un fleuve, un affluent, une source haute et une côte. Le niveau de la mer vaut zéro. Le rendu est sobre, avec une couleur d’eau unie.

**Une seule construction :**
- Le cours et son profil descendant constituent l’ossature du relief.
- Une coupe transversale lisse donne le fond, les berges et les versants.
- Le relief des massifs et ses détails croissent à partir des berges ; leur amplitude y est nulle.
- La même fonction rend hauteur du lit, niveau d’eau et distance au cours, en coordonnées fixes sur la planète.
- Les deux branches partagent leur niveau à la confluence.

**Ordre du premier essai :**
1. Maillage fixe et géométrie simple ; vérifier le lit, la confluence et l’arrivée à la côte.
2. Approches à plusieurs hauteurs sur ces trois lieux ; mesurer les écarts du sol aux mêmes coordonnées.
3. Maillage glissant, caméra immobile, même géométrie ; mesurer le scintillement et comparer au maillage fixe.

**Critère d’arrêt :** si la version fixe échoue, revoir la fonction de relief. Si seule la version glissante échoue, traiter l’échantillonnage du maillage avant de complexifier les rivières.

**Coût contenu :** un petit modèle analytique et un seul visualiseur. Le graphe hydrologique global, les sources climatiques, les deltas, la végétation et les textures détaillées restent hors de ce premier essai. Le relief de complexplanet sera réintroduit aux grandes échelles après cette vérification.

**Pour tester :** ouvrir `tools/river-first/index.html` dans un navigateur, ou lancer `tools/lance-rivieres-simples.ps1`. Aucun téléchargement, serveur ni compilation n’est requis.
- Choisir Confluence, Berge du fleuve, Source haute ou Côte ; le bassin entier est une vue d’ensemble.
- Le bouton de descente approche la berge jusqu’à 3 m, avec la même maille pendant toute l’approche.
- Comparer Fixe et Glissement simulé à caméra immobile. Le glissement décale la grille d’une maille ; la caméra et le champ de relief restent indépendants.
- Décocher Eau pour voir le fond. Glisser pour regarder, molette pour la hauteur, ZQSD ou flèches pour le déplacement, R/F pour monter et descendre.

**Modèle :** deux courbes analytiques, un profil commun de 20 m/km, un lit de 3 m, chenaux de 130 à 240 m, versants sur 1,4 km. Un bruit borné module l’amplitude des versants ; il ne modifie pas le niveau d’eau. La projection sur la sphère est calculée sans soustraction de deux grands flottants.

**Code :** `tools/river-first/model.js` porte le champ CPU et sa traduction GLSL ; le banc vérifie leur concordance. `viewer.js` ne filtre ni ne régénère ce champ avec la distance. Une grille de 512² cellules reste à résolution constante ; le changement de maille est une action explicite.

**Banc :** `node tools/banc_rivieres_simples.cjs x64/RiverFirst` ; `--cpu-only` suffit pour les invariants et les erreurs géométriques. Les captures requièrent Playwright et pngjs, disponibles dans le runtime de travail ; le visualiseur n’en dépend pas.
- 39 000 sondes de cours : aucune coupure ni remontée ; profondeur centrale de 3 m.
- Concordance CPU/GPU : écart maximal mesuré de 1,26 mm sur 256 points.
- Maille 16 m, surface affichée : erreur géométrique maximale de 8,29 cm sur les sondes et phases du banc ; à 8 m, 4,09 cm. Le fond seul est plus sensible : maximum 23,93 cm à 16 m, 6,42 cm à 8 m.
- Source, confluence et côte : descente automatique jusqu’à 3 m, sans déplacement de l’ancrage du maillage.
- Neuf vues immobiles à 3, 120 et 1 200 m : écart d’image nul en maillage fixe. Huit phases de glissement : écart moyen maximal 0,125/255, au bord de côte à 3 m ; jusqu’à 1,11 % des pixels dépassent 3/255 dans la zone centrale mesurée. Le scintillement n’est donc pas déclaré nul.
- Rapport et captures : `x64/RiverFirst/rapport.json` et `x64/RiverFirst/*.png`. Rendus sans fenêtre ni prise de focus.

**Limites :** bassin analytique fini, sans simulation hydrologique ni réalisme de matériaux. Le maillage fixe n’est pas un remplacement du maillage planétaire du moteur. Les mailles grossières de 64 et 128 m servent à observer l’échantillonnage ; leur approche du sol n’est pas validée. Le banc qualité de MyPlanetEngine n’est pas applicable à ce rendu distinct ; les mesures précédentes du moteur ne sont pas remplacées.

**État git :** aucun commit ni push ; tag de piste à poser sur un commit demandé. Les mutations signalées dans Dendry ne sont pas déclarées corrigées par ce visualiseur.


### 2026-10-26 · Relief CP indépendant, avant les bassins intégrés

**État précédent du visualiseur :**

**Repères git :** tag `piste/rivieres-spikes` ; tag de départ `jalon/avant-spikes-rivieres` sur `b0252c9`, état Dendry du 25 octobre avant ces spikes. Les modifications expérimentales restent non committées.

**Statut : variante avec relief inspiré de complexplanet à juger par l’utilisateur. Aucun banc lancé, à sa demande. Code confié à GPT-6.1 Terra xhigh ; architecture et jugement conservés par l’agent principal.**

**Pour essayer :** `tools/lance-rivieres-simples.ps1`, ou `tools/river-first/index.html` dans le navigateur. Recharger l’onglet pour remplacer l’ancien modèle à deux courbes.
- Seed puis Appliquer, ou +1 : mêmes paramètres et même générateur pour toutes les seeds, entier signé de 32 bits.
- Octaves de 1 à 4 : profondeur des ramifications fractales.
- Relief CP / Relief simple : comparaison aux mêmes coordonnées, angle et hauteur au-dessus du sol. Le mode CP est actif par défaut ; aucun recadrage au changement de mode.
- Lieux générés depuis la seed : ramifications, berge d’un tronc, source, côte, réseau entier.
- Eau permet de voir le lit ; Fixe/Glissement et la descente restent disponibles.

**Construction :** un module de ramifications dyadiques produit un champ de distance aux cours. Les cellules filles convergent continûment vers leur cellule mère en descendant. Le hachage de la seed place les axes à chaque échelle ; un bruit de gradient à quatre octaves déforme leurs positions. Aucun tracé n’est stocké ni ajusté pour une seed particulière.

**Relief :** le profil commun décroît vers la côte ; les versants partent du champ fluvial. Le mode simple garde le bruit de gradient 2D précédent. Le mode CP adapte le groupe montagnes hautes/basses et collines de `ComplexPlanet.hlsli` : RidgedMulti, Billow, Turbulence, mélange et exponentiation, puis sélection douce de massifs.
- Les fréquences de la sphère sont divisées par 6 378 et les puissances de turbulence multipliées par 6 378 pour travailler en kilomètres.
- Lacunarités source : 2,142578125 pour les montagnes, 2,162109375 pour les collines.
- Caps fixes du spike : montagnes basses 8 → 3 octaves, collines 6 → 3, turbulences → 2. Ils ne varient pas avec la caméra ni la maille.
- Le relief positif en km est assemblé par `0,25 + 1,5 × collines + 2,5 × montagnes × sélection de massif`, puis multiplié par l’enveloppe transversale qui vaut zéro aux rives. Le profil d’eau, l’incision et le réseau fluvial restent ceux de la variante seedée.
- L’adaptation réutilise le bruit de gradient 2D local ; ce n’est pas un portage 3D bit à bit de complexplanet. Aucun tracé, patch par seed, solveur ou passe de correction n’est ajouté.

**Affichage :** le graphe de relief est évalué aux sommets. Les normales interpolées proviennent de la hauteur centrale et de deux voisines sur la sphère, soit trois évaluations par sommet. Le fragment ne réévalue que la distance fluviale et utilise la hauteur interpolée pour la couleur. Ce compromis garde le relief à juger sans rendre chaque triangle plat.

**Limite volontaire :** cette première construction reste orientée selon une direction aval commune, avec des bassins répétés. Elle explore un module fractal générique ; elle ne démontre pas encore un drainage adapté aux continents arbitraires de complexplanet. La seed n’est pas encore branchée au moteur C++.

**Contrôle :** démarrage et prévisualisation simple/CP sur la seed 13, 4 octaves ; crêtes et vallons nettement visibles sur la même zone. Le jugement en mouvement reste celui de l’utilisateur. Aucun banc ni mesure multi-seeds ; les anciens résultats analytiques ne valident pas cette variante. Aucun commit ni push.


### 2026-10-26 · Premier cadrage des bassins intégrés

- **Essai :** seed 14, quatre octaves ; première prévisualisation trop lisse et parallèle, relief fin écrasé par le facteur quadratique de l’écart entre chenaux.
- **Réglage remplacé :** `smoothstep(0, largeurBassin × 0,35, écart)` ; remplacé par `écart/(écart+1,5 km)` avec une modulation CP amplifiée.
- **Cadrage :** vue élargie à une maille de 64 m et déplacée vers la dernière bifurcation ; altitude 8 km et inclinaison 60°.
- **Seconde prévisualisation :** crêtes et vallées lisibles ; disposition encore très parallèle. Aucun banc lancé.


### 2026-10-26 · Bassins intégrés à plusieurs niveaux, remplacés par le bassin fixe

**Variante bassins-integres-2, état précédent :**

**Repères git :** tag `piste/rivieres-spikes` ; tag de départ `jalon/avant-spikes-rivieres` sur `b0252c9`. Aucun commit ni push des expériences.

**Statut :** spike `bassins-integres-2`, à juger par l’utilisateur. Code confié à GPT-6.1 Terra xhigh ; architecture et jugement par l’agent principal. Aucun banc lancé, à la demande de l’utilisateur.

**Pour essayer :** recharger `tools/river-first/index.html`, ou lancer `tools/lance-rivieres-simples.ps1`.
- Bassins intégrés est le mode par défaut ; Versants / torrents cadre les branches hautes et leurs raccords.
- CP indépendant et Relief simple restent accessibles aux mêmes coordonnées et à la même hauteur au-dessus du sol.
- Seed / +1 changent le champ déterministe entier ; Octaves règle sa profondeur de 1 à 4.
- Source, Ramifications, Berge du tronc, Côte et Réseau entier donnent d’autres cadrages.
- Eau montre ou masque la surface ; Fixe / Glissement et la descente vers la berge restent disponibles.

**Composition :** potentiel grossier → bassins, profils et crêtes → détails des versants.
- Un potentiel de gradient à 50 km, séparable en x/y, influence le placement des nœuds vers les potentiels bas et leurs incréments d’altitude. Il représente ici l’entrée grossière ; il n’est pas encore le champ des continents et chaînes du moteur.
- Les ramifications dyadiques restent implicites, déformées par le bruit commun ; aucun graphe routé ni tracé stocké.
- L’altitude d’un nœud additionne les incréments positifs de ses ancêtres : `0,16 + 0,34 × potentiel` km au premier niveau, puis `0,12 + 0,43 × potentiel` km par niveau. Les enfants partagent l’altitude de leur parent à la confluence.
- L’eau interpole les altitudes parent/enfant ; la dernière branche gagne encore `0,12 + 0,25 × potentiel` km jusqu’à sa source. Le plan incliné commun appartient aux anciens modes.
- La demi-largeur initiale de 120 à 160 m est multipliée par 0,47 à chaque niveau ; elle s’effile à zéro sur le dernier kilomètre avant la source. À quatre niveaux, les torrents terminaux font environ 12 à 16 m de large avant cet effilement.
- Entre deux chenaux, leurs profils s’interpolent doucement. Une crête dépend de leur écart physique et du potentiel grossier : `4u(1−u) × écart/(écart+1,5 km) × (0,6+1,2 × potentiel)` km ; elle s’annule quand deux branches coïncident.
- RidgedMulti et Billow de l’adaptation 2D de complexplanet modulent cette crête par un résidu borné : trois octaves, lacunarités 2,142578125 et 2,162109375, facteur `0,25 + 2,5 × détail²`. Les montagnes complètes indépendantes restent dans le mode de comparaison.
- La structure latérale s’annule dans le lit, puis remonte sur une enveloppe de 80 m ; incision centrale de 3 m. La remontée après les sources interpole les deux voisins pour rester continue.

**Affichage :** même champ CPU / GLSL, hachage entier et paramètres de seed communs. Trois évaluations du terrain par sommet pour les normales interpolées ; le fragment calcule seulement les chenaux. Cinq candidats locaux, sans calcul des altitudes ancestrales dans le fragment. La maille reste fixe pendant l’approche. La couleur dépend de la hauteur au-dessus du profil d’eau interpolé, comme les formes des vallées.

**Limites :** région sphérique locale, côte commune et drainage orienté vers y décroissant ; bassin dyadique encore reconnaissable. Le potentiel grossier est simplifié et séparable. Ce spike explore le module intermédiaire ; il ne démontre ni le drainage de continents arbitraires, ni l’intégration à la seed C++ de complexplanet. Le rendu logiciel démarre lentement ; aucune mesure du GPU matériel.

**Contrôle :** syntaxe et démarrage WebGL sur seed 14 / 4 octaves, prévisualisation du cadrage par défaut. Crêtes et vallées lisibles, organisation encore très parallèle ; jugement en mouvement confié à l’utilisateur. Aucun banc, aucune mesure multi-seeds. Les variantes précédentes et leurs réglages sont dans la partie « Les essais remplacés ».


### 2026-10-27 · Premiers raccords des affluents latéraux

- **Premier lancement :** compilation trop lourde ; programme spécialisé par mode et valeurs des nœuds mémorisées sur le GPU, sans changer les fonctions du champ.
- **Première vue locale :** affluent visible et raccordé, avec des crêtes d’aspect abrupt. La sélection dure du candidat le plus proche présente aussi un risque de rupture ; elle est remplacée par une composition continue des vallées voisines, chaque demi-versant se raccordant à son collecteur.
- **Comparaison finale à pose fixe :** les crêtes abruptes sont également présentes sans affluents. Le nouveau vallon remodèle fortement le versant ; son incision reste à juger par l’utilisateur.
- **Contrôle :** prévisualisations de travail, aucun banc.


### 2026-10-27 · Affluents latéraux versants-1, écartés après essai utilisateur

**Jugement utilisateur :** cours trop rectilignes, tranchant les montagnes, aspect de nervures de feuilles ; résultat moins bon que le bassin à une octave.

**Cause de construction :** courbes obliques dans des cellules puis recomposition d’une bande de versant ; les grandes crêtes ne découlent pas de ces ramifications. La continuité du mélange ne résout pas cette incohérence de structure.

**État de l’essai avant rejet :**

**Repères git :** tag `piste/rivieres-spikes` ; tag de départ `jalon/avant-spikes-rivieres` sur `b0252c9`. Aucun commit ni push des expériences ; tag de cette piste en attente d’un commit demandé.

**Statut :** spike `versants-1`, à juger par l’utilisateur. Code GPT-6.1 Terra xhigh ; architecture et jugement par l’agent principal. Aucun banc lancé, à la demande de l’utilisateur.

**Pour essayer :** recharger `tools/river-first/index.html`, ou lancer `tools/lance-rivieres-simples.ps1`.
- Le bassin reste à un niveau ; les anciens liens à plusieurs octaves sont ramenés à un niveau.
- Réseau entier est la vue initiale, seed 14 en l’absence de seed dans le lien.
- Ruisseaux / torrents active les affluents sans déplacer la caméra ; désactiver retrouve le terrain intégré de référence à une octave.
- Versants / torrents et Source cadrent un affluent réel de la seed, avec une maille centrale de 16 m.
- CP indépendant, Relief simple, Eau et la descente restent disponibles.

**Bassin conservé :** axes des collecteurs, côte et profils du bassin intégré à une octave. Potentiel grossier de gradient à 50 km ; détails RidgedMulti / Billow adaptés en 2D. Les niveaux supplémentaires n’allongent plus le bassin. L’ancienne construction à plusieurs niveaux et ses réglages sont dans la partie « Les essais remplacés ».

**Affluents :** courbes latérales implicites, construites dans les demi-intervalles entre collecteurs.
- Cellules longitudinales de 3,2 km, jonctions décalées par la seed ; longueur longitudinale de 2,2 à 3,3 km.
- La branche traverse jusqu’à 84 % de son demi-versant, avec un léger fléchissement ; aucune traversée de la ligne de partage centrale.
- Les cellules appartiennent à la bande entre le premier branchement principal et sa tête ; elles ne prolongent pas le bassin.
- Le profil est `H_collecteur(y) + A × smoothstep(0,1,v)`, avec `A = (0,4+0,3 × potentiel) × écart/(écart+1,5 km)` km, constant par affluent. La montée est positive ; à la confluence, `v=0` retrouve le collecteur.
- Largeur totale de 40 m à l’aval, décroissante puis effilée à zéro près de la tête ; profondeur centrale de 3 m.
- Le relief du versant se recompose autour du même profil : enveloppe de vallée de 250 m, relief latéral positif sur 120 m, détail CP borné. Ce remplacement peut abaisser ou relever le précédent microrelief ; ce n’est pas une incision stricte dans un terrain arbitraire immuable.
- Le poids de vallée vaut exactement un dans le chenal. Lit et surface d’eau utilisent le même profil ; aucune interpolation de l’ancien relief bruité dans l’eau.
- Sur la berge du collecteur, un profil partagé raccorde progressivement la branche ; le lit principal est conservé.
- Chaque demi-versant appartient à son collecteur ; les enveloppes de vallées s’annulent à la ligne de partage. Les trois cellules voisines se composent par poids continus : `poidsRéférence=Π(1−qᵢ)`, `poidsValléeᵢ=qᵢ × Πⱼ≠ᵢ(1−qⱼ)`, puis normalisation. Un chenal de poids un conserve exactement son profil.
- Aucun graphe stocké, routage, rejet selon les bosses rencontrées, passe de correction ou exception par seed.

**Visualiseur :** domaine de 65,536 km de côté pour toutes les résolutions, grille de 512² cellules.
- Pour un indice `i` entre −256 et 256, `t=i/256` : `x=i × mailleCentre + signe(t) × (32,768−256 × mailleCentre) × |t|³`, en km ; même loi pour y.
- La maille de 8 à 128 m règle la résolution centrale ; la périphérie reste plus grossière. Le domaine ne rétrécit plus quand on affine la maille.
- Aucune adaptation à la caméra ; géométrie et maillage restent stables pendant le zoom. Le glissement simulé reste un contrôle explicite.
- L’orbite utilise la cible du terrain de référence ; la bascule des ruisseaux ne déplace pas la pose.
- Le champ CPU et GLSL partage les mêmes formules. Le fragment évalue les chenaux ; les hauteurs et normales restent aux sommets.
- Le programme graphique est spécialisé et mémorisé par mode ; le bassin est fixé à un niveau. Un cache GPU de 64 nœuds mémorise les positions et altitudes de la fonction procédurale sur la région, sans routage ni graphe hydrologique précalculé.

**Limites :** collecteurs encore parallèles, potentiel grossier simplifié et drainage régional orienté ; une seule échelle d’affluents, sans sous-réseau ramifié complet. Le relief fin est remodelé autour des branches et les vallons peuvent être très incisés ; cet aspect reste à juger. La périphérie et la vue d’ensemble ne résolvent pas les petits lits avec la même précision que le centre des vues locales. Pas d’intégration au moteur C++ ni de drainage des continents arbitraires de complexplanet.

**Contrôle :** syntaxe JavaScript, compilation WebGL, vue d’ensemble et comparaison locale avec/sans affluents à caméra fixe sur seed 14. L’affluent apparaît dans le versant ; les crêtes abruptes sont aussi présentes dans la référence. Aucun banc ni mesure multi-seeds. Le jugement en mouvement reste celui de l’utilisateur.


### 2026-10-27 · Retour à la référence avant le module commun

**État avant bassins-communs-1 :**

**Repères git :** tag `piste/rivieres-spikes` ; tag de départ `jalon/avant-spikes-rivieres` sur `b0252c9`. Aucun commit ni push des expériences.

**Statut :** retour au bassin de référence à une octave. Les affluents latéraux `versants-1` sont écartés après jugement utilisateur ; leur code reste disponible par une case désactivée par défaut. Paramètres et détail de l’essai dans la partie « Les essais remplacés ».

**Pour essayer :** recharger `tools/river-first/index.html`, ou lancer `tools/lance-rivieres-simples.ps1`. Cache des scripts : `reference-bassin-1`.
- Réseau entier est la vue initiale ; bassin à un niveau, seed 14 en l’absence de seed dans le lien.
- Essai des affluents est décoché. L’activer permet de revoir l’essai écarté sans changer la pose.
- Les modes CP indépendant / simple, Eau et les vues locales restent disponibles.

**Base conservée :** collecteurs du bassin intégré à une octave, côte et profils. Potentiel grossier de gradient à 50 km et détails RidgedMulti / Billow adaptés en 2D. Les cours principaux restent orientés et parallèles ; cette base visuelle ne valide pas encore le drainage d’une planète entière.

**Visualiseur conservé :** domaine fixe de 65,536 km de côté ; grille de 512² cellules à résolution centrale réglable de 8 à 128 m. La projection cubique concentre les sommets au centre sans rétrécir la région. L’orbite utilise la cible de référence ; le zoom ne régénère ni le terrain ni le maillage. Programmes spécialisés par mode et cache GPU des valeurs de 64 nœuds, sans routage ni graphe hydrologique précalculé.

**Décision d’architecture :** le module intermédiaire doit construire les vallées et les lignes de partage d’une même organisation de bassins, puis accueillir le détail CP sur les versants. Dans l’essai écarté, les tracés obliques étaient définis séparément des grandes crêtes et le relief n’était remanié que dans leur voisinage. Cette construction ne répond pas à l’architecture visée.

**Contrôle :** défauts de démarrage corrigés, syntaxe JavaScript vérifiée ; aucun banc ni nouveau rendu pour ce retour à la référence, conformément au rythme d’itération demandé. Aucun nouvel essai de drainage n’est présenté comme validé.


### 2026-10-27 · Première subdivision du module commun

- **Première construction :** points de partage sur le bord haut, 40 triangles par racine. Prévisualisation trop en éventail et sources alignées près de la limite amont.
- **Remplacement :** sommet de partage intérieur et triangle de crête linéaire, 47 triangles ; seconde bande de déformation commune à 3,7 km.
- **Affichage :** cadrage repris de 48 km / 88° vers 30 km / 65° ; palette remplacée par l’altitude continue, le profil du cours le plus proche produisant des plages de couleur discontinues hors de l’eau.
- **Jugement final de travail :** structure commune visible avant CP, mais aspect encore géométrique. Aucun banc ; prévisualisations uniquement.


### 2026-10-27 · Bassins triangulaires, non concluants visuellement

**Décision :** le rendu reste un schéma géométrique peu lisible ; la propriété commune du générateur ne suffit pas à produire un paysage naturel. Essai mis de côté ; le bassin à une octave est conservé pour Phasor.

**État de bassins-communs-1 avant mise de côté :**

**Repères git :** tag `piste/rivieres-spikes` ; tag de départ `jalon/avant-spikes-rivieres` sur `b0252c9`. Aucun commit ni push ; tag du nouvel essai en attente d’un commit demandé.

**Statut :** spike `bassins-communs-1`, à juger. Code GPT-6.1 Terra xhigh ; architecture et jugement par l’agent principal. Aucun banc à la demande de l’utilisateur.

**Pour essayer :** recharger `tools/river-first/index.html`, ou lancer `tools/lance-rivieres-simples.ps1`.
- Bassins communs est le mode initial, seed 14 en l’absence de seed dans le lien.
- Détail CP désactivé montre la structure complète du nouveau module : vallées, affluents, versants et crêtes.
- Référence · 1 octave conserve le terrain de comparaison exact, sans l’essai latéral écarté. Changer le mode ou le détail ne recadre pas.
- Réseau entier cadre le bassin ; Versants / torrents, Ramifications et Source utilisent des tronçons du nouveau module.
- Le domaine fixe de 65,536 km, la maille centrale réglable, Eau et le glissement explicite restent disponibles.

**Module :** subdivision hiérarchique de cellules de bassin triangulaires, déterministe depuis la seed. Il s’agit d’un module structuré, distinct d’une simple somme de bruits fBm. Il ne route pas de cours dans un terrain déjà constitué et ne simule pas l’érosion.
- Une cellule porte un exutoire bas O et deux bornes hautes L/R. La subdivision produit une jonction J, le cours O–J et ses deux flancs.
- Un sommet de partage intérieur M crée les deux sous-bassins J/L/M et J/M/R, ainsi que le triangle de crête M/L/R. La forme des vallées et celle de leur séparation proviennent de la même découpe.
- Les jonctions montent de 25 à 40 % de la différence entre l’exutoire et la plus basse borne ; les sources terminales montent de 65 à 80 %. Les profils des tronçons interpolent les mêmes altitudes.
- Les flancs utilisent les coordonnées barycentriques du bassin : `H=W+c^1,4 × (hC−W)`, avec W le profil du fond. Les caps terminaux utilisent une remontée de même exposant. Les triangles de crête intérieure interpolent linéairement leurs trois hauteurs pour raccorder les bords hauts des sous-bassins.
- Trois niveaux fixes donnent 47 triangles de structure et 15 tronçons par cellule racine. Des caps latéraux complètent son rectangle ; les bornes entre cellules racines partagent la même hauteur.
- Les bornes hautes valent `1,8+1,2 × potentiel` km. Le sommet M est placé à l’intérieur de J/L/R, à 18–40 % du chemin du bord haut vers J ; sa montée vaut 90–115 % de celle du bord correspondant.
- Une déformation commune à 12 km et 3,7 km courbe l’ensemble du champ ; déplacement borné à 600 m, nul à la côte. Vallées et crêtes subissent la même transformation.
- Largeur initiale de 200 m, divisée par deux par niveau jusqu’à 25 m aux feuilles ; effilement terminal et profondeur de 3 m. Le poids du lit vaut un dans le chenal ; le profil d’eau n’emprunte pas le bruit de détail.

**Détail CP après la structure :** RidgedMulti / Billow adaptés en 2D, trois octaves, modulation bornée à 10 % de la hauteur disponible au-dessus du profil local. La bulle barycentrique s’annule sur les arêtes ; cours et partages restent ceux du module structurel. Ce mode n’ajoute pas le groupe complet des montagnes indépendantes de complexplanet.

**Rendu :** valeurs des cellules mémorisées dans une texture RGBA32F, 62 lignes par racine, sans calcul hydrologique externe. CPU et GLSL utilisent les mêmes contrôles et formules. Programmes spécialisés par mode ; couleur de terre fondée sur l’altitude continue, sans prolonger la hauteur du cours le plus proche à travers tout le versant. L’orbite utilise une référence commune aux deux terrains.

**Limites :** formes encore géométriques et relief de détail peu marqué ; répétition des bassins racines et prolongement plat au-delà de leur limite haute. La construction reste régionale, sans continents arbitraires ni raccord au moteur C++. Une prévisualisation ne démontre pas la stabilité à toute distance ou toutes les seeds. L’amélioration visuelle n’est pas déclarée acquise.

**Contrôle :** syntaxe, démarrage et compilation WebGL ; vues d’ensemble et structure locale sur seed 14, puis reprise du sommet intérieur et du cadrage. Aucun banc, aucune mesure multi-seeds. L’utilisateur reste le contrôleur du rendu.


### 2026-10-27 · Première organisation globale à arcs libres · remplacée

**Statut :** prototype mondial grossier dans `tools/global-basins/`, hors moteur. Il remplace la fenêtre côtière par une construction sur toute la sphère ; le rendu natif régional de la section 11 reste une référence distincte. Il ne constitue pas encore une hydrologie mondiale ni un module de production.

**Pour essayer :** `tools/lance-bassins-globaux.ps1`, ou http://127.0.0.1:8766/global-basins/. Basculer CP actuel / CP + bassins conserve la caméra, la lumière, le maillage et l’amplification. Le réseau est un diagnostic structurel, pas une surface d’eau. Le bassin local à une octave et l’essai côtier restent accessibles séparément.

**Entrée CP :**
- `prepare_cp.py` évalue le port NumPy de ComplexPlanet sur 32 514 directions et 65 024 triangles ; pôles partagés et couture de longitude fermée. Rayon 6 378 km, graine commune 0.
- L’élévation complète filtrée à 30 km fournit les hauteurs de contrôle et le signe terre/mer ; le poids de montagnes CP module la sélection des sources. La maille géométrique équatoriale est d’environ 157 km, distincte de la largeur du filtre.
- 4 154 zéros côtiers viennent des arêtes changeant de signe, affinés par bissections du même champ CP. Les petites îles ou changements de signe absents de la grille restent absents.
- Les champs continentaux et l’élévation filtrée à 10 km sont exportés pour les étapes suivantes ; ils ne deviennent pas encore une nouvelle bande de détail du modèle. La hauteur de contrôle comprend le bruit fluvial CP natif : les bandes de CP ne sont pas encore toutes séparées.

**Construction structurée :**
- La connexité des arêtes terre–terre définit les composantes terrestres, sans écoulement sur les altitudes. Chaque composante conserve au moins un exutoire ; un ordre de hash commun sélectionne des sites côtiers espacés d’au moins 600 km.
- Chaque point terrestre appartient au site le plus proche de sa composante, selon la distance sphérique. Cette partition ne rattache pas une petite île à un autre continent.
- Des sources seedées occupent 4 à 6 % des sommets selon le poids montagneux CP ; une cellule sans source conserve son point le plus haut. Chaque source garde exactement la direction et l’altitude de son contrôle CP.
- Des subdivisions binaires en coordonnées tangentes construisent les jonctions. Les enfants héritent de la position et de la hauteur du parent ; les profils linéaires descendent vers leur racine de niveau 0.
- Le jeu courant contient 208 sites, 781 sources et 1 354 tronçons. Ce sont des paramètres globaux générés, indépendants de la caméra ; aucune fenêtre locale n’est greffée à la planète.

**Champ commun :**
- Tous les profils fluviaux et les arcs côtiers de hauteur 0 contribuent au champ `W` par interpolation de Shepard, poids `1/d⁴`. Aucun seuil de voisinage ne choisit des branches différentes selon la caméra.
- Avec `D` la distance au réseau, `H = W + max(H_CP−W,0) × smooth(D/120 km)`. Le relief latéral s’annule sur les axes isolés ; CP contrôle les reliefs entre les fonds. La largeur est celle de cette structure mondiale grossière, pas celle d’un chenal réaliste.
- Le visualiseur subdivise chaque triangle en quatre avec sommets d’arête partagés : 130 050 sommets, 260 096 triangles. Les nouvelles hauteurs CP sont interpolées ; le même module évalue les nouvelles hauteurs de bassin.
- Sur chaque arête côtière, le nouveau sommet est le zéro CP affiné plutôt que le milieu ; les exutoires et la côte visible partagent ainsi le point de niveau 0. Les deux modes utilisent cette même géométrie de contrôle.
- Les normales viennent de la surface affichée. L’amplification visuelle, initialement ×20, s’applique identiquement aux deux modes et ne modifie pas les altitudes du modèle.

**Limites à traiter :**
- Les cellules sont géométriques ; elles ne suivent pas encore les lignes de partage des grands massifs. Un arc peut traverser une baie concave ou croiser une branche d’un autre niveau. Les jonctions héritées garantissent leur raccord propre, pas la compatibilité de tous les croisements spatiaux.
- `W > H_CP` peut relever un bas terrain ; la conservation exacte des massifs n’est pas garantie. Les grandes chaînes doivent rester reconnaissables dans la comparaison, sans présenter cela comme une preuve globale.
- La maille peut masquer les axes et n’échantillonne pas leurs rives. Il n’y a ni lit fin, ni surface d’eau, ni détail de versant rebranché dans ce visualiseur.
- Les profils construits descendent ; aucune preuve ne porte sur toutes les gouttes des versants, tous les continents ou toutes les graines. La source courante est la graine 0 ; changer la graine nécessite de régénérer CP et les bassins ensemble.
- Aucun drainage de terrain, remplissage de cuvettes, recherche de chemin ou simulation d’érosion. Le coût d’évaluation de tous les noyaux et le portage GPU restent ouverts.

**Travail :** code GPT-6.1 Terra xhigh ; architecture et jugement par l’agent principal. Syntaxe et aperçu ciblé avant présentation ; aucun banc, balayage multi-seeds, commit ni push. Tag de piste en attente d’un commit demandé.

**Aperçu :** globe et bassin principal comparés à pose identique, réseau désactivé puis affiché ; aucune erreur JavaScript au chargement. Les grandes chaînes restent reconnaissables et les nouvelles vallées sont visibles ; les branches restent très directes et certaines sont masquées par la maille. L’éclairage d’inspection suit la caméra dans les deux modes. Captures de travail `x64/GlobalBasins/*-lit.png`. Ce constat ne valide ni les croisements ni un chenal en eau.

### 2026-10-27 · Portage global natif sur contrôles grossiers · rejeté

**Constat utilisateur :** relief CP effacé, géométrie dégradée et cours trop rectilignes. Les raccordements des nappes ne validaient pas la morphologie.

**But :** juger le réseau global avec le terrain natif, ses matériaux, son atmosphère et ses commandes de vol, de l’orbite à la berge. Ce mode reprend le module cellulaire de la section 12 et le chenal de la section 13 ; les anciens modes natifs régionaux restent distincts.

**Données :**
- `tools/export-global-basins.cjs` exécute le même générateur de réseau et exporte tous les segments fluviaux et côtiers de la sphère, les contrôles CP et un index spatial fixe.
- Graine 0 uniquement : 74 412 segments fluviaux, 4 154 côtiers, 130 050 sommets de contrôle CP ; tampon d’environ 46 Mo. Aucun raster final du relief fluvial ni fenêtre de remplacement.
- Le format V3, marqueur `−271028`, est décrit dans `tools/global-basins/README-format-natif.md`. Le moteur valide dimensions, sections et indices avant chargement.
- Les directions sont séparées en float principal et résidu. Les différences planétaires sont prises en double avant conversion des petits décalages en flottants ; le champ ne dépend pas de la caméra.

**Terrain :**
- `GlobalBasin.hlsli` retrouve les triangles de contrôle CP et évalue les mêmes arcs, profils, supports compacts et opérateurs de chenal sur la sphère. `Terrain.hlsli` l’appelle avant les anciens chemins régionaux.
- Le contrôle CP est celui du globe grossier. Le nouveau mode n’est pas l’élévation complète originale de CP inchangée : sa structure intermédiaire est celle du module partagé.
- Une première bande de `MountainousHigh` CP sous 1 km enrichit le relief. Sa différence fin/grossier est pondérée par les montagnes, bornée à 10 % du relief latéral et nulle dans le chenal et à la côte.
- La carte planétaire et les passes de sol utilisent ce même relief global ; les autres modes gardent leur chemin antérieur.
- Dans ce mode, la carte régionale conserve le sol pour la brume et les matériaux, avec canaux de lacs et d’aire drainée à zéro. Le drainage historique de la carte n’est pas exécuté ; il ne fournit ni le réseau ni les niveaux d’eau du nouveau module.

**Eau :**
- Le calcul du terrain conserve le fond brut et ajoute à chaque sommet le niveau d’eau, la distance signée au chenal et la hauteur de contrôle CP.
- La passe d’eau reprend les mêmes indices et directions du maillage natif. Une instance porte la mer de niveau 0 ; l’autre porte le profil fluvial. Les masques interpolés séparent mer, chenal et terre.
- La position d’eau vient du niveau déjà calculé, sans relèvement pour contourner le sol. Y masque la passe d’eau et conserve le fond et la caméra.
- Les contours sont approchés par les interpolants du maillage natif. Ce premier portage ne découpe pas chaque triangle aux rives comme le visualiseur local ; la qualité du contact et de l’approche reste à juger.
- Les objets et les plantes sont exclus du masque d’eau global ; les objets réutilisent l’évaluation de leur sol, les plantes interrogent les seuls arcs fluviaux pour le masque.

**Parcours :** `tools/lance-global-basins-planete.ps1`, exécutable isolé dans `x64/GlobalBasinsNative/bin/`, palette `tools/tests/2026-10-27-global-basins.txt`. F1 orbite, F2 bassin complet, F3 source haute, F4 confluence, F5 collecteur, F6 embouchure, F7 berge, F8 relief du bassin. Le bassin est choisi par ses branches et son altitude ; la source haute est vers 3 652 m. Le soleil, les caps et les positions sont dérivés du réseau. La berge se regarde à 100 m au-dessus du sol, avec un angle visant le collecteur ; la dernière vue montre un contrôle élevé à environ 100 km du cours le plus proche. `-SansPlantes` et `-SansEau` sont disponibles ; l’environnement est restauré par le lanceur.

**Portée :** fonction globale pour la graine préparée, avec un parcours d’inspection dans un bassin complet. Ce n’est pas une hydrologie validée pour toutes les graines. La géographie CP reste grossière, le chenal garde sa largeur uniforme de 600 m et sa profondeur nominale de 8 m ; débit, deltas, détail de versant complet et qualité des transitions de maillage restent ouverts.

**Travail :** code GPT-6.1 Terra xhigh ; architecture et jugement par l’agent principal. Compilation et aperçu natif requis avant présentation ; aucun banc ni balayage de graines. Aucun commit ni push ; tag en attente d’un commit demandé.

**Aperçu natif :** compilation Release isolée réussie ; les captures couvrent orbite, source, relief élevé, confluence, embouchure, berge et confluence sans eau. Les vues de confluence et d’embouchure montrent le raccord des nappes ; masquer l’eau conserve le terrain creusé. La source garde un cap large et le relief reste trop lisse ; les matériaux et l’atmosphère du moteur ne suffisent pas à valider la morphologie. Les captures indiquent un coût GPU sensible et des cadences variables ; aucune mesure dédiée ni stabilité en mouvement n’est validée. Le premier démarrage a demandé plusieurs minutes dans certains lancements. Images `x64/GlobalBasinsNative/native-*.png` ; utilisateur contrôleur du vol.

### 2026-10-27 · Intégration CP complet avec profil grossier · remplacée par V4

**Statut :** reprise du portage après rejet du relief lissé. La première version et son contrôle insuffisant sont dans [l’historique](#les-essais-remplacés).

**Composition :**
- `Terrain.hlsli` évalue `ComplexPlanetElevation` complet à la fréquence courante et conserve sa rugosité.
- Le réseau mondial de la section 12 fournit le profil W, la distance au chenal et sa profondeur nominale de 8 m.
- Le terrain devient `lerp(CP, W - profondeur, integration * masque)`.
- Le masque vaut 1 dans le chenal et décroît continûment à 0 sur 3 km depuis la rive, contre 120 km auparavant.
- Au-delà de cette portée, chaque hauteur est exactement celle du graphe CP complet ; aucune bande de montagne intermédiaire n’est retirée.
- Les contrôles CP grossiers servent encore à la structure du réseau et au profil W, jamais à remplacer le sol hors vallée.
- La carte régionale évalue toujours CP original ; elle reste stable pendant la comparaison et ne lance pas le drainage historique dans ce mode.

**Avant/après :**
- B bascule CP original / CP + vallées ; même pose, même soleil, même taille d’image et mêmes réglages.
- Le GPU est synchronisé avant le changement du poids dans le tampon ; l’historique temporel est invalidé.
- Le verrouillage au sol reste suspendu après B jusqu’au prochain déplacement pour ne pas changer le cadrage.
- `-Reference` et `MYPLANETENGINE_GLOBAL_REFERENCE=1` démarrent en référence CP.
- Y masque l’eau sans changer le lit ; les rivières sont masquées en référence, la mer reste présente.
- Les normales fines, le terrain et les placements utilisent le même état ; la référence mer vient du CP complet.

**Données et vol :**
- Format V3, graine 0, réseau et index globaux inchangés ; 74 412 arcs fluviaux, 4 154 côtiers, environ 46 Mo.
- Le champ 29 porte la transition de 3 km ; le champ 45 porte le poids d’intégration, 0 ou 1 pour la comparaison.
- `tools/lance-global-basins-planete.ps1`, exécutable isolé `x64/GlobalBasinsNative/bin/`, palette `tools/tests/2026-10-27-global-basins.txt`.
- F1 orbite, F2 bassin complet, F3 source, F4 confluence, F5 collecteur, F6 embouchure, F7 inspection de vallée, F8 relief.
- Les cadrages rapprochés sont surélevés pour comparer CP complet ; les altitudes sont absolues et identiques entre les modes.
- Le lanceur réutilise l’export s’il est à jour ; il restaure ses variables d’environnement.

**Limites :**
- Le profil du réseau grossier peut dépasser CP : la composition peut alors relever le sol dans son influence.
- Ce spike ne résout pas encore le dessin artificiel des branches, la largeur uniforme de 600 m, les débits ou les deltas.
- La côte exacte CP peut différer de celle utilisée pour construire le réseau ; le raccord de l’eau à la mer doit être inspecté.
- Les contours d’eau restent interpolés sur la maille native ; mouvement et transitions de maille restent ouverts.
- Cette composition locale conserve CP mais ne démontre pas encore une construction commune des crêtes et du réseau adaptée à toutes les graines.

**Vérification :** compilation Release isolée réussie ; paires natives source, confluence et relief au même cadrage et au même éclairage inspectées dans `x64/GlobalBasinsNative/cp2-*-avant.png` et `cp2-*-apres.png`. La vue de relief conserve les montagnes CP. La confluence reste un tracé trop uniforme et rectiligne ; à la source, le niveau W relève le sol CP. Le contrôle visuel confirme la conservation du terrain hors influence, mais rejette encore la morphologie du réseau comme intégration aboutie. La touche B a été actionnée dans le moteur ; aucun banc ni balayage de graines, aucune validation complète en mouvement. Le coût des requêtes globales reste élevé.

**Travail :** code GPT-6.1 Terra xhigh ; architecture, orchestration et jugement par l’agent principal. Aucun commit ni push ; tag en attente d’un commit demandé.

## Le journal des spikes

### 2026-10-27 · Profils CP et morphologie V4

- **Règle :** une incision ne relève jamais CP ; profil commun borné par les sondes de l’axe et des berges en CP32/256, marge 8 m, enveloppe descendante et facteur d’amont `d/(d+20 km)`.
- **Côte :** premier contact marin interpolé depuis chaque source ; retrait des tronçons marins et des sources que le CP fin place en mer, aucun routage de remplacement.
- **Courbes :** bruits de gradient de pas 12 et 3,5 km, poids 1 et 0,45 ; déplacement limité par les secteurs et 2 200 m ; fondu de 1,2 km aux jonctions.
- **Largeur :** demi-largeur 4 m à la source puis base 24√(sources), fluctuation cohérente de pas 9 km et coefficient 0,3 ; évasement ×2,2 sur les 25 derniers km. Aucun bras de delta ajouté.
- **Données :** V4, 1 456 417 segments fluviaux, 196 nouveaux contacts, 268 Mo ; phases seedées et subdivision adaptative selon max(10 m, 25 % de la demi-largeur), pas cible de 125 m à 1 km ; hash 20 km et support 12 km, sections alignées sur 64 floats.
- **Référence :** ancien exécutable et données conservés dans `x64/GlobalBasinsAvantMorpho` ; nouveau mode dans `x64/GlobalBasinsMorpho`, même pose et finesse 0,25 dans les captures comparées.
- **Vérification :** Release réussi ; source, confluence et embouchure comparées au même cadrage, soleil et finesse. Cap de source supprimé et contact marin rétabli ; largeurs variables, organisation des branches encore géométrique. Pas de delta ramifié ni de validation générale du mouvement ; coût sensible. Captures `x64/GlobalBasinsMorpho/*-{avant,apres}.png`. Aucun banc ni balayage de graines.
- **Jalon :** `jalon/rivieres-cp-resultat-prometteur`, sauvegarde demandée par l’utilisateur le 27 octobre 2026 sur la branche du tag `piste/rivieres-spikes`. Ce repère conserve les sources et outils des spikes ; les exécutables, caches et captures sous `x64/` restent locaux.
- **Travail :** code GPT-6.1 Terra xhigh, architecture et jugement par l’agent principal. Résultat prometteur, sans validation générale de l’hydrologie ni des performances.

### 2026-10-27 · Reprise sur CP complet et comparaison

- **Rejet précédent :** relief effacé et cours artificiels ; les seuls raccords de nappes ne suffisaient pas à accepter le portage.
- **Terrain :** retour au graphe CP complet et à sa rugosité ; influence du chenal limitée à 3 km depuis la rive, CP exact au-delà.
- **Comparaison :** B bascule CP original / CP + vallées sans déplacer la caméra ni le soleil ; historique temporel réinitialisé. Y conserve le lit en masquant l’eau.
- **Carte :** référence CP stable dans les deux états, aucun drainage historique ajouté au mode.
- **Limite assumée :** W reste issu du réseau grossier et peut relever localement le sol ; tracés, côte et détail du réseau restent à inspecter.
- **Vol :** même palette F1 à F8, cadrages rapprochés surélevés ; option `-Reference` et export réutilisé quand il est à jour.
- **Vérification :** Release isolé réussi ; trois paires de vues natives au même cadrage inspectées. Relief CP conservé, mais source localement relevée et confluence trop rectiligne ; morphologie fluviale non validée. Captures `x64/GlobalBasinsNative/cp2-*-avant.png` et `cp2-*-apres.png`. B actionné dans le moteur ; aucun banc ni balayage de graines. Coût global encore élevé.
- **Travail :** code GPT-6.1 Terra xhigh, architecture et jugement par l’agent principal ; aucun commit ni push. Tag en attente d’un commit demandé.

### 2026-10-27 · Portage natif du réseau global

- **Mode :** `MYPLANETENGINE_GLOBAL_BASINS`, format V3 distinct ; tous les noyaux fluviaux et côtiers, contrôles CP et index spatial de la sphère, graine 0, environ 46 Mo. Aucune fenêtre de remplacement du terrain.
- **Fonction :** mêmes profils et chenal 600 m / profondeur nominale 8 m que le prototype ; requêtes analytiques en HLSL, première bande `MountainousHigh` CP sous 1 km, bornée et nulle aux rives.
- **Rendu :** terrain brut et métadonnées d’eau dans les mêmes sommets ; passes mer et fleuves depuis les mêmes indices natifs. Y masque l’eau sans déplacer le fond. Les contours restent interpolés par la maille native.
- **Carte :** le mode global n’exécute pas le drainage historique ; carte de sol pour la brume et les matériaux, réseau et eau fournis par le champ global.
- **Vol :** `tools/lance-global-basins-planete.ps1`, palette F1 à F8 ; bassin 34, 16 sources, 15 confluences, source à 3 652 m. Orbite, bassin, source, confluence, collecteur, embouchure, berge et relief éloigné du cours.
- **Vérification :** Release isolé réussi ; captures natives avec et sans eau, source, relief, raccord côtier et globe inspectés. Source encore large, relief trop lisse et coût GPU sensible ; premières initialisations parfois longues. Mouvement, LOD et qualité générale restent à juger en vol. Captures `x64/GlobalBasinsNative/native-*.png`.
- **Travail :** code GPT-6.1 Terra xhigh, architecture et jugement par l’agent principal ; aucun banc, balayage de graines, commit ni push. Tag en attente d’un commit demandé.

### 2026-10-27 · Retour au globe pour situer l’essai d’eau

- **Constat utilisateur :** la vue locale de mise en eau rompt le contexte de la sphère et le terrain côtier plat rend le creusement peu lisible.
- **Entrée :** globe centré sur le site choisi par le modèle, repère et emprises de 32 km ; parcours Planète → Bassin → Lit et eau. L’ancienne adresse d’eau redirige vers cette entrée.
- **Détail :** accès explicite, fil d’Ariane, retours planète/bassin et localisateur construit depuis les données CP. La portée locale du test est annoncée ; aucune mise en eau mondiale revendiquée.
- **Aperçu :** ancienne adresse redirigée vers le globe ; repère visible, clic vers le bassin puis vers le détail vérifiés sur le même bassin 55. Aucune erreur JavaScript. Captures `x64/GlobalWater/context-*.png`.
- **Périmètre :** guidage et cadrage, sans modification de réseau, de terrain, de niveau d’eau ou de graine. Code GPT-6.1 Terra xhigh, aperçu ciblé, aucun banc ni commit.

### 2026-10-27 · Lit et mise en eau du réseau global

- **But :** traduire le même réseau global en lit, rives et nappe d’eau ; aucun changement de seed, de courbe ou de jonction.
- **Profil :** `sampleChannel` reprend `W` et `D`, largeur uniforme 600 m et profondeur nominale 8 m ; relief latéral nul à la rive, lit prolongé sous la mer. La référence du globe reste accessible.
- **Maillage :** fenêtres de 32 km / pas de 125 m, contrôles CP interpolés comme dans le globe ; découpe commune côte puis chenal, sommets de rive partagés et une seule union mouillée à la confluence.
- **Lecture :** `tools/global-basins/water.html`, Collecteur / Confluence / Embouchure ; Berge rapproche une rive, Eau masque la nappe en gardant le lit et la pose. Précision métrique locale, profondeur graphique logarithmique et amplification identique terrain/eau.
- **Limites :** largeur constante, profondeur représentée approximativement par la maille, côte et relief CP grossiers ; ni débits, ni deltas, ni nouveaux détails de versant ou portage natif.
- **Aperçu :** confluence et embouchure du bassin 55 inspectées ; lit conservé sans eau, coupe des triangles du collecteur avec environ 8 m d’écart fond/eau. Approche de 180 à 100 m et rotation, même maillage conservé, aucune erreur de chargement. Rendu sobre et profondeur peu lisible à grande échelle ; captures `x64/GlobalWater/review-*.png`.
- **Travail :** code GPT-6.1 Terra xhigh ; architecture et jugement par l’agent principal. Aucun banc, balayage de graines, commit ni push ; tag en attente d’un commit demandé. Détails : section 13.

### 2026-10-27 · Réseau global dans les cellules terrestres

- **Remplace :** arcs libres vers les exutoires, qui pouvaient se croiser et traverser des baies. La méthode précédente passe dans la partie « Les essais remplacés ».
- **Structure :** polygones terrestres convexes découpés au zéro CP, ports d’arête partagés, exutoires par composante et forêt seedée ; Voronoï macroscopique avant l’ordre de hash. Aucun choix de route par pente ou distance optimale dans CP.
- **Courbes :** bras dans des éventails disjoints aux confluences ; une seule cubique de port à port dans les cellules de passage, sans le coude du centre. Contrôles contenus dans le domaine et progression monotone ; ports et altitudes hérités.
- **Profils :** exutoires à 0, sources à leur hauteur CP positive, niveaux intermédiaires croissants vers l’amont. La courbure change la géométrie, pas les niveaux de jonction.
- **Champ :** noyaux compacts de 450 km, repli continu vers CP, largeur de structure 120 km ; index spatial fixe. Le terrain et le diagnostic lisent les mêmes profils et courbes.
- **Jeu courant :** graine 0, 35 956 cellules, 217 exutoires, 610 sources, 74 412 petits arcs. La dépendance au maillage et la conservation des grands massifs restent à travailler.
- **Portée :** non-croisement et confinement concernent le domaine côtier grossier ; aucune validation du champ CP fin ni de toutes les gouttes des versants. Visualiseur sans surface d’eau, toujours hors moteur.
- **Aperçu :** globe, bassin, embouchure et île de 131 sommets inspectés ; courbes plus douces et raccords visibles, retours serrés encore schématiques. Option Voir les axes masqués pour lire la topologie sans la confondre avec l’incision de la grille. Captures `x64/GlobalBasins/cell-review-*.png` ; aucune erreur de chargement.
- **Travail :** code GPT-6.1 Terra xhigh, architecture et jugement par l’agent principal ; syntaxe et aperçus ciblés, aucun banc, balayage multi-seeds, commit ni push. Tag en attente d’un commit demandé.

### 2026-10-27 · Bassins sur la sphère CP entière · premier prototype

- **But :** juger l’organisation mondiale avant un nouveau portage natif ; conserver les contrôles CP et supprimer la fenêtre côtière greffée.
- **Source :** graine commune 0, sphère de 32 514 directions ; hauteur CP complète filtrée à 30 km, poids montagneux et 4 154 zéros côtiers. Les détails sous la grille ne sont pas reconstruits.
- **Organisation :** composantes terrestres géométriques, sites côtiers espacés de 600 km dans chaque composante, cellules sphériques et arbres seedés ; 208 sites, 781 sources, 1 354 tronçons. Aucun routage sur les pentes.
- **Relief :** profils descendants hérités, interpolation commune `1/d⁴` avec supports côtiers de niveau 0, relief latéral guidé par CP sur 120 km. Les axes restent schématiques ; une baie traversée ou des branches qui se croisent ne sont pas encore résolues.
- **Comparaison :** `tools/lance-bassins-globaux.ps1`, CP actuel / CP + bassins à pose, lumière, amplification et grille identiques. Subdivision globale en quatre, 130 050 sommets ; zéros côtiers insérés comme sommets partagés.
- **Portée :** visualiseur de structure mondiale, sans surface d’eau, sans intégration globale au moteur ni validation hydrologique. Une seule graine préparée ; ni toutes les pentes ni les croisements ne sont démontrés.
- **Travail :** code GPT-6.1 Terra xhigh ; architecture et aperçu ciblé par l’agent principal. Aucun banc, balayage de graines, commit ni push ; tag en attente d’un commit demandé. Détails : section 12.

### 2026-10-27 · Trois bassins voisins sur une côte CP

- **But :** passer du bassin isolé à trois réseaux voisins, avec leurs crêtes communes et des exutoires côtiers issus de CP.
- **Côte :** zéro de l’élévation CP complète filtrée à 500 m ; recherche déterministe d’un graphe côtier sur la sphère, sans drainage. 256 points sur 75 km, graine commune 0 ; repère proche de 2,868° N / 78,750° E. Sans tronçon valide, échec explicite, pas de côte inventée.
- **Champ commun :** `v=y−C(x)`, domaine latent injectif conservant `v`, minimum des distances des trois arbres, profil `W(v)` partagé. 57 tronçons dans le jeu courant ; subdivisions et longueurs seedées, raccords hérités.
- **Côte et versants :** enveloppe `1−exp(−(v/5000)²)` pour une remontée progressive ; lit de 4,5 m. Deux contrôles CP 192² issus de MountainBase et de la différence de Mountainous à deux filtrages ; modulation positive du relief latéral, nulle aux rives.
- **Pour juger :** `tools/lance-bassins-cotiers.ps1`, vues Ensemble / Crête commune / Embouchure, eau et relief CP activés. La préparation et le modèle partagent la même seed ; les anciens spikes restent accessibles.
- **Aperçu :** même pose avec/sans Relief CP, graine 0 ; trois réseaux rejoignent la mer, crêtes continues entre bassins. Relief plus riche, encore schématique, traces d’échantillonnage visibles. Une seule côte et une seule graine inspectées.
- **Natif V2 :** format distinct avec côte, cellules et contrôles CP ; fenêtre de 100 km et limite amont dérivée de la plus haute source plus 8 km, tous les cours dans le cœur non mélangé. `tools/lance-bassins-planete.ps1`, palette calculée depuis le repère côtier et les branches ; seed 0 uniquement, autres graines refusées explicitement.
- **Compilation :** un calcul CP normal et un calcul CP filtré factorisés dans les chemins historiques, après une compilation trop longue ; pas de changement de leurs formules. Release réussi avec les avertissements Materials connus. Ensemble natif inspecté : côte irrégulière et relief lisibles, cours fins à 40 km ; aucun banc ni jugement en mouvement.
- **Embouchure native :** pose depuis le large calculée depuis le même exutoire ; raccord rivière/mer visible au même niveau, rives encore anguleuses et eau uniforme. Captures `x64/BassinsCotiers/native-ensemble.png` et `native-embouchure.png`.
- **Travail :** code GPT-6.1 Terra xhigh ; architecture et jugement par l’agent principal. Aucun banc, balayage multi-seeds, commit ni push ; tag en attente d’un commit demandé.

### 2026-10-27 · Premier rendu natif du noyau de bassin

- **Mode :** `MYPLANETENGINE_BASSIN` charge un format analytique distinct avant l’ancien Dendry ; noyaux HLSL aux coordonnées fixes de la planète, sans carte de hauteurs ni mips du bassin.
- **Structure :** même modèle JS, graine 13, structure variée et sources hautes ; 21 cellules et 12 060 sommets de ruban. Graine propre de Complex Planet conservée à 0.
- **Détail CP :** différence fin/grossier sous environ 1 km, bornée à ±10 % du relief latéral et nulle aux rives. Niveau d’eau indépendant des bosses du détail.
- **Rendu :** matériaux, éclairage et atmosphère du moteur ; eau découpée par le champ signé. Première confluence inspectée, continue à cette vue ; eau encore uniforme et berges abruptes.
- **Ensemble :** côte trop rectiligne, mer en bande et réseau peu lisible à 20 km d’altitude ; fusion régionale encore insatisfaisante. Captures conservées sous `x64/BasinNoise/planete-*.png`, sans prétention de validation du rendu global.
- **Démarrage :** première initialisation Release longue et fortement consommatrice de mémoire lors de la préparation des shaders ; aucun banc de performance. Nombre d’images d’aperçu configurable par `MYPLANETENGINE_CAPTURE_FRAMES`, défaut conservé à 200.
- **Région :** fenêtre de 64 km centrée sur 34° N / 40° O ; centre correspondant à `y=9 km` du bassin, rayon 6 378 km. Bordure de transition de 8 km vers CP hors zone jugée ; essai local, pas une organisation planétaire des bassins.
- **Pour juger :** `tools/lance-bassin-planete.ps1`, ouverture sur la vue générale ; palette `tools/tests/2026-10-27-bassin-noise.txt`, F1 à F5. Export analytique en répertoire temporaire ; paramètres de lancement restaurés.
- **Contrôle :** compilation Release x64 réussie ; captures ponctuelles sans fenêtre, pas de banc, de balayage multi-seeds ni de validation en mouvement. Code GPT-6.1 Terra xhigh, jugement par l’agent principal ; aucun commit ni push, tag en attente d’un commit demandé.

### 2026-10-27 · Ramifications et crêtes moins répétitives

- **Demande :** varier la structure du bassin, garder les sources hautes, la descente et les raccordements ; poursuivre ensuite le rendu dans le moteur Complex Planet.
- **Subdivisions :** fin par hash aux niveaux 2 à 4, au plus 31 noyaux ; poursuite 0,74 au niveau 2 puis 0,52 au niveau 3 ; partages de 24 à 76 %, confluences déphasées.
- **Champ commun :** `u=x+650 N(seed+4099,x/9000+17,31,y/4200−7,1)` m ; `du/dx>0,54`, `y` conservé. Vallées, crêtes et rives subissent la même transformation.
- **Relief latéral :** modulation positive `1+0,22 N(seed+239,x/5200+3,8,y/6000−2,4)` ; nulle aux rives par multiplication. Pas de relief indépendant superposé aux cours.
- **Comparaison :** Structure variée activée au départ ; désactivation restitue l’arbre précédent, sans recadrage. Le nombre réel de tronçons et sources est affiché.
- **Aperçu :** Ensemble et Sources à pose fixe, détail désactivé, graine 13 : 21 tronçons et 11 sources. Répartition plus asymétrique ; profils encore schématiques, naturel complet non acquis.
- **Travail :** code GPT-6.1 Terra xhigh ; jugement par l’agent principal. Aucun banc, balayage multi-seeds, commit ni push ; tag en attente d’un commit demandé.

### 2026-10-27 · Sources de hauteurs variées dans le même bassin

- **Retour utilisateur :** structure encourageante, motifs répétitifs ; faire naître certains ruisseaux plus haut en montagne. La répétition vient aussi du noyau binaire et du détail à fréquence unique, pas seulement du visualiseur.
- **Portée :** modifier uniquement les huit cellules terminales, par hash dédié ; fin `max(yDépart+800,18 000 × (0,72+0,38 h²))` m. Les cellules parentes et les bifurcations restent identiques.
- **Profil :** `W=1 250 t+2 200 max(t−0,45,0)²` m, `t=y/18 000` ; dérivée positive, eau et terrain communs, aval jusqu’à 8,1 km identique. Cette variante change aussi le relief amont ; elle ne relève pas l’eau sur un ancien terrain.
- **Comparaison :** case Sources hautes activée au départ ; désactivée, ancien module exact. La pose est conservée à la bascule. Vue Sources ajoutée pour voir les têtes au-dessus des crêtes proches.
- **Détail facultatif :** 550 / 290 / 150 m, champs de gradient tournés, poids 0,6 / 0,3 / 0,1 ; référence à 550 m conservée. Détail désactivé au départ.
- **Aperçu :** ensemble et sources à pose fixe sur graine 13 ; trois têtes vers 2 060 à 2 284 m, cinq vers 1 159 à 1 355 m dans le profil. Descente et raccordements conservés par construction ; sources synthétiques et répétitions du noyau encore présentes.
- **Travail :** code GPT-6.1 Terra xhigh, contrôle visuel par l’agent principal. Aucun banc, balayage multi-seeds, commit ni push ; tag en attente d’un commit demandé.

### 2026-10-27 · Noyau de bassin cohérent et descendant · spike local

- **But :** faire naître vallées, crêtes et cours raccordés d’un même module, avant le détail Complex Planet.
- **Module :** cellules seedées divisées sur trois générations, 15 noyaux finis ; chaque parent transmet position et largeur à deux enfants à sa bifurcation. Aucun routage ni drainage d’un relief antérieur.
- **Descente :** coordonnée amont `y` conservée par les courbes ; profil linéaire `W=1 250 y / 18 000` m, mer à zéro. La preuve porte sur les axes et leurs connexions, pas sur toutes les pentes ni sur la planète.
- **Relief :** distance commune par section et cap ; montée latérale non saturante `1,3 × (hypot(max(D,0),80)−80)^0,9`. Rives partagées, lit de 4,5 m ; détail de gradient à 550 m facultatif, désactivé au départ.
- **Visualiseur :** `tools/basin-noise/`, domaine 22 × 23,5 km, grille fixe 448², eau activée. Un bassin macro ; les trois générations internes ne sont pas trois octaves du bassin de référence. Phasor demeure accessible séparément.
- **Jugement préalable :** ensemble, confluence eau/lit, détail et versant inspectés sur graine 13. Connexions et crêtes communes lisibles ; rendu encore schématique, sources synthétiques, pas de delta traité.
- **Travail :** code GPT-6.1 Terra xhigh ; architecture et jugement par l’agent principal. Aucun banc, balayage multi-seeds, commit ni push ; tag en attente d’un commit demandé.

### 2026-10-27 · Collecteurs du bassin Phasor en eau

- **Décision utilisateur :** conserver uniquement les collecteurs en eau pour l’instant ; aucun drainage local calculé pour les ravines.
- **Profil :** `referenceSample.water`, indépendant du détail Phasor ; lit de référence incisé de 3 m.
- **Rives :** découpe des triangles à distance signée zéro ; sommets communs eau/terre au profil. La même triangulation sert avec et sans eau.
- **Rendu :** nappe opaque bleue, normale du profil ; avec eau, le terrain du chenal n’est pas dessiné par-dessus. Sans eau, le lit redevient visible. Source des auteurs inchangée.
- **Calcul :** géométrie de rive mise en cache au changement de bassin/graine ; caméra et case Eau ne relancent pas de drainage ou de reconstruction.
- **Contrôle :** syntaxe et aperçu eau/lit sur graine 13, même pose ; aucun banc ni mesure multi-seeds. Code GPT-6.1 Terra xhigh, aucun commit ni push ; tag de piste en attente d’un commit demandé.

### 2026-10-27 · Phasor reproduit puis branché au bassin · spike à juger

- **Référence :** dépôt officiel TerrainEnhancement, état `e0c75976013514e713bc05215927d4ec46462075` ; cartes et shaders conservés dans `tools/phasor-reference/`.
- **Adaptateur :** `tools/phasor-spike/` ; bassin de référence à une octave, région 20 km, textures et grille 512², échelle fixe de 3 km.
- **Réglages :** fréquence 50, amplitude 0,04, second niveau ×3 et ×0,3 comme la démo ; lissage d’orientation de 16 passes pour le bassin. Amplitude pilotée par distance au collecteur et pente physique, sans carte hydrologique externe.
- **Comparaison :** hauteur originale identique avant/après, normales calculées sur la hauteur finale à l’échelle physique ; pose conservée à la bascule. Vue Versant et graine 13 par défaut.
- **Jugement préalable :** nouveaux sillons visibles sur les versants, grandes formes conservées. Référence des auteurs puis bassin inspectés ; aucun banc ni mesure multi-seeds.
- **Limites :** géométrie des ravines, sans mise en eau ni garantie de réseau global ; domaine régional, hors moteur. Les cellules triangulaires précédentes sont non concluantes visuellement et mises de côté.
- **Travail :** code GPT-6.1 Terra xhigh ; architecture et jugement par l’agent principal. Aucun commit ni push ; tag de piste en attente d’un commit demandé.

### 2026-10-27 · Bassins communs avant détail CP · non concluant visuellement

- **Architecture :** une subdivision de bassin crée simultanément tronçon fluvial, flancs et partage intérieur ; les détails CP viennent ensuite. La référence intégrée à une octave est conservée en comparaison.
- **Structure :** profondeur 3, 47 triangles et 15 cours par racine ; exposant transversal 1,4 ; bornes de 1,8 à 3 km ; jonctions à 25–40 % de la montée disponible, sources à 65–80 %.
- **Sommets intérieurs :** M à 18–40 % du bord haut vers J, montée à 90–115 % de celle du bord ; triangle de crête linéaire pour raccorder les sous-bassins.
- **Champ commun :** déformations à 12 km et 3,7 km, déplacement limité à 600 m ; largeur initiale 200 m divisée par deux jusqu’à 25 m, lit de 3 m.
- **Détail :** RidgedMulti / Billow bornés à 10 % du relief au-dessus du fond, nuls sur les arêtes ; case Détail CP pour voir la structure seule. Cache RGBA32F des valeurs du module, sans routage dans un relief existant.
- **Visualiseur :** comparaison sans recadrage ; palette d’altitude continue ; vue d’ensemble à 30 km, inclinaison 65°, maille centrale 64 m.
- **Jugement initial :** module commun visible sans CP, formes encore très géométriques ; amélioration visuelle non acquise. Aucun banc, prévisualisations uniquement sur seed 14.
- **Travail :** code GPT-6.1 Terra xhigh ; architecture et jugement par l’agent principal. Aucun commit ni push ; cache `bassins-communs-1`, tag de piste en attente d’un commit demandé.

### 2026-10-27 · Affluents latéraux écartés, retour au bassin seul

- **Jugement utilisateur :** cours hyper rectilignes coupant les montagnes, aspect de nervures de feuilles ; résultat moins bon.
- **Décision :** conserver le bassin à une octave et les corrections du visualiseur ; désactiver les affluents au démarrage. Leur essai reste accessible par une case décochée.
- **Cause :** tracés obliques puis recomposition d’une bande, sans structure commune des grandes crêtes et du réseau.
- **Réglage :** `tributaries=false` dans le modèle et le démarrage ; case Essai des affluents décochée ; cache `reference-bassin-1`.
- **Contrôle :** syntaxe seulement, aucun banc ni rendu ; code GPT-6.1 Terra xhigh. Aucun commit ni push.

### 2026-10-27 · Bassin fixe et affluents de versant · essai écarté

- **Retour utilisateur :** le bassin à une octave est cohérent ; quatre niveaux produisent des bandes parallèles et le visualiseur change trop l’étendue. Les sources principales restent au pied des montagnes.
- **Conservation :** bassin à un niveau, axes, côte et profils principaux ; bascule des ruisseaux vers la référence exacte.
- **Affluents :** cellules de 3,2 km, longueurs de 2,2 à 3,3 km, têtes à 84 % du demi-versant ; montée `A × smoothstep(v)`, avec `A=(0,4+0,3 × potentiel) × écart/(écart+1,5 km)` km ; largeur de 40 m effilée jusqu’à zéro, lit de 3 m.
- **Relief :** enveloppe de vallée de 250 m, relief latéral sur 120 m ; versants recomposés autour du profil partagé, sans conservation stricte de l’ancien microrelief. Poids égal à un dans le chenal ; raccord au collecteur par un même profil d’eau et de lit. Mélange continu des cellules voisines, éteint à la ligne de partage.
- **Visualiseur :** grille cubique fixe de 65,536 km de côté, maille centrale de 8 à 128 m ; orbite liée à la cible de référence ; Réseau entier par défaut, vues locales sur un affluent réel. Programmes spécialisés par mode et cache GPU des 64 valeurs de nœuds, calculées par les fonctions CPU inchangées.
- **Contrôle :** syntaxe et prévisualisation, aucun banc à la demande utilisateur. Une échelle d’affluents et collecteurs encore parallèles ; pas de validation hydrologique globale.
- **Travail :** code GPT-6.1 Terra xhigh ; architecture et jugement par l’agent principal. Aucun commit ni push ; cache `versants-1`, tag de piste en attente d’un commit demandé.

### 2026-10-26 · Bassins intégrés au relief · spike à juger

- **Architecture :** potentiel grossier à 50 km, structure commune des profils, vallées et crêtes, puis détails des versants. Le potentiel simplifié remplace provisoirement l’entrée grossière de complexplanet.
- **Profils :** incréments positifs hérités des ancêtres, raccords parent/enfants à même altitude, montée terminale jusqu’aux sources ; le plan d’eau incliné reste dans l’ancien mode.
- **Réglages :** largeur multipliée par 0,47 par niveau ; effilement terminal sur 1 km ; enveloppe latérale de 80 m ; incision de 3 m ; RidgedMulti / Billow bornés à trois octaves. Après le premier cadrage trop lisse : crête `écart/(écart+1,5 km) × (0,6+1,2 × potentiel)` et modulation `0,25+2,5 × détail²` ; cadrage élargi à la confluence, cache `bassins-integres-2`.
- **Essai :** Bassins intégrés / CP indépendant / Relief simple ; nouvelle vue Versants / torrents ; seed 14 et quatre octaves pour le premier jugement.
- **Contrôle :** syntaxe, démarrage et cadrage visuel, repris après le réglage des crêtes ; aucun banc à la demande utilisateur. Drainage encore orienté et région locale, sans intégration au moteur.
- **Travail :** code GPT-6.1 Terra xhigh ; architecture et jugement par l’agent principal. Aucun commit ni push ; tag de piste en attente d’un commit demandé.

### 2026-10-26 · Relief CP adapté dans le visualiseur seedé · spike à juger

- **Composition :** groupes montagnes hautes/basses et collines de complexplanet, adaptés au gradient 2D ; RidgedMulti, Billow et Turbulence, puis mélange positif contraint par la vallée.
- **Réglages :** fréquences source divisées par R = 6 378 km, puissances multipliées par R ; lacunarités source ; montagnes basses et collines limitées à trois octaves, turbulences à deux. Aucun réglage par seed ou distance à la caméra.
- **Altitude latérale :** `0,25 + 1,5 × collines + 2,5 × montagnes × masque de massif`, en km, annulée à la rive par l’enveloppe de vallée. Le réseau et le profil d’eau sont conservés.
- **Rendu :** trois évaluations par sommet pour hauteur et normale interpolée ; le fragment garde uniquement le champ de rivière et la hauteur interpolée. A/B Relief CP / simple sans recadrage.
- **Jugement initial :** relief nettement enrichi sur seed 13 / 4 octaves ; simple prévisualisation, aucun banc conformément à la demande utilisateur.
- **Travail :** code GPT-6.1 Terra xhigh ; architecture, choix et jugement par l’agent principal. Aucun commit ni push ; tag de piste en attente d’un commit demandé.

### 2026-10-26 · Module fluvial fractal avec seed · spike à juger

- **Remplace :** les deux cours analytiques prédéfinis du visualiseur autonome ; historique dans la partie « Les essais remplacés ».
- **Module :** subdivisions dyadiques de cellules, de 1 à 4 octaves ; largeur de bassin de 20 à 28 km ; positions déterminées par hachage de la seed ; interpolation mère-filles continue.
- **Bruits :** déformation des cours par bruit de gradient 1D à quatre octaves, lacunarité 2 et gain 0,5 ; modulation des versants par bruit de gradient 2D à trois octaves, lacunarité 2,14, gain 0,5 et amplitude 30 %.
- **Profil :** pente de 14 à 24 m/km suivant la seed, fond à −3 m ; largeur des cours multipliée par 0,78 à chaque ramification. Les paramètres ne sont pas retouchés par seed.
- **Limite :** direction aval commune ; pas encore de couplage aux continents arbitraires de complexplanet.
- **Livraison :** Seed, +1 et Octaves dans le même visualiseur. Aucun banc pour cette itération, sur instruction utilisateur ; aucun commit ni push. Le tag attend un commit demandé.

### 2026-10-26 · Relief construit par les rivières · visualiseur autonome

- **Modèle :** une fonction unique autour d’un fleuve et d’un affluent ; profil de 20 m/km, fond à −3 m, chenaux de 130 à 240 m ; versants lisses sur 1,4 km et modulation bornée de 25 % de leur amplitude.
- **Géométrie :** projection sur une sphère de rayon 6 378 km ; maillage de 512² cellules, maille constante pendant la descente ; décalage sinusoïdal de la grille pour isoler le glissement.
- **Réglages de jugement :** mailles 8 et 16 m ; vues source, confluence et côte ; approches jusqu’à 3 m. Les mailles 64 et 128 m ne sont pas validées au sol.
- **Mesures :** 39 000 sondes sans coupure ni remontée ; CPU/GPU à 1,26 mm près ; erreur maximale de surface de 8,29 cm à maille 16 m sur les sondes du banc. Les images fixes sont identiques ; le glissement garde un écart moyen maximal de 0,125/255 au bord de côte proche.
- **Livraison :** `tools/lance-rivieres-simples.ps1`, sans compilation ni réseau. Rapport dans `x64/RiverFirst/rapport.json`.
- **Statut :** spike analytique hors moteur, sans commit ni push. Le tag attend le commit demandé ; aucune validation de l’intégration à complexplanet.

### 2026-10-26 · Maquette Dendry, tronçons continus et lit incisé · écartée après essai en vol

**Constat utilisateur :** mutations et scintillement importants à l’approche. Les bancs de profil et les captures fixes étaient insuffisants. La suite repart d’un relief unique construit autour des rivières ; proposition en section 8.

- **Remplace :** le profil sur champs interpolés, écarté ; [essais et mesures](#les-essais-remplacés).
- **Profil :** pente minimale 1 m/km ; marge 3 m sous Catmull-Rom mip 0 sur l'axe et les deux rives ; sondes au plus tous les 2,29 m. Les 194 156 nœuds descendent vers l'aval.
- **Couplage préalable :** 36 passes ; plafonds par les berges des autres branches, hors de leurs chenaux, tolérance de 5 cm ; propagation aval exacte sur le graphe partagé. Baisse de plus de 1 m sur 1,65 % des points, p95 nul et maximum 565,77 m. La relaxation reste non convergée : résidu auxiliaire maximal 0,617 m.
- **Berges :** rayons Hermite monotones, raccordés aux confluences ; retour du détail et des mips sur 100 m. La partition continue des incisions empêche une vallée voisine de supprimer la berge d'un autre cours.
- **Combinaison :** poids de berge `masque / (max(distance − demi-largeur, 0)² + 0,25²)` ; garde de chenal prolongée par `4 × distance extérieure²` ; minimum lissé sur 0,05 m. Aucun remblai au-dessus de la référence.
- **Précision :** projection et soustraction du cours en double précision ; suppression des marches de 0,3 à 0,8 m dues à l'ancien calcul en float planétaire.
- **Rendu :** 129 126 tronçons, 774 756 sommets d'eau ; index CSR de 512² cellules ; payload de 22,22 Mo ; erreur de niveau due à la simplification bornée à 4 cm. Ruban indépendant, couverture progressive entre 8 et 10 km du bord de la maquette.
- **Contrôle rivière :** 4 817 634 sondes ; 3 132 rives hors chenaux actives après incision, dépassement maximal 5,1 cm ; centres actifs sous l'eau d'au moins 18,5 cm. F10 garde une gorge raide et des ruisseaux masqués de loin.
- **Banc qualité :** trente lieux rejoués, 1 350 vues ; les 59 p95 du premier spike sont inchangés. La référence officielle reste hors seuil sur 22 des 57 p95 comparables.
- **Palette :** les changements de lieu maintiennent la caméra à la position demandée pendant douze images, pour que le sol de la vue précédente ne la remonte pas ; build Release vérifié.
- **Pour juger :** `tools/lance-rivieres.ps1`, douze boutons et F1 à F12. Sources glaciaires et delta restent les étapes suivantes.
- **État git :** sans commit ni push. Le tag de piste attend le commit demandé après jugement en vol.

## Les règles et les surcouches de la branche

**Les règles ajoutées à `principes.md`,** non reprises dans `main`.

**Dans « Le principe » :**
- **Une géométrie se valide aussi en mouvement.** Des vues fixes ne prouvent ni sa stabilité à l’approche ni son absence de scintillement ; distinguer le changement de relief du changement de son échantillonnage.
- **Une comparaison avant/après conserve la pose, l’échelle et la hauteur de référence.** Les normales correspondent à la géométrie affichée ; un changement d’ombrage ne remplace pas un changement de relief.

**L'eau suit le drainage, pas les bosses du maillage** (`../recherche-rivieres.md`).
- **Les sources et les exutoires appartiennent au graphe hydrologique :** ruissellement et fonte rejoignent un récepteur jusqu'à la mer ou un lac.
- **Le niveau d'eau descend vers l'aval,** sauf sur la surface plate d'un lac.
- **Tout abaissement du profil se propage vers l'aval.** La surface de l'eau et les berges se raccordent sans marche.
- **Un cours conserve ses connexions à toute distance.** Un champ filtré ne décide pas de sa topologie.
- **Le lit est creusé sous un profil d'eau indépendant.** Un delta se forme à l'exutoire côtier selon le débit.
- **Une géométrie construite autour des cours partage une seule fonction pour le fond, les berges et l’eau.** Son relief latéral s’annule aux rives ; le détail ne déplace pas le profil.
- **La rive appartient au terrain et à l’eau.** Leur découpe partage les mêmes sommets ; masquer l’eau conserve la géométrie des berges.
- **Le profil et le lit partagent le même terrain de référence.** L'axe, les rives et les creusements voisins sont vérifiés après leur combinaison ; le filtrage ne déplace pas la berge sous l'eau.
- **La précision suit l'échelle du chenal.** On soustrait les coordonnées planétaires avant de les convertir en flottants locaux ; les raccords de berges ne changent pas de branche par saut.
- **Un zoom d’inspection affine l’échantillonnage du même champ global.** Sa fenêtre et sa caméra ne définissent ni un autre bassin ni une fonction de relief locale ; masquer l’eau ne reconstruit pas le terrain.
- **Un essai local garde son contexte planétaire visible.** Son emprise est repérée sur la sphère et le passage au zoom annonce son échelle et sa portée ; une fenêtre d’essai ne démontre pas une fonction disponible sur toute la planète.

**La piste « rivières par bruits » conserve une composition mathématique générique** (`../recherche-rivieres.md`).
- **Des modules déterministes et leurs paramètres :** octaves, déformations du domaine, courbes et opérateurs ; une forme fixée sur la planète.
- **Aucune exception par lieu ni retouche corrective par passes.** Un algorithme externe de drainage ou d’érosion constitue une autre approche et doit être annoncé comme tel.
- **Une fonction pure à courbes prédéfinies ne constitue pas encore un bruit fluvial générique.** La connexion et la descente des cours restent à démontrer par construction.
- **La continuité du bruit ne garantit pas la descente.** Un noyau spécialisé peut imposer une coordonnée amont monotone, un profil d’eau croissant selon cette coordonnée et des jonctions héritées ; la preuve porte alors sur ses cours construits, pas sur toutes les pentes du terrain ni sur une planète entière.
- **Le relief grossier guide la structure commune des bassins, vallées et crêtes avant les détails des versants.** Le module fluvial s’intercale entre les grandes chaînes et les montagnes individuelles ; les détails conservent les profils d’eau et leurs raccords.
- **Une bande de relief remaniée autour de tracés séparés ne construit pas ensemble les crêtes et le drainage.** Les lignes de partage et les ramifications doivent découler de la même structure intermédiaire, avant le détail CP.
- **Affiner le drainage conserve le bassin et ses collecteurs.** Les ramifications plus fines enrichissent les versants à des échelles plus courtes ; leur nombre ne rallonge pas le bassin vers l’amont.
- **La portée des sources appartient au module de bassin.** Sa variation par cellule conserve les jonctions héritées et le profil descendant commun ; relever une source ne consiste pas à poser l’eau sur les bosses d’un relief indépendant.
- **Varier la forme conserve la construction commune.** Une déformation du domaine agit aussi sur les cours, les crêtes et les rives ; elle reste injective et conserve la coordonnée amont utilisée pour la descente.
- **Deux bassins voisins partagent leur relief de séparation.** Un champ commun et des profils compatibles définissent leurs crêtes ; juxtaposer des terrains calculés séparément ne suffit pas à garantir leur raccord.
- **Une généralisation planétaire se juge sur la source CP globale et une graine commune.** Répéter une fenêtre côtière ne démontre pas l’organisation des continents ; des jonctions héritées ne démontrent pas la compatibilité de deux branches qui se croisent ailleurs.
- **La topologie évite les croisements avant le dessin des courbes.** Des connexions à travers des cellules terrestres partagées et des bras dans des secteurs disjoints définissent le domaine admissible ; une simple courbure de tracés libres ne garantit ni ce domaine ni les raccords.
- **Le détail des versants se compose autour des profils fluviaux.** Un ancien microrelief arbitraire ne décide pas de masquer ou d’interrompre les cours ; son remplacement local relève du module partagé, sans correction par passes ni exception par seed.

**Les surcouches ajoutées à `geometrie.md`,** dans son tableau :

| Surcouche | Famille | Échelle | Amplitude | Où | Arrêt | Statut |
|---|---|---|---|---|---|---|
| Maquette Dendry | Remplacement : le relief de l'arbre des rivières, complexplanet n'en donne que les massifs et la rugosité ; lit incisé sous un profil d'eau indépendant, tronçons vectoriels et ruban séparé | vallées de 1 à 10 km, fonds de 150 m à 2 km, chenal creusé selon son débit ; berges Catmull mip 0, détail raccordé sur 100 m | celle de complexplanet, ses cuvettes drainées | une zone de 150 km seulement, calculée hors moteur par `tools/hydro/dendry.py`, bordée de 8 km de raccord | sans `MYPLANETENGINE_DENDRY` | écartée après régression en approche ; historique dans la partie « Les essais remplacés » ; nouvelle proposition dans section 8 |
| Relief construit par les rivières, autonome | Remplacement expérimental | bassin racine de 20 à 28 km, subdivision en trois niveaux ; déformation commune à 12 et 3,7 km | bornes de 1,8 à 3 km, lit de 3 m ; cours et crêtes du même module de cellules ; détail CP limité à 10 % du relief latéral | champ procédural seedé du visualiseur `tools/river-first/`, domaine fixe de 65,536 km ; hors moteur | Référence · 1 octave, ou fermer le visualiseur | bassins-communs-1 non concluant visuellement, mis de côté ; référence conservée, essais dans la partie « Les essais remplacés » ; section 8 |
| Phasor sur le bassin de référence | Remplacement expérimental | région de 20 km ; ravines d’environ 400 m et 133 m | intensité 0,04 de l’échelle de hauteur 3 km ; second niveau ×0,3, amplitude bornée par distance au collecteur et pente | visualiseur `tools/phasor-spike/`, hors moteur | Relief Original | méthode officielle reproduite puis adaptée ; collecteurs en eau et rives partagées, sans drainage des ravines ; section 8 |
| Bruit spécialisé de bassin | Remplacement expérimental | un bassin macroscopique ; deux à quatre niveaux internes avant le détail | profil d’eau croissant vers l’amont ; champ commun de cellules et déformation latérale de 650 m ; relief latéral modulé, nul aux rives | visualiseur `tools/basin-noise/`, hors moteur ; aucune simulation ni carte de drainage | Structure variée désactivée pour la référence précédente ; fermer le visualiseur | essai local de raccordement et de descente par construction ; ne prouve pas l’hydrologie de Complex Planet ; section 9 |
| Noyau de bassin dans MyPlanetEngine | Remplacement régional expérimental | fenêtre de 64 km ; même noyau analytique que le visualiseur ; détail CP sous environ 1 km | eau au profil commun, lit de 4,5 m ; détail CP borné à ±10 % du relief latéral, nul aux rives | mode explicite `MYPLANETENGINE_BASSIN` ; paramètres de cellules exportés, aucune carte de hauteurs ; transition extérieure de 8 km hors zone jugée | Relancer sans le mode ; les variables du lanceur sont restaurées | première confluence inspectée dans le rendu natif ; ni intégration globale ni stabilité en mouvement démontrée ; section 10 |
| Trois bassins côtiers CP | Remplacement régional expérimental | 75 km de côte, bassins de 15 à 23 km ; deux contrôles montagneux CP | profil commun en distance amont à la côte, relief latéral modulé par CP et nul aux rives ; lit de 4,5 m | `tools/coastal-basins/` et mode natif V2, graine commune 0 ; côte et contrôles CP, aucune carte finale de hauteurs du bassin ; fenêtre native de 100 km, raccord extérieur après les sources | Fermer le visualiseur ou relancer le moteur sans données de bassin ; références antérieures conservées | trois réseaux et crêtes communes inspectés sur un tronçon, ensemble natif inspecté ; généralisation planétaire ouverte ; section 11 |
| Bassins globaux sur CP | Remplacement expérimental hors moteur | sphère entière ; cellules terrestres de la grille CP, sites côtiers espacés de 600 km ; relief de structure sur 120 km | forêt cellulaire seedée, courbes contenues dans les cellules, profils hérités descendants ; champ commun guidé par CP | `tools/global-basins/`, graine commune 0 ; construction globale discrète sans routage sur les pentes ; support compact de 450 km, maillage fixe | CP actuel dans le visualiseur ; moteur inchangé par ce prototype | arcs libres remplacés pour éviter croisements et baies du domaine discrétisé ; dépendance à la grille et conservation des massifs restent ouvertes ; section 12 |
| Lit et eau du réseau global | Remplacement expérimental hors moteur | chenal de largeur uniforme 600 m ; trois fenêtres de maillage fixes de 32 km, pas de 125 m | lit nominal jusqu’à 8 m sous le profil global, rives et nappe triangulées ensemble ; mêmes courbes et contrôles CP | `tools/global-basins/water.html`, graine 0 ; fonction de chenal globale, zooms locaux pour l’inspection, aucune fenêtre de remplacement de la fonction | Fermer le zoom ; Eau masque seulement la nappe, le lit reste présent | prototype de confluence et embouchure ; détails CP fins, débit, deltas et niveaux de maillage ouverts ; section 13 |
| Bassins globaux natifs V4 | Remplacement par incision autour du réseau global | CP complet ; chenaux variables et raccord de 3 km depuis les rives | sol strictement inférieur ou égal à CP ; profils bornés aux sondes CP32/256, largeur source puis collecteurs et évasement côtier | mode `MYPLANETENGINE_GLOBAL_BASINS`, graine 0 ; méandres communs aux axes et vallées, hash de 20 km | B pour CP original au même cadrage ; Y pour masquer l’eau | profils et morphologie repris ; delta ramifié et garanties entre sondes restent ouverts ; sections 14–15 |
