#!/usr/bin/env python3
"""
Process questions and find user pairs.
Strategy: Extract all questions, batch them for classification, then find pairs.
"""

import json
import re
from collections import defaultdict

def parse_input_file(filepath):
    """Parse the input file and extract user-question pairs."""
    user_questions = defaultdict(list)
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("Date:") is False:
                continue
            
            # Parse: Date: ... || User: ... || Instance: ...
            match = re.match(r'Date:\s*[^|]+\|\|\s*User:\s*(\d+)\s*\|\|\s*Instance:\s*(.+)', line)
            if match:
                user_id = match.group(1)
                question = match.group(2).strip()
                user_questions[user_id].append(question)
    
    return user_questions

def save_questions_for_classification(user_questions, output_path):
    """Save all unique questions with their user associations for classification."""
    question_to_users = defaultdict(set)
    
    for user_id, questions in user_questions.items():
        for question in questions:
            question_to_users[question].add(user_id)
    
    # Save questions with index
    questions_list = []
    for idx, (question, users) in enumerate(sorted(question_to_users.items())):
        questions_list.append({
            'idx': idx,
            'question': question,
            'users': sorted(list(users))
        })
    
    with open(output_path, 'w') as f:
        json.dump(questions_list, f, indent=2)
    
    return questions_list

if __name__ == '__main__':
    input_file = '/Users/max/Documents/code/proseRlm/experiments/oolong-pairs/input_task1_1M.txt'
    output_file = '/Users/max/Documents/code/proseRlm/experiments/oolong-pairs/questions_for_classification.json'
    
    print("Parsing input file...")
    user_questions = parse_input_file(input_file)
    print(f"Found {len(user_questions)} unique users")
    
    print("Preparing questions for classification...")
    questions_list = save_questions_for_classification(user_questions, output_file)
    print(f"Found {len(questions_list)} unique questions")
    
    print(f"Saved to {output_file}")
