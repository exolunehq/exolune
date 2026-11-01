# Search: night sky

**Status: a plan. The night sky is made on the branch `etoiles`, tag `piste/etoiles`, the 2026-10-25; it is not in `main` and remains to be integrated.**

**What is done, on the branch:**
- stars and planets in point images, the eye threshold, the Milky Way, atmospheric glow, night exposure and sticks;
- the code: `Stars.hlsl`, `StarsPixel.hlsl`, `Sky.hlsli`, `NightSky.hlsli`, `BrightStars.hlsli`, and brackets marked in `Atmosphere.hlsli`, `AtmospherePass.hlsl`, `AtmosphereSkyIrradiance.hlsl`, `ToneMap.hlsl`, `D3DApp.cpp`;
- measures: `tools/banc_etoiles.py`, views `tools/tests/2026-10-25-etoiles.txt`, entry of 2026-10-25 of `journal-planete.md`;
- three rules of `principes.md`, on the branch only: the sky is light, not a decor; night remains night; a table resolves the function it carries.

**To integrate it:**
- the branch starts from the `jalon/18-lumiere`: before the sea FFT, the planetary clouds, the detailed vegetation and the ship;
- in the game, the air is integrated by the composition of the clouds (`spec-nuages.md`, `Clouds.hlsli`): the atmospheric glow and the light of the stars on the ground are to be reported, to be checked at the integration;
- its rules go in `principes.md`, its settings in the table of `journal-planete.md`.

**What remains,** according to the branch journal:
- twilight from 0° to -6°, 1,7 to 4 times too clear, and zodiacal light, absent;
- catalogues, downloadable on request, section 7; no Moon;
- the night sky on the screen and the twilight, to judge in flight.

## Conclusion

- **A star is the image of a point.** Its light, a magnitude related to that of the Sun, goes to the pixels that cover its image, each its share: the rule of the solar disk. No geometry: 65 536 quads of a single drawing, calculated in the vertex shader.
- **The eye decides what we see.** The Schaefer threshold (1993) against the luminance of the sky behind the star: none during the day, brightest first at twilight, up to magnitude 6,6 to 7 at night, depending on the sky. No fading added: only the luminance of the sky counts.
- **Air acts by its transmittance,** that of the atmosphere table: extinction and redness near the horizon.
- **The Milky Way is the light of stars too faint to be points.** Its average comes from the counts of stars, its shape from the counts by galactic latitude; its clouds, from a noise, waiting for a map of the sky.
- **The night has its light.** The atmospheric glow, emitted in the walk of the sky, and the light of the stars. The ground receives it by the illuminance table from the sky: 6e-4 lux, against 1e-3 lux released with zodiacal light, absent.
- **Exposure follows the exposure meter, which reads at night.** The clarity that the eye gives to a scene decreases with light (Krawczyk 2005): -4,5 EV at night compared to day. The sticks see without color what is dark; the stars keep theirs.
- **The planets follow the ephemeris of JPL,** at the date given by the place of the Sun, in 2026.
- **No flicker:** at 60 frames per second, it reads as a default.
- **Catalogue:** 320 stars written here up to 3,5, then a procedural field faithful to the accounts. Files desired at the end of document.

## 1. How do others do

**Jensen et al. 2001, "A Physically-Based Night Sky Model" (SIGGRAPH), the most comprehensive reference.**
- The Yale Bright Star catalog, about 9 000 stars, position, magnitude and color.
- A separate image of stars, multiplied by an image of atmosphere transmittance, then added to the rendering.
- Photometry: E = 10^(0,4 (-m - 19)) W/m², or 2,5e-8 W/m² for m = 0.
- Color: temperature derived from B-V, then Planck spectrum.
- Star shape: a glare filter (Spencer 1995).
- Milky Way: a photographic mosaic of 14 400 × 7 200, bright stars removed.
- Diffuse lights: integrated constant star light, zodiacal light in table, atmospheric glow in active layer at 80 km.
- Rendering for the eye: Ward operator for scotopic vision, and a shift to blue.

**Stellarium (open source, `StelSkyDrawer`).**
- Each magnitude gives a radius and a luminance to the screen.
- Limit magnitude depends on field, eye adaptation and point source parameters; extinction and scintillation optional.

**Celestia.** Gaussian disks whose area grows with brightness, saturated in the center (developer forum).

