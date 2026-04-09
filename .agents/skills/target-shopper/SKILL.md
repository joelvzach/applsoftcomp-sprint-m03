---
name: target-shopper
description: Help users find the optimal path to collect grocery items from Target Binghamton Vestal. Extracts items from user query (or uses project/list.md as fallback), fetches aisle/price data from Target.com, and generates session folder with interactive store map and optimized route.
---

# Target Shopper AI Assistant - Skill Instructions

## Overview

This skill helps users find the optimal path to collect grocery items from Target Binghamton Vestal (Store ID: 1056). It extracts items from user query (or reads `project/list.md` as fallback), fetches real-time aisle/price data from Target.com, and generates an interactive store map with optimized route. All outputs are organized in session folders: `project/output/<title>_<date>_<n>/`. The store location is hardcoded to save runtime computation.

---

## Trigger Pattern

**Activate when user query contains:**
- "Target" OR "store" OR "shopping" + route-related terms
- Examples:
  - "show me my target shopping grocery route for eggs, milk, bread"
  - "generate my target route"
  - "find items at Target: butter, salt, chives"
  - "shopping list for french omelette"

---

## WRITE Section (User Preferences)

**Before starting, save/update user preferences to `project/preferences.md`:**

1. **Store is hardcoded** to Binghamton Vestal (ID: 1056) - no extraction needed
2. **Extract item preferences** if mentioned (e.g., "always pick organic", "avoid brand X")
3. **Extract special requests** (e.g., "keep cold items together", "budget under $50")
4. **Save as bullet points** in free-form format (not key-value)

Example `project/preferences.md`:
```markdown
# User Preferences

## Store Location
- Default store: Binghamton Vestal (ID: 1056)
- Store URL: https://www.target.com/sl/binghamton-vestal/1056

## Item Preferences
- Always pick organic when available
- Prefer Good & Gather brand

## Special Requests
- Keep cold items together
- Budget under $50
```

---

## SELECT Section (Context Retrieval)

**Before responding, read relevant context:**

