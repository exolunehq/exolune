# Search: tell the distance by the atmosphere

Status: research, the 2026-10-24. No code changed, engine not started: everything comes from reading the code and sources, listed at the end of the file. Steps 2 to 5 made the same day, visibility of 40 km (`journal-planete.md`, the fog of the boundary layer). The 2026-10-25, the layer follows the regional ground, read on the planet map (3.5; `journal-planete.md`, the planet map). The benchmark of the 1 stage remains to be done.

**In the game:** air passes through the composition of clouds (`spec-nuages.md`, `CloudAirPiece`), 12 not towards a surface, 24 towards the sky. The fog on the regional ground along the view there is made the 2026-10-30, to judge in flight (`tools/tests/2026-10-30-lumiere.txt`); until then, its air was that of a ground at sea level. The section 2 describes the state before this work.

## 1. Conclusion and order of work

**Our air is almost perfectly pure: this is the main cause of the lack of depth.**
- Our aerosols are those of the demo of Bruneton, taken as is by Hillaire and by Unreal: an optical thickness of 0,005.
- The average measured by satellite is 0,19 on land and 0,13 on oceans.
- The visibility on the ground is worth 217 km here. An ordinary day gives 20 to 60.
- At 10 km, a peak keeps 84 % of its contrast here, 38 % in ordinary clear weather. The second plan does not detach from the first.

**The “slight blur of distance” sought is this veil, not a blur.**
- Air removes the same contrast at all scales. It does not remove any detail.
- The eye first loses the fine details with little contrast: the sweetness of the distant comes alone.
- A true depth of field is false to our field of vision, and makes the landscape read like a model.

**The altitude effect comes from the same air, without altitude rule.**
- On the ground, the veil grows with the distance: clear foreground, successive shots increasingly pale and blue.
- Above the fog layer, it depends on the angle of view and not on the distance: everything is "far the same".
- It is enough that the air has the right amount and the right height, and that the calculation sees it at any altitude.

**Recommended order: correct the existing one first.** The steps 2 to 5 only affect the existing atmosphere, at zero cost.
1. **The benchmark of depth:** veil, color and contrast according to distance, on photos with known depth and on our renderings. Nothing can be done without him.
2. **Steps that show the average of the air:** orbit view, the calculation counts today 4,6 times too little fog. Invisible as long as it is weak; a realistic fog would mutate into a descent. That is the prerequisite.
3. **The visibility adjusted on the photos:** a single setting, the visibility in km, from which the density of aerosols is deduced. Departure towards 40 km. The biggest win.
4. **The color and phase of the aerosols:** a slightly more blue veil, exposing from Ångström to 1,3; an asymmetry of 0,8 brought back to 0,7.
5. **The boundary layer:** a soft peak mist towards 1,5 at 2 km, instead of a single exponential. It makes the fog strip viewed from an airplane.
6. **The shadows cast by the relief, then the sun rays:** the strongest clue remaining to separate the plans. A spec apart, at the real cost.

**Do not do:** depth of field on the landscape, blur filter according to distance, heat reflection.

**Later, with weather:** valley fogs, cloud shadows, exposure set on the illuminance, optical veil around the sun.

## 2. What we have

**Aerial perspective is calculated at each pixel, only once** (`AtmospherePass.hlsl`).
- A radius goes from the camera to the field, to the distance that the field writes in the alpha of the image HDR, floating 32 bits.
- 12 not regular for the ground, 32 for the sky. Each step takes the density of the air in its midst.
- Rayleigh and Mie's single scattering at every step, plus the multiple scattering of Hillaire's table.
- The sun is only hidden by the Earth: no shadows of the relief, neither in the air nor on the ground.

**The air, in `PlanetSettings.hlsli`, is that of the demo of Bruneton 2017:**

| Component | Sea level coefficient | Height of ladder | Phase |
|---|---|---|---|
| Rayleigh | 5,8, 13,6 and 33,1 × 10⁻³ km⁻¹ to 680, 550 and 440 nm | 8 km | Rayleigh |
| Mie | diffusion 4,0 × 10⁻³, extinction 4,4 × 10⁻³ km⁻¹, colourless | 1,2 km | Cornette-Shanks, g = 0,8 |
| Ozone | absorption only, in tent from 10 to 40 km | not applicable | not applicable |

