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

    def __init__(self, md):
        super().__init__(md)

    def run(self, lines):
        prev_li = False
        new_lines = []

        for line in lines:
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
                continue

            new_lines.append(line)

        return new_lines


def render_markdown(md_text: str):
    if md_text is None:
        return ''
    return markupsafe.Markup(markdown.markdown(
        text=md_text,
        extensions=[
            DSWMarkdownExt(),
        ],
    ))
