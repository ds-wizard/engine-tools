# Tests

Within Jinja templates, you can use so-called [*tests*](https://jinja.palletsprojects.com/en/3.0.x/templates/#tests). Basically, those are helpers usable in conditions after `is` keyword:

```jinja
{% if loop.index is divisibleby 3 %}
    {# ... #}
{% endif %}
```

All of our filters are implemented in [templates.tests](../document_worker/templates/tests.py) module.

## Bultin Tests

There are several widely used [builtin tests](https://jinja.palletsprojects.com/en/3.0.x/templates/#builtin-tests) directly in Jinja.

## Custom Tests

### not_empty

*Checks if size of a collection is higher than 0*

Example: `items is not_empty`

### of_type

*Checks if an object is instance of a certain type / class*

Example: `parent is of_type "ListQuestion"`

:bulb: The name must be a string; however, it is case-insensitive. It also checks all superclasses.
