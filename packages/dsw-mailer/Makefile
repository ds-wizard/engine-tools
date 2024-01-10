.PHONY: verify
verify:
	@echo "Executing command: dsw-mailer --version"
	@dsw-mailer --version

.PHONY: local-deps
local-deps:
	@echo "Installing local dependencies"
	pip install ../dsw-config
	pip install ../dsw-database
	pip install ../dsw-command-queue

.PHONY: docker-image-name
docker-image-name:
	@echo "mailer"

.PHONY: test
test:
	@echo "No tests for this package"

.PHONE: install-python-requirements
install-python-requirements:
	python3.11 -m pip install --upgrade --target ./package -r $(FILE)

.PHONE: install-dependency
install-dependency:
	$(MAKE) install-python-requirements FILE=../$(MODULE)/requirements.txt
	cp -R ../$(MODULE)/dsw ./package

.PHONY: build-lambda-package
build-lambda-package:
	$(MAKE) clean

	# 1. Install and copy DSW packages
	mkdir package
	$(MAKE) install-python-requirements FILE=../../requirements.txt
	$(MAKE) install-dependency MODULE=dsw-command-queue
	$(MAKE) install-dependency MODULE=dsw-config
	$(MAKE) install-dependency MODULE=dsw-database
	$(MAKE) install-dependency MODULE=dsw-models
	$(MAKE) install-dependency MODULE=dsw-storage
	$(MAKE) install-dependency MODULE=dsw-mailer

	# 2. Fix postgres library for Lambda
	python3.11 -m pip install --upgrade --target ./package --platform manylinux2014_x86_64 --implementation cp --only-binary=:all: "psycopg[binary]"
	cp package/psycopg_binary/_psycopg.cpython-311-x86_64-linux-gnu.so package/psycopg/_psycopg.so
	cp package/psycopg_binary/_psycopg.cpython-311-x86_64-linux-gnu.so package/psycopg_binary/_psycopg.so

	# 3. Package the ZIP and clean
	cd package && zip -r ../mailer-lambda.zip .
	rm -rf package

.PHONY: clean
clean:
	rm -rf src/__pycache__
	rm -rf package
	rm mailer-lambda.zip || true
