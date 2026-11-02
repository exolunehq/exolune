# Historique de la spec d’érosion

**2026-11-01 · Visible water was deferred.**
- The earlier erosion spec stored river discharge and stage but rendered only the sea.
- Its remaining step 6 deferred river and lake surfaces to later work with the sea.
- Replaced by `../spec-eaux-interieures.md`: shared channel envelopes, terminal stages and water optics.
- A nearest-cell lake stage was rejected after sampled coarse divides produced water steps up to 276.5 m.
- Continuous reconstruction replaces that lookup; connecting bands remain an approximation of unresolved spillways.

**Modèles côtiers remplacés ; voir [la spec actuelle](../spec-erosion.md).** Piste `piste/erosion-globale`.

**2026-11-01 · L’atténuation des plis avant l’érosion, retirée.**
- `EROSION_FOLD_DEPTH = (800, 2000)` effaçait les grands plis selon l’incision du réseau, avant la décision de creusement local.
- Ce couplage pouvait changer un versant sans que la vallée l’entaille ; près du canyon boisé, le support perdait environ 933 m.
- Le support est désormais indépendant ; seul le profil érosif peut le couper.

**2026-10-31 · Le profil en distance.**
- **Le modèle :** paroi tracée depuis le rivage estimé jusqu’au recul, hauteur extrapolée du point.
- **Le défaut rendu :** le proxy ignore le détail ; montagnes rabattues au platier, canaux intérieurs et parois kilométriques.
- **Les mesures de pente seules ne le validaient pas :** elles ne contrôlaient ni l’abaissement maximal ni les fenêtres voisines.

**2026-10-31 · Le contour par la pente côtière.**
- **Le modèle :** remappage de h, Hc entre 8 et 400 m, abaissement borné à Hc + 1 m.
- **Le défaut rendu :** G entre 0,03 et 0,1 m/m sous-estime les versants réels de 30 à 45° ; les parois restent invisibles à 4 km.

**2026-10-31 · Le contour par la pente locale du détail.**
- **Le modèle :** `SLOPE_KM = 0.3`, sept octaves de 50 km à 566 m ; deux parois de plus de 100 m mesurées, visibles en vol.
- **Le défaut rendu :** Hc change sur une échelle plus petite que son platier ; coupes enclavées et terre entre la paroi et la mer.
- **L’inondation, trois fenêtres de 10 km au pas de 50 m :** 19,432 %, 1,373 %, 3,883 % des coupes de plus de 10 m inaccessibles ; centres dans la spec actuelle.

**2026-10-31 · La variante de pente attendue, comparée au filtre de 9 km.**
- **Le coefficient RMS :** 0,0002283923092 /m ; 65 536 directions fixes, douze octaves ridgées à amplitude unitaire, sans plis ni ravines ; amplitude tectonique avant le terme des parois de vallée.
- **Les parts enclavées :** 8,411 %, 0,555 %, 0 % ; le seuil de 5 % échoue aussi sur la première fenêtre.
- **Les trois coupes fixes :** 256,328 / 111,488 / 132,693 m ; platiers −1,069 / −1,770 / −2,199 m ; aucune terre devant le pied.
- **Le choix :** filtre de 9 km, qui conserve les parois hautes et la côte basse observée sans proxy statistique supplémentaire ; aucun des deux choix ne garantissait la connexité avec la bande symétrique.

**2026-10-31 · La bande symétrique autour du rivage estimé.**
- **Le modèle :** `abs(shoreKm / shoreMetric) < W + 1 km`, extinction sur 500 m ; proxy brut de 8 km ; pente filtrée à 9 km.
- **Le défaut rendu :** une plage et des collines devant la paroi tropicale, une coupe noyée à l’intérieur ; le détail déplace le rivage hors de la bande.
- **Les fenêtres :** 8,889 %, 0 %, 0 % enclavés ; les 108 cellules isolées de la première fenêtre restent inaccessibles même sans plafond d’abaissement dans la bande.
- **Les distributions Hc précédentes, médiane/p90/maximum :** 149,855/257,947/337,176 ; 82,360/121,832/177,379 ; 91,426/159,114/245,786 ; 119,426/247,176/340,331 ; 137,097/168,253/193,122 ; 124,299/224,383/329,615 m ; mêmes six centres que la spec actuelle.
- **La correction :** côté mer, ouverture jusqu’au proxy ; côté terre, ajout du déplacement `relief / coastSlope`, plafond de 8 km ; Hc reste inchangé.

**2026-10-31 · Le cinquième passage, sans contrôle d’accès marin.**
- **Le rendu graine 0 :** paroi tropicale et stack validés ; plus de bande de terre devant elle ni de fosse intérieure ; falaise propre à 3° S.
- **Le défaut graine 1 :** canaux et anneaux de falaise autour des lacs de la plaine à −65,00789/−113,42094.
- **L’ablation sur 10 km au pas de 50 m :** bande symétrique 15,720 % abaissé de plus de 10 m ; ouverture seule 16,121 % ; extension intérieure seule 16,198 % ; ensemble 16,200 %.
- **Les parts enclavées correspondantes :** 31,286 %, 32,735 %, 32,579 %, 32,574 % ; aucun point de mer originale selon le seuil de −50 m dans cette fenêtre.
- **La cause :** Hc régional coupe les bas reliefs sans vérifier l’accès aux vagues ; aucun lien de vallée du niveau 0 ne creusait les points concernés.
- **Les deux extensions aggravent légèrement un défaut antérieur :** les retirer seules ne le corrige pas ; l’ouverture côté mer est conservée.
- **Les distributions Hc de graine 0 :** 134,698/251,737/337,176 ; 64,505/114,265/177,379 ; 78,409/162,371/245,786 ; 92,216/159,570/340,331 ; 131,832/163,650/193,122 ; 102,872/208,796/329,615 m ; médiane/p90/maximum aux six centres de la spec.
- **La correction retenue :** un témoin marin avant érosion à 3 km dans la direction du large ; les parois validées et la face froide restent identiques, la fenêtre glaciaire n’est plus abaissée.

**2026-10-31 · Les crêtes et le climat provisoires, remplacés.**
- **L’activation :** le maximum de la glace des auges et de la bande de la ligne d’équilibre affinait aussi les sols sous la glace.
- **Le profil :** `scale × k × u^0,7`, appliqué à la crête centrée déjà arrondie, réamplifiait ses petites valeurs ; sa pente tend vers l’infini à zéro.
- **Le climat :** pluie et température zonales, sans continentalité ; vent côtier zonal, force de 1 à 1,6, avec un repère est opposé à celui de la carte calculée.
- **Les premiers essais :** élargir seul l’arrondi ne garantissait pas la disparition des raidissements ; le profil monotone retenu borne aussi son amplification de pente.
- **Le cache :** relief, graine et date de l’exécutable ; le climat lui-même n’était pas dans la clé.

**Les mesures avant le climat calculé, conservées comme référence historique.**

**Les mesures CPU, graines 0 et 1 :** `python tools/cotes/verifie_falaises.py`.
- **Les trois coupes fixes :** centres rendus par l’utilisateur ; orientation par la pente du sol original ; face recherchée à moins de 2 km du centre, pas de 10 m.
- **La hauteur :** du platier voisin à la crête qui rejoint le sol original, sans remplacer cette mesure par Hc.
- **La terre devant le pied :** largeur cumulée au-dessus de +5 m, jusqu’au premier fond original sous −20 m vers le large.

| Centre | Paroi, m | Angle | Platier, m | Terre devant, m |
|---|---:|---:|---:|---:|
| 8,72580 ; −103,29430 | 252,295 | 80,95° | −1,157 | 0 |
| −23,18981 ; 157,86949 | 42,020 | 67,38° | −1,242 | 0 |
| −3,21302 ; 169,26372 | 121,945 | 83,76° | −1,939 | 0 |

**Les six fenêtres restent sous 5 % de coupes enclavées et 4 km de portée au p99.**
- **Les fenêtres :** 10 × 10 km, 201² points incluant les bords, pas et maille de 50 m.
- **L’inondation :** départ du sol original sous −20 m ; quatre voisins ; passage par le sol nouveau sous 0 m ou abaissé de plus de 1 m.
- **La part enclavée :** fraction des points abaissés de plus de 10 m que l’inondation n’atteint pas.
- **La mer originale :** sol original sous 0 m relié, par quatre voisins dans la fenêtre, à un sol sous −50 m.
- **La distance à la mer :** minimum euclidien exact sur cette grille, pour les points abaissés de plus de 10 m ; p99 et maximum, sans scipy.
- **Une fenêtre sans coupe :** aucun quantile à calculer, noté « — ».

| Graine ; centre | Enclavé | Distance mer p99 / maximum, m | Abaissement maximal, m | Surface abaissée de plus de 10 m |
|---|---:|---:|---:|---:|
| 0 ; 8,73276 ; −103,30263 | 0 % | 604,152 / 680,074 | 296,530 | 4,846 % |
| 0 ; −23,18173 ; 157,88952 | 0 % | 400,000 / 502,494 | 109,573 | 1,317 % |
| 0 ; −3,21302 ; 169,26372 | 0 % | 549,885 / 696,419 | 227,117 | 2,728 % |
| 1 ; −65,00789 ; −113,42094 | 0 % | — | 0 | 0 % |
| 1 ; 23,78161 ; −126,35919 | 0,113 % | 1 388,320 / 1 656,050 | 365,902 | 4,384 % |
| 1 ; 40,46592 ; −84,75513 | 0 % | 559,017 / 626,498 | 189,467 | 2,267 % |

