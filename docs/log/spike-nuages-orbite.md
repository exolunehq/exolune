# Nuages : première intégration orbitale

**Au log depuis le 2026-10-30 :** spike clos. Sa quadrature lointaine est celle des nuages du jeu, `../spec-nuages.md`. Lanceur et assets de l'essai : tag `piste/nuages-orbite-spike`.

**État, 27 octobre 2026 :** essai prêt pour le vol ; rendu, opacité et carte compilés. Quatre vues et deux captures de comparaison inspectées. Les grandes masses sont moins granuleuses depuis l'orbite, avec un surcoût mesuré sur la capture à800 km.

**Retour utilisateur :** les autres nuages régionaux sont jugés corrects ; les cirrus sont trop nombreux et trop régulièrement espacés. Priorité suivante : très haute altitude et orbite.

**Lancer :**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-orbite.ps1
```

- F1–F6 : même région à30,80,150,300,800 et1500 km.
- F7 : vue rasante ; F8–F9 : cumulus et nappe proches ; F10–F11 : cirrus de dessous et de dessus ; F12 : soleil bas depuis800 km.
- B : opacité ; C : qualité ; Espace : pause/reprise ; V : météo×1/×5.
- `-Temoin` ouvre la version régionale figée, avec ses anciens cirrus et sa palette.
- `-SansFiltrage` garde les nouvelles données de cirrus et désactive le seul filtrage orbital ; sortie séparée pour une comparaison à données identiques.
- `-Vue Meteo` et `-Vue Opacite` ouvrent les diagnostics ; `-Build -NoLaunch` recompile la variante choisie.

**Cirrus :**

- MétéoB répartie en groupes irréguliers, avec de grandes zones vides ; moyenne ramenée à26,8% de la version régionale et pics conservés vers0,286.
- Nouveau champ3D de fibres rares et orientées selon plusieurs directions ; façonnage avant les mips de densité.
- Après façonnage,7,42% des texels du mip0 de fibres dépassent0,05 ; les pics atteignent1,0. Ce sont des statistiques du champ, pas une mesure de la couverture du ciel.
- MétéoR/G/A et forme3DR/B/A copiées exactement à chaque mip ; détail32³ et table des profils64³ copiés intégralement.
- La répartition basse, ses profils et la recette des cumulus/nappes restent ceux validés par l'utilisateur.
- Données et empreintes : `assets/frostbite-orbit/orbit-manifest.json` ; source : `tools/gen_frostbite_orbit_assets.py`.

**Filtrage distant :**

- Le rayon central conserve le parcours et les niveaux de détail hérités.
- Le poids distant augmente continûment pour une empreinte du pixel de0,25 à0,8 km au premier segment nuageux.
- Des rampes de sécurité réservent ce premier essai aux caméras au-dessus des couches et aux vues suffisamment plongeantes ; incidence mesurée au point du nuage.
- Mode économique : quadrature2×2 de quatre rayons sous-pixel ; mode plus fin :3×3 de neuf rayons.
- Chaque rayon distant échantillonne la densité fine puis intègre sa propre lumière et sa propre transmittance avant la moyenne.
- Le mélange avec le rayon central porte sur la lumière prémultipliée, la transmittance et les poids de profondeur ; aucune moyenne de densité avant l'exponentielle.
- La composition atmosphérique reste calculée une fois par pixel après la moyenne des rayons nuageux.
- Le centre hérité est aussi tracé pour le mélange : jusqu'à cinq ou dix parcours nuageux par pixel, sans historique temporel ni jitter renouvelé.
- Les données, la phase mondiale et l'horloge partagée restent indépendantes du nombre d'images et de la caméra.

**Isolation :**

- Témoin régional figé : `x64/NuageFrostbiteRegionalTemoin/`, quarante fichiers et sources vérifiés par empreintes.
- Sources et binaires antérieurs conservés ; nouvel exécutable identique au binaire V4, seules les données et shaders isolés changent.
- Publication Git : sources, assets et outils inclus ; `x64/` reste ignoré. Les exécutables figés, captures et manifestes des témoins restent locaux. Les lanceurs requièrent ces sorties natives ; `-Build` recompile les shaders et réutilise le binaire V4 figé.
- Région1200×800 km et enveloppe650 km conservées ; aucune extension à toute la planète.

**Limites :**

- Quatre ou neuf rayons restent une quadrature finie ; ce premier essai ne garantit pas la disparition de tout grain ou scintillement.
- Les textures périodiques peuvent rester reconnaissables à des échelles résolues.
- Les vues rasantes reviennent progressivement au parcours central ; elles ne bénéficient pas toutes du filtrage orbital.
- La profondeur du terrain du pixel central sert aussi aux rayons voisins ; approximation de ce spike surtout maritime.
- Le coût du filtrage reste à juger sur les vues distantes ; le mode plus fin n'est pas une référence convergée.
- Les vérifications en vol appartiennent à l'utilisateur ; aucun banc prolongé.

**Contrôles courts :**

- Rendu, opacité, carte et rendu sans filtrage compilés ; seul avertissement préexistant de `Materials.hlsli`.
- Vues à800 et1500 km, cirrus vus de dessous et point proche à4 km ; comparaison sans filtrage à800 km et au même point proche.
- La vue proche très sombre est identique pixel pour pixel avec et sans filtrage ; ce point de contrôle se trouve dans le volume. Les boutons de survol permettent un départ plus lisible pour le vol.
- Au même point à800 km, nuages+air ponctuels2,88 ms sans filtrage et11,37 ms avec quatre rayons distants ;5,96 ms à1500 km sur une autre capture. GPU partagé, aucun budget global validé.
- Les autres captures donnent11,87 ms sous les cirrus et3,32 ms au point proche ; titres de fenêtre parfois retardés dans le mode batch, seuls les résumés GPU de la capture sont repris ici.
- Canaux bas, copies détail/profils, mips de présence cirrus et empreintes du témoin vérifiés intacts.
- Captures et comptes rendus : `x64/OrbitPreview/` et `x64/OrbitPreviewSansFiltrage/` ; stabilité en mouvement et transitions à juger par l'utilisateur.

**Mémoire :** cumulonimbus retenu pour la suite, hors du présent essai.

**Références :** [répartition régionale](spike-nuages-region.md), [familles locales](spike-nuages-cirrus.md), [provenance Frostbite](spike-nuages-reference.md).
