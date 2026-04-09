#!/usr/bin/env python3
"""
Target Shopper - Complete Version

Features:
- Hardcoded Vestal store (no lookup)
- Cached maze data (instant loading)
- Real-time progress dashboard with overlay modal
- Date-level > Time-level > Title folder structure
- Auto-opens map in overlay
"""

import sys
from pathlib import Path
from datetime import datetime
import json
import time

tools_dir = Path(__file__).parent / "tools"
sys.path.insert(0, str(tools_dir))

# Hardcoded Vestal store
STORE_CONFIG = {"name": "Binghamton Vestal", "store_id": "1056", "url": "https://www.target.com/sl/binghamton-vestal/1056"}

# Load cached maze data
TEMPLATES_DIR = Path(__file__).parent / "templates"
with open(TEMPLATES_DIR / "maze_cache_vestal.json") as f:
    _cached_maze = json.load(f)

# Imports
from parallel_search import parallel_search
from report_generator import generate_report, load_items_from_search
from route_visualizer import save_svg_with_route
from maze_analyzer import StoreMaze
from maze_pathfinder import find_maze_path, calculate_path_length
from html_generator import generate_html_map
from output_generator import generate_output_summary
from progress_server import init_progress_server


def run_workflow(items: list):
    print("=" * 70)
    print("TARGET SHOPPER - COMPLETE VERSION")
    print("=" * 70)
    
    # Setup output directory with new format: datelevel > timelevel > title
    output_dir = Path(__file__).parent.parent.parent.parent / "project" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create date-level folder
    date_folder = output_dir / datetime.now().strftime("%Y-%m-%d")
    date_folder.mkdir(parents=True, exist_ok=True)
    
    # Create time-level session folder with title
    time_str = datetime.now().strftime("%H-%M-%S")
    title = "_".join(items[:3]) if items else "shopping"
    if len(title) > 30:
        title = title[:27] + "..."
    session_dir = date_folder / f"{time_str}_{title}"
    session_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📁 Session: {session_dir.parent.name}/{session_dir.name}")
    
    # Initialize progress server (opens browser automatically)
    progress_server = init_progress_server(port=8000, open_browser=True)
    progress_server.set_session_path(str(session_dir))
    
    # Task 1: Store config
    print("\n[1/6] Loading store configuration...")
    progress_server.task_start(1, "Loading store...")
    store_result = STORE_CONFIG
    print(f"  ✓ {store_result['name']} (ID: {store_result['store_id']})")
    progress_server.log(f"Store: {store_result['name']}", "success")
    progress_server.task_complete(1, "Config loaded")
    
    # Task 2: Item search
    print(f"\n[2/6] Searching for {len(items)} items...")
    progress_server.task_start(2, f"Searching {len(items)} items...")
    search_results = parallel_search(items, store_result["url"], headless=True)
    available = sum(1 for r in search_results if r.get("available"))
    print(f"  ✓ Found: {available}/{len(items)} items")
    progress_server.log(f"Found {available}/{len(items)} items", "success")
    progress_server.task_complete(2, f"{available}/{len(items)} found")
    
    # Save search results
    with open(session_dir / "search_results.json", "w") as f:
        json.dump(search_results, f, indent=2)
    
    # Task 3: Load cached map
    print("\n[3/6] Loading cached store map...")
    progress_server.task_start(3, "Loading map...")
    with open(TEMPLATES_DIR / "store_map_vestal.svg", 'r') as f:
        svg_content = f.read()
    svg_result = {"svg_content": svg_content}
    
    with open(session_dir / "store_map.svg", "w") as f:
        f.write(svg_content)
    print(f"  ✓ Map loaded from cache")
    progress_server.log("Map loaded from cache", "success")
    progress_server.task_complete(3, "Map loaded")
    
    # Task 4: Route optimization
    print("\n[4/6] Optimizing route...")
    progress_server.task_start(4, "Building route...")
    
    maze = StoreMaze(svg_content)
    maze.grid_width = _cached_maze["grid_width"]
    maze.grid_height = _cached_maze["grid_height"]
    maze.aisle_labels = {k: tuple(v) for k, v in _cached_maze["aisle_labels"].items()}
    maze.special_locations = {k: tuple(v) for k, v in _cached_maze["special_locations"].items()}
    
    available_aisles = [r["aisle"] for r in search_results if r.get("aisle")]
    stops = ["entrance"] + available_aisles + ["checkout"]
    full_path, total_distance = [], 0.0
    
    for i in range(len(stops) - 1):
        start = maze.special_locations.get(stops[i]) if stops[i] in ["entrance", "checkout"] else maze.aisle_labels.get(stops[i])
        end = maze.special_locations.get(stops[i+1]) if stops[i+1] in ["entrance", "checkout"] else maze.aisle_labels.get(stops[i+1])
        if start and end:
            segment_path = find_maze_path(maze, start, end)
            if segment_path:
                full_path.extend(segment_path[1:] if full_path else segment_path)
                total_distance += calculate_path_length(segment_path)
    
    print(f"  ✓ Route: {len(full_path)} points, {total_distance:.1f} SVG units")
    progress_server.log(f"Route: {len(full_path)} points", "success")
    progress_server.task_complete(4, f"{len(full_path)} points")
    
    # Save route
    with open(session_dir / "route_coords.json", "w") as f:
        json.dump({"path": full_path, "distance": total_distance}, f)
    
    # Task 5: Generate outputs
    print("\n[5/6] Generating outputs...")
    progress_server.task_start(5, "Generating outputs...")
    
    # Report
    items_for_report = load_items_from_search(search_results)
    report_path = generate_report(items_for_report, output_dir=str(session_dir))
    print(f"  ✓ Report: {Path(report_path).name}")
    
    # SVG visualization
    aisle_positions = maze.aisle_labels
    route_labels = ["entrance"] + [r["aisle"] for r in search_results if r.get("aisle")] + ["checkout"]
    viz_path_str = str(session_dir / "route_viz.svg")
    save_svg_with_route(svg_result, full_path, route_labels, viz_path_str, aisle_positions)
    print(f"  ✓ Visualization: route_viz.svg")
    
    # HTML map
    html_path = generate_html_map(
        svg_content, full_path, search_results,
        dict(aisle_positions), maze.special_locations,
        output_path=str(session_dir / "route_map.html"),
    )
    print(f"  ✓ HTML Map: route_map.html")
    
    # Summary
    output_path = generate_output_summary(
        search_results, full_path, total_distance,
        html_path=html_path, svg_path=viz_path_str,
        output_dir=str(session_dir), timestamp=datetime.now(),
    )
    print(f"  ✓ Summary: {Path(output_path).name}")
    progress_server.task_complete(5, "All outputs saved")
    
    # Task 6: Complete and show dashboard
    print("\n[6/6] Finalizing...")
    summary = f"✅ {available}/{len(items)} items found (${sum(r.get('price', 0) or 0 for r in search_results if r.get('available')):.2f}) • Route: {len(full_path)} points"
    progress_server.complete(summary)
    
    print("\n" + "=" * 70)
    print("WORKFLOW COMPLETE")
    print("=" * 70)
    print(f"\n🌐 Progress dashboard: http://127.0.0.1:8000/")
    print(f"💡 Click 'View Interactive Map' to see route in overlay modal")
    print(f"💡 Dashboard will stay open for 60 seconds")
    print(f"\n📁 Session folder: {session_dir}")
    
    # Keep server running for 60 seconds
    try:
        time.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        progress_server.stop()
        print("\n✓ Progress server stopped")
    
    return session_dir


if __name__ == "__main__":
    print("Usage: python main_minimal.py <item1> [item2] ...")
    print("Example: python main_minimal.py eggs milk bread")
    print("Store: Target Binghamton Vestal (ID: 1056) - Hardcoded\n")
    
    args = sys.argv[1:] if len(sys.argv) > 1 else ["eggs", "milk", "bread"]
    run_workflow(args)
