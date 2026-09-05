# Contributing

When contributing to this repository, please first discuss the change you wish to make via issue, email, or any other
method with the owners of this repository before making a change.

## Development and Code Style

- Set up the development environment with `make install` (creates the [uv](https://docs.astral.sh/uv/) workspace
  environment via `uv sync` and generates the build info)
- Dependencies are managed exclusively through `uv`: declare them in the relevant `pyproject.toml` and run
  `make lock` (or `make upgrade` to bump within constraints). `uv.lock` is the single source of truth — there are
  no hand-maintained `requirements.txt` files
- Use Python version conforming the specification in `pyproject.toml`
- Use type annotations and verify it with `mypy`
- Code should comply with `PEP8` and additional checks made by `flake8` (see CI)

### Monorepo Structure

* `packages/` = all Python packages that are part of this monorepo
  * `<package>/` = package directory, should start with `dsw-` prefix
    * `dsw/` = namespace module common across all packages
    * `...` = other files (see *Adding New Package*)
* `scripts/` = scripts for development and building packages

### Adding New Package

A new package can be created by adding a subdirectory of `packages/`:

* All packages should use the namespace module `dsw` (without `__init__.py` according to 
  [PEP420](https://peps.python.org/pep-0420/)).
* Add basic files related to OSS: `CHANGELOG.md`, `LICENSE`, `README.md`
* Add the package's `pyproject.toml` using the `uv_build` backend and declare runtime dependencies under
  `[project.dependencies]` (see existing packages for reference); do not add `requirements.txt` or `setup.py`
* Register the package in the root `pyproject.toml`: it is picked up by `[tool.uv.workspace]` members (`packages/*`),
  and if other packages depend on it, add it to `[tool.uv.sources]` as `{ workspace = true }`; then run `make lock`
* Add `Makefile` (see existing packages for reference)
* Adjust CI workflows under `.github/` to build, test, and eventually release the package correctly
* Add link to the root `README.md`

## Pull Request Process

1. Ensure any unnecessary install or build dependencies and other generated files are removed (adjust `.gitignore` or `.dockerignore` if necessary).
2. Explain the changes and update in the Pull Request message. If it affects our [User Guide](https://guide.ds-wizard.org), 
   state explicitly how it should be changed.
3. Be ready to communicate about the Pull Request and make changes if required by reviewers.
4. The Pull Request may be merged once it passes the review and automatic checks.

## Git Workflow

`main` is the only long-lived branch. There is no `develop`, and there are no `release/*` or `hotfix/*` branches:
a release is a Git-tag on a commit of `main`, and a hotfix is an ordinary change on `main` that gets tagged.

* __main__ is the single line of development and the base of every branch. It is protected on GitHub — it cannot be
  force-pushed, and all checks must pass before a change lands.
* Every change is developed on a short-lived branch off `main`, named for what it does (`feature/*`, `fix/*`,
  `chore/*`). Maintainers typically use a [git worktree](https://git-scm.com/docs/git-worktree) per branch so several
  can be in flight at once.
* Before merging, rebase the branch onto the current `main` and merge it with `git merge --ff-only`, so the history
  stays linear and every commit on `main` is a commit CI has seen in its final form.
* Delete the branch once it has landed.

Please note, that for tasks from [our Jira](https://ds-wizard.atlassian.net/projects/DSW/issues), we use such
as `[DSW-XXX]` identifying the project and task number.

## Release Management

For the release management we use:

* [Semantic versioning](https://semver.org)
* Release Candidates - X.Y.Z-rc.N should be created if don’t expect any problems (in that case use alpha or beta), and
  make a walkthrough to verify its functionality according to the manuals finally - it also verifies that the
  documentation is up to date with the new version.
* Docker Hub image - in case of release, Docker image with the same tag will be created automatically.
* Compatibility in DSW - the matching major and minor version of DSW components must be compatible.

The changes must be captured in our [User Guide](https://guide.ds-wizard.org).

### Release Steps

Releases are cut directly on `main` — there is no release branch to merge back.

* Update `CHANGELOG.md` files for the release. Their `[Unreleased]` link compares the previous release tag against
  `main` (`/../../compare/vX.Y.Z...main`), so bump it to the tag being released.
* Commit a version bump to semver `X.Y.Zrc1` (`python scripts/version.py X.Y.Zrc1`) and Git-tag that commit with
  `vX.Y.Z-rc.1`.
* Test the RC version (it will not be published via PyPI unless GitHub pre-release is published).
* If needed, add fix and create a new RC revision.
* When ready, commit a version bump to semver `X.Y.Z`, wait for the `Pipeline` workflow to be green for that commit,
  create the `vX.Y.Z` Git-tag on it, and publish the GitHub release (that is what publishes to PyPI).

### Post-Release Steps

* After the release, add a commit on `main` that bumps the version to the next one with the dev-suffix: `X.Y.Z.dev1`.
* When needed, the number after `dev` can be increased during the development cycle.

### Version Number in Files

Version numbers (according to [PEP440](https://peps.python.org/pep-0440/)) are present in all packages inside
`pyproject.toml` files. Eventually, packages may contain `consts.py` module with a constant with the version.
The local dependencies must use the same package version.

The Git-tag version is automatically generated in `build_info.py` module of each package via the script from 
`scripts/build-info.sh`. The version of Git-tag should match the version of packages. All packages must keep 
consistent versioning!
