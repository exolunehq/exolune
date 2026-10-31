# Journal de la planète

Historique des réglages du terrain : ce qui a changé, pourquoi, ce que ça a coûté ou rapporté, et comment revenir en arrière. L'entrée la plus récente est en haut.

## 2026-10-31 · Parcours cinématique hors temps réel

- **Le mode `MYPLANETENGINE_CINE` :** poses indépendantes du vaisseau et de la caméra, cockpit du jeu, pas fixe, sans audio ni commandes ; les historiques survivent au mouvement, sauf au changement de vue.
- **La sécurité :** lecture GPU du relief courant sous les deux poses ; chaque pince laisse son index dans `cine.log`.
- **La météo du verre suit le vaisseau,** avec des constantes distinctes de la caméra extérieure ; température et pluie ne dépendent plus de son éloignement.
- **Le générateur :** `tools/cine/parcours.py`, NumPy et relief CPU d'Exolune ; splines quintiques C2, bande de terrain et garde vérifiée après lissage.
- **Le rendu :** `tools/cine/rendre.ps1`, plages de 600 images, chauffe de 120 ; H.264 CRF 14, suppression des BMP après vérification, reprise par empreinte.
- **L'essai :** `tools/cine/essai.json`, graine 0, 10 s, descente de 2 000 km vers −7,37 / 116,88, rase-mottes à 150 m, cockpit puis caméra libre ; sortie finale `x64/cine/essai-640-livre/film.mp4`.
- **Vérifié :** compilation VS 2022 Release x64 sans erreur ; 9 contrôles CPU ciblés ; 600 images à 60 Hz, H.264 `yuv420p`, 640×360 ; 12 images inspectées, vaisseau et habitacle présents, seules coupes de vue aux images 360 et 480 ; aucune pince.
- **Les raccords :** rotation de la caméra extérieure limitée à 1,67° entre deux images sur cet essai ; garde minimale de 152 m sur la bande en rase-mottes ; rendu en deux plages de 300 essayé, puis version finale avec la plage de 600 ; reprise et suppression des BMP vérifiées.
- **Reste à juger en vol :** `tools/tests/2026-10-31-cine.txt` ; atterrissage, mer, pluie et givre restent à contrôler visuellement dans le futur parcours de 90 s.
- **État :** travail non commité, sans tag ; aucun banc lancé ; jugement en vol par l'utilisateur encore nécessaire.

## 2026-10-31 · Filtrer la partie émergée des cordons

- **La règle :** un profil qui franchit la mer émerge sur deux mailles au moins, ou reste noyé ; sa largeur totale ne suffit pas.
- **Le filtre :** `ReliefSeaProfile` redistribue le sommet dans un cœur aplati et abaisse son amplitude ; l'aire du profil reste constante, débordements compris.
- **Le périmètre :** les cordons, leurs pointes et leurs débordements ; aucun profil distinct de flèche, platier ou motu volcanique sur cette branche.
- **Les formes résolues restent identiques ;** aucune distance tectonique en double n'est convertie en flottant.
- **Vérification ciblée, sans banc de `tools/` :** 200 000 profils satisfont la largeur émergée ou la submersion ; sur 40 intégrations numériques, erreur relative d'aire au plus 3,5 × 10⁻¹² ; à maille nulle, identité exacte du portage.
- **Le portage contre la carte GPU :** 600 points, médiane 6,48 cm, p99 2,17 m, maximum 13,39 m ; même mesure avant et après.
- **Les rendus :** graine 0, trois côtes à 20, 8 et 3 km, plus 60 m ; référence `−27,18082 / −152,21264`, autres cordons trouvés par `cp.py` à `26,5 / 104,5` et `18,5 / −5,5`.
- **Résultat observé :** aucun pointillé sur les neuf vues d'altitude après filtrage ; à 3 km, écart maximal de 1/255 par canal ; à 60 m, même borne sauf un pixel de feuillage sur la côte est, sans changement visible de silhouette.
- **Les fichiers de contrôle :** `x64/Codex/rendus/avant/`, `apres/`, `comparaisons/` et `differences.txt` ; compilation Release x64 isolée dans `x64/Codex/`.
- **À juger en vol :** `tools/tests/2026-10-31-cordons-emergence.txt` ; changements non commités, sans nouveau tag.

## Comment s'en servir

- **Avant toute correction, lire `principes.md` :** on corrige des règles, pas des cas. Ce fichier fait référence.
- **Tous les réglages sont dans `MyPlanetEngine/PlanetSettings.hlsli`.** Changer une valeur et recompiler, 2 secondes, suffit à retrouver une configuration du journal.
- **Pour un retour complet**, chaque entrée donne son commit ou son tag.
- **Mesures :** temps de calcul GPU du terrain, au-dessus de 15° S, 50° E. Le pire cas est la pire des dix vues de référence décrites dans `log/spec-champ-de-vision.md`.
- **Écart visuel :** comparaison pixel à pixel de captures avant et après, sur six vues : deux au-dessus du continent de départ, une vue d'orbite, un autre continent et deux vues de côte. Les images du journal montrent dans l'ordre : avant, après, différence amplifiée 8 fois.

## Jalons et pistes

**Chaque étape validée et chaque piste essayée a un tag git.** `git checkout <tag>` retrouve l'état exact.

| Tag | Contenu |
|---|---|
| `piste/orbite-rendu` | La planète vue d'orbite face à Apollo 17 : diffusion multiple des aérosols par similitude, lumière des nuages calée sur Monte-Carlo, eau indépendante de la couverture, statistique du pixel à la place de la quadrature lointaine, exposition d'orbite (`spec-rendu-orbite.md`). |

| `piste/meteo-epaisseur` | L'épaisseur des masses structurée pour l'eau du nuage du rendu : nappes minces en cellules, têtes et fronts épais, bords effilochés ; la table R remesurée (`spec-nuages.md`). |
| `piste/meteo-bimodale` | Des ciels clairs : le ciel clair par défaut, le moucheté de petits nuages dans quatre régimes, la couverture portée par les masses, calée sur la photo d'Apollo 17 (`spec-nuages.md`). |
| `piste/meteo-orbite` | La carte météo vue d'orbite : dépressions en virgule, fronts froids, ZCIT en amas, nappes, en masses opaques ; les petits nuages au grain du shader ; la couverture de la Terre par latitude (`spec-nuages.md`). |
| `piste/nuages-climat` | La carte météo des nuages calculée au démarrage sur le climat et le relief : ZCIT, anticyclones, nappes des côtes froides, dépressions en virgule, bancs au vent (`spec-nuages.md`). |
| `piste/climat` | Le climat calculé au démarrage sur la forme tectonique : vents, vapeur portée depuis les mers, pluie au vent des reliefs, continentalité, courants froids ; la carte lue par les matériaux, les plantes, la mer et le vaisseau (`spec-climat.md`). |
| `piste/volcanisme` | Les volcans déduits de la carte tectonique : arcs, points chauds et leurs chaînes, atolls et guyots, rifts, calderas, coulées, cônes, traps ; basaltes et cendres ; branche `claude/volcanisme-7c3aea`, partie de `bruit-propre`, à juger en vol (`spec-volcanisme.md`). |
| `jalon/29-avant-ouverture` | `main` juste avant le rangement pour l'ouverture, commit `48f2e42` : les essais de nuages, de végétation et de terrain encore dans le code, le lanceur `tools/nuages-planete.ps1`. |
| `jalon/28-vaisseau-habitacle` | Le vaisseau, son vol et son habitacle : vue sans vaisseau et caméra libre, gaz à la molette, tête qui suit les accélérations ; panache des tuyères, ombres du relief sur le vaisseau et du vaisseau au sol, verrière qui sèche, écrans animés, commandes mobiles ; son synthétisé sur XAudio2. |
| `piste/vegetation-relais-fondu` | Relais imposteur-maillage des modèles `game` : fondu tramé, animé à chaque image, entre 0,8 et 1,25 fois le seuil de chaque plante, touche H pour le couper ; imposteurs éclairés sur la dispersion de leurs feuilles et recuits en linéaire ; validé en vol. |
| `jalon/27-vaisseau` | Le vaisseau dans le jeu : paquet cuit, vues du cockpit et de poursuite, pilotage clavier-souris, ombres propres ; verrière avec givre et eau simulée ; météo lue dans les nuages planétaires (`spec-vaisseau.md`). |
| `piste/optimisation-r8-sol-vol-rapide` | Round 8 de l'optimisation : trouées de ciel dans les feuilles remplies par l'historique, grille du terrain en paires de floats en vol ; en vol rapide, forêt de 49 à 60 fps, lisière de 43 à 55, montagne de 48 à 54 ; image immobile identique, validé en vol. |
| `piste/optimisation-r7-nuages-rapides` | Round 7 de l'optimisation : sous 14 km, les nuages dont l'historique a glissé sont tracés un pixel par carré 2×2, les autres interpolés ; cumulus en vol rapide de 36 à 90 fps, plongée près du sol de 34 à 52 ; image immobile identique, validé en vol. |
| `piste/optimisation-r6-nuages-mouvement` | Round 6 de l'optimisation : chaque trace fraîche des nuages vérifie l'historique ; traînées, bruit et ghosting corrigés au banc, 4 à 6 ms de plus en vol lent en altitude et près des cumulus ; mis de côté, la branche `optimisation` reste sur la version rapide. |
| `jalon/optimisation-r1-r5` | Phase d'optimisation, rounds 1 à 5, sur la branche `optimisation` : la version rapide, avec ses effets de bord des nuages en mouvement. |
| `piste/optimisation-r5-mesure` | Round 5 de l'optimisation, arrêté à la mesure : le GPU n'attend le CPU que 0,6 à 1,2 ms par image ; cadence réelle au banc ; lanceur en plein écran 1920x1080. |
| `piste/optimisation-r4-terrain` | Round 4 de l'optimisation : calcul du terrain gardé tant que ses entrées sont celles de l'image précédente ; au sol, 73 à 77 fps immobile, rien en vol ; image identique, validé en vol. |
| `piste/optimisation-r3-vegetation` | Round 3 de l'optimisation : sol exact des plantes gardé d'une image à l'autre, imposteurs en profondeur conservatrice, maillages proches en profondeur d'abord ; forêt de 30 à 17 ms, image identique, validé en vol. |
| `piste/optimisation-r1-nuages-mouvement` | Round 1, suite : passe temporelle des nuages juste en mouvement ; historique douteux retracé, air de la composition continu dans la distance du nuage ; plaques et seconde peau disparues en vol. |
| `piste/optimisation-r2-terrain` | Round 2 de l'optimisation : terrain en profondeur d'abord, couleur sur la seule surface visible ; calculs sautés là où ils sont prouvés sans effet ; validé en vol. |
| `piste/optimisation-r1-nuages` | Round 1 de l'optimisation : nuages tracés un pixel sur 16 par image et reprojetés dans le monde ; image immobile identique, jugement en vol à faire. |
| `jalon/26-nuages-main` | Nuages planétaires, météo et ombres portées intégrés à main avec mer FFT et végétation ; éclairage précédent conservé. |
| `piste/nuages-main-integration` | `main` au commit `f66ead9` fusionné dans les nuages, éclairage précédent conservé ; base du jalon 26. |
| `piste/nuages-planete-spike` | Ombres des nuages sur la terre et la mer, météo sur la sphère entière ; les nuages du jeu (`spec-nuages.md`). |
| `jalon/25-vegetation-performance-main` | Optimisation des bases angulaires, HiZ conservateur et profondeur matérielle des maillages ; populations et portée conservées. |
| `jalon/24-vegetation-detaillee-main` | Version acceptée en l'état : modèles de jeu, maillages proches, imposteurs lointains et douze arbustes climatiques ; écarts de banc consignés. |
| `piste/vegetation-optimisation-base` | Départ de la phase différée d'optimisation GPU et mémoire, à rendu, population et portée conservés. |
| `piste/vegetation-hiz-base` | Base de la pyramide de profondeur courante et du masque conservateur ; travail de performance non commité. |
| `piste/arbustes-climatiques-base` | Base du catalogue de six familles et douze formes, instances conservées et sous-plages GPU partagées ; travail intégré au jalon 24. |
| `piste/vegetation-bouquets-lumiere-base` | Base des bouquets foliaires, normales locales et visibilités précalculées ; tag sur le commit de départ, travail intégré au jalon 24. |
| `piste/vegetation-silhouettes-arbustes-base` | Base du relais sans tramage, des mipmaps et du remplacement des arbustes ; mêmes instances et portée, travail intégré au jalon 24. |
| `piste/vegetation-modeles-jeu-base` | Base du remplacement des bouquets pleins par des modèles d'artistes à feuillage découpé et matériaux détaillés ; mêmes instances et portée, travail intégré au jalon 24. |
| `piste/vegetation-stylisee-base` | Base du remplacement des arbres photo par des modèles originaux semi-réalistes stylisés ; mêmes instances et portée, travail intégré au jalon 24. |
| `piste/vegetation-imposteurs-filtrage-base` | Base de l'optimisation des rectangles et du filtrage matériel des imposteurs ; densité et portée conservées, travail intégré au jalon 24. |
| `piste/vegetation-compaction-stable-base` | Base de la correction des sélections GPU saturées ; compaction déterministe des tuiles et des plantes, travail intégré au jalon 24. |
| `piste/vegetation-imposteurs-hybrides-base` | Base de la variante maillage proche et imposteurs lointains ; mêmes forêts et mêmes seuils que l'hybride volumique, travail intégré au jalon 24. |
| `piste/vegetation-planetaire-base` | Base de l'essai de remplacement des arbres planétaires par les modèles détaillés et volumes ; premier jugement directement en vol, travail intégré au jalon 24. |
| `piste/vegetation-foliage-base` | Base du prototype de végétation détaillée ; travail intégré au jalon 24. |
| `piste/nuages-orbite-spike` | Essais voxel et Frostbite conservés, trois familles locales, répartition régionale et première quadrature orbitale ; cirrus plus rares. |
| `jalon/01-jet1` | Une face du cube tournée vers la caméra, complexplanet porté en HLSL. |
| `jalon/02-anneaux` | Champ de vision couvert par les anneaux, filtrage des octaves par sommet. |
| `jalon/03-performance` | Pire cas du calcul de 15,1 à 1,6 ms. |
| `piste/aimantation-crans` | Abandonnée : maillage aimanté par crans, niveaux de détail à paliers. |
| `jalon/04-normales-voisins` | Normales sur les sommets voisins, grain fin par pixel, banc de tremblement. |
| `jalon/05-atmosphere` | Haute dynamique, atmosphère, ciel et soleil. |
| `jalon/06-materiaux` | Matériaux par pixel, climat simple. |
| `piste/relief-par-pixel` | Abandonnée : vrai relief des montagnes par pixel. |
| `jalon/07-lissage-192` | Lissage temporel, 192 mailles par côté. |
| `jalon/08-aretes-arrondies` | Arêtes arrondies à l'échelle de la maille. |
| `piste/sommets-fixes-etape1` | Sommets fixés sur la planète, étape 1 : cube et carreaux, sans fondu. |
| `piste/sommets-fixes-etape3` | Close : sommets fixes avec fondu imbriqué et rangées de bord, sans fente ni couture, mais saccadé en vol. |
| `jalon/09-normales-spline` | Normales par pixel en B-spline lissante, coupure du relief réglable. |
| `jalon/10-herbe` | Textures de près, le cadre et l'herbe. |
| `jalon/11-sable-roche` | Voie B : matériaux générés au démarrage, rides du sable au pixel à phase exacte, roche et éboulis, ombres fines, banc visuel. |
| `jalon/12-roche-relief-lointain` | Relief réel des matériaux dans le maillage, détail fin au millimètre, couleurs de roche par région, roche en bancs, diaclases et corniches sur 64 m, mesure de réalisme ; de loin, roche et neige en fractions de la maille. |
| `jalon/13-coherence-distance` | La planète garde la même apparence de l'orbite au sol : grille fine du vrai relief sous la maille, relief qui garde sa hauteur moyenne, règle universelle des limites entre matériaux, banc de descente et vues de diagnostic. |
| `piste/couleurs-manuelles` | Les couleurs du sol choisies à la main, avant la palette de Blue Marble ; avec les principes et le correctif des strates au feutre. |
| `piste/essai-hybride-scans` | Essai des scans photo pour le sable et la roche litée, mesurés contre le procédural ; repris pour le sable par la photo (`log/spec-hybride-scans.md`). |
| `piste/palette-blue-marble` | Les couleurs du sol tirées de la vraie Terre : la palette de biomes mesurée sur Blue Marble. |
| `piste/parois-gradins` | Parois en gradins : falaises des bancs durs, replats à l'angle d'éboulis, ravines et granite dans le maillage. Bien de près ; de 100 m à 1 km, encore rectiligne, « tissu ». |
| `piste/bandes-cassees` | Strates cassées par des failles, teintes par groupes de formations. |
| `piste/bandes-immobiles` | Bandes immobiles à l'approche, granite sans grillage, failles coupées, doc rangée. |
| `piste/sol-nu` | Le sol nu, un matériau oublié, prend sa texture ; les bancs le mesurent. |
| `jalon/14-banc-qualite` | Le banc de qualité : lieux tirés par matériau, flou, trous d'échelle, répétition, bandes droites, mutation ; référence chiffrée. |
| `jalon/15-roche-photo` | Une seule roche, sa photo ; strates en couleur, perturbées, d'épaisseur variable ; papier peint en partie réglé. |
| `jalon/16-une-roche` | Le code d'une seule roche : familles, tuiles dessinées, failles, marches de la colonne et parallaxe retirées. |
| `piste/roche-regionale` | Mise de côté, avant « une seule roche » : la roche régionale par pixel selon la province, une croûte de roche mouillée, la forêt sur les pentes (`log/roche-regionale.md`). |
| `jalon/17-brume` | La brume de la couche limite : visibilité de 40 km, aérosols colorés, pas du rayon à la moyenne de l'air. |
| `piste/integration` | Une palette de tests pour chaque fonction ; ses fusions sont dans `main`. |
| `jalon/18-lumiere` | La lumière : halo de l'objectif, exposition et courbe de tons, ombres portées du relief, rayons de soleil dans la brume ; parts des matériaux stables à l'approche. |
| `jalon/19-detail-sol` | Le détail du sol près de la caméra : cailloux, touffes d'herbe et rochers selon le sol, à place fixe sur la planète, sans pop ni flottement. |
| `jalon/20-ombre-carte` | Une seule ombre du relief, pour le sol et les rayons de soleil ; cailloux v5, présents par zones ; la brume suit le sol régional de la carte de la planète, carte hydrologique calculée au démarrage. |
| `jalon/21-vegetation` | La végétation v3 : arbres et arbustes selon le climat, régions sans arbres, clairières, crêtes nues ; les arbres entiers ou absents, la canopée lointaine à leur hauteur. |
| `piste/mutation-approche` | Correctif : la tache verte garde sa forme à l'approche ; grille fine jusqu'à 160 m du sol, neige sans la pente des textures, banc de descente des parts vues. Avec le nettoyage « une seule roche ». |
| `piste/bandes-declarees` | La pile de bandes déclarée par matériau et son validateur mesuré. |
| `piste/bandes-detail` | Les bandes de détail : neige, sable, herbe, éboulis. |
| `piste/photo-falaise` | Géométrie à complexplanet, géométrie de proximité désactivée, photo de paroi `marble_cliff_04` sur la roche litée. |
| `piste/erosion-filtre` | Mise de côté : filtre d'érosion dans le relief, une surcouche de remplacement de complexplanet (`geometrie.md`). |
| `piste/papier-peint` | Essai roche-photo v12 ; deux photos du marbre selon l'orientation, bandes de la roche à la pente de sa photo, étalement mesuré au banc. |
| `piste/cercles-orbite` | Correctif : plus de cercles sur les océans vus de loin ; la distance passée à l'atmosphère en flottants 32 bits. |
| `piste/patchs-pixels` | Un bruit de gradient pour tous les champs : plus de mosaïque de loin ; la géographie est retirée. |
| `piste/halo-optique` | Le halo de l'objectif autour du soleil, en 1/θ², qui conserve l'énergie, avant la courbe de tons. |
| `piste/tons-exposition` | L'exposition réglée sur la lumière du jour sous la caméra, posemètre tourné vers le soleil ; la courbe de tons des photorécepteurs sur le canal le plus fort. |
| `piste/ombres-relief` | Les ombres portées du relief : horizon vers le soleil à chaque sommet, interpolé comme un angle, part du soleil au pixel. |
| `piste/rayons-soleil` | Rayons de soleil : l'air à l'ombre du relief, par la hauteur d'ombre lue à chaque pas du rayon de vue. |
| `piste/etoiles` | Le ciel nocturne : étoiles et planètes en images de points, seuil de l'œil de Schaefer, Voie lactée, lueur atmosphérique, nuit au posemètre et clé de l'œil, bâtonnets. Branche `etoiles`, gardée pour être intégrée (`recherche-ciel-nocturne.md`). |
| `piste/plages` | Les plages : la plage de 0 à 2,5 m, la ligne d'eau nette, le sable mouillé et sa brillance, la laisse de mer, les ceintures des roches. Branche `plages`, faite sur l'ancienne mer, à porter sur la mer FFT (`recherche-cotes.md`). |
| `piste/objets-proximite` | Objets de proximité, étape 3 : le détail du sol, cailloux et touffes d'herbe, des débris seulement dans les régions caillouteuses, à place fixe sur la grille de la planète, sans pop. |
| `piste/ombre-unique` | Une seule ombre du relief : la marche de l'horizon de chaque sommet donne aussi la hauteur d'ombre de l'air ; la grille polaire et ses deux passes retirées. |
| `piste/carte-planete` | La carte de la planète : complexplanet sur un cube fixe, calculé et drainé au démarrage ; la brume suit le sol régional ; lacs et réseau mesurés. |
| `piste/vegetation` | La végétation, étape 1 : arbres et arbustes selon le climat, trois espèces générées au démarrage, objets proches et canopée dans la matière du sol au-delà, raccordés en couche booléenne. |
| `piste/vegetation-v2` | La végétation v2 : régions sans arbres et clairières par deux champs de bruit, arbustes par taches et en lisière, crêtes nues, huit variantes, sortie à 14 pixels avec une forme grossière. |
| `piste/vegetation-v3` | La végétation v3 : les arbres entiers ou absents, jamais grandissants ; la canopée lointaine à la hauteur de ses arbres ; un cinquième d'arbustes en moins ; pas de forêt sous 1 000 mm. |
| `piste/rivieres-lits` | Mise de côté : lacs au niveau du bilan d'eau, rivières larges de leur débit, lits creusés. Jugé très mauvais : lacs sur 35 % des terres, eau plate, tranchées sèches. À reprendre en prototype rapide, à deux. |
| `piste/dendry-maquette` | La maquette Dendry : le relief de l'arbre des rivières sur une zone de 150 km, lu par le moteur ; contenue dans la branche `erosion-niveaux`. |
| `jalon/avant-spikes-rivieres` | La maquette Dendry avant les spikes rivières du 26 octobre, commit `b0252c9` ; un `jalon/` posé sur une étape de piste. |
| `piste/rivieres-spikes` | Mise de côté : les spikes rivières des 26 et 27 octobre, bassins construits avec leurs rivières, réseau global sur complexplanet, profils bornés, méandres et largeurs variables ; repris par `erosion-niveaux` (`log/recherche-rivieres-historique.md`). |
| `jalon/rivieres-cp-resultat-prometteur` | Le commit de `piste/rivieres-spikes`, `31a1271` : le résultat jugé prometteur le 27 octobre ; un `jalon/` posé sur une étape de piste. |
| `piste/mer-animee` | La mer : vent sur le climat, reflet du soleil et du ciel par Cox-Munk, vagues animées dans les pixels à variance constante, moutons de Monahan qui naissent et s'effacent, couleur de l'eau et fond vu. Branche `mer-animee`. |
| `piste/essai-fusion-mer-plages` | Essai de fusion de `piste/plages` dans la mer animée : un seul reflet de l'eau ; mis de côté avec l'ancienne mer. |
| `piste/mer-fft-spike` | Base du prototype FFT indépendant, avant le travail validé au jalon suivant. |
| `jalon/22-mer-fft` | Océan FFT en quatre cascades, géométrie et normales communes, écume persistante ; aspect validé en vol. |
| `jalon/23-mer-fft-main` | Mer FFT rebasée et intégrée à main, avec sa végétation, sa carte et son ombre unique. |
| `piste/nuages` | Les nuages en volume, de l'orbite au sol : la carte du temps sur le climat, un volume lancé au quart des pixels, volutes 3D, cumulonimbus, ombres et brouillard. |

## Réglages actuels

| Réglage | Valeur | Effet |
|---|---|---|
| Relief (`Relief.hlsli`) | relief tectonique, `PLANET_SEED` 0 | Les grandes formes de la carte tectonique, gauchies de 30 km ; les côtes de 60 à 3 km, déplacées de 12 km sur les côtes raides, 8 sur les plates, cordons et lagunes ; le détail en 12 octaves de 50 km à 13,5 m, lacunarité 2,11, la plus large des chaînes en plis à 36 km, les trois plus larges étirées le long d'elles ; les réglages `RELIEF_*` de `PlanetSettings.hlsli` (`spec-relief-tectonique.md`). |
| Carte tectonique | 6 × 512², trois tranches RGBA16F, une quatrième au quart pour les vues, au démarrage | Continents par lieu, 40 à 44 % de croûte ; 12 à 20 plaques ; frontières, familles de profils, âges, sutures ; rifts ouverts en mers étroites ; soulèvement et érodabilité pour le niveau 0 ; 0,85 s et 38 Mo ; écrite à côté de l'exécutable pour le portage CPU, cinq tranches (`Tectonics.cpp`). |
| Volcans (`Volcanoes.hlsli`) | 1 113 volcans, 15 points chauds, graine 0, au démarrage | Arcs à 140 à 230 km de la fosse, chaînes de points chauds, rifts ; profils concaves ou en bouclier, contours lobés de 20 %, cratères, calderas, coulées de 40 et 15 m, cônes tous les 2,5 km, guyots et atolls ; houle des panaches, traps et plateaux océaniques dans la carte ; les réglages `VOLCANO_*` (`spec-volcanisme.md`). |
| `EXACT_LATTICE_MAX_CELL` | 4 m | Double précision seulement pour les mailles de moins de 4 m. |
| `CREASE_ROUNDING` | 2 | Arêtes de Billow et RidgedMulti arrondies sur environ deux mailles. L'arrondi perd son excès moyen : le relief garde sa hauteur moyenne à toute distance. |
| `CREASE_MIN_CELL` | 2 m | Les crêtes ne s'affinent plus sous des mailles de 2 m, si proche que soit la caméra. |
| Projection des textures | triplanaire, `max(|n| − 0,45, 0)²` | Un, deux ou trois plans selon la normale, continus partout ; remplace la biplanaire à la puissance 8. |
| `MESH_BAND_LIMIT` | 2 | Longueur d'onde la plus courte du relief, en mailles. 3 ou 4 scintillent moins, mais la forme mute davantage à l'approche. |
| `DETAIL_SLOPE` | 0,08 | Grain fin de l'éclairage dessiné dans les pixels : pente ajoutée par octave. 0 le désactive. |
| `TEXTURE_DETAIL` | 1 | Textures de près des matériaux : herbe et roche calculées au pixel, sable généré au démarrage. 0 les désactive. |
| `STRATA_FORMATION_CONTRAST` | 0,3 | Teintes par groupes de formations, palette des grès aux trois quarts. Couleur seulement. |
| `STRATA_SLOPE` | 0,4 | Perturbation des strates de 8 km à 4 m, pente moindre de 15 % à chaque octave ; l'épaisseur des couches varie le long des parois. |
| `SNOW_BANDS`, `SAND_BANDS`, `GRASS_BANDS`, `SCREE_BANDS` | voir `PlanetSettings.hlsli` | Bandes de détail de chaque matériau, `DetailBands` : longueurs d'onde, pente et couleur par octave. |
| `SOIL_BANDS` | 50 cm à 64 m ; 0,05 ; 0,05 | Sol nu : photo du gravier sableux et bandes de détail. |
| `ROCK_TILE` | 64/5 m | Tuile de la roche : la photo de paroi `marble_cliff_04`, 12,7 m, sur les pentes de plus de 45°. |
| `ROCK_TOP_TILE` | 64/3 m | Le même marbre pris de dessus, `marble_cliff_05`, 20 m, sur la roche plus douce ; tranche `MATERIAL_ROCK_TOP`. |
| `ROCK_BANDS` | 8 à 64 m ; 0,24 ; 0,06 | Bandes de la roche, au-dessus de ses photos : la pente par octave de sa photo, `STONE_SLOPE_SIGMA`. |
| `BLEND_RISE` | 0,3 m | Hauteur de texture qui déplace d'un poids entier une bordure entre matériaux ; le mélange par la hauteur s'estompe pour les pixels de 25 cm à 2 m. |
| Grille fine | 4 × la face, dès des mailles de 20 m | Normales et altitude du vrai relief sous la maille, recalculées à chaque image (`FineSubdivision`, `FineMinCell`). |
| `OCTAVE_SLOPE` | 0,16 | Pente portée par chaque octave cachée des montagnes. Rugosité du relief : chaînes jeunes 1, mesas et badlands 0,6, vieilles chaînes 0,5, collines 0,35, plaines 0,1. |
| `TEXTURE_FINE` | 1 | Tuile fine de 1 m par matériau, 1 mm par texel, posée sur la grossière tant qu'un pixel couvre moins de 1 à 2 cm. 0 la retire. |
| `SPLINE_NORMALS` | 1 | Normale par pixel, B-spline sur les 4 × 4 sommets voisins. 0 revient à la normale des sommets. |
| `SPLINE_SURFACE` | 1 | Matériaux et grain fin pris sur la surface spline, à la rencontre du rayon de vue. |
| `DETAIL_MIN_WAVELENGTH` | 13,5 m | Pas de grain plus fin que l'octave la plus fine du relief. |
| `DETAIL_MAX_WAVELENGTH` | 6 km | Pas de grain plus large que les octaves fines du relief. |
| Matériaux | la carte du climat, `GroundMaterials` dans `Materials.hlsli` | Température : celle de la carte au niveau de la mer, −5 °C/km, bruit de la limite des neiges de 2 km au plus, ±0,6 °C. Neige sous −2 °C. Roche au-delà d'une pente de 0,65 à 1,0, éboulis de 0,43 à 0,75. Humidité : le log des précipitations de la carte, de 100 à 3 000 mm, plus `CLIMATE_LOCAL`, 0,08, de 100 à 6 km. Chaque limite montre sa moyenne sur le pixel (`SpreadStep`, `SlopeShares`) ; les versants cachés comptent 4 °C par unité de pente. |
| Carte du climat | 6 × 256², deux cubes RGBA16F, 9 mips, au démarrage, après la carte tectonique (`Climate.hlsli`) | Précipitations, température au niveau de la mer, demi-amplitude des saisons, part de la pluie en été ; vent, continentalité, courants froids. Transport de la vapeur à l'équilibre sur 200 puis 100 km ; 0,23 s et 8 Mo ; écrite à côté de l'exécutable pour le portage (`Climate.cpp`, `spec-climat.md`). |
| `LEDGE_SCREE`, `LEDGE_SOIL` | 0,72 à 0,82 ; 0,84 à 0,92 | Planéité de la roche texturée au-delà de laquelle éboulis puis sol couvrent les replats. |
| `STONE_SLOPE_SIGMA` | 0,6 | Écart de la pente de la texture de roche, que les mips perdent de loin : la part des replats en tient compte. |
| `EXPOSURE_COMPENSATION` | 1 IL | L'exposition suit la lumière du jour sous la caméra, un posemètre incident tourné vers le soleil : une carte grise face au soleil y montre sa réflectance, plus cette compensation. Après le coucher, la lumière du coucher. |
| `FILM_CONTRAST` | 1,5 | Courbe de tons x^a / (x^a + k^a) sur le canal le plus fort, par la carte grise : pente 1,5 dans les ombres, 1,23 au gris, épaule vers le blanc. |
| `HORIZON_STEP` | 0,02 | Ombres portées et rayons : pas de la marche vers le soleil, en part de la distance parcourue, jamais sous la maille. 0,05 donne les mêmes ombres au sol, mais les rayons tremblent davantage. |
| Atmosphère | la Terre, d'après Hillaire 2020 | Rayleigh, ozone, 100 km d'épaisseur ; aérosols de la couche limite, visibilité de 40 km au niveau de la mer, jusqu'à 2 km au-dessus du sol régional ; albédo du sol 0,3, soleil d'éclairement π. |
| `HAZE_GROUND_SCALE_KM` | 10 km | La couche de brume se pose sur le sol de la carte de la planète, lissé sur cet écart type : elle suit les plateaux, se nivelle sur les crêtes et les vallées. |
| Carte de la planète | 6 × 1 024², au démarrage, après la carte tectonique (`PlanetMap.hlsli`) | Le relief sur un cube fixé sur la planète : le sol, l'eau des cuvettes remplies, l'aire drainée. De la donnée, aucun sommet ne bouge. |
| `GLARE_STRAYLIGHT` | 0,3 deg²/sr | Halo de l'objectif : une source d'éclairement E voile l'image à θ degrés d'elle de 0,3 E / θ². Un objectif récent. 0 le retire. Coupé par défaut ; `MYPLANETENGINE_GLARE` l'active. |
| `OBJECT_STONY` | 0,27 à 0,42 ; 0,22 | Objets de proximité : où il y a des débris, un champ de 0,5 à 32 km relevé par les éboulis, le sol nu sec et la pente. Aucun débris sur 74 % des prairies, 70 % des sables et sols nus, 11 % des éboulis. |
| `PEBBLES`, `GRASS_ROCKS`, `TUFT_COVER` | 2 % à 3 cm, effacé au-delà de 8 cm ; 0,03 ; 20 % et 1 % par octave | La recette par sol : cailloux du sable et du sol nu ; rochers de l'herbe, loi de Golombek et Rapp ; touffes dans l'herbe, sèches sur le sable et le sol nu. |
| `DEBRIS_ABUNDANCE` | 0,05 ; 0,25 | Pierres des éboulis ; éboulements au pied des vraies parois. Une loi de Golombek et Rapp chacune. |
| `OBJECT_OCTAVES`, `TUFT_OCTAVES` | 3 cm à 2 m ; 12 à 50 cm | Les octaves de tailles des cailloux et des touffes ; le gravier plus fin est la texture du sol. |
| `OBJECT_LANDFORM`, `OBJECT_CREST`, `OBJECT_GATHER`, `OBJECT_PATCHES`, `OBJECT_CLUMPS` | 16 m ; 0,004 à 0,02 /m, 10 % ; 10 à 20° ; nulles sur 58 % du sol ; 0,4 à 1,6 fois | La forme du sol lue sur 16 m ; les crêtes ; le pied des parois ; les taches des rochers ; les amas des cailloux et des touffes. |
| `OBJECT_REPOSE`, `OBJECT_BURIAL` | 38°, −1° par octave, 3° ; 8 à 40 %, 3 mm au moins | Angle de repos par taille ; enfouissement de la roche au sol meuble. |
| `OBJECT_PIXELS`, `OBJECT_CELLS` | 6 à 9 px ; 1 à 1,5 fois la largeur | Un objet sort du sol de 6 à 9 pixels de large, et seulement où les mailles font moins de 1,5 fois sa largeur. |
| `TREE_SEASON_START`, `TREE_LINE` | 0,9 °C ; 5,7 à 7,1 °C | Végétation : les saisons de la carte du climat, sur terre 3,5 + 18 sin² de la latitude à la continentalité moyenne, ajusté sur TerraClimate ; la ligne des arbres par la saison de croissance, Körner et Paulsen. |
| `TREE_CEILING`, `TREELESS_RAIN`, `FOREST_RAIN`, `TREE_COVER_MODES`, `STAND_COVER` | 1,98 × aridité − 0,142 ; 820 ± 190 mm, plancher 2 % ; 2 100 ± 380 mm, rien sous 1 000 mm ; 20 et 80 % ; 90 % | L'eau : plafond de Sankaran ; les trois états de Hirota, sans arbres, savane, forêt ; peuplements. |
| `PRESENCE_SCALES` | 32 km et 1 km, jusqu'à 8 m | Où sont les bois : le champ des régions, puis celui des taches, les clairières. |
| `EXPOSURE_RELIEF`, `EXPOSED_SEASON`, `EXPOSED_DRIVE` | 300 m ; 0,5 °C ; 2 écarts | Les crêtes et les creux : la hauteur sur le sol régional, la saison et les champs des bois. |
| `SHRUB_LAND`, `SHRUB_COVER`, `SHRUB_ARIDITY`, `SHRUB_HEIGHT` | 50 % des terres ; 20, 60, 35 et 25 % ; 0,03 à 0,12, 0,3 à 1 ; 1,5 m | Les arbustes par taches : désert, terres sèches, clairières humides, sous-bois. |
| `FOREST_EDGE`, `SHRUB_LINE_OFFSET` | 32 m, 2 écarts ; 1,5 °C | Le manteau d'arbustes des lisières ; le krummholz au-dessus de la ligne des arbres. |
| `CANOPY_HEIGHT`, `PLANT_HEIGHT_SPREAD` | 40 m ; 0,6 octave | La hauteur de la canopée par la saison et l'eau ; l'étalement des hauteurs. |
| `CANOPY_ALBEDO`, `PLANT_TINT`, `SHRUB_ALBEDO`, `CANOPY_RELIEF` | Amazonie ; 0,7 ; gris olive ; 0,6 et 0,2, les arbres seuls | Couleur de la canopée, des conifères, des arbustes ; relief des couronnes au sol. |
| `PLANT_OCTAVES`, `PLANT_LOD_PIXELS` | 0,5 à 64 m ; 64 à 48 px | Les plantes sur la grille, une octave de hauteurs par niveau ; chacune entière dès qu'elle est dessinée, de 8 à 5 pixels de haut (`PlantPixelRange`, `Vegetation.hlsli`) ; sous 48 pixels, le pied sur le sol du maillage, de 48 à 64 vers le sol exact. |
| Végétation planétaire | sortie 5 à 8 px ; 512 tuiles ; relais imposteur-maillage de 96 à 128 px selon la graine, fondu de 0,8 à 1,25 fois ce seuil ; auto-ombrage 0,65 | Le seul feuillage, actif par défaut, ses réglages en dur (`PlanetFoliage.cpp`, `PlanetFoliageLod.hlsli`) : maillages proches, imposteurs lointains, quatorze modèles ; canopée et placement partagent le seuil. |
| `CANOPY_SIDE_LIGHT` | 0,2 ; 3 | La lumière de la canopée vue à l'élévation e, 1 − 0,2 (1 − sin e)³, mesurée sur les plantes dessinées. |
| Ombre du relief dans l'air | hauteur d'ombre par sommet (`Shadows.hlsli`) | Donnée par la marche de l'horizon de chaque sommet, lue entre les sommets ; la lumière du soleil diffusée une fois est coupée sous elle. |
| La mer | Quatre FFT 256² ; écume persistante dans deux cartes 512² ; `FOAM_ALBEDO` 0,22 au loin | Déplacement et normales communs ; la couleur de l'eau par la température de la carte du climat ; vent uniforme par vue, la carte du climat porte le vent, raccord à faire ; temps à 1/60 s par image en capture. |
| Nuages | `Clouds.hlsli`, `CloudsTemporal.hlsli`, `assets/clouds`, `Climate::Weather` | Les nuages du jeu, actifs par défaut (`spec-nuages.md`) : couche basse de 2 à 8 km, cirrus de 9 à 13 km ; carte météo planétaire 1 024 × 512, calculée au démarrage sur le climat, forme sur 32 km, érosion sur 4 km ; extinction 80 /km, quatre pas vers le soleil, double Henyey-Greenstein ; vent de 12 m/s vers l'est ; passe temporelle, une trace par tuile 4 × 4. L'air de leur composition garde rayons et brume régionale. Vues `clouds`, `weather`, `cloudshadow`. |

Hors de ce fichier : `PLANT_CROWN` dans `Objects.hlsli`, 0,3, 0,45 et 1,1, les couronnes de Tallo ; `PlanetPlantWindow`, 512 tuiles de 4 × 4 cellules. Maillage de 192 × 192 + anneaux de croissance 1 + 2/192, réglés par le seul `FaceCells`, k = 2, rayon de 6 378 km, dans `D3DApp.h` et `D3DApp.cpp`. Le maillage glisse en continu avec la caméra. L'éclairage utilise la normale calculée sur les sommets voisins, dans le vertex shader, plus le grain fin dans les pixels ; la touche R revient à l'éclairage à facettes. Le soleil et le ciel éclairent le terrain à travers l'atmosphère, en lumière linéaire, dans une image en haute dynamique, en flottants 32 bits : son alpha porte la distance du terrain à l'atmosphère.

---

## 2026-10-31 · L'orbite basse : des nappes texturées, des cumulus organisés

- **Le défaut :** à 750 km, des nappes blanches uniformes aux bords nets ; un semis régulier de petits cumulus entre elles.
- **Les causes, par élimination :** l'eau d'un cœur de front dans toutes les nappes, τ ≈ 60, réflectance saturée ; une octave manquante entre 10 et 150 km, l'érosion de 4 km plaçant seule les cumulus. Ni la carte au mip 0 ni la variance fine.
- **La correction :** l'eau dans le nuage suit l'épaisseur de la carte, `0,25 + 0,75 e`, e = (R − 0,28) / 0,62, convention partagée avec le climat ; la forme relue à 128 km, axes permutés, ajoutée au seuil (`spec-nuages.md`).
- **Le résultat :** nappes texturées aux bords effilochés, cumulus en amas et en allées ; orbite tenue, nuage épais 0,674 ; de près, plus translucides et plus doux.
- **Le coût :** +0,3 à +1,7 ms, le plus au sol sous la convection.
- **Pour le climat :** la part couverte des R partiels bouge un peu avec l'octave ; sa table est à remesurer.

## 2026-10-31 · Les nuages vus de près, sans reflet sur leurs contours

- **Le défaut :** en vol, de près, des nuages de plastique brillant, un cerne sombre sur les contours et les plis, un liseré à contre-jour, un intérieur plat.
- **Les causes, par élimination :** le facteur d'épaisseur F de la diffusion multiple mesuré le long de la vue, mince sur un bord rasant ; des bords opaques en 12 m sur un bruit lisse sous 125 m. Ni la phase ni la carte au mip 0.
- **La correction :** F sur la colonne du nuage là où il existe, lissée à l'échelle de la diffusion, environ 1 km, et au moins l'épaisseur traversée ; la variance des échelles plus fines que les texels des bruits, 0,0124 et 0,033, à toute distance. Écartés : F le long du soleil, de la normale, de la colonne moyenne (`spec-rendu-orbite.md`).
- **Le résultat :** plus de cerne, de pli ni de plastique ; orbite inchangée, nuage épais 0,685. Le relief des cumulus de près reste plus doux qu'avant la piste.
- **Le coût :** +0,1 à +0,5 ms.

## 2026-10-31 · La planète vue d'orbite face à Apollo 17

- **Le défaut :** à 10 000 km, des nuages gris rosé et translucides, un grain sableux sur les nuages lointains, un voile lavande sur toute la planète. Mesuré contre « Blue Marble » : l'océan à 102, 129, 177 en sRGB contre 45, 67, 100 ; les nuages épais à 189, 186, 195 contre 220 à 233.
- **Les causes, établies par élimination et contre des Monte-Carlo** (`tools/calage_orbite.py`) : la diffusion multiple des aérosols, prise isotrope, trois à cinq fois trop forte vers l'orbite, et un sol gris de 0,3 sous l'air ; des nuages plafonnés vers 0,25 de réflectance, une phase renvoyant dix fois trop de lumière simple vers l'arrière, une eau proportionnelle à la couverture ; des pas de six épaisseurs optiques et 4 à 8 rayons ponctuels par pixel de 10 km ; une exposition de paysage.
- **Les corrections :** la similitude de van de Hulst pour les aérosols, `AIR_GROUND_ALBEDO` 0,12 ; une phase de gouttes, g = 0,85, une diffusion multiple calée sur Monte-Carlo, soleil et ciel ensemble, six échantillons vers le soleil, l'eau indépendante de la couverture ; la statistique jointe de la forme et de l'érosion au pixel, en colonnes de recouvrement maximal par empreinte, à la place de la quadrature lointaine ; la carte météo en B-spline ; 0 IL d'exposition en orbite, +1 au sol, la part de l'air sous la caméra entre les deux. Le détail : `spec-rendu-orbite.md`.
- **Le résultat d'orbite :** l'océan à 55, 75, 111, les nuages à 208, 202, 203, plus de grain. En réflectance équivalente, avant la courbe : nuage épais 0,645 contre 0,237, océan 0,061 contre 0,090, contraste 10,5 au zénith et 6,6 au soleil oblique, contre 2,6 et 1,8 ; CERES : 0,5 à 0,8, 0,08 à 0,1. Au-dessus d'une couche à midi, des sommets blancs non écrêtés aux ombres internes plus marquées qu'avant ; au soleil bas, plus douces. Au-dessous, des bases plus claires, un peu crème à midi.
- **Le même jour, la carte se lit au mip 0** et la source multiple décroît en `1 / (1 + b τs)`, la transmission diffuse d'une couche : W 3,40, b 0,040, k 0,061.
- **Le coût :** d'orbite +0,5 ms ; à 10 km +1,7 à +2,8 ms, l'image sous les 60 images par seconde au-dessus des cumulus ; au sol 0,2 à 1 ms de moins.
- **Reste :** une octave manque entre 32 et 160 km, les champs partiels sont flous en taches ; le coût à 10 km.
- **À juger en vol :** `tools/tests/2026-10-31-orbite-rendu.txt`.
- **Pour revenir :** le commit avant le tag `piste/orbite-rendu`.

## 2026-10-31 · L'épaisseur des masses, pour des nappes texturées

- **Ce qui change :** la carte porte au-dessus de R = 0,28 une épaisseur e structurée, que le rendu lit pour l'eau du nuage, `0,25 + 0,75 e` (journal du même jour, l'orbite basse). Nappes et stratus minces, de 0 à 0,25, en cellules de 120 km ; boucliers et bras moyens ; têtes, axes des fronts et cœurs convectifs épais, jusqu'à 1 ; des variations de 80 et 250 km ; e effilé à 0 sur les 40 à 80 km des bords. `spec-nuages.md`, la carte météo.
- **La table R → part couverte,** remesurée sur la loi du rendu avec son octave de 128 km : plus douce, pleine à 0,92 pour R = 0,28.
- **La couverture ne bouge pas,** à 0,02 près : 0,35 et 0,34 sur les graines 0 et 1, ciel clair sur 52 et 53 % de l'aire.
- **Vérifié** à 10 000, 750 et 10 km, sur la branche du rendu fusionnée (`238439c`) : les nappes ont une texture et des bords effilochés vus de 750 km.
- **Écrit par Codex,** relu ; la table mesurée et posée à la main.
- **Pour revenir :** le tag `piste/meteo-bimodale` ; la piste porte le tag `piste/meteo-epaisseur`.

## 2026-10-31 · Des ciels clairs : la couverture bimodale

- **Le défaut, jugé en vol :** « des nuages quasiment partout ». Des champs partiels de 0,35 à 0,7 couvraient presque toute la sphère, et la loi du rendu en faisait un moucheté de cumulus partout, sans un ciel dégagé.
- **Ce qui change :** le ciel est clair par défaut. Le moucheté n'existe que dans quatre régimes, éteints à 0 sur leurs bords : cellules ouvertes derrière les fronts, bords défaits des nappes, alizés en aval des nappes, terres humides et chaudes. Les masses organisées portent la couverture. Anticyclones, dorsales, secteurs chauds et déserts se dégagent sans plancher.
- **Les cibles :** celles de la photo d'Apollo 17, 37 % de blanc, bimodale, et non plus les 0,66 de MODIS, qui comptent cirrus fins et nuages fragmentés.
- **Les chiffres,** graines 0 et 1 : fraction opaque 0,37 et 0,35, contre 0,63 ; ciel clair sur 52 % de l'aire, contre 0 ; couvert sur 31 %.
- **Vérifié** à 10 000, 750 et 10 km, avant et après, sur la branche `integration` et sa loi du rendu.
- **Écrit par Codex,** relu et mesuré ; `spec-nuages.md`, la carte météo.
- **À juger en vol :** `tools/tests/2026-10-31-meteo-orbite.txt`.
- **Pour revenir :** le tag `piste/meteo-orbite` ; la piste porte le tag `piste/meteo-bimodale`.

## 2026-10-31 · La météo vue d'orbite

- **Ce qui change :** la carte météo dessine elle-même, à la façon de la Terre d'Apollo 17, des masses organisées opaques : les virgules des dépressions, 8 à 10 en anneau au sud et 6 à 8 au nord, leurs fronts froids de 2 500 à 5 000 km, leurs boucliers, les amas de la ZCIT, les nappes déchirées des côtes froides. Les champs de petits nuages sont laissés au grain du shader ; les déserts, les fentes sèches et les allées des fronts se dégagent. `spec-nuages.md`, la carte météo.
- **Ce que R veut dire :** la part du ciel couverte, par une table mesurée sous la loi de la session du rendu, où la densité ne dépend plus de R ; l'épaisseur au-dessus de 0,28. Le plafond de 0,6 disparaît.
- **La couverture,** graines 0 et 1 : 0,625 et 0,619, contre 0,110 avant, pour 0,66 sur Terre ; chaque bande de latitude dans ±0,08 des moyennes de la Terre, sauf 20-30° S de la graine 1, plus désertique, à 0,40.
- **Ce qui ne change pas :** le format, ses mips, l'interface, la liste des dépressions ; le shader. Sous la loi actuelle, les champs partiels restent un voile translucide jusqu'à la fusion de la branche du rendu.
- **Le démarrage :** 140 à 220 ms au titre, machine chargée ; au bit près d'un calcul à l'autre.
- **Écrit par Codex** sur trois briefs, relu, calibré et vérifié d'orbite sur deux graines.
- **À juger en vol :** `tools/tests/2026-10-31-meteo-orbite.txt`.
- **Pour revenir :** le tag `piste/nuages-climat` ; la piste porte le tag `piste/meteo-orbite`.

## 2026-10-31 · Les plages, à la distance de l'eau

- **Le défaut :** la plage était une bande d'altitude, de 5 à 25 m. Sur les côtes plates et autour des cordons, des kilomètres de sable à l'intérieur des terres ; sur les côtes raides, une bande de sable peinte au ras de l'eau ; les motus des atolls, à 3 m, tout en sable, sans plantes.
- **La bande :** l'étape 1 de `piste/plages`, commit `c87dcd9`, portée sur la mer FFT (`recherche-cotes.md`). Une hauteur d'eau, de 0 à la berme de 2,5 m, adoucie de ±1 m, multipliée par l'exposition aux vagues ; une part de la terre du pixel, `ShoreBelow` ; sous les pentes de 0,12 à 0,22 ; au-dessus de 0 °C. Sans le sable mouillé ni la laisse de mer de l'étape 2.
- **La largeur plafonnée à 120 m fois l'exposition :** le haut de la bande vaut `min(2,5 m, 120 m × pente)`. Une bande de 2,5 m sur une pente de 0,002 faisait 1,25 km.
- **La pente, à l'échelle de la plage :** prise sur 60 m de part et d'autre, `SHORE_BASELINE`, sur la surface du maillage. Prise sur la normale des matériaux, à 1 m, elle suivait les bosses et le plafond ne mordait pas : au portage, 73 % des terres d'une plaine côtière restaient en plage, 3 % avec la pente prise sur 20 m. Une règle nouvelle de `principes.md`.
- **Au loin, la grille fine porte cette pente** dès que ses mailles couvrent 60 m. Vues de 20 km, les mailles de la face font 417 m : elles ne résolvent plus les flancs d'un cordon, et la normale des sommets, verticale sur sa crête, effaçait sa plage de 5 à 20 km. Plus fine, la grille ramènerait les bosses.
- **L'exposition au large :** l'eau ouverte à 3, 10 et 30 km vers le bas de la pente, lue sur la carte de la planète ; une côte abritée garde 40 % de son exposition.
- **Réglages :** `BEACH` 2,5 m, 1 m, 120 m et 0,4 ; `BEACH_SLOPE` 0,12 et 0,22 ; `BEACH_FETCH` 3, 10 et 30 km ; `SHORE_BASELINE` 60 m.
- **Vérifié en rendu :**
  - les motus d'un atoll, verts et frangés de sable ;
  - un cordon de 20 km à 150 m, sa plage de 50 à 90 m côté mer, plus étroite côté lagune ;
  - une côte plate, la plaine rendue aux couleurs du climat ;
  - une côte raide, sans plage.
- **Les limites :**
  - les mares de quelques centaines de mètres derrière un cordon gardent un anneau de sable : la carte de la planète, lue à 3 km, ne les voit pas abritées ;
  - au-delà de la face du maillage, sans grille fine, un cordon étroit perd sa plage.
- **Coût :** 16 lectures de sommets de plus par sommet sous 60 m de maille ; trois lectures de la carte de la planète par pixel près de la mer. Non mesuré.
- **À juger en vol :** `tools/tests/2026-10-31-plages.txt`.
- **Pour revenir :** le commit `5fc1d47`.

## 2026-10-31 · Les failles des rifts et les cordons des côtes plates

- **Défaut 1, la faille du rift émergé :** vue de près, une tranchée droite en V, des corniches parallèles le long de ses murs, des rangées de dents blanches.
  - **La cause :** le décalage du détail le long des transformantes, 8 km sur une zone de 0,3 km de part et d'autre. Le bruit y était cisaillé 13 fois : étiré le long de la faille, ses pentes multipliées. Il s'appliquait aussi aux rifts obliques, dont la part de cisaillement dépasse 1 m.
  - **La preuve :** dans le moteur, vue `sun` facettée, la bande striée disparaît en coupant ce seul décalage, à deux endroits de la frontière ; le creux de la transformante, le graben et les plis n'y sont pour rien. Au portage, six failles sur les graines 0 à 2 : la même bande partout. Élargir la zone ne suffit pas : à 4 km la tranchée reste, à 8 km le décalage ne se voit plus.
  - **La correction :** le décalage retiré, `RELIEF_TRANSFORM` réduit au creux. Une règle nouvelle de `principes.md`.
- **Défaut 2, le cordon de la côte plate :** un ruban de largeur constante, en segments et en angles vifs, collé à la terre par un bloc rectangulaire.
  - **La cause :** il suivait le contour du rivage bruité. Les octaves fines et les rias du bruit des côtes y font les angles ; dans une ria plus étroite que lui, ses deux flancs se rejoignaient en un bloc plat à 3 m. Sa crête, toujours 3 m, et sa largeur, toujours 0,6 km, faisaient le tuyau.
  - **La preuve :** dans le moteur au même lieu, sans les rias le bloc disparaît, le ruban reste sinueux ; sans le bruit des côtes, le cordon devient un arc lisse. Au portage, le détail domine le rivage des côtes les plus plates : un cordon sur les seules grandes formes tombait à terre sur 50 à 90 % de sa longueur.
  - **La correction :** le cordon suit le rivage lissé, les grandes formes, les trois plus larges octaves du bruit des côtes et du détail. Des îles en arcs entre des passes, recourbées vers elles ; dunes, largeur et crête variables ; des cônes de débordement côté lagune ; relevé depuis le relief sous lui, sa crête entière ; jamais sur la terre émergée. `spec-relief-tectonique.md`, les côtes.
- **La ligne blanche pointillée sur la mer :** un cordon étroit vu de loin, échantillonné par le maillage. Son profil a deux mailles de large, mais seul son sommet émerge, un tiers de sa largeur sur une mer de 10 m : les sommets du maillage tombent tour à tour dessus et à côté. Établi dans le moteur au même cordon : en tirets à 20 km, continu à 8 et à 3 km ; le portage, à 20 m, le dessine continu. Le relever depuis le relief sous lui garde sa crête entière, 3,2 % de ses points au ras de l'eau au lieu de 8,3, mais n'ôte pas les tirets. Reste à faire : une crête émergée d'au moins deux mailles, un profil plus plat au sommet par exemple.
- **Réglages :** `RELIEF_TRANSFORM` en float2 ; `RELIEF_BARRIER_FORM` nouveau, 0,6, 0,15, 4 km, 3 octaves.
- **Les ordres de grandeur,** portage, graines 0 et 2 : inchangés, terres 32,9 et 30,5 %, sommets, fosses, part au-dessus de 3 km ; 9 à 12 % des points bougent, près des transformantes, de 11 à 14 m en médiane.
- **Le portage :** contre la carte de la planète, écart médian 6,5 cm, p99 2,2 m.
- **Coût du terrain :** un bruit de plus sur les cordons ; plus de décalage près des transformantes.
- **À juger en vol :** `tools/tests/2026-10-31-relief-tectonique.txt`, la faille à 40 m et les cordons à 1,5 km et 60 m.
- **Pour revenir :** le commit `ba3372e`.

## 2026-10-31 · Les atolls, sur la forme de leur volcan

- **Le défaut, vu en vol :** des atolls en anneaux trop circulaires, un récif « en bande ». Le contour du récif était un cercle bruité à part, son platier à +0,5 m de largeur constante : la houle le découvrait, une plage continue.
- **La règle :** une forme posée sur une autre en suit le contour (`principes.md`). Le récif se lit sur le contour même de l'édifice, au niveau de l'ancien rivage ; un récif-barrière, un atoll, un guyot ont la forme de leur volcan.
- **Le contour des édifices,** pour tous : allongé selon une direction tirée, jusqu'à 10 % du rayon d'un stratovolcan, 35 % d'un bouclier ; lobé et anguleux, deux octaves, 12 % à un écart-type ; 30 % au plus. La portée de l'index passe à 1,7 rayon.
- **Le récif :** un platier à −1,5 m, sous l'eau, rongé, de 0,25 à 0,8 km, plus large au vent, l'est des alizés ; des motus séparés à +3 m, de 150 à 500 m de large, nombreux au vent, rares sous le vent ; des passes surtout sous le vent ; le fond du lagon par taches.
- **Le repère de chaque volcan redressé :** son « est » était l'ouest.
- **Réglages :** `VOLCANO_REEF` 4,5 m, −12 m, 1,5 km ; `VOLCANO_LOBES` 0,12, 0,1 et 0,35.
- **Vérifié :** trois atolls et un récif-barrière de la graine 0, trois atolls et un récif-barrière de la graine 1, de 25 km à 300 m, au vent et sous le vent ; le portage à 7,6 cm au sol, 0,3 cm sur la carte de la planète.
- **La limite :** les motus restent en sable nu près de l'eau, la plage étant une bande d'altitude de 5 à 25 m (`Materials.hlsli`) ; quelques palmiers seulement.
- **Pour revenir :** le commit `5a546e6`.

## 2026-10-31 · La neige qui scintille au bord de la roche

- **Le défaut :** à 1 m du sol, dans la transition entre la neige et la roche ou le sol orange, la neige scintillait en mouchetures allongées dans la pente et bougeait avec la caméra.
- **La cause :** la normale des décisions était celle des sommets, prise sur deux mailles, 4 cm à 1 m du sol. Elle suivait les millimètres du maillage, 1 à 3° qui changent à chaque glissement ; la neige en dépend par la pente qui la chasse et par l'exposition au pôle, 8 °C par unité d'inclinaison, sur une transition de 2 °C. Établi par élimination au même lieu, à la maille changée seule (k 2,0 contre 2,4) : couper la pente et l'exposition l'annule, rien d'autre. Déjà là avant la pile tectonique, deux fois moins fort.
- **La correction :** les matériaux se décident sur une normale prise à `DECISION_BASELINE`, 1 m de part et d'autre, lue sur la surface du maillage (`VertexShader.hlsl`), là où les mailles sont plus fines ; l'octave de 13,5 m y garde 96 % de sa pente. Sur trois lieux, la neige qui change avec la maille passe de 4,1 % des pixels à 0,2 %, en vol entre deux poses de 2 cm de 4,7 % à 0,8 %.
- **Reste :** à l'arrêt, le maillage repasse du calcul en paires au calcul exact, et quelques lignes de neige basculent une fois, 1,9 % des pixels contre 6,3 %.
- **Coût :** 16 lectures de sommets par sommet sous 1 m de maille ; le dessin du terrain prend 0,05 à 0,14 ms de plus à la mesure.
- **Pour revenir :** le commit `5a7b586`.

## 2026-10-31 · Les nuages tirés du climat

- **Ce qui change :** la carte météo des nuages n'est plus une texture de bruit figée, `weather-planet1024`, sans lien avec la géographie. Elle se calcule au démarrage sur la carte du climat et les grandes formes (`Climate::Weather`) : la convection de la ZCIT en amas, le ciel dégagé sous les anticyclones et sur les déserts, les nappes de stratocumulus au large des côtes à courant froid, 18 dépressions en virgule sur les rails vers 50° avec leurs fronts, leurs boucliers et leurs cirrus, les cellules derrière les fronts, les bancs au vent des reliefs et le ciel clair sous le vent. `spec-nuages.md`, la carte météo.
- **Ce qui ne change pas :** le format, RGBA8 en 1 024 × 512, et ses mips, le maximum de R et de B dès le mip 2 ; le rendu, le vent vers l'est et l'horloge ; la verrière lit la même carte.
- **Retirés :** `assets/clouds/weather-planet1024.rgba8mips` et `tools/gen_cloud_weather.py` (`log/spec-nuages-historique.md`) ; le manifeste ne décrit plus que les trois volumes.
- **Le budget,** graine 0 : couverture moyenne 0,110, contre 0,094 ; au-dessus de 0,2 sur 16,8 % de la sphère, contre 15,5 ; cirrus au-dessus de 0,03 sur 3,3 %, contre 1,6. Le coût des nuages en vol n'est pas mesuré : aucun banc demandé.
- **Le démarrage :** 235 à 296 ms de plus au titre, machine chargée ; au bit près d'un calcul à l'autre. Le moteur écrit `meteo-<graine>.bin` et la liste de ses dépressions, `meteo-<graine>.txt`.
- **À juger en vol :** `tools/tests/2026-10-31-nuages-climat.txt`.
- **Pour revenir :** le commit `07c8e0d`, avant la piste ; la piste porte le tag `piste/nuages-climat`.

## 2026-10-31 · Le catalogue de plantes partagé, la planète nue sans lui

- **Le défaut :** un worktree sans catalogue de plantes, fichiers générés que git ne suit pas, montrait un mur strié à distance fixe de la caméra, partout où pousse la forêt. Signalé en vol sur la branche d'intégration.
- **La cause :** sans catalogue, la canopée au sol était dessinée partout ; vue de sous ses cimes, à hauteur d'homme, elle fait un rideau au bord de la portée des plantes. Établi en ajoutant le catalogue au même worktree : la forêt revient, le rideau disparaît. Le sol nu en deçà de la portée, essayé d'abord, noircissait le sol, ombré par des arbres absents : abandonné.
- **La correction :** sans catalogue, aucune végétation, ni dessinée ni en canopée (`VegetationAbsent`, `TreesHere`, `ShrubsHere`). Le catalogue est publié à côté des dépôts par `tools\plantes.ps1`, `plantes/climate_shrubs_v2`, et tous les worktrees le trouvent en remontant depuis leur exe, comme les scans : un seul catalogue de 743 Mo pour tous.
- **Pour revenir :** le commit `d304da0`.

## 2026-10-31 · Le climat calculé au démarrage

- **Ce qui change :** l'humidité n'est plus un bruit régional et une bande sèche à 24°, ni la température un bruit de ±3,6 °C. Une carte du climat se calcule au démarrage sur les grandes formes de la carte tectonique : les vents des trois cellules, l'équateur thermique qui suit l'été, les dépressions thermiques des terres ; la vapeur portée depuis les mers, la pluie par l'ascendance et au vent des reliefs, l'ombre pluviométrique ; la continentalité ; les courants froids. `spec-climat.md`, le détail.
- **Ce qui la lit :** les matériaux et les plantes, température, humidité et demi-amplitude des saisons ; la couleur de la mer ; la verrière du vaisseau, dont le cube de bruit cuit au démarrage, `ShipClimate.hlsl`, est retiré. Les nuages ne la lisent pas.
- **Réglages :** les lois en tête de `Climate.cpp` ; `CLIMATE_LOCAL` 0,08, la variation de la pluie sous la carte, de 100 à 6 km (`Materials.hlsli`) ; `SEASON_AMPLITUDE` quitte `PlanetSettings.hlsli`, la carte la donne.
- **Les ordres de grandeur,** portage, graine 0 : 879 mm sur les terres ; 2 167 mm de 0 à 10°, 596 de 20 à 30° ; déserts sous 250 mm sur 28,5 % des terres, 33 % de la bande de 20 à 30° ; graines 1 et 2, 45 et 46 % de cette bande.
- **Le démarrage :** 0,22 à 0,24 s au titre, machine chargée ; 8,0 Mo sur le GPU ; au bit près d'un calcul à l'autre. Le fichier `climat-<graine>.bin`, 12,6 Mo, pour le portage et l'érosion.
- **Coût du terrain :** une lecture de la carte et quatre octaves de bruit de plus par pixel des matériaux ; non mesuré.
- **Les lieux changent de climat :** la côte plate tropicale des vues de contrôle est une côte sous le vent, 250 mm ; les mesas, une savane de mousson ; une plaine équatoriale qui était un désert est une forêt.
- **À juger en vol :** `tools/tests/2026-10-31-climat.txt`.
- **Pour revenir :** le commit `fd92705`, avant la piste ; la piste porte le tag `piste/climat`.

## 2026-10-31 · Le volcanisme

- **Ce qui change :** la planète a ses volcans, listés au démarrage à la fin de `Tectonics::Build` et évalués point par point par `Volcanoes.hlsli`, sur la forme avant érosion. `spec-volcanisme.md`.
- **Les lieux :** les arcs sur la plaque chevauchante, à 140 à 230 km de la fosse, un volcan tous les 35 à 80 km ; les rifts continentaux ; 8 à 16 points chauds, chacun une chaîne le long du mouvement de sa plaque, jusqu'à la tête de son panache, traps ou plateau océanique. Chaque volcan ramené par le gauchissement de la lecture de la carte : une règle nouvelle de `principes.md`.
- **Les édifices :** stratovolcans concaves, boucliers presque droits, contours lobés ; cratères et calderas ; coulées de moyenne nulle, en langues étirées le long de la pente ; champs de cônes de scories ; îles arasées, guyots, récifs-barrières et atolls sous les tropiques. Tout profil sur deux mailles au moins, son volume gardé.
- **Dans la carte :** la houle des panaches, 0,6 à 1,3 km ; les traps en marches ; les plateaux océaniques ; la roche volcanique autour des volcans.
- **Les matériaux :** `gVolcanic`, dans l'ancien champ `relief` de `FaceVertex` : basalte pour la roche, cendres et scories sombres pour le sol, plages noires.
- **Réglages :** `VOLCANO_FLOWS` 1,5 km, 0,25 rayon, 40 et 15 m ; `VOLCANO_CONES` 2,5 km ; `VOLCANO_REEF` 0,5 km, 3 m, −12 m, 3 km ; `VOLCANO_LOBES` 0,2 ; `VOLCANIC_ASH` 0,07, `VOLCANIC_COVER` 0,85.
- **Les ordres de grandeur,** portage, mailles de 2 km : terres 32,8, 34,3 et 30,7 %, graines 0 à 2, contre 32,6, 34,0 et 30,5 % ; médiane des terres 388 m contre 380 ; modes +375 et −4 525 m ; au-dessus de 3 km 2,03 % contre 1,99. Graine 0 : 697 stratovolcans, 352 boucliers, 163 calderas, 26 atolls, 113 guyots.
- **Le démarrage :** 60 à 77 ms de volcanisme sur 1,0 à 1,3 s de carte, la machine chargée par d'autres sessions ; mémoire GPU +0,18 Mo.
- **Coût du terrain,** en mouvement, contre la même version les édifices coupés : +0,02 à +0,12 ms aux lieux volcaniques, 0,20 à 0,65 ms en tout ; GPU partagé.
- **Le portage :** `cp.py` lit `volcans-<graine>.bin` ; contre la carte de la planète, 0,4 cm en médiane sur les volcans ; au sol, 7,9 cm en médiane après la fusion de `d304da0` et les cônes placés en doubles, la pente des flancs et le décimètre du titre.
- **À juger en vol :** `tools/tests/2026-10-31-volcanisme.txt`, dix-sept vues.
- **Pour revenir :** le commit `d304da0` de `bruit-propre`.

## 2026-10-31 · Les murs des chaînes vus de près

- **Le défaut :** vu à 1 m, le sol des chaînes formait des espaliers, des murs de 8 à 17 cm tous les 0,5 m, en damier par endroits, et un fourmillement en vol, le maillage glissant sur ces marches. Signalé en vol sur une pente orange et une colline grise.
- **La cause :** la distance lissée à la frontière, des centaines de km en flottant, avançait par pas de quelques cm ; le soulèvement des chaînes et la phase des plis, qui la rendent au relief à environ 1 m par m, en faisaient des marches. Établi en coupant les deux : les murs disparaissent. Ni le scan de roche, ni le spéculaire, ni la position de lecture dans la carte : `precise` sur celle-ci ne changeait rien.
- **La correction :** cette distance lue en double (`TectonicSample.along`), le soulèvement en double, la phase des plis en double ramenée à un tour. Vérifié sur cinq lieux, pente de chaîne, vue d'en haut, dôme enneigé, colline, t43 : plus aucun mur.
- **Réglage :** le soulèvement suit une quintique au lieu d'une tanh, même pente à la frontière et même hauteur, atteinte à 844 km ; le relief des chaînes bouge un peu. Le portage suit.
- **Coût :** une somme de B-spline en double par face lue ; le temps du terrain n'a pas bougé à la mesure, 0,2 à 0,3 ms.
- **Pour revenir :** le commit `fd92705`.

## 2026-10-31 · Les plis des chaînes, moins réguliers

- **Ce qui change :** vus de 300 km, les plis des chaînes formaient des bandes parallèles d'espacement constant, une empreinte digitale. Désormais deux jeux, de 26 et 52 km, se relaient selon un bruit de 120 km : l'espacement varie du simple au double, et les crêtes d'un jeu prennent le relais de l'autre en échelon. Leur amplitude varie par segments de 50 km, de presque rien au double, sur le poids de l'octave ; un décalage commun, jamais plus raide que la distance, les courbe sans boucle ; les chevrons vifs près des jonctions triples s'effacent. `spec-relief-tectonique.md`, le détail.
- **Réglages :** `RELIEF_FOLD` 26 km, décalage 0,35, 150 km ; `RELIEF_FOLD_SETS` nouveau, 2 et 120 km ; `RELIEF_FOLD_SADDLES` 0,8 et 50 km ; `RELIEF_FOLD_REACH` gagne le seuil des chevrons, 0,5 à 0,7 de la pente de la distance.
- **Les ordres de grandeur,** portage, graine 0 : terres 32,9 % ; sommets des 12 plus hautes chaînes 6,9 à 7,6 km, contre 6,3 à 7,3 ; le reste inchangé. La carte tectonique n'a pas bougé : démarrage et mémoire identiques.
- **Coût du terrain :** deux bruits de plus par sommet sur les chaînes, quatre en tout pour les plis.
- **Le portage :** contre la carte de la planète, écart médian 6 cm, p99 1,9 m.
- **À juger en vol :** `tools/tests/2026-10-31-relief-tectonique.txt`, la chaîne à 300 km et la cordillère.
- **Pour revenir :** le commit `f4bf87d`, tag `piste/relief-tectonique`.

## 2026-10-31 · Le relief tectonique, seconde passe

- **Ce qui change :** les défauts connus de la première version corrigés ; `spec-relief-tectonique.md`, ses sections des côtes, du niveau 0 et des mesures.
- **Les côtes :** près du rivage, un bruit de 60 à 3 km déplace la côte de 12 km à un écart-type sur une côte raide, 8 sur une plate ; son amplitude est la pente des grandes formes fois ce déplacement, une règle nouvelle de `principes.md`. Caps, baies, îles et rias ; sur la moitié des côtes plates, des cordons à 2,5 km au large, des lagunes et des flèches ; les plaines côtières plates plus calmes, leurs badlands aussi. Réglages `RELIEF_COAST`, `_COAST_SLOPE`, `_COAST_NOISE`, `_RIAS`, `_BARRIER`, `_BARRIER_GAPS`, `_COAST_QUIET`.
- **Les rifts :** chacun s'ouvre depuis 1 à 3 Ma ; au-delà de 50 km, une mer étroite, croûte jeune de 2 à 3 km de fond, dorsale au milieu, marges jeunes et leurs épaulements. Les autres gardent un fond émergé : un dôme de 1,2 km, des épaulements de 1,1 km, un graben de 0,5 à 0,8 km. Rifts : 2,5, 8,6 et 2,5 % des frontières, graines 0 à 2, contre 15,7, 17,6 et 10,9 %.
- **Les chaînes :** la plus large octave des chaînes en plis, des crêtes continues le long des lignes de niveau de la distance à la frontière, à 36 km, gauchies, des cols ; les vallées entre les chaînons ; les deux octaves suivantes réduites de moitié dessous, plus de taches. Jusqu'à 800 km de la frontière, sauf à mi-chemin de deux. Réglages `RELIEF_FOLD`, `_FOLD_SADDLES`, `_FOLD_REACH`.
- **Le démarrage :** 0,81 à 0,86 s au titre, contre 2,53 s ; 0,88 à 0,90 s hors du moteur. Propagations sur des seaux, calculs indépendants en parallèle, ce qui dépasse 300 km sur un cube de demi-résolution. Mémoire GPU 37,9 Mo, contre 49,5 : la tranche des vues au quart. Toujours au bit près d'un calcul à l'autre.
- **Le niveau 0 :** le soulèvement et l'érodabilité dans la carte, lus par `cp.uplift` et `cp.erodibility` ; le fichier `EXOTECT2`, cinq tranches, 65 Mo. Le branchement est décrit dans la spec, à faire sur `erosion-niveaux`.
- **Les lieux :** le départ du jeu au-dessus d'un continent, −12°, 116,875°, la chaîne à l'horizon ; le globe du lanceur sur le grand continent ; `tools/tests/vues.txt` et ses ombres sur une terre, des collines sous des cumulus épars ; huit vues de contrôle, `rend_tecto.ps1`, référence `base_tecto`.
- **Les ordres de grandeur,** portage, graine 0 : terres 32,9 % ; modes +125 m et −4 525 m ; sommets des 12 plus hautes chaînes 6,3 à 7,3 km ; fosses −9,1 à −10,1 km ; au-dessus de 3 km, 2,0 %.
- **Coût du terrain :** image immobile, 0,1 à 0,4 ms de calcul avant comme après ; en mouvement, non mesuré : quelques bruits de plus près des côtes et sur les chaînes.
- **Le portage :** contre la carte de la planète, écart médian 6 cm, p99 1,8 m.
- **À juger en vol :** `tools/tests/2026-10-31-relief-tectonique.txt`, mise à jour.
- **Pour revenir :** l'entrée `relief tectonique v1, avant vol` de `git stash list`.

## 2026-10-31 · Le relief tectonique

- **Ce qui change :** `Relief.hlsli` est réécrit sur la carte tectonique ; il ne garde rien de la composition héritée de complexplanet, ni graphe, ni réglages, ni noms. La première section de `PlanetSettings.hlsli` devient les réglages `RELIEF_*` ; `CUR_SEED` devient `PLANET_SEED`. `spec-relief-tectonique.md`.
- **La carte tectonique corrigée :** la croûte continentale par lieu, plus par plaque ; les marges passives et actives ; les familles de profils par le signe du mouvement ; quatre tranches par face, avec une bordure, lues en B-spline et mêlées près des arêtes. Une vue `relief` en plus.
- **Les grandes formes :** océans par l'âge, fosses et bourrelets, cordillères et arcs, chaînes de collision et plateaux, avant-pays, rifts, transformantes, vieilles chaînes, cratons ; lois de Stein et Stein, Turcotte et Schubert, Stern.
- **Le détail :** les chaînes en 1 − |n|, orientées le long des frontières ; l'érosion par la pente sur un bruit à dérivées (`RlGradientNoiseD`) ; mesas et badlands. Aucune vallée n'est creusée.
- **Le portage CPU :** `tools/hydro/cp.py` lit la carte du moteur, `x64/Release/tectonique-<graine>.bin` ; 8 cm d'écart au plus contre la carte de la planète.
- **Les ordres de grandeur,** portage, graine 0 : terres 33,0 % ; modes +125 m et −4 625 m ; sommets des 12 plus hautes chaînes 6,8 à 7,9 km ; fosses −9,4 à −10,5 km. Graines 1 et 2 : terres 33,8 et 30,4 %.
- **Coût :** carte tectonique 2,5 s et 50 Mo au démarrage, contre 1 s et 32 Mo ; calcul du terrain en mouvement 0,3 à 0,7 ms aux vues de référence, contre 0,5 à 1,3 ms, et 0,7 à 2,5 ms au ras du sol, contre 3,9.
- **Les lieux tombent ailleurs :** les vues de référence sont en mer, sauf l'orbite et `macro` ; la référence du banc de qualité ne vaut plus.
- **À juger en vol :** `tools/tests/2026-10-31-relief-tectonique.txt`, dix vues ; la carte, `tools/tests/2026-10-31-tectonique.txt`.
- **Pour revenir :** le commit d'avant, `f00004d` ; la piste prendra le tag `piste/relief-tectonique` à son premier commit.

## 2026-10-31 · Le relief en code original

- **Ce qui change :** le relief est réécrit en salle blanche, depuis une spécification fonctionnelle, sans voir le portage de complexplanet ni libnoise. `ComplexPlanet.hlsli` et `LibNoise.hlsli` sont supprimés ; `Relief.hlsli` et `Noise.hlsli` les remplacent. `ComplexPlanetElevation` devient `ReliefElevation`, avec la surcharge `valleys` de `erosion-niveaux`.
- **Le bruit :** gradient de Perlin sur le réseau entier, hachage xxHash32 imbriqué axe par axe, 256 gradients unitaires sur une spirale de Fibonacci. Écart-type 0,40 dans les deux qualités. Chaque octave décalée d'une fraction de maille (`principes.md`). Graines : 64 par module, sans recouvrement.
- **Gardé :** le graphe et ses valeurs, les trois découpages du réseau, le filtrage des octaves, l'arrondi des crêtes, la rugosité. Moyennes remesurées : billow −0,350 et −0,345, ridged 0,510 et 0,505, Voronoï −0,055.
- **Retiré :** `VECTOR_TURBULENCE`, la voie non vectorielle de la turbulence n'existe plus.
- **Le portage CPU :** `tools/hydro/cp.py` réécrit, même hachage ; `tools/cotes/cp.py` s'appuie sur lui.
- **Le caractère,** portage CPU, graine 0, mailles de 55 km, 2 km et 50 m :
  - terres 59,8 / 60,1 / 60,3 %, contre 58,6 / 58,1 / 57,2 % ;
  - médiane des terres 945 / 889 / 880 m, contre 736 / 691 / 686 m ;
  - montagnes 8,6 / 8,9 / 8,6 % des terres, contre 6,6 / 6,7 / 6,8 % ; collines 17,7 / 17,8 / 17,3 %, contre 12,5 à 13,2 % ;
  - point culminant 5,1 / 5,5 / 6,1 km, contre 5,0 / 6,0 / 5,7 km ;
  - sur huit graines, les terres vont de 37 à 60 % ; la médiane et la part des montagnes restent au-dessus de l'ancien relief.
- **Les lieux tombent ailleurs :** départ, bancs et tests en vol sont à revoir. La référence du banc de qualité ne vaut plus.
- **À juger en vol :** `tools/tests/2026-10-31-relief.txt`, de l'orbite au sol.
- **Licence :** `NOTICE` ne cite plus complexplanet ni libnoise ; `LICENSES/LGPL-2.1-or-later.txt` retiré ; `LICENSE` inchangé.
- **Coût :** non mesuré.
- **Pour revenir :** le commit d'avant, `f00004d`.

## 2026-10-30 · Rangement pour l'ouverture

- **Ce qui change :** le dépôt rangé pour sa publication sous GPL-2.0-or-later. L'exécutable sans variable est le jeu ; un seul lanceur, `tools/lance.ps1`.
- **Les commits :**
  - `d4f00c9`, la documentation : specs closes au log, index par thème, licence et `NOTICE` des tiers ;
  - `3a4508a`, végétation et terrain : prototype volumique, végétation v3, relief des matériaux, parois en gradins et préfiltre spline retirés (entrée suivante) ;
  - `df5c2b3`, les docs et outils de végétation à jour, les lanceurs et bancs des modes retirés supprimés ;
  - `3663177`, nuages et atmosphère : un seul chemin, celui du jeu, actif par défaut. L'ancien volume, le POC, le voxel, Wicked V1 à V5, Formes, Courants et les variantes Frostbite sont retirés avec leurs lanceurs, générateurs et assets. Les shaders du jeu sont compilés par le projet sous des noms neutres ; ses quatre textures, figées dans `assets/clouds` avec leur provenance. TAA et halo découplés des nuages : le TAA coupé au démarrage, la touche T le rétablit ; le halo coupé, `MYPLANETENGINE_GLARE` l'active.
- **La lumière de l'air rendue au jeu,** en place, à juger en vol (`tools/tests/2026-10-30-lumiere.txt`) : rayons de soleil, brume sur le sol régional le long de la vue, disque solaire derrière les nuages. La composition des nuages les omettait ; elle reprend l'air de la passe d'atmosphère d'avant (`spec-nuages.md`, l'air autour des nuages).
- **La documentation :** `spike-nuages-planete.md` devient `spec-nuages.md`, la référence des nuages du jeu ; ses sections d'histoire vont dans `log/spec-nuages-historique.md`. Les docs vivantes ne citent plus le code retiré. Le `README.md` racine, en anglais, est la porte d'entrée publique.
- **Écart visuel :** rendu du jeu identique au bit près sur six vues, avec et sans variables, d'après les messages des commits. La lumière rendue change l'air ; non mesurée.
- **Coût :** non remesuré.
- **Pour revenir :** `jalon/29-avant-ouverture`, l'état de `main` d'avant ; la chaîne des données des nuages, `jalon/26-nuages-main`.

## 2026-10-30 · Ouverture : le code hors jeu retiré, végétation et terrain

- **Réglages retirés,** avec le code qu'ils commandaient, commit `3a4508a` :
  - `MATERIAL_RELIEF`, `_BAND`, `_MAX_CELL`, 0 ; 8 mailles ; 8 m, et `RELIEF_NORMAL_CELLS`, 32 : le relief des matériaux dans le maillage, désactivé depuis le 2026-10-23. Tag `piste/parois-gradins`, où il est actif.
  - `WALL_RELIEF`, `_MAX_CELL`, `_SLOPE`, `_CLIFF`, `_REPOSE`, 0 ; 16 m ; 0,55 à 1 ; 0,35 ; 0,67 : les parois en gradins, désactivées depuis le 2026-10-23. Tag `piste/parois-gradins`.
  - `SPLINE_SHARPENING`, 0, et le préfiltre de la spline cardinale : la B-spline lissante lit les sommets eux-mêmes. Tag `jalon/09-normales-spline`.
  - `LEAF_ALBEDO`, 2,6, 1,7 et 1,8, et `PLANT_PIXELS`, 14 à 21 px : les plantes générées v1 à v3, qui ne dessinaient plus rien en jeu. Tag `piste/vegetation-v3`.
- **Le feuillage du jeu, seul et par défaut :** maillages proches, imposteurs lointains, quatorze modèles, HiZ et profondeur matérielle. Ses variables sont retirées, ses réglages en dur ; son catalogue se trouve seul, et sans lui aucune plante. Le prototype volumique, les autres modes et les modèles `photo` et `stylized` restent au tag `piste/vegetation-relais-fondu`.
- **Pourquoi :** la publication du moteur ; sans variable, l'exécutable montre le jeu.
- **Coût :** les passes de copie du relief et du préfiltre ne tournent plus ; elles prenaient 0,07 à 0,19 et 0,02 à 0,13 ms au profil du round 4. Non remesuré.
- **Écart visuel :** rendu du jeu identique au bit près sur six vues, d'après le message du commit.
- **Pour revenir :** les tags ci-dessus ; l'état juste avant est le commit `d4f00c9`.

## 2026-10-29 · Le relais imposteur-maillage : fondu et éclairage

- **Réglage, le fondu :** pour les modèles `game` et les arbustes, un fondu tramé au relais, entre 0,8 et 1,25 fois le seuil de chaque plante. Le tramage change à chaque image : sans antialiasing temporel, coupé par le lanceur de vol, l'œil le fond. La touche H le coupe, pour comparer.
- **Pourquoi :** sans fondu depuis le 2026-10-27, chaque arbre basculait d'un coup, et l'écart de lumière en faisait un saut net.
- **En vol, le fondu :** validé.

- **Réglage :** l'imposteur s'éclaire sur la dispersion de ses feuilles. La longueur de sa normale moyenne en donne la cohérence ; le direct, le contre-jour et le terme sol/ciel en prennent l'espérance, au lieu de la normale renormalisée qui l'éclairait comme une carte face à l'œil. Ses couleurs cuites se moyennent en linéaire, et non plus en sRGB ; les quatorze imposteurs sont recuits.
- **Pourquoi :** en vol, un arbre sombre s'éclairait en devenant maillage. Antérieur à l'optimisation : `242d0f7` donne la même image.
- **Mesure, luminance maillage / imposteur des mêmes plantes, 4 lieux et 5 soleils :** au sol, de 0,82–1,30 à 0,87–1,15, écart moyen de 13 à 7 % ; au relais, à 25 m du sol, de 0,86–2,05 à 0,86–1,74, écart moyen de 21 à 13 %. Le reste, maillage plus clair sous un soleil haut devant ou rasant, n'est pas expliqué.
- **Coût :** quelques opérations par pixel d'imposteur, non mesuré au banc.
- **Écart visuel :** les maillages sont identiques au bit près ; tous les imposteurs changent, plus clairs en contre-jour et sous un soleil haut, plus sombres soleil dans le dos.
- **En vol, l'éclairage seul :** sans effet visible sur le saut ; gardé avec le fondu. `tools/tests/2026-10-29-imposteurs-eclairage.txt`.
- **Détail :** `vegetation-planetaire.md`, l'éclairage des imposteurs.

## 2026-10-29 · Optimisation, round 8 : le sol en vol rapide

- **Réglage :** sous 14 km, une trouée de ciel dans les feuilles que ni l'historique ni les tuiles fraîches ne voient prend le texel le plus proche de l'historique qui voit le ciel, au lieu d'être tracée par la résolution ; à défaut, claire pour une image. En vol, mailles de moins de 4 m, la grille du terrain se découpe en paires de floats au lieu de doubles, dans un shader à part ; le sommet sous la caméra reste exact, et tout le maillage à l'arrêt.
- **Mesure, `tools/banc_perf.py`, vol rapide à 5 % de la hauteur par image, contre le binaire d'avant dans la même séance :** forêt de 49 à 60 fps réels, lisière de 43 à 55, montagne de 48 à 54 ; calcul du terrain de 4,6 à 3,0 ms en forêt, résolution des nuages de 3,6 à 0,9 ms en lisière. Au-dessus du sol, inchangé.
- **Écart visuel :** image immobile identique au bit près ; en mouvement, 0,05 à 0,09 niveau moyen au sol contre le binaire d'avant, aux bords des feuilles ; contre la passe pleine, les mêmes écarts à 0,1 niveau près. `banc_qualite.py` sans p95 changé.
- **En vol :** validé, `tools/tests/2026-10-29-optimisation-sol-vol-rapide.txt`. Les arbres qui s'éclairent en passant de l'imposteur au maillage viennent d'avant l'optimisation : l'éclairage de l'imposteur, traité à part.
- **Détail :** `optimisation.md`.

## 2026-10-29 · Optimisation, round 7 : nuages en vol rapide

- **Réglage :** sous 14 km, la porte de la quadrature lointaine, les pixels dont l'historique des nuages a glissé ou tourné ne sont plus tous retracés : un pixel par carré 2×2 est tracé, à tour de rôle, les trois autres en sont interpolés. Au-dessus, rien ne change. Le round 6, mis de côté, reste au tag `piste/optimisation-r6-nuages-mouvement`.
- **Mesure, `tools/banc_perf.py`, vol rapide à 5 % de la hauteur par image :** cumulus à 10 km, passe de 24,2 à 8,1 ms, de 36 à 90 fps réels ; 150 m sous les cumulus, de 59 à 70 fps, et en plongée de 34 à 52. À 160 km, 440 km et en orbite, inchangé : 57, 53 et 22 fps.
- **Écart visuel :** image immobile identique au bit près ; en mouvement, contre la passe pleine, écarts égaux sur onze vues, sauf le cumulus en vol rapide, 0,06 → 0,13 niveau moyen par des écarts d'un niveau, moins de pixels au-delà de 8. `banc_qualite.py` sans p95 changé.
- **En vol :** validé, `tools/tests/2026-10-28-optimisation-nuages-rapides.txt`.
- **Détail :** `optimisation.md`.

## 2026-10-28 · Optimisation, round 5 : images en vol

- **Réglage :** aucun. Mesuré puis arrêté : le GPU n'attend le CPU que 0,6 à 1,2 ms par image, sous le seuil d'1 ms au sol. Le banc mesure désormais l'image du CPU, la cadence réelle et l'inactivité du GPU.
- **Mesure, `tools/banc_perf.py`, 1080p :** enregistrement et soumission 0,6 à 0,9 ms, préparation 0,01 ms ; au sol, cadence réelle de 64 à 71 fps immobile, 44 à 50 en vol, contre 68 à 75 et 45 à 52 au temps GPU. Deux images en vol rendraient ces 4 à 6 % au sol.
- **Écart visuel :** aucun, dix vues identiques au bit près.
- **Détail :** `optimisation.md`.

## 2026-10-28 · Optimisation, round 4 : calcul du terrain

- **Réglage :** le calcul du terrain n'est pas relancé quand les constantes que lisent ses passes sont, au bit près, celles de l'image précédente ; le maillage seul égal, la caméra tournant sur place, seuls les sommets entrés dans la vue sont calculés.
- **Mesure, `tools/banc_perf.py`, 1080p :** immobile, calcul du terrain de 3,3 à 4,2 ms à 0 au sol, 73 à 76 fps ; en tournant sur place, de 4,3 à 1,7 ms en forêt, 52 à 59 fps au sol. En vol, rien ne change : 41 à 52 fps au sol.
- **Écart visuel :** aucun, immobile comme en mouvement, contre le calcul entier à chaque image ; `banc_qualite.py` sans p95 changé.
- **En vol :** validé, `tools/tests/2026-10-28-optimisation-terrain.txt`.
- **Détail :** `optimisation.md`.

## 2026-10-28 · Optimisation, round 3 : végétation

- **Réglage :** sol exact des tuiles de plantes gardé d'une image à l'autre, effacé à chaque saut de la caméra ; imposteurs en profondeur conservatrice, à la borne de leur test HiZ ; maillages proches en profondeur d'abord, couleur en profondeur égale ; tri des tuiles sans ses seize plans quand la borne le prouve.
- **Mesure, `tools/banc_perf.py`, 1080p :** placement et feuillage de 18-20 ms à 6 ms en forêt ; 54 à 59 fps au sol, 83 en survol, 115 en mer.
- **Écart visuel :** au plus 1 niveau sur 3 à 11 pixels, sur seize vues ; `banc_qualite.py` sans p95 changé. En mouvement, la table garde des arrondis d'une caméra précédente : 0,006 % des pixels au plus.
- **En vol :** validé, `tools/tests/2026-10-28-optimisation-vegetation.txt`.
- **Détail :** `optimisation.md`.

## 2026-10-28 · Optimisation, round 1, suite : nuages en mouvement

- **Réglage :** l'historique des nuages qui a dérivé, ou dont la direction de vue tourne de plus d'1° par image, est retracé au lieu d'être rempli ; dérive mesurée sur l'étalement en distance de la lumière ; moyenne lointaine plafonnée à deux rayons en mouvement. L'air de la composition n'est plus coupé qu'au pas où se trouve le nuage.
- **Mesure, `tools/banc_perf.py`, vol rapide à 5 % de la hauteur par image :** plaques à 160 km de 18 % à 3 % de l'image contre la passe unique ; au-delà de x5 en orbite, la passe coûte la passe unique, 10 à 38 ms.
- **Écart visuel :** image immobile à moins de 0,3 niveau ; `banc_qualite.py`, mêmes sites que le round 2, tous les p95 identiques.
- **En vol :** plaques et seconde peau disparues ; reste un bruit des nuages à haute vitesse, mis de côté, comme les traînées de la plongée depuis l'orbite.
- **Détail :** `optimisation.md`.

## 2026-10-28 · Optimisation, round 2 : dessin du terrain

- **Réglage :** pré-passe de profondeur du terrain, puis sa couleur en profondeur égale, après objets et feuillage ; strates, présence des bois et fondus de la végétation calculés seulement où ils peuvent changer le pixel.
- **Mesure, `tools/banc_perf.py`, 1080p :** dessin du terrain de 11-17 ms à 3-7 ms près du sol ; de 27-28 à 33-37 fps au sol, 64 en survol.
- **Écart visuel :** au plus 1 niveau sur quelques pixels ; `banc_qualite.py` sans p95 dégradé, comparé à `main` sur les mêmes sites.
- **En vol :** validé avec les nuages en passe unique (`nuages-planete.ps1 -PassePleine`, nouvelle option). Les plaques vues en vol viennent de la passe temporelle des nuages, en correction.
- **Détail :** `optimisation.md`.

## 2026-10-28 · Optimisation, round 1 : nuages et atmosphère

- **Réglage :** passe temporelle des nuages, une trace par tuile 4×4 et par image, reprojetée dans le repère de la météo ; quadrature lointaine étalée sur jusqu'à huit visites. `MYPLANETENGINE_CLOUD_FULL=1` rend la passe unique d'avant.
- **Mesure, `tools/banc_perf.py`, 1080p :** passe des nuages de 10 à 51 ms à 1,2 à 4,8 ms ; de 17 à 34 fps à 27 à 195 fps selon la vue.
- **Écart visuel :** image immobile de 0 à 0,65 niveau ; 0,8 % des pixels au-delà de 8 niveaux au globe, dans le grain du bord.
- **Reste à juger en vol :** zones découvertes et ombre au sol en retard d'au plus 16 images ; `tools/tests/2026-10-28-optimisation-nuages.txt`.
- **Détail :** `optimisation.md`.

## 2026-10-28 · Profil Release et plein écran

- **Demande :** exécutable optimisé en plein écran, avec meilleure utilisation des ressources et conservation du rendu.
- **Affichage :** résolution du moniteur au démarrage, fenêtre sans bordure, Alt+Entrée et Échap ; présentation libre avec capacité DXGI vérifiée. Les captures et bancs restent invisibles.
- **Compilation :** options Release x64 `/O2`, fonctions en ligne, vitesse, optimisation globale et LTCG explicites ; sélection du GPU haute performance déjà présente, contrôlée et nom du GPU affiché.
- **Profil :** `tools/lance_optimise.ps1` prépare `x64/Optimise/MyPlanetEngine.exe` et son fichier INI ; nuages, végétation détaillée et mer conservés. Le profil se recharge aussi par double-clic ; les variables de banc priment.
- **Limites :** une image GPU en vol, constantes et lectures CPU encore partagées ; le plein écran1080p demande2,25 fois les pixels du720p. Pas de changement de portée, de densité ou de qualité pour produire un gain apparent.
- **Vérification :** trois vues720p comparées au runtime précédent, un pixel différent au total ; deux vues1080p hors écran, forêt et mer, profil chargé et aucun dépassement végétal. Plein écran1920×1080 et retour en fenêtre observés ; capture souris annulée lors du basculement pour éviter une rotation parasite.
- **État :** runtime préparé et relancé ; pas de gain FPS global mesuré, aucun commit ni push demandé. Guide : `execution-optimisee.md`.

## 2026-10-27 · Composition des ombres de nuages sur la végétation

- **Cause :** arbres et arbustes détaillés écrivaient leur couleur mais pas leur part solaire ; la composition relisait celle du terrain caché. Le chemin HiZ ne reliait aussi que la cible HDR après le calcul d'occlusion.
- **Effet :** silhouettes noires ou végétation apparemment transparente devant le terrain, surtout clair ; les contours suivaient les formations végétales dessinées au sol, pas l'horizon.
- **Correction :** deux sorties cohérentes sur toutes les surfaces opaques, y compris la profondeur matérielle et les imposteurs ; soleil direct séparé sans changer l'éclairage total des modèles. Réunion des deux cibles après HiZ ; retrait solaire borné et strictement neutre à transmission1.
- **Régression reproduite :** en transmission forcée à1, l'ancien rendu modifiait154921,433185,37695 et115553 pixels de plus de1/255 sur quatre vues ; les nuages entièrement désactivés retrouvaient les mêmes images avec/sans ombres.
- **Contrôle après correction :** compilation native Release x64 et72 shaders, puis shader Planète DXC ; transmission forcée à1 : quatre images strictement identiques avec/sans composition solaire, zéro pixel différent. Ni modèles, ni géométrie, ni population modifiés.
- **Conservation :** composition solaire désactivée, quatre images avant/après strictement identiques ; éclairage des modèles conservé. Deux captures avec vraies ombres inspectées au sol et à35 m en forêt boréale : silhouettes opaques retrouvées ; vol relancé à35 m depuis main.
- **Outil :** `tools/banc_composition_surfaces.py`, quatre vues hors écran ; captures et rapports dans `x64/SurfaceComposition/`. Aucun commit ni push demandé ; vérification en mouvement confiée à l'utilisateur.

## 2026-10-27 · Activation de la végétation dans le lanceur nuages

- **Cause :** les modèles détaillés étaient dans main, mais le lanceur nuages effaçait les variables de végétation sans sélectionner leur mode ; le rendu historique restait actif.
- **Correction :** `tools/nuages-planete.ps1` sélectionne par défaut `hybrid-impostor`, modèles `game`, catalogue `climate_shrubs_v2`, volume0,65, HiZ et profondeur matérielle.
- **Contrôle :** caches des deux arbres et douze arbustes présents ; application relancée près du sol, titre confirmant les modèles de jeu et des maillages d'arbres et d'arbustes actifs, sans dépassement. Vérification visuelle en vol confiée à l'utilisateur.
- **Comparaison :** `-AncienneVegetation` retrouve le mode précédent ; `-Parcours` permet de choisir la palette végétale sans changer la palette nuages par défaut. Aucun shader ni modèle modifié.
- **État :** correction locale sur main, sans commit ni push demandés.

## 2026-10-27 · Retour de l'éclairage précédent et fusion de main

- **Décision utilisateur :** « C'était mieux avant. » Compensation diffuse retirée ; éclairage du commit `5b53b81` conservé. Essai et mesures déplacés dans `log/spike-nuages-lumiere.md`.
- **Intégration :** fusion de `main` au commit `f66ead9` dans `codex/nuages-voxel-poc`, sans réécriture de son historique publié ; piste `piste/nuages-main-integration`.
- **Contrats :** végétation et angle du pixel restent dans `taa.zw`, mer dans `waveAxisX/Y`, météo dans `cloudMotion.xy` ; carte globale en `t29`, hors des ressources des nuages. Diagnostic nuages32, diagnostics terrain et climat de main conservés.
- **Surfaces :** mer FFT avec profondeur signée conservée pour le lissage, distance absolue pour les rayons de nuages. La seconde cible reçoit le direct solaire exact du sol, de l'eau et de l'écume ; le reflet du ciel reste séparé.
- **Construction :** lanceur Planète reconstruit le natif Release x64 et ses shaders dans un dossier isolé ; liens Direct3D et sous-système Windows configurés aussi en Release. Témoins figés inchangés.
- **Vérification :** C++ et72 shaders du projet compilés, puis variante Planète DXC ; captures hors écran en orbite et à60 m au-dessus de la mer FFT. Nuages+air ponctuels27,65 et17,75 ms ; pas de banc prolongé ni de validation en mouvement.
- **Végétation détaillée :** démarrage avec les assets locaux de main,13610 imposteurs, zéro dépassement ni flottement ; GPU total37,97 ms, dont14,44 ms nuages+air, sur une seule capture.
- **Référence :** `docs/spike-nuages-planete.md`, `tools/nuages-planete.ps1`, captures dans `x64/MainCloudPreview/`.

## 2026-10-27 · Intégration des performances végétales · `jalon/25-vegetation-performance-main`

**Décision :** demande de commit, push, rebase puis fusion dans `main`.

**Contenu :** bases angulaires partagées, HiZ de l'image courante, masque conservateur et variante de profondeur matérielle des maillages proches. Modèles, sources, densité et portée conservés.

**Vérification :** compilation et bancs déjà terminés avant le vol comparatif ; résultats et limites dans `vegetation-hiz.md` et `../tools/foliage/results/2026-10-27/hiz.json`.

**Suite :** réduire le coût du placement et des calculs de terrain ; le gain du dessin ne suffit pas encore à garantir une grande marge globale en vol.

## 2026-10-27 · HiZ végétation · base `piste/vegetation-hiz-base`

**Demande :** culling hiérarchique par profondeur, à rendu, densité et portée conservés ; dégager une marge au-dessus des 30 FPS signalés.

**Règle :** profondeur de l'image courante après terrain et maillages proches, pyramide par minimum en Z inversé, masque de visibilité GPU. Sources et ordre de dessin conservés ; cas incertains visibles. Les imposteurs cachés produisent un quad dégénéré avant le travail coûteux.

**Profondeur proche :** variante matérielle du shader mesh, mêmes couleurs et découpes alpha, sans profondeur recalculée ni earlydepthstencil forcé. Le témoin reste accessible.

**Mesures :** quatre états intercalés dans un seul processus, six vues, 64 cycles par vue. Rendu végétal tempéré intérieur de 10,30 à 4,64 ms, tropical de 8,21 à 3,46 ms ; le temps GPU total reste borné aussi par terrain et placement. Voir `vegetation-hiz.md`.

**Vérification :** HiZ seul strictement identique sur quatorze vues dans les deux modes de profondeur ; variante finale avec 25 pixels d'écart au total. Populations et ressources inchangées, zéro dépassement. Banc général : dix pixels modifiés sur 745 crops, aucune nouvelle régression de plus de 10 % sur 59 p95 face au témoin courant ; écarts canoniques antérieurs conservés. Synthèse : `../tools/foliage/results/2026-10-27/hiz.json`.

**État :** intégré au jalon 25 ; compilation et bancs hors écran terminés. Version relancée en vol par `tools/lance_vegetation_hiz.ps1`, zéro dépassement à la vue de départ ; témoin accessible par `-Reference`.

## 2026-10-27 · Optimisation de la végétation · base `piste/vegetation-optimisation-base`

**Demande :** réduire le coût en conservant le rendu, la densité et la portée, puis relancer en vol ; auditer le culling existant.

**Changement retenu :** les bases angulaires des quatre vues d'imposteurs, déjà calculées au vertex, sont réutilisées au pixel. Le placement, les représentations, les seuils et les modèles restent identiques.

**Mesure :** horodatage du placement distinct de la classification, même instrumentation dans le témoin et le candidat. Les essais de scans ne donnent pas de gain stable et sont écartés ; `log/optimisation-vegetation-historique.md`.

**Culling :** rejet des sommets hors champ avant le bruit de relief, filtrage des octaves, sélection de tuiles puis de plantes, commandes indirectes et profondeur. Aucune pyramide de profondeur pour éliminer les plantes masquées ; `optimisation-vegetation.md`.

**État :** travail non commité sur sa branche, intégré depuis au `jalon/25-vegetation-performance-main`, base taguée ; compilation et comparaisons hors écran, puis palette de vol `2026-10-27-vegetation-performance.txt`.

**Vérification :** quatorze BMP identiques, mêmes comptes par modèle, zéro dépassement. Banc général sur six lieux et cinq hauteurs : 744 PNG identiques sur 745, un pixel d'écart de 1/255, aucun nouveau p95 dégradé de plus de 10 %. Dessin des forêts denses réduit d'environ 0,3 à 0,55 ms dans plusieurs vues ; temps total variable. Synthèse : `../tools/foliage/results/2026-10-27/optimisation.json`.

## 2026-10-27 · Intégration validée · `jalon/24-vegetation-detaillee-main`

**Décision :** l'utilisateur valide la végétation en l'état et demande son rebase puis sa fusion sur `main`.

**Périmètre :** modèles de jeu, maillage proche et imposteurs lointains, bouquets et éclairage, douze arbustes climatiques. Densité et portée du vol validé conservées. La maquette Dendry de la branche de départ reste hors de cette intégration ; la mer de `main` est conservée.

**Acceptation :** jugement visuel utilisateur, avec les cinq écarts p95 connus des comparaisons appariées. Le seuil automatique reste non satisfait ; aucun changement de métrique ni de référence. Les rapports et leurs limites restent consignés dans les deux specs de végétation.

**Intégration :** compilation complète Debug x64 réussie après rebase, mer et végétation réunies. Plages de descripteurs séparées ; horodatages mer 6–7 et végétation 8–11. Aucun banc de rendu relancé pour cette fusion.

**Suite différée :** optimisation des performances GPU et de la mémoire, décrite dans `optimisation-vegetation.md`, base `piste/vegetation-optimisation-base`. Aucun nouveau réglage de rendu pour cette phase.

## 2026-10-27 · Arbustes climatiques · base `piste/arbustes-climatiques-base`

**Demande :** diversifier les arbustes et leur donner un port et un feuillage cohérents avec le froid, l'aridité et la montagne, comme les arbres.

**Réglages :**
- Six familles, deux architectures chacune ; 2 492 à 4 272 triangles par modèle.
- Hauteurs relatives : boréal 0,65, désert 0,85, steppe 0,60, montagne 0,30, tempéré 1, tropical 1,15 ; couronne maximale de référence 1,1.
- Partition continue des champs climatiques existants, sans plancher forçant une famille hors de son climat.
- Graines, positions, tailles sources, présence et portée conservées ; mêmes fichiers des deux arbres.
- Six régions GPU partagées de 192 Mio ; comptage, préfixes et dispersion, puis dessins groupés par représentation et commandes vides ignorées sur GPU.

**Vérification :** compilation isolée réussie ; identités et positions identiques sur quatorze vues, mêmes totaux, zéro dépassement ; quatre lieux voisins supplémentaires. Les BMP avant/après réorganisation des appels sont identiques. Les représentations ajoutent environ 445 Mio de données, hors files.

**Qualité :** les vingt-quatre sites terminent sans perte GPU, mais deux p95 régressent de plus de 10 % face au candidat précédent. Les trois échecs antérieurs restent hérités. Il s'agit d'une piste de jugement, sans validation du critère du projet ; `arbustes-climatiques.md` et son log donnent les mesures.

**Retour :** `-Assets assets/foliage/volume_look_normals` retrouve l'arbuste unique précédent sur le même exécutable. Le tag est sur le commit de départ ; les changements ne sont pas commités.

## 2026-10-27 · Bouquets et lumière · base `piste/vegetation-bouquets-lumiere-base`

**Demande :** poursuivre le rendu des feuillus et des arbustes par itérations comparées à des références de forêt ; plus de densité foliaire et de volume, même population et portée.

**Réglages :**
- Feuilles d'origine réparties autour des rameaux ; feuillu 7 010 triangles, arbuste 13 406, pin inchangé.
- Normales foliaires mélangées à 55 % vers un champ radial local, biais haut 0,15.
- Ciel : seize rayons précalculés ; soleil : six directions locales ; force de rendu 0,65.
- Couvert lumineux du sol et des objets composé par transmission : l'addition arbres + arbustes dépassait parfois 1.
- Relais 96–128 pixels, fenêtre 512 et sortie 5–8 pixels inchangés.
- Les premiers essais comparent la géométrie, puis les forces 0 / 0,65 / 1 et les normales à géométrie égale ; les mesures intermédiaires restent dans le log.

**Vérification :** captures cachées sur huit vues, deux soleils et quatre biomes ; mêmes six comptes d'instances, aucun dépassement dans ces vues. Une lecture hors allocation du buffer de visibilité absent a été identifiée dans le shader compilé, corrigée par un tampon neutre complet, puis vérifiée sur la vue qui bloquait le GPU. Les rapports détaillés sont sous `x64/ForetVolumeComparaisons/` ; `vegetation-planetaire.md` décrit le protocole.

**Retour :** `-Assets assets/foliage -Volume 0` retrouve les modèles et leur éclairage source ; la composition corrigée du couvert du sol reste active. Le tag désigne le commit de départ ; les modifications et les données générées ne sont pas dans un commit.

**Statut du banc :** les deux séries de 24 sites terminent sans perte GPU. Le candidat ne passe pas trois p95 sur 59 ; il reste une piste de jugement, sans correction acceptée. Les mesures, leurs échantillons et les limites des masques sont consignés dans `vegetation-planetaire.md` et son log.

## 2026-10-27 · Silhouettes et arbustes · base `piste/vegetation-silhouettes-arbustes-base`

**Demande :** corriger le grain et le flou à hauteur d'homme, puis remplacer les arbustes pleins en restant efficient ; même densité et même portée, sans tests avant le vol.

**Le changement :**
- Modèles `game` : une seule représentation par plante, seuil stable de 96 à 128 pixels selon la graine et l'encombrement projeté hauteur/largeur.
- Fin du fondu en points pour ces modèles ; troncs proches opaques. Un saut de forme reste possible au relais.
- Alpha-test fixe 0,5 pour leurs imposteurs ; mipmaps conservant approximativement la couverture et soutien de silhouette entre les quatre vues.
- Textures des maillages filtrées par le matériel, anisotropie ×8, mipmaps pondérés par alpha et couleurs dilatées aux bords.
- Arbuste Searsia Lucida f CC0 de Poly Haven, 7 232 triangles, branches et feuilles découpées ; même pipeline que les arbres.
- Six files GPU et quinze SRV ; les anciens appels de dessin des plantes sont sautés en mode planétaire.
- Présence, graines, allométrie, fenêtre 512 tuiles et retrait à 5–8 pixels conservés.
- F12 reprend la vue au sol signalée ; `-Sun` permet de reprendre aussi son éclairage.

**Préparation :** construction des assets, revue statique croisée et compilation uniquement ; aucun test, banc ou capture de contrôle avant le vol.
- L'initialisation et la mémoire augmentent ; le buffer des files réserve 192 Mio. Aucun gain de FPS annoncé sans mesure.
- Les modèles d'arbres sont conservés pour juger d'abord leur représentation ; la qualité de la bibliothèque reste à poursuivre.
- Travail non commité ; le tag garde la base, pas les modifications locales.

**Détail :** `vegetation-planetaire.md` ; signalement précédent dans `log/vegetation-planetaire-historique.md`.

## 2026-10-27 · Modèles d'arbres pour le jeu · base `piste/vegetation-modeles-jeu-base`

**Demande :** des arbres réalistes de qualité jeu AAA, feuilles et branches crédibles ; densité et distance conservées, essai directement en vol.

**Le changement :**
- Pin d'evolveduk sous CC BY 4.0, 5 627 triangles ; feuillu Rakshi Games Tree10_1 sous CC BY 3.0, 3 308 triangles.
- Modèles d'artistes, branches maillées et cartes de feuillage découpées ; les bouquets opaques ont été rejetés.
- Atlas couleur, normales, rugosité et transmission ; normales Unity empaquetées converties pour le feuillu.
- Le feuillu utilise une rugosité constante ; les cartes source du pin sont conservées.
- Normal mapping proche, occlusion ambiante, reflet solaire modéré et transmission foliaire bornée ; lumière atmosphérique commune.
- Imposteurs 12 × 5 en 128² et volume 64³ reconstruits depuis les mêmes maillages ; filtrage matériel et rectangles conservés.
- Même peuplement, hauteur, largeur de couronne, retrait 5–8 pixels et relais maillage/proxy 384–512 pixels.
- Le lanceur choisit `-Models game` et `-Mode hybrid-impostor` par défaut ; crédits et sources dans `../assets/foliage/game_origins.md`.

**Préparation :** sources récupérées, conversion, construction des représentations et compilation uniquement ; aucun test, banc ou capture de vérification avant le vol.
- La qualité visuelle et les performances restent à juger ; les budgets de triangles ne prouvent pas un niveau AAA.
- Travail non commité ; le tag garde la base, pas les modifications locales.

**Détail :** `vegetation-planetaire.md`.

## 2026-10-27 · Arbres semi-réalistes stylisés · base `piste/vegetation-stylisee-base`

**Demande :** remplacer les modèles trop photoréalistes par des formes naturelles au feuillage en masses ; même densité et même portée, jugement directement en vol.

**Le changement :**
- Deux modèles originaux construits hors ligne : feuillu ramifié, 9 720 triangles ; conifère étagé, 8 174 triangles.
- Bouquets lobés opaques, percées dans la couronne, branches effilées et textures de couleurs simplifiées.
- Même maillage source pour les imposteurs 12 × 5 en 128² et le volume 64³.
- `-Models stylized` devient le défaut du lanceur ; `-Models photo` garde les arbres précédents pour comparaison.
- Même population, graines, climat, allométrie, distances et relais à 384–512 pixels.
- Filtrage matériel et rectangles projetés conservés ; les arbustes gardent leur géométrie actuelle.

**Préparation :** génération des assets, revue statique et compilation ; aucun test, banc ou capture de vérification avant le vol.
- Les budgets de triangles décrivent les nouveaux maillages ; ils ne mesurent pas un gain de FPS.
- Travail non commité ; le tag garde la base, pas les modifications locales.

**Détail :** `vegetation-planetaire.md` et `../assets/foliage/README.md`.

## 2026-10-27 · Rectangles et filtrage matériel des imposteurs · base `piste/vegetation-imposteurs-filtrage-base`

**Demande :** optimiser les imposteurs sans changer la densité ni la distance ; relancer pour comparaison en vol, sans tests préalables.

**Le changement :**
- Rectangle perspective calculé sur les quatre plans de vues, limité à l'ancien carré ; marge d'un pixel et repli conservateur au plan proche.
- Deux tableaux de textures RGBA16F par espèce ; couleur linéaire, normales et profondeur prémultipliées par la couverture.
- Filtrage bilinéaire et entre mipmaps par le matériel ; même mélange des quatre vues.
- Population, modèles, placement, relais à 384–512 pixels et retrait à 5–8 pixels conservés.
- Les modèles suivants devront suivre la direction semi-réaliste stylisée choisie par l'utilisateur : formes naturelles et feuillage en masses.

**Vérification :** revue statique et compilation uniquement ; aucun banc, capture ou test avant le vol de l'utilisateur.
- Aucun gain chiffré annoncé avant comparaison.
- Travail non commité ; le tag garde la base de la piste, pas l'état des modifications locales.

**Détail :** `vegetation-planetaire.md`.

## 2026-10-27 · Sélection stable des arbres · base `piste/vegetation-compaction-stable-base`

**Problème :** des arbres lointains clignotent à caméra immobile pendant le vol de l'utilisateur.

**Cause identifiée :**
- Le titre annonce 87 395 plantes lointaines pour une liste de 65 536, et un autre dépassement dans le renderer.
- Les append atomiques saturés gardent des sous-ensembles différents selon l'ordre des vagues GPU.

**La règle corrigée :**
- Index fixe de tuile, puis sommes préfixes et compaction dans un ordre déterministe.
- Même méthode pour les individus proches et lointains ; les grandes octaves sont prioritaires.
- Listes sources de 262 144 plantes ; files de rendu de 524 288, suffisantes pour leur union.
- Les limites amont restent explicites ; elles ne choisissent plus les arbres selon l'ordre d'arrivée.
- Les modèles, le climat, les graines, le terrain et les seuils de distance restent les mêmes.

**Vérification :** lecture des compteurs existants, revue statique croisée et compilation ; aucun banc ni capture préalable, selon la demande de l'utilisateur.
- La mémoire temporaire augmente ; le peuplement auparavant tronqué peut aussi demander davantage de dessin.
- La stabilité et le coût de cette version restent à juger en vol.

**Détail :** `vegetation-planetaire.md` ; essais remplacés dans `log/vegetation-planetaire-historique.md`. Travail non commité.

## 2026-10-27 · Maillage proche et imposteurs lointains · base `piste/vegetation-imposteurs-hybrides-base`

**Demande :** juger l'approche avec les imposteurs sur les mêmes forêts, sans tests préalables.

**Le changement :**
- Nouveau mode `hybrid-impostor` : les modèles détaillés remplacent les imposteurs à l'approche.
- Même relais complémentaire entre 384 et 512 pixels que l'hybride volumique.
- Même population, placement, taille, climat, lumière et palette F1 à F12.
- Le mode `impostor` reste disponible pour les imposteurs seuls, même de près.
- Compilation puis lancement interactif ; aucun banc ni capture de validation.
- Les performances et le rendu de cette variante restent à juger en vol.

**Lancer :** `tools/lance_planet_foliage.ps1 -Mode hybrid-impostor`. Travail non commité ; détail dans `vegetation-planetaire.md`.

## 2026-10-27 · Essai planétaire de la végétation détaillée · base `piste/vegetation-planetaire-base`

**Demande :** remplacer les arbres actuels pour juger les performances et l'approche en vol ; aucun test préalable demandé par l'utilisateur.

**Le changement :**
- Les instances du peuplement alimentent directement des files GPU de conifères et de feuillus.
- Maillage détaillé de près, volume 64³ au loin ; fondu complémentaire entre 384 et 512 pixels.
- Sortie entre 5 et 8 pixels et fenêtre de 512 tuiles ; même règle pour retirer les plantes de la canopée.
- Le terrain, le climat, les graines et les hauteurs restent communs au placement actuel.
- Les arbustes restent sur leur rendu précédent.
- La palette de douze vues couvre quatre lieux ; lancement direct en forêt tempérée par `tools/lance_planet_foliage.ps1`.

**Vérification :** compilation uniquement ; aucun banc ni capture avant le jugement de l'utilisateur.
- Les mesures de la parcelle isolée ci-dessous ne valident pas ce raccord.
- La conservation du couvert, les bases des proxies et le coût des forêts denses restent à observer.
- Le titre indique les comptes et les dépassements des files de rendu.

**Détail :** `vegetation-planetaire.md`. Sans `MYPLANETENGINE_PLANET_FOLIAGE`, retour à la végétation habituelle. Travail non commité.

## 2026-10-27 · Prototype de végétation détaillée · base `piste/vegetation-foliage-base`

**But :** comparer les modèles détaillés, les imposteurs multivues et les volumes hiérarchiques avant le raccord à la végétation de la planète.

**La piste :**
- Travail non commité sur sa branche, intégré depuis au `jalon/24-vegetation-detaillee-main` ; le tag garde sa base.
- Jacaranda et jeune sapin Poly Haven CC0 ; 3 863 832 et 157 402 triangles importés.
- Même arbre normalisé à 12 m, même ancre, même caméra, même lumière dans les trois modes.
- Volumes de 32³ à 128³ ; 64³ par défaut ; transmission filtrée pour conserver le couvert.
- Pied sur le vrai triangle dessiné, par intersection radiale en double précision ; le terrain ne change pas.
- Activation par `MYPLANETENGINE_FOLIAGE` ; absent, le rendu habituel reste inchangé.

**Ce qu'on retient :**
- Le volume 64³ améliore le masque sur les six vues finales ; il coûte davantage que l'imposteur.
- Pour 1 024 instances demandées, le dessin du jacaranda coûte 0,980 ms de médiane en volume 64³, contre 0,373 ms en imposteur, sur RTX 4070 Ti.
- Le 128³ rapproche le couvert de la référence, avec huit fois plus de mémoire et un gain de forme modéré.
- De près, seul le modèle détaillé garde les feuilles individuelles ; le sapin source peut aussi être moins coûteux que ses proxies.
- Les normales moyennées et la visibilité restent insuffisantes pour la lumière ; ombres et vent sont absents.
- La parcelle de comparaison ne remplace pas encore le peuplement planétaire ni son relais de distance.

**Vérification :**
- Compilation C++ et HLSL ; captures sans fenêtre, modes mesurés successivement.
- Comparaison finale de six vues à deux résolutions, plus les essais de charge.
- Douze cas de placement sur deux lieux ; résidu au plan inférieur à 0,032 mm pour les pieds trouvés ; un cas proche de 1 024 demandes n'en trouve que 971.
- Exploration sur deux lieux et plusieurs lumières ; les essais invalides sont consignés dans le log.
- Le rendu habituel garde ses mesures sur 24 lieux et ses 2 990 extraits identiques pixel par pixel.
- Les dépassements de la référence historique existent déjà avant ce travail ; aucun p95 supplémentaire ne se dégrade.
- Les palettes de `tools/tests/2026-10-26-vegetation-prototype*.txt` permettent le jugement en vol, via `tools/lance_foliage.ps1`.

**Détail et mesures :** `log/prototype-vegetation-volumique.md` ; `tools/foliage/results/2026-10-26/`.

## 2026-10-27 · Les spikes rivières, mis de côté · tag `piste/rivieres-spikes`

**Hors de `main` :** l'ancienne branche `codex/rivieres-spikes`, partie de la maquette Dendry, tag `jalon/avant-spikes-rivieres`. Doc complète, état final, essais remplacés et journal des spikes : `log/recherche-rivieres-historique.md`.

- **Essayé les 26 et 27 octobre :** la maquette Dendry en tronçons continus, écartée en vol ; un relief construit avec ses rivières, dans un visualiseur ; le Phasor de Grenier et al. sur un bassin ; un bruit de bassin aux cours descendants par construction, rendu dans le moteur ; trois bassins côtiers ; un réseau global en cellules sur complexplanet, puis dans le moteur.
- **Le résultat,** tag `jalon/rivieres-cp-resultat-prometteur` : l'incision ne relève jamais complexplanet ; les profils descendent, bornés par le terrain ; méandres et largeurs variables jusqu'à l'embouchure. Jugé prometteur, sur une seule graine.
- **Restait :** une organisation des branches encore géométrique, pas de delta, la stabilité en mouvement, les autres graines, le coût.
- **La suite :** la branche `erosion-niveaux`.

## 2026-10-26 · Mer FFT dans main · jalon/23-mer-fft-main

- **Demande :** rebase, fusion et lancement depuis main.
- **Base :** main 083bfb1 ; végétation v3, objets de proximité, carte planétaire et ombre unique conservés.
- **Raccord GPU :** carte en t10, mer en t11 à t16 ; horodatages de mer 6 et 7, distincts des objets.
- **Diagnostics :** identifiants 1 à 26 de main conservés ; les cinq vues de mer ajoutées de 27 à 31.
- **Atmosphère :** appel de la lumière de l'eau sur la tranche de brume à sol régional nul ; ombre unique de main conservée.
- **Qualité :** six lieux appariés, un par matériau, cinq hauteurs ; 753 crops strictement identiques au témoin de main, aucun nouveau p95 dégradé. Référence inchangée ; ses dépassements préexistants sont consignés dans le log.
- **Tempête :** simulation 0,13 ms GPU ; rendu 1,22 ms, minimum 1,20 ms ; placement d'objets 0,23 ms, aucun objet sur l'eau ; 1280 × 720, après 600 images.
- **En vol :** tools/tests/2026-10-26-mer-main.txt, mer, deux forêts, orbite et pôles ; tools/lance.ps1.

## 2026-10-26 · Océan FFT validé · jalon/22-mer-fft

**État :** aspect validé en vol par l'utilisateur. Base 47c404b sous piste/mer-fft-spike.

- **Demande :** noyau visuel neuf après le rejet des filets d'écume et des bandes translucides.
- **Réglages :** quatre FFT 256², tailles 1 103 / 113,1 / 11,57 / 1,183 m ; choppiness 1,25 amortie sous 40 cm ; fetch 90 km, JONSWAP 3,3 ; houle explicite.
- **Écume :** deux cartes 512² de 128 / 1 024 m ; seuil de Jacobien 0,68, gain 2 ; dissipation 0,22/s, fraîcheur 1,6/s ; pores multiéchelles.
- **Coordonnées :** plan transporté, origines modulo en double, indices de cartes entiers.
- **Caméra :** surface déformée et garde de 75 cm ; ancien sol en cache et lecture GPU de l'ancienne position invalidés au changement de lieu.
- **Coût :** simulation et écume 0,13 ms GPU ; rendu 1,12–1,27 ms en pleine mer, minimum 3,35 ms sur la côte signalée ; 1280 × 720, Debug x64, shaders optimisés.
- **Qualité :** 30 lieux appariés, 3 891 crops, trois pixels changés d'un niveau ; aucun nouveau p95 dégradé. Six dépassements de la référence existaient déjà, inchangés.
- **Vérifications :** mer fraîche, tempête, côte signalée, ras de l'eau et deux pôles ; terrain stable, variation de la mer figée encore présente.
- **Reflet :** écart moyen Cox-Munk de 2,8 % à 12 m/s et 6,2 % à 24 m/s ; cible 5 % manquée en vent fort. Mesures dans log/spec-mer-fft-spike-historique.md.
- **Limites :** vent contrôlé, côte et raccord planétaire simplifiés ; spec-mer-fft-spike.md.
- **Comparaison :** ancien rendu conservé dans mer-animee ; ce jalon porte le noyau FFT validé.
- **Source :** Noniv/web-ocean, MIT ; licence conservée dans third_party/web-ocean.

## 2026-10-25 · La végétation v3 : les arbres ne poussent plus · tag `piste/vegetation-v3`

**Réglages nouveaux :** `CANOPY_SIDE_LIGHT` ; `FOREST_RAIN.z`, 1 000 mm ; `SHRUB_LAND` 50 %, `SHRUB_COVER` 35 et 25 % ; `SHRUB_ALBEDO` gris-vert. Détail et mesures : `recherche-vegetation.md`, section « v3 ».

- **Demande :** dans les vues comme F3, les arbres semblent pousser à mesure que la caméra avance ; un peu moins d'arbustes.
- **La cause :** un arbre grandissait avec son fondu, de 14 à 21 pixels ; au-delà, la canopée était plate, une hauteur d'arbre sous les cimes.
- **Fait :**
  - **un arbre entier ou absent,** à son propre seuil du fondu ; la forme grossière couvre l'écran comme la fine ;
  - **la canopée à la hauteur de ses arbres :** le rayon de vue traverse les couronnes des plantes non dessinées avant le sol ; les lisières se dressent, les cimes ont leur parallaxe, la perspective aérienne leur distance ; leur lumière vue de biais, mesurée sur les plantes dessinées ;
  - **les arbustes,** un cinquième de moins ; les buissons du désert, des dômes bas gris-vert ;
  - **pas d'état de forêt sous 1 000 mm** (Staver) : plus de taches sombres sur les déserts vus d'orbite.
- **Essayé, pas gardé :** les couronnes de chaque arbre lancées dans le pixel, 10 ms de plus à F3.
- **Mesures :**
  - **le vol,** banc `mouvement` : la hauteur vue de la forêt au-delà des arbres dessinés, 26 à 37 m jusqu'à 3 km, contre 0 à 4 m en v2 au-delà de 2 km ; par bande de sol, 1,92 m d'une image à la suivante contre 2,58 à 150 m ;
  - **le relais de lumière** à F3, de 1 à 3 km : les arbres dessinés 5 à 12 % plus sombres que la canopée, contre 13 à 20 % ;
  - **pas de pop en descente,** aucune plante ne flotte, le tremblement inchangé ;
  - **le coût :** le rendu du sol 1 ms de plus, le placement inchangé.
- **Questions en suspens, posées à l'utilisateur :** réchauffer le climat des latitudes moyennes ; retirer la part de forêt de la palette des biomes.
- **Images :** `journal/2026-10-25-vegetation-v3-avant-apres-1.jpg` et `-2.jpg`, v2 à gauche, v3 à droite ; `-v3-vol-150m.jpg`, 1 km de vol image par image ; `-v3-tests.jpg`.
- **Pour revenir :** le tag `piste/vegetation-v2`.
- **Verdict, le 2026-10-25 :** validée, fusionnée en `jalon/21-vegetation`. À reprendre plus tard : l'apparition des arbres reste trop brutale.

## 2026-10-25 · La végétation v2 : où il n'y a pas d'arbres · tag `piste/vegetation-v2`

**Réglages nouveaux :** `PRESENCE_SCALES`, `SHRUB_LAND`, `FOREST_EDGE`, `SHRUB_LINE_OFFSET`, `EXPOSURE_RELIEF`, `EXPOSED_SEASON`, `EXPOSED_DRIVE`, `TREELESS_RAIN`, `FOREST_RAIN`, `PLANT_LOD_PIXELS` ; `PLANT_PIXELS` de 24 à 14 pixels. Détail et mesures : `recherche-vegetation.md`, section « v2 ».

- **Demande :** des règles de répartition avec du bruit, comme pour les cailloux, des endroits sans arbres quel que soit le sol ; plus d'arbustes, par taches ; pas d'arbres sur les crêtes ; des arbres un peu plus complexes, qui sortent plus tôt.
- **Fait :**
  - **où sont les bois :** deux champs de bruit, une seule règle ; les régions, 32 km à 8 m, laissent des terres entières sans arbres ; les taches, 1 km à 8 m, ouvrent des clairières de 30 m à 1 km dans toute forêt ;
  - **les arbustes :** un champ de taches à eux, sur 60 % des terres ; 40 % du sol dans les clairières humides, 30 % en sous-bois ; un manteau sur les lisières ; le krummholz au-dessus de la ligne des arbres ;
  - **les crêtes :** la hauteur du sol sur le sol régional de la carte de la planète, à 16 km ; les crêtes perdent leurs arbres, les creux les gardent ;
  - **les formes :** huit variantes par espèce, verticilles étagés, feuillus sur plusieurs troncs, couronnes penchées ;
  - **sortir plus tôt :** à 14 pixels au lieu de 24, une forme grossière de 156 sommets sous 48 pixels, sans trame ; au loin, le pied sur le sol dessiné.
- **Mesures :**
  - **les crêtes,** au-dessus de 300 m sur le sol régional : 0 à 2 % de sol sous les arbres, contre 11 à 83 % en v1 ; les creux, 14 à 80 % ;
  - **la couverture des arbres :** 7 à 9 points de moins dans les biomes forestiers, 43 à 50 % ; plus d'arbustes ;
  - **pas de pop :** la part de forêt par pixel à ±1 point de 2 km à 200 m, ±1,5 en savane ;
  - **aucune plante ne flotte** d'un demi-pixel sur les seize vues de test ;
  - **le tremblement,** sans lissage, monte de 0,01 à 0,03 jusqu'à 0,05 à 0,10, le niveau du sol nu d'avant ; avec, 0,02 au plus ;
  - **le coût des plantes :** 0,6 à 1,6 ms au repos, contre 0,4 à 1,2, pour trois fois plus de surface ; le premier jet coûtait 2,5 à 4 ms ;
  - **le raccord de lumière :** 0,98 à 1,14, sauf la forêt boréale de biais, 0,48 : ses cônes cachent la neige des clairières.
- **Questions en suspens, posées à l'utilisateur :** réchauffer le climat des latitudes moyennes ; retirer la part de forêt de la palette des biomes.
- **Images :** `journal/2026-10-25-vegetation-v2-avant-apres-1.jpg` et `-2.jpg`, v1 à gauche, v2 à droite ; `-v2-tests.jpg`, les vues de `tools/tests/2026-10-25-vegetation-v2.txt`.
- **Pour revenir :** le tag `piste/vegetation` retrouve la v1.

## 2026-10-25 · La végétation, étape 1

**Réglages nouveaux :** le bloc « Vegetation » de `PlanetSettings.hlsli`, tableau ci-dessus. Tag `piste/vegetation`. Recherche, détail et mesures : `recherche-vegetation.md`.

- **Demande :** des arbres de plusieurs types selon l'altitude et le terrain, des arbustes, des forêts ; l'état de l'art d'abord.
- **L'architecture :** une seule population, `Vegetation.hlsli`, deux représentations.
  - **Près :** une classe d'objets de plus sur la grille de la planète ; trois espèces générées au démarrage, conifère, feuillu, arbuste, quatre variantes chacune ; elles sortent du sol de 24 à 36 pixels de haut.
  - **Loin :** la canopée dans la matière du sol, sa part dessinée retirée en couche booléenne ; sa couleur, celle de l'Amazonie, plus sombre pour les conifères ; le relief de ses couronnes ; son ombre au sol, aux cailloux et aux touffes.
- **Où pousse quoi :** la saison de croissance pour le froid, Körner ; l'aridité de Holdridge, le plafond de Sankaran, les modes de Hirota, la bistabilité de Staver pour l'eau ; des peuplements par un champ de bruit ; les hauteurs par la saison et l'eau ; Tallo pour les couronnes.
- **Mesures :**
  - **pas de pop :** la part de forêt par pixel, de 20 km à 50 m, à ±1,5 point près sur trois lieux ; avant le raccord booléen, elle perdait 8 points où les arbres naissent ;
  - **la couverture par biome :** arbres 52 à 58 % dans les biomes forestiers, 15 % en savane et dans les terres sèches, 3 % au désert, comme les modes publiés ;
  - **la ligne des arbres :** les arbres tombent à moitié pour une saison de 5,3 à 6,3 °C, Körner donne 6,4 ± 0,7 ; 4 320 m à l'équateur, la Terre 3 100 à 3 900 ; aux latitudes moyennes, 1,5 à 2,5 km sous celle de la Terre : le climat de la planète y est plus froid ;
  - **le raccord de lumière** entre plantes et canopée : 0,99 à 1,07 pour les feuillus, la savane et le maquis ; 0,70 à 0,89 pour la forêt boréale sur la neige ;
  - **aucune plante ne flotte** d'un demi-pixel sur les quatorze vues de test ;
  - **le tremblement** ne monte nulle part ;
  - **le coût :** sous la charge des autres instances, le placement passe de 0 à 9 % du calcul du terrain à 24 à 47 % dans les forêts, 0,1 à 2 ms rapporté au repos ; le dessin, 0,1 à 0,2 ms au repos.
  - **le banc de qualité,** 12 lieux : l'herbe gagne +4 à +10 dB de détail fin de 50 m à 3 km ; à 12 m, les troncs droits, la répétition des quatre variantes et les masses lisses des arbustes dégradent segments, répétition, trou et détail fin au-delà des 10 % ; la mutation p95, +16 à +45 % de 200 m à 3 km. À traiter avant toute fusion : les formes.
- **Correctif en chemin :** la vue de diagnostic `objects` dessinait les objets dans la vue `sun` ; `ObjectsView` de 12 à 13.
- **Images :** `journal/2026-10-25-vegetation.jpg`, les vues de `tools/tests/2026-10-25-vegetation.txt` ; `-descente.jpg` ; `-raccord.jpg`.
- **Pour revenir :** `MYPLANETENGINE_NO_PLANTS` retire les objets, la canopée au sol partout ; le tag `jalon/19-detail-sol` retrouve l'état d'avant.

## 2026-10-25 · Objets de proximité : où il y a des cailloux, et lesquels · tag `piste/objets-proximite`

**Réglages :** `OBJECT_STONY` nouveau ; `OBJECT_OCTAVES` dès 3 cm ; `PEBBLES` 2 %, effacé au-delà de 8 cm ; `GRASS_ROCKS` 0,03. Spec : `spec-objets-proximite.md`, étape 3.

- **L'avis en vol :** trop de cailloux partout, un peu trop gros ; du gravier couramment, les plus gros moins ; de grandes prairies et de grands sables sans rien.
- **Avant,** la présence venait des seules parts des sols et des taches de 8 à 64 m : tout sable portait des cailloux.
- **Changements :**
  - un champ de pierrosité propre aux débris, de 0,5 à 32 km, relevé par les éboulis, le sol nu sec et la pente, seuillé par la règle des limites ;
  - le gravier sous 3 cm laissé à la texture du sol ; des cailloux cinq fois moins nombreux à chaque octave au-dessus de 3 cm ;
  - les rochers de l'herbe au bas des sites mesurés.
- **Mesures :**
  - sans débris : 74 % des prairies, 70 % des sables et sols nus, 11 % des éboulis, 68 % de tout le sol, sur 67 lieux tirés au hasard ;
  - sable caillouteux, par m² de 3 à 50 cm : 5,2, 1,0, 0,14, 0,008, le bas de la photo, 16, 6, 0,5 ;
  - tout le sol de 0 à 10° : 2,2 objets par m² au lieu de 71 ;
  - aucun objet flottant ; arrivées à 0,06 px au plus ; tremblement jamais plus que sans objets ;
  - placement 6 à 19 % du calcul du terrain sous charge, contre 14 à 28 %.
- **Tests en vol, remplacés :** sable caillouteux, sable sans débris près de la côte, herbe et rochers, prairie sèche sans débris, sol nu caillouteux, pente d'éboulis.
- Image : `journal/2026-10-25-objets-pierrosite.jpg`, les photos à gauche.

## 2026-10-25 · Une seule ombre du relief · tag `piste/ombre-unique`

**Réglages :** `HORIZON_STEP` 0,05 → 0,02 ; la hauteur d'ombre de l'air vient de la marche de l'horizon, la grille polaire de 512 × 512 et ses passes `SunShadowTerrain.hlsl`, `SunShadow.hlsl` sont retirées.

- **Pourquoi :** deux sources pour une ombre. Les ombres portées marchaient vers le soleil à chaque sommet, sur les hauteurs de l'image ; les rayons recalculaient le relief sur leur grille et marchaient à nouveau.
- **Changements** (`recherche-rayons.md`, partie 4) :
  - la marche de l'horizon garde aussi, de chaque point marché, sa hauteur au-dessus du rayon du soleil tiré du sommet ; la plus grande donne la hauteur d'ombre de la colonne, `FaceVertex.shadow` ;
  - elle s'arrête quand rien ne peut plus dépasser l'horizon, ni passer au-dessus du rayon tiré de la hauteur d'ombre : un sommet au soleil marche comme avant ;
  - l'atmosphère lit la hauteur d'ombre entre les quatre sommets autour du point, `MeshCell`, la même recherche que la hauteur du maillage ; `ShadowRay` perd son champ `grid` ;
  - la couverture tient : le maillage garde toute colonne visible de la mer à 10 km, et tout relief dont l'ombre peut l'atteindre (`ShadowSweep`).
- **Mesures,** contre `jalon/18-lumiere`, `images/ombre-unique-avant-apres.jpg` : avant, après, différence amplifiée 8 fois.
  - Rayons, onze vues : écart moyen de 0,00 à 0,88 niveau sur 255, 99,9e centile 19 au plus, sauf « pic, soleil de côté », 45. L'air est un peu plus sombre au ras des crêtes : une grille de 1 024 × 1 024 s'écarte deux fois moins de la nouvelle ombre que de l'ancienne, 0,33 contre 0,64 sur six vues. La grille de 512 abaissait les crêtes.
  - Ombres portées, huit vues : écart moyen de 0,03 à 0,74 ; quelques bords d'ombre gagnent un à trois pixels, ce que la marche à 5 % manquait ; 99,9e centile 67 au plus, « plans successifs ».
  - Tremblement avec / sans lissage, `banc_tremblement.py` : pic à 14°, 0,10 / 0,66 → 0,10 / 0,66 ; vallées à 9°, 0,07 / 0,43 → 0,06 / 0,40 ; aiguille à 11°, 0,07 / 0,45 → 0,06 / 0,45 ; massif à 8 km, 0,18 / 1,14 → 0,18 / 1,12 ; pyramide, 0,14 / 0,71 → 0,13 / 0,71.
  - Coût, paires de captures successives sur le GPU partagé : calcul −0,7 à −1,3 ms sur les quatre vues de rayons mesurées au calme, rendu inchangé à 0,1 ms près ; au pas de 5 %, −0,7 à −1,0 ms sur les dix-neuf vues. Soleil dans le dos, le pire cas de la marche, mesuré seulement avec quatre autres instances sur le GPU : −0,4 à −1,2 ms en médiane, à confirmer.
  - Code : 248 lignes retirées, 110 ajoutées, en HLSL et C++ ; trois fichiers de moins.
- **Essayé, pas gardé :** le pas de 5 %. Ombres du sol inchangées, 1 ms de moins, mais l'air tremblait davantage au pic à 14°, 0,12 / 0,69. La hauteur d'ombre compte une hauteur manquée entre deux pas entière, l'horizon seulement sur sa distance. 3 % : 0,10 / 0,67.
- **Pour les nuages, tag `piste/nuages` :** `IntegrateScattering` et `ShadowRay` gardent leur forme ; `ShadowRay` perd seulement `grid`, et `ShadowGridScale` disparaît : `AtmospherePass.hlsl` ne remplit plus ce champ. Le registre `t9` de l'atmosphère porte le maillage, `StructuredBuffer<FaceVertex>` ; `Clouds.hlsli` y déclare `cloudWeatherZ`, un conflit déjà présent depuis `jalon/18-lumiere`.
- **Reste :** la pénombre du soleil dans l'air ; des pas plus serrés près de la caméra sur les rayons du ciel.
- **Retour arrière :** le tag `jalon/18-lumiere`.

## 2026-10-25 · La carte de la planète : la brume suit le sol · tag `piste/carte-planete`

**Réglages :** `HAZE_GROUND_SCALE_KM` = 10, nouveau. La carte de la planète, nouvelle (`PlanetMap.hlsli`, `PlanetMap.hlsl`, `PlanetMap.cpp`). Tables de l'atmosphère à 25 tranches de sol. Vues `ground`, `haze`, `lakes`, `rivers` ; banc `tools/banc_carte.py`.

- **Pourquoi une carte :** deux besoins, une seule source.
  - La brume suivait le niveau de la mer : un haut plateau restait dans l'air pur (la brume de la couche limite, plus bas).
  - Aucun calcul par point ne trouve le niveau d'un lac ni le chemin vers la mer (`recherche-rivieres.md`).
- **La carte :**
  - complexplanet tel quel, la fonction du maillage, au centre de chaque texel d'un cube fixé sur la planète ; octaves filtrées à deux texels, comme le maillage à deux mailles ;
  - 1 024² par face, la maille du plan des rivières : 9,8 km au centre d'une face, 4,6 km aux coins ;
  - de la donnée, pas de la géométrie : aucun sommet ne bouge (`geometrie.md`) ;
  - par texel : le sol, max(e, 0) ; l'eau des cuvettes remplies ; l'aire drainée ; des mips par moyennes 2 × 2.
- **Le coût au démarrage, mesuré :**
  - calcul sur GPU, lecture comprise, 14 à 125 ms selon la charge du GPU ; drainage sur CPU, 0,6 à 0,8 s ; mips et demi-flottants, 0,15 s ; envoi, 0,03 à 0,1 s. Moins d'une seconde en tout ;
  - 64 Mo sur le GPU, RGBA en demi-flottants avec mips ; au démarrage, 0,3 Go de mémoire vive et 0,1 Go sur le GPU, rendus aussitôt ;
  - le drainage est compilé optimisé même en Debug. Avec le tas et l'accès vérifié de la STL, il prenait 2,4 s.
- **Vérifiée** (`tools/banc_carte.py`) :
  - altitude contre le portage numpy de complexplanet, 600 mailles : écart médian 7 cm, 9,5 m au plus ;
  - surface remplie identique, maille pour maille, à un Priority-Flood simple écrit à part ;
  - chaque maille s'écoule vers une voisine sans monter, jusqu'à la mer, qui reçoit 100 % des terres.

**La brume suit le sol régional :**
- **La règle physique :** la couche limite suit le relief à grande échelle et se nivelle au-dessus des reliefs étroits. Un plateau bien plus large que la couche est épaisse fait sa propre couche ; une crête ou une vallée de quelques fois cette épaisseur, non (De Wekker et Kossmann 2015).
- **Le choix :** le sol de la carte lissé sur 10 km d'écart type, le mip de 20 km lu linéairement, à la même échelle sur tout le cube.
  - Un plateau de 100 km garde 82 % de sa hauteur ; des crêtes espacées de 20 km, moins de 1 %.
  - La brume s'amincit sur les sommets et remplit les vallées.
- **Le long du rayon de vue :** chaque pas lit le sol régional à ses deux bouts et en son milieu. La moyenne exacte de la brume sur le pas suit sa hauteur au-dessus de ce sol.
- **Les tables du démarrage, la solution juste la plus simple :** une troisième dimension, le sol de la brume.
  - 25 tranches de 0 à 6 km ; le sol régional le plus haut fait 5,2 km. Chaque tranche est l'air d'un sol uniforme.
  - Le pixel et chaque pas les lisent au sol régional de leur point ; le reste de l'air garde l'altitude au-dessus de la mer.
  - Interpolation entre tranches : 0,06 % de la transmission au soleil zénithal, 0,5 % au soleil à 6°, au pire, au sommet de la couche.
  - L'exposition garde sa carte grise au niveau de la mer, dans la brume de la mer : inchangée.
- **Mesures,** avant → après :
  - le sol lointain sur le ciel d'horizon, à 5 km d'altitude : 2,47 → 1,62 et 4,17 → 2,00 ; en plaine, 1,00 avant comme après. Le ciel d'horizon du plateau austral s'éclaircit : 0,18 → 0,31 ;
  - descente au-dessus du plateau, de 1 500 km à 30 m : contre l'ancienne brume, au plus 0,05 IL d'une hauteur à la suivante. Vu d'en haut, −0,07 IL : la brume voile la neige ;
  - tremblement avec/sans lissage : plateau austral 0,14 / 0,71 → 0,11 / 0,57 ; plateau du nord 0,04 / 0,22 → 0,02 / 0,14 ; montagnes 0,19 / 1,37 → 0,17 / 1,25 ;
  - coût du rendu inchangé au bruit près, le GPU partagé : minimum sur 8 captures, 4,47 → 4,30 ms au sol du plateau, 2,20 → 2,31 ms en avion. Deux lectures de la carte par pas du rayon, des tables en trois dimensions ; +3,5 Mo de tables ;
  - plaines, mer, côte et orbite inchangées, écart moyen de 0,5 à 3 / 255 ; montagnes, 8 à 15 / 255 ; plateaux, 15 à 18 / 255. Banc de qualité, 12 lieux, contre l'avant : mutation p95 en baisse, 0,140 → 0,108 à 200 m, 0,085 → 0,060 à 800 m ; un seul p95 au-delà de 10 %, le trou de la neige à 200 m, 1,0 → 1,2 dB, la brume voilant désormais la neige d'altitude ; les photos en ont 3,5.
- **À juger en vol :** `tools/tests/2026-10-25-carte.txt`, plateaux et montagnes ; `tools/tests/2026-10-24-profondeur.txt`, plaines, côte et orbite, inchangées. Avant et après, `journal/2026-10-25-carte.jpg`.

**L'hydrologie, étape 1 du plan des rivières :**
- **Un Priority-Flood depuis la mer** (Barnes 2014) : le niveau de chaque cuvette, le sens de l'écoulement, l'aire drainée. Sur CPU : plus simple, et assez rapide.
- **Les lacs, chaque cuvette remplie :** 43 % des terres, 231 m de fond en médiane ; le banc 0 en trouvait 41 % à 55 km. 20 359 lacs.
  - Trois cuvettes de 58, 28 et 10 millions de km² : les intérieurs des continents, plus bas que leurs bords.
  - 95 % des terres se jettent dans une cuvette ; sur Terre, les bassins sans issue font 20 % (Wang 2018).
  - Tailles : N(>A) ∝ A^−0,99 au-dessus de 1 000 km² ; HydroLAKES, A^−1,14 (Cael et Seekell 2016).
- **Le réseau :**
  - densité de drainage au-delà de 1 000 km² drainés : 0,056 km/km² ; sur Terre, environ 0,037, HydroRIVERS prolongé par l'exposant terrestre ;
  - P(A > a) ∝ a^−0,63, contre a^−0,43 sur Terre ; loi de Hack, exposant 0,36, contre 0,5 à 0,6 ;
  - trop peu ramifié : il traverse les grandes cuvettes en lignes droites, du seuil vers l'amont. Une rivière dans un lac n'en est pas une : la vue `rivers` les masque.
- **Ce que ça tranche :** les mers intérieures. Sans bilan d'eau, 43 % des terres seraient sous l'eau. Le bilan d'eau vient avant tout lac dessiné.

**Reste, pour dessiner lacs et rivières :**
- le bilan d'eau, Fill-Spill-Merge, du ruissellement de notre climat : la part réelle des lacs, et le choix pour les mers intérieures ;
- un identifiant et un niveau par lac dans la carte ; l'eau plate au niveau du lac, avec le modèle d'eau de la mer de la branche `mer-animee` ; la côte généralisée par `SpreadStep` ;
- les rivières : le réseau hors des lacs, lissé et méandré, largeur 7,2 Q^0,5, un ruban en part du pixel ; puis les tuiles fines près de la caméra.

**Pour revenir :** `RegionalGround` qui rend 0 ramène la brume au niveau de la mer, tables comprises ; la carte reste, inutilisée.
**Réglages nouveaux :** le bloc « Vegetation » de `PlanetSettings.hlsli`, tableau ci-dessus. Tag `piste/vegetation`. Recherche, détail et mesures : `recherche-vegetation.md`.
## 2026-10-25 · La mer animée : reflet du soleil et du ciel, moutons, vagues · tag `piste/mer-animee`

**Réglages :** `WAVE_LONGEST` = 512 m, `SLOPE_OCTAVES` = 16, `FOAM_ALBEDO` = 0,22, nouveaux ; 14 octaves de 12 ondes (`Planet.hlsli`, `D3DApp.h`). Nouveau fichier `Sea.hlsli` ; vues `foam` et `glint` ; `MYPLANETENGINE_TIME`. Détail : `recherche-mer.md`, section 8.

- **Demande :** « Mer : reflet du soleil et du ciel, moutons. Mais animé, pas statique. »
- **Avant :** une mer plate et diffuse, bleue selon la profondeur sur 3 000 m ; ni reflet, ni écume, ni mouvement.
- **Changements :**
  - **le vent,** une carte sur le climat : circulation par latitude, temps de 3 000 à 300 km, rafales de 100 à 5 km ;
  - **la pente de la mer a la variance de Cox et Munk à toute distance :** 168 ondes dessinées dans le pixel, chacune sa moyenne sur lui ; le reste élargit le reflet ;
  - **un seul reflet de l'eau, `ReflectOnWater` :** le soleil par Cox-Munk et masquage de Smith, le ciel marché depuis l'eau, le Fresnel moyen de Bruneton ;
  - **les vagues bougent :** dispersion en eau profonde, sous le vent du pixel ; leur plan est porté par la caméra, leurs phases tenues en double sur le CPU ;
  - **les moutons :** la part de Monahan de loin ; de près, nés sur les crêtes des groupes de vagues, ils les suivent et s'effacent, à la même moyenne ;
  - **l'eau :** un type par latitude et plateau, le fond vu en eau peu profonde ; plus de dégradé sur 3 000 m ;
  - **le lissage temporel** saute les pixels de mer qui montrent des vagues : il étalait leur mouvement, 30 % de contraste perdu à 20 m ;
  - **la barre de titre** donne aussi l'image la plus rapide : le GPU est partagé, les autres programmes allongent la moyenne.
- **Mesures :**
  - **le reflet d'orbite contre Cox-Munk,** pixel par pixel : à 1 % près au centre de 2,6 à 14,6 m/s, 2 % à 20 m/s ; écart moyen 1,1 à 3,6 % (`images/mer-reflet-cox-munk.png`) ;
  - **en descente,** de 1 500 km à 10 m, trois sites de 6,7 à 26,6 m/s : le reflet moyen à 2 % de Cox-Munk jusqu'à 200 m, −8 à +11 % plus bas où la vue ne voit qu'un groupe de vagues ; les moutons à 1 % de Monahan jusqu'à 3 km, ±8 % de près, 20 % dessous à 6,7 m/s ;
  - **scintillement,** maillage qui glisse : hors de la mer, inchangé quand elle bouge, 0,02 / 0,08 à la côte ; la mer, 0,05 figée ; son mouvement garde tout son contraste, contre 70 % avec le lissage d'avant ;
  - **coût,** image la plus rapide : +0,4 ms d'orbite, +1,5 à 2 ms près de l'eau en plein écran, 1280 × 720, RTX 4070 Ti ;
  - **la terre est inchangée,** au pixel près.
- **Choix :** une somme d'ondes au pixel plutôt qu'une FFT. Ni ressource ni passe nouvelle, un filtrage exact par onde, le vent local sur chaque amplitude. 6 ondes par octave dessinaient un treillis ; s'effacer sur une octave seulement, aussi.
- **Fusion avec `plages` :** essai fait et compilé, tag `piste/essai-fusion-mer-plages` ; `WaterSheen` remplacé par `ReflectOnWater` (`recherche-mer.md`, section 8).
- **Vues en vol :** `tools/tests/2026-10-25-mer.txt` ; planche `images/mer-tests.jpg`.
- **Reste :** les vagues en géométrie près de la caméra, le déferlement à la côte, une FFT pour le coût de près, la houle, le fetch, les lacs.
- **Pour revenir :** le commit `044bcf2`.
## 2026-10-27 · Ombres des nuages et première météo sur la sphère entière

- **Retour utilisateur :** rendu jugé plutôt bon ; ajouter des ombres sur terre et mer, puis essayer une répartition planétaire issue des références.
- **Témoin :** Orbit accepté figé dans `x64/NuageFrostbiteOrbitTemoin/`,44 fichiers vérifiés, dont les sources copiées ; base Git `6cd34e7`, tag `piste/nuages-orbite-spike`.
- **Ombres :** parcours des deux coquilles depuis la surface vers le soleil ; même densité et temps ; extinction80/km ; pas minimum250 m et au plus256 intervalles par segment. Seul le direct solaire `t17` est atténué avant l'air.
- **Répartition :** carte globale1024×512, champs Perlin3D sur la sphère, fronts irréguliers, nappes et régions convectives ; tendances de latitude douces. R>0,03 sur55,93% de l'aire de la carte ; B>0,03 sur1,59%, sans équivalence avec la couverture rendue.
- **Conservation :** trois textures3D copiées exactement d'Orbit ; pas et filtrage de vue hérités. La variante régionale et l'option sans ombres permettent des comparaisons séparées.
- **Contrôles courts :** rendu de deux hémisphères, région dense à800 km, ombres sur terre et mer, comparaisons avec/sans et diagnostic de transmittance. La comparaison terrestre change32,1% des pixels de plus de2/255 ; l'effet maritime à80 km reste discret. Aucune validation en mouvement ni banc prolongé.
- **Coût ponctuel :** nuages+air19,46 et18,76 ms sur les deux globes ;28,09 ms sur la région dense à800 km ;10,36 contre8,98 ms sur le point terrestre à30 km avec/sans ombres. GPU partagé ; ces captures ne valident pas un budget.
- **Limites :** météo artistique sans géographie, carte mip1 proche de78 km à l'équateur, fibres de cirrus dans le repère fixe du site initial ; coût et filtrage des ombres encore approximatifs.
- **Essayer :** `tools/nuages-planete.ps1`, palette `tools/tests/2026-10-27-nuages-planete.txt` ; détail et références dans `spike-nuages-planete.md`.
- **Publication sur demande :** tag `piste/nuages-planete-spike` ; sources, assets et outils inclus, sorties `x64/` locales et ignorées. PR en brouillon contre `main` ;12 conflits signalés par la simulation de fusion avec `f66ead9`.

## 2026-10-27 · Cirrus plus rares et première quadrature orbitale

- **Retour utilisateur :** les nuages bas régionaux sont corrects ; trop de cirrus régulièrement alignés. Passage demandé à la très haute altitude et à l'orbite.
- **Témoin :** version Régional figée dans `x64/NuageFrostbiteRegionalTemoin/`, quarante fichiers et sources avec empreintes.
- **Cirrus :** météoB groupée à24/42/70 km, moyenne26,8% de Régional ; nouveau champ de filaments rares,7,42% du mip0 au-dessus de0,05. FormeR/B/A et météoR/G/A inchangées à tous les mips.
- **Filtrage :** moyenne de la lumière prémultipliée et de la transmittance de quatre ou neuf rayons distants, avec mélange continu au rayon hérité ; empreinte0,25–0,8 km et rampes de sécurité hors des couches/rayons rasants.
- **Près :** recette de densité basse inchangée ; vue de contrôle proche identique pixel à pixel avec et sans filtrage. Composition atmosphérique une fois après la quadrature.
- **Coût :** à800 km sur une paire de captures à données identiques, nuages+air2,88 ms sans filtre et11,37 ms avec quatre rayons ; premier compromis à juger, sans budget global validé.
- **Contrôle :** quatre variantes compilées, quatre vues et deux comparaisons cachées inspectées ; copies, mips et témoin vérifiés.
- **Livraison :** `tools/nuages-orbite.ps1`, douze vues ; `-Temoin` pour Régional et `-SansFiltrage` pour comparer le filtre avec les mêmes nouveaux cirrus.
- **Limites :** quadrature finie, coût accru et périodicité résiduelle ; validation en vol par l'utilisateur, sans historique temporel.
- **Publication sur demande :** tag `piste/nuages-orbite-spike` ; sources, assets et licences inclus, sorties `x64/` locales et ignorées.

## 2026-10-27 · Formations régionales sur une carte météo étendue

- **Décision :** étendre d'abord la répartition, puis juger le même champ à plusieurs distances ; carte vue de dessus avant remise en main du volume.
- **Témoin :** scène locale des trois familles figée dans `x64/NuageFrostbiteFamiliesTemoin/`, quarante fichiers avec empreintes ; sources et données antérieures conservées.
- **Météo :** carte1024×512 sur1200×800 km, origine0,5°/161,775° ; nappes/fronts fragmentés, deux régions d'amas de cumulus, cirrus associés et grandes éclaircies.
- **Réglages :** variations du masque à15/60/160 km ; R couverture basse, G type, B cirrus ; source et paramètres dans `tools/gen_frostbite_regional_weather.py` et le manifeste régional.
- **Conservation :** les trois textures3D, les profils, la lumière et les pas d'intégration restent ceux de la scène locale ; seules météo, étendue et accélération du vide changent.
- **Parcours :** sphère650 km autour de l'origine fixe ; preuve du vide aux mips7–3, sauts bornés à50 km ; mipsR/B de présence conservateurs.
- **Limite :** carte artistique régionale ; répétition des bruits et transparence lointaine encore à juger, sans nouvelle reconstruction temporelle ni nouveau LOD statistique.
- **Contrôle :** trois variantes compilées ; carte légendée et quatre captures sur deux distances et deux lieux inspectées ; copies3D, densité basse, mips de présence et témoin vérifiés.
- **Constat :** répartition régionale visible ; grain répétitif lointain et stries des cirrus toujours présents. Nuages+air ponctuels2,93–9,24 ms ; calcul terrain coûteux sur deux lieux proches, sans verdict de performance globale.
- **Livraison :** `tools/nuages-region.ps1`, vues Rendu/Meteo/Opacite, douze positions ; validation en vol à l'utilisateur.
- **Git :** aucun commit, tag ni push demandé.

## 2026-10-27 · Trois familles ensemble et correction du masque des cirrus

- **Retour utilisateur :** les ondulations des cirrus sont plutôt bonnes, mais leurs contours communs semblent coupés par un masque ; fibres trop larges par rapport à leur longueur.
- **Scène :** cumulus, nappe et cirrus réunis ; données et recette de densité des deux familles validées conservées exactement.
- **Canaux :** t24R reste la forme Frostbite, t24G porte les fibres ; t27R/G restent la météo basse, t27B porte les cirrus ; mips bas inchangés.
- **Contours :** suppression du seuil de couverture0,03 pour les seuls cirrus ; queues gaussiennes et exponentielles raccordées sur4 km, halo faible, fondus aux extrémités.
- **Fibres :** domaine64×16×8 km, corrélations Est8/6 km et Nord0,28/0,14 km ; léger cisaillement mondial, densité maximale0,018.
- **Parcours :** jusqu'à quatre segments des coquilles2–8 et9–13 km, triés le long du rayon ; pas de parcours du vide entre couches.
- **Contrôle :** trois variantes compilées et quatre captures cachées inspectées ; données, recette basse, mips de présence et témoin vérifiés. Validation en vol à l'utilisateur.
- **Livraison :** `tools/nuages-familles.ps1`, douze vues ; B opacité, C qualité, Espace pause, V météo×1/×5.
- **Git :** aucun commit, tag ni push demandé.

## 2026-10-27 · Cirrus locaux et conservation des témoins

- **Retour utilisateur :** rendu et stabilité à l'approche du cumulus et de la nappe excellents ; validation locale acquise.
- **Priorité :** compléter les formes locales avec des cirrus avant d'étendre la répartition.
- **Témoin :** copie figée des binaires, shaders, quatre assets et palette dans `x64/NuageFrostbiteReferenceTemoin/`, avec empreintes vérifiées.
- **Cirrus :** champ3D fibreux anisotrope précalculé128³, domaine fixe Est64/Nord32/vertical8 km ; trois bandes locales de couverture.
- **Densité :** fibres façonnées avant les mips ; profil compact centré vers11 km, centre variable de±0,35 km et épaisseur0,7–1,2 km dans une coquille9–13 km ; maximum0,022 avec extinction80/km héritée.
- **Limite :** essai artistique local, pas une météo planétaire ni une nouvelle reproduction complète de Frostbite ; vérifications en vol à l'utilisateur.
- **Mémoire :** cumulonimbus retenu pour la suite, après les familles locales courantes.
- **Git :** aucun commit, tag ni push demandé.

## 2026-10-27 · Référence locale guidée par Frostbite

- **Décision :** arrêter les variations globales sans référence visuelle ; isoler deux familles et leurs diagnostics.
- **Bruits :** générateur C++ original sebh/TileableVolumeNoise, révision1f879a26b89aaa4b5a7f112f14ec149d08057661 ; aucun paramètre ni formule modifié.
- **Entrées :** profils de densité/érosion explicites, carte locale256×128 km et deux zones dessinées ; choix artistiques du test, pas données originales du moteur Frostbite.
- **Rendu :** forme32 km, détail4 km, extinction80/km neutre, albédo1, quatre intervalles solaires ; intégration analytique et repères doubles conservés.
- **Diagnostics :** coupe de densité fixe, opacité3D et rendu éclairé séparés ; exposition neutralisée dans les seules vues de données.
- **Contrôle :** trois compilations et cinq captures sur deux lieux ; mips et données vérifiés. Aucun banc complet ni validation en mouvement.
- **Livraison :** `tools/nuages-frostbite-reference.ps1`, palette du27 octobre ; Courants C figé comme témoin.
- **Limite :** profils encore à juger ; passage planétaire et reconstruction à traiter après la validation locale.
- **Git :** aucun commit, tag ni push demandé.

## 2026-10-27 · Courants C : remettre la perturbation à l'échelle macro

- **Retour utilisateur :** B déforme les nuages en filaments ; la demande visait les grands ensembles et courants.
- **Retrait :** shader B repris avec warp24 vers3 seulement ; B et sa vraie météo B figés comme témoin.
- **Macro :** transport conjoint RGBA depuis météo A, champ tangent2/4 sur la sphère, déplacement médian182 km et maximum573 km.
- **Preuve de présence :** R modifié, mips conservateurs reconstruits ; trois textures3D identiques.
- **Comparaison :** C avec cartes A/C, même shader local ; `-MeteoA` isole le transport et `-Temoin` retrouve B.
- **Contrôle :** compilation et deux paires cachées à180/1 600 km, deux hémisphères ; aucun pli mesuré sur la grille de carte.
- **Limite :** transport statique de référence ; répétitions, plafonds et coût proche ne sont pas résolus par cet essai.
- **Livraison :** `tools/nuages-courants-c.ps1 -Static`, douze vues dans la palette.
- **Git :** aucun commit, tag ni push demandé.

## 2026-10-27 · Formes B : retour sur les silhouettes et les régimes

- **Retour utilisateur :** Formes A reste répétitive, plate en haut et en bas ; grands contours trop géométriques.
- **Densité :** potentiel3D moins hauteur au carré, puis partie positive au carré ; suppression des deux rampes à plateau.
- **Variété :** mélange mondial de bandes8/29,3 km, déformation128 km d'amplitude±12 km, demi-hauteurs locales variables.
- **Macro :** GBA perturbés ensemble sur la sphère ; R et les trois textures3D conservés. Option `-MeteoA` pour isoler cette modification.
- **Témoin :** Formes A et ses assets figés ; code natif et marcher inchangés.
- **Contrôle :** compilation, audit des données et captures cachées ciblées ; coût proche initial accru, aucun verdict global ou de mouvement.
- **Livraison :** `tools/nuages-formes-b.ps1 -Static`, `-Temoin` pour Formes A ; détails et limites dans la notice du spike.
- **Git :** aucun commit, tag ni push demandé.

## 2026-10-27 · Formes A : cumulus, nappes et extinction verticale

- **Demande :** deux familles distinctes, bases et sommets moins clampés ; remise rapide pour jugement en vol.
- **Témoin :** météo A et rendu V4 figés, quatre textures empaquetées avec empreintes ; aucune modification de sa session.
- **Densité :** champ large de 32 km pour les nappes, champ 3D primaire de 8 km pour les cumulus ; G interpole les familles.
- **Profil :** support local variable lu au mip 3 fixe, puis fades après le seuil de couverture et l'érosion ; aucun déplacement de profil selon la caméra.
- **Bornes :** support compris entre 1,45 et 8,47 km, strictement dans la coquille 1–9 km.
- **Contraste de nappe :** `smoothstep(0,55, 0,85, sheetMacro)` ; support normalisé par `smoothstep(0,50, 0,90, sheetMacro)`.
- **Préservation :** carte météo, quatre textures, exécutable, lumière, extinction et marcher identiques ; seul le shader de densité change.
- **Coût :** même maximum de cinq lectures par densité occupée, carte météo incluse ; aucun nouveau volume ni historique. Pas de mesure de performance statistique.
- **Contrôle :** DXC réussi ; trois paires de captures initiales, puis deux paires ciblées après correction d'une nappe trop uniforme. Deux lieux et deux familles ; vol à l'utilisateur.
- **Livraison :** `tools/nuages-formes-a.ps1 -Static` ; `-Temoin` pour météo A aux mêmes douze vues. Sources et sorties isolées.
- **Limites :** aspect et disparition de l'effet clamp à juger ; aucun nouveau LOD, cirrus, correction des bandes radiales ou validation planétaire.
- **Git :** aucun commit, tag ni push demandé.

## 2026-10-27 · Météo A : essai de répartition seule sur V4

- **Demande :** isoler la répartition avant de reprendre les formes et le LOD ; remise rapide pour les vérifications en vol.
- **Règle :** comparer à temps, rendu et positions identiques ; seul R de la carte change.
- **Conversion :** `R = 0,75 × smoothstep(0,08, 0,68, L)` remplace le relèvement des faibles luminances NASA.
- **Limite :** hypothèse de contraste régional ; ce coefficient n'est pas une fraction nuageuse physique ni une nouvelle simulation météo.
- **Préservation :** exécutable, shaders, trois textures 3D V4 et GBA de tous les mips identiques ; témoin sans écriture.
- **Mesure de carte :** moyenne R pondérée par l'aire de 0,403798 à 0,215494 ; aucune équivalence avec la couverture rendue.
- **Contrôle :** trois paires de captures cachées, orbite, motifs à 271 km et nappe proche ; empreintes et sidecars dans `x64/WickedWeatherACompare/`.
- **Constat :** zones faibles moins couvertes ; répétitions toujours visibles dans les bancs denses. Aucun verdict de mouvement ni de performance.
- **Livraison :** `tools/nuages-meteo-a.ps1 -Static`, `-Temoin` pour V4 ; douze vues communes dans la palette du 27 octobre.
- **Git :** aucun commit, tag ni push demandé.

## 2026-10-27 · Retour en vol : V5 non retenue

- **Aspect :** LOD jugé moins bon ; répétitions persistantes, contours plus nets et réduction de bruit peu convaincante.
- **Régression proche :** les hausses de couverture et le remplissage des nappes changent aussi le champ fin ; J ne retire pas ces modifications.
- **Limites confirmées :** répartition sans organisation météo convaincante, profils verticaux trop visibles, absence de cirrus distincts.
- **Décision :** V4 conservée comme témoin ; aucun nouveau réglage ni binaire dans ce diagnostic.
- **Suivi :** séparer les essais de répartition, de morphologie et de LOD ; détails de la V5 déplacés au log du spike.
- **Git :** aucun commit, tag ni push demandé.

## 2026-10-27 · Wicked V5 : formations et couverture optique

- **Demande :** varier les organisations horizontales et filtrer les contours lointains, avec remise rapide à l'utilisateur.
- **Formes :** bancs régionaux à 192 km, enveloppe à 32 km et microvolume à 8 km ; modulation continue des nappes et amas convectifs.
- **Filtrage :** moyenne de transmittance sur 512 colonnes × 48 pas dans une table 32³ ; aucun seuil nouveau sur un bruit déjà moyenné.
- **LOD :** mélange lumière/transmittance entre 0,12 et 0,65 km d'empreinte ; mode J pour comparer à la même formation fine.
- **Limbe :** milieu de segment pour les rayons sans croisement du proxy, cap de hauteur continu ; approximation à contrôler.
- **Natif :** une texture t28, b1 conservé, drapeau `MYPLANETENGINE_CLOUD_WICKED_OPTICAL_LOD`, J et `-FineOnly` ; sorties V5 distinctes.
- **Contrôles :** compilation ciblée et captures cachées, plusieurs lieux ; pas de banc complet ni de validation de mouvement.
- **Limites :** éclairage moyen et statistiques locales approximatifs ; bandes radiales fines non résolues.
- **Livraison :** `tools/nuages-wicked-v5.ps1`, témoin V4 aux mêmes positions et palette du 27 octobre ; aucun commit/tag/push demandé.

## 2026-10-27 · Wicked V4 : correction ciblée de la grille

- **Périmètre utilisateur :** garder le rendu actuel ; corriger rayons et distribution rectiligne.
- **Bruit :** octave Perlin périodique à une cellule remplacée par une base 3 ; fréquences 3–48 et somme des poids conservée.
- **Mips :** filtre binomial périodique du shape, sans changer son mip0 ; filtres de la seconde lecture shape et de la déformation adaptés à leurs fréquences.
- **Données :** `assets/wicked-clouds-v4/` séparé ; détail, déformation, météo et profils V2 conservés.
- **Rayons :** essais d'interpolation positive, signée et quadratique, puis d'albédo constant, écartés pour bandes restantes et coût. Déformation apériodique HLSL également écartée ; voir le log du spike.
- **Décision :** marche V2 conservée ; V4 livre seulement la correction de grille. Les rayons restent ouverts.
- **Contrôle :** quatre captures courtes à météo figée, pas de banc complet ni de validation du mouvement. Poses et coûts dans `x64/WickedV4DeliveryPreview/startup.json`.
- **Livraison :** `tools/nuages-wicked-v4.ps1`, F1 proche, F7 à 454 km, F8 à 2 601 km ; `-Temoin` ouvre la V2 avec la même palette et les mêmes positions.
- **Notice :** `log/spike-nuages-reference.md` ; vérifications en vol à l'utilisateur. Aucun commit, tag ni push demandé.

## 2026-10-27 · Wicked V3 de diagnostic : bandes radiales

- **Retour utilisateur :** anneaux mobiles à 2 601 km et près des nuages ; motifs répétitifs à 454 km.
- **Cause isolée :** bandes présentes en opacité seule, sans atmosphère et avec une forme macro constante ; sous-échantillonnage du volume par les pas de 48–240 m.
- **Essais :** pas uniforme de 12 m trop cher ; raffinement par variation optique insuffisant près des nuages ; archives sous `x64/RadialDiagnostic/` et `x64/Recovery/WickedV3AdaptiveFirst/`.
- **V3 :** subdivision des intervalles contenant du nuage à 12 m Éco / 6 m Référence ; parcours vide et saut météo conservateur maintenus ; arrêt sur transmission sous 0,003.
- **Contrôle court :** quatre captures cachées, trois lieux et plusieurs distances ; grandes bandes atténuées, répétitions restantes.
- **Coût nuages + air :** 31,67 / 26,26 / 38,55 / 45,88 ms ; régression, version de diagnostic non validée comme solution finale.
- **Livraison :** `tools/nuages-wicked-v3.ps1`, palette du 27 octobre, `-Temoin` pour V2 ; binaires V2 inchangés.
- **Notice :** `log/spike-nuages-reference.md` ; vérifications en vol confiées à l'utilisateur, aucun banc complet ni commit/tag/push demandé.

## 2026-10-27 · Wicked V2 : enveloppes locales et couverture de référence

- **Retour utilisateur :** progrès de stabilité près des nuages ; limites hautes et basses trop planes, répartition uniforme et motifs répétitifs surtout vers 160 km.
- **Enveloppes :** coquille de parcours 1–9 km ; profils locaux de base et de sommet, variations macro et rampes douces. Le profil de famille ne recoupe plus avant la rampe finale.
- **Formes :** deux repères de bruit monde fixes ; un seul remap des Perlin-Worley combinés, niveaux macro fractionnaires et lumière solaire indépendante du LOD vue.
- **Essai écarté :** carte météo purement synthétique ; trop grandes plaques pleines et rendu granuleux. Conservé sous `x64/WickedV2Preview/` et `x64/Recovery/WickedV2Start/`.
- **Référence :** composite historique NASA Blue Marble Clouds comme proxy de couverture ; types, bases et épaisseurs restent synthétiques. Crédits et image originale dans `third_party/NASA/`.
- **Vide :** mip1 réel inchangé ; R des mips2+ au maximum pour prouver le vide. Sauts bornés par le secteur sphérique et la marge bilinéaire, jamais par sigma seul.
- **Livraison :** `x64/NuageWickedV2/MyPlanetEngineWickedV2.exe`, lanceur `tools/nuages-wicked-v2.ps1`, témoin V1 par `-Temoin`. La session utilisateur en V1 n'est pas interrompue.
- **Contrôles finaux :** trois captures ciblées, proche, 160 km et orbite ; compilation native et DXC réussies. GPU nuages+air 13,12 / 3,22 / 8,57 ms en 720p figé sur GPU partagé ; coût et moyenne distance restent imparfaits.
- **État :** essai en vol attendu, pas de validation globale. Notice `log/spike-nuages-reference.md`, artefacts `x64/WickedV2FinalPreview/`. Aucun commit, tag ni push demandé.

## 2026-10-27 · Premier spike Wicked Engine · tag `piste/nuages-orbite-spike`

- **Demande :** repartir d'une base publiée, garder l'ancien témoin et laisser rapidement l'utilisateur juger en vol.
- **Modèle :** adaptation HLSL de Wicked Engine, révision `5433f0a6cb0ed9ddfd41b7742978d038eaff70de`, licence MIT conservée dans `third_party/WickedEngine/`.
- **Champ :** une coquille de 3 à 6,5 km ; couverture et type météo continus en 3D, forme Perlin-Worley et érosion, sans instancier le volume du POC.
- **Textures :** 128³, 32³ et 64³ RGBA8 avec mips, 10 935 148 octets ; chargées une fois et animées par les coordonnées.
- **Premières captures :** la période de forme initiale de 1,67 km répétait ses silhouettes ; réglage remplacé par 8 km, détail 1 km et déformation continue ±1,5 km à l'échelle de 37 km.
- **Précision :** références d'entrée et phases en double, racines raffinées par Newton et plancher entier, puis décalages float dans les boucles.
- **Qualité :** C compare 48–240 m / un échantillon solaire et 24–160 m / deux échantillons ; aucun historique temporel dans ce premier jet.
- **Contrôles :** compilation réussie ; quatre vues cachées initiales et deux après réglage. Derniers contrôles en 720p figé : profil 9,91 ms/frame dont 8,76 ms nuages+air ; dessus 7,51 dont 6,10 ms. GPU partagé, mesures ponctuelles.
- **Livraison :** lanceur `tools/nuages-wicked.ps1`, palette du 27 octobre ; `-Temoin` ouvre l'ancienne V2, dont les binaires sont inchangés. Première session `MyPlanetEngineWicked.exe` conservée ouverte ; `MyPlanetEngineWickedV1.exe` corrige le compteur et les accents au prochain lancement, avec le même shader.
- **Limites :** lumière, perspective aérienne, filtrage après seuil et rendu orbital restent des approximations à juger. Essais en vol confiés à l'utilisateur ; aucun commit, tag ni push demandé.
- **Notice :** `log/spike-nuages-reference.md` ; captures finales `x64/WickedPreview/`.

## 2026-10-27 · Arrêt de la V3 voxel et retour aux références publiées

- **Retour utilisateur :** bandes et scintillement vus de côté ; distribution répétitive, performances insuffisantes et bénéfice voxel non démontré.
- **Décision :** interrompre les agents avant la compilation V3 ; conserver la V2 comme témoin.
- **État rétabli :** sources natives et lanceur V2 ; le shader V3 à trois familles n'a pas été implémenté. Sauvegarde des préparatifs natifs dans `x64/Recovery/V3Interrupted-20261027/`.
- **Recherche :** Nubis Evolved, Nubis³, documentation Unreal et shaders HLSL de Wicked Engine. Cadrage dans `log/spike-nuages-reference.md` ; aucun nouveau binaire livré.
- **Proposition :** adapter un noyau publié de météo, forme, érosion et éclairage ; commencer par une couche convaincante et les vues sol, profil, intérieur, dessus et orbite.
- **Portée :** aucune campagne GPU ou end to end lancée ; vérifications en vol confiées à l'utilisateur. Aucun commit, tag ni push demandé.

## 2026-10-26 · Spike voxel planétaire · tag `piste/nuages-orbite-spike`

**Demande :** après un POC local fonctionnel, essayer rapidement l'échelle planétaire dans les mêmes conditions ; l'utilisateur réalise les vérifications en vol.

- **Retour V1 :** environ 10 FPS en voxel et procédural ; blocs trop répétitifs pour juger le lointain. Ancienne distribution et mesures dans `log/spike-nuages-voxel-planete-historique.md`.
- **V2 :** calculs d'entrée en double, puis boucles en coordonnées locales float ; couverture régionale continue, 1 023 cellules par axe et formations plus petites et variées.
- **Diagnostic V2 :** N coupe réellement les nuages ; temps GPU nuages+air et frame visibles. Sortie distincte `x64/NuageVoxelPlaneteV2/`. Deux captures finales à météo figée : 13,66 ms/frame en approche, 26,97 ms depuis l'orbite. Rapport `x64/VoxelPlanetV2Placement/startup.json` ; aucun verdict en vol.
- **Placement V2 :** centres largement décalés, neuf cellules candidates et somme des recouvrements ; rangées cassées, petites formations encore visibles comme des points depuis l'orbite. Première optimisation plus rapide mais encore alignée conservée dans l'historique.

- **Choix V1 :** répéter le volume partagé sur six faces de 127 × 127 cellules fixes ; aucune texture de densité par formation.
- **But de l'essai :** couverture, continuité en descente et fluidité visible ; formes répétées et marche lointaine simplifiées.
- **Isolation V1 :** sortie `x64/NuageVoxelPlanete/MyPlanetEngineVoxelPlanete.exe`, POC local conservé.
- **État V1 :** compilation Debug x64 réussie ; deux captures cachées, planète à 8 000 km et approche, produites sans erreur. Distribution régulière visible depuis l'orbite ; aucun verdict en vol ni banc complet. Contrôle `x64/VoxelPlanetStartup/startup.json`. Aucun commit, tag ou push demandé.
- **Notice archivée :** `log/spike-nuages-voxel-planete.md`, lanceur témoin V2 `tools/nuage-voxel-planete.ps1`.

## 2026-10-26 · POC voxel isolé · tag `piste/nuages-orbite-spike`

**Demande :** essai rapide dans un worktree séparé ; l'utilisateur prend la main dès qu'une version est montrable. La conversation principale poursuit sa solution planétaire.

- **Base :** `7298330`, POC proche animé validé.
- **Volume :** densité finale R32_FLOAT, cube local fixe de 4,8 km, grille 128³ ou 256³, sans mipmap.
- **Temps :** même météo ; volume reconstruit quand sa phase change, réutilisé pendant la pause.
- **Comparaison :** C bascule voxel/procédural à pose et temps identiques ; palette F1–F8 conservée.
- **Portée :** un nuage local dense ; aucune conclusion sur la mémoire ou les performances planétaires.
- **Vérification :** compilation et démarrage léger seulement, selon la demande ; verdict visuel confié à l'utilisateur.
- **État :** compilation Debug x64 réussie ; une capture cachée 128³ en 1 280 × 720 produite sans erreur. Nuage visible, corps de la fonction procédurale inchangé. Contrôle `x64/VoxelStartup/startup.json` ; aucun banc complet, aucun verdict en vol. Aucun commit, tag ou push demandé.
- **Notice :** `log/poc-nuage-voxel.md`, lanceur `tools/nuage-voxel-poc.ps1`.

## 2026-10-26 · Une météo partagée, des franges plus légères · branche `codex/nuage-poc`

**Retour utilisateur :** le POC précédent reste stable à l'approche et son aspect est validé. Demande suivante : mouvement et déformation avec le temps, pensés comme une météo commune ; rendu un peu moins solide.

- **Champ commun :** vent par rotation autour de l'axe de la planète, 12 m/s à l'équateur ; inverse du même mouvement pour lire la densité. Trois ondes dans le monde, périodes 120/150/200 s, amplitudes 80/40/60 m. Détail entraîné vers le haut à 1,71 m/s. Aucun paramètre de mouvement propre à l'identité d'un nuage.
- **Horloge :** temps réel partagé, indépendant des entrées de caméra et du nombre d'images ; phase continue bouclée à 2 400 s. Les bancs figent le temps, avec instantanés par tâche. Espace pause/reprise, V ×1/×5 ; F1–F8 suivent le vent sans réinitialiser le temps.
- **Aspect :** extinction 24 → 16 /km, franges 0,18 → 0,26 avec profil au carré, base plus progressive ; diffus 0,18 → 0,22. Même budget de marche et de lumière, toujours deux lectures de détail par densité ; trois ondes analytiques en plus.
- **Versions :** nouveau binaire `x64/NuagePoc/MyPlanetEngineAnime.exe` ; version figée validée conservée dans `x64/NuagePocReference/`. Historique : `log/poc-nuage-stable-historique.md`. Aucune fusion, aucun commit ou push demandé.
- **Validation :** compilation complète réussie ; les cinq vérifications de `tools/banc_nuage_poc.py` passent. Retour au même temps et à la même vue : différence d'opacité exactement nulle. Variation moyenne à 1/60 s : 0,0000211 ; déformation après suivi du vent à 30 s : 0,0214 ; raccord 2 399,99 → 2 400 s : 0,00000911. Valeurs d'opacité linéaire moyennées sur l'image. Le vol interactif reste au jugement de l'utilisateur.
- **Franges mesurées, vue d'approche :** 36 739 pixels d'opacité partielle contre 24 907 dans la référence ; opacité moyenne de l'image 0,1234 contre 0,1374. Les deux versions complètes sont comparées, déformation initiale comprise.
- **Coût mesuré sur ce poste, même vue et soleil, temps 0 :** rendu médian 1,93 → 2,75 ms (nouvelle version : 2,59–3,12 ms sur quatre relevés). Comparaison des versions complètes, avec les nouvelles franges, pas une mesure isolée des trois ondes. Résultats : `x64/NuagePocAnimationCheck/verification.json`, `animation.png`, `cout/mesures.json`.
- **Portée :** la loi de mouvement commune s'exerce sur la formation du POC ; intégration de la couverture planétaire hors du périmètre de cette itération.

## 2026-10-26 · Un cumulus fixe, référence d'approche · branche `codex/nuage-poc`

**But :** valider rapidement la position, la forme et le contour en approche, avant les optimisations. Mode explicite `MYPLANETENGINE_CLOUD_POC`, sans modification du rendu normal. L'utilisateur prend en charge le verdict end to end.

- **Réglages de maquette :** centre à 4 000 m, 0,5 N, 161,5 E ; quatre lobes, tuile 3D fixe à 4,096 et 1,024 km, extinction au plus 24 /km ; pleine résolution, pas d'au plus 12 m, au plus 384 pas et six points vers le soleil.
- **Règle :** la densité dépend de la position dans le nuage, jamais du maillage glissant, de l'ancre ou de l'empreinte de caméra. Position relative calculée en double précision avant passage au shader. Sans cascade, damier, jitter, vent, lissage temporel ni halo.
- **Lancer et itérer :** `tools/nuage-poc.ps1`, `-Build` après modification. Build `x64/NuagePoc`. Palette F1–F8 : loin, approche, bord, entrée, intérieur, retour, dessus, dessous.
- **Portée :** un seul volume local, éclairage simplifié et pas d'ombre au sol. Le banc planétaire de qualité est hors du périmètre de cette référence. Pas de fusion, commit ou tag avant demande et validation.
- **Validation :** compilation complète réussie ; cinq captures sans fenêtre à 1 280 × 720 (loin, approche, bord, intérieur, opacité). Sur huit images d'opacité à caméra fixe avec le maillage du terrain en mouvement : différence moyenne de 0,0000355 sur 255, maximum de 1 sur 255. Cela contrôle l'indépendance du maillage, pas le vol réel. Résultats locaux : `x64/NuagePocCheck/verification.json`, `apercu.png`. Approche et traversée en vol à valider par l'utilisateur.
- **Itérations :** les passages plein écran sont tous compilés par DXC pour conserver une chaîne compatible ; reconstruction incrémentale contrôlée. Les erreurs d'un banc sans fenêtre s'écrivent dans `<jobs>.error.txt` au lieu d'attendre une boîte de dialogue invisible.
- **Détail :** `log/poc-nuage-stable.md`, `MyPlanetEngine/CloudPoc.hlsli`, `tools/tests/2026-10-26-nuage-poc.txt`.

## 2026-10-25 · La stabilité des nuages · branche `muse-nuages-stabilite`

**Symptôme, en vol sur le volume ci-dessous :** des fourmillements et des scintillements, des glitches carrés et tournés à 54 et 135 km, un disque sombre vu du sol, des mutations à l'approche ; et une animation qui semblait vivre en petit à l'intérieur du nuage. Le champ est figé, sans vent : tout ce mouvement était du bruit d'échantillonnage.

**Les causes, et ce qui les règle** (détail et règles : `log/recherche-nuages-historique.md`, « La stabilité » ; `principes.md`) :
- **La couture des cascades :** leur portée se lisait en norme max, un carré, et chaque recentrage reprenait des axes est-nord qui tournaient la grille et redécoupaient chaque colonne. Portée en distance, fondu élargi, recentrage par texels entiers du plan propre, axes transportés, niveau fin fractionnaire en descente, maximum lissé entre contraintes de niveau.
- **Le damier :** la moitié des texels gardait la marche de l'image précédente, et l'historique la remélangeait comme fraîche, dans une caméra qui a bougé. La confiance se gouverne par le déplacement de reprojection en texels ; la distance des nuages s'accumule comme leur lumière ; le passé se clipse aux moments du voisinage.
- **Le disque du détail proche :** son fondu était linéaire en distance, et la même volute ouvrait la porte et soulevait le sommet, gonflant l'épaisseur moyenne d'un côté du fondu. Fondu par octaves d'empreinte, sommet en lognormal de moyenne la colonne, porte décalée de la corrélation.
- **La coupure au terrain** se faisait par quarts de pixels entiers : la distance se lit filtrée comme la lumière.

**Tremblement au repos** (banc `stabilite`, nouveau : caméra fixe, maillage en vol ; écart moyen entre images successives, avec lissage) :

| Vue signalée | Avant | Après |
|---|---|---|
| Sol, 764 m, vers le haut | 0,23 | 0,09 |
| 54 km | 0,22 | 0,23 |
| 135 km | 0,29 | 0,28 |

- **Sans lissage :** 3,48 → 2,66 au sol ; 2,87 → 3,11 et 3,76 → 3,99 en hauteur : la marche brute varie un peu plus, le fondu du détail couvre plus d'octaves.
- **Mutation en descente rendue,** 200 → 25 km par pas, centres appariés : 0,0347 → 0,0344 de luminance linéaire en moyenne. Les captures du banc sont convergées vue par vue : le gain des recentrages en vol continu se juge en vol, pas au banc.
- **Écartés par la mesure :** le décalage de marche fixe par pixel (repos à 0,01-0,07, mais un pointillé régulier de biais de quadrature sur les images convergées) et sa progression dorée commune (1,05 et 1,38). Le décalage renouvelé par image est gardé ; l'historique gouverné l'absorbe.
- **Inchangés :** fraction par bande et descente du banc (43,6 → 43,0 %, écart 0,5 point). Disque entier : contraste 2,5 → 2,7, rapport des pixels sombres 12,9 → 11,0 ; la planète laiteuse reste, ci-dessous.
- **Banc qualité,** 12 sites, `--before` la base de la branche : 23 tuiles sur 26 à ±0,0. Trois trous p95 bougent de +0,4 à +0,8 dB (neige à 12 et 800 m, herbe à 800 m), là où l'ombre des nuages change de place avec les cascades ; le p95 des photos est à 3,4 dB. Segments droits et mutation du maillage inchangés.

**Reste :** un arc fin au passage de portée des cascades (le plafond et le sigma d'un texel grossier ne sont pas la moyenne des fins : cascades par moyennage descendant à faire) ; le vent et le mouvement ample des formations, chantier suivant ; le coût sous les cirrus et la planète laiteuse, inchangés.

- Image : `journal/2026-10-25-nuages-stabilite.jpg`. Tests en vol : `tools/tests/2026-10-25-nuages-stabilite.txt`. Bancs : `tools/banc_nuages.py --parts stabilite`, `tools/banc_tremblement.py`.

## 2026-10-25 · Les nuages en volume, de l'orbite au sol · tag `piste/nuages`

**Réglages :** nouveaux fichiers `Clouds.cpp`, `Clouds.h`, `GpuHelpers.h` et les passes `CloudBake.hlsl`, `CloudDetail.hlsl`, `CloudCascades.hlsl`, `CloudVolume.hlsl`, `CloudResolve.hlsl`. La couche 2D est retirée. Cascades de 1 024² texels, demi-largeurs 32 × 4^k km ; tuile de volutes de 128³ texels ; 80 pas au plus, la moitié des pixels par image en damier, trois points vers le soleil. Vue de diagnostic `clouds` : 14. Registres des nuages : t10 à t22. Plan et écarts : `recherche-nuages.md`, section « Fait : le volume ».

**Pourquoi une refonte :** en vol, l'utilisateur voyait des nuages plats, cassés dessous et dedans ; d'orbite, des grilles de points et une planète laiteuse ; à 855 km, des ponts coupés aux côtes ; à 2,5 km, un pont plein, sans transparence.

**Les causes, et ce qui les règle :**
- **Les grilles de points :** les octaves du bruit s'annulaient ensemble aux nœuds de leurs grilles emboîtées. Chaque octave est décalée (`CloudFbm`). Règle ajoutée à `principes.md`.
- **Les côtes :** la carte ne connaît pas la terre ; la couche 2D effaçait les nuages d'une région entière. Le volume la remplace.
- **Le pont plein et gris :** la diffusion multiple inversait ses deux faces, R à la base et 1 − R au sommet. Remise à l'endroit, et prise le long du rayon du soleil.
- **Des aiguilles et des falaises :** un champ 2D dressé en hauteur. Ses octaves de 1 km et moins passent en 3D, des volutes de même écart-type. Règle ajoutée à `principes.md`.
- **Des pyramides au loin :** le pied d'un pas valait toute sa longueur, et floutait les tours. Il vaut l'empreinte du pixel plus un quart du pas.

**Photos de référence,** de mémoire, aucune n'étant téléchargée, contre les tests en vol :
- **de l'ISS, 400 km :** cumulus des alizés en pop-corn, chacun avec son ombre sur l'océan sombre ; ponts de stratocumulus en cellules ; enclumes en disques. Tenu : pop-corn et ombres, ponts troués où la mer se voit.
- **d'avion au-dessus d'un pont :** sommets bosselés blancs au soleil, creux plus sombres. Tenu à 2,5 km.
- **du sol :** cumulus à base plate et grise, sommets ronds éclairés ; plafond de stratus gris uniforme ; brouillard à 100 m de visibilité. Tenu, bases un peu claires.
- **de côté :** cumulus en chou-fleur, cumulonimbus en tour coiffée d'une enclume. Tenu pour les cumulus ; les tours sont trop régulières, des cylindres bosselés.

**Épaisseur optique et couverture :** τ croît avec la profondeur dans le champ, de 0 au bord à 11 pour un stratus de 0,3 km et 34 pour un cumulus de 1,5 km, 45 /km d'extinction. Une région en partie couverte transmet 1 − c (1 − e^−τ) : la mer se voit entre les nuages, jamais à travers un cœur épais.

**Fraction nuageuse par bande de 10°,** vue `clouds`, 16 vues par bande, contre MODIS (King et al. 2013) :

| Bande | 90-80 S | 80-70 S | 70-60 S | 60-50 S | 50-40 S | 40-30 S | 30-20 S | 20-10 S | 10-0 S |
|---|---|---|---|---|---|---|---|---|---|
| Nuages | 70 % | 92 % | 86 % | 72 % | 69 % | 62 % | 58 % | 56 % | 64 % |
| MODIS | 45 % | 55 % | 82 % | 88 % | 82 % | 68 % | 55 % | 55 % | 62 % |

| Bande | 0-10 N | 10-20 N | 20-30 N | 30-40 N | 40-50 N | 50-60 N | 60-70 N | 70-80 N | 80-90 N |
|---|---|---|---|---|---|---|---|---|---|
| Nuages | 68 % | 53 % | 47 % | 57 % | 73 % | 81 % | 84 % | 94 % | 96 % |
| MODIS | 68 % | 57 % | 50 % | 57 % | 68 % | 75 % | 76 % | 78 % | 76 % |

- **Le globe :** 65,5 % contre 65,1 %.
- **De 40° S à 70° N, à 8 points près.** L'océan austral, −16 et −13 ; l'Arctique, +16 et +20. Le décalage des octaves a changé le tirage de la planète, pas la loi ; 16 vues par bande au lieu de 32.

**Descente,** part de nuages d'une zone de 60 km, de 1 500 à 60 km, 8 lieux : moyenne de 43,6 à 43,0 %, écart maximal 0,5 point.

**Côtes,** 12 lieux vus de 400 km, part de nuages par distance à la côte :

| Bande | terre 25-50 km | terre 10-25 km | terre 0-10 km | mer 0-10 km | mer 10-25 km | mer 25-50 km |
|---|---|---|---|---|---|---|
| Nuages | 51,2 % | 51,9 % | 55,2 % | 56,9 % | 60,2 % | 61,3 % |

- **Pas de marche à la côte :** 1,7 point entre les deux bandes qui la bordent, moins qu'entre deux bandes voisines du même côté. La pente d'ensemble vient du tirage de 12 lieux.

**Disque entier depuis 7 400 km,** soleil dans le dos, 6 vues :
- **Océan dégagé,** sous moins de 20 % de nuage au pixel de 20 km : 4,4 % du disque. Pixels sombres, sous deux fois sa lumière : 57 %.
- **Contraste nuages épais sur océan dégagé :** 2,5 ; 3,1 avant la fusion avec `jalon/19-detail-sol`. Sur Terre, nuages épais 0,5 à 0,8, océan vu d'orbite avec son air 0,08 à 0,1 (CERES) : 6 à 8.
- **Déciles de luminance,** linéaire : de 0,19-0,30 à 10 % à 0,70-0,72 à 90 %.
- **La planète reste laiteuse, pour deux raisons mesurées.** Sans nuages, l'océan dégagé est 2,1 fois plus clair qu'avant la fusion, 0,233 contre 0,109 : l'exposition. Et le champ des cumulus, ses petites octaves pesées 2,5 fois, laisse peu de grandes zones claires au pixel de 20 km. Les ramener à 1,5 fois ne change presque rien au disque et rend les cumulus en blocs : gardé à 2,5.

**Luminance rendue d'une zone de 60 km, de 1 500 à 25 km :** 0,316 à 0,373 sur l'équateur, 0,19 à 0,26 à 41° S, sans tendance ; à 15 % près.

**Coût** des passes du volume, cascades, marche et lissage, entre deux horodatages GPU. Le GPU était occupé à 92-97 % par cinq autres moteurs, qui découpent les longues passes : la moyenne n'y veut rien dire. Le temps retenu est le minimum sur cinq lancements de 165 images chacun, une borne haute du temps au repos :

| Vue | Sous des cumulus, 500 m | Pont, 2,5 km | Sommets, 2,6 km | Cumulus de 6 km | Cumulonimbus, 3 km | Brouillard | Horizon, 1,7 km | Avion, 10 km | 400 km | 855 km | 7 400 km |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Nuages | 2,0 ms | 1,3 ms | 1,7 ms | 1,0 ms | 2,3 ms | 0,8 ms | 0,6 ms | 3,6 ms | 0,8 ms | 0,6 ms | 0,6 ms |

- **Dans le budget de 2 à 3 ms sauf sous les cirrus,** 3,6 ms : un rayon rasant y traverse des dizaines de km de voile.
- **Ce qui l'a ramené là :** la moitié des pixels marchée par image, en damier ; trois points vers le soleil ; le niveau des cascades partagé par pas ; douze pas à travers les cirrus ; le décalage des tours limité à la forte convection.
- **Non compté :** l'ombre et l'air sous les nuages dans la passe d'atmosphère.

**Reste :**
- **le coût sous les cirrus,** 3,6 ms ;
- **la planète laiteuse d'orbite,** ci-dessus ;
- **les tours de cumulonimbus trop régulières ;**
- **pas de vent,** cirrus et rues figés ;
- **le scintillement,** non mesuré au banc.

- Image : `journal/2026-10-25-nuages-volume.jpg`. Tests en vol : `tools/tests/2026-10-24-nuages.txt`. Bancs : `tools/banc_nuages.py`, côtes et disque entier ajoutés.

## 2026-10-25 · Le ciel nocturne : étoiles, planètes, Voie lactée · tag `piste/etoiles`

**Hors de `main` :** branche `etoiles`, gardée pour être intégrée ; le plan est dans `recherche-ciel-nocturne.md`. Ses réglages ne sont pas dans « Réglages actuels ».

**Réglages :** `SUN_MAGNITUDE` = -26,74, `SUN_LUX` = 125 885 lx, `STAR_POINT_LIMIT` = 8, `DIFFUSE_GALACTIC_LIGHT` = 0,3, `AIRGLOW_ZENITH_MAGNITUDE` = 22,4, `AIRGLOW_ALTITUDE_KM` = 90, `AIRGLOW_WIDTH_KM` = 4, `AIRGLOW_COLOR_INDEX` = 0,8, nouveaux ; tables de l'atmosphère en flottants 32 bits, diffusion multiple sur 256 × 32 au lieu de 32 × 32. Recherche, choix et sources : `recherche-ciel-nocturne.md`.

- **Demande :** les étoiles, constellations, galaxies et planètes, vues de l'espace et du sol ; leur visibilité de jour et de nuit à travers l'air ; une lumière faible sur les nuits.
- **Règles, dans `principes.md` :** le ciel est de la lumière, pas un décor ; la nuit reste la nuit ; une table résout la fonction qu'elle porte.
- **Changements :**
  - **les étoiles et les planètes,** `Stars.hlsl` : un quad par étoile, un seul dessin, dans une couche à elles que la courbe de tons ajoute après le lissage temporel. Leur lumière en magnitudes, par l'échelle du Soleil ; leur couleur, de B-V par Planck ; leur image, un profil de Moffat de 2 pixels, chaque pixel la part qu'il couvre ;
  - **ce qu'on voit :** la transmittance de l'air, puis le seuil de l'œil de Schaefer contre le ciel derrière l'étoile, lu dans l'image composite ; l'œil ne voit que l'excès ;
  - **les étoiles,** `BrightStars.hlsli` : 320 écrites jusqu'à 3,5 ; un champ procédural jusqu'à 8, aux comptes publiés par magnitude et à la concentration galactique d'Allen ;
  - **les planètes :** éléments de JPL à la date que donne la place du Soleil, en 2026 ; magnitudes de l'Astronomical Almanac ;
  - **la Voie lactée,** `Sky.hlsli` : la lumière des étoiles plus faibles que 8, sa moyenne par les comptes, sa forme par les comptes d'Allen, des nuages de bruit de gradient ; dans la passe du ciel, derrière l'air ;
  - **la lueur atmosphérique,** `NightSky.hlsli` : une émission dans la marche du ciel, couche en sech² à 90 km ; elle éclaire le sol par la table d'éclairement du ciel, avec la moyenne de la lumière des étoiles ;
  - **l'exposition,** `ToneMap.hlsl` : le posemètre lit le crépuscule et la nuit, au lieu de garder la lumière du coucher ; la clé de l'œil de Krawczyk, rapportée à midi, assombrit la nuit de 4,5 IL ; les bâtonnets voient sans couleur ce qui est sombre pour un œil adapté au sombre ;
  - **les tables de l'atmosphère :** en flottants 32 bits, la nuit tombait sous le plus petit demi-flottant ; la diffusion multiple sur 256 hauteurs du soleil ;
  - **la sortie 8 bits :** un demi-niveau de bruit fixe sur l'écran avant l'arrondi ; le dégradé du ciel de nuit se coupait en paliers ;
  - **une vue de mesure,** `MYPLANETENGINE_VIEW=luminance` : la luminance sur 16 bits et le posemètre ; `MYPLANETENGINE_NO_STARS` retire les étoiles ;
  - **un banc,** `tools/banc_etoiles.py` : vues, crépuscule, comptes, scintillement, coût.
- **Mesures, `tools/banc_etoiles.py` :**
  - **comptes,** tout le ciel, table et champ, contre les comptes publiés : à 4, 523 contre 513 ; à 5, 1 624 contre 1 603 ; à 6, 4 821 contre 4 797 ; à 6,5, 9 123 contre 9 099 ; à 8, 41 999 contre 41 976 ;
  - **concentration galactique,** densité à moins de 10° du plan sur plus de 60° : 3,17 à 6, Allen 3,20 ; 3,02 à 8, Allen 3,10 ;
  - **le dessin contre le modèle,** une calotte de 25° autour du centre galactique vue de l'espace : 132 étoiles plus brillantes que 5, 132 attendues ; 361 à 6, 362 attendues ;
  - **du jour à la nuit,** le désert à 26° N, vers le zénith, le soleil de 0° à -24° : le ciel, le posemètre et la magnitude limite contre le modèle de Schaefer et les éclairements publiés ; les étoiles que le seuil laisse passer, celles que l'écran montre (3 niveaux de plus au moins) :

| Soleil | 0° | -4° | -6° | -8° | -10° | -12° | -14° | -16° | -18° | -24° |
|---|---|---|---|---|---|---|---|---|---|---|
| Zénith, cd/m² | 169 | 9,9 | 1,0 | 0,086 | 0,012 | 2,4e-3 | 6,2e-4 | 2,5e-4 | 1,5e-4 | 1,4e-4 |
| Schaefer, cd/m² | 101 | 2,4 | 0,38 | 0,059 | 9,4e-3 | 1,7e-3 | 4,6e-4 | 2,7e-4 | 2,4e-4 | 2,4e-4 |
| Posemètre, lux | 1 050 | 66 | 9,8 | 0,87 | 0,076 | 0,011 | 2,8e-3 | 1,0e-3 | 7,1e-4 | 6,0e-4 |
| Publié, lux | 410 à 585 | | 2 à 3,5 | | | 0,008 | | | 6e-4 | |
| Limite à l'œil, ce ciel | -0,5 | 1,9 | 3,3 | 3,9 | 4,2 | 4,9 | 5,9 | 6,4 | 6,7 | 6,7 |
| Limite, ciel de Schaefer | 0,0 | 2,8 | 3,6 | 4,0 | 4,2 | 5,2 | 6,1 | 6,4 | 6,4 | 6,5 |
| Étoiles passées, à l'écran | 0, 0 | 6, 0 | 29, 1 | 41, 13 | 43, 30 | 76, 70 | 207, 190 | 381, 369 | 522, 515 | 599, 581 |
| La plus faible à l'écran | | | 0,2 | 3,3 | 4,0 | 4,8 | 5,8 | 6,4 | 6,7 | 6,7 |

  - **lecture :** de -8° à la nuit, ciel et limite suivent Schaefer à 45 % et 0,3 magnitude près ; la nuit, notre ciel est 0,5 magnitude plus sombre que le sien, qui compte la lumière zodiacale. De 0° à -6°, le ciel est 1,7 à 4 fois trop clair. Dans ce champ, la première étoile paraît à -6° : Arcturus, 0,2 à travers l'air ;
  - **scintillement,** la caméra tournant de 0,04° par image, 24 images, environ 350 étoiles suivies : leur lumière sommée change de 0,5 % (p95 3,5 %), leur pixel le plus brillant de 6,6 %, 1,9 niveau de l'écran (p95 3,1). Caméra immobile : 0. En points d'un pixel : 0,1 %, 0 niveau, mais toute étoile plus brillante que 5,5 y était le même pixel blanc ;
  - **la nuit au sol :** posemètre 6,0e-4 lux, soleil à -20° ; l'intégrale de van Rhijn sur notre air en attend 5,7e-4, lueur 3,3e-4 et étoiles 2,3e-4 ; publié 6e-4 lux à -18°, 1e-3 lux avec la lumière zodiacale, absente ici. Le désert, d'albédo 0,10, à 1,2e-5 cd/m² : une silhouette noire sous un ciel gris foncé ;
  - **les vues de test, la nuit,** `tools/tests/2026-10-25-etoiles.txt` : le ciel au centre de 21,15 mag/arcsec² vers le centre galactique à 22,13 ailleurs, publié 21,9 à 22,0 ; de 84 à 1 269 étoiles à l'écran selon le champ ; la plus faible à 0,01 ou 0,02 magnitude de la limite de l'œil sur le ciel derrière elle, entre 6,6 et 7,1 ;
  - **de jour, ou face au jour :** aucune étoile à l'écran. D'orbite, la planète au jour devant : 22 étoiles passent le seuil de l'œil sur le noir, aucune ne se voit, l'exposition est celle du jour ; vers le terminateur, 476 et aucune ;
  - **au crépuscule :** à -4° vers l'est, 2 dessinées, aucune à l'écran ; à -9° vers l'ouest, 14 dessinées, 3 à l'écran, Vénus, Jupiter et Mercure ; à l'aube de décembre, -12°, 34 à l'écran, Vénus en tête ;
  - **les tons,** `tools/banc_tons.py`, contre le jalon 18, sol médian à l'écran : vues de jour à 0,02 IL près ; soleil bas de 8° à 2°, -0,08 à -0,26 IL, la clé de l'œil ; crépuscule à -3°, +1,34 IL, le posemètre suivant la lumière au lieu de garder celle du coucher ;
  - **coût,** `banc_etoiles.py cout`, RTX 4070 Ti partagée avec d'autres instances, le moins de six captures alternées, 1280 × 720 : la passe des étoiles reste sous le bruit, 0,01 ms ; la passe du ciel prend 0,12 ms de plus vers l'espace, 0,26 ms sous un ciel de jour qui remplit l'image, la Voie lactée par pixel et la lueur à chaque pas de la marche. Au sol de nuit, le bruit de mesure, 0,5 ms, couvre l'écart ;
- **Essayé et écarté :**
  - **les étoiles en points d'un pixel :** parfaitement stables, mais toutes saturées, sans hiérarchie d'éclat ;
  - **le lissage temporel sur les étoiles :** il étale et assombrit une étoile qui glisse ; d'où leur couche à part ;
  - **une couleur de lueur à moitié dans la raie verte :** un ciel vert olive ; puis la couleur mesurée du ciel, brune près de l'horizon. Les bâtonnets la rendent grise ;
  - **une Voie lactée au profil d'Allen seul, bruitée partout :** des nuages sur tout le ciel ; d'où la bande étroite, seule bruitée.
- **Reste :**
  - **le crépuscule de 0° à -6°,** 1,7 à 4 fois plus clair que le modèle de Schaefer, le posemètre 2 fois au coucher et 3 à 5 fois à -6° : l'approximation de la diffusion multiple de Hillaire ;
  - **la lumière zodiacale,** 20 à 30 % de la nuit, et son cône au crépuscule ;
  - **les catalogues :** le BSC5 pour les étoiles jusqu'à 6,5, la carte de la NASA pour la Voie lactée ; fichiers à demander, `recherche-ciel-nocturne.md` ;
  - **une seule couche de lueur,** de couleur moyenne : vue d'orbite, la ligne verte de l'oxygène à 97 km ne s'en distingue pas ;
  - **au crépuscule, l'écran perd 0,2 à 0,7 magnitude sur l'œil :** l'image d'une étoile, 2 pixels de 5', dilue la lumière que l'œil des cônes concentre sur 1' ; la nuit, 0,01 à 0,02. Un écran plus fin la rapproche ;
  - **le ciel de nuit à l'écran,** gris à 25 % : à juger en vol ;
  - **pas de Lune ; la date** ne parcourt que la moitié de l'année, de décembre à juin ;
  - **la Voie lactée et la lueur se calculent aussi de jour,** invisibles : 0,26 ms qu'un test sur la clarté du ciel épargnerait ;
  - **le crépuscule plus clair à l'écran qu'au jalon 18,** +1,3 IL à -3°, le posemètre le suivant : à juger en vol.
- **Pour revenir :** `MYPLANETENGINE_NO_STARS=1` retire les étoiles et les planètes ; le reste, `git checkout jalon/18-lumiere`.
- **Tests en vol :** `tools/tests/2026-10-25-etoiles.txt`, à lancer par `tools/lance.ps1 -Exe x64\Etoiles\MyPlanetEngine.exe -Tests tools\tests\2026-10-25-etoiles.txt` ; les quatorze vues, `images/ciel-nocturne.jpg`.

## 2026-10-25 · Les plages · tag `piste/plages`

**Hors de `main` :** branche `plages`, faite sur l'ancienne mer, à porter sur la mer FFT ; le plan est dans `recherche-cotes.md`. Ses réglages ne sont pas dans « Réglages actuels ».

**Réglages :** la plage passe d'une bande de 5 à 25 m, ±9 m, à une bande de 0 à 2,5 m, ±1 m, sur les pentes de moins de 0,12 à 0,22 ; nouveaux, le sol mouillé et sa brillance, la laisse de mer, les algues et le lichen noir des roches ; la ligne d'eau perd son fondu fixe de −1 à +1 m (`GroundMaterials`, `PixelShader.hlsl`). Plan et recherche : `recherche-cotes.md`, étapes 1 et 2.

- **Symptôme :** des plages de 540 m de large en médiane, plus de 1,9 km pour un rivage sur dix ; du sable jusqu'à 25 m sur les falaises ; 30 à 45 m de rivage flou.
- **Cause :** une bande d'altitude de 5 à 25 m sur des côtes de plaine en pente de 4 à 6 %. La largeur d'une bande est sa hauteur sur la pente : sur Terre, les bandes d'un rivage sont des hauteurs d'eau, de 1 à 3 m.
- **Règles, dans `principes.md` :** la côte est une limite comme les autres ; un bruit élargit une limite de ce qu'il la déplace, pas plus.
- **Changements :**
  - toutes les bandes sont des hauteurs d'eau, multipliées par l'exposition de la côte, `CoastExposure`, tirée du bruit local : plage 2,5 m, sol mouillé 1 m, laisse 1,06 à 1,16 m, algues 0,4 m, lichen noir 0,8 à 3 m ;
  - chacune est une part de la terre du pixel, `ShoreBelow`, puisque la mer couvre le reste ; la mer couvre la part des hauteurs sous 0, celles que cache la maille et celles du pixel, sa pente fois sa taille, `ShoreSpread` ;
  - la plage s'arrête aux pentes de 0,12 à 0,22, les faces de plage réelles ; le sol mouillé est deux fois plus sombre et brille, un film d'eau de rugosité 0,2 au Fresnel de l'eau, `WaterSheen`, à partager avec la mer ;
  - la laisse est cassée en taches par un bruit de 16 m à 50 cm ; algues et lichen ne teintent que la roche.
- **Mesures :**
  - largeur de plage sur 968 rivages, portage CPU, `tools/cotes/t8.py` : médiane 502 → 39 m, 53 m là où il y a une plage ; p90 2 196 → 209 m ; 18 % des rivages sans plage, trop raides ; sol mouillé, médiane 14 m, p90 51 m ;
  - banc de descente, part de plage, côte de 0,478° N 116,513° E : carré de 300 km, 4,7 → 2,8 % avant, 0,3 à 0,4 % après, de 1 500 à 260 km ; carré de 60 km, 4,3 à 5,2 % → 0,4 à 0,6 % de 800 à 60 km, pour 0,65 % au sol (`t9.py`) ; carré de 2 km, 14,8 à 16,2 % ; carré de 150 m, 46,0 à 47,0 % ;
  - autre côte, 28,32° S 104,70° O : carré de 60 km, 11,3 → 5,5 % avant, 0,5 à 1,0 % après, pour 1,0 % au sol ; carré de 2 km, 12,9 → 9,9 %, en suivant la part de mer, qui varie autant avant ;
  - banc de qualité, 30 lieux : identique, aucun lieu tiré n'a de rivage ;
  - tremblement avec / sans lissage : mer à 120 m 0,01 / 0,04 → 0,01 / 0,05 ; ras de l'eau 0,00 / 0,01, inchangé ; contre-jour à 30 m 0,01 / 0,06 → 0,01 / 0,08 ; falaise 0,08 / 0,39 → 0,08 / 0,41 ;
  - coût : sous le bruit de mesure, le GPU partagé avec d'autres bancs.
- **Essayé et écarté :** la limite de pente de la plage déplacée par le bruit des limites de la roche : son étalement, pris pour des limites vers 0,8, retirait de loin deux tiers de la plage.
- **Vues en vol :** `tools/tests/2026-10-25-plages.txt` ; avant et après, `journal/2026-10-25-plages.jpg`.
- **Reste :**
  - au ras de l'eau, le sable mouillé reflète le ciel et paraît blanc à côté d'une mer encore sans reflet : la mer doit refléter le ciel de même ;
  - la part de mer de loin varie de 6 points sur un carré de 2 km, avant comme après : `ElevationSpread`, une rugosité tirée du type de terrain ;
  - les rides de vent restent sur la face de plage ; pas encore de galets ni de vase, le type de côte, étape 3.
- **Pour revenir :** le commit `044bcf2`, tag `jalon/18-lumiere`.

## 2026-10-24 · La mutation à l'approche

**Réglages :** `FineMinCell`, 20 → 3,4 m (`D3DApp.h`) ; `FINE_LIGHT_MIN_CELL`, 20 m, nouveau : la lumière garde l'ancien seuil ; la neige ne tient plus compte de la pente des textures (`GroundMaterials`).

- **Symptôme,** en vol vers un massif enneigé : une tache verte dans la neige, de forme nette à 1,6 km du sol, mangée petit à petit par le blanc à 1,3 km, revenue à 530 m ; puis des taches brunes au dernier moment, à 143 m. Vues : `tools/tests/2026-10-24-approche.txt`.
- **Le banc :** `tools/banc_descente.py` rend en un seul lancement toutes les hauteurs et toutes les vues de diagnostic, et donne les parts vues, neige sur roche sur éboulis sur sol, comme `banc_qualite.py`. Ici, un carré de 100 m sous la tache, 32,9325° N 173,9705° E, de 2 km à 100 m.
- **Cause 1, la forme de la tache :** la normale des décisions perdait les formes de 13,5 à 100 m.
  - La grille fine s'éteignait entre des mailles de face de 40 et 20 m, de 1,9 km à 960 m de haut.
  - Le maillage seul ne porte une octave qu'au-delà de 4 mailles : 84 m à 1 km, 13,5 m seulement sous 160 m.
  - La tache est un versant tourné vers l'équateur, plus chaud. Lissé, il se refroidissait : la neige gagnait, puis reculait quand le maillage s'affinait.
- **Cause 2, les taches brunes :** la pente des textures s'ajoutait à la normale de la neige pour les pixels de moins de 2 m, sans que sa part perdue compte de loin. Elle changeait la neige de plusieurs points sur les 600 derniers mètres : −7 points sur les pentes douces, la roche apparaissant dessous, +8 sur la roche raide.
- **Règles, dans `principes.md` :** les décisions voient les formes du relief à toute hauteur ; un effet des textures sur une limite ne s'efface avec le pixel que s'il garde la moyenne.
- **Changements :**
  - la grille fine reste active pour les décisions jusqu'aux mailles de face de 3,4 m, où le maillage porte l'octave de 13,5 m sur ses 4 mailles : de 2 km à 160 m, elles voient le même relief ;
  - la lumière ne la prend qu'à partir de mailles de 20 m, comme avant, `FINE_LIGHT_MIN_CELL` ;
  - la neige ne tient compte que de la pente du terrain ; la hauteur des textures la déplace toujours, `HeightBlend`, centrée.
- **Mesures sur la tache, parts vues, de 2 km à 100 m :**

| Part vue | 2 km | 1,5 km | 1,2 km | 1 km | 800 m | 600 m | 400 m | 250 m | 150 m | 100 m |
|---|---|---|---|---|---|---|---|---|---|---|
| Neige, avant | 8,3 | 6,1 | 10,3 | 11,9 | 8,9 | 6,2 | 5,3 | 6,6 | 7,9 | 9,1 |
| Neige, après | 8,3 | 7,4 | 8,6 | 9,4 | 9,4 | 9,5 | 10,2 | 8,0 | 8,0 | 9,2 |
| Roche, avant | 3,1 | 1,3 | 1,1 | 2,4 | 2,6 | 3,6 | 6,7 | 7,7 | 8,4 | 9,2 |
| Roche, après | 3,1 | 5,8 | 8,4 | 9,2 | 9,8 | 8,9 | 9,1 | 8,2 | 8,4 | 9,1 |
| Sol, avant | 51,3 | 56,0 | 53,6 | 48,3 | 49,6 | 53,2 | 52,7 | 47,9 | 44,2 | 43,0 |
| Sol, après | 51,3 | 50,0 | 45,8 | 42,3 | 43,8 | 45,7 | 44,7 | 45,5 | 44,2 | 43,0 |

- **Sur neuf autres lieux, enneigés et herbeux,** le plus grand écart d'une part vue de 2 km à 100 m, avant → après :
  - neige : −34,7° −122,3° 7,4 → 5,9 ; −47,5° 124,2° 4,3 → 4,3 ; −67,2° 32,5° 13,8 → 7,1 ; −41,9° 64,0° 7,0 → 2,2 ;
  - roche, éboulis, herbe ou sol : −67,2° 32,5° 21,2 → 13,6 ; collines, 0,89° 133,68°, 40,7 → 24,1 ; −41,9° 64,0° 5,1 → 2,1 ; −20,2° 79,9° 8,1 → 6,3 ; 12,8° −111,1° 5,4 → 6,0 ; deux prairies, 32,3° 17,9° et 45,1° −161,7°, plates à 2 points près, avant comme après.
  - De loin, rien ne change : descentes de 1 500 à 60 km identiques au dixième, site de la roche et Afrique du Nord.
- **Vue d'en haut,** `journal/2026-10-24-approche.jpg` : la tache garde ses lobes de 2 km à 300 m ; avant, ils fondaient à 1 km.
- **Scintillement, avec / sans lissage :** 1,6 km 0,27 / 1,80 → 0,30 / 1,96 ; 1,3 km 0,25 / 1,70 → 0,28 / 1,97 ; 530 m 0,35 / 2,23 → 0,28 / 1,83 ; 143 m 0,22 / 1,11 → 0,21 / 0,99 ; crête enneigée 0,08 / 0,46 → 0,07 / 0,41 ; dune inchangée. Total des six vues −2 %.
- **Coût :** de 160 à 770 m du sol, la grille fine en double précision, +3,5 ms de calcul, 0,5 → 4,1 ms, GPU au repos. En simple précision, +1 ms, mais ses normales tremblent deux fois plus quand elles éclairent : 0,66 / 4,13 à 530 m.
- **Banc de qualité, 30 lieux, contre la base du jour :** aucun p95 ne se dégrade de plus de 10 % ; au plus +0,2 dB, le trou de la neige à 12 m. Mutation p95 0,080 → 0,077 à 200 m, +6 % à 800 m, +3 % à 3 km ; segments droits inchangés.
- **Essayé et écarté :**
  - compter dans `SlopeSpread` les octaves que la normale perd vraiment, sous 4 mailles et par la différence centrée, au lieu de celles sous la maille : roche plate sur la tache, mais la rugosité par type de terrain déborde ailleurs, écart de 5 à 12 points à 12,8° −111,1°, et la roche d'orbite gagne 50 % ;
  - la pente perdue des textures de roche dans la même quadrature 2D que les pentes cachées, au lieu d'un `SpreadStep` sur une norme : dérive du sol des replats divisée par deux sur la roche raide, mais roche vue d'orbite +65 à +95 % ;
  - les versants cachés comptés à 8 °C : neige de loin deux fois trop abondante sur la tache ;
  - la grille fine éclairant aussi toute l'approche : lumière et décisions sur le même relief, détail fin +1,5 à +4 dB à 800 m, mais des traits fins le long des crêtes, le trou p95 à 800 m +1 dB sur la neige et le sol, au-delà des 10 %, et le scintillement +40 % à 1,3 km.
- **Reste :**
  - la roche monte encore de 3 à 9 % sur la tache entre 2 et 1,2 km, de 4 à 17 % sur des collines jusqu'à 400 m : les octaves de 13,5 et 27 m manquent à la grille fine au-dessus de 500 m, et `SlopeSpread` ne les compte pas. Il faut une rugosité mesurée, pas tirée du type de terrain ;
  - sur la roche raide, les replats couverts passent de 47 à 33 % du sol à l'approche, à −67,2° 32,5°, `RockShares` ;
  - les vues de diagnostic tirent leurs seuils d'un hachage biaisé : un poids de 0,25 donne 23 %.
- **Pour revenir :** `FineMinCell = 20.0` ; `normal = normalize(normal - gHeightBlend * textureSlope)` avant la neige, sur `SlopeOf(dot(normal, up))`.
- Tests en vol : `tools/tests/2026-10-24-approche.txt`. Le soleil n'était pas relevé : celui du démarrage y est couché, les quatre dernières vues ont un soleil levé.

## 2026-10-24 · Le halo de l'objectif

**Réglage :** `GLARE_STRAYLIGHT` = 0,3, nouveau.

- **Symptôme :** le soleil, 45 750 fois un blanc au soleil, n'était qu'un point blanc de 6 pixels ; rien ne disait sa force.
- **La règle :** le halo d'un point décroît en s E / θ², la loi lointaine de l'œil (CIE, Vos 2003) et des objectifs. Linéaire, il conserve l'énergie : l'image garde 1 − W de sa lumière, le halo répartit W. Pas de seuil, avant la courbe de tons (`recherche-halo.md`).
- **Changements :**
  - une pyramide de demi-images, du pixel à l'écran, sommée à poids égaux : exactement la loi en 1/θ², sans échelle ; `GlareDown.hlsl`, `GlareUp.hlsl` ;
  - fondue dans l'image composite avant le lissage temporel ; `ToneMap.hlsl` inchangé ;
  - le disque du soleil montre la part du pixel qu'il couvre : à bord franc, son énergie variait de −10 à +5 % d'un pixel à l'autre, et le halo aurait pulsé.
- **Le réglage :** s = 0,3, un objectif récent mesuré en ISO 18844 (Koren 2018). Essayé à 1,7, un voile de 1 % : une boule blanche de 4,3° autour du soleil haut, pas discrète. Pas le halo de l'œil, s ≈ 10 : l'œil du spectateur ajoute déjà le sien à ce que montre l'écran.
- **Mesures,** `tools/banc_halo.py` :
  - le soleil vu de l'espace, sans air : le halo suit la loi à 0,91 à 1,06 près de 2° à 20°, +24 % au bord de l'écran ;
  - soleil à 36° : +33 % de luminance à 2,4°, +9 % à 5°, +3 % à 10° ;
  - autour de la neige : sous un niveau de la sortie 8 bits, comme la loi le prédit ;
  - tremblement inchangé, 0,05 / 0,39 contre 0,05 / 0,40 aux montagnes ; pompage du soleil d'un pixel à l'autre, 0,4 % ;
  - coût, 0,17 ms en 1280 × 720.
- **À juger en vol :** `tools/tests/2026-10-24-halo.txt`, à comparer avec `MYPLANETENGINE_NO_GLARE=1`.
- **Reste :** pas de halo pour un soleil hors champ ; tramage de la sortie 8 bits, dont le dégradé du halo montre les paliers ; l'auréole de l'air trop faible près du soleil.

## 2026-10-24 · L'exposition et la courbe de tons

**Réglages :** `EXPOSURE_COMPENSATION` = 1 IL et `FILM_CONTRAST` = 1,5, nouveaux ; la courbe de Khronos PBR Neutral retirée. Recherche, choix et mesures : `recherche-tons-exposition.md`.

- **Symptôme :** les images ne se lisent pas comme des photos : sol terne, ombres claires, peu de relief ; au soleil bas, l'image s'éteint.
- **Cause :** aucune exposition, une radiance de 1 donnait le blanc ; une courbe sans pied, l'identité sous 0,76. Sol médian 0,096 en luminance linéaire, contre 0,266 sur les photos ensoleillées ; 0,023 au soleil bas.
- **Règle, dans `principes.md` :** l'écran montre la lumière, pas le cadrage.
- **Changements, `ToneMap.hlsl` :**
  - l'exposition suit la lumière du jour sous la caméra, un posemètre incident tourné vers le soleil, lu dans les tables de l'atmosphère ; une carte grise face au soleil y montre sa réflectance, plus 1 IL ; après le coucher, la lumière du coucher ;
  - la courbe des photorécepteurs, x^a / (x^a + k^a), sur le canal le plus fort, par la carte grise : pente 1,5 dans les ombres, 1,23 au gris ; les teintes ne tournent pas, les hautes lumières blanchissent ;
  - le lissage temporel garde la lumière de la scène, avant l'exposition ; un halo s'ajoute à la ligne marquée, avant la courbe ;
  - les vues de diagnostic ne passent ni par l'exposition ni par la courbe : leur blanc vaut 1 ;
  - `D3DApp.cpp` : la passe finale reçoit les tables de l'atmosphère.
- **Mesures, `tools/banc_tons.py` :**
  - jour, sol p5, p50, p95 : 0,036, 0,096, 0,262 → 0,095, 0,254, 0,520 ; photos 0,011, 0,266, 0,571 ;
  - soleil bas, sol médian 0,023 → 0,224 ; vers le soleil, le ciel s'écrête sur 9 à 16 % de l'image ;
  - tourner la caméra : le même ciel et le même sol à 0,02 IL près, quand l'image entière varie de 1,4 à 2,1 IL ;
  - descente de 1 500 km à 30 m : sans saut, 0,07 IL au plus d'une hauteur à la suivante ;
  - tremblement avec lissage 0,16 → 0,18 et 0,09 → 0,12, pour une image 1,5 fois plus claire ;
  - banc de qualité, 12 lieux : la neige gagne 3 à 6 dB de détail fin ; le reste à 0,2 dB près ; au-delà de 10 %, le trou d'échelle p95 de la neige à 800 et 3 000 m, +0,5 dB, et la mutation p95 à 12 et 200 m, +19 et +11 % ; la répétition du sable à 50 m, 0,12 → 0,28, un p95 qui bascule d'un crop à l'autre.
- **Essayé, pas gardé :** le posemètre à plat, soleil bas plus clair que midi ; le ciel propre de la carte, 0,1 à 0,5 IL de moins au soleil bas, pour une table de plus.
- **Vues en vol :** `tools/tests/2026-10-24-tons.txt` ; avant et après sur sept vues, `images/tons-avant-apres.jpg`.
- **Reste :** les ombres portées, 1,3 IL d'ombres contre 4,6 sur les photos ; vers un soleil bas, brume et ciel restent clairs ; d'orbite au-dessus de la nuit, le jour au loin est surexposé.

## 2026-10-24 · Les ombres portées du relief

**Réglage :** `HORIZON_STEP` = 0,05, nouveau. Nouvelle passe `Horizon.hlsl`, nouveau fichier `Shadows.hlsli`, vue de diagnostic `sun`, banc `tools/banc_ombres.py`.

- **Symptôme :** aucune ombre portée ; au soleil bas, les fonds de vallée restent éclairés, les plans ne se découpent pas (`recherche-profondeur-atmospherique.md`, 3.6).
- **Choix :** l'horizon du relief vers le soleil, par sommet, marché sur les hauteurs du maillage ; interpolé comme un angle, la part du disque solaire prise au pixel. État de l'art et raisons : `recherche-ombres-relief.md`.
- **Changements :**
  - la passe `Horizon.hlsl`, après le relief des matériaux : pour chaque sommet visible, la marche le long du grand cercle vers le soleil, pas de 5 % de la distance, arrêt quand rien ne peut plus dépasser l'horizon et le bas du disque ;
  - le maillage calcule aussi les sommets dont l'ombre peut tomber à l'écran (`ShadowSweep`) ;
  - le pixel prend la part du disque au-dessus de l'horizon interpolé, élargie de l'étalement de l'horizon qu'il couvre, fois l'ombrage de Smith du relief plus fin que la maille ;
  - seule la lumière directe change.
- **Mesures,** détail dans `recherche-ombres-relief.md`, image `images/ombres-avant-apres.jpg` :
  - scintillement, avec / sans lissage, jamais au-dessus d'avant sur quatre vues de montagne au soleil bas : par exemple 0,18 / 0,98 → 0,16 / 0,92 sur un massif à 8 km ;
  - descente de 50 km à 200 m, lumière directe moyenne sur le même sol : écarts de +5, +4, +2, −6 % d'une hauteur à la suivante, contre +7, +7, +13, −10 % pour l'éclairage d'avant ; sur un fond de vallée, le bord de l'ombre reste en place de 8 km à 200 m ;
  - l'ombrage de Smith retenu sur cette mesure : sans lui, le loin est 3 à 8 % trop clair ;
  - coût de calcul +0,2 à +1,4 ms, le pire le soleil dans le dos ; rendu inchangé au bruit près ;
  - pas de 2 % : mêmes ombres qu'à 5 %.
  - banc de qualité, 10 lieux, soleil vers 50° : inchangé à 0,0 dB près, mutation comprise.
- **Essai écarté :** le ciel caché par les versants, quatre marches de plus par sommet : +6 ms.
- **Reste :** le ciel caché, avec des marches bornées par le plus haut sommet du maillage ; des contours d'ombre arrondis de loin ; les rayons de soleil ; des photos de montagne au soleil bas pour juger.

## 2026-10-24 · Les rayons de soleil : l'air à l'ombre du relief · tag `piste/rayons-soleil`

**Réglages :** la hauteur d'ombre, nouvelle, sur une grille de 512 × 512 (`SunShadow.hlsli`), filtrée par `MESH_BAND_LIMIT` ; `MAX_TERRAIN_HEIGHT` passe de `Terrain.hlsli` à `PlanetSettings.hlsli`.

- **Symptôme :** à contre-jour, le soleil derrière une montagne, l'air devant elle restait baigné de lumière ; aucun rayon, aucune ombre dans la brume (`recherche-profondeur-atmospherique.md`, 3.7).
- **Cause :** l'atmosphère ne savait pas que le relief cache le soleil ; seul l'horizon de la sphère coupait sa lumière.
- **Changements** (`recherche-rayons.md`) :
  - la hauteur d'ombre : l'altitude au-dessus de laquelle une colonne d'air voit le soleil. Un champ en deux dimensions, sur une grille polaire autour de la caméra, toutes directions ;
  - chaque image, le relief sur la grille, puis une marche vers le soleil sur la sphère, d'une demi-cellule par pas, d'après la carte d'ombre du terrain de Red Dead Redemption 2 ;
  - chaque pas du rayon de vue lit la hauteur d'ombre à ses bouts et en son milieu, et garde la part éclairée de sa longueur. Seule la lumière du soleil diffusée une fois est coupée : l'ombre garde la lumière du ciel ;
  - une règle dans `principes.md` : l'ombre du relief est une hauteur d'ombre, pour l'air comme pour le sol, et rien ne vient de l'écran.
- **Mesures :** `tools/tests/2026-10-24-rayons.txt`, planche par `tools/banc_tests.py` ; `images/rayons-avant-apres.jpg`.
  - Soleil caché par un pic : la lueur devant lui disparaît, la caméra est dans son ombre. Soleil juste au-dessus des crêtes : faisceaux et coins d'ombre de chaque aiguille dans la brume. Soleil de côté ou dans le dos, désert, orbite : peu ou pas de changement.
  - Coût, minimum sur les images, RTX 4070 Ti, 1280 × 720 : relief 0,50 à 0,67 ms, marche 0,27 à 0,37 ms, lecture 0,02 à 0,09 ms ; en tout 0,8 à 1,1 ms de calcul en plus.
  - Tremblement avec/sans lissage, trois vues de rayons : 0,04 / 0,34 → 0,06 / 0,46 ; 0,06 / 0,40 → 0,06 / 0,44 ; 0,04 / 0,30 → 0,05 / 0,34. L'air seul : 0,01 / 0,05 → 0,01 / 0,09, aux bords des faisceaux ; l'image plus sombre pèse aussi dans le chiffre.
  - Rotation de 1° : l'air seul, ramené sur l'image précédente, s'écarte de 0,41 avec l'ombre, 0,43 sans. Rien ne rampe quand la caméra tourne.
  - Une grille de 256 × 256 abaissait les aiguilles : l'air devant le haut d'un pic restait au soleil et tremblait. 768 × 768 ne change presque plus rien, pour 2,4 ms.
- **Reste :** une seule marche avec les ombres portées, tag `piste/ombres-relief`, qui marchent déjà l'horizon de chaque sommet du maillage : la même boucle donnerait la hauteur d'ombre, la grille et ses passes disparaîtraient. Puis la pénombre du soleil, et des pas plus serrés près de la caméra sur les rayons du ciel.
- **Retour arrière :** le commit `565e598` ; ou `shadow.on = false` dans `AtmospherePass.hlsl`, qui retire l'ombre de l'air sans retirer ses passes.
## 2026-10-24 · Les nuages, étapes 1 et 2 : la carte du temps et la couche 2D · commit `6a88d33`

**Réglages :** nouveau fichier `Clouds.hlsli`. `CLOUD_GAIN` = 0,79 ; nébulosité 0,58 + 0,40 × (humidité − 0,6) + 0,16 au front polaire, de 19 à 56° ; nuages hauts 0,05 + front + 0,3 × convection ; humidité relative 0,3 + 0,55 × humidité + 0,15 × fronts ; `CLOUD_EXTINCTION` = 45 /km ; `CLOUD_BEAM_SHARE` = 0,2775 ; `CLOUD_CELL_KM` = 5 ; `HIGH_CLOUD_THICKNESS` = 1,5 km. Vue de diagnostic `clouds`. Plan : `recherche-nuages.md`, étapes 1 et 2.

- **La carte, étape 1 :** sur le climat existant, partagé avec le sol (`ClimateNoise`, `SeaLevelTemperature`), deux bruits de plus. Elle décide par colonne la nébulosité, la convection, le type, la base de Lawrence, le brouillard quand la base touche le sol, le sommet, les cirrus.
- **Un seul spectre, sans trou d'échelle :** le temps et les nuages sont les octaves d'un même bruit de gain 0,79, le k^-5/3 des champs nuageux. Avec les gains du plan, 0,5 et 0,55, rien entre 30 et 300 km : des nuages tous de la même taille, en peau de léopard. C'est la règle de `principes.md`, chaque échelle couverte.
- **Les couches, étape 2 :** une coquille épaisse par étage, de la base au sommet ; un rayon y voit la première cellule qu'il rencontre, la part du pixel, puis la moyenne de la région derrière elle. Lumière à deux flux, éclairée par nos tables ; le sommet des cumulus éclairé selon sa pente.
- **Composée avec l'air :** l'intégration de l'atmosphère est coupée aux traversées des couches ; l'air sous les nuages n'est éclairé que de ce qu'ils laissent passer.
- **Le sol :** l'ombre des deux couches, moyenne sur le pixel et le disque du soleil ; sous un plafond, le ciel renvoyé vers le haut et la lumière du soleil diffusée vers le bas.
- **Hooks :** une ligne dans `AtmospherePass.hlsl` (`CloudyScattering`) ; l'ombre et la lumière diffuse dans `PixelShader.hlsl` (`CloudShadeAt`) ; le nom de la vue dans `D3DApp.cpp`.

**Fraction nuageuse par bande de 10°,** vue `clouds` d'en haut, 32 vues par bande, contre MODIS, Terra et Aqua en moyenne annuelle (King et al. 2013 ; Stubenrauch et al. 2013), lu sur leurs profils à 5 points près :

| Bande | 90-80 S | 80-70 S | 70-60 S | 60-50 S | 50-40 S | 40-30 S | 30-20 S | 20-10 S | 10-0 S |
|---|---|---|---|---|---|---|---|---|---|
| Nuages | 79 % | 77 % | 78 % | 82 % | 74 % | 61 % | 46 % | 53 % | 65 % |
| MODIS | 45 % | 55 % | 82 % | 88 % | 82 % | 68 % | 55 % | 55 % | 62 % |

| Bande | 0-10 N | 10-20 N | 20-30 N | 30-40 N | 40-50 N | 50-60 N | 60-70 N | 70-80 N | 80-90 N |
|---|---|---|---|---|---|---|---|---|---|
| Nuages | 72 % | 56 % | 48 % | 71 % | 71 % | 70 % | 77 % | 71 % | 87 % |
| MODIS | 68 % | 57 % | 50 % | 57 % | 68 % | 75 % | 76 % | 78 % | 76 % |

- **Le globe :** 64,8 % contre 65,1 %.
- **La loi de la carte,** moyennée sur les climats possibles, tient MODIS à 8 points près sur toutes les bandes, hors calotte antarctique.
- **Notre planète s'en écarte de plus de 10 points sur deux bandes :** 30-40° N, +13,5, où son climat est humide, 58 % d'humidité contre 38 % attendus ; 80-90° N, +11. Ce sont ses propres climats : les nuages suivent l'humidité qui fait ses forêts et ses déserts.
- **Le profil est vérifié deux fois :** une réplique exacte de la carte en Python, sur une grille de 1°, rend les mêmes bandes à 2 points près.
- **La calotte antarctique,** 90-70° S, +34 et +22 : une glace à 3 km, l'air le plus sec de la Terre, qu'une colonne au niveau de la mer ne peut pas connaître avant la carte du relief de l'étape 4.

**Descente :** la part de nuages d'une zone de 60 km, de 1 500 à 60 km, sur 8 lieux.
- **La moyenne des lieux :** de 53,0 à 52,6 %, écart maximal 0,5 point.
- **Chaque lieu :** à 2,4 points près, ce que permet le tirage d'une zone de 25 pixels à 1 500 km.

**Aspect,** sur les tests en vol, comparé de mémoire à la base des photos de l'ISS, aucune photo n'étant téléchargée :
- **ce qui tient :** d'orbite, des systèmes de centaines de km aux bords effilochés, des cumulus épars sur des régions entières, des trous où l'océan sombre porte l'ombre des nuages. Des nuages 10 fois plus clairs que l'océan, comme sur les photos. Un plafond gris, plus clair vers le soleil ; le brouillard ; des nuages orange au coucher.
- **ce qui manque :** les cumulus en pop-corn nets, avec leur ombre portée sur le pont ; les rues de nuages et les cirrus effilochés, faute de vent ; les tours de cumulonimbus.

**Coût,** images alternées avec et sans nuages dans le même processus, GPU au repos, trois passages identiques à 0,01 ms près :

| Hauteur | 2 000 km | 400 km | 160 km | 30 km | 10 km | 1 km | 300 m, sous un plafond |
|---|---|---|---|---|---|---|---|
| Rendu sans nuages | 1,12 ms | 0,50 ms | 0,45 ms | 0,57 ms | 0,60 ms | 0,64 ms | 0,69 ms |
| Nuages | +1,90 ms | +1,86 ms | +1,49 ms | +1,68 ms | +1,79 ms | +1,97 ms | +1,40 ms |

- **L'ombre et la lumière diffuse sur le sol en prennent 0,9 à 1,8 ms :** la passe du terrain, déjà lourde, les calcule pixel par pixel. Les couches dans le ciel, 0,3 à 0,7 ms.
- **Deux fois le budget du plan,** 0,3 à 0,9 ms.
- **Les pistes :** la carte du temps cuite au démarrage, celle de l'étape 4, retire les bruits du climat et du temps, la moitié des octaves ; l'ombre calculée dans une passe d'écran plutôt que dans celle du terrain.

**Reste :**
- **Dans la couche, tout est plat :** pas de tours ni de flancs ; la caméra dans le nuage voit un brouillard uniforme, avec un mince trait clair à l'horizon. C'est l'étape 3, le volume.
- **Les cirrus ne sont pas effilochés,** il faudrait le vent ; ils se voient gris par-dessous.
- **L'air sous les nuages est ombré par la moyenne de la région ;** le sol ne renvoie pas sa lumière vers leur base.
- **Le lissage temporel** reprojette les nuages à la profondeur du terrain, ou à l'infini sur le ciel : traînées possibles de près, en vol rapide.
- **Le coût,** ci-dessus.

- **Pour revenir :** `IntegrateScattering` à la place de `CloudyScattering` dans `AtmospherePass.hlsl` ; `clouds.sun` et `clouds.sky` retirés de l'éclairage dans `PixelShader.hlsl`.
- Image : `journal/2026-10-24-nuages.jpg`. Tests en vol : `tools/tests/2026-10-24-nuages.txt`. Banc : `tools/banc_nuages.py`.

## 2026-10-24 · La brume de la couche limite

**Réglages :** `VISIBILITY_KM` = 40, nouveau, d'où se déduisent `MIE_EXTINCTION` et `MIE_SCATTERING` ; `HAZE_TOP_KM` = 2, `HAZE_TOP_WIDTH_KM` = 0,3, nouveaux, au lieu de `MIE_SCALE_HEIGHT` = 1,2 ; `MIE_ASYMMETRY` 0,8 → 0,7.

- **Symptôme :** pas de profondeur ; les plans successifs ne se séparent pas (`recherche-profondeur-atmospherique.md`).
- **Cause :** l'air de la démo de Bruneton, presque pur, une épaisseur optique d'aérosols de 0,005 contre 0,19 sur les continents : 217 km de visibilité, quand un beau jour ordinaire en donne 20 à 60. Et sa brume, une exponentielle de 1,2 km depuis la mer, ne laissait que 4 % d'elle-même à un sol à 4 km.
- **Changements :**
  - un seul réglage, la visibilité au niveau de la mer ; l'extinction des aérosols s'en déduit (Koschmieder), 90 % en diffusion ;
  - la brume remplit la couche limite jusqu'à 2 km, puis s'éclaircit sur 0,3 km : la bande vue d'avion, l'air clair au-dessus ; à 40 km, une épaisseur optique de 0,17 ;
  - les aérosols colorés selon Ångström, exposant 1,3, et un halo vers le soleil moins serré ;
  - chaque pas du rayon, à l'écran comme dans les tables du démarrage, montre la moyenne de l'air qu'il traverse : vue d'orbite, la brume était comptée 4,6 fois trop faible et aurait changé d'aspect à la descente.
- **Mesures :** descente verticale sur un désert de 400 km à 1,5 km, couleur au centre régulière, sans saut. Vue en vol, essai A contre B, `tools/tests/2026-10-24-profondeur.txt` : « globalement, ça marche plutôt bien ».
- **Reste :** la couche suit le niveau de la mer, pas le sol : un haut plateau reste dans l'air pur ; il faudra une carte du relief régional. Puis les ombres portées du relief, l'exposition et la courbe de tons, le halo, les rayons.

## 2026-10-25 · Objets de proximité : le détail du sol, une recette par sol · tag `piste/objets-proximite`

**Réglages :** `PEBBLES`, `GRASS_ROCKS`, `TUFT_OCTAVES`, `TUFT_COVER`, `OBJECT_CREST`, `OBJECT_CLUMPS`, nouveaux ; `OBJECT_HOLLOW` retiré ; `OBJECT_OCTAVES` dès 1,5 cm ; `DEBRIS_ABUNDANCE` 0,05 ; 0,25 ; `OBJECT_BURIAL` 8 à 40 %, 3 mm au moins. Spec : `spec-objets-proximite.md`, étape 2.

- **L'avis en vol,** deux photos à l'appui : « plus rendu des roches sur un thème éboulis que réellement des détails du sol » ; des cailloux au bas de chaque ravin ; « posés au milieu de nulle part ».
- **Les photos comptées :** une tache de premier plan d'environ 3,7 m², son échelle tirée de l'horizon de la mer et d'un appareil à 1,6 m ; les touffes et les rochers de l'herbe, à l'échelle des touffes.
- **Changements :**
  - une recette par sol : cailloux et graviers sur le sable et le sol nu ; touffes partout dans l'herbe, rochers à demi enfouis par taches ; pierres des éboulis ;
  - les touffes d'herbe, une classe nouvelle sur la même grille, 40 brins générés, la couleur de l'herbe du sol ; un second dessin indirect ;
  - une octave de 1,5 cm, un enfouissement de 3 mm au moins ;
  - les éboulements au pied des seules pentes de plus de 35 à 45°, plus au fond des creux.
- **Mesures,** par m², le moteur puis la photo :
  - sable, cailloux de 1,5 à 25 cm par octave : 54, 12, 2,6, 0,45 ; 30 et plus, 16, 6, 0,5 ; 6,7 % du sol, 6 à 8 % ;
  - herbe : 9 touffes sur 34 % du sol, 6 à 15 sur 30 à 60 % ; rochers de 20 cm à 1 m dans les taches, 1,1 contre 2 ;
  - creux : 10 % de blocs de 50 cm et plus au lieu de 40 % ;
  - aucun objet flottant ; arrivées à 0,07 px au plus sur 8 800 ; tremblement jamais plus que sans objets ;
  - placement 0,4 à 0,75 ms sous charge, dessin 0,04 à 0,23 ms.
- **Tests en vol, remplacés,** à 1,7 m, regard devant : sable près de la côte, crête herbeuse, sol nu, pente d'éboulis.
- Image : `journal/2026-10-25-objets-sol.jpg`, les photos à gauche.

## 2026-10-24 · Objets de proximité : la forme du sol et les taches · tag `piste/objets-proximite`

**Réglages :** `OBJECT_LANDFORM`, `OBJECT_HOLLOW`, `OBJECT_GATHER`, `OBJECT_PATCHES`, nouveaux ; `OBJECT_FOOT` retiré ; `DEBRIS_ABUNDANCE` 0,05 ; 0,25 ; 0,01. Spec : `spec-objets-proximite.md`, étape 1 ter.

- **L'avis en vol :** trop uniforme ; des blocs au fond des ravines, de petites pierres dans les pentes, presque rien sur les crêtes, les hauts de falaise et les plaines.
- **Les références :** les fragments de roche des sols, Poesen et Lavee ; les blocs des chenaux, Shobe et al. ; les regs, Wood et al. ; l'agrégation des semis de pierres, Hickory Run, Mars, Ryugu.
- **Changements :**
  - la forme du sol, lue sur 16 m sur le sol exact : pente au-dessus, courbure, pente des bords ;
  - les débris s'amassent où le sol s'adoucit sous 10 à 20°, au pied d'une pente raide ou au fond d'un creux encaissé, avec une abondance de 0,25 ;
  - les crêtes n'en gardent que 10 % ;
  - chaque source sa loi de Golombek et Rapp : petites pierres où les débris passent, blocs où ils s'amassent ;
  - des taches de 8 à 64 m, vides sur 58 % du sol, qui changent le nombre, pas les tailles.
- **Mesures, avant puis après,** couverture du sol :
  - creux 1,65 → 1,09 %, dont 40 % de blocs ; plat 1,63 → 0,19 % ; crêtes 1,27 → 0,06 % ;
  - pentes de 20 à 35°, 4 à 8 % de blocs au lieu de 14 à 22 % ;
  - la moitié des pierres de 25 cm et plus dans 9 % des cellules de 20 m, contre 25 % ;
  - aucun objet flottant ; tremblement jamais plus que sans objets ;
  - placement 14 à 17 % du calcul du terrain sous charge, contre 12 à 14 %.
- **Tests en vol, remplacés :** fond de ravine, ravine vue de 30 m, pied de pente, crête, plaine, pente d'éboulis.
- Image : `journal/2026-10-24-objets-formes.jpg`, avant à gauche.

## 2026-10-24 · Objets de proximité : des cailloux, leurs tailles et leurs pentes

**Réglages :** `DEBRIS_ABUNDANCE`, `OBJECT_REPOSE`, `OBJECT_FOOT`, `OBJECT_BURIAL` remplacent `SCREE_OBJECTS` et `ROCK_OBJECTS`. Spec : `spec-objets-proximite.md`, étape 1 bis.

- **L'avis en vol :** trop d'objets sur les pentes raides, où ils ne tiendraient pas ; trop de rochers moyens ; des blocs à demi enfouis dans les parois, « mauvaise intégration ».
- **La ligne, écrite dans la spec :** cette piste fait les cailloux, des débris posés ; la roche en place et son relief sont la piste de la géométrie.
- **Le banc d'abord :** `tools/banc_objets.py recensement`, chaque cellule de 23 lieux enregistrée par le moteur, gardée ou non ; objets par m² et part couverte par octave de taille, par bande de pente, au pied des pentes.
- **Les références :** la loi de Golombek et Rapp, mesurée sur Terre et sur Mars ; l'angle de repos des talus, 33 à 37° ; le tri par la chute, les gros au pied.
- **Changements :**
  - plus aucun objet sur la roche nue ;
  - trois sources de débris : éboulis, pied des pentes de plus de 35 à 45°, sol nu et désert ;
  - leur abondance partagée par la loi de Golombek et Rapp ;
  - rien au-delà de 38° pour les plus petits, un degré de moins par octave ;
  - enfouis de 30 % dans un sol meuble, de 8 % sur la roche, jamais moins de 1 cm ;
  - la lumière renvoyée par le sol sur les faces à l'ombre.
- **Mesures, avant puis après :**
  - au-delà de 40°, de 9 à 11 % du sol couvert à rien ;
  - au pied des parois, de 1,7 % à 15 %, dont 29 % de blocs ;
  - sur les éboulis, les tailles de 25 cm à 1 m de 7,8 % à 2,7 % ; 2,1 petits cailloux par m² pour 0,03 pierre de plus de 50 cm ;
  - sur le sol nu et le désert, de rien à 3 %, la loi à chaque octave ;
  - aucun objet flottant de 200 à 1,5 m ; tremblement jamais plus qu'avant les objets.
- **Coût :** un sol exact de plus par candidat ; sous charge, placement 13 à 24 % du calcul du terrain, contre 7 à 27 % ; dessin jusqu'à 0,6 ms sur un reg, des formes trop fines pour quelques pixels.
- **Pour revenir :** le commit `1a74c9e`.
- **Tests en vol, remplacés :** éboulis, talus au pied d'une paroi, blocs tombés, reg, champ de pierres, pied de paroi vu de 20 m.
- Image : `journal/2026-10-24-objets-cailloux.jpg`, avant à gauche.

## 2026-10-24 · Objets de proximité, étape 1 : pierres et blocs

**Réglages nouveaux :** `SCREE_OBJECTS`, `ROCK_OBJECTS`, `OBJECT_OCTAVES`, `OBJECT_PIXELS`, `OBJECT_CELLS`. Spec : `spec-objets-proximite.md`.

- **La demande :** des petits cailloux, des touffes, des rochers qui sortent un peu du sol ; placés selon les bruits, mais pas glissés image par image comme le maillage ; un niveau de détail classique, qui apparaît à proximité ; un terrain d'abord, puis tous.
- **Le terrain choisi : les éboulis et la roche.**
  - Des objets statiques, sans vent ni transparence ;
  - deux matériaux qui existent, dont `GroundMaterials` donne la part partout ;
  - des silhouettes dures, le test le plus sévère du flottement et du pop.
- **Le système, un pour toutes les classes à venir :**
  - **une place fixe :** une cellule de la grille cartésienne de la planète, une octave de tailles par niveau, de 6 cm à 2 m ; place, taille, forme, tirage viennent du hachage de la cellule ;
  - **une densité :** la part du sol que couvre chaque octave, par matériau, multipliée par la part visible du matériau, filtrée à la cellule, sur le sol exact ;
  - **une apparition :** de 6 à 9 pixels de large, l'objet grandit depuis son pied enfoui, là seulement où les mailles font moins de 1,5 fois sa largeur ;
  - **deux passes de calcul :** une légère sur 112 × 112 cellules par octave, une lourde sur la liste des candidats vus, puis un seul dessin indirect ;
  - **huit formes,** générées au démarrage : une icosphère coupée par des plans, arêtes adoucies ; la couleur du sol de roche à sa place, la photo de la roche et sa tuile fine dans le repère de la pierre, la lumière du sol.
- **Le flottement :** le pied sur le sol exact, enfoui d'un quart de sa hauteur sur les éboulis, de moitié sur la roche. Sur trois lieux, de 200 à 1,5 m : aucun objet ne flotte, écart à l'écran sous 0,6 px, 1,75 px au plus près du sol.
  - **La règle des mailles,** mesurée : sans elle, des blocs de 2 m vus de 200 m, dans des mailles de 4 m, flottaient de 84 cm.
  - **Trouvé en chemin :** complexplanet a un plancher de précision près du sol. Déplacer le point de 1 mm change son altitude jusqu'à 16 mm à 2,6 km d'altitude, 1,2 mm à 1 km : l'arrondi des flottants dans la somme des octaves. Le maillage le porte aussi ; une piste pour le tremblement près du sol.
- **Le pop :** sur des descentes de 40 à 3 m, 1 670 objets arrivés à l'écran avec au plus 0,06 px de large ; entiers, ils arrivaient à 7,5 à 8,6 px en médiane, 15,6 px au plus.
- **Le tremblement :** jamais plus qu'avant sur cinq vues d'éboulis et de roche, un peu moins près du sol, 3,59 → 3,49 avec lissage.
- **Banc de qualité,** 30 lieux contre la référence : trous de la roche −0,8 à −2,7 dB au p95, répétition −0,1 ; détail fin de la roche à 12 m −4,6 dB en médiane, les blocs ajoutant du contraste moyen ; ailleurs moins de 0,4 dB.
- **Coût,** GPU au repos : placement 0,31 à 0,43 ms, dessin 0,01 à 0,08 ms, pour un calcul du terrain de 2 à 5 ms. Une passe unique coûtait 40 à 80 % du calcul du terrain, les candidats vus épars dans les vagues.
- **Outils :** la vue de diagnostic `objects`, les mesures du flottement dans le titre, `tools/banc_objets.py`. `RockColor` passe dans `Materials.hlsli`, `BorderPoint` dans `Mesh.hlsli`.
- **Pour revenir :** `SCREE_OBJECTS.z = ROCK_OBJECTS.z = 0`, ou le commit `cfba322`.
- Image : `journal/2026-10-24-objets.jpg`, avant à gauche. Tests en vol : `tools/tests/2026-10-24-objets.txt`.

## 2026-10-24 · Une seule roche dans le code

**Réglages retirés :** `STRATA_DIP`, `STRATA_FOLD`, `STRATA_WANDER`, `STRATA_PLATE_RISE`, `STRATA_PLATE_TILT`, `STRATA_FAULT_ZONE`, `MASSIVE_TILE`, `MATERIAL_PARALLAX`, `PARALLAX_DEPTH`, `PARALLAX_STEPS`. Tranches de matériaux : 12 → 7.

- **Pourquoi :** l'essai roche-photo, validé en vol, laissait du code mort marqué `EXPERIMENT` : familles, tuiles dessinées, marches de la colonne, décalage de la photo, failles.
- **Retiré, image identique :** les familles de roche, `RockFamilies` ; les générateurs du granite, du basalte et des badlands et leurs tranches ; les failles, `StrataPlates` ; les anciens pendage, plis et ondulation ; la tuile de 64 m et le décalage dans `GeneratedTexture`.
  - Vérifié sur 12 vues de 160 km à 16 m : identiques au pixel près.
  - Seule la photo de dessus est retirée au sort : sa tranche a changé de numéro, et le numéro tire la place de ses copies.
- **Retiré, image changée :** la parallaxe de la roche, `RockParallax`, avec la tuile dessinée de 64 m et le relief de la colonne qu'elle seule lisait encore. Elle décalait la photo selon un relief que les pixels ne montrent plus.
  - Aspect inchangé à l'œil : les copies de la photo se placent un peu autrement de près.
  - Scintillement sans lissage −3 à −5 % sur quatre vues de roche, inchangé avec.
  - Rendu −0,65 à −0,93 ms, 12 à 22 %.
- **Banc de qualité, mêmes 30 lieux, avant puis après le nettoyage :** roche à 0,3 dB près de 50 à 800 m ; à 12 m, détail fin médian −1,0 dB, p5 +2,1 dB, trou −0,4 dB ; les autres matériaux ne bougent pas.
- **Contre l'ancienne roche dessinée,** la référence du banc : −3 à −6 dB de détail fin. Ce sont ses corniches, craquelures et traits que le banc comptait comme détail. Comparée en vol sur 7 vues du banc où la roche photo est la plus floue, `tools/tests/2026-10-24-detail-roche.txt` : la roche photo jugée meilleure sur 6, l'ancienne sur une, à 12 m, pour ses corniches. Les corniches de près relèvent de la géométrie de proximité, à part (`geometrie.md`).
- **Palette de tests :** un test sans soleil reprend celui du démarrage ; il gardait celui du test précédent, parfois de nuit.
- **Docs :** `spec-parallaxe.md` passe dans `log/` ; `spec-roche-organique.md` dit ce qui en reste ; `tools/bandes_materiaux.json` n'a plus qu'une roche.
- **Code :** 522 lignes de moins.

## 2026-10-24 · Le papier peint des parois

**Réglages :** `ROCK_BANDS`, pente de 0,05 à 0,24 par octave ; nouvelle tranche `MATERIAL_ROCK_TOP`, la photo `marble_cliff_05`. Sur l'essai roche-photo v12, commité tel quel avec.

- **Symptôme,** en vol : de 100 à 400 m, les parois tapissées du même petit motif de la photo, égal partout, pire sur les grandes faces, `2828.4 -0.03727 118.14886 -9.7 176.8`. Et un dallage sur une paroi vue en rasant, `1758.2 0.00182 118.14986 -10.9 81.8`.
- **Cause :** au-dessus de la tuile de 12,8 m, rien ne variait.
  - Les bandes de 8 à 64 m portaient 0,05 de pente par octave, copiée des éboulis : le quart de celle de la photo.
  - La règle lointaine compte pourtant ces octaves, `STONE_SLOPE_SIGMA` sur treize octaves. De près, elles manquaient.
  - La photo de paroi couvrait aussi la roche douce.
- **Règles, dans `principes.md` :** les bandes prolongent la pente de la photo ; une photo garde l'orientation de sa prise de vue.
- **Changements :**
  - `ROCK_BANDS` porte 0,24, la pente par octave de la photo : ombres, facettes et replats de 8 à 64 m.
  - La roche de moins de 45° prend `marble_cliff_05`, le même marbre pris de dessus. La limite suit `SlopeShares` et le bruit des limites : les deux photos se rencontrent par plaques.
  - Le banc de qualité mesure l'étalement d'un crop à l'autre : clarté, contraste, contraste relatif, photos réelles en regard. `uniformite.py` y est fondu.
- **Mesures, crops de roche des vues, avant puis après, en dB :**

| Vue | Étalement de la clarté | Du contraste | Du contraste relatif |
|---|---|---|---|
| `4363.2 16.26802 …` | 1,82 → 2,10 | 4,65 → 4,38 | 2,08 → 1,94 |
| `4376.2 16.42557 …` | 0,16 → 0,22 | 1,28 → 1,71 | 1,45 → 2,07 |
| `2828.4 -0.03727 …` | 0,88 → 0,95 | 1,52 → 1,07 | 2,05 → 2,55 |
| `1758.2 0.00182 …` | 0,34 → 0,58 | 1,23 → 1,15 | 1,62 → 1,85 |
| Photos réelles | 0,44 à 2,32 | 0,71 à 11,5 | 0,80 à 15,6 |

- **Banc de qualité, 30 lieux :** les p95 de la roche baissent, trou à 50 et 200 m de 3,8 et 4,1 à 2,9 et 2,5 dB, répétition de 50 à 800 m de 0,15 à 0,32 avant, 0,10 à 0,12 après. Le reste bouge dans le bruit du tirage, au plus +8 % contre v12, le trou du sable à 50 m. Étalement de la clarté de la roche à 200 m de 0,38 à 0,52 dB, à 800 m de 0,59 à 0,43 : sur des lieux tirés au hasard, le défaut n'est que partiellement réglé.
- **Scintillement, sans lissage :** inchangé sur deux vues ; +7 à +12 % sur trois autres, `2828.4`, `1022.9`, `4363.2`. Avec le lissage, à 0,01 près partout.
- **Ce que le test a montré :** la paroi « douce » de la vue `1758.2` monte de 25 m pour 10 m, 68°. La règle d'orientation y garde la photo de face, comme sur les trois vues signalées, toutes au-delà de 60°. Elle sert la roche douce : sommets de buttes, épaulements.
- **Essayé et écarté :**
  - le bruit de clarté à spectre égal par octave, même écart : aucun effet mesuré ;
  - le même deux à trois fois plus fort : clarté du sommet `4376.2` de 0,16 à 0,34 dB, au prix de taches sales ;
  - le contraste des photos modulé de lieu en lieu : contraste relatif proche de la médiane des photos, mais scintillement +20 % sur deux vues et trou du sable à 12 m +56 %.
- **Reste :** la clarté du sommet `4376.2` sous les photos, son relief au-delà de 64 m étant celui du maillage, lisse ; le dallage de la vue `1758.2` ; la parallaxe lit encore la tuile de 64 m effacée par l'essai.
- **Pour revenir :** `ROCK_BANDS.z = 0.05` ; `face = 1.0` dans `GroundMaterials`.
- Image : `journal/2026-10-24-papier-peint.jpg`, avant à gauche : `2828.4`, `4376.2`, la falaise orange, la paroi rasante. Tests en vol : `tools/tests/2026-10-24-papier.txt`.

## 2026-10-24 · Une seule roche, la photo

**Réglages :** essai roche-photo, marqué `EXPERIMENT` dans le code. `RockFamilies` rend la roche litée seule ; plus de tuile dessinée de 64 m sur la roche ; `ROCK_BANDS`, nouveau ; strates en couleur seulement ; `STRATA_SLOPE` = 0,4 remplace `STRATA_DIP`, `STRATA_FOLD` et `STRATA_WANDER` ; palette des grès aux trois quarts de son contraste.

- **Symptômes,** en vol, tous de la même famille :
  - craquelures du granite en traits arrondis, `4242.2 16.27025 123.15986 16.1 -166.5` ;
  - traits au feutre sur le granite, `4363.2 16.26802 123.16025 23.7 -111.3` et `4376.2 16.42557 123.15934 7.3 63.0` ;
  - strates arc-en-ciel des badlands, `4074.5 16.27626 123.18392 10.8 155.2` ; courbes de niveau, `1941.7 0.00280 118.14145 -0.2 156.6` ; corniches claires et noires, `2828.4 -0.03727 118.14886 -9.7 176.8` ;
  - traînées étirées, `1415.0 -9.54451 102.98665 4.2 -98.9`.
  - Jugées belles, à garder : la roche litée et sa photo, `1022.9 -0.23076 118.41645 7.3 61.0`, `2922.5 3.15497 110.91028 20.7 50.3`, `487.8 -0.05421 112.67541 0.6 -25.5`.
- **Cause commune :** des structures dessinées à la main, fissures, sillons, rigoles, marches, rideaux sombres, qui se lisent comme un dessin ; des couches parfaitement planes là où la région n'avait ni pendage ni plis. La photo, elle, passait. Plutôt que corriger chaque dessin, on les retire.
- **Changements :**
  - une seule roche, la photo de paroi, partout : granite, basalte et badlands dessinés ne s'affichent plus ;
  - plus de tuile dessinée de 64 m sur la roche : des bandes de détail à la place, comme pour les autres matériaux ;
  - la photo n'est plus décalée le long des strates : sur une pente parallèle aux couches, le décalage l'étirait sans fin. Tournée par les couches perturbées, elle tourbillonnait : elle reste de niveau ;
  - strates en couleur seulement : leurs marches traçaient des traits continus sur des faces entières ;
  - une seule perturbation des couches, de 8 km à 4 m, partout, sa pente moindre de 15 % à chaque octave vers le mètre ; elle remplace pendage, plis et ondulation, qui ne touchaient que certaines régions ;
  - l'épaisseur des couches varie le long de la paroi, jusqu'au biseau : deux sinus de 23 et 7,3 m le long des couches, aux phases tirées de 32 à 256 m, leurs pentes à 0,9 au plus pour qu'aucune couche ne se replie.
- **Mesures, banc de qualité de l'étape « couleur seulement » contre la référence, mêmes 30 lieux :** roche +1,7 à +4,2 dB de détail fin de 50 à 200 m, répétition en baisse de 0,1 ; aucun autre matériau ne bouge ; mutation inchangée.
- **Validé en vol** le 2026-10-24, avec le papier peint de l’entrée ci-dessus : « franchement pas mal ».
- **Reste :** retirer le code mort, familles, générateurs dessinés, marches et corniches des strates, décalage de la photo, réglages remplacés ; `RockParallax` lit encore la tuile de 64 m retirée.

## 2026-10-24 · Plus de patchs de pixels de loin : un bruit de gradient partout

**La géographie est retirée.** Déserts, prairies, neiges et sortes de roche changent de place. Le relief ne bouge pas : complexplanet et `LibNoise.hlsli` sont intacts.

- **Symptôme,** en vol : de loin, le sol en mosaïque de carrés de quelques km aux teintes plates, comme une texture basse résolution, `160551.2 1.12602 114.67687 31.2 -88.7` et `300000.0 -15.00000 50.00000 50.0 0.0`.
- **Cause :** la clarté du sol, `m.local.z`, un `Fbm3` de bruit de valeur.
  - Un bruit de valeur est plat autour de chaque point de sa grille.
  - Ses octaves, sur des grilles emboîtées, alignent leurs plateaux.
  - Au-delà de 50 km, le pixel n'en garde que deux ou trois : les plateaux se voient.
  - Écartés : l'alpha du rendu HDR, carrés inchangés en 32 bits ; la grille fine et le grain : carrés inchangés sans eux. Sans la clarté, plus de carrés.
- **Règle :** un bruit ne montre jamais sa grille (`principes.md`).
- **Changement :** `ValueNoise3` devient `Noise3`, trois bruits de gradient pour un hachage par coin.
  - Ses bits sont posés en mantisses, sans conversion : le coût reste proche.
  - Il est ramené à l'écart type du bruit de valeur : écart type du `Fbm3` 0,195 contre 0,194, queues à 3 % près. Les seuils restent valables.
  - Tous les champs y passent : climat, géologie, clarté, limites de neige et de roche, plages, strates, lentilles, herbe, rides.
- **Lieux déplacés,** vus à 2 km du sol :
  - `banc_visuel` : le désert (26° N, 45° E) devient prairie, l'herbe (15° S, 50° E) devient désert, la roche (14,96° S, 119,99° E) perd sa neige ;
  - `banc_roche` : le canyon (11,05° S, 50,07° E) devient désert ; sec, granite et badlands (20° S, 125° E) deviennent verts, le granite devient grès orange ;
  - `banc_cretes` : la crête sèche (24,3° S, 129,75° E) perd sa neige ;
  - `banc_hybride` : le sable (26° N, 45° E) devient prairie, les éboulis (31,16° N, 8,59° E) perdent leur neige ;
  - `banc_descente` : la chaîne d'Afrique du Nord (32,3° N, 17,9° E) n'a plus de neige ; le site de la roche (15° S, 120° E) ne change pas ;
  - tests : « Sol nu en montagne » devient prairie à roche orange, « Désert de 50 m à 1 km » devient prairie, les craquelures perdent de la roche, « Orange et vert » devient gris ;
  - inchangés : « Neige », « Paroi litée », « Orbite », la roche rouge.
- **Mesures :**
  - **Le bruit seul,** segments droits de 20 px et plus, par 1 000 px de terre : 160 km 10,2 → 4,9, 300 km 2,7 → 1,2, 200 km 6,6 → 3,2, 600 km 0,5 → 0,1 ; à 3 et 10 km, inchangés.
  - **Le rendu,** segments de 12 px et plus : −20 % à 160 km, −27 % à 300 km, −23 % à 200 km.
  - **Mêmes statistiques, lieux déplacés,** sur 60 lieux tirés au hasard : neige 22 → 20 %, roche 2,8 → 3,1 %, éboulis 4,0 → 4,2 %, herbe 35 → 32 %, sable 30 → 37 %.
  - **Scintillement :** de loin, inchangé. Vue de neige : 0,51 → 0,64 sans lissage. À 564 m : 1,20 → 3,84, car le versant de sable ridé est devenu de la roche. Le bruit seul ne scintille pas : 0,07 au plus.
  - **Coût :** de loin, rien. Près du sol, +0,4 ms à 564 m et +1,4 ms à 2,6 km, minimum de 8 rendus sous charge.
  - **Banc de qualité,** 30 lieux retirés, contre les photos (trou p95 3,5 dB, répétition p95 0,18) : trous de la roche à 200 et 800 m, 5,1 et 4,8 dB sur 33 et 23 crops ; répétition du sable à 12 m 0,47, les rides, 0,55 avant ; le reste au niveau des photos ou dessous. Les segments longs du banc montent à 800 et 3 000 m avec les nouveaux lieux ; sur les mêmes vues, ceux du bruit seul baissent, de 166 à 116.
- **La référence du banc est remplacée** par cette mesure : l'ancienne portait sur des lieux qui ont changé.
- **Pour revenir :** l'ancien `ValueNoise3` à la place de `Noise3`, dans `Materials.hlsli` (commit `3f899da`).
- **Tests :** `tools/tests/2026-10-24-pixels.txt`.

## 2026-10-24 · Des craquelures et des rigoles organiques

- **Symptômes,** en vol : des craquelures en segments droits aux angles vifs, `4242.2 16.27025 123.15986 16.1 -166.5` ; un versant de badlands couvert de rides verticales régulières, du velours côtelé, `4285.0 16.27172 123.16603 4.8 -159.1`.
- **Causes :** les fissures du granite, les cristaux et les pierres suivent les bords d'un Voronoi, droits par construction ; les rigoles des badlands, toutes les 1,3 à 2,7 m, à profondeur presque égale, sur toute la tuile de 64 m. Deux structures d'un trait uniforme (`principes.md`).
- **Changement :** la grille du Voronoi est déformée par un bruit périodique d'une demi-maille et d'un huitième, ses bords ondulent, à l'endroit commun à ses trois usages ; une fissure de granite s'élargit, se resserre et s'interrompt le long d'elle-même ; les rigoles vont et viennent par plaques de 8 à 32 m et se rassemblent en ravines d'environ 16 m.
- **Mesures :** banc de qualité sans régression nette, le trou d'échelle de la roche à 12 m de 3,0 à 3,4 dB, sous le niveau des photos ; scintillement inchangé.
- **Coût :** aucun, les tuiles sont générées au démarrage.

## 2026-10-24 · Correctif : les cercles sur les océans, vus de loin

**Réglage :** l'image HDR en flottants 32 bits, au lieu de 16 (`HdrFormat`, `D3DApp.h`).

- **Symptôme,** en vol : de très loin, les océans couverts d'anneaux concentriques autour de nombreux centres, `24622915.3 46.51198 60.64808 79.2 78.2`. Nets de 10 000 à 30 000 km, pâles dès 2 000 km, sur les terres aussi. Présent depuis `jalon/05-atmosphere`.
- **Cause :** l'atmosphère reçoit la distance du terrain dans l'alpha de l'image HDR, en demi-flottant : des pas de 16 km au-delà de 16 384 km. Le rayon s'arrêtait jusqu'à 8 km avant le sol et perdait, selon le pixel, l'air le plus dense. Ces paliers forment des cercles autour du nadir, repliés en moiré par les pixels.
- **Correctif :** la distance garde le mètre à toute distance. Règle nouvelle dans `principes.md`.
- **Mesures :** cercles disparus de 2 000 à 30 000 km sur deux régions ; parts de neige et de mer en descente identiques au dixième ; banc de qualité sur 30 lieux : tous les p95 à 0,1 dB près de la référence, mutation identique ; près du sol, image identique à 1/255 près ; coût dans le bruit de mesure, moins de 0,1 ms.
- **Pour revenir :** `HdrFormat` en `DXGI_FORMAT_R16G16B16A16_FLOAT`.
- Image : `images/cercles-avant-apres.jpg`. Détails : `spec-rendu-lointain.md`. Tests en vol : `tools/tests/2026-10-24-cercles.txt`.

## 2026-10-23 · Le sol nu, un matériau oublié

**Réglage, nouveau :** `SOIL_BANDS`, de 50 cm à 64 m.

- **Symptôme,** en vol : de larges zones brun clair floues à toute distance, en montagne et ailleurs, `2588.6 32.10988 10.53312 9.8 49.1`.
- **Cause :** du sol nu, trop sec pour l'herbe et trop humide ou froid pour le sable : aucun matériau, la seule couleur du biome, aucune texture. Les bancs ne le mesuraient pas.
- **Changement :** le sol nu prend la photo du gravier sableux et ses bandes de détail ; le banc et le validateur ont une classe `soil`.
- **Mesures, mêmes 30 lieux :** détail fin du sol nu +4,7 à +5,4 dB de près, trous d'échelle −1 à −2,5 dB ; rien d'autre ne bouge ; scintillement inchangé.
- **Essayé et retiré :** le grain du relief sous la maille ; sans gain, il coûtait un point de roche en descente et 14 % de scintillement sur une vue.
- **Pour revenir :** `soilAmount` à 0 dans `GroundMaterials`.
- Détails : `spec-texturage-universel.md`, étape 3.

## 2026-10-23 · Correctif : la géologie de nouveau par sommet

- **Symptôme,** en vol : de l'orbite, à 1 228 km, `1228341.6 0.13844 115.66320 56.0 -33.3`, les régions de roche couvertes de taches rondes de granite gris, de basalte noir et de grès orange.
- **Cause :** la géologie passée au pixel le 2026-10-23, avec les strates et les lentilles. Filtrée par la maille, elle s'effaçait de loin ; au pixel, ses octaves de 5 à 40 km se voient, et le partage des familles de roche les découpe en taches.
- **Correctif :** la géologie revient aux sommets ; les strates et les lentilles restent aux pixels, c'étaient elles qui faisaient glisser les bandes. Vérifié : orbite comme avant, bandes toujours immobiles à l'approche.
- **Reste à revoir :** le partage des familles en taches rondes, qui se verrait dès que la géologie serait filtrée au pixel. Les vraies régions géologiques sont des ceintures.

## 2026-10-23 · Les bandes de détail : neige, sable, herbe, éboulis

**Réglages, nouveaux :** `SNOW_BANDS`, `SAND_BANDS`, `GRASS_BANDS`, `SCREE_BANDS` : longueurs d'onde, pente et couleur par octave.

- **Changement :** une seule fonction, `DetailBands`, comble les échelles vides de chaque matériau, mesurées par `tools/valide_bandes.py` : une octave de bruit par longueur d'onde, à pente et couleur égales.
- **Pourquoi :** la neige n'avait aucun détail ; le sable rien de 50 cm à 16 m ; l'herbe deux creux.
- **Effet :** la neige prend une surface ; le sable comble son creux au niveau de ses scans réels ; les trous d'échelle du banc reviennent au niveau des photos.
- **Mesures :** neige +30 dB sous 1 m ; sable +18 dB à 4 m ; herbe +2 à +5 dB ; tremblement, répétition et mutation inchangés.
- **Pour revenir :** les quatre réglages à une pente et une couleur nulles.
- Détails : `spec-texturage-universel.md`, étape 3.

## 2026-10-23 · Des bandes immobiles, un granite sans grillage, la doc rangée

**Réglages :** `STRATA_WANDER` = 2,5 m, nouveau ; `MASSIVE_TILE` = 8 m, nouveau ; `STRATA_PLATE_RISE` = 0 et `STRATA_PLATE_TILT` = 0, au lieu de 20 m et 0,12.

- **Les bandes ne glissent plus à l'approche :** géologie, décalage des strates et lentilles sont calculés dans les pixels, filtrés par leur taille. Filtrés par la maille, 13 pixels, leurs octaves apparaissaient à vue.
- **Les strates ondulent davantage,** 2,5 m d'écart type sur 4 à 256 m, au lieu de 0,8 m sur 4 à 64 m.
- **Le granite n'a plus de grillage :** ses grandes fractures se montrent par tronçons. Granite et basalte retrouvent leur tuile de 8 m.
- **Les failles sont coupées :** elles arrêtaient les bandes net, les « sparadraps ». Leur code reste, fixé sur la planète, pour la règle des arrêts.
- **La doc :** 10 specs passées dans `log/`, un index `README.md`, `AGENTS.md` et sa règle du log ; la méthode change, `spec-texturage-universel.md`.
- **Mesures :** tremblement avec lissage égal ou meilleur ; descente de la roche inchangée.
- **Pour revenir :** le tag `piste/bandes-cassees`.

## 2026-10-23 · Les bandes cassées

**Réglages, nouveaux :** `STRATA_PLATE_RISE` = 20 m, `STRATA_PLATE_TILT` = 0,12, `STRATA_FORMATION_CONTRAST` = 0,3.

- **Changement :** des failles presque verticales cassent les strates en plaques d'environ 128 m, relevées et inclinées chacune ; les formations prennent la teinte de groupes cinq fois plus épais. Couleur seulement, la géométrie ne change pas.
- **Pourquoi :** de 300 m à 1 km, des bandes continues et régulières faisaient tissu.
- **Effet :** des bandes interrompues et décalées, des couleurs par grandes masses ; restent les joints sombres entre bancs, en tronçons.
- **Mesures :** tremblement avec lissage 0,43 → 0,42 et 0,23 → 0,26 ; rendu +0,1 à 0,3 ms ; descente de la roche inchangée.
- **Pour revenir :** `STRATA_PLATE_RISE` = 0, `STRATA_PLATE_TILT` = 0, `STRATA_FORMATION_CONTRAST` = 1.
- Détails : `spec-parois-minerales.md`.

## 2026-10-23 · La géométrie à complexplanet, la photo de falaise sur la roche

**Réglages :** `MATERIAL_RELIEF` = 0 et `WALL_RELIEF` = 0, au lieu de 1 ; `ROCK_TILE` = 64/5 m, au lieu de 8 m.

- **La règle :** complexplanet est la source de vérité de la géométrie. Toute surcouche est classée et documentée dans `geometrie.md` ; un remplacement vit sur une piste taguée.
- **La géométrie de proximité est désactivée,** relief des matériaux et gradins : le rendu se règle d'abord sur complexplanet seul.
- **Le filtre d'érosion est mis de côté,** tag `piste/erosion-filtre`.
- **La photo de falaise :** `marble_cliff_04` de Poly Haven, CC0, une paroi de 12,7 m de face, sur la tuile de la roche litée. Toutes ses longueurs d'onde, 30 % de sa teinte.
- **Effet :** une matière fracturée et cannelée sur les parois ; de 300 m à 1 km, les bandes de strates dominent encore.
- **Mesures :** tremblement avec lissage 0,40 → 0,43 au pire ; coût et descente de la roche inchangés.
- **Pour revenir :** les deux réglages à 1, `ROCK_TILE` à 8 m et la ligne `marble_cliff_04` retirée de `kScans`.
- Détails : `spec-parois-minerales.md`.

## 2026-10-23 · Parois en gradins, options 1 et 2

**Réglages, nouveaux :** `WALL_RELIEF` = 1, `WALL_MAX_CELL` = 16 m, `WALL_SLOPE` = 0,55 à 1, `WALL_CLIFF` = 0,35, `WALL_REPOSE` = 0,67.

- **Changement :** les bancs durs de la colonne stratigraphique font des falaises, les bancs tendres des replats à l'angle d'éboulis. Le maillage porte ce qu'il peut sans trembler, les pixels éclairent le reste. Ravines, contreforts et masses de granite dans le maillage.
- **Pourquoi :** les parois de 15 à 150 m étaient lisses et peintes de bandes ; le défaut était la géométrie.
- **Effet :** vraies falaises en gradins sur les parois très raides ; pentes de 45° presque inchangées ; rien sous l'angle d'éboulis.
- **Mesures :** tremblement avec lissage de 0,37 à 0,61 sur la paroi la plus raide, +0,03 à +0,05 ailleurs ; descente de la roche inchangée.
- **Coût :** +0,2 ms.
- **Pour revenir :** `WALL_RELIEF` = 0.
- Détails : `log/spec-parois.md`.

## 2026-10-22 · Le sable en photo

**Réglages :** `SAND_TILE` = 64/24 m, au lieu de 8 m ; `kScanKeep` = 0,5 m dans `D3DApp.cpp`.

- **Changement :** la tuile du sable est un scan photo CC0, `sandy_gravel_02` de Poly Haven, chargé au démarrage par WIC à son échelle réelle. Il reste un facteur de moyenne 1, recoloré par le biome. Il ne porte que les longueurs d'onde de moins de 50 cm ; le grain fin et le reste restent procéduraux. La roche reste procédurale.
- **Pourquoi :** la recommandation de l'essai hybride, les sols meubles aux scans, la roche au procédural.
- **Effet :** un sol de désert à graviers et cailloux de près, au lieu d'un sable uniforme. Rien ne change au-delà de 50 m.
- **Mesures :** réalisme contre `aerial_sand` ×7,66 → ×6,54, spectre 8,8 → 5,2 dB ; descente du sable et de l'herbe inchangée de 800 à 8 km ; tremblement inchangé avec lissage.
- **Coût :** aucun mesurable au rendu ; +1,1 s au démarrage en Debug.
- **Pour revenir :** retirer la ligne de `kScans` et remettre `SAND_TILE` à 8 m.
- Détails : `log/spec-hybride-scans.md`.

## 2026-10-22 · Couleurs du sol tirées de la vraie Terre

- **Changement :** la couleur du sol vient d'un tableau température × humidité mesuré sur Blue Marble et sur les normales TerraClimate, `BiomePalette.hlsli`, généré par `tools/palette_biomes.py`. Il remplace les teintes choisies à la main : désert, steppe, prairie, forêt, toundra.
- **Effet :** déserts presque inchangés ; régions humides tempérées moins vertes, plus olive.
- **Coût :** aucun mesurable.
- **Pour revenir :** le commit précédent.
- Détails : `spec-photos-par-echelle.md`.

## 2026-10-22 · Principes et correctif de l'effet « feutre » des strates

- **`principes.md`, nouveau :** on corrige des règles, pas des cas. Il recense les règles établies et les bancs qui les vérifient. Ce fichier fait référence.
- **Strates :**
  - marches des plans en loi au cube, la plupart à peine visibles ;
  - bords qui ondulent ;
  - bancs qui s'interrompent sur 16 à 128 m, seuil élargi selon la règle universelle ;
  - couloirs continus et irréguliers, plus discrets.
- **Mesures :** tremblement en légère baisse ; roche en descente inchangée ; coût à remesurer, GPU partagé.
- Détails : `spec-roche-organique.md`.

## 2026-10-22 · Parallaxe du relief de la roche

**Réglages :** `MATERIAL_PARALLAX` = 1, `PARALLAX_DEPTH` = 1,5 m, `PARALLAX_STEPS` = 8.

- **Changement :** les pixels suivent leur rayon de vue dans le relief de la roche que le maillage ne porte pas encore, tuile de 64 m et colonne stratigraphique, et prennent les matériaux au point touché.
- **Effet :** la corniche a sa profondeur dès 11 m, au lieu de surgir avec la géométrie.
- **Coût :** +0,8 à +1,0 ms de près, rien de loin. **Tremblement :** légèrement plus, 0,17 → 0,22 à 11 m.
- **Outil :** les bancs rendent sans afficher la fenêtre et ne prennent plus le focus ; le titre va dans `<capture>.txt`.
- **Pour revenir :** `MATERIAL_PARALLAX = 0`.
- Détails : `log/spec-parallaxe.md`. Retirée le 2026-10-24.

## 2026-10-22 · Correctif : les matériaux ne dépendent plus du relief porté par le maillage

- **Symptôme :** une corniche changeait de matériau dans les derniers mètres de l'approche ; sa couleur disparaissait, puis revenait sous une autre forme.
- **Cause :** les décisions se prenaient sur la normale du maillage, qui porte de plus en plus du relief des matériaux en approchant.
- **Correctif :** décisions sur la normale du terrain seul, calculée sur les sommets d'avant la passe de relief, et sur la pente entière des textures. La lumière seule retire la part portée par le maillage.
- **Mesure :** la bande du replat reste à sa place de 11 m à 5 m ; tremblement inchangé ; descente inchangée.
- Détails : `log/spec-relief-reel.md`.

## 2026-10-22 · Fusion de la roche organique, sous la règle universelle

**Réglage :** `STONE_SLOPE_SIGMA` = 0,6.

- **Fusion :** la branche `roche-organique`, PR EtienneLescot/MyPlanetEngine#10, apporte familles de roche, colonne stratigraphique, pendage, plis, replats et usure. En cas de conflit, le travail de cohérence a gardé la priorité : règle universelle, projection triplanaire, correctifs du relief.
- **Converti à la règle universelle :**
  - **familles :** leurs limites sur le bruit de géologie s'élargissent de ce que la maille en cache ;
  - **roche tendre :** ses limites de pente passent par `SlopeShares` ;
  - **replats :** une part, par quadrature sur les pentes cachées et la pente perdue de la texture, `RockShares`.
- **Pourquoi les replats :** tels quels, ils se décidaient sur la pente douce du maillage de loin, et couvraient toute la roche. Elle tombait à 0 % de 800 à 90 km. Maintenant, la roche vue reste à 9–13 % de 800 à 8 km, et la roche avant replats à 18–22 %.
- **Sommets :** `FaceVertex` garde la rugosité et reçoit le relief porté.
- **Coût :** les tuiles ne sont plus lues au-delà d'un pixel de deux tuiles, et la quadrature des replats saute près de la caméra. Rendu +0,1 à +0,8 ms par rapport à avant la fusion.
- **Tremblement :** roche rouge 2,1 → 0,57 ; vue du constat 0,23 → 0,35.
- **Neige :** inchangée au banc de descente.
- **Vue de diagnostic :** `rockall`, la roche, replats compris.

## 2026-10-22 · Correctif : lames, aiguilles et scintillement du relief des matériaux

**Réglages :** `CREASE_MIN_CELL` = 2 m ; `RELIEF_NORMAL_CELLS` = 32 ; projection triplanaire.

- **Neige :** dans la passe de relief, elle ne se décide plus sur la pente des textures. Elle basculait d'un sommet à l'autre et dressait des lames.
- **Projection :** des poids triplanaires continus remplacent la biplanaire à la puissance 8, qui basculait près de la diagonale du cube.
- **Normale de la passe de relief :** sur 32 mailles au lieu de 4.
- **Mesure,** banc de tremblement : roche rouge 10,1 → 2,1, crête enneigée 1,7 → 0,55. Plus de lames ni d'aiguilles sur les vues signalées.
- **Coût :** +0,2 à 0,3 ms de calcul.
- Détails : `log/spec-relief-reel.md`.

## 2026-10-22 · Correctif : scintillement de près, précision de l'arrondi des crêtes

- **Symptôme :** après le jalon 13, gros scintillements et formes aberrantes près du sol.
- **Cause :** le retrait de l'excès moyen de l'arrondi des crêtes. Sa forme exacte perdait sa précision en simple précision pour les petits arrondis, donc près de la caméra.
- **Correctif :** la série de cet excès sous un arrondi de 0,4.
- **Mesure,** banc de tremblement sur les deux positions signalées : 1,26 → 0,37 et 2,37 → 0,16 avec lissage, mieux qu'avant le jalon.
- **Nouveau banc :** `tools/banc_tremblement.py`, qui reprend une position exacte de la barre de titre.
- Détails : `spec-rendu-lointain.md`.

## 2026-10-22 · Jalon 13 : la même planète de l'orbite au sol · tag `jalon/13-coherence-distance`

**Le jalon :** testé en vol par l'utilisateur, « une avancée considérable ». La planète ne change plus d'apparence en descendant : les montagnes gardent leur taille, la neige et la roche gardent leur place et leur part.

- **Le vrai relief sous la maille, d'orbite :** une grille quatre fois plus fine que la face, recalculée à chaque image, donne au pixel la normale et l'altitude du relief que le maillage ne porte pas.
- **Le relief garde sa hauteur moyenne :** l'arrondi des crêtes perd son excès moyen. Les montagnes ne gonflent plus de 300 à 1 000 m vers 200 km de vue.
- **Une règle pour toutes les limites entre matériaux :** un pixel montre la moyenne d'une limite sur ce qu'il couvre. Les bruits restent les mêmes à toute distance, et ce que le pixel n'en montre pas élargit la limite.
- **Les outils de mesure :** le banc de descente, `tools/banc_descente.py`, et les vues de diagnostic, `MYPLANETENGINE_VIEW`. Chaque matériau se mesure de 800 km à quelques km.
- **Mesures, de loin à près :**
  - roche 18 → 22 %, contre 0 → 17 % ;
  - neige 12 → 16 %, contre 6 → 45 → 26 % ;
  - altitude moyenne sans bosse ;
  - mer, plage, éboulis et herbe stables.
- **Ce qui reste ouvert :**
  - la grille fine ne couvre que la face, pas les anneaux ;
  - un écart de 400 m du relief sur une chaîne ;
  - une rugosité mesurée plutôt que tirée du type de terrain ;
  - de près, le tremblement de la roche et l'aspect de briques vers 100 m.
- Détails : `spec-rendu-lointain.md`.

## 2026-10-22 · Règle universelle des limites entre matériaux

**Réglages :** `OCTAVE_SLOPE` = 0,16 ; rugosités par type de terrain 1 / 0,6 / 0,4 / 0,1 ; orientation des versants cachés à 4 °C par unité de pente.

- **La règle :** un pixel montre la moyenne d'une limite sur ce qu'il couvre. Les bruits restent les mêmes à toute distance, et ce que le pixel n'en montre pas élargit la limite.
- **Appliquée à** la neige, la roche, les éboulis, la plage, la mer, l'herbe et le sable, et à la couleur de la toundra.
- **Mesures, de loin à près :** roche 18 → 22 % contre 0 → 17 % ; neige 12 → 16 % ; mer et plage stables.
- **Vues de diagnostic :** `MYPLANETENGINE_VIEW` = snow, rock, elevation, spread, scree, grass, sand, beach, wet ou sea.
- **Coût :** +0,10 à +0,28 ms.
- Détails : `spec-rendu-lointain.md`.

## 2026-10-22 · Mutation en descente : relief et neige

- **Le relief garde sa hauteur moyenne :** l'arrondi des crêtes, `CreaseAbs`, perd son excès moyen. Les montagnes ne gonflent plus de 300 à 1 000 m vers 200 km de vue.
- **La neige suit l'altitude de la grille fine,** et un bruit de température de 2 km au plus, le même à toute distance. Ce que le pixel n'en montre pas élargit la limite des neiges.
- **Mesure,** banc de descente sur la chaîne d'Afrique du Nord : neige de 6 → 45 → 26 % à 8 → 12 % de 400 à 60 km.
- Détails : `spec-rendu-lointain.md`.

## 2026-10-22 · Roche organique, étape 5 : l'usure

- **Lentilles :** un champ lent, bruits de 256 et 128 m calculés par sommet, contre lequel chaque plan de stratification a son seuil. En dessous, sa marche s'efface : les bancs s'interrompent en lentilles. Les formations, rarement.
- **Arêtes arrondies :** contremarches et replats 2,5 fois plus larges pour la roche tendre.
- **Coût :** une famille sous 5 % n'est plus calculée, les autres se partagent sa place.
- **Mesure finale, GPU libre, rendu :** +0,26 ms au constat, +0,32 ms au canyon à 100 m, +0,53 ms au site sec à 100 m. Calcul inchangé. Le site sec est au budget de 0,5 ms à 0,03 ms près : la pression de registres des quatre familles déroulées, même non prises.
- **Essayé sans gain :** deux familles choisies par indice, `[branch]`, boucle non déroulée, hachage plus court.
- Détails : `spec-roche-organique.md`.

## 2026-10-22 · Roche organique, étape 4 : coulées et roches tendres

**Réglages :** `STRATA_FOLD` 0,4 → 0,25.

- **Quatre familles :** basalte en coulées, granite massif, calcaire et grès lités, badlands tendres là où la région est sèche et ferrugineuse. Transitions étroites entre deux familles.
- **Coulées :** bancs de 3 à 20 m, chacun terminé par un large replat, son talus ; tuile de 64 m en colonnes prismatiques. Basalte presque noir.
- **Tendre :** bandes de 2 à 15 m très colorées, bancs de 0,8 à 3 m ; tuile de 64 m en rigoles serrées ; roche nue dès 25° de pente.
- **Pendage et plis dosés par le bruit de géologie** au lieu d'un bruit régional propre : moins cher par sommet.
- **Allègements :** hachage 1D pour les plans de stratification, recherche plus courte, sorties rapides au loin.
- **Mesure :** coût total depuis le départ +0,2 à +0,35 ms au rendu, estimé sous un GPU chargé à 80 % par une autre instance. Crêtes sans pics.
- Détails : `spec-roche-organique.md`.

## 2026-10-22 · Roche organique, étape 3 : familles massive et litée

- **Deux familles,** choisies par le bruit de géologie : granite, massif ; calcaire et grès, lités. Elles se mêlent entre deux régions.
- **Litée, une colonne stratigraphique** calculée au pixel sur l'altitude moins le décalage de l'étape 2 : formations de 10 à 60 m teintées du blanc au rouge, bancs de 4 à 24 m, durs en replats, tendres en pente. Les bancs filent d'un bout à l'autre de la paroi et ne se répètent jamais. La tuile de 64 m ne garde que diaclases, couloirs, stratification oblique et rideaux.
- **Massive, deux tuiles granite** de 8 m et 64 m : bosses, dômes, écailles courbes, grandes fractures, stries d'eau. Couleur gris clair.
- **Corrigé en route :** zigzags d'éclairage, l'altitude de la spline lissée ne suivait pas le relief retranché ; dents de scie, effacement des bancs par plan.
- **Mesure :** coût +0,1 à 0,2 ms au rendu par rapport à l'étape 2. Crêtes sans pics.
- Détails : `spec-roche-organique.md`.

## 2026-10-22 · Roche organique, étape 2 : pendage et plis

**Réglages :** `STRATA_DIP` = 0,5 et `STRATA_FOLD` = 0,4, tangentes du pendage régional et des plis.

- **Les strates montent ou descendent d'un champ en mètres,** calculé par sommet : pendage régional sur des octaves de 8 à 2 km, plis de 1 km à 128 m là où la région est déformée. Les tuiles de roche décalent leurs strates d'autant.
- **Essayé puis écarté :** tourner les tuiles par plan de projection. Chaque plan voit un autre pendage : chevrons nets le long des coutures de la projection biplanaire.
- **Mesure :** coût +0,1 ms au rendu, +0,1 ms au calcul près du sol. Crêtes sans pics. Les strates dessinent des V dans les ravins.
- Détails : `spec-roche-organique.md`.

## 2026-10-22 · Roche organique, étape 1 : le sol sur les replats

**Réglages :** `LEDGE_SCREE` = 0,72 à 0,82 et `LEDGE_SOIL` = 0,84 à 0,92, cosinus de la pente de la roche texturée.

- **La décision prend la pente de la texture :** là où la surface de la roche, maillage plus tuile, devient plate, les éboulis puis le sol la couvrent. Le relief et la pente gardent la forme de la roche.
- **Des replats dans la tuile de 64 m :** le haut de chaque banc penche vers l'arrière sur 40 % du banc, au plus 2,5 m ; une contremarche au pied du banc suivant. `HEIGHT_RANGE` de la tuile : 4 → 6 m.
- **Mesure :** coût nul à 0,01 ms près. Crêtes sans pics. Les replats s'effacent avec le filtrage de la tuile, au-delà de 500 m.
- Détails : `spec-roche-organique.md`.

## 2026-10-21 · Rendu de loin, étape 2 : la grille fine

- **Changement :** une grille 4 fois plus fine que la face du maillage, recalculée à chaque image pour les normales des pixels, au-dessus de mailles de face de 20 m. Le vrai relief sous la maille, d'orbite.
- **Coût :** +0,6 à 1,6 ms en altitude.
- **Corrections :** plantage loin de la planète, lecture hors du buffer des normales fines au bord de la face ; hauteurs des copies mêlées sans amplification, ce qui supprime les lames sur les crêtes ; relief enfoui sous la neige ; position de la caméra dans le titre, cap en argument ; banc des crêtes.
- Détails : `spec-rendu-lointain.md`.

## 2026-10-21 · Rendu de loin, étape 1 : roche et neige en fractions

**Réglage :** `MATERIAL_RELIEF_MAX_CELL` = 8 m, au lieu de 1 m.

- **De loin,** roche, éboulis et neige deviennent des fractions de la maille, d'après la dispersion des pentes que le maillage ne porte pas. Les bruits locaux s'effacent avec la taille du pixel. Les confettis vus d'orbite disparaissent.
- **Rayures de neige et de roche à 450 m :** le mélange par la hauteur s'estompe pour des pixels de 25 cm à 2 m.
- **Ailerons de près :** la passe de relief prend la normale sur quatre mailles.
- Détails : `spec-rendu-lointain.md`.

## 2026-10-21 · Structure de la roche au-delà de 8 m

- **Changement :** une tuile de roche de 64 m, 6 cm par texel : bancs de 2 à 8 m en corniches, fractures en couloirs, rideaux de vernis. La hauteur sous la caméra est lue après la passe de relief.
- **Mesure :** coût +0,10 à 0,22 ms. Tremblement sur la roche à 3 m 0,05 → 0,10, venu du relief de ±1 m porté par le maillage.
- Détails : `spec-textures-generees.md`.

## 2026-10-21 · Sable mêlé de roche, roche en bancs et diaclases

- **Sable mêlé de roche :** les bordures entre matériaux comparent les vraies hauteurs, en mètres, `BLEND_RISE` = 0,3 m. La roche n'affleure plus dans chaque creux de ride.
- **Roche :** les blocs de Voronoi tous de 1,3 m, vus comme des écailles en vol, deviennent des bancs de 0,5 à 2 m recoupés de diaclases tous les 0,8 à 4 m, une sur quatre ouverte.
- **Réalisme :** neutre, motifs un peu moins bons, spectre un peu meilleur.
- Détails : `spec-textures-generees.md`.

## 2026-10-21 · Couleurs de la roche

**Changement :** la roche n'a plus une seule couleur. Détails : `spec-textures-generees.md`.

- **Par région :** un bruit de 500 m à 40 km, calculé par sommet, choisit dans une palette de roches réelles : basalte, granite, calcaire, grès ocre, grès rouge. Deux autres bruits ajoutent l'oxydation et le vernis du désert.
- **Dans l'affleurement :** couches teintées du pâle à la rouille, blocs à ±20 %, taches d'oxyde de fer, vernis dans les coulures, lichens en colonies.
- **Coût :** +0,05 à 0,08 ms.

## 2026-10-21 · Correctif : pics du relief des matériaux

**Symptôme :** en zone sèche, des pics de 10 à 30 cm sortent du sol et scintillent en vol.

- **Cause :** le mélange des matériaux par la hauteur, `HeightBlend`. Dans la passe de relief, il faisait basculer un sommet de la hauteur de la roche à celle du sable entre deux voisins, au rythme des rides et des pierres. La roche porte ±30 cm, le sable presque rien : un pic.
- **Correctif :** la passe de relief mêle les matériaux sans la hauteur, `gHeightBlend` = 0. Les pixels gardent le mélange par la hauteur.
- **Mesure :** les plaques en pointe disparaissent en désert rocheux, à 26° N, 130° E. Tremblement 0,07 → 0,06.

## 2026-10-21 · Niveau de détail fin des matériaux

**Réglage :** `TEXTURE_FINE` = 1. Une seconde tuile de 1 m par matériau, 1 mm par texel : grains et graviers du sable, cristaux et piqûres de la roche, gravillons des éboulis. Le grain de 7,8 mm de la tuile de sable grossière disparaît. Détails : `spec-textures-generees.md`.

- **Réalisme, motifs :** sable ×17 → ×4,9 ; roche ×5,3 → ×2,3, ×8,8 → ×3,2, ×7,5 → ×3,6.
- **Tremblement :** inchangé. **Coût :** +0,05 ms à 1,5 m.
- **Pour revenir :** `TEXTURE_FINE = 0`.

## 2026-10-21 · Mesure de réalisme contre six scans réels

**Changement :** six scans Poly Haven, sous licence CC0, rangés hors du dépôt dans `../scans/`. `tools/realisme.py` les compare au sol du moteur, à la même échelle. Détails : `spec-textures-generees.md`.

- **Notes :** roche ×5 à ×9 du scan, sable ×8 à ×17. Le scan contre lui-même vaut ×1.
- **Leçons :** matériaux flous de près, texel de 7,8 mm ; sable sans grain ni cailloux ; couleurs de roche ternes.

## 2026-10-21 · Relief réel des matériaux, étapes 1 à 3 · gain visuel faible

**Changement :** une passe déplace les sommets proches de la hauteur des matériaux, filtrée à leur maille. Spécification : `log/spec-relief-reel.md`.

- **Code commun** des matériaux et du maillage, sans changement de rendu, vérifié au pixel près.
- **`MATERIAL_RELIEF` = 1,** qui s'efface quand les mailles approchent `MATERIAL_RELIEF_MAX_CELL` = 1 m. 0 revient à la texture seule.
- **Plancher de la caméra relevé de 30 cm,** pour ne jamais toucher le relief.
- **Étape 3 :** les pixels ne gardent que le relief plus fin que le filtre du maillage.
- **`MATERIAL_RELIEF_BAND` = 8 :** filtré à deux mailles, le relief faisait trembler la roche quatre fois plus ; à huit mailles, 0,06 contre 0,04 sans relief.
- **Gain visuel faible :** la roche générée est trop douce pour découper des silhouettes. Coût : 0,1 ms.
- **Mesure de réalisme :** `tools/realisme.py` compare le sol à un scan réel, à la même échelle. Il faut des scans du matériau visé.

## 2026-10-21 · Voie B, étape 2 : rides au pixel, roche et éboulis générés · tag `jalon/11-sable-roche`

**Changement :** les rides du sable sont calculées au pixel, en onde plane à phase exacte, au lieu d'être pavées. Roche et éboulis sont générés au démarrage, et mêlés au sol par la hauteur. Détails : `spec-textures-generees.md`.

- **Le sable :** plus de raccords ni de rides croisées, espacement et crêtes variables, antialiasing selon le pas à l'écran.
- **La roche :** six tours de banc, des écailles aux dalles et fissures discrètes ; ombres fines au soleil. Reste plate : relief réel à spécifier.
- **Le banc visuel :** `tools/banc_visuel.py` capture chaque site à quatre hauteurs à côté de sa référence.
- **La roche calculée au pixel de l'étape D.2 est retirée.**

## 2026-10-21 · Voie B, étape 1 : générateur de matériaux et sable · commit `63ebda2`

**Changement :** un générateur de matériaux tourne une fois au démarrage, en compute, et produit des tuiles sans couture : couleur et creux, pente et hauteur, avec leurs mipmaps. Premier matériau : le sable. Spécification : `spec-textures-generees.md`, cible : `images/cible-desert.jpg`.

- **Le sable :** rides de 12,5 cm au profil dissymétrique, tournées par un vent régional, posées par un pavage stochastique ancré sur la planète et une projection biplanaire.
- **Couleur de loin préservée,** tremblement inchangé avec lissage temporel, coût non mesurable.
- **Pour revenir :** `TEXTURE_DETAIL = 0` désactive toutes les textures de près.

## 2026-10-21 · Textures de près, étape D.2 : la roche · jugée peu convaincante

**Changement :** la roche a sa texture de près. Détails et mesures : `log/spec-rendu.md`, étape D.

- **La roche :** strates ondulées d'environ 0,8 m tirées d'un bruit de 256 m, fissures de 2 m et 50 cm, lichens gris-vert de 25 cm, rugosité jusqu'au pixel. Ses bosses percent la neige mince.
- **L'herbe n'est plus calculée sous la roche pleine :** la roche ne coûte presque rien en plus, +0,07 ms au ras du sol.
- **Couleur de loin préservée,** tremblement inchangé avec lissage temporel.
- **Pour revenir :** `TEXTURE_DETAIL = 0` désactive herbe et roche.

## 2026-10-21 · Textures de près, étape D.1 : le cadre et l'herbe · commit `cbdcb87`

**Changement :** chaque matériau peut avoir sa texture de près, couleur et pente, de 4 m jusqu'au pixel, ancrée sur la planète et filtrée sous 2 pixels. Premier matériau : l'herbe. Spécification et mesures : `log/spec-rendu.md`, étape D.

- **L'herbe :** plaques de 2 m, touffes douces de 15 à 35 cm, grain des brins à partir de 3 cm. Sa hauteur déplace les frontières : les touffes percent une neige mince.
- **Couleur de loin préservée,** tremblement inchangé avec lissage temporel.
- **Coût :** +0,4 ms au pire, au ras du sol.
- **Pour revenir :** `TEXTURE_DETAIL = 0`.

## 2026-10-21 · Mesure de la mutation au banc · ajoutée

**Changement :** le banc mesure aussi la mutation, la lente transformation des formes quand la maille rétrécit à l'approche. `MYPLANETENGINE_TREMBLE_FRAMES=64`, détails dans `log/spec-stabilite.md`.

- **Mesure :** caméra immobile, maillage qui avance d'environ une hauteur ; écart entre la moyenne des 8 premières et des 8 dernières images, après un flou de 8 pixels.
- **Validée sur la coupure du relief :** à 50 m, le premier plan mute deux fois plus à 4 mailles qu'à 2, de 0,17 à 0,36. Le jugement en vol est confirmé.
- **À 10 km, la mutation ne dépend pas de la coupure :** forte entre 20 et 120 km avec les trois coupures. Cause à chercher.
- **Réglages inchangés :** coupure à 2 mailles.

## 2026-10-21 · Normales spline et coupure du relief · spline gardée, coupure laissée à 2 mailles

**Changement :** la normale de l'éclairage reconstruite par pixel, en B-spline sur les 4 × 4 sommets voisins. Spécification et mesures : `spec-normales-spline.md`. Pistes : `log/pistes-glissement.md`.

- **B-spline lissante :** 12 à 16 % de tremblement en moins sur les trois vues. La spline cardinale, qui passe par les sommets, l'aggrave au contraire de 27 à 59 %.
- **Diagnostic :** les deux tiers du tremblement de la vue de montagne à 10 km ne viennent pas de la normale, mais de la géométrie.
- **Coupure du relief, `MESH_BAND_LIMIT` :** à 4 mailles au lieu de 2, scintillement divisé par deux au banc, de 1,01 à 0,51 sans lissage temporel.
- **Jugé en vol, les trois coupures côte à côte :** 2 mailles reste la meilleure. Plus la coupure est haute, plus chaque détail naît près de la caméra, donc grand à l'écran, et plus la forme mute à l'approche. Le banc ne mesure pas cette mutation lente : à ajouter.
- **Marge d'écart hors champ :** 6 mailles au lieu de 3, pour la spline et son préfiltre.
- **Coût :** moins de 0,1 ms.
- **Pour revenir :** `SPLINE_NORMALS = 0`.

## 2026-10-21 · POC des sommets fixes, étapes 2 et 3 · clos, tag `piste/sommets-fixes-etape3`

**Changement :** le fondu de hauteur entre niveaux et les rangées de bord. Détails et mesures dans `log/spec-sommets-fixes.md`.

- **Fondu imbriqué :** à la jonction, le carreau grossier est lui-même en partie fondu. Chaque carreau fond donc ses sept niveaux de grille, du plus grossier au plus fin. La surface ne dépend plus que du point et de sa distance : plus de fente.
- **Rangées de bord :** des sommets non dessinés à 1, 2, 4 et 8 mailles, pour des normales identiques des deux côtés d'un bord. La couture d'éclairage vue en vol a disparu.
- **Vol automatique :** `MYPLANETENGINE_FLIGHT=fichier` vole tout droit et note chaque image ; `MYPLANETENGINE_SPEED` règle la vitesse.
- **Verdict en vol :** le vaisseau semble ralentir puis réaccélérer. Mesuré : 34 % d'images à-coups en montagne, contre 0,5 % pour le plan glissant. Le coût suit le nombre de carreaux, qui varie sans cesse.
- **Décision :** POC clos. On revient au plan glissant, dont le coût constant fait la fluidité.
- **Tag :** `piste/sommets-fixes-etape3`.

## 2026-10-21 · POC des sommets fixes, étape 1 · tag `piste/sommets-fixes-etape1`

**Changement :** un second mode de maillage, touche M : les six faces d'un cube, en carreaux de 64 × 64 mailles choisis à chaque image selon la distance. Chaque sommet reste sur son point de la planète. Spécification : `log/spec-sommets-fixes.md`.

- **Étape 1 :** cube, carreaux, choix sur le processeur, un seul dispatch et un seul appel de dessin. Pas encore de fondu entre niveaux.
- **Corrigé :** la tangente du GPU, imprécise pour les petits angles, laissait une maille de fente entre tous les carreaux.
- **Mesure :** calcul 4 à 5 fois plus cher que le plan glissant près du sol, à réduire à l'étape 5.
- **Tag :** `piste/sommets-fixes-etape1`.

## 2026-10-21 · Arêtes arrondies à l'échelle de la maille · validé en vol, gain léger

**Changement :** la valeur absolue des bruits Billow et RidgedMulti devient une parabole sous un seuil qui suit la maille du sommet. Les crêtes et les creux vifs sont arrondis sur environ deux mailles, et se raffermissent en continu à l'approche. Spécification : `log/spec-stabilite.md`.

- **Pourquoi :** une arête infiniment fine ne s'échantillonne jamais sans erreur, et un maillage qui glisse déplace cette erreur à chaque image.
- **Mesure :** tremblement en montagne à 10 km de 0,46 à 0,17 avec le lissage, de 3,02 à 1,20 sans. Coût nul.
- **Écart visuel :** crêtes un peu plus douces à 10 km, presque rien de près.
- **Pour revenir :** `CREASE_ROUNDING = 0`.

## 2026-10-21 · Maillage de 192 mailles par côté · validé en vol

**Changement :** de 128 à 192 mailles par côté. Une maille fait environ 7 pixels à l'écran au lieu de 11, de près comme de loin.

- **Une seule source de vérité :** `FaceCells` dans `D3DApp.h`. La croissance des anneaux en découle, 1 + 2/FaceCells. Le facteur de taille du plan ne règle plus que l'étendue du plan central.
- **Mesure :** calcul au pire de 1,8 à 3,9 ms, au ras du sol. Tremblement en montagne à 10 km, avec le lissage, de 0,62 à 0,46.
- **Constat en vol :** nettement mieux, pas encore parfait.
- **Pour revenir :** `FaceCells = 128`.

## 2026-10-21 · Vrai relief des montagnes dans les pixels · arrêté ; lissage temporel · gardé

**Changement :** les pixels réévaluent les fractales des montagnes de complexplanet, à leur propre résolution. Le relief que la géométrie ne montre pas encore plie la normale et relève l'élévation. Un lissage temporel, reprojeté exactement, absorbe le scintillement. Spécification : `log/spec-rendu.md`, étape C bis.

- **Même source de vérité :** les fonctions du compute shader, partagées avec le pixel shader. Les déformations et le facteur d'échelle viennent des sommets.
- **Mutation,** après un flou de 8 pixels : de 1,91 à 1,36 à 10 km, de 2,76 à 1,95 à 3 km.
- **Tremblement :** en montagne à 10 km, de 3,39 à 0,95. Sans le lissage, le relief seul le portait à 7,99, à cause de la parallaxe.
- **Écarté :** une correction de parallaxe, plus chère et pire.
- **Corrigé après essai en vol :** de fausses crêtes, dues aux octaves comptées deux fois. Les sommets donnent maintenant une normale sans les montagnes, le pixel y ajoute toute leur pente.
- **Arrêté :** de loin, seules les crêtes des montagnes apparaissaient, sans le volume que la géométrie montre de près. Tout le graphe par pixel coûterait 8 à 33 ms. Le coût est dans le bruit, pas dans les sommets : densifier le maillage est la meilleure voie. Seul le lissage temporel est gardé.
- **Coût :** rendu jusqu'à 1,6 ms en montagne à 50 m.
- **Pour comparer :** touche T pour couper le lissage, `MYPLANETENGINE_NO_TAA=1`.
- **Pour revenir :** le commit précédent.

## 2026-10-21 · Matériaux par pixel et climat simple · en test

**Changement :** la couleur ne suit plus l'altitude par seuils nets. Un climat simple, fait de quelques bruits fixés sur la planète, choisit le sol pixel par pixel. Spécification : `log/spec-rendu.md`, étape C.

- **Température :** latitude, altitude, bruits régional et local, versants tournés vers le pôle plus froids.
- **Humidité :** désert, steppe, prairie ou forêt ; toundra dans le froid.
- **Roche sur les pentes, neige sous −2 °C, plage près de la mer.** Toutes les limites sont découpées par le bruit local, du kilomètre au mètre.
- **Normales :** le grain fin est renforcé sur la roche, adouci sur la neige et le sable.
- **Mesure :** rendu de 0,26 à 0,78 ms au pire. Tremblement inchangé, divisé par deux en montagne à 50 m.
- **Pour revenir :** le commit précédent.

![Départ à 50 m : avant, après](journal/2026-10-21-materiaux-depart-50m.png)
![Montagne à 50 m](journal/2026-10-21-materiaux-montagne-50m.png)
![Montagne à 10 km](journal/2026-10-21-materiaux-montagne-10km.png)
![Continent à 50 km](journal/2026-10-21-materiaux-continent-50km.png)

## 2026-10-21 · Atmosphère, ciel et soleil · en test

**Changement :** l'image est calculée en haute dynamique, sous une atmosphère d'après Hillaire 2020. Spécification : `log/spec-rendu.md`, étapes A et B.

- **Étape A, chaîne d'image :** rendu en virgule flottante, compression des hautes lumières, sortie sRGB. Image identique à ±1 niveau près.
- **Étape B, atmosphère :** trois petites tables calculées au démarrage, puis le ciel et la perspective aérienne calculés pixel par pixel.
- **Éclairage :** les couleurs du terrain deviennent des réflectances. Le soleil arrive filtré par l'air, et le ciel éclaire les ombres.
- **Mesure :** rendu de 0,11 à 0,26 ms au pire des dix vues de référence. Calcul du terrain inchangé.
- **Pour comparer :** touches O et P pour déplacer le soleil, `MYPLANETENGINE_SUN` pour les captures.
- **Pour revenir :** le commit précédent. Les réglages de l'atmosphère sont dans `PlanetSettings.hlsli`.

![Départ à 50 m : avant, après](journal/2026-10-21-atmosphere-depart-50m.png)
![Montagne à 10 km](journal/2026-10-21-atmosphere-mont-10km.png)
![Côte à 200 m](journal/2026-10-21-atmosphere-cote-200m.png)
![Orbite à 300 km](journal/2026-10-21-atmosphere-orbite-300km.png)
![Coucher de soleil à 50 m, orbite à 2 000 km](journal/2026-10-21-atmosphere-coucher-orbite.png)

## 2026-10-21 · Normales sur les sommets voisins et grain fin dans les pixels · gardées, à reprendre

**Changement :** la normale vient des quatre sommets voisins, sur deux mailles. Le grain fin perdu est redessiné dans les pixels par un bruit léger, fixe sur la planète. Spécification : `log/spec-stabilite.md`.

- **Vues :** le continent de départ, 15° S, 50° E, et des montagnes à 15° S, 120° E.
- **Problème :** le banc de mesure a montré que le tremblement vient presque entièrement de l'éclairage. La normale à un quart de maille capte les arêtes fines du relief, qui changent dès que les sommets glissent.
- **Grain fin :** seulement entre 1 et 8 mailles, la bande que les normales des sommets perdent, et seulement entre 13,5 m et 6 km, là où complexplanet a du relief fin. Sinon il inventerait du relief.
- **Mesure :** pire cas du calcul de 4,9 à 1,9 ms : plus d'évaluations supplémentaires par sommet. Rendu de 0,05 à 0,11 ms au plus.

| Tremblement, sur 255 | Avant | Après |
|---|---|---|
| Départ, 50 m, horizon | 0,49 | 0,22 |
| Départ, 50 m, vers le bas | 0,43 | 0,23 |
| Départ, 10 km, horizon | 0,79 | 0,45 |
| Montagne, 50 m, horizon | 1,74 | 0,57 |
| Montagne, 10 km, horizon | 17,6 | 6,6 |

- **Écart visuel :** au-dessus du continent de départ, quasi identique, même grain fin mesuré à 3 % près. En montagne, les arêtes sont plus douces : 9 % de grain en moins à 50 m, 38 % à 10 km. Le bruit générique ne reproduit pas les arêtes vives du bruit ridged.
- **Reste en montagne à 10 km :** surtout la couleur roche ou neige, qui dépend encore de la pente aux sommets.
- **Pour revenir :** `DETAIL_SLOPE = 0` retire le grain. Pour l'ancienne normale, le commit précédent.

![Départ à 50 m : avant, après, différence × 8](journal/2026-10-21-normales-voisins-depart-50m.png)
![Départ à 10 km](journal/2026-10-21-normales-voisins-depart-10km.png)
![Montagne à 50 m](journal/2026-10-21-normales-voisins-montagne-50m.png)
![Montagne à 10 km](journal/2026-10-21-normales-voisins-montagne-10km.png)

## 2026-10-21 · Normales lisses calculées sur le relief · remplacées

**Changement :** l'éclairage utilise la normale du relief lui-même, au lieu de la pente de chaque triangle.

- **Problème :** l'éclairage à facettes amplifiait le tremblement. Quand un sommet bouge de quelques centimètres, la pente des triangles voisins change, donc leur luminosité aussi.
- **Principe :** dans le compute shader, chaque sommet évalue le relief en deux points supplémentaires, à un quart de maille, et en déduit la normale de la surface. L'éclairage devient lisse et presque indépendant de la position des sommets.
- **Mesure :** pire cas de 1,6 à 5,6 ms, à cause des deux évaluations supplémentaires par sommet. À optimiser si la solution est gardée.
- **Pour comparer :** touche R, qui revient à l'éclairage à facettes.

## 2026-10-21 · Stabilisation par crans · abandonnée

Le maillage revient au glissement continu. Les réglages `RING_FILTER_CELLS` et `RING_FILTER_RAMP` sont retirés.

- **Constat en vol :** plus de tremblement dans le carré central, mais des changements de géométrie par paliers. Hors du carré, le tremblement restait. Un filtrage plus sévère, testé avec les touches M et N, lissait trop le relief sans supprimer le tremblement.
- **Pourquoi c'est abandonné :** le glissement continu du plan est justement ce qui densifie le maillage progressivement et rend l'approche sans couture. Des crans le transforment en niveaux de détail à paliers, à l'ancienne.

## 2026-10-20 · Stabilisation du maillage · abandonnée le 2026-10-21

**Réglages :** `RING_FILTER_CELLS` de 2 à 4, `RING_FILTER_RAMP` = 16, et la stabilisation côté C++. Détail dans `log/spec-stabilite.md`.

- **Problème :** en vol, le relief tremblait. La touche G, qui fige le maillage, l'a fait disparaître : c'était le maillage qui glissait sur le relief, pas la précision.
- **Principe :** la grille ne bouge plus que par crans, choisis pour que les sommets retombent sur d'anciens sommets.
  - Le plan tourne par crans d'une maille du carré central.
  - La taille change par crans de croissance des anneaux, d'après une hauteur du sol lissée.
  - Les anneaux, qui glissent encore un peu, sont filtrés plus sévèrement.
- **Mesure :** pire cas de 1,6 à 1,9 ms, sous la cible de 2 ms.
- **Écart visuel :** le relief lointain est un peu plus doux, à cause du filtrage des anneaux.
- **Pour revenir :** touche H en vol pour comparer. Pour tout retirer : `RING_FILTER_CELLS = 2.0` et `mStabilized = false` dans `D3DApp.h`.

## 2026-10-20 · Turbulence vectorielle · activée

**Réglage :** `VECTOR_TURBULENCE` de `false` à `true`. Le code est arrivé désactivé dans le commit `ea35946`, et l'activation suit l'entrée de ce journal dans l'historique git.

- **Principe :** une turbulence déplace un point avec trois bruits de Perlin, un par axe. La version vectorielle calcule les trois axes d'un coup : même découpage de la grille de bruit, mêmes poids de mélange, mêmes graines que libnoise. Mais les trois axes sont échantillonnés au point lui-même, au lieu de trois points décalés.
- **Mesure :** pire cas de 2,8 à 1,6 ms. Toutes les autres vues sont sous 0,3 ms.
- **Écart visuel :** le caractère du relief reste le même, mêmes zones de roche et de collines. La forme exacte des taches de roche et des ondulations change. Écart moyen de 1 à 3 sur 255 selon la vue, environ 1 % des pixels changent nettement.
- **Images :** `journal/2026-10-20-turbulence-vectorielle-1m.png`, `-10km.png`, `-cote.png`.
- **Décision :** testée en vol, avec puis sans. Aucune différence remarquée à l'œil : on garde la version la plus rapide.
- **Pour revenir :** `VECTOR_TURBULENCE = false`.

## 2026-10-20 · Turbulences des continents plafonnées · commit `ea35946`

**Réglage :** `CONTINENT_TURBULENCE_MAX_FREQUENCY` de sans limite à 1024.

- **Principe :** les trois turbulences des continents perdent leurs octaves fines. Celles-ci ne déplaçaient les côtes que de quelques mètres.
- **Mesure :** pire cas de 3,2 à 2,8 ms.
- **Écart visuel :** seul le contour fin de quelques îlots change, sur la vue de côte : 0,2 % des pixels. Rien ailleurs.
- **Image :** `journal/2026-10-20-turbulences-continents-1024-cote.png`.
- **Pour revenir :** `CONTINENT_TURBULENCE_MAX_FREQUENCY = NO_LIMIT`.
- Le même commit regroupe tous les réglages dans `PlanetSettings.hlsli`.

## 2026-10-20 · Table de gradients partagée, double précision près de la caméra · commit `5d221d4`

**Réglage :** `EXACT_LATTICE_MAX_CELL` = 4 m. Avant, la double précision servait partout.

- **Table de gradients en mémoire partagée :** rendu identique au pixel près. Gain de 16 à 50 % selon la vue.
- **Double précision réservée aux mailles de moins de 4 m :** plus loin, la précision du float, 0,4 m sur la planète, ne se voit pas. Écart visuel de 0,01 sur 255. Jusqu'à 70 % de gain selon la vue.
- **Correctif :** la caméra pouvait rester sous le relief si la fenêtre perdait le focus au démarrage.
- **Mesure :** pire cas de 4,6 à 3,2 ms.
- **Pour revenir :** `EXACT_LATTICE_MAX_CELL = NO_LIMIT`. La table partagée n'a pas de réglage, puisqu'elle ne change rien au rendu.

## 2026-10-20 · Champ de vision, type de terrain filtré · commit `5429682`

**Réglage :** `TERRAIN_TYPE_MAX_FREQUENCY` = 64. Avant, il n'y avait pas de limite.

- **Champ de vision :** les sommets hors du champ ne sont plus calculés. Pire cas de 15,1 à 7,6 ms. Aucun effet visuel.
- **Type de terrain :** limité aux longueurs d'onde de plus de ~100 km, puisqu'il ne sert qu'à choisir entre plaines, collines et montagnes. Pire cas de 7,6 à 4,6 ms. Écart visuel d'au plus 0,13 sur 255.
- **Pour revenir :** `TERRAIN_TYPE_MAX_FREQUENCY = NO_LIMIT`.

## 2026-10-20 · Anneaux jusqu'à l'horizon, filtrage des octaves · commit `91bcea4`

- **Maillage :** face de 128 × 128 mailles, entourée d'anneaux qui grandissent de 1 + 2/128 chacun, jusqu'à l'horizon plus 323 km pour les montagnes. k = 2.
- **Filtrage des octaves :** chaque sommet n'évalue que les octaves visibles à sa taille de maille. Une octave écartée est remplacée par sa moyenne : −0,36 pour Billow, 0,52 pour RidgedMulti, −0,06 pour Voronoi.
- **Mesure :** pire cas de 15,1 ms au ras du sol.

## 2026-10-20 · Portage de complexplanet · commit `b7b8c76`

- **Terrain :** l'exemple complexplanet de libnoise, porté en HLSL avec ses valeurs d'origine, mais avec la version actuelle du bruit de libnoise. Les images du site de libnoise utilisent l'ancienne version 1 : la planète n'est donc pas la même.
- **Précision :** la position dans la grille de bruit est calculée en double précision. Le compute shader passe par DXC, en Shader Model 6, à cause d'un bug du pilote NVIDIA avec FXC.
- **Rayon :** 6 378 km, contre environ 7 040 km pour la planète de complexplanet. Les reliefs sont donc environ 10 % plus petits que dans l'original.
