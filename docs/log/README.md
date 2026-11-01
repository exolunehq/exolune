# Log de la documentation

**Ce qui n'est plus d'actualité, pour mémoire.** Rien ici ne décrit l'état présent : pour lui, voir `../README.md`.

## Ce qui y va

- **Une spec close, remplacée ou désactivée,** entière, déplacée par `git mv` ; ses renvois, dans le code et les docs, pointent vers `docs/log/`.
- **Les sections dépassées d'une spec vivante :** essais, mesures intermédiaires, options écartées. Elles vont dans `<spec>-historique.md`, et la spec garde un lien.
- **Une piste mise de côté hors de `main` :** sa doc, prise dans son tag, quand elle n'existe nulle part ailleurs.

## Ce qu'il contient

**Les origines**

| Fichier | Pourquoi ici |
|---|---|
| `general_spec.md` | La spec d'origine, au maillage radial ; remplacée par `../concept.md`. |
| `concept-historique.md` | L'état des sources avant le portage de complexplanet, et la prochaine étape d'alors ; le portage est fait depuis le jalon 01. |
| `spec-rendu.md` | Le plan de rendu d'origine, étapes A à E ; faites ou remplacées par les specs suivantes. |
| `spec-champ-de-vision.md` | Le champ de vision et les performances, faits : jalons 02 et 03. Ses dix vues de référence servent encore de mesure. |
| `spec-stabilite.md` | L'enquête sur le tremblement ; ses règles sont dans `../principes.md`. |
| `spec-sommets-fixes.md` | La piste des sommets fixes, close. |
| `pistes-glissement.md` | Pistes contre le tremblement du maillage glissant, après les sommets fixes. |

**Le terrain et ses matériaux**

| Fichier | Pourquoi ici |
|---|---|
| `etat-de-l-art-details.md` | Recherche du 2026-10-21 sur les détails de surface ; ses voies ont été suivies ou écartées. |
| `spec-herbe.md` | Les brins d'herbe en géométrie, proposés le 2026-10-21, jamais faits ; des touffes de brins générés à la place, parmi les objets de proximité. |
| `spec-hybride-scans.md` | L'essai des scans photo, tag `piste/essai-hybride-scans` ; ses conclusions sont intégrées. |
| `spec-textures-generees-historique.md` | Les pistes tirées de la comparaison et ce qu'elles sont devenues ; les tours de la roche générée et sa structure de 64 m, retirée le 2026-10-24. |
| `spec-relief-reel.md` | Le relief des matériaux porté par le maillage : désactivé le 2026-10-23, retiré du code le 2026-10-30, tag `piste/parois-gradins` ; voie géométrie (`../geometrie.md`). |
| `spec-parois.md` | Les parois en gradins : désactivées le 2026-10-23, retirées du code le 2026-10-30, tag `piste/parois-gradins`. |
| `spec-normales-spline-historique.md` | Le préfiltre de la spline cardinale et `SPLINE_SHARPENING`, retirés le 2026-10-30, tag `jalon/09-normales-spline`. |
| `spec-rendu-lointain-historique.md` | Deux correctifs de la passe de relief des matériaux, retirée le 2026-10-30. |
| `spec-parois-minerales-historique.md` | Les options de la voie rendu, les bandes cassées et leurs correctifs, retirés le 2026-10-24 ; le filtre d'érosion, tag `piste/erosion-filtre`. |
| `spec-relief-tectonique-historique.md` | Les versions remplacées de la carte et des cordons du 2026-10-31, leurs mesures et leurs défauts. |
| `spec-parallaxe.md` | La parallaxe du relief de la roche : retirée le 2026-10-24, le relief qu'elle lisait ne s'affiche plus. |
| `roche-regionale.md` | La roche régionale par pixel, mise de côté le 2026-10-24 avant « une seule roche », tag `piste/roche-regionale` ; ses mesures. |

**La lumière, la mer et les rivières**

| Fichier | Pourquoi ici |
|---|---|
| `recherche-rayons-historique.md` | La hauteur d'ombre sur une grille polaire, étape 1 des rayons : remplacée le 2026-10-24 par la marche des ombres portées. |
| `recherche-mer-historique.md` | Premier noyau de mer en pixels, remplacé sur la piste FFT ; conservé comme témoin. |
| `spec-mer-fft-spike-historique.md` | Mesures du prototype FFT du 2026-10-26 et de son intégration à main ; qualité, stabilité, reflet et coût. |
| `recherche-cotes-historique.md` | Le plan de l'étape 1 des plages, avant de la faire sur la branche `plages`. |
| `recherche-rivieres-historique.md` | Les spikes rivières des 26 et 27 octobre, tag `piste/rivieres-spikes`, hors de `main` : état final, essais remplacés, journal, règles et surcouches de la branche. |