**SpaceEngine.** A menu adjusts the exposure and limit magnitude (manual). No public details on the rendering.

**Microsoft Flight Simulator.** Real catalog and planets. User feedback criticizes too many stars and a Milky Way too bright. No primary source on the method.

**Elite Dangerous, Star Citizen.** Elite's background sky comes from its simulated galaxy (Stellar Forge); nothing published on its photometry. Star Citizen.

**Unreal, Sky atmosphere.** Nothing about the stars in what we could read: the use is a textured sky dome, without photometry (tutorials).

**What we keep.**
- Jensen's structure: a layer of stars apart, air transmittance, a catalog and photometry of magnitudes.
- From Stellarium: a limit magnitude that comes from the eye, not from a setting.
- Celestia and photos: an image that grows with the brightness. Without it, any star brighter than 6 gives the same white pixel.

## 2. Photometry

**Only one scale, that of the Sun.** A magnitude m illuminates from E = E☉ 10^(-0,4 (m - m☉)), m☉ = -26,74 in V, E☉ = π in the engine units. The Schaefer zero, a candlestick for magnitude -16,57, gives 1,26e5 lux to the Sun and 2,5e-6 lux to m = 0, as Jensen.

**The color.** B-V gives the temperature (Ballesteros 2012), then the ratio of Planck's laws of the star and the Sun to the three primary, of luminance 1. The Sun, B-V = 0,65, remains white; Betelgeuse is orange, Rigel bluish.

**The image of a point.**
- A point in a single pixel does not shake, but all visible stars saturate it: at twice the threshold of the eye, a star is already worth thirteen times the sky of its pixel.
- We take the image that an optics makes of it: the Moffat profile (1969), (1 + r²/a²)^-β, that of the images of stars, β = 3, wide of 2 pixels at half-height, the narrowest without folding.
- Each pixel takes the part of the image it covers, averaged by four points. The image extends as far as it passes a star at the threshold; its share beyond is returned to the rest.
- Bright stars appear larger, as in a photo or in the eye.

**Temporary smoothing.** It would spread the few pixels of a gliding star. The stars have their layer, added after him by the tone curve.

**The 8 bits of the screen.** The night sky is a slow and dark gradient: rounded at the level, it cuts into visible layers. A half level of noise, fixed on the screen, before rounding (noise gradient interlaced, Jimenez 2014) erases them.

## 3. Catalogues and catalogues

**The catalogues.**
- **Yale Bright Star, 5e edition (Hoffleit and Warren 1991):** 9 110 stars, complete to 6,5; J2000, V, B-V. The CDS broadcasts it (V/50); 574 KB compressed.
- **Hipparcos (ESA 1997):** 118 218 stars, complete to V = 7,3 to 9.
- **Tycho-2:** 2,5 millions of stars, up to 11,5.
- **Gaia:** more than a billion stars; only extracts are usable.
- Beyond the magnitude 8, no eye can see a single star: the BSC is enough for the points, and the Milky Way takes the rest.

**This is done without downloading.**
- **The bright stars, written here:** 320 stars, complete at 3,0 (169 against 171) and at 95 % at 3,5, plus the Pleiades, the Little Bear, the Key of Hercules, the Lyre and the Dolphin.
- **The procedural field, from 3,5 to 8:** the counts of the whole sky by magnitude (Sunspot 1997: 4 800 to 6, 9 100 to 6,5, 42 000 to 8). The k-th star takes the magnitude of its rank: the numbers are exact by construction.
- **His galactic latitude:** Allen's counts at 7, 0,407, 0,170 and 0,107 star per square degree at 0, 30 and 90°.
- **Its color:** the distribution of the B-V of the BSC, by deciles.
- **The Milky Way:** the light from stars fainter than 8, integrated on the counts up to 40, plus 30 % of light scattered by dust (Leinert 1998; Jensen 2001). Its average: 22,6 mag/arcsec²; 24,0 at the galactic poles, 21,4 in the plane, as measured.
- **Its shape:** a wide disk and a narrow band of 11°, according to Allen's counts of light from faint stars; lighter towards the galactic center; clouds and dark bands of a noise of log-normal gradient of mean 1.
- **Its limit:** it looks like a Milky Way, not ours. The NASA card replaces it.

## 4. The planets

