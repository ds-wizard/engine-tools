PIP = pip
PYTHON = python

.PHONY: verify
verify:
	@echo "Trying to import: dsw.command_queue"
	$(PYTHON) -c 'import dsw.command_queue'

.PHONY: local-deps
local-deps:
	@echo "Installing local dependencies"
	$(PIP) install ../dsw-config
	$(PIP) install ../dsw-database

.PHONY: test
test:
	@echo "No tests for this package"
