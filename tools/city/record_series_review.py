"""Bind explicit visual judgements to every exact neutral-series capture."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--notes',type=Path,required=True)
    args=p.parse_args();series=json.loads((args.out/'series.json').read_text(encoding='utf-8'));notes=json.loads(args.notes.read_text(encoding='utf-8'));records=[]
    expected={a['id'] for a in series['assets']}
    if set(notes)!=expected:raise ValueError('Notes must cover exactly the delivered models')
    for asset in series['assets']:
        if sha(asset['master'])!=asset['master_sha256']:raise ValueError('Source changed after review: '+asset['id'])
        if set(notes[asset['id']])!=set(asset['views']):raise ValueError('Missing or extra view judgement: '+asset['id'])
        for name,view in asset['views'].items():
            note=notes[asset['id']][name]
            if not isinstance(note,str) or len(note.strip())<30:raise ValueError('Provide a concrete visual judgement')
            if sha(view['path'])!=view['sha256']:raise ValueError('Capture changed after inspection')
            records.append({'asset':asset['id'],'view':name,'source_sha256':asset['master_sha256'],'capture':view['path'],'capture_sha256':view['sha256'],'judgement':note})
    result={'stage':'Neutral source review','reviewer':'assistant visual inspection','capture_count':len(records),'judgements':records,
            'source_stage_inspected':True,'user_art_accepted':False,'production_art_accepted':False,'performance_accepted':False,
            'series_sha256':sha(args.out/'series.json'),'notes_sha256':sha(args.notes)}
    (args.out/'art-review.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Recorded',len(records),'image-bound judgements; production gates remain open.')


if __name__=='__main__':main()
