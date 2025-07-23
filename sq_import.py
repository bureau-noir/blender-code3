import bpy
import os
import json

# === CONFIGURATION ===
BASE_IMPORT = '/Users/PeteTurcotte/Dropbox/Cursor/blender-code3/Montreal_1772509/MDA-Nicolet_STR'
INDEX_PATH = os.path.join(BASE_IMPORT, 'index.json')
GLB_DIR = os.path.join(BASE_IMPORT, 'glb')

# === FILTRES D'IMPORT ===
# Laissez vide pour importer tous les niveaux, ou spécifiez un niveau
STOREY_FILTER = 'NIVEAU 3'  # Exemple : importer seulement NIVEAU 3
DISCIPLINE_FILTER = 'STR'    # Discipline à importer

# === LECTURE DE L'INDEX ===
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

for (discipline, storey, glb_path), items in batch_map.items():
    # Créer la collection Discipline/Niveau si elle n'existe pas
    coll_name = f"{discipline}/{storey}"
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