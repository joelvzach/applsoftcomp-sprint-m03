#!/usr/bin/env python3
"""
Report Generator - Generates grocery_report_<timestamp>.md

Generates item availability and pricing report in markdown table format.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Dict


def generate_report(items: List[Dict], output_dir: str = None) -> str:
    """
    Generate grocery report markdown file.
    
    Args:
        items: List of item dicts with keys: item, available, aisle, price, product_url
        output_dir: Output directory path (defaults to project/output from script location)
        
    Returns:
        Path to generated report file
    """
    if output_dir is None:
        script_dir = Path(__file__).parent.parent
        output_dir = script_dir.parent.parent.parent / "project" / "output"
    else:
        output_dir = Path(output_dir)
    """
    Generate grocery report markdown file.
    
    Args:
        items: List of item dicts with keys: item, available, aisle, price, product_url
        output_dir: Output directory path
        
    Returns:
        Path to generated report file
    """
    timestamp = datetime.now()
    filename = f"grocery_report_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
    filepath = output_dir / filename
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    available_count = sum(1 for item in items if item.get('available', False))
    missing_count = len(items) - available_count
    
    content = f"""# Grocery Report - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- **Total items:** {len(items)}
- **Available:** {available_count}
- **Missing:** {missing_count}

## Item Details

| Item | Available | Aisle | Price | Product URL |
|------|-----------|-------|-------|-------------|
"""
    
    for item in items:
        name = item.get('item', 'Unknown')
        available = item.get('available', False)
        aisle = item.get('aisle', 'N/A')
        price = item.get('price', 'N/A')
        url = item.get('product_url', '')
        
        if available:
            avail_str = "Yes"
            aisle_str = str(aisle) if aisle else "N/A"
            price_str = f"${price:.2f}" if price and price != 'N/A' else "N/A"
        else:
            avail_str = "No"
            aisle_str = "N/A"
            price_str = "N/A"
        
        url_display = f"[Link]({url})" if url else "N/A"
        content += f"| {name} | {avail_str} | {aisle_str} | {price_str} | {url_display} |\n"
    
    content += f"\n---\n*Generated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}*\n"
    
    filepath.write_text(content)
    return str(filepath)


def load_items_from_search(search_results: List[Dict]) -> List[Dict]:
    """
    Normalize search results to report format.
    
    Args:
        search_results: Raw results from item_search.py
        
    Returns:
        Normalized list of item dicts
    """
    items = []
    for result in search_results:
        items.append({
            'item': result.get('name', result.get('item', 'Unknown')),
            'available': result.get('available', False),
            'aisle': result.get('aisle', None),
            'price': result.get('price', None),
            'product_url': result.get('product_url', '')
        })
    return items


if __name__ == "__main__":
    test_items = [
        {'item': 'eggs', 'available': True, 'aisle': 'G12', 'price': 4.99, 'product_url': 'https://target.com/p/eggs'},
        {'item': 'milk', 'available': True, 'aisle': 'D5', 'price': 3.49, 'product_url': 'https://target.com/p/milk'},
        {'item': 'bread', 'available': False, 'aisle': None, 'price': None, 'product_url': ''},
    ]
    
    filepath = generate_report(test_items)
    print(f"Generated report: {filepath}")
