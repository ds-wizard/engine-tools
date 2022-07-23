.PHONY: verify
verify:
	@echo "Executing command: dsw-data-seeder --version"
	@dsw-data-seeder --version

.PHONY: local-deps
local-deps:
	@echo "Installing local dependencies"
	pip install ../dsw-config
	pip install ../dsw-database
	pip install ../dsw-storage
	pip install ../dsw-command-queue

.PHONY: docker-image-name
docker-image-name:
	@echo "data-seeder"

.PHONY: test
test:
	@echo "No tests for this package"
