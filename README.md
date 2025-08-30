## Production Runbook — Yash Full-Stack App

End-to-end guide to deploy a production-ready stack:

- Backend: FastAPI, SQLAlchemy (PostgreSQL), Alembic, JWT, bcrypt, CORS, AWS Lambda (API Gateway + Serverless + mangum)
- Frontend: React 18, Vite, React-Bootstrap, React Router, Axios (S3 + CloudFront hosting)

This document is step-by-step and opinionated for a smooth, secure launch.

---

## 0) Prerequisites

- AWS account with admin access (for initial provisioning)
- AWS CLI configured (`aws configure`) with the right account/region
- Python 3.11, Node.js 18+
- PostgreSQL access (local for dev; Amazon RDS in prod)
- Serverless Framework: `npm i -g serverless`

Repo layout highlights:

```
/backend  # FastAPI app
/infra    # serverless.yml, requirements, Makefile
/frontend # React + Vite app
```

---

## 1) Provision Production Infrastructure (AWS)

### 1.1 Create a PostgreSQL RDS instance

- Engine: PostgreSQL (14 or 15 recommended)
- Instance class: match load (e.g., t4g.small/t3.small for small apps)
- Storage: gp3, autoscaling enabled
- VPC: place RDS in a private subnet
- Security groups: allow inbound from Lambda security group (to be created/attached later)
- Get connection info: host, port (5432), db name, username, password

Construct your `DATABASE_URL`:
```
postgresql+psycopg2://<USER>:<PASSWORD>@<HOST>:5432/<DBNAME>
```

### 1.2 Store secrets in AWS SSM Parameter Store (recommended)

Use SecureString for sensitive values. Example namespace: `/yash/`.

```bash
aws ssm put-parameter --name /yash/DATABASE_URL --type SecureString --value "postgresql+psycopg2://..." --overwrite
aws ssm put-parameter --name /yash/JWT_SECRET --type SecureString --value "change_me_prod" --overwrite
aws ssm put-parameter --name /yash/JWT_EXPIRE_MINUTES --type String --value "15" --overwrite
aws ssm put-parameter --name /yash/WEB_ORIGIN --type String --value "https://your-frontend.example.com" --overwrite
aws ssm put-parameter --name /yash/ADMIN_EMAILS --type String --value "admin@example.com" --overwrite
```

You can inject these into the Serverless deploy environment (option A below), or wire Serverless to read SSM (option B).

### 1.3 (Optional but recommended) VPC for Lambda

If your RDS is in private subnets (recommended), attach Lambda to the same VPC and allowed subnets/security groups. In `infra/serverless.yml`, add a `vpc` block under `provider` or the `functions.api` definition:

```yaml
provider:
  vpc:
    securityGroupIds:
      - sg-xxxxxxxx
    subnetIds:
      - subnet-aaaaaaaa
      - subnet-bbbbbbbb
```

Ensure the security group allows outbound to RDS and RDS SG allows inbound from this Lambda SG.

---

## 2) Local Development (sanity check)

### 2.1 Backend

```bash
python -m venv .venv
# macOS/Linux
. .venv/bin/activate
# Windows PowerShell
.# .venv\Scripts\Activate.ps1

pip install -r infra/requirements.txt
cp ENV_BACKEND.example backend/.env

# Migrate DB (point DATABASE_URL to your local Postgres for dev)
DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/appdb" \
  alembic -c backend/alembic.ini upgrade head

uvicorn backend.main:app --reload
```

Seed admin users from `ADMIN_EMAILS`:
```bash
python -m backend.seed
```

### 2.2 Frontend

```bash
cd frontend
npm install
cp ../ENV_FRONTEND.example .env
npm run dev
```

Open `http://localhost:5173`. Ensure `VITE_API_BASE_URL` matches your API (`http://localhost:8000/api`).

---

## 3) Database Migration (production)

Run Alembic against your RDS using a secure workstation or CI runner:

macOS/Linux:
```bash
DATABASE_URL="postgresql+psycopg2://<USER>:<PASS>@<HOST>:5432/<DB>" \
  alembic -c backend/alembic.ini upgrade head
```

Windows PowerShell:
```powershell
$env:DATABASE_URL="postgresql+psycopg2://<USER>:<PASS>@<HOST>:5432/<DB>"; \
alembic -c backend/alembic.ini upgrade head
```

Tip: For CI, load `DATABASE_URL` from SSM or your secret store.

---

## 4) Backend Deployment (Serverless → Lambda + API Gateway)

Install Serverless plugin:
```bash
npm i -g serverless
sls plugin install -n serverless-python-requirements
```

There are two ways to provide env vars during deploy:

