# Optimisation de la végétation : essais du 2026-10-27

**Base :** `piste/vegetation-optimisation-base` ; suite dans `../optimisation-vegetation.md`.

**Premier candidat :**
- Second scan, remise à zéro et recopie bornés par des commandes indirectes portant la longueur GPU.
- Termes atmosphériques des imposteurs calculés au vertex au lieu du pixel.
- Quatorze BMP identiques à la référence, mêmes comptes et aucun dépassement.
- Aucun gain démontré sur la première série ; les temps de placement augmentent.
- Une répétition de la référence montre aussi des écarts importants ; la cause de chaque écart ne peut pas être attribuée à une modification seule.
- Variante retirée de la livraison ; rapports dans `x64/VegetationPerf/mesure_candidat/` et `mesure_reference_b/`.

**Deuxième candidat :**
- Dispatchs directs ; les groupes du second scan quittent selon le nombre GPU de tuiles retenues.
- Premier scan inchangé ; même essai atmosphérique.
- Quatorze BMP identiques, mêmes comptes et aucun dépassement.
- Une application de rendu distincte démarre pendant la série ; les derniers temps augmentent fortement, sans instance du banc laissée ouverte.
- Le GPU reste occupé à environ 95 % après la fin du banc ; ces temps ne démontrent pas une régression du code.
- Le programme extérieur est conservé ; aucune application d'un autre travail n'est interrompue.
- Rapport : `x64/VegetationPerf/mesure_candidat2/`.

**Pistes non engagées :**
- La profondeur reconstruite des imposteurs ne se borne pas sûrement par la seule boîte du modèle.
- Les faibles alphas peuvent tirer la profondeur vers la caméra ; aucune annotation de profondeur conservatrice n'est activée sans preuve.
- Un instantané de profondeur peut rejeter des pixels avant les lectures de visibilité, mais ajoute copie, transitions et lectures ; il reste à mesurer séparément.

**Troisième candidat :**
- Quatre valeurs par thread pour les scans et leurs additions ; moins de groupes et de barrières, préfixes exclusifs conservés.
- Les fonctions trigonométriques des quatre vues d'imposteurs sont réutilisées depuis le vertex ; l'essai atmosphérique est retiré.
- Quatorze images identiques, mêmes comptes, aucun dépassement.
- Sur GPU libre, le dessin gagne environ 4 à 7 % dans les forêts denses ; le placement ne montre pas de gain stable selon le lieu.
- Les nouveaux scans sont donc retirés ; seule la réutilisation des vues entre dans la livraison suivante.
- Rapports : `x64/VegetationPerf/reference_libre/`, `candidat_libre/` ; sources de cet essai sous `source_candidat3/`.

**HiZ : variantes écartées :**
- Une partition d'imposteurs proches comme occluseurs change leur ordre de dessin et les gagnants aux profondeurs égales ; elle est retirée.
- Une nouvelle compaction et quatorze dispatchs indirects ajoutent des files et du travail ; la version retenue conserve les files et utilise un masque de 128 Kio.
- Un repli à la première élévation désactive le culling des arbres lointains vus du dessus ; il est remplacé par la borne de la paire de vues effectivement utilisée.
- La simple boîte physique du modèle ne borne pas la profondeur reconstruite ; la version retenue utilise les moments HALF et les erreurs de filtrage.

**HiZ : mesures intermédiaires :**
- Plusieurs rendus de rivières et de nuages extérieurs redémarrent pendant les séries séquentielles ; ces temps ne servent pas au jugement final.
- Les séries `scout_*`, `libre_*` et `hardware_*`, sous `x64/VegetationHiZ/`, servent à vérifier images, comptes et ressources.
- La série `matrix` compare les quatre états dans chaque cycle du même processus ; six vues et 64 cycles par vue, sans autre processus MyPlanetEngine observé durant cette série.
- Le banc général final est comparé au témoin courant, en conservant les écarts déjà acceptés envers la référence canonique.

**Le vol de comparaison, retiré le 2026-10-30 avec son lanceur :**
- `tools/lance_vegetation_perf.ps1` ouvre la version retenue ; `-Reference` retrouve les shaders témoins, sans changement de peuplement.
- Les deux vols utilisent le même exécutable et diffèrent seulement par leurs shaders d'imposteurs ; les binaires de mesure figés restent sous `x64/VegetationPerf/`.
- Palette `tools/tests/2026-10-27-vegetation-performance.txt` : clairière et forêts, six familles climatiques, côte, mer et orbite.
- Un seul vol à la fois pour comparer les performances.
- Le temps de la mer redevient animé en vol.
- Le lanceur passait par `tools/lance_planet_foliage.ps1`, retiré le même jour avec les modes du feuillage ; les deux restent au tag `jalon/25-vegetation-performance-main`.
