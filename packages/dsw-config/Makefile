PYTHON = python

.PHONY: verify
verify:
	@echo "Trying to import: dsw.config"
	$(PYTHON) -c 'import dsw.config'

.PHONY: test
test:
	pytest -s tests
