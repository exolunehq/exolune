# Vaisseau triangulaire

**Fichiers**

- `vaisseau_travail.blend` : scène modifiable, pièces du cockpit séparées et textures incluses.
- `vaisseau.glb` : modèle statique glTF 2.0, textures incluses, sans décor ni panaches.
- `vaisseau.vsx` : le paquet lu par le moteur, cuit depuis le GLB par `paquet_moteur.py` (`python paquet_moteur.py`, sans Blender) ; à relancer après chaque export (`docs/spec-vaisseau.md`).
- `forme.py` : la forme N, une seule source pour `design_v2.py`, `details_v3.py` et `controle_geometrie.py` : le dessus creusé sous la verrière, la goutte et la bulle, leurs seuils. Le moteur en recopie les nombres (`Ship.hlsli`).
- `pieces_mobiles.py` : marque le manche et la manette des gaz, que le moteur fait tourner, et pose leurs pivots.
- `exporter.py` : l'export du GLB, commun à `preparer.py`, `pieces_mobiles.py` et `details_v3.py`.
- `details_v3.py` : les petites pièces de peau, les feux et l'équipement du cockpit, posés sur la scène de travail sans changer la silhouette. Rejouable : il retire ses propres objets avant de les reconstruire.
- `modules_cockpit.py` : dimensions, commandes et place dans l'atlas de chaque module d'équipement. Source unique de la sérigraphie et de la géométrie.
- `plaques.png` : atlas de sérigraphie des modules, 2048 × 2048.
- `poupe_base.png` : le fond de poupe, carreaux de céramique, métal bleui autour des tuyères et suie, 1024 × 1024 ; fait par `design_v2.py`.
- `cockpit.png`, `commandes.png`, `pilote.png`, `pupitre.png`, `exterieur.png`, `arriere.png` : rendus de contrôle de la scène Blender. La verrière est masquée sur les vues du cockpit et des commandes.
- `export_controle.png` et `export_pilote.png` : rendus du GLB réimporté dans une scène vide.

**Modèle**

- Reprise du fichier `spaceship.blend` d'Antigravity, conversation « Blender Spaceship 3D Modeling » du 25 octobre 2026. L'original reste intact.
- Silhouette triangulaire d'origine. Coque, poupe et cockpit sont reconstruits par `design_v2.py` ; aucune pièce d'origine ne reste dans le modèle.
- **Forme N, choisie le 2026-10-31 sur maquettes** (`forme.py`), d'après la verrière arrondie d'une autre version Antigravity :
  - **la verrière écrase la ligne :** l'arête garde sa pente jusqu'au nez de la bulle, s'aplatit sous elle, 33 cm plus bas qu'avant à son arrière, puis remonte jusqu'au sommet de la poupe, qui ne bouge pas ;
  - le dessus fait trois facettes de chaque côté, en éventail depuis le coin de chine de la poupe ; leurs plis partent du nez et de la queue de la bulle ;
  - **la bulle :** une goutte sans pointe de 4,24 m sur 1,60 m, deux demi-ellipses jointes au plus large ; son sommet monte à 1,48 m, ses flancs sont pleins ; elle est assise dans le creux et son arrière rentre dans la coque qui remonte ;
  - un bourrelet de métal en couvre le pied ; un pourtour peint de 15 cm la sépare des tôles.

**Coque**

- Une peau continue ferme le volume, de la pointe au cadre de poupe. Les tôles affleurent toutes à 12 mm au-dessus, séparées par des joints gravés de 4 mm.
- La tôlerie suit la structure. Des sections entre cadres principaux, aux pointes avant et arrière du vitrage, croisent des bandes entre lisses qui convergent vers le nez. Les joints sont décalés d'une bande à l'autre et ne forment jamais de grille.
- Les tôles ont des tailles variées et un quart de leurs angles sont chanfreinés. Des rivets suivent les cadres et la lisse basse de chaque tôle.
- Les rivets ne sont pas modélisés dans le modèle de jeu. Des dômes de 2 mm servent seulement à cuire une carte de normales et une carte d'occlusion, puis sont supprimés.
- Ces cartes utilisent une deuxième UV des tôles, `UVDetail` : une île par tôle, sans recouvrement, à 371 px/m. Les îles sont projetées dans le même repère que l'UV de peinture, et les deux UV partagent donc les tangentes.
- Les tôles s'arrêtent à la découpe du pourtour, un polygone convexe autour de la goutte ; elles sont coupées le long des plis, et chaque morceau descend sur sa facette.
- **Renforts des plis :** une bande à cheval sur chaque pli, de la découpe au coin de poupe, 3,5 mm au-dessus des tôles, boulonnée tous les 30 cm.
- Les équipements de peau sont posés chacun dans une seule tôle, sur une seule facette et hors du pourtour, ce que le script vérifie :
  - trappes rivetées à angles chanfreinés et trappes de train à joint large ;
  - bouchons, grilles d'aération et marquages rouges et blancs ;
  - une antenne sur le dos, deux sous la quille.
