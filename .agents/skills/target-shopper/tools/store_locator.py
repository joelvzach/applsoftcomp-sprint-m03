#!/usr/bin/env python3
"""
Store Locator - Find Target store URL from store name or ID.
Uses Playwright to interact with Target.com store locator.

Strategies (in order):
1. Direct store ID access (fastest, most reliable)
2. State directory navigation (bypasses anti-bot)
3. Recent stores cache (for repeat users)
4. Traditional search (fallback, may be blocked)
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from typing import Optional, List, Dict, Tuple
import re
import json
from pathlib import Path
from datetime import datetime, timedelta


# State abbreviations mapping
STATE_ABBREVS = {
    'NY': 'New York', 'CA': 'California', 'TX': 'Texas',
    'FL': 'Florida', 'IL': 'Illinois', 'PA': 'Pennsylvania',
    'OH': 'Ohio', 'GA': 'Georgia', 'NC': 'North Carolina',
    'MI': 'Michigan', 'NJ': 'New Jersey', 'VA': 'Virginia',
    'WA': 'Washington', 'AZ': 'Arizona', 'MA': 'Massachusetts',
    'TN': 'Tennessee', 'IN': 'Indiana', 'MO': 'Missouri',
    'MD': 'Maryland', 'WI': 'Wisconsin', 'CO': 'Colorado',
    'MN': 'Minnesota', 'SC': 'South Carolina', 'AL': 'Alabama',
    'LA': 'Louisiana', 'KY': 'Kentucky', 'OR': 'Oregon',
    'OK': 'Oklahoma', 'CT': 'Connecticut', 'UT': 'Utah',
    'IA': 'Iowa', 'NV': 'Nevada', 'AR': 'Arkansas',
    'MS': 'Mississippi', 'KS': 'Kansas', 'NM': 'New Mexico',
    'NE': 'Nebraska', 'WV': 'West Virginia', 'ID': 'Idaho',
    'HI': 'Hawaii', 'NH': 'New Hampshire', 'ME': 'Maine',
    'MT': 'Montana', 'RI': 'Rhode Island', 'DE': 'Delaware',
    'SD': 'South Dakota', 'ND': 'North Dakota', 'AK': 'Alaska',
    'VT': 'Vermont', 'WY': 'Wyoming', 'DC': 'District of Columbia'
}

# Reverse mapping: full state name → abbreviation
STATE_NAMES = {v: k for k, v in STATE_ABBREVS.items()}


def get_store_by_id(store_id: str, headless: bool = True) -> Optional[Dict[str, str]]:
    """
    Get store info by directly accessing the store page.
    This is the most reliable method when you know the store ID.
    """
    store_url = f"https://www.target.com/sl/store-{store_id}/{store_id}"
    
    with sync_playwright() as p:
        browser = p.webkit.launch(headless=headless)
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


def parse_location(query: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse location query into state and city.
    
    Examples:
        "New York" → ("New York", None)
        "Manhattan, NY" → ("New York", "Manhattan")
        "Los Angeles, CA" → ("California", "Los Angeles")
        "Vestal" → (None, None)  # Falls back to traditional search
    """
    # Check for "City, ST" format
    if ',' in query:
        parts = query.split(',')
        city = parts[0].strip()
        state_part = parts[1].strip().upper()
        
        # Convert abbreviation to full state name
        state = STATE_ABBREVS.get(state_part, state_part.title())
        return (state, city)
    
    # Check if query is a state name
    query_title = query.title()
    if query_title in STATE_NAMES:
        return (query_title, None)
    
    # Not parseable - fallback to traditional search
    return (None, None)


