#!/usr/bin/env python3
"""
Verify classification quality and show samples.
"""

import json
import random

def show_samples(classified_data, category, num_samples=10):
    """Show random samples from a category."""
    items = [item for item in classified_data if item['category'] == category]
    samples = random.sample(items, min(num_samples, len(items)))
    
    print(f"\n{category.upper()} - {len(items)} total")
    print("=" * 80)
    for item in samples:
        print(f"  {item['question']}")
    print()

if __name__ == '__main__':
    base_path = '/Users/max/Documents/code/proseRlm/experiments/oolong-pairs'
    
    with open(f'{base_path}/classified_all.json', 'r') as f:
        classified_data = json.load(f)
    
    # Show samples for numeric value and location
    show_samples(classified_data, 'numeric value', 15)
    show_samples(classified_data, 'location', 15)
