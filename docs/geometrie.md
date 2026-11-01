# La géométrie : le relief et ses surcouches

Statut : référence, depuis le 2026-10-23. Complète `principes.md`, qui y renvoie.

## La règle

**Le relief tectonique d'Exolune est la source de vérité de la géométrie,** depuis le 2026-10-31 (`spec-relief-tectonique.md`).

- **Les grandes formes, au-dessus de 50 km, viennent de la carte tectonique :** continents, marges, fosses, chaînes, plateaux, rifts et dorsales, mers étroites, calculés au démarrage (`Tectonics.cpp`), lus en B-spline et mis en profils (`Tectonics.hlsli`, `Relief.hlsli`).
- **Les côtes, de 60 à 3 km, se découpent par type de marge,** un bruit qui déplace le rivage d'une distance donnée : caps, baies, îles et rias sur les côtes raides, cordons et lagunes sur les plates.
- **Le détail, sous 50 km, vient du bruit de `Noise.hlsli`,** modulé par la géologie de la carte ; la plus large octave des chaînes en plis le long d'elles.
- **Du code original,** écrit en salle blanche depuis `recherche-relief.md`.
- **Avant :** du 2026-10-20 au 2026-10-30, le portage de l'exemple complexplanet de libnoise, commit `b7b8c76` et suivants ; le 2026-10-31, une réécriture originale de sa composition, commit `f00004d`. Il n'en reste rien.

- **L'apparence des matériaux se travaille dans le rendu :** couleurs, textures, normales des pixels, parallaxe, ombres. Un désert qui ressemble à un désert, une roche qui ressemble à de la roche, c'est d'abord un travail de rendu.
- **Toute modification de la géométrie est une surcouche,** inscrite dans le tableau ci-dessous avant d'être fusionnée.
- **Chaque surcouche donne :** sa famille, ses longueurs d'onde, son amplitude, où elle agit, son réglage d'arrêt et sa spec.

**Les trois familles de surcouches :**
1. **Filtrage :** la même composition, dont on retire ou arrondit ce que la maille ne peut pas porter. La forme reste celle du relief à l'échelle de la maille.
2. **Ajout de détail :** des longueurs d'onde que le relief n'a pas, sous sa plus fine octave, 13,5 m. Au-dessus, la forme reste la sienne.
3. **Remplacement :** la forme change à des échelles que le relief décide déjà. On s'éloigne de la composition d'origine.

**Un remplacement est un sujet à part :**
- une spec dédiée et une décision explicite ;
- une branche et un tag `piste/…` tant qu'il n'est pas décidé ;
- un réglage qui le ramène à 0.

## Les surcouches

