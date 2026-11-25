"""Materials of the Navette AAA: the concept's palette, on Principled BSDF only (glTF-safe)."""
import os

import bpy

# Tiling micro-surface maps, generated outside Git. A missing map leaves the plain material.
TEXTURES = os.environ.get("NAVETTE_TEXTURES", "E:/ExoluneAssets/navette-exolune-aaa-2026-11-22/textures")


def _linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def principled(name, srgb, rough, metal=0.0, coat=0.0, emit=None, emit_strength=0.0, alpha=1.0):
    mat = bpy.data.materials.new(name)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*[_linear(c) for c in srgb], 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Coat Weight"].default_value = coat
    bsdf.inputs["Coat Roughness"].default_value = 0.06
    if emit is not None:
        bsdf.inputs["Emission Color"].default_value = (*[_linear(c) for c in emit], 1.0)
        bsdf.inputs["Emission Strength"].default_value = emit_strength
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        mat.surface_render_method = "BLENDED"
    return mat


def textured(mat, normal=None, rough=None, tiles=4.0, strength=0.15):
    """Add tiling micro-surface maps to a Principled material: UVs are in metres, tiles per metre."""
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (tiles, tiles, tiles)
    nt.links.new(coord.outputs["UV"], mapping.inputs["Vector"])
    for name, socket in ((normal, "Normal"), (rough, "Roughness")):
        path = os.path.join(TEXTURES, name) if name else None
        if not path or not os.path.exists(path):
            continue
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(path, check_existing=True)
        tex.image.colorspace_settings.name = "Non-Color"
        nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
        if socket == "Normal":
            bump = nt.nodes.new("ShaderNodeNormalMap")
            bump.inputs["Strength"].default_value = strength
            nt.links.new(tex.outputs["Color"], bump.inputs["Color"])
            nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        else:
            # keep the material's own level: the map only varies it
            base = bsdf.inputs["Roughness"].default_value
            ramp = nt.nodes.new("ShaderNodeMapRange")
            ramp.inputs["To Min"].default_value = max(base - 0.06, 0.02)
            ramp.inputs["To Max"].default_value = base + 0.10
            nt.links.new(tex.outputs["Color"], ramp.inputs["Value"])
            nt.links.new(ramp.outputs["Result"], bsdf.inputs["Roughness"])
    return mat


def library():
    m = {}
    m["white"] = principled("NAV_Email_Blanc", (0.90, 0.89, 0.86), 0.24, 0.0, coat=0.5)
    m["teal"] = principled("NAV_Email_Sarcelle", (0.035, 0.26, 0.31), 0.22, 0.0, coat=0.6)
    m["belly"] = principled("NAV_Email_Ventre", (0.80, 0.79, 0.75), 0.30, 0.0, coat=0.35)
    m["blade"] = principled("NAV_Metal_Aube", (0.10, 0.11, 0.12), 0.34, 0.85)
    m["titanium"] = principled("NAV_Metal_Titane", (0.42, 0.43, 0.45), 0.32, 0.9)
    m["dark"] = principled("NAV_Metal_Sombre", (0.075, 0.08, 0.09), 0.40, 0.8)
    m["duct"] = principled("NAV_Tuyere_Conduit", (0.045, 0.047, 0.052), 0.48, 0.75)
    m["core"] = principled("NAV_Tuyere_Coeur", (0.03, 0.03, 0.035), 0.6, 0.5, emit=(1.0, 0.36, 0.06), emit_strength=0.02)
    m["seam"] = principled("NAV_Joint_Panneau", (0.16, 0.17, 0.18), 0.7)
    m["panel"] = principled("NAV_Panneau_Radiateur", (0.02, 0.17, 0.21), 0.12, 0.3, coat=1.0)
    m["nav_red"] = principled("NAV_Feu_Rouge", (0.45, 0.01, 0.01), 0.12, emit=(1.0, 0.01, 0.005), emit_strength=0.9)
    m["nav_green"] = principled("NAV_Feu_Vert", (0.01, 0.40, 0.10), 0.12, emit=(0.0, 1.0, 0.15), emit_strength=0.9)
    m["rubber"] = principled("NAV_Joint_Noir", (0.035, 0.037, 0.04), 0.62)
    m["amber"] = principled("NAV_Lumiere_Ambre", (1.0, 0.45, 0.05), 0.3, emit=(1.0, 0.36, 0.03), emit_strength=1.5)
    m["amber_strong"] = principled("NAV_Lumiere_Tuyere", (1.0, 0.45, 0.05), 0.3, emit=(1.0, 0.33, 0.02),
                                   emit_strength=4.0)
    m["amber_paint"] = principled("NAV_Email_Ambre", (0.93, 0.47, 0.07), 0.28, 0.0, coat=0.4,
                                  emit=(1.0, 0.45, 0.06), emit_strength=0.6)
    m["glass"] = principled("NAV_Verre_Verriere", (0.13, 0.25, 0.29), 0.02, 0.0, coat=1.0, alpha=0.15)
    m["glass"].node_tree.nodes.get("Principled BSDF").inputs["IOR"].default_value = 1.49
    for key in ("white", "teal", "belly"):
        textured(m[key], "hull_enamel_normal.png", "hull_enamel_roughness.png", tiles=3.0, strength=0.12)
    for key in ("dark", "blade", "titanium", "duct"):
        textured(m[key], "metal_brushed_normal.png", "metal_brushed_roughness.png", tiles=4.0, strength=0.25)
    return m
