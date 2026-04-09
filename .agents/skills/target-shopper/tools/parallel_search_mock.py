#!/usr/bin/env python3
"""
Mock Parallel Search - For testing without Target.com API calls.
Returns fake data instantly for development/testing.
"""

from typing import List, Dict
import random

def parallel_search(items: List[str], store_url: str = None, headless: bool = True) -> List[Dict]:
    """
    Mock item search that returns instant results.
    
    Args:
        items: List of item names to search
        store_url: Target store URL (ignored in mock)
        headless: Browser headless mode (ignored in mock)
    
    Returns:
        List of item dicts with fake aisle/price data
    """
    print(f"MOCK SEARCH: Searching for {len(items)} items (instant results)...")
    
    # Fake aisle assignments
    aisles = ['A1', 'B5', 'C12', 'D8', 'E15', 'F3', 'G22', 'H9']
    
    results = []
    for item in items:
        # 80% chance item is found
        available = random.random() < 0.8
        result = {
            "item": item,
            "available": available,
            "aisle": random.choice(aisles) if available else None,
            "price": round(random.uniform(1.0, 10.0), 2) if available else None,
            "product_url": f"https://www.target.com/p/{item.replace(' ', '-')}/-/A12345678" if available else None,
        }
        results.append(result)
        print(f"  ✓ {item}: ${result['price'] if result['price'] else 'N/A'} ({result['aisle'] or 'Not found'})")
    
    return results
