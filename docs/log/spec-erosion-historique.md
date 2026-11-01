# Historique de la spec d’érosion

**Modèles côtiers remplacés ; voir [la spec actuelle](../spec-erosion.md).** Piste `piste/erosion-globale`.

**2026-10-31 · Le profil en distance.**
- **Le modèle :** paroi tracée depuis le rivage estimé jusqu’au recul, hauteur extrapolée du point.
- **Le défaut rendu :** le proxy ignore le détail ; montagnes rabattues au platier, canaux intérieurs et parois kilométriques.
- **Les mesures de pente seules ne le validaient pas :** elles ne contrôlaient ni l’abaissement maximal ni les fenêtres voisines.

**2026-10-31 · Le contour par la pente côtière.**
- **Le modèle :** remappage de h, Hc entre 8 et 400 m, abaissement borné à Hc + 1 m.
- **Le défaut rendu :** G entre 0,03 et 0,1 m/m sous-estime les versants réels de 30 à 45° ; les parois restent invisibles à 4 km.

**2026-10-31 · Le contour par la pente locale du détail.**
- **Le modèle :** `SLOPE_KM = 0.3`, sept octaves de 50 km à 566 m ; deux parois de plus de 100 m mesurées, visibles en vol.
- **Le défaut rendu :** Hc change sur une échelle plus petite que son platier ; coupes enclavées et terre entre la paroi et la mer.
- **L’inondation, trois fenêtres de 10 km au pas de 50 m :** 19,432 %, 1,373 %, 3,883 % des coupes de plus de 10 m inaccessibles ; centres dans la spec actuelle.

**2026-10-31 · La variante de pente attendue, comparée au filtre de 9 km.**
- **Le coefficient RMS :** 0,0002283923092 /m ; 65 536 directions fixes, douze octaves ridgées à amplitude unitaire, sans plis ni ravines ; amplitude tectonique avant le terme des parois de vallée.
- **Les parts enclavées :** 8,411 %, 0,555 %, 0 % ; le seuil de 5 % échoue aussi sur la première fenêtre.
- **Les trois coupes fixes :** 256,328 / 111,488 / 132,693 m ; platiers −1,069 / −1,770 / −2,199 m ; aucune terre devant le pied.
- **Le choix :** filtre de 9 km, qui conserve les parois hautes et la côte basse observée sans proxy statistique supplémentaire ; aucun des deux choix ne garantissait la connexité avec la bande symétrique.

**2026-10-31 · La bande symétrique autour du rivage estimé.**
- **Le modèle :** `abs(shoreKm / shoreMetric) < W + 1 km`, extinction sur 500 m ; proxy brut de 8 km ; pente filtrée à 9 km.
- **Le défaut rendu :** une plage et des collines devant la paroi tropicale, une coupe noyée à l’intérieur ; le détail déplace le rivage hors de la bande.
- **Les fenêtres :** 8,889 %, 0 %, 0 % enclavés ; les 108 cellules isolées de la première fenêtre restent inaccessibles même sans plafond d’abaissement dans la bande.
- **Les distributions Hc précédentes, médiane/p90/maximum :** 149,855/257,947/337,176 ; 82,360/121,832/177,379 ; 91,426/159,114/245,786 ; 119,426/247,176/340,331 ; 137,097/168,253/193,122 ; 124,299/224,383/329,615 m ; mêmes six centres que la spec actuelle.
- **La correction :** côté mer, ouverture jusqu’au proxy ; côté terre, ajout du déplacement `relief / coastSlope`, plafond de 8 km ; Hc reste inchangé.

**2026-10-31 · Le cinquième passage, sans contrôle d’accès marin.**
- **Le rendu graine 0 :** paroi tropicale et stack validés ; plus de bande de terre devant elle ni de fosse intérieure ; falaise propre à 3° S.
- **Le défaut graine 1 :** canaux et anneaux de falaise autour des lacs de la plaine à −65,00789/−113,42094.
- **L’ablation sur 10 km au pas de 50 m :** bande symétrique 15,720 % abaissé de plus de 10 m ; ouverture seule 16,121 % ; extension intérieure seule 16,198 % ; ensemble 16,200 %.
- **Les parts enclavées correspondantes :** 31,286 %, 32,735 %, 32,579 %, 32,574 % ; aucun point de mer originale selon le seuil de −50 m dans cette fenêtre.
- **La cause :** Hc régional coupe les bas reliefs sans vérifier l’accès aux vagues ; aucun lien de vallée du niveau 0 ne creusait les points concernés.
- **Les deux extensions aggravent légèrement un défaut antérieur :** les retirer seules ne le corrige pas ; l’ouverture côté mer est conservée.
- **Les distributions Hc de graine 0 :** 134,698/251,737/337,176 ; 64,505/114,265/177,379 ; 78,409/162,371/245,786 ; 92,216/159,570/340,331 ; 131,832/163,650/193,122 ; 102,872/208,796/329,615 m ; médiane/p90/maximum aux six centres de la spec.
- **La correction retenue :** un témoin marin avant érosion à 3 km dans la direction du large ; les parois validées et la face froide restent identiques, la fenêtre glaciaire n’est plus abaissée.
