# Target Shopper AI Assistant

AI-powered shopping assistant that generates optimal routes through Target stores.

## Features

- 🎯 **Store Locator** - Find any Target store by name, city, or ZIP code
- 🛒 **Parallel Item Search** - Search up to 4 items simultaneously
- 🗺️ **Interactive Store Maps** - D3.js visualization with aisle markers
- 🚀 **Optimized Routes** - Maze-based A* pathfinding avoids cutting through aisles
- 📊 **Real-time Pricing** - Current prices and availability from Target.com
- 📱 **Multi-floor Support** - Automatically routes via escalator/elevator for multi-level stores

---

## Installation

### Prerequisites

- Python 3.11 or higher
- `uv` for Python version management (recommended)

### Setup

1. **Navigate to the skill directory:**
   ```bash
   cd .agents/skills/target-shopper
   ```

2. **Install dependencies:**
   ```bash
   uv pip install -r requirements.txt
   ```

3. **Install Playwright browsers:**
   ```bash
   playwright install
   ```

4. **Verify installation:**
   ```bash
   python main.py --help
   ```

---

## Usage

### Basic Usage

```bash
python main.py <store_name> <item1> <item2> [item3] ...
```

**Examples:**

```bash
# Search for items at Vestal store
python main.py Vestal eggs milk bread

# Search with city and ZIP code
python main.py "Portland 9800" hand soap calculator

# Search for fried rice ingredients
python main.py "San Francisco" jasmine rice eggs soy sauce sesame oil
```

### Using a Shopping List File

Create `project/list.md` with your items:

```markdown
# Shopping List

- eggs
- milk
- bread
- butter
- cheese
```

Then run:
```bash
# (Future feature - will read from list.md automatically)
```

---

## Output Files

All outputs are saved to `project/output/`:

| File | Description |
|------|-------------|
| `grocery_report_<timestamp>.md` | Item availability table with prices and aisles |
| `route_map_<timestamp>.html` | Interactive D3.js map with route visualization |
| `route_viz_<timestamp>.svg` | Static SVG route visualization |
| `output_<timestamp>.md` | Route summary with walking distance and time estimates |

### Viewing Outputs

**Open interactive map in browser:**
```bash
open project/output/route_map_20260402_123456.html
```

**View grocery report:**
```bash
cat project/output/grocery_report_20260402_123456.md
```

---

## Setting Preferences

Edit `project/preferences.md` to set defaults:

```markdown
# User Preferences

## Store Location
- Default store: Portland East Washington Street (ID: 1419)

## Item Preferences
- Always pick organic when available
- Prefer Good & Gather brand

## Special Requests
- Keep cold items together
- Budget under $50
```

---

## Troubleshooting

### "No stores found" Error

**Cause:** Store name not recognized or Target.com blocking automated requests.

**Solutions:**
- Try just the city name (e.g., "Portland" instead of "Portland 9800")
- Use a specific store ID if known (e.g., "1419")
- Wait a few minutes and retry (rate limiting)

### "Store map button not found" Error

**Cause:** Target.com has anti-bot protection that blocks automated browsers.

**Solutions:**
- Use previously generated SVG files if available
- Try during off-peak hours
- Consider using API-based alternatives (advanced)

### Items Not Found

**Cause:** Search terms too specific or item unavailable at selected store.

**Solutions:**
- Use simpler search terms (e.g., "chicken" instead of "rotisserie chicken")
- Try alternative names (e.g., "hand soap" instead of "handwash soap")
- Check nearby stores

### HTML Map Shows Blank/White Screen

**Cause:** D3.js CDN not loading or SVG embedding issue.

**Solutions:**
- Check internet connection (D3.js loads from CDN)
- Open browser console (F12) for errors
- Use the static SVG file instead

### Python Version Errors

**Cause:** Python version incompatible with dependencies.

**Solutions:**
```bash
# Install correct Python version
uv python install 3.11

# Recreate virtual environment
rm -rf .venv
uv venv
uv pip install -r requirements.txt
```

---

## File Structure

```
.agents/skills/target-shopper/
├── main.py                 # Main orchestrator script
├── SKILL.md                # Agent workflow instructions
├── README.md               # This file
├── requirements.txt        # Python dependencies
├── tools/
│   ├── store_locator.py    # Find Target store URL
│   ├── item_search.py      # Search items, extract aisle/price
│   ├── parallel_search.py  # Distribute searches (4 workers max)
│   ├── svg_fetcher.py      # Extract store map SVG
│   ├── route_optimizer.py  # Basic route optimization
│   ├── maze_analyzer.py    # Convert SVG to walkability grid
│   ├── maze_pathfinder.py  # A* pathfinding with turn minimization
│   ├── maze_visualizer.py  # Debug SVG generation
│   ├── route_visualizer.py # Color-coded route visualization
│   ├── report_generator.py # Generate grocery report
│   ├── html_generator.py   # Generate interactive HTML map
│   └── output_generator.py # Generate route summary
├── templates/
│   ├── preferences.md      # User preferences template
│   ├── grocery_report.md   # Report format template
│   └── output.md           # Summary format template
└── project/
    ├── list.md             # Shopping list
    ├── preferences.md      # Saved preferences
    └── output/             # Generated reports and maps
```

---

## Advanced Usage

### Custom Output Directory

```bash
# (Future feature - specify output path)
python main.py Vestal eggs milk --output ./custom_output
```

### Headless Mode (Faster, No Browser UI)

```bash
python main.py Vestal eggs milk --headless
```

### Verbose Output

```bash
# (Future feature - detailed logging)
python main.py Vestal eggs milk --verbose
```

---

## Limitations

- **Target.com Protection:** Automated browser access may be blocked during peak hours
- **Real-time Inventory:** Prices and availability may change after search
- **Multi-floor Stores:** Escalator/elevator positions approximated from map labels
- **Walking Speed:** Time estimates assume 60 feet/minute (leisurely shopping pace)

---

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review `SKILL.md` for agent workflow details
3. Check `project/output/` for error messages in generated files

---

## Version

**Current:** Version 1.0
- Maze-based A* pathfinding
- Multi-floor support
- Interactive D3.js maps
- Parallel item search (4 workers)

**Planned:**
- Step count/exercise mode
- Animated path drawing
- Unit price comparison
- Offline mode