- **Altitude is taken above sea level.** A ground at 4 km sees only 3,6 % of the sea level fog.
- **Optical thickness of aerosols:** 4,44 × 10⁻³ × 1,2 = 0,005. Rayleigh at 550 nm: 0,11.

**Visibility on the ground, by Koschmieder's law:** V = 3,912 / β, with β extinction at 550 nm.
- β = 13,6 × 10⁻³ + 4,4 × 10⁻³ = 18,0 × 10⁻³ km⁻¹, therefore **V = 217 km.**
- Rayleigh alone would give 289 km: our air is three-quarters molecular.
- The contrast is halved only in 38 km.

**No fog above, no fog layer on the ground.** The only fog is Mie's exponential. No clouds, no local fog, no illuminated volume.

**The lighting of the field** (`PixelShader.hlsl`):
- the sun filtered by the air above the point;
- the sky of a horizontal floor, weighted by the orientation of the normal and by the cavity of the textures;
- micro-shadows of cavity.
- **Missing:** the shadows carried by the relief and the sky hidden by the slopes of the valleys.

**The transition to the screen** (`ToneMap.hlsl`):
- temporal smoothing, 10 % of new image, exact reprojection;
- compression of Khronos PBR Neutral highlights: identity under 0,76, then faded to white, desaturation 0,15;
- sRGB output by hardware.
- **No exposure:** a radiance of 1 gives white. No auto exposure, no halo, no depth of field, no calibration.

**A sampling defect, invisible today:**
- Seen from orbit, the radius enters the air at 100 km; its 12 steps make 8,3 km.
- The last step reads the fog at 4,2 km altitude: 3 % of its density on the ground. The true mean on this step is 14 %.
- The fog is therefore counted 4,6 times too low; Rayleigh, 5 % too low.
- At 10 km altitude, the steps are 0,8 km and the error falls to 2 %.
- With a realistic fog, it would grow by a factor 4 as it descends: a mutation, contrary to principles.

**As shown in the images.** `images/actuel-cote.png` vs. target image `images/cible-cote.jpg`:
- at our place, the sky remains saturated blue to the horizon, and the sea dark blue to the line;
- on the target, the horizon whitens and the sea pales in the distance.
- The blurred edges of the target are a flip effect, not to be copied (3.13).

## 3. Indices, by impact and cost

| # | Index | Impact | Cost | At our house |
|---|---|---|---|---|
| 3.1 | Air veil: contrast and clarity depending on distance | very strong | zero, one adjustment | too low, V = 217 km |
| 3.2 | No integration just | prerequisite | zero | undercounted fog viewed from above |
| 3.3 | Color of the veil, desaturation | strong, comes with 3.1 | zero | Colourless aerosols |
| 3.4 | Fog clearer towards the sun | medium, strong backlight | zero | g = 0,8, a little strong |
| 3.5 | Boundary layer, fog height | strong at altitude, medium at ground | low | exponential only |
| 3.6 | Cast shadows, hidden sky of the valleys | very strong for plans | High | absent |
| 3.7 | Sunshine, air in the shade | average, depending on scene | 1 ms | experiment `rayons-soleil`, `recherche-rayons.md`  |
| 3.8 | Valley Fogs | strong but depending on the weather | Medium to high | absent |
| 3.9 | Shadows of the Clouds | strong | high, clouds are needed | absent |
| 3.10 | Exposition | low for depth | low | fixed |
| 3.11 | Optical sail near the sun | low | low | done, `recherche-halo.md`  |
| 3.12 | Atmospheric blur | negligible to our pixel | not applicable | Not to do |
| 3.13 | Depth of Field | counterproductive | not applicable | Not to do |
| 3.14 | Mirroring of heat | Negligible | not applicable | Not to do |
| 3.15 | Close-up: detail, micro-shadows | strong | Done | in place |

### 3.1 The veil of air

