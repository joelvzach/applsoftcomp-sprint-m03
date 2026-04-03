# Target Shopper AI Assistant - Skill Instructions

## Overview

This skill helps users find the optimal path to collect grocery items from a specified Target store. It reads a shopping list, fetches real-time aisle/price data from Target.com, and generates an interactive store map with an optimized route.

---

## Trigger Pattern

**Activate when user query contains:**
- "Target" OR "store" OR "shopping" + route-related terms
- Examples:
  - "show me my target shopping grocery route at Vestal outlet"
  - "generate my target route"
  - "find items at Target Portland"
  - "shopping list for Target"

---

## WRITE Section (User Preferences)

**Before starting, save/update user preferences to `project/preferences.md`:**

1. **Extract store preference** from user query (e.g., "Vestal", "Portland 9800")
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
2. **`project/list.md`** - Shopping list (if not provided in query)
3. **`project/output/`** - Recent outputs if user asks about past runs
4. **Previous reports** if user asks questions about historical data

**If `project/list.md` is missing:**
- Check if user provided items in the prompt
- If yes, create `project/list.md` with provided items
- If no, prompt user to provide shopping list

---

## ISOLATE Section (Subagent Delegation)

**Maximum 4 parallel subagents for item searches ONLY.**

### Lead Agent Responsibilities:
1. Coordinate all subagents
2. Run sequential tasks (SVG fetch, route optimize, report gen)
3. Handle errors and edge cases
4. Generate final response with all outputs

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

Each subagent writes to `templates/progress.txt`:
```
[item_name]: [status: pending/searching/found/missing] - [aisle if found]
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
> "show me my target shopping grocery route at Vestal outlet"

With 15 items in `project/list.md`.

**Evaluation Criteria:**
- ✅ All 4 output files generated correctly
- ✅ Route is optimal (no aisle cut-through)
- ✅ Preferences saved to `project/preferences.md`
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
