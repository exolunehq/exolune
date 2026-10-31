"""Convertit les modèles de jeu crédités dans sources_jeu.json en FOLMESH1/FOLMAT01.

Dépendances : numpy, Pillow et UnityPy (pour le prefab Unity 5.3 de Rakshi).
Les sources se téléchargent par telecharge_jeu.py dans le cache ignoré par git.
"""
from pathlib import Path
import json, struct
import numpy as np
from PIL import Image
from importe import accessor, ROOT, CACHE, OUT


def rgba(path):
    return Image.open(path).convert('RGBA')


def make_mask(size, roughness, transmission):
    r = np.asarray(roughness.convert('L'), np.uint8)
    t = np.full(r.shape, transmission, np.uint8)
    return Image.fromarray(np.stack([np.full(r.shape, 255, np.uint8), r, t, np.full(r.shape, 255, np.uint8)], -1))


def write(name, parts, colors, normals, masks):
    if not(len(colors)==len(normals)==len(masks)==2): raise ValueError('deux matériaux requis')
    tile = (1024, 1024)
    atlases=[]
    for imgs in (colors,normals,masks):
        atlas=Image.new('RGBA',(tile[0]*2,tile[1]))
        for i,im in enumerate(imgs): atlas.paste(im.resize(tile,Image.Resampling.LANCZOS),(i*tile[0],0))
        atlases.append(atlas)
    pos=np.concatenate([p[0] for p in parts]); lo=pos.min(axis=0); hi=pos.max(axis=0)
    height=hi[1]-lo[1]; offset=np.array([(lo[0]+hi[0])/2,lo[1],(lo[2]+hi[2])/2])
    out=OUT/name;out.mkdir(parents=True,exist_ok=True)
    verts=[];indices=[]; n=0
    for position, normal, uv, idx, mat in parts:
        v=np.empty((len(position),9),'<f4');v[:,:3]=(position-offset)/height
        v[:,3:6]=normal/np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-20)
        v[:,6:8]=uv;v[:,8]=mat;verts.append(v);indices.append(np.asarray(idx,dtype='<u4').reshape(-1)+n);n+=len(v)
    lo=(lo-offset)/height;hi=(hi-offset)/height
    with (out/'mesh.bin').open('wb') as f:
        f.write(struct.pack('<8s5I6f',b'FOLMESH1',n,sum(map(len,indices)),2048,1024,2,*lo,*hi))
        for v in verts:f.write(v.tobytes())
        for i in indices:f.write(i.tobytes())
        f.write(atlases[0].tobytes())
    with (out/'material.bin').open('wb') as f:
        f.write(struct.pack('<8s2I',b'FOLMAT01',2048,1024));f.write(atlases[1].tobytes());f.write(atlases[2].tobytes())
    print(name,n,sum(map(len,indices))//3,lo,hi,flush=True)


def pine():
    folder=CACHE/'pine-game';d=json.loads((folder/'scene.gltf').read_text());blob=(folder/'scene.bin').read_bytes()
    parts=[]
    def visit(i,parent):
        node=d['nodes'][i]
        if any(k in node for k in ('translation','rotation','scale')): raise ValueError('TRS non pris en charge')
        matrix=parent @ np.asarray(node.get('matrix',np.eye(4).T.reshape(-1)),dtype=float).reshape(4,4).T
        if 'mesh' in node:
            for p in d['meshes'][node['mesh']]['primitives']:
                att=p['attributes'];pos=accessor(d,blob,att['POSITION']).astype(float)
                norm=accessor(d,blob,att['NORMAL']).astype(float) @ np.linalg.inv(matrix[:3,:3])
                pos=pos @ matrix[:3,:3].T+matrix[:3,3]
                parts.append((pos,norm,accessor(d,blob,att['TEXCOORD_0']),accessor(d,blob,p['indices']),p['material']))
        for c in node.get('children',[]):visit(c,matrix)
    for node in d['scenes'][d.get('scene',0)]['nodes']:visit(node,np.eye(4))
    colors=[];normals=[];masks=[]
    for i in range(2):
        root=folder/'textures'/f'Tree_{i}Mat_'
        c=rgba(str(root)+'baseColor.png')
        # Le moteur et le bake coupent à 0,5 ; source glTF coupe à 0,208.
        if i==1:
            arr=np.array(c); a=arr[:,:,3].astype(float)/255
            arr[:,:,3]=np.rint(np.clip(a*(0.5/0.207986616724512),0,1)*255).astype('u1');c=Image.fromarray(arr)
        colors.append(c);normals.append(rgba(str(root)+'normal.png'))
        rough=rgba(str(root)+'metallicRoughness.png').getchannel('G')
        masks.append(make_mask(c.size,rough,255 if i else 0))
    write('game_fir',parts,colors,normals,masks)


def broadleaf():
    import UnityPy
    from UnityPy.helpers.MeshHelper import MeshHandler
    folder=CACHE/'tree10'/'extract'; files={p.read_text().strip():p.parent/'asset' for p in folder.glob('*/pathname')}
    def file(name):return files['Assets/Tree10/'+name]
    env=UnityPy.load(str(file('Tree10_1.prefab')))
    mesh=next(o.read() for o in env.objects if o.type.name=='Mesh')
    h=MeshHandler(mesh);h.process(); pos=np.asarray(h.m_Vertices);normal=np.asarray(h.m_Normals);uv=np.asarray(h.m_UV0).copy();uv[:,1]=1-uv[:,1]
    triangles=h.get_triangles()
    # Unity tree creator place écorce puis feuilles dans les deux sous-maillages.
    parts=[(pos,normal,uv,np.array(triangles[i]),1-i) for i in range(2)]
    color=rgba(file('Tree10_1_Textures/diffuse.png'))
    leaf=np.array(color); leaf[:,:,3]=np.rint(leaf[:,:,3].astype(float)*(0.5/0.622)).clip(0,255).astype('u1'); leaf=Image.fromarray(leaf)
    bark=color.copy();bark.putalpha(255)
    packed=np.array(rgba(file('Tree10_1_Textures/normal_specular.png')))
    # Unity Tree Creator : X en alpha, Y en vert ; inversion de Y après conversion des UV.
    x=packed[:,:,3].astype(np.float32)/127.5-1;y=1-packed[:,:,1].astype(np.float32)/127.5
    z=np.sqrt(np.maximum(0,1-x*x-y*y));normalmap=np.stack([np.clip((x+1)*127.5,0,255),np.clip((y+1)*127.5,0,255),np.clip((z+1)*127.5,0,255),np.full(x.shape,255)],axis=-1).astype('u1')
    nm=Image.fromarray(normalmap);rough=Image.new('L',color.size,190)
    write('game_broadleaf',parts,[leaf,bark],[nm,nm],[make_mask(color.size,rough,255),make_mask(color.size,rough,0)])

if __name__=='__main__':
    pine();broadleaf()
