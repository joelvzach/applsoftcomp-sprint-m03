#!/usr/bin/env python3
"""
Store Map SVG Fetcher - Extract SVG store map via Playwright browser automation.
Supports multi-floor stores with escalator/elevator connections.
"""

from playwright.sync_api import sync_playwright
from typing import Optional, Dict, List
import re


def detect_floor_selector(page) -> Optional[str]:
    """
    Detect if store has multiple floors and return selector for floor buttons.
    Returns selector pattern or None if single floor.
    """
    # Check for floor selector buttons
    floor_patterns = [
        'button[aria-label*="Floor"]',
        'button[aria-label*="Level"]',
        '[data-floor]',
        '.floor-selector button',
        '.floor-tabs button',
    ]
    
    for pattern in floor_patterns:
        buttons = page.locator(pattern)
        if buttons.count() > 1:
            return pattern
    
    # Check for text indicating multiple floors
    floor_text = page.evaluate(r'''() => {
        const text = document.body.innerText;
        const floorMatches = text.match(/Floor\s*\d+|Level\s*\d+/gi);
        return floorMatches ? [...new Set(floorMatches)] : [];
    }''')
    
    if floor_text and len(floor_text) > 1:
        return 'text'  # Special handling for text-based floor indicators
    
    return None


def extract_floor_data(svg_content: str, floor_num: int = 1) -> Dict:
    """
    Extract aisle and special location data from SVG content.
    """
    # Extract aisle labels from SVG text elements
    aisles = []
    aisle_markers = []
    
    # Match text elements with aisle labels
    text_matches = re.findall(r'<text[^>]*x="([\d.-]+)"[^>]*y="([\d.-]+)"[^>]*>([A-Z]{1,2}\d{1,3}|CL\d{1,2})</text>', svg_content)
    
    for x, y, aisle in text_matches:
        if aisle not in aisles:
            aisles.append(aisle)
        try:
            aisle_markers.append({
                'aisle': aisle,
                'x': float(x),
                'y': float(y)
            })
        except ValueError:
            pass
    
    # Extract special locations (entrance, checkout, escalator, elevator)
    special_locations = {}
    
    patterns = [
        (r'<text[^>]*x="([\d.-]+)"[^>]*y="([\d.-]+)"[^>]*>entrance</text>', 'entrance'),
        (r'<text[^>]*x="([\d.-]+)"[^>]*y="([\d.-]+)"[^>]*>checkout</text>', 'checkout'),
        (r'<text[^>]*x="([\d.-]+)"[^>]*y="([\d.-]+)"[^>]*>escalator</text>', 'escalator'),
        (r'<text[^>]*x="([\d.-]+)"[^>]*y="([\d.-]+)"[^>]*>elevator</text>', 'elevator'),
        (r'<text[^>]*x="([\d.-]+)"[^>]*y="([\d.-]+)"[^>]*>stairs</text>', 'stairs'),
    ]
    
    for pattern, location in patterns:
        for match in re.finditer(pattern, svg_content):
            x = float(match.group(1))
            y = float(match.group(2))
            key = f"{location}_floor{floor_num}" if floor_num > 1 else location
            if key not in special_locations:
                special_locations[key] = (x, y)
    
    return {
        'aisles': aisles,
        'aisle_markers': aisle_markers,
        'special_locations': special_locations
    }


