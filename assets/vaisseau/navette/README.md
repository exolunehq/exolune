# Playable transport shuttle

**Runtime asset**

- The `navette` profile loads `vaisseau.vsx`, the self-contained VSX4 packet of the approved V9 shuttle.
- Source GLB SHA-256 is `0cf43af7664acc6534002f6c66a991fa10ab32a8f441e99ad4394143ca2c1b31`.
- The packet includes 47 material batches, two vectoring exhaust charts, seven mirrored auxiliary outlet pairs, the canopy weather chart, seat controls and four independent rigid clips.
- The flight, navigation and equipment displays read the live flight state.
- Launch the [transport route](../../../tools/jouer_navette.cmd) from a local checkout.

**Rebuild**

- Use Blender 5.2 and a system `python` with Pillow on PATH.
- Pass the exact reviewed GLB and the destination packet to the [cooker](../navette_aaa/flight_packet.py).
- The source Blender file, GLB and review images live under `E:/ExoluneAssets/navette-exolune-aaa-2026-11-22`.

~~~powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --python-exit-code 1 -P assets/vaisseau/navette_aaa/flight_packet.py -- 'E:/ExoluneAssets/navette-exolune-aaa-2026-11-22/Navette_Exolune_AAA_v9.glb' 'assets/vaisseau/navette/vaisseau.vsx'
~~~

- [Source geometry and animations](../navette_aaa/README.md)
- [Flight controls](../../../docs/lancement.md#transport-shuttle)
