# Historique des textures générées

**Les sections dépassées de `../spec-textures-generees.md`,** sorties le 2026-10-30. L'état présent y est.

## Les autres pistes tirées de la comparaison, ce qu'elles sont devenues

- **Les cailloux et pierres semés :** les objets de proximité, `../spec-objets-proximite.md`.
- **Les ombres portées du relief :** l'horizon par sommet, `../recherche-ombres-relief.md`.
- **La brume :** la brume de la couche limite, `../recherche-profondeur-atmospherique.md`.
- **Les brins d'herbe :** jamais faits, `spec-herbe.md` ; des touffes de brins générés à la place, parmi les objets de proximité.
- **La mer près du rivage :** la mer FFT, `../spec-mer-fft-spike.md` ; les plages, `../recherche-cotes.md`.
- **La profondeur de champ :** pas faite.

Le texte d'origine :

### Les autres pistes tirées de la comparaison

**Hors de la voie B, mais nécessaires pour approcher la cible :**

- **Les cailloux et pierres semés en géométrie,** étape E. C'est ce qui pèse le plus dans le premier plan de la cible, après les rides.
- **Les ombres portées du relief.** Le moteur n'en a pas : les vallées restent éclairées. Deux pistes : une carte d'ombre en cascades, ou un lancer de rayon sur le relief.
- **La brume.** La perspective aérienne de Hillaire est en place, mais la cible montre un air plus chargé. Il faut régler la densité des aérosols et ajouter une brume de vallée en hauteur. Réglage rapide.
- **Les brins d'herbe et les arbustes secs,** en géométrie : `spec-herbe.md`, jamais faite.
- **La mer près du rivage :** dégradé de couleur avec la profondeur, vagues et écume. Une piste à part entière.
- **La profondeur de champ,** en dernier, si elle sert encore.

## Étape 2 : les tours de la roche générée

Avant la photo de paroi, `jalon/15-roche-photo`.

- **Six tours de banc sur la roche :**
  - **Écailles :** un second niveau de facettes de 40 cm cernait chaque facette d'une ombre. Retiré.
  - **Ardoises :** toutes les limites de strates étaient creusées et assombries. Désormais, une couche sur trois seulement recule, et peu.
  - **Cratères :** les pierres des éboulis étaient des disques, tranchés net quand ils débordaient de leur cellule. Refaites en fragments anguleux, chacun sa cellule de Voronoï rétrécie, posés sur de la poussière.
  - **Barres noires :** les crevasses étaient trop sombres. Adoucies.
- **État :** la roche se lit en dalles et en fissures discrètes, mais elle reste plate. Le relief réel, en géométrie, avec des ombres de contact, devient le levier principal.

## La structure de la roche au-delà de 8 m

**Retirée le 2026-10-24,** avec les familles de roche et la parallaxe, `jalon/16-une-roche` : la roche est une seule photo, sans tuile dessinée de 64 m.

Statut : fait le 2026-10-21 ; à juger en vol.

**Le constat :** la tuile de roche se répète tous les 8 m. Vue de 15 à 50 m, la paroi reste un quadrillage uniforme de bancs et de diaclases, sans corniches, couloirs ni contreforts.

**Le principe : une troisième tuile pour la roche, de 64 m en 1024 texels, 6 cm par texel.** C'est le pendant du niveau fin, à l'autre bout de l'échelle.

- **Les grands bancs :** des couches de 2 m groupées en bancs de 2 à 8 m. Chaque banc avance ou recule de ±0,5 m et finit en corniche arrondie. Les bancs tendres reculent sous les durs.
- **Les grandes fractures :** tous les 4 à 16 m selon le banc. Quatre sur dix sont des couloirs de 0,3 à 1,2 m de large et de 0,6 m de profondeur, qui découpent des contreforts.
- **Les couleurs :** une teinte par banc, et des rideaux de vernis de quelques mètres de large qui coulent le long de la paroi.
- **Même lecture :** pavage aléatoire, cellules de 32 m, 64 m les divisent ; projection biplanaire, strates tournées vers la verticale. Couleur et occlusion multipliées, pentes et hauteurs ajoutées, moyenne conservée.
- **Le maillage porte ce relief** là où ses mailles le permettent, comme celui des autres tuiles.
- **La caméra :** ce relief atteint ±1 m. La hauteur sous la caméra est donc lue après la passe de relief, et non plus avant.

**La mesure :** vues à 50 m, 15 m et 1,5 m sur pente raide, avant et après ; le banc de tremblement ; le coût.

**Critère :** de 15 à 50 m, une paroi structurée et non plus un quadrillage, sans tremblement en plus, pour moins de 0,3 ms.

**Résultats :**

- **De 15 à 50 m,** les parois montrent des corniches, des bancs en retrait, des couloirs : le quadrillage a disparu.
- **De près,** les corniches découpent leur silhouette, et l'herbe tient sur les bancs en retrait.
- **Coût :** +0,10 à 0,22 ms sur la roche.
- **Tremblement, roche à 3 m, avec et sans lissage temporel :**

| Variante | Roche à 3 m | Sol sec à 1,3 m |
|---|---|---|
| Avant la tuile de 64 m | 0,05 / 0,27 | 0,06 / 0,39 |
| Tuile de 64 m, bancs en marches | 0,12 / 0,58 | 0,08 / 0,51 |
| Bancs raccordés en rampes de 0,6 m, retenu | 0,10 / 0,52 | 0,08 / 0,51 |
| Sans relief dans le maillage | 0,04 / 0,25 | 0,05 / 0,35 |

- **D'où vient le tremblement :** du relief de ±1 m que porte le maillage. Filtrer à 16 mailles au lieu de 8 ne gagne que 0,02 ; porter le relief jusqu'aux mailles de 8 m ne change rien.
- **Il reste faible :** 0,10 sur 255 en moyenne, sous le 0,17 du filtrage à 2 mailles écarté plus tôt. Il se concentre aux bordures entre roche et herbe. À juger en vol.
- **La caméra** lit maintenant la hauteur du sol après la passe de relief : plus de marge fixe de 30 cm.
