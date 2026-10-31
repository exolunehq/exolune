# Recherche : les nuages, de l'orbite au sol

Statut : recherche du 2026-10-24 : état de l'art, carte du temps, types et rendu, de l'orbite au sol. Ce qu'elle a donné les 24 et 25 octobre, la couche 2D puis l'ancien volume en cascades, tag `piste/nuages`, est au log : `log/recherche-nuages-historique.md`. Les nuages du jeu, en place, sont décrits par `spec-nuages.md` : ils viennent des spikes Frostbite et Wicked, pas de ce plan. Couvre les nuages, le brouillard et les stratus qui touchent le sol, et leurs liens avec l'atmosphère et le terrain. La brume et la perspective aérienne relèvent d'une autre recherche : on n'en parle ici que là où elles touchent les nuages.

## 1. Conclusion et plan

**La conclusion.**
- **Une carte du temps, deux bruits de plus.** Deux appels à `Fbm3`, posés sur le climat qui existe déjà, décident la couverture, le type, la base et l'épaisseur. Tous les moteurs font ainsi : Horizon, Frostbite et Unity lisent trois nombres par colonne d'air dans une texture 2D.
- **Un champ, deux façons de l'intégrer.** De loin, une couche 2D montre la moyenne exacte du champ sur le pixel. De près, un volume en lancer de rayons montre sa forme. Les deux ont la même épaisseur optique par colonne : le passage ne change pas la part de nuage.
- **La règle universelle s'applique telle quelle.** La couverture est un seuil sur un bruit. `SpreadStep` et `FbmLostShare` donnent la part du pixel sous un nuage, la même à toute distance.
- **La base vient du climat.** Lawrence (2005) : base ≈ (20 + T/5) × (100 − HR) m. Quand l'air est saturé, elle tombe au sol : c'est le brouillard.
- **Le coût tient.** Couche 2D et ombres : 0,3 à 0,9 ms en 1440p, estimé. Volume proche : 1 à 2 ms visés, en quart de résolution avec accumulation temporelle, comme Unreal et Horizon.
- **Rien de publié ne traite le passage de l'orbite au sol sous la règle de la moyenne.** Unreal et Star Citizen lancent leurs rayons jusque depuis l'espace. L'équipe de SpaceEngine jugeait en 2017 qu'aucune méthode ne tenait de l'espace au sol. La couche 2D comme moyenne du volume est notre proposition.

**Le plan.**

| Étape | Contenu | Mesure de réussite | Coût |
|---|---|---|---|
| 1 | La carte du temps, et une vue de diagnostic `clouds` : la part de nuage par pixel, sans rendu | fraction par bande de 10° de latitude à 10 points de MODIS au plus ; part constante à 2 points près de 1 500 à 60 km au banc de descente | moins de 0,1 ms |
| 2 | La couche 2D éclairée, dans la passe d'atmosphère ; ses ombres sur le terrain ; la lumière diffuse sous un plafond | aspect contre des photos de l'ISS, à hauteur et soleil égaux | 0,3 à 0,9 ms |
| 3 | Le volume près de la caméra, sur la même carte ; le fondu vers la couche 2D | banc de transition : même zone en 2D et en volume, moyenne à 2 % près | 1 à 2 ms |
| 4 | Tous les types : cumulonimbus et enclumes, nuages hauts, brouillard de vallée, nuages de relief ; une carte terre-mer cuite au démarrage | répartition en hauteur contre CALIPSO ; types contre ISCCP ; photos au sol par genre | à mesurer |
| 5 | La lumière fine : ombres des nuages dans l'air, sol qui éclaire leur base, carte d'ombre près du sol | photos de couchers de soleil et de rayons | à mesurer |

**L'étape 1 est petite et mesurable.**
- **Ce qu'elle touchait :** un fichier `Clouds.hlsli`, une vue de diagnostic de plus dans `PixelShader.hlsl` et `D3DApp.cpp`, un banc `tools/banc_nuages.py`. Faite le 2026-10-24, retirée le 2026-10-30 avec l'ancien volume, tag `piste/nuages`.
- **Rien ne s'affiche en vol :** on cale la carte sur les données avant de dessiner un nuage.

**Ce qu'on laisse pour plus tard :** le vent et l'évolution dans le temps, la pluie, les éclairs, les halos. Des nuages fixes sur la planète se reprojettent exactement d'une image à l'autre, comme le terrain.

## 2. La carte du temps

### Ce que font les moteurs

