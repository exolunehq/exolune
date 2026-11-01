# The player's ship

**The player pilots a ship, seen from the cockpit or from behind.** The free camera remains available for the benchmarks and focus.

**Try, in the game (`AGENTS.md`, `lancement.md`):** from the root of the worktree,
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Parcours tools\tests\2026-10-29-vaisseau.txt
```
after `tools\lance.ps1 -Build -NoLaunch` if the code has changed.

## The model in the engine

- **The source is `assets/vaisseau/vaisseau.glb`** (`assets/vaisseau/README.md`).
- **The engine reads a cooked packet, `vaisseau.vsx`,** written by `assets/vaisseau/paquet_moteur.py`:
  - flattened knots and intertwined vertices;
  - drawing ranges, opaque first;
  - materials PBR;
  - images PNG decoded by WIC.
- **There is no JSON or glTF drive in the engine.** You have to rerun the script after each export of the GLB.
- **`Ship::Load` looks for the package** in the first folder above the executable. Without a package, the ship remains absent and the free camera alone remains.
- **reference frame of the ship, Blender's:** nose to −Y, top +Z, left of the pilot +X, in meters.
- **The planet's reference frame is left-handed** (is × north = down). `Cross(haut, avant)` is right there, as for the camera. The transition from one to the other is a symmetry: the X-axis of the vessel moves to its left, and the bitangent of glTF changes sign.
- **The handle and throttle remain mobile:**
  - each vertex of the packet bears its pose, the attribute `_POSE` of `assets/vaisseau/pieces_mobiles.py`;
  - the package also keeps their two pivots, point and axis;
  - `ShipPose` (`Ship.hlsli`) applies to their vertex a matrix of `Ship::Constants::pose`, in the stage pass as in the shadows;
  - `D3DApp::UpdateShipFrame` fills these matrices, in one place.

## The rendering (`Ship.h`, `Ship*.hlsl`)

- **Its own shadow cards, 2048², on a sphere of 6,7 m:**
  - one towards the sun, for shadows carried in the cockpit;
  - one from above, for the sky that the shell hides.
- **The opaque surfaces are drawn first in the stage pass:**
  - Lambert and GGX;
  - sun through the air and whole sky, as near objects;
  - the occlusion cooked on the second UV of the sheets.
- **The direct part of the sun goes into the second target:** clouds shade the ship as the ground.
- **The canopy glass is drawn in a separate layer, after the atmosphere.** The tone map applies it after the temporal smoothing: screen = smoothed × alpha + rgb.
  - What sticks to the glass moves with the ship, the world behind it doesn't.
  - Kept out of history, nothing drags.
  - Without ship, the layer is (0, 0, 0, 1): render identical to the bit.
- **Time smoothing reprojects the pixels of the ship with it.** In its sphere, a fixed point in its reference frame is carried from the current ship to the previous (`reprojectShip`, `shipSphere`).
- **The close-up moves to 5 cm** as soon as the ship is drawn. The reversed Z keeps the depth of the distant field.

## The canopy glass and the time

- **`ShipWeather.hlsl`, one wire per frame, keeps the glass state.** It reads the game clouds, the same at the same time, by `Clouds.hlsli` (`spec-nuages.md`). The temperature comes from the climate map (`Climate.hlsli`), at sea level minus 6,5 °C/km.
- **Weather is read at the ship's position,** in its own constant cloud game; moving the outside camera away does not change rain, temperature, or frost.
- **The state of the glass:**
  - **Wet:** in the rain, and in a cloud, the faster the ship passes through it quickly; out of the water, the air dries it, faster at high speed.
  - **Rain:** under a thick cumulus, the cumulus part of the weather and the optical depth above the ship.
  - **Freeze:** under 0 °C, on a wet glass; the temperature is that of the sea minus 6,5 °C/km.
- **`ShipGlass.hlsl` draws:**
  - Fresnel reflection, from the sky outside or from the cockpit inside, and the sunshine;
  - **water** (`docs/recherche-eau-verriere.md`): simulated drops (`ShipWater.hlsli`), 8 192 at most:
    - they are born from rain or water captured in clouds, grow larger, merge, and flow under gravity and air;
    - **their path:** straight, until a defect of the glass, a cell of 5 mm on twelve about, where they mark a time and leave with a heading until 45° of side, which returns on 5 cm; they lean a little towards a wet trace;
    - **their shape:** a never completely round edge, domed sides; flowing, flatter, not wider than their trail;
    - **their trail:** a film of their width, which the following take over; it dries in about five seconds, slower under the rain, by crumble;
    - **the air thrust increases from 0 to 100 km/h, then remains that of 100 km/h:** beyond, the water always flows to 30 to 50 cm/s;
  - **their rendering:** each drop is a wide angle lens. It has a dark edge and, out of the clouds, a point of sky;
  - frost in slings from the thresholds, on a wet glass only.
- **No fog:** a veil on all the glass blurred the view without showing anything of the time.
- **The canopy glass also serves as a focuser:**
  - horizon, pitch scale all 10° and speed vector marker, infinite, in a cone of 24° around the nose;
  - the small combiner is under the line of sight, with no space under the roof;
  - off on start, U turns it on or off.
- **The edge of the two front windows is not seen:** at 35 cm from it, the normal glass turns to that of the edge, as on a single folded sheet. Otherwise their reflections cut off sharply on a straight line.
- **Viewed from the outside, the canopy glass is a dark bronze mirror,** like the treated hunters' skylights:
  - it reflects 30 % about from the front, all to the racing impacts, and lets through 8 %;
  - the sky is reflected clearer towards the horizon, the ground below the horizon;
  - **viewed from inside, nothing changes:** a lightly smoky glass.
- **`MYPLANETENGINE_VERRIERE=pluie`, `nuage` or `givre` forces a state,** for captures.

## The dashboard screens

- **The three screens and three dials show the flight,** for the eye only: `ShipScreens.hlsli`, called by `ShipPixel.hlsl` for the pack materials 13 to 18.
- **Their images remain the background:** frames, titles and labels of `textures_cockpit.py`. What the flight changes is erased and then redesigned, in the same colors, in segmented numbers.
- **FLIGHT / ATTITUDE :**
  - artificial horizon in roll and pitch, scale all 5°, digitized all 10°;
  - rose of the caps that turns under a fixed index, north in amber;
  - speed in km/h, altitude above sea level in km, heading, minutes and seconds of the clock.
- **NAV / TERRAIN:** a map in level lines, heading up, 40 m by texel, which scrolls with the ship; actual latitude and longitude. The relief of the map is invented.
- **SHIP / SYSTEMS:** bars follow throttle, speed and clock; hull temperature is that of standard air, heated by speed.
- **The dials:** THRUST tracks the throttle, ATT the pitch (4 flat, ±90° at the stops), ALT the height above the ground in km.
- **The data, at the end of `Ship::Constants`:** `course` (head, latitude, longitude, ground height) and `gauges` (gas), filled with `ship.air` in `D3DApp::UpdateShipFrame`.

## The piloting

- **The standard for keyboard and mouse space games,** Star Citizen and Everspace:
  - **Mouse:** pitch and lacing, by a virtual handle that refocuses at rest.
  - **Rolls:** Q and E, or A and E in AZERTY.
  - **Throttle:** the throttle wheel. Upwards, the ship goes faster, and the speed holds without touching anything; downwards, it slows down until it stops. Thirty marks, of 35 % each.
  - **Sliding:** A and D (Q and D) on the side; W and S (Z and S), or Space and Ctrl, up and down, in the ship's axis.
  - **Accelerate, brake:** Maj accelerates five times, X brakes.
  - **Free head:** Right click held; on releasing, the view stays where it is and the mouse pilots again.
  - **Swing head:** H gives the mouse to the head; H returns it to the ship again, and the head stays where it is.
  - **R brings the head back to rest,** a little below the horizon, of 4,5°. In free camera, R keeps the shading faceted.
- **A flight assistance keeps the speed of the throttle.** As for the free camera, it is proportional to the height above the ground, at least 60 m. The middle step is worth the default speed of the free camera. The slips go at least at this speed, even gas cut off.
- **The handle follows the commands:**
  - it retracts by 12° when the nose rises, leans by 12° on the side of the roll, and turns by 15° with the lacing, like a twist handle;
  - the pitch and the lacing come from the virtual mouse handle, the rolling of the keys, softened in a tenth of a second;
  - **the throttle handle** swings 40° on its thirty steps, forward with the throttle.
- **The ship is carried along the sphere:** flying around the planet keeps the plate.
- **The head follows the acceleration,** as in flight simulators: a dampened spring, according to [MSFS Physics Camera](https://flightsim.to/addon/114953/msfs-physics-camera).
  - **The sense:** the eye retreats when accelerating, moves forward when braking, leans at the opposite corners. The parallax with the cockpit gives the depth.
  - **The measure:** the acceleration is compressed by its logarithm, because the ship is going at the speed of light. About 1,5 cm to 0,2 g, 4 cm to 2 g, at most 6 cm forward and 3 cm side.
  - **The spring:** 1,4 Hz, dampened to 0,6. The head drags a little, then comes back with a slight bounce.
  - **Acceleration is that of the eye,** at 1 m above the rolling axis: a rolling throws it to the side.
  - **When rolling, the head also drags in rotation,** of 3° at most, around the axis of the gaze: the direction of the gaze does not change. It does not turn either in tangle or lace.
- **The mouse is read raw,** hidden and kept in the window. Alt held releases, to reach the test palette. M leaves it to Windows, the window in front, for a screenshot, then takes it back. It is also released when the window loses focus.
- **Space rises in the ship views:** the weather pause only responds to it in free camera.
- **Tab:** cockpit, chase, hidden ship.
  - **Then,** the right click rotates the camera all around the ship, from below to above, and all the way up to the front of it.
  - **The hidden ship** keeps the pilot's eye and the same controls, without hull or canopy glass: the widest view.
- **Backward:** the camera free, with its own controls, then back to the cockpit. Switching from free camera to ship brings the ship to the camera.
- **`MYPLANETENGINE_VAISSEAU=cockpit`, `poursuite`, `sans` or `libre` selects the first view.** The benchmarks are going free camera.

## Jets and shadows

- **The plume of the three nozzles** (`ShipPlume.hlsli`, `ShipPlumeVertex.hlsl`, `ShipPlumePixel.hlsl`):
  - a flame of light at the exit of each nozzle, of a blue-white heart to the purple, with weak shock diamonds;
  - **it ends in pointe:** it widens a little at the exit of the nozzle, then becomes thinner and extinguishes up to its tip;
  - **it follows the throttle, step by step,** from nothing throttle cut off until full at the thirtieth step, with the same response time as speed. Linked to speed, it was full from the first step in altitude, where speed follows height;
  - **its length:** from 1,7 m at the first intersection to 8 m.
- **Attitude jets:** ten small water vapor jets, at both ends of the stern and nose, up, down and side.
  - **Each pulls when its push serves the command:** the slip, or the torque of the roll, the pitch and the lacing around the center of the ship.
  - **Slides pull as long as the key is held;** rotations, at the beginning and end of the movement, on angular acceleration, like real attitude propellers.
  - **In gentle puffs,** two or three per second, each blast offset from the others.
  - **Only when the ship is not moving forward:** they turn off between 2 and 10 m/s forward; on the way, the nozzles and air direct the ship. Up, down or slide the guard.
  - **Never seen from the cockpit,** to keep the view clear.
  - **The water vapor is white and light,** lit by the sun and the sky.
- **The rendering of the jets is done in the layer of the canopy glass:**
  - each jet is run in its box, 24 not;
  - the walk stops at the distance of the stage, so that the hull and the floor hide what is behind them;
  - out of the temporal smoothing, nothing drags.
- **The shadow of the relief on the ship:**
  - walking to the sun from the ground (`Shadows.hlsli`), once per frame, from the origin of the ship, in the weather pass (`ShipWeather.hlsl`);
  - its share of sun multiplies the sun of the surfaces and the brightness of the canopy glass, with a delay image.
- **The shadow of the ship on the land and the sea** (`PixelShader.hlsl`, `ShipShadowOn`):
  - the map of the ship towards the sun, read beyond its sphere along the sun;
  - **the solar disc blurs it with distance,** on its penumbra of 0,0093 rad, in 16 readings;
  - after about a mile, the penumbra is as wide as the ship, and the shadow fades.

## Limits

- **Shadows:**
  - **the relief shades the ship by a block,** since its origin: a ridge does not cut the hull in two;
  - **the ship does not shade nearby objects,** stones and plants; only the ground and the sea.
- **Images:** mips calculated on the CPU, average of sRGB codes, and without compression. The ship maps take up about 120 MB of video memory.
- **Screens:** No interaction; outside the handle and controller, controls and lights remain static.
- **Time smoothing does not follow the handle:** it reprojects its pixels with the ship. The game cuts it off at startup; the T key restores it.
- **The reflection of the canopy glass** is that of an average sky and ground, without clouds or relief.
- **Jets:** no light from the plume on the ground or hull, no heat distortion.
- **Frost:** its temperature comes from the average climate, not from the weather of the day.