**Physics.**
- The light of the object goes out on the way: t(d) = exp(−β d) on a horizontal path.
- The air between the object and the eye returns the light from the sun and the sky to the eye: the light of the air. We see L₀ t + L_air (1 − t).
- A dark object lightens towards the color of the horizon. The contrasts all decrease by the same t factor.
- Koschmieder defines visibility as the distance at which a black object retains only 2% of contrast on the sky horizon. "= 3,912 / β".
- From one day to the next, it is the aerosols that change; Rayleigh varies little.

**Orders of magnitude.**
- Fog below 1 km, wet mist from 1 to 2 km, dry mist from 2 to 5 km.
- 23 km: the usual "clear" setting of the rural model of MODTRAN.
- U.S. National Parks: 53 to 145 km west, 23 to 39 km east.
- Very pure Arctic or mountain air: up to 240 km. Rayleigh limit: 296 km.
- Aerosol optical thickness at 550 nm, average MODIS: 0,19 on land, 0,13 to 0,14 on oceans.

**Contrast kept at the ground, on a horizontal path:**

| Visibility | Mie at ground level, km⁻¹ | Times today | Optical thickness, H = 1,2 km | 1 km | 5 km | 10 km | 30 km |
|---|---|---|---|---|---|---|---|
| 217 km, today | 0,004 | 1 | 0,005 | 98 % | 91 % | 84 % | 58 % |
| 60 km | 0,052 | 12 | 0,06 | 94 % | 72 % | 52 % | 14 % |
| 40 km | 0,084 | 19 | 0,10 | 91 % | 61 % | 38 % | 5 % |
| 23 km | 0,157 | 35 | 0,19 | 84 % | 43 % | 18 % | 1 % |

- **The foreground remains sharp:** at 40 km of visibility, an object at 300 m takes only 3 % of sail.
- **Planes separate:** from the crests at 2, 5, 10 and 20 km take 18, 39, 62 and 86 % of sail. Today: 3, 9, 17 and 30 %.
- **All the lighting follows:** direct sunlight a little weaker, clearer sky, shadows lighter and more blue, sunsets more orange. It is expected, and wanted.

**Who does it, and how.**
- **Unreal 5, Sky Atmosphere:** the Hillaire 2020 method. His doc specifies that the Mie is "in itself a fog in height". Its default values are ours; scenes add the Exponential Height Fog to have fog.
- **Frostbite 2016:** Same model. Mie's coefficient there "depends on the state of the atmosphere": purity, pollution, dust. A fog in height is added, colored by the table on the horizon.
- **Decima, for Death Stranding:** a fog in analytical height, at a single scale height, illuminated by the sun and the table sky. Two table games, clear weather and dense fog, mixed according to the weather.
- **Ghost of Tsushima:** Rayleigh and Mie tables, plus a fog volume of 128 × 64 × 64 cells, from 10 cm to 100 km.
- **Flight Simulator:** the fog follows the visibility of the bulletins METAR. In 2024, the broadcast is redone by throwing rays, fog, clouds and fog together.
- **Hoffman and Preetham 2002:** the origin in video game, extinction and light of air of constant density.

**Proposed parameters.**
- **One single setting, `VISIBILITY_KM`,** the visibility at sea level. Mie extinction is derived from this: 3,912 / V, less Rayleigh at 550 nm. The broadcast in guard 90 %, as today.
- **Starting: 40 km,** which is an optical thickness of 0,10. Plausible range: 23 to 60 km. The final value comes from the benchmark.
- **Startup tables take more steps:** a thin and dense layer requires it, and this cost is paid only once.

**Measure.**
- **The veil, by dark pixels:** in each distance band, the 2ᵉ percentile of luminance, compared to the sky horizon of the same image, is about 1 − t(d). This is the idea of the dark channel of He et al. We get β, so V.
- **Means by distance band,** as Kopf et al. 2008 on photos offset on a field model. Their curves deviate significantly from an exponential: we compare curves, not a single β.
- **Photos at known depth:** GeoPose3K, more 3 000 mountain photos, with position, field, orientation and depth map drawn from the ground. We keep the photos of good weather.
- **Our renderings:** it takes the distance of each pixel. The alpha of the HDR image already has it; a `MYPLANETENGINE_VIEW=distance` diagnostic view is enough.
- **The same shots as the picture:** camera at 2 m and 100 m, three sites, sun front and back.
- **Criterion:** our curves in the interquartile deviation of the good weather photos.
- **The quality benchmark to watch out for:** its octave ratios do not see a uniform veil, but the relative detail drops to 800 and 3 000 m. Compare it with and without fog.

