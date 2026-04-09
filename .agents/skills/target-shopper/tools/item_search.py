#!/usr/bin/env python3
"""
Item Search - Search Target.com for grocery items and extract aisle/price data.
Uses 'Shop in Store' filter to get aisle locations.
"""

from playwright.sync_api import sync_playwright
from typing import Optional, Dict, List
import re
import os
from pathlib import Path
from datetime import datetime


def search_item(
    item_name: str, store_url: str, headless: bool = True, trace_dir: str = None
) -> Optional[Dict]:
    """
    Search for an item on Target.com with 'Shop in Store' filter.
    Returns item data: {item, available, aisle, price, product_url, product_name}

    Args:
        item_name: Item to search for
        store_url: Target store URL
        headless: Run browser in headless mode
        trace_dir: Directory to save Playwright traces (optional)
    """

    # Create trace directory if specified
    if trace_dir:
        os.makedirs(trace_dir, exist_ok=True)
        trace_path = os.path.join(trace_dir, f"{item_name.replace(' ', '_')}.zip")
    else:
        trace_path = None

    with sync_playwright() as p:
        browser = p.webkit.launch(headless=headless)
        # Create new context to avoid cached store data
        context = browser.new_context()

        # Start tracing if directory specified
        if trace_path:
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            print(f"  📸 Tracing enabled for {item_name}")

        page = context.new_page()

        try:
            # Go to store page first to set location context
            page.goto(store_url, timeout=30000, wait_until="networkidle")
            page.wait_for_timeout(5000)  # Extra wait for store context

            # Click "Shop this store" button to set the store location
            try:
                shop_btn = page.locator('button:has-text("Shop this store")').first
                if shop_btn.count() > 0:
                    shop_btn.click()
                    page.wait_for_timeout(3000)
            except Exception:
                pass

            # Search for item
            search_input = page.locator('input[placeholder*="What can we help"]').first
            search_input.fill(item_name)
            page.wait_for_timeout(500)
            search_input.press("Enter")
            page.wait_for_timeout(5000)

            # Click 'Shop in store' filter to get aisle info
            try:
                filter_btn = page.locator('button:has-text("Shop in store")').first
                filter_btn.click()
                page.wait_for_timeout(3000)
            except Exception:
                pass  # Filter might already be applied

            # Wait for full content load
            page.wait_for_timeout(5000)

            # Extract products with aisle info using JavaScript
            products = page.eval_on_selector(
                "body",
                f"""() => {{
                const results = [];
                const links = Array.from(document.querySelectorAll('a[href*="/p/"]'));
                
                for (const link of links) {{
                    const text = link.innerText.trim();
                    const href = link.href;
                    
                    // Check if this product matches our search
                    if (text.length > 10 && text.length < 200 && 
                        text.toLowerCase().includes('{item_name.lower()}')) {{
                        
                        // Walk up DOM to find parent with both price AND aisle
                        let parent = link.parentElement;
                        let foundData = null;
                        
                        for (let i = 0; i < 8 && parent; i++) {{
                            const parentText = parent.innerText;
                            const hasPrice = /\\$[\\d,.]+/.test(parentText);
                            const hasAisle = /[Aa]isle\\s*[A-Z]?\\d+/i.test(parentText);
                            
                            if (hasPrice && hasAisle) {{
                                // Extract price
                                const priceMatch = parentText.match(/\\$([\\d,.]+)/);
                                let price = null;
                                if (priceMatch) {{
                                    price = parseFloat(priceMatch[1].replace(/,/g, ''));
                                }}
                                
                                // Extract aisle
                                const aisleMatch = parentText.match(/[Aa]isle\\s*([A-Z]?\\d+[A-Z]?)/);
                                let aisle = null;
                                if (aisleMatch) {{
                                    aisle = aisleMatch[1].toUpperCase();
                                }}
                                
                                if (price && aisle) {{
                                    foundData = {{
                                        name: text,
                                        href: href,
                                        price: price,
                                        aisle: aisle
                                    }};
                                    break;
                                }}
                            }}
                            parent = parent.parentElement;
                        }}
                        
                        if (foundData) {{
                            results.push(foundData);
                            if (results.length >= 5) break;
                        }}
                    }}
                }}
                
                return results;
            }}""",
            )

            if not products:
                return {
                    "item": item_name,
                    "product_name": None,
                    "available": False,
                    "aisle": "N/A",
                    "price": "N/A",
                    "product_url": None,
                }

            # Find cheapest option
            cheapest = min(products, key=lambda p: p["price"])

            return {
                "item": item_name,
                "product_name": cheapest["name"],
                "available": True,
                "aisle": cheapest["aisle"],
                "price": cheapest["price"],
                "product_url": cheapest["href"],
            }

        except Exception as e:
            print(f"  ❌ Error searching for {item_name}: {e}")

            # Save HTML snapshot on error for debugging
            if trace_dir:
                error_html_dir = os.path.join(trace_dir, "error_snapshots")
                os.makedirs(error_html_dir, exist_ok=True)
                error_html_path = os.path.join(
                    error_html_dir, f"{item_name.replace(' ', '_')}_error.html"
                )
                try:
                    with open(error_html_path, "w", encoding="utf-8") as f:
                        f.write(page.content())
                    print(f"  📄 Error snapshot saved: {error_html_path}")
                except Exception as html_err:
                    print(f"  ⚠️  Could not save error snapshot: {html_err}")

            return {
                "item": item_name,
                "product_name": None,
                "available": False,
                "aisle": "N/A",
                "price": "N/A",
                "product_url": None,
            }
        finally:
            # Stop and save trace if enabled
            if trace_path:
                try:
                    context.tracing.stop(path=trace_path)
                    print(f"  💾 Trace saved: {trace_path}")
                except Exception as trace_err:
                    print(f"  ⚠️  Could not save trace: {trace_err}")

            context.close()
            browser.close()


def search_items_batch(
    items: List[str], store_url: str, headless: bool = True
) -> List[Dict]:
    """
    Search for multiple items sequentially.
    Returns list of item data dictionaries.
    """
    results = []
    for item in items:
        print(f"  Searching: {item}")
        result = search_item(item, store_url, headless)
        results.append(result)
        if result["available"]:
            print(f"    -> Found: ${result['price']} - Aisle {result['aisle']}")
        else:
            print(f"    -> Not found")
    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python item_search.py <store_url> <item1> [item2] ...")
        print(
            "Example: python item_search.py https://www.target.com/sl/store-1056/1056 eggs milk"
        )
        sys.exit(1)

    store_url = sys.argv[1]
    items = sys.argv[2:]

    print(f"Searching for {len(items)} items at {store_url}")
    results = search_items_batch(items, store_url, headless=False)

    print("\nResults:")
    for r in results:
        if r["available"]:
            print(f"  {r['item']}: ${r['price']} - Aisle {r['aisle']}")
            print(
                f"    Product: {r['product_name'][:60] if r['product_name'] else 'N/A'}..."
            )
            print(f"    URL: {r['product_url']}")
        else:
            print(f"  {r['item']}: Not available")
