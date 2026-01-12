#!/usr/bin/env python3
"""
Generate a summary of the results.
"""

import json

if __name__ == '__main__':
    base_path = '/Users/max/Documents/code/proseRlm/experiments/oolong-pairs'
    
    with open(f'{base_path}/classified_all.json', 'r') as f:
        classified_data = json.load(f)
    
    # Count questions by category
    category_counts = {}
    for item in classified_data:
        cat = item['category']
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    # Find users with numeric value or location questions
    users_numeric = set()
    users_location = set()
    users_both = set()
    
    for item in classified_data:
        if item['category'] == 'numeric value':
            users_numeric.update(item['users'])
        elif item['category'] == 'location':
            users_location.update(item['users'])
    
    users_both = users_numeric | users_location
    
    print("SUMMARY")
    print("=" * 80)
    print(f"\nTotal unique questions: {len(classified_data)}")
    print(f"\nCategory breakdown:")
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat}: {count}")
    
    print(f"\nUsers with 'numeric value' questions: {len(users_numeric)}")
    print(f"Users with 'location' questions: {len(users_location)}")
    print(f"Users with 'numeric value' OR 'location' questions: {len(users_both)}")
    
    # Calculate number of pairs
    n = len(users_both)
    num_pairs = n * (n - 1) // 2
    print(f"\nNumber of unique user pairs: {num_pairs}")
    print(f"  (Calculated as C({n}, 2) = {n} * {n-1} / 2 = {num_pairs})")
