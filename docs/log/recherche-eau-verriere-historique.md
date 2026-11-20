# Canopy water history

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
