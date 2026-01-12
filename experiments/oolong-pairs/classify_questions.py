#!/usr/bin/env python3
"""
Classify questions based on semantic meaning.
This uses pattern matching and keyword analysis as a heuristic.
"""

import json
import re

def classify_question(question):
    """
    Classify a question into one of these categories:
    - numeric value
    - location  
    - entity
    - human being
    - description/abstract concept
    - abbreviation
    """
    q_lower = question.lower().strip()
    
    # Abbreviation: "What does X stand for?" or "What is the full form of"
    if ('stand for' in q_lower or 'full form' in q_lower or 
        'abbreviation' in q_lower or 'acronym' in q_lower or
        re.search(r'what does [A-Z]{2,}', question) or
        re.search(r'what is [A-Z]{2,}', question)):
        return "abbreviation"
    
    # Numeric value: Questions seeking numbers, dates, quantities
    numeric_patterns = [
        r'\bhow many\b', r'\bhow much\b', r'\bhow old\b', r'\bhow long\b',
        r'\bhow tall\b', r'\bhow high\b', r'\bhow deep\b', r'\bhow far\b',
        r'\bwhat year\b', r'\bwhen was\b', r'\bwhen did\b', r'\bwhat date\b',
        r'\bwhat percentage\b', r'\bwhat number\b', r'\bhow big\b',
        r'\bwhat age\b', r'\bwhat time\b', r'\bborn\b'
    ]
    for pattern in numeric_patterns:
        if re.search(pattern, q_lower):
            return "numeric value"
    
    # Location: Questions seeking places
    location_patterns = [
        r'\bwhere\b', r'\bwhat city\b', r'\bwhat country\b', r'\bwhat state\b',
        r'\bwhat place\b', r'\bwhat location\b', r'\bin what\b.*\bcountry\b',
        r'\bin what\b.*\bstate\b', r'\bin what\b.*\bcity\b', r'\btake place\b'
    ]
    for pattern in location_patterns:
        if re.search(pattern, q_lower):
            return "location"
    
    # Human being: Questions seeking people
    human_patterns = [
        r'^who\b', r'\bwho was\b', r'\bwho is\b', r'\bwho were\b',
        r'\bwho killed\b', r'\bwho invented\b', r'\bwho created\b',
        r'\bwho discovered\b', r'\bwho said\b', r'\bwhat person\b',
        r'\bname a\b.*\bperson\b', r'\bwhich person\b', r'\bwhich president\b'
    ]
    for pattern in human_patterns:
        if re.search(pattern, q_lower):
            return "human being"
    
    # Description/abstract concept: Seeking definitions, explanations, reasons
    description_patterns = [
        r'^what is\b', r'^what are\b', r'^what was\b', r'^what were\b',
        r'^why\b', r'^how do\b', r'^how does\b', r'^how did\b',
        r'^how can\b', r'\bwhat does\b.*\bmean\b', r'\bwhat causes\b',
        r'\bdefine\b', r'\bexplain\b'
    ]
    for pattern in description_patterns:
        if re.search(pattern, q_lower):
            # Check if it's not another more specific category
            if not any(re.search(p, q_lower) for p in numeric_patterns + location_patterns):
                return "description/abstract concept"
    
    # Default to entity for other "what" questions
    if q_lower.startswith('what ') or q_lower.startswith('which '):
        return "entity"
    
    # Default fallback
    return "description/abstract concept"

def process_batch(batch_file, output_file):
    """Process a batch of questions and classify them."""
    with open(batch_file, 'r') as f:
        questions = json.load(f)
    
    results = []
    for item in questions:
        category = classify_question(item['question'])
        results.append({
            'idx': item['idx'],
            'question': item['question'],
            'category': category,
            'users': item['users']
        })
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    return results

if __name__ == '__main__':
    base_path = '/Users/max/Documents/code/proseRlm/experiments/oolong-pairs'
    
    all_results = []
    for i in range(3):
        batch_file = f'{base_path}/batch_{i}.json'
        output_file = f'{base_path}/classified_batch_{i}.json'
        
        print(f"Processing batch {i}...")
        results = process_batch(batch_file, output_file)
        all_results.extend(results)
        print(f"  Classified {len(results)} questions")
    
    # Save combined results
    combined_file = f'{base_path}/classified_all.json'
    with open(combined_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\nTotal classified: {len(all_results)} questions")
    print(f"Combined results saved to {combined_file}")
    
    # Show category distribution
    from collections import Counter
    categories = Counter(r['category'] for r in all_results)
    print("\nCategory distribution:")
    for cat, count in categories.most_common():
        print(f"  {cat}: {count}")