1. **`project/preferences.md`** - Saved preferences and default store
2. **`project/list.md`** - Shopping list (fallback if user didn't provide items)
3. **`project/output/`** - Recent session folders if user asks about past runs
4. **Previous reports** if user asks questions about historical data

**Item extraction priority:**
1. Extract items directly from user query (primary)
2. If no items in query, check `project/list.md` (fallback)
3. If neither, prompt user to provide shopping list

**Session folder naming:**
- Format: `<camelCaseTitle>_<YYYYMMDD>_<n>/`
- Title: Derived from items or user-provided context (e.g., "frenchOmelette")
- Date: Current date in YYYYMMDD format
- Sequence: Daily counter (1st run of day = 1, 2nd = 2, etc.)
- Example: `frenchOmelette_20260408_1/`

---

## ISOLATE Section (Subagent Delegation)

**Maximum 4 parallel subagents for item searches ONLY.**

### Lead Agent Responsibilities:
1. Coordinate all subagents
2. Run sequential tasks (load cached map, route optimize, report gen)
3. Handle errors and edge cases
4. Generate final response with all outputs

### Note on Store Map:
- Store map is **pre-cached** in `templates/store_map_vestal.svg`
- No browser automation or network calls needed for map fetching
- White background fill ensures visibility and proper maze pathfinding
- To refresh cache: use `project/test_scripts/svg_fetcher.py` (standalone script)

### Subagent Delegation Pattern:

```
Lead Agent → spawns up to 4 subagents for item search
Subagent 1: Search items 1-5
Subagent 2: Search items 6-10
Subagent 3: Search items 11-15
Subagent 4: Search items 16-20
```

**Other tasks run sequentially:**
- Store locator (Lead Agent)
- SVG fetcher (Lead Agent)
- Route optimizer (Lead Agent)
- Report generators (Lead Agent)

### Progress Tracking:

**After each task, append to `project/output/progress_<timestamp>.txt`:**

```
[TIMESTAMP] Task N: <Task Name> - <STATUS>
Files Generated:
- [File Name](relative/path/to/file)
- [File Name](relative/path/to/file)
```

**Each subagent also writes to `templates/progress.txt`:**
```
[item_name]: [status: pending/searching/found/missing] - [aisle if found]
```

**Progress file format example:**
```
[2026-04-03 12:30:45] Task 1: Project Setup - COMPLETE
Files Generated:
- requirements.txt (tools/requirements.txt)
- Python environment (.venv/)

[2026-04-03 12:31:02] Task 2: Store Locator - COMPLETE
Files Generated:
- Store Preference (project/preferences.md)
- Store Cache (project/.store_cache.json)

[2026-04-03 12:32:15] Task 3: Parallel Item Search - COMPLETE
Files Generated:
- Search Results (project/output/search_results_<timestamp>.json)
- Progress Log (templates/progress.txt)

[2026-04-03 12:33:40] Task 4: SVG Fetcher - COMPLETE
Files Generated:
- Store Map SVG (project/output/store_map_<timestamp>.svg)

[2026-04-03 12:34:22] Task 5: Route Optimizer - COMPLETE
Files Generated:
- Route Coordinates (project/output/route_coords_<timestamp>.json)

[2026-04-03 12:35:10] Task 6: Report Generator - COMPLETE
Files Generated:
- Grocery Report (project/output/grocery_report_<timestamp>.md)

[2026-04-03 12:35:45] Task 7: HTML Map Generator - COMPLETE
Files Generated:
- Interactive Map (project/output/route_map_<timestamp>.html)

[2026-04-03 12:36:02] Task 8: Output Summary - COMPLETE
Files Generated:
- Route Summary (project/output/output_<timestamp>.md)
- Route Visualization (project/output/route_viz_<timestamp>.svg)
```

---

## Execution Workflow

### Step 1: Store Selection
```python
store = find_store(user_store_preference or saved_default)
if multiple_stores:
    show_numbered_list()
    user_selects()
save_to_preferences(store)
```

### Step 2: Item Search (Parallel - Max 4 Workers)
```python
items = read_shopping_list()
results = parallel_search(items, store.url, max_workers=4)
# Each result: {item, available, aisle, price, product_url}
```

### Step 3: Store Map Fetch
```python
svg_data = fetch_store_map(store.url)
# Returns: {svg_content, aisle_markers, special_locations, floors, ...}
```

### Step 4: Route Optimization (Maze A*)
```python
maze = StoreMaze(svg_data['svg_content'])
route = find_maze_path_through_aisles(maze, items, entrance, checkout)
# Follows walkable corridors, avoids cutting through aisles
# Uses escalator/elevator for multi-floor stores
```

### Step 5: Generate Outputs
```python
# SVG visualization
save_svg_with_route(svg_data, route, items)

# Interactive HTML map
generate_html_map(svg_data, route, items)

# Grocery report
generate_report(items)

# Route summary
generate_output_summary(items, route, html_path)
```

---

## Output Files

All outputs saved to `project/output/`:

| File | Format | Description |
|------|--------|-------------|
| `grocery_report_<timestamp>.md` | Markdown | Item availability table with prices |
| `route_map_<timestamp>.html` | HTML | Interactive D3.js map with markers |
| `route_viz_<timestamp>.svg` | SVG | Static route visualization |
| `output_<timestamp>.md` | Markdown | Route summary with statistics |

---

## Error Handling

### Store Not Found
- Show message: "No stores found for '{query}'"
- Suggest: "Try using a city name, ZIP code, or store ID"
- Continue with text-only output if user provides alternative

### Item Search Fails
- Mark item as "missing" in report
- Continue with remaining items
- Show clear status in output

### SVG Fetch Fails
- Continue with text-only outputs (grocery_report.md, output.md)
- Note in output: "Store map unavailable"
- Suggest retry later

### Target.com Unreachable
- Show error: "Target.com is currently unreachable"
- Suggest: "Please check your internet connection and retry"
- Gracefully exit without crashing

---

## Natural Language Response Format

**After generating all outputs, respond with:**

```
✅ **Route Generated Successfully!**

**Store:** {store_name}

**Items Found:** {available}/{total} ({missing} missing)

**Total Cost:** ${total_cost}

**Route:** {distance_feet} feet through {unique_aisles} aisles

### Outputs Generated:
- 📄 [Grocery Report]({report_link}) - Item availability and prices
- 🗺️ [Interactive Map]({html_link}) - D3.js visualization
- 📊 [Route Summary]({output_link}) - Walking distance and time estimate

**Missing Items:**
- {item1}
- {item2}

View the interactive map in your browser to see the complete route!
```

---

## Testing

**Test Case:** Run with query:
> "show me my target shopping grocery route"

With items in `project/list.md` (e.g., French omelette: eggs, butter, salt, chives).

**Evaluation Criteria:**
- ✅ All 4 output files generated correctly
- ✅ Route is optimal (no aisle cut-through)
- ✅ Store is hardcoded to Binghamton Vestal (ID: 1056)
- ✅ No errors or crashes
- ✅ Natural language response includes all key information

---

## Version Notes

**Version 1 (Current):**
- Shortest path only (maze-based A* pathfinding)
- Static SVG path visualization
- D3.js interactive map via CDN
- Multi-floor support with escalator/elevator detection

**Deferred Features:**
- Step count/exercise mode
- Animated path drawing
- Unit price comparison
- Offline mode
- Real-time inventory checking
