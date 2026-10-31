# Le chasseur

**Le vaisseau du joueur, d'après le concept de l'utilisateur.** Sa vue de trois quarts est la cible artistique ; les vues de dessus, de profil et d'arrière n'ont servi qu'où elles s'accordent avec elle. Forme validée sur maquettes le 2026-10-31, puis détaillée.

**Fichiers**

- `forme_chasseur.py` : la forme, seule source de la géométrie, sans Blender. Coque en sections, bulle, aile et élevons, prises d'air, capots, tuyères, œil du pilote. `python forme_chasseur.py` contrôle les raccords.
- `textures_chasseur.py` : l'atlas de la coque, 4096², en numpy (`python textures_chasseur.py`, 40 s). Couleur, normale, occlusion, métal-rugosité : `chasseur_*.png`.
- `design_chasseur.py` : le modèle dans Blender, ses rendus de contrôle et l'export.
- `cockpit_chasseur.py` : le cockpit, appelé par `design_chasseur.py`.
- `modules_cockpit.py` et `textures_cockpit.py` : les plaques sérigraphiées (`plaques.png`), les écrans et les cadrans (`ecran_*.png`, `jauge_*.png`).
- `pieces_mobiles.py` : marque le manche et la manette des gaz, pose leurs pivots.
- `exporter.py`, `paquet_moteur.py` : le GLB, puis le paquet `vaisseau.vsx` lu par le moteur (`docs/spec-vaisseau.md`).
- `vaisseau_travail.blend`, `vaisseau.glb`, `vaisseau.vsx` : la scène, le modèle, le paquet.
- `exterieur.png`, `arriere.png`, `dessous.png`, `pilote.png`, `cockpit.png`, `siege.png`, `commandes.png` : rendus de contrôle ; `export_controle.png` et `export_pilote.png` : le GLB réimporté (`verifier_glb.py`).
- **La forme N est archivée** dans `archive/forme-n/`, avec ses scripts et ses textures.
- **Le moteur recopie la bulle et les tuyères** (`Ship.hlsli`, `ShipPlume.hlsli`) : à reporter après tout changement de `forme_chasseur.py`.

**Coque**

- **Une seule grande arête court de la pointe à la poupe :** la chine, au bas de la bande orange, sous la bulle, au haut de la prise d'air, puis en arête d'épaule jusqu'au capot moteur.
- **Derrière la bulle, deux arêtes de plus,** relevées sur les traits de l'utilisateur à la caméra du trois-quarts :
  - la ligne haute quitte l'arceau et rejoint l'arête du dos ;
  - la diagonale monte du coin bas de la bulle vers elle ;
  - entre elles, le dos bombé, un pan raide de 48 à 57° et la terrasse, qui porte la bande bleue.
- **Sous la chine,** le flanc, puis la chine basse, qui file au bord d'attaque de l'aile, le chanfrein bas et le ventre plat.
- **La pointe :** un chanfrein tout autour, un cadre de tôle claire, la fenêtre du capteur en retrait de 3 cm.
- **La peinture suit les pans :** tôles décalées d'une bande à l'autre, trappes, grilles ; bande orange du chanfrein, panneaux bleus, bande bleue de la terrasse, ventre plus sombre.
- **Autour du verre, une bande anthracite de 5,5 cm.** L'orange ne passe pas devant la bulle : au coin, le chanfrein orange se resserre et file en bande de queue, d'un seul tenant.
- **Le raccord du verre :** les sommets de peau sous le verre vont sur son bord, à sa hauteur ; la peau s'arrête net sur le contour. Le cadre tubulaire, 1,2 cm au-delà du bord, couvre le raccord.
- **L'usure, d'après le concept :** têtes de rivet sombres et rouillées, auréolées de rouille ; crasse brune au bord des joints, voile de poussière ; éclats, rayures, coulures, suie de poupe. Un seul matériau, « Jeu | Tole », sur la deuxième UV, `UVDetail`.
- **Les pièces :** bulle et son cadre, aile à nervure, quatre élevons, deux prises d'air à lames, quatre capots et quatre tuyères à foyer chaud, feux, dix jets d'attitude, antennes, écopes.
- **L'équipement de peau,** petites pièces qui ont une fonction, profilées :
  - trappes de train sous le ventre et trappes d'accès sur les flancs et le pont du nez, en relief de 3 mm sur un joint sombre, vissées ;
  - deux aérofreins sur le dos, qui épousent la peau, charnière à l'avant ;
  - deux bouches auxiliaires sur le dos, ouïes sur les capots moteurs ;
  - deux ailettes ventrales déversées, deux lames le long de la chine basse du nez, une cloison sur chaque aile entre les élevons ;
  - carénages d'articulation sous les élevons, sondes d'incidence à la pointe, déperditeurs au bout des ailes, feux de formation verts.