**The choice: the real ones, at a date drawn from the Sun.**
- **Why:** the sky is that of the Earth, same constellations, on a planet of its radius and air. The real configurations are just by themselves: Venus never more than 47° from the Sun, Mercury close to it. They cost no data.
- **A fixed position** of an imaginary system would have been simpler, but nothing would have said where to place it.
- **The date:** the declination of the Sun, its subsolar latitude, gives its ecliptic longitude, then the date in 2026; we take the branch of the solstice of December to that of June.
- **The orbits:** the Kepler elements of JPL (Standish, table 1, 1800 to 2050), Kepler by Newton, in the vertex shader.
- **The magnitudes:** those of the Astronomical Almanac (Meeus, chapter 41), according to the distance and the angle of phase. Saturn's rings, by the slice in 2025 and 2026, do not count.
- **In June 2026,** Venus (-4,0), Jupiter and Mercury shine west after sunset; **in December,** Venus (-4,5) is the morning star, Jupiter and Mars are high at midnight.
- **No Moon:** the project does not have one.

## 5. Visibility

**Twilights (American Meteorological Society, glossary).**
- **Civil, up to -6°:** the horizontal illuminance changes from 410 to 585 lux at nightfall to 2 to 3,5 lux.
- **Nautical, up to -12°:** 0,008 lux at the end.
- **Astronomical, up to -18°:** 6e-4 lux, at night.

**The limit magnitude (Schaefer 1993, Vistas in Astronomy 36; his program, Sky & Telescope, may 1998).**
- Hecht's law: the fastest point seen against a sky of luminance B shines with I = c1 (1 + √(c2 B))², I in candlesticks, B in nanolamberts.
- **Sticks,** under 1 500 nL: c1 = 10^-9,8, c2 = 10^-1,9. **Cones,** above: c1 = 10^-8,35, c2 = 10^-5,9. We take the more sensitive of the two: the law remains continuous.
- **reference frames:** a black sky gives 7,9; a night sky of 21,9 mag/arcsec² (54 nL), 6,6; a day sky, -4, Venus at best.
- **His sky model** serves as a witness: twilight loses 0,4 magnitude per degree.

**What the engine does.**
- Each star compares its light, after the air, to the threshold given by the sky behind it, read in the composite image: diffusion, atmospheric glow, Milky Way, halo.
- **The eye sees only excess.** A star twice the threshold keeps half of its light; below the threshold, nothing. The transition is ongoing.
- **Physics decides:** no time-dependent fade. The threshold follows the luminance of the sky, the rest follows the transmittance.

**The scintillation.**
- It is real: about 25 % of eye-off at zenith, much closer to the horizon (Young 1967; Dravins et al. 1997), to 10 to 100 Hz.
- Not retained: on images of 2 to 4 pixels to 60 frames per second, it is read as a jitter, which the benchmark prohibits.
- Possible later, slow and reserved on the horizon.

## 6. The light of the night

**Its shares (Leinert et al. 1998; Jensen 2001).**
- **Atmospheric glow:** green line of oxygen at 557,7 nm (about 250 R), bands OH, sodium, continuum; a layer towards 85 at 100 km.
- **Zodiacal light:** the Sun diffused by interplanetary dust.
- **The integrated light of stars,** and that diffused by galactic dust.
- **The natural sky at zenith,** at solar minimum: V = 21,9 to 22,0 mag/arcsec², B = 22,7, R = 21,0 (Hänel et al. 2018; La Palma).
- **The ground without Moon:** about 1e-3 lux, 6e-4 at the end of the astronomical twilight. The full moon gives 0,05 to 0,3 lux.

**What the engine does.**
- **Atmospheric glow is an emission from the middle,** in the walk of `IntegrateScattering`: a layer in six² at 90 km, 7 km at mid-height. Each step takes the exact average, like the fog.
- **Sa luminance at zenith, out of the air:** 22,4 mag/arcsec², the natural sky less zodiacal light and that of the stars. Its color: B-V = 0,8, that of the sky measured.
- **It comes by itself:** the lightening towards the horizon (van Rhijn), the blushing near the horizon, the line of the limb seen from orbit, the light that falls on the ground by the table of illuminance.
- **The light of the stars on the ground:** the average of all, points and Milky Way, distributed over the sky, in the same table.
- **Missing zodiacal light:** about 20 to 30 % of night.