| Moteur | La carte | Ce qu'elle décide |
|---|---|---|
| Horizon Zero Dawn, Schneider 2015 | texture 2D : rouge la couverture, vert la précipitation, bleu le type ; sortie d'une simulation météo, ou peinte pour les cinématiques | trois profils en hauteur, stratus, stratocumulus, cumulus, mêlés par le type ; la précipitation mène au cumulonimbus vers 70 % de couverture |
| Frostbite, Högfeldt 2016, §5.3.1 | texture météo 2D peinte : rouge la couverture projetée, vert le type ; répétable au besoin | table séparée type × hauteur : densité et érosion ; bruits3D pour les formes et le détail |
| Unity HDRP | carte : rouge la couverture, vert la pluie, bleu le type ; table type × hauteur : profil, sensibilité à l'érosion, occlusion | quatre préréglages : épars, nuageux, couvert, orage |
| takram three-clouds | jusqu'à quatre couches, une par canal d'une texture météo ; profil a·e^(bη) + cη + d | base et épaisseur par couche |
| Unreal, Hillaire 2020 | un matériau volumique libre, dans une couche de base et d'épaisseur données | tout, au prix d'un graphe par projet |
| Red Dead Redemption 2, Bauer 2019 | nuages et brouillard dans un même lancer de rayons | non détaillé hors des diapositives |
| Flight Simulator | prévisions de Meteoblue | passage des données aux nuages non publié |

- **Le point commun :** trois ou quatre nombres par colonne d'air, couverture, type, base, épaisseur, et un profil vertical par type.
- **Horizon dessine ses nuages bas en volume, de 1 500 à 4 000 m,** et les nuages moyens et hauts en textures 2D qui défilent au-dessus.
- **Ces cartes sont des textures qui se répètent.** Schneider les décrit comme plusieurs bruits qui défilent, parfois retouchés à la main. Sur une planète entière, un bruit sur la grille de la planète les remplace sans répétition.

### Notre carte : quatre couches, dont une existe

| Couche | Bruit | Longueurs d'onde | Ce qu'elle décide |
|---|---|---|---|
| Le climat | existant : `regional` de `GroundMaterials`, `ClimateHumidity`, la température | 3 000 à 200 km | la nébulosité moyenne, la base |
| Le temps, `W` | un `Fbm3` | 4 000 à 30 km | x : fronts et dépressions ; y : vigueur de la convection ; z : nuages hauts |
| Les nuages, `M` | un `Fbm3` | 30 km au pixel | x : présence, seuillée ; y : épaisseur ; z : détail des nuages hauts |
| Le détail, de près seulement | une tuile 3D générée au démarrage | 2 km à 20 m | l'érosion des bords, bombés ou effilochés |

- **`Fbm3` donne trois bruits pour le prix d'une grille :** chaque couche coûte un seul appel.
- **Le prix :** 15 à 25 octaves par pixel en tout. Le relief en demande environ 340 par sommet.

### Ce que chaque grandeur suit

**La nébulosité visée, `cloudiness`,** la part de ciel couvert attendue en moyenne sur la région.
- **L'humidité du climat en porte déjà une partie :** son creux vers 24° de latitude est celui des déserts, sous la branche descendante de la circulation. Les mêmes descentes d'air dégagent le ciel.
- **Deux ceintures montantes à ajouter,** de la même forme en gaussienne de latitude : la zone de convergence intertropicale près de l'équateur ; les latitudes moyennes, surtout l'océan Austral.
- **MODIS les montre ainsi :** beaucoup de nuages dans la zone intertropicale, sur l'océan Austral et sur les bancs de stratocumulus ; moins de 15 à 30° de latitude ; peu sur les déserts, le Groenland et l'Antarctique (King et al. 2013).
- **Le temps, `W.x`,** ajoute les fronts et les dépressions : de grandes zones couvertes de 500 à 2 000 km.
- **Les mers plus que les terres :** 72 % contre 55 % sur Terre, 67 % en moyenne (King et al. 2013). Il faut la carte terre-mer : étape 4.

**La couverture du pixel, `cover`.** Un seuil sur `M.x`, réglé pour que la part au-dessus vaille `cloudiness`.
- **Le seuil :** t = 0,146 × Probit(1 − cloudiness), 0,146 étant l'écart-type de `Fbm3`. Probit(p) ≈ ln(p / (1 − p)) / 1,7 suffit.
- **La part du pixel :** `SpreadStep` autour de t, élargie de ce que le pixel ne montre pas de `M`, par `FbmLostShare`. La part moyenne ne bouge pas avec la distance.

**Le type,** de 0 à 1 : 0 stratiforme, 0,5 cumulus, 1 cumulonimbus. Comme le canal bleu d'Horizon et d'Unity.
- **Convectif quand l'air est chaud et humide en bas :** la température au niveau de la mer, l'humidité, `W.y`.
- **Cumulonimbus là où l'air monte :** zone intertropicale, et `W.y` fort.
- **Stratiforme sous les descentes d'air, sur mer :** les bancs de stratocumulus des bords est des océans subtropicaux. Leur couverture croît d'environ 6 % par degré de stabilité de l'air (Klein et Hartmann 1993).
- **Stratiforme dans les fronts :** `W.x` fort aux latitudes moyennes donne nimbostratus et altostratus, avec des cirrus en avant.
- **Stratus et brouillard au froid humide,** quand la base tombe au sol.

