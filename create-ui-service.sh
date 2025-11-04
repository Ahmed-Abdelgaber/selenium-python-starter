#!/bin/bash

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
SERVICE_NAME="${SERVICE_NAME:-medical-report-ui-service}"
CLUSTER_NAME="${CLUSTER_NAME:-etc-report-automation}"
TASK_DEFINITION_FAMILY="${TASK_DEFINITION_FAMILY:-medical-report-ui-task}"
DESIRED_COUNT="${DESIRED_COUNT:-1}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Creating ECS service for UI...${NC}"

# Check if service already exists
if aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION --query 'services[0].status' --output text 2>/dev/null | grep -q "ACTIVE"; then
  echo -e "${YELLOW}Service '$SERVICE_NAME' already exists in cluster '$CLUSTER_NAME'.${NC}"
  exit 0
fi

# Get the latest task definition
LATEST_TASK_DEF=$(aws ecs describe-task-definition \
  --task-definition $TASK_DEFINITION_FAMILY \
  --region $AWS_REGION \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text 2>/dev/null)

if [ -z "$LATEST_TASK_DEF" ]; then
  echo -e "${RED}Error: Task definition '$TASK_DEFINITION_FAMILY' not found.${NC}"
  echo -e "${YELLOW}Please register the task definition first by running:${NC}"
  echo "aws ecs register-task-definition --cli-input-json file://ui-taskdef.json --region $AWS_REGION"
  exit 1
fi

echo -e "${YELLOW}Using task definition: $LATEST_TASK_DEF${NC}"

# Create CloudWatch log group if it doesn't exist
LOG_GROUP_NAME="/ecs/medical-report-ui"
echo -e "${YELLOW}Ensuring CloudWatch log group exists...${NC}"
if ! aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP_NAME" --region $AWS_REGION --query "logGroups[?logGroupName=='$LOG_GROUP_NAME'].logGroupName" --output text | grep -q "$LOG_GROUP_NAME"; then
  echo -e "${YELLOW}Creating log group: $LOG_GROUP_NAME${NC}"
  aws logs create-log-group --log-group-name "$LOG_GROUP_NAME" --region $AWS_REGION
  echo -e "${GREEN}Log group created successfully${NC}"
else
  echo -e "${GREEN}Log group already exists${NC}"
fi

# Try to get network configuration from existing service
EXISTING_SERVICE=$(aws ecs list-services --cluster $CLUSTER_NAME --region $AWS_REGION --query 'serviceArns[0]' --output text 2>/dev/null | awk -F'/' '{print $NF}')

if [ ! -z "$EXISTING_SERVICE" ]; then
  echo -e "${YELLOW}Found existing backend service in cluster: $EXISTING_SERVICE${NC}"
  EXISTING_SUBNETS=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $EXISTING_SERVICE --region $AWS_REGION --query 'services[0].networkConfiguration.awsvpcConfiguration.subnets[]' --output text 2>/dev/null | tr '\t' ',' | sed 's/,$//')
  EXISTING_SG=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $EXISTING_SERVICE --region $AWS_REGION --query 'services[0].networkConfiguration.awsvpcConfiguration.securityGroups[0]' --output text 2>/dev/null)
  EXISTING_PUBLIC_IP=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $EXISTING_SERVICE --region $AWS_REGION --query 'services[0].networkConfiguration.awsvpcConfiguration.assignPublicIp' --output text 2>/dev/null)
  
  echo -e "${YELLOW}Network configuration from backend service (recommended to use same subnets):${NC}"
  echo -e "  Subnets: ${EXISTING_SUBNETS:-none}"
  echo -e "  Security Group: ${EXISTING_SG:-none} ${RED}(Note: UI needs inbound port 80)${NC}"
  echo -e "  Assign Public IP: ${EXISTING_PUBLIC_IP:-ENABLED}"
  echo ""
fi

# Prompt for network configuration
echo -e "${YELLOW}Please provide the following information:${NC}"
echo -e "${YELLOW}Recommended: Use the same subnets as the backend service${NC}"
read -p "Subnet IDs (comma-separated)${EXISTING_SUBNETS:+ [default: ${EXISTING_SUBNETS}]}: " SUBNETS
SUBNETS=${SUBNETS:-$EXISTING_SUBNETS}

read -p "Security Group IDs (comma-separated)${EXISTING_SG:+ [${EXISTING_SG}]}: " SECURITY_GROUPS
SECURITY_GROUPS=${SECURITY_GROUPS:-$EXISTING_SG}

DEFAULT_PUBLIC_IP=${EXISTING_PUBLIC_IP:-ENABLED}
read -p "Assign Public IP? (ENABLED/DISABLED) [${DEFAULT_PUBLIC_IP}]: " ASSIGN_PUBLIC_IP
ASSIGN_PUBLIC_IP=${ASSIGN_PUBLIC_IP:-$DEFAULT_PUBLIC_IP}

# Convert comma-separated values to arrays (remove spaces)
OLD_IFS=$IFS
IFS=',' read -ra SUBNET_LIST <<< "$(echo "$SUBNETS" | tr -d ' ')"
IFS=',' read -ra SG_LIST <<< "$(echo "$SECURITY_GROUPS" | tr -d ' ')"
IFS=$OLD_IFS

# Validate subnet format (must start with subnet-)
for subnet in "${SUBNET_LIST[@]}"; do
  if [[ ! "$subnet" =~ ^subnet-[0-9a-f]+$ ]]; then
    echo -e "${RED}Error: Invalid subnet format: $subnet. Subnets must match subnet-[0-9a-f]+${NC}"
    exit 1
  fi
done

# Build network configuration string properly formatted for AWS CLI
# AWS CLI expects space-separated values in the array brackets
SUBNET_STRING=$(IFS=' '; echo "${SUBNET_LIST[*]}")
SG_STRING=$(IFS=' '; echo "${SG_LIST[*]}")
IFS=$OLD_IFS

# Create the service
echo -e "${YELLOW}Creating ECS service...${NC}"
echo -e "${YELLOW}Using subnets: ${SUBNET_LIST[*]}${NC}"
echo -e "${YELLOW}Using security groups: ${SG_LIST[*]}${NC}"

# Create temporary JSON file for network configuration
TMP_NETWORK_CONFIG=$(mktemp)
cat > "$TMP_NETWORK_CONFIG" <<EOF
{
  "awsvpcConfiguration": {
    "subnets": $(printf '%s\n' "${SUBNET_LIST[@]}" | jq -R . | jq -s .),
    "securityGroups": $(printf '%s\n' "${SG_LIST[@]}" | jq -R . | jq -s .),
    "assignPublicIp": "$ASSIGN_PUBLIC_IP"
  }
}
EOF

aws ecs create-service \
  --cluster "$CLUSTER_NAME" \
  --service-name "$SERVICE_NAME" \
  --task-definition "$LATEST_TASK_DEF" \
  --desired-count "$DESIRED_COUNT" \
  --launch-type FARGATE \
  --network-configuration "file://$TMP_NETWORK_CONFIG" \
  --region "$AWS_REGION"

# Clean up temp file
rm -f "$TMP_NETWORK_CONFIG"

echo -e "${GREEN}Service '$SERVICE_NAME' created successfully!${NC}"
echo -e "${YELLOW}Waiting for service to become stable...${NC}"

aws ecs wait services-stable \
  --cluster $CLUSTER_NAME \
  --services $SERVICE_NAME \
  --region $AWS_REGION

echo -e "${GREEN}Service is now stable and running!${NC}"
