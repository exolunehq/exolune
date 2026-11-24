"""Print the legends behind the native instruments. Values, needles and lights come from flight."""
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont

def make(directory):
    for panel, title, number in [('Vol','ATTITUDE  /  VOL','01'),('Nav','NAVIGATION','02'),('Systemes','CONFIGURATION  /  %','03')]:
        im = Image.new('RGB',(640,512),(9,23,30))
        pen = ImageDraw.Draw(im)
        def label(x,y,text,size=19,color='#b7d9dc'):
            pen.text((x,y),text,font=ImageFont.load_default(size=size),fill=color,stroke_width=0)
        for x in range(16,630,32):
            pen.line((x,63,x,445),fill='#102a31')
        for y in range(64,445,32):
            pen.line((12,y,628,y),fill='#102a31')
        pen.rounded_rectangle((5,5,634,506),radius=13,outline='#31757c',width=3)
        pen.line((16,59,624,59),fill='#31757c',width=2)
        label(23,15,title,30)
        label(563,22,'/ '+number,20,'#e7b35d')
        if panel=='Vol':
            label(26,108,'KM/H',18)
            label(534,108,'KM',18)
            label(26,420,'VITESSE  KM/H')
            label(364,420,'ALTITUDE  KM')
        elif panel=='Nav':
            label(27,420,'CAP  DEG')
            label(365,420,'LATITUDE  DEG')
            label(28,91,'LON  DEG',16)
        else:
            for y,name in zip((112,191,270,349),('AILES','TRAIN','AEROFREIN','RAMPE')):
                label(28,y,name,23)
            label(26,423,'GAZ %',17)
            label(174,423,'MOTEUR %',17)
            label(455,23,'RX',15)
            label(379,434,'AUTO',19,'#96b6b4')
            label(507,434,'MANUEL',19,'#e8b66b')
        im.save(directory/('NAV_Ecran_'+panel+'.png'))
if __name__=='__main__':
    make(Path(sys.argv[1]))
