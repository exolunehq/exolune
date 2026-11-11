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
- **Architecture and settlements:** follow the [generated city pipeline](docs/spec-ville-procedurale.md). Retain method and source hashes, validate support, access and LOD surfaces, then inspect the exact bank in Exolune. Plan density and protected nature corridors before placing structural variants. Compose shared garden habitats and sparse pedestrian connections; do not substitute a suburban frontage or vehicle-road grammar.
  - Take a building's form from a generated first draft; follow the [generated route](tools/city/README.md#generated-first-draft-building). The user validated this route on 2026-11-11. Make clean views and new variants in the user's ChatGPT, driven through Chrome; spend no Tripo credits on images. Use Blender to clean, scale, reduce and fit, never to author the form. Reduce the H3.1 draft locally to the asset's budget; no Tripo retopology (user decision, 2026-11-11). Hosted generation spends the user's credits: state the estimate first. Never display a generated atlas: read it as [material classes](docs/spec-ville-procedurale.md#generated-shell-surfaces) and review near, far and at dusk.
  - Follow the [architecture method decision](docs/recherche-generation-architecture.md) when selecting neural, parametric or hybrid generation. Review source junctions and openings before promoting a whole-building mesh. Use connected manufactured surfaces and shared PBR detail instead of disconnected primitive decoration.
  - Validate the master against the original design before production promotion through the shared cooker. Explicitly requested exploratory variants may precede artistic acceptance; keep that status open and review each exact source. `tools/city/finish_house_pair.py` retains a rejected technical control, not an accepted house recipe.
  - Follow the [neutral architecture series](tools/city/README.md#neutral-architecture-series) for the user-requested house and public-building variations. Preserve shared junctions, planar glazing, fitted access and bounded deformation. A topology pass is independent of art, LOD and native acceptance. Keep recipes and tools in Git; source GLBs, Blender files and CPU captures stay on E:.
  - Integrate reviewed neutral sources through the [series runtime bridge](tools/city/README.md#integrate-a-neutral-series-into-the-city). Preserve exact parent hashes and unchanged city sources; verify fitted access, structural reduction, five LODs and the exact native bank before a user test launch.
- **Vegetation assets:** follow the [vegetation production pipeline](docs/spec-pipeline-creation3d.md) for every master and variant. Retain the recipe and exact source hash, cook LODs and impostors through the common tools, and review in Exolune before promoting an asset. Keep weights, sources, cooked binaries and captures outside Git.
- **Generate every new and replacement plant model.** Use local neural generation, seeded procedural authoring, or a combination for trees, shrubs and ground flora. A downloaded mesh is a legacy review control. Keep it out of new source recipes and remove its active roles as reviewed generated replacements become available.
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
