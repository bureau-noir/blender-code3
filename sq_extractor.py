import bpy  # type: ignore
import os
import sqlite3
import json
from datetime import datetime

# === CONFIGURATION GLOBALE ===
BASE_EXPORT = '/Users/PeteTurcotte/Dropbox/Cursor/blender-code3/data'

# === FILTRES D'EXTRACTION ===
PROJECT_FILTER = 'Montreal_1772509'   # Nom du projet à extraire (ex: 'Montreal_1772509')
BUILDING_FILTER = 'MDA-Nicolet'       # Nom du bâtiment à extraire (ex: 'MDA-Nicolet')
DISCIPLINE_FILTER = 'STR'             # Discipline à extraire (ex: 'STR', 'MEP', 'ARC', ou None pour tout)
COLLECTION_FILTER = None               # Nom exact de la collection à extraire (ex: 'IfcProject/527508', ou None pour auto)

# === COLLECTIONS À EXTRAIRE (calculées automatiquement) ===
def get_collections_to_extract():
    collections = []
    
    # Si COLLECTION_FILTER est spécifié, utiliser directement ce nom (même si bizarre)
    if COLLECTION_FILTER:
        if COLLECTION_FILTER in bpy.data.collections:
            collections.append(COLLECTION_FILTER)
            print(f"🎯 Collection spécifiée : {COLLECTION_FILTER}")
        else:
            print(f"❌ Collection spécifiée non trouvée : {COLLECTION_FILTER}")
            print(f"   Collections disponibles :")
            for coll in bpy.data.collections:
                if coll.name.startswith('IfcProject/'):
                    print(f"   - {coll.name}")
        return collections
    
    # Sinon, utiliser la logique de filtrage automatique
    if PROJECT_FILTER and BUILDING_FILTER and DISCIPLINE_FILTER:
        # Extraire le numéro de projet du PROJECT_FILTER (ex: Montreal_1772509 -> 1772509)
        project_id = PROJECT_FILTER.split('_')[-1] if '_' in PROJECT_FILTER else PROJECT_FILTER
        collection_name = f'IfcProject/{project_id}/{DISCIPLINE_FILTER}'
        if collection_name in bpy.data.collections:
            collections.append(collection_name)
        else:
            print(f"⚠️ Collection non trouvée : {collection_name}")
    elif PROJECT_FILTER and DISCIPLINE_FILTER:
        # Extraire toutes les disciplines du projet
        project_id = PROJECT_FILTER.split('_')[-1] if '_' in PROJECT_FILTER else PROJECT_FILTER
        for coll in bpy.data.collections:
            if coll.name.startswith(f'IfcProject/{project_id}/'):
                collections.append(coll.name)
    elif PROJECT_FILTER:
        # Extraire tout le projet
        project_id = PROJECT_FILTER.split('_')[-1] if '_' in PROJECT_FILTER else PROJECT_FILTER
        for coll in bpy.data.collections:
            if coll.name.startswith(f'IfcProject/{project_id}/'):
                collections.append(coll.name)
    else:
        # Extraire tous les projets
        for coll in bpy.data.collections:
            if coll.name.startswith('IfcProject/'):
                collections.append(coll.name)
    
    # Si aucune collection trouvée avec les filtres, mais qu'il n'y a qu'une seule collection IfcProject, la sélectionner automatiquement
    if not collections:
        ifc_collections = [coll.name for coll in bpy.data.collections if coll.name.startswith('IfcProject/')]
        if len(ifc_collections) == 1:
            collections = ifc_collections
            print(f"🎯 Collection unique détectée et sélectionnée automatiquement : {collections[0]}")
        elif len(ifc_collections) > 1:
            print(f"⚠️ Plusieurs collections IfcProject trouvées, aucune sélectionnée automatiquement :")
            for coll in ifc_collections:
                print(f"   - {coll}")
            print(f"   Spécifiez COLLECTION_FILTER pour choisir une collection spécifique")
        else:
            print(f"❌ Aucune collection IfcProject trouvée dans la scène")
    
    return collections

COLLECTIONS_TO_EXTRACT = get_collections_to_extract()

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

print(f"🔍 Extraction configurée :")
print(f"   Projet: {PROJECT_FILTER or 'Tous'}")
print(f"   Bâtiment: {BUILDING_FILTER or 'Tous'}")
print(f"   Discipline: {DISCIPLINE_FILTER or 'Toutes'}")
print(f"   Collections trouvées: {len(COLLECTIONS_TO_EXTRACT)}")

for coll_name in COLLECTIONS_TO_EXTRACT:
    coll = bpy.data.collections.get(coll_name)
    if not coll:
        print(f"❌ Collection non trouvée : {coll_name}")
        continue
    
    # Utiliser les filtres configurés pour la structure de dossiers
    if PROJECT_FILTER:
        project_name = PROJECT_FILTER.replace(' ', '_')
    else:
        # Fallback : extraire du nom de collection si pas de filtre
        project_id = coll_name.split('/')[1] if '/' in coll_name else 'unknown'
        project_name = f"Project_{project_id}"
    
    if BUILDING_FILTER and DISCIPLINE_FILTER:
        building_discipline_name = f"{BUILDING_FILTER}_{DISCIPLINE_FILTER}".replace(' ', '_')
    elif BUILDING_FILTER:
        building_discipline_name = BUILDING_FILTER.replace(' ', '_')
    elif DISCIPLINE_FILTER:
        building_discipline_name = DISCIPLINE_FILTER.replace(' ', '_')
    else:
        # Fallback : extraire du nom de collection si pas de filtre
        building_discipline_name = 'Building_Discipline'
    
    print(f"📁 Structure basée sur les filtres :")
    print(f"   Projet: {project_name}")
    print(f"   Bâtiment_Discipline: {building_discipline_name}")
    
    # Créer la structure de dossiers simplifiée : PROJECT/BUILDING_DISCIPLINE
    project_dir = os.path.join(BASE_EXPORT, project_name)
    building_discipline_dir = os.path.join(project_dir, building_discipline_name)
    glb_dir = os.path.join(building_discipline_dir, 'glb')
    os.makedirs(glb_dir, exist_ok=True)
    db_path = os.path.join(building_discipline_dir, 'bim_library.sqlite')
    log_path = os.path.join(building_discipline_dir, 'log.txt')
    index_path = os.path.join(building_discipline_dir, 'index.json')
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
    discipline_name = DISCIPLINE_FILTER or 'unknown'
    with open(log_path, 'a') as log:
        log.write(f"\nExtraction {datetime.now().isoformat()} - Discipline: {discipline_name}\n")
    print(f"Extraction de la discipline : {discipline_name} dans {building_discipline_dir}")
    index_list = []
    # --- Nouvelle logique : batch par niveau ---
    for storey_coll in [c for c in coll.children if c.name.startswith('IfcBuildingStorey')]:
        storey = storey_coll.name.replace('IfcBuildingStorey/', '').replace('/STR','').replace('/INT','')
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
        discipline = DISCIPLINE_FILTER or 'unknown'
        glb_filename = f"{discipline}_{storey.replace(' ', '_')}.glb"  # Garder le préfixe discipline
        glb_path = os.path.join(glb_dir, glb_filename)
        # Supprimer cette ligne qui crée un sous-dossier inutile
        # os.makedirs(os.path.dirname(glb_path), exist_ok=True)
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
    print(f"\n✅ Extraction terminée pour {discipline} dans {building_discipline_dir}")
    with open(log_path, 'a') as log:
        log.write(f"\n✅ Extraction terminée pour {discipline} dans {building_discipline_dir}\n")
    conn.close() 