#!/usr/bin/env python3
"""
Maze Visualizer - Generate debug SVG showing walkability grid and paths.
"""

import re
import numpy as np
from typing import List, Tuple, Optional


def extract_group(svg_content: str, group_id: str) -> Optional[str]:
    """Extract a group from SVG with proper nesting handling."""
    start_pattern = f'<g id="{group_id}"'
    start_idx = svg_content.find(start_pattern)
    
    if start_idx == -1:
        # Try without attributes
        start_pattern = f'<g id="{group_id}">'
        start_idx = svg_content.find(start_pattern)
    
    if start_idx == -1:
        return None
    
    # Find the actual opening tag end
    open_tag_end = svg_content.find('>', start_idx)
    if open_tag_end == -1:
        return None
    
    # Count nesting to find matching close tag
    depth = 1
    pos = open_tag_end + 1
    last_close_pos = None
    
    while pos < len(svg_content):
        # Find next <g (with space) or <g> (bare)
        next_open_space = svg_content.find('<g ', pos)
        next_open_bare = svg_content.find('<g>', pos)
        
        # Get the earliest opening
        next_open = None
        if next_open_space != -1 and next_open_bare != -1:
            next_open = min(next_open_space, next_open_bare)
        elif next_open_space != -1:
            next_open = next_open_space
        elif next_open_bare != -1:
            next_open = next_open_bare
        
        next_close = svg_content.find('</g>', pos)
        
        if next_close == -1:
            break
        
        # Check if there's an opening tag before the closing
        if next_open is not None and next_open < next_close:
            depth += 1
            pos = next_open + 1
        else:
            depth -= 1
            last_close_pos = next_close + 4
            if depth == 0:
                # Found matching close tag
                return svg_content[start_idx:next_close + 4]
            pos = next_close + 4
    
    # If we get here, the group wasn't properly closed in the source
    # Return what we have with an added closing tag
    if last_close_pos:
        return svg_content[start_idx:last_close_pos] + '</g>'
    return None


