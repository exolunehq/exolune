"""Draw the actual supported footprints and access graph, not a beauty rendering."""
from pathlib import Path
import argparse
import json
import math
from collections import Counter
from PIL import Image,ImageDraw,ImageFont


def draw_plan(layout,out):
    im=Image.new('RGB',(1850,1450),'#eeeadd');d=ImageDraw.Draw(im)
    def font(n,bold=False):return ImageFont.truetype('C:/Windows/Fonts/segoe'+('uib' if bold else 'ui')+'.ttf',n)
    d.text((50,32),'ARCHIPEL TRESSÉ',font=font(40,True),fill='#173e39')
    d.text((50,89),'Implantation sur le relief d’Exolune • extérieurs, communs et transport suspendu',font=font(23),fill='#48675d')
    extent=layout['masterplan'].get('extent_m',1024);half=extent/2
    ox=50;oy=158;scale=1.15*1024/extent;side=extent*scale
    def point(x,y):return (ox+(x+half)*scale,oy+(half-y)*scale)
    d.rounded_rectangle((ox,oy,ox+side,oy+side),radius=18,fill='#214a3e')
    palette={'core':'#d39756','mixed':'#bc9b70','garden':'#a0ba82','food':'#c8c583','arrival':'#81adb5','civic':'#d39a87','transport':'#9fd3d0',
             'farm':'#c8c583','cliff_foot':'#d39756','cliff_top':'#a0ba82','cliff_face':'#a0ba82'}
    spec=layout['masterplan']
    for corridor in spec['habitat_corridors']:d.line([point(*v) for v in corridor],fill='#466f53',width=28)
    for hub in layout['districts']:
        x,y=point(*hub['centre']);r=hub['radius']*scale
        d.ellipse((x-r,y-r*.9,x+r,y+r*.9),outline='#4c6e54',width=1)
    for line in layout['road_lines']:d.line([point(*v) for v in line],fill='#a4ad87',width=3)
    for poly in layout['commons']:d.polygon([point(*v) for v in poly],fill='#b9b496')
    for poly in layout['access_paths']:d.polygon([point(*v) for v in poly],fill='#a4ad87')
    # Parcels follow their owners' order: the spaceport terminal, then every building on its own pad.
    buildings=[p for p in layout['instances'] if 'support_max' in p or p.get('foundation')=='spaceport platform']
    for p,poly in zip(buildings,layout['parcels']):
        colour=palette[p['zone']];d.polygon([point(*v) for v in poly],fill=colour,outline='#e9dcc0',width=1)
        if p.get('floors',1)>1:
            x,y=point(*p['position'][:2]);label=str(p['floors']);d.text((x-4,y-7),label,font=font(13,True),fill='#273e33')
    for p in layout['instances']:
        if p['zone'] in ['public','agriculture']:
            x,y=point(*p['position'][:2]);d.ellipse((x-2,y-2,x+2,y+2),fill='#cbd7b0')
    # Only built transport: the guideway on a level site, otherwise the cable car.
    if layout['transport']['length_m']:d.line([point(*v) for v in spec['rail']],fill='#aae4df',width=4)
    for line in layout.get('cables',[]):d.line([point(*v[:2]) for v in line],fill='#aae4df',width=2)
    for i,xy in enumerate(spec['stations']):
        x,y=point(*xy);d.ellipse((x-11,y-11,x+11,y+11),fill='#f2e8ce',outline='#80c5ba',width=3)
        d.text((x-30,y+17),'S'+str(i+1),font=font(19,True),fill='#eeeadd')
    x=1280;y=165
    for title,value in [('BÂTIMENTS',str(len(buildings))),('SECTEURS',str(len(layout['districts']))),
                        *([('STATIONS',str(layout['transport']['stations'])),('LIGNE SUSPENDUE',f"{layout['transport']['length_m']:.0f} m")]
                          if layout['transport']['length_m'] else
                          [('GARES',str((layout['transport'].get('cable_car') or {}).get('stations',0))),
                           ('TÉLÉPHÉRIQUE',f"{(layout['transport'].get('cable_car') or {}).get('length_m',0):.0f} m")])]:
        d.text((x,y),title,font=font(19,True),fill='#587265');d.text((x,y+26),value,font=font(40,True),fill='#173e39');y+=111
    y+=15
    for colour,label in [(palette['core'],'Collectif dense'),(palette['mixed'],'Habitat mixte'),(palette['garden'],'Lisières habitées'),
                         (palette['food'],'Serres et cultures'),(palette['civic'],'Savoirs et ateliers'),('#aae4df','Transport aérien'),('#466f53','Corridors naturels')]:
        d.rounded_rectangle((x,y,x+24,y+24),radius=4,fill=colour);d.text((x+38,y-3),label,font=font(22),fill='#173e39');y+=48
    y+=25
    for line in ['Les chiffres sur les bâtiments','indiquent les étages des variantes.','','Les empreintes et les accès sont','vérifiés sur le relief existant.','Aucune route automobile.','','Rames et cabines : statiques.','Art et performances : à valider.']:
        d.text((x,y),line,font=font(20),fill='#587265');y+=30
    d.line((75,oy+side-36,75+200*scale,oy+side-36),fill='#eeeadd',width=3)
    d.text((75,oy+side-65),'200 m',font=font(18),fill='#eeeadd')
    d.text((50,1370),'Plan d’implantation réel — les objets sont générés, les espaces naturels sont réservés avant placement.',font=font(22),fill='#48675d')
    out.parent.mkdir(parents=True,exist_ok=True);im.save(out)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--layout',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();draw_plan(json.loads(a.layout.read_text()),a.out)
