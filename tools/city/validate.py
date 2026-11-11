"""CPU invariants for the urban composition and native asset payloads; no benchmark."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import numpy as np
from layout import Terrain,build_plan,footprint
from grading import grade_point
from settlement import PYLON_BASE,SEAT_M
from shapely.geometry import Point,Polygon,LineString
from shapely.ops import unary_union


def validate(terrain,library,seed):
    report,surfaces,bits,grade=build_plan(terrain,library,seed)
    assert report['connected_pedestrian_network']
    lots=[Polygon(p) for p in report['parcels']]
    paths=[Polygon(p) for p in report['access_paths']]
    for i,lot in enumerate(lots):
        assert lot.is_valid and lot.area>0
        for j,other in enumerate(lots):
            if i!=j:assert lot.intersection(other).area<1e-7
    # An access leaves its own lot only: pylons and the spaceport terminal have none, so no index pairing.
    for path in paths:assert sum(lot.intersection(path).area>=1e-7 for lot in lots)<=1,'Access crosses another footprint'
    assert not report['policy']['vehicle_roads'] and not report['policy']['private_plots']
    assert report['policy']['path_width_m'][1]<=3
    collective=[p for p in report['instances'] if p['id'].startswith('ribbon_')]
    assert len(collective)>=25,'Dense shared habitat disappeared'
    assert len(report['parcels'])>=95,'City density collapsed'
    assert len({p['id'] for p in collective})>=6,'Structural variants disappeared'
    protected=unary_union([LineString(line).buffer(report['masterplan']['corridor_half_width_m']) for line in report['masterplan']['habitat_corridors']])
    # Parcels follow their owners' order; a pylon footing may cross a corridor, a building never does.
    owners=[p for p in report['instances'] if 'support_max' in p or p.get('foundation')=='spaceport platform']
    assert len(owners)==len(lots)
    assert all(owner.get('overhang') or not lot.intersects(protected) for owner,lot in zip(owners,lots)),'Building occupies a protected habitat corridor'
    # The guideway needs a level line: stations on it (three in the city, one where a branch passes the farms), or none
    # and no beam, ring or train. A cable car may serve either kind of site, never across the guideway.
    assert report['transport']['stations']==0 or report['transport']['stations']>=3
    if report['transport']['stations']==0:assert not any(p['id'] in ('canopy_guideway','viaduct_ring','panoramic_train') for p in report['instances'])
    # Every building stands on its own level earthwork: the engine's grading of the natural relief
    # (the same pads, in the same order) is flat under its whole footprint, at its ground datum.
    cells,flat=grade.index((-terrain.half,-terrain.half),terrain.half*2/32)
    graded=terrain.values;terrain.values=terrain.natural
    try:
        for instance in report['instances']:
            if 'pad' not in instance:continue
            pad=grade.pads[instance['pad']];assert abs(instance['position'][2]-pad[7]-SEAT_M)<1e-6
            if 'support_max' in instance:
                assert instance['foundation']=='earthwork'
                assert instance['support_max']-instance['support_min']<=report['policy']['steep_relief_m']
                assert instance['support_min']>=report['policy']['water_level_m']
                assert instance['access_length']<105
            lo,hi=library['models'][instance['model']]['bounds_z_up'];x,y,_=instance['position'];c,s=np.cos(instance['yaw']),np.sin(instance['yaw'])
            if instance.get('overhang'):lo,hi=PYLON_BASE  # a pylon's footing, under its crossarm
            for u in np.linspace(lo[0],hi[0],4):
                for v in np.linspace(lo[1],hi[1],4):
                    px,py=x+u*c-v*s,y+u*s+v*c
                    level=grade_point(grade.pads,px,py,terrain.sample(px,py),cells,flat,(-terrain.half,-terrain.half),terrain.half*2/32)
                    assert abs(level-pad[7])<2e-3,f"{instance['id']} not level on its earthwork: {level-pad[7]:+.3f} m"
        # Nothing floats: furniture on the ground stands no higher than its lowest graded ground plus its embedding,
        # sampled as the planner sampled it; on a court's paving it stands on the paving.
        origin,cell_=(-terrain.half,-terrain.half),terrain.half*2/32
        for instance in report['instances']:
            if instance['zone'] not in ('public','agriculture') or instance.get('elevated') or instance.get('seat')=='paving':continue
            model=library['models'][instance['model']];shape=footprint(model,*instance['position'][:2],instance['yaw'],0)
            x0,y0,x1,y1=shape.bounds
            points=[(px,py) for px in np.linspace(x0,x1,4) for py in np.linspace(y0,y1,4) if shape.covers(Point(px,py))]+list(shape.exterior.coords)
            low=min(grade_point(grade.pads,px,py,terrain.sample(px,py),cells,flat,origin,cell_) for px,py in points)
            base=instance['position'][2]+model['bounds_z_up'][0][2]
            assert base<=low+.03,f"{instance['id']} floats {base-low:+.2f} m above its ground at {instance['position'][:2]}"
    finally:
        terrain.values=graded
    for foundation in report['foundations']:assert foundation['kind']=='stair' and Polygon(foundation['outline']).is_valid
    for cable in report['transport']['cable_cars']:
        assert cable['min_clearance_m']>=report['policy']['cable_clearance_m'] and cable['stations']>=2
    # Earthworks stay local: none shows farther than its reach limit beyond its pad.
    assert report['earthworks']['largest_reach_m']<=report['earthworks']['reach_limit_m']+.5,'Earthworks reach too far'
    # Independent full instance collision check includes furniture and shelters.
    # Guidebeams, their bearings and cabins intentionally interlock in height.
    # Their supports occupy the reserved transit strip, not a building footprint.
    # A shuttle rests on its landing pad; a pylon's crossarm overhangs its reserved corridor.
    ground=[p for p in report['instances'] if not (p.get('elevated') or p.get('carried') or p.get('overhang'))]
    shapes=[footprint(library['models'][p['model']],*p['position'][:2],p['yaw'],.05) for p in ground]
    for i,shape in enumerate(shapes):
        for other in shapes[i+1:]:assert shape.intersection(other).area<1e-5
    for i,(shape,*_) in enumerate(surfaces):
        assert shape.is_valid
        for other,*_ in surfaces[i+1:]:assert shape.intersection(other).area<1e-6,'Overlapping path materials at a junction'
    return report,bits


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--terrain',type=Path,required=True)
    p.add_argument('--library',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--recipe',type=Path,default=Path(__file__).resolve().parents[2]/'assets/city/solarpunk.json')
    a=p.parse_args();terrain=Terrain(a.terrain);library=json.loads(a.library.read_text())
    recipe=json.loads(a.recipe.read_text(encoding='utf8'));budgets=recipe['source_geometry_budgets']
    small={'bench','lamp','fountain','planter','growing_bed','canopy','irrigation','cabinet','wayfinding','beacon','cable_cabin','sorting','insect_hotel'}
    geometry=[]
    for model in library['models']:
        limit=budgets['furniture_lod0_triangles' if model['kind'] in small else 'building_lod0_triangles']
        triangles=model['levels'][0]['triangles']
        assert triangles<=limit,f"{model['id']} exceeds its source geometry budget: {triangles}/{limit}"
        geometry.append({'id':model['id'],'triangles':triangles,'limit':limit})
        if recipe.get('detail_contract'):
            fittings=model.get('fittings',{})
            for name,roles in fittings.get('assemblies',{}).items():
                if 'door' in roles:assert set(roles).intersection({'handle','opening_control','opening_drive'}),f'Door without opening system: {model["id"]}/{name}'
            accessible={'house','ribbon_habitat','apartments','courtyard_habitat','civic','terminal','greenhouse','market','hangar','station'}
            if model['kind'] in accessible:
                assert fittings.get('primary_entries'),f'No physical entrance: {model["id"]}'
                assert fittings.get('approach_clear') is True,f'Obstructed or unaudited entrance approach: {model["id"]}'
                assert all(fittings['parts'].get(part,0)>0 for part in ['door','threshold']),f'Incomplete entrance: {model["id"]}'
                lo,hi=model['bounds_z_up'];entry=model['entrance_z_up']
                assert lo[0]-.5<=entry[0]<=hi[0]+.5 and lo[1]-.5<=entry[1]<=hi[1]+.5
    results=[]
    for seed in [11072026,17,33,2048]:
        report,bits=validate(terrain,library,seed)
        results.append({'seed':seed,'instances':len(report['instances']),'buildings':len(report['parcels']),
                        'built_surface_fraction':report['land_use']['built_surface_fraction']})
    left,lb=validate(terrain,library,11072026);right,rb=validate(terrain,library,11072026)
    assert left==right and np.array_equal(lb,rb),'Seeded output changed'
    invalid=copy.copy(terrain)
    # Sea everywhere, then a 60 % plane: steeper than any stair the planner may build.
    for values in [np.full_like(terrain.values,-1),np.broadcast_to(np.arange(terrain.side)*terrain.cell*.6+1000,terrain.values.shape)]:
        invalid.values=values
        try:build_plan(invalid,library,11072026)
        except ValueError:pass
        else:raise AssertionError('Unsupported water/steep site accepted')
    for model in library['models']:
        counts=[level['triangles'] for level in model['levels']]
        assert all(x>=y>0 for x,y in zip(counts,counts[1:]))
        for lod in model['levels']:
            if 'sampled_surface_p95_m' in lod:assert lod['sampled_surface_p95_m']<=lod['surface_p95_limit_m']
    a.out.write_text(json.dumps({'passed':True,'scope':'CPU structure, placement and source-relative LOD bounds',
        'performance_accepted':False,'seeds':results,'water_and_steep_sites_rejected':True,
        'geometry_budgets':geometry,'recipe_sha256':hashlib.sha256(a.recipe.read_bytes()).hexdigest(),
        'library_sha256':hashlib.sha256(a.library.read_bytes()).hexdigest(),
        'terrain_sha256':terrain.digest},indent=2)+'\n')
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
