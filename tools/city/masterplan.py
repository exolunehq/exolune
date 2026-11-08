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


def proposal(seed=11072026,pattern='braid'):
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
