from __future__ import annotations

import re

import nh3


# Attributes that hold a URL and therefore need scheme checking
URL_ATTRIBUTES = frozenset({
    ('a', 'href'),
    ('area', 'href'),
    ('blockquote', 'cite'),
    ('del', 'cite'),
    ('img', 'src'),
    ('ins', 'cite'),
    ('q', 'cite'),
})

# Tags allowed in the sanitized output (nh3 defaults + table footer)
ALLOWED_TAGS = nh3.ALLOWED_TAGS | {'tfoot'}

# Attributes allowed per tag ('*' applies to all tags)
ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
    tag: set(attrs) for tag, attrs in nh3.ALLOWED_ATTRIBUTES.items()
}
ALLOWED_ATTRIBUTES['*'] = {'class', 'dir', 'id', 'lang', 'title'}
ALLOWED_ATTRIBUTES.setdefault('a', set()).update({'href', 'hreflang', 'target'})
ALLOWED_ATTRIBUTES.setdefault('ol', set()).update({'start', 'type'})
ALLOWED_ATTRIBUTES.setdefault('time', set()).add('datetime')
for _tag in ('div', 'img', 'p', 'span', 'table', 'td', 'th', 'tr'):
    ALLOWED_ATTRIBUTES.setdefault(_tag, set()).add('style')

# URL schemes allowed at all (further restricted per attribute below)
ALLOWED_URL_SCHEMES = frozenset({'data', 'http', 'https', 'mailto'})

# CSS properties allowed in the "style" attribute; anything that can reference
# an external resource (e.g. background-image with url(...)) is left out
ALLOWED_STYLE_PROPERTIES = frozenset({
    'background-color', 'border', 'border-bottom', 'border-collapse',
    'border-color', 'border-left', 'border-right', 'border-style',
    'border-top', 'border-width', 'color', 'font-family', 'font-size',
    'font-style', 'font-variant', 'font-weight', 'height', 'letter-spacing',
    'line-height', 'margin', 'margin-bottom', 'margin-left', 'margin-right',
    'margin-top', 'padding', 'padding-bottom', 'padding-left', 'padding-right',
    'padding-top', 'text-align', 'text-decoration', 'text-indent',
    'text-transform', 'vertical-align', 'white-space', 'width', 'word-break',
})

_SCHEME_PATTERN = re.compile(r'^([a-zA-Z][a-zA-Z0-9+.\-]*):')
_IMG_SCHEMES = frozenset({'http', 'https'})
_LINK_SCHEMES = frozenset({'http', 'https', 'mailto'})


def _url_scheme(value: str) -> str | None:
    # Strip whitespace (incl. embedded tabs/newlines used to obfuscate schemes)
    url = ''.join(value.split()).lower()
    match = _SCHEME_PATTERN.match(url)
    if match is None:
        return None  # relative URL
    return match.group(1)


def _attribute_filter(tag: str, attr: str, value: str) -> str | None:
    if (tag, attr) not in URL_ATTRIBUTES:
        return value
    scheme = _url_scheme(value)
    if scheme is None:
        return value  # relative URLs are resolved against the document base
    if tag == 'img':
        if scheme in _IMG_SCHEMES:
            return value
        if ''.join(value.split()).lower().startswith('data:image/'):
            return value
        return None
    if scheme in _LINK_SCHEMES:
        return value
    return None


def sanitize_html(html: str) -> str:
    """Sanitize an HTML fragment using a strict allow-list.

    Removes scripting (tags, event handlers), embedded content (iframe,
    object, embed, svg, ...), stylesheets, and URLs with unexpected schemes
    such as ``file:``, ``javascript:`` or ``data:text/html``.
    """
    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=set(ALLOWED_URL_SCHEMES),
        attribute_filter=_attribute_filter,
        filter_style_properties=set(ALLOWED_STYLE_PROPERTIES),
    )
