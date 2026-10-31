# Recherche : le ciel nocturne

**Statut : un plan. Le ciel nocturne est fait sur la branche `etoiles`, tag `piste/etoiles`, le 2026-10-25 ; il n'est pas dans `main` et reste à intégrer.**

**Ce qui est fait, sur la branche :**
- les étoiles et les planètes en images de points, le seuil de l'œil, la Voie lactée, la lueur atmosphérique, l'exposition de nuit et les bâtonnets ;
- le code : `Stars.hlsl`, `StarsPixel.hlsl`, `Sky.hlsli`, `NightSky.hlsli`, `BrightStars.hlsli`, et des crochets marqués dans `Atmosphere.hlsli`, `AtmospherePass.hlsl`, `AtmosphereSkyIrradiance.hlsl`, `ToneMap.hlsl`, `D3DApp.cpp` ;
- les mesures : `tools/banc_etoiles.py`, les vues `tools/tests/2026-10-25-etoiles.txt`, l'entrée du 2026-10-25 de `journal-planete.md` ;
- trois règles de `principes.md`, sur la branche seulement : le ciel est de la lumière, pas un décor ; la nuit reste la nuit ; une table résout la fonction qu'elle porte.

**Pour l'intégrer :**
- la branche part du `jalon/18-lumiere` : avant la mer FFT, les nuages planétaires, la végétation détaillée et le vaisseau ;
- dans le jeu, l'air est intégré par la composition des nuages (`spec-nuages.md`, `Clouds.hlsli`) : la lueur atmosphérique et la lumière des étoiles sur le sol y sont à reporter, à vérifier à l'intégration ;
- ses règles vont dans `principes.md`, ses réglages dans le tableau de `journal-planete.md`.

**Ce qui reste,** d'après le journal de la branche :
- le crépuscule de 0° à -6°, 1,7 à 4 fois trop clair, et la lumière zodiacale, absente ;
- les catalogues, à télécharger sur demande, section 7 ; pas de Lune ;
- le ciel de nuit à l'écran et le crépuscule, à juger en vol.

## Conclusion

- **Une étoile est l'image d'un point.** Sa lumière, une magnitude rapportée à celle du Soleil, va aux pixels que couvre son image, chacun sa part : la règle du disque solaire. Pas de géométrie : 65 536 quads d'un seul dessin, calculés dans le vertex shader.
- **L'œil décide de ce qu'on voit.** Le seuil de Schaefer (1993) contre la luminance du ciel derrière l'étoile : aucune le jour, les plus brillantes d'abord au crépuscule, jusqu'à la magnitude 6,6 à 7 la nuit, selon le ciel. Aucun fondu ajouté : seule la luminance du ciel compte.
- **L'air agit par sa transmittance,** celle de la table de l'atmosphère : extinction et rougissement près de l'horizon.
- **La Voie lactée est la lumière des étoiles trop faibles pour être des points.** Sa moyenne vient des comptes d'étoiles, sa forme des comptes par latitude galactique ; ses nuages, d'un bruit, en attendant une carte du ciel.
- **La nuit a sa lumière.** La lueur atmosphérique, émise dans la marche du ciel, et la lumière des étoiles. Le sol la reçoit par la table d'éclairement du ciel : 6e-4 lux, contre 1e-3 lux publié avec la lumière zodiacale, absente.
- **L'exposition suit le posemètre, qui lit la nuit.** La clarté que l'œil donne à une scène baisse avec la lumière (Krawczyk 2005) : -4,5 IL la nuit par rapport au jour. Les bâtonnets voient sans couleur ce qui est sombre ; les étoiles gardent la leur.
- **Les planètes suivent les éphémérides de JPL,** à la date que donne la place du Soleil, en 2026.
- **Pas de scintillation :** à 60 images par seconde, elle se lit comme un défaut.
- **Catalogue :** 320 étoiles écrites ici jusqu'à 3,5, puis un champ procédural fidèle aux comptes. Fichiers souhaités en fin de document.

## 1. Comment font les autres

