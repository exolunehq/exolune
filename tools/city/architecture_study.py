"""Reproducible local ComfyUI controls for the architectural model comparison."""
import argparse
import json
from pathlib import Path
import sys

LOCAL = Path(__file__).resolve().parents[1] / 'foliage/local3d'
sys.path.insert(0, str(LOCAL))
from pipeline import Comfy, fingerprint, image_stage, save, stage, upload_reference


def ancestors(prompt, outputs):
    keep = set()
    def visit(identifier):
        if identifier in keep:
            return
        keep.add(identifier)
        for value in prompt[identifier]['inputs'].values():
            if isinstance(value, list) and len(value) == 2 and str(value[0]) in prompt:
                visit(str(value[0]))
    for identifier in outputs:
        visit(identifier)
    return {k: v for k, v in prompt.items() if k in keep}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['pixal-multiview', 'prepare-partcrafter', 'clean-reference'], required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--rig', type=Path)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--resolution', type=int, choices=[512, 1024], default=512)
    parser.add_argument('--comfy-url', default='http://127.0.0.1:8190')
    parser.add_argument('--comfy-root', type=Path, default=Path('E:/ComfyUI'))
    parser.add_argument('--models', type=Path, default=Path('E:/ComfyUI_Models/models'))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    args.allow_shared_gpu = True
    args.yield_if_gpu_busy = False
    args.minimum_free_vram_gib = 6.5
    args.recipe = {'name': 'house_' + args.mode.replace('-', '_'), 'seed': args.seed,
                   'resolution': args.resolution, 'art_accepted': False}
    comfy = Comfy(args.comfy_url, args.comfy_root)
    schema = comfy.call('object_info')
    if args.mode == 'pixal-multiview':
        if not args.rig:
            parser.error('--rig is required for multiview')
        rig = json.loads(args.rig.read_text())
        p = json.loads((LOCAL / 'templates/wood_pixal3d.json').read_text())['prompt']
        views = {}
        for index, name in enumerate(['front', 'left', 'back', 'right'], 400):
            entry = rig['views'][name]
            path = Path(entry['image'])
            if fingerprint(path) != entry['sha256']:
                raise ValueError('Changed calibrated input: ' + name)
            p[str(index)] = {'class_type': 'LoadImage', 'inputs': {'image': upload_reference(path, args)}}
            views[name] = [str(index), 0]
        p['298'] = {'class_type': 'Pixal3DMultiViewConditioning', 'inputs': {
            'clip_vision_model': ['15', 0], 'fov': rig['fov_degrees'], **views}}
        p['319']['inputs']['unet_name'] = 'pixal3d_multiview_int8_convrot.safetensors'
        p['3']['inputs']['seed'] = p['18']['inputs']['seed'] = p['23']['inputs']['seed'] = args.seed
        if args.resolution == 512:
            p['92']['inputs']['samples'] = ['18', 0]
        roles = {'342': 'high_raw'}
        body = {'prompt': ancestors(p, roles)}
        files = [('diffusion_models', 'pixal3d_multiview_int8_convrot.safetensors'),
                 ('vae', 'trellis_2_shape_vae_bf16.safetensors'),
                 ('clip_vision', 'dino_v3_L_naf_fp32.safetensors')]
        args.recipe['rig'] = {'path': str(args.rig.resolve()), 'sha256': fingerprint(args.rig),
                              'scope': rig['scope'], 'source_sha256': rig['source_sha256']}
    elif args.mode == 'clean-reference':
        if not args.reference:
            parser.error('--reference is required for reference cleanup')
        args.recipe.update({'description': 'The same inhabited solarpunk shell house, exterior architecture only.',
            'image_resolution': 1024, 'image_seeds': {'reference': args.seed},
            'reference': {'path': str(args.reference.resolve()), 'sha256': fingerprint(args.reference)},
            'captions': {'reference':
                'Preserve the exact overall design and proportions of this two-storey house: the small upper '
                'oval inhabited shell above the long lower shell, the continuous flowing structural arch on '
                'the right, the deep openings and the asymmetric ivory curves. Make an isolated exterior '
                'architectural model with clean continuous manufactured surfaces and believable shell thickness. '
                'REMOVE ALL furniture, tables, chairs, plants, hanging vines, rocks, people and loose objects. '
                'The small terrace is completely EMPTY. All glazing is smooth smoked dark teal glass with '
                'fine structural frames; no interior contents visible. Ivory ceramic outer shell, restrained '
                'golden timber recesses and blue solar roof. Show the entire building, including its base, '
                'in the same three-quarter view. Plain white studio background, soft even light. '
                'One building only, no labels, no surrounding ground, no collage.'}})
        files = [('diffusion_models', 'flux3-image-klein-int8-convrot.safetensors'),
                 ('text_encoders', 'qwen3vl_4b_int8_convrot.safetensors'), ('vae', 'flux2-vae.safetensors')]
    else:
        if not args.reference:
            parser.error('--reference is required for input preparation')
        source = upload_reference(args.reference, args)
        body = {'prompt': {
            '1': {'class_type': 'LoadImage', 'inputs': {'image': source}},
            '2': {'class_type': 'LoadBackgroundRemovalModel', 'inputs': {'bg_removal_name': 'birefnet.safetensors'}},
            '3': {'class_type': 'RemoveBackground', 'inputs': {'bg_removal_model': ['2', 0], 'image': ['1', 0]}},
            '4': {'class_type': 'ImageCropToMask', 'inputs': {'images': ['1', 0], 'masks': ['3', 0],
                    'width': 1024, 'height': 1024, 'pad_factor': 1.1, 'grow_mask': 0, 'background': '#ffffff'}},
            '5': {'class_type': 'SaveImage', 'inputs': {'images': ['4', 0], 'filename_prefix': 'house_reference'}}}}
        roles = {'5': 'reference'}
        files = [('background_removal', 'birefnet.safetensors')]
        args.recipe['reference'] = {'path': str(args.reference.resolve()), 'sha256': fingerprint(args.reference)}
    models = []
    for folder, name in files:
        path = args.models / folder / name
        models.append({'path': str(path), 'bytes': path.stat().st_size, 'sha256': fingerprint(path)})
    save(args.out / 'recipe.json', args.recipe)
    if args.mode == 'clean-reference':
        outputs = {'reference': image_stage('reference', args.reference, args, comfy, schema, models)}
    else:
        outputs = stage('wood_mesh' if args.mode == 'pixal-multiview' else 'reference', body, roles,
                        args, comfy, schema, models)
    save(args.out / 'manifest.json', {'recipe': args.recipe, 'models': models,
         'artifacts': {k: {'path': str(v), 'sha256': fingerprint(v)} for k, v in outputs.items()},
         'art_accepted': False, 'runtime_accepted': False, 'performance_accepted': False})


if __name__ == '__main__':
    main()
