# POC cloud: fixed reference, 26 October 2026

**Validated in flight by the user:** position, shape and contours stable on approach; appearance considered satisfactory. The requested follow-up is movement with time and less solid fringes.

**Reference stored locally:** `x64/NuagePocReference/`, executable and shaders of the valid version. The first build was in `x64/NuagePoc/`, under the name `MyPlanetEngine.exe`. `codex/nuage-poc` working branch, no commit or push requested.

**Initial settings:** center at 4 000 m, 0,5 N, 161,5 E; four lobes, tile 3D fixed at 4,096 and 1,024 km; extinction at most 24 /km, body fade of 0 to 0,18, diffuse background of 0,18. Full resolution, no more than 12 m, 384 no more than maximum, six points to the sun. No animation, cascade, checkerboard, jitter, history or halo.

**Windowless controls:** five captures at 1 280 × 720 (away, approach, edge, inside and opacity). Eight opacity images with fixed camera and mobile mesh: average difference 0,0000355 on 255, maximum 1 on 255. This check did not demonstrate the actual flight; the user then validated it.

**Iterations:** All full-screen passages must use the same shader format; DXC for full-screen vertex, atmosphere, tones and halo. A DXBC/DXIL mixture prevented pipeline creation during development; fixed before delivery.

**Current follow-up:** `poc-nuage-stable.md`.
