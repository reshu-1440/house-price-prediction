#!/usr/bin/env bash
set -euo pipefail

STACK_NAME="${STACK_NAME:-house-price-prediction-prod}"
AWS_REGION="${AWS_REGION:-ap-south-1}"
ENVIRONMENT="${ENVIRONMENT:-production}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
VPC_ID="${VPC_ID:?Set VPC_ID before running aws_deploy.sh}"
SUBNET_IDS="${SUBNET_IDS:?Set comma-separated SUBNET_IDS before running aws_deploy.sh}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
ECR_REPO="house-price-prediction-api"
FULL_IMAGE="${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}"

echo "Verifying ECR repository exists..."
aws ecr describe-repositories --repository-names "${ECR_REPO}" --region "${AWS_REGION}" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "${ECR_REPO}" --region "${AWS_REGION}" >/dev/null

echo "Logging into ECR and pushing ${FULL_IMAGE}..."
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${ECR_REGISTRY}"
docker build --target runtime -t "${FULL_IMAGE}" .
docker push "${FULL_IMAGE}"

echo "Deploying CloudFormation stack ${STACK_NAME}..."
aws cloudformation deploy \
  --template-file infrastructure/cloudformation.yaml \
  --stack-name "${STACK_NAME}" \
  --region "${AWS_REGION}" \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    Environment="${ENVIRONMENT}" \
    VpcId="${VPC_ID}" \
    SubnetIds="${SUBNET_IDS}" \
    ContainerImage="${FULL_IMAGE}"

aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${AWS_REGION}" \
  --query "Stacks[0].Outputs" \
  --output table
