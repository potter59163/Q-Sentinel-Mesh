#!/usr/bin/env bash
set -euo pipefail

ACCOUNT="335158494927"
REGION="ap-southeast-7"

echo "=== Q-Sentinel Mesh — AWS Deployment ==="
echo "Account: $ACCOUNT | Region: $REGION"
echo ""

# Step 1: CDK bootstrap
echo "[1/5] Bootstrapping CDK..."
cd "$(dirname "$0")/cdk"
npm install --silent
npx cdk bootstrap "aws://${ACCOUNT}/${REGION}"

# Step 2: Deploy infrastructure
echo "[2/5] Deploying CDK stack..."
npx cdk deploy --require-approval never --outputs-file ../../cdk-outputs.json

BUCKET=$(python3 - <<'PY'
import json
with open("../../cdk-outputs.json", encoding="utf-8") as f:
    data = json.load(f)
print(data.get("QSentinelStack", {}).get("BucketName", ""))
PY
)

if [ -z "$BUCKET" ]; then
  echo "ERROR: BucketName output not found in cdk-outputs.json"
  exit 1
fi

# Step 3: Upload runtime assets to S3
echo "[3/5] Uploading runtime assets to S3 bucket ${BUCKET}..."
cd ../..
aws s3 cp weights/ "s3://${BUCKET}/weights/" --recursive \
  --storage-class STANDARD_IA \
  --region "$REGION"
aws s3 cp data/samples/ "s3://${BUCKET}/data/samples/" --recursive \
  --region "$REGION" || true

# Step 4: Upload results and optional artifacts to S3
echo "[4/5] Uploading results/artifacts to S3..."
aws s3 cp results/ "s3://${BUCKET}/results/" --recursive \
  --region "$REGION"
aws s3 cp slide_imgs/ "s3://${BUCKET}/reports/" --recursive \
  --region "$REGION" || true

# Step 5: Print outputs
echo "[5/5] Deployment complete!"
echo ""
cat cdk-outputs.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
stack = data.get('QSentinelStack', {})
print('API URL:          ', stack.get('ApiUrl', 'not deployed yet'))
print('S3 Bucket:        ', stack.get('BucketName', ''))
print('ECR URI:          ', stack.get('EcrUri', ''))
print('GitHub Actions Role:', stack.get('GithubActionsRoleArn', ''))
print('')
print('Next steps:')
print('1. Add AWS_ROLE_ARN secret to GitHub repo (value above)')
print('2. Create Amplify app in a supported Amplify region')
print('2. Frontend stays on CloudFront; set NEXT_PUBLIC_API_URL there if needed')
print('3. Push to main branch to trigger backend CI/CD')
"
