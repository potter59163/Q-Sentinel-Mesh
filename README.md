# Q-Sentinel Mesh

Clinical AI workspace for intracranial hemorrhage review, federated learning demos, and post-quantum security storytelling.

This repo now has 4 main parts:

- `frontend/`: Next.js dashboard UI
- `backend/`: FastAPI inference and demo API
- `src/` and `scripts/`: training, federated learning, PQC, evaluation
- `infra/`: AWS deployment helpers and CDK stack for container infrastructure

## Architecture

### Frontend

- Next.js App Router
- clinical dashboard UX for:
  - CT review
  - AI hemorrhage analysis
  - federated learning metrics
  - PQC/security view

### Backend

- FastAPI
- syncs runtime assets from S3 on startup when `USE_S3=true`
- loads baseline and hybrid weights from `weights/`
- serves:
  - `/api/ct/*`
  - `/api/predict/*`
  - `/api/federated/*`
  - `/api/pqc/*`
  - `/api/health`
  - `/api/health/ready`
- adds request tracing headers:
  - `x-request-id`
  - `x-response-time-ms`

### ML / Federated

- EfficientNet-B4 baseline
- hybrid quantum classifier
- Flower federated training
- ML-KEM / PQC utilities

## Local Development

### Backend

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate
py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install -r backend\requirements.txt
py -3.11 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Frontend

Create `frontend/.env.local`

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Then run:

```bat
cd frontend
npm ci
npm run dev
```

Open:

- frontend: `http://localhost:3000`
- backend health: `http://localhost:8000/api/health`
- backend readiness: `http://localhost:8000/api/health/ready`

Frontend notes:

- local API defaults to `http://localhost:8000`
- CT upload supports `.nii`, `.nii.gz`, and `.dcm`
- the dashboard opens a newly loaded CT at the middle slice by default
- changing CT case or switching model clears stale AI heatmaps/results
- the AI panel now includes loading, error, and run-status states

## Production Notes

### Required runtime assets

The backend expects these local assets at runtime:

- `weights/finetuned_ctich.pth`
- `weights/high_acc_b4.pth`
- `weights/hybrid_qsentinel.pth`
- optional demo scans in `data/samples/`

These large files are not stored in GitHub.

Runtime sync behavior:

- EC2 path: `infra/ec2-user-data.sh` syncs runtime assets before services start
- ECS path: backend startup syncs `weights/` and `data/samples/` directly from S3 when:
  - `USE_S3=true`
  - `S3_BUCKET` is set

Relevant backend env vars:

```env
USE_S3=true
S3_BUCKET=q-sentinel-runtime-<account-id>
WEIGHTS_S3_PREFIX=weights/
DEMO_SAMPLES_S3_PREFIX=data/samples/
```

### Frontend API configuration

The frontend reads:

```env
NEXT_PUBLIC_API_URL=
```

Examples:

- same origin via reverse proxy: leave empty
- direct backend URL: `NEXT_PUBLIC_API_URL=http://<backend-host>:8000`

In the current AWS setup, the recommended production value is the CloudFront origin:

```env
NEXT_PUBLIC_API_URL=https://d3grijenetuyp6.cloudfront.net
```

## AWS Deployment

There are 2 deployment paths in this repo.

### Option A: One-box EC2 deployment

Best when you want a fast, working deployment without local Docker.

- one EC2 instance
- Nginx reverse proxy
- Next.js frontend on port `3000`
- FastAPI backend on port `8000`
- public traffic through port `80`

Recommended security group:

- `80/tcp` from `0.0.0.0/0`
- `22/tcp` only if you need SSH

The helper deployment files are in:

- [infra/ec2-user-data.sh](C:/Users/parip/Downloads/CEDT%20hack/q-sentinel-mesh/infra/ec2-user-data.sh)
- [infra/upload-runtime-assets.ps1](C:/Users/parip/Downloads/CEDT%20hack/q-sentinel-mesh/infra/upload-runtime-assets.ps1)

That script:

