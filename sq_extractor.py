import bpy
import os
import sqlite3
import json
from datetime import datetime

# === CONFIGURATION GLOBALE ===
BASE_EXPORT = '/Users/PeteTurcotte/Dropbox/Cursor/blender-code3'
COLLECTIONS_TO_EXTRACT = [
    'IfcProject/1772509/STR',
    # Ajouter d'autres disciplines si besoin
]

# === OUTIL POUR EXTRAIRE LES PROPRIÉTÉS IFC (filtrage des types simples) ===
def get_ifc_properties(obj):
    props = {}
    if hasattr(obj, 'BIMObjectProperties'):
        bim_props = obj.BIMObjectProperties
        if isinstance(bim_props, (list, tuple)):
            for pset in bim_props:
                if hasattr(pset, 'properties'):
                    for prop in pset.properties:
                        if isinstance(prop.value, (str, int, float, bool)):
                            props[prop.name] = str(prop.value)
        elif hasattr(bim_props, 'properties'):
            for prop in bim_props.properties:
                if isinstance(prop.value, (str, int, float, bool)):
                    props[prop.name] = str(prop.value)
    for k, v in obj.items():
        if k not in {'_RNA_UI'} and isinstance(v, (str, int, float, bool)):
            props[k] = str(v)
    return props

def clean_bim_properties(obj):
    bim_properties_to_remove = [
        'BIMObjectProperties', 'BIMProperties', 'DocProperties', 
        'BIMGeoreferenceProperties', 'BIMAggregateProperties', 'BIMNestProperties',
        'BIMModelProperties', 'WebProperties', 'BIMProjectProperties', 
        'BIMSystemProperties', 'BIMDebugProperties', 'DiffProperties',
        'BIMSpatialDecompositionProperties', 'BIMRootProperties', 'BIMGridProperties',
        'BIMGeometryProperties', 'BIMSearchProperties', 'GlobalPsetProperties',
        'BIMQtoProperties', 'BIMMaterialProperties', 'BIMStylesProperties',
        'BIMProfileProperties', 'BIMClassificationProperties', 'BIMBSDDProperties',
        'BIMClassificationReferenceProperties'
    ]
    for prop_name in bim_properties_to_remove:
        if hasattr(obj, prop_name):
            try:
                delattr(obj, prop_name)
            except:
                pass

def get_hierarchy_info(coll):
    site_name = project_id = building_name = None
    for sub in coll.children:
        if sub.name.startswith('IfcSite'):
            site_name = sub.name.split('/', 1)[-1].replace('/STR','').replace('/INT','')
        if sub.name.startswith('IfcBuilding'):
            building_name = sub.name.split('/', 1)[-1].replace('/STR','').replace('/INT','')
    if coll.name.startswith('IfcProject'):
        project_id = coll.name.split('/')[1].replace('/STR','').replace('/INT','')
    return site_name, project_id, building_name

