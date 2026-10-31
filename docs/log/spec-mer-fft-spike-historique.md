# Spike FFT : mesures du 2026-10-26

**Piste mesurée :** base 47c404b, tag `piste/mer-fft-spike`, avant le commit du `jalon/22-mer-fft`.
**État courant :** [spec-mer-fft-spike.md](../spec-mer-fft-spike.md).
**Sorties locales :** x64/MerFFT/validation et x64/MerFFT/qualite.

**Protocole**
- Bancs cachés, aucun rendu concurrent du moteur.
- 1280 × 720 ; Debug x64, shaders optimisés.
- Temps simulé : 1/60 s par image, vitesse 1 ; vitesse 0 pour la mer figée.
- Vent contrôlé, direction 70° dans le plan transporté.
- Mesures réalisées avant le commit du jalon ; ancien prototype conservé au tag `piste/mer-animee`.

**Aspect et coût**
- Captures à 1 et 3 m, en mer fraîche à 20 m, en tempête à 20 m et sur la vue utilisateur à 142,4 m.
- Tempête : vent 24 m/s, houle Hs 3,5 m ; capture après 600 images, soit 10 s simulées.
- Vue utilisateur : 142.4 -44.75718 177.39448 22.5 -151.6 ; soleil 15 165.
- Les filets blancs continus et les larges bandes translucides du témoin sont absents de cette capture.
- Les premières captures montraient trop de plis très fins ; choppiness désormais amortie sous 40 cm de longueur d'onde.
- Coût de la simulation complète : 0,13 ms GPU en mer fraîche et en tempête.
- Rendu : 1,27 ms, minimum 1,25 ms, en mer fraîche ; 1,12 ms, minimum 1,10 ms, en tempête.
- Ces temps proviennent du dernier intervalle affiché après 600 images, pas d'un percentile sur une longue session.
- Côte signalée : 3,50 ms de rendu, minimum 3,35 ms, terrain compris, dans la capture précédente à instrumentation graphique identique.
- Aspect à valider en vol ; ces mesures ne prouvent pas le réalisme de l'écume.

**Qualité du terrain**
- tools/banc_qualite.py --sites 30 --reuse-sites utilise les lieux, caps et matériaux cibles du témoin MerAnimee/bench-qualite-volume/qualite.json.
- Toutes les couleurs, tous les masques et toutes les variantes de maille sont recalculés.
- Comparaison requise par --before tools/banc_qualite_reference.json ; référence conservée.
- Les mêmes 3 891 crops sont retenus ; aucun ajouté ou retiré.
- 3 888 crops identiques ; dans chacun des trois autres, un pixel change d'un niveau sur 255.
- Aucun p95 de trou, répétition ou mutation ne régresse de plus de 10 % par rapport au témoin.
- Les six dépassements suivants de la référence sont strictement identiques à ceux du témoin.

| Matériau | Hauteur | Mesure | Dépassement de la référence |
|---|---|---|---|
| Roche | 12 m | Répétition p95 | +14,9 % |
| Roche | 3 000 m | Trou p95 | +314,3 % ; trois crops seulement |
| Sable | 50 m | Répétition p95 | +50,8 % |
| Éboulis | 12 m | Trou p95 | +66,6 % |
| Neige | 3 000 m | Trou p95 | +21,7 % |
| Neige | 3 000 m | Répétition p95 | +39,1 % |

**Stabilité**
- tools/banc_tremblement_mer.py : caméra fixe, maillage glissant comme en vol ; écart maximal des canaux entre images, moyenné sur les pixels.
- Les valeurs sont en niveaux d'image 8 bits ; l'écart animé inclut le mouvement voulu des vagues.
- Vent frais : 12 / 70 / 1,8 ; côte : même vent ; micro : 4 / 70 / 0,4.

| Vue | Cas | Sol hors mer | Mer | Contraste du détail de mer |
|---|---|---|---|---|
| Fraîche, 20 m | Figée, lissage | — | 0,90 | 10,94 |
| Fraîche, 20 m | Figée, sans lissage | — | 0,93 | 10,94 |
| Fraîche, 20 m | Animée, lissage | — | 2,17 | 11,41 |
| Fraîche, 20 m | Animée, sans lissage | — | 2,19 | 11,41 |
| Côte, 120 m | Figée, lissage | 0,02 | 0,43 | 6,36 |
| Côte, 120 m | Figée, sans lissage | 0,08 | 0,51 | 6,36 |
| Côte, 120 m | Animée, lissage | 0,02 | 0,59 | 6,34 |
| Côte, 120 m | Animée, sans lissage | 0,08 | 0,65 | 6,36 |
| Micro, 1 m | Figée, lissage ou sans | — | 1,06 | 14,33 |
| Micro, 1 m | Animée, lissage ou sans | — | 12,75 | 18,56 |

