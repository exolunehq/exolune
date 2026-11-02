# Spec : l'érosion globale

Statut : spec vivante, depuis le 2026-10-31, branche `erosion-globale`, piste `piste/erosion-globale`. Elle part de la pile tectonique (`spec-relief-tectonique.md`) ; la recherche de la branche `erosion-niveaux` n'est qu'une source (section « Ce que la recherche a appris »). Parcours courant : `tools/tests/2026-11-01-auges.txt` ; les étapes précédentes restent dans `tools/tests/2026-10-31-erosion.txt`.

## L'objectif

**Les fleuves et les glaciers forment un seul système, de la planète au détail de 100 m.** Les chaînes montrent des vallées transverses ramifiées, des arêtes, des contreforts et une ligne de partage continue ; les plis restent en avant-pays ; tous les fleuves atteignent la mer ou un lac.

## L'architecture

**Trois niveaux, un seul réseau.** Le niveau 0 décide où va l'eau et à quelle hauteur ; les vallées et les ravines n'en sont que le dessin, de plus en plus fin, accroché à lui.

| Niveau | Échelles | Où, quand | Ce qu'il fait |
|---|---|---|---|
| 0, le réseau | nœuds à 20 km ; formes au-dessus de 40 km | CPU, au démarrage, sur la grille de la carte tectonique ; cache par graine | drainage vers la mer, lacs par bilan d'eau, niveau de l'eau par puissance fluviale, débit, glace, cônes et deltas |
| 1, les vallées du réseau | de 40 km à la largeur du lit | shader, par point (`Erosion.hlsli`) | chaque lien creuse sa vallée dans le sol grossier : fond au niveau de l'eau, versants à la pente de seuil, en U sous la glace ; deltas et cônes |
| 2, les ravines | de 11 km à 100 m | shader, dans les octaves du détail (`Relief.hlsli`) | les octaves réorientées le long de la pente du relief au-dessus d'elles : chaque ravine descend vers la vallée qui la porte |

**Pourquoi ce partage :**
- **Le niveau 0 est global :** un fleuve dépend de la mer et de tout l'amont. Il se calcule une fois, au démarrage, comme la carte tectonique.
- **Les niveaux fins sont locaux et déterministes :** une érosion simulée par tuiles est chaotique et coud mal (recherche, spike B). Une vallée ne lit que les liens du niveau 0 autour d'elle ; une ravine, la pente des octaves au-dessus d'elle.
- **Rien ne se calcule en route :** les niveaux 1 et 2 sont des fonctions du point, comme le bruit ; le niveau 0 est en mémoire dès le départ.
- **Un arbre explicite à plusieurs niveaux, à la Dendry, est écarté :** chaque nœud fin doit connaître les liens plus grossiers autour de lui, et ainsi de suite ; par sommet, le coût croît comme 9 puissance le nombre de niveaux.

## Le niveau 0, `Erosion.cpp`

**La grille :** celle de la carte tectonique, 6 × 512², environ 20 km. Le soulèvement et l'érodabilité s'y lisent sans interpolation.

**Les entrées :**
- **la forme avant érosion,** `ReliefElevation(p, false)` filtrée à deux mailles, calculée au démarrage sur le GPU au centre de chaque cellule (`ErosionForm.hlsl`) ;
- **le soulèvement U et l'érodabilité K,** tranches 3 et 4 de la carte tectonique, gardées en mémoire jusque-là ;
- **les précipitations P et la température T,** par `ErosionClimate`, lecture bilinéaire continue de `Climate::At` sur la carte CPU gardée depuis `CreateClimateMap`.

**Le calcul :**
1. **Le drainage :** un Priority-Flood depuis la mer donne la surface comblée et l'ordre de l'eau (Barnes, Lehman et Mulla 2014). Un corps sans mer se draine vers son point le plus bas.
2. **Les lacs par bilan d'eau :** une cuvette garde un lac terminal si l'eau qui y arrive est moindre que ce que toute sa surface évaporerait, moins la pluie sur elle ; son niveau, là où les cellules les plus basses évaporent l'apport. Les autres cuvettes débordent et se comblent : des plaines.
3. **Le routage :** chaque cellule vers sa voisine la plus basse sur la surface comblée, un plat par l'ordre de l'inondation ; la pente vers chaque voisine pesée de ±15 %, tirée par cellule et par voisine, d'après rho8 (Fairfield et Leymarie 1991) mais également : les chemins hésitent entre les deux directions qui encadrent la pente, au lieu de lignes droites à 45°. Le ruissellement par la courbe de Schreiber, cumulé vers l'aval.
4. **Le niveau de l'eau :** depuis la mer et les lacs, vers l'amont, la pente d'équilibre de la puissance fluviale, S = ks A^−θ, θ = 0,45 (Kirby et Whipple 2012) ; A l'aire drainée au ruissellement de référence, un bassin sec est plus raide. ks = √(30² + 150² U) / √K, U en mm/an : 30 sur les plaines, 150 à 1 mm/an, 330 à 5, l'Himalaya ; la racine, l'exposant de pente n = 2 mesuré sur les chaînes terrestres. Le niveau ne dépasse jamais la surface comblée : là où l'équilibre serait plus haut, le fleuve coule sur sa plaine.
5. **Le recul des points d'inflexion :** l'entaille remonte à vitesse finie, K A^0,5, le long des caractéristiques de la loi (Tzathas et al. 2024). Au-delà de 1 000 km parcourus par un fleuve de 10⁵ km², moins vite pour un plus petit, le sol garde sa forme : les plateaux ne sont entaillés qu'à leurs bords.
6. **La glace :** la ligne d'équilibre du dernier maximum glaciaire, 900 m sous l'actuelle ; l'actuelle où la température d'été vaut celle d'Ohmura, Kasser et Funk (1992) pour la précipitation, avec une correction fixe d'été de +8 °C à la moyenne annuelle. Le bilan, 0,6 m/an par 100 m, au plus 2 m/an et la précipitation ; cumulé le long du même réseau, la glace d'amont plus le bilan de la cellule là où elle en a. Un glacier là où le flux reste positif.
7. **Les dépôts :** un cône là où un fleuve sort d'une vallée de plus de 200 m pour un sol qu'il entaille moins du quart ; un delta à l'embouchure sans glace d'un débit de plus de 300 m³/s.

