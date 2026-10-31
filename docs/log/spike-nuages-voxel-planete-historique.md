# Spike voxel planétaire : historique

**Arrêt, 27 octobre 2026 :** la V3 prévue est interrompue avant implémentation shader et compilation. Les préparatifs natifs sont sauvegardés, puis les sources et le lanceur remis à la V2. Le [nouveau cadrage](spike-nuages-reference.md) part de références techniques publiées.

**V1, 26 octobre 2026**

- Une texture 128³ répétée sur six faces de 127 × 127 cellules, soit 96 774 grands bancs.
- Positions et calculs de densité en double à chaque point de vue et de soleil.
- Binaire `x64/NuageVoxelPlanete/MyPlanetEngineVoxelPlanete.exe`, SHA-256 `EA23375D6CA7975B23B471462AB6EBD3D27383E284F41D331290BE66E089EE68`.
- Deux captures initiales conformes au démarrage : `x64/VoxelPlanetStartup/`.
- Leurs titres indiquaient 74,89 ms de rendu GPU à 8 000 km et 58,67 ms en approche ; mesures ponctuelles, sans séparation terrain/nuages.
- Retour utilisateur : environ 10 FPS dans les deux modes C ; blocs répétés empêchant de juger le lointain.
- C changeait la source de densité, avec le même parcours et le même éclairage dans les deux modes.
- Décision : déplacer les calculs planétaires hors des boucles, ajouter une coupure réelle des nuages et mesurer la passe, puis remplacer les grands blocs uniformes par une population plus fine et une couverture régionale.

**V2, contrôle numérique limité**

- Ancrage numérique météo de 32 km par intervalle, avec entrée et références de cellules calculées en double.
- Les boucles utilisent des décalages locaux float ; les positions planétaires complètes ne passent pas en float pour la densité.
- Contrôle CPU ponctuel sur 2 000 paires de points de coquille : erreur maximale d'altitude 3,92 cm, de coordonnée locale 5,61 cm, zéro différence d'identité de cellule.
- Ce contrôle vérifie l'arithmétique ; il ne remplace pas les images ni une validation de stabilité en vol.
- Rapport `x64/VoxelPlanetV2Startup/local-precision.json`.

**V2, première optimisation sans placement large**

- Deux captures statiques : orbite 10,36 ms/frame dont 6,11 ms nuages+air ; approche 6,69 ms/frame dont 3,99 ms nuages+air.
- Contrôle orbite sans nuages : 9,12 ms/frame, dont 0,73 ms pour l'air. Ne pas soustraire les temps de frame entre captures pour isoler une passe ; les timestamps 6–7 mesurent directement cette passe.
- Rapport `x64/VoxelPlanetV2Startup/startup.json`.
- Les centres ne bougeaient encore que faiblement dans leurs cellules ; les rangées restaient visibles.
- Décision : décaler largement les centres, sommer le voisinage 3×3 et autoriser les recouvrements. Ce placement plus riche augmente le coût par rapport à cette première optimisation.

**V2, placement large et retour utilisateur du 27 octobre 2026**

- Six faces de 1 023 × 1 023 cellules fixes ; une seule famille de densité partagée.
- Décalage des centres jusqu'à ±2,1 unités locales, rotation libre, dimensions variables et somme des neuf voisins.
- Deux bruits de couverture régionale déterminent la présence ; les silhouettes restent celles des quatre lobes du POC.
- Binaire `x64/NuageVoxelPlaneteV2/MyPlanetEngineVoxelPlaneteV2.exe` ; EXE `4F02017258B14A9B793EF85C74F3E70BECA3B61A51CDEFDE457F1B1698495C4F`, shader `C9F77F3303FB6FC471B1689A5E79BE2D8C1CE0A9094FEAD1E8104A8996E4C6F3`.
- Captures `x64/VoxelPlanetV2Placement/` : approche 13,66 ms/frame dont 11,34 ms nuages+air ; orbite 26,97 ms/frame dont 24,23 ms nuages+air.
- Deux vues statiques en 720p ; aucune validation de stabilité en vol.
- Retour utilisateur : vue de dessus acceptable, bandes horizontales et scintillement vus de côté ; répétition d'une même famille, coût encore élevé, avantage voxel non démontré.
- Le parcours visait `24 m / max(vitesse radiale, 0,05)` ; il pouvait atteindre 480 m avant le plafond de 512 pas, qui augmentait encore le pas des trajets longs.
- Cette règle sous-échantillonne les structures latérales par rapport aux 37,8 m du volume local 128³.
- Décision : remplacer cette règle, sauter les supports vides, introduire un LOD de parcours et de lumière, puis trois profils communs au bake et au calcul direct.
- La palette V2 est conservée sous `tools/tests/2026-10-26-nuage-voxel-planete.txt` ; la V3 utilise une nouvelle palette.
