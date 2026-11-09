"""Bind explicit visual judgements to the exact native capture protocols.

This records an inspection. It cannot infer artistic or performance acceptance
from successful rendering, pixel statistics, geometry counts or a prose note.
"""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--notes',type=Path,required=True)
    p.add_argument('--routes',default='native-review,native-details',help='Comma-separated functional capture directories')
    a=p.parse_args();notes=json.loads(a.notes.read_text(encoding='utf8'));routes=[]
    for directory in a.routes.split(','):
        if Path(directory).name!=directory:raise ValueError('Use capture-directory names within the production root')
        evidence=json.loads((a.out/directory/'functional.json').read_text())
        expected={c['name'] for c in evidence['captures']}
        if set(notes.get(directory,{}))!=expected:raise ValueError('Missing or stale view judgements: '+directory)
        records=[]
        for capture in evidence['captures']:
            name=capture['name'];note=notes[directory][name]
            if note.get('status') not in ['reviewable','open_issue','rejected']:raise ValueError('Explicit view status required: '+name)
            if not note.get('judgement'):raise ValueError('Explicit judgement required: '+name)
            image=a.out/directory/(name+'.bmp')
            digest=hashlib.sha256(image.read_bytes()).hexdigest()
            if digest!=capture['sha256']:raise ValueError('Capture changed since execution: '+name)
            records.append({'name':name,'path':str(image),'sha256':digest,**note})
        routes.append({'route':directory,'protocol':evidence['protocol'],'judgements':records})
    report={'schema':1,'scope':'Native exterior visual inspection, not an AAA or performance acceptance',
            'art_accepted':False,'performance_accepted':False,'routes':routes}
    (a.out/'art-review.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print('Recorded',sum(len(r['judgements']) for r in routes),'explicit native-view judgements')


if __name__=='__main__':main()