**Les sorties, une texture `R32G32_UINT` par face, `t23` (`Erosion.h`) :**
- le niveau de l'eau au nœud et la surface comblée, au quart de mètre ;
- le receveur parmi les huit voisines, les affluents parmi les huit ; les drapeaux : lac, mer, cône, embouchure ;
- le débit et le flux de glace, en log.
- **Le nœud de chaque cellule** est un point tiré dans la cellule par son hachage, à 0,3 cellule au plus : rien à stocker.

**L’intégration avec le climat et les volcans :** `t18` porte la tectonique, `t19` ses vues, `t20` le climat, `t21` les volcans, `t22` leur index, `t23` l’érosion. La table contient six descripteurs. Le niveau 0 lit la forme avant érosion complète, édifices et finition volcanique compris. Les vallées et les dépôts précèdent l’abrasion ; les cordons suivent le rivage lissé, puis vient la finition des récifs. Le climat est calculé avant le niveau 0, qui lit sa carte CPU ; `ErosionClimate` et `ErosionWaveWind` lisent les mêmes champs côté shader et portage.

**Le cache par graine :** `x64/Release/erosion-<graine>.bin`, sa clé la forme lue, la taille et tous les champs CPU du climat, la graine et la date de l’exécutable. L’ancienne clé ne couvrait pas explicitement le climat ; tout changement de ses champs invalide désormais le cache, même à exécutable et relief identiques. Le portage CPU le lit aussi.

**Shared terrain and water data:** valley floors, river surfaces and terminal lakes read the same drainage map. The six additional terminal-stage slices and channel construction are documented in [inland water](spec-eaux-interieures.md).

**Le contrat de la pile**
- Le support tectonique et volcanique, ses plis et ses octaves de plus de 20 km ne dépendent pas du réseau qui va les creuser.
- Le réseau fournit une seule enveloppe de vallée, avec ses paramètres de drainage.
- L’écart entre cette enveloppe et le support décide de l’incision et guide le détail plus fin.
- Le détail des versants entre dans l’enveloppe de coupe ; cette enveloppe coupe le terrain complet sans le relever.
- Le fond éteint ce détail une seule fois ; mesas et plateaux ne reçoivent plus un second masque préalable.
- Les dépôts restent une opération distincte, suivie de l’abrasion côtière et de la finition du littoral.
- Le préfixe grossier et le détail se calculent dans la même boucle ; aucun deuxième calcul du support n’est ajouté pour les vallées.
- Le réseau global reste calculé au démarrage et mis en cache ; aucune simulation d’érosion ne tourne pendant le vol.

## Le niveau 1 : les vallées du réseau, `ErosionValleys`

**Le tracé et les raccords**
- Chaque lien suit une courbe quadratique entre les milieux des liens voisins.
- Quatre cordes initialisent la recherche du point proche ; quatre pas de Newton mesurent ensuite la courbe elle-même.
- Les sources et exutoires à contrôle répété sont des segments : distance et paramètre se calculent directement, sans division par une tangente nulle.
- Les distances se prennent dans le plan tangent à la direction unitaire ; la flèche radiale d’une corde n’est pas une berge.
- Hauteur et sol de référence suivent la même quadratique ; leur pente est continue au milieu partagé.
- Débit géométrique et flux de glace arithmétique suivent aussi la quadratique entre leurs valeurs partagées ; leur dérivée ne devient pas singulière aux sources.
- Le gauchissement garde les longueurs d’onde de 40 et 20 km, avec une amplitude de 2 km.
- À 7 km, son jacobien changeait de signe sur près de 13 % des points testés : une vallée pouvait se replier ou se dédoubler.
- La réduction à 2 km est vérifiée sur 100 000 directions par graine ; ce contrôle numérique ne constitue pas une preuve globale d’injectivité.

