# Recherche : les rayons de soleil, l'air à l'ombre du relief

Statut : recherche et étape 1 faites le 2026-10-24, tag `piste/rayons-soleil`. Étape 2, le 2026-10-25 : une seule marche avec les ombres portées, tag `piste/ombre-unique` ; la grille polaire de l'étape 1 est dans `log/recherche-rayons-historique.md`. Suite de `recherche-profondeur-atmospherique.md`, indice 3.7. Sources en fin de fichier.

**Dans le jeu :** l'air passe par la composition des nuages (`spec-nuages.md`, `CloudAirPiece`), qui lit la même hauteur d'ombre. Les rayons y sont rendus le 2026-10-30, à juger en vol (`tools/tests/2026-10-30-lumiere.txt`) ; jusque-là, cette composition les omettait.

## 1. Conclusion

**Un rayon de soleil, c'est de l'air que le relief prive de soleil.**
- L'air à l'ombre ne renvoie plus que la lumière du ciel. L'air voisin, au soleil, renvoie aussi celle du soleil.
- Le contraste entre les deux dessine les rayons. Ils divergent depuis le soleil par la seule perspective.
- Il suffit donc que le calcul de l'atmosphère sache quels points de l'air voient le soleil. Aucun effet ajouté par-dessus.

**Retenu : la hauteur d'ombre, un seul champ, lu par les pas existants du rayon de vue.**
- Une colonne d'air voit le soleil au-dessus d'une altitude, la hauteur d'ombre. En dessous, le relief cache le soleil.
- Ce champ en deux dimensions décrit tout le volume d'ombre d'un relief en hauteur. Il donne aussi l'ombre du sol : un point du sol sous la hauteur d'ombre est à l'ombre.
- Comme la carte d'ombre du terrain de Red Dead Redemption 2, elle se marche vers le soleil sur les hauteurs. Ici, c'est la marche des ombres portées, à chaque sommet du maillage : une seule marche, une seule ombre, pour le sol et pour l'air (`recherche-ombres-relief.md`).
- Chaque pas du rayon de vue garde la part de sa longueur au-dessus de la hauteur d'ombre : il montre la moyenne de sa lumière.
- Rien ne vient de l'écran : le maillage garde toute colonne d'air visible et tout relief dont l'ombre l'atteint. Le soleil hors champ, dans le dos ou de côté ne change rien.

**Écartés :**
- **les rayons d'écran de Mitchell :** un flou radial vers le soleil, sur l'image. Rien hors champ ni dos au soleil, des sauts quand un relief sort de l'image. Une couche par-dessus l'image, pas de la physique.
- **les froxels de Frostbite et d'Unreal :** quelques dizaines à 160 m de profondeur, pour les lumières proches. Ils ne voient pas l'ombre d'une montagne à 20 km, et ne tiennent que par la gigue et le lissage temporel, avec des traînées.
- **la longueur d'ombre de Bruneton :** une seule longueur par pixel, placée au début ou à la fin du rayon. Faux dès que le rayon traverse plusieurs ombres, ce qui fait justement les rayons.
- **l'échantillonnage épipolaire :** une accélération du marchage le long des rayons de vue, pas une source d'ombre. À reprendre si le coût de l'atmosphère l'exige.

**Coût :** presque rien de plus que les ombres portées. La grille de l'étape 1 coûtait 0,8 à 1,1 ms par image en 1280 × 720 sur RTX 4070 Ti ; la marche commune en rend 0,7 à 1,3 ms. Stabilité : le tremblement ne monte pas. Détail en partie 4.

## 2. Quand voit-on des rayons