- La peinture est mate, gris clair et légèrement usée : passé du soleil, coulures discrètes vers l'arrière, rares éclats groupés et rayures.
- Livrée :
  - la plupart des tôles gardent la peinture d'origine ;
  - certaines sont des reprises à peine plus sombres, tirées au hasard ;
  - une bande bleue passée couvre les capots arrière et suit les joints, d'où son bord en escalier ;
  - le nez est bleu-gris, le ventre plus sombre.
- Toutes ces teintes multiplient une même texture, et glTF les exporte en facteur de couleur. La texture fait 1024 × 1024 et couvre 2 m, plaquée à l'échelle du monde sans rupture d'une tôle à l'autre.

**Poupe**

- Un cadre ferme tout le losange arrière, pointes comprises, et dépasse de 4 cm de la peau. Le fond est en retrait de 40 cm : carreaux de céramique, métal bleui en anneaux autour des tuyères, suie qui s'étale vers le bas (`poupe_base.png`).
- Trois tuyères compactes de 35 cm, perpendiculaires au fond, sur brides boulonnées : col usiné, divergent court, lèvre et raidisseur. Deux vérins d'orientation par tuyère.
- Rien ne dépasse du vaisseau : la lèvre des tuyères s'arrête 5 cm en retrait du plan de poupe, et `controle_geometrie.py` le vérifie.
- **Aucun bloc cubique :**
  - un collier galbé autour de chaque bride, tenu par douze goussets ;
  - au-dessus et au-dessous des tuyères, trois conduites sur colliers ronds et pattes ;
  - entre les tuyères, des vérins de cardan : corps, tige sous soufflet, chapes ;
  - deux évents à lames inclinées, dans des cadres en stade aux bouts arrondis.
- Feux de position en lentilles aux pointes : rouge à gauche du pilote, vert à droite.

**Cockpit**

- **Tout part de la bulle.** Les parois de la cuve descendent de son seuil, la goutte posée sur le dessus, évasées de 8 % vers le plancher, jusqu'au plancher ou aux cloisons avant et arrière. Un rail de seuil boulonné fait le tour de la bulle.
- **Le pupitre principal** va d'une paroi à l'autre, incliné de 27° vers l'oeil. Son haut est un arc : au ras du bandeau d'alarmes au milieu, il descend jusqu'au rail sur les côtés. La casquette de l'auvent part de cet arc et suit la bulle jusqu'à son nez. Le collimateur tête haute est dans l'axe de visée.
- **Les ailes et les consoles** suivent chaque paroi avec un même profil : panneau incliné sous le rail, puis tablette à hauteur de coude. Leur haut suit le seuil de la bulle, 2,5 cm sous le rail ; la tablette s'abaisse là où le seuil descend, pour garder la place des plaques.
- **Les épaules du pilote dépassent du seuil,** comme dans un chasseur à bulle ; sa tête garde 41 cm sous la bulle.
- L'équipement est fait de modules standards : plaque sérigraphiée, chant chanfreiné, quatre fixations quart de tour. Interrupteurs, gardes, rotacteurs, disjoncteurs, voyants, clavier et cadrans sont posés aux coordonnées de leurs légendes.
- Le même boîtier d'affichage est monté trois fois : cadre usiné, touches de bord, vis.
- Siège sur glissières, flasques et baquet en tôle, rails de guidage, coffre d'appui-tête et harnais. Baie d'équipements et trappes d'accès vissées derrière le siège et sur les consoles.
- Palette des panneaux de la navette : gris peint, boîtiers noirs, métal brossé, légendes blanches.
- Toutes les faces sont planes. Les pièces rondes sont lissées, les arêtes de plus de 35° restent vives. Gauche et droite sont celles du pilote, qui regarde vers −Y : sa gauche est en +X, côté manette des gaz.

**Détails v3** (`details_v3.py`)

- **La silhouette ne change pas :** rien ne dépasse de plus de quelques centimètres, hors de la sonde de nez.
- **Rien ne fait face à l'écoulement en arête vive :** les tuyères d'attitude sont percées dans la peau, les carénages profilés, les baguettes effilées, les lèvres arrondies (`docs/principes.md`).
- **Dehors, des pièces qui ont une fonction :**
  - volets de bord de fuite à la poupe, dessus et dessous, presque affleurants, avec jeu sombre, carénages d'articulation et déperditeurs d'électricité statique ; ils bougent dans le moteur comme des élevons, par l'attribut `_POSE`, de 3 à 6, et leurs pivots « Pivot | volet … » posés sur la charnière ;
  - deux petites ailettes ventrales en flèche, deux lames le long des chines du nez ;
  - baguettes de bord d'attaque effilées sur les chines, tuyères d'attitude affleurantes à la poupe et au nez, avec bague et auréole de suie, sonde de nez annelée de rouge ;
  - écopes NACA sur le dos et au ventre, trappe de secours de la verrière à liseré rouge et flèche, poignée à trappe poussoir et marchepied encastré sous la chine, chemin antidérapant sur le dos ;
  - feux anticollision rouges sur le dos et sous la quille, sur socle profilé ; feux à éclats blancs sur le cadre de poupe, à côté des feux de position ; bandes de formation vertes au bord des chines ; phares d'atterrissage sous le nez.
