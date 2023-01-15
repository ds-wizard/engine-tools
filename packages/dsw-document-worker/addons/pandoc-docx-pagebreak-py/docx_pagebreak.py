#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" pandoc-docx-pagebreakpy
Pandoc filter to insert pagebreak as openxml RawBlock
Only for docx output

- https://github.com/UoA-eResearch/pandoc-docx-pagebreak-py
"""
import panflute as pf


class DocxPagebreak(object):

    @staticmethod
    def _make_pagebreak():
        return pf.RawBlock('<w:p><w:r><w:br w:type="page" /></w:r></w:p>', format='openxml')

    @staticmethod
    def _make_toc(instr: str):
        toc_lines = [
            r'<w:sdt>',
            r'<w:sdtContent xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
            r'<w:p><w:r>',
            r'<w:fldChar w:fldCharType="begin" w:dirty="true" />',
        ]

        if instr == r"\toc1":
            toc_lines.append(r'<w:instrText xml:space="preserve">TOC \o "1-1" \h \z \u</w:instrText>')
        elif instr == r"\toc2":
            toc_lines.append(r'<w:instrText xml:space="preserve">TOC \o "1-2" \h \z \u</w:instrText>')
        elif instr == r"\toc4":
            toc_lines.append(r'<w:instrText xml:space="preserve">TOC \o "1-4" \h \z \u</w:instrText>')
        elif instr == r"\toc5":
            toc_lines.append(r'<w:instrText xml:space="preserve">TOC \o "1-5" \h \z \u</w:instrText>')
        elif instr == r"\toc6":
            toc_lines.append(r'<w:instrText xml:space="preserve">TOC \o "1-6" \h \z \u</w:instrText>')
        else:
            toc_lines.append(r'<w:instrText xml:space="preserve">TOC \o "1-3" \h \z \u</w:instrText>')

        toc_lines.append(r'<w:fldChar w:fldCharType="separate" />')
        toc_lines.append(r'<w:fldChar w:fldCharType="end" />')
        toc_lines.append(r'</w:r></w:p>')
        toc_lines.append(r'</w:sdtContent>')
        toc_lines.append(r'</w:sdt>')
        return pf.RawBlock('\n'.join(toc_lines), format='openxml')

    def action(self, elem, doc):
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
    dp = DocxPagebreak()
    return pf.run_filter(dp.action, doc=doc)


if __name__ == '__main__':
    main()
