# Optimisation of vegetation: trials of the 2026-10-27

**Base:** `piste/vegetation-optimisation-base`; continued in `../optimisation-vegetation.md`.

**First candidate:**
- Second scan, reset and replay bounded by indirect commands with the length GPU.
- Atmospheric terms of impostors calculated at vertex instead of pixel.
- Fourteen BMP identical to reference, same accounts and no overrun.
- No gains demonstrated on the first series; placement times increase.
- A repeat of the reference also shows significant variations; the cause of each variation cannot be attributed to a single modification.
- Variant withdrawn from delivery; reports in `x64/VegetationPerf/mesure_candidat/` and `mesure_reference_b/`.

**Second candidate:**
- Direct dispatch; the groups of the second scan leave according to the number GPU of tiles retained.
- First scan unchanged; same atmospheric test.
- Fourteen identical BMP, same accounts and no overruns.
- A separate rendering application starts during the series; the last times increase sharply, with no instance of the benchmark left open.
- The GPU remains busy at about 95 % after the benchmark is finished; these times do not demonstrate code regression.
- The external program is retained; no application of other work is interrupted.
- Report: `x64/VegetationPerf/mesure_candidat2/`.

**experiments Uncommitted:**
- The reconstructed depth of the impostors is certainly not limited by the model's box alone.
- Weak alphas can pull depth to the camera; no conservative depth annotation is activated without evidence.
- A depth snapshot may reject pixels before visibility readings, but adds copy, transitions, and readings; it remains to be measured separately.

**Third candidate:**
- Four values per thread for scans and their additions; fewer groups and barriers, exclusive prefixes retained.
- The trigonometric functions of the four views of impostors are reused from the vertex; the atmospheric test is removed.
- Fourteen identical images, same accounts, no overruns.
- On free GPU, the drawing gains about 4 to 7 % in dense forests; the placement does not show a stable gain depending on location.
- New scans are therefore removed; only the reuse of views enters the next delivery.
- Reports: `x64/VegetationPerf/reference_libre/`, `candidat_libre/`; sources of this essay under `source_candidat3/`.

**HiZ: rejected variants:**
- A partition of impostors close as occlusors changes their drawing order and the winners at equal depths; it is removed.
- A new compaction and fourteen indirect dispatch adds queues and work; the selected version retains the queues and uses a mask of 128 KiB.
- A retreat at the first elevation disables the culling of distant trees seen from above; it is replaced by the bound of the actual view pair used.
- The simple physical box of the model does not limit the reconstructed depth; the selected version uses the HALF moments and filtering errors.

**HiZ: intermediate measures:**
- Several river and outer cloud renders restart during sequential series; these times are not used for final judgment.
- The `scout_*`, `libre_*` and `hardware_*` series, under `x64/VegetationHiZ/`, are used to check images, accounts, and resources.
- The series `matrix` compares the four states in each cycle of the same process; six views and 64 cycles per view, with no other MyPlanetEngine process observed during this series.
- The final general benchmark is compared to the current control, retaining the already accepted deviations from the canonical reference.

**The comparison flight, removed the 2026-10-30 with its launcher:**
- `tools/lance_vegetation_perf.ps1` opens the retained version; `-Reference` finds the shaders, without changing population.
- Both flights use the same executable and differ only in their shaders from impostors; the frozen measurement binary remains under `x64/VegetationPerf/`.
- Palette `tools/tests/2026-10-27-vegetation-performance.txt`: clearing and forests, six climate families, coast, sea and orbit.
- Only one flight at a time to compare performance.
- The time of the sea becomes animated again in flight.
- The launcher was `tools/lance_planet_foliage.ps1`, removed the same day with the foliage modes; both remain at the `jalon/25-vegetation-performance-main` tag.