**Jensen et al. 2001, « A Physically-Based Night Sky Model » (SIGGRAPH), la référence la plus complète.**
- Le catalogue Yale Bright Star, environ 9 000 étoiles, position, magnitude et couleur.
- Une image d'étoiles à part, multipliée par une image de transmittance de l'atmosphère, puis ajoutée au rendu.
- Photométrie : E = 10^(0,4 (-m - 19)) W/m², soit 2,5e-8 W/m² pour m = 0.
- Couleur : température tirée de B-V, puis spectre de Planck.
- Forme des étoiles : un filtre d'éblouissement (Spencer 1995).
- Voie lactée : une mosaïque photographique de 14 400 × 7 200, étoiles brillantes retirées.
- Lumières diffuses : lumière intégrée des étoiles constante, lumière zodiacale en table, lueur atmosphérique en couche active à 80 km.
- Rendu pour l'œil : opérateur de Ward pour la vision scotopique, et un décalage vers le bleu.

**Stellarium (code ouvert, `StelSkyDrawer`).**
- Chaque magnitude donne un rayon et une luminance à l'écran.
- La magnitude limite dépend du champ, de l'adaptation de l'œil et des paramètres des sources ponctuelles ; extinction et scintillation en option.

**Celestia.** Des disques gaussiens dont l'aire croît avec l'éclat, saturés au centre (forum des développeurs).

**SpaceEngine.** Un menu règle l'exposition et la magnitude limite (manuel). Pas de détail public sur le rendu.

**Microsoft Flight Simulator.** Catalogue réel et planètes. Les retours d'utilisateurs reprochent trop d'étoiles et une Voie lactée trop vive. Pas de source primaire sur la méthode.

**Elite Dangerous, Star Citizen.** Le fond de ciel d'Elite vient de sa galaxie simulée (Stellar Forge) ; rien de publié sur sa photométrie. Rien trouvé pour Star Citizen.

**Unreal, Sky Atmosphere.** Rien sur les étoiles dans ce qu'on a pu lire : l'usage est un dôme de ciel texturé, sans photométrie (tutoriels).

**Ce qu'on retient.**
- La structure de Jensen : une couche d'étoiles à part, la transmittance de l'air, un catalogue et la photométrie des magnitudes.
- De Stellarium : une magnitude limite qui vient de l'œil, pas d'un réglage.
- De Celestia et des photos : une image qui grandit avec l'éclat. Sans elle, toute étoile plus brillante que 6 donne le même pixel blanc.

## 2. La photométrie

**Une seule échelle, celle du Soleil.** Une magnitude m éclaire de E = E☉ 10^(-0,4 (m - m☉)), m☉ = -26,74 en V, E☉ = π dans les unités du moteur. Le zéro de Schaefer, un pied-bougie pour la magnitude -16,57, donne 1,26e5 lux au Soleil et 2,5e-6 lux à m = 0, comme Jensen.

**La couleur.** B-V donne la température (Ballesteros 2012), puis le rapport des lois de Planck de l'étoile et du Soleil aux trois primaires, de luminance 1. Le Soleil, B-V = 0,65, reste blanc ; Bételgeuse est orange, Rigel bleutée.

**L'image d'un point.**
- Un point dans un seul pixel ne tremble pas, mais toutes les étoiles visibles y saturent : à deux fois le seuil de l'œil, une étoile vaut déjà treize fois le ciel de son pixel.
- On prend donc l'image qu'en fait une optique : le profil de Moffat (1969), (1 + r²/a²)^-β, celui des images d'étoiles, β = 3, large de 2 pixels à mi-hauteur, le plus étroit sans repliement.
- Chaque pixel prend la part de l'image qu'il couvre, moyenne de quatre points. L'image s'étend tant qu'elle dépasse une étoile au seuil ; sa part au-delà est rendue au reste.
- Les étoiles brillantes paraissent plus larges, comme sur une photo ou à l'œil.

**Le lissage temporel.** Il étalerait les quelques pixels d'une étoile qui glisse. Les étoiles ont leur couche, ajoutée après lui par la courbe de tons.

**Les 8 bits de l'écran.** Le ciel de nuit est un dégradé lent et sombre : arrondi au niveau, il se coupe en paliers visibles. Un demi-niveau de bruit, fixe sur l'écran, avant l'arrondi (bruit à gradient entrelacé, Jimenez 2014) les efface.

