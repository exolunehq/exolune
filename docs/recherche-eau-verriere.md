# L'eau sur la verrière

**Le but :** de l'eau réaliste et belle sur la verrière du vaisseau. Elle se pose en nuage et sous la pluie, se rassemble, coule, et l'air la chasse. Pas de gouttes dessinées avec des traînées rectilignes.

**L'état, 2026-10-29 :** les gouttes simulées sont en place, à juger en vol.
- **Les gouttes :** `ShipWater.hlsli`, trois passes de calcul par image (`ShipWaterMove`, `ShipWaterClear`, `ShipWaterSplat`), 8 192 au plus.
- **Le rendu :** dans `ShipGlass.hlsl`, gouttes et traînées qui sèchent en se morcelant.
- **Les fines perles d'une texture préparée sont retirées :** elles faisaient un grain qui ne ressemblait pas à de l'eau.
- **Le séchage, réglé le 2026-10-29 :**
  - **L'air est celui de l'altitude :** la vitesse passée au verre est ramenée au niveau de la mer, comme la pression dynamique. Dans l'espace, l'air ne pousse plus les gouttes.
  - **Les gouttes que l'air ne peut chasser,** sous 0,5 mm, sèchent en une minute en air calme et en sept secondes environ en air rapide. Avant, il leur fallait plus d'une heure.
  - **Au-dessus de 20 à 35 km, l'eau bout :** gouttes et traînées partent en deux ou trois secondes.
- **Le coût ne se mesure pas :** dans le bruit, de 4 à 7 ms par image en 1080p selon la vue.
- **La mémoire :** la carte et la pellicule prennent 46 Mo.

## Le constat, 2026-10-29

- **Le modèle actuel est procédural** (`ShipGlass.hlsl`) : des perles et des filets tirés d'une grille de hachage, déplacés d'un bloc par colonne.
  - Rien ne persiste : une goutte n'a pas d'histoire, ne fusionne pas et ne laisse pas d'eau derrière elle.
  - Le mouvement est rectiligne et régulier. D'où les « clous » à grande vitesse.
- **Pas de gouttes en traversant un nuage, en vol.** Trois causes se cumulent :
  - **Le séchage est trop rapide :** à 500 m/s, l'air sèche le verre en une demi-seconde. Au bord d'un nuage, la densité faible ne mouille presque pas.
  - **Les perles disparaissent :** au-dessus de 15 m/s, elles tombent au quart.
  - **Les filets vont trop vite :** à 5 m/s, ils sautent d'une cellule entière à chaque image. Ils ne se voient plus.
- **On repart donc de zéro,** sur une simulation de l'eau.

## L'état de l'art

