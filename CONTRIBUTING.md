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
- Use type annotations and verify them with `ty`
- Code is linted with `ruff`; run `make check` before opening a pull request — it
  runs what CI runs (`ruff`, `ty`, `cspell`)

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
* Add the package's `pyproject.toml` using the `hatchling` backend with `uv-dynamic-versioning` (see existing
  packages for reference); do not add `requirements.txt`, `setup.py` or `MANIFEST.in`. It must declare
  `dynamic = ["version"]`, `[tool.hatch.version] source = "uv-dynamic-versioning"`, and
  `[tool.hatch.build.targets.wheel] packages = ["dsw"]` with `artifacts = ["dsw/*/build_info.py"]`.
  Declare third-party runtime dependencies under `[project.dependencies]` — but if the package depends on another
  `dsw-*` package, add `"dependencies"` to `dynamic` and move the whole list into
  `[tool.hatch.metadata.hooks.uv-dynamic-versioning]`, writing the sibling as `dsw-other=={{ version }}` so it
  stays in lockstep
* Register the package in the root `pyproject.toml`: it is picked up by `[tool.uv.workspace]` members (`packages/*`),
  and if other packages depend on it, add it to `[tool.uv.sources]` as `{ workspace = true }`; then run `make lock`
* Add `Makefile` (see existing packages for reference)
* Adjust CI workflows under `.github/` to build, test, and eventually release the package correctly
* If the package ships a Docker image, add its `README.md` to the dependency-manifest layer of **every** Dockerfile
  (`uv export` builds each member's metadata, and hatchling validates `project.readme` while doing so)
* Add link to the root `README.md`

## Pull Request Process

1. Ensure any unnecessary install or build dependencies and other generated files are removed (adjust `.gitignore` or `.dockerignore` if necessary).
2. Explain the changes and update in the Pull Request message. If it affects our [User Guide](https://guide.ds-wizard.org), 
   state explicitly how it should be changed.
3. Be ready to communicate about the Pull Request and make changes if required by reviewers.
4. The Pull Request may be merged once it passes the review and automatic checks.

## Git Workflow

`main` is the primary development branch and there is no `develop` or `release/*` branch: a release is a Git-tag
on a commit of `main`. The only other long-lived branches are the maintenance branches `hotfix/X.Y`, one per
supported minor line, described under [Hotfixes](#hotfixes) below.

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
* Git-tag the commit you are releasing with `vX.Y.Z-rc.1`. There is no version bump to commit — the version is
  derived from the tag.
* Test the RC version (it will not be published via PyPI unless GitHub pre-release is published).
* If needed, add fix and create a new RC revision.
* When ready, wait for the `Pipeline` workflow to be green for the commit, create the `vX.Y.Z` Git-tag **on that
  exact commit**, and publish the GitHub release (that is what publishes to PyPI).

### Post-Release Steps

No version bump. Commits after the tag automatically build as `X.Y.Z.post<N>.dev0+<sha>`, so there is no dev-suffix
to make and nothing to keep in sync.

For a new minor line, create its maintenance branch from the released commit: `git branch hotfix/X.Y vX.Y.0`.

### Hotfixes

Each supported minor release has one maintenance branch `hotfix/X.Y`, created from its `vX.Y.0` tag and holding a
cumulative sequence of fixes for that line. Several may coexist — `hotfix/1.3` and `hotfix/1.4` each take only the
fixes relevant to them and carry their own patch tags.

* Commit the fix on `hotfix/X.Y`, then tag that commit with the next patch version — `vX.Y.1`, `vX.Y.2`, and so on.
* Apply the same logical fix at the current tip of `main` through a reviewed Pull Request, normally a cherry-pick.
  The two commits are the same fix and need not share a hash.
* **Do not rebase `hotfix/X.Y` and do not merge it into `main`.** It stays a simple history of the released line,
  with the patch tags identifying exactly what was deployed.

If a maintenance branch is deleted, recreate it from its highest `vX.Y.Z` patch tag, or from `vX.Y.0` if no patch
has been released yet.

Note that `latest` on Docker Hub follows `latest=auto`, which does not compare versions — a patch tag on an older
line moves it, and it must be repointed by hand afterwards.

### Version Number in Files

**There is no version number stored anywhere in this repository.** Every version (according to
[PEP440](https://peps.python.org/pep-0440/)) is derived from the git tag at build time by
[uv-dynamic-versioning](https://github.com/ninoseki/uv-dynamic-versioning): the packages declare
`dynamic = ["version"]`, and the lockstep `dsw-*` dependencies between them are rendered as `=={{ version }}` by the
hatch metadata hook, so they can never drift apart.

Two consequences worth knowing:

* Anything that builds a distribution needs the tag to be reachable — CI jobs must check out with `fetch-depth: 0`.
  A shallow checkout does not fail; it quietly builds `0.0.0.post<N>.dev0+<sha>`. `scripts/check-release.py`
  guards the release path against exactly this.
* Docker builds cannot see the tag, because `.dockerignore` excludes `.git`. The version is passed in as the
  `PACKAGE_VERSION` build argument instead.

The Git-tag version is automatically generated in `build_info.py` module of each package via the script from 
`scripts/build-info.sh`. The version of Git-tag should match the version of packages. All packages must keep 
consistent versioning!
