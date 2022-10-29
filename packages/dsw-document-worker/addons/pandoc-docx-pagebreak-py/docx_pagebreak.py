#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" pandoc-docx-pagebreakpy
Pandoc filter to insert pagebreak as openxml RawBlock
Only for docx output

- https://github.com/UoA-eResearch/pandoc-docx-pagebreak-py
"""

import panflute as pf


class DocxPagebreak(object):
    pagebreak = pf.RawBlock("<w:p><w:r><w:br w:type=\"page\" /></w:r></w:p>", format="openxml")
    toc = pf.RawBlock(r"""
<w:sdt>
    <w:sdtContent xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        <w:p>
            <w:r>
                <w:fldChar w:fldCharType="begin" w:dirty="true" />
                <w:instrText xml:space="preserve">TOC \o "1-3" \h \z \u</w:instrText>
                <w:fldChar w:fldCharType="separate" />
                <w:fldChar w:fldCharType="end" />
            </w:r>
        </w:p>
    </w:sdtContent>
</w:sdt>
""", format="openxml")

    def action(self, elem, doc):
        if doc.format != "docx":
            return elem
        if isinstance(elem, (pf.Para, pf.Plain)):
            for child in elem.content:
                if isinstance(child, pf.Str) and child.text == r"\newpage":
                    elem = self.pagebreak
                elif isinstance(child, pf.Str) and child.text == r"\toc":
                    elem = self.toc
        if isinstance(elem, pf.RawBlock):
            if elem.text == r"\newpage":
                elem = self.pagebreak
            elif elem.text == r"\toc":
                elem = self.toc
        return elem


def main(doc=None):
    dp = DocxPagebreak()
    return pf.run_filter(dp.action, doc=doc)


if __name__ == "__main__":
    main()
