# Route Summary - {timestamp}

## Overview
- **Store:** {store_name}
- **Total items:** {total_items}
- **Available:** {available_count}
- **Missing:** {missing_count}
- **Estimated total:** ${total_cost}

## Items in Route Order

1. **{item_name}** - Aisle {aisle} (${price})
2. **{item_name}** - Aisle {aisle} (${price})
...

## Aisles Visited

{aisle1} → {aisle2} → ... → {aisleN}

## Statistics

| Metric | Value |
|--------|-------|
| Total walking distance | {distance_feet} feet ({distance_svg} SVG units) |
| Path points | {path_points} |
| Unique aisles | {unique_aisles} |
| Items collected | {available}/{total} |

## Estimated Time

- **Walking time:** ~{walk_time} minutes (at 60 ft/min shopping pace)
- **Shopping time:** ~{shop_time} minutes (including item selection)

## Visualizations

- [🗺️ Interactive Route Map]({html_link}) - D3.js visualization with markers and controls
- [📄 Static Route SVG]({svg_link}) - High-quality vector image

---
*Generated: {timestamp}*
*Target Shopper AI Assistant*