### 3.2 Steps that show the average of the air

**The proposed rule:** an integration step shows the average of the air it passes through. This is the pixel rule of `principes.md`, applied to the radius.
- For an exponential density, the average over one step is exactly: H (e^(−h₁/H) − e^(−h₂/H)) / (h₂ − h₁), with h₁ and h₂ the altitudes of its ends.
- For a small difference in altitude, its series: no subtraction of almost equal terms.
- The light source remains in the middle of the step.

**Who does it.**
- **Hillaire 2020, reference code:** 4 to 14 not according to the length of the radius, distributed in square, tight near the camera.
- **Ghost of Tsushima:** Progressive slices of 1,2.
- **Red Dead Redemption 2:** a cell volume up to 160 m, then a ray throw beyond.
- These distributions serve a camera on the ground. Viewed from above, the fog is at the end of the radius: only the exact average is valid at any altitude.

**Parameters.** The 12 and 32 not current; maybe less once the exact average.

**Measure.**
- **A reference to 512 step** against the current calculation: camera at 2 m, 1 km, 10 km, 100 km and 1 000 km; to the nadir, at 45° and to the horizon.
- **Criterion:** less than 1/255 gap after compression.
- **The benchmark of descent:** the part of the sail at the nadir, without jumping 1 000 km to the ground.
- **The silhouettes on the sky:** the ground, in 12 not, and the sky behind it, in 32, connect without liseré.

### 3.3 The color of the veil, desaturation

**Physics.**
- The light from the air has the color of the sky near the horizon: blue by Rayleigh, whitened by aerosols.
- Dark objects bluish in the distance. Clear objects, snow and clouds, yellow a little: the air removes the blue.
- Saturation decreases as light from the air dominates.
- Fine aerosols spread blue more. Exponer of Ångström from 1,2 to 2,5 for pollution and fumes, from 0 to 1,6 for dust (Dubovik et al. 2002).

**At our house.** Everything is calculated by wavelength, except Mie, without color: zero exponent of Ångström, as in the demo of Bruneton.

**Here.** Bruneton expects the exponent of Ångström in its settings. Real-time engines leave the Mie gray and color the fogs they add.

**Parameters.**
- The Mie in three channels, proportional to (λ / 550 nm)^(−α), α to 1,3 at the start.
- The desert dust, α close to 0, will wait for air that varies according to the region, drawn from the existing climate.

**Measurement.** The hue and chroma CIELAB of dark and medium pixels, by distance band, on photos and renderings. The shade of the sky on the horizon.

### 3.4 The clearer fog towards the sun

**Physics.**
- Aerosols diffuse mainly forward. Backlit, the veil is clear and warm; back to the sun, darker and bluer.
- Around the sun, a white halo.
- Measurements AERONET: g asymmetry from 0,68 to 0,69 to 440 nm, from 0,58 to 0,66 to 670 nm, for pollution, fumes and dust; 0,75 on the ocean (Dubovik et al. 2002). Or 0,65 to 0,7 to 550 nm.

**At our house.** Cornette-Shanks with g = 0,8, the value of Bruneton, Hillaire and Unreal. A little too far forward: once the fog is thick, it will be too dark back to the sun.

**Here.**
- **Ghost of Tsushima:** Mie receives the shadow of the sun, Rayleigh the occultation of the sky, because Mie comes mainly from the sun.
- **Red Dead Redemption 2:** several Henyey-Greenstein phases, of decreasing asymmetry, to approach the multiple scattering.

**Parameters.** g to 0,7, set to benchmark.

**Measure.**
- The sky at 10° above the horizon, at 30°, 90° and 180° from the sun, relative to the zenith.
- References: clear sky types of the standard CIE sky, which the Python library `colour` calculates; photos.
- On the photos at known depth: the veil from the same distance, towards the sun and back to him.

### 3.5 The boundary layer, the height of the fog

