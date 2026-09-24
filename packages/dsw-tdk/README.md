# dsw-tdk

[![User Guide](https://img.shields.io/badge/docs-User%20Guide-informational)](https://guide.ds-wizard.org)
[![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/ds-wizard/engine-tools)](https://github.com/ds-wizard/engine-tools/releases)
[![PyPI](https://img.shields.io/pypi/v/dsw-tdk)](https://pypi.org/project/dsw-tdk/)
[![Docker Pulls](https://img.shields.io/docker/pulls/datastewardshipwizard/dsw-tdk)](https://hub.docker.com/r/datastewardshipwizard/dsw-tdk)
[![LICENSE](https://img.shields.io/github/license/ds-wizard/engine-tools)](LICENSE)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/4975/badge)](https://bestpractices.coreinfrastructure.org/projects/4975)
[![Python Version](https://img.shields.io/badge/Python-%E2%89%A5%203.12-blue)](https://python.org)

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
-  `pot` = create a POT file with translatable strings of the local template project
-  `render` = render a document from the local template project and a document context (no DSW instance needed)

### Rendering documents locally

`render` uses the same engine as the DSW document worker ([dsw-templating](../dsw-templating)). You need a document context as a JSON file:

```shell script
$ dsw-tdk render --context context.json --format "HTML Document" --output document.html
$ dsw-tdk render -c context.json -F "PDF Document" --po cs.po --project-files ./files
```

- `--format` accepts the UUID or name of a format (it can be omitted if the template has only one)
- `--po` renders with translations from a PO file (e.g. a translated `dsw-tdk pot` output); the language is taken from `document.language` of the context unless `--language` is given
- `--project-files` is a directory with files uploaded to the project, named by their UUID or file name
- Only files selected by `_tdk.files` are available to the rendering, as on the server
- The context is completed as the document worker does it with its default configuration: `config` gets the service name and URL of the Data Stewardship Wizard and fallbacks for missing branding (app title, colors, logo), and `extras` requested by the format but missing in the context are rendered as for a document without a project (with a warning)
- The worker's defaults can be overridden with `-D NAME=VALUE` (repeatable), named as in the `documentContext` section of the document worker configuration, or with its environment variables (also in `.env`); the option wins over the environment:

```shell script
$ dsw-tdk render -c context.json -F "HTML Document" -D "serviceName=FAIR Wizard" -D serviceUrl=https://fair-wizard.com
$ echo 'DOCUMENT_CONTEXT_SERVICE_NAME=FAIR Wizard' >> .env
```

| Name | Environment variable | Default |
|---|---|---|
| `serviceName` | `DOCUMENT_CONTEXT_SERVICE_NAME` | `Data Stewardship Wizard` |
| `serviceNameShort` | `DOCUMENT_CONTEXT_SERVICE_NAME_SHORT` | `DSW` |
| `serviceUrl` | `DOCUMENT_CONTEXT_SERVICE_URL` | `https://ds-wizard.org` |
| `serviceDomainName` | `DOCUMENT_CONTEXT_SERVICE_DOMAIN_NAME` | `ds-wizard.org` |
| `defaultPrimaryColor` | `DOCUMENT_CONTEXT_DEFAULT_PRIMARY_COLOR` | `#0033aa` |
| `defaultIllustrationsColor` | `DOCUMENT_CONTEXT_DEFAULT_ILLUSTRATIONS_COLOR` | `#0033aa` |
| `defaultLogoUrl` | `DOCUMENT_CONTEXT_DEFAULT_LOGO_URL` | `{{clientUrl}}/assets/logo.svg` |
| `defaultAppTitle` | `DOCUMENT_CONTEXT_DEFAULT_APP_TITLE` | `DS Wizard` |
| `defaultAppTitleShort` | `DOCUMENT_CONTEXT_DEFAULT_APP_TITLE_SHORT` | `DS Wizard` |

The `service*` values are always set; the `default*` ones apply only where the context has no value.
- Steps `weasyprint`, `excel` and `rdflib-convert`, the `requests` global and the `pandoc-docx-pagebreakpy` Pandoc filter need optional dependencies: `pip install 'dsw-tdk[all]'`; WeasyPrint also needs [Pango](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation) and the `pandoc` step needs [pandoc](https://pandoc.org) installed
- The `docx-*.lua` Pandoc filters of the document worker are always available; `--pandoc-filters DIR` adds more (searched first) and `--pandoc-templates DIR` provides templates for the `template` option of the `pandoc` step (or `PANDOC_FILTERS` / `PANDOC_TEMPLATES`, as for the worker)
- The `secrets` and `requests` globals exist only when configured for the template on the server; locally, `--secret NAME=VALUE` (repeatable) provides `secrets` and `--allow-requests` provides `requests`

### Environment variables

You can use the following environment variables to avoid repeating CLI options.

- `DSW_API_URL` = URL of DSW API you want to use, e.g., https://api.demo.ds-wizard.org (notice that it is **not** the URL of client, you can find it out by clicking Help > About in DSW)
    - Used when `--api-url` not specified
- `DSW_API_KEY` = API Key of the user authorized to manage document templates
    - Used when `--api-key` not specified
  
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

-  [Python 3.12+](https://www.python.org/downloads/)
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
