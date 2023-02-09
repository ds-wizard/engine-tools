import aiohttp
import aiohttp.client_exceptions
import functools
import pathlib
import urllib.parse

from typing import List, Optional

from .consts import DEFAULT_ENCODING, APP, VERSION
from .model import Template, TemplateFile, TemplateFileType


class DSWCommunicationError(RuntimeError):

    def __init__(self, reason: str, message: str):
        """
        Exception representing communication error with DSW.

        Args:
            reason (str): Cause of the error.
            message (str): Additional information about the error.
        """
        self.reason = reason
        self.message = message


def handle_client_errors(func):
    @functools.wraps(func)
    async def handled_client_call(job, *args, **kwargs):
        try:
            return await func(job, *args, **kwargs)
        except DSWCommunicationError as e:
            # Already DSWCommunicationError (re-raise)
            raise e
        except aiohttp.client_exceptions.ContentTypeError as e:
            raise DSWCommunicationError(
                reason='Unexpected response type',
                message=e.message
            )
        except aiohttp.client_exceptions.ClientResponseError as e:
            raise DSWCommunicationError(
                reason='Error response status',
                message=f'Server responded with error HTTP status {e.status}: {e.message}'
            )
        except aiohttp.client_exceptions.InvalidURL as e:
            raise DSWCommunicationError(
                reason='Invalid URL',
                message=f'Provided API URL seems invalid: {e.url}'
            )
        except aiohttp.client_exceptions.ClientConnectorError as e:
            raise DSWCommunicationError(
                reason='Server unreachable',
                message=f'Desired server is not reachable (errno {e.os_error.errno})'
            )
        except Exception as e:
            raise DSWCommunicationError(
                reason='Communication error',
                message=f'Communication with server failed ({e})'
            )
    return handled_client_call


