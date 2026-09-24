# Data Stewardship Wizard: Templating

[![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/ds-wizard/engine-tools)](https://github.com/ds-wizard/engine-tools/releases)
[![PyPI](https://img.shields.io/pypi/v/dsw-templating)](https://pypi.org/project/dsw-templating/)
[![LICENSE](https://img.shields.io/github/license/ds-wizard/engine-tools)](LICENSE)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/4975/badge)](https://bestpractices.coreinfrastructure.org/projects/4975)
[![Python Version](https://img.shields.io/badge/Python-%E2%89%A5%203.12-blue)](https://python.org)

*Rendering of Data Stewardship Wizard document templates*

The engine behind the [document worker](../dsw-document-worker): it renders a document from a
document template on disk and a document context, with no database, storage or queue behind it.

## Installation

```bash
pip install dsw-templating
pip install 'dsw-templating[all]'  # every optional step dependency
```

| Extra | Needed for |
|---|---|
| `pdf` | `weasyprint` step (WeasyPrint, needs Pango installed) |
| `rdf` | `rdflib-convert` step and the `rdflib` global in Jinja templates |
| `excel` | `excel` step (XlsxWriter) |
| `docx` | the `pandoc-docx-pagebreakpy` Pandoc filter command (panflute) |
| `http` | `requests` global in Jinja templates (Requests) |

A step whose extra is missing raises `MissingExtraError` ("install dsw-templating[pdf]") when it
is used. The `pandoc` step needs the [pandoc](https://pandoc.org) executable.

## Usage

```python
import json
import pathlib

from dsw.templating import RenderContext, RenderSettings, Template

template = Template.from_directory(pathlib.Path('my-template'), settings=RenderSettings())
context = json.loads(pathlib.Path('context.json').read_text())
document = template.render('d3e98eb6-344d-481f-8e37-6a67b6cd1ad2', context,
                           render_ctx=RenderContext.null(language='en'))
document.store('document')  # document.<extension>
```

Everything the rendering depends on is passed in explicitly:

| Input | Purpose |
|---|---|
| `Template(template_dir=..., formats=..., assets=...)` | Template files on disk and the formats of `template.json` (`from_directory` reads both) |
| `RenderSettings` | URL security policy (`SecuritySettings`), Pandoc command, filters and timeout (`PandocSettings`), per-template `secrets` and HTTP `requests` (`TemplateSettings`) |
| `RenderContext` | Translations (`gettext`), language and locale of the document |
| `ProjectFileResolver` | Files uploaded to the project (`assets(file)` in templates); none by default |
| `plugins` | A pluggy manager; `create_manager()` loads plugins of the `dsw_templating_plugins` entry point |

Plugins implement the hooks of `dsw.templating.plugins.specs` (marked with
`dsw.templating.hookimpl`); steps they provide are registered with `register_plugin_steps(pm)`.

`dsw.templating.pot` extracts translatable messages of Jinja files into a POT file, and
`enrich_context_config(context, ContextDefaults())` adds to `ctx.config` what the document worker
adds (service information and fallbacks for missing branding).

## Documentation for template developers

* [Document Context](./support/DocumentContext.md)
* [Jinja Filters](./support/JinjaFilters.md)
* [Jinja Tests](./support/JinjaTests.md)
* [Translations](./support/Translations.md)
* Steps: [archive](./support/steps/archive.md), [enrich-docx](./support/steps/enrich-docx.md),
  [excel](./support/steps/excel.md), [jinja](./support/steps/jinja.md), [json](./support/steps/json.md),
  [pandoc](./support/steps/pandoc.md), [rdflib-convert](./support/steps/rdflib-convert.md),
  [weasyprint](./support/steps/weasyprint.md)

## License

This project is licensed under the Apache License v2.0 - see the
[LICENSE](LICENSE) file for more details.
