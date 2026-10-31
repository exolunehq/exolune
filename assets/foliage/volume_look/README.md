# Variantes d'aspect et éclairage précalculé — 27 octobre 2026

- **Sources :** `game_broadleaf` et `game_shrub` ; détails et licences dans `assets/foliage/game_origins.md` et `assets/foliage/game_shrub_origins.md`. Le pin est copié sans modification.
- **Feuillage :** copies de cartes de feuilles d'origine orientées autour du point de branche le plus proche. Les branches d'origine, les textures et les bornes restent inchangées. Aucune enveloppe pleine n'est ajoutée.
- **Budgets :** 7 010 triangles pour le feuillu ; 13 406 pour l'arbuste. Les brindilles alpha de l'arbuste restent classées comme branches pour l'éclairage.
- **Éclairage :** rayons dans le volume alpha 64³, départ à 2,25 cellules, six directions locales et seize directions de ciel. Le paramétrage du calcul est dans `bake_metadata.json`.
- **Formats :** `lighting.bin` associe huit flottants par sommet. `impostor_light.bin` associe deux plans RGBA8 aux 60 vues, non prémultipliés, dans le même ordre que `impostor.bin`.
- **Reconstruction :** depuis la racine, `python tools/foliage/volume_assets.py`. Les fichiers sources d'arbres et d'arbuste doivent être préparés au préalable ; dépendances : numpy, Pillow et numba.
- **Limite :** les silhouettes CPU montrent davantage de feuilles, mais l'arbuste reste ouvert. L'aspect et la performance dans l'application restent à évaluer.
