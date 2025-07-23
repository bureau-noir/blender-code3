import bpy  # type: ignore
import os
import json

# === CONFIGURATION HIÉRARCHIQUE ===
BASE_LIBRARY = '/Users/PeteTurcotte/Dropbox/Cursor/blender-code3/data'
PROJECT_FILTER = 'Montreal_1772509'  # Nom du projet
BUILDING_FILTER = 'MDA-Nicolet'      # Nom du bâtiment
DISCIPLINE_FILTER = 'STR'            # Discipline à importer (STR, MEP, ARC, ou None pour tout)
STOREY_FILTER = 'NIVEAU 3'           # Niveau spécifique ou None pour tout

# === CHEMINS DYNAMIQUES ===
PROJECT_PATH = os.path.join(BASE_LIBRARY, PROJECT_FILTER)
BUILDING_DISCIPLINE_PATH = os.path.join(PROJECT_PATH, f"{BUILDING_FILTER}_{DISCIPLINE_FILTER}")
INDEX_PATH = os.path.join(BUILDING_DISCIPLINE_PATH, 'index.json')
GLB_DIR = os.path.join(BUILDING_DISCIPLINE_PATH, 'glb')

# === LECTURE DE L'INDEX ===
if not os.path.exists(INDEX_PATH):
    print(f"❌ Fichier index non trouvé : {INDEX_PATH}")
    print(f"   Vérifiez que le chemin existe : {BUILDING_DISCIPLINE_PATH}")
    exit()

with open(INDEX_PATH, 'r') as f:
    index = json.load(f)

# Grouper les éléments par (discipline, storey, glb_path)
batch_map = {}
for item in index:
    # Appliquer les filtres
    if STOREY_FILTER and STOREY_FILTER not in item['storey']:
        continue
    if DISCIPLINE_FILTER and DISCIPLINE_FILTER not in item['discipline']:
        continue
    
    key = (item['discipline'], item['storey'], item['glb_path'])
    if key not in batch_map:
        batch_map[key] = []
    batch_map[key].append(item)

print(f"📦 Import de {len(batch_map)} lots après filtrage...")
print(f"   Projet: {PROJECT_FILTER}")
print(f"   Bâtiment: {BUILDING_FILTER}")
print(f"   Discipline: {DISCIPLINE_FILTER}")
print(f"   Niveau: {STOREY_FILTER or 'Tous'}")

for (discipline, storey, glb_path), items in batch_map.items():
    # Nettoyer le nom du niveau en enlevant 'IfcBuildingStorey/'
    clean_storey = storey.replace('IfcBuildingStorey/', '').replace('/STR', '').replace('/INT', '')
    
    # Créer la collection BUILDING_FILTER/DISCIPLINE_FILTER/STOREY_FILTER
    coll_name = f"{BUILDING_FILTER}/{discipline}/{clean_storey}"
    if coll_name not in bpy.data.collections:
        new_coll = bpy.data.collections.new(coll_name)
        bpy.context.scene.collection.children.link(new_coll)
    else:
        new_coll = bpy.data.collections[coll_name]
    
    # Importer le .glb batch
    if not os.path.isabs(glb_path):
        glb_path = os.path.join(GLB_DIR, os.path.basename(glb_path))
    if glb_path and os.path.exists(glb_path):
        try:
            bpy.ops.import_scene.gltf(filepath=glb_path)
            imported_objs = [obj for obj in bpy.context.selected_objects]
            for obj in imported_objs:
                new_coll.objects.link(obj)
                if obj.name in bpy.context.scene.collection.objects:
                    bpy.context.scene.collection.objects.unlink(obj)
            print(f"✅ Importé batch : {glb_path} dans {coll_name}")
        except Exception as e:
            print(f"⚠️ Erreur lors de l'import de {glb_path} : {e}")
    else:
        print(f"❌ Fichier manquant : {glb_path}")

print(f"\n✅ Import batch terminé pour {len(batch_map)} lots.") 