**La base,** au-dessus du niveau de la mer : z ≈ (20 + T/5) × (100 − HR) m, à 15 % près pour HR de 50 à 100 % et T de 0 à 30 °C (Lawrence 2005).
- **T :** la température du climat au niveau de la mer, sans l'altitude du lieu.
- **HR :** tirée de l'humidité du climat ; la correspondance se cale au banc 3.
- **Ordres de grandeur :** 750 m pour 25 °C et 70 % ; 0 m à 100 % ; plus de 2 km sur les déserts.
- **La base est la même au-dessus des plaines et des montagnes d'une région.** Là où le relief la dépasse, le sol est dans le nuage : le brouillard de colline vient sans règle de plus, et les sommets percent une mer de nuages.

**Le sommet,** selon le type.
- **Stratus, stratocumulus :** quelques centaines de mètres au-dessus de la base, sous l'inversion (Wood 2012).
- **Cumulus :** 0,5 à 2 km d'épaisseur, modulée par `M.y` ; jusqu'à 6 km en congestus.
- **Cumulonimbus :** jusqu'à la tropopause, de 16 km sous les tropiques à 8 ou 9 km aux pôles. Une fonction de la latitude suffit.
- **Nuages hauts :** une couche à part, tirée de `W.z` et des cumulonimbus voisins : les enclumes s'étalent en cirrus.

### Le croquis de la fonction

```hlsl
// Clouds.hlsli, proposition. q : point de la planète depuis l'ancre ; pixel : log2 de sa taille sur la couche (m).
const float3 W = Fbm3(q, log2(4.0e6), log2(3.0e4), pixel, 0.5, 71u);  // le temps
const float3 M = Fbm3(q, log2(3.0e4), 0.0, pixel, 0.55, 73u);        // les nuages
const float cloudiness = saturate(c0 + c1 * (humidity - 0.6) + Belts(sinLat) + c2 * W.x); // à caler, banc 1
const float t = 0.146 * Probit(1.0 - cloudiness);
const float sigma = 0.146 * sqrt(FbmLostShare(log2(3.0e4), 0.0, pixel, 0.55));
const float cover = SpreadStep(t - 0.02, t + 0.02, M.x, sigma);       // part du pixel sous un nuage
const float base = (20.0 + seaLevelT / 5.0) * (100.0 - RelativeHumidity(humidity)); // m, Lawrence 2005
```

### Le relief, la terre et la mer : étape 4

- **Les nuages doivent savoir ce qu'il y a sous eux,** à des centaines de kilomètres de la caméra : terre ou mer, relief lissé. On ne peut pas évaluer complexplanet à chaque pas d'un rayon.
- **Proposition : une carte cuite au démarrage,** comme les tuiles des matériaux. Une cubemap de 6 × 512² texels, environ 20 km, avec le relief filtré à sa maille, la part de mer, la carte du temps grossière. Ses mipmaps gardent la moyenne.
- **Ce qu'elle permet :**
  - plus de nuages sur mer que sur terre, et les stratocumulus sur mer seulement ;
  - les nuages de relief : au vent, l'air monte, et la nébulosité croît avec la pente du relief lissé face au vent ; sous le vent, le ciel s'ouvre (Houze 2012) ;
  - le brouillard de vallée : il remplit le relief sous un sommet de brouillard tiré du relief lissé, au froid humide ;
  - les vents dominants par latitude, alizés d'est puis vents d'ouest, pour orienter les rues de nuages et les cirrus.

### Ce qui garde la carte sous nos règles

- **Bruit de gradient, `Noise3`, sur la grille de la planète.** Les nuages sont fixes dans le repère de la planète, jamais relatifs à l'ancre.
- **Aucun bruit ne s'efface :** sa part invisible élargit le seuil de couverture.
- **Un écart à documenter :** la forme bombée des cumulus vient, chez tous, d'un bruit cellulaire de Worley. Le dépôt en a un, `VoronoiDistance`, et `Billow`. Essayer d'abord un Billow sur `Noise3`, et ne garder le cellulaire que si le banc d'aspect le justifie.

## 3. Les types de nuages

**Les hauteurs de l'Atlas international des nuages,** par étage :

| Étage | Pôles | Latitudes moyennes | Tropiques |
|---|---|---|---|
| Hauts : cirrus, cirrocumulus, cirrostratus | 3 à 8 km | 5 à 13 km | 6 à 18 km |
| Moyens : altocumulus, altostratus | 2 à 4 km | 2 à 7 km | 2 à 8 km |
| Bas : stratus, stratocumulus, cumulus, base des cumulonimbus | 0 à 2 km | 0 à 2 km | 0 à 2 km |

- **Les exceptions de l'Atlas :** le nimbostratus déborde sur les autres étages ; cumulus et cumulonimbus ont leur base en bas et montent jusqu'aux étages moyen et haut.

