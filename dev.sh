#!/bin/bash

set -e

echo "Starting gateway + microservices + frontend..."
echo "  Gateway:          http://localhost:3000"
echo "  Auth service:     http://localhost:8001/api"
echo "  Events service:   http://localhost:8002/api"
echo "  Projects service: http://localhost:8003/api"
echo "  Frontend:         http://localhost:5173"
echo ""

# Ensure Kafka is running and topics exist
if ! docker compose ps --status running | grep -q kafka; then
  echo "Starting Kafka..."
  docker compose up -d
  echo "Waiting for Kafka to be ready..."
  sleep 5
fi

echo "Ensuring Kafka topics exist..."
docker compose exec -T kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic votes --partitions 1 --replication-factor 1 2>/dev/null || true

echo "Open http://localhost:3000 in your browser."
echo ""

pnpm run dev
