# Flight, canopy and suit

**Pilot experience**

- In space, steering brings the flight path back towards the nose. A reversal keeps momentum through the turn. The pilot can brake deliberately.
- In air, bank redirects the lift of the hull. The ship can glide at flying speed and sinks as it slows. The wheel gives an immediate response for approach and cruise. Full thrust is available at every altitude.
- Cut thrust above the ground and the ship settles. Sufficient forward speed, upward thrust or a deliberate powered hold can support it.
- A fast descent from space produces a short burst of hot gas and sound. Flying fast along a coastline or leaving the atmosphere keeps the ordinary engine and wind cues.
- Walking brings the listener inside a helmet. Nearby vegetation, footsteps, breathing and radio should be distinguishable with the master at its default gain.

**Design basis**

| Reference | Decision for Exolune |
| --- | --- |
| Frontier separates inertial flight, powered manoeuvring and engine boost. Cloud Imperium's flight design describes the different control needs of docking and travel. [Elite Dangerous manual](https://hosting.zaonce.net/elite/website/assets/ELITE-DANGEROUS-GAME-MANUAL.pdf) [Cloud Imperium design notes](https://robertsspaceindustries.com/en/comm-link/engineering/15031-Design-Notes-Flight-Model-Changes-In-Star-Citizen-Alpha-20) | Put precision at the bottom of a continuous power range. Give the pilot full forward thrust and boost anywhere, with explicit braking. |
| Pioneer describes a cruise controller which follows the ship's heading and allows temporary thruster overrides. [Pioneer flight controls](https://github.com/pioneerspacesim/pioneer/blob/master/Quickstart.txt) | Let a wheel change or a reversal produce a visible change in the flight path. Keep full power directly accessible. |
| Lift acts across the relative flow, drag along it. Their magnitude scales with dynamic pressure. [NASA Glenn](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/lift-to-drag-ratio/) | A few vector operations per integration step give speed-dependent lift, a banking response and drag. Use the ship's motion through the local air. |
| Banking tilts the lift vector and gives it a horizontal component which turns the aircraft. [NASA Glenn on banking turns](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/aircraft-motion-turns/) | Couple bank to the curvature of the actual path. Use wind-relative velocity for sideslip, so a crosswind still carries the craft over the ground. |
| Stagnation-point convective heating rises steeply with speed and depends on density and nose geometry. [Sutton and Graves, NASA TR R-376](https://ntrs.nasa.gov/citations/19720003329) | For a fixed effective nose, use a normalized heating cue with thermal inertia. A fast lunar pass gives no entry light or atmospheric roar. |
| The bow shock compresses the atmosphere ahead of an entering craft. Hot gas flows around the windward face and expands on the leeward side. [NASA Ames](https://www.nasa.gov/ames/entry-systems-and-technology-division/thermophysics-facilities-faq/) | Give the emitting layer thickness and a stand-off distance ahead of the hull. Sweep it downstream relative to the air. Check the changing silhouette from several angles. |
| Orion EFT-1 shows an amber patch beside a clear view of Earth. STS-42 shows a pale glow through a dark flight deck. Artemis I also shed fragments of heat-shield material. [Orion photograph](https://www.nasa.gov/image-article/orion-re-entry/) [STS-42 photograph](https://images-assets.nasa.gov/image/S42-45-033/S42-45-033~medium.jpg) [NASA OIG, figure 3](https://oig.nasa.gov/wp-content/uploads/2024/05/ig-24-011.pdf) | Let the exterior gas light nearby cockpit material. Use occasional bright grains with independent trajectories and leave the instruments readable. |
| Windshield rain needs a continuous mapping on each exposed pane, consistent scale and separate cabin occlusion. [Laminar Research](https://developer.x-plane.com/article/windshield-rain-effects/) | Keep water attached to the selected cockpit surface. The opaque canopy frame and dashboard hide the effects. |
| Fine scratches scatter light in relation to their tangents. Their apparent strength changes with the source, the observer and the pixel footprint. [Werner et al.](https://rgl.epfl.ch/publications/Werner2017Scratch) [Velinov et al.](https://light.informatik.uni-bonn.de/papers/VelinovEtAl-RTWaveOpticalScratches-EG2018.pdf) | Use groups of gently curved grooves anchored to the dry pane. Filter perpendicular to each groove and light its local three-dimensional tangent. |
| ElevenLabs supports loopable effects with specified durations. [Sound effects guide](https://elevenlabs.io/docs/overview/capabilities/sound-effects) | Generate isolated sounds, retain their recipes and load the cooked recordings locally. Mix layers continuously from the flight state and sampled habitat. |

**Shared inputs**

| Signal | Units and owner | Consumers |
| --- | --- | --- |
| Position, velocity and local vertical | World metres, m/s and unit vector, from flight and the celestial body | Motion, existing swept contact, pilot instruments |
| Velocity relative to the air | World m/s, from flight | Drag, lift, surface flow direction |
| Density and equivalent airspeed | Sea-level density ratio and m/s, from flight | Wind loading, wet glass, sound transport |
| Dynamic pressure | Pa, from flight | Aerodynamic response and checks |
| Engine effort | Unit interval, from delivered thrust | Propulsion sound and instruments |
| Entry heat | Unit interval, from the ship's inward passage, atmospheric load and time within the event | Exterior gas and sparks, reflected light, systems display and entry sound |
| Liquid precipitation, cloud water and frost | Existing weather and climate samples at the exposed surface | Water collection and drying |
| Habitat and listener | Existing world sound probe, walking state and camera mode | Trees, outside ambience, cockpit and suit mix |

**Flight model and tuning**

- `FlightDynamics.h` integrates a point mass in double precision. Each frame advances up to 0.1 s in steps of at most 1/60 s. The interactive hull sweep validates the resulting travel.
- Exolune uses inverse-square gravity from its existing gravitational parameter. Each moon contributes the surface gravity and radius in its manifest. The local lunar field dominates inside four lunar radii and blends back to the primary by eight radii.
- The molecular atmosphere shares its 8 km scale height and 100 km top with rendering. A smooth taper over the last scale height closes the flight medium. The existing climate wind supplies the air velocity.
- Dynamic pressure is `0.5 × 1.225 × densityRatio × relativeSpeed²` in Pa. Axial drag uses an effective ballistic coefficient of 2,400 kg/m². A broadside hull presents four times that drag area. At very high speed the fractional drag rate approaches 1.2 per second, preserving a controllable coast.
- In vacuum, steering rotates the velocity vector along an arc towards the new heading. Its length carries through a turn. A settled, unpowered ship can follow an orbit under gravity. Air density and dynamic pressure blend this assistance into atmospheric flight.
- Atmospheric trim builds between 22 and 80 m/s equivalent airspeed. Incidence changes the lift, bank turns the heading and reverse flow sheds lift. Acceleration from the wings is limited to 40 m/s². The fin reduces sideslip relative to the wind. A held translation command allows a deliberate slide.
- The first 24 wheel notches select cruise speeds. Notch 15 commands 100 m/s. The controller uses time constants of 0.35 s for acceleration and 0.65 s for deceleration. In air the control acts along the flight axis relative to the wind. Notches 25–30 command a continuous burn, with unrestricted speed.
- Holding Up commands full thrust at any lever setting. Shift engages the boosted drive. X brakes across all axes and supplies the thrust needed to hold position. The cockpit title reports the wheel setting and selected cruise speed or continuous burn.
- The drive reports total effort for the mix and axial output for the main nozzles. The pilot's seat responds to specific force, so free fall does not push the pilot back.
- An observed ship position at or above 100 km arms atmospheric entry. Crossing 92 km inwards qualifies the passage at an airspeed of at least 1,800 m/s and a radial descent of at least 100 m/s. The hot phase can start below 78 km when density and relative speed produce sufficient flux.
- During the event, brightness follows `sqrt(densityRatio) × (relativeSpeed / 2500 m/s)³`. The burst fades over its last three seconds and ends within twelve seconds, or earlier as the ship approaches 40 km. Levelling, ascent and sub-threshold airspeed extinguish it. Another visit above the atmospheric ceiling rearms the effect.
- Flight tuning belongs in [the integrator](../MyPlanetEngine/FlightDynamics.h). The three ships share the first handling profile. It represents assisted point-mass flight with a six-axis control interface. Rigid-body inertia tensors, measured airfoils, structural damage and predictive thermal protection are outside this first version.

**Controls and state changes**

- Releasing Up restores the wheel setting. Yaw and pitch engage the spaceflight assist. Hold X for powered braking and station keeping.
- The detached camera keeps its exploration controls. The pilot's attitude survives a change of terrain reference frame.
- Swept hull and chase-camera contact remains authoritative over the proposed displacement. Walking uses its own controller and the parked ship.
- A route pose can seed physical velocity along the nose. Re-selecting a pose resets the flight and thermal history. The entry review starts above the atmosphere and crosses it during playback. An authored `depuis-espace` pose explicitly replays a preceding steady descent through the same conditions.
- Cinematic poses retain their authored timing. Sensory state reads the motion on that path. The entry camera track sets `coast` so an unpowered pass has dark exhaust nozzles.

**Rendering and sound**

- Share the glass material and weather response across classic, fighter and Navigator cockpits. Each model supplies its optical surface. Preserve the Navigator's mirrored silhouette from outside.
- Render fine glass surface detail after temporal reconstruction. Occlude it against cockpit structure. Bare and detached cameras give a clean view of the world.
- Give the bow a detached luminous front and the flanks a cooler, thinning flow. Use the opaque scene depth to decide how much gas a viewer can see in front of the hull. A cold stationary cockpit tests the dry coating.
- Keep the walking visor subtle. Reflecting a bright light at the periphery should reveal it even on an airless body. Atmospheric contributions depend on the actual environment.
- Layer propulsion, cabin, hull airflow and entry resonance in flight. In the suit, mix breathing with exertion, protected radio and the existing habitat and contact sounds.
- Retain the Navigator's quiet propulsion identity. The calm cockpit and ordinary climb must sound different from entry.
- Read files during audio initialization. Bound playback voices, keep generated media local and apply the existing mix controls.

**Assets and ownership**

- [Ship profiles](../MyPlanetEngine/ShipProfiles.h) supply the water-map dimensions and physical scale. Classic and fighter retain their original glazing. The Navigator uses its 2560 × 1536 panoramic mapping at 1.8 mm per texel.
- [Surface optics](../MyPlanetEngine/OpticalSurface.hlsli) supplies pane wear and Fresnel response. Micro-abrasion is mapped in metres on the classic and fighter panes and on the angular Navigator field. The helmet retains its separate, finer wear treatment.
- A [48 × 48 cubemap on six faces](../MyPlanetEngine/ShipShockHull.cpp) records a convex envelope of the selected VSX model once at load. The windward gap and layer thickness are measured in metres. The [volume shader](../MyPlanetEngine/ShipEntryVolumePixel.hlsl) integrates emission and transmission along the view ray up to the first opaque surface. The metal and glass receive separate, local highlights.
- The narrow incandescent core gets finer integration than the surrounding air. The shader takes at most 64 steps per ray inside the projected volume. The two shoulders can stretch 1.30 m downstream while the wake behind the engines fades.
- The visor reads the walker's exertion and the atmosphere at the wearer's location. Condensation starts near the chin and recedes as effort falls. A narrow highlight follows the rolled seal at the lower corners.
- One GPU weather sample schedules the water passes. A dry, empty surface dispatches zero particle and atlas groups. Existing droplets keep their motion after rain stops. The film keeps drying to the 0.5 µm visibility threshold before a final clear.
- The [particle shader](../MyPlanetEngine/ShipEntryParticleVertex.hlsl) sheds small grains from exposed shoulders and from the compressed gas. The hull, cockpit posts and wings occlude them. The volume and particles skip their draw calls when cold.
- [The audio manifest](../assets/audio/immersion/bank.ini) identifies the seven production takes, source hashes, prompts, channel layouts and nominal gains. The [PCM receipt](../assets/audio/immersion/cooked.json) identifies the exact cooked sounds. The local bank totals 7,761,498 bytes.
- [The runtime mixer](../MyPlanetEngine/WorldAudio.cpp) maps flight and habitat signals onto the layers. The procedural Navigator resonance, ground material contacts and wildlife keep their own identities. [Audio design and verification](recherche-son.md)
- Enter or the radio button plays the French relay response over the cockpit or helmet receiver. The mix briefly ducks under the voice. Airflow, foliage and entry noise need their respective physical source. The sealed receiver and breathing work on the moons.

**Acceptance in the engine**

| Scenario | Observation |
| --- | --- |
| Turn through 90 degrees and reverse in space | The path follows the new heading promptly. The pilot carries speed through the turn and can choose when to brake. |
| Bank over the ocean, then repeat at low airspeed | Lift turns the flight path and weakens as the hull loses airspeed. |
| Stationary near the surface | Cut thrust to settle, hold X to arrest the descent, then release it to settle again. The ground supports the hull. |
| Cross into Exolune, cruise below the entry layer, then climb | The crossing lights the air ahead of the bow and along the flanks once. Gas, sparks and entry sound die away during flight. Fast level passes and departures stay clear. |
| Same cockpit at low speed, in rain and at night | Surface water follows the pane, markings stay subtle and instruments remain legible. Repeat on each model. |
| Airless moon, moving and on foot | Gravity and contact remain active. Entry glow, outdoor wind and habitat are silent or absent. Suit breathing and radio still work. |
| Forest floor, walking, sprinting and stopping | Breath follows exertion. Foliage follows local vegetation and wind. The radio can be triggered once per press. |
| Cockpit, chase, bare, detached camera, suit, then cockpit again | Each switch selects the correct optics and sound perspective. Old weather, heat and radio must respect their lifetime. |

**Implementation and review sequence**

1. Integrate the bounded flight step behind the existing control and contact paths. Exercise gravity, braking, coasting, heating and timestep variation.
2. Connect the optical surfaces and audio mixer to the same physical state. Exercise every cockpit and the walking view.
3. Build Release x64 and fly the [assisted flight route](../tools/tests/2026-11-20-vol-assiste.txt). Compare the marine pass and vacuum turn at the same indicated speed. The separate [immersion route](../tools/tests/2026-11-20-vol-immersion.txt) covers the suit, radio and cockpit weather.

**Functional evidence**

- The [production flight checks](../tools/tests/flight_dynamics_checks.cpp) exercise the three lunar gravities, an unpowered orbit, contact support, vertical thrust, powered braking, banked lift, heating and frame subdivision. At a 250 km circular orbit the radius drifts less than 2 m in two minutes.
- The [walking and audio checks](../tools/tests/check_walking.ps1) render 21 s through the game's mixer. The sequence covers entry, vacuum, walking through trees and a radio call at 15.5 s.
- In dense air a 45-degree bank at 100 m/s changes course by 28 degrees in five seconds. A 16 m/s crosswind carries the trimmed hull with the air. One second after a commanded reversal in space the velocity is within one degree of the nose.
- The [interactive cockpit check](../tools/tests/check_cockpit_wheel.py) sends wheel detents to the native window over the sea and in space. In space the first and third settings reached 4.8 and 14.9 m/s. On the steep descent from 102 km the light lasted about six seconds and extinguished near 39 km at 8.4 km/s. The 7,750 m/s level pass stayed cold. The [entry checks](../tools/tests/entry_heat_checks.cpp) also exercise shallow approaches, exits, reversals and a second passage.
- Thirteen [native still cases](../tools/tests/capture_flight_immersion.py) cover the three cockpits, matched entry and level poses, the playable chase camera, the forest visor and two lunar controls. Rain changes the exposed glass on all three ships. The lower opaque dashboard stays unchanged in the dry/wet comparison.
- The [exterior check](../tools/tests/check_entry_volume.py) locates the silhouette using a cold ship and the same empty view. On all three craft the hot front changes at least 99% of the patch clear of the nose. Flank coverage reaches about 54% on the fighter, 60% on the classic and 65% on the Navigator. The distant-sky control stays cold. Inside the fighter, the horizon retains 90% of its measured cold contrast.
- The [twelve-stop route](../tools/tests/2026-11-20-vol-immersion.txt) opens in orbit. F2 and F3 compare entry speed. F4 exercises powered support. F8 and F11 compare the suit in forest and vacuum. F12 starts below the clouds for a rain pass.
- The [motion capture](../tools/tests/capture_reentry_motion.py) follows an 18-second passage from the cold approach through the luminous layer and back to cold flight. The exterior camera travels around the moving ship from ahead of the bow to the rear quarter. The cockpit camera turns 32 degrees and leans 9 cm. A separate six-second shot inspects dry scratches in grazing sunlight.
- Under a sun 13 degrees above the sea, fine scratches on the classic pane brighten on one side and darken on the other. Disabling only the scratches changes the sampled side highlights by up to 21 levels out of 255. The forward sight changes by at most four levels in this pose.
- The [thrust and windscreen route](../tools/tests/2026-11-20-propulsion-verriere.txt) opens in entry. F1 and F2 compare the same cockpit hot and cold. F3 and F4 test full-power departures. F5 and F6 reverse the grazing light. [First iteration and pilot feedback](log/spec-vol-immersion-historique.md)
