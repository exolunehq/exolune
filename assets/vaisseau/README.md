# Vaisseau triangulaire

**Fichiers**

- `vaisseau_travail.blend` : scène modifiable, pièces du cockpit séparées et textures incluses.
- `vaisseau.glb` : modèle statique glTF 2.0, textures incluses, sans décor ni panaches.
- `vaisseau.vsx` : le paquet lu par le moteur, cuit depuis le GLB par `paquet_moteur.py` (`python paquet_moteur.py`, sans Blender) ; à relancer après chaque export (`docs/spec-vaisseau.md`).
- `pieces_mobiles.py` : marque le manche et la manette des gaz, que le moteur fait tourner, et pose leurs pivots.
- `exporter.py` : l'export du GLB, commun à `preparer.py` et `pieces_mobiles.py`.
- `modules_cockpit.py` : dimensions, commandes et place dans l'atlas de chaque module d'équipement. Source unique de la sérigraphie et de la géométrie.
- `plaques.png` : atlas de sérigraphie des modules, 2048 × 2048.
- `cockpit.png`, `commandes.png`, `pilote.png`, `pupitre.png`, `exterieur.png`, `arriere.png` : rendus de contrôle de la scène Blender. La verrière est masquée sur les vues du cockpit et des commandes.
- `export_controle.png` et `export_pilote.png` : rendus du GLB réimporté dans une scène vide.

**Modèle**

- Reprise du fichier `spaceship.blend` d'Antigravity, conversation « Blender Spaceship 3D Modeling » du 25 octobre 2026. L'original reste intact.
- Silhouette triangulaire d'origine conservée. Coque, poupe et cockpit sont reconstruits par `design_v2.py` ; aucune pièce d'origine ne reste dans le modèle.
- Verrière revenue aux proportions d'origine, composée de deux faces jointives sans arceau central ni traverse. Un joint sombre suit son pourtour.

**Coque**

- Une peau continue ferme le volume, de la pointe au cadre de poupe. Les tôles affleurent toutes à 12 mm au-dessus, séparées par des joints gravés de 4 mm.
- La tôlerie suit la structure. Des sections entre cadres principaux, aux pointes avant et arrière du vitrage, croisent des bandes entre lisses qui convergent vers le nez. Les joints sont décalés d'une bande à l'autre et ne forment jamais de grille.
- Les tôles ont des tailles variées et un quart de leurs angles sont chanfreinés. Des rivets suivent les cadres et la lisse basse de chaque tôle.
- Les rivets ne sont pas modélisés dans le modèle de jeu. Des dômes de 2 mm servent seulement à cuire une carte de normales et une carte d'occlusion, puis sont supprimés.
- Ces cartes utilisent une deuxième UV des tôles, `UVDetail` : une île par tôle, sans recouvrement, à 371 px/m. Les îles sont projetées dans le même repère que l'UV de peinture, et les deux UV partagent donc les tangentes.
- Les équipements de peau sont posés chacun dans une seule tôle, ce que le script vérifie :
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

- Un cadre ferme tout le losange arrière, pointes comprises, et dépasse de 4 cm de la peau. Le fond est en retrait de 40 cm et peint, pour rester lisible à l'ombre.
- Trois tuyères compactes de 35 cm, perpendiculaires au fond, sur brides boulonnées : col usiné, divergent court, lèvre et raidisseur. Deux vérins d'orientation par tuyère.
- Rien ne dépasse du vaisseau : la lèvre des tuyères s'arrête 5 cm en retrait du plan de poupe, et `controle_geometrie.py` le vérifie.
- Longerons au-dessus et au-dessous des tuyères, raidisseurs entre elles, deux caissons de ventilation.
- Feux de position aux pointes : rouge à gauche du pilote, vert à droite.

**Cockpit**

