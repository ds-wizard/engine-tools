"""Markdown rendering and HTML sanitizing for document contexts (``dsw-models[rendering]``).

Port of ``dsw.document_worker.model.utils`` and ``dsw.document_worker.sanitizer``.
"""
from __future__ import annotations

import io
import re
import typing

import markdown
import markdown.preprocessors
import markupsafe
import nh3


def unmark_element(element, stream=None):
    if stream is None:
        stream = io.StringIO()
    if element.text:
        stream.write(element.text)
    for sub in element:
        unmark_element(sub, stream)
    if element.tail:
        stream.write(element.tail)
    return stream.getvalue()


# patching Markdown
markdown.Markdown.output_formats['plain'] = unmark_element
__md = markdown.Markdown(output_format='plain')
__md.stripTopLevelTags = False


def strip_markdown(text):
    return __md.convert(text)


class DSWMarkdownExt(markdown.extensions.Extension):

    @typing.override
    def extendMarkdown(self, md):
        md.preprocessors.register(DSWMarkdownProcessor(md), 'dsw_markdown', 27)
        md.registerExtension(self)


class DSWMarkdownProcessor(markdown.preprocessors.Preprocessor):
    LI_RE = re.compile(r'^[ ]*((\d+\.)|[*+-])[ ]+.*')
    # Opening of a fenced code block, mirroring the `fenced_code` extension:
    # a run of at least three backticks or tildes at the start of the line.
    FENCE_RE = re.compile(r'^(?P<fence>`{3,}|~{3,})')

    def __init__(self, md):
        super().__init__(md)

    def _find_fence_close(self, lines, start, fence):
        # `fenced_code` closes on the exact same marker (same character and
        # length), optionally followed by trailing spaces.
        for index in range(start, len(lines)):
            if lines[index].rstrip(' ') == fence:
                return index
        return None

    def run(self, lines):
        prev_li = False
        new_lines = []
        index = 0

        while index < len(lines):
            line = lines[index]

            # Copy complete fenced code blocks verbatim so that list-like or
            # backslash-terminated code lines are not rewritten. A block counts
            # only when a matching closing fence exists later, exactly as the
            # `fenced_code` extension requires; an unterminated fence is treated
            # as ordinary text.
            fence_match = self.FENCE_RE.match(line)
            if fence_match is not None:
                fence = fence_match.group('fence')
                close = self._find_fence_close(lines, index + 1, fence)
                if close is not None:
                    new_lines.extend(lines[index:close + 1])
                    prev_li = False
                    index = close + 1
                    continue

            # Add line break before the first list item
            if self.LI_RE.match(line):
                if not prev_li:
                    new_lines.append('')
                prev_li = True
            elif line == '':
                prev_li = False

            # Replace trailing un-escaped backslash with (supported) two spaces
            _line = line.rstrip('\\')
            if line[-1:] == '\\' and (len(line) - len(_line)) % 2 == 1:
                new_lines.append(f'{line[:-1]}  ')
                index += 1
                continue

            new_lines.append(line)
            index += 1

        return new_lines


def render_markdown(md_text: str, sanitize: bool = True):
    """Render Markdown to HTML.

    The result is sanitized by default as it may contain raw HTML coming from
    end users (e.g. project replies) that would otherwise be passed through
    verbatim. Use ``sanitize=False`` only for content fully controlled by the
    document template itself.
    """
    if md_text is None:
        return ''
    html = markdown.markdown(
        text=md_text,
        extensions=[
            DSWMarkdownExt(),
            'fenced_code',
            'pymdownx.tilde',
        ],
        extension_configs={
            # only enable ~~strikethrough~~, keep single ~tilde~ literal
            'pymdownx.tilde': {'subscript': False},
        },
    )
    if not sanitize:
        # explicitly requested raw HTML pass-through (template-controlled content)
        return markupsafe.Markup(html)  # noqa: S704
    return markupsafe.Markup(sanitize_html(html))


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
