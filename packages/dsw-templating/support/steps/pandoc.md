# Step: `pandoc`

![](https://img.shields.io/badge/status-stable-green)
![](https://img.shields.io/badge/metamodel%20version-%E2%89%A5%201-blue)

Transformation step that converts Pandoc-compatible document formats.

## Input

Gets a file from the previous step (otherwise it fails), format needs to be specified using `from` option.

## Output

Results in a document in desired format specified using `to` option.

## Options

* `from` = specification of the input format (passed to Pandoc via `--from`, see [docs](https://pandoc.org/MANUAL.html#general-options))
* `to` = specification of the output format (passed to Pandoc via `--to`, see [docs](https://pandoc.org/MANUAL.html#general-options))
* (optional) `args` = additional command line arguments passed to [pandoc](https://pandoc.org/MANUAL.html)
* (optional, experimental) `filters` = additional [Pandoc filters](https://pandoc.org/MANUAL.html#general-options) to be used, comma separated; the filters shipped with `dsw-templating` (`docx-landscape.lua`, `docx-pagebreak.lua`, `docx-toc.lua`) are always available, others need to be located in a directory configured by the runner (the Document Worker uses `/pandoc/filters`, or other set by `PANDOC_FILTERS` environment variable)
* (optional, experimental) `template` = [Pandoc template](https://pandoc.org/MANUAL.html#general-options) to be used, need to be located under `/pandoc/templates` directory (or other set by `PANDOC_TEMPLATES` environment variable)

## Notes

* Pandoc filter `pandoc-docx-pagebreakpy` is installed as a command with `dsw-templating[docx]` (see [docx_pagebreak](../../dsw/templating/docx_pagebreak.py)).
* Pandoc filter `pandoc-docx-pagebreakpy` will be removed with the next template metamodel version, use `` for the `filters` option instead.

## Example

```json
{
  "name" : "pandoc",
  "options" : {
    "from" : "html",
    "to" : "docx",
    "args": "--filter=pandoc-docx-pagebreakpy --reference-doc=src/reference.docx",
    "filters": "docx-pagebreak.lua, docx-toc.lua"
  }
}
```
