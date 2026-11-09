"""Run the pinned PartCrafter implementation locally with explicit source evidence.

Uses its separate environment and model directory. No hosted VLM, image service
or training dependency is required. Invalid parts are reported, never replaced
with placeholder triangles.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import traceback


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, default=Path('E:/ExoluneTools/PartCrafter'))
    p.add_argument('--models', type=Path, default=Path('E:/ComfyUI_Models/models/partcrafter'))
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--parts', type=int, default=6)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--steps', type=int, default=50)
    p.add_argument('--decode-depth', type=int, choices=[8, 9], default=9)
    args = p.parse_args()
    if not 2 <= args.parts <= 12:
        p.error('Use between 2 and 12 explicit parts')
    args.out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(args.repo.resolve()))
    import torch
    import trimesh
    from PIL import Image
    from src.pipelines import pipeline_partcrafter as implementation
    from src.pipelines.pipeline_partcrafter import PartCrafterPipeline
    from accelerate.utils import set_seed
    if torch.cuda.mem_get_info()[0] < 6 * 1024**3:
        raise RuntimeError('This attempt needs 6 GiB free VRAM; do not close unrelated sessions')
    recipe = {'backend': 'PartCrafter official implementation, local isolated runtime',
              'source_revision': subprocess.check_output(['git', '-C', str(args.repo), 'rev-parse', 'HEAD'], text=True).strip(),
              'reference': {'path': str(args.reference.resolve()), 'sha256': digest(args.reference)},
              'parts': args.parts, 'seed': args.seed, 'steps': args.steps, 'tokens_per_part': 1024,
              'guidance': 7.0, 'dense_octree_depth': min(8, args.decode_depth),
              'hierarchical_octree_depth': args.decode_depth, 'cpu_offload': True,
              'models': [{'path': str(f), 'sha256': digest(f)} for f in sorted(args.models.rglob('*.safetensors'))],
              'runner_sha256': digest(__file__)}
    (args.out / 'recipe.json').write_text(json.dumps(recipe, indent=2) + '\n')
    # The official pipeline catches decoder exceptions. Retain their exact
    # evidence instead of silently substituting a dummy part in the export.
    extract = implementation.hierarchical_extract_geometry
    def logged_extract(*values, **keywords):
        try:
            return extract(*values, **keywords)
        except Exception:
            traceback.print_exc()
            raise
    implementation.hierarchical_extract_geometry = logged_extract
    PartCrafterPipeline.model_cpu_offload_seq = 'image_encoder_dinov2->transformer->vae'
    print('Loading pinned local PartCrafter weights', flush=True)
    pipe = PartCrafterPipeline.from_pretrained(str(args.models), torch_dtype=torch.float16, local_files_only=True)
    pipe.enable_model_cpu_offload()
    set_seed(args.seed)
    reference = Image.open(args.reference).convert('RGB')
    # The upstream callback branch references uninitialized image_embeds_1/2.
    # Observe the scheduler result instead; this does not alter inference.
    original_step = pipe.scheduler.step
    completed_steps = 0
    def checkpoint_step(*values, **keywords):
        nonlocal completed_steps
        result = original_step(*values, **keywords)
        completed_steps += 1
        if completed_steps == args.steps:
            latent = result[0] if isinstance(result, tuple) else result.prev_sample
            torch.save(latent.detach().cpu(), args.out / 'shape-latents.pt')
        return result
    pipe.scheduler.step = checkpoint_step
    with torch.inference_mode():
        outputs = pipe(image=[reference] * args.parts, attention_kwargs={'num_parts': args.parts},
                       num_tokens=1024, num_inference_steps=args.steps, guidance_scale=7.0,
                       generator=torch.Generator(device='cuda').manual_seed(args.seed),
                       dense_octree_depth=min(8, args.decode_depth), hierarchical_octree_depth=args.decode_depth,
                       max_num_expanded_coords=64_000_000).meshes
    scene = trimesh.Scene()
    records = []
    colours = [(82, 170, 220, 255), (215, 91, 78, 255), (45, 136, 117, 255),
               (247, 172, 83, 255), (145, 120, 180, 255), (145, 204, 192, 255)]
    for index, mesh in enumerate(outputs):
        if mesh is None or len(mesh.faces) == 0:
            records.append({'index': index, 'status': 'decode failed'})
            continue
        mesh.visual.vertex_colors = colours[index % len(colours)]
        target = args.out / f'part_{index:02}.glb'
        mesh.export(target)
        scene.add_geometry(mesh, geom_name=f'part_{index:02}')
        records.append({'index': index, 'status': 'candidate', 'path': str(target), 'sha256': digest(target),
                        'vertices': len(mesh.vertices), 'triangles': len(mesh.faces),
                        'watertight': bool(mesh.is_watertight), 'winding_consistent': bool(mesh.is_winding_consistent)})
    if scene.geometry:
        scene.export(args.out / 'parts.glb')
    report = {'recipe': recipe, 'parts': records, 'all_parts_decoded': all(r['status'] == 'candidate' for r in records),
              'scope': 'Diagnostic part colours, no PBR material generation',
              'art_accepted': False, 'runtime_accepted': False, 'performance_accepted': False}
    (args.out / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'parts': len(scene.geometry), 'triangles': sum(r.get('triangles', 0) for r in records)}), flush=True)
    if not report['all_parts_decoded']:
        raise RuntimeError('Some parts failed decoding; retained partial evidence')


if __name__ == '__main__':
    main()
