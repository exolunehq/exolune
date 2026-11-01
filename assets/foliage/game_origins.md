# Game models: sources and conversion

- **Pine:** “Pine Tree”, by evolveduk. [Source](https://sketchfab.com/3d-models/pine-tree-d45218a3fab349e5b1de040f29e7b6f9), [CC BY 4.0 license](https://creativecommons.org/licenses/by/4.0/). Source copy from [godot-forest-demo](https://github.com/GamesNotDeveloped/godot-forest-demo/tree/623212ffeb4efbf4c95323a4a6a57e726be4f6e9/objects/pine-tree-1).
- **Broadleaf:** “Free Realistic Tree 10”, model Tree10_1, by Rakshi Games. [Source](https://opengameart.org/content/free-realistic-tree-10), [CC BY 3.0 license](https://creativecommons.org/licenses/by/3.0/).
- **Modifications:** meshes and textures converted to the engine's formats; alpha threshold adjusted; volumes and impostors generated. Broadleaf normals are decoded from Unity format.
- **Rebuild:** `python tools/foliage/telecharge_jeu.py`, then `python tools/foliage/importe_jeu.py`, then `python tools/foliage/bake.py game_fir game_broadleaf --volume-res 64`. Dependencies: numpy, Pillow, numba and UnityPy.
- **Limits:** 5,627 triangles for the pine and 3,308 for the broadleaf. Appearance and cost in flight remain to be evaluated. Broadleaf roughness is constant: its source provides a Unity gloss map rather than a PBR roughness map.

This work is based on "Pine Tree" (https://sketchfab.com/3d-models/pine-tree-d45218a3fab349e5b1de040f29e7b6f9) by evolveduk (https://sketchfab.com/evolveduk), licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).

"Free Realistic Tree 10" by Rakshi Games (https://opengameart.org/content/free-realistic-tree-10), licensed under CC BY 3.0 (https://creativecommons.org/licenses/by/3.0/).
