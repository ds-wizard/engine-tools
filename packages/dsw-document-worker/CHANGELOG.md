# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Switch to use semver for document template metamodel versioning


## [4.21.0]

Released for version consistency with other DSW tools.

## [4.20.1]

### Changed

- Updated to newer Docker base image due to vulnerability (CVE-2025-6965)[https://nvd.nist.gov/vuln/detail/CVE-2025-6965]

## [4.20.0]

### Added

- Support item title for all types of questions
- Add Jinja filter and mechanism to extract replies using KM annotations 

### Fixed

- Fixed file replies linked from file questions

## [4.19.1]

### Changed

- Updated to newer Docker base image due to vulnerability (CVE-2025-4517)[https://nvd.nist.gov/vuln/detail/CVE-2025-4517]

## [4.19.0]

### Fixed

- Improved reporting of template-invoked errors

## [4.18.3]

Released for version consistency with other DSW tools.

## [4.18.2]

Released for version consistency with other DSW tools.

## [4.18.1]

Released for version consistency with other DSW tools.

## [4.18.0]

### Changed

- Update of Pandoc to 3.6.4

## [4.17.0]

### Fixed

- Fixed filtering Sentry events for document template issues

## [4.16.0]

Released for version consistency with other DSW tools.

## [4.15.0]

### Added

- Initial support for plugins (Steps, Jinja environment, document context enrichment)

### Fixed

- Fixed error reporting on worker startup

## [4.14.0]

### Changed

- Improved error reporting
- Improved retry mechanism for failed commands

### Fixed

- Fixed storage limits checking

## [4.13.0]

### Changes

- Added support for value question validations

## [4.12.0]

### Changed

- Added support for file question

## [4.11.0]

Released for version consistency with other DSW tools.

## [4.10.6]

### Fixed

- Fixed inconsistencies in document context with metamodel version 14

## [4.10.5]

### Fixed

- Fixed command queue job timeout (moved support from workers to queue, reliable timeout approach)

## [4.10.4]

Released for version consistency with other DSW tools.

## [4.10.3]

### Changed

- Updated to newer Docker base image due to vulnerabilities (CVE-2024-45490)[https://nvd.nist.gov/vuln/detail/CVE-2024-45490], (CVE-2024-45491)[https://nvd.nist.gov/vuln/detail/CVE-2024-45491], (CVE-2024-45492)[https://nvd.nist.gov/vuln/detail/CVE-2024-45492]

## [4.10.2]

Released for version consistency with other DSW tools.

## [4.10.1]

Released for version consistency with other DSW tools.

## [4.10.0]

### Changed

- Restructured document context
- Added support for item select question
- Added support for resource collections and pages

## [4.9.1]

### Changed

- Updated to newer Docker base image due to vulnerability (CVE-2024-38428)[https://nvd.nist.gov/vuln/detail/CVE-2024-38428]

## [4.9.0]

Released for version consistency with other DSW tools.

## [4.8.1]

### Changed

- Updated to newer Docker base image due to vulnerability (CVE-2024-5535)[https://nvd.nist.gov/vuln/detail/CVE-2024-5535]

## [4.8.0]

### Changed

- Simplify PDF generation options

## [4.7.0]

Released for version consistency with other DSW tools.

## [4.6.0]

### Added

- Support lambda deployment

### Fixed

- Markdown filter in Jinja uses training backslashes for newlines
- Use UTC timezone consistently

## [4.5.0]

Released for version consistency with other DSW tools.

## [4.4.1]

Released for version consistency with other DSW tools.

## [4.4.0]

### Changed

- Enhanced support for Pandoc filters in `pandoc` step

## [4.3.1]

Released for version consistency with other DSW tools.

## [4.3.0]

### Added

- Support for Jinja policies
- Support for Lambda deployment

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
[4.3.0]: /../../tree/v4.3.0
[4.3.1]: /../../tree/v4.3.1
[4.4.0]: /../../tree/v4.4.0
[4.4.1]: /../../tree/v4.4.1
[4.5.0]: /../../tree/v4.5.0
[4.6.0]: /../../tree/v4.6.0
[4.7.0]: /../../tree/v4.7.0
[4.8.0]: /../../tree/v4.8.0
[4.8.1]: /../../tree/v4.8.1
[4.9.0]: /../../tree/v4.9.0
[4.9.1]: /../../tree/v4.9.1
[4.10.0]: /../../tree/v4.10.0
[4.10.1]: /../../tree/v4.10.1
[4.10.2]: /../../tree/v4.10.2
[4.10.3]: /../../tree/v4.10.3
[4.10.4]: /../../tree/v4.10.4
[4.10.5]: /../../tree/v4.10.5
[4.10.6]: /../../tree/v4.10.6
[4.11.0]: /../../tree/v4.11.0
[4.12.0]: /../../tree/v4.12.0
[4.13.0]: /../../tree/v4.13.0
[4.14.0]: /../../tree/v4.14.0
[4.15.0]: /../../tree/v4.15.0
[4.16.0]: /../../tree/v4.16.0
[4.17.0]: /../../tree/v4.17.0
[4.18.0]: /../../tree/v4.18.0
[4.18.1]: /../../tree/v4.18.1
[4.18.2]: /../../tree/v4.18.2
[4.18.3]: /../../tree/v4.18.3
[4.19.0]: /../../tree/v4.19.0
[4.19.1]: /../../tree/v4.19.1
[4.20.0]: /../../tree/v4.20.0
[4.20.1]: /../../tree/v4.20.1
[4.21.0]: /../../tree/v4.21.0
