# Tekton CI/CD Pipeline Quick Guide

## Overview

This project uses Tekton Pipelines for CI/CD on OpenShift. The pipeline automatically builds, tests, and deploys the application when code is pushed to GitHub.

## Pipeline Flow

```
                ┌── lint ──┐
git-clone ──────┤          ├── build → deploy → behave
                └── test ──┘
```

| Task | Description |
|------|-------------|
| git-clone | Clone repository from GitHub |
| lint | Run pylint code quality checks |
| test | Run pytest unit tests (parallel with lint) |
| build | Build container image with buildah |
| deploy | Deploy to OpenShift |
| behave | Run BDD integration tests |

## Directory Structure

```
.tekton/
├── pipeline.yaml          # Main CD pipeline definition
├── tasks.yaml             # Custom tasks (pylint, pytest-env, deploy-image, behave)
├── workspace.yaml         # PVC for pipeline workspace (1Gi)
└── events/
    ├── event_listener.yaml    # Listen for GitHub webhooks
    ├── trigger.yaml           # Connect binding and template
    ├── trigger_binding.yaml   # Extract data from webhook payload
    └── trigger_template.yaml  # Create PipelineRun from trigger

k8s/
├── deployment.yaml        # Application deployment
├── service.yaml           # ClusterIP service
├── route.yaml             # OpenShift route (external access)
├── ingress.yaml           # Kubernetes ingress (local K3d)
└── postgres/
    ├── secret.yaml        # Database credentials
    ├── service.yaml       # PostgreSQL service
    └── statefulset.yaml   # PostgreSQL StatefulSet
```

## Quick Setup

### 1. Deploy K8s Resources (First Time)

```bash
# Deploy database and secrets
oc apply -f k8s/postgres/

# Deploy service and route
oc apply -f k8s/service.yaml
oc apply -f k8s/route.yaml
```

### 2. Deploy Tekton Resources

```bash
# Deploy tasks, workspace, pipeline, and triggers
oc apply -f .tekton/tasks.yaml
oc apply -f .tekton/workspace.yaml
oc apply -f .tekton/pipeline.yaml
oc apply -f .tekton/events/

# Grant pipeline permissions
oc policy add-role-to-user edit system:serviceaccount:$(oc project -q):pipeline
```

### 3. Expose EventListener

```bash
oc expose service el-cd-listener
oc get route el-cd-listener
```

### 4. Configure GitHub Webhook

1. Go to **Settings** → **Webhooks** → **Add webhook**
2. **Payload URL**: Use the route URL from step 3
3. **Content type**: `application/json`
4. **Events**: Select `Just the push event`
5. Click **Add webhook**

### 5. Manual Pipeline Run (Optional)

```bash
tkn pipeline start cd-pipeline \
  -p GIT_REPO=https://github.com/CSCI-GA-2820-FA25-003/promotions \
  -p GIT_REF=master \
  -p IMAGE_NAME=promotions \
  -p IMAGE_TAG=latest \
  -w name=pipeline-workspace,claimName=pipeline-pvc \
  --showlog
```

Or use OpenShift Console: **Pipelines** → **cd-pipeline** → **Actions** → **Start**

## Verify Deployment

```bash
# Check pipeline runs
oc get pipelineruns

# Check pods
oc get pods

# Check route
oc get route
```

## Local Development (K3d)

```bash
# Create local cluster
make cluster

# Build and deploy
make build
make push
make deploy

# Cleanup
make cluster-rm
```

## Troubleshooting

### PVC Issues
```bash
oc delete pvc pipeline-pvc
oc apply -f .tekton/workspace.yaml
```

### View Pipeline Logs
```bash
tkn pipelinerun logs -f
```
