local ooxml = function (s)
  return pandoc.RawBlock('openxml', s)
end

function _make_toc(instr)
  local toc_lines = {
    '<w:sdt>',
    '<w:sdtContent xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
    '<w:p><w:r>',
    '<w:fldChar w:fldCharType="begin" w:dirty="true" />',
  }

  if instr == "\\toc1" then
    table.insert(toc_lines, '<w:instrText xml:space="preserve">TOC \\o "1-1" \\h \\z \\u</w:instrText>')
  elseif instr == "\\toc2" then
    table.insert(toc_lines, '<w:instrText xml:space="preserve">TOC \\o "1-2" \\h \\z \\u</w:instrText>')
  elseif instr == "\\toc4" then
    table.insert(toc_lines, '<w:instrText xml:space="preserve">TOC \\o "1-4" \\h \\z \\u</w:instrText>')
  elseif instr == "\\toc5" then
    table.insert(toc_lines, '<w:instrText xml:space="preserve">TOC \\o "1-5" \\h \\z \\u</w:instrText>')
  elseif instr == "\\toc6" then
    table.insert(toc_lines, '<w:instrText xml:space="preserve">TOC \\o "1-6" \\h \\z \\u</w:instrText>')
  else
    table.insert(toc_lines, '<w:instrText xml:space="preserve">TOC \\o "1-3" \\h \\z \\u</w:instrText>')
  end

  table.insert(toc_lines, '<w:fldChar w:fldCharType="separate" />')
  table.insert(toc_lines, '<w:fldChar w:fldCharType="end" />')
  table.insert(toc_lines, '</w:r></w:p>')
  table.insert(toc_lines, '</w:sdtContent>')
  table.insert(toc_lines, '</w:sdt>')

  return ooxml(table.concat(toc_lines, '\n'))
end

function _Para (para)
  for _, inline in ipairs(para.content) do
    if inline.t == 'Str' and inline.text:match('^\\toc%d$') then
      return _make_toc(inline.text)
    end
  end
end

function _RawBlock (raw)
  if raw.text:match('^\\toc%d$') then
    return _make_toc(raw.text)
  end
end

if FORMAT == 'docx' then
    return { { Plain = _Para, Para = _Para, RawBlock = _RawBlock } }
end