- Le terrain côtier garde les valeurs du témoin : 0,02 avec lissage, 0,08 sans.
- La mer figée fraîche varie davantage que le témoin analytique, 0,90 contre 0,20 ; la nouvelle géométrie reste sensible au déplacement du maillage.
- Le banc ne prouve donc pas l'absence de scintillement géométrique ; jugement en vol nécessaire.
- Aux pôles nord et sud, à 100 m : masque d'eau blanc sur 921 600 pixels, sans trou visible.

**Reflet lointain**
- tools/banc_mer.py, mode reflet, à 400 km ; lieux -17.36 -26.84 et 55.95 8.07.
- Vent 12 m/s : écart moyen de 2,8 % sur chacun des deux lieux.
- Vent 24 m/s : écart moyen de 6,2 % ; la cible de 5 % de la recherche initiale est manquée.
- La faible queue du reflet est moins bien reproduite en vent fort ; raccord statistique à reprendre avant intégration.
- Le vent planétaire et la couverture proche de Monahan ne sont pas validés par ce prototype à vent uniforme.

**Jugement en vol**
- tools/lance.ps1 avec tools/tests/2026-10-26-mer-fft-spike.txt et x64/MerFFT/MyPlanetEngine.exe.
- F1 et F2 : microrelief ; F5 : tempête ; F7 : vue côtière signalée ; F11 et F12 : pôles.
- Les cartes d'écume repartent au changement de vue ; laisser quelques secondes pour voir les traînées.

**Intégration à main · 2026-10-26**
- Rebase sur main 083bfb1 ; code terrestre du témoin identique à celui de la végétation v3, exécutable Veg3.
- Debug x64 recompilé après le rebase ; ressources de la mer, carte planétaire, végétation et objets réunis.
- Temps : 1280 × 720, Debug x64 avec shaders optimisés, après 600 images ; valeurs du dernier intervalle de titre sur cette machine.
- Banc de qualité sur six lieux du tirage initial, un par matériau ; mêmes caps, cinq hauteurs, toutes les vues recalculées sur les deux exécutables.
- Comparaison par --before à tools/banc_qualite_reference.json, puis comparaison appariée au témoin de main.
- 753 crops communs, tous strictement identiques ; aucun ajouté ou retiré ; aucun p95 ne régresse par rapport au témoin.
- Les quinze dépassements de la référence ci-dessous sont identiques dans le témoin et dans l'intégration ; le tirage de six lieux diffère du banc initial de trente lieux.

| Matériau | Hauteur | Mesure | Dépassement de la référence |
|---|---|---|---|
| grass | 12 m | repeat_p95 | +113,3 % |
| grass | 50 m | repeat_p95 | +11,6 % |
| grass | 200 m | repeat_p95 | +24,1 % |
| rock | 3000 m | gap_p95 | +105,9 % |
| sand | 50 m | repeat_p95 | +25,4 % |
| sand | 200 m | repeat_p95 | +37,8 % |
| scree | 12 m | gap_p95 | +78,2 % |
| scree | 12 m | repeat_p95 | +192,1 % |
| snow | 50 m | repeat_p95 | +13,6 % |
| snow | 3000 m | gap_p95 | +45,3 % |
| snow | 3000 m | repeat_p95 | +68,3 % |
| soil | 12 m | gap_p95 | +242,7 % |
| soil | 12 m | repeat_p95 | +126,5 % |
| soil | 800 m | gap_p95 | +13,7 % |
| mutation | 12 m | p95 | +510,6 % |

- Sorties locales : x64/MerMain/qualite-main-6, qualite-integre-6 et qualite-comparaison-main.json.
- Tempête à 20 m, vent 24 m/s et houle Hs 3,5 m, 600 images : 0,13 ms de simulation, 1,22 ms de rendu, minimum 1,20 ms ; placement d'objets 0,23 ms, objets absents de l'eau.
- Banc de vues de végétation : forêts tempérée et tropicale à 150 m ; les deux images 1280 × 720 sont strictement identiques au témoin, pixel par pixel.