- **La côte tropicale de graine 1 :** secteur actif le plus proche de 23,70143/−126,32998 dans un carré de 60 km, pas de 496 m ; aucune coupe dans le carré initial de 10 km.
- **La plaine glaciaire :** aucun abaissement ; son témoin reste sur des terres, de +26 à +799 m pour les anciennes coupes.
- **Le diagnostic :** le défaut existait avec la bande symétrique ; les deux extensions du cinquième passage ne l’aggravaient que légèrement, [historique](log/spec-erosion-historique.md).
- **L’hypothèse des vallées :** aucun lien du niveau 0 ne creusait les points abaissés de cette fenêtre ; un Hc régional trop permissif suffit à y couper les collines et les dépressions du détail.
- **Le contour :** Hc, son filtre de 9 km et les trois parois mesurées restent inchangés ; l’ouverture côté mer est conservée derrière le contrôle d’accès.
- **La limite globale :** le test d’accès local n’est pas un routage océanique ; la distance est vérifiée sur le sol réellement érodé, et le plafond du proxy peut encore exclure un rivage déplacé de plus de 8 km.
- **La borne mesurée sur ces fenêtres :** `abaissement − Hc ≤ 0,998 m`.
- **La côte plate témoin :** écart nul à 16,71/−89,28, sur la coupe et 441 points d’un carré de 10 km.
- **`valleys = false` :** identique au portage commité sur 288 points de chacune des deux graines, aux mailles de 10 m, 1 km et 30 km.
- **Le portage :** les deux scripts affichent `ok` ; continuité aux trois raccords du profil et aux bords de la bande, ouverture côté mer, fond profond et abaissement borné vérifiés jusqu’à une maille de 30 km.
- **La compilation :** Release x64 réussie, aucun avertissement dans les fichiers modifiés ; aucun moteur ni banc lancé.

**Hc sur la côte active, médiane/p90/maximum, en mètres :** carré de 60 km, 201² points, pas de 300 m, maille de 10 m ; sol original entre 0 et Hc, abaissé de plus de 1 m.

| Centre | Points | Médiane | p90 | Maximum |
|---|---:|---:|---:|---:|
| 8,54005 ; −103,23344 | 112 | 134,698 | 251,737 | 337,176 |
| −23,01696 ; 158,00809 | 105 | 64,819 | 110,074 | 126,281 |
| −3,34285 ; 169,01181 | 229 | 78,515 | 163,812 | 245,786 |
| −51,89165 ; −40,94037 | 89 | 89,894 | 132,712 | 214,339 |
| −8,11021 ; 131,04460 | 140 | 135,055 | 163,490 | 192,919 |
| 8,76166 ; −103,24998 | 173 | 110,260 | 219,854 | 329,615 |

**Les côtes froide et active :** recentrage sur le premier passage par zéro du sol original, le plus proche du point demandé sur une coupe de 30 km normale aux grandes formes.
- **La recherche :** passage encadré au pas de 10 m, affiné par dichotomie ; aucune sélection sur la hauteur ou la raideur de la paroi.
- **La côte froide :** rivage à −51,79251/−40,80271 ; paroi de 86,900 m à 75,62°, platier à −1,576 m ; bande et proxy à 1, exposition 0,28, K 0,984724.
- **La limite de cette coupe froide :** elle croise encore 660 m de terres au-dessus de +5 m entre ce pied et le premier fond original sous −20 m.
- **La côte active :** rivage à −8,10764/131,04054 ; aucune face à moins de 2 km sur sa coupe ; exposition 0,663389, K 1, proxy et bande nuls.
- **La cause sur la côte active :** son proxy de 11,407 km dépasse le plafond conservé de 8 km ; ce n’est pas un abri des vagues.
- **Les statistiques de Hc :** la valeur du champ au point reste identique ; le témoin filtre les surfaces actives, donc les distributions changent.
- **Les modèles remplacés :** [historique](log/spec-erosion-historique.md) ; jugement en vol par l’utilisateur : `tools/tests/2026-10-31-erosion.txt` pour la graine 0, `2026-10-31-falaises-graine1.txt` sur un build de la graine 1.

**Le réseau, graines 0, 1 et 2,** mesuré sur le fichier du moteur, `erosion-<graine>.bin` :

| Graine | Vers la mer, vers les lacs | Lacs | Glace | Plus grands bassins | Plus grand débit | Entaille aux nœuds, p90 et p99 |
|---|---|---|---|---|---|---|
| 0 | 82,2 %, 17,8 % | 0,95 % | 22,1 % | 5,6, 3,1, 2,4 Mkm² | 71 000 m³/s | 314 m, 2,3 km |
| 1 | 81,2 %, 18,8 % | 0,80 % | 18,3 % | 4,6, 3,5, 2,9 Mkm² | 93 000 m³/s | 430 m, 2,3 km |
| 2 | 86,4 %, 13,6 % | 1,87 % | 21,8 % | 7,7, 3,0, 2,8 Mkm² | 185 000 m³/s | 559 m, 2,6 km |

- **Toutes les terres atteignent la mer ou un lac terminal,** aucun cycle, pour les trois graines. Sur Terre, environ 18 % des terres sont endoréiques ; l'Amazone draine 7 Mkm², 200 000 m³/s.
- **Graine 0 :** 787 deltas, 2 115 cônes ; entaille médiane nulle, les fleuves des plaines coulent sur leur plaine.
- **Les graines 1 et 2** ont été vérifiées avant le routage pesé ; la graine 0, avant et après, garde un drainage complet.

**Coût et portage avant ce raccord, non remesurés.**

## Les mesures, graine 0

| Mesure | Valeur | Budget proposé, et pourquoi |
|---|---|---|
| Démarrage, niveau 0 à froid | 0,54 s, dont 0,50 s de réseau ; le shader de la forme compilé pendant la carte tectonique | 0,5 s par planète : la moitié de la carte tectonique, le système entier en quelques secondes au premier lancement |
| Démarrage, depuis le cache | 0,03 s | 0,05 s : un fichier de 12 Mo par corps |
| Mémoire GPU | 12 Mo | 13 Mo : 8 octets par cellule, un tiers de la carte tectonique |
| Calcul du terrain, en mouvement | 0,67 à 1,46 ms contre 0,28 à 0,95 ms, +0,2 à +0,65 ms ; minimum de 3 passages, GPU partagé et chargé à 75 % | +0,5 ms au plus : la marge d'une image à 120 fps |
| Portage contre la carte de la planète, 600 mailles | écart médian 0,6 cm ; p99 0,22 m ; 0,6 m au plus | 10 cm en médiane |
| Portage contre le sol sous la caméra, mailles fines, 7 lieux | médiane 0,18 m, 0,5 m au plus, la précision du titre | — |

**2026-10-31 · Avant le budget de pente des ravines.**
- **Le retour utilisateur après le raccord :** fin de la forêt supprimée, lacs et forêt non glaciée propres, climat puis érosion au démarrage sans erreur.
- **Le défaut restant :** tranchées, palissades et banque dus aux bandes des ravines, sans vallée ni dépôt ; le profil sans cuspide ne bornait pas leur pente.
- **Les essais écartés :** limiter seulement la pente nominale de l’onde laisse la rotation de ses directions et la variation de ses poids raidir le sol ; une limitation de l’amplitude de l’octave entière affaiblit aussi son bruit porteur.
- **Les anciennes mesures :** réseau antérieur au nouveau démarrage de l’utilisateur ; elles ne décrivent pas la saturation actuelle.

## Les mesures CPU du raccord, graine 0

**Référence :** `fe22cfe9d6d96e9680ca44ef2fd5e47704467939`, mêmes caches de niveau 0 avant/après, mêmes coordonnées, maille de 1 m.
- **Les transects :** vers le nord, de 0 à 25 m, pas de 0,25 m ; pente maximale entre deux points, montée maximale sur 0,5 m.
- **Les fenêtres :** 200 × 200 m, 201² points, pas de 1 m ; norme du gradient centré sur les 199² points intérieurs.

| Lieu, latitude ; longitude | Pente nord maximale, avant → après | Montée sur 0,5 m, avant → après | Fenêtre au-dessus de 60°, avant → après |
|---|---:|---:|---:|
| Forêt, 34,1611352 ; −73,72443 | 82,110° → 40,624° | 2,888525 → 0,424922 m | 9,504810 → 9,812884 % |
| Versant, −48,3497 ; −44,8221 | 9,541° → 34,412° | 0,029690 → 0,087256 m | 6,530138 → 4,628671 % |
| Arêtes, −46,9 ; −33,8 | 38,073° → 39,998° | descente sur toute la coupe | 11,416378 → 28,203833 % |

- **La variation absolue sur 0,5 m :** forêt 3,106238 → 0,424922 m ; versant 0,084017 → 0,341587 m ; arêtes 0,391559 → 0,418452 m.
- **Les arêtes restent actives :** enlever le seul affûtage après correction déplace le sol d’au plus 157,873 m dans leur fenêtre ; pente maximale de fenêtre 86,993°, finie.
- **Le contrôle analytique :** profils monotones, dérivée nulle au sommet, arrondis de 0,0001 à 10 fois l’amplitude ; erreur de dérivée contre différences finies sous 6,94·10⁻⁸, variation de moyenne sous 4,48·10⁻¹³ unité de bruit.
- **La limite :** la forêt garde des pentes fortes ailleurs dans sa fenêtre ; leur part n’y diminue pas. Le versant signalé n’avait pas de mur sur sa seule coupe nord de 25 m. Ces chiffres ne remplacent pas le jugement en vol.
- **Le changement de climat :** ligne d’équilibre forêt 2 982 → 2 033 m, versant 1 287 → 28 m, chaîne 1 472 → 467 m ; la nouvelle pluie et la nouvelle température modifient l’activation, même à réseau fixé.

**Hc sur les six côtes, médiane / p90 / maximum en mètres :** carrés de 60 km, 201² points, pas de 300 m, maille de 10 m ; sol avant vagues entre 0 et Hc, abaissé de plus de 1 m.

| Centre, latitude ; longitude | Hc avant | Hc après | Force du vent avant → après |
|---|---:|---:|---:|
| 8,54005 ; −103,23344 | 134,511 / 251,589 / 337,002 | 211,469 / 376,231 / 400,000 | 1,000059 → 1,000000 |
| −23,01696 ; 158,00809 | 64,505 / 109,177 / 126,281 | 64,505 / 109,177 / 126,281 | 1,020926 → 1,000000 |
| −3,34285 ; 169,01181 | 89,815 / 175,176 / 233,046 | 89,815 / 175,176 / 233,046 | 1,000004 → 1,000000 |
| −51,89165 ; −40,94037 | 54,558 / 130,787 / 214,107 | 54,558 / 133,071 / 214,107 | 1,431430 → 1,121946 |
| −8,11021 ; 131,04460 | 121,440 / 186,622 / 234,563 | 54,275 / 69,711 / 89,271 | 1,000047 → 1,000000 |
| 8,76166 ; −103,24998 | 110,260 / 219,275 / 329,433 | 177,989 / 349,712 / 400,000 | 1,000066 → 1,000000 |

