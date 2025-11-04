#!/bin/bash

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-380264618909}"
ECR_REPOSITORY="${ECR_REPOSITORY:-medical-report-ui}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
TASK_DEFINITION_FILE="ui-taskdef.json"
SERVICE_NAME="${SERVICE_NAME:-medical-report-ui-service}"
CLUSTER_NAME="${CLUSTER_NAME:-etc-report-automation}"
API_BASE_URL="${API_BASE_URL:-3.230.1.49:8000}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting UI deployment to ECS...${NC}"

# Step 1: Login to ECR
echo -e "${YELLOW}Step 1: Logging in to Amazon ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Step 2: Create ECR repository if it doesn't exist
echo -e "${YELLOW}Step 2: Ensuring ECR repository exists...${NC}"
aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION 2>/dev/null || \
aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION --image-scanning-configuration scanOnPush=true

# Step 2.5: Create CloudWatch log group if it doesn't exist
LOG_GROUP_NAME="/ecs/medical-report-ui"
echo -e "${YELLOW}Step 2.5: Ensuring CloudWatch log group exists...${NC}"
if ! aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP_NAME" --region $AWS_REGION --query "logGroups[?logGroupName=='$LOG_GROUP_NAME'].logGroupName" --output text 2>/dev/null | grep -q "$LOG_GROUP_NAME"; then
  aws logs create-log-group --log-group-name "$LOG_GROUP_NAME" --region $AWS_REGION
  echo -e "${GREEN}Log group created${NC}"
fi

# Step 3: Build Docker image
echo -e "${YELLOW}Step 3: Building Docker image...${NC}"
cd ui
docker build --build-arg VITE_API_BASE_URL=http://$API_BASE_URL -t $ECR_REPOSITORY:$IMAGE_TAG .
cd ..

# Step 4: Tag image
echo -e "${YELLOW}Step 4: Tagging Docker image...${NC}"
docker tag $ECR_REPOSITORY:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG

# Step 5: Push image to ECR
echo -e "${YELLOW}Step 5: Pushing Docker image to ECR...${NC}"
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG

# Step 6: Update task definition with new image and API URL
echo -e "${YELLOW}Step 6: Updating task definition...${NC}"
IMAGE_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG"

# Update the task definition JSON with the new image URI and API_BASE_URL
# Create a temporary file for the updated task definition
TMP_TASK_DEF=$(mktemp)
cat "$TASK_DEFINITION_FILE" | \
  jq --arg img "$IMAGE_URI" --arg api_url "$API_BASE_URL" '
    .containerDefinitions[0].image = $img |
    .containerDefinitions[0].environment = (
      .containerDefinitions[0].environment |
      map(if .name == "API_BASE_URL" then .value = $api_url else . end)
    )
  ' > "$TMP_TASK_DEF"

# Step 7: Register new task definition revision
echo -e "${YELLOW}Step 7: Registering new task definition revision...${NC}"
TASK_DEF_ARN=$(aws ecs register-task-definition --cli-input-json file://"$TMP_TASK_DEF" --region $AWS_REGION --query 'taskDefinition.taskDefinitionArn' --output text)

# Clean up temp file
rm -f "$TMP_TASK_DEF"

echo -e "${GREEN}Task definition registered: $TASK_DEF_ARN${NC}"

# Step 8: Update ECS service (if service exists)
echo -e "${YELLOW}Step 8: Updating ECS service...${NC}"
if aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION --query 'services[0].status' --output text 2>/dev/null | grep -q "ACTIVE"; then
  aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $SERVICE_NAME \
    --task-definition $TASK_DEF_ARN \
    --region $AWS_REGION \
    --force-new-deployment > /dev/null
  
  echo -e "${GREEN}Service update initiated. Waiting for service to stabilize...${NC}"
  aws ecs wait services-stable \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --region $AWS_REGION
  
  echo -e "${GREEN}Service update completed successfully!${NC}"
else
  echo -e "${YELLOW}Service '$SERVICE_NAME' does not exist. Skipping service update.${NC}"
  echo -e "${YELLOW}You may need to create the service manually.${NC}"
  echo -e "${YELLOW}Example command:${NC}"
  echo "aws ecs create-service \\"
  echo "  --cluster $CLUSTER_NAME \\"
  echo "  --service-name $SERVICE_NAME \\"
  echo "  --task-definition $TASK_DEF_ARN \\"
  echo "  --desired-count 1 \\"
  echo "  --launch-type FARGATE \\"
  echo "  --network-configuration 'awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}' \\"
  echo "  --region $AWS_REGION"
fi

echo -e "${GREEN}Deployment completed successfully!${NC}"
