.PHONY: clean
clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find packages -type d -name 'build' -exec rm -rf {} +
	find packages -type d -name 'dist' -exec rm -rf {} +
	find packages -type d -name '*.egg-info' -exec rm -rf {} +

.PHONY: install
install:
	./scripts/prepare-dev.sh --clean
	./scripts/build-info.sh

.PHONY: dev-install
dev-install:
	pip install -r requirements.dev.txt

.PHONY: code-style
code-style:
	flake8 \
		--count
		--max-complexity=12
		--max-line-length=130
		--statistics \
		packages

.PHONY: lint
lint:
	pylint \
		--rcfile=.pylintrc.ini \
		--recursive y \
		--verbose \
		packages/*/dsw

.PHONY: spelling
spelling:
	cspell \
		--no-progress \
		--no-summary \
		--config .cspell/cspell.json \
		packages/**/*.py \
		packages/**/*.md \
		packages/**/*.json \
		packages/**/*.toml \
		packages/**/*.yml \
		packages/**/*.yaml

.PHONY: type-check
type-check:
	mypy \
		--install-types \
		--check-untyped-defs \
		--non-interactive \
		packages/*/dsw
