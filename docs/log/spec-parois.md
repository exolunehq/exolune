# Spécification : les parois rocheuses, procédural ou hybride

**Au log :** les gradins, options 1 et 2, désactivés le 2026-10-23, leur code retiré le 2026-10-30, `WALL_RELIEF` compris. Ils restent au tag `piste/parois-gradins`.

Statut : options 1 et 2 essayées le 2026-10-23, à juger en vol. Résultats en fin de fichier.

## Le constat

Les parois verticales ne sont pas convaincantes, de 15 à 150 m : des surfaces lisses drapées comme un tissu, rayées de bandes de couleur. Pas de blocs, pas de surplombs, pas de marches dans la géométrie, pas de cônes d'éboulis.

## Ce que la comparaison a montré

**Le procédural et l'hybride à l'essai,** avec le scan `dark_rock_02` à la place de la roche de 8 m, sur cinq parois (`spec-hybride-scans.md`, planches de cette spec) :
- **à moins de 10 m,** le scan donne des fissures plus fines, sur la roche rouge ;
- **de 15 à 150 m, rien ne change.**

**Le défaut n'est donc pas la matière de près, mais l'échelle de 2 à 100 m, et c'est de la géométrie :**
- **un champ de hauteur n'a qu'une hauteur par colonne :** pas de surplomb, une silhouette lisse ;
- **une paroi verticale n'a que deux ou trois sommets en hauteur :** les triangles s'étirent ;
- **nos strates sont des bandes de couleur et un relief de matériau d'un à deux mètres,** sur un relief complexplanet lisse à ces échelles.

**Une photo n'y peut rien seule :** les scans libres font 2 m de large ; des photos de falaises de 10 à 100 m sont rares sous licence libre, et une paroi verticale sur un champ de hauteur les étirerait.

## Ce que font les autres