**Les types, leur aspect et leur profil.** Épaisseurs et épaisseurs optiques en ordres de grandeur, à confirmer au banc ISCCP.

| Type | Base | Épaisseur | Épaisseur optique | Aspect | Profil en hauteur |
|---|---|---|---|---|---|
| Stratus, brouillard | 0 à 500 m | 0,1 à 0,5 km | 5 à 20 | gris uniforme ; d'orbite, nappe lisse qui épouse les vallées | dense partout, coupé net en haut |
| Stratocumulus | 0,3 à 1,5 km | 0,2 à 0,5 km, sous l'inversion | 5 à 15 | nappe bosselée, plages grises ; d'orbite, cellules ouvertes ou fermées | croît vers le haut, sommet plat |
| Cumulus | 0,5 à 2 km, plus haut au sec | 0,5 à 2 km ; congestus jusqu'à 6 km | 5 à 50 | base plate et sombre, sommet en chou-fleur, bords nets | croît vers le haut, sommet arrondi ; bombé en haut, effiloché en bas |
| Cumulonimbus | 0,5 à 2 km | jusqu'à la tropopause ; enclume de 50 à 200 km | 50 à plus de 100 | tour blanche, base noire, rideaux de pluie ; d'orbite, disques lisses | colonne ; en haut, seuil de couverture abaissé : l'enclume s'étale |
| Nimbostratus | 0,5 à 2 km | 3 à 7 km | 20 à 60 | gris sombre, base floue, pluie | épais, doux, base diffuse |
| Altostratus | 2 à 7 km | 1 à 3 km | 5 à 20 | voile gris, soleil comme derrière un verre dépoli | uniforme |
| Altocumulus | 2 à 7 km | 0,2 à 0,7 km | 1 à 10 | galets ou rouleaux en bancs | mince, bosselé |
| Cirrus et voisins | 5 à 13 km ; 6 à 18 km aux tropiques | mince | 0,1 à 3 | filaments, voiles, halos | couche 2D étirée dans le vent |

- **L'épaisseur optique va de moins de 0,1 pour un cirrus fin à plus de 1 000 pour un grand cumulonimbus** (glossaire de l'AMS).
- **Les stratocumulus couvrent plus de la Terre que tout autre type,** plus de la moitié des océans subtropicaux frais en moyenne annuelle ; ils sont minces, au sommet de la couche limite (Wood 2012).

**Comment les moteurs les représentent.**
- **Un profil de densité par type,** en fonction de la hauteur relative η dans la couche : Horizon en a trois, Unity une table type × hauteur, takram une formule.
- **La densité croît vers le haut** dans les nuages convectifs : l'eau condensée augmente avec la hauteur au-dessus de la base. Horizon et takram le font.
- **L'érosion :** un bruit fin retranché au bord, plus fort là où la densité est faible. Inversé en bas, il effiloche la base : Horizon, Frostbite.
- **Les nuages hauts en 2D :** Horizon les dessine en textures qui défilent ; leur faible épaisseur le justifie.

**Notre table de types :** une petite texture type × η, générée au démarrage. Elle donne la densité, l'érosion, la part bombée ou effilochée, et l'intégrale du profil pour l'épaisseur optique de la couche 2D.

**Le brouillard est un nuage dont la base touche le sol.**
- **Même modèle, même extinction.** La visibilité vaut 3,9 / σ (Koschmieder).
- **Dans un nuage d'eau,** σ ≈ 3 × eau liquide / (2 × masse volumique de l'eau × rayon effectif) (Stephens 1978) : 0,02 à 0,1 m⁻¹, soit 40 à 200 m de visibilité.
- **Le brouillard commence sous 1 km de visibilité.** Au-delà, c'est la brume, de l'autre recherche.

## 4. Le rendu, de l'orbite à l'intérieur d'un nuage

### L'état de l'art : le lancer de rayons volumique

- **Beer-Lambert, intégré pas à pas.** Hillaire intègre analytiquement la lumière sur chaque pas : le résultat ne dépend plus de la longueur du pas. Notre `IntegrateScattering` le fait déjà pour l'air.
- **La diffusion multiple en octaves de diffusion simple** (Wrenninge 2013) : chaque octave diffuse plus, est moins ombrée, et a une phase plus isotrope. Unreal recommande une octave en jeu, deux au plus.
- **La phase :** Henyey-Greenstein à deux lobes, avant et arrière : Unreal, takram.
- **L'effet « poudre » d'Horizon,** les bords sombres face au soleil. Hillaire le juge non physique : il préfère baisser l'albédo aux bords, là où la densité tombe.
- **La lumière du soleil.** Horizon prend 6 échantillons en cône vers le soleil, le dernier loin, pour l'ombre des nuages voisins. Unreal propose aussi sa carte d'ombre de Beer : moins précise, en gris, mais à portée illimitée.
- **Le ciel :** une lumière ambiante qui croît avec la hauteur dans le nuage.
- **Sauter le vide :** pas grossiers hors du nuage, fins dedans ; arrêt quand la transmittance passe sous 0,01. Nubis 2023 ajoute des champs de distance signée.

