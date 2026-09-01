import pytest

from dsw.document_worker.model.utils import render_markdown
from dsw.document_worker.sanitizer import sanitize_html


@pytest.mark.parametrize('html', [
    '<script>alert(1)</script>',
    '<iframe src="https://example.org"></iframe>',
    '<object data="file:///etc/passwd"></object>',
    '<embed src="file:///etc/passwd">',
    '<svg><use href="file:///etc/passwd"/></svg>',
    '<style>body { background: url(file:///etc/passwd) }</style>',
    '<link rel="stylesheet" href="file:///etc/passwd">',
])
def test_dangerous_elements_removed(html):
    result = sanitize_html(html)
    assert 'file:' not in result
    assert 'script' not in result
    assert 'iframe' not in result
    assert 'object' not in result
    assert 'embed' not in result


@pytest.mark.parametrize('html', [
    '<img src="file:///etc/passwd">',
    '<img src="http://169.254.169.254/latest/meta-data/" onerror="alert(1)">',
    '<a href="javascript:alert(1)">x</a>',
    '<a href="JaVaScRiPt:alert(1)">x</a>',
    '<a href="java\tscript:alert(1)">x</a>',
    '<a href="data:text/html,alert">x</a>',
    '<div onclick="alert(1)">x</div>',
    '<img src="x" onerror="alert(1)">',
])
def test_dangerous_attributes_removed(html):
    result = sanitize_html(html)
    assert 'file:' not in result
    assert 'javascript' not in result.lower()
    assert 'data:text/html' not in result
    assert 'onerror' not in result
    assert 'onclick' not in result


def test_url_with_no_scheme_survives():
    # relative URLs are resolved against the document (template directory)
    assert 'logo.png' in sanitize_html('<img src="logo.png">')


def test_data_image_survives():
    result = sanitize_html('<img src="data:image/png;base64,AAAA">')
    assert 'data:image/png;base64,AAAA' in result


def test_common_markup_survives():
    html = (
        '<h1 id="x">Title</h1>\n<p class="lead"><strong>bold</strong>'
        ' <em>italic</em> <del>strike</del> <code>code</code></p>\n'
        '<ul><li>item</li></ul>\n<pre><code class="language-python">'
        'print(1)</code></pre>\n'
        '<table><thead><tr><th>h</th></tr></thead><tbody><tr>'
        '<td align="center">c</td></tr></tbody><tfoot><tr><td>f</td>'
        '</tr></tfoot></table>\n'
        '<a href="https://example.org" title="t">link</a>'
        ' <a href="mailto:someone@example.org">mail</a>'
    )
    result = sanitize_html(html)
    for expected in ('<h1 id="x">', 'class="lead"', '<strong>', '<em>', '<del>',
                     'class="language-python"', '<tfoot>', 'align="center"',
                     'href="https://example.org"', 'title="t"',
                     'href="mailto:someone@example.org"'):
        assert expected in result


def test_style_attribute_filtered():
    result = sanitize_html(
        '<div style="color: red; background-image: url(http://example.org/x)">x</div>'
    )
    assert 'color:red' in result.replace(' ', '')
    assert 'background-image' not in result


def test_render_markdown_sanitizes_by_default():
    result = render_markdown('Hello <script>alert(1)</script> world')
    assert '<script>' not in result
    assert 'Hello' in result


def test_render_markdown_sanitizes_markdown_syntax_urls():
    assert 'file:' not in render_markdown('![x](file:///etc/passwd)')
    assert 'javascript' not in render_markdown('[x](javascript:alert(1))').lower()


def test_render_markdown_raw_opt_in():
    result = render_markdown('<script>alert(1)</script>', sanitize=False)
    assert '<script>alert(1)</script>' in result


def test_render_markdown_keeps_features():
    result = render_markdown('# Title\n\n- a\n- b\n\n~~gone~~\n\n```py\nx = 1\n```')
    assert '<h1>Title</h1>' in result
    assert '<li>a</li>' in result
    assert '<del>gone</del>' in result
    assert 'class="language-py"' in result


def test_render_markdown_none():
    assert render_markdown(None) == ''
