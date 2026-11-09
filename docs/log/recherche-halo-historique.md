# Optical glare history

Archived on 2026-11-07: opt-in status, research alternatives and intermediate measurements. Current implementation: `../recherche-halo.md`.

# Research: the optical halo around the sun and snow

Status: research and first implementation, the 2026-10-24, experiment `piste/halo-optique`. Item 3.11 from `recherche-profondeur-atmospherique.md`. Sources at the end of the file.

**In-game, the Halo is off by default.** `MYPLANETENGINE_GLARE` activates it, at the direct launch of the exe: `tools/lance.ps1` deletes the variables (`lancement.md`). Since the 2026-10-30, it no longer depends on clouds.

## 1. Conclusion

**A single halo, linear, which conserves energy, on the image before the tone curve.**
- **The law:** far from a bright spot, the halo decreases as s E / θ². This is the distant halo of the eye, Stiles-Holladay law and dominant term of the equation CIE (Vos 2003). It is also the diffusion of polished optical surfaces.
- **One single setting:** the diffusion s = θ² L/E, in square degrees per steradian, `GLARE_STRAYLIGHT`.
- **A pyramid is enough:** half-images of the pixel on the screen, summed at equal weights, decrease exactly in 1/θ². Each octave of angle carries the same part of light, regardless of the resolution.
- **Light is moved, never added:** the image keeps 1 − W of its light, the pyramid distributes W. No threshold, no light created.

**The setting: a recent objective, s = 0,3.**
- **Measured:** 0,13 to 0,19 % of sail in ISO 18844 for current objectives (Koren 2018), or s ≈ 0,2 to 0,3.
- **Stronger elsewhere:** the devices measured by McCann and Rizzi, 1 to 8 %, give s ≈ 1,4 to 11; a young eye, s ≈ 10.
- **Not the eye:** the halo is linear. In front of the screen, the viewer's eye already adds its own to everything that the screen shows. Adding it to the image would count it twice.
- **Tested at s = 1,7,** a veil of 1 %: the high sun becomes an almost white ball of 4,3° in diameter, against 1,9° at s = 0,3. Just for an ordinary device, not discreet.

**Snow has no visible halo, and that's right.**
- A snow in the sun returns about 0,7 times the luminance of a perfect white.
- At s = 0,3, its veil on what surrounds it remains below a level of the output 8 bits: measured, compliant with the law.
- The halo of snow on the photos comes from overexposure, or from several percent sail lenses.

**Measured, section 5:**
- around the sun seen from space, the halo follows the law at 0,91 to 1,06 near, from 2° to 20°;
- sun high: +33 % of luminance to 2,4°, +9 % to 5°, +3 % to 10°;
- jitter unchanged; sun pumping from pixel to pixel, 0,4 %;
- cost, 0,17 ms in 1280 × 720 on RTX 4070 Ti.

## 2. What the sources say

### 2.1 The halo of the eye

**Spencer, Shirley, Zimmerman and Greenberg 1995.**
- The diffusion in the cornea, the lens and the retina spreads the light from a point: veil, lenticular halo, ciliary crown.
- Their spread function sums a Gaussian core and terms in 1/θ³ and 1/θ², weighted according to adaptation.
- **Their reason:** a screen can only produce the luminance that dazzles. We add to the image the halo that the eye would have had.
- The Cornell site was unreachable: their constants are not reproduced here.

**The equation CIE of disability glare (Your 2003, CIE 146:2002).**
- Ψ(θ) = L/E = 10/θ³ + (5/θ² + 0,1 p/θ)(1 + (A/62,5)⁴) + 0,0025 p, in sr⁻¹, θ in degrees, valid from 0,1° to 100°.
- A is age; p pigmentation, 0 for dark eyes, 0,5 brown, 1 blue or green.
- For an eye of 25 years: 27 % of scattered light beyond 0,1°, 8 % beyond 1°.
- Beyond 2°, the term in 1/θ² dominates: it is the Stiles-Holladay law, 10/θ².
- Van den Berg derives the diffusion parameter, s = θ² Ψ: log s ≈ 1 for a young eye.

### 2.2 The halo of objectives

- **ISO 9358:** the sail index is the light received at the center of a black spot, in a uniformly clear field.
- **McCann and Rizzi:** 1 to 8 % of maximum for the devices measured; in the worst case, the veil limits the image to about 25:1.
- **Koren 2018, ISO 18844:** 0,187 % for a Canon 90 mm on Sony A7R II to f/5,6; 0,130 % for a Canon zoom 75-300.
- **1984 classes for the 35 mm:** very good under 1,5 %, poor beyond 3 %.
- **The diffusion of polished surfaces** decreases in power of the angle, near 1/θ²: the same law as the eye.

