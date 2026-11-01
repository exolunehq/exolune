# Archive : le vaisseau triangulaire, forme N

**Le vaisseau du 2026-10-31, remplacé ensuite par un nouveau dessin.** La pyramide d'Antigravity, creusée sous une bulle en goutte bordée de métal, avec les détails v3 (`README.md` de ce dossier, état d'alors).

- **Le paquet `vaisseau.vsx`** est en version 3. Pour le revoler, le copier dans `assets/vaisseau/` à la place du paquet courant ; l'eau de la verrière et les jets attendent alors les nombres de la forme N, ceux de `Ship.hlsli` et `ShipPlume.hlsli` à cette date.
- **`vaisseau_travail.blend`** est la scène de travail ; le GLB s'en exporte par `exporter.py`.
- **Pour le régénérer :** depuis ce dossier, `blender -b <spaceship.blend d'Antigravity> --python preparer.py`, puis `details_v3.py`, puis `python paquet_moteur.py`. Les textures du cockpit sont ici ; celles de la coque et de la poupe se refont.
- **Aperçus :** `exterieur.png`, `pilote.png`.
