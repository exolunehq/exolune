# Variante de normales des feuilles — 27 octobre 2026

- **Base :** `volume_look`. La géométrie, les UV, les indices, les atlas et les bornes sont identiques ; le pin est recopié sans modification.
- **Feuillage :** normales originales orientées vers l'extérieur puis mélangées à 55 % avec un champ radial ancré au point de branche le plus proche de chaque carte. Ce champ comporte un biais vertical de 0,15. L'écorce et les brindilles ne sont pas modifiées.
- **Référence :** principe d'ancrage des normales « Parent Puffiness » dans la [documentation SpeedTree](https://docs9.speedtree.com/modeler/doku.php?id=card_generator). Cette variante n'utilise pas le logiciel SpeedTree.
- **Reconstruction :** `python tools/foliage/volume_assets.py --normals` ; les options `--mix` et `--up` règlent le mélange et le biais. Le volume et les normales d'imposteurs sont recalculés. Les deux fichiers de visibilité sont identiques à la base car les surfaces et leur alpha ne changent pas.
- **Limite :** le modelé doit être comparé en moteur aux vues de référence ; cette variante ne garantit pas à elle seule un aspect plus réaliste.
