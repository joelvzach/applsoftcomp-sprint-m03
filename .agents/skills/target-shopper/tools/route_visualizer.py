#!/usr/bin/env python3
"""
Route Visualizer - Draw optimized path on SVG store map.
Supports both maze-based and basic routing.
"""

import re
from typing import List, Dict, Tuple, Optional

try:
    from .maze_visualizer import smooth_path_with_bezier
except ImportError:
    def smooth_path_with_bezier(path, turning_radius=0.2):
        """Fallback: simple line path"""
        if len(path) < 2:
            return ""
        svg_path = f"M {path[0][0]:.4f} {path[0][1]:.4f}"
        for x, y in path[1:]:
            svg_path += f" L {x:.4f} {y:.4f}"
        return svg_path


def parse_svg_viewbox(svg_content: str) -> Tuple[float, float, float, float]:
    """Extract viewBox attributes from SVG."""
    match = re.search(r'viewBox="([^"]+)"', svg_content)
    if match:
        parts = match.group(1).split()
        if len(parts) >= 4:
            return float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])
    return 0.0, 0.0, 0.0, 0.0


def extract_aisle_positions(svg_content: str) -> Dict[str, Tuple[float, float]]:
    """Extract aisle marker positions from SVG text elements."""
    aisles = {}
    
    text_pattern = r'<text[^>]*x="([\d.-]+)"[^>]*y="([\d.-]+)"[^>]*>([A-Z]{1,2}\d{1,3}|CL\d{1,2}|G\d{2,3})</text>'
    
    for match in re.finditer(text_pattern, svg_content):
        x = float(match.group(1))
        y = float(match.group(2))
        aisle = match.group(3)
        
        if aisle not in aisles:
            aisles[aisle] = (x, y)
    
    return aisles


def extract_special_locations(svg_content: str) -> Dict[str, Tuple[float, float]]:
    """Extract entrance, checkout locations from SVG labels."""
    locations = {}
    
    patterns = [
        (r'<text[^>]*x="([\d.-]+)"[^>]*y="([\d.-]+)"[^>]*>entrance</text>', 'entrance'),
        (r'<text[^>]*x="([\d.-]+)"[^>]*y="([\d.-]+)"[^>]*>checkout</text>', 'checkout'),
    ]
    
    for pattern, location in patterns:
        matches = re.findall(pattern, svg_content)
        for x, y in matches:
            if location not in locations:
                try:
                    locations[location] = (float(x), float(y))
                except ValueError:
                    pass
    
    return locations


def create_arrow_marker() -> str:
    """Create SVG arrow marker definition with store map styles."""
    return '''
  <defs>
    <marker id="arrowhead" markerWidth="6" markerHeight="5" 
            refX="5" refY="2.5" orient="auto">
      <polygon points="0 0, 6 2.5, 0 5" fill="#e31c23" opacity="0.8"/>
    </marker>
    <marker id="hop-arrow" markerWidth="6" markerHeight="5" 
            refX="5" refY="2.5" orient="auto">
      <polygon points="0 0, 6 2.5, 0 5" fill="#e31c23" opacity="0.6"/>
    </marker>
  </defs>
  <style type="text/css">
    #background path { fill: #ffffff !important; }
    #Wall-Shapes path { fill: #f5f5f5 !important; stroke: #cccccc; stroke-width: 0.1; }
    #Floor-Pads path { fill: #e0e0e0 !important; stroke: #bbbbbb; stroke-width: 0.1; }
    #Register-Shapes path { fill: #d0d0d0 !important; stroke: #aaaaaa; stroke-width: 0.1; }
    #Aisle-Shapes path { fill: #ffffff !important; stroke: #dddddd; stroke-width: 0.1; }
  </style>
'''


