#!/bin/bash
set -euo pipefail

# Load .env file from project root
ENV_PATH="$(cd "$(dirname "$0")/.." && pwd)/.env"
if [ -f "$ENV_PATH" ]; then
  set -a
  source "$ENV_PATH"
  set +a
fi

PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
REGION="${GCP_REGION:-us-central1}"
SA_NAME="fi-nightlight-invoker"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Deploying fi-nightlight to ${PROJECT_ID} (${REGION})"

# Enable APIs
gcloud services enable \
  cloudfunctions.googleapis.com \
  cloudscheduler.googleapis.com \
  firestore.googleapis.com \
  --project="$PROJECT_ID"

# Deploy function (authenticated — no --allow-unauthenticated)
echo "Deploying Cloud Function..."

# Write env vars to a temp YAML file (avoids comma-delimiter conflicts with --set-env-vars)
ENV_FILE=$(mktemp)
trap "rm -f $ENV_FILE" EXIT
cat > "$ENV_FILE" <<ENVEOF
FI_USERNAME: "${FI_USERNAME}"
FI_PASSWORD: "${FI_PASSWORD}"
LATITUDE: "${LATITUDE}"
LONGITUDE: "${LONGITUDE}"
TIMEZONE: "${TIMEZONE:-America/New_York}"
GCP_PROJECT_ID: "${PROJECT_ID}"
FIRESTORE_COLLECTION: "${FIRESTORE_COLLECTION:-fi_nightlight}"
CUTOFF_HOUR: "${CUTOFF_HOUR:-1}"
POLL_INTERVAL_MINUTES: "${POLL_INTERVAL_MINUTES:-2}"
SLOW_POLL_INTERVAL_MINUTES: "${SLOW_POLL_INTERVAL_MINUTES:-5}"
LED_COLOR: "${LED_COLOR:-5}"
PET_NAME: "${PET_NAME:-}"
ENVEOF

gcloud functions deploy fi-nightlight \
  --gen2 \
  --runtime=python312 \
  --region="$REGION" \
  --source="$(cd "$(dirname "$0")/.." && pwd)" \
  --entry-point=fi_nightlight \
  --trigger-http \
  --no-allow-unauthenticated \
  --memory=512MiB \
  --env-vars-file="$ENV_FILE" \
  --project="$PROJECT_ID"

FUNCTION_URL=$(gcloud functions describe fi-nightlight --gen2 --region="$REGION" --project="$PROJECT_ID" --format='value(serviceConfig.uri)')

# Create service account for Cloud Scheduler
echo "Setting up service account..."
gcloud iam service-accounts create "$SA_NAME" \
  --display-name="Fi Nightlight Scheduler Invoker" \
  --project="$PROJECT_ID" 2>/dev/null || true

gcloud functions add-invoker-policy-binding fi-nightlight \
  --gen2 \
  --region="$REGION" \
  --member="serviceAccount:${SA_EMAIL}" \
  --project="$PROJECT_ID"

# Create scheduler job (every 5 min, authenticated)
echo "Creating Cloud Scheduler job..."
gcloud scheduler jobs create http fi-nightlight-check \
  --schedule="*/5 * * * *" \
  --uri="$FUNCTION_URL" \
  --http-method=GET \
  --oidc-service-account-email="$SA_EMAIL" \
  --time-zone="${TIMEZONE:-America/New_York}" \
  --location="$REGION" \
  --project="$PROJECT_ID" \
  2>/dev/null || gcloud scheduler jobs update http fi-nightlight-check \
  --schedule="*/5 * * * *" \
  --uri="$FUNCTION_URL" \
  --http-method=GET \
  --oidc-service-account-email="$SA_EMAIL" \
  --time-zone="${TIMEZONE:-America/New_York}" \
  --location="$REGION" \
  --project="$PROJECT_ID"

echo ""
echo "Deployed!"
echo "  Function: $FUNCTION_URL"
echo "  Scheduler: every 5 min (throttled to ${SLOW_POLL_INTERVAL_MINUTES:-6} min when dog is inside)"
