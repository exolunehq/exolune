# Historique de la recherche sur la végétation : les plantes générées

**Les plantes générées des versions 1 à 3,** sorties de `../recherche-vegetation.md` le 2026-10-30, quand leur code a quitté le moteur, commit `3a4508a` : `Vegetation.cpp`, `PlantVertex.hlsl`, `PlantCoarseVertex.hlsl`, `PlantPixel.hlsl`, `LEAF_ALBEDO`, `PLANT_PIXELS` et le banc `banc_vegetation.py cout`. Elles restent aux tags `piste/vegetation`, `piste/vegetation-v2` et `piste/vegetation-v3`.

**L'état présent :** depuis le 2026-10-27, le jeu dessine la même population par ses modèles, `../vegetation-planetaire.md`. Le climat, le placement et la canopée au sol sont restés, `../recherche-vegetation.md`.

## Étape 1

**Les formes, générées au démarrage :** trois espèces de quatre variantes, une même topologie, 402 sommets et 712 triangles.
- Un tronc, huit masses de feuillage, icosphères de 42 sommets ridées par quelques ondes, une branche vers chacune.
- Le conifère en verticilles empilés en cône, dès 0,3 à 0,45 de sa hauteur ; le feuillu en masses autour d'une couronne ellipsoïdale ; l'arbuste en masses basses.
- Chaque couronne est élargie pour que son empreinte vue de dessus soit le disque de Tallo : 0,3, 0,45 et 1,1 fois la hauteur.
- Son ombre propre : la part du ciel que chaque sommet voit entre les autres masses, 64 rayons.

**Le fondu, une croissance :** la plante sort du sol de 24 à 36 pixels de haut ; seulement où les mailles font moins d'une fois et demie sa hauteur.

**La lumière des feuilles, au banc `raccord` :**
- **Le réglage mesuré :** l'albédo des feuilles sur celui de la canopée, par espèce, `LEAF_ALBEDO` : 2,6 pour les conifères, 1,7 pour les feuillus, 1,8 pour les arbustes. Une feuille réfléchit plus qu'une canopée, qui cache ses ombres.
- **Avant l'ombre propre tirée des masses,** les conifères demandaient deux fois l'albédo des feuillus ; après, 1,5 fois.

### Le coût

`banc_vegetation.py cout`, sous la charge de plusieurs autres instances, médianes de trois passages ; le placement et le dessin des objets sur le calcul du terrain de la même capture.

| Vue | Plantes | Placement / calcul du terrain, avant puis après | Dessin des objets, avant puis après |
|---|---|---|---|
| Forêt tempérée, 2 m | 7 900 | 19 % puis 24 % | 0,34 puis 0,67 ms |
| Forêt tempérée, 150 m | 5 900 | 0 puis 30 % | 0 puis 0,45 ms |
| Forêt boréale, 150 m | 11 000 | 9 puis 47 % | 0 puis 0,66 ms |
| Forêt boréale, 2 m | 19 900 | 11 puis 26 % | 0 puis 1,35 ms |
| Savane, 2 m | 350 | 20 puis 24 % | 0,26 puis 0,32 ms |
| Crête herbeuse, 1,7 m | 1 000 | 11 puis 11 % | 0,23 puis 0,28 ms |

- **Les temps gonflent tous sous la charge,** le calcul du terrain de 17 à 60 ms au lieu de 2 à 5 ms au repos. Rapporté au repos, le placement des plantes coûte de 0,1 à 2 ms, le plus dans la forêt boréale dense ; leur dessin, 0,1 à 0,2 ms.
- **Le chemin vers ce coût :**
  - la passe légère borne chaque candidat par le climat avant la lourde : de 37 000 à 21 600 candidats lourds dans la forêt tempérée, pour 7 900 plantes ;
  - elle tire l'espèce comme la lourde, au lieu de borner par la plus étroite des couronnes ;
  - la lourde décide sans échantillonner les textures, ni les strates (`gMaterialTextures`) ;
  - aucun dispatch des plantes plus haut que leur fenêtre, 1,7 km.
- **Ce qui borne la portée à 24 pixels :** le nombre de plantes à portée croît comme l'inverse du carré du seuil ; à 6 pixels, seize fois plus. D'où le cache par tuile.

### Le banc de qualité

`banc_qualite.py`, 12 lieux, graine 1, avant puis après sur les mêmes lieux ; le GPU partagé n'a pas permis les 30 lieux habituels, le tirage des lieux dépassant 10 minutes.
- **L'herbe gagne de 50 m à 3 km :** son détail fin, hf médiane, +4 à +10 dB ; la prairie floue devient canopée et couronnes.
- **Ce qui se dégrade, au-delà des 10 % de la règle :**
  - à 12 m, les troncs comptent comme des segments droits, 11 par vue contre 0,6 ; la répétition p95 de l'herbe monte de 0,10 à 0,46, les quatre variantes de chaque espèce et leurs masses rondes ; son trou p95, de 3,2 à 8,7 dB ;
  - à 12 m, le détail fin du sable, −8 dB, et du sol nu, −7 dB : les masses lisses des arbustes devant eux ;
  - la mutation p95, de +16 % à 200 m à +45 % à 800 m : la canopée sombre change de part avec la roche et les éboulis, décidés sur la normale du maillage, avec plus de contraste que l'herbe.