**Cockpit**

- **La verrière est dégagée :** tout l'équipement reste sous le seuil du verre, sauf le haut du pupitre, 5 cm au-dessus et sous la ligne qui rase le nez de la bulle.
- **Un assemblage sans jour :** le pupitre va de paroi à paroi, ses coins sur le seuil ; les consoles partent de son plan, montent au seuil et finissent dans la cloison arrière ; le pont antireflet s'appuie sur le bord du verre ; la cloison et sa tablette ferment l'arrière, jusqu'à la paroi qui monte vers l'arceau.
- **Le pupitre :** trois écrans dans leur boîtier usiné, le bandeau d'alarmes. Un pont antireflet le prolonge jusqu'au nez de la bulle.
- **Les consoles,** le long de chaque paroi : un pan incliné, qui porte l'aile d'instruments et deux plaques, puis une tablette à hauteur de coude, avec deux plaques. Les commandes sont posées sur leurs légendes.
- **Les plaques du pan incliné sont montées sur un socle** qui descend jusqu'au pan : il n'est pas plan le long de la paroi, une plaque plane s'y enfonçait par un bout. Deux petites plaques, LIGHTS et FUEL, sur les côtés du pupitre, au-dessus des consoles.
- **Les grandes faces du cockpit portent leur tôlerie,** dans une région de l'atlas de la coque (`textures_chasseur.INTERIEUR`) : panneaux de 30 × 20 cm décalés, joints fins, vis aux coins, sans rouille ni crasse.
- **Le siège baquet, d'après le concept :** dossier et assise à bourrelets ronds, coussins capitonnés, appui-tête rembourré. Coque basse de graphite sur glissières, rails d'éjection, coffre du parachute, harnais à réglages de cuir fauve.
- **Les commandes :** palonnier, manche entre les genoux, manette des gaz sur la tablette gauche. Le manche et la manette bougent dans le moteur, par l'attribut `_POSE` et leurs pivots.
- **L'œil est à 1,03 m,** en d 4,40 ; l'appui-tête est juste derrière le casque.

**Maillage**

- **29 555 triangles,** 16 maillages, 46 tracés, 10 images ; GLB et paquet de 8 Mo.
- **Allégé de 35 000 :**
  - anneaux de coque serrés là où la forme tourne vite, lâches ailleurs ;
  - sections à 22 points sur le dessus ;
  - verrière, cadre et tuyères moins découpés.
- **Le cockpit fait environ 10 000 triangles, l'équipement de peau 2 200.** Il est fusionné en un seul maillage à l'export, une primitive par matériau ; la verrière reste à part.
- **Repère :** nez vers −Y, haut +Z, gauche du pilote +X, en mètres ; d est la distance à la pointe du nez.

**Reproduction**

- `python textures_chasseur.py`, puis `blender -b --factory-startup --python design_chasseur.py`, puis `python paquet_moteur.py`.
- `-- --sans-export` n'écrit rien dans ce dossier ; `-- --rendus DOSSIER` fait les vues de contrôle. `RENDU_VUES` les choisit, `RENDU_SPP` règle les échantillons.
- Pour changer une plaque, éditer son module dans `modules_cockpit.py`, puis `python textures_cockpit.py`.