def create_maze_debug_svg(
    maze,
    path: List[Tuple[float, float]] = None,
    waypoint_positions: List[Tuple[float, float]] = None,
    output_path: str = None
) -> str:
    """
    Generate debug visualization showing:
    - Original store map layout (preserved)
    - Path overlay (red line with arrows)
    - Numbered waypoint markers (no text labels on aisles)
    """
    viewBox = maze.viewBox
    original_svg = maze.svg_content
    
    # Create SVG header
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     viewBox="{viewBox.x} {viewBox.y} {viewBox.width} {viewBox.height}"
     width="1600" height="1200">'''
    
    # Add styles
    svg += '''
  <defs>
    <style type="text/css">
      .displayNone { display: none; }
      .adjacency-name { transform: translateY(-1.2301px); font-size: 1.0943px; }
      #Wall-Shapes path { fill: #f5f5f5; stroke: #cccccc; stroke-width: 0.1; }
      #Floor-Pads path { fill: #e0e0e0; stroke: #bbbbbb; stroke-width: 0.1; }
      #Register-Shapes path { fill: #d0d0d0; stroke: #aaaaaa; stroke-width: 0.1; }
      #Aisle-Shapes path { fill: #ffffff; stroke: #dddddd; stroke-width: 0.1; }
      .adjacency-name { fill: #333333; }
      .path-line { stroke: #e31c23; stroke-width: 0.35; fill: none; stroke-linecap: round; stroke-linejoin: round; opacity: 0.9; }
      .waypoint-text { font-family: Arial, sans-serif; font-size: 0.2; font-weight: bold; fill: #fff; }
    </style>
    <marker id="arrowhead" markerWidth="4" markerHeight="3" refX="3" refY="1.5" orient="auto">
      <polygon points="0 0, 4 1.5, 0 3" fill="#e31c23"/>
    </marker>
  </defs>
'''
    
    # Layer 1: Original store map - extract content group only
    svg += '  <!-- Original store map -->\n'
    
    content_group = extract_group(original_svg, 'content')
    if content_group:
        svg += '  ' + content_group + '\n'
    
    # Layer 2: Path overlay with hop arcs at crossings
    if path and len(path) > 1:
        svg += '  <!-- Path overlay -->\n'
        svg += '  <g id="path-overlay">\n'
        
        # Import hop detection from route_visualizer
        try:
            from .route_visualizer import smooth_path_orthogonal, detect_path_crossings, create_hop_arc
            
            # Simplify path for rendering (take every 10th point)
            simplified_path = [path[0]] + path[10:-10:10] + [path[-1]] if len(path) > 20 else path
            
            # Use orthogonal smoothing with hop detection on SIMPLIFIED path
            path_d = smooth_path_orthogonal(simplified_path, turning_radius=0.2, add_hops=True)
            
            # Also add explicit hop arcs based on simplified path
            hop_arcs = []
            if len(simplified_path) >= 10:
                crossing_segments = detect_path_crossings(simplified_path, min_segment_gap=3)
                for seg1, seg2 in crossing_segments:
                    p1, p2 = simplified_path[seg1], simplified_path[seg1 + 1]
                    crossing_x = (p1[0] + p2[0]) / 2
                    crossing_y = (p1[1] + p2[1]) / 2
                    hop_arc = create_hop_arc((crossing_x, crossing_y), hop_height=0.15)
                    hop_arcs.append(hop_arc)
        except ImportError:
            # Fallback: simple line path
            simplified_path = [path[0]] + path[10:-10:10] + [path[-1]] if len(path) > 20 else path
            path_d = f'M {simplified_path[0][0]:.4f} {simplified_path[0][1]:.4f}'
            for x, y in simplified_path[1:]:
                path_d += f' L {x:.4f} {y:.4f}'
            hop_arcs = []
        
        svg += f'    <path d="{path_d}" class="path-line" marker-end="url(#arrowhead)"/>\n'
        
        # Add hop arcs
        # Debug: Add comment showing count
        svg += f'    <!-- Hop arcs: {len(hop_arcs)} detected -->\n'
        for hop_arc in hop_arcs:
            svg += f'    <path d="{hop_arc}" stroke="#e31c23" stroke-width="0.35" '
            svg += f'fill="none" stroke-linecap="round" opacity="0.7"/>\n'
        
        svg += '  </g>\n'
    
    # Layer 3: Waypoint markers (circles only, no text labels)
    if waypoint_positions and len(waypoint_positions) > 0:
        svg += '  <!-- Waypoint markers -->\n'
        svg += '  <g id="waypoint-markers">\n'
        
        for i, (x, y) in enumerate(waypoint_positions):
            # Small circle marker at each waypoint
            svg += f'    <circle cx="{x:.4f}" cy="{y:.4f}" r="0.3" '
            if i == 0:
                svg += f'fill="#22c55e" stroke="#fff" stroke-width="0.1"/>\n'
            elif i == len(waypoint_positions) - 1:
                svg += f'fill="#ef4444" stroke="#fff" stroke-width="0.1"/>\n'
            else:
                svg += f'fill="#3b82f6" stroke="#fff" stroke-width="0.1"/>\n'
        
        svg += '  </g>\n'
    
    svg += '</svg>'
    
    # Save to file if path provided
    if output_path:
        with open(output_path, 'w') as f:
            f.write(svg)
        print(f"Maze debug SVG saved to: {output_path}")
    
    return svg


def create_smoothed_path_svg(
    maze,
    path: List[Tuple[float, float]],
    turning_radius: float = 0.2,
    output_path: str = None
) -> str:
    """Generate SVG with smoothed path (bezier curves)."""
    viewBox = maze.viewBox
    
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     viewBox="{viewBox.x} {viewBox.y} {viewBox.width} {viewBox.height}"
     width="1200" height="900">'''
    
    svg += '''
  <defs>
    <marker id="arrowhead2" markerWidth="5" markerHeight="4" refX="4" refY="2" orient="auto">
      <polygon points="0 0, 5 2, 0 4" fill="#e31c23"/>
    </marker>
  </defs>
'''
    
    # Smooth path with bezier curves
    smoothed_path = smooth_path_with_bezier(path, turning_radius)
    
    svg += f'  <path d="{smoothed_path}" '
    svg += f'stroke="#e31c23" stroke-width="0.15" '
    svg += f'fill="none" stroke-linecap="round" stroke-linejoin="round" '
    svg += f'marker-end="url(#arrowhead2)"/>\n'
    
    svg += '</svg>'
    
    if output_path:
        with open(output_path, 'w') as f:
            f.write(svg)
        print(f"Smoothed path SVG saved to: {output_path}")
    
    return svg


def smooth_path_with_bezier(
    path: List[Tuple[float, float]],
    turning_radius: float = 0.2
) -> str:
    """Convert raw path to smooth SVG path with bezier curves."""
    if len(path) < 2:
        return ""
    
    if len(path) == 2:
        return f"M {path[0][0]:.4f} {path[0][1]:.4f} L {path[1][0]:.4f} {path[1][1]:.4f}"
    
    svg_path = f"M {path[0][0]:.4f} {path[0][1]:.4f}"
    
    for i in range(1, len(path) - 1):
        p0 = path[i - 1]
        p1 = path[i]
        p2 = path[i + 1]
        
        dx1 = p1[0] - p0[0]
        dy1 = p1[1] - p0[1]
        dx2 = p2[0] - p1[0]
        dy2 = p2[1] - p1[1]
        
        len1 = np.sqrt(dx1**2 + dy1**2)
        len2 = np.sqrt(dx2**2 + dy2**2)
        
        if len1 > 0 and len2 > 0:
            dx1, dy1 = dx1 / len1, dy1 / len1
            dx2, dy2 = dx2 / len2, dy2 / len2
            
            dot_product = dx1 * dx2 + dy1 * dy2
            
            if dot_product < 0.9:
                cp_x = p1[0] - dx1 * turning_radius
                cp_y = p1[1] - dy1 * turning_radius
                end_x = p1[0] + dx2 * turning_radius
                end_y = p1[1] + dy2 * turning_radius
                
                svg_path += f" Q {cp_x:.4f} {cp_y:.4f} {end_x:.4f} {end_y:.4f}"
                i += 1
            else:
                svg_path += f" L {p1[0]:.4f} {p1[1]:.4f}"
        else:
            svg_path += f" L {p1[0]:.4f} {p1[1]:.4f}"
    
    svg_path += f" L {path[-1][0]:.4f} {path[-1][1]:.4f}"
    
    return svg_path


if __name__ == '__main__':
    test_path = [(0, 0), (10, 0), (10, 10), (20, 10)]
    smoothed = smooth_path_with_bezier(test_path, turning_radius=0.5)
    print(f"Smoothed path: {smoothed}")
