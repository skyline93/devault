# Helm

- **Chart 路径**：[`devault/`](./devault/)（`helm install … deploy/helm/devault`）
- **文档**：文档站 [Kubernetes（Helm）](../../website/docs/install/kubernetes-helm.md)

在**仓库根目录**执行：

```bash
docker build -f deploy/Dockerfile -t devault:latest .
helm lint deploy/helm/devault
helm template demo deploy/helm/devault
helm template demo-mon deploy/helm/devault --set monitoring.enabled=true >/dev/null
```

内置告警规则副本：`deploy/helm/devault/prometheus-alerts.yml`（与 `deploy/prometheus/alerts.yml` 同步维护）。

## 企业控制台（Ant Design Pro）同域反代（十五-08）

Chart 当前以 **api** 为主；**`console/dist`** 静态资源建议由 **Ingress 或前置 Nginx** 与 **`/api` → 控制面 Service** 同域发布。示例配置见 **`deploy/nginx/console-spa.conf`**（Compose 可选服务 **`console`**，`--profile with-console`）。
