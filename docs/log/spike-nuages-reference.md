# Référence locale guidée par Frostbite

**Au log depuis le 2026-10-30 :** spike clos. Sa recette, les bruits de Frostbite, les profils et l'extinction de 80/km, est reprise par les nuages du jeu, `../spec-nuages.md`. Lanceur, shaders et assets de l'essai : tag `piste/nuages-orbite-spike`. Les commandes ci-dessous décrivent l'essai, pas le lancement courant, `../lancement.md`.

**État, 27 octobre 2026 :** rendu local et stabilité à l'approche validés en vol par l'utilisateur pour le cumulus et la nappe. Cette version reste le témoin des essais de nouvelles familles. Aucun résultat planétaire validé.

**Lancer le rendu :**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-frostbite-reference.ps1
```

- Météo figée par défaut ; F1–F6 : cumulus ; F7–F11 : nappe ; F12 : deux zones vues de dessus.
- B : opacité sans éclairage ; C : pas économique48 m / référence24 m ; Espace : pause météo.
- `-Vue Opacite` ouvre directement le diagnostic3D : blanc opaque, noir transparent.
- `-Vue Densite` ouvre une coupe2D fixe du vrai champ, indépendante de la caméra.
- Coupe : ouest à gauche, est à droite, de−64 à+64 km ; altitude0 en bas,10 km en haut ; blanc pour densité≥0,25.
- Les diagnostics contournent exposition et courbe de tons ; le rendu éclairé les conserve.
- `-Build -NoLaunch -Vue Rendu`, `Densite` ou `Opacite` recompile seulement la variante choisie.
- `-Temoin` ouvre Courants C avec ses quatre assets réels figés ; sa météo diffère, ce n'est pas une comparaison à données identiques.

**Ce qui vient des sources :**

- Rapport : [Hillaire, Physically Based Sky, Atmosphere and Cloud Rendering in Frostbite, chapitre5](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/s2016-pbs-frostbite-sky-clouds-new.pdf), en particulier pages33–39.
- Générateur : [sebh/TileableVolumeNoise, révision1f879a26b89aaa4b5a7f112f14ec149d08057661](https://github.com/sebh/TileableVolumeNoise/tree/1f879a26b89aaa4b5a7f112f14ec149d08057661).
- Le code C++ original et ses paramètres sont inchangés ; MSVC19.44.35209, exécution4,68 s pour les TGA.
- `noiseShapePacked.tga` fournit la forme128³ ; `noiseErosionPacked.tga` fournit l'érosion32³.
- Conversion documentée des axes TGA, canaux RGB égaux et alpha255 ; mips par moyenne3D, sans modification de plage dynamique.
- Sources et licences : `third_party/FrostbiteNoise/`, `third_party/FrostbiteNoise/README-provenance.md` ; commande et empreintes : `assets/frostbite-reference/noise-manifest.json`.

**Ce qui est choisi pour ce test :**

- Le rapport ne fournit pas le shader de densité complet ni les réglages artistiques de ses images ; ce prototype n'est pas un port complet de Frostbite.
- Deux zones de météo dessinées : cumulus autour de0,5°/161,5°, nappe autour de0,5°/162,05°.
- Carte locale256×128 km, projetée sur une origine fixe0,5°/161,775° ; aucune répartition climatique ou NASA dans cette scène.
- Les traits de couverture sont explicites et déterministes ; il ne s'agit pas d'une distribution naturelle globale à juger.
- Profils de densité et d'érosion selon type/hauteur : `profiles-authored.json`, générés depuis les constantes de `tools/gen_frostbite_reference_scene.py`.
- La table2D de profils est stockée dans le conteneur3D64³ existant, identique sur Z, pour éviter une modification native ; lecture au mip0.
- Forme à période32 km, détail à4 km ; phases mondiales en double et reste local float, sans déformation ni bande additionnelle.
- Combinaison fixée : seuil du bruit par couverture, multiplication par profil de densité, puis érosion pondérée par le second canal du profil.
- Extinction neutre80/km et albédo1 ; quatre intervalles solaires progressifs0,125/0,25/0,5/1 km, échantillonnés au milieu.
- Intégration analytique par segment conservée ; phase et approximation de second ordre héritées du spike, distinctes du moteur Frostbite complet.

**Support et isolation :**

- Couche2–8 km ; profils nuls aux deux extrémités.
- Le support météo entre dans une sphère80 km autour de l'origine fixe ; elle limite le parcours sans dessiner les silhouettes.
- R météo mip1 moyen, mips2+ maximum conservateur ; sauts du vide mesurés dans le plan local avec marge du filtre.
- Même exécutable V4 figé et mêmes ressources b1/t24–27 ; seuls les shaders locaux et leurs données changent.
- Sorties indépendantes : `x64/NuageFrostbiteRefRendu/`, `NuageFrostbiteRefOpacite/`, `NuageFrostbiteRefDensite/`.
- Témoin validé figé : `x64/NuageFrostbiteReferenceTemoin/`, exécutable, shaders, quatre assets et palette copiés ; empreintes dans `witness.json`.
- En diagnostic, seule une copie isolée de ToneMap contourne l'exposition ; les anciens binaires et shaders restent intacts.

**Contrôle court :**

- Trois compilations DXC réussies, avertissement de shift préexistant dans Materials.hlsli.
- Cinq captures : deux familles éclairées, deux silhouettes d'opacité et une coupe de densité ; source et poses dans `x64/FrostbiteReferencePreview/`.
- La coupe confirme des profils distincts ; l'opacité permet de juger les contours sans l'éclairage.
- Cumulus : sommets bourgeonnants visibles ; nappe : profil nettement plus mince et encore très lisse.
- Bruits non constants, mips météo conservateurs, tranches de profils identiques et densité nulle aux limites vérifiés.
- Temps ponctuels nuages+air :6,52 ms cumulus et5,29 ms nappe dans les captures ; GPU partagé, aucune comparaison statistique ni extrapolation à la planète.
- Aucun banc complet ni historique temporel ; la validation du rendu et de la stabilité à l'approche vient des vérifications en vol de l'utilisateur.

**Suite retenue :**

- Compléter d'abord les familles locales avec les [cirrus](spike-nuages-cirrus.md), dans une sortie isolée.
- Conserver la recette du cumulus et de la nappe validés.
- Étudier ensuite la répartition de formations plus vastes, le filtrage lointain et l'extension planétaire.
- Cumulonimbus : piste intéressante retenue pour plus tard ; tours et enclumes à traiter après les familles locales courantes.
- Aucun commit, tag ni push demandé.

**Historique :** [recherche, variantes Wicked et Courants C](spike-nuages-reference-historique.md).
