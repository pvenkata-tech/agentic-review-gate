# Deployment Guide

Quick-start guides for deploying the agentic-review-gate system to various platforms.

## Local Development

```bash
# 1. Clone repo
git clone https://github.com/your-org/agentic-review-gate.git
cd agentic-review-gate

# 2. Create environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -e ".[dev,llm]"

# 4. Create .env file
cat > .env << EOF
GITHUB_TOKEN=ghp_...
GITHUB_OWNER=your-org
GITHUB_REPO=your-repo
LOG_LEVEL=INFO
USE_LLM_LOGIC=false
EOF

# 5. Run server
python -m code_reviewer.main

# 6. In another terminal, run examples
python examples.py
```

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[llm]"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run server
CMD ["python", "-m", "code_reviewer.main"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  code-reviewer:
    build: .
    ports:
      - "8000:8000"
    environment:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
      GITHUB_OWNER: ${GITHUB_OWNER}
      GITHUB_REPO: ${GITHUB_REPO}
      LOG_LEVEL: INFO
      USE_LLM_LOGIC: "false"
    volumes:
      - ./logs:/app/logs
    networks:
      - code-review
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - code-review
    restart: unless-stopped

networks:
  code-review:
    driver: bridge
```

Build and run:

```bash
docker-compose up -d
```

## Kubernetes Deployment

### Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: code-reviewer
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: code-reviewer
  template:
    metadata:
      labels:
        app: code-reviewer
    spec:
      containers:
      - name: code-reviewer
        image: your-registry/code-reviewer:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: github-secrets
              key: token
        - name: GITHUB_OWNER
          value: "your-org"
        - name: GITHUB_REPO
          value: "your-repo"
        - name: LOG_LEVEL
          value: "INFO"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"

---
apiVersion: v1
kind: Service
metadata:
  name: code-reviewer-service
spec:
  selector:
    app: code-reviewer
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

Deploy:

```bash
# Create secret
kubectl create secret generic github-secrets \
  --from-literal=token=ghp_...

# Deploy
kubectl apply -f deployment.yaml

# Check status
kubectl get pods
kubectl logs -f deployment/code-reviewer
```

## AWS ECS/Fargate

### Task Definition

```json
{
  "family": "code-reviewer",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "code-reviewer",
      "image": "your-account.dkr.ecr.us-east-1.amazonaws.com/code-reviewer:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "GITHUB_OWNER",
          "value": "your-org"
        },
        {
          "name": "GITHUB_REPO",
          "value": "your-repo"
        },
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        }
      ],
      "secrets": [
        {
          "name": "GITHUB_TOKEN",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789:secret:github-token"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/code-reviewer",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 5
      }
    }
  ]
}
```

### CloudFormation Template

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: Code Reviewer ECS Fargate Deployment

Parameters:
  GithubToken:
    Type: String
    NoEcho: true

Resources:
  EcsCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: code-reviewer-cluster

  TaskRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: ecs-tasks.amazonaws.com
            Action: 'sts:AssumeRole'

  TaskExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: ecs-tasks.amazonaws.com
            Action: 'sts:AssumeRole'
      ManagedPolicyArns:
        - 'arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy'

  Service:
    Type: AWS::ECS::Service
    Properties:
      Cluster: !Ref EcsCluster
      TaskDefinition: !Ref TaskDefinition
      DesiredCount: 2
      LaunchType: FARGATE

  TaskDefinition:
    Type: AWS::ECS::TaskDefinition
    Properties:
      Family: code-reviewer
      NetworkMode: awsvpc
      RequiresCompatibilities: [FARGATE]
      Cpu: 256
      Memory: 512
      TaskRoleArn: !GetAtt TaskRole.Arn
      ExecutionRoleArn: !GetAtt TaskExecutionRole.Arn
      ContainerDefinitions:
        - Name: code-reviewer
          Image: your-account.dkr.ecr.us-east-1.amazonaws.com/code-reviewer:latest
          PortMappings:
            - ContainerPort: 8000
          Environment:
            - Name: GITHUB_TOKEN
              Value: !Ref GithubToken
```

