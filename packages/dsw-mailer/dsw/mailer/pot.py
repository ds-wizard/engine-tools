"""The default mail POT: built with the templates, kept current in S3 by the mailer (WEP 27, B2).

The default templates are rendered from the mailer's own templates directory, so S3 holds only
their POT, at the instance-level key ``mail-templates/mail.pot``, for the backend to serve for
translating. The POT is built when the templates are packaged (``dsw-mailer make-pot``), into
``<templates>/locale/mail.pot``, with ``Project-Id-Version: <kind>:<version>`` and empty
``Language`` and ``X-Display-Name`` for the translator.

The mailer uploads it at startup, and on request (``dsw-mailer sync-default-pot``, or the
``syncDefaultPot`` Lambda event), storing the version as the object metadata ``version``. It
replaces the stored POT only with a newer version, or with the same version but other content;
it never downgrades it unless forced.
"""
from __future__ import annotations

import enum
import hashlib
import logging
import typing

import jinja2.ext
import packaging.version
import polib


if typing.TYPE_CHECKING:
    import pathlib

    from dsw.storage import ObjectInfo, S3Storage


LOG = logging.getLogger(__name__)

DEFAULT_POT_OBJECT = 'mail-templates/mail.pot'
#: relative to the templates directory
POT_PATH = 'locale/mail.pot'
POT_CONTENT_TYPE = 'text/x-gettext-translation'
VERSION_METADATA = 'version'
DEFAULT_KIND = 'dsw-mail-templates'
#: Jinja extensions the templates use, besides i18n
EXTENSIONS = 'jinja2.ext.do'
POT_HEADER = ('Fill in the header before uploading the translation:\n'
              "  Language        the language's code, such as de or pt-BR\n"
              '  X-Display-Name  its name as people choose it, such as Deutsch')


def build_pot(templates_dir: pathlib.Path, project_id_version: str) -> bytes:
    """The POT of every ``*.j2`` template, in file and line order, deterministic."""
    pot = polib.POFile(wrapwidth=0)
    # the upload reads the language and its name from the header (WEP 27), so the POT
    # carries both, empty, and says what goes there - as the frontend's UI POT does
    pot.header = POT_HEADER
    pot.metadata = {
        'Project-Id-Version': project_id_version,
        'Language': '',
        'X-Display-Name': '',
        'MIME-Version': '1.0',
        'Content-Type': 'text/plain; charset=UTF-8',
        'Content-Transfer-Encoding': '8bit',
        'Plural-Forms': 'nplurals=2; plural=n == 1 ? 0 : 1;',
    }
    entries: dict[tuple[str, str], polib.POEntry] = {}
    for path in sorted(templates_dir.rglob('*.j2'), key=lambda p: p.as_posix()):
        name = path.relative_to(templates_dir).as_posix()
        with path.open('rb') as fileobj:
            extracted = list(jinja2.ext.babel_extract(
                fileobj, jinja2.ext.GETTEXT_FUNCTIONS, [], {'extensions': EXTENSIONS}))
        for lineno, _, message, comments in extracted:
            msgid, msgid_plural = _message_ids(message)
            if not msgid:
                continue
            key = (msgid, msgid_plural)
            if key not in entries:
                entries[key] = polib.POEntry(
                    msgid=msgid, msgid_plural=msgid_plural,
                    msgstr_plural={0: '', 1: ''} if msgid_plural else {},
                    comment='\n'.join(comments), occurrences=[],
                )
                pot.append(entries[key])
            entries[key].occurrences.append((name, str(lineno)))
    return str(pot).encode('utf-8')


def _message_ids(message: str | tuple | None) -> tuple[str, str]:
    if isinstance(message, tuple):
        singular = message[0] or ''
        plural = message[1] if len(message) > 1 and message[1] else ''
        return singular, plural
    return message or '', ''


def project_id_version(pot: bytes) -> tuple[str, str]:
    """``(kind, version)`` from the ``Project-Id-Version: <kind>:<version>`` header."""
    value = polib.pofile(pot.decode('utf-8')).metadata.get('Project-Id-Version', '')
    kind, sep, version = value.rpartition(':')
    if not sep or not kind or not version:
        raise ValueError(f'Project-Id-Version is not <kind>:<version>: "{value}"')
    return kind, version


class SyncResult(enum.Enum):
    UPLOADED = 'uploaded, none was stored'
    REPLACED = 'replaced'
    UP_TO_DATE = 'up to date'
    NEWER_STORED = 'kept, the stored one is newer'


def decide(stored: ObjectInfo | None, version: str, md5: str, *,
           force: bool = False) -> SyncResult:
    """What to do with the stored default POT, given the local version and content MD5."""
    if stored is None:
        return SyncResult.UPLOADED
    stored_version = stored.metadata.get(VERSION_METADATA)
    if stored_version == version and stored.etag == md5:
        return SyncResult.UP_TO_DATE
    if force:
        return SyncResult.REPLACED
    try:
        older = packaging.version.Version(stored_version or '')
    except packaging.version.InvalidVersion:
        LOG.warning('Stored default mail POT has no valid version (%s), replacing it',
                    stored_version)
        return SyncResult.REPLACED
    newer = packaging.version.Version(version)
    if older > newer:
        return SyncResult.NEWER_STORED
    return SyncResult.REPLACED


def sync_default_pot(s3: S3Storage, templates_dir: pathlib.Path, *,
                     force: bool = False) -> SyncResult:
    """Make ``mail-templates/mail.pot`` in S3 the POT of these templates, unless it is newer."""
    pot = (templates_dir / POT_PATH).read_bytes()
    kind, version = project_id_version(pot)
    packaging.version.Version(version)  # fail before touching S3
    md5 = hashlib.md5(pot, usedforsecurity=False).hexdigest()
    result = decide(s3.head_instance_object(object_name=DEFAULT_POT_OBJECT), version, md5,
                    force=force)
    if result in (SyncResult.UPLOADED, SyncResult.REPLACED):
        s3.store_instance_object(
            object_name=DEFAULT_POT_OBJECT,
            content_type=POT_CONTENT_TYPE,
            data=pot,
            metadata={VERSION_METADATA: version},
        )
    LOG.info('Default mail POT %s:%s: %s', kind, version, result.value)
    return result


__all__ = ['DEFAULT_KIND', 'DEFAULT_POT_OBJECT', 'POT_PATH', 'SyncResult', 'build_pot',
           'decide', 'project_id_version', 'sync_default_pot']
