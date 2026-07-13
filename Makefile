.PHONY: clean
clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find packages -type d -name 'build' -exec rm -rf {} +
	find packages -type d -name 'dist' -exec rm -rf {} +
	find packages -type d -name '*.egg-info' -exec rm -rf {} +

.PHONY: install
install:
	uv sync --all-packages --all-extras --dev --group test --group translations
	./scripts/build-info.sh

.PHONY: lock
lock:
	uv lock

.PHONY: upgrade
upgrade:
	uv lock --upgrade

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
