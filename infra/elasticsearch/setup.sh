#!/bin/bash
set -euo pipefail

ES_URL="${ELASTICSEARCH_URL:-http://elasticsearch:9200}"

echo "Waiting for Elasticsearch to be ready..."
until curl -sf "${ES_URL}/_cluster/health" > /dev/null 2>&1; do
    sleep 2
done
echo "Elasticsearch is ready."

echo "Creating index template..."
curl -sf -X PUT "${ES_URL}/_index_template/rules_template" \
    -H "Content-Type: application/json" \
    -d @/setup/rules-index-template.json

echo ""
echo "Creating rules index if it does not exist..."
curl -sf -X PUT "${ES_URL}/rules" -H "Content-Type: application/json" -d '{}' || true

echo ""
echo "Elasticsearch setup complete."
