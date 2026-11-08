# Orbital rendering history

**2026-11-08 · Clouds clipped by the distant-surface blend**
- During overlap with detailed terrain, the proxy used a sphere raised by 8,192 m and published its coverage distance as the physical surface distance.
- The same blend factors interpolated colour and HDR alpha, although alpha contains distance and may be negative for moving ocean pixels.
- Mixing opposite distance signs could move the apparent occluder far in front of both the actual planet and its clouds.
- Even over land, the raised coverage sphere could truncate the 2–8 km low-cloud layer.
- The replacement keeps colour blending, writes filtered physical depth without interpolation and leaves the detailed depth buffer intact.
- Cloud density, layers, weather, exposure and temporal sampling are unchanged.
