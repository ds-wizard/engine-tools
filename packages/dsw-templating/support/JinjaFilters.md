# Filters

Within Jinja templates, you can use so-called [*filters*](https://jinja.palletsprojects.com/en/3.0.x/templates/#filters). Basically, those are functions applied to a first argument using pipe `|` symbol.

All of our filters are implemented in [filters](../dsw/templating/filters.py) module.

## Bultin Filters

There are several widely used [builtin filters](https://jinja.palletsprojects.com/en/3.0.x/templates/#builtin-filters) directly in Jinja.

## Value Conversion

We provide several filters that can be used for conversion of values:

### datetime_format

*Formats timestamp*

Arguments:

* `iso_timestamp` - `datetime` or ISO 8601 `str`
* `fmt` - datetime format passed to [`strftime`](https://docs.python.org/3/library/datetime.html#datetime.date.strftime)

Example: `x.created_at|datetime_format("%d/%m/%y")`

### of_alphabet

*Converts integer to characters*

Arguments:

* `n` - integer >= 0, usually some index

Example: `x|of_alphabet`

:idea: It prints `a` (for 0) to `z` and then continues with `aa`, `ab`, etc.

### roman

*Converts integer to Roman numeral*

Arguments:

* `n` - integer >= 0, usually some index

Example: `x|roman`

### markdown

*Converts markdown to HTML*

Arguments:

* `md_text` - string containing Markdown syntax
* (optional) `sanitize` - whether the resulting HTML is sanitized (default: `True`)

Example: `x|markdown`

:warning: The result is sanitized using an allow-list by default because Markdown
may contain raw HTML. This is essential for content coming from end users (e.g.
replies in a project): without it, an answer can inject `<script>` into HTML
documents or make the PDF renderer fetch local files and internal URLs (e.g.
`<img src="file:///etc/passwd">`). Sanitization removes scripting (such as
`<script>` and `on*` attributes), embedded content (such as `<iframe>`,
`<object>`, or `<svg>`), stylesheets, and URLs with unexpected schemes (such as
`file:`, `javascript:`, or `data:text/html`); plain Markdown output and common
inline HTML formatting are preserved.

Use `x|markdown(sanitize=false)` to get the previous (unrestricted) behaviour,
but only for content that is fully controlled by the document template itself
and never for end-user input.

### dot

*Ends sentence if not already ended*

* `text`

Example: `"This sentence has no end"|dot`

### extract

*Extracts values from object by having keys*

* `obj` - object for getting values (typically `dict`)
* `keys` - list of keys to retrieve

Example: `entities.questions|extract([uuid1, uuid2, uuid3])`

## Reply Helpers

These filters are handy when you need to work with `repliesMap` from the plain JSON-like context.

### reply_path

*Joins list of UUIDs into a path*

* `uuids` - list of UUIDs

Example: `[uuid1, uuid2, uuid3]|reply_path`

### find_reply

*Tries to find a reply value using a path*

* `replies` - dict with replies
* `path` - list of UUIDs or path-string
* `cast_type` (optional) - desired type of return value (`"string"`, `"int"`, `"float"`, `"list"`)

Example: `replies|find_reply(path, "list")`

### reply_str_value

*Extracts string value from a reply if possible*

* `reply` - object that might a reply

Example: `reply|reply_str_value`

Returns an empty string if not possible to extract it from the reply. Suitable for `AnswerReply`, `StringReply` and `IntegrationReply`.

### reply_int_value

*Extracts integer value from a reply if possible*

* `reply` - object that might a reply

Example: `reply|reply_int_value`

Returns zero if not possible to extract it from the reply. Suitable for `StringReply` with numeric value type.

### reply_float_value

*Extracts float value from a reply if possible*

* `reply` - object that might a reply

Example: `reply|reply_float_value`

Returns zero if not possible to extract it from the reply. Suitable for `StringReply` with numeric value type.

### reply_items

*Extracts list of strings from a reply if possible*

* `reply` - object that might a reply

Example: `reply|reply_items`

Returns empty list if not possible to extract it from the reply. Suitable for `MultiChoiceReply` and `ItemListReply`.

## Special

These filters are more complex and add various support to template development.

### to_context_obj

*Converts plain context to well-defined objects*

* `ctx` - plain JSON-like document context

This filter is used for easier transition and might be removed in the future.

### extract_replies

*Extracts the replies of a project into nested objects keyed by knowledge model annotations*

* `ctx` - document context object (from `to_context_obj`)
* `config` (optional) - configuration; the values given replace the defaults below, the rest are kept

Example: `{% set x = dc|extract_replies({'version': '2'}) %}` and then `{{ x.dataset.title._value }}`

The defaults:

```python
{
    'variant': 'simple',
    'version': '1',
    'annotations': {
        'key': 'json.key',      # annotation of chapters and questions: the key of the object
        'value': 'json.value',  # annotation of answers and choices: their `_value`
    },
    'options': {
        'include_reply_objects': False,  # add the reply object as `_reply`
    },
}
```

The result is a dictionary keyed by the `json.key` annotations (not by UUIDs), nested as follows:

* a chapter with a key is an object under that key; the questions of a chapter without a key are in the result itself;
* the follow-up questions of the selected answer are in the options question's object; those of an options question without a key are in the object that holds the options question;
* list and multi-choice questions are lists; the item questions of a list are in each item's object;
* a list question without a key leaves out all its item questions (a warning is logged);
* questions without a key are left out, and two questions with the same key in one object overwrite each other (a warning is logged).

The fields of the objects:

| Question | `simple:1` | `simple:2` adds |
|---|---|---|
| value | `_value` (the string reply), `_path` | `_value` is a number for number questions |
| integration | `_value`, `_raw` (not for plain replies), `_path` | |
| options | `_uuid`, `_label`, `_value` (from `json.value`), `_path` of the question | |
| multi-choice | a list of `_uuid`, `_label`, `_value`, `_path` per choice | |
| list | a list of `_uuid`, `_path` of the list question per item | `_value` (item UUID), `_label` (item title), `_path` of the item |
| item select | `_uuid`, `_label`, `_path` | `_value` (item UUID) |
| file | `_uuid`, `_name`, `_size`, `_content_type`, `_url`, `_path` | `_value` (file UUID) |

With `include_reply_objects`, each object has `_reply`; for list and multi-choice questions, each item and each choice has it.

**Version `1`** (the default):

* an unanswered question is `None` (lists and multi-choice questions `[]`) and the follow-ups of unselected answers are absent, so a path through an unanswered question fails;
* `json.value` is converted loosely: `true`/`false` in any case to booleans and anything Python's `int()` or `float()` accepts to a number (`007` becomes `7`, `1e3` becomes `1000.0`, `nan` a float).

**Version `2`**:

* every annotated question is present: unanswered ones are objects with `_value` set to `None` (lists and multi-choice questions `[]`), and the follow-ups of unselected answers are added in the same way without overwriting those of the selected one, so any path along the knowledge model is safe;
* `json.value` is converted only when it is exactly `true` or `false`, or a plain integer without leading zeros (`-3`, `0`, `12`); everything else, including `007`, `1.5` or `yes`, stays a string;
* every object has `_value`, as in the table above.
