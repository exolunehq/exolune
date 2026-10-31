"""Dessine les interfaces statiques des trois écrans du cockpit."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math
ROOT=Path(__file__).resolve().parent
FONT='C:/Windows/Fonts/consola.ttf'
FONT_BOLD='C:/Windows/Fonts/consolab.ttf'
def font(n,bold=False): return ImageFont.truetype(FONT_BOLD if bold else FONT,n)
W=512; H=512
bg=(6,16,22); line=(24,74,83); text=(159,218,221); cyan=(51,208,218); amber=(246,171,69)
def setup(title, subtitle):
    im=Image.new('RGB',(W,H),bg); d=ImageDraw.Draw(im)
    for x in range(16,W,32): d.line((x,44,x,H-36),fill=(10,30,36))
    for y in range(48,H-36,32): d.line((16,y,W-16,y),fill=(10,30,36))
    d.rectangle((8,8,W-9,H-9),outline=(49,121,130),width=2)
    d.rectangle((16,17,496,40),fill=(12,40,47))
    d.text((23,20),title,font=font(16,True),fill=cyan)
    d.text((24,466),subtitle,font=font(12),fill=text)
    d.text((419,20),'SYS OK',font=font(12,True),fill=cyan)
    return im,d
def tick(d,center,r,ang,length,color=line,width=2):
    x,y=center; a=math.radians(ang)
    d.line((x+math.sin(a)*(r-length),y-math.cos(a)*(r-length),x+math.sin(a)*r,y-math.cos(a)*r),fill=color,width=width)

im,d=setup('FLIGHT / ATTITUDE','AFT CTRL   |   AUTO TRIM   |   04:18:22')
d.ellipse((88,78,424,414),outline=line,width=3); d.ellipse((112,102,400,390),outline=cyan,width=2)
for i in range(0,360,10): tick(d,(256,246),159,i,12 if i%30==0 else 5,cyan if i%30==0 else line)
d.line((119,246,220,246),fill=cyan,width=3); d.line((292,246,393,246),fill=cyan,width=3)
d.line((224,246,242,246,256,260,270,246,288,246),fill=amber,width=4)
for n,dy in [(-10,-58),(-5,-29),(5,29),(10,58)]:
    d.line((224,246+dy,288,246+dy),fill=text,width=2); d.text((295,238+dy),str(n),font=font(12),fill=text)
d.text((22,95),'SPD',font=font(13),fill=text); d.text((18,115),'248',font=font(24,True),fill=cyan)
d.text((422,95),'ALT',font=font(13),fill=text); d.text((421,115),'1.62',font=font(20,True),fill=cyan)
d.text((222,423),'HDG  274',font=font(15,True),fill=amber)
im.save(ROOT/'ecran_vol.png')

im,d=setup('NAV / TERRAIN','MAP 1:240K    |    SURFACE TRACK')
for offset in range(7):
    pts=[]
    for x in range(22,490,4):
        y=95+offset*48+19*math.sin(x*.015+offset*.8)+8*math.sin(x*.038+offset)
        pts.append((x,y))
    d.line(pts,fill=(24,95,93),width=2)
d.line((35,358,110,325,168,335,229,282,287,252,354,204,469,149),fill=cyan,width=3)
d.polygon([(246,256),(238,278),(256,271)],fill=amber)
for x,y,l in [(111,325,'WP 02'),(354,204,'WP 03'),(469,149,'DEST')]:
    d.ellipse((x-4,y-4,x+4,y+4),fill=cyan); d.text((x+8,y-15),l,font=font(12),fill=text)
d.text((30,400),'LAT  42.183 N',font=font(16),fill=text)
d.text((30,425),'LON  08.442 E',font=font(16),fill=text)
im.save(ROOT/'ecran_nav.png')

im,d=setup('SHIP / SYSTEMS','POWER DISTRIBUTION    |    NOMINAL')
for j,(label,value) in enumerate([('REACTOR',.82),('THRUST',.64),('SHIELDS',.91),('LIFE SUP',.76),('THERMAL',.49)]):
    y=76+j*62; d.text((28,y),label,font=font(16,True),fill=text)
    d.rectangle((180,y+2,462,y+16),outline=line,width=2)
    d.rectangle((184,y+6,184+int(270*value),y+12),fill=cyan if value>.55 else amber)
    d.text((398,y+21),f'{int(value*100):02d} %',font=font(13),fill=text)
d.rectangle((28,397,482,442),outline=line,width=2)
d.text((42,406),'CORE  98.4%   /   TEMP  614 K',font=font(16),fill=cyan)
im.save(ROOT/'ecran_systemes.png')

# Sérigraphie des modules dans un seul atlas : les commandes sont modélisées
# aux mêmes coordonnées (modules_cockpit.py), l'image ne porte que peinture et légendes.
from modules_cockpit import MODULES, ECHELLE as K, ATLAS, atlas
PEINTURE=(146,151,153); BLANC=(238,238,232); ARETE=(86,90,92); FENTE=(24,27,28)
im=Image.new('RGB',(ATLAS,ATLAS),PEINTURE); d=ImageDraw.Draw(im)
small=font(round(.0052*K),True); tiny=font(round(.0042*K),True); head=font(round(.0075*K),True)
for name,((w,h),title,items) in MODULES.items():
    x0,y0,x1,y1=atlas()[name]
    def px(u,v): return (x0+u*K, y1-v*K)
    d.rectangle((x0,y0,x1-1,y1-1),outline=ARETE,width=3)
    for u in (.008,w-.008):
        for v in (.008,h-.008):
            x,y=px(u,v); r=.0058*K; d.ellipse((x-r,y-r,x+r,y+r),fill=ARETE)
    if title:
        d.text(px(.016,h-.007),title,font=head,fill=BLANC,anchor='lt')
        x,y=px(.016,h-.017); d.line((x,y,x1-.016*K,y),fill=BLANC,width=2)
    for it in items:
        kind=it[0]
        if kind=='line': d.line([px(u,v) for u,v in it[1]],fill=BLANC,width=3); continue
        if kind=='box':
            _,u0,v0,u1,v1,label=it; d.rectangle((*px(u0,v1),*px(u1,v0)),outline=BLANC,width=2)
            box=d.textbbox(px(u0+.008,v1),label,font=small,anchor='lm')
            d.rectangle((box[0]-4,box[1],box[2]+4,box[3]),fill=PEINTURE); d.text(px(u0+.008,v1),label,font=small,fill=BLANC,anchor='lm'); continue
        if kind=='slot':
            _,u0,v0,u1,v1=it; a=px(u0-.006,v1); b=px(u1+.006,v0)
            d.rounded_rectangle((*a,*b),radius=.006*K,fill=FENTE,outline=ARETE,width=2); continue
        _,u,v,label,*opt=it
        if kind=='text': d.text(px(u,v),label,font=small,fill=BLANC,anchor='mm')
        elif kind in ('tog','gtog'): d.text(px(u,v+.016),label,font=small,fill=BLANC,anchor='mb')
        elif kind=='rot':
            x,y=px(u,v)
            for a in range(-135,136,45):
                t=math.radians(a); d.line((x+math.sin(t)*.016*K,y-math.cos(t)*.016*K,x+math.sin(t)*.0195*K,y-math.cos(t)*.0195*K),fill=BLANC,width=2)
            d.text(px(u,v+.025),label,font=small,fill=BLANC,anchor='mb')
        elif kind in ('push','lamp','tb'): d.text(px(u,v-(.0135 if kind=='push' else .0105)),label,font=small,fill=BLANC,anchor='mt')
        elif kind=='cb': d.text(px(u,v-.009),label,font=tiny,fill=BLANC,anchor='mt')
        elif kind=='gauge': d.text(px(u,v+.053),label,font=small,fill=BLANC,anchor='mb')
im.save(ROOT/'plaques.png')

# Trois instruments analogiques, avec graduation indépendante du mesh.
for name,title,unit,needle in [('jauge_alt','ALT','KM',-35),('jauge_att','ATT','DEG',22),('jauge_prop','THRUST','%',54)]:
    im=Image.new('RGB',(512,512),(12,18,19)); d=ImageDraw.Draw(im)
    d.ellipse((12,12,500,500),fill=(20,27,27),outline=(126,137,129),width=9)
    d.ellipse((39,39,473,473),outline=(55,66,64),width=4)
    for i in range(-120,121,10):
        tick(d,(256,256),200,i,23 if i%30==0 else 10,(210,218,200) if i%30==0 else (95,109,101),3 if i%30==0 else 2)
    for i in range(9):
        a=math.radians(-120+i*30); x=256+math.sin(a)*151; y=256-math.cos(a)*151
        d.text((x-9,y-9),str(i),font=font(18,True),fill=(210,218,200))
    a=math.radians(needle); d.line((256,256,256+math.sin(a)*150,256-math.cos(a)*150),fill=(243,184,89),width=6)
    d.ellipse((244,244,268,268),fill=(224,225,207)); d.text((209,320),title,font=font(21,True),fill=(209,220,204)); d.text((235,352),unit,font=font(15),fill=(152,167,154))
    im.save(ROOT/(name+'.png'))
