PIP = pip

.PHONY: verify
verify:
	@echo "Executing command: dsw-data-seeder --version"
	@dsw-data-seeder --version

.PHONY: local-deps
local-deps:
	@echo "Installing local dependencies"
	$(PIP) install ../dsw-config
	$(PIP) install ../dsw-database
	$(PIP) install ../dsw-storage
	$(PIP) install ../dsw-command-queue

.PHONY: docker-image-name
docker-image-name:
	@echo "data-seeder"

.PHONY: test
test:
	@echo "No tests for this package"

.PHONE: lambda-package-requirements
lambda-package-requirements:
	$(PIP) install --upgrade --target ./package -r $(FILE)

.PHONE: lambda-dependency
lambda-dependency:
	$(MAKE) lambda-package-requirements FILE=../$(PKG)/requirements.txt
	cp -R ../$(PKG)/dsw ./package

.PHONY: lambda-package
lambda-package:
	$(MAKE) clean

	# 1. Install and copy DSW packages
	mkdir package
	$(MAKE) lambda-package-requirements FILE=../../requirements.txt
	$(MAKE) lambda-dependency PKG=dsw-command-queue
	$(MAKE) lambda-dependency PKG=dsw-config
	$(MAKE) lambda-dependency PKG=dsw-database
	$(MAKE) lambda-dependency PKG=dsw-storage
	$(MAKE) lambda-dependency PKG=dsw-data-seeder

	# 2. Fix postgres library for Lambda
	$(PIP) install --upgrade --target ./package --platform manylinux2014_x86_64 --implementation cp --only-binary=:all: "psycopg[binary]"
	cp package/psycopg_binary/_psycopg.cpython-311-x86_64-linux-gnu.so package/psycopg/_psycopg.so
	cp package/psycopg_binary/_psycopg.cpython-311-x86_64-linux-gnu.so package/psycopg_binary/_psycopg.so

	# 3. Package the ZIP and clean
	cd package && zip -r ../data-seeder-lambda.zip .
	rm -rf package

.PHONY: clean
clean:
	find . -type d -name __pycache__ -exec rm -r {} \; >/dev/null || true
	rm -rf package
	rm data-seeder-lambda.zip || true