**Les nuages**

| Fichier | Pourquoi ici |
|---|---|
| `recherche-nuages-historique.md` | La couche 2D et l'ancien volume en cascades des 24 et 25 octobre, tag `piste/nuages`, et sa stabilité ; remplacés par les nuages du jeu. |
| `poc-nuage-stable.md` | POC d'un nuage stable et animé par une météo partagée ; clos. |
| `poc-nuage-stable-historique.md` | Référence figée validée le 26 octobre 2026, avant le mouvement météo partagé. |
| `poc-nuage-voxel.md` | POC d'un volume voxelisé local ; clos. |
| `spike-nuages-voxel-planete.md` | Plan de V3 interrompu avant compilation ; nouveau spike à fonder sur des références publiées. |
| `spike-nuages-voxel-planete-historique.md` | Premier placement régulier trop répétitif, retour de performance et essais intermédiaires du spike voxel. |
| `spike-nuages-reference.md` | Référence locale guidée par Frostbite : bruits, profils, extinction, provenance ; recette reprise par les nuages du jeu. |
| `spike-nuages-reference-historique.md` | Spikes Wicked V1 à V5, essai de répartition météo A et mesures intermédiaires ; Formes A et B insuffisantes en vol, Courants C conservé, notice courante pour la référence locale Frostbite. |
| `spike-nuages-cirrus.md` | Cumulus, nappe et cirrus dans une scène locale commune ; familles reprises par les nuages du jeu. |
| `spike-nuages-cirrus-historique.md` | Premier essai isolé de cirrus ; fibres trop larges et enveloppe qui coupe les ondulations, remplacé par une scène commune des trois familles. |
| `spike-nuages-region.md` | Formations régionales sur une carte météo étendue ; remplacées par la météo sur la sphère entière. |
| `spike-nuages-orbite.md` | Cirrus plus rares et première quadrature orbitale ; quadrature reprise par les nuages du jeu. |
| `spike-nuages-lumiere.md` | Compensation diffuse sans rayon ajouté, écartée en vol ; éclairage précédent rétabli avant fusion de main. |
| `spec-nuages-historique.md` | L'ancien `spike-nuages-planete.md`, devenu `../spec-nuages.md` le 2026-10-30 : son lancement et ses variantes, le témoin figé, l'isolation et les mesures du spike et de l'intégration ; tags `piste/nuages-planete-spike`, `jalon/26-nuages-main`. |

**La végétation et l'optimisation**

| Fichier | Pourquoi ici |
|---|---|
| `recherche-vegetation-historique.md` | Les plantes générées v1 à v3, leurs formes, leur coût et leur aspect ; retirées du code le 2026-10-30, tags `piste/vegetation`, `-v2` et `-v3`. |
| `prototype-vegetation-volumique.md` | Le prototype comparé des modèles détaillés, volumes et imposteurs multivues, clos, son code retiré le 2026-10-30 ; ses mesures restent la référence de comparaison. |
| `prototype-vegetation-volumique-historique.md` | Premiers volumes écartés, défaut de couverture et choix du filtrage par transmission ; mesures intermédiaires du prototype. |
| `vegetation-planetaire-historique.md` | Premiers vols, saturation des files, modèles écartés et itérations comparatives des bouquets, normales et visibilités du feuillage ; les comparatifs du jalon 24 ; les modes, modèles et lanceur retirés le 2026-10-30. |
| `arbustes-climatiques-historique.md` | Première collection trop apparentée, sélection de familles remplacée et mise au point des sous-plages GPU ; le vol de jugement d'alors. |
| `vegetation-hiz-historique.md` | Les témoins du HiZ, profondeur historique et modes intercalés, retirés le 2026-10-30 ; la comparaison intercalée et son vol. |
| `optimisation-vegetation-historique.md` | Essais de compaction et de déplacement des calculs des imposteurs ; limites des mesures sur GPU partagé ; le vol de comparaison, retiré le 2026-10-30. |
| `optimisation-historique.md` | L'analyse de départ de chaque round de `../optimisation.md` : le coût de chaque part, mesuré par variantes. |
| [Ship assembly history](spec-vaisseau-historique.md) | Former cockpit supports, panel layouts, junctions, foredeck profile and intermediate asset counts. |
