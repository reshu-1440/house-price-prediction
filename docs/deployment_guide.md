# Cloud Deployment Guide (AWS ECS Fargate)

This guide covers deploying the House Price Prediction FastAPI service to AWS using [`infrastructure/cloudformation.yaml`](../infrastructure/cloudformation.yaml), [`config/production.yaml`](../config/production.yaml), and [`scripts/aws_deploy.sh`](../scripts/aws_deploy.sh).

---

## 1. Prerequisites

- AWS CLI v2 configured via IAM user profile or GitHub Actions OIDC (`AWS_DEPLOY_ROLE_ARN`) — never commit access keys.
- Docker Engine / Buildx installed locally or running in CI.
- Existing VPC ID and at least two subnet IDs across distinct Availability Zones.
- Trained model artifact (`models/house_price_pipeline.joblib` + `models/metadata.json`) generated via `python -m src.pipeline.training_pipeline`.

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
