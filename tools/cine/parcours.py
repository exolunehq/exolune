"""Parcours Exolune hors temps réel, NumPy seul. Voir docs/lancement.md."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hydro"))
import cp


def unit(p):
    return p / np.maximum(np.linalg.norm(p, axis=-1, keepdims=True), 1e-20)


def direction(ll):
    lat, lon = np.radians(np.asarray(ll).T[:2])
    return np.stack([np.cos(lat)*np.cos(lon), np.sin(lat), np.cos(lat)*np.sin(lon)], -1)


def latlon(p):
    p = unit(p)
    return np.degrees(np.stack([np.arcsin(np.clip(p[..., 1], -1, 1)), np.arctan2(p[..., 2], p[..., 0])], -1))


def basis(p):
    ll = np.radians(latlon(p)); la, lo = ll[..., 0], ll[..., 1]
    north = np.stack([-np.sin(la)*np.cos(lo), np.cos(la), -np.sin(la)*np.sin(lo)], -1)
    east = np.stack([-np.sin(lo), np.zeros_like(lo), np.cos(lo)], -1)
    return north, east


def ease(u):
    return u*u*u*(10+u*(-15+6*u))


# L'orbite et la montée sont exponentielles en hauteur au-dessus du sol de leur bout bas, plus ce décalage (m) : la
# vitesse décroît avec la hauteur jusqu'à celle d'une approche, sans freinage au raccord.
ORBIT_OFFSET = 300.0


def orbit_law(u, low, high, base):
    """Hauteur de u = 0 en `low` à u = 1 en `high` (altitudes), exponentielle au-dessus de `base`."""
    a, b = np.log(low-base+ORBIT_OFFSET), np.log(high-base+ORBIT_OFFSET)
    return base + np.exp((1-u)*a + u*b) - ORBIT_OFFSET


def orbit_share(alt, low, high, base):
    """Part du trajet horizontal, de 0 en `low` à 1 en `high` : elle suit la hauteur, (h+décalage)^0,6, pour que la
    pente s'adoucisse près du sol sans croisière horizontale jusqu'en bas."""
    f = lambda a: (np.asarray(a)-base+ORBIT_OFFSET)**0.6
    return np.clip((f(alt)-f(low))/(f(high)-f(low)), 0, 1)


def route(controls, u):
    """Points de passage répartis par longueur, sans freinage aux extrémités."""
    lengths = np.linalg.norm(np.diff(controls, axis=0), axis=1)
    keep = np.r_[True, lengths > 1e-12]
    controls = controls[keep]
    if len(controls) == 1:
        return np.broadcast_to(controls[0], (len(u), 3)).copy()
    knots = np.r_[0, np.cumsum(np.linalg.norm(np.diff(controls, axis=0), axis=1))]
    knots /= knots[-1]
    curve = Spline(knots, controls)
    # Inverser la longueur de la spline, plutôt que son paramètre : les points
    # rapprochés et les virages ne doivent pas commander la vitesse du vol.
    sample = np.unique(np.r_[np.linspace(0, 1, max(257, len(controls)*64)), knots])
    p = unit(curve(sample))
    distance = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
    return unit(curve(np.interp(u*distance[-1], distance, sample)))


class Spline:
    """Hermite quintique C2 ; dérivées communes aux nœuds, arrêts explicites."""
    def __init__(self, t, p, stops=(), velocity=None, acceleration=None):
        self.t = np.asarray(t)
        p = np.asarray(p, float)
        if p.ndim == 1:
            p = p[:, None]
        # Contrôle de forme par les points de Bézier quintiques : aucun retour en arrière
        # entre deux valeurs monotones, même au voisinage d'un arrêt très lent.
        slope = np.diff(p, axis=0)/np.diff(t)[:, None]
        v = np.vstack([slope[0], (slope[:-1]+slope[1:])/2, slope[-1]])
        same = slope[:-1]*slope[1:] > 0
        v[1:-1] = np.where(same, np.sign(v[1:-1])*np.minimum(np.abs(v[1:-1]),
                              1.25*np.minimum(np.abs(slope[:-1]),np.abs(slope[1:]))), 0)
        v[0] = np.sign(v[0])*np.minimum(np.abs(v[0]), 1.25*np.abs(slope[0]))
        v[-1] = np.sign(v[-1])*np.minimum(np.abs(v[-1]), 1.25*np.abs(slope[-1]))
        a = np.zeros_like(p)
        if velocity is not None:
            v = np.asarray(velocity, float).reshape(p.shape)
        if acceleration is not None:
            a = np.asarray(acceleration, float).reshape(p.shape)
        for i in stops:
            v[i] = a[i] = 0
        h = np.diff(t)[:, None]
        c0, c1, c2 = p[:-1], v[:-1]*h, a[:-1]*h*h/2
        d = p[1:] - c0 - c1 - c2
        e = v[1:]*h - c1 - 2*c2
        f = a[1:]*h*h - 2*c2
        self.c = np.stack([c0, c1, c2, 10*d-4*e+f/2, -15*d+7*e-f, 6*d-3*e+f/2])

    def __call__(self, t, derivative=0):
        t = np.asarray(t)
        i = np.clip(np.searchsorted(self.t, t, side="right")-1, 0, len(self.t)-2)
        h = self.t[i+1]-self.t[i]
        u = (t-self.t[i])/h
        out = np.zeros(t.shape + (self.c.shape[-1],))
        for k in range(5, derivative-1, -1):
            factor = np.prod(np.arange(k-derivative+1, k+1)) if derivative else 1
            out = out*u[..., None] + self.c[k, i]*factor
        return out / h[..., None]**derivative


class FlightPath:
    """Longueur parcourue à vitesse de croisière, raccords C2 et arrêts choisis.

    La sécurité précède le changement d'horloge : on conserve toute la courbe,
    y compris ses surélévations. Seule l'orbite conserve son horloge exponentielle.
    """
    def __init__(self, sample_t, evaluate, ranges, fps):
        self.evaluate = evaluate
        self.ranges = [(a/fps, b/fps, s) for a,b,s in ranges]
        pos, vel, acc = evaluate(sample_t)
        distance = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pos, axis=0), axis=1))]
        keep = np.r_[True, np.diff(distance) > 1e-8]
        speed = np.linalg.norm(vel, axis=1)
        moving = speed > 1e-7
        tangent = np.zeros_like(pos)
        curvature = np.zeros_like(pos)
        if moving.any():
            tangent[moving] = vel[moving]/speed[moving,None]
            curvature[moving] = (acc[moving]-tangent[moving]*np.sum(acc[moving]*tangent[moving],axis=1)[:,None])/speed[moving,None]**2
            for k in range(3):
                tangent[~moving,k] = np.interp(sample_t[~moving],sample_t[moving],tangent[moving,k])
        self.distance = distance
        self.keep = keep
        # Une pause seule n'a aucune longueur ; garder une courbe constante valide.
        if distance[-1] < 1e-8:
            self.curve = Spline([0.,1.], np.repeat(pos[:1],2,axis=0), [0,1])
        else:
            self.curve = Spline(distance[keep], pos[keep], velocity=tangent[keep], acceleration=curvature[keep])
        boundaries = np.array([self.ranges[0][0]]+[b for _,b,_ in self.ranges])
        self.edges = np.interp(boundaries, sample_t, distance)
        means = np.diff(self.edges)/np.diff(boundaries)
        speeds = np.r_[means[0],np.minimum(means[:-1],means[1:]),means[-1]]
        accelerations = np.zeros_like(speeds)
        for i,(a,b,s) in enumerate(self.ranges):
            if s['type'] in {'pause','decollage'}:
                speeds[i] = 0
            if s['type'] in {'pause','atterrissage'}:
                speeds[i+1] = 0
            if s['type'] in {'orbite','ascension'}:
                _,v,c = evaluate(np.array([a,b]))
                norm = np.linalg.norm(v,axis=1)
                speeds[i:i+2] = norm
                accelerations[i:i+2] = np.sum(v*c,axis=1)/np.maximum(norm,1e-20)
        self.clocks = []
        for i,(a,b,_) in enumerate(self.ranges):
            # Un quart du segment pour chaque raccord, croisière au milieu.
            # L'intégrale des rampes fixe la vitesse de croisière, sans rattrapage.
            ramp = (b-a)/4
            v0,v1 = speeds[i:i+2]; a0,a1 = accelerations[i:i+2]
            length = self.edges[i+1]-self.edges[i]
            cruise = (length-ramp*(v0+v1)/2-ramp*ramp*(a0-a1)/12)/(b-a-ramp)
            left = ramp*(v0+cruise)/2+ramp*ramp*a0/12
            right = ramp*(cruise+v1)/2-ramp*ramp*a1/12
            self.clocks.append(Spline([a,a+ramp,b-ramp,b],
                self.edges[i]+np.array([0,left,length-right,length]),
                velocity=[v0,cruise,cruise,v1], acceleration=[a0,0,0,a1]))

    def __call__(self, t):
        t = np.asarray(t)
        pos = np.empty((len(t),3)); vel = np.empty_like(pos); acc = np.empty_like(pos)
        for i,(a,b,s) in enumerate(self.ranges):
            mask = (t>=a)&((t<b) if i<len(self.ranges)-1 else (t<=b))
            if s['type'] in {'orbite','ascension'}:
                pos[mask],vel[mask],acc[mask] = self.evaluate(t[mask])
                continue
            clock = self.clocks[i]
            distance = clock(t[mask])[:,0]
            speed = clock(t[mask],1)
            acceleration = clock(t[mask],2)
            tangent = self.curve(distance,1)
            pos[mask] = self.curve(distance)
            vel[mask] = tangent*speed
            acc[mask] = self.curve(distance,2)*speed**2+tangent*acceleration
        return pos,vel,acc


def ground(p, cell=1.0):
    shape = p.shape[:-1]
    flat = unit(p.reshape(-1, 3))
    # Le portage alloue plusieurs tableaux par octave : borner la mémoire.
    return np.concatenate([cp.elevation(cp.Ctx(cell), flat[i:i+2048]) for i in range(0, len(flat), 2048)]).reshape(shape)


def corridor(p, width, spacing, cell):
    """Bande transversale ; les échantillons longitudinaux sont densifiés par generate."""
    p = unit(p)
    tangent = np.gradient(p, axis=0) if len(p)>1 else np.zeros_like(p)
    north, _ = basis(p)
    tangent = np.where(np.linalg.norm(tangent, axis=1)[:, None] > 1e-12, tangent, north)
    side = unit(np.cross(p, tangent))
    offsets = np.linspace(-width, width, max(3, int(np.ceil(2*width/spacing))+1))
    q = unit(p[:, None, :] + side[:, None, :]*offsets[None, :, None]/cp.R)
    return np.maximum(0, ground(q, cell)).max(axis=1)


def attitude(pos, fps, fallback=0, velocity=None):
    up = unit(pos); north, east = basis(up)
    vel = np.gradient(pos, 1/fps, axis=0, edge_order=2) if velocity is None else velocity
    horizontal = vel - up*np.sum(vel*up, axis=1)[:, None]
    speed = np.linalg.norm(horizontal, axis=1)
    cap = np.unwrap(np.arctan2(np.sum(horizontal*east, axis=1), np.sum(horizontal*north, axis=1)))
    moving = speed > 0.1
    if moving.any():
        cap = np.interp(np.arange(len(cap)), np.flatnonzero(moving), cap[moving])
    else:
        cap[:] = np.radians(fallback)
    pitch = np.arctan2(np.sum(vel*up, axis=1), speed)
    flying = np.linalg.norm(vel,axis=1) > 0.1
    if flying.any():
        pitch = np.interp(np.arange(len(pitch)), np.flatnonzero(flying), pitch[flying])
    else:
        pitch[:] = 0
    yaw_rate = np.gradient(cap, 1/fps)
    roll = np.arctan2(speed*yaw_rate, 9.81)
    return np.degrees(np.stack([cap, pitch, np.clip(roll, -0.65, 0.65)], -1)), vel


def generate(scenario):
    fps = int(scenario.get("fps", 60))
    if not 1 <= fps <= 240:
        raise ValueError("fps entre 1 et 240")
    cp.PLANET_SEED = int(scenario.get("graine", 0))
    if cp.PLANET_SEED != 0:
        raise ValueError("Le moteur de cette branche compile la graine 0 ; recaler le moteur avant une autre graine.")
    cell = float(scenario.get("cellule", 1.0))
    width = float(scenario.get("bande", 40))
    spacing = float(scenario.get("pas_sol", 10))
    margin = float(scenario.get("marge", 12))
    if min(cell, spacing, margin) <= 0 or width < 7:
        raise ValueError("cellule, pas_sol, marge positifs ; bande >= 7 m")
    start = scenario["depart"]
    current = direction(start[:2]); altitude = float(start[2])
    times, dirs, alts, stops = [0.0], [current], [altitude], []
    ranges = []
    frame = 0
    for seg in scenario["segments"]:
        kind = seg["type"]
        if kind not in {"orbite", "ascension", "approche", "atterrissage", "pause", "decollage", "rase-mottes", "mer"}:
            raise ValueError(f"Type inconnu : {kind}")
        n = round(float(seg["duree"])*fps)
        if n < 3 or abs(n/fps-float(seg["duree"])) > 1e-7:
            raise ValueError("Durée : au moins 3 images, multiple de 1/fps")
        # Nœuds à 4 Hz minimum ; les points de passage sont interpolés en C2.
        count = max(4, int(np.ceil(n/fps*4)))
        u = np.linspace(0, 1, count+1)
        waypoints = seg.get("points", [seg.get("point", latlon(current).tolist())])
        controls = unit(np.vstack([current, direction(waypoints)]))
        p = route(controls, u)
        if kind in {"pause", "decollage"}:
            stops.append(len(times)-1)
        if kind == "pause":
            p[:] = current; alt = np.full(len(u), altitude)
        elif kind == "orbite":
            base = max(0, float(ground(p[-1:])[0]))
            target = base + float(seg.get("hauteur", 150))
            if "altitude" in seg:
                target = float(seg["altitude"])
            if altitude <= target or target < base:
                raise ValueError("orbite : altitude de départ supérieure à l'arrivée, arrivée au-dessus du sol")
            # La descente exponentielle reste temporelle ; aucun arrêt en orbite.
            alt = orbit_law(1-u, target, altitude, base)
            p = route(controls, 1-orbit_share(alt, target, altitude, base))
        elif kind == "ascension":
            # La montée vers l'orbite : la même loi exponentielle, de bas en haut, jusqu'à `altitude`.
            target = float(seg["altitude"])
            base = max(0, float(ground(current[None])[0]))
            if altitude >= target or altitude < base:
                raise ValueError("ascension : altitude d'arrivée supérieure au départ, départ au-dessus du sol")
            alt = orbit_law(u, altitude, target, base)
            p = route(controls, orbit_share(alt, altitude, target, base))
        elif kind in {"rase-mottes", "mer"}:
            floor = ground(p, cell) if kind == "rase-mottes" else np.zeros(len(p))
            target = np.maximum(floor, 0) + float(seg.get("hauteur", 150 if kind == "rase-mottes" else 20))
            alt = target + (altitude-target[0])*(1-ease(u))
        else:
            target = max(0, float(ground(p[-1:], cell)[0])) + float(seg.get("hauteur", 4 if kind == "atterrissage" else 100))
            alt = altitude*(1-u) + target*u
        if np.min(alt) < 0:
            raise ValueError("Altitude négative")
        times.extend((frame/fps+u[1:]*n/fps).tolist()); dirs.extend(p[1:]); alts.extend(alt[1:])
        if kind in {"atterrissage", "pause"}:
            stops.append(len(times)-1)
        ranges.append((frame, frame+n, seg))
        frame += n; current = p[-1]; altitude = alt[-1]
    if frame < 4:
        raise ValueError("Parcours vide")
    ts = np.arange(frame)/fps
    ds = Spline(times, dirs, stops); hs = Spline(times, alts, stops)
    # Vérification entre images et entre nœuds : pas au sol <= pas_sol près du terrain.
    checks = [ts, np.asarray(times)]
    for a, b in zip(ts[:-1], ts[1:]):
        if min(hs(np.array([a,b]))[:, 0]) < cp.MAX_TERRAIN_HEIGHT+500:
            length = np.linalg.norm(ds(np.array([b]))-ds(np.array([a])))*cp.R
            subdivisions = max(2, int(np.ceil(length/spacing))+1)
            if subdivisions > 500000:
                raise ValueError("Trajet trop rapide près du sol")
            checks.append(np.linspace(a, b, subdivisions))
    check_t = np.unique(np.concatenate(checks))
    if len(check_t) > 500000:
        raise ValueError("Trajet trop rapide près du sol : > 500 000 échantillons")
    q = unit(ds(check_t)); floor = corridor(q, width, spacing, cell)
    base = hs(check_t)[:, 0]
    # Une surélévation C2, jamais inférieure au déficit du segment.
    lifts = []
    # Atterrissage autorisé à 4 m, garde coque 2,5 m ; marge locale demandée par le segment.
    required = np.full(len(check_t), margin)
    for a,b,s in ranges:
        mask = (check_t >= a/fps)&(check_t <= b/fps)
        local_margin = float(s.get("marge", margin))
        if local_margin <= 0:
            raise ValueError("marge de segment positive")
        if s["type"] in {"atterrissage", "pause"}:
            required[mask] = max(2.5,min(local_margin, float(s.get("hauteur", 4))))
        elif s["type"] in {"approche", "decollage"}:
            required[mask] = np.maximum(2.5,np.minimum(local_margin,base[mask]-floor[mask]))
        elif s["type"] == "mer":
            if float(s.get("hauteur", 20)) < 3:
                raise ValueError("mer : hauteur minimale de 3 m")
            required[mask] = 3
        elif s["type"] == "rase-mottes":
            required[mask] = max(local_margin,float(s.get("hauteur",150)))
        else:
            required[mask] = local_margin
    remaining = np.maximum(floor+required-base, 0)
    for i,(a,b,s) in enumerate(ranges):
        mask = (check_t >= a/fps)&((check_t < b/fps) if i<len(ranges)-1 else (check_t<=b/fps))
        if s["type"] == "mer" and np.max(floor[mask]) > 0:
            raise ValueError("Un segment mer traverse du terrain émergé ; déplacer ses points")
        lift = float(remaining[mask].max(initial=0))
        lifts.append(lift+2 if lift>0 else 0)
    # Une pause garde sa position : propager le niveau requis à ses deux bouts.
    for _ in ranges:
        old = lifts.copy()
        for i,(_,_,s) in enumerate(ranges):
            if s["type"] == "pause":
                lifts[i] = max(lifts[max(i-1,0):min(i+2,len(lifts))])
        if lifts == old: break
    boundaries = [lifts[0]] + [max(a,b) for a,b in zip(lifts[:-1],lifts[1:])] + [lifts[-1]]

    def correction(t, derivative=0):
        out = np.zeros_like(t, dtype=float)
        for i,(a,b,_) in enumerate(ranges):
            a /= fps; b /= fps
            mask = (t>=a)&((t<b) if i<len(ranges)-1 else (t<=b))
            ramp = min(0.5,(b-a)/3)
            x = np.clip((t[mask]-a)/ramp,0,1); y = np.clip((b-t[mask])/ramp,0,1)
            left = boundaries[i]-lifts[i]; right = boundaries[i+1]-lifts[i]
            if derivative == 2:
                out[mask] = (-left*60*x*(2*x*x-3*x+1)-right*60*y*(2*y*y-3*y+1))/ramp**2
            elif derivative == 1:
                out[mask] = (-left*30*x*x*(x-1)**2+right*30*y*y*(y-1)**2)/ramp
            else:
                out[mask] = lifts[i]+left*(1-ease(x))+right*(1-ease(y))
        return out

    def height(t):
        return hs(t)[:,0]+correction(t)

    safe = height(check_t)-floor
    if np.min(safe-required) < -1e-5:
        raise ValueError("Garde au sol insuffisante après lissage")
    def original(t):
        raw = ds(t); rate = ds(t,1); second = ds(t,2)
        norm = np.linalg.norm(raw,axis=1)[:,None]
        p = raw/norm; radial = np.sum(p*rate,axis=1)[:,None]
        dp = (rate-p*radial)/norm
        ddp = (second-p*np.sum(dp*rate+p*second,axis=1)[:,None]-2*dp*radial)/norm
        h = height(t)[:,None]
        dh = hs(t,1)+correction(t,1)[:,None]
        ddh = hs(t,2)+correction(t,2)[:,None]
        return p*(cp.R+h),dp*(cp.R+h)+p*dh,ddp*(cp.R+h)+2*dp*dh+p*ddh

    flight = FlightPath(check_t, original, ranges, fps)
    pos,velocity,_ = flight(ts)
    p = unit(pos); h = np.linalg.norm(pos,axis=1)-cp.R
    # Contrôler aussi l'interpolation en longueur, aux nœuds et à mi-distance.
    distance = flight.distance[flight.keep]
    arc_checks = np.unique(np.r_[distance,(distance[:-1]+distance[1:])/2])
    arc_pos = flight.curve(arc_checks)
    arc_safe = np.linalg.norm(arc_pos,axis=1)-cp.R-corridor(unit(arc_pos),width,spacing,cell)
    arc_required = np.interp(arc_checks,distance,required[flight.keep])
    for i,(_,_,s) in enumerate(ranges):
        if s['type'] in {'approche','decollage'}:
            # Leur garde variable a déjà été vérifiée sur la courbe source ;
            # le changement de paramètre doit conserver la garde de la coque.
            mask = (arc_checks>=flight.edges[i])&(arc_checks<=flight.edges[i+1])
            arc_required[mask] = 2.5
        elif s['type'] == 'rase-mottes':
            # Sa hauteur de croisière est vérifiée sur la courbe source ; la reparamétrisation garde la marge.
            mask = (arc_checks>=flight.edges[i])&(arc_checks<=flight.edges[i+1])
            arc_required[mask] = float(s.get("marge", margin))
    if np.min(arc_safe-arc_required) < -1e-4:
        i = np.argmin(arc_safe-arc_required)
        k = min(max(int(np.searchsorted(flight.edges, arc_checks[i]))-1, 0), len(ranges)-1)
        raise ValueError(f"Garde au sol insuffisante après réglage de la vitesse : {arc_safe[i]:.6f} < {arc_required[i]:.6f} à {arc_checks[i]:.6f} m, segment {k} ({ranges[k][2]['type']}), lat/lon {latlon(unit(arc_pos[i:i+1]))[0].round(5).tolist()}, altitude {np.linalg.norm(arc_pos[i])-cp.R:.1f} m")
    angles, velocity = attitude(pos, fps, scenario.get("cap", 0), velocity)
    # Le cap d'une tangente tend vers une limite aux arrêts ; filtrer ses petits
    # mouvements numériques et l'inclinaison, avant la spline d'assiette C2.
    radius = max(1, round(fps*0.4)); sigma = fps*0.16
    kernel = np.exp(-0.5*(np.arange(-radius,radius+1)/sigma)**2); kernel /= kernel.sum()
    angles = np.stack([np.convolve(np.pad(angles[:,k],radius,mode="edge"),kernel,mode="valid") for k in range(3)],axis=1)
    pause_nodes = []
    for a,b,s in ranges:
        if s["type"] != "pause": continue
        rest = angles[max(0,a-radius)].copy()
        before = max(0,a-radius); after = min(frame,b+radius)
        if a > before:
            w = ease(np.arange(a-before)/(a-before))[:,None]
            angles[before:a] = angles[before:a]*(1-w)+rest*w
        angles[a:b] = rest
        if after > b:
            w = ease(np.arange(after-b)/(after-b))[:,None]
            angles[b:after] = rest*(1-w)+angles[b:after]*w
        pause_nodes.extend([a,min(b,frame-1)])
    # Lissage C2 de l'assiette issue de la tangente ; dérouler le cap avant la spline.
    stride = max(1, fps//8); ids = np.unique(np.r_[np.arange(0, frame, stride), frame-1, pause_nodes]).astype(int)
    angles = Spline(ts[ids], angles[ids])(ts)
    nav = np.column_stack([latlon(p), h, angles])
    north, east = basis(p)
    heading = np.radians(angles[:,0]); forward = north*np.cos(heading[:,None])+east*np.sin(heading[:,None])
    camera = np.empty_like(pos); cam_dir = np.empty_like(pos)
    views = np.full(frame, "exterieur", dtype="U10"); fov = np.full(frame, 60.0)
    previous_spec = None

    def camera_pose(spec, sl):
        kind = spec.get("type", "poursuite")
        if kind == "pleine":
            # L'œil du pilote, le vaisseau caché (vue pleine du moteur) : au-dessus de sa pose de `hauteur`.
            return pos[sl] + p[sl]*float(spec.get("hauteur", 1.1))
        distance = float(spec.get("distance", 22)); high = float(spec.get("hauteur", 8))
        relative = np.radians(float(spec.get("cap_relatif", 90 if kind == "libre" else 180)))
        right = unit(np.cross(p[sl], forward[sl]))
        offset = distance*(forward[sl]*np.cos(relative)+right*np.sin(relative)) + p[sl]*high
        return pos[sl]+offset

    def camera_look(spec, sl, location):
        if spec.get("type") == "pleine":
            # Le regard suit le cap et le tangage du vaisseau, tourné de `cap_relatif` et `tangage` : un fondu entre
            # deux vues pleines tourne la tête en douceur. Jamais au-delà de ±88° : passé le nadir, le cap de la caméra
            # basculerait de 180° et l'image ferait un tonneau.
            yaw = np.radians(float(spec.get("cap_relatif", 0)))
            pitch = np.radians(np.clip(angles[sl,1] + float(spec.get("tangage", -4)), -88, 88))
            right = unit(np.cross(p[sl], forward[sl]))
            level = forward[sl]*np.cos(yaw) + right*np.sin(yaw)
            return unit(level*np.cos(pitch)[:,None] + p[sl]*np.sin(pitch)[:,None])
        if spec.get("regard") == "paysage":
            cap = np.radians(float(spec.get("cap",0))); pitch = np.radians(float(spec.get("tangage",0)))
            return (north[sl]*np.cos(cap)+east[sl]*np.sin(cap))*np.cos(pitch)+p[sl]*np.sin(pitch)
        return unit(pos[sl]-location)

    for a,b,s in ranges:
        spec = s.get("camera", {"type":"poursuite"})
        if isinstance(spec, str): spec = {"type": spec}
        if spec.get("type", "poursuite") not in {"cockpit", "poursuite", "libre", "pleine"}:
            raise ValueError("Caméra inconnue")
        sl = slice(a,b); camera[sl] = camera_pose(spec, sl)
        cam_dir[sl] = camera_look(spec, sl, camera[sl])
        fov[sl] = float(spec.get("fov", 60))
        if spec.get("type") == "pleine": views[sl] = "pleine"
        if spec.get("type") == "cockpit": views[sl] = "cockpit"
        elif previous_spec and previous_spec.get("type") != "cockpit":
            blend = max(float(spec.get("fondu", 1.0)), 1/fps)
            if blend > (b-a)/fps:
                raise ValueError("Le fondu doit finir avant le segment suivant")
            w = ease(np.clip(np.arange(b-a)/fps/blend,0,1))[:,None]
            old_pos = camera_pose(previous_spec, sl)
            camera[sl] = old_pos*(1-w)+camera[sl]*w
            old_look = camera_look(previous_spec, sl, camera[sl])
            new_look = camera_look(spec, sl, camera[sl])
            # Interpolation sphérique, y compris deux regards opposés.
            dot = np.clip(np.sum(old_look*new_look,axis=1),-1,1)
            angle = np.arccos(dot)[:,None]
            axis = unit(np.cross(old_look,new_look))
            opposite = dot < -0.999999
            if opposite.any():
                axis[opposite] = cp.tangent_basis(old_look[opposite])[0]
            cam_dir[sl] = unit(old_look*np.cos(angle*w)+np.cross(axis,old_look)*np.sin(angle*w)
                                    +axis*np.sum(axis*old_look,axis=1)[:,None]*(1-np.cos(angle*w)))
            old_fov = float(previous_spec.get("fov",60)); fov[sl] = old_fov*(1-w[:,0])+fov[sl]*w[:,0]
        previous_spec = spec
    # La position de caméra est C2 par construction (pose navire C2, mélange quintique).
    cam_up = unit(camera); cn, ce = basis(cam_up)
    cam_angles = np.degrees(np.stack([np.arctan2(np.sum(cam_dir*ce,axis=1),np.sum(cam_dir*cn,axis=1)),
                                    np.arcsin(np.clip(np.sum(cam_dir*cam_up,axis=1),-1,1)), np.zeros(frame)],-1))
    cam_alt = np.linalg.norm(camera,axis=1)-cp.R
    # Caméra propre : même vérification de bande et correction constante, donc C2.
    cf = corridor(cam_up, max(7,width/4), spacing, cell)
    exterior = views == "exterieur"
    camera_lift = max(0, float(np.max((cf+3-cam_alt)[exterior], initial=0)))
    if camera_lift:
        camera = cam_up*(cp.R+cam_alt[:,None]+camera_lift+2)
        cam_alt = np.linalg.norm(camera,axis=1)-cp.R
        # Conserver le regard paysage ; corriger seulement les vues visant le navire.
        for a,b,s in ranges:
            spec = s.get("camera", {})
            if not isinstance(spec,dict) or spec.get("regard") != "paysage":
                cam_dir[a:b] = unit(pos[a:b]-camera[a:b])
        cam_angles[:,0] = np.degrees(np.arctan2(np.sum(cam_dir*ce,axis=1),np.sum(cam_dir*cn,axis=1)))
        cam_angles[:,1] = np.degrees(np.arcsin(np.clip(np.sum(cam_dir*cam_up,axis=1),-1,1)))
    cam = np.column_stack([latlon(camera), cam_alt, cam_angles])
    weather = float(scenario.get("meteo",0))+ts*float(scenario.get("vitesse_meteo",1))
    if not np.isfinite(np.c_[nav,cam,fov,weather]).all() or np.min(weather)<0 or np.min(fov)<5 or np.max(fov)>150:
        raise ValueError("Pose, météo ou FOV invalide")
    summary = {"fps":fps,"images":frame,"duree":frame/fps,"graine":cp.PLANET_SEED,
               "bande_m":width,"pas_sol_m":spacing,"echantillons_sol":len(check_t),"camera_rehausse_m":camera_lift,"segments":[]}
    for i,(a,b,s) in enumerate(ranges):
        mask = (arc_checks>=flight.edges[i])&(arc_checks<=flight.edges[i+1])
        clearance = float(arc_safe[mask].min())
        if s['type'] in {'orbite','ascension','pause'}:
            # L'orbite conserve sa courbe temporelle ; une pause vérifie sa bande
            # immobile, sans emprunter la tangente du départ suivant.
            source_mask = (check_t>=a/fps)&(check_t<=b/fps)
            clearance = float(safe[source_mask].min())
        speed = np.linalg.norm(velocity[a:b],axis=1)
        # Inclure le raccord de fin, même si son image appartient au segment suivant.
        boundary_speed = np.linalg.norm(flight(np.array([b/fps]))[1],axis=1)
        summary["segments"].append({"type":s["type"],"images":[a,b-1],"garde_min_m":clearance,
                                    "vitesse_min_m_s":float(min(speed.min(),boundary_speed[0])),"vitesse_max_m_s":float(max(speed.max(),boundary_speed[0])),
                                    "vitesse_moy_m_s":float(speed.mean())})
    return fps, views, nav, cam, fov, weather, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path); parser.add_argument("sortie", type=Path)
    args = parser.parse_args()
    scenario = json.loads(args.scenario.read_text(encoding="utf-8-sig"))
    fps, views, nav, cam, fov, weather, summary = generate(scenario)
    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    with args.sortie.open("w", encoding="utf-8", newline="\n") as out:
        out.write("# Exolune : index vue navLat navLon navAlt navCap navTangage navRoulis camLat camLon camAlt camCap camTangage camRoulis fov meteo\n")
        out.write(f"fps {fps}\n")
        for i in range(len(views)):
            values = np.r_[nav[i],cam[i],fov[i],weather[i]]
            out.write(f"{i} {views[i]} "+" ".join(f"{x:.9f}" for x in values)+"\n")
    summary["sha256"] = hashlib.sha256(args.sortie.read_bytes()).hexdigest()
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    args.sortie.with_suffix(".resume.json").write_text(text+"\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
