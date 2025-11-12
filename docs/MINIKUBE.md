# Minikube Compatibility Notes

This appendix describes how to run the Promotions Service on **Minikube** instead of K3D. It covers image visibility, ingress differences, and fallback access methods.

> Target audience: developers using Minikube locally
> Goal: build an image discoverable by the cluster and access the app via **Ingress** (recommended) or **NodePort/port-forward**.

---

## Prerequisites

* Minikube v1.30+ with a Kubernetes version compatible with your manifests
* `kubectl` installed and pointed at your Minikube context
* (Optional) GNU Make if you use provided `make` targets
* Docker (or container runtime supported by Minikube)

---

## Quick Start (TL;DR)

```bash
# 0) Start Minikube and enable NGINX Ingress
minikube start
minikube addons enable ingress
kubectl wait -n ingress-nginx --for=condition=Ready pods \
  -l app.kubernetes.io/component=controller --timeout=120s

# 1) Make your image visible to Minikube (choose ONE approach below)
#    A) Build inside Minikube’s Docker
eval $(minikube -p minikube docker-env)
# If you have a Makefile build target:
make build
# Or plain Docker (example):
# docker build -t promotions:local .
# (Optional) Restore your shell environment after building:
unset DOCKER_TLS_VERIFY DOCKER_HOST DOCKER_CERT_PATH MINIKUBE_ACTIVE_DOCKERD

#    B) OR: Load an already-built local image into Minikube
# minikube image load promotions:local
# minikube image load cluster-registry:5000/promotions:1.0

#    C) OR: Retag and patch Deployment to use a tag you control (see details below)

# 2) Deploy manifests (same manifests as K3D)
kubectl apply -f k8s/postgres/statefulset.yaml
kubectl apply -f k8s/postgres/service.yaml
kubectl apply -f k8s/secrets/promotions-db.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# 3) Ingress for Minikube uses NGINX (not Traefik)
kubectl apply -f k8s/ingress.yaml
# Ensure ingress class is "nginx":
kubectl patch ingress promotions-ingress --type=merge -p '{"spec":{"ingressClassName":"nginx"}}'
# (If your manifest uses the legacy annotation instead, overwrite it:)
kubectl annotate ingress promotions-ingress kubernetes.io/ingress.class=nginx --overwrite

# 4) Add local DNS entry for host routing
echo "$(minikube ip) promotions.local" | sudo tee -a /etc/hosts

# 5) Verify
kubectl rollout status deploy/promotions-deployment
curl -i http://promotions.local/health      # Expect: HTTP/1.1 200 OK
```

---

## Differences vs K3D

| Topic                 | K3D (Course Default)         | Minikube (This Appendix)                           |
| --------------------- | ---------------------------- | -------------------------------------------------- |
| Ingress controller    | Traefik                      | NGINX (via `minikube addons enable ingress`)       |
| Ingress class         | `traefik`                    | `nginx` (patch/annotation may be required)         |
| Registry/image flow   | Push to K3D’s local registry | Build inside Minikube **or** `minikube image load` |
| Hostname resolution   | `/etc/hosts` → K3D LB IP     | `/etc/hosts` → `minikube ip`                       |
| LoadBalancer behavior | Real LB via K3D              | Requires `minikube tunnel` if you use LB services  |

---

## Making Images Visible to Minikube

Choose one of the following:

### A) Build inside Minikube’s Docker (recommended for simplicity)

```bash
eval $(minikube -p minikube docker-env)
# If Makefile exists:
make build
# Or:
# docker build -t promotions:local .
unset DOCKER_TLS_VERIFY DOCKER_HOST DOCKER_CERT_PATH MINIKUBE_ACTIVE_DOCKERD
```

**If you built as `promotions:local`,** ensure your Deployment uses that name:

```bash
kubectl set image deploy/promotions-deployment promotions=promotions:local
```

> Tip: Ensure `imagePullPolicy: IfNotPresent` in your Deployment to avoid unnecessary pulls.

### B) Load a prebuilt image into Minikube

```bash
# Example tags accepted (with or without registry prefixes)
minikube image load promotions:local
minikube image load cluster-registry:5000/promotions:1.0
```

### C) Retag and patch your Deployment image

```bash
# Retag locally (if needed)
# docker tag your/source:tag promotions:local

# Patch the running Deployment to your tag
kubectl set image deploy/promotions-deployment promotions=promotions:local
```

---

## Ingress on Minikube (NGINX)

Enable and wait for the controller:

