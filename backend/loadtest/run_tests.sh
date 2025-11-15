#!/bin/bash
# Quick stress test runner with common scenarios

set -e

# Default configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
RESULTS_DIR="results/$(date +%Y%m%d_%H%M%S)"

mkdir -p "$RESULTS_DIR"

echo "🚀 Podium Stress Test Suite"
echo "   Backend: $BACKEND_URL"
echo "   Results: $RESULTS_DIR"
echo ""

# Test 1: Baseline (cached, normal load)
echo "📊 Test 1/3: Baseline (cached, 200 users, 10min)"
locust -f loadtest/locustfile.py --headless \
  -u 200 -r 50 -t 10m \
  --host "$BACKEND_URL" \
  --csv "$RESULTS_DIR/baseline" \
  --html "$RESULTS_DIR/baseline.html"

echo ""
sleep 5

# Test 2: Cache-buster (stress Airtable)
echo "📊 Test 2/3: Cache-buster (150 users, 8min)"
CACHE_BUSTER=true locust -f loadtest/locustfile.py --headless \
  -u 150 -r 25 -t 8m \
  --host "$BACKEND_URL" \
  --csv "$RESULTS_DIR/cache_buster" \
  --html "$RESULTS_DIR/cache_buster.html"

echo ""
sleep 5

# Test 3: High concurrency (10 events)
echo "📊 Test 3/3: High concurrency (500 users, 10 events, 15min)"
EVENTS=10 locust -f loadtest/locustfile.py --headless \
  -u 500 -r 100 -t 15m \
  --host "$BACKEND_URL" \
  --csv "$RESULTS_DIR/high_load" \
  --html "$RESULTS_DIR/high_load.html"

echo ""
echo "✅ All tests complete!"
echo "   Results saved to: $RESULTS_DIR"
echo ""
echo "📈 Quick comparison:"
echo "   Baseline voting p95:      $(tail -n +2 "$RESULTS_DIR/baseline_stats.csv" | grep '/events/:id/vote' | cut -d',' -f7)"
echo "   Cache-buster voting p95:  $(tail -n +2 "$RESULTS_DIR/cache_buster_stats.csv" | grep '/events/:id/vote' | cut -d',' -f7)"
echo "   High-load voting p95:     $(tail -n +2 "$RESULTS_DIR/high_load_stats.csv" | grep '/events/:id/vote' | cut -d',' -f7)"
