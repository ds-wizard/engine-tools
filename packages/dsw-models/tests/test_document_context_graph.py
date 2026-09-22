import copy

import pytest
from conftest import load_synthetic

from dsw.models.document_context import graph


def enriched() -> dict:
    ctx = copy.deepcopy(load_synthetic('document_context.json'))
    ctx['config'].update({'serviceName': 'FAIR Wizard', 'serviceNameShort': 'FW',
                          'serviceUrl': 'https://fw.example.org/', 'serviceDomainName': 'fw.example.org',
                          'appTitle': 'FW', 'appTitleShort': 'FW', 'primaryColor': '#0033aa',
                          'logoUrl': ''})
    return ctx


@pytest.fixture
def dc() -> graph.DocumentContext:
    context = graph.DocumentContext(ctx=enriched())
    context.resolve_links()
    return context


def test_object_model(dc):
    assert dc.current_phase.title == 'Before submitting'
    assert dc.project.todos == ['00000000-0000-0000-0000-000000000101.00000000-0000-0000-0000-000000000201']
    assert dc.cfg is dc.config and dc.e is dc.km.entities and dc.pkg is dc.km_package
    question = dc.km.chapters[0].questions[0]
    assert question.is_required
    assert [reply.item_title for reply in question.replies.values()] == ['Yes']
    item_select = dc.e.questions['00000000-0000-0000-0000-000000000206']
    assert [reply.item_title for reply in item_select.replies.values()] == ['first item']
    assert dc.config.primary_color.is_dark
    assert dc.groups[0].group.members[0].membership_type == 'owner'
    assert dc.project.files['60000000-0000-0000-0000-000000000001'].download_url.endswith('/download')


def test_file_question_quirk_is_kept(dc):
    file_question = dc.e.questions['00000000-0000-0000-0000-000000000207']
    assert file_question.is_required is None
    assert file_question.tags == []


def test_metamodel_version_is_checked():
    ctx = enriched()
    ctx['metamodelVersion'] = '17.0'
    with pytest.raises(ValueError, match='expected major version 18'):
        graph.DocumentContext(ctx=ctx)


def test_markdown():
    pytest.importorskip('markdown')
    reply = graph.StringReply(path='a.b', value='**bold**\n\n<script>x</script>', created_at=None,
                              created_by=None)
    assert str(reply.markdown_html) == '<p><strong>bold</strong></p>\n'
    assert reply.markdown_plain.startswith('bold')  # raw HTML text is kept, as in the worker
