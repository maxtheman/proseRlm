#!/usr/bin/env python3
"""
Find all pairs of users where BOTH users have at least one question 
classified as 'numeric value' OR 'location'.
"""

import json
from itertools import combinations

def find_users_with_numeric_or_location(classified_data):
    """Find all users who have at least one question classified as numeric value or location."""
    target_users = set()
    
    for item in classified_data:
        if item['category'] in ['numeric value', 'location']:
            # Add all users who asked this question
            target_users.update(item['users'])
    
    return sorted(target_users, key=int)

def find_user_pairs(target_users):
    """Find all pairs of users (lower ID first, no duplicates)."""
    # Convert to integers for proper sorting
    user_ids = sorted([int(u) for u in target_users])
    
    # Generate all pairs with lower ID first
    pairs = []
    for i in range(len(user_ids)):
        for j in range(i + 1, len(user_ids)):
            pairs.append((user_ids[i], user_ids[j]))
    
    return pairs

if __name__ == '__main__':
    base_path = '/Users/max/Documents/code/proseRlm/experiments/oolong-pairs'
    
    print("Loading classified questions...")
    with open(f'{base_path}/classified_all.json', 'r') as f:
        classified_data = json.load(f)
    
    print("Finding users with numeric value or location questions...")
    target_users = find_users_with_numeric_or_location(classified_data)
    print(f"Found {len(target_users)} users with numeric value or location questions")
    
    print("Generating user pairs...")
    pairs = find_user_pairs(target_users)
    print(f"Generated {len(pairs)} unique pairs")
    
    # Save pairs
    output_file = f'{base_path}/user_pairs.txt'
    with open(output_file, 'w') as f:
        for pair in pairs:
            f.write(f"({pair[0]}, {pair[1]})\n")
    
    print(f"Pairs saved to {output_file}")
    
    # Show first 10 pairs
    print("\nFirst 10 pairs:")
    for pair in pairs[:10]:
        print(f"  ({pair[0]}, {pair[1]})")
    
    # Show last 10 pairs
    print("\nLast 10 pairs:")
    for pair in pairs[-10:]:
        print(f"  ({pair[0]}, {pair[1]})")