- Tout part de la verrière. Les parois de la cuve sont des plans qui passent par ses arêtes, évasés de 8 % vers le plancher. Un rail de seuil boulonné suit chaque arête, les deux rails se rejoignent en onglet aux pointes.
- L'auvent est posé dans le plan du seuil, de la pointe avant du vitrage au pupitre. Le collimateur tête haute est dans l'axe de visée.
- Le pupitre principal va d'une paroi à l'autre, incliné de 27° vers l'oeil. Les ailes et les consoles suivent chaque paroi avec un même profil : panneau incliné sous le rail, puis tablette à hauteur de coude.
- L'équipement est fait de modules standards : plaque sérigraphiée, chant chanfreiné, quatre fixations quart de tour. Interrupteurs, gardes, rotacteurs, disjoncteurs, voyants, clavier et cadrans sont posés aux coordonnées de leurs légendes.
- Le même boîtier d'affichage est monté trois fois : cadre usiné, touches de bord, vis.
- Siège sur glissières, flasques et baquet en tôle, rails de guidage, coffre d'appui-tête et harnais. Baie d'équipements et trappes d'accès vissées derrière le siège et sur les consoles.
- Palette des panneaux de la navette : gris peint, boîtiers noirs, métal brossé, légendes blanches.
- Toutes les faces sont planes. Les pièces rondes sont lissées, les arêtes de plus de 35° restent vives. Gauche et droite sont celles du pilote, qui regarde vers −Y : sa gauche est en +X, côté manette des gaz.

**Maillage**

- 21 237 triangles, 11 maillages et 60 primitives dans le GLB, 4,8 Mo. Le cockpit est fusionné en un seul maillage à l'export, une primitive par matériau ; le combineur et la verrière restent à part.
- Unité Blender : mètre. Environ 9,8 m de long et 6,2 m de large. Dans Blender : avant vers −Y, haut vers +Z. À l'export glTF : avant vers −Z, haut vers +Y.
- Matériaux PBR, verrière transparente et affichages émissifs. La coque utilise une couleur et une rugosité répétables en 1024 × 1024 sur `UVMap`. Les tôles ajoutent une normale de 4096 × 4096 et une occlusion de 2048 × 2048, cuites sur `UVDetail` : `coque_details_normale.png` et `coque_occlusion.png`. Ces textures sont une nouvelle approximation de jeu, pas une cuisson des matériaux procéduraux d'origine.
- Normales et tangentes sont présentes dans chaque primitive. La carte normale est en espace tangent. Rugosité, normale et occlusion sont des données linéaires.
- Le moteur devra lire la deuxième UV : `normalTexture` et `occlusionTexture` des matériaux « Jeu | Tole » portent `texCoord: 1`.

**Intégration**

- L'export a été réimporté et rendu dans Blender. Le moteur le charge par son paquet `vaisseau.vsx` (`docs/spec-vaisseau.md`).
- `controle_geometrie.py` compare les coins de la verrière au modèle original, puis vérifie neuf points de chaque dalle d'écran vus de l'oeil du pilote, le raccord des plaques, le fond de cuve, la position des éléments sous le vitrage et celle des tuyères dans la poupe. La suppression des traverses et du retrait du vitrage crée un écart maximal de 1,7 cm aux coins de référence. Ce contrôle ne remplace pas une inspection depuis toutes les positions du joueur.
- Le moteur devra importer glTF, gérer les matériaux PBR, la transparence de la verrière et les émissions, puis valider les axes, l'échelle et l'éclairage en vol. Les panaches sont à réaliser séparément.
- **Le manche et la manette des gaz bougent dans le moteur** (`pieces_mobiles.py`) :
  - chaque sommet porte un attribut `_POSE`, exporté dans le GLB : 0 fixe, de 0 à 1 le manche, de 1 à 2 la manette ;
  - le soufflet du manche passe de 0 sur sa bride à 1 en haut, le carter reste fixe ;
  - deux vides, `Pivot | manche` et `Pivot | gaz`, donnent le pivot et l'axe Z de chaque pièce ; ils sont retrouvés sur la géométrie, sans cote recopiée.
- Les écrans sont des éléments statiques. Les cartes ne comprennent ni occlusion ambiante cuite ni niveaux de détail. L'éclairage de scène du cockpit n'est pas exporté : son éclairage en jeu reste à régler dans le moteur.

**Reproduction**

- Exécuter `textures_cockpit.py` avec Python et Pillow, puis ouvrir l'original en arrière-plan avec Blender 5.2 et exécuter `preparer.py`. Le script `design_v2.py` reconstruit la coque et le cockpit ; les textures et le GLB sont enregistrés dans ce dossier.
- Pour modifier un panneau, éditer son module dans `modules_cockpit.py`, puis relancer les deux étapes : la légende et la commande bougent ensemble.
- Après une retouche du manche ou de la manette dans la scène de travail : `blender -b vaisseau_travail.blend --python pieces_mobiles.py`, qui marque, sauve et exporte, puis `python paquet_moteur.py`.
- `verifier.py` rend les vues de la scène ; `verifier_glb.py` réimporte et rend le GLB ; `controle_geometrie.py` contrôle ses raccords dans la scène de travail. Ces scripts ne nécessitent pas de fenêtre Blender.
