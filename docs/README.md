# Documentation

**Ce dossier ne garde que ce qui est d'actualité :** la vision, les règles, les systèmes en place et les plans à venir. Ce qui ne l'est plus passe dans `log/`.

## Les références

- **`concept.md` :** la face de cube qui suit la caméra, recalculée à chaque image.
- **`principes.md` :** on corrige des règles, pas des cas. Ce fichier fait référence.
- **`geometrie.md` :** la géométrie vient du relief tectonique d'Exolune ; ses surcouches, classées.
- **`journal-planete.md` :** l'historique des réglages, les jalons et les pistes taguées.
- **`lancement.md` :** lancer l'app pour juger en vol ; les assets à construire dans une worktree neuve, les variables du lanceur, les touches.

## Les systèmes en place

**Le terrain et ses matériaux**
- **`spec-rendu-lointain.md` :** la même planète de l'orbite au sol, la règle universelle des limites.
- **`spec-normales-spline.md` :** les normales par pixel en B-spline.
- **`spec-textures-generees.md` :** les tuiles des matériaux, générées au démarrage, et leur pavage ; la roche est une photo depuis le 2026-10-24.
- **`spec-texturage-universel.md` :** l'échelle de détail de chaque matériau, du texel au kilomètre, et le banc de qualité qui la vérifie ; étape 3 en cours.
- **`spec-photos-par-echelle.md` :** des photos réelles recomposées par nos bruits ; la palette des biomes et les sols photo faits, les motifs vus d'avion repris par le texturage universel.
- **`spec-roche-organique.md` :** la colonne stratigraphique en couleur, ses lentilles, les replats ; ses familles de roche, retirées le 2026-10-24.
- **`spec-parois-minerales.md` :** les parois de 100 m à 1 km : la photo de paroi et les strates au pixel.
- **`spec-objets-proximite.md` :** le détail du sol près de la caméra, cailloux, rochers et touffes d'herbe, à place fixe sur la planète, sans pop ; `jalon/19-detail-sol`.

**La lumière et l'air**
- **`recherche-tons-exposition.md` :** l'exposition réglée sur l'éclairement, la courbe de tons ; état de l'art, choix, mesures contre des photos.
- **`recherche-ombres-relief.md` :** les ombres portées du relief, horizon par sommet ; le ciel caché reste à faire.
- **`recherche-rayons.md` :** les rayons de soleil, l'air à l'ombre du relief, par la marche des ombres portées.
- **`recherche-profondeur-atmospherique.md` :** la distance par l'air, voile, brume basse, visibilité ; la brume de la couche limite, sur le sol régional.
- **`recherche-halo.md` :** le halo de l'objectif autour du soleil et de la neige, la loi en 1/θ² et sa mesure ; piste `piste/halo-optique`.
- **`spec-rendu-orbite.md` :** la planète vue d'orbite face à Apollo 17 : la diffusion multiple des aérosols par similitude, la lumière des nuages calée sur Monte-Carlo, leur eau indépendante de la couverture, la statistique du pixel à la place des rayons fins, l'exposition d'orbite ; piste `piste/orbite-rendu`, à juger en vol.
- **L'air du jeu passe par la composition des nuages** (`spec-nuages.md`) : rayons et brume du sol régional y sont rendus le 2026-10-30, à juger en vol ; le halo est coupé par défaut.

**La mer, les nuages et la végétation**
- **`spec-mer-fft-spike.md` :** mer FFT, normales et écume persistante, intégrées à main ; limites physiques et raccord au vent planétaire documentés.
- **`spec-nuages.md` :** les nuages du jeu, de l'orbite au sol : le modèle, les passes, les ressources, les données et leur provenance, les défauts connus ; leur ombre sur la terre et la mer ; leur carte météo tirée du climat depuis le 2026-10-31.
- **`recherche-vegetation.md` :** arbres, arbustes et forêts de l'orbite au sous-bois ; état de l'art ; le climat, le placement et la canopée au sol en place ; les plantes générées v1 à v3, retirées le 2026-10-30, au log.
- **`vegetation-planetaire.md` :** arbres et arbustes du jeu, le seul feuillage, actif par défaut ; maillages proches et imposteurs lointains, population déterministe ; bouquets foliaires, éclairage précalculé.
- **`arbustes-climatiques.md` :** douze formes réparties entre six familles climatiques ; mêmes instances et portée, sous-plages GPU partagées.
- **`vegetation-hiz.md` :** pyramide de profondeur courante et masque GPU pour les imposteurs entièrement cachés ; peuplement et ordre de dessin conservés.
- **`optimisation-vegetation.md` :** le culling et les temps GPU de la végétation, à aspect, densité et distance conservés ; la mémoire reste à optimiser.

