PIP = pip

.PHONY: verify
verify:
	@echo "Executing command: dsw-mailer --version"
	@dsw-mailer --version

.PHONY: local-deps
local-deps:
	@echo "Installing local dependencies"
	$(PIP) install ../dsw-config
	$(PIP) install ../dsw-database
	$(PIP) install ../dsw-command-queue
	$(PIP) install ../dsw-storage

.PHONY: docker-image-name
docker-image-name:
	@echo "mailer"

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
	$(MAKE) lambda-dependency PKG=dsw-mailer

	# 2. Fix postgres library for Lambda
	$(PIP) install --upgrade --target ./package --platform manylinux2014_x86_64 --implementation cp --only-binary=:all: "psycopg[binary]"
	cp package/psycopg_binary/_psycopg.cpython-311-x86_64-linux-gnu.so package/psycopg/_psycopg.so
	cp package/psycopg_binary/_psycopg.cpython-311-x86_64-linux-gnu.so package/psycopg_binary/_psycopg.so

	# 3. Package the ZIP and clean
	cd package && zip -r ../mailer-lambda.zip .
	rm -rf package

.PHONY: clean
clean:
	find . -type d -name __pycache__ -exec rm -r {} \; >/dev/null || true
	rm -rf package
	rm mailer-lambda.zip || true

.PHONY: pot
pot:
	pybabel extract --no-wrap --omit-header --ignore-dirs=.* \
		 --mapping templates/babel.registry.cfg --output-file=templates/locale/registry.plain.pot .
	pybabel extract --no-wrap --omit-header --ignore-dirs=.* \
		--mapping templates/babel.wizard.cfg --output-file=templates/locale/wizard.plain.pot .
	pybabel extract --no-wrap --omit-header --ignore-dirs=.* \
		--mapping templates/babel.cfg --output-file=templates/locale/default.plain.pot .
	cd templates/locale && \
		./make-header.sh "wizard-mail-templates:4.18.0" wizard.plain.pot > wizard.pot && rm wizard.plain.pot && \
		./make-header.sh "registry-mail-templates:4.18.0" registry.plain.pot > registry.pot && rm registry.plain.pot && \
		./make-header.sh "mail-templates:4.18.0" default.plain.pot > default.pot && rm default.plain.pot
