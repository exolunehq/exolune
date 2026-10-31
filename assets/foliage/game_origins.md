# Modèles de jeu : sources et conversion

- **Pin :** « Pine Tree », par evolveduk. [Source](https://sketchfab.com/3d-models/pine-tree-d45218a3fab349e5b1de040f29e7b6f9), [licence CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Copie source issue de [godot-forest-demo](https://github.com/GamesNotDeveloped/godot-forest-demo/tree/623212ffeb4efbf4c95323a4a6a57e726be4f6e9/objects/pine-tree-1).
- **Feuillu :** « Free Realistic Tree 10 », modèle Tree10_1, par Rakshi Games. [Source](https://opengameart.org/content/free-realistic-tree-10), [licence CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).
- **Modifications :** conversion des maillages et textures vers les formats du moteur ; adaptation du seuil alpha ; génération des volumes et imposteurs. Les normales du feuillu sont décodées depuis le format Unity.
- **Reconstruction :** `python tools/foliage/telecharge_jeu.py`, puis `python tools/foliage/importe_jeu.py`, puis `python tools/foliage/bake.py game_fir game_broadleaf --volume-res 64`. Dépendances : numpy, Pillow, numba et UnityPy.
- **Limites :** 5 627 triangles pour le pin et 3 308 pour le feuillu. L'aspect et le coût en vol restent à évaluer. La rugosité du feuillu est une valeur constante, sa source fournissant une carte Unity de brillance et non une carte PBR de rugosité.

This work is based on "Pine Tree" (https://sketchfab.com/3d-models/pine-tree-d45218a3fab349e5b1de040f29e7b6f9) by evolveduk (https://sketchfab.com/evolveduk), licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).

"Free Realistic Tree 10" by Rakshi Games (https://opengameart.org/content/free-realistic-tree-10), licensed under CC BY 3.0 (https://creativecommons.org/licenses/by/3.0/).
