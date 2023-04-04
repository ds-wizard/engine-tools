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

## Notes

* Pandoc filter `pandoc-docx-pagebreakpy` can be found in [addons](../../addons) directory.

## Example

```json
{
  "name" : "pandoc",
  "options" : {
    "from" : "html",
    "to" : "docx",
    "args": "--filter=pandoc-docx-pagebreakpy --reference-doc=src/reference.docx"
  }
}
```
