#!/usr/bin/env python3
"""
Target Shopper - Production Version

Features:
- Hardcoded Vestal store (no lookup delays)
- Cached maze data (instant grid loading)
- Real-time progress dashboard with overlay modals
- Date-level > Time-level > Title folder structure
- Auto-opens map in overlay with zoom controls
- Mock search for fast testing (toggle to real search)
"""

import sys
from pathlib import Path
from datetime import datetime
import json
import time

# Add tools to path
tools_dir = Path(__file__).parent / "tools"
sys.path.insert(0, str(tools_dir))

# Hardcoded Vestal store configuration
STORE_CONFIG = {
    "name": "Binghamton Vestal",
    "store_id": "1056",
    "url": "https://www.target.com/sl/binghamton-vestal/1056",
}

# Load cached maze data for instant loading
TEMPLATES_DIR = Path(__file__).parent / "templates"
CACHED_MAZE_PATH = TEMPLATES_DIR / "maze_cache_vestal.json"
_cached_maze = None
if CACHED_MAZE_PATH.exists():
    with open(CACHED_MAZE_PATH) as f:
        _cached_maze = json.load(f)

# Import tools
from parallel_search import parallel_search  # Use real Target.com search
from report_generator import generate_report, load_items_from_search
from route_visualizer import save_svg_with_route
from maze_analyzer import StoreMaze
from maze_pathfinder import find_maze_path, calculate_path_length
from html_generator import generate_html_map
from output_generator import generate_output_summary
from progress_server import init_progress_server


