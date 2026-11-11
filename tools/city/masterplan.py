"""Ecological space and density precede buildings. No road/frontage subdivision.

The proposal board is a planning diagram, not a render or population forecast.
The same district centres and reserves drive the terrain-constrained placement.
"""
from pathlib import Path
import argparse
import json
import math
import random
import numpy as np


def rail_point(x):
    return np.array([x,32*math.sin(x/155)])


def rail_heading(x):
    return math.atan2(32/155*math.cos(x/155),1)


def braid_along(spine,extent,seed,fits=None,region=None):
    """The braid laid along a mobility spine that follows the site (a contour on a hill site): inhabited crowns
    on both sides of it, denser where both sides fill in its middle third; garden rows beyond; fields, workshops
    and the spaceport at the edges; protected habitat fingers across it. Stations at a sixth, a half and five
    sixths of its length. Every centre keeps inside the site; `fits(x, y, radius, role)`, when given, keeps a
    district off ground the terrain would refuse, so the edge districts move to their next free place."""
    from shapely.geometry import LineString,Point
    rng=random.Random(seed);line=LineString(spine);length=line.length;half=extent/2;districts=[]
    x0,y0,x1,y1=region or (-half,-half,half,half)  # the box the city keeps to inside a wider export
    def frame(s):
        a=line.interpolate(max(0,s-2));b=line.interpolate(min(length,s+2));p=line.interpolate(s)
        d=np.array([b.x-a.x,b.y-a.y]);d/=max(np.linalg.norm(d),1e-9);return np.array([p.x,p.y]),np.array([-d[1],d[0]])
    def add(s,offset,role,density,radius,label,overlap=1.0):
        """A district at arc length s, `offset` metres across the spine; False outside the site or on another.
        Crowns may overlap a quarter of their reach: the densest fabric runs on along the spine."""
        p,n=frame(s);x,y=p+n*offset+np.array([rng.uniform(-12,12),rng.uniform(-12,12)])
        if not (x0+radius+10<=x<=x1-radius-10 and y0+radius+10<=y<=y1-radius-10) or (fits and not fits(x,y,radius,role)):return False
        if any(math.dist((x,y),d['centre'])<(d['radius']+radius)*overlap+20*(overlap==1) for d in districts):return False
        districts.append({'centre':[round(float(x),3),round(float(y),3)],'role':role,'density':density,'radius':radius,
                          'label':label,'seed':rng.randrange(1,1000000)})
        return True
    stations=[[float(v) for v in frame(length*f)[0]] for f in (1/6,1/2,5/6)]
    # Fields, workshops and the spaceport first, at the edges, wherever the site has room for them.
    for f,role,radius,label in [(.12,'food',61,'Cultures partagées'),(.5,'food',66,'Serres et eau'),(.88,'food',61,'Vergers'),
                                (.3,'civic',61,'Savoirs et ateliers'),(.7,'civic',61,'Halles'),(.95,'arrival',66,'Accueil aérien')]:
        density=.22 if role=='food' else .7 if role=='civic' else .35
        offsets=(-600,600,-480,480,-360,360) if role=='food' else (600,-600,480,-480,360,-360)
        # Along the spine as well as across it: the first free place near its intended one.
        next((True for df in (0,-.08,.08,-.16,.16,-.24,.24) for offset in offsets
              if 0<f+df<1 and add(length*(f+df),offset,role,density,radius,label)),False)
    count=max(4,round(length/120))
    for k in range(count):
        s=length*(k+.5)/count;middle=abs(s/length-.5)<1/6
        if min(math.dist(frame(s)[0],q) for q in stations)<70:continue
        for side in ([-1,1] if middle else [1 if k%2 else -1]):
            add(s,side*rng.uniform(95,115),'core' if abs(s/length-.5)<.3 else 'mixed',1 if middle else .75,
                85 if middle else 72,f'Canopée {len(districts)+1}',overlap=.75)
    for row,offset in enumerate([-275,275,-430,430]):
        for k in range(max(3,round(length/200))):
            add(length*(k+.5+.5*(row%2))/max(3,round(length/200)),offset,'garden',.42,64,f'Jardin {len(districts)+1}')
    corridors=[]
    for f in (1/3,2/3):
        p,n=frame(length*f);t=np.array([n[1],-n[0]])
        corridors.append([[float(v) for v in p+n*u+t*23*math.sin(u/115+.8)] for u in np.linspace(-extent,extent,121)
                          if x0<=(p+n*u)[0]<=x1 and y0<=(p+n*u)[1]<=y1])
    return {'schema':2,'pattern':'braid_along','seed':seed,'extent_m':extent,'districts':districts,'stations':stations,
            'rail':[[float(x),float(y)] for x,y in spine],'habitat_corridors':corridors,'corridor_half_width_m':12,
            'rules':['Shared inhabited groups, no private plots','Density through stacked floors and wing variants, densest mid-spine',
                     'Permeable pedestrian connections; elevated shared transport on a level spine','Protected habitat fingers; no continuous ground road'],
            'stage':'planning proposal; exact footprints require terrain and access validation'}


