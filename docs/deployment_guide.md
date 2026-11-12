# Cloud Deployment Guide (AWS ECS Fargate)

This guide covers deploying the House Price Prediction FastAPI service to AWS using [`infrastructure/cloudformation.yaml`](../infrastructure/cloudformation.yaml), [`config/production.yaml`](../config/production.yaml), and [`scripts/aws_deploy.sh`](../scripts/aws_deploy.sh).

---

## 1. Prerequisites

- AWS CLI v2 configured via IAM user profile or GitHub Actions OIDC (`AWS_DEPLOY_ROLE_ARN`) — never commit access keys.
- Docker Engine / Buildx installed locally or running in CI.
- Existing VPC ID and at least two subnet IDs across distinct Availability Zones.
- Trained model artifact (`models/house_price_pipeline.joblib` + `models/metadata.json`) generated via:
  ```bash
  python Data/data_download.py
  python -m src.pipeline.training_pipeline
  ```
  *(Note: `models/*.joblib` and `Data/house_prices.csv` are gitignored. Docker builds succeed without them, and `/health` reports `degraded` until `models/house_price_pipeline.joblib` is present or mounted at `MODEL_PATH`.)*

---

## 2. Architecture Provisioned by CloudFormation

`infrastructure/cloudformation.yaml` provisions:
- **Amazon ECR** (`house-price-prediction-api`) with scan-on-push and 10-image retention.
- **Amazon S3** encrypted, versioned bucket with public access blocked for model artifacts.
- **Amazon ECS Fargate Cluster & Service** running non-root container port `8000` with CloudWatch Logs (`/ecs/house-price-prediction-<env>`).
- **Application Load Balancer (ALB)** forwarding HTTP port `80` to ECS tasks with `/health` target health checks.

---

## 3. Manual / Scripted Deployment

```bash
export AWS_REGION="ap-south-1"
export VPC_ID="vpc-xxxxxxxx"
export SUBNET_IDS="subnet-aaaaaaa,subnet-bbbbbbb"
export IMAGE_TAG="v0.1.0"

bash scripts/aws_deploy.sh
```

After deployment finishes, verify the ALB endpoint output:

```bash
curl -fsS "http://<ALB_DNS_NAME>/health"
```

---

## 4. Production Configuration Overrides

Runtime server parameters (`host`, `port`, `workers`, `log_level`, `cors.allowed_origins`) are stored in [`config/production.yaml`](../config/production.yaml) and loaded by `load_production_settings()` in [`src/api/app.py`](../src/api/app.py). Environment variables `MODEL_PATH` and `ALLOWED_ORIGINS` override YAML defaults at container runtime.

---

## 5. Teardown

```bash
aws cloudformation delete-stack --stack-name house-price-prediction-prod --region ap-south-1
```

---

## 6. Free Deployment (Vercel Frontend + Render Backend + UptimeRobot)

For zero-cost portfolio/demo hosting without AWS charges:

1. **Backend + Model on Render Free (`render.yaml`, `Dockerfile.render`, `requirements-serve.txt`)**:
   - Uses a slim inference-only image (`requirements-serve.txt`), binds dynamic `${PORT:-8000}`, and runs `--workers 1` to fit within Render Free's **512 MB RAM** limit.
   - `models/house_price_pipeline.joblib` (~2.02 MB) is allowlisted in `.gitignore` so GitHub auto-deploys include the trained pipeline.
   - `buildFilter` in `render.yaml` skips backend rebuilds when only `frontend/` changes.
   - Set `ALLOWED_ORIGINS` in the Render dashboard to your Vercel URL (e.g., `https://your-app.vercel.app`) alongside `APP_ENV=production`.
2. **Frontend on Vercel (`frontend/vercel.json`)**:
   - Import the repo in Vercel with **Root Directory** set to `frontend`.
   - Set environment variable `VITE_API_BASE_URL` to your Render service URL (e.g., `https://house-price-prediction-api.onrender.com`).
3. **Keep Render Awake with UptimeRobot**:
   - Create one free HTTP(S) or Keyword monitor in UptimeRobot targeting `https://<your-render-service>.onrender.com/health` at a **5-minute** (free minimum) or **10-minute** interval.
   - Both `GET /health` and `HEAD /health` return HTTP `200`.
   - Keeping **1** service awake 24/7 uses ~744 of Render's **750 free monthly instance-hours** per workspace; do not run a second always-awake free web service in the same Render workspace.
