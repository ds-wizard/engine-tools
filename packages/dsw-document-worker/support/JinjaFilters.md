# Filters

Within Jinja templates, you can use so-called [*filters*](https://jinja.palletsprojects.com/en/3.0.x/templates/#filters). Basically, those are functions applied to a first argument using pipe `|` symbol.

All of our filters are implemented in [templates.filters](../document_worker/templates/filters.py) module.

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

Example: `x|roman`

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
* `xtype` (optional) - desired type of return value (`"string"`, `"int"`, `"float"`, `"list"`)

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
