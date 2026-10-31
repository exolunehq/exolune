# État de l'art : des détails de près convaincants

Statut : recherche du 2026-10-21, faite après le jugement en vol de la roche de l'étape D, « ne rend pas bien ». Synthèse de trois recherches : matériaux et techniques hybrides, herbe, roche et micro-relief.

## La conclusion

**Aucun moteur qui paraît réaliste de près ne dessine le sol avec du bruit calculé au pixel seul.** Tous font la même séparation :

- **Des règles procédurales décident où** va chaque matériau : climat, pente, courbure, altitude. C'est ce que fait déjà notre étape C.
- **Des matériaux d'exemple décident à quoi il ressemble :** de petites textures sans couture, scannées ou générées par un graphe de type Substance. Couleur, relief, rugosité et creux y sont corrélés.
- **La géométrie porte ce qui se dresse :** herbe, cailloux, rochers, falaises.

**Le procédural réaliste existe, mais il est hybride.** Soit il s'appuie sur des scans, soit il génère ses textures d'exemple une fois, avec des recettes soignées, puis les répète sans motif visible.

## Pourquoi notre sol paraît faux

- **Le détail ne vit que dans la normale :** pas de creux qui s'assombrit, pas d'ombre, pas de parallaxe, pas de silhouette. D'où l'aspect d'enduit.
- **Couleur, relief et rugosité viennent de bruits séparés,** sans lien entre eux. Dans une vraie roche, tout est corrélé : la fissure est creuse, sombre et mate à la fois.
- **Le bruit de gradient est rond et isotrope.** La roche est faite de faces planes, d'arêtes vives et d'éclats.
- **Les strates sont des lignes de niveau d'un bruit,** et non des plans inclinés.
- **L'herbe sous 10 m, ce sont des brins.** Aucune texture ne les remplace en vue rasante.

## Ce que font les autres

| Moteur | Sol de près |
|---|---|
| Star Citizen, Planet Tech v4/v5 | Le climat choisit le biome. Jeux de matériaux construits dans Substance, calés sur des scans, mélangés par la hauteur, avec parallaxe. Rochers et falaises en objets placés |
| Outerra | Matériaux choisis par altitude, pente et courbure ; trois petites textures mêlées par un bruit fractal contre la répétition |
| SpaceEngine | Table de 128 textures sans couture, choisies par altitude, latitude et pente, mélangées par la hauteur |
| Horizon Zero Dawn | Placement sur GPU, déterministe et stable, de plus de 100 000 objets pour 0,25 ms |
| Ghost of Tsushima | Chaque brin d'herbe généré sur GPU à chaque image ; textures et placement par règles |
| Far Cry 4 et 5 | Texture virtuelle mise en cache autour de la caméra ; falaises en objets, déplacement du terrain |
| Unreal Engine 5 | Couches mêlées par la hauteur, texture virtuelle, déplacement par tessellation, placement procédural |

**La leçon d'Elite Dangerous :** sans technique contre la répétition, les joueurs voient le motif des textures.

## Les techniques utiles

### Répéter une texture sans que ça se voie

- **Pavage hexagonal,** Mikkelsen 2022. Une grille d'hexagones, chacun avec un décalage et une rotation au hasard, mêlés avec des poids accentués. 3 lectures, aucun précalcul, normales tournées correctement. **Le meilleur choix par défaut.**
- **Mélange préservant l'histogramme,** Heitz et Neyret 2018. Même idée, contraste exact, mais il faut un précalcul par texture et le résultat se limite aux textures sans formes nettes.
- **Tout ceci est ancré sur la planète :** les cellules sont hachées sur des indices entiers, donc rien ne glisse. Nos indices de réseau exacts autour de l'ancre de 64 m conviennent tels quels.

### Générer des textures réalistes au démarrage

- **Un graphe de nœuds à la Substance,** porté en compute et exécuté une fois au démarrage, comme nos tables d'atmosphère : répartition de motifs, flou de pente, déformation directionnelle, cellules, fissures, érosion.
- **Il produit des tableaux de textures sans couture,** couleur, normale, hauteur et rugosité en 1K à 2K, par matériau et par graine de planète.
- **Réalisme : élevé pour roche, fissures, graviers, sable et neige ; moyen pour la terre et la litière.** Le coût à l'image est celui de textures ordinaires.
- **Référence ouverte :** les nœuds GLSL de Material Maker.

### Mieux faire la roche, même procédurale

- **Un seul champ de hauteur par matériau,** avec son gradient analytique. La normale, les creux, les ombres fines et la couleur en dérivent. C'est cette cohérence qui donne l'impression de matière.
- **Des blocs, pas des bosses :** l'identifiant de la cellule de Voronoï donne à chaque bloc une face plane inclinée au hasard, avec des arêtes chanfreinées. On obtient des plateaux aux bords ébréchés.
- **Des strates en relief :** des plans inclinés, en gradins, où les couches dures avancent et les tendres reculent.
- **L'érosion :** le filtre d'érosion de Clay John, raffiné en 2023 puis en 2026, trace des ravines ramifiées le long de la pente. Le fBm à dérivées d'Inigo Quilez donne une érosion bon marché.
- **La couleur suit la forme :** poussière dans les creux, coulures sombres dans le sens de la pente, lichens sur les faces bombées tournées vers le haut, mousse dans les creux.

