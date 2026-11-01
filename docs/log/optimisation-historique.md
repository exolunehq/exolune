# History of optimization

**What was used for rounds, and no longer describes the present state** (`../optimisation.md`).

## Round 1: the initial analysis

**Cloud passing weighs the most everywhere,** from 10 to 51 ms. One ray per pixel at full resolution, in each frame; with each step in a cloud, four samples towards the sun.

**What each part costs,** measured by shader variants:
- **The distant quadrature,** four rays more per pixel in the distance (`spike-nuages-orbite.md`): 39 ms on 51 in orbit, 11 on the globe, 6 at sea, 4 at cumulus. In sea and cumulus, the camera under 14 km turns it off: these 6 and 4 ms came from the weight of its code on the registers of all pixels.
- **The shadow of clouds on the ground,** a walk to the sun per illuminated pixel: 3 to 4 ms near the ground, 1 to 6 elsewhere.
- **The main march, without these two parts:** still 23 to 35 ms at sea, at cumulus and on the globe. By raking the horizon, a radius crosses hundreds of kilometers of layer at steps of 240 m at most.

## Round 2: the initial analysis

**The terrain drawing weighed 11 to 17 ms near the ground, and 12 ms overhead.** The vertex shader and the frame take only 0,2 to 0,3 ms: everything is in the pixel shader.

**What each part costs,** shader variants before depth first, ms in forest / mountain / flyover:
- **The whole soil, materials and vegetation:** 12,4 / 16,6 / 11,4. The rest, normal, light, sea: 0,5 to 0,7.
- **Vegetation:** 4,9 / 7,0 / 5,5.
- **The textures:** 5,1 / 9,4 / 4,1.
- **The local and retail noise functions:** 2,9 / 3,0 / 2,8.
- **The strata:** 0,8 / 0,4 / 1,0; squares of slopes 0,2 / 1,8 / 0,4; normals of splines and fine slope, up to 0,5 each.

**After depth first,** ms in forest / mountain / flyover / orbit:
- **The presence of wood:** 1,5 / 1,8 / 2,6 / 0,6; the slab of the canopy: 0,8 / 1,0 / 1,1 / 0,2; `PlantsDrawn`: 0,8 / 0,8 / 0,6 / 0,5.
- **Rock:** 1,0 / 2,8 / 1,5 / 0,7; grass: 1,2 / 0,9 / 0,7 / 0,3.

**Quad overhead,** measured after depth first (`IsHelperLane`, model 6.6): 2,0 lanes per pixel shown in flyby, 1,9 in forest, 1,6 in mountain and cumulus, 1,2 in orbit.
