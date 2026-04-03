# Target Shopper - Product Requirements Document

## Overview
AI assistant that helps users find the shortest path to collect grocery items from a specified Target store. Reads shopping list from `project/list.md`, fetches real-time aisle/price data from Target.com, and generates an interactive store map with optimal route.

---

## File Structure

```
.agents/skills/target-shopper/
  main.py                (orchestrator script - runs complete workflow)
  SKILL.md               (agent workflow instructions) [TODO]
  README.md              (user guide - copied to project/) [TODO]
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
    html_generator.py    (generate interactive HTML map) [TODO]
  templates/
    preferences.md       (user preferences template) [TODO]
    list.md              (sample grocery list template) [exists in project/]
    grocery_report.md    (report table format) ✅
    output.md            (route summary format) [TODO]
    progress.txt         (item search tracking) [TODO]

project/
  PRD.md                 (this file)
  list.md                (user's shopping list)
  preferences.md         (saved preferences: store, items, special requests)
  output/
    grocery_report_<timestamp>.md
    output_<timestamp>.md
    route_map_<timestamp>.html
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

## Task 2: Store Locator & URL Builder
- **Implemented**: true
- **Test Passed**: true
- **Notes**: Supports city+zip fallback, auto-selects most common city
- **Goal**: Convert user-provided store name to Target store URL
- **Inputs**: Store name from user query (e.g., "Vestal", "Binghamton")
- **Outputs**: Target store URL (e.g., `https://www.target.com/sl/binghamton-vestal/1056`)
- **Specifications**:
  - Search Target.com store locator for matching stores
  - If multiple matches found, display numbered list for user to pick
  - Save confirmed store to `project/preferences.md` as default for future runs
  - Extract store ID from URL for subsequent API calls
  - If user specifies different store in future query, update preference
- **Test Case**: Input "Vestal" → Output store URL; Input ambiguous name → Show options
- **Evaluation Criteria**: Correct URL returned, user prompted if ambiguous, preference saved to `project/preferences.md`

---

## Task 3: Parallel Item Search Agent (ISOLATE)
- **Implemented**: true
- **Test Passed**: true
- **Notes**: 4 parallel workers, extracts price+aisle, writes to progress.txt
- **Goal**: Search Target.com for each grocery item and extract aisle/price data
- **Inputs**: Item name from `project/list.md`, store URL
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

## Task 4: Store Map SVG Fetcher
- **Implemented**: true
- **Test Passed**: true
- **Notes**: Multi-floor support, extracts vertical connections (escalator/elevator)
- **Goal**: Extract SVG store map via Playwright browser automation
- **Inputs**: Store URL
- **Outputs**: Raw SVG content with aisle markers
- **Specifications**:
  - Navigate to store page using Playwright
  - Click "Store Map" button to open modal
  - Wait for SVG element to fully load (up to 10 seconds)
  - Extract complete SVG element including aisle markers/labels
  - Parse aisle positions from SVG for route calculation
- **Test Case**: Fetch Vestal store (store ID 1056) map SVG
- **Evaluation Criteria**: Valid SVG returned, aisle markers present, no truncation

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
- **Implemented**: false
- **Test Passed**: false
- **Status**: Pending - Agent workflow definition

---

## Task 10: Edge Case Handler
- **Implemented**: partial
- **Test Passed**: false
- **Status**: Basic error handling in place, needs comprehensive testing

---

## Task 11: Template Files Creation
- **Implemented**: partial
- **Test Passed**: false
- **Status**: grocery_report.md created, others pending

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

## Progress Summary (Updated: 2026-04-02)

### Completed Tasks (6/12 - 50%)
✅ **Task 1**: Project Setup - Directory structure, requirements.txt, .venv  
✅ **Task 2**: Store Locator - City/zip search, auto-select most common city  
✅ **Task 3**: Parallel Item Search - 4 workers, aisle+price extraction  
✅ **Task 4**: SVG Fetcher - Multi-floor support, vertical connections  
✅ **Task 5**: Route Optimizer - Maze A* pathfinding, orthogonal routing  
✅ **Task 6**: Report Generator - Markdown table with summary  

### In Progress / Partial (1/12)
🟡 **Task 10**: Edge Case Handler - Basic error handling implemented  

### Pending Tasks (5/12)
❌ **Task 7**: HTML Map Generator - D3.js interactive visualization  
❌ **Task 8**: Output Summary - Route statistics markdown  
❌ **Task 9**: SKILL.md - Agent orchestrator workflow  
❌ **Task 11**: Template Files - preferences.md, output.md, progress.txt  
❌ **Task 12**: README.md - User documentation  

### Key Features Implemented
- **Maze-based pathfinding**: Avoids cutting through aisles, follows walkable corridors
- **Multi-floor support**: Detects floor selectors, routes via escalator/elevator
- **City fallback**: "Portland 9800" → searches "Portland" if zip fails
- **Color-coded routes**: Different shades for each path segment
- **Orthogonal routing**: 90° turns, minimizes direction changes

---

## Version Notes
- **Version 1 (Current)**: Shortest path only, static SVG path, D3.js via CDN
- **Deferred**: Step count/exercise mode, animated path drawing, unit price comparison, offline mode
