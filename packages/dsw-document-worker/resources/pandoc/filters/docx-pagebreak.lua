local ooxml = function (s)
  return pandoc.RawBlock('openxml', s)
end

local pagebreak = ooxml [[
  <w:p><w:r><w:br w:type="page" /></w:r></w:p>
]]

function _Div (div)
  if div.classes:includes 'newpage-before' then
    div.content:insert(1, pagebreak)
  end
  if div.classes:includes 'newpage-after' then
    div.content:insert(pagebreak)
  end
  return div
end

function _Para (para)
  for _, inline in ipairs(para.content) do
    if inline.t == 'Str' and inline.text == '\\newpage' then
      return pagebreak
    end
  end
end

function _RawBlock (raw)
  if raw.text == '\\newpage' then
    return pagebreak
  end
end

if FORMAT == 'docx' then
    return { { Div = _Div, Plain = _Para, Para = _Para, RawBlock = _RawBlock } }
end