| Surcouche | Famille | Échelle | Amplitude | Où | Arrêt | Statut |
|---|---|---|---|---|---|---|
| Octaves filtrées par maille | Filtrage | sous 2 mailles, `MESH_BAND_LIMIT` | octave remplacée par sa moyenne | partout | aucun, c'est l'échantillonnage | en place |
| Fréquences maximales du type de terrain et des turbulences | Filtrage | sous ~100 km et ~6 km | 0,13/255 à l'écran ; côtes de quelques mètres | partout | `NO_LIMIT` | retirée le 2026-10-31 avec l'ancien relief |
| Crêtes arrondies | Filtrage | 2 mailles, jamais sous des mailles de 2 m | creux et crêtes du billow et du ridged multifractal, et des chaînes du relief tectonique | partout | `CREASE_ROUNDING` = 0 | en place |
| Profils élargis | Filtrage | 2 mailles | fosses, vallées axiales, grabens, creux des transformantes, cordons des côtes plates : plus larges, moins profonds ou moins hauts, leur moyenne gardée | partout | aucun, c'est l'échantillonnage | en place depuis le 2026-10-31 |
| Profils franchissant la mer | Filtrage | partie émergée sur au moins 2 mailles, ou entièrement noyée | cordons, pointes et débordements compris : cœur aplati, amplitude abaissée, aire du profil conservée ; profil résolu inchangé | côtes plates ; aucun profil distinct de flèche, platier ou motu sur cette branche | maille nulle : profil original | 2026-10-31, `ReliefSeaProfile`, `spec-relief-tectonique.md` ; à juger en vol |
| Relief des matériaux | Ajout de détail, qui déborde | du centimètre jusqu'à la tuile de 64 m | centimètres à quelques mètres ; corniches de la tuile de 64 m au-dessus de 13,5 m | mailles de 8 m et moins | `MATERIAL_RELIEF`, retiré | désactivée le 2026-10-23, retirée du code le 2026-10-30 ; tag `piste/parois-gradins`, où elle est active ; `log/spec-relief-reel.md` |
| Parois en gradins | Remplacement | bancs de 10 à 60 m | jusqu'aux deux tiers de l'épaisseur d'un banc, soit 10 à 40 m | pentes raides, mailles de 16 m et moins | `WALL_RELIEF`, retiré | désactivée le 2026-10-23, retirée du code le 2026-10-30 ; tag `piste/parois-gradins` ; `log/spec-parois.md` |
| Filtre d'érosion | Remplacement | ravines de 366 m à 11 m | dizaines de mètres | toutes les pentes, mailles de 91 m et moins | `EROSION` = 0 | mis de côté, tag `piste/erosion-filtre` |
| Patchs de relief réel | Remplacement | 1 à 200 m | celle du lieu réel | non intégré | — | dalles IGN LiDAR HD dans `../donnees-terre/lidar-hd`, essai hors moteur inachevé |
| Objets de proximité | Ajout de détail, le détail du sol posé, cailloux et touffes, jamais la roche en place | 3 cm à 2 m | enfouis de 8 % sur la roche à 40 % dans un sol meuble ; le sol ne bouge pas | dans les régions caillouteuses seulement, une recette par sol : sable et sol nu, herbe, éboulis, pied des vraies parois ; par taches et par amas, sous l'angle de repos ; sous 6 pixels ou dans des mailles de plus de 1,5 fois leur largeur, rien | `PEBBLES`, `GRASS_ROCKS`, `DEBRIS_ABUNDANCE`, `TUFT_COVER` à 0 | piste, tag `piste/objets-proximite`, `spec-objets-proximite.md` |
| Plantes | Ajout de détail, des objets posés : arbres et arbustes, jamais une forme du relief | 0,5 à 64 m de haut | le sol ne bouge pas ; le tronc enfoui à 15 % de la hauteur ; au loin, le pied sur le sol du maillage, de près sur le sol exact ; entière ou absente, jamais grandissante | selon le climat, par régions et par taches, rares sur les crêtes ; ni sur la roche nue, ni sur les éboulis, ni sur la plage ; sous 5 à 8 pixels, la canopée dans la matière du sol, à la hauteur des arbres, sans déplacer un sommet | `MYPLANETENGINE_NO_PLANTS`, ou pas de catalogue | en place : la population de `piste/vegetation-v3`, dessinée par la végétation planétaire ; les plantes générées v1 à v3 retirées du code le 2026-10-30, tags `piste/vegetation`, `-v2` et `-v3` ; `recherche-vegetation.md` |
| Prototype de végétation détaillée | Ajout de détail, des objets posés ; représentation par maillage, imposteurs ou volumes | arbres de 12 m dans une parcelle de comparaison bornée ; volumes de 32³ à 128³ | le sol ne bouge pas ; les pieds suivent le maillage dessiné | parcelle déterministe attachée à une ancre planétaire ; mêmes poses dans les trois modes | `MYPLANETENGINE_FOLIAGE`, retiré | prototype isolé, clos ; retiré du code le 2026-10-30, tag `jalon/24-vegetation-detaillee-main` ; `log/prototype-vegetation-volumique.md` |
| Végétation détaillée planétaire | Ajout de détail, des objets posés ; maillage proche et imposteur lointain | hauteur et largeur des instances du peuplement existant ; imposteurs multivues, rectangles projetés sur leur support | le terrain ne change pas ; prolongement du bas du tronc proche sous le pied | même grille, climat et graines ; arbustes conservés | `MYPLANETENGINE_NO_PLANTS`, ou pas de catalogue | en place, `jalon/24-vegetation-detaillee-main` et `jalon/25-vegetation-performance-main` ; le volume 64³ lointain et les autres modes retirés du code le 2026-10-30, tag `piste/vegetation-relais-fondu` ; `vegetation-planetaire.md` |
| Volcans | Remplacement, sur une piste : des formes que le relief n'avait pas, de 120 km aux cônes de 0,5 km | arcs, chaînes de points chauds, rifts ; stratovolcans de 2 à 5 km, boucliers de 4 à 9 km au-dessus du fond, guyots, atolls, calderas, coulées de 15 à 40 m, cônes de 60 à 190 m ; houle des panaches, traps et plateaux océaniques dans la carte | autour des volcans listés au démarrage, 0,5 à 0,6 % de la surface ; tout profil sur deux mailles au moins | aucun réglage : sans volcanisme, le commit `d304da0` de `bruit-propre` | 2026-10-31, branche `claude/volcanisme-7c3aea`, tag `piste/volcanisme`, à juger en vol ; `spec-volcanisme.md` |
| Relief tectonique | Remplacement, décidé : c'est le relief | formes de plus de 40 km, deux texels de la carte tectonique ; les côtes de 60 à 3 km ; le bruit en dessous | continents, plateaux, chaînes de 6,9 à 7,6 km, fosses de −9,1 à −10,1 km, abysses vers −4,5 km ; côtes déplacées de 8 à 12 km | partout | aucun : l'ancien relief est au commit `f00004d` | étapes 1 à 3 du 2026-10-31, défauts corrigés le même jour : côtes par type de marge, rifts émergés et mers étroites, plis des chaînes en deux jeux qui se relaient ; leur soulèvement et leurs plis lus en double, sans murs au sol, le soulèvement en quintique ; le détail plus décalé le long des transformantes, les cordons le long du rivage lissé, en arcs entre des passes ; branche `bruit-propre`, à juger en vol ; `spec-relief-tectonique.md` |

