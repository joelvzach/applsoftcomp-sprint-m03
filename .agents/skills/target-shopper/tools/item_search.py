#!/usr/bin/env python3
"""
Item Search - Search Target.com for grocery items and extract aisle/price data.
Uses Playwright to handle JavaScript-rendered content.
"""

from playwright.sync_api import sync_playwright
from typing import Optional, Dict, List
import re


def search_item(item_name: str, store_url: str, headless: bool = True) -> Optional[Dict]:
    """
    Search for an item on Target.com filtered to a specific store.
    Returns item data: {item, available, aisle, price, product_url}
    """
    with sync_playwright() as p:
        browser = p.webkit.launch(headless=headless)
        page = browser.new_page()
        
        try:
            page.goto(store_url, timeout=30000, wait_until='domcontentloaded')
            page.wait_for_timeout(2000)
            
            search_input = page.locator('input[placeholder*="What can we help"]').first
            
            try:
                search_input.fill(item_name)
                page.wait_for_timeout(500)
                search_input.press('Enter')
                page.wait_for_timeout(5000)
            except Exception as e:
                print(f"Search error for {item_name}: {e}")
                return {
                    'item': item_name,
                    'available': False,
                    'aisle': 'N/A',
                    'price': 'N/A',
                    'product_url': None
                }
            
            products = page.eval_on_selector('body', '''() => {
                const links = Array.from(document.querySelectorAll('a[href*="/p/"]'));
                const products = [];
                for (const link of links) {
                    const text = link.innerText.trim();
                    const href = link.href;
                    if (text.length > 10) {
                        let parent = link.parentElement;
                        while (parent && parent.tagName !== 'BODY') {
                            const priceSpan = parent.querySelector('[data-test="current-price"]');
                            if (priceSpan) {
                                products.push({
                                    text: text,
                                    href: href,
                                    price: priceSpan.innerText
                                });
                                if (products.length >= 5) break;
                            }
                            parent = parent.parentElement;
                        }
                        if (products.length >= 5) break;
                    }
                }
                return products;
            }''')
            
            if not products:
                return {
                    'item': item_name,
                    'available': False,
                    'aisle': 'N/A',
                    'price': 'N/A',
                    'product_url': None
                }
            
            cheapest = min(products, key=lambda p: parse_price(p['price']) or float('inf'))
            price_val = parse_price(cheapest['price'])
            
            if not price_val:
                return {
                    'item': item_name,
                    'available': False,
                    'aisle': 'N/A',
                    'price': 'N/A',
                    'product_url': None
                }
            
            return {
                'item': item_name,
                'available': True,
                'aisle': 'TBD',
                'price': price_val,
                'product_url': cheapest['href']
            }
            
        except Exception as e:
            print(f"Error searching for {item_name}: {e}")
            return {
                'item': item_name,
                'available': False,
                'aisle': 'N/A',
                'price': 'N/A',
                'product_url': None
            }
        finally:
            browser.close()


def parse_price(price_text: str) -> Optional[float]:
    """Extract numeric price from price string."""
    if not price_text:
        return None
    
    match = re.search(r'\$?([\d,]+\.?\d*)', str(price_text).replace(',', ''))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def search_items_batch(items: List[str], store_url: str, headless: bool = True) -> List[Dict]:
    """
    Search for multiple items sequentially.
    Returns list of item data dictionaries.
    """
    results = []
    for item in items:
        print(f"  Searching: {item}")
        result = search_item(item, store_url, headless)
        results.append(result)
        if result['available']:
            print(f"    -> Found: ${result['price']}")
        else:
            print(f"    -> Not found")
    return results


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python item_search.py <store_url> <item1> [item2] ...")
        print("Example: python item_search.py https://www.target.com/sl/store-1056/1056 eggs milk")
        sys.exit(1)
    
    store_url = sys.argv[1]
    items = sys.argv[2:]
    
    print(f"Searching for {len(items)} items at {store_url}")
    results = search_items_batch(items, store_url, headless=False)
    
    print("\nResults:")
    for r in results:
        if r['available']:
            print(f"  {r['item']}: ${r['price']}")
        else:
            print(f"  {r['item']}: Not available")