- **Le sens du vent compte :** la conversion de vitesse reste dans l’ancienne plage utile ; le repère est corrigé pour lire le climat. Hc peut donc changer fortement, et les points actifs aussi.
- **`valleys = false` :** identique au bit près sur 288 points par graine, graines 0 et 1, aux mailles de 10 m, 1 km et 30 km.
- **La côte plate :** écart nul sur sa coupe et les 441 points de son carré de 10 km, à 16,71 ; −89,28.
- **Les caches :** tectonique, volcans et climat de graine 0 présents dans `x64/Release`, calculés avec les sources intégrées inchangées ; niveau 0 ancien, non reconstruit. Pour la graine 1 du contrôle côtier, cartes tectonique, volcanique et climatique existantes reprises du worktree climat, générateur tectonique identique et `Climate::Build` identique ; réseau ancien conservé.
- **Le coût :** aucun banc demandé ni lancé ; les anciennes mesures de coût restent dans l’historique.
- **La compilation :** `tools/lance.ps1 -Build -NoLaunch`, Release x64 réussie ; aucun avertissement dans les fichiers modifiés.
- **Les contrôles :** `cp.py`, `verifie_cretes_climat.py` et `verifie_falaises.py` affichent `ok` ; deux faces fixes présentes avant et après, dont une au-dessus de 100 m. Le contrôle côtier compare ce témoin intégré, car sa troisième face historique est déjà absente avant le raccord.
- **Les coupes avec accès marin :** au plus 0,500 % enclavées dans les six fenêtres, portée p99 au plus 1 373,851 m ; 2 950,013 m dans la fenêtre supplémentaire du cap tropical ; `abaissement − Hc ≤ 0,998 m`.

**Le réseau global doit être remesuré après reconstruction du niveau 0.** Le portage lit le fichier du moteur ; il ne calcule pas ce niveau. Les anciennes parts de terres drainées, gelées et lacustres restent dans [l’historique](log/spec-erosion-historique.md).

## 2026-10-31 · Mesures avant le raccord des fonds et la borne rocheuse

**Le budget C, avant D.**

**Avant/après sur le même réseau actuel, calculé par le moteur lancé par l’utilisateur.** Aucun moteur ni banc lancé pendant cette correction.
- **La référence avant C :** `x64/Release/cp-avant-pentes.py`, copie du port avant modification ; SHA256 `2240e47c60635f41d3877f53abdb355d7c72bec428ffe5f85b8acbeba986d7ea`.
- **Le contrôle :** `python tools/hydro/verifie_pentes_ravines.py`, ou `--only analytic`, `windows`, `coasts` ; le paramètre `--before-file` accepte une autre copie de référence.
- **Les fenêtres :** 100 × 100 m entre les bords, 101² points, pas de 1 m ; gradient centré, différence à un côté sur le bord.

| Lieu, latitude ; longitude | >35°, avant → après | >45°, avant → après | >60°, avant → après | Maximum, avant → après |
|---|---:|---:|---:|---:|
| Forêt, 34,1611352 ; −73,72443 | 39,320 → 0 % | 10,460 → 0 % | 3,794 → 0 % | 84,939° → 30,648° |
| Versant, −48,3497 ; −44,8221 | 13,724 → 0 % | 5,784 → 0 % | 1,245 → 0 % | 71,630° → 22,578° |
| Canyon, −38,1080 ; 166,4916 | 83,364 → 14,254 % | 74,640 → 0 % | 40,869 → 0 % | 84,484° → 44,060° |
| Plat, 44,16 ; −60,08 | 0 → 0 % | 0 → 0 % | 0 → 0 % | 4,610° → 4,613° |
| Arêtes, −46,9 ; −33,8 | 63,082 → 31,948 % | 49,770 → 0,863 % | 31,977 → 0 % | 86,751° → 47,432° |

**Les témoins, sans ravines / avant érosion :**

| Lieu | >35° sans ravines / `valleys=false` | >45° sans ravines / `valleys=false` | >60° | Maximum sans ravines / `valleys=false` |
|---|---:|---:|---:|---:|
| Forêt | 0 / 0 % | 0 / 0 % | 0 % | 30,648° / 30,648° |
| Versant | 0 / 0 % | 0 / 0 % | 0 % | 22,577° / 22,577° |
| Canyon | 14,254 / 25,909 % | 0 / 1,500 % | 0 % | 44,060° / 47,268° |
| Plat | 0 / 0 % | 0 / 0 % | 0 % | 4,612° / 4,612° |
| Arêtes | 31,948 / 31,948 % | 0,863 / 0,863 % | 0 % | 47,432° / 47,432° |

- **La cible est tenue :** aucun point au-dessus de 45° dans les quatre fenêtres de sol mobile, contre au plus 1,500 % sur la forme avant érosion.
- **La réserve est conservatrice :** ravines entièrement retirées dans la forêt et le canyon, effet inférieur à 1 mm sur le versant ; le bruit porteur est conservé au bit près, pas aplati.
- **Les arêtes :** crêtes rocheuses de 47,432°, 31,948 % de la fenêtre au-dessus de 35° ; le remplacement par les ravines y est presque nul, environ 1 µm de hauteur. Les anciennes pentes de 86,751° venaient du motif problématique.
- **La maille :** résultats identiques au bit près sur ces cinq fenêtres entre des mailles de 0,25 et 1 m, où les octaves sont résolues.
- **La moyenne :** profils de bandes centrés, erreur de quadrature sous 1,03·10⁻¹³ unité de bruit, arrondis de 0,0001 à 2 amplitudes ; une fenêtre de 100 m ne moyenne pas les phases des octaves de plusieurs km.

**Les deux transects nord :** 0 à 25 m, pas de 0,25 m, maille de 1 m.

| Lieu | Pente maximale, avant → après | Montée maximale sur 0,5 m | Variation absolue maximale sur 0,5 m |
|---|---:|---:|---:|
| Forêt | 40,624° → 17,267° | 0,424922 → 0,155406 m | 0,424922 → 0,155406 m |
| Versant | 34,412° → 13,486° | 0,087256 → 0,119753 m | 0,341587 → 0,119753 m |

**Le contour des six falaises est conservé :** comparaison de Hc aux mêmes 201² points des fenêtres de `verifie_falaises.py`, écart maximal nul sur chaque champ ; quantiles ci-dessous pris aux points actifs avant C.

| Centre | Hc médiane / p90 / maximum aux points actifs avant, m | Hc aux points actifs après, m |
|---|---:|---:|
| 8,54005 ; −103,23344 | 211,469 / 376,231 / 400,000 | 203,744 / 382,981 / 400,000 |
| −23,01696 ; 158,00809 | 69,649 / 109,531 / 126,281 | 67,239 / 109,075 / 126,281 |
| −3,34285 ; 169,01181 | 89,815 / 175,176 / 233,046 | 82,142 / 175,291 / 218,965 |
| −51,89165 ; −40,94037 | 46,701 / 134,083 / 214,107 | 54,649 / 137,112 / 214,107 |
| −8,11021 ; 131,04460 | 54,275 / 69,711 / 89,271 | 50,437 / 71,033 / 89,271 |
| 8,76166 ; −103,24998 | 177,989 / 349,712 / 400,000 | 171,101 / 345,552 / 400,000 |

- **Le champ Hc ne change en aucun point :** la correction du sol déplace les points actifs ; leur médiane varie de −8,54 à +17,02 %, leur p90 d’au plus 2,26 %. Les mêmes points gardent exactement les mêmes quantiles avant/après.

- **`valleys=false` :** identique au bit près sur 288 points par graine, graines 0 et 1, aux mailles de 1 m, 1 km et 30 km.
- **Sans ravines :** identique au bit près avant/après C dans les cinq fenêtres.
- **La côte plate :** écart nul sur les 441 points de son carré de 10 km, à 16,71 ; −89,28.
- **Les fichiers du réseau :** caches actuels lus par les deux versions ; pas de nouveau niveau 0 produit pendant C.
- **Le jugement en vol reste à faire :** `tools/tests/2026-10-31-pentes-ravines.txt`.
- **La vérification :** Release x64 par `tools/lance.ps1 -Build -NoLaunch`, aucune erreur ni nouvel avertissement dans les fichiers modifiés ; `cp.py`, `verifie_pentes_ravines.py`, `verifie_falaises.py` et le contrôle des crêtes affichent `ok`.


**Règle de C remplacée après le retour utilisateur :**
- **Pas de seuil plus haut sous le seul drapeau glaciaire :** la glace au dernier maximum ne prouve pas la présence de roche nue ; les ravines restent un motif de sol mobile. Le bruit qui porte les crêtes rocheuses, les profils des vallées et les falaises ne sont pas plafonnés par ce réglage.

## 2026-10-31 · D avant projection sphérique et séparation des échelles

**Les mesures de D.**

**Même réseau actuel avant/après D, fourni par le moteur lancé par l’utilisateur.** Aucun moteur ni banc lancé ici ; le portage ne reconstruit pas le niveau 0.
- **La référence :** `x64/Release/cp-avant-fonds.py`, SHA256 `e8e551b5df2a62e8caaec981be4fb1289f8a07c424d9665bc800c70987a2f3e4` ; mesures C et références antérieures dans [l’historique](log/spec-erosion-historique.md).
- **Les commandes :** `python tools/hydro/verifie_fonds_vallees.py` ; `python tools/hydro/verifie_pentes_ravines.py --before-file x64/Release/cp-avant-fonds.py`.
- **L’inondation :** carré de 4 km entre les bords, 161² points, pas de 25 m, huit voisins, bords ouverts. Premier carré centré 2 325 m au nord et 1 475 m à l’est de −25,566 ; −26,916 ; second centré sur −25,486 ; −27,075. Maille du portage de 5 m.

| Zone | Profondeur fermée maximale du carré, avant → après | Au point le plus profond avant, avant → après | Carré de 10 km sous son niveau d’eau de plus de 5 m, avant → après |
|---|---:|---:|---:|
| Première auge | 77,010 → 72,964 m | 77,010 → 48,373 m | 0,450936 → 0 % |
| Seconde auge | 734,793 → 681,453 m | 734,793 → 579,469 m | 0,666601 → 0,058818 % |