def create_path_elements(
    route: List[Tuple[float, float]],
    route_labels: List[str],
    aisle_positions: Dict[str, Tuple[float, float]],
    special_locations: Dict[str, Tuple[float, float]],
    svg_width: float,
    svg_height: float,
    turning_radius: float = 0.2
) -> str:
    """
    Create SVG elements showing the optimized path with color-coded segments.
    Uses 90-degree turns (orthogonal routing) instead of 45-degree diagonals.
    Each segment between stops has a different shade of red for easy tracking.
    Shows waypoint markers at key stops (entrance, aisles, checkout).
    
    IMPORTANT: route is the full A* path (500+ points), route_labels are the waypoints.
    We build segments between actual waypoint coordinates, NOT by slicing route.
    """
    if len(route) < 2 or not route_labels:
        return ""
    
    svg_elements = create_arrow_marker()
    
    # Build ordered list of waypoint coordinates from route_labels
    # This gives us the actual positions for each stop
    waypoint_coords = []
    waypoint_labels = []
    
    for label in route_labels:
        if label == 'entrance' and 'entrance' in special_locations:
            waypoint_coords.append(special_locations['entrance'])
            waypoint_labels.append(label)
        elif label == 'checkout' and 'checkout' in special_locations:
            waypoint_coords.append(special_locations['checkout'])
            waypoint_labels.append(label)
        elif label in aisle_positions:
            waypoint_coords.append(aisle_positions[label])
            waypoint_labels.append(label)
    
    # Color gradient for route segments (different shades of red/orange)
    segment_colors = [
        '#8B0000',  # Dark red
        '#B22222',  # Fire brick
        '#DC143C',  # Crimson
        '#E31C23',  # Target red
        '#FF4500',  # Orange red
        '#FF6347',  # Tomato
        '#FF7F50',  # Coral
        '#FFA07A',  # Light salmon
    ]
    
    svg_elements += '''
  <!-- Optimized Shopping Route -->
  <g id="shopping-route">
'''
    
    # Draw each segment with different color between consecutive waypoints
    for seg_idx in range(len(waypoint_coords) - 1):
        start_pos = waypoint_coords[seg_idx]
        end_pos = waypoint_coords[seg_idx + 1]
        start_label = waypoint_labels[seg_idx]
        end_label = waypoint_labels[seg_idx + 1]
        
        # Create a simple path between these two waypoints
        # We use the full route to extract the segment between these points
        # Find indices in full route closest to these waypoints
        start_idx_in_route = 0
        end_idx_in_route = len(route) - 1
        
        # Find closest point in route to start_pos
        min_dist = float('inf')
        for i, pt in enumerate(route):
            dist = (pt[0] - start_pos[0])**2 + (pt[1] - start_pos[1])**2
            if dist < min_dist:
                min_dist = dist
                start_idx_in_route = i
        
        # Find closest point in route to end_pos (after start_idx)
        min_dist = float('inf')
        for i in range(start_idx_in_route, len(route)):
            dist = (route[i][0] - end_pos[0])**2 + (route[i][1] - end_pos[1])**2
            if dist < min_dist:
                min_dist = dist
                end_idx_in_route = i
        
        # Extract segment from full route
        segment_route = route[start_idx_in_route:end_idx_in_route + 1]
        
        if len(segment_route) < 2:
            # Fallback: direct line
            segment_route = [start_pos, end_pos]
        
        # Get color for this segment
        color = segment_colors[seg_idx % len(segment_colors)]
        
        # Smooth this segment
        segment_path = smooth_path_orthogonal(segment_route, turning_radius, add_hops=False)
        
        # Add arrow marker only to last segment
        marker_attr = ' marker-end="url(#arrowhead)"' if seg_idx == len(waypoint_coords) - 2 else ''
        
        svg_elements += f'    <!-- Segment {seg_idx + 1}: {start_label} → {end_label} -->\n'
        svg_elements += f'    <path d="{segment_path}" stroke="{color}" stroke-width="0.4" fill="none" '
        svg_elements += f'stroke-linecap="round" stroke-linejoin="round" opacity="0.85"{marker_attr}/>\n'
    
    # Detect crossings for hop arcs (on full route)
    hop_arcs = []
    if len(route) > 10:
        crossing_segments = detect_path_crossings(route, min_segment_gap=5)
        for seg1, seg2 in crossing_segments:
            p1, p2 = route[seg1], route[seg1 + 1]
            crossing_x = (p1[0] + p2[0]) / 2
            crossing_y = (p1[1] + p2[1]) / 2
            hop_arc = create_hop_arc((crossing_x, crossing_y), hop_height=0.15)
            hop_arcs.append(hop_arc)
    
    # Add hop arcs
    if hop_arcs:
        svg_elements += '\n    <!-- Hop arcs at path crossings -->\n'
        for hop_arc in hop_arcs:
            svg_elements += f'    <path d="{hop_arc}" stroke="#e31c23" stroke-width="0.35" '
            svg_elements += f'fill="none" stroke-linecap="round" opacity="0.7"/>\n'
    
    svg_elements += '''
    <!-- Waypoint markers (circles at key stops) -->
'''
    
    # Add markers at actual waypoint locations
    for i, (pos, label) in enumerate(zip(waypoint_coords, waypoint_labels)):
        if label == 'entrance':
            color = '#22c55e'  # Green
        elif label == 'checkout':
            color = '#ef4444'  # Red
        else:
            color = '#3b82f6'  # Blue for aisles
        
        svg_elements += f'    <circle cx="{pos[0]:.4f}" cy="{pos[1]:.4f}" r="0.3" '
        svg_elements += f'fill="{color}" stroke="#fff" stroke-width="0.1"/>\n'
    
    svg_elements += '''  </g>
'''
    
    return svg_elements


