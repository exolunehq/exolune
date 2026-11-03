# Vegetation art direction

**Authority and status**
- User direction, 2026-11-02: believable aerial forests and a warm, substantial game world at ground level.
- Avoid photographic saplings, pencil trunks and fragmented needle silhouettes as the dominant close representation.
- Give trunks body, foliage readable bouquets and roots a genuine volumetric connection to the ground.
- Reworking or replacing existing vegetation is authorized.
- Restart model sourcing; controlled structural variants remain preferable to continuing to reshape the old library.
- Latest user direction: reject FoliMesh after native review; continue vegetation work in the other active conversation.
- Tool survey and proposed comparison: `recherche-generation-vegetale.md`.
- The FoliMesh POC looks worse than the previous vegetation to the user; its technical results and limitations are archived in `log/recherche-generation-vegetale-historique.md`.
- Premium paid packs with broad model and variant coverage remain an alternative.
- Bentley previews were insufficient; the linked Tripo oak is too cartoon-like.
- Local ComfyUI authoring remains an experimental comparison; the first Pixal3D tree has fused foliage; `recherche-comfyui-vegetation.md`.
- The circled mature tree in Tripo's article cover is an artistic reference; its provenance and actual 3D output are unverified.
- Implementation is in progress; the first diverse catalogue is a technical baseline, not an accepted artistic result.
- The 31-model rooted prototype passes functional checks; its close art and dark undergrowth remain insufficient against the boards.
- Validation remains in background processes and hidden native renders; no Computer Use or interactive launch.

**Reference boards**
- Source: [user-provided biome boards](https://chatgpt.com/s/m_6ae84ff1010c8191b850e1332368b7f5).
- All eight boards were retrieved from the shared page and inspected.
- Reference images and their fingerprints remain in ignored `x64/VegetationDiversity/references/`.
- Treat the boards as art direction; do not apply their pictures as terrain textures or add decorative terrain forms.

| Biome | Dominant silhouettes | Ground layer and connection |
|---|---|---|
| Temperate forest | Mature broad trunks, asymmetric full crowns, occasional slender companions | Fern masses, bushes, grasses, leaf litter, mossy roots and stones |
| Meadow and hedgerow | Open-crowned broadleaves and grouped shrubs | Uneven grass heights, restrained flower patches, exposed rooted soil |
| Mediterranean | Gnarled trunks, broad evergreen crowns and parasol forms | Dry grey-green shrubs, coarse grass clumps, dusty roots and pale stones |
| Boreal and mountain | Substantial conifers, layered crowns, exposed mature pine forms | Low shrubs, fern/heather-like masses, moss, litter and roots gripping rock |
| Desert and arid land | Rare small trees, sparse rounded scrub | Dry grass tufts, bare ground and restrained dusty root contacts |
| Savanna | Widely spaced umbrella crowns and strong branching | Golden grass masses, scattered shrubs and large open intervals |
| Humid tropical forest | Large trunks, buttresses, layered leafy crowns | Broad leaves, fern masses, rich undergrowth and strong root flares |
| Marsh and wetland | Open damp woodland, broad or drooping crowns | Reed-like grass clumps and bank vegetation around water; rooted terrain stays authoritative |

**Implementation rules**
- Strengthen silhouettes and foliage masses without replacing crowns abruptly during approach.
- Bake each proxy from its own final game model; preserve the existing whole-plant and mesh/impostor relay.
- Use real root meshes, buried ends and a flared trunk base; a flat disc or colour decal alone is insufficient.
- Fit nearby roots to shared terrain samples; never create a second terrain or a pedestal under each tree.
- Keep the trunk's actual base at the placement origin and preserve crown scale when adding root bounds.
- Blend contact materials locally; colour grading must not conceal a floating root or a missing volume.
- Retain climate-compatible dominant forms and companions; diversity does not imply a random botanical mixture.
- Keep warm material variation restrained; retain each biome's dry, cold or humid character.
- Bound placement, root sampling and animation; no new per-frame CPU/GPU wait.
- Check several sites, both approach and ground views, and more than one sun direction.

**First review targets**
- Temperate and tropical broadleaves: stronger lower trunks, fuller leaf bouquets, readable rooted bases.
- Conifers: replace the overly photographic sparse fir presentation with a more substantial game architecture.
- Forest floor: introduce fern forms and connect low vegetation to tree bases without filling every clearing.
- Grounding: cached local terrain contacts, fixed roots under wind and smoothly introduced contact detail.