- **Le premier fond :** au point de profondeur maximale avant, sol 992,265 → 1 021,138 m, son niveau d’eau. Au point décalé donné dans le signalement, sol 1 049,607 → 1 036,022 m, son niveau ; profondeur fermée 19,668 → 33,489 m. Le maximum résiduel du carré, 72,964 m, existe aussi dans le sol grossier creusé sans détail.
- **Le second fond :** au point de profondeur maximale avant, sol 1 060,705 → 1 216,029 m, son niveau d’eau. La fermeture du carré n’est pas supprimée : le sol grossier creusé seul, sans aucun détail, contient déjà une cuvette de 441,570 m. Cause de cette cuvette du réseau actuel à rechercher ; elle ne vient pas du seul détail résiduel.
- **Les plateaux réellement bornés à l’eau :** 4 592 et 2 764 points ; écarts sol − eau de [−67,036 ; +191,015] m et [−155,324 ; +164,339] m avant, zéro après. Les traces des thalwegs prennent le profil grossier le plus profond de chaque coupe, sans sélectionner sur la hauteur fine : 72 et 50 points ; écarts [−15,521 ; +58,883] m et [−39,522 ; +88,158] m avant, zéro après. CSV dans `x64/Release/thalweg-*-*.csv`.
- **Les carrés de 10 km :** 101² points à 100 m, centrés sur les deux coordonnées signalées. Sous le niveau de plus de 5 m parmi les points à `floorShare > 0` : 0,137241 → 0 % et 0,313695 → 0 %. Le déficit résiduel de 64,863 m de la seconde fenêtre est hors de ce masque.
- **La cuvette initiale de 84 m n’est pas reproduite avec le nouveau réseau :** ne pas confondre les mesures d’intégration avant A–C avec cette référence avant D.
- **Hors creusement :** correction des fonds isolée de la borne rocheuse, 6 172 et 7 234 points des deux carrés de 10 km identiques au bit près.

**Les fenêtres C :** 100 × 100 m entre les bords, 101² points à 1 m ; différences centrées, à un côté sur le bord.

| Lieu | >35°, avant → après | >45°, avant → après | >60°, avant → après | Maximum, avant → après |
|---|---:|---:|---:|---:|
| Forêt, 34,1611352 ; −73,72443 | 0 → 0 % | 0 → 0 % | 0 → 0 % | 30,647836 → 30,647798° |
| Versant, −48,3497 ; −44,8221 | 0 → 0 % | 0 → 0 % | 0 → 0 % | 22,577514 → 22,577126° |
| Canyon, −38,1080 ; 166,4916 | 14,253505 → 14,253505 % | 0 → 0 % | 0 → 0 % | 44,060265 → 44,060258° |
| Plat, 44,16 ; −60,08 | 0 → 0 % | 0 → 0 % | 0 → 0 % | 4,613229 → 4,613229° |
| Arêtes, −46,9 ; −33,8 | 31,947848 → 31,947848 % | 0,862661 → 0,862661 % | 0 → 0 % | 47,432335 → 47,432339° |

- **Le seuil rocheux ne suffit pas à restaurer les parois :** tan(70°) est bien appliqué, mais l’enveloppe conservatrice de C limite encore le motif à 0,255 mm dans la fenêtre d’arêtes. Le retour de parois au-dessus de 60° reste non obtenu ; il faudra resserrer les enveloppes de pente et de rotation, sans enlever la protection des sols.
- **Les sols restent comme en C :** zéro au-dessus de 45° dans les quatre témoins ; le canyon avant érosion reste à 1,499853 %. Le raccord des fonds ne change pas leurs bruits sans ravines, identiques au bit près.
- **Transects nord, 0 à 25 m à 0,25 m :** forêt, pente 17,267267 → 17,267291°, montée et variation absolue sur 0,5 m 0,155405864 → 0,155406092 m ; versant, 13,486420 → 13,485948°, 0,119753109 → 0,119749038 m pour les deux variations.
- **Indépendance de la maille :** cinq fenêtres identiques au bit près entre des mailles résolues de 0,25 et 1 m.

**Hc médiane / p90 / maximum :** mêmes six carrés de 60 km, 201² points ; mêmes points actifs avant/après D. Écart de champ nul partout.

| Centre | Hc avant = après, m |
|---|---:|
| 8,54005 ; −103,23344 | 203,744 / 382,981 / 400,000 |
| −23,01696 ; 158,00809 | 67,239 / 109,075 / 126,281 |
| −3,34285 ; 169,01181 | 82,142 / 175,291 / 218,965 |
| −51,89165 ; −40,94037 | 54,649 / 137,112 / 214,107 |
| −8,11021 ; 131,04460 | 50,437 / 71,033 / 89,271 |
| 8,76166 ; −103,24998 | 171,101 / 345,552 / 400,000 |

- **`valleys=false` :** 288 points × trois mailles, graines 0 et 1, identiques au bit près.
- **Côte plate :** 441 points du carré de 10 km à 16,71 ; −89,28, identiques au bit près ; le témoin plat C aussi.
- **Contrôles :** `cp.py`, falaises, contrôle analytique du budget et raccord des fonds affichent `ok`. Le contrôle des fenêtres échoue désormais explicitement sur les parois d’arêtes au-dessus de 60°, non restaurées ; les fermetures grossières restent mesurées, sans être déclarées corrigées.
- **Compilation :** Release x64 par `tools/lance.ps1 -Build -NoLaunch`, zéro erreur, aucun nouvel avertissement dans les fichiers modifiés ; avertissements restants dans les fichiers inchangés `Materials`, `Mesh`, `OceanSurface`, `PixelShader` et `PlanetFoliageMeshPixel`. Résultats dans `x64/Release/verification-build-fonds-final.txt`.
- **Jugement en vol :** `tools/tests/2026-10-31-fonds-vallees.txt`, sans lancement automatique.


**Le budget remplacé :**