for coll_name in COLLECTIONS_TO_EXTRACT:
    coll = bpy.data.collections.get(coll_name)
    if not coll:
        print(f"❌ Collection non trouvée : {coll_name}")
        continue
    discipline = coll_name.split('/')[-1]
    site_name, project_id, building_name = get_hierarchy_info(coll)
    if not (site_name and project_id and building_name):
        print(f"❌ Impossible de déterminer la hiérarchie pour {coll_name}")
        continue
    site_name_clean = site_name.replace(' ', '_')
    building_name_clean = building_name.replace(' ', '_')
    project_dir = os.path.join(BASE_EXPORT, f"{site_name_clean}_{project_id}")
    bldg_disc_dir = os.path.join(project_dir, f"{building_name_clean}_{discipline}")
    glb_dir = os.path.join(bldg_disc_dir, 'glb')
    os.makedirs(glb_dir, exist_ok=True)
    db_path = os.path.join(bldg_disc_dir, 'bim_library.sqlite')
    log_path = os.path.join(bldg_disc_dir, 'log.txt')
    index_path = os.path.join(bldg_disc_dir, 'index.json')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ifc_element (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        global_id TEXT,
        name TEXT,
        type TEXT,
        storey TEXT,
        discipline TEXT,
        glb_path TEXT,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS ifc_property (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        element_id INTEGER,
        name TEXT,
        value TEXT,
        FOREIGN KEY(element_id) REFERENCES ifc_element(id)
    )''')
    conn.commit()
    with open(log_path, 'a') as log:
        log.write(f"\nExtraction {datetime.now().isoformat()} - Discipline: {discipline}\n")
    print(f"Extraction de la discipline : {discipline} dans {bldg_disc_dir}")
    index_list = []
    # --- Nouvelle logique : batch par niveau ---
    for storey_coll in [c for c in coll.children if c.name.startswith('IfcBuildingStorey')]:
        storey = storey_coll.name.replace('/STR','').replace('/INT','')
        print(f"  → Traitement de l'étage : {storey}")
        with open(log_path, 'a') as log:
            log.write(f"  → Étape : {storey}\n")
        # Sélectionner tous les objets MESH de ce niveau (tous types)
        objs = [obj for obj in storey_coll.all_objects if obj.type == 'MESH']
        if not objs:
            continue
        # Nettoyer les propriétés BIM
        for obj in objs:
            clean_bim_properties(obj)
        # Sélectionner tous les objets pour export batch
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objs:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        # Exporter en un seul .glb
        glb_filename = f"{discipline}_{storey.replace(' ', '_')}.glb"
        glb_path = os.path.join(glb_dir, glb_filename)
        os.makedirs(os.path.dirname(glb_path), exist_ok=True)  # Correction ici
        try:
            bpy.ops.export_scene.gltf(
                filepath=glb_path,
                export_apply=True,
                export_yup=True,
                export_format='GLB',
                use_selection=True,
                export_materials='EXPORT',
                export_extras=False
            )
            print(f"    ✅ Export batch : {glb_path}")
            with open(log_path, 'a') as log:
                log.write(f"    ✅ Export batch : {glb_path}\n")
        except Exception as e:
            print(f"    ❌ Erreur export GLB batch pour {storey} : {e}")
            with open(log_path, 'a') as log:
                log.write(f"    ❌ Erreur export GLB batch pour {storey} : {e}\n")
            glb_path = ''
        # Indexer tous les objets du batch
        conn.execute('BEGIN TRANSACTION')
        types_in_batch = set()
        for obj in objs:
            name = obj.name
            global_id = obj.get('GlobalId', '')
            obj_type = obj.type
            types_in_batch.add(obj_type)
            c.execute('''INSERT INTO ifc_element (global_id, name, type, storey, discipline, glb_path, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (global_id, name, obj_type, storey, discipline, glb_path, datetime.now().isoformat()))
            element_id = c.lastrowid
            props = get_ifc_properties(obj)
            for prop_name, prop_value in props.items():
                c.execute('''INSERT INTO ifc_property (element_id, name, value) VALUES (?, ?, ?)''',
                    (element_id, prop_name, prop_value))
            index_list.append({
                "name": name,
                "storey": storey,
                "type": obj_type,
                "discipline": discipline,
                "glb_path": glb_path,
                "global_id": global_id,
                "properties": props
            })
        conn.commit()
        print(f"  ✅ Batch export terminé pour l'étage : {storey}")
        with open(log_path, 'a') as log:
            log.write(f"  ✅ Batch export terminé pour l'étage : {storey}\n")
    # Écriture de l'index JSON
    with open(index_path, 'w') as f:
        json.dump(index_list, f, indent=2)
    print(f"✅ Index JSON généré : {index_path}")
    print(f"\n✅ Extraction terminée pour {discipline} dans {bldg_disc_dir}")
    with open(log_path, 'a') as log:
        log.write(f"\n✅ Extraction terminée pour {discipline} dans {bldg_disc_dir}\n")
    conn.close() 