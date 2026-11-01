"""Modules d'équipement du cockpit : dimensions, commandes et place dans l'atlas.

Une seule source pour la sérigraphie (textures_cockpit.py) et la géométrie
(cockpit_chasseur.py) : chaque commande est posée là où sa légende est imprimée.
Coordonnées en mètres dans le plan du module : u vers la droite du lecteur,
v vers le haut des légendes. Sur les flancs, u va vers le nez à gauche du
pilote et vers l'arrière à sa droite ; sur les tablettes, v va vers le nez.
"""
ECHELLE = 1800   # pixels par mètre dans l'atlas
ATLAS = 4096
MARGE = 10
TEINTE = 'teinte'  # carré de peinture unie pour les chants des plaques

def _colonnes(us, nom, haut, bas):
    items = []
    for i, u in enumerate(us):
        items += [('tb', u, .175, ''), ('tog', u, .12, f'{nom} {haut[i]}'), ('tog', u, .055, bas[i])]
    return items

MODULES = {
    # Bandeau d'alarmes sous l'auvent.
    'alarme': ((.86, .05), None,
        [('push', .035, .031, 'ALARM', None)]
        + [('lamp', .10 + i*.0733, .032, l, 'amber' if l == 'ENG 2' else None)
           for i, l in enumerate(['FUEL', 'HYD', 'ELEC', 'ENG 1', 'ENG 2', 'ENG 3', 'RCS', 'O2', 'COMM', 'NAV'])]
        + [('push', .825, .031, 'CAUTION', 'amber')]),
    # Bande basse du pupitre, de part et d'autre du manche.
    'bas_g': ((.48, .12), None, [
        ('box', .015, .008, .175, .098, 'GEAR'),
        ('lamp', .045, .075, 'NOSE', 'cyan'), ('lamp', .095, .075, 'LEFT', 'cyan'), ('lamp', .145, .075, 'RIGHT', 'cyan'),
        ('gtog', .06, .028, 'ARM'), ('gtog', .13, .028, 'DOWN'),
        ('box', .19, .008, .37, .098, 'BRAKES'),
        ('tog', .225, .045, 'PARK'), ('tog', .28, .045, 'ANTISKID'), ('tog', .335, .045, 'STEER'),
        ('rot', .425, .045, 'FLOOD')]),
    'bas_d': ((.48, .12), None, [
        ('box', .015, .008, .17, .098, 'DISPLAY'),
        ('rot', .055, .045, 'MODE'), ('rot', .13, .045, 'SOURCE'),
        ('box', .185, .008, .395, .098, 'POWER'),
        ('tog', .215, .045, 'HUD'), ('tog', .265, .045, 'MFD 1'), ('tog', .315, .045, 'MFD 2'), ('tog', .365, .045, 'MFD 3'),
        ('push', .44, .072, 'TEST', None), ('push', .44, .03, 'ACK', 'cyan')]),
    # Ailes inclinées qui prolongent le pupitre le long des parois.
    'aile_g': ((.50, .17), None, [
        ('box', .02, .012, .19, .15, 'STANDBY'),
        ('tog', .055, .10, 'STBY'), ('tog', .105, .10, 'CAGE'), ('tog', .155, .10, 'BARO'),
        ('push', .065, .04, 'TEST', None), ('push', .145, .04, 'RESET', None),
        ('gauge', .260, .075, 'ATT', 'jauge_att'), ('gauge', .405, .075, 'ALT', 'jauge_alt'),
        ('rot', .340, .180, 'BRT')]),
    'aile_d': ((.50, .17), None, [
        ('gauge', .07, .075, 'THRUST', 'jauge_prop'),
        ('box', .135, .012, .275, .15, 'EVENT TIMER'),
        ('timer', .205, .10, ''), ('push', .17, .04, 'START', None), ('push', .24, .04, 'STOP', None),
        ('box', .29, .012, .48, .15, 'FLIGHT CTRL'),
        ('tog', .325, .10, 'RCS'), ('tog', .385, .10, 'TRIM'), ('tog', .445, .10, 'AUTO'),
        ('tog', .325, .04, 'MAN'), ('tog', .385, .04, 'DAMP'), ('tog', .445, .04, 'YAW')]),
    # Consoles latérales : panneau incliné sous le rail de verrière.
    'prop': ((.35, .24), 'PROPULSION',
        [('line', [(.06, .205), (.30, .205), (.30, .14)])]
        + [('line', [(u, .205), (u, .19)]) for u in (.06, .14, .22)]
        + _colonnes((.06, .14, .22), 'ENG', '123', ['IGN 1', 'IGN 2', 'IGN 3'])
        + [('rot', .30, .105, 'MODE'), ('gtog', .30, .035, 'ARM')]),
    'elec': ((.35, .24), 'ELECTRICAL',
        [('line', [(.06, .022), (.20, .022)])]
        + [('line', [(u, .022), (u, .033)]) for u in (.06, .13, .20)]
        + _colonnes((.06, .13, .20), 'BUS', 'ABC', ['TIE A', 'TIE B', 'TIE C'])
        + [('rot', .285, .14, 'SELECT'), ('push', .285, .055, 'RESET', None)]),
    'disj': ((.35, .24), 'CIRCUIT BREAKERS',
        [('cb', .035 + .035*i, v, f'{r}{i+1}') for r, v in zip('ABC', (.165, .105, .045)) for i in range(9)]),
    'env': ((.35, .24), 'ENVIRONMENT', [
        ('line', [(.06, .085), (.06, .11)]), ('line', [(.14, .085), (.14, .11)]),
        ('line', [(.06, .03), (.20, .03), (.20, .055)]),
        ('rot', .06, .14, 'TEMP'), ('rot', .14, .14, 'O2 FLOW'),
        ('tb', .06, .06, 'CABIN'), ('tb', .14, .06, 'SUIT'),
        ('tog', .21, .15, 'FAN 1'), ('tog', .26, .15, 'FAN 2'), ('tog', .31, .15, 'H2O'),
        ('tog', .21, .07, 'HEAT'), ('gtog', .29, .07, 'PURGE')]),
    # Tablettes horizontales à hauteur de coude.
    'gaz': ((.13, .40), 'THRUST', [
        ('slot', .085, .07, .085, .31), ('text', .085, .328, 'MAX'), ('text', .085, .052, 'IDLE')]
        + [('line', [(.068, v), (.074, v)]) for v in (.10, .16, .22, .28)]
        + [('tog', .033, .30, 'RCS'), ('tog', .033, .235, 'BOOST'), ('tog', .033, .17, 'GIMBAL'), ('gtog', .033, .09, 'ARM')]),
    'trim': ((.13, .28), 'TRIM', [
        ('rot', .065, .19, 'PITCH'), ('tog', .035, .085, 'PARK'), ('tog', .095, .085, 'AUTO'),
        ('push', .065, .035, 'DISC', 'amber')]),
    'clavier': ((.13, .40), 'KEYBOARD',
        [('key', .028 + .025*i, .06 + .03*j, '') for j in range(7) for i in range(4)]
        + [('push', .035, .295, 'CLEAR', None), ('push', .095, .295, 'ENTER', 'cyan'), ('lamp', .065, .345, 'EXEC', 'cyan')]),
    # Côtés du pupitre, au-dessus des consoles.
    'feux': ((.12, .17), 'LIGHTS', [
        ('tog', .03, .095, 'NAV'), ('tog', .06, .095, 'STRB'), ('tog', .09, .095, 'LAND'), ('rot', .06, .035, 'PANEL')]),
    'carbu': ((.12, .17), 'FUEL', [
        ('lamp', .035, .125, 'L', 'amber'), ('lamp', .085, .125, 'R', None),
        ('tog', .035, .07, 'PUMP L'), ('tog', .085, .07, 'PUMP R'), ('push', .06, .025, 'XFEED', None)]),
    'com': ((.13, .28), 'COMM', [
        ('rot', .04, .19, 'VOL'), ('rot', .095, .19, 'CHAN'),
        ('tog', .035, .085, 'XMIT'), ('tog', .095, .085, 'ICS'), ('lamp', .065, .035, 'LINK', 'cyan')]),
    'identite': ((.20, .035), None, [
        ('text', .10, .022, 'EXOLUNE  /  EX-01'), ('text', .10, .011, 'FLIGHT SYSTEMS   S/N 0047')]),
    'secours': ((.17, .075), 'RESCUE', [
        ('text', .085, .038, 'HARNESS RELEASE'), ('text', .085, .023, 'TURN / LIFT')]),
    'oxygene': ((.17, .075), 'LIFE SUPPORT', [
        ('text', .085, .038, 'O2  /  28 VDC'), ('text', .085, .023, 'SERVICE ACCESS')]),
    'immatriculation': ((.28, .095), None, [
        ('mark', .14, .058, 'EX-01'), ('text', .14, .021, 'EXOLUNE  /  SURVEY CRAFT')]),
}

