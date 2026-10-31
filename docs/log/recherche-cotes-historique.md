# Historique des côtes

**Les sections dépassées de `../recherche-cotes.md`.** L'état présent y est.

## 2026-10-24 · Le plan de l'étape 1, avant de la faire

Remplacé le 2026-10-25 par l'étape faite sur la branche `plages`, tag `piste/plages` : la limite de pente y est de 0,12 à 0,22, et toutes les bandes suivent l'exposition de la côte.

**L'étape 1, petite et mesurable :**
- **Le changement :** dans `GroundMaterials`, `beachBase` passe de `SpreadStep(5, 25, elevation - 60 * local.y)` à environ `SpreadStep(1.5, 3.5, elevation - 7 * local.y)`. Le bruit déplace la limite de ±1 m au lieu de ±9 m ; `beachSigma` suit, 1,04 au lieu de 76,7. Un facteur de pente retire le sable au-dessus de 0,12 à 0,22, par la règle universelle.
- **La mesure, avant le moteur :** le banc CPU de la section 6 donne la distribution des largeurs.
- **La mesure, dans le moteur :** `banc_descente.py` avec `BANC_MATERIAU=beach`, de 1 500 km au sol ; le banc de qualité, sans p95 dégradé.
- **Ce qui change à l'œil :** les terres de 3 à 25 m reprennent les couleurs du climat, herbe ou sol nu. Derrière une vraie plage, c'est la dune et sa végétation.

**Le statut d'alors :** « aucun code changé » ; les scripts du portage CPU, `cp.py` et `t2.py` à `t7.py`, étaient dans un dossier de travail volatil. Ils sont depuis dans `tools/cotes/`.