```bash
minikube addons enable ingress
kubectl wait -n ingress-nginx --for=condition=Ready pods \
  -l app.kubernetes.io/component=controller --timeout=120s
```

Ensure your Ingress resource targets the **nginx** class:

```bash
kubectl patch ingress promotions-ingress --type=merge -p '{"spec":{"ingressClassName":"nginx"}}'
# or (legacy annotation)
kubectl annotate ingress promotions-ingress kubernetes.io/ingress.class=nginx --overwrite
```

Add an `/etc/hosts` entry mapping your Minikube IP to the host used in `ingress.yaml` (e.g., `promotions.local`):

```bash
echo "$(minikube ip) promotions.local" | sudo tee -a /etc/hosts
```

Verify:

```bash
curl -i http://promotions.local/health
curl -i http://promotions.local/promotions
```

> **Note:** You usually do **not** need `minikube tunnel` for NGINX Ingress. Run the tunnel only if you rely on `Service.type=LoadBalancer` elsewhere.

---

## Fallback Access Methods

### Fallback A: NodePort

```bash
kubectl patch svc promotions-service -p '{"spec":{"type":"NodePort"}}'
export NODE_PORT=$(kubectl get svc promotions-service -o jsonpath='{.spec.ports[0].nodePort}')
export NODE_IP=$(minikube ip)
curl -i "http://${NODE_IP}:${NODE_PORT}/health"
```

Or let Minikube print the URL:

```bash
minikube service promotions-service --url
```

### Fallback B: Local port-forward

```bash
kubectl port-forward svc/promotions-service 8080:80
curl -i http://127.0.0.1:8080/health
```

---

## Troubleshooting

* **`ImagePullBackOff` / `ErrImagePull`**

  * Confirm the image tag in the Deployment matches what you built/loaded.
  * Use `kubectl describe pod <pod>` to see which image is being requested.
  * Re-run **A** or **B** above and ensure `imagePullPolicy: IfNotPresent`.

* **Ingress returns 404 (default backend)**

  * Check that the **host** in your Ingress matches `/etc/hosts` (e.g., `promotions.local`).
  * Ensure the **ingress class** is `nginx` (patch/annotate as shown).
  * Verify the `Service` name/port in Ingress backend matches `promotions-service:80`.

* **Database not ready / app CrashLoop**

  * Confirm Postgres StatefulSet is Ready:

    ```bash
    kubectl get pods -l app=postgres
    kubectl logs statefulset/postgres
    ```
  * Ensure DB Secret (`k8s/secrets/promotions-db.yaml`) is applied and env vars match the app.

* **Cannot reach via host name**

  * Re-add hosts mapping: `echo "$(minikube ip) promotions.local" | sudo tee -a /etc/hosts`
  * Test by IP + NodePort to isolate DNS/hosts issues.

---

## Acceptance Checklist (copy/paste)

```bash
# Image is visible to the cluster
kubectl get pods -l app=promotions
kubectl describe pod -l app=promotions | egrep -i 'image:|reason|message'

# Ingress reachable (preferred)
curl -i http://promotions.local/health | head -n 1  # expect 200

# OR NodePort fallback
NODE_IP=$(minikube ip)
NODE_PORT=$(kubectl get svc promotions-service -o jsonpath='{.spec.ports[0].nodePort}')
curl -i "http://${NODE_IP}:${NODE_PORT}/health" | head -n 1  # expect 200

# OR port-forward fallback
kubectl port-forward svc/promotions-service 8080:80 &
sleep 2
curl -i http://127.0.0.1:8080/health | head -n 1      # expect 200
```

---

## Cleanup

```bash
kubectl delete -f k8s/ingress.yaml --ignore-not-found
kubectl delete -f k8s/service.yaml --ignore-not-found
kubectl delete -f k8s/deployment.yaml --ignore-not-found
kubectl delete -f k8s/secrets/promotions-db.yaml --ignore-not-found
kubectl delete -f k8s/postgres/statefulset.yaml --ignore-not-found
kubectl delete -f k8s/postgres/service.yaml --ignore-not-found

# Optional: stop/remove Minikube
minikube stop
# minikube delete
```

---

### Notes

* If your manifests explicitly set `ingressClassName: traefik`, change it to `nginx` for Minikube or use the `kubectl patch` shown above.
* If your K3D flow expects an internal registry (e.g., `cluster-registry:5000/...`), it still works on Minikube as long as you **build inside Minikube** or **load the image** with `minikube image load` using the same tag. Alternatively, retag to `promotions:local` and update the Deployment image.
