# Local image build / push (same Dockerfile as CI: deploy/Dockerfile).
# Examples:
#   make docker-build IMAGE=registry.cn-shenzhen.aliyuncs.com/greene/devault:latest-amd64
#   make docker-build-push IMAGE=registry.cn-shenzhen.aliyuncs.com/greene/devault:latest-amd64
#   make docker-buildx-push IMAGE=registry.cn-shenzhen.aliyuncs.com/greene/devault:latest
# Cross-build one arch with buildx load (optional):
#   make docker-build PLATFORMS=linux/arm64 IMAGE=...:latest-arm64

DOCKERFILE := deploy/Dockerfile
CONTEXT := .
# Default Docker Hub namespace (override for other registries).
IMAGE ?= glf9832/devault:latest
# Empty = plain `docker build` for the host. Set e.g. linux/arm64 for buildx --load (single platform only).
PLATFORMS ?=
# Used only by docker-buildx-push (manifest list).
PLATFORMS_MULTI ?= linux/amd64,linux/arm64

.PHONY: help docker-build docker-push docker-build-push docker-buildx-push

help:
	@echo "DeVault — image targets (registry-agnostic; set IMAGE to your full ref)"
	@echo ""
	@echo "  make docker-build [IMAGE=...] [PLATFORMS=linux/arm64]"
	@echo "      Build using $(DOCKERFILE). DOCKER_BUILDKIT=1. With PLATFORMS=, uses buildx --load (one platform)."
	@echo ""
	@echo "  make docker-push IMAGE=registry/namespace/name:tag"
	@echo "      Push an already-built tag (run docker login to your registry first)."
	@echo ""
	@echo "  make docker-build-push IMAGE=..."
	@echo "      docker-build then docker-push (single-arch unless PLATFORMS is set)."
	@echo ""
	@echo "  make docker-buildx-push IMAGE=..."
	@echo "      Multi-arch build and push (default PLATFORMS_MULTI=$(PLATFORMS_MULTI))."
	@echo ""
	@echo "Current default IMAGE=$(IMAGE)"

docker-build:
	@if [ -z "$(strip $(PLATFORMS))" ]; then DOCKER_BUILDKIT=1 docker build -f $(DOCKERFILE) -t $(IMAGE) $(CONTEXT); else docker buildx build --platform $(PLATFORMS) -f $(DOCKERFILE) -t $(IMAGE) --load $(CONTEXT); fi

docker-push:
	docker push $(IMAGE)

docker-build-push: docker-build docker-push

docker-buildx-push:
	docker buildx build --platform $(PLATFORMS_MULTI) -f $(DOCKERFILE) -t $(IMAGE) --push $(CONTEXT)
