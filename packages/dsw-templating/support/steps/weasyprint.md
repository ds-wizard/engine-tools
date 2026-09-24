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
* Resources referenced from the rendered HTML (images, stylesheets, fonts) are
  fetched through a restricted URL fetcher:
  * `file:` URLs are allowed only within the template directory (and the
    directories listed in `security.allowedPaths`),
  * `http(s)` URLs are allowed only if external resources are enabled
    (`security.allowExternalResources`) and the host does not resolve to a
    private, loopback, or link-local address (unless it is listed in
    `security.allowedHosts` or `security.allowPrivateNetwork` is enabled),
  * `data:` URLs are always allowed, other schemes are rejected.
* Blocked resources are logged as a warning and simply not included in the
  resulting PDF (as with any other resource that cannot be retrieved).

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
