# Data Stewardship Wizard: Data Seeder

[![User Guide](https://img.shields.io/badge/docs-User%20Guide-informational)](https://guide.ds-wizard.org)
[![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/ds-wizard/pydsw)](https://github.com/ds-wizard/pydsw/releases)
[![Docker Pulls](https://img.shields.io/docker/pulls/datastewardshipwizard/data-seeder)](https://hub.docker.com/r/datastewardshipwizard/data-seeder)
[![GitHub](https://img.shields.io/github/license/ds-wizard/pydsw)](LICENSE)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/4975/badge)](https://bestpractices.coreinfrastructure.org/projects/4975)

*Worker for seeding DSW data*

## Usage

-  You can use identical DSW configuration `dsw.yml` file as for DSW server itself (see `config.example.yml`). 
-  You need a directory that contains recipe(s) described in `json` files (see `example/seed.example.json`), usually one seed recipe is enough.
-  From a recipe file, you can link SQL scripts and S3 app directory (paths are relative to the `json` file).
-  To verify recipes, use `dsw-seeder -c config.example.yml -w example/ list`.
-  To run directly seeder, use `dsw-seeder  -c config.example.yml -w seed -r "example"` (`example` is the recipe name).
-  To run worker, use `dsw-seeder  -c config.example.yml -w run -r "example"`.
-  For more information, use `dsw-seeder --help`.

## Docker

Docker image is prepared with basic dependencies and worker installed. It is available though Docker Hub: [datastewardshipwizard/data-seeder](https://hub.docker.com/r/datastewardshipwizard/data-seeder).

### Build image

You can easily build the image yourself:

```bash
$ docker build . -t datastewardshipwizard/data-seeder:local
```

### Environment variables

-  `DSW_CONFIG` (default: `/app/config.yml`)
-  `SEEDER_DATA_DIR` (default: `/app/data`)
-  `SEEDER_RECIPE` (default: `example`)

### Mount points

-  `/app/config.yml` (`DSW_CONFIG`) = configuration file (see [example](config.example.yml))
-  `/app/data` (`SEEDER_DATA_DIR`) = directory with recipe(s)

## License

This project is licensed under the Apache License v2.0 - see the
[LICENSE](LICENSE) file for more details.
