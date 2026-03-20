#!/bin/bash

KESTRA_URL="http://localhost:8080"
HEALTH_URL="http://localhost:8081/health"
NAMESPACE="tech.observatory"
CREDENTIALS_FILE="/home/derrrick-ryan-giggs/.gcp/tech-obs-sa.json"
FLOW_FILE="$HOME/Desktop/DEZ Capstone/kestra/tech_observatory_flow.yml"
AUTH=$(echo -n 'admin@admin.com:@Rayann18' | base64)

echo "Waiting for Kestra to be ready..."
until curl -s "$HEALTH_URL" | grep -q '"status":"UP"'; do
    sleep 2
done
echo "Kestra is ready."

# Register or update the flow (PUT creates or updates)
echo "Registering flow..."
curl -s -X PUT "$KESTRA_URL/api/v1/flows/tech.observatory/tech_observatory_pipeline" \
    -H "Authorization: Basic $AUTH" \
    -H "Content-Type: application/x-yaml" \
    --data-binary @"$FLOW_FILE"
echo ""
echo "Flow registered."

# Set GCP credentials in KV store
echo "Setting GCP_CREDENTIALS in KV store..."
GCP_CREDS=$(cat "$CREDENTIALS_FILE")
curl -s -X PUT "$KESTRA_URL/api/v1/namespaces/$NAMESPACE/kv/GCP_CREDENTIALS" \
    -H "Authorization: Basic $AUTH" \
    -H "Content-Type: text/plain" \
    -d "$GCP_CREDS"
echo ""
echo "KV pair set."

echo "Done. Go to $KESTRA_URL"
