# Data Stewardship Wizard Engine Tools

[![User Guide](https://img.shields.io/badge/docs-User%20Guide-informational)](https://guide.ds-wizard.org)
[![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/ds-wizard/engine-tools)](https://github.com/ds-wizard/engine-tools/releases)
[![LICENSE](https://img.shields.io/github/license/ds-wizard/engine-tools)](LICENSE)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/4975/badge)](https://bestpractices.coreinfrastructure.org/projects/4975)

*All DSW Python components and related libraries together at once place*

## Packages

In this monorepo, we manage the following Python packages (each has its own subdirectory):

### Libraries

*Libraries are currently intended for internal use to support DRYness*

* [Command Queue (dsw-command-queue)](packages/dsw-command-queue)
* [Config (dsw-config)](packages/dsw-config)
* [Database (dsw-database)](packages/dsw-database)
* [Storage (dsw-storage)](packages/dsw-storage)

Libraries are currently kept compatible with Python 3.10 and higher.

### Utilities

* [Template Development Kit (dsw-tdk)](packages/dsw-tdk)

Utilities are currently kept compatible with Python 3.9 and higher.

### Workers

* [Data Seeder (dsw-data-seeder)](packages/dsw-data-seeder)
* [Document Worker (dsw-document-worker)](packages/dsw-document-worker)
* [Mailer (dsw-mailer)](packages/dsw-mailer)

Workers are currently kept compatible with Python 3.10 and higher.

## License

This project is licensed under the Apache License v2.0 - see the
[LICENSE](LICENSE) file for more details.
