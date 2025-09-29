"""Response time reporting and visualization."""

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    np = None

from typing import List, Tuple, Dict, Any
from collections import defaultdict
import json


def generate_response_time_report(response_times: List[Tuple[str, float, int]]) -> Dict[str, Any]:
    """Generate a comprehensive response time report."""
    if not response_times:
        return {"error": "No response times to analyze"}
    
    # Group by endpoint
    endpoint_stats = defaultdict(list)
    for endpoint, time, status_code in response_times:
        endpoint_stats[endpoint].append((time, status_code))
    
    times = [rt[1] for rt in response_times]
    success_count = sum(1 for rt in response_times if 200 <= rt[2] < 300)
    
    avg_time = sum(times) / len(times) if times else 0
    
    report = {
        "summary": {
            "total_requests": len(response_times),
            "unique_endpoints": len(endpoint_stats),
            "avg_response_time": avg_time,
            "min_response_time": min(times) if times else 0,
            "max_response_time": max(times) if times else 0,
            "success_rate": success_count / len(response_times) if response_times else 0
        },
        "endpoints": {}
    }
    
    # Per-endpoint statistics
    for endpoint, times_statuses in endpoint_stats.items():
        times = [t[0] for t in times_statuses]
        status_codes = [t[1] for t in times_statuses]
        success_count = sum(1 for sc in status_codes if 200 <= sc < 300)
        
        # Calculate stats manually
        mean_time = sum(times) / len(times) if times else 0
        variance = sum((t - mean_time) ** 2 for t in times) / len(times) if times else 0
        std_time = variance ** 0.5
        
        report["endpoints"][endpoint] = {
            "request_count": len(times),
            "avg_response_time": mean_time,
            "min_response_time": min(times) if times else 0,
            "max_response_time": max(times) if times else 0,
            "std_response_time": std_time,
            "success_rate": success_count / len(status_codes) if status_codes else 0,
            "error_count": sum(1 for sc in status_codes if sc >= 400),
            "status_codes": list(set(status_codes))
        }
    
    return report


def create_response_time_graph(
    response_times: List[Tuple[str, float, int]], 
    output_file: str = "response_times.png",
    title_suffix: str = ""
) -> str:
    """Create a response time visualization."""
    if not MATPLOTLIB_AVAILABLE:
        return "Matplotlib not available, skipping graph generation"
    
    if not response_times:
        return "No data to visualize"
    
    # Group by endpoint
    endpoint_times = defaultdict(list)
    for endpoint, time, status_code in response_times:
        endpoint_times[endpoint].append(time)
    
    # Create subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot 1: Response times by endpoint (box plot)
    endpoints = list(endpoint_times.keys())
    times_by_endpoint = [endpoint_times[ep] for ep in endpoints]
    
    ax1.boxplot(times_by_endpoint, labels=endpoints)
    ax1.set_title(f"Response Times by Endpoint{title_suffix}")
    ax1.set_ylabel("Response Time (seconds)")
    ax1.tick_params(axis='x', rotation=45)
    
    # Plot 2: Response time distribution
    all_times = [rt[1] for rt in response_times]
    ax2.hist(all_times, bins=20, alpha=0.7, edgecolor='black')
    ax2.set_title(f"Response Time Distribution{title_suffix}")
    ax2.set_xlabel("Response Time (seconds)")
    ax2.set_ylabel("Frequency")
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    return f"Graph saved to {output_file}"


def create_endpoint_comparison_graph(
    response_times: List[Tuple[str, float, int]], 
    output_file: str = "endpoint_comparison.png",
    title_suffix: str = ""
) -> str:
    """Create a comparison graph of endpoints."""
    if not MATPLOTLIB_AVAILABLE:
        return "Matplotlib not available, skipping graph generation"
    
    if not response_times:
        return "No data to visualize"
    
    # Group by endpoint
    endpoint_stats = defaultdict(lambda: {"times": [], "success_count": 0, "total_count": 0})
    
    for endpoint, time, status_code in response_times:
        endpoint_stats[endpoint]["times"].append(time)
        endpoint_stats[endpoint]["total_count"] += 1
        if 200 <= status_code < 300:
            endpoint_stats[endpoint]["success_count"] += 1
    
    # Prepare data
    endpoints = []
    avg_times = []
    success_rates = []
    
    for endpoint, stats in endpoint_stats.items():
        if stats["times"]:
            endpoints.append(endpoint)
            avg_times.append(sum(stats["times"]) / len(stats["times"]))
            success_rates.append(stats["success_count"] / stats["total_count"])
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Plot 1: Average response times
    bars1 = ax1.bar(range(len(endpoints)), avg_times, color='skyblue', alpha=0.7)
    ax1.set_title(f"Average Response Times by Endpoint{title_suffix}")
    ax1.set_ylabel("Response Time (seconds)")
    ax1.set_xticks(range(len(endpoints)))
    ax1.set_xticklabels(endpoints, rotation=45, ha='right')
    
    # Add value labels on bars
    for i, bar in enumerate(bars1):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{height:.3f}s', ha='center', va='bottom', fontsize=8)
    
    # Plot 2: Success rates
    bars2 = ax2.bar(range(len(endpoints)), success_rates, color='lightgreen', alpha=0.7)
    ax2.set_title(f"Success Rates by Endpoint{title_suffix}")
    ax2.set_ylabel("Success Rate")
    ax2.set_ylim(0, 1.1)
    ax2.set_xticks(range(len(endpoints)))
    ax2.set_xticklabels(endpoints, rotation=45, ha='right')
    
    # Add value labels on bars
    for i, bar in enumerate(bars2):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{height:.1%}', ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    return f"Comparison graph saved to {output_file}"


def print_summary_report(report: Dict[str, Any]):
    """Print a formatted summary report."""
    print("\n" + "="*60)
    print("STRESS TEST SUMMARY REPORT")
    print("="*60)
    
    summary = report["summary"]
    print(f"Total Requests: {summary['total_requests']}")
    print(f"Unique Endpoints: {summary['unique_endpoints']}")
    print(f"Average Response Time: {summary['avg_response_time']:.3f}s")
    print(f"Min Response Time: {summary['min_response_time']:.3f}s")
    print(f"Max Response Time: {summary['max_response_time']:.3f}s")
    print(f"Success Rate: {summary['success_rate']:.1%}")
    
    print("\n" + "-"*60)
    print("PER-ENDPOINT BREAKDOWN")
    print("-"*60)
    
    for endpoint, stats in report["endpoints"].items():
        print(f"\n{endpoint}:")
        print(f"  Requests: {stats['request_count']}")
        print(f"  Avg Time: {stats['avg_response_time']:.3f}s")
        print(f"  Min Time: {stats['min_response_time']:.3f}s")
        print(f"  Max Time: {stats['max_response_time']:.3f}s")
        print(f"  Std Dev: {stats['std_response_time']:.3f}s")
        print(f"  Success Rate: {stats['success_rate']:.1%}")
        print(f"  Errors: {stats['error_count']}")
        print(f"  Status Codes: {stats['status_codes']}")


def save_report_to_file(report: Dict[str, Any], filename: str = "stress_test_report.json"):
    """Save the report to a JSON file."""
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    return f"Report saved to {filename}"
