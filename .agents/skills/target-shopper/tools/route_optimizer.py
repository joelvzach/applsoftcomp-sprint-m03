#!/usr/bin/env python3
"""
Route Optimizer - Calculate shortest walking path through Target store.
Uses maze-based pathfinding through walkability grid.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import re
import math

try:
    from maze_analyzer import StoreMaze
    from maze_pathfinder import find_maze_path, calculate_path_length
    MAZE_AVAILABLE = True
except ImportError as e:
    MAZE_AVAILABLE = False
    # Only print if actually trying to use maze
    pass


def parse_svg_viewbox(svg_content: str) -> Tuple[float, float, float, float]:
    """Extract viewBox attributes from SVG."""
    match = re.search(r'viewBox="([^"]+)"', svg_content)
    if match:
        parts = match.group(1).split()
        if len(parts) >= 4:
            return float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])
    return 0.0, 0.0, 0.0, 0.0


def extract_aisle_positions(svg_content: str) -> Dict[str, Tuple[float, float]]:
    """Extract aisle marker positions from SVG text elements."""
    aisles = {}
    
    text_matches = re.findall(
        r'<text[^>]*x="([\d.-]+)"[^>]*y="([\d.-]+)"[^>]*>([A-Z]{1,2}\d{1,3}|CL\d{1,2}|G\d{2,3})</text>',
        svg_content
    )
    
    for x, y, aisle in text_matches:
        if aisle not in aisles:
            try:
                aisles[aisle] = (float(x), float(y))
            except ValueError:
                pass
    
    return aisles


def extract_special_locations(svg_content: str) -> Dict[str, Tuple[float, float]]:
    """Extract entrance, checkout locations from SVG labels."""
    locations = {}
    
    patterns = [
        (r'<text[^>]*x="([\d.-]+)"[^>]*y="([\d.-]+)"[^>]*>entrance</text>', 'entrance'),
        (r'<text[^>]*x="([\d.-]+)"[^>]*y="([\d.-]+)"[^>]*>checkout</text>', 'checkout'),
    ]
    
    for pattern, location in patterns:
        matches = re.findall(pattern, svg_content)
        for x, y in matches:
            if location not in locations:
                try:
                    locations[location] = (float(x), float(y))
                except ValueError:
                    pass
    
    return locations


def group_items_by_aisle(
    items: List[Dict],
    route_order: List[str]
) -> List[Dict]:
    """
    Order items according to the optimized route.
    Items in same aisle are grouped together.
    """
    aisle_order = {aisle: i for i, aisle in enumerate(route_order) if aisle not in ['entrance', 'checkout']}
    
    def item_sort_key(item):
        aisle = item.get('aisle', 'ZZ999')
        order = aisle_order.get(aisle, 999)
        return (order, aisle, item.get('name', ''))
    
    return sorted(items, key=item_sort_key)


def calculate_route(
    svg_content: str,
    items: List[Dict],
    use_maze: bool = True
) -> Dict:
    """
    Main function to calculate optimal route.
    
    Args:
        svg_content: SVG map content
        items: List of items with 'name' and 'aisle' keys
        use_maze: Whether to use maze-based pathfinding (default True)
    
    Returns:
        Dictionary with route, ordered_items, total_distance, etc.
    """
    viewBox = parse_svg_viewbox(svg_content)
    svg_width = viewBox[2]
    svg_height = viewBox[3]
    
    # Extract aisle positions and special locations
    aisle_positions = extract_aisle_positions(svg_content)
    special_locations = extract_special_locations(svg_content)
    
    # Get entrance and checkout positions
    entrance = special_locations.get('entrance', (svg_width * 0.9, svg_height * 0.95))
    checkout = special_locations.get('checkout', (svg_width * 0.7, svg_height * 0.85))
    
    # Get unique aisles from items
    required_aisles = list(dict.fromkeys([
        item.get('aisle', '') 
        for item in items 
        if item.get('aisle') and item.get('available', True)
    ]))
    
    if not required_aisles:
        return {
            'route': [entrance, checkout],
            'route_labels': ['entrance', 'checkout'],
            'ordered_items': items,
            'total_distance': 0,
            'aisle_positions': aisle_positions,
            'error': 'No aisles specified in items'
        }
    
    # Use maze-based pathfinding if available
    if use_maze and MAZE_AVAILABLE:
        try:
            print("Building walkability grid...")
            maze = StoreMaze(svg_content)
            
            # Build waypoint list (aisles in order)
            waypoints = [aisle_positions[aisle] for aisle in required_aisles if aisle in aisle_positions]
            
            print(f"Finding path through maze ({len(waypoints)} waypoints)...")
            path = find_maze_path(
                maze,
                entrance,
                checkout,
                waypoints,
                heuristic_method='euclidean'
            )
            
            if path:
                distance = calculate_path_length(path)
                print(f"Path found: {len(path)} points, {distance:.2f} SVG units")
                
                return {
                    'route': path,
                    'route_labels': ['entrance'] + required_aisles + ['checkout'],
                    'ordered_items': group_items_by_aisle(items, required_aisles),
                    'total_distance': distance,
                    'aisle_positions': aisle_positions,
                    'aisles_visited': required_aisles,
                    'item_count': len(items),
                    'available_items': len([i for i in items if i.get('available', False)]),
                    'maze': maze  # Include maze for visualization
                }
            else:
                print("Maze pathfinding failed, falling back to basic routing")
                
        except Exception as e:
            print(f"Maze pathfinding error: {e}")
            print("Falling back to basic routing")
    
    # Fallback: basic nearest-neighbor routing
    print("Using basic nearest-neighbor routing")
    route, distance = basic_route_optimization(
        aisle_positions, required_aisles, entrance, checkout
    )
    
    return {
        'route': route,
        'route_labels': ['entrance'] + required_aisles + ['checkout'],
        'ordered_items': group_items_by_aisle(items, required_aisles),
        'total_distance': distance,
        'aisle_positions': aisle_positions,
        'aisles_visited': required_aisles,
        'item_count': len(items),
        'available_items': len([i for i in items if i.get('available', False)])
    }


def basic_route_optimization(
    aisle_positions: Dict[str, Tuple[float, float]],
    required_aisles: List[str],
    entrance: Tuple[float, float],
    checkout: Tuple[float, float]
) -> Tuple[List[Tuple[float, float]], float]:
    """
    Basic nearest-neighbor route optimization (fallback).
    """
    if not required_aisles:
        return [entrance, checkout], 0.0
    
    route = [entrance]
    current = entrance
    total_distance = 0.0
    remaining = set(required_aisles)
    
    while remaining:
        best_next = None
        best_dist = float('inf')
        
        for aisle in remaining:
            if aisle in aisle_positions:
                pos = aisle_positions[aisle]
                dist = math.sqrt((pos[0] - current[0])**2 + (pos[1] - current[1])**2)
                if dist < best_dist:
                    best_dist = dist
                    best_next = aisle
        
        if best_next is None:
            break
        
        route.append(aisle_positions[best_next])
        total_distance += best_dist
        current = aisle_positions[best_next]
        remaining.remove(best_next)
    
    # Add checkout
    route.append(checkout)
    final_dist = math.sqrt((checkout[0] - current[0])**2 + (checkout[1] - current[1])**2)
    total_distance += final_dist
    
    return route, total_distance


def estimate_walking_distance(route_distance: float, svg_scale: float = 10.0) -> float:
    """
    Convert SVG coordinate distance to estimated feet.
    Default scale: 1 SVG unit = 10 feet
    """
    return route_distance * svg_scale


if __name__ == '__main__':
    # Test with sample data
    test_svg = '''<svg viewBox="0 0 100 60">
        <text x="10" y="10">A1</text>
        <text x="30" y="10">A2</text>
        <text x="50" y="10">A3</text>
        <text x="85" y="55">entrance</text>
        <text x="70" y="50">checkout</text>
    </svg>'''
    
    test_items = [
        {'name': 'Milk', 'aisle': 'A1', 'available': True},
        {'name': 'Bread', 'aisle': 'A2', 'available': True},
        {'name': 'Eggs', 'aisle': 'A3', 'available': True},
    ]
    
    result = calculate_route(test_svg, test_items, use_maze=False)
    
    print("\nRoute Optimizer Test Results")
    print("=" * 40)
    print(f"Aisles visited: {result['aisles_visited']}")
    print(f"Total distance: {result['total_distance']:.2f} units")
    print(f"Estimated walking: {estimate_walking_distance(result['total_distance']):.1f} feet")
    print(f"\nItems in order:")
    for i, item in enumerate(result['ordered_items'], 1):
        print(f"  {i}. {item['name']} - Aisle {item['aisle']}")
