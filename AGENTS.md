# Instructions for agents

## Documentation

- **`docs/` contains only current material.** Move outdated material to `docs/log/` (`docs/log/README.md`):
  - move an entire closed, superseded or disabled spec with `git mv`, and update its references in the code and documentation;
  - move outdated sections of a living spec, experiments, intermediate measurements and discarded options to `docs/log/<spec>-historique.md`.
- **`docs/README.md` is the index:** update it whenever a spec is created or archived.
- **`docs/principes.md` is authoritative:** fix rules, not individual cases. Record new rules there.
- **`docs/geometrie.md`:** geometry comes from Exolune's terrain; classify every geometry change there.
- **`docs/journal-planete.md`:** record every settings change; give each milestone or experiment a git tag, `jalon/…` or `piste/…`.
- **Style:** concise English; bold headings, lists, one idea per sentence.

## Work

- **Fix shared rules at planetary scale.** Reported coordinates are regression witnesses, never special-case conditions. Follow `docs/principes.md`.
- **The user reviews a fix in flight, at several locations,** never only in the reported view: create `tools/tests/<date>.txt`, one test per line, and launch it from the worktree root with:
  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Parcours tools\tests\<date>.txt
  ```
  - **After changing code,** first run `tools\lance.ps1 -Build -NoLaunch`: the Release x64 solution, in `x64\Release`.
  - **The executable alone runs the game:** clouds, FFT sea and detailed vegetation, without any environment variables. The launcher adds the palette, the sun and 1920x1080 full screen (`docs/lancement.md`).
  - **The “Tests” palette:** one button per line, in windowed mode only (`-Resolution fenetre`, or Alt+Enter); F1 to F12 work everywhere.
  - **Ground photos are not in git:** sand and rock, Poly Haven CC0, in `..\scans`. If the title says “scans absents”, or the rock becomes a checkerboard, `tools\telecharger_scans.ps1` downloads them again (28 MB).
- **Run the benchmarks in `tools/` only at the user's request.** Do not run performance or quality benchmarks on your own initiative.
- **When a benchmark is requested:**
  - it renders without a window and does not take focus;
  - only one engine runs on the GPU at a time;
  - compare the quality benchmark, `tools/banc_qualite.py`, with `tools/banc_qualite_reference.json` using `--before`: no p95 may worsen by more than 10% (`docs/spec-texturage-universel.md`).
- **Public remote:** the only remote is `origin`, `https://github.com/exolunehq/exolune.git`. Never publish commits from the old-license history, including through ancestry, branches or tags. Follow the [public Git history rule](docs/principes.md#public-git-history) before any requested push.
- **Commit and push only on request.**
