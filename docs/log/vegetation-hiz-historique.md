# Historique de l'occlusion hiérarchique de la végétation

**Les sections de `../vegetation-hiz.md` sorties le 2026-10-30,** quand ses témoins ont quitté le moteur, commit `3a4508a`. Ils restent au tag `jalon/25-vegetation-performance-main`. L'état présent est dans `../vegetation-hiz.md`.

**Les témoins retirés :**
- `MYPLANETENGINE_FOLIAGE_HIZ=0` coupait le HiZ.
- `MYPLANETENGINE_FOLIAGE_MESH_HARDWARE`, absent par défaut, gardait la profondeur historique des maillages : le shader original recalculait `SV_DEPTH`. Le choix se faisait par PSO.
- `MYPLANETENGINE_FOLIAGE_HIZ_INTERLEAVE` et `MYPLANETENGINE_FOLIAGE_MESH_INTERLEAVE` alternaient ces états en batch.
- Les volumes et les imposteurs à alpha stochastique, des représentations retirées le même jour, gardaient leur dessin intégral faute de borne de profondeur.
- Leurs outils : `tools/lance_vegetation_hiz.ps1`, et les options `--hiz off|interleave`, `--mesh-depth legacy` et `--matrix` de `tools/banc_arbustes_climat.py`.

**La mesure, 2026-10-27 :**
- `tools/banc_arbustes_climat.py --hiz off` et `--hiz on` utilisent le même exécutable, les mêmes modèles, poses, soleils et le temps de mer figé.

**La comparaison intercalée :**
- Un mode batch alterne les quatre états : profondeur historique ou matérielle, HiZ désactivé ou activé.
- La caméra, les modèles et les données résident dans le même processus ; chaque cycle donne une comparaison rapprochée, moins sensible aux autres rendus.
- Six vues, 32 images de chauffe, 256 mesures par vue, soit 64 cycles complets.
- Le mode intercalé est réservé au batch ; il n'est pas utilisé en vol.
- Dans la forêt tempérée intérieure, le rendu végétal passe de 10,30 à 4,64 ms et l'image GPU de 27,61 à 21,84 ms.
- Dans la forêt tropicale, il passe de 8,21 à 3,46 ms et l'image GPU de 28,64 à 24,06 ms.
- En forêt boréale, il passe de 5,95 à 4,27 ms et l'image GPU de 23,69 à 21,54 ms.
- Le désert paie un surcoût : dessin de 0,38 à 0,54 ms, image GPU de 14,41 à 14,47 ms.
- Ces temps GPU ne sont pas une garantie de FPS ; le terrain, le placement et le coût CPU restent présents.

**Le vol :**
- `tools/lance_vegetation_hiz.ps1` ouvre la version retenue ; `-Reference` désactive HiZ et retrouve la profondeur historique.
- `-LegacyDepth` isole le HiZ en gardant la profondeur historique des maillages.
- Même exécutable, même palette `2026-10-27-vegetation-hiz.txt`, mêmes modèles, densité et portée ; un seul vol à la fois.
