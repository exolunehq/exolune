"""One resumable local vegetation chain, from authoring to native acceptance.

Run benchmarks only when requested by the user. --watch retries short isolated
measurement blocks; foreign sessions are never stopped. Reports remain pending
or failed until every declared production gate passes.
"""
from pathlib import Path
import argparse
import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'tools/tests'))
from banc_local3d import RUNTIME, sha
from check_local3d_native import assets
from check_local3d_measurements import check as check_measurements
from audit import check
from review_lods_cpu import review as review_lod_coverage
from variations import derive


def save(path,value):
    path=Path(path);temporary=path.with_suffix(path.suffix+'.'+str(os.getpid())+'.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');temporary.replace(path)


def key(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()[:20]


def variant_approved(variation,digest):
    """A master's approval never approves a different silhouette."""
    if not variation.get('art_approved',False):return False
    if variation.get('approved_sha256')!=digest:raise ValueError('Variant art approval must name the reviewed derived GLB fingerprint')
    return True


def run(command,log):
    print('Running',Path(command[1]).name if len(command)>1 else command[0],flush=True)
    with Path(log).open('a',encoding='utf-8') as stream:
        subprocess.run(list(map(str,command)),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)


def catalogue_hashes(folder):
    result={'biomes.txt':sha(folder/'biomes.txt')}
    for name in sorted({line.split()[0] for line in (folder/'biomes.txt').read_text().splitlines()[1:]}):
        for filename in RUNTIME:
            path=folder/name/filename
            if path.exists():result[name+'/'+filename]=sha(path)
    return result


def store_catalogue(source,target,store):
    """Copy immutable content once, then hardlink it across species catalogues."""
    store.mkdir(parents=True,exist_ok=True);target.mkdir(parents=True,exist_ok=True)
    fingerprints=catalogue_hashes(source)
    for relative,digest in fingerprints.items():
        original=source/relative;dest=target/relative;dest.parent.mkdir(parents=True,exist_ok=True)
        cached=store/(digest+'.bin')
        if not cached.exists():
            temp=store/(digest+'.'+str(os.getpid())+'.tmp');shutil.copyfile(original,temp)
            if sha(temp)!=digest:raise ValueError('Input changed during freezing')
            temp.replace(cached)
        if sha(cached)!=digest:raise ValueError('Shared content store changed: '+str(cached))
        if not dest.exists():
            try:os.link(cached,dest)
            except OSError:shutil.copyfile(cached,dest)
        if sha(dest)!=digest:raise ValueError('Published catalogue changed: '+str(dest))
    for filename in ['native-report.json']:
        shutil.copyfile(source/filename,target/filename)
    name=json.loads((source/'native-report.json').read_text())['name']
    shutil.copyfile(source/name/'lod-report.json',target/name/'lod-report.json')
    save(target/'content.json',fingerprints)


def adopt_performance(previous,target):
    """Reuse raw completed rounds only when frozen render inputs are identical.

    Quality protocols may change independently. Never reuse a quality verdict.
    """
    prior=json.loads((previous/'inputs.json').read_text());current=json.loads((target/'inputs.json').read_text())
    if prior!=current:raise ValueError('Performance adoption requires identical executable, shaders and runtime assets')
    audit=check_measurements(previous);perf=json.loads((previous/'performance.json').read_text())
    if perf['protocol']['samples_per_view_per_round']!=128 or perf['protocol']['warmup']!=32 or perf['protocol']['resolution']!=[1920,1080]:raise ValueError('Performance adoption protocol mismatch')
    hashes={}
    for sequence,kind in enumerate(perf['protocol']['order']):
        source=previous/f'{sequence}_{kind}';dest=target/source.name;dest.mkdir(exist_ok=True)
        for original in source.iterdir():
            if not original.is_file():continue
            copied=dest/original.name
            if not copied.exists():shutil.copyfile(original,copied)
            if sha(copied)!=sha(original):raise ValueError('Adopted capture changed')
            hashes[str(copied.relative_to(target))]=sha(copied)
    shutil.copyfile(previous/'performance.json',target/'performance.json')
    save(target/'performance-adoption.json',{'from':str(previous),'inputs_sha256':sha(previous/'inputs.json'),
          'verified_all_rounds':audit['all_round_populations_equal'],'capture_hashes':hashes,'quality_reused':False})
    check_measurements(target)


def execute(args,recipe,out):
    source_spec=recipe.get('source');authoring=recipe.get('authoring_recipe')
    if bool(source_spec)==bool(authoring):raise ValueError('Declare exactly one source GLB or authoring recipe')
    if source_spec:
        original=Path(source_spec['glb']).resolve()
        if sha(original)!=source_spec['sha256']:raise ValueError('Reviewed master fingerprint mismatch')
        source_approved=source_spec.get('art_approved',False)
    else:
        brief=(args.recipe.resolve().parent/authoring).resolve()
        if not args.report_only:run([args.comfy_python,HERE/'pipeline.py',brief,'--out',out/'authoring','--comfy-url',args.comfy_url],out/'authoring.log')
        manifest=json.loads((out/'authoring/manifest.json').read_text());original=Path(manifest['asset'])
        if sha(original)!=manifest['sha256']:raise ValueError('Authoring output changed')
        source_approved=False
    variation=recipe.get('variation');variation_report=None
    if variation:
        check(original,recipe.get('source_triangle_budget',40000),recipe.get('height_m',8))
        if set(variation)-{'profile','seed','art_approved','approved_sha256'}:raise ValueError('Unknown structural variation field')
        variation_inputs={'master':sha(original),'variation':{'profile':variation['profile'],'seed':variation.get('seed',424242)},'script':sha(HERE/'variations.py')}
        variant=out/'variations'/key(variation_inputs)/'plant.glb'
        if not variant.exists():
            if args.report_only:raise ValueError('Structural variant has not been derived yet')
            derive(original,variant,variation['profile'],variation.get('seed',424242),recipe.get('source_triangle_budget',40000))
        variation_report=json.loads(variant.with_suffix('.variation.json').read_text())
        if variation_report['master_sha256']!=variation_inputs['master'] or variation_report['script_sha256']!=variation_inputs['script'] or variation_report['sha256']!=sha(variant):
            raise ValueError('Structural variation provenance mismatch')
        original=variant;source_approved=variant_approved(variation,variation_report['sha256'])
    digest=sha(original);source=out/'sources'/digest/'plant.glb';source.parent.mkdir(parents=True,exist_ok=True)
    if not source.exists():shutil.copyfile(original,source)
    if sha(source)!=digest:raise ValueError('Immutable master changed')
    save(source.parent/'provenance.json',{'original':str(original),'sha256':digest,'source_spec':source_spec,
                                        'structural_variation':variation_report,
                                        'authoring_manifest':str(out/'authoring/manifest.json') if authoring else None})
    source_audit=check(source,recipe.get('source_triangle_budget',40000),recipe.get('height_m',8))
    save(source.parent/'audit.json',source_audit)
    scripts={p.name:sha(p) for p in HERE.glob('*.py')}
    dependencies={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'tools/foliage/prepare_biomes.py',ROOT/'tools/foliage/bake.py',ROOT/'tools/foliage/volume_assets.py']}
    cook=recipe.get('cook',{});base=ROOT/'assets/foliage/game_biomes_v1'
    cook_inputs={'source':digest,'cook':{k:v for k,v in cook.items() if k!='adopt_catalogue'},
                 'scripts':{name:scripts[name] for name in ['native.py','lods.py','wood_lods.py','near_wood.py','roots.py','variations.py']},
                 'dependencies':dependencies,'baseline':catalogue_hashes(base)}
    cooked=out/'native'/key(cook_inputs)
    if not (cooked/'content.json').exists():
        adopted=cook.get('adopt_catalogue')
        if adopted:
            candidate=Path(adopted);info=json.loads((candidate/'native-report.json').read_text())
            if info['source_sha256']!=digest or info['cooker_sha256']!=cook_inputs['scripts']:raise ValueError('Adopted cook does not match the source and current cooker')
            if (info['tile']!=cook.get('tile',2048) or info['name']!=recipe['name']
                    or info.get('shrub_family')!=cook.get('shrub_family')):raise ValueError('Adopted cook settings mismatch')
        else:
            work=out/'cook-attempts';work.mkdir(exist_ok=True);candidate=work/f'{key(cook_inputs)}-{time.time_ns()}'
            command=[sys.executable,HERE/'native.py','--source',source,'--out',candidate,'--tile',str(cook.get('tile',2048)),
                     '--lods','--name',recipe['name'],'--blender',args.blender]
            if cook.get('shrub_family') is not None:command+=['--shrub-family',str(cook['shrub_family'])]
            run(command,out/'cook.log')
        assets(candidate)
        store_catalogue(candidate,cooked,out.parent/'_local3d-store')
        save(cooked/'inputs.json',cook_inputs)
    elif catalogue_hashes(cooked)!=json.loads((cooked/'content.json').read_text()):raise ValueError('Cooked catalogue changed')
    if json.loads((cooked/'inputs.json').read_text())!=cook_inputs:raise ValueError('Cook provenance changed')
    structural=assets(cooked)
    if structural['source_sha256']!=digest:raise ValueError('Cooked master identity changed')
    save(cooked/'asset-checks.json',structural)
    coverage_inputs={'mesh':structural['hashes']['mesh.bin'],'lods':structural['hashes']['lods.bin'],
                     'reviewer':scripts['review_lods_cpu.py'],'rasterizer':dependencies[str(Path('tools/foliage/bake.py'))]}
    coverage=out/'coverage'/key(coverage_inputs)
    if args.report_only and not (coverage/'coverage.json').exists():
        # Report refresh never starts even CPU renders; the full chain supplies these.
        coverage_report=None
    else:
        review_lod_coverage(cooked,coverage);coverage_report=str(coverage/'coverage.json')
    engine=ROOT/'x64/Release';binary={'exe':sha(engine/'MyPlanetEngine.exe'),'shaders':{p.name:sha(p) for p in engine.glob('*.cso')}}
    validation_inputs={'binary':binary,'assets':sha(cooked/'content.json'),'reviewer':scripts['review_native.py'],
                       'benchmark':sha(ROOT/'tools/banc_local3d.py'),'quality_helper':sha(ROOT/'tools/quality_local3d.py')}
    validation=out/'validation'/key(validation_inputs);validation.mkdir(parents=True,exist_ok=True)
    save(validation/'inputs.json',validation_inputs)
    measurements=validation/'measurements'
    command=[sys.executable,ROOT/'tools/banc_local3d.py','--catalogue',cooked,'--out',measurements,'--opportunistic','--quality']
    if not args.report_only:run(command+['--freeze-only'],validation/'freeze.log')
    if args.adopt_measurements and not (measurements/'performance.json').exists():
        if args.report_only:raise ValueError('Run the producer once before refreshing adopted evidence')
        adopt_performance(args.adopt_measurements.resolve(),measurements)
    exe=measurements/'frozen/bin/MyPlanetEngine.exe'
    functional_inputs={k:v for k,v in validation_inputs.items() if k in ['binary','assets','reviewer']}
    review=out/'reviews'/key(functional_inputs);review.mkdir(parents=True,exist_ok=True)
    save(review/'inputs.json',functional_inputs)
    if not (review/'native-review.json').exists():
        if args.report_only:raise ValueError('No completed native review for these inputs')
        run([sys.executable,HERE/'review_native.py','--catalogue',cooked,'--exe',exe,'--out',review],validation/'functional.log')
    gates={'reviewed_master':{'status':'pass' if source_approved else 'pending'},
           'native_assets':{'status':'pass','report':str(cooked/'asset-checks.json')},
           'native_functional':{'status':'pass','report':str(review/'native-review.json')},
           'native_art_review':{'status':'pending','views':str(review)},
           'performance':{'status':'pending'},'quality':{'status':'pending'}}
    save(out/'production-progress.json',{'status':'native checks complete; measurements in progress',
         'production_ready':False,'catalogue':str(cooked),'validation':str(validation),'review':str(review),
         'levels':structural['levels'],'gates':gates,'lod_coverage':coverage_report})
    if not args.report_only:run(command,validation/'measurements.log')
    visual=review/'visual-acceptance.json'
    if visual.exists():
        approval=json.loads(visual.read_text())
        if approval.get('inputs_sha256')==sha(review/'inputs.json'):
            gates['native_art_review']={'status':'pass' if approval.get('accepted') else 'fail','report':str(visual)}
    perf_file=measurements/'performance.json'
    if perf_file.exists():
        audit=check_measurements(measurements);save(measurements/'capture-audit.json',audit)
        perf=json.loads(perf_file.read_text());checks=[];target=1000/recipe.get('target_fps',60)
        for name,row in perf['views'].items():
            paired=row['candidate']['frame']['p95_ms']<=row['baseline']['frame']['p95_ms']*1.1
            budget=row['candidate']['frame']['p95_ms']<=target and row['candidate']['cadence_mean_ms']<=target
            checks.append({'view':name,'gpu_p95_ms':row['candidate']['frame']['p95_ms'],'budget_ms':target,
                           'cadence_mean_ms':row['candidate']['cadence_mean_ms'],
                           'paired_gpu_p95_delta_percent':(row['candidate']['frame']['p95_ms']/row['baseline']['frame']['p95_ms']-1)*100,
                           'baseline_also_misses_budget':row['baseline']['frame']['p95_ms']>target or row['baseline']['cadence_mean_ms']>target,
                           'paired_regression_pass':paired,'frame_budget_pass':budget,'pass':paired and budget})
        gates['performance']={'status':'pass' if all(c['pass'] for c in checks) else 'fail',
                              'paired_regression_pass':all(c['paired_regression_pass'] for c in checks),
                              'frame_budget_pass':all(c['frame_budget_pass'] for c in checks),'checks':checks,'report':str(perf_file),
                              'capture_audit':str(measurements/'capture-audit.json')}
    quality_file=measurements/'quality-guard.json'
    if quality_file.exists():
        guard=json.loads(quality_file.read_text())
        gates['quality']={'status':'pass' if guard['candidate_vs_canonical']['pass'] and guard['candidate_vs_current']['pass'] else 'fail',
                          'inherited_baseline_failure':not guard['baseline_vs_canonical']['pass'],'report':str(quality_file)}
    statuses=[g['status'] for g in gates.values()]
    status='failed acceptance' if 'fail' in statuses else 'pending acceptance' if 'pending' in statuses else 'production ready'
    report={'status':status,'production_ready':status=='production ready','recipe':str(args.recipe.resolve()),'source':str(source),
            'catalogue':str(cooked),'validation':str(validation),'levels':structural['levels'],'gates':gates,'lod_coverage':coverage_report,
            'scope':json.loads((cooked/'native-report.json').read_text())['scope'],
            'next':'Review native art, resolve failed gates and finish pending checks'}
    if recipe.get('preflight_quality'):
        prior_path=Path(recipe['preflight_quality']);prior=json.loads(prior_path.read_text())
        report['preflight_quality']={'report':str(prior_path),'candidate_vs_current_pass':prior['candidate_vs_current']['pass'],
                                    'note':'Preflight evidence is retained separately from the complete survey'}
    save(out/'production-report.json',report)
    lines=['# Vegetation production validation','', '**'+status+'**','']
    lines+=['- '+name+': **'+gate['status']+'**.' for name,gate in gates.items()]
    lines+=['','**Geometry**','','| LOD | Triangles | Exported vertices |','|---|---:|---:|']
    lines+=[f"| {row['level']} | {row['triangles']:,} | {row['vertices']:,} |" for row in structural['levels']]
    if perf_file.exists():
        lines+=['','**Paired performance, 1080p**','','GPU frame times; A/B/B/A, 256 samples per view and catalogue. Clouds and sea are enabled.','',
                '| View | Baseline median ms | Candidate median ms | GPU p95 change |','|---|---:|---:|---:|']
        for name,row in perf['views'].items():
            delta=(row['candidate']['frame']['p95_ms']/row['baseline']['frame']['p95_ms']-1)*100
            lines.append(f"| {name} | {row['baseline']['frame']['median_ms']:.2f} | {row['candidate']['frame']['median_ms']:.2f} | {delta:+.2f}% |")
        cost='passes' if gates['performance']['paired_regression_pass'] else 'fails'
        budget='passes' if gates['performance']['frame_budget_pass'] else 'fails'
        inherited=sum(row['baseline_also_misses_budget'] for row in gates['performance']['checks'])
        lines+=['',f"The relative cost gate {cost}. The declared {recipe.get('target_fps',60)} fps GPU/cadence budget {budget}. Baseline misses this budget in {inherited} of {len(perf['views'])} controls."]
    if recipe.get('preflight_quality'):
        verdict='passes' if prior['candidate_vs_current']['pass'] else 'fails'
        missing=len(prior['candidate_vs_canonical'].get('missing_material_heights',[]))
        lines+=['','**Quality preflight**','',f'The paired preflight guard {verdict}; {missing} canonical material/height pairs are missing. Its evidence remains recorded. The 30-site survey has its own verdict.']
    lines+=['','**Native review**','',
        f"- [Ground render]({(review/'automatic/near_natural.png').as_posix()}).",
        f"- [Material diagnostic]({(review/'automatic/near_plantalbedo.png').as_posix()}).",
        f"- [LOD diagnostic]({(review/'automatic/near_plantlod.png').as_posix()})."]
    if coverage_report:lines.append(f"- [CPU coverage sheet]({(coverage/'coverage.png').as_posix()}); unlit diagnostic, separate from native art acceptance.")
    lines+=['',report['scope']+'. Distinct variants require a combined-catalogue memory and quality check.',
            '',f'Catalogue: `{cooked}`.', '',f'Evidence: `{validation}`.']
    (out/'production-report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)
    return gates['performance']['status']=='pending' or gates['quality']['status']=='pending'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('recipe',type=Path);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--comfy-python',type=Path,default=Path('E:/ComfyUI/.venv/Scripts/python.exe'))
    parser.add_argument('--comfy-url',default='http://127.0.0.1:8188')
    parser.add_argument('--blender',type=Path,default=Path('C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'))
    parser.add_argument('--watch',action='store_true',help='Retry pending GPU blocks in the background')
    parser.add_argument('--report-only',action='store_true',help='Refresh the report from completed evidence; no inference or rendering')
    parser.add_argument('--adopt-measurements',type=Path,help='Reuse completed performance rounds after verifying identical frozen inputs; quality is rerun')
    parser.add_argument('--watch-minutes',type=float,default=120);args=parser.parse_args();out=args.out.resolve()
    if out.drive.lower()!='e:':raise ValueError('Production outputs belong on E:')
    out.mkdir(parents=True,exist_ok=True);recipe=json.loads(args.recipe.read_text(encoding='utf-8'))
    # The OS releases this lock after crashes; it never becomes a stale PID file.
    if args.report_only and args.watch:raise ValueError('Choose --report-only or --watch')
    with contextlib.nullcontext() if args.report_only else (out/'producer.lock').open('a+b') as lock:
        if os.name=='nt' and lock is not None:
            import msvcrt
            lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        deadline=time.monotonic()+args.watch_minutes*60
        while True:
            try:
                pending=execute(args,recipe,out)
                previous_error=out/'production-error.json'
                if previous_error.exists():
                    archive=out/'errors';archive.mkdir(exist_ok=True)
                    previous_error.rename(archive/(str(time.time_ns())+'.json'))
            except Exception as error:
                save(out/'production-error.json',{'status':'pipeline error','production_ready':False,'error':str(error),'time':time.time()})
                raise
            if not args.watch or not pending or time.monotonic()>=deadline:break
            time.sleep(30)
    report=json.loads((out/'production-report.json').read_text())
    if not report['production_ready']:raise SystemExit(2 if report['status']=='failed acceptance' else 3)


if __name__=='__main__':main()