def detect_path_crossings(
    route: List[Tuple[float, float]],
    min_segment_gap: int = 5
) -> List[Tuple[int, int]]:
    """
    Detect where path segments cross each other.
    Only reports crossings where segments are at least min_segment_gap apart along the path.
    
    Returns list of (segment_index_1, segment_index_2) pairs.
    """
    crossings = []
    
    def on_segment(p, q, r) -> bool:
        """Check if point q lies on segment pr."""
        if (min(p[0], r[0]) <= q[0] <= max(p[0], r[0]) and
            min(p[1], r[1]) <= q[1] <= max(p[1], r[1])):
            return True
        return False
    
    def orientation(p, q, r) -> int:
        """Find orientation of ordered triplet (p, q, r)."""
        val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
        if abs(val) < 1e-10:
            return 0  # Collinear
        return 1 if val > 0 else 2  # Clockwise or Counterclockwise
    
    def segments_intersect(p1, p2, p3, p4) -> bool:
        """Check if line segment p1-p2 intersects with p3-p4."""
        o1 = orientation(p1, p2, p3)
        o2 = orientation(p1, p2, p4)
        o3 = orientation(p3, p4, p1)
        o4 = orientation(p3, p4, p2)
        
        # General case
        if o1 != o2 and o3 != o4:
            return True
        
        # Special cases (collinear)
        if o1 == 0 and on_segment(p1, p3, p2):
            return True
        if o2 == 0 and on_segment(p1, p4, p2):
            return True
        if o3 == 0 and on_segment(p3, p1, p4):
            return True
        if o4 == 0 and on_segment(p3, p2, p4):
            return True
        
        return False
    
    # Check each pair of non-adjacent segments
    for i in range(len(route) - 1):
        for j in range(i + min_segment_gap, len(route) - 1):
            if segments_intersect(route[i], route[i+1], route[j], route[j+1]):
                crossings.append((i, j))
    
    return crossings


def create_hop_arc(
    crossing_point: Tuple[float, float],
    hop_height: float = 0.15
) -> str:
    """
    Create SVG arc that 'hops' over a path crossing.
    Draws a small semi-circle above the crossing point.
    """
    x, y = crossing_point
    r = hop_height
    
    # Arc from left to right, curving upward
    return f'M {x - r:.4f} {y:.4f} Q {x:.4f} {y - r:.4f} {x + r:.4f} {y:.4f}'


def smooth_path_orthogonal(
    route: List[Tuple[float, float]],
    turning_radius: float = 0.2,
    add_hops: bool = True
) -> str:
    """
    Convert raw path to SVG path with 90-degree (orthogonal) turns.
    Instead of diagonal cuts, routes follow horizontal/vertical corridors.
    
    Args:
        route: List of (x, y) coordinates
        turning_radius: Radius for rounded corners
        add_hops: Whether to add hop arcs at path crossings
    
    Returns:
        SVG path d attribute
    """
    if len(route) < 2:
        return ""
    
    if len(route) == 2:
        return f"M {route[0][0]:.4f} {route[0][1]:.4f} L {route[1][0]:.4f} {route[1][1]:.4f}"
    
    # Detect path crossings for hop arcs
    crossings = set()
    if add_hops and len(route) > 10:
        crossing_segments = detect_path_crossings(route, min_segment_gap=5)
        for seg1, seg2 in crossing_segments:
            # Calculate approximate crossing point
            p1, p2 = route[seg1], route[seg1 + 1]
            p3, p4 = route[seg2], route[seg2 + 1]
            # Use midpoint of first segment as crossing point
            crossing_x = (p1[0] + p2[0]) / 2
            crossing_y = (p1[1] + p2[1]) / 2
            crossings.add((round(crossing_x, 2), round(crossing_y, 2)))
    
    svg_path = f"M {route[0][0]:.4f} {route[0][1]:.4f}"
    
    for i in range(1, len(route) - 1):
        p0 = route[i - 1]
        p1 = route[i]
        p2 = route[i + 1]
        
        # Check if this point is near a crossing
        near_crossing = False
        if crossings:
            for cx, cy in crossings:
                if abs(p1[0] - cx) < 0.3 and abs(p1[1] - cy) < 0.3:
                    near_crossing = True
                    break
        
        # Determine direction of incoming and outgoing segments
        dx1 = p1[0] - p0[0]
        dy1 = p1[1] - p0[1]
        dx2 = p2[0] - p1[0]
        dy2 = p2[1] - p1[1]
        
        # Normalize to get primary direction
        if abs(dx1) > abs(dy1):
            dir1 = 'h' if dx1 > 0 else 'h_rev'
        else:
            dir1 = 'v' if dy1 > 0 else 'v_rev'
        
        if abs(dx2) > abs(dy2):
            dir2 = 'h' if dx2 > 0 else 'h_rev'
        else:
            dir2 = 'v' if dy2 > 0 else 'v_rev'
        
        # If direction changes, add rounded corner
        if dir1 != dir2:
            # Calculate corner point with turning radius
            if dir1 in ['h', 'h_rev']:
                # Coming in horizontally, leaving vertically
                cp_x = p1[0] - (turning_radius if dx1 > 0 else -turning_radius)
                cp_y = p1[1]
                end_x = p1[0]
                end_y = p1[1] + (turning_radius if dy2 > 0 else -turning_radius)
            else:
                # Coming in vertically, leaving horizontally
                cp_x = p1[0]
                cp_y = p1[1] - (turning_radius if dy1 > 0 else -turning_radius)
                end_x = p1[0] + (turning_radius if dx2 > 0 else -turning_radius)
                end_y = p1[1]
            
            # Draw line to corner start, then quarter-circle
            svg_path += f" L {cp_x:.4f} {cp_y:.4f}"
            svg_path += f" Q {p1[0]:.4f} {p1[1]:.4f} {end_x:.4f} {end_y:.4f}"
        else:
            # Same direction, just draw line
            svg_path += f" L {p1[0]:.4f} {p1[1]:.4f}"
    
    # Draw to final point
    svg_path += f" L {route[-1][0]:.4f} {route[-1][1]:.4f}"
    
    return svg_path


