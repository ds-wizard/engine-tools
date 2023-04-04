# Step: `archive`

![](https://img.shields.io/badge/status-stable-green)
![](https://img.shields.io/badge/metamodel%20version-%E2%89%A5%2011-blue)

Step that puts file from previous step to an archive file (ZIP or TAR).

## Input

Any input file provided from the previous step.

## Output

ZIP or TAR archive (based on `options`) containing the file from the previous step.

## Options

* `inputFileDst` = destination of the file inside the archive (POSIX-like path including filename)
* (optional) `type` = whether to produce `zip` or `tar` (defaults to `zip`)
* (optional) `compression` = compression method to be used (`none`, `gzip`, `bzip2`, `lzma`; defaults to `none`)
* (optional) `compressionLevel` = value specifying level of compression (`0` to `9`; defaults to `9`)
* (optional) `format` = only for `tar` it allows to specify format (`ustar`, `gnu`, `pax`; defaults to `pax`)

## Notes

* Currently, only a single file can be put into the produced archive.
* Value of `compressionLevel` must be provided as a string (even though it is a numeric value).
* For `zip`, [`zipfile`](https://docs.python.org/3/library/zipfile.html) standard library from Python is used.
* For `tar`, [`tarfile`](https://docs.python.org/3/library/tarfile.html) standard library from Python is used.
* For `bzip2`, if `compressionLevel` is set to `0`, it is automatically fixed to value `1`.

## Example

```json
{
  "name": "archive",
  "options": {
    "type": "tar",
    "compression": "bzip2",
    "compressionLevel": "5",
    "format": "gnu",
    "inputFileDst": "example/file.html"
  }
}
```
