# POC nuage : référence figée, 26 octobre 2026

**Validée en vol par l'utilisateur :** position, forme et contours stables à l'approche ; aspect jugé satisfaisant. La suite demandée est le mouvement avec le temps et des franges moins solides.

**Référence conservée localement :** `x64/NuagePocReference/`, exécutable et shaders de la version validée. Le premier build était dans `x64/NuagePoc/`, sous le nom `MyPlanetEngine.exe`. Branche de travail `codex/nuage-poc`, sans commit ni push demandés.

**Réglages initiaux :** centre à 4 000 m, 0,5 N, 161,5 E ; quatre lobes, tuile 3D fixe à 4,096 et 1,024 km ; extinction au plus 24 /km, fondu du corps de 0 à 0,18, fond diffus de 0,18. Pleine résolution, pas d'au plus 12 m, 384 pas maximum, six points vers le soleil. Sans animation, cascade, damier, jitter, historique ou halo.

**Contrôles sans fenêtre :** cinq captures à 1 280 × 720 (loin, approche, bord, intérieur et opacité). Huit images d'opacité avec caméra fixe et maillage mobile : différence moyenne 0,0000355 sur 255, maximale 1 sur 255. Ce contrôle ne démontrait pas le vol réel ; l'utilisateur a ensuite validé celui-ci.

**Itérations :** l'ensemble des passages plein écran doit utiliser le même format de shader ; DXC pour le sommet plein écran, l'atmosphère, les tons et le halo. Un mélange DXBC/DXIL avait empêché la création du pipeline pendant la mise au point ; corrigé avant livraison.

**Suite actuelle :** `poc-nuage-stable.md`.
