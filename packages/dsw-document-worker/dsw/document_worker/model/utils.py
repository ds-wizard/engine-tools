import io

import markdown


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
markdown.Markdown.output_formats['plain'] = unmark_element  # type: ignore
__md = markdown.Markdown(output_format='plain')  # type: ignore
__md.stripTopLevelTags = False


def unmarkdown(text):
    return __md.convert(text)
