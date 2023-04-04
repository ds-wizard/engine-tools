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

## Notes

* All paths (e.g. for `import` or `extends` in Jinja2 templates are relative from the template root, i.e. directory with `template.json`).
* The [`do` Jinja2 extension](https://jinja.palletsprojects.com/en/3.0.x/extensions/#expression-statement) is enabled.
* Using file extension `.j2` or `.jinja2` for templates is just a convention.
* The document context is provided in `ctx` variable, other variables, filters, and tests are documented in other documents.

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
