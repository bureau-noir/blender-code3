"""
Module pour appliquer la transparence à une sélection d'objets dans Blender
Usage :
    1. Sélectionner une collection avec coll_selector.py
    2. Appeler apply_transparency(percent=50) pour rendre la sélection à 50% transparente
"""

import bpy  # type: ignore

def apply_transparency(percent: float = 50.0, mat_name_prefix: str = "Transparent_"):
    """
    Applique un matériau transparent à tous les Meshs sélectionnés.
    Args:
        percent (float): Pourcentage de transparence (0 = opaque, 100 = totalement invisible)
        mat_name_prefix (str): Préfixe pour le nom du matériau
    """
    alpha_value = max(0.0, min(1.0, 1.0 - percent / 100.0))  # 0=opaque, 1=invisible
    mat_name = f"{mat_name_prefix}{int(percent)}"
    
    # Créer ou récupérer le matériau
    if mat_name not in bpy.data.materials:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Alpha"].default_value = alpha_value
        mat.blend_method = 'BLEND'
    else:
        mat = bpy.data.materials[mat_name]
    
    # Appliquer le matériau à tous les Meshs sélectionnés
    count = 0
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)
            count += 1
    print(f"✅ {count} objets Mesh rendus transparents à {percent}% (alpha={alpha_value})") 