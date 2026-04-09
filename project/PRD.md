# Target Shopper - Product Requirements Document

## Overview
AI assistant that helps users find the shortest path to collect grocery items from Target Binghamton Vestal (Store ID: 1056). Extracts items from user query (or reads `project/list.md` as fallback), fetches real-time aisle/price data from Target.com, and generates an interactive store map with optimal route. All outputs are organized in session folders named `<title>_<date>_<n>` (e.g., `frenchOmelette_20260408_1`). The store location is hardcoded to save runtime computation.

---

## File Structure

```
.agents/skills/target-shopper/
  main.py                (orchestrator script - runs complete workflow)
  SKILL.md               (agent workflow instructions) ✅
  README.md              (user guide - copied to project/) ✅
  tools/
    store_locator.py     (find Target store URL from name) ✅
    item_search.py       (search item, extract aisle/price) ✅
    parallel_search.py   (distribute searches across 4 workers) ✅
    route_optimizer.py   (basic route optimization) ✅
    maze_analyzer.py     (convert SVG to walkability grid) ✅
    maze_pathfinder.py   (A* pathfinding with turn minimization) ✅
    maze_visualizer.py   (debug SVG generation) ✅
    route_visualizer.py  (color-coded route visualization) ✅
    report_generator.py  (generate grocery_report markdown) ✅
    html_generator.py    (generate interactive HTML map) ✅
  templates/
    preferences.md       (user preferences template) ✅
    list.md              (sample grocery list template) ✅
    grocery_report.md    (report table format) ✅
    output.md            (route summary format) ✅
    progress.txt         (item search tracking) ✅
    store_map_vestal.svg (cached store map for Vestal location) ✅

project/
  PRD.md                 (this file)
  list.md                (user's shopping list - optional fallback)
  preferences.md         (saved preferences: store, items, special requests)
  output/
    <title>_<date>_<n>/   (session folder with camelCase title)
      grocery_report.md
      output.md
      route_map.html
      route_viz.svg
      search_results.json
      store_map.svg
      route_coords.json
      progress.txt
      list.md
  test_scripts/
    svg_fetcher.py       (standalone script for fetching store maps - future use)
```
.agents/skills/target-shopper/
  main.py                (orchestrator script - runs complete workflow)
  SKILL.md               (agent workflow instructions) ✅
  README.md              (user guide - copied to project/) ✅
  tools/
    store_locator.py     (find Target store URL from name) ✅
    item_search.py       (search item, extract aisle/price) ✅
    parallel_search.py   (distribute searches across 4 workers) ✅
    svg_fetcher.py       (extract store map SVG via Playwright) ✅
    route_optimizer.py   (basic route optimization) ✅
    maze_analyzer.py     (convert SVG to walkability grid) ✅
    maze_pathfinder.py   (A* pathfinding with turn minimization) ✅
    maze_visualizer.py   (debug SVG generation) ✅
    route_visualizer.py  (color-coded route visualization) ✅
    report_generator.py  (generate grocery_report markdown) ✅
    html_generator.py    (generate interactive HTML map) ✅
  templates/
    preferences.md       (user preferences template) ✅
    list.md              (sample grocery list template) ✅
    grocery_report.md    (report table format) ✅
    output.md            (route summary format) ✅
    progress.txt         (item search tracking) ✅

