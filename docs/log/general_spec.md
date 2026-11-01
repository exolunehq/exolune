# Technical and functional specifications

## Engine objective

Create a 3D engine that performs under DirectX for a space game capable of:

* View a planet in real time, from space to landing on its surface.
* Dynamically generate detailed terrain based on camera position and orientation. View more

## Main features of the app

### General view of the

* Seamless transition between space (distant planetary view) and local (detailed planet surface) views.

## Generation of the planetary terrain

### Basic principles

* The initial plane mesh consists of a certain number of vertices, positioned at a certain altitude relative to the orbital center of the planet.
* The wick should always be oriented facing the camera position to maximize the efficiency of the rendering.

### Generation methodology

* Each frame:

  1. Position the mesh:

     1. **Positioning:**

        * The center of the mesh must be located exactly on the line connecting the center of the planet to the camera.
        * The position of the mesh must be at an exact distance of **6 378 km** from the center of the planet, or to the Earth's surface.

     2. **Orientation:**

        * The mesh must be oriented according to the plane tangent to the surface of the planet at the point determined previously.
        * The orientation of the mesh must be perpendicular to the vector connecting the center of the planet and the camera (the normal of the mesh corresponds exactly to this vector).
    
    Possible practical implementation:
    1. We position the mesh at the center of the planet (0,0,0)
    2. It is simply oriented so that it always faces the camera position.
    3. We move the coordinates of the vertices so that they are at 6,378km from the center. As we are in
    the relative space of the mesh, in fact we just have to raise the vertices (so we could even do it before the point 2 if we wanted)
    4. Finally we normalize to spherize.

     ### Summary in technical terms

     * **Mesh center**: Position of the tangent point on the planet surface, determined by the intersection of the line connecting the center of the planet to the camera.
     * **Normal mesh**: Vector directed from the center of the planet to the camera.
     * **Exact distance**: Earth radius of 6 378 km.

  2. Normalize the vertices to obtain a natural spherical curvature of the mesh.

  3. Subdivision of the mesh

     #### 1. Adaptive subdivision into "spider web"

     * The subdivision follows a radial pattern, similar to a spider web, with a high density of subdivision in the center.
     * The subdivision density gradually decreases as one moves away from the center to the edges of the mesh.

     #### 2. Dynamic determination of the subdivision center

     * The center of the canvas does not necessarily correspond to the geometric center of the mesh.
     * The center is determined dynamically in real time, based on:

       * The position of the camera relative to the mesh.
       * The viewing vector (direction of viewing) of the camera.
       * The intersection between the look vector and the mesh (focal point).

     #### 3. Dynamic management of the level of detail

     * Implementation of an adaptive retail control system to:

       * Dynamically adjust the density of the mesh around the focal point.
       * Rapidly reduce density away from the focal point to save resources.
     * Ensure a smooth and imperceptible transition between different detail level areas.

  4. Select only the vertices visible by the camera for optimization.

  5. Send the vertex coordinates to the Compute Shader for parallel computing.

  6. Apply nested coherent noise functions (Coherent Noise) to calculate the elevations of each vertex.

  7. Applying elevation to vertices

  8. Generate a consistent color rendering according to elevation (ex: blue for water, brown for earth, white for snow).

### Optimizing performance

* Intense use of the GPU via Compute Shaders (GP-GPU).
* Generation only of visible vertices to avoid waste of resources GPU.

## Management of the Camera

### Positioning and movement

* Initially positioned in near orbit for development.
* Ability to move smoothly to the surface to verify consistency and performance of the rendering in real time.

###

## General technical specifications

### Technology and environment

* DirectX (Direct3D) for graphics rendering.
* Compute Shader for intensive parallel computing (GPGPU).
* Nested Coherent Noise algorithms for consistent and realistic procedural generation.

### Performance requirements

* Real time with smooth refresh rate (minimum 30-60 FPS).
* Generate and instantly adapt details to each movement or change of camera view.

## Additional notes

* The initial generation on a cosmic scale (positioning of solar systems) is planned but will be addressed in a second step.
* This document is evolving, to be enriched as technical progress and intermediate validations.
