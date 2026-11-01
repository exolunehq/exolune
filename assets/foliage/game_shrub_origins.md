# Game shrub: source and conversion

- **Source:** [Searsia Lucida](https://polyhaven.com/a/searsia_lucida), variant `searsia_lucida_f_LOD0`, by James Ray Cock (modeling) and Jenelle van Heerden (photography).
- **License:** [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/); free use and redistribution.
- **Mesh:** 7,232 triangles, original branches and leaves. Opaque bark uses material 0; cutout leaves and twigs use material 1.
- **Textures:** colors, separate alpha, OpenGL normals, occlusion and roughness from Poly Haven. Transmission is constant per material.
- **Modifications:** conversion to the engine's format, horizontal centering, normalized height, volume and impostor generation. Alpha cutout is adjusted to the engine's threshold; the source model uses gradual transparency.
- **Rebuild:** `python tools/foliage/importe_arbuste.py` downloads files pinned by SHA-256 and creates atlases and mesh; `python tools/foliage/bake.py game_shrub --volume-res 64` creates the volume and impostors. Dependencies: numpy, Pillow and numba.
- **Limit:** appearance and cost in flight remain to be evaluated.
