#!/usr/bin/env python3
"""
Output Summary Generator - Generate route summary with statistics.

Creates output_<timestamp>.md with:
- Item order in route
- Aisles visited in sequence
- Total estimated walking distance
- Hyperlink to HTML map
"""

from datetime import datetime
from pathlib import Path
from typing import List, Dict


def generate_output_summary(
    items: List[Dict],
    route_coords: List[tuple],
    route_distance: float,
    html_path: str = None,
    svg_path: str = None,
    report_path: str = None,
    output_dir: str = None,
    timestamp: datetime = None,
) -> str:
    """
    Generate route summary markdown file.

    Args:
        items: List of item dicts with aisle, price, availability
        route_coords: Route path coordinates
        route_distance: Total route distance in SVG units
        html_path: Path to HTML map file
        svg_path: Path to SVG visualization file
        report_path: Path to grocery report file
        output_dir: Output directory (default: project/output)
        timestamp: Generation timestamp

    Returns:
        Path to generated output file
    """
    if timestamp is None:
        timestamp = datetime.now()

    if output_dir is None:
        # Find project root by looking for .git directory
        current = Path(__file__).parent
        while current != current.parent:
            if (current / ".git").exists():
                output_dir = current / "project" / "output"
                break
            current = current.parent
        else:
            output_dir = Path(__file__).parent.parent / "project" / "output"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    filename = "output.md"
    filepath = output_dir / filename

    # Calculate statistics
    total_items = len(items)
    available_items = sum(1 for i in items if i.get("available"))
    missing_items = total_items - available_items
    total_cost = sum(i.get("price", 0) or 0 for i in items if i.get("available"))

    # Get aisles in route order (excluding entrance/checkout)
    aisles_visited = []
    seen_aisles = set()
    for item in items:
        if item.get("available") and item.get("aisle"):
            aisle = item["aisle"]
            if aisle not in seen_aisles:
                aisles_visited.append(aisle)
                seen_aisles.add(aisle)

    # Build items in route order
    items_in_order = []
    for item in items:
        if item.get("available"):
            items_in_order.append(
                {
                    "name": item.get("item", "Unknown"),
                    "aisle": item.get("aisle", "N/A"),
                    "price": item.get("price", 0),
                }
            )

    # Estimate walking distance in feet (assuming 1 SVG unit ≈ 10 feet)
    walking_distance_feet = route_distance * 10

    # Generate relative paths for hyperlinks
    if html_path:
        html_link = Path(html_path).name
    else:
        html_link = None

    if svg_path:
        svg_link = Path(svg_path).name
    else:
        svg_link = None

    # Build content
    content = f"""# Route Summary - {timestamp.strftime("%Y-%m-%d %H:%M:%S")}

## Overview
- **Store:** Target
- **Total items:** {total_items}
- **Available:** {available_items}
- **Missing:** {missing_items}
- **Estimated total:** ${total_cost:.2f}

## Items in Route Order

"""

    for i, item in enumerate(items_in_order, 1):
        content += (
            f"{i}. **{item['name']}** - Aisle {item['aisle']} (${item['price']:.2f})\n"
        )

    if missing_items > 0:
        content += "\n### Missing Items\n\n"
        for item in items:
            if not item.get("available"):
                content += f"- {item.get('item', 'Unknown')}\n"

    content += f"""

## Aisles Visited

{" → ".join(aisles_visited)}

## Statistics

| Metric | Value |
|--------|-------|
| Total walking distance | {walking_distance_feet:.0f} feet ({route_distance:.1f} SVG units) |
| Path points | {len(route_coords)} |
| Unique aisles | {len(aisles_visited)} |
| Items collected | {available_items}/{total_items} |

## Estimated Time

- **Walking time:** ~{max(1, int(walking_distance_feet / 60))} minutes (at 60 ft/min shopping pace)
- **Shopping time:** ~{max(5, int(available_items * 2))} minutes (including item selection)

"""

    if html_link or svg_link:
        content += "## Visualizations\n\n"
        if html_link:
            content += f"- [🗺️ Interactive Route Map]({html_link}) - D3.js visualization with markers and controls\n"
        if svg_link:
            content += (
                f"- [📄 Static Route SVG]({svg_link}) - High-quality vector image\n"
            )
        content += "\n"

    content += f"""---
*Generated: {timestamp.strftime("%Y-%m-%d %H:%M:%S")}*
*Target Shopper AI Assistant*
"""

    filepath.write_text(content)
    return str(filepath)


if __name__ == "__main__":
    # Test with sample data
    test_items = [
        {"item": "milk", "available": True, "aisle": "G10", "price": 3.99},
        {"item": "bread", "available": True, "aisle": "A5", "price": 2.49},
        {"item": "eggs", "available": False, "aisle": None, "price": None},
    ]
    test_route = [(10, 90), (50, 90), (50, 50), (80, 50), (80, 10)]

    output_path = generate_output_summary(
        test_items,
        test_route,
        route_distance=150.5,
        html_path="project/output/route_map_test.html",
        svg_path="project/output/route_viz_test.svg",
    )
    print(f"Generated: {output_path}")
