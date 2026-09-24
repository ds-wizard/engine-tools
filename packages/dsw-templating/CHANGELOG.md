# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Rendering engine of document templates extracted from `dsw-document-worker`: formats, steps,
  Jinja filters and tests, document context helpers, conversions (Pandoc, WeasyPrint, RDFLib,
  Excel), URL policy, HTTP requests from templates and POT file extraction
- `Template` built from a template directory and its format metadata (`Template.from_directory`
  reads `template.json`), rendered with explicit `RenderSettings`, `RenderContext` and
  `ProjectFileResolver` instead of the worker's configuration and services
- Optional extras `pdf`, `rdf`, `excel`, `docx`, `http` and `all`; a step whose extra is missing
  fails with `MissingExtraError` when it is used
- Pandoc filters shipped as package data (`settings.bundled_pandoc_filters`)
- `enrich_context_config` and `ContextDefaults`: the service information and branding fallbacks the document worker adds to `ctx.config`
- Plugins use the `dsw-templating` pluggy project and the `dsw_templating_plugins` entry point
- The `pandoc-docx-pagebreakpy` Pandoc filter is a command of this package (`docx` extra) instead of a separate addon installed only in the document worker image
