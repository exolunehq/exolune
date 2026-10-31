# Cumulus, nappe et cirrus locaux

**Au log depuis le 2026-10-30 :** spike clos. Les familles locales, cumulus, nappe et cirrus, sont reprises par les nuages du jeu, `../spec-nuages.md`. Lanceur et assets de l'essai : tag `piste/nuages-orbite-spike`.

**État, 27 octobre 2026 :** variante commune compilée et prête pour le vol, après le retour sur les contours des cirrus. Quatre captures cachées inspectées. Le rendu et la stabilité à l'approche du cumulus et de la nappe de référence restent validés par l'utilisateur ; le correctif des cirrus attend son jugement.

**Demande :** voir les trois familles dans la même scène ; affiner et allonger les cirrus, laisser leurs fibres se prolonger au-delà de l'enveloppe principale.

**Lancer :**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-familles.ps1
```

- Palette de douze vues : ensemble, cumulus, nappe, cirrus et distance.
- B : rendu éclairé/opacité ; C : qualité48/24 m.
- Espace : pause/reprise météo ; V : vitesse météo×1/×5.
- La météo démarre figée ; la molette règle la vitesse de la caméra.
- `-Temoin` ouvre le cumulus et la nappe validés, avec leurs données et leur palette figées.
- `-Vue Opacite` et `-Vue Densite` : diagnostics séparés ; la densité montre une coupe fixe du champ.
- `-Build -NoLaunch -Vue Rendu`, `Opacite` ou `Densite` recompile la variante choisie.

**Conservation des familles validées :**

- Forme128³ : canalR et chacun de ses mips copiés exactement depuis la référence ; canalG réservé aux fibres des cirrus.
- Détail32³ et table des profils64³ copiés intégralement.
- Météo locale : canauxR/G et leurs mips conservés exactement ; canalB réservé à la couverture des cirrus.
- La densité basse conserve la recette du cumulus et de la nappe, leurs positions et leurs profils.
- Coquilles2–8 km et9–13 km parcourues par segments triés le long du rayon ; le vide entre elles est sauté.
- L'atténuation des couches se cumule dans leur ordre de visibilité ; l'approximation atmosphérique héritée reste la même.
- Témoin figé : `x64/NuageFrostbiteReferenceTemoin/`, empreintes dans `witness.json`.

**Correction des cirrus :**

- Dans le premier essai, une enveloppe météo compacte et un seuil de couverture0,03 pouvaient couper les fibres encore visibles.
- La variante commune conserve les faibles couvertures des cirrus et dessine des queues de faible densité.
- Les fibres ont un champ3D distinct, fixé au monde ; domaine Est64/Nord16/vertical8 km.
- Corrélations Est8/6 km, Nord0,28/0,14 km, vertical0,20/0,12 km ; cisaillement Nord continu d'amplitude maximale0,5 km, fixé au monde.
- Leur façonnage précède les mips de densité ; le shader lit ensuite leur densité filtrée.
- Le profil haut reste centré vers11 km, avec épaisseur et hauteur variables ; aucune limite visible ne doit venir de la coquille9–13 km.
- Les choix de fibres et de plumes sont artistiques et locaux ; la scène n'est pas une météo planétaire.
- Source des données : `tools/gen_frostbite_cloud_families.py` ; paramètres et empreintes : `assets/frostbite-families/families-manifest.json`.
- Sorties isolées : `x64/NuageFrostbiteFamiliesRendu/`, `NuageFrostbiteFamiliesOpacite/`, `NuageFrostbiteFamiliesDensite/`.

**Vérification :**

- Trois variantes DXC compilées ; avertissement de décalage binaire préexistant dans `Materials.hlsli`.
- Quatre captures : ensemble des trois familles, cumulus, nappe et cirrus vus de dessous ; `x64/FamiliesPreview/`, compte rendu dans `report.json`.
- Données basses identiques sur tous les mips ; corps de fonction de densité basse identique après normalisation des noms des bornes.
- MipsB de preuve du vide vérifiés conservateurs ; témoin complet et sources de référence intacts.
- Les fibres restent fortement orientées ; leur naturel, la traversée et l'animation restent à juger en vol par l'utilisateur.
- Aucun banc prolongé, validation planétaire, commit, tag ou push.

**Mémoire pour la suite :** cumulonimbus retenu le27 octobre2026 pour une étape ultérieure, avec tours et enclumes. Ce chantier vient après les familles locales courantes.

**Extension régionale :** la [carte météo étendue](spike-nuages-region.md) conserve cette scène comme témoin figé dans `x64/NuageFrostbiteFamiliesTemoin/`.

**Références :** [familles locales guidées par Frostbite](spike-nuages-reference.md) ; [premiers essais de cirrus](spike-nuages-cirrus-historique.md) ; [cirrus, Atlas international des nuages](https://cloudatlas.wmo.int/fr/clouds-genera-cirrus.html).
