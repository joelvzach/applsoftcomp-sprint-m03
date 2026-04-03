#!/usr/bin/env python3
"""
Target Shopper - Main Orchestrator

Runs the complete workflow:
1. Store Locator
2. Parallel Item Search
3. SVG Fetcher
4. Route Optimizer
5. Route Visualizer
6. Report Generator
7. HTML Generator
8. Output Summary
"""

import sys
import os
from pathlib import Path

# Add tools to path
tools_dir = Path(__file__).parent / "tools"
sys.path.insert(0, str(tools_dir))

from store_locator import find_store
from parallel_search import parallel_search
from svg_fetcher import fetch_store_map
from route_optimizer import basic_route_optimization
from report_generator import generate_report, load_items_from_search
from route_visualizer import save_svg_with_route, extract_special_locations
from maze_analyzer import StoreMaze
from maze_pathfinder import find_maze_path, calculate_path_length
from html_generator import generate_html_map
from output_generator import generate_output_summary


def run_workflow(store_name: str, items: list, headless: bool = True):
    """Execute complete Target shopper workflow."""
    
    print("=" * 70)
    print("TARGET SHOPPER - GROCERY ROUTE OPTIMIZER")
    print("=" * 70)
    
    # Task 1-2: Store Locator
    print("\n[1/8] Finding store...")
    store_result = find_store(store_name)
    if not store_result:
        print(f"ERROR: Could not find store '{store_name}'")
        return None
    
    print(f"  ✓ Store: {store_result['name']}")
    print(f"  ✓ URL: {store_result['url']}")
    
    # Task 3: Parallel Item Search
    print(f"\n[2/8] Searching for {len(items)} items...")
    search_results = parallel_search(items, store_result['url'], headless=headless)
    
    available = sum(1 for r in search_results if r.get('available'))
    print(f"  ✓ Found: {available}/{len(items)} items")
    
    # Task 4: SVG Fetcher
    print("\n[3/8] Fetching store map...")
    svg_result = fetch_store_map(store_result['url'], headless=headless)
    if not svg_result:
        print("  ⊘ Map unavailable, continuing with text-only output")
    else:
        print(f"  ✓ Map fetched: {svg_result.get('width')}x{svg_result.get('height')}")
        print(f"  ✓ Aisles: {len(svg_result.get('aisles', []))}")
    
    # Task 5: Route Optimizer (Maze-based A* pathfinding with multi-floor support)
    print("\n[4/8] Optimizing route...")
    route_coords = None
    route_distance = 0
    if svg_result:
        available_aisles = [r['aisle'] for r in search_results if r.get('aisle')]
        if available_aisles:
            # Check if multi-floor store
            is_multi_floor = svg_result.get('is_multi_floor', False)
            floors = svg_result.get('floors', [svg_result])
            vertical_connections = svg_result.get('vertical_connections', [])
            
            if is_multi_floor:
                print(f"  ✓ Multi-floor store: {len(floors)} floor(s)")
                print(f"  ✓ Vertical connections: {len(vertical_connections)} (escalator/elevator)")
                
                # Group items by floor
                items_by_floor = {floor['floor']: [] for floor in floors}
                aisle_to_floor = {}
                
                for floor_data in floors:
                    for aisle in floor_data['aisles']:
                        aisle_to_floor[aisle] = floor_data['floor']
                
                for aisle in available_aisles:
                    floor_num = aisle_to_floor.get(aisle, 1)
                    items_by_floor[floor_num].append(aisle)
                
                # Build mazes for each floor
                floor_mazes = {}
                for floor_data in floors:
                    floor_mazes[floor_data['floor']] = StoreMaze(floor_data['svg_content'])
                    print(f"    Floor {floor_data['floor']}: {floor_mazes[floor_data['floor']].grid_width}x{floor_mazes[floor_data['floor']].grid_height} cells")
                
                # Build route: entrance → floor 1 items → vertical connection → floor 2 items → ... → checkout
                full_path = []
                total_distance = 0.0
                current_floor = 1
                current_pos = None
                
                # Start at entrance (floor 1)
                entrance_pos = floors[0]['special_locations'].get('entrance')
                if entrance_pos:
                    current_pos = entrance_pos
                
                # Process each floor in order
                for floor_num in sorted(items_by_floor.keys()):
                    floor_items = items_by_floor[floor_num]
                    if not floor_items:
                        continue
                    
                    maze = floor_mazes[floor_num]
                    floor_data = floors[floor_num - 1] if floor_num <= len(floors) else floors[0]
                    
                    # If switching floors, use vertical connection
                    if floor_num != current_floor and vertical_connections:
                        # Find vertical connection on current floor
                        conn_on_current = [c for c in vertical_connections if c['floor'] == current_floor]
                        conn_on_target = [c for c in vertical_connections if c['floor'] == floor_num]
                        
                        if conn_on_current and conn_on_target:
                            # Navigate to vertical connection on current floor
                            conn_pos = conn_on_current[0]['position']
                            segment_path = find_maze_path(maze, current_pos, conn_pos)
                            if segment_path:
                                full_path.extend(segment_path[1:] if full_path else segment_path)
                                total_distance += calculate_path_length(segment_path)
                            
                            # "Teleport" to corresponding position on target floor
                            target_conn_pos = conn_on_target[0]['position']
                            current_pos = target_conn_pos
                            print(f"    → Switched to Floor {floor_num} via {conn_on_current[0]['type']}")
                    
                    # Navigate to items on this floor
                    for aisle in floor_items:
                        aisle_pos = maze.aisle_labels.get(aisle)
                        if aisle_pos and current_pos:
                            segment_path = find_maze_path(maze, current_pos, aisle_pos)
                            if segment_path:
                                full_path.extend(segment_path[1:] if full_path else segment_path)
                                total_distance += calculate_path_length(segment_path)
                                current_pos = aisle_pos
                    
                    current_floor = floor_num
                
                # Navigate to checkout (usually floor 1)
                checkout_floor = 1
                checkout_pos = floor_mazes[checkout_floor].special_locations.get('checkout')
                if checkout_pos and current_pos:
                    final_maze = floor_mazes[checkout_floor]
                    
                    # If on different floor, use vertical connection
                    if current_floor != checkout_floor and vertical_connections:
                        conn_on_current = [c for c in vertical_connections if c['floor'] == current_floor]
                        if conn_on_current:
                            conn_pos = conn_on_current[0]['position']
                            segment_path = find_maze_path(final_maze, current_pos, conn_pos)
                            if segment_path:
                                full_path.extend(segment_path[1:])
                                total_distance += calculate_path_length(segment_path)
                            current_pos = conn_pos
                    
                    # Navigate to checkout
                    segment_path = find_maze_path(final_maze, current_pos, checkout_pos)
                    if segment_path:
                        full_path.extend(segment_path[1:])
                        total_distance += calculate_path_length(segment_path)
                
                if full_path:
                    route_coords = full_path
                    route_distance = total_distance
                    print(f"  ✓ Route: {len(route_coords)} path points (multi-floor)")
                    print(f"  ✓ Distance: {route_distance:.1f} SVG units")
                else:
                    print("  ⊘ No valid path found")
            
            else:
                # Single floor - original logic
                maze = StoreMaze(svg_result['svg_content'])
                print(f"  ✓ Maze grid: {maze.grid_width}x{maze.grid_height} cells")
                
                # Build ordered list of stops: entrance → aisles → checkout
                stops = ['entrance']
                stops.extend(available_aisles)
                stops.append('checkout')
                
                # Find A* path through maze for each segment
                full_path = []
                total_distance = 0.0
                
                for i in range(len(stops) - 1):
                    start_label = stops[i]
                    end_label = stops[i + 1]
                    
                    # Get coordinates for start and end
                    if start_label == 'entrance':
                        start = maze.special_locations.get('entrance')
                    elif start_label == 'checkout':
                        start = maze.special_locations.get('checkout')
                    else:
                        start = maze.aisle_labels.get(start_label)
                    
                    if end_label == 'entrance':
                        end = maze.special_locations.get('entrance')
                    elif end_label == 'checkout':
                        end = maze.special_locations.get('checkout')
                    else:
                        end = maze.aisle_labels.get(end_label)
                    
                    if start and end:
                        segment_path = find_maze_path(maze, start, end)
                        if segment_path:
                            if i == 0:
                                full_path.extend(segment_path)
                            else:
                                full_path.extend(segment_path[1:])  # Skip duplicate start point
                            total_distance += calculate_path_length(segment_path)
                
                if full_path:
                    route_coords = full_path
                    route_distance = total_distance
                    print(f"  ✓ Route: {len(route_coords)} path points")
                    print(f"  ✓ Distance: {route_distance:.1f} SVG units")
                else:
                    print("  ⊘ No valid path found")
        else:
            print("  ⊘ No available items to route")
    else:
        print("  ⊘ Skipped (map unavailable)")
    
    # Task 5b: Route Visualizer
    print("\n[5/8] Generating route visualization...")
    viz_path = None
    if svg_result and route_coords:
        # Build aisle_positions dict from maze
        aisle_positions = maze.aisle_labels
        
        # Build route labels with entrance/checkout
        route_labels = ['entrance']
        route_labels.extend([r['aisle'] for r in search_results if r.get('aisle')])
        route_labels.append('checkout')
        
        viz_path = save_svg_with_route(
            svg_result,
            route_coords,
            route_labels,
            f"project/output/route_viz_{len(search_results)}items.svg",
            aisle_positions
        )
        if viz_path:
            print(f"  ✓ Saved: {viz_path}")
        else:
            print("  ⊘ Failed to save visualization")
    else:
        print("  ⊘ Skipped")
    
    # Task 6: Report Generator
    print("\n[6/8] Generating grocery report...")
    items_for_report = load_items_from_search(search_results)
    report_path = generate_report(items_for_report)
    print(f"  ✓ Saved: {report_path}")
    
    # Task 7: HTML Generator
    print("\n[7/8] Generating interactive HTML map...")
    html_path = None
    if svg_result and route_coords:
        # Get aisle positions and special locations
        if is_multi_floor:
            # Use first floor for HTML (simplified view)
            aisle_positions = floors[0]['aisle_markers']
            special_locations = floors[0]['special_locations']
        else:
            aisle_positions = {aisle: pos for aisle, pos in maze.aisle_labels.items()}
            special_locations = maze.special_locations
        
        html_path = generate_html_map(
            svg_result['svg_content'],
            route_coords,
            search_results,
            aisle_positions,
            special_locations
        )
        print(f"  ✓ Saved: {html_path}")
    else:
        print("  ⊘ Skipped (map unavailable)")
    
    # Task 8: Output Summary
    print("\n[8/8] Generating route summary...")
    output_path = None
    if route_coords:
        output_path = generate_output_summary(
            search_results,
            route_coords,
            route_distance,
            html_path=html_path,
            svg_path=viz_path if isinstance(viz_path, str) else None
        )
        print(f"  ✓ Saved: {output_path}")
    else:
        print("  ⊘ Skipped (no route data)")
    
    print("\n" + "=" * 70)
    print("WORKFLOW COMPLETE")
    print("=" * 70)
    
    return {
        'store': store_result,
        'items': search_results,
        'svg': svg_result,
        'route': route_coords,
        'report': report_path,
        'visualization': viz_path
    }


if __name__ == '__main__':
    # Example usage
    print("Usage: python main.py <store_name> <item1> [item2] ...")
    print("Example: python main.py Vestal eggs milk bread")
    print("Note: Uses visible browser by default to avoid anti-bot detection")
    
    # Default to non-headless (visible browser) to avoid Target's anti-bot detection
    headless = '--headless' in sys.argv
    args = [a for a in sys.argv if not a.startswith('--')]
    
    if len(args) < 3:
        # Demo with sample items - use visible browser
        print("\nRunning demo with sample items...")
        run_workflow("Vestal", ["eggs", "milk", "bread"], headless=False)
    else:
        store_name = args[1]
        items = args[2:]
        run_workflow(store_name, items, headless=headless)
