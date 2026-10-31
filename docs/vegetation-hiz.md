# Occlusion hiérarchique de la végétation

**Statut : version intégrée à main sur demande le 2026-10-27.**
- Suite de `optimisation-vegetation.md`.
- Base Git : `piste/vegetation-hiz-base` ; intégration : `jalon/25-vegetation-performance-main`.
- Objectif : dégager une marge au-dessus des quelque 30 FPS signalés en forêt, sans changer le rendu, le peuplement ou la portée.
- **Toujours actifs depuis le 2026-10-30 :** la profondeur matérielle partout, le HiZ hors des vues de diagnostic. Leurs témoins, le HiZ coupé, la profondeur historique et les modes intercalés, sont retirés : `log/vegetation-hiz-historique.md`.

**La profondeur courante :**
- Le terrain, les objets et tous les maillages proches sont dessinés dans leur ordre habituel.
- La profondeur D32 se lit en R32 depuis une ressource typeless ; son format de dessin ne change pas.
- Une pyramide R32 réduit par minimum, puisque le moteur utilise le Z inversé.
- Le ciel et le remplissage hors écran valent zéro ; ils ne peuvent masquer une plante.
- La pyramide utilise l'image courante, sans réutilisation temporelle.
- À 1280 × 720 : texture de 2048 × 1024, douze niveaux, environ 10,67 Mio de texels et 26 descripteurs.

**Le test d'une plante :**
- Les quatre carrés de vues bornent l'enveloppe raster de l'imposteur, avec marges et repli aux frontières de vue.
- La profondeur est bornée sur les moments HALF réellement téléchargés, dans toutes les vues et tous les mipmaps.
- La reconstruction tient compte des vues d'alpha infime, des filtrages séparés et des bases trigonométriques imparfaitement orthogonales.
- Les divisions mal conditionnées, non-finis, passages du plan proche et sorties de l'écran restent visibles.
- Le minimum des texels HiZ couvrant tout le rectangle doit être strictement devant la borne de profondeur de la plante.
- La boîte physique du modèle seule ne suffit pas pour les imposteurs ; elle n'est pas utilisée comme preuve de rejet.
- Les gardes numériques sont conservatrices et se vérifient par les comparaisons d'images ; elles ne constituent pas une preuve formelle de toute implémentation matérielle.
- Un imposteur garde son dessin intégral lorsque cette borne n'est pas admissible.

**Le masque GPU :**
- Les sources, la classification, les arguments de dessin et leurs préfixes restent intacts.
- Un masque de visibilité de 128 Kio est reconstruit à chaque image ; toute plante visible ou incertaine inscrit son bit par une opération OR.
- Une collision de hachage conserve une plante cachée ; elle ne peut retirer une plante visible.
- Le vertex shader des proxies rejette les absents avant le calcul du rectangle et le travail des pixels.
- Tous les maillages puis tous les proxies gardent l'ordre de dessin initial, y compris les cas de profondeur égale.
- `hiz_rejected_candidates` compte les décisions d'occlusion ; `hiz_rejected` tient compte des collisions du masque.
- Les comptes historiques et ceux par modèle décrivent toujours le peuplement source.

**La mesure :**
- Le 2026-10-27, HiZ coupé contre actif, dans le même exécutable : le protocole est dans `log/vegetation-hiz-historique.md`.
- Le champ de temps `draw` comprend maillages, construction HiZ, test et dessin des proxies restants.
- `hiz_gpu_samples_ms` sépare construction et culling ; les horodatages détaillés restent réservés au batch.
- La synthèse durable est dans `../tools/foliage/results/2026-10-27/hiz.json` ; captures et rapports bruts sous `x64/VegetationHiZ/`.
- Les essais écartés et les séries perturbées sont consignés dans `log/optimisation-vegetation-historique.md`.

**La profondeur des maillages proches :**
- Une variante conserve la couleur et toutes les découpes alpha du shader original, avec la profondeur interpolée par le matériel.
- Elle retire la sortie `SV_DEPTH` recalculée, permettant au GPU de rejeter plus tôt les fragments cachés.
- Aucun attribut `earlydepthstencil` n'est forcé ; les trous alpha ne doivent pas écrire de profondeur.
- Elle est la seule depuis le 2026-10-30 : le shader original, à profondeur recalculée, est retiré.
- Depuis le round 3 (`optimisation.md`), cette variante écrit sa profondeur seule, puis sa couleur en profondeur égale ; la borne du test sert aussi de profondeur conservatrice aux imposteurs.
- Deux avertissements FXC d'initialisation potentielle apparaissent dans la fonction appelée par le wrapper ; les branches concernées retournent un résultat initialisé ou rejettent le pixel. Ils restent visibles dans le log de compilation et demandent les comparaisons d'images.
- Sur quatorze vues, la profondeur matérielle change seulement 25 pixels au total, aux égalités de profondeur ; le HiZ seul garde les quatorze images strictement identiques.

**Le gain mesuré :**
- Rendu végétal de 10,30 à 4,64 ms en forêt tempérée, de 8,21 à 3,46 ms en tropicale, de 5,95 à 4,27 ms en boréale ; au désert, un surcoût de 0,38 à 0,54 ms.
- Mesuré par une comparaison intercalée des quatre états, retirée avec les témoins : `log/vegetation-hiz-historique.md`.
- Ces temps GPU ne sont pas une garantie de FPS ; le terrain, le placement et le coût CPU restent présents.

**La conservation du rendu :**
- Quatorze vues de six familles climatiques, mêmes comptes par modèle, mêmes représentations et aucun dépassement.
- HiZ seul : quatorze images strictement identiques, avec la profondeur historique comme avec la profondeur matérielle.
- Variante finale contre témoin historique : 25 pixels modifiés au total sur quatorze images de 1280 × 720, aux égalités de profondeur.
- Banc général sur six lieux et cinq hauteurs, avec `--before tools/banc_qualite_reference.json` : 736 crops identiques sur 745 ; dix pixels modifiés au total.
- Les 59 p95 comparés entre le témoin courant et la variante finale ne montrent aucune nouvelle dégradation de plus de 10 %.
- Les écarts antérieurs à la référence canonique, acceptés au jalon 24, restent présents ; ni référence ni métriques ne sont modifiées.

**Les limites à garder visibles :**
- Le placement et ses bruits sont encore recalculés ; le HiZ intervient au dessin.
- L'occlusion à l'intérieur du groupe des imposteurs n'alimente pas cette pyramide ; les maillages proches et le terrain sont ses occluseurs.
- Le masque conserve des faux visibles ; cela réduit le gain, sans éclaircir le couvert.
- Les autres rendus doivent être suspendus pour juger le temps total et les FPS.
