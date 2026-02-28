# Helm Deployment (EKS/Kubernetes)

## Install

```bash
helm upgrade --install aiops ./deploy/helm/aiops \
  --namespace aiops \
  --create-namespace \
  -f ./deploy/helm/aiops/values.yaml
```

## Notes

- Configure image repositories/tags in `values.yaml`.
- Route `/api/*` to backend and `/` to frontend via ingress.
- Backend and frontend have HPAs enabled for concurrent user scaling.
- Inject secrets using external secret manager where possible.