def search_by_state_directory(state: str, city: str = None, headless: bool = True) -> List[Dict[str, str]]:
    """
    Navigate through store directory: state page → filter by city.
    Bypasses anti-bot protection by using static directory pages.
    
    Args:
        state: State name (e.g., "New York", "California")
        city: Optional city filter (e.g., "Manhattan", "Buffalo")
        headless: Run browser without UI
    
    Returns:
        List of stores: [{name, url, store_id, address}]
    """
    stores = []
    
    with sync_playwright() as p:
        browser = p.webkit.launch(headless=headless)
        page = browser.new_page()
        
        try:
            # Go to state directory page
            state_slug = state.lower().replace(' ', '-')
            state_url = f"https://www.target.com/store-locator/store-directory/{state_slug}"
            
            print(f"  → Navigating to {state_slug} store directory...")
            page.goto(state_url, timeout=30000, wait_until='domcontentloaded')
            page.wait_for_timeout(3000)
            
            # Extract all stores on the page
            stores_data = page.evaluate('''() => {
                const results = [];
                // Look for store cards or links
                const allLinks = document.querySelectorAll('a[href*="/sl/"]');
                
                allLinks.forEach(link => {
                    const href = link.href;
                    const storeIdMatch = href.match(/\\/sl\\/[^\\/]+\\/(\\d+)/);
                    if (!storeIdMatch) return;
                    
                    // Try to find store name in surrounding elements
                    let name = link.innerText.trim();
                    if (!name || name.length < 3) {
                        // Try parent elements
                        let parent = link.parentElement;
                        let depth = 0;
                        while (parent && depth < 5) {
                            const text = parent.innerText || '';
                            if (text.length > 5 && text.length < 100 && !text.includes('http')) {
                                name = text.split('\\n')[0].trim();
                                if (name.length > 3) break;
                            }
                            parent = parent.parentElement;
                            depth++;
                        }
                    }
                    
                    if (name && name.length > 3) {
                        results.push({
                            name: name,
                            url: href,
                            store_id: storeIdMatch[1]
                        });
                    }
                });
                
                // Deduplicate by store ID
                const seen = new Set();
                const unique = results.filter(s => {
                    if (seen.has(s.store_id)) return false;
                    seen.add(s.store_id);
                    return true;
                });
                
                return unique;
            }''')
            
            stores = stores_data
            
        except Exception as e:
            print(f"Error fetching state directory: {e}")
        finally:
            browser.close()
    
    # Filter by city if specified
    if city and stores:
        city_lower = city.lower()
        filtered = [
            s for s in stores 
            if city_lower in s['name'].lower()
        ]
        if filtered:
            print(f"  → Filtered to {len(filtered)} stores in {city}")
            stores = filtered
        else:
            # Special handling for "New York City" - look for boroughs
            if city_lower in ['new york city', 'nyc']:
                nyc_boroughs = ['bronx', 'brooklyn', 'queens', 'staten', 'manhattan', 'flushing', 'jamaica']
                borough_filtered = [
                    s for s in stores
                    if any(borough in s['name'].lower() for borough in nyc_boroughs)
                ]
                if borough_filtered:
                    print(f"  → Found {len(borough_filtered)} stores in NYC boroughs")
                    stores = borough_filtered
                else:
                    print(f"  → No stores found in {city}, showing all {len(stores)} stores in {state}")
            else:
                print(f"  → No stores found in {city}, showing all {len(stores)} stores in {state}")
    
    return stores


def get_recent_stores(max_age_days: int = 30, limit: int = 5) -> List[Dict]:
    """
    Get recently used stores from cache.
    
    Args:
        max_age_days: Maximum age of cached stores
        limit: Maximum number of stores to return
    
    Returns:
        List of recent stores
    """
    cache_file = Path(__file__).parent.parent / "project" / ".store_cache.json"
    
    if not cache_file.exists():
        return []
    
    try:
        with open(cache_file, 'r') as f:
            cache = json.load(f)
        
        cutoff = datetime.now() - timedelta(days=max_age_days)
        recent = []
        
        for entry in cache.get('stores', []):
            last_used = datetime.fromisoformat(entry.get('last_used', '1970-01-01'))
            if last_used > cutoff:
                recent.append(entry['store'])
        
        return recent[:limit]
    
    except Exception:
        return []


def save_store_to_cache(store: Dict):
    """Save store to recent stores cache."""
    cache_file = Path(__file__).parent.parent / "project" / ".store_cache.json"
    
    try:
        cache = {}
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                cache = json.load(f)
        
        if 'stores' not in cache:
            cache['stores'] = []
        
        # Remove existing entry for this store
        cache['stores'] = [s for s in cache['stores'] if s['store']['store_id'] != store['store_id']]
        
        # Add new entry with timestamp
        cache['stores'].append({
            'store': store,
            'last_used': datetime.now().isoformat()
        })
        
        # Keep only last 20 entries
        cache['stores'] = cache['stores'][-20:]
        
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump(cache, f, indent=2)
    
    except Exception as e:
        print(f"Warning: Could not save to cache: {e}")