## Heroku Deployment

### Procfile

```
web: python -m code_reviewer.main
```

### Build Script

```bash
# Create buildpack configuration
heroku buildpacks:add heroku/python

# Create app
heroku apps:create code-reviewer

# Set environment variables
heroku config:set GITHUB_TOKEN=ghp_...
heroku config:set GITHUB_OWNER=your-org
heroku config:set GITHUB_REPO=your-repo

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

## GitHub Actions Workflow

```yaml
name: Deploy Code Reviewer

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: |
        docker build -t code-reviewer:${{ github.sha }} .
        docker tag code-reviewer:${{ github.sha }} code-reviewer:latest
    
    - name: Push to registry
      run: |
        echo ${{ secrets.REGISTRY_PASSWORD }} | docker login -u ${{ secrets.REGISTRY_USER }} --password-stdin
        docker push code-reviewer:${{ github.sha }}
        docker push code-reviewer:latest
    
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/code-reviewer \
          code-reviewer=code-reviewer:${{ github.sha }} \
          --record
```

## Environment Variables

Required:
```env
GITHUB_TOKEN=ghp_...           # GitHub API token
GITHUB_OWNER=your-org          # Repository owner
GITHUB_REPO=your-repo          # Repository name
```

Optional:
```env
LOG_LEVEL=INFO                 # DEBUG, INFO, WARNING, ERROR
USE_LLM_LOGIC=false            # Enable LLM-based Logic agent
USE_LLM_SECURITY=false         # Enable LLM-based Security agent
ANTHROPIC_API_KEY=sk-ant-...   # Claude API key (if using LLM)
OPENAI_API_KEY=sk-...          # OpenAI API key (if using LLM)
REDIS_URL=redis://...          # Redis for caching/state
```

## GitHub Webhook Setup

1. Go to repository Settings → Webhooks
2. Click "Add webhook"
3. **Payload URL**: `https://your-domain.com/webhook/github`
4. **Content type**: `application/json`
5. **Events**: Select "Pull requests"
6. **Active**: Check this option
7. Click "Add webhook"

GitHub will send POST requests when:
- PR opened
- PR commits updated
- PR reopened

## Monitoring

### CloudWatch (AWS)

```python
# In logger.py
import watchtower

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        watchtower.CloudWatchLogHandler()
    ]
)
```

### DataDog

```python
from ddtrace import tracer

@tracer.wrap("review.complete")
async def review_pr(request):
    # Metrics are auto-tracked
    pass
```

### Prometheus

```python
from prometheus_client import Counter, Histogram

review_counter = Counter('reviews_total', 'Total reviews', ['status'])
review_duration = Histogram('review_duration_seconds', 'Review duration')

with review_duration.time():
    await coordinator.review_pr(state)
```

## Health Checks

The `/health` endpoint returns:
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

Use this for:
- Kubernetes liveness/readiness probes
- Load balancer health checks
- Docker HEALTHCHECK
- Application Performance Monitoring (APM)

## Performance Tuning

### Scaling Horizontally
- Run multiple instances behind load balancer
- Use Redis for shared state
- Implement request queuing

### Caching
- Cache agent analysis results
- Store findings in Redis
- Implement TTL-based invalidation

### Database Optimization
- Index by `pr_number`
- Partition by date
- Archive old reviews

## Troubleshooting

### Pod keeps restarting
```bash
# Check logs
kubectl logs pod-name

# Check events
kubectl describe pod pod-name

# Check resource limits
kubectl top pod pod-name
```

### GitHub webhook not firing
1. Check webhook delivery in repo settings → Webhooks
2. Verify payload URL is accessible
3. Check authentication headers
4. Review CloudWatch logs for errors

### High token usage
1. Implement caching for identical diffs
2. Set token budgets in LLM agents
3. Monitor costs in Anthropic/OpenAI dashboard
4. Consider batch processing

---

Choose the deployment method that best fits your infrastructure!