**Physics.**
- Aerosols remain in the layer that the sun brews during the day: 1 to 2 km on land, capped by an inversion. At night and in winter, it falls to a few hundred meters.
- CALIOP: more than half of the optical thickness under 2 km, on the twelve regions studied.
- Air view: a white stripe below the horizon, at the sharp edge, and an equal veil when looking down.
- The peaks that come out of the layer cut clearly on the fog.

**At our house.** An exponential of 1,2 km above sea level: no layer top, therefore no net band seen from above.

**Here.**
- **Ghost of Tsushima:** an exponential density and a sigmoid density according to height, both exactly integrable.
- **Unreal:** two exponential layers, each with its density, decrease and shift.
- **Red Dead Redemption 2:** a global fog in height, plus a map of 8 × 8 km: starting height, decrease, density, depending on the weather and time.
- **Flight Simulator:** According to the players, the fog stops at 900 m above the ground, and forms a white spot seen from above. A ceiling too sharp or too low is seen.

**Proposed parameters.**
- **In `MediumAt`, the fog becomes a soft top layer plus a weak bottom.**
- **The layer:** constant density up to a summit towards 1,5 at 2 km, then a logistic descent on 0,3 at 0,5 km. Its integral is exact, so the step average of 3.2 is also exact.
- **The bottom:** an exponential of a few kilometers, 20 to 30 % of the optical thickness.
- **Height taken above the regional ground,** makes the 2026-10-25: the ground of the planet map, smoothed on 10 km of standard deviation, `HAZE_GROUND_SCALE_KM`. A plateau much wider than the layer is thick makes its own layer; a ridge or valley of several times this thickness, no: the top of the layer remains level above them (De Wekker and Kossmann 2015). The fog thins on the summits and fills the valleys.
- **The tables of the start** take the ground of the mist in third dimension: 25 slices of 0 to 6 km. The rest of the air keeps the altitude above the sea.

**Measure.**
- **The benchmark of descent:** the sail towards the nadir, at 60° and 80° of the nadir, from 1 000 km to 10 m. A jumpless curve, which stabilizes above the layer.
- **Plane and summit photos:** the angular thickness of the fog band under the horizon, the sharpness of its edge.
- **The CALIOP profiles,** as a priori, not as target.

### 3.6 The shadows cast by the relief, the hidden sky of the valleys

**Physics.**
- A slope in the shade receives only the sky. The veil in front of her remains the same: on a dark surface, it is seen much more. The blue mountains of the painters are mostly their faces in the shadow.
- Each ridge casts its shadow on the valley behind it: the planes are cut into light and dark bands.
- At the bottom of a valley, the slopes hide a part of the sky: the bottom darkens.

**At our house.** No cast shadow, no obstruction of the sky by the relief; only the micro-shadows of the textures.

**Here.**
- **Red Dead Redemption 2:** a shadow map of the field, by a ray throw on the map from the heights to the sun. 128 × 128 texels, softened according to the radius length. It serves on the ground and in the air.
- **Ghost of Tsushima:** the fog takes the average visibility of the sky as occultation.

**Parameters.** A spec apart, with the constraints of our principles:
- nothing jumps when the mesh is sharpened;
- the shadow of what the pixel does not see is a part, as for the limit rule.

**Measurement.** On mountain photos at sun height known: the share of shadow, and the luminance of the shadow faces according to the distance.

### 3.7 The sun's rays, the air in the shade

**Physics.** The air in the shadow of a mountain no longer reflects the sun: dark veil behind the ridges, rays towards a low sun.

**Here.**
- **Unreal:** a volumetric fog in cells of the screen, shaded.
- **Frostbite 2015:** volumetric shadow cards.
- **Red Dead Redemption 2:** a shadow volume near the camera, a ray throw in the distance, with the shadow of the field.
- **Star Citizen:** announcement of sun rays, no technical detail published.

**Cost.** High, and it must first 3.6.

**Make, in experiment:** the shadow height of the relief, read by the steps of the viewing radius, without waiting 3.6; the same field can give the shadow of the ground (`recherche-rayons.md`).

**Measurement.** Backlit, low sun: the luminance of the air in front of a ridge in the shade, against the sky above it.

