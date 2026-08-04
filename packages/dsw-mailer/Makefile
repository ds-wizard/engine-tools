PIP = uv pip
VERSION = 4.33.0

.PHONY: verify
verify:
	@echo "Executing command: dsw-mailer --version"
	@dsw-mailer --version

.PHONY: docker-image-name
docker-image-name:
	@echo "mailer"

.PHONY: test
test:
	@echo "No tests for this package"

.PHONY: lambda-deps
lambda-deps:
	uv export --frozen --no-dev --no-emit-workspace --no-hashes \
		--package dsw-mailer -o requirements.lambda.txt
	$(PIP) install --upgrade --target ./package --no-cache -r requirements.lambda.txt
	rm -f requirements.lambda.txt

.PHONY: lambda-vendor
lambda-vendor:
	cp -R ../$(PKG)/dsw ./package

.PHONY: lambda-package
lambda-package:
	$(MAKE) clean

	# 1. Install third-party dependencies (resolved from uv.lock)
	mkdir package
	$(MAKE) lambda-deps

	# 2. Vendor DSW package sources
	$(MAKE) lambda-vendor PKG=dsw-command-queue
	$(MAKE) lambda-vendor PKG=dsw-config
	$(MAKE) lambda-vendor PKG=dsw-database
	$(MAKE) lambda-vendor PKG=dsw-storage
	$(MAKE) lambda-vendor PKG=dsw-mailer

	# 3. Fix postgres library for Lambda
	$(PIP) install --upgrade --target ./package --python-platform x86_64-manylinux2014 --only-binary :all: "psycopg[binary]"
	cp package/psycopg_binary/_psycopg.cpython-314-x86_64-linux-gnu.so package/psycopg/_psycopg.so
	cp package/psycopg_binary/_psycopg.cpython-314-x86_64-linux-gnu.so package/psycopg_binary/_psycopg.so

	# 4. Clean up unnecessary files
	find package -type d -name "tests" -exec rm -rf {} + || true
	find package -type d -name "__pycache__" -exec rm -rf {} + || true
	find package -type d -name "*.dist-info" -exec rm -rf {} + || true
	find package -type d -name "*.egg-info" -exec rm -rf {} + || true
	find package -type f -name "*.pyc" -delete || true
	find package -type f -name "*.pyo" -delete || true
	find package -type f -name "*.so" -exec strip --strip-debug {} + || true

	# 5. Package the ZIP and clean
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
		./make-header.sh "wizard-mail-templates:${VERSION}" wizard.plain.pot > wizard.pot && rm wizard.plain.pot && \
		./make-header.sh "registry-mail-templates:${VERSION}" registry.plain.pot > registry.pot && rm registry.plain.pot && \
		./make-header.sh "mail-templates:${VERSION}" default.plain.pot > default.pot && rm default.plain.pot
