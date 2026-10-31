# Spécification : le relief réel des matériaux

**Au log :** désactivée le 2026-10-23, son code retiré le 2026-10-30, `MaterialRelief.hlsl` et `MATERIAL_RELIEF` compris. Il reste au tag `piste/parois-gradins`, où il est actif. Voie géométrie : `../geometrie.md`.

Statut : validée le 2026-10-21. Étapes 1 à 3 faites ; gain visuel encore faible. Suite de la voie B (`spec-textures-generees.md`) : après six tours de banc, la roche reste plate. Recommandation 4 de `etat-de-l-art-details.md`.

## Le constat

**Le relief des matériaux n'existe que dans la normale.** Les bosses, les dalles, les fissures et les pierres éclairent comme du relief, mais :

- **aucune silhouette :** une pierre ne se découpe jamais sur le fond ;
- **aucune occultation :** rien ne cache rien ;
- **aucune ombre portée :** une bosse n'ombre pas sa voisine.

**C'est la limite de la texture seule,** et on l'a atteinte.

## Le but

**Que le maillage porte lui-même le relief des matériaux là où ses mailles le permettent.**

- **Près de la caméra, les mailles font déjà quelques centimètres :** 3 cm à 1,5 m du sol, 20 cm à 10 m.
- **Le relief des matériaux y devient une octave de plus du relief,** sous celles de complexplanet.
- **Plus loin, il reste dans la normale,** comme aujourd'hui.
- **Tout reste calculé à chaque image, sans mémoire.**

## Le principe

### Une passe de déplacement, après le relief

**Une seconde passe de calcul déplace chaque sommet visible** le long de la normale de la surface, de la hauteur des matériaux à son point de la planète.

1. **La normale du sommet,** par ses voisins, comme dans le vertex shader. Elle choisit les axes de la projection biplanaire et donne la direction du déplacement. Une bosse de roche avance donc hors de la paroi, et pas vers le ciel.
2. **Les poids des matériaux** : climat, pente, sable, éboulis, roche, neige. C'est le même code que les pixels du sol, mis en commun dans un fichier partagé.
3. **La hauteur de chaque matériau,** lue dans les textures générées, au niveau de mipmap qui correspond à la maille du sommet.
4. **Les rides du sable,** par la même fonction que les pixels, filtrée à la maille.
5. **Le déplacement,** mêlé par la hauteur comme les couleurs.

- **Pas de déplacement sous la mer.**
- **Sous la neige, le relief s'adoucit.**
- **Le préfiltre spline vient après :** les normales spline voient le relief déplacé.

### Le partage entre maillage et pixels

**Chaque longueur d'onde est portée une seule fois.**

- **Le maillage porte ce qui dépasse deux mailles,** selon la même règle de coupure que complexplanet, `MESH_BAND_LIMIT`. C'est ce que donne le niveau de mipmap choisi.
- **Les pixels ne gardent que le relief plus fin que la maille :** la pente de la texture moins sa pente au niveau de mipmap du maillage.
- **Les rides :** dans le maillage tant que deux mailles tiennent dans une ride, sinon dans les pixels.

### Les ombres

**Trois échelles, du plus fin au plus large.**

- **Ombres fines au soleil,** déjà en place : les creux coupent la lumière directe.
- **Ombres de la texture,** au pixel : quelques pas sur la hauteur de la texture, vers le soleil, pour le relief plus fin que la maille. Une fissure ombre son flanc, une pierre ombre la poussière. Huit pas au plus, seulement de près.
- **Ombres de contact du relief déplacé,** à l'écran : un court lancer de rayon vers le soleil dans la profondeur, à la manière de Bend Studio pour Days Gone. Il demande une passe de profondeur préalable, pour que le pixel shader du sol connaisse l'ombre avant d'éclairer. C'est l'étape la plus lourde : elle vient en dernier.
- **Les ombres des montagnes sur les vallées** restent hors de cette spec. Il leur faut une carte d'ombre ou un lancer de rayon sur le grand relief.

## Les risques

- **Tremblement :** le relief des matériaux glisse avec le maillage comme le reste du relief. La coupure à deux mailles et les normales spline le limitent. Le banc de tremblement le mesurera.
- **Mutation :** à l'approche, le relief passe des pixels au maillage. L'éclairage était déjà le même, seules silhouettes et occultations apparaissent, progressivement. Le banc de mutation le mesurera.
- **La caméra au ras du sol :** la hauteur sous la caméra ignore le relief des matériaux. À 1 m, une bosse de roche de 20 cm pourrait frôler l'objectif. On relèvera le plancher de la caméra de l'amplitude maximale du relief.
- **Le coût :** une évaluation des matériaux par sommet visible, soit 100 000 à 150 000. Ordre de grandeur : 0,3 à 0,6 ms.

## Ce qui change dans le code