- Option A (simple): export env vars in your shell before running `sls deploy`.
  ```bash
  export DATABASE_URL=$(aws ssm get-parameter --name /yash/DATABASE_URL --with-decryption --query Parameter.Value --output text)
  export JWT_SECRET=$(aws ssm get-parameter --name /yash/JWT_SECRET --with-decryption --query Parameter.Value --output text)
  export JWT_EXPIRE_MINUTES=$(aws ssm get-parameter --name /yash/JWT_EXPIRE_MINUTES --query Parameter.Value --output text)
  export WEB_ORIGIN=$(aws ssm get-parameter --name /yash/WEB_ORIGIN --query Parameter.Value --output text)
  export ADMIN_EMAILS=$(aws ssm get-parameter --name /yash/ADMIN_EMAILS --query Parameter.Value --output text)

  sls deploy
  ```

- Option B (infra-as-code): change `infra/serverless.yml` to read from SSM directly, e.g. `${ssm:/yash/DATABASE_URL~true}`. Example:
  ```yaml
  provider:
    environment:
      DATABASE_URL: ${ssm:/yash/DATABASE_URL~true}
      JWT_SECRET: ${ssm:/yash/JWT_SECRET~true}
      JWT_EXPIRE_MINUTES: ${ssm:/yash/JWT_EXPIRE_MINUTES}
      WEB_ORIGIN: ${ssm:/yash/WEB_ORIGIN}
      ADMIN_EMAILS: ${ssm:/yash/ADMIN_EMAILS}
  ```
  Then simply run `sls deploy`.

After deployment, note the API base URL from Serverless output (HTTP API). Your base will look like:
```
https://<api-id>.execute-api.<region>.amazonaws.com
```
Set frontend `VITE_API_BASE_URL` to `https://.../api`.

Logs:
```bash
sls logs -f api --stage dev --tail
```

---

## 5) Frontend Production Build & Hosting (S3 + CloudFront)

### 5.1 Build
```bash
cd frontend
npm ci
echo VITE_API_BASE_URL=https://<api-id>.execute-api.<region>.amazonaws.com/api > .env
npm run build
```

### 5.2 S3 static hosting

- Create an S3 bucket (block public access OFF if using static website hosting) or keep private + serve via CloudFront OAI/OAC (recommended)
- Upload `dist/` contents to S3

CLI example (public bucket for simplicity; prefer CloudFront + OAC in production):
```bash
aws s3 sync dist s3://your-frontend-bucket --delete
```

### 5.3 CloudFront (recommended)

- Create a CloudFront distribution with the S3 bucket as origin
- Set `Default Root Object` to `index.html`
- Add a behavior to serve single-page app routes (return `index.html` on 404)
- Configure TLS with your domain (ACM cert in us-east-1)

Update `WEB_ORIGIN` SSM parameter to your CloudFront URL and redeploy the backend if needed (for strict CORS).

---

## 6) CI/CD (high-level)

Recommended pipeline:

1) On push to `main`:
- Backend: run `ruff`, `pytest` against a temporary or staging Postgres
- Alembic: run upgrade against staging DB
- Serverless deploy to staging

2) On release:
- Alembic upgrade against production DB
- Serverless deploy to production
- Frontend: Vite build, sync `dist/` to S3, create CloudFront invalidation

You can store secrets in GitHub Actions using OIDC + IAM roles, and fetch runtime config from SSM.

---

## 7) Verifications (post-deploy)

- Register → Login → Get `/api/users/me` with token
- Update profile, plans, notification prefs
- Fetch `/api/billing/invoices`
- Confirm CORS: DevTools network requests succeed from your frontend origin

---

## 8) Operations & Security

- CORS: lock `WEB_ORIGIN` to your exact frontend URL
- JWT secret: rotate periodically; store in SSM/Secrets Manager
- RDS: enable automated backups + multi-AZ (as budget allows)
- VPC: place RDS in private subnets, attach Lambda to VPC subnets/SG
- Least privilege IAM: Serverless deploy role, Lambda execution role
- Logging: CloudWatch Logs (API errors visible via `sls logs`)
- Metrics/Alarms: set CloudWatch alarms on 5XX, latency, throttles
- Migrations: run Alembic from CI/CD before backend deploys

---

## 9) Testing

Backend (requires Postgres `DATABASE_URL`):
```bash
pytest
```

Frontend:
```bash
cd frontend
npm test
```

---

## 10) Troubleshooting

- 401 Unauthorized: check token header, `JWT_SECRET`, clock skew
- CORS blocked: `WEB_ORIGIN` must exactly match your frontend URL
- Lambda cannot reach RDS: verify VPC/subnets/SG routing, NACLs, DNS
- Alembic errors: check `DATABASE_URL` and DB permissions; ensure migrations ran
- 5XX on API Gateway: inspect CloudWatch logs for the `api` function

---

## Useful Commands (Makefile shortcuts)

From repo root:

```bash
# Create venv, install backend deps
make venv

# Local dev (Uvicorn)
make dev

# Run Alembic migrations (uses env DATABASE_URL)
make migrate

# Deploy via Serverless
make deploy

# Tail Lambda logs
make logs
```

---

## API Summary

- POST `/api/auth/register`
- POST `/api/auth/login` → `{ access_token }`
- GET `/api/users/me`
- PUT `/api/users/me`
- DELETE `/api/users/me`
- GET `/api/users` (admin list via `ADMIN_EMAILS`)
