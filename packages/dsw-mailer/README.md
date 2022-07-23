# Data Stewardship Wizard: Mailer

[![User Guide](https://img.shields.io/badge/docs-User%20Guide-informational)](https://guide.ds-wizard.org)
[![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/ds-wizard/pydsw)](https://github.com/ds-wizard/pydsw/releases)
[![Docker Pulls](https://img.shields.io/docker/pulls/datastewardshipwizard/mailer)](https://hub.docker.com/r/datastewardshipwizard/mailer)
[![GitHub](https://img.shields.io/github/license/ds-wizard/pydsw)](LICENSE)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/4975/badge)](https://bestpractices.coreinfrastructure.org/projects/4975)
[![Python Version](https://img.shields.io/badge/Python-%E2%89%A5%203.9-blue)](https://python.org)

*Standalone Mailer Service for DS Wizard*

## Dependencies

-  PostgreSQL

For more information, see [deployment example](https://github.com/ds-wizard/dsw-deployment-example).

## Documentation

For general information, please visit our [User Guide](https://guide.ds-wizard.org).

## Docker

Docker image is prepared with basic dependencies and worker installed. It is available though Docker Hub: [datastewardshipwizard/mailer](https://hub.docker.com/r/datastewardshipwizard/mailer).

### Build image

You can easily build the image yourself:

```bash
$ docker build . -t mailer:local
```

### Mount points

- `/app/config.yml` = configuration file (see [example](config.example.yml))
- `/app/templates` = email templates (see [templates](templates))

A template must always contain the `message.json` descriptor, having both HTML and Plain text part is recommended.

## License

This project is licensed under the Apache License v2.0 - see the
[LICENSE](LICENSE) file for more details.