**Les conditions (Lynch 1987, glossaire de l'AMS) :**
- **un soleil bas :** les ombres sont longues, les rayons traversent beaucoup d'air ;
- **un soleil caché ou à demi caché :** derrière une crête ou un nuage, l'observateur dans l'ombre ou près de son bord ;
- **le regard vers le soleil :** le contraste est maximal à moins de 15° du soleil, et à moins de 15° du point antisolaire, les rayons anticrépusculaires ;
- **de la brume, sans excès :** les aérosols diffusent vers l'avant et rendent l'air au soleil brillant. Une brume trop dense éclaire aussi l'ombre, par la lumière du ciel, et le contraste baisse.

**Ce qui fait leur force :**
- la longueur du trajet du regard dans l'ombre compte d'abord, avant la phase des aérosols ;
- puis le rapport entre la lumière du soleil diffusée et celle du ciel. L'ombre n'est éclairée que par le ciel.

**Les montagnes :** au soleil bas, depuis un sommet, chaque pic jette dans la brume une ombre triangulaire (Livingston et Lynch 1979). Dans une vallée à contre-jour, l'air devant une crête à l'ombre est sombre, et des faisceaux passent par les cols.

**Chez nous :** la brume de la couche limite, 40 km de visibilité jusqu'à 2 km d'altitude, est le bon milieu. Une montagne qui dépasse la couche n'a plus d'air à assombrir au-dessus : ses rayons naissent dans les vallées.

## 3. Les techniques

| Technique | Entrée | Coût publié | Stabilité | Chez nous |
|---|---|---|---|---|
| Rayons d'écran, Mitchell 2007 | image d'occlusion | faible, non chiffré | sauts aux bords de l'écran, rien hors champ | écarté |
| Épipolaire, Engelhardt et Dachsbacher 2010 | carte d'ombre, profondeur | 28 ms en 1080p sur HD 4850, contre 71 ms en force brute | « stable et sans scintillement » selon les auteurs | une accélération, pour plus tard |
| Épipolaire et arbres min/max, Yusov 2013 | cartes d'ombre en cascade | non vérifié | raffinement sur la diffusion plutôt que la profondeur | idem |
| Froxels, Wronski 2014, Hillaire 2015, Unreal | cartes d'ombre en cascade | 1,1 à 3 ms sur PS4 | crénelage en mouvement, gigue et lissage temporel, traînées | portée trop courte |
| Longueur d'ombre, Bruneton 2008 et 2017 | volumes d'ombre | faible | stable | une seule ombre par rayon |
| Carte d'ombre du terrain, Bauer 2019 | carte des hauteurs | 1,31 ms sur PS4 pour le marchage | lissage temporel, découpage dans le temps | **retenu** |

### 3.1 Les rayons d'écran, Mitchell, GPU Gems 3

- **Principe :** chaque pixel prend des échantillons sur la droite qui le joint au soleil à l'écran, avec une décroissance. La somme s'ajoute à l'image.
- **Entrée :** une image d'occlusion, le relief en noir, le ciel clair. Seuls les obstacles visibles comptent.
- **Limites, selon l'auteur :** des rayons du fond passent devant les objets proches ; ils scintillent quand un obstacle passe le bord de l'écran ; face au soleil de côté, sa position à l'écran part à l'infini, il faut estomper l'effet. Le soleil dans le dos n'est pas traité.

### 3.2 L'échantillonnage épipolaire, Engelhardt et Dachsbacher 2010

- **Principe :** les rayons de lumière se projettent à l'écran sur des droites issues du soleil. On n'échantillonne que le long de 256 à 1 024 de ces droites, 8 à 32 points chacune, plus deux points à chaque saut de profondeur.
- **Le marchage :** chaque point marche dans la carte d'ombre le long du rayon de vue. Une interpolation bilatérale remplit l'écran.
- **Coût :** 1,2 ms pour les droites, 6,0 ms pour les sauts, 16,7 ms pour le marchage, 4,4 ms pour l'interpolation, sur HD 4850 en 1080p : 36 images par seconde contre 14 en force brute.
- **Yusov, Intel 2013 :** l'atmosphère d'une planète, des cartes d'ombre en cascade, et des arbres min/max à une dimension. Dans la carte d'ombre redressée, chaque droite épipolaire devient un relief à une dimension.

### 3.3 Les froxels, Frostbite et Unreal

- **Principe :** une grille alignée sur l'écran, 8 × 8 pixels et 64 tranches en profondeur chez Frostbite, 160 × 90 × 64 chez Wronski. Chaque cellule prend la carte d'ombre du soleil.
- **Stabilité :** un échantillon par cellule crénèle en mouvement, « les ombres l'aggravent » (Hillaire). Corrigé par une gigue de Halton, une reprojection et 5 % de l'image nouvelle. Unreal annonce un lissage temporel fort, avec des traînées derrière les lumières rapides.
- **Coût :** 2,95 ms sur PS4 en 900p chez Frostbite, dont 0,5 ms pour le soleil ; environ 1,1 ms chez Wronski ; environ 1 ms sur PS4 chez Unreal.
- **Portée :** 50 à 128 m chez Wronski, 160 m dans Red Dead Redemption 2. Au-delà, autre chose.

### 3.4 La longueur d'ombre, Bruneton

- **2008 :** des volumes d'ombre donnent, par pixel, la longueur totale du regard dans l'ombre. La diffusion de cette longueur est retirée.
- **2017 :** la démo calcule cette longueur pour l'ombre d'une sphère, analytiquement. Le ciel la retire au début du rayon, la diffusion vers un point la retire à la fin. Une ombre en un seul morceau, à un bout.
- **Un artifice :** les rayons s'estompent quand le soleil approche de l'horizon, `lightshaft_fadein_hack`.

### 3.5 La carte d'ombre du terrain, Red Dead Redemption 2

- **Principe :** un marchage sur la carte des hauteurs, vers le soleil, dans une texture de 128 × 128. Elle garde la hauteur de l'intersection et la longueur du rayon, qui adoucit l'ombre.
- **L'air :** près de la caméra, les froxels lisent cette carte avec les cascades et l'ombre des nuages. Au loin, un marchage en demi-résolution, refait sur 4 images. Le ciel est modulé par la visibilité moyenne, « pas physiquement correct, mais plausible ».
- **Coût :** 1,31 ms pour le marchage de l'air sur PS4.

## 4. Ce qui est fait : la hauteur d'ombre, par sommet

**Une seule marche (`SunHorizon`, `Shadows.hlsli`, passe `Horizon.hlsl`).** Celle des ombres portées (`recherche-ombres-relief.md`, partie 4).
- À chaque sommet visible, le long du grand cercle vers le soleil, sur les hauteurs du maillage, à pas de 2 % de la distance parcourue, jamais sous la maille.
- Chaque point marché donne l'horizon, pour le sol, et sa hauteur au-dessus du rayon du soleil tiré du sommet, pour l'air : q · (u − sin θ s) / cos² θ, pour un point q vu du sommet, u la verticale, s le soleil à la hauteur θ. Exacte : les points marchés sont à leur vraie place, courbure comprise.
- La plus grande, ajoutée au sol du sommet, est la hauteur d'ombre de la colonne. Sol et air voient le même relief : un sommet est à l'ombre si et seulement si sa hauteur d'ombre dépasse son sol.
- La marche s'arrête quand rien au-delà, même un sommet de 10 km, ne peut dépasser l'horizon trouvé et le bas du disque, ni passer au-dessus du rayon du soleil tiré de la hauteur d'ombre. Un sommet au soleil marche comme avant ; un sommet à l'ombre, au plus aussi loin.

**Ce que le maillage couvre.**
- **Toute colonne d'air visible :** le maillage garde un sommet si sa colonne, de la mer à `MAX_TERRAIN_HEIGHT`, peut être vue (`MaybeVisible`). L'air que la caméra voit sous le plus haut sommet est donc au-dessus de sommets calculés, même quand leur sol est hors de l'image.
- **Tout relief qui lui fait de l'ombre :** le maillage garde aussi un sommet si sa colonne, balayée à l'opposé du soleil, peut tomber dans l'image (`ShadowSweep`). Le balayage couvre la colonne entière, pas seulement le sol : l'ombre d'un relief hors champ sur l'air du champ est marchée.
- **Au-delà des anneaux,** l'horizon passé, pas de relief : la grille s'arrêtait à la même portée.

**La lecture (`Atmosphere.hlsli`, `IntegrateScattering`).**
- La hauteur d'ombre, bilinéaire entre les quatre sommets autour du point, comme la hauteur du maillage (`MeshCell`, `Mesh.hlsli`).
- Le rayon de vue garde ses 12 pas vers le terrain ; vers le ciel, 24 dans le jeu, où le nuage coupe en deux le pas où il tombe (`spec-nuages.md`). Chaque pas lit la hauteur d'ombre à ses deux bouts et en son milieu.
- La part éclairée de chaque moitié est exacte pour une marge linéaire entre ses bouts : le bord d'un rayon glisse dans le pas, il ne saute pas d'un pas à l'autre.
- Seule la lumière du soleil diffusée une fois est coupée. La diffusion multiple, la lumière du ciel, reste : l'ombre n'est éclairée que par le ciel.
- Les tables du démarrage n'ont pas de relief : `(ShadowRay)0`.

**Ce que l'on voit,** planche de `tools/banc_tests.py` sur `tools/tests/2026-10-24-rayons.txt`, `images/rayons-avant-apres.jpg` :
- **contre-jour, soleil derrière le pic :** la lueur qui baignait l'air devant le pic disparaît, la caméra est dans son ombre ;
- **soleil juste au-dessus des crêtes :** des faisceaux clairs entre les ombres des crêtes, et le coin d'ombre de chaque aiguille sur la brume ;
- **soleil de côté ou dans le dos, désert, orbite :** peu ou pas de changement.

**Mesures de l'étape 2, contre la grille polaire** (`journal-planete.md`, 2026-10-25 ; `images/ombre-unique-avant-apres.jpg`) :
- **Images presque identiques :** écart moyen de 0,00 à 0,88 niveau sur 255 sur les onze vues des rayons, de 0,03 à 0,74 sur les huit des ombres portées.
- **L'air un peu plus sombre au ras des crêtes,** quelques niveaux sur quelques pixels. Une grille polaire de 1 024 × 1 024 s'écarte deux fois moins de la nouvelle ombre que de l'ancienne : la grille de 512 abaissait les crêtes.
- **Tremblement jamais au-dessus d'avant,** sur trois vues de rayons et deux d'ombres portées.
- **Coût,** RTX 4070 Ti partagée, paires de captures successives : le calcul perd 0,7 à 1,3 ms sur les quatre vues mesurées au calme, le rendu ne bouge pas à 0,1 ms près. Le soleil dans le dos, pire cas de la marche, n'a été mesuré qu'avec quatre autres instances du moteur sur le GPU : −0,4 à −1,2 ms en médiane, à confirmer au calme.
- **Le pas compte :** à 5 %, le sol gardait ses ombres, mais l'air tremblait plus qu'avant au pic à 14°, 0,10 / 0,66 → 0,12 / 0,69. À 2 %, 0,10 / 0,66.

## 5. La suite

- **La pénombre :** le soleil fait 0,53°. Une ombre à 10 km de son relief a 93 m de pénombre. Ici, le bord ne s'adoucit que par la maille et la marge linéaire.
- **Les pas du ciel :** 24 pas sur tout le rayon, plus de 30 km chacun à l'horizon. L'ombre près de la caméra y est grossière. Des pas plus serrés près de la caméra si une vue le montre.
- **L'ombre des nuages dans l'air,** absente : seule leur ombre au sol est faite (`spec-nuages.md`). C'est aussi une hauteur d'ombre, par-dessous.

## Sources

- K. Mitchell, « Volumetric Light Scattering as a Post-Process », GPU Gems 3, ch. 13, 2007. https://developer.nvidia.com/gpugems/gpugems3/part-ii-light-and-shadows/chapter-13-volumetric-light-scattering-post-process
- T. Engelhardt, C. Dachsbacher, « Epipolar Sampling for Shadows and Crepuscular Rays in Participating Media with Single Scattering », I3D 2010. https://faculty.digipen.edu/~gherron/references/References/LightEffects/VolumetricLighting/espmss10.pdf
- E. Yusov, « Practical Implementation of Light Scattering Effects Using Epipolar Sampling and 1D Min/Max Binary Trees », GDC 2013 ; GPU Pro 5. https://github.com/GameTechDev/OutdoorLightScattering
- S. Hillaire, « Physically Based and Unified Volumetric Rendering in Frostbite », SIGGRAPH 2015. https://advances.realtimerendering.com/s2015/Frostbite%20PB%20and%20unified%20volumetrics.pptx
- B. Wronski, « Volumetric Fog », SIGGRAPH 2014. https://bartwronski.com/wp-content/uploads/2014/08/bwronski_volumetric_fog_siggraph2014.pdf
- Epic Games, « Volumetric Fog in Unreal Engine ». https://dev.epicgames.com/documentation/en-us/unreal-engine/volumetric-fog-in-unreal-engine
- E. Bruneton, F. Neyret, « Precomputed Atmospheric Scattering », EGSR 2008. https://inria.hal.science/inria-00288758
- E. Bruneton, « Precomputed Atmospheric Scattering: a New Implementation », 2017. https://ebruneton.github.io/precomputed_atmospheric_scattering/
- F. Bauer, « Creating the Atmospheric World of Red Dead Redemption 2 », SIGGRAPH 2019. https://advances.realtimerendering.com/s2019/slides_public_release.pptx
- D. K. Lynch, « Optics of sunbeams », JOSA A 4, 609, 1987. https://thulescientific.com/Lynch_Sunbeams.PDF
- W. Livingston, D. Lynch, « Mountain shadow phenomena », Applied Optics 18, 265, 1979. https://authors.library.caltech.edu/records/nk414-7an79
- American Meteorological Society, glossaire : « Crepuscular rays », « Anticrepuscular rays ». https://glossary.ametsoc.org/wiki/Crepuscular_rays
