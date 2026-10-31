# Le son du vaisseau

**Le but :** un vaisseau qui s'entend. Le moteur suit la poussée demandée, les stabilisateurs soufflent quand on roule ou glisse, le vent monte dans l'atmosphère.

**L'état, 2026-10-29 :** en place, à juger en vol.
- **Le choix :** synthèse procédurale, jouée par XAudio2. Aucun fichier son, aucune dépendance.
- **Le code :** `MyPlanetEngine/Audio.h` et `Audio.cpp`. Un appel par image, `mAudio.Update(ShipSound)`, rempli dans `D3DApp::UpdateShip`.
- **Les voix :** le moteur, trois groupes de stabilisateurs (roulis, glissement latéral, montée et descente), le vent.

## L'état de l'art

**Les jeux de vol et d'espace :**
- **Star Citizen :** Wwise, après FMOD. Des boucles en couches pilotées par des paramètres ; le paramètre des propulseurs s'appelait encore « RPM ». Le moteur principal est baissé quand la surpropulsion parle ([Audio Update, 2015](https://robertsspaceindustries.com/comm-link/transmission/14853-Star-Citizen-Audio-Update)).
- **Elite Dangerous :** les modules montés changent le son du vaisseau, qu'on juge à l'oreille ([Jose Castro, Frontier](https://forums.frontier.co.uk/goto/post?id=176161)). Le son des moteurs suit la poussée demandée, pas la vitesse.
- **MSFS :** Wwise. Des boucles enregistrées à plusieurs régimes, fondues sur une « blend track » selon le RPM, avec une courbe de hauteur ([Engine Audio Setup](https://docs.flightsimulator.com/msfs2024/retail/sound/aircraft-audio/engine-audio-setup/)).
- **X-Plane 11 et 12 :** FMOD Studio, des événements pilotés par les datarefs ([Using FMOD with X-Plane](https://developer.x-plane.com/article/using-fmod-with-x-plane/)).
- **No Man's Sky :** Wwise, avec VocAlien, un greffon de synthèse des voix des créatures, et Pulse pour la musique ([Paul Weir, Audiokinetic](https://www.audiokinetic.com/en/blog/behind-the-sound-of-no-mans-sky-a-qa-with-paul-weir-on-procedural-audio) ; [GDC 2017](https://gdcvault.com/play/1024067/The-Sound-of-No-Man)).
- **Everspace 2 :** sons conçus aux synthés (Phase Plant, Vital, modulaire) puis joués en boucles ([Lukas Deuschel, Rockfish](https://everspace-game.com/rockfish-games-senior-sound-designer-lukas-deuschel-interview/)).
- **Le défaut connu :** un son lié à la vitesse plutôt qu'à la poussée. Les joueurs le relèvent ([Space Engineers 2](https://support.keenswh.com/spaceengineers2/pc/comments/93488/vote/toggle)).

**Les techniques du moteur piloté :**
- **Boucles fondues :** quelques boucles enregistrées à des régimes fixes, fondues et transposées selon le paramètre. La règle des simulateurs. Simple, mais la transposition s'entend et les boucles se répètent.
- **Granulaire :** des grains tirés d'un enregistrement en montée de régime, rejoués à la vitesse voulue. Pas de boucle audible. Crankcase REV et SoundSeed Grain, greffons payants de Wwise ([REV](https://www.audiokinetic.com/products/plug-ins/crankcase-rev/), [modélisation granulaire](https://www.audiokinetic.com/engine-sound-modeling-from-sampling-to-granular-synthesis-in-wwise)).
- **Synthèse procédurale :** le son comme un processus, bruits filtrés et oscillateurs. Le réacteur de Farnell : turbine et combustion ([Designing Sound, Practical 24](https://mitp-content-server.mit.edu/books/content/sectbyfn/books_pres_0/8375/designing_sound.zip/practical24.html)). Excellente pour les souffles, le vent, les jets de gaz ; plus difficile pour un moteur à pistons réel.

**Le middleware contre l'API nue :**
- **FMOD et Wwise :** outil auteur, mixage, paramètres en temps réel, greffons. Gratuits sous un plafond de budget, puis payants ; un SDK et un éditeur de plus.
- **XAudio2 nu :** livré avec Windows 10 et 11, dans le SDK. Voix, filtres, réverbération, spatialisation X3DAudio. Rien à écrire pour l'auteur, tout à écrire pour le son.

## Les bibliothèques de sons libres

- **Freesound :** des milliers de jets de gaz, souffles, réacteurs ; licences CC0, CC-BY, CC-BY-NC à trier une à une ([licences](https://freesound.org/help/faq/#licenses)). Téléchargement après connexion.
- **OpenGameArt :** CC0 et CC-BY surtout, qualité inégale ([sons de moteurs](https://opengameart.org/content/space-ship-engine-sounds)).
- **Sonniss GDC :** des dizaines de Go chaque année, libres de droits, usage commercial, sans attribution ; pas de redistribution des fichiers seuls, donc pas dans un dépôt public ([GDC 2024](https://gamefromscratch.com/sonniss-27-5gb-sound-effect-giveaway-at-gdc-2024/)).

## Les bibliothèques audio pour C++ sous Windows

- **XAudio2 :** natif, `xaudio2.lib` ; rien à ajouter au dépôt.
- **miniaudio :** un en-tête, domaine public ou MIT-0 ; décodeurs WAV, FLAC, MP3, graphe de nœuds ([miniaud.io](https://miniaud.io/)).
- **SoLoud :** zlib/libpng ; filtres, synthèse sfxr, sources multiples ([solhsa.com/soloud](https://solhsa.com/soloud/)).
- **OpenAL Soft :** LGPL, donc une DLL à livrer ; 3D et HRTF ([openal-soft.org](https://openal-soft.org/)).

## Le choix

**La règle :** le plus joli d'abord, puis le moins de dépendances.

- **La synthèse procédurale sonne mieux ici :**
  - **Le vaisseau est imaginaire,** aucun enregistrement n'en est la vérité. Les trois sons voulus sont des souffles : grondement, jets de gaz, vent. Les bruits filtrés les rendent bien.
  - **La plage de poussée est continue :** pas de boucle à transposer, pas de raccord entre régimes, pas de répétition.
  - **Chaque jet est différent :** filtre et durée tirés au hasard, sans banque de variantes.
- **Le moins de dépendances :** XAudio2, déjà dans Windows. Ni middleware, ni bibliothèque, ni fichier dans `assets/`.
- **Ce qui ferait changer d'avis :** un son mécanique précis, un démarrage ou un cliquetis de vanne. Alors un enregistrement CC0, chargé en WAV par XAudio2.

## La mise en œuvre

**Le flux :** une voix source XAudio2, 48 kHz stéréo en flottants. Le rappel `OnVoiceProcessingPassStart` calcule les échantillons demandés, sur le fil d'XAudio2. Le jeu ne passe que des cibles atomiques ; la synthèse les lisse, sans craquement.

**Le moteur :**
- **La poussée,** de 0 à 1 : le cran de la molette sur 30, à la puissance 2,5. Au 20ᵉ cran, 100 km/h près du sol, le moteur est au tiers ; à fond au 30ᵉ. La vitesse, elle, suit l'altitude jusqu'à celle de la lumière : le son ne suit que les gaz.
- **Les gaz seuls, pas l'accélération :** l'écart entre vitesse voulue et réelle, essayé d'abord, faisait gronder le moteur au premier cran et longtemps après les gaz coupés, le temps que le vaisseau ralentisse.
- **La réponse :** 0,25 s à la montée, 0,12 s à la coupure.
- **Trois couches :** un grondement de bruit brun, un bourdon à quelques harmoniques de 32 à 75 Hz qui ondule, un souffle de bruit blanc filtré dont la fréquence monte avec la poussée.
- **Au ralenti,** un ronron à peine audible reste.

**Les stabilisateurs :**
- **Un « pschit » à chaque pression,** puis un souffle tenu plus bas tant que la touche reste, et une queue de 80 ms au relâché.
- **Le bruit blanc passé haut,** fréquence tirée à chaque jet. Le roulis à gauche et à droite, le glissement du côté de la tuyère qui souffle ; la montée au centre.

**Le vent :**
- **La vitesse ramenée au niveau de la mer,** comme pour la verrière. Le volume lui est proportionnel : audible dès 30 km/h, net à 100 km/h, plein à 150 m/s. Comme dans la vraie vie, à 100 km/h le vent couvre déjà un moteur à faible régime.
- **Le volume suit la densité de l'air,** hauteur d'échelle 8 km : l'air rare porte peu le son. Il faut ce facteur : la vitesse croît avec l'altitude, et la vitesse ramenée au niveau de la mer restait forte à 50 km. Le vent s'éteint vers 30 km, quelle que soit la vitesse.
- **Un bruit passe-bande** qui monte en fréquence avec la vitesse, et des rafales lentes.

**La vue :**
- **En cockpit,** tout passe dans un passe-bas : on entend à travers la coque. Le grondement grave reste, le souffle est étouffé.
- **Dehors,** plein spectre.

**Les réglages :** les gains et fréquences sont en tête de `Audio.cpp`.
