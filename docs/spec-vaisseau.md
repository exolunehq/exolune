# The player's ship

**Night instrument lighting, 2026-11-07:** screens, HUD, cockpit indicators and Navigator cabin fixtures automatically dim from the common incident meter; exterior navigation beacons keep their emission (`spec-ciel-celeste.md`).

**The player pilots a ship, seen from the cockpit or from behind.** The free camera remains available for the benchmarks and focus.

**J disembarks instantly onto dry terrain; J returns to the saved ship.** Walking controls and environmental audio are specified in [spec-marche-ambiances.md](spec-marche-ambiances.md).

**Try, in the game (`AGENTS.md`, `lancement.md`):** from the root of the worktree,
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Parcours tools\tests\2026-11-01-modeles-vaisseau.txt
```
after `tools\lance.ps1 -Build -NoLaunch` if the code has changed.

**Cabin finish and assembly · 2026-11-01**

- The geometry rule is in `principes.md`; implementation and rebuild commands are in [the asset README](../assets/vaisseau/chasseur/README.md).
- Continuous folded consoles meet the dashboard and receive instruments in real closed recesses.
- Seven panels follow their mounting contours and sit 1.5 mm below the fascia; three display rims project by 1 mm.
- Full-length console panels and tapered dashboard wings share one control and printing layout.
- Wing panels stop at the visible console boundary; cubic returns replace the overlapping diagonal ends.
- Four side service covers are also recessed; horizontal controls sit in the 18 cm shelf.
- The dashboard crown and alert strip form a shallow curve, keeping the centre height and lowering the shoulders by 35 mm along the panel plane.
- The nose shoulders roll down around the fixed glazing contour; an 18 mm forward rake clears the normal head travel.
- The pilot camera and glass/weather geometry remain unchanged.
- The canopy uses a flat 34 × 12 mm retainer and a separate 4 mm seal, following the glass tangent plane.
- The glass keeps its analytic shape with finer tessellation, 64 columns × 52 rows.
- Screen recesses have closed returns; structural housings have 1.5 mm bevels.
- Service covers, defogging vents, cable clips, seat anchors and restraint straps make the assembly explicit.
- Two 1024px micro-surface maps distinguish cabin paint, upholstery, webbing and machined metal.
- The 4096px label atlas carries graphite/petrol panels, coating grain, restrained wear and cyan sector markings.
- The package uses 12 images and 48 draw ranges; the engine retains its 12-image descriptor capacity.
- `controle_finitions.py` checks 504 mounting samples, 14 closed pockets, fascia protrusion, control clearance, 27 display sightlines, eye clearance and six animation pivots.
- `controle_visibilite.py` checks the forward cone and 1,180 wing-panel sightlines from five pilot-eye positions.
- Reimported GLB captures verify the final asset; the in-flight route covers daylight, low sun, cloud, sea, polar conditions, orbit and night.
- Earlier construction and counts: [ship history](log/spec-vaisseau-historique.md).

**Model selection**

| Model | Asset directory | Package | Pilot eye height | Main engines | Pivots | Water map |
|---|---|---|---|---|---|---|
| `chasseur` (default) | `assets/vaisseau/chasseur/` | VSX3 | 1.03 m | 4 | 6 | 1684 × 2450 |
| `classique` | `assets/vaisseau/` | VSX2 | 1.07 m | 3 | 2 | 1584 × 3660 |
| `navigateur` (cabin prototype) | `assets/vaisseau/navigateur/` | VSX3 | 0.70 m | 0 | 0 | disabled |

- The executable alone selects the approved fighter.
- `tools/lance.ps1 -ModeleVaisseau classique` selects the original triangular ship.
- Direct launches can use `MYPLANETENGINE_MODELE_VAISSEAU=classique`, `chasseur` or `navigateur`.
- The Navigator starts in its cabin, with eye offsets 0.65 m ahead and 0.70 m up. Tab cycles cockpit/chase/bare. Its panoramic field has no canopy weather simulation; see `spec-navigateur-cockpit-son.md` and `spec-reflets-vaisseau.md`.
- `MYPLANETENGINE_VAISSEAU` still selects the camera view, independently of the model.
- Each model retains its own source, Blender scene, GLB and cooked package.
- `ShipProfiles.h` selects the package, pilot eye, shadow centre, water-map dimensions, jets and pivots.
- `ShipClassique.hlsli` retains the original folded canopy and jet positions.
- `ShipChasseur.hlsli` describes the curved canopy and four nozzles from `chasseur/forme_chasseur.py`.
- The shader selector travels in `shipOptions.z`; geometry, water, frost and jets always use the same model.
- Only the selected package is loaded into GPU memory.

**Asset loading and animation**

- Each directory contains its own `vaisseau.glb`, `paquet_moteur.py` and `vaisseau.vsx`.
- The engine reads cooked vertices, draw ranges, PBR materials and PNGs; WIC decodes the images.
- VSX3 materials carry explicit animation roles in 96 bytes.
- VSX2 materials remain 92 bytes on disk; loading expands them and maps original screen indices 13–18 to roles 1–6.
- The original package and generator remain unchanged.
- `Ship::Load` validates the selected profile's pivot count.
- The package is found above the executable; an absent package leaves the free camera available.
- The ship frame uses metres: nose −Y, up +Z, pilot's left +X.
- The planet frame is left-handed; the ship-to-world transform reflects X and the glTF bitangent sign.
- Both models animate the stick and throttle through vertex `_POSE` weights and packet pivots.
- The fighter also animates four elevons, mixing pitch and roll up to 20°.
- The classic's unused pose matrices remain identity.
- `UpdateShipFrame` fills the matrices once; scene and shadow passes share them.

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
- **All views use a 5 cm near plane,** independent of ground clearance; reversed Z keeps distant depth precision. The previous altitude-dependent free-camera plane is [archived](log/spec-vaisseau-historique.md).

**Cliff approach, 2026-11-01:**
- `Draw` uses the same near plane for free, hidden-ship, cockpit and chase views; the far plane stays at 1e9 m.
- A cliff one metre from the eye must remain visible even when the ground below lies tens of metres away.
- Release x64 builds; numerical projection checks remain finite and monotone from ground to orbital distances.
- Paired native captures at `77.5 8.488890670 -103.555961023 0 -154.17278` show the near wall filling the former clipping hole.
- Projection and physical contact are separate; neither establishes that distant crest shimmer is fixed.

**Interactive terrain contact, 2026-11-01 (`D3DAppContact.cpp`, `FlightGround.hlsl`):**
- Sweep the proposed displacement before accepting it; the replaced nadir-only clamp is [archived](log/spec-vaisseau-historique.md).
- Free and chase cameras use a 0.25 m sphere; the hull uses a fixed sphere around `mShipPos`, radius `Ship::Radius + hypot(CentreY, CentreZ)`, about 8.851 m.
- The hull envelope contains every intermediate attitude; the cockpit eye remains attached inside it, including when translation stops.
- Chase mode tests the hull and external eye separately, then accepts their common first-contact fraction; it is a constrained rig, not an independently retracting boom.
- Sample shared `ReliefElevation` with exact lattice coordinates and the physical 2 m crease floor; contact uses the maximum of terrain, inland water stage and sea level.
- Sweep each sphere continuously against the sampled triangles, including faces, edges and vertices; keep a 2 mm separation and remove velocity into the contact normal.
- Retain the last tangent for sliding over at most 1 m, rechecking every proposed movement; moving away and tangency remain free.
- After placement or a view change, initialize a valid pose with conservative local vertical recovery; ordinary travel never uses this recovery to climb a wall.
- Queue probes in the existing command list and read them after the ordinary frame fence; no extra GPU wait or terrain-field readback.
- Reuse a validated stationary body's clearance; looking around only resamples an external eye if its position changes.
- Near terrain, translation is accepted one frame later; free-camera look remains immediate.
- An accepted stationary sphere requires no new probe; chase still checks its eye when it moves around a stationary hull.
- The cockpit's display and speed reference still use the delayed nadir height; collision does not use it.

**Coverage and cost:**
- Test the complete chord and its body radius against `PLANET_RADIUS + MAX_TERRAIN_HEIGHT`; clear endpoints alone do not prove the path clear.
- Probe from the outer-envelope entry to its exit, or to the first analytic sea-sphere contact if earlier; convert local contacts back to the original movement fraction.
- From a valid flight pose, this interval stays in one tangent hemisphere; a planet-spanning chord stops on its near side without a clamped projection.
- An existing sea overlap permits outward or tangent movement; only inward travel is blocked, with placement recovery handled separately.
- Ordinary grid spacing is 0.5 m for the camera and about 0.59 m for the hull; projected sphere bounds include curvature at long range.
- Each body uses at most 33 columns and 8,192 cell rows; exceptionally long corridors increase the longitudinal spacing instead of skipping the remaining path or adding a budget wall.
- The bound is 270,369 distinct vertices, or 278,785 height evaluations including shared group edges and the endpoint; a zero-length hull placement probe uses about 1,090 evaluations.
- At most two bodies return 8,224 bytes in total: group contact fractions, normals and support metadata.
- Sweeps are exact against this triangulated contact field, not a proof of the continuous terrain between samples; very long chords can miss features below their larger sample spacing.
- The hull sphere is conservative, not mesh collision; trees, individual rocks and FFT wave displacement are outside this contact field.
- Walking retains its own controller; automated captures and cinematic routes retain their existing positioning path and do not validate this interactive solver.
- A spherical free-camera contact never restores an older look direction, including during placement recovery or invalid-query rollback.
- Airless contact applies the same outward/slide policy through its shared physical field; its bounded support and checks are in `spec-lune-terrain.md`.

**Review:**
- `powershell -NoProfile -ExecutionPolicy Bypass -File tools/tests/check_flight_contact.ps1` checks the production sweep algebra, overlap retreat, sea tangency, planet-spanning chords and projected bounds on 52 shell cases.
- `tools/tests/2026-11-01-contacts-vol.txt` covers several coasts, steep slopes, snow, plain, sea and orbit; try approach, retreat, lateral sliding and turning in free, cockpit and chase views.
- F1 retains `96.7 -46.990030 -32.992581 12.92 70.17`; placement recovery may raise a ship whose hull initially intersects the terrain.
- CPU checks, Release x64 and interactive startup pass. The near-wall hull placement exercised recovery; free-camera mode and the orbital view work. Continuous wall approach, retreat and sliding remain for flight review.
- Crest shimmer is not isolated or claimed fixed by this contact work.

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
- **On the classic model, the edge of the two front windows is not seen:** at 35 cm from it, the normal glass turns to that of the edge, as on a single folded sheet. Otherwise their reflections cut off sharply on a straight line.
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
- **Flight keeps its own attitude:** translation and body-frame changes do not rotate the ship or curve its velocity around a planet.
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
- **Backspace** detaches the camera or returns to the cockpit. The ship takes the camera's attitude before applying its cockpit head offset.
- **Home** cycles the detached camera through Free, Horizon and Fixed altitude. The upper-left hint shows the active mode.
- **Free flight** uses the camera's own axes for right-drag look and translation. Shift + Left/Right rolls through a full turn.
- **Horizon** restores the original exploration controls. Forward and reverse follow the sightline, so holding forward while looking down descends towards the surface.
- **Fixed altitude** moves forward and sideways along the surface at constant radius, even while looking straight down.
- **Both level modes** follow the planet or moon selected on entry. Right drag yaws around its vertical and pitches from nadir to zenith. Switching between them keeps the same position and aim.
- **Altitude** uses E/Q (E/A on AZERTY) or Page Up/Down. Lift follows the local vertical in the two level modes and the screen's up axis in free flight.
- **The wheel** scales movement speed with clearance in all three modes.
- **Terrain contact** applies to Exolune and all three moons. The three outer planets support orbit around their visible spheres.
- **Walking** uses the local gravity vertical.
- **Launch** with `-Camera libre`, `-Camera orbite` (Horizon) or `-Camera altitude-fixe`. The game starts in the cockpit by default.
- **Review** the coastal approach at F1 and the downward lunar view at F5 in `tools/tests/2026-11-10.txt`. The same forward input distinguishes Horizon from Fixed altitude.
- **Checks** in `tools/tests/check_flight_frame.ps1` cover the mode cycle, climbs and dives, fixed-radius travel and free attitude. `tools/tests/check_celestial.ps1` checks target selection across the system.

## Jets and shadows

- **The plumes of the selected model’s nozzles** (`ShipPlume.hlsli`, `ShipPlumeVertex.hlsl`, `ShipPlumePixel.hlsl`):
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
  - each plume is marched through its box: 32 steps for main engines, 24 for attitude jets;
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
- **Images:** mips calculated on the CPU, average of sRGB codes, and without compression. Only the selected model’s images are uploaded; all 12 image slots are used by the fighter.
- **Screens:** live flight displays, without interaction. Switches remain static; the fighter’s nozzle cores and navigation lights animate by material role.
- **Time smoothing does not follow the handle:** it reprojects its pixels with the ship. The game cuts it off at startup; the T key restores it.
- **The reflection of the canopy glass** is that of an average sky and ground, without clouds or relief.
- **Jets:** no light from the plume on the ground or hull, no heat distortion.
- **Frost:** its temperature comes from the average climate, not from the weather of the day.
