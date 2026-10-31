# Le vaisseau du joueur

**Le joueur pilote un vaisseau, vu de son cockpit ou de derrière.** La caméra libre reste disponible pour les bancs et la mise au point.

**Essayer, dans le jeu (`AGENTS.md`, `lancement.md`) :** depuis la racine du worktree,
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Parcours tools\tests\2026-10-29-vaisseau.txt
```
après `tools\lance.ps1 -Build -NoLaunch` si le code a changé.

## Le modèle dans le moteur

- **La source est `assets/vaisseau/vaisseau.glb`** (`assets/vaisseau/README.md`).
- **Le modèle est le chasseur du concept de l'utilisateur** (`assets/vaisseau/forme_chasseur.py`, `design_chasseur.py`, `cockpit_chasseur.py`) : coque à arêtes vives sous une bulle, atlas unique, équipement de peau, cockpit dégagé sous le seuil du verre, 29 555 triangles.
- **`Ship.hlsli` recopie la bulle du chasseur** (`assets/vaisseau/forme_chasseur.py`), pour l'eau et le givre : son contour en plan, nez émoussé puis queue ronde, et sa section ronde ; la hauteur du pont et de la couronne, échantillonnée tous les 1/32 de sa longueur (`CanopyZ`, `CanopyInside`, `CanopyNormal`). `ShipPlume.hlsli` recopie ses quatre tuyères et ses dix jets. Les deux doivent rester d'accord avec le modèle.
- **L'œil du pilote est à 1,03 m** (`kEyeUp`), en d 4,40, comme `forme_chasseur.OEIL`.
- **Le moteur lit un paquet cuit, `vaisseau.vsx`,** écrit par `assets/vaisseau/paquet_moteur.py` :
  - nœuds aplatis et sommets entrelacés ;
  - plages de dessin, opaques d'abord ;
  - matériaux PBR, chacun avec son rôle : ce que le moteur anime, écrans, cœur des tuyères, feux (`ROLES`) ;
  - images PNG décodées par WIC.
- **Le paquet est en version 3 :** le rôle allonge chaque matériau à 96 octets. `paquet_moteur.py` vérifie que chaque rôle y est ; un nom de matériau changé dans Blender le fait échouer.
- **Il n'y a ni lecteur JSON ni glTF dans le moteur.** Il faut relancer le script après chaque export du GLB.
- **`Ship::Load` cherche le paquet** dans le premier dossier au-dessus de l'exécutable. Sans paquet, le vaisseau reste absent et la caméra libre seule reste.
- **Repère du vaisseau, celui de Blender :** nez vers −Y, haut +Z, gauche du pilote +X, en mètres.
- **Le repère de la planète est gaucher** (est × nord = bas). `Cross(haut, avant)` y est la droite, comme pour la caméra. Le passage de l'un à l'autre est une symétrie : l'axe X du vaisseau va vers sa gauche, et la bitangente de glTF change de signe.
- **Le manche et la manette des gaz restent mobiles :**
  - chaque sommet du paquet porte sa pose, l'attribut `_POSE` de `assets/vaisseau/pieces_mobiles.py` ;
  - le paquet garde aussi leurs deux pivots, point et axe ;
  - `ShipPose` (`Ship.hlsli`) applique à leurs sommets une matrice de `Ship::Constants::pose`, dans la passe de scène comme dans les ombres ;
  - `D3DApp::UpdateShipFrame` remplit ces matrices, en un seul endroit.
- **Les quatre élevons bougent aussi** (`assets/vaisseau/design_chasseur.py`) :
  - leur pose va de 3 à 6, intérieur gauche, intérieur droit, extérieur gauche, extérieur droit ; leurs pivots, sur la charnière, suivent ceux du manche et de la manette dans le paquet, six en tout ;
  - de chaque côté, le tangage et le roulis se mêlent, lus sur la rotation du vaisseau, donc adoucis en un dixième de seconde ;
  - bord de fuite vers le haut pour cabrer, et du côté où le vaisseau s'incline ; dans les deux sens, 20° au plus.

## Le rendu (`Ship.h`, `Ship*.hlsl`)

- **Ses propres cartes d'ombre, 2048², sur une sphère de 6,7 m :**
  - une vers le soleil, pour les ombres portées dans le cockpit ;
  - une d'en haut, pour le ciel que la coque cache.
- **Les surfaces opaques sont dessinées en premier dans la passe de scène :**
  - Lambert et GGX ;
  - soleil à travers l'air et ciel entier, comme les objets proches ;
  - **le reflet du ciel suit la direction réfléchie,** comme sur la verrière : plus clair vers l'horizon, le sol dessous. Le métal nu et les tuyères le montrent ; une surface rugueuse le fond dans la lumière du ciel, et il s'éteint sous la coque avec le ciel ;
  - l'occlusion cuite sur la deuxième UV des tôles.
- **Les feux s'animent par leur rôle** (`ShipPixel.hlsl`, `SHIP_ROLE_…`) :
  - le cœur des quatre tuyères suit les gaz, de 4 % gaz coupés à plein au trentième cran ;
  - les feux à éclats blancs, aux pointes de la poupe : double éclat toutes les 1,3 s ;
  - les feux anticollision rouges, sur le dos et sous la quille : une pulsation à 0,8 Hz, l'un après l'autre ;
  - les feux de position et de formation restent fixes ;
  - **leur intensité :** 1 vaut un blanc au soleil. La nuit, l'exposition vaut environ 130 fois celle de midi, et la courbe du film blanchit ce qui la dépasse ;
  - **les feux de position et de formation,** vers 0,01, restent rouges et verts la nuit et s'effacent en plein jour, comme les vrais ;
  - **les éclats et les feux anticollision** se voient de jour ; la nuit, ils blanchissent, comme le cœur des tuyères.
- **La part directe du soleil va dans la seconde cible :** les nuages ombrent le vaisseau comme le sol.
- **La verrière est dessinée dans une couche à part, après l'atmosphère.** Le tone map l'applique après le lissage temporel : écran = lissé × alpha + rgb.
  - Ce qui colle au verre bouge avec le vaisseau, le monde derrière non.
  - Gardé hors de l'historique, rien ne traîne.
  - Sans vaisseau, la couche vaut (0, 0, 0, 1) : rendu identique au bit près.
- **Le lissage temporel reprojette les pixels du vaisseau avec lui.** Dans sa sphère, un point fixe dans son repère est porté du vaisseau courant au précédent (`reprojectShip`, `shipSphere`).
- **Le plan proche passe à 5 cm** dès que le vaisseau est dessiné. Le Z inversé garde la profondeur du terrain lointain.

## La verrière et le temps

- **`ShipWeather.hlsl`, un fil par image, tient l'état du verre.** Il lit les nuages du jeu, les mêmes au même temps, par `Clouds.hlsli` (`spec-nuages.md`). La température vient de la carte du climat (`Climate.hlsli`), au niveau de la mer moins 6,5 °C/km.
- **La météo est lue à la position du vaisseau,** dans son propre jeu de constantes nuages ; éloigner la caméra extérieure ne change ni pluie, ni température, ni givre.
- **L'état du verre :**
  - **Mouillé :** sous la pluie, et dans un nuage, d'autant plus vite que le vaisseau le traverse vite ; hors de l'eau, l'air le sèche, plus vite à grande vitesse.
  - **Pluie :** sous un cumulus épais, la part de cumulus de la météo et la profondeur optique au-dessus du vaisseau.
  - **Givre :** sous 0 °C, sur un verre humide ; la température est celle de la mer moins 6,5 °C/km.
- **`ShipGlass.hlsl` dessine :**
  - le reflet de Fresnel, du ciel dehors ou du cockpit dedans, et l'éclat du soleil ;
  - **l'eau** (`docs/recherche-eau-verriere.md`) : des gouttes simulées (`ShipWater.hlsli`), 8 192 au plus, sur la bulle ; leur carte couvre la bulle, au millimètre et deux dixièmes, et les forces sont prises dans le plan tangent à la bulle sous chaque goutte :
    - elles naissent de la pluie ou de l'eau captée en nuage, grossissent, fusionnent, et coulent sous la gravité et l'air ;
    - **leur trajet :** droit, jusqu'à un défaut du verre, une cellule de 5 mm sur douze environ, où elles marquent un temps et repartent avec un cap jusqu'à 45° de côté, qui revient sur 5 cm ; elles penchent un peu vers une trace mouillée ;
    - **leur forme :** un bord jamais tout à fait rond, des flancs bombés ; en coulant, plus plates, pas plus larges que leur traînée ;
    - **leur traînée :** une pellicule de leur largeur, que les suivantes reprennent ; elle sèche en cinq secondes environ, plus lentement sous la pluie, en se morcelant ;
    - **la poussée de l'air croît de 0 à 100 km/h, puis reste celle de 100 km/h :** au-delà, l'eau défile toujours à 30 à 50 cm/s ;
  - **leur rendu :** chaque goutte est une lentille grand-angle. Elle a un bord sombre et, hors des nuages, un point de ciel ;
  - le givre en frondes depuis le seuil de la bulle, sur un verre humide seulement.
- **Pas de buée :** un voile sur tout le verre brouillait la vue sans rien montrer du temps.
- **La verrière sert aussi de collimateur :**
  - horizon, échelle de tangage tous les 10° et marqueur de vecteur vitesse, à l'infini, dans un cône de 24° autour du nez ;
  - le petit combineur est sous la ligne des yeux, sans place sous le toit ;
  - éteint au démarrage, U l'allume ou l'éteint.
- **Vue de dehors, la verrière est un miroir bronze sombre,** comme les verrières traitées des chasseurs :
  - elle reflète 30 % environ de face, tout aux incidences rasantes, et laisse passer 8 % ;
  - le ciel s'y reflète plus clair vers l'horizon, le sol sous l'horizon ;
  - **vue de dedans, rien ne change :** un verre légèrement fumé.
- **`MYPLANETENGINE_VERRIERE=pluie`, `nuage` ou `givre` force un état,** pour les captures.

## Les écrans du tableau de bord

- **Les trois écrans et les trois cadrans montrent le vol,** pour l'œil seulement : `ShipScreens.hlsli`, appelé par `ShipPixel.hlsl` pour les rôles 1 à 6 du paquet.
- **Leurs images restent le fond :** cadres, titres et libellés de `textures_cockpit.py`. Ce que le vol change y est effacé puis redessiné, dans les mêmes couleurs, en chiffres à segments.
- **FLIGHT / ATTITUDE :**
  - horizon artificiel en roulis et en tangage, échelle tous les 5°, chiffrée tous les 10° ;
  - rose des caps qui tourne sous un index fixe, nord en ambre ;
  - vitesse en km/h, altitude au-dessus de la mer en km, cap, minutes et secondes de l'horloge.
- **NAV / TERRAIN :** une carte en courbes de niveau, cap en haut, 40 m par texel, qui défile avec le vaisseau ; latitude et longitude réelles. Le relief de la carte est inventé.
- **SHIP / SYSTEMS :** les barres suivent les gaz, la vitesse et l'horloge ; la température de coque est celle de l'air standard, réchauffé par la vitesse.
- **Les cadrans :** THRUST suit les gaz, ATT le tangage (4 à plat, ±90° aux butées), ALT la hauteur au-dessus du sol en km.
- **Les données, en fin de `Ship::Constants` :** `course` (cap, latitude, longitude, hauteur du sol) et `gauges` (gaz), remplies avec `ship.air` dans `D3DApp::UpdateShipFrame`.

## Le pilotage

- **Le standard des jeux spatiaux au clavier et à la souris,** Star Citizen et Everspace :
  - **Souris :** tangage et lacet, par un manche virtuel qui se recentre au repos.
  - **Roulis :** Q et E, soit A et E en AZERTY.
  - **Les gaz :** la molette. Vers le haut, le vaisseau va plus vite, et la vitesse tient sans rien toucher ; vers le bas, il ralentit jusqu'à l'arrêt. Trente crans, de 35 % chacun.
  - **Glissement :** A et D (Q et D) sur le côté ; W et S (Z et S), ou Espace et Ctrl, vers le haut et le bas, dans l'axe du vaisseau.
  - **Accélérer, freiner :** Maj accélère cinq fois, X freine.
  - **Tête libre :** clic droit maintenu ; au relâcher, la vue reste où elle est et la souris pilote de nouveau.
  - **Tête en bascule :** H donne la souris à la tête ; H à nouveau la rend au vaisseau, et la tête reste où elle est.
  - **R ramène la tête au repos,** un peu sous l'horizon, de 4,5°. En caméra libre, R garde l'ombrage facetté.
- **Une assistance de vol tient la vitesse des gaz.** Comme pour la caméra libre, elle est proportionnelle à la hauteur au-dessus du sol, au moins 60 m. Le cran du milieu vaut la vitesse par défaut de la caméra libre. Les glissements vont au moins à cette vitesse, même gaz coupés.
- **Le manche suit les commandes :**
  - il recule de 12° quand le nez monte, penche de 12° du côté du roulis, et tourne de 15° avec le lacet, comme un manche à torsion ;
  - le tangage et le lacet viennent du manche virtuel de la souris, le roulis des touches, adouci en un dixième de seconde ;
  - **la manette des gaz** bascule de 40° sur ses trente crans, vers l'avant avec les gaz.
- **Le vaisseau est porté le long de la sphère :** voler autour de la planète garde l'assiette.
- **La tête suit les accélérations,** comme dans les simulateurs de vol : un ressort amorti, d'après [MSFS Physics Camera](https://flightsim.to/addon/114953/msfs-physics-camera).
  - **Le sens :** l'œil recule à l'accélération, avance au freinage, penche à l'opposé des virages. La parallaxe avec le cockpit donne la profondeur.
  - **La mesure :** l'accélération est comprimée par son logarithme, car le vaisseau va du pas à la vitesse de la lumière. Environ 1,5 cm à 0,2 g, 4 cm à 2 g, au plus 6 cm vers l'avant et 3 cm de côté.
  - **Le ressort :** 1,4 Hz, amorti à 0,6. La tête traîne un peu, puis revient avec un léger rebond.
  - **L'accélération est celle de l'œil,** à 1 m au-dessus de l'axe de roulis : un roulis le jette de côté.
  - **Au roulis, la tête traîne aussi en rotation,** de 3° au plus, autour de l'axe du regard : la direction du regard ne change pas. Elle ne tourne ni en tangage ni en lacet.
- **La souris est lue en brut,** cachée et gardée dans la fenêtre. Alt maintenu la libère, pour atteindre la palette de tests. M la laisse à Windows, la fenêtre devant, pour une capture d'écran, puis la reprend. Elle est aussi relâchée quand la fenêtre perd le focus.
- **Espace monte dans les vues du vaisseau :** la pause de la météo n'y répond qu'en caméra libre.
- **Tab :** cockpit, poursuite, vaisseau caché.
  - **En poursuite,** le clic droit tourne la caméra tout autour du vaisseau, de dessous à dessus, et jusque devant lui.
  - **Le vaisseau caché** garde l'œil du pilote et les mêmes commandes, sans coque ni verrière : la vue la plus large.
- **Retour arrière :** la caméra libre, avec ses propres commandes, puis retour au cockpit. Passer de la caméra libre au vaisseau amène le vaisseau à la caméra.
- **`MYPLANETENGINE_VAISSEAU=cockpit`, `poursuite`, `sans` ou `libre` choisit la première vue.** Les bancs partent en caméra libre.

## Les jets et les ombres

- **Le panache des quatre tuyères** (`ShipPlume.hlsli`, `ShipPlumeVertex.hlsl`, `ShipPlumePixel.hlsl`) : les deux grandes des capots, les deux petites des emplantures, plus courtes à proportion de leur rayon.
  - une flamme de lumière à la sortie de chaque tuyère, d'un cœur blanc bleuté vers le violet, avec des losanges de choc et une faible lueur large autour du cœur ;
  - **elle finit en pointe :** elle s'élargit un peu au sortir de la tuyère, puis s'affine et s'éteint jusqu'à une pointe effrangée ;
  - **elle vit :** une turbulence à deux échelles descend le panache à une vingtaine de m/s, en fait onduler l'axe et strie le cœur ; les losanges tremblent ; chaque tuyère scintille une vingtaine de fois par seconde, à son propre rythme ;
  - **il suit les gaz, cran par cran,** de rien gaz coupés jusqu'à plein au trentième cran, avec le même temps de réponse que la vitesse. Lié à la vitesse, il était plein dès le premier cran en altitude, où la vitesse suit la hauteur ;
  - **sa longueur :** de 1,7 m au premier cran à 8 m.
- **Les jets d'attitude :** dix petits jets de vapeur, percés dans la peau (`assets/vaisseau/design_chasseur.py` imprime leurs positions) : au bout des ailes, vers le haut et le bas ; sur les capots moteurs, sur le côté ; au nez, vers le haut, le bas et chaque côté.
  - **Chacun tire quand sa poussée sert la commande :** le glissement, ou le couple du roulis, du tangage et du lacet autour du centre du vaisseau.
  - **Les glissements tirent tant que la touche est tenue ;** les rotations, au début et à la fin du mouvement, sur l'accélération angulaire, comme de vrais propulseurs d'attitude.
  - **En bouffées douces,** deux ou trois par seconde, chaque jet décalé des autres.
  - **Seulement quand le vaisseau n'avance pas :** ils s'éteignent entre 2 et 10 m/s vers l'avant ; en route, les tuyères et l'air dirigent le vaisseau. Monter, descendre ou glisser les garde.
  - **Jamais vus du cockpit,** pour garder la vue dégagée.
  - **La vapeur est blanche et légère,** éclairée par le soleil et le ciel.
- **Le rendu des jets se fait dans la couche de la verrière :**
  - chaque jet est marché dans sa boîte, 24 pas ;
  - la marche s'arrête à la distance de la scène, si bien que la coque et le sol cachent ce qui est derrière eux ;
  - hors du lissage temporel, rien ne traîne.
- **L'ombre du relief sur le vaisseau :**
  - la marche vers le soleil du terrain (`Shadows.hlsli`), une fois par image, depuis l'origine du vaisseau, dans la passe météo (`ShipWeather.hlsl`) ;
  - sa part de soleil multiplie le soleil des surfaces et l'éclat de la verrière, avec une image de retard.
- **L'ombre du vaisseau sur le sol et la mer** (`PixelShader.hlsl`, `ShipShadowOn`) :
  - la carte du vaisseau vers le soleil, lue au-delà de sa sphère le long du soleil ;
  - **le disque solaire la floute avec la distance,** sur sa pénombre de 0,0093 rad, en 16 lectures ;
  - au bout d'un kilomètre environ, la pénombre est aussi large que le vaisseau, et l'ombre s'efface.

## Limites

- **Ombres :**
  - **le relief ombre le vaisseau d'un bloc,** depuis son origine : une crête ne coupe pas la coque en deux ;
  - **le vaisseau n'ombre pas les objets proches,** pierres et plantes ; seulement le terrain et la mer.
- **Images :** mips calculés sur le CPU, en moyenne des codes sRGB, et sans compression. Les cartes du vaisseau prennent environ 125 Mo de mémoire vidéo. Les 12 images du paquet remplissent `Ship::MaxImages` : une image de plus demande d'agrandir le tableau et de décaler les registres de `Ship.hlsli`.
- **Les gouttes glissent sur la bulle comme sur son plan tangent :** près du pied, où les flancs se dressent, elles ne tombent pas de la verrière, elles s'y arrêtent au seuil.
- **Écrans :** aucune interaction ; hors du manche et de la manette, les commandes et voyants restent statiques.
- **Le lissage temporel ne suit pas le manche :** il reprojette ses pixels avec le vaisseau. Le jeu le coupe au démarrage ; la touche T le rétablit.
- **Le reflet de la verrière et de la coque** est celui d'un ciel et d'un sol moyens, sans les nuages ni le relief.
- **Le lissage temporel ne suit pas non plus les élevons.**
- **Les feux n'éclairent rien :** ni la coque ni le sol autour d'eux.
- **Jets :** ni lumière portée du panache sur le sol ou la coque, ni distorsion de chaleur.
- **Givre :** sa température vient du climat moyen, pas de la météo du jour.