**Modèles planétaires validés du 2026-10-27 :** ajout de détail aux objets posés, jalon `jalon/24-vegetation-detaillee-main`. Feuillu Rakshi Games enrichi à 7 010 triangles, pin evolveduk à 5 627 triangles, douze arbustes climatiques à 2 492–4 272 triangles. Feuilles découpées autour de rameaux maillés ; normales par bouquets et visibilités précalculées sans déplacement des sommets. Instances et portée conservées ; `vegetation-planetaire.md`.

**Arbustes climatiques :** six familles de deux formes ramifiées ; mêmes graines et positions, couronne de référence conservée, hauteur de silhouette adaptée au climat. Le terrain ne change pas. Le diagnostic de hauteur reprend la moyenne des familles ; le couvert lointain reste surfacique, sans parallaxe verticale précise. `arbustes-climatiques.md`. Les modèles antérieurs et leurs essais restent décrits dans `log/vegetation-planetaire-historique.md`.

**Surface d'eau du spike FFT :** surcouche spécifique, quatre cascades, amplitude du spectre JONSWAP et de la houle ; sommets sous la mer, amortis par la profondeur et filtrés par la maille. Le fond du relief est conservé. Déplacement et normale partagent leurs dérivées ; voir [spec-mer-fft-spike.md](spec-mer-fft-spike.md). Le premier noyau reste dans mer-animee.

