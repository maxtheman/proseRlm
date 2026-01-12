#!/usr/bin/env python3
"""
Prepare classification task content for sub-agents.
"""

import json

def prepare_classification_task(batch_num):
    """Prepare the full task content for a batch."""
    batch_file = f'/Users/max/Documents/code/proseRlm/experiments/oolong-pairs/batch_{batch_num}.json'
    prompt_file = '/Users/max/Documents/code/proseRlm/experiments/oolong-pairs/classification_prompt.txt'
    
    with open(prompt_file, 'r') as f:
        prompt = f.read()
    
    with open(batch_file, 'r') as f:
        batch_data = json.load(f)
    
    task_content = f"{prompt}\n\nQUESTIONS TO CLASSIFY:\n\n{json.dumps(batch_data, indent=2)}"
    
    output_file = f'/Users/max/Documents/code/proseRlm/experiments/oolong-pairs/task_batch_{batch_num}.txt'
    with open(output_file, 'w') as f:
        f.write(task_content)
    
    print(f"Batch {batch_num}: Task prepared ({len(task_content)} chars) -> {output_file}")
    return output_file

if __name__ == '__main__':
    for i in range(3):
        prepare_classification_task(i)
