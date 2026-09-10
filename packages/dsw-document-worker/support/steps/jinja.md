# Step: `jinja`

![](https://img.shields.io/badge/status-stable-green)
![](https://img.shields.io/badge/metamodel%20version-%E2%89%A5%201-blue)

Renders requested Jinja2 template with document context from Wizard Server and optionally other data.

## Input

If not used as a first step, then the previous document is available from `document` variable.

## Output

Results to a file of specified type (via `content-type` option) and file extension (via `extension` option).

## Options

* `template` = path to template file to be rendered
* `content-type` = MIME type of resulting file
* `extension` = file extension for the produced file (without leading dot)
* `jinja-ext` = comma-separated list of optional Jinja2 extensions to enable; only `debug` is supported

Other `policy.*` options map to [Jinja2 policies](https://jinja.palletsprojects.com/en/3.1.x/api/#policies): `policy.truncate.leeway`, `policy.urlize.rel`, `policy.urlize.target`, `policy.urlize.extra_schemes`, and `policy.json.dumps_kwargs.<name>`.

## Notes

* All paths (e.g. for `import` or `extends` in Jinja2 templates are relative from the template root, i.e. directory with `template.json`).
* The [`do`](https://jinja.palletsprojects.com/en/3.1.x/extensions/#expression-statement), [`loopcontrols`](https://jinja.palletsprojects.com/en/3.1.x/extensions/#loop-controls) and [`i18n`](https://jinja.palletsprojects.com/en/3.1.x/extensions/#i18n-extension) Jinja2 extensions are always enabled.
* `{% trans %}` blocks are **always trimmed** and the `policy.ext.i18n.trimmed` option has been removed. Trimming decides the `msgid`, and the POT file is generated per document template while this option was per format, so no single value could have been correct for every format's catalog. Use `{% trans notrimmed %}` where the whitespace matters.
* The experimental `i18n-dir`, `i18n-domain` and `i18n-lang` options have been **removed** and are ignored. Translations are provided per document as [document template locales](../Translations.md), not shipped inside the template.
* Using file extension `.j2` or `.jinja2` for templates is just a convention.
* The document context is provided in `ctx` variable, other variables, filters, and tests are documented in other documents.
* If enabled via `templates.<id>.requests.enabled` in the worker configuration, a `requests` object is available for making HTTP requests from the template. Enabling it means that the template can reach any host the worker can reach, and the response can be embedded in the document. Therefore:
  * only `http` and `https` URLs are allowed,
  * hosts resolving to private, loopback, or link-local addresses (e.g. cloud metadata endpoints) are rejected unless allowed via the `security` configuration,
  * TLS verification cannot be disabled and the timeout cannot be extended from the template (`verify`, `timeout`, `proxies`, and `hooks` arguments are rejected),
  * redirects are followed up to `security.maxRedirects` hops, each of them checked again, and credentials (`auth`, `cookies`, `Authorization` header) are dropped when a redirect points to another host.

## Example

```json
{
  "name" : "jinja",
  "options" : {
    "template" : "src/default.html.j2",
    "content-type" : "text/html",
    "extension" : "html"
  }
}
```
