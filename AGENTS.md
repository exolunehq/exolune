# Consignes pour les agents

## La documentation

- **`docs/` ne garde que ce qui est d'actualité.** Ce qui ne l'est plus passe dans `docs/log/` (`docs/log/README.md`) :
  - une spec close, remplacée ou désactivée, entière, par `git mv`, en mettant à jour ses renvois dans le code et les docs ;
  - les sections dépassées d'une spec vivante, essais, mesures intermédiaires, options écartées, dans `docs/log/<spec>-historique.md`.
- **`docs/README.md` est l'index :** à tenir à jour quand une spec naît ou passe au log.
- **`docs/principes.md` fait référence :** on corrige des règles, pas des cas. Une règle nouvelle y est écrite.
- **`docs/geometrie.md` :** la géométrie vient du relief d'Exolune ; toute modification de la géométrie y est classée.
- **`docs/journal-planete.md` :** chaque changement de réglage y a son entrée ; chaque étape ou piste a un tag git, `jalon/…` ou `piste/…`.
- **Le style :** en français, concis ; titres en gras, listes, une idée par phrase.

## Le travail

- **Une correction se juge en vol, par l'utilisateur, sur plusieurs lieux,** jamais sur la seule vue signalée : un fichier `tools/tests/<date>.txt`, un test par ligne, lancé depuis la racine du worktree par :
  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Parcours tools\tests\<date>.txt
  ```
  - **Après un changement de code,** d'abord `tools\lance.ps1 -Build -NoLaunch` : la solution en Release x64, dans `x64\Release`.
  - **L'exe seul est le jeu :** nuages, mer FFT, végétation détaillée, sans aucune variable. Le lanceur ajoute la palette, le soleil et le plein écran 1920x1080 (`docs/lancement.md`).
  - **La palette « Tests » :** un bouton par ligne, en fenêtre seulement (`-Resolution fenetre`, ou Alt+Entrée) ; F1 à F12 partout.
  - **Les photos de sol ne sont pas dans git :** sable et roche, Poly Haven CC0, dans `..\scans`. Si le titre dit « scans absents », ou si la roche tourne au damier, `tools\telecharger_scans.ps1` les retélécharge (28 Mo).
- **Les bancs de `tools/` ne tournent que sur demande de l'utilisateur.** Aucun banc de perf ni de qualité de sa propre initiative.
- **Quand un banc est demandé :**
  - il rend sans fenêtre et ne prend pas le focus ;
  - un seul moteur à la fois sur le GPU ;
  - le banc de qualité, `tools/banc_qualite.py`, se compare à `tools/banc_qualite_reference.json` par `--before` : aucun p95 ne se dégrade de plus de 10 % (`docs/spec-texturage-universel.md`).
- **Commits et push sur demande seulement.**