**Les ruses de résolution.**
- **Horizon :** un pixel sur 16 recalculé par image, le reste reprojeté. De 20 ms à environ 2 ms sur PS4.
- **Unreal, mode 0 :** trace en quart de résolution, reconstruit en demi, puis plein. Recommandé du sol à l'espace.
- **Toft et al. 2016 :** 8 pas au lieu de 128, avec un départ aléatoire et une accumulation temporelle.
- **Le prix :** traînées et fantômes sur ce qui bouge vite. Nubis 2022 y consacre une partie, et vise 1080p sans reconstruction temporelle.

### Les moteurs à l'échelle d'une planète

- **Unreal :** le même lancer de rayons de l'espace au sol, mode 0 recommandé. Hillaire montre de petites planètes avec les ombres douces de leurs nuages.
- **Star Citizen :** démonstration de 2023, nuages volumétriques planétaires et passage de l'espace au sol. Technique non publiée.
- **Michelic et al. 2019, poster d'I3D :** nuages volumétriques et atmosphère précalculée, transitions continues du sol à l'espace, plus de 120 images/s. Détails non publiés.
- **Pixar, 2022 :** une image 2D de nuages plaquée dans une coquille sphérique épaisse, pour des vues de l'espace.
- **takram three-clouds :** couches sur l'ellipsoïde, vues de l'espace seulement prévues.
- **Elite Dangerous Odyssey :** atmosphères légères, pas de système météo. **No Man's Sky, Outerra :** rien de publié ; Outerra n'avait qu'une couche.
- **SpaceEngine, 2017 :** aucune méthode jugée assez bonne de l'espace au sol.

### Notre proposition : un champ, deux intégrateurs

**De loin : la couche 2D, moyenne exacte du champ.** Une coquille sphérique par couche. À son intersection avec le rayon :
- **La part du pixel couverte, `cover`,** par la règle universelle. La taille du pixel sur la coquille vaut la distance fois l'angle du pixel, divisée par le cosinus de l'incidence.
- **L'épaisseur optique dans le nuage,** τ = σ × épaisseur × intégrale du profil.
- **La transmittance moyenne du pixel :** 1 − cover + cover × e^(−τ/μ). C'est la moyenne des transmittances, pas la transmittance de la moyenne : e^(−τ) n'est pas linéaire.
- **La lumière renvoyée,** à deux flux, nuage non absorbant : R ≈ (1 − g) τ / (2 + (1 − g) τ), avec g ≈ 0,85 (Bohren 1987). τ = 10 donne R ≈ 0,43 ; τ = 50, 0,79. Le reste, 1 − R, traverse en diffus. Le facteur se cale sur les photos.
- **L'éclairage vient de nos tables :** la transmittance du soleil jusqu'au sommet, l'irradiance du ciel.
- **Le relief des sommets :** la hauteur du sommet varie avec l'épaisseur ; sa pente donne une normale, comme pour un terrain. D'orbite, les champs de cumulus se lisent en bosses.

**De près : le volume.**
- **La densité :** cover × profil(type, η) × érosion par la tuile 3D.
- **L'érosion est un seuil sur un bruit : même règle.** Les mipmaps de la tuile donnent la moyenne sous l'empreinte du pas ; sa part invisible élargit le seuil.
- **La colonne du volume a l'épaisseur optique de la couche 2D :** la table des types porte l'intégrale du profil, et le banc de transition vérifie l'égalité.
- **Quart de résolution et accumulation temporelle,** dans un historique propre aux nuages, reprojeté par leur profondeur moyenne.
- **Dans le volume, `Fbm3` coûterait trop à chaque pas.** La carte grossière se lit dans la cubemap de l'étape 4, la fine dans une tuile 2D générée, comme les tuiles des matériaux.

**Le passage.**
- **Le critère :** l'épaisseur du nuage à l'écran, en pixels. Sous un pixel, le volume n'apporte rien que la couche 2D n'ait déjà.
- **À 1440p, un pixel couvre 0,73 mrad.** Un nuage de 1 km d'épaisseur fait 14 pixels à 100 km, 5 pixels à 300 km.
- **Le budget borne donc le volume :** jusqu'à 100 à 200 km, takram s'arrête à 200 km ; puis un fondu vers la 2D sur un facteur 2 de distance. Il se verra de côté, vers l'horizon : le banc de transition le mesure.
- **D'orbite,** tout nuage est à plus de 200 km : couche 2D seule.
- **Les nuages hauts restent en 2D** à toute distance, comme chez Horizon.

**Dans le nuage.** Le rayon part de la caméra, la densité est celle du volume, le brouillard de même. La visibilité vient de σ seule.