class DSWAPIClient:

    def _headers(self, extra=None):
        headers = {
            'Authorization': f'Bearer {self.token}',
            'User-Agent': f'{APP}/{VERSION}'
        }
        if extra is not None:
            headers.update(extra)
        return headers

    @staticmethod
    def _check_status(r: aiohttp.ClientResponse, expected_status):
        r.raise_for_status()
        if r.status != expected_status:
            raise DSWCommunicationError(
                reason='Unexpected response status',
                message=f'Server responded with unexpected HTTP status {r.status}: '
                        f'{r.reason} (expecting {expected_status})'
            )

    def __init__(self, api_url: str, session=None):
        """
        Exception representing communication error with DSW.

        Args:
            api_url (str): URL of DSW API for HTTP communication.
            session (aiohttp.ClientSession): Optional custom session for HTTP communication.
        """
        self.api_url = api_url
        self.token = None
        self.session = session or aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False))

    @property
    def templates_endpoint(self):
        return f'{self.api_url}/document-templates'

    @property
    def drafts_endpoint(self):
        return f'{self.api_url}/document-template-drafts'

    async def close(self):
        await self.session.close()

    async def safe_close(self) -> bool:
        try:
            await self.session.close()
            return True
        except Exception:
            return False

    async def _post_json(self, endpoint, json) -> dict:
        async with self.session.post(f'{self.api_url}{endpoint}', json=json, headers=self._headers()) as r:
            self._check_status(r, expected_status=201)
            return await r.json()

    async def _put_json(self, endpoint, json) -> dict:
        async with self.session.put(f'{self.api_url}{endpoint}', json=json, headers=self._headers()) as r:
            self._check_status(r, expected_status=200)
            return await r.json()

    async def _get_json(self, endpoint) -> dict:
        async with self.session.get(f'{self.api_url}{endpoint}', headers=self._headers()) as r:
            self._check_status(r, expected_status=200)
            return await r.json()

    async def _get_bytes(self, endpoint) -> bytes:
        async with self.session.get(f'{self.api_url}{endpoint}', headers=self._headers()) as r:
            self._check_status(r, expected_status=200)
            return await r.read()

    async def _delete(self, endpoint) -> bool:
        async with self.session.delete(f'{self.api_url}{endpoint}', headers=self._headers()) as r:
            return r.status == 204

    @handle_client_errors
    async def login(self, email: str, password: str) -> Optional[str]:
        req = {'email': email, 'password': password}
        body = await self._post_json('/tokens', json=req)
        self.token = body.get('token', None)
        return self.token

    @handle_client_errors
    async def check_template_exists(self, remote_id: str) -> bool:
        async with self.session.get(f'{self.templates_endpoint}/{remote_id}', headers=self._headers()) as r:
            if r.status == 404:
                return False
            self._check_status(r, expected_status=200)
            return True

    @handle_client_errors
    async def check_draft_exists(self, remote_id: str) -> bool:
        async with self.session.get(f'{self.drafts_endpoint}/{remote_id}', headers=self._headers()) as r:
            if r.status == 404:
                return False
            self._check_status(r, expected_status=200)
            return True

    @handle_client_errors
    async def get_templates(self) -> List[Template]:
        body = await self._get_json('/document-templates/all')
        return list(map(_load_remote_template, body))

    @handle_client_errors
    async def get_drafts(self) -> List[Template]:
        # TODO: better paging
        body = await self._get_json('/document-template-drafts?size=10000')
        drafts = body.get('_embedded', {}).get('documentTemplateDrafts', [])
        return list(map(_load_remote_template, drafts))

    @handle_client_errors
    async def get_template_bundle(self, remote_id: str) -> bytes:
        async with self.session.get(
                url=f'{self.api_url}/document-templates/{remote_id}/bundle'
                    f'?Authorization=Bearer%20{self.token}',
                headers=self._headers(),
        ) as r:
            self._check_status(r, expected_status=200)
            return await r.content.read()

    @handle_client_errors
    async def get_template_draft(self, remote_id: str) -> Template:
        body = await self._get_json(f'/document-template-drafts/{remote_id}')
        return _load_remote_template(body)

    @handle_client_errors
    async def get_template_draft_files(self, remote_id: str) -> List[TemplateFile]:
        body = await self._get_json(f'/document-template-drafts/{remote_id}/files')
        result = []
        for file_body in body:
            file_id = file_body['uuid']
            template_file = await self.get_template_draft_file(remote_id, file_id)
            result.append(template_file)
        return result

    @handle_client_errors
    async def get_template_draft_file(self, remote_id: str, file_id: str) -> TemplateFile:
        body = await self._get_json(f'/document-template-drafts/{remote_id}/files/{file_id}')
        return _load_remote_file(body)

    @handle_client_errors
    async def get_template_draft_assets(self, remote_id: str) -> List[TemplateFile]:
        body = await self._get_json(f'/document-template-drafts/{remote_id}/assets')
        result = []
        for file_body in body:
            asset_id = file_body['uuid']
            template_asset = await self.get_template_draft_asset(remote_id, asset_id)
            result.append(template_asset)
        return result

    @handle_client_errors
    async def get_template_draft_asset(self, remote_id: str, asset_id: str) -> TemplateFile:
        body = await self._get_json(f'/document-template-drafts/{remote_id}/assets/{asset_id}')
        content = await self._get_bytes(f'/document-template-drafts/{remote_id}/assets/{asset_id}/content')
        return _load_remote_asset(body, content)

    @handle_client_errors
    async def create_new_template_draft(self, template: Template, remote_id: str) -> Template:
        created_template = await self._post_json(
            endpoint='/document-template-drafts',
            json=template.serialize_for_create(),
        )
        if created_template['id'] != remote_id:
            raise RuntimeError('Organization ID changed during the process')
        body = await self._put_json(
            endpoint=f'/document-template-drafts/{remote_id}',
            json=template.serialize_for_update()
        )
        return _load_remote_template(body)

    @handle_client_errors
    async def update_template_draft(self, template: Template, remote_id: str) -> Template:
        body = await self._put_json(
            endpoint=f'/document-template-drafts/{remote_id}',
            json=template.serialize_for_update(),
        )
        return _load_remote_template(body)

    @handle_client_errors
    async def post_template_draft_file(self, remote_id: str, tfile: TemplateFile):
        data = await self._post_json(
            endpoint=f'/document-template-drafts/{remote_id}/files',
            json={
                'fileName': tfile.filename.as_posix(),
                'content': tfile.content.decode(DEFAULT_ENCODING)
            }
        )
        return _load_remote_file(data)

    @handle_client_errors
    async def put_template_draft_file_content(self, remote_id: str, tfile: TemplateFile):
        self.session.headers.update(self._headers())
        async with self.session.put(
                f'{self.api_url}/document-template-drafts/{remote_id}/files/{tfile.remote_id}/content',
                data=tfile.content,
                headers={'Content-Type': 'text/plain;charset=UTF-8'},
        ) as r:
            self._check_status(r, expected_status=200)
            body = await r.json()
            return _load_remote_file(body)

    @handle_client_errors
    async def post_template_draft_asset(self, remote_id: str, tfile: TemplateFile):
        data = aiohttp.FormData()
        data.add_field(
            name='file',
            value=tfile.content,
            filename=tfile.filename.as_posix(),
            content_type=tfile.content_type,
        )
        data.add_field(
            name='fileName',
            value=tfile.filename.as_posix(),
        )
        async with self.session.post(
                f'{self.api_url}/document-template-drafts/{remote_id}/assets',
                data=data,
                headers=self._headers(),
        ) as r:
            self._check_status(r, expected_status=201)
            body = await r.json()
            return _load_remote_asset(body, tfile.content)

    @handle_client_errors
    async def put_template_draft_asset_content(self, remote_id: str, tfile: TemplateFile):
        data = aiohttp.FormData()
        data.add_field(
            name='file',
            value=tfile.content,
            filename=tfile.filename.as_posix(),
            content_type=tfile.content_type,
        )
        data.add_field(
            name='fileName',
            value=tfile.filename.as_posix(),
        )
        async with self.session.put(
                f'{self.api_url}/document-template-drafts/{remote_id}/assets/{tfile.remote_id}/content',
                data=data,
                headers=self._headers()
        ) as r:
            self._check_status(r, expected_status=200)
            body = await r.json()
            return _load_remote_asset(body, tfile.content)

    @handle_client_errors
    async def delete_template_draft(self, remote_id: str) -> bool:
        return await self._delete(f'/document-template-drafts/{remote_id}')

    @handle_client_errors
    async def delete_template_draft_file(self, remote_id: str, file_id: str) -> bool:
        if file_id is None:
            raise RuntimeWarning('Tried to delete file without ID (None)')
        return await self._delete(f'/document-template-drafts/{remote_id}/files/{file_id}')

    @handle_client_errors
    async def delete_template_draft_asset(self, remote_id: str, asset_id: str) -> bool:
        if asset_id is None:
            raise RuntimeWarning('Tried to delete asset without ID (None)')
        return await self._delete(f'/document-template-drafts/{remote_id}/assets/{asset_id}')

    @handle_client_errors
    async def get_api_version(self) -> str:
        body = await self._get_json('/')
        return body['version']

    @handle_client_errors
    async def get_organization_id(self) -> str:
        body = await self._get_json('/configs/bootstrap')
        return body['organization']['organizationId']


def _load_remote_file(data: dict) -> TemplateFile:
    content = data.get('content', None)  # type: str
    filename = str(data.get('fileName', ''))  # type: str
    template_file = TemplateFile(
        remote_id=data.get('uuid', None),
        remote_type=TemplateFileType.file,
        filename=pathlib.Path(urllib.parse.unquote(filename)),
        content=content.encode(encoding=DEFAULT_ENCODING),
    )
    return template_file


def _load_remote_asset(data: dict, content: bytes) -> TemplateFile:
    filename = str(data.get('fileName', ''))
    template_file = TemplateFile(
        remote_id=data.get('uuid', None),
        remote_type=TemplateFileType.asset,
        filename=pathlib.Path(urllib.parse.unquote(filename)),
        content_type=data.get('contentType', None),
        content=content,
    )
    return template_file


def _load_remote_template(data: dict) -> Template:
    return Template.load_remote(data)
