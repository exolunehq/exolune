# History of the coasts

**The outdated sections of `../recherche-cotes.md`.** The present state is there.

## 2026-10-24 · The plan of step 1, before doing it

Replaced the 2026-10-25 by the step made on the branch `plages`, tag `piste/plages`: the slope limit there is from 0,12 to 0,22, and all the bands follow the exposure of the coast.

**The 1 step, small and measurable:**
- **The change:** in `GroundMaterials`, `beachBase` goes from `SpreadStep(5, 25, elevation - 60 * local.y)` to about `SpreadStep(1.5, 3.5, elevation - 7 * local.y)`. The noise moves the limit of ±1 m instead of ±9 m; `beachSigma` follows, 1,04 instead of 76,7. A slope factor removes sand above 0,12 to 0,22, by the universal rule.
- **Measurement, before the engine:** the benchmark CPU of the section 6 gives the distribution of the widths.
- **The measurement, in the engine:** `banc_descente.py` with `BANC_MATERIAU=beach`, of 1 500 km to the ground; the quality benchmark, without p95 degraded.
- **What changes to the eye:** the lands of 3 to 25 m take the colors of the climate, grass or bare ground. Behind a real beach, it is the dune and its vegetation.

**The status at that time:** "no code changed"; the scripts of port CPU, `cp.py` and `t2.py` to `t7.py`, were in a volatile working folder. They have since been in `tools/cotes/`.