**La limite de la couche 2D :** vers l'horizon, les flancs des nuages comblent les trous entre eux ; une coquille sans épaisseur les laisse ouverts. C'est une raison de plus pour le volume près du sol.

### Le budget

**Ce qui est publié.**

| Source | Matériel | Méthode | Coût |
|---|---|---|---|
| Horizon, 2015 | PS4 | 64 à 128 pas, 6 échantillons de lumière ; 1 pixel sur 16 par image | 20 ms, puis environ 2 ms |
| Toft et al. 2016 | GTX 1080, 1080p | demi-résolution, 8 pas, départ aléatoire, accumulation | 7,5 ms ; 2,4 ms en quart de résolution ; 297,7 ms pour 128 pas en pleine résolution |
| Unity HDRP, 2021 | PS4 ; GPU haut de gamme récent | non précisé | 2 ms ; moins de 0,5 ms |
| Frostbite, Högfeldt 2016 | Radeon HD 7870 | 960 × 540, accumulation à 5 % | en courbes seulement |
| takram, version 0.0.1 | RTX 4090, navigateur | 1/16 des texels par image | 60 images/s, plafonnées |

**Nos estimations, à mesurer, sur la RTX 4070 Ti.**
- **La couche 2D :** deux `Fbm3` par pixel. `GroundMaterials` en fait davantage pour 0,1 à 2 ms de rendu. Estimé 0,2 à 0,6 ms en 1440p.
- **Les ombres sur le terrain :** un `Fbm3` de plus par pixel de sol, 0,1 à 0,3 ms.
- **Le volume :** quart de résolution en 1440p, 0,9 million de rayons, 64 pas au plus. La 4070 Ti calcule environ quatre fois plus vite qu'une GTX 1080, et l'écran a 1,8 fois plus de pixels : Toft donnerait environ 1 ms. Cible : 1 à 2 ms.

## 5. Avec l'atmosphère et le terrain

**Composer avec l'atmosphère.**
- **La couche 2D entre dans la boucle de `IntegrateScattering`.** Au pas qui franchit la coquille, la lumière du nuage s'ajoute, multipliée par la transmittance déjà accumulée ; puis la transmittance se multiplie par celle du nuage. L'air et le sol derrière sont voilés d'autant.
- **Le volume rend lumière, transmittance et profondeur moyenne pondérée par l'opacité.** La passe d'atmosphère insère le nuage à cette profondeur.
- **takram fait de même,** avec des défauts quand deux nuages épars se recouvrent à des distances différentes. Unreal offre une perspective aérienne par pas, plus chère.
- **La profondeur des nuages passe en flottants 32 bits,** comme celle du terrain : règle de précision des passes.

**L'atmosphère éclaire les nuages.**
- **Le soleil :** la table de transmittance donne sa couleur à l'altitude du point. Au coucher, les nuages rougissent par en dessous. Hillaire la prend à chaque pas pour les couchers de soleil.
- **Le ciel :** la table d'irradiance s'arrête à 10 km. Il faut la monter vers 18 km pour les sommets de cumulonimbus et les cirrus.
- **Le sol éclaire la base,** plus sur neige ou désert. Unreal l'offre en option : étape 5.

**Les nuages agissent sur l'atmosphère.**
- **Sous un plafond, l'air ne diffuse plus le soleil direct.** Sinon, l'air sous un ciel couvert reste bleu et lumineux : une faute visible.
- **Le remède simple :** à chaque pas de l'atmosphère sous la couche, l'ombre grossière, tirée de `W` seule.
- **Les rayons de soleil entre les nuages** viennent de la même ombre, prise plus finement : étape 5.

**L'ombre sur le terrain.**
- **Analytique, sans carte d'ombre.** Au point de sol, le rayon vers le soleil croise la coquille ; la transmittance moyenne en ce point est l'ombre. Son décalage avec la hauteur du soleil vient tout seul.
- **Elle suit la règle du pixel :** la part d'ombre est la moyenne sur ce que le pixel couvre.
- **Une carte d'ombre ne tient pas à l'échelle d'une planète :** d'orbite, elle devrait couvrir un hémisphère. Unreal la borne à un rayon autour de la caméra. Elle ne servira qu'au volume près du sol.
- **La lumière diffuse sous les nuages :** la part transmise en diffus, 1 − R, moins le direct, s'ajoute à la lumière du ciel. Sous un plafond épais, le sol est éclairé sans ombres portées.

**La brume, là où elle touche les nuages.** Points à partager avec l'autre recherche.
- **Une même hauteur de couche limite :** la brume des basses couches s'arrête sous l'inversion, au sommet des stratocumulus, ou vers la base des cumulus. Proposition : un seul champ pour les deux.
- **Un même champ d'humidité :** les aérosols gonflent avec l'humidité ; vers 100 %, le nuage prend le relais.
- **Une extinction continue de la brume au brouillard,** de part et d'autre de 1 km de visibilité.

