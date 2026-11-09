# Celestial prototype history

**2026-11-08 first landable body**
- Superseded the first moon's visual-only sphere and LROC material with shared procedural relief, contact and a cooked far proxy.
- The other two moons retain the previous visual implementation.
- The fixed 5 cm near plane from the erosion integration replaces the former variable near plane; infinite reversed Z remains.

**2026-11-07 visual iteration**
- Rejected broad procedural lunar albedo: smooth spots read as a painted sphere during approach.
- Replaced it with normalized LROC albedo and LOLA normal slopes, with source credit and a reproducible asset cook.
- Reduced local bright-disc exposure from 24 to 8 to retain surface contrast.
- Replaced sky-only sphere composition with scene-depth rendering so nearby moons can occult Exolune and reproject at their actual distance.
- Broke up the initial regular galactic dust lane with volume-scale density variation.
- Capped stellar display exposure at 2,000,000 while retaining its 650,000 lower response bound.
- Replaced the 1-billion-metre far plane after it clipped the finite Sun; infinite reversed depth retains astronomical sources.
- Replaced fixed night cockpit emission after it saturated the instrument displays under night adaptation.
- Enabled the existing energy-conserving glare after the correctly sized solar disc read as a weak point on the display.
- Current behavior: `../spec-ciel-celeste.md`.
