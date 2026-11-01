# Regional rock per pixel: test set aside

**Status:** work in progress set aside the 2026-10-24, without doc, without quality benchmark. Tag `piste/roche-regionale`, commit `50b37a5`, on `8b4e9b9`. It precedes "one rock", `jalon/16-une-roche`, and has not been recalled.

**Why this file:** its measures only existed in the commit message; they are included here.

## What he was doing

- **Geology per pixel:** a province noise from 3 000 to 200 km, plus units from 40 km to 500 m, `ROCK_UNITS` = 0,5. The pixel takes the average color of its geology, over three readings.
- **A wet rock crust,** `ROCK_CRUST`, and the forest held on the slopes, `VEGETATION_HOLD`.
- **Smoother shades of strata:** `STRATA_TINT` = 0,5; badlands to `STRATA_FORMATION_CONTRAST`.
- **A view of the albedo,** `ALBEDO_VIEW`, and `BANC_MATERIAU=albedo` in `tools/banc_descente.py`, to follow the color in descent.

## What he measured

- **Albedo in descent,** from 800 to 25 km, at 14,85° N 123,2° E: blue lost 20 % before, it gains 4 %.
- **Contrast view of orbit of an arid and rocky earth,** CIELAB on 15 to 60 km: Blue Marble 2,85; before 0,98, faded; geology by pixel only 6,48; the test 3,59.
- **The palette groups:** deviations ΔE from 15 to 19 reduced to 7 to 10.
- **Unmeasured:** `ROCK_CRUST` and `VEGETATION_HOLD`, are mere estimates.

## What is left of it

- **Nothing in `main`:** the rock is a single photo since the 2026-10-24, its strata in color (`../spec-roche-organique.md`).