def deplacer(items, du, dv):
    result=[]
    for item in items:
        kind=item[0]
        if kind=='line': result.append((kind,[(u+du,v+dv) for u,v in item[1]]))
        elif kind in ('box','slot'):
            result.append((kind,item[1]+du,item[2]+dv,item[3]+du,item[4]+dv,*item[5:]))
        else: result.append((kind,item[1]+du,item[2]+dv,*item[3:]))
    return result


# One fitted skin per console face. Functional sectors share its surface rather
# than repeating rectangular equipment trays inside a larger trapezoid.
MODULES['flanc_g'] = ((1.36,.28), None,
    deplacer(MODULES['elec'][2],.025,.018)+deplacer(MODULES['prop'][2],.405,.018)+deplacer(MODULES['aile_g'][2],.795,.045)+[
    ('sector',.025,.264,'01 / POWER'),('sector',.405,.264,'02 / PROPULSION'),('sector',.795,.264,'03 / INERTIAL'),
    ('text',1.05,.244,'ATTITUDE  /  ALTITUDE'),('trace',1.06,.027,'EX-01 / VECTOR BUS')])
MODULES['flanc_d'] = ((1.36,.28), None,
    deplacer(MODULES['aile_d'][2],.045,.045)+deplacer(MODULES['disj'][2],.585,.018)+deplacer(MODULES['env'][2],.975,.018)+[
    ('sector',.045,.264,'04 / FLIGHT'),('sector',.585,.264,'05 / CIRCUITS'),('sector',.975,.264,'06 / HABITAT'),
    ('text',.295,.244,'RCS  /  VECTOR CONTROL'),('trace',.295,.027,'EX-01 / FLIGHT BUS')])
