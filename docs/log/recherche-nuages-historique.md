# Historique des nuages : la couche 2D et l'ancien volume

**Ce qu'a donné `../recherche-nuages.md` les 24 et 25 octobre 2026,** sorti de la recherche le 2026-10-30 : la carte du temps et la couche 2D, commit `6a88d33`, puis le volume en cascades de l'orbite au sol, tag `piste/nuages`, et sa stabilité, branche `muse-nuages-stabilite`. Les nuages du jeu les remplacent : `../spec-nuages.md`.

Les sections suivent, telles qu'elles étaient dans la recherche, la plus récente en haut.

## Fait : le volume, de l'orbite au sol (2026-10-25)

**La couche 2D est retirée.** Les nuages sont un volume lancé au quart des pixels partout où ils sont en vue, de l'orbite au sol, la moitié d'entre eux par image en damier, accumulé d'une image à l'autre. Le plan gardait une couche 2D de loin : en vol, elle était plate, pleine, sans transparence, et coupait les ponts aux côtes.

**Le champ.**
- **La carte du temps est cuite au démarrage,** sur un cube : le climat et les octaves du temps de 131 km et plus.
- **Les colonnes tiennent dans cinq cascades fixées sur la planète,** de 62,5 m à 16 km le texel, chaque texel la moyenne de la colonne sur lui. Une cascade n'est recalculée que quand la caméra a parcouru le quart de sa largeur. Au-delà de la dernière, au limbe, la colonne est calculée sur place.
- **Les octaves de 1 km et moins passent en 3D.** Une tuile de cellules en volutes les remplace, de même écart-type (0,389 de celui des nuages). Elles découpent les bords et soulèvent le sommet : cumulus en chou-fleur, ponts bosselés. De loin, les mips de la tuile en rendent la moyenne : la règle universelle.
- **Le sommet monte avec la profondeur dans le champ :** les nuages s'amincissent à leur bord, en dômes pour les cumulus, à flancs raides pour les ponts.
- **Les cumulonimbus :** en forte convection, les pics des octaves de 16 et 8 km, un dixième de l'air environ. Tours jusqu'à la tropopause, flancs bosselés par un décalage de lecture qui varie avec la hauteur ; enclumes parmi les cirrus.
- **Les cirrus en fibres,** d'est en ouest, la tuile étirée huit fois.
- **Plus de grilles de points vues d'orbite.** Les octaves d'un bruit de gradient partageaient les nœuds de leurs grilles emboîtées, où toutes s'annulent ensemble. Chaque octave est décalée d'une fraction du nombre d'or (`CloudFbm`).

**La lumière.**
- **Simple diffusion :** trois points vers le soleil, de 50 m à 1,5 km ; deux lobes de Henyey-Greenstein ; la poudre des bords à contre-jour.
- **Diffusion multiple à deux flux (Bohren 1987) :** R sur la face éclairée, le diffus transmis sur l'autre, entre les deux selon la part de l'épaisseur optique côté soleil, prise le long du rayon du soleil. Flancs éclairés, bases et faces à l'ombre sombres. La première version inversait les deux faces : des sommets gris, des nuages minces laiteux.
- **Le ciel par le haut, le sol par le bas.**
- **Un pas par unité d'épaisseur optique environ,** pour ne pas sauter la peau éclairée ; le pied d'un pas vaut l'empreinte du pixel, plus un quart du pas.

**Dans les autres passes.** Le terrain écrit sa lumière du soleil seule dans une seconde cible ; la passe d'atmosphère y applique l'ombre des nuages et la lumière diffuse sous eux, et coupe l'air à la profondeur des nuages.

**La stabilité (2026-10-25, branche `muse-nuages-stabilite`).** En vol : fourmillements, coutures carrées puis tournées des cascades, disque du détail proche, mutations à l'approche. Le champ est figé : tout ce mouvement était de l'échantillonnage.
- **L'historique se gouverne par l'erreur de reprojection** (`CloudResolve.hlsl`) : en texels du quart de résolution. Dessous, la marche de l'image précédente, fraîche ou autre moitié du damier, est un échantillon du même nuage et s'accumule ; au-delà d'un texel, le texel non marché porte son passé reprojeté seul, et un écart de distance (le centroïde d'opacité, en rampe large) retire le passé. La distance elle-même s'accumule. Le passé est clipsé aux moments du voisinage, deux écarts-types.
- **Les cascades ne dessinent plus leur carré** : portée en distance sur le plan, fondu de 0,35 à 0,98 du demi-côté, niveau fin fractionnaire en descente, maximum lissé entre contraintes de niveau (`LevelMax`, règle dans `../principes.md`), recentrage par texels entiers du plan propre, axes transportés.
- **Le détail proche garde la moyenne** : fondu par octaves d'empreinte ; sommet multiplié en lognormal, de moyenne la colonne ; porte décalée de la corrélation porte × plafond, `fine × lift`.
- **La coupure au terrain** lit la distance des nuages filtrée comme leur lumière ; la distance de reprojection du lissage est pondérée par l'opacité.
- **Le décalage de la marche reste renouvelé par image** : fixe par pixel, il laissait le biais de quadrature de chaque texel en pointillé régulier sur les images convergées, mesuré ; en progression dorée commune, le tremblement doublait. C'est l'historique gouverné qui l'absorbe.
- **Mesures :** `tools/banc_nuages.py --parts stabilite` (nouveau) et `docs/journal-planete.md`, même jour.

