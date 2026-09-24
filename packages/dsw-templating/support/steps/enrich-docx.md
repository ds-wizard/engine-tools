# Step: `enrich-docx`

![](https://img.shields.io/badge/status-stable-green)
![](https://img.shields.io/badge/metamodel%20version-%E2%89%A5%2011-blue)

Enrichment step for MS Word (`docx`) documents.

## Input

Gets a `docx` document as input.

## Output

Results in a `docx` document as input.

## Options

Options are used as a dictionary for rewrites with the following syntax:

* Keys can be prefixed with:
  * `rewrite:` and followed by path of file to be rewritten
  * *(currently there are no other prefixes then `rewrite`).*

* Values can be prefixed with:
  * `static:` and followed by path to a file in a template; then it is used as-is to rewrite the original file in `docx`
  * `render:` and followed by path to a file in a template; then it is rendered first as `jinja` template with document context provided and result is used to rewrite the original file in `docx`

## Notes

* Internally, the step unpacks the provided `docx` file, makes adjustments on the level of internal `XML` (and other) files, and packs it back to `docx`.
* To figure out what to rewrite, you should first generate the `docx` later used as input, unzip it and go through the contents.
* A good way to adjust things is to put there some placeholder first (e.g. via `reference.docx` passed to `pandoc`) and then just adjust the placeholder with other / dynamic content.
* Paths to files in a template are relative to template root, i.e. directory with `template.json`.
* It does not matter if the file to be rewritten is missing in the `docx`, then the desired file is simply added.
* The document context is provided in `ctx` variable, other variables, filters, and tests are documented in other documents (same as for `jinja` step).

## Example

```json
{
  "name": "enrich-docx",
  "options": {
    "rewrite:word/footer1.xml": "static:src/docx/footer1.xml",
    "rewrite:word/header1.xml": "render:src/docx/header1.xml.j2"
  }
}
```