**From index to s.** Under the s/θ² law, a θ1 radius spot in a θ2 radius field receives 2π (π/180)² s ln(θ2/θ1), or 0,0019 s ln(θ2/θ1).
- ISO 9358, spot of 1° in a field of 30°: 0,0065 s. A veil of 1 % gives s ≈ 1,5.
- ISO 18844 to 90 mm, cavity of 0,25° in a field of 7°: 0,0064 s. 0,19 % returns s ≈ 0,3.
- **This is an estimate:** these sources do not give the exact geometry of the mires.

### 2.3 Real time techniques

**Jimenez 2014, Call of Duty: Advanced Warfare.**
- A pyramid: descending by 13 samples, five boxes 2 × 2 that overlap; rising by a tent 3 × 3.
- No threshold: blur blends into the image for a small part, energy is conserved.
- A Karis average at the first level, against fireflies. **Dismissed here:** it would extinguish the sun.

**Bjørge 2015, the Kawase double filter.** The same pyramid, at 5 and 8 samples: cheaper, less round.

**Unreal, the halo by convolution.**
- A FFT of the image by a core image, which conserves energy.
- Reserved for kinematics and high-end machines, for its cost.
- Useful for a non-radial core: diffraction stars, lenticular halo. Not our need.

**Why the pyramid is enough.**
- A sum of double-width blurs with equal weights decreases exactly in 1/r² between the first and last level.
- The law is scaleless: the weight of a level does not depend on resolution or field of view.
- Simulated offline, it follows the law at 5 % near 4 to 128 pixels. Between axes and diagonals, the gap remains below 4 %, 11 % at worst.

### 2.4 Save energy, ahead of the curve

- **Halo is a spread:** the total light of the image does not change.
- **On the linear image, before the curve:** the sun, 45 750 times a white to the sun, keeps all its energy, which the curve would have crushed.
- **No threshold:** a threshold makes the halo appear in steps, and sparkle the surfaces that cross it.

## 3. How much halo, and how to measure it

**The orders of magnitude,** sun at 40° height, in fraction of a white to the sun:

| Angle to the sun | Recent objective, s = 0,3 | Ordinary device, s = 1,5 | Young eye, CIE | Our sky without halo |
|---|---|---|---|---|
| 1° | 0,71 | 3,5 | 36 | 0,30 |
| 2° | 0,18 | 0,88 | 6,0 | 0,30 |
| 5° | 0,028 | 0,14 | 0,70 | 0,28 |
| 10° | 0,007 | 0,035 | 0,16 | 0,25 |
| 20° | 0,002 | 0,009 | 0,04 | 0,20 |

**Measure against photos.**
- **Where to read:** the radial profile of luminance around the sun, in linear light, with fixed slope on a log-log scale.
- **A photo mixes two things:** the halo of air, diffusion forward of aerosols, and the halo of the lens. Separating them requires a photo RAW and the halo measured with solar photometer, like those of AERONET.
- **The proper measure:** the sun before the darkness of space. Without air, the image is the halo alone: this is the case of 1 of `tools/banc_halo.py`.
- **Around Snow:** the veil added next to the snow field, depending on the distance to its edge, compared to the convoluted law with the image without halo.

**Our halo is weaker than that of the photos.**
- The Cornette-Shanks phase at g = 0,7 does not have the narrow front peak of real aerosols.
- Our sky remains at 0,30 of 1° to 2° of the sun; a real sky is much clearer there.
- **It is not the halo to compensate for it:** it is the phase of aerosols, atmosphere side.

## 4. What is done

- **`GlareDown.hlsl`, `GlareUp.hlsl`:** the pyramid, 9 levels in 1280 × 720, from half screen to 2 × 1 pixels. Descent by the 13 samples of Jimenez, climb by the tent 3 × 3, at equal weights.
- **`PlanetSettings.hlsli`:** `GLARE_STRAYLIGHT` = 0,3, the only adjustment. The weight of each level is derived from this, 2π ln 2 (π/180)² s.
- **`Glare.cpp`:** `Glare::Initialize` and `Glare::Draw`, between atmosphere and time smoothing, with their own descriptor stacks. `MYPLANETENGINE_GLARE` activates it; without it, neither its images nor its pass.
- **`ToneMap.hlsl` unchanged:** halo is blended into composite image, alpha kept. Temporal smoothing smooths it like the rest.
- **The sun disc shows the part of the pixel it covers** (`principes.md`): a line of the composition, today `CloudComposite` in `Clouds.hlsli`. At free-board, its energy varied from −10 to +5 % from one position to another: the halo would have pulsed.

## 5. Measures

**The profile around the sun, seen from 2 000 km,** `tools/banc_halo.py`, in fraction of a white to the sun:

