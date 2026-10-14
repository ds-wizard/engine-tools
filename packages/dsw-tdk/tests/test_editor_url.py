"""The link to the template editor printed by `put` (Wizard 5.0 client addresses)."""
import asyncio
import types

import pytest

from dsw.tdk.api_client import WizardAPIClient
from dsw.tdk.core import TDKCore


class FakeClient:

    def __init__(self, draft_workspace, workspaces):
        self.client_url = 'https://fw.example.org'
        self.draft_workspace = draft_workspace
        self.workspaces = workspaces

    async def get_template_draft(self, remote_uuid):
        return types.SimpleNamespace(workspace_uuid=self.draft_workspace)

    async def get_workspace_uuids(self, limit=2):
        return self.workspaces[:limit]


@pytest.mark.parametrize(('draft_workspace', 'workspaces', 'expected'), [
    ('ws-of-draft', ['ws-1', 'ws-2'], 'https://fw.example.org/w/ws-of-draft/document-template-editors/d1'),
    (None, ['ws-1'], 'https://fw.example.org/w/ws-1/document-template-editors/d1'),
    (None, ['ws-1', 'ws-2'], None),  # shared by the organization: any workspace opens it
])
def test_remote_editor_url(draft_workspace, workspaces, expected):
    core = TDKCore()
    core.client = FakeClient(draft_workspace, workspaces)
    core.remote_uuid = 'd1'
    assert asyncio.run(core.remote_editor_url()) == expected


@pytest.mark.parametrize(('api_url', 'client_url'), [
    ('https://fw.example.org/api', 'https://fw.example.org'),
    ('https://fw.example.org/api/', 'https://fw.example.org'),
    ('http://localhost:3000', 'http://localhost:3000'),
])
def test_client_url(api_url, client_url):
    async def make():
        client = WizardAPIClient(api_url=api_url, api_key='k')
        await client.close()
        return client.client_url
    assert asyncio.run(make()) == client_url
