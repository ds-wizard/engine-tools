.PHONY: verify
verify:
	@echo "Executing command: dsw-tdk --version"
	@dsw-tdk --version

.PHONY: docker-image-name
docker-image-name:
	@echo "dsw-tdk"

.PHONY: test
test:
	pip install pytest
	pytest tests
