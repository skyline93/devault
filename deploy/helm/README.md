# Helm

- **Chart 路径**：[`devault/`](./devault/)（`helm install … deploy/helm/devault`）
- **文档**：文档站 [Kubernetes（Helm）](../../website/docs/install/kubernetes-helm.md)

在**仓库根目录**执行：

```bash
docker build -f deploy/Dockerfile -t devault:latest .
helm lint deploy/helm/devault
helm template demo deploy/helm/devault
```
