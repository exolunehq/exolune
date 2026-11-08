"""Preserve thin roof overlays after independent bounded LOD reductions.

The contract is local Z-up. Piecewise planar heights reach their worst clearance
at vertices of the projected triangle intersections; sparse rays can miss it.
Only distant representations receive a bounded outward compensation.
"""
import math
import numpy as np


def upward_triangles(raw):
    triangles=np.asarray(raw[:,:3],dtype='f8').reshape(-1,3,3)
    normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    keep=normals[:,2]>1e-9
    return triangles[keep],normals[keep]


def overlap(a,b):
    points=[p.copy() for p in a]
    for start,end in zip(b,np.roll(b,-1,axis=0)):
        edge=end-start;result=[]
        for p,q in zip(points,points[1:]+points[:1]):
            dp=edge[0]*(p[1]-start[1])-edge[1]*(p[0]-start[0])
            dq=edge[0]*(q[1]-start[1])-edge[1]*(q[0]-start[0])
            inside_p=dp>=-1e-10;inside_q=dq>=-1e-10
            if inside_p:result.append(p)
            if inside_p!=inside_q and abs(dp-dq)>1e-15:result.append(p+(q-p)*(dp/(dp-dq)))
        points=result
        if not points:break
    return points


def clearance(support,overlay):
    roof,normals=upward_triangles(support);panels,panel_normals=upward_triangles(overlay)
    if not len(roof) or not len(panels):raise ValueError('Roof contact has no projected surface')
    lower=roof[:,:,:2].min(1);upper=roof[:,:,:2].max(1)
    minimum=math.inf;pairs=0
    for panel,normal in zip(panels,panel_normals):
        lo=panel[:,:2].min(0);hi=panel[:,:2].max(0)
        possible=np.flatnonzero(((lower<=hi+1e-9)&(upper>=lo-1e-9)).all(1))
        for index in possible:
            poly=overlap(panel[:,:2],roof[index,:,:2])
            if not poly:continue
            points=np.asarray(poly);base=roof[index,0];rn=normals[index]
            rz=base[2]-((points-base[:2])*rn[:2]).sum(1)/rn[2]
            pz=panel[0,2]-((points-panel[0,:2])*normal[:2]).sum(1)/normal[2]
            minimum=min(minimum,float((pz-rz).min()));pairs+=1
    if not math.isfinite(minimum):raise ValueError('Overlay has no projected supporting roof')
    return minimum,pairs


def preserve(objects,parts,contracts,level,extent):
    reports=[]
    for contract in contracts:
        if contract['projection_axis']!='Z':raise ValueError('Unsupported contact projection')
        support=[part for obj,part in zip(objects,parts) if obj.get('city_part')==contract['support_role'] and part is not None]
        if not support:raise ValueError('Missing structural contact support')
        if not any(obj.get('city_part')==contract['overlay_role'] and part is not None for obj,part in zip(objects,parts)):
            raise ValueError('Missing structural contact overlay')
        base=np.concatenate(support)
        for obj,part in zip(objects,parts):
            if part is None or obj.get('city_part')!=contract['overlay_role']:continue
            before,pairs=clearance(base,part)
            move=max(0,contract['minimum_clearance_m']-before)
            threshold=[math.inf,520,260,115,42][level]
            bound=min(contract['maximum_compensation_m'],extent*contract['maximum_screen_error_px']/threshold)
            if move>bound+1e-5 or (level==0 and move>1e-6):raise ValueError('Surface contact exceeds the LOD screen-error contract: '+obj.name)
            if move:
                # Uniform translation preserves this closed part, its normals
                # and UVs. It adds no vertices and is never applied to LOD0.
                part[:,2]+=move+1e-5
            reports.append({'overlay':obj.name,'minimum_before_m':before,'minimum_after_m':before+move,
                            'outward_compensation_m':move,'maximum_compensation_m':bound,
                            'projected_triangle_pairs':pairs})
    return reports
