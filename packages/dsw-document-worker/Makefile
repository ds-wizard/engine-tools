PIP = pip

.PHONY: verify
verify:
	@echo "Executing command: dsw-document-worker --version"
	@dsw-document-worker --version

.PHONY: local-deps
local-deps:
	@echo "Installing local dependencies"
	$(PIP) install ../dsw-config
	$(PIP) install ../dsw-database
	$(PIP) install ../dsw-storage
	$(PIP) install ../dsw-command-queue

.PHONY: docker-image-name
docker-image-name:
	@echo "document-worker"

.PHONY: test
test:
	@echo "No tests for this package"
