"""Checkpoint the official quality survey without changing its metrics or sites.

The material-balanced sites use banc_qualite.pick_sites unchanged. Selection
captures are cached losslessly so an interrupted heading search can be resumed.
Each subsequent site is a separate guarded invocation with --before.
"""
from pathlib import Path
import hashlib
import json
import os
import sys
from PIL import Image
import banc_qualite as quality
from banc_local3d import ROOT, GpuBusy, guarded, quality_delta, save, sha


def run_quality(out,exe,catalogues,environment,site_count=30):
    if site_count<6 or site_count%6:raise ValueError('Quality site count must be a positive multiple of six, at least six')
    root=out/'quality';root.mkdir(exist_ok=True)
    canonical=ROOT/'tools/banc_qualite_reference.json'
    protocol={'surveyor':sha(Path(quality.__file__)),'helper':sha(Path(__file__)),
              'canonical':sha(canonical),'inputs':sha(out/'inputs.json'),'sites':site_count,'seed':1,
              'resolution':[1280,720],'warmup':32,'samples':1}
    marker=root/'protocol.json'
    if marker.exists() and json.loads(marker.read_text())!=protocol:raise ValueError('Quality protocol changed; use a new measurement folder')
    save(marker,protocol)
    inputs=json.loads((out/'inputs.json').read_text())
    scans=Path(environment['MYPLANETENGINE_SCANS'])
    shared_protocol={k:v for k,v in protocol.items() if k!='inputs'}|{
        'executable':inputs['executable'],'shaders':inputs['shaders'],'shared_assets':inputs['shared_assets'],
        'baseline':inputs['catalogues']['baseline'],
        'ground_scans':{str(p.relative_to(scans)):sha(p) for p in scans.rglob('*') if p.is_file()}}
    cache_key=hashlib.sha256(json.dumps(shared_protocol,sort_keys=True).encode()).hexdigest()
    shared=Path('E:/ExoluneAssets/_local3d-quality-cache')/cache_key;shared.mkdir(parents=True,exist_ok=True)
    # One producer owns a shared cache at a time; Windows releases this on exit.
    lease=(shared/'cache.lock').open('a+b')
    if os.name=='nt':
        import msvcrt
        lease.seek(0);lease.write(b'0');lease.flush();lease.seek(0)
        try:msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            lease.close();save(out/'progress.json',{'status':'pending shared quality cache','cache':str(shared)})
            return False
    save(shared/'protocol.json',shared_protocol)
    save(root/'shared-baseline.json',{'cache':str(shared),'protocol':shared_protocol})
    base_env=environment|{'MYPLANETENGINE_RESOLUTION':'1280 720','MYPLANETENGINE_FOLIAGE_WARMUP':'32',
                         'MYPLANETENGINE_FOLIAGE_SAMPLES':'1'}|quality.ENGINE
    sites_file=shared/'sites.json'
    try:
        if not sites_file.exists():
            selection=shared/'selection';selection.mkdir(exist_ok=True)
            original_run=quality.run
            def checkpoint_run(executable,jobs,path,sun):
                # Preserve the official job ordering and site selection algorithm.
                for first in range(0,len(jobs),24):
                    group=jobs[first:first+24]
                    signature=hashlib.sha256(json.dumps([group,sun],sort_keys=True).encode()).hexdigest()
                    cache=selection/signature;cache.mkdir(exist_ok=True);done=cache/'complete.json'
                    if not done.exists():
                        job_file=cache/'jobs.txt';job_file.write_text('\n'.join(' '.join(map(str,j)) for j in group)+'\n')
                        env=base_env|{'MYPLANETENGINE_BATCH':str(job_file),'MYPLANETENGINE_SUN':sun,
                                     'MYPLANETENGINE_FOLIAGE_ASSETS':str(catalogues['baseline'])}
                        guarded([str(exe)],env,exe.parent,cache/'engine.log',exe,wait=False)
                        for i,job in enumerate(group):Image.open(job[0]).save(cache/f'{i}.png')
                        save(done,{'signature':signature,'images':{f'{i}.png':sha(cache/f'{i}.png') for i in range(len(group))}})
                    record=json.loads(done.read_text())
                    for i,job in enumerate(group):
                        image=cache/f'{i}.png'
                        if sha(image)!=record['images'][image.name]:raise ValueError('Selection cache changed')
                        Image.open(image).save(job[0])
            quality.run=checkpoint_run
            try:land=quality.pick_sites(str(exe),str(selection),site_count,1)
            finally:quality.run=original_run
            if len(land)!=site_count:raise ValueError('Quality selection did not return the requested material-balanced sites')
            save(sites_file,{'sites':[dict(zip(['lat','lon','heading','target'],row)) for row in land]})
        sites=json.loads(sites_file.read_text())['sites']
        save(root/'sites.json',{'sites':sites})
        reports={}
        for name,catalogue in catalogues.items():
            merged=[]
            for index,site in enumerate(sites):
                folder=(shared if name=='baseline' else root)/name/f'site_{index:02}';folder.mkdir(parents=True,exist_ok=True)
                done=folder/'complete.json'
                if done.exists():
                    record=json.loads(done.read_text());report_file=Path(record['report'])
                    if sha(report_file)!=record['sha256']:raise ValueError('Completed quality report changed')
                else:
                    # Keep incomplete attempts as evidence; never reuse their captures.
                    attempt=folder/f'attempt_{len(list(folder.glob("attempt_*"))):03}';attempt.mkdir()
                    single=attempt/'site.json';save(single,{'sites':[site]})
                    env=base_env|{'MYPLANETENGINE_FOLIAGE_ASSETS':str(catalogue)}
                    command=[sys.executable,'-u',str(ROOT/'tools/banc_qualite.py'),str(exe),str(attempt),
                             '--sites','1','--from-sites',str(single),'--batch-suns','--before',str(canonical)]
                    print('Quality:',name,index+1,'/',site_count,flush=True)
                    guarded(command,env,exe.parent,attempt/'survey.log',exe,wait=False)
                    report_file=attempt/'qualite.json'
                    save(done,{'report':str(report_file),'sha256':sha(report_file)})
                records=json.loads(report_file.read_text())['sites']
                if len(records)!=1 or len(records[0]['views'])!=len(quality.HEIGHTS):raise ValueError('Incomplete quality site')
                merged+=records
            summ=quality.summary(merged);reports[name]=summ
            save(root/(name+'.json'),{'sites':merged,'summary':summ})
            (root/(name+'.md')).write_text(quality.report(summ,json.loads(canonical.read_text())['summary'])+'\n',encoding='utf-8')
        reference=json.loads(canonical.read_text())['summary']
        save(out/'quality-guard.json',{'protocol':protocol,
             'baseline_vs_canonical':quality_delta(reference,reports['baseline']),
             'candidate_vs_canonical':quality_delta(reference,reports['candidate']),
             'candidate_vs_current':quality_delta(reports['baseline'],reports['candidate'])})
        return True
    except GpuBusy as error:
        save(out/'progress.json',{'status':'pending GPU availability','stage':'quality','reason':str(error)})
        print('Quality pending:',error,flush=True)
        return False
    finally:lease.close()
