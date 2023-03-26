# Step: `weasyprint`

![](https://img.shields.io/badge/status-experimental-orange)
![](https://img.shields.io/badge/metamodel%20version-%E2%89%A5%20X-blue)

Transformation step that converts HTML file from previous step to PDF using [WeasyPrint](https://weasyprint.org/).

## Input

Gets HTML file from the previous step (otherwise it fails).

## Output

Always results in a PDF file (`application/pdf`) with file extension `.pdf`.

## Options

* (optional) `render.presentational_hints` = whether HTML presentational hints are followed (default: `False`)
* (optional) `render.optimize_size` = specify what should be optimized (`''`, `'fonts'`, `'images'`, `'fonts,images'`, default: `'fonts'`)
* (optional) `render.forms` = whether PDF forms have to be included (default: `False`)
* (optional) `pdf.zoom` = zoom value as a floating number (default: `'1'`)
* (optional) `pdf.variant` = a PDF variant name
* (optional) `pdf.version` = a PDF version number
* (optional) `pdf.custom_metadata` = whether custom HTML metadata should be stored in the generated PDF

## Notes

* Check the official [WeasyPrint](https://weasyprint.org/) documentation and examples for more information.

## Example

```json
{
  "name" : "weasyprint",
  "options" : {
    "render.optimize_size": "fonts,images",
    "render.forms": "True",
    "pdf.zoom": "1.2"
  }
}
```