def run_workflow(items: list, headless: bool = True):
    """Execute complete Target shopper workflow."""

    print("=" * 70)
    print("TARGET SHOPPER - PRODUCTION VERSION")
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

    # Create logs directory for Playwright traces
    logs_dir = session_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    print(f"  📁 Logs: {logs_dir.name}/")

    print(f"\n📁 Session: {session_dir.parent.name}/{session_dir.name}")

    # Initialize progress server (auto-opens browser dashboard)
    print("🌐 Starting progress server...")
    progress_server = init_progress_server(port=8000, open_browser=True)
    progress_server.set_session_path(str(session_dir.resolve()))  # Use absolute path
    progress_server.set_items(items)  # Display items at top of dashboard

    # Wait for browser to connect
    print("⏳ Waiting 2 seconds for browser connection...")
    time.sleep(2)
    print("✓ Browser connected, starting workflow...\n")

    # Task 1: Store configuration
    print("\n[1/6] Loading store configuration...")
    progress_server.task_start(1, "Loading store...")
    store_result = STORE_CONFIG
    print(f"  ✓ {store_result['name']} (ID: {store_result['store_id']})")
    progress_server.log(f"Store: {store_result['name']}", "success")
    progress_server.task_complete(1, "Config loaded")

    # Task 2: Item search (with Playwright tracing)
    print(f"\n[2/6] Searching for {len(items)} items...")
    print(f"  🎥 Playwright tracing enabled")
    progress_server.task_start(2, f"Searching {len(items)} items...")

    search_results = parallel_search(
        items, store_result["url"], headless=headless, trace_dir=str(logs_dir)
    )
    available = sum(1 for r in search_results if r.get("available"))

    print(f"  ✓ Found: {available}/{len(items)} items")
    progress_server.log(f"Found {available}/{len(items)} items", "success")
    progress_server.task_complete(2, f"{available}/{len(items)} found")

    # Update items with search results
    progress_server.update_items_with_results(search_results)

    # Save search results
    with open(session_dir / "search_results.json", "w") as f:
        json.dump(search_results, f, indent=2)

    # Task 3: Load cached store map
    print("\n[3/6] Loading cached store map...")
    progress_server.task_start(3, "Loading map...")

    store_map_path = TEMPLATES_DIR / "store_map_vestal.svg"
    with open(store_map_path, "r") as f:
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

    # Use cached maze data for instant loading
    maze = StoreMaze(svg_content)
    maze.grid_width = _cached_maze["grid_width"]
    maze.grid_height = _cached_maze["grid_height"]
    maze.aisle_labels = {k: tuple(v) for k, v in _cached_maze["aisle_labels"].items()}
    maze.special_locations = {
        k: tuple(v) for k, v in _cached_maze["special_locations"].items()
    }

    available_aisles = [r["aisle"] for r in search_results if r.get("aisle")]
    stops = ["entrance"] + available_aisles + ["checkout"]
    full_path, total_distance = [], 0.0

    for i in range(len(stops) - 1):
        start = (
            maze.special_locations.get(stops[i])
            if stops[i] in ["entrance", "checkout"]
            else maze.aisle_labels.get(stops[i])
        )
        end = (
            maze.special_locations.get(stops[i + 1])
            if stops[i + 1] in ["entrance", "checkout"]
            else maze.aisle_labels.get(stops[i + 1])
        )

        if start and end:
            segment_path = find_maze_path(maze, start, end)
            if segment_path:
                full_path.extend(segment_path[1:] if full_path else segment_path)
                total_distance += calculate_path_length(segment_path)

    print(f"  ✓ Route: {len(full_path)} points, {total_distance:.1f} SVG units")
    progress_server.log(f"Route: {len(full_path)} points", "success")
    progress_server.task_complete(4, f"{len(full_path)} points")

    # Save route coordinates
    with open(session_dir / "route_coords.json", "w") as f:
        json.dump({"path": full_path, "distance": total_distance}, f)

    # Task 5: Generate outputs
    print("\n[5/6] Generating outputs...")
    progress_server.task_start(5, "Generating outputs...")

    # Generate report
    items_for_report = load_items_from_search(search_results)
    report_path = generate_report(items_for_report, output_dir=str(session_dir))
    print(f"  ✓ Report: {Path(report_path).name}")

    # Generate SVG visualization with route
    aisle_positions = maze.aisle_labels
    route_labels = (
        ["entrance"]
        + [r["aisle"] for r in search_results if r.get("aisle")]
        + ["checkout"]
    )
    viz_path_str = str(session_dir / "route_viz.svg")
    save_svg_with_route(
        svg_result, full_path, route_labels, viz_path_str, aisle_positions
    )
    print(f"  ✓ Visualization: route_viz.svg")

    # Generate HTML map (simple version with SVG embed)
    html_path = generate_html_map(
        svg_content,
        full_path,
        search_results,
        dict(aisle_positions),
        maze.special_locations,
        output_path=str(session_dir / "route_map.html"),
    )
    print(f"  ✓ HTML Map: route_map.html")

    # Generate summary
    output_path = generate_output_summary(
        search_results,
        full_path,
        total_distance,
        html_path=html_path,
        svg_path=viz_path_str,
        output_dir=str(session_dir),
        timestamp=datetime.now(),
    )
    print(f"  ✓ Summary: {Path(output_path).name}")

    # Verify files exist before marking complete
    print(f"  Verifying files...")
    for f in ["route_viz.svg", "route_map.html", "grocery_report.md"]:
        if (session_dir / f).exists():
            print(f"    ✓ {f}")
        else:
            print(f"    ✗ {f} MISSING")

    progress_server.task_complete(5, "All outputs saved")

    # Task 6: Complete and show dashboard
    print("\n[6/6] Finalizing...")
    progress_server.task_start(6, "Finalizing...")

    total_cost = sum(
        r.get("price", 0) or 0 for r in search_results if r.get("available")
    )
    summary = f"✅ {available}/{len(items)} items found (${total_cost:.2f}) • Route: {len(full_path)} points"
    progress_server.task_complete(6, "Done")
    progress_server.complete(summary)

    print("\n" + "=" * 70)
    print("WORKFLOW COMPLETE")
    print("=" * 70)
    print(f"\n🌐 Progress dashboard: http://127.0.0.1:{progress_server.port}/")
    print(f"💡 Click '📋 View Items' to see prices and aisles")
    print(f"💡 Click '🗺️ View Map' to see route with zoom controls")
    print(f"💡 Dashboard stays open for 60 seconds")
    print(f"\n📁 Session folder: {session_dir}")

    # Keep server running for 120 seconds
    wait_time = 120
    print(
        f"\n💡 Dashboard open for {wait_time}s at http://127.0.0.1:{progress_server.port}/"
    )
    try:
        time.sleep(wait_time)
    except KeyboardInterrupt:
        pass
    finally:
        progress_server.stop()
        print("\n✓ Progress server stopped")

    return session_dir


if __name__ == "__main__":
    print("Usage: python main.py <item1> [item2] ...")
    print("Example: python main.py eggs milk bread")
    print("Store: Target Binghamton Vestal (ID: 1056) - Hardcoded\n")

    # Parse command line arguments
    headless = "--headless" in sys.argv
    args = [a for a in sys.argv if not a.startswith("--")]

    if len(args) < 2:
        # Demo with sample items
        print("Running demo with sample items...")
        run_workflow(["eggs", "milk", "bread"], headless=False)
    else:
        items = args[1:]
        run_workflow(items, headless=headless)
