"""Metric polygon tools for fascia outlines, recesses and control clearances."""
import math


def area(points):
    return .5*sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points, points[1:]+points[:1]))


def ccw(points):
    points = [tuple(p) for p in points]
    return points if area(points)>0 else points[::-1]


def offset(points, distance):
    """Positive distance insets an ordered polygon by a metric amount."""
    points = ccw(points); lines = []
    for a,b in zip(points, points[1:]+points[:1]):
        dx,dy = b[0]-a[0], b[1]-a[1]; length = math.hypot(dx,dy)
        dx,dy = dx/length,dy/length
        lines.append(((a[0]-dy*distance,a[1]+dx*distance),(dx,dy)))
    result = []
    for (a,u),(b,v) in zip(lines[-1:]+lines[:-1],lines):
        cross = u[0]*v[1]-u[1]*v[0]
        t = ((b[0]-a[0])*v[1]-(b[1]-a[1])*v[0])/cross if abs(cross)>1e-9 else 0
        result.append((a[0]+u[0]*t,a[1]+u[1]*t) if abs(cross)>1e-9 else b)
    return result


def chamfer(points, amount=.008):
    result = []
    for a,p,b in zip(points[-1:]+points[:-1],points,points[1:]+points[:1]):
        da,db=math.dist(a,p),math.dist(b,p)
        ua=((a[0]-p[0])/da,(a[1]-p[1])/da); ub=((b[0]-p[0])/db,(b[1]-p[1])/db)
        if ua[0]*ub[0]+ua[1]*ub[1] < -.995:
            result.append(p); continue
        d=min(amount,da*.25,db*.25)
        result.extend([(p[0]+ua[0]*d,p[1]+ua[1]*d),(p[0]+ub[0]*d,p[1]+ub[1]*d)])
    return result


def clearance(points, point):
    """Signed distance to an arbitrary simple panel outline."""
    x,y=point; inside=False; distance=math.inf
    for a,b in zip(points,points[1:]+points[:1]):
        dx,dy=b[0]-a[0],b[1]-a[1]
        t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)))
        distance=min(distance,math.hypot(x-a[0]-t*dx,y-a[1]-t*dy))
        if (a[1]>y)!=(b[1]>y) and x < a[0]+dx*(y-a[1])/dy: inside=not inside
    return distance if inside else -distance
