import pathlib
import types

import pytest

from dsw.document_worker.config import TemplatesConfig
from dsw.document_worker.context import Context


class FakeS3:
    """Minimal in-memory stand-in for the document template locale storage."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.downloads: list[str] = []
        self.stored: list[str] = []

    @staticmethod
    def _key(locale_uuid: str, file_name: str) -> str:
        return f'{locale_uuid}/{file_name}'

    def download_document_template_locale(self, *, tenant_uuid, locale_uuid,
                                          file_name, target_path) -> bool:
        key = self._key(locale_uuid, file_name)
        self.downloads.append(key)
        data = self.objects.get(key)
        if data is None:
            return False
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)
        return True

    def store_document_template_locale(self, *, tenant_uuid, locale_uuid,
                                       file_name, content_type, data):
        key = self._key(locale_uuid, file_name)
        self.stored.append(key)
        self.objects[key] = data


@pytest.fixture
def fake_context(tmp_path: pathlib.Path):
    original = Context._instance
    s3 = FakeS3()
    Context.initialize(
        db=None,
        s3=s3,
        config=types.SimpleNamespace(templates=TemplatesConfig(templates=[])),
        workdir=tmp_path,
    )
    yield types.SimpleNamespace(s3=s3, workdir=tmp_path)
    Context._instance = original
