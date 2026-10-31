# Spike : océan FFT et écume persistante

**Statut :** aspect validé en vol le 2026-10-26 ; rebase sur main 083bfb1, puis intégration au jalon/23-mer-fft-main.
**Jalon initial :** jalon/22-mer-fft ; base 47c404b conservée sous piste/mer-fft-spike.

**Objectif**
- Repartir sur un noyau proche neuf après le rejet des filets blancs et des bandes de mousse.
- Le premier jet reste au tag `piste/mer-animee` ; sa doc est dans `log/recherche-mer-historique.md`.

**Architecture**
- Spectre JONSWAP à fetch limité, étalement de Donelan-Banner, houle séparée.
- Quatre cascades 256² : tuiles de 1 103, 113,1, 11,57 et 1,183 m ; bandes disjointes.
- Choppiness 1,25, amortie sous 40 cm de longueur d'onde ; les rides capillaires restent proches du modèle linéaire.
- Spectre initial précalculé ; évolution temporelle, FFT des lignes puis des colonnes.
- Sorties communes : déplacement XYZ, cinq dérivées, premiers et seconds moments des pentes ; mips à chaque image.
- Normale par inverse du Jacobien horizontal ; covariance non résolue transformée avec ce Jacobien.
- Écume déposée selon le Jacobien ; densité et fraîcheur dans deux cartes toriques 512² de 128 et 1 024 m.
- Dérive de 0,03 U dans le sens du vent ; densité dissipée à 0,22/s, fraîcheur à 1,6/s.
- Pores périodiques multiéchelles précalculés sur GPU ; mousse blanche éclairée par la surface, traînées selon le vent.
- Environ 40 Mio de ressources nominales ; aucune texture mondiale.
- Hauteur locale pour la caméra, quatre itérations sur GPU et lecture de 16 octets ; garde de 75 cm.
- Le compteur FFT sépare la simulation du reste des calculs GPU.
- Sur main : SRV t11 à t16, après l'ombre t9 et la carte planétaire t10 ; horodatages FFT 6 et 7, distincts des objets.
- Diagnostics de main conservés de 1 à 26 ; foam, glint, foamfresh, foamold et crest ajoutés de 27 à 31.

**Planète**
- Ciel, atmosphère, couleur des fonds, terrain et maillage sphérique conservés.
- Plan tangent transporté ; coordonnées accumulées en double sur CPU.
- Fractions modulo les tuiles et différences d'indices entiers dans les shaders.
- Cartes d'écume vidées après un saut de caméra ou un changement de spectre.
- Déplacement amorti par la profondeur ; vagues incluses dans la marge de visibilité.

**Limites du spike**
- Vent uniforme et houle réglés par vue ; carte de vent planétaire à raccorder.
- Déferlement côtier et réfraction non traités.
- Raccord lointain simplifié vers Cox-Munk et Monahan ; couverture proche non calibrée sur Monahan.
- Reflet à 400 km : écart moyen de 2,8 % à 12 m/s, 6,2 % à 24 m/s ; la cible de 5 % n'est donc pas atteinte en vent fort.
- La variation mesurée sur mer figée quand le maillage glisse n'est pas supprimée.
- Champ de hauteur : pas de lame retournée ni de gouttelettes.
- La réussite visuelle précède l'intégration ; compilation et moyennes ne suffisent pas à valider la mousse.

**État**
- Aspect accepté par l'utilisateur après essai ; le raccord au vent planétaire et les limites ci-dessus restent ouverts.
- Saut de caméra : hauteur du sol en cache et lecture GPU de l'ancienne position invalidées avant la collision.
- Banc initial sur 30 lieux, stabilité, pôles, intégration à main et coût : [mesures et limites dans le log](log/spec-mer-fft-spike-historique.md).

**Essayer et mesurer**
- Palette `tools/tests/2026-10-26-mer-main.txt`, par `-Parcours` du lanceur de jeu (`lancement.md`) ; F1 à F7 pour la mer, F8 et F9 pour les forêts, F10 pour l'orbite, F11 et F12 pour les pôles.
- Quatrième colonne facultative : vitesse du vent, direction en degrés, hauteur significative de houle.
- MYPLANETENGINE_OCEAN_WIND fournit ces trois nombres au démarrage.
- MYPLANETENGINE_CAPTURE_FRAME fixe l'image de capture pour laisser mûrir les traînées.
- tools/banc_qualite.py --reuse-sites précédent/qualite.json réemploie les lieux et caps ; toutes les images, tous les masques et tous les scores sont recalculés.

**Provenance et code**
- Simulation et matière d'écume adaptées de [Noniv/web-ocean](https://github.com/Noniv/web-ocean), commit a07c7fd522ef0a897601c114f927a49d93d95520.
- MIT, copyright 2026 Maksymilian Dendura ; licence conservée dans third_party/web-ocean/LICENSE.
- Ordonnancement DX12, barrières, transport du plan et coordonnées toriques précises propres au spike.
- Ocean.cpp / Ocean.h : ressources et ordonnancement ; OceanCompute.hlsl : simulation ; OceanSurface.hlsli / Sea.hlsli : géométrie et lumière ; OceanUniform.hlsli : constantes.
