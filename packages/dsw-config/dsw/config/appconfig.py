"""Read the configuration YAML from AWS AppConfig instead of a local file.

Opt-in: with ``AWS_APP_CONFIG`` unset, the local file is read as before. The
identifiers follow the backend (``Shared.Bootstrap.AwsAppConfig``): the
environment is ``Default`` and the profile is the config file name with dots
replaced by dashes (``application.yml`` -> ``application-yml``); both can be
overridden. Credentials and region come from the standard AWS chain, i.e. the
Lambda execution role.

A warm Lambda keeps its session between invocations and only asks AppConfig
again once the poll interval has passed; an unchanged configuration comes back
empty and the cached copy is used.
"""
from __future__ import annotations

import dataclasses
import logging
import os
import time
import typing

from .parser import InvalidConfigurationError


if typing.TYPE_CHECKING:
    import pathlib


LOG = logging.getLogger(__name__)

VAR_APPLICATION = 'AWS_APP_CONFIG'
VAR_ENVIRONMENT = 'AWS_APP_CONFIG_ENVIRONMENT'
VAR_PROFILE = 'AWS_APP_CONFIG_PROFILE'
DEFAULT_ENVIRONMENT = 'Default'


@dataclasses.dataclass
class _Session:
    content: str
    token: str | None
    interval: int
    next_poll_at: float


_client: typing.Any = None
_sessions: dict[tuple[str, str, str], _Session] = {}


def _get_client():
    global _client  # noqa: PLW0603
    if _client is None:
        import boto3  # noqa: PLC0415
        _client = boto3.client('appconfigdata')
    return _client


def profile_for(path: pathlib.Path) -> str:
    return path.name.replace('.', '-')


def _start(session_key: tuple[str, str, str]) -> str:
    application, environment, profile = session_key
    LOG.info('Starting an AWS AppConfig session (%s)', '/'.join(session_key))
    start = _get_client().start_configuration_session(
        ApplicationIdentifier=application,
        EnvironmentIdentifier=environment,
        ConfigurationProfileIdentifier=profile,
    )
    return start['InitialConfigurationToken']


def _poll(session_key: tuple[str, str, str], previous: _Session | None) -> _Session:
    token = previous.token if previous is not None and previous.token is not None \
        else _start(session_key)
    response = _get_client().get_latest_configuration(ConfigurationToken=token)
    content = response['Configuration'].read().decode('utf-8')
    if not content:
        if previous is None:
            raise InvalidConfigurationError(
                f'AWS AppConfig returned an empty configuration for {"/".join(session_key)}',
            )
        content = previous.content
    interval = response.get('NextPollIntervalInSeconds', 60)
    session = _Session(
        content=content,
        token=response['NextPollConfigurationToken'],
        interval=interval,
        next_poll_at=time.monotonic() + interval,
    )
    _sessions[session_key] = session
    return session


def fetch(application: str, environment: str, profile: str) -> str:
    session_key = (application, environment, profile)
    session = _sessions.get(session_key)
    if session is None:
        return _poll(session_key, None).content
    if time.monotonic() < session.next_poll_at:
        return session.content
    try:
        return _poll(session_key, session).content
    except Exception as e:
        # A token is single-use and expires after 24 hours, and it is spent whether or not
        # the response reached us. Dropping it makes the next poll start a new session
        # instead of retrying a dead token forever; the cached content stays the fallback.
        LOG.warning('AWS AppConfig poll failed, using the cached configuration: %s', e)
        session.token = None
        session.next_poll_at = time.monotonic() + session.interval
        return session.content


def read_config(path: pathlib.Path, encoding: str = 'utf-8') -> str:
    application = os.environ.get(VAR_APPLICATION)
    if not application:
        return path.read_text(encoding=encoding)
    return fetch(
        application=application,
        environment=os.environ.get(VAR_ENVIRONMENT) or DEFAULT_ENVIRONMENT,
        profile=os.environ.get(VAR_PROFILE) or profile_for(path),
    )