def proposal(seed=11072026,pattern='braid',extent=1024,spine=None,fits=None,region=None):
    if spine is not None:return braid_along(spine,extent,seed,fits,region)
    rng=random.Random(seed);districts=[]
    def add(x,y,role,density,radius,label):
        districts.append({'centre':[round(x,3),round(y,3)],'role':role,'density':density,
                          'radius':radius,'label':label,'seed':rng.randrange(1,1000000)})
    stations=[rail_point(x).tolist() for x in [-300,0,300]]
    if pattern=='braid':
        # Staggered inhabited crowns on both banks of a planted mobility spine.
        # The negative space is a continuous habitat, not leftover cadastral land.
        for i,x in enumerate([-345,-180,-15,150,315]):
            for side in [-1,1]:
                xx=x+rng.uniform(-13,13);yy=side*(102+rng.uniform(-16,16))+rail_point(x)[1]
                add(xx,yy,'core' if i in [1,2,3] else 'mixed',1 if i in [1,2,3] else .7,72,f'Canopée {len(districts)+1}')
        for x,y in [(-395,275),(-205,285),(5,265),(205,290),(385,260),(-390,-285),(-170,-290),(60,-270),(285,-290)]:
            add(x+rng.uniform(-12,12),y+rng.uniform(-10,10),'garden',.42,64,f'Jardin {len(districts)-9}')
        add(-300,392,'food',.22,61,'Cultures partagées')
        add(190,400,'food',.22,66,'Serres et eau')
        add(380,390,'arrival',.35,66,'Accueil aérien')
        add(-15,-420,'civic',.7,61,'Savoirs et ateliers')
    elif pattern=='islands':
        for i,(x,y) in enumerate([(-320,0),(0,10),(310,0),(-285,290),(65,310),(-150,-300),(235,-270)]):
            add(x,y,'core' if i<3 else 'mixed',1 if i<3 else .65,105,f'Île habitée {i+1}')
            for a in [1.1,3.6,5.2]:add(x+math.cos(a)*95,y+math.sin(a)*95,'garden',.35,42,'Lisière')
    elif pattern=='delta':
        for branch,a in enumerate([.65,2.65,4.7]):
            for i,r in enumerate([85,225,370]):
                x=math.cos(a)*r;y=math.sin(a)*r
                add(x,y,'core' if i<2 else 'garden',1-.28*i,88,f'Branche {branch+1}.{i+1}')
                if i>0:add(x+math.cos(a+1.57)*95,y+math.sin(a+1.57)*95,'mixed',.6,60,'Terrasses')
    else:raise ValueError('Unknown masterplan')
    # Two protected, meandering habitat fingers divide the inhabited crowns.
    corridors=[]
    if pattern=='braid':
        for base in [-258,243]:
            corridors.append([[base+23*math.sin(y/115+.8),y] for y in np.linspace(-480,480,61)])
    return {'schema':2,'pattern':pattern,'seed':seed,'extent_m':1024,
            'districts':districts,'stations':stations,
            'rail':[[float(v) for v in rail_point(x)] for x in np.linspace(-455,455,183)],
            'habitat_corridors':corridors,'corridor_half_width_m':12,
            'rules':['Shared inhabited groups, no private plots','Density through stacked floors and wing variants',
                     'Permeable pedestrian connections; elevated shared transport','Protected habitat fingers; no continuous ground road'],
            'stage':'planning proposal; exact footprints require terrain and access validation'}