### L'éclairage qui fait le volume

- **Les creux :** le relief complet moins le relief lissé, presque gratuit.
- **Les ombres fines,** à la manière de Call of Duty WWII : l'occlusion se change en cône qui coupe la lumière directe. Quelques opérations par pixel.
- **Les ombres de contact,** écran par écran : le code de Bend Studio pour Days Gone est public. Il saisit les ombres au centimètre.
- **La rugosité varie dans les creux.** Elle compte plus que la brillance.

### Le relief réel, en géométrie

- **Notre maillage a déjà des mailles de quelques centimètres** sous une caméra à 1 m du sol. Ajouter le champ de hauteur des matériaux au relief de complexplanet donne vrais creux, vraies ombres et vraies silhouettes.
- **C'est l'octave de plus dont tu parlais,** filtrée à 2 mailles comme les autres. Le banc mesurera son tremblement et sa mutation.
- **La parallaxe** n'a de sens qu'avec des hauteurs en texture, donc avec un graphe au démarrage ou des scans. Elle coûte des dizaines de lectures par pixel et ne change pas la silhouette.

### Les objets semés

- **Cailloux, pierres, rochers :** des cases fixes sur la planète par classe de taille, environ 25 cm, 2 m et 16 m. Le hachage de la case donne existence, position, rotation, taille et variante.
- **10 à 30 formes de rochers,** générées au démarrage à partir de sphères déformées par un bruit ou de blocs fracturés. Chaque rocher est enterré de 20 à 40 % pour cacher le contact.
- **Les falaises :** aucun moteur publié ne les rend avec le seul relief. Tous ajoutent des objets.

### Le neuronal

- **Rien ne bat aujourd'hui** les textures d'exemple avec pavage hexagonal, en réalisme par milliseconde.
- **Le seul usage utile :** entraîner hors ligne, puis générer au démarrage.

## Les trois voies

| Voie | Principe | Réalisme | Concept |
|---|---|---|---|
| **A. Procédural amélioré** | Champ de hauteur unifié, blocs, strates en relief, érosion, creux et ombres fines, au pixel | Moyen à bon | Intact |
| **B. Procédural généré au démarrage** | Graphe de nœuds en compute au démarrage, tableaux de textures, pavage hexagonal, mélange par la hauteur | Bon, proche de Star Citizen pour roche, sable et neige | Intact : aucun fichier, une planète différente par graine |
| **C. Hybride avec des scans** | Scans libres de droits, Poly Haven et ambientCG en CC0, pavage hexagonal, choisis par nos masques | Le meilleur, surtout pour la terre et la litière | Abandonne la règle « aucune image chargée », pour quelques Mo |

**Dans les trois voies,** l'herbe est en géométrie, les cailloux et rochers sont semés, et les ombres de contact et fines sont ajoutées.

## Recommandation

**La voie B, bâtie sur A.** Elle est la plus fidèle au concept et atteint un bon réalisme.

1. **Le champ de hauteur unifié de la roche,** avec blocs, strates en relief, creux et ombres fines. C'est le gain le plus rapide contre l'aspect d'enduit, et la recette du graphe de la voie B en découle.
2. **Les brins d'herbe en géométrie,** selon `spec-herbe.md` révisée.
3. **Le graphe au démarrage et le pavage hexagonal,** pour roche, sable, neige et graviers.
4. **Le relief des matériaux ajouté au maillage,** plus les ombres de contact.
5. **Les cailloux et rochers semés.**

**Un étalon, sans renoncer au procédural :** garder deux ou trois scans CC0 hors du moteur, comme référence visuelle pour juger nos matériaux côte à côte. La voie C reste une porte de sortie si la terre et la litière restent trop pauvres.

## Sources principales

- Pavage hexagonal, Mikkelsen 2022 : https://jcgt.org/published/0011/03/05/
- Mélange préservant l'histogramme, Heitz et Neyret 2018 : https://eheitzresearch.wordpress.com/722-2/
- Star Citizen Planet Tech v4 : https://starcitizen.tools/Planet_Tech_v4
- Outerra, textures de détail : https://gamedev.net/blogs/entry/1884822-playing-with-detail-texturing
- SpaceEngine, matériaux : https://spaceengine.org/news/blog110730/
- Placement sur GPU dans Horizon Zero Dawn : https://www.guerrilla-games.com/read/gpu-based-procedural-placement-in-horizon-zero-dawn
- Herbe de Ghost of Tsushima, GDC 2021 : https://www.youtube.com/watch?v=Ibe1JBF5i5Y
- Terrain de Far Cry 5 : https://gdcvault.com/play/1025261/Terrain-Rendering-in-Far-Cry
- Filtre d'érosion, 2026 : https://blog.runevision.com/2026/03/fast-and-gorgeous-erosion-filter.html
- Bruits à dérivées, Inigo Quilez : https://iquilezles.org/articles/morenoise/
- Ombres fines, Call of Duty WWII : http://www.realtimerendering.com/advances/s2018/MaterialAdvancesInWWII-course_notes.pdf
- Ombres de contact, Bend Studio : https://www.bendstudio.com/blog/inside-bend-screen-space-shadows/
- Material Maker : https://rodzilla.itch.io/material-maker
- Licences CC0 : https://polyhaven.com/license , https://docs.ambientcg.com/license/