**Les mesures :** `../journal-planete.md`, 2026-10-25.

**Ce qui reste :**
- **le coût dépasse le budget sous les cirrus,** 3,6 ms, voir le journal ;
- **les tours de cumulonimbus sont trop régulières,** des cylindres bosselés coiffés d'un disque ;
- **pas de vent :** cirrus et rues de nuages figés ; le mouvement ample des formations est le chantier suivant, le champ restant une fonction pure du lieu et du temps pour que l'historique se reprojette ;
- **un arc fin au passage de portée des cascades,** adouci mais visible sur les captures à 54 et 135 km : plafond et sigma d'un texel grossier ne sont pas la moyenne des texels fins qu'il couvre. La règle voudrait des cascades grossières moyennées depuis les fines là où elles se recouvrent, au lieu d'un `ColumnAt` par texel à chaque échelle.

## Fait : étapes 1 et 2

**La carte du temps décide, par colonne d'air :**
- **la nébulosité,** la part moyenne de ciel couvert : l'humidité du climat et une ceinture montante au front polaire, de 19 à 56° ;
- **la convection,** de 0 à 1 : chaleur et humidité au niveau de la mer, et `W.y` ;
- **le type :** stratiforme sans convection, cumulus avec, cumulonimbus au cœur des nuages en forte convection ;
- **la base,** par la formule de Lawrence ; le brouillard quand elle touche le sol, 2 à 3 % des colonnes ;
- **le sommet :** 0,3 km pour les stratus, 1,5 km pour les cumulus ;
- **les cirrus :** une couche de 1,5 km, 3 km sous la tropopause, leur nébulosité tirée du front polaire et des enclumes.

**Ce qui s'écarte du plan.**
- **Un seul spectre, du millier de km au mètre.** Le temps `W` et les nuages `M` sont les octaves d'un même bruit de gain 0,79, le spectre en k^-5/3 des champs nuageux (Cahalan et Snider 1989). Les fronts sont dans le champ seuillé, pas dans la nébulosité. Avec les gains 0,5 et 0,55 du plan, rien entre 30 et 300 km : tous les nuages avaient la même taille, en peau de léopard.
- **Les cumulus pèsent leurs petites octaves 2,5 fois plus :** des champs épars sur des régions entières. Les fronts font des nappes.
- **Pas de ceinture intertropicale :** l'ajustement lui donnait 0,065. Le creux d'humidité des déserts porte déjà le profil.
- **Les couches sont des coquilles épaisses,** de la base au sommet, placées par les octaves du temps de 131 km et plus.
- **Un rayon voit la première cellule qu'il rencontre,** celle du pixel, puis la moyenne de la région derrière elle : une cellule tous les 5 km le long du trajet, mesurés sur le champ. La moyenne sur tout le trajet rendait flou un champ vu de biais.
- **La lumière : deux flux, g = 0,85.** La part diffusée vers l'avant reste dans le faisceau (delta, 1 − g²) : un cirrus laisse voir ce qu'il couvre. Le sommet des cumulus est éclairé selon sa pente, chaque octave l'inclinant autant, comme les bandes de détail du sol.

**Les mesures :** `../journal-planete.md`, 2026-10-24. Bancs : `tools/banc_nuages.py`. Tests en vol : `tools/tests/2026-10-24-nuages.txt`.

**Ce qui restait plat ou manquait après l'étape 2,** traité par le volume sauf le vent :
- **dans la couche, tout est plat :** pas de tours ni de flancs. La caméra dans le nuage y voit un brouillard uniforme ;
- **les cirrus ne sont pas effilochés :** il faudrait le vent ;
- **l'air sous les nuages est ombré par la moyenne de la région,** pas nuage par nuage ;
- **le sol ne renvoie pas sa lumière vers la base des nuages ;**
- **le coût dépasse le budget du plan,** voir le journal.
