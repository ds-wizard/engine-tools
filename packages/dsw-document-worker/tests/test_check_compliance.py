"""What the worker does with the document context before rendering."""
import types

import pytest

from dsw.document_worker.exceptions import JobError
from dsw.document_worker.worker import Job


def make_job(doc_context: dict, project_uuid: str | None = None, db=None) -> Job:
    # Job.__init__ needs the application context and the database; neither matters here
    job = Job.__new__(Job)
    job.doc_uuid = '00000000-0000-0000-0000-000000000001'
    job.tenant_uuid = '00000000-0000-0000-0000-0000000000aa'
    job.doc_context = doc_context
    job.doc = types.SimpleNamespace(project_uuid=project_uuid)
    job.format = types.SimpleNamespace(requires_via_extras=lambda name: True)
    job.ctx = types.SimpleNamespace(app=types.SimpleNamespace(db=db))
    job._enrich_context_config = lambda: None
    return job


@pytest.mark.parametrize('version', ['19.0', '19', '19.4'])
def test_current_metamodel_is_accepted(version):
    make_job({'metamodelVersion': version}).check_compliance()


@pytest.mark.parametrize(('version', 'shown'), [
    ('18.3', '18.3'),
    ('17', '17.0'),
    ('20.0', '20.0'),
    (None, 'missing'),
    ('x.y', 'missing'),
])
def test_other_metamodel_asks_for_regeneration(version, shown):
    context = {} if version is None else {'metamodelVersion': version}
    with pytest.raises(JobError) as error:
        make_job(context).check_compliance()
    # exactly what ends up in the document's worker_log
    assert error.value.db_message() == (
        f'Unsupported document context metamodel version {shown}, expected 19.x. '
        'Regenerate the document.')
    assert error.value.skip_reporting  # an expected condition, not a bug to report


class FakeDb:

    def __init__(self):
        self.calls = []

    def fetch_project_submissions(self, project_uuid, tenant_uuid):
        self.calls.append('submissions')
        return [types.SimpleNamespace(to_dict=lambda: {'uuid': 's1'})]

    def fetch_project_simple(self, project_uuid, tenant_uuid):
        self.calls.append('project')
        return types.SimpleNamespace(to_dict=lambda: {'uuid': project_uuid})


def test_extras_of_a_project_document():
    db = FakeDb()
    job = make_job({}, project_uuid='00000000-0000-0000-0000-000000000002', db=db)
    job._enrich_context()
    assert job.doc_context['extras'] == {
        'submissions': [{'uuid': 's1'}],
        'project': {'uuid': '00000000-0000-0000-0000-000000000002'},
    }


def test_extras_of_a_km_editor_document():
    # a KM editor preview has no project: nothing to fetch
    db = FakeDb()
    job = make_job({}, project_uuid=None, db=db)
    job._enrich_context()
    assert job.doc_context['extras'] == {'submissions': [], 'project': None}
    assert db.calls == []


def test_questionnaire_extras_are_gone():
    # `extras.questionnaire` was the deprecated alias of `extras.project` (removed in 19.0)
    job = make_job({}, project_uuid='00000000-0000-0000-0000-000000000002', db=FakeDb())
    job._enrich_context()
    assert 'questionnaire' not in job.doc_context['extras']
