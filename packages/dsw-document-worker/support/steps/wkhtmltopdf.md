# Step: `wkhtmltopdf`

![](https://img.shields.io/badge/status-stable-green)
![](https://img.shields.io/badge/metamodel%20version-%E2%89%A5%201-blue)

Transformation step that converts HTML file from previous step to PDF.

## Input

Gets HTML file from the previous step (otherwise it fails).

## Output

Always results in a PDF file (`application/pdf`) with file extension `.pdf`.

## Options

* (optional) `args` = command line arguments passed to [wkhtmltopdf](https://wkhtmltopdf.org/usage/wkhtmltopdf.txt)

## Notes

* For security reasons, `--disable-local-file-access` is enforced (except working directory where the template is stored).
* We recommend using [`weasyprint`](./weasyprint.md) step instead.

## Example

```json
{
  "name" : "wkhtmltopdf",
  "options" : {
    "args": "--disable-smart-shrinking -B 20mm -L 20mm -R 20mm -T 25mm"
  }
}
```