project/
  PRD.md                 (this file)
  list.md                (user's shopping list - optional fallback)
  preferences.md         (saved preferences: store, items, special requests)
  output/
    <title>_<date>_<n>/   (session folder with camelCase title)
      grocery_report.md
      output.md
      route_map.html
      route_viz.svg
      search_results.json
      store_map.svg
      route_coords.json
      progress.txt
      list.md
```

---

## Task 1: Project Setup & Dependencies
- **Implemented**: true
- **Test Passed**: true
- **Goal**: Create project structure and dependency management
- **Inputs**: None
- **Outputs**: `.agents/skills/target-shopper/` directory, `requirements.txt`, Python environment config
- **Specifications**:
  - Create `tools/` folder with all Python scripts
  - Create `templates/` folder with markdown templates
  - Use `uv` for Python version management (3.11+)
  - `requirements.txt`: `playwright`, `networkx`, `jinja2`, `beautifulsoup4`, `lxml`, `requests`
  - Include setup instructions in SKILL.md
- **Test Case**: Run `uv pip install -r requirements.txt` and `playwright install`
- **Evaluation Criteria**: All dependencies install successfully, Playwright browsers installed, no errors

---

## Task 2: Store Configuration (Hardcoded)
- **Implemented**: true
- **Test Passed**: true
- **Notes**: Store location hardcoded to Target Binghamton Vestal (ID: 1056) to save runtime computation
- **Goal**: Use pre-configured Target store URL
- **Inputs**: None (store is hardcoded)
- **Outputs**: Target store URL (`https://www.target.com/sl/binghamton-vestal/1056`)
- **Specifications**:
  - Store is hardcoded to Binghamton Vestal (ID: 1056)
  - Store URL: `https://www.target.com/sl/binghamton-vestal/1056`
  - Store map SVG layout is cached/pre-extracted for faster route calculation
  - No store search needed - eliminates API calls and user prompts
- **Test Case**: Store URL is always available for Vestal outlet
- **Evaluation Criteria**: Correct URL used, no search delays, map layout available

---

## Task 3: Parallel Item Search Agent (ISOLATE)
- **Implemented**: true
- **Test Passed**: true
- **Notes**: 4 parallel workers, extracts price+aisle, writes to progress.txt
- **Goal**: Search Target.com for each grocery item and extract aisle/price data
- **Inputs**: Item names from user query (primary) or `project/list.md` (fallback), store URL
- **Outputs**: `{item, available, aisle, price, product_url}` per item
- **Specifications**:
  - Maximum 4 parallel subagents for item searches
  - Distribute N items across 4 agents (e.g., 20 items = 5 per agent)
  - Search item on Target.com filtered to selected store
  - Pick cheapest option from top 5 results (flat price, not unit price)
  - Extract aisle location from product page (e.g., "G22", "A15")
  - Mark unavailable items as "missing" in report
  - Each subagent writes to `templates/progress.txt` (append only)
- **Test Case**: Search "eggs", "milk", "bread", "cheese", "butter" (5 items) → Return aisle/price data for each
- **Evaluation Criteria**: Correct aisle extracted, cheapest item selected, missing items flagged, parallel execution completes

---

## Task 4: Cached Store Map Loader
- **Implemented**: true
- **Test Passed**: true
- **Notes**: Vestal store map cached in templates/ with white background fill for visibility
- **Goal**: Load pre-cached SVG store map from templates/store_map_vestal.svg
- **Inputs**: None (map is cached for hardcoded Vestal location)
- **Outputs**: Raw SVG content with aisle markers, white background fill
- **Specifications**:
  - Load cached SVG from `templates/store_map_vestal.svg`
  - SVG includes white background fill (#ffffff) for proper visibility
  - Parse aisle positions from cached SVG for route calculation
  - Fallback: If cache missing, skip map-dependent features (route optimization, visualization)
  - For future: svg_fetcher.py available in project/test_scripts/ to refresh cache
- **Test Case**: Load Vestal store (store ID 1056) cached map
- **Evaluation Criteria**: Valid SVG loaded, background visible, aisle markers present, no network calls

---

## Task 5: Route Optimizer
- **Implemented**: true
- **Test Passed**: true
- **Notes**: Maze-based A* pathfinding, orthogonal routing, turn minimization, multi-floor support with escalator connections
- **Goal**: Calculate shortest walking path through store
- **Inputs**: List of aisles with items, store SVG dimensions, entrance location, checkout location
- **Outputs**: Ordered list of items with path coordinates and sequence
- **Specifications**:
  - Parse SVG for aisle positions and walkable paths
  - Use `networkx` for graph-based pathfinding
  - Path must follow walkable routes (no cutting through aisles/shelves)
  - Start point: store entrance
  - End point: checkout/exit
  - Group items in same aisle together
  - Optimize for shortest total walking distance
  - Version 1: Shortest path only (step count feature deferred)
- **Test Case**: 10 items across 5 aisles → Optimal route from entrance to checkout
- **Evaluation Criteria**: Path is continuous, no aisle cut-through, entrance→checkout, items in same aisle grouped

---

## Task 6: Report Generator (grocery_report_<timestamp>.md)
- **Implemented**: true
- **Test Passed**: true
- **Notes**: Generates markdown table with summary, template saved in templates/
- **Goal**: Generate item availability and pricing report
- **Inputs**: Item search results from Task 3
- **Outputs**: `project/output/grocery_report_<timestamp>.md`
- **Specifications**:
  - Filename format: `grocery_report_YYYYMMDD_HHMMSS.md`
  - Table format with columns: Item | Available | Aisle | Price | Product URL
  - Missing items: Available = "No", Aisle = "N/A", Price = "N/A"
  - Fresh generation each run (no caching of item data)
  - Follow template from `templates/grocery_report.md`
- **Test Case**: 5 items (3 available, 2 missing) → Markdown table with all fields
- **Evaluation Criteria**: Correct table format, all fields populated, missing items clearly marked, timestamp in filename

---

## Task 7: HTML Map Generator
- **Implemented**: false
- **Test Passed**: false
- **Status**: Pending - D3.js interactive visualization

---

## Task 8: Output Summary Generator (output_<timestamp>.md)
- **Implemented**: false
- **Test Passed**: false
- **Status**: Pending - Route summary with statistics

---

## Task 9: SKILL.md Orchestrator with WRITE/SELECT/ISOLATE
- **Implemented**: true
- **Test Passed**: true
- **Status**: Complete - Agent workflow definition with hardcoded Vestal store

---

## Task 10: Edge Case Handler
- **Implemented**: true
- **Test Passed**: true
- **Status**: Complete - Error handling for all failure modes

---

## Task 11: Template Files Creation
- **Implemented**: true
- **Test Passed**: true
- **Status**: Complete - All templates created (preferences.md, output.md, grocery_report.md, progress.txt)

---

## Task 12: README.md for Users
- **Implemented**: false
- **Test Passed**: false
- **Status**: Pending - User documentation
- **Goal**: Generate interactive HTML with store map and route visualization
- **Inputs**: SVG map, route coordinates, item data
- **Outputs**: `project/output/route_map_<timestamp>.html`
- **Specifications**:
  - Filename format: `route_map_<timestamp>.html`
  - Standalone HTML file
  - D3.js loaded via CDN (requires internet connection)
  - Embed SVG store map
  - Add markers at aisle locations showing: aisle number + item name
  - Draw static path line following walkable routes (no animation in v1)
  - Dropdown toggle for view options (e.g., show/hide item names, show/hide path)
  - Color-coded markers (e.g., green = collected, red = missing)
- **Test Case**: Generate HTML with 10-item route visualization
- **Evaluation Criteria**: Map renders correctly, path visible, markers labeled with aisle+item, dropdown functional, no console errors

---

## Stop Conditions
- All 12 tasks implemented and tested
- All output files generate correctly
- Natural language trigger works reliably
- User can successfully run skill end-to-end
- Sub-agent fails repeatedly → Escalate to user
- User cancels

---

## Progress Summary (Updated: 2026-04-08)

### ✅ All Tasks Complete (12/12 - 100%)

**Core Functionality:**
✅ **Task 1**: Project Setup - Directory structure, requirements.txt, .venv  
✅ **Task 2**: Store Configuration - Hardcoded to Target Binghamton Vestal (ID: 1056)  
✅ **Task 3**: Parallel Item Search - 4 workers, aisle+price extraction  
✅ **Task 4**: Cached Store Map Loader - Vestal map cached with white background  
✅ **Task 5**: Route Optimizer - Maze A* pathfinding, orthogonal routing  
✅ **Task 6**: Report Generator - Markdown table with summary  

**Output Generation:**
✅ **Task 7**: HTML Map Generator - D3.js interactive visualization  
✅ **Task 8**: Output Summary - Route statistics with walking distance/time  

**Documentation & Orchestration:**
✅ **Task 9**: SKILL.md - Agent workflow with WRITE/SELECT/ISOLATE patterns  
✅ **Task 10**: Edge Case Handler - Error handling for all failure modes  
✅ **Task 11**: Template Files - preferences.md, output.md, grocery_report.md  
✅ **Task 12**: README.md - Complete user documentation  

### Key Features Implemented

**Core Functionality:**
- ✅ Maze-based A* pathfinding - avoids cutting through aisles, follows walkable corridors
- ✅ Multi-floor support - detects floor selectors, routes via escalator/elevator
- ✅ Hardcoded store - Target Binghamton Vestal (ID: 1056) eliminates search overhead
- ✅ Cached store map - Pre-fetched SVG with white background, no network calls needed
- ✅ Session folder organization - `<title>_<date>_<n>/` format with camelCase titles
- ✅ Color-coded routes - different shades for each path segment
- ✅ Orthogonal routing - 90° turns, minimizes direction changes
- ✅ Parallel item search - 4 workers max, distributes N items efficiently

**Output Generation:**
- ✅ Interactive HTML maps - D3.js visualization with markers, tooltips, view toggles
- ✅ Static SVG visualizations - High-quality vector route maps
- ✅ Grocery reports - Markdown tables with availability, prices, product links
- ✅ Route summaries - Walking distance, time estimates, aisle sequences

**Documentation:**
- ✅ SKILL.md - Complete agent workflow with WRITE/SELECT/ISOLATE patterns
- ✅ README.md - User guide with installation, usage, troubleshooting
- ✅ Template files - preferences.md, output.md, grocery_report.md

### Files Created

**Tools (11 scripts):**
- `main.py` - Orchestrator (coordinates all tasks)
- `store_locator.py` - Store search with city fallback
- `item_search.py` - Item search with aisle/price extraction
- `parallel_search.py` - 4-worker parallel search distribution
- `svg_fetcher.py` - Multi-floor SVG map extraction
- `route_optimizer.py` - Basic route optimization
- `maze_analyzer.py` - SVG to walkability grid conversion
- `maze_pathfinder.py` - A* pathfinding with turn minimization
- `maze_visualizer.py` - Debug SVG generation
- `route_visualizer.py` - Color-coded route overlay
- `report_generator.py` - Grocery report markdown
- `html_generator.py` - Interactive D3.js HTML map
- `output_generator.py` - Route summary with statistics

**Documentation:**
- `SKILL.md` - Agent workflow instructions
- `README.md` - User documentation (copied to project/)
- `templates/preferences.md` - User preferences template
- `templates/output.md` - Route summary template
- `templates/grocery_report.md` - Report template

### Test Results

**Test Case 1: Vestal Store - French Omelette (5 items)**
- Store: Binghamton Vestal (ID: 1056) - Hardcoded
- Items: eggs, butter, salt, black pepper, fresh chives
- Result: ✅ 4/5 found (80%), route: 417 points, 208.0 SVG units

**Test Case 2: Vestal Store - PBJ Sandwich (3 items)**
- Store: Binghamton Vestal (ID: 1056) - Hardcoded
- Items: bread, peanut butter, jelly
- Result: ✅ All found, route optimized

**Test Case 3: Vestal Store - Breakfast Items (demo)**
- Store: Binghamton Vestal (ID: 1056) - Hardcoded
- Items: eggs, milk, bread
- Result: ✅ All found, route: 355 points, 177.0 SVG units

### Known Limitations

1. **Target.com Anti-Bot Protection** - Floating UI overlays may block Playwright automation during peak hours
2. **Real-time Inventory** - Prices/availability may change after search
3. **Multi-floor Routing** - Escalator positions approximated from map labels
4. **Walking Speed Estimates** - Assumes 60 ft/min (leisurely shopping pace)
5. **Single Store Support** - Hardcoded to Target Binghamton Vestal (ID: 1056), other stores not supported

---

## Version Notes
- **Version 1 (Current)**: Shortest path only, static SVG path, D3.js via CDN, hardcoded to Target Binghamton Vestal (ID: 1056)
- **Deferred**: Step count/exercise mode, animated path drawing, unit price comparison, offline mode, multi-store support
