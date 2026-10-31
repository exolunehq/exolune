# Nuages du jeu : historique

**Ce qu'était `../spec-nuages.md` avant le 2026-10-30,** sous le nom `spike-nuages-planete.md` : le spike des ombres et du premier globe, puis son intégration à `main`. Rien ici ne décrit l'état présent.

- **Code et lanceurs d'alors :** tag `piste/nuages-planete-spike` (`5b53b81`) pour le spike ; `jalon/26-nuages-main` pour l'intégration ; `jalon/29-avant-ouverture` pour le dernier état avant le rangement.
- **Retirés le 2026-10-30,** commit `3663177` : le lanceur `tools/nuages-planete.ps1` et ses variantes, le générateur `tools/gen_frostbite_planet_assets.py`, les dossiers `assets/frostbite-*`, le témoin figé. Le shader du jeu s'appelait `CloudFrostbiteOrbit.hlsli`, sa passe temporelle `CloudFrostbiteTemporal.hlsli`.

## La lumière et le pixel lointain, jusqu'au 2026-10-31

**Remplacés le 2026-10-31 par la piste `piste/orbite-rendu`** (`../spec-rendu-orbite.md`) : d'orbite, ils donnaient des nuages gris et translucides, et un grain sableux.

- **La densité des nuages bas** gardait le facteur de couverture : `remap(forme, 1 − R, 1) × R × profil`, puis l'érosion. Un champ à 10 % avait dix fois moins d'eau qu'un front.
- **La phase :** deux lobes de Henyey-Greenstein, g = 0,5 et −0,5, le second à 20 %.
- **Vers le soleil :** quatre pas de 125, 250, 500 et 1 000 m, 1,875 km en tout.
- **Un second ordre approché,** additif et isotrope : extinction ×0,2, profondeur vers le soleil ×0,2, source ×0,35. La réflectance d'un nuage infini plafonnait vers 0,25.
- **Le pas** n'était pas borné en épaisseur optique ; la marche s'arrêtait à une transmission de 0,003.
- **La quadrature lointaine :** loin, un pixel moyennait des rayons fins, au mip 0, 2 × 2 en qualité Éco et 3 × 3 en Référence, en lumière prémultipliée et en transmittance. Son poids croissait avec l'empreinte du pixel à l'entrée de la couche, de 0,25 à 0,8 km, la caméra au-dessus de 14 à 22 km et la vue assez plongeante (`CLOUD_FAR_*`). La passe temporelle traçait un rayon fin par visite et en moyennait huit au plus, deux en mouvement (`CLOUD_TEMPORAL_FAR_RAYS`, le jitter de `cloudTemporal.w`).
- **La carte météo** se lisait en bilinéaire.
- **L'air** comptait toute la diffusion des aérosols dans sa table de diffusion multiple isotrope, et un sol gris à 0,3 sous lui, l'océan compris.

## La carte météo artistique, jusqu'au 2026-10-31

**`assets/clouds/weather-planet1024.rgba8mips` et `tools/gen_cloud_weather.py`, retirés le 2026-10-31** (commit `051e3f0`, tag `piste/nuages-climat`) : la carte se calcule désormais sur le climat (`../spec-nuages.md`, la carte météo).
- **Ce qu'elle était :** des champs de Perlin 3D sur la sphère unité, de 2 600 à 90 km, graines et décalages distincts par octave ; des fronts en lignes de niveau, des bancs, des régions convectives fragmentées ; la convergence tropicale et les rails des moyennes latitudes en faibles penchants.
- **Ses chiffres :** couverture moyenne 0,094 ; au-dessus de 0,03 sur 56 % de la sphère, de 0,2 sur 15,5 %, de 0,4 sur 3,3 % ; cirrus au-dessus de 0,03 sur 1,6 %.
- **Son défaut :** aucun lien avec la géographie ; une répartition sans cohérence météorologique, jugée peu naturelle en vol.

