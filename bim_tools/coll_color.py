"""
Module pour appliquer des couleurs aux collections dans Blender
Usage :
    apply_color_to_collection("MDA-Nicolet/STR/NIVEAU 5", (0.0, 0.0, 0.8, 1.0))  # Bleu foncé
    apply_color_to_collection("MDA-Nicolet/INT/NIVEAU 3", (1.0, 0.0, 0.0, 1.0))  # Rouge
"""

import bpy  # type: ignore

def apply_color_to_collection(collection_name: str, color: tuple = (0.0, 0.0, 1.0, 1.0), 
                            force_new_material: bool = True):
    """
    Applique une couleur à tous les objets d'une collection via un matériau.
    
    Args:
        collection_name (str): Nom de la collection (ex: "MDA-Nicolet/STR/NIVEAU 5")
        color (tuple): Couleur RGBA (r, g, b, a) où chaque valeur est entre 0 et 1
        force_new_material (bool): Si True, supprime tous les matériaux existants
    
    Returns:
        bool: True si succès, False sinon
    """
    collection = bpy.data.collections.get(collection_name)
    
    if not collection:
        print(f"❌ Collection '{collection_name}' non trouvée")
        print("Collections disponibles :")
        for coll in bpy.data.collections:
            if "/" in coll.name:  # Collections avec hiérarchie
                print(f"  - {coll.name}")
        return False
    
    # Créer un nom de matériau basé sur la collection
    safe_name = collection_name.replace('/', '_').replace(' ', '_')
    mat_name = f"Color_{safe_name}"
    
    # Supprimer le matériau existant s'il existe et qu'on force
    if force_new_material and mat_name in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials[mat_name])
    
    # Créer un nouveau matériau
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    
    # Nettoyer tous les nœuds existants pour un matériau propre
    mat.node_tree.nodes.clear()
    
    # Créer un nœud Principled BSDF simple
    bsdf = mat.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    
    # Créer un nœud Output
    output = mat.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (300, 0)
    
    # Connecter les nœuds
    mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    # Définir la couleur et les propriétés du matériau
    bsdf.inputs['Base Color'].default_value = (color[0], color[1], color[2], 1.0)
    bsdf.inputs['Metallic'].default_value = 0.0
    bsdf.inputs['Roughness'].default_value = 0.5
    
    # Appliquer le matériau à tous les objets de la collection
    count = 0
    for obj in collection.all_objects:
        if obj.type == 'MESH':
            if force_new_material:
                # Vider tous les matériaux existants
                obj.data.materials.clear()
            # Ajouter le nouveau matériau
            obj.data.materials.append(mat)
            count += 1
    
    # Forcer l'affichage des matériaux dans toutes les vues 3D
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'
    
    print(f"✅ Collection '{collection_name}' colorée ({count} objets traités)")
    print(f"   Matériau créé : {mat_name}")
    print(f"   Couleur appliquée : RGBA{color}")
    print(f"   Affichage matériaux activé dans les vues 3D")
    
    return True

def apply_color_to_collection_simple(collection_name: str, color: tuple = (0.0, 0.0, 1.0, 1.0)):
    """
    Version simplifiée qui garde les matériaux existants et ajoute juste la couleur.
    """
    return apply_color_to_collection(collection_name, color, force_new_material=False)

def get_color_presets():
    """
    Retourne un dictionnaire de couleurs prédéfinies utiles.
    """
    return {
        'rouge': (1.0, 0.0, 0.0, 1.0),
        'vert': (0.0, 1.0, 0.0, 1.0),
        'bleu': (0.0, 0.0, 1.0, 1.0),
        'jaune': (1.0, 1.0, 0.0, 1.0),
        'cyan': (0.0, 1.0, 1.0, 1.0),
        'magenta': (1.0, 0.0, 1.0, 1.0),
        'orange': (1.0, 0.5, 0.0, 1.0),
        'violet': (0.5, 0.0, 1.0, 1.0),
        'bleu_fonce': (0.0, 0.0, 0.8, 1.0),
        'rouge_fonce': (0.8, 0.0, 0.0, 1.0),
        'vert_fonce': (0.0, 0.8, 0.0, 1.0),
        'gris': (0.5, 0.5, 0.5, 1.0),
        'blanc': (1.0, 1.0, 1.0, 1.0),
        'noir': (0.0, 0.0, 0.0, 1.0)
    }

def apply_preset_color(collection_name: str, color_name: str):
    """
    Applique une couleur prédéfinie à une collection.
    
    Args:
        collection_name (str): Nom de la collection
        color_name (str): Nom de la couleur prédéfinie (ex: 'rouge', 'bleu_fonce')
    """
    presets = get_color_presets()
    
    if color_name not in presets:
        print(f"❌ Couleur '{color_name}' non trouvée")
        print(f"Couleurs disponibles : {list(presets.keys())}")
        return False
    
    return apply_color_to_collection(collection_name, presets[color_name])

# Exemples d'utilisation
if __name__ == "__main__":
    # Exemple 1 : Appliquer une couleur personnalisée
    # apply_color_to_collection("MDA-Nicolet/STR/NIVEAU 5", (0.0, 0.0, 0.8, 1.0))
    
    # Exemple 2 : Utiliser une couleur prédéfinie
    # apply_preset_color("MDA-Nicolet/STR/NIVEAU 5", "bleu_fonce")
    
    # Exemple 3 : Appliquer sans forcer (garde les matériaux existants)
    # apply_color_to_collection_simple("MDA-Nicolet/STR/NIVEAU 5", (1.0, 0.0, 0.0, 1.0))
    
    print("Module coll_color.py chargé !")
    print("Fonctions disponibles :")
    print("  - apply_color_to_collection(collection_name, color)")
    print("  - apply_preset_color(collection_name, color_name)")
    print("  - apply_color_to_collection_simple(collection_name, color)")
    print("  - get_color_presets()") 