"""
Module pour appliquer la transparence à une collection dans Blender
Usage :
    apply_transparency(percent=50, collection_name="MDA-Nicolet/STR/NIVEAU 5")
"""

import bpy  # type: ignore

def apply_transparency(percent: float = 50.0, mat_name_prefix: str = "Transparent_", collection_name: str = None):
    """
    Applique un matériau transparent à tous les Meshs d'une collection.
    Args:
        percent (float): Pourcentage de transparence (0 = opaque, 100 = totalement invisible)
        mat_name_prefix (str): Préfixe pour le nom du matériau
        collection_name (str): Nom de la collection à traiter (optionnel)
    """
    alpha_value = max(0.0, min(1.0, 1.0 - percent / 100.0))  # 0=opaque, 1=invisible
    
    # Si une collection est spécifiée, sélectionner ses objets
    if collection_name:
        # Désélectionner tout d'abord
        bpy.ops.object.select_all(action='DESELECT')
        
        # Trouver et sélectionner la collection
        target_collection = None
        for collection in bpy.data.collections:
            if collection_name in collection.name:
                target_collection = collection
                break
        
        if target_collection:
            # Sélectionner tous les objets de la collection
            for obj in target_collection.objects:
                obj.select_set(True)
            print(f"📦 Collection '{target_collection.name}' sélectionnée ({len(target_collection.objects)} objets)")
        else:
            print(f"❌ Collection '{collection_name}' non trouvée")
            return
    
    # Appliquer la transparence à tous les Meshs sélectionnés
    count = 0
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            # Préserver le matériau existant ou en créer un nouveau
            if obj.data.materials:
                # Utiliser le matériau existant
                mat = obj.data.materials[0]
                if not mat.use_nodes:
                    mat.use_nodes = True
            else:
                # Créer un nouveau matériau rouge transparent
                mat = bpy.data.materials.new(name=f"{mat_name_prefix}{obj.name}")
                mat.use_nodes = True
                obj.data.materials.append(mat)
                
                # Configurer le matériau rouge
                bsdf = mat.node_tree.nodes.get("Principled BSDF")
                if bsdf:
                    bsdf.inputs["Base Color"].default_value = (0.8, 0.1, 0.1, 1.0)  # Rouge
            
            # Ajouter la transparence au matériau existant
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                bsdf.inputs["Alpha"].default_value = alpha_value
            mat.blend_method = 'BLEND'
            
            count += 1
    
    print(f"✅ {count} objets Mesh rendus transparents à {percent}% (alpha={alpha_value})") 