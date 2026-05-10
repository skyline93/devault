# 最小 Terraform（curl / null_resource）

不依赖第三方 DeVault provider：在 `apply` 时通过 **`local-exec`** 调用 **`curl`**，与 **OpenAPI** 一致。

## 用法

```bash
cd deploy/iac/terraform-minimal
terraform init
export TF_VAR_devault_api_base_url=http://127.0.0.1:8000
export TF_VAR_devault_api_token=changeme
export TF_VAR_agent_id=00000000-0000-4000-8000-000000000001
export TF_VAR_tenant_id=<uuid>
terraform apply
```

仅演示 **enrollment** 一步；池与策略可照 **`../examples/`** 与文档站 **`website/docs/guides/iac-bootstrap.md`** 扩展。
