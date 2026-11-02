PYTHON = python

.PHONY: verify
verify:
	@echo "Trying to import: dsw.command_queue"
	$(PYTHON) -c 'import dsw.command_queue'

.PHONY: test
test:
	pytest -s tests