- **ToyShop, ATI 2006** ([Tatarchuk, chapitre 3.8](https://advances.realtimerendering.com/s2006/Chapter3-Artist-Directable_Real-Time_Rain_Rendering_in_City_Environments.pdf)), d'après [Kaneda 1999](https://home.hiroshima-u.ac.jp/kin/publications/JVCA/index.html).
  - **Une grille de cellules sur la vitre,** dans une texture 16 bits RGBA : masse d'eau, vitesse x et y, passage d'une goutte ; plus la masse et l'affinité.
  - **Les forces :** la gravité selon la masse, contre les frottements statique et dynamique. Ces frottements varient sur la vitre, par une carte.
  - **Le trajet :** une goutte passe à l'une des trois cellules en aval. Le tirage est biaisé par sa vitesse, l'affinité et la mouillure de la cellule visée. Les gouttes préfèrent le mouillé, d'où les méandres et le suivi des traces.
  - **Le rendu :** la masse donne une carte de normales. Celle-ci déplace l'image de la scène pour la réfraction et la réflexion. Une goutte lourde jette une ombre avec une pseudo-caustique.
- **X-Plane 12** ([guide développeur](https://developer.x-plane.com/article/windshield-rain-effects/)).
  - **Gouttes simulées en 3D :** vitesse, direction et quantité de mouvement, sous la gravité et les forces aérodynamiques. Elles sont déplacées sur une texture 2D, une île d'UV par vitre.
  - **Une goutte meurt en sortant de son île.**
  - **Le frottement règle les traînées :** moins de frottement, moins de traînées.
- **Particules et carte de hauteur :**
  - [Stuppacher 2007](https://old.cescg.org/CESCG-2007/papers/Hagenberg-Stuppacher-Ines/index.htm) garde l'eau dans une carte de hauteur sur le GPU. Il la floute, en tire des normales et l'éclaire par Fresnel.
  - Chen, Chen et Wong 2013 (cités dans la [revue de 2024](https://arxiv.org/pdf/2411.15880)) mêlent particules et carte de hauteur : fusion des gouttes et formation de filets.
  - Une [thèse d'Umeå, 2021](https://www.diva-portal.org/smash/get/diva2:1571363/FULLTEXT01.pdf), simule les gouttes d'un pare-brise par compute shader, puis les rend dans une texture 2D qui déforme le fond. Gravité, vent, essuie-glace, et les gouttes entre elles. Le document n'a pas pu être lu en entier.
- **La physique de l'eau en vol,** d'après les études de givrage, par exemple [Leng et al.](https://uhra.herts.ac.uk/id/eprint/14127/1/Leng_et_al_water_film_accepted_manuscript.pdf) :
  - **En nuage :** les gouttelettes captées se rassemblent en un film mince, poussé vers l'aval par le cisaillement de l'air.
  - **Sous une épaisseur critique,** la tension de surface brise le film en filets.
  - **Plus l'air va vite,** plus les filets naissent tôt et courent vite, plus ils sont étroits et serrés.
  - **Les gouttes d'un nuage sont minuscules :** quelques dizaines de microns. On ne les voit pas une à une : on voit l'eau qu'elles forment sur le verre.

## Ce qu'on retient

- **Une simulation, pas un motif :** l'eau de la verrière est un état persistant. Elle tombe, se rassemble, coule et part.
- **L'hybride particules et carte de hauteur,** le choix commun de la thèse, de Chen 2013 et de X-Plane :
  - **les gouttes visibles sont des particules,** avec masse, vitesse et frottement. Petites, elles restent collées ; grosses, ou poussées par l'air, elles partent ;
  - **une carte de hauteur dans l'espace de la vitre** reçoit les gouttes chaque image, et garde l'eau qu'elles laissent : leurs traces, que la suivante préfère ;
  - **le rendu se lit dans cette carte :** normale, réfraction de la scène, Fresnel, éclat du ciel. Le verre ne dessine plus de goutte lui-même.
- **Le nuage mouille par un film, puis des filets :** la capture suit la densité et la vitesse. Le film se brise en filets d'autant plus fins et rapides que l'air va vite.

## Le plan

1. **La carte de l'eau :**
   - deux textures dans le plan du vaisseau, qui couvrent les deux vitres, 1,9 × 4,4 m, à 1,2 mm le texel ;
   - la carte, en R32_UINT : la hauteur d'eau et le numéro de la goutte la plus haute, pour les fusions ;
   - la pellicule, en R32_FLOAT : l'eau laissée sur le passage des gouttes ;
   - la vitre est plane, faite de deux triangles : pas d'UV à créer, le plan du vaisseau suffit.
2. **Les gouttes en particules** (`ShipWater.hlsli`, compilé en calcul par `ShipWaterMove.hlsl`, `ShipWaterSplat.hlsl` et `ShipWaterClear.hlsl`), quelques milliers dans un tampon :
   - **Naissance :** à la pluie, en impacts ; en nuage, par la capture du film, qui se rassemble en gouttes. Ces gouttes grossissent ensuite d'un demi-millimètre par seconde, jusqu'à couler.
   - **Forces :**
     - la gravité dans le plan de la vitre ;
     - la traînée de l'air, vers l'arrière, en carré de la vitesse ; la goutte baigne dans la couche limite, où l'air ne va qu'au dixième de la vitesse du vaisseau ;
     - un seuil de frottement statique, croissant pour les petites gouttes ;
     - l'attrait du mouillé, pour les méandres ;
     - un bruit de surface, pour qu'aucune trajectoire ne soit droite.
   - **Fusion :** deux gouttes qui se touchent n'en font qu'une, par une grille de hachage.
   - **Mort :** sortie de la vitre, ou évaporation. Le séchage est réglé sur la durée d'un vol, pas d'une image.
3. **Le dépôt :**
   - chaque goutte écrit sa calotte dans la carte, et laisse une fine pellicule sur son passage ;
   - la carte s'efface lentement, plus vite dans l'air rapide.
4. **Le rendu dans `ShipGlass.hlsl` :**
   - normale tirée de la carte, lissée ;
   - réfraction de la scène par cette normale ;
   - Fresnel et croissant de ciel ;
   - la pellicule floute à peine la vue.
5. **Vérifier :**
   - **en vol :** entrer dans un nuage et en sortir, à 30, 150 et 500 m/s ; pluie sous un cumulus ; arrêt au sol ;
   - **en capture :** une suite d'images, pas une image seule.

**Le givre reste tel quel.** **La buée est retirée** : un voile sur tout le verre brouillait la vue sans rien montrer du temps.
