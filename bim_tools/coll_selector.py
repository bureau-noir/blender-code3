"""
Module de sélection de collections BIM
Outils robustes pour sélectionner complètement les collections et leurs éléments
"""

# Import conditionnel de bpy pour permettre l'import du module en dehors de Blender
BLENDER_AVAILABLE = False
try:
    import bpy  # type: ignore
    import mathutils  # type: ignore
    import time  # type: ignore
    BLENDER_AVAILABLE = True
except ImportError:
    print("⚠️  Blender non disponible - certaines fonctionnalités seront limitées")

from typing import Dict, List, Any, Optional, Tuple
import re


class CollectionSelector:
    """Classe pour la sélection robuste de collections BIM"""
    
    def __init__(self, debug=False):
        if not BLENDER_AVAILABLE:
            raise RuntimeError("Blender n'est pas disponible - impossible d'initialiser CollectionSelector")
        self.scene = bpy.context.scene
        self.selection_history = []
        self.debug = debug
        
    def select_collection_complete(self, collection_name: str, include_hidden: bool = False) -> Dict[str, Any]:
        """
        Sélectionne complètement une collection et tous ses éléments
        
        Args:
            collection_name: Nom de la collection à sélectionner
            include_hidden: Inclure les objets cachés
            
        Returns:
            Dict avec les informations de sélection
        """
        print(f"🎯 SÉLECTION COMPLÈTE DE LA COLLECTION: {collection_name}")
        
        # Désélectionner tout d'abord
        bpy.ops.object.select_all(action='DESELECT')
        
        # Trouver la collection
        collection = self._find_collection(collection_name)
        if not collection:
            return self._create_error_result(f"Collection '{collection_name}' non trouvée")
        
        # NOUVEAU : S'assurer que tous les objets sont dans le View Layer courant
        self._ensure_objects_in_view_layer()
        
        # Analyser la collection
        analysis = self._analyze_collection_structure(collection, include_hidden)
        
        # Sélectionner tous les objets
        selected_objects = self._select_all_objects_recursive(collection, include_hidden)
        
        # Attendre que la sélection soit bien prise en compte (max 10s)
        expected = len(selected_objects)
        for i in range(20):
            selected = len(bpy.context.selected_objects)
            if self.debug:
                print(f"Objets sélectionnés (sync): {selected}/{expected}")
            if selected >= expected:
                break
            time.sleep(0.5)
        # Forcer un refresh de la vue
        bpy.context.view_layer.update()
        print("Sélection terminée et synchronisée.")
        
        # Créer le résultat
        result = {
            'success': True,
            'collection_name': collection_name,
            'total_selected': len(selected_objects),
            'analysis': analysis,
            'selected_objects': [obj.name for obj in selected_objects],
            'selection_details': self._get_selection_details(selected_objects)
        }
        
        print(f"✅ SÉLECTION TERMINÉE: {len(selected_objects)} objets sélectionnés")
        return result
    
    def _find_collection(self, collection_name: str) -> Optional['bpy.types.Collection']:
        """Trouve une collection par nom (support des patterns)"""
        collections = bpy.data.collections
        
        # Recherche exacte
        for collection in collections:
            if collection.name == collection_name:
                return collection
        
        # Recherche par pattern (ex: "IfcProject/527508.003")
        for collection in collections:
            if collection_name in collection.name:
                print(f"   Collection trouvée par pattern: {collection.name}")
                return collection
        
        return None
    
    def _analyze_collection_structure(self, collection: 'bpy.types.Collection', include_hidden: bool) -> Dict[str, Any]:
        """Analyse la structure d'une collection"""
        analysis = {
            'collection_name': collection.name,
            'direct_objects': 0,
            'sub_collections': len(collection.children),
            'total_objects': 0,
            'by_type': {},
            'by_category': {},
            'visibility_issues': []
        }
        
        def analyze_recursive(col):
            # Objets directs
            for obj in col.objects:
                if include_hidden or obj.visible_get():
                    analysis['total_objects'] += 1
                    if col == collection:  # Seulement pour la collection principale
                        analysis['direct_objects'] += 1
                    
                    # Compter par type
                    obj_type = obj.type
                    analysis['by_type'][obj_type] = analysis['by_type'].get(obj_type, 0) + 1
                    
                    # Compter par catégorie IFC
                    ifc_category = self._extract_ifc_category(obj.name)
                    if ifc_category:
                        analysis['by_category'][ifc_category] = analysis['by_category'].get(ifc_category, 0) + 1
                    
                    # Vérifier la visibilité
                    if not obj.visible_get():
                        analysis['visibility_issues'].append(obj.name)
                else:
                    analysis['visibility_issues'].append(obj.name)
            
            # Sous-collections
            for sub_col in col.children:
                analyze_recursive(sub_col)
        
        analyze_recursive(collection)
        return analysis
    
    def _select_all_objects_recursive(self, collection, include_hidden=True):
        """
        Sélectionne récursivement tous les objets dans une collection et ses sous-collections.
        Force la sélection même des objets avec hide_select = True.
        Retourne la liste des objets sélectionnés.
        """
        selected_objects = []
        original_hide_select_states = {}
        
        # Sélectionner tous les objets dans cette collection
        for obj in collection.objects:
            # Sauvegarder l'état original de hide_select
            original_hide_select_states[obj.name] = obj.hide_select
            # Forcer la sélection en désactivant temporairement hide_select et en rendant visible
            obj.hide_set(False)
            obj.hide_viewport = False
            obj.hide_select = False
            try:
                obj.select_set(True)
                selected_objects.append(obj)
            except Exception:
                pass
            # Restaurer l'état original
            obj.hide_select = original_hide_select_states[obj.name]
        
        # Sélectionner récursivement dans les sous-collections
        for child_col in collection.children:
            selected_objects.extend(self._select_all_objects_recursive(child_col, include_hidden))
        
        return selected_objects
    
    def _extract_ifc_category(self, object_name: str) -> Optional[str]:
        """Extrait la catégorie IFC depuis le nom de l'objet"""
        if 'Ifc' in object_name:
            # Extraire le type IFC (ex: IfcColumn, IfcBeam, etc.)
            parts = object_name.split('/')
            for part in parts:
                if part.startswith('Ifc'):
                    return part
        return None
    
    def _get_selection_details(self, selected_objects: List['bpy.types.Object']) -> Dict[str, Any]:
        """Obtient les détails de la sélection"""
        details = {
            'mesh_objects': [],
            'empty_objects': [],
            'other_objects': [],
            'ifc_types': {},
            'position_range': {'min': [float('inf')]*3, 'max': [float('-inf')]*3}
        }
        
        for obj in selected_objects:
            # Catégoriser par type
            if obj.type == 'MESH':
                details['mesh_objects'].append(obj.name)
            elif obj.type == 'EMPTY':
                details['empty_objects'].append(obj.name)
            else:
                details['other_objects'].append(obj.name)
            
            # Compter les types IFC
            ifc_type = self._extract_ifc_category(obj.name)
            if ifc_type:
                details['ifc_types'][ifc_type] = details['ifc_types'].get(ifc_type, 0) + 1
            
            # Calculer la plage de positions
            for i in range(3):
                details['position_range']['min'][i] = min(details['position_range']['min'][i], obj.location[i])
                details['position_range']['max'][i] = max(details['position_range']['max'][i], obj.location[i])
        
        return details
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Crée un résultat d'erreur"""
        return {
            'success': False,
            'error': error_message,
            'total_selected': 0,
            'analysis': {},
            'selected_objects': [],
            'selection_details': {}
        }
    
    def select_by_pattern(self, pattern: str, include_hidden: bool = False) -> Dict[str, Any]:
        """
        Sélectionne les collections correspondant à un pattern
        
        Args:
            pattern: Pattern de recherche (ex: "IfcProject/527508")
            include_hidden: Inclure les objets cachés
            
        Returns:
            Dict avec les résultats de sélection
        """
        print(f"🔍 SÉLECTION PAR PATTERN: {pattern}")
        
        matching_collections = []
        for collection in bpy.data.collections:
            if pattern in collection.name:
                matching_collections.append(collection.name)
        
        if not matching_collections:
            return self._create_error_result(f"Aucune collection trouvée pour le pattern: {pattern}")
        
        results = {}
        for collection_name in matching_collections:
            results[collection_name] = self.select_collection_complete(collection_name, include_hidden)
        
        return {
            'success': True,
            'pattern': pattern,
            'matching_collections': matching_collections,
            'results': results
        }
    
    def select_structure_layer(self, include_hidden: bool = False) -> Dict[str, Any]:
        """Sélectionne spécifiquement la couche structure"""
        return self.select_by_pattern("IfcProject/527508.003", include_hidden)
    
    def select_envelope_layer(self, include_hidden: bool = False) -> Dict[str, Any]:
        """Sélectionne spécifiquement la couche enveloppe"""
        return self.select_by_pattern("IfcProject/525519", include_hidden)
    
    def validate_selection(self, expected_types: List[str] = None) -> Dict[str, Any]:
        """
        Valide la sélection actuelle
        
        Args:
            expected_types: Types d'éléments attendus
            
        Returns:
            Dict avec les résultats de validation
        """
        selected_objects = [obj for obj in bpy.context.selected_objects]
        
        validation = {
            'total_selected': len(selected_objects),
            'by_type': {},
            'by_ifc_category': {},
            'missing_types': [],
            'warnings': []
        }
        
        # Analyser la sélection
        for obj in selected_objects:
            # Par type Blender
            obj_type = obj.type
            validation['by_type'][obj_type] = validation['by_type'].get(obj_type, 0) + 1
            
            # Par catégorie IFC
            ifc_category = self._extract_ifc_category(obj.name)
            if ifc_category:
                validation['by_ifc_category'][ifc_category] = validation['by_ifc_category'].get(ifc_category, 0) + 1
        
        # Vérifier les types attendus
        if expected_types:
            for expected_type in expected_types:
                if expected_type not in validation['by_ifc_category']:
                    validation['missing_types'].append(expected_type)
        
        # Générer des avertissements
        if validation['total_selected'] == 0:
            validation['warnings'].append("Aucun objet sélectionné")
        
        if 'EMPTY' not in validation['by_type']:
            validation['warnings'].append("Aucun empty sélectionné")
        
        return validation

    def _ensure_objects_in_view_layer(self) -> int:
        """
        S'assure que tous les objets de la scène sont dans le View Layer courant
        Retourne le nombre d'objets liés
        """
        view_layer = bpy.context.view_layer
        linked_count = 0
        
        # Lier TOUS les objets de la scène au View Layer courant
        for obj in bpy.data.objects:
            # Exclure les objets de type IFC (définitions, pas instances)
            if obj.users_collection and any('IfcTypeProduct' in col.name for col in obj.users_collection):
                continue
                
            # Vérifier si l'objet est déjà dans le View Layer
            if obj.name not in view_layer.objects:
                try:
                    # Lier l'objet au View Layer
                    view_layer.objects.link(obj)
                    linked_count += 1
                    print(f"   🔗 Lié au View Layer: {obj.name}")
                except Exception as e:
                    print(f"   ⚠️  Impossible de lier {obj.name}: {e}")
        
        print(f"   📊 {linked_count} objets liés au View Layer")
        return linked_count


def create_collection_selector() -> CollectionSelector:
    """Factory function pour créer un sélecteur de collection"""
    return CollectionSelector() 