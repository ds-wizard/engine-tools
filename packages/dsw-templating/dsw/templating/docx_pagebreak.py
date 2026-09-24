"""Pandoc filter `pandoc-docx-pagebreakpy`: page breaks and TOC as OpenXML raw blocks (DOCX only).

`\\newpage` becomes a page break and `\\toc` (`\\toc1` to `\\toc6` for the depth) a table of
contents. Installed as the `pandoc-docx-pagebreakpy` command with the `docx` extra, for
`--filter=pandoc-docx-pagebreakpy` in the `args` of the `pandoc` step. Deprecated in favour of the
`docx-pagebreak.lua` and `docx-toc.lua` filters.

Based on https://github.com/pandocker/pandoc-docx-pagebreak-py (formerly the
`pandoc-docx-pagebreak` addon of the document worker):
"""
# MIT License
#
# Copyright (c) 2018 pandocker
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from __future__ import annotations

import sys

from .exceptions import MissingExtraError, require


TOC_DEPTHS = {r'\toc1': 1, r'\toc2': 2, r'\toc4': 4, r'\toc5': 5, r'\toc6': 6}
DEFAULT_TOC_DEPTH = 3


class DocxPagebreak:

    def __init__(self):
        self.pf = require('panflute', 'docx')

    def _make_pagebreak(self):
        return self.pf.RawBlock('<w:p><w:r><w:br w:type="page" /></w:r></w:p>', format='openxml')

    def _make_toc(self, instr: str):
        depth = TOC_DEPTHS.get(instr, DEFAULT_TOC_DEPTH)
        toc_lines = [
            r'<w:sdt>',
            r'<w:sdtContent xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
            r'<w:p><w:r>',
            r'<w:fldChar w:fldCharType="begin" w:dirty="true" />',
            rf'<w:instrText xml:space="preserve">TOC \o "1-{depth}" \h \z \u</w:instrText>',
            r'<w:fldChar w:fldCharType="separate" />',
            r'<w:fldChar w:fldCharType="end" />',
            r'</w:r></w:p>',
            r'</w:sdtContent>',
            r'</w:sdt>',
        ]
        return self.pf.RawBlock('\n'.join(toc_lines), format='openxml')

    def action(self, elem, doc):
        pf = self.pf
        if doc.format != 'docx':
            return elem
        if isinstance(elem, (pf.Para, pf.Plain)):
            for child in elem.content:
                if isinstance(child, pf.Str) and child.text == r'\newpage':
                    elem = self._make_pagebreak()
                elif isinstance(child, pf.Str) and child.text.startswith(r'\toc'):
                    elem = self._make_toc(child.text)
        if isinstance(elem, pf.RawBlock):
            if elem.text == r'\newpage':
                elem = self._make_pagebreak()
            elif elem.text.startswith(r'\toc'):
                elem = self._make_toc(elem.text)
        return elem


def main(doc=None):
    try:
        dp = DocxPagebreak()
    except MissingExtraError as e:
        # run by pandoc: a message on stderr rather than a traceback
        sys.exit(f'pandoc-docx-pagebreakpy: {e}')
    return dp.pf.run_filter(dp.action, doc=doc)
