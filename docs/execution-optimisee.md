# Exécution optimisée

**Lancer :** `powershell -NoProfile -ExecutionPolicy Bypass -File tools/lance_optimise.ps1`.

- Le lanceur prépare `x64/Optimise/MyPlanetEngine.exe`, ses shaders et `MyPlanetEngine.ini` ; un double-clic sur cet exécutable reprend ensuite le profil.
- `-Build` reconstruit le natif Release x64 et les shaders par le lanceur Planète ; `-NoLaunch` prépare les fichiers sans ouvrir de fenêtre.
- Les assets restent dans le dépôt et les scans à leur emplacement configuré ; cet exécutable ne se déplace pas seul.

**Affichage :**

- Plein écran sans bordure sur le moniteur principal, à sa résolution native au démarrage.
- VSync désactivée dans ce profil ; cadence non limitée au rafraîchissement par l'application, sous réserve du compositeur et du pilote.
- Le flag DXGI de présentation libre est utilisé seulement si le système le supporte ; compatibilité VRR selon le pilote et l'écran.
- Alt+Entrée alterne plein écran et fenêtre ; Échap revient en fenêtre, puis ferme l'application au second appui.
- F1–F12 gardent les douze vues végétales ; la palette de boutons apparaît en mode fenêtre.
- Le passage en fenêtre conserve la résolution interne et étire l'image ; pas de réallocation des volumes, des cibles HDR et du HiZ pendant le vol.
- `-Fenetre` démarre en fenêtre ; `-VSync` active la synchronisation ; `-Resolution '1280 720'` garde le coût du720p même en plein écran. Choisir le même rapport largeur/hauteur que l'écran pour éviter l'étirement.
- Le profil indique ces choix dans `[Affichage]` ; `Resolution=auto` choisit le moniteur pour le plein écran,1280×720 pour les captures sans fenêtre.
- Les variables `MYPLANETENGINE_FULLSCREEN`, `MYPLANETENGINE_VSYNC` et `MYPLANETENGINE_RESOLUTION` prennent le pas sur le fichier ; les bancs restent invisibles.

**Rendu et compilation :**

- GPU haute performance demandé à DXGI ; nom réellement retenu, résolution et VSync inscrits dans le titre.
- Release x64 : `/O2`, fonctions en ligne, préférence vitesse, optimisation globale et édition de liens LTCG ; aucune approximation flottante nouvelle.
- Végétation de jeu, catalogue climatique, HiZ et profondeur matérielle ; nuages Planète avec ombres et mer FFT.
- Densité, portée et seuils LOD conservés ; qualité Éco des nuages comme dans le vol précédent.
- La météo démarre en pause pour les comparaisons ; Espace la reprend et V alterne×1/×5.

**Coût et limites :**

- 1920×1080 comporte2,25 fois plus de pixels que1280×720 ; les FPS à résolution native peuvent baisser malgré la présentation libre.
- Le profil ne promet ni FPS minimal ni occupation de tous les cœurs ; les passes de nuages, de terrain et de placement gardent leur coût.
- Le moteur attend encore la fin GPU de chaque image ; les allocateurs, constantes et lectures CPU partagés exigent des ressources par image avant d'autoriser plusieurs images en vol.
- Aucun réglage global de Windows ou du pilote n'est modifié.

**Références :** [DXGI, présentation et VRR](https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/variable-refresh-rate-displays), [préférence GPU haute performance](https://learn.microsoft.com/en-us/windows/win32/api/dxgi1_6/ne-dxgi1_6-dxgi_gpu_preference).

**Contrôles du28 octobre :** trois vues720p comparées, un pixel différent au total ; deux vues1080p en forêt et sur la mer, sans fenêtre ni dépassement végétal. Plein écran natif et retour en fenêtre observés ; aucun gain global de FPS chiffré.
