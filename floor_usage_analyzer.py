import bpy
import bmesh
from mathutils import Vector
import sqlite3

def analyze_floor_usage():
    """Analyse les utilisations du sol et crée une visualisation basée sur la géométrie réelle"""
    
    print("🏠 ANALYSE DES UTILISATIONS DU SOL - NIVEAU 5")
    print("=" * 60)
    
    # Obtenir les données depuis SQLite
    usage_data = get_floor_usage_data()
    
    if usage_data:
        # Créer la visualisation basée sur la géométrie réelle
        create_realistic_floor_usage_visualization(usage_data)
    
    return usage_data

def get_floor_usage_data():
    """Récupère les données d'utilisation du sol depuis SQLite"""
    
    try:
        conn = sqlite3.connect('bim_library.sqlite')
        cursor = conn.cursor()
        
        # Récupérer les éléments du NIVEAU 5
        cursor.execute("""
            SELECT name, type, COUNT(*) as count 
            FROM ifc_element 
            WHERE storey = 'NIVEAU 5' 
            GROUP BY name, type 
            ORDER BY count DESC
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        # Catégoriser les éléments
        usage_categories = {
            'CHAMBRE': {'count': 0, 'color': (0.1, 0.8, 0.1, 1.0)},
            'SALLE_DE_BAIN': {'count': 0, 'color': (0.8, 0.1, 0.8, 1.0)},
            'CUISINE': {'count': 0, 'color': (1.0, 0.5, 0.0, 1.0)},
            'SALON': {'count': 0, 'color': (0.1, 0.1, 0.8, 1.0)},
            'FOYER': {'count': 0, 'color': (0.1, 0.8, 0.8, 1.0)},
            'BUREAU': {'count': 0, 'color': (0.8, 0.8, 0.1, 1.0)},
            'CORRIDOR': {'count': 0, 'color': (0.8, 0.4, 0.1, 1.0)},
            'RANGEMENT': {'count': 0, 'color': (0.6, 0.6, 0.6, 1.0)},
            'AUTRE': {'count': 0, 'color': (0.5, 0.5, 0.5, 1.0)}
        }
        
        total_elements = 0
        
        for name, element_type, count in results:
            category = categorize_element(name)
            if category in usage_categories:
                usage_categories[category]['count'] += count
                total_elements += count
        
        print("\n📊 RÉSULTATS DE L'ANALYSE:")
        for category, data in usage_categories.items():
            if data['count'] > 0:
                print(f"   {category}: {data['count']} éléments")
        
        print(f"\n📈 TOTAL: {total_elements} éléments analysés")
        
        return usage_categories
        
    except Exception as e:
        print(f"❌ Erreur SQLite: {e}")
        return None

def categorize_element(name):
    """Catégorise un élément selon son nom"""
    name_lower = name.lower()
    
    # Catégories principales pour les espaces
    if any(keyword in name_lower for keyword in ['chambre', 'bedroom', 'room']):
        return 'CHAMBRE'
    elif any(keyword in name_lower for keyword in ['bain', 'bath', 'douche', 'shower', 'toilette', 'toilet', 'wc']):
        return 'SALLE_DE_BAIN'
    elif any(keyword in name_lower for keyword in ['cuisine', 'kitchen']):
        return 'CUISINE'
    elif any(keyword in name_lower for keyword in ['salon', 'living', 'séjour']):
        return 'SALON'
    elif any(keyword in name_lower for keyword in ['foyer', 'entrée', 'entrance', 'hall']):
        return 'FOYER'
    elif any(keyword in name_lower for keyword in ['bureau', 'office', 'étude']):
        return 'BUREAU'
    elif any(keyword in name_lower for keyword in ['corridor', 'couloir', 'passage', 'hallway']):
        return 'CORRIDOR'
    elif any(keyword in name_lower for keyword in ['rangement', 'storage', 'closet']):
        return 'RANGEMENT'
    else:
        # Pour tous les autres éléments architecturaux, les classer selon leur fonction
        # Murs et cloisons -> CORRIDOR (définissent les espaces)
        # Planchers -> ESPACE_GENERAL
        # Autres éléments architecturaux -> ESPACE_GENERAL
        return 'ESPACE_GENERAL'

def create_realistic_floor_usage_visualization(usage_data):
    """Crée une visualisation réaliste basée sur la géométrie des objets avec sous-collections"""
    
    print(f"\n🎨 CRÉATION DE LA VISUALISATION RÉALISTE AVEC SOUS-COLLECTIONS")
    
    # Supprimer collection existante
    if 'FLOOR_USAGE_VISUALIZATION' in bpy.data.collections:
        bpy.data.collections.remove(bpy.data.collections['FLOOR_USAGE_VISUALIZATION'])
    
    # Créer collection principale
    main_collection = bpy.data.collections.new('FLOOR_USAGE_VISUALIZATION')
    bpy.context.scene.collection.children.link(main_collection)
    
    # Trouver la collection cible (INT/NIVEAU 5)
    target_collection = None
    for collection in bpy.data.collections:
        if 'MDA-Nicolet' in collection.name and 'INT' in collection.name and 'NIVEAU 5' in collection.name:
            target_collection = collection
            break
    
    if not target_collection:
        print("❌ Collection MDA-Nicolet/INT/NIVEAU 5 non trouvée")
        return
    
    print(f"   Collection utilisée: {target_collection.name}")
    
    # Définir les couleurs pour toutes les catégories
    category_colors = {
        'CHAMBRE': (0.1, 0.8, 0.1, 1.0),  # Vert
        'SALLE_DE_BAIN': (0.8, 0.1, 0.8, 1.0),  # Violet
        'CUISINE': (1.0, 0.5, 0.0, 1.0),  # Orange
        'SALON': (0.1, 0.1, 0.8, 1.0),  # Bleu
        'FOYER': (0.1, 0.8, 0.8, 1.0),  # Cyan
        'BUREAU': (0.8, 0.8, 0.1, 1.0),  # Jaune
        'CORRIDOR': (0.8, 0.4, 0.1, 1.0),  # Orange foncé
        'RANGEMENT': (0.6, 0.6, 0.6, 1.0),  # Gris
        'ESPACE_GENERAL': (0.5, 0.5, 0.5, 1.0)  # Gris clair
    }
    
    # Créer les sous-collections
    subcollections = {}
    
    # Traiter chaque objet de la collection avec filtrage
    processed_objects = 0
    filtered_objects = 0
    category_counts = {}
    
    for obj in target_collection.objects:
        if obj.type == 'MESH':
            # Filtrer les objets non pertinents
            if should_include_object(obj.name):
                # Catégoriser l'objet
                main_category, subcategory = categorize_element_with_subcategory(obj.name)
                
                # Créer la sous-collection si elle n'existe pas
                if main_category not in subcollections:
                    subcollections[main_category] = bpy.data.collections.new(f"FLOOR_USAGE_{main_category}")
                    main_collection.children.link(subcollections[main_category])
                
                # Créer un prisme 2D basé sur la bounding box de l'objet
                create_usage_prism(obj, main_category, subcategory, {'color': category_colors.get(main_category, (0.5, 0.5, 0.5, 1.0))}, subcollections[main_category])
                
                # Compter les objets par catégorie
                if main_category not in category_counts:
                    category_counts[main_category] = {}
                
                if subcategory not in category_counts[main_category]:
                    category_counts[main_category][subcategory] = 0
                category_counts[main_category][subcategory] += 1
                
                processed_objects += 1
            else:
                filtered_objects += 1
    
    # Créer les textes 3D flottants pour chaque catégorie
    create_floating_category_labels_with_subcategories(category_counts, category_colors, main_collection)
    
    print(f"   {processed_objects} objets traités")
    print(f"   {filtered_objects} objets filtrés (non pertinents)")
    print(f"   Collection 'FLOOR_USAGE_VISUALIZATION' créée avec {len(subcollections)} sous-collections")

def categorize_element_with_subcategory(name):
    """Catégorise un élément selon son nom avec sous-catégorie"""
    name_lower = name.lower()
    
    # Identifier la sous-catégorie avec plus de précision
    subcategory = 'GENERAL'
    if any(keyword in name_lower for keyword in ['lit', 'bed', 'soin']):
        subcategory = 'LIT_SOIN'
    elif any(keyword in name_lower for keyword in ['plafond', 'ceiling', 'composé', 'plaf']):
        subcategory = 'PLAFOND'
    elif any(keyword in name_lower for keyword in ['mur', 'wall', 'clois', 'partition']):
        subcategory = 'CLOISON'
    elif any(keyword in name_lower for keyword in ['porte', 'door']):
        subcategory = 'PORTE'
    elif any(keyword in name_lower for keyword in ['fenêtre', 'window']):
        subcategory = 'FENETRE'
    elif any(keyword in name_lower for keyword in ['plancher', 'floor', 'sol']):
        subcategory = 'PLANCHER'
    elif any(keyword in name_lower for keyword in ['escalier', 'stair']):
        subcategory = 'ESCALIER'
    elif any(keyword in name_lower for keyword in ['ascenseur', 'elevator']):
        subcategory = 'ASCENSEUR'
    elif any(keyword in name_lower for keyword in ['rampe', 'ramp']):
        subcategory = 'RAMPE'
    elif any(keyword in name_lower for keyword in ['toilette', 'wc', 'bathroom']):
        subcategory = 'SANITAIRE'
    elif any(keyword in name_lower for keyword in ['douche', 'shower']):
        subcategory = 'DOUCHE'
    elif any(keyword in name_lower for keyword in ['lavabo', 'sink']):
        subcategory = 'LAVABO'
    elif any(keyword in name_lower for keyword in ['cuisine', 'kitchen']):
        subcategory = 'CUISINE'
    elif any(keyword in name_lower for keyword in ['chambre', 'bedroom']):
        subcategory = 'CHAMBRE'
    elif any(keyword in name_lower for keyword in ['salon', 'living']):
        subcategory = 'SALON'
    elif any(keyword in name_lower for keyword in ['corridor', 'couloir']):
        subcategory = 'CORRIDOR'
    elif any(keyword in name_lower for keyword in ['foyer', 'entrée']):
        subcategory = 'FOYER'
    elif any(keyword in name_lower for keyword in ['bureau', 'office']):
        subcategory = 'BUREAU'
    elif any(keyword in name_lower for keyword in ['rangement', 'storage']):
        subcategory = 'RANGEMENT'
    elif any(keyword in name_lower for keyword in ['mobilier', 'furniture', 'chair', 'table', 'desk', 'cabinet', 'shelf']):
        subcategory = 'FURNISHING'
    elif any(keyword in name_lower for keyword in ['lamp', 'light', 'fixture', 'luminaire']):
        subcategory = 'ECLAIRAGE'
    elif any(keyword in name_lower for keyword in ['appliance', 'appareil', 'machine']):
        subcategory = 'APPAREIL'
    elif any(keyword in name_lower for keyword in ['garde-corps', 'mainscourante', 'railing', 'handrail']):
        subcategory = 'GARDE_CORPS'
    elif any(keyword in name_lower for keyword in ['proxy', 'elementproxy', 'buildingelementproxy']):
        subcategory = 'PROXY'
    elif any(keyword in name_lower for keyword in ['generic', 'undefined', 'unknown', 'misc']):
        subcategory = 'GENERIC'
    
    # Identifier la catégorie principale - extraire certaines sous-catégories comme catégories principales
    if any(keyword in name_lower for keyword in ['chambre', 'bedroom', 'room']):
        main_category = 'CHAMBRE'
    elif any(keyword in name_lower for keyword in ['bain', 'bath', 'douche', 'shower', 'toilette', 'toilet', 'wc']):
        main_category = 'SALLE_DE_BAIN'
    elif any(keyword in name_lower for keyword in ['cuisine', 'kitchen']):
        main_category = 'CUISINE'
    elif any(keyword in name_lower for keyword in ['salon', 'living', 'séjour']):
        main_category = 'SALON'
    elif any(keyword in name_lower for keyword in ['foyer', 'entrée', 'entrance', 'hall']):
        main_category = 'FOYER'
    elif any(keyword in name_lower for keyword in ['bureau', 'office', 'étude']):
        main_category = 'BUREAU'
    elif any(keyword in name_lower for keyword in ['corridor', 'couloir', 'passage', 'hallway']):
        main_category = 'CORRIDOR'
    elif any(keyword in name_lower for keyword in ['rangement', 'storage', 'closet']):
        main_category = 'RANGEMENT'
    elif any(keyword in name_lower for keyword in ['mur', 'wall', 'clois', 'partition']):
        main_category = 'CLOISON'
    elif any(keyword in name_lower for keyword in ['mobilier', 'furniture', 'chair', 'table', 'desk', 'cabinet', 'shelf']):
        main_category = 'FURNISHING'
    elif any(keyword in name_lower for keyword in ['plafond', 'ceiling', 'composé', 'plaf']):
        main_category = 'PLAFOND'
    elif any(keyword in name_lower for keyword in ['plancher', 'floor', 'sol']):
        main_category = 'PLANCHER'
    elif any(keyword in name_lower for keyword in ['porte', 'door']):
        main_category = 'PORTE'
    else:
        main_category = 'ESPACE_GENERAL'
    
    return main_category, subcategory

def create_usage_prism(obj, main_category, subcategory, category_data, collection):
    """Crée un prisme 2D basé sur la bounding box de l'objet"""
    
    # Obtenir la bounding box de l'objet
    bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    
    # Calculer les dimensions du prisme
    min_x = min(corner.x for corner in bbox_corners)
    max_x = max(corner.x for corner in bbox_corners)
    min_y = min(corner.y for corner in bbox_corners)
    max_y = max(corner.y for corner in bbox_corners)
    
    # Créer le mesh du prisme
    mesh = bpy.data.meshes.new(f"Usage_Prism_{main_category}_{subcategory}_{obj.name}")
    prism_obj = bpy.data.objects.new(f"Usage_Prism_{main_category}_{subcategory}_{obj.name}", mesh)
    collection.objects.link(prism_obj)
    
    # Créer la géométrie du prisme
    bm = bmesh.new()
    
    # Hauteur du prisme (extrusion en Z)
    height = 0.1
    
    # Créer les vertices du prisme
    v1 = bm.verts.new((min_x, min_y, 0))
    v2 = bm.verts.new((max_x, min_y, 0))
    v3 = bm.verts.new((max_x, max_y, 0))
    v4 = bm.verts.new((min_x, max_y, 0))
    v5 = bm.verts.new((min_x, min_y, height))
    v6 = bm.verts.new((max_x, min_y, height))
    v7 = bm.verts.new((max_x, max_y, height))
    v8 = bm.verts.new((min_x, max_y, height))
    
    # Créer les faces
    # Face inférieure
    bm.faces.new([v1, v2, v3, v4])
    # Face supérieure
    bm.faces.new([v5, v6, v7, v8])
    # Faces latérales
    bm.faces.new([v1, v2, v6, v5])
    bm.faces.new([v2, v3, v7, v6])
    bm.faces.new([v3, v4, v8, v7])
    bm.faces.new([v4, v1, v5, v8])
    
    bm.to_mesh(mesh)
    bm.free()
    
    # Créer le matériau coloré
    material = bpy.data.materials.new(f"Usage_Material_{main_category}_{subcategory}")
    material.use_nodes = True
    material.node_tree.nodes.clear()
    
    bsdf = material.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
    output = material.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
    material.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    # Utiliser la couleur définie pour cette catégorie
    bsdf.inputs['Base Color'].default_value = category_data['color']
    bsdf.inputs['Metallic'].default_value = 0.1
    bsdf.inputs['Roughness'].default_value = 0.3
    
    prism_obj.data.materials.append(material)

def create_floating_category_labels_with_subcategories(category_counts, category_colors, collection):
    """Crée des textes 3D flottants pour chaque catégorie avec sous-catégories"""
    
    # Position de départ pour les labels
    label_x = 0
    label_y = 0
    label_z = 2.0  # Hauteur flottante
    
    for main_category, subcategories in category_counts.items():
        if subcategories:
            # Créer le texte 3D pour la catégorie principale
            text_data = bpy.data.curves.new(type="FONT", name=f"Text_{main_category}")
            text_obj = bpy.data.objects.new(f"Label_{main_category}", text_data)
            collection.objects.link(text_obj)
            
            # Positionner le texte
            text_obj.location = (label_x, label_y, label_z)
            text_obj.scale = (0.5, 0.5, 0.5)
            
            # Calculer le total d'éléments pour cette catégorie
            total_elements = sum(subcategories.values())
            
            # Définir le contenu du texte
            text_data.body = f"{main_category} ({total_elements} éléments)"
            
            # Créer le matériau du texte
            text_material = bpy.data.materials.new(f"Text_Material_{main_category}")
            text_material.use_nodes = True
            text_material.node_tree.nodes.clear()
            
            bsdf = text_material.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
            output = text_material.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
            text_material.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
            
            # Texte en noir pour la lisibilité
            bsdf.inputs['Base Color'].default_value = (0.0, 0.0, 0.0, 1.0)
            
            text_obj.data.materials.append(text_material)
            
            # Déplacer la position pour le prochain label
            label_x += 5.0

def should_include_object(obj_name):
    """Détermine si un objet doit être inclus dans la visualisation"""
    
    name_lower = obj_name.lower()
    
    # Exclure seulement les éléments vraiment non pertinents
    exclude_keywords = [
        'mobilier', 'mobili', 'furniture', 'chair', 'table', 'desk', 'bed',
        'cabinet', 'shelf', 'lamp', 'light', 'fixture', 'appliance',
        'proxy', 'elementproxy', 'buildingelementproxy',
        'garde-corps', 'mainscourante', 'railing', 'handrail'
    ]
    
    # Vérifier si l'objet contient des mots-clés d'exclusion
    for keyword in exclude_keywords:
        if keyword in name_lower:
            return False
    
    # Inclure tous les autres éléments (murs, planchers, cloisons, etc.)
    # Ne pas être trop restrictif - inclure tout ce qui n'est pas explicitement exclu
    return True

if __name__ == "__main__":
    analyze_floor_usage() 