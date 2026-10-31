# Sources et reproduction

**Catalogue du jeu, trouvé par défaut par le moteur dans `assets/foliage/climate_shrubs_v2` :**
- `climate_shrubs_v2` : deux arbres issus de `volume_look_normals` et douze arbustes de six familles climatiques.
- Tout se construit en une commande, depuis la racine : `tools\plantes.ps1`. Il enchaîne l'import des sources de jeu ci-dessous, `volume_assets.py`, `volume_assets.py --normals`, puis `arbustes_climatiques_v2.py --preview` et `--final`.
- Le catalogue et ses limites sont décrits dans `../../docs/arbustes-climatiques.md` ; les binaires générés restent ignorés par git.
- Un catalogue construit avant le 2026-10-29 garde des imposteurs moyennés en sRGB, plus sombres : les recuire selon `../../docs/lancement.md`.

**Modèles de jeu sources :**
- Pin [Pine Tree](https://sketchfab.com/3d-models/pine-tree-d45218a3fab349e5b1de040f29e7b6f9), evolveduk, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) : 5 627 triangles.
- Feuillu [Free Realistic Tree 10 / Tree10_1](https://opengameart.org/content/free-realistic-tree-10), Rakshi Games, [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) : 3 308 triangles.
- Arbuste [Searsia Lucida](https://polyhaven.com/a/searsia_lucida), James Ray Cock et Jenelle van Heerden, CC0 : 7 232 triangles ; crédits dans `game_shrub_origins.md`.
- Modèles d'artistes avec branches maillées et feuillage découpé ; la texture porte les feuilles et rameaux fins.
- Les sources sont conservées dans le cache avec URL et SHA-256 figés dans `tools/foliage/sources_jeu.json`.
- Conversion des repères, des UV Unity et des normales empaquetées ; atlas de deux matériaux en 2 048 × 1 024.
- Les cartes de rugosité du pin sont conservées ; le feuillu utilise une rugosité constante, faute de carte source exploitable.
- Crédits complets et transformations : `game_origins.md`.

```powershell
python -m pip install numpy pillow numba UnityPy
python tools/foliage/telecharge_jeu.py
python tools/foliage/importe_jeu.py
python tools/foliage/bake.py game_fir game_broadleaf --volume-res 64
python tools/foliage/importe_arbuste.py
python tools/foliage/bake.py game_shrub --volume-res 64
./tools/lance.ps1 -Build
```

- `material.bin` : magic `FOLMAT01`, uint32 largeur et hauteur, atlas RGBA8 de normales OpenGL, puis RGBA8 de masques AO, rugosité, transmission, alpha 255.
- Le moteur juxtapose ces deux atlas à la couleur dans le buffer du maillage ; le bit 0 de `unused` active leur lecture.
- Le chemin actif crée aussi trois tableaux de textures par modèle : couleur sRGB, normales et masques UNORM, une couche par matériau ; anisotropie ×8 et mipmaps pondérés par la couverture.
- Le bit 1 choisit le relais et l'alpha stable de `game` et des arbustes ; le bit 2 active ces textures matérielles.
- Les imposteurs et le volume gardent les normales du maillage, sans les détails de la carte de normales ni le reflet du matériau proche.
- Les budgets de triangles sont ceux des fichiers importés ; aucun niveau de qualité AAA ni gain de FPS n'est validé avant jugement en vol.
- Aucun banc, test ou rendu de vérification n'a été lancé avant le vol demandé.

**Fichiers, little-endian :**
- Les variantes de feuillage se reconstruisent après les modèles de jeu : `python tools/foliage/volume_assets.py`, puis `python tools/foliage/volume_assets.py --normals`. Le catalogue courant reprend ces deux arbres ; `MYPLANETENGINE_FOLIAGE_ASSETS` désigne un autre catalogue. Les modèles sources restent dans `game_*`.
- `lighting.bin` : magic `FOLLIT01`, uint32 nombre de sommets et stride 8 flottants, puis ciel, soleil +X/−X/+Y/−Y/+Z/−Z et masque de feuille par sommet, tous dans [0, 1].
- `impostor_light.bin` : magic `FOLIL001`, quatre uint32 azimuts, élévations, largeur, hauteur ; deux plans RGBA8 non prémultipliés, dans l'ordre des vues d'`impostor.bin`, portant les mêmes huit champs.
- `mesh.bin` : magic `FOLMESH1`, quatre nombres uint32 donnant sommets, indices, largeur et hauteur de l'atlas, puis uint32 nombre de matériaux et deux float3 de bornes. Sommets `float3 position, float3 normale, float2 UV, float matériau`, indices uint32, puis atlas RGBA8 sRGB, tuiles matériaux juxtaposées. Couleur non prémultipliée.
- `volume32.bin`, `volume64.bin`, `volume128.bin` : magic `FOLVOL01`, uint32 résolution 32, 64 ou 128 et nombre de niveaux 6, 7 ou 8, bornes float3 min et max. `volume.bin` est une copie du 64 par défaut. Niveaux de la résolution choisie à 1³, X le plus rapide puis Y, Z ; voxel `float4 couverture, albédo RGB linéaire`, puis `float4 normale XYZ, dispersion`. Au niveau de base, la couverture est `1-exp(-0,5 × surface alpha / aire moyenne des faces)`. Chaque parent conserve la transmission de ses enfants : produit le long de deux cellules, moyenne des quatre colonnes, puis moyenne des extinctions des trois axes. Les couleurs et normales restent pondérées par les surfaces. Dispersion : 1 moins la longueur de la normale moyenne avant normalisation. La répartition des échantillons et la moyenne isotrope restent approximatives.
- `impostor.bin` : magic `FOLIMP01`, uint32 nombres d'azimuts 12, élévations 5, largeur et hauteur 128, bornes float3 min et max, float rayon. Puis 60 images RGBA8 sRGB, puis 60 images float4 normale objet XYZ, profondeur ; ordre élévation, azimut, ligne, colonne. Couleur non prémultipliée. Un test alpha 0,5 sur une image de 256², réduit en quatre échantillons, conserve une couverture fractionnaire.
- Azimut θ=2πa/12 ; élévation φ=πe/8. Caméra `(sinθ cosφ, sinφ, cosθ cosφ)`, droite `(cosθ,0,-sinθ)`, haut `(-sinθ sinφ,cosφ,-cosθ sinφ)`. Centre `(0 ; 0,5 ; 0)` ; image orthographique de −rayon à +rayon sur chaque axe, haut de l'image en haut ; profondeur `dot(position-centre, caméra)` croissante vers la caméra. Les normales double face sont orientées vers la caméra.

**Les modèles photo et stylisés,** essais du prototype volumique, sont retirés avec lui ; ils restent au tag `jalon/24-vegetation-detaillee-main`, et leur histoire dans `../../docs/log/prototype-vegetation-volumique-historique.md`.
