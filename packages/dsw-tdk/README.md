# dsw-tdk

[![User Guide](https://img.shields.io/badge/docs-User%20Guide-informational)](https://guide.ds-wizard.org)
[![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/ds-wizard/engine-tools)](https://github.com/ds-wizard/engine-tools/releases)
[![PyPI](https://img.shields.io/pypi/v/dsw-tdk)](https://pypi.org/project/dsw-tdk/)
[![Docker Pulls](https://img.shields.io/docker/pulls/datastewardshipwizard/dsw-tdk)](https://hub.docker.com/r/datastewardshipwizard/dsw-tdk)
[![LICENSE](https://img.shields.io/github/license/ds-wizard/engine-tools)](LICENSE)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/4975/badge)](https://bestpractices.coreinfrastructure.org/projects/4975)
[![Python Version](https://img.shields.io/badge/Python-%E2%89%A5%203.7-blue)](https://python.org)

*Template Development Kit for [Data Stewardship Wizard](https://ds-wizard.org)*

## Installation

### Python package

You can easily install this tool using [pip](https://pip.pypa.io/en/stable/) (from [PyPI](https://pypi.org/project/dsw-tdk/)):

```shell script
$ pip install dsw-tdk
```

Optionally, you can clone any version from this repository and install it directly:

```shell script
$ git clone https://github.com/ds-wizard/dsw-tdk.git
$ pip install -e .
```

We recommend using [virtual environments](https://docs.python.org/3/library/venv.html) to avoid clashes in dependencies with other projects.

### Dockerized tool

If you don't want to use Python directly on your machine, you can easily use Docker image with DSW TDK:

```
$ docker run datastewardshipwizard/dsw-tdk --help
$ docker run datastewardshipwizard/dsw-tdk:develop --help
```

See [datastewardshipwizard/dsw-tdk on Docker Hub](https://hub.docker.com/repository/docker/datastewardshipwizard/dsw-tdk) to check available tags.

## Usage

You can find out possibilities directly using `--help` flag:

```shell script
$ dsw-tdk --help
$ dsw-tdk put --help
```

For further information, visit our [documentation](https://docs.ds-wizard.org).

### Basic commands

-  `new` = create a new template project locally using interactive wizard
-  `list` = list templates available in configured DSW instance
-  `get` = download a template from DSW instance
-  `put` = upload a template to DSW instance (create or update)
-  `verify` = check the metadata of local template project
-  `package` = create a distribution ZIP package that is importable to DSW via web interface

### Environment variables

You can use the following environment variables to avoid repeating CLI options.

- `DSW_API` = URL of DSW API you want to use, e.g., https://api.demo.ds-wizard.org (notice that it is **not** the URL of client, you can find it out by clicking Help > About in DSW)
    - Used when `--api-server` not specified
- `DSW_USERNAME` = username (email address) that you use to login with your admin account
    - Used when `--username` not specified
- `DSW_PASSWORD` = corresponding password to login with your admin account
    - Used when `--password` not specified
  
 You can also use them in `.env` file which is automatically loaded from current directory or specify it using `--dot-env` option:
 
```shell script
$ ls -a
. .. .env my-other-file
$ dsw-tdk list
$ dsw-tdk --dot-env /path/to/my/.env list
```
 
### How to start

1.  Prepare your DSW instance and admin account (optionally, prepare `.env` file)
2.  Verify the connection by issuing `dsw-tdk list`
3.  Create a new template project `dsw-tdk new` or get existing `dsw-tdk get` (or re-use some local)
4.  Go to the template project and make edits you need to do
5.  Update template in DSW with `dsw-tdk put` (or continually with `dsw-tdk put --watch`)
6.  (or) Create a distribution ZIP package that is importable via DSW web interface with `dsw-tdk package`

### Verbosity

You can use `--quiet` and `--debug` flags to toggle less or more output messages:

```shell script
$ dsw-tdk --quiet list
$ dsw-tdk --debug list
```

## Requirements

-  [Python 3.8+](https://www.python.org/downloads/)
-  DSW instance with matching version (e.g. a local one using [Docker](https://github.com/ds-wizard/dsw-deployment-example))
-  Admin credentials (email+password) to the DSW instance

## Contributing

We welcome any form of feedback and contribution to this tool:

-  Report bugs or ask in case of uncertainty using [GitHub Issues](https://github.com/ds-wizard/dsw-tdk/issues).
-  Share ideas and feature requests using [DSW Ideas site](https://ideas.ds-wizard.org).
-  Submit enhancements using [Pull Requests](https://docs.github.com/en/free-pro-team@latest/github/collaborating-with-issues-and-pull-requests/about-pull-requests), just please make sure that you comply with used conventions.

For more information read [CONTRIBUTING](CONTRIBUTING.md).

## License

This project is licensed under the Apache 2 License - see the [LICENSE](LICENSE) file for more details.
