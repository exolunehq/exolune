# Local 3D generation trials

**Status**

- Three official Comfy-Org graphs, copied without changes on 2026-11-02.
- Source revision, fingerprints and license: `sources.json`, `LICENSE.Comfy-Org`.
- JSON syntax, unique outer node IDs, link endpoints and an export node were checked.
- The unchanged upstream graphs have not been executed locally.
- A derived Pixal3D 1024 graph completed on the RTX 4070 Ti 12 GiB; see `trials/2026-11-02-oak-pixal3d/`.
- Models already installed on E: were reused; no model download or ComfyUI source change was needed.
- The user finds the first tree visually promising; density and fused foliage remain production constraints.

**Completed local trial**

- [Canvas](trials/2026-11-02-oak-pixal3d/workflow.json), [API request](trials/2026-11-02-oak-pixal3d/api.json), [provenance and result](trials/2026-11-02-oak-pixal3d/manifest.json).
- ComfyUI: `http://127.0.0.1:8188`; saved workflow: `Exolune/01_oak_pixal3d_1024.json`.
- Input: `E:/ComfyUI/input/exolune/oak-reference.png`; a 210 by 274 pixel crop from the user's temperate board.
- Outputs and five actual Blender views: `E:/ComfyUI/output/Exolune/2026-11-02/`.
- The graph saves raw GLB and vertex-coloured GLB before any reduction or solid remeshing.
- Vertex colour is not a UV-baked PBR material; the approximately 14-million-triangle export is an authoring result.
- Load the canvas from ComfyUI's workflow list, or import the canvas JSON; the API file is a `/prompt` request body.
- Reference pixels and GLBs are excluded from git; the manifest fingerprints the local files and six model containers.
- Detailed assessment: `docs/log/recherche-generation-vegetale-historique.md`.
- CPU reduction review: `E:/ComfyUI/output/Exolune/2026-11-02/reduction/`; cleaned derivative: 40,159 triangles / 18,877 vertices.
- Vertex-colour-only reduction loses surface detail; UV/normal baking and leaf deformation remain separate work.
- Learned compact-mesh candidates and usage limits: `docs/recherche-comfyui-vegetation.md`.

**Choose a graph**

| File | Use |
|---|---|
| [pixal3d_trellis2.json](pixal3d_trellis2.json) | Same input image through Pixal3D or TRELLIS.2; full PBR processing |
| [pixal3d_multiview.json](pixal3d_multiview.json) | Several consistent views of the same subject; additional sides must depict the same branches |
| [hunyuan3d21_geometry.json](hunyuan3d21_geometry.json) | Independent Hunyuan3D 2.1 geometry comparison; native template produces an untextured mesh |

**Load and models**

- Import the JSON into a current ComfyUI with the corresponding native nodes.
- [Official Pixal3D setup and model locations](https://docs.comfy.org/tutorials/3d/pixal3d).
- [Official TRELLIS.2 setup and model locations](https://docs.comfy.org/tutorials/3d/trellis2).
- [Official Hunyuan3D setup](https://docs.comfy.org/tutorials/3d/hunyuan3D-2).
- In the combined graph, node 316 selects the model: false is Pixal3D, true is TRELLIS.2.
- Use the published INT8 diffusion files for the initial consumer-GPU trial.
- Model file size is not peak VRAM; sparse shape complexity, VAE decoding and texture baking also matter.
- The official single-view graph references both checkpoints; follow its model notes before running.
- The multi-view graph's crop coordinates target its supplied character sheet; adapt every crop to the actual tree views.

**Vegetation trial**

- First input: one mature temperate tree matching the user's boards, fully visible on a simple background.
- Include the root flare; omit a landscape, circular soil slab, caption, dramatic shadow and artificial depth blur.
- Compare the raw geometry with a neutral material before judging generated texture detail.
- Preserve a raw export before remeshing, hole filling or aggressive reduction.
- Evaluate the full tree first; if foliage collapses, compare a woody trunk/root subject and a separate leafy branch subject.
- A second view helps hidden sides only when it is consistent with the first; independent invented views can contradict branch structure.
- Inspect lower trunk body, branch junctions, crown gaps, root volume and all sides at walking distance.
- Generate several variants only after one candidate meets the art direction.

**Upstream settings and trial choices**

- Batch size 1; run geometry and texture stages separately when possible.
- The upstream graph's shape upsampling is 1536 (node 94); try 1024 first to assess local feasibility.
- The upstream remesher uses solid mode at 768 (node 241); compare against the raw mesh before applying it to foliage.
- The upstream decimator targets 700,000 faces (node 186); this is an authoring mesh, not a forest instance budget.
- Texture and normal baking start at 2048; raise detail only when the structural trial is convincing.
- These lower-resolution choices can lose fine leaves; a successful low-memory run does not establish final fidelity.
- Keep neutral views of the raw and reduced versions together; bark painted on a smooth trunk cannot replace its volume.
- Do not run Exolune and inference on the GPU together during a trial.

**Output**

- Preserve reference, model revision, seed, workflow JSON, raw mesh and final material maps.
- ComfyUI authoring stays outside gameplay; only selected cooked assets enter the game.
- The current Exolune catalogue is unchanged by these graph files.
