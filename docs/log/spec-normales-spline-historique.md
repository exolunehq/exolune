# Historique des normales spline

**Le préfiltre de la spline cardinale,** sorti de `../spec-normales-spline.md` le 2026-10-30, quand ses passes ont quitté le moteur, commit `3a4508a`. Elles restent au tag `jalon/09-normales-spline`. L'état présent est dans `../spec-normales-spline.md`.

**Le plan d'origine :** une B-spline cubique cardinale, qui passe par les sommets. Variation attendue : 0,4 % pour une onde de 8 mailles, contre 17 % pour la normale des sommets. Au banc du 2026-10-21, elle aggravait le tremblement ; la B-spline lissante, sans préfiltre, a été gardée.

**Le préfiltre :**
- **Une B-spline cubique ne passe par ses points de contrôle que si on les préfiltre.** C'est ce qui la rend cardinale.
- **Le préfiltre exact** est l'inverse du filtre [1 4 1] / 6. Sa réponse impulsionnelle vaut √3 · z^|d|, avec z = √3 − 2 ≈ −0,268.
- **Tronqué à 7 coefficients,** de d = −3 à 3, puis normalisé pour que leur somme fasse 1 : les constantes et les pentes uniformes restent exactes. Erreur de troncature d'environ 0,5 %.
- **Séparable :** une passe le long du premier axe de chaque carte, i ou b, puis une passe le long du second, j ou r.

**Le code d'alors :**
- `SplinePrefilter.hlsl` : les deux passes du préfiltre, après le calcul du terrain. Une passe par axe, un fil par sommet.
- Deux tampons de float4 par sommet : le résultat intermédiaire et les coefficients, lus par le pixel shader.
- `SPLINE_SHARPENING`, dans `PlanetSettings.hlsli` : 1, la spline cardinale ; 0, la B-spline lissante ; entre les deux, un mélange. À 0 depuis le banc : le préfiltre ne servait plus, ses passes restaient pour l'essai.
- Leur coût, avec le pixel shader : moins de 0,1 ms en tout ; le préfiltre seul, 0,02 à 0,13 ms au profil du round 4 (`../optimisation.md`).
