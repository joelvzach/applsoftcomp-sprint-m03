# Target Shopper - Product Requirements Document

## Overview
AI assistant that helps users find the shortest path to collect grocery items from a specified Target store. Reads shopping list from `project/list.md`, fetches real-time aisle/price data from Target.com, and generates an interactive store map with optimal route.

---

## File Structure

```
.agents/skills/target-shopper/
  PRD.md                 (this file)
  SKILL.md               (agent workflow instructions)
  README.md              (user guide - copied to project/)
  tools/
    store_locator.py     (find Target store URL from name)
    item_search.py       (search item, extract aisle/price)
    svg_fetcher.py       (extract store map SVG via Playwright)
    route_optimizer.py   (calculate shortest path with networkx)
    report_generator.py  (generate grocery_report markdown)
    html_generator.py    (generate interactive HTML map)
  templates/
    preferences.md       (user preferences template)
    list.md              (sample grocery list template)
    grocery_report.md    (report table format)
    output.md            (route summary format)
    progress.txt         (item search tracking)

project/
  list.md                (user's shopping list)
  preferences.md         (saved preferences: store, items, special requests)
  output/
    grocery_report_<timestamp>.md
    output_<timestamp>.md
    route_map_<timestamp>.html
```

---

## Task 1: Project Setup & Dependencies
- **Implemented**: false
- **Test Passed**: false
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
- **Implemented**: false
- **Test Passed**: false
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
- **Implemented**: false
- **Test Passed**: false
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
- **Implemented**: false
- **Test Passed**: false
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
- **Implemented**: false
- **Test Passed**: false
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
- **Implemented**: false
- **Test Passed**: false
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

## Task 8: Output Summary Generator (output_<timestamp>.md)
- **Implemented**: false
- **Test Passed**: false
- **Goal**: Generate route summary with statistics
- **Inputs**: Route data, item list, report data
- **Outputs**: `project/output/output_<timestamp>.md`
- **Specifications**:
  - Filename format: `output_<timestamp>.md`
  - Include: item order in route, aisles visited in sequence, total estimated distance
  - Hyperlink to HTML map file (relative path: `route_map_<timestamp>.html`)
  - Follow template from `templates/output.md`
  - Concise format (not verbose)
- **Test Case**: 10-item route → Summary with all stats and working HTML link
- **Evaluation Criteria**: All statistics present, HTML link clickable and resolves correctly

---

## Task 9: SKILL.md Orchestrator with WRITE/SELECT/ISOLATE
- **Implemented**: false
- **Test Passed**: false
- **Goal**: Define agent workflow with WRITE, SELECT, ISOLATE patterns
- **Inputs**: Natural language query containing "Target" and/or "store" and/or "shopping"
- **Outputs**: All output files generated in `project/output/`
- **Specifications**:

### WRITE Section (User Preferences)
- Save user preferences to `project/preferences.md` in bullet-point format
- Track: preferred store location, item preferences (brands, organic, etc.), special requests about items
- Update preferences when user explicitly states them (e.g., "always pick organic", "avoid brand X")
- Free-form bullet format, not key-value

### SELECT Section (Context Retrieval)
- Before responding, read relevant context:
  - `project/preferences.md` for saved preferences and default store
  - `project/list.md` for shopping list
  - Previous reports if user asks questions about past runs
  - `project/output/` folder for recent outputs
- If user adds questions to consider, review relevant files before responding

### ISOLATE Section (Subagent Delegation)
- Maximum 4 parallel subagents for item searches only
- Other tasks (SVG fetch, route optimize, report gen) run sequentially
- Lead Agent coordinates all subagents
- Subagents report progress to `templates/progress.txt`

### Trigger Pattern
- Match natural language containing: "Target" OR "store" OR "shopping" + route-related terms
- Examples: "show me my target shopping grocery route at Vestal outlet", "generate my target route"

