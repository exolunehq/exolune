# Spécification : normales par pixel reconstruites en spline

Statut : piste 1 de `log/pistes-glissement.md`, mesurée au banc le 2026-10-21, tag `jalon/09-normales-spline`. Gain modeste, gardé avec la B-spline lissante ; la coupure du relief fait l'essentiel. Le préfiltre de la spline cardinale, retiré le 2026-10-30, est dans `log/spec-normales-spline-historique.md`.

## Le but

**Un éclairage qui ne dépend plus de la position des sommets.** Les sommets du plan glissant sont exacts ; c'est la reconstruction entre eux qui tremble, surtout celle de la pente.

- **Aujourd'hui :** la normale est calculée sur les sommets voisins, puis interpolée linéairement sur le triangle. Une onde de 8 mailles fait encore varier la pente de 17 % quand le maillage glisse.
- **Avec la spline :** chaque pixel reconstruit la surface sur les 4 × 4 sommets voisins, avec une B-spline cubique lissante, et en tire sa normale. La spline cardinale du plan d'origine tremblait davantage (« Résultats du banc »).
- **Rien d'autre ne change :** ni le relief, ni le maillage, ni la géométrie dessinée. Seule la normale de l'éclairage est remplacée.

## Le principe

### Les deux cartes du maillage

**La spline travaille dans les coordonnées de la grille du maillage,** où les sommets sont espacés régulièrement.

- **La face :** coordonnées (i, j), de 0 à n, n = 192.
- **Les anneaux :** coordonnées (b, r). b est la position sur l'anneau, de 0 à 4n, et revient à 0 après un tour. r est le numéro d'anneau, à partir de 1.
- **La spline reconstruit la position 3D des sommets,** pas seulement leur hauteur. Le passage de la grille au plan est lisse dans chaque carte : linéaire dans la face, géométrique d'un anneau au suivant. La spline le reproduit sans erreur notable.

### Les sommets pour coefficients

**La B-spline lissante prend les positions des sommets pour coefficients,** sans préfiltre : elle ne passe pas par eux, et adoucit les ondes de 2 à 3 mailles, celles qui tremblent.

- **Aux bords d'une carte,** le voisin manquant est remplacé par le dernier sommet de la carte. Les anneaux commencent à r = 1 : le bord de la face n'est pas pris comme anneau 0, car ses voisins ne suivent pas la même grille.

### La normale du pixel

- **Chaque pixel reçoit ses coordonnées dans sa carte,** interpolées depuis ses sommets.
- **Il lit les 4 × 4 sommets voisins** et calcule les deux dérivées de la surface, le long de chaque axe de la carte. Leur produit vectoriel donne la normale.
- **Aucun bruit n'est évalué :** 16 lectures et quelques multiplications par pixel.

### Les zones de repli

**Là où la spline ne s'applique pas, le pixel garde la normale actuelle,** avec un fondu sur deux mailles.

- **Le bord de la face :** les deux cartes ne se prolongent pas l'une l'autre. Normale actuelle jusqu'à 3 mailles du bord, spline complète à partir de 5 mailles, des deux côtés.
- **Les coins des anneaux :** la grille y tourne d'un quart de tour. Même fondu, de 3 à 5 mailles du coin.
- **Les triangles entre la face et le premier anneau,** qui mêlent les deux cartes : normale actuelle.
- **Les sommets écartés hors du champ :** la marge d'écart passe de 3 à 6 mailles, pour que la spline n'en touche jamais à l'écran. Si l'un d'eux est touché malgré tout, normale actuelle.

## Ce qui change dans le code

- **`VertexShader.hlsl`** transmet au pixel ses coordonnées de carte, sa carte et sa distance au coin le plus proche.
- **`PixelShader.hlsl`** lit les sommets du maillage eux-mêmes, `splineVertices`, la ressource du vertex shader. Il reconstruit la normale et la mêle à la normale actuelle selon les zones de repli. Le grain fin par pixel s'ajoute ensuite, comme aujourd'hui.
- **`TerrainCompute.hlsl`** : marge d'écart de 6 mailles.
- **`PlanetSettings.hlsli`** : `SPLINE_NORMALS`, le poids de la normale spline. 1 l'active, 0 revient à la normale actuelle.

## La mesure

1. **Le banc de tremblement,** avec et sans lissage temporel, sur les trois vues de référence : montagne à 50 m et à 10 km, plaine à 10 km. `SPLINE_NORMALS` à 0 puis à 1, même binaire par ailleurs.
2. **Les cartes de chaleur du banc,** pour voir où le tremblement reste : les zones de repli devraient ressortir.
3. **Le coût GPU** de la spline.
4. **Le jugement en vol.**

## Critères de validation

- **Tremblement au banc nettement plus bas** sans lissage temporel, hors zones de repli.
- **Pas de couture visible** entre la spline et les zones de repli.
- **Coût :** moins de 0,3 ms en tout.

## Résultats du banc

Tremblement moyen entre deux images, sur 255, sans lissage temporel ; avec lissage entre parenthèses. Banc du 2026-10-21, mêmes vues que `log/spec-stabilite.md`.

| Variante | Montagne, 50 m | Montagne, 10 km | Plaine, 10 km |
|---|---|---|---|
| Normale actuelle, coupure à 2 mailles | 0,17 (0,04) | 1,20 (0,17) | 0,08 (0,01) |
| Spline cardinale | 0,27 (0,06) | 1,52 (0,24) | 0,09 (0,01) |
| Spline à moitié préfiltrée | 0,20 (0,04) | 1,24 (0,19) | 0,08 (0,01) |
| B-spline lissante | 0,15 (0,03) | 1,04 (0,15) | 0,07 (0,01) |
| B-spline lissante, matériaux sur la surface spline | 0,15 (0,03) | 1,01 (0,15) | 0,07 (0,01) |
| Idem, coupure à 3 mailles | 0,13 (0,03) | 0,69 (0,11) | 0,05 (0,00) |
| Idem, coupure à 4 mailles | 0,12 (0,02) | 0,51 (0,09) | 0,04 (0,00) |
| Normale actuelle, coupure à 4 mailles | 0,13 (0,03) | 0,60 (0,09) | 0,04 (0,00) |

- **La spline cardinale aggrave le tremblement :** elle restitue la pente des ondes de 2 à 3 mailles, que la normale actuelle effaçait presque. La table de `log/pistes-glissement.md` est corrigée en conséquence.
- **La B-spline lissante,** sans préfiltre, l'abaisse de 12 à 16 %. C'est le réglage gardé. Le préfiltre et son réglage, `SPLINE_SHARPENING`, sont retirés le 2026-10-30 ; tag `jalon/09-normales-spline`.
- **Les matériaux pris sur la surface spline,** à la rencontre du rayon de vue, n'apportent presque rien : 1,04 → 1,01. Gardé, car sans coût notable.
- **Le diagnostic :** éclairée avec une normale constante, la vue de montagne à 10 km tremble encore de 0,79. Les deux tiers du tremblement ne viennent donc pas de la normale, mais de la géométrie : les contours des reliefs qui se masquent.
- **La coupure du relief fait l'essentiel :** à 4 mailles, le tremblement est divisé par deux. La spline y ajoute 15 % sur la vue de montagne à 10 km.
- **Le prix de la coupure, jugé en vol :** chaque détail naît plus près de la caméra, donc plus grand à l'écran, et la forme mute davantage à l'approche. Coupure laissée à 2 mailles. Le banc ne mesure pas encore cette mutation lente.
- **Coût,** mesuré avec le préfiltre : moins de 0,1 ms en tout.
- **Les zones de repli** sont bien limitées : rendu du poids de la spline vérifié sur deux vues.