- **Les jeux livrés posent des objets de roche sur le terrain :** kits de photogrammétrie ou Megascans, raccordés au sol par les normales et un tramage de profondeur. Placement par règles de pente et de courbure, souvent sur le GPU : [Horizon Zero Dawn](https://www.guerrilla-games.com/media/News/Files/GDC2017_VanMuijden_GPUBasedProceduralPlacementInHorizonZeroDawn.pdf), [Ghost Recon Wildlands](https://80.lv/articles/procedural-technology-in-ghost-recon-wildlands/), [Far Cry 5](https://80.lv/articles/houdini-procedural-world-generation-of-far-cry-5/), [Star Citizen](https://starcitizen.tools/Planet_Tech_v5).
- **[Outerra](https://www.gamedeveloper.com/programming/horizontal-fractal-displacement) déplace les sommets raides à l'horizontale,** dans le sens de la pente, par un bruit fractal : la roche bombe ou se creuse.
- **La recherche :** [déplacement triplanaire, Weiss et al. 2020](https://cs.cit.tum.de/cg/research/publications/2020/triplanar-displacement-mapping) ; [falaises stratifiées implicites, Paris et al. 2019](https://perso.liris.cnrs.fr/aparis/public_html/projects/paris2019_3D.html) ; [blocs de fracture, Paris et al. 2020](https://hal.archives-ouvertes.fr/hal-02926218).
- **Écartés pour nous :** voxels et marching cubes à chaque image, trop chers ; érosion simulée, qui demande un état stocké ; parallaxe seule, qui ne change pas la silhouette.

## Les options

**1. Les falaises géologiques, dans le relief lui-même.** La géologie fait les parois : les bancs durs tiennent en falaise, les bancs tendres s'effondrent en talus, d'où les profils en gradins.
- **La colonne stratigraphique existe déjà,** par sommet ; ses formations de 10 à 60 m deviennent des gradins du relief, dans le calcul du maillage, sur les pentes raides.
- **La silhouette se casse par vraies marches,** et les strates ne sont plus des bandes peintes : elles sont la forme.
- **Universel :** toute roche litée de la planète, à toute distance, filtré comme le reste du relief.

**2. Le déplacement horizontal des sommets raides.** Dans la direction de la pente, par un bruit de blocs et de fractures : la paroi bombe, se creuse, prend des contreforts et de faux surplombs.
- **Peu coûteux :** quelques octaves sur les seuls sommets raides.
- **Les pièges connus :** recalculer les normales sur les positions déplacées, et le tremblement d'un relief porté par le maillage, que nos règles encadrent déjà (`principes.md`).

**3. Des rochers semés en vrais volumes.** Blocs, piliers et éboulis, instanciés sur le GPU par un hachage au-dessus d'un seuil de pente, raccordés au sol.
- **Le seul vrai volume 3D,** avec surplombs et ombres.
- **Le plus cher** en calcul et en code : un nouveau pipeline.

**4. L'hybride pour la matière des parois.** Des scans de falaise sur la tuile de 8 m.
- **Après la géométrie seulement :** seul, il ne change que les fissures à moins de 10 m.

## Recommandation

**Les options 1 et 2 ensemble, puis 3.**
- Elles s'attaquent à la cause, la géométrie, au lieu de la peinture.
- Elles restent dans le concept, tout recalculé à chaque image, sans mémoire.
- L'option 1 relie ce qu'on voit de loin, les strates, à ce qu'on voit de près, les gradins : la même structure à toutes les échelles.
- L'hybride de la matière reste ouvert ensuite, comme couche de détail.

**La mesure :** les vues de parois de cette spec, à 15, 50 et 150 m, à côté des photos `cible-*.jpg` ; les bancs de tremblement, de descente et des crêtes ; le coût du calcul du maillage.

## Résultats des options 1 et 2

**Ce qui est en place :**
- **Option 1, les gradins :** chaque banc dur de la colonne stratigraphique fait une falaise sur le tiers bas de sa hauteur, `WALL_CLIFF`, puis un replat. Le relief passe par la hauteur : le sol reste un champ de hauteur.
- **Les replats reposent à l'angle d'éboulis,** 34°, `WALL_REPOSE` ; les falaises prennent le reste de la montée. Une paroi pas plus raide que ses éboulis n'a pas de gradins ; plus elle est raide, plus ils sont marqués.
- **Le partage :** le maillage porte les gradins arrondis sur 16 mailles, les pixels éclairent le reste. De près, les gradins sont dans la silhouette ; de loin, dans la lumière seulement.
- **Option 2 :** ravines et contreforts par un bruit étiré à la verticale, masses arrondies du granite, dans le maillage, jusqu'aux mailles de 16 m. Sans tremblement mesurable.

**Ce qui a été écarté :**
- **Le déplacement horizontal d'Outerra :** sur un champ de hauteur, les sommets déplacés se replient. Trous noirs, dents de scie.
- **Les gradins nets dans le maillage seul :** le meilleur rendu, mais 2,5 fois plus de tremblement. Arrondis sur 16 mailles, ils ne se voient presque plus.
- **Des replats plats :** chaque pente raide devenait un escalier zébré, de loin surtout.
- **Un défaut corrigé en route :** la pente ajoutée dans la lumière doit être multipliée par la composante verticale de la normale. Sans cela, les replats penchaient en arrière et passaient au noir.

**Mesures,** tremblement avec et sans lissage, base puis parois :
- paroi très raide, `1391.1 -11.04542 50.06777 2.6 55.3` : 0,37 / 2,47 → 0,61 / 5,05 ;
- montagne à 45°, `3756.3 -39.55694 12.77814 -13.1 -141.1` : 0,19 / 1,54 → 0,22 / 1,67 ;
- corniche, `2182.0 31.16045 8.58814 1.9 -17.1` : 0,18 / 1,12 → 0,21 / 1,23 ;
- montagnes à 5 km, `4657 -14.9635 119.991 10` : 0,11 / 0,61 → 0,16 / 0,73.
- **Descente de la roche :** inchangée de 800 à 8 km.
- **Coût :** +0,2 ms de rendu sur la paroi raide, +0,2 ms de calcul à la corniche.

**Le tremblement restant,** sur les parois très raides :
- **Écartés comme cause :** l'arrondi des arêtes au pixel, la normale utilisée, la part du maillage, la taille des mailles, l'altitude fine du pixel. Aucun ne le réduit.
- **En partie :** les replats éclairés rendent cette paroi plus claire de 36 %, et l'écart entre deux images croît avec la clarté.
- **Piste suivante :** la hauteur `s` des gradins, interpolée entre les sommets qui glissent.

**Réglages :** `WALL_RELIEF` 1, 0 désactive tout ; `WALL_MAX_CELL` 16 m ; `WALL_SLOPE` 0,55 à 1 ; `WALL_CLIFF` 0,35 ; `WALL_REPOSE` 0,67.

**Suite :** de 100 m à 1 km, le rendu reste rectiligne, « tissu ». La méthode est revue dans `spec-parois-minerales.md`.
