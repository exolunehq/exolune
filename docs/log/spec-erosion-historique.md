# Historique de la spec d’érosion

**Modèles côtiers remplacés ; voir [la spec actuelle](../spec-erosion.md).** Piste `piste/erosion-globale`.

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