**Ne sont pas des surcouches :**
- **La grille fine :** la même fonction, échantillonnée quatre fois plus fin, pour les normales des pixels.
- **La grille du bruit en paires de floats, en vol :** la même fonction ; le découpage de chaque octave sur la grille en deux floats, 48 bits, au lieu d'un double, sur les sommets qui glissent (`Noise.hlsli`, `optimisation.md`, round 8). Le point est le même à 2·10⁻⁸ m près ; seul le dernier bit d'une hauteur peut changer. Le sommet sous la caméra reste en doubles ; à l'arrêt, tout le maillage aussi.
- **La carte de la planète :** la même fonction sur un cube fixé sur la planète, 6 × 1 024², calculée au démarrage après la carte tectonique (`PlanetMap.hlsli`). De la donnée pour la brume et l'eau : elle ne déplace aucun sommet.
- **La carte tectonique :** elle fait partie du relief, elle n'en est pas une surcouche.
- **La parallaxe :** une illusion dans les pixels, sans changement de géométrie.
- **Le grain fin des pixels :** les octaves du relief que la maille ne porte pas, dessinées dans la lumière.

## La voie géométrie, à part

Ouverte le 2026-10-23, à reprendre après le rendu. **La géométrie de proximité y attend :** le relief des matériaux et les gradins, désactivés le 2026-10-23, sont retirés du code le 2026-10-30 ; tag `piste/parois-gradins`. Le rendu du relief passe d'abord au plus près du photoréalisme. Elle surgissait dans les derniers mètres, signe qu'elle n'est pas encore bien intégrée à la génération par bruits. La question : comment affiner le relief sous ses échelles, et par quoi ? Elle se posait alors sur complexplanet ; elle se pose désormais sur le relief tectonique.
- **Des bruits ou des algorithmes :** le filtre d'érosion, `spec-parois-minerales.md`.
- **Du relief réel :** des patchs lidar fondus par nos bruits.
- **Des objets :** des rochers semés en vrais volumes, `log/spec-parois.md`, option 3. Ouverte le 2026-10-24 pour les pierres et les blocs : `spec-objets-proximite.md`.


**2026-11-01 · Manufactured ship geometry**

- **Classification:** added detail on a manufactured asset, outside the terrain-overlay system.
- **Scope:** fitted console panels, curved console returns, integrated dashboard recesses, curved coaming, rolled foredeck, glazing retainer, seat upholstery, service fittings and identification plates.
- **Scale:** 1.5 mm recessed instrument faces, 10–28 mm pockets, a 34 × 12 mm glazing retainer and 4 mm seal.
- **Panel outlines:** seven custom skins follow their support contours with 7–12 mm margins and chamfered corners.
- **Dashboard curve:** the centre stays at 0.845 m; the shoulders lower by 35 mm along the dashboard plane.
- **Console junction:** a 65 mm lateral return meets the dashboard and the flat console bay at d = 3.84 m with tangent cubic sections.
- **Foredeck:** shoulder relief rises smoothly to at most 220 mm and fades before d = 3.8 m; the forward centreline lowers by at most 18 mm, fading before d = 2 m.
- **Sightline:** five eye positions cover the nominal eye, ±30 mm sideways and ±60 mm fore/aft; the camera settings are unchanged.
- **Attached details:** hull paint is regenerated from the new sections; the top and side forward attitude jets follow the revised skin.
- **Glass:** unchanged analytic shape, tessellated at 64 × 52 for the thinner retainer.
- **Reference frame:** the ship; no change to Exolune relief, planetary meshes or terrain settings.
- **Source:** `assets/vaisseau/forme_chasseur.py`, `cockpit_chasseur.py`, `panneaux_cockpit.py`, `encastrements.py`, `cadre_verriere.py` and `finitions_cockpit.py`.
- **Return point:** `piste/2026-11-01-vaisseau-finitions-base` (`ad981f4`); current edits remain on `codex/vaisseau-finitions`.
- **Specification:** [ship assembly](spec-vaisseau.md).