**Le profil**
- Le fond fluvial garde sa largeur selon le débit et la pente longitudinale.
- Le U glaciaire part du niveau drainé, avec `z + c x² / W`, `c = 0,3`.
- `W` dépend du flux de glace, de 150 à 1 500 m.
- La parabole rejoint sa tangente quand sa pente atteint 0,85 ; hauteur et pente sont continues.
- Le profil parabolique est une approximation morphologique, d’après [Hirano et Aniya, 1988](https://www.jstage.jst.go.jp/article/jgeography1889/97/2/97_2_107/_article/-char/en).
- La loi de largeur et son calibrage restent ceux du moteur ; ils ne sont pas déduits de cet article.
- Le surcreusement souterrain puis le plafonnement à l’eau sont retirés : ils transformaient tout le U en ruban plat.
- **Mesh filtering:** exact local box mean of the physical fluvial/glacial section, with radius `max(cellMetres, CREASE_MIN_CELL)`.
- The 2 m minimum uses the existing physical crest rounding; there is no new setting.
- Averaging a convex section only raises its profile, by at most `maximumWallSlope × radius / 2`; far planar banks remain fixed.
- The filter ignores coarse reference depth and leaves the physical floor mask unchanged.
- This is a local profile mean, not a claim of exact area conservation after clipping against arbitrary terrain.

**La réunion des vallées**
- La surface est le minimum des profils ; chacun porte déjà son propre niveau drainé.
- Le niveau du lien géométriquement le plus proche ne borne plus la surface d’un autre lien.
- La pente qui guide les ravines se mélange sur 60 m entre profils concurrents ; elle ne saute plus au changement de lien.
- The cut surface carries positive spurs, fading on the floor; negative residual detail is not added to the cut a second time.
- Its C1 positive part uses the existing 60 m join scale; original hollows survive through intersection with the full terrain.
- New excavation cannot go below the valley envelope; this prevents artificial side trenches beside a perched channel.
- The cut is `depth × smoothstep(0, 60 × (1 - floorShare), depth)` on the shoulders; at full floor share it reaches the profile without a degenerate smoothstep.
- Le creusement ne relève jamais un creux ; l’extinction commandée par le seul support grossier pouvait dresser un rebord de plusieurs centaines de mètres.
- Un creux initial sous le profil reste présent ; son remplissage relève des dépôts ou des lacs, pas de cette coupe.
- Aux recouvrements, un point de l’ancien axe peut appartenir au versant d’une vallée plus basse ; son sol suit ce profil, pas un niveau d’eau pris indépendamment.
- The fluvial floor includes the liquid channel width, subject to the existing reach bound, and does not drop its floor mask at terminal nodes.
- Channel cutting after terrain finishing is bounded by its compact depth; it cannot re-excavate an unbounded V profile.

**Le relief support reste indépendant de sa finition**
- Les deux octaves de plus de 20 km sont calculées avant l’activation des ravines.
- Leur hauteur décide du creusement réel, avec la forme tectonique et volcanique.
- Le fond ne supprime pas ces octaves avant le calcul de l’entaille.
- L’incision ne supprime plus les plis tectoniques en amont ; le réglage `EROSION_FOLD_DEPTH` est retiré.
- Le renfort des contreforts et les ravines ne portent que sur les octaves suivantes.
- Leur amplitude minimale reste 0,35 de la profondeur locale, bornée par l’incision du réseau.
- Une vallée située au-dessus de ce support ne peut plus orienter ses ravines.

**Les dépôts et la portée**
- Deltas et cônes conservent leurs profils et leurs limites de portée.
- La requête lit les 4 × 4 nœuds voisins ; leurs influences s’éteignent avant le changement des nœuds lus.
- La profondeur et la glace restent des maxima continus d’influences locales.
- Les détails des anciens profils et mesures sont dans [l’historique](log/spec-erosion-historique.md).

## Le niveau 2 : les ravines, dans `ReliefDetail`

**Les octaves du détail de 11 km à 100 m changent de motif là où le sol penche :**
- **un bruit de phase** (Tricard et al. 2019, *Procedural Phasor Noise*) : des ondes planes à travers la pente, une période par maille de l'octave, sur les 8 coins d'une maille de deux périodes, chacun sa phase ; la phase de leur somme. Ses singularités sont les confluences ;
- **la pente qui l'oriente :** celle du support complet à plus de 20 km, ou des versants de la vallée là où elle le creuse réellement, plus celle des octaves plus larges ;
- **un remplacement centré de l’octave ordinaire,** demandé à 85 % sur une pente de plus de 0,15, rien sous 0,02 ; sa part est réduite par le budget de pente, sans réduire le bruit porteur ;
- **près et au-dessus de la glace,** la bande de ±300 m autour de la ligne d’équilibre du maximum glaciaire seule active les arêtes ; le flux de glace façonne les auges en U sans affûter le détail ;
- **un profil monotone à pente finie :** pour `u = |x| / scale`, `(1+b)u − bu²` jusqu’à 1, puis sa tangente ; `b = 0,2 × glacial`, zéro l’arrête ; sa dérivée augmente d’au plus 15,1 % avant arrondi, contre une puissance singulière auparavant ;
- **le même intervalle d’arrondi :** une parabole raccordée en valeur et pente sur `max(crease, CREASE_ROUNDING × f / gCreaseMaxFrequency)` ; aucune largeur plus fine n’est réintroduite ;
- **la moyenne gardée :** normalisation par `E|cos| = 2/π` et `E cos² = 1/2`, puis soustraction de l’excès exact de l’arrondi sur les bandes sinusoïdales ; une série évite la soustraction de termes voisins ; le changement est exactement nul à `b = 0` ;
- **elles s'éteignent où la pente qui les oriente se retourne :** sur les crêtes de l'octave au-dessus et de la plus large, celle des chaînes et des plis, et au rebord des vallées. Le motif des deux versants ne s'y raccorde pas : il dressait des lames en peigne le long des crêtes ;
- **elles s'éteignent autour de leurs bifurcations,** où la somme des ondes tombe sous 0,3 : la phase y prend toutes les valeurs, le sol s'y déchirait ;
- **les plis appartiennent au support :** les vallées les entaillent selon leur profil, sans atténuation préalable commandée par le réseau.

**One directional-pattern budget for soil and rock (`ReliefGullyRock`, `ReliefGullyGain`):**
- The rock fraction still follows mountain relief, wavelength and glacial climate.
- The admissible slope interpolates from `1.25` to `tan(70 degrees)` with that fraction.
- Both materials reserve the ordinary octave and the full directional-stripe envelope.
- The stripe envelope includes changes of direction, interpolation weights and phase forks.
- The gain is `B / sqrt(B*B + [share*(N+G)]^2)`, with `B = max(Sc-s-N, 0)^2/Sc`.
- Exhausting the reserve restores the ordinary octave; it does not remove the supporting terrain.
- The former rock exception used only amplitude divided by wavelength and produced metre-wide blades.
- This change adds no terrain lookup, octave, cache or simulation.
- The envelope is conservative: rock gullies are almost absent in the four reproduced defect windows.
- This is a geometry correction awaiting flight review, not a validated final gully model.
- Recovering stronger gullies requires a direction field coherent at their own wavelength, not relaxing the turning budget.
- The replaced budget is preserved in `log/spec-erosion-historique.md`.

**Blade regression checks, 2026-11-01:**
- `tools/hydro/verifie_lames.py` checks four 81-by-81 metre windows in two regions against public-history commit `7187c1b`.
- Maximum neighbouring one-metre height steps fall from 39.25, 39.09, 514.73 and 48.63 m to 1.55, 0.79, 1.64 and 1.32 m.
- No sampled slope exceeds 80 degrees after the change; maxima range from 40.82 to 59.44 degrees.
- The terrain before erosion is bit-identical; resolved outputs at 1 m and 0.25 m are identical.
- These are reproducible additional locations, not recovered camera coordinates from the user's screenshots.
- They do not prove global geometry validity or settle distant network repetition.
- Flight review: `tools/tests/2026-11-01-lames.txt`, close defects on F1-F4 and broader witnesses on F5-F12.
- Native captures at two close poses and two wider poses show continuous nearby slopes without the large blade family reproduced by the CPU checks.
- The distant relief diagnostic still shows serrated edges; regular large-scale drainage also remains visible. Their causes are not resolved by this correction.
- Capture artifacts are local in `x64/erosion-continuation/`; Windows window activation failed, so inspection used the engine's native image capture.

## Les falaises côtières

**L’abrasion suit un contour du sol complet, détail, vallées et dépôts inclus.**
- **Où :** `ErosionCoast`, après les dépôts et avant les cordons, avec `valleys = true` seulement.
- **Le rivage estimé borne la portée :** il ne place plus une paroi dans les montagnes.
- **Contour:** `Hc = clamp(1000 W G, 8, 400)` m; the physical incision ends at `Hc + delta`, its sampled support at `Hc + delta + footprint`.
- **La largeur W :** 1,2 km × exposition × érodabilité, au plus 3 km ; variation de 45 % par un bruit de 2,4 km (Sunamura 1992, force sur résistance).
- **La pente G :** norme tangentielle des grandes formes et des trois octaves du détail de plus de 9 km, avant la limitation des ravines des sols mobiles ; la pente côtière `coastSlope × shoreMetric / 1000` reste un plancher.
- **Pourquoi 9 km :** trois fois le recul maximal ; les octaves de 50, 23,7 et 11,2 km gardent les grands versants sans laisser les petits éperons déplacer Hc.
- **Une seule évaluation du relief :** `cliffSlope` vient du `ReliefDetail` principal et de ses trois octaves de plus de 9 km ; aucun recalcul ni lecture hors sphère pour figer Hc. Le paramètre de projection est retiré : les vallées se lisent toujours sur la sphère.
- **Le plafond de 400 m :** calibrage proche des 426 m de Conachair recensés par [NatureScot](https://www.nature.scot/landscapes-and-habitats/habitat-types/coast-and-seas/coastal-habitats/coastal-cliffs), sans maximum géologique universel.
- **Les caps et les anses :** roche dure et abri réduisent W et le contour ; roche tendre et exposition les augmentent.

**Physical coastal metric (2026-11-01):**
- `ReliefCoastGradient` measures the coastal deformation at `EROSION_CLIFF_SLOPE_KM`, the existing 9 km erosion scale.
- Its maximum frequency is `min(meshMaxFrequency, planetRadiusKm / slopeKm)`; its crease frequency uses the same physical ceiling.
- Both octave weights and the derivative of `abs(noise)` use that ceiling; selecting long octaves alone leaves metre-wide cusps.
- The full coast noise still places the shore; the broad metric controls the contour height and the inland reach only.
- No setting, seed, map or neighbouring terrain query is added; the metric reads three contributing octaves instead of five at fine meshes.
- `python tools/cotes/verifie_metrique_cotiere.py` compares 576 derivatives with independent height differences, across three seeds.
- The derivative is identical from 0.25 m through 4,500 m sampling cells; maximum finite-difference error is below 6e-6 per radian.
- Six fixed terrain windows cover the reported cusp and its surroundings, cold, tropical, southern and flat coasts.
- The cusp's maximum 1 m height step falls from 172.67 m to 0.176 m; its 1-to-4 m mesh change is below 0.187 m.
- Source terrain is unchanged; flat coast is bit-identical; three other windows retain cuts greater than 10 m.
- The second reported canyon pose was inside the false excavation; its review camera is raised above the restored ground.
- Native captures at the original pose and the raised second pose remove the false wall and its needles.
- A wider view still shows an overly straight incision and a serrated distant bank; this correction does not establish globally clean geometry.
- The southern coastal witness no longer shows the previous isolated inland pits in its visible area.
- Flight route: `tools/tests/2026-11-01-metrique-cotiere.txt`; user review pending.
- The previous mesh-scale metric and measurements are [archived](log/spec-erosion-historique.md#2026-11-01-rejected-mesh-scale-coastal-metric).

**Le profil remappe la hauteur h.**
- **Sous Hc :** `min(h, P)` ; P vaut −1 m au pied, puis descend linéairement avec h vers l’ancien rivage.
- **Le platier :** pente nominale de 2 % sur W, dénivelé limité à 4 m (Trenhaile 1987).
- **Sous la mer :** raccord continu à la même droite ; tout fond plus profond reste intact.
- **Face:** fixed physical width `delta = 0.1 Hc`; filter the composed incision over the symmetric height radius `footprint = 1000 cellKm G`.
- **L’abaissement :** au plus `Hc + 1 m`, même à maille grossière ; aucun sol relevé.
- **Talus:** nominal 35-degree apron, up to 22% of Hc, in 900 m patches; its landward end meets the cliff face at that prescribed height.
- **Les stacks :** rares croisements de bandes de 130 m conservant le sol original ; élargis sur deux mailles, moins forts en proportion de leur surface.
- **Les rivières :** les fonds bas peuvent percer le contour et devenir des entrées de mer.

**Connected talus, `ErosionCliffScree` (2026-11-01):**
- A symmetric mound at Hc created a second downslope face before the cliff, leaving an artificial moat.
- Let `H = Hc - platformFoot`, and `T` be the existing talus-height setting times its patch mask.
- Find `t` on the cliff face from `delta*t + H*(3*t*t - 2*t*t*t) = T`; the contact is `Hc + delta*t`.
- A quadratic upper bound and four Newton steps solve this monotone interval; no terrain query or map is added.
- The apron above the platform is `max(T - screeSlope*max(contact-h, 0)/G, 0)`.
- Its excess rises towards the wall; beyond contact the cliff profile is already higher and takes over.
- The resulting section is continuous and nondecreasing in h for fixed parameters; it never rises above the original ground.
- Existing heights, patch sizes and slope settings are unchanged; the earlier symmetric profile is [archived](log/spec-erosion-historique.md#2026-11-01-rejected-symmetric-coastal-talus).

**Filtering after coastal composition, 2026-11-01:**
- `ErosionCliffMean` integrates the physical incision after the talus and min/max intersections.
- Split at the platform, talus contact and face joins; integrate linear and cubic pieces in local coordinates.
- No extra terrain query, map or generation setting is needed.
- For a planar source and frozen coastal parameters, the normalized symmetric mean preserves the incision area and its centre.
- `tools/cotes/verifie_filtre_falaises.py` checks an independent adaptive quadrature, joins, bounds, float32 precision and four terrain windows.
- Variable masks, the marine witness and later terrain composition remain outside this local conservation guarantee.
- The former one-sided widening and its measurements are [archived](log/spec-erosion-historique.md#2026-11-01-one-sided-coastal-filter).

**Talus regression checks:**
- `python tools/cotes/verifie_pied_falaise.py`: 384 parameter sections and an independent contact solver; maximum support error below 2e-10 m.
- The old profile reversed slope in 288 sections; the new profile reverses none.
- Four terrain windows cover the reported cold location, tropical and southern rocky coasts, and a flat coast; the flat coast is unchanged.
- The new physical coastal metric rejects the former cold-location cut; the independent profile check still covers its talus failure.
- The original camera comparison and its snow ribbons are [archived](log/spec-erosion-historique.md#2026-11-01-rejected-symmetric-coastal-talus); material rules are unchanged.
- Flight review: `tools/tests/2026-11-01-pieds-falaises.txt`; no performance or quality benchmark was run.
- This correction addresses the talus connection; amplification of detail filtering by the coastal remap remains a separate open issue.

**Les entrées et la portée sont conservées.**
- **La roche :** classe convertie par texel avant B-spline ; croûte océanique 1, volcanique 0,6, jeune chaîne 1, sédiments 1,6, vieille chaîne 0,45, bouclier 0,25.
- **Les sédiments tendres :** facteur `1 + saturate(-forms.w)` au texel ; proxy continu du K absent de la carte GPU.
- **Le seul vent :** `ErosionWaveWind`, son jumeau CPU `erosion_wave_wind`, cube 1 du climat, est et nord en m/s, direction de déplacement.
- **La force relative :** 1 jusqu’à 5 m/s, linéaire vers 1,6 à 8 m/s, plafonnée ; les calmes s’éteignent continûment de 0 à 1 m/s. L’intervalle utile 1–1,6 garde la calibration précédente, sans conserver ses directions zonales.
- **Le repère :** est `(-d.z, 0, d.x)`, nord `cross(est, d)`, comme `Climate.cpp` ; aucune inversion du vent ni direction « venant de ».
- **L’exposition :** direction du large par le gradient des grandes formes ; houle omnidirectionnelle de 0,28.
- **Les baies :** éteintes à −12 km de déplacement côtier, pleinement exposées à −6 km.
- **La bande côté mer :** aucune limite intérieure au proxy brut de 8 km ; le détail peut y faire émerger la côte réelle.
- **La bande côté terre :** `shoreKm / shoreMetric < min(W + 1 + relief / coastSlope, 8)` km ; extinction sur les 500 derniers mètres.
- **Le déplacement du détail :** son amplitude tectonique `relief`, avant le terme des parois de vallée, divisée par la pente côtière en m/km ; une distance en km, sans nouvelle lecture.
- **Le proxy brut :** `abs(shoreKm) < 8 km`, extinction sur 500 m des deux côtés ; limite de calcul conservée, indépendante de la maille.
- **L’accès marin :** un témoin à 3 km, `RETREAT.z`, dans la direction du large des grandes formes déjà utilisée pour les vagues ; son sol avant érosion doit être sous −50 m.
- **Pourquoi avant érosion :** une vallée ou une auge creusée ne doit pas ouvrir à elle seule l’accès aux vagues.
- **Le témoin :** même relief, cordons et limitation des sommets, sans vallées, ravines d’érosion ni dépôts ; aucune lecture supplémentaire du réseau d’érosion.
- **Le raccord :** sa présence passe continûment de 1 à 0 sur 250 m de distance côtière, convertis par la pente du témoin ; elle vaut 0 dès −50 m.
- **La nature du test :** témoin marin conservateur, pas une mesure globale de connexité ; le seuil de −50 m est celui du contrôle de portée, pas une profondeur universelle d’abrasion.
- **La position du témoin :** rotation à petit angle en doubles ; aucun produit d’une position planétaire en float par le rayon.
- **Rien sur les côtes plates ni dans les baies totalement abritées.**
- **Le coût :** sorties précoces hors bande ; les sols intacts sautent les bruits des éboulis et des vestiges ; seule une coupe potentielle lit ce second point de terrain, sans nouvelle recherche de vallées.
- **Le branchement :** `ReliefSampleGround` sépare le sol du traitement côtier ; `ReliefFinish` garde les cordons et le plafond ; le témoin ne récursive pas et ne remplace pas la rugosité du point principal.

**Les réglages, préfixe `EROSION_CLIFF_` dans `PlanetSettings.hlsli` :**

| Réglage | Valeur | Sens |
|---|---|---|
| `RETREAT` | `(1, 1.2, 3, 0.45)` | activation, recul unitaire et maximum en km, variation relative |
| `NOISE` | `2.4` | longueur d’onde du recul, km |
| `BAY` | `(-12, -6)` | extinction et pleine exposition, km de déplacement |
| `REACH` | `(1, 0.5, 8)` | marge intérieure en plus du recul et du détail, extinction, plafond intérieur et borne du proxy, km |
| `SEA` | `(50, 0.25)` | profondeur minimale du témoin en m, transition en km ; sa distance est `RETREAT.z` |
| `HEIGHT` | `(8, 400)` | bornes Hc, m |
| `SLOPE_KM` | `9` | physical slope scale in km; detail octave cutoff and coastal metric's spectrum and crease filtering |
| `FACE` | `0.1` | part minimale de Hc pour δ |
| `SCREE` | `(0.7002, 0.22)` | pente de repos, part de Hc |
| `PLATFORM` | `(-1, 0.02, 4)` | pied en m, pente nominale, dénivelé maximal en m |
| `STACK` | `(0.065, 0.8, 1.4)` | demi-largeur et bruit en km, seuil régional |
| `WAVES` | `(0.28, 1.6)` | houle, force relative maximale à 8 m/s |

**Les contrôles actuels :** `python tools/cotes/verifie_falaises.py`, puis `python tools/hydro/verifie_cretes_climat.py --before fe22cfe9d6d96e9680ca44ef2fd5e47704467939`.
- **Les trois coupes fixes restent mesurées :** avec les caches intégrés, le port commité ne retrouve déjà que deux faces, dont une de plus de 100 m ; la troisième face historique est absente avant le raccord. Le contrôle compare les nombres avant/après sur ce même témoin, sans changer les limites physiques.
- **Les limites physiques restent sur le vent calculé :** abaissement au plus Hc + 1 m, aucun sol relevé, montagnes intactes, moins de 5 % de coupes enclavées et portée p99 sous 4 km.
- **Les anciennes tables :** [historique](log/spec-erosion-historique.md).

## Le drapeau `valleys`

**`ReliefElevation(p, true)` rend le relief érodé ; `(p, false)` la forme avant érosion,** sans aucun niveau, celle que le niveau 0 lit. Le niveau 0 ne lit jamais ses propres sorties.

## Les branchements

**Avec le climat :** `ErosionClimate` rend P en m/an, précipitations annuelles du cube 0 divisées par 1 000, et T annuelle au niveau de la mer en °C.
- **CPU :** `CreateTectonicMap` appelle `CreateClimateMap`, qui garde `mClimateCpu`, puis vient `CreateErosionMap` et `Erosion::Build` ; aucune boucle, le climat lit toujours la forme avant érosion.
- **GPU :** `ClimateAt` lit t20 ; les passes terrain, terrain fin, carte planétaire et placement gardent leur table t18–t23, avec le sampler linéaire s4 ; l’érosion reste t23.
- **Le portage :** `erosion_climate` et `erosion_wave_wind` lisent `cp.climate(p)`.
- **La ligne d’équilibre :** relation d’Ohmura, correction d’été fixe de 8 °C, gradient de 6,5 K/km et abaissement glaciaire de 900 m conservés ; pas de nouvelle formule ni de recalage de la part glaciée. La demi-amplitude calculée n’est pas utilisée ici.
- **La limite de mesure :** la part glaciée du réseau n’est pas remesurée ici ; le portage ne reconstruit pas le niveau 0.

**Avec le volcanisme :** ses édifices s'ajoutent à la forme avant érosion, `ReliefElevation(p, false)`. Le niveau 0 les voit s'ils dépassent 40 km ; plus petits, les ravines les découpent comme tout relief. `ReliefDetail` gagne deux paramètres, les ravines et la somme grossière.

**Visible water:** rivers use link discharge and stage; terminal lakes use their water-balance level. The shared channel envelopes, basin transitions, rendering and limits are in [inland water](spec-eaux-interieures.md).

## Le portage CPU

**`tools/hydro/cp.py` lit le niveau 0 du moteur,** `erosion-<graine>.bin`, et refait les vallées, les dépôts et les ravines ; les nœuds en float32, comme le shader. `EXOLUNE_EROSION` donne un autre chemin.

## Current verification, 2026-11-01

**Scope:** working corrections on the public-history erosion branch in `Exolune`.
- `verifie_lames.py` compares with public replay `7187c1b`.
- `verifie_auges.py` now uses public replay `7c9f475`; no legacy Git history is imported.
- Earlier closure measurements and their failed quality threshold are [archived](log/spec-erosion-historique.md#2026-11-01-archive-worktree-closure).

**Approach mutation:** the snowy pose was recovered from the running engine during the report.
- Pose: `4096.4 -46.85004 -33.85772 31.9 -63.4`; second view 31.4 m lower.
- The former filter scaled the entire valley by its intersection with coarse reference ground.
- Near zero reference depth, changing the mesh moved distant planar banks by hundreds of metres.
- The new filter averages the physical cross-section locally; it does not scale its coordinates or its floor mask.
- In a fixed 4 km window, changing mesh spacing from 1 to 4 m moves terrain by at most 1.06 m, previously 220.85 m.
- At 16 m spacing, the maximum is 9.55 m, previously 417.73 m; filtered terrain still changes with resolution.

**Targeted checks:** no performance or quality benchmark was run for these working corrections.
- `python tools/hydro/verifie_filtre_vallees.py`: 240 profile samples against independent piecewise Gaussian quadrature; maximum error below 6e-12 m.
- Checks cover zero reference depth, unchanged distant planar banks, bounded rise and an analytic derivative.
- Three fixed terrain windows cover the reported snowy approach, a snowy trough and a tropical trough.
- Mesh spacing of 1 and 0.25 m gives identical heights in these windows.
- The existing profile, curve and endpoint checks pass; the four blade regressions still pass.
- Release x64 builds through `tools/lance.ps1 -Build -NoLaunch`.
- Two native captures retain the snowy cliff's main form through the descent; this is a local visual check.
- Review route: `tools/tests/2026-11-01-mutations.txt`; F1/F2 are the snowy pair.

**Open cases:** the green disappearing scar has no recovered exact position yet.
- A nearby coastal witness is not that screenshot's position.
- At `8.48997 -103.55646`, changing mesh spacing from 1 to 16 m changes height by 45.19 m.
- The cliff remap amplifies a 3.87 m change in its input height; its width parameter is unchanged there.
- The physical coastal metric correction does not alter this witness; the nearby captures do not reproduce the reported zigzag scar.
- Useful gully amplitude, distant repetitive drainage and the previous quality failures remain unresolved.

## Les défauts connus

- **Hydrological integration remains incomplete:** coarse paths and repeated valley profiles can dominate fine mountains and cut volcanic bowls whose outlet the coarse map does not resolve.
- The composition correction removes a demonstrated source of false side trenches; it does not validate the distribution, age or connectivity of all incisions.
- A cap from coarse network incision alone was rejected because its reference heights differ from the rendered support; stage and route reconciliation must come first.
- Volcanic freshness currently quiets detail and controls bare materials; the drainage solve does not directly use it to limit incision.
- The new flight route `tools/tests/2026-11-01-composition.txt` includes river banks, confluences, mountain ranges, two craters, an outlet, a lake and a coastal witness.

- **Le retour en vol du 2026-11-01 invalide une conclusion de géométrie propre :** lames minces, aiguilles et raccords en dents de scie subsistent dans les captures ci-dessous, malgré les contrôles CPU passés sur leurs échantillons.
- **Previous quality failures remain open:** the archived closure recorded thirteen texture p95 regressions; this working correction has not rerun that benchmark.
- **Les ravines sont désormais liées au creusement réel :** les pentes ne perdent plus leur support grossier avant la décision. Certaines crêtes non incisées perdent les bandes artificielles de la version E ; leur forme est à juger en vol.
- **Glacial floors:** the U remains curved, with continuous joins in the checked cases. Hillside hollows remain. Rivers and terminal lakes now have a first visible-water implementation (`spec-eaux-interieures.md`).
- **Les vallées du niveau 0 restent régulières à grande échelle :** le U corrige le fond glaciaire ; les versants fluviaux convexes-concaves et les éperons tronqués restent à construire.
- **Les deltas sont petits, et l'un d'eux faux :** 5 km au plus, la portée des nœuds lus ; à l'embouchure du plus grand fleuve, -7,8°, 27,2°, une langue de dépôt isolée au large, cause non trouvée, et un pan de côte aux bords droits, qui ne vient pas des dépôts. Les grands deltas demandent un champ des dépôts lu en B-spline.
- **Les ravines peuvent se voir peu de loin :** leur amplitude est désormais bornée par le sol porteur ; les deux octaves de plus de 20 km gardent leurs crêtes orientées le long des chaînes.
- **Cost:** earlier flight measurements are archived; the current filter adds no terrain query or simulation, and its runtime cost has not been benchmarked.
- **Les fleuves des flancs restent parallèles et droits sur 50 à 100 km,** sur les pentes régulières : la forme avant érosion filtrée à 40 km n'y a pas de relief qui les dévie.
- **Les falaises manquent où le rivage réel s'écarte de plus de 8 km de son estimation :** la côte active à -8,11°, 131,04° n'en a pas ; le plafond borne le coût.
- **Les falaises ne se voient qu'à quelques km :** de 30 km, le platier n'est qu'une bande turquoise ; la paroi à 23° S reste basse, 42 m.
- **Le témoin marin relit le relief avant érosion là où une coupe est possible :** son coût GPU n'a pas été mesuré au banc, seulement dans le bruit des rendus en mouvement.
- **Les douze vues courantes** sont à juger en vol avec `tools/tests/2026-11-01-auges.txt` ; les étapes précédentes gardent leur ancien parcours.

**Captures de reprise fournies par l’utilisateur**
- Les cinq originaux sont conservés sans retouche dans `images/erosion-2026-11-01/`.
- Les hauteurs sont celles des barres de titre ; les coordonnées de caméra ne sont pas lisibles dans ces titres tronqués.
- [11:57:24, dents de scie](images/erosion-2026-11-01/115724-dents-de-scie.png) : hauteur 40,1 m, sol vers 3,8 km ; longues rangées de pointes sur plusieurs versants.
- [11:57:33, paroi mince](images/erosion-2026-11-01/115733-paroi-mince.png) : même hauteur ; lame de grande amplitude dressée sur le versant et peigne au loin.
- [11:57:55, lames](images/erosion-2026-11-01/115755-lames.png) : hauteur 61,7 m, sol vers 1,9 km ; parois très minces et aiguilles, y compris en zone boisée.
- [11:58:16, aiguilles](images/erosion-2026-11-01/115816-aiguilles.png) : hauteur 78,9 m, sol vers 3,5 km ; nombreux pics sur un rebord abrupt et raccords dentelés.
- [11:59:12, motifs lointains](images/erosion-2026-11-01/115912-motifs-lointains.png) : hauteur 417,5 km ; vallées parallèles, espacement et courbures trop réguliers sur certaines régions.
- The screenshots alone do not identify the cause. Subsequent CPU probes reproduce blades in the height field and isolate the rock-gully budget exception; see the regression checks above.
- The active continuation is in the Exolune clone on the replayed erosion branch. Review the blade and valley-filter corrections in flight; recover the green scar position before declaring the approach artifacts resolved.

## Ce que la recherche a appris

Branche `erosion-niveaux`, `docs/recherche-erosion-niveaux.md` :
- **un niveau 0 global, calculé une fois, tient** (spikes A3) : drainage complet, lacs par bilan d'eau, bassins de 1 à 9 millions de km². Repris ici, son bilan d'eau compris ;
- **une érosion simulée par tuiles est chaotique** (spike B) : 43 m d'écart moyen entre tuiles et calcul d'un bloc, jusqu'à 2 km. Les niveaux fins sont donc une construction locale ;
- **un tracé choisi sur des cellules de 25 km fait passer les fleuves à travers les montagnes** (constat du 2026-10-27) : 44 % de leur longueur creusée à plus de 50 m sous le sol. D'où : le sol grossier s'abaisse jusqu'à la vallée au lieu d'être coupé, la vallée a des versants, le détail s'éteint sur son fond ;
- **ce qu'on ne reprend pas :** le soulèvement inventé à partir des hauteurs, l'érosion pas à pas, 10 minutes par graine, les tuiles calculées à l'approche.

## Les sources

- Selby, *A rock mass strength classification for geomorphic purposes: with tests from Antarctica and New Zealand*, Zeitschrift für Geomorphologie 24(1), 31–51, 1980 ; Augustinus, *The influence of rock mass strength on the form and evolution of deglaciated valley slopes in the English Lake District*, Scottish Journal of Geology 38(1), 15–20, 2002.
- Grieve, Mudd, Hurst, *How long is a hillslope?*, Earth Surface Processes and Landforms 41(8), 1039–1054, 2016, DOI `10.1002/esp.3884`.
- Roering, Kirchner, Dietrich, *Evidence for nonlinear, diffusive sediment transport on hillslopes and implications for landscape morphology*, Water Resources Research 35(3), 853–870, 1999, DOI `10.1029/1998WR900090`.
- Barnes, Lehman, Mulla, *Priority-Flood: An Optimal Depression-Filling and Watershed-Labeling Algorithm*, Computers & Geosciences 62, 2014.
- Kirby, Whipple, *Expression of active tectonics in erosional landscapes*, Journal of Structural Geology 44, 2012.
- Tzathas, Gailleton, Steer, Cordonnier, *Physically-based Analytical Erosion for fast Terrain Generation*, CGF 43(2), 2024.
- Ohmura, Kasser, Funk, *Climate at the equilibrium line of glaciers*, Journal of Glaciology 38(130), 1992.
- Tricard, Efremov, Zanni, Neyret, Martínez, Lefebvre, *Procedural Phasor Noise*, ACM TOG 38(4), 2019.
- Fairfield, Leymarie, *Drainage networks from grid digital elevation models*, Water Resources Research 27(5), 1991 : rho8.
- Sunamura, *Geomorphology of Rocky Coasts*, Wiley, 1992 : force des vagues et résistance de la roche ; distance cumulée paramétrée ici, sans simulation temporelle.
- Trenhaile, *The Geomorphology of Rock Coasts*, Oxford University Press, 1987 : platiers d'abrasion à faible pente.
- Gaillard, Guérin, Galin, Peytavie, Paris, *Dendry: A Procedural Model for Dendritic Patterns*, I3D 2019 : lu, écarté pour son coût par sommet.

## Le plan par étapes

| Étape | Contenu | Statut |
|---|---|---|
| 1 | Le niveau 0 au démarrage, sa texture, les vallées de ses liens | fait le 2026-10-31 |
| 2 | Les ravines, le recul des points d'inflexion, les cônes et les deltas, le portage | fait le 2026-10-31 |
| 3 | Le coût : positions en flottants, cache par graine | fait le 2026-10-31 |
| 3 bis | Les lames et les déchirures des ravines, la continuité de ce que lit le détail, le routage pesé, le portage à 0,6 cm | fait le 2026-10-31 |
| 3 ter | Arêtes sans cuspide, pluie, température et vent calculés ; clé du cache climatique | fait et rendu validé par l’utilisateur le 2026-10-31 ; nouveau réseau livré |
| 3 quater | Ravines à pente critique, moyenne nulle et bruit porteur conservé | sols validés par l’utilisateur ; arêtes reprises par E |
| 3 quinquies | Fonds raccordés à l’eau, borne rocheuse à 70° | fait dans D ; limites reprises par E |
| 3 sexies | Ravines selon roche et échelle ; directions gauchies sur la sphère | code et contrôles CPU faits ; jugement en vol à faire |
| 4 | U continus, gauchissement sans repli dans les contrôles, relief support conservé | étape figée ; contrôles CPU passés, géométrie invalidée en vol par les lames et aiguilles ; treize p95 en échec |
| 4a | Shared gully slope budget and local valley-profile filtering | CPU checks and snowy approach captures pass; user flight review, green scar and coastal mutation remain open |
| 4b | Connected talus and physical coastal metric | Profile and six terrain checks pass; native captures remove the reported false wall; wider straight incision and approach sensitivity remain open |
| 4 bis | Versants fluviaux convexes-concaves, éperons tronqués | à faire |
| 5 | Les grands deltas, par un champ des dépôts | à faire |
| 6 | Water from the same river and lake network | first implementation, 2026-11-01; flight review and limitations in `spec-eaux-interieures.md` |