old_gaz,old_keyboard = MODULES['gaz'][2],MODULES['clavier'][2]
MODULES['gaz'] = ((.16,1.30),None,
    deplacer(old_gaz,.015,.51)+deplacer(MODULES['trim'][2],.015,.08)+[
    ('sector',.018,1.245,'VECTOR'),('sector',.018,.935,'THRUST'),('sector',.018,.395,'TRIM'),
    ('rot',.045,1.14,'GAIN'),('rot',.115,1.14,'AXIS'),('tog',.045,1.055,'HOLD'),('gtog',.115,1.055,'DOCK'),
    ('trace',.08,.455,'A / 28 VDC')])
MODULES['clavier'] = ((.16,1.30),None,
    deplacer(old_keyboard,.015,.51)+deplacer(MODULES['com'][2],.015,.08)+[
    ('sector',.018,1.245,'NAV'),('sector',.018,.935,'INPUT'),('sector',.018,.395,'COMM'),
    ('rot',.045,1.14,'RANGE'),('rot',.115,1.14,'SCAN'),('push',.045,1.055,'MARK','cyan'),('tog',.115,1.055,'TRACK'),
    ('trace',.08,.455,'B / DATA LINK')])
MODULES['feux'] = ((.32,.21),'LIGHT / DOCK',[
    ('tog',.045,.125,'NAV'),('tog',.105,.125,'STRB'),('tog',.165,.125,'BEACON'),('tog',.225,.125,'DOCK'),
    ('rot',.045,.045,'PANEL'),('rot',.115,.045,'CABIN'),('push',.165,.045,'TEST','cyan'),
    ('trace',.16,.175,'EX / GUIDANCE')])
