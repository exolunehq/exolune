"""Slim rigid glazing retainer: a chamfered strip and a separate narrow seal."""
import math
from mathutils import Vector


def construire(g):
    points, glass, Piece = g['TOUR_VERRE'], g['verre'], g['Piece']
    count = len(points)
    frames = []
    for k, p in enumerate(points):
        tangent = (points[(k+1)%count]-points[k-1]).normalized()
        n = min(glass.data.vertices, key=lambda v: (v.co-p).length_squared).normal.copy()
        n = (n-tangent*n.dot(tangent)).normalized()
        outward = tangent.cross(n).normalized()
        if outward.dot(g['dehors'](k)) < 0: outward = -outward
        frames.append((outward, n, tangent))
    pc = Piece('Verriere | cadre')
    def sweep(profile, material):
        rings = [[p+b*x+n*z for x,z in profile] for p,(b,n,_) in zip(points, frames)]
        g['loft'](pc, rings+[rings[0]], material, bouts=(False, False))
    # 34 mm wide, 12 mm thick. Flat faces carry the light, 2 mm chamfers
    # break the edge; the former 104 mm circular section is gone.
    sweep([(-.010,-.007),(.024,-.007),(.024,.003),(.022,.005),(-.008,.005),(-.010,.003)], g['BROSSE'])
    sweep([(-.014,-.004),(-.010,-.004),(-.010,.001),(-.014,.001)], g['CAOUTCHOUC'])
    distance = .18
    for k, p in enumerate(points):
        distance += (p-points[k-1]).length
        if distance < .18: continue
        distance = 0
        b,n,t = frames[k]; center = p+b*.007+n*.0052
        ring = [center+(b*math.cos(j*math.tau/8)+t*math.sin(j*math.tau/8))*.0024 for j in range(8)]
        pc.face(ring, g['BROSSE'], n=n)
        pc.face([center+b*x+t*y+n*.00015 for x,y in ((-.0016,-.00035),(.0016,-.00035),(.0016,.00035),(-.0016,.00035))], g['CAOUTCHOUC'], n=n)
    obj = pc.fin(25)
    obj['retainer_width_m'] = .034; obj['retainer_thickness_m'] = .012; obj['seal_width_m'] = .004
    return obj
