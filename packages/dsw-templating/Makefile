PYTHON = python

.PHONY: verify
verify:
	@echo "Trying to import: dsw.templating"
	$(PYTHON) -c 'import dsw.templating'

.PHONY: test
test:
	pytest -s tests