**The eye and the device at night.**
- **The adaptation (CIE 191:2010):** photopic vision above 5 cd/m², mesopic from 0,005 to 5, scotopic below.
- **Purkinje:** sensitivity changes from 555 nm to 507 nm.
- **Colours fade,** sharpness drops to a tenth below the stars. The “blue of the night” of films is a convention (Thompson et al. 2002); not accepted.
- **An incident exposure meter** reads 1e-3 lux under the stars, IL100 = -11: it would make night a day.
- **Astrophotographers expose about 5 EV below:** 20 s, f/2,8, ISO 3 200, or IL100 = -6,3.
- **The clarity that the eye gives to a scene:** the key of Krawczyk, Myszkowski and Seidel (2005), 1,03 - 2 / (2 + log10(L + 1)), L the luminance adaptation in cd/m². It is worth 0,69 under the Sun at noon, 0,12 at the end of civil twilight, 0,03 at night: -4,5 EV, like astrophotographers.
- **The choice:** the exposure meter reads twilight and night; the exposure follows it, multiplied by the key of the eye compared to that of noon. The day barely changes: -0,07 EV to 10° of height, -0,15 to 5°, -0,45 at sunset; then -1,3 EV to -4°, -2,5 to -6°, -4,5 from -12° (postmeter at noon: 1,13e5 lux).
- **The sticks:** what is dark, for an eye adapted to the dark, loses its color, its luminance kept. Their share goes from 0 to 5 cd/m² to 1 to 0,005 cd/m², depending on the clearer pixel and adaptation. The glow of a twilight therefore keeps its color, the night sky becomes gray; the stars keep theirs.

## 7. Downloadable, on request

- **The Yale Bright Star Catalogue, 5e revised edition, preliminary:** `https://cdsarc.cds.unistra.fr/ftp/V/50/catalog.gz`, 573 921 bytes, 9 110 stars. The CDS requests credit; no explicit license in the `ReadMe`. It would replace `BrightStars.hlsli` and the procedural field up to 6,5.
- **The Milky Way of the NASA, « Deep Star Maps 2020 »:** `https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/milkyway_2020_4k.exr`, 4 096 × 2 048, 34,7 MB, background without the bright stars of Hipparcos and Tycho, in equatorial coordinates. Credit: NASA/Goddard Space Flight Center Scientific Visualization Studio; Gaia DR2: ESA/Gaia/DPAC. No published calibration: we would put it on the average and the galactic profile from here.
- **Optionally, zodiacal light:** the table of Leinert et al. 1998, to CDS (J/A+AS/127/1), a few KB.

## Sources

- Jensen, Durand, Stark, Premože, Dorsey, Shirley, « A Physically-Based Night Sky Model », SIGGRAPH 2001.
- Schaefer, « Astronomy and the limits of vision », Vistas in Astronomy 36, 1993; « To the visual limits », Sky & Telescope, May 1998, programme taken by L. Bogan (bogan.ca/astro/optics/vislimit.html).
- Leinert et al., « The 1997 reference of diffuse night sky brightness », A&AS 127, 1998.
- Hänel et al. 2018, cited by « Natural Night Sky Brightness during Solar Minimum », arXiv:2105.01066.
- Allen, Astrophysical Quantities, counts of stars by galactic latitude (reprinted by the Isaac Newton Group, WEAVE).
- Counts of the whole sky: Sunspot Solar Observatory 1997, quoted by Wikipedia, "Apparent magnitude".
- Standish, "Keplerian Elements for Approximate Positions of the Major Planets", JPL; Meeus, Astronomical Algorithms, chapter 41.
- Ballesteros, « New insights into black bodies », EPL 97, 2012.
- Moffat, « A theoretical investigation of focal stellar images », A&A 3, 1969.
- Krawczyk, Myszkowski, Seidel, « Lightness perception in tone reproduction for high dynamic range images », Eurographics 2005.
- CIE 191:2010, mesopic photometry; Thompson, Shirley, Ferwerda, « A spatial post-processing algorithm for images of night scenes », 2002.
- American Meteorological Society, Glossary of Meteorology: civil, nautical, astronomical twilight.
- Young 1967, Astronomical Journal 72; Dravins, Lindegren, Mezey, Young, PASP 109, 1997: scintillation.
- NASA SVS 4851, Deep Star Maps 2020 ; CDS V/50, Bright Star Catalogue.
