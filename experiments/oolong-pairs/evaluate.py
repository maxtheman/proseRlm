#!/usr/bin/env python3
"""
Evaluate OOLONG-Pairs predictions against ground truth.
Computes F1 score as used in the RLM paper.
"""

import json
import re
import argparse
from typing import Set, Tuple


def parse_pairs(text: str) -> Set[Tuple[int, int]]:
    """Parse pairs from model output."""
    pairs = set()
    
    # Match patterns like (1, 2), (1,2), 1,2, etc.
    pattern = r'\(?\s*(\d+)\s*,\s*(\d+)\s*\)?'
    
    for match in re.finditer(pattern, text):
        id1, id2 = int(match.group(1)), int(match.group(2))
        # Normalize to (lower, higher)
        pair = (min(id1, id2), max(id1, id2))
        pairs.add(pair)
    
    return pairs


def compute_f1(predicted: Set[Tuple[int, int]], ground_truth: Set[Tuple[int, int]]) -> dict:
    """Compute precision, recall, and F1 score."""
    
    if len(predicted) == 0 and len(ground_truth) == 0:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    
    if len(predicted) == 0:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    
    if len(ground_truth) == 0:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    
    true_positives = len(predicted & ground_truth)
    precision = true_positives / len(predicted)
    recall = true_positives / len(ground_truth)
    
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positives": true_positives,
        "predicted_count": len(predicted),
        "ground_truth_count": len(ground_truth),
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate OOLONG-Pairs predictions")
    parser.add_argument("--prediction", type=str, required=True, help="File with predicted pairs")
    parser.add_argument("--dataset", type=str, default="dataset.json", help="Dataset file with ground truth")
    args = parser.parse_args()
    
    # Load ground truth
    with open(args.dataset) as f:
        data = json.load(f)
    
    ground_truth = set(tuple(p) for p in data["correct_pairs"])
    
    # Load predictions
    with open(args.prediction) as f:
        prediction_text = f.read()
    
    predicted = parse_pairs(prediction_text)
    
    # Compute metrics
    metrics = compute_f1(predicted, ground_truth)
    
    print(f"Ground truth pairs: {metrics['ground_truth_count']}")
    print(f"Predicted pairs: {metrics['predicted_count']}")
    print(f"True positives: {metrics['true_positives']}")
    print(f"Precision: {metrics['precision']:.2%}")
    print(f"Recall: {metrics['recall']:.2%}")
    print(f"F1 Score: {metrics['f1']:.2%}")
    
    # Show some examples of correct and incorrect predictions
    correct = predicted & ground_truth
    missed = ground_truth - predicted
    false_positives = predicted - ground_truth
    
    if correct:
        print(f"\nCorrect predictions (first 5): {list(correct)[:5]}")
    if missed:
        print(f"Missed pairs (first 5): {list(missed)[:5]}")
    if false_positives:
        print(f"False positives (first 5): {list(false_positives)[:5]}")
    
    return metrics


if __name__ == "__main__":
    main()
