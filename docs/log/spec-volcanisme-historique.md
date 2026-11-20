# Volcanism history

**Round flank cones, superseded on 2026-11-20**

- One proposal per 2.5 km cell had an isotropic radial density. Every retained cone used a radius of 0.25 to 0.75 km, a height of one quarter of its radius and a concentric bowl of fixed proportions.
- The upper two-fifths of the cone profile formed a plateau. The bowl took up that same area. Snow and the wide scoria disk outlined the repeated rims on the reported flank.
- The former distant mask reduced cover as each widened disc grew. This prevented the two-cell discs from appearing and disappearing from orbit. The current mask follows deposit thickness and keeps the same area reduction.

**Breach trial, 2026-11-20**

- A channel of fixed width gave several close vents a straight dark incision. The retained opening is angular and widens into the apron.

**Initial measurements, 2026-10-31**

- The with-and-without comparison disabled `VolcanoEdifices` on `bruit-propre`. The original relief was reviewed in `2026-10-31-volcanisme.txt` and the session's `volcanisme_planche.jpg`.
- The 200 volcanic map samples at 12 km cells had a CPU/GPU median difference of 0.4 cm and a maximum of 6 cm. The 33 near-ground samples had a 7.9 cm median and a 0.9 m maximum after double-precision cone placement.
- The catalogue contained 697 stratovolcanoes, 352 shields, 163 calderas, 26 atolls, 3 barrier reefs and 113 guyots at seed 0. External catalogue runs for seeds 1 and 2 gave 1,060 and 1,041 volcanoes and 10 hotspots each.

| Original measure | With volcanism | Without volcanism |
|---|---|---|
| Catalogue startup | 60–77 ms | — |
| Additional GPU catalogue storage | 0.18 MB | — |
| Moving terrain near volcanoes | 0.20–0.65 ms | 0.19–0.54 ms |
| Land share, seeds 0, 1 and 2 | 32.8%, 34.3%, 30.7% | 32.6%, 34.0%, 30.5% |
| Median land, seed 0 | 388 m | 380 m |
| Median ocean floor, seed 0 | −4,430 m | −4,450 m |
| Land and ocean modes | +375 m and −4,525 m | +375 m and −4,525 m |
| Area above 3 km, seed 0 | 2.03% | 1.99% |
| Area with an edifice above 10 m | 0.5–0.6% | — |

- The statistics used 400,000 terrain samples at 2 km cells. GPU timings came from a shared machine.