## 3. Catalogues et Voie lactée

**Les catalogues.**
- **Yale Bright Star, 5e édition (Hoffleit et Warren 1991) :** 9 110 étoiles, complet vers 6,5 ; J2000, V, B-V. Le CDS le diffuse (V/50) ; 574 ko compressé.
- **Hipparcos (ESA 1997) :** 118 218 étoiles, complet vers V = 7,3 à 9.
- **Tycho-2 :** 2,5 millions d'étoiles, jusqu'à 11,5.
- **Gaia :** plus d'un milliard d'étoiles ; seuls des extraits sont utilisables.
- Au-delà de la magnitude 8, aucun œil ne voit d'étoile isolée : le BSC suffit pour les points, et la Voie lactée prend le reste.

**Ce qui est fait sans téléchargement.**
- **Les étoiles brillantes, écrites ici :** 320 étoiles, complètes à 3,0 (169 contre 171) et à 95 % à 3,5, plus les Pléiades, la Petite Ourse, la Clé de voûte d'Hercule, la Lyre et le Dauphin.
- **Le champ procédural, de 3,5 à 8 :** les comptes de tout le ciel par magnitude (Sunspot 1997 : 4 800 à 6, 9 100 à 6,5, 42 000 à 8). La k-ième étoile prend la magnitude de son rang : les nombres sont exacts par construction.
- **Sa latitude galactique :** les comptes d'Allen à 7, 0,407, 0,170 et 0,107 étoile par degré carré à 0, 30 et 90°.
- **Sa couleur :** la répartition des B-V du BSC, par déciles.
- **La Voie lactée :** la lumière des étoiles plus faibles que 8, intégrée sur les comptes jusqu'à 40, plus 30 % de lumière diffusée par la poussière (Leinert 1998 ; Jensen 2001). Sa moyenne : 22,6 mag/arcsec² ; 24,0 aux pôles galactiques, 21,4 dans le plan, comme mesuré.
- **Sa forme :** un disque large et une bande étroite de 11°, d'après les comptes d'Allen de la lumière des étoiles faibles ; plus claire vers le centre galactique ; nuages et bandes sombres d'un bruit de gradient log-normal de moyenne 1.
- **Sa limite :** elle ressemble à une Voie lactée, pas à la nôtre. La carte de la NASA la remplace.

## 4. Les planètes

**Le choix : les vraies, à une date tirée du Soleil.**
- **Pourquoi :** le ciel est celui de la Terre, mêmes constellations, sur une planète de son rayon et de son air. Les vraies configurations sont justes d'elles-mêmes : Vénus jamais à plus de 47° du Soleil, Mercure près de lui. Elles ne coûtent aucune donnée.
- **Une position fixe** d'un système imaginaire aurait été plus simple, mais rien n'aurait dit où la placer.
- **La date :** la déclinaison du Soleil, sa latitude subsolaire, donne sa longitude écliptique, puis la date en 2026 ; on prend la branche du solstice de décembre à celui de juin.
- **Les orbites :** les éléments képlériens de JPL (Standish, table 1, 1800 à 2050), Kepler par Newton, dans le vertex shader.
- **Les magnitudes :** celles de l'Astronomical Almanac (Meeus, chapitre 41), selon la distance et l'angle de phase. Les anneaux de Saturne, par la tranche en 2025 et 2026, ne comptent pas.
- **En juin 2026,** Vénus (-4,0), Jupiter et Mercure brillent à l'ouest après le coucher ; **en décembre,** Vénus (-4,5) est l'étoile du matin, Jupiter et Mars sont hauts à minuit.
- **Pas de Lune :** le projet n'en a pas.

## 5. La visibilité

**Les crépuscules (American Meteorological Society, glossaire).**
- **Civil, jusqu'à -6° :** l'éclairement horizontal passe de 410 à 585 lux au coucher à 2 à 3,5 lux.
- **Nautique, jusqu'à -12° :** 0,008 lux à la fin.
- **Astronomique, jusqu'à -18° :** 6e-4 lux, la nuit.