- **Les deux premières viennent des formes :** des troncs droits et des masses lisses. Plus de variantes, des troncs courbes, des feuilles et des trouées de près les traiteront ; c'est l'étape des formes. La troisième est la mutation des limites de roche, déjà là, rendue plus visible.

### L'aspect

Planche : `../journal/2026-10-25-vegetation.jpg`, les quatorze vues de `tools/tests/2026-10-25-vegetation.txt`.
- **Une pente de conifères :** à 150 m, une forêt sombre de cônes sur la neige, sa lisière avec la canopée au sol lointaine sans marche visible. Sur les photos, les cônes sont plus effilés et plus irréguliers.
- **Une lisière de forêt tempérée,** depuis une clairière : un mur de troncs et de couronnes, le sol de la clairière au soleil, celui de la forêt à l'ombre. Sur une photo, la lisière porte des arbustes et des branches basses, le manteau ; ici, des troncs nus jusqu'à mi-hauteur.
- **Une savane :** des arbres épars à couronne plate, des arbustes, l'herbe entre eux ; de 100 m, les arbres se comptent. Sur une photo d'acacias, les couronnes sont plus fines, plus étalées, en parasol.
- **Un maquis :** des arbustes gris olive serrés, quelques arbres. Sur une photo, les arbustes sont plus bas, plus denses, d'un vert plus sombre, sans les masses rondes.
- **Ce qui reste loin :** les masses de feuillage lisses, sans feuilles ni trouées ; le sous-bois très sombre, l'exposition ne voyant pas le couvert ; pas d'ombres portées des plantes.

## v2

**Les formes, `Vegetation.cpp` :**
- **Huit variantes par espèce au lieu de quatre,** douze masses au lieu de huit, 594 sommets.
- **Le conifère** en verticilles étagés, chacun un peu hors de l'axe ; **le feuillu** en deux couches de masses autour d'une couronne penchée, souvent sur plusieurs troncs ; **l'arbuste** bas, sur trois tiges.

**Sortir plus tôt :**
- **Les plantes sortent du sol de 14 à 21 pixels de haut,** au lieu de 24 à 36 : 1,7 fois plus loin, un arbre de 20 m à 1 km.
- **Deux niveaux de la même forme :** sous 48 pixels, une forme grossière de 156 sommets, les coins des icosaèdres ; de 64 à 48 pixels, chaque sommet fin glisse vers le milieu de l'arête grossière qu'il coupe. Le passage ne montre rien.
- **Pourquoi pas d'imposteurs :** la forme grossière coûte 156 sommets, et son raccord à la forme fine se fait sans trame ni fondu. Les imposteurs restent la voie pour descendre sous 14 pixels.
- **Le banc `tests <fichier> v2`** écrivait la palette v2 ; `tests` n'écrit plus que la palette v3.

**Le coût** (`banc_vegetation.py cout`, au repos, médianes de trois passages, ms) : le placement des objets, cailloux et touffes compris, et leur dessin.

| Vue | Placement v1 | Placement v2 | Dessin v1 | Dessin v2 | Plantes fines v2 |
|---|---|---|---|---|---|
| Forêt tempérée, 2 m | 1,10 | 2,16 | 0,63 | 0,72 | 1 079 |
| Forêt tempérée, 150 m | 0,48 | 1,53 | 0,39 | 0,51 | 554 |
| Forêt boréale, 150 m | 0,65 | 1,49 | 0,66 | 0,81 | 733 |
| Forêt boréale, 2 m | 1,60 | 1,62 | 1,29 | 0,53 | 2 737 |
| Savane, 2 m | 1,32 | 1,21 | 0,10 | 0,14 | 116 |
| Crête herbeuse, 1,7 m | 1,04 | 1,66 | 0,12 | 0,12 | 221 |

- **Les plantes seules, sans les cailloux ni les touffes :** 0,6 à 1,6 ms en v2, 0,4 à 1,2 ms en v1, pour une portée 1,7 fois plus grande, trois fois plus de surface. Plus de 20 000 plantes grossières au loin dans les forêts.
- **Le chemin vers ce coût :** le premier jet des tuiles coûtait 2,5 à 4 ms. Le sol exact par plante en prenait les deux tiers, par la divergence de seize plantes par fil ; posé sur le sol dessiné au loin, il ne sert plus qu'aux plantes fines. La passe légère écarte la tuile par son milieu ; le champ des taches n'est lu que dans les bois.

## v3

**Ni rétrécir ni enfler** (`Vegetation.cpp`) :
- **La forme grossière couvre l'écran comme la fine :** les coins de chaque masse écartés de son centre de 1,104, le rapport des aires de l'icosaèdre et de l'icosphère, 9,57 et 11,67.

**Les arbustes :**
- **Un buisson est un dôme posé au sol :** ses masses partent du sol, ses tiges cachées dedans. Les buissons du désert ne lisent plus comme de petits arbres.
