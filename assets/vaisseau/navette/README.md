# Navette flight exterior

**Production packet**

- `vaisseau.vsx` is the playable derivative of the *Exolune par les crêtes* and *Surface Echo* film shuttle. Its SHA-256 is `0802c68fe617cdc2ca3b1c9b6a1ed4f9b9338fc89d9f84250499f8f227c78d0f`.
- The source comes from film renderer snapshot `34d3840`. Its packet SHA-256 is `d4498a432d77d4f37d68865fb0a3564d80c18ee9e1650977b355d7c1d865dfc6`.
- The side profile follows `design/design-A3-verre.png`. The formed nacelle shoulders follow its rear study `design/revue-arriere/petites-ailes-arrondies.png`.
- The original enamel cap, rolled lip and liner extend sideways together above each turbine. Their span grows from 5.37 m to 8.56 m. The six stators in each opening stay seated.
- A keyed spar guides each lip. Twin telescopic rams connect it to the fixed nacelle through a transverse pin. Each sleeve retains at least 12 cm of engagement at full deployment. The terminal shoes follow the triangles of the rolled underside.
- Two dorsal airbrakes lift from the pressure shell inboard of the nacelles.
- The dark teal belt follows the original amber sill fibre. Its colour uses the enamel's second UV set. The raised amber guide follows the six measured vane edges.
- `JET3` carries each film exhaust axis and its fitted aperture. A linear 192 × 96 image records discharge depth, individual slot emission and the merged envelope. Both plumes start between the six ceramic vanes.
- The fin keeps its turquoise leading panel. Its trailing edge sweeps into the deck, and the aft sections narrow towards the stern. Fine panel breaks and fasteners follow the shell. Four hover outlets fit its underside.
- The cabin keeps the seats and instruments. The cooker omits the 37,892 pilot and passenger triangles and their two exclusive images. The film source used Microsoft Rocketbox. [Source license](licences/Rocketbox.txt)
- `FLW2` stores the brake hinges and the transverse travel. The skin carries its displacement gradient. Each rigid slide has a constant displacement. The colour and shadow passes use the same pose. `WTR1` carries the canopy normals, radii and edge distances for water and frost.

**Rebuild**

- Run the cooker with Blender 5.2 from the worktree root. Pass a pristine copy of the film VSX and a distinct output path.

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b --factory-startup --python-exit-code 1 -P assets/vaisseau/navette/finish_exterior.py -- '<film>/vaisseau.vsx' '<output>/vaisseau.vsx'
```

- [Model selection and flight review](../../../docs/lancement.md)
