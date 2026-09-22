PYTHON = python

.PHONY: verify
verify:
	@echo "Trying to import: dsw.models"
	$(PYTHON) -c 'import dsw.models'

.PHONY: test
test:
	pytest -s tests
