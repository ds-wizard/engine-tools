.PHONY: verify
verify:
	@echo "Executing command: dsw-tdk --version"
	@dsw-tdk --version

.PHONY: local-deps
local-deps:
	@echo "There are no local dependencies"

.PHONY: docker-image-name
docker-image-name:
	@echo "dsw-tdk"

.PHONY: test
test:
	pip install pytest
	pytest tests