| Ring | 2,4° | 3,5° | 4,9° | 6,9° | 9,8° | 13,9° | 19,6° | 27,7° |
|---|---|---|---|---|---|---|---|---|
| Measured | 0,144 | 0,078 | 0,036 | 0,019 | 0,0091 | 0,0052 | 0,0024 | 0,0015 |
| Law, s = 0,3 | 0,157 | 0,079 | 0,039 | 0,020 | 0,0098 | 0,0049 | 0,0025 | 0,0012 |
| Report | 0,92 | 1,00 | 0,91 | 0,99 | 0,93 | 1,06 | 0,99 | 1,24 |
| Young eye, CIE | 4,9 | 2,1 | 0,98 | 0,46 | 0,22 | 0,11 | 0,058 | 0,032 |

- **On the edge of the screen, +24 %:** the last levels keep on the screen the light that would go beyond.
- **Same as s = 1,7:** 0,92 to 1,04 from 2,4° to 20°. The pyramid follows the law regardless of its strength.

**Sun in the air,** gain of luminance on image without halo:
- **Sun at 36° on the mountains:** +33 % at 2,4°, +18 % at 3,5°, +9 % at 5°, +3 % at 10°, +1,7 % at 14°;
- **sun low, 5°:** halo weak, the air lets through only a small part; the halo of the air dominates.

**Snow, sun in the back:** the veil added next to the snow field is worth 0,0005 to 0,0007 of a white, from 2° to 28° of its edge; the law predicts 0,0005 to 0,0007. Net deviation to image without halo: below a level of output 8 bits.

**The jitter,** `tools/banc_tremblement.py`, with and without halo, smoothing with and without:
- mountains in the sun: 0,05 and 0,39, against 0,05 and 0,40;
- desert at low sun: 0,00 and 0,01, unchanged;
- snow: 0,08 and 0,45, against 0,08 and 0,46.

**Pumping:** the sun moved by pixel eighths, the halo from 3° to 10° varies from 0,4 % at most. At free edge, the disc would have varied from −10 to +5 %.

**Cost:** 0,17 ms in 1280 × 720 on RTX 4070 Ti, median of six measurements, orbit view.

## 6. Open items

- **Sun off screen does not give any halo.** The halo appears suddenly when his disc enters. Possible remedy: the halo of the sun calculated separately, by its direction.
- **The eye dazzle,** s ≈ 10, for the only light that the screen can not show: to be decided with the new exposure and the new curve.
- **The output 8 bits** are seen in the gradient of the halo on the black of space. A half-level dithering at the output, in `ToneMap.hlsl`, would erase them.
- **The cost:** floating 16 bit levels would divide the bandwidth by two. The sun, 45 750, is near their limit of 65 504: to avoid as long as no margin is safe.
- **The air halo** from 1° to 3° of the sun, weaker than on the photos: the phase of aerosols, atmosphere side.

## 7. Sources

**Eye**
- Spencer, Shirley, Zimmerman and Greenberg, 1995, Physically-Based Glare Effects for Digital Images, SIGGRAPH 95: [article](https://w1.graphics.cornell.edu/pubs/1995/SSZG95.pdf).
- Vos 2003, On the cause of disability glare and its dependence on glare angle, age and ocular pigmentation, Clinical and Experimental Optometry 86(6), 363-370 ; CIE 146:2002, *CIE equations for disability glare.
- The general equation, copied and discussed by Bará and Bao-Varela 2023, *Skyglow inside your eyes*: [article](https://arxiv.org/abs/2212.09103).
- Van den Berg, Franssen, Kruijt et Coppens 2013, *History of ocular straylight measurement: A review*, Z. - Honey. Phys. 23, 6-20 : [two](https://doi.org/10.1016/j.zemedi.2012.10.009).

**Objectives**
- ISO 9358:1994, sail index and spread function: [ISO](https://www.iso.org/standard/17042.html).
- McCann and Rizzi, veil of the devices and limits of the images HDR, ECVP 2006, JSID 2007 and 2009: [archives de Milan](https://air.unimi.it/handle/2434/192417).
- Koren 2018, measurements ISO 18844 and dynamics of devices, Electronic Imaging: [article](https://www.imatest.com/wp-content/uploads/2018/01/EI2018_Norman_Koren_final_paper.pdf).
- Lens veil classes 35 mm, SPIE 467, 1984: [Summary](https://proceedings.spiedigitallibrary.org/conference-proceedings-of-spie/467/0000/Simplified-Method-For-Measuring-And-Assessing-The-Veiling-Glare-Of/10.1117/12.941584.full).
- Talvala, Adams, Horowitz and Levoy 2007, *Veiling Glare in High Dynamic Range Imaging*: [project](https://graphics.stanford.edu/papers/glare_removal/).

**Real time**
- Jimenez 2014, *Next Generation Post Processing in Call of Duty: Advanced Warfare*, SIGGRAPH : [slides](https://www.iryoku.com/next-generation-post-processing-in-call-of-duty-advanced-warfare/).
- Bjørge 2015, *Bandwidth-Efficient Rendering*, course SIGGRAPH 2015 *Moving Mobile Graphics*.
- Unreal Engine, the standard halo and by convolution: [documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/bloom-in-unreal-engine).
