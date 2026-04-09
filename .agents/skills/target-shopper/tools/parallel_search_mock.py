#!/usr/bin/env python3
"""
Mock Parallel Search - For testing without Target.com API calls.
Returns fake data instantly for development/testing.
"""

from typing import List, Dict
import random


def parallel_search(
    items: List[str], store_url: str = None, headless: bool = True
) -> List[Dict]:
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

    # Fake aisle assignments - only use aisles in main connected component (component 0)
    # A5, A6, A7 are isolated in other components - avoid them
    aisles = ["A1", "A2", "A3", "A4", "A8", "A9", "A10", "B21", "B26", "D1"]

    # Generate realistic Target product URLs with proper A-number format
    def generate_product_url(item_name: str) -> str:
        """Generate realistic Target product URL with unique A-number."""
        # Create a hash-based A-number for consistency
        item_hash = abs(hash(item_name.lower())) % 100000000
        a_number = f"A{item_hash:08d}"
        item_slug = (
            item_name.lower()
            .replace(" ", "-")
            .replace("/", "-")
            .replace("(", "")
            .replace(")", "")
        )
        return f"https://www.target.com/p/{item_slug}/-/{a_number}"

    results = []
    for item in items:
        # 80% chance item is found
        available = random.random() < 0.8
        result = {
            "item": item,
            "available": available,
            "aisle": random.choice(aisles) if available else None,
            "price": round(random.uniform(1.0, 10.0), 2) if available else None,
            "product_url": generate_product_url(item) if available else None,
        }
        results.append(result)
        print(
            f"  ✓ {item}: ${result['price'] if result['price'] else 'N/A'} ({result['aisle'] or 'Not found'})"
        )

    return results
