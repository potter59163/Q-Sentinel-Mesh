#!/bin/bash
set -euxo pipefail

APP_DIR="/opt/q-sentinel-mesh"
REPO_URL="https://github.com/potter59163/Q-Sentinel-Mesh.git"
APP_USER="ec2-user"
ASSET_BUCKET="__ASSET_BUCKET__"

dnf update -y
dnf install -y git nginx python3.11 python3.11-pip gcc gcc-c++ make tar gzip libgomp mesa-libGL curl
dnf remove -y nodejs nodejs-full-i18n npm || true
curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
dnf install -y nodejs
node -v
npm -v

mkdir -p /opt
cd /opt

if [ -d "$APP_DIR" ]; then
  rm -rf "$APP_DIR"
fi

git clone "$REPO_URL" "$APP_DIR"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

cd "$APP_DIR"

mkdir -p weights data/samples
if [ -n "$ASSET_BUCKET" ] && [ "$ASSET_BUCKET" != "__ASSET_BUCKET__" ]; then
  aws s3 sync "s3://${ASSET_BUCKET}/weights/" weights/ || true
  aws s3 sync "s3://${ASSET_BUCKET}/data/samples/" data/samples/ || true
fi

python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

cd frontend
npm ci
cat > .env.production <<'EOF'
NEXT_PUBLIC_API_URL=
EOF
npm run build
cd ..

cat > /etc/systemd/system/qsentinel-backend.service <<'EOF'
[Unit]
Description=Q-Sentinel FastAPI Backend
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/q-sentinel-mesh/backend
Environment=PYTHONUNBUFFERED=1
Environment=AWS_REGION=ap-southeast-7
Environment=USE_S3=false
Environment=CORS_ORIGINS=["*"]
ExecStart=/opt/q-sentinel-mesh/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/qsentinel-frontend.service <<'EOF'
[Unit]
Description=Q-Sentinel Next.js Frontend
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/q-sentinel-mesh/frontend
Environment=NODE_ENV=production
ExecStart=/usr/bin/npx next start -p 3000 -H 0.0.0.0
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/nginx/conf.d/qsentinel.conf <<'EOF'
server {
    listen 80 default_server;
    server_name _;

    client_max_body_size 250M;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

rm -f /etc/nginx/conf.d/default.conf
systemctl daemon-reload
systemctl enable qsentinel-backend qsentinel-frontend nginx
systemctl restart qsentinel-backend
systemctl restart qsentinel-frontend
systemctl restart nginx
