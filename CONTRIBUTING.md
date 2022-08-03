# Contributing

When contributing to this repository, please first discuss the change you wish to make via issue, email, or any other
method with the owners of this repository before making a change.

## Development and Code Style

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
* Add Python package files: `pyproject.toml` ([setuptools](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html)),
  `requirements.txt`, and `setup.py` (see existing packages for reference)
* Add `Makefile` (see existing packages for reference)
* Adjust CI workflows under `.github/` to build, test, and eventually release the package correctly
* Add link to the root `README.md`

## Pull Request Process

1. Ensure any unnecessary install or build dependencies and other generated files are removed (adjust `.gitignore` or `.dockerignore` if necessary).
2. Explain the changes and update in the Pull Request message. If it affects our [User Guide](https://guide.ds-wizard.org), 
   state explicitly how it should be changed.
3. Be ready to communicate about the Pull Request and make changes if required by reviewers.
4. The Pull Request may be merged once it passes the review and automatic checks.

## Gitflow Workflow

We use the standard [Gitflow Workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow):

* __main__ branch is used only for releases (and eventually hotfixes), this branch is also protected on GitHub (pull
  requests with review and all checks must pass)
* __develop__ branch is used for development and as a base for following development branches of features, support
  stuff, and as a base for releases
* __feature/*__ (base develop, rebase-merged back to develop when done)
* __chore/*__ (like the feature but semantically different, not the feature but some chore, e.g., cleanup or update of
  Dockerfile)
* __fix/*__ (like the feature but semantically different, not something new but fix of a non-critical bug)
* __release/*__ (base develop, merged to main and develop when ready for release+tag)
* __hotfix/*__ (base main, merged to main and develop)

Please note, that for tasks from [our Jira](https://ds-wizard.atlassian.net/projects/DSW/issues), we use such
as `[DSW-XXX]` identifying the project and task number.

## Release Management

For the release management we use (aside from the [Gitflow Workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow)):

* [Semantic versioning](https://semver.org)
* Release Candidates - X.Y.Z-rc.N should be created if don’t expect any problems (in that case use alpha or beta), and
  make a walkthrough to verify its functionality according to the manuals finally - it also verifies that the
  documentation is up to date with the new version.
* Docker Hub image - in case of release, Docker image with the same tag will be created automatically.
* Compatibility in DSW - the matching major and minor version of DSW components must be compatible.

The changes must be captured in our [User Guide](https://guide.ds-wizard.org).

### Release Steps

* Update `CHANGELOG.md` files for the release.
* In the release/hotfix branch, commit a version bump to semver `X.Y.Zrc1` and Git-tag it with `vX.Y.Z-rc.1`.
* Test the RC version (it will not be published via PyPI unless GitHub pre-release is published).
* If needed, add fix and create a new RC revision.
* When ready, commit a version bump to semver `X.Y.Z`, merge it to `main` and `develop`, create `vX.Y.Z` Git-tag,
  and publish GitHub release (to publish via PyPI).

### Post-Release Steps

* After merging the release branch to develop, add a commit that bumps the version to the next one with the 
  dev-suffix: `X.Y.Z.dev1`.
* When needed, the number after `dev` can be increased during the development cycle.

### Version Number in Files

Version numbers (according to [PEP440](https://peps.python.org/pep-0440/)) are present in all packages inside
`pyproject.toml` files. Eventually, packages may contain `consts.py` module with a constant with the version.
The local dependencies must use the same package version.

The Git-tag version is automatically generated in `build_info.py` module of each package via the script from 
`scripts/build-info.sh`. The version of Git-tag should match the version of packages. All packages must keep 
consistent versioning!