def fetch_store_map(store_url: str, headless: bool = True) -> Optional[Dict]:
    """
    Navigate to store page, click Store Map button, and extract SVG(s).
    Handles multi-floor stores by fetching each floor's map.
    Returns: {floors: [{svg_content, aisles, aisle_markers, ...}], vertical_connections}
    """
    with sync_playwright() as p:
        browser = p.webkit.launch(headless=headless)
        page = browser.new_page()
        
        try:
            page.goto(store_url, timeout=30000, wait_until='domcontentloaded')
            page.wait_for_timeout(2000)
            
            map_btn = page.locator('button:has-text("Store Map")').first
            
            if map_btn.count() == 0:
                print("Store map button not found")
                return None
            
            map_btn.click()
            page.wait_for_timeout(5000)
            
            modal = page.locator('[role="dialog"]').first
            
            if modal.count() == 0:
                print("Map modal not found")
                return None
            
            # Check for multiple floors
            floor_selector = detect_floor_selector(page)
            floors_data = []
            vertical_connections = []
            
            if floor_selector:
                # Multi-floor store - fetch each floor
                if floor_selector == 'text':
                    # Text-based floor detection - likely single floor with floor mentions
                    floor_count = 1
                else:
                    # Button-based floor selector
                    floor_buttons = page.locator(floor_selector)
                    floor_count = floor_buttons.count()
                
                print(f"Multi-floor store detected: {floor_count} floor(s)")
                
                for floor_idx in range(floor_count):
                    if floor_selector != 'text':
                        # Click floor button
                        floor_buttons.nth(floor_idx).click()
                        page.wait_for_timeout(2000)
                    
                    # Extract SVG for this floor
                    floor_svg = page.evaluate('''() => {
                        const modal = document.querySelector('[role="dialog"]');
                        if (!modal) return null;
                        
                        const svgs = modal.querySelectorAll('svg');
                        for (const svg of svgs) {
                            const html = svg.outerHTML;
                            if (html.length > 10000) {
                                return html;
                            }
                        }
                        return null;
                    }''')
                    
                    if floor_svg:
                        # Parse SVG attributes
                        attr_match = re.search(r'<svg([^>]+)>', floor_svg)
                        if attr_match:
                            attrs_str = attr_match.group(1)
                            viewBox_match = re.search(r'viewBox="([^"]+)"', attrs_str)
                            viewBox = viewBox_match.group(1) if viewBox_match else ''
                            
                            width, height = 0, 0
                            if viewBox:
                                parts = viewBox.split()
                                if len(parts) >= 4:
                                    width = float(parts[2])
                                    height = float(parts[3])
                            
                            # Extract floor data
                            floor_data = extract_floor_data(floor_svg, floor_idx + 1)
                            
                            floors_data.append({
                                'floor': floor_idx + 1,
                                'svg_content': floor_svg,
                                'full_svg': floor_svg,
                                'aisles': floor_data['aisles'],
                                'aisle_markers': floor_data['aisle_markers'],
                                'special_locations': floor_data['special_locations'],
                                'width': width,
                                'height': height,
                                'viewBox': viewBox
                            })
                            
                            # Look for vertical connections (escalator/elevator positions)
                            if 'escalator' in floor_data['special_locations'] or 'elevator' in floor_data['special_locations']:
                                for key, pos in floor_data['special_locations'].items():
                                    if key.startswith('escalator') or key.startswith('elevator') or key.startswith('stairs'):
                                        vertical_connections.append({
                                            'floor': floor_idx + 1,
                                            'type': key.split('_')[0],
                                            'position': pos
                                        })
                
                if not floors_data:
                    print("No floor SVGs extracted")
                    return None
                
                # Return combined data
                return {
                    'floors': floors_data,
                    'vertical_connections': vertical_connections,
                    'is_multi_floor': len(floors_data) > 1,
                    # For backward compatibility, use floor 1 as default
                    'svg_content': floors_data[0]['svg_content'],
                    'aisles': floors_data[0]['aisles'],
                    'aisle_markers': floors_data[0]['aisle_markers'],
                    'special_locations': floors_data[0]['special_locations'],
                    'width': floors_data[0]['width'],
                    'height': floors_data[0]['height'],
                    'viewBox': floors_data[0]['viewBox'],
                    'full_svg': floors_data[0]['full_svg']
                }
            
            else:
                # Single floor store - original behavior
                full_svg = page.evaluate('''() => {
                    const modal = document.querySelector('[role="dialog"]');
                    if (!modal) return null;
                    
                    const svgs = modal.querySelectorAll('svg');
                    for (const svg of svgs) {
                        const html = svg.outerHTML;
                        if (html.length > 10000) {
                            return html;
                        }
                    }
                    return null;
                }''')
                
                if not full_svg:
                    print("No large SVG found in modal")
                    return None
                
                # Parse SVG attributes
                attr_match = re.search(r'<svg([^>]+)>', full_svg)
                if not attr_match:
                    return None
                
                attrs_str = attr_match.group(1)
                
                # Extract viewBox
                viewBox_match = re.search(r'viewBox="([^"]+)"', attrs_str)
                viewBox = viewBox_match.group(1) if viewBox_match else ''
                
                # Extract width/height from viewBox
                width, height = 0, 0
                if viewBox:
                    parts = viewBox.split()
                    if len(parts) >= 4:
                        width = float(parts[2])
                        height = float(parts[3])
                
                # Extract floor data
                floor_data = extract_floor_data(full_svg, 1)
                
                return {
                    'svg_content': full_svg,
                    'aisles': floor_data['aisles'],
                    'aisle_markers': floor_data['aisle_markers'],
                    'special_locations': floor_data['special_locations'],
                    'width': width,
                    'height': height,
                    'viewBox': viewBox,
                    'full_svg': full_svg,
                    'floors': [{
                        'floor': 1,
                        'svg_content': full_svg,
                        'full_svg': full_svg,
                        'aisles': floor_data['aisles'],
                        'aisle_markers': floor_data['aisle_markers'],
                        'special_locations': floor_data['special_locations'],
                        'width': width,
                        'height': height,
                        'viewBox': viewBox
                    }],
                    'vertical_connections': [],
                    'is_multi_floor': False
                }
            
        except Exception as e:
            print(f"Error fetching store map: {e}")
            return None
        finally:
            browser.close()


