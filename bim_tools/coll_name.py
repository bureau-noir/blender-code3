# type: ignore
import bpy
import re
import sys
import os

# Ajoute automatiquement le dossier parent au PYTHONPATH si besoin
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_path not in sys.path:
    sys.path.append(project_path)

def clean_collection_name(name):
    """Nettoie le nom de collection pour éviter les doublons et incohérences"""
    # Supprimer les préfixes redondants
    if name.startswith("IfcBuildingStorey/IfcBuildingStorey/"):
        name = name.replace("IfcBuildingStorey/IfcBuildingStorey/", "IfcBuildingStorey/")
    return name

def rename_to_ifc_hierarchy(project_code, site_name, building_name, collection_name=None, level_map=None, discipline=None, dry_run=False):
    """
    Renomme récursivement la collection importée (collection_name) et tous ses enfants selon la hiérarchie IFC.
    Standardise les noms des niveaux (NIVEAU X, NIV_X, etc.) en IfcBuildingStorey/Niv_X/DISCIPLINE.
    Gère intelligemment les cas spéciaux comme FONDATIONS, NIVEAU TOIT, etc.
    Ne touche à rien d'autre dans le projet.
    """
    if not collection_name:
        print("collection_name doit être spécifié pour éviter d'impacter tout le projet !")
        return
    
    # Suffixe discipline (STR, MEP, ENV, etc.)
    discipline_suffix = f"/{discipline}" if discipline else ".001"
    
    root = bpy.data.collections.get(collection_name)
    if not root:
        print(f"Collection '{collection_name}' non trouvée.")
        return
    
    print(f"Renommage de la collection '{collection_name}' et ses enfants...")
    
    # 1. Renommer la collection racine
    if not dry_run:
        root.name = f"IfcProject/{project_code}{discipline_suffix}"
    print(f"  Collection racine: {collection_name} -> IfcProject/{project_code}{discipline_suffix}")
    
    # 2. Renommer récursivement tous les enfants
    def rename_children_recursive(col):
        for child in col.children:
            old_name = child.name
            new_name = None
            
            # Détecter et renommer les sites
            if "SITE" in child.name.upper() or "IfcSite" in child.name:
                new_name = f"IfcSite/{site_name}{discipline_suffix}"
                print(f"    Site: {old_name} -> {new_name}")
            
            # Détecter et renommer les bâtiments (mais PAS les niveaux)
            elif ("BUILDING" in child.name.upper() or "IfcBuilding" in child.name) and "STOREY" not in child.name.upper():
                new_name = f"IfcBuilding/{building_name}{discipline_suffix}"
                print(f"    Building: {old_name} -> {new_name}")
            
            # Détecter et renommer les niveaux (IfcBuildingStorey) selon leur contenu
            elif "STOREY" in child.name.upper() or child.name.startswith("IfcBuildingStorey/"):
                # Extraire le nom après "IfcBuildingStorey/"
                if "/" in child.name:
                    level_name = child.name.split("/", 1)[1]
                else:
                    level_name = child.name
                
                # Traiter les cas spéciaux
                if "FONDATION" in level_name.upper():
                    new_name = f"IfcBuildingStorey/Fond.{discipline_suffix}"
                    print(f"    Fondation: {old_name} -> {new_name}")
                
                elif "TOIT" in level_name.upper():
                    new_name = f"IfcBuildingStorey/Toit{discipline_suffix}"
                    print(f"    Toit: {old_name} -> {new_name}")
                
                elif "D.A." in level_name or "MARQUISE" in level_name.upper() or "SUP." in level_name.upper():
                    # Garder le nom original mais le standardiser
                    clean_name = level_name.replace(" ", "_").replace(".", "_")
                    new_name = f"IfcBuildingStorey/{clean_name}{discipline_suffix}"
                    print(f"    Élément spécial: {old_name} -> {new_name}")
                
                # Traiter les niveaux numériques (NIVEAU X)
                elif "NIVEAU" in level_name.upper():
                    level_match = re.search(r'(\d+(?:\.\d+)?)', level_name)
                    if level_match:
                        level_num = level_match.group(1)
                        new_name = f"IfcBuildingStorey/Niv_{level_num}{discipline_suffix}"
                        print(f"    Niveau: {old_name} -> {new_name}")
                    else:
                        # Si pas de numéro, utiliser le nom original nettoyé
                        clean_name = level_name.replace("NIVEAU ", "").replace(" ", "_")
                        new_name = f"IfcBuildingStorey/{clean_name}{discipline_suffix}"
                        print(f"    Niveau: {old_name} -> {new_name}")
                
                else:
                    # Cas par défaut pour les autres niveaux
                    clean_name = level_name.replace(" ", "_")
                    new_name = f"IfcBuildingStorey/{clean_name}{discipline_suffix}"
                    print(f"    Niveau: {old_name} -> {new_name}")
            
            # Appliquer le nouveau nom si trouvé
            if new_name:
                new_name = clean_collection_name(new_name)
                if not dry_run:
                    child.name = new_name
            
            # Continuer récursivement
            rename_children_recursive(child)
    
    rename_children_recursive(root)
    
    if dry_run:
        print("Mode DRY RUN - Aucun changement effectué")
    else:
        print("Renommage terminé !")

def rename_and_reorganize_ifc_collections(rename_map, hierarchy_order, dry_run=False):
    """
    Renomme les collections existantes selon rename_map et les réorganise selon hierarchy_order (liste de tuples parent/enfant).
    Ne crée aucune nouvelle collection, agit uniquement sur l'existant.
    """
    # Renommer les collections existantes
    for old_name, new_name in rename_map.items():
        col = bpy.data.collections.get(old_name)
        if col:
            if not dry_run:
                col.name = new_name
            print(f"Renommé: {old_name} -> {new_name}")
        else:
            print(f"Collection '{old_name}' non trouvée")
    # Réorganiser la hiérarchie IFC
    for parent_name, child_name in hierarchy_order:
        parent = bpy.data.collections.get(parent_name)
        child = bpy.data.collections.get(child_name)
        if parent and child:
            if child.name not in [c.name for c in parent.children]:
                if not dry_run:
                    parent.children.link(child)
                print(f"Ajouté: {child.name} sous {parent.name}")
        else:
            print(f"Parent '{parent_name}' ou enfant '{child_name}' non trouvé")

# Exemple d'utilisation :
# rename_to_ifc_hierarchy(
#     project_code="1772509",
#     site_name="Montreal",
#     building_name="MDA-Nicolet",
#     collection_name="IfcProject/1772509.001"
# )

# Exemple d'utilisation :
# rename_map = {
#     'IfcProject/My Project': 'IfcProject/1772509',
#     'IfcSite/My Site': 'IfcSite/Montreal',
#     'IfcBuilding/My Building': 'IfcBuilding/MDA-Nicolet',
#     'IfcBuildingStorey/My Storey': 'IfcBuildingStorey/Niv_1',
# }
# hierarchy_order = [
#     ('IfcProject/1772509', 'IfcSite/Montreal'),
#     ('IfcSite/Montreal', 'IfcBuilding/MDA-Nicolet'),
#     ('IfcBuilding/MDA-Nicolet', 'IfcBuildingStorey/Niv_1'),
# ]
# rename_and_reorganize_ifc_collections(rename_map, hierarchy_order) 