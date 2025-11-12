## Deploying to Kubernetes with K3D

This guide provides instructions for deploying the Promotions microservice to a local K3D/K3S cluster.

### Prerequisites

*   Docker
*   kubectl
*   k3d

### 1. Cluster Setup

Create a local K3D cluster with a load balancer and a local registry:

```bash
make cluster
```

This command creates a cluster named `nyu-devops` with 2 agent nodes and maps the host port `8080` to the load balancer's port `80`.

To remove the cluster:

```bash
make cluster-rm
```

### 2. Build and Push the Image

Build the Docker image and push it to the local registry:

```bash
make build
make push
```

The `make push` command will attempt to push to the local registry and fall back to importing the image directly into the k3d cluster if the registry is not reachable.

### 3. Deploy the Application

Deploy the PostgreSQL database and the Promotions service to the cluster:

```bash
kubectl apply -f k8s/postgres/statefulset.yaml
kubectl apply -f k8s/postgres/service.yaml
kubectl apply -f k8s/secrets/promotions-db.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
```

### 4. Validate the Deployment

Wait for the pods to be ready:

```bash
kubectl get pods -l app=promotions -w
```

Once the pods are ready, you can validate the deployment by accessing the `/health` endpoint:

```bash
curl -i -H "Host: promotions.local" http://localhost:8080/health
```

You should see an `HTTP/1.1 200 OK` response.

### 5. Troubleshooting

*   **Postgres CrashLoopBackOff**: If the PostgreSQL pod is not starting correctly, you may need to delete the Persistent Volume Claim (PVC) and restart the pod.
*   **Ingress 404**: Ensure you are using the `Host` header in your `curl` command or have added `127.0.0.1 promotions.local` to your `/etc/hosts` file.
*   **App cannot reach DB**: Check the logs of the `promotions-deployment` pod for any database connection errors.

### 6. Cleanup

To remove the application from the cluster:

```bash
kubectl delete -f k8s/ingress.yaml
kubectl delete -f k8s/service.yaml
kubectl delete -f k8s/deployment.yaml
kubectl delete -f k8s/postgres/service.yaml
kubectl delete -f k8s/postgres/statefulset.yaml
kubectl delete -f k8s/secrets/promotions-db.yaml
```