def board(out,seed=11072026):
    from PIL import Image,ImageDraw,ImageFont
    out.mkdir(parents=True,exist_ok=True)
    im=Image.new('RGB',(2100,1150),'#eeeadd');d=ImageDraw.Draw(im)
    def font(n,bold=False):return ImageFont.truetype('C:/Windows/Fonts/segoe'+('uib' if bold else 'ui')+'.ttf',n)
    d.text((55,32),'HABITER UNE CANOPÉE',font=font(39,True),fill='#173e39')
    d.text((55,87),'Trois compositions • plans de principe avant implantation • environ 1 km de côté',font=font(23),fill='#48675d')
    names=[('braid','01  ARCHIPEL TRESSÉ','Trois pôles reliés, des lisières ouvertes.','Base retenue pour la prochaine itération.'),
           ('islands','02  ÎLES HABITÉES','Des noyaux compacts et de grands vides.','Une ville fragmentée dans un paysage continu.'),
           ('delta','03  DELTA DE JARDINS','Des branches habitées autour des communs.','Une densité qui décroît vers les lisières.')]
    palette={'core':'#c87a40','mixed':'#d4a66c','garden':'#84a17c','food':'#b6bf77','arrival':'#7b9ca7','civic':'#be8a72'}
    for col,(key,title,line,desc) in enumerate(names):
        spec=proposal(seed,key);(out/(key+'.json')).write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        ox=55+col*690;oy=210;side=620;scale=side/1024
        def p(x,y):return (ox+(x+512)*scale,oy+(512-y)*scale)
        d.rounded_rectangle((ox,oy,ox+side,oy+side),radius=18,fill='#244d40')
        for corridor in spec['habitat_corridors']:d.line([p(*q) for q in corridor],fill='#487057',width=25)
        rr=random.Random(seed)
        for district in spec['districts']:
            x,y=district['centre'];r=district['radius'];xy=p(x,y);colour=palette[district['role']]
            d.ellipse((xy[0]-r*scale,xy[1]-r*scale,xy[0]+r*scale,xy[1]+r*scale),fill='#365c46',outline='#73926c',width=1)
            for k in range(round(6+district['density']*10)):
                a=k*2.399963;rho=r*(.32+.55*rr.random());cx,cy=p(x+rho*math.cos(a),y+rho*math.sin(a))
                w=6+district['density']*5;h=3+rr.random()*6
                d.rounded_rectangle((cx-w,cy-h,cx+w,cy+h),radius=3,fill=colour)
        d.line([p(*q) for q in spec['rail']],fill='#b7e2db',width=4)
        for station in spec['stations']:
            x,y=p(*station);d.ellipse((x-7,y-7,x+7,y+7),fill='#f0e6cd',outline='#193d37',width=2)
        d.text((ox,153),title,font=font(26,True),fill='#173e39')
        d.text((ox,850),line,font=font(21,True),fill='#173e39')
        d.text((ox,886),desc,font=font(18),fill='#48675d')
        d.line((ox,oy+side-25,ox+121,oy+side-25),fill='#eeeadd',width=3)
        d.text((ox+5,oy+side-53),'200 m',font=font(16),fill='#eeeadd')
    x=60
    for colour,label in [('#c87a40','Habitat dense'),('#d4a66c','Mixte'),('#84a17c','Lisières habitées'),('#b6bf77','Cultures'),('#b7e2db','Transport suspendu')]:
        d.rounded_rectangle((x,970,x+20,990),radius=4,fill=colour);d.text((x+30,964),label,font=font(21),fill='#173e39');x+=365
    d.text((60,1042),'Les surfaces vertes sont structurantes. Les chemins et les emprises seront calculés sur le relief du jeu.',font=font(23),fill='#48675d')
    im.save(out/'propositions.png')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();board(a.out)