## 6. Mesurer

**Banc 1, la fraction nuageuse par latitude.** Étape 1.
- **La référence :** MODIS, fraction nuageuse mensuelle, en moyenne annuelle par bande de 10°. Images sur NASA NEO ; nombres à 1° dans les produits MOD08_M3 et MYD08_M3, avec un compte Earthdata gratuit.
- **Notre mesure :** la vue `clouds` rendue en équirectangulaire à 1° ; chaque pixel blanc avec la probabilité de sa couverture, comme les autres vues de diagnostic. À défaut, des captures verticales sur une grille de lieux.
- **La cible :** la forme du profil, et une moyenne proche de 67 %. Écart par bande sous 10 points.
- **Plus tard :** terres et mers séparées, 55 % et 72 %, avec la carte terre-mer.

**Banc 2, la descente.** `tools/banc_descente.py` avec la vue `clouds` : la part de nuage d'une zone de 60 km, de 1 500 à 60 km de haut. Une courbe plate, à 2 points près, prouve la règle universelle.

**Banc 3, les hauteurs et les types.**
- **CALIPSO-GOCCP :** fraction nuageuse par latitude, longitude et altitude, par mois. Comparer notre coupe latitude × altitude : bases, sommets, tours tropicales.
- **ISCCP :** neuf types par pression du sommet et épaisseur optique. Comparer la part de chaque type par bande de latitude.
- **La base :** la formule de Lawrence contre la table de son article ; la répartition des bases contre GOCCP.

**Banc 4, l'aspect d'orbite.**
- **Les photos de l'ISS,** base « Gateway to Astronaut Photography of Earth » : chacune donne son point au nadir, l'altitude, l'angle du soleil et une couverture estimée.
- **Les captures du moteur** à la même hauteur et au même soleil, sur un lieu de même climat.
- **Les mesures :** part couverte, histogramme de luminance, spectre de puissance pour la taille des cellules et des trous, décalage des ombres.
- **Blue Marble 2002 :** sa couche de nuages, composite de deux jours de MODIS, pour l'aspect global.

**Banc 5, l'aspect au sol.**
- **Les photos de l'Atlas international des nuages,** par genre, à hauteur de soleil connue ou estimable.
- **Les mesures :** rapport de luminance entre base et ciel, contraste des bords, spectre, comme `realisme.py`.
- **Le banc de transition,** à l'étape 3 : la même zone en 2D et en volume, à la distance de bascule ; écart moyen et écart-type de luminance.

**Le coût :** la passe des nuages en ms à 1, 10, 100, 400 et 2 000 km, comme le reste du journal.

## 7. Sources

