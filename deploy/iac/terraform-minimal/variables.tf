variable "devault_api_base_url" {
  type        = string
  description = "e.g. http://127.0.0.1:8000 (no trailing slash)"
}

variable "devault_api_token" {
  type        = string
  sensitive   = true
  description = "Admin Bearer (DEVAULT_API_TOKEN or API key secret)"
}

variable "agent_id" {
  type = string
}

variable "tenant_id" {
  type = string
}