- **Chaque pièce tient dans une tôle,** à l'écart des trappes et grilles de `design_v2.py`. Les décalques sont à 12,3 mm de la peau, comme les siens.
- **Dedans :** couples en T sur les parois arrière, lisse, faisceaux de trois câbles bridés tous les 25 cm, poignées de maintien sous les rails, extincteur à droite du pilote, tuyau d'oxygène annelé du siège à la console.
- **Le cœur des trois tuyères** passe au matériau « Jeu | Tuyere chaude », que le moteur règle sur les gaz. Le feu rouge de poupe quitte le « Signal rouge » des voyants du cockpit pour « Jeu | Feu de position rouge » : les feux de position et de formation, vers 0,01 d'émission, gardent leur teinte la nuit et s'effacent de jour (`docs/spec-vaisseau.md`).
- **Les matériaux animés par le moteur** gardent leur nom : `paquet_moteur.py` leur donne un rôle par ce nom (`ROLES`).
- 6 070 triangles de plus.

**Maillage**

- 44 564 triangles, 18 maillages et 90 primitives dans le GLB, 7,7 Mo, 12 images. Le cockpit est fusionné en un seul maillage à l'export, une primitive par matériau ; le combineur et la verrière restent à part.
- Unité Blender : mètre. Environ 9,8 m de long et 6,2 m de large. Dans Blender : avant vers −Y, haut vers +Z. À l'export glTF : avant vers −Z, haut vers +Y.
- Matériaux PBR, verrière transparente et affichages émissifs. La coque utilise une couleur et une rugosité répétables en 1024 × 1024 sur `UVMap`. Les tôles ajoutent une normale de 4096 × 4096 et une occlusion de 2048 × 2048, cuites sur `UVDetail` : `coque_details_normale.png` et `coque_occlusion.png`. Ces textures sont une nouvelle approximation de jeu, pas une cuisson des matériaux procéduraux d'origine.
- Normales et tangentes sont présentes dans chaque primitive. La carte normale est en espace tangent. Rugosité, normale et occlusion sont des données linéaires.
- Le moteur devra lire la deuxième UV : `normalTexture` et `occlusionTexture` des matériaux « Jeu | Tole » portent `texCoord: 1`.

**Intégration**

- L'export a été réimporté et rendu dans Blender. Le moteur le charge par son paquet `vaisseau.vsx` (`docs/spec-vaisseau.md`).
- `controle_geometrie.py` vérifie neuf points de chaque dalle d'écran vus de l'oeil du pilote, le raccord des tôles au pourtour de la bulle, le pied de la bulle sur le dessus creusé et son sommet, le fond de cuve, que rien du cockpit ne dépasse de la bulle ou du dessus, et la position des tuyères dans la poupe. Ce contrôle ne remplace pas une inspection depuis toutes les positions du joueur.
- Le moteur devra importer glTF, gérer les matériaux PBR, la transparence de la verrière et les émissions, puis valider les axes, l'échelle et l'éclairage en vol. Les panaches sont à réaliser séparément.
- **Le manche et la manette des gaz bougent dans le moteur** (`pieces_mobiles.py`) :
  - chaque sommet porte un attribut `_POSE`, exporté dans le GLB : 0 fixe, de 0 à 1 le manche, de 1 à 2 la manette ;
  - le soufflet du manche passe de 0 sur sa bride à 1 en haut, le carter reste fixe ;
  - deux vides, `Pivot | manche` et `Pivot | gaz`, donnent le pivot et l'axe Z de chaque pièce ; ils sont retrouvés sur la géométrie, sans cote recopiée.
- Les écrans sont des éléments statiques. Les cartes ne comprennent ni occlusion ambiante cuite ni niveaux de détail. L'éclairage de scène du cockpit n'est pas exporté : son éclairage en jeu reste à régler dans le moteur.

**Reproduction**

- Exécuter `textures_cockpit.py` avec Python et Pillow, puis ouvrir l'original en arrière-plan avec Blender 5.2 et exécuter `preparer.py` : `blender -b <spaceship.blend d'Antigravity> --python preparer.py`, une minute et demie, cuissons comprises. Le script `design_v2.py` reconstruit la coque et le cockpit ; les textures et le GLB sont enregistrés dans ce dossier. Puis `details_v3.py` et `paquet_moteur.py`.
- Pour modifier un panneau, éditer son module dans `modules_cockpit.py`, puis relancer les deux étapes : la légende et la commande bougent ensemble.
- Après une retouche du manche ou de la manette dans la scène de travail : `blender -b vaisseau_travail.blend --python pieces_mobiles.py`, qui marque, sauve et exporte, puis `python paquet_moteur.py`.
- Les détails v3, sur la scène de travail : `blender -b vaisseau_travail.blend --python details_v3.py`, qui construit, sauve et exporte, puis `python paquet_moteur.py`. Avec `-- --sans-export`, rien n'est sauvé : pour des rendus d'essai.
- `verifier.py` rend les vues de la scène ; `verifier_glb.py` réimporte et rend le GLB ; `controle_geometrie.py` contrôle ses raccords dans la scène de travail. Ces scripts ne nécessitent pas de fenêtre Blender.
