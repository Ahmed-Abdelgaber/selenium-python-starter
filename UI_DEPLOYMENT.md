# UI ECS Deployment Guide

This guide explains how to deploy the medical report UI to Amazon ECS.

## Prerequisites

1. AWS CLI configured with appropriate credentials
2. Docker installed and running
3. `jq` installed (for JSON parsing in deployment script)
4. AWS ECS cluster created
5. ECR repository access
6. IAM roles configured:
   - `ecsTaskExecutionRole` - for ECS task execution
   - `etc-report-automation-task-role` - for task role

## Configuration

The UI is configured to connect to the backend API at `3.230.1.49:8000`. This is set in:
- `ui-taskdef.json` - Environment variable `API_BASE_URL`
- `ui/Dockerfile` - Default environment variable
- `deploy-ui.sh` - Can be overridden via `API_BASE_URL` env variable

**Note**: The deployment is configured to use the existing cluster `etc-report-automation`.

## Quick Deployment

### 1. First-time Setup

If this is your first deployment, you need to:
- Register the task definition
- Create the ECS service

```bash
# Make scripts executable
chmod +x deploy-ui.sh create-ui-service.sh

# Register the task definition
aws ecs register-task-definition \
  --cli-input-json file://ui-taskdef.json \
  --region us-east-1

# Create the service (will prompt for network config)
./create-ui-service.sh
```

### 2. Deploy Updates

For subsequent deployments, simply run:

```bash
./deploy-ui.sh
```

This script will:
1. Login to ECR
2. Create ECR repository if needed
3. Build the Docker image
4. Push the image to ECR
5. Register a new task definition revision
6. Update the ECS service with the new image

### 3. Custom Configuration

You can override default values using environment variables:

```bash
# Deploy with custom backend URL
API_BASE_URL=your-backend-ip:port ./deploy-ui.sh

# Deploy with custom image tag
IMAGE_TAG=v1.0.0 ./deploy-ui.sh

# Deploy to different region/cluster
AWS_REGION=us-west-2 \
CLUSTER_NAME=my-cluster \
SERVICE_NAME=my-ui-service \
./deploy-ui.sh
```

## Architecture

### Components

1. **Docker Image**: Multi-stage build with Node.js for building React app and Nginx for serving
2. **Nginx Configuration**: 
   - Serves static React app
   - Proxies `/api` requests to backend at `3.230.1.49:8000`
   - Includes health check endpoint at `/health`
3. **ECS Task Definition**: Fargate-compatible task with minimal resources (256 CPU, 512 MB memory)
4. **Health Checks**: Container health check via `/health` endpoint

### Network Configuration

The UI service should use the same subnets as the backend service for optimal network connectivity:
- **Subnets**: Same as backend (`subnet-0c57f7450bc4a5961`, `subnet-014111be20e4d32a0`)
- **Public IP**: Same as backend (`ENABLED`)
- **Security Group**: Can use the same security group OR create a new one that allows:
  - Inbound HTTP (port 80) from the internet/ALB
  - Outbound traffic to backend API (port 8000) if needed

**Note**: The `create-ui-service.sh` script automatically detects and suggests the backend service's network configuration.

### Load Balancer (Optional)

For production, consider adding an Application Load Balancer:

```bash
# Create target group
aws elbv2 create-target-group \
  --name medical-report-ui-tg \
  --protocol HTTP \
  --port 80 \
  --vpc-id vpc-xxx \
  --target-type ip \
  --health-check-path /health

# Create/update listener to forward to target group
# ... (configure ALB rules)
```

Then update the ECS service to register with the target group:
```bash
aws ecs update-service \
  --cluster etc-report-automation \
  --service medical-report-ui-service \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=medical-report-ui,containerPort=80
```

## Troubleshooting

### Check Service Status
```bash
aws ecs describe-services \
  --cluster etc-report-automation \
  --services medical-report-ui-service \
  --region us-east-1
```

### View Logs
```bash
aws logs tail /ecs/medical-report-ui --follow --region us-east-1
```

### Check Task Status
```bash
aws ecs list-tasks \
  --cluster etc-report-automation \
  --service-name medical-report-ui-service \
  --region us-east-1
```

### Manual Task Execution (for testing)
```bash
aws ecs run-task \
  --cluster etc-report-automation \
  --task-definition medical-report-ui-task \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --region us-east-1
```

## Cost Optimization

- Current configuration uses minimal resources (256 CPU, 512 MB)
- Consider using Spot instances for non-production environments
- Enable CloudWatch logs retention policy to manage log costs
- Use Application Load Balancer with proper idle timeout settings

## Security Considerations

1. **Backend Communication**: The UI proxies API requests to `3.230.1.49:8000`. Ensure:
   - Network connectivity from ECS tasks to backend
   - Security groups allow traffic on port 8000
   - Backend is secured with authentication

2. **HTTPS**: For production, set up:
   - SSL certificate in ACM
   - Application Load Balancer with HTTPS listener
   - Redirect HTTP to HTTPS

3. **Environment Variables**: Sensitive data should be stored in:
   - AWS Secrets Manager
   - AWS Systems Manager Parameter Store
   - Not hardcoded in task definitions
