# History of the volume vegetation prototype

**2026-10-26: volume filtering.** The present state is in `prototype-vegetation-volumique.md`.

**The rejected test:** add the leaf surfaces in each parent, then apply an isotropic Poisson law.
- The already hidden leaves contributed as if they were all visible.
- The cover grew with simplification.
- The CPU audit compares 60 orthographic projections of the same model.
- It integrates the expected coverage of the rays; it does not measure any GPU time.

**Average ratio of projected area, hierarchy from 128³:**

| Model | Level | Sum of surfaces | Transmission of children |
|---|---:|---:|---:|
| Sapin | 64³ | 1,10 | 1,04 |
| Sapin | 32³ | 1,22 | 1,06 |
| Sapin | 16³ | 1,36 | 1,08 |
| Sapin | 8³ | 1,50 | 1,10 |
| Jacaranda | 64³ | 1,05 | 1,02 |
| Jacaranda | 32³ | 1,12 | 1,04 |
| Jacaranda | 16³ | 1,24 | 1,06 |
| Jacaranda | 8³ | 1,43 | 1,09 |

**Choice:** filter the transmission of two children along the radius, then average the four columns and extinctions of the three axes.
- The base level remains unchanged.
- Average coverage improves, without a coefficient specific to a view.
- The worst area ratio, on all levels and angles, goes down from 2,77 to 1,61.
- The isotropic mean remains imperfect depending on the angle.
- At the level 32³, the jacaranda seen from above changes from 0,991 to 0,917.
- On the fir tree at 8³ level, the soft intersection/union goes from 0,477 to 0,453, despite a reduced absolute mean error from 0,0649 to 0,0576.

**The first functional captures:**
- All three modes and binary mask work.
- Pipeline statistics check the 2 518 432 triangles of 16 firs.
- These captures were made during the initial quality benchmark.
- Their GPU times are excluded from the final comparison.

**Interpolation of feet, replaced:**
- The first prototype interpolated the four vertices of a grid cell.
- The mesh draws two triangles; the surfaces do not coincide exactly.
- The audit on both locations finds less 0,008 pixel gap in cases of 16 trees.
- The error in meters increases with the size of the grid cell in the distance.
- The selected version meets directly the triangle following the line of the planetary anchor.
- A first fix found 0,097 mm in eight cases, but omitted the trees alone on a border of grid cell.
- The strict test of triangle coordinates then rejected some feet to a few millionths of the boundary.
- Campaigns `FoliageFinal64`, `FoliageFinal128` and `FoliageFinalStress64` are invalidated; tree masks alone were empty.
- The selected patch meets the two triangles and the neighboring grid cells, without moving the anchor.
- Regression captures cover two models, two locations, one tree or sixteen, in color and mask.
- The benchmark now refuses any empty reference, before its statistics and boards.
- The large projection deviations from the initial audit to 1 024 very close shafts include feet off screen and almost at camera plane; they do not measure a visible defect.

**Reproduction:** `tools/foliage/audit.py` and `tools/foliage/filtre_transmission.py`; intermediate files remain under `x64/FoliageAssetsAudit/`.

**2026-10-27: review before the final campaign.**
- The first volume step applied a full length to the last step, even if it was over the box.
- The last segment is limited to the length actually crossed before final measurements.
- The depth is accumulated in the middle of the segment, like the sampled material, instead of its beginning.
- The results of the first campaign remain exploratory; they do not replace the final measurements of the corrected code.
