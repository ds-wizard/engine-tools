PYTHON = python

.PHONY: verify
verify:
	@echo "Trying to import: dsw.storage"
	$(PYTHON) -c 'import dsw.storage'

.PHONY: test
test:
	pytest -s tests
