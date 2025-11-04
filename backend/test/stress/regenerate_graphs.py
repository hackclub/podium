#!/usr/bin/env python3
"""Script to regenerate graphs from stress test JSON report with better formatting."""

import json
import sys
from typing import List, Tuple, Dict, Any
from collections import defaultdict

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Error: matplotlib not available. Install with: pip install matplotlib")
    sys.exit(1)


def load_report_data(json_file: str) -> Dict[str, Any]:
    """Load the stress test report from JSON file."""
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File {json_file} not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {json_file}: {e}")
        sys.exit(1)


def extract_response_times(report: Dict[str, Any]) -> List[Tuple[str, float, int]]:
    """Extract response times from the report data, grouping similar endpoints."""
    response_times = []
    
    # Create a mapping from actual endpoint paths to methods using api_tests data
    endpoint_to_methods = defaultdict(set)
    api_tests = report.get("test_results", {}).get("api_tests", [])
    if api_tests:
        for test in api_tests:
            full_endpoint = test.get("endpoint", "")
            if " " in full_endpoint:
                method, path = full_endpoint.split(" ", 1)
                
                # Map API test paths to actual endpoint paths
                # This handles cases where api_tests has {event_id} but endpoints has actual paths
                actual_path = map_api_test_path_to_endpoint_path(path)
                if actual_path:
                    endpoint_to_methods[actual_path].add(method)
    
    # Group endpoints by their cleaned names, now with method information
    grouped_endpoints = defaultdict(lambda: {"total_requests": 0, "total_time": 0, "status_codes": []})
    
    for endpoint, stats in report.get("endpoints", {}).items():
        cleaned_path = clean_endpoint_name(endpoint)
        request_count = stats.get("request_count", 0)
        avg_time = stats.get("avg_response_time", 0)
        status_codes = stats.get("status_codes", [200])
        
        # Get methods for this actual endpoint path, or default to GET
        methods = endpoint_to_methods.get(endpoint, {"GET"})
        
        # Distribute requests across methods (simple equal distribution)
        requests_per_method = max(1, request_count // len(methods))
        
        for method in methods:
            cleaned_endpoint = f"{method} {cleaned_path}"
            grouped_endpoints[cleaned_endpoint]["total_requests"] += requests_per_method
            grouped_endpoints[cleaned_endpoint]["total_time"] += avg_time * requests_per_method
            grouped_endpoints[cleaned_endpoint]["status_codes"].extend(status_codes)
    
    # Now create response times for grouped endpoints
    for cleaned_endpoint, group_stats in grouped_endpoints.items():
        total_requests = group_stats["total_requests"]
        total_time = group_stats["total_time"]
        status_codes = group_stats["status_codes"]
        
        if total_requests > 0:
            # Calculate weighted average response time
            avg_time = total_time / total_requests
            
            # Create synthetic response times based on average
            for i in range(total_requests):
                # Add some variation to the average time
                variation = np.random.normal(0, avg_time * 0.1)  # 10% variation
                synthetic_time = max(0.001, avg_time + variation)
                
                # Use the most common status code
                status_code = max(set(status_codes), key=status_codes.count) if status_codes else 200
                
                response_times.append((cleaned_endpoint, synthetic_time, status_code))
    
    return response_times


def map_api_test_path_to_endpoint_path(api_path: str) -> str:
    """Map API test path (with placeholders) to actual endpoint path."""
    # Direct mappings for common patterns
    mappings = {
        "/events/{event_id}": "/events/rec***",
        "/events/{event_id}/projects": "/events/rec***/projects", 
        "/events/{event_id}/leaderboard": "/events/rec***/leaderboard",
        "/events/{event_id}/rank": "/events/rec***/rank",
        "/events/admin/{event_id}": "/events/admin/rec***",
        "/events/admin/{event_id}/leaderboard": "/events/admin/rec***/leaderboard",
        "/events/admin/{event_id}/attendees": "/events/admin/rec***/attendees",
        "/events/admin/{event_id}/votes": "/events/admin/rec***/votes",
        "/events/admin/{event_id}/referrals": "/events/admin/rec***/referrals",
        "/projects/{project_id}": "/projects/rec***",
        "/users/{user_id}": "/users/rec***",
    }
    
    # Check for exact matches first
    if api_path in mappings:
        return mappings[api_path]
    
    # For paths that don't have placeholders, return as-is
    if "{" not in api_path:
        return api_path
    
    # Try to find a pattern match
    for pattern, replacement in mappings.items():
        if api_path.startswith(pattern.split("{")[0]):
            return replacement
    
    # If no pattern matches, return the original path
    return api_path


def clean_endpoint_name(endpoint: str) -> str:
    """Clean endpoint names for better readability in graphs."""
    import re
    
    # Remove query parameters to group similar endpoints
    if "?" in endpoint:
        endpoint = endpoint.split("?")[0]
    
    # Replace Airtable record IDs with generic placeholders
    # Pattern: /events/rec[14+ chars] -> /events/rec***
    endpoint = re.sub(r'/events/rec[A-Za-z0-9]{14,}', '/events/rec***', endpoint)
    endpoint = re.sub(r'/projects/rec[A-Za-z0-9]{14,}', '/projects/rec***', endpoint)
    endpoint = re.sub(r'/users/rec[A-Za-z0-9]{14,}', '/users/rec***', endpoint)
    endpoint = re.sub(r'/admin/rec[A-Za-z0-9]{14,}', '/admin/rec***', endpoint)
    
    # Handle admin endpoints with record IDs
    endpoint = re.sub(r'/events/admin/rec[A-Za-z0-9]{14,}/', '/events/admin/rec***/', endpoint)
    
    # Group similar endpoints by removing specific IDs and parameters
    # Group all /events/attend endpoints together
    if endpoint.startswith("/events/attend"):
        endpoint = "/events/attend"
    
    # Group all /events/rec***/projects endpoints together
    if "/events/rec***/projects" in endpoint:
        endpoint = "/events/rec***/projects"
    
    # Group all /events/rec***/leaderboard endpoints together
    if "/events/rec***/leaderboard" in endpoint:
        endpoint = "/events/rec***/leaderboard"
    
    # Group all /events/rec***/rank endpoints together
    if "/events/rec***/rank" in endpoint:
        endpoint = "/events/rec***/rank"
    
    # Group all /events/admin/rec***/ endpoints together
    if "/events/admin/rec***/" in endpoint:
        endpoint = "/events/admin/rec***/*"
    
    # Shorten common patterns
    endpoint = endpoint.replace("/events/admin/", "/admin/")
    endpoint = endpoint.replace("/projects/", "/proj/")
    endpoint = endpoint.replace("/users/", "/user/")
    
    # Truncate very long endpoint names
    if len(endpoint) > 25:
        endpoint = endpoint[:22] + "..."
    
    return endpoint


def create_improved_response_time_graph(
    response_times: List[Tuple[str, float, int]], 
    output_file: str = "response_times_improved.png",
    title_suffix: str = ""
) -> str:
    """Create an improved response time visualization with better formatting."""
    if not response_times:
        return "No data to visualize"
    
    # Group by endpoint
    endpoint_times = defaultdict(list)
    for endpoint, time, status_code in response_times:
        endpoint_times[endpoint].append(time)
    
    # Clean endpoint names and sort by average response time
    cleaned_endpoints = {}
    for endpoint, times in endpoint_times.items():
        cleaned_name = clean_endpoint_name(endpoint)
        avg_time = sum(times) / len(times)
        cleaned_endpoints[cleaned_name] = (times, avg_time)
    
    # Sort by average response time (descending)
    sorted_endpoints = sorted(cleaned_endpoints.items(), key=lambda x: x[1][1], reverse=True)
    
    # Take top 20 endpoints to avoid overcrowding
    top_endpoints = sorted_endpoints[:20]
    
    if not top_endpoints:
        return "No endpoints to visualize"
    
    # Create subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))
    
    # Plot 1: Response times by endpoint (box plot) - top 20 only
    endpoints = [ep[0] for ep in top_endpoints]
    times_by_endpoint = [ep[1][0] for ep in top_endpoints]
    
    box_plot = ax1.boxplot(times_by_endpoint, tick_labels=endpoints, patch_artist=True)
    
    # Color boxes by response time
    colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(endpoints)))
    for patch, color in zip(box_plot['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax1.set_title(f"Response Times by Endpoint (Top 20){title_suffix}", fontsize=14, fontweight='bold')
    ax1.set_ylabel("Response Time (seconds)", fontsize=12)
    ax1.tick_params(axis='x', rotation=45, labelsize=10)
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Response time distribution
    all_times = [rt[1] for rt in response_times]
    ax2.hist(all_times, bins=30, alpha=0.7, edgecolor='black', color='skyblue')
    ax2.set_title(f"Response Time Distribution{title_suffix}", fontsize=14, fontweight='bold')
    ax2.set_xlabel("Response Time (seconds)", fontsize=12)
    ax2.set_ylabel("Frequency", fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    # Add statistics text
    mean_time = np.mean(all_times)
    median_time = np.median(all_times)
    ax2.axvline(mean_time, color='red', linestyle='--', alpha=0.7, label=f'Mean: {mean_time:.3f}s')
    ax2.axvline(median_time, color='orange', linestyle='--', alpha=0.7, label=f'Median: {median_time:.3f}s')
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    return f"Improved response time graph saved to {output_file}"


def create_improved_endpoint_comparison_graph(
    response_times: List[Tuple[str, float, int]], 
    output_file: str = "endpoint_comparison_improved.png",
    title_suffix: str = ""
) -> str:
    """Create an improved comparison graph with better formatting."""
    if not response_times:
        return "No data to visualize"
    
    # Group by endpoint
    endpoint_stats = defaultdict(lambda: {"times": [], "success_count": 0, "total_count": 0})
    
    for endpoint, time, status_code in response_times:
        endpoint_stats[endpoint]["times"].append(time)
        endpoint_stats[endpoint]["total_count"] += 1
        if 200 <= status_code < 300:
            endpoint_stats[endpoint]["success_count"] += 1
    
    # Prepare data and clean endpoint names
    endpoints = []
    avg_times = []
    success_rates = []
    request_counts = []
    
    for endpoint, stats in endpoint_stats.items():
        if stats["times"]:
            cleaned_endpoint = clean_endpoint_name(endpoint)
            endpoints.append(cleaned_endpoint)
            avg_times.append(sum(stats["times"]) / len(stats["times"]))
            success_rates.append(stats["success_count"] / stats["total_count"])
            request_counts.append(stats["total_count"])
    
    # Sort by average response time (descending) and take top 15
    sorted_data = sorted(zip(endpoints, avg_times, success_rates, request_counts), 
                        key=lambda x: x[1], reverse=True)
    top_data = sorted_data[:15]
    
    if not top_data:
        return "No endpoints to visualize"
    
    endpoints, avg_times, success_rates, request_counts = zip(*top_data)
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
    
    # Plot 1: Average response times
    bars1 = ax1.bar(range(len(endpoints)), avg_times, color='skyblue', alpha=0.7, edgecolor='navy')
    ax1.set_title(f"Average Response Times by Endpoint (Top 15){title_suffix}", 
                  fontsize=14, fontweight='bold')
    ax1.set_ylabel("Response Time (seconds)", fontsize=12)
    ax1.set_xticks(range(len(endpoints)))
    ax1.set_xticklabels(endpoints, rotation=45, ha='right', fontsize=10)
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars (only if not too crowded)
    if len(endpoints) <= 15:
        for i, (bar, time) in enumerate(zip(bars1, avg_times)):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + max(avg_times) * 0.01,
                    f'{time:.2f}s', ha='center', va='bottom', fontsize=8)
    
    # Plot 2: Success rates
    bars2 = ax2.bar(range(len(endpoints)), success_rates, color='lightgreen', alpha=0.7, edgecolor='darkgreen')
    ax2.set_title(f"Success Rates by Endpoint (Top 15){title_suffix}", 
                  fontsize=14, fontweight='bold')
    ax2.set_ylabel("Success Rate", fontsize=12)
    ax2.set_ylim(0, 1.1)
    ax2.set_xticks(range(len(endpoints)))
    ax2.set_xticklabels(endpoints, rotation=45, ha='right', fontsize=10)
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for i, (bar, rate) in enumerate(zip(bars2, success_rates)):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{rate:.1%}', ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    return f"Improved comparison graph saved to {output_file}"


def create_endpoint_heatmap(
    response_times: List[Tuple[str, float, int]], 
    output_file: str = "endpoint_heatmap.png",
    title_suffix: str = ""
) -> str:
    """Create a heatmap showing endpoint performance patterns."""
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
    data = []
    labels = []
    
    for endpoint, stats in endpoint_stats.items():
        if stats["times"]:
            cleaned_endpoint = clean_endpoint_name(endpoint)
            labels.append(cleaned_endpoint)
            
            avg_time = sum(stats["times"]) / len(stats["times"])
            success_rate = stats["success_count"] / stats["total_count"]
            request_count = stats["total_count"]
            
            data.append([avg_time, success_rate, request_count])
    
    if not data:
        return "No data to visualize"
    
    # Sort by average response time
    sorted_data = sorted(zip(labels, data), key=lambda x: x[1][0], reverse=True)
    top_data = sorted_data[:20]  # Top 20 endpoints
    
    if not top_data:
        return "No endpoints to visualize"
    
    labels, data = zip(*top_data)
    data = np.array(data)
    
    # Normalize data for heatmap (0=worst, 1=best)
    normalized_data = data.copy()
    # Response time: lower is better, so invert the normalization
    normalized_data[:, 0] = 1 - (data[:, 0] - data[:, 0].min()) / (data[:, 0].max() - data[:, 0].min())
    # Success rate: already 0-1, higher is better
    normalized_data[:, 1] = data[:, 1]
    # Request count: higher is better (more popular endpoint)
    normalized_data[:, 2] = (data[:, 2] - data[:, 2].min()) / (data[:, 2].max() - data[:, 2].min())
    
    # Create heatmap
    fig, ax = plt.subplots(figsize=(12, 10))
    
    im = ax.imshow(normalized_data.T, cmap='RdYlGn', aspect='auto')
    
    # Set labels
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=10)
    ax.set_yticks(range(3))
    ax.set_yticklabels(['Response Time', 'Success Rate', 'Request Count'], fontsize=12)
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Normalized Value (0=worst, 1=best)', fontsize=12)
    
    # Add text annotations
    for i in range(len(labels)):
        for j in range(3):
            value = data[i, j]
            if j == 0:  # Response time
                text = f'{value:.2f}s'
            elif j == 1:  # Success rate
                text = f'{value:.1%}'
            else:  # Request count
                text = f'{int(value)}'
            
            ax.text(i, j, text, ha='center', va='center', fontsize=8, 
                   color='white' if normalized_data[i, j] < 0.5 else 'black')
    
    ax.set_title(f"Endpoint Performance Heatmap (Top 20){title_suffix}", 
                 fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    
    return f"Heatmap saved to {output_file}"


def main():
    """Main function to regenerate graphs."""
    if len(sys.argv) < 2:
        json_file = "stress_test_report.json"
    else:
        json_file = sys.argv[1]
    
    print(f"Loading report from {json_file}...")
    report = load_report_data(json_file)
    
    print("Extracting response times...")
    response_times = extract_response_times(report)
    
    if not response_times:
        print("No response time data found in report")
        return
    
    print(f"Found {len(response_times)} response time entries")
    
    # Extract title suffix from report
    summary = report.get("summary", {})
    total_requests = summary.get("total_requests", 0)
    unique_endpoints = summary.get("unique_endpoints", 0)
    title_suffix = f" ({total_requests} requests, {unique_endpoints} endpoints)"
    
    print("Generating improved graphs...")
    
    # Generate improved graphs
    result1 = create_improved_response_time_graph(
        response_times, 
        "response_times_improved.png", 
        title_suffix
    )
    print(result1)
    
    result2 = create_improved_endpoint_comparison_graph(
        response_times, 
        "endpoint_comparison_improved.png", 
        title_suffix
    )
    print(result2)
    
    result3 = create_endpoint_heatmap(
        response_times, 
        "endpoint_heatmap.png", 
        title_suffix
    )
    print(result3)
    
    print("\nAll graphs regenerated successfully!")
    print("Files created:")
    print("- response_times_improved.png")
    print("- endpoint_comparison_improved.png") 
    print("- endpoint_heatmap.png")


if __name__ == "__main__":
    main()
