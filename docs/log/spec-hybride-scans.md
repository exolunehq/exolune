# Essai hybride : scans photo pour la matière de près

Statut : essai fait le 2026-10-22, tag `piste/essai-hybride-scans`. Recommandation retenue : les sols meubles passent aux scans, la roche reste procédurale. Intégré par la photo du sable, fusionnée le 2026-10-23, voir « L'intégration » en fin de fichier.

## Le constat

- **Le procédural plafonne au détail de près.** Notre meilleure roche est à ×2,3 d'un scan réel à la mesure de réalisme.
- **L'essai :** la voie C de `etat-de-l-art-details.md`. Des scans photo donnent la matière de près ; le procédural garde la structure et la répartition.
- **La règle « aucune image chargée » du concept est levée pour cet essai seulement.**

## Les scans

**Source :** Poly Haven, https://polyhaven.com. **Licence :** CC0, domaine public, sans attribution obligatoire.

| Scan | Auteurs | Largeur réelle | Rôle |
|---|---|---|---|
| `dark_rock_02` | Amal Kumar | 2,00 m | chargé : roche litée, `MATERIAL_ROCK` |
| `sandy_gravel_02` | Dario Barresi | 2,53 m | chargé : sable, `MATERIAL_SAND` |
| `cliff_side` | James Ray Cock, Dario Barresi, Jenelle van Heerden | 1,83 m | témoin pour la roche |
| `gray_rocks` | Dimitrios Savva | 1,80 m | témoin pour la roche |
| `aerial_sand` | Rob Tuytel | 15 m | témoin pour le sable |