## La première carte tirée du climat, le 2026-10-31

**Remplacée le même jour** par la météo vue d'orbite (`../spec-nuages.md`, la carte météo ; journal du 2026-10-31). Commit `051e3f0`, tag `piste/nuages-climat`.
- **Son défaut, vu d'orbite :** trois à quatre fois trop peu de nuages, 17 % de la sphère couverte contre deux tiers sur Terre, et des taches isolées sans organisation. Sous la loi `remap(forme, 1 − R, 1) × R`, seul le contour R ≈ 0,2 dessinait un nuage visible, et le plafond de 0,6 bornait tout.
- **Ses composantes :**

| Nuage | Où | Couverture, famille |
|---|---|---|
| Convection, la ZCIT et les moussons | pluie forte et chaude, de 800 à 2 500 mm et de 14 à 26 °C, en amas étirés le long de l'équateur thermique | 0,58 dans les amas, 0,04 entre eux ; cumulus |
| Cumulus de beau temps | terres humides | 0,2 ; cumulus |
| Cumulus des alizés | mers chaudes, éclaircis par la subsidence, la faible pluie | 0,1 ; cumulus |
| Nappes de stratocumulus | au-dessus des remontées d'eau froide, lissées sur 500 km et portées 700 km sous le vent | 0,5 ; nappe |
| Bancs au vent des reliefs | où le vent monte la pente des grandes formes lissée sur 120 km, de 0,02 à 0,12 m/s | 0,42 ; mixte |
| Stratus des mers froides | au-delà de 45 à 62° | 0,3 ; nappe |
| Dépressions des rails | 18 à la fois, vers 50°, où les vents d'ouest soufflent sur la mer, à 2 600 km les unes des autres | la tête en virgule 0,6, sa fente sèche ; le front froid 0,52 ; le front chaud 0,45 ; son bouclier 0,42 sous des cirrus de 0,24 ; épaisses |
| Cellules derrière les fronts | l'air froid sur la mer | 0,3 ; cumulus |
| Stratus des rails | entre les dépressions | 0,16 ; nappe |

- **Le plus fort l'emporte,** et donne sa famille.
- **Le ciel se dégage** sur les déserts, sous 80 à 350 mm, et sous le vent des reliefs, où l'air descend de 0,015 à 0,1 m/s ; les nappes gardent les mers sèches.
- **Les cirrus :** les enclumes au-dessus des amas de la ZCIT ; des traînées du courant-jet vers 31° ; les boucliers des fronts chauds.
- **Les bruits,** de gradient sur la sphère, de 1 200 à 160 km : la carte est lue vers 80 km, plus fin ne ferait que baisser sa moyenne.
- **Une dépression,** sur sa propre échelle de 700 à 1 200 km et son stade, d'une onde à une occlusion : la tête au nord-ouest du centre ; la fente sèche qui s'y enroule depuis le sud-ouest ; le front froid, une courbe de 300 à 200 km de large vers le sud-sud-ouest ; le front chaud et son bouclier à l'est ; en miroir au sud. Son contour gauchi de 18 % de son échelle.
- **Le budget,** graine 0 : couverture moyenne 0,110, contre 0,094 avant ; au-dessus de 0,2 sur 16,8 % de la sphère, contre 15,5 ; au-dessus de 0,4 sur 3,1 %, contre 3,3 ; cirrus au-dessus de 0,03 sur 3,3 %, contre 1,6. Par bande : 0,150 de 0 à 10°, 0,059 de 20 à 35°, 0,128 de 35 à 60°.
- **Le temps :** 235 à 296 ms au titre, sur une machine chargée par d'autres rendus.
- **Ses chiffres,** graine 0 : couverture moyenne 0,110 ; au-dessus de 0,2 sur 16,8 % de la sphère ; cirrus au-dessus de 0,03 sur 3,3 %.

