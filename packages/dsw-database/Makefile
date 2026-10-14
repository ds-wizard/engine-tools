PYTHON = python

.PHONY: verify
verify:
	@echo "Trying to import: dsw.database"
	$(PYTHON) -c 'import dsw.database'

.PHONY: test
test:
	pytest -s tests
