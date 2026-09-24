local ooxml = function (s)
  return pandoc.RawBlock('openxml', s)
end

local end_portrait_section = ooxml [[
  <w:p><w:pPr><w:sectPr></w:sectPr></w:pPr></w:p>
]]

local end_landscape_section = ooxml [[
<w:p>
  <w:pPr>
    <w:sectPr>
      <w:pgSz w:h="11906" w:w="16838" w:orient="landscape" />
    </w:sectPr>
  </w:pPr>
</w:p>
]]

function Div (div)
  if div.classes:includes 'landscape' then
    div.content:insert(1, end_portrait_section)
    div.content:insert(end_landscape_section)
    return div
  end
end

function Para (para)
  for _, inline in ipairs(para.content) do
    if inline.t == "Str" and inline.text == "\\landscape" then
      return end_portrait_section
    end
    if inline.t == "Str" and inline.text == "\\portrait" then
      return end_landscape_section
    end
  end
end