- **Test Case**: Run skill with query "show me my target shopping grocery route at Vestal outlet" with 15 items in list.md
- **Evaluation Criteria**: All files generated correctly, route optimal, preferences saved, no errors

---

## Task 10: Edge Case Handler
- **Implemented**: false
- **Test Passed**: false
- **Goal**: Handle errors and edge cases gracefully
- **Inputs**: Error conditions (missing list.md, store not found, SVG fetch fail, item search fail)
- **Outputs**: User-friendly error messages, graceful degradation
- **Specifications**:
  - If `project/list.md` missing:
    - Prompt user to create it OR
    - If user provides items in prompt, overwrite `project/list.md` with provided items (unless user says "append")
  - If store name ambiguous:
    - Show numbered list of matching stores for user to pick
    - Save selection to `project/preferences.md`
  - If SVG fetch fails:
    - Continue with text-only output (grocery_report.md and output.md)
    - Note in output that map unavailable
  - If item search fails:
    - Mark item as missing in report
    - Continue with remaining items
  - If Target.com is unreachable:
    - Show error message with suggestion to retry
- **Test Case**: Run with missing list.md, invalid store name, unreachable Target.com
- **Evaluation Criteria**: Clear error messages displayed, graceful degradation, no crashes

---

## Task 11: Template Files Creation
- **Implemented**: false
- **Test Passed**: false
- **Goal**: Create all template files under `templates/` folder
- **Inputs**: None
- **Outputs**: Template files in `.agents/skills/target-shopper/templates/`
- **Specifications**:

### templates/preferences.md
```markdown
# User Preferences

## Store Location
- Default store: [store name and URL]

## Item Preferences
- [e.g., Always pick organic when available]
- [e.g., Avoid specific brands]

## Special Requests
- [e.g., Keep cold items together]
- [e.g., Budget constraints]
```

### templates/list.md
```markdown
# Shopping List

- eggs
- milk
- bread
- butter
- cheese
```

### templates/grocery_report.md
```markdown
# Grocery Report - {timestamp}

| Item | Available | Aisle | Price | Product URL |
|------|-----------|-------|-------|-------------|
| {item} | Yes/No | {aisle} | {price} | {url} |
```

### templates/output.md
```markdown
# Route Summary - {timestamp}

## Items in Order
1. {item} - Aisle {aisle}
2. {item} - Aisle {aisle}
...

## Aisles Visited
{aisle1} → {aisle2} → ... → {aisleN}

## Statistics
- Total items: {N}
- Available: {M}
- Missing: {K}
- Estimated walking distance: {X} feet

## Interactive Map
[View Route Map](./route_map_{timestamp}.html)
```

### templates/progress.txt
```
[item_name]: [status: pending/searching/found/missing] - [aisle if found]
```

- **Test Case**: All templates created with correct format
- **Evaluation Criteria**: Templates match specifications, placeholders correctly formatted

---

## Task 12: README.md for Users
- **Implemented**: false
- **Test Passed**: false
- **Goal**: Create user documentation
- **Inputs**: None
- **Outputs**: `project/README.md` (copied from skill template)
- **Specifications**:
  - Explain how to install dependencies (`uv pip install -r requirements.txt`, `playwright install`)
  - How to add items to `list.md`
  - How to run the skill (natural language triggers)
  - How to view outputs in `project/output/`
  - How to set preferences
  - Troubleshooting common issues
  - Copy to `project/README.md` during setup
- **Test Case**: New user follows README and successfully runs skill
- **Evaluation Criteria**: Clear instructions, no missing steps, troubleshooting section helpful

---

## Stop Conditions
- All 12 tasks implemented and tested
- All output files generate correctly
- Natural language trigger works reliably
- User can successfully run skill end-to-end
- Sub-agent fails repeatedly → Escalate to user
- User cancels

---

## Version Notes
- **Version 1 (Current)**: Shortest path only, static SVG path, D3.js via CDN
- **Deferred**: Step count/exercise mode, animated path drawing, unit price comparison, offline mode
