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

.PHONY: lint
lint:
	uv run ruff check

.PHONY: type-check
type-check:
	uv run ty check
