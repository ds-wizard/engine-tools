.PHONY: verify
verify:
	@echo "Executing command: dsw-mailer --version"
	@dsw-mailer --version

.PHONY: local-deps
local-deps:
	@echo "Installing local dependencies"
	pip install ../dsw-config
	pip install ../dsw-database
	pip install ../dsw-command-queue

.PHONY: docker-image-name
docker-image-name:
	@echo "mailer"

.PHONY: test
test:
	@echo "No tests for this package"
