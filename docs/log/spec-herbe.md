# Specification: grass strands in geometry

**In the log since the 2026-10-30:** never made. The near grass came otherwise: from tufts of 40 strands generated, among the near objects, `../spec-objets-proximite.md`, step 2.

Status: proposed the 2026-10-21, revised after the search of `etat-de-l-art-details.md`, to validate. Part of the `spec-rendu.md` E stage, details on the surface. Follows the grass texture from step D.

## The purpose

**Real strands that stand near the camera,** to give the scale at ground level.

- **The grass texture of step D** paints the floor: tufts, grain, shades. Viewed from above, it is enough.
- **In a raised view, it remains flat:** nothing rises, nothing is cut on the bottom. Yet this is what the eye takes for scale reference frame.
- **The strands extend the texture,** without replacing it: same tufts, same shades. From afar, only the texture remains.

## The two approaches

|  | Strands in geometry | Shells |
|---|---|---|
| **Prince** | A calculation generates the nearest strands for each frame; each is a small ribbon of triangles, drawn by instances | The near ground is redrawn in 8 to 16 superimposed layers; each pixel in a layer keeps or throws a strand section |
| **Top view** | Well | Well |
| **Raised view** | Straight strands, silhouettes on the background | Layers separate: stacks of discs, no silhouette |
| **flicker** | Thin strands to hold at least one pixel wide | Cuts to pixel close, sparkles under temporal smoothing |
| **Cost** | Proportional to the number of strands | Proportional to near surface area, multiplied by number of layers |
| **Concept** | All by frame, no memory | All by frame, no memory |

**Recommendation: strands in geometry.** Only they give the scale in rasant view, where it is lacking. The shells are hardly better than the current texture.

## The principle adopted

### A grid fixed on the planet

**Each strand is born in a square of a fixed grid on the planet:** the six faces of a cube projected on the sphere, as in the POC of fixed vertices.

- **Exact clues:** one face, then two integers per square. With boxes of 3 cm, they remain under 2³¹.
- **Precision:** the CPU doubles the center of the window of boxes around the camera; the GPU works in float offsets from this center. Method and tangent in series taken from POC, tag `piste/sommets-fixes-etape3`.
- **Each strand is drawn from the hash of its box:** position in the box, orientation, height, width, curvature, hue. Nothing is stored from one frame to another: the same strand reappears in the same place, identical.

### Where the grass grows, and how much

- **The strands are born from tufts:** density follows the range of tufts of grass texture, `TuftField` in `PixelShader.hlsl`. The strands are grouped in tufts, with sparser feet between them.
- **Only where grass texture is present:** same weight as in `GroundAt`, including height mixing with snow and rock.
- **Same shade as the ground below:** the ground color is evaluated at the base of the strand, by the same function as the ground pixels. The foot takes this color, the tip pulls towards yellow-green. A strand that fades leaves the ground of the same color.
- **The ground under the grass darkens** according to the density of the strands, by the same function.

### Lightening with distance

**The density decreases continuously with distance, without step.**

- **Each strand is randomly ranked** between 0 and 1. It is kept if its rank is below the desired density at its distance.
- **A strand that will disappear shrinks first,** on a small margin of row. He doesn't jump.
- **The far strands widen** to stay at least one pixel away, and do not flicker. Fewer strands, wider, rather than transparency.
- **In the distance, the normal tends to that of the tuft:** reflections no longer sparkle.
- **Beyond about 30 m, no more strands:** the texture alone, of the same medium shade.
- **Above 30 m altitude, no strands at all,** with a fade between 20 and 30 m.

### Laid on the floor drawn

**The strands must land exactly on the floor that we see,** which is the mesh sliding.

- **By inversion of the mesh:** the position of a strand on the planet gives its coordinates in the face or in a ring, by the inverse calculation of that of the vertices. We read the three vertices of the triangle that bears it, and we interpolate their height.
- **No additional password,** and no memory.
- **Near the camera, the mesh has grid cells of a few centimeters:** the height slides by less than a millimeter, without jitter visible.
- **A local elevation map, viewed from above,** planned first, remains in reserve if reversal proves too costly.

### Calculation and drawing

1. **A per-box calculation** of the window around the camera: it pulls the strand, applies density, spreads strands out of the field, and adds the others to a list.
2. **An indirect drawing** of the strands of the list.

### The form, after Ghost of Tsushima

- **Each strand is a Bézier curve,** set by its height, inclination, curvature, and orientation, and tapers toward the tip.
- **Two levels:** 15 summits up to about 15 m, then 7. The strand takes the simplified form before the swing, without jump.
- **tufts from Voronezh,** mixed between the two closest centers to avoid seams. The tuft adjusts height, hue and orientation, and the strands lean towards its center.
- **Heterogeneity:** bare plates, dry strands or brown tip according to a slow moisture noise, 5 to 15 % to start.

### The lighting

- **Normal curve** along the strand and across, so that it lights up like a rounded ribbon.
- **A strand seen by the slice** thickens a little towards the camera, so as not to disappear.
- **A waxy reflection** in rasant view, in trails along the strand.
- **Translucency:** a backlit strand lets through a part of the light, tinted green.
- **Darker foot:** single occlusion, from base to tip.
- **Same track as ground:** high dynamic, distance in alpha for atmosphere and temporal smoothing.
- **No cast shadows:** the engine does not have any yet. The screen contact shadows, from Bend Studio, will come with the rock.

### Wind, optional

- **A curve that waves,** taken from a noise fixed on the planet that scrolls with time.
- **The greatest risk:** temporal smoothing assumes a still scene, and a moving strand leaves a trail.
- **The remedy, inexpensive:** each strand being a function of hash and time, we recalculate it to the previous image to write its movement. The temporal smoothing must then read this movement per pixel. To do before the wind.

## The budget

- **Less than 1 ms to 2 m from the ground,** in 1280 × 720.
- **Order of magnitude:** 50 000 to 100 000 visible strands. Ghost of Tsushima drew about 83 000 strands in 2,5 ms on PS4; a current desktop card should hold 200 000 strands in 1 to 2 ms.
- **The limit will be the drawing of the thin triangles,** not the calculation: to measure early.
- **Nothing when the camera is high.**

## The steps

1. **The strands immobile,** without lighting neat: grid, inversion of the mesh, density, lightening.
2. **The shape and the tufts:** Bézier, two levels, Voronoi, dry strands.
3. **lighting:** normal curve, translucency, dark foot, ground tone.
4. **Settings and measurements:** density, distances, cost.
5. **Motion per pixel for temporal smoothing,** then wind.

## The measure

- **The benchmark of jitter and the mutation benchmark,** on views at 2 m and 10 m above the grass. The strands must not shake when the mesh slides, nor appear in waves when approaching.
- **The cost GPU,** at worst, grass covering the entire screen.
- **The judgment in flight,** at ground level and in descent.

## Validation criteria

- **The scale is read in raised view:** straight strands, silhouettes on the bottom.
- **No visible layer** between strands and texture, neither in flight nor in descent.
- **No flicker** of thin strands.
- **Cost:** less than 1 ms at worst.