**Moteurs et conférences.**
- Schneider, *The Real-time Volumetric Cloudscapes of Horizon Zero Dawn*, SIGGRAPH 2015 : [diapositives](https://www.advances.realtimerendering.com/s2015/The%20Real-time%20Volumetric%20Cloudscapes%20of%20Horizon%20-%20Zero%20Dawn%20-%20ARTR.pdf)
- Schneider, *Nubis: Authoring Real-Time Volumetric Cloudscapes with the Decima Engine*, SIGGRAPH 2017 : [page](https://www.guerrilla-games.com/read/nubis-authoring-real-time-volumetric-cloudscapes-with-the-decima-engine)
- Schneider, *Nubis, Evolved*, SIGGRAPH 2022 : [page](https://www.guerrilla-games.com/read/nubis-evolved), [PDF](https://advances.realtimerendering.com/s2022/SIGGRAPH2022-Advances-NubisEvolved-NoVideos.pdf)
- Schneider, *Nubis³*, SIGGRAPH 2023 : [page](https://www.guerrilla-games.com/read/nubis-cubed), [PDF](https://advances.realtimerendering.com/s2023/Nubis%20Cubed%20(Advances%202023).pdf)
- Hillaire, *Physically Based Sky, Atmosphere and Cloud Rendering in Frostbite*, SIGGRAPH 2016 : [notes](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/s2016_pbs_frostbite_sky_clouds.pdf)
- Högfeldt, *Convincing Cloud Rendering*, mémoire, Chalmers 2016 : [PDF](https://publications.lib.chalmers.se/records/fulltext/241770/241770.pdf)
- Hillaire, *Physically Based and Scalable Atmospheres in Unreal Engine*, SIGGRAPH 2020 : [diapositives](https://blog.selfshadow.com/publications/s2020-shading-course/hillaire/s2020_pbs_hillaire_slides.pdf)
- Hillaire, *A Scalable and Production Ready Sky and Atmosphere Rendering Technique*, EGSR 2020 : [article](https://diglib7.eg.org/bitstream/handle/10.1111/cgf14050/v39i4pp013-022.pdf)
- Unreal Engine, nuages volumétriques : [composant](https://dev.epicgames.com/documentation/en-us/unreal-engine/volumetric-cloud-component-in-unreal-engine), [propriétés](https://dev.epicgames.com/documentation/en-us/unreal-engine/volumetric-cloud-component-properties-in-unreal-engine)
- Bauer, *Creating the Atmospheric World of Red Dead Redemption 2*, SIGGRAPH 2019 : [cours](https://advances.realtimerendering.com/s2019/index.htm)
- Unity HDRP, nuages volumétriques : [manuel](https://docs.unity3d.com/Packages/com.unity.render-pipelines.high-definition@14.0/manual/Override-Volumetric-Clouds.html) ; coûts annoncés dans le [blog Unity](https://blog.unity.com/technology/experience-true-volumetric-clouds-with-hdrp-unity-20212), lus dans un extrait de recherche, la page ne répondant plus
- Toft, Bowles, Zimmermann, *Optimisations for Real-Time Volumetric Cloudscapes*, 2016 : [arXiv](https://arxiv.org/abs/1609.05344)
- takram, *three-clouds* : [dépôt](https://github.com/takram-design-engineering/three-geospatial/tree/main/packages/clouds)
- Flight Simulator 2024, résumé d'une émission des développeurs : [msfsaddons](https://msfsaddons.com/2024/09/25/msfs-team-answers-questions-about-msfs-2024-in-latest-developer-livestream)
- Star Citizen, démonstration CitizenCon 2953 : [DSOGaming](https://www.dsogaming.com/?p=175272)
- Michelic et al., *Real-time Rendering of Procedural Planets at Arbitrary Altitudes*, poster I3D 2019 : [page](https://www.cg.tuwien.ac.at/research/publications/2019/kerbl_2019_planet_poster/)
- Pixar, planètes et nuages vus de l'espace, SIGGRAPH 2022 : [article](https://graphics.pixar.com/library/PlanetAndClouds/paper.pdf)
- Elite Dangerous Odyssey, émission sur les planètes : [Massively OP](https://massivelyop.com/?p=324331)
- SpaceEngine, forum, 31 juillet 2017 : [fil](https://forum.spaceengine.org/viewtopic.php%3Fp=10919.html)
- Wrenninge, Kulla, Lundqvist, *Oz: The Great and Volumetric*, SIGGRAPH 2013 : [archive](https://history.siggraph.org/learning/oz-the-great-and-volumetric-by-wrenninge-kulla-and-lundqvist)
- Webanck et al., *Procedural Cloudscapes*, Eurographics 2018 : [PDF](https://perso.liris.cnrs.fr/eric.galin/Articles/2018-cloudscapes.pdf)

**Climat et physique des nuages.**
- King et al., *Spatial and Temporal Distribution of Clouds Observed by MODIS*, IEEE TGRS 2013 : [PDF](https://atmosphere-imager.gsfc.nasa.gov/sites/default/files/ModAtmo/King_et_al.2013.pdf)
- Klein et Hartmann, *The Seasonal Cycle of Low Stratiform Clouds*, J. Climate 1993
- Wood, *Stratocumulus Clouds*, Monthly Weather Review 2012 : [publications](https://atmos.uw.edu/~robwood/publications.html)
- Lawrence, *The Relationship between Relative Humidity and the Dewpoint Temperature in Moist Air*, BAMS 2005, doi 10.1175/BAMS-86-2-225
- Houze, *Orographic Effects on Precipitating Clouds*, Reviews of Geophysics 2012
- Stephens, *Radiation Profiles in Extended Water Clouds*, J. Atmos. Sci. 1978
- Bohren, *Multiple Scattering of Light and Some of Its Observable Consequences*, Am. J. Phys. 1987
- OMM, Atlas international des nuages : [les étages](https://cloudatlas.wmo.int/en/useful-concepts.html), [accueil et photos](https://cloudatlas.wmo.int/en/home.html)
- AMS, glossaire, épaisseur optique des nuages : [page](https://glossary.ametsoc.org/wiki/cloud-optical-depth/)

**Données pour les bancs.**
- MODIS, fraction nuageuse mensuelle : [NASA SVS](https://svs.gsfc.nasa.gov/30397/), [NASA NEO](https://science.nasa.gov/earth/nasa-earth-observations-neo/)
- CALIPSO-GOCCP, fraction nuageuse 3D : [CFMIP-OBS](https://climserv.ipsl.polytechnique.fr/cfmip-obs/Calipso_goccp.html)
- ISCCP, types de nuages : [projet](https://isccp.giss.nasa.gov/projects/fieldvars.html), [ISCCP-H par type, ERDDAP](https://www.ncei.noaa.gov/erddap/griddap/iscpp_hgg_by_cloud_type.html)
- Photos de l'ISS : [Gateway to Astronaut Photography of Earth](https://eol.jsc.nasa.gov/)
- Blue Marble 2002 : [Earth Observatory](https://earthobservatory.nasa.gov/Features/BlueMarble/BlueMarble_2002.php)
