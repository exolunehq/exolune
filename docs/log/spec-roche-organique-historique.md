# Rock ledge history

**2026-11-20 · Replaced texture-driven ledge cover**

- The previous implementation added the rock texture's sampled slope to the terrain slope. It widened the cutoffs only for the texture's unresolved wavelengths.
- At close range, painted grooves generated elongated soil and scree patches across visibly continuous rock.
- The original 64 m rock tile tilted the upper 40% of each bed back by its rise, up to 2.5 m. Height recovered at the foot of the next bed.
- Soil, grass and sand followed those ledges in regular strips. The effect faded towards the texture average by about 500 m.