## L'état et le lancement d'alors

**État, 27 octobre 2026 :** éclairage précédent rétabli après rejet de la compensation diffuse ; intégration à `main` avec mer FFT et végétation. Les familles locales et la météo planétaire restent celles du spike.

**Essai écarté :** [lumière économique](spike-nuages-lumiere.md). Le modèle d'éclairage conservé est celui du commit `5b53b81`.

**Lancer :**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-planete.ps1
```

- F1–F2 : deux hémisphères depuis10000 km.
- F3–F6 : cumulus et nappes depuis800,300 et80 km.
- F7–F9 : survols des trois familles.
- F10–F11 : raccord de longitude et région polaire ; F12 : ombres depuis30 km.
- B : opacité ; C : qualité ; Espace : pause ; V : météo×1/×5 ; O/P : déplacer le soleil.
- `-Regional` : seule l'ombre change par rapport aux données Orbit acceptées ; palette régionale dédiée.
- `-SansOmbres` : mêmes données, même rendu, sans ombres de nuages sur les surfaces ; exécutable séparé.
- `-Temoin` : Planète au commit `5b53b81`, avant l'essai d'éclairage rejeté et avant cette intégration ; natif, palette et textures figés.
- `-Vue Meteo`, `-Vue Opacite`, `-Vue Ombres` : diagnostics isolés ; blanc dans Ombres signifie transmission solaire1.
- `-Soleil '5 215'` : choisir le soleil au lancement, par latitude et longitude ; les boutons de test portent leur propre soleil.
- `-Build -NoLaunch` : compiler le natif Release x64 fusionné puis le shader choisi ; Visual Studio2022/MSBuild et DXC requis.
- Par défaut, le lanceur active la végétation validée de main : modèles de jeu, maillages proches, imposteurs lointains, douze arbustes climatiques, HiZ et profondeur matérielle.
- Les caches attendus sont dans `assets/foliage/climate_shrubs_v2/` ; `-VegetationAssets` choisit un autre dossier préparé. Un cache absent arrête le lancement avec une erreur explicite.
- La végétation historique, v3, est retirée du moteur le 2026-10-30 : on n'y revient plus que par son tag, `piste/vegetation-v3` (`recherche-vegetation-historique.md`).
- `-Parcours tools/tests/2026-10-27-arbustes-climatiques.txt` : remplacer la palette de vol par les douze vues végétales ; `-Position` choisit la vue initiale.

## La régression de composition végétale, mesures du 27 octobre


- L'ancienne intégration conservait la part solaire du terrain sous les arbres détaillés ; même sans atténuation solaire, le clamp de `scène − soleil` réinjectait ce terrain dans leur couleur.
- Contrôle hors écran : `tools/banc_composition_surfaces.py --exe <natif> --out <dossier-neuf> --dxc <dxc.exe> --scans <scans>`.
- Le banc copie le runtime et les shaders ; il force seulement la transmission des ombres à1, avec les nuages actifs. Les quatre vues boréales, tempérée et désertique doivent retrouver l'image sans ombres, à1/255 près. Les copies de test ne servent jamais au vol.
- `--sans-hiz` et `--profondeur-historique` isolent les variantes de profondeur et de dessin.
- Contrôle du27 octobre : quatre images strictement identiques après correction, zéro pixel différent ; l'ancien code modifiait jusqu'à433185 pixels de plus de1/255. Les nuages entièrement désactivés étaient déjà neutres ; il faut garder leur passe active pour reproduire ce défaut.
- Sans composition solaire, les quatre images avant/après restent strictement identiques ; éclairage total des plantes conservé. Rendu courant avec vraies ombres inspecté au sol et à35 m en forêt boréale, puis confié au vol ; pas de nouveau budget de performance validé.

## L'isolation, le témoin et les variantes


- Témoin accepté : `x64/NuageFrostbitePlaneteTemoin/`,44 fichiers vérifiés par empreintes, dont les sources copiées ; référence Git `5b53b81`, tag `piste/nuages-planete-spike`.
- Assets nouveaux dans `assets/frostbite-planet/` ; générateur `tools/gen_frostbite_planet_assets.py`, manifeste et points de vol livrés avec le pack.
- Météo artistique déterministe ; pas de simulation atmosphérique, ni de couplage avec les côtes et le relief de cette planète.
- Les fibres des cirrus conservent le repère E/N fixe de la scène acceptée ; leur direction ne suit pas encore un vent tangent local sur tout le globe.
- La carte globale a un pas proche de39 km à l'équateur, environ78 km au mip1 ; les petites variations de couverture régionales ne sont pas reproduites par cette carte.
- Le parcours d'ombre est une référence de spike ; son filtrage par les mips de densité et son plafond d'échantillons ne constituent pas une moyenne optique exacte.
- Toute la planète peut couvrir davantage de pixels nuageux que la région ; le coût du rendu global reste à juger, sans promesse de budget validé.
- Publication demandée : branche `codex/nuages-voxel-poc`, tag `piste/nuages-planete-spike` ; exécutables, captures et témoins sous `x64/` locaux et ignorés.
- Natif intégré isolé dans `x64/NuageFrostbiteMainNative/`, variantes dans `x64/NuageFrostbitePlaneteMain*/`. Les anciens exécutables V4 et témoins ne sont pas écrasés.
- La fusion conserve les champs végétation et mer de `main` ; phase et vent des nuages ont un vecteur distinct. Carte planétaire en `t29`, hors des ressources nuageuses.
- Piste d'intégration : `piste/nuages-main-integration`. Le mode nuages32 conserve les diagnostics terrain, carte et climat0–31 de main.
- La seconde cible solaire garde les contributions directes de la terre, de l'eau, du reflet solaire et de l'écume ; le ciel réfléchi reste dans la composante ambiante.
- Les anciens lanceurs de spikes reposant sur V4 se reconstruisent à leur tag historique ; le lanceur Planète courant et son natif utilisent le nouveau contrat GPU de main.
- Vérifications de vol confiées à l'utilisateur ; pas de banc prolongé.

## Les contrôles courts du spike et de l'intégration


- Compilation DXC du rendu avec/sans ombres et des diagnostics ; seul avertissement préexistant de `Materials.hlsli`.
- Deux globes rendus sur les hémisphères opposés, puis région dense à800 km et surface terrestre à30 km.
- Mer à80 et300 km avec/sans ombres, puis soleil plus haut à80 km ; diagnostic de transmission inspecté.
- Terre à30 km : comparaison identique sauf ombres, écart moyen3,23/255, maximum123/255 ;32,1% des pixels assombris de plus de2/255. Ce contrôle confirme un effet visible, pas sa convergence optique.
- Nuages+air ponctuels :19,46 et18,76 ms pour les deux globes,28,09 ms dans la région dense,10,36 contre8,98 ms sur terre avec/sans ombres ; GPU partagé.
- Captures ignorées par Git dans `x64/PlanetPreview/`, `x64/PlanetLandShadow/`, `x64/PlanetLandShadowSansOmbres/` et `x64/ShadowDiagnostic/`.
- Aucune vérification E2E en mouvement ; les pôles, le raccord et l'approche restent à juger en vol.
- Après intégration : Release x64 et72 shaders du projet compilés, puis variante Planète ; captures en orbite à800 km et à60 m sur la mer FFT, sans erreur de démarrage. Nuages+air ponctuels27,65 et17,75 ms.
- Végétation détaillée vérifiée avec les assets locaux déjà préparés de main :13610 imposteurs de feuillus, zéro dépassement ni plante flottante ; capture à567,2 m au-dessus du sol. GPU total37,97 ms, dont14,44 ms nuages+air ; cette vue ne valide pas un budget global.
