# Navigator cockpit and original sound

**2026-11-03.** A connected pilotable cabin and a quiet synthesized levitation resonance extend the smooth Navigator; visual fidelity and timbre remain under review.

**Reference interpretation**

- The film shows a metallic chamber with a broad forward viewing field.
- [08:40 and 08:55](https://www.youtube.com/watch?v=qB12mrdYPkc&t=520s) show the landscape filling that field beside the seat, consoles and sensor.
- [10:30](https://www.youtube.com/watch?v=qB12mrdYPkc&t=630s) shows the closed rear wall and its circular fitting.
- The images support a view-dependent panoramic field; they do not establish an ordinary glazed canopy or its optical construction.
- The game treats it as a clear forward field in cockpit view, with an opaque chrome exterior in external views.
- No glass pane, glass distortion or canopy rain simulation is attached to this field.
- Interior proportions are reconstructed from film views, without authenticated production dimensions.

**Geometry**

- Source: `assets/vaisseau/navigateur/vaisseau_travail.blend`.
- Current GLB: `assets/vaisseau/navigateur/navigateur-cockpit.glb`; runtime packet: `vaisseau.vsx`.
- `cabine_maillage.py` and `instruments.py` create six editable closed solids; `preparer.py` retains those parts before batching the GLB export by material.
- The approved subdivided outer hull retains its shape, scale and chrome material.
- A preservation comparison finds less than 0.002 mm position change after the intended scale and rotation; export normals differ by less than 0.01 degrees.
- Cabin walls follow ray intersections with the actual outer hull, inset by 12.5%.
- One connected mesh joins 139 formed wall panels, light sockets, a 1.56 m octagonal rear optical fitting, coved floor, rooted station and swept sensor support.
- Five fitted solids complete the two consoles, bucket seat, seat pad and docking frame.
- Each console has a graduated circular instrument, two knurled rotary controls, a formed palm well, a recessed engraved legend and four captive fastener seats.
- Wells, scales, seals and fasteners share the console's closed surface; their boundaries join the actual deck edges.
- Planar decks retain flat normals beside the rounded returns; sharp transitions split shading at 45 degrees.
- The sensor's casing has a formed crown, side bearing reliefs and cooling returns around a frosted amber lens.
- Curved plate interiors use nested surface samples instead of long triangle fans that distort reflections.
- The cushion has a closed underside projected onto the evaluated bucket shell, with padding formed along its local normals.
- No disconnected primitive meshes form the cabin.
- The complete packet contains 459,757 vertices, 723,264 triangles, 12 material ranges and no texture images.
- Three recessed blue fixtures supply their generated positions to `ShipNavigatorFixtures.hlsli`.
- `controler.py` checks all six evaluated solids are connected and closed, cabin containment and pilot eye clearance.
- At 1,876 sampled mounting points, the consoles, seat frame and cushion contact their actual support meshes with less than 0.02 mm gap.
- Eight rays through the evaluated cabin verify the dial faces and tactile wells are visible from the pilot eye.
- The pilot eye is `(0, -0.65, 0.70)` m in ship space.
- Rotary controls, tactile wells and the sensor remain static; no character voice, facial performance or entrance animation is implemented.

**Instrument design and surface hierarchy**

- Amber and blue segmented arcs distinguish the two main instruments.
- Outer scale marks and shallow geometric legends are mesh regions; no texture or photographed highlight is baked in.
- These are authored interpretations of the film's tactile and optical fittings, not authenticated instrument functions.
- The left blue dial displays actual heading, with a compass needle, cardinal marks and a degree readout.
- The right amber dial displays commanded propulsion, with a 270-degree needle, segmented arc and percentage readout.
- Both read the existing flight constant buffer; no elapsed-time animation substitutes for telemetry.
- Dial centres and radii are generated from the console patches into `ShipNavigatorFixtures.hlsli`.
- Shader marks replace the former fixed raised needles on a continuous flat face; physical rims and mounting interfaces remain intact.
- Perspective derivatives filter fine strokes; luminous marks use linear blue `(0.18, 0.40, 1.0)` or amber `(1.0, 0.32, 0.045)`, emission gain 0.32.
- Dark recesses, a charcoal seat and satin tactile surfaces separate the polished borders from the room's chrome.
- Changed materials use these linear values; unchanged fixture materials remain defined in `cabine_maillage.py`.

| Surface | Linear base colour | Metal | Roughness |
| --- | --- | --- | --- |
| Recess | .012, .018, .027 | .82 | .30 |
| Inner silver | .52, .57, .64 | .97 | .16 |
| Rolled edge | .67, .72, .79 | 1 | .105 |
| Floor | .12, .145, .18 | .90 | .32 |
| Seat | .006, .008, .012 | 0 | .46 |
| Tactile surface | .22, .27, .32 | .88 | .265 |
| Sensor lens | .30, .17, .075 | .02 | .28 |
| Instrument face | .004, .009, .013 | .15 | .20 |
| Etched scale | .34, .41, .45 | .55 | .27 |
| Amber indicator | .45, .13, .018 | .18 | .24 |

- Sensor emission is `(1, .38, .10) × .075`; amber indicators use `(1, .32, .045) × .32`.
- Blender review lighting uses broad white light, a blue strip, a weaker warm return and a local reading light.
- Those studio lights and mild close-up depth of field are review settings, not baked asset data or game lighting changes.

**Rendering and selection**

- `navigateur` starts in cockpit view; Tab cycles cockpit, chase and bare view.
- The fighter remains the executable's default model.
- `ShipProfiles.h` supplies both pilot eye offsets and separates cabin availability from canopy weather.
- VSX material role 10 identifies the reflective exterior; role 11 identifies cabin materials; role 12 identifies live instrument faces.
- Draw the cabin in the ordinary opaque pass in cockpit views, with the world's depth, atmosphere and temporal smoothing.
- Omit hidden cabin geometry from the exterior reflection source to prevent false interior hits.
- Draw the exterior through the existing reflection pass in exterior views; omit it for the cockpit's virtual field.
- Exterior shadows retain the complete closed hull in both views.
- Cabin lights use visible fixture positions and convert authored candela to the engine's normalized solar units.
- Exterior reflection behavior and off-screen limits remain in `spec-reflets-vaisseau.md`.

**Original sound design**

- The film extracts remain listening references; their music and dialogue are not runtime material.
- `NavigatorSound.h` generates every sample from oscillators, filtered noise and short damped delays.
- Quiet noise-excited bands at 164.9, 437.7 and 1031.3 Hz carry the field; slow drift stays below 0.5%.
- A faint 38.17/53.83 Hz sub layer and damped stereo delays add body.
- Power and maneuver demand mainly change level and brightness, without a throttle-linked pitch sweep, combustion pulse or nozzle layer.
- The broad wash is deliberately faint following the user's rejection of the previous motor and jet impressions.
- Power changes glide continuously, without restarting a recorded loop.
- Interior filtering retains body vibration; exterior transport fades with air density.
- Environmental wind remains in world audio and is not duplicated in the ship voice.
- XAudio2 uses the existing master and ship mix controls.
- The other ship profiles retain their existing synthesized engine voices.
- The callback allocates no memory and opens no media files.

**Validation and review**

- Required build: `tools/lance.ps1 -Build -NoLaunch`.
- `tools/tests/check_navigator_sound.ps1` checks finite bounded samples, callback-size invariance, stopping tails and exterior vacuum attenuation.
- The same production synth produces `artifacts/navigateur-cockpit-son-2026-11-03/navigateur-synthese.wav`.
- A 36 s preview covers idle, ramp, cruise, maneuver, cut and exterior sound; its timbre remains subject to listening review.
- `navigateur-regime-v3-ecoute.mp3` isolates seconds 9–22 with +6 dB for listening only; the runtime gain is unchanged by that excerpt.
- `tools/tests/capture_navigator_cabin.py` captures sea, forest, orbit, night, a cabin cutaway, the opaque exterior and paired live instrument states.
- These are normal-rendering functional stills, without desktop automation or performance benchmarks.
- Current native captures are in `artifacts/navigateur-cockpit-son-2026-11-03/integration-v6/`; their CINE logs complete without terrain clamps.
- Native paired views verify heading 000/090 degrees and propulsion 000/060 percent, using the ordinary CINE pose/velocity path.
- `rendus.py --glb --view instruments` reviews physical fittings in Blender; live marks are supplied only by the native shader.
- Release x64, packet shading frames, six-solid topology, mounting contacts and exterior preservation checks pass.
- Warn the user before any game launch; interactive flight and sound timbre remain subject to user review.
- CINE `cabine` accepts the supplied inspection camera while retaining cockpit surface behavior; ordinary `cockpit` uses the profile's pilot eye.
- In-flight route: `tools/tests/2026-11-03-navigateur-cockpit.txt`.
- Launch: `tools/lance.ps1 -ModeleVaisseau navigateur -Resolution fenetre -Parcours tools/tests/2026-11-03-navigateur-cockpit.txt`.
- Superseded primitive construction and sound candidates: `log/recherche-vaisseau-navigateur-historique.md`.
