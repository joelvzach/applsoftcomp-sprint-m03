#!/usr/bin/env python3
"""
Parallel Item Search - Distribute item searches across max 4 parallel subagents.
Implements the ISOLATE pattern from the PRD.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
import os

from item_search import search_item


def write_progress(item: str, status: str, aisle: str = None, progress_path: str = None):
    """Write search progress to progress.txt (append only)."""
    if progress_path is None:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        templates_dir = os.path.join(script_dir, 'templates')
        progress_path = os.path.join(templates_dir, 'progress.txt')
    
    try:
        with open(progress_path, 'a') as f:
            if aisle:
                f.write(f"[{item}]: [{status}] - [{aisle}]\n")
            else:
                f.write(f"[{item}]: [{status}]\n")
    except Exception as e:
        print(f"Error writing progress: {e}")


def search_item_subagent(args):
    """
    Subagent function for parallel item search.
    Args: (item_name, store_url, headless, progress_path)
    """
    item_name, store_url, headless, progress_path = args
    
    write_progress(item_name, 'searching', progress_path=progress_path)
    
    result = search_item(item_name, store_url, headless)
    
    if result['available']:
        write_progress(item_name, 'found', result['aisle'], progress_path=progress_path)
    else:
        write_progress(item_name, 'missing', progress_path=progress_path)
    
    return result


def parallel_search(items: List[str], store_url: str, max_workers: int = 4, 
                    headless: bool = True, progress_path: str = None) -> List[Dict]:
    """
    Search for items in parallel using max 4 subagents.
    Distributes N items across 4 workers.
    """
    if not items:
        return []
    
    if progress_path is None:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        templates_dir = os.path.join(script_dir, 'templates')
        progress_path = os.path.join(templates_dir, 'progress.txt')
    
    os.makedirs(os.path.dirname(progress_path), exist_ok=True)
    
    with open(progress_path, 'w') as f:
        f.write(f"# Item Search Progress\n# Store: {store_url}\n# Items: {len(items)}\n\n")
    
    workers = min(max_workers, len(items))
    tasks = [(item, store_url, headless, progress_path) for item in items]
    
    results = []
    print(f"Starting parallel search with {workers} workers for {len(items)} items")
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(search_item_subagent, task): task[0] for task in tasks}
        
        for future in as_completed(futures):
            item_name = futures[future]
            try:
                result = future.result()
                results.append(result)
                status = f"${result['price']}" if result['available'] else "Not found"
                print(f"  Completed: {item_name} -> {status}")
            except Exception as e:
                print(f"  Error searching {item_name}: {e}")
                results.append({
                    'item': item_name,
                    'available': False,
                    'aisle': 'N/A',
                    'price': 'N/A',
                    'product_url': None
                })
    
    print_progress_summary(results)
    return results


def print_progress_summary(results: List[Dict]):
    """Print summary of search results."""
    available = sum(1 for r in results if r['available'])
    missing = len(results) - available
    
    print(f"\nSearch Complete:")
    print(f"  Available: {available}/{len(results)}")
    print(f"  Missing: {missing}/{len(results)}")
    
    if available > 0:
        total = sum(r['price'] for r in results if r['available'])
        print(f"  Total estimated cost: ${total:.2f}")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python parallel_search.py <store_url> <item1> [item2] ...")
        print("Example: python parallel_search.py https://www.target.com/sl/store-1056/1056 eggs milk bread butter cheese")
        sys.exit(1)
    
    store_url = sys.argv[1]
    items = sys.argv[2:]
    
    print(f"Searching for {len(items)} items at {store_url}")
    results = parallel_search(items, store_url, headless=False)
    
    print("\nDetailed Results:")
    for r in results:
        if r['available']:
            print(f"  {r['item']}: ${r['price']} - Aisle {r['aisle']}")
            print(f"    URL: {r['product_url']}")
        else:
            print(f"  {r['item']}: Not available")