def extract_aisles_from_svg(svg_content: str) -> list:
    """Extract aisle labels from SVG text content."""
    aisles = []
    
    aisle_pattern = r'\b([A-Z]{1,2}\d{1,3}|CL\d{1,2})\b'
    
    matches = re.findall(aisle_pattern, svg_content)
    
    seen = set()
    for match in matches:
        if match not in seen:
            seen.add(match)
            aisles.append(match)
    
    aisles.sort(key=lambda x: (x[0], int(x[1:]) if x[1:].isdigit() else 0))
    
    return aisles


def save_svg(svg_data: Dict, output_path: str, highlight_aisles: list = None) -> bool:
    """
    Save SVG to file with proper CSS for standalone rendering.
    Adds highlight markers for specified aisles.
    """
    try:
        full_svg = svg_data.get('full_svg') or svg_data.get('svg_content')
        
        if not full_svg:
            return False
        
        # Add CSS styles for standalone rendering (after opening <svg> tag)
        css_styles = '''
  <defs>
    <style type="text/css">
      .displayNone { display: none; }
      .adjacency-name { transform: translateY(-1.2301px); font-size: 1.0943px; }
      #Wall-Shapes path { fill: #f5f5f5; stroke: #cccccc; stroke-width: 0.1; }
      #Floor-Pads path { fill: #e0e0e0; stroke: #bbbbbb; stroke-width: 0.1; }
      #Register-Shapes path { fill: #d0d0d0; stroke: #aaaaaa; stroke-width: 0.1; }
      #Aisle-Shapes path { fill: #ffffff; stroke: #dddddd; stroke-width: 0.1; }
      .adjacency-name { fill: #333333; }
    </style>
  </defs>
'''
        
        # Insert CSS after opening svg tag
        full_svg = full_svg.replace('overflow="visible">', f'overflow="visible">{css_styles}')
        
        # If highlighting aisles, add markers just before closing </svg>
        if highlight_aisles:
            aisle_markers = svg_data.get('aisle_markers', [])
            
            # Build highlight elements
            highlight_elements = '\n  <!-- Highlighted aisles -->\n'
            highlight_elements += '  <g id="highlighted-aisles">\n'
            
            for marker in aisle_markers:
                if marker['aisle'] in highlight_aisles:
                    x = marker.get('x', 0)
                    y = marker.get('y', 0)
                    # Red circle with white text
                    highlight_elements += f'    <circle cx="{x}" cy="{y}" r="9" fill="none" stroke="#e31c23" stroke-width="2"/>\n'
                    highlight_elements += f'    <circle cx="{x}" cy="{y}" r="7" fill="#e31c23" stroke="#fff" stroke-width="1.5"/>\n'
                    highlight_elements += f'    <text x="{x}" y="{y}" text-anchor="middle" dominant-baseline="central" fill="#fff" font-family="Arial, sans-serif" font-size="11" font-weight="bold">{marker["aisle"]}</text>\n'
            
            highlight_elements += '  </g>\n'
            
            # Insert before closing </svg>
            full_svg = full_svg.replace('</svg>', highlight_elements + '</svg>')
        
        with open(output_path, 'w') as f:
            f.write(full_svg)
        
        return True
    except Exception as e:
        print(f"Error saving SVG: {e}")
        return False


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python svg_fetcher.py <store_url>")
        print("Example: python svg_fetcher.py https://www.target.com/sl/ocean-township/1378")
        sys.exit(1)
    
    store_url = sys.argv[1]
    print(f"Fetching store map for {store_url}")
    
    result = fetch_store_map(store_url, headless=False)
    
    if result:
        print(f"\nStore map fetched successfully!")
        print(f"  Width: {result['width']}")
        print(f"  Height: {result['height']}")
        print(f"  Aisles found: {len(result['aisles'])}")
        
        if len(sys.argv) > 2:
            output_path = sys.argv[2]
            if save_svg(result, output_path):
                print(f"  Saved to: {output_path}")
        
        print(f"\nFirst 10 aisles: {result['aisles'][:10]}")
    else:
        print("Failed to fetch store map")
