import bpy
import bmesh
from mathutils import Vector
import numpy as np

def tile_building_footprint():
    """
    Décompose l'empreinte irrégulière en modules de 14'x48' par tiling simple
    """
    print("🏗️ TILING SIMPLE DE L'EMPREINTE IRRÉGULIÈRE")
    print("=" * 50)
    
    # 1. Obtenir l'empreinte du bâtiment
    building_bounds = get_building_bounds()
    
    if not building_bounds:
        print("❌ Impossible d'obtenir l'empreinte")
        return None
    
    # 2. Créer modules par tiling simple
    modules = create_simple_tiling_modules(building_bounds)
    
    # 3. Visualiser le résultat
    visualize_tiling_result(modules, building_bounds)
    
    return modules

def get_building_bounds():
    """Obtient l'empreinte réelle du bâtiment avec grille de densité"""
    
    print("🔍 ANALYSE DE L'EMPREINTE RÉELLE")
    
    # Trouver la collection de structure spécifique
    target_collection = None
    for collection in bpy.data.collections:
        if 'MDA-Nicolet' in collection.name and 'STR' in collection.name and 'NIVEAU 5' in collection.name:
            target_collection = collection
            break
    
    if not target_collection:
        print("❌ Collection MDA-Nicolet/STR/NIVEAU 5 non trouvée")
        return None
    
    # Collecter les objets de structure de la collection spécifique
    structure_objects = [obj for obj in target_collection.objects if obj.type == 'MESH']
    
    if not structure_objects:
        print("❌ Aucun objet mesh dans la collection de structure")
        return None
    
    print(f"   Collection utilisée: {target_collection.name}")
    print(f"   Objets de structure trouvés: {len(structure_objects)}")
    
    # Créer une grille de densité fine (1m cell pour précision)
    grid_size = 1.0
    all_vertices = []
    for obj in structure_objects:
        for vertex in obj.data.vertices:
            world_vertex = obj.matrix_world @ vertex.co
            all_vertices.append(world_vertex)
    
    # Limites globales
    min_x = min(v.x for v in all_vertices)
    max_x = max(v.x for v in all_vertices)
    min_y = min(v.y for v in all_vertices)
    max_y = max(v.y for v in all_vertices)
    min_z = min(v.z for v in all_vertices)
    max_z = max(v.z for v in all_vertices)
    
    # Grille footprint (1 = occupé)
    grid_width = int((max_x - min_x) / grid_size) + 1
    grid_height = int((max_y - min_y) / grid_size) + 1
    footprint_grid = np.zeros((grid_width, grid_height), dtype=int)
    
    for vertex in all_vertices:
        grid_x = int((vertex.x - min_x) / grid_size)
        grid_y = int((vertex.y - min_y) / grid_size)
        if 0 <= grid_x < grid_width and 0 <= grid_y < grid_height:
            footprint_grid[grid_x, grid_y] = 1
    
    bounds = {
        'width': max_x - min_x,
        'length': max_y - min_y,
        'height': max_z - min_z,
        'min': Vector((min_x, min_y, min_z)),
        'max': Vector((max_x, max_y, max_z)),
        'footprint_grid': footprint_grid,
        'grid_size': grid_size,
        'grid_width': grid_width,
        'grid_height': grid_height
    }
    
    print(f"   Empreinte: {bounds['width']:.1f}m x {bounds['length']:.1f}m")
    print(f"   Grille: {grid_width} x {grid_height} cellules")
    
    return bounds

