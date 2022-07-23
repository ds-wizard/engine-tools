.PHONY: verify
verify:
	@echo "Executing command: dsw-document-worker --version"
	@dsw-document-worker --version

.PHONY: local-deps
local-deps:
	@echo "Installing local dependencies"
	pip install ../dsw-config
	pip install ../dsw-database
	pip install ../dsw-storage
	pip install ../dsw-command-queue

.PHONY: docker-image-name
docker-image-name:
	@echo "document-worker"

.PHONY: test
test:
	@echo "No tests for this package"
