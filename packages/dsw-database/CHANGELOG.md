# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed

- Removed unnecessary Tenant Config which is now refactored in database


## [4.20.1]

Released for version consistency with other DSW tools.

## [4.20.0]

Released for version consistency with other DSW tools.

## [4.19.1]

Released for version consistency with other DSW tools.

## [4.19.0]

Released for version consistency with other DSW tools.

## [4.18.3]

Released for version consistency with other DSW tools.

## [4.18.2]

Released for version consistency with other DSW tools.

## [4.18.1]

Released for version consistency with other DSW tools.

## [4.18.0]

Released for version consistency with other DSW tools.

## [4.17.0]

Released for version consistency with other DSW tools.

## [4.16.0]

Released for version consistency with other DSW tools.

## [4.15.0]

Released for version consistency with other DSW tools.

## [4.14.0]

Released for version consistency with other DSW tools.

## [4.13.0]

Released for version consistency with other DSW tools.

## [4.12.0]

Released for version consistency with other DSW tools.

## [4.11.0]

Released for version consistency with other DSW tools.

## [4.10.6]

Released for version consistency with other DSW tools.

## [4.10.5]

Released for version consistency with other DSW tools.

## [4.10.4]

Released for version consistency with other DSW tools.

## [4.10.3]

Released for version consistency with other DSW tools.

## [4.10.2]

Released for version consistency with other DSW tools.

## [4.10.1]

Released for version consistency with other DSW tools.

## [4.10.0]

Released for version consistency with other DSW tools.

## [4.9.1]

Released for version consistency with other DSW tools.

## [4.9.0]

### Changed

- Updated `instance_mail_config` to support Amazon SES configuration

## [4.8.1]

### Changed

- Updated to newer Docker base image due to vulnerability (CVE-2024-5535)[https://nvd.nist.gov/vuln/detail/CVE-2024-5535]

## [4.8.0]

### Removed

- Phased out tenant config features

## [4.7.0]

Released for version consistency with other DSW tools.

## [4.6.0]

### Fixed

- Use UTC timezone consistently

## [4.5.0]

Released for version consistency with other DSW tools.

## [4.4.1]

Released for version consistency with other DSW tools.

## [4.4.0]

Released for version consistency with other DSW tools.

## [4.3.1]

### Fixed

- Fix retrieving configs

## [4.3.0]

Released for version consistency with other DSW tools.

## [4.2.1]

Released for version consistency with other DSW tools.

## [4.2.0]

Released for version consistency with other DSW tools.

## [4.1.1]

Released for version consistency with other DSW tools.

## [4.1.0]

Released for version consistency with other DSW tools.

## [4.0.0]

### Changed

- Adapt DB renames in documents table

## [3.28.0]

Released for version consistency with other DSW tools.

## [3.27.1]

Released for version consistency with other DSW tools.

## [3.27.0]

Released for version consistency with other DSW tools.

## [3.26.1]

Released for version consistency with other DSW tools.

## [3.26.0]

Released for version consistency with other DSW tools.

## [3.25.0]

Released for version consistency with other DSW tools.

## [3.24.0]

Released for version consistency with other DSW tools.

## [3.23.0]

### Changed

- Allow to avoid auto-connect on init

## [3.22.1]

Released for version consistency with other DSW tools.

## [3.22.0]

Released for version consistency with other DSW tools.

## [3.21.0]

Released for version consistency with other DSW tools.

## [3.20.2]

### Fixed

- Fix retrieving questionnaires
- Fix retrieving app configs

## [3.20.1]

Released for version consistency with other DSW tools.

## [3.20.0]

### Changed

- Add TemplateFile/TemplateAsset timestamps
- Rename template-related tables to document_template
- Add phase to document_template

## [3.19.2]

Released for version consistency with other DSW tools.

## [3.19.1]

### Added

- Possibility to fetch questionnaire

## [3.19.0]

Released for version consistency with other DSW tools.

## [3.18.0]

Released for version consistency with other DSW tools.

## [3.17.0]

### Added

- Allow access to submissions

### Changed

- Switch to psycopg3

## [3.16.0]

Released for version consistency with other DSW tools.

## [3.15.3]

### Fixed

- Avoid on-start query memory leaks

## [3.15.2]

Released for version consistency with other DSW tools.

## [3.15.1]

Released for version consistency with other DSW tools.

## [3.15.0]

Released for version consistency with other DSW tools.

## [3.14.1]

Released for version consistency with other DSW tools.

## [3.14.0]

### Added

- Initiated this library from *dsw-data-seeder*, *dsw-document-worker*, and *dsw-mailer*


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
[3.25.1]: /../../tree/v3.25.1
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
