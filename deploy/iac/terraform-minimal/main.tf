resource "null_resource" "agent_enrollment" {
  triggers = {
    agent_id   = var.agent_id
    tenant_id  = var.tenant_id
    api_base   = var.devault_api_base_url
    token_hash = sha256(var.devault_api_token)
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -euo pipefail
      curl -sfS -X PUT "${var.devault_api_base_url}/api/v1/agents/${var.agent_id}/enrollment" \
        -H "Authorization: Bearer ${var.devault_api_token}" \
        -H "Content-Type: application/json" \
        -d '{"allowed_tenant_ids":["${var.tenant_id}"]}'
    EOT
  }
}
