#!/usr/bin/env python3
# watch -- poetry.exe run python -m quality.analyze_correctness
"""
Simple script to analyze correctness percentage from quality check results.

Usage:
    poetry run python -m quality.analyze_correctness
"""

PRINT_SPECIFICS = True

import os
import csv
import glob


def load_sample_data(sample_file: str):
    """Load sample data from CSV file."""
    sample_data = {}
    
    if not os.path.exists(sample_file):
        print(f"Warning: Sample file {sample_file} not found")
        return sample_data
    
    with open(sample_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            demo_url = row.get('demo', '').strip()
            judgement = row.get('judgement', '').strip().lower()
            if demo_url and judgement:
                sample_data[demo_url] = judgement
    
    return sample_data


def load_quality_results(results_folder: str):
    """Load quality check results from the most recent results file."""
    date_folders = glob.glob(os.path.join(results_folder, "*/"))
    if not date_folders:
        print(f"No results found in {results_folder}")
        return []
    
    latest_folder = max(date_folders, key=os.path.getctime)
    results_file = os.path.join(latest_folder, "results.csv")
    
    if not os.path.exists(results_file):
        print(f"Results file not found: {results_file}")
        return []
    
    results = []
    with open(results_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            results.append(row)
    
    return results


def calculate_percentage_correct(sample_data, quality_results):
    """Calculate percentage correct for unified validation only.
    
    Note: Sample data only contains unified judgements (approved/rejected for entire projects),
    so we can only meaningfully compare against unified validation results.
    """
    
    unified_correct = 0
    total_matched = 0
    
    # Track false rejections and false approvals for unified validation
    unified_false_rejections = 0
    unified_false_approvals = 0
    
    # Count total approved/rejected in sample data
    total_approved_in_sample = 0
    total_rejected_in_sample = 0
    
    incorrect_predictions = []
    
    for result in quality_results:
        demo_url = result.get('demo', '').strip()
        
        if demo_url not in sample_data:
            continue
        
        sample_approved = sample_data[demo_url] == 'approved'
        # Use the 'valid' field from the current CSV structure
        system_valid = result.get('valid', '').lower() == 'true'
        
        total_matched += 1
        
        # Count sample data distribution
        if sample_approved:
            total_approved_in_sample += 1
        else:
            total_rejected_in_sample += 1
        
        # Compare system validation against sample judgement
        if system_valid == sample_approved:
            unified_correct += 1
        else:
            if sample_approved and not system_valid:
                unified_false_rejections += 1
            elif not sample_approved and system_valid:
                unified_false_approvals += 1
        
        # Collect incorrect predictions for detailed analysis
        if system_valid != sample_approved:
            incorrect_predictions.append({
                'demo_url': demo_url,
                'project_index': result.get('project_index', ''),
                'system_valid': system_valid,
                'sample_approved': sample_approved,
                'error': result.get('error', ''),
                'explanation': result.get('explanation', ''),
                'raw_result': result.get('raw_result', '')
            })
    
    # Calculate percentages
    unified_percent = (unified_correct / total_matched * 100) if total_matched > 0 else 0
    
    # Calculate false rejection/approval percentages
    unified_false_rejection_percent = (unified_false_rejections / total_approved_in_sample * 100) if total_approved_in_sample > 0 else 0
    unified_false_approval_percent = (unified_false_approvals / total_rejected_in_sample * 100) if total_rejected_in_sample > 0 else 0
    
    return {
        'unified_percent': unified_percent,
        'total_matched': total_matched,
        'total_approved_in_sample': total_approved_in_sample,
        'total_rejected_in_sample': total_rejected_in_sample,
        'unified_false_rejections': unified_false_rejections,
        'unified_false_approvals': unified_false_approvals,
        'unified_false_rejection_percent': unified_false_rejection_percent,
        'unified_false_approval_percent': unified_false_approval_percent,
        'incorrect_predictions': incorrect_predictions
    }


def main():
    """Main function."""
    sample_file = "sample_projects.csv"
    results_folder = "quality_check_results"
    
    # Load data
    sample_data = load_sample_data(sample_file)
    quality_results = load_quality_results(results_folder)
    
    if not sample_data or not quality_results:
        print("Error: Could not load required data")
        return
    
    # Calculate percentages
    results = calculate_percentage_correct(sample_data, quality_results)
    print(f"Unified validation correct: {results['unified_percent']:.1f}%")
    print(f"Total projects analyzed: {results['total_matched']}")
    
    # Output results
    # Show incorrect predictions
    if results['incorrect_predictions'] and PRINT_SPECIFICS:
        print(f"\nIncorrect Predictions ({len(results['incorrect_predictions'])} total):")
        print("=" * 80)
        
        for i, pred in enumerate(results['incorrect_predictions'], 1):
            print(f"\n{i}. Project {pred['project_index']}: {pred['demo_url']}")
            print(f"   Real result: {'Approved' if pred['sample_approved'] else 'Rejected'}")
            print(f"   System output: {'Valid' if pred['system_valid'] else 'Invalid'}")
            
            # Show reasoning
            if pred['explanation']:
                print(f"   System reasoning: {pred['explanation']}")
            if pred['error']:
                print(f"   System error: {pred['error']}")
            if pred['raw_result']:
                print(f"   Raw result: {pred['raw_result']}")
            
            print("-" * 80)
    
    
    # Print comprehensive stats after per-project details
    print(f"\n=== COMPREHENSIVE STATISTICS ===")
    print(f"Sample data distribution:")
    print(f"  - Approved projects: {results['total_approved_in_sample']}")
    print(f"  - Rejected projects: {results['total_rejected_in_sample']}")
    
    print(f"\nUnified validation breakdown:")
    print(f"  - False rejections: {results['unified_false_rejections']} ({results['unified_false_rejection_percent']:.1f}% of approved projects)")
    print(f"  - False approvals: {results['unified_false_approvals']} ({results['unified_false_approval_percent']:.1f}% of rejected projects)")
    


if __name__ == "__main__":
    main() 