- **`Materials.hlsli`,** nouveau : poids des matériaux, lecture des textures générées et rides, partagés entre le calcul des sommets et les pixels.
- **`MaterialRelief.hlsl`,** nouveau : la passe de déplacement.
- **`D3DApp.cpp`** : la passe, entre le calcul du relief et le préfiltre spline, et le plancher de la caméra.
- **`PixelShader.hlsl`** : il ne garde que le relief plus fin que la maille, et ajoute les ombres de la texture.
- **`PlanetSettings.hlsli`** : `MATERIAL_RELIEF`, l'intensité du relief déplacé ; 0 revient à la texture seule.

## Les étapes

1. **Le code commun,** sans changement de rendu, vérifié image pour image.
2. **Le déplacement,** sur la roche et les éboulis d'abord, puis le sable.
3. **Le partage entre maillage et pixels.**
4. **Les ombres de la texture.**
5. **Les ombres de contact,** avec la passe de profondeur.

## La mesure

- **Le banc visuel,** à 1,5 m, 10 m, 100 m et 1 km, sur la roche, les éboulis et le désert : silhouettes et occultations visibles de près.
- **Les bancs de tremblement et de mutation.**
- **Le coût GPU** de la passe et des ombres.

## Critères de validation

- **De près, les pierres et les bosses se découpent** sur le fond, et se cachent les unes les autres.
- **Pas de tremblement ni de mutation visibles en plus,** en vol.
- **Coût :** moins de 1 ms en tout pour les étapes 1 à 4.

## Résultats des étapes 1 et 2

- **Étape 1, le code commun :** `Materials.hlsli` et `Mesh.hlsli`, partagés par les pixels, le vertex shader et la passe de relief. Rendu identique au pixel près sur toutes les vues du banc.
- **Étape 2, le déplacement :** la passe `MaterialRelief.hlsl` déplace les sommets proches. Les fissures et les bosses de la roche prennent du relief réel.
- **Défaut attendu jusqu'à l'étape 3 :** le relief est compté deux fois, dans le maillage et dans la normale de la texture. Près de la caméra, il en résulte des facettes trop sombres le long des fissures.
- **Sable :** les rides de 6 mm changent peu la géométrie ; leur effet passe surtout par la lumière.

## Résultats de l'étape 3 et mesures

- **Le partage entre maillage et pixels :** chaque lecture de texture donne aussi sa pente à l'échelle du filtre du maillage ; le pixel la retranche, dosée comme la passe de relief. Les facettes trop sombres le long des fissures ont disparu.
- **Le tremblement, sur la roche, avec et sans lissage temporel :**

| Variante | Roche à 3 m | Roche à 14 m |
|---|---|---|
| Sans relief | 0,04 / 0,25 | 0,03 / 0,22 |
| Relief filtré à 2 mailles | 0,17 / 0,91 | 0,12 / 0,72 |
| Relief filtré à 4 mailles | 0,09 / 0,49 | 0,07 / 0,41 |
| Relief filtré à 8 mailles | 0,06 / 0,33 | 0,04 / 0,27 |

- **Réglage retenu :** `MATERIAL_RELIEF_BAND` = 8, le relief ne porte que les ondes de huit mailles et plus. Le sable ne tremble pas, ses rides de 6 mm changent à peine la géométrie.
- **Coût :** 0,1 ms de calcul en plus.
- **Le gain visuel reste faible :** en vue rasante à 1,5 m, sans relief et avec relief se ressemblent presque. Les bosses et facettes de la roche générée, de quelques centimètres à 15 cm, sont trop douces pour découper une silhouette. Il faudra des formes plus franches dans la recette, blocs, corniches, rochers, ou des objets semés.

## Correctif du 2026-10-21 : les pics

- **Symptôme :** en zone sèche, des pics de 10 à 30 cm qui scintillent en vol.
- **Cause :** le mélange par la hauteur n'est pas linéaire. Sur des hauteurs pourtant filtrées, il fait basculer un sommet d'un matériau à l'autre entre deux voisins. Le relief saute alors de celui de la roche, ±30 cm, à celui du sable.
- **Correctif :** la passe de relief mêle les matériaux par leurs poids de base, sans la hauteur. Le relief reste aussi filtré que les textures.

## Correctif du 2026-10-22 : lames, aiguilles et scintillement du relief

**Symptôme,** en vol après le jalon 13 : des lames et des aiguilles de un à trois mètres, et un relief qui scintille. Positions `6559.3 -18.67003 131.64985 37.0 -70.2` et `586.6 -25.21899 135.73187 -0.2 92.0`.

**Trois causes,** isolées une à une au banc de tremblement, qui reprend une position exacte :