def create_simple_tiling_modules(building_bounds):
    """Tiling simple : placer modules horizontaux et garder ceux qui touchent l'empreinte"""
    
    print("\n📐 TILING SIMPLE PAR OVERLAP")
    
    # Dimensions module en mètres (14' = 4.267m, 48' = 14.63m)
    MODULE_WIDTH = 4.267   # 14' sur Y
    MODULE_LENGTH = 14.63  # 48' sur X
    
    print(f"   Module: {MODULE_LENGTH:.2f}m (X) x {MODULE_WIDTH:.2f}m (Y)")
    
    # Paramètres
    footprint_grid = building_bounds['footprint_grid']
    grid_size = building_bounds['grid_size']
    min_x, min_y = building_bounds['min'].x, building_bounds['min'].y
    
    modules = []
    module_id = 0
    
    # Calculer nombre de modules pour couvrir complètement
    num_rows = int(building_bounds['length'] / MODULE_WIDTH) + 2
    num_cols = int(building_bounds['width'] / MODULE_LENGTH) + 2
    
    print(f"   Test de {num_cols} x {num_rows} positions")
    
    # TILING SIMPLE : tester chaque position et garder si overlap > seuil
    for row in range(num_rows):
        for col in range(num_cols):
            # Position du module
            module_x = min_x + (col * MODULE_LENGTH)
            module_y = min_y + (row * MODULE_WIDTH)
            
            # Calculer overlap avec empreinte réelle
            overlap_ratio = calculate_footprint_overlap(
                module_x, module_y, MODULE_LENGTH, MODULE_WIDTH,
                footprint_grid, grid_size, min_x, min_y,
                building_bounds['grid_width'], building_bounds['grid_height']
            )
            
            # Garder module si overlap significatif (seuil très bas pour couvrir toute l'empreinte)
            if overlap_ratio > 0.01:  # Seuil : 1% d'overlap minimum pour couvrir complètement
                modules.append({
                    'id': module_id,
                    'position': Vector((module_x, module_y, 0)),
                    'dimensions': Vector((MODULE_LENGTH, MODULE_WIDTH, 0)),
                    'overlap_ratio': overlap_ratio,
                    'rotated': False,
                    'grid_pos': (col, row)
                })
                module_id += 1
    
    print(f"   Modules créés: {len(modules)}")
    return modules

def calculate_footprint_overlap(module_x, module_y, module_length, module_width, 
                               footprint_grid, grid_size, min_x, min_y, grid_width, grid_height):
    """Calcule l'overlap d'un module avec l'empreinte réelle"""
    
    # Convertir coordonnées module en indices grille
    start_grid_x = int((module_x - min_x) / grid_size)
    start_grid_y = int((module_y - min_y) / grid_size)
    end_grid_x = int((module_x + module_length - min_x) / grid_size)
    end_grid_y = int((module_y + module_width - min_y) / grid_size)
    
    # Compter cellules occupées dans la zone du module
    occupied_cells = 0
    total_cells = 0
    
    for gx in range(max(0, start_grid_x), min(grid_width, end_grid_x + 1)):
        for gy in range(max(0, start_grid_y), min(grid_height, end_grid_y + 1)):
            total_cells += 1
            if footprint_grid[gx, gy] == 1:
                occupied_cells += 1
    
    return occupied_cells / total_cells if total_cells > 0 else 0

def visualize_tiling_result(modules, building_bounds):
    """Visualise le résultat du tiling"""
    
    print("\n🎨 VISUALISATION")
    
    # Supprimer collection existante
    if 'SIMPLE_TILING' in bpy.data.collections:
        bpy.data.collections.remove(bpy.data.collections['SIMPLE_TILING'])
    
    tiling_collection = bpy.data.collections.new('SIMPLE_TILING')
    bpy.context.scene.collection.children.link(tiling_collection)
    
    # Empreinte bâtiment (forme réelle basée sur grille)
    create_real_footprint(building_bounds, tiling_collection)
    
    # Modules
    for module in modules:
        create_module_visualization(module, tiling_collection)
    
    print("   Collection 'SIMPLE_TILING' créée")