MODULES['carbu'] = ((.32,.21),'FEED / RCS',[
    ('lamp',.080,.135,'MAIN','amber'),('lamp',.160,.135,'AUX',None),('lamp',.240,.135,'RCS','cyan'),
    ('tog',.140,.06,'PUMP L'),('tog',.190,.06,'PUMP R'),('gtog',.240,.06,'CROSS'),('rot',.282,.06,'MODE'),
    ('trace',.16,.175,'EX / PROPULSION')])
def alarme_v(u): return .086-.060*(2*u/1.36-1)**2
MODULES['alarme'] = ((1.36,.11),None,[('push',.035,alarme_v(.035),'ALARM',None),('push',1.325,alarme_v(1.325),'CAUTION','amber')]+[
    ('lamp',.105+i*.096,alarme_v(.105+i*.096),label,'amber' if label=='ENG 2' else None)
    for i,label in enumerate(('FUEL','HYD','ELEC','ENG 1','ENG 2','ENG 3','RCS','O2','COMM','NAV','DOCK','CABIN','AIRLOCK'))])
for name in ('bas_g','bas_d','aile_g','aile_d','prop','elec','disj','env','trim','com'):
    del MODULES[name]

def atlas():
    """Deterministic nonrotating MaxRects packing, including the service plates.

    Reuse gaps below shorter panels instead of allocating full-height shelves.
    Preserve 1800 px/m labels; full-length console skins require a 4096px atlas.
    """
    sizes = [(n, round(w*ECHELLE), round(h*ECHELLE)) for n, ((w, h), _, _) in MODULES.items()]
    sizes.append((TEINTE, 32, 32))
    sizes.sort(key=lambda s: (-max(s[1:]), -s[1]*s[2], s[0]))
    rects = {}; free = [(MARGE, MARGE, ATLAS-MARGE, ATLAS-MARGE)]
    for n, w, h in sizes:
        candidates = [r for r in free if r[2]-r[0] >= w+MARGE and r[3]-r[1] >= h+MARGE]
        assert candidates, f'atlas too small for {n}'
        x, y, _, _ = min(candidates, key=lambda r: (min(r[2]-r[0]-w-MARGE, r[3]-r[1]-h-MARGE), r[1], r[0]))
        rects[n] = (x, y, x+w, y+h)
        right, bottom = x+w+MARGE, y+h+MARGE
        split = []
        for a, b, d, e in free:
            if right <= a or x >= d or bottom <= b or y >= e:
                split.append((a, b, d, e)); continue
            if a < x: split.append((a, b, x, e))
            if right < d: split.append((right, b, d, e))
            if b < y: split.append((a, b, d, y))
            if bottom < e: split.append((a, bottom, d, e))
        split = sorted(set(split))
        free = [r for r in split if not any(r != q and q[0] <= r[0] and q[1] <= r[1] and q[2] >= r[2] and q[3] >= r[3] for q in split)]
    return rects

if __name__ == '__main__':
    r = atlas()
    assert len(r) == len(MODULES) + 1
    for a in r.values():
        for b in r.values():
            if a is not b: assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], (a, b)
    print('atlas OK', max(v[3] for v in r.values()), 'px de haut')
