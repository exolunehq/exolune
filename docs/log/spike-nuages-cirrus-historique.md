# Cirrus : premiers essais locaux

**Retour utilisateur, 27 octobre 2026 :** rendu inférieur au cumulus et à la nappe validés. Fibres trop larges, bords communs trop nets : les captures à33 km montrent une enveloppe qui coupe les ondulations. L’utilisateur demande de réunir les trois familles et de conserver une atténuation en traînées.

**Notice de livraison du premier essai, conservée pour mémoire :**

# Cirrus locaux

**État, 27 octobre 2026 :** premier essai prêt pour le vol. Rendu, opacité et coupe compilés ; quatre captures initiales puis deux captures après correction inspectées. Le rendu et la stabilité à l'approche du cumulus et de la nappe de référence sont validés en vol par l'utilisateur ; ceux des cirrus restent à juger.

**Lancer :**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-frostbite-cirrus.ps1
```

- F1 : dessous ; F2–F4 : ensemble, approche et traversée ; F5 : dessus ; F6–F7 : distance ; F8 : soleil bas ; F9 : dessous depuis l'est.
- B : opacité ; C : qualité48/24 m ; Espace : pause météo, activée par défaut.
- `-Temoin` ouvre le cumulus et la nappe validés, avec leur palette et leurs quatre assets figés ; aucune reconstruction des données du témoin.
- `-Vue Opacite` : diagnostic3D ; `-Vue Densite` : coupe2D fixe Est/altitude0–16 km, densité normalisée par0,022.
- `-Build -NoLaunch -Vue Rendu`, `Opacite` ou `Densite` recompile la variante isolée choisie.

**Objectif :** ajouter des nuages hauts fibreux et peu opaques, à juger de dessous, de côté, en traversée et de dessus.

- Le champ reste fixé au monde à météo figée.
- Une enveloppe d'altitude continue éteint la densité avant les bornes de parcours.
- Les fibres ont leur propre champ3D ; elles ne viennent pas d'un profil de cumulus déplacé en altitude.
- La scène locale est dessinée pour comparer les formes ; elle ne représente pas encore une distribution météorologique planétaire.
- Les vérifications en vol appartiennent à l'utilisateur ; captures cachées courtes avant remise en main.

**Réglages explicites de cet essai :**

- Bruit128³ auteur : deux champs gaussiens filtrés par FFT, corrélations Est6/3,5 km, Nord0,75/0,40 km, vertical0,25/0,15 km ; poids0,55/0,45.
- Domaine fixe Est64/Nord32/vertical8 km ; fibres façonnées au mip0 avant les moyennes3D.
- Centre vers11 km, variation douce maximale±0,35 km ; épaisseur totale0,7–1,2 km, éteinte bien avant la coquille9–13 km.
- Cisaillement Nord±0,8 km, période16 km Est et8 km en altitude ; ancrage mondial et continu.
- Trois rubans météo à support compact ; emprise mesurée Est−28,625..25,625 km, Nord−12,875..12,875 km.
- Densité maximale0,022, extinction80/km et intégration héritées de la référence.
- Manifeste, empreintes et aperçus : `assets/frostbite-cirrus/scene-manifest.json` ; paramètres sources dans `tools/gen_frostbite_cirrus_scene.py`.
- Exécutable natif V4 identique ; sorties `x64/NuageFrostbiteCirrusRendu/`, `NuageFrostbiteCirrusOpacite/`, `NuageFrostbiteCirrusDensite/`.

**Contrôle court :**

- Trois variantes DXC compilées ; avertissement préexistant de décalage binaire dans `Materials.hlsli`.
- Quatre vues initiales : dessous, côté, dessus,80 km ; correction du voile trop lisse et du support rectangulaire, puis deux vues finales dessous/80 km.
- Captures et compte rendu : `x64/CirrusPreview/` ; premier jet dans `premier-jet/`.
- Temps ponctuels nuages+air après correction :4,22 ms dessous,2,25 ms à80 km ; GPU partagé, aucun verdict de performance générale.
- Le champ reste volontairement simple et lisse ; les captures ne valident ni le vol, ni la distribution planétaire, ni le rendu orbital.
- Témoin complet, sources et assets de référence vérifiés inchangés.

**Témoin :** `x64/NuageFrostbiteReferenceTemoin/`, copie figée de l'exécutable, des shaders, des quatre assets et de la palette validés ; empreintes dans `witness.json`.

**Mémoire pour la suite :** le 27 octobre 2026, l'utilisateur demande de conserver le cumulonimbus comme piste future. Prévoir des tours à forte extension verticale et des enclumes ; ce chantier vient après les formes locales courantes et ne fait pas partie du présent essai.

**Références :** [familles locales guidées par Frostbite](spike-nuages-reference.md) ; [cirrus, Atlas international des nuages](https://cloudatlas.wmo.int/fr/clouds-genera-cirrus.html).
