# Arbuste de jeu : source et conversion

- **Source :** [Searsia Lucida](https://polyhaven.com/a/searsia_lucida), variante `searsia_lucida_f_LOD0`, par James Ray Cock (modélisation) et Jenelle van Heerden (photographie).
- **Licence :** [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) ; usage et redistribution libres.
- **Maillage :** 7 232 triangles, branches et feuilles d'origine. L'écorce opaque utilise le matériau 0 ; les feuilles et rameaux découpés utilisent le matériau 1.
- **Textures :** couleurs, alpha séparé, normales OpenGL, occlusion et rugosité de Poly Haven. La transmission est une valeur constante par matériau.
- **Modifications :** conversion au format du moteur, centrage horizontal, hauteur normalisée, génération du volume et des imposteurs. Le découpage alpha est adapté au seuil du moteur ; le modèle source utilise une transparence progressive.
- **Reconstruction :** `python tools/foliage/importe_arbuste.py` télécharge les fichiers figés par SHA-256 et crée les atlas et le maillage ; `python tools/foliage/bake.py game_shrub --volume-res 64` crée volume et imposteurs. Dépendances : numpy, Pillow et numba.
- **Limite :** l'aspect et le coût en vol restent à apprécier.
