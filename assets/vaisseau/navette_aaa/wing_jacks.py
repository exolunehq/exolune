"""Double-ended telescopic actuators carried by the fore and aft webs of the wing bay."""
import numpy as np
from mathutils import Matrix

import anim
import gear
import meshkit

COL = "02_Exterieur_Appendices"


def axis(point, direction):
    """The local Z axis follows the ram. Both clevis pins stay parallel to local Y."""
    return gear.frame(point, direction, (direction[2], 0, -direction[0]))


def annular(profile, n=32):
    part = gear.lathe(profile, n)
    end = (len(profile)-1)*n
    faces = list(part.f) + [(end+j,end+(j+1)%n,(j+1)%n,j) for j in range(n)]
    return gear.Part(part.v,faces)


def lug(length, width, radius, bore):
    """A forged lug with a real pin bore and a tapered neck pointing along +Z."""
    angle = np.arange(40)*2*np.pi/40
    rays = np.column_stack((np.cos(angle),np.sin(angle)))
    support = np.maximum(radius, length*rays[:,1]+0.58*radius)
    reach = (support[None,:]/np.maximum(rays@rays.T,1e-9)).min(axis=1)
    b = 0.0008
    rings = []
    for y, r in ((-width/2,reach-b),(-width/2+b,reach),(width/2-b,reach),(width/2,reach-b),
                 (width/2,bore+b),(width/2-b,bore),(-width/2+b,bore),(-width/2,bore+b)):
        rings.append(np.column_stack((r*rays[:,0], np.full(len(rays),y), r*rays[:,1])))
    n=len(rays)
    faces=[(i*n+j,((i+1)%len(rings))*n+j,((i+1)%len(rings))*n+(j+1)%n,i*n+(j+1)%n)
           for i in range(len(rings)) for j in range(n)]
    return gear.Part(np.vstack(rings),faces)


def mount(g, point, foot):
    """Two bushed ears and their retained pin. The foot lands on the door or the end web."""
    direction=(foot-point)/np.linalg.norm(foot-point)
    transform=axis(point,direction)
    length=np.linalg.norm(foot-point)
    for y in (-0.0102,0.0102):
        g.add(lug(length,0.0050,0.0125,0.00625),"titanium",transform@gear.shift(y=y))
    spindle=gear.lathe([(0.0073,-0.0158),(0.0081,-0.0150),(0.0081,-0.0131),(0.0055,-0.0131),
                        (0.0055,0.0131),(0.0074,0.0131),(0.0074,0.0153),(0.0065,0.0161)],
                       24,caps=("grid","grid"))
    g.add(spindle,"titanium",gear.shift(*point)@gear.AXIS_Y)


def obj(name,g,mats):
    keys=list(dict.fromkeys(g.m))
    o=meshkit.mesh_object(name,np.vstack(g.v),g.f,COL,materials=[mats[k] for k in keys],
                          face_mats=[keys.index(k) for k in g.m])
    o.data.set_sharp_from_angle(angle=np.deg2rad(48))
    return o


def moving(name,g,mats,placement):
    o=obj(name,g,mats)
    rest=placement(0)
    o.matrix_world=Matrix(rest.tolist())
    inverse=np.linalg.inv(rest)
    anim.bake(o,"Ailes",lambda u: placement(u)@inverse)
    return o


def build(shoulder,web,mats,sign,side,upper,motion):
    """Return the bonded feet for the main door and bay after rigging their hydraulic rams."""
    mats = gear.gear_materials(mats)
    door_fit, web_fit = gear.Geo(),gear.Geo()
    face="Haut" if upper else "Bas"
    for label,d,end in (("Avant",1,0),("Arriere",-1,-1)):
        station = shoulder.a[end] + d*0.48
        centre_z = shoulder.centre_z
        rim = shoulder.row_z(station,shoulder.top if upper else shoulder.bottom)
        z = centre_z + (rim-centre_z)*(0.41 if upper else 0.42)
        skin,normal=shoulder.skin(station,z)
        normal=normal*np.array((sign,1,1))
        skin=skin*np.array((sign,1,1))
        # The pivot axis is straight in Y even where the two jambs taper in plan.
        outward=np.array((normal[0],0,normal[2]))
        outward/=np.linalg.norm(outward)
        Q=skin-0.034*np.array((sign,0,0))
        P=Q+np.array((-sign*0.405,0,0.045 if upper else 0.125))
        foot=skin-0.004*outward
        mount(door_fit,Q,foot)
        pad=gear.lathe([(0.012,-0.007),(0.016,-0.004),(0.017,-0.0012)],24,caps=("grid","grid"))
        door_fit.add(pad,"cast",axis(skin,outward))
        heel=P+np.array((-sign*0.027,0,0))
        mount(web_fit,P,heel)
        landing=web.ray_cast(heel,(0,-d,0),0.20)[0]
        if landing is None:
            raise ValueError(f"{face} {label}: missing bulkhead under the fixed pivot")
        wall_y=landing.y-d*0.0015
        # One end of the cross-boss is cast into the fore or aft bulkhead.
        extent=abs(heel[1]-wall_y)+0.016
        pedestal=gear.lathe([(0.0195,0),(0.0195,0.006),(0.012,0.013),
                             (0.012,extent-0.002),(0.010,extent)],24,caps=("grid","grid"))
        web_fit.add(pedestal,"ti",gear.frame((heel[0],wall_y,heel[2]),(0,d,0)))
        span=np.linalg.norm(Q-P)
        nose=span-0.040
        barrel=gear.Geo().add(lug(0.030,0.012,0.0145,0.00645),"titanium")
        barrel.add(annular([(0.011,0.020),(0.0145,0.027),(0.0145,0.039),(0.0128,0.042),
                            (0.0128,nose-0.019),(0.0140,nose-0.016),(0.0140,nose-0.004),
                            (0.0120,nose),(0.0076,nose),(0.0076,0.032),(0.008,0.020)]),"ti")
        barrel.add(annular([(0.0142,nose-0.016),(0.0144,nose-0.015),(0.0144,nose-0.007),
                            (0.0141,nose-0.006),(0.0139,nose-0.006),(0.0139,nose-0.016)]),"cast")
        rod=gear.Geo().add(lug(0.022,0.012,0.0135,0.00645),"titanium",gear.frame((0,0,0),(0,0,-1)))
        rod.add(gear.lathe([(0.0062,-span+0.044),(0.0067,-span+0.045),(0.0067,-0.031),
                            (0.009,-0.028),(0.009,-0.018),(0.007,-0.015)],24,caps=("grid","grid")),"chrome")
        def placement(u,rod_end,P=P,Q=Q):
            head=Q+motion(u)[:3,3]
            return axis(head if rod_end else P,head-P)
        suffix=f"_{face}_{label}_{side}"
        moving("Aile_Verin"+suffix,barrel,mats,lambda u: placement(u,False))
        moving("Aile_Tige"+suffix,rod,mats,lambda u: placement(u,True))
    return obj("Pieds_Trappe_"+face+"_"+side,door_fit,mats),obj("Paliers_Fixes_"+face+"_"+side,web_fit,mats)
