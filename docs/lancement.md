# Lancer l'app

**L'exécutable seul est le jeu :** `x64\Release\MyPlanetEngine.exe`, sans aucune variable. Pour juger en vol, `tools/lance.ps1` le compile au besoin, puis l'ouvre avec la palette « Tests ».

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Build -NoLaunch
powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Parcours tools\tests\<date>.txt
```

## Avant le premier lancement d'une worktree

**Les binaires des plantes ne sont pas versionnés :** `assets/foliage/.gitignore` les exclut. Sans eux, l'app vole sans plantes et son titre dit « végétation absente ».

- **Le catalogue de vol :** `assets/foliage/climate_shrubs_v2`, deux arbres et douze arbustes.
- **Le construire,** une fois, depuis la racine : `tools\plantes.ps1` télécharge les modèles sources (`assets/foliage/README.md`), les importe et cuit le catalogue. Python 3 est nécessaire ; environ 3 minutes et 750 Mo. Il est publié à côté des dépôts, `plantes/climate_shrubs_v2`, où tous les worktrees le trouvent.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\plantes.ps1
```

- **Les scans,** s'ils manquent, sont téléchargés par `tools\lance.ps1` au premier lancement.

- **Les imposteurs du 2026-10-29 :** couleurs moyennées en linéaire (`vegetation-planetaire.md`, l'éclairage des imposteurs). Un catalogue construit avant `7f462fc` garde les anciens imposteurs, plus sombres. Les recuire seuls, sans toucher aux maillages ni aux volumes :

```powershell
python tools/foliage/bake.py --impostor-only --out assets/foliage/climate_shrubs_v2 game_broadleaf game_fir shrub_boreal_0 shrub_boreal_1 shrub_desert_0 shrub_desert_1 shrub_montane_0 shrub_montane_1 shrub_steppe_0 shrub_steppe_1 shrub_temperate_0 shrub_temperate_1 shrub_tropical_0 shrub_tropical_1
```

- **Les scans :** `..\scans` à côté du dépôt par défaut, ou `-Scans <dossier>`, ou `MYPLANETENGINE_SCANS`. Le sable et la roche litée en viennent ; `tools\telecharger_scans.ps1` les retélécharge.
- **Les données des nuages :** `assets/clouds`, trouvé au-dessus de l'exe comme le vaisseau ; provenance dans son `manifest.json`.
- **Le build :** `-Build` compile la solution en Release x64, l'exe et ses shaders dans `x64\Release`. Une worktree sans `x64/` recompile tout, environ 8 minutes. En Debug, MSBuild avec `/p:Configuration=Debug` sort `x64\Debug\MyPlanetEngine.exe`.

## Les options du lanceur

- **`-Build`,** **`-NoLaunch`** : compiler, puis ne pas ouvrir.
- **`-Parcours <fichier>`** : la palette « Tests », un bouton par ligne et F1 à F12 ; `tools\tests\vues.txt` par défaut. Une ligne : `libellé | alt lat lon tangage cap [vue] | lat lon du soleil`, la vue étant un nom de `MYPLANETENGINE_VIEW`, facultatif ; sans elle, le rendu du jeu.
- **`-Position '<alt> <lat> <lon> <tangage> <cap>'`** : la vue de départ, le globe par défaut.
- **`-Soleil '<lat> <lon>'`** : le soleil, `10 -5` par défaut.
- **`-Resolution '1920 1080'`** par défaut, plein écran ; `fenetre` pour la fenêtre 1280x720, où la palette s'affiche.
- **`-PassePleine`** : les nuages en passe unique, sans leur passe temporelle (`optimisation.md`) ; pour comparer.
- **`-Scans <dossier>`** : les photos de sol.

**Il efface les `MYPLANETENGINE_*` de la session le temps du lancement, puis les restaure.** Il ne pose que `MYPLANETENGINE_TESTS`, `_SUN`, `_RESOLUTION` et `_FULLSCREEN`, `_SCANS`, et `_CLOUD_FULL` avec `-PassePleine`.

## Le jeu par défaut, et les variables des bancs

- **Les nuages :** toujours, dans leur passe temporelle. Leur météo démarre en pause, à l'instant 0.
- **L'antialiasing temporel :** coupé au démarrage ; la touche T le rétablit.
- **Le halo de l'objectif :** coupé.
- **Les variables d'exception,** pour les bancs et les comparaisons :

| Variable | Effet |
|---|---|
| `MYPLANETENGINE_NO_CLOUDS` | Sans nuages, comme la touche N |
| `MYPLANETENGINE_CLOUD_FULL=1` | Nuages en passe unique |
| `MYPLANETENGINE_WEATHER_TIME` | L'instant de la météo, en secondes |
| `MYPLANETENGINE_TAA` | L'antialiasing temporel dès le démarrage |
| `MYPLANETENGINE_GLARE` | Le halo de l'objectif |
| `MYPLANETENGINE_VIEW` | Une vue de diagnostic ; celles du terrain brutes, sans nuages ni air, sauf `ground`, la silhouette des nuages |
| `MYPLANETENGINE_SEED` | Une autre graine pour la carte tectonique et le climat, pour comparer des planètes ; le bruit du détail garde la sienne |

- **Les vues des nuages :** `clouds`, leur opacité ; `weather`, la carte météo de la planète ; `cloudshadow`, leur ombre sur toute surface tournée vers le soleil. Les deux dernières passent en passe unique.
- **Les vues de la carte tectonique,** de l'orbite à 500 km : `plates`, `boundaries`, `boundarydist`, `crustage`, `rocktype`, `uplift` ; et `relief`, le relief en teintes et au soleil, le fond de la mer compris (`spec-relief-tectonique.md`).
- **Les vues du climat,** de l'orbite : `precipitation`, la pluie de l'année ; `wind`, le vent dominant et ses flèches ; `temperature`, celle du sol, en gris (`spec-climat.md`).
- **Le profil d'exécution,** `tools/lance_optimise.ps1` et `MyPlanetEngine.ini` (`execution-optimisee.md`), lance le même jeu, avec la palette `tools\tests\vues.txt`.
- **Les bancs** posent leurs exceptions eux-mêmes ; ils ne tournent que sur demande (`AGENTS.md`).

## Le mode cinématique

**Un parcours précalculé, une image rendue par pas fixe, sans audio ni commande de vol.** La fenêtre reste cachée, comme les captures automatisées ; le temps de calcul ne change pas le temps du film.

| Variable | Effet |
|---|---|
| `MYPLANETENGINE_CINE` | Chemin du parcours ; exclusif de `BATCH`, `CAPTURE` et `TREMBLE` |
| `MYPLANETENGINE_CINE_OUT` | Dossier existant où écrire les images et `cine.log` |
| `MYPLANETENGINE_CINE_RANGE="0 600 120"` | Première image, nombre d'images, nombre d'images de chauffe |
| `MYPLANETENGINE_RESOLUTION="640 360"` | Dimensions du rendu ; mêmes bornes que les autres captures |

- **Sans plage :** tout le parcours, avec 120 images de chauffe.
- **La chauffe rejoue les images précédentes sans les écrire.** Avant l'index 0, elle répète sa pose ; les horloges et les phases temporelles avancent jusqu'à cette première image.
- **Le pas vaut `1/fps` :** mer, plantes, état du verre et historiques ; la météo prend exactement l'instant de chaque ligne, comme `MYPLANETENGINE_WEATHER_TIME`.
- **L'historique est conservé,** sauf au passage extérieur/cockpit ; le cockpit prend l'œil et la tête au repos du jeu, sans inertie de tête.
- **La pince GPU lit le relief courant sous les deux poses.** Toute intervention écrit l'index et `pince camera` ou `pince vaisseau` dans `cine.log` ; coque à 2,5 m, caméra à 1 m au moins.
- **Les images s'appellent `frame_00000.bmp`,** puis `frame_00001.bmp` ; l'index reste global dans une plage ; l'application ferme après la dernière.
- **Une erreur renvoie un code non nul** et écrit `<parcours>.error.txt`.

**Le fichier du parcours, UTF-8, séparateurs blancs, point décimal :** commentaires `#`, première ligne utile `fps 60`, puis exactement :

```text
index vue navLat navLon navAlt navCap navTangage navRoulis camLat camLon camAlt camCap camTangage camRoulis fov meteo
```

- **Indices contigus, à partir de 0 ;** `vue` vaut `exterieur`, `cockpit` ou `pleine` (l'œil du pilote sans habitacle ni coque, la pose `cam*`).
- **Angles en degrés :** latitude nord positive, longitude est positive, cap depuis le nord vers l'est, tangage positif vers le haut, roulis positif à droite.
- **Altitudes en mètres au-dessus du niveau marin 0 ;** `fov` vertical, entre 5 et 150° ; `meteo` en secondes, non négatif.
- **En extérieur,** chaque pose est indépendante ; coque, ombres et panache suivent le vaisseau ; les gaz sont déduits du mouvement.
- **En cockpit,** les six valeurs `cam*` restent requises mais l'œil est déduit de `nav*` ; intérieur, pluie et givre suivent le rendu du jeu.

**Générer, depuis la racine :** Python 3 et NumPy, sans SciPy ; `cp.py` lit `x64/Release/tectonique-0.bin`, produit par un lancement du moteur, ou `EXOLUNE_TECTONIQUE` (`spec-relief-tectonique.md`).

```powershell
python tools/cine/parcours.py tools/cine/essai.json x64/cine/essai.parcours
powershell -NoProfile -ExecutionPolicy Bypass -File tools/cine/rendre.ps1 -Parcours x64/cine/essai.parcours -Sortie x64/cine/essai-640 -Resolution '640 360'
```

- **Le scénario JSON :** `fps` (60), `graine` (0 sur cette branche), `depart: [lat, lon, altitude]`, `meteo` (0), `vitesse_meteo` (1), puis `segments`.
- **Chaque segment :** `type`, `duree` en secondes, `point: [lat, lon]` ou `points: [[lat, lon], ...]`, `hauteur` au-dessus du sol, et `camera`.
- **`orbite` :** descente exponentielle depuis l'altitude précédente, courbée vers le point, à `hauteur` (150 m par défaut), ou `altitude` absolue explicite.
- **`ascension` :** la même loi exponentielle, de bas en haut, jusqu'à l'`altitude` demandée ; un point proche donne l'angle de montée.
- **`approche`, `atterrissage`, `decollage` :** raccord à la hauteur du point, respectivement 100, 4 et 100 m par défaut.
- **`pause` :** pose maintenue ; `rase-mottes` : points de passage à `hauteur` au-dessus du relief (150 m par défaut) ; `mer` : hauteur au-dessus de 0 (20 m par défaut).
- **Les segments sont raccordés en position, vitesse et accélération.** Seuls la fin d'un atterrissage, toute la pause et le début d'un décollage imposent l'arrêt ; les points de passage restent traversés en spline quintique ; cap tangent, tangage selon la pente, roulis selon la courbure.
- **La vitesse suit la longueur du trajet sécurisé,** avec une croisière centrale et deux raccords doux aux vitesses voisines ; les distances entre points ne commandent pas les accélérations. L'orbite conserve sa décroissance exponentielle d'altitude, donc sa vitesse variable.
- **Caméra :** chaîne `cockpit`, ou objet `{"type":"poursuite","distance":22,"hauteur":8,"fov":60}` ; `libre` accepte aussi `cap_relatif` (90° par défaut), `regard:"paysage"`, `cap` et `tangage` ; `pleine` place l'œil à `hauteur` (1,1 m) au-dessus de la pose, regard selon le cap et le tangage du vaisseau, décalé de `cap_relatif` et `tangage` (−4°).
- **`fondu` :** durée du raccord de pose en secondes, 1 par défaut ; seules les transitions cockpit coupent ; entre deux vues pleines, il tourne la tête ; 0 coupe.
- **La sécurité du générateur :** `bande` de part et d'autre (40 m), `pas_sol` longitudinal et transversal (10 m), `cellule` du relief CPU (1 m), `marge` du terrain (12 m ; surcharge possible dans chaque segment ; atterrissage à la hauteur demandée).
- **Une surélévation lisse garde la bande libre** après les splines ; en rase-mottes, la hauteur demandée devient la garde minimale sur cette bande, avec 2 m de marge si une correction est nécessaire ; après la reparamétrisation en longueur, seule la `marge` reste exigée ; la caméra vérifie aussi sa bande.
- **Le segment `mer` doit rester sur l'eau :** un passage sur du terrain émergé est refusé ; sa hauteur se compte depuis le niveau marin 0, jusqu'à 3 m, sans la marge du terrain ; aucune géométrie du monde n'est modifiée.
- **Le résumé `<sortie>.resume.json`** donne durée, vitesses minimale, moyenne et maximale, garde minimale par segment et empreinte du parcours ; les extrema de vitesse incluent le raccord de fin.

**Rendre le film :** `rendre.ps1` prend des plages de 600 images et 120 de chauffe ; `-Plage` et `-Chauffe` permettent un essai plus court.

- **Un seul moteur à la fois :** le script refuse de démarrer si un MyPlanetEngine est déjà ouvert ; il n'en arrête aucun.
- **Encodage :** `C:\ProgramData\chocolatey\bin\ffmpeg.exe`, H.264, CRF 14, 60 images/s, `yuv420p` ; `ffprobe.exe` vérifie le compte des images avant tout effacement.
- **Disque :** les BMP d'une plage sont supprimés dès que son MP4 est vérifié ; les MP4 de plages restent, puis sont concaténés en `<Sortie>/film.mp4`.
- **Reprise :** relancer la même commande ; `rendu.json` vérifie parcours, moteur, shaders et réglages ; seules les plages complètes sont réutilisées.
- **Le script isole et restaure les variables du moteur ;** il active le TAA et garde les chemins explicites des scans et des plantes.
- **Les contrôles CPU ciblés :** `python tools/cine/test_parcours.py` ; ils ne lancent aucun moteur ni banc.

## Les touches en vol

- **H :** le fondu imposteur-maillage des arbres, actif par défaut ; coupé, chaque arbre bascule d'un coup.
- **T :** l'antialiasing temporel.
- **O et P,** maintenues : le soleil tourne.
- **Espace, V :** la météo reprend ou s'arrête ; sa vitesse ×1 ou ×5.
- **N :** les nuages, oui ou non. **C :** leur qualité, Éco ou Référence. **B :** la vue du sol, sous la silhouette des nuages.
- **F :** fil de fer. **R :** ombrage facetté. **G :** le maillage du terrain ne suit plus la caméra.
- **K et L,** ou **− et + :** maillage du terrain plus fin ou plus grossier, pour tester.
- **F1 à F12 :** les tests du parcours. **Échap :** fenêtre, puis fermeture.
