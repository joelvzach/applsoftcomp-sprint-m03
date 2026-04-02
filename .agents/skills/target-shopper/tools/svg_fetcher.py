#!/usr/bin/env python3
"""
Store Map SVG Fetcher - Extract SVG store map via Playwright browser automation.
"""

from playwright.sync_api import sync_playwright
from typing import Optional, Dict
import re


def fetch_store_map(store_url: str, headless: bool = True) -> Optional[Dict]:
    """
    Navigate to store page, click Store Map button, and extract SVG.
    Returns: {svg_content, aisles, aisle_markers, width, height, viewBox}
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
            
            # Extract the complete SVG from the modal
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
            
            # Extract aisle labels from SVG text elements
            aisles = []
            aisle_markers = []
            
            # Match text elements with aisle labels - be more specific to avoid matching font-family
            text_matches = re.findall(r'<text[^>]*x="([\d.-]+)"[^>]*y="([\d.-]+)"[^>]*>([A-Z]{1,2}\d{1,3}|CL\d{1,2})</text>', full_svg)
            
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
                    pass  # Skip if x/y can't be converted to float
            
            return {
                'svg_content': full_svg,
                'aisles': aisles,
                'aisle_markers': aisle_markers,
                'width': width,
                'height': height,
                'viewBox': viewBox,
                'full_svg': full_svg  # Keep original
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