- **Fichiers :** couleur en JPEG 2k, hauteur en PNG 16 bits 2k. Hors du dépôt, dans `MyPlanetEngine\scans\`.
- **Les témoins n'ont pas servi au rendu :** la mesure contre eux n'est pas circulaire.
- **`dark_rock_02` plutôt que `cliff_side` :** sa couleur varie surtout en clarté. `cliff_side` porte des veines rouges et des blocs pâles que `RockColor` recolorerait mal hors du grès.

## Le chargement

- **Au démarrage, par WIC,** intégré à Windows : aucune dépendance nouvelle. `LoadScans` dans `D3DApp.cpp`.
- **Le dossier :** `MYPLANETENGINE_SCANS`, sinon le premier dossier `scans` au-dessus de l'exécutable.
- **Dans les mêmes tableaux que le générateur,** `materialColor` et `materialSurface`. Le générateur écrit toutes les tranches, puis les scans remplacent les leurs, mip par mip, par copie.
- **Un scan absent** laisse la tuile générée, à la mauvaise échelle. Le titre affiche alors « scans absents ».
- **1024 px avec les mips :** le 2k est réduit par moyennes de 2 × 2, puis chaque mip moyenne la précédente, comme le générateur.
- **Retourné verticalement :** le haut de la photo va vers le y de la tuile, qui monte le long des parois.

**L'échelle :**

- **Roche :** tuile de 2 m, l'échelle réelle exacte.
- **Sable :** tuile de 64/24 = 2,67 m, qui divise 64 m. Le scan est agrandi de 5 %, hauteurs comprises.
- **Les tuiles générées gardent leur taille :** granite à 8 m, éboulis à 4 m, structures à 64 m. D'où `MASSIVE_TILE`, séparée de `ROCK_TILE`.

**La couleur :**

- **Un facteur autour de 1,** la moyenne retirée, comme les tuiles générées : couleur linéaire divisée par sa moyenne.
- **Stocké divisé par 4,** pour tenir les facteurs jusqu'à 4. Le pixel divise déjà par la moyenne de la tuile, le mip 1 × 1.
- **Pas d'occlusion :** la photo porte déjà la sienne.
- **La saturation du scan est gardée,** `kScanSaturation` = 1. Ses écarts de teinte sont faibles : écart type 0,06 pour la roche, 0,10 pour le sable, contre 0,26 et 0,28 en clarté. `RockColor` donne la teinte de la région.

**Le relief :**

- **La pente :** différences centrées sur le tore, en mètres par mètre, sur la tuile mise à l'échelle.
- **La hauteur,** en mètres, sur la `HEIGHT_RANGE` inchangée de la tranche : ±30 cm pour la roche, ±3 cm pour le sable.
- **Poly Haven ne publie pas l'échelle de hauteur.** Le MaterialX donne 0,01 pour tous ses scans : une valeur par défaut. `metresPerUnit` est donc la nôtre :
  - roche, 0,15 m par unité : 12 cm de relief sur 2 m. Ses pentes ont alors un écart type de 0,65, celui que la règle universelle suppose pour la roche, `STONE_SLOPE_SIGMA` = 0,6 ;
  - sable, 0,05 m par unité : 3 cm sur 2,5 m, pente type 0,26.

**Le passe-haut, pour le sable :**

- **Le défaut :** dès 10 m, le sable montrait un camouflage régulier. Les taches de 1 m du scan se répètent d'une copie de la tuile à l'autre.
- **Le correctif :** les longueurs d'onde de plus de 50 cm sont retirées de la couleur et de la hauteur du scan. Trois flous en boîte sur le tore, proches d'une gaussienne.
- **La roche n'en a pas :** ses plaques de 1 à 2 m font son caractère, et ne se répètent pas visiblement.

## Ce que le procédural garde

- **Où va quel matériau :** les décisions ne changent pas, `docs/spec-rendu-lointain.md`. Seules leurs entrées de texture changent, hauteurs et pentes du scan.
- **La structure de 64 m,** `MATERIAL_MACRO`, la colonne stratigraphique, le pendage et les replats.
- **La teinte par région,** `RockColor` : le scan n'est qu'un facteur.
- **Les rides du sable,** dessinées au pixel.
- **Le granite et les autres familles,** générés.

**Le grain fin procédural reste sur les scans :**

- **Le scan est moins net que la tuile fine.** Un 2k ramené à 1024 texels donne 2 à 2,6 mm par texel. La tuile fine générée en a 1 mm.
- **Sans elle,** la roche paraît lisse et plastique à moins de 2 m, et la mesure le voit : `dark_rock_02` rendu ne fait que ×5,7 contre lui-même.
- **Avec elle,** ×1,7. Le scan porte donc les échelles de 3 cm à sa tuile, 50 cm pour le sable. Le procédural porte le plus fin et le plus grand.

## La mesure

**Les variantes, mêmes réglages, même génération de build :**

- **avant :** `b63d0ad`, procédural ;
- **hybride brut :** scans sans passe-haut ni tuile fine, écarté pour le camouflage du sable ;
- **hybride sans grain fin :** passe-haut du sable, sans tuile fine ;
- **hybride retenu :** passe-haut du sable et tuile fine, l'état de la branche.

**Réalisme, `tools/realisme.py`, vue verticale à 1,5 m,** motifs puis spectre. Le site `litee` est ajouté à `banc_visuel.py` : le site `roche` montre une autre famille de roche, que l'essai ne touche pas : ses notes ne bougent pas.

| Témoin | Site | Avant | Sans grain fin | Retenu | Plancher du spectre |
|---|---|---|---|---|---|
| `cliff_side` | litee | ×2,77 ; 1,6 dB | ×2,58 ; 1,3 dB | ×2,94 ; 1,3 dB | 1,3 dB |
| `gray_rocks` | litee | ×2,90 ; 3,0 dB | ×3,65 ; 3,0 dB | ×3,49 ; 2,4 dB | 2,1 dB |
| `aerial_sand` | desert, 4,6 m | ×7,63 ; 8,8 dB | ×6,04 ; 5,0 dB | ×6,55 ; 5,2 dB | 1,0 dB |
| `dark_rock_02`, chargé | litee | ×1,92 ; 2,4 dB | ×5,71 ; 1,5 dB | ×1,73 ; 1,0 dB | 1,2 dB |
| `sandy_gravel_02`, chargé | desert | ×3,83 ; 10,4 dB | ×7,54 ; 3,7 dB | ×5,79 ; 4,0 dB | 1,5 dB |

- **Le spectre gagne partout :** le scan donne la bonne répartition d'énergie de 3 cm à 1 m. Sable 8,8 → 5,2 dB contre `aerial_sand`. La roche atteint le plancher du scan contre lui-même.
- **Les motifs ne départagent pas la roche :** ×2,77 → ×2,94 contre `cliff_side`, ×2,90 → ×3,49 contre `gray_rocks`. La note se joue au pixel, sur le grain, où le scan 2k est trop flou.
- **Le sable gagne contre son témoin,** ×7,63 → ×6,55. Contre `sandy_gravel_02` lui-même, il perd : nos rides de 12,5 cm s'ajoutent au sol caillouteux, et le scan rendu est plus flou que l'original.

**Banc visuel,** `tools/banc_hybride.py` : les trois vues proches, puis sable et roche litée à 2, 10 et 50 m. Planches : `docs/images/hybride-avant-apres.jpg`, `hybride-detail.jpg` et `hybride-repetition.jpg`.

- **Sable à 2 m :** des graviers, des cailloux épars, un sol de désert crédible. Le procédural montrait un sable uniforme.
- **Roche à 2 m :** un réseau de fissures et de plaques réel, au lieu des fissures générées. Les grandes taches de couleur, les bancs et les corniches restent ceux du procédural.
- **À 10 m :** des fissures plus fines ; le reste est identique.
- **À 50 m et au-delà,** et sur les vues constat, corniche et roche rouge : rien ne change. La tuile s'efface quand un pixel couvre 2 à 4 m.

**La répétition,** à 2, 10 et 50 m :

- **Roche :** aucun motif répété visible.
- **Sable brut :** un camouflage régulier dès 10 m, les taches de 1 m du scan. **Après le passe-haut :** plus rien, `hybride-repetition.jpg`.

**Tremblement, `tools/banc_tremblement.py`,** avec et sans lissage temporel :

| Vue | Avant | Sans grain fin | Retenu |
|---|---|---|---|
| Roche litée à 3 m, `588.1 -25.21899 135.73187 30 92` | 0,66 / 3,78 | 0,68 / 3,89 | 0,67 / 4,21 |
| Sable à 1,5 m, `122.8 26.0 45.0 8`, soleil `20 110` | 0,01 / 0,07 | 0,01 / 0,11 | 0,01 / 0,11 |

- **Inchangé avec le lissage.** Sans lui, un peu plus de scintillement : le scan a plus de détail fin que la tuile générée.

**Coût de rendu,** même génération de build, Debug, cinq captures par build en alternance, minimum puis médiane du temps de rendu GPU :

| Vue | Avant | Sans grain fin | Retenu |
|---|---|---|---|
| Sable à 1,5 m | 3,25 ; 3,41 ms | 3,31 ; 3,38 ms | 3,25 ; 3,56 ms |
| Roche litée à 2 m | 5,11 ; 5,39 ms | 4,42 ; 4,55 ms | 5,16 ; 5,45 ms |
| Constat | 5,27 ; 5,37 ms | 5,03 ; 5,19 ms | 5,23 ; 5,35 ms |
| Corniche | 4,92 ; 5,02 ms | 4,96 ; 5,04 ms | 4,94 ; 5,18 ms |

- **Le rendu ne coûte rien de plus :** mêmes lectures de texture, à ±0,05 ms près. Sans la tuile fine, la roche gagnerait 0,7 ms.
- **Le démarrage :** +1,8 s en Debug, 7,9 s au lieu de 6,1 s pour une capture complète. Décodage WIC et calcul des mips sur le CPU.
- **Les temps affichés sur les planches** ne servent pas : d'autres rendus tournaient en même temps.

## La recommandation : mélanger selon l'échelle, et selon le matériau

- **Les sols meubles, sable, gravier, terre : passer à l'hybride,** sur la bande de 3 cm à 50 cm. C'est là que le procédural est le plus pauvre, et que le scan gagne à l'œil et à la mesure : un sol de désert crédible à 2 m, spectre 8,8 → 5,2 dB.
- **La roche : garder le procédural.** Le scan n'y gagne qu'une fissuration plus fine à moins de 10 m, et la mesure ne le départage pas. La forme d'une paroi vient de la structure de 64 m, de la colonne stratigraphique et des replats : tout cela reste procédural.
- **Toujours procédural :** sous 3 cm, le grain fin, plus net qu'un scan 2k ; au-dessus de 50 cm, la structure, la répartition et la teinte. Le passe-haut coupe le scan à cette limite, sinon il se répète en camouflage.
- **Le prix :** la règle « aucune image chargée » tombe, pour 8 à 11 Mo de scans 2k par matériau sur disque. La mémoire graphique ne change pas. Et l'échelle de hauteur des scans est à deviner : Poly Haven ne la publie pas.

**Si l'hybride est retenu pour les sols :**

- un scan par sol, choisi par nos masques, comme le prévoit la voie C ;
- des scans en 4k sur des tranches de 2048 texels, pour descendre sous 2 mm par texel ;
- la mesure de réalisme sur une vue rasante aussi, où le grain compte moins que la forme.

**Non fait :** `cliff_side` comme roche chargée, et une saturation partagée. Avec `dark_rock_02`, la question ne s'est pas posée. `cliff_side` en aurait besoin : 0,21 de teinte, et des facteurs jusqu'à 5, au-delà des 4 que tient le stockage.

## L'intégration : les sols photo

Statut : fait le 2026-10-22, à partir de `f385126` ; fusionné le 2026-10-23, commit `7bf38a9`.

**Ce qui est reporté de l'essai :**

- **Le chargement WIC,** `LoadScans` dans `D3DApp.cpp`, inchangé.
- **Le scan `sandy_gravel_02` dans la tranche du sable,** tuile de 64/24 m, 0,05 m de hauteur par unité.
- **Le passe-haut à 50 cm,** devenu une règle pour tout scan, `kScanKeep` : un scan ne porte que les longueurs d'onde de moins de 50 cm.
- **Le grain fin procédural reste** sur le scan.
- **La roche reste procédurale :** `dark_rock_02` n'est pas reporté, `ROCK_TILE` reste à 8 m.

**La recoloration par le biome :**

- **Le sable reste un facteur autour de 1,** qui multiplie la couleur du biome, `BiomeColor` dans `PixelShader.hlsl`.
- **Les moyennes sont prises après le passe-haut :** le facteur stocké a une moyenne de 1 sur chaque canal. Vérifié sur une copie Python du chargement, coupure et arrondi 8 bits compris : 1,0000 ; 1,0000 ; 1,0000, et 0,001 % de texels coupés.
- **Le pixel divise en plus par le mip 1 × 1 de la tuile.** La teinte moyenne vient donc du biome, jamais du scan. Le scan ne garde que ses écarts locaux, surtout en clarté : écart type 0,28, contre 0,10 en teinte.

**Les éboulis, essayés puis écartés :**

- **Le seul scan en main** pour une autre tranche est `gray_rocks`, des pierres en tas. Pas de scan de terre ni de sol herbeux dans `../scans/`, et aucun téléchargement.
- **Essayé sur la tranche des éboulis,** tuile de 2 m : plus naturel à 10 m, un vrai tas de pierres.
- **Écarté :** vu de la corniche, il devient un tapis uniforme de petites pierres. Les pierres générées de 25 cm, éparses sur la poussière, se lisent mieux de loin. Et ce n'est pas un sol meuble au sens de la recommandation.
- **Pour l'essayer :** une ligne dans `kScans`, et `SCREE_TILE` à 2 m. Planche : `docs/images/sols-photo-eboulis.jpg`.

**La mesure, `f385126` contre `sols-photo`, mêmes builds Debug :**

- **Descente, `tools/banc_descente.py`, de 800 à 8 km,** sur 8 km de côté :
  - sable, désert à 26° N 45° E : 100 % à toutes les hauteurs, dans les deux builds ;
  - herbe, à 15° S 50° E : 100 % à toutes les hauteurs, dans les deux builds ;
  - sable en marge de désert, à 30,16° N 54,68° E, où il n'occupe qu'une part du carré : 0,0 ; 0,0 ; 0,2 ; 0,6 ; 1,4 ; 2,6 ; 3,4 %, de 800 à 8 km, identique dans les deux builds.
  - **Inchangé partout,** à la décimale près : de 8 km et plus haut, la tuile du scan est effacée.
  - **La courbe de la marge n'est pas plate,** de 0 à 3,4 %, déjà dans `f385126`. À examiner à part : le carré ne fait que 6 pixels à 800 km.
- **Réalisme contre `aerial_sand` :** motifs ×7,66 → ×6,54 ; spectre 8,8 → 5,2 dB, plancher 1,0 dB.
- **Tremblement,** avec et sans lissage :
  - sable à 1,5 m, `122.8 26.0 45.0 8`, soleil `20 110` : 0,01 / 0,07 → 0,01 / 0,11 ;
  - corniche, `2182.0 31.16045 8.58814 1.9 -17.1` : 0,17 / 1,11 → 0,18 / 1,12.
- **Coût de rendu,** cinq captures par build en alternance, minimum puis médiane :

| Vue | `f385126` | `sols-photo` |
|---|---|---|
| Sable à 1,5 m | 4,03 ; 4,24 ms | 4,02 ; 4,08 ms |
| Roche litée à 2 m | 5,83 ; 6,19 ms | 5,71 ; 6,10 ms |
| Constat | 5,32 ; 5,40 ms | 5,38 ; 5,43 ms |
| Corniche | 4,62 ; 4,71 ms | 4,56 ; 4,65 ms |

- **Aucun surcoût mesurable :** les écarts restent sous 0,1 ms, dans le bruit. Le démarrage prend 1,1 s de plus en Debug, 6,1 s au lieu de 5,0 s pour une capture complète.
- **Planches :** `docs/images/sols-photo-avant-apres.jpg`.