def create_real_footprint(building_bounds, collection):
    """Crée l'empreinte réelle du bâtiment basée sur la grille de densité"""
    
    mesh = bpy.data.meshes.new("Real_Footprint")
    obj = bpy.data.objects.new("Real_Footprint", mesh)
    collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Créer mesh basé sur grille de densité
    footprint_grid = building_bounds['footprint_grid']
    grid_size = building_bounds['grid_size']
    min_x, min_y = building_bounds['min'].x, building_bounds['min'].y
    
    # Créer faces pour chaque cellule occupée
    for i in range(footprint_grid.shape[0]):
        for j in range(footprint_grid.shape[1]):
            if footprint_grid[i, j] == 1:
                # Coordonnées de la cellule
                x1 = min_x + (i * grid_size)
                y1 = min_y + (j * grid_size)
                x2 = x1 + grid_size
                y2 = y1 + grid_size
                
                # Créer quad
                v1 = bm.verts.new((x1, y1, -0.01))
                v2 = bm.verts.new((x2, y1, -0.01))
                v3 = bm.verts.new((x2, y2, -0.01))
                v4 = bm.verts.new((x1, y2, -0.01))
                
                bm.faces.new([v1, v2, v3, v4])
    
    # Fusionner vertices proches pour créer forme continue
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.1)
    
    bm.to_mesh(mesh)
    bm.free()
    
    # Matériau rouge transparent
    material = bpy.data.materials.new("Real_Footprint_Material")
    material.use_nodes = True
    material.node_tree.nodes.clear()
    
    bsdf = material.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
    output = material.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
    material.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    bsdf.inputs['Base Color'].default_value = (0.8, 0.1, 0.1, 0.4)
    bsdf.inputs['Alpha'].default_value = 0.4
    material.blend_method = 'BLEND'
    
    obj.data.materials.append(material)

def create_module_visualization(module, collection):
    """Crée la visualisation d'un module avec contours rouges"""
    
    mesh = bpy.data.meshes.new(f"Module_{module['id']}")
    obj = bpy.data.objects.new(f"Module_{module['id']}", mesh)
    collection.objects.link(obj)
    
    bm = bmesh.new()
    
    # Créer rectangle du module
    x, y = module['position'].x, module['position'].y
    length, width = module['dimensions'].x, module['dimensions'].y
    
    # Créer les vertices avec une légère élévation pour les contours
    bm.verts.new((x, y, 0.01))
    bm.verts.new((x + length, y, 0.01))
    bm.verts.new((x + length, y + width, 0.01))
    bm.verts.new((x, y + width, 0.01))
    
    # Créer la face principale
    bm.faces.new(bm.verts)
    
    # Créer les bords pour les contours (lignes rouges)
    edges = list(bm.edges)
    for edge in edges:
        edge.select = True
    
    bm.to_mesh(mesh)
    bm.free()
    
    # Créer le matériau vert
    material = create_module_material(module)
    obj.data.materials.append(material)
    
    # Activer l'affichage des bords en mode Solid
    obj.show_wire = True
    obj.show_all_edges = True

def create_module_material(module):
    """Crée matériau vert avec contour rouge visible en mode Solid"""
    
    material = bpy.data.materials.new(f"Module_Material_{module['id']}")
    material.use_nodes = True
    material.node_tree.nodes.clear()
    
    # Nœud principal avec couleur verte
    bsdf = material.node_tree.nodes.new(type='ShaderNodeBsdfPrincipled')
    output = material.node_tree.nodes.new(type='ShaderNodeOutputMaterial')
    material.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    # Couleur verte pour le module
    bsdf.inputs['Base Color'].default_value = (0.1, 0.8, 0.1, 0.8)
    bsdf.inputs['Metallic'].default_value = 0.0
    bsdf.inputs['Roughness'].default_value = 0.2
    
    # Activer les bords pour qu'ils soient visibles en mode Solid
    material.use_backface_culling = False
    material.blend_method = 'OPAQUE'
    
    return material

if __name__ == "__main__":
    tiling_result = tile_building_footprint()
    if tiling_result:
        print(f"\n✅ TILING TERMINÉ")
        print(f"   Modules placés: {len(tiling_result)}")
    else:
        print(f"\n❌ ÉCHEC")