1. **La neige se décidait sur le relief lui-même.** Dans la passe de relief, la pente des textures, celle du relief de la tuile de 64 m, chassait la neige. Or la neige écrase le relief à 10 % : un sommet sur deux basculait entre roche et neige, et dressait une lame.
   - **Correctif :** la pente des textures déplace la limite des neiges comme le mélange par la hauteur, avec le même dosage `gHeightBlend`. Elle est absente de la passe de relief et s'estompe pour les grands pixels.
2. **La projection biplanaire basculait près de la diagonale du cube.** Ses poids, élevés à la puissance 8, tendaient tous deux vers zéro quand la normale approchait d'une diagonale. Le moindre écart de normale faisait alors passer d'un plan à l'autre, et le relief d'une copie de tuile à une autre.
   - **Correctif :** des poids triplanaires `max(|n| − 0,45, 0)²`. Un plan seul à moins de 25° de son axe, deux le long d'une arête du cube, trois à sa diagonale, et continus partout.
3. **La normale de la passe de relief était trop fine.** Prise sur 4 mailles, elle suivait les ondes du maillage longues de 2 à 8 mailles, qui glissent sous les sommets. Les mètres de relief de la tuile de 64 m changeaient de projection à chaque image.
   - **Correctif :** la normale est prise sur 32 mailles, `RELIEF_NORMAL_CELLS`. Coût : +0,2 à 0,3 ms de calcul.

**Et une précaution :** les crêtes de complexplanet ne sont plus arrondies sur moins de deux mailles de 2 m, `CREASE_MIN_CELL`, si proche que soit la caméra. Le relief n'a pas d'octave sous 13,5 m, et une crête large de quelques centimètres tournait la normale d'un sommet à l'autre.

| Tremblement, avec / sans lissage | Avant | Après | Sans relief des matériaux |
|---|---|---|---|
| Roche rouge, `586.6 -25.21899 135.73187` | 10,1 / 21,4 | 2,1 / 7,5 | 1,1 / 5,6 |
| Crête enneigée, `6559.3 -18.67003 131.64985` | 1,7 / 7,8 | 0,55 / 1,1 | 0,45 / 1,7 |
| Crête enneigée, `6561.8` | 0,19 / 0,86 | 0,12 / 0,48 | 0,12 / 0,56 |
| Dune, `563.6 5.98065 127.83668` | 0,16 / 1,0 | 0,16 / 0,94 | 0,13 / 0,86 |
| Site de la roche, 3 m | | 0,10 / 0,42 | 0,06 / 0,29 |

- **Les lames et les aiguilles ont disparu** sur les deux vues signalées. Les corniches de la tuile de 64 m restent sur les falaises.
- **Il reste un surcoût de tremblement** sur la roche rouge, 2,1 contre 1,1 sans relief.
- **La vraie solution, à étudier :** une structure de roche en volume, fonction de l'altitude et de la position, plutôt que projetée sur des plans. Strates et diaclases n'auraient alors plus de projection à choisir, ni de normale dont dépendre.

## Correctif du 2026-10-22 : une corniche qui change de matériau à l'approche

**Symptôme,** en vol : de 11 m à 5 m d'une corniche, positions `2182.0 31.16045 8.58814 1.9 -17.1` à `2181.5 31.16051 8.58812 2.3 -11.8`.
- De loin, la corniche se voit par sa couleur.
- En approchant, la couleur disparaît, et la géométrie se forme.
- Tout près, une autre tache de sable apparaît, d'une autre forme.

**La cause :** les matériaux, roche, replat ou sable, se décidaient sur la normale du maillage. Or le maillage porte une part croissante du relief des matériaux à mesure que ses mailles rétrécissent. Le replat devenait plat dans la géométrie, n'était plus de la roche, et changeait de matériau.

**La règle, qui vaut pour tout matériau :** les décisions ne dépendent jamais de la part du relief que porte le maillage.
- **La normale de décision** est celle du terrain seul. Le vertex shader la calcule sur les sommets d'avant la passe de relief. De loin, la grille fine, qui ne porte que le terrain, prend le relais.
- **Les textures rendent leur pente entière,** et à part, la part que porte le maillage (`Texture.carried`). Les décisions prennent la pente entière ; la lumière des pixels en retire la part portée.

**Mesures :**
- **Sans relief dans le maillage,** la corniche gardait déjà sa couleur et sa forme sur les trois positions : c'est la référence.
- **Avec ce correctif,** la bande claire du replat reste à sa place de 11 m à 5 m.
- **Tremblement,** à 5 m : 0,31, contre 0,29 avant le correctif et 0,22 sans relief. À 11 m : 0,17 contre 0,18.
- **Banc de descente :** roche et neige inchangées.

**Ce qui reste :** la géométrie de la corniche apparaît encore dans les derniers mètres. C'est le prix d'un maillage qui ne porte un relief qu'à partir de huit mailles par longueur d'onde. Pour l'adoucir, il faudrait que les pixels montrent la profondeur avant le maillage, par une parallaxe, ou que le maillage porte le relief plus tôt, au prix du tremblement.
