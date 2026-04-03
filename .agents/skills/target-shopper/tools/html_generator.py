#!/usr/bin/env python3
"""
HTML Map Generator - Generate interactive HTML with D3.js route visualization.

Creates standalone HTML file with:
- Embedded SVG store map
- Interactive markers at aisle locations
- Color-coded route path
- Dropdown toggles for view options
"""

from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import json


def generate_html_map(
    svg_content: str,
    route_coords: List[tuple],
    items: List[Dict],
    aisle_positions: Dict[str, tuple],
    special_locations: Dict[str, tuple],
    output_path: str = None,
    timestamp: datetime = None
) -> str:
    """
    Generate interactive HTML map with D3.js visualization.
    
    Args:
        svg_content: Raw SVG store map content
        route_coords: List of (x, y) coordinates for the route path
        items: List of item dicts with aisle, price, availability
        aisle_positions: Dict mapping aisle labels to (x, y) positions
        special_locations: Dict with entrance, checkout, etc. positions
        output_path: Output file path (default: project/output/route_map_<timestamp>.html)
        timestamp: Generation timestamp
        
    Returns:
        Path to generated HTML file
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    if output_path is None:
        # Navigate from tools/html_generator.py to project/output
        # Path: .agents/skills/target-shopper/tools/ -> ../../../../project/output
        script_dir = Path(__file__).parent
        output_dir = script_dir.parent.parent.parent.parent / "project" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"route_map_{timestamp.strftime('%Y%m%d_%H%M%S')}.html"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Prepare item data for markers
    markers_data = []
    
    # Add entrance marker
    if 'entrance' in special_locations:
        markers_data.append({
            'type': 'entrance',
            'label': 'Entrance',
            'x': special_locations['entrance'][0],
            'y': special_locations['entrance'][1],
            'aisle': None,
            'item': None,
            'price': None
        })
    
    # Add item markers
    for item in items:
        if item.get('available') and item.get('aisle'):
            aisle = item['aisle']
            if aisle in aisle_positions:
                markers_data.append({
                    'type': 'item',
                    'label': aisle,
                    'x': aisle_positions[aisle][0],
                    'y': aisle_positions[aisle][1],
                    'aisle': aisle,
                    'item': item.get('item', 'Unknown'),
                    'price': item.get('price')
                })
    
    # Add checkout marker
    if 'checkout' in special_locations:
        markers_data.append({
            'type': 'checkout',
            'label': 'Checkout',
            'x': special_locations['checkout'][0],
            'y': special_locations['checkout'][1],
            'aisle': None,
            'item': None,
            'price': None
        })
    
    # Convert route coords to D3 path format
    route_path = ""
    if route_coords:
        route_path = "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in route_coords)
    
    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Target Store Route Map - {timestamp.strftime('%Y-%m-%d %H:%M')}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: #c41230;
            color: white;
            padding: 20px;
        }}
        
        .header h1 {{
            font-size: 24px;
            margin-bottom: 8px;
        }}
        
        .header p {{
            opacity: 0.9;
            font-size: 14px;
        }}
        
        .controls {{
            padding: 15px 20px;
            background: #f9f9f9;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            gap: 20px;
            align-items: center;
            flex-wrap: wrap;
        }}
        
        .control-group {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .control-group label {{
            font-weight: 500;
            color: #333;
            font-size: 14px;
        }}
        
        .control-group select,
        .control-group input[type="checkbox"] {{
            cursor: pointer;
        }}
        
        .control-group select {{
            padding: 6px 12px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 14px;
            background: white;
        }}
        
        .map-container {{
            padding: 20px;
            overflow: auto;
            max-height: 80vh;
        }}
        
        #map {{
            width: 100%;
            height: auto;
        }}
        
        .route-path {{
            fill: none;
            stroke-linecap: round;
            stroke-linejoin: round;
            opacity: 0.85;
        }}
        
        .marker {{
            cursor: pointer;
            transition: transform 0.2s;
        }}
        
        .marker:hover {{
            transform: scale(1.2);
        }}
        
        .marker-entrance {{
            fill: #22c55e;
        }}
        
        .marker-checkout {{
            fill: #ef4444;
        }}
        
        .marker-item {{
            fill: #3b82f6;
        }}
        
        .marker-item.missing {{
            fill: #9ca3af;
        }}
        
        .tooltip {{
            position: absolute;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 10px 14px;
            border-radius: 6px;
            font-size: 13px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
            max-width: 250px;
            z-index: 1000;
        }}
        
        .tooltip strong {{
            display: block;
            margin-bottom: 4px;
            font-size: 14px;
        }}
        
        .legend {{
            padding: 15px 20px;
            background: #f9f9f9;
            border-top: 1px solid #e0e0e0;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
            color: #555;
        }}
        
        .legend-color {{
            width: 14px;
            height: 14px;
            border-radius: 3px;
        }}
        
        .stats {{
            padding: 15px 20px;
            background: #fff;
            border-top: 1px solid #e0e0e0;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
        }}
        
        .stat {{
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #c41230;
        }}
        
        .stat-label {{
            font-size: 12px;
            color: #666;
            margin-top: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Target Store Route Map</h1>
            <p>Generated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="controls">
            <div class="control-group">
                <label for="viewToggle">View:</label>
                <select id="viewToggle">
                    <option value="all">Show All</option>
                    <option value="route">Route Only</option>
                    <option value="markers">Markers Only</option>
                    <option value="map">Map Only</option>
                </select>
            </div>
            
            <div class="control-group">
                <label>
                    <input type="checkbox" id="showLabels" checked>
                    Show Labels
                </label>
            </div>
            
            <div class="control-group">
                <label>
                    <input type="checkbox" id="showItemNames" checked>
                    Show Item Names
                </label>
            </div>
            
            <div class="control-group">
                <label>
                    <input type="checkbox" id="showPrices" checked>
                    Show Prices
                </label>
            </div>
        </div>
        
        <div class="map-container">
            <div id="map"></div>
        </div>
        
        <div class="stats" id="stats">
            <div class="stat">
                <div class="stat-value" id="totalItems">0</div>
                <div class="stat-label">Total Items</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="availableItems">0</div>
                <div class="stat-label">Available</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="missingItems">0</div>
                <div class="stat-label">Missing</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="totalCost">$0</div>
                <div class="stat-label">Est. Total</div>
            </div>
        </div>
        
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color" style="background: #22c55e;"></div>
                <span>Entrance</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #3b82f6;"></div>
                <span>Item Location</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #ef4444;"></div>
                <span>Checkout</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: linear-gradient(90deg, #8B0000, #B22222, #DC143C, #E31C23);"></div>
                <span>Route Path</span>
            </div>
        </div>
    </div>
    
    <div class="tooltip" id="tooltip"></div>
    
    <script>
        // Data
        const markersData = {json.dumps(markers_data)};
        const routePath = "{route_path}";
        const routeCoords = {json.dumps(route_coords)};
        
        // Statistics
        const totalItems = {len(items)};
        const availableItems = {sum(1 for i in items if i.get('available'))};
        const missingItems = totalItems - availableItems;
        const totalCost = {sum(i.get('price', 0) or 0 for i in items if i.get('available')):.2f};
        
        document.getElementById('totalItems').textContent = totalItems;
        document.getElementById('availableItems').textContent = availableItems;
        document.getElementById('missingItems').textContent = missingItems;
        document.getElementById('totalCost').textContent = '$' + totalCost;
        
        // Parse SVG viewBox
        const svgContent = `{svg_content.replace('`', '\\`')}`;
        const viewBoxMatch = svgContent.match(/viewBox="([^"]+)"/);
        const viewBox = viewBoxMatch ? viewBoxMatch[1].split(' ').map(Number) : [0, 0, 800, 600];
        
        // Create D3 visualization
        const margin = {{ top: 20, right: 20, bottom: 20, left: 20 }};
        const width = viewBox[2];
        const height = viewBox[3];
        
        const svg = d3.select("#map")
            .append("svg")
            .attr("viewBox", viewBox.join(" "))
            .attr("preserveAspectRatio", "xMidYMid meet")
            .attr("id", "storeMap");
        
        // Embed original store map SVG content (without the outer <svg> tag)
        const svgInner = svgContent.replace(/<svg[^>]*>/, '').replace(/<\\/svg>/, '');
        svg.append("g").html(svgInner);
        
        // Create groups for interactive elements
        const routeGroup = svg.append("g").attr("id", "routeLayer");
        const markerGroup = svg.append("g").attr("id", "markerLayer");
        const labelGroup = svg.append("g").attr("id", "labelLayer");
        
        // Color gradient for route segments
        const routeColors = ["#8B0000", "#B22222", "#DC143C", "#E31C23", "#FF4500", "#FF6347", "#FF7F50", "#FFA07A"];
        
        // Draw route path
        if (routePath) {{
            routeGroup.append("path")
                .attr("d", routePath)
                .attr("class", "route-path")
                .attr("stroke", "#E31C23")
                .attr("stroke-width", 0.5)
                .attr("opacity", 0.85);
            
            // Add arrow marker at end
            svg.append("defs")
                .append("marker")
                .attr("id", "arrowhead")
                .attr("viewBox", "0 0 10 10")
                .attr("refX", 9)
                .attr("refY", 5)
                .attr("markerWidth", 6)
                .attr("markerHeight", 6)
                .attr("orient", "auto")
                .append("path")
                .attr("d", "M 0 0 L 10 5 L 0 10 Z")
                .attr("fill", "#E31C23");
            
            routeGroup.select(".route-path")
                .attr("marker-end", "url(#arrowhead)");
        }}
        
        // Create markers
        const markerRadius = Math.max(width, height) * 0.004;
        
        const markers = markerGroup.selectAll(".marker")
            .data(markersData)
            .enter()
            .append("circle")
            .attr("class", d => `marker marker-${{d.type}}`)
            .attr("cx", d => d.x)
            .attr("cy", d => d.y)
            .attr("r", markerRadius)
            .attr("stroke", "white")
            .attr("stroke-width", markerRadius * 0.3);
        
        // Create labels
        const labels = labelGroup.selectAll(".label")
            .data(markersData)
            .enter()
            .append("g")
            .attr("class", "label-group")
            .attr("transform", d => `translate(${{d.x}}, ${{d.y - markerRadius * 2}})`);
        
        labels.append("text")
            .attr("text-anchor", "middle")
            .attr("font-size", markerRadius * 1.5)
            .attr("font-weight", "bold")
            .attr("fill", "#333")
            .text(d => d.label);
        
        // Item name labels (conditionally shown)
        labels.filter(d => d.item)
            .append("text")
            .attr("class", "item-name")
            .attr("text-anchor", "middle")
            .attr("font-size", markerRadius * 1.2)
            .attr("fill", "#666")
            .attr("dy", markerRadius * 2)
            .text(d => d.item);
        
        // Price labels (conditionally shown)
        labels.filter(d => d.price)
            .append("text")
            .attr("class", "item-price")
            .attr("text-anchor", "middle")
            .attr("font-size", markerRadius)
            .attr("fill", "#22c55e")
            .attr("font-weight", "bold")
            .attr("dy", markerRadius * 3.2)
            .text(d => `$${{d.price.toFixed(2)}}`);
        
        // Tooltip
        const tooltip = d3.select("#tooltip");
        
        markers.on("mouseover", function(event, d) {{
            let content = `<strong>${{d.label}}</strong>`;
            if (d.item) {{
                content += `<div>Item: ${{d.item}}</div>`;
            }}
            if (d.price) {{
                content += `<div>Price: $${{d.price.toFixed(2)}}</div>`;
            }}
            if (d.type === 'entrance') {{
                content += `<div>Start here</div>`;
            }}
            if (d.type === 'checkout') {{
                content += `<div>Pay here</div>`;
            }}
            
            tooltip.html(content)
                .style("opacity", 1)
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 10) + "px");
            
            d3.select(this).attr("stroke", "#c41230").attr("stroke-width", markerRadius * 0.5);
        }})
        .on("mouseout", function() {{
            tooltip.style("opacity", 0);
            d3.select(this).attr("stroke", "white").attr("stroke-width", markerRadius * 0.3);
        }});
        
        // Control handlers
        document.getElementById('viewToggle').addEventListener('change', function() {{
            const value = this.value;
            const routeEl = document.getElementById('routeLayer');
            const markerEl = document.getElementById('markerLayer');
            const labelEl = document.getElementById('labelLayer');
            const svgInner = document.querySelector('#storeMap > g:not(#routeLayer):not(#markerLayer):not(#labelLayer)');
            
            switch(value) {{
                case 'all':
                    routeEl.style.display = 'block';
                    markerEl.style.display = 'block';
                    labelEl.style.display = 'block';
                    svgInner.style.display = 'block';
                    break;
                case 'route':
                    routeEl.style.display = 'block';
                    markerEl.style.display = 'none';
                    labelEl.style.display = 'none';
                    svgInner.style.display = 'none';
                    break;
                case 'markers':
                    routeEl.style.display = 'none';
                    markerEl.style.display = 'block';
                    labelEl.style.display = 'block';
                    svgInner.style.display = 'none';
                    break;
                case 'map':
                    routeEl.style.display = 'none';
                    markerEl.style.display = 'none';
                    labelEl.style.display = 'none';
                    svgInner.style.display = 'block';
                    break;
            }}
        }});
        
        document.getElementById('showLabels').addEventListener('change', function() {{
            labelGroup.selectAll('.label-group').style('display', this.checked ? 'block' : 'none');
        }});
        
        document.getElementById('showItemNames').addEventListener('change', function() {{
            labelGroup.selectAll('.item-name').style('display', this.checked ? 'block' : 'none');
        }});
        
        document.getElementById('showPrices').addEventListener('change', function() {{
            labelGroup.selectAll('.item-price').style('display', this.checked ? 'block' : 'none');
        }});
        
        // Auto-fit to container
        function fitToContainer() {{
            const container = document.querySelector('.map-container');
            const svgEl = document.getElementById('storeMap');
            if (container && svgEl) {{
                const containerWidth = container.clientWidth - 40;
                svgEl.style.width = containerWidth + 'px';
            }}
        }}
        
        window.addEventListener('resize', fitToContainer);
        setTimeout(fitToContainer, 100);
    </script>
</body>
</html>
"""
    
    output_path.write_text(html_content)
    return str(output_path)


if __name__ == "__main__":
    # Test with sample data
    test_svg = '<svg viewBox="0 0 100 100"><g id="test">Test SVG</g></svg>'
    test_route = [(10, 90), (50, 90), (50, 50), (80, 50), (80, 10)]
    test_items = [
        {'item': 'milk', 'available': True, 'aisle': 'G10', 'price': 3.99},
        {'item': 'bread', 'available': True, 'aisle': 'A5', 'price': 2.49},
        {'item': 'eggs', 'available': False, 'aisle': None, 'price': None}
    ]
    test_aisles = {'G10': (50, 50), 'A5': (80, 10)}
    test_special = {'entrance': (10, 90), 'checkout': (80, 50)}
    
    output = generate_html_map(
        test_svg,
        test_route,
        test_items,
        test_aisles,
        test_special
    )
    print(f"Generated: {output}")
