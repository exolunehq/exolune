# POC : nuage stable et animé

**Au log depuis le 2026-10-30 :** POC clos. Les nuages du jeu sont décrits par `../spec-nuages.md`. Sources et lanceur de l'essai : tag `piste/nuages-orbite-spike`, qui contient la branche `codex/nuage-poc`.

**But :** une formation cohérente quand on s'approche, qui évolue avec le temps. La référence figée a été validée en vol par l'utilisateur le 26 octobre 2026. Cette itération ajoute un mouvement météo partagé et des franges plus légères. Branche `codex/nuage-poc` ; vérifications end to end confiées à l'utilisateur à sa demande.

**Lancer :** `powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuage-poc.ps1`. Ajouter `-Build` après modification, `-Build -NoLaunch` pour compiler seulement. Binaire animé : `x64/NuagePoc/MyPlanetEngineAnime.exe`. Le binaire précédent peut rester ouvert : il est distinct. L'exécutable et les shaders validés sont aussi conservés dans `x64/NuagePocReference/` ; réglages et mesures dans `poc-nuage-stable-historique.md`.

**Contrôles :**
- **Espace :** mettre en pause ou reprendre la météo, en gardant la caméra libre.
- **V :** vitesse météo normale ou ×5. La barre de titre donne le temps, la pause et la vitesse.
- **B :** opacité en blanc sur fond noir, ou rendu éclairé, pour séparer le contour de l'éclairage.
- **F1–F8 :** loin, approche, bord, entrée, intérieur, autre face, dessus et dessous. Ces vues suivent le déplacement du nuage sans remettre l'horloge à zéro. Le lancement commence sur l'approche, à environ 3,3 km du centre.
- Flèches pour se déplacer, Page haut/bas pour monter/descendre, bouton droit et souris pour regarder, molette pour la vitesse de vol.

**Comparer à temps figé :** `tools/nuage-poc.ps1 -Static`, ou Espace dans l'app. `-Time 60` démarre à 60 secondes ; F2 recale la vue sur le nuage actuel. L'horloge ne dépend ni du nombre d'images, ni du déplacement de caméra, ni des changements de vue. Les bancs sans fenêtre gardent le temps fixé.

**Le mouvement est un champ commun :**
- Vent vers l'est : rotation partagée autour de l'axe de la planète, 12 m/s à l'équateur, vitesse locale proportionnelle au cosinus de latitude. Le centre et les coordonnées de densité utilisent le même déplacement inverse.
- Déformation : trois ondes spatiales larges, de périodes 120, 150 et 200 s, évaluées dans les coordonnées de la planète entraînées par le vent. Aucun déphasage lié à l'identité d'un nuage. Déplacements de 80, 40 et 60 m au plus sur les axes de la planète.
- Détail : remontée commune d'environ 1,71 m/s dans la tuile 3D. Les périodes et le défilement bouclent continûment à 2 400 s ; les phases restent précises en flottants.
- Coût : même tuile, toujours deux lectures 3D par évaluation de densité ; trois ondes analytiques en plus. Aucun volume animé à recalculer ou cache météo supplémentaire.

**Aspect moins solide :** extinction maximale de 24 à 16 /km, franges élargies de 0,18 à 0,26 dans le profil puis adoucies au carré, base plus progressive et éclairage diffus de 0,18 à 0,22. Le cœur reste opaque ; l'objectif est une enveloppe plus vaporeuse, pas de rendre tout le cumulus transparent.

**Ce qui reste de la référence :** quatre lobes centrés à 4 000 m, position relative soustraite en double précision ; ray marching en pleine résolution, au plus 384 pas de 12 m, six points vers le soleil. Sans cascade, damier, jitter, historique temporel ou halo. La touche T garde le lissage désactivé. L'air est inséré au centroïde d'opacité, sans rétroaction sur la forme. Pas d'ombre de ce nuage au sol.

**Critères en vol :** en pause, même stabilité d'approche que la version validée. En marche, le nuage dérive et ses contours évoluent lentement même avec une caméra immobile. Bouger la caméra ne doit pas accélérer ni déclencher cette évolution. La pause reprend sans saut ; F1–F8 ne rajeunissent pas la formation.

**Portée :** une seule formation dans le POC ; la loi de mouvement est partagée et réutilisable, mais la couverture nuageuse de la planète n'est pas intégrée ici. Les lobes, densités et vitesses sont des réglages de maquette. Le rendu normal reste accessible sans `MYPLANETENGINE_CLOUD_POC`.

**Fichiers :** `CloudMotion.hlsli` pour le champ commun, `CloudPoc.hlsli` pour la densité et l'éclairage, `D3DApp.cpp` pour l'horloge et le vent. Tous sous `MyPlanetEngine/`. Le passage plein écran est compilé par DXC pour les itérations rapides.

**Contrôles sans fenêtre :** `python tools/banc_nuage_poc.py <exe> <sortie> [--reference <exe-v1>]`. Le banc compare une caméra fixe à plusieurs temps, suit le vent pour isoler la déformation, revient au même temps après d'autres vues et contrôle le raccord de la phase à 2 400 s. Format batch : `sortie.bmp vue hauteur latitude longitude inclinaison cap [faceFactor [weatherTime]]`. `MYPLANETENGINE_WEATHER_TIME` fixe le temps par défaut ; `MYPLANETENGINE_VIEW=clouds` rend l'opacité réellement intégrée. Le banc de qualité planétaire reste hors du périmètre de ce POC local.

**Validation de cette itération :** compilation complète et cinq vérifications du banc réussies. Revenir à la même vue et au même temps redonne une opacité identique au pixel près. Déformation visible après compensation du vent et raccord continu à 2 400 s. Vue d'approche : 36 739 pixels partiellement transparents contre 24 907 dans la référence. Rendu médian mesuré à 2,75 ms contre 1,93 ms pour la version complète précédente, sur la même vue de ce poste. Détail et limites dans `../journal-planete.md` ; sorties locales sous `x64/NuagePocAnimationCheck/`. Jugement en vol attendu de l'utilisateur.
