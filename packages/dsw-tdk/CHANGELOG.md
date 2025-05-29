# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]


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

### Added

- Add check for no matching files (warning and use of defaults)

### Changed

- Unified IDs (organization, document template, knowledge model)

## [4.16.0]

Released for version consistency with other DSW tools.

## [4.15.0]

### Fixed

- Fixed broken variables in logs

## [4.14.0]

### Changed

- Improved hidden file handling
- Updated initial Jinja file for new projects

## [4.13.0]

### Changed

- Added support for metamodel v16

## [4.12.0]

### Changed

- Added support for metamodel v15

## [4.11.0]

Released for version consistency with other DSW tools.

## [4.10.6]

Released for version consistency with other DSW tools.

## [4.10.5]

Released for version consistency with other DSW tools.

## [4.10.4]

Released for version consistency with other DSW tools.

## [4.10.3]

### Changed

- Updated to newer Docker base image due to vulnerabilities (CVE-2024-45490)[https://nvd.nist.gov/vuln/detail/CVE-2024-45490], (CVE-2024-45491)[https://nvd.nist.gov/vuln/detail/CVE-2024-45491], (CVE-2024-45492)[https://nvd.nist.gov/vuln/detail/CVE-2024-45492]

## [4.10.2]

Released for version consistency with other DSW tools.

## [4.10.1]

### Fixed

- Fix unknown document template metamodel version 14

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

Released for version consistency with other DSW tools.

## [4.5.0]

Released for version consistency with other DSW tools.

## [4.4.1]

Released for version consistency with other DSW tools.

## [4.4.0]

Released for version consistency with other DSW tools.

## [4.3.1]

Released for version consistency with other DSW tools.

## [4.3.0]

### Fixed

- Fix `watch` mode errors after descriptor change

## [4.2.1]

Released for version consistency with other DSW tools.

## [4.2.0]

Released for version consistency with other DSW tools.

## [4.1.1]

Released for version consistency with other DSW tools.

## [4.1.0]

### Changed

- Adjusted with template metamodel version 12 (integration and integration reply changes)

### Fixed

- Fixed directory handling in `watch` mode

## [4.0.0]

### Fixed

- Fixed `unpackage` with default output directory
- Fixed terminating watch mode
- Fixed non-printable characters handling

## [3.28.0]

Released for version consistency with other DSW tools.

## [3.27.1]

Released for version consistency with other DSW tools.

## [3.27.0]

### Changed

- Removed legacy support for authentication using credentials

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

- Added support for authentication using API keys
- Added deprecated warning for username/password authentication

## [3.22.1]

Released for version consistency with other DSW tools.

## [3.22.0]

### Changed

- Use Alpine-based Docker image

### Fixed

- Download published document template with `get` command

## [3.21.0]

### Changed

- Rectify API URL (trailing slash)

## [3.20.2]

### Fixed

- Fix updating `template.json` file

## [3.20.1]

### Fixed

- Fix reported version using `--version`
- Fix creation of document template draft if DSW instance uses different organization ID

## [3.20.0]

### Added

- Added `unpackage` command

### Changed

- Updated according to API changes for Template Editor

## [3.19.2]

### Fixed

- Correct version constant

## [3.19.1]

### Fixed

- Fixed issue with `remote_type` resolution
- Serialization of path for `get` command 

## [3.19.0]

Released for version consistency with other DSW tools.

## [3.18.0]

Released for version consistency with other DSW tools.

## [3.17.0]

Released for version consistency with other DSW tools.

## [3.16.0]

Released for version consistency with other DSW tools.

## [3.15.3]

Released for version consistency with other DSW tools.

## [3.15.2]

Released for version consistency with other DSW tools.

## [3.15.1]

Released for version consistency with other DSW tools.

## [3.15.0]

Released for version consistency with other DSW tools.

## [3.14.1]

### Fixed

- Template creation using `dsw-tdk new`

## [3.14.0]

### Changed

- Moved from [ds-wizard/dsw-tdk](https://github.com/ds-wizard/dsw-tdk) to the monorepo

## [3.13.0]

Released for version consistency with other DSW tools.

## [3.12.0]

### Changed

- Updated with template metamodel 10
- Check file and asset ID on delete

## [3.11.0]

Released for version consistency with other DSW tools.

## [3.10.0]

### Changed

- Updated with template metamodel 9
- Dropped support of Python 3.6 and started with 3.10

## [3.9.0]

Released for version consistency with other DSW tools.

## [3.8.0]

### Changed

- Updated with template metamodel 8
- Updated several dependencies

## [3.7.0]

### Changed

- Updated with template metamodel 7
- Updated several dependencies

## [3.6.0]

### Changed

- Updated with template metamodel 6
- Updated several dependencies

## [3.5.2]

## Fixed

- Loading ID of local template

## [3.5.1]

## Fixed

- Default metamodel version
- Listing all templates

## [3.5.0]

### Changed

- Updated with template metamodel 5
- Updated several dependencies

## [3.4.0]

Released for version consistency with other DSW tools.

## [3.3.0]

Released for version consistency with other DSW tools.

## [3.2.1]

### Fixed

- Retrieving remote API version
- No default start pattern for files

## [3.2.0]

### Changed

- Updated with template metamodel 4

### Fixed

- Checking remote API version if not stable release

## [3.1.0]

Released for version consistency with other DSW tools.

## [3.0.0]

Released for version consistency with other DSW tools.

## [2.14.0]

Released for version consistency with other DSW tools.

## [2.13.0]

### Fixed

- `dsw-tdk put` uploads file synchronously to avoid inconsistency
- Fix `Content-Disposition` escaping in filename of uploaded assets

## [2.12.1]

### Added

- Checks for metamodel version compatibility

### Fixed

- Metamodel version matching new DSW

## [2.12.0]

Released for version consistency with other DSW tools.

## [2.11.0]

### Fixed

- Added timestamps into descriptor for ZIP package.

## [2.10.0]

Released for version consistency with other DSW tools.

## [2.9.0]

Released for version consistency with other DSW tools.

## [2.8.1]

### Changed

- Fix matching template files that have relative path to template dir
- Fix starter Jinja template file (questionnaireReplies)
- Add LICENSE to Python package

## [2.8.0]

Initial DSW Template Development Kit (versioned as part of the [DSW platform](https://github.com/ds-wizard))

### Added

- `new` for initializing new template project
- `list` for listing remote templates
- `get` for retrieving remote template and storing it locally
- `put` for uploading local template project to DSW instance including `watch` functionality for smooth template development
- `verify` for checking template metadata
- `package` for creating an importable ZIP package from local project

[Unreleased]: /../../compare/main...develop
[2.8.0]: https://github.com/ds-wizard/dsw-tdk/tree/v2.8.0
[2.8.1]: https://github.com/ds-wizard/dsw-tdk/tree/v2.8.1
[2.9.0]: https://github.com/ds-wizard/dsw-tdk/tree/v2.9.0
[2.10.0]: https://github.com/ds-wizard/dsw-tdk/tree/v2.10.0
[2.11.0]: https://github.com/ds-wizard/dsw-tdk/tree/v2.11.0
[2.12.0]: https://github.com/ds-wizard/dsw-tdk/tree/v2.12.0
[2.12.1]: https://github.com/ds-wizard/dsw-tdk/tree/v2.12.1
[2.13.0]: https://github.com/ds-wizard/dsw-tdk/tree/v2.13.0
[2.14.0]: https://github.com/ds-wizard/dsw-tdk/tree/v2.14.0
[3.0.0]: https://github.com/ds-wizard/dsw-tdk/tree/v3.0.0
[3.1.0]: https://github.com/ds-wizard/dsw-tdk/tree/v3.1.0
[3.2.0]: https://github.com/ds-wizard/dsw-tdk/tree/v3.2.0
[3.3.0]: https://github.com/ds-wizard/dsw-tdk/tree/v3.3.0
[3.4.0]: https://github.com/ds-wizard/dsw-tdk/tree/v3.4.0
[3.5.0]: https://github.com/ds-wizard/dsw-tdk/tree/v3.5.0
[3.5.1]: https://github.com/ds-wizard/dsw-tdk/tree/v3.5.1
[3.5.2]: https://github.com/ds-wizard/dsw-tdk/tree/v3.5.2
[3.6.0]: https://github.com/ds-wizard/dsw-tdk/tree/v3.6.0
[3.7.0]: https://github.com/ds-wizard/dsw-tdk/tree/v3.7.0
[3.8.0]: https://github.com/ds-wizard/dsw-tdk/tree/v3.8.0
[3.9.0]: https://github.com/ds-wizard/dsw-tdk/tree/v3.9.0
[3.10.0]: https://github.com/ds-wizard/dsw-tdk/tree/v3.10.0
[3.11.0]: https://github.com/ds-wizard/dsw-tdk/tree/v3.11.0
[3.12.0]: https://github.com/ds-wizard/dsw-tdk/tree/v3.12.0
[3.13.0]: https://github.com/ds-wizard/dsw-tdk/tree/v3.13.0
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
