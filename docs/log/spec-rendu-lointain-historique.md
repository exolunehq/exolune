# History of distant rendering

**Face-only reconstruction, superseded on 2026-11-20**

- The initial 768 × 768 fine grid stopped at the face. It faded inside the last eight mesh cells. Ring triangles used the coarser surface alone.
- The face was centred on the camera nadir. During oblique flight, a moving ridge could cross the fine-to-coarse boundary below the centre of the image.
- The October review showed clearer snowy ridges at 300 km and clearer desert relief at 5 km. The recorded fine-grid cost rose from 0.2 to 1.8 ms at 56 km and from 0.1 to 0.7 ms at 300 km. The 5 km result stayed within measurement noise.

**The corrections of the material relief pass,** released from `../spec-rendu-lointain.md`, “Corrections made on the way”, the 2026-10-30, when the pass left the engine, commit `3a4508a`. It remains on the `piste/parois-gradins` tag, where it is active; its spec is `spec-relief-reel.md`. The present state is in `../spec-rendu-lointain.md`.

- **Finners in the scree, close up:** in the relief pass, the normal between immediate neighbors varied from one summit to another, and the choices that it commands, rock or not and projection plane, made the relief jump by a meter. The pass now takes the normal on four grid cells on each side. Not reproduced on our sites: to be checked in flight.
- **Relief of the summits further:** it is brought up to the grid cells of 8 m, instead of 1 m, so that cornices and corridors appear earlier on approach. Cost and jitter unchanged.

## 2026-11-02: rejected options of the screen relief

Tried during the screen relief work, then rejected in flight; the current state is in `../spec-rendu-lointain.md`.

- **A smooth-minimum approximation of the valleys' footprint mean of `min(ground, profile)`:** furrows appeared along the divides, and the ground trembled more. Its details are in `spec-erosion-historique.md`; the exact clipped mean replaced it the same day (`../spec-erosion.md`).
- **A statistical water coverage for lakes:** square blocks appeared, because the lake level is fixed per erosion cell. A continuous lake level must come first (`../spec-eaux-interieures.md`).
