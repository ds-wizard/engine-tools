# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]


## [4.13.0]

Released for version consistency with other DSW tools.

## [4.12.0]

Released for version consistency with other DSW tools.

## [4.11.0]

Released for version consistency with other DSW tools.

## [4.10.6]

Released for version consistency with other DSW tools.

## [4.10.5]

### Fixed

- Fixed command queue job timeout (moved support from workers to queue, reliable timeout approach)

## [4.10.4]

### Fixed

- Fix selection of SMTP security mechanism

## [4.10.3]

### Changed

- Updated to newer Docker base image due to vulnerabilities (CVE-2024-45490)[https://nvd.nist.gov/vuln/detail/CVE-2024-45490], (CVE-2024-45491)[https://nvd.nist.gov/vuln/detail/CVE-2024-45491], (CVE-2024-45492)[https://nvd.nist.gov/vuln/detail/CVE-2024-45492]

## [4.10.2]

Released for version consistency with other DSW tools.

## [4.10.1]

Released for version consistency with other DSW tools.

## [4.10.0]

Released for version consistency with other DSW tools.

## [4.9.1]

Released for version consistency with other DSW tools.

## [4.9.0]

Released for version consistency with other DSW tools.

## [4.8.1]

### Changed

- Updated to newer Docker base image due to vulnerability (CVE-2024-5535)[https://nvd.nist.gov/vuln/detail/CVE-2024-5535]

## [4.8.0]

Released for version consistency with other DSW tools.

## [4.7.0]

Released for version consistency with other DSW tools.

## [4.6.0]

### Fixed

- Use UTC timezone consistently

## [4.5.0]

Released for version consistency with other DSW tools.

## [4.4.1]

### Fixed

- Fixed color handling for custom colors in emails

## [4.4.0]

Released for version consistency with other DSW tools.

## [4.3.1]

Released for version consistency with other DSW tools.

## [4.3.0]

### Added

- Enable to use colors and logo in email templates

## [4.2.1]

### Fixed

- Use Jinja2 sandboxing
- Update base Docker images (due to [CVE-2023-7104](https://nvd.nist.gov/vuln/detail/CVE-2023-7104))

## [4.2.0]

Released for version consistency with other DSW tools.

## [4.1.1]

Released for version consistency with other DSW tools.

## [4.1.0]

Released for version consistency with other DSW tools.

## [4.0.0]

Released for version consistency with other DSW tools.

## [3.28.0]

Released for version consistency with other DSW tools.

## [3.27.1]

Released for version consistency with other DSW tools.

## [3.27.0]

### Added

- Notification emails about API keys

## [3.26.1]

### Fixed

- Fix loading custom mail config

## [3.26.0]

Released for version consistency with other DSW tools.

## [3.25.0]

Released for version consistency with other DSW tools.

## [3.24.0]

Released for version consistency with other DSW tools.

## [3.23.0]

### Changed

- Improved command queue
- Changed envvars for configuration
- Enhanced error reporting

### Fixed

- Buttons visual compatibility in templates

## [3.22.1]

Released for version consistency with other DSW tools.

## [3.22.0]

### Changed

- Use Alpine-based Docker image

## [3.21.0]

### Added

- Add 2FA verification email
- Support for email headers: `date`, `message-id`, `language`, `priority`, `sensitivity`, and `importance`

## [3.20.2]

Released for version consistency with other DSW tools.

## [3.20.1]

Released for version consistency with other DSW tools.

## [3.20.0]

Released for version consistency with other DSW tools.

## [3.19.2]

### Fixed

- Correct version constant

## [3.19.1]

Released for version consistency with other DSW tools.

## [3.19.0]

### Changed

- Adjusted for new `dsw-config`

## [3.18.0]

Released for version consistency with other DSW tools.

## [3.17.0]

### Changed

- Switch to psycopg3

## [3.16.0]

Released for version consistency with other DSW tools.

## [3.15.3]

### Fixed

- Update of the database dependency to fix on-start query memory leaks
- Setting of log level to all internal loggers

## [3.15.2]

### Fixed

- Timezone for job retrieval in workers

## [3.15.1]

Released for version consistency with other DSW tools.

## [3.15.0]

### Changed

- Improved Sentry reporting

## [3.14.1]

Released for version consistency with other DSW tools.

## [3.14.0]

### Changed

- Moved from [ds-wizard/mailer](https://github.com/ds-wizard/mailer) to the monorepo


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
