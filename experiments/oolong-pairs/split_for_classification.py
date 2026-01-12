#!/usr/bin/env python3
"""
Split questions into batches for parallel classification by sub-agents.
"""

import json

def split_into_batches(questions_list, num_batches=3):
    """Split questions into roughly equal batches."""
    batch_size = len(questions_list) // num_batches + 1
    batches = []
    
    for i in range(0, len(questions_list), batch_size):
        batches.append(questions_list[i:i+batch_size])
    
    return batches

if __name__ == '__main__':
    input_file = '/Users/max/Documents/code/proseRlm/experiments/oolong-pairs/questions_for_classification.json'
    
    with open(input_file, 'r') as f:
        questions_list = json.load(f)
    
    print(f"Total questions: {len(questions_list)}")
    
    # Split into 3 batches for parallel processing
    batches = split_into_batches(questions_list, num_batches=3)
    
    for i, batch in enumerate(batches):
        output_file = f'/Users/max/Documents/code/proseRlm/experiments/oolong-pairs/batch_{i}.json'
        with open(output_file, 'w') as f:
            json.dump(batch, f, indent=2)
        print(f"Batch {i}: {len(batch)} questions saved to {output_file}")
