from __future__ import annotations

import io
import re
import typing

import markdown
import markdown.preprocessors
import markupsafe


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


def render_markdown(md_text: str):
    if md_text is None:
        return ''
    return markupsafe.Markup(markdown.markdown(
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
    ))
