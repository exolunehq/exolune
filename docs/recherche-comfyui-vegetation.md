# Local ComfyUI vegetation generation

**Current result**

- Checked against primary documentation and exercised locally on 2026-11-02.
- A complete brief/reference-to-GLB authoring chain runs through native ComfyUI and background Blender.
- The selected witness uses FLUX.3 Image Klein references, TRELLIS.2 wood, UV material baking and separately generated leaf cutouts.
- On the same bare-oak reference, TRELLIS.2 gave a more convincing woody body and roots than Pixal3D.
- This subject-specific comparison does not establish a universal model ranking.
- The user selects the earlier surface assembly: 39,933 triangles, two materials and 4,644 individual leaf cutouts.
- The fuller crown-volume assembly remains an alternative; it does not replace the approved master.
- The pipeline completes locally on the existing 12 GiB RTX 4070 Ti; all models remain on E:.
- No well-documented, vegetation-specific neural model proving the requested FPS result was found.
- Native import, seven mesh LODs, source-weighted wind and impostor cooking are implemented; legacy five-level assets remain compatible.
- Native review exposed source branch loops; the selected offline render does not approve that master for production.
- Native art and complete performance/quality acceptance remain separate gates in the production report.
- Current design and usage: `spec-pipeline-creation3d.md` and `tools/foliage/local3d/README.md`.
- Earlier whole-tree and reduction trials: `log/recherche-generation-vegetale-historique.md`.

**Verified candidates**