def search_stores(store_name: str, headless: bool = True) -> List[Dict[str, str]]:
    """
    Search for Target stores by name using Playwright.
    Returns list of matching stores with name, URL, and store ID.
    
    Note: This method may be blocked by Target's anti-bot protection.
    Use search_by_state_directory() as primary method instead.
    """
    stores = []
    
    with sync_playwright() as p:
        browser = p.webkit.launch(headless=headless)
        page = browser.new_page()
        
        try:
            page.goto("https://www.target.com/store-locator", timeout=30000, wait_until='domcontentloaded')
            page.wait_for_timeout(3000)
            
            store_buttons = page.locator('button[aria-label*="Store:"]').all()
            
            if store_buttons:
                store_buttons[0].click()
                page.wait_for_timeout(2000)
                
                try:
                    modal = page.locator('[role="dialog"]').first
                    modal.wait_for(timeout=5000)
                    
                    search_input = modal.locator('input[name="zip-code-city-or-state"]').first
                    search_input.fill(store_name)
                    page.wait_for_timeout(500)
                    search_input.press('Enter')
                    page.wait_for_timeout(8000)
                    
                    # Use JavaScript to extract store data properly
                    stores = page.evaluate(f'''() => {{
                        const results = [];
                        const searchLower = '{store_name.lower()}';
                        
                        // Find all "More info" links and extract store data from parent
                        const moreInfoLinks = document.querySelectorAll('a');
                        
                        moreInfoLinks.forEach(link => {{
                            if (!link.innerText.toLowerCase().includes('more info')) return;
                            
                            const href = link.href;
                            const storeIdMatch = href.match(/\\/sl\\/[^\\/]+\\/(\\d+)/);
                            if (!storeIdMatch) return;
                            
                            // Find parent container with store info
                            let parent = link.parentElement;
                            let cardText = '';
                            let depth = 0;
                            
                            while (parent && depth < 10) {{
                                const text = parent.innerText || '';
                                if (text.includes('miles') && text.length > 50 && text.length < 500) {{
                                    cardText = text;
                                    break;
                                }}
                                parent = parent.parentElement;
                                depth++;
                            }}
                            
                            if (!cardText) return;
                            
                            // Extract store name (first line of card text)
                            const lines = cardText.split('\\n').map(l => l.trim()).filter(l => l);
                            let name = '';
                            
                            for (const line of lines) {{
                                if (line.length > 2 && line.length < 80 && 
                                    !line.toLowerCase().includes('skip') &&
                                    !line.toLowerCase().includes('ship to') &&
                                    !line.includes('miles')) {{
                                    name = line;
                                    break;
                                }}
                            }}
                            
                            if (name && name.length > 2) {{
                                results.push({{
                                    name: name,
                                    url: href,
                                    store_id: storeIdMatch[1],
                                    fullText: cardText.substring(0, 200)
                                }});
                            }}
                        }});
                        
                        // Deduplicate by store ID
                        const seen = new Set();
                        const unique = results.filter(s => {{
                            if (seen.has(s.store_id)) return false;
                            seen.add(s.store_id);
                            return true;
                        }});
                        
                        // Filter by search term if specified
                        if (searchLower && unique.length > 0) {{
                            const filtered = unique.filter(s => 
                                searchLower.split(' ').every(term => 
                                    term.length > 2 && (s.name.toLowerCase().includes(term) || s.fullText.toLowerCase().includes(term))
                                )
                            );
                            if (filtered.length > 0) return filtered;
                        }}
                        
                        return unique.slice(0, 10);
                    }}''')
                    
                    # Deduplicate by store ID (already done in JS, but double-check)
                    seen_ids = set()
                    deduped = []
                    for store_data in stores:
                        store_id = store_data.get('store_id')
                        if store_id and store_id not in seen_ids:
                            seen_ids.add(store_id)
                            deduped.append({
                                'name': store_data['name'],
                                'url': store_data['url'],
                                'store_id': store_id
                            })
                    stores = deduped
                            
                except Exception as e:
                    pass
            
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
    
    Strategy (in order):
    1. Direct store ID access (if numeric)
    2. Recent stores cache (for repeat users)
    3. State directory navigation (bypasses anti-bot)
    4. Traditional search (fallback, may be blocked)
    
    If multiple matches, auto-selects most reasonable option or prompts user.
    Returns selected store info or None if not found.
    """
    # Strategy 1: Direct store ID access
    if store_name.isdigit() and len(store_name) >= 3:
        store = get_store_by_id(store_name, headless)
        if store:
            print(f"Found store: {store['name']} (ID: {store['store_id']})")
            if save_preference:
                save_store_preference(store)
            save_store_to_cache(store)
            return store
    
    # Strategy 2: Check recent stores cache
    recent_stores = get_recent_stores()
    if recent_stores:
        # Check if any recent store matches the query
        query_lower = store_name.lower()
        for recent in recent_stores:
            if query_lower in recent['name'].lower() or query_lower in recent.get('address', '').lower():
                print(f"Using recent store: {recent['name']}")
                if save_preference:
                    save_store_preference(recent)
                save_store_to_cache(recent)
                return recent
    
    # Strategy 3: State directory navigation (primary method)
    state, city = parse_location(store_name)
    if state:
        print(f"  → Searching {state} store directory...")
        stores = search_by_state_directory(state, city, headless)
        
        if stores:
            if len(stores) == 1:
                print(f"Found store: {stores[0]['name']}")
                if save_preference:
                    save_store_preference(stores[0])
                save_store_to_cache(stores[0])
                return stores[0]
            
            # Auto-select most reasonable option
            # Prefer stores with city name in title, or first store
            if city:
                city_lower = city.lower()
                for store in stores:
                    if city_lower in store['name'].lower():
                        print(f"Auto-selected: {store['name']}")
                        if save_preference:
                            save_store_preference(store)
                        save_store_to_cache(store)
                        return store
            
            # Select first store as default
            selected = stores[0]
            print(f"Auto-selected: {selected['name']}")
            if save_preference:
                save_store_preference(selected)
            save_store_to_cache(selected)
            return selected
    
    # Strategy 4: Traditional search (fallback)
    stores = search_stores(store_name, headless)
    
    # If search term contains space (like "Portland 9800"), also try city-only search
    if ' ' in store_name:
        city_name = store_name.split()[0]
        city_stores = search_stores(city_name, headless)
        
        if city_stores and (not stores or (len(stores) >= 10 and len(city_stores) < 10)):
            print(f"Using city-only search: '{city_name}' ({len(city_stores)} stores)")
            stores = city_stores
    
    if not stores:
        print(f"No stores found for '{store_name}'")
        print("Tip: Try using format 'City, ST' (e.g., 'Manhattan, NY') or a store ID")
        return None
    
    if len(stores) == 1:
        print(f"Found store: {stores[0]['name']}")
        if save_preference:
            save_store_preference(stores[0])
        save_store_to_cache(stores[0])
        return stores[0]
    
    # Find most common city/location from store names
    city_counts = {}
    for store in stores:
        # Extract city from store name (usually first word or before parentheses)
        name = store['name']
        city = name.split('(')[0].split(',')[0].strip().split()[0]
        city_counts[city] = city_counts.get(city, 0) + 1
    
    # Find the city with most stores
    most_common_city = max(city_counts.keys(), key=lambda c: city_counts[c])
    most_common_count = city_counts[most_common_city]
    
    print(f"Found {len(stores)} stores matching '{store_name}':")
    for i, store in enumerate(stores, 1):
        print(f"  {i}. {store['name']} (ID: {store['store_id']})")
    
    if auto_select:
        # Select first store from most common city
        for store in stores:
            if most_common_city in store['name']:
                print(f"Auto-selecting {most_common_city} store: {store['name']}")
                if save_preference:
                    save_store_preference(store)
                return store
        
        # Fallback to first store
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