**La magnitude limite (Schaefer 1993, Vistas in Astronomy 36 ; son programme, Sky & Telescope, mai 1998).**
- La loi de Hecht : le plus faible point vu contre un ciel de luminance B éclaire de I = c1 (1 + √(c2 B))², I en pieds-bougies, B en nanolamberts.
- **Bâtonnets,** sous 1 500 nL : c1 = 10^-9,8, c2 = 10^-1,9. **Cônes,** au-dessus : c1 = 10^-8,35, c2 = 10^-5,9. On prend le plus sensible des deux : la loi reste continue.
- **Repères :** un ciel noir donne 7,9 ; un ciel de nuit de 21,9 mag/arcsec² (54 nL), 6,6 ; un ciel de jour, -4, Vénus au mieux.
- **Son modèle de ciel** sert de témoin : le crépuscule perd 0,4 magnitude par degré.

**Ce que le moteur fait.**
- Chaque étoile compare sa lumière, après l'air, au seuil que donne le ciel derrière elle, lu dans l'image composite : diffusion, lueur atmosphérique, Voie lactée, halo.
- **L'œil ne voit que l'excès.** Une étoile au double du seuil garde la moitié de sa lumière ; sous le seuil, rien. La transition reste continue.
- **La physique décide :** pas de fondu selon l'heure. Le seuil suit la luminance du ciel, le reste suit la transmittance.

**La scintillation.**
- Elle est réelle : environ 25 % d'écart à l'œil au zénith, bien plus près de l'horizon (Young 1967 ; Dravins et al. 1997), à 10 à 100 Hz.
- Pas retenue : sur des images de 2 à 4 pixels à 60 images par seconde, elle se lit comme un tremblement, ce que le banc interdit.
- Possible plus tard, lente et réservée à l'horizon.

## 6. La lumière de la nuit

**Ses parts (Leinert et al. 1998 ; Jensen 2001).**
- **La lueur atmosphérique :** raie verte de l'oxygène à 557,7 nm (environ 250 R), bandes OH, sodium, continuum ; une couche vers 85 à 100 km.
- **La lumière zodiacale :** le Soleil diffusé par la poussière interplanétaire.
- **La lumière intégrée des étoiles,** et celle que diffuse la poussière galactique.
- **Le ciel naturel au zénith,** au minimum solaire : V = 21,9 à 22,0 mag/arcsec², B = 22,7, R = 21,0 (Hänel et al. 2018 ; La Palma).
- **Le sol sans Lune :** environ 1e-3 lux, 6e-4 à la fin du crépuscule astronomique. La pleine Lune donne 0,05 à 0,3 lux.

**Ce que le moteur fait.**
- **La lueur atmosphérique est une émission du milieu,** dans la marche de `IntegrateScattering` : une couche en sech² à 90 km, 7 km à mi-hauteur. Chaque pas en prend la moyenne exacte, comme la brume.
- **Sa luminance au zénith, hors de l'air :** 22,4 mag/arcsec², le ciel naturel moins la lumière zodiacale et celle des étoiles. Sa couleur : B-V = 0,8, celle du ciel mesuré.
- **Il en vient tout seul :** l'éclaircissement vers l'horizon (van Rhijn), le rougissement près de l'horizon, la ligne du limbe vue d'orbite, la lumière qui tombe sur le sol par la table d'éclairement.
- **La lumière des étoiles sur le sol :** la moyenne de toutes, points et Voie lactée, répartie sur le ciel, dans la même table.
- **Il manque la lumière zodiacale :** environ 20 à 30 % de la nuit.