### 3.8 Valley mists, the mist at the ground level

**Physics.** At night, cold air descends into the valleys and accumulates there under an inversion. Fog and fog remain there in the morning; on the water, the fog rises.

**Here.**
- **Red Dead Redemption 2:** its fog card makes morning mist on the water, which dissipates with the hour.
- **Unreal:** the second layer of fog. **Star Citizen:** a ground fog integrated into the atmosphere.

**At our house.** Nothing. It takes a density relative to the bottom of the valleys, so a map of the relief smoothed around the camera, and a weather.

**Cost.** Medium to high. Strong signature, but according to the time and the weather: with the weather.

**Measurement.** Inversions photos: height of the fog roof above the valley bottom.

### 3.9 The Shadows of Clouds

- **Physical:** shadow spots at all distances, which cut the landscape into planes. Painters use it.
- **Who:** Red Dead Redemption 2, a cloud shadow map of 768 × 768.
- **At home:** made with the clouds of the game, traced towards the sun at every pixel of surface (`spec-nuages.md`); not yet in the air.

### 3.10 The exhibition

- **Does the 2026-10-24,** set on the illuminance, with a tone curve at foot and shoulder: `recherche-tons-exposition.md`.
- **Not a distance indicator,** but it determines the reading of the veil.
- **A realistic fog clears the horizon and the sky.** Fixed exposure is sufficient during the day; not at bedtime, already noted (`log/spec-rendu.md`, step B).
- **Ghost of Tsushima sets the exposure on the illuminance,** not on the luminance: light floors do not darken the image.
- **Later.**

### 3.11 The optical veil near the sun

- **Physical:** Scatter in the eye or lens adds a halo around the sun and very clear sky, and lowers contrast near it (Spencer et al. 1995).
- **Who:** Unreal, a halo by convolution.
- **Low impact,** only towards the sun. After the rest.
- **Make the 2026-10-24:** a halo in 1/θ², that of a recent objective, before the tone curve (`recherche-halo.md`). Off by default; `MYPLANETENGINE_GLARE` enables it.

### 3.12 The atmospheric blur

- **Physics:** the diffusion to the front of aerosols blurs a little images on long trips. Its importance is debated (Kopeika et al.).
- **Our pixel covers 1,45 mrad,** 60° on 720 lines: this blur remains below, except thick fog.
- **The softness of the distant comes from the veil:** the eye sees hard the fine details little contrast (Campbell and Robson 1968).
- **No blur filter.** It would go against all the texture work, for an effect that already comes from 3.1.

### 3.13 The depth of field

- **Our field:** 60° in height, 92° in width, or a lens of 18 to 21 mm in full frame.
- **At f/8, the hyperfocal is from 1,4 to 1,8 m:** everything is clear from about 0,8 m to infinity.
- **The eye refocuses** where it looks.
- **A blur on the distant makes a model read:** this is the effect of tilt and offset, explained and measured by Held et al. 2010.
- **The blurred edges of `cible-cote.jpg`** are of this order: not to be copied.
- **It is part of the staging:** cinematics, photo mode. Not of a free camera over a landscape.

### 3.14 The reflection of heat

- **Physics:** Turbulence at the level of a warm ground makes the image shake over long distances.
- **Visible especially at telephoto:** its deviations remain well below our pixel. Mirages at the level of burning grounds are a case in point.
- **Not now.**

### 3.15 The foreground

- **It's not the air:** at 300 m, it veils only 3 %, even at 40 km of visibility.
- **This is the texture gradient, sharpness, saturation, small shadows.** Textures on all scales and micro-shades already give it.
- **Missing:** cast shadows (3.6); contact shadows, when there will be objects.

### Control by painting and photo

- **Leonardo da Vinci:** the distant mountains take the color of the air; further away, bluer and less defined.
- **The value shots:** landscape painters think in three or four shots, from the contrasting and warm foreground to the clear and cold distant.
- **Carlson and his theory of angles:** the sky is the clearest, then the flat ground, then the slopes, then the verticals. Our sky on the ground, weighted by orientation, already follows this rule.
- **Photographers:** the telephoto lens stacks the shots and shows the veil; the polarizer reduces it, because the light from the air is polarized (Schechner et al. 2003).
- **The agreement with physics:** veil, blurring, contrast decreasing, plans. Painters also soften the distant edges: this is what the eye perceives of a low-contrast detail, not a blur of the air.

