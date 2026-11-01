"""Reproducible cabin micro-surfaces. Two 1024px maps, four padded swatches.

Colour stays in the material factors; G is roughness, B metallic, RGB normals
are linear tangent-space data. No lighting or large panel seams are baked here.
Run with Python, numpy and Pillow before design_chasseur.py.
"""
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
SIZE, TILE, BORDER = 1024, 512, 8


def generer():
    from PIL import Image
    rng = np.random.default_rng(110126)
    normal = np.zeros((SIZE, SIZE, 3), np.float32)
    orm = np.ones((SIZE, SIZE, 3), np.float32)
    y, x = np.mgrid[:TILE, :TILE].astype(np.float32) / TILE
    for k in range(4):
        noise = rng.normal(0, 1, (TILE, TILE)).astype(np.float32)
        fine = sum(np.roll(noise, d, axis=0) for d in (-1, 0, 1)) / 3
        mottling = np.sin(2*np.pi*(x*5+y*3)) * np.sin(2*np.pi*(x*3-y*7))
        if k == 0:  # powder-coated alloy: restrained stipple, no metallic paint
            h = .000035*fine
            rough, metal = .92 + .018*mottling + .014*fine, .025
        elif k == 1:  # upholstery: irregular grain and shallow pores
            grain = np.sin(2*np.pi*(x*73 + .24*np.sin(y*160))) * np.sin(2*np.pi*(y*89+.2*np.sin(x*131)))
            h = .00011*grain + .000025*fine
            rough, metal = .70+.045*grain+.02*mottling, 0.0
        elif k == 2:  # woven harness webbing, distinct from the seat leather
            warp = np.cos(2*np.pi*x*96)
            weft = np.cos(2*np.pi*y*112)
            h = .00010*(warp+weft) + .000025*warp*weft
            rough, metal = .84+.035*warp*weft, 0.0
        else:  # directional machined metal
            brush = np.sin(2*np.pi*y*103) + .35*np.sin(2*np.pi*y*177)
            h = .000025*brush + .000006*fine
            rough, metal = .34+.035*brush+.015*mottling, .85
        dx = (np.roll(h, -1, 1)-np.roll(h, 1, 1))*TILE/2
        dy = -(np.roll(h, -1, 0)-np.roll(h, 1, 0))*TILE/2
        n = np.stack((-dx, -dy, np.ones_like(dx)), axis=-1)
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        rs, cs = slice((k//2)*TILE, (k//2+1)*TILE), slice((k%2)*TILE, (k%2+1)*TILE)
        normal[rs, cs] = n*.5+.5
        orm[rs, cs, 1] = rough
        orm[rs, cs, 2] = metal
    for name, data in [('cabine_normale', normal), ('cabine_metal_rugosite', orm)]:
        Image.fromarray(np.uint8(np.clip(data, 0, 1)*255+.5)).save(ROOT/(name+'.png'))
    print('Cabin maps: two 1024 x 1024 linear PNGs')


def appliquer(g):
    """Assign physical materials and nondegenerate UVs before glTF export."""
    import bpy
    from mathutils import Vector
    # (atlas tile, minimum footprint in metres, roughness multiplier, bump scale)
    finishes = {
        'Jeu | Structure cabine': (0, 1.0, .64/.92, 1.0),
        'Jeu | Structure graphite': (0, .7, .595/.92, .8),
        'Jeu | Ceramique graphite': (0, .5, .608/.92, .6),
        'Jeu | Antireflet': (0, .7, .896/.92, .6),
        'Jeu | Caoutchouc': (0, .3, .832/.92, .4),
        'Jeu | Cuir': (1, .45, 1.0, 1.0),
        'Jeu | Sangle': (2, .35, 1.0, .8),
        'Jeu | Metal brosse': (3, .4, 1.0, .5),
        'Jeu | plaques': (0, .50, .54/.92, .85),
    }
    for name, (tile, _, roughness, strength) in finishes.items():
        mat = bpy.data.materials.get(name)
        if mat is None:
            continue
        nt = mat.node_tree
        p = nt.nodes['Principled BSDF']
        layer = 'UVDetail' if name == 'Jeu | plaques' else 'UVMap'
        uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = layer
        def texture(filename):
            tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = g['image'](filename, True)
            nt.links.new(uv.outputs['UV'], tex.inputs['Vector'])
            return tex
        channels = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(texture('cabine_metal_rugosite.png').outputs['Color'], channels.inputs['Color'])
        # glTF-compatible roughness factor; keep the same shared image.
        scale = nt.nodes.new('ShaderNodeMath'); scale.operation = 'MULTIPLY'; scale.inputs[1].default_value = roughness
        nt.links.new(channels.outputs['Green'], scale.inputs[0]); nt.links.new(scale.outputs[0], p.inputs['Roughness'])
        nt.links.new(channels.outputs['Blue'], p.inputs['Metallic'])
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.uv_map = layer; nm.inputs['Strength'].default_value = strength
        nt.links.new(texture('cabine_normale.png').outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs[0], p.inputs['Normal'])
    for obj in g['ship'].all_objects:
        if obj.type != 'MESH':
            continue
        for face in obj.data.polygons:
            name = obj.data.materials[face.material_index].name
            if name not in finishes:
                continue
            uv = obj.data.uv_layers.get('UVDetail' if name == 'Jeu | plaques' else 'UVMap')
            if uv is None: continue
            tile, footprint, _, _ = finishes[name]
            pts = [obj.matrix_world @ obj.data.vertices[obj.data.loops[i].vertex_index].co for i in face.loop_indices]
            ab = g['projection'](pts)
            lo = [min(p[k] for p in ab) for k in range(2)]
            span = max(footprint, *(max(p[k] for p in ab)-lo[k] for k in range(2)))
            # A border prevents adjacent finishes bleeding into ordinary mips.
            for li, (a, b) in zip(face.loop_indices, ab):
                uv.data[li].uv = ((tile%2)/2 + (BORDER+(a-lo[0])/span*(TILE-2*BORDER))/SIZE,
                                  1-(tile//2)/2 - (BORDER+(b-lo[1])/span*(TILE-2*BORDER))/SIZE)


if __name__ == '__main__':
    generer()
