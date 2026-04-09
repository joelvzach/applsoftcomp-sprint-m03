#!/usr/bin/env python3
"""
Target Shopper - Main Orchestrator (Optimized for Vestal Location)

Runs the complete workflow with:
- Hardcoded Vestal store (no lookup)
- Cached store map (no Playwright browser automation)
- Cached maze data (instant grid loading)
- Real-time progress dashboard
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add tools to path
tools_dir = Path(__file__).parent / "tools"
sys.path.insert(0, str(tools_dir))

# Hardcoded Vestal store config - no lookup needed
STORE_CONFIG = {
    "name": "Binghamton Vestal",
    "store_id": "1056",
    "url": "https://www.target.com/sl/binghamton-vestal/1056",
}

# Load cached map and maze data
TEMPLATES_DIR = Path(__file__).parent / "templates"
CACHED_MAP_PATH = TEMPLATES_DIR / "store_map_vestal.svg"
CACHED_MAZE_PATH = TEMPLATES_DIR / "maze_cache_vestal.json"
_cached_maze = None
if CACHED_MAZE_PATH.exists():
    import json
    with open(CACHED_MAZE_PATH) as f:
        _cached_maze = json.load(f)

# Import tools
from parallel_search_mock import parallel_search  # Using mock for fast testing
from route_optimizer import basic_route_optimization
from report_generator import generate_report, load_items_from_search
from route_visualizer import save_svg_with_route, extract_special_locations
from maze_analyzer import StoreMaze
from maze_pathfinder import find_maze_path, calculate_path_length
from html_generator import generate_html_map
from output_generator import generate_output_summary
# from progress_server import init_progress_server  # Disabled for testing


class ProgressTracker:
    """Track progress and generate hyperlinked progress file."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.progress_file = output_dir / "progress.txt"
        self.entries = []
    
    def log(self, task_num: int, task_name: str, status: str, files: dict = None):
        """Log task completion with file links."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] Task {task_num}: {task_name} - {status}\n"
        
        if files:
            entry += "Files Generated:\n"
            for name, path in files.items():
                rel_path = path.name if hasattr(path, 'name') else str(path)
                entry += f"- [{name}]({rel_path})\n"
        
        entry += "\n"
        self.entries.append(entry)
        
        with open(self.progress_file, "w") as f:
            f.writelines(self.entries)


def run_workflow(items: list, headless: bool = True):
    """Execute complete Target shopper workflow."""
    
    print("=" * 70)
    print("TARGET SHOPPER - GROCERY ROUTE OPTIMIZER")
    print("=" * 70)
    
    # Setup output directory
    output_dir = Path(__file__).parent.parent.parent / "project" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create session folder with timestamp
    session_dir = output_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize progress server
    print("Skipping progress server for testing")
    progress_server = None
    progress_server.set_session_path(str(session_dir))
    progress = ProgressTracker(session_dir)
    
    # Task 1: Use hardcoded Vestal store
    print("\n[1/8] Loading store configuration...")
    # progress_server.task_start(1, "Loading store config...")
    store_result = STORE_CONFIG
    print(f"  ✓ Store: {store_result['name']} (ID: {store_result['store_id']})")
    print(f"  ✓ URL: {store_result['url']}")
    # progress_server.log(f"Store: {store_result['name']}", "success")
    # progress_server.task_complete(1, "Config loaded")
    progress.log(1, "Store Configuration", "COMPLETE")
    
    # Task 2: Parallel Item Search
    print(f"\n[2/8] Searching for {len(items)} items...")
    # progress_server.task_start(2, f"Searching {len(items)} items...")
    search_results = parallel_search(items, store_result["url"], headless=headless)
    
    available = sum(1 for r in search_results if r.get("available"))
    print(f"  ✓ Found: {available}/{len(items)} items")
    # progress_server.log(f"Found {available}/{len(items)} items", "success")
    # progress_server.task_complete(2, f"{available}/{len(items)} found")
    progress.log(2, "Parallel Item Search", "COMPLETE", {"Search Results": session_dir / "search_results.json"})
    
    # Save search results
    import json
    with open(session_dir / "search_results.json", "w") as f:
        json.dump(search_results, f, indent=2)
    
    # Task 3: Load cached store map
    print("\n[3/8] Loading cached store map...")
    # progress_server.task_start(3, "Loading map...")
    svg_result = None
    if CACHED_MAP_PATH.exists():
        with open(CACHED_MAP_PATH, 'r') as f:
            svg_content = f.read()
        svg_result = {"svg_content": svg_content}
        
        svg_path = session_dir / "store_map.svg"
        with open(svg_path, "w") as f:
            f.write(svg_content)
        
        print(f"  ✓ Loaded cached map: {CACHED_MAP_PATH.name}")
        # progress_server.log("Map loaded from cache", "success")
        # progress_server.task_complete(3, "Map loaded")
        progress.log(3, "Cached Store Map", "COMPLETE", {"Store Map SVG": svg_path})
    else:
        print("  ⊘ Cached map not found")
        # progress_server.task_failed(3, "Cache missing")
        progress.log(3, "Cached Store Map", "FAILED")
    
    # Task 4: Route Optimizer
    print("\n[4/8] Optimizing route...")
    # progress_server.task_start(4, "Building route...")
    route_coords = None
    route_distance = 0
    
    if svg_result and _cached_maze:
        # Use cached maze data for instant loading
        maze = StoreMaze(svg_result["svg_content"])
        maze.grid_width = _cached_maze["grid_width"]
        maze.grid_height = _cached_maze["grid_height"]
        maze.aisle_labels = {k: tuple(v) for k, v in _cached_maze["aisle_labels"].items()}
        maze.special_locations = {k: tuple(v) for k, v in _cached_maze["special_locations"].items()}
        
        available_aisles = [r["aisle"] for r in search_results if r.get("aisle")]
        if available_aisles:
            stops = ["entrance"] + available_aisles + ["checkout"]
            full_path = []
            total_distance = 0.0
            
            for i in range(len(stops) - 1):
                start = maze.special_locations.get(stops[i]) if stops[i] in ["entrance", "checkout"] else maze.aisle_labels.get(stops[i])
                end = maze.special_locations.get(stops[i+1]) if stops[i+1] in ["entrance", "checkout"] else maze.aisle_labels.get(stops[i+1])
                
                if start and end:
                    segment_path = find_maze_path(maze, start, end)
                    if segment_path:
                        full_path.extend(segment_path[1:] if full_path else segment_path)
                        total_distance += calculate_path_length(segment_path)
            
            if full_path:
                route_coords = full_path
                route_distance = total_distance
                print(f"  ✓ Route: {len(route_coords)} path points")
                print(f"  ✓ Distance: {route_distance:.1f} SVG units")
                # progress_server.log(f"Route: {len(route_coords)} points", "success")
                # progress_server.task_complete(4, f"{len(route_coords)} points")
    
    if not route_coords:
        # progress_server.task_failed(4, "No route")
        progress.log(4, "Route Optimizer", "FAILED")
    
    # Task 5: Route Visualizer
    print("\n[5/8] Generating route visualization...")
    # progress_server.task_start(5, "Drawing route...")
    viz_path = None
    if svg_result and route_coords:
        aisle_positions = maze.aisle_labels
        route_labels = ["entrance"] + [r["aisle"] for r in search_results if r.get("aisle")] + ["checkout"]
        
        viz_path_str = str(session_dir / "route_viz.svg")
        if save_svg_with_route(svg_result, route_coords, route_labels, viz_path_str, aisle_positions):
            print(f"  ✓ Saved: {viz_path_str}")
            # progress_server.task_complete(5, "Visualization saved")
            progress.log(5, "Route Visualizer", "COMPLETE", {"Route Visualization": session_dir / "route_viz.svg"})
            viz_path = viz_path_str
        else:
            # progress_server.task_failed(5, "Save failed")
            progress.log(5, "Route Visualizer", "FAILED")
    
    # Task 6: Report Generator
    print("\n[6/8] Generating grocery report...")
    # progress_server.task_start(6, "Creating report...")
    items_for_report = load_items_from_search(search_results)
    report_path = generate_report(items_for_report, output_dir=str(session_dir))
    print(f"  ✓ Saved: {report_path}")
    # progress_server.task_complete(6, "Report saved")
    progress.log(6, "Report Generator", "COMPLETE", {"Grocery Report": session_dir / "grocery_report.md"})
    
    # Task 7: HTML Generator
    print("\n[7/8] Generating interactive HTML map...")
    # progress_server.task_start(7, "Building HTML map...")
    html_path = None
    if svg_result and route_coords:
        aisle_positions = {aisle: pos for aisle, pos in maze.aisle_labels.items()}
        special_locations = maze.special_locations
        
        html_path = generate_html_map(
            svg_result["svg_content"],
            route_coords,
            search_results,
            aisle_positions,
            special_locations,
            output_path=str(session_dir / "route_map.html"),
        )
        print(f"  ✓ Saved: {html_path}")
        # progress_server.task_complete(7, "Map saved")
        progress.log(7, "HTML Map Generator", "COMPLETE", {"Interactive Map": session_dir / "route_map.html"})
    
    # Task 8: Output Summary
    print("\n[8/8] Generating route summary...")
    # progress_server.task_start(8, "Creating summary...")
    output_path = None
    if route_coords:
        output_path = generate_output_summary(
            search_results,
            route_coords,
            route_distance,
            html_path=html_path,
            svg_path=viz_path,
            output_dir=str(session_dir),
            timestamp=datetime.now(),
        )
        print(f"  ✓ Saved: {output_path}")
        # progress_server.task_complete(8, "Summary saved")
        progress.log(8, "Output Summary", "COMPLETE", {"Route Summary": session_dir / "output.md"})
    
    # Complete workflow
    print("\n" + "=" * 70)
    print("WORKFLOW COMPLETE")
    print("=" * 70)
    print(f"\n📁 Session folder: {session_dir}")
    
    available = sum(1 for r in search_results if r.get("available"))
    total_cost = sum(r.get("price", 0) or 0 for r in search_results if r.get("available"))
    summary = f"✅ {available}/{len(items)} items found (${total_cost:.2f}) • Route: {len(route_coords) if route_coords else 0} points"
    
    # progress_server.complete(summary)
    
    # Auto-open route map
    import webbrowser
    import time as time_module
    route_map_path = session_dir / "route_map.html"
    if route_map_path.exists():
        print(f"\n🗺️ Opening interactive map...")
        time_module.sleep(2)
        # webbrowser.open(f"file://{route_map_path}")
    
    print(f"\n💡 Dashboard stays open for 60 seconds")
    
    try:
        pass  # No wait
    except KeyboardInterrupt:
        pass
    finally:
        # progress_server.stop()
        print("\n✓ Progress server stopped")
    
    return {"session_dir": session_dir}


if __name__ == "__main__":
    print("Usage: python main.py <item1> [item2] ...")
    print("Example: python main.py eggs milk bread")
    print("Store: Target Binghamton Vestal (ID: 1056) - Hardcoded\n")
    
    headless = "--headless" in sys.argv
    args = [a for a in sys.argv if not a.startswith("--")]
    
    if len(args) < 2:
        print("Running demo with sample items...")
        run_workflow(["eggs", "milk", "bread"], headless=False)
    else:
        items = args[1:]
        run_workflow(items, headless=headless)