## 4. Depending on altitude

**One rule only:** the air sails according to the amount of air on the route. The following speeds are derived from this, without altitude adjustment.

**At ground level, in the layer:**
- The journeys are horizontal: the veil grows with the distance.
- **Close-up, under 300 m:** clear, saturated, almost without veil. The detail and shadows carry it.
- **Second plan, from 1 to 10 km:** the ridges separate into increasingly pale and blue plans. This is the main gain.
- **Far away, beyond 30 km:** the relief blends into a white horizon.

**Climbing, in the layer, up to 1,5 to 2 km:**
- Downwards, the trails quickly come out of the fog: the ground below you regains contrast.
- Towards the horizon, the fog thickens in strips.

**Above the layer, from 2 to 15 km:**
- **The veil depends on the angle, more on the distance:** crossing the layer costs its thickness divided by the cosinus of the angle at the nadir.
- **Example at 10 km altitude, optical thickness of 0,10,** Rayleigh included: the ground retains 84 % of its contrast towards the nadir, 70 % at 60° and 36 % at 80° of the nadir.
- **Hence the "everything is far from the same":** two points seen from the same angle have the same veil, regardless of their distance.
- **On the horizon, a white band,** clear if the layer has a vertex (3.5). The peaks that overhang remain sharp.

**Toward orbit, beyond 100 km:**
- The lands take on a whitish veil, that of the optical thickness, which grows towards the limb.
- This is the "pink fog towards the horizon" of `spec-rendu-lointain.md`, experiment 3: to be reviewed with the realistic fog, against orbit photos.

**What this requires in the calculation:**
- **The layer is seen at any altitude:** the exact steps of 3.2. Otherwise the fog changes in descent.
- **The benchmark of descent checks it,** as for materials: a curve without jump.

**The leading clues that don't come from the air:**
- **Depth of Field:** no, at no altitude (3.13).
- **Contact shadows and occultation:** with cast shadows and objects.

## 5. Sources

