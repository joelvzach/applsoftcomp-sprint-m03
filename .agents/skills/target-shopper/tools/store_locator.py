#!/usr/bin/env python3
"""
Store Locator - Find Target store URL from store name or ID.
Uses Playwright to interact with Target.com store locator.
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from typing import Optional, List, Dict
import re


def get_store_by_id(store_id: str, headless: bool = True) -> Optional[Dict[str, str]]:
    """
    Get store info by directly accessing the store page.
    """
    store_url = f"https://www.target.com/sl/store-{store_id}/{store_id}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        
        try:
            page.goto(store_url, timeout=30000, wait_until='domcontentloaded')
            page.wait_for_timeout(2000)
            
            title = page.title()
            
            if title and 'Target' in title and 'Store' in title:
                name = title.replace('Target', '').replace('Store', '').strip()
                return {
                    'name': name,
                    'url': store_url,
                    'store_id': store_id
                }
        except Exception as e:
            print(f"Error accessing store {store_id}: {e}")
        finally:
            browser.close()
    
    return None


def search_stores(store_name: str, headless: bool = True) -> List[Dict[str, str]]:
    """
    Search for Target stores by name using Playwright.
    Returns list of matching stores with name, URL, and store ID.
    """
    stores = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        
        try:
            page.goto("https://www.target.com/store-locator", timeout=30000, wait_until='domcontentloaded')
            page.wait_for_timeout(2000)
            
            try:
                search_input = page.locator('input[placeholder*="Store"], input[placeholder*="ZIP"], input[placeholder*="City"]').first
                search_input.fill(store_name)
                page.wait_for_timeout(500)
                search_input.press('Enter')
                page.wait_for_timeout(3000)
            except Exception as e:
                print(f"Search input error: {e}")
            
            store_cards = page.locator('[data-test*="store"], [class*="store-result"]').all()
            
            for card in store_cards:
                try:
                    link = card.locator('a[href*="/sl/"]').first
                    href = link.get_attribute('href')
                    name = card.inner_text().strip()[:100]
                    
                    if href:
                        store_id = extract_store_id(href)
                        if store_id:
                            stores.append({
                                'name': name or f"Store {store_id}",
                                'url': href if href.startswith('http') else f"https://www.target.com{href}",
                                'store_id': store_id
                            })
                except Exception:
                    continue
            
            if not stores:
                links = page.locator('a[href*="/sl/"]').all()
                seen_ids = set()
                search_lower = store_name.lower()
                
                for link in links[:20]:
                    try:
                        href = link.get_attribute('href')
                        if not href:
                            continue
                        
                        store_id = extract_store_id(href)
                        if not store_id or store_id in seen_ids:
                            continue
                        
                        name = link.inner_text().strip()[:100]
                        
                        if search_lower in name.lower() or search_lower in href.lower():
                            seen_ids.add(store_id)
                            stores.append({
                                'name': name or f"Store {store_id}",
                                'url': href if href.startswith('http') else f"https://www.target.com{href}",
                                'store_id': store_id
                            })
                    except Exception:
                        continue
                        
        except Exception as e:
            print(f"Error searching stores: {e}")
        finally:
            browser.close()
    
    return stores


def extract_store_id(store_url: str) -> Optional[str]:
    """Extract store ID from Target store URL."""
    match = re.search(r'/(\d{4,})$', store_url.rstrip('/'))
    if match:
        return match.group(1)
    return None


def find_store(store_name: str, headless: bool = True, auto_select: bool = False, save_preference: bool = True) -> Optional[Dict[str, str]]:
    """
    Find a Target store by name or ID.
    If multiple matches, prompt user to select (or auto-select first if auto_select=True).
    Returns selected store info or None if not found.
    """
    if store_name.isdigit() and len(store_name) >= 3:
        store = get_store_by_id(store_name, headless)
        if store:
            print(f"Found store: {store['name']} (ID: {store['store_id']})")
            if save_preference:
                save_store_preference(store)
            return store
    
    stores = search_stores(store_name, headless)
    
    if not stores:
        print(f"No stores found for '{store_name}'")
        print("Tip: Try using a city name, ZIP code, or store ID")
        return None
    
    if len(stores) == 1:
        print(f"Found store: {stores[0]['name']}")
        if save_preference:
            save_store_preference(stores[0])
        return stores[0]
    
    print(f"Found {len(stores)} stores matching '{store_name}':")
    for i, store in enumerate(stores, 1):
        print(f"  {i}. {store['name']} (ID: {store['store_id']})")
    
    if auto_select:
        print(f"Auto-selecting first store: {stores[0]['name']}")
        if save_preference:
            save_store_preference(stores[0])
        return stores[0]
    
    while True:
        try:
            choice = input(f"Select a store (1-{len(stores)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(stores):
                print(f"Selected: {stores[idx]['name']}")
                if save_preference:
                    save_store_preference(stores[idx])
                return stores[idx]
            else:
                print(f"Please enter a number between 1 and {len(stores)}")
        except ValueError:
            print("Please enter a valid number")
        except EOFError:
            print(f"Auto-selecting first store: {stores[0]['name']}")
            if save_preference:
                save_store_preference(stores[0])
            return stores[0]


def get_store_url(store_id: str) -> str:
    """Build Target store URL from store ID."""
    return f"https://www.target.com/sl/store-{store_id}/{store_id}"


def save_store_preference(store: Dict[str, str], preferences_path: str = None) -> bool:
    """
    Save selected store to preferences.md file.
    Returns True if successful.
    """
    if preferences_path is None:
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        skill_dir = os.path.dirname(script_dir)
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(skill_dir)))
        project_dir = os.path.join(root_dir, 'project')
        preferences_path = os.path.join(project_dir, 'preferences.md')
    
    try:
        with open(preferences_path, 'r') as f:
            content = f.read()
        
        lines = content.split('\n')
        new_lines = []
        in_store_section = False
        
        for line in lines:
            if line.startswith('## Store Location'):
                in_store_section = True
                new_lines.append(line)
            elif in_store_section and line.startswith('- Default store:'):
                new_lines.append(f"- Default store: {store['name']} (ID: {store['store_id']})")
                new_lines.append(f"- Store URL: {store['url']}")
                in_store_section = False
            elif in_store_section and line.startswith('-'):
                if 'Store URL' not in line:
                    continue
                new_lines.append(line)
                in_store_section = False
            else:
                new_lines.append(line)
        
        with open(preferences_path, 'w') as f:
            f.write('\n'.join(new_lines))
        
        return True
    except Exception as e:
        print(f"Error saving preferences: {e}")
        return False


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        store_name = ' '.join(sys.argv[1:])
        store = find_store(store_name, headless=False)
        if store:
            print(f"URL: {store['url']}")
            print(f"Store ID: {store['store_id']}")
    else:
        print("Usage: python store_locator.py <store_name>")
        print("Example: python store_locator.py Vestal")
        print("       python store_locator.py 1056")
