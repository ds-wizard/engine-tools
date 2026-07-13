PIP = uv pip

.PHONY: verify
verify:
	@echo "Executing command: dsw-data-seeder --version"
	@dsw-data-seeder --version

.PHONY: docker-image-name
docker-image-name:
	@echo "data-seeder"

.PHONY: test
test:
	@echo "No tests for this package"

.PHONY: lambda-deps
lambda-deps:
	uv export --frozen --no-dev --no-emit-workspace --no-hashes \
		--package dsw-data-seeder -o requirements.lambda.txt
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
	$(MAKE) lambda-vendor PKG=dsw-data-seeder

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
	cd package && zip -r ../data-seeder-lambda.zip .
	rm -rf package

.PHONY: clean
clean:
	find . -type d -name __pycache__ -exec rm -r {} \; >/dev/null || true
	rm -rf package
	rm data-seeder-lambda.zip || true
