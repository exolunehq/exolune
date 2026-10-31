# POC : nuage voxelisé

**Au log depuis le 2026-10-30 :** POC clos, remplacé par les références publiées des spikes Frostbite. Sources et lanceur de l'essai : tag `piste/nuages-orbite-spike`.

**But :** obtenir rapidement un volume voxelisé à juger en vol, à côté du POC procédural validé.

**Retour utilisateur, 26 octobre :** « ça fonctionne ». L'[essai planétaire](spike-nuages-voxel-planete.md) est arrêté le 27 octobre ; un [nouveau cadrage](spike-nuages-reference.md) compare des bases techniques publiées.

**Isolation :** une branche à part, aujourd'hui dans le tag `piste/nuages-orbite-spike`. Base `7298330`.

**État :** compilé en Debug x64. Une capture cachée 128³, à temps 0, est produite en 1 280 × 720 sans erreur. Le nuage est visible ; aucun verdict de stabilité en vol ou de performance finale n'est acquis. L'utilisateur réalise les essais end to end.

**Binaire :** `x64/NuageVoxelPoc/MyPlanetEngineVoxel.exe`. Empreinte SHA-256 `658C6FC9337E7D9B0B1E281A1301295CEFBDCF10D9F5CD8ABDE0713C907057C4`. Capture et contrôle de démarrage : `x64/VoxelStartup/voxel128.png` et `startup.json`.

**Principe :**

- Stocker la densité finale du même nuage à quatre lobes dans une texture 3D R32_FLOAT.
- Garder le cube local `[-2,4 ; +2,4] km` fixé au repère du nuage.
- Générer le volume à partir de la même fonction procédurale, avec la météo du temps courant.
- Recalculer quand la phase météo change ; réutiliser le volume pendant la pause.
- Lire la densité par interpolation trilinéaire, sans mipmap.
- Garder le vent global, les rayons de vue et de soleil, l'éclairage et la composition du POC.
- Comparer les deux lectures de densité à pose et temps identiques avec C.

**Résolutions :** 128³ par défaut, environ 37,8 m entre échantillons et 8 MiB de densité. Option 256³, environ 18,8 m et 64 MiB. Ces tailles excluent les autres ressources du moteur et l'alignement des allocations.

**Lancer, une fois compilé :**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuage-voxel-poc.ps1
```

**Variantes :** `-Static` pour vérifier l'approche à temps figé ; `-Size 256` pour la grille plus fine ; `-Time 60` pour un autre temps initial ; `-Build -NoLaunch` pour compiler seulement.

**Contrôles :** C voxel/procédural ; Espace pause/reprise ; B silhouette ; V météo ×5 ; F1–F8 vues de la palette. Flèches, Page haut/bas et souris comme dans le POC précédent.

**Essai manuel court :** figer le temps, avancer vers le contour et entrer dans le nuage ; basculer C sur les mêmes vues ; reprendre la météo ; essayer le dessus et l'autre face. Relever les changements de contour, le flou, les éventuels blocs et la fluidité.

**Portée :** premier volume local dense. Aucune couverture planétaire, brique creuse, transition de résolution ou validation de performance finale. Le coût de reconstruction en animation fait partie de l'essai. Les voxels ne prouvent pas à eux seuls la stabilité ni la transparence lointaine.
