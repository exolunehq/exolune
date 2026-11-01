# Vegetation campaign, October 26 and 27, 2026

**Reading:** `docs/log/prototype-vegetation-volumique.md` gives the assessment and limitations.

**Final results:**
- `comparaison64.json` and `comparaison128.json`: six views, two models, three screen sizes.
- `stress64.json`: 64, 256 and 1,024 requested instances, two models, two representations.
- `manifeste-final.json`: cameras, anchor and lighting for the final comparison.
- `provenance64.json`, `provenance128.json` and `provenance-stress64.json`: hashes of the executable, shaders, data and benchmarks.
- `pieds.json`: twelve placement cases, at two locations and two distances, for 1, 16 and 1,024 requested instances.
- `qualite.json`: before/after check at the same 24 locations, with the prototype disabled.
- `contexte.json`: hardware and protocol.

**Exploration:**
- `comparaison-initiale64.json`: twenty distinct views and four movements, before the final fixes.
- `binaire-initial.json`: shader and executable hashes for this exploration.
- Earlier GPU series remain in `x64/FoliageComparaison64/rapport.json`; the exploratory export retains their statistics.
- Intermediate `FoliageFinal*` campaigns are invalidated and excluded.

**Local data:**
- `x64/FoliageValide64/` and `x64/FoliageValide128/` retain color captures, masks, raw measurements and contact sheets.
- `x64/FoliageValideStress64/` retains load tests.
- `x64/FoliageValidePieds/` retains placement GPU readbacks.
- `x64/QualiteAvant/` and `x64/QualiteValideApres/` retain the two complete quality benchmarks.
- These large outputs are ignored by git; scripts can regenerate them.

**Interpretation:**
- Series contain consecutive frames, not independent repetitions.
- Drawing time excludes placement, terrain and atmosphere.
- Small durations near zero reach GPU timestamp resolution.
- Requested count does not mean that many visible trees; bases may lie outside the terrain's coverage.
- `triangles_par_instance` is the source model's triangle count; each of the two proxies draws two support triangles per instance.
- Representation memory describes uncompressed formats, without extrapolating to optimized impostors.
- The historical quality benchmark baseline is unchanged; its preexisting deviations are distinguished from this prototype's changes.
