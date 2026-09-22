# Reference fixtures

Real payloads, so the models are checked against data the backend produced and not only against
our reading of its code.

| File | Source | Licence |
|---|---|---|
| `dsw_root_2.8.1.km.gz` | Common DSW Knowledge Model `dsw:root:2.8.1`, exported from the registry | Apache-2.0 |
| `dsw_smp_1.2.4.km.gz` | Software Management Planning KM `dsw:smp:1.2.4` | Apache 2.0 |
| `dmp.eosc.cz_czech-nrp-km_1.0.2.km.gz` | Czech National Repository Platform KM `dmp.eosc.cz:czech-nrp-km:1.0.2` | Apache-2.0 |

All bundles are knowledge model metamodel version 20. They contain no personal data; integration
secrets appear only as placeholders.

## Refreshing

When the knowledge model metamodel version changes, export the same bundles again from the
registry and compress them reproducibly:

```bash
gzip -9nc dsw_root_X.Y.Z.km > dsw_root_X.Y.Z.km.gz
```

## Document templates

`templates/*.json` are the local `template.json` descriptors of public DSW templates (metamodel
`18.0`, all Apache-2.0), copied from the default branch of each repository:

| File | Repository |
|---|---|
| `madmp-template.json` | `ds-wizard/madmp-template` |
| `questionnaire-report-template.json` | `ds-wizard/questionnaire-report-template` |
| `horizon-europe-dmp-template.json` | `ds-wizard/horizon-europe-dmp-template` |
| `smp-template.json` | `ds-wizard/smp-template` |