| Workflow | Current evidence | Remaining limit |
|---|---|---|
| [Native TRELLIS.2](https://docs.comfy.org/tutorials/3d/trellis2) | Successful local woody geometry and PBR cooking at 1024; selected for the witness | Thin tips and unseen surfaces remain imperfect; no botanical hierarchy is inferred |
| [Native Pixal3D](https://docs.comfy.org/tutorials/3d/pixal3d) | Successful local whole-tree and isolated-wood trials; same downstream material cook | The full-tree crown becomes fused masses; wood quality differs by input |
| [Pixal3D multiview](https://docs.comfy.org/tutorials/3d/pixal3d#pixal3d-multi-views) | Official workflow accepts several views | No local comparison; input branches and roots must agree between views |
| [Hunyuan3D 2.1](https://docs.comfy.org/tutorials/3d/hunyuan3D-2) | Official native geometry comparison remains available | Not executed here; the native geometry graph alone is not the complete PBR pipeline |

**Why this decomposition**

- Generate artistic wood and leaf appearance, then assemble game-specific leaf geometry explicitly.
- Reducing an entire vertex-coloured tree lost visible surface detail in the first trial.
- Bake high geometry and predicted materials onto the low woody mesh instead.
- Keep leaf transparency and attachment data outside solid woody remeshing.
- A generated leaf provides a reusable texture; distinct curved cutouts provide geometry that can flutter.
- Surface and bounded crown-volume presets provide different crown structures from the same wood and leaf sources.
- This is an implemented hybrid workflow, not a specialized botanical foundation model.
- Technical export checks cannot accept the tree's art direction.

**Learned compact-mesh generation, checked 2026-11-02**

- This fork focuses on local ComfyUI generation; other asset sourcing is handled separately.
- Distinguish learned mesh reconstruction, conventional decimation and a complete game-asset workflow.
- A low vertex count alone provides neither UVs nor leaf attachments, material separation or wind weights.

| Candidate | Verified capability | Current limit |
|---|---|---|
| [TreeMeshGPT](https://github.com/sail-sg/TreeMeshGPT) | Released dense-mesh reconstruction; up to 5,500 / 11,000 faces with 7-bit / 9-bit checkpoints; [MIT code](https://github.com/sail-sg/TreeMeshGPT/blob/main/LICENSE) | First codebase retained for a bounded comparison; checkpoint terms, Windows memory and ComfyUI integration remain unverified; its name describes mesh sequencing, not botany |
| [MeshFlow](https://github.com/facebookresearch/meshflow) | Learned positions/connectivity, optional image guidance and approximate vertex control; [ComfyUI wrapper](https://github.com/Rizzlord/ComfyUI-MeshFlow) available | [FAIR Noncommercial Research License](https://github.com/facebookresearch/meshflow/blob/main/LICENSE) covers outputs; not a commercial production recommendation; no local run |
| [FastMesh](https://github.com/jhkim0759/FastMesh) | Released inference and V1K/V4K compact-mesh variants | [S-Lab noncommercial licence](https://github.com/jhkim0759/FastMesh/blob/main/LICENSE); upstream A6000 setup does not establish a 12 GiB ComfyUI run |
| [MeshAnything V2](https://github.com/buaacyw/MeshAnythingV2) | Official maximum 1,600 faces; approximately 8 GiB inference reported on A6000 | [S-Lab noncommercial licence](https://github.com/buaacyw/MeshAnythingV2/blob/main/LICENSE.txt); bounded woody components are a more plausible first subject than an entire mature crown |
| [BPT](https://github.com/Tencent-Hunyuan/bpt) | Released point-cloud reconstruction above 8,000 faces; approximately 12 GiB FP16 upstream; [ComfyUI wrapper](https://github.com/Easymode-ai/ComfyUI-BPT) | [Current upstream licence](https://github.com/Tencent-Hunyuan/bpt/blob/main/License) expressly excludes the EU; do not install it here under that grant |
| [Mesh Silksong](https://github.com/gaochao-s/Mesh-Silksong) | Learned topology preservation, lite checkpoint and [MIT repository code](https://github.com/gaochao-s/Mesh-Silksong/blob/main/LICENSE) | Checkpoint terms and local memory need verification; no ComfyUI integration validated here |

- None of the inspected demonstrations establishes the required animated FPS tree.
- No additional model above was downloaded, installed or executed during this survey.
- TreeMeshGPT's dependencies differ from the working Python 3.13 environment; keep any future trial isolated.
- For Pixal3D, preserve high-detail geometry, derive a compact mesh and bake colour and normal detail onto UVs.
- Evaluate woody structure and leaf clusters separately before expecting coherent wind.

**Local implementation**

- Tested with ComfyUI 0.43.0, Python 3.13.1, torch 2.11.0+cu128 and Blender 5.2.1 LTS.
- Native INT8 image and 3D weights reuse the existing `E:/ComfyUI_Models/models` files.
- No new wrapper, checkpoint, cloud service or environment downgrade was needed.
- CPU assembly and exported-file review avoid taking desktop focus.
- Stages preserve API graphs, native canvases, execution histories and artifact hashes.
- Native templates derive from Comfy-Org revision `60d0d2c2f5c98ab50116abd837156e4010534657`, MIT.
- Model terms remain separate from workflow licensing; retain the [FLUX Kommunity terms](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy/blob/main/LICENSE.md) for the image stages.
- The runner can resume a submitted job and reuse verified completed stages.
- The current experiment establishes functional feasibility, not a peak-memory bound or forest performance.

**Production acceptance**

- Review a convincing mature tree before expanding to biomes.
- Inspect neutral geometry and textured relighting from all sides, including under the crown.
- Remove or repair torn branch tips; inspect leaf scale and crown asymmetry.
- Check roots on flat and sloping Exolune terrain after selection.
- Preserve a bounded pool of artistically coherent variants.
- The common native cook derives LODs and distant proxies from the selected plant, with coverage-preserving leaf mipmaps.
- Source weights now drive the shared colour/depth wind deformation around fixed roots.
- Verify seamless approach, native materials and frame budgets through `produce.py` before expanding the library.
- The 40k-only native cost comparison failed the performance target; history is retained in `log/spec-pipeline-creation3d-historique.md`.
- The multi-LOD candidate must pass its own paired measurements and canonical quality comparison.
