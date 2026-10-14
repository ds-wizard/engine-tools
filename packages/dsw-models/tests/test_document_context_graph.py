import copy

import pytest
from conftest import load_synthetic

from dsw.models.document_context import graph


def enriched(name: str = 'document_context.json') -> dict:
    ctx = copy.deepcopy(load_synthetic(name))
    ctx['config'].update({'serviceName': 'FAIR Wizard', 'serviceNameShort': 'FW',
                          'serviceUrl': 'https://fw.example.org/', 'serviceDomainName': 'fw.example.org',
                          'appTitle': 'FW', 'primaryColor': '#0033aa', 'logoUrl': ''})
    return ctx


@pytest.fixture
def dc() -> graph.DocumentContext:
    context = graph.DocumentContext(ctx=enriched())
    context.resolve_links()
    return context


def test_object_model(dc):
    assert dc.hash.startswith('sha256:')
    assert dc.workspace.name == 'Faculty of Science'
    assert dc.km_editor is None
    assert dc.questionnaire.phase.title == 'Before submitting'
    assert dc.questionnaire.todos == ['00000000-0000-0000-0000-000000000101.00000000-0000-0000-0000-000000000201']
    assert dc.questionnaire.version.name == '1.0'
    question = dc.km.chapters[0].questions[0]
    assert question.is_required
    assert [reply.item_title for reply in question.replies.values()] == ['Yes']
    item_select = dc.km.entities.questions['00000000-0000-0000-0000-000000000206']
    assert [reply.item_title for reply in item_select.replies.values()] == ['first item']
    assert dc.config.primary_color.is_dark
    assert dc.project.visibility == 'PrivateProjectVisibility'
    assert dc.project.users[0].is_owner
    assert dc.project.groups[0].group.members[0].membership_type == 'owner'
    file = dc.questionnaire.files['60000000-0000-0000-0000-000000000001']
    assert file.reply is not None
    assert file.download_url == ('https://fair-wizard.example.org/projects/'
                                 '80000000-0000-0000-0000-000000000004/files/'
                                 '60000000-0000-0000-0000-000000000001/download')
    assert [m.metric.abbreviation for m in dc.questionnaire.report.total_report.metrics] == ['F']
    assert dc.km_package.id == 'synthetic'  # no version in the id since 19.0
    assert dc.km_package.version == '1.0.0'


def test_document(dc):
    document = dc.document
    assert (document.document_template.id, document.document_template.version) == (
        'questionnaire-report', '2.4.0')
    assert document.format.name == 'PDF'
    assert document.preview is False
    assert document.event_uuid == '30000000-0000-0000-0000-000000000012'
    assert document.locale.code == 'cs'


def test_km_editor_context():
    dc = graph.DocumentContext(ctx=enriched('document_context_km_editor.json'))
    dc.resolve_links()
    assert dc.project is None
    assert (dc.km_editor.id, dc.km_editor.version) == ('synthetic', '1.1.0')
    assert dc.km_editor.previous_package_version == '1.0.0'
    assert dc.km_editor.knowledge_model_metamodel_version == 20
    assert dc.km_package.version == '1.0.0'
    assert dc.document is None
    assert dc.questionnaire.phase is graph.PHASE_NEVER
    assert len(dc.questionnaire.replies) == 7


def test_document_and_package_may_be_missing():
    ctx = enriched('document_context_km_editor.json')
    ctx['knowledgeModelPackage'] = None
    del ctx['document']
    dc = graph.DocumentContext(ctx=ctx)
    dc.resolve_links()
    assert dc.km_package is None
    assert dc.document is None


@pytest.mark.parametrize('removed', ['e', 'cfg', 'org', 'pkg', 'doc', 'replies', 'current_phase',
                                     'report', 'users', 'groups', 'organization'])
def test_18_shortcuts_are_gone(dc, removed):
    assert not hasattr(dc, removed)


def test_entity_shortcuts_stay(dc):
    assert dc.km.e is dc.km.entities
    assert dc.km.a is dc.km.annotations


def test_file_question_quirk_is_kept(dc):
    file_question = dc.km.entities.questions['00000000-0000-0000-0000-000000000207']
    assert file_question.is_required is None
    assert file_question.tags == []


@pytest.mark.parametrize('version', ['18.3', '17.0', '20.0'])
def test_metamodel_version_is_checked(version):
    ctx = enriched()
    ctx['metamodelVersion'] = version
    with pytest.raises(ValueError, match='expected major version 19'):
        graph.DocumentContext(ctx=ctx)


def test_markdown():
    pytest.importorskip('markdown')
    reply = graph.StringReply(path='a.b', value='**bold**\n\n<script>x</script>', created_at=None,
                              created_by=None)
    assert str(reply.markdown_html) == '<p><strong>bold</strong></p>\n'
    assert reply.markdown_plain.startswith('bold')  # raw HTML text is kept, as in the worker
