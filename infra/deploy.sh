#!/usr/bin/env bash
set -euo pipefail

ACCOUNT="335158494927"
REGION="ap-southeast-7"
BUCKET="q-sentinel-data-${ACCOUNT}"

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

# Step 3: Upload weights to S3
echo "[3/5] Uploading model weights to S3..."
cd ../..
aws s3 cp weights/ "s3://${BUCKET}/weights/" --recursive \
  --storage-class STANDARD_IA \
  --region "$REGION"

# Step 4: Upload results to S3
echo "[4/5] Uploading results to S3..."
aws s3 cp results/ "s3://${BUCKET}/results/" --recursive \
  --region "$REGION"

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
print('   - Connect to GitHub: potter59163/Q-Sentinel-Mesh')
print('   - Set NEXT_PUBLIC_API_URL =', stack.get('ApiUrl', '<API_URL>'))
print('3. Push to main branch to trigger CI/CD')
"
