# Spike : nuages voxelisés sur la planète

**Archive du 27 octobre 2026 :** V3 interrompue à la demande de l'utilisateur avant l'implémentation shader et la compilation. Les sections ci-dessous décrivent le plan envisagé, pas un résultat disponible. Le lanceur et les sources natives ont été remis à la V2 ; ses limites et mesures figurent dans l'[historique](spike-nuages-voxel-planete-historique.md). Le nouveau cadrage est dans [la recherche de référence](spike-nuages-reference.md).

**But :** comparer rapidement une densité voxelisée et son calcul direct pendant un vol du sol à l'orbite.

- Les vérifications en vol restent confiées à l'utilisateur.
- Les contrôles de cette itération se limitent à la compilation et à quelques captures cachées.
- Une branche à part, aujourd'hui dans le tag `piste/nuages-orbite-spike`.
- Les anciens essais et mesures sont dans l'[historique](spike-nuages-voxel-planete-historique.md).

**V3 :** correction du parcours latéral, variété des profils et réduction du coût avec la distance.

- La V2 présentait des stries de côté et répétait une même famille.
- Son pas dépendait de l'inclinaison du rayon et pouvait dépasser 480 m sur les trajets longs.
- La V3 retire cette règle et le plafond de 512 pas qui étirait les échantillons.
- Les zones vides sont sautées selon les supports géométriques, avec des marges ; un échantillon nul de densité ne suffit pas.
- La météo et les identités des formations restent indépendantes de la caméra.

**Champ commun aux deux modes :**

- Six faces de cube sphérique portent chacune 1 023 × 1 023 cellules fixes.
- Les décalages, orientations et dimensions dépendent de ces identités.
- Le voisinage 3×3 conserve les recouvrements.
- La couverture régionale ouvre des trouées et mélange trois profils : cumulus, stratocumulus et nappes fragmentées.
- Il s'agit d'une distribution visuelle simplifiée, sans simulation météorologique.
- Les trois sources de densité servent au bake et au mode procédural.
- Le vent entraîne le repère commun ; le temps météo anime les profils.
- Les références planétaires sont calculées en double ; les boucles utilisent des décalages locaux float.

**Stockage :**

- Texture planétaire `N × N × 3N`, trois volumes contigus sur Z.
- Densité `R32_FLOAT`, 24 Mio à N=128 et 192 Mio à N=256.
- Chaque famille utilise ses propres centres de texels ; aucune interpolation ne traverse une frontière de famille.
- Le volume local validé garde sa texture N³ et son propre binaire.
- La texture est reconstruite au temps météo courant puis publiée entière.

**Lancer :**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuage-voxel-planete.ps1
```

- Binaire : `x64/NuageVoxelPlaneteV3/MyPlanetEngineVoxelPlaneteV3.exe`.
- Options : `-Static`, `-Time 60`, `-Size 256`, `-Clear`, `-Build -NoLaunch`.
- C : comparer voxel et procédural avec le même champ et le même parcours.
- N : couper les nuages et leur bake ; conserver l'air et le terrain.
- Espace : figer la météo ; B : opacité ; V : vitesse météo ×5.
- Palette `tools/tests/2026-10-26-nuage-voxel-planete.txt` : F4 profil latéral, F5 intérieur, F7 horizon, F8 planète entière ; F9 à F11 changent de région.
- Le titre donne le temps GPU « nuages+air », bake compris lorsqu'il est exécuté.

**Limites de jugement :**

- Un LOD de parcours ne suffit pas à filtrer correctement des formations plus petites qu'un pixel.
- La composition de l'air et l'éclairage restent des approximations du spike.
- Une capture statique ne valide pas le scintillement en mouvement.
- Aucun avantage des voxels n'est acquis ; C doit montrer si le cache de densité justifie son coût mémoire et sa reconstruction.
