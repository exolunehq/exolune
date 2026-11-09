"""Cook NASA LROC albedo and LOLA normal slopes; no terrain displacement or baked light.

Reproduce with: python tools/prepare_celestial.py
Source cache stays in artifacts; the runtime needs only assets/celestial/lunar.rgba8mips.
"""
from pathlib import Path
import hashlib
import json
import urllib.request
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'artifacts/ciel-2026-11-07/sources'
OUTPUT = ROOT / 'assets/celestial'
URL = 'https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/'
PINS = {
    'lroc_color_2k.jpg': 'f7130a1822681fa7512d7dcfd40db8c10b9ba4f06777910348698260ed7a2170',
    'ldem_4_uint.tif': 'e6668bec27fc9b8fbb02d198c7ddfb08eedeeb790167b494f95e6b34201da05e',
}

def main():
    SOURCE.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    sources=[]
    for name, expected in PINS.items():
        path=SOURCE/name
        if not path.exists():
            urllib.request.urlretrieve(URL+name,path)
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=expected:
            raise ValueError(f'Unverified source revision: {name}')
        sources.append({'url':URL+name,'sha256':digest})
    colour=np.asarray(Image.open(SOURCE/'lroc_color_2k.jpg').convert('RGB'),dtype=np.float32)/255
    linear=np.where(colour<=.04045,colour/12.92,((colour+.055)/1.055)**2.4)
    albedo=linear@np.array([.2126,.7152,.0722],dtype=np.float32)
    h,w=albedo.shape
    latitude=(.5-(np.arange(h)+.5)/h)*np.pi
    cosine=np.cos(latitude)[:,None]
    mean=np.sum(albedo*cosine)/(np.sum(cosine)*w)
    height=(np.asarray(Image.open(SOURCE/'ldem_4_uint.tif'),dtype=np.float32)*.5-10000)
    height=np.asarray(Image.fromarray(height).resize((w,h),Image.Resampling.BILINEAR))
    east=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))/(2*(2*np.pi/w)*1737400*np.maximum(cosine,.05))
    north=-np.gradient(height,axis=0)/(np.pi/h*1737400)
    data=np.stack([np.clip(albedo/mean,0,2)/2,np.clip(east,-1,1),np.clip(north,-1,1),np.clip((height+10000)/32767.5,0,1)],axis=-1)
    packet=[]
    while True:
        packed=np.empty(data.shape,dtype=np.uint8)
        packed[...,0]=np.rint(data[...,0]*255).clip(0,255).astype(np.uint8)
        packed[...,1:3]=np.rint(data[...,1:3]*127+128).clip(1,255).astype(np.uint8)
        packed[...,3]=np.rint(data[...,3]*255).clip(0,255).astype(np.uint8)
        packet.append(packed.tobytes())
        if data.shape[:2]==(1,1): break
        size=(max(1,data.shape[1]//2),max(1,data.shape[0]//2))
        data=np.stack([np.asarray(Image.fromarray(data[...,i].astype(np.float32)).resize(size,Image.Resampling.BOX)) for i in range(4)],axis=-1)
    blob=b''.join(packet)
    (OUTPUT/'lunar.rgba8mips').write_bytes(blob)
    manifest={'credit':"NASA's Scientific Visualization Studio; Ernie Wright; LRO/LROC/LOLA instrument teams",'page':'https://svs.gsfc.nasa.gov/4720/','usage':'https://svs.gsfc.nasa.gov/help/','sources':sources,'width':w,'height':h,'mips':len(packet),'bytes':len(blob),'source_linear_mean':float(mean),'runtime_sha256':hashlib.sha256(blob).hexdigest(),'format':'RGBA8_UNORM: R relative linear albedo / 2; GB tangent slopes (byte-128)/127; A elevation preview. Mips average linear fields.'}
    (OUTPUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(f'Cooked {w}x{h}, {len(packet)} mips, {len(blob)} bytes; mean reflectance multiplier 1.')

if __name__=='__main__': main()