**Engines and games**
- Hillaire 2020, *A Scalable and Production Ready Sky and Atmosphere Rendering Technique*, EGSR : [article](https://diglib.eg.org/handle/10.1111/cgf14050), [Reference code](https://github.com/sebh/UnrealEngineSkyAtmosphere).
- Hillaire 2016, *Physically Based Sky, Atmosphere and Cloud Rendering in Frostbite* : [Notes de cours](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/s2016_pbs_frostbite_sky_clouds.pdf).
- Hillaire 2015, *Physically Based and Unified Volumetric Rendering in Frostbite* : [presentation](https://www.ea.com/news/physically-based-unified-volumetric-rendering-in-frostbite), [course SIGGRAPH 2015](https://advances.realtimerendering.com/s2015/).
- Unreal Engine : [Sky Atmosphere](https://dev.epicgames.com/documentation/en-us/unreal-engine/sky-atmosphere-component-in-unreal-engine), [Exponential Height Fog](https://dev.epicgames.com/documentation/en-us/unreal-engine/exponential-height-fog-in-unreal-engine).
- Carpentier and Ishiyama 2017, *Decima Engine: Advances in Lighting and AA*, Death Stranding fog: [slides](https://advances.realtimerendering.com/s2017/DecimaSiggraph2017.pdf).
- Patry 2021, *Lighting, Atmosphere, and Tonemapping in Real-Time Samurai Cinema*, Ghost of Tsushima : [slides](https://www.advances.realtimerendering.com/s2021/jpatry_advances2021/index.html).
- Bauer 2019, *Creating the Atmospheric World of Red Dead Redemption 2*: [course SIGGRAPH 2019](https://advances.realtimerendering.com/s2019/index.htm), file `slides_public_release.pptx`.
- Bruneton 2017, *Precomputed Atmospheric Scattering*, new implementation: [code](https://github.com/ebruneton/precomputed_atmospheric_scattering), Mie values in `atmosphere/demo/demo.cc`.
- Hoffman and Preetham 2002, Rendering Outdoor Light Scattering in Real Time: [GDC 2002](https://renderwonk.com/publications/gdc-2002/).
- Flight Simulator 2024, report from a stream of the developers: [msfsaddons](https://msfsaddons.com/2024/09/25/msfs-team-answers-questions-about-msfs-2024-in-latest-developer-livestream); the fog and the METAR, according to the players: [forum](https://forums.flightsimulator.com/t/missing-haze-visibility-outside-metar-vicinity/550442).
- Star Citizen, demo from CitizenCon 2953, promotional source: [overclock3d](https://overclock3d.net/?p=265778).
- **No primary source found:** Outerra; a Guerrilla's presentation on the Horizon atmosphere, outside Decima 2017.

**Physics, measurements, data**
- Visibility, Koschmieder law, thresholds of fog and fogs, Rayleigh limit: [Wikipedia, Visibility](https://en.wikipedia.org/wiki/Visibility).
- MODTRAN, rural model at 23 km, example of use: [Sensors 2021, table 1](https://pmc.ncbi.nlm.nih.gov/articles/PMC8271715/table/sensors-21-04313-t001).
- Visibility in U.S. National Parks: [EPA](https://archive.epa.gov/ttn/naaqsimp/web/html/hazefs.html).
- Remer et al. 2008, aerosol climatology MODIS: [Summary](https://espo.nasa.gov/aaoe/node/14101).
- Vertical distribution of aerosols by CALIOP, ACP 2021: [article](https://acp.copernicus.org/articles/21/15309/2021/acp-21-15309-2021.html).
- De Wekker and Kossmann 2015, Convective Boundary Layer Heights Over Mountainous Terrain—A Review of Concepts*, Frontiers in Earth Science: [article](https://www.frontiersin.org/journals/earth-science/articles/10.3389/feart.2015.00077/full).
- Dubovik et al. 2002, optical properties of aerosols AERONET: [article](https://www.cfa.harvard.edu/hitran/HITRAN2012/Aerosols/papers/dubovik_et_al._(2002).pdf).
- Narasimhan and Nayar 2002, Vision and the Atmosphere: [article](https://www.cs.cmu.edu/~ILIM/publications/PDFs/NN-IJCV02.pdf).
- He, Sun and Tang, dark channel: [article PAMI](https://people.csail.mit.edu/kaiming/publications/pami10dehaze.pdf).
- Kopf et al. 2008, *Deep Photo*, fog curves according to depth: [article](https://johanneskopf.de/publications/deep_photo/deep_photo.pdf).
- Brejcha and Čadík 2017, GeoPose3K: [data set](https://cphoto.fit.vutbr.cz/geoPose3K/).
- Standard sky CIE: [CIE](https://cie.co.at/publications/spatial-distribution-daylight-cie-standard-general-sky-0), [implementation in `colour`](https://colour.readthedocs.io/en/latest/_modules/colour/phenomena/sky/cie2003.html).
- Schechner et al. 2003, the fog seen by polarization: [article](https://webee.technion.ac.il/~yoav/publications/haze_osa.pdf).
- Aerosol blur: [Kopeika et al., JOSA and 1995](https://www.doi.org/10.1364/JOSAA.12.000970), [*Aerosol MTF revisited*](https://cris.iucc.ac.il/en/publications/aerosol-mtf-revisited/).
- Spencer et al. 1995, *Physically-Based Glare Effects for Digital Images* : [article](https://en-cg-web.coecis.cornell.edu/pubs/1995/SSZG95.pdf).

**Perception, painting**
- Campbell and Robson 1968, contrast sensitivity according to fineness: [article](https://doi.org/10.1113/jphysiol.1968.sp008574).
- Held et al. 2010, *Using Blur to Affect Perceived Distance and Size* : [article](https://pmc.ncbi.nlm.nih.gov/articles/PMC3088122).
- Leonardo da Vinci, notebooks, aerial perspective: [Richter, § 295](https://www.fromoldbooks.org/Richter-NotebooksOfLeonardo/section-6/item-295.html).
- Carlson, angle theory: [Summary](https://theartistsroad.net/articles/thecarlsontheoryofangles).