def save_svg_with_route(
    svg_data: Dict,
    route: List[Tuple[float, float]],
    route_labels: List[str],
    output_path: str,
    aisle_positions: Dict[str, Tuple[float, float]] = None,
    turning_radius: float = 0.2
) -> bool:
    """
    Save SVG with route visualization.
    Preserves original store map layout, overlays path on top.
    Adds white background to ensure visibility.
    """
    try:
        full_svg = svg_data.get('full_svg') or svg_data.get('svg_content')
        
        if not full_svg:
            return False
        
        # Add white background fill to the background path
        # This ensures the SVG doesn't appear black in viewers
        full_svg = re.sub(
            r'(<g id="background"[^>]*>)(\s*<path d="[^"]+")(>)',
            r'\1\2 fill="#ffffff"\3',
            full_svg
        )
        
        # Also add explicit background style at the beginning
        if '<style' in full_svg:
            # Add to existing style block
            full_svg = re.sub(
                r'(<style[^>]*>)',
                r'\1\n    #background path { fill: #ffffff !important; }',
                full_svg,
                count=1
            )
        else:
            # Add new style block after <svg> tag
            full_svg = re.sub(
                r'(<svg[^>]*>)',
                r'\1\n  <style type="text/css">\n    #background path { fill: #ffffff !important; }\n  </style>',
                full_svg,
                count=1
            )
        
        viewBox = parse_svg_viewbox(full_svg)
        svg_width = viewBox[2]
        svg_height = viewBox[3]
        
        special_locations = extract_special_locations(full_svg)
        
        # Create path elements
        if route and route_labels:
            route_elements = create_path_elements(
                route,
                route_labels,
                aisle_positions or {},
                special_locations,
                svg_width,
                svg_height,
                turning_radius
            )
            if route_elements:
                # Insert before closing </svg> tag
                full_svg = full_svg.replace('</svg>', route_elements + '</svg>')
        
        with open(output_path, 'w') as f:
            f.write(full_svg)
        
        return True
    except Exception as e:
        print(f"Error saving SVG with route: {e}")
        return False


if __name__ == '__main__':
    # Test with sample data
    test_svg = '''<svg viewBox="0 0 100 60" overflow="visible">
        <text x="10" y="10">G44</text>
        <text x="30" y="10">G16</text>
        <text x="85" y="55">entrance</text>
        <text x="70" y="50">checkout</text>
    </svg>'''
    
    test_route = [
        (85, 55),  # entrance
        (10, 10),  # G44
        (30, 10),  # G16
        (70, 50),  # checkout
    ]
    test_labels = ['entrance', 'G44', 'G16', 'checkout']
    aisle_positions = extract_aisle_positions(test_svg)
    special = extract_special_locations(test_svg)
    
    viewBox = parse_svg_viewbox(test_svg)
    result = create_path_elements(
        test_route, test_labels, aisle_positions, special,
        viewBox[2], viewBox[3], turning_radius=0.2
    )
    print(result)
