# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Support for Jinja policies

### Fixed

- Fix unnecessary ensuring ASCII with `tojson` Jinja filter


## [4.2.1]

### Fixed

- Use Jinja2 sandboxing
- Update base Docker images (due to [CVE-2023-7104](https://nvd.nist.gov/vuln/detail/CVE-2023-7104))

## [4.2.0]

Released for version consistency with other DSW tools.

## [4.1.1]

Released for version consistency with other DSW tools.

## [4.1.0]

### Changed

- Adjusted with template metamodel version 12 (integration and integration reply changes)

### Removed

- Support of `wkhtmltopdf` step (marked as deprecated in v3.24)

### Fixed

- Reporting Jinja2 template syntax errors

## [4.0.0]

Released for version consistency with other DSW tools.

## [3.28.0]

### Added

- Send charset as part of S3 object content-type

## [3.27.1]

### Fixed

- Fix PDF output format detection

## [3.27.0]

Released for version consistency with other DSW tools.

## [3.26.1]

Released for version consistency with other DSW tools.

## [3.26.0]

Released for version consistency with other DSW tools.

## [3.25.0]

Released for version consistency with other DSW tools.

## [3.24.0]

### Fixed

- Fix document context for old replies

## [3.23.0]

### Changed

- Improved command queue
- Changed envvars for configuration
- Enhanced error reporting

## [3.22.1]

Released for version consistency with other DSW tools.

## [3.22.0]

### Added

- `weasyprint` step for PDF generation
- Provide `rdflib` for use in Jinja templates

### Changed

- Use Alpine-based Docker image
- Allow `jinja` to be other than the first step

## [3.21.0]

### Added

- Support for i18n in templates (Jinja2 extension)

## [3.20.2]

Released for version consistency with other DSW tools.

## [3.20.1]

Released for version consistency with other DSW tools.

## [3.20.0]

### Changed

- Use file/asset timestamps for cache optimization
- Updated according to DB changes for Template Editor

## [3.19.2]

### Fixed

- Correct version constant

## [3.19.1]

### Changed

- Allowed more levels of ToC using Pandoc filter
- Allowed questionnaire in extras
- Provide original `content` in `enrich-docx` step

## [3.19.0]

### Changed

- Adjusted for new `dsw-config`

## [3.18.0]

### Fixed

- Fix Excel step for datetime

## [3.17.0]

### Added

- Allow access submissions in document generation
- Support ZIP/TAR archives (new step)
- Support ToC in Pandoc for docx
- Support Excel document format (new step)

### Changed

- Switch to psycopg3
- Update Pandoc to 2.19.2

## [3.15.3]

### Fixed

- Update of the database dependency to fix on-start query memory leaks
- Setting of log level to all internal loggers

## [3.15.2]

### Fixed

- Timezone for job retrieval in workers

## [3.15.1]

### Fixed

- Handling document generation exceptions

## [3.15.0]

### Changed

- Improved Sentry reporting

## [3.14.1]

Released for version consistency with other DSW tools.

## [3.14.0]

### Changed

- Moved from [ds-wizard/document-worker](https://github.com/ds-wizard/document-worker) to the monorepo


[Unreleased]: /../../compare/main...develop
[3.14.0]: /../../tree/v3.14.0
[3.14.1]: /../../tree/v3.14.1
[3.15.0]: /../../tree/v3.15.0
[3.15.1]: /../../tree/v3.15.1
[3.15.2]: /../../tree/v3.15.2
[3.15.3]: /../../tree/v3.15.3
[3.16.0]: /../../tree/v3.16.0
[3.17.0]: /../../tree/v3.17.0
[3.18.0]: /../../tree/v3.18.0
[3.19.0]: /../../tree/v3.19.0
[3.19.1]: /../../tree/v3.19.1
[3.19.2]: /../../tree/v3.19.2
[3.20.0]: /../../tree/v3.20.0
[3.20.1]: /../../tree/v3.20.1
[3.20.2]: /../../tree/v3.20.2
[3.21.0]: /../../tree/v3.21.0
[3.22.0]: /../../tree/v3.22.0
[3.22.1]: /../../tree/v3.22.1
[3.23.0]: /../../tree/v3.23.0
[3.24.0]: /../../tree/v3.24.0
[3.25.0]: /../../tree/v3.25.0
[3.26.0]: /../../tree/v3.26.0
[3.26.1]: /../../tree/v3.26.1
[3.27.0]: /../../tree/v3.27.0
[3.27.1]: /../../tree/v3.27.1
[3.28.0]: /../../tree/v3.28.0
[4.0.0]: /../../tree/v4.0.0
[4.1.0]: /../../tree/v4.1.0
[4.1.1]: /../../tree/v4.1.1
[4.2.0]: /../../tree/v4.2.0
[4.2.1]: /../../tree/v4.2.1
