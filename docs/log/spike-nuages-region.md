# Formations nuageuses régionales

**Au log depuis le 2026-10-30 :** spike clos, remplacé par la météo sur la sphère entière, `../spec-nuages.md`. Lanceur et assets de l'essai : tag `piste/nuages-orbite-spike`.

**État, 27 octobre 2026 :** premier essai régional prêt pour le vol. Carte inspectée, trois variantes compilées et quatre captures cachées vérifiées. La répartition étendue est visible ; le rendu lointain conserve du grain répétitif et les cirrus des stries.

**Retour en vol :** l'utilisateur juge les autres nuages corrects et demande de réduire les cirrus trop réguliers. Le [spike orbital](spike-nuages-orbite.md) poursuit ce travail ; cette version régionale reste figée comme témoin dans `x64/NuageFrostbiteRegionalTemoin/`.

**Lancer :**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-region.ps1
```

- F1–F4 : même centre depuis800,200,80 et30 km ; F11 :500 km.
- F5–F7 : deux champs de cumulus et la nappe ; F8–F9 : cirrus ; F10 : éclaircie ; F12 : soleil bas.
- `-Vue Meteo` ouvre la carte fixe ; `-Vue Opacite` ouvre la transmission en3D ; B bascule l'opacité dans le rendu normal.
- `-Temoin` ouvre la scène locale figée des trois familles, avec sa palette.
- C : qualité48/24 m ; Espace : pause/reprise ; V : météo×1/×5 ; météo figée au démarrage.
- `-Build -NoLaunch -Vue Rendu`, `Meteo` ou `Opacite` recompile la variante choisie.

**Objectif :** juger des formations plus vastes et plus nombreuses à plusieurs distances, en gardant les formes locales comme référence.

**Répartition :**

- Carte météo locale de1200×800 km, origine0,5°/161,775° ; projection tangentielle fixe sur les couches sphériques.
- Nappes fragmentées, front irrégulier, régions d'amas de cumulus, cirrus étendus et grandes éclaircies.
- Les variations à plusieurs échelles agissent sur la carte météo.
- Les profils verticaux, textures3D, éclairage et intégration des familles locales sont conservés.
- La carte est un choix artistique explicite, inspiré du découpage météo/type/forme de Frostbite ; aucune simulation météorologique planétaire n'est revendiquée.

**Isolation :**

- Sources, données et binaires des essais précédents conservés.
- Témoin des trois familles : `x64/NuageFrostbiteFamiliesTemoin/`, quarante fichiers copiés, empreintes dans `witness.json`.
- Trois textures3D copiées intégralement depuis `assets/frostbite-families/` ; seule la texture météo2D change.
- R météo : couverture basse ; G : type nappe/cumulus ; B : cirrus ; A inutilisé.
- Mip1 de couverture moyen, mips2+ maximum conservateur ; profil de type moyenné.
- Bornes et enveloppe d'accélération élargies au support régional ; aucun parcours au-delà de la profondeur du terrain.
- Les segments des deux couches restent triés le long du rayon.
- Données, paramètres, empreintes et points de test : `assets/frostbite-regional/regional-manifest.json` et `regional-probes.json`.
- Carte légendée : `assets/frostbite-regional/regional-weather-art-preview.png` ; carte des canaux et recadrage central fournis à côté.

**Remise en main :**

- Examiner d'abord la carte de répartition vue de dessus.
- Puis compiler le rendu régional et faire quelques captures cachées sur plusieurs lieux et distances.
- Palette dans `tools/tests/2026-10-27-nuages-region.txt` ; lancement par `tools/nuages-region.ps1`.
- B : opacité ; C : qualité ; Espace : pause météo ; V : météo×1/×5.
- Les vérifications en vol appartiennent à l'utilisateur ; aucun banc prolongé.

**Contrôle effectué :**

- Trois compilations DXC réussies ; avertissement de décalage binaire préexistant dans `Materials.hlsli`.
- Quatre captures : région depuis800 et80 km, cumulus vus depuis10 km et nappe depuis6 km ; `x64/RegionalPreview/report.json`.
- Trois textures3D identiques aux sources, recette de densité basse inchangée,11 mips météo conformes, mipsR/B de présence conservateurs et bords vides vérifiés.
- Témoin complet et sources figées vérifiés intacts.
- Nuages+air ponctuels :2,93 ms à800 km,5,59 ms à80 km,9,24 ms sur le champ de cumulus,5,15 ms sur la nappe ; GPU partagé, aucune comparaison statistique.
- Sur les deux lieux proches, le calcul GPU du terrain domine aussi le temps total ; les FPS globaux de ces captures ne mesurent pas le seul coût des nuages.
- Les captures rendent les limites lointaines explicites ; elles ne valident pas la stabilité en mouvement.

**Limites à juger séparément :**

- Les bruits3D périodiques peuvent rester reconnaissables sur une grande région.
- Les mips de bruit ne garantissent pas la conservation de la transparence après seuillage.
- L'extension permet d'observer ces limites ; elle ne valide pas encore un rendu stable de l'orbite au sol.
- La couverture et la longueur des parcours peuvent augmenter le coût malgré le saut du vide.
- Le filtrage lointain, la reconstruction temporelle et la répartition sur toute la planète restent des étapes suivantes.

**Mémoire :** cumulonimbus retenu pour une étape ultérieure ; tours et enclumes hors du présent essai.

**Références :** [familles locales](spike-nuages-cirrus.md) ; [référence Frostbite et provenance](spike-nuages-reference.md).