**Le vaisseau et l'exécution**
- **`spec-vaisseau.md` :** le vaisseau du joueur, son cockpit, son pilotage clavier-souris et la météo sur sa verrière.
- **[Ship assembly history](log/spec-vaisseau-historique.md):** former mounting rules, panel layouts, junctions, foredeck profile and intermediate asset counts.
- **`recherche-eau-verriere.md` :** l'eau sur la verrière, gouttes, filets et film en vol ; état de l'art ; gouttes simulées et leurs traînées en place, à juger en vol.
- **`recherche-son.md` :** le son du vaisseau, moteur, stabilisateurs et vent ; état de l'art, choix de la synthèse procédurale sur XAudio2, en place à juger en vol.
- **`execution-optimisee.md` :** exécutable Release avec profil local, plein écran sans bordure, résolution au démarrage et présentation libre optionnelle.

## Les plans

- **`spec-relief-tectonique.md` :** le relief du jeu depuis le 2026-10-31 : une carte tectonique calculée au démarrage, continents, plaques et frontières ; les grandes formes en profils, le détail modulé par la géologie ; le portage CPU par un cache ; étapes 1 à 3 faites, à juger en vol.
- **`spec-climat.md` :** le climat du jeu depuis le 2026-10-31 : vents des trois cellules, vapeur portée depuis les mers, pluie au vent des reliefs et ombre pluviométrique, continentalité, courants froids, calculés au démarrage sur la forme tectonique ; la carte lue par les matériaux, les plantes, la mer et le vaisseau, et par le portage pour l'érosion ; étape 1 faite, à juger en vol.
- **`spec-volcanisme.md` :** les volcans déduits de la carte tectonique, listés au démarrage et évalués point par point : arcs, points chauds et leurs chaînes, atolls et guyots, rifts, calderas, coulées, cônes, traps ; basaltes et cendres ; piste `piste/volcanisme`, à juger en vol.
- **`recherche-relief.md` :** le relief planétaire, tectonique, érosion, bruits érodés et jeux ; les licences ; l'architecture en quatre couches et le plan qui fondent la spec.
- **`optimisation.md` :** 60 fps au minimum en 1080p, 120 visées, à qualité perçue conservée ; le banc de performance, la référence et les rounds.
- **`recherche-nuages.md` :** la couverture nuageuse, carte du temps, types et rendu de l'orbite au sol ; état de l'art et plan ; l'ancien volume est au log.
- **`recherche-mer.md` :** la mer et les lacs ; état de l'art et lois de référence ; la côte et les lacs restent à faire.
- **`recherche-cotes.md` :** plages, falaises et rivages ; audit de complexplanet à la côte, état de l'art et plan ; étape 1 portée sur la mer FFT, la plage à la distance de l'eau ; étape 2 sur la branche `plages`, à porter.
- **`recherche-rivieres.md` :** rivières, fleuves et lacs de montagne ; audit des vallées de complexplanet, état de l'art et plan ; étape 1, la carte de la planète, faite ; les spikes du 26 et 27 octobre au log ; la recherche continue sur la branche `erosion-niveaux`.
- **`recherche-ciel-nocturne.md` :** étoiles, planètes, Voie lactée, lueur atmosphérique, l'œil la nuit ; fait sur la branche `etoiles`, à intégrer.
- **`recherche-geometrie-proximite.md` :** corniches et relief au mètre près de la caméra, sans surgir ni trembler ; état de l'art et plan, rien de décidé.

## Le log

**`log/` garde ce qui n'est plus d'actualité,** pour mémoire : specs closes, remplacées ou désactivées, recherches anciennes, sections dépassées des specs vivantes. Voir `log/README.md`.
