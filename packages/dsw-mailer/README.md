# Data Stewardship Wizard: Mailer

[![User Guide](https://img.shields.io/badge/docs-User%20Guide-informational)](https://guide.ds-wizard.org)
[![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/ds-wizard/engine-tools)](https://github.com/ds-wizard/engine-tools/releases)
[![Docker Pulls](https://img.shields.io/docker/pulls/datastewardshipwizard/mailer)](https://hub.docker.com/r/datastewardshipwizard/mailer)
[![GitHub](https://img.shields.io/github/license/ds-wizard/engine-tools)](LICENSE)
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

## Translations

Mails are translated with the tenant's **mail template locales**: PO files uploaded in the
Wizard's mail settings, stored at `mail-template-locales/<uuid>/mail.po`. Each recipient gets one
mail, in the enabled mail template locale whose code matches the code of their UI locale (exact,
then the base language: `de-AT` matches `de`), otherwise in the tenant's default one, otherwise in
`en`, otherwise in the built-in English. A recipient who is not a user gets the default. A command
with `sendAsOne` is sent as a single mail to all recipients, in English. The mailer compiles a PO
once and stores `mail.mo` next to it.

Translators work from the **default mail POT**, the strings of the built-in templates:

- It is built with the templates and shipped in the image as `templates/locale/mail.pot`:
  `dsw-mailer make-pot TEMPLATES-DIR [--kind KIND] [--version VERSION]` (or `make pot`). Its
  `Project-Id-Version` is `<kind>:<version>`, `dsw-mail-templates:<mailer version>` by default.
  Run it again whenever you replace the templates.
- The mailer keeps it current in S3 at `mail-templates/mail.pot` (never tenant-prefixed), where
  the Wizard serves it: at startup, and with `dsw-mailer sync-default-pot [--force]` (in Lambda,
  the event `{"syncDefaultPot": {"force": false}}`), meant to run after each deployment. It is
  uploaded when it is missing, older or of the same version but other content; a newer one is
  kept (an older mailer never downgrades it) unless `--force` is given. A failed sync is
  reported, but never stops mail from being sent.
- The mailer therefore needs write access to `mail-templates/` and `mail-template-locales/` in
  the bucket. Set `mail.syncDefaultPot: false` (`MAIL_SYNC_DEFAULT_POT`) to turn the sync off, as
  for the Registry server, whose mails are in English only.

## License

This project is licensed under the Apache License v2.0 - see the
[LICENSE](LICENSE) file for more details.