**Le budget de pente, `ReliefGullyGain` :**
- **Le seuil des sols mobiles :** `EROSION_GULLY_CRITICAL = 1,25`, environ 51,3° ; valeur de travail issue de MR1, `1,25 ± 0,10`, [Roering, Kirchner et Dietrich 1999](https://seismo.berkeley.edu/~kirchner/reprints/1999_29_Roering_nonlinear.pdf), §5.2 et tableau 1. Leur transport croît sans borne à l’approche de ce seuil ; ce n’est pas l’angle de repos de grains sans cohésion.
- **Le seuil rocheux :** `Sc = lerp(1,25, tan(70°), gullies.glacial)`, `EROSION_GULLY_ROCK = 2,74747742` ; seule la bande de ligne d’équilibre, jamais `valley.glacier`. Selby 1980 relie la pente rocheuse à la résistance du massif ; 70° est notre choix pour la roche forte, dans la plage 60–80° signalée, pas un seuil universel de l’article. Le [travail de terrain d’Augustinus 2002](https://pubs.geoscienceworld.org/gsl/sjg/article-abstract/38/1/15/114650/The-influence-of-rock-mass-strength-on-the-form) reprend cet équilibre de résistance sur des versants déglacés. Le bruit ordinaire, les profils des vallées et les falaises ne changent pas de loi.
- **D’abord la place du bruit ordinaire :** `s` est la pente des octaves au-dessus, `N` une enveloppe de celle de l’octave ordinaire ; `L = max(Sc − s − N, 0)` et `B = L² / Sc`. Le carré raccorde la réserve à zéro avec une dérivée nulle.
- **Puis le remplacement seul :** `D = share × (N + G)`, `gain = B / sqrt(B² + D²)` ; le motif est mêlé au bruit pour `share × gain`, sans écrêter une hauteur. Sa pente supplémentaire est au plus B, B au plus L ; réserve épuisée, le bruit ordinaire reste entier.
- **G couvre les bandes et leur orientation :** période de l’onde, poids quintiques des huit coins et normalisation près des bifurcations ; la rotation de la direction suit l’enveloppe de courbure des octaves au-dessus, divisée par leur pente. Limiter la seule pente nominale de la sinusoïde ne suffisait pas.
- **Les enveloppes du bruit quintique :** 26 pour son gradient, 512 pour sa courbure en unités de maille ; des majorants conservateurs depuis les coins unitaires et les dérivées des poids, pas des réglages par lieu. La courbure des crêtes arrondies utilise le plancher physique de 2 m et la géologie ; jamais la maille courante, ni le poids de filtrage de l’octave.
- **La moyenne :** bruit et bande sont centrés séparément avant le remplacement ; pour les crêtes des bandes, moyenne exacte de la sinusoïde arrondie, affûtage compris. Le gain dépend des formes porteuses, pas de la phase de l’octave courante.
- **Le coût :** aucune lecture voisine de terrain ni de carte ; un budget épuisé saute le calcul du motif, sauf l’octave côtière de calibration. Aucun banc GPU lancé.

## 2026-10-31 · Estimateur côtier doublé de E, retiré

- **La calibration est indépendante du creusement :** aux seuls points où les vagues peuvent agir, la lecture de vallée et les trois octaves de plus de 9 km gardent l’estimateur de D ; le sol réel utilise la projection sphérique et les nouvelles ravines. Hc reste ainsi identique aux mêmes points. Cela ajoute une requête de vallées et trois octaves dans cette seule bande côtière ; aucun sol voisin ni relief complet réévalué pour Hc.

**Les témoins côtiers :** mêmes six carrés de 60 km, 201² points, même Hc aux mêmes points, écart de champ nul partout. Quantiles aux points actifs de D, médiane / p90 / maximum en m :

| Centre | Hc D = E |
|---|---:|
| 8,54005 ; −103,23344 | 203,744 / 382,981 / 400,000 |
| −23,01696 ; 158,00809 | 67,239 / 109,075 / 126,281 |
| −3,34285 ; 169,01181 | 82,142 / 175,291 / 218,965 |
| −51,89165 ; −40,94037 | 54,649 / 137,112 / 214,107 |
| −8,11021 ; 131,04460 | 50,437 / 71,033 / 89,271 |
| 8,76166 ; −103,24998 | 171,101 / 345,552 / 400,000 |

- **Les points actifs changent avec le sol :** leurs quantiles peuvent donc varier sans changement du champ Hc.
**Retiré à la demande de l’utilisateur :** l’identité de Hc au bit près était sur-spécifiée ; elle ne justifie ni une seconde lecture de vallées hors sphère, ni trois octaves recalculées. Les mesures courantes sont dans `../spec-erosion.md`.


## 2026-11-01 · Profils et mesures remplacés de la version 14c99ec

Les auges surcreusées puis arasées à l’eau, les quatre cordes par courbe et le gauchissement de 7 km sont remplacés. Les mesures suivantes portent sur cet ancien état.

## Le niveau 1 : les vallées du réseau, `ErosionValleys`

**Chaque lien du niveau 0 est une courbe :** une B-spline quadratique entre les milieux des liens, tangente d'un lien à l'autre ; un affluent rejoint le tronc tangentiellement, vers l'aval. Le point se lit gauchi de 7 km, de 40 et 20 km de longueur d'onde, pour que les liens droits serpentent.

**Un gauchissement de direction reste sur la sphère :**
- **La cause des auges fermées :** la turbulence déplaçait p en 3D sans le renormaliser. La distance à la courbe comptait son décalage radial, parfois kilométrique, comme une distance transversale ; le profil remontait sur le thalweg et fermait le fond.
- **La correction dans `ErosionValleys` :** retour à l’unité avant la localisation et les distances ; estimation de la racine inverse en flottant, un raffinement de Newton en doubles avant de multiplier p. Aucun niveau d’eau modifié, aucun seuil forcé ni drainage local.
- **Le sol non creusé reste libre :** le fond ne calme le détail que si `h > max(surface, level)` ; la même surface bornée à l’eau sert à estimer la part creusée et le renfort de détail des parois. Le profil sous l’eau ne doit pas effacer un sol situé sous son niveau et qu’il ne peut creuser.

**La vallée, autour de la courbe la plus proche :**
- **le fond,** au niveau de l'eau interpolé le long de la courbe, d'une demi-largeur 2 √Q m, jusqu'à 15 fois plus sur un fleuve lent, 0,15 cellule au plus ; le détail s'y éteint, sauf sous la mer, rien de plus fin que le niveau 0 ne barre le cours ;
- **les versants,** à la pente de seuil, 14° sur les sols tendres à 33° sur les chaînes jeunes ;
- **sous la glace,** une auge en U : demi-largeur 600 m à 10⁸ m³/an de glace, comme sa puissance 0,4, de 150 m à 1,5 km ; surcreusée de 0,3 de sa demi-largeur, versants à 40° ; le détail s'éteint en son milieu, où se rencontreraient les ravines de ses deux versants. Près d'une côte froide, son fond passe sous la mer : un fjord ;
- **le maillage :** une vallée moins large que deux mailles s'élargit, moins profonde d'autant.

**Le creusement déplace le sol grossier, il ne le coupe pas :** le sol s'abaisse d'autant que la vallée passe sous les grandes formes et les octaves de plus de 20 km, par un minimum lissé sur 60 m, jamais sous le niveau de l'eau. Le détail plus fin reste sur les versants, renforcé jusqu'à 0,35 de la profondeur creusée au point : contreforts et ravines à l'échelle du versant, rien de plus sur une plaine.

**Le fond se raccorde au niveau de l’eau, dans les deux sens (`ErosionCarve`) :**
- **Le résidu fin est `h − coarse` :** le simple abaissement grossier le laissait creuser des fosses et dresser des seuils au milieu des auges.
- **Le plateau réellement noyé compte entier :** le profil brut `bed` est borné par `min(coarse, level)` ; là où cette borne impose l’eau, le raccord retire tout le résidu, positif ou négatif. Le seul `floorShare` ne suffisait pas : le milieu calme du U s’arrête avant toute sa partie sous l’eau.
- **Vers les parois :** part `max(floorShare, 1 − smoothstep(0, 60, bed − level))` ; même part du fond, complétée par le plateau réellement borné à l’eau. Un `smoothstep(0, 60, coarse − cut)` ouvre le raccord avec le creusement ; aucun creusement, aucun changement. Le relief grossier et le profil restent entiers.
- **Le niveau vient toujours du lien lu :** un lac du niveau 0 garde son niveau propre ; aucune hauteur d’eau locale inventée. Ces fonds indiquent où sera l’eau des fleuves et des lacs ; elle n’est pas encore rendue.

**Les dépôts :** un delta, un lobe vers le large à 3 m au-dessus de la mer, 60 √Q m, 1,6 fois plus large le long de la côte, son front descendant vers le plateau ; un cône, de 120 √Q m vers l'aval, pente de 3 %, son pied à 45°. L'un et l'autre bornés à 0,25 cellule, éteints à 0,3 cellule de leur sommet : les nœuds lus les tiennent toujours.

**Les recherches dans la texture :** les 4 × 4 nœuds autour du point, chacun avec ses affluents et son receveur ; un nœud à plus de 1,75 cellule est sauté ; aucune vallée ne porte au-delà de 0,5 cellule, ni en mer à plus de 500 m de fond. Les positions sont relatives au point, en flottants : une seule lecture en doubles par sommet.

**Ce que le détail lit en est continu :** la profondeur et la glace d'une vallée sont le maximum de celles des liens proches, chacune éteinte avant que les liens lus ne changent. Prises au seul lien le plus bas, elles sautaient d'un lien à l'autre, et le détail avec elles.

## Les mesures CPU des ravines rocheuses et des auges ouvertes, graine 0

**Références sur les mêmes caches :** intégration `fe22cfe`, D `1ca9743`, sources chargées directement par `git show` ; aucune reconstruction du niveau 0. Commande : `python tools/hydro/verifie_erosion_roche.py`, ou `--only windows`, `troughs`, `coasts`.

**Les chaînes vues de loin :** carrés de 5 × 5 km entre les bords, 201² points à 25 m, maille de 25 m ; gradient centré, différence à un côté sur le bord. Parts en pour cent.

| Lieu | Version | >35° | >45° | >60° |
|---|---|---:|---:|---:|
| −25,60 ; −26,94 | Intégration | 56,867 | 40,472 | 7,039 |
| | D | 45,595 | 26,715 | 0,196 |
| | E | 51,432 | 44,746 | 6,307 |
| −46,9 ; −33,8 | Intégration | 26,390 | 9,784 | 1,017 |
| | D | 5,745 | 0,183 | 0 |
| | E | 27,645 | 11,599 | 2,193 |

- **Même échantillonnage, maille de 5 m pour contrôle :** chaîne E 51,662 / 44,454 / 6,903 %, arêtes E 29,455 / 12,178 / 2,205 % ; crêtes fines davantage résolues.
- **La protection de C reste tenue :** dans les quatre carrés de 100 × 100 m à 1 m, zéro au-dessus de 45° et de 60°, avant et après E. Maxima D → E : forêt 30,648 → 31,358°, versant 22,577 → 20,052°, canyon 44,060 → 43,960°, plat 4,613 → 4,613°. Au-dessus de 35°, seul le canyon : 14,254 → 12,214 %.
- **La petite fenêtre d’arêtes reste locale :** sur 100 m à 1 m, E atteint 14,626 % au-dessus de 45°, zéro au-dessus de 60°, maximum 52,675° ; elle peut tomber sur un seul flanc d’une bande kilométrique. Le contrôle rocheux de E porte sur le carré de 5 km demandé, où les parois au-dessus de 60° sont présentes. Le bruit sans érosion reste comparé par `valleys=false` ; le sol sans ravines mais creusé peut changer avec la correction des vallées.
- **La moyenne des bandes reste nulle :** gain et part rocheuse indépendants de la phase courante ; mêmes profils centrés, même affûtage et même arrondi. Quadrature du profil : erreur sous 1,03·10⁻¹³ unité de bruit.

**Les auges :** carrés de 4 km, 161² points à 25 m ; inondation à huit voisins, bords ouverts, maille de 5 m. Premier centre à −25,545112988 ; −26,901313945, soit le décalage signalé de 2 325 m nord et 1 475 m est ; second à −25,486 ; −27,075.

| Zone | Fermeture du creusement grossier D → E | Fermeture du fond borné à l’eau D → E | Maximum sur tout le carré D → E |
|---|---:|---:|---:|
| Première auge | 72,964 → 0 m | 72,964 → 0 m | 72,964 → 57,498 m |
| Seconde auge | 441,570 → 0 m | 609,559 → 0 m | 681,453 → 65,790 m |

- **Les maxima restants sont hors creusement :** sol 3 067,853 m contre niveau d’eau 963,779 m pour le premier, 3 281,771 contre 1 225,714 m pour le second ; `coarse == cut`, `floorShare == 0`. Ils ne ferment pas les fonds des auges.
- **Les vrais thalwegs sont suivis vers l’aval :** courbe du lien, puis de ses receveurs ; inversion du gauchissement angulaire, erreur sous 3,4 nm. Parcours de 5 002 et 5 046 m, sans interpoler des hauteurs hors de la courbe ; CSV `x64/Release/erosion-e-thalweg-*.csv`.
- **Écart sol − eau, premier parcours :** D de 0 à +708,725 m à maille 5 m, 0 à +690,982 m à 200 m ; E zéro aux deux mailles. Creusement grossier E − eau : zéro aussi.
- **Second parcours :** D de +571,903 à +3 177,031 m à maille 5 m, +592,529 à +3 180,971 m à 200 m ; E zéro aux deux mailles, sol complet et grossier. Le niveau d’eau descend sur les deux parcours.
- **Les lacs du niveau 0 :** seize débouchés lacustres recevant un affluent ; niveau lu à leur nœud à moins de 0,000006 m de leur niveau stocké. Les cellules lacustres isolées n’ont pas de courbe de niveau 1 ; elles ne font pas partie de ce contrôle.

**Les falaises sans recalcul côtier :** comparaison avant/après suppression du bloc qui conservait Hc au bit près. Même port E et mêmes caches actuels pour les deux versions ; référence `x64/Release/cp-avant-simplification-cotes.py`, SHA256 `b89e84542c3826aea5656bdc73315e366479693d32a10496781f5941f4c3ed01`. Commande du relevé : `python x64/Release/mesure-simplification-cotes.py` ; sortie `verification-simplification-cotes.txt` dans le même dossier.

**Hc sur les six côtes, médiane / p90 / maximum en m :** carrés de 60 km, 201² points, maille de 10 m ; quantiles sur les points actifs de chaque version, comme `distribution` dans `verifie_falaises.py`.

| Centre | Avant | Après |
|---|---:|---:|
| 8,54005 ; −103,23344 | 212,071 / 378,526 / 400,000 | identique |
| −23,01696 ; 158,00809 | 70,800 / 109,075 / 119,508 | identique |
| −3,34285 ; 169,01181 | 80,218 / 180,002 / 255,085 | 81,427 / 181,618 / 343,741 |
| −51,89165 ; −40,94037 | 54,558 / 133,074 / 214,107 | identique à 0,001 m près |
| −8,11021 ; 131,04460 | 51,545 / 68,277 / 89,271 | 51,969 / 68,365 / 89,271 |
| 8,76166 ; −103,24998 | 170,834 / 345,453 / 400,000 | identique |

- **La variation principale :** maximum de la troisième fenêtre +88,657 m ; médiane +1,209 m, p90 +1,616 m. Le plafond reste 400 m ; le maximum ne doit pas être décrit comme une petite variation.
- **Le sol avant abrasion est identique au bit près** dans les six carrés ; seuls la pente fournie à Hc et le résultat des vagues changent.

**Les trois coupes fixes :** avant = après aux précisions indiquées ; angle à pas de 10 m, platier adjacent à la face, terre au-dessus de +5 m jusqu’à la mer originale.

| Coupe, latitude ; longitude | Paroi | Angle | Platier | Terre devant |
|---|---:|---:|---:|---:|
| 8,72580 ; −103,29430 | 377,816 m | 84,91° | −1,412 m | 0 m |
| −23,18981 ; 157,86949 | 41,877 m | 72,47° | −1,099 m | 0 m |
| −3,21302 ; 169,26372 | 42,519 m | 75,64° | −1,540 m | 0 m |

**Les trois fenêtres de contrôle, graine 0 :** carrés de 10 km, 201² points à 50 m ; avant = après aux précisions indiquées.

| Centre | Part enclavée avant → après | Portée marine p99 avant = après |
|---|---:|---:|
| 8,73276 ; −103,30263 | 0 → 0 % | 1 138,519 m |
| −23,18173 ; 157,88952 | 0 → 0 % | 400,031 m |
| −3,21302 ; 169,26372 | 0 → 0 % | 683,482 m |

- **Aucune cible des falaises n’échoue :** trois faces actives, dont une de plus de 100 m, avant et après ; aucun seuil terrestre devant leur pied, aucune coupe enclavée dans ces trois fenêtres, p99 sous 4 km, abaissement sous Hc + 1 m. Le contrôle complet `python tools/cotes/verifie_falaises.py` affiche aussi `ok`.
- **Les ressources :** une requête `ErosionValleys`, toujours sur la sphère, et le seul `ReliefDetail` principal pour `cliffSlope` ; paramètres `sphere` / `project` retirés. Aucun gain de temps GPU annoncé sans mesure.
- **Le jugement en vol :** `tools/tests/2026-10-31-cotes-sans-recalcul.txt`, sans lancement automatique ; le parcours E des chaînes reste valable.

- **`valleys=false` :** identique au bit près sur 288 points × trois mailles, graines 0 et 1. Côte plate, 441 points à 16,71 ; −89,28 : écart nul.
- **Vérifications de la simplification :** `cp.py`, comparaison avant/après et contrôle complet des falaises affichent `ok` ; Release x64 sans erreur ni nouvel avertissement dans les fichiers modifiés (`verification-build-simplification-cotes.txt`). L’ancienne assertion d’identité de Hc est retirée ; les limites physiques restent testées.
- **Limites :** ni moteur ni banc lancé ; le retour en vol reste nécessaire, `tools/tests/2026-10-31-ravines-roche-auges.txt`. Les caches ne sont pas réécrits.


## 2026-11-01: rejected rock-only characteristic slope budget

Superseded by the shared turning envelope. Four CPU windows reproduce blades up to 514.73 m per one-metre step. The former specification follows.

**Deux sols, deux échelles, un mélange continu (`ReliefGullyRock`, `ReliefGullyGain`) :**
- **Le sol et les éboulis :** `Sc = 1,25`, Roering et al. 1999 ; sous 300 m de longueur d’onde et hors des chaînes, le budget conservateur de C reste entier.
- **Le passage à la roche :** de 300 m à 1 km, `smoothstep` physique, jamais le pas du maillage. [Grieve, Mudd et Hurst 2016](https://onlinelibrary.wiley.com/doi/10.1002/esp.3884), *How long is a hillslope?*, mesurent des médianes de versants de 98 à 228 m ; la plage 300 m–1 km est notre séparation progressive entre ces versants et les incisions de massif, pas une constante universelle tirée de l’article.
- **La roche présente :** `r = mountains × smoothstep(600, 1400, relief) × smoothstep(0,3, 1, wavelengthKm) × (0,8 + 0,2 glacial)`. `relief` est l’amplitude en mètres passée au détail, `mountains` la part de chaînes existante ; la ligne d’équilibre renforce la roche, elle n’est plus sa seule preuve. Jamais `valley.glacier`.
- **La résistance rocheuse :** `Sc = tan(70°)`, choix de roche forte dans le cadre de Selby 1980, conservé de D. L’arrondi fini des crêtes et leur moyenne ne changent pas.
- **La saturation commune :** pour la pente porteuse s, la réserve de l’octave ordinaire N et celle de la bande G, `L = max(Sc − s − N, 0)`, `B = L²/Sc`, `gain = B / sqrt(B² + [share × (N + G)]²)` ; raccord C1 à réserve nulle.
- **Sur le manteau :** N et G gardent les enveloppes conservatrices de C, gradient 26 et courbure 512 du bruit, poids et bifurcations des bandes compris ; l’arrondi physique de 2 m borne les retournements.
- **Dans la roche large :** réserve à l’échelle de l’octave : N est amplitude × fréquence, G la pente de la sinusoïde finie, `2π × stripeScale × amplitude × fréquence`, affûtage compris. Garder les enveloppes de retournement à 2 m pour une incision kilométrique annulait ses bandes même à `Sc = tan(70°)`.
- **La portée de ce seuil rocheux :** pente caractéristique à l’échelle de l’octave, pas plafond de toutes les pentes locales après orientation ; des parois locales dépassent 70°, comme le bruit et les profils des vallées conservés. Le manteau garde son enveloppe conservatrice point par point.
- **Le mélange :** `share × lerp(gainSoil, gainRock, r)` remplace le seul motif ; il ne réduit pas le bruit ordinaire lorsque la réserve est épuisée. Gain et part rocheuse ne lisent pas la phase courante ; bruit et bande restent centrés séparément.
- **Le coût :** aucune lecture voisine de relief ni nouvelle octave pour le budget ; mêmes bandes, saturation scalaire. Le coût de la pile est mesuré ci-dessous ; celui de ce seul budget n’est pas isolé.

## 2026-11-01: rejected depth-derived profile dilation

The following contract passed positive-depth area checks but moved unbounded banks when reference depth approached zero. It is replaced by a local profile mean.

- La largeur se mesure à l’intersection exacte du profil avec son sol de référence.
- Une vallée plus étroite que deux mailles s’élargit ; sa profondeur et toute sa section verticale diminuent dans le rapport inverse.
- Cette transformation conserve l’aire creusée de la coupe ; l’ancienne formule ne contractait pas tout le profil et pouvait laisser un U sous deux mailles.

## 2026-11-01: archive worktree closure

Historical checks before the current blade and approach corrections; these are not current validation results. Legacy hashes below identify archive-only references.

### Original verification

**Référence :** `14c99ec`, le dernier état de « Érosion globale : fleuves et glaciers ».

**Passage au dépôt public**
- Cette étape est figée dans le worktree local `claude/erosion-globale-b42982`, devenu archive ; aucun push de cette branche ni de son ancienne ascendance.
- La suite se fait dans `C:\Users\etien\Documents\repos\Exolune`, après reprise des changements sur le `main` public par la session coordinatrice.
- `verifie_auges.py` charge encore le port de référence par `git show 14c99ec:tools/hydro/cp.py` ; ce témoin devra être adapté au nouveau clone sans y importer l’ancien historique Git.
- Les captures, caches et rapports bruts restent dans `x64/erosion-2026-11-01` de l’archive locale, hors Git ; le présent bilan, les contrôles et le parcours de vol sont versionnés.

**Contrôles réalisés**

- `python tools/hydro/verifie_auges.py` : profils, courbes, quatre sols, deux fenêtres glaciaires, 200 raccords et six traces sur les graines 0 et 1.
- Dix-huit coupes vérifient la largeur de deux mailles et la conservation de l’aire ; erreur d’intégration inférieure à 0,001 %.
- Les courbes sont comparées à toutes les racines de leur polynôme de distance ; 500 cas, erreur maximale inférieure à 10⁻⁸ rayon.
- Les paramètres des sources et exutoires sont vérifiés sur 804 positions ; la seule distance ne détectait pas leurs sauts de largeur.
- Dix mille coupes aléatoires vérifient que l’effacement du détail ne relève aucun creux.
- Sur 4 010 points répartis entre les deux graines, le support grossier est identique au bit près, érosion activée ou non.
- Sur les 3 908 points hors incision de ce tirage, le détail avant la coupe reste également identique.
- Les 840 traversées de frontières de faces ou de fenêtres de lecture donnent zéro saut résiduel de hauteur ; écart résiduel de pente directrice inférieur à 0,0005 m/m.
- Les six traces couvrent 11 à 23 km chacune ; aucun résidu du détail sur les fonds creusés.
- Les recouvrements expliquent des écarts au niveau d’eau du lien sélectionné allant jusqu’à 16,12 m ; l’eau des fleuves n’est pas rendue et son futur raccord devra suivre la surface réellement gagnante.
- Le bruit sans érosion reste identique au bit près dans les quatre fenêtres de sol.
- Le réseau de niveau 0 du rendu, graine 0, conserve tous ses texels au bit près face à `14c99ec` ; seule la clé de cache dépendant de l’exécutable change.
- Les coupes résolues à 1 m et 0,25 m sont identiques.

| Fenêtre de 4 km, graine 0 | Avant | Après |
|---|---:|---:|
| Première auge : surface à moins de 10 cm du niveau d’eau | 31,60 % | 0,47 % |
| Seconde auge : même mesure | 33,53 % | 0,96 % |
| Première auge : plus grande cuvette locale | 57,50 m | 23,88 m |
| Seconde auge : plus grande cuvette locale | 65,79 m | 15,40 m |

- Les cuvettes restantes de ces fenêtres sont hors du fond contrôlé ; un carré à bords ouverts ne mesure pas le drainage complet d’un bassin.
- Les pentes maximales des quatre sols sont 30,65°, 22,58°, 47,27° et 4,61° ; le seuil du manteau est `atan(1,25) = 51,34°`.
- La déformation angulaire est contrôlée sur 200 000 directions, deux graines : 12,87–12,91 % de jacobiens négatifs à 7 km, aucun à 2 km ; minima 0,181 et 0,231.
- Résultats locaux dans `x64/erosion-2026-11-01/geometrie-finale.json`.
- Release x64 compilée ; douze vues rendues sans fenêtre dans `x64/erosion-2026-11-01/apres-native`.
- Le banc de qualité termine sur les douze lieux ; treize p95 sur les 47 comparables dépassent de plus de 10 % ceux de `14c99ec`.
- Le critère d’acceptation reste non satisfait ; cette piste n’est pas intégrée.

**Le coût en mouvement**
- `tools/banc_perf.py`, trois vues fixées, 1920 × 1080, VSync désactivée, météo figée, moyenne de 120 images par vue.
- Mouvement par image : `1 0 0 1 0 0.003`, mêmes trajectoires pour `14c99ec` et la pile corrigée ; une exécution à la fois.
- Résultats dans `perf-reference/perf.json` et `perf-apres/perf.json`, sous le même dossier de validation.

| Vol | Calcul terrain avant → après | GPU total avant → après |
|---|---:|---:|
| Auge, 3 km | 1,243 → 1,416 ms | 28,119 → 29,304 ms |
| Vallée tropicale, 5 km | 1,177 → 1,260 ms | 19,289 → 20,928 ms |
| Forêt, 50 m | 2,103 → 2,376 ms | 22,864 → 24,193 ms |

- La correction ajoute 0,08 à 0,27 ms au calcul du terrain ; le temps GPU total augmente de 4,2 à 8,5 % sur ces vols.
- Ces moyennes ne constituent pas une mesure de variance entre exécutions.

**La référence de qualité**
- Douze lieux communs, cinq hauteurs de 12 m à 3 km, 1920 × 1080 ; lissage temporel et halo activés, nuages masqués.
- Commande : `tools/banc_qualite.py ... --from-sites x64/erosion-2026-11-01/sites.json --batch-suns --before tools/banc_qualite_reference.json`.
- `14c99ec` fournit 3 254 crops et dépasse déjà 10 % sur 22 mesures p95 contre la référence historique du 2026-10-24.
- Cette référence précède le relief tectonique ; elle est conservée, avec une seconde comparaison sur les mêmes lieux contre `14c99ec`.
- Certains couples matériau–hauteur ont moins de vingt crops ; leurs résultats restent signalés, sans exclusion du seuil.
- Le témoin ne fournit aucun crop de sable isolé, malgré les deux lieux visés ; les éboulis n’ont que quatre crops à 12 m, aucun aux autres hauteurs.
- Cette couverture ne permet pas de valider toutes les familles de matériaux.
- La mutation mesure l’image entière sous son masque gris ; contrairement aux crops, elle n’exclut pas explicitement la mer.
- Les captures donnent une hauteur au-dessus du sol filtré ; à grande altitude, les caméras des deux maillages peuvent donc différer. Le témoin atteint 40,3 m d’écart à 3 km, contre zéro aux vues à 12 et 50 m.
- Ces limites sont conservées dans les deux passages ; ni métrique ni référence ne sont modifiées pour passer le seuil.

**Le résultat du banc**
- Deux passages complets : 60 vues et 540 captures chacun ; 3 254 crops avant, 2 535 après.
- Toutes les mesures finales sont finies ; aucun couple matériau–hauteur du témoin ne disparaît.
- Les éboulis à 50 m apparaissent avec seize crops ; leurs deux p95 n’ont pas de témoin comparable.
- Contre la référence historique, 19 dépassements sur les 47 p95 comparables, contre 22 avant ; cela ne valide pas la correction.
- Contre `14c99ec`, les treize dépassements sont les suivants ; les faibles effectifs restent comptés.

| Matériau, hauteur | Mesure p95 | Avant → après | Crops avant → après |
|---|---|---:|---:|
| Herbe, 200 m | Répétition | 0,090 → 0,112 | 235 → 157 |
| Herbe, 3 km | Répétition | 0,203 → 0,234 | 171 → 183 |
| Roche, 3 km | Trou / répétition | 2,24 → 2,71 dB / 0,144 → 0,193 | 157 → 46 |
| Éboulis, 12 m | Répétition | 0,073 → 0,187 | 4 → 18 |
| Neige, 800 m | Trou | 2,73 → 3,01 dB | 174 → 212 |
| Neige, 3 km | Trou | 2,69 → 3,41 dB | 231 → 234 |
| Sol nu, 12 m | Répétition | 0,070 → 0,103 | 16 → 104 |
| Sol nu, 50 m | Trou / répétition | 2,20 → 5,73 dB / 0,076 → 0,216 | 46 → 96 |
| Sol nu, 200 m | Trou / répétition | 1,01 → 2,67 dB / 0,080 → 0,217 | 40 → 103 |
| Sol nu, 800 m | Répétition | 0,094 → 0,205 | 14 → 20 |

- La mutation p95 baisse aux cinq hauteurs : 0,200 → 0,196 à 12 m ; 0,205 → 0,146 à 50 m ; 0,216 → 0,168 à 200 m ; 0,110 → 0,101 à 800 m ; 0,060 → 0,049 à 3 km.
- Le principal trou du sol à 50 m vient du lieu −25,6°, −26,94°, devenu sol nu et neige là où le témoin montrait une paroi rocheuse.
- Une fenêtre de 800 m autour de ce lieu, 1 681 sondes à maille de 1 m, est entièrement hors incision ; son sol est identique au bit près avec ou sans érosion.
- Le manque de détail mesuré dans cette fenêtre appartient donc au rendu du support conservé ; la coupe n’y éteint aucun détail.
- Les vues couleur et relief sur ce lieu et le canyon sont dans `diagnostic-reference` et `diagnostic-apres` ; les écarts par crop dans `attribution-qualite.json`, sous le même dossier de validation.
- Rapports complets : `qualite-apres/rapport.md`, `qualite-apres/comparaison-14c99ec.md` et `audit-qualite.json`.

## 2026-11-01: rejected symmetric coastal talus

- The former support was `platform + max(talus - screeSlope*abs(h-Hc)/G, 0)`.
- Its mound fell on the landward side before meeting the cliff, making a false groove.
- The user's pose `28.7 -47.008952 -32.993928 62.67 -50.35` reproduced the defect exactly.
- Snow accumulated on both false ridges; changing the material would not repair the geometry.
- The old profile reversed slope in 288 of 384 parameter sections; the reported section dropped 7.39 m behind its crest.
- The replacement finds the contact on the cliff face and extends the apron seaward; see the current specification.
- Before the coastal metric correction, native color, snow and relief captures at the same reported pose removed the false groove and its two snow ribbons.
- A wider cold view and a tropical witness retained continuous coastlines; the southern witness still showed isolated inland pits.
- The physical coastal metric subsequently rejected the cold-location cut altogether; these screenshots describe the earlier metric, not the current terrain.

**Superseded specification:**
- **Les éboulis :** pente de 35°, jusqu’à 22 % de Hc, par taches de 900 m ; distance au pied exprimée par `abs(h − Hc) / G`.

## 2026-11-01: rejected mesh-scale coastal metric

- `ReliefCoastGradient` previously used all five coastal octaves and the rendering mesh's crease rounding.
- At the user's pose `254.1 34.983719 88.511430 43.46 -106.41`, a ria cusp produced a straight wall with thin needles.
- Across a 10 m cusp crossing, the metric changed from 1.31 to 5.93 and the cliff-height contour from 56.89 to 258.82 m.
- The same 128 m window sampled every metre contained a 172.67 m height step.
- The coast before wave erosion remained continuous; disabling wave erosion isolated the cause from the valley and mesh profile.
- Filtering only the source octave wavelengths would not remove an absolute-value cusp in their derivative.
- The replacement filters both the metric spectrum and its crease derivative at the existing 9 km physical scale.
- The second reported pose `78.3 34.977346 88.514165 4.61 -99.01` was in the same false excavation; its ground changes from 36.19 to 235.03 m.
- Local diagnostic captures and arrays are under `x64/erosion-walls/`; no performance or image-quality benchmark was run.

## 2026-11-01: hydrology composition audit

**Scope: diagnosis and proposed design, no generator change.**
- The user requested a structural response to ribbon-like rivers, perched channels, closed outlets, geometric junctions, coastal serrations and late visibility.
- Evaluator: current `tools/hydro/cp.py`, seed 0, existing `EXOEROS3` cache.
- The probes are functional terrain inspections, not performance or image-quality benchmarks.

**Perched river reproduction**
- Reported camera: `150.9 -12.406891 52.928246 26.44 -118.93`.
- A transverse section crosses the nearby wet channel at latitude -12.4068909864, longitude 52.9309713794.
- Section length: 5 km, 1,001 samples, 2 m terrain footprint.
- At its centre: parent before valley cutting 176.48 m, coarse support 372.46 m, valley stage 31.63 m, final bed 30.65 m.
- At -250 m across: pre-erosion ground 236.10 m, final ground -63.44 m.
- Disabling coastal erosion leaves this false side depression unchanged.
- No deposit raises the ground anywhere in the accompanying 12 km window.
- The cause is `surface = valleySurface + (height - coarse) * (1 - floorShare)`.
- Negative residual detail lowers the banks past their drainage level while the floor suppresses that same residual.
- The existing cut-only rule prevents raising the parent ground, but does not prevent manufacturing a deeper side channel.
- The 12 km window uses 81 by 81 samples and an 8 m footprint: 423 samples are cut below their channel stage despite starting above it; maximum undercut 278.25 m.
- Of those window samples, 350 move from positive parent elevation to negative elevation through valley cutting.
- These counts describe this sampled window, not planetary prevalence.

**Other observations and limits**
- The geometric-junction window at -12.486714, 52.694265 also contains newly manufactured side depressions; the closed-outlet window at -1.882499, 69.597920 does not reproduce this particular mechanism.
- The closed outlet therefore remains a separate connectivity investigation; it is not proven to be a delta-deposit defect.
- Coarse drainage stages and rendered paths use different sample positions, as shown by `ErosionForm`, `ErosionNode` and the later relief warp.
- The late-water failure is independently visible in `PixelShader`: finer terrain elevation is combined with a coarse-mesh water-depth cap.
- Local diagnostic arrays and the transverse plot are under `x64/water-approach/`; they are not checked into Git.
- No shader, geometry setting or executable was changed during this audit.
- The subsequent implementation and remaining revision are in `../spec-eaux-interieures.md`.

## 2026-11-01: bounded valley composition and floor coupling

**Superseded rules**
- Signed residual detail was added to the valley envelope, except on its floor; negative detail could dig a second, lower channel.
- The floor mask was set to zero on terminal links, restoring residual obstacles before the coarse outlet.
- The valley join used a constant 60 m depth even on the floor; an 8 m incision barely lowered the terrain and left a barrier.
- The final water pass used `min(terrain, channelBed)` with an unbounded bank profile, hiding incomplete floor construction by excavating another V valley.
- The replacement carries positive spurs, retains original hollows, couples the floor to the channel and bounds the final water cut by compact channel depth.

**Rejected absolute incision cap**
- The prototype bounded lowering by the coarse network's stored incision at every detailed sample.
- At the river witness -1.828016777, 69.643755616: parent 234.02 m, coarse support 197.51 m, stage 21 m and stored incision 31.625 m.
- This left the carved ground at 216.92 m and the bounded channel bed at 207.17 m; the formerly wet bed was 11.25 m.
- The cap cannot be used before reconciling the network's reference terrain with its rendered route.
- It is not integrated; no absolute network-incision limit is claimed.

**Focused checks**
- 20,000 random compositions preserve the original upper bound, the valley-envelope lower bound and existing hollows.
- 96,048 channel samples stay within physical channel depth; tributary switching stays continuous.
- Six terrain windows pass composition bounds; four earlier blade witnesses retain no slope above 80 degrees.
- The reported transverse bank minimum becomes 42.70 m over offsets 125–500 m; the wet centre retains 0.98 m depth.
- The two formerly dry outlet witnesses pass after the floor join fades to zero; all ten water windows pass presence and 2–16 m approach checks.
- Filter checks retain independent quadrature and derivative comparisons; the historical failure control restores both the old profile and the old signed-detail composition.
- The old blade reference reads the original six slices of the current EXOEROS3 cache through the current decoder; its geometry rules remain historical.
- Diagnostic logs and captures remain local under `x64/water-approach/` and `x64/inland-water/`.
- Release x64 passes with the floor join; the existing `Materials.hlsli:46` bit-shift warning remains.
- `composition-floor-join-perched.bmp` removes the side pools and opens the previously dry cross-ridge; its width remains visually uniform.
- `composition-floor-join-range.bmp` retains the massif's broad shape; repeated incisions and a few distant water/terrain artifacts remain visible.
- No performance or image-quality benchmark was run.

**Volcanic integration remains unresolved**
- These are diagnostic witnesses, not the unidentified crater reported by the user.
- Seed 0 volcano 15: centre 9.3391172538, -50.0430150622; freshness 0.97245; crater radius 2,492.49 m.
- All 128 nominal rim samples lose over 100 m; maximum lowering is 1,378.82 m with the first composition correction.
- Volcano 170: centre 11.6826844900, -51.4192830407; freshness 0.621637; crater radius 523.17 m; maximum rim lowering 980.69 m.
- Volcano 1002, a shield witness, has no rim lowering in the same inspection.
- Freshness currently modifies detail and materials, not drainage incision directly.
- A coarse support can miss a small closed crater; monotone graph stages cannot certify a real outlet through its rim.
- The evidence supports checking common terrain support, construction history and spillways before adding any volcanic exclusion mask.

## 2026-11-01: coarse water classification failure

- User orbital pose: `5717762.1 -13.777632 124.771150 84.18 43.01`, seed 0.
- `orbit-coast-before.bmp` reproduces the broad diamond/triangle coastal fringe at that pose.
- The old pixel shader selected inland water with `interpolatedStage > 0`, although dry land could carry its own positive height as the candidate stage.
- The type switch then replaced the finer ocean shoreline across whole mesh triangles.
- Fine elevation was shaded with `min(stage - fineElevation, meshWaterDepth)`, so dry coarse vertices could erase water resolved on the fine grid.
- Superseded rule: wet coverage required positive mesh water depth and the fine grid had no water samples.
- The replacement carries premultiplied wet quantities at both resolutions and composes independent ocean/inland coverages.
- The running erosion build was the Exolune checkout; terrain shaders dated 18:34 followed the 18:31 composition edit. Shader loading resolves paths beside the executable.
- The user subsequently accepted disappearance of the side trenches at F7/F8 of the extended mountain route; the other hydrology complaints remain in scope.
- Native captures `orbit-coast-after.bmp`, `orbit-water-river18km.bmp` and `orbit-water-river14km.bmp` confirm the removal of the orbital fringe and water presence at both approach poses. Serrated banks, regular junctions and reach interruptions remain; these still images do not validate motion stability.
- Additional witnesses: `orbit-other-coast.bmp`, `orbit-water-lake.bmp` and `orbit-water-mountain.bmp`. A second coast and a lake shoreline preserve their classifications. Mountain water is visible from the overview; its straight path and stair-stepped banks remain.

## 2026-11-01 one-sided coastal filter

- Superseded rule: `delta = max(0.1 Hc, 2 * cellMetres * G)` widened the cliff only landward.
- A 100 m cliff on a 0.2 source slope moved its crest by 78 m at 64 m cells, adding 13.54% to the excavated section.
- At 256 m cells the displacement was 462 m and the added section 80.20%.
- Replacement: compose the physical cliff, talus and min/max joins, then average its incision symmetrically.
- Independent quadrature: 1,440 cases, maximum discrepancy 3.74e-8 m; simulated float32 error 0.12 mm.
- Forty-five join checks and 384 talus sections pass; four terrain windows retain a bit-identical flat coast.
- These are local CPU proofs and witnesses, not global visual or temporal acceptance.

## 2026-11-01 pixel water contour refinement

**Report and reproduction**
- The user still saw moving orbital blocks and late, aliased river banks after the first water reconstruction.
- Latest orbital pose: `4957836.7 -13.909648 124.644062 84.18 43.05`, seed 0.
- Two native CINE reproductions use 120 frames at 60 Hz, 1280 by 720, clouds hidden, TAA unset and 60 warm-up frames.
- The orbital route approaches by 180 km while shifting latitude by 0.08 degrees and longitude by 0.13 degrees.
- The river route descends from the reported 18,045.3 m pose to 14,271 m over the same reach.
- Final artifacts: `x64/inland-water/motion-orbit-review/` and `motion-river-review/`; baseline folders end in `-before`.
- Inspected first, middle and last orbital frames retain the same coastal features without the former broad grid diamonds.
- The river's broad repetitive bank steps are strongly reduced. A narrow interruption in the actual bed remains visible at both ends of the approach.
- `contour-lake.bmp` retains a continuous shoreline; `contour-mountain.bmp` improves the narrow banks but still exposes a straight prescribed route.
- Interactive F4, F7 and F8 were checked after relaunch; F7/F8 still have no artificial side pools. The application was left on F1 in free camera at speed 5.77.
- These are targeted reproductions, not performance or quality benchmarks, nor acceptance of all locations and movements.

**Implementation checks**
- Candidate support survives dry grid samples; the pixel evaluates the shared physical terrain only near unresolved contours.
- Sixteen derivative-quad masks, 2,673 angle/grid-phase cases, 1,380 explicit intersection cases and four dry-floor scales pass in `tools/hydro/verifie_contours.py`.
- The noise table's 256 vectors are bit-identical; the shared frame is 4,800 bytes, with the table at offset 704 and a 4,864-byte constant-buffer allocation.
- Mesh vertices use 64 bytes and fine samples 32 bytes; existing resource bindings are retained.
- Release x64 passes in `x64/inland-water/build-contours-land.log`; the existing material bit-shift warning remains.
- The isolated D3D12 PSO check succeeds with no InfoQueue errors using the final paired shaders.
- A live F1 title showed about 7.64 ms GPU rendering, versus about 2.08 ms in the user's preceding screenshot. This is not a controlled comparison, but the added orbital cost is material and remains open.

**Rejected prototypes**
- FXC compilation of the expanded pixel shader stalled for several minutes; the terrain VS and PS now use DXC with HLSL 2018 syntax.
- Mixing the prior DXBC vertex shader with the DXIL pixel shader failed PSO creation because varying register packing differed; compiling both together resolves it.
- A quad wave-operation prototype was replaced with fine derivatives; no new WaveOps requirement is introduced.
- Divergent evaluations with a large negative clearance sentinel made false wet halos; common derivative-quad evaluation and bounded fallback remove that cause.
- A physical-width-only support cap clipped the averaged channel's halo; support now includes its filter radius.
- Symmetric inland coverage made exactly dry drainage-stage planes half wet; the final inland coverage remains zero at nonpositive clearance.
- Using the pixel-refined height for land materials exposed orbital snow and material hatching. The final query refines water only and retains the existing land-material bandwidth.
- Intermediate folders ending in `-after` or `-final` contain these superseded prototypes; `-review` contains the delivered contour version.

**Remaining limits**
- Pixel classification does not repair bed connectivity, coarse routing, width regularity, closed outlets or volcanic incision.
- Geometry, depth, normals and silhouettes retain their mesh/fine-grid sampling.
- The separate coastal mean composes before filtering; the upstream valley profile still needs equivalent intersection-aware filtering.
- Full wet-area integration below a pixel and the extra cost of contour terrain queries remain unresolved.