**L'œil et l'appareil la nuit.**
- **L'adaptation (CIE 191:2010) :** vision photopique au-dessus de 5 cd/m², mésopique de 0,005 à 5, scotopique en dessous.
- **Purkinje :** la sensibilité passe de 555 nm à 507 nm.
- **Les couleurs disparaissent,** l'acuité tombe vers un dixième sous les étoiles. Le « bleu de la nuit » des films est une convention (Thompson et al. 2002) ; pas retenu.
- **Un posemètre incident** lit 1e-3 lux sous les étoiles, IL100 = -11 : il ferait de la nuit un jour.
- **Les astrophotographes exposent environ 5 IL en dessous :** 20 s, f/2,8, ISO 3 200, soit IL100 = -6,3.
- **La clarté que l'œil donne à une scène :** la clé de Krawczyk, Myszkowski et Seidel (2005), 1,03 - 2 / (2 + log10(L + 1)), L la luminance d'adaptation en cd/m². Elle vaut 0,69 sous le Soleil de midi, 0,12 à la fin du crépuscule civil, 0,03 la nuit : -4,5 IL, comme les astrophotographes.
- **Le choix :** le posemètre lit le crépuscule et la nuit ; l'exposition le suit, multipliée par la clé de l'œil rapportée à celle de midi. Le jour change à peine : -0,07 IL à 10° de hauteur, -0,15 à 5°, -0,45 au coucher ; puis -1,3 IL à -4°, -2,5 à -6°, -4,5 dès -12° (posemètre de midi : 1,13e5 lux).
- **Les bâtonnets :** ce qui est sombre, pour un œil adapté au sombre, perd sa couleur, sa luminance gardée. Leur part va de 0 à 5 cd/m² à 1 à 0,005 cd/m², selon le plus clair du pixel et de l'adaptation. Le rougeoiement d'un crépuscule garde donc sa couleur, le ciel de nuit devient gris ; les étoiles gardent la leur.

## 7. À télécharger, sur demande

- **Le Yale Bright Star Catalogue, 5e édition révisée, préliminaire :** `https://cdsarc.cds.unistra.fr/ftp/V/50/catalog.gz`, 573 921 octets, 9 110 étoiles. Le CDS demande de citer la source ; pas de licence explicite dans le `ReadMe`. Il remplacerait `BrightStars.hlsli` et le champ procédural jusqu'à 6,5.
- **La Voie lactée de la NASA, « Deep Star Maps 2020 » :** `https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/milkyway_2020_4k.exr`, 4 096 × 2 048, 34,7 Mo, fond sans les étoiles brillantes de Hipparcos et Tycho, en coordonnées équatoriales. Crédit : NASA/Goddard Space Flight Center Scientific Visualization Studio ; Gaia DR2 : ESA/Gaia/DPAC. Pas d'étalonnage publié : on le caserait sur la moyenne et le profil galactique d'ici.
- **En option, la lumière zodiacale :** la table de Leinert et al. 1998, au CDS (J/A+AS/127/1), quelques ko.

## Sources

- Jensen, Durand, Stark, Premože, Dorsey, Shirley, « A Physically-Based Night Sky Model », SIGGRAPH 2001.
- Schaefer, « Astronomy and the limits of vision », Vistas in Astronomy 36, 1993 ; « To the visual limits », Sky & Telescope, mai 1998, programme repris par L. Bogan (bogan.ca/astro/optics/vislimit.html).
- Leinert et al., « The 1997 reference of diffuse night sky brightness », A&AS 127, 1998.
- Hänel et al. 2018, cité par « Natural Night Sky Brightness during Solar Minimum », arXiv:2105.01066.
- Allen, Astrophysical Quantities, comptes d'étoiles par latitude galactique (repris par l'Isaac Newton Group, WEAVE).
- Comptes de tout le ciel : Sunspot Solar Observatory 1997, repris par Wikipédia, « Apparent magnitude ».
- Standish, « Keplerian Elements for Approximate Positions of the Major Planets », JPL ; Meeus, Astronomical Algorithms, chapitre 41.
- Ballesteros, « New insights into black bodies », EPL 97, 2012.
- Moffat, « A theoretical investigation of focal stellar images », A&A 3, 1969.
- Krawczyk, Myszkowski, Seidel, « Lightness perception in tone reproduction for high dynamic range images », Eurographics 2005.
- CIE 191:2010, photométrie mésopique ; Thompson, Shirley, Ferwerda, « A spatial post-processing algorithm for images of night scenes », 2002.
- American Meteorological Society, Glossary of Meteorology : civil, nautical, astronomical twilight.
- Young 1967, Astronomical Journal 72 ; Dravins, Lindegren, Mezey, Young, PASP 109, 1997 : scintillation.
- NASA SVS 4851, Deep Star Maps 2020 ; CDS V/50, Bright Star Catalogue.
