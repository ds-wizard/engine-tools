import pytest

from dsw.config import (
    DSWConfigParser,
    InvalidConfigurationError,
    MissingConfigurationError,
)


MINIMAL_CONFIG = 'database:\n  connectionString: postgresql://user:pass@db:5432/dsw\n'


def make_parser(content: str = MINIMAL_CONFIG) -> DSWConfigParser:
    parser = DSWConfigParser()
    parser.read_string(content)
    return parser


@pytest.mark.parametrize('content', ['just a string', '- a\n- b', '42', 'a: [1,'])
def test_reject_non_mapping_config(content):
    parser = DSWConfigParser()
    assert not parser.can_read(content)
    with pytest.raises(InvalidConfigurationError):
        parser.read_string(content)


def test_empty_config_is_readable_but_invalid():
    parser = DSWConfigParser()
    assert parser.can_read('')
    parser.read_string('')
    assert parser.cfg == {}
    with pytest.raises(MissingConfigurationError) as e:
        parser.validate()
    assert e.value.missing == ['database.connectionString']


def test_validate_passes_with_connection_string():
    make_parser().validate()


def test_validate_passes_with_env_connection_string(monkeypatch):
    monkeypatch.setenv('DSW_DATABASE_CONNECTION_STRING', 'postgresql://user:pass@db:5432/dsw')
    parser = make_parser('general:\n  environment: Test\n')
    parser.validate()


def test_prefixed_env_var_wins_over_generic(monkeypatch):
    monkeypatch.setenv('SENTRY_DSN', 'https://ambient@example.org/1')
    monkeypatch.setenv('DSW_SENTRY_DSN', 'https://own@example.org/2')
    parser = make_parser()
    assert parser.sentry.workers_dsn == 'https://own@example.org/2'


def test_prefixed_alias_wins_over_generic(monkeypatch):
    monkeypatch.setenv('SENTRY_DSN', 'https://ambient@example.org/1')
    monkeypatch.setenv('DSW_SENTRY_WORKER_DSN', 'https://own@example.org/3')
    parser = make_parser()
    assert parser.sentry.workers_dsn == 'https://own@example.org/3'


def test_env_var_boolean_disables(monkeypatch):
    monkeypatch.setenv('DSW_CLOUD_ENABLED', 'false')
    parser = make_parser('cloud:\n  enabled: true\n')
    assert parser.cloud.multi_tenant is False


def test_yaml_boolean():
    assert make_parser('cloud:\n  enabled: true\n').cloud.multi_tenant is True
    assert make_parser('cloud:\n  enabled: false\n').cloud.multi_tenant is False
    assert make_parser().cloud.multi_tenant is False


def test_sentry_numeric_options():
    parser = make_parser('sentry:\n  maxBreadcrumbs: 100\n  tracesSampleRate: 0.5\n')
    sentry = parser.sentry
    assert sentry.max_breadcrumbs == 100
    assert sentry.traces_sample_rate == 0.5


def test_sentry_numeric_options_from_env(monkeypatch):
    monkeypatch.setenv('DSW_SENTRY_MAX_BREADCRUMBS', '50')
    monkeypatch.setenv('DSW_SENTRY_TRACES_SAMPLE_RATE', '0.25')
    sentry = make_parser().sentry
    assert sentry.max_breadcrumbs == 50
    assert sentry.traces_sample_rate == 0.25


def test_sentry_defaults():
    sentry = make_parser().sentry
    assert sentry.enabled is False
    assert sentry.workers_dsn is None
    assert sentry.max_breadcrumbs is None
    assert sentry.traces_sample_rate is None
