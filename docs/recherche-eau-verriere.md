# Water on the canopy glass

**The goal:** realistic and beautiful water on the canopy glass ship. It settles in clouds and in the rain, gathers, sinks, and the air chases it away. No drops drawn with straight-line trails.

**The state, 2026-10-29:** the simulated drops are in place, to be judged in flight.
- **Droplets:** `ShipWater.hlsli`, three calculation passes per frame (`ShipWaterMove`, `ShipWaterClear`, `ShipWaterSplat`), 8 192 at most.
- **The rendering:** in `ShipGlass.hlsl`, drops and trails that dry by crumbling.
- **The fine beads of a prepared texture are removed:** they made a grain that did not look like water.
- **Drying, set the 2026-10-29:**
  - **The air is that of altitude:** the speed passed to the glass is brought back to sea level, like the dynamic pressure. In space, the air no longer pushes the drops.
  - **Droplets that the air cannot blow away,** below 0,5 mm, dry in one minute in calm air and in about seven seconds in fast air. Before, it took them more than an hour.
  - **Above 20 to 35 km, water boils:** drops and trails leave in two or three seconds.
- **Cost is not measured:** in the noise, from 4 to 7 ms per frame in 1080p depending on the view.
- **Memory:** the card and film take 46 MB.

## The observation, 2026-10-29

- **The current model is procedural** (`ShipGlass.hlsl`): beads and nets drawn from a hash grid, moved one block per column.
  - Nothing persists: a drop has no history, does not merge and leaves no water behind it.
  - The movement is straight and regular. Hence the "nail" at high speed.
- **No drops when crossing a cloud, in flight.** Three causes are cumulative:
  - **Drying is too fast:** at 500 m/s, air dries the glass in half a second. At the edge of a cloud, low density hardly wets.
  - **Pearls disappear:** above 15 m/s, they fall to the quarter.
  - **The nets go too fast:** at 5 m/s, they jump of a whole cell at each frame. They don't see each other anymore.
- **We start again from scratch,** on a simulation of water.

## State of the art

- **ToyShop, ATI 2006** ([Tatarchuk, chapter 3.8](https://advances.realtimerendering.com/s2006/Chapter3-Artist-Directable_Real-Time_Rain_Rendering_in_City_Environments.pdf)), based on [Kaneda 1999](https://home.hiroshima-u.ac.jp/kin/publications/JVCA/index.html).
  - **A grid of cells on the glass,** in a texture 16 bits RGBA: mass of water, speed x and y, passage of a drop; plus mass and affinity.
  - **Forces:** gravity according to mass, against static and dynamic friction. These frictions vary on the glass, by a card.
  - **The path:** a drop passes to one of the three cells downstream. The draw is biased by its speed, affinity and wetting of the target cell. Droplets prefer wet, hence the meanders and the tracking of traces.
  - **Rendering:** the mass gives a map of normals. This moves the image of the scene for refraction and reflection. A heavy drop casts a shadow with a pseudo-caustic.
- **X-Plane 12** ([guide développeur](https://developer.x-plane.com/article/windshield-rain-effects/)).
  - **Drop simulated in 3D:** speed, direction and amount of movement, under gravity and aerodynamic forces. They are moved on a 2D texture, one UV island per glass.
  - **A drop dies when leaving its island.**
  - **Friction regulates drags:** less friction, less drags.
- **Particulate matter and height map:**
  - [Stuppacher 2007](https://old.cescg.org/CESCG-2007/papers/Hagenberg-Stuppacher-Ines/index.htm) keeps water in a height card on the GPU. He blurs it, draws normals from it and illuminates it by Fresnel.
  - Chen, Chen and Wong 2013 (cited in the [review by 2024](https://arxiv.org/pdf/2411.15880)) mix particles and height map: merging of droplets and network formation.
  - A [thesis of Umeå, 2021](https://www.diva-portal.org/smash/get/diva2:1571363/FULLTEXT01.pdf), simulates the drops of a windshield by compute shader, then renders them in a 2D texture that distorts the background. Gravity, wind, wiper, and the drops between them. The document could not be read in its entirety.
- **Physics of water in flight,** based on ice-forming studies, e.g. [Leng et al.](https://uhra.herts.ac.uk/id/eprint/14127/1/Leng_et_al_water_film_accepted_manuscript.pdf):
  - **Cloud:** the droplets collected gather into a thin film, pushed downstream by the shear of the air.
  - **Below a critical thickness,** surface tension breaks the film into strands.
  - **The faster the air goes,** the earlier the nets are born and run faster, the narrower and tighter they are.
  - **Droplets in a cloud are tiny:** a few tens of microns. We don't see them one by one: we see the water they form on the glass.

## What we recall

- **A simulation, not a pattern:** the water of the canopy glass is a persistent state. It falls, gathers, sinks and leaves.
- **The hybrid particles and height map,** the common choice of the thesis, of Chen 2013 and X-Plane:
  - **the visible droplets are particles,** with mass, velocity and friction. Small, they remain stuck; big, or pushed by the air, they leave;
  - **a height card in the space of the glass** receives the drops each frame, and keeps the water they leave: their traces, that the next one prefers;
  - **the rendering is read in this map:** normal, refraction of the scene, Fresnel, brightness of the sky. The glass no longer draws a drop itself.
- **The cloud is wetted by a film, then nets:** the capture follows density and speed. The film breaks into thinner and faster nets as the air goes fast.

## The plan

1. **The water map:**
   - two textures in the plane of the ship, which cover the two windows, 1,9 × 4,4 m, at 1,2 mm the texel;
   - the map, in R32_UINT: the water level and the number of the highest drop, for fusions;
   - the film, in R32_FLOAT: the water left on the passage of the drops;
   - the glass is flat, made of two triangles: no UV to create, the plane of the ship is enough.
2. **Droplets in particles** (`ShipWater.hlsli`, compiled in calculation by `ShipWaterMove.hlsl`, `ShipWaterSplat.hlsl` and `ShipWaterClear.hlsl`), a few thousand in a buffer:
   - **Birth:** in rain, in impacts; in cloud, by the capture of the film, which gathers in drops. These droplets then grow by half a millimeter per second, until they drop.
   - **Forces:**
     - gravity in the plane of the glass;
     - the drag of the air, backwards, squared on the speed; the drop bathes in the limit layer, where the air goes only at a tenth of the speed of the vessel;
     - a static friction threshold, increasing for small droplets;
     - the attraction of the wet, for the meanders;
     - a noise surface, so that no trajectory is straight.
   - **Fusion:** two drops that touch make one, by a hash grid.
   - **Death:** exit of the glass, or evaporation. Drying is set to the duration of a flight, not an image.
3. **Deposit:**
   - each drop writes its cap in the map, and leaves a thin film on its passage;
   - the card fades slowly, faster in fast air.
4. **The rendering in `ShipGlass.hlsl`:**
   - normal drawn from the card, smoothed;
   - refraction of the scene by this normal;
   - Fresnel and crescent sky;
   - the film barely blurs the view.
5. **Check:**
   - **in flight:** entering and exiting a cloud at 30, 150 and 500 m/s; rain under a cumulus; ground stop;
   - **in capture:** a sequence of images, not a single image.

**The frost remains as it is.** **The fog is removed**: a veil on all the glass blurred the view without showing anything of the time.
