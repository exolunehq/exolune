"""Télécharge les sources figées puis extrait le prefab Unity, sans lancer de programme fourni."""
from pathlib import Path
import hashlib, json, tarfile, urllib.request, zipfile
from importe import CACHE

manifest=json.loads((Path(__file__).parent/'sources_jeu.json').read_text(encoding='utf8'))
for item in manifest['files']:
    path=CACHE/item['path']; path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
        data=urllib.request.urlopen(item['url'],timeout=120).read()
        if hashlib.sha256(data).hexdigest()!=item['sha256']: raise ValueError('SHA-256 incorrect : '+item['url'])
        path.write_bytes(data)
    print(path,flush=True)
folder=CACHE/'tree10';folder.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(CACHE/'tree10.zip') as z:
    with z.open('uploadtool_Tree10.unitypackage') as src, (folder/'uploadtool_Tree10.unitypackage').open('wb') as dst:
        import shutil;shutil.copyfileobj(src,dst)
with tarfile.open(folder/'uploadtool_Tree10.unitypackage') as tar:
    tar.extractall(folder/'extract',filter='data')
