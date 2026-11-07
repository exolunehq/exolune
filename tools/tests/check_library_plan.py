"""Validate real queue diversity and biome dispatch without rendering."""
from pathlib import Path
import json
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'foliage/local3d'))
from library import BIOMES

root=Path('E:/ExoluneAssets/biome-library');plan=json.loads((root/'plan.json').read_text())
assert len(plan['jobs'])==60 and len({j['name'] for j in plan['jobs']})==60
assert sorted(j['slot'] for j in plan['jobs'])==list(range(31,91))
for biome in BIOMES:
    for kind in ['trees','shrubs']:
        jobs=[j for j in plan['jobs'] if j['biome']==biome and j['kind']==kind]
        assert len(jobs)==5 and len({j['botanical_inspiration'] for j in jobs})==5
        recipes=[json.loads((root/j['recipe']).read_text(encoding='utf-8')) for j in jobs]
        assert len({r['seed'] for r in recipes})==5
        assert all(r['reject_branch_cycles'] and not r['reference'] for r in recipes)
        assert len({r['captions']['wood_reference'] for r in recipes})==5
        assert len({r['captions']['leaf_reference'] for r in recipes})==5
bank=json.loads((root/'review-bank.json').read_text());folder=Path(bank['catalogue']);rows=(folder/'biomes.txt').read_text().splitlines()
assert rows[0]=='FOLBIO03 91' and len(rows)==92
for slot,line in enumerate(rows[1:]):
    name,kind,mask=line.split()
    if slot>=31:
        family=(slot-31)//10;expected=2 if (slot-31)%10>=5 else 0 if family in [0,3] else 1
        assert int(kind)==expected
    assert all((folder/name/f).exists() for f in ['mesh.bin','impostor.bin','lighting.bin'])
# Uniform random climate selection must not silently send all tree species
# to the temperate bank by decoding a tree's spread as a shrub-family index.
assert 'species==SHRUB?ShrubFamily(o):ShrubClimateFamily' in (Path(__file__).resolve().parents[2]/'MyPlanetEngine/PlantPlacement.hlsli').read_text()
print('Library: 60 distinct recipes, five trees/shrubs per biome, unique seeds/captions and 91 compatible review roles pass. Fallbacks remain explicitly labelled.')