- installs Node.js 20, Python 3.11, Nginx, and Git
- clones `https://github.com/potter59163/Q-Sentinel-Mesh.git`
- syncs weights and demo assets from S3
- installs frontend/backend dependencies
- builds the frontend
- starts backend and frontend with `systemd`
- routes `/api/*` to FastAPI and everything else to Next.js

### Option B: ECS + ECR + ALB

Best when you want the more cloud-native path.

- CDK stack in `infra/cdk/`
- frontend hosted behind CloudFront (`*.cloudfront.net` or custom domain)
- backend image in ECR
- ECS/Fargate service
- ALB endpoint (HTTP by default, HTTPS when Route53+ACM context is provided)
- S3 runtime bucket for uploads, model artifacts, reports, and results
- Secrets Manager for runtime env values
- CloudWatch alarms + SNS alert topic

Notes:

- this path needs Docker available during image build
- OIDC config now targets repo `potter59163/Q-Sentinel-Mesh`
- Route53/ACM is optional but recommended for production API domain

## AWS CLI Flow

### CDK / container path

```bash
cd infra/cdk
npm ci
npx cdk bootstrap aws://335158494927/ap-southeast-7
npx cdk deploy --require-approval never
```

To provision an HTTPS API domain (Route53 + ACM + ALB listener 443), set CDK context before deploy:

```bash
npx cdk deploy \
  -c apiDomainName=api.example.com \
  -c hostedZoneName=example.com \
  -c hostedZoneId=Z123456789 \
  -c alarmEmail=ops@example.com
```

If those contexts are omitted, stack deploys with ALB HTTP endpoint and still outputs `ApiUrl`.

### EC2 path

1. Launch an EC2 instance in `ap-southeast-7`
2. Use Amazon Linux 2023
3. Create an S3 bucket for runtime assets
4. Upload weights and optional demo scans with `infra/upload-runtime-assets.ps1`
5. Paste `infra/ec2-user-data.sh` into user data and replace `__ASSET_BUCKET__`
6. Open port `80`
7. Wait for cloud-init to finish
8. Open the EC2 public IP in the browser

Practical CLI flow:

```powershell
aws s3 mb s3://q-sentinel-runtime-<account-id> --region ap-southeast-7
powershell -ExecutionPolicy Bypass -File infra/upload-runtime-assets.ps1 q-sentinel-runtime-<account-id>
```

Then edit `infra/ec2-user-data.sh` and replace `__ASSET_BUCKET__` with that bucket name before launching the instance.

Recommended instance shape for demo use:

- `t3.large` minimum
- `50 GB` gp3 root volume
- IAM role with `AmazonS3ReadOnlyAccess` and `AmazonSSMManagedInstanceCore`

After boot, verify:

```bash
curl http://<ec2-public-ip>/api/health
curl http://<ec2-public-ip>/api/health/ready
```

Run post-deploy smoke checks:

```bash
python scripts/post_deploy_smoke.py --base-url http://<ec2-public-ip>
```

## GitHub

Primary deployment repo:

- [potter59163/Q-Sentinel-Mesh](https://github.com/potter59163/Q-Sentinel-Mesh)

Legacy repo:

- [potter59163/QsentinelMesh](https://github.com/potter59163/QsentinelMesh)

## Verification

Frontend checks:

```bat
cd frontend
npm run lint
npx tsc --noEmit
```

Backend health:

```bat
curl http://localhost:8000/api/health
curl http://localhost:8000/api/health/ready
py -3.11 scripts\post_deploy_smoke.py --base-url http://localhost:8000
```

Useful production checks:

```bash
curl https://d3grijenetuyp6.cloudfront.net/api/health
curl https://d3grijenetuyp6.cloudfront.net/api/health/ready
curl https://d3grijenetuyp6.cloudfront.net/api/ct/demo
```

## Hackathon Context

Built for CEDT Hackathon 2026 as a privacy-first medical AI demo combining:

- CT hemorrhage triage
- federated learning
- post-quantum secure model exchange

## License

MIT
