# Water and light on cockpit glazing

**Surface simulation**

- The classic ship's folded glass, the fighter's bubble and the Navigator's panoramic field use a common droplet simulation. Each profile describes the coordinates and scale of its exposed surface.
- Up to 8,192 particles store position, size, velocity and flow history. Three compute passes move and merge droplets, dry the film, and write the new water thickness.
- The ship samples existing precipitation and cloud water. Adhesion pins small droplets. Gravity and local air shear move larger ones. Trails temporarily guide following drops.
- The glass shader reads the water thickness and refracts the scene. Use a clear approach, a rainy cloud crossing and a polar approach to judge adhesion, drying and frost in motion.

**Research decisions**

- Laminar Research describes simulating rain on individual window surfaces with continuous mapping and consistent texel density. Exolune keeps its established particle and film implementation and supplies the optical domain per ship. [X-Plane windshield effects](https://developer.x-plane.com/article/windshield-rain-effects/)
- Tatarchuk's real-time rain work describes surface adhesion, rivulets and normal perturbations. These inform the persistent wet traces and highlights. [SIGGRAPH course paper](https://advances.realtimerendering.com/s2006/Chapter3-Artist-Directable_Real-Time_Rain_Rendering_in_City_Environments.pdf)
- Werner and colleagues relate fine scratches on glass to directional highlights. Exolune projects the groove tangent on the actual pane and filters its width across a pixel. The pilot can turn toward a grazing sun and see the grooves catch and release the light. [EPFL paper](https://rgl.epfl.ch/publications/Werner2017Scratch)
- The exterior shock layer casts light onto the window and its seal. The same passage supplies the cockpit and exterior views. [Flight and suit specification](spec-vol-immersion.md)
- Earlier observations, measurements and the original triangular-canopy experiment are in the [research history](log/recherche-eau-verriere-historique.md).
