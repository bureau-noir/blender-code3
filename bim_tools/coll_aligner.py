"""
Module d'alignement de collections BIM
Outils pour analyser et aligner les positions des collections Structure et Enveloppe
"""

# Import conditionnel de bpy pour permettre l'import du module en dehors de Blender
BLENDER_AVAILABLE = False
try:
    import bpy  # type: ignore
    import mathutils  # type: ignore
    BLENDER_AVAILABLE = True
except ImportError:
    print("⚠️  Blender non disponible - certaines fonctionnalités seront limitées")

from typing import Dict, List, Any, Optional, Tuple
import re
import math


class CollAligner:
    """Classe pour analyser et aligner les distances entre collections BIM"""
    
    def __init__(self, debug=False):
        if not BLENDER_AVAILABLE:
            raise RuntimeError("Blender n'est pas disponible - impossible d'initialiser CollAligner")
        self.scene = bpy.context.scene
        self.debug = debug
        
    def analyze_collections_distance(self, collection1_name: str, collection2_name: str) -> Dict[str, Any]:
        """
        Analyse la distance entre deux collections BIM
        
        Args:
            collection1_name: Nom de la première collection (ex: "IfcProject/527508.003")
            collection2_name: Nom de la deuxième collection (ex: "IfcProject/525519")
            
        Returns:
            Dict avec l'analyse complète des distances
        """
        print(f"🔍 ANALYSE DE DISTANCE ENTRE COLLECTIONS")
        print(f"   Collection 1: {collection1_name}")
        print(f"   Collection 2: {collection2_name}")
        
        # Trouver les collections
        collection1 = self._find_collection(collection1_name)
        collection2 = self._find_collection(collection2_name)
        
        if not collection1:
            return self._create_error_result(f"Collection '{collection1_name}' non trouvée")
        if not collection2:
            return self._create_error_result(f"Collection '{collection2_name}' non trouvée")
        
        # Analyser les collections
        analysis1 = self._analyze_collection_positions(collection1, "Collection 1")
        analysis2 = self._analyze_collection_positions(collection2, "Collection 2")
        
        # Calculer les distances
        distance_analysis = self._calculate_collections_distance(analysis1, analysis2)
        
        # Résultat complet
        result = {
            'success': True,
            'collection1': {
                'name': collection1_name,
                'analysis': analysis1
            },
            'collection2': {
                'name': collection2_name,
                'analysis': analysis2
            },
            'distance_analysis': distance_analysis,
            'alignment_recommendations': self._generate_alignment_recommendations(distance_analysis)
        }
        
        self._print_analysis_summary(result)
        return result
    
    def list_available_collections(self) -> List[str]:
        """Liste toutes les collections disponibles dans la scène"""
        collections = []
        for collection in bpy.data.collections:
            collections.append(collection.name)
        return collections
    
    def find_collections_by_pattern(self, pattern: str) -> List[str]:
        """Trouve toutes les collections correspondant à un pattern"""
        matching_collections = []
        for collection in bpy.data.collections:
            if pattern.lower() in collection.name.lower():
                matching_collections.append(collection.name)
        return matching_collections
    
    def analyze_multiple_collections(self, collection_names: List[str]) -> Dict[str, Any]:
        """
        Analyse les distances entre plusieurs collections
        
        Args:
            collection_names: Liste des noms de collections à analyser
            
        Returns:
            Dict avec l'analyse complète de toutes les paires
        """
        print(f"🔍 ANALYSE MULTIPLE DE {len(collection_names)} COLLECTIONS")
        
        results = {}
        comparisons = []
        
        # Analyser chaque paire de collections
        for i in range(len(collection_names)):
            for j in range(i + 1, len(collection_names)):
                col1 = collection_names[i]
                col2 = collection_names[j]
                
                print(f"\n📊 Comparaison: {col1} ↔ {col2}")
                result = self.analyze_collections_distance(col1, col2)
                comparisons.append({
                    'collection1': col1,
                    'collection2': col2,
                    'result': result
                })
        
        # Résumé global
        total_distance = sum(comp['result']['distance_analysis']['center_distance'] 
                           for comp in comparisons if comp['result']['success'])
        avg_distance = total_distance / len(comparisons) if comparisons else 0
        
        return {
            'success': True,
            'collections_analyzed': collection_names,
            'comparisons': comparisons,
            'summary': {
                'total_comparisons': len(comparisons),
                'average_distance': avg_distance,
                'recommendations': self._generate_global_recommendations(comparisons)
            }
        }
    
    def _generate_global_recommendations(self, comparisons: List[Dict]) -> List[str]:
        """Génère des recommandations globales basées sur toutes les comparaisons"""
        recommendations = []
        
        # Analyser les distances moyennes
        distances = [comp['result']['distance_analysis']['center_distance'] 
                   for comp in comparisons if comp['result']['success']]
        
        if distances:
            avg_distance = sum(distances) / len(distances)
            max_distance = max(distances)
            
            if avg_distance > 100:
                recommendations.append(f"Distance moyenne élevée: {avg_distance:.1f}m")
            
            if max_distance > 200:
                recommendations.append(f"Distance maximale importante: {max_distance:.1f}m")
        
        return recommendations

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Obtient des informations détaillées sur une collection spécifique
        
        Args:
            collection_name: Nom de la collection
            
        Returns:
            Dict avec les informations de la collection
        """
        collection = self._find_collection(collection_name)
        if not collection:
            return {'success': False, 'error': f"Collection '{collection_name}' non trouvée"}
        
        analysis = self._analyze_collection_positions(collection, collection_name)
        
        return {
            'success': True,
            'collection_name': collection_name,
            'total_objects': analysis['total_objects'],
            'empty_objects': len(analysis['empty_objects']),
            'mesh_objects': len(analysis['mesh_objects']),
            'center': analysis['position_stats']['center'],
            'bounds': analysis['position_stats']['bounds'],
            'ifc_categories': analysis['ifc_categories'],
            'key_reference_points': len(analysis['key_reference_points'])
        }
    
    def _find_collection(self, collection_name: str) -> Optional['bpy.types.Collection']:
        """Trouve une collection par nom (support des patterns)"""
        collections = bpy.data.collections
        
        # Recherche exacte
        for collection in collections:
            if collection.name == collection_name:
                return collection
        
        # Recherche par pattern
        for collection in collections:
            if collection_name in collection.name:
                if self.debug:
                    print(f"   Collection trouvée par pattern: {collection.name}")
                return collection
        
        return None
    
    def _analyze_collection_positions(self, collection: 'bpy.types.Collection', label: str) -> Dict[str, Any]:
        """Analyse les positions des objets dans une collection"""
        analysis = {
            'collection_name': collection.name,
            'label': label,
            'total_objects': 0,
            'empty_objects': [],
            'mesh_objects': [],
            'position_stats': {
                'min': [float('inf')] * 3,
                'max': [float('-inf')] * 3,
                'center': [0.0] * 3,
                'bounds': {
                    'width': 0.0,
                    'height': 0.0,
                    'depth': 0.0
                }
            },
            'ifc_categories': {},
            'key_reference_points': []
        }
        
        def analyze_recursive(col):
            for obj in col.objects:
                analysis['total_objects'] += 1
                
                # Catégoriser par type
                if obj.type == 'EMPTY':
                    analysis['empty_objects'].append({
                        'name': obj.name,
                        'location': list(obj.location),
                        'ifc_category': self._extract_ifc_category(obj.name)
                    })
                elif obj.type == 'MESH':
                    analysis['mesh_objects'].append({
                        'name': obj.name,
                        'location': list(obj.location),
                        'ifc_category': self._extract_ifc_category(obj.name)
                    })
                
                # Analyser les positions
                if obj.location:
                    for i in range(3):
                        analysis['position_stats']['min'][i] = min(
                            analysis['position_stats']['min'][i], 
                            obj.location[i]
                        )
                        analysis['position_stats']['max'][i] = max(
                            analysis['position_stats']['max'][i], 
                            obj.location[i]
                        )
                
                # Compter les catégories IFC
                ifc_category = self._extract_ifc_category(obj.name)
                if ifc_category:
                    analysis['ifc_categories'][ifc_category] = analysis['ifc_categories'].get(ifc_category, 0) + 1
            
            # Récursif pour les sous-collections
            for child_col in col.children:
                analyze_recursive(child_col)
        
        analyze_recursive(collection)
        
        # Calculer le centre et les dimensions
        if analysis['total_objects'] > 0:
            for i in range(3):
                analysis['position_stats']['center'][i] = (
                    analysis['position_stats']['min'][i] + 
                    analysis['position_stats']['max'][i]
                ) / 2
            
            analysis['position_stats']['bounds']['width'] = (
                analysis['position_stats']['max'][0] - 
                analysis['position_stats']['min'][0]
            )
            analysis['position_stats']['bounds']['height'] = (
                analysis['position_stats']['max'][2] - 
                analysis['position_stats']['min'][2]
            )
            analysis['position_stats']['bounds']['depth'] = (
                analysis['position_stats']['max'][1] - 
                analysis['position_stats']['min'][1]
            )
        
        # Identifier les points de référence clés (empties importants)
        for empty in analysis['empty_objects']:
            if any(keyword in empty['name'] for keyword in ['IfcBuildingStorey', 'IfcSite', 'IfcBuilding']):
                analysis['key_reference_points'].append(empty)
        
        return analysis
    
    def _calculate_collections_distance(self, analysis1: Dict[str, Any], analysis2: Dict[str, Any]) -> Dict[str, Any]:
        """Calcule les distances entre deux collections"""
        distance_analysis = {
            'center_distance': 0.0,
            'min_distance': 0.0,
            'max_distance': 0.0,
            'axis_distances': {
                'x': 0.0,
                'y': 0.0,
                'z': 0.0
            },
            'alignment_issues': [],
            'reference_point_distances': []
        }
        
        # Distance entre les centres
        center1 = analysis1['position_stats']['center']
        center2 = analysis2['position_stats']['center']
        
        distance_analysis['center_distance'] = math.sqrt(
            (center1[0] - center2[0])**2 + 
            (center1[1] - center2[1])**2 + 
            (center1[2] - center2[2])**2
        )
        
        # Distances par axe
        for i, axis in enumerate(['x', 'y', 'z']):
            distance_analysis['axis_distances'][axis] = abs(center1[i] - center2[i])
        
        # Distance minimale et maximale entre les boîtes englobantes
        min1 = analysis1['position_stats']['min']
        max1 = analysis1['position_stats']['max']
        min2 = analysis2['position_stats']['min']
        max2 = analysis2['position_stats']['max']
        
        # Calculer la distance minimale entre les boîtes
        min_distance = 0.0
        for i in range(3):
            if max1[i] < min2[i] or max2[i] < min1[i]:
                # Les boîtes ne se chevauchent pas sur cet axe
                min_distance += min(abs(max1[i] - min2[i]), abs(max2[i] - min1[i]))**2
        distance_analysis['min_distance'] = math.sqrt(min_distance)
        
        # Distance maximale (coins opposés)
        max_distance = 0.0
        for i in range(3):
            max_distance += max(abs(max1[i] - min2[i]), abs(max2[i] - min1[i]))**2
        distance_analysis['max_distance'] = math.sqrt(max_distance)
        
        # Analyser les distances entre points de référence
        for ref1 in analysis1['key_reference_points']:
            for ref2 in analysis2['key_reference_points']:
                if ref1['ifc_category'] == ref2['ifc_category']:
                    distance = math.sqrt(
                        (ref1['location'][0] - ref2['location'][0])**2 +
                        (ref1['location'][1] - ref2['location'][1])**2 +
                        (ref1['location'][2] - ref2['location'][2])**2
                    )
                    distance_analysis['reference_point_distances'].append({
                        'category': ref1['ifc_category'],
                        'object1': ref1['name'],
                        'object2': ref2['name'],
                        'distance': distance
                    })
        
        # Identifier les problèmes d'alignement
        if distance_analysis['center_distance'] > 100:  # Plus de 100m de distance
            distance_analysis['alignment_issues'].append("Distance importante entre les centres")
        
        if distance_analysis['axis_distances']['z'] > 50:  # Plus de 50m de différence en hauteur
            distance_analysis['alignment_issues'].append("Différence importante en hauteur (axe Z)")
        
        return distance_analysis
    
    def _generate_alignment_recommendations(self, distance_analysis: Dict[str, Any]) -> List[str]:
        """Génère des recommandations d'alignement basées sur l'analyse"""
        recommendations = []
        
        if distance_analysis['center_distance'] > 100:
            recommendations.append(f"Alignement des centres: Déplacer une collection de {distance_analysis['center_distance']:.1f}m")
        
        if distance_analysis['axis_distances']['z'] > 50:
            recommendations.append(f"Alignement vertical: Corriger la différence de {distance_analysis['axis_distances']['z']:.1f}m en hauteur")
        
        if distance_analysis['axis_distances']['x'] > 50:
            recommendations.append(f"Alignement X: Corriger la différence de {distance_analysis['axis_distances']['x']:.1f}m")
        
        if distance_analysis['axis_distances']['y'] > 50:
            recommendations.append(f"Alignement Y: Corriger la différence de {distance_analysis['axis_distances']['y']:.1f}m")
        
        if not recommendations:
            recommendations.append("Les collections semblent bien alignées")
        
        return recommendations
    
    def _extract_ifc_category(self, object_name: str) -> Optional[str]:
        """Extrait la catégorie IFC depuis le nom de l'objet"""
        if 'Ifc' in object_name:
            parts = object_name.split('/')
            for part in parts:
                if part.startswith('Ifc'):
                    return part
        return None
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Crée un résultat d'erreur"""
        return {
            'success': False,
            'error': error_message,
            'collection1': {},
            'collection2': {},
            'distance_analysis': {},
            'alignment_recommendations': []
        }
    
    def _print_analysis_summary(self, result: Dict[str, Any]):
        """Affiche un résumé de l'analyse"""
        if not result['success']:
            print(f"❌ ERREUR: {result['error']}")
            return
        
        print(f"\n📊 RÉSUMÉ DE L'ANALYSE:")
        print(f"   Collection 1: {result['collection1']['analysis']['collection_name']}")
        print(f"   Collection 2: {result['collection2']['analysis']['collection_name']}")
        print(f"   Distance entre centres: {result['distance_analysis']['center_distance']:.2f}m")
        print(f"   Distance minimale: {result['distance_analysis']['min_distance']:.2f}m")
        print(f"   Distance maximale: {result['distance_analysis']['max_distance']:.2f}m")
        
        print(f"\n📏 DISTANCES PAR AXE:")
        for axis, distance in result['distance_analysis']['axis_distances'].items():
            print(f"   {axis.upper()}: {distance:.2f}m")
        
        print(f"\n🎯 RECOMMANDATIONS:")
        for rec in result['alignment_recommendations']:
            print(f"   - {rec}")

    def analyze_precise_alignment(self, collection1_name: str, collection2_name: str, reference_category: str = "IfcBuildingStorey") -> Dict[str, Any]:
        """
        Analyse l'alignement précis basé sur des points de référence spécifiques
        
        Args:
            collection1_name: Nom de la première collection
            collection2_name: Nom de la deuxième collection
            reference_category: Catégorie IFC pour les points de référence (ex: "IfcBuildingStorey")
            
        Returns:
            Dict avec l'analyse précise d'alignement
        """
        print(f"🎯 ANALYSE D'ALIGNEMENT PRÉCIS")
        print(f"   Collection 1: {collection1_name}")
        print(f"   Collection 2: {collection2_name}")
        print(f"   Catégorie de référence: {reference_category}")
        
        # Trouver les collections
        collection1 = self._find_collection(collection1_name)
        collection2 = self._find_collection(collection2_name)
        
        if not collection1:
            return self._create_error_result(f"Collection '{collection1_name}' non trouvée")
        if not collection2:
            return self._create_error_result(f"Collection '{collection2_name}' non trouvée")
        
        # Analyser les points de référence précis
        reference_analysis = self._analyze_precise_reference_points(collection1, collection2, reference_category)
        
        if not reference_analysis['success']:
            return reference_analysis
        
        # Calculer les déplacements précis
        alignment_data = self._calculate_precise_displacements(reference_analysis)
        
        # Résultat complet
        result = {
            'success': True,
            'collection1': {
                'name': collection1_name,
                'reference_points': reference_analysis['collection1_points']
            },
            'collection2': {
                'name': collection2_name,
                'reference_points': reference_analysis['collection2_points']
            },
            'alignment_analysis': alignment_data,
            'recommendations': self._generate_precise_recommendations(alignment_data)
        }
        
        self._print_precise_analysis_summary(result)
        return result
    
    def _analyze_precise_reference_points(self, collection1: 'bpy.types.Collection', collection2: 'bpy.types.Collection', reference_category: str) -> Dict[str, Any]:
        """Analyse les points de référence précis dans les deux collections"""
        
        def find_reference_points(collection, label):
            reference_points = []
            
            def search_recursive(col):
                for obj in col.objects:
                    if obj.type == 'EMPTY':
                        ifc_category = self._extract_ifc_category(obj.name)
                        if ifc_category == reference_category:
                            # Extraire le nom spécifique (ex: "NIVEAU 1" depuis "IfcBuildingStorey/NIVEAU 1.001")
                            specific_name = self._extract_specific_name(obj.name)
                            reference_points.append({
                                'name': obj.name,
                                'specific_name': specific_name,
                                'location': list(obj.location),
                                'ifc_category': ifc_category
                            })
                
                for child_col in col.children:
                    search_recursive(child_col)
            
            search_recursive(collection)
            return reference_points
        
        # Trouver les points de référence dans les deux collections
        points1 = find_reference_points(collection1, "Collection 1")
        points2 = find_reference_points(collection2, "Collection 2")
        
        if not points1:
            return self._create_error_result(f"Aucun point de référence '{reference_category}' trouvé dans {collection1.name}")
        if not points2:
            return self._create_error_result(f"Aucun point de référence '{reference_category}' trouvé dans {collection2.name}")
        
        # Trier par hauteur (Z)
        points1.sort(key=lambda x: x['location'][2])
        points2.sort(key=lambda x: x['location'][2])
        
        return {
            'success': True,
            'collection1_points': points1,
            'collection2_points': points2,
            'reference_category': reference_category
        }
    
    def _extract_specific_name(self, object_name: str) -> str:
        """Extrait le nom spécifique depuis le nom complet de l'objet"""
        if '/' in object_name:
            # Exemple: "IfcBuildingStorey/NIVEAU 1.001" -> "NIVEAU 1"
            specific_part = object_name.split('/')[1]
            # Enlever les suffixes numériques (.001, .002, etc.)
            if '.' in specific_part:
                specific_part = specific_part.split('.')[0]
            return specific_part
        return object_name
    
    def _calculate_precise_displacements(self, reference_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calcule les déplacements précis basés sur les points de référence"""
        
        points1 = reference_analysis['collection1_points']
        points2 = reference_analysis['collection2_points']
        
        # Créer des dictionnaires pour faciliter la correspondance
        points1_dict = {point['specific_name']: point for point in points1}
        points2_dict = {point['specific_name']: point for point in points2}
        
        # Trouver les correspondances exactes
        exact_matches = []
        for name1, point1 in points1_dict.items():
            if name1 in points2_dict:
                point2 = points2_dict[name1]
                exact_matches.append({
                    'name': name1,
                    'point1': point1,
                    'point2': point2,
                    'distance': abs(point1['location'][2] - point2['location'][2])
                })
        
        # Trier par distance (du plus petit au plus grand)
        exact_matches.sort(key=lambda x: x['distance'])
        
        # Analyser les déplacements par axe
        displacements = {
            'x': [],
            'y': [],
            'z': []
        }
        
        for match in exact_matches:
            point1 = match['point1']['location']
            point2 = match['point2']['location']
            
            for i, axis in enumerate(['x', 'y', 'z']):
                displacement = point1[i] - point2[i]
                displacements[axis].append({
                    'name': match['name'],
                    'displacement': displacement
                })
        
        # Calculer les déplacements recommandés
        recommended_displacement = [0.0, 0.0, 0.0]
        
        if exact_matches:
            # Utiliser le premier match (le plus proche) comme référence principale
            primary_match = exact_matches[0]
            point1 = primary_match['point1']['location']
            point2 = primary_match['point2']['location']
            
            recommended_displacement = [
                point1[0] - point2[0],  # X
                point1[1] - point2[1],  # Y
                point1[2] - point2[2]   # Z
            ]
        
        return {
            'exact_matches': exact_matches,
            'displacements_by_axis': displacements,
            'recommended_displacement': recommended_displacement,
            'primary_reference': exact_matches[0] if exact_matches else None
        }
    
    def _generate_precise_recommendations(self, alignment_data: Dict[str, Any]) -> List[str]:
        """Génère des recommandations précises basées sur l'analyse"""
        recommendations = []
        
        if not alignment_data['exact_matches']:
            recommendations.append("Aucune correspondance exacte trouvée entre les points de référence")
            return recommendations
        
        primary_match = alignment_data['primary_reference']
        if primary_match:
            recommendations.append(f"Point de référence principal: {primary_match['name']}")
            recommendations.append(f"Distance entre les points correspondants: {primary_match['distance']:.2f}m")
        
        displacement = alignment_data['recommended_displacement']
        
        if abs(displacement[0]) > 1.0:
            recommendations.append(f"Déplacement X: {displacement[0]:.2f}m")
        if abs(displacement[1]) > 1.0:
            recommendations.append(f"Déplacement Y: {displacement[1]:.2f}m")
        if abs(displacement[2]) > 1.0:
            recommendations.append(f"Déplacement Z: {displacement[2]:.2f}m")
        
        # Analyser la cohérence des déplacements
        z_displacements = [match['distance'] for match in alignment_data['exact_matches']]
        if len(z_displacements) > 1:
            max_diff = max(z_displacements) - min(z_displacements)
            if max_diff > 5.0:  # Plus de 5m de différence
                recommendations.append(f"⚠️  Incohérence détectée: Différence de {max_diff:.2f}m entre les points de référence")
            else:
                recommendations.append("✅ Alignement cohérent entre tous les points de référence")
        
        return recommendations
    
    def _print_precise_analysis_summary(self, result: Dict[str, Any]):
        """Affiche un résumé de l'analyse précise"""
        if not result['success']:
            print(f"❌ ERREUR: {result.get('error', 'Erreur inconnue')}")
            return
        
        print(f"\n🎯 RÉSUMÉ DE L'ANALYSE PRÉCISE:")
        print(f"   Collection 1: {result['collection1']['name']}")
        print(f"   Collection 2: {result['collection2']['name']}")
        
        alignment = result['alignment_analysis']
        
        if alignment['exact_matches']:
            print(f"\n📊 CORRESPONDANCES EXACTES:")
            for match in alignment['exact_matches']:
                print(f"   - {match['name']}: {match['distance']:.2f}m")
            
            if alignment['primary_reference']:
                primary = alignment['primary_reference']
                print(f"\n🎯 POINT DE RÉFÉRENCE PRINCIPAL:")
                print(f"   - Nom: {primary['name']}")
                print(f"   - Distance: {primary['distance']:.2f}m")
                print(f"   - Position Collection 1: {primary['point1']['location']}")
                print(f"   - Position Collection 2: {primary['point2']['location']}")
            
            displacement = alignment['recommended_displacement']
            print(f"\n💡 DÉPLACEMENT RECOMMANDÉ:")
            print(f"   - X: {displacement[0]:.2f}m")
            print(f"   - Y: {displacement[1]:.2f}m")
            print(f"   - Z: {displacement[2]:.2f}m")
        
        print(f"\n🎯 RECOMMANDATIONS:")
        for rec in result['recommendations']:
            print(f"   - {rec}")
    
    def apply_precise_alignment(self, collection1_name: str, collection2_name: str, reference_category: str = "IfcBuildingStorey") -> Dict[str, Any]:
        """
        Applique l'alignement précis en déplaçant la deuxième collection
        
        Args:
            collection1_name: Collection de référence
            collection2_name: Collection à déplacer
            reference_category: Catégorie IFC pour les points de référence
            
        Returns:
            Dict avec les résultats de l'alignement
        """
        print(f"🚀 APPLICATION DE L'ALIGNEMENT PRÉCIS")
        
        # Analyser l'alignement
        analysis = self.analyze_precise_alignment(collection1_name, collection2_name, reference_category)
        
        if not analysis['success']:
            return analysis
        
        # Obtenir le déplacement recommandé
        displacement = analysis['alignment_analysis']['recommended_displacement']
        
        # Appliquer le déplacement
        collection2 = self._find_collection(collection2_name)
        if not collection2:
            return self._create_error_result(f"Collection '{collection2_name}' non trouvée")
        
        # Déplacer tous les objets de la collection
        moved_objects = []
        
        def move_recursive(col):
            for obj in col.objects:
                if obj.location:
                    original_location = obj.location.copy()
                    obj.location.x += displacement[0]
                    obj.location.y += displacement[1]
                    obj.location.z += displacement[2]
                    moved_objects.append({
                        'name': obj.name,
                        'original_location': list(original_location),
                        'new_location': list(obj.location)
                    })
            
            for child_col in col.children:
                move_recursive(child_col)
        
        move_recursive(collection2)
        
        return {
            'success': True,
            'collection_moved': collection2_name,
            'displacement_applied': displacement,
            'objects_moved': len(moved_objects),
            'analysis': analysis
        }


def create_coll_aligner() -> CollAligner:
    """Factory function pour créer un aligneur de collections"""
    return CollAligner() 