# History of the sea

## First core replaced on the experiment FFT

## 8. Fact: the animated sea, experiment `piste/mer-animee` (2026-10-25)

**In short:** the wind, the reflection of the sun and sky, the whitecaps and the animated waves in the pixels, all in `Sea.hlsli`. The slope always has the Cox and Munk variance: shown by the waves or lost in the roughness of the reflection. The reflection and the whitecaps keep their average orbit at the water level.

**What is done:**
- **The wind, `SeaWind`:** the circulation by latitude of the section 2, the time of 3 000 to 300 km, 3 m/s by axis, the gusts and calm blankets of 100 to 5 km, a factor e^X of ±30 %. The swell, the layer 4, is not made; the sea is raised everywhere, without fetch.
- **Reflection, `ReflectOnWater`:** Cox-Munk anisotropic around the slope shown, Fresnel of water at the base of the facet (0,0204), Smith masking; sky walked from water by `IntegrateScattering`, 6 not, at Bruneton average Fresnel. One function for the sea and, when melted, wet sand.
- **Waves:** 168 waves, 14 octaves from 512 m to 6 cm, 12 directions each, one per sector. Pierson-Moskowitz: same slope per octave, peak at 0,83 U². Spread cos⁴ of half difference windward; deep water dispersion, including capillarity.
  - **Each wave shows its average on the pixel,** one cardinal sine per side, and fades from 8 to 2 pixels per wavelength. Its peaks, short, lose their phase in two wavelengths; the pixel also averages them along them.
  - **What they don't show enlarges the reflection:** = Cox-Munk variance lost minus variance shown, axis by axis.
  - **A sum of waves per pixel, not a FFT:** neither resource nor new pass, an exact filtering wave by wave, the wind of the pixel on each amplitude. Its limitations: a poorer pattern than a FFT close, and the cost.
- **Their plan:** tangent to the camera, carried without turning when it flies; its origin keeps the path traveled, in double precision. Phases are calculated on the CPU, `D3DApp::UpdateWaves`. A jump of the camera starts again from an origin drawn from the place.
- **Time:** the clock in flight, 1/60 s per frame in capture and to benchmarks; `MYPLANETENGINE_TIME="début [vitesse]"`.
- **The whitecaps:** Monahan's share, his average on the bursts that the pixel does not show.
  - **Close up,** where half-peak waves group: the square of their envelope beyond a threshold. The foam is born on the crest, follows it, then fades over a fifth of period, in lace.
  - **The threshold keeps the Monahan mean:** e^-u for the envelope of a Gaussian sum. Beyond 5,5 %, in storm, an old uniform foam does the rest.
  - **The fresh foam is worth 0,55, the old 0,1:** 0,22 on average, Koepke.
- **The color of water:** a type of water by latitude, greener in cold water and on the plateaus. The bottom is visible, Maritorena: wet sand, attenuation by channel. Its average is exact on pixel depths, normal law truncated at the coast. The gradient on 3 000 m is removed.
- **Time smoothing:** a pixel of sea that shows waves has no more waves; the distance passed to the atmosphere is negative. Each frame already shows the average pixel.

**Measurements,** RTX 4070 Ti shared, 1280 × 720:
- **Orbit reflection against Cox-Munk,** `tools/banc_mer.py reflet`, at 400 km, sun at 20° of zenith, pixel by pixel windward of pixel:

| Median wind | > 0,5 of the max. | 0,2 to 0,5 | 0,05 to 0,2 | 0,01 to 0,05 | Average variance |
|---|---|---|---|---|---|
| 2,6 m/s | 0,994 | 0,992 | 0,992 | 0,993 | 1,1 % |
| 6,6 m/s | 0,994 | 0,992 | 0,992 | 0,997 | 1,4 % |
| 13,0 m/s | 0,995 | 0,992 | 0,990 | 1,003 | 1,9 % |
| 14,6 m/s | 0,992 | 0,991 | 0,986 | 1,009 | 2,0 % |
| 20,2 m/s | 0,989 | 0,978 | 0,977 | 1,038 | 3,6 % |

  - Profiles in the sun plane: `images/mer-reflet-cox-munk.png`. The calm layers make the peaks, as in the images of the NASA.
- **The descent,** `tools/banc_mer.py descente`, from 1 500 km to 10 m, sun at 20° of zenith, three sites of 6,7, 10,5 and 26,6 m/s:
  - **average reflection** remains at 2 % of Cox-Munk from 1 500 km to 200 m. Lower, the view of 10 to 80 m covers only a part of a group of waves: on 16 instants, −8 to +11 %;
  - **the share of whitecaps** is that of Monahan at 1 % near orbit at 3 km. Close up: at ±8 % to 10,5 and 26,6 m/s; 20 % below to 6,7 m/s, where the threshold is high and the band has only a few waves. At 10 m, a view of 12 m rarely sees a whitecap.

| Height | Reflet / Cox-Munk, 10,5 m/s | whitecaps, vus / Monahan, 10,5 m/s | whitecaps, 26,6 m/s |
|---|---|---|---|
| 1 500 km | 0,994 | 4,12 / 4,10 % | 8,08 / 8,04 % |
| 100 km | 0,985 | 13,00 / 12,99 % | 21,75 / 21,73 % |
| 10 km | 0,992 | 1,18 / 1,18 % | 22,59 / 22,51 % |
| 1 km | 0,992 | 1,13 / 1,15 % | 27,69 / 27,66 % |
| 200 m | 0,995 | 1,10 / 1,15 % | 28,43 / 27,89 % |
| 30 m | 0,973 | 1,07 / 1,16 % | 29,53 / 27,69 % |

  The wind changes from one height to another because the view covers more or less gusts; the comparison is windward of each pixel.
- **The flicker,** `tools/banc_tremblement_mer.py`, mesh slide, fixed camera, average deviation from one frame to another on 255:

| View | Offshore floor, with / without smoothing | Frozen Sea | Animated sea, with / without smoothing | Contrast of detail, with / without smoothing |
|---|---|---|---|---|
| Coast, 120 m | 0,02 / 0,08, freeze as animated | 0,05 | 0,55 / 0,56 | 8,52 / 8,52 |
| 20 m, cool sea | no ground | 0,05 | 2,29 / 2,29 | 15,69 / 15,69 |
| 500 m, moderate sea | no ground | 0,02 | 0,38 / 0,38 | 9,59 / 9,59 |

  - **Out of the sea, nothing changes** when it moves. The usual benchmark of jitter, frozen sea, at the coast: 0,01 / 0,04 before, 0,02 / 0,03 after.
  - **The sea does not shake with the mesh,** 0,05: its waves are calculated on the planet, not on the peaks.
  - **His movement is no longer spread:** with time smoothing, he kept 70% of the contrast of his waves at 20 m, 10,48 against 14,70, and 68% of his movement. Without smoothing on the waves, both cases are equal.
- **Cost,** the fastest frame of each capture, four captures, against the base:

| View | Base | Animated sea |
|---|---|---|
| 20 m, cool sea | 1,20 ms | 3,22 ms |
| 500 m, moderate sea | 0,86 ms | 2,32 ms |
| Coast, 120 m | 2,12 ms | 3,95 ms |
| Orbite, 1 000 km | 0,59 ms | 1,00 ms |
| Mountain, 1,9 km, without sea | 5,22 ms | 5,58 ms, close to noise |

  - **Orbit, +0,4 ms:** the 1 single stage, wind, reflection and sky. **Near the water, +1,5 to 2 ms:** waves, full screen.
  - The GPU was used by seven other engines at the same time; the average of the images doubled these differences. The title bar now gives the fastest image.
- **The quality benchmark:** the earth is unchanged to the pixel close, two views compared; the rendering of the earth does not pass through the sea.

**Merge with `plages` (`c87dcd9`),** made on trial and compiled, tag `piste/essai-fusion-mer-plages`:
- **The sea share:** that of `plages`, `LandShare` and `ShoreSpread`; `SeaSurfaceAt` takes their spread, `ShoreSpread`, instead of `elevationSpread`, for the bottom seen.
- **`WaterSheen` disappears:** wet sand calls `ReflectOnWater`, Beckmann variance half the square of its roughness, `0,5 (0,04 + slopeSpread²)`.
- **The albedo of the sea on 3 000 m disappears:** `albedo = ground.albedo`, `wet = ground.wet`, and the radiance is shared with the sea by `sea` at the end.

**Rest:**
- **Waves in geometry near the camera:** vertical and horizontal displacement of waves of more than two grid cells, on the surface of the water alone, to be classified in `geometrie.md`.
- **The coastal surge:** waves dampened and refracted by depth, H > 0,78 d, edge foam in part of the pixel, with `plages`.
- **The cost of close, a FFT:** the sum of waves costs 1,5 to 2 ms in full screen near water. Three or four cascades FFT would replace it, variance accounting unchanged.
- **Swell, fetch, lakes**; color against Blue Marble; water type without the noise regional climate; the whitecaps near low wind, 20 % under Monahan.
