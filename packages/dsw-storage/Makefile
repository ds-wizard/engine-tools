PIP = pip
PYTHON = python

.PHONY: verify
verify:
	@echo "Trying to import: dsw.storage"
	$(PYTHON) -c 'import dsw.storage'

.PHONY: local-deps
local-deps:
	@echo "Installing local dependencies"
	$(PIP) install ../dsw-config

.PHONY: test
test:
	@echo "No tests for